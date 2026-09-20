# Review: `05_greend_eda.ipynb`

**Scope.** Independent review of `docs/reports/dataset_eda/05_greend_eda.ipynb`, the GREEND pass over `data/fnd/greend/`: eight Italian and Austrian households, 2013-12 to 2015-06, per-plug readings in one wide Parquet per building, labels taken from the vendored NILMTK metadata. In this series GREEND is the span reference and the label-trust case study: labelled channels that carry no data, and channels whose data contradicts the label. Companion reviews: `03_redd_eda_peer_review.md`, `04_eco_eda_peer_review.md`, `06_ampds2_eda_peer_review.md`.

**Method.** Every headline number was recomputed from `data/fnd/greend/building0..7.parquet` with `./.venv/bin/python` (pyarrow batch scans; `src/pipelines/02_fnd_eda_notebooks/eda_fnd_lib.py` `channel_stats` so the ON-threshold rule matches the notebook exactly), plus the raw daily CSVs under `data/raw/GREEND_0-2_300615/` for column order. No notebook output was trusted. Where a claim summarises the notebook's own table, its definition is reproduced first and then exactly one thing is varied: rank order versus YAML meter-id order for label attachment; NaN share over all rows versus over a channel's own reporting window; gap count versus time-integrated missingness; an all-NaN dead-column scan versus a tiered uptime screen. The `Europe/Rome` offsets used in the clock check were validated against pandas on a 3,946-row sample (no mismatches).

---

## 1. Verdict

GREEND's shape facts are exact. Eight buildings, 196,943,999 rows, 75 plug columns, 67 labelled meters, 5 fully dead columns, the year-2000 clock rows, the 1,064-row drop and every Q6 canon number reproduce to the digit, and the DST argument is correct in substance. The defects are all in one layer: how much of the calendar the data actually covers, and which physical device sits behind which column.

1. **The 290-499 day spans are calendar spans, not coverage.** Per-building coverage of the span is **30.5 % (b7), 48.7 % (b6), 72.8 % (b3), 74.1 % (b0), 77.1 % (b5), 78.7 % (b4), 85.6 % (b1), 91.3 % (b2)**; single outages run 10.2 days (b4) to **94.4 days (b7)**, and b6 and b7 each carry three outages longer than 20 days. The building-level mean inter-row step is 1.10-3.27 s (0.31-0.91 Hz), with only 7.7-47.0 % of steps at 1.001 s or under, so Q3's “the 1 Hz claim is real on average” is true of the median only. The gap census counts events, which inverts severity: b3's 530 gaps outrank b7's 238 while b7 is missing 69.5 % of its seconds. Q8's “full-season coverage” is a calendar statement, and the ×24 h energy extrapolations in Q4 rest on an unstated representativeness assumption.
2. **The label-to-column join is asserted, never tested, and two independent screens contradict it.** (a) Physics: under the join, b5's “electric oven” channel never exceeds 58 W over 27.9 M rows and its “fridge freezer” has a 666 W median-on level and a 1,948 W maximum; b7's “dish washer” never exceeds 13 W and its “hair dryer” never exceeds 168 W; b1's “freezer” peaks at 1,876 W. (b) Aggregate identity: `building6.yaml` declares meters 1-2 as site meters (outlets, lights), so under the join b5 column 1 is the outlets meter — yet it sits below the sum of the seven monitored device channels in 85.7 % of jointly-finite rows, below a single one of them in 85.4 %, and averages 26.9 W against 134.5 W for those seven. Either the column order is not the YAML id order (the notebook's own “mapping trap ... silently mislabels an entire building”) or the metadata labels are wrong; under both readings the Q6 verdict table is unsafe for b4, b5 and b7. Raw CSV header order is stable and identical to the fnd column order (checked on two daily files per house, out of 396 and 134 files), so the join reduces to one unasked question: is CSV header order the YAML id order?
3. **The uptime prose contradicts the notebook's own sparsity table, and near-dead channels still carry verdicts.** “Live columns up to 47.5 % NaN (b3 worst)” — the notebook's own table prints worst-column 100.0 for b4, b5 and b6 and 86.9 for b7. Building 6 hides three labelled channels at 99.97 %, 98.12 % and 97.16 % NaN (television: 5,867 samples, about 1.6 h; lamp; washing machine: 484,427 samples, about 5.6 d inside a 404-day span), and b5's “fridge freezer” channel is 58.4 % NaN. The washing machine still receives a Q6 “genuinely heater-class” verdict and the Q7 onset zoom, and Q8's three dead labelled channels in building 6 should read six.
4. **The dataset-wide power record is miscredited and unscreened.** “b4 hair dryer, 7,382 W”: under the join that 7,382 W sample is on b4 column 1 = meter 1 = vacuum cleaner, while b4's hair-dryer channel peaks at 1,731 W. Column 1 is an 84.4 %-duty, 77 W-median channel whose own p99.9 is 2,292 W, so the record is an outlier 3.2× above its channel's p99.9 with 2,171 samples above 3,000 W — precisely the kind of number that needs a spike screen before it is quoted as a data-integrity fact.
5. **“All eight spans cross 2014-03-30” is false.** b7 runs 2014-04-24 to 2015-03-26 and crosses only the 2014-10-26 transition. The conclusion still holds for b7, but the proof as stated does not.

