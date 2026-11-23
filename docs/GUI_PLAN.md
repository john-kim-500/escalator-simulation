# GUI Plan: Configure and Visualize Runs

The goal is a browser interface where you can set every parameter, watch both
strategies run side by side on the same crowd, and run `compare`/`sweep`
experiments with charts. It follows the tech-stack decision in
[PLAN.md](PLAN.md#tech-stack): the existing Python engine runs **in the
browser through Pyodide**, and the page is static, so no server is needed.

## Goals

1. **Configure:** every `SimConfig` parameter as a labelled control with its
   units, valid range and a short explanation. Presets cover common scenarios.
2. **Watch:** an animation of both strategies running *at the same time on the
   same crowd*, with live numbers and a chart of how many people have reached the top.
3. **Experiment:** run `compare` and `sweep` from the page, with progress and a
   cancel button, and see the results as tables and charts with error bars.
4. **Share:** the settings are kept in the page URL, so a link reproduces a
   scenario. Results download as CSV or JSON, in the same format as the command line.

**Not in this plan:** editing strategies in the browser, multi-user features,
and any backend.

## Architecture

```
 Browser tab
 ┌──────────────────────────────────────────────┐      ┌────────────────────────────────┐
 │ Main thread (UI)                             │      │ Web Worker                     │
 │  index.html, app.js                          │ msgs │  sim-worker.js                 │
 │  ├ config panel (built from PARAM_INFO)      │◀────▶│  ├ Pyodide (CPython in WASM)   │
 │  ├ live view: canvases + live chart          │ JSON │  └ escalator_sim (unchanged    │
 │  └ experiments view: tables + charts         │      │      Python package)           │
 └──────────────────────────────────────────────┘      └────────────────────────────────┘
```

- **The engine runs in a Web Worker,** so the page never freezes during a long
  sweep. The worker loads Pyodide from a CDN and then loads the `escalator_sim`
  files straight from the repo, so there is exactly one copy of the engine.
- **The main thread only draws.** It never simulates anything.
  `requestAnimationFrame` asks the worker to advance and receives snapshots back.
- **Data goes over as JSON strings** (`json.dumps` in Python, `JSON.parse` in
  JS). This is faster and simpler than converting Python objects to JS ones.
- **Front end:** plain JavaScript modules and HTML canvas, with no framework and
  no build step. The one library is **Chart.js**, at a pinned version from
  jsDelivr, for the experiment charts. The live chart is simple enough to draw
  directly on canvas.
- **The Pyodide version is pinned** to an exact release chosen when this is
  built. Pyodide 0.26+ ships Python 3.12, and the engine needs 3.10+.

### Files

```
web/
  index.html          # layout, loading screen
  style.css           # light/dark theme tokens, responsive layout
  app.js              # app state, view switching, URL state
  sim-worker.js       # loads Pyodide + escalator_sim, implements the protocol
  worker-client.js    # promise-based wrapper around postMessage
  config-panel.js     # builds controls from PARAM_INFO; presets; validation messages
  live-view.js        # animation loop, playback controls
  escalator-canvas.js # draws one strategy's escalator from a snapshot
  live-chart.js       # people-at-the-top-over-time chart (canvas)
  experiments-view.js # compare/sweep forms, progress, tables, downloads
  experiment-charts.js # Chart.js loader, bar charts with error bars, sweep bands
  experiment-util.js  # pure helpers: sweep ranges, time left, formatting
  dom.js              # tiny element-building helper shared by the views
  manifest.json       # list of escalator_sim/*.py files for the worker to load
tests/
  test_web_support.py # engine additions + manifest matches the package
web/tests/            # node --test unit tests for pure JS (URL state, scaling, formatting)
```

### Messages between the page and the worker

| Request | Reply | Purpose |
|---|---|---|
| `init` | `ready {version, param_info, strategies, presets}` | Load Pyodide and the engine; send the parameter details the UI is built from |
| `validate {config}` | `ok` or `error {field, message}` | Check settings with the same `SimConfig` rules the command line uses |
| `live.start {config, strategies, seed}` | `snapshot` | Create one `Simulation` per strategy with the **same seed**, so both get the same crowd |
| `live.advance {seconds}` | `snapshot {time, sims: [...], stats}` | Advance every simulation by the same simulated time |
| `exp.run {kind, config, ...}` | `progress {done, total}` … `result {...}` | Run compare/sweep one job at a time and report progress |
| `exp.cancel` | `cancelled` | Stop after the current job |

The worker answers one request at a time. Cancelling works because a long
experiment returns control between jobs, so the worker can read the cancel
message.

## Changes needed in the engine

These are small additions that keep to the engine rules in PLAN.md: standard
library only, plain data, no I/O. Each comes with unit tests.

1. **Parameter details in `config.py`: `PARAM_INFO`.** For each parameter: its
   label, unit, group, min, max, step, and a one-line help text. The GUI builds
   its controls from this, and the command line's `--help` can use it too, so
   the two never disagree. Also add **`PRESETS`**: *Defaults*, *Rush hour*,
   *Off-peak*, *Tall escalator (Holborn-like)*, *Nobody switches lanes*.
2. **Who-is-who in `snapshot()`.** Add a `kind` field to each person:
   `stander`, `walker`, `defector` (a stander who switched to walking) or
   `blocker` (standing in the walk lane). The strategy supplies it, so this logic
   stays in Python rather than being worked out again in JS.
3. **A limit on queue detail in `snapshot()`.** An overloaded run can have
   hundreds of people queueing. The snapshot gives the first *N* people in full
   and the total queue length as a number, so the size of each frame stays small.
4. **Live statistics.** Add a cheap `live_stats()` that keeps running counts:
   people at the top so far, current throughput over the last 60 s, queue
   lengths, and average wait so far. Calling `results()` every frame would
   re-scan everyone.
5. **Experiments that can be split up.** Split `compare`/`sweep` into
   `plan_*() → jobs`, `run_one(job)` and `collect_*(jobs, runs)`. The command
   line keeps calling `compare()`/`sweep()`, which use these internally. The
   worker calls the pieces one job at a time, which is what makes progress and
   cancelling possible.

## Screens

### Layout (desktop; on narrow screens the panels stack)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Escalator Simulator            [ Live ] [ Experiments ]      Preset: Rush ▾ │
├────────────────────┬────────────────────────────────────────────────────────┤
│ ▾ Escalator        │   stand-both                  walk-left                │
│   Rise   [15 ] m   │   ┌──────┬──────┐            ┌──────┬──────┐          │
│   Belt  ─●── 0.75  │   │ ●    │  ●   │  ▲ top     │  ◆   │ ●    │          │
│ ▾ Crowd            │   │   ●  │ ●    │            │ ◆    │   ●  │          │
│   Arrivals ─●─ 120 │   │ ●    │   ●  │            │   ◆  │ ●    │          │
│   Walk %  ●── 25%  │   └──────┴──────┘  bottom    └──────┴──────┘          │
│ ▸ Spacing          │    queue: 41 | 40             queue: 12 | 97           │
│ ▸ Behaviour        │   112 /min  wait 22 s         95 /min  wait 41 s       │
│ ▸ Run              │                                                        │
│                    │   People at the top ─────────────────────────────      │
│ Seed [1] [New]     │    ── stand-both   ── walk-left    (lines diverge)    │
│                    │                                                        │
│ ⚠ warm-up < ride   │   ⏮ ⏯ ⏭   Speed: 1× 2× 5× 10× 50×   t = 03:12        │
└────────────────────┴────────────────────────────────────────────────────────┘
```

### Configuration panel (both screens)
- The parameters are grouped as in `SimConfig`: Escalator, Crowd, Spacing,
  Behaviour, Run. Each has a slider plus a number box, with its unit and help text.
- Values are checked by the engine itself. Errors show next to the field, using
  the same messages as the command line.
- Calculated values are shown next to the settings: escalator length, ride time
  and the capacity of each lane (`belt ÷ gap × 60`). The warm-up warning from the
  command line appears here too.
- Behaviour settings that only matter for `walk-left` are labelled as such.
- Changing a setting during the live view restarts the run, after a short pause
  so that dragging a slider doesn't restart it on every pixel.

### Live view
- **One escalator per strategy, side by side, same seed.** The crowds are
  identical, so any difference you see comes from the strategy.
- **Drawing:** a **top-down** view of the escalator, with the bottom at the
  bottom and the lanes as columns, so both lanes are clearly visible. A side view
  would hide one lane behind the other. Steps are drawn as faint lines that move
  with the belt.
- **Who is who:** standers, walkers, defectors and blockers each get a distinct
  colour **and** shape, so they can be told apart without relying on colour.
  The queue is a cluster below the escalator. When it's longer than the drawing
  limit, it ends in a "+137" label.
- **Live numbers per strategy:** throughput over the last 60 s, total queue,
  average wait so far, and the share of people walking.
- **Live chart:** people who have reached the top over time, for both
  strategies on the same axes. When the escalator is overloaded the lines visibly
  split apart, which makes the case for or against the theory in one picture.
- **Controls:** play/pause, step forward, reset, speed (1×–50×), and a new
  random crowd. Space bar plays and pauses.

### Experiments view
- Choose **Compare** or **Sweep**, the strategies, the number of replications
  and the first seed. For Sweep, also choose the parameter and its values, which
  can be entered as a list or as a from/to/step range.
- A progress bar with an estimated time left and a Cancel button.
- **Compare results:** the same table as the command line, with means and 95%
  margins of error, plus a bar chart of throughput and average wait with error bars.
- **Sweep results:** line charts of throughput and wait against the swept
  parameter, one line per strategy, with a shaded band for the margin of error.
  A row of labels shows which strategy wins at each value, or "tie", using the
  same rule as the command line.
- Download the results as **CSV/JSON in the same format as `--output`**, so files
  from the GUI and the command line can be analysed the same way.
- A **"Watch this scenario"** button on any result opens it in the live view
  with the same settings and seed.

## Performance

These are estimates to check during milestone 2.

- **Live view:** a native run of 600 simulated seconds takes about 0.1 s.
  Pyodide is typically 1.5–3× slower than native Python. Even at 50× speed with
  two simulations, that is roughly 25–50 ms of computing per real second, so
  there is plenty of room. Snapshots take under 1 ms natively, even with 300+
  people queueing.
- **Experiments:** a sweep of 5 values × 2 strategies × 10 replications is 100
  runs, roughly 20–40 s in a single worker. The progress bar makes that
  bearable. If it turns out too slow, a pool of workers is the follow-up (see
  milestone 6), at a cost of about 50–100 MB of memory per worker.
- **First load:** Pyodide is about 10 MB, and the browser keeps it cached after
  the first visit. A loading screen shows progress.

## Running and hosting

- **Locally:** run `python3 -m http.server 8000` from the repository root, then
  open `http://localhost:8000/web/`. It needs an HTTP server rather than opening
  the file directly, because browsers block workers and file fetches on `file://`.
  - **In Docker:** the container must publish the port (`-p 8000:8000`).
    `http.server` already listens on all network interfaces.
  - It needs internet access for the Pyodide and Chart.js downloads, unless they
    are bundled into the repo later.
- **GitHub Pages (optional):** a small GitHub Actions workflow could publish
  `web/` and `escalator_sim/`. **Note:** the repository is private, and Pages
  for private repos needs a paid GitHub plan. Otherwise it stays local-only, or
  the repo is made public.

## Testing

- **Python:** unit tests for `PARAM_INFO` (every parameter is described, the
  ranges include the defaults, presets are valid), the snapshot `kind` field and
  queue limit, `live_stats()`, and splitting experiments into jobs (the result
  must match `compare()`/`sweep()` exactly). A test also checks that
  `web/manifest.json` lists every file in `escalator_sim/`.
- **JavaScript:** `node --test` for the pure functions: URL encoding of
  settings, coordinate scaling, number formatting and sweep-range parsing.
- **In the browser:** a short manual checklist per milestone: it loads, runs
  both strategies, the numbers match the command line for the same seed,
  cancelling works, and the layout works at phone width and in light and dark
  themes. Automated browser tests (Playwright) can be added later if this becomes
  tedious.
- **Matching the command line:** for one fixed seed, the throughput shown in the
  GUI must equal `python3 -m escalator_sim run` exactly. This is the strongest
  check that the browser runs the same engine.

## Milestones

1. ✅ **Engine additions:** `PARAM_INFO`, `PRESETS`, the snapshot `kind` field and
   queue limit, `live_stats()`, and split experiments, with tests. The command
   line keeps working unchanged.
2. ✅ **Web skeleton:** `index.html`, the worker loading Pyodide and the package,
   the loading screen, and one headless run whose results appear on the page.
   Check the performance estimates.
3. ✅ **Live view** *(checked in Firefox)*: the configuration panel built from `PARAM_INFO`, two
   escalators side by side, playback controls, live numbers and the live chart.
4. ✅ **Experiments view** *(built and tested in Node and jsdom; not yet checked in a real browser)*:
   compare and sweep with progress and cancel, tables, charts, CSV/JSON
   download, and "Watch this scenario".
5. **Polish:** presets, settings kept in the URL, phone-width layout, dark mode,
   keyboard controls, and a short "how to read this" help panel.
6. *(Optional)* A pool of workers for faster sweeps, bundling Pyodide for
   offline use, and the GitHub Pages workflow.

## Decisions

Confirmed on 2026-11-20.

| Question | Decision |
|---|---|
| Where it runs | Locally with `http.server` for now. GitHub Pages only if you upgrade your plan or make the repo public |
| Drawing style | Top-down view of the lanes, clearest for two lanes. A decorative side view could come later |
| Live view default | Both strategies side by side on the same crowd |
| Front end | Plain JS with no build step, plus Chart.js for experiment charts. Move to a framework only if the UI grows a lot |
| First target | Live view first (milestones 1–3), then experiments |
