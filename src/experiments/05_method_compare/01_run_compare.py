"""Batch runner for the method comparison (rules vs FHMM vs seq2seq).

Stages (default: all three in order):
  train    fit the cross-home seq2seq, one net per device, on the pre-split
           spans of the 20 development homes -> data/results/method_compare/seq2seq/
  predict  every home x method x seed -> metrics.csv, plus one prediction
           file per home (seed 2026) for the explorer notebook
  summary  print the comparison tables from metrics.csv

Usage:
  uv run python3 src/experiments/05_method_compare/01_run_compare.py [stage ...]
      [--homes refit/house_2,...] [--workers 6]
"""
from __future__ import annotations

import argparse
import multiprocessing as mp
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compare_lib as cl  # noqa: E402


def stage_train(homes: list[dict]) -> None:
    import torch
    torch.set_num_threads(4)  # the box is shared; 8 threads oversubscribe it
    cl.S2S_DIR.mkdir(parents=True, exist_ok=True)
    dev_homes = [h for h in homes if h["group"] == "dev"]
    rng = np.random.default_rng(cl.S2S["seed"])
    data = {d: ([], []) for d in cl.DEVICES}
    for h in dev_homes:
        t0 = time.time()
        home = cl.load_home(h["tag"], h["group"])
        for d in home["plan"]["devs"]:
            got = cl.s2s_training_windows(home, d, rng)
            if got is not None:
                data[d][0].append(got[0])
                data[d][1].append(got[1])
        print(f"  windows from {h['tag']} ({time.time() - t0:.0f}s)", flush=True)
        del home
    for d, (xs, ys) in data.items():
        if not xs:
            print(f"  {d}: no training homes, skipped")
            continue
        X, Y = np.concatenate(xs), np.concatenate(ys)
        print(f"  training {d}: {len(X)} windows from {len(xs)} homes", flush=True)
        net = cl.s2s_train(X, Y)
        torch.save(net.state_dict(), cl.s2s_path(d))


def _job(h: dict) -> list[dict]:
    import torch
    torch.set_num_threads(1)
    t0 = time.time()
    home = cl.load_home(h["tag"], h["group"])
    devs = home["plan"]["devs"]
    base = {"tag": h["tag"], "group": h["group"], "dataset": h["tag"].split("/")[0]}
    rows, preds, saved_calib = [], {}, None
    for d in devs:
        rows.append({**base, "device": d, "method": cl.REFERENCE, "seed": -1,
                     **cl.score(np.zeros(len(home["ts_e"]), np.float32), home, d)})
        net = cl.load_s2s(d)
        if net is not None:
            w = cl.s2s_predict(net, home["feed_e"])
            preds[("seq2seq", d)] = w
            rows.append({**base, "device": d, "method": "seq2seq", "seed": -1,
                         **cl.score(w, home, d)})
    for seed in cl.SEEDS:
        calib = cl.calibrate(home, seed)
        if calib is None:
            continue
        out = {"rules": cl.run_rules(home, calib, seed, with_thr=False),
               "rules_gt_thr": cl.run_rules(home, calib, seed, with_thr=True),
               "fhmm": cl.run_fhmm(home, calib)}
        for m, pm in out.items():
            for d in devs:
                rows.append({**base, "device": d, "method": m, "seed": seed,
                             **cl.score(pm[d], home, d)})
                if seed == cl.PRED_SEED:
                    preds[(m, d)] = pm[d]
        if seed == cl.PRED_SEED:
            saved_calib = calib
    cl.save_preds(home, preds, saved_calib)
    print(f"  {h['tag']:18s} {len(devs)} devices, {len(rows)} rows "
          f"({time.time() - t0:.0f}s)", flush=True)
    return rows


def stage_predict(homes: list[dict], workers: int) -> None:
    rows = []
    ctx = mp.get_context("fork")
    with ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as ex:
        for r in ex.map(_job, homes):
            rows.extend(r)
    df = pd.DataFrame(rows)
    if cl.METRICS_CSV.exists() and len(homes) < len(cl.home_list()):
        old = pd.read_csv(cl.METRICS_CSV)
        df = pd.concat([old[~old["tag"].isin({h["tag"] for h in homes})], df])
    cl.RESULTS.mkdir(parents=True, exist_ok=True)
    df.to_csv(cl.METRICS_CSV, index=False)
    print(f"  wrote {cl.METRICS_CSV} ({len(df)} rows)")


def summarize(df: pd.DataFrame) -> dict:
    """Per (group, method, device): median over seeds per pair, then the
    mean over pairs. Returns {group: DataFrame} for printing/plotting."""
    per_pair = (df.groupby(["group", "tag", "device", "method"], as_index=False)
                  .median(numeric_only=True))
    cols = ["f1", "precision", "recall", "nde", "ea", "daily_energy_err",
            "total_energy_err", "mae_w", "mae_zero_w"]
    out = {}
    for g, sub in per_pair.groupby("group"):
        t = sub.groupby(["method", "device"])[cols].mean()
        allrow = sub.groupby("method")[cols].mean()
        allrow["device"] = "ALL"
        out[g] = pd.concat([t.reset_index(),
                            allrow.reset_index()]).set_index(["method", "device"])
    return out


def stage_summary() -> None:
    df = cl.load_metrics()
    pd.set_option("display.width", 200)
    for g, t in summarize(df).items():
        n = df[df.group == g][["tag", "device"]].drop_duplicates().shape[0]
        print(f"\n=== {g} homes ({n} device-home pairs); mean over pairs")
        print(t.round(3).to_string())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stages", nargs="*", default=["train", "predict", "summary"])
    ap.add_argument("--homes", default="")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    homes = cl.home_list()
    if a.homes:
        want = set(a.homes.split(","))
        homes = [h for h in homes if h["tag"] in want]
    for s in a.stages:
        print(f"--- stage {s}", flush=True)
        t0 = time.time()
        if s == "train":
            stage_train(cl.home_list())
        elif s == "predict":
            stage_predict(homes, a.workers)
        elif s == "summary":
            stage_summary()
        else:
            raise SystemExit(f"unknown stage {s}")
        print(f"--- stage {s} done in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
