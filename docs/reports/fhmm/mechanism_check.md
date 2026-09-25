# FHMM mechanism check (Phase 0, plan section 7)
Frozen before any FHMM run. How to read the tables below:
- Ground truth (GT): the hand-annotated device cycle marks; a press is one cycle read as a simulated start/stop button press.
- Parity rule: calibration windows come from GT marks; the aggregate supplies the watts; submeters are never a model input.
- floor / sigma_off: the aggregate's always-on base level (10th-percentile watts) and the noise width around it (1.4826 x MAD), estimated over the pre-split span.
- margin: a device's mean ON level minus the floor, in sigmas of the noise. >= 4 clear, >= 2 marginal, else sub-noise: not separable from background.
- Pair tables: when two devices run together, the predicted sum of their levels vs the observed median level - how close the additive model is.

## house_1
floor 156.0 W, sigma_off 100.8 W
| device | n_sess | level W | sd W | dwell s | margin (sd) | verdict |
|---|---|---|---|---|---|---|
| washing_machine | 20 | 1084.1 | 955.8 | 7085 | 9.2 | clear |
| kettle | 1138 | 2692.7 | 205.0 | 136 | 25.2 | clear |
| microwave | 775 | 1787.8 | 290.9 | 82 | 16.2 | clear |
| fridge | 39666 | 141.0 | 8.0 | 1473 | -0.1 | sub-noise |

| pair | n_overlaps | pred sum W | obs p50 W | ratio p50 |
|---|---|---|---|---|
| washing_machine+kettle | 527 | 3776.8 | 3050.2 | 0.81 |
| washing_machine+microwave | 255 | 2871.9 | 2199.3 | 0.77 |
| washing_machine+fridge | 2574 | 1225.1 | 709.0 | 0.58 |
| kettle+microwave | 350 | 4480.6 | 4187.9 | 0.93 |
| kettle+fridge | 2817 | 2833.7 | 2670.7 | 0.94 |
| microwave+fridge | 1228 | 1928.8 | 1708.6 | 0.89 |

## house_2
floor 134.0 W, sigma_off 93.4 W
| device | n_sess | level W | sd W | dwell s | margin (sd) | verdict |
|---|---|---|---|---|---|---|
| washing_machine | 20 | 963.5 | 953.0 | 3026 | 8.9 | clear |
| dishwasher | 20 | 1626.2 | 973.9 | 3356 | 16.0 | clear |
| kettle | 522 | 3225.1 | 92.8 | 168 | 33.1 | clear |
| microwave | 261 | 1400.2 | 135.5 | 109 | 13.6 | clear |
| fridge | 3839 | 74.0 | 8.0 | 912 | -0.6 | sub-noise |

| pair | n_overlaps | pred sum W | obs p50 W | ratio p50 |
|---|---|---|---|---|
| washing_machine+dishwasher | 4 | 2589.7 | 1651.8 | 0.64 |
| washing_machine+kettle | 16 | 4188.7 | 3319.2 | 0.79 |
| washing_machine+microwave | 17 | 2363.7 | 1643.9 | 0.7 |
| washing_machine+fridge | 72 | 1037.5 | 806.5 | 0.78 |
| dishwasher+kettle | 45 | 4851.3 | 4839.0 | 1.0 |
| dishwasher+microwave | 3 | 3026.3 | 3072.7 | 1.02 |
| dishwasher+fridge | 163 | 1700.2 | 1738.1 | 1.02 |
| kettle+microwave | 16 | 4625.3 | 4241.2 | 0.92 |
| kettle+fridge | 269 | 3299.1 | 3114.6 | 0.94 |
| microwave+fridge | 149 | 1474.2 | 1473.0 | 1.0 |

## house_5
floor 428.0 W, sigma_off 130.5 W
| device | n_sess | level W | sd W | dwell s | margin (sd) | verdict |
|---|---|---|---|---|---|---|
| washing_machine | 20 | 763.1 | 771.6 | 9261 | 2.6 | marginal |
| dishwasher | 20 | 1373.6 | 1041.3 | 6213 | 7.2 | clear |
| kettle | 186 | 3811.9 | 290.1 | 110 | 25.9 | clear |
| fridge | 2987 | 159.0 | 8.0 | 1311 | -2.1 | sub-noise |

| pair | n_overlaps | pred sum W | obs p50 W | ratio p50 |
|---|---|---|---|---|
| washing_machine+dishwasher | 8 | 2136.7 | 1463.3 | 0.68 |
| washing_machine+kettle | 14 | 4575.0 | 3380.1 | 0.74 |
| washing_machine+fridge | 206 | 922.1 | 795.9 | 0.86 |
| dishwasher+kettle | 6 | 5185.5 | 4728.4 | 0.91 |
| dishwasher+fridge | 89 | 1532.6 | 1271.2 | 0.83 |
| kettle+fridge | 66 | 3970.9 | 3235.6 | 0.81 |

## Written predictions (frozen pre-run)

- house_1/washing_machine: clear at 9.21 sigma_off above the floor - FHMM should separate it from ambient.
- house_1/kettle: clear at 25.16 sigma_off above the floor - FHMM should separate it from ambient.
- house_1/microwave: clear at 16.19 sigma_off above the floor - FHMM should separate it from ambient.
- house_1/fridge: level within 2 sigma_off of the floor - marginal; expect intermittent claims.
- house_2/washing_machine: clear at 8.88 sigma_off above the floor - FHMM should separate it from ambient.
- house_2/dishwasher: clear at 15.98 sigma_off above the floor - FHMM should separate it from ambient.
- house_2/kettle: clear at 33.09 sigma_off above the floor - FHMM should separate it from ambient.
- house_2/microwave: clear at 13.56 sigma_off above the floor - FHMM should separate it from ambient.
- house_2/fridge: level within 2 sigma_off of the floor - marginal; expect intermittent claims.
- house_5/washing_machine: clear at 2.57 sigma_off above the floor - FHMM should separate it from ambient.
- house_5/dishwasher: clear at 7.25 sigma_off above the floor - FHMM should separate it from ambient.
- house_5/kettle: clear at 25.94 sigma_off above the floor - FHMM should separate it from ambient.
- house_5/fridge: level within 2 sigma_off of the floor - marginal; expect intermittent claims.
