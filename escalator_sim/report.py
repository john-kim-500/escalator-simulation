"""Result formatting shared by the command line and the web interface.

Keeping CSV/JSON output and the "who wins" rule here means a file downloaded
from the browser is byte-for-byte what `--output csv|json` prints.
"""
from __future__ import annotations

import csv
import io
import json
from typing import Any

# Metrics shown in result tables: (key, header, format)
TABLE_METRICS = [
    ("throughput_per_min", "Thru/min", "{:.1f}"),
    ("wait_mean", "Wait avg s", "{:.1f}"),
    ("wait_p95", "Wait p95 s", "{:.1f}"),
    ("trip_mean", "Trip avg s", "{:.1f}"),
    ("trip_mean_cares", "Walkers' trip s", "{:.1f}"),
    ("trip_mean_others", "Others' trip s", "{:.1f}"),
    ("queue_max", "Max queue", "{:.0f}"),
    ("queue_end", "Queue end", "{:.0f}"),
    ("walked_share", "Walked", "{:.0%}"),
]


def winner(stats: dict[str, dict[str, float | None]]) -> str:
    """Strategy with the highest mean, or 'tie' if its lead is within the 95% CIs.

    `stats` maps strategy name to a mean_ci() dict ({mean, ci95, n}).
    """
    ranked = sorted(stats, key=lambda s: stats[s]["mean"] or 0, reverse=True)
    if len(ranked) < 2:
        return ranked[0] if ranked else "-"
    best, second = stats[ranked[0]], stats[ranked[1]]
    margin = (best["ci95"] or 0) + (second["ci95"] or 0)
    if best["ci95"] is None or (best["mean"] or 0) - (second["mean"] or 0) <= margin:
        return "tie"
    return ranked[0]


def time_winner(entry: dict[str, Any]) -> str:
    """Faster strategy for people who want to walk, from one time_saved() entry.

    `by` if the paired saving is above zero by more than its 95% margin, `over`
    if below by more, else 'tie'. '-' if there's no margin or the runs didn't
    drain (then the saving leaves out different people for each strategy).
    """
    stats = entry["cares"]
    if not entry["drained"] or stats["mean"] is None or stats["ci95"] is None:
        return "-"
    if stats["mean"] > stats["ci95"]:
        return entry["by"]
    if stats["mean"] < -stats["ci95"]:
        return entry["over"]
    return "tie"


def winners(data: dict[str, Any], metric: str = "throughput_per_min") -> list[str]:
    """Winner by `metric` for a compare result (one entry) or each sweep point."""
    if "points" in data:
        groups = [p["strategies"] for p in data["points"]]
    else:
        groups = [data["strategies"]]
    return [winner({s: d["summary"][metric] for s, d in g.items()}) for g in groups]


def flat_run(r: dict[str, Any]) -> dict[str, Any]:
    """One run's results as a flat CSV row (per-lane lists become columns)."""
    flat = {k: v for k, v in r.items() if not isinstance(v, list)}
    for i, v in enumerate(r["throughput_by_lane"]):
        flat[f"throughput_lane{i}"] = v
    return flat


def to_csv(rows: list[dict[str, Any]]) -> str:
    """Rows may have different columns (e.g. a sweep over lanes); the header is
    their union in first-seen order, and missing cells are left empty."""
    fieldnames = list(dict.fromkeys(k for row in rows for k in row))
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def to_json(data: Any) -> str:
    return json.dumps(data, indent=2) + "\n"


def compare_csv(data: dict[str, Any]) -> str:
    """Every run of a compare, one row each."""
    return to_csv([flat_run(r) for d in data["strategies"].values() for r in d["runs"]])


def sweep_csv(data: dict[str, Any]) -> str:
    """One row per (value, strategy) with the mean and CI of each metric."""
    rows = []
    for point in data["points"]:
        for s, d in point["strategies"].items():
            row = {data["param"]: point["value"], "strategy": s}
            for key, stats in d["summary"].items():
                row[f"{key}_mean"] = stats["mean"]
                row[f"{key}_ci95"] = stats["ci95"]
            rows.append(row)
    return to_csv(rows)


def experiment_csv(data: dict[str, Any]) -> str:
    return sweep_csv(data) if "points" in data else compare_csv(data)
