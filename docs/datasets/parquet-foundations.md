# Parquet data foundation (`data/fnd/`)

Raw-fidelity parquet copies of all six NILM datasets, one directory per dataset,
built by resumable extractors in `src/pipelines/01_extract_dataset/`.
Source files in `data/` are never modified; the foundation is fully rebuildable
from them (each extractor reads only from `data/`, writes only to `data/fnd/`).

## Layout

```
data/fnd/<dataset>/manifest.json        # per-file records + dataset notes
data/fnd/<dataset>/*.parquet            # one parquet per source table/stream
src/wattwiser/                        # shared helpers (paths, log, parquet I/O,
                                      # manifests, label canonicalization)
src/pipelines/01_extract_dataset/extract_<name>.py  # one per dataset, argparse --force
```

## Conventions

- **Raw fidelity**: every source measurement column is kept verbatim (no
  resampling, no renaming, no unit conversion). Source sentinels stay as-is:
  REDD/REFIT NULLs become null, ECO `-1` missing markers are preserved as
  `-1`. AMPds2 columns that are not measurements (billing period dates,
  ECCC quality flags, weather text, the HistoricalNormals month grid with
  its extreme-date cells) are kept verbatim as nullable strings and recorded
  per file in the manifest (`non_numeric_cols`); the same goes for a
  non-time first column (HistoricalNormals `Item`, NaturalGas_HeatValues
  `Day` - the table's row identity, kept beside its null `ts_us`).
- **`ts_us`**: int64 microseconds since Unix epoch as the first column, derived
  from the source's own timestamp semantics (per-dataset anchors below).
  Rows whose source ts cannot parse keep `ts_us` null (never dropped).
- **Compression**: zstd level 3 via the shared writer (`wattwiser.parquet.write_parquet`).
- **Extra derived column (REFIT only)**: refit parquets add `ts_local_us` -
  the true UK local wall clock (Europe/London conversion of `ts_us`, stored as
  naive local epoch microseconds) - because UK-DALE-style DST-aware local-time
  joins need it. Every other dataset keeps `ts_us` only.
- **Resumable**: a per-dataset `manifest.json` keys every output; reruns skip
  finished outputs unless `--force`. Records carry `path, rows, bytes,
  ts_min_us, ts_max_us, src, src_bytes` plus dataset-specific fields.
- **Labels/provenance kept with the data**: REDD attrs -> `redd_meta.json`,
  UK-DALE `labels.dat` + README copied per house, ECO `doc.txt` +
  `eco_labels.json` per house.

## Datasets (verified 2026-02-13; REFIT and ampds2 aux files rebuilt +
re-verified 2026-09-20; rows == parquet metadata for every file)

| dataset | files | rows | out MB | ts range | extractor quirks |
| --- | ---: | ---: | ---: | --- | --- |
| ukdale | 182 | 970,784,319 | 4,353 | 2012-11-09..2017-04-26 | houses 1-5 `.dat` whitespace tables incl. `button_press` event logs; `labels.dat` skipped as data and copied verbatim; ts = round(unix_s * 1e6) |
| ampds2 | 38 | 31,553,674 | 236 | 2013..2014 (1970 rows = non-time tables) | ts fallback chain numeric -> parsed datetime -> nullable Int64; Climate_HistoricalNormals `Item` and NaturalGas_HeatValues `Day` are not time series (ts null, first column kept as string); other non-numeric columns kept as nullable strings |
| redd | 147 | 56,342,478 | 227 | 2011-04-16..2011-06-14 | pytables direct API (`arr['index']` ns, `arr['values_block_0']`); float32 source dtype preserved; NILMTK cache tables converted too; attrs -> `redd_meta.json` |
| refit | 20 | 119,495,879 | 1,085 | 2013-09-17..2015-07-10 | streamed per house from `CLEAN_REFIT_081116.7z` (fresh py7zr handle per member - handle reuse corrupts); `Unix` s * 1e6; also carries derived `ts_local_us` (see Conventions); the release `Time` string column verified to render the same corrected timeline and dropped - the RAW variant's `Time` is the uncorrected logger clock |
| greend | 8 | 196,943,999 | 1,203 | 2000-01-01..2015-06-29 | block-aware parser below; rows == source data lines verified for all 8 buildings |
| eco | 71 | 849,398,400 | 5,401 | 2012-05-30..2013-01-31 | see below; matlab zips not converted |

