# Baseline campaign summary (plan section 6, all runs conducted)

> **SUPERSEDED 2026-09-20** — calibration was idealized (signatures derived from clean submeter traces) and the per-class pass gates are retired [owner decision]. Kept unmodified as [quarantined] comparison points — upper-bound anchors cited by the hypothesis registry; the redo is the button-press calibration simulation (H02 spec), not a re-run of these runs. See docs/PROBLEM_STATEMENTS.md §6-§7 and docs/reports/quarantine-contradiction-review.md.

Protocol (plan 3.0, fixed before any run): calibration = first 7.0 d wall-clock of each
substrate (signatures locked there); reference = the remainder. The detector (M0:
threshold + hysteresis + dwell, single-channel) sees ONLY the aggregate; submeters are
ground truth for scoring only. Matching per plan 5.2; metrics per plan 5.3.

Scripts: `analysis/baseline_ukdale.py` (substrate loader + R1 protocol),
`analysis/plan_runs.py` (R2-R6). Artifacts: one `report.md` + `metrics.json` per run
directory below. All numbers below are from those artifacts.

## R1 - baseline table (the anchor)

| substrate | kettle F1 | fridge F1 | washing_machine F1 | dish_washer F1 | FP rate | residual |
|---|---|---|---|---|---|---|
| slice 70.7 d (custom agg) | 0.62 (P .45 R .98) | 0.51 | 0.06 | 0.03 | 20.0% | 2.9 kWh |
| house1 full 1629 d (real mains) | 0.22 (P .15 R .46) | 0.00* | 0.07 | 0.00 | 16.9% | 62.8 kWh |
| house2 full 236 d | 0.49 (P .35 R .82) | 0.00 | 0.04 | 0.00 | 0.0%* | 0.2 kWh |
| house3 full 40 d (kettle only) | 0.09 (P .05 R .64) | - | - | - | 93.7%* | 99.1 kWh |
| house4 full 206 d (composites) | 0.08 | 0.37 | 0.06 | - | 29.2% | 6.0 kWh |
| house5 full 137 d (composites) | 0.08 | 0.02 | 0.01 | 0.00 | 8.7% | 0.5 kWh |
| AMPds2 730 d (60 s native) | n/a (no kettle) | 0.06 | 0.00 | 0.01 | 18.4% | 13.5 kWh |

* house1 fridge: GT fragments into 543,982 episodes (noisy ch12 ON-mask) - episode recall
is structurally unreachable for any detector against that GT. house2/3 "FP" rates are
underestimates of detector error in the other direction: house2/3 have large UNLABELED
loads, so detections there count as "not false" while matching nothing known. house3's
93.7% FP is the honest reading: an aggregate full of unlabeled appliances. Est/GT energy
on matched pairs is ~0.4-1.3 across the board - the M0 rectangle is roughly energy-honest
where it matches.

Headline: the kettle transfers across all 5 houses + the slice; everything below ~200 W
standby (dish_washer/washing_machine signatures at 97-123 W on slice/houses 1-2) does not
separate from the always-on floor with a fixed threshold. Residual coverage 96.8-100%
(slice + houses 1,2,4,5) - the always-on + UNKNOWN design carries the energy accounting.

## R2 - sampling-rate rungs (60 s / 300 s, mean + max buckets)

Full table: `R2_rungs/report.md`. The measured story reverses the naive expectation:

- On the SLICE, 60 s HELPS the big classes (fridge 0.51 -> 0.76, kettle 0.62 -> 0.76):
  bucketing absorbs 6 s noise and compressor micro-cycles.
- On REAL mains (house1), 60 s is where M0 degrades hard: fridge 0.39, kettle 0.48,
  dish_washer 0.00. The custom-aggregate slice flatters the rung - the deployment 60 s
  verdict must come from real mains.
- At 300 s the kettle halves (0.38 mean / 0.58 max); AMPds2 stays near-floor.
- 60 s gates (plan 5.6): fridge PASS (P .82/R .71), kettle R PASS / P FAIL (.64 vs .90),
  washing_machine R FAIL (.45 vs .60) - the client's 60 s default is an explicit risk
  item for small-load classes, exactly as the plan anticipated.

## R3 - calibration learning curve (the deliverable metric)

Full table: `R3_learning_curve/report.md`.

- The curve is FLAT from N=1 for single-state loads (fridge 0.50 at N=1 vs 0.51 at all;
  kettle 0.62 throughout): one episode lands the threshold in the right band.
- washing_machine is NON-monotonic: N=1 locks a standby signature (54 W), N=2 a heater
  signature that overfires, N>=10 stabilizes. What matters is covering the appliance's
  MODES, not collecting more episodes of one mode.
- Session-length answer: minutes, not days - 10-20 episodes (~2 min kettle, tens of
  minutes cyclic loads) is the ceiling; the knee is at or below it.
- 500 W-floor variant: only the kettle clears 500 W on this substrate - a big-load-only
  product is kettle-only, and its curve is flat from N=1 (F1 0.62).

## R4 - which rules carry the accuracy + negative control

Full table: `R4_rules/report.md`. Variants are (detector min dwell, GT min dwell):

- Removing the detector dwell filter (2,2)->(1,2) costs fridge F1 0.51 -> 0.42
  (precision .43 -> .31): the dwell rule IS the fridge precision carrier.
- Loosening GT to 1 sample (2,1) fragments GT and drops recall everywhere
  (kettle .98 -> .90, fridge .64 -> .53) - the 2-sample GT floor is load-bearing for
  honest recall numbers.
- Monitor negative control (plan 5.4): the monitor channel run through the same pipeline
  produces 991 hysteresis episodes in 63.7 d (signature 117 W on an 80% duty always-on
  stream) - a threshold detector WILL claim the always-on load with noise episodes; it
  must be rejected and handled by the always-on/UNKNOWN design, never as an appliance.

## R5 - measurement-error robustness (stretch)

Full table: `R5_noise/report.md`. 5% multiplicative noise + 30 VA measurement floor on
top of 60 s: F1 moves by hundredths (noise) to hundredths-positive (VA floor deletes
standby episodes, slightly helping precision, hurting small-load recall). The cliff is
sampling rate, not measurement error - threshold + hysteresis absorbs +-5% by design.

## R6 - anomaly-loop rehearsal (the demoable-now mechanics)

Full table: `R6_anomaly/report.md`. On the R1 residual (aggregate - always-on -
attributed), 8 synthetic shapes, generic 1000 W threshold, onset-based detection:

- 7/8 detected with 0 s latency (2 kW step, 3 kW spike, 800 W stuck load, 1.2 kW
  cycling, 1.5 kW and 2.5 kW unusual events, 900 W event).
- The 400 W x 2 h injection never crosses the generic threshold - small-but-long loads
  need their own signature (the same lesson as the small classes at 60 s).
- Background: 7 detections / 3.27 kWh on the clean residual - the UNKNOWN stream the
  product loop consumes, measured.

## Device campaign (all labeled channels, E00-E19, F2 disaggregation)

Full verdict: `campaign.md`. Universe: 126 labeled channels over 7 substrates;
framework `analysis/device_campaign.py`; per-experiment dirs `experiments/E00_anchor`
... `experiments/E19_f2_stack`, `experiments/leaderboard.md`, `enrollment/enrollment.md`.
- Enrollment: 87/126 devices (69%) enroll from the 7 d house-calibration window,
  +10 recoverable from the device's own first dense 7 d, 29 (23%) never enrollable.
- Weak class (dish/wash): none of the 14 detection variants materially improves it
  (best: E06 dwell prior, +0.006-0.012 weak F1); two failure modes (noise-floor
  over-firing 5-17x, and fragmented GT) bracket every substrate.
- E06 dwell prior is the production default (kettle +0.11-0.15 on 3 houses).
- F2 event-then-classify (E19 best): kettle attribution P 0.84-0.91, event accuracy
  0.38 (6 s slice) / 0.08 (60 s real mains); its library gate excludes sub-floor
  devices, so weak devices remain unreachable without higher-rate sampling.

## Honesty notes (plan 7)

- The slice's aggregate is custom (sum of submeters, no residual): it flatters every
  rung; the real-mains houses are the deployment-relevant R1/R2 rows.
- house4/house5 archetype channels are composites (freezer, washer_dryer,
  kettle_radio, washing_machine_microwave_breadmaker) - their GT is not a pure
  appliance.
- Calibration windows start where ALL channels are dense (house1 +34 d, house2 +3 mo
  rollout) - noted per report; zero-signature appliances would silently produce no
  detections otherwise.
- house2/3 FP rates are not comparable to the slice: unlabeled loads make
  "overlaps-no-known-GT" mean something different.
- Never point-wise accuracy; never tuned on the reference; no random windows.
