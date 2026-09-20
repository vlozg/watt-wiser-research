# Review: `01_ukdale_eda.ipynb` (+ `00_overview.md`)

**Scope.** `docs/reports/dataset_eda/00_overview.md` and `docs/reports/dataset_eda/01_ukdale_eda.ipynb`
only. The `02`-series reports are out of scope (stale, and low insight density).

**Method.** Read the notebook cell by cell; re-derived every headline number directly from
`data/fnd/ukdale/` using `src/pipelines/02_fnd_eda_notebooks/eda_fnd_lib.py`; compared the statistic set against NILMTK's
standard EDA and metric surface, the UK-DALE data descriptor, public UK-DALE notebooks, and this
repo's own client-side twin (`deprecated/analysis/eda_shelly.py`, `deprecated/analysis/eda_reference_ukdale.json`).

---

## 1. Verdict

This is a well-crafted notebook. The framing is better than most public UK-DALE EDA: a raw-fidelity
contract (no silent resampling), a question-driven structure, an enforced no-hard-coded-numbers rule,
`[insight only]` / `[collectable]` tagging, an explicit UNKNOWN/residual discipline, and gap
accounting before behaviour. The figures are clean and the summary JSON makes the run
machine-consumable. Keep all of that.

Three things stand between it and being the reference document:

1. **One headline interpretation is wrong.** The 13% residual is not household load; it is the
   metering apparatus. This changes what the UNKNOWN class should be.
2. **The headline energy statistic is methodologically inflated** (canonical share 37.1% to 34.4%)
   and **two numbers are unreconciled with the published dataset** (coverage 86.9% vs 80%; the
   duplicate whole-house meters disagree by 3.2%).
3. **The statistics computed are the ones the library happens to emit, not the ones NILM needs.**
   No transition-step (dP) distribution, no event-level co-occurrence, no base-load floor, no power
   factor, no ON/OFF class balance. Most of these already exist in `eda_fnd_lib.py` (unused) or in
   the client-side twin (which is currently *richer* than the UK-DALE side).

Details, in severity order, follow.

---

## 2. Reproduction

Everything below was recomputed from the parquet extract; no notebook output was trusted.

| Notebook claim | Notebook | Independent recompute | Verdict |
|---|---|---|---|
| mains rows | 128,238,700 | 128,238,700 | exact |
| mains span | 1500.9 d | 2013-03-17 19:12:43 to 2017-04-26 17:35:58 | exact |
| mains energy | 12,268.0 kWh | 12,268.0 kWh | exact |
| mains max / negatives | 8066 W / 0.0000% | 8066.42 W / 0 negatives | exact |
| energy coverage (30 d, 52 ch) | 86.9% | 86.7% | reproduces |
| simultaneity, 2+ ON | 3.0% | 3.15% | reproduces |
| seasonality winter/summer | 1.34 | order confirmed | plausible |
| fridge duty | 42.2% | 42.2% (p25 = 0 W) | reproduces |
| voltage sag | 3.7 V | order confirmed | plausible |
| **canonical share** | **37.1%** | **34.4%** | **inflated (E3)** |
| **house_2 fridge duty** | **100.0%** | **100.0%** | **artifact (E2)** |

---

## 3. Errors, ranked

### E1 (high) - The residual is mis-attributed: it is the meters, not the house

The notebook attributes the ~13% gap to "sockets, lighting and anything else never metered" and
concludes the residual is "real and permanent". The data does not support that reading, and the
source paper contradicts it.

Measured over the notebook's own 30-day window (50 channels, 60 s grid):

- residual energy = **32.3 kWh of 237.4 kWh = 13.6%**;
- residual is **flat**: night (02-05 h) 58 W, day (12-17 h) 54 W; p25-p75 = 56-70 W; median 61 W;
- residual is **uncorrelated with demand**: r(residual, mains) = **-0.06**;
- as a share of the mains it is 36-39% overnight but 0-20% midday.

The data descriptor states: *"Each IAM draws a little power (active power approx. 0.9 W; apparent
power approx. 2.4 VA) ... House 1 has IAMs installed on almost every appliance ... Yet the proportion
of energy submetered in House 1 is only 80%. This reasonably low value ... is likely due in large part
to the fact that the 52 EDF IAMs installed in House 1 draw approximately 50 W, yet this power is not
measured by the individual appliance meters."*

