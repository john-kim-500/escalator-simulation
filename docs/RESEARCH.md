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
| [Filippidis et al.](#filippidis-gwynne-lawrence--galea-2025-station-simulation) | 2025 | Simulation of each person in a station, compared with Holborn | Everyone standing helps once the crowd at the bottom reaches about 1 person per m² | Abstract only |

**Where the studies agree:** standing on both sides moves more people when
the escalator is **tall** and the bottom is **crowded**. With few people or
short escalators, a walking lane can be as good or better.

**Where they are silent:** few studies measure how much time walkers
actually save, or how well people keep to a rule over time. Both matter for
this project's `feature/time-saved` work and for the rule-breaking settings
(`defect_threshold`, `defect_prob`, `blocker_rate`).

## Studies used in the code

### Davis & Dutta (2002): counts at 10 London stations

**Checked:** used in the code (`tests/test_calibration.py`, class
`DavisDutta2002`).

P. Davis and G. Dutta (2002). "Estimation of Capacity of Escalators in London
Underground." IIM Ahmedabad working paper 2002-11-01.
[PDF](https://www.iima.ac.in/sites/default/files/rnpfiles/2002-11-01GoutamDutta.pdf)

**What they did:** counted people standing and people walking separately on
busy up escalators at 10 central London stations, while a line was waiting at
the bottom. All escalators were under stand-right/walk-left. Escalator heights
(rise) ranged from about 7.6 m to 23.4 m.

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

### Harrison et al. (2016): the Holborn trial

**Checked:** used in the code (`tests/test_calibration.py`, class
`HolbornTrial2015`).

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
and other sites give 141 vs. 115. These don't match the report as read for
this project. They may count something different (for example, a pair of
escalators, or a peak rather than an average). **Don't quote them without
checking the original report.** An earlier test at Holborn in 2002 was judged
inconclusive, because people didn't keep standing on both sides for long
([IanVisits](https://www.ianvisits.co.uk/articles/holborn-tests-standing-on-both-sides-of-the-escalator-15833/)).

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

**Checked:** abstract only. The full paper is free to read, but its text
couldn't be extracted with the tools available when this was written.

L. Filippidis, S. M. V. Gwynne, P. J. Lawrence and E. R. Galea (2025).
"Assessing the impact of rider-only escalator etiquette using agent-based
modelling." *Safety Science* 196, 107064. doi:10.1016/j.ssci.2025.107064.
Open access, CC BY 4.0.
[University of Greenwich record](https://gala.gre.ac.uk/id/eprint/51899/) ·
[ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0925753525002899)

**What they did:** simulated each person leaving an underground station,
including the escalator, using the buildingEXODUS software. The escalator was
24 m tall (close to Holborn's 23.4 m). They varied how many people arrived and
compared everyone standing with stand-right/walk-left. Results were compared
with the Holborn trial.

**What they found:**
- Everyone standing **clearly helps once the crowd at the bottom of the
  escalator reaches about 1 person per square metre or more**.
- At 4 people per square metre, the abstract reports: people carried up by
  38.9, time to empty the station down by 66.77, time per person down by 26.5.
  **The abstract gives no units**; these are probably percentages, but that
  needs checking in the full paper.
- Time spent in crowded conditions fell in every case tested (by 15.8 to 74.2
  for everyone).
- The abstract says nothing about benefits to walkers, people breaking the
  rule, or how many people wanted to walk.

**Use in this project:** this is the study closest to this simulation, and
the best one to compare results with. One difference: it measures crowding as
**people per square metre at the bottom**, while this simulation counts
**people in line**. Comparing the two would need an assumed size for the
waiting area.

**To do:** read the full paper for its settings (walking speeds, spacing,
share of walkers, demand levels) and the units of its results.

## Open questions for this project

Questions the studies raise that this simulation could help answer:

1. **At what escalator height does the answer flip?** Holborn (23.4 m) favours
   standing; Canary Wharf (shorter) favours walk-left. A sweep over `rise`
   could find the crossover.
2. **How much time do walkers save, and what does it cost everyone else?**
   Yamamoto et al. suggest the answers point in opposite directions. This is
   the `feature/time-saved` work.
3. **How much rule-breaking can a stand-on-both-sides rule survive?** Japan's
   experience suggests people drift back to walking.
4. **Does the simulation agree with Filippidis et al.?** It would need their
   settings and a way to compare crowding per square metre with people in line.

## Adding a study

For each new study, add a row to the summary table and a section with: the
full reference and a link, how carefully it was checked (using the marks
above), what was done, what was found (with units), and what it means for
this project. If its numbers are used in the code, say which test checks them.
