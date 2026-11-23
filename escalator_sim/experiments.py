"""Batch experiments: replications, strategy comparisons and parameter sweeps.

These are plain functions returning plain data. The command line adds parallel
running and formatting on top; a web front end can call them directly.
"""
from __future__ import annotations

from typing import Any, Callable, Optional, Sequence

from .config import SimConfig
from .engine import Simulation
from .metrics import aggregate

# A "map" function lets callers swap in a parallel pool; the default is serial.
MapFn = Callable[[Callable[[tuple], dict], list[tuple]], list[dict]]


def run_one(job: tuple[dict[str, Any], str, int]) -> dict[str, Any]:
    """Run one simulation. Takes a tuple so it can be sent to a process pool."""
    config_dict, strategy, seed = job
    sim = Simulation(SimConfig.from_dict(config_dict), strategy, seed)
    return sim.run()


def _serial_map(fn, jobs):
    return [fn(job) for job in jobs]


def compare(
    config: SimConfig,
    strategies: Sequence[str],
    replications: int,
    base_seed: int = 1,
    map_fn: Optional[MapFn] = None,
) -> dict[str, Any]:
    """Run every strategy with the same seeds (same crowds) and aggregate."""
    map_fn = map_fn or _serial_map
    seeds = [base_seed + i for i in range(replications)]
    jobs = [(config.to_dict(), s, seed) for s in strategies for seed in seeds]
    runs = map_fn(run_one, jobs)
    by_strategy = {s: runs[i * replications:(i + 1) * replications] for i, s in enumerate(strategies)}
    return {
        "config": config.to_dict(),
        "seeds": seeds,
        "strategies": {
            s: {"summary": aggregate(rs), "runs": rs} for s, rs in by_strategy.items()
        },
    }


def sweep(
    config: SimConfig,
    param: str,
    values: Sequence[Any],
    strategies: Sequence[str],
    replications: int,
    base_seed: int = 1,
    map_fn: Optional[MapFn] = None,
) -> dict[str, Any]:
    """Compare strategies at each value of one parameter."""
    if param not in SimConfig.field_names():
        raise ValueError(f"unknown parameter {param!r}")
    configs = [config.with_changes(**{param: v}) for v in values]  # validates early
    map_fn = map_fn or _serial_map
    seeds = [base_seed + i for i in range(replications)]
    jobs = [(c.to_dict(), s, seed) for c in configs for s in strategies for seed in seeds]
    runs = map_fn(run_one, jobs)

    points = []
    i = 0
    for value in values:
        point = {"value": value, "strategies": {}}
        for s in strategies:
            rs = runs[i:i + replications]
            i += replications
            point["strategies"][s] = {"summary": aggregate(rs), "runs": rs}
        points.append(point)
    return {"config": config.to_dict(), "param": param, "seeds": seeds, "points": points}
