# R6: anomaly-loop rehearsal on the R1 residual/UNKNOWN stream

| injected shape | level W | dwell s | detected | latency |
|---|---|---|---|---|
| 2 kW x 5 min step | 2000 | 300 | yes | 0 s |
| 3 kW x 1 min spike | 3000 | 60 | yes | 0 s |
| 800 W x 30 min stuck load | 800 | 1800 | yes | 0 s |
| 1.2 kW x 10 min (on/off at 60 s) | 1200 | 600 | yes | 0 s |
| 1.5 kW x 20 min at 03:17 | 1500 | 1200 | yes | 0 s |
| 2.5 kW x 45 min unusual | 2500 | 2700 | yes | 0 s |
| 400 W x 2 h small-but-long | 400 | 7200 | NO | - |
| 900 W x 10 min mid-morning | 900 | 600 | yes | 0 s |

## Result

7/8 synthetic anomalies detected (onset-based) by a generic 1000 W threshold on the
residual stream; background: 7 detections on the clean residual (3.27 kWh of unattributed energy - the UNKNOWN stream the product loop consumes).

## Mechanics verdict

- Step anomalies (2 kW+, >2 min) are caught with single-sample latency; the loop
  mechanics (detect -> attribute -> UNKNOWN) close with zero human labels.
- Small-but-long loads (400 W) never cross the generic threshold: they need their
  own signature - the same lesson the 60 s rung teaches for the small classes.
