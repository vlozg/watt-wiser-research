# Experiment 2 — Seq2Seq Multi-Appliance Power Estimation

## 1. Experiment Overview

**Experiment ID:** EXP-02  
**Method:** Lightweight CNN Seq2Seq  
**Formulation:** Appliance-level power estimation / disaggregation  
**Dataset:** UK-DALE  
**House:** House 1  
**Cadence:** 6 seconds  
**Appliances:** Kettle, Microwave, Fridge, Washing Machine  
**Calibration sizes (K):** 1, 3, 5, 10  
**Random draws per K:** 10  
**Training epochs:** 5  
**Total model runs:** 4 × 4 × 10 = **160 runs**

## 2. Research Question

> How does a lightweight Seq2Seq model perform at estimating appliance-level power across different appliance types, and how does performance change as the number of calibration sessions increases?

## 3. Experimental Setup

Aggregate household mains power at 6-second cadence was used as input. The target was continuous appliance power for one appliance at a time. A lightweight CNN-based Seq2Seq model processed fixed temporal windows and predicted appliance power.

Calibration-session budgets were K = 1, 3, 5, and 10, with 10 random draws for each K.

## 4. Metrics

- **MAE (W):** mean absolute power error; lower is better.
- **nMAE:** normalized MAE; lower is better.
- **Energy Error:** difference between estimated and actual appliance energy; lower is better.
- **F1:** pointwise ON/OFF detection F1 using the experiment's 50 W threshold; higher is better.

> This F1 is the pointwise metric used by the current Seq2Seq experiment and is not directly equivalent to the episode/span F1 used in the FHMM experiment.

## 5. Complete Results

| Appliance | K | MAE (W) | nMAE | Energy Error | F1 |
|---|---:|---:|---:|---:|---:|
| Fridge | 1 | 66.80 | 1.654 | 1.541 | 0.140 |
| Fridge | 3 | 102.32 | 2.533 | 2.317 | 0.481 |
| Fridge | 5 | 125.68 | 3.111 | 2.869 | 0.487 |
| Fridge | 10 | 71.12 | 1.761 | 1.434 | 0.231 |
| Kettle | 1 | 285.06 | 20.539 | 19.537 | 0.011 |
| Kettle | 3 | 167.63 | 12.078 | 10.952 | 0.037 |
| Kettle | 5 | 186.37 | 13.428 | 12.341 | 0.036 |
| Kettle | 10 | 216.74 | 15.616 | 14.551 | 0.034 |
| Microwave | 1 | 159.78 | 21.275 | 20.138 | 0.058 |
| Microwave | 3 | 97.80 | 13.023 | 11.641 | 0.030 |
| Microwave | 5 | 104.37 | 13.897 | 12.505 | 0.031 |
| Microwave | 10 | 127.95 | 17.037 | 15.734 | 0.035 |
| Washing Machine | 1 | 311.01 | 11.941 | 11.007 | 0.094 |
| Washing Machine | 3 | 327.40 | 12.570 | 11.667 | 0.068 |
| Washing Machine | 5 | 300.88 | 11.552 | 10.653 | 0.085 |
| Washing Machine | 10 | 323.01 | 12.401 | 11.564 | 0.100 |

## 6. Appliance-by-Appliance Performance

### Fridge

The fridge produced the highest pointwise F1 in the experiment. F1 increased from 0.140 at K=1 to 0.481 at K=3 and 0.487 at K=5, then fell to 0.231 at K=10. Best MAE was 66.80 W at K=1; best energy error was 1.434 at K=10.

### Kettle

The kettle showed weak performance overall. Best MAE was 167.63 W at K=3, best nMAE was 12.078 at K=3, best energy error was 10.952 at K=3, and best F1 was only 0.037 at K=3.

### Microwave

The microwave had the lowest MAE among the four appliances: 97.80 W at K=3. Its best nMAE was 13.023 and best energy error was 11.641, both at K=3. Its highest F1 was 0.058 at K=1.

