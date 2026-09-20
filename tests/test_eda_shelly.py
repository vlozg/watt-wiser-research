"""Tests for the eda_shelly battery -- the single implementation in deprecated/analysis/eda_shelly.py.

One file, two runners:
    uv run pytest tests/ -q                       (pytest is a dev dependency)
    ./.venv/bin/python3 tests/test_eda_shelly.py  (plain runner, no extra deps)

Data-dependent tests skip cleanly when user-staged inputs are absent
(repo/WattWiser clone, research-logs UK-DALE slice); both are re-downloadable.
"""

import json
import os
import subprocess
import sys
import tempfile

import numpy as np
import pandas as pd

os.environ.setdefault("MPLCONFIGDIR", "/tmp/mplcfg")
os.environ.setdefault("MPLBACKEND", "Agg")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "deprecated", "analysis"))

import eda_shelly  # noqa: E402

FIXTURE = os.path.join(ROOT, "repo", "WattWiser", "data", "raw", "synthetic_shelly_data.csv")
STORED_REF = os.path.join(ROOT, "deprecated", "analysis", "eda_reference_ukdale.json")
UKDALE_SLICE = os.path.join(ROOT, "research-logs", "sakunrasilka_nilm-test2")


def _csv(path, header, rows):
    with open(path, "w") as f:
        f.write(",".join(header) + "\n")
        for r in rows:
            f.write(",".join(str(x) for x in r) + "\n")
    return path


def test_load_csv_discovers_columns():
    with tempfile.TemporaryDirectory() as d:
        p = _csv(
            os.path.join(d, "in.csv"),
            ["timestamp", "active_power_W", "kettle_power_W", "kettle_on", "fridge_W"],
            [["2024-01-01 00:00:00", 100, 0, 0, 5], ["2024-01-01 00:00:10", 110, 2000, 1, 5]],
        )
        df, apps, S = eda_shelly.load_csv(p)
    assert S["ts_column"] == "timestamp" and S["power_column"] == "active_power_W"
    assert sorted(apps) == ["kettle"]
    assert "fridge_W" in S["ignored_columns"]
    assert df["ts"].dt.day.iloc[0] == 1 and df["power"].iloc[1] == 110


def test_schema_warns_on_mismatch():
    with tempfile.TemporaryDirectory() as d:
        p = _csv(
            os.path.join(d, "in.csv"),
            ["t", "power_kw", "kettle_on", "fridge_W"],
            [["2024-01-01 00:00:00", 5.0, 0, 5], ["2024-01-01 00:00:10", 6.0, 1, 5]],
        )
        _, apps, S = eda_shelly.load_csv(p)
    w = " | ".join(S["warnings"])
    assert "timestamp column guessed as 't'" in w
    assert "power column guessed by heuristic as 'power_kw'" in w
    assert "looks like kW" in w
    assert "ON flag 'kettle_on' has no matching 'kettle_power_W'" in w
    assert "'fridge_W' looks like a power channel" in w
    assert apps == {}


def test_schema_clean_on_wellformed():
    with tempfile.TemporaryDirectory() as d:
        p = _csv(
            os.path.join(d, "in.csv"),
            ["timestamp", "active_power_W", "kettle_power_W", "kettle_on"],
            [["2024-01-01 00:00:00", 100, 0, 0], ["2024-01-01 00:00:10", 110, 2000, 1]],
        )
        _, _, S = eda_shelly.load_csv(p)
    assert S["warnings"] == []


def test_compute_metrics_smoke():
    n = 3 * 24
    ts = pd.date_range("2024-01-01", periods=n, freq="h")
    evening = (ts.hour >= 18) & (ts.hour < 21)
    df = pd.DataFrame({"ts": ts, "power": np.where(evening, 820.0, 120.0)})
    apps = {"heater": np.where(evening, 700.0, 0.0)}
    m = eda_shelly.compute_metrics(df, apps)
    assert m["sampling"]["rows"] == n and m["sampling"]["dt_median_s"] == 3600.0
    assert set(m) >= {"sampling", "power", "steps", "diurnal", "appliances", "overlap"}
    assert m["appliances"]["heater"]["duty_pct"] == 12.5


def test_reference_roundtrip_synthetic_fixture():
    if not os.path.exists(FIXTURE):
        print("SKIP: client repo not staged (repo/WattWiser)")
        return
    with open(STORED_REF) as f:
        ref = json.load(f)
    df, apps, S = eda_shelly.load_csv(FIXTURE)
    assert sorted(apps) == ["fridge", "kettle", "microwave", "washing_machine"]
    joined = " | ".join(S["warnings"])
    assert "guessed" not in joined and "_on" not in joined  # ts/power exact, flags have siblings
    assert all("apparent_power_VA" in w for w in S["warnings"])  # the only power-suffixed extra
    rows = eda_shelly.compare(eda_shelly.compute_metrics(df, apps), ref)
    assert len(rows) == 10
    assert all(r["verdict"] in ("PASS", "FLAG", "MODERATE") for r in rows)
    dt = next(r for r in rows if r["metric"] == "dt median (s)")
    assert dt["verdict"] == "FLAG"  # 5 s synthetic vs 6 s reference, by construction


def test_ukdale_reference_rebuild():
    """Old nb_validate cases 1+2: the stored reference must be reproducible from the
    staged slice, and must judge all-PASS against itself. Slow (~1 min loadtxt).

    Provenance (2026-09-21 forensics): the staged slice is UK-DALE house-5 data
    relabeled house_1-style with a synthetic aggregate - this checks reproducibility
    from the same input, not house_1 identity. See the eda_shelly module docstring."""
    if not os.path.exists(os.path.join(UKDALE_SLICE, "channel_1.dat")):
        print("SKIP: UK-DALE slice not staged (research-logs)")
        return
    with open(STORED_REF) as f:
        ref = json.load(f)
    df, apps, _ = eda_shelly.load_ukdale()
    m = eda_shelly.compute_metrics(df, apps)
    for k in ("sampling", "power", "steps", "diurnal", "appliances", "overlap"):
        assert m[k] == ref[k], k
    assert all(r["verdict"] == "PASS" for r in eda_shelly.compare(m, ref))


def test_cli_end_to_end():
    if not os.path.exists(FIXTURE):
        print("SKIP: client repo not staged (repo/WattWiser)")
        return
    with tempfile.TemporaryDirectory() as d:
        r = subprocess.run(
            [sys.executable, os.path.join(ROOT, "deprecated", "analysis", "eda_shelly.py"), FIXTURE,
             "--reference", STORED_REF, "--out", d],
            capture_output=True, text=True, timeout=900, cwd=ROOT,
        )
        assert r.returncode == 0, r.stderr[-2000:]
        assert os.path.exists(os.path.join(d, "eda_fig01_ladder.png"))
        report = open(os.path.join(d, "report.md")).read()
        assert "## Schema" in report and "Domain shift" in report
        m = json.load(open(os.path.join(d, "metrics.json")))
        assert m["schema"]["appliance_columns"] == [
            "fridge", "kettle", "microwave", "washing_machine",
        ]


if __name__ == "__main__":
    import traceback

    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = []
    for name, fn in tests:
        try:
            fn()
            print("PASS %s" % name)
        except Exception:
            failed.append(name)
            print("FAIL %s" % name)
            traceback.print_exc()
    print("%d/%d passed" % (len(tests) - len(failed), len(tests)))
    sys.exit(1 if failed else 0)
