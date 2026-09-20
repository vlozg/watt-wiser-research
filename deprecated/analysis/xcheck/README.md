# NILMTK cross-check probes

Row-for-row verification of the `data/fnd/` parquet foundations against NILMTK's
official dataset converters. The results table in
`docs/datasets/parquet-foundations.md` was produced by these scripts.

| script | checks |
| --- | --- |
| `verify_all.py` | every `data/fnd/<name>/manifest.json` entry re-read from disk: file exists, row count matches; per-dataset rows / MB / ts-range table |
| `xcheck_greend2.py` | replicates `nilmtk/dataset_converters/greend/convert_greend.py` block parser on 5 sample building-days; compares rows, values (float32 precision, 1 us ts tolerance), NaN masks, ragged-line policy |
| `xcheck_others.py` | ECO sm + plug, UK-DALE channel_1 / channel_5, REFIT House1, AMPds2 Electricity_CDE against the respective NILMTK converter conventions |
| `xcheck_mains.py` | UK-DALE 1 Hz `mains.parquet` vs raw `mains.dat`: all rows, ts set, all 3 value columns (NILMTK's converter skips mains.dat) |

Run with the project env (works from any cwd):

```bash
uv run python3 analysis/xcheck/verify_all.py
uv run python3 analysis/xcheck/xcheck_greend2.py
uv run python3 analysis/xcheck/xcheck_others.py
uv run python3 analysis/xcheck/xcheck_mains.py
```

Requires the staged raw datasets under `data/` (intake:
`docs/datasets/data-collection.md`) and the built foundation under
`data/fnd/` (`docs/datasets/parquet-foundations.md`).