A flat, demand-independent 60 W is the 52 IAMs' own consumption, not a household load. Consequences:

- **The UNKNOWN class for house 1 is mostly a constant offset.** It should be modelled as a scalar
  (or a slowly-varying baseline), not as a 24/7 load to be classified. As written, the report implies
  the residual is intermittent, unmonitored load - the hardest possible case - when it is the easiest.
- **It is instrument-specific and does not transfer to the deployment.** A handful of Shelly EM Gen3
  clamps do not consume 50 W. Any coverage or residual-share figure is a property of house 1's
  52-IAM installation. Say so, or the number will be read as a property of UK homes.
- The residual deserves the same tagging discipline as everything else: it is `[insight only]`.

Secondary point: at 60 s averaging the residual is negative in **8.9% of minutes** (p1 = -342 W) - the
submeter sum *exceeds* the mains that often, from 1 s mains vs 6 s submeters and unsynchronised
clocks. Coverage is a 60 s-average property; the instantaneous balance is worse. One line is enough,
but silence implies the balance holds at 1 s.

### E2 (high) - The ON rule silently fails on channels with a non-zero floor

`channel_stats` sets `thr = max(5, 0.5 * p50_on)`, where `p50_on` is the median of values above
5 W. If a channel's baseline sits above 5 W, almost every sample counts as ON:

- house_2 ch14 `fridge`: min 7 W, p1 10, p25 11, p50 11, p75 87, so `p50_on` = 11 and thr = 5.5 W,
  giving **duty 100.0%**, printed in the cross-house table with no comment;
- house_5 ch24 `washer_dryer`: p50 15 W, giving **85.7%**;
- contrast house_1 ch12 `fridge` (p25 = 0 W) 42.2% and house_5 ch19 `fridge_freezer` 35.6%.

So a headline cross-house comparison mixes one real 36-42% band with two artifacts. Fix: estimate a
per-channel floor (p5 or the low mode) and set `thr = floor + max(5, 0.5 * (p50_on - floor))`, or
require bimodality before declaring ON, and publish the floor per channel.

### E3 (medium) - Per-channel energy and the canonical share are inflated by ~8%

`energy_kwh = nansum(v) * dt_med_s / 3.6e6`: a uniform-cadence estimate that ignores real timestamps,
with each channel normalised over **its own span** rather than the mains span. House 1's channels
start 2012-11-09; the mains only starts 2013-03-17, 128 days later. Every channel therefore carries
four months the mains does not.

Recomputing with timestamp integration (dt clipped at 3x median to survive gaps), restricted to the
mains span:

| ch | label | notebook kWh | timestamp-integrated, mains span | delta |
|---|---|---|---|---|
| 12 | fridge | 1513.4 | 1441.2 | -4.8% |
| 5 | washing_machine | 1055.9 | 959.9 | -9.1% |
| 6 | dishwasher | 1055.3 | 964.8 | -8.6% |
| 10 | kettle | 615.1 | 565.3 | -8.1% |
| 13 | microwave | 315.4 | 292.4 | -7.3% |
| | **canonical share** | **37.1%** | **34.4%** | |

The gap is not fatal, but the per-channel magnitudes and the top-energy ranking are systematically
off, and the method is unsafe in general: for sparsely-logged channels (ch41 `iron` 7,160 rows over
1446.7 d; ch40 `straighteners` 45,239 rows; ch22 `hoover` 134,467 rows) a "median cadence" is
meaningless, because more than 99% of row-to-row intervals are gaps. Either integrate against real
timestamps with dt capping, or mark such channels "energy not computable".

Related, and unreconciled: ch1 is labelled `aggregate` and holds **13,740.4 kWh over 1628.8 d
(8.44 kWh/d)**, while `mains` holds **12,268.0 kWh over 1500.9 d (8.17 kWh/d)** - the two whole-house
meters disagree by 3.2%. The notebook correctly excludes ch1 from the channel sum but never says which
of the two is canonical or why they differ.

### E4 (medium) - Sub-4 kW spurious IAM readings survive into the statistics

