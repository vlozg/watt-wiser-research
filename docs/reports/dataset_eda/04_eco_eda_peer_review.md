# Review: `04_eco_eda.ipynb`

**Scope.** Independent review of `docs/reports/dataset_eda/04_eco_eda.ipynb`, the ECO (Swiss, 2012) pass over `data/fnd/eco/`: six apartments, five with a complete 17-column smart-meter panel, 49 plug meters, ten seasonal occupancy windows. This is the series reference for a *measured* panel-vs-plug relation, 1 Hz clock conventions and occupancy-labelled load. Companion: `03_redd_eda_peer_review.md` (REDD), `06_ampds2_eda_peer_review.md` (integrity benchmark).

**Method.** Every headline number was recomputed from `data/fnd/eco/*.parquet` with `./.venv/bin/python` (pandas, pyarrow; `analysis/eda_fnd_lib.py` for `channel_stats` and `kwh_of` so the definitions match the notebook's exactly). No notebook output was trusted. Where the claim under test is the notebook's own printed table, I first reproduce its definitions, then vary them one at a time (e.g. span-based coverage vs sample-based coverage; plug sum with and without a nested group).

---

## 1. Verdict

ECO's *measurement* layer is the strongest in this series. The clock audit, the phase-identity validation, the 10 W quantisation trap and the common-window attribution method all survive independent recomputation to the digit, and the notebook is honest where it is weak (“plug instrumentation ... captures 95% of panel energy in house 2 ... but only 8% in house 3”). The defects are one layer up: how per-plug energy is *aggregated* and how ranges are *summarised*.

1. **House 2's 95% plug attribution is a double count.** The `Entertainment` plug (302.7 kWh) is a group meter for `TV` + `Stereo` (215.5 + 94.5 kWh): over 20.39 M overlapping 1 Hz seconds the three series satisfy `entertainment = tv + stereo` with correlation 0.991, mean absolute difference 0.90 W, and 99.4% of samples within 1 W. Q7 sums all three, so house 2's figure is **70.2%**, not 94.8%. This is the notebook's headline (“the near-complete one”) and the number the TL;DR carries.
2. **The recommended kettle signature contradicts the notebook's own table.** Q8 asks the gold layer to store a kettle prior of “consistent 1.0-1.4 kW / 60-180 s”. Q5, two cells earlier, prints 1.8-2.0 kW from the same mask, and the data agree with Q5: median ON power 1,765 W (house 1), 1,838 W (house 2), 2,025 W (house 6). Q8 is the transferable table; it is wrong by ~40% on the flagship appliance.
3. **The occupancy window range mixes days and per cent.** “39-94 days of 1 Hz labels each” (TL;DR and Q6) is not a day range. The day counts the notebook itself computes are 39, 46, 83, 45, 57, **21**, 38, 48, 43, **31** — a **21-83 day** range (calendar span 32-95 days); 39 is house 1 summer's day count and 94 is house 4 winter's *occupancy fraction* (94.3%), recycled as a day count. The occupancy range 71-94% is correct.
4. **Coverage is reported on one axis only.** The Q5 `%of_sm` column is a span ratio, so it hides internal sample dropout: house 1's kettle spans 97% of its panel window but holds 86% of the 1 Hz seconds inside it (house 1's plugs: 84-98%), house 3's plugs span 36-53% and hold **38%** (PC 38%, fridge 47%, kettle 51%), and house 6's lamp holds 76%. House 5 is the only genuinely complete plug set (7 of 8 at 100%). With one axis, “fridge 6/6, kettle 5/6” reads as supervision counts; per-plug screening (below) shows several instances are chatter channels.
5. **A cross-document inconsistency.** Q3 contrasts ECO's peak demand with “REDD's 24 kW split-phase ceiling”. `03_redd_eda.ipynb` measures the REDD panel maximum at 12,333 W (my recompute: `max(m1+m2)` = 12,333 W; sum of leg maxima 12,628 W). 24 kW is a US service *rating* (240 V x 100 A), not REDD's data, and comparing a measured 7.1-11.1 kW against it flatters ECO.

