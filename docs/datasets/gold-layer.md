# Gold layer (03_gold_nilm)

The gold layer turns the raw-fidelity parquet foundations (01) into
**analysis-ready NILM tables**: per building, the whole-home aggregate plus
one series per labeled appliance, in a uniform schema and naming. **Every**
labeled device is included - the five client targets and everything else
(`boiler`, `electric_oven`, `television`, ...) - so gold is a source of
trust and analyses simply filter on the `canonical` field instead of the
build dropping data. Everything is a native-sampling pass-through from
`data/fnd/`: no resampling, no gap filling, no rounding.

## Layout

    data/gold/
      appliance_map.json                  # meter -> label/canonical map (01 labels.py)
      thresholds.json                     # per-appliance ON thresholds + method
      <dataset>/<building>/mains.parquet  # ts_us int64, w float64 (watts)
      <dataset>/<building>/<name>[_N].parquet
      <dataset>/manifest.json             # provenance + label/canonical per table

`mains.parquet` is omitted when a dataset has no site meter (GREEND).

Manual annotations that the gold build cannot derive are kept in a
separate, git-tracked layer: `data/gold_annot/` (per-dataset
hand-marked cycle annotations - schema, provenance convention and load
contract in `data/gold_annot/README.md`).
Appliance file names: the canonical label for target appliances
(`kettle, fridge, microwave, washing_machine, dishwasher`), a slug of the
original device label otherwise (`electric_oven`, `food_mixer`); a repeat
inside one building gets an ordinal suffix in stable meter order (REDD
building_1 has `washing_machine.parquet` and `washing_machine_2.parquet`).
Manifest records and thresholds entries carry `label` (raw name) and
`canonical` (target type or null) - that is the filter key downstream,
e.g. "kettle or microwave" = canonical in {kettle, microwave}.

## Per-dataset conventions

| dataset | mains | appliances | cadence (measured) |
|---|---|---|---|
| ukdale | `channel_1` aggregate | 103 channels, 5 houses | 6 s |
| refit | `Aggregate` column | 180 columns, 20 houses | 7-8 s |
| eco | `sm.parquet:powerallphases` | 49 plugs, 6 houses | 1 s |
| greend | - (no site meter) | 76 plugs, 8 buildings | 1 s |
| redd | `mains1 + mains2` (panel sum) | 104 submeters, 6 buildings | 1-3 s |
| ampds2 | `Electricity_WHE:P` | 20 submeters, 1 building | 60 s |

- **REDD** site meters record the two split-phase panels; their sum is the
  whole-home aggregate. The two panel meters share one timestamp grid per
  building (verified at build time; a keyed union-sum fallback exists).
- **ECO** plugs cover a partial meter set and house_04's smart meter has no
  data (its `mains.parquet` is empty by design); appliance energy shares are
  lower bounds.
- **GREEND** is per-plug metering only (no mains); one meter can carry
  several labeled plugs (all kept, e.g. building_3 meter 2 = UPS + games
  console + computer). Un-timestamped rows (1 in building_4, 1 in
  building_7) are dropped at gold time and logged. The unlabeled partial
  aggregates (total outlets / lights meters) stay in fnd only.
- **AMPds2** is a single building at 60 s; the appliance map's meter numbers
  key into the `Electricity_<label>` fnd files (site meter 1 = WHE), and
  file names are the lowercased label stems (`b1e`, `dwe`, ...). The fnd
  manifest notes flag the corrupt `Pt/Qt/St` registers, idle-filled
  `f/DPF/APF`, the split-phase `V*I` = 2x `S` trap, and the computed
  `MHE`/`UNE` wide columns; gold manifest records carry per-table notes
  (register-incident zero minutes on mains; labels the data contradicts,
  e.g. `HTE`; sub-panels that are not devices: `RSE`, `GRE`).

## Mains is NOT the sum of the device tables

The aggregate is an independent measurement, and submetering is partial, so
summing the appliance tables does not reconstruct `mains`:

- ampds2 has the densest submetering (20 circuits): the submeter sum
  integrates to 82.1% of WHE (16,006 of 19,488 kWh over 2 years); the 17.9%
  residual is the release's own computed "Unmetered" remainder (wide-file
  column `UNE` = `WHE` - `RSE` - `GRE` - 18 named circuits, exact in P and
  S). It is not a meter - it violates `S >= P` on 99.3% of minutes - and it
  is water-heating shaped, so model it as the unknown class rather than as
  measurement error (see `docs/reports/dataset_eda/06_ampds2_eda.ipynb`,
  Q5/Q6).
- ukdale appliance channels are event-sampled (readings every ~6 s while
  active, hours apart when idle; the fridge channel's gaps range 7 s to
  174 h). A naive grid-aligned sum of house_1's 52 channels covers only
  6.9% of mains energy - the sampling gaps, not the wiring, dominate.
  Residuals therefore need cadence-aware alignment (or time integration
  with an explicit gap policy), which is analysis code, not a gold table.
- REDD `mains` is the panel sum, GREEND has no mains at all, and ECO plugs
  cover a partial set - in all three the aggregate-vs-devices relation is
  dataset-specific.

Sum(device tables) is best read as "metered appliance load"; the gap to
`mains` is unmetered load + sampling/measurement artifacts.

## ON thresholds

`data/gold/thresholds.json` holds, per appliance, a reference ground-truth
threshold with the fixed rule:

    thr_on_W = max(5.0, 0.5 * p50_on_W)
    p50_on_W = median of samples above the 5 W noise floor
    ON := w > thr_on_W

This mirrors the M0 detector convention (enter at 0.5 x nominal ON power).
Each entry also stores `p50_on_W`, `n_above_floor`, the ON share, and the
`label` / `canonical` identity; channels with fewer than 100 above-floor
samples keep the plain noise floor and are flagged `method: noise_floor`
(mostly-unplugged ECO plugs, low-signal GREEND plugs). Detectors that
calibrate their own signatures (M0 from a calibration window) can ignore
these thresholds; they exist so analyses have a consistent, documented GT
binarization for any device, not just the targets.

## Build + verify

    make gold          # resumable; gold-force rebuilds from fnd
    uv run python3 src/pipelines/03_gold_nilm/qa_gold.py
                       # quality gate: re-derives every table from fnd and compares

`qa_gold` verifies rows, timestamp endpoints, and exact value sums
against the fnd sources, checks that every labeled meter in
`appliance_map.json` has a gold table under the documented naming rule with
matching `label` / `canonical` identity, and recomputes every threshold.

## Verification (first full build)

    ampds2  21/ 21 tables verified, 20 labeled meters  (3 canonical)
    eco     55/ 55 tables verified, 49 labeled meters (19 canonical)
    greend  76/ 76 tables verified, 76 labeled meters (26 canonical)
    redd   110/110 tables verified,104 labeled meters (24 canonical)
    refit  200/200 tables verified,180 labeled meters(106 canonical)
    ukdale 108/108 tables verified,103 labeled meters (19 canonical)
    TOTAL 570 tables, 0 failures

## Scripts

`src/pipelines/03_gold_nilm/`: `_common.py` (map/manifest/threshold helpers,
naming rule, shared write path), one self-contained builder per dataset
(`gold_<dataset>.py`), and the `gold_all.py` driver. Manifests use the same
resume bookkeeping as fnd (root=GOLD). `src/pipelines/03_gold_nilm/qa_gold.py` is the
independent verifier (quality-gate pattern, like `qa_raw.py` for fnd).
