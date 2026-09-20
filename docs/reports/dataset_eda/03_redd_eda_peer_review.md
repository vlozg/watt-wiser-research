# Review: `03_redd_eda.ipynb`

**Scope.** Independent peer review of `docs/reports/dataset_eda/03_redd_eda.ipynb` (46 cells: 23 markdown, 23 code, 9 figures). REDD is this series’ split-phase / 110 V reference: the notebook asks what a US panel, two legs and a 3–4 s circuit clock do to the assumptions every later notebook inherits. Scope is the notebook as written — claims, code, printed output, prose and the machine-readable summary at the end. The builder’s own self-review (`03_redd_eda_review.md`) sits alongside this file and covers the same ground from the inside; I did not use it while forming these findings, and I have not edited it.

**Method.** Everything below was recomputed from the source of truth: `data/fnd/redd/` (147 parquet — 116 main, 31 `_cache_`, 56,341,629 main rows), `data/gold/appliance_map_redd.json`, and `src/pipelines/02_fnd_eda_notebooks/eda_fnd_lib.py` read directly. I re-implemented `channel_stats` (both the `legacy` and the floor-aware rule) and `simultaneity` from the library source and ran them over all 6 buildings, and I re-read the notebook’s own cell outputs to check prose against table. Where my number differs from the notebook’s I say which is right and why. Tags follow the series convention: `[insight only]` (true of REDD, not generalisable) versus `[collectable]` (something worth measuring on a client site).

---

## 1. Verdict

This is a strong, honest notebook. Every structural claim I checked reproduces to the digit: 116 meters (12 site + 104 labelled circuits), 56.3 M main rows, all six per-building spans and coverages, the four b1 outages, the 13-of-104 degenerate-circuit sweep, the 77.3 per cent attribution, the 91.5 / 40.3 simultaneity pair, the canonical label matrix, and the 18:00 local diurnal peak. The provenance section is unusually candid about the two cache files and about float32.

It is also the first notebook in the series where I can reproduce the *defect*, not just the finding: three prose numbers are contradicted by the notebook’s own printed tables, and one printed number is wrong by eleven orders of magnitude. Ranked by consequence:

1. **Q7’s fridge anatomy is computed on the mask Q4 declares broken, and the prose attributes it to the repaired rule** (R2). Both the number (13.4 episodes/day, 16 s median) and the causal claim are wrong; the correct post-repair anatomy is 17.8 episodes/day, 1,096 s median.
2. **The canonical-target matrix counts labels, not live data** (R3). 29 of 104 labelled circuits carry under 0.5 kWh across their entire record — including three of the twelve washing-machine and dishwasher instances. That matrix is the one a suite-level consumer is most likely to quote.
3. **The `good_sections` cache is mis-united** (R1). The notebook prints “15103748716099.5 days” of continuity, then describes the same cache as “epoch seconds in both columns” in two places. The correct reading is mixed units (`ts_us` in microseconds, `value_0` in nanoseconds) and one 36.34-day section.
4. **Q9’s simultaneity denominator counts empty minutes as “zero appliances ON”** (R5). 8.5 per cent of the 60 s grid holds no circuit sample at all; conditioning on covered minutes moves the floor-rule headline from 40.3 to 44.1 per cent and “zero ON” from 25.9 to 19.0 per cent.
5. **Q5’s three-source cadence ranking mixes two yardsticks, and its 78 per cent is never computed anywhere in the notebook** (R4). I could not find 78 in any cell output: the circuits are 95.2 per cent complete against their own cadence (4.8 per cent missing) and 23.8 per cent complete against a 1 Hz clock. On the meter’s own clock the dropout cache *over*-reports loss, which inverts the ranking the prose draws.
6. **The largest missing analysis is paired coverage** (P0). The panel’s clock is a strict subset of the circuits’ (only 2 of 52,236 minutes are panel-only), and 41.1 per cent of the clock has appliance data with no aggregate above it. REDD’s supervised yield is 50.3 per cent of its span — a number the notebook never states, though it reports the two marginal coverages (49.8 and 91.5) that bracket it.
7. **Two prose counts contradict the notebook’s own tables** (R8): “four b1 meters read always-ON” (there are three) and “four lights” in b1 (there are three). Both are small, and both are the kind of error the series claims to have audited out.

None of these undermine the notebook’s structural conclusions. They do mean that Q7’s appliance anatomy and Q9’s coincidence number should not be quoted onward until fixed.

---

## 2. Reproduction

Every row was recomputed independently from the fnd layer; “Notebook” is what the cell output prints or the prose asserts. `kWh_cap` uses the notebook’s own rules (`dt_cap_s=10` for the panel at 1 s, 30 for circuits at 4 s).

