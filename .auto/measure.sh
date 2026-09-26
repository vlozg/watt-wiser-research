#!/usr/bin/env bash
# Frozen benchmark entry point - prints METRIC lines; min_device_f1 is primary.
set -euo pipefail
cd "$(dirname "$0")/.."
export UV_CACHE_DIR=/tmp/uvcache
export OMP_NUM_THREADS=8
exec uv run python3 .auto/bench.py