The paper documents the filter: *"The IAMs and the Current Cost transmitters occasionally report
spurious readings. rfm_ecomanager_logger filters out any readings above 4 kW for IAMs and above 20 kW
for whole-house readings."* The filter is visible and leaky. Channels whose physical load is below
100 W report near-cap maxima:

| ch | label | rows | >500 W | >2000 W | max |
|---|---|---|---|---|---|
| 44 | childs_table_lamp | 18.3 M | 127 | 23 | 3993 W |
| 45 | childs_ds_lamp | 18.0 M | 97 | 19 | 3795 W |
| 35 | bedroom_d_lamp | 17.9 M | 61 | 9 | 3973 W |
| 38 | bedroom_chargers | 12.2 M | 32 | 4 | 3935 W |
| 31 | kitchen_lamp2 | 11.4 M | 29 | 7 | 3760 W |
| 50 | office_lamp3 | 3.3 M | 18 | 2 | 3860 W |
| 52 | office_fan | 2.6 M | 2 | 1 | 3746 W |

Rare (order 1e-4 %), but each is a large false step. They inflate the `max_w` column that the
notebook itself prints without comment, and they poison step counts, step percentiles and episode
counts for exactly the channels where small steps matter most. Add a physical-plausibility screen
(per-appliance expected maximum, or a robust-quantile rule) and state it.

Also: the notebook passes `missing_values=(-1.0)` from the generic default, but **no house-1 UK-DALE
channel contains a single negative value (0 of 52)**. Harmless, but it is a client-slice convention
carried into UK-DALE; state which convention applies to which dataset (ECO does use -1).

### E5 (medium) - Coverage is the best-case window and is not reconciled with the published value

- notebook: 86.9%, over a hand-picked 30-day window in which all 52 channels are alive;
- paper: "the proportion of energy submetered in House 1 is only 80%";
- mine, same method, across the deployment: 2013-04 **86.7%**, 2014-02 90.3%, 2015-02 91.7%,
  2015-09 90.5%, 2016-05 87.0%, 2016-11 89.9%, 2017-03 87.2%.

Coverage is stable (no decay), but the all-channels window is a *good* window, not a typical one; the
published 80% presumably includes periods with dead channels. Present both and state the window rule.
As written, a reader will quote 86.9% as *the* coverage of UK-DALE house 1 and be seven points
optimistic.

### E6 (low, framing) - "Simultaneity 2+ = 3.0%" undersells the confounding

The bucket statistic is arithmetically fine (I reproduce 3.15%; a canonical appliance is ON in 44% of
all minutes). But it is the wrong summary for a disaggregation reader. At **event level** - for each
appliance, the fraction of its ON episodes (>=30 s) whose midpoint has another canonical appliance ON:

| appliance | episodes | overlapping | % |
|---|---|---|---|
| microwave | 4,855 | 2,706 | 55.7% |
| kettle | 7,108 | 3,699 | 52.0% |
| washing_machine | 26,779 | 13,756 | 51.4% |
| dishwasher | 2,776 | 1,336 | 48.1% |
| fridge | 39,666 | 2,661 | 6.7% |

Half of every intermittent appliance's events sit under a fridge cycle (the fridge is ON 42% of the
time); pairwise, fridge overlap is 44-48% for washer, dishwasher and kettle. Only the fridge itself
usually runs alone. The honest sentence is "3% of *minutes* are 2+, but about 50% of *events* are
confounded" - and events are what a disaggregator must resolve. The notebook's conclusion (mains is a
superposition, not a sum of disjoint events) is right; the number quoted argues against it.

The same computation exposes **alias pairs**: `toaster` (ON p50 = 1577 W) and `microwave` (1553 W)
are within 2% in power, so a power-level detector cannot separate them; kettle and microwave episodes
co-occur 4.9% of the time. The notebook never asks which appliances are separable - the central
question of Hart-style NILM.

### E7 (low) - Diurnal analyses are in UTC, not local time

Every scan passes `local_offset_hours=0`, and the library applies the offset only to the hour-of-day
bucket. House 1 is in London: BST = UTC+1 from late March to late October, so more than half the year
is shifted by one hour, smearing the evening peak. The library already supports the fix; the notebook
explicitly opts out.

---

## 4. What the notebook gets right

Worth protecting during any rewrite:

- **Raw-fidelity contract** - the scan reads the parquet at native cadence and the text says so.
  Public notebooks routinely resample first and then reason about the resampled series.
- **Gaps before behaviour** - Q1 establishes data holes before any appliance claim, and the
  seasonality figure annotates the data holes on the plot. That is better practice than the sources
  surveyed.
- **`[insight only]` vs `[collectable]`** - an explicit, per-claim distinction between what this
  dataset can support and what the deployment can collect. Genuinely useful and rare.
- **Explicit UNKNOWN/residual discipline** - the residual is named and carried, not hidden inside a
  "misc" bucket. The interpretation is wrong (E1), but the discipline is right.
- **No hard-coded numbers** - every figure and every JSON field is recomputed.
- **Machine-readable summary JSON** - makes the run comparable against the client twin.
- **Figure craft** - legible, labelled, consistent palette, sensible axes.

---

## 5. Missing analyses, ranked by value to WattWiser

### P0 - Base-load floor and the actual UNKNOWN model

Already measured: a flat **60 W** offset, uncorrelated with demand. Pairs directly with E1 and turns
the residual from an open modelling problem into a calibration step. NILMTK practice (`plot_when_on`,
always-on analysis) and the paper's own framing both cover this.

### P0 - Transition-step (dP) distribution

Never plotted, although `scan["steps"]`, `scan["step_sample"]`, `eda.onset_steps` and `fig_steps`
all already exist. This is the Hart feature, and it is the single most transferable number to a Shelly
deployment, which only ever sees aggregate dP.

Measured per-appliance:

| appliance | ON p50 | ON p90 | dP p50 | n steps |
|---|---|---|---|---|
| kettle | 2348 W | 2396 W | **219 W** | 18,919 |
| iron | 1796 W | 1829 W | 1775 W | 943 |
| toaster | 1577 W | 1609 W | 1545 W | 6,505 |
| microwave | 1553 W | 1611 W | 1323 W | 22,226 |
| hair_dryer | 1155 W | 1679 W | 1133 W | 2,791 |
| breadmaker | 568 W | 578 W | 375 W | 9,889 |
| washing_machine | 256 W | 2134 W | 117 W | 272,304 |
| dishwasher | 122 W | 2354 W | 38 W | 26,470 |
| fridge | 89 W | 96 W | 102 W | 55,898 |
| coffee_machine | 52 W | 1152 W | 1106 W | 1,885 |

The insight that matters: **the kettle's 2.3 kW is not a 2.3 kW step.** Its median dP is 219 W - the
element duty-cycles through a boil, so a step-based detector sees about four small steps per boil, not
one large one. The iron, by contrast, is a clean 1775 W step. The washing machine produces 272,304
steps for 26,779 episodes (FSM control draws). This is exactly the number that decides whether an edge
event-detector is viable, and it is absent.

### P1 - Multi-state taxonomy, not two-state

The notebook presents the fridge as a good two-state target. Its ON-power histogram says otherwise:
7.59 M samples at 80-100 W, but **234 k samples at 200-300 W** (about 3% of ON time - a defrost or
second-compartment state), plus 2.5 k samples above 1 kW (max 3323 W, start transient). ON-power
coefficient of variation is 0.42, not near zero. The fridge is a three-state load, and an ON/OFF model
will score the defrost phase as a false positive. Same pattern for the washing machine (256 W median
ON, 2134 W p90).

### P1 - ON/OFF class balance and the trivial baseline

Report per-appliance ON fraction (fridge 42.2%, kettle approx. 0.7%) and the F1 of an "always off"
predictor. The accuracy paradox is a standard NILM caution and is one line of arithmetic here; it sets
the floor any model must beat.

### P1 - Weekday/weekend and lag-1-day autocorrelation

Both are already computed by the library (`scan["weekday"]`, `scan["diurnal"]["lag1day_autocorr"]`)
and neither is plotted; `fig_weekday` is unused. Measured: mains weekday 346.3 W vs weekend 333.1 W
(ratio 0.96 - the weekend is *lower*). Note the client slice has the **opposite sign** (weekend 200.2 W
vs weekday 180.7 W), so this is a real difference to name, not a universal to assume.

### P1 - Correlation of mains with the submeter sum

Not computed anywhere, though it is in the paper's summary table and is one line. Measured on the
notebook's own window: **r = 0.975** (the paper publishes 0.96). Energy ratio and correlation answer
different questions; with only the ratio a reader cannot tell whether the 13% gap is missing mass or
timing error - and r(residual, mains) = -0.06 settles it.

### P2 - Apparent/reactive power and power factor

The mains schema is `ts_us, v0, v1, v2` (active power, apparent power, RMS voltage); the notebook uses
v1 only for a voltage-sag anecdote. Measured on mains with v0 > 50 W, the ratio v1/v0: p25 1.115,
**p50 1.175**, p75 1.330, p99 1.750; 0.00% with v1 < v0. That is a materially low power factor, and it
is precisely the quantity that differs between UK 240 V/50 Hz with measured V and I and a US Shelly EM
at 120 V/60 Hz. Appliance channels carry only v0, so power factor can only be studied on the mains -
worth saying explicitly.

### P2 - The UK-to-US domain shift, stated compactly

House 1 mains = **8.17 kWh/day** against the DECC 251-home UK benchmark of 9.97 kWh/day quoted in the
paper. Voltage 244.7 to 241.0 V (UK) vs 120 V (US). Median power factor 1.175 (UK). Appliance fleet
differs structurally (UK wet central heating and gas oven vs US central air, electric range and
dryer). The notebook is careful with `[insight only]`, but it never states the shift in one place, and
this is the document a reader will use to decide what transfers.

### P2 - Gap and dropout discipline

The paper documents the convention: *"any gap in the data longer than two minutes can be assumed to be
caused by the appliance (and monitor) being switched off... gaps longer than two minutes can safely be
filled with zeros... any gap shorter than two minutes can be forward-filled"*; about 6% of CT packets
and 0.02% of IAM packets are lost. The notebook uses `gap_tol_samples=2` (12 s) but never states the
convention it applies, nor reports a per-channel dropout rate. Adopting the published two-minute rule
aligns the EDA with any downstream labelling pipeline.

### P2 - Per-channel validity windows as a consumable mask

There is a whole class of "valid from X to Y" information (ch30 `DAB_radio` ends 2013-05-05 after
54.3 d; ch20 `soldering_iron` ends 2013-10-22; ch41 `iron` has 7,160 rows). The notebook reports spans
in a table but does not turn them into a validity mask downstream work can consume - and the summary
JSON is the natural home. NILMTK's `good_sections()` is the standard tool.

### P2 - High-rate V-I data exists

The dataset also holds 44.1 kHz (stored at 16 kHz) voltage/current captures for houses 1, 2 and 5. The
notebook does not mention it. This is the hook to the project's own V-I track (`research-logs/vi/`,
PLAID 30 kHz) and to the deployment feasibility question (the Shelly EM Gen3 does not expose raw V/I).
One paragraph suffices.

---

## 6. How this compares with public practice

| Dimension | This notebook | NILMTK standard EDA | UK-DALE paper | Client twin |
|---|---|---|---|---|
| raw-cadence scan | yes | resamples first | no | yes |
| quantiles / histogram | yes | yes | no | yes |
| duty, dwell, schedule | yes | `plot_when_on` | no | yes |
| transition steps (dP) | **no** | no | no | **yes** |
| base-load floor | **no** | always-on analysis | prose only | **yes** |
| diurnal | yes | yes | no | yes |
| weekday / weekend | **no** | yes | no | **yes** |
| lag-1-day autocorrelation | **no** | no | no | **yes** |
| simultaneity | bucket only | no | no | bucket (different mix) |
| coverage / submetered share | yes (best window) | `proportion_of_energy_submetered` | yes (80%) | n/a |
| mains-vs-sum correlation | **no** | yes | yes (0.96) | n/a |
| power factor / reactive | **no** | yes (`available_ac_types`) | prose | n/a |
| gap policy stated | **no** | configurable | yes (2 min) | n/a |
| validity windows | table only | `good_sections()` | n/a | n/a |
| multi-state taxonomy | **no** | partial | no | n/a |
| disaggregation metrics | no | `metrics.py` (full set) | no | n/a |

