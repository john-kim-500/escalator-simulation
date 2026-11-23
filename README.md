# Escalator Simulator

An agent-based simulation that tests whether an escalator moves more people when
everyone **stands on both sides** (`stand-both`) than with the usual **stand
right, walk left** convention (`walk-left`). See [docs/PLAN.md](docs/PLAN.md) for the design
and the reasons behind it.

Requires Python 3.10+ (run as `python3`) and only the standard library.

**Full guide: [docs/USAGE.md](docs/USAGE.md)**, covering every command and
parameter, how to read the results, JSON/CSV output, recipes for testing the
theory, and troubleshooting.

## Web interface

```bash
python3 -m http.server 8000      # from the project folder
```

Then open http://localhost:8000/web/. You can change any setting and watch both
strategies run side by side on the same crowd, or run comparisons and sweeps
over many crowds, with charts and CSV/JSON downloads. The simulator runs entirely in
your browser through Pyodide, and needs internet access on first load to
download the Python runtime. In Docker, start the container with
`-p 8000:8000`. See [docs/USAGE.md](docs/USAGE.md#web-interface) for details.

**After updating the code**, the browser may keep using old copies of some
files, because `http.server` doesn't tell it when to check for new ones. If
the page says "The simulator could not start" with an `ImportError`, clear the
site's data for that address (or open it in a private window) and reload.
While working on the page, tick **Disable cache** in the browser's developer
tools (Network tab).

## Command line

```bash
python3 -m escalator_sim strategies                       # list strategies
python3 -m escalator_sim run --strategy stand-both        # one run
python3 -m escalator_sim compare -n 20                    # both strategies, same 20 crowds
python3 -m escalator_sim sweep --param walk_fraction --values 0,0.1,0.25,0.5 -n 10 -j 0
python3 -m escalator_sim compare --help                   # every parameter with its default
```

- Every parameter in `escalator_sim/config.py` is a flag, e.g. `--arrival-rate 90 --rise 24`.
- `--output json|csv` prints machine-readable results, e.g. `> results.csv`.
- `-j N` runs replications in parallel (`-j 0` uses all CPUs).
- `compare` and `sweep` give the same seeds to every strategy. Every strategy
  therefore faces exactly the same arrivals, so the differences come from the
  strategy rather than from luck.

## Using the engine directly (e.g. from a GUI)

```python
from escalator_sim import Simulation, SimConfig

sim = Simulation(SimConfig(arrival_rate=90), strategy="walk-left", seed=1)
while not sim.done:
    sim.step()                 # advances config.dt seconds
    state = sim.snapshot()     # plain dict: lanes -> people on the belt and in the queue
print(sim.results())
```

## Reading the results

- **Thru/min:** people reaching the top per minute after the warm-up.
- **Wait:** time spent queueing at the bottom. People still queueing at the end
  count with the time waited so far, so under overload the waits are a lower bound.
- **Queue end:** people still waiting when the run stops. If this is large, the
  escalator is overloaded and the queue keeps growing.
- The warm-up must be longer than one ride (`length / belt_speed`); otherwise
  the output shows a warning.

## Tests

```bash
python3 -m unittest discover -s tests   # engine and command line
npm install && npm test                 # web: runs the engine in Pyodide under Node
pip install -r requirements-dev.txt && npm run lint   # style checks
npm run lint:fix                                       # fix what it can, list the rest
```
