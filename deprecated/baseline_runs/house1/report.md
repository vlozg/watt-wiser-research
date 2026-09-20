# R1 baseline: UK-DALE FULL house1 (real mains, 6 s)

Calibration 7.0 d / reference 1572.2 d wall (1482.36 d of sampled rows). Detector sees only the aggregate.
Always-on floor 169 W. Matching: greedy one-to-one, onset tol 12 s, dwell ratio 0.5-2.0, min dwell 2 samples.

Notes: channel_1 = real aggregate mains | calibration starts 2012-12-29 12:08:04: first 7-d window where aggregate + all archetype channels are dense (house rollout artifact) | house label for dish_washer is composite: dishwasher

| appliance | GT ep | det ep | P | R | F1 | onset err p50/p90 s | est/GT energy | GT kWh |
|---|---|---|---|---|---|---|---|---|
| fridge | 543982 | 36379 | 0.03 | 0.00 | 0.00 | 0.0 / 6.0 | 1.03 | 1341.4 |
| dish_washer | 31811 | 34942 | 0.00 | 0.00 | 0.00 | 6.0 / 7.8 | 4.69 | 833.5 |
| washing_machine | 79511 | 36521 | 0.11 | 0.05 | 0.07 | 6.0 / 12.0 | 1.17 | 842.1 |
| kettle | 10697 | 33578 | 0.15 | 0.46 | 0.22 | 0.0 / 6.0 | 0.99 | 434.2 |

Negative control: 23909/141420 detections false (16.9%), 306.93 kWh spurious.
Residual honesty: 7464.1 kWh above always-on; 99.2% covered; 62.8 kWh residual.

## Confusability (GT episodes overlapped by another signature)

| GT vs claimed | counts |
|---|---|
| fridge | dish_washer 494632, washing_machine 383100, kettle 27416 |
| dish_washer | fridge 31420, washing_machine 30866, kettle 12162 |
| washing_machine | fridge 77795, dish_washer 77424, kettle 17442 |
| kettle | fridge 10683, dish_washer 10681, washing_machine 10665 |
