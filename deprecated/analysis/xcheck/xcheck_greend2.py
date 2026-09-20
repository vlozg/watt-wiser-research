"""Cross-check extract_greend.py output against nilmtk's convert_greend logic."""
import os
from io import StringIO

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(ROOT, 'data', 'raw', 'GREEND_0-2_300615', 'GREEND_0-2_300615')
FND = os.path.join(ROOT, 'data', 'fnd', 'greend')
DROPPED = [0]


def nilmtk_blocks(filename, skip_ragged=False, skip_special=False):
    dfs = []
    block_data = None
    previous_header = None
    dtypes = {'timestamp': np.float64}
    DROPPED[0] = 0

    def _process_block():
        if block_data is None:
            return
        block_data.seek(0)
        try:
            dfs.append(pd.read_csv(block_data, index_col='timestamp', dtype=dtypes))
        except pd.errors.ParserError:
            if skip_ragged:
                try:
                    dfs.append(pd.read_csv(block_data, index_col='timestamp',
                                           dtype=dtypes, on_bad_lines='skip'))
                except pd.errors.ParserError:
                    # pandas 3 cannot skip-and-index this file; emulate nilmtk's
                    # error_bad_lines=False intent by filtering ragged rows manually
                    lines = block_data.getvalue().split('\n')
                    n = len(lines[0].strip().split(','))
                    kept = [lines[0].strip()] + [l for l in lines[1:] if len(l.split(',')) == n]
                    DROPPED[0] += len(lines) - 1 - (len(kept) - 1)
                    dfs.append(pd.read_csv(StringIO('\n'.join(kept)),
                                           index_col='timestamp', dtype=dtypes))
            else:
                raise

    with open(filename) as f:
        for line in f:
            line = line.strip('\0')
            if skip_special and ('0.072.172091508705606' in line
                                 or line.strip() == '1409660828.0753369,NULL,NUL'):
                continue
            if 'time' in line:
                if not line.startswith('time'):
                    line = line[line.find('time'):]
                if previous_header == line.strip():
                    continue
                for col in line.strip().split(',')[1:]:
                    dtypes[col] = np.float32
                _process_block()
                block_data = StringIO()
                previous_header = line.strip()
            block_data.write(line)
    _process_block()
    df = pd.concat(dfs, sort=False).sort_index()
    df.index = pd.to_datetime(df.index, unit='s')
    return df


def xcheck(fn, ragged=False, skip_special=False):
    nd = nilmtk_blocks(os.path.join(SRC, fn), ragged, skip_special)
    us = (nd.index.astype('int64') // 1000).values
    b = fn.split('/')[0]
    full = pq.ParquetFile(os.path.join(FND, '%s.parquet' % b))
    t = full.read(columns=['ts_us'])['ts_us'].combine_chunks().to_numpy(zero_copy_only=False)
    my_day = np.sort(t[(t >= us.min() - 1) & (t <= us.max() + 1)])
    print('%s: nilmtk_rows=%d | my_rows=%d (within +-1us window) | nilmtk_ragged_dropped=%d'
          % (fn, len(nd), my_day.size, DROPPED[0]))
    # value comparison with +-1us tolerance alignment, first two plug columns
    us_s = us[np.argsort(us, kind='stable')]
    for vcol in nd.columns[:2]:
        nv = nd[vcol].values.astype('float64')
        nv = nv[np.argsort(us, kind='stable')]
        tbl = full.read(columns=['ts_us', vcol])
        mt = tbl['ts_us'].combine_chunks().to_numpy(zero_copy_only=False)
        mv = tbl[vcol].combine_chunks().to_numpy(zero_copy_only=False)
        o = np.argsort(mt, kind='stable')
        mt, mv = mt[o], mv[o]
        # align each nilmtk ts to nearest my ts within 1 us
        idx = np.searchsorted(mt, us_s)
        idx = np.clip(idx, 1, mt.size - 1)
        left, right = mt[idx - 1], mt[idx]
        pick = np.where(np.abs(left - us_s) <= np.abs(right - us_s), idx - 1, idx)
        near_ok = np.abs(mt[pick] - us_s) <= 1
        both = near_ok & ~np.isnan(nv) & ~np.isnan(mv[pick])
        d = np.abs(nv[both] - mv[pick][both])
        print('   %s: aligned=%d/%d max_abs_diff=%.6g mismatches_atol1e-2=%d | NaN: nilmtk=%d mine=%d'
              % (vcol, int(near_ok.sum()), us_s.size, d.max() if d.size else 0.0,
                 int((d > 1e-2).sum()), int(np.isnan(nv).sum()), int(np.isnan(mv[pick]).sum())))


xcheck('building0/dataset_2013-12-07.csv')
xcheck('building2/dataset_2014-02-15.csv')
xcheck('building5/dataset_2014-02-04.csv', ragged=True)
xcheck('building5/dataset_2014-01-28.csv', skip_special=True)
xcheck('building6/dataset_2014-09-02.csv', skip_special=True)
