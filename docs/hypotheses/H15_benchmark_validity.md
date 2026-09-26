# H15 - Benchmark validity: the v1 episode benchmark was unlearnable; cycle scoring with a sanity gate is the valid instrument

**Status: proved** (defect reproduced exactly on 2026-09-30; replacement
protocol validated by a sanity gate; owner approved the change).

## Claim

An evaluation benchmark for this transfer-NILM problem is only valid if a
near-perfect predictor scores near-perfect on it. The v1 autoresearch
benchmark failed that test; protocol v2 passes it.

## The defect (v1, reproduced)

External review alleged the benchmark was broken; every allegation was
reproduced to the third decimal (evidence: the ceiling-test battery in
.scratch/ceiling_test.py + log run 28):

- GT "episodes" were flicker/recording-gap fragments, not cycles: over a
  90-day span the fridge GT held 28,034 episodes (83% shorter than 36 s)
  vs 1,337 real compressor cycles; the dishwasher 1,353 episodes vs ~10
  real cycles per 30 days. Cause: ~68k single-sample NaN runs per device
  channel shred the threshold mask into p50 = 30 s fragments.
- Consequence: a median-3-smoothed **perfect** predictor scored
  kettle 0.425 / microwave 0.703 / fridge 0.043 / wm 0.460 / dw 0.006
  under v1 episode matching; 2%-of-peak noise alone collapsed wm to 0.42
  and dw to 0.21. The best-ever loop min (dw 0.030) **exceeded** the
  smoothed-perfect dw ceiling - the optimization line (runs 10-27) was
  fitting noise.
- v1 build_calibration handed the model the submeter device_win trace
  inside its calibration windows - a direct FAQ Q1 violation ("there is a
  single signal... submeters exist only inside public datasets, and only
  for scoring").

## Protocol v2 (owner-approved; frozen)

- Eval span 90 days; cadence/thresholds/split unchanged (v1 frozen values).
- Events = cycles: ON mask at the frozen thresholds, gaps up to
  MERGE_S {60, 60, 12, 600, 600} s bridged, merged spans shorter than
  DWELL_S {30, 30, 30, 600, 600} s dropped (the pre-split per-class rules
  from data/gold_annot/ukdale/house_1/device_profile.csv).
- One-to-one greedy matching: predicted vs GT cycle onsets within
  TAU_ONSET_S {60, 60, 120, 600, 600} s, duration inside (1/3, 3.0)x the
  GT duration. Primary metric mean_device_f1 (higher better), guardrail
  min_device_f1; secondaries pooled cycle F1, MAE/nMAE, coverage.
- Calibration is aggregate-only (FAQ Q1): K=5 simulated button marks per
  device placed around whole PRE-span cycles (seeded), boundaries jittered
  +-30 s independently, 60 s pre/post roll (a real session records before
  switch-on). The model receives marks_us + aggregate slices; the fridge
  gets a passive 3 h aggregate window instead of marks. The PRE-span
  device channel is used only to place the marks (disclosed).
- Sanity gate (.auto/bench_v2.py --selftest and every run): the
  median-3-smoothed perfect predictor must score >= 0.9 per device or the
  benchmark declares itself invalid. Result over 90 d: kettle 0.981
  (366 cycles), microwave 0.952 (286), fridge 0.915 (2,805), wm 1.000
  (80), dw 1.000 (28) - **min 0.915**.

## Where it lives

- .auto/bench_v2.py (scoring + calibration v2 + sanity gate),
  .auto/measure.sh swapped to it; .auto/bench.py (v1) retired, kept for
  provenance. The swap and evidence are in log run 28 (.auto/log.jsonl,
  commit ca6a00f).
- First v2 reference model: rules v0 (log run 28): mean_device_f1 0.184,
  min 0.047 - every device detects real cycles, unlike v1 where the
  best-ever min sat above the noise ceiling.

## Implications for other hypotheses

- Runs 10-27 optimized an unlearnable metric: their per-run numbers are
  not comparable to anything under v2 (no cross-protocol comparisons).
- H04 ("program devices unreachable by threshold+duration rules") was
  measured against v1 GT episodes; the v2 cycle framing supersedes its
  evidence - do not cite its quarantined numbers.
- The min-metric hostage problem (10 dishwasher runs per 30 days) is
  handled at the metric level: mean is primary, min is the guardrail.
- Loop hygiene going forward: family cap ~3 runs per idea; ceiling check
  (smoothed-perfect battery) before declaring any device stuck.
