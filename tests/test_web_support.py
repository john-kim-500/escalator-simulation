"""Tests for the engine pieces the GUI relies on."""
import json
import math
import unittest
from pathlib import Path

from escalator_sim import SimConfig, Simulation, compare, sweep
from escalator_sim.config import PARAM_INFO, PRESETS, GROUPS
from escalator_sim.experiments import (collect_compare, collect_sweep, plan_compare,
                                       plan_sweep, run_one)
from escalator_sim.session import Session, check_config, dumps
from escalator_sim.strategies import KINDS

ROOT = Path(__file__).resolve().parent.parent
SHORT = dict(duration=180.0, warmup=60.0)


class ParamInfo(unittest.TestCase):
    def test_every_parameter_described(self):
        self.assertEqual(set(PARAM_INFO), set(SimConfig.field_names()))
        for name, info in PARAM_INFO.items():
            self.assertIn(info["group"], GROUPS, name)
            self.assertTrue(info["label"] and info["help"], name)

    def test_ranges_include_defaults(self):
        defaults = SimConfig()
        for name, info in PARAM_INFO.items():
            self.assertLessEqual(info["min"], getattr(defaults, name), name)
            self.assertGreaterEqual(info["max"], getattr(defaults, name), name)
            self.assertGreater(info["step"], 0, name)

    def test_presets_are_valid(self):
        for key, preset in PRESETS.items():
            config = SimConfig().with_changes(**preset["values"])
            self.assertEqual(config.warnings(), [], key)


class Kinds(unittest.TestCase):
    def test_kinds_set_for_everyone(self):
        cfg = SimConfig(blocker_rate=0.1, **SHORT)
        sim = Simulation(cfg, "walk-left", 2)
        sim.run()
        seen = {p.kind for p in sim.people}
        self.assertEqual(seen, set(KINDS))
        for p in sim.people:
            if p.kind == "defector":
                self.assertTrue(p.walking and not p.wants_to_walk)
            if p.kind == "blocker":
                self.assertTrue(p.lane == 0 and not p.walking)

    def test_stand_both_only_standers(self):
        sim = Simulation(SimConfig(**SHORT), "stand-both", 2)
        sim.run()
        self.assertEqual({p.kind for p in sim.people}, {"stander"})


class SnapshotAndLiveStats(unittest.TestCase):
    def test_queue_limit(self):
        sim = Simulation(SimConfig(arrival_rate=300, **SHORT), "stand-both", 1)
        sim.run(until=120)
        snap = sim.snapshot(max_queue=5)
        for lane, q in zip(snap["lanes"], sim.queues):
            self.assertEqual(len(lane["queue"]), 5)
            self.assertEqual(lane["queue_length"], len(q))
            self.assertEqual([p["id"] for p in lane["queue"]], [p.id for p in list(q)[:5]])
        self.assertEqual(len(sim.snapshot()["lanes"][0]["queue"]), len(sim.queues[0]))

    def test_live_stats_match_full_scan(self):
        sim = Simulation(SimConfig(**SHORT), "walk-left", 3)
        sim.run(until=150)
        stats = sim.live_stats()
        boarded = [p for p in sim.people if p.board_time is not None]
        self.assertAlmostEqual(stats["wait_mean"],
                               sum(p.board_time - p.arrival_time for p in boarded) / len(boarded))
        recent = [p for p in sim.finished if p.exit_time > sim.time - 60]
        self.assertAlmostEqual(stats["throughput_recent"], len(recent))
        self.assertEqual(stats["finished"], len(sim.finished))
        self.assertAlmostEqual(stats["walked_share"],
                               sum(p.walking for p in sim.finished) / len(sim.finished))

    def test_live_stats_at_start(self):
        stats = Simulation(SimConfig(), "walk-left").live_stats()
        self.assertEqual(stats["throughput_recent"], 0.0)
        self.assertIsNone(stats["wait_mean"])


class SplitExperiments(unittest.TestCase):
    def test_compare_split_matches(self):
        cfg = SimConfig(**SHORT)
        plan = plan_compare(cfg, ["stand-both", "walk-left"], 2, 5)
        split = collect_compare(plan, [run_one(j) for j in plan["jobs"]])
        self.assertEqual(split, compare(cfg, ["stand-both", "walk-left"], 2, 5))

    def test_sweep_split_matches(self):
        cfg = SimConfig(**SHORT)
        plan = plan_sweep(cfg, "lanes", [2, 3], ["walk-left"], 2)
        split = collect_sweep(plan, [run_one(j) for j in plan["jobs"]])
        self.assertEqual(split, sweep(cfg, "lanes", [2, 3], ["walk-left"], 2))
        self.assertEqual(plan["values"], [2, 3])


