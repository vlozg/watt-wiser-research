"""wattwiser - shared helpers for the NILM research pipelines.

Installed editable by `uv sync` (hatchling backend), so every script can just
`from wattwiser import ...` regardless of where it is invoked from.
"""
from wattwiser.paths import DATA, FND, GOLD, RAW, ROOT, STAGE
from wattwiser.util import ensure, human, log
from wattwiser.parquet import stat_parquet, write_parquet
from wattwiser.manifest import done, load_manifest, manifest_path, record, save_manifest

__all__ = [
    'ROOT', 'DATA', 'RAW', 'FND', 'GOLD', 'STAGE',
    'log', 'ensure', 'human',
    'write_parquet', 'stat_parquet',
    'manifest_path', 'load_manifest', 'save_manifest', 'done', 'record',
]
