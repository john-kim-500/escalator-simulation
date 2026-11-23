"""Simulation parameters.

All parameters live in one flat, frozen dataclass so they map one-to-one onto
command-line flags, sweep parameters and web controls. `PARAM_INFO` describes
each parameter (label, unit, range, help) for both the CLI help and the GUI.
Distances are meters measured along the incline, times are seconds, speeds are m/s.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, fields
from typing import Any


@dataclass(frozen=True)
class SimConfig:
    # --- Escalator ---
    rise: float = 15.0
    incline_deg: float = 30.0
    belt_speed: float = 0.75
    step_depth: float = 0.4
    lanes: int = 2

    # --- Crowd ---
    arrival_rate: float = 120.0
    walk_fraction: float = 0.25
    walk_speed_mean: float = 0.7
    walk_speed_sd: float = 0.15
    walk_speed_min: float = 0.2

    # --- Spacing and boarding ---
    stand_gap: float = 0.8
    walk_gap: float = 0.9
    board_headway: float = 0.5

    # --- Behavior (walk-left strategy) ---
    defect_threshold: int = 10
    defect_prob: float = 0.3
    blocker_rate: float = 0.0

    # --- Run control ---
    duration: float = 600.0
    warmup: float = 120.0
    dt: float = 0.1
    drain: int = 1          # finish everyone measured after the run ends; 0 = stop at duration

    def __post_init__(self) -> None:
        self.validate()

    @property
    def length(self) -> float:
        """Length of the escalator along the incline (m)."""
        return self.rise / math.sin(math.radians(self.incline_deg))

    # ------------------------------------------------------------ checking

    def validate(self) -> None:
        errors = check_values(self.to_dict())
        if errors:
            raise ValueError("; ".join(msg for _, msg in errors))

    def warnings(self) -> list[tuple[str, str]]:
        """Valid but questionable settings, as (field, message) pairs."""
        out = []
        ride = self.length / self.belt_speed
        if self.warmup < ride:
            out.append(("warmup", f"warm-up ({self.warmup:g} s) is shorter than one standing ride "
                                  f"({ride:.0f} s), so throughput is underestimated"))
        if self.duration - self.warmup < 2 * ride:
            measured = self.duration - self.warmup
            out.append(("duration", f"only {measured:g} s are measured, less than "
                                    f"two rides ({2 * ride:.0f} s); results will be noisy"))
        return out

    def derived(self) -> dict[str, float]:
        """Values calculated from the settings, for display."""
        headway_cap = 60.0 / self.board_headway if self.board_headway > 0 else math.inf
        return {
            "length": self.length,
            "ride_time": self.length / self.belt_speed,
            "stand_lane_capacity": min(self.belt_speed / self.stand_gap * 60.0, headway_cap),
            # Upper bound: assumes everyone walks at the average speed.
            "walk_lane_capacity": min(
                (self.belt_speed + self.walk_speed_mean) / self.walk_gap * 60.0, headway_cap),
        }

    # ---------------------------------------------------------- conversion

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SimConfig:
        values, errors = convert_values(data)
        if errors:
            raise ValueError("; ".join(msg for _, msg in errors))
        return cls(**values)

    def with_changes(self, **changes: Any) -> SimConfig:
        return self.from_dict({**self.to_dict(), **changes})

    @classmethod
    def field_names(cls) -> list[str]:
        return [f.name for f in fields(cls)]

    @classmethod
    def field_types(cls) -> dict[str, type]:
        """Python type of each parameter (taken from its default value)."""
        defaults = cls.__dataclass_fields__
        return {name: type(defaults[name].default) for name in cls.field_names()}


def convert_values(data: dict[str, Any]) -> tuple[dict[str, Any], list[tuple[str, str]]]:
    """Convert raw values (e.g. from a form) to the right types.

    Returns (converted values, [(field, message), ...]). Unknown names are errors.
    """
    types = SimConfig.field_types()
    values: dict[str, Any] = {}
    errors: list[tuple[str, str]] = []
    for key, raw in data.items():
        if key not in types:
            errors.append((key, f"unknown parameter: {key}"))
            continue
        try:
            number = float(raw)
        except (TypeError, ValueError):
            errors.append((key, f"{key} must be a number, got {raw!r}"))
            continue
        if not math.isfinite(number):
            errors.append((key, f"{key} must be a finite number"))
        elif types[key] is int:
            if number != int(number):
                errors.append((key, f"{key} must be a whole number, got {raw!r}"))
            else:
                values[key] = int(number)
        else:
            values[key] = number
    return values, errors


def check_values(v: dict[str, Any]) -> list[tuple[str, str]]:
    """Validation rules, as (field, message) pairs for every broken rule."""
    rules = [
        ("rise", v["rise"] > 0, "rise must be > 0"),
        ("incline_deg", 0 < v["incline_deg"] < 90, "incline_deg must be between 0 and 90"),
        ("belt_speed", v["belt_speed"] > 0, "belt_speed must be > 0"),
        ("step_depth", v["step_depth"] > 0, "step_depth must be > 0"),
        ("lanes", v["lanes"] >= 1, "lanes must be >= 1"),
        ("arrival_rate", v["arrival_rate"] >= 0, "arrival_rate must be >= 0"),
        ("walk_fraction", 0 <= v["walk_fraction"] <= 1, "walk_fraction must be in [0, 1]"),
        ("walk_speed_mean", v["walk_speed_mean"] >= 0, "walk_speed_mean must be >= 0"),
        ("walk_speed_sd", v["walk_speed_sd"] >= 0, "walk_speed_sd must be >= 0"),
        ("walk_speed_min", v["walk_speed_min"] >= 0, "walk_speed_min must be >= 0"),
        ("stand_gap", v["stand_gap"] > 0, "stand_gap must be > 0"),
        ("walk_gap", v["walk_gap"] > 0, "walk_gap must be > 0"),
        ("board_headway", v["board_headway"] >= 0, "board_headway must be >= 0"),
        ("defect_threshold", v["defect_threshold"] >= 0, "defect_threshold must be >= 0"),
        ("defect_prob", 0 <= v["defect_prob"] <= 1, "defect_prob must be in [0, 1]"),
        ("blocker_rate", 0 <= v["blocker_rate"] <= 1, "blocker_rate must be in [0, 1]"),
        ("duration", v["duration"] > 0, "duration must be > 0"),
        ("warmup", 0 <= v["warmup"] < v["duration"], "warmup must be in [0, duration)"),
        ("dt", 0 < v["dt"] <= 1, "dt must be in (0, 1]"),
        ("drain", v["drain"] in (0, 1), "drain must be 0 or 1"),
    ]
    return [(name, msg) for name, ok, msg in rules if not ok]


# --------------------------------------------------------------------------
# Parameter details for help text and GUI controls. min/max/step are the
# ranges offered by sliders, not validation limits (see check_values).

GROUPS = {
    "escalator": "Escalator",
    "crowd": "Crowd",
    "spacing": "Spacing and boarding",
    "behaviour": "Behavior (walk-left)",
    "run": "Run control",
}


def _p(
    group: str, label: str, unit: str, lo: float, hi: float, step: float, help: str,
    only_for: list[str] | None = None,
) -> dict[str, Any]:
    return {"group": group, "label": label, "unit": unit, "min": lo, "max": hi,
            "step": step, "help": help, "only_for": only_for}


PARAM_INFO: dict[str, dict[str, Any]] = {
    "rise": _p("escalator", "Rise", "m", 2, 60, 0.5,
               "Vertical height climbed. Length along the incline = rise / sin(incline)."),
    "incline_deg": _p("escalator", "Incline", "°", 20, 40, 1, "Angle of the escalator."),
    "belt_speed": _p("escalator", "Belt speed", "m/s", 0.3, 1.0, 0.05, "Speed of the steps."),
    "step_depth": _p("escalator", "Step depth", "m", 0.3, 0.5, 0.01,
                     "Depth of one step. Only used for drawing."),
    "lanes": _p("escalator", "Lanes", "", 1, 4, 1,
                "Number of lanes. Lane 0 is the left (walk) lane; walk-left needs 2+."),
    "arrival_rate": _p("crowd", "Arrival rate", "people/min", 0, 300, 5,
                       "Average arrivals per minute, at random (Poisson) intervals."),
    "walk_fraction": _p("crowd", "Want to walk", "share", 0, 1, 0.05,
                        "Share of people who would walk if they could."),
    "walk_speed_mean": _p("crowd", "Walking speed", "m/s", 0, 1.5, 0.05,
                          "Average walking speed on top of the belt speed."),
    "walk_speed_sd": _p("crowd", "Walking speed spread", "m/s", 0, 0.5, 0.01,
                        "Standard deviation of walking speed between people."),
    "walk_speed_min": _p("crowd", "Slowest walker", "m/s", 0, 1, 0.05,
                         "Walking speeds below this are raised to it."),
    "stand_gap": _p("spacing", "Standing gap", "m", 0.3, 2, 0.05,
                    "Closest a stander gets to the person ahead (0.8 m ≈ one empty step)."),
    "walk_gap": _p("spacing", "Walking gap", "m", 0.3, 3, 0.05,
                   "Closest a walker gets to the person ahead (0.9 m fits measured London flows; "
                   "see tests/test_calibration.py)."),
    "board_headway": _p("spacing", "Boarding interval", "s", 0, 3, 0.1,
                        "Minimum time between two people stepping onto the same lane."),
    "defect_threshold": _p("behaviour", "Switch threshold", "people", 0, 50, 1,
                           "How much longer the right queue must be before standers are "
                           "tempted to walk.",
                           only_for=["walk-left"]),
    "defect_prob": _p("behaviour", "Switch chance", "share", 0, 1, 0.05,
                      "Chance a tempted stander walks in the left lane instead.",
                      only_for=["walk-left"]),
    "blocker_rate": _p("behaviour", "Blockers", "share", 0, 1, 0.01,
                       "Share of standers who stand in the walk lane.", only_for=["walk-left"]),
    "duration": _p("run", "Duration", "s", 60, 3600, 30, "Simulated time."),
    "warmup": _p("run", "Warm-up", "s", 0, 1200, 10,
                 "Time at the start left out of the results. Should exceed one ride."),
    "dt": _p("run", "Time step", "s", 0.02, 0.5, 0.01,
             "Simulation step. Smaller is slightly more precise and slower."),
    "drain": _p("run", "Finish the line", "", 0, 1, 1,
                "1 = after the run ends, stop arrivals and keep going until everyone "
                "measured reaches the top, so waits and trip times are complete. People "
                "per minute and line length still stop at the end. 0 = stop at the end."),
}


PRESETS: dict[str, dict[str, Any]] = {
    "defaults": {"label": "Defaults", "description": "The built-in default settings.",
                 "values": {}},
    "rush-hour": {"label": "Rush hour",
                  "description": "More arrivals than two standing lanes can carry.",
                  "values": {"arrival_rate": 150}},
    "off-peak": {"label": "Off-peak",
                 "description": "Light traffic: both strategies carry everyone.",
                 "values": {"arrival_rate": 40}},
    "tall": {"label": "Tall escalator (24 m rise)",
             "description": "Like Holborn: about 45% walk at rush hour (Davis & Dutta 2002).",
             "values": {"rise": 24, "walk_fraction": 0.45, "warmup": 180, "duration": 900}},
    "no-switching": {"label": "Nobody switches lanes",
                     "description": "Standers never walk or block the walk lane.",
                     "values": {"defect_prob": 0, "blocker_rate": 0}},
}
