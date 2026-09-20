# R2: sampling-rate rungs (60 s / 300 s, mean + max buckets)

| substrate | rung | per-appliance |
|---|---|---|
| slice | 6 s raw (R1 anchor) | fridge F1 0.51 (P 0.43 R 0.64) | dish_washer F1 0.03 (P 0.02 R 0.30) | kettle F1 0.62 (P 0.45 R 0.98) | washing_machine F1 0.06 (P 0.04 R 0.18) |
| slice | 60 s mean | fridge F1 0.76 (P 0.82 R 0.71) | dish_washer F1 0.01 (P 0.00 R 0.16) | kettle F1 0.76 (P 0.64 R 0.94) | washing_machine F1 0.03 (P 0.01 R 0.45) |
| slice | 60 s max | fridge F1 0.70 (P 0.74 R 0.67) | dish_washer F1 0.01 (P 0.01 R 0.29) | kettle F1 0.78 (P 0.65 R 0.97) | washing_machine F1 0.04 (P 0.02 R 0.77) |
| slice | 300 s mean | fridge F1 0.71 (P 0.89 R 0.60) | dish_washer F1 0.03 (P 0.01 R 0.65) | kettle F1 0.38 (P 0.29 R 0.55) | washing_machine F1 0.05 (P 0.03 R 0.66) |
| slice | 300 s max | fridge F1 0.74 (P 0.89 R 0.64) | dish_washer F1 0.02 (P 0.01 R 0.54) | kettle F1 0.58 (P 0.41 R 0.97) | washing_machine F1 0.04 (P 0.02 R 0.47) |
| house1 full (real mains) | 60 s mean | fridge F1 0.39 | dish_washer F1 0.00 | washing_machine F1 0.02 | kettle F1 0.48 |
| house1 full (real mains) | 60 s max | fridge F1 0.40 | dish_washer F1 0.00 | washing_machine F1 0.04 | kettle F1 0.44 |
| AMPds2 (native 60 s) | 60 s max (native 60 s) | fridge F1 0.06 | dish_washer F1 0.01 | washing_machine F1 0.00 |
| AMPds2 (native 60 s) | 300 s mean | fridge F1 0.18 | dish_washer F1 0.01 | washing_machine F1 0.00 |

## 60 s pass gates (plan 5.6, slice substrate)

| appliance | verdict |
|---|---|
| kettle | P=0.64 vs 0.90 FAIL; R=0.94 vs 0.80 PASS |
| fridge | P=0.82 vs 0.70 PASS; R=0.71 vs 0.70 PASS |
| washing_machine | R=0.45 vs 0.60 FAIL |
| dish_washer | no gate (report only) |

## Survival reading (measured)

- On the SLICE, coarsening to 60 s HELPS the big classes: fridge 0.51 -> 0.76 and
  kettle 0.62 -> 0.76 - mean-bucketing smooths compressor micro-cycles and 6 s noise
  into single coherent episodes, and false alarms fall (fridge P 0.43 -> 0.82).
- On REAL mains (house1 full) the same 60 s rung is far worse: fridge 0.39,
  washing_machine 0.02, kettle 0.48. The custom-aggregate slice (sum of submeters,
  no residual) flatters the rung; the deployment-relevant 60 s verdict must come
  from real mains, and there only kettle recall holds (0.48 F1).
- At 300 s the kettle halves on the slice (0.76 -> 0.38 mean; max-bucket recovers
  0.58 by keeping the peaks); AMPds2 stays near-floor at both rungs. 300 s is the
  utility band where the episode framing stops applying.
- max-bucket vs mean at 60 s (slice): trades fridge precision (0.82 -> 0.74) for
  washing_machine recall (0.45 -> 0.77) - it preserves short heater steps AND noise
  spikes. It is the history-API worst case, not a free lunch.
- Gates (plan 5.6): fridge passes both P and R at 60 s; kettle passes R, fails P;
  washing_machine fails R - the 60 s default is an explicit risk item for the
  small-load classes, exactly as the plan anticipated.
