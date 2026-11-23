# Time Saved Plan: Measure What Walking Is Worth

So far the simulator answers one question: which strategy moves **more people
per minute**? This plan adds a second one: **for the passengers who care, how
much time does each strategy save them?** It builds on the model in
[PLAN.md](PLAN.md) and the calibration in `tests/test_calibration.py`.

## Goals

1. **Trip time by group:** for the passengers who want to walk ("cares") and
   for everyone else ("don't care"), measure the time from arriving at the
   bottom to reaching the top.
2. **Time saved:** for each "cares" passenger, the trip time under stand-both
   minus the trip time under walk-left, on the same crowd. Report the cost (or
   gain) to the "don't care" group next to it.
3. **Count everyone who arrives:** nobody who arrives during the measured
   window is left out because the run ended before they reached the top.
4. **Show it everywhere:** CLI tables, CSV/JSON, and the GUI's live and
   experiments views, with a "most time saved" winner beside the throughput
   winner.

**Not in this plan:** overtaking in the walk lane, mixed queues at the bottom
(the model still has one queue per lane), and costs such as safety or comfort.

## Assumptions

- **"Cares" means `wants_to_walk`.** It's a person's intent, drawn on arrival
  with probability `walk_fraction`. Under stand-both these people stand like
  everyone else, but they are still the "cares" group.
- **"Don't care" people mostly stand on the standing side.** Some stand in the
  walk lane instead. That's the existing `blocker_rate`: the share of
  don't-care people who stand in the walk lane under walk-left.
- **Defectors count as "don't care".** These are standers who switch to
  walking when their queue is long (`defect_threshold`, `defect_prob`). They
  walk because of the queue, not because they were in a hurry, so they're
  grouped by intent.

## What the engine already provides

- Every `Person` has `wants_to_walk`, `arrival_time`, `board_time` and
  `exit_time`. Trip time is simply `exit_time - arrival_time`.
