# R3: calibration learning curve (F1 vs N calibration episodes)

| N | dt | fridge | dish_washer | kettle | washing_machine |
|---|---|---|---|---|---|
| 1 | 6 s| 0.50 (P 0.41 R 0.64, on 106 W) | 0.03 (P 0.02 R 0.39, on 57 W) | 0.62 (P 0.45 R 0.98, on 2921 W) | 0.05 (P 0.03 R 0.22, on 54 W) |
| 2 | 6 s| 0.50 (P 0.41 R 0.64, on 106 W) | 0.03 (P 0.02 R 0.30, on 97 W) | 0.62 (P 0.45 R 0.98, on 2924 W) | 0.00 (P 0.00 R 0.00, on 2089 W) |
| 5 | 6 s| 0.51 (P 0.42 R 0.64, on 108 W) | 0.03 (P 0.02 R 0.30, on 97 W) | 0.62 (P 0.45 R 0.98, on 2916 W) | 0.00 (P 0.00 R 0.00, on 2072 W) |
| 10 | 6 s| 0.51 (P 0.42 R 0.64, on 108 W) | 0.03 (P 0.02 R 0.30, on 97 W) | 0.62 (P 0.45 R 0.98, on 2896 W) | 0.09 (P 0.07 R 0.15, on 290 W) |
| 20 | 6 s| 0.51 (P 0.43 R 0.64, on 109 W) | 0.03 (P 0.02 R 0.30, on 97 W) | 0.62 (P 0.45 R 0.98, on 2887 W) | 0.09 (P 0.06 R 0.19, on 243 W) |
| all | 6 s| 0.51 (P 0.43 R 0.64, on 109 W) | 0.03 (P 0.02 R 0.30, on 97 W) | 0.62 (P 0.45 R 0.98, on 2884 W) | 0.06 (P 0.04 R 0.18, on 177 W) |
| 1 | 60 s| 0.77 (P 0.82 R 0.72, on 106 W) | 0.01 (P 0.00 R 0.16, on 97 W) | 0.76 (P 0.64 R 0.94, on 1856 W) | 0.03 (P 0.01 R 0.45, on 152 W) |
| 2 | 60 s| 0.77 (P 0.82 R 0.72, on 107 W) | 0.01 (P 0.00 R 0.16, on 97 W) | 0.76 (P 0.64 R 0.94, on 1856 W) | 0.03 (P 0.01 R 0.45, on 154 W) |
| 5 | 60 s| 0.77 (P 0.82 R 0.72, on 108 W) | 0.01 (P 0.00 R 0.16, on 97 W) | 0.76 (P 0.64 R 0.94, on 1761 W) | 0.03 (P 0.01 R 0.45, on 152 W) |
| 10 | 60 s| 0.77 (P 0.82 R 0.72, on 108 W) | 0.01 (P 0.00 R 0.16, on 97 W) | 0.76 (P 0.64 R 0.94, on 1765 W) | 0.03 (P 0.01 R 0.45, on 152 W) |
| 20 | 60 s| 0.76 (P 0.82 R 0.71, on 108 W) | 0.01 (P 0.00 R 0.16, on 97 W) | 0.76 (P 0.64 R 0.93, on 1994 W) | 0.03 (P 0.01 R 0.45, on 152 W) |
| all | 60 s| 0.76 (P 0.82 R 0.71, on 109 W) | 0.01 (P 0.00 R 0.16, on 97 W) | 0.76 (P 0.64 R 0.94, on 1941 W) | 0.03 (P 0.01 R 0.45, on 152 W) |

## 500 W-floor variant

Only the kettle clears a 500 W signature floor on this substrate; the variant is
therefore the kettle curve alone:
| N | dt | kettle F1 |
|---|---|---|
| 1 | 6 s | 0.62 (P 0.45 R 0.98) |
| 2 | 6 s | 0.62 (P 0.45 R 0.98) |
| 5 | 6 s | 0.62 (P 0.45 R 0.98) |
| 10 | 6 s | 0.62 (P 0.45 R 0.98) |
| 20 | 6 s | 0.62 (P 0.45 R 0.98) |
| all | 6 s | 0.62 (P 0.45 R 0.98) |

## Verdict (measured)

- The curve is FLAT from N=1 for the single-state loads: fridge F1 0.50 at N=1 vs
  0.51 at N=all, kettle 0.62 throughout - one episode already lands the threshold
  in the right band when the load has one dominant ON level.
- washing_machine is the exception and it is NON-monotonic: N=1 locks a standby-
  level signature (54 W, F1 0.05); N=2 locks a heater episode (2089 W) and overfires
  (P 0.00); only N>=10 stabilizes (F1 0.09). Multi-state loads need episodes
  covering their modes, not more episodes of one mode.
- Session-length answer: minutes, not days. A 10-20 episode cap per appliance
  (~2 min for the kettle, tens of minutes for the cyclic loads) is enough; the
  binding constraint is covering the modes, not the episode count.
- At 60 s the same flatness holds (fridge 0.77 from N=1) - coarser sampling does
  not make calibration harder for M0, it makes episodes cleaner.
