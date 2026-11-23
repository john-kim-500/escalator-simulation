import io
import json
import unittest

from escalator_sim import SimConfig, Simulation, compare, sweep
from escalator_sim.cli import main
from escalator_sim.draws import Draws
from escalator_sim.metrics import mean_ci, percentile
from escalator_sim.report import time_winner
from escalator_sim.strategies import WalkLeft

SHORT = dict(duration=180.0, warmup=60.0)  # warm-up must exceed the 40 s ride


def stepped(sim, check):
    """Run sim to completion, calling check(sim) after every step."""
    while not sim.done:
        sim.step()
        check(sim)


class SpacingAndMovement(unittest.TestCase):
    def test_gaps_respected_and_nobody_slower_than_belt(self):
        cfg = SimConfig(walk_fraction=0.5, arrival_rate=150, blocker_rate=0.1, **SHORT)
        sim = Simulation(cfg, "walk-left", seed=3)
        last_pos = {}

        def check(s):
            for lane in s.on_belt:
                for ahead, behind in zip(lane, lane[1:]):
                    self.assertGreaterEqual(ahead.pos - behind.pos, behind.gap(cfg) - 1e-6)
                for p in lane:
                    if p.id in last_pos:
                        moved = p.pos - last_pos[p.id]
                        self.assertGreaterEqual(moved, cfg.belt_speed * cfg.dt - 1e-9)
                    last_pos[p.id] = p.pos

        stepped(sim, check)

    def test_single_stander_trip_time(self):
        cfg = SimConfig(arrival_rate=0, **SHORT)
        sim = Simulation(cfg, "stand-both")
        sim.queues[0].append(_person(sim, arrival=0.0))
        sim.run()
        p = sim.finished[0]
        self.assertAlmostEqual(p.exit_time - p.board_time, cfg.length / cfg.belt_speed, places=6)

    def test_walker_blocked_by_stander_moves_at_belt_speed(self):
        cfg = SimConfig(arrival_rate=0, **SHORT)
        sim = Simulation(cfg, "walk-left")
        stander = _person(sim, arrival=0.0)
        walker = _person(sim, arrival=0.0, walking=True)
        sim.queues[0].extend([stander, walker])
        sim.run()
        # The walker can't overtake, so they ride one gap behind at belt speed,
        # then cover that last gap at walking speed once the stander steps off.
        self.assertAlmostEqual(walker.exit_time - stander.exit_time,
                               cfg.walk_gap / (cfg.belt_speed + walker.walk_speed), delta=cfg.dt)


class Capacity(unittest.TestCase):
    def test_standing_lane_capacity_matches_theory(self):
        cfg = SimConfig(arrival_rate=400, **SHORT)
        r = Simulation(cfg, "stand-both", seed=1).run()
        expected = cfg.lanes * cfg.belt_speed / cfg.stand_gap * 60
        self.assertAlmostEqual(r["throughput_per_min"], expected, delta=expected * 0.02)

    def test_capacity_independent_of_dt(self):
        a = Simulation(SimConfig(arrival_rate=400, dt=0.05, **SHORT), "stand-both", 1).run()
        b = Simulation(SimConfig(arrival_rate=400, dt=0.25, **SHORT), "stand-both", 1).run()
        self.assertAlmostEqual(a["throughput_per_min"], b["throughput_per_min"], delta=1.5)

    def test_board_headway_limits_capacity(self):
        cfg = SimConfig(arrival_rate=400, board_headway=2.0, **SHORT)
        r = Simulation(cfg, "stand-both", seed=1).run()
        self.assertAlmostEqual(r["throughput_per_min"], cfg.lanes * 30, delta=1.0)

    def test_walk_left_without_walkers_uses_one_lane(self):
        cfg = SimConfig(walk_fraction=0, defect_prob=0, blocker_rate=0, **SHORT)
        r = Simulation(cfg, "walk-left", seed=1).run()
        self.assertEqual(r["throughput_by_lane"][0], 0)
        self.assertAlmostEqual(r["throughput_by_lane"][1], 56.25, delta=1.5)


