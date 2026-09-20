"""Small shared utilities: logging setup, mkdir, human-readable sizes."""
from __future__ import annotations

import logging
import os


def setup_logging(level: int = logging.INFO) -> None:
    """Configure the root logger: '[HH:MM:SS] LEVEL message' on stderr.

    StreamHandler flushes after every record, so `tail -f` keeps working.
    Entry-point scripts call this once at startup; later calls are no-ops.
    """
    logging.basicConfig(
        level=level,
        format='[%(asctime)s] %(levelname)-8s %(message)s',
        datefmt='%H:%M:%S',
    )


def ensure(path: str) -> None:
    """mkdir -p for one directory."""
    os.makedirs(path, exist_ok=True)


def human(n: int | float) -> str:
    """Byte count -> '383 MB'-style string (SI units, 1 decimal above B)."""
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if n < 1000 or unit == 'TB':
            return ('%d %s' % (round(n), unit)) if unit == 'B' else ('%.1f %s' % (n, unit))
        n /= 1024.0
    raise AssertionError('unreachable: the TB branch always returns')
