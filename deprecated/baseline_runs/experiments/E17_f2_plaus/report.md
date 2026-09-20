# E17 f2_plaus

Hypothesis: F2 + plausibility (signature >= 60% of event level)

Config: {"f2": true, "f2_norm": "abs", "f2_plaus": true, "gt_gap_merge_s": 12}

## slice (weak 0.002 (-0.046 vs E00), all 0.161 (-0.146), devices 2, fp None%, 0.0s)

| device | GT | det | P | R | F1 | dF1 vs E00 |
|---|---|---|---|---|---|---|
| kettle | 171 | 556 | 0.21 | 0.68 | 0.32 | -0.30 |
| washing_machine | 101 | 1502 | 0.00 | 0.02 | 0.00 | -0.06 |

F2: threshold 85 W, library 2 devices, 2058 generic events, rejected: margin 0 / plaus-dwell 0.

Top confusion (GT device <- events attributed to):
- washing_machine <- kettle 64
- kettle <- washing_machine 11

## house2 (weak 0.004 (-0.014 vs E00), all 0.039 (-0.005), devices 6, fp None%, 0.0s)

| device | GT | det | P | R | F1 | dF1 vs E00 |
|---|---|---|---|---|---|---|
| kettle | 504 | 100 | 0.32 | 0.06 | 0.11 | -0.38 |
| microwave | 417 | 47 | 0.57 | 0.07 | 0.12 | -0.09 |
| dish_washer | 217 | 29 | 0.00 | 0.00 | 0.00 | +0.00 |
| washing_machine | 162 | 114 | 0.01 | 0.01 | 0.01 | -0.03 |
| rice_cooker | 45 | 1246 | 0.00 | 0.04 | 0.00 | -0.00 |
| toaster | 20 | 163 | 0.00 | 0.00 | 0.00 | -0.01 |

F2: threshold 84 W, library 6 devices, 1744 generic events, rejected: margin 0 / plaus-dwell 45.

Top confusion (GT device <- events attributed to):
- kettle <- rice_cooker 442, toaster 5, dish_washer 4, microwave 1
- microwave <- rice_cooker 357, toaster 11, kettle 1
- dish_washer <- rice_cooker 189, microwave 5, kettle 4, toaster 2
- washing_machine <- rice_cooker 124, toaster 33, kettle 14, microwave 8
- toaster <- rice_cooker 20

## house5 (weak None, all 0.078 (+0.058), devices 6, fp None%, 0.1s)

| device | GT | det | P | R | F1 | dF1 vs E00 |
|---|---|---|---|---|---|---|
| electric_hob | 1009 | 606 | 0.09 | 0.05 | 0.07 | -0.13 |
| kettle | 153 | 635 | 0.13 | 0.54 | 0.21 | +0.13 |
| hairdryer | 105 | 158 | 0.01 | 0.02 | 0.01 | -0.08 |
| nespresso_pixie | 80 | 90 | 0.16 | 0.17 | 0.17 | +0.16 |
| toaster | 22 | 562 | 0.01 | 0.14 | 0.01 | +0.00 |
| steam_iron | 2 | 335 | 0.00 | 0.00 | 0.00 | +0.00 |

F2: threshold 464 W, library 6 devices, 2401 generic events, rejected: margin 0 / plaus-dwell 15.

Top confusion (GT device <- events attributed to):
- electric_hob <- toaster 464, kettle 386, steam_iron 65, nespresso_pixie 13
- hairdryer <- toaster 83, steam_iron 15, nespresso_pixie 11, kettle 2
- nespresso_pixie <- steam_iron 47, electric_hob 6, toaster 3, kettle 2
- kettle <- toaster 39
- toaster <- kettle 9, hairdryer 1, steam_iron 1
- steam_iron <- kettle 2

## ampds2 (weak 0.008 (-0.009 vs E00), all 0.005 (-0.002), devices 3, fp None%, 0.2s)

| device | GT | det | P | R | F1 | dF1 vs E00 |
|---|---|---|---|---|---|---|
| DWE | 2003 | 6904 | 0.00 | 0.01 | 0.00 | -0.01 |
| CDE | 628 | 4312 | 0.01 | 0.05 | 0.01 | -0.04 |
| MHE | 4 | 118 | 0.00 | 0.00 | 0.00 | +0.00 |

F2: threshold 344 W, library 3 devices, 11538 generic events, rejected: margin 0 / plaus-dwell 204.

Top confusion (GT device <- events attributed to):
- DWE <- CDE 1623, MHE 107
- CDE <- MHE 18, DWE 7
- MHE <- CDE 4, DWE 3