| Notebook claim | Notebook | Independent recompute | Verdict |
|---|---|---|---|
| 6 buildings, 116 meters (12 site + 104 circuits) | 116 / 104 | 116 main parquet: 6 x 2 site + 104 labelled (b1 18, b2 9, b3 20, b4 18, b5 24, b6 15) | exact |
| 56.3 M rows in the main files | 56.3 M | 56,341,629 | exact |
| b1 panel: 1,561,660 rows, 36.3 d, 49.8 per cent 1 Hz coverage | same | 1,561,660 rows over 36.34 d = 49.79 per cent | exact |
| per-building coverage 39.6 / 36.9 / 40.5 / 8.0 / 43.9 per cent | same | 1,198,534 / 1,427,284 / 1,679,839 / 302,122 / 887,457 rows over 35.0 / 44.8 / 48.0 / 43.8 / 23.4 d = 39.6 / 36.9 / 40.5 / 8.0 / 43.9 | exact |
| b1 four outages 41–227 h (largest 9.45 d) | same | 41.21 / 65.3 / 87.34 / 226.81 h = 1.72 / 2.72 / 3.64 / 9.45 d | exact |
| b5 one 31-day outage; 8 per cent of 44 d | same | span 43.8 d, max gap 31.42 d, coverage 8.0 per cent | exact |
| mean dt 2.01 s; 99.1 per cent of gaps exactly 1 s | same | mean 2.007 s; 99.05 per cent of deltas equal 1 s | exact |
| legs mean 226.9 and 157.1 W; sum 384.0 W | same | 226.9 / 157.1 / 384.0 W | exact |
| leg imbalance 30.8 per cent | same | label is self-documenting (`abs(mean1-mean2)/mean1`): 30.8 per cent; against the mean of the two legs it is 36.4 per cent | exact, definition stated in the print label |
| joint steps (both legs within one sample) 519 | 519 | 519, of which 247 rises, 263 falls, 9 anti-correlated (one leg up, one down) | exact; composition not stated |
| uncapped 341.3 / capped 167.7 / phantom 173.6 kWh | same | 341.3 / 167.7, difference 173.6 | exact |
| degenerate circuits under the legacy rule: 13 of 104 | 13, with a 13-row list | 13, same 13 (building, meter) pairs and same legacy and floor duties and thresholds | exact |
| circuits sample every 4 s | b1 dt_med 4.0 s | b1 4.0 s, but b2/b3/b6 circuits are 3.0 s; the 104-circuit sweep’s dt_med set is {3.0, 4.0} | see R6 |
| dropout_rate cache: 21.2 per cent of expected samples missing inside sections | 21.2 per cent | cache mean 0.212 over 24 rows; but the circuit clock is 95.2 per cent complete against its own cadence (4.8 per cent missing) | cache value exact, comparison in R4 |
| good_sections cache: 26 rows, 1 unique section, “15103748716099.5 days” | 26 / 1 / 1.5e13 days | 26 rows, 1 unique pair; raw values are start 1,303,132,929,000,000 (µs) and end 1,306,267,022,000,000,000 (ns) = 36.34 d | see R1 |
| Q7: fridge 13.4 episodes/day, median 16 s, p90 326 s | same | legacy mask: 13.4 / 16 / 326 s. Floor mask: 17.8 / 1,096 / 1,624 s | see R2 |
| Q7: dishwasher 9.3 / 176 s, microwave 12.1 / 60 s, washing machine 1.7 / 432 s | same | reproduce exactly under both masks | exact |
| Q8: 14 of 37 full days; panel 128.2, submeter 99.1 kWh; attributed 77.3 per cent | same | 14 of 37 days; 128.20 / 99.11 kWh = 77.30 per cent; unattributed 29.1 kWh | exact |
| Q9: two-plus share legacy 91.5 per cent, floor 40.3 per cent | same | reproduce exactly on the notebook’s denominator (all buckets); 100.0 and 44.1 per cent on covered buckets | exact, denominator in R5 |
| Q9 shares {0: 25.9, 1: 33.8, 2: 20.1, 3: 11.4, 4: 5.7, 5: 1.5} | same | reproduce; conditional on covered buckets {0: 19.0, 1: 36.9, 2: 21.9, 3: 12.5, 4: 6.3, 5: 1.7} | exact, denominator in R5 |
| diurnal peak 18:00 local (UTC-4) | 18 | mean W by local hour peaks at 18:00 (807 W), next 22:00 (450 W) | exact |
| canonical matrix: dishwasher 6/6, washing machine 6/6, fridge 5/6, microwave 4/6, kettle 0/6 | same | label counts reproduce exactly; live-data counts differ (R3) | exact as labels, see R3 |
| “four b1 meters read always-ON” | 4 | b1 legacy duty over 85 per cent: exactly 3 (m5 99.4, m7 100.0, m8 100.0); the simultaneity histogram’s minimum on covered minutes is 3 | notebook wrong (R8) |
| “building 1’s 18 circuits include four sockets, four lights and two unknown” | 4 / 4 / 2 | 4 sockets, 3 lights, 2 unknown (the notebook’s own duplicate-label line prints “light x3”) | notebook wrong (R8) |
| “far from the 78 per cent the circuit clocks actually lose” | 78 per cent | not printed anywhere in the notebook; circuit rows are 23.8 per cent of a 1 Hz expectation (76.2 per cent lost) and 95.2 per cent of their own cadence | notebook wrong / underivable (R4) |
| — (not in notebook) paired aggregate + appliance coverage | — | wall-clock minutes 52,236; panel present 26,300 (50.3), circuits present 47,791 (91.5), both 26,298 (50.3), panel-only 2, circuit-only 21,493 (41.1) | missing analysis (P0) |
| — (not in notebook) near-zero-energy circuits | — | 29 of 104 labelled circuits below 0.5 kWh for the whole record | missing analysis (P0) |

