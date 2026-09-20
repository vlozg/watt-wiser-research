"""Project path constants - single source of truth for the data tree.

Medallion layout:
  data/raw   user-staged dataset downloads (immutable input, user-managed)
  data/fnd   immutable per-dataset parquet foundations (silver layer)
  data/gold  curated label maps / gold tables (consumed by analysis)
"""
import os

ROOT: str = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
DATA: str = os.path.join(ROOT, 'data')
RAW: str = os.path.join(DATA, 'raw')
FND: str = os.path.join(DATA, 'fnd')
GOLD: str = os.path.join(DATA, 'gold')
# transient scratch for extraction staging (never referenced by docs)
STAGE: str = os.path.join(ROOT, '.scratch', 'extract_stage')
