"""Summary statistics for a run and across replications.

Everything is measured after the warm-up period:
  * throughput counts people reaching the top during [warmup, end];
  * waits and trip times cover people who *arrived* after warm-up. People
    still queueing at the end count with the time waited so far, so waits are
    a lower bound when the escalator is overloaded (instead of hiding the
    longest waits).
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .engine import Simulation


def percentile(values: Sequence[float], q: float) -> float | None:
    """Linear-interpolated percentile (q in [0, 100]); None for no data."""
    if not values:
        return None
    data = sorted(values)
    k = (len(data) - 1) * q / 100.0
    lo, hi = math.floor(k), math.ceil(k)
    return data[lo] + (data[hi] - data[lo]) * (k - lo)


def mean(values: Sequence[float]) -> float | None:
    return sum(values) / len(values) if values else None


def summarize(sim: Simulation) -> dict[str, Any]:
    cfg = sim.config
    start, end = cfg.warmup, sim.time
    window = max(end - start, 1e-9)

    exits = [p for p in sim.finished if p.exit_time >= start]
    by_lane = [0] * cfg.lanes
    for p in exits:
        by_lane[p.lane] += 1

    cohort = [p for p in sim.people if p.arrival_time >= start]
    waits = [
        (p.board_time if p.board_time is not None else end) - p.arrival_time
        for p in cohort
    ]
    trips = [p.exit_time - p.arrival_time for p in cohort if p.exit_time is not None]
    queued_at_end = sum(len(q) for q in sim.queues)

    return {
        "strategy": sim.strategy.name,
        "seed": sim.seed,
        "measured_seconds": window,
        "throughput_per_min": len(exits) / window * 60.0,
        "throughput_by_lane": [n / window * 60.0 for n in by_lane],
        "wait_mean": mean(waits),
        "wait_p95": percentile(waits, 95),
        "wait_max": max(waits) if waits else None,
        "trip_mean": mean(trips),
        "trip_p95": percentile(trips, 95),
        "queue_mean": sim.queue_sum / sim.queue_samples if sim.queue_samples else 0.0,
        "queue_max": sim.queue_max,
        "lane_queue_max": list(sim.lane_queue_max),
        "queue_end": queued_at_end,
        "walked_share": (sum(p.walking for p in exits) / len(exits)) if exits else None,
        "arrived": len(sim.people),
        "finished": len(sim.finished),
        # Throughput is underestimated if the measured window starts before
        # anyone could have reached the top.
        "warmup_too_short": start < sim.length / cfg.belt_speed,
    }


# t critical values (two-sided 95%) for small samples; 1.96 beyond 30.
_T95 = [12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228,
        2.201, 2.179, 2.160, 2.145, 2.131, 2.120, 2.110, 2.101, 2.093, 2.086,
        2.080, 2.074, 2.069, 2.064, 2.060, 2.056, 2.052, 2.048, 2.045, 2.042]


def mean_ci(values: Iterable[float | None]) -> dict[str, float | None]:
    """Mean and 95% confidence half-width, ignoring missing values."""
    data = [v for v in values if v is not None]
    n = len(data)
    if n == 0:
        return {"mean": None, "ci95": None, "n": 0}
    m = sum(data) / n
    if n == 1:
        return {"mean": m, "ci95": None, "n": 1}
    sd = math.sqrt(sum((x - m) ** 2 for x in data) / (n - 1))
    t = _T95[n - 2] if n - 1 <= len(_T95) else 1.96
    return {"mean": m, "ci95": t * sd / math.sqrt(n), "n": n}


SCALAR_METRICS = [
    "throughput_per_min", "wait_mean", "wait_p95", "wait_max", "trip_mean",
    "trip_p95", "queue_mean", "queue_max", "queue_end", "walked_share",
]


def aggregate(results: Sequence[dict[str, Any]]) -> dict[str, dict[str, float | None]]:
    """Mean and 95% CI of each scalar metric across replications."""
    out = {key: mean_ci(r[key] for r in results) for key in SCALAR_METRICS}
    lanes = len(results[0]["throughput_by_lane"]) if results else 0
    for i in range(lanes):
        out[f"throughput_lane{i}"] = mean_ci(r["throughput_by_lane"][i] for r in results)
    return out
