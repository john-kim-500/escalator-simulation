"""Command line: python3 -m escalator_sim {run,compare,sweep,strategies} ...

Every SimConfig parameter is available as a flag (e.g. --arrival-rate 90).
"""
from __future__ import annotations

import argparse
import sys
from typing import Any, Optional, Sequence

from .config import GROUPS, PARAM_INFO, SimConfig
from .engine import Simulation
from .experiments import compare, sweep
from .report import TABLE_METRICS, experiment_csv, flat_run, to_csv, to_json, winner
from .strategies import available_strategies

# ------------------------------------------------------------------ parsing

def _config_parent() -> argparse.ArgumentParser:
    parent = argparse.ArgumentParser(add_help=False)
    defaults = SimConfig()
    groups = {key: parent.add_argument_group(f"{title} (defaults in brackets)")
              for key, title in GROUPS.items()}
    for name, typ in SimConfig.field_types().items():
        info = PARAM_INFO[name]
        unit = f" ({info['unit']})" if info["unit"] else ""
        groups[info["group"]].add_argument(
            "--" + name.replace("_", "-"), dest=name, type=typ, default=None,
            metavar=typ.__name__.upper(),
            help=f"{info['help']}{unit} [{getattr(defaults, name)}]",
        )
    return parent


def _strategy_list(text: str) -> list[str]:
    names = [s.strip() for s in text.split(",") if s.strip()]
    unknown = [s for s in names if s not in available_strategies()]
    if unknown:
        raise argparse.ArgumentTypeError(f"unknown strategy: {', '.join(unknown)}")
    return names


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m escalator_sim",
        description="Agent-based escalator simulator: stand on both sides vs walk on one.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    cfg = _config_parent()
    all_strategies = ",".join(available_strategies())

    def output_args(p):
        p.add_argument("--output", choices=["table", "json", "csv"], default="table",
                       help="output format, printed to stdout [table]")

    def batch_args(p, reps):
        p.add_argument("--strategies", type=_strategy_list, default=list(available_strategies()),
                       help=f"comma-separated [{all_strategies}]")
        p.add_argument("--replications", "-n", type=int, default=reps,
                       help=f"runs per strategy, seeds seed..seed+n-1 [{reps}]")
        p.add_argument("--seed", type=int, default=1, help="first seed [1]")
        p.add_argument("--jobs", "-j", type=int, default=1,
                       help="parallel processes (0 = all CPUs) [1]")

    p = sub.add_parser("run", parents=[cfg], help="run one simulation")
    p.add_argument("--strategy", choices=list(available_strategies()), default="walk-left")
    p.add_argument("--seed", type=int, default=1)
    output_args(p)

    p = sub.add_parser("compare", parents=[cfg], help="compare strategies on the same crowds")
    batch_args(p, 10)
    output_args(p)

    p = sub.add_parser("sweep", parents=[cfg], help="compare strategies across values of one parameter")
    p.add_argument("--param", required=True, choices=SimConfig.field_names())
    p.add_argument("--values", required=True, help="comma-separated values, e.g. 0,0.1,0.2")
    batch_args(p, 5)
    output_args(p)

    sub.add_parser("strategies", help="list available strategies")
    return parser


def config_from_args(args: argparse.Namespace) -> SimConfig:
    overrides = {k: getattr(args, k) for k in SimConfig.field_names() if getattr(args, k, None) is not None}
    return SimConfig.from_dict({**SimConfig().to_dict(), **overrides})


# --------------------------------------------------------------- formatting

def _fmt(value: Optional[float], fmt: str, ci: Optional[float] = None) -> str:
    if value is None:
        return "-"
    text = fmt.format(value)
    if ci is not None and "%" not in fmt:
        text += " ±" + fmt.format(ci)
    return text


def render_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    widths = [max(len(str(c)) for c in col) for col in zip(headers, *rows)]
    lines = ["  ".join(str(c).ljust(w) for c, w in zip(headers, widths))]
    lines.append("  ".join("-" * w for w in widths))
    lines += ["  ".join(str(c).ljust(w) for c, w in zip(row, widths)) for row in rows]
    return "\n".join(lines)


def _describe(config: SimConfig) -> str:
    warnings = "".join(f"WARNING: {msg}. Raise --{field}.\n" for field, msg in config.warnings())
    return warnings + (f"Escalator {config.length:.1f} m long ({config.rise:g} m rise), belt {config.belt_speed:g} m/s; "
            f"{config.arrival_rate:g} arrivals/min, {config.walk_fraction:.0%} want to walk; "
            f"measured {config.duration - config.warmup:g} s after {config.warmup:g} s warm-up.")


def _relative(a: Optional[float], b: Optional[float]) -> str:
    if a is None or not b:
        return "-"
    return f"{(a - b) / b:+.1%}"


# ----------------------------------------------------------------- commands

