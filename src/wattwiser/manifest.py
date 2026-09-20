"""<root>/<dataset>/manifest.json read/write + resume bookkeeping.

Every extraction records one manifest entry per output file (path, source,
row/byte stats, timing, notes). Re-runs skip entries whose output already
exists unless the caller passes --force.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import asdict
from typing import Any

from wattwiser.parquet import ParquetStats
from wattwiser.paths import FND
from wattwiser.util import ensure


def manifest_path(name: str, root: str = FND) -> str:
    return os.path.join(root, name, 'manifest.json')


def load_manifest(name: str, notes: list[str], root: str = FND) -> dict[str, Any]:
    """Load the dataset manifest (fresh dict with `notes` if absent)."""
    p = manifest_path(name, root)
    if os.path.exists(p):
        with open(p) as fh:
            man = json.load(fh)
    else:
        man = {'dataset': name, 'files': {}, 'notes': []}
    man['notes'] = notes
    return man


def save_manifest(name: str, man: dict[str, Any], root: str = FND) -> None:
    ensure(os.path.join(root, name))
    man['updated_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
    with open(manifest_path(name, root), 'w') as fh:
        json.dump(man, fh, indent=1)


def done(man: dict[str, Any], key: str) -> bool:
    """True if `key` is recorded and its output exists.

    Aggregate pseudo-entries (e.g. eco 'house_NN/plugs') carry no 'path' -
    being recorded is enough.
    """
    rec = man['files'].get(key)
    return rec is not None and ('path' not in rec or os.path.exists(rec['path']))


def record(man: dict[str, Any], name: str, key: str, out: str, src: str, st: ParquetStats,
           t0: float, root: str = FND, **extra: Any) -> None:
    """Record one output entry (parquet stats `st` + timing) and persist."""
    man['files'][key] = dict(asdict(st), path=out, src=src,
                             secs=round(time.time() - t0, 1), **extra)
    save_manifest(name, man, root)
