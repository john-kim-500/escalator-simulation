"""Batch experiments: replications, strategy comparisons and parameter sweeps.

Each experiment is split into three steps so callers can control how the runs
are executed:

    jobs = plan_compare(...)            # list of independent runs
    runs = [run_one(job) for job in jobs]   # serially, in a pool, or one per frame
    data = collect_compare(jobs, runs)

`compare()` and `sweep()` do all three. Everything is plain data, so the same
functions serve the command line (with a process pool) and the browser worker
(one job at a time, with progress and cancel).
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from .config import SimConfig
from .engine import Simulation
from .metrics import aggregate, mean_ci

# A job is (config dict, strategy name, seed); it is a tuple so it pickles cheaply.
Job = tuple
MapFn = Callable[[Callable[[Job], dict], list[Job]], list[dict]]


def run_one(job: Job) -> dict[str, Any]:
    """Run one simulation to the end and return its results."""
    config_dict, strategy, seed = job
    return Simulation(SimConfig.from_dict(config_dict), strategy, seed).run()


def _serial_map(fn: Callable[[Job], dict], jobs: list[Job]) -> list[dict]:
    return [fn(job) for job in jobs]


def _seeds(replications: int, base_seed: int) -> list[int]:
    if replications < 1:
        raise ValueError("replications must be >= 1")
    return [base_seed + i for i in range(replications)]


def _difference(a: float | None, b: float | None) -> float | None:
    return None if a is None or b is None else a - b


def time_saved(runs: dict[str, Sequence[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Paired time saved for each pair of strategies, in the order given.

    `runs` maps strategy name to its runs, in seed order. For the pair
    (over, by), each seed's saving is trip(over) - trip(by): positive means
    `by` gets that group up faster. The margin of error is taken over these
    per-seed differences, so the crowd-to-crowd noise cancels. It is only fair
    when every run drained: otherwise each strategy leaves out different people.
    """
    names = list(runs)
    out = []
    for i, over in enumerate(names):
        for by in names[i + 1:]:
            pairs = list(zip(runs[over], runs[by]))
            per_seed = {
                group: [_difference(a[f"trip_mean_{group}"], b[f"trip_mean_{group}"])
                        for a, b in pairs]
                for group in ("cares", "others")
            }
            out.append({
                "by": by, "over": over,
                "drained": bool(pairs) and all(a["drained"] and b["drained"] for a, b in pairs),
                "cares": mean_ci(per_seed["cares"]),
                "others": mean_ci(per_seed["others"]),
                "per_seed": per_seed,
            })
    return out


# ------------------------------------------------------------------ compare

def plan_compare(config: SimConfig, strategies: Sequence[str], replications: int,
                 base_seed: int = 1) -> dict[str, Any]:
    seeds = _seeds(replications, base_seed)
    jobs = [(config.to_dict(), s, seed) for s in strategies for seed in seeds]
    return {"kind": "compare", "config": config.to_dict(), "strategies": list(strategies),
            "seeds": seeds, "jobs": jobs}


def collect_compare(plan: dict[str, Any], runs: Sequence[dict[str, Any]]) -> dict[str, Any]:
    n = len(plan["seeds"])
    by_strategy = {s: list(runs[i * n:(i + 1) * n]) for i, s in enumerate(plan["strategies"])}
    return {
        "config": plan["config"],
        "seeds": plan["seeds"],
        "strategies": {s: {"summary": aggregate(rs), "runs": rs} for s, rs in by_strategy.items()},
        "time_saved": time_saved(by_strategy),
    }


def compare(config: SimConfig, strategies: Sequence[str], replications: int,
            base_seed: int = 1, map_fn: MapFn | None = None) -> dict[str, Any]:
    """Run every strategy with the same seeds (same crowds) and aggregate."""
    plan = plan_compare(config, strategies, replications, base_seed)
    return collect_compare(plan, (map_fn or _serial_map)(run_one, plan["jobs"]))


# -------------------------------------------------------------------- sweep

def plan_sweep(config: SimConfig, param: str, values: Sequence[Any], strategies: Sequence[str],
               replications: int, base_seed: int = 1) -> dict[str, Any]:
    if param not in SimConfig.field_names():
        raise ValueError(f"unknown parameter {param!r}")
    configs = [config.with_changes(**{param: v}) for v in values]  # validates early
    seeds = _seeds(replications, base_seed)
    jobs = [(c.to_dict(), s, seed) for c in configs for s in strategies for seed in seeds]
    return {"kind": "sweep", "config": config.to_dict(), "param": param,
            "values": [getattr(c, param) for c in configs], "strategies": list(strategies),
            "seeds": seeds, "jobs": jobs}


def collect_sweep(plan: dict[str, Any], runs: Sequence[dict[str, Any]]) -> dict[str, Any]:
    n = len(plan["seeds"])
    points = []
    i = 0
    for value in plan["values"]:
        point = {"value": value, "strategies": {}}
        for s in plan["strategies"]:
            rs = runs[i:i + n]
            i += n
            point["strategies"][s] = {"summary": aggregate(rs), "runs": list(rs)}
        point["time_saved"] = time_saved({s: d["runs"] for s, d in point["strategies"].items()})
        points.append(point)
    return {"config": plan["config"], "param": plan["param"], "seeds": plan["seeds"],
            "points": points}


def sweep(config: SimConfig, param: str, values: Sequence[Any], strategies: Sequence[str],
          replications: int, base_seed: int = 1, map_fn: MapFn | None = None) -> dict[str, Any]:
    """Compare strategies at each value of one parameter."""
    plan = plan_sweep(config, param, values, strategies, replications, base_seed)
    return collect_sweep(plan, (map_fn or _serial_map)(run_one, plan["jobs"]))


def collect(plan: dict[str, Any], runs: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Collect either kind of experiment."""
    return (collect_compare if plan["kind"] == "compare" else collect_sweep)(plan, runs)
