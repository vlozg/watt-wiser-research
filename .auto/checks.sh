#!/usr/bin/env bash
# Correctness gate: run after a passing benchmark. Exit 0 = pass.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BENCH_ROOT="$ROOT" python3 - <<'PYEOF'
import json, os, sys
root = os.environ['BENCH_ROOT']
try:
    d = json.load(open(os.path.join(root, '.auto/last_bench_v4.json')))
    pool = json.load(open(os.path.join(root, '.auto/pool_v4.json')))
except Exception as e:
    print('checks: cannot read the v4 artefacts:', e); sys.exit(1)
exp = {'kettle', 'microwave', 'fridge', 'washing_machine', 'dishwasher'}
dm = d.get('dev_med', {})
if set(dm) != exp:
    print('checks: device set mismatch:', sorted(dm)); sys.exit(1)
for k in ('primary', 'p10', 'device_balanced', 'house_1_v4_mean'):
    v = d.get(k)
    if v is None or not (0.0 <= v <= 1.0):
        print('checks:', k, '=', v, 'out of range'); sys.exit(1)
for name, v in sorted(dm.items()):
    if v is None or not (0.0 <= v <= 1.0):
        print('checks:', name, 'f1 =', v, 'out of range'); sys.exit(1)
if d.get('n_houses') != pool.get('n_houses') or d.get('n_pairs') != pool.get('n_pairs'):
    print('checks: scored', d.get('n_houses'), 'houses /', d.get('n_pairs'),
          'pairs but the frozen pool holds', pool.get('n_houses'), '/',
          pool.get('n_pairs'), '- a house or pair dropped out'); sys.exit(1)
if not pool.get('frozen'):
    print('checks: pool_v4.json is not frozen'); sys.exit(1)
if not d.get('seed_means'):
    print('checks: no per-seed means recorded'); sys.exit(1)
print('checks: OK -', d['n_houses'], 'houses /', d['n_pairs'],
      'pairs re-calibrated; primary', round(d['primary'], 4),
      'p10', round(d['p10'], 4))
PYEOF