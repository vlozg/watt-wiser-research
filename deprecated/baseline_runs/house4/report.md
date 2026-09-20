# R1 baseline: UK-DALE FULL house4 (real mains, 6 s)

Calibration 7.0 d / reference 191.9 d wall (138.46 d of sampled rows). Detector sees only the aggregate.
Always-on floor 154 W. Matching: greedy one-to-one, onset tol 12 s, dwell ratio 0.5-2.0, min dwell 2 samples.

Notes: channel_1 = real aggregate mains | calibration starts 2013-03-16 08:42:18: first 7-d window where aggregate + all archetype channels are dense (house rollout artifact) | house label for fridge is composite: freezer | house label for washing_machine is composite: washing_machine_microwave_breadmaker | house label for kettle is composite: kettle_radio

| appliance | GT ep | det ep | P | R | F1 | onset err p50/p90 s | est/GT energy | GT kWh |
|---|---|---|---|---|---|---|---|---|
| fridge | 4522 | 3665 | 0.41 | 0.34 | 0.37 | 0.0 / 6.0 | 1.02 | 116.6 |
| washing_machine | 3599 | 4349 | 0.06 | 0.07 | 0.06 | 0.0 / 12.0 | 0.39 | 55.0 |
| kettle | 707 | 7830 | 0.04 | 0.50 | 0.08 | 0.0 / 6.0 | 0.39 | 52.8 |

Negative control: 4630/15844 detections false (29.2%), 36.55 kWh spurious.
Residual honesty: 872.0 kWh above always-on; 99.3% covered; 6.0 kWh residual.

## Confusability (GT episodes overlapped by another signature)

| GT vs claimed | counts |
|---|---|
| fridge | washing_machine 4067, kettle 1720 |
| washing_machine | fridge 3361, kettle 2542 |
| kettle | fridge 706, washing_machine 706 |