Total: 2,224,518,749 rows, ~12.5 GB parquet (zstd).

## GREEND: mid-file header rows (no rows dropped)

GREEND daily files embed repeated header rows (`timestamp,<mac ids>`): routine
~15 min checkpoints (same plug set) and plug-set changes mid-day (new column
list). A naive parse either drops them (`on_bad_lines='skip'` lost ~13 h of
building0) or parses them as data. The extractor maps every block onto the
building-wide union of plug MACs; plugs absent from a block are null for that
interval. Verified per building: parquet rows == source data lines exactly
(b0 19,886,555; b1 35,088,199; b2 39,352,920; b3 29,083,125; b4 19,726,407;
b5 27,906,892; b6 17,029,415 - plus 30 zero-byte days skipped; b7 8,870,486).
Mid-file header rows per building (manifest `midfile_header_rows`):
b0 22,808, b2 46,955, b4 40,255, b5 36,460, b6 31,222, b7 12,051 (b1/b3 none).
Two degenerate whitespace-only lines (b4 2014-02-03, b7 2015-03-05) are kept as
rows with null ts and null plugs.

## ECO specifics

- Smart meter: headerless daily 16-column CSVs (`powerallphases` ...
  `phaseanglecurrentvoltagel3`, doc.txt order); one row per second; `-1` =
  missing, preserved verbatim.
- Plugs: per-plug daily single-value CSVs (consumption W) -> `plug_PP.parquet`
  per house; plug names/days/coverage parsed from `NN_doc.txt` ->
  `house_NN/eco_labels.json` (labels survive, raw MAC/file-id columns kept).
- Occupancy (houses 1-5): day-matrix CSVs (86,400 s/day after a header line of
  time labels) -> long `occupancy_summer.parquet` / `occupancy_winter.parquet`
  (`ts_us`, `occupancy` 0/1); summer and winter kept separate.
- **ts anchor**: `ts_us` = the file's date at midnight (naive local wall clock,
  CET/CEST as measured, no DST correction) + row-index seconds; the same rule
  for plugs and occupancy. Documented in the dataset `notes`.

## Quality gate (`src/pipelines/01_extract_dataset/qa_raw.py`)

The pipeline is extract (data/raw = verbatim strings on disk) -> quality gate
-> cast (the extractors build typed parquet in data/fnd). `qa_raw.py` is the
gate: it re-reads every raw source as text (per-column numeric parse rates,
junk-cell examples - exactly the values an `errors='coerce'` would silently
NaN - plus missing/NULL counts) and audits the landed parquets (all-NaN ghost
columns, `ts_us` duplicates, non-monotonic runs). It writes
`data/fnd/qa/qa_report.json` and prints a summary; it is read-only on data.

```bash
uv run python3 src/pipelines/01_extract_dataset/qa_raw.py            # all datasets
uv run python3 src/pipelines/01_extract_dataset/qa_raw.py ampds2     # subset
```

First full findings (2026-09-20; ampds2 aux files rebuilt same day to keep
their text columns): the only coercion losses ever found in fnd came from
AMPds2's auxiliary files - 56,257 raw cells (date labels, quality flags,
weather text); every meter/climate measurement CSV and all 19 REFIT house
CSVs are fully numeric. At extract time the same policy is enforced inline:
`extract_refit.py` raises on non-numeric measurement cells;
`extract_ampds2.py` keeps non-numeric columns verbatim as nullable strings
with a manifest record (dropping them had discarded usable metadata - e.g.
the HistoricalNormals extreme-event dates - and NaNifying cells had been
silent corruption of mostly-numeric columns).

## Cross-checks against public loaders (NILMTK converters, verified 2026-02-13)

