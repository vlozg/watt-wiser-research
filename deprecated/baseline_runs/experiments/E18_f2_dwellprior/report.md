# E18 f2_dwellprior

Hypothesis: F2 + dwell-prior rejection of misfit events

Config: {"f2": true, "f2_norm": "abs", "f2_dwell_prior": true, "gt_gap_merge_s": 12}

## slice (weak 0.004 (-0.044 vs E00), all 0.286 (-0.021), devices 2, fp None%, 0.0s)

| device | GT | det | P | R | F1 | dF1 vs E00 |
|---|---|---|---|---|---|---|
| kettle | 171 | 223 | 0.50 | 0.66 | 0.57 | -0.05 |
| washing_machine | 101 | 967 | 0.00 | 0.02 | 0.00 | -0.06 |

F2: threshold 85 W, library 2 devices, 2058 generic events, rejected: margin 0 / plaus-dwell 868.

Top confusion (GT device <- events attributed to):
- washing_machine <- kettle 11
- kettle <- washing_machine 1

## house2 (weak 0.004 (-0.014 vs E00), all 0.04 (-0.004), devices 6, fp None%, 0.0s)

| device | GT | det | P | R | F1 | dF1 vs E00 |
|---|---|---|---|---|---|---|
| kettle | 504 | 82 | 0.39 | 0.06 | 0.11 | -0.38 |
| microwave | 417 | 42 | 0.64 | 0.07 | 0.12 | -0.09 |
| dish_washer | 217 | 18 | 0.00 | 0.00 | 0.00 | +0.00 |
| washing_machine | 162 | 131 | 0.01 | 0.01 | 0.01 | -0.03 |
| rice_cooker | 45 | 875 | 0.00 | 0.04 | 0.00 | -0.00 |
| toaster | 20 | 86 | 0.00 | 0.00 | 0.00 | -0.01 |

F2: threshold 84 W, library 6 devices, 1744 generic events, rejected: margin 0 / plaus-dwell 510.

Top confusion (GT device <- events attributed to):
- washing_machine <- rice_cooker 43, toaster 28, kettle 3, microwave 1
- microwave <- rice_cooker 67, toaster 7
- kettle <- rice_cooker 52, dish_washer 4
- dish_washer <- rice_cooker 4, kettle 1, toaster 1, washing_machine 1
- toaster <- rice_cooker 2

## house5 (weak None, all 0.09 (+0.070), devices 6, fp None%, 0.1s)

| device | GT | det | P | R | F1 | dF1 vs E00 |
|---|---|---|---|---|---|---|
| electric_hob | 1009 | 621 | 0.10 | 0.06 | 0.07 | -0.12 |
| kettle | 153 | 472 | 0.17 | 0.52 | 0.26 | +0.17 |
| hairdryer | 105 | 158 | 0.01 | 0.02 | 0.01 | -0.08 |
| nespresso_pixie | 80 | 90 | 0.16 | 0.17 | 0.17 | +0.16 |
| toaster | 22 | 177 | 0.02 | 0.14 | 0.03 | +0.02 |
| steam_iron | 2 | 335 | 0.00 | 0.00 | 0.00 | +0.00 |

F2: threshold 464 W, library 6 devices, 2401 generic events, rejected: margin 0 / plaus-dwell 548.

Top confusion (GT device <- events attributed to):
- electric_hob <- kettle 66, steam_iron 65, toaster 37, nespresso_pixie 13
- hairdryer <- toaster 40, steam_iron 15, nespresso_pixie 11
- nespresso_pixie <- steam_iron 47, electric_hob 6, hairdryer 1, kettle 1
- toaster <- kettle 5, hairdryer 1, steam_iron 1
- kettle <- electric_hob 2, toaster 1

## ampds2 (weak 0.01 (-0.007 vs E00), all 0.007 (+0.000), devices 3, fp None%, 0.2s)

| device | GT | det | P | R | F1 | dF1 vs E00 |
|---|---|---|---|---|---|---|
| DWE | 2003 | 7074 | 0.00 | 0.01 | 0.00 | -0.01 |
| CDE | 628 | 2992 | 0.01 | 0.05 | 0.02 | -0.04 |
| MHE | 4 | 0 | 0.00 | 0.00 | 0.00 | +0.00 |

F2: threshold 344 W, library 3 devices, 11538 generic events, rejected: margin 0 / plaus-dwell 1472.

Top confusion (GT device <- events attributed to):
- DWE <- CDE 210
- CDE <- DWE 7
- MHE <- CDE 4, DWE 3

