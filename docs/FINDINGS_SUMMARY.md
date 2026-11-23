# Findings Summary: Time Saved and People Moved

A short view of [FINDINGS.md](FINDINGS.md): how much time stand-right/walk-left
saves or costs each group per trip, and how many people per minute it moves, by
how busy it is and how many people stand in the walk lane. All numbers come
from the simulation, not from measurements. See [What the model leaves
out](FINDINGS.md#what-the-model-leaves-out) before quoting them.

**Settings:** the Holborn escalator (23.4 m rise), 45% want to walk, standers
spaced as Davis & Dutta counted (0.74 m, 58.4 per minute per lane), 100 seeds
per point, line finished. "—" means the combination wasn't run. Source tables:
sections 2, 3 and 5 of [FINDINGS.md](FINDINGS.md).

**How the time tables compare the rules:** both rules get the same crowd, with
the same people arriving at the same moments. Only the rule changes. Each value
is a group's average trip time under stand-both minus its average under
walk-left, in seconds. A trip runs from arriving at the bottom to reaching the
top, including the wait in line. A positive number means walk-left is faster for
that group; a negative number means slower.

**Blockers** are standers who stand in the walk lane. The percentage is a share
of standers, not of everyone: with 55% standing, 5% blockers is about 2.75% of
all arrivals.

## Walkers

Time saved per trip by people who want to walk, under walk-left (where they
walk up the left lane) compared with everyone standing on both sides (where
they stand too).

| Arrivals/min | 0% blockers | 1% | 2% | 5% | 10% |
|---|---|---|---|---|---|
| 60 | +28.9 | — | +22.5 | +16.3 | — |
| 90 | +28.1 | +21.9 | +17.1 | +8.4 | +0.9 |
| 110 | +30.1 | +19.1 | +6.3 | **−28.9** | **−62.9** |
| 130 † | +88.2 | — | +5.3 (tie) | **−66.0** | — |

- **When it's quiet (60–90/min), with no blockers, walkers save about 28 s.**
  That's roughly the gap between standing the whole ride (65 s) and walking up
  (33 s).
- **Blockers wipe out the saving.** Each one holds up every walker behind them
  for the whole ride. At 90/min, 10% blockers leave walkers about 1 s.
- **When it's busy, blockers hurt walkers more.** At 110/min, 2% blockers
  leave walkers 6 s, and 5% make them slower under walk-left than if everyone
  stood on both sides.
- **The bigger saving at 130/min with no blockers** is mostly time walkers
  avoid waiting in the standing line, not faster climbing.

## Standers

Time saved per trip by people who stand, blockers included, under walk-left
(where they share the one standing lane on the right) compared with everyone
standing on both sides.

| Arrivals/min | 0% blockers | 1% | 2% | 5% | 10% |
|---|---|---|---|---|---|
| 60 | −0.4 | — | −0.3 | −0.3 | — |
| 90 | −2.1 | −1.9 | −1.7 | −1.4 | −1.2 |
| 110 | **−28.4** | −24.1 | −20.2 | −12.7 | −9.5 |
| 130 † | −62.9 | — | −49.0 | −32.9 | — |

- **When it's quiet (60–90/min), standers lose about 2 s or less.** Both rules keep up.
  The small loss comes from walk-left's single standing lane having a slightly
  longer line.
- **From about 110/min, standers lose about 28 s per trip with no blockers.**
  About 60 standers arrive per minute, but walk-left's one standing lane carries
  only 58.4, so their line keeps growing. Under stand-both they have two lanes.
- **Blockers reduce standers' losses.** Blockers take load off the standing
  line. At 110/min, going from 0% to 10% blockers cuts standers' loss from 28 s
  to 10 s, while walkers go from saving 30 s to losing 63 s. At 10%, walk-left
  mostly turns into a slower form of standing on both sides.

## People per minute

People reaching the top per minute, on one escalator. Margins are about ±0.5
per minute. Percentages compare walk-left with stand-both.

| Arrivals/min | stand-both | walk-left, 0% blockers | 1% | 2% | 5% | 10% |
|---|---|---|---|---|---|---|
| 60 | 60.0 | 60.2 | — | 60.1 | 60.1 | — |
| 90 | 90.0 | 90.0 | 90.0 | 90.1 | 89.9 | 89.8 |
| 110 | 110.0 | 107.3 (−2.5%) | 107.8 (−2%) | 107.7 (−2%) | 105.7 (−4%) | 103.6 (−6%) |
| 130 † | 116.8 | 116.7 (0%) | — | 111.4 (−5%) | 107.6 (−8%) | — |

- **Up to 90/min, the rule makes no difference.** Both rules carry everyone who
  arrives. Blockers change who waits, not how many get through.
- **At 110/min, stand-both moves 2–6% more people,** 2–6 more per minute.
  Under walk-left, the single standing lane is the limit: it carries 58.4 per
  minute.
- **More than a few blockers lower people per minute.** At 110/min, 1–2%
  blockers change walk-left's total by under 1 per minute (section 9 of
  [FINDINGS.md](FINDINGS.md)). From 5%, they slow the walk lane enough that
  the total falls.