Every extractor was cross-checked against NILMTK's official converter for the
same dataset (`nilmtk/dataset_converters/<name>/convert_<name>.py`, master
branch), re-run on the same source files and compared row-for-row with the
parquets (probe scripts under `analysis/xcheck/`, runnable from any cwd).

| dataset | NILMTK check | result |
| --- | --- | --- |
| greend | block parser replicated from `convert_greend.py` | b0 2013-12-07: 81,502 = 81,502 rows; b2 2014-02-15: 35,231 = 35,231; b6 2014-09-02: 33,456 = 33,456; values match to float32 precision (max diff 6e-5), NaN masks identical. b5 2014-01-28: mine +2 rows (NILMTK hard-skips 2 corrupt lines); b5 2014-02-04: mine +3 rows (NILMTK drops 3 ragged 13-field lines). Both deviations are raw-fidelity keeps of lines NILMTK discards. |
| eco | `convert_eco.py` sm (16 cols, 86,400 s/day, `date_range(tz='GMT')`) + 1-column plug CSVs | house_01 2012-06-01: all 86,400 s aligned, `powerl1/currentl1/voltagel1/phaseanglecurrentvoltagel1` max diff 6.1e-6 (float32 quantization only), 0 mismatches; `plug_01` consumption max diff 0 (exact). Column order identical to NILMTK's 1..16 mapping. |
| ukdale | `_load_csv` style (`sep=' '`, float32, `to_datetime(unit='s', utc=True)`) | house_1 `channel_1` 21,837,636 = 21,837,636 (max diff 0), `channel_5` 19,555,935 = 19,555,935 (max diff 0), 1 Hz `mains.parquet` 128,238,700 rows, ts set equal, all 3 value columns max diff 0. Zero duplicate timestamps (NILMTK's `drop_duplicates` policy would drop nothing). |
| refit | `convert_refit.py` (`usecols=['Unix','Aggregate','Appliance1..9']`) | CLEAN_House1: 6,960,008 = 6,960,008 rows, ts exactly equal, `Aggregate`/`Appliance1`/`Appliance5` max diff 0 across all rows. Both parsers pick the `Unix` seconds column and ignore the text `Time` column. |
| ampds2 | `convert_ampds.py` (R2013; same `unix_ts` seconds convention, no separate AMPds2 converter in NILMTK master) | Electricity_CDE: 1,051,200 = 1,051,200 rows, all aligned, `V`/`P`/`Pt` max diff 0 (exact). |
| redd | source h5 *is* NILMTK's own datastore product (built by `convert_redd.py`) | inherently consistent; parsed with the pytables direct API (`arr['index']`, `arr['values_block_0']`). |

Deliberate differences from NILMTK (raw fidelity by design):

- NILMTK casts to float32 and, per converter policy, drops duplicate timestamps
  (REDD/UK-DALE option), ECO `-1` missing rows, AMPds NaN rows, GREEND ragged
  or corrupt lines. The parquets keep every row verbatim; sentinels are
  preserved (`-1` ECO, NULL -> null REDD/REFIT).
- NILMTK localizes timestamps to dataset timezones (Europe/London, US/Eastern,
  GMT, ...) for display; the parquets keep UTC microseconds (`ts_us`).
- GREEND sub-microsecond timestamps differ from NILMTK by up to 1 us: NILMTK
  floors the ns-precision index, `ts_us = round(unix_s * 1e6)` rounds to
  nearest. All timestamps align within 1 us (values compared with that
  tolerance).
- UK-DALE `mains.dat` (1 Hz, 4-column aggregate) is converted per house
  (houses 1, 2, 5 - the source only has it there) as `house_N/mains.parquet`;
  NILMTK's converter skips it (its regex matches only `channel_<n>.dat`).

## Re-running

```bash
uv run python3 src/pipelines/01_extract_dataset/extract_<name>.py [--force]
```

Reruns are incremental (manifest-keyed). To rebuild one building/house, drop
its key from that dataset's `manifest.json` `files` and rerun.
