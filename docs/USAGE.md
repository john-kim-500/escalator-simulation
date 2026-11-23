# Running the Escalator Simulator

This guide covers installing, running and reading the results of the simulator.
For the design and the reasons behind it, see [PLAN.md](PLAN.md).

- [Requirements](#requirements)
- [Quick start](#quick-start)
- [Commands](#commands)
- [Parameters](#parameters)
- [Reading the results](#reading-the-results)
- [Saving results: JSON and CSV](#saving-results-json-and-csv)
- [Recipes for testing the theory](#recipes-for-testing-the-theory)
- [Web interface](#web-interface)
- [Using the engine from Python](#using-the-engine-from-python)
- [Troubleshooting](#troubleshooting)
- [Running the tests](#running-the-tests)

---

## Requirements

- Python 3.10 or newer.
- Nothing else. The simulator uses only the standard library, so there is nothing to install.

Run every command from the project folder (the one containing `escalator_sim/`):

```bash
cd escalator-simulator
python3 -m escalator_sim --help
```

## Quick start

```bash
# Compare both strategies on the same 10 crowds, using the default rush-hour settings
python3 -m escalator_sim compare
```

```
Escalator 30.0 m long (15 m rise), belt 0.75 m/s; 120 arrivals/min, 25% want to walk; measured 480 s after 120 s warm-up.
10 replications per strategy (seeds 1-10); values are mean ±95% CI.

Strategy    Thru/min    Wait avg s  Wait p95 s  Trip avg s  Max queue  Queue end  Walked
----------  ----------  ----------  ----------  ----------  ---------  ---------  ------
stand-both  112.2 ±0.4  21.9 ±6.2   37.0 ±9.2   61.0 ±6.0   83 ±20     74 ±25     0%
walk-left   111.1 ±0.7  28.8 ±4.8   68.0 ±12.2  58.9 ±4.2   99 ±20     91 ±23     49%

stand-both vs walk-left: throughput +1.0%, average wait -24.1%
```

The default settings are rough guesses, not measured values (see [Parameters](#parameters)).

## Commands

The general form is:

```
python3 -m escalator_sim <command> [parameters] [options]
```

| Command | What it does |
|---|---|
| `strategies` | Lists the strategies you can simulate |
| `run` | Runs one simulation of one strategy |
| `compare` | Runs every strategy on the same crowds, repeated several times, and averages the results |
| `sweep` | Repeats `compare` for each value of one parameter |

Add `--help` to any command to see every flag with its default, e.g.
`python3 -m escalator_sim sweep --help`.

### `strategies`

```bash
python3 -m escalator_sim strategies
```

| Name | Behavior |
|---|---|
| `stand-both` | Everyone stands in every lane, including people who would rather walk. Each person joins the shortest queue |
| `walk-left` | Standers queue on the right, walkers on the left (lane 0). When the right queue is long, some standers walk in the left lane instead (`defect_threshold`, `defect_prob`). Some standers stand in the walk lane and block it (`blocker_rate`) |

### `run`: one simulation

```bash
python3 -m escalator_sim run --strategy stand-both --seed 1
```

| Option | Default | Meaning |
|---|---|---|
| `--strategy NAME` | `walk-left` | Strategy to simulate |
| `--seed INT` | `1` | Random seed. The same seed always gives the same crowd and the same result |
| `--output table\|json\|csv` | `table` | Output format |

Besides the summary, this prints the throughput of each lane and how many people
arrived and finished. Use it to look at a single scenario closely. A single run
is noisy, so use `compare` to draw conclusions.

### `compare`: strategies side by side

```bash
python3 -m escalator_sim compare -n 20 -j 0
```

| Option | Default | Meaning |
|---|---|---|
| `--strategies A,B` | all | Comma-separated list of strategies to compare |
| `-n`, `--replications INT` | `10` | Runs per strategy, using seeds `seed` … `seed + n − 1` |
| `--seed INT` | `1` | First seed |
| `-j`, `--jobs INT` | `1` | Number of parallel processes. `0` uses all CPUs |
| `--output table\|json\|csv` | `table` | Output format |

Every strategy gets the same seeds, so every strategy faces exactly the same
arrivals: the same arrival times, the same walkers and the same walking speeds.
Any difference in the results therefore comes from the strategy, not from luck.
The last lines give each strategy's difference from `walk-left`.

### `sweep`: how the answer changes with one parameter

```bash
python3 -m escalator_sim sweep --param arrival_rate --values 60,90,120,150 -n 10 -j 0
```

```
arrival_rate  stand-both thru/min  walk-left thru/min  stand-both wait s  walk-left wait s  Most throughput
------------  -------------------  ------------------  -----------------  ----------------  ---------------
60            58.3 ±1.6            58.2 ±1.7           0.3 ±0.0           1.3 ±0.3          tie
90            88.6 ±2.5            88.9 ±2.5           1.1 ±0.2           6.8 ±0.5          tie
120           112.2 ±0.4           111.1 ±0.7          21.9 ±6.2          28.8 ±4.8         tie
150           112.5 ±0.0           113.9 ±0.8          87.4 ±5.8          84.3 ±6.0         walk-left
```

| Option | Default | Meaning |
|---|---|---|
| `--param NAME` | *(required)* | Any parameter name from the [table below](#parameters), with underscores, e.g. `walk_fraction` |
| `--values LIST` | *(required)* | Comma-separated numbers, e.g. `0,0.1,0.25` |
| `--strategies`, `-n`, `--seed`, `-j`, `--output` | | Same as `compare` (`-n` defaults to `5` here) |

The other parameters keep their defaults unless you set them, e.g.
`sweep --param walk_fraction --values 0,0.5 --defect-prob 0`.

**Most throughput** names a strategy only if its lead is larger than the two
95% margins of error added together; otherwise it says `tie`. This is a cautious
test, so a `tie` can still hide a small real difference. Use more replications
(`-n`) to narrow the margins.

## Parameters

Every parameter can be set on `run`, `compare` and `sweep` as a flag, written
with dashes (`--arrival-rate 90`). In `sweep --param` and in Python it is written
with underscores (`arrival_rate`).

Distances are in meters along the incline, times in seconds and speeds in m/s.

### Escalator

| Flag | Default | Meaning |
|---|---|---|
| `--rise` | 15 | Vertical rise (m) |
| `--incline-deg` | 30 | Incline angle. Escalator length = rise ÷ sin(angle), so 30 m by default |
| `--belt-speed` | 0.75 | Speed of the steps |
| `--step-depth` | 0.4 | Depth of one step. Used only for drawing; it has no effect on results |
| `--lanes` | 2 | Number of lanes. Lane 0 is the left (walk) lane. `walk-left` needs at least 2 |

### Crowd

| Flag | Default | Meaning |
|---|---|---|
| `--arrival-rate` | 120 | Arrivals per minute, at random intervals (a Poisson process) |
| `--walk-fraction` | 0.25 | Share of people who *want* to walk (0–1) |
| `--walk-speed-mean` | 0.7 | Average walking speed on top of the belt speed |
| `--walk-speed-sd` | 0.15 | Spread of walking speeds between people (standard deviation) |
| `--walk-speed-min` | 0.2 | Lowest allowed walking speed |

### Spacing and boarding

| Flag | Default | Meaning |
|---|---|---|
| `--stand-gap` | 0.8 | Closest a stander gets to the person ahead (0.8 m ≈ leaving one step empty) |
| `--walk-gap` | 0.9 | Closest a walker gets to the person ahead (fitted to measured London flows) |
| `--board-headway` | 0.5 | Minimum time between two people stepping onto the same lane |

These set each lane's capacity. A full standing lane carries
`belt_speed ÷ stand_gap × 60` people per minute, which is 56.25 with the defaults.

### Behavior (`walk-left` only)

| Flag | Default | Meaning |
|---|---|---|
| `--defect-threshold` | 10 | How many more people the right queue must have than the left before standers are tempted to walk |
| `--defect-prob` | 0.3 | Chance that a tempted stander walks in the left lane (0–1) |
| `--blocker-rate` | 0 | Share of standers who stand in the walk lane, blocking walkers behind them (0–1) |

### Run control

| Flag | Default | Meaning |
|---|---|---|
| `--duration` | 600 | Simulated seconds |
| `--warmup` | 120 | Seconds at the start that are left out of the results. Must be longer than one ride (see [Troubleshooting](#troubleshooting)) |
| `--dt` | 0.1 | Time step. Smaller values are slightly more precise and slower |

> **The defaults are guesses.** The spacing, walking speed and lane-switching
> values strongly affect the result and have not yet been checked against real
> observations. Treat the results as "what happens if people behave like this"
> and sweep the uncertain parameters rather than relying on one setting.

## Reading the results

| Column | Meaning |
|---|---|
| **Thru/min** | People reaching the top per minute after the warm-up. **This is the main measure for testing the theory** |
| **Wait avg s / Wait p95 s** | Time queueing at the bottom: the average, and the wait that 95% of people beat |
| **Trip avg s** | Time from joining the queue to reaching the top |
| **Max queue** | Longest total queue (both lanes) after the warm-up |
| **Queue end** | People still queueing when the run stops |
| **Walked** | Share of the people who reached the top that walked |
| **±** | 95% margin of error across the replications (only in `compare` and `sweep`) |

Things to keep in mind:

- **Throughput only differs when the escalator is overloaded.** If people arrive
  more slowly than the escalator can carry them, both strategies carry everyone
  and throughput simply equals the arrival rate. The strategies then differ only
  in waiting time. To test the theory, use rush-hour arrival rates, where
  **Queue end** is large.
- **Under overload, waits are a minimum.** People still in the queue at the end
  count with the time they've waited so far. A large and growing **Queue end**
  means the queue never stops growing, and the real waits keep rising with the
  run length.
- **Height doesn't change who walks yet.** In reality fewer people walk up tall
  escalators. Here the share is set by `--walk-fraction` alone, so when you
  sweep `rise`, also set the walk fraction you expect for that height.

## Saving results: JSON and CSV

`--output` prints to the screen; redirect it to save a file:

```bash
python3 -m escalator_sim compare -n 20 --output csv  > compare.csv
python3 -m escalator_sim sweep --param walk_fraction --values 0,0.25,0.5 --output csv > sweep.csv
python3 -m escalator_sim compare -n 20 --output json > compare.json
```

**CSV**
- `run` and `compare`: one row per individual run. The columns are `strategy`,
  `seed`, `throughput_per_min`, `wait_mean`, `wait_p95`, `wait_max`,
  `trip_mean`, `trip_p95`, `queue_mean`, `queue_max`, `queue_end`,
  `walked_share`, `arrived`, `finished`, `warmup_too_short`,
  `throughput_lane0`, `throughput_lane1`, … .
- `sweep`: one row per parameter value and strategy, with `<metric>_mean` and
  `<metric>_ci95` columns. In a sweep over `lanes`, the extra lane columns
  are added at the end and left empty for the rows with fewer lanes.

**JSON** contains everything, including the full settings used:

```text
compare:  { config, seeds, strategies: { <name>: { summary, runs[] } } }
sweep:    { config, param, seeds, points: [ { value, strategies: { <name>: { summary, runs[] } } } ] }
run:      { config, result }
```

In `summary`, each metric has the form `{ "mean": …, "ci95": …, "n": … }`.

## Recipes for testing the theory

```bash
# 1. The basic claim: rush hour, nobody switches lanes
python3 -m escalator_sim compare -n 20 --defect-prob 0

# 2. How many walkers does the walk lane need before stand-on-the-right pays off?
python3 -m escalator_sim sweep --param walk_fraction --values 0,0.1,0.2,0.3,0.4,0.5,0.6 \
    --defect-prob 0 -n 10 -j 0

# 3. A tall escalator (Holborn-like: 24 m rise), where about 45% walk at rush hour
python3 -m escalator_sim compare -n 20 --rise 24 --walk-fraction 0.45 --warmup 180 --duration 900

# 4. How much does lane switching rescue walk-left?
python3 -m escalator_sim sweep --param defect_prob --values 0,0.1,0.3,0.6 -n 10 -j 0

# 5. People standing in the walk lane
python3 -m escalator_sim sweep --param blocker_rate --values 0,0.05,0.1,0.2 -n 10 -j 0

# 6. How sensitive is the answer to the spacing?
python3 -m escalator_sim sweep --param walk_gap --values 0.6,0.9,1.2,1.6 -n 10 -j 0
python3 -m escalator_sim sweep --param stand_gap --values 0.4,0.8,1.2 -n 10 -j 0

# 7. From quiet to crowded
python3 -m escalator_sim sweep --param arrival_rate --values 30,60,90,120,150 -n 10 -j 0
```

Recipe 3 lengthens the warm-up because a 24 m rise makes a 64 s ride (see the
next section).

## Web interface

The browser interface lets you change settings and watch the strategies run.
It uses the same engine and gives the same numbers as the command line for
the same settings and seed.

**Start it** from the project folder:

```bash
python3 -m http.server 8000
```

Then open **http://localhost:8000/web/**.

- You need a web server; opening `web/index.html` directly as a file doesn't
  work, because browsers block the simulation worker on `file://` pages.
- On the first visit the page downloads the Python runtime (about 12 MB) from
  cdn.jsdelivr.net, and the chart library when you first run an experiment.
  After that they load from the browser cache.
- **In Docker:** the container must publish the port, e.g.
  `docker run -p 8000:8000 ...`. Otherwise the browser on your computer can't
  reach the server. `http.server` already listens on all network interfaces.
  If port 8000 is taken, use another number in both places.

The **Live** and **Experiments** buttons at the top switch views. Both use the
settings on the left. The animation pauses while Experiments is showing.

**Live view:**

| Area | What it does |
|---|---|
| Settings (left; below the animation on phones) | Every parameter, with its unit, a slider and help text. Changes are checked and restart the run after a short pause. Errors appear next to the field. The gray box shows calculated values: escalator length, ride time and lane capacities |
| Controls | Play/Pause (**Space**), Step +1 s, Restart, and speed (1×–50×). Tick or untick strategies. **Seed** picks the crowd, and **New crowd** picks a random seed |
| Escalators | One per strategy, seen from above, with the top of the escalator at the top. Every strategy gets the same crowd. Shapes show who is who: ● standing, ▲ walking, ◆ a stander who switched to walking, ■ standing in the walk lane. The queue is below each lane; a number like `97 (+57)` means 97 are queueing and 57 of them didn't fit in the drawing |
| Live numbers | People at the top, throughput over the last 60 s, queue per lane, average wait so far, and share walking |
| People at the top | A chart of how many people have reached the top over time, per strategy. The dashed line is everyone who has arrived. The shaded area is the warm-up |
| Results | When the run finishes, the same metrics as `run`, measured after the warm-up, side by side |

The live numbers include the warm-up and cover only one crowd. Use
Experiments (or `compare`) for conclusions over many crowds.

**Experiments view** runs `compare` or `sweep` in the browser:

| Area | What it does |
|---|---|
| Compare / Sweep | Compare averages every strategy over the same crowds. Sweep does that at each value of one setting |
| Strategies, Replications, First seed | Like `--strategies`, `-n` and `--seed`. The defaults are the command line's: 10 replications for Compare and 5 for Sweep. The line below the form says how many runs that is |
| Setting to vary (Sweep only) | Any parameter. Enter the values as a **Range** (from, to, step) or a **List** such as `0, 0.1, 0.25`. Up to 50 values. The swept values replace that setting from the panel on the left |
| Run / Cancel | A progress bar shows the runs done and the estimated time left. Cancel stops after the current slice of runs |
| Results | The command line's table, with mean ±95% margin of error. Compare adds the percentage difference and whether the throughput lead is bigger than the margins of error. Sweep shows the leader at each value, or `tie`, using the command line's rule |
| Charts | Compare: throughput and average wait per strategy, with error bars. Sweep: throughput and average wait against the swept value, with a shaded band for the margin of error |
| Download CSV / JSON | Exactly what `--output csv` / `--output json` prints for the same experiment, so files from either can be analyzed the same way |
| Watch this scenario | Opens the live view with that result's settings and its first seed. In a sweep, each row has its own **Watch** button |

As a rough guide, one 10-minute run takes about 0.15 s in the browser, so the
default compare (20 runs) takes a few seconds. Experiments run in a background
worker, so the page stays responsive.

## Using the engine from Python

The command line is a thin layer on top of the engine. Scripts, notebooks and the
web interface use the engine directly:

```python
from escalator_sim import Simulation, SimConfig, compare, sweep

config = SimConfig(arrival_rate=90, walk_fraction=0.2)

# Step through one simulation (this is how a visual front end would drive it)
sim = Simulation(config, strategy="walk-left", seed=1)
while not sim.done:
    sim.step()                     # advances config.dt seconds
    state = sim.snapshot()         # plain dict, see below
print(sim.results())               # same metrics as the `run` command

# Or run to the end in one call
result = Simulation(config, "stand-both", seed=1).run()

# Batch experiments return the same data as --output json
data = compare(config, ["stand-both", "walk-left"], replications=10)
data = sweep(config, "walk_fraction", [0, 0.25, 0.5], ["stand-both", "walk-left"], replications=5)

# Change settings without editing the original
taller = config.with_changes(rise=24, warmup=180, duration=900)
```

`snapshot()` returns:

```text
{ time, length, belt_speed, step_depth, strategy, arrived, finished,
  lanes: [ { index,
             people: [ {id, lane, pos, speed, walking, wants_to_walk}, ... ],   # on the belt, top first
             queue:  [ ...same fields... ] } ] }                                 # waiting, front first
```

`pos` is meters from the bottom along the incline, from 0 to `length`.

## Troubleshooting

**`WARNING: warm-up (20 s) is shorter than one standing ride (40 s), so throughput is underestimated.`**
For the first part of the measured window, nobody could have reached the top yet,
so throughput comes out too low. Set `--warmup` longer than one ride, which takes
`length ÷ belt_speed` (= 2 × rise ÷ belt_speed at 30°). A comfortable choice is
at least 1.5× that, and `--duration` should be several times the warm-up.

**`error: walk_fraction must be in [0, 1]`** (or a similar message)
A parameter is outside its valid range. The message names the parameter and the allowed range.

**`error: argument --param: invalid choice: ...`**
`--param` takes a parameter name with underscores (`walk_fraction`), not a flag
(`--walk-fraction`). Strategies can't be swept; use `--strategies` instead.

**`error: argument --lanes: invalid int value: '2.5'`** or **`error: lanes must be a whole number, got 2.5`**
Whole-number parameters (`lanes`, `defect_threshold`) can't take values like
`2.5`, either as a flag or in `sweep --values`.

**The results barely change between strategies.**
The escalator is probably not overloaded (see
[Reading the results](#reading-the-results)). Raise `--arrival-rate` until
**Queue end** is well above zero.

**It's slow.**
Use `-j 0` to run in parallel, reduce `-n`, or raise `--dt` to `0.2`. A single
default run takes about 0.1 s.

## Running the tests

```bash
python3 -m unittest discover -s tests
npm install && npm test
```

The Python tests check spacing, boarding, the lane-capacity calculation,
strategy behavior, reproducibility, the command line and the pieces the GUI
uses. `npm test` runs the engine inside Pyodide under Node, checks that its
results match native Python, and tests the web helper functions. It needs
Node.js 22 or newer; `npm install` downloads Pyodide for the tests only.