---

## 3. What the notebook gets right

- **Inventory and clock discipline.** The meter/circuit census, per-building spans, per-building coverages and the four multi-day outages all reproduce exactly. The 1 Hz-equivalent coverage definition is the honest one (rows over span seconds), and it is applied consistently across buildings, which is what makes the b5 comparison (8.0 per cent) legible next to b1 (49.8 per cent).
- **The clock-over-cache framing (Q5).** Treating the timestamp grid as authoritative and the converter caches as summaries is the correct instinct, and it is the right lesson to carry into the client pipeline, where Shelly EM Gen3 will also produce gaps that a summary layer can hide. The structural finding that the `good_sections` cache collapses to one section while the grid shows 9.45 days of outage is real and useful.
- **The degenerate-channel sweep (Q4) is the best-conceived analysis in the notebook.** It is run over all 104 labelled circuits rather than the reference home, it reports both rules side by side, and both my re-implementations reproduce all 13 rows — legacy duty, legacy threshold, floor duty, floor threshold, floor level — exactly. A threshold rule that turns a fridge into a 99.4 per cent-duty appliance is a genuine trap for any pipeline that inherits it, and the notebook quantifies it rather than asserting it.
- **Q8’s denominator discipline.** Restricting attribution to days with at least 80 per cent panel coverage (14 of 37) and capping dt before integrating is exactly right, and the notebook explicitly flags that it is *not* using the naive own-span comparison. The 77.3 per cent result reproduces to two decimals, including the unattributed 29.1 kWh.
- **Q9’s pairing of the two rules.** Showing 91.5 per cent under the legacy rule and 40.3 per cent under the repaired rule, in one table, makes the point that most of the apparent “coincidence” was threshold error. That is a better framing than reporting either number alone, and the share histogram is printed, so a reader can re-derive the conclusion.
- **Canonical-target honesty.** “No kettle anywhere” is stated in the TL;DR, and the matrix prints the actual meter numbers (washing machine 10,20 / 7 / 13,14 / 7 / 8,9 / 4), so a reader can see that b1 carries washer and dryer as two labelled circuits. The 5/6 fridge gap is explained (b4 labels no fridge circuit) rather than hidden.
- **Timezone reasoning.** All six spans fall between 2011-04-16 and 2011-06-14, inside a single US DST window, so the fixed UTC-4 offset is correct everywhere — stated once, with the reason, which is more than most EDA notebooks manage.
- **Provenance and release terms.** Attribution (Kolter and Johnson 2011; see R11), conversion tooling (NILMTK), the cache-file names and the float32 caveat are all recorded. The one error in this section is the cache unit statement (R1), but the practice of writing the caveat down is right.
- **The provenance/limits paragraph (Q10).** “Heritage reference, not a training corpus — weeks, not years; half the clock missing; no kettle” is the correct downstream conclusion, and it is consistent with every number I recomputed. P0 below sharpens “half the clock missing” from an impression into a measured 50.3 per cent.

---

## 4. Errors, ranked

### R1 (high) - the `good_sections` cache is mis-united, and the notebook prints a number that is wrong by eleven orders of magnitude

The cell that decodes the cache prints:

    m1 good_sections cache: 26 rows -> 1 UNIQUE section, claiming 15103748716099.5 days
    of continuity over the 36.3-day span

The unit statement that accompanies it, in the cell comment and repeated in the provenance section, is: “the good_sections cache stores epoch seconds in both columns (`ts_us` = section start, `value_0` = section end, despite the column name)”. Both halves are wrong. Reading the file directly:

- `ts_us` = 1,303,132,929,000,000 — that is **microseconds** (dividing by 1e6 gives 2011-04-18, the first b1 panel sample);
- `value_0` = 1,306,267,022,000,000,000 — that is **nanoseconds** (dividing by 1e9 gives 2011-05-24, the last b1 panel sample).

So the two columns are in different units, the single unique pair is (2011-04-18, 2011-05-24) = 36.34 days, and the notebook’s `(end-start)/86400` therefore divides a nanosecond-scale difference by a seconds-per-day constant. The prose then reports “36.3-day span” for the cache, which is the *grid’s* span, not anything the cache arithmetic produced — the notebook silently substitutes the right answer for the number its own code printed. The conclusion survives (one unique section really does claim the full span), but a reader auditing the notebook’s “every number is computed” discipline finds a printed value that is wrong by 1e11 and a unit claim that is wrong in two columns.

