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

- **When the escalator keeps up (up to about 100 arrivals per minute),
  walk-left saves each walker about 28 s per trip, and costs everyone else
  under 7 s.** Both rules move the same number of people. In total,
  walk-left saves people time.
- **Close to capacity (110–120 per minute), walk-left's standing side fills
  up first.** At 110 per minute, people who stand lose about 28 s per trip,
  slightly more in total than walkers gain, and stand-both moves about 2.5%
  more people. At 120, standers lose 55 s and stand-both moves 3.5% more.
- **Above capacity, with walking held at the rate measured at Holborn,
  stand-both moves about 11% more people** (117 vs. 106 per minute). People
  who stand lose more time than walkers save, by more the longer the rush
  lasts.
- **A few people standing in the walk lane cancel the benefit.** At 90 per
  minute, 2% of standers blocking it cut walkers' saving from 28 s to 17 s.
  At 110 per minute, 2% cut it to 6 s, and 5% make stand-both faster even for
  the walkers. The model has no overtaking, so one blocker holds up every
  walker behind them.
- **So the answer depends on how busy it is.** Walk-left suits off-peak
  hours. At the rush-hour peak on a tall escalator, standing on both sides
  moves more people and costs less time in total. That matches the Holborn
  trial, which found a benefit only at the busiest times.
- **How closely people stand matters.** With standers spaced as the engine's
  default (0.8 m) rather than as Davis & Dutta counted (0.74 m), walk-left
  falls behind about 10 arrivals per minute sooner, and standers' losses near
  capacity are about twice as large (section 10).
