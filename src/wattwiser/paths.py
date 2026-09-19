"""Project path constants - single source of truth for the data tree.

Medallion layout:
  data/raw   user-staged dataset downloads (immutable input, user-managed)
  data/fnd   immutable per-dataset parquet foundations (silver layer)
  data/gold  curated label maps / gold tables (consumed by analysis)
"""
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
DATA = os.path.join(ROOT, 'data')
RAW = os.path.join(DATA, 'raw')
FND = os.path.join(DATA, 'fnd')
GOLD = os.path.join(DATA, 'gold')
# transient scratch for extraction staging (never referenced by docs)
STAGE = os.path.join(ROOT, '.scratch', 'extract_stage')
