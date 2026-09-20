# H13 - User-mark annotation: the mark corpus we do not have

**Status:** AI drafted (no human review yet) · **Last updated:** 2026-09-21 · **Framing:** docs/PROBLEM_STATEMENTS.md §5, §8 · **Registry:** docs/hypotheses/README.md

## The data gap (read this first)

**We do not have enough data.** The annotation-led flow - a user marks
the period a device ran; the mark forms a device profile; the profile
disaggregates the aggregate - needs a corpus of hand-marked annotations
on public datasets. **No such corpus exists.** The only marks in the
repo are 20 washing-machine calibration cycles seeded into
data/gold_annot/ukdale/house_1/cycles.csv during the GT-cycle EDA - a
seed big enough to stabilize a scalar profile, far too small to validate
the flow. Producing marks on the public datasets (UK-DALE first: about
20 calibration marks per device, plus a strictly-later test span) is
**real data collection** - human review labor, review sheets,
provenance-tagged - and must be planned and resourced as such. Until it
runs, nothing downstream of device identification may be quoted as
validated.

## Statement (falsifiable)

Two-part:
(a) **Identification.** Marks identify their device: leave-one-out
nearest-mark on aggregate-only features beats chance substantially.
(b) **Disaggregation.** Marks support profile formation with predictive
power: profile-gated detection finds the device's cycles on unseen
aggregate data at useful P/R/F1.
Measured so far (single seed run, unreviewed): (a) yes - 0.79 vs 0.25
chance on 169 marks; (b) **not demonstrated** with scalar (dP, dur)
profiles - the major appliances' dP profiles nearly coincide and
aggregate runs chain across devices; a ceiling analysis bounds what any
run-anchored detector could recall. The hypothesis survives iff (a)
holds and (b) is demonstrated with a profile representation the corpus
can support (multi-activation rhythm, within-cycle shape, time-of-day,
assignment-style matching) - or the deliverable is honestly re-scoped
to identification + energy bounds.

## Why it matters

- This is the product's core hypothesis in its cheapest form: no extra
  hardware, no runtime submeter - the user's own annotation is the
  calibration. Everything above it rests on whether marks carry enough
  signal, which is a data-availability question before it is a
  modeling question.
- The missing corpus is the difference between "we showed a toy works"
  and "the flow works"; nobody reading the registry should mistake the
  20-mark seed for having the data.

## How to verify

1. **Annotate.** Review-sheet curation on UK-DALE house_1 (the GT-cycle
   EDA notebook generates candidates: rule cycles on the submeter
   channel, ranked by energy; the reviewer keeps spans covering exactly
   one coherent cycle). Extend data/gold_annot/ to all four canonical
   devices (washing_machine, dishwasher, kettle, microwave), at least
   20 marks each, one source tag per review pass. Marks stay strictly
   inside the calibration span; the test span is never annotated for
   calibration use.
2. **Identify.** Leave-one-out nearest-mark (or equivalent) on
   aggregate-only features; report confusion matrix + accuracy per
   device.
3. **Disaggregate.** Profiles built from marks only; scored against
   submeter cycle GT on a strictly later span under the §7 contract
   (episode-level P/R/F1 + energy share, UNKNOWN mandatory). Margin
   over the baseline ladder frozen before the run.
4. **Ceiling.** Per GT cycle: is there any qualifying aggregate
   activation inside it (and in-profile)? Separates detector loss
   (fixable attribution) from aggregate ambiguity (not fixable).

## Instrument

The GT-cycle EDA notebook - source
src/pipelines/04_eda_annot_gt_cycle/01_ukdale_gt_cycle_eda.py, render
docs/reports/gt_cycle/01_ukdale_gt_cycle_eda.ipynb. Parts A-D establish
the cycle-label rules (program 600 s/600 s; burst raw; duty excluded)
and the aggregate activation vocabulary; part E generates the review
sheets and loads the mark store; part F runs the identify/disaggregate
chain and the ceiling. Mark store: data/gold_annot/ (schema +
provenance in data/gold_annot/README.md). It is the second instrument
of the registry, beside the button-press calibration simulation (H02).

## Evidence so far

- [none] (measured but not owner-reviewed): single seed run on UK-DALE
  house_1 - identification 0.79 (169 marks); disaggregation with scalar
  profiles: WM F1 0.21, DW 0.09, kettle 0.11, MW 0.08 vs cycle GT;
  ceiling 0.88/0.86 (WM), 0.74/0.70 (kettle); scalar profile stable at
  10 marks, tight at 20 (bootstrap). All from the instrument above.