- **Walk-left keeps up with stand-both only at a sustained 130/min with no
  blockers,** and only because 45% keep walking. With walking held at the rate
  Davis & Dutta measured, walk-left carries about 106 per minute from 110 to
  150, so stand-both moves 4–11% more (section 6 of
  [FINDINGS.md](FINDINGS.md)). That
  fits the Holborn trial, which found standing on both sides helped only at the
  busiest times.

## Side by side, in the realistic range

| Arrivals/min | Blockers | Walkers save s | Standers save s | Extra people/min with stand-both |
|---|---|---|---|---|
| 90 | 0% | +28.1 | −2.1 | 0 |
| 90 | 5% | +8.4 | −1.4 | 0 |
| 110 | 0% | +30.1 | −28.4 | +2.7 |
| 110 | 5% | −28.9 | −12.7 | +4.3 |

At 90/min, walk-left is a good trade: walkers gain a lot, and standers lose
little. At 110/min, standers lose about as much per person as walkers gain, and
there are more of them (55%). That's why walk-left costs a little time in total
there. At 120/min, standers lose 55 s against walkers' 48 s, and the total
loss is four times larger (section 1 of [FINDINGS.md](FINDINGS.md)).

How closely people stand matters. With the engine's default spacing (0.8 m,
54 per minute per lane), walk-left falls behind about 10 arrivals per minute
sooner, and standers lose about 53 s at 110/min (section 10 of
[FINDINGS.md](FINDINGS.md)).

A gap of a few percent in people per minute looks small. But near capacity it
decides whether the line keeps growing, and that's where standers' large
losses come from.

## † A sustained 130 per minute is unrealistic

- **What's been seen:** at Holborn, most readings were 50–100 per minute per
  escalator, with brief highs of about 115–141 (Harrison et al. 2017, via
  Filippidis et al. 2025). Filippidis et al.'s busiest case is a short burst at
  120 after two trains. See [RESEARCH.md](RESEARCH.md#harrison-et-al-2016-the-holborn-trial).
- **What the 130 rows do:** they run 130 per minute steadily for 15 minutes, so
  the line keeps growing. Both groups' time savings in those rows grow with the
  length of the run. Read it as a stress test.
- **It also assumes 45% keep walking.** That's more walking than Davis & Dutta
  saw at this height. With walking held at their measured rate (about 47 per
  minute), walkers save about 90 s at 130/min, but standers lose about 165 s
  (section 6 of [FINDINGS.md](FINDINGS.md)).
- **Realistic busy range: 90–110 per minute**, with short bursts up to about
  120. Counts at the top can only show how many people the escalator carried,
  so the real peak arrival rate may be somewhat higher, but it hasn't been
  measured.
- **Arrivals in the model are steady.** Real arrivals come in bursts as trains
  unload. A steady 110 per minute for 15 minutes likely overstates how long the
  line grows, so it overstates both walkers' savings and standers' losses near
  capacity.

## Limitations

The model's results are a guide, not a measurement. Two kinds of source stand
behind them:

- **Real counts:** Davis & Dutta (2002) counted 10 London stations, and the
  Holborn trial (2015–16) counted passengers standing on both sides. The model
  is set to match Davis & Dutta, and checked against Holborn.
- **Another simulation:** Filippidis et al. (2025) modeled a Holborn-like
  station in different software. They agree on the direction and on walkers'
  30 s, but their findings are a comparison, not evidence.

What the model leaves out, and which rule each point likely favors:

- **No overtaking.** One blocker holds up every walker behind them for the
  whole ride. This makes blockers costly, so the blocker columns likely
  overstate walkers' losses (favors stand-both).
- **How many people block the walk lane has never been counted.** The tables
  show it matters as much as how busy it is. Treat the blocker columns as
  "what if," not as a prediction.
- **Standing spacing doesn't shrink when it's crowded.** The model carries at
  most 58.4 standers per minute per lane, Davis & Dutta's average at this
  height, so stand-both tops out at 117 per minute. Real counts went higher:
  Holborn's highest reading was 141 per minute with nearly everyone standing,
  and Davis & Dutta saw 75.6 per minute standing in one lane. So the 2–6%
  stand-both gain in the tables is probably low (favors walk-left).
- **Boarding doesn't slow when it's crowded at the bottom.** In Filippidis et
  al., the crowd slows boarding, and walk-left carries far fewer people at the
  peak (favors walk-left).
- **Real counts sit between the two models.** For walk-left, Davis & Dutta
  measured about 106 per minute at this height: what this model gives, since
  it's fitted to them, and well above Filippidis et al. (71–80). For how much
  more everyone standing carries, the Holborn report counted 27% more people
  in an hour with everyone standing, closer to Filippidis et al.'s 19–39% than
  to the 2.5–11% here.
- **Arrivals are steady.** Real arrivals come in bursts as trains unload. A
  steady rate for 15 minutes likely overstates how long the line grows near
  capacity, and with it both walkers' savings and standers' losses.
- **The share who walk is fixed at 45%.** In reality fewer walk when it's
  crowded. This is why the 130 rows favor walk-left (see † above).
- **Walkers' time saved has never been measured.** The 28 s is the model's own
  answer, though Filippidis et al.'s model gives about 30 s too.

Full list: [What the model leaves out](FINDINGS.md#what-the-model-leaves-out).
