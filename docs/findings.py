"""Makes the tables in docs/FINDINGS.md: time saved for walkers at the Holborn settings.

Run from the project folder:

    python3 -m docs.findings              # full run, about a minute on 16 cores
    python3 -m docs.findings --quick      # short runs and 2 seeds, to check it works

Prints Markdown. Each table compares stand-both with walk-left on the same
crowds (seeds), with the line finished so every measured person counts.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable, Sequence
from concurrent.futures import ProcessPoolExecutor
from typing import Any, TextIO

from escalator_sim import SimConfig, __version__, sweep
from escalator_sim.metrics import mean_ci
from escalator_sim.report import time_winner, winner

STRATEGIES = ["stand-both", "walk-left"]

# Holborn 5/6 (23.4 m rise, one of a pair), as calibrated in tests/test_calibration.py.
# 45% walk: Davis & Dutta's formulas give 47.4 walking and 58.4 standing per minute there.
HOLBORN = dict(
    rise=23.4, belt_speed=0.72, step_depth=0.4, walk_gap=0.9, walk_fraction=0.45,
    defect_prob=0.0, blocker_rate=0.0, warmup=180.0, duration=900.0, drain=1,
)
# --quick: still longer than one ride (65 s) and two rides measured.
QUICK = dict(warmup=120.0, duration=300.0)

ARRIVALS = [60, 70, 80, 90, 100, 110, 120, 130, 140, 150]
BLOCKERS = [0.0, 0.01, 0.02, 0.05, 0.1]
WALK_SHARES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
GRID_ARRIVALS = [60, 90, 110, 130]
GRID_BLOCKERS = [0.0, 0.02, 0.05]
# Davis & Dutta's walking-side formula at 23.4 m, one of a pair: the most people seen walking
# with a queue waiting. Above about 105 arrivals/min, a fixed 45% would walk more than that.
MEASURED_WALKERS_PER_MIN = 83.49 - 1.20 * 23.4 - 8.05
CAPPED_ARRIVALS = [110, 120, 130, 140, 150]

# (heading, swept parameter, its values, fixed settings)
SWEEPS: list[tuple[str, str, list[float], dict[str, float]]] = [
    ("Arrival rate, no blockers", "arrival_rate", ARRIVALS, {}),
    ("People standing in the walk lane, at 90 arrivals/min", "blocker_rate", BLOCKERS,
     {"arrival_rate": 90}),
    ("People standing in the walk lane, at 110 arrivals/min", "blocker_rate", BLOCKERS,
     {"arrival_rate": 110}),
    ("Share who want to walk, at 110 arrivals/min", "walk_fraction", WALK_SHARES,
     {"arrival_rate": 110}),
]
HEADERS = ["stand-both people/min", "walk-left people/min", "Walkers save s",
           "Others save s", "Net saved, person-s/min", "Fastest for walkers", "Most people/min"]


def net_saving_per_min(point: dict[str, Any]) -> dict[str, float | None]:
    """Total time walk-left saves everyone, in person-seconds per minute measured.

    For each seed: walkers' saving × walkers measured + others' saving × others
    measured, divided by the measured minutes. Mean and 95% margin over seeds.
    An empty group adds nothing; a seed with a missing saving is skipped.
    """
    entry = point["time_saved"][0]
    runs = point["strategies"][entry["by"]]["runs"]
    values: list[float | None] = []
    for i, run in enumerate(runs):
        total = 0.0
        for group in ("cares", "others"):
            saving, count = entry["per_seed"][group][i], run[f"{group}_count"]
            if count and saving is None:
                total = None
                break
            total += (saving or 0.0) * count
        values.append(None if total is None else total / (run["measured_seconds"] / 60.0))
    return mean_ci(values)


def _fmt(stats: dict[str, float | None], digits: int = 1, sign: bool = True) -> str:
    if stats["mean"] is None:
        return "–"
    text = f"{stats['mean']:+.{digits}f}" if sign else f"{stats['mean']:.{digits}f}"
    if stats["ci95"] is not None:
        text += f" ±{stats['ci95']:.{digits}f}"
    return text.replace("-", "−")


def row(point: dict[str, Any]) -> list[str]:
    """Table cells for one sweep point, after its value column(s)."""
    sums = {s: point["strategies"][s]["summary"] for s in STRATEGIES}
    entry = point["time_saved"][0]
    return [
        _fmt(sums["stand-both"]["throughput_per_min"], sign=False),
        _fmt(sums["walk-left"]["throughput_per_min"], sign=False),
        _fmt(entry["cares"]),
        _fmt(entry["others"]),
        _fmt(net_saving_per_min(point), digits=0),
        time_winner(entry),
        winner({s: sums[s]["throughput_per_min"] for s in STRATEGIES}),
    ]


def table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines)


def _label(param: str, value: float) -> str:
    return f"{value:.0%}" if param in ("blocker_rate", "walk_fraction") else f"{value:g}"


def main(argv: Sequence[str] | None = None, out: TextIO | None = None) -> int:
    out = out or sys.stdout
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--replications", "-n", type=int, default=20)
    parser.add_argument("--jobs", "-j", type=int, default=0, help="0 = all CPUs [0]")
    parser.add_argument("--quick", action="store_true", help="short runs, 2 seeds")
    args = parser.parse_args(argv)
    settings = {**HOLBORN, **(QUICK if args.quick else {})}
    reps = 2 if args.quick else args.replications
    base = SimConfig(**settings)

    pool = ProcessPoolExecutor(max_workers=args.jobs or os.cpu_count()) if args.jobs != 1 else None
    map_fn: Callable | None = None
    if pool:
        def map_fn(fn: Callable, items: list) -> list:
            return list(pool.map(fn, items, chunksize=4))

    def run(param: str, values: list[float], fixed: dict[str, float]) -> list[dict[str, Any]]:
        config = base.with_changes(**fixed)
        return sweep(config, param, values, STRATEGIES, reps, map_fn=map_fn)["points"]

    shown = ", ".join(f"{k}={v:g}" for k, v in settings.items())
    out.write(f"Engine {__version__}; {reps} seeds per point (1–{reps}); settings: {shown}.\n")
    out.write("Savings are walk-left vs stand-both: positive means walk-left is faster.\n")
    try:
        for i, (heading, param, values, fixed) in enumerate(SWEEPS, start=1):
            points = run(param, values, fixed)
            rows = [[_label(param, p["value"]), *row(p)] for p in points]
            out.write(f"\n### {i}. {heading}\n\n{table([param, *HEADERS], rows)}\n")
        rows = []
        for blockers in GRID_BLOCKERS:
            for p in run("arrival_rate", GRID_ARRIVALS, {"blocker_rate": blockers}):
                rows.append([f"{p['value']:g}", _label("blocker_rate", blockers), *row(p)])
        rows.sort(key=lambda r: (float(r[0]), r[1]))
        out.write(f"\n### {len(SWEEPS) + 1}. Arrival rate and blockers together\n\n"
                  f"{table(['arrival_rate', 'blocker_rate', *HEADERS], rows)}\n")
        rows = []
        for rate in CAPPED_ARRIVALS:
            share = MEASURED_WALKERS_PER_MIN / rate
            (p,) = run("arrival_rate", [rate], {"walk_fraction": share})
            rows.append([f"{rate:g}", f"{share:.0%}", *row(p)])
        out.write(f"\n### {len(SWEEPS) + 2}. Arrival rate, walkers held at the measured "
                  f"{MEASURED_WALKERS_PER_MIN:.1f} per minute, no blockers\n\n"
                  f"{table(['arrival_rate', 'walk_fraction', *HEADERS], rows)}\n")
    finally:
        if pool:
            pool.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
