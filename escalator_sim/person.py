"""A single person moving through the system."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config import SimConfig


@dataclass(slots=True)
class Person:
    id: int
    arrival_time: float
    wants_to_walk: bool
    walk_speed: float               # preferred walking speed relative to the belt (m/s)
    lane: int = -1                  # set by the strategy on arrival
    walking: bool = False           # whether they actually walk on the escalator
    kind: str = ""                  # stander/walker/defector/blocker, set by the strategy
    pos: float = 0.0                # distance from the bottom along the incline (m)
    speed: float = 0.0              # ground speed during the last step (m/s)
    board_time: float | None = None
    exit_time: float | None = None

    def gap(self, config: SimConfig) -> float:
        """Minimum distance this person keeps to the person ahead."""
        return config.walk_gap if self.walking else config.stand_gap

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "lane": self.lane,
            "pos": self.pos,
            "speed": self.speed,
            "walking": self.walking,
            "wants_to_walk": self.wants_to_walk,
            "kind": self.kind,
        }
