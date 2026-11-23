# Findings: Time Saved for Walkers at Holborn

This answers the question in [TIME_SAVED_PLAN.md](TIME_SAVED_PLAN.md): **at a
tall, busy escalator, how much time does stand-right/walk-left save the people
who want to walk, and what does it cost everyone else?** It sets that next to
the original question: which rule moves more people per minute?

All numbers come from the simulation, not from measurements. See
[What the model leaves out](#what-the-model-leaves-out) before quoting them.
For the time saved by walkers and standers in two short tables, see
[FINDINGS_SUMMARY.md](FINDINGS_SUMMARY.md).

## Summary

- **When the escalator keeps up (up to about 90 arrivals per minute),
  walk-left saves each walker about 29 s per trip, and costs everyone else
  under 5 s.** Both rules move the same number of people. In total,
  walk-left saves people time.
- **Close to capacity (100–110 per minute), walk-left's standing side fills
  up first.** At 110 per minute, people who stand lose about 49 s per trip,
  more than walkers gain, and stand-both moves about 4% more people.
- **Above capacity, with walking held at the rate measured at Holborn,
  stand-both moves about 7% more people** (108 vs. 101 per minute). People
  who stand lose more time than walkers save, by more the longer the rush
  lasts.
- **A few people standing in the walk lane cancel the benefit.** At 90 per
  minute, 2% of standers blocking it cut walkers' saving from 29 s to 17 s.
  At 110 per minute, 5% make stand-both faster even for the walkers. The model
  has no overtaking, so one blocker holds up every walker behind them.
- **So the answer depends on how busy it is.** Walk-left suits off-peak
  hours. At the rush-hour peak on a tall escalator, standing on both sides
  moves more people and costs less time in total. That matches the Holborn
  trial, which found a benefit only at the busiest times.
- **Another simulation agrees on the direction and on walkers' 30 s, but finds
  a much bigger gain at the peak** (19–39% more people, against 4–7% here).
  Its settings don't explain the gap. More likely it's the crowd at the
  bottom, which this model leaves out (see [Against another
  model](#against-another-model)).

## How these were made

- **The escalator:** Holborn's escalators 5 and 6, which were used in the 2015
  trial. It has a 23.4 m rise (46.8 m long) and a belt speed of 0.72 m/s. A
  standing ride takes 65 s.
- **The settings:** those calibrated against Davis & Dutta's London counts in
  `tests/test_calibration.py`. 45% of people want to walk, which is the share
  Davis & Dutta's formulas give at this height. Standers never switch to
  walking (`defect_prob` 0). Nobody blocks the walk lane unless that's what's
  being varied.
- **Each point:** 20 crowds (seeds 1–20). Each crowd faces both rules, after a
  3-minute warm-up, measured for 12 minutes. The line is finished, so everyone
  measured counts.
- **"Walkers save" and "Others save":** how much shorter the average trip
  (from joining the line to reaching the top) is under walk-left than under
  stand-both, on the same crowd. A minus sign means a longer trip. "Others" is
  everyone who doesn't want to walk, including people who stand in the walk
  lane.
- **"Net saved":** walkers' saving times the number of walkers, plus others'
  saving times the number of others, per minute measured. It's the total
  time walk-left saves everyone, in person-seconds per minute. For example,
  +900 means that each minute, all passengers together spend 15 fewer minutes
  on the escalator than under stand-both.
- **±:** the 95% margin of error over the 20 crowds. "Fastest for walkers" and
  "Most people/min" name a rule only when it leads by more than that margin.

To make the tables again (about 3 minutes on 16 cores):

```bash
python3 -m docs.findings > findings.md
```

Section 7 of the script's output is in [Against another model](#against-another-model),
and sections 8–9 are in [Double-checks](#double-checks).

The script printed:

```
Engine 0.1.0; 20 seeds per point (1–20); settings: rise=23.4, belt_speed=0.72, step_depth=0.4, walk_gap=0.9, walk_fraction=0.45, defect_prob=0, blocker_rate=0, warmup=180, duration=900, drain=1.
Savings are walk-left vs stand-both: positive means walk-left is faster.
```

## 1. How busy it is

| arrival_rate | stand-both people/min | walk-left people/min | Walkers save s | Others save s | Net saved, person-s/min | Fastest for walkers | Most people/min |
|---|---|---|---|---|---|---|---|
| 60 | 59.8 ±1.1 | 59.9 ±1.2 | +29.0 ±0.2 | −0.5 ±0.1 | +762 ±22 | walk-left | tie |
| 70 | 69.8 ±1.1 | 69.9 ±1.0 | +28.7 ±0.2 | −0.9 ±0.3 | +872 ±26 | walk-left | tie |
| 80 | 79.7 ±1.1 | 79.7 ±1.1 | +28.5 ±0.2 | −1.8 ±0.7 | +950 ±48 | walk-left | tie |
| 90 | 89.8 ±1.1 | 89.7 ±1.1 | +28.7 ±0.3 | −4.6 ±1.9 | +929 ±109 | walk-left | tie |
| 100 | 100.0 ±1.2 | 98.2 ±1.1 | +30.2 ±0.8 | −19.5 ±6.1 | +266 ±361 | walk-left | tie |
| 110 | 107.2 ±0.6 | 103.4 ±1.0 | +43.8 ±4.5 | −49.2 ±8.3 | −830 ±604 | walk-left | stand-both |
| 120 | 108.0 ±0.0 | 108.0 ±1.0 | +86.2 ±5.9 | −58.8 ±8.0 | +730 ±691 | walk-left | tie |
| 130 | 108.0 ±0.0 | 112.1 ±1.1 | +133.9 ±6.1 | −64.1 ±8.5 | +3165 ±834 | walk-left | walk-left |
| 140 | 108.0 ±0.0 | 116.5 ±1.2 | +181.3 ±6.0 | −69.6 ±8.8 | +5938 ±939 | walk-left | walk-left |
| 150 | 108.0 ±0.0 | 120.9 ±1.2 | +226.8 ±5.4 | −75.0 ±9.2 | +8994 ±987 | walk-left | walk-left |

- **Up to 90 per minute** the escalator keeps up under both rules. Walkers
  save 29 s, close to the difference between standing (65 s) and walking up
  at the average speed (33 s). They save a little less because some walkers
  are held up behind slower ones.
- **At 100–110 per minute** walk-left's standing side overloads first. 55% of
  people stand, which is 60 per minute at 110 arrivals, but under walk-left
  one standing lane carries only 54. Stand-both still has two standing lanes.
  So people who stand start to lose a lot of time.
- **From 120 per minute** both rules are overloaded, and walk-left looks
  better again. But that comes from a fixed 45% walking even when 150 people
  arrive per minute, which is more walking than has been seen at this height
  (see section 6).

## 2. People standing in the walk lane, at 90 per minute

| blocker_rate | stand-both people/min | walk-left people/min | Walkers save s | Others save s | Net saved, person-s/min | Fastest for walkers | Most people/min |
|---|---|---|---|---|---|---|---|
| 0% | 89.8 ±1.1 | 89.7 ±1.1 | +28.7 ±0.3 | −4.6 ±1.9 | +929 ±109 | walk-left | tie |
| 1% | 89.8 ±1.1 | 89.9 ±1.1 | +22.0 ±1.4 | −4.0 ±1.6 | +684 ±112 | walk-left | tie |
| 2% | 89.8 ±1.1 | 90.0 ±1.1 | +17.0 ±1.5 | −3.5 ±1.4 | +512 ±98 | walk-left | tie |
| 5% | 89.8 ±1.1 | 89.9 ±1.1 | +8.3 ±1.4 | −2.4 ±1.1 | +210 ±86 | walk-left | tie |
| 10% | 89.8 ±1.1 | 89.6 ±1.1 | +0.5 ±2.1 | −1.7 ±0.5 | −68 ±97 | tie | tie |

Each blocker standing in the walk lane holds up every walker behind them
for the whole ride. At 10%, walkers save nothing, and walk-left's only effect
is a small loss for everyone else.

## 3. People standing in the walk lane, at 110 per minute

| blocker_rate | stand-both people/min | walk-left people/min | Walkers save s | Others save s | Net saved, person-s/min | Fastest for walkers | Most people/min |
|---|---|---|---|---|---|---|---|
| 0% | 107.2 ±0.6 | 103.4 ±1.0 | +43.8 ±4.5 | −49.2 ±8.3 | −830 ±604 | walk-left | stand-both |
| 1% | 107.2 ±0.6 | 104.0 ±0.9 | +30.9 ±4.0 | −42.9 ±8.2 | −1091 ±513 | walk-left | stand-both |
| 2% | 107.2 ±0.6 | 104.4 ±0.7 | +17.6 ±5.7 | −37.1 ±7.7 | −1413 ±369 | walk-left | stand-both |
| 5% | 107.2 ±0.6 | 102.4 ±0.4 | −18.7 ±8.9 | −22.1 ±5.9 | −2311 ±294 | stand-both | stand-both |
| 10% | 107.2 ±0.6 | 101.7 ±0.6 | −55.5 ±8.4 | −7.2 ±3.8 | −3215 ±332 | stand-both | stand-both |

Near capacity, blockers matter more. At 5%, walkers themselves are 19 s
slower under walk-left than if everyone stood on both sides.

## 4. Share who want to walk, at 110 per minute

| walk_fraction | stand-both people/min | walk-left people/min | Walkers save s | Others save s | Net saved, person-s/min | Fastest for walkers | Most people/min |
|---|---|---|---|---|---|---|---|
| 10% | 107.2 ±0.6 | 64.8 ±0.4 | +48.1 ±4.5 | −431.2 ±7.7 | −42160 ±1170 | walk-left | stand-both |
| 20% | 107.2 ±0.6 | 75.6 ±0.6 | +47.0 ±4.5 | −324.2 ±9.4 | −27589 ±1088 | walk-left | stand-both |
| 30% | 107.2 ±0.6 | 86.7 ±0.7 | +45.9 ±4.5 | −212.4 ±9.0 | −14893 ±865 | walk-left | stand-both |
| 40% | 107.2 ±0.6 | 97.8 ±0.9 | +44.6 ±4.6 | −102.6 ±8.2 | −4846 ±647 | walk-left | stand-both |
| 50% | 107.2 ±0.6 | 108.0 ±1.2 | +42.9 ±4.6 | −5.6 ±5.8 | +2031 ±443 | walk-left | tie |
| 60% | 107.2 ±0.6 | 109.6 ±1.3 | +38.4 ±3.9 | +15.0 ±4.2 | +3194 ±457 | walk-left | walk-left |
| 70% | 107.2 ±0.6 | 104.6 ±1.0 | −0.8 ±4.7 | +16.8 ±4.5 | +493 ±389 | tie | stand-both |

- **With few walkers, walk-left wastes the walk lane.** At 10–40%, the
  standing side carries most people through one lane, and people who stand
  lose minutes per trip.
- **Around 50% walkers**, the two lanes carry about the same load, and
  others' loss is within the margin of error. **At 60%** walk-left helps
  everyone: others save 15 s too. Most of that comes from the model's standing
  lane being about 7% low. With it matched to Davis & Dutta, walk-left only
  ties at 55–60%, and others save 1–3 s (see [Double-checks](#double-checks)).
- **At 70%**, the walk lane itself fills up, and walkers gain nothing.
- At Holborn's height, about 45% walk (Davis & Dutta). That's between 40%,
  where walk-left costs people time in total, and 50%, where it saves time.

## 5. How busy it is, and blockers together

| arrival_rate | blocker_rate | stand-both people/min | walk-left people/min | Walkers save s | Others save s | Net saved, person-s/min | Fastest for walkers | Most people/min |
|---|---|---|---|---|---|---|---|---|
| 60 | 0% | 59.8 ±1.1 | 59.9 ±1.2 | +29.0 ±0.2 | −0.5 ±0.1 | +762 ±22 | walk-left | tie |
| 60 | 2% | 59.8 ±1.1 | 59.9 ±1.3 | +22.3 ±1.1 | −0.4 ±0.1 | +584 ±31 | walk-left | tie |
| 60 | 5% | 59.8 ±1.1 | 59.8 ±1.2 | +16.5 ±1.1 | −0.4 ±0.1 | +430 ±31 | walk-left | tie |
| 90 | 0% | 89.8 ±1.1 | 89.7 ±1.1 | +28.7 ±0.3 | −4.6 ±1.9 | +929 ±109 | walk-left | tie |
| 90 | 2% | 89.8 ±1.1 | 90.0 ±1.1 | +17.0 ±1.5 | −3.5 ±1.4 | +512 ±98 | walk-left | tie |
| 90 | 5% | 89.8 ±1.1 | 89.9 ±1.1 | +8.3 ±1.4 | −2.4 ±1.1 | +210 ±86 | walk-left | tie |
| 110 | 0% | 107.2 ±0.6 | 103.4 ±1.0 | +43.8 ±4.5 | −49.2 ±8.3 | −830 ±604 | walk-left | stand-both |
| 110 | 2% | 107.2 ±0.6 | 104.4 ±0.7 | +17.6 ±5.7 | −37.1 ±7.7 | −1413 ±369 | walk-left | stand-both |
| 110 | 5% | 107.2 ±0.6 | 102.4 ±0.4 | −18.7 ±8.9 | −22.1 ±5.9 | −2311 ±294 | stand-both | stand-both |
| 130 | 0% | 108.0 ±0.0 | 112.1 ±1.1 | +133.9 ±6.1 | −64.1 ±8.5 | +3165 ±834 | walk-left | walk-left |
| 130 | 2% | 108.0 ±0.0 | 106.8 ±0.7 | +44.7 ±13.9 | −47.5 ±8.4 | −853 ±610 | walk-left | stand-both |
| 130 | 5% | 108.0 ±0.0 | 102.9 ±0.3 | −25.1 ±11.2 | −28.0 ±7.2 | −3501 ±349 | stand-both | stand-both |

This replaces the "Early numbers" table in the time-saved plan. Those came
from a throwaway script that left out people who hadn't finished, which
biased the busiest rows. The direction is the same: no blockers favor
walk-left for walkers, and 5% blockers at 110+ per minute favor stand-both
for everyone.

## 6. How busy it is, with walking held at the measured rate

Davis & Dutta counted Holborn-height escalators with a line waiting. The
walking side carried about **47 people per minute**, so that's roughly how many
people are willing to walk up 23.4 m. The model normally sends a fixed 45% of
arrivals to walk, which above about 105 arrivals per minute is more than 47 per
minute. Here the share is lowered so that 47.4 per minute want to walk. Everyone
else stands.

| arrival_rate | walk_fraction | stand-both people/min | walk-left people/min | Walkers save s | Others save s | Net saved, person-s/min | Fastest for walkers | Most people/min |
|---|---|---|---|---|---|---|---|---|
| 110 | 43% | 107.2 ±0.6 | 101.2 ±0.9 | +44.1 ±4.5 | −69.1 ±7.6 | −2258 ±574 | walk-left | stand-both |
| 120 | 39% | 108.0 ±0.0 | 101.2 ±0.9 | +87.3 ±6.0 | −125.3 ±7.2 | −5035 ±653 | walk-left | stand-both |
| 130 | 36% | 108.0 ±0.0 | 100.8 ±1.1 | +136.2 ±6.3 | −176.0 ±8.2 | −8134 ±891 | walk-left | stand-both |
| 140 | 34% | 108.0 ±0.0 | 100.9 ±1.1 | +185.3 ±6.5 | −225.9 ±8.3 | −12184 ±1010 | walk-left | stand-both |
| 150 | 32% | 108.0 ±0.0 | 100.8 ±1.1 | +234.5 ±7.0 | −278.0 ±8.6 | −17534 ±1193 | walk-left | stand-both |

- **Walk-left levels off at about 101 per minute:** 54 standing plus about 47
  walking. Davis & Dutta measured about 106 per minute in total at this
  height. The model's standing lane is about 7% low; see below.
- **Stand-both carries 108 per minute, about 7% more.**
- **The extra people standing under walk-left wait far longer** than walkers
  save, so walk-left costs time in total. The gap grows with every minute the
  rush lasts. The sizes here are for a 15-minute run, but the direction holds
  for any run length.

## What the model leaves out

Each point below says which rule it likely favors.

- **No overtaking.** A walker can't pass a slower walker or a blocker. This
  makes blockers costly (it favors stand-both whenever there are blockers).
  Real walkers sometimes squeeze past.
- **How many people block the walk lane hasn't been measured.** Sections 2, 3
  and 5 show it matters as much as how busy it is. It needs a real count
  before any conclusion leans on it (see the open questions in
  [TIME_SAVED_PLAN.md](TIME_SAVED_PLAN.md#open-questions)).
- **People don't change their minds.** The share who want to walk is fixed.
  In reality more people stand when the walk lane is full, and some walk when
  the standing line is long. Section 6 shows how much this matters at the
  peak.
- **One line per lane at the bottom.** In reality the crowd at the bottom is a
  mix, and joining the right lane takes time and space. The model doesn't
  count that. Filippidis et al. do, and their walk-left carries far fewer
  people at the peak (see [Against another model](#against-another-model)). So
  this likely favors walk-left here.
- **Blockers don't depend on the crowd.** Here a fixed share of standers
  blocks the walk lane. In Filippidis et al., standers end up there mostly in
  a crush, so blocking grows exactly when it hurts most (this favors
  walk-left here).
- **The standing lane is about 7% low at 23 m.** In Davis & Dutta's counts,
  more people squeeze onto the standing side of taller escalators. The model
  carries a fixed 54 per minute per standing lane
  ([RESEARCH.md](RESEARCH.md#davis--dutta-2002-counts-at-10-london-stations)).
  Stand-both has two standing lanes, so this likely understates
  stand-both's people per minute more than walk-left's (it favors walk-left).
  It's enough to change section 4's answer at 55–60% walkers (see
  [Double-checks](#double-checks)).
- **Walkers step on like standers.** This slightly reduces walkers' saving
  (see the open questions in [ENGINE_DESIGN.md](ENGINE_DESIGN.md#open-questions)).
  It favors stand-both, by a little.

## Against real data

- **Holborn trial (Harrison et al. 2016):** on the all-standing day, single
  escalators carried up to about 90 per minute, as many as arrived, so that's
  a lower limit. The model's stand-both carries 108 per minute at full load,
  consistent with that limit.
- **Davis & Dutta (2002):** about 106 per minute in total under walk-left at
  this height, with a line waiting. The model gives 101 with walking held at
  the measured rate (section 6), 5% low, in line with its standing lane being
  about 7% low.
- **The trial's follow-up** found a benefit only at the busiest times (over
  about 100 arriving per minute). The model puts the switch at about 100–110
  per minute.
- **Walkers' time saved has never been measured** (see
  [RESEARCH.md](RESEARCH.md#summary)). The 29 s at quiet times is the model's
  own answer.

## Against another model

Filippidis et al. (2025) simulated the same question with buildingEXODUS, on
a station modeled on Holborn: a 23.75 m rise, 0.75 m/s, 40% walkers, and
walkers leaving two empty steps (1.2 m). See
[RESEARCH.md](RESEARCH.md#filippidis-gwynne-lawrence--galea-2025-station-simulation).

**Where the two agree:**
- **Walk-left helps when it's quiet, and everyone standing wins at the peak.**
  They see the switch at about 80–104 arriving per minute; this simulation at
  100–110.
- **Walkers save about 30 s on the escalator** (65.6 s riding against 33–37 s
  walking there; 29 s here).
- **Varied walking speeds hurt walk-left.** Walkers get held up behind slower
  ones in both models.

**Where they differ: how much more everyone standing carries.** At the peak,
everyone standing moves **19–39% more** people there, against **4–7%** here.
Their walk-left levels off at 71–80 per minute; here it's about 101.

**Settings explain little of the gap.** Running this simulation with their
settings:

| arrival_rate | stand-both people/min | walk-left people/min | Walkers save s | Others save s | Net saved, person-s/min | Fastest for walkers | Most people/min |
|---|---|---|---|---|---|---|---|
| 40 | 39.6 ±0.8 | 39.6 ±0.9 | +28.3 ±0.2 | −0.2 ±0.0 | +441 ±12 | walk-left | tie |
| 70 | 69.8 ±1.1 | 69.9 ±1.0 | +27.1 ±0.2 | −1.1 ±0.3 | +710 ±29 | walk-left | tie |
| 90 | 89.9 ±1.1 | 89.5 ±1.0 | +26.6 ±0.3 | −9.0 ±4.1 | +457 ±254 | walk-left | tie |
| 100 | 100.0 ±1.3 | 96.0 ±0.9 | +27.0 ±0.5 | −39.5 ±8.4 | −1325 ±553 | walk-left | stand-both |
| 120 | 112.4 ±0.2 | 104.1 ±0.9 | +60.3 ±5.1 | −112.7 ±7.3 | −5267 ±626 | walk-left | stand-both |

Everyone standing gains at most 8% here, even with their settings. The rest
likely comes from what their model has and this one doesn't. Under walk-left
at the peak, their walk lane carried only 27.5 per minute and their standing
lane 44.2, against about 48 and 56 here. The likely reasons:
- people at the bottom get in each other's way while choosing a lane, which
  slows boarding;
- standers end up in the walk lane once it's crowded;
- walkers can't always reach a free space.

These are the same things listed in [What the model leaves out](#what-the-model-leaves-out).
Leaving them out favors walk-left here, so this simulation's 4–7% is probably a
low estimate of the gain at the peak. Real counts sit between the two models:
Davis & Dutta measured about 106 per minute under walk-left at this height,
and the Holborn report counted 27% more people in an hour on the escalator
where everyone stood.

## Double-checks

Two small effects in the tables above looked new, so they were checked with
more crowds. These tables compare each crowd with itself under the other
setting ("same crowds"), which shows small differences far more clearly than
comparing two averages. Neither effect holds up.

### 8. Walk-left at 55–60% walkers, with the standing lane matched to Davis & Dutta

Section 4 shows walk-left moving more people than stand-both at 55–60%
walkers, with others saving time too. The model's standing lane carries 54 per
minute (0.80 m between standers). Davis & Dutta counted 58.4 per minute on the
standing side at 23.4 m, which is 0.74 m. All at 110 per minute, 100 crowds:

| standing lane | walk_fraction | stand-both people/min | walk-left people/min | Walk-left extra people/min, same crowds | Walkers save s | Others save s |
|---|---|---|---|---|---|---|
| 0.80 m (54.0/min) | 45% | 107.2 ±0.3 | 103.4 ±0.4 | −3.8 ±0.4 | +45.3 ±2.1 | −53.0 ±3.5 |
| 0.80 m (54.0/min) | 50% | 107.2 ±0.3 | 108.3 ±0.5 | +1.1 ±0.4 | +44.3 ±2.1 | −6.2 ±2.3 |
| 0.80 m (54.0/min) | 55% | 107.2 ±0.3 | 110.0 ±0.5 | +2.8 ±0.4 | +42.9 ±2.0 | +13.2 ±1.9 |
| 0.80 m (54.0/min) | 60% | 107.2 ±0.3 | 110.0 ±0.6 | +2.8 ±0.5 | +39.9 ±1.9 | +16.9 ±2.1 |
| 0.80 m (54.0/min) | 65% | 107.2 ±0.3 | 108.9 ±0.5 | +1.7 ±0.4 | +29.4 ±1.6 | +17.9 ±2.1 |
| 0.74 m (58.4/min) | 45% | 110.0 ±0.6 | 107.3 ±0.4 | −2.7 ±0.4 | +30.2 ±0.4 | −28.6 ±3.2 |
| 0.74 m (58.4/min) | 50% | 110.0 ±0.6 | 109.9 ±0.5 | −0.2 ±0.2 | +29.2 ±0.4 | −3.9 ±1.0 |
| 0.74 m (58.4/min) | 55% | 110.0 ±0.6 | 110.1 ±0.6 | +0.1 ±0.2 | +27.7 ±0.4 | +1.3 ±0.4 |
| 0.74 m (58.4/min) | 60% | 110.0 ±0.6 | 110.0 ±0.6 | −0.0 ±0.2 | +24.7 ±0.4 | +2.6 ±0.4 |
| 0.74 m (58.4/min) | 65% | 110.0 ±0.6 | 108.9 ±0.5 | −1.1 ±0.3 | +14.2 ±1.7 | +3.2 ±0.4 |

- **With the matched standing lane, walk-left only ties at 55–60% walkers.**
  The gain of about 3 per minute came from the model's standing lane being
  too small.
- **What's left is a narrow band where walk-left costs nobody time.** At
  55–60%, walkers save about 25–28 s, and others gain 1–3 s.
- **At Holborn's 45%, the original answer stands.** Walk-left carries about 3
  fewer people per minute, and others lose about 29 s.
- At 120 per minute, walk-left still wins at 55–60% walkers, but that means
  66–72 people per minute walking, against about 47 that Davis & Dutta saw at
  this height.

### 9. A few blockers, with 200 crowds

Section 3 shows 1–2% blockers raising walk-left from 103.4 to 104.4 people per
minute at 110 arrivals, within the margin of error. Walk-left only, with the
model's standing lane:

| arrival_rate | blocker_rate | walk-left people/min | Change from 0% blockers, same crowds | walk lane people/min | standing lane people/min |
|---|---|---|---|---|---|
| 100 | 0% | 98.0 ±0.3 | +0.0 ±0.0 | 44.7 ±0.3 | 53.3 ±0.1 |
| 100 | 1% | 98.2 ±0.4 | +0.3 ±0.1 | 45.2 ±0.3 | 53.1 ±0.2 |
| 100 | 2% | 98.5 ±0.4 | +0.6 ±0.2 | 45.7 ±0.3 | 52.9 ±0.2 |
| 100 | 5% | 98.6 ±0.3 | +0.6 ±0.2 | 46.7 ±0.2 | 51.9 ±0.2 |
| 110 | 0% | 103.2 ±0.3 | +0.0 ±0.0 | 49.2 ±0.3 | 54.0 ±0.0 |
| 110 | 1% | 103.7 ±0.3 | +0.5 ±0.2 | 49.7 ±0.3 | 54.0 ±0.0 |
| 110 | 2% | 103.6 ±0.3 | +0.4 ±0.2 | 49.7 ±0.3 | 53.9 ±0.0 |
| 110 | 5% | 102.5 ±0.2 | −0.7 ±0.3 | 48.7 ±0.1 | 53.8 ±0.1 |
| 120 | 0% | 107.7 ±0.3 | +0.0 ±0.0 | 53.7 ±0.3 | 54.0 ±0.0 |
| 120 | 1% | 107.8 ±0.3 | +0.1 ±0.2 | 53.8 ±0.3 | 54.0 ±0.0 |
| 120 | 2% | 106.0 ±0.3 | −1.7 ±0.3 | 52.0 ±0.3 | 54.0 ±0.0 |
| 120 | 5% | 103.0 ±0.1 | −4.7 ±0.3 | 49.0 ±0.1 | 54.0 ±0.0 |

- **The rise is real, but under 1 per minute.** At 110 per minute, 1%
  blockers add about 0.5. They move a few standers into the walk lane, which
  has room.
- **From 2–5% blockers, the total falls.** The busier it is, the sooner: at
  120 per minute, 2% blockers cost about 1.7 per minute and 5% cost 4.7.
