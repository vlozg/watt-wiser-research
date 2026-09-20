# repo-analysis

Reproducible checks on the client-supplied dataset from `github.com/AdibReza/WattWiser`.

**The dataset and the clone are not vendored here on purpose** — the CSV is 50 MB of third-party data and the upstream clone carries its own `.git`, which would nest a second repository inside this one. Fetch it when needed:

```bash
git clone --depth 1 https://github.com/AdibReza/WattWiser.git repo/WattWiser
```

Then run all 12 checks and regenerate the saved output:

```bash
uv run python3 analysis/repo-forensics/analyze_synthetic.py \
    repo/WattWiser/data/raw/synthetic_shelly_data.csv
```

| File | What it is |
|---|---|
| `analyze_synthetic.py` | All checks: cadence, internal arithmetic, label purity, autocorrelation, additivity, simultaneity, voltage coupling, diurnal shape, night activity, trivial baseline |
| `findings.txt` | Captured output of the above, as run on commit `d39f0e0` |

Requires `pandas` and `numpy`. Findings are written up in `../../docs/client/repo-review.md`.
