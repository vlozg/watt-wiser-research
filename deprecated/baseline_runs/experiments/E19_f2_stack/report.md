# E19 f2_stack

Hypothesis: F2 + plausibility + dwell prior + margin

Config: {"f2": true, "f2_norm": "abs", "f2_margin": 1.3, "f2_plaus": true, "f2_dwell_prior": true, "gt_gap_merge_s": 12}

## slice (weak 0.003 (-0.045 vs E00), all 0.37 (+0.063), devices 2, fp None%, 0.0s)

| device | GT | det | P | R | F1 | dF1 vs E00 |
|---|---|---|---|---|---|---|
| kettle | 171 | 133 | 0.84 | 0.66 | 0.74 | +0.12 |
| washing_machine | 101 | 669 | 0.00 | 0.01 | 0.00 | -0.06 |

F2: threshold 85 W, library 2 devices, 2058 generic events, rejected: margin 1121 / plaus-dwell 135.

Top confusion (GT device <- events attributed to):
- washing_machine <- kettle 11

## house2 (weak 0.004 (-0.014 vs E00), all 0.036 (-0.008), devices 6, fp None%, 0.1s)

| device | GT | det | P | R | F1 | dF1 vs E00 |
|---|---|---|---|---|---|---|
| kettle | 504 | 33 | 0.91 | 0.06 | 0.11 | -0.38 |
| microwave | 417 | 30 | 0.70 | 0.05 | 0.09 | -0.11 |
| dish_washer | 217 | 13 | 0.00 | 0.00 | 0.00 | +0.00 |
| washing_machine | 162 | 82 | 0.01 | 0.01 | 0.01 | -0.03 |
| rice_cooker | 45 | 855 | 0.00 | 0.04 | 0.00 | -0.00 |
| toaster | 20 | 11 | 0.00 | 0.00 | 0.00 | -0.01 |

F2: threshold 84 W, library 6 devices, 1744 generic events, rejected: margin 314 / plaus-dwell 406.

Top confusion (GT device <- events attributed to):
- microwave <- rice_cooker 62, toaster 3
- kettle <- rice_cooker 42
- washing_machine <- rice_cooker 31, toaster 3, kettle 1, microwave 1
- toaster <- rice_cooker 2
- dish_washer <- rice_cooker 1

## house5 (weak None, all 0.096 (+0.076), devices 6, fp None%, 0.0s)

| device | GT | det | P | R | F1 | dF1 vs E00 |
|---|---|---|---|---|---|---|
| electric_hob | 1009 | 54 | 0.46 | 0.03 | 0.05 | -0.15 |
| kettle | 153 | 365 | 0.21 | 0.51 | 0.30 | +0.22 |
| hairdryer | 105 | 33 | 0.06 | 0.02 | 0.03 | -0.07 |
| nespresso_pixie | 80 | 60 | 0.20 | 0.15 | 0.17 | +0.16 |
| toaster | 22 | 47 | 0.02 | 0.04 | 0.03 | +0.02 |
| steam_iron | 2 | 43 | 0.00 | 0.00 | 0.00 | +0.00 |

F2: threshold 464 W, library 6 devices, 2401 generic events, rejected: margin 1720 / plaus-dwell 79.

Top confusion (GT device <- events attributed to):
- electric_hob <- kettle 57, toaster 19, nespresso_pixie 8, hairdryer 3
- hairdryer <- toaster 18, nespresso_pixie 9, steam_iron 1
- nespresso_pixie <- steam_iron 4, electric_hob 1, kettle 1, toaster 1
- toaster <- kettle 4, hairdryer 1

## ampds2 (weak 0.012 (-0.005 vs E00), all 0.008 (+0.001), devices 3, fp None%, 0.2s)

| device | GT | det | P | R | F1 | dF1 vs E00 |
|---|---|---|---|---|---|---|
| DWE | 2003 | 6233 | 0.00 | 0.01 | 0.01 | -0.00 |
| CDE | 628 | 2473 | 0.01 | 0.05 | 0.02 | -0.04 |
| MHE | 4 | 0 | 0.00 | 0.00 | 0.00 | +0.00 |

F2: threshold 344 W, library 3 devices, 11538 generic events, rejected: margin 1920 / plaus-dwell 912.

Top confusion (GT device <- events attributed to):
- DWE <- CDE 174
- CDE <- DWE 7
- MHE <- CDE 3, DWE 3

