#!/usr/bin/env bash
# Benchmark entry point - prints METRIC lines. v3 (owner-directed segment-2
# protocol): PRIMARY = median of mean_device_f1 over the frozen 10-seed
# calibration list, guardrails p10 + per-device medians, plus the frozen
# transfer track (ukdale house_2/house_5 + 5 REFIT houses) with per-pair
# smoothed-perfect and random-floor gates. house_1 protocol otherwise
# identical to v2 (cycle scoring, aggregate-only marks). bench_v2.py is
# frozen reference; v1 retired earlier.
set -euo pipefail
cd "$(dirname "$0")/.."
export UV_CACHE_DIR=/tmp/uvcache
export OMP_NUM_THREADS=8
exec uv run python3 .auto/bench_v3.py