## 2. Reproduction

| Notebook claim | Notebook | Independent recompute | Verdict |
| --- | --- | --- | --- |
| Six apartments, 17-column `sm`, house 4 panel empty | 0 rows | 6 houses, 17 columns each; house 4 `sm` = 0 rows | ok |
| 49 plug meters (7/12/7/8/8/7) | table | 49 plug files, same per-house counts | ok |
| Occupancy labels 10 of 12 windows; house 6 none | 10 | 10 windows (houses 1-5 x 2 seasons); house 6 has none | ok |
| House 1: 245 d continuous, zero gaps, dt = 1 s | table | 21,168,000 rows, 245.0 d, 100.0% coverage, `dt` set = {1,000,000 µs} | ok |
| Houses 2/3/5/6: exactly one outage each (1/52/4/53 d) | table | one gap > 60 s per house: 1.00/52.00/4.00/53.00 d; zero micro-gaps | ok |
| Phase identity: p99 <= 2 W, mean <= 0.03 W | table | p99 |residual| 0.01/2.00/2.00/0.01/0.01 W; mean 0.0073/0.0283/0.0222/0.0191/0.0065 W | ok |
| Negative noise floor down to -7.9 W | table | house 2 min -7.9 W; others -1.0 W | ok |
| Peak demand 7.1-11.1 kW | table | 7,112 / 9,064 / 7,961 / 10,591 / 11,094 W (h2/h1/h6/h3/h5) | ok |
| Diurnal peak 20:00-23:00 at offset 0; house 6 at 07:00 | table | argmax hour 22 / 20 / 22 / 23 / 07 | ok |
| House 1: 10 W-quantised until 2012-06-29 13:10:36 (28.5 d, 11.6%) | table | first off-grid sample at index 2,466,636 = 2012-06-29 13:10:36; 28.55 d = 11.65%; before 100.00% multiples of 10 (565 distinct values), after 0.18% (1,026,776 distinct) | ok |
| Other houses are fine-grained from sample 0 | table | first off-grid index 0 in houses 2, 3, 5, 6 | ok |
| House 2 `currentneutral` all zero | table | max 0.0; other houses 23.8-27.1 A | ok |
| No NaNs, no sentinels, no exact zeros in `powerallphases` | prose | 0 zeros and 0 NaNs in all five panels (true, but no cell computes it) | ok (unverified in-notebook) |
| Kettle median ON 1.8-2.0 kW, ~1-2 eps/day, ~0.3% duty | Q5 | 1,764.7 W / 1.8 eps/d / 0.26% (h1); 1,838.0 / 1.3 / 0.27% (h2); 2,025.0 / 0.5 / 0.13% (h6) | ok |
| Houses 3 and 5 kettle read a 17 W / 9 W median | Q5 | 17.1 W (h3), 8.7 W (h5) | ok |
| House 5 kettle logged just 25 September days | Q5 | 2012-09-06 to 2012-09-30 = 25.0 d | ok |
| Plug/panel energy: h1 33%, h2 95%, h3 8%, h5 16%, h6 29% | Q7 | 33.0% / **70.2%** (94.8% before removing the nested group) / 7.9% / 15.7% / 28.9% | h2 wrong |
| House 1 leads with washer 131, dryer 125, fridge 115, freezer 101 kWh | Q7 | 130.9 / 125.0 / 114.7 / 101.0 kWh over the 237 d window | ok |
| Occupancy windows 39-94 days each, 71-94% occupied | Q6 | **21-83 d** by 1 Hz rows (house 3 winter 21 d, house 5 winter 31 d, house 4 summer 38 d); 32-95 d by calendar span; 71.2-94.3% occupied | range wrong |
| Kettle “consistent 1.0-1.4 kW / 60-180 s” | Q8.3 | 1,765 / 1,838 / 2,025 W; dwell medians 103 / 168 / 217 s | power wrong |
| House 4 `%of_sm` column | 999% | raw value 2.1e13% (panel span 0, then clamped) | artefact |
| REDD 24 kW split-phase ceiling | Q3 | REDD panel max 12,333 W (REDD review) | wrong |

