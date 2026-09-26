#!/usr/bin/env bash
# Benchmark entry point - prints METRIC lines. v2 (owner-approved protocol
# change): cycle scoring, mean_device_f1 primary, min_device_f1 guardrail;
# sanity gate must pass or the run is invalid. v1 (bench.py) retired - see
# .auto/log.jsonl run 27 and the benchmark-integrity review.
set -euo pipefail
cd "$(dirname "$0")/.."
export UV_CACHE_DIR=/tmp/uvcache
export OMP_NUM_THREADS=8
exec uv run python3 .auto/bench_v2.py