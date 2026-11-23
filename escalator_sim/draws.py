"""Random numbers keyed by (seed, purpose, person number).

Each number is a hash of its key, not the next value in a sequence. So adding
a new kind of draw (a new purpose) leaves every existing draw unchanged, and
the results don't depend on which Python version runs them: the conversions
below are written here rather than taken from `random`, whose methods other
than `random()` may change between versions.

Never rename a purpose or change how one is keyed: that changes the crowd for
every seed. Add a new purpose instead.
"""
from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from typing import TypeVar

# Arrivals: who comes, when, and how they'd like to travel.
ARRIVAL_GAP = "arrival_gap"
WANTS_TO_WALK = "wants_to_walk"
WALK_SPEED = "walk_speed"
# Behavior: choices the strategy makes.
TIE_BREAK = "tie_break"
BLOCKER = "blocker"
DEFECT = "defect"

_T = TypeVar("_T")
_SCALE = 2.0 ** -53


class Draws:
    """All random numbers for one simulation run."""

    def __init__(self, seed: int) -> None:
        self.seed = seed

    def uniform(self, purpose: str, index: int) -> float:
        """A number in [0, 1), with 53 bits of precision like `random()`."""
        key = f"{self.seed}:{purpose}:{index}".encode()
        digest = hashlib.blake2b(key, digest_size=8).digest()
        return (int.from_bytes(digest, "big") >> 11) * _SCALE

    def exponential(self, purpose: str, index: int, rate: float) -> float:
        """A random gap whose average is 1 / rate."""
        return -math.log(1.0 - self.uniform(purpose, index)) / rate

    def normal(self, purpose: str, index: int, mean: float, sd: float) -> float:
        """A bell-curve value (Box-Muller, from two keyed uniforms)."""
        u1 = self.uniform(purpose + ".1", index)
        u2 = self.uniform(purpose + ".2", index)
        z = math.sqrt(-2.0 * math.log(1.0 - u1)) * math.cos(2.0 * math.pi * u2)
        return mean + sd * z

    def choice(self, purpose: str, index: int, options: Sequence[_T]) -> _T:
        """One of `options`, each equally likely."""
        n = len(options)
        return options[min(int(self.uniform(purpose, index) * n), n - 1)]
