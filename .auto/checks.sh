#!/usr/bin/env bash
# Correctness gate: run after a passing benchmark. Exit 0 = pass.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BENCH_ROOT="$ROOT" python3 - <<'PYEOF'
import json, math, sys, os
root = os.environ['BENCH_ROOT']
try:
    d = json.load(open(os.path.join(root, '.auto/last_bench.json')))
except Exception as e:
    print('checks: cannot read last_bench.json:', e); sys.exit(1)
devs = d.get('devices', {})
expected = {'kettle', 'microwave', 'fridge', 'washing_machine', 'dishwasher'}
if set(devs) != expected:
    print('checks: device set mismatch:', sorted(devs)); sys.exit(1)
for name, s in devs.items():
    if s['n_gt'] <= 0:
        print('checks:', name, 'has no GT episodes in eval window'); sys.exit(1)
    for k in ('precision', 'recall', 'f1'):
        v = s[k]
        if v is None or not (0.0 <= v <= 1.0):
            print('checks:', name, k, '=', v, 'out of range'); sys.exit(1)
    m = s['mae_w']
    if m is None or m < 0 or m != m:
        print('checks:', name, 'mae_w not finite'); sys.exit(1)
    if s['nonnull_frac'] < 0.5:
        print('checks:', name, 'GT data coverage', round(s['nonnull_frac'], 2), '< 0.5'); sys.exit(1)
mn = min(s['f1'] for s in devs.values())
if abs(d['min_device_f1'] - mn) > 1e-9:
    print('checks: min_device_f1 inconsistent with per-device F1s'); sys.exit(1)
print('checks: OK - 5 devices scored, finite, consistent; min F1 =', round(mn, 4))
PYEOF