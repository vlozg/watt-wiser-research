"""Small shared utilities: timestamped logging, mkdir, human-readable sizes."""
import os
import time


def log(msg):
    """Print a '[HH:MM:SS] msg' progress line (flushed so `tail -f` works)."""
    print('[%s] %s' % (time.strftime('%H:%M:%S'), msg), flush=True)


def ensure(path):
    """mkdir -p for one directory."""
    os.makedirs(path, exist_ok=True)


def human(n):
    """Byte count -> '383 MB'-style string (SI units, 1 decimal above B)."""
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if n < 1000 or unit == 'TB':
            return ('%d %s' % (round(n), unit)) if unit == 'B' else ('%.1f %s' % (n, unit))
        n /= 1024.0
