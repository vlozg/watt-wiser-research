# WattWiser NILM baseline - terminal-state dossier (autoresearch segment 1)

Status: TERMINAL under the named primary (mean_device_f1). No testable
hypothesis remains under the anti-overfit discipline; every lever has
been measured or priced. This document consolidates the logged evidence
for the owner's three decisions. All decomposition numbers are
pre-span, analysis-only; the evaluation span was touched only through
the official benchmark.

## 1. Score (unchanged since run 40)

| metric | value |
|---|---|
| mean_device_f1 | 0.5896539900882762 |
| pooled_cycle_f1 | 0.539318 |
| min_device_f1 (microwave) | 0.361702 |
| mean_mae_w | 23.5071 |
| worst_mae_w (washing_machine) | 54.0205 |
| mean_nmae | 0.067679 |
| coverage (pred / true share) | 0.256488 / 0.252640 |

Per device (F1 / MAE W): kettle 0.7793 / 10.26; microwave 0.3617 /
7.02; fridge 0.5187 / 28.46; washing_machine 0.6220 / 54.02;
dishwasher 0.6667 / 17.77.

## 2. Terminal-state proof

Seven consecutive holding evaluations (runs 52-58) print identical
METRIC lines; the only inter-run difference in the raw logs is the
wall-clock timing line. The frozen calibration draw (CALIB_SEED=2026)
and the deterministic machinery make the score exactly reproducible.
The three non-identical logs in the window are deliberately-varied
declined-variant evaluations, each worse than baseline: run 41
0.586553, run 50 0.587077, run 51 0.589314 (the heater-filtered
subset). Reproduce with: bash .auto/measure.sh (run logs in
.auto/runs/<n>.log).

## 3. Calibration-noise envelope (runs 53-54)

The score is ONE draw from a wide, benchmark-unquantified calibration
distribution. Across 26 protocol-legal calibration resamples: microwave
band admission 734-1238 events (frozen draw: 750); chain thresholds
+-20%; the frozen draw sits at the distribution EDGE (mw mark duration
at the minimum, kettle/wm amp at the maximum). Attribution: cycle
SELECTION dominates (selection-only resampling reproduces 607-1111 of
the 734-1238 spread); press jitter is secondary (+6-8% admission within
a fixed selection, with one pathological zero-jitter interaction).
Scaling: admission spread 50.3% -> 45.6% -> 31.8% at k_calib 5/10/20 -
quadrupling the marks halves the wobble; a tighter press protocol
removes only the secondary term; zero jitter is not safer.

## 4. Recall-gap decomposition (runs 55-56)

Visibility funnel (pre-span GT cycles vs aggregate events; L1_any =
cycle overlapped by any extracted event; capture = eval recall /
in-band material):

| device | n_cyc | L1_any | material | eval recall | capture |
|---|---|---|---|---|---|
| kettle | 1160 | 0.909 | 0.572 | 0.699 | 1.224* |
| microwave | 899 | 0.904 | 0.310 | 0.297 | 0.958 |
| fridge | 7774 | 0.821 | 0.779 | 0.416 | 0.534 |
| washing_machine | 208 | 0.966 | 0.817 | 0.638 | 0.780 |
| dishwasher | 94 | 0.968 | 0.500 | 0.500 | 1.000 |

*cross-span caveat. Program-device replication validated exactly
against recorded anchors (dw runs 49; wm net-new 82; named chains 139).

Unified conclusion: the aggregate input is never binding (L1_any
0.82-0.97 everywhere). The losses live in (a) the frozen admission
bands (microwave capture 0.958 - the pipeline extracts everything its
band allows), (b) the detector shape gates (dishwasher is pure
yield-limited: capture 1.000), and (c) the emission/dedup machinery
(fridge 0.534, wm 0.780). Every lever touching (a), (b) or (c) is an
admission spend priced dead at the 18.1-41.2% F1 breakevens against
the measured 16.7% contamination conversion.

## 5. Declined levers (integrity record)

- Admission-pool spends: dead at the breakevens above.
- Heater-filtered subsets: post-hoc re-litigation; run 51 measured
  0.589314 (worse) and was declined.
- Resampled-seed eval-span evaluations: off-protocol; keeping a
  favorable calibration draw would be manipulation.
- Draw-robustness variants: unquantified expected value.
- Metric-package rebuild (menu item 3): F1-bitwise-identical on an
  identical baseline - unkeepable under the named metric (runs 44-45).

## 6. Owner decisions (evidence pointers)

1. Primary redefinition - regression package in runs 44-45: every
   alternate metric definition is bitwise-identical on this baseline.
2. E3-scale rebuild - headroom map in section 4: recall headroom
   exists in gates/emission but is F1-dead under the current primary.
3. New data / collection constraints - the contamination economics
   above; the k_calib=20 prescription (section 3) if the button-press
   protocol can be relaxed.
