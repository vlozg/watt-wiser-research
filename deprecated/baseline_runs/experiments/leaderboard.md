# Experiment leaderboard

weak = mean F1 over dish/washer-class devices with GT episodes; guards: kettle, fridge.

| exp | substrate | weak F1 | all F1 | kettle | fridge | hypothesis |
|---|---|---|---|---|---|---|
| E00 | ampds2 | 0.017 | 0.007 | - | 0.06 | R1 M0 config (delta baseline) |
| E00 | house1 | 0.037 | 0.012 | 0.223 | 0.004 | R1 M0 config (delta baseline) |
| E00 | house2 | 0.018 | 0.044 | 0.488 | 0.0 | R1 M0 config (delta baseline) |
| E00 | house5 | 0.004 | 0.02 | 0.083 | 0.025 | R1 M0 config (delta baseline) |
| E00 | slice | 0.048 | 0.307 | 0.619 | 0.514 | R1 M0 config (delta baseline) |
| E01 | ampds2 | 0.017 | 0.007 | - | 0.06 | plan 3.2 gap merge 12 s on episodes (det + GT) |
| E01 | house2 | 0.007 | 0.046 | 0.527 | 0.0 | plan 3.2 gap merge 12 s on episodes (det + GT) |
| E01 | house5 | 0.002 | 0.017 | 0.094 | 0.063 | plan 3.2 gap merge 12 s on episodes (det + GT) |
| E01 | slice | 0.021 | 0.312 | 0.644 | 0.562 | plan 3.2 gap merge 12 s on episodes (det + GT) |
| E02 | ampds2 | 0.026 | 0.006 | - | 0.01 | gap merge 600 s: multi-state programs become one window |
| E02 | house1 | 0.001 | 0.024 | 0.33 | 0.398 | gap merge 600 s: multi-state programs become one window |
| E02 | house2 | 0.005 | 0.052 | 0.574 | 0.0 | gap merge 600 s: multi-state programs become one window |
| E02 | house5 | 0.001 | 0.025 | 0.213 | 0.123 | gap merge 600 s: multi-state programs become one window |
| E02 | slice | 0.007 | 0.359 | 0.767 | 0.657 | gap merge 600 s: multi-state programs become one window |
| E03 | ampds2 | 0.001 | 0.004 | - | 0.06 | signature from ON p25 instead of median |
| E03 | house2 | 0.006 | 0.041 | 0.484 | 0.0 | signature from ON p25 instead of median |
| E03 | house5 | 0.004 | 0.018 | 0.083 | 0.025 | signature from ON p25 instead of median |
| E03 | slice | 0.042 | 0.302 | 0.619 | 0.505 | signature from ON p25 instead of median |
| E04 | ampds2 | 0.018 | 0.008 | - | 0.071 | signature from ON p90 (upper level) |
| E04 | house2 | 0.004 | 0.043 | 0.493 | 0.0 | signature from ON p90 (upper level) |
| E04 | house5 | 0.004 | 0.019 | 0.085 | 0.025 | signature from ON p90 (upper level) |
| E04 | slice | 0.004 | 0.287 | 0.619 | 0.523 | signature from ON p90 (upper level) |
| E05 | ampds2 | 0.01 | 0.005 | - | 0.033 | enter at 0.25x signature (lower entry) |
| E05 | house2 | 0.009 | 0.027 | 0.33 | 0.0 | enter at 0.25x signature (lower entry) |
| E05 | house5 | 0.005 | 0.015 | 0.069 | 0.023 | enter at 0.25x signature (lower entry) |
| E05 | slice | 0.041 | 0.264 | 0.601 | 0.373 | enter at 0.25x signature (lower entry) |
| E06 | ampds2 | 0.017 | 0.007 | - | 0.062 | reject detections outside signature dwell [p10,p90] x [0.5,2] |
| E06 | house1 | 0.043 | 0.017 | 0.336 | 0.004 | reject detections outside signature dwell [p10,p90] x [0.5,2] |
| E06 | house2 | 0.027 | 0.056 | 0.61 | 0.0 | reject detections outside signature dwell [p10,p90] x [0.5,2] |
| E06 | house5 | 0.004 | 0.023 | 0.108 | 0.026 | reject detections outside signature dwell [p10,p90] x [0.5,2] |
| E06 | slice | 0.06 | 0.352 | 0.773 | 0.512 | reject detections outside signature dwell [p10,p90] x [0.5,2] |
| E07 | ampds2 | 0.003 | 0.012 | - | 0.008 | subtract 5-min rolling median before thresholding |
| E07 | house2 | 0.021 | 0.043 | 0.4 | 0.0 | subtract 5-min rolling median before thresholding |
| E07 | house5 | 0.009 | 0.023 | 0.115 | 0.018 | subtract 5-min rolling median before thresholding |
| E07 | slice | 0.026 | 0.206 | 0.768 | 0.003 | subtract 5-min rolling median before thresholding |
| E08 | ampds2 | 0.013 | 0.018 | - | 0.155 | 30-min rolling baseline |
| E08 | house2 | 0.019 | 0.054 | 0.609 | 0.0 | 30-min rolling baseline |
| E08 | house5 | 0.006 | 0.026 | 0.104 | 0.024 | 30-min rolling baseline |
| E08 | slice | 0.022 | 0.18 | 0.655 | 0.018 | 30-min rolling baseline |
| E09 | ampds2 | 0.017 | 0.015 | - | 0.008 | relative-threshold 2nd pass for sub-floor signatures |
| E09 | house2 | 0.018 | 0.042 | 0.488 | 0.0 | relative-threshold 2nd pass for sub-floor signatures |
| E09 | house5 | 0.009 | 0.022 | 0.083 | 0.018 | relative-threshold 2nd pass for sub-floor signatures |
| E09 | slice | 0.043 | 0.177 | 0.619 | 0.003 | relative-threshold 2nd pass for sub-floor signatures |
| E10 | ampds2 | 0.013 | 0.006 | - | 0.049 | wider hysteresis (enter .40, exit .20) |
| E10 | house2 | 0.013 | 0.037 | 0.44 | 0.0 | wider hysteresis (enter .40, exit .20) |
| E10 | house5 | 0.004 | 0.018 | 0.075 | 0.024 | wider hysteresis (enter .40, exit .20) |
| E10 | slice | 0.053 | 0.292 | 0.62 | 0.44 | wider hysteresis (enter .40, exit .20) |
| E11 | ampds2 | 0.024 | 0.009 | - | 0.079 | narrower hysteresis (enter .60, exit .30) |
| E11 | house2 | 0.021 | 0.05 | 0.554 | 0.0 | narrower hysteresis (enter .60, exit .30) |
| E11 | house5 | 0.005 | 0.022 | 0.105 | 0.026 | narrower hysteresis (enter .60, exit .30) |
| E11 | slice | 0.051 | 0.324 | 0.661 | 0.533 | narrower hysteresis (enter .60, exit .30) |
| E12 | ampds2 | 0.019 | 0.008 | - | 0.06 | detector min dwell 3 samples |
| E12 | house2 | 0.008 | 0.048 | 0.512 | 0.0 | detector min dwell 3 samples |
| E12 | house5 | 0.004 | 0.018 | 0.091 | 0.027 | detector min dwell 3 samples |
| E12 | slice | 0.044 | 0.321 | 0.626 | 0.569 | detector min dwell 3 samples |
| E13 | ampds2 | 0.002 | 0.004 | - | 0.062 | p25 signature + dwell prior + gap merge 12 s |
| E13 | house1 | 0.007 | 0.026 | 0.463 | 0.262 | p25 signature + dwell prior + gap merge 12 s |
| E13 | house2 | 0.001 | 0.054 | 0.666 | 0.0 | p25 signature + dwell prior + gap merge 12 s |
| E13 | house5 | 0.003 | 0.018 | 0.114 | 0.064 | p25 signature + dwell prior + gap merge 12 s |
| E13 | slice | 0.023 | 0.356 | 0.827 | 0.55 | p25 signature + dwell prior + gap merge 12 s |
| E14 | ampds2 | 0.008 | 0.005 | - | - | F2 disaggregation: generic events + nearest signature (level+dwell) |
| E14 | house2 | 0.004 | 0.039 | 0.106 | - | F2 disaggregation: generic events + nearest signature (level+dwell) |
| E14 | house5 | - | 0.079 | 0.211 | - | F2 disaggregation: generic events + nearest signature (level+dwell) |
| E14 | slice | 0.002 | 0.161 | 0.319 | - | F2 disaggregation: generic events + nearest signature (level+dwell) |
| E15 | ampds2 | 0.01 | 0.007 | - | - | F2 + ambiguity margin (second-best/best >= 1.3) |
| E15 | house2 | 0.004 | 0.036 | 0.112 | - | F2 + ambiguity margin (second-best/best >= 1.3) |
| E15 | house5 | - | 0.09 | 0.261 | - | F2 + ambiguity margin (second-best/best >= 1.3) |
| E15 | slice | 0.003 | 0.266 | 0.528 | - | F2 + ambiguity margin (second-best/best >= 1.3) |
| E16 | ampds2 | 0.008 | 0.005 | - | - | F2 with IQR-normalized distance |
| E16 | house2 | 0.004 | 0.039 | 0.106 | - | F2 with IQR-normalized distance |
| E16 | house5 | - | 0.079 | 0.211 | - | F2 with IQR-normalized distance |
| E16 | slice | 0.002 | 0.161 | 0.319 | - | F2 with IQR-normalized distance |
| E17 | ampds2 | 0.008 | 0.005 | - | - | F2 + plausibility (signature >= 60% of event level) |
| E17 | house2 | 0.004 | 0.039 | 0.106 | - | F2 + plausibility (signature >= 60% of event level) |
| E17 | house5 | - | 0.078 | 0.211 | - | F2 + plausibility (signature >= 60% of event level) |
| E17 | slice | 0.002 | 0.161 | 0.319 | - | F2 + plausibility (signature >= 60% of event level) |
| E18 | ampds2 | 0.01 | 0.007 | - | - | F2 + dwell-prior rejection of misfit events |
| E18 | house2 | 0.004 | 0.04 | 0.109 | - | F2 + dwell-prior rejection of misfit events |
| E18 | house5 | - | 0.09 | 0.256 | - | F2 + dwell-prior rejection of misfit events |
| E18 | slice | 0.004 | 0.286 | 0.569 | - | F2 + dwell-prior rejection of misfit events |
| E19 | ampds2 | 0.012 | 0.008 | - | - | F2 + plausibility + dwell prior + margin |
| E19 | house1 | 0.002 | 0.051 | 0.112 | - | F2 + plausibility + dwell prior + margin |
| E19 | house2 | 0.004 | 0.036 | 0.112 | - | F2 + plausibility + dwell prior + margin |
| E19 | house5 | - | 0.096 | 0.301 | - | F2 + plausibility + dwell prior + margin |
| E19 | slice | 0.003 | 0.37 | 0.737 | - | F2 + plausibility + dwell prior + margin |
