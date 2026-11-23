# Research: studies on standing vs. walking on escalators

This document collects the studies relevant to the question this project
tests: **does an escalator move more people when everyone stands on both
sides than when people stand on one side and walk on the other?**

It is meant as a reference for later work. Each entry says what the study
did, what it found, **how carefully we've checked it**, and what it means for
this simulation. For how the simulation works, see `ENGINE_DESIGN.md`. For the
design and the reasons behind it, see `PLAN.md`.

Last updated: 21 November 2026.

## How much to trust each entry

Each study is marked with how closely it has been read:

| Mark | Meaning |
|---|---|
| **Used in the code** | Numbers from it are checked by the tests (`tests/test_calibration.py`) |
| **Read in full** | The study itself was read |
| **Abstract only** | Only the summary was read; numbers may lack context or units |
| **Second-hand** | Known only from news or other reports; the original wasn't found or read |

## Summary

| Study | Year | Kind | What it says | Checked |
|---|---|---|---|---|
| [Davis & Dutta](#davis--dutta-2002-counts-at-10-london-stations) | 2002 | Counts at 10 London stations | Under stand-right/walk-left, people per minute on each side depends on escalator height | Used in the code |
| [Harrison et al., Holborn trial](#harrison-et-al-2016-the-holborn-trial) | 2016 | Real-world trial | Everyone standing moved more people at peak times on a tall escalator | Used in the code |
| [Canary Wharf study](#canary-wharf-study-2015) | 2015 | London Underground study | On shorter escalators, everyone standing would move *fewer* people | Second-hand |
| [Yamamoto, Yanagisawa & Nishinari](#yamamoto-yanagisawa--nishinari-2019-simplified-model) | 2019 | Simplified mathematical model | Two standing lanes are better for large crowds; a walking lane helps only with few people | Read in part |
| [COVID-era simulation](#covid-era-simulation-2021) | 2021 | Computer simulation | Standing on both sides moved more people | Second-hand |
| [Japan's rules against walking](#japans-rules-against-walking-2021-onwards) | 2021– | Local rules and before/after counts | People went back to walking within about a year | Second-hand |
| [Filippidis et al.](#filippidis-gwynne-lawrence--galea-2025-station-simulation) | 2025 | Simulation of each person in a station, compared with Holborn | Everyone standing moves 19–39% more people once the crowd at the bottom reaches about 1 person per m²; walkers save about 30 s on the escalator | Read in full |

**Where the studies agree:** standing on both sides moves more people when
the escalator is **tall** and the bottom is **crowded**. With few people or
short escalators, a walking lane can be as good or better.

**Where they are silent:** no study found so far *measures* how much time
walkers save. Filippidis et al. *simulate* it (about 30 s on a 24 m
escalator), which matches this simulation's 29 s. Davis & Dutta and the Holborn trial show that walkers care about
time, but neither puts a number on it (see "Walkers' time" in each entry). Few
studies look at how well people keep to a rule over time. Both matter for
this project's `feature/time-saved` work and for the rule-breaking settings
(`defect_threshold`, `defect_prob`, `blocker_rate`).

## Studies used in the code

### Davis & Dutta (2002): counts at 10 London stations

**Checked:** used in the code (`tests/test_calibration.py`, class
`DavisDutta2002`) and read in full.

P. Davis and G. Dutta (2002). "Estimation of Capacity of Escalators in London
Underground." IIM Ahmedabad working paper 2002-11-01.
[PDF](https://www.iima.ac.in/sites/default/files/rnpfiles/2002-11-01GoutamDutta.pdf)

**What they did:** counted people standing and people walking separately on
busy up escalators at 10 central London stations, while a line was waiting at
the bottom. All escalators were under stand-right/walk-left. Escalator heights
(rise) ranged from about 7.6 m to 23.4 m. **Holborn was one of the stations**:
they counted escalators 4–7 (Figure 6.4). Holborn 5, at 23.39 m, is the
tallest in their data (Chart 7.2). The same tall escalators were later used
for the 2015 trial.

**What they found:** two formulas for people per minute on each side, by
height:

```
standing side = 41.27 + 0.73 × rise
walking side  = 83.49 − 1.20 × rise − 8.05 (if one of a pair of escalators)
```

So the walking side carries more people on short escalators, and fewer on tall
ones, because fewer people are willing to walk a long way up. Escalators ran at
0.72 m/s with 0.4 m steps.

**Use in this project:** the walking spacing (`walk_gap` = 0.9 m) was chosen
so the simulation matches the walking-side formula at every height. The
belt speed and step depth come from the paper. The tests allow 10% difference
per lane, because individual escalators in the paper scatter around the
formulas by several people per minute.

**Known mismatch:** in the paper, the standing side carries more people on
taller escalators (people squeeze in from the walking line). The simulation's
standing side carries a fixed number, so it is about 7% low at 23 m.

**Their own Holborn experiment (section 8.1):** Holborn already asked people
to stand on both sides of the up escalators when busy. With the supervisor's
help, announcements ran about every two minutes. Findings, all on escalator 3:
- **Most people ignored the announcements.** They believed walking carried
  more people, or wanted to save their own time.
- **Only two readings had both sides standing.** They gave **49.4 per minute
  on the standing side and 75.6 per minute standing on the walking side**,
  about 10 more than usually walk there. 75.6 standing in one lane is more
  than this simulation allows (54 per minute at 0.72 m/s with one empty step),
  so people must have stood closer together.
- **People stood only because one or two did**, which forced everyone behind
  them to stand. Those behind kept pushing to walk, and in both readings they
  soon did.
- **Their conclusion:** the experiment couldn't show what an escalator carries
  when everyone stands. Finding out would take counts from systems where
  standing on both sides is normal, or a simulation of people on and around
  escalators.

**Walkers' time:** not measured. Two related points:
- **People in a hurry walk more (measured).** On Friday nights at Leicester
  Square and Tottenham Court Road, when most riders weren't commuters, about
  **10.9 fewer people per minute walked**, and 3.6 more stood. The authors
  explain this by commuters wanting "to minimise travel time", while other
  riders, "being in less of a hurry, are less likely to walk up escalators"
  (section 6.2.5).
- **Walking speed is assumed, not measured.** The paper's own capacity
  calculation assumes walkers climb at 36 m per minute (0.6 m/s) on top of the
  belt (section 5.2.1). It never works out the time this saves.

### Harrison et al. (2016): the Holborn trial

**Checked:** used in the code (`tests/test_calibration.py`, class
`HolbornTrial2015`) and read in full.

Harrison et al. (2016). "Pilot for Standing on Both Sides of Escalators."
6th Symposium on Lift & Escalator Technologies.
[PDF](https://liftescalatorlibrary.org/paper_indexing/papers/00000115.pdf)

**What they did:** London Underground asked passengers on the up escalators
at Holborn station (23.4 m rise) to stand on both sides, in pilots from 2015
into 2016, and counted people.

**What they found:**
- On the all-standing day (8 December 2015), single escalators carried up to
  about **450 people per 5 minutes**, about **90 per minute** (read from
  Graph 3). The counts matched the ticket gates, so this is a lower limit on
  what the escalator could carry, not its maximum.
- The often-quoted figures of **81 vs. 112.5 people per minute** were
  calculations made *before* the trial, not measurements.
- A follow-up in April–May 2016 found the benefit only at the busiest times
  (over about 100 people per minute arriving), with no clear difference at
  quieter times ([Wikipedia](https://en.wikipedia.org/wiki/Escalator_etiquette)).
  No permanent rule was introduced.

**Use in this project:** a test checks that the simulation, with everyone
standing on a 23.4 m escalator, carries at least the 90 per minute observed.

**Conflicting figures:** news reports give different numbers. Londonist
reports about 151 per minute standing vs. 115 normally
([Londonist](https://londonist.com/london/transport/the-results-of-the-holborn-standing-escalator-trial-are-in)),
and other sites give 141 vs. 115. These don't match the symposium paper read
for this project. **Partly resolved:** Filippidis et al. (2025) trace 141 vs.
115 to the full London Underground report (Harrison et al. 2017, pp. 94–95).
There, they're the *highest* flows observed, not averages, and walkers could
be counted twice
([details](#filippidis-gwynne-lawrence--galea-2025-station-simulation)). The
151 figure is still unexplained. **Quote 141 vs. 115 only as peak flows.** An
earlier test at Holborn in 2002 was judged
inconclusive, because people didn't keep standing on both sides for long
([IanVisits](https://www.ianvisits.co.uk/articles/holborn-tests-standing-on-both-sides-of-the-escalator-15833/)).
This is very likely Davis & Dutta's own experiment
([details](#davis--dutta-2002-counts-at-10-london-stations)).

**Walkers' time:** not measured. The trial planned "timed walks from
platforms" (section 4.2), but the report gives no results for them. The only
mention of time comes from passenger complaints: recurring themes were that
the trial wouldn't work, that people felt "deprived of the choice to walk",
and that it "delays their journey" (section 5.2.1). Three people supported the
trial but wanted at least one escalator kept for walking.

## Other studies

### Canary Wharf study (2015)

**Checked:** second-hand (Londonist only).

**What it found:** a 2015 London Underground study at Canary Wharf found that
requiring everyone to stand would **reduce** the number of people carried by
about 10%. The escalators there are shorter, so more people walk, and the
walking side carries more.

**Use in this project:** a second test case besides Holborn: the simulation
should show walk-left winning on short escalators. That matches what Davis &
Dutta's formulas suggest. The original study hasn't been found.

### Yamamoto, Yanagisawa & Nishinari (2019): simplified model

**Checked:** read in part (about the first half verbatim; the rest from a
summary).

H. Yamamoto, D. Yanagisawa and K. Nishinari (2019). "Comparison of escalator
strategies in models using a modified totally asymmetric simple exclusion
process." [arXiv:1904.03988](https://arxiv.org/abs/1904.03988). A related
journal version is listed as *Physica A* (2020),
doi:10.1016/j.physa.2020.124571 (not checked).

**What they did:** a deliberately simple model. Each lane is a row of slots,
people move forward one slot at a time, and walkers sometimes move two. It has
no real distances, speeds or times, and wasn't compared with real counts. It
compares two standing lanes, one standing and one walking lane, and two walking
lanes.

**What they found:**
- With many people, **two standing lanes get everyone through faster**. With
  one standing and one walking lane, it does best when exactly half the people
  want to walk, and even then it carries fewer people than two standing lanes.
  Otherwise one lane gets overloaded while the other has room.
- A walking lane is better **only with few people**, an uncrowded entrance and
  many people who want to walk.
- **Even in a big crowd, the first people to arrive get through faster with a
  walking lane.** The benefit to individuals and the benefit to everyone can
  point in opposite directions.

**Use in this project:** the last point is what `feature/time-saved` sets out
to measure (time saved by people who want to walk, against the cost to everyone
else). The share of people who want to walk (`walk_fraction`) should matter a
lot; this project's sweeps can check that.

### COVID-era simulation (2021)

**Checked:** second-hand (search summary only).

"Assessing escalator pedestrian traffic dynamics amid COVID-19 pandemic using
hybrid simulation."
[ResearchGate](https://www.researchgate.net/publication/354052831_Assessing_escalator_pedestrian_traffic_dynamics_amid_COVID-19_pandemic_using_hybrid_simulation)

**What it found:** compared standing on both sides, walking on both sides and
stand-right/walk-left, and found that standing on both sides moved more
people. How it treated social distancing is not known.

### Japan's rules against walking (2021 onwards)

**Checked:** second-hand (news reports; the original study wasn't found).

**What happened:** Saitama Prefecture (from 1 October 2021) and Nagoya (from 1
October 2023) made rules asking people not to walk on escalators. Neither has
a penalty. Nagoya's lets people stand on either side
([Sumimasen Guide](https://sumimasenguide.com/articles/escalator-manners-japan),
[Mothership](https://mothership.sg/2023/10/nagoya-escalator-walking/)).

**What was found:** on one escalator at Omiya station, the share of people
walking fell from **62% to 38%** within three months of Saitama's rule, but
was back at **61%** by 2022 ([Mothership](https://mothership.sg/2023/10/nagoya-escalator-walking/)).
The reasons given for the rules are safety (805 accidents from improper use in
2018–2019, according to the Japan Elevator Association) rather than moving
more people. No study of people per minute was found.

**Use in this project:** a rule to stand on both sides only works if people
keep to it, and here they mostly stopped within about a year. That's a reason
to test how sensitive the results are to people breaking the rule
(`defect_threshold`, `defect_prob`, `blocker_rate`).

### Filippidis, Gwynne, Lawrence & Galea (2025): station simulation

**Checked:** read in full (22 pages).

L. Filippidis, S. M. V. Gwynne, P. J. Lawrence and E. R. Galea (2025).
"Assessing the impact of rider-only escalator etiquette using agent-based
modelling." *Safety Science* 196, 107064. doi:10.1016/j.ssci.2025.107064.
Open access, CC BY 4.0.
[University of Greenwich record](https://gala.gre.ac.uk/id/eprint/51899/) ·
[ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0925753525002899)

**What they did:** simulated people leaving a made-up station modeled on
Holborn, with the buildingEXODUS software, which moves each person on a grid
of 0.5 m squares.
- **Escalator:** 23.75 m rise, 49.6 m long horizontally, belt 0.75 m/s, steps
  0.4 m. A standing ride takes about 65.6 s.
- **People:** two trains release 450 people, who arrive at the escalator at
  14–120 per minute. That gives a crowd at the bottom of 0.1–4 people per m².
- **Two rules:** 0% walkers (everyone stands on both sides) or 40% walkers
  (stand right, walk left). The 40% comes from London Underground counts for a
  24 m escalator. Walking speeds on the escalator vary from 0.32 to 1.51 m/s.
  One extra case gave every walker the same speed (0.915 m/s).
- **Spacing:** standers leave one empty step (0.8 m) and walkers two (1.2 m),
  from Al-Sharif (1996).
- **Behavior:**
  - Walkers win more of the jostling for space at the bottom.
  - A walker can overtake a slower walker by stepping into the right lane,
    if there's room there.
  - When the area at the bottom is more than 75% full, the two lines break
    up. Standers may then board the walk lane and block the walkers behind
    them.
- **Runs:** 50 for each case. People per minute was measured only while the
  flow was steady.

**What they found** (all percentages):
- **People per minute:**
  - Everyone standing levels off at about **99 per minute**. Walk-left levels
    off at about **80**, and drops to **71** at 4 people per m².
  - Everyone standing moves **0–12% more** below 1 person per m² (under about
    80 arriving per minute), and **19–39% more** above it.
  - At the peak, walk-left's walk lane carried only **27.5 per minute**, and
    its standing lane 44.2.
- **Time on the escalator:** standers **65.6 s**; walkers **33.2 s** when
  quiet and **37.0 s** at the peak (held up by slower walkers). So walking
  saves about **30 s**.
- **Time per person from platform to exit**, after removing the time spent
  waiting to arrive:
  - Walk-left is **10–13% faster on average** up to 1 person per m². Under
    walk-left, walkers are 20–34% faster than standers.
  - At 2–3 people per m² the two rules are within 3%.
  - At 4 people per m², everyone standing is **26.5% faster** on average.
- **Time to empty the station:** 12–21% shorter with everyone standing from 1
  person per m² up (67% with the waiting-to-arrive time removed, at 4 per m²).
- **Time stuck in crowds:** 45–74% less with everyone standing. With every
  walker at the same speed, only 16% less, because walkers no longer get
  stuck behind slower ones.

**From their review of other sources** (useful here):
- **Where the "141 vs 115" figures come from.** They're the *highest* flows
  observed at Holborn in the full London Underground report (Harrison et al.
  2017, pp. 94–95): 141 per minute with nearly everyone standing, 115 with
  40–60% walking. Most readings fell between 50 and 100 per minute. Someone
  was counted as a walker after walking 5 m, so walkers could be counted
  twice. See [the Holborn trial](#harrison-et-al-2016-the-holborn-trial).
- **The trial over one hour:** an escalator managed as standing-only carried
  **27.3% more** people than one where walking was allowed (16,220 vs 12,745).
- **Share who walk by height** (Holborn report): % walking ≈ −0.142h² +
  0.8237h + 101.5, with h the escalator height in meters. This gives 40% at 24
  m and 43% at 23.4 m (this project uses 45%). The first minus sign was read
  from a character the PDF doesn't map to text, so check it before relying on
  it. The formula only makes sense near those heights; it gives over 100% for
  short escalators.

**Use in this project:**
- **The same answer.** Walk-left helps when it's quiet; everyone standing wins
  at the peak. The switch comes at about 80–104 arriving per minute there, and
  100–110 in this simulation. See
  [FINDINGS.md](FINDINGS.md#against-another-model).
- **Walkers save about 30 s** in both models.
- **Everyone standing gains much more there** (19–39%, against 4–7% here).
  Their walk-left carries far fewer people at the peak. Likely reasons:
  - their wider walker spacing (1.2 m, against 0.9 m here, fitted to Davis &
    Dutta);
  - the crowd at the bottom slowing everyone's boarding;
  - an underused walk lane.

  This simulation's walk-left is closer to Davis & Dutta's measured total at
  this height (about 106 per minute).
- **Things their model has and this one doesn't:**
  - overtaking;
  - blockers who appear only when it's crowded;
  - boarding slowed by the crowd at the bottom.

  See the open questions in [TIME_SAVED_PLAN.md](TIME_SAVED_PLAN.md#open-questions).

## Open questions for this project

Questions the studies raise that this simulation could help answer:

1. **At what escalator height does the answer flip?** Holborn (23.4 m) favors
   standing; Canary Wharf (shorter) favors walk-left. A sweep over `rise`
   could find the crossover.
2. **How much time do walkers save, and what does it cost everyone else?**
   Yamamoto et al. suggest the answers point in opposite directions. No study
   measures it, though Davis & Dutta and Holborn show walkers care. The
   simulation's answer at Holborn's height is in [FINDINGS.md](FINDINGS.md).
3. **How much rule-breaking can a stand-on-both-sides rule survive?** Japan's
   experience suggests people drift back to walking.
4. **Does the simulation agree with Filippidis et al.?** On the direction and
   on walkers' time saved, yes; on how much more everyone standing carries,
   no (19–39% there, 4–7% here). See
   [FINDINGS.md](FINDINGS.md#against-another-model). Running this
   simulation with their settings (40% walkers, 1.2 m walker spacing, 0.75 m/s)
   would show how much of the gap the settings explain.

## Adding a study

For each new study, add a row to the summary table and a section with: the
full reference and a link, how carefully it was checked (using the marks
above), what was done, what was found (with units), and what it means for
this project. If its numbers are used in the code, say which test checks them.
