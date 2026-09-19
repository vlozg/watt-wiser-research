"""data/fnd/<dataset>/manifest.json read/write + resume bookkeeping.

Every extraction records one manifest entry per output file (path, source,
row/byte stats, timing, notes). Re-runs skip entries whose output already
exists unless the caller passes --force.
"""
import json
import os
import time

from wattwiser.paths import FND
from wattwiser.util import ensure


def manifest_path(name):
    return os.path.join(FND, name, 'manifest.json')


def load_manifest(name, notes):
    """Load the dataset manifest (fresh dict with `notes` if absent)."""
    p = manifest_path(name)
    if os.path.exists(p):
        with open(p) as fh:
            man = json.load(fh)
    else:
        man = {'dataset': name, 'files': {}, 'notes': []}
    man['notes'] = notes
    return man


def save_manifest(name, man):
    ensure(os.path.join(FND, name))
    man['updated_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
    with open(manifest_path(name), 'w') as fh:
        json.dump(man, fh, indent=1)


def done(man, key):
    """True if `key` is recorded and its output exists.

    Aggregate pseudo-entries (e.g. eco 'house_NN/plugs') carry no 'path' -
    being recorded is enough.
    """
    rec = man['files'].get(key)
    return rec is not None and ('path' not in rec or os.path.exists(rec['path']))


def record(man, name, key, out, src, st, t0, **extra):
    """Record one output entry (stats dict `st` + timing) and persist."""
    man['files'][key] = dict(st, path=out, src=src,
                             secs=round(time.time() - t0, 1), **extra)
    save_manifest(name, man)
