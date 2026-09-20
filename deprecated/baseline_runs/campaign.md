# Device campaign: enrollment universe, F2 disaggregation, weak-device sweep (E00-E19)

> **SUPERSEDED 2026-09-20** — calibration was idealized (signatures derived from clean submeter traces) and the per-class pass gates are retired [owner decision]. Kept unmodified as [quarantined] comparison points — upper-bound anchors cited by the hypothesis registry; the redo is the button-press calibration simulation (H02 spec), not a re-run of these runs. See docs/PROBLEM_STATEMENTS.md §6-§7 and docs/reports/quarantine-contradiction-review.md.

Protocol unchanged (plan 3.0): calibration = first 7.0 d of the common span;
detector sees only the aggregate minus the always-on floor; submeters are GT only.
Code: `analysis/device_campaign.py`. Every number below is read from
`baseline_runs/experiments/*/metrics.json` or `baseline_runs/enrollment/*.md`.

Device universe: 126 labeled channels over 7 substrates - slice 4, house1 50,
house2 18, house3 4, house4 5 (composites), house5 23, AMPds2 22.

## 1. Enrollment across the whole device range

| substrate | devices | enrolled (house cal) | fallback (own 7 d) | not enrollable |
|---|---|---|---|---|
| slice | 4 | 4 | 0 | 0 |
| house1 | 50 | 17 | 10 | 23 |
| house2 | 18 | 16 | 0 | 2 |
| house3 | 4 | 4 | 0 | 0 |
| house4 | 5 | 5 | 0 | 0 |
| house5 | 23 | 21 | 0 | 2 |
| ampds2 | 22 | 20 | 0 | 2 |
| **total** | **126** | **87 (69%)** | **10 (8%)** | **29 (23%)** |

- 69% of the universe enrolls from the house-calibration window alone; another
  8% enrolls from the device's own first dense 7 d (all in house1: lamps, chargers,
  office gear - channels that are dead during the house-cal window).
  Not enrollable (23%): channels with no 7-d dense window anywhere (e.g.
  house1 `data_logger_pc`, `soldering_iron`), or pure-standby composites (house4).
- Enrollment quality where it works stays high: matched-energy ratio stays 0.99
  (slice, R1); kettle signatures transfer across all five houses with recall
  0.46-0.98. Full tables: `enrollment/slice.md` ... `enrollment/ampds2.md`.

## 2. Weak-device sweep (E00-E19, plan 3.2-3.4 knobs)

Weak class = mean F1 over dish/washer-family channels with GT episodes
(kettle and fridge guarded separately). E00 = R1 M0 config (anchor).

| exp | what changes | weak F1 (best substrate vs E00) | notable per-device wins |
|---|---|---|---|
| E01 gap merge 12 s | episode-level 12 s merge | slice 0.021 (0.048) worse | house2 kettle 0.53 (+0.04) |
| E02 activity windows 600 s | multi-state programs = 1 episode | slice 0.007 worse | slice fridge 0.66 (+0.14), all-F1 0.36 (+0.05) |
| E03/E04 sig p25/p90 | signature statistic | no weak gain anywhere | house2 kettle 0.49 (p90, flat) |
| E05 entry 0.25x | lower entry threshold | house2 0.009 (+0.0) | kettle worse everywhere |
| E06 dwell prior | reject det outside dwell [p10,p90]x[0.5,2] | **slice 0.060 (+0.012), house2 0.027 (+0.009), house1 0.043 (+0.006)** | **kettle +0.15 slice (0.77), +0.12 house2, +0.11 house1** |
| E07/E08 rolling baseline | 5/30-min median subtraction | slice weak worse (0.026/0.022) | fridge collapses on slice (0.003) |
| E09 rel. threshold | 2nd pass sub-floor | house5 0.009 (+0.005) | helps small loads marginally |
| E10/E11 hysteresis width | 0.40/0.60 entry | ampds2 0.024 (+0.007) | kettle +0.04-0.04 flat |
| E12 min dwell 3 | shorter episodes | no weak gain | slice fridge 0.57 (+0.06) |
| E13 stack (p25+dwell+gm12) | best knobs combined | house1 weak 0.007 (-0.03) | **kettle 0.83 slice, 0.67 house2, 0.46 house1; house1 fridge 0.004->0.262** |

