# Review: `05_greend_eda.ipynb`

**Scope.** `docs/reports/dataset_eda/05_greend_eda.ipynb` only. The other notebooks in the
series are out of scope except where this one cites them.

**Method.** Read the rebuilt notebook cell by cell (33 cells: 19 markdown, 14 code; 6 figures,
0 execution errors). Re-derived the headline numbers independently of the notebook's own
printed output where the check is cheap: the dead-column census was re-run as a fresh
early-exit scan over all 75 plug columns of all eight buildings (read row-group by row-group,
stop at the first non-NaN value), the year-2000 timestamp runs were re-read from the raw
`ts_us` columns of `building4.parquet` and `building5.parquet`, and the inventory row
counts were re-read from Parquet metadata during the build. The final SUMMARY block was parsed
as JSON (24 keys) and cross-checked field by field against the prose claims - the same
automated prose-versus-table check used for the other rebuilt notebooks. Sources consulted for
context: the extraction pipeline (`src/pipelines/01_extract_dataset/extract_greend.py`), the
gold label map (`data/gold/appliance_map_greend.json`), the vendored GREEND metadata README,
the thresholds file (`data/gold/thresholds.json`), and the series overview (`00_overview.md`).

---

## 1. Verdict

This is the series' **label-trust notebook**, and the rebuilt version makes that case with
evidence instead of anecdotes: a physics-verdict table over 25 labelled canonical channels in
which *not one* of the four labelled kettle channels behaves like a kettle, a supervision-hole
taxonomy that separates MAC-only, dead-labelled and multi-label columns, and a clock census
whose garbage is informative (year-2000 runs of honest 1 s ticks, not scattered corruption).
Every headline quantity in the printed SUMMARY reproduces exactly on independent
re-derivation, and the house rule (every prose number matches a printed table cell) holds
across the final build.

Three review findings were fixed during the rebuild and are described in section 3; the most
interesting is that the dead columns are **NaN-valued, not null-valued**, which makes them
invisible to Parquet statistics and to any null_count-based ingestion QA - a finding the
notebook now states and encodes as a SUMMARY quirk.

## 2. What the notebook establishes (verified)

- **Inventory and shape.** Eight buildings, 196,943,999 rows, 75 plug columns in one wide
  Parquet per building (a `ts_us` column plus one column per raw plug MAC in the
  building-wide union), spans 290-499 days - the longest continuous coverage in the suite and
  the only dataset here with full-season spans. **No mains channel exists anywhere.** Labels
  attach positionally (meter k = k-th MAC column); 67 columns carry labels, 8 are MAC-only
  aggregates the paper left unlabelled.

- **Clock semantics.** Timestamps are UTC microseconds. The garbage is one phenomenon:
  1,062 rows sit in two short year-2000 runs (b4: 311 rows, 2000-01-01 00:26:21-00:42:48 UTC,
  median step 1.00 s; b5: 751 rows, 04:11:34-04:26:09 UTC, median step 1.01 s) - plug clocks
  that woke at their power-on default and ticked honestly until the first gateway sync - plus
  2 NaN-timestamp rows. A `ts > 2010` filter drops 1,064 of 196.9M rows (0.0005%): the only
  cleaning the clocks need. The timezone proof: b2's plug-sum by Europe/Rome local hour peaks
  at hour 18 (626 W) while naive-UTC bucketing peaks at hour 16 (638 W), evening band
  18-22 = 542 W local vs 445 W naive - a two-hour smear exactly as CEST dominance predicts.

- **Cadence.** Nominal 1 Hz, wireless-jittered: dt median 1.00-1.09 s per building, p1 as low
  as 0.54 s, p99 to 12.75 s; b6 ships 23,671 gaps over 60 s against b0's 3. The Q3 ECDF
  (local-time axis) and the gap census make the delivery story checkable.