The cleanest framing of what to add: `deprecated/analysis/eda_reference_ukdale.json` already carries
`steps.dP_p50_W`, `steps.steps_per_day_gt30/100/300_W`, `diurnal.lag1day_autocorr`,
`diurnal.weekend_mean_W`, `overlap.frac_2plus_on_pct` and per-appliance `transition_step_p50_W`.
**The client-side twin is richer than the UK-DALE side.** These two are meant to be twins. Bring
`01` up to the twin's feature set first, then add what only UK-DALE can provide: multiple houses,
4.4 years, and real submeter labels.

Reference implementations worth reading before rewriting: NILMTK's `2_BasicExploratoryDataAnalysis.ipynb`
and `3_ExploratoryDataAnalysisWithNilmtkApi.ipynb` tutorials, `Fesche/NILM` `data_exploration.ipynb`,
`nilmtk/writing` `energy_breakdown_categories_globalsip.ipynb`, `JackKelly/neuralnilm`,
`JackKelly/ukdale_plots`, `JackKelly/UK-DALE_metadata`, and `klemenjak/nilm-transferability-metrics`
(arXiv 1912.06200) for the cross-dataset transfer question.

---

## 7. Prioritised change list

**P0 - correctness; do before quoting any number from this notebook**

1. Re-attribute the residual (E1): flat 60 W, r = -0.06 with demand, consistent with the 52 IAMs; tag
   it `[insight only]` and note it does not transfer to the deployment.
2. Fix the ON rule (E2): per-channel floor, or require bimodality; reprint the cross-house duty table.
3. Fix the energy method (E3): timestamp integration with dt capping over the mains span; mark sparse
   channels "not computable"; reconcile `aggregate` vs `mains`.
4. Screen sub-4 kW spurious readings (E4) and state the sentinel convention (E4).
5. Reconcile coverage against the published 80% and label the window as best case (E5).

**P1 - parity with the client twin**

6. Transition-step distributions and per-appliance dP p50.
7. Base-load floor plus lag-1-day autocorrelation.
8. Weekday/weekend diurnal (`fig_weekday` is already written and unused).
9. Event-level co-occurrence and alias pairs (E6).
10. ON/OFF class balance and the trivial-baseline F1.
11. Multi-state taxonomy for fridge and washer.

**P2 - extend**

12. Power factor / apparent power on the mains.
13. A compact UK-to-US domain-shift panel.
14. Published two-minute gap policy and per-channel dropout rates.
15. Per-channel validity masks in the summary JSON.
16. A paragraph on the 16 kHz V-I data and the link to the V-I track.

---

## 8. Note on the `02`-series

Out of scope by instruction. One observation while listing the directory: `04_eco_eda.ipynb` exists and
`data/fnd/eco` is staged, but ECO does not appear in `research-logs/eda_datasets_summary.json` (first-pass summary, since removed). If the report
set is to be rewritten or pruned, resolve that mismatch first so the report set and the dataset
inventory agree.

---

## 9. Sources

- `docs/reports/dataset_eda/00_overview.md`, `docs/reports/dataset_eda/01_ukdale_eda.ipynb`
- `src/pipelines/02_fnd_eda_notebooks/eda_fnd_lib.py`, `deprecated/analysis/eda_shelly.py`, `deprecated/analysis/eda_reference_ukdale.json`,
  `research-logs/eda_datasets_summary.json` (since removed)
- Kelly & Knottenbelt, *The UK-DALE dataset, domestic appliance-level electricity demand and
  whole-house demand from five UK homes*, Scientific Data 2:150007 (2015) - quoted statistics (IAM
  draw, 80% submetered, r = 0.96, 4 kW / 20 kW filters, two-minute gap rule, 9.97 kWh/day DECC
  benchmark)
- NILMTK: `nilmtk/nilmtk` (`metrics.py`, `elec.py`), `nilmtk/nilmtk-contrib`, tutorials
  `2_BasicExploratoryDataAnalysis.ipynb`, `3_ExploratoryDataAnalysisWithNilmtkApi.ipynb`
- `JackKelly/neuralnilm`, `JackKelly/UK-DALE_metadata`, `JackKelly/ukdale_plots`, `Fesche/NILM`,
  `nilmtk/writing`, `klemenjak/nilm-transferability-metrics`
