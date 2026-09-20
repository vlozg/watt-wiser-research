# R1 baseline: UK-DALE FULL house3 (real mains, 6 s)

Calibration 7.0 d / reference 25.7 d wall (22.55 d of sampled rows). Detector sees only the aggregate.
Always-on floor 109 W. Matching: greedy one-to-one, onset tol 12 s, dwell ratio 0.5-2.0, min dwell 2 samples.

Notes: channel_1 = real aggregate mains | calibration starts 2013-03-06 11:45:29: first 7-d window where aggregate + all archetype channels are dense (house rollout artifact)

| appliance | GT ep | det ep | P | R | F1 | onset err p50/p90 s | est/GT energy | GT kWh |
|---|---|---|---|---|---|---|---|---|
| kettle | 53 | 735 | 0.05 | 0.64 | 0.09 | 0.0 / 6.0 | 0.97 | 3.4 |

Negative control: 689/735 detections false (93.7%), 183.09 kWh spurious.
Residual honesty: 249.4 kWh above always-on; 60.3% covered; 99.1 kWh residual.

## Confusability (GT episodes overlapped by another signature)

| GT vs claimed | counts |
|---|---|
