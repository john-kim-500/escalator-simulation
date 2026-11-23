"""JSON API for front ends (used by the browser worker through Pyodide).

Every method takes and returns JSON strings, so the JavaScript side only needs
`JSON.stringify` / `JSON.parse` and never handles Python objects. No I/O,
threads or sleeping: the caller drives everything.
"""
from __future__ import annotations

import json
import math
import time
from typing import Any

from . import __version__
from .config import GROUPS, PARAM_INFO, PRESETS, SimConfig, check_values, convert_values
from .engine import Simulation
from .experiments import collect, plan_compare, plan_sweep, run_one
from .report import experiment_csv, time_winner, to_json, winners
from .strategies import KINDS, available_strategies, get_strategy


def dumps(data: Any) -> str:
    """JSON with non-finite floats as null (JSON.parse rejects Infinity/NaN)."""
    return json.dumps(_finite(data), separators=(",", ":"))


def _finite(x: Any) -> Any:
    if isinstance(x, float) and not math.isfinite(x):
        return None
    if isinstance(x, dict):
        return {k: _finite(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_finite(v) for v in x]
    return x


def check_config(values: dict[str, Any], strategies: list[str] | None = None) -> dict[str, Any]:
    """Validate partial settings (missing ones take defaults).

    Returns {ok, errors: [{field, message}], warnings: [...], derived, config}.
    """
    converted, errors = convert_values(values)
    full = {**SimConfig().to_dict(), **converted}
    if not errors:
        errors = check_values(full)
    result: dict[str, Any] = {"ok": False, "errors": [], "warnings": [], "derived": None,
                              "config": None}
    if not errors:
        config = SimConfig(**full)
        for name in strategies or []:
            try:
                get_strategy(name, config)
            except ValueError as exc:
                field = "lanes" if "lane" in str(exc) else "strategies"
                errors.append((field, f"{name}: {exc}"))
        if not errors:
            result.update(ok=True, config=config.to_dict(), derived=config.derived(),
                          warnings=[{"field": f, "message": m} for f, m in config.warnings()])
    result["errors"] = [{"field": f, "message": m} for f, m in errors]
    return result


class Session:
    """State for one front end: a set of live simulations and one experiment."""

    def __init__(self) -> None:
        self.sims: list[Simulation] = []
        self._plan: dict[str, Any] | None = None
        self._runs: list[dict[str, Any]] = []

    # ------------------------------------------------------------- info

    def info(self) -> str:
        return dumps({
            "version": __version__,
            "defaults": SimConfig().to_dict(),
            "param_info": PARAM_INFO,
            "groups": GROUPS,
            "presets": PRESETS,
            "strategies": available_strategies(),
            "kinds": KINDS,
        })

    def check(self, values_json: str, strategies_json: str = "null") -> str:
        return dumps(check_config(json.loads(values_json), json.loads(strategies_json)))

    # ------------------------------------------------------------- live

    def live_start(self, values_json: str, strategies_json: str, seed: int,
                   max_queue: int = 60) -> str:
        """Start one simulation per strategy, all with the same seed (same crowd)."""
        config = SimConfig.from_dict({**SimConfig().to_dict(), **json.loads(values_json)})
        self.sims = [Simulation(config, s, int(seed)) for s in json.loads(strategies_json)]
        return self._live_state(max_queue)

    def live_advance(self, seconds: float, max_queue: int = 60) -> str:
        """Advance every live simulation by the same simulated time.

        Only whole steps are taken (never overshooting), so a caller that asks
        for less than one step gets no change and can carry the remainder over
        to its next call. The final step to `duration` is always taken.
        """
        if self.sims:
            config = self.sims[0].config
            target = min(self.sims[0].time + float(seconds), config.duration)
            for sim in self.sims:
                if target >= config.duration - 1e-9:
                    sim.run(until=config.duration)
                else:
                    while sim.time + config.dt <= target + 1e-9:
                        sim.step()
        return self._live_state(max_queue)

    def _live_state(self, max_queue: int) -> str:
        return dumps({
            "time": self.sims[0].time if self.sims else 0.0,
            "done": all(s.done for s in self.sims),
            "sims": [{"strategy": s.strategy.name, "snapshot": s.snapshot(max_queue),
                      "stats": s.live_stats()} for s in self.sims],
        })

    def live_results(self) -> str:
        """Full results() of each live simulation (e.g. when it finishes).

        With config.drain on, finished simulations drain first, so the results
        equal Simulation.run().
        """
        for s in self.sims:
            if s.config.drain and s.done:
                s.drain()
        return dumps([s.results() for s in self.sims])

    # ------------------------------------------------------ experiments

    def exp_start(self, spec_json: str) -> str:
        """Plan an experiment. spec: {kind, config, strategies, replications, seed,
        and for sweeps param, values}. Returns {done: 0, total}.

        Errors are ValueErrors with the same messages as the command line.
        """
        spec = json.loads(spec_json)
        config = SimConfig.from_dict({**SimConfig().to_dict(), **spec.get("config", {})})
        strategies = list(spec.get("strategies") or [])
        if not strategies:
            raise ValueError("choose at least one strategy")
        for name in strategies:
            get_strategy(name, config)  # unknown name or too few lanes
        args = (strategies, int(spec["replications"]), int(spec.get("seed", 1)))
        if spec["kind"] == "compare":
            self._plan = plan_compare(config, *args)
        elif spec["kind"] == "sweep":
            param = spec["param"]
            if param not in SimConfig.field_names():
                raise ValueError(f"unknown parameter {param!r}")
            raw = list(spec["values"])
            if not raw:
                raise ValueError("enter at least one value to sweep")
            values = []
            for v in raw:
                converted, errors = convert_values({param: v})
                if not errors:
                    errors = check_values({**config.to_dict(), **converted})
                if errors:
                    raise ValueError(f"{param} = {v}: {errors[0][1]}")
                swept = config.with_changes(**converted)
                for name in strategies:
                    try:
                        get_strategy(name, swept)
                    except ValueError as exc:
                        raise ValueError(f"{param} = {v}: {exc}") from None
                values.append(converted[param])
            self._plan = plan_sweep(config, param, values, *args)
        else:
            raise ValueError(f"unknown experiment kind {spec['kind']!r}")
        self._runs = []
        return dumps({"done": 0, "total": len(self._plan["jobs"])})

    def exp_step(self, budget_seconds: float = 0.25) -> str:
        """Run jobs until about `budget_seconds` have passed. Returns {done, total}."""
        if self._plan is None:
            raise ValueError("no experiment started")
        jobs = self._plan["jobs"]
        start = time.perf_counter()
        while len(self._runs) < len(jobs):
            self._runs.append(run_one(jobs[len(self._runs)]))
            if time.perf_counter() - start >= budget_seconds:
                break
        return dumps({"done": len(self._runs), "total": len(jobs)})

    def exp_result(self) -> str:
        """{data, winners, time_winners, csv, json}: data is what compare()/sweep()
        return; winners uses the command line's tie rule on throughput and
        time_winners its "Fastest for walkers" rule (one entry per sweep value;
        "-" with fewer than two strategies or without the drain); csv/json are
        exactly what `--output csv|json` prints."""
        if self._plan is None or len(self._runs) < len(self._plan["jobs"]):
            raise ValueError("experiment not finished")
        data = collect(self._plan, self._runs)
        groups = data["points"] if "points" in data else [data]
        time_winners = [time_winner(g["time_saved"][0]) if g["time_saved"] else "-"
                        for g in groups]
        return dumps({"data": data, "winners": winners(data), "time_winners": time_winners,
                      "csv": experiment_csv(data), "json": to_json(data)})

    def exp_cancel(self) -> None:
        self._plan, self._runs = None, []
