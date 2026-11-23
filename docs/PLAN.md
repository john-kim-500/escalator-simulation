# Escalator Simulator — Plan

## Goal

Test the claim that an escalator moves more people when **everyone stands on both
lanes** than under the usual convention of **standing on one side and walking on
the other**. For background, see the 2015–16 London Underground trial at Holborn
station, where the escalator managed as standing-only carried about 27% more people
in an hour.
For that trial and other studies, see [RESEARCH.md](RESEARCH.md).

## Design principles

- **Agent-based:** each person is modeled individually, with their own position,
  lane, speed and timestamps.
- **The engine has no display code:** it advances in fixed time steps and exposes
  its full state through `snapshot()`. The command line tool comes first, and a
  visual front end can be added later on the same engine without changing it.
- **Reproducible:** every run takes a random seed.
- **Pluggable strategies:** lane choice and behavior live in strategy classes,
  so a new rule can be added without touching the engine.
- **Standard library only** for the engine. Plotting and GUI dependencies stay
  optional.

## Tech stack

**Decision: a Python engine that also runs in the browser through Pyodide (option A).**

- **Command line and experiments:** native Python 3.11. Plotting and analysis
  libraries (matplotlib, pandas) are optional extras, never needed by the engine.
- **Web interface:** a static page (HTML, JS and canvas) that loads the
  `escalator_sim` package into Pyodide, which is CPython compiled to WebAssembly.
  The page calls `step()` and `snapshot()` directly. Everything runs on the user's
  machine, so no server is needed and the page can be hosted as a static site
  (e.g. GitHub Pages).

### Options considered

| Option | How the web version works | Pros | Cons |
|---|---|---|---|
| **A. Python engine + Pyodide** ✅ | Engine runs in the browser through WebAssembly; JS draws the interface | One engine. Python analysis tools for the experiments. No server | About 12 MB download and a few seconds to start. Small overhead on calls between JS and Python |
| B. Python engine on a server | FastAPI or similar streams snapshots to the browser over WebSockets | Plain Python everywhere | Needs hosting and a running server. Network delay on every frame. Every viewer uses server CPU |
| C. TypeScript engine | Runs natively in the browser; the command line runs on Node | Fastest and smallest in the browser. One language | Weaker tools for statistics and plotting |
| D. Python batch runs + recorded replays | Python writes a JSON trace; a static page plays it back | Very simple | No live sliders. Can only watch runs recorded beforehand |

Also rejected: keeping two engines, such as Python for experiments plus a JS copy
for the visuals. The two would drift apart, and the visuals would stop matching
the experiment results.

**Reasons for choosing A:** the engine already needs only the standard library,
so it runs in Pyodide unchanged. Speed is not a concern: a few hundred people on
screen is trivial even with Pyodide's overhead. Option C stays the fallback if
the web version becomes the main product and fast page loads matter.

### Rules for the engine, so it keeps working in Pyodide
- Standard library only. No numpy inside the engine.
- It only takes and returns plain data (dicts, lists and numbers) that can be
  turned into JSON.
- No threads, no file input/output, no `time.sleep`. The caller drives the loop
  by calling `step()`.
- File output and terminal formatting belong in `cli.py`, never in the engine.

## Variables

### Escalator
| Parameter | Meaning | Default (approx.) |
|---|---|---|
| `rise` | Vertical rise (m). The incline length is derived from it at 30° | 15 m |
| `belt_speed` | Speed of the steps (m/s) | 0.75 |
| `step_depth` | Depth of one step (m) | 0.4 |
| `lanes` | Number of lanes | 2 |

### Crowd
| Parameter | Meaning | Default |
|---|---|---|
| `arrival_rate` | Arrival rate (people/min, each arriving at a random time) for rush hour vs off-peak | 120 |
| `walk_fraction` | Share of people who *want* to walk | 0.25 |
| `walk_speed_mean` / `_sd` | Walking speed relative to the belt (m/s), varied per person | 0.7 / 0.15 |

### Spacing and boarding
| Parameter | Meaning | Default |
|---|---|---|
| `stand_gap` | Minimum spacing for people standing (m). Standers often leave a step empty | 0.8 |
| `walk_gap` | Minimum spacing for people walking (m). Fitted to measured flows (Davis & Dutta 2002) | 0.9 |
| `board_headway` | Minimum time between boardings in one lane (s) | 0.5 |

