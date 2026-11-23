import io
import json
import unittest

from escalator_sim import SimConfig, Simulation, compare, sweep
from escalator_sim.cli import main
from escalator_sim.metrics import mean_ci, percentile

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
                        self.assertGreaterEqual(p.pos - last_pos[p.id], cfg.belt_speed * cfg.dt - 1e-9)
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
        self.assertEqual(Simulation(cfg, "walk-left", 7).run(), Simulation(cfg, "walk-left", 7).run())

    def test_same_crowd_across_strategies(self):
        cfg = SimConfig(**SHORT)
        a, b = Simulation(cfg, "walk-left", 7), Simulation(cfg, "stand-both", 7)
        a.run(), b.run()
        key = lambda s: [(p.arrival_time, p.wants_to_walk, p.walk_speed) for p in s.people]
        self.assertEqual(key(a), key(b))

    def test_people_conserved(self):
        sim = Simulation(SimConfig(**SHORT), "walk-left", 4)
        stepped(sim, lambda s: self.assertEqual(
            len(s.people),
            len(s.finished) + sum(map(len, s.queues)) + sum(map(len, s.on_belt))))


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
        self.assertTrue(Simulation(SimConfig(duration=100, warmup=10), "stand-both").run()["warmup_too_short"])
        self.assertFalse(Simulation(SimConfig(**SHORT), "stand-both").run()["warmup_too_short"])

    def test_overloaded_waits_include_people_still_queueing(self):
        cfg = SimConfig(arrival_rate=300, **SHORT)
        r = Simulation(cfg, "stand-both", 1).run()
        self.assertGreater(r["queue_end"], 0)
        self.assertGreater(r["wait_max"], 30)


class Config(unittest.TestCase):
    def test_validation(self):
        for bad in [dict(walk_fraction=1.5), dict(belt_speed=0), dict(warmup=700), dict(dt=0)]:
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