- The same seed gives the **same crowd under every strategy**: the same
  arrival times, the same `wants_to_walk` and the same walking speeds (see
  "Determinism" in [APP_DESIGN.md](APP_DESIGN.md#determinism)). So person `i` is the
  same passenger under both strategies, and the comparison is per person, not
  just between group averages.
- `blocker_rate` already models don't-care people standing in the walk lane.

## Early numbers

These have been replaced by [FINDINGS.md](FINDINGS.md). They came from a
throwaway script that left out everyone who hadn't finished, which biased the
busiest rows. The direction held up: with no blockers walk-left saves walkers
time, and a few blockers flip the result.

## Changes needed in the engine

### 1. Let everyone who arrives finish (drain phase) ✅

Done: `drain`, on by default (`--drain 0` turns it off). It started as an
option, off by default, and was switched on so the page and the command line
agree and time saved always shows. With it on, **waits** are complete too, not
just trip times.
There is no cap on how long the drain runs. See "Finishing the line" in
[ENGINE_DESIGN.md](ENGINE_DESIGN.md#finishing-the-line-drain).

**Problem:** `summarize()` takes trip times only from people who reached the
top. People still queueing or riding when the run ends are left out. When the
escalator is overloaded, that hides the longest trips, and it hides more of
them for the strategy that leaves the longer queue.

**Change:** the measured group is everyone who arrives during
`[warmup, duration]`.
- After `duration`, stop new arrivals and keep stepping until every member of
  that group has reached the top.
- Throughput and queue statistics stay measured over `[warmup, duration]`
  exactly as now. Only trip times use the drain.

**Why this doesn't change the answer:**
- Queues are first come, first served, and nobody overtakes. So a later
  arrival can never change an earlier person's trip.
- Defectors and blockers decide on arrival, from the queue lengths at that
  moment.
- So running on with no new arrivals gives exactly the trip times the group
  would have had in an endless run.

**Details:**
- `run()` gains the drain; `step()` stays the same.
- No cap on drain length: an overloaded run takes as long as clearing its line.
- The live view stops at `duration` as now. Its final results include the
  drain.
- With `drain = 1`, the existing `trip_mean`/`trip_p95` and the waits cover
  the full measured group. With `drain = 0` they stay as before.

### 2. Trip time by group ✅

`summarize()` adds:

| Field | Meaning |
|---|---|
| `trip_mean_cares`, `trip_p95_cares` | Trip time for `wants_to_walk` passengers |
| `trip_mean_others`, `trip_p95_others` | Trip time for everyone else (including blockers and defectors) |
| `cares_count`, `others_count` | Size of each group (the same for every strategy on the same seed) |

Add them to `SCALAR_METRICS` so `aggregate()` gives a mean and 95% CI for each.

### 3. Time saved, paired by seed ✅

- **This needs `drain = 1`.** Without it, each strategy leaves out a
  different set of unfinished people. The numbers are always in the JSON,
  marked `drained`, but the command line shows them only when the runs
  drained (the default) and prints a hint with `--drain 0`.
- With the drain, both strategies measure the **same people** for a given
  seed. So the per-person average saving is exactly
  `trip_mean_cares(stand-both) − trip_mean_cares(walk-left)` for that seed. No
  per-person data has to leave the engine.
- In `collect_compare`/`collect_sweep`, add a `time_saved` section for each
  pair of strategies. It holds the per-seed differences for both groups, and
  their mean and 95% CI computed on those differences.
- That paired CI is much tighter than combining two independent CIs, because
  the crowd-to-crowd noise cancels.
- A per-person distribution (e.g. "90% of walkers saved at least X s") would
  need per-person trip times, which is too much data to send to the GUI. Leave
  it as an option for later (see Open questions).

## Output

- **CLI `compare` / `sweep`:**
  - Trip-by-group columns in the results table.
  - A line per strategy pair, e.g. "walk-left vs stand-both: walkers save
    41.7 ±7.4 s per trip; others lose 10.2 ±5.1 s". ✅
  - A "Fastest for walkers" winner (`report.time_winner`). ✅ It uses the
    paired saving and its margin of error, rather than the lowest
    `trip_mean_cares`, so it agrees with the time-saved line and doesn't call
    a tie when the paired margin shows a clear difference.
- **CSV/JSON (`report.py`):** the new per-run fields as columns, plus the
  `time_saved` summary in JSON. ✅ The GUI downloads stay identical to the CLI
  output, because both use `report.py`.
- **GUI experiments view:**
  - The new rows in the results table.
  - A "Time saved" chart: per-person saving against the swept value, with
    error bars.
  - The "most time saved" winner shown next to the throughput winner.
- **GUI live view:**
  - "Average trip so far" for each group in the stats table, from new
    running counters in `live_stats()`.
  - A time-saved row in the final results when exactly two strategies are
    shown.

## Experiments this enables

- **Sweep `arrival_rate`** at Holborn settings: where does the walkers'
  saving peak, and where do the don't-care group's losses outweigh it?
- **Sweep `blocker_rate`** from 0 to 10%: how many people standing in the walk
  lane cancel the benefit of walk-left?
- **Sweep `walk_fraction`**: whether there's a share of walkers where
  walk-left helps both groups.
- **Total time:** the saving for the "cares" group times its size, minus the
  loss for the "don't care" group times its size. This gives the net
  person-seconds per minute, a single figure to set against throughput.

## Testing

- **Group sizes:** `cares_count` and `others_count` match between strategies
  for the same seed, and sum to the measured group.
- **Drain is complete:** every measured person has an `exit_time` after
  `run()`.
- **Drain doesn't bias trips:** for a run with spare capacity, trip times of
  people who finish before `duration` are the same with and without the drain.
- **Paired equals per-person:** for one seed, the `time_saved` mean equals the
  average of per-person differences computed directly from `Simulation.people`.
- **Directional checks:**
  - With `blocker_rate = 0` and spare capacity, the walk-left saving for the
    "cares" group is positive and close to the ride-time difference (see the
    formula below).
  - With everyone standing (`walk_fraction = 0`), the "cares" group is empty
    and the metric is `None`, not an error.

  The ride-time difference is `length / belt_speed − length / (belt_speed +
  mean walk speed)`.
- **Front ends:** the Python–Pyodide cross-check in
  `web/tests/engine.test.mjs` covers the new fields, and
  `tests/test_web_support.py` checks that `Session` gives the same
  `time_saved` as `compare()`.

## Milestones

1. ✅ **Drain phase and trip by group** in the engine and `summarize()`, with
   tests. The drain is on by default; `drain = 0` turns it off.
2. ✅ **Paired time saved** in `experiments.py` and `report.py`. CLI tables and
   CSV/JSON. The "Fastest for walkers" winner rule. Hidden with `--drain 0`.
3. ✅ **GUI:** experiments table rows, the time-saved chart and winner, and the
   live-view stats. Shown when "Finish the line" is 1, with a hint otherwise.
4. ✅ **Write-up:** run the sweeps above at the Holborn settings and record the
   findings, including the throughput and time-saved figures side by side.
   See [FINDINGS.md](FINDINGS.md); `python3 -m docs.findings` makes the tables.

## Open questions

- **Saving distribution:** is an average enough, or do we want "X% of walkers
  saved at least Y s"? The second needs per-person trip times in the results.
  That's fine on the CLI, but heavy for the GUI with many replications.
- **Default `blocker_rate`:** should it stay at 0, or move to an observed
  value? It matters a lot here, so it needs a source, like the
  [walk_gap calibration](../tests/test_calibration.py) had. The findings
  confirm it: 2–5% blockers change the answer as much as how busy it is.
- **Overtaking:** the model has none, which is what makes blockers so costly.
  The findings show blockers can decide the result, so overtaking (or walkers
  stepping around blockers) deserves its own plan. Filippidis et al. (2025)
  let walkers overtake through the right lane when there's room.
  Now a follow-up question in [ENGINE_DESIGN.md](ENGINE_DESIGN.md#open-questions).
- **The crowd at the bottom:** Filippidis et al. find that people choosing a
  lane in a crowd slow everyone's boarding, and that standers end up in the
  walk lane once it's crowded. Their walk-left carries 71–80 per minute at the
  peak, against about 106 here ([findings](FINDINGS.md#against-another-model)).
  Should boarding slow down, and `blocker_rate` rise, as the line grows?
- **How many people walk at the peak:** a fixed `walk_fraction` lets more
  people walk than Davis & Dutta saw at Holborn's height once more than about
  105 people arrive per minute (findings, section 6). Should the share who
  walk depend on how many arrive, or be capped at the measured walking rate?