### Behavior (stand-one-side-walk-the-other strategy)
| Parameter | Meaning | Default |
|---|---|---|
| `defect_threshold` | Queue-length difference at which a stander is tempted to walk in the walk lane | 10 |
| `defect_prob` | Probability that a tempted stander actually switches | 0.3 |
| `blocker_rate` | Fraction of standers who stand in the walk lane | 0.0 |

### Run control
`duration`, `warmup` (excluded from metrics), `dt` (time step, default 0.1 s), `seed`, `replications`.

## Strategies

1. **`stand-both`:** everyone stands, including people who would rather walk, and
   picks the shorter queue.
2. **`walk-left`:** standers queue right, walkers queue left. The defection and
   blocker rules above apply.
3. *(Later)* **mixed or adaptive:** for example, switch to stand-both when the
   queues get long.

## Movement model

- Each lane is a one-dimensional track from the bottom of the escalator (`0`) to
  the top (`L`).
- A person's speed is `belt_speed + own walking speed`, limited by the person
  ahead: they can't get closer than their required gap. Nobody moves slower than
  the belt.
- A person boards when the last person in the lane has moved at least one gap up
  from the bottom and the minimum time between boardings has passed.
- Each lane has its own queue at the bottom. People are recorded as finished when
  they reach the top.

## Metrics

Metrics are measured after the warm-up period:
- People per minute reaching the top, both total and per lane.
- Queue wait: mean, 95th percentile and maximum.
- Total time from arrival to reaching the top: mean and 95th percentile, also
  split into people who want to walk and everyone else.
- Longest queue reached, and the share of people who walked.

## Code layout

```
escalator_sim/
  config.py      # dataclasses for the parameters above
  person.py      # Person state
  draws.py       # random numbers keyed by seed, purpose and person
  strategies.py  # Strategy base class + registry
  engine.py      # Simulation: step(), run(), snapshot(), results()
  metrics.py     # summary statistics
  experiments.py # compare / sweep across seeds (plain data; reusable from the web UI)
  report.py      # CSV/JSON output and the winner/tie rule
  session.py     # JSON-string API the browser calls
  cli.py         # argparse entry point (python3 -m escalator_sim)
tests/           # unittest (pytest is not installed)
```

### Engine API (shared by the command line and the web interface)
```python
sim = Simulation(config, strategy="walk-left", seed=1)
sim.step()             # advance one time step
sim.snapshot()         # {time, lanes:[{people:[{id,pos,walking}]}], queues, ...}
sim.run(until=600)
sim.results()          # summary metrics
```

## Command line

```
python3 -m escalator_sim run      --strategy walk-left --arrival-rate 120 --walk-fraction 0.25
python3 -m escalator_sim compare  --replications 20          # all strategies, same seeds
python3 -m escalator_sim sweep    --param walk_fraction --values 0,0.1,0.2,0.4 --replications 10
```
Results print as text tables, or as JSON or CSV with `--output json|csv`.

## Milestones

1. ✅ Configuration, the `Person` class and the engine with both strategies, plus unit tests for
   spacing, boarding and finishing.
2. ✅ Metrics and the `run`/`compare` commands.
3. ✅ The `sweep` command, which answers *when* each strategy wins (arrival rate,
   walk fraction, rise).
4. *(Partly done)* Check the results against measured data. `walk_gap` is fitted to Davis &
   Dutta (2002) and pinned by `tests/test_calibration.py`. The 2015 Holborn trial's 81 vs 112.5
   ppm were pre-trial calculations, not measurements. The findings also fit `stand_gap` to
   Davis & Dutta at Holborn's height (0.74 m). Still guessed: walking speeds, defection.
5. ✅ A static web front end: Pyodide loads `escalator_sim`, a JS canvas
   draws `snapshot()`, and sliders set the parameters. See [GUI_PLAN.md](GUI_PLAN.md).
   Some polish is still open there.
6. ✅ Time saved for people who want to walk. See [TIME_SAVED_PLAN.md](TIME_SAVED_PLAN.md)
   and [FINDINGS.md](FINDINGS.md).
7. *(Later)* Mixed or adaptive strategies, and boarding-time distributions.