class Strategies(unittest.TestCase):
    def test_stand_both_never_walks(self):
        sim = Simulation(SimConfig(walk_fraction=1.0, **SHORT), "stand-both", 2)
        sim.run()
        self.assertFalse(any(p.walking for p in sim.people))

    def test_walk_left_lane_assignment(self):
        cfg = SimConfig(defect_prob=0, blocker_rate=0, **SHORT)
        sim = Simulation(cfg, "walk-left", 2)
        sim.run()
        for p in sim.people:
            self.assertEqual(p.lane == 0, p.wants_to_walk)
            self.assertEqual(p.walking, p.wants_to_walk)

    def test_blockers_stand_in_walk_lane(self):
        cfg = SimConfig(blocker_rate=1.0, walk_fraction=0, **SHORT)
        sim = Simulation(cfg, "walk-left", 2)
        sim.run()
        self.assertTrue(all(p.lane == 0 and not p.walking for p in sim.people))

    def test_walk_left_needs_two_lanes(self):
        with self.assertRaises(ValueError):
            Simulation(SimConfig(lanes=1), "walk-left")

    def test_unknown_strategy(self):
        with self.assertRaises(ValueError):
            Simulation(SimConfig(), "nope")


class Reproducibility(unittest.TestCase):
    def test_same_seed_same_results(self):
        cfg = SimConfig(**SHORT)
        first, second = Simulation(cfg, "walk-left", 7).run(), Simulation(cfg, "walk-left", 7).run()
        self.assertEqual(first, second)

    def test_same_crowd_across_strategies(self):
        cfg = SimConfig(**SHORT)
        a, b = Simulation(cfg, "walk-left", 7), Simulation(cfg, "stand-both", 7)
        a.run(), b.run()
        def key(s):
            return [(p.arrival_time, p.wants_to_walk, p.walk_speed) for p in s.people]
        self.assertEqual(key(a), key(b))

    def test_new_draw_leaves_crowd_and_choices_unchanged(self):
        class ExtraDraw(WalkLeft):
            def choose(self, person, queue_lengths, draws):
                draws.uniform("test.extra", person.id)
                return super().choose(person, queue_lengths, draws)

        cfg = SimConfig(blocker_rate=0.1, **SHORT)
        plain = Simulation(cfg, "walk-left", 7)
        extra = Simulation(cfg, "walk-left", 7)
        extra.strategy = ExtraDraw(cfg)
        plain.run(), extra.run()
        def key(s):
            return [(p.arrival_time, p.wants_to_walk, p.walk_speed, p.lane, p.walking)
                    for p in s.people]
        self.assertEqual(key(plain), key(extra))

    def test_walk_fraction_keeps_arrival_times(self):
        def times(fraction):
            sim = Simulation(SimConfig(walk_fraction=fraction, **SHORT), "walk-left", 5)
            sim.run()
            return [p.arrival_time for p in sim.people]
        self.assertEqual(times(0.25), times(0.5))

    def test_people_conserved(self):
        sim = Simulation(SimConfig(**SHORT), "walk-left", 4)
        stepped(sim, lambda s: self.assertEqual(
            len(s.people),
            len(s.finished) + sum(map(len, s.queues)) + sum(map(len, s.on_belt))))


class RandomDraws(unittest.TestCase):
    def test_known_values(self):
        # Pinned so a change in hashing or Python's math shows up here first.
        d = Draws(1)
        self.assertEqual(d.uniform("arrival_gap", 0), 0.7669341712655976)
        self.assertAlmostEqual(d.normal("walk_speed", 5, 0.7, 0.2), 0.6839428765673651,
                               places=12)
        self.assertAlmostEqual(d.exponential("arrival_gap", 3, 2.0), 0.11116357945484559,
                               places=12)

    def test_same_key_same_value_and_keys_independent(self):
        a, b = Draws(1), Draws(1)
        self.assertEqual(a.uniform("x", 3), b.uniform("x", 3))
        values = {a.uniform("x", 3), a.uniform("y", 3), a.uniform("x", 4), Draws(2).uniform("x", 3)}
        self.assertEqual(len(values), 4)

    def test_choice_covers_options(self):
        d = Draws(1)
        picks = [d.choice("pick", i, ["a", "b", "c"]) for i in range(300)]
        self.assertEqual(set(picks), {"a", "b", "c"})

    def test_distributions_match_theory(self):
        d, n = Draws(3), 10_000
        u = [d.uniform("u", i) for i in range(n)]
        self.assertTrue(all(0.0 <= x < 1.0 for x in u))
        self.assertAlmostEqual(sum(u) / n, 0.5, delta=0.01)
        gaps = [d.exponential("e", i, 2.0) for i in range(n)]
        self.assertAlmostEqual(sum(gaps) / n, 0.5, delta=0.02)
        z = [d.normal("n", i, 0.7, 0.2) for i in range(n)]
        mean = sum(z) / n
        sd = (sum((x - mean) ** 2 for x in z) / (n - 1)) ** 0.5
        self.assertAlmostEqual(mean, 0.7, delta=0.01)
        self.assertAlmostEqual(sd, 0.2, delta=0.01)


