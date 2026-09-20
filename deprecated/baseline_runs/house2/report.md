# R1 baseline: UK-DALE FULL house2 (real mains, 6 s)

Calibration 7.0 d / reference 128.8 d wall (103.26 d of sampled rows). Detector sees only the aggregate.
Always-on floor 122 W. Matching: greedy one-to-one, onset tol 12 s, dwell ratio 0.5-2.0, min dwell 2 samples.

Notes: channel_1 = real aggregate mains | calibration starts 2013-05-27 09:25:33: first 7-d window where aggregate + all archetype channels are dense (house rollout artifact)

| appliance | GT ep | det ep | P | R | F1 | onset err p50/p90 s | est/GT energy | GT kWh |
|---|---|---|---|---|---|---|---|---|
| fridge | 123 | 3848 | 0.00 | 0.00 | 0.00 | None / None | 0.00 | 115.4 |
| dish_washer | 264 | 1518 | 0.00 | 0.00 | 0.00 | None / None | 0.00 | 104.8 |
| washing_machine | 843 | 2003 | 0.03 | 0.06 | 0.04 | 6.0 / 12.0 | 0.75 | 28.3 |
| kettle | 535 | 1263 | 0.35 | 0.82 | 0.49 | 0.0 / 0.0 | 0.98 | 63.3 |

Negative control: 0/8632 detections false (0.0%), 0.00 kWh spurious.
Residual honesty: 456.4 kWh above always-on; 100.0% covered; 0.2 kWh residual.

## Confusability (GT episodes overlapped by another signature)

| GT vs claimed | counts |
|---|---|
| fridge | washing_machine 104, dish_washer 40, kettle 39 |
| dish_washer | fridge 264, washing_machine 253, kettle 145 |
| washing_machine | fridge 843, dish_washer 162, kettle 149 |
| kettle | fridge 535, washing_machine 535, dish_washer 532 |
