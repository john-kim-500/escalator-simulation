"""Lane-choice strategies.

A strategy decides, when a person arrives, which lane's queue they join and
whether they will walk once on the escalator. New strategies subclass
`Strategy` and are added with `@register`.
"""
from __future__ import annotations

from collections.abc import Sequence

from . import draws as _draws
from .config import SimConfig
from .person import Person

WALK_LANE = 0  # the left lane


KINDS = {
    "stander": "Standing",
    "walker": "Walking",
    "defector": "Stander who switched to walking",
    "blocker": "Standing in the walk lane",
}


class Strategy:
    name: str = ""
    description: str = ""

    def __init__(self, config: SimConfig) -> None:
        self.config = config
        self.validate()

    def validate(self) -> None:
        """Raise ValueError if the strategy cannot run with this config."""

    def choose(
        self, person: Person, queue_lengths: Sequence[int], draws: _draws.Draws
    ) -> tuple[int, bool]:
        """Return (lane, walking) for a newly arrived person.

        Random choices come from `draws`, keyed by `person.id` and a purpose
        from `draws.py`, so each strategy's choices don't disturb the crowd.
        """
        raise NotImplementedError

    def kind(self, person: Person) -> str:
        """Label for display, once lane and walking are set."""
        return "walker" if person.walking else "stander"


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


def _shortest(lanes: Sequence[int], queue_lengths: Sequence[int], draws: _draws.Draws,
              person: Person) -> int:
    best = min(queue_lengths[i] for i in lanes)
    tied = [i for i in lanes if queue_lengths[i] == best]
    return draws.choice(_draws.TIE_BREAK, person.id, tied)


@register
class StandBoth(Strategy):
    name = "stand-both"
    description = "Everyone stands in every lane and joins the shortest queue."

    def choose(
        self, person: Person, queue_lengths: Sequence[int], draws: _draws.Draws
    ) -> tuple[int, bool]:
        return _shortest(range(len(queue_lengths)), queue_lengths, draws, person), False


@register
class WalkLeft(Strategy):
    name = "walk-left"
    description = (
        "Stand on the right, walk on the left. Some standers walk in the left "
        "lane when the right queue is long (defect_*); some stand in it (blocker_rate)."
    )

    def validate(self) -> None:
        if self.config.lanes < 2:
            raise ValueError("walk-left needs at least 2 lanes")

    def choose(
        self, person: Person, queue_lengths: Sequence[int], draws: _draws.Draws
    ) -> tuple[int, bool]:
        cfg = self.config
        if person.wants_to_walk:
            return WALK_LANE, True
        if draws.uniform(_draws.BLOCKER, person.id) < cfg.blocker_rate:
            return WALK_LANE, False
        lane = _shortest(range(1, len(queue_lengths)), queue_lengths, draws, person)
        tempted = queue_lengths[lane] - queue_lengths[WALK_LANE] >= cfg.defect_threshold
        if tempted and draws.uniform(_draws.DEFECT, person.id) < cfg.defect_prob:
            return WALK_LANE, True
        return lane, False

    def kind(self, person: Person) -> str:
        if person.walking and not person.wants_to_walk:
            return "defector"   # a stander who switched to walking
        if person.lane == WALK_LANE and not person.walking:
            return "blocker"    # standing in the walk lane
        return super().kind(person)
