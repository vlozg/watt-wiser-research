# Review: `02_refit_eda.ipynb`

**Scope.** `docs/reports/dataset_eda/02_refit_eda.ipynb` only. The stale `03`-`07` notebooks are out of scope.

**Method.** Read the notebook cell by cell; re-derived every headline number directly from
`data/fnd/refit/` using `analysis/eda_fnd_lib.py` and independent re-implementations of its two
run-detectors; read the release's own documentation (`data/raw/REFIT/CLEAN_READ_ME_081116.txt`,
`REFIT_Readme.txt`) and the dataset's data descriptor (**Murray, Stankovic & Stankovic, *Scientific
Data* 4:160122, 2017** — full text retrieved); cross-checked the statistics against what the
published descriptor itself reports about the same dataset; inspected the extraction pipeline
(`src/pipelines/01_extract_dataset/extract_refit.py`) whose output the notebook consumes.

---

## 1. Verdict

This is a stronger notebook than the UK-DALE one in its data-integrity instincts, and its numbers
are unusually trustworthy: **every headline quantity reproduces exactly**, including an
independent statistic that could easily have drifted (the correlation range printed as
`0.322 .. 0.946` came back `min 0.322 max 0.946`). The gap-run accounting, the plateau/phantom-
energy bookkeeping, the label audit and the per-channel floor threshold rule are all good work.

Four things keep it from being the reference document for this dataset:

1. **Its local-time caveat is self-inflicted.** The release *does* ship a local, daylight-saving-
   corrected clock. Our extractor destroys it, and the notebook then adopts a flat UTC+1
   approximation to work around the loss.
2. **The day-of-week analysis is indexed one day off**, which inverts one prose conclusion and
   silently points the behaviour section at Friday+Saturday instead of the weekend.
3. **Channel-level freezes are invisible to the mask the notebook uses.** Several canonical channels
   are 90-98% frozen value; their "measured" ON power, duty and episode counts are reported as
   appliance physics and then recommended for the gold layer.
4. **The release's own published tables are never consulted**, even though the notebook computes the
   exact matching quantities. That omission is what lets the coverage headline and the appliance
   definitional gaps go unnoticed.

Details, in severity order.

---

## 2. Reproduction

Everything below was recomputed from the parquet extract. No notebook output was trusted.

| Notebook claim | Notebook | Independent recompute | Verdict |
|---|---|---|---|
| fleet rows | 119,495,879 | 119,495,879 | exact |
| fleet energy (raw / cleaned) | 117,145 / 110,807 kWh | 117,145 / 110,807 kWh | exact |
| phantom energy on masked plateaus | 6,338 kWh (5.4%) | 6,337 kWh (5.41%) | reproduces |
| coverage range / median | 15.1-52.6% / 36.3% | 15.1-52.6% / 36.3% | exact |
| corr(agg, submeter sum), alive rows | 0.322 .. 0.946 | 0.322 .. 0.946 | **exact** |
| mean residual range, alive rows | 170 .. 548 W | 170 .. 549 W | reproduces |
| houses with a contiguous 30 d stretch | 0 of 20; best H9 22.1 d | 0 of 20; best H9 22.1 d | exact |
| fleet maximum aggregate | 68,232 W | 68,232 W | exact |
| H1: issues %, rows > 11 kW, max | 0.84%, 4,273, 29,159 W | 0.84%, 4,273, 29,159 W | exact |
| worst aggregate plateau | H10 855 h at 2,169 W | H10 855 h at 2,169 W | exact |
| "Issues decodes as submeter-sum > aggregate" | 1 / 0 split | 0 mismatches in 119,495,879 rows | exact, but documented (§4 R7) |
| **weekday kWh/day (H2)** | **Sat 9.9, Sun 11.2, Mon-Fri 10.5** | **Sat 11.2, Sun 11.4, Mon-Fri 10.16** | **wrong (§4 R1)** |
| IAM readings above 4,000 W | not tested | **0 of 1,075,462,911; max 3,975 W** | honours the release (§3) |
| published uptime (descriptor: 88% avg, H2 76%, H18 94%) | not reported | **88.0% avg, H2 76.1%, H18 94.3%** | reproduced (§5 P0) |

Row-level integrity checks worth stating explicitly, because the notebook does not claim them and
they are the strongest evidence that the fnd layer is faithful:

* **Exact row-count agreement with the published descriptor.** The paper reports "119,495,879
  timestamped readings"; our 20-house row total is exactly that. Its IAM total, 1,194,958,790 divided
  by 10 and multiplied by 9, is 1,075,462,911, and that is exactly our IAM row count. Two exact
  matches to nine significant figures is not a coincidence.
* **The 4 kW IAM ceiling is genuinely enforced.** Zero readings above 4,000 W across 1.08 billion IAM
  samples, maximum 3,975 W. The release documents this ("spikes of greater than 4000 Watts have been
  removed from the IAM values and replaced with zeros") and our extract honours it.

---

## 3. What the notebook gets right

* **Raw-fidelity contract.** No silent resampling; aggregate and submeters are compared on the same
  rows. The claim that the wide layout makes aggregate-vs-submeter auditing free is correct and is
  the notebook's best structural insight.
* **The questions-first structure, the enforced no-hard-coded-numbers rule and the
  `[insight only]` / `[collectable]` tagging** all work. The figures are legible and the summary
  JSON makes the run machine-consumable.
* **The "no contiguous 30-day recording" finding is correct and important.** Best stretch is H9 at
  22.1 days, and no house clears 30 days. This is a real constraint on windowing, correctly derived,
  and it is a stronger statement than the descriptor's own availability figure makes.
* **The plateau / phantom-energy accounting is right.** H10's aggregate holds a single value for
  855 hours and the cleaning removes 1,794 kWh from it. Both figures reproduce.
* **The label audit earns its place.** H12's "Kettle" idling at 113 W, H13's duplicate "Microwave"
  with one compressor-like channel, the four channels that go silent mid-study, and the H15 toaster
  rounding trap are all real and all correctly read off the data. The advice to trust statistics plus
  one human look per channel is sound.
* **`thr_rule='floor'` is the right threshold design** for this fleet: a per-channel floor plus a
  fraction of the observed ON level adapts to real per-home variation, and it is what makes the
  fridge/kettle families behave. Keep it.
* **The quirks section and the "mask-then-train, never smooth" verdict** are the right summaries for
  downstream training.

---

## 4. Errors, ranked

### R1 (high) - The day-of-week analysis is indexed one day off, and the weekend flag points at the wrong days

Both weekday computations use `(day_index + 4) % 7`:

```python
nd = np.bincount(((udays + 4) % 7).astype(int), minlength=7)
wk = np.bincount((day_ids + 4) % 7, weights=agg * dcap) / 3.6e6 / np.maximum(nd, 1)
...
wknd = np.isin(((ts[ons] // 86400000).astype(int) + 4) % 7, [5, 6])
```

Unix day 0 is a **Thursday**. The correct Mon=0 shift is `+3` (which is what
`eda_fnd_lib.py`'s own weekday helper uses). With `+4` the buckets are
Sun=0, Mon=1, Tue=2, Wed=3, Thu=4, Fri=5, Sat=6, so:

* every bar in the weekday chart is labelled **one day ahead** of the data it holds (index 0 is
  Sunday but is labelled "Mon"); and
* `wknd` selects indices 5 and 6, i.e. **Friday and Saturday**, not Saturday and Sunday.

Verified on House 2 (the house the prose quotes), kWh/day, all rows. The seven values are
fixed; only their labels move, so the table is indexed by bucket position:

| bucket position | 0 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|---|
| kWh/day | 11.4 | 11.0 | 9.8 | 10.5 | 9.6 | 9.9 | 11.2 |
| notebook label (`+4`) | Mon | Tue | Wed | Thu | Fri | Sat | Sun |
| true weekday (`+3`) | Sun | Mon | Tue | Wed | Thu | Fri | Sat |

Read against the correct labels: **Sunday 11.4 kWh (heaviest, so that sentence survives by luck),
Saturday 11.2 kWh, Mon-Fri mean 10.16 kWh.** The notebook's prose claim that "Saturday actually sits
below the Mon-Fri mean (9.9 vs 10.5)" is therefore **inverted** — the `9.9` it read as Saturday is
Friday, and true Saturday is *above* the weekday mean. Restricted to non-frozen rows the same
inversion holds (Saturday 11.1 vs Mon-Fri 10.06).

Impact: the `[insight only]` conclusion in the diurnal section is wrong, and every onset histogram
in the behaviour section is split on Friday+Saturday rather than the weekend.

Fix: change `+ 4` to `+ 3` in both places, and print the weekday table with day names in the same
cell that computes it so the mapping is visible in the output rather than only in the chart.

### R2 (high) - Local time is in the release; our extractor deletes it, and the notebook then approximates

The notebook states in the quirks section: "Local time is not stored; UTC+1 shift used throughout is
an approximation (UK summer time would want UTC+1, winter UTC+0)." That is **not true of the
dataset**. The release's documented record format is

```
DATETIME, UNIX TIMESTAMP (UCT), Aggregate, Appliance1, Appliance2, ..., Appliance9, Issues
```

and its headline cleaning step is, verbatim, "correcting the time for UK daylight savings". The local
clock is the release's *product*, not something it omits.

The all-null `Time` column in our parquet is caused by `src/pipelines/01_extract_dataset/extract_refit.py`:

```python
df.insert(0, 'ts_us', (pd.to_numeric(df.pop(tcol)) * 1e6).astype('int64'))
df = df.apply(pd.to_numeric, errors='coerce')     # <-- nulls the DATETIME column
```

Line 44 pops the Unix-seconds column; line 45 then coerces **every remaining column** to numeric,
which turns the datetime string column into NaN. The file's own note claims "all columns verbatim
numeric", which is the intent — it just also catches the one column that is not numeric. Measured on
the extract: `Time` is null in 119,495,879 of 119,495,879 rows; the nine measurement columns and
`Issues` are null in zero rows.

Consequences: (a) a documented, exact, DST-correct local clock is discarded and re-approximated;
(b) the diurnal profile adds a flat +1 hour, which is correct in summer and one hour wrong in winter,
so the 08:00 peak is a blend of two populations rather than a measurement; (c) the weekday
computation has to re-derive the calendar from the epoch and gets it wrong (R1).

Fix, one line: parse or drop the datetime column before the blanket coercion (e.g. select the
numeric columns explicitly, or `df = df.drop(columns=[dcol])` after capturing it). Then the diurnal
and weekday sections can use real local time, the "+1 approximation" caveat disappears, and R1 is
retired at the same time. A re-extract is required; 20 houses at ~13 s each is cheap.

### R3 (high) - The IAM spike-removal is documented, has a visible low-end signature, and is never analysed

The readme says the cleaning replaced IAM spikes above 4,000 W **with zeros**. That single sentence
explains two things the notebook reports as unexplained or misses entirely:

* **The 4 kW ceiling is active and shapes the data.** Confirmed: 0 of 1,075,462,911 IAM readings
  exceed 4,000 W; the global IAM maximum is 3,975 W. On a channel whose real draw is 4.5 kW, the
  cleaned value becomes **0 W**, which is a fabricated OFF state inside a real ON period. It splits
  episodes and corrupts the episode and dwell statistics the notebook reports per channel. This is
  the exact mirror of the UK-DALE review's E4: there the problem was spurious high IAM values, here
  it is the removal of real high values. The notebook's Q7 frames plausibility as an *upper* bound
  only.
* **Zero-blips are measurable.** Counting single-sample 0 W values that sit between two non-zero
  samples on the same channel: **961 fleet-wide**, concentrated in **House 19 Appliance7 with 588**,
  then H6 (72), H16 (35), H9 (30), H5 (26). A kettle- or dryer-class channel dropping to exactly 0 W
  for one 8-second sample and back is physically impossible; it is the fingerprint of the removal
  rule.

Fix: add a low-end plausibility gate symmetric to the existing high-end one, count and report the
zero-blips in the inventory table, and state the ceiling explicitly (the notebook's Q7 prose argues
for a ~20 kW gate on the aggregate but never mentions that the IAM channels were already clipped at
4 kW by the release). Where a channel is clipped, note that its episode statistics are lower bounds.

### R4 (high) - The gold-layer threshold table is built from contaminated medians

Q11's design table reports a median per canonical appliance and explicitly recommends adopting those
values ("[collectable]"). Rebuilding it while keeping only physically plausible channels per family
(p50 ON > 500 W and duty < 25% for microwave/dishwasher/washing machine; p50 ON < 300 W for fridge;
p50 ON > 800 W for kettle) moves the recommended numbers a long way:

| family | channels (all -> plausible) | median p50 ON, W (all -> plausible) | median threshold, W | factor |
|---|---|---|---|---|
| microwave | 17 -> **8** | 180 -> **1,186** | 90.5 -> 593 | **6.2x** |
| dishwasher | 15 -> **5** | 109 -> **2,129** | 54.5 -> 1,064.5 | **19.5x** |
| washing_machine | 24 -> **1** | 146 -> 1,371 | - | not estimable |
| fridge | 35 -> 34 | 85 -> 85 | 43 -> 42.8 | stable |
| kettle | 15 -> 14 | 2,614 -> 2,662 | 1,307 -> 1,331 | stable |
| tumble_dryer | 7 -> 6 | 2,298 -> 2,381 | - | stable |

The excluded channels are not marginal: 23 washing-machine channels sit at 73-394 W (standby, not a
wash cycle), 10 dishwasher channels at 42-118 W, and 9 microwave channels at 21-180 W. The existing
duty audit rule (`duty > 50%`) cannot separate these from legitimate slow appliances — it fires on
H6 "PGM Computer" (93.7%), H9/H17 "Television Site" (93.3% / 88.9%) *and* on genuine fridges
(H10 chest freezer 60.3%, H3 51.6%). A low-power/high-duty shape, not duty alone, is the discriminator.

The kettle family is the one that is genuinely clean: 13 of 15 channels cluster at 1,415-2,946 W with
H12's 113 W "kettle" the single outlier the notebook already flags. Credit for that catch — but the
same logic was not applied to the other five families.

Fix: gate the family medians on a plausibility predicate before recommending them, and print both the
all-channel and plausible-channel medians side by side so the sensitivity is visible.

### R5 (high) - Channel-level freezes are invisible to the mask the notebook uses

The notebook masks the aggregate on identical-value runs of 1 hour or more, and IAM channels only on
runs of **6 hours** or more. The asymmetry matters, because the per-channel detector finds a great
deal that the aggregate detector cannot see. Longest non-zero constant run on a channel **excluding**
all rows inside an aggregate freeze, per house:

| house | channel | longest frozen run | share of that channel's rows frozen and outside an aggregate freeze |
|---|---|---|---|
| H1 | Appliance9 | **3,897 h** | 90.0% |
| H9 | Appliance8 | 1,115 h | 94.4% |
| H13 | Appliance5 | 852 h | - |
| H18 | Appliance8 | 517 h | 96.4% |
| H3 | Appliance7 | 493 h | - |
| H5 | Appliance6 | 457 h | - |
| H10 | Appliance2 | 411 h | - |

Frozen-row shares surviving the 6-hour mask for canonical channels: **H13 microwave 98.5%,
H18 microwave 96.4%, H6 microwave 95.4%, H9 Hi-Fi 94.4%, H1 electric heater 90.0%, H4 microwave
82.8%, H21 vivarium 70.0%, H12 unknown 59.2%, H2 fridge-freezer 30.1%, H20 microwave 27.5%**.

House 1's Appliance9 holding one value for 162 days while the rest of the house varies is not
appliance physics; it is a stalled channel. Because the notebook's threshold rule reads each
channel's own floor and ON level, a stalled channel returns a confident-looking `p50_on_w`, duty and
episode rate — and those numbers are then reported in the Q4 inventory, used in the Q5 transferability
comparison, and recommended for the gold layer in Q11. Two of the six microwave channels that Q11
flags as sitting "below half the median" (H6 at 43 W and H18 at 180 W) are among the most heavily
frozen channels in the fleet, so the microwave pathology in R4 and the freeze pathology here are the
same defect seen twice.

Credit where due: the aggregate mask is a **good** whole-house-freeze detector. I checked the
stricter mask (all nine IAM channels *and* the aggregate constant) against the aggregate-only mask,
and the row shares agree to within 0.1 pp in every house — whenever the aggregate holds for an hour,
the whole house almost always does. The gap is that the converse fails badly: the aggregate is
healthy while a single channel is dead for months.

Fix: apply the same 1-hour run detector to every measurement channel inside the inventory pass, and
add a `frozen_pct` column to the Q4 table. Report statistics only for channels under some frozen
threshold, and mark the rest. This is cheap — the detector already exists in the notebook.

### R6 (high) - The three solar houses are never identified, and one of them sets the headline coverage floor

The descriptor's "Known issues" states plainly: "Houses' 3, 11 & 21 aggregate readings are affected
by solar panel generation as re-wiring was not possible." Its own coverage table marks those three
houses **N/A** for exactly this reason.

The notebook never mentions solar generation anywhere. House 11 supplies the headline coverage
minimum ("15-53% of mains energy", floor 15.1%), and it is one of the three houses the release says
the metric is undefined for. Solar export also depresses the aggregate, which contaminates
correlation, the residual, the seasonality panel, the spike ceiling and the plateau list. The
fleet-synchronous freeze dates and the "fleet stood still" section treat all 20 houses as comparable
when three of them are not.

Fix: add a `solar` boolean to the inventory table, exclude or explicitly annotate H3/H11/H21 in
every fleet-wide aggregate, and restate the coverage headline over the 17 comparable houses.

### R7 (medium) - The "Issues" decode is a documented definition, presented as a discovery

The notebook presents the decode as an empirical finding ("The Issues column decodes cleanly") and
then prints a pass/fail check. Both the readme and the descriptor define the column outright: the
readme says it "is set to 1 if the sum of the sub-metering (IAMs) is greater than that of the
household aggregate", and the descriptor repeats it. I verified the identity holds on **every one of
119,495,879 rows (zero mismatches)** — so the decode is exactly right, and it is worth stating as a
*verification* of documented behaviour, which is genuinely useful. What it must not be is a
"discovery", and the accompanying check is a tautology: the `PASS['flag']` split compares the sign of
`aggregate - submeter sum` on rows selected *by* that sign. It cannot fail.

Fix: cite the readme, relabel the section as confirming the documented flag, and keep the 0-mismatch
row count because that number *is* informative. Drop the 100%/0% "clean vs flagged" print, or reframe
it as the definition being self-consistent.

### R8 (medium) - Coverage is not reconciled with the published definition, and ours sits systematically below it

The descriptor reports "% Captured by sub-metering" per house. Ours against it, 17 comparable houses
(the three solar houses are N/A in the paper):

| house | 1 | 2 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 12 | 13 | 15 | 16 | 17 | 18 | 19 | 20 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| paper % | 35 | 33 | 48 | 48 | 40 | 46 | 22 | 38 | 43 | 36 | 48 | 36 | 37 | 45 | 55 | 35 | 46 |
| ours % | 32.7 | 30.6 | 46.4 | 36.9 | 38.4 | 38.0 | 20.1 | 35.8 | 34.3 | 28.2 | 42.4 | 32.8 | 37.2 | 43.6 | 52.6 | 29.6 | 44.8 |
| delta | -2.3 | -2.4 | -1.6 | -11.1 | -1.6 | -8.0 | -1.9 | -2.2 | -8.7 | -7.8 | -5.6 | -3.2 | +0.2 | -1.4 | -2.4 | -5.4 | -1.2 |

Mean ours **36.7%** vs paper **40.6%**; median 36.9% vs 40.0%; mean absolute difference **3.9 pp**.
Sixteen of seventeen are below the published value. The descriptor also states the fleet-level
result as "up to 55% of consumed energy can be attributed to appliances monitored via appliance
plugs", whereas the notebook's headline is "only 15-53%".

Most likely mechanism, and it is testable: the release forward-filled NaN with the last value, so a
period in which an IAM stopped reporting contributes its stale value (usually 0) to the numerator
while the aggregate keeps accumulating in the denominator. That deflates our percentage relative to a
definition computed over rows where the IAMs were reporting. The two worst gaps (H5 -11.1 pp,
H10 -8.7 pp) are both houses with heavy aggregate plateaus (H10 is the 855-hour house), which is
consistent.

Fix: state the definition used, reconcile against the published column, and report both numbers.
A four-percentage-point systematic offset is worth a sentence, not silence.

### R9 (medium) - The descriptor's published tables are never consulted, which is what hides the appliance-level definitional gaps

The notebook computes per-appliance use counts, energy and channel inventories — the same quantities
as the descriptor's Tables 3, 4 and 6 — and never compares. Two comparisons are worth making:

**Use counts (uses per appliance per day, ours over ~730 days divided by the descriptor's):**
washing machine **28.7x**, tumble dryer **20.1x**, dishwasher **6.2x**, microwave 2.1x, fridge 1.5x,
kettle 1.4x. The descriptor documents its method — "To estimate the number of uses per appliance,
edge detection was used", and for fridges a "use" is one cooling cycle (motor start to wind down).
Our washer and dryer counts are episode counts from a floor-based threshold, so a dryer that cycles
its heater on and off dozens of times per load counts as dozens of uses. Neither number is wrong;
they are different definitions, and the notebook should say which one it is producing, because
"episodes per day" is exactly the kind of number that gets carried into a training target.

**Energy per appliance (ours / descriptor):** fridge **0.46x**, dishwasher 0.76x, washer 0.97x,
dryer 1.14x, kettle 0.94x, microwave 1.16x. Four of six within +/-20% is a genuine integrity credit.
The fridge gap is large and the direction is the one the freeze analysis predicts (fridges are the
most-freezing family and 16 of 35 fridge channels record samples above 3,000 W). Worth reconciling
rather than ignoring.

**Inventory (descriptor Table 3 vs `data/gold/appliance_map_refit.json`):** washing machine 20 = 20,
dishwasher 15 = 15, electric heater 4 = 4 all match. Differences: cold appliances 36 vs 35,
kettle 16 vs 15, microwave 16 vs 17, tumble dryer 10 vs 7, washer-dryer 2 vs 4. The tumble-dryer
and washer-dryer gaps are label swaps (the release metadata calls H1's and H8's appliance a "Washer
Dryer" where the paper says "Tumble Dryer"), and H13 is a genuine double-assignment. The descriptor's
own Table 6 is internally inconsistent with its Table 3 on cold appliances (33 vs 36), so treat these
as definitional noise to be documented, not as errors to be chased.

A concrete, cheap validation the descriptor offers and the notebook skips: its Table 4 compares
utility-meter consumption against monitored consumption for nine house-intervals. Our monthly
aggregates reproduce those intervals exactly, so this is a ready-made external check of the whole
pipeline.

Fix: one reconciliation subsection with a table per descriptor table, listing match / definitional
difference / genuinely unexplained. This is the single highest-leverage addition to the notebook.

### R10 (medium) - The correlation statistic is resolution-insensitive and flatters the alignment; the change correlation is the informative one

The notebook's `r` is `corrcoef(agg[alive], sub[alive])` on raw 8-second rows, and it reports
0.322 .. 0.946. I reproduce that range exactly. But the level correlation is dominated by the slow
component that both series necessarily share — the overnight floor and the daily envelope are in both
by construction — so it barely responds to resolution. The quantity that actually tests "does the
submeter sum decompose the aggregate row by row" is the correlation of the **changes**:

| statistic | 8 s rows | 60 s means |
|---|---|---|
| corr(levels) | mean 0.632 (0.322-0.946) | mean **0.638** (0.341-0.958) |
| corr(changes) | mean **0.365** (0.167-0.699) | mean **0.583** (0.248-0.886) |

Pooling to one minute raises the change correlation by about 1.6x while leaving the level correlation
flat, which is the cleanest evidence in this dataset for the notebook's own recommendation to work at
a coarser resolution. It also reorders the houses: the worst house by level correlation is H11
(0.322, a solar house), but by change correlation it is H1 (0.167) — a house with a healthy-looking
0.425 level correlation and the stalled channel from R5.

The claim in the "one clock" section that per-row arithmetic is trustworthy is *arithmetically*
correct — the rows are aligned, and no resampling is needed. But the notebook should add the caveat
that the descriptor documents a residual reporting-time offset ("most IAMs should lead the aggregate
by 2 or 3 readings at most"), and that at the row scale the two streams only co-move weakly.

Fix: print both statistics, and state the recommendation as "compare at 1 minute or coarser".

### R11 (medium) - Q7 checks plausibility on the aggregate only

Q7 is titled "sentinels, nulls, and impossible spikes" and concludes that the cleaned columns are
hygienic. It tests the aggregate's upper tail and its null count. It never tests the IAM channels,
which visibly contain the same pathology: channels whose maximum exceeds 3,000 W number 16 of 35
fridges, 15 of 24 washing machines, 11 of 15 dishwashers, 10 of 15 kettles, 11 of 17 microwaves and
4 of 7 dryers; the global IAM maximum is 3,975 W. A 3,969 W reading on a fridge is physically
impossible. The descriptor bounds IAM errors at "less than 0.004% of total IAM readings" with "an
average of only 215 errors per IAM", i.e. roughly 43,000 readings across our fleet — a bound the
notebook could test and does not.

Combined with R3, the complete picture is: the IAM channels have both an uncorrected high-end
problem and a release-introduced low-end problem, and the notebook's hygiene section sees neither.

### R12 (medium) - The plateau mechanism is asserted, not sourced, and the exact alternative is on disk

The notebook calls the plateaus a "frozen meter" with no citation. The release documents the actual
mechanism: the cleaning forward-filled NaN values, and the descriptor's technical validation warns
that "in some cases, the power will remain static (originally NaN values which have been forward
filled) for a long period of time due to a connection loss that caused a lack of updates", with NaN
at 6.4% of readings and uptime at 88% on average.

This matters beyond attribution, because the **non-forward-filled raw variant is already on disk**
(`data/raw/REFIT/Processed_Data_CSV.7z`) and has never been used. It would turn the plateau
heuristic into an **exact** forward-fill mask: every static run would be a run that was NaN in the
raw file, with no detection rule and no threshold to justify. That is a materially better mask than
any identical-value heuristic, and the notebook's central data-quality claim currently rests on the
heuristic.

Also worth noting: the notebook's own null-free finding is the *other side* of the same fact. The
"no nulls anywhere in the cleaned measurement columns" reading is correct as stated, but it is not a
hygiene property of the data — it is the forward-fill. The descriptor puts the underlying null rate
at 6.4%.

The plateau mechanism was also verified to be whole-house in at least the worst case: for H10's
855-hour run (2014-02-28 21:28:09 to 2014-03-31 16:51:32, 439,731 rows, all nine IAM channels at
exactly one value each for the entire window), the aggregate is one constant value after the start.
Rows continue at the nominal cadence carrying no measurement. So the notebook's "the rows exist on
one clock but the measurement is frozen" reading is right; only the cause is unsourced, and the
sentence in cell 20 that reports both "EXACTLY constant" and "unique values = 1515" is
self-contradictory because the window it prints includes 12 hours of pre-plateau lead-in.

### R13 (medium) - The stated freeze durations match neither the code nor any printed output

The fleet-synchronous freeze section says 2014-08-30 lasted "~9 h" and 2014-08-01 "~2 h". The
constants in the notebook are `FREEZE_W = [(1409400259 * 10**6, 10), (1406913138 * 10**6, 4)]`, i.e.
10 hours and 4 hours. No cell prints either duration, so the two prose numbers are hard-coded
assertions that contradict the code that produced the figure. Under the repo's own
no-hard-coded-numbers rule this is exactly the failure mode the rule exists to prevent.

Fix: print the measured plateau length for both windows and let the prose read off the printed value.

### R14 (medium) - Citation venue is wrong

The header cites "(Murray et al., *LBNL*, 2017)". The correct reference, confirmed against Crossref,
is Murray D., Stankovic L., Stankovic V., "An electrical load measurements dataset of United Kingdom
households from a two-year longitudinal study", ***Scientific Data* 4, 160122 (2017)**, DOI
10.1038/sdata.2016.122 (PMID 28055033). Worth fixing in both the header and the provenance section,
since the provenance section is what a reader will cite.

### R15 (low) - Smaller defects

| # | where | issue |
|---|---|---|
| a | cell 14 | the same four-line paragraph appears verbatim twice |
| b | quirks | "3 dead + 3 truly-all-zero channels in H12" describes the same three channels twice; H12 has three all-zero channels |
| c | quirks | H13's 1,521 W "Freezer" `p50_on` outlier (against a fridge family median of 85 W) is the same channel that goes silent on 2014-08-18; the notebook reports both facts in different sections and never links them |
| d | Q11 table promises "dwell" but the three panels are `p50_on_w`, `duty_pct`, `eps_per_day`; `dwell_p50_s` is computed in the pass but never plotted |
| e | Q4 | tumble dryer is counted as 7 channels in 7 houses via a label-substring patch, because the gold map has no canonical tumble-dryer type; the descriptor lists 10. Disclose the patch and the count it produces |
| f | TL;DR | "house 14 dropped out of the trial and was replaced by house 21" is unsourced narrative; the release documents only that house 14 is skipped |
| g | quirks | H15's toaster is called a "rounding trap (0.04% non-zero)" and then kept in the signature gallery, where it shows nothing |
| h | Q8 | the notebook's own coverage/stretch statistic is not compared with the descriptor's published uptime; see §5 |
| i | provenance | no cross-reference to `01_ukdale_eda.ipynb`; the two notebooks are meant to be read together, and the coverage contrast (REFIT 36% vs UK-DALE house 1 at 86.9%) is the single most useful cross-dataset fact available |

---

## 5. Missing analyses, ranked by value

### P0 - Exact local time, via a one-line extractor fix

Covered in R2. This is the highest-value change in the review because it is one line of pipeline
code that deletes an entire class of approximation and a whole error (R1) with it.

### P0 - Reconcile with the descriptor's published tables

Covered in R8/R9. The notebook already computes Table 3, 4, 5 and 6 quantities. A single
reconciliation subsection with one row per published number (match / definitional difference /
unexplained) converts this from a self-consistent notebook into a citable reference on the dataset,
and it is the check that surfaces the fridge energy gap and the use-count definitional gap.

### P0 - The descriptor's uptime, which our data reproduces exactly

The descriptor reports data availability as "uptime": time between gaps longer than one hour,
normalised by monitoring duration, with "average 88%", "House 2 lowest at 76%", "House 18 highest at
94%". Computing it on our aggregate — sum of inter-sample intervals of at most one hour, divided by
`ts_last - ts_first` — gives:

* **fleet mean 88.0%** (descriptor: 88%)
* **House 2: 76.1%** (descriptor: 76%, the documented minimum)
* **House 18: 94.3%** (descriptor: 94%, the documented maximum)

That is a three-way exact reproduction using a definition the notebook does not implement, and it is
strictly better than the notebook's current stretch statistic for cross-paper comparison. It belongs
in the inventory table next to `issues_pct`, and it also gives the "no 30-day stretch" finding a
published companion (the two are not contradictory: short gaps and long gaps are different
questions).

### P0 - A per-channel freeze mask, applied before any channel statistic

Covered in R5. The detector already exists; it needs to be pointed at the nine IAM channels and its
output surfaced as a column.

### P0 - The IAM low-end gate and the descriptor's IAM error allowance

Covered in R3 and R11. Count the zero-blips, bound the IAM maxima against a per-appliance physical
ceiling, and check the descriptor's own "<0.004% of IAM readings" claim.

### P1 - Compare at 1 minute and report the change correlation

Covered in R10. The notebook's recommendation to work at a coarser resolution is right; the statistic
that demonstrates it is the change correlation, and it currently is not computed.

### P1 - A solar flag, carried through every fleet table

Covered in R6.

### P1 - Per-appliance transition steps across houses

The verdict promises the notebook is "the best source of 'same appliance, different homes' priors
this project has", and the Q5 transferability section starts towards it, but the fleet never gets the
one statistic that would deliver it: the distribution of step magnitude (delta-P) at each
appliance's ON transition, per house, per canonical family. ON power alone conflates a kettle's
single 3 kW step with a washing machine's dozens of small ones. The UK-DALE review asked for the same
thing on a single house; here it is available across twenty, which is the entire point of the
dataset. `channel_stats` already computes ON power per channel, so this is a modest addition.

### P1 - Event-level simultaneity across the fleet

The summary JSON carries a single fleet number (3.9% of buckets with two or more appliances on).
The UK-DALE analysis showed this bucket statistic badly undersells the confound; the informative
version is per-appliance event co-occurrence (which there ran 48-56% for the big four against 6.7%
for the fridge). With twenty houses this is a cheap and highly quotable table.

### P2 - Use the non-forward-filled variant to make the plateau mask exact

Covered in R12.

### P2 - Re-derive channel statistics on non-frozen rows and publish the delta

Once the freeze mask exists (P0), the interesting output is the difference between statistics with
and without it, per canonical family. For H13/H18/H6 microwaves that difference is the whole
statistic.

---

## 6. Suggested order of work

| order | change | effort | payoff |
|---|---|---|---|
| 1 | extractor: stop nulling the datetime column, re-extract, switch diurnal/weekday to real local time | one line + 5 min | retires R2, R1, and the largest caveat in the notebook |
| 2 | weekday/weekend index `+4` -> `+3` | one character | fixes an inverted conclusion and a wrong behaviour panel |
| 3 | per-channel 1 h freeze mask; `frozen_pct` in the inventory table | small | retires R5, de-contaminates R4 |
| 4 | plausibility-gated family medians in the gold-layer table | small | retires R4, the wrong 6-20x thresholds |
| 5 | descriptor reconciliation subsection (Tables 3-6 + uptime) | medium | turns the notebook into a citable reference; surfaces R8, R9 |
| 6 | solar flag through all fleet tables | small | retires R6 |
| 7 | change correlation + 1-minute agreement, alongside the existing `r` | small | retires R10; makes the resolution recommendation evidence-backed |
| 8 | IAM low-end gate and zero-blip count | small | retires R3, R11 |
| 9 | cite the readme for the Issues column and the 4 kW ceiling; fix the citation; print freeze durations; dedupe cell 14 | small | retires R7, R12, R13, R14, R15 |

Items 1-4 are the ones I would not ship the notebook without: they change numbers that are
recommended for the gold layer, not just prose.
