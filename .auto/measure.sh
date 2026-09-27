#!/usr/bin/env bash
# Benchmark entry point - prints METRIC lines. v4 (owner-directed segment-2
# protocol): PRIMARY = median over the frozen 5 seeds of the mean F1 over the
# frozen pool's (house, device) pairs, every house RE-CALIBRATED with its own
# K=5 marks, its own pre-split history and a fresh build_and_train - the
# deployment path. v3's transfer track applied house_1's predictor to other
# homes, which the product never does; it is retained only as a frozen
# guardrail readout and is reported separately at milestones.
# Pool eligibility is frozen GT-only in .auto/pool_v4.json by .auto/pool_v4.py.
set -euo pipefail
cd "$(dirname "$0")/.."
export UV_CACHE_DIR=/tmp/uvcache
export OMP_NUM_THREADS=8
exec uv run python3 .auto/bench_v4.py