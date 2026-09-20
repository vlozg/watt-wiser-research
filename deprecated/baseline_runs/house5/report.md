# R1 baseline: UK-DALE FULL house5 (real mains, 6 s)

Calibration 7.0 d / reference 123.3 d wall (109.64 d of sampled rows). Detector sees only the aggregate.
Always-on floor 533 W. Matching: greedy one-to-one, onset tol 12 s, dwell ratio 0.5-2.0, min dwell 2 samples.

Notes: channel_1 = real aggregate mains | calibration starts 2014-07-06 10:40:17: first 7-d window where aggregate + all archetype channels are dense (house rollout artifact) | house label for fridge is composite: fridge_freezer | house label for dish_washer is composite: dishwasher | house label for washing_machine is composite: washer_dryer

| appliance | GT ep | det ep | P | R | F1 | onset err p50/p90 s | est/GT energy | GT kWh |
|---|---|---|---|---|---|---|---|---|
| fridge | 9725 | 5175 | 0.04 | 0.02 | 0.02 | 0.0 / 6.0 | 1.02 | 100.2 |
| dish_washer | 762 | 5551 | 0.00 | 0.01 | 0.00 | 6.0 / 6.0 | 0.93 | 44.4 |
| washing_machine | 9733 | 11847 | 0.01 | 0.01 | 0.01 | 6.0 / 12.0 | 0.88 | 105.3 |
| kettle | 155 | 2607 | 0.04 | 0.74 | 0.08 | 0.0 / 6.0 | 0.99 | 15.7 |

Negative control: 2189/25180 detections false (8.7%), 4.88 kWh spurious.
Residual honesty: 514.1 kWh above always-on; 99.9% covered; 0.5 kWh residual.

## Confusability (GT episodes overlapped by another signature)

| GT vs claimed | counts |
|---|---|
| fridge | washing_machine 6589, dish_washer 5963, kettle 1591 |
| dish_washer | washing_machine 745, fridge 730, kettle 476 |
| washing_machine | dish_washer 6443, fridge 6337, kettle 2038 |
| kettle | washing_machine 155, fridge 154, dish_washer 154 |