class TripGroups(unittest.TestCase):
    def test_groups_add_up_and_match_across_strategies(self):
        cfg = SimConfig(walk_fraction=0.4, **SHORT)
        a, b = Simulation(cfg, "walk-left", 3), Simulation(cfg, "stand-both", 3)
        ra, rb = a.run(), b.run()
        measured = [p for p in a.people if p.arrival_time >= cfg.warmup]
        self.assertEqual(ra["cares_count"] + ra["others_count"], len(measured))
        self.assertEqual(ra["cares_count"], sum(p.wants_to_walk for p in measured))
        self.assertEqual((ra["cares_count"], ra["others_count"]),
                         (rb["cares_count"], rb["others_count"]))

    def test_empty_group_gives_none(self):
        r = Simulation(SimConfig(walk_fraction=0, drain=1, **SHORT), "walk-left", 1).run()
        self.assertEqual(r["cares_count"], 0)
        self.assertIsNone(r["trip_mean_cares"])
        self.assertIsNone(r["trip_p95_cares"])
        self.assertIsNotNone(r["trip_mean_others"])


OVERLOADED = dict(arrival_rate=200, **SHORT)
WINDOW_FIELDS = ["throughput_per_min", "throughput_by_lane", "queue_mean", "queue_max",
                 "lane_queue_max", "queue_end", "walked_share", "finished", "arrived",
                 "measured_seconds", "cares_count", "others_count"]


class Drain(unittest.TestCase):
    def test_everyone_measured_finishes(self):
        sim = Simulation(SimConfig(drain=1, **OVERLOADED), "walk-left", 2)
        r = sim.run()
        measured = [p for p in sim.people if p.arrival_time >= sim.config.warmup]
        self.assertTrue(all(p.board_time is not None and p.exit_time is not None
                            for p in measured))
        self.assertEqual(r["drained"], 1)
        self.assertGreater(sim.time, sim.config.duration)

    def test_off_by_default(self):
        sim = Simulation(SimConfig(**OVERLOADED), "walk-left", 2)
        r = sim.run()
        self.assertEqual(r["drained"], 0)
        self.assertAlmostEqual(sim.time, sim.config.duration)

    def test_window_figures_unchanged(self):
        for strategy in ("stand-both", "walk-left"):
            off = Simulation(SimConfig(**OVERLOADED), strategy, 2).run()
            on = Simulation(SimConfig(drain=1, **OVERLOADED), strategy, 2).run()
            with self.subTest(strategy=strategy):
                self.assertGreater(off["queue_end"], 0)
                for key in WINDOW_FIELDS:
                    self.assertEqual(on[key], off[key], key)

    def test_earlier_trips_unchanged(self):
        cfg = SimConfig(arrival_rate=60, **SHORT)
        off, on = Simulation(cfg, "walk-left", 4), Simulation(cfg.with_changes(drain=1),
                                                              "walk-left", 4)
        off.run(), on.run()
        before = {p.id: (p.board_time, p.exit_time) for p in off.finished}
        self.assertTrue(before)
        for p in on.people[:len(off.people)]:
            if p.id in before:
                self.assertEqual((p.board_time, p.exit_time), before[p.id])

    def test_fixes_undercount_when_overloaded(self):
        off = Simulation(SimConfig(**OVERLOADED), "walk-left", 2).run()
        on = Simulation(SimConfig(drain=1, **OVERLOADED), "walk-left", 2).run()
        self.assertGreater(on["wait_mean"], off["wait_mean"])
        self.assertGreater(on["trip_mean"], off["trip_mean"])
        self.assertGreater(on["trip_mean_cares"], off["trip_mean_cares"])

    def test_drain_twice_is_harmless(self):
        sim = Simulation(SimConfig(drain=1, **OVERLOADED), "stand-both", 5)
        first = sim.run()
        sim.drain()
        self.assertEqual(sim.results(), first)

    def test_run_until_never_drains(self):
        sim = Simulation(SimConfig(drain=1, **SHORT), "walk-left", 1)
        sim.run(until=SHORT["duration"])
        self.assertFalse(sim.drained)


BOTH = ["stand-both", "walk-left"]
DRAINED = dict(drain=1, **SHORT)