## 3. What the notebook gets right

- **The clock audit is exemplary.** House 1 holds 21,168,000 samples with every inter-sample `dt` exactly 1,000,000 µs, and the series starts on a sharp local midnight. The DST fall-back day (2012-10-28) does have 86,400 rows. My recompute confirms the conclusion (naive local wall clock, offset 0) and the supporting evidence (evening peak at 20:00-23:00, house 6 at 07:00).
- **The 10 W quantisation trap is a genuine discovery.** The boundary at 2012-06-29 13:10:36 is exact, 28.55 days long (11.65% of the panel series), and the before/after contrast is stark: 565 distinct values then vs 1,026,776 now. Any model trained on house 1 without trimming the first month sees a 10 W-quantised aggregate.
- **The phase identity is a free ingestion validator**, and the notebook frames it that way. p99 residual <= 2 W, mean <= 0.03 W, house 2's neutral channel flat at zero, min -7.9 W. This is exactly the check our own Shelly stack should assert on every upload.
- **The common-window lower-bound method is the right answer** to “is ECO fully supervised?”: intersect spans, integrate only present samples, report a lower bound — and it is applied consistently in Q7 with `kwh_of(..., dt_cap_s=2.0)`, which correctly refuses to extrapolate across a multi-day hole.
- **The occupancy join is done correctly**: `searchsorted` against the label series, with the match rate printed (house 1 summer: 3,369,600 of 3,628,800 panel seconds = 92.9%), instead of the positional join that would silently mis-align 7% of the hours.
- **Several small claims reproduce exactly**: the house 5 kettle's 25 September days, the house 3/5 kettle anomalies (17.1 W / 8.7 W), house 2's all-zero neutral, the 7.1-11.1 kW peak range, the 71-94% occupancy range, and the honest “partially, and very unevenly” framing of plug coverage.
- **The REDD contrast is drawn from a real structural difference** (24 W split-phase legs vs a three-phase 400 V service), even though the 24 kW figure itself is a nameplate.

## 4. Errors, ranked

### R1 (high) - House 2's plug share double counts a nested group

Q7 sums every plug file under a house. House 2 ships `Entertainment` (05), `TV` (11) and `Stereo` (12), and the first is the parent of the other two. Over the 20,390,400 seconds where all three are present: mean 53.4 W vs 54.3 W for `tv + stereo`, mean absolute difference 0.90 W, correlation 0.9911, 99.4% of samples within 1 W, and 302.7 kWh vs 310.0 kWh of energy. The notebook's sum therefore counts the entertainment group roughly twice, adding ~303 kWh to a 1,167.7 kWh total against a 1,232.1 kWh panel.

Consequences: the corrected figure is **865.0 kWh = 70.2%** (69.6% if the parent is kept and the children dropped), so the summary line “plug instrumentation captures 95% ... in house 2” overstates the one house that anchors the whole “partially supervised” claim, and the TL;DR ordering (95% vs 8-33% elsewhere) understates the gap between house 2 and the rest by a factor of ~2.7 in the *difference*.

House 1 is clean (washer and dryer are two distinct appliances, and their channels are uncorrelated — washer 130.9 kWh at median ON 34 W, dryer 125.0 kWh at 788 W). House 4's `Kitchen appliances` (43.7 kWh) is not a superset of its fridge/freezer pair. So the defect is specific but material.

Fix: add a nesting detector — for every house, test each plug against the sum of the others (and against small candidate subsets) and record a `submeter_of` relation on the offending edge; then compute the share on a de-duplicated set.

### R2 (high) - The kettle prior in Q8 contradicts Q5 and the data

