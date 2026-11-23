"""Checks the engine against measured London Underground escalator flows.

Source: P. Davis and G. Dutta (2002), "Estimation of Capacity of Escalators in
London Underground", IIM Ahmedabad working paper 2002-11-01. They counted
standers and walkers separately on busy up escalators at 10 central London
stations while a queue was waiting (walk-left etiquette), and fitted:

    standing side (ppm) = 41.27 + 0.73 * rise                          (sec. 6.3.1)
    walking side  (ppm) = 83.49 - 1.20 * rise - 8.05 * double_escalator  (sec. 6.3.2)

Escalators: 0.4 m steps, 43.2 m/min (0.72 m/s). Measured rises span about 7.6-23.4 m;
Holborn 5/6 (23.4 m, one of a pair) is the escalator pair later used for the
2015 stand-on-both-sides trial.

These tests use explicit settings rather than the defaults, so they keep
checking the engine's flow mechanics when someone changes a default. The
settings below are the calibrated values: the paper gives belt speed, step
depth and (through the two formulas) the walking share; `walk_gap` = 0.9 m was
fitted so the walking side matches across all rises (with the old 1.2 m gap the
engine was 13-21% low below 15 m rise). Walking speeds were not measured and
keep their defaults.

Tolerance: the paper's regressions have adjusted R^2 of 0.81 (standing) and
0.85 (walking), so individual escalators scatter by several ppm around them.
10% per lane catches broken mechanics without demanding more precision than
the data has. The engine's standing lane has a fixed capacity, whereas the
paper's rises with rise (people squeezing in from the walking queue), so the
standing error grows to about -7% at 23 m.
"""
import unittest

from escalator_sim import SimConfig, Simulation

CALIBRATED = dict(
    belt_speed=0.72,      # 43.2 m/min, measured
    step_depth=0.4,       # measured
    walk_gap=0.9,         # fitted to the walking-side formula
    defect_prob=0.0,      # the formulas count lanes as observed; no extra switching
    blocker_rate=0.0,
    duration=900.0,
    warmup=240.0,         # longer than one ride at 23.4 m rise (65 s)
)
SEEDS = (1, 2)
TOLERANCE = 0.10

# (rise in meters, one of a pair of up escalators)
CASES = [(8.0, False), (12.0, False), (16.0, False), (20.0, False), (23.4, True)]


def measured(rise: float, double: bool) -> tuple[float, float]:
    """(standing ppm, walking ppm) from Davis & Dutta's regressions."""
    standing = 41.27 + 0.73 * rise
    walking = 83.49 - 1.20 * rise - 8.05 * double
    return standing, walking


def simulated_lanes(cfg: SimConfig) -> tuple[float, float]:
    """Mean (standing lane, walking lane) throughput over SEEDS."""
    runs = [Simulation(cfg, "walk-left", seed=s).run() for s in SEEDS]
    walk = sum(r["throughput_by_lane"][0] for r in runs) / len(runs)
    stand = sum(r["throughput_by_lane"][1] for r in runs) / len(runs)
    return stand, walk


class DavisDutta2002(unittest.TestCase):
    def test_walk_left_lane_flows_match_measurements(self):
        for rise, double in CASES:
            stand, walk = measured(rise, double)
            total = stand + walk
            # Arrivals at the measured total with the measured walking share:
            # the conditions under which the paper counted.
            cfg = SimConfig(rise=rise, arrival_rate=total, walk_fraction=walk / total,
                            **CALIBRATED)
            sim_stand, sim_walk = simulated_lanes(cfg)
            with self.subTest(rise=rise, double=double):
                self.assertAlmostEqual(sim_walk, walk, delta=walk * TOLERANCE,
                                       msg=f"walking lane {sim_walk:.1f} vs measured {walk:.1f}")
                self.assertAlmostEqual(sim_stand, stand, delta=stand * TOLERANCE,
                                       msg=f"standing lane {sim_stand:.1f} vs measured {stand:.1f}")


class HolbornTrial2015(unittest.TestCase):
    """Harrison et al. (2016), "Pilot for Standing on Both Sides of Escalators",
    6th Symposium on Lift & Escalator Technologies. On the all-standing day
    (8 Dec 2015) single escalators carried up to about 450 people per 5 minutes
    (Graph 3, read from the chart), i.e. about 90 per minute. Counts matched the
    gate line, so that is a lower bound on capacity, not capacity itself."""

    def test_stand_both_capacity_at_least_observed_peak(self):
        cfg = SimConfig(rise=23.4, arrival_rate=200, **CALIBRATED)
        r = Simulation(cfg, "stand-both", seed=1).run()
        self.assertGreaterEqual(r["throughput_per_min"], 90)


if __name__ == "__main__":
    unittest.main()