class TimeSaved(unittest.TestCase):
    """Time saved with the drain on, the only mode where it's a fair comparison."""

    def test_paired_saving_equals_per_person_average(self):
        cfg = SimConfig(walk_fraction=0.4, **DRAINED)
        entry = compare(cfg, BOTH, 1, base_seed=3)["time_saved"][0]
        self.assertEqual((entry["by"], entry["over"]), ("walk-left", "stand-both"))
        self.assertTrue(entry["drained"])
        a, b = Simulation(cfg, "stand-both", 3), Simulation(cfg, "walk-left", 3)
        a.run(), b.run()
        for group, wants in (("cares", True), ("others", False)):
            saved = [(pa.exit_time - pa.arrival_time) - (pb.exit_time - pb.arrival_time)
                     for pa, pb in zip(a.people, b.people)
                     if pa.arrival_time >= cfg.warmup and pa.wants_to_walk == wants]
            with self.subTest(group=group):
                self.assertAlmostEqual(entry["per_seed"][group][0], sum(saved) / len(saved),
                                       places=9)

    def test_walkers_save_about_the_ride_difference_with_spare_capacity(self):
        cfg = SimConfig(arrival_rate=30, blocker_rate=0, **DRAINED)
        entry = compare(cfg, BOTH, 5)["time_saved"][0]
        ride = cfg.length / cfg.belt_speed - cfg.length / (cfg.belt_speed + cfg.walk_speed_mean)
        # Slightly less than `ride`: walking speeds vary (slow walkers lose more than fast
        # ones gain) and a walker can be held up behind a slower one. Waits are near zero.
        self.assertGreater(entry["cares"]["mean"], 0)
        self.assertAlmostEqual(entry["cares"]["mean"], ride, delta=0.15 * ride)
        self.assertEqual(time_winner(entry), "walk-left")

    def test_empty_group_gives_none(self):
        entry = compare(SimConfig(walk_fraction=0, **DRAINED), BOTH, 2)["time_saved"][0]
        self.assertIsNone(entry["cares"]["mean"])
        self.assertEqual(entry["per_seed"]["cares"], [None, None])
        self.assertEqual(time_winner(entry), "-")

    def test_sweep_has_time_saved_for_every_point(self):
        s = sweep(SimConfig(**DRAINED), "blocker_rate", [0.0, 0.1], BOTH, 2)
        for point in s["points"]:
            self.assertEqual(len(point["time_saved"]), 1)
            self.assertTrue(point["time_saved"][0]["drained"])

    def test_time_winner_rule(self):
        def entry(m, ci, drained=True):
            return {"by": "walk-left", "over": "stand-both", "drained": drained,
                    "cares": {"mean": m, "ci95": ci, "n": 5}}
        self.assertEqual(time_winner(entry(10.0, 3.0)), "walk-left")
        self.assertEqual(time_winner(entry(-10.0, 3.0)), "stand-both")
        self.assertEqual(time_winner(entry(2.0, 3.0)), "tie")
        self.assertEqual(time_winner(entry(10.0, None)), "-")
        self.assertEqual(time_winner(entry(10.0, 3.0, drained=False)), "-")

    def test_cli_prints_saving_and_winner(self):
        out = io.StringIO()
        short = ["--duration", "180", "--warmup", "60", "--drain", "1"]
        main(["compare", "-n", "2", *short], out=out)
        text = out.getvalue()
        self.assertIn("walk-left vs stand-both: walkers save", text)
        self.assertIn("Fastest for walkers:", text)
        self.assertNotIn("Add --drain 1", text)
        out = io.StringIO()
        main(["sweep", "--param", "blocker_rate", "--values", "0,0.1", "-n", "2", *short],
             out=out)
        self.assertIn("Fastest for walkers", out.getvalue())


class LiveTripGroups(unittest.TestCase):
    def test_live_group_averages_match_finished_people(self):
        sim = Simulation(SimConfig(walk_fraction=0.4, **SHORT), "walk-left", 6)
        stats = sim.live_stats()
        self.assertIsNone(stats["trip_mean_cares"])
        self.assertIsNone(stats["trip_mean_others"])
        for until in (90.0, SHORT["duration"]):
            sim.run(until=until)
            stats = sim.live_stats()
            for key, wants in (("trip_mean_cares", True), ("trip_mean_others", False)):
                trips = [p.exit_time - p.arrival_time for p in sim.finished
                         if p.wants_to_walk == wants]
                with self.subTest(until=until, key=key):
                    self.assertAlmostEqual(stats[key], sum(trips) / len(trips), places=9)


class SnapshotAndResults(unittest.TestCase):
    def test_snapshot_and_results_are_json(self):
        sim = Simulation(SimConfig(**SHORT), "walk-left", 1)
        for _ in range(300):
            sim.step()
        snap = json.loads(json.dumps(sim.snapshot()))
        self.assertEqual(len(snap["lanes"]), 2)
        self.assertGreater(snap["arrived"], 0)
        json.dumps(sim.run())

    def test_warmup_too_short_flag(self):
        short = SimConfig(duration=100, warmup=10)
        self.assertTrue(Simulation(short, "stand-both").run()["warmup_too_short"])
        self.assertFalse(Simulation(SimConfig(**SHORT), "stand-both").run()["warmup_too_short"])

    def test_overloaded_waits_include_people_still_queueing(self):
        cfg = SimConfig(arrival_rate=300, **SHORT)
        r = Simulation(cfg, "stand-both", 1).run()
        self.assertGreater(r["queue_end"], 0)
        self.assertGreater(r["wait_max"], 30)


