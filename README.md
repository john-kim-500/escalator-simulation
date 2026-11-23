# Escalator Simulator

An agent-based simulation that tests whether an escalator moves more people when
everyone **stands on both sides** (`stand-both`) than with the usual **stand
right, walk left** convention (`walk-left`). See [PLAN.md](PLAN.md) for the design
and the reasons behind it.

Requires Python 3.10+ (run as `python3`) and only the standard library.

**Full guide: [docs/USAGE.md](docs/USAGE.md)**, covering every command and
parameter, how to read the results, JSON/CSV output, recipes for testing the
theory, and troubleshooting.

## Usage

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
python3 -m unittest discover -s tests
```
