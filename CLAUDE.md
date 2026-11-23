# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Agent-based simulation testing whether an escalator moves more people when everyone stands on both sides (`stand-both`) than with stand-right/walk-left (`walk-left`). Design rationale is in `docs/PLAN.md`; how the browser GUI and the engine fit together is in `docs/APP_DESIGN.md`; how the engine runs each step is in `docs/ENGINE_DESIGN.md`; the GUI milestone status is in `docs/GUI_PLAN.md`; user-facing docs are in `docs/USAGE.md`; studies and real-world data (with how carefully each has been checked) are in `docs/RESEARCH.md`; the plan for measuring time saved by people who want to walk is in `docs/TIME_SAVED_PLAN.md`, and its results at the Holborn settings are in `docs/FINDINGS.md` (tables made by `docs/findings.py`), with a short version in `docs/FINDINGS_SUMMARY.md`. All documentation except this file and `README.md` lives in `docs/`.

## Directives

- **Commits and PR titles:** use semantic style, `type: summary` (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`). The PR title becomes the merge commit title.
- **Documentation language:** when writing or reviewing docs, use business English with American spelling and usage.
- **Be terse:** prefer short, direct sentences. Cut filler and repetition.
- **No jargon:** readers may know software, math or civil engineering, but not all three. Avoid terms from any of them (e.g. "deque", "O(n)", "Poisson process", "headway", "throughput"). Say it plainly: "people per minute", "minimum time between two people stepping on". Code names are fine in `code font` with a plain explanation.

## Coding standards

These describe how the existing code is written. Follow them in new code. `npm run lint` checks line length, type hints, quotes and `var` (Ruff for Python, ESLint for JavaScript); GitHub runs it and both test suites on every pull request (`.github/workflows/checks.yml`).

**All code**
- Lines are 100 characters or less. URLs and strings that can't be split are the only exceptions.
- Every file opens with a short comment or docstring saying what it is for.
- Comments explain why, not what. Keep them short.
- Spelling in comments and on-screen text is American. Don't rename existing code names just to fix spelling.
- Errors shown to users are short, lowercase and say what to fix (e.g. `"walk-left needs at least 2 lanes"`).
- New behavior comes with a test. Keep tests fast (`duration=180, warmup=60`).

**Python**
- Start each module with `from __future__ import annotations`. Add type hints to function arguments and return values.
- Double quotes. `snake_case` for functions and variables, `PascalCase` for classes, `UPPER_CASE` for constants. Prefix internal names with `_`.
- Raise `ValueError` for bad input. Settings checks collect every problem and report them together, not one at a time.
- Tests use `unittest`, grouped into classes by topic.

**JavaScript**
- ES modules with named exports. `const` by default, `let` when the value changes, never `var`.
- Double quotes, semicolons, two-space indent. `camelCase` for functions and variables, `PascalCase` for classes, `UPPER_CASE` for constants.
- `/** ... */` comments on exported functions and on anything non-obvious.
- Use `el()` from `dom.js` to build page elements.
- Tests use `node:test` with `node:assert/strict`.

## Commands

```bash
python3 -m unittest discover -s tests                          # all Python tests (pytest is NOT installed)
python3 -m unittest tests.test_engine.Capacity                 # one test class
python3 -m unittest tests.test_engine.Capacity.test_board_headway_limits_capacity  # one test
npm install && npm test                                        # JS tests: runs the real engine in Pyodide under Node (Node 22+)
node --test web/tests/helpers.test.mjs                         # one JS test file
pip install -r requirements-dev.txt && npm run lint            # style checks (Ruff + ESLint)
npm run lint:fix                                               # fix what the checkers can, list the rest

python3 -m escalator_sim compare -n 20                         # CLI; see --help on run/compare/sweep
python3 -m http.server 8000                                    # from repo root, then open http://localhost:8000/web/
python3 -m docs.findings > findings.md                         # remake the tables in docs/FINDINGS.md (~3 min)
```

There is no build step and no automatic formatter. `npm run lint:fix` fixes quotes, import order, `let`/`const` and indentation; fix the rest (mostly long lines and type hints) by hand. The web GUI is plain ES modules served as static files. Style settings live in `pyproject.toml` (Ruff only; it is not a package build file) and `eslint.config.js`.

## Architecture

One Python engine (`escalator_sim/`) serves both the CLI and the browser. The browser runs the *same unchanged package* inside Pyodide in a Web Worker; there is deliberately no JS copy of the engine.

### Engine rules (required for Pyodide compatibility)
- Standard library only (no numpy). Python 3.10+.
- Plain, JSON-serializable data in and out (dicts, lists, numbers).
- No threads, file I/O or `time.sleep` in the engine; the caller drives the loop via `Simulation.step()`. File output and terminal formatting belong in `cli.py`/`report.py`.

### Python package
- `config.py`: `SimConfig` is one flat frozen dataclass; each field maps one-to-one to a CLI flag (`walk_fraction` → `--walk-fraction`), a sweep parameter and a GUI control. `PARAM_INFO` (label, unit, group, min/max/step, help) and `GROUPS` drive both the CLI `--help` and the GUI's config panel, and `PRESETS` holds the named scenarios. **Adding a parameter means updating the dataclass, `PARAM_INFO`, and validation**; tests check that every field is described and that ranges contain defaults.
- `draws.py`: every random number. `Draws(seed)` hashes (seed, purpose, person number), so no draw depends on another or on order. **Never rename or re-key an existing purpose** (it changes every seed's crowd); add a new purpose constant instead. Don't use `random` in the engine except to pick a seed.
- `strategies.py`: `Strategy` subclasses registered with `@register`; `choose(person, queue_lengths, draws)` returns `(lane, walking)` on arrival and `kind()` labels people for display (`stander`/`walker`/`defector`/`blocker`). Lane 0 is the walk (left) lane.
- `engine.py`: `Simulation(config, strategy, seed)` with `step()`, `run()`, `snapshot(max_queue)`, `live_stats()` (cheap running counts for per-frame use) and `results()`.
- `experiments.py`: `compare`/`sweep` are built from `plan_*() → jobs`, `run_one(job)`, `collect(plan, runs)`. The split lets the worker run one job at a time for progress and cancel. All strategies get the same seeds, so they face identical arrivals.
- `session.py`: the JSON-string API (`Session`) the browser calls. Every method takes and returns JSON strings; `dumps()` turns non-finite floats into `null` because `JSON.parse` rejects them.
- `report.py`: CSV/JSON output and the winner/tie rule, shared by CLI and GUI so downloads match `--output`.

### Web (`web/`)
- `engine-core.js` loads Pyodide, writes the package files listed in `web/manifest.json` into Pyodide's FS, and wraps `Session`. It is shared by `sim-worker.js` (browser) and `web/tests/engine.test.mjs` (Node), so both use identical loading code. **When adding or removing a `.py` file in `escalator_sim/`, update `web/manifest.json`** (`tests/test_web_support.py` enforces this).
- The Pyodide version is pinned in two places: `PYODIDE_VERSION` in `engine-core.js` and the `pyodide` devDependency in `package.json`. Keep them in sync.
- `sim-worker.js` speaks a `{id, type, args}` → `{id, ok, result|error}` protocol (`info`, `check`, `live.*`, `exp.run`, `exp.cancel`); `worker-client.js` is the promise wrapper on the main thread. The main thread only draws and never simulates.
- Pure helpers (formatting, layout, sweep ranges) live in separate modules so `node --test` can test them without a browser.
- Chart.js is the only front-end library, loaded at a pinned version from jsDelivr.

### Cross-checks to preserve
- `tests/test_engine.py` pins a few `Draws` values; if they change, every seed's results changed.
- For a fixed seed, GUI/Pyodide results must equal native `python3 -m escalator_sim run`. Pyodide ships Python 3.14, whose float summation differs slightly from 3.11, so the Node test compares counts exactly and averages with a tolerance.
- The warm-up must exceed one ride (`length / belt_speed`), otherwise metrics carry a warning. Tests use `duration=180, warmup=60` for speed.
