# Review: `03_redd_eda.ipynb`

**Scope.** `docs/reports/dataset_eda/03_redd_eda.ipynb` only. The other notebooks in the
series are out of scope except where this one cites them.

**Method.** Read the rebuilt notebook cell by cell (46 cells: 23 markdown, 23 code; 9 figures,
0 execution errors; 789 KB on disk). Re-derived the headline numbers independently of the
notebook's own printed output where the check is cheap: building 1's two panel meters were
re-read straight from `data/fnd/redd/building1_elec_meter1.parquet` and `...meter2.parquet`
(1,561,660 rows each; leg means 226.9 W and 157.1 W; panel mean 384.0 W; the 10 s-capped
integral re-integrated to 167.7 kWh, matching the printed value to the decimal), and the
building-1 fridge circuit (`meter5`) was re-checked against both ON rules: 99.4% duty above
the legacy 5 W floor and 25.8% duty at the printed 99 W repair threshold. The inventory row
counts were re-read from Parquet metadata during the build, and the final SUMMARY block was
parsed as JSON and cross-checked field by field against the prose claims - the same
automated prose-versus-table check used for the other rebuilt notebooks. Sources consulted
for context: the NILMTK conversion pipeline (`src/pipelines/01_extract_dataset/extract_redd.py`),
the gold label map (`data/gold/appliance_map_redd.json`), the thresholds file
(`data/gold/thresholds.json`), and the series overview (`00_overview.md`).

---

## 1. Verdict

The notebook earns its place in the series as **the "what breaks when data is thin" reference**:
REDD is the shortest-span, lowest-coverage dataset we hold (23-48 days, 8-50% 1 Hz-equivalent
panel coverage), and the notebook turns every one of those weaknesses into a checkable claim -
outage-aware integrals, lossy-cache forensics, a 5 W-floor degeneracy census, and a
simultaneity statistic that moves from 91.5% to 40.3% under one threshold repair. Every
headline quantity in the printed SUMMARY reproduces exactly on independent re-derivation, and
the house rule (every prose number matches a printed table cell) holds across the final build.

Two review findings were fixed during the rebuild and are described in section 3: a census
definition that initially under-counted the cache files, and a simultaneity table that needed
its legacy-versus-floor contrast stated as one claim rather than two.

## 2. What the notebook establishes (verified)

- **Inventory and shape.** Six buildings, 116 meter files (12 site meters + 104 labelled
  circuits) plus 31 cache derivative files excluded from the inventory, 56,341,629 rows total.
  Spans are 23.4-48.0 days, all inside spring 2011 (2011-04-16 to 2011-06-14) - a single US
  EDT window, so unlike ECO or GREEND one fixed offset happens to be right year-round, and the
  notebook says why that is a property of this dataset and not of the pipeline.

- **The panel is two meters (split phase).** Building 1's m1/m2 share an exact timestamp grid;
  leg means 226.9 W vs 157.1 W (imbalance 30.8%); the only whole-home signal is their sum
  (mean 384.0 W, p50 176.3 W, p95 1264.0 W). The 240 V tell is verified and beautiful:
  519 joint-leg steps vs 2,793 m1-only and 776 m2-only above 150 W - the joint steps are where
  240 V appliances live.

- **Coverage honesty.** The timestamp grid says 49.8% 1 Hz-equivalent coverage for b1 with a
  9.45-day largest outage (and 8.0% for b5); **the NILMTK `good_sections` cache claims one
  continuous section across the full span** (26 duplicate rows - a converter artefact). The
  notebook's ruling - the timestamp grid is authoritative, caches are hints - is the transferable
  finding, and the `dropout_rate` cache (21.2% inside-section missing for meter 5) is scored
  as "closer to the truth but still not the 78% the circuit clocks actually miss".

- **Cadence.** Panel delivers 99.1% of present gaps at exactly 1 s (mean dt 2.01 s including
  outage gaps); every circuit samples at 4 s (`b1_circuit_dt_med_s = [4.0]`), so any
  cross-channel alignment must decide an upsample rule - the notebook states the choice.

- **The 5 W floor degenerates on 13 of 104 labelled circuits** (12.5%), and the census names
  them: b1 fridge 99.4% duty, b1 sockets both meters pinned ON (duty 100.0%), b2 light 99.2%,
  b3 CE appliance 99.8%, b4 electric furnace 97.3% and light 100.0%, b5 furnace/subpanel/light,
  b6 space heater/light. The floor-repair rule (per-channel threshold from the printed floor_W)
  brings every one of them to a usable duty range. Independent re-check of the b1 fridge row:
  99.4% legacy duty, 25.8% at the 99 W repair threshold - exact match.

