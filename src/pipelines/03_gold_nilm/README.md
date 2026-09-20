# 03_gold_nilm — gold layer

Turns the raw-fidelity foundations (01) into **analysis-ready NILM tables**:
per building, one `mains.parquet` (whole-home aggregate) plus one parquet per
labeled appliance — every labeled device, not just the five client targets —
all in the uniform gold schema. Appliance labels come from
`data/gold/appliance_map.json` (written by 01's `labels.py`); gold is a
source of trust, and analyses filter on the `canonical` field downstream.

## Contract

- `data/gold/<dataset>/<building>/mains.parquet` — `ts_us int64, w float64`
  watts. Omitted when a dataset has no site meter (GREEND).
- `data/gold/<dataset>/<building>/<name>[_N].parquet` — same schema, one file
  per labeled appliance meter. The name is the canonical label for the five
  client targets (`kettle, fridge, microwave, washing_machine, dishwasher`)
  and a slug of the original device label otherwise (`electric_oven`); a
  repeat inside a building gets an ordinal suffix (`washing_machine_2`) in
  stable meter order.
- `data/gold/<dataset>/manifest.json` — provenance (source fnd paths), row
  counts, cadence (`dt_s`) and the `label` / `canonical` identity per table;
  same resume bookkeeping as the fnd manifests.
- `data/gold/thresholds.json` — per appliance: `thr_on_W` (ON threshold),
  `p50_on_W`, share stats, the derivation method, and the same
  `label` / `canonical` identity.

Copies are native-sampling pass-throughs from fnd: no resampling, no gap
filling, no rounding. Dataset-specific conventions (REDD panel sum, ECO
partial plug set, GREEND without mains, AMPds2 60 s) are documented in
`docs/datasets/gold-layer.md` and in each dataset's manifest notes.

## Usage

    make gold            # build/update all six datasets (resumable)
    make gold-force      # rebuild everything from fnd
    uv run python3 src/pipelines/03_gold_nilm/qa_gold.py   # quality gate: verify gold vs fnd

Or run a single dataset:

    uv run python3 src/pipelines/03_gold_nilm/gold_ukdale.py [--force]

## Files

- `_common.py` — map/manifest/threshold helpers, the shared write path
- `gold_<dataset>.py` — one self-contained builder per dataset
- `gold_all.py` — driver for all six