Fix: decode explicitly (`start_s = ts_us/1e6`, `end_s = value_0/1e9`), report the section length in days, and correct the unit sentence in the provenance section. Also worth recording in the same breath that the cache, once decoded, agrees with the grid at the *section* level while missing the four outages entirely — which is the actual lesson.

### R2 (high) - Q7’s fridge row is the mask Q4 calls broken, and the prose attributes it to the repair

Q4 establishes that the legacy threshold rule makes the b1 fridge 99.4 per cent duty with a 5 W threshold — a threshold-chatter artefact, because the appliance’s idle is only ~6 W. Q7 then reports, for the fridge: 13.4 episodes/day, median dwell 16 s, p90 326 s, and the prose says the fridge “even after the threshold repair — is dominated by short electronics blips (median 16 s)”.

Both halves are wrong. The 13.4 / 16 s / 326 s row is the **legacy** mask (I reproduce it exactly under the legacy rule). Under the floor-aware rule the same channel gives 17.8 episodes/day, median 1,096 s, p90 1,624 s, duty 25.8 per cent — compressor-scale cycles, which is what a fridge should look like and what the Q4 repair was for. The prose therefore draws the opposite conclusion from the notebook’s own Q4 result: it presents the artefact as evidence that the fridge remains blip-dominated after repair.

The other three rows (dishwasher 9.3 / 176 s, microwave 12.1 / 60 s, washing machine 1.7 / 432 s) reproduce under both rules, so the fix is narrow: recompute the fridge row under the floor rule, or report both, and change the sentence. Given the series’ house style, reporting both masks is the better fix — it turns the row into a second demonstration of why the rule matters.

### R3 (high) - the canonical matrix counts labels, not live data; 29 of 104 circuits are effectively dead

The notebook reports canonical coverage as label counts: dishwasher 6/6, washing machine 6/6, fridge 5/6, microwave 4/6. Integrating each labelled circuit over its whole record (dt capped at 30 s) I get 29 of the 104 labelled circuits below 0.5 kWh total, i.e. at least one dead or mislabelled channel in every building:

- b5 m8 and m9 (“washer dryer”): 0.019 and 0.003 kWh;
- b6 m9 (“dish washer”): 0.078 kWh;
- b4 m9, m10 and m20 (“air conditioner”): 0.070, 0.030, 0.003 kWh;
- b5 m4 (“light”): 0.001 kWh with a maximum sample of 3 W; b1 m19 (“unknown”): 0.0 kWh; among others.

So three of the twelve dishwasher and washing-machine instances carry no usable energy, and building 5’s canonical washing machine is one of them. The matrix is a statement about the label file, not about the data, and a downstream consumer reading “6/6” will assume twelve usable supervision streams where at least nine are. This matters more here than in the UK-centric notebooks because REDD’s whole value proposition in this series is the four canonical targets across six homes.

Fix: add a liveness column (capped kWh over the record, and maximum observed power) to the Q3 matrix, and print the dead-channel census — count, list, and the effect on the canonical counts. A channel that reads under a few Wh over weeks is a meter or label fault, not a quiet appliance, and the notebook already has the machinery to say so in one line.

### R4 (medium) - Q5’s cadence ranking mixes two yardsticks, and its 78 per cent is never computed

Q5 compares three sources for “how much of the clock is present”: the timestamp grid (49.8 per cent 1 Hz-equivalent), the `dropout_rate` cache (21.2 per cent missing *inside* sections), and “still far from the 78 per cent the circuit clocks actually lose”. That ordering is not derivable from the notebook’s own outputs, and I could not find the value 78 anywhere in the cell outputs. The measurements that exist:

- circuit rows over their span against their **own** cadence (4 s): 95.2 per cent present, 4.8 per cent missing;
- circuit rows against a **1 Hz** clock: 23.8 per cent present, 76.2 per cent missing.

So the cache’s 21.2 per cent sits between the 1 Hz figure and the own-cadence figure only because those are different questions. Against the grid the cache is trying to describe (missing samples for this meter, given its own clock) the cache **over**-states loss by about four times; against a 1 Hz standard, everything is missing three quarters of the time, which says nothing about the cache. The prose draws the opposite ranking (“closer to the truth”) from a number the notebook never computed. The same conflation recurs in Q10, where the circuit clock is described as “4 s nominal plus about 21 per cent internal dropout” — that combination would imply a 5 s effective cadence when the measured median is 4.0 s.

One further structural fact worth stating, which the notebook misses: all 18 b1 circuit files hold **exactly the same 745,878 rows on the same grid**, so the 4.8 per cent that is missing is common-mode (one logger, one set of hiccups), not per-channel dropout. That strengthens the notebook’s “the clock is authoritative” point, and it is one line of code to check.

