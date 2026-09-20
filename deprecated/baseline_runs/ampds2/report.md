# R1 baseline: AMPds2 single house 730 d (WHE + FGE/DWE/CWE)

Calibration 7.0 d / reference 723.0 d wall (723.00 d of sampled rows). Detector sees only the aggregate.
Always-on floor 370 W. Matching: greedy one-to-one, onset tol 120 s, dwell ratio 0.5-2.0, min dwell 2 samples.

Notes: 60 s rung: onset tol 120 s, min dwell 120 s | no kettle class in AMPds2; FRE = furnace fan, not used

| appliance | GT ep | det ep | P | R | F1 | onset err p50/p90 s | est/GT energy | GT kWh |
|---|---|---|---|---|---|---|---|---|
| fridge | 28047 | 7091 | 0.15 | 0.04 | 0.06 | 0.0 / 120.0 | 1.29 | 876.0 |
| dish_washer | 2003 | 11148 | 0.01 | 0.03 | 0.01 | 60.0 / 120.0 | 1.20 | 259.9 |
| washing_machine | 427 | 7099 | 0.00 | 0.01 | 0.00 | 120.0 / 120.0 | 1.03 | 75.6 |

Negative control: 4652/25338 detections false (18.4%), 196.49 kWh spurious.
Residual honesty: 12859.6 kWh above always-on; 99.9% covered; 13.5 kWh residual.

## Confusability (GT episodes overlapped by another signature)

| GT vs claimed | counts |
|---|---|
| fridge | washing_machine 27859, dish_washer 21487 |
| dish_washer | fridge 1995, washing_machine 1995 |
| washing_machine | fridge 427, dish_washer 426 |
