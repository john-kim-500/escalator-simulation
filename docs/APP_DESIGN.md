# Design: how the GUI and the engine fit together

This document explains how the parts of the simulator talk to each other. For
*why* the model is built the way it is (movement rules, parameters,
calibration), see `PLAN.md`. For the GUI's milestones, see `GUI_PLAN.md`.

## The big idea: one engine, two front ends

There is exactly one simulation engine: the Python package `escalator_sim/`.
The command line runs it with normal Python. The browser runs the **same,
unchanged files** inside [Pyodide](https://pyodide.org) (Python compiled to
WebAssembly), inside a Web Worker. There is no JavaScript copy of the engine.

That one decision shapes the rest of the design:

- Results can't drift between the CLI and the GUI, because they run the same
  code. For a fixed seed, they give the same numbers (tested; see
  [Cross-checks](#cross-checks)).
- The engine must work in Pyodide. That means standard library only, no
  threads, no file I/O and no sleeping. The caller decides when time advances.
- Everything that crosses between JavaScript and Python is a **JSON string**,
  so neither side ever holds the other's objects.

```
 ┌───────────────────────── Browser: main thread ─────────────────────────┐
 │  index.html → app.js                                                   │
 │    ConfigPanel ─────┐                                                  │
 │    LiveView ────────┼──► EngineClient (worker-client.js)               │
 │    ExperimentsView ─┘        promise per request, by id                │
 └──────────────────────────────────┬─────────────────────────────────────┘
                 postMessage {id, type, args}   ▲ {id, ok, result|error}
                                    ▼           │ {type: "status"|"progress"|"fatal"}
 ┌──────────────────────────── Web Worker ────────────────────────────────┐
 │  sim-worker.js   handlers: info, check, live.*, exp.run, exp.cancel    │
 │      │                                                                 │
 │  engine-core.js  loadEngine(): starts Pyodide, copies the .py files    │
 │      │           in manifest.json into its file system, wraps Session  │
 │      ▼           JSON strings in and out                               │
 │  ┌─────────────── Pyodide (Python 3.14 in WebAssembly) ─────────────┐  │
 │  │ escalator_sim.session.Session  ◄── the only entry point from JS  │  │
 │  │   ├─ config      SimConfig, PARAM_INFO, PRESETS, validation      │  │
 │  │   ├─ engine      Simulation: step / snapshot / live_stats        │  │
 │  │   ├─ experiments plan_* → jobs, run_one, collect                 │  │
 │  │   └─ report      winners, CSV, JSON                              │  │
 │  └──────────────────────────────────────────────────────────────────┘  │
 └────────────────────────────────────────────────────────────────────────┘

 ┌──────────────────────────── Command line ──────────────────────────────┐
 │  python3 -m escalator_sim → cli.py → config / engine / experiments /   │
 │                                      report  (same modules as above)   │
 │  Experiments can run in a ProcessPoolExecutor (--jobs)                 │
 └────────────────────────────────────────────────────────────────────────┘
```

## Layers and what each one owns

| Layer | Files | Owns | Never does |
|---|---|---|---|
| Model | `config.py`, `person.py`, `strategies.py`, `engine.py`, `metrics.py` | The simulation and its statistics | I/O, timing, formatting |
| Batch runs | `experiments.py` | Splitting experiments into independent jobs and putting the results back together | Deciding *how* jobs run |
| Output | `report.py` | Winner/tie rule, CSV and JSON text | Printing or saving files |
| Front-end API | `session.py` | One front end's state; JSON in and out | Anything the CLI also needs (that lives lower down) |
| CLI | `cli.py`, `__main__.py` | Argument parsing, terminal tables, process pool, writing files | Simulation logic |
| Worker | `sim-worker.js`, `engine-core.js` | Loading Pyodide, the message protocol, running experiments in slices | Drawing, DOM |
| Main thread | `app.js`, `*-view.js`, `config-panel.js`, canvases, charts | Drawing and user input | Simulating |
| Pure helpers | `format.js`, `experiment-util.js`, layout functions in `escalator-canvas.js` | Formatting, sweep ranges, layout maths | Touching the DOM or the worker (so Node can test them) |

### The engine is driven from outside

`Simulation` has no loop of its own that needs to own the clock:

- `step()` advances one `dt`.
- `run(until)` just calls `step()` repeatedly.
- `snapshot(max_queue)` returns everyone's position for drawing.
- `live_stats()` returns cheap running counts, safe to call every frame.
- `results()` returns the full summary (excludes the warm-up).

All of them return plain dicts and lists. The CLI calls `run()`. The browser
calls `step()` a few at a time between animation frames. Nothing in the engine
knows which one is happening.

### The engine describes itself

The GUI doesn't hard-code any parameter. `Session.info()` sends:

- `defaults`, plus `param_info`: label, unit, group, min/max/step, help text,
  and `only_for` (which strategies a parameter applies to)
- `groups` and `presets`
- `strategies` (names and descriptions)
- `kinds` (stander, walker, defector, blocker, with display labels)

`ConfigPanel` builds every slider from that. So a new field in `SimConfig` with
a `PARAM_INFO` entry appears in the CLI's `--help`, as a sweep parameter and in
the GUI, with no JavaScript changes. Likewise, a new `@register`ed strategy
appears as a checkbox in both views.

Validation lives only in Python as well. `Session.check()` returns
`{ok, errors: [{field, message}], warnings, derived, config}`, and the panel
just shows the messages next to the named fields. Because of this, the GUI and
the CLI reject the same inputs with the same wording.

## The worker protocol

Requests from the main thread look like `{id, type, args}`. Every request gets
exactly one final reply, `{id, ok: true, result}` or `{id, ok: false, error}`.
The worker can also send these messages, which aren't replies:

| Message | When |
|---|---|
| `{type: "status", message}` | While Pyodide and the package load |
| `{type: "fatal", error}` | Loading failed; every pending request is rejected |
| `{id, type: "progress", done, total}` | During `exp.run`; sent to that request's progress callback |

| Request | Session method | Used by |
|---|---|---|
| `info` | `info()` (plus the Pyodide version) | `app.js` at start-up |
| `check` | `check(values, strategies)` | `app.js` on every settings change |
| `live.start` | `live_start(values, strategies, seed, max_queue)` | `LiveView.restart()` |
| `live.advance` | `live_advance(seconds, max_queue)` | `LiveView.tick()` / "Step +1 s" |
| `live.results` | `live_results()` | `LiveView.finish()` |
| `exp.run` | `exp_start`, then `exp_step` repeatedly, then `exp_result` | `ExperimentsView.run()` |
| `exp.cancel` | sets a flag that `exp.run` checks between slices | `ExperimentsView.cancel()` |

`EngineClient` (`worker-client.js`) turns this into
`client.request(type, args, onProgress) → Promise`.

Python exceptions are cut down to their last line: `pythonErrorMessage` turns
`ValueError: rise must be > 0` into `rise must be > 0`. That text reaches the
UI as a rejected promise.

`dumps()` in `session.py` turns `inf` and `NaN` into `null`, because
`JSON.parse` would reject them.

## How the pieces interact

### Start-up

1. `app.js` refuses to run from `file://`, because browsers block module
   workers there.
2. It creates `EngineClient`, which starts `sim-worker.js`.
3. The worker imports Pyodide from jsDelivr (pinned version) and calls
   `loadEngine()`. That reads `web/manifest.json`, fetches each listed `.py`
   file from `../escalator_sim/`, writes it into Pyodide's file system, and
   creates a single `Session`. Status messages update the loading screen.
4. `app.js` sends `info` and builds `ConfigPanel`, `LiveView` and
   `ExperimentsView` from the reply.
5. It checks the default settings, which starts the first live run.

The worker starts loading as soon as it's created. Requests sent before loading
finishes wait on the same `ready` promise.

### Changing a setting

```
ConfigPanel (debounced edit)
  → app.applySettings(values)
  → client.request("check", {values, strategies})
  → ConfigPanel.showCheck(result)      field errors, warnings, derived values
  → ExperimentsView.settingsChanged()  re-validates its form and summary
  → result.ok ? LiveView.start(result.config) : LiveView.stop()
```

A sequence number throws away replies to older edits, so fast slider drags
can't apply stale settings. The live view starts from `result.config`, which is
the engine's normalised copy, not the raw form values. The experiments view
reads the same last check result through `getSettings()`, so both views always
use the settings shown in the panel.

### The live view (animation)

`Session` can hold several simulations at once: one per selected strategy, all
with the same seed. The same seed means the same crowd (see
[Determinism](#determinism)).

```
requestAnimationFrame → LiveView.tick
  owed += frame time × speed      (capped, so a slow device doesn't build a backlog)
  if not busy and owed ≥ dt:
      client.request("live.advance", {seconds: owed, maxQueue: 80})
        → Session advances every sim to the same time, in whole steps only
        → {time, done, sims: [{strategy, snapshot, stats}]}
      owed −= time actually advanced
      EscalatorCanvas.update(snapshot); stats table; LiveChart history
  when done: client.request("live.results") → results table
```

Points to note:

- **At most one request is in flight.** The `busy` flag stops a second
  `live.advance` from being sent before the first one returns. That makes the
  worker set the pace, and requests never pile up.
- **Whole steps only.** `live_advance` never goes past the requested time.
  Whatever is left over stays in `owed`, so the simulated time shown matches
  what the user asked for at any speed.
- **Limited data per frame.** Snapshots list at most `maxQueue` queueing people
  per lane, plus the full count. Per-frame numbers come from `live_stats()`
  (running counters), not `results()`.
- **Generations.** Every restart increases `generation`, and replies from an
  older generation are ignored. That covers restarts, seed changes, strategy
  changes and invalid settings.
- **Hidden view.** The animation stops advancing while the Experiments tab is
  showing (`setActive(false)`). The run is kept and continues when the user
  switches back.

### Experiments (compare and sweep)

Experiments are many independent full runs. In `experiments.py`, each one is
split into three steps:

```
plan = plan_compare(...) or plan_sweep(...)   # {kind, ..., jobs: [(config dict, strategy, seed), ...]}
runs = [run_one(job) for job in plan["jobs"]] # how the jobs run is up to the caller
data = collect(plan, runs)                    # summaries with confidence intervals
```

The two front ends run the middle step differently:

- **CLI:** `compare()` and `sweep()` take a `map_fn`. With `--jobs`, that's a
  `ProcessPoolExecutor`, so the jobs run in parallel.
- **Browser:** `Session` keeps the plan and calls `run_one` in time-limited
  slices:

```
ExperimentsView.run → request("exp.run", {spec}, onProgress)
  worker: runExperiment(engine, spec)
    expStart(spec)            → validates, plans → {done: 0, total}
    loop:
      await setTimeout(0)     ← lets an "exp.cancel" message be handled
      if cancelled: expCancel() → {cancelled: true}
      expStep(0.2)            → runs jobs for about 0.2 s → {done, total} → progress message
    expResult()               → {data, winners, csv, json}
```

The `setTimeout(0)` pause matters. A Web Worker handles one message at a time,
so the cancel message can only arrive while `exp.run` is waiting. For the same
reason, a cancel stops the experiment at the next slice boundary (within about
0.2 s), not partway through a run.

`exp_result` returns the CSV and JSON text made by `report.py`. Those are the
same functions behind `--output csv|json`. The "Download" buttons save exactly
that text, so a GUI download is identical to the CLI output for the same
settings.

### From an experiment to the live view

Each result table has a "Watch this scenario" button. It calls
`onWatch({config, seed, strategies})` in `app.js`, which:

1. sets the live view's seed and strategies (`setScenario`)
2. switches to the Live tab
3. calls `ConfigPanel.setValues(config)`

`setValues` goes through the normal check-then-start path above. The animation
then shows the first replication's crowd with exactly the settings the
experiment used.

## State: who holds what

| State | Lives in | Notes |
|---|---|---|
| Form values, slider positions | `ConfigPanel` | Only becomes settings after `check` passes |
| Last valid settings | `app.js` (`lastCheck`) | Shared with `ExperimentsView` |
| Live simulations | `Session.sims` in the worker | Replaced on every `live.start` |
| Seed, speed, play/pause, history for the chart | `LiveView` | History is rebuilt on restart |
| Experiment plan and finished runs | `Session._plan`, `_runs` | One experiment at a time; cleared by cancel or by the next start |
| Last experiment result | `ExperimentsView.last` | Used for redrawing charts (e.g. a theme change) and downloads |

Nothing is saved between page loads.

## Determinism

`Simulation` uses two separate random streams, both seeded from the run's seed:

- **Arrivals** (`"arrivals-{seed}"`): arrival times, who wants to walk, and
  walking speeds. Always drawn in the same order.
- **Behaviour** (`"behaviour-{seed}"`): strategy decisions such as defecting
  and blocking.

Strategies differ only in how they use the behaviour stream. So with the same
seed, every strategy faces **the same crowd**. That's what makes the
side-by-side animation and the compared experiments a fair like-for-like test.
Experiments use seeds `seed, seed+1, …` for every strategy.

## Cross-checks

These tests guard the boundaries described above:

- `tests/test_web_support.py`:
  - `Session` matches direct `Simulation`/`compare`/`sweep` calls (including
    experiments run in slices).
  - The live view's lockstep and no-overshoot rules hold.
  - Errors name the problem.
  - Every parameter is described and every preset is valid.
  - `web/manifest.json` lists every module in `escalator_sim/`.
- `web/tests/engine.test.mjs`: loads the real package into Pyodide under Node,
  using the same `loadEngine()` as the browser, and compares results with
  native `python3 -m escalator_sim`. Counts must match exactly. Averages may
  differ in the last digits, because Pyodide's Python 3.14 sums floats
  differently from 3.11.
- `web/tests/helpers.test.mjs`: the pure JavaScript helpers.
- `tests/test_calibration.py`: checks the engine against measured London
  Underground flows. It uses explicit settings, so it keeps working if the
  defaults change.

## Making common changes

| Change | Touch | Front ends pick it up through |
|---|---|---|
| New parameter | `SimConfig` field, `PARAM_INFO` entry, validation | `info` → config panel, sweep list, CLI flags |
| New strategy | `Strategy` subclass with `@register` in `strategies.py` | `info.strategies` → checkboxes in both views, CLI choices |
| New per-person label | `KINDS` plus the strategy's `kind()`, then a `--kind-*` colour and a shape in `escalator-canvas.js` | `info.kinds` → legend |
| New result metric | `metrics.summarize` / `aggregate`; columns in `report.py` | CSV/JSON automatically; GUI tables list their metrics explicitly |
| New engine module | Add the `.py` file **and** add it to `web/manifest.json` | Pyodide file system on load |
| New worker request | A `Session` method, a wrapper in `engine-core.js`, a handler in `sim-worker.js` | `client.request(type)` |
| Pyodide upgrade | `PYODIDE_VERSION` in `engine-core.js` **and** the `pyodide` dev dependency in `package.json` | Both must match |