Q8 item 3 asks the gold layer to treat ECO as “the best cross-household kettle-and-cold-chain reference we have” on the strength of “consistent 1.0-1.4 kW / 60-180 s signatures”. The same notebook's Q5 prose and table say 1.8-2.0 kW, and the recompute puts the three healthy kettle medians at 1,765 / 1,838 / 2,025 W with 0.13-0.27% duty and 0.5-1.8 episodes/day. The dwell band is roughly right (medians 103 / 168 / 217 s). A 1.0-1.4 kW kettle prior would mis-scale exactly the appliance class this dataset is best at.

Fix: state the number once, in the table, and reference it from Q8 instead of retyping it.

### R3 (medium) - “39-94 days” conflates a day count with an occupancy percentage

Q6 computes the window length as `len(occupancy_ts)/86400`, i.e. 1 Hz rows, and prints 39/46/83/45/57/21/38/48/43/31 days for the ten windows. The prose's lower bound (39) is house 1 summer and its upper bound (94) is house 4 winter's *occupied fraction*, so the sentence “39-94 days each, 71-94% occupied” silently reuses 94 in two units. The true ranges are **21-83 days of 1 Hz labels** and 32-95 days of calendar span; house 3's winter window is 21 days, which is materially less training data than the prose implies.

Fix: quote the printed range (21-83 d) and keep the percentage sentence separate; if calendar span is meant, print it as a second column rather than dividing rows by 86,400.

### R4 (medium) - Coverage is a span ratio, so internal dropout is invisible

The Q5 column is `100 * span_d / sm_span` with `min(cov, 999)`. Recomputing 1 Hz coverage *inside* the span for all 49 plugs: house 1 sits at 84-98% (kettle 86%, PC 84%, coffee machine 86%), house 2 at 96-98% (stove 57%), house 3 at **38-96%** (PC 38%, fridge 47%, kettle 51%, entertainment 55%), house 6 at 76-100% (lamp 76%), and house 5 at 99.5-100%. The span ratio reports 97%/100% for channels that are missing 2-16% of their seconds, and it makes house 3 look like a coverage problem in *time* when it is also one in *samples*.

This matters because the notebook's own `03` sibling reports both axes for REDD, and because `kwh_of(dt_cap_s=2.0)` is justified precisely by that dropout — the justification should be visible in the table.

Fix: add a `int_cov` column = rows / (span x 1 Hz) next to the span ratio.

### R5 (medium) - No per-plug trust screen, so canonical coverage counts overstate usable supervision

The gold map's canonical counts (fridge 6/6, kettle 5/6, freezer 5/6, microwave 2/6, coffee machine 4/6, entertainment 5/6) are label counts. A one-pass screen over the same 49 plugs finds: house 5 tablet 6,501 episodes/day at 6.5 W median ON, house 5 microwave 2,975 eps/day at 6.6 W (against house 4's microphone-verified microwave at 1,371 W and 16 eps/day — same canonical, wildly different channel), house 6 laptop 2,200 eps/day, house 6 coffee machine 226 eps/day, house 1 washing machine 177 eps/day at 34 W median ON while carrying 131 kWh of real energy, house 1 PC 85% duty, house 5 PC 98% duty, house 6 router 97%, house 5 fountain 99%.

The energy integrals are still right (they integrate every sample); what is not right is treating those channels as ON/OFF supervision. The notebook flags the two dead kettles and asks for “the per-plug duty flag as the trust gate”, but never builds it, and `03` already contains the machinery (legacy vs floor threshold comparison) that would show house 5's microwave for what it is.

Fix: add `p50_on_w`, `duty`, `eps_per_day` and `int_cov` as trust columns in the Q5 matrix and mark instances failing a duty/eps band, then report canonical coverage twice (labelled / usable).

### R6 (medium-low) - The DST row-count argument does not discriminate

Q2 offers “the 2012-10-28 fall-back day has exactly 86,400 rows (a UTC grid would need 90,000)” as proof of the naive-local convention. The count is a property of the stored 1 s grid, not of the convention: under a true-UTC export the stored day bins still hold 86,400 samples each, and only the *local* rendering of that day is 90,000 s long. The argument therefore cannot separate the two hypotheses, and it duplicates what the “all `dt` = 1 s” test already shows (the grid never jumps or repeats).