- **Another simulation agrees on the direction and on walkers' 30 s, but finds
  a much bigger gain at the peak** (19–39% more people, against 2.5–11% here).
  Its settings don't explain the gap. More likely it's the crowd at the
  bottom, which this model leaves out (see [Against another
  model](#against-another-model)).

## How these were made

- **The escalator:** Holborn's escalators 5 and 6, which were used in the 2015
  trial. It has a 23.4 m rise (46.8 m long) and a belt speed of 0.72 m/s. A
  standing ride takes 65 s.
- **The settings:** fitted to Davis & Dutta's London counts at this height.
  Walkers keep 0.9 m from the person ahead, fitted in
  `tests/test_calibration.py`. Standers keep 0.74 m, so one standing lane
  carries the 58.4 people per minute that Davis & Dutta counted on the
  standing side at 23.4 m. (The engine's default is 0.8 m, or 54 per minute;
  section 10 compares the two.) 45% of people want to walk, which is the share
  Davis & Dutta's formulas give at this height. Standers never switch to
  walking (`defect_prob` 0). Nobody blocks the walk lane unless that's what's
  being varied.
- **Each point:** 100 crowds (seeds 1–100). Each crowd faces both rules, after
  a 3-minute warm-up, measured for 12 minutes. The line is finished, so
  everyone measured counts.
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
- **±:** the 95% margin of error over the crowds. "Fastest for walkers" and
  "Most people/min" name a rule only when it leads by more than that margin.
- **Earlier version:** before 23 November 2026, these tables used the
  engine's default 0.8 m between standers and 20 crowds per point. That
  version is in the [git history](https://github.com/john-kim-500/escalator-simulation/blob/eb98241/docs/FINDINGS.md).

To make the tables again (about 10 minutes on 16 cores):

```bash
python3 -m docs.findings > findings.md
```

Section 7 of the script's output is in [Against another model](#against-another-model),
and sections 8–10 are in [Double-checks](#double-checks).

The script printed:

```
Engine 0.1.0; 100 seeds per point (1–100); settings: rise=23.4, belt_speed=0.72, step_depth=0.4, walk_gap=0.9, stand_gap=0.74, walk_fraction=0.45, defect_prob=0, blocker_rate=0, warmup=180, duration=900, drain=1.
Savings are walk-left vs stand-both: positive means walk-left is faster.
```

## 1. How busy it is

| arrival_rate | stand-both people/min | walk-left people/min | Walkers save s | Others save s | Net saved, person-s/min | Fastest for walkers | Most people/min |
|---|---|---|---|---|---|---|---|
| 60 | 60.0 ±0.5 | 60.2 ±0.5 | +28.9 ±0.1 | −0.4 ±0.0 | +763 ±9 | walk-left | tie |
| 70 | 70.2 ±0.5 | 70.2 ±0.5 | +28.6 ±0.1 | −0.6 ±0.0 | +871 ±9 | walk-left | tie |
| 80 | 80.0 ±0.5 | 80.0 ±0.5 | +28.3 ±0.1 | −1.0 ±0.1 | +968 ±11 | walk-left | tie |
| 90 | 90.0 ±0.6 | 90.0 ±0.5 | +28.1 ±0.1 | −2.1 ±0.2 | +1026 ±16 | walk-left | tie |
| 100 | 100.2 ±0.6 | 99.9 ±0.5 | +28.2 ±0.1 | −6.7 ±1.1 | +887 ±66 | walk-left | tie |
| 110 | 110.0 ±0.6 | 107.3 ±0.4 | +30.1 ±0.4 | −28.4 ±3.2 | −266 ±204 | walk-left | stand-both |
| 120 | 116.2 ±0.2 | 112.3 ±0.4 | +47.7 ±2.2 | −54.8 ±3.3 | −1071 ±247 | walk-left | stand-both |
| 130 | 116.8 ±0.0 | 116.7 ±0.4 | +88.2 ±2.9 | −62.9 ±3.1 | +640 ±288 | walk-left | tie |
| 140 | 116.8 ±0.0 | 121.2 ±0.5 | +131.9 ±3.0 | −68.0 ±3.2 | +3058 ±332 | walk-left | walk-left |
| 150 | 116.8 ±0.0 | 125.6 ±0.5 | +174.1 ±3.0 | −72.7 ±3.3 | +5741 ±358 | walk-left | walk-left |

- **Up to 100 per minute** the escalator keeps up under both rules. Walkers
  save about 28 s, close to the difference between standing (65 s) and
  walking up at the average speed (33 s). They save a little less because
  some walkers are held up behind slower ones.
- **At 110–120 per minute** walk-left's standing side overloads first. 55% of
  people stand, which is 60 per minute at 110 arrivals, but under walk-left
  one standing lane carries only 58.4. Stand-both still has two standing
  lanes. So people who stand start to lose a lot of time, and in total
  walk-left costs time.
- **From 130 per minute** both rules are overloaded, and walk-left looks
  better again. But that comes from a fixed 45% walking even when 150 people
  arrive per minute, which is more walking than has been seen at this height
  (see section 6).

## 2. People standing in the walk lane, at 90 per minute

| blocker_rate | stand-both people/min | walk-left people/min | Walkers save s | Others save s | Net saved, person-s/min | Fastest for walkers | Most people/min |
|---|---|---|---|---|---|---|---|
| 0% | 90.0 ±0.6 | 90.0 ±0.5 | +28.1 ±0.1 | −2.1 ±0.2 | +1026 ±16 | walk-left | tie |
| 1% | 90.0 ±0.6 | 90.0 ±0.6 | +21.9 ±0.5 | −1.9 ±0.2 | +786 ±24 | walk-left | tie |
| 2% | 90.0 ±0.6 | 90.1 ±0.6 | +17.1 ±0.5 | −1.7 ±0.2 | +600 ±25 | walk-left | tie |
| 5% | 90.0 ±0.6 | 89.9 ±0.6 | +8.4 ±0.5 | −1.4 ±0.2 | +266 ±23 | walk-left | tie |
| 10% | 90.0 ±0.6 | 89.8 ±0.6 | +0.9 ±0.9 | −1.2 ±0.1 | −32 ±40 | walk-left | tie |

Each blocker standing in the walk lane holds up every walker behind them
for the whole ride. At 10%, walkers save about 1 s, and walk-left's only
effect is a small loss for everyone else.

## 3. People standing in the walk lane, at 110 per minute

| blocker_rate | stand-both people/min | walk-left people/min | Walkers save s | Others save s | Net saved, person-s/min | Fastest for walkers | Most people/min |
|---|---|---|---|---|---|---|---|
| 0% | 110.0 ±0.6 | 107.3 ±0.4 | +30.1 ±0.4 | −28.4 ±3.2 | −266 ±204 | walk-left | stand-both |
| 1% | 110.0 ±0.6 | 107.8 ±0.5 | +19.1 ±1.1 | −24.1 ±3.0 | −553 ±192 | walk-left | stand-both |
| 2% | 110.0 ±0.6 | 107.7 ±0.5 | +6.3 ±2.3 | −20.2 ±2.6 | −951 ±195 | walk-left | stand-both |
| 5% | 110.0 ±0.6 | 105.7 ±0.4 | −28.9 ±4.0 | −12.7 ±1.9 | −2245 ±221 | stand-both | stand-both |
| 10% | 110.0 ±0.6 | 103.6 ±0.4 | −62.9 ±4.2 | −9.5 ±0.7 | −3722 ±244 | stand-both | stand-both |

Near capacity, blockers matter more. At 2%, walkers save only 6 s. At 5%,
walkers themselves are 29 s slower under walk-left than if everyone stood on
both sides.

## 4. Share who want to walk, at 110 per minute

| walk_fraction | stand-both people/min | walk-left people/min | Walkers save s | Others save s | Net saved, person-s/min | Fastest for walkers | Most people/min |
|---|---|---|---|---|---|---|---|
| 10% | 110.0 ±0.6 | 69.2 ±0.2 | +34.5 ±0.4 | −374.4 ±4.9 | −36824 ±659 | walk-left | stand-both |
| 20% | 110.0 ±0.6 | 80.2 ±0.3 | +33.3 ±0.4 | −273.7 ±4.8 | −23451 ±533 | walk-left | stand-both |
| 30% | 110.0 ±0.6 | 91.1 ±0.3 | +32.2 ±0.4 | −172.3 ±4.5 | −12296 ±408 | walk-left | stand-both |
| 40% | 110.0 ±0.6 | 102.3 ±0.4 | +30.9 ±0.4 | −72.1 ±4.1 | −3447 ±293 | walk-left | stand-both |
| 50% | 110.0 ±0.6 | 109.9 ±0.5 | +29.1 ±0.4 | −3.9 ±1.0 | +1384 ±68 | walk-left | tie |
| 60% | 110.0 ±0.6 | 110.0 ±0.6 | +24.6 ±0.4 | +2.6 ±0.4 | +1739 ±38 | walk-left | tie |
| 70% | 110.0 ±0.6 | 104.9 ±0.4 | −14.9 ±3.1 | +3.5 ±0.4 | −1058 ±237 | stand-both | stand-both |

- **With few walkers, walk-left wastes the walk lane.** At 10–40%, the
  standing side carries most people through one lane, and people who stand
  lose minutes per trip.
- **At 50–60% walkers**, the two lanes carry about the same load. Walk-left
  moves as many people as stand-both, and costs others little or nothing: at
  60%, they save 3 s.
- **At 70%**, the walk lane itself fills up, and walkers lose time too.
- At Holborn's height, about 45% walk (Davis & Dutta). That's between 40%,
  where walk-left costs people time in total, and 50%, where it saves time.

## 5. How busy it is, and blockers together

| arrival_rate | blocker_rate | stand-both people/min | walk-left people/min | Walkers save s | Others save s | Net saved, person-s/min | Fastest for walkers | Most people/min |
|---|---|---|---|---|---|---|---|---|
| 60 | 0% | 60.0 ±0.5 | 60.2 ±0.5 | +28.9 ±0.1 | −0.4 ±0.0 | +763 ±9 | walk-left | tie |
| 60 | 2% | 60.0 ±0.5 | 60.1 ±0.5 | +22.5 ±0.4 | −0.3 ±0.0 | +592 ±12 | walk-left | tie |
| 60 | 5% | 60.0 ±0.5 | 60.1 ±0.5 | +16.3 ±0.4 | −0.3 ±0.0 | +427 ±11 | walk-left | tie |
| 90 | 0% | 90.0 ±0.6 | 90.0 ±0.5 | +28.1 ±0.1 | −2.1 ±0.2 | +1026 ±16 | walk-left | tie |
| 90 | 2% | 90.0 ±0.6 | 90.1 ±0.6 | +17.1 ±0.5 | −1.7 ±0.2 | +600 ±25 | walk-left | tie |
| 90 | 5% | 90.0 ±0.6 | 89.9 ±0.6 | +8.4 ±0.5 | −1.4 ±0.2 | +266 ±23 | walk-left | tie |
| 110 | 0% | 110.0 ±0.6 | 107.3 ±0.4 | +30.1 ±0.4 | −28.4 ±3.2 | −266 ±204 | walk-left | stand-both |
| 110 | 2% | 110.0 ±0.6 | 107.7 ±0.5 | +6.3 ±2.3 | −20.2 ±2.6 | −951 ±195 | walk-left | stand-both |
| 110 | 5% | 110.0 ±0.6 | 105.7 ±0.4 | −28.9 ±4.0 | −12.7 ±1.9 | −2245 ±221 | stand-both | stand-both |
| 130 | 0% | 116.8 ±0.0 | 116.7 ±0.4 | +88.2 ±2.9 | −62.9 ±3.1 | +640 ±288 | walk-left | tie |
| 130 | 2% | 116.8 ±0.0 | 111.4 ±0.5 | +5.3 ±5.4 | −49.0 ±3.0 | −3238 ±271 | tie | stand-both |
| 130 | 5% | 116.8 ±0.0 | 107.6 ±0.2 | −66.0 ±4.5 | −32.9 ±2.7 | −6256 ±153 | stand-both | stand-both |

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
| 110 | 43% | 110.0 ±0.6 | 105.5 ±0.4 | +30.4 ±0.4 | −43.8 ±3.7 | −1341 ±246 | walk-left | stand-both |
| 120 | 39% | 116.2 ±0.2 | 105.7 ±0.4 | +48.7 ±2.2 | −113.8 ±3.4 | −6011 ±268 | walk-left | stand-both |
| 130 | 36% | 116.8 ±0.0 | 105.6 ±0.4 | +90.2 ±2.9 | −164.5 ±3.2 | −9349 ±316 | walk-left | stand-both |
| 140 | 34% | 116.8 ±0.0 | 105.7 ±0.4 | +135.5 ±3.0 | −211.1 ±3.3 | −13168 ±370 | walk-left | stand-both |
| 150 | 32% | 116.8 ±0.0 | 105.6 ±0.4 | +181.6 ±3.2 | −258.5 ±3.3 | −18038 ±433 | walk-left | stand-both |

- **Walk-left levels off at about 106 per minute:** 58.4 standing plus about
  47 walking. That's Davis & Dutta's measured total at this height, which is
  expected, since both lanes are fitted to their counts.
- **Stand-both carries 117 per minute, about 11% more.**
- **The extra people standing under walk-left wait far longer** than walkers
  save, so walk-left costs time in total. The gap grows with every minute the
  rush lasts. The sizes here are for a 15-minute run, but the direction holds
  for any run length.

## What the model leaves out

Each point below says which rule it likely favors.

- **No overtaking.** A walker can't pass a slower walker or a blocker. This
  makes blockers costly (it favors stand-both whenever there are blockers).
  Real walkers sometimes squeeze past. See the open questions in
  [ENGINE_DESIGN.md](ENGINE_DESIGN.md#open-questions).
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
- **Standing spacing is fixed.** Standers keep 0.74 m, fitted to Davis &
  Dutta's average at this height. Their formula is an average over escalators
  that scatter by several people per minute, and Holborn's highest reading
  (141 per minute with nearly everyone standing) means people sometimes stand
  closer still. Closer standing helps stand-both more, since it has two
  standing lanes. Section 10 shows how much the spacing matters.
- **Walkers step on like standers.** This slightly reduces walkers' saving
  (see the open questions in [ENGINE_DESIGN.md](ENGINE_DESIGN.md#open-questions)).
  It favors stand-both, by a little.

## Against real data

- **Holborn trial (Harrison et al. 2016):** on the all-standing day, single
  escalators carried up to about 90 per minute, as many as arrived, so that's
  a lower limit. The model's stand-both carries 117 per minute at full load,
  consistent with that limit.
- **Davis & Dutta (2002):** about 106 per minute in total under walk-left at
  this height, with a line waiting. The model gives the same with walking held
  at the measured rate (section 6). That's a check that the fit works, not
  independent support, since both lanes are fitted to these counts.
- **The trial's follow-up** found a benefit only at the busiest times (over
  about 100 arriving per minute). The model puts the switch between 100 and
  110 per minute.
- **Walkers' time saved has never been measured** (see
  [RESEARCH.md](RESEARCH.md#summary)). The 28 s at quiet times is the model's
  own answer.

## Against another model

Filippidis et al. (2025) simulated the same question with buildingEXODUS, on
a station modeled on Holborn: a 23.75 m rise, 0.75 m/s, 40% walkers, standers
leaving one empty step (0.8 m) and walkers two (1.2 m). See
[RESEARCH.md](RESEARCH.md#filippidis-gwynne-lawrence--galea-2025-station-simulation).

**Where the two agree:**
- **Walk-left helps when it's quiet, and everyone standing wins at the peak.**
  They see the switch at about 80–104 arriving per minute; this simulation at
  100–110.
- **Walkers save about 30 s on the escalator** (65.6 s riding against 33–37 s
  walking there; 28 s here).
- **Varied walking speeds hurt walk-left.** Walkers get held up behind slower
  ones in both models.

**Where they differ: how much more everyone standing carries.** At the peak,
everyone standing moves **19–39% more** people there, against **2.5–11%** here
(2.5–3.5% at 110–120 per minute with 45% walking; 11% with walking held at the
measured rate). Their walk-left levels off at 71–80 per minute; here it's
about 106.

**Settings explain little of the gap.** Running this simulation with their
settings:

| arrival_rate | stand-both people/min | walk-left people/min | Walkers save s | Others save s | Net saved, person-s/min | Fastest for walkers | Most people/min |
|---|---|---|---|---|---|---|---|
| 40 | 39.9 ±0.4 | 39.9 ±0.4 | +28.4 ±0.1 | −0.2 ±0.0 | +444 ±7 | walk-left | tie |
| 70 | 70.2 ±0.5 | 70.2 ±0.5 | +27.2 ±0.1 | −1.2 ±0.1 | +707 ±10 | walk-left | tie |
| 90 | 90.0 ±0.6 | 89.6 ±0.5 | +26.6 ±0.1 | −9.8 ±1.6 | +409 ±94 | walk-left | tie |
| 100 | 100.2 ±0.6 | 96.0 ±0.4 | +26.9 ±0.2 | −42.8 ±3.8 | −1539 ±248 | walk-left | stand-both |
| 120 | 112.4 ±0.1 | 104.2 ±0.4 | +62.2 ±2.6 | −115.0 ±3.2 | −5342 ±262 | walk-left | stand-both |

Everyone standing gains at most 8% here, even with their settings. The rest
likely comes from what their model has and this one doesn't. Under walk-left
at the peak, their walk lane carried only 27.5 per minute and their standing
lane 44.2, against about 48 and 56 here with their settings. The likely
reasons:
- people at the bottom get in each other's way while choosing a lane, which
  slows boarding;
- standers end up in the walk lane once it's crowded;
- walkers can't always reach a free space.

These are the same things listed in [What the model leaves out](#what-the-model-leaves-out).
Leaving them out favors walk-left here, so this simulation's 2.5–11% is probably
a low estimate of the gain at the peak. For walk-left alone, this model matches
Davis & Dutta's measured 106 per minute, and Filippidis et al.'s is well below
it. For the gain from everyone standing, the Holborn report's 27% more people
in an hour, on the escalator where everyone stood, sits between the two models.

## Double-checks

Three results above depend on small differences or on one uncertain setting,
so they were checked further. Sections 8 and 9 compare each crowd with itself
under the other setting ("same crowds"), which shows small differences far
more clearly than comparing two averages.

### 8. Walk-left at 50–60% walkers, and the standing spacing

With the engine's default spacing between standers (0.8 m, 54 per minute per
lane), walk-left moved about 3 more people per minute than stand-both at
55–60% walkers, and others saved 13–17 s. Was that real? All at 110 per
minute:

| standing lane | walk_fraction | stand-both people/min | walk-left people/min | Walk-left extra people/min, same crowds | Walkers save s | Others save s |
|---|---|---|---|---|---|---|
| 0.80 m (54.0/min) | 45% | 107.2 ±0.3 | 103.4 ±0.4 | −3.8 ±0.4 | +45.3 ±2.1 | −53.0 ±3.5 |
| 0.80 m (54.0/min) | 50% | 107.2 ±0.3 | 108.3 ±0.5 | +1.1 ±0.4 | +44.3 ±2.1 | −6.2 ±2.3 |
| 0.80 m (54.0/min) | 55% | 107.2 ±0.3 | 110.0 ±0.5 | +2.8 ±0.4 | +42.9 ±2.0 | +13.2 ±1.9 |
| 0.80 m (54.0/min) | 60% | 107.2 ±0.3 | 110.0 ±0.6 | +2.8 ±0.5 | +39.9 ±1.9 | +16.9 ±2.1 |
| 0.80 m (54.0/min) | 65% | 107.2 ±0.3 | 108.9 ±0.5 | +1.7 ±0.4 | +29.4 ±1.6 | +17.9 ±2.1 |
| 0.74 m (58.4/min) | 45% | 110.0 ±0.6 | 107.3 ±0.4 | −2.7 ±0.4 | +30.1 ±0.4 | −28.4 ±3.2 |
| 0.74 m (58.4/min) | 50% | 110.0 ±0.6 | 109.9 ±0.5 | −0.1 ±0.2 | +29.1 ±0.4 | −3.9 ±1.0 |
| 0.74 m (58.4/min) | 55% | 110.0 ±0.6 | 110.1 ±0.6 | +0.1 ±0.2 | +27.7 ±0.4 | +1.3 ±0.4 |
| 0.74 m (58.4/min) | 60% | 110.0 ±0.6 | 110.0 ±0.6 | −0.0 ±0.2 | +24.6 ±0.4 | +2.6 ±0.4 |
| 0.74 m (58.4/min) | 65% | 110.0 ±0.6 | 108.9 ±0.5 | −1.1 ±0.3 | +14.2 ±1.7 | +3.2 ±0.4 |

- **With Davis & Dutta's spacing, walk-left only ties at 50–60% walkers.**
  The gain of about 3 per minute came from the default standing lane being too
  small.
- **What's left is a narrow band where walk-left costs nobody time.** At
  55–60%, walkers save about 25–28 s, and others gain 1–3 s.
- **At Holborn's 45%, stand-both wins with either spacing.** Walk-left carries
  3–4 fewer people per minute.

### 9. A few blockers, with 200 crowds

Under walk-left, a few blockers move some standers from the full standing line
into the walk lane, which has room. Does that add people per minute? Walk-left
only:

| arrival_rate | blocker_rate | walk-left people/min | Change from 0% blockers, same crowds | walk lane people/min | standing lane people/min |
|---|---|---|---|---|---|
| 100 | 0% | 99.7 ±0.4 | +0.0 ±0.0 | 44.7 ±0.3 | 55.0 ±0.3 |
| 100 | 1% | 99.7 ±0.4 | −0.0 ±0.1 | 45.2 ±0.3 | 54.5 ±0.3 |
| 100 | 2% | 99.7 ±0.4 | +0.0 ±0.1 | 45.7 ±0.3 | 54.0 ±0.3 |
| 100 | 5% | 99.2 ±0.4 | −0.5 ±0.2 | 46.7 ±0.2 | 52.5 ±0.3 |
| 110 | 0% | 107.1 ±0.3 | +0.0 ±0.0 | 49.2 ±0.3 | 57.9 ±0.1 |
| 110 | 1% | 107.5 ±0.4 | +0.4 ±0.2 | 49.7 ±0.3 | 57.8 ±0.1 |
| 110 | 2% | 107.3 ±0.3 | +0.2 ±0.2 | 49.7 ±0.3 | 57.6 ±0.1 |
| 110 | 5% | 105.7 ±0.3 | −1.5 ±0.3 | 48.8 ±0.1 | 56.8 ±0.2 |
| 120 | 0% | 112.1 ±0.3 | +0.0 ±0.0 | 53.7 ±0.3 | 58.4 ±0.0 |
| 120 | 1% | 112.1 ±0.3 | +0.1 ±0.2 | 53.8 ±0.3 | 58.4 ±0.0 |
| 120 | 2% | 110.4 ±0.3 | −1.7 ±0.3 | 52.0 ±0.3 | 58.3 ±0.0 |
| 120 | 5% | 107.4 ±0.1 | −4.6 ±0.3 | 49.2 ±0.1 | 58.2 ±0.1 |

- **Barely.** At 110 per minute, 1% blockers add about 0.4 per minute, and at
  100 and 120 per minute, nothing.
- **From 2–5% blockers, the total falls.** The busier it is, the sooner: at
  120 per minute, 2% blockers cost about 1.7 per minute and 5% cost 4.6.

### 10. How busy it is, with both standing spacings

| arrival_rate | standing lane | stand-both people/min | walk-left people/min | Walkers save s | Others save s | Net saved, person-s/min | Fastest for walkers | Most people/min |
|---|---|---|---|---|---|---|---|---|
| 90 | 0.74 m (58.4/min) | 90.0 ±0.6 | 90.0 ±0.5 | +28.1 ±0.1 | −2.1 ±0.2 | +1026 ±16 | walk-left | tie |
| 90 | 0.80 m (54.0/min) | 90.0 ±0.6 | 89.9 ±0.5 | +28.6 ±0.1 | −5.0 ±0.8 | +901 ±43 | walk-left | tie |
| 100 | 0.74 m (58.4/min) | 100.2 ±0.6 | 99.9 ±0.5 | +28.2 ±0.1 | −6.7 ±1.1 | +887 ±66 | walk-left | tie |
| 100 | 0.80 m (54.0/min) | 100.1 ±0.6 | 98.2 ±0.4 | +30.2 ±0.3 | −22.9 ±2.9 | +61 ±172 | walk-left | stand-both |
| 110 | 0.74 m (58.4/min) | 110.0 ±0.6 | 107.3 ±0.4 | +30.1 ±0.4 | −28.4 ±3.2 | −266 ±204 | walk-left | stand-both |
| 110 | 0.80 m (54.0/min) | 107.2 ±0.3 | 103.4 ±0.4 | +45.3 ±2.1 | −53.0 ±3.5 | −997 ±234 | walk-left | stand-both |
| 120 | 0.74 m (58.4/min) | 116.2 ±0.2 | 112.3 ±0.4 | +47.7 ±2.2 | −54.8 ±3.3 | −1071 ±247 | walk-left | stand-both |
| 120 | 0.80 m (54.0/min) | 108.0 ±0.0 | 107.9 ±0.4 | +88.2 ±2.9 | −62.9 ±3.3 | +579 ±279 | walk-left | tie |

- **The direction is the same with either spacing.** Walk-left suits quiet
  times; near capacity, stand-both moves more people and costs less time in
  total.
- **With the default 0.8 m, everything happens 10 per minute sooner.**
  Stand-both already moves more people at 100 per minute, and at 110 standers
  lose 53 s instead of 28 s.
- **The rows at 120 per minute show why sustained overload is hard to read.**
  With 0.8 m, both rules are overloaded and the fixed 45% walking makes
  walk-left look better again, as in section 1 from 130 per minute.