Fix: state each denominator explicitly and drop 78; use 4.8 per cent (own cadence) and 76.2 per cent (1 Hz) with their yardsticks named; correct the Q10 sentence.

### R5 (medium) - Q9’s simultaneity denominator counts empty minutes as zero-ON

`simultaneity` buckets each circuit into 60 s bins, marks a bin ON when its mean exceeds 0.5, and then computes shares over the full grid. Bins with no sample at all therefore enter the histogram as “zero appliances ON”. On the b1 grid (52,235 bins over 36.3 days) **4,448 bins — 8.5 per cent — hold no circuit sample**, because the common-mode gaps are shared. Conditioning on covered bins:

| rule | two-plus, all bins | two-plus, covered bins | zero-ON, all bins | zero-ON, covered bins |
|---|---|---|---|---|
| legacy | 91.5 per cent | 100.0 per cent | 8.5 per cent | 0.0 per cent |
| floor | 40.3 per cent | 44.1 per cent | 25.9 per cent | 19.0 per cent |

The printed 40.3 per cent therefore understates the repaired coincidence share by 3.8 points, and the printed 25.9 per cent zero-ON inflates silence by 6.9 points. The notebook cares about exactly this class of denominator honesty in Q8 (where it correctly restricts to 80-per-cent days), so the omission here is an internal inconsistency rather than a nitpick. The share histogram is also printed with its max at 11–12 circuits, which is itself informative — but only if the reader knows that 8.5 per cent of the mass is “no data”.

Fix: either condition the shares on covered bins, or label the zero-ON row as “zero or no data” and print the empty fraction alongside. State the minimum circuit count on covered bins (3), which is what makes the legacy 91.5 per cent legible as an artefact.

### R6 (medium) - “circuits sample every 4 s” is true of building 1 only

The TL;DR, Q6’s question line and (via the series overview) the dataset table all say REDD circuits are 4 s. The fnd layer disagrees by building: dt_med is 4.0 s in b1, b4 and b5, and **3.0 s in b2, b3 and b6**; the 104-circuit sweep’s distinct dt_med set is {3.0, 4.0}. Within b1 the mode is 4 s for only 47 per cent of intervals, so even there the clock is irregular. The notebook already knows this — the machine-readable summary carries a `circuits_4s_not_1s` quirk — but the quirk is phrased as a comparison with 1 s, so it does not catch the 3 s case.

Consequence: any downstream statement that treats REDD circuits as uniformly 4 s (including a resample rule or a nominal-cadence table) is wrong for half the buildings. Fix: report per-building circuit cadence, and say 3–4 s. The same one-word change should be carried into `00_overview.md` line 15, which repeats “4 s circuits”.

### R7 (medium) - the 519 “joint steps” mix switch-ons, switch-offs and anti-correlated steps, and the detector is never validated

Q2’s dual-leg detector counts samples where both legs move by at least 150 W within one sample: 519 events, against 2,793 leg-1-only and 776 leg-2-only. That 519 is a sum over edges, not a count of 240 V switch-ons: decomposing by sign, 247 are rises on both legs, 263 are falls on both legs, and 9 have one leg rising while the other falls (a leg-balance shift, not a 240 V load). A 240 V appliance produces two transitions per cycle, so the physically meaningful count is 247 onsets, and the 9 opposite-signed events are unexplained by the 240 V story the notebook tells.

More importantly, the detector is never validated against the labelled 240 V loads that exist in the same home: b1 m3 and m4 (“electric oven”), m14 (“electric stove”), m13 (“electric space heater”). The notebook presents the detector as both an insight and a candidate gold-layer feature; a feature that recommends itself for the pipeline should be checked against the labels in the one home where labels exist. As written, a reader cannot tell whether 519 is a 240 V census or an artefact of the two legs’ noise.

Fix: split the count by sign, then intersect the 247 joint rises with the labelled 240 V circuits’ ON onsets (the notebook already loads those channels), and report precision and recall. Report the 9 anti-correlated steps separately.

### R8 (low) - two prose counts contradict the notebook’s own tables

- Q9’s prose says “four b1 meters read always-ON”. The b1 duty census over the legacy rule gives exactly three above 85 per cent (m5 99.4, m7 100.0, m8 100.0), and the simultaneity histogram’s minimum count on covered bins is 3, which independently confirms three. The Q4 flag list for b1 is also three. Fix: four -> three.
- Q9’s prose says b1’s 18 circuits include “four sockets, four lights and two unknown channels”. The true decomposition is 4 sockets (m7, m8, m15, m16), **3 lights** (m9, m17, m18) and 2 unknown (m12, m19); with four lights the categories sum to 19 circuits, not 18. The notebook’s own duplicate-label line prints “light x3”, so the table needed only to be read. Fix: four -> three.

### R9 (low) - “zero episodes” describes a rounded 0.0, and a 34.5-day dwell is printed without comment