The discriminating evidence is what the notebook also has: the series begins exactly at local midnight (2012-06-01 00:00:00) and the evening peak sits at 20:00-23:00 at offset 0 (house 1 hours 20-23 carry the maximum; house 6 peaks at 07:00). The conclusion is right; one of the three proofs does not support it. Fix: keep the midnight start and the diurnal shape as the proof, and demote the row count to a consistency check.

### R7 (low) - “999%” in the Q5 table is a divide-by-zero clamp

House 4 has no panel, so `sm_span` is 0 and `cov` evaluates to 2.1e13%; `min(cov, 999)` prints “999%” for all eight house 4 plugs. The clamp makes an undefined ratio look like a measurement. Fix: print “-” when the panel span is 0.

### R8 (low) - “REDD's 24 kW split-phase ceiling”

`03_redd_eda.ipynb` measures the REDD panel maximum at 12,333 W, and my recompute agrees (leg maxima 6,081 W and 6,547 W, sum of maxima 12,628 W). 24 kW is the service rating of a 240 V/100 A US panel. Comparing ECO's measured 7.1-11.1 kW with a REDD nameplate flatters ECO and contradicts the sibling notebook. Fix: “REDD's measured 12.3 kW panel peak”.

### R9 (low) - The cleanliness claim is true but not computed, and under-scoped

