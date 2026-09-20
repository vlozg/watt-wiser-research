"""Cross-check extract_* output against nilmtk converter logic for ECO, UK-DALE, REFIT, AMPds2."""
import io
import os
import zipfile

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, 'data', 'raw')
FND = os.path.join(ROOT, 'data', 'fnd')


def align(m_us, m_val, n_us):
    o = np.argsort(m_us, kind='stable')
    m_us, m_val = m_us[o], m_val[o]
    idx = np.clip(np.searchsorted(m_us, n_us), 1, m_us.size - 1)
    left, right = m_us[idx - 1], m_us[idx]
    pick = np.where(np.abs(left - n_us) <= np.abs(right - n_us), idx - 1, idx)
    ok = np.abs(m_us[pick] - n_us) <= 1
    return m_us[pick], m_val[pick], ok


def report(tag, n_us, n_val, m_us, m_val, atol=1e-2):
    mu, mv, ok = align(m_us, m_val, n_us)
    both = ok & ~np.isnan(n_val) & ~np.isnan(mv)
    d = np.abs(n_val[both] - mv[both])
    print('%-46s nilmtk=%d mine=%d aligned=%d/%d maxdiff=%.3g mismatch=%d NaN: nilmtk=%d mine=%d'
          % (tag, n_val.size, m_val.size, int(ok.sum()), n_val.size,
             d.max() if d.size else 0.0, int((d > atol).sum()),
             int(np.isnan(n_val).sum()), int(np.isnan(mv[ok]).sum())))


def col(tbl, name):
    return tbl[name].combine_chunks().to_numpy(zero_copy_only=False)


print('=== AMPds2: Electricity_CDE.csv vs nilmtk convert_ampds style ===')
n = pd.read_csv(os.path.join(DATA, 'AMPds2', 'Electricity_CDE.csv'))
n.index = (pd.DatetimeIndex(pd.to_datetime(n['unix_ts'], unit='s', utc=True)).as_unit('ns').astype('int64') // 1000).values
mine = pq.ParquetFile(os.path.join(FND, 'ampds2', 'Electricity_CDE.parquet')).read()
for cname in ['V', 'P', 'Pt']:
    report('CDE.' + cname, n.index.values, n[cname].values.astype('float64'),
           col(mine, 'ts_us'), col(mine, cname))

print()
print('=== UK-DALE house_1 mains (channel_1) vs nilmtk _load_csv style ===')
src = os.path.join(DATA, 'ukdale-full', 'house_1', 'channel_1.dat')
n = pd.read_csv(src, sep=' ', header=None)
n.index = (pd.DatetimeIndex(pd.to_datetime(n[0], unit='s', utc=True)).as_unit('ns').astype('int64') // 1000).values
mine = pq.ParquetFile(os.path.join(FND, 'ukdale', 'house_1', 'channel_1.parquet')).read()
print('my channel_1 columns:', mine.schema.names)
for i, cname in enumerate([c for c in mine.schema.names if c != 'ts_us']):
    report('mains.col%d' % (i + 1), n.index.values, n[i + 1].values.astype('float64'),
           col(mine, 'ts_us'), col(mine, cname))
mt = col(mine, 'ts_us')
print('duplicate ts in my channel_1 (nilmtk drops these): %d' % int(pd.Series(mt).duplicated().sum()))

print()
print('=== UK-DALE house_1 channel_5 (6-sec secondary) spot check ===')
src5 = os.path.join(DATA, 'ukdale-full', 'house_1', 'channel_5.dat')
n5 = pd.read_csv(src5, sep=' ', header=None)
n5.index = (pd.DatetimeIndex(pd.to_datetime(n5[0], unit='s', utc=True)).as_unit('ns').astype('int64') // 1000).values
mine5 = pq.ParquetFile(os.path.join(FND, 'ukdale', 'house_1', 'channel_5.parquet')).read()
report('channel_5.watts', n5.index.values, n5[1].values.astype('float64'),
       col(mine5, 'ts_us'), col(mine5, mine5.schema.names[1]))

print()
print('=== ECO house_01: sm + plug vs nilmtk convert_eco style ===')
zf = zipfile.ZipFile(os.path.join(DATA, 'ECO', '01_sm_csv.zip'))
day = sorted(x for x in zf.namelist() if x.endswith('.csv'))[0]
print('sm member:', day, '| members:', len(zf.namelist()))
nsm = pd.read_csv(io.BytesIO(zf.read(day)), header=None, names=range(1, 17), dtype=np.float32)
date = day.split('/')[-1][:-4]

base = int(pd.Timestamp(date).timestamp()) * 1000000
nsm.index = base + np.arange(86400) * 1000000
mine = pq.ParquetFile(os.path.join(FND, 'eco', 'house_01', 'sm.parquet')).read()
print('my sm columns:', mine.schema.names)
for i, cname in [(1, 'powerl1'), (5, 'currentl1'), (8, 'voltagel1'), (13, 'phaseanglecurrentvoltagel1')]:
    report('sm.' + cname, nsm.index.values, nsm[i + 1].values.astype('float64'),
           col(mine, 'ts_us'), col(mine, cname))
smv = col(mine, 'powerl1')
print('sm.powerl1 rows with -1 preserved in mine (nilmtk drops these): %d' % int((smv == -1).sum()))

zp = zipfile.ZipFile(os.path.join(DATA, 'ECO', '01_plugs_csv.zip'))
pnames = sorted(n for n in zp.namelist() if n.endswith('.csv') and '/01/' in n)
pday = pnames[0]
print('plug member:', pday, '| plug-01 members:', len(pnames))
npl = pd.read_csv(io.BytesIO(zp.read(pday)), header=None, names=[1], dtype=np.float64)
pdate = pday.split('/')[-1][:-4]
pbase = int(pd.Timestamp(pdate).timestamp()) * 1000000
npl.index = pbase + np.arange(86400) * 1000000
minep = pq.ParquetFile(os.path.join(FND, 'eco', 'house_01', 'plug_01.parquet')).read()
report('plug_01.consumption', npl.index.values, npl[1].values,
       col(minep, 'ts_us'), col(minep, minep.schema.names[1]))

print()
print('=== REFIT CLEAN_House1 vs nilmtk convert_refit style (usecols Unix..Appliance9) ===')
import tempfile

import py7zr

tmp = tempfile.mkdtemp(prefix='refit_xcheck_')
with py7zr.SevenZipFile(os.path.join(DATA, 'REFIT', 'CLEAN_REFIT_081116.7z')) as z:
    z.extract(targets=['CLEAN_House1.csv'], path=tmp)  # installed py7zr has no in-memory .read()
usecols = ['Unix', 'Aggregate'] + ['Appliance%d' % i for i in range(1, 10)]
n = pd.read_csv(os.path.join(tmp, 'CLEAN_House1.csv'), usecols=usecols)
n.index = n['Unix'].values.astype('int64') * 1000000
mine = pq.ParquetFile(os.path.join(FND, 'refit', 'CLEAN_House1.parquet')).read()
print('my REFIT columns:', mine.schema.names)
report('House1.Aggregate', n.index.values, n['Aggregate'].values.astype('float64'),
       col(mine, 'ts_us'), col(mine, 'Aggregate'))
report('House1.Appliance1', n.index.values, n['Appliance1'].values.astype('float64'),
       col(mine, 'ts_us'), col(mine, 'Appliance1'))
print('ts exact equality check:', np.array_equal(np.sort(n.index.values), np.sort(col(mine, 'ts_us'))))
