"""Lane-choice strategies.

A strategy decides, when a person arrives, which lane's queue they join and
whether they will walk once on the escalator. New strategies subclass
`Strategy` and are added with `@register`.
"""
from __future__ import annotations

import random
from typing import Sequence

from .config import SimConfig
from .person import Person

WALK_LANE = 0  # the left lane


class Strategy:
    name: str = ""
    description: str = ""

    def __init__(self, config: SimConfig) -> None:
        self.config = config
        self.validate()

    def validate(self) -> None:
        """Raise ValueError if the strategy cannot run with this config."""

    def choose(
        self, person: Person, queue_lengths: Sequence[int], rng: random.Random
    ) -> tuple[int, bool]:
        """Return (lane, walking) for a newly arrived person."""
        raise NotImplementedError


_REGISTRY: dict[str, type[Strategy]] = {}


def register(cls: type[Strategy]) -> type[Strategy]:
    _REGISTRY[cls.name] = cls
    return cls


def available_strategies() -> dict[str, str]:
    """Map of strategy name to description."""
    return {name: cls.description for name, cls in _REGISTRY.items()}


def get_strategy(name: str, config: SimConfig) -> Strategy:
    try:
        cls = _REGISTRY[name]
    except KeyError:
        raise ValueError(
            f"unknown strategy {name!r}; choose from {', '.join(_REGISTRY)}"
        ) from None
    return cls(config)


def _shortest(lanes: Sequence[int], queue_lengths: Sequence[int], rng: random.Random) -> int:
    best = min(queue_lengths[i] for i in lanes)
    return rng.choice([i for i in lanes if queue_lengths[i] == best])


@register
class StandBoth(Strategy):
    name = "stand-both"
    description = "Everyone stands in every lane and joins the shortest queue."

    def choose(self, person, queue_lengths, rng):
        return _shortest(range(len(queue_lengths)), queue_lengths, rng), False


@register
class WalkLeft(Strategy):
    name = "walk-left"
    description = (
        "Stand on the right, walk on the left. Some standers walk in the left "
        "lane when the right queue is long (defect_*); some stand in it (blocker_rate)."
    )

    def validate(self):
        if self.config.lanes < 2:
            raise ValueError("walk-left needs at least 2 lanes")

    def choose(self, person, queue_lengths, rng):
        cfg = self.config
        if person.wants_to_walk:
            return WALK_LANE, True
        if rng.random() < cfg.blocker_rate:
            return WALK_LANE, False
        lane = _shortest(range(1, len(queue_lengths)), queue_lengths, rng)
        tempted = queue_lengths[lane] - queue_lengths[WALK_LANE] >= cfg.defect_threshold
        if tempted and rng.random() < cfg.defect_prob:
            return WALK_LANE, True
        return lane, False