class Config(unittest.TestCase):
    def test_validation(self):
        for bad in [dict(walk_fraction=1.5), dict(belt_speed=0), dict(warmup=700), dict(dt=0),
                    dict(drain=2)]:
            with self.assertRaises(ValueError):
                SimConfig(**bad)

    def test_from_dict(self):
        self.assertEqual(SimConfig.from_dict({"lanes": 3.0}).lanes, 3)
        with self.assertRaises(ValueError):
            SimConfig.from_dict({"lanes": 2.5})
        with self.assertRaises(ValueError):
            SimConfig.from_dict({"nope": 1})

    def test_length(self):
        self.assertAlmostEqual(SimConfig(rise=10, incline_deg=30).length, 20.0)


class Metrics(unittest.TestCase):
    def test_percentile(self):
        self.assertEqual(percentile([1, 2, 3, 4, 5], 50), 3)
        self.assertIsNone(percentile([], 50))

    def test_mean_ci(self):
        r = mean_ci([1.0, 2.0, 3.0, None])
        self.assertEqual(r["n"], 3)
        self.assertAlmostEqual(r["mean"], 2.0)
        self.assertAlmostEqual(r["ci95"], 4.303 * 1 / 3 ** 0.5, places=3)


class Experiments(unittest.TestCase):
    def test_compare_and_sweep(self):
        cfg = SimConfig(**SHORT)
        c = compare(cfg, ["stand-both", "walk-left"], 2)
        self.assertEqual(set(c["strategies"]), {"stand-both", "walk-left"})
        s = sweep(cfg, "walk_fraction", [0.0, 0.5], ["walk-left"], 2)
        self.assertEqual([p["value"] for p in s["points"]], [0.0, 0.5])

    def test_time_saved_without_drain_is_marked_and_has_no_winner(self):
        c = compare(SimConfig(**SHORT), ["stand-both", "walk-left"], 2)
        self.assertEqual(len(c["time_saved"]), 1)
        self.assertFalse(c["time_saved"][0]["drained"])
        self.assertEqual(time_winner(c["time_saved"][0]), "-")
        one = compare(SimConfig(**SHORT), ["walk-left"], 1)
        self.assertEqual(one["time_saved"], [])


class Cli(unittest.TestCase):
    def run_cli(self, *argv):
        out = io.StringIO()
        self.assertEqual(main(list(argv), out=out), 0)
        return out.getvalue()

    def test_commands(self):
        short = ["--duration", "90", "--warmup", "45"]
        self.assertIn("Thru/min", self.run_cli("run", *short))
        self.assertIn("vs walk-left", self.run_cli("compare", "-n", "2", *short))
        self.assertIn("Most throughput", self.run_cli("sweep", "--param", "arrival_rate",
                                                      "--values", "60,120", "-n", "2", *short))
        json.loads(self.run_cli("compare", "-n", "2", "--output", "json", *short))
        self.assertIn("strategy", self.run_cli("run", "--output", "csv", *short).splitlines()[0])
        self.assertIn("stand-both", self.run_cli("strategies"))

    def test_without_drain_hints_instead_of_time_saved(self):
        short = ["--duration", "90", "--warmup", "45"]
        for command in (["compare", "-n", "2"],
                        ["sweep", "--param", "arrival_rate", "--values", "60,120", "-n", "2"]):
            text = self.run_cli(*command, *short)
            with self.subTest(command=command[0]):
                self.assertIn("Add --drain 1 to measure time saved", text)
                self.assertNotIn("walkers save", text)
                self.assertNotIn("Fastest for walkers", text)

    def test_bad_parameter_exits(self):
        with self.assertRaises(SystemExit):
            main(["run", "--walk-fraction", "2"], out=io.StringIO())
        with self.assertRaises(SystemExit):
            main(["sweep", "--param", "lanes", "--values", "2.5"], out=io.StringIO())


def _person(sim, arrival, walking=False):
    from escalator_sim.person import Person
    p = Person(len(sim.people), arrival, walking, 0.7, lane=0, walking=walking)
    sim.people.append(p)
    return p


if __name__ == "__main__":
    unittest.main()