class ConfigChecks(unittest.TestCase):
    def test_field_errors(self):
        r = check_config({"walk_fraction": 2, "rise": "abc", "lanes": 2.5})
        self.assertFalse(r["ok"])
        self.assertEqual({e["field"] for e in r["errors"]}, {"rise", "lanes"})  # type errors first
        r = check_config({"walk_fraction": 2})
        self.assertEqual([e["field"] for e in r["errors"]], ["walk_fraction"])

    def test_strategy_errors(self):
        r = check_config({"lanes": 1}, ["walk-left"])
        self.assertFalse(r["ok"])
        self.assertEqual(r["errors"][0]["field"], "lanes")

    def test_ok_with_warnings_and_derived(self):
        r = check_config({"warmup": 10})
        self.assertTrue(r["ok"])
        self.assertEqual(r["warnings"][0]["field"], "warmup")
        self.assertAlmostEqual(r["derived"]["stand_lane_capacity"], 56.25)

    def test_dumps_handles_infinity(self):
        self.assertEqual(json.loads(dumps({"a": math.inf, "b": [math.nan]})), {"a": None, "b": [None]})
        r = json.loads(dumps(check_config({"board_headway": 0})))
        self.assertTrue(r["ok"])


class SessionApi(unittest.TestCase):
    def test_info(self):
        info = json.loads(Session().info())
        self.assertEqual(set(info["param_info"]), set(SimConfig.field_names()))
        self.assertIn("walk-left", info["strategies"])

    def test_live_same_crowd_and_lockstep(self):
        s = Session()
        s.live_start(json.dumps(SHORT), json.dumps(["stand-both", "walk-left"]), 4)
        state = json.loads(s.live_advance(30.0))
        self.assertAlmostEqual(state["time"], 30.0)
        a, b = state["sims"]
        self.assertEqual(a["stats"]["arrived"], b["stats"]["arrived"])
        state = json.loads(s.live_advance(10_000))
        self.assertTrue(state["done"])
        self.assertAlmostEqual(state["time"], SHORT["duration"])

    def test_live_advance_never_overshoots(self):
        s = Session()
        s.live_start(json.dumps(SHORT), json.dumps(["walk-left"]), 1)
        self.assertEqual(json.loads(s.live_advance(0.016))["time"], 0.0)  # under one step
        self.assertAlmostEqual(json.loads(s.live_advance(0.25))["time"], 0.2)
        # A duration that is not a whole number of steps still finishes.
        s.live_start(json.dumps({**SHORT, "duration": 100.05}), json.dumps(["walk-left"]), 1)
        self.assertTrue(json.loads(s.live_advance(1000))["done"])

    def test_live_matches_cli_run(self):
        s = Session()
        s.live_start(json.dumps(SHORT), json.dumps(["walk-left"]), 9)
        for _ in range(50):
            s.live_advance(7.3)
        expected = Simulation(SimConfig(**SHORT), "walk-left", 9).run()
        self.assertEqual(json.loads(s.live_results())[0]["throughput_per_min"],
                         expected["throughput_per_min"])

    def test_experiment_steps_match_compare(self):
        s = Session()
        spec = {"kind": "compare", "config": SHORT, "strategies": ["stand-both", "walk-left"],
                "replications": 2, "seed": 1}
        self.assertEqual(json.loads(s.exp_start(json.dumps(spec)))["total"], 4)
        progress = json.loads(s.exp_step(0))
        self.assertEqual(progress["done"], 1)
        with self.assertRaises(ValueError):
            s.exp_result()
        while progress["done"] < progress["total"]:
            progress = json.loads(s.exp_step(0))
        result = json.loads(s.exp_result())
        expected = json.loads(dumps(compare(SimConfig(**SHORT), ["stand-both", "walk-left"], 2, 1)))
        self.assertEqual(result, expected)

    def test_sweep_experiment_and_cancel(self):
        s = Session()
        spec = {"kind": "sweep", "config": SHORT, "strategies": ["walk-left"],
                "replications": 1, "param": "walk_fraction", "values": [0, 0.5]}
        s.exp_start(json.dumps(spec))
        s.exp_cancel()
        with self.assertRaises(ValueError):
            s.exp_step()


class WebManifest(unittest.TestCase):
    def test_manifest_lists_every_module(self):
        manifest = ROOT / "web" / "manifest.json"
        if not manifest.exists():
            self.skipTest("web/manifest.json not created yet")
        listed = set(json.loads(manifest.read_text())["files"])
        actual = {p.name for p in (ROOT / "escalator_sim").glob("*.py")}
        self.assertEqual(listed, actual)


if __name__ == "__main__":
    unittest.main()
