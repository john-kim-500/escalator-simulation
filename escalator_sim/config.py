"""Simulation parameters.

All parameters live in one flat, frozen dataclass so they map one-to-one onto
command-line flags, sweep parameters and (later) web sliders.
Distances are metres measured along the incline, times are seconds, speeds are m/s.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, fields, replace
from typing import Any


@dataclass(frozen=True)
class SimConfig:
    # --- Escalator ---
    rise: float = 15.0             # vertical rise (m)
    incline_deg: float = 30.0      # incline angle (degrees); length = rise / sin(angle)
    belt_speed: float = 0.75       # step speed (m/s)
    step_depth: float = 0.4        # depth of one step (m); used for display only
    lanes: int = 2                 # lane 0 is the left lane

    # --- Crowd ---
    arrival_rate: float = 120.0    # people per minute (Poisson)
    walk_fraction: float = 0.25    # share of people who *want* to walk
    walk_speed_mean: float = 0.7   # preferred walking speed relative to the belt (m/s)
    walk_speed_sd: float = 0.15
    walk_speed_min: float = 0.2    # walking speeds below this are raised to it

    # --- Spacing and boarding ---
    stand_gap: float = 0.8         # min distance to person ahead when standing (m)
    walk_gap: float = 1.2          # min distance to person ahead when walking (m)
    board_headway: float = 0.5     # min time between boardings in one lane (s)

    # --- Behaviour (walk-left strategy) ---
    defect_threshold: int = 10     # queue difference that tempts a stander to walk
    defect_prob: float = 0.3       # chance a tempted stander walks in the walk lane
    blocker_rate: float = 0.0      # share of standers who stand in the walk lane

    # --- Run control ---
    duration: float = 600.0        # simulated seconds
    warmup: float = 120.0          # seconds excluded from metrics
    dt: float = 0.1                # time step (s)

    def __post_init__(self) -> None:
        self.validate()

    @property
    def length(self) -> float:
        """Length of the escalator along the incline (m)."""
        return self.rise / math.sin(math.radians(self.incline_deg))

    def validate(self) -> None:
        checks = [
            (self.rise > 0, "rise must be > 0"),
            (0 < self.incline_deg < 90, "incline_deg must be between 0 and 90"),
            (self.belt_speed > 0, "belt_speed must be > 0"),
            (self.step_depth > 0, "step_depth must be > 0"),
            (self.lanes >= 1, "lanes must be >= 1"),
            (self.arrival_rate >= 0, "arrival_rate must be >= 0"),
            (0 <= self.walk_fraction <= 1, "walk_fraction must be in [0, 1]"),
            (self.walk_speed_mean >= 0, "walk_speed_mean must be >= 0"),
            (self.walk_speed_sd >= 0, "walk_speed_sd must be >= 0"),
            (self.walk_speed_min >= 0, "walk_speed_min must be >= 0"),
            (self.stand_gap > 0, "stand_gap must be > 0"),
            (self.walk_gap > 0, "walk_gap must be > 0"),
            (self.board_headway >= 0, "board_headway must be >= 0"),
            (self.defect_threshold >= 0, "defect_threshold must be >= 0"),
            (0 <= self.defect_prob <= 1, "defect_prob must be in [0, 1]"),
            (0 <= self.blocker_rate <= 1, "blocker_rate must be in [0, 1]"),
            (self.duration > 0, "duration must be > 0"),
            (0 <= self.warmup < self.duration, "warmup must be in [0, duration)"),
            (0 < self.dt <= 1, "dt must be in (0, 1]"),
        ]
        errors = [msg for ok, msg in checks if not ok]
        if errors:
            raise ValueError("; ".join(errors))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SimConfig":
        names = cls.field_names()
        unknown = set(data) - set(names)
        if unknown:
            raise ValueError(f"unknown parameter(s): {', '.join(sorted(unknown))}")
        types = cls.field_types()
        converted = {}
        for key, value in data.items():
            if types[key] is int and float(value) != int(float(value)):
                raise ValueError(f"{key} must be a whole number, got {value!r}")
            converted[key] = types[key](float(value)) if types[key] is int else types[key](value)
        return cls(**converted)

    def with_changes(self, **changes: Any) -> "SimConfig":
        return self.from_dict({**self.to_dict(), **changes})

    @classmethod
    def field_names(cls) -> list[str]:
        return [f.name for f in fields(cls)]

    @classmethod
    def field_types(cls) -> dict[str, type]:
        """Python type of each parameter (taken from its default value)."""
        defaults = cls.__dataclass_fields__
        return {name: type(defaults[name].default) for name in cls.field_names()}