Q4’s prose says the b1 sockets meters have “duty 100 per cent, zero episodes”. The Q4 table prints `eps/day = 0.0` (rounded) and `dwell_p50 = 2983512 s` — i.e. one episode running 34.5 days, the whole record. “Zero episodes” is therefore false at the resolution the table itself reports, and the 2,983,512 s cell is a visibly degenerate value left unflagged in a table whose purpose is to flag degeneracy. Fix: say “one episode spanning the entire record”, and have the flag rule catch dwell longer than, say, half the span.

### R10 (low) - the machine-readable summary carries hand-typed statistics and a false quirk

The JSON block at the end is the interface a later notebook or a suite-level table would consume, and it contains three literals I would not trust: `good_sections_cache_rows: 26` and `degenerate_channels_all_buildings: 13` are hand-typed rather than derived (both happen to be correct, but they cannot be re-derived from the JSON), and the quirks list asserts `cache_units_epoch_seconds`, which R1 shows is false for both columns. A consumer that branches on that quirk key inherits the unit bug.

Fix: compute the two counts, drop or correct the unit quirk, and add the decoded cache section length. The summary is otherwise the most useful artefact in the notebook and worth keeping accurate.

---

### R11 (low) - the citation names a co-author the release does not, and mis-titles the paper

Line 10 and the closing block attribute the dataset to "Kolter & Chakravarty 2011" and to *REDD: A Reference Data Set for Energy Disaggregation*. The release README's own citation block names **J. Zico Kolter and Matthew J. Johnson**, *REDD: A public data set for energy disaggregation research* (SustKDD 2011), and the public Kaggle mirror repeats that attribution; a GitHub code search for "Anustup Chakravarty" (the name the notebook gives) returns zero files. The attribution is unsupported, and it reached this review's §8, which is corrected as part of this pass.

Fix: replace both occurrences with the README's citation. Low consequence for the analysis, but the JSON summary is an interface other documents copy.

---

## 5. Missing analyses, ranked by value

### P0 - paired aggregate/appliance coverage: the number that decides whether REDD can supervise anything

The notebook reports two marginal coverages side by side — the panel’s 49.8 per cent and the circuits’ clock — and separately notes that the circuits kept recording during the panel’s outages. The consequence is a single hard number that appears nowhere: bucketing both clocks into the same 60 s grid over b1’s shared span (52,236 minutes),

| minutes | count | share |
|---|---|---|
| panel only | 2 | 0.004 per cent |
| both (usable aggregate + appliance) | 26,298 | 50.3 per cent |
| circuits only (appliance data, no aggregate) | 21,493 | 41.1 per cent |

Two facts fall out and both are quotable. First, the panel’s coverage is a strict subset of the circuits’ — only two minutes in 36 days have an aggregate and no submeter data, which is a much cleaner structural statement than “they overlap”. Second, 41.1 per cent of the wall clock contains labelled appliance data with nothing above it, so the supervised yield is 50.3 per cent, not 49.8 and certainly not 91.5. A disaggregation corpus needs aggregate and appliance co-present; REDD is a 36-day dataset that behaves like an 18-day one. Q10’s “half the clock missing” is the right instinct — this is the measurement behind it, and it is two lines of code.

### P0 - dead-channel and liveness census for the label matrix

R3 gives the count (29 of 104 below 0.5 kWh) and the canonical casualties. The analysis that should own this is Q3/Q4: a liveness table next to the canonical matrix — capped kWh, maximum observed power, largest single sample — with the canonical counts recomputed on “live” channels only. That turns “6/6 dishwasher” into “6/6 labelled, 5/6 live” and makes the label file’s quality auditable. It also gives the natural sanity check for the future Shelly pipeline: the same liveness column, computed per circuit, is how one detects a miswired or unused CT channel on a client site.

### P0 - validate the dual-leg 240 V detector, and split it into onsets and offsets

R7 gives the decomposition (247 rises, 263 falls, 9 anti-correlated). The missing analysis is the one that would make Q2’s detector a deliverable: intersect the joint rises with the ON onsets of the labelled 240 V circuits in b1 — the two oven circuits (m3, m4), the electric stove (m14) and the electric space heater (m13) — and report how much of each appliance’s energy is recovered by the joint-step test alone. If it recovers the ovens and the stove, the detector is a genuine feature for the client pipeline (a split-phase panel is where 240 V detection is cheapest); if it does not, the notebook should say the detector is unvalidated. Either outcome is worth more than the current unexplained 519.

### P1 - infer each circuit’s leg, and explain the 30.8 per cent imbalance

Q2 quantifies the leg imbalance (226.9 versus 157.1 W mean, 30.8 per cent by the notebook’s own metric) and then, correctly, notes that the label set does not record which leg a 120 V circuit sits on. That is a limitation for *validation*, but it is not an obstacle to *inference*: each labelled circuit’s ON episodes produce a step on one leg and not the other, so correlating a circuit’s step series against `diff(m1)` and `diff(m2)` assigns it a leg with high confidence. Doing that would (a) explain the imbalance as circuit placement plus unlabelled 240 V load, (b) produce a derived label the notebook currently says is missing, and (c) test the joint-step detector from the other direction. This is the single highest-value analysis the split-phase framing makes possible and the notebook does not attempt it.