- **Values are clean but sparse.** No negative samples; the per-building minimum reads 0.0 W
  in a printed column; worst live-column NaN runs to 47.49% (b3) and 86.88% (b7); five columns
  are fully NaN. The energy wedge: per-plug own-mean upper bounds 1.59 (b1) to 9.22 (b2)
  kWh/day vs b2's honest row-level simultaneous sum of 8.07 - the wedge is joint plug-offline
  time, i.e. the uptime measurement.

- **Supervision holes, three species (verified by independent scan).** (1) 8 MAC-only columns
  (b1: 1, b4: 2, b5: 3, b7: 2); (2) **5 fully dead columns - b4 m10 and m11 (MAC-only) and,
  in b6, three labelled ones: the electric space heater (m4), the laptop (m6), and the
  building's only fridge channel (m9)** - a labelled channel with zero data is a supervision
  hole, not supervision; (3) 8 multi-label meters carrying 2-3 devices each (e.g. b3 m2 =
  UPS + games console + computer), which make any per-channel prior ambiguous by construction.

- **Canonical coverage and verdicts.** Washing machine 8/8, fridge 6/8 (but b6's is the dead
  channel, so 5/8 live), dishwasher 6/8, kettle 4/8, microwave 1/8. The verdict table (25
  channel rows) is the deliverable: kettle verdicts are near-dead/standby-plateau/episodic
  (b0 reads a 70-100 W plateau at 57.8% duty, max 296 W - network-equipment physics; only b2
  shows kettle-class maxima, 3,043 W at 7.0% duty); b0's washing machine never exceeds 13 W;
  b1's is a noise-storm (73.9 episodes/day); b3 and b6 washing machines are genuinely
  heater-class (p50 ON 1,974 W and 1,805 W); the fridge picture runs from textbook (b2:
  p50 ON 390 W at 37.9% duty) to empty (b6); and even the single microwave channel (b2) is a
  noise-storm (194 episodes/day), not clean transients.

- **Rhythms.** b2's weekly trace shows strong daily structure under 1 kW typical; the b6
  washing-machine zoom resolves the heater step at raw wireless cadence (onset value 1,964 W,
  window peak 1,981 W, pre-window median 0 W) - second-scale event onsets survive this
  collection, which is why GREEND stays useful for event-based priors despite the label
  verdicts.

- **Gold-layer items (Q8).** Ship physics-verdict flags with every label; store pseudo-mains
  as an explicit lower bound (8.07 vs 9.22 kWh/day for b2 printed side by side); fix clock
  semantics once (UTC + drop ts <= 2010 + Europe/Rome for local features); encode the
  supervision-hole taxonomy as a per-channel state; use GREEND for span and seasonality, not
  for supervision.

## 3. Findings and fixes during review

1. **P0 (fixed in build): dead-column detection silently returned nothing.** The v2 build
   detected dead columns from Parquet row-group statistics (`null_count`), which printed
   empty "dead" cells across Q1 and Q5. Root cause: GREEND's plug columns store **NaN values,
   not nulls** (verified: every b6 column reports null_count 0, yet three of them are 100%
   NaN by content). The final build detects dead columns by scanning column data with an
   early-exit per row group, prints the actual meter ids (b4: m10, m11; b6: m4, m6, m9), and
   computes the SUMMARY `dead_cols` field instead of hard-coding it.

2. **P0 (fixed in build): the year-2000 census told the wrong story.** The v2 prose claimed
   1,063 rows stamped at exactly 2000-01-01T00:00:00.000000. Equality matching found **zero**
   rows at that sentinel; the real population is 1,062 rows in two buildings forming short
   continuous runs that advance at ~1 s steps from the 2000-01-01 power-on default until the
   first gateway sync (b4: 311 rows over 16.4 min; b5: 751 rows over 14.6 min). The census
   cell, TL;DR bullet, Q2 reading block, Q8 item 3 and the SUMMARY quirks were all rewritten
   to the printed story (runs with ranges and median steps; 1,064 total dropped).