Verdict on weak devices (dishwasher / washing machine): **no detection variant
unlocks them on real aggregate mains.** Two failure modes, both unfixable by the
knobs tested: where the detector over-fires (slice dish_washer 3096 det vs 179 GT,
AMPds2 CWE 16.6x) the entry threshold sits in the noise floor; where GT is
fragmented into micro-episodes (house1 washing_machine 79511 GT episodes vs 38000
det, F1 0.075) onset matching cannot pair them. The dwell prior (E06) is the only
knob that improves the weak class on every substrate, and only slightly.
AMPds2 (60 s native) collapses under every variant: all-F1 <= 0.02 - 60 s dt
destroys episode timing.

## 3. F2 disaggregation (event-then-classify, E14-E19)

One generic detector on the aggregate; each event classified to the nearest
signature in (level, log-dwell); rejections: ambiguity margin, plausibility
(signature >= 60% of event level), dwell prior. Library gate: signature must
exist in calibration AND sit above the always-on floor.

| metric | slice | house2 | house5 | ampds2 | house1 |
|---|---|---|---|---|---|
| events (E19) | 2058 | 1744 | 2401 | 11538 | 28090 |
| rejected by margin/plaus (E19) | 54% | 41% | 75% | 25% | 71% |
| event accuracy (E14 -> E19) | 0.18 -> **0.38** | 0.09 -> 0.08 | 0.09 -> **0.22** | 0.05 -> 0.02 | - -> **0.29** |
| kettle F1: F2 best vs detection | 0.74 vs 0.62 | 0.11 vs 0.49 | 0.30 vs 0.08 | - | 0.11 vs 0.22 |

- E19 (margin + plausibility + dwell prior) is the best F2 config everywhere.
- F2 beats per-device detection exactly where the signature is strong and rare:
  kettle attribution on the slice has P=0.84 at R=0.66; house5 kettle F1 0.30 vs
  0.08 detection. Confusion concentrates on same-level siblings (house5:
  electric_hob <- kettle 57; ampds2: dryer DWE <- CDE 174).
- The library gate **excludes the weak devices themselves**: house5 dish_washer
  (97 W signature) sits below the 535 W always-on floor, so F2 cannot attribute
  it at all; on ampds2 only 3 of 22 channels survive the gate. Weak devices are
  therefore unreachable by F2 as specified - they are below the floor, not above it.
- Attribution quality on 60 s real mains (house2) is 0.08 - disaggregation needs
  the 6 s sample rate the slice provides.

## 4. Campaign verdict

1. **Enrollment generalizes**: 69% of 126 devices enroll from a 7 d house window, +8%
   recoverable per-device; the 23% never enrollable are sparse/standby channels that
   need a longer calibration or plug-level sampling, not better signatures.
2. **Detection cannot rescue dishwasher/washing-machine class** - 14 variants,
   0 material weak-class gains; det/GT ratio 10-30x shows the failure is noise
   masking, not threshold placement. The dwell prior (E06) is the only universal
   improvement and the right production default.
3. **Disaggregation works only above the floor**: F2 attributes kettle-class events
   with precision 0.84-0.91, but the same gate that makes it precise makes weak
   devices unattributable. Weak-device disaggregation needs their contribution
   separated from the always-on floor (higher-rate sampling), not a bigger threshold search.

Artifacts: `experiments/E00_anchor` ... `E19_f2_stack` (report.md + metrics.json each),
`experiments/leaderboard.md`, `enrollment/{slice,house1..5,ampds2}.md`, `enrollment/enrollment.md`.