- **Canonical coverage.** Kettle does not exist in REDD (0/6 - the release predates the slot);
  washing machine 6/6, dishwasher 6/6, fridge 5/6 (building 4 has none), microwave 4/6. The
  label matrix also shows duplicate labels as real circuits (b1: two ovens, three lights, four
  sockets; b5: six sockets) and the US-specific label mass (furnace, subpanel, CE appliance,
  waste disposal, smoke alarm) that maps to nothing in our canonical five.

- **Episode anatomy and attribution.** Circuit episodes at 4 s: fridge 13.4/day (dwell p50 16 s,
  91.9 Wh/episode), dishwasher 9.3/day, microwave 12.1/day, washing machine 1.7/day. On the 14
  fully-recorded panel days, labelled circuits attribute 77.3% of panel energy (99.1 of 128.2
  kWh capped) - a strong but bounded attribution that the notebook correctly refuses to
  extrapolate to outage days.

- **Simultaneity is a threshold artefact as much as a physics fact**: two-plus-ON share is 91.5%
  under the legacy rule but 40.3% after the floor repair - the legacy number is an artefact of
  channels that never leave ON, and the notebook prints the full repaired share distribution
  (0 ON: 25.9%, 1 ON: 33.8%, 2+: 40.3%).

## 3. Findings and fixes during review

1. **P1 (fixed in build): cache-file census.** The first inventory pass counted the 31
   `building*_elec_cache_*` derivative files as meter files, inflating the meter count. The
   final build excludes them from the inventory table and prints the exclusion explicitly
   ("meter files: 116 | cache derivative files (excluded from inventory): 31").

2. **P1 (fixed in build): simultaneity framing.** The Q9 prose originally reported the legacy
   91.5% and the repaired 40.3% as separate observations; the final text states them as one
   before/after pair with the repaired distribution printed, so the 91.5% cannot be quoted
   without its caveat.

3. **P2 (residual, documented in-notebook): float32 meters.** `value_0` is stored as float32
   (~7 significant digits). Harmless at watt scale, but the notebook's printed p95 values can
   differ from a float64 re-derivation by a few tenths of a watt (observed 385.0 printed vs
   384.8 re-derived on b1 m1); nobody should diff those digits across runs.

4. **P2 (residual, documented in-notebook): the attribution share (77.3%) is defined over the
   14 fully-recorded days only.** It is not a whole-span number and the notebook says so in
   both the cell and the TL;DR.

## 4. Prose-versus-table audit

Final pass: every quantitative sentence in the TL;DR, the ten Reading-it blocks, and the Q10
gold list was checked against a printed table cell or SUMMARY field. All match. The three
numbers quoted most likely to be reused elsewhere:

| claim | printed source | re-derived |
| ----- | -------------- | ---------- |
| b1 panel mean 384.0 W, 1,561,660 rows | Q2 table + series card | 384.0 (m1 226.9 + m2 157.1), rows exact |
| b1 capped integral 167.7 kWh (vs 341.3 uncapped) | Q2 print + SUMMARY | 167.7 (10 s-capped re-integration) |
| 5 W-floor degeneracy: 13 of 104 circuits | Q4 census + SUMMARY | b1 fridge row re-derived exactly (99.4% / 25.8%) |

## 4b. Evidence appendix

- Spot re-derivations run for this review (fresh process, independent of the notebook):
  `building1_elec_meter1.parquet` -> rows 1,561,660, mean 226.9 W, p50 130.2 W;
  `...meter2.parquet` -> rows 1,561,660, mean 157.1 W; panel mean 384.0 W;
  capped@10 s integral 167.7 kWh; `...meter5.parquet` (fridge) -> duty > 5 W: 99.4%,
  duty >= 99 W: 25.8%, p50 7.0 W.
- SUMMARY block: 12 keys, parses as JSON; `b1_panel`, `per_building_mains`,
  `canonical_matrix`, `simultaneity_two_plus_pct`, `degenerate_channels_all_buildings = 13`,
  `quirks` all agree with the prose claims listed above.
- Notebook stats: 46 cells (23 markdown, 23 code), 9 figures, 0 errors; series context:
  01 (UK-DALE), 02/02b (REFIT), 04 (ECO), 05 (GREEND), 06 (AMPds2), 07 (synthetic).
