"""Time-stepped, agent-based escalator simulation.

The engine does no I/O, uses no threads and never sleeps. The caller drives it
by calling `step()` and reads state through `snapshot()` and `results()`. Both
return plain data that can be turned into JSON, so the same engine runs from the
command line or in the browser through Pyodide.

Movement model (one track per lane, positions measured from the bottom):
  * A person's speed is belt_speed plus their walking speed (0 when standing).
  * Nobody gets closer to the person ahead than their own gap
    (stand_gap or walk_gap), and nobody moves slower than the belt.
  * A person at the front of a lane's queue boards once the last person on that
    lane is one gap up and board_headway has passed since the last boarding.
    Boarding times are worked out within a step, so lane capacity does not
    depend on dt.
"""
from __future__ import annotations

import math
import random
from collections import deque
from typing import Any

from . import draws
from .config import SimConfig
from .metrics import summarize
from .person import Person
from .strategies import get_strategy

_EPS = 1e-9


class Simulation:
    def __init__(
        self,
        config: SimConfig | None = None,
        strategy: str = "walk-left",
        seed: int | None = 0,
    ) -> None:
        self.config = config or SimConfig()
        self.strategy = get_strategy(strategy, self.config)
        if seed is None:
            seed = random.randrange(2**32)
        self.seed = seed
        # Arrival draws are keyed apart from strategy draws, so the same seed
        # gives the same crowd under every strategy (a like-for-like comparison).
        self._draws = draws.Draws(seed)

        lanes = self.config.lanes
        self.length = self.config.length
        self.steps = 0
        self.time = 0.0
        self.people: list[Person] = []
        self.queues: list[deque[Person]] = [deque() for _ in range(lanes)]
        self.on_belt: list[list[Person]] = [[] for _ in range(lanes)]  # top first
        self.finished: list[Person] = []
        self._last_board = [-math.inf] * lanes
        self.queue_end: int | None = None  # line length at `duration`, saved by drain()
        self._next_arrival = self._draw_interarrival(0.0)

        # Queue statistics, sampled at the end of each step after warm-up.
        self.queue_samples = 0
        self.queue_sum = 0
        self.queue_max = 0
        self.lane_queue_max = [0] * lanes

        # Running counts for live_stats(), so a GUI can poll it every frame.
        self._recent_exits: deque[float] = deque()   # exit times in the last window
        self._boarded = 0
        self._wait_sum = 0.0
        self._walked = 0

    # ------------------------------------------------------------------ API

    @property
    def done(self) -> bool:
        return self.time >= self.config.duration - _EPS

    def step(self) -> None:
        """Advance the simulation by one time step (config.dt)."""
        cfg = self.config
        t0 = self.time
        t1 = (self.steps + 1) * cfg.dt
        self._arrive(t1)
        for lane in range(cfg.lanes):
            self._move_lane(lane, t1, t1 - t0)
            self._board_lane(lane, t0, t1)
        self.steps += 1
        self.time = t1
        self._sample_queues()

    def run(self, until: float | None = None) -> dict[str, Any]:
        """Step until `until` seconds (default: config.duration); return results().

        A full run (no `until`) also calls drain() when config.drain is 1.
        """
        target = self.config.duration if until is None else until
        while self.time < target - _EPS:
            self.step()
        if until is None and self.config.drain:
            self.drain()
        return self.results()

    @property
    def drained(self) -> bool:
        return self.queue_end is not None

    def drain(self) -> None:
        """Stop arrivals and step until everyone who arrived after warm-up is at the top.

        Has no cap: an overloaded run takes as long as clearing its line does.
        This doesn't change anyone's trip: lines are first come, first served
        and nobody overtakes, so people arriving later never affect earlier ones.
        """
        if self.drained:
            return
        self.run(until=self.config.duration)
        self.queue_end = sum(len(q) for q in self.queues)
        self._next_arrival = math.inf
        start = self.config.warmup
        waiting = [p for p in self.people if p.arrival_time >= start and p.exit_time is None]
        for p in waiting:  # stops once the last of them is at the top
            while p.exit_time is None:
                self.step()

    def snapshot(self, max_queue: int | None = None) -> dict[str, Any]:
        """Current state as plain data (for visual front ends).

        `max_queue` limits how many queueing people are listed per lane (the
        front of the queue); `queue_length` always gives the full count.
        """
        def queue_people(q: deque[Person]) -> list[dict[str, Any]]:
            shown = q if max_queue is None else list(q)[:max_queue]
            return [p.to_dict() for p in shown]

        return {
            "time": self.time,
            "length": self.length,
            "belt_speed": self.config.belt_speed,
            "step_depth": self.config.step_depth,
            "strategy": self.strategy.name,
            "arrived": len(self.people),
            "finished": len(self.finished),
            "lanes": [
                {
                    "index": i,
                    "people": [p.to_dict() for p in self.on_belt[i]],
                    "queue": queue_people(self.queues[i]),
                    "queue_length": len(self.queues[i]),
                }
                for i in range(self.config.lanes)
            ],
        }

    LIVE_WINDOW = 60.0  # seconds used for live throughput

    def live_stats(self) -> dict[str, Any]:
        """Cheap running statistics (no warm-up exclusion) for live displays."""
        window = min(self.LIVE_WINDOW, self.time)
        return {
            "time": self.time,
            "arrived": len(self.people),
            "finished": len(self.finished),
            "throughput_recent": len(self._recent_exits) / window * 60.0 if window > 0 else 0.0,
            "queue_lengths": [len(q) for q in self.queues],
            "on_belt": [len(lane) for lane in self.on_belt],
            "wait_mean": self._wait_sum / self._boarded if self._boarded else None,
            "walked_share": self._walked / len(self.finished) if self.finished else None,
        }

    def results(self) -> dict[str, Any]:
        """Summary metrics for the run so far (excluding warm-up)."""
        return summarize(self)

    # ------------------------------------------------------------ internals

    def _draw_interarrival(self, after: float) -> float:
        rate = self.config.arrival_rate / 60.0
        if rate <= 0:
            return math.inf
        return after + self._draws.exponential(draws.ARRIVAL_GAP, len(self.people), rate)

    def _arrive(self, t1: float) -> None:
        cfg = self.config
        d = self._draws
        while self._next_arrival <= t1:
            n = len(self.people)
            wants = d.uniform(draws.WANTS_TO_WALK, n) < cfg.walk_fraction
            speed = d.normal(draws.WALK_SPEED, n, cfg.walk_speed_mean, cfg.walk_speed_sd)
            person = Person(n, self._next_arrival, wants, max(cfg.walk_speed_min, speed))
            lane, walking = self.strategy.choose(person, [len(q) for q in self.queues], d)
            person.lane, person.walking = lane, walking
            person.kind = self.strategy.kind(person)
            self.people.append(person)
            self.queues[lane].append(person)
            self._next_arrival = self._draw_interarrival(self._next_arrival)

    def _move_lane(self, lane: int, t1: float, dt: float) -> None:
        cfg = self.config
        belt = cfg.belt_speed
        people = self.on_belt[lane]
        limit = math.inf  # new position of the person ahead
        for p in people:
            desired = p.pos + (belt + (p.walk_speed if p.walking else 0.0)) * dt
            new = min(desired, limit - p.gap(cfg))
            new = max(new, p.pos + belt * dt)  # the belt always carries you
            p.speed = (new - p.pos) / dt
            p.pos = new
            limit = new
        while people and people[0].pos >= self.length:
            p = people.pop(0)
            p.exit_time = t1 - (p.pos - self.length) / p.speed
            p.pos = self.length
            self.finished.append(p)
            self._recent_exits.append(p.exit_time)
            self._walked += p.walking
        cutoff = t1 - self.LIVE_WINDOW
        while self._recent_exits and self._recent_exits[0] <= cutoff:
            self._recent_exits.popleft()

    def _board_lane(self, lane: int, t0: float, t1: float) -> None:
        cfg = self.config
        queue = self.queues[lane]
        people = self.on_belt[lane]
        while queue:
            p = queue[0]
            gap = p.gap(cfg)
            earliest = max(t0, p.arrival_time, self._last_board[lane] + cfg.board_headway)
            if people:
                last = people[-1]
                if last.pos < gap - _EPS:
                    break
                # When the last person was exactly one gap up.
                earliest = max(earliest, t1 - (last.pos - gap) / last.speed)
            if earliest > t1 + _EPS:
                break
            earliest = min(earliest, t1)
            pos = cfg.belt_speed * (t1 - earliest)
            if people:
                pos = min(pos, people[-1].pos - gap)
            queue.popleft()
            p.pos = max(pos, 0.0)
            p.speed = cfg.belt_speed
            p.board_time = earliest
            people.append(p)
            self._last_board[lane] = earliest
            self._boarded += 1
            self._wait_sum += earliest - p.arrival_time

    def _sample_queues(self) -> None:
        if not self.config.warmup - _EPS <= self.time <= self.config.duration + _EPS:
            return
        lengths = [len(q) for q in self.queues]
        total = sum(lengths)
        self.queue_samples += 1
        self.queue_sum += total
        self.queue_max = max(self.queue_max, total)
        self.lane_queue_max = [max(a, b) for a, b in zip(self.lane_queue_max, lengths)]
