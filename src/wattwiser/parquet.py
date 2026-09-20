"""Parquet I/O helpers shared by the extraction pipelines.

Convention: zstd level 3; first column of every extract is ts_us int64
(microseconds since epoch, source time semantics preserved verbatim).
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from wattwiser.util import ensure


def write_parquet(df: pd.DataFrame, path: str, schema: pa.Schema | None = None) -> pa.Table:
    """Write one parquet file (zstd/3); returns the written table."""
    ensure(os.path.dirname(path))
    table = pa.Table.from_pandas(df, preserve_index=False, schema=schema)
    pq.write_table(table, path, compression='zstd', compression_level=3)
    return table


@dataclass(frozen=True)
class ParquetStats:
    """Shape stats of one written parquet file, as recorded in the manifest."""
    rows: int          # data rows in the table (parquet metadata num_rows)
    cols: int          # total column count, incl. the leading ts_us column
    ts_min_us: int     # smallest ts_us in the file (0 when the ts column is all-null)
    ts_max_us: int     # largest ts_us in the file (0 when the ts column is all-null)
    bytes: int         # file size on disk (zstd-compressed)


def stat_parquet(path: str) -> ParquetStats:
    """File stats: rows / column count / ts_us range / bytes (None-safe on nullable ts)."""
    pf = pq.ParquetFile(path)
    meta = pf.metadata
    mn: int | None = None
    mx: int | None = None
    for g in range(meta.num_row_groups):
        col = pf.read_row_group(g, columns=['ts_us'])['ts_us']
        mm = pc.min_max(col)
        lo, hi = mm['min'].as_py(), mm['max'].as_py()
        mn = lo if mn is None or (lo is not None and lo < mn) else mn
        mx = hi if mx is None or (hi is not None and hi > mx) else mx
    return ParquetStats(rows=int(meta.num_rows),
                        cols=int(meta.num_columns),
                        ts_min_us=0 if mn is None else int(mn),
                        ts_max_us=0 if mx is None else int(mx),
                        bytes=os.path.getsize(path))