“No NaNs, no sentinel constants, no exact zeros anywhere in `powerallphases`” is true — I verified 0 zeros and 0 NaNs across all five panels — but no cell counts zeros or NaNs, and the printed min/max (-1.0 and -7.9 W) cannot imply the absence of zeros. It also reads as a statement about the dataset when it is a statement about one column: plug channels do carry negatives (house 6's lamp integrates to -0.3 kWh and never recovers). Fix: print the counts (one line per house) and scope the sentence to the panel.

### R10 (low) - The summary JSON mixes computed and hand-typed values

`plug_counts`, `h1_quantised_until`, `dst_fallback_day_rows` and the whole `canonical_coverage` block are literals next to genuinely computed fields (`identity_residual_p99_W`, `h1_quantised_days`, `kettle_p50_on_W`, `plug_attribution_share_pct`). Same class as the notes in the REDD and AMPds2 reviews: a reader cannot tell which numbers would move if the data changed. Fix: derive the counts, or mark the literals. Minor, same cell: the `del ts_c, v_c` in the Q5 and Q7 loops frees nothing (the arrays are still referenced by the loop's list), which matters at house 5's 18.5 M rows.

## 5. Missing analyses, ranked by value

### P0 - Nesting and de-duplication (fixes R1)
A per-house `plug x sum-of-others` test, plus the specific `entertainment = tv + stereo` confirmation, then a de-duplicated share. This is the single change that moves a headline number.

### P0 - Per-canonical plausibility table (kWh/day)
Plug energy rates by canonical label expose label/scale faults that no share can: freezers run 0.43, 0.64, 0.13, 0.20 kWh/day in houses 1, 2, 3, 6 — and **3.69 kWh/day in house 4** (774.8 kWh over 210 days, median ON 179 W, 84% duty), 6-28x the others. Fridges run 0.11-1.08 kWh/day (house 3's 0.11 kWh/day is implausibly low for a fridge). House 6's lamp is negative. House 4 is the house where this matters most: it has 8 plugs totalling ~1,256 kWh, 62% of it that one freezer, and **no panel to validate against** — so an undetected fault there is invisible to the notebook's only cross-check.

### P0 - House-level intensity table (kWh/day of panel)
House 5's panel is 4,074.6 kWh over 219 days = **18.6 kWh/day**, against 6.8 (h1), 5.0 (h2), 5.4 (h3) and 3.8 (h6). Its 16% attribution is therefore mostly a *denominator* effect (the panel carries a large unplugged mass, plausibly resistance heating), not evidence that its plugs are worse than house 6's. Reporting the denominator alongside the share prevents the reader from ranking plug quality by share.

### P1 - What the unplugged remainder actually is
Q7 asserts “the 7 plugs there simply do not cover the cooking/heating mass” but never measures it. The residual `panel - sum(plugs)` is available second-by-second: its diurnal shape, its weather correlation and its largest steps would say whether the remainder is cooking, heating or base load, and would make the h5-16% finding actionable. House 2's dishwasher cycles give a natural validation target.

### P1 - Occupancy-conditional energy, not just occupancy-conditional mean power
The occupied-vs-vacant cross is the notebook's most under-used asset. Recomputing house 1 summer: 261 W occupied vs 127 W vacant over 3.37 M matched seconds, with 82.2% of matched seconds occupied. A per-window table (occupied %, mean W occupied, mean W vacant, and the ratio) is a few lines and is exactly the prior Q6 promises; the notebook prints mean power only for one house and never pools the ten windows.

### P1 - Apply the `03` threshold audit to ECO's fridges
ECO's fridge duties under the legacy rule (h1 36.6%, h2 33.0%, h3 14.3%, h4 28.3%, h5 34.9%, h6 18.8%) are *physically plausible*, unlike REDD's. That is a real and useful cross-dataset contrast — the ECO data has no 6 W idle floor problem — and it takes one cell to show the floor-threshold variant changes nothing here. It also gives a trustworthy baseline against which house 5's microwave and tablet channels stand out.

### P2 - Clock audit for the plug and occupancy files
The panel's clock is audited; the plugs and labels are assumed to share it. A single `dt` histogram per plug family (and the same DST check) would close that gap, especially with house 5's 25-day kettle and house 3's 38%-full PC channel.

### P2 - Temperature and season split
ECO ships indoor temperature and the notebook notes the winter-heavy panel load but never joins them. The occupied-vs-vacant separation and the h5 intensity story would both be sharper with a temperature axis.

## 6. How this compares with public practice

The ECO paper itself (Beckel et al., 2014) publishes the plug inventory and the panel-vs-plug relation, and the occupancy labels come from Kleiminger et al. (2015); the notebook's framing follows both. What public practice adds is exactly the two missing pieces. First, NILM Metadata (Kelly and Knottenbelt, 2015) expects a per-meter `submeter_of` relation and a coverage/quality field, precisely so that a group meter and its children are not summed — the R1 defect is a metadata gap, not a measurement gap. Second, dataset reviews (Pereira and Nunes, 2019) put missing data and label noise at the top of the obstacle list, and toolkits such as NILMTK (Batra et al., 2014) ship dataset-level quality reports for this reason; this notebook's span-ratio coverage is the same idea with one axis removed. The common-window lower-bound method in Q7, by contrast, is *ahead* of most published EDA on this dataset and should be the template for our own Shelly-plus-submeter validation.

## 7. Suggested order of work

1. **Aggregation (R1).** Nesting test, de-duplicated plug set, corrected shares, updated TL;DR and Q7 prose. Everything downstream of the share story changes.
2. **Prose numbers (R2, R3, R5, R8).** The kettle magnitude, the occupancy day range, the REDD contrast and the canonical coverage wording. Each is a one-line edit that removes a contradiction with the notebook's own tables.
3. **Trust and plausibility tables (R4, P0).** Coverage on two axes, per-plug duty/eps/int_cov, per-canonical kWh/day, house-level kWh/day. These turn four asserted claims into printed ones.
4. **Reuse `03`'s threshold machinery (P1).** Show that ECO's fridges are threshold-robust, and re-screen the chatter channels under both rules.
5. **Remainder analysis (P1).** Panel-minus-plugs by hour, so ECO's supervision claim is measured rather than argued.

## 8. Sources

- `docs/reports/dataset_eda/04_eco_eda.ipynb` and its build-time review (claim inventory).
- `docs/reports/dataset_eda/03_redd_eda.ipynb` (REDD panel maximum, threshold audit) and `03_redd_eda_peer_review.md`.
- `data/fnd/eco/`, `data/gold/appliance_map_eco.json`; `analysis/eda_fnd_lib.py` (`channel_stats`, `kwh_of`).
- Beckel, C., Kleiminger, W., Cicchetti, R., Staake, T., Santini, S. (2014). The ECO Data Set and the Performance of Non-Intrusive Load Monitoring Algorithms. BuildSys '14.
- Kleiminger, W., Beckel, C., Santini, S. (2015). Household Occupancy Monitoring Using Electricity Meters. UbiComp '15.
- Kelly, J., Knottenbelt, W. (2015). Metadata for Energy Disaggregation (NILM Metadata).
- Pereira, L., Nunes, N. (2019). Performance evaluation of non-intrusive load monitoring algorithms: a review. Energy and Buildings.
- Batra, N., Kelly, J., Parson, O., Dutta, H., Knottenbelt, W., Rogers, A., Singh, A., Srivastava, M. (2014). NILMTK: An Open Source Toolkit for Non-intrusive Load Monitoring. e-Energy '14.

---

## 9. External cross-check

Checked against the dataset's own shipped documentation: `data/raw/ECO/READ_ME_FIRST.txt` and the per-house `01..06_doc.txt` files, which state the plug inventory, the periods, the coverage fractions and the disaggregation notes that the EDA is making claims about. Third-party EDA artifacts were also sampled in a signed-in browser session (closing note).

**Confirms**

- **R1 is a documented identity, not a modelling judgement.** `02_doc.txt` states it directly: "The entertainment system consists of a stereo system and a TV. We 'manually' disaggregated those two into plugs 11 and 12 ... adding the consumption of plugs 11 and 12 equals the consumption of plug 05." The 94.8 % to 70.2 % correction is therefore reproducing the dataset's own group/child relation. The other house docs name Entertainment as TV plus stereo, and `04_doc.txt` additionally lists "04: Stereo and laptop" alongside "07: Entertainment", so the overlapping-child class is wider than the single house the review tested.
- **The notebook's own coverage sentences match the official docs.** "house 5's kettle logged just 25 September days" corresponds to Kettle in `05_doc.txt`, and house 1's PC stopping in August to the 66-day PC entry in `01_doc.txt`. Credit where due: the thin-supervision claims are exact.
- **Official smart-meter coverage, for the outage claims.** Panel coverage is h1 245 days / 99.64 %, h2 244 / 98.58 %, h3 138 / 98.89 %, h4 219 / 99.39 %, h5 215 / 99.05 %, h6 166 / 99.67 %. House 1's 245 days matches the notebook's "continuous for 245 days", and because the sub-100 % figures are sample-level, "zero gaps" and 99.64 % coverage are compatible rather than contradictory.

**New**

- **The sentinel convention is in the *plug* files, and it exactly reproduces the official coverage.** Each plug parquet is a full 1 Hz grid over the documented period, and missing seconds are encoded as **-1.0 W** rather than null: the -1.0 count divided by the documented day count returns the coverage the notebook prints (house 1 Fridge 98.53 %, house 2 Laptops 83.36 %, house 3 Fridge 56.00 %, house 6 Lamp 67.20 %), while plugs with 100 % coverage (house 2 Stove, house 2 TV) contain no sentinel at all. That sharpens R9 from a footnote into a correctness issue: the EDA's "No NaNs, no sentinel values" sentence is scoped to the three-phase smart-meter check it is attached to, but every plug-level aggregate, duty fraction and energy total inherits a bias proportional to how much of the file is sentinel, and the sentinel is negative so it can make a plug look quiescent.

**Public artifacts checked (signed-in browser session).** ECO has no comparable public EDA layer: Kaggle dataset and notebook searches for energy disaggregation surface REDD, GREEND, AMPds and London smart-meter mirrors but no ECO mirror and no ECO notebook, and GitHub results are the toolkit converters already cited. For this dataset the official documentation is the whole public record, which is also the stronger source.