### P1 - the two b5 subpanel circuits, and what they mean for any suite-level attribution

The label table already prints “building_5 duplicate labels: subpanel x2”, and Q4 flags one of them (b5 m10) as a degenerate 100 per cent-duty channel. Subpanel meters sit *above* other labelled circuits in the same building, so summing b5’s labelled circuits double-counts whatever the subpanels feed — which is precisely why Q8 is scoped to b1. The notebook is careful here, but never says why Q8 is b1-only, and a suite-level table that averages “attributed share” across the six homes would silently inherit the problem. Fix: state the nesting explicitly, and either exclude the two subpanels from any aggregate or nest them. The same note protects the eventual multi-dataset attribution comparison in `00_overview.md`.

### P1 - report per-building circuit cadence, not one number for the dataset

R6: the 3 s / 4 s split is per building, and the fnd `_cache_` files for `total_energy` will have been computed on whichever grid the converter chose. A one-line table (building, dt_med, modal fraction) would let the reader see that b2/b3/b6 are not the same shape as b1, and would justify the resample rule used in Q8’s integration.

### P2 - attribution for the other five homes, with the subpanel caveat attached

Q8’s 77.3 per cent is b1-only and the prose is appropriately cautious. But the interesting cross-dataset claim in this series — where REDD sits between UK-DALE and REFIT on attribution — needs at least two more homes. b2 and b6 are the candidates (no subpanels, 40–44 per cent panel coverage), and per-building numbers would also expose whether the “unattributed 29 kWh” is dominated by one building’s missing circuit (b1’s cold chain may hide in `unknown`/`sockets`).

### P2 - a typical day, not only the highest-energy day, in the signature gallery

Q6 is explicit that each window is the circuit’s highest-energy day, which is the right choice for showing “real work” and is honestly labelled. It is worth one extra panel per circuit chosen as the **median**-energy day, because the gallery’s purpose in this series is to calibrate what a client-site signature will look like, and the peak day is not that. Optional, cheap, and it removes the only place in the notebook where a peak window could be mistaken for a typical one.

---

## 6. How this compares with public practice

- **Clock over cache is the right default, and it is under-practised.** Most published REDD usage consumes `redd.h5` (NILMTK’s conversion) and never re-derives coverage from the low-frequency CSVs, so the `good_sections` and `dropout_rate` caches propagate unchallenged. This notebook is doing better than the common case by disbelieving them; R1 and R4 are both consequences of doing that job only half-way, which is a fair summary of where the practice sits.
- **“How much of REDD is actually usable” is usually answered with the mains coverage only.** Papers that report a REDD train/test split typically report the mains series’ span, not the co-presence of aggregate and submeters, and almost never report the subpanel nesting in building 5. The paired-coverage metric in P0 is the honest version of the same question, and it is cheap.
- **Threshold-rule degeneracy is a real and widely suffered artefact.** The legacy rule that makes a fridge 99.4 per cent ON (threshold at half the median of nonzero samples, floored at 5 W) is the standard simple ON/OFF detector in the disaggregation literature; the low-power idle of a modern fridge defeats it, and the failure mode — apparent “coincidence” between always-ON channels — is routinely mistaken for behaviour. Q4 and Q9 together are a better treatment of this than most published pipelines, once R5 is fixed.
- **240 V detection from two legs is a known NILM lever.** Public REDD work generally uses the two mains channels as one aggregate and discards the split-phase structure, which is what makes the two-leg joint-step test here comparatively novel for this series. That is also why R7’s validation gap matters: the technique is worth stating only if the labels back it.
- **Liveness checks are standard practice in utility-grade submetering and rare in research EDA.** A channel reading under a Wh per week is a fault, not an appliance; production submeter installs screen for exactly this. R3/P0 propose importing that check into the research workflow, which is the direction the client pipeline needs anyway.

---

## 7. Suggested order of work

1. **R2 (Q7 fridge row)** — recompute under the floor rule, report both masks, fix the sentence. Small, and it is the one finding that changes a quoted number.
2. **R3 + P0 (liveness)** — add the capped-kWh/max-power column to the canonical matrix, print the dead-channel census, recompute the canonical counts on live channels. Medium effort, changes what the matrix means.
3. **R1 + R4 (cache decode and cadence)** — decode the `good_sections` units, correct the provenance sentence and the JSON quirk, replace the 78 per cent comparison with named-denominator numbers, and record the common-mode dropout fact.
4. **R5 (simultaneity denominator)** — either condition on covered bins or label the zero-ON row and print the empty fraction; add the minimum circuit count.
5. **P0 (paired coverage)** — one table: panel-only, both, circuit-only over the shared grid, per building where the grids allow. This becomes the honest “usable span” line for REDD in `00_overview.md`.
6. **P0 + R7 (240 V detector validation)** — split by sign, then intersect with the labelled 240 V circuits.
7. **P1 (leg inference)** — correlate circuit step series against the two legs; explain the imbalance and produce the derived leg label.
8. **R8 + R6 + R9 + P1/P2 (text and small tables)** — the two count fixes, the per-building cadence table, the dwell flag, the subpanel note, and the overview’s “4 s circuits” wording.