---

## 2. Reproduction

| # | Notebook claim | Independent recompute | Verdict |
|---|---|---|---|
| 1 | 8 buildings, one wide Parquet each | `building0..7.parquet`, 8 files | exact |
| 2 | 196.9 M rows | 196,943,999 (19,886,555 / 35,088,199 / 39,352,920 / 29,083,125 / 19,726,407 / 27,906,892 / 17,029,415 / 8,870,486) | exact |
| 3 | 75 plug columns, 9-11 per building | 9/9/9/9/11/10/9/9 = 75 | exact |
| 4 | 9-11 columns named by raw plug MAC | raw header order is stable day to day and identical to the fnd column order | exact |
| 5 | 67 labelled meters, 8 MAC-only | 67 labelled slots; of the 8 unlabelled columns, 4 are YAML-declared site meters (b5 ids 1-2, b7 ids 8-9), 2 are all-NaN (b4), 1 is a live 1.7 W channel (b1), 1 is a phantom (b5) | exact, mis-described |
| 6 | 8 multi-label meters | 8 | exact |
| 7 | 5 fully dead columns (b4 m10/m11, b6 m4/m6/m9) | exactly 5 all-NaN columns | exact |
| 8 | spans 290-499 days | 289.9 (b4), 310.5 (b0), 336.2 (b7), 404.4 (b6), 419.0 (b5), 462.2 (b3), 474.6 (b1), 498.9 (b2) | exact |
| 9 | 2013-12 to 2015-06 | 2013-12-06 23:55 (b0) to 2015-06-29 21:58 (b3) | exact |
| 10 | dt median 1.00-1.09 s every building | medians 1.002-1.087 s, but means 1.10-3.27 s (0.31-0.91 Hz); fraction of steps at or under 1.001 s is 7.7-47.0 % | median exact, “1 Hz on average” false |
| 11 | p1 0.54-0.88 s, p99 1.10 s (b6) to 12.8 s (b7) | p1 0.54-0.88 s, p99 1.11 s (b6) to 12.75 s (b7) | exact (b6 prints 1.10) |
| 12 | gaps over 60 s: b0 3, b6 23,671, b5 2,135, b7 238 | b0 3, b1 7, b2 76, b3 530, b4 44, b5 2,135, b6 23,671, b7 238 | exact where stated, census incomplete |
| 13 | 1,062 year-2000 rows (b4 311, b5 751) plus 2 NaN rows; filter drops 1,064 | b4 311 (2000-01-01 00:26:21-00:42:48), b5 751 (04:11:34-04:26:09), NaN-ts 1 in b4 and 1 in b7; dropped 1,064 | exact |
| 14 | b5 year-2000 run starts 04:12 | 04:11:34 | 26 s early |
| 15 | Europe/Rome hour-18 peak, 18-22 band 542 W | Rome peak hour 18, band 541.3 W, hour-18 mean 626.7 W; naive UTC peak hour 16, band 444.8 W | exact |
| 16 | all eight spans cross 2014-03-30 | 7 do; b7 crosses only 2014-10-26 | false |
| 17 | no negatives; minimum is 0.0 W in every building | no negative sample anywhere; per-building minimum 0.0 (two individual columns bottom out at 4.4 W and 21.5 W) | exact |
| 18 | live columns up to 47.5 % NaN (b3 worst), b7 worst 86.9 % | worst-column NaN 28.04 (b0), 41.70 (b1), 37.03 (b2), 47.49 (b3), 100.00 (b4), 100.00 (b5), 100.00 (b6), 86.88 (b7) | contradicts its own table |
| 19 | highest single draw: b4 hair dryer 7,382 W | 7,382 W is on b4 meter 1 (vacuum cleaner); b4's hair-dryer channel peaks at 1,731 W | miscredited |
| 20 | no mains channel exists anywhere | no whole-home channel; b5 and b7 do ship YAML-declared outlets/lights site meters among the unlabelled columns | exact, under-used |
| 21 | energy bounds 1.59 (b1) to 9.22 (b2) kWh/day | 4.01 (b0), 1.59 (b1), 9.22 (b2), 2.94 (b3), 6.32 (b4), 5.14 (b5), 8.67 (b6), 3.83 (b7) | exact |
| 22 | row-level 3.88 (b0) to 8.07 (b2) kWh/day, b2 mean 336 W | 3.88/1.41/8.07/2.25/5.55/4.02/3.13/2.59; b2 336.4 W | exact |
| 23 | washer 8/8 buildings, dishwasher 6/8, kettle 4/8, microwave 1/8, fridge 6 buildings | 8 / 6 / 4 (b0, b1, b2, b4) / 1 (b2) / 7 meters in 6 buildings | exact |
| 24 | television appears in 9 meter slots | 9 (one per building plus b6's second set) | exact |
| 25 | b0 kettle: 73 W median on, 57.8 % duty, 296 W max | 73.0 W, 57.8 %, 296 W | exact |
| 26 | b1 and b4 kettles never exceed 42 W and 48 W | 42 W, 48 W | exact |
| 27 | b2 kettle max 3,043 W at 7.0 % duty | 3,043 W, 7.0 % | exact |
| 28 | b0 washer max 13 W; b1 washer 74 eps/day; b2 microwave 194 eps/day | 13 W; 73.9; 194.0 | exact |
| 29 | b3 washer median on 1,974 W; b6 washer 1,805 W | 1,973.7 W; 1,805.4 W, but on a 97.16 %-NaN channel | exact, unguarded |
| 30 | b2 fridge: compressor cycle, 390 W median on, 37.9 % duty | 389.7 W, 37.9 % | exact |

---

## 3. What the notebook gets right

- **The clock audit is exact and correctly diagnosed.** 1,062 rows stamp 2000-01-01 (b4 311 rows over 16.5 min, b5 751 rows over 14.6 min), 2 rows carry a NaN timestamp (one each in b4 and b7), and the filter drops exactly 1,064 rows. Attributing this to a battery-free plug with no real-time clock, and explicitly ruling out a DST artifact, is the right call.
- **The NaN-as-value insight is correct and load-bearing.** Parquet statistics hide NaN in a double column, so a metadata-only read of these files shows no missingness at all; the dead columns are written as explicit NaN, not nulls. Scanning the data, not the footer, is why the dead-channel count is right.
- **The DST argument reproduces.** Rome hour-18 band 541.3 W against the notebook's 542 W, naive UTC hour-16 band 444.8 W against 445 W, offset steps validated at three transitions. The conclusion — no fixed offset is valid across a 290-499 day span — is correct, and the 2015 table entry that is a day and a half late does not change the result.
- **Q4's energy wedge is the honest framing.** Own-mean upper bounds 1.59-9.22 kWh/day against row-level 1.41-8.07 kWh/day, with b2's 336.4 W whole-row mean, all reproduce, and the statement that the row-level figure is a lower bound because a silent plug contributes zero is exactly the right caveat.
- **The label inventory is exact and useful.** Canonical counts, the 8 multi-label meters, the 3 dead labelled channels in building 6, and the observation that television occupies 9 slots while microwave occupies 1 are all correct, and the “kettle-class labels that never boil” forensics (42 W, 48 W, 3,043 W, 73 W) is the single most transferable finding in the notebook.
- **“No mains, so pseudo-mains is a lower bound” is right**, and it is the correct reason a dataset is best used here for span, cadence realism and label-trust testing rather than for whole-home share supervision. The follow-on point that our wired panel meters do not have this wireless tail is supported by the measurements above.

---

## 4. Errors, ranked

### R1 (high) - the spans are calendar spans and the coverage is 30.5-91.3 %
The claim: “290-499 days per building”, “the longest continuous spans in our suite”, and Q8's “full-season coverage”. Measured, per building, as rows divided by span seconds:

| Building | Span (d) | Rows | Coverage | Rows/day | Mean step (s) | Steps <= 1.001 s | Longest outages (d) |
|---|---|---|---|---|---|---|---|
| b0 | 310.5 | 19,886,555 | 74.1 % | 64,040 | 1.349 | 23.5 % | 48.6, 21.7 |
| b1 | 474.6 | 35,088,199 | 85.6 % | 73,935 | 1.169 | 8.5 % | 2.4 |
| b2 | 498.9 | 39,352,920 | 91.3 % | 78,886 | 1.095 | 15.4 % | 1.0 |
| b3 | 462.2 | 29,083,125 | 72.8 % | 62,921 | 1.373 | 7.7 % | 26.1, 13.6, 11.7 |
| b4 | 289.9 | 19,726,407 | 78.7 % | 68,036 | 1.270 | 9.7 % | 13.7, 10.2 |
| b5 | 419.0 | 27,906,892 | 77.1 % | 66,608 | 1.297 | 33.0 % | 15.1 |
| b6 | 404.4 | 17,029,415 | 48.7 % | 42,114 | 2.052 | 47.0 % | 68.8, 61.5, 20.9 |
| b7 | 336.2 | 8,870,485 | 30.5 % | 26,383 | 3.275 | 44.1 % | 94.4, 61.9, 26.9 |

Consequences that follow: (a) “full-season coverage” must be restated as calendar reach with a coverage column, or the longest *continuous* stretch quoted instead (b2's is ~1 year, b7's longest run between outages is about 100 days); (b) cross-building comparisons of energy, episodes or duty inherit a three-fold sampling difference that the per-row mean does not correct for; (c) the Q3 prescription that any energy integral needs a dt cap is right, but the Q4 energy columns are rate extrapolations (mean power × 24 h) that never apply that cap or state what the missing seconds are assumed to be doing.

### R2 (high) - the meter-to-column join is an untested positional assumption
The gold layer keys labels by YAML meter id; the notebook attaches them by column position. The pipeline documents this as an assumption (“meter k = k-th MAC column”), and the notebook itself warns that a mapping trap “silently mislabels an entire building”, but no cell tests it. Two screens test it here and both fail:

- **Physics, under the join:** b5 meter 6 “electric oven” max 58 W (27.5 M samples); b5 meter 5 “fridge freezer” median-on 666.0 W, max 1,948 W, 54.3 % duty — a fridge signature that a compressor cannot produce; b5 meter 3 “television” median-on 778.8 W; b5 meter 4 “television plus set-top” median-on 1,306.9 W; b7 meter 1 “hair dryer” max 168 W at 98.4 % duty; b7 meter 7 “dish washer” max 13 W at 99.6 % duty; b1 meter 2 “freezer” max 1,876 W. Meanwhile b5's oven-shaped channel (median-on 1,306.9 W, 4.9 % duty, max 1,660 W) and b5's compressor-shaped channel (63.6 W, 54.3 % duty) sit under other labels.
- **Aggregate identity:** `building6.yaml` (House#5, our b5) declares meters 1-2 as site meters (outlets, lights) and `building8.yaml` (House#7, our b7) declares meters 8-9 as site meters. Under the join, b5 column 1 is therefore the outlets meter; measured over 3,068,409 jointly-finite rows it is greater than or equal to the sum of the seven device channels in only 14.3 % of rows, is below the largest single device channel in 85.4 %, and averages 26.9 W against those seven channels' 134.5 W. For b7 the same test on column 8 (3.07 M rows finite, because the column is 86.9 % NaN) gives 18.1 % and 63.4 %.

Either the column order is not the YAML id order, or the metadata's per-device labels for these houses are wrong. Both are blocking for per-channel claims. Note that the raw CSV header order is stable across the sampled daily files and matches the fnd column order exactly, so the only open question is whether that order is the YAML id order — a one-line check against the paper's device table, and it is not made.

### R3 (high) - the live/dead boundary is unstated, and verdicts ignore data volume
The prose does say live columns run “up to 47.5 % NaN (b3 worst)” and that five columns are fully dead, alongside a sparsity cell printing `colnan.max()/n` per building, i.e. 100.0 for b4, b5 and b6 and 86.9 for b7, so the summary and the table agree. What is never stated is the boundary the two sentences rely on: a column with a handful of samples counts as live. The near-dead cases that matter are labelled channels: b6 meter 1 television 99.97 % NaN (5,867 samples, 1.6 h of a 404-day span), b6 meter 2 lamp 98.12 %, b6 meter 8 washing machine 97.16 % (484,427 samples, 5.6 d); b5 meter 5 fridge freezer 58.4 %; b7 column 8 86.9 %. The washing machine is then given a Q6 “genuinely heater-class” verdict and the Q7 onset zoom, and Q8's supervision-hole taxonomy counts 3 dead labelled channels in building 6 where a data-volume gate would count 6. A verdict computed from 5.6 days of a 404-day span is not a verdict about that appliance.

### R4 (medium) - the 7,382 W record is on the wrong channel and never screened
Q1's integrity headline credits b4's hair dryer. Under the join the sample is on b4 column 1 = meter 1 = vacuum cleaner; b4's hair-dryer channel peaks at 1,731 W. The channel carrying it runs at 77 W median-on for 84.4 % of the time, has p99.9 = 2,292 W, and exceeds 3,000 W in 2,171 of 19.4 M samples: a bimodal channel with a rare high tail. Quoting the maximum as a dataset-integrity fact without a spike or saturation screen (and without the correct label) is the weakest number in the notebook.

### R5 (medium) - “all eight spans cross 2014-03-30” is false
b7 starts 2014-04-24 and ends 2015-03-26, so it crosses only 2014-10-26. The DST conclusion survives (b7 still contains a validated transition), but the stated evidence does not; the check should be per-building rather than “all eight”.

### R6 (low) - three small arithmetic and completeness slips
(a) The gap census names only four buildings; b3 has 530 gaps over 60 s and b2 has 76, and b3 is also the worst-NaN building, so omitting it hides the second-least trustworthy house. (b) b5's year-2000 run starts 04:11:34, not the printed 04:12. (c) b6's p99 step is 1.11 s, printed as 1.10 s.

### R7 (low) - live/dead is binary, and the boundary case is real
The dead-column scan is exact only because it tests all-NaN. b5's tenth column (MAC 3A5F99) carries exactly 1 sample in 27,906,892 rows — visible in the header of every daily file, invisible to the dead scan, and printing as 100.00 % NaN in the sparsity table. b6's television channel at 5,867 samples is the same species one order of magnitude up. The notebook should publish a tiered screen (say: dead = zero samples, unusable = under 1 % of the building's rows, thin = under 50 %) rather than a binary.

---

## 5. Missing analyses, ranked by value

### P0 - resolve the meter-to-column join before any per-channel verdict
Three checks, in order: (1) compare the raw CSV header order with the paper's device table for each house (the metadata README already tells us the site meters sit at ids 1-2 in House#5 and ids 8-9 in House#7, so the two orderings are distinguishable); (2) re-run the label-physics screen under both the id-order and the rank-order join and report which channels flip; (3) publish the resolved mapping in the gold layer as a per-house column-to-MAC table, so downstream notebooks cannot re-guess it. Until this lands, Q6's verdict table should carry an explicit “label provenance unverified” flag on b4, b5 and b7.

### P0 - a tiered uptime screen that gates every claim
Per channel and per building: rows, active days, NaN share over the channel's own window and over the building span, longest gap, and samples above the ON threshold. Then gate: no appliance verdict unless the channel is finite for at least, say, 20 active days and 25 % of the building's rows. This converts R3 from a prose fix into a rule, and it is the table a training plan needs anyway — which labels are actually available, per house, for how much time.

### P0/P1 - extend the physics verdict to all 67 labelled meters
Q6 examines roughly 15 channels of 67. The same signature screen (median-on level, duty, episode rate, maximum, duty of the maximum) applied to all 67 would surface the b5 oven and fridge contradictions, b7's dishwasher and hair dryer, and b1's freezer automatically, and would leave a reusable per-label verdict table rather than four anecdotes.

### P1 - read the site-meter columns the metadata declares
Q1 correctly notes the unlabelled “aggregate” columns but never opens them. For b5 (outlets and lights at ids 1-2) and b7 (ids 8-9) these are measured circuit aggregates, not plug sums: they can validate the pseudo-mains lower bound rather than leaving it a construction, and they are the only place in GREEND where a measured (if partial) mains-like quantity exists. The aggregate-identity test in R2 is the first step; a correlation of the outlets channel against the plug sum, with the dominance fraction, is the second.

### P1 - coverage-aware energy intervals
Replace the two-number wedge with three: own-mean × 24 h (upper), row-level mean × 24 h (current lower), and a dt-capped, coverage-weighted integral with the observed-seconds fraction stated. For b7 the three differ by a factor near three, and the choice should be visible rather than implicit.

### P1 - a spike and saturation screen for channel maxima
Before any maximum is quoted: count of samples above the channel's p99.9, longest run above it, and whether the values look quantised or saturated. b4's column 1 (2,171 samples above 3,000 W) and b2's two spike-dominated channels (means 5.7 W and 6.1 W with 1.9-2.1 kW maxima) both need it.

### P2 - a per-plug cadence and onset audit
Q3 characterises the grid; Q7 claims about 1 s onset resolution from one morning window. A per-channel table (median step, mean step, share of steps at 1 s) plus an onset timing check against the raw daily files would settle whether the reported jitter is network or clock drift, and would give event-detection work a defensible resolution limit per house.

### P2 - a seasonality study that states its coverage
The 290-499 day spans invite a monthly or seasonal split (Q7 defers it). With coverage of 30-91 % and multi-month outages concentrated in winter and spring for b6 and b7, any seasonal statement must be conditioned on which months are present; a month-by-building coverage heatmap is the minimum companion.

---

## 6. How this compares with public practice

- Published GREEND usage typically trusts the vendored NILMTK labels and reports the nominal 1 s rate and the span, exactly as this notebook does. Disclosing per-house coverage and running a label-physics screen is *above* typical practice, which is why the two defects here (an untested positional join and a coverage figure carried only in a table) are the sort that a converter bug can hide behind for years.
- The 2014 GREEND paper documents the houses and their metering, and NILMTK's conversion conventions (including the site-meter concept) are the source of the YAML we ship. A MAC-level reconciliation against that table is the standard converter-maintenance step; treating the pipeline's own assumption as the ground truth is not.
- Label-quality literature and the NILM Metadata effort both treat canonical labels as curated annotations with provenance, not as facts. This notebook's Q6 verdict table is a good first instance of provenance checking; it needs the volume gate (R3) and the full-coverage sweep (P0) to be usable as a gold-layer convention.

---

## 7. Suggested order of work

1. Resolve the join (P0) and publish a per-house column-to-MAC map. Everything per-channel depends on it.
2. Publish the tiered uptime screen (P0) and apply the volume gate to Q6 and Q7.
3. Correct the four prose/number defects: coverage versus span (R1), the live/dead boundary (R3), the 7,382 W attribution (R4), the DST span claim (R5).
4. Extend the physics screen to all 67 labels (P0/P1) and record the verdicts in the gold layer.
5. Read the site-meter columns (P1) and upgrade the energy wedge to a coverage-aware interval (P1).
6. Add the cadence/onset audit (P2) and the coverage-conditioned seasonality study (P2).

---

## 8. Sources

- Notebook under review: `docs/reports/dataset_eda/05_greend_eda.ipynb`; builder self-review: `docs/reports/dataset_eda/05_greend_eda_review.md`.
- Data: `data/fnd/greend/building0..7.parquet`; raw daily CSVs under `data/raw/GREEND_0-2_300615/GREEND_0-2_300615/`.
- Pipeline contract: `src/pipelines/01_extract_dataset/extract_greend.py`; vendored metadata and notes in `src/pipelines/01_extract_dataset/metadata/greend/` (`building1..8.yaml`, `README.md`).
- Shared definitions: `src/pipelines/02_fnd_eda_notebooks/eda_fnd_lib.py` (`channel_stats`, `kwh_of`, `onset_steps`).
- Cross-references: `docs/reports/dataset_eda/00_overview.md` (repeat of the REDD 4 s cadence wording at line 15; the 383 W versus 134 W occupied/away figures at line 120 do not match ECO's house-1 summer pair of 261 W and 127 W), `03_redd_eda_peer_review.md` (the ON-threshold rule that GREEND's `channel_stats` also uses), `04_eco_eda_peer_review.md` (the same positional-label risk in miniature).
- Public work referenced: Monacchi, Egarter, Elmenreich, D'Alessandro and Tonello, *GREEND: An energy consumption dataset of households in Italy and Austria*, IEEE SmartGridComm 2014 (arXiv:1405.3100); Batra, Kelly, Singh, Knottenbelt et al., *NILMTK: An open source toolkit for non-intrusive load monitoring*, e-Energy 2014; Kelly and Knottenbelt, *Metadata for the NILM datasets*, 2015; Pereira and Nunes, *Performance evaluation of NILM methods: a review*, 2019.

---

## 9. External cross-check

Checked against primary sources rather than other notebooks: the GREEND paper (Monacchi, Egarter, Elmenreich, D'Alessandro, Tonello, IEEE SmartGridComm 2014, arXiv:1405.3100, full text), the reference converter and vendored metadata in NILMTK (`dataset_converters/greend/convert_greend.py`, `metadata/building1..8.yaml`), the release's own non-CSV files, and the raw daily CSVs. Third-party EDA artifacts were also sampled in a signed-in browser session (closing note).

**Confirms**

- **Cadence is a published spec, not a unit guess.** Paper Table 1: GREEND Austria and Italy, "1 year (3-6 months completed)", 9 households, 9 sensors, power only, **1 Hz**. Section 3.3: a Plugwise Basic kit, "a Zigbee network of 9 sensing outlets", collecting "in epochs", with nodes skipped when packets are missed. The delivered 0.31-0.91 Hz mean rate and 30.5-91.3 % row coverage of R1 is therefore a spec-versus-delivery gap, and the paper supplies the mechanism (skipped epochs on packet failure) rather than a clock fault.
- **Site meters do exist, so Q1's summary is wrong twice over.** Paper Table 2 lists Houses 5, 7 and 8 with "Total outlets, total lights" (House 5: the first two entries; Houses 7 and 8: the last two), which is exactly the `site_meter` declaration in `building6.yaml` (meters 1-2) and `building8.yaml` (meters 8-9). Q1's "No mains channel exists anywhere" is refuted by the paper *and* by the notebook's own Q1 body, which already allows that houses 5, 7 and 8 shipped unlabelled total-outlets and total-lights columns.
- **R5 stands, from the deployment schedule.** Paper Section 3.1: "the last two platforms (house #7 and #8) were deployed in April"; `building7.parquet` starts 2014-04-24, so "all eight spans also cross the 2014-03-30 European DST switch" is false for b7.
- **The join is a toolkit convention, not a validation.** `convert_greend.py` enumerates the wide table's columns and keys meters by position (`for column in overall_df.columns: ... Key(building=h, meter=m)`, with h one higher than our building index) and never reads the plug MAC. The notebook's "meter k corresponds to the k-th MAC column in column order" is inherited from NILMTK, and from our own extractor, which is what makes R2 a blocking untested assumption rather than a notebook slip.
- **Label provenance, with exactly one exception.** The paper's Table 2 device order matches `metadata/greend/building1..8.yaml` for Houses 0, 1, 2, 3, 5, 6 and 7. House 4 is the exception: the paper's first position reads **"Entrance outlet"** where `building5.yaml` says "vacuum cleaner" (positions 2-9 match). Physics agrees with the paper rather than our YAML: that column runs at 77 W median-on for 84.4 % of hours, an always-on outlet circuit, not a vacuum cleaner. R4's attribution error is confirmed from the primary source, and the label is wrong in our metadata regardless of how the join resolves.

**New**

- **Co-reporting cardinality is building- and era-dependent, and it re-scopes what a NaN means.** Raw b6 daily rows carry one or two non-NULL values in the 2014-02 file (35.1 % / 64.9 %) against 5-9 in b0 and 8-9 in b7, and the staged table inherits that shape: `building6.parquet` has **no row with more than five finite plug columns** (95.9 % exactly three, 1.0 % with none), b7 spreads over four to nine (38.2 % at five, 33.8 % at eight), and b0-b5 sit at seven to nine. Two consequences: per-column NaN fractions still measure per-plug uptime, but no *row-level* claim does, because a NaN cell can mean "this epoch did not poll that plug"; and a row-sum pseudo-mains is only meaningful for the dense buildings. Q4's per-column reading survives; framing the grid as "all plugs, NaN where silent" does not.
- **Release-supplied time-offset metadata is unread.** `building0/date.txt`, the only non-CSV, non-`DS_Store` file in the eight building trees, carries a `time-offset` section: `till 2014_4_29 -> 980282` and `from 2014_6_17 -> 1026458`. Those two dates are exactly the boundaries of b0's two largest gaps (48.6 d and 21.7 d in the reproduction table). Neither `extract_greend.py` nor any notebook cell reads it, so b0's biggest outage is quoted as physical absence while the release's own note on that interval is ignored; the file should be decoded and cited until its unit is settled.

**Self-correction.** R3's original headline claimed the uptime prose contradicted the notebook's own table. It does not: the summary line names both the 47.5 % worst-NaN figure and the five fully dead columns. R3 has been reworded to the surviving defect, an unstated live/dead threshold that lets b6 meter 1 (5,867 samples, 1.6 h of a 404-day span) count as live and collect a Q6 verdict and the Q7 zoom.

**Public artifacts checked (signed-in browser session).** The Kaggle mirror of the release independently describes it: "active power (Watts) at 1 Hz", **eight households** (four in the province of Udine, four around Klagenfurt), and daily CSVs whose header names each Zigbee node MAC — matching the raw layout in `data/raw/` and confirming both the 1 Hz spec and the eight-directory count from a second source, with the paper's ninth platform absent from the public snapshot. That mirror carries **no notebooks at all**, and a Kaggle notebook search for energy disaggregation returns thirteen results, none about GREEND. GitHub holds two GREEND repositories, both from 2016 and both thin wrappers around NILMTK's converter, and no issue thread on the meter-to-column mapping. So the join that R2 shows is untested is also unremarked publicly: the only public artifact encoding it is the NILMTK converter, and it encodes it by column position.