"""wattwiser - shared helpers for the NILM research pipelines.

Installed editable by `uv sync` (hatchling backend), so every script can just
`from wattwiser import ...` regardless of where it is invoked from.
"""
from wattwiser.manifest import done, load_manifest, manifest_path, record, save_manifest
from wattwiser.parquet import ParquetStats, stat_parquet, write_parquet
from wattwiser.paths import DATA, FND, GOLD, RAW, ROOT, STAGE
from wattwiser.util import ensure, human, setup_logging

__all__ = [
    'ROOT', 'DATA', 'RAW', 'FND', 'GOLD', 'STAGE',
    'ensure', 'human', 'setup_logging',
    'write_parquet', 'stat_parquet', 'ParquetStats',
    'manifest_path', 'load_manifest', 'save_manifest', 'done', 'record',
]
