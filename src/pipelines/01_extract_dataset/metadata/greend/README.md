# GREEND appliance metadata (vendored)

Per-building appliance labels for the GREEND dataset (houses 0-7).

## Provenance

- Source: NILMTK dataset-converter metadata, fetched 2025 from
  https://raw.githubusercontent.com/nilmtk/nilmtk/master/nilmtk/dataset_converters/greend/metadata/
  (`dataset.yaml`, `building1.yaml` ... `building8.yaml`).
- License: nilmtk is Apache-2.0 (https://github.com/nilmtk/nilmtk/blob/master/LICENSE).
- Verified against the original paper: Monacchi, Egarter, Elmenreich, D'Alessandro,
  Tonello, "GREEND: An energy consumption dataset of households in Italy and Austria",
  IEEE SmartGridComm 2014 (open preprint: arXiv:1405.3100), Table 2 (device configurations
  in the monitored households). Meter k in building(k-1) of the paper corresponds to
  `building{k+1}.yaml` here; NILMTK numbers buildings from 1.

## Usage

Parsed by `src/pipelines/01_extract_dataset/extract_greend.py --labels`
(into `data/gold/appliance_map_greend.json`, merged by `labels.py` into
`data/gold/appliance_map.json`; GREEND meter k = the k-th MAC address column
in the raw CSVs, in column order).
A few columns are intentionally unlabeled in the metadata: houses 5, 7 and 8 of the paper
include "total outlets" / "total lights" aggregate columns.
