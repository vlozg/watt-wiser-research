# Experiment 2 --- Pattern/Profile Matching

## 1. Experiment Overview

**Experiment:** 2 --- Pattern/Profile Matching\
**Formulation:** Pattern matching\
**Method:** Calibrated appliance-profile matching\
**Dataset:** UK-DALE\
**Houses evaluated:** House 1 and House 2\
**Appliances:** Dishwasher, fridge, kettle, microwave, washing machine\
**Calibration sizes (K):** 1, 3, 5, 10, 20\
**Draws per K:** 10\
**Total completed runs:** 500

### Research Question

Can a simple calibrated appliance-profile matching approach identify
appliance activity and estimate appliance power from aggregate household
electricity measurements?

A secondary question was whether increasing the number of calibration
sessions consistently improves performance.

## 2. Method

For each house and appliance, K calibration sessions were selected for
each experiment run. An appliance profile was constructed from those
sessions and matched against the aggregate test signal. The resulting
appliance power estimate was evaluated against the ground-truth
appliance signal.

The experiment was repeated for K = 1, 3, 5, 10 and 20, with 10 random
draws at each K value.

## 3. Evaluation Metrics

-   **MAE (W):** Mean absolute error of estimated appliance power.
-   **nMAE:** Normalised MAE.
-   **Energy Error:** Error in estimated appliance energy.
-   **F1:** Appliance activity/detection F1 score.

Lower MAE, nMAE and energy error indicate lower estimation error. Higher
F1 indicates better detection.

## 4. Results Summary

  House   Appliance           Best/lowest MAE observed   Highest F1 observed
  ------- ----------------- -------------------------- ---------------------
  H1      Dishwasher                     116.0 W (K=1)          0.074 (K=10)
  H1      Fridge                          40.8 W (K=1)          0.034 (K=10)
  H1      Kettle                         185.4 W (K=3)           0.121 (K=3)
  H1      Microwave                     296.3 W (K=20)          0.036 (K=20)
  H1      Washing machine                184.1 W (K=1)           0.025 (K=3)
  H2      Dishwasher                     173.9 W (K=1)           0.354 (K=3)
  H2      Fridge                          53.6 W (K=3)           0.268 (K=1)
  H2      Kettle                         152.8 W (K=3)           0.221 (K=3)
  H2      Microwave                      160.8 W (K=3)           0.041 (K=3)
  H2      Washing machine                123.3 W (K=1)           0.009 (K=5)

## 5. Appliance-Level Findings

### Dishwasher

Performance differed strongly between houses. House 1 had low detection
F1, approximately 0.05--0.07. House 2 reached an F1 of 0.354 at K=3.
Increasing K beyond 3 did not consistently improve detection.

### Fridge

The fridge showed an important difference between estimation error and
detection. House 1 had low MAE, around 41--47 W, but F1 remained close
to zero. House 2 had MAE around 54--56 W and substantially higher F1,
reaching 0.268 at K=1.

### Kettle

The kettle was relatively consistent across both houses. House 1 MAE was
approximately 185--197 W, while House 2 MAE was approximately 153--160
W. F1 was around 0.12 in House 1 and 0.21--0.22 in House 2. Increasing K
produced only small changes.

### Microwave

Microwave detection was weak in both houses. House 1 MAE ranged from
approximately 296--392 W and House 2 from approximately 161--174 W. F1
remained low at approximately 0.02--0.04.

### Washing Machine

The washing machine was inconsistent. House 1 MAE ranged from
approximately 184--263 W and House 2 from approximately 123--250 W.
Detection F1 remained low in both houses.

## 6. Effect of Calibration Size

Increasing calibration size did **not** produce a consistent
improvement.

For example, House 2 dishwasher F1 increased from 0.303 at K=1 to 0.354
at K=3, but decreased at larger K values. Kettle performance remained
relatively stable across K values. House 2 washing-machine MAE increased
substantially after K=3.

Therefore, more calibration sessions alone did not guarantee better
performance for the profile-matching approach.

## 7. Main Findings

1.  Pattern/profile matching can estimate appliance power, but
    performance varies substantially by appliance and household.
2.  Detection performance was limited for several appliances,
    particularly microwave and washing machine.
3.  Household variation was significant: the same appliance behaved
    differently across houses.
4.  More calibration data did not consistently improve performance.
5.  Power-estimation error and detection performance did not always
    agree. The clearest example is House 1 fridge, which had low MAE but
    almost zero F1.
6.  The experiment provides a useful baseline for the pattern-matching
    formulation, which can be compared with the other candidate
    formulations.

## 8. Limitations

The completed experiment covered **two houses**, resulting in 500 runs.
The originally planned three-house design would have produced 750 runs.

Therefore, these results should not be treated as representative of all
UK-DALE households.

The experiment also evaluates a relatively simple profile-matching
approach rather than a more advanced temporal model.

## 9. Conclusion

Experiment 2 evaluated pattern/profile matching as a candidate
formulation for appliance-level disaggregation.

The approach showed useful performance for some appliance-house
combinations, particularly House 2 dishwasher and fridge detection and
kettle estimation. However, performance varied considerably across
appliances and houses, and increasing calibration sessions did not
consistently improve results.

Overall, the experiment establishes a simple empirical baseline for the
**pattern-matching formulation** and shows why both appliance detection
and continuous power estimation need to be evaluated when comparing NILM
approaches.

## 10. Reproducibility

The experiment was run using the WattWiser pattern-matching
implementation with reproducible random draws for the
calibration-session selection.

Results are stored in:

``` text
data/results/pattern_matching/
├── pattern_matching_raw.csv
└── pattern_matching_summary.csv
```

The experiment implementation is located under:

``` text
src/experiments/03_pattern_matching/
```
