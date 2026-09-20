# R1 baseline: M0 @ 6 s, deployment-parity split

> **SUPERSEDED 2026-09-20** — calibration was idealized (signatures derived from clean submeter traces) and the per-class pass gates are retired [owner decision]. Kept unmodified as [quarantined] comparison points — upper-bound anchors cited by the hypothesis registry; the redo is the button-press calibration simulation (H02 spec), not a re-run of these runs. See docs/PROBLEM_STATEMENTS.md §6-§7 and docs/reports/quarantine-contradiction-review.md.

Calibration 7.0 d (signatures locked) / reference 61.58 d. Detector sees only the aggregate.
Always-on floor 147 W (locked from calibration daily p10). Matching: greedy one-to-one, onset tol 12 s, dwell ratio 0.5-2.0.

| appliance | GT ep | det ep | P | R | F1 | onset err p50/p90 s | est/GT energy | GT kWh |
|---|---|---|---|---|---|---|---|---|
| fridge | 1762 | 2632 | 0.43 | 0.64 | 0.51 | 0.0 / 0.0 | 0.99 | 59.2 |
| dish_washer | 179 | 3096 | 0.02 | 0.30 | 0.03 | 0.0 / 6.0 | 0.94 | 23.7 |
| kettle | 172 | 371 | 0.45 | 0.98 | 0.62 | 0.0 / 6.0 | 0.99 | 18.4 |
| washing_machine | 507 | 2478 | 0.04 | 0.18 | 0.06 | 0.0 / 12.0 | 0.96 | 16.5 |

Negative control: 1714/8577 detections are false positives (20.0%), 2.36 kWh spurious; monitor GT episodes: 24.

Residual honesty: 91.1 kWh above always-on; 96.8% covered by detections; 2.9 kWh residual.

## Confusability (GT episodes overlapped by another signature)

| GT vs claimed | counts |
|---|---|
| fridge | dish_washer 1268, washing_machine 1085, kettle 117 |
| dish_washer | fridge 135, washing_machine 119, kettle 58 |
| kettle | fridge 172, dish_washer 172, washing_machine 171 |
| washing_machine | dish_washer 437, fridge 428, kettle 42 |
