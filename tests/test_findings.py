"""Tests for docs/findings.py, the script behind docs/FINDINGS.md."""
import io
import unittest

from docs import findings


def _point(cares, others, cares_count, others_count, seconds=600.0):
    runs = [{"cares_count": c, "others_count": o, "measured_seconds": seconds}
            for c, o in zip(cares_count, others_count)]
    return {"strategies": {"walk-left": {"runs": runs}},
            "time_saved": [{"by": "walk-left", "per_seed": {"cares": cares, "others": others}}]}


class NetSaving(unittest.TestCase):
    def test_weights_each_group_by_its_size_per_minute(self):
        # Seed 1: (10 s × 30 + -2 s × 50) / 10 min = 20; seed 2: (20 × 40 - 4 × 60) / 10 = 56.
        point = _point([10.0, 20.0], [-2.0, -4.0], [30, 40], [50, 60])
        self.assertAlmostEqual(findings.net_saving_per_min(point)["mean"], 38.0)

    def test_empty_group_adds_nothing_and_missing_saving_skips_the_seed(self):
        point = _point([None, None, 5.0], [3.0, 1.0, 1.0], [0, 10, 10], [20, 20, 20])
        stats = findings.net_saving_per_min(point)
        self.assertEqual(stats["n"], 2)  # seed 2 has walkers but no saving
        self.assertAlmostEqual(stats["mean"], (60.0 / 10 + 70.0 / 10) / 2)


class PairedChange(unittest.TestCase):
    def test_matches_runs_by_seed(self):
        before = [{"seed": 1, "throughput_per_min": 100.0}, {"seed": 2, "throughput_per_min": 90.0}]
        after = [{"seed": 2, "throughput_per_min": 92.0}, {"seed": 1, "throughput_per_min": 101.0}]
        stats = findings.paired_change(before, after)
        self.assertEqual(stats["n"], 2)
        self.assertAlmostEqual(stats["mean"], 1.5)


class QuickRun(unittest.TestCase):
    def test_prints_every_table(self):
        out = io.StringIO()
        self.assertEqual(findings.main(["--quick", "--jobs", "0"], out=out), 0)
        text = out.getvalue()
        self.assertEqual(text.count("\n### "), len(findings.SWEEPS) + 6)
        self.assertEqual(text.count("| Walkers save s |"), len(findings.SWEEPS) + 5)
        self.assertIn("drain=1", text)
        self.assertEqual(text.count("same crowds |"), 2)


if __name__ == "__main__":
    unittest.main()
