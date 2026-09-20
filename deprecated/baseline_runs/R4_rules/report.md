# R4: dwell-rule ablation + monitor negative control

| variant (det_min, gt_min) | fridge | dish_washer | kettle | washing_machine |
|---|---|---|---|---|
| (2,2) anchor | 0.43/0.64/0.51 | 0.02/0.30/0.03 | 0.45/0.98/0.62 | 0.04/0.18/0.06 |
| (1,2) no detector dwell | 0.31/0.64/0.42 | 0.01/0.30/0.02 | 0.44/0.98/0.61 | 0.03/0.20/0.06 |
| (2,1) loose GT | 0.43/0.53/0.48 | 0.02/0.24/0.03 | 0.45/0.90/0.60 | 0.04/0.10/0.06 |
| (1,1) no dwell rules | 0.32/0.54/0.40 | 0.01/0.24/0.02 | 0.44/0.90/0.59 | 0.04/0.12/0.06 |

## Confusability with no dwell rules (1,1)

| GT vs claimed | counts |
|---|---|
| fridge | dish_washer 1343, washing_machine 1138, kettle 121 |
| dish_washer | fridge 147, washing_machine 127, kettle 60 |
| kettle | fridge 176, dish_washer 176, washing_machine 175 |
| washing_machine | dish_washer 667, fridge 658, kettle 49 |

## Monitor negative control (plan 5.4)

Monitor channel run through the same pipeline as if it were an appliance:
signature 117 W on its own floor 113 W; the always-on stream produced 991 hysteresis episodes in the reference window vs 24 GT episodes.
A threshold detector cannot win the monitor (duty 80%) - by design it belongs to the always-on/UNKNOWN handling, and any detector logic that claims it is fit to noise.