---

## 8. Sources

- `docs/reports/dataset_eda/03_redd_eda.ipynb` — the notebook under review (46 cells, 9 figures).
- `docs/reports/dataset_eda/00_overview.md` — series framing; line 15 repeats the “4 s circuits” wording (R6), and the cross-dataset claims that Q8’s b1-only number feeds.
- `src/pipelines/02_fnd_eda_notebooks/eda_fnd_lib.py` — `channel_stats` (legacy and floor rules), `simultaneity`, `kwh_of`; read directly and re-implemented for this review.
- `data/fnd/redd/` — 147 parquet (116 main, 31 `_cache_`), 56,341,629 main rows; `data/gold/appliance_map_redd.json` — labels and canonical roles; `data/gold/thresholds.json`.
- Kolter, J. Z. and Johnson, M. J., *REDD: A public data set for energy disaggregation research*, SustKDD 2011 — the citation printed in the release README itself (see R11); distributed for research use.
- Batra, N. et al., *NILMTK: An Open Source Toolkit for NILM*, e-Energy 2014 — the conversion tooling whose caches Q5 decodes.

---

## 9. External cross-check

Checked against the release documentation and the reference toolkit: the REDD release README (Kolter and Johnson) retrieved from the Internet Archive (the canonical host `redd.csail.mit.edu` is unreachable from here, http and https both failing to respond), the vendored NILMTK converter `dataset_converters/redd/convert_redd.py`, and the published cadence table in the GREEND paper (Table 1) that lists REDD's own specs. Third-party EDA artifacts were also sampled in a signed-in browser session (closing note).

**Confirms**

- **R6, and it is a documentation error, not a units slip.** The README: data are "logged at a frequency of about once a second for a mains and once every three seconds for the circuits". The published specification is therefore 1 s and 3 s, which is what b2, b3 and b6 already show; b1's 4 s is the outlier, and the notebook's "Panel meters clock at 1 s; circuit meters sample every **4 s**" and "circuits = 4 s nominal plus ~21 % internal dropout" invert the story by treating the outlier as the spec. The same wording is repeated in `00_overview.md` line 15 and in a [collectable] recommendation ("the 4 s circuit cadence is still ample"), so the correction is three edits rather than one.
- **Labels are circuit categories, not appliance ground truth.** The README: `labels.dat` carries "the device category labels", and the authors "attempted to best categorize the main type of appliance on the circuit". That supports the framing §3 credits, and it is the right frame for R3's liveness census and R9's socket dwell: a label describes the circuit, so a circuit that is mostly a small always-on load is not evidence about the appliance a model expects to find there.
- **Mains channels are 1 and 2.** The README's own example is `1 mains_1`, `2 mains_2`, consistent with the legacy channel mask whose load-bearing role R2 uncovers.

**New**

- **REDD circuit "watts" are apparent power, and nothing in the EDA says so.** The README states that circuit files record "the apparent power", while NILMTK's converter assigns `ac_type = 'apparent'` to the mains only (`chan_id <= 2`) and `'active'` to every circuit, and our gold layer carries no apparent/active distinction at all. The consequence is concrete: the circuit Wh/kWh episodes and the Q8 "~77 % attribution" comparison place circuit VA next to other datasets' active power. Either label the circuits apparent and keep power-factor effects out of cross-dataset energy comparisons, or state the approximation in the cell that computes them.
- **The release documentation itself is not in the repo.** `data/raw/redd/` contains only `redd.h5`; the README and `labels.dat` semantics came from the Internet Archive. Since our pipeline's label provenance and the 3 s cadence both live in that README, it should be staged with the data (or its content cited in the metadata), not left implicit.

**Public artifacts checked (signed-in browser session).** GitHub code and repository search for GREEND/REDD NILM work returns two GREEND repositories, both last updated in 2016 with one star between them, and no issue thread about the meter-to-column join. The legacy `nilmtk/dataset/redd.py` published in public forks copies the README sentence "once a second for a mains and once every three seconds for the circuits" into its own docstring, a second public statement of the 3 s spec. On Kaggle, the REDD mirror reproduces the README's `labels.dat` convention and attributes the dataset to Kolter and Johnson, and it carries only two notebooks, the most-upvoted an HMM device-usage exercise; a Kaggle notebook search for energy disaggregation returns thirteen results, led by a competition visualisation. None of the public artifacts examines cadence, apparent versus active power, or per-channel liveness: the defects above are unremarked publicly, not disputed.