3. **P1 (fixed in build): unbacked minima and low-end sparsity claims.** "No negatives, min
   0.0 W in every column" had no printed backer; the Q4 table now prints a **min W (any col)**
   column (0.0 in all eight buildings) and a **cleanest col NaN %** column (0.02-1.41%), and
   the unbacked "0.3-28 percent" TL;DR range was replaced by the printed worst-column range
   (up to 47.5%, b3).

4. **P1 (fixed in build): Q6/Q7 prose drift against the verdict table.** The v2 prose called
   b5's washing machine a noise-storm; the table reads episodic high-power (11.7 episodes/day)
   - rewritten. The Q7 zoom print showed only the window-end value (71 W), which could not
   back the "~1.8 kW step" claim; the print now shows the onset value (1,964 W), window peak
   (1,981 W) and pre-window median (0 W), and the prose references them.

5. **P2 (residual, documented in-notebook): `worst col NaN %` rounds 99.99+% to 100.00.**
   b5's worst live column prints 100.00 without being fully NaN (its dead list is empty;
   Q1's ids are the authority). Two decimals were adopted to make the distinction visible, but
   a reader diffing Q1 against Q4 at face value should read Q1 as definitive.

6. **P2 (residual, now a SUMMARY quirk): NaN-valued columns are invisible to Parquet
   statistics** (`null_count = 0` on a column that is 100% NaN). Any ingestion QA that relies
   on statistics rather than content will miss the five dead columns - the notebook's
   dead-scan is the pattern to copy.

## 4. Prose-versus-table audit

Final pass: every quantitative sentence in the TL;DR, the Reading-it blocks, and the Q8 gold
list was checked against a printed table cell or SUMMARY field. All match. The numbers quoted
most likely to be reused elsewhere:

| claim | printed source | re-derived |
| ----- | -------------- | ---------- |
| 5 fully dead columns (b4 m10+m11; b6 m4, m6, m9) | Q1/Q5 tables + SUMMARY `dead_col_ids` | independent early-exit scan, exact match |
| 1,062 year-2000 rows (b4: 311, b5: 751) + 2 NaN = 1,064 dropped | Q2 census + run prints | fresh ts re-read of b4/b5, exact match |
| min 0.0 W, no negatives | Q4 min W column | printed per building |
| kettle labels 0/4 physics-clean; b6 fridge EMPTY | Q6 verdict table | channel_stats during build, table exact |
| b2 energy wedge 8.07 vs 9.22 kWh/day | Q4 table + TL;DR | printed exact |

## 4b. Evidence appendix

- Independent dead-column scan (fresh process, early-exit per column over all row groups):
  b0-b3, b5, b7: none; b4: m10, m11 (MAC-only); b6: m4 (electric space heater), m6 (laptop
  computer), m9 (fridge) - all NaN-valued, null_count 0.
- Independent year-2000 run probe: b4 311 unique-ish stamps from 946686381497298 to
  946687368221734 us (2000-01-01 00:26:21-00:42:48 UTC), median step 1.00 s; b5 751 stamps
  from 946699894990713 to 946700769116669 us (04:11:34-04:26:09 UTC), median step 1.01 s.
- SUMMARY block: 24 keys, parses as JSON; `dead_cols = 5`, `dead_col_ids`,
  `rows_dropped_by_ts2010 = 1064`, `bad_ts`, `canonical_coverage` (WM 8/8, fridge 6/8,
  DW 6/8, kettle 4/8, microwave 1/8), `quirks` (8 entries incl.
  `dead_cols_are_nan_values_not_nulls`, `uninitialized_clock_year2000_runs_b4_b5`,
  `b6_fridge_channel_empty`) all agree with the prose.
- Notebook stats: 33 cells (19 markdown, 14 code), 6 figures, 0 errors; series context:
  01 (UK-DALE), 02/02b (REFIT), 03 (REDD), 04 (ECO), 06 (AMPds2), 07 (synthetic).