- Cycle-label findings carried alongside (not hypothesis evidence):
  the gold episode rule is the wrong label for cycles (program devices
  need program-scale dwell/merge); cycle onset is a quiet valve/fill
  phase, so profiles must use within-cycle activations, never the
  marked start point.

## Why the synthetic fixture cannot fill this gap (measured 2026-09-21)

The client's synthetic CSV (repo/WattWiser/data/raw/synthetic_shelly_data.csv,
30 d @ 5 s) was probed as a candidate source of cycle-episode labels. It
cannot stand in for the missing mark corpus:

- **Labels exist but are free.** Every appliance window ships its own
  `<device>_power_W` + `<device>_on` channel, exact by construction
  (label purity: OFF samples max 0.0 W). Transcribing them into
  data/gold_annot/ would record generator output, not human review -
  the store's entire point.
- **The label type the flow needs does not exist in it.** No dishwasher
  channel at all; the washing machine is a single ON window (27 windows
  in 30 d, 45-108 min) whose power is a random walk capped at 1500 W -
  no multi-stage program, no quiet fill onset, none of the within-cycle
  activation structure the GT-cycle EDA showed a real WM cycle has.
- **The difficulty is largely absent by construction.** Minute-level
  2+ ON is 1.7% of fixture samples vs 3.0% of 60 s buckets in the
  UK-DALE gold EDA (5 canonical targets) - comparable at that
  resolution. The gap is at event level: fixture device runs essentially
  never begin during another appliance's run, while in the gold EDA about
  half of kettle/washer/dishwasher events do (the fridge is ON 42% of
  the time). The four dP profiles are cleanly separated (kettle 2011 /
  microwave 1021 / WM 1648 W p50; UK-DALE: 2439 / 1787 / 2844 W, nearly
  coincident); every large fixture aggregate step traces to a labeled
  appliance (labeled share 29%), while the real aggregate's
  non-canonical ~66% is bursty competing appliance activity, not smooth
  base load.
- **Measured on its own substrate** (cal days 1-15, test days 16-30,
  aggregate-only features, same scalar-profile chain as the UK-DALE
  instrument): LOO identification 0.994 (n=697, chance 0.25; UK-DALE:
  0.79); detection ceiling 0.96-1.00 (UK-DALE: 0.74-0.88); detection F1
  0.00-0.15 with the UK-DALE-tuned thresholds, 0.56-0.73 re-tuned to the
  fixture's own 265 W base - the number is a function of threshold fit to
  the fixture, not of a validated mechanism. The real-data collapse
  mechanism (attribution among coincident profiles and runs chained
  across devices) is exactly what the fixture omits.

Verdict: the fixture validates plumbing only (tier-A role in
experiment-data-strategy.md); it cannot arbitrate H13's open question
(whether richer profiles close the disaggregation gap) and cannot
substitute for annotating the public dataset. Correction carried here:
repo-review.md's "single simulated day replayed 30 times" is too strong -
the file is one diurnal template (hourly-mean base corr 0.9998 across
days) with fresh per-day noise and re-drawn appliance schedules; the
unusable-as-substrate verdict is unaffected. Second correction
2026-09-21: an earlier draft contrasted the fixture's 1.7% with
"UK-DALE house_1: 32.7%" 2+ ON. That figure came from the deprecated
6-channel reference slice (research-logs/sakunrasilka_nilm-test2), which
signal forensics showed is UK-DALE house_5 data (four channels verbatim)
with a synthetic sum aggregate and an always-on "monitor" channel -
not house_1. The gold-EDA numbers above replace it.

## Open questions

- Does a richer profile (multi-activation rhythm, within-cycle shape,
  time-of-day priors) close the disaggregation gap, or does the
  aggregate-ambiguity ceiling cap the whole flow? (Ceiling rows decide.)
- Corpus size for the richer representation: is 20 per device still
  enough? (Bootstrap re-run per feature set.)
- Annotator protocol: do the review-sheet keep/reject rules survive a
  cheaper, non-expert annotator? (Label-trust discipline as in REFIT.)
- Transfer: do marks collected on UK-DALE house_1 transfer across
  houses (H09 form), or is per-house annotation required?

## History

- 2026-09-21 - probed the client synthetic fixture as a candidate
  cycle-label source: labels free by construction, no program structure,
  difficulty absent by construction; measured identification 0.994 and
  threshold-dependent detection F1 (0.00-0.73) on its own substrate.
  Recorded under "Why the synthetic fixture cannot fill this gap".
- 2026-09-21 - created from the GT-cycle EDA on owner direction: record
  that the mark/annotation corpus is missing, that annotating the
  public dataset is the real data-collection task for this line, and
  that the flow is validated only at identification so far.
