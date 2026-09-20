# E15 f2_margin

Hypothesis: F2 + ambiguity margin (second-best/best >= 1.3)

Config: {"f2": true, "f2_norm": "abs", "f2_margin": 1.3, "gt_gap_merge_s": 12}

## slice (weak 0.003 (-0.045 vs E00), all 0.266 (-0.041), devices 2, fp None%, 0.0s)

| device | GT | det | P | R | F1 | dF1 vs E00 |
|---|---|---|---|---|---|---|
| kettle | 171 | 268 | 0.43 | 0.68 | 0.53 | -0.09 |
| washing_machine | 101 | 669 | 0.00 | 0.01 | 0.00 | -0.06 |

F2: threshold 85 W, library 2 devices, 2058 generic events, rejected: margin 1121 / plaus-dwell 0.

Top confusion (GT device <- events attributed to):
- washing_machine <- kettle 50

## house2 (weak 0.004 (-0.014 vs E00), all 0.036 (-0.008), devices 6, fp None%, 0.1s)

| device | GT | det | P | R | F1 | dF1 vs E00 |
|---|---|---|---|---|---|---|
| kettle | 504 | 33 | 0.91 | 0.06 | 0.11 | -0.38 |
| microwave | 417 | 30 | 0.70 | 0.05 | 0.09 | -0.11 |
| dish_washer | 217 | 23 | 0.00 | 0.00 | 0.00 | +0.00 |
| washing_machine | 162 | 85 | 0.01 | 0.01 | 0.01 | -0.03 |
| rice_cooker | 45 | 1247 | 0.00 | 0.04 | 0.00 | -0.00 |
| toaster | 20 | 12 | 0.00 | 0.00 | 0.00 | -0.01 |

F2: threshold 84 W, library 6 devices, 1744 generic events, rejected: margin 314 / plaus-dwell 0.

Top confusion (GT device <- events attributed to):
- kettle <- rice_cooker 456
- microwave <- rice_cooker 360, toaster 3
- dish_washer <- rice_cooker 197
- washing_machine <- rice_cooker 127, toaster 3, kettle 1, microwave 1
- toaster <- rice_cooker 20

## house5 (weak None, all 0.09 (+0.070), devices 6, fp None%, 0.1s)

| device | GT | det | P | R | F1 | dF1 vs E00 |
|---|---|---|---|---|---|---|
| electric_hob | 1009 | 54 | 0.46 | 0.03 | 0.05 | -0.15 |
| kettle | 153 | 444 | 0.18 | 0.51 | 0.26 | +0.18 |
| hairdryer | 105 | 33 | 0.06 | 0.02 | 0.03 | -0.07 |
| nespresso_pixie | 80 | 60 | 0.20 | 0.15 | 0.17 | +0.16 |
| toaster | 22 | 47 | 0.02 | 0.04 | 0.03 | +0.02 |
| steam_iron | 2 | 43 | 0.00 | 0.00 | 0.00 | +0.00 |

F2: threshold 464 W, library 6 devices, 2401 generic events, rejected: margin 1720 / plaus-dwell 0.

Top confusion (GT device <- events attributed to):
- electric_hob <- kettle 250, toaster 19, nespresso_pixie 8, hairdryer 3
- hairdryer <- toaster 18, nespresso_pixie 9, kettle 2, steam_iron 1
- toaster <- kettle 8, hairdryer 1
- nespresso_pixie <- steam_iron 4, kettle 2, electric_hob 1, toaster 1

## ampds2 (weak 0.01 (-0.007 vs E00), all 0.007 (+0.000), devices 3, fp None%, 0.2s)

| device | GT | det | P | R | F1 | dF1 vs E00 |
|---|---|---|---|---|---|---|
| DWE | 2003 | 6355 | 0.00 | 0.01 | 0.01 | -0.00 |
| CDE | 628 | 3239 | 0.01 | 0.05 | 0.01 | -0.04 |
| MHE | 4 | 24 | 0.00 | 0.00 | 0.00 | +0.00 |

F2: threshold 344 W, library 3 devices, 11538 generic events, rejected: margin 1920 / plaus-dwell 0.

Top confusion (GT device <- events attributed to):
- DWE <- CDE 1008, MHE 43
- CDE <- DWE 7, MHE 6
- MHE <- CDE 3, DWE 3

