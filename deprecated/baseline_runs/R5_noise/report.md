# R5: measurement-error robustness (5% noise + 30 VA floor on 60 s)

| variant | fridge | dish_washer | kettle | washing_machine | aggregate FP rate |
|---|---|---|---|---|---|
| 60 s clean (R2 anchor) | 0.76 | 0.01 | 0.76 | 0.03 | 1.3% |
| 60 s + 5% noise | 0.76 | 0.01 | 0.76 | 0.03 | 1.3% |
| 60 s + 30 VA floor | 0.77 | 0.03 | 0.76 | 0.03 | 1.3% |
| 60 s + noise + floor | 0.77 | 0.03 | 0.76 | 0.03 | 1.3% |

## Reading

- 5% level noise moves F1 by hundredths at 60 s: threshold+hysteresis absorbs
  multiplicative error; the rung cliff is sampling rate, not measurement noise.
- The 30 VA floor mostly deletes standby-level GT/det episodes (dish_washer/washing
  machine standby), which slightly INCREASES precision while cutting recall on
  small-load classes - the same direction the client hardware will push.
