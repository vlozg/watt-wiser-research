"""UK-DALE 1 Hz mains.parquet vs raw mains.dat: rows, ts set, all 3 value columns.

NILMTK's converter skips mains.dat (its regex only matches channel_<n>.dat);
this checks the extra file the foundation converts (houses 1, 2, 5).
"""
import os

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

m = pq.ParquetFile(os.path.join(ROOT, 'data', 'fnd', 'ukdale', 'house_1', 'mains.parquet'))
mt = m.read(columns=['ts_us'])['ts_us'].combine_chunks().to_numpy(zero_copy_only=False)
print('mains.parquet rows=%d cols=%s first_ts=%d last_ts=%d' % (mt.size, m.schema.names, mt[0], mt[-1]))
nfull = pd.read_csv(os.path.join(ROOT, 'data', 'raw', 'ukdale-full', 'house_1', 'mains.dat'),
                    sep=' ', header=None, names=['ts', 'a', 'b', 'c'], dtype=np.float64)
n_us = np.round(nfull['ts'].values * 1e6).astype(np.int64)
print('rows equal:', mt.size == n_us.size, '| ts set equal:', np.array_equal(np.sort(mt), np.sort(n_us)))
tbl = m.read()
for i, cname in enumerate(['a', 'b', 'c']):
    nv = nfull[cname].values
    mv = tbl[cname if cname in tbl.schema.names else tbl.schema.names[1 + i]].combine_chunks().to_numpy(zero_copy_only=False)
    d = np.abs(nv - mv)
    print('  col%d maxdiff=%.3g' % (i + 1, d.max()))