### Washing Machine

The washing machine remained difficult to estimate. Best MAE was 300.88 W at K=5, best nMAE was 11.552 at K=5, best energy error was 10.653 at K=5, and highest F1 was 0.100 at K=10.

## 7. Cross-Appliance Findings

- **Fridge:** highest pointwise F1, reaching **0.487 at K=5**.
- **Microwave:** lowest MAE, reaching **97.80 W at K=3**.
- **Kettle:** best MAE **167.63 W** and best F1 **0.037**, both at K=3.
- **Washing machine:** largest absolute MAE range, about **301–327 W**.

The appliances did not respond consistently to calibration size. More calibration sessions did not automatically improve performance.

## 8. Effect of Calibration Size

The K-curve was non-monotonic across appliances. For example:

- Fridge F1: 0.140 → 0.481 → 0.487 → 0.231
- Kettle F1: 0.011 → 0.037 → 0.036 → 0.034
- Microwave F1: 0.058 → 0.030 → 0.031 → 0.035
- Washing machine F1: 0.094 → 0.068 → 0.085 → 0.100

Therefore, within this experiment, increasing calibration sessions from K=1 to K=10 did not produce a monotonic improvement.

## 9. Interpretation

The same Seq2Seq architecture behaved substantially differently across appliance types. The fridge produced much stronger pointwise detection F1, while kettle and washing machine detection remained weak. The microwave produced the lowest absolute power error among the four appliances.

These results indicate that appliance type and signal characteristics matter when evaluating Seq2Seq for WattWiser. Calibration size alone did not explain performance.

## 10. Limitations

1. Only **House 1** was evaluated.
2. Only **6-second cadence** was evaluated; 60-second Seq2Seq performance has not been tested.
3. Only four appliances were included.
4. Current calibration-session selection uses labelled appliance data and is not yet identical to the final aggregate-only WattWiser user calibration workflow.
5. The reported F1 is pointwise and is not directly comparable to the FHMM episode/span F1.
6. This is a lightweight CNN Seq2Seq implementation, not a reproduction of a specific published SOTA model.

## 11. What This Experiment Establishes

1. Seq2Seq can be evaluated as a direct appliance-power estimation approach.
2. Performance varies substantially between appliance types.
3. Calibration size K has a non-monotonic relationship with performance in this experiment.
4. Fridge produced the strongest pointwise detection F1.
5. Microwave produced the lowest MAE among the four appliances.
6. Kettle and washing machine remained difficult under the current configuration.
7. Broader household evaluation and a more faithful calibration protocol are required before stronger conclusions are made.

## 12. Next Experimental Direction

A useful follow-up is to run the same Seq2Seq configuration on additional houses, using the same appliances where available. This will help distinguish appliance-specific difficulty from household-specific effects and model/calibration limitations.

## 13. Reproducibility

**Dataset:** UK-DALE  
**House:** House 1  
**Cadence:** 6 seconds  
**Model:** Lightweight CNN Seq2Seq  
**Window:** 128 samples  
**Batch size:** 64  
**Epochs:** 5  
**Learning rate:** 1e-3  
**K:** 1, 3, 5, 10  
**Draws:** 10 per K  
**Total runs:** 160  
**Evaluation:** MAE, nMAE, energy error, pointwise F1

Expected result files:

```text
data/results/seq2seq/
    seq2seq_multi_appliance_raw.csv
    seq2seq_multi_appliance_summary.csv
```

## Final Summary

The multi-appliance Seq2Seq experiment tested **160 model runs** across four appliance types and four calibration budgets using House 1 at 6-second resolution. The fridge achieved the highest pointwise F1, while the microwave achieved the lowest MAE among the four appliances. The kettle and washing machine were comparatively difficult under the current configuration. Increasing calibration sessions from K=1 to K=10 did not consistently improve performance.
