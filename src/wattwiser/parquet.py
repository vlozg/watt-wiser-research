"""Parquet I/O helpers shared by the extraction pipelines.

Convention: zstd level 3; first column of every extract is ts_us int64
(microseconds since epoch, source time semantics preserved verbatim).
"""
import os

import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.compute as pc

from wattwiser.util import ensure


def write_parquet(df, path, schema=None):
    """Write one parquet file (zstd/3); returns the written table."""
    ensure(os.path.dirname(path))
    table = pa.Table.from_pandas(df, preserve_index=False, schema=schema)
    pq.write_table(table, path, compression='zstd', compression_level=3)
    return table


def stat_parquet(path):
    """File stats: rows / column count / ts_us range / bytes (None-safe on nullable ts)."""
    pf = pq.ParquetFile(path)
    meta = pf.metadata
    mn = mx = None
    for g in range(meta.num_row_groups):
        col = pf.read_row_group(g, columns=['ts_us'])['ts_us']
        mm = pc.min_max(col)
        lo, hi = mm['min'].as_py(), mm['max'].as_py()
        mn = lo if mn is None or (lo is not None and lo < mn) else mn
        mx = hi if mx is None or (hi is not None and hi > mx) else mx
    return {'rows': int(meta.num_rows),
            'cols': int(meta.num_columns),
            'ts_min_us': 0 if mn is None else int(mn),
            'ts_max_us': 0 if mx is None else int(mx),
            'bytes': os.path.getsize(path)}
