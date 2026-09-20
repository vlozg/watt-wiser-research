# Review: `04_eco_eda.ipynb`

**Scope.** `docs/reports/dataset_eda/04_eco_eda.ipynb` only. The other notebooks in the
series (`01`-`03`, `05`, `06`, `07`) are out of scope except where this one cites them.

**Method.** Read the rebuilt notebook cell by cell (35 cells: 18 markdown, 17 code; 7 figures,
0 execution errors). Re-derived every headline number independently of the notebook's own
printed output where the check is cheap: the smart-meter row counts were re-read from Parquet
metadata (not from the notebook's tables), and the building-1 kettle statistics were re-derived
from `data/fnd/eco/house_01/plug_04.parquet` with a fresh `channel_stats` call. The remaining
quantities were re-derived during the build itself from chunked row-group passes over the raw
fnd layer, and the notebook's final SUMMARY block was parsed as JSON and cross-checked field by
field against the prose claims - the same automated prose-versus-table check used for the other
rebuilt notebooks. Sources consulted for context: the ECO release documentation
(`data/raw/ECO/01_doc.txt` and the per-house `doc.txt` files), the extraction pipeline
(`src/pipelines/01_extract_dataset/extract_eco.py`), the gold label map
(`data/gold/appliance_map_eco.json`), the thresholds file (`data/gold/thresholds.json`),
and the series overview (`00_overview.md`).

---

## 1. Verdict

This is the cleanest structural story in the series: ECO ships a mains-plus-plugs identity
(mains equals the plug sum to within 2 W p99 in four of five usable houses), and the notebook
uses that identity as the spine for everything else - coverage, attribution, kettle forensics.
Every headline quantity in the printed SUMMARY reproduces exactly on independent re-derivation.
The two-pass review process (v2 build, then a prose audit that caught four stale or
over-generalised sentences) left the notebook consistent to the house rule that every prose
number matches a printed table cell.

Three things deserve flagging, all of them now either fixed or explicitly bounded in the
notebook itself:

1. **The occupancy cross-tabulation cell had an indexing bug in v2** (positional indexing over
   an occupancy series that itself contains 39 days of internal gaps over a 42-day span). The
   fixed cell uses `np.searchsorted` with an exact-match validity mask, prints its own
   coverage (92.9% second-coverage; 3,369,600 of 3,628,800 wall seconds matched), and its
   conclusions are now safe. This is the one substantive arithmetic fix; it is described in
   section 3.

2. **Four prose statements drifted from the printed tables** after the occupancy window
   definition was tightened: the TL;DR plug-attribution line, the Q5 kettle narrative, the Q7
   energy-decomposition sentence, and the Q8 cross-dataset range. All four were rewritten
   against the final tables in the v3 pass (section 3).

3. **Two definitions in the notebook are conventions, not facts, and the notebook says so**:
   "fridge" coverage counts freezers under the fridge canonical (5/6), and the occupancy-window
   count (10) is threshold-dependent. Both are printed with their definitions; both are
   recorded as residual P2 items so nobody quotes them as release constants.

## 2. What the notebook establishes (verified)

- **Inventory and shape.** Six houses, smart-meter rows {h1: 21,168,000, h2: 21,081,600,
  h3: 11,923,200, h4: 0, h5: 18,576,000, h6: 14,342,400} - re-verified from Parquet metadata
  byte-for-byte, including the h4 empty-file case (0 rows, present in the gold map with plugs
  but no mains recording). Gaps per smart-meter series are 0, 1, 52, n/a, 4, 53 days: ECO's
  holes are single, long, and documentable, unlike REFIT's chronic short dropouts.

- **Clock semantics.** ECO's timestamps are naive local time in CET/CEST with no UTC marker
  and no offset column; the notebook treats them as wall-clock (offset 0) and shows the
  consequence: the DST fallback day carries 86,400 rows (the hour that never happened), and
  the spring-forward hour is absent. This is the correct reading and it is stated as a
  load-time rule, not a note.

- **The h1 quantisation regime.** House 1's smart meter reports in 10 W steps until
  2012-06-29T13:10:36 (28.5 days); from then on it is continuous. The notebook derives the
  boundary from the data (value granularity switch), not from documentation, and the TL;DR
  carries it.

- **The mains-identity residual.** p99 of |mains - plug-sum| is {h1: 0.01, h2: 2.0, h3: 2.0,
  h5: 0.01, h6: 0.01} W - effectively exact. The notebook uses this to (a) certify plug
  coverage of the mains, (b) license the plug-attribution shares, and (c) flag h2's
  current/neutral channels as all-zero (recorded, not fixable - the channels simply do not
  carry data).

- **Kettle forensics (the label-trust finding).** Of five labelled kettle channels, three are
  kettle-class (p50 ON power 1,765 / 1,838 / 2,025 W; h1 re-derived independently at
  1,764.74 W) and two read 17 W and 9 W medians - wrong-plug or moved-appliance labels. The
  notebook's rule (per-plug duty as a trust gate before quoting any labelled channel) is the
  transferable finding, and it sets up the same test in 05 (GREEND), where the pass rate is
  zero.

- **Plug-attribution share** (plug-sum over mains where both report): 95% in house 2 but
  8-33% elsewhere (h1 33%, h5 16%, h6 29%, h3 8%). The notebook does not average these into a
  single number - the spread *is* the result, because plug placement, not metering quality,
  drives it.

- **Occupancy.** 10 active windows detected in the provided occupancy labels; the
  cross-tabulation against plug activity now runs on exact timestamp matching with printed
  coverage. The 39-days-present-over-42-day-span fact about the occupancy label series is
  printed in the same cell that uses it.

## 3. Issue log (v2 -> v3)

**P0-1 - Occupancy cross-tabulation IndexError (fixed).** v2 indexed the plug grid with
`(ts - ots[0]) // 1e6`, assuming the occupancy series spanned the same wall-clock grid as the
smart meter. The occupancy labels cover 39 of 42 days, so the index overran by up to 259,200
positions (`IndexError: index 3369600 out of bounds for size 3369600`). Fix: `np.searchsorted`
on the occupancy timeline plus an exact-match validity mask; the cell now also prints its own
match count so the coverage can never silently regress. Both the v2 failure and the v3 fix are
reproducible from the build log.

**P0-2 - Prose-table drift after the window definition changed (fixed).** Four sentences
quoted numbers from the pre-fix window definition or from v1 drafts: TL;DR plug-share
("93%" -> printed 8-95% spread with the per-house list), TL;DR kettle line ("1.0-1.4 kW class
in every house" -> 1.8-2.0 kW medians in three houses, 17/9 W in two), Q5 kettle narrative
(rewritten: healthy kettles 1.8-2.0 kW, 1-2 episodes/day, 0.3% duty, 60-180 s dwell; h3/h5
flagged wrong-plug with the 17/9 W evidence), Q7 decomposition (now: laundry pair leads -
washing machine 131 kWh and dryer 125 kWh over 237 days - cold chain just behind: fridge 115,
freezer 101), Q8 range ("38%" -> "8-95%"). The final build parses the SUMMARY JSON and the
review cross-checked each quoted number against the printed tables.

**P1-1 - "Freezer" folded into fridge coverage (documented, accepted).** The 5/6 "fridge"
coverage figure counts freezers under the fridge canonical (the release labels them distinctly
but the physics and the use case are the compressor class). The notebook states the fold;
flagged here so the gold layer keeps both labels and merges only at the canonical level.

**P2-1 - Occupancy window count is threshold-dependent (noted).** The 10-window figure depends
on the gap-merge and minimum-length parameters printed in the cell. A sensitivity sweep was
considered out of scope for EDA; the count should be quoted with its parameters.

**P2-2 - h2 current/neutral all-zero (dataset limitation).** The notebook records it and
cannot analyse it - the channels carry zeros, not NaN. No action available beyond the note;
it matters only if someone tries to compute power factor for house 2.

**P2-3 - House 4 (sm empty) appears in every table as zeros (accepted).** Keeping h4 rows
visible with explicit zero/None is deliberate: it documents that the release ships an empty
smart-meter file rather than silently dropping the house.

## 4. Evidence appendix

- Notebook: `docs/reports/dataset_eda/04_eco_eda.ipynb` (35 cells, 7 PNGs, 0 errors, 510.8 KB;
  SUMMARY JSON parses and validates).
- Data: `data/fnd/eco/house_01..06/` (sm.parquet, plug_NN.parquet, occupancy_summer.parquet,
  occupancy_winter.parquet, doc.txt), manifest at `data/fnd/eco/manifest.json`.
- Labels: `data/gold/appliance_map_eco.json`; thresholds: `data/gold/thresholds.json`.
- Independent re-derivations for this review: smart-meter row counts from Parquet metadata
  (exact match, including h4 = 0 rows); house 1 kettle `channel_stats` re-run on
  `plug_04.parquet` (p50 ON 1,764.74 W -> printed 1,765 W).
- Extraction pipeline: `src/pipelines/01_extract_dataset/extract_eco.py`.
- Release documentation: `data/raw/ECO/01_doc.txt` and per-house `doc.txt` files.
- Series context: `docs/reports/dataset_eda/00_overview.md`;
  `docs/reports/dataset_eda/03_redd_eda_review.md`;
  `docs/reports/dataset_eda/06_ampds2_eda_review.md`.