def _map_fn(jobs: int):
    if jobs == 1:
        return None
    from concurrent.futures import ProcessPoolExecutor

    def pooled(fn, items):
        with ProcessPoolExecutor(max_workers=jobs or None) as pool:
            return list(pool.map(fn, items, chunksize=4))
    return pooled


def cmd_run(args, out) -> None:
    config = config_from_args(args)
    result = Simulation(config, args.strategy, args.seed).run()
    if args.output == "json":
        out.write(to_json({"config": config.to_dict(), "result": result}))
    elif args.output == "csv":
        out.write(to_csv([flat_run(result)]))
    else:
        out.write(_describe(config) + "\n")
        out.write(f"Strategy {result['strategy']}, seed {result['seed']}\n\n")
        rows = [[header, _fmt(result[key], fmt)] for key, header, fmt in TABLE_METRICS]
        for i, v in enumerate(result["throughput_by_lane"]):
            rows.append([f"Lane {i} thru/min", f"{v:.1f}"])
        rows.append(["Arrived / finished", f"{result['arrived']} / {result['finished']}"])
        out.write(render_table(["Metric", "Value"], rows) + "\n")


def _strategy_rows(summaries: dict[str, dict]) -> list[list[str]]:
    rows = []
    for name, summary in summaries.items():
        row = [name]
        for key, _, fmt in TABLE_METRICS:
            row.append(_fmt(summary[key]["mean"], fmt, summary[key]["ci95"]))
        rows.append(row)
    return rows


def cmd_compare(args, out) -> None:
    config = config_from_args(args)
    data = compare(config, args.strategies, args.replications, args.seed, _map_fn(args.jobs))
    summaries = {s: d["summary"] for s, d in data["strategies"].items()}
    if args.output == "json":
        out.write(to_json(data))
        return
    if args.output == "csv":
        out.write(experiment_csv(data))
        return
    out.write(_describe(config) + "\n")
    out.write(f"{args.replications} replications per strategy (seeds {data['seeds'][0]}-{data['seeds'][-1]}); "
              "values are mean ±95% CI.\n\n")
    headers = ["Strategy"] + [h for _, h, _ in TABLE_METRICS]
    out.write(render_table(headers, _strategy_rows(summaries)) + "\n")
    if len(summaries) >= 2:
        names = list(summaries)
        base = "walk-left" if "walk-left" in summaries else names[0]
        out.write("\n")
        for name in names:
            if name == base:
                continue
            a, b = summaries[name], summaries[base]
            out.write(f"{name} vs {base}: throughput "
                      f"{_relative(a['throughput_per_min']['mean'], b['throughput_per_min']['mean'])}, "
                      f"average wait {_relative(a['wait_mean']['mean'], b['wait_mean']['mean'])}\n")


def _parse_values(param: str, text: str) -> list[Any]:
    typ = SimConfig.field_types()[param]
    try:
        values = [float(v) for v in text.split(",") if v.strip()]
    except ValueError:
        raise SystemExit(f"error: --values must be numbers, got {text!r}")
    if typ is int:
        bad = [v for v in values if v != int(v)]
        if bad:
            raise SystemExit(f"error: {param} must be a whole number, got {bad[0]:g}")
        return [int(v) for v in values]
    return values


def cmd_sweep(args, out) -> None:
    config = config_from_args(args)
    values = _parse_values(args.param, args.values)
    data = sweep(config, args.param, values, args.strategies, args.replications,
                 args.seed, _map_fn(args.jobs))
    if args.output == "json":
        out.write(to_json(data))
        return
    if args.output == "csv":
        out.write(experiment_csv(data))
        return

    out.write(_describe(config) + "\n")
    out.write(f"Sweeping {args.param}; {args.replications} replications per point; "
              "mean ±95% CI.\n\n")
    strategies = args.strategies
    headers = [args.param]
    headers += [f"{s} thru/min" for s in strategies]
    headers += [f"{s} wait s" for s in strategies]
    headers += ["Most throughput"]
    rows = []
    for point in data["points"]:
        sums = {s: point["strategies"][s]["summary"] for s in strategies}
        row = [f"{point['value']:g}"]
        row += [_fmt(sums[s]["throughput_per_min"]["mean"], "{:.1f}", sums[s]["throughput_per_min"]["ci95"])
                for s in strategies]
        row += [_fmt(sums[s]["wait_mean"]["mean"], "{:.1f}", sums[s]["wait_mean"]["ci95"]) for s in strategies]
        row.append(winner({s: sums[s]["throughput_per_min"] for s in strategies}))
        rows.append(row)
    out.write(render_table(headers, rows) + "\n")


def cmd_strategies(args, out) -> None:
    for name, desc in available_strategies().items():
        out.write(f"{name}\n    {desc}\n")


def main(argv: Optional[Sequence[str]] = None, out=None) -> int:
    out = out or sys.stdout
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "replications", 1) < 1:
        parser.error("--replications must be >= 1")
    try:
        {"run": cmd_run, "compare": cmd_compare, "sweep": cmd_sweep,
         "strategies": cmd_strategies}[args.command](args, out)
    except ValueError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
