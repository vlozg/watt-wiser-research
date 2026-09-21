# Phases, solar, and the aircon question, explained like you're five

Why the wiring in the house changes what the meter sees. This is the primer
behind two practical questions: "is our panel single-phase or three-phase", and
"why did we order a meter with three CT clamps".

## One pipe or three pipes

The plumbing analogy from `ELI5_NILM.md`: voltage is pressure, current is
flow. A **phase** is one pipe into the house.

- **Single-phase** (most houses): one active wire + one neutral. All the
  household power flows through that one pipe. In Australia the push is about
  230 V, and a typical main switch lets the whole house share roughly
  14-15 kW through it.
- **Three-phase**: three active wires, each carrying its own 230 V supply,
  fed from the street in a rotating pattern. Three pipes means roughly three
  times the total capacity. Between any two actives you measure about 400 V;
  each active to neutral is still 230 V, so ordinary appliances do not care.

Why does a house get three-phase at all? Capacity. The loads that tend to
push a single pipe past its limit:

- **Ducted / large air-conditioning** - one big compressor gulp.
- **Large rooftop solar** - pushing power back to the street needs pipe
  capacity too, not just drawing it.
- **EV fast charging**, big workshops, some pools and spas.

(For contrast: US homes are built differently - one service wire pair giving
two "halves" at 120 V each, 240 V across the pair. That is called split-phase,
and it is why the US dataset REDD records two mains channels that must be
summed. It does not apply in Australia.)

## How to tell from a photo - no contact needed

Look at the **main switch** in a switchboard photo:

| What you see | What it means |
|---|---|
| One thick active cable into the main switch, plus one neutral | Single-phase. One CT on the active sees the whole home. |
| Three thick active cables into the main switch | Three-phase. One CT per active; the whole-home number is the **sum of all three**. |
| A separate solar breaker with its own cables | There is rooftop PV - it deserves its own CT. |

Counting cables in a photo is a purely visual check. Nobody needs to touch
anything to answer the phase question.

## Why solar flips the picture

A solar inverter pushes power back down the same wire the house pulls from.
The mains meter sits on that shared wire, so it reads:

```
mains reading = house consumption - solar generation
```

In Australia roughly one in three houses has rooftop solar, so this is not an
edge case - it is likely to be our house.

What that does to the data, visualized: a normal house is a staircase line
wandering between a night floor and an evening peak. A solar day shows the
**duck curve** instead: a morning ramp, then a **midday dive toward zero or
below** (power flowing backwards to the street reads as negative watts), then
the evening peak. The nasty consequence: an appliance switching on at noon may
show **no rise at the mains at all**, because the solar was about to spill to
the street and the appliance took its slice back. The kettle still draws its
2,000 W - it is just invisible in the mains number.

That is the "PV breaks the heuristic approach unless separately metered" line
in `docs/research/research-brief.md` (the scope questions). With one CT on the
solar circuit the arithmetic is trivial and the reconstructed consumption
trace looks like a normal house again.

## Why ducted aircon matters twice

1. It is a common **reason a house has three-phase**: the compressor's gulp
   exceeds what one pipe can give.
2. It is a hard neighbour in the data. An old aircon is a multi-kilowatt block
   that starts, runs for hours, and cycles - already a lot of masking. A modern
   **inverter** unit is trickier: it does not step on cleanly, it ramps and
   then *modulates* continuously between a whisper and full noise. In the data
   that is a long slow ramp with a drifting plateau - no clean edges for a
   step-change detector, and hours of background noise that smaller appliances
   have to shout over.

## What the data looks like when you plot it

- **Single-phase house** (what UK-DALE's flagship house shows): one staircase.
  Kettle = short 2,000 W+ spikes. Fridge = a sawtooth cycling around
  100-200 W. Dishwasher = a long low block hiding an internal heater spike.
  See the poster-week and one-day figures in
  `docs/reports/dataset_eda/01_ukdale_eda.ipynb`.
- **Three-phase house**: three smaller staircases. Each big appliance sits on
  one phase permanently, so its steps appear in exactly one channel; the
  whole-home line is the sum. ECO's Swiss buildings are the corpus example
  sitting on a three-phase 400 V service
  (`docs/reports/dataset_eda/04_eco_eda_peer_review.md`).
- **Solar day**: midday, the mains line dives to zero or negative while the
  actual house staircases continue unseen underneath. Add a PV channel and you
  can draw "consumption = mains + solar" - the staircase reappears.

## Can we transform between the shapes?

This is the domain-shift worry, and the answer is asymmetric:

- **Three-phase → our aggregate: easy and standard.** Add the phase channels.
  That is literally what a utility meter does, and what REDD processing does
  with its two mains legs (`docs/reports/dataset_eda/00_overview.md`). A
  detector trained on a summed aggregate does not care how many phases
  produced the sum. So a three-phase pilot house does **not** block the
  approach - the per-phase channels are a bonus (each one sees fewer
  simultaneous appliances, which would *reduce* the masking noise that buried
  the dishwasher/washing-machine class in the quick experiment). A bonus worth
  testing, not yet promised.
- **Our aggregate → three-phase: the hard direction.** Splitting one line into
  phases requires knowing which appliance sat on which phase, and public
  aggregate data does not carry that. If we ever need it, the honest version
  is assignment-based simulation from our hand-annotated marks
  (`data/gold_annot/`): give each appliance a fixed phase, then build each
  phase's trace appliance by appliance. Random splitting fakes the picture,
  because per-phase peaks and masking come from the *fixed* assignment.

The domain-shift axes that actually matter are the ones our docs already
track (`docs/datasets/experiment-data-strategy.md`): voltage level (120 V US
vs 230 V AU/UK vs 220 V VN), plug culture, appliance fleet, climate and
seasonality, and sampling cadence. Phase count is not one of them, as long as
we compare summed aggregates.

## CT placement cheat-sheet (Pro 3EM, three clamps)

| Panel situation | Where the CTs go |
|---|---|
| Single-phase, no solar | 1 on the main active; 2 spare (or one on a heavy circuit) |
| Single-phase + solar | 1 on mains, 1 on the solar inverter circuit, 1 spare |
| Three-phase | 1 per phase (aggregate = the sum; solar shows up inside the sum) |

Cross-refs: `docs/research/research-brief.md` section 4 (what the meter
actually collects), `docs/datasets/experiment-data-strategy.md` (the
method-not-market caveat), `docs/knowledge/ELI5_NILM.md` (the base analogy).
