"""Mechanism check (plan section 7, Phase 0 - must precede any FHMM run).

Per house and device: session-derived ON level vs the always-on floor +
noise band; pairwise emission sums vs observed joint levels. Writes the
recoverable-overlap map (JSON + markdown) with written separability
predictions, frozen before the runs so the experiment cannot be tuned
around its own predictions.

Run: .venv/bin/python3 src/experiments/01_fhmm/00_mechanism_check.py
"""
import itertools
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '00_baseline'))
import baseline_lib as bl  # noqa: E402
import fhmm_lib as f  # noqa: E402

DATASET = "ukdale"
HOUSES = ["house_1", "house_2", "house_5"]
# plan section 2: score per device only where press/GT coverage exists;
# dishwasher house_1 has no marks, microwave house_5 channel has no signal
ENROLLED = {
    "house_1": ["washing_machine", "kettle", "microwave", "fridge"],
    "house_2": ["washing_machine", "dishwasher", "kettle", "microwave", "fridge"],
    "house_5": ["washing_machine", "dishwasher", "kettle", "fridge"],
}
EXCLUDED_NOTE = {
    ("house_1", "dishwasher"): "no gold_annot marks at all (Appendix A)",
    ("house_5", "microwave"): "channel reads a constant ~50 W; profile excluded",
}
CAD = 6.0
FROZEN_COVER = f.FROZEN["interference_max_cover"]


def session_sets(dataset, house, cfg, ts, w, floor_w, rng):
    """Valid sessions (or passive-profile windows for the fridge) per device."""
    split = cfg["split_us"]
    pools, ests, gt_eps = {}, {}, {}
    for dev in ENROLLED[house]:
        d = cfg["devices"][dev]
        gt_eps[dev] = f.eval_episodes(dataset, house, dev, d, None, split)
        if dev == "fridge":
            ests[dev] = f.fridge_passive_params(dataset, house, d, floor_w,
                                                8.0, split, CAD)  # sigma_off unused inside
            pools[dev] = gt_eps[dev]
            continue
        pool = f.press_pool(dataset, house, dev, split)
        pools[dev] = pool
        others = {o: p for o, p in pools.items() if o != dev and len(p)}
        if len(pool) == 0:
            ests[dev] = None
            continue
        k = min(20, len(pool))
        valid, attempts = f.sample_valid_sessions(pool, k, rng, others,
                                                  FROZEN_COVER)
        ests[dev] = f.estimate_device_params(ts, w, floor_w, valid, CAD)
    return pools, ests, gt_eps


def verdict_for(mu_w, floor_w, sigma_off):
    margin = (mu_w - floor_w) / sigma_off
    if margin >= 4.0:
        v = "clear"
    elif margin >= 2.0:
        v = "marginal"
    else:
        v = "sub-noise"
    return v, margin


def pairwise(dataset, house, cfg, ts, w, floor_w, ests, gt_eps):
    """Observed joint level over overlapping GT episodes vs the emission sum."""
    rows = []
    for a, b in itertools.combinations(ENROLLED[house], 2):
        ea, eb = gt_eps[a], gt_eps[b]
        if ests.get(a) is None or ests.get(b) is None or len(ea) == 0 or len(eb) == 0:
            rows.append({"house": house, "pair": a + "+" + b, "n_overlaps": 0})
            continue
        a_on = ea["t_on_us"].to_numpy(np.int64)
        a_off = ea["t_off_us"].to_numpy(np.int64)
        b_on = eb["t_on_us"].to_numpy(np.int64)
        b_off = eb["t_off_us"].to_numpy(np.int64)
        obs = []
        for i in range(len(ea)):
            lo = np.maximum(b_on, a_on[i])
            hi = np.minimum(b_off, a_off[i])
            for lo_i, hi_i in zip(lo, hi):
                if hi_i - lo_i < 60_000_000:
                    continue
                i0 = int(np.searchsorted(ts, lo_i, side="left"))
                i1 = int(np.searchsorted(ts, hi_i, side="right"))
                if i1 - i0 < 5:
                    continue
                obs.append(float(np.mean(w[i0:i1])) - floor_w)
        if not obs:
            rows.append({"house": house, "pair": a + "+" + b, "n_overlaps": 0})
            continue
        obs = np.array(obs)
        pred_sum = ests[a]["mu_w"] + ests[b]["mu_w"]
        ratio = obs / pred_sum if pred_sum > 0 else np.full(len(obs), np.nan)
        rows.append({
            "house": house, "pair": a + "+" + b, "n_overlaps": len(obs),
            "pred_sum_w": round(pred_sum, 1),
            "obs_p50_w": round(float(np.percentile(obs, 50)), 1),
            "obs_p10_w": round(float(np.percentile(obs, 10)), 1),
            "obs_p90_w": round(float(np.percentile(obs, 90)), 1),
            "ratio_p50": round(float(np.nanpercentile(ratio, 50)), 2),
        })
    return rows


def main():
    rng = np.random.default_rng(f.FROZEN["seed_base"])
    out = {"houses": {}, "excluded": {h + "/" + d: note
                                      for (h, d), note in EXCLUDED_NOTE.items()}}
    md = ["# FHMM mechanism check (Phase 0, plan section 7)", ""
          "Frozen before any FHMM run. Levels are session-derived from the "
          "aggregate over GT intervals only (parity rule); floors are the "
          "pre-split p10/MAD estimates. Margin = (level - floor) / sigma_off.", ""]
    for house in HOUSES:
        cfg = f.house_config(DATASET, house)
        bg = f.background_estimates(DATASET, house, cfg["split_us"])
        floor_w, sig = bg["floor_w"], bg["sigma_off_w"]
        mains = bl.load_series(bl.gold_file(DATASET, house, "mains"))
        ts = mains["ts_us"].to_numpy(np.int64)
        w = mains["w"].to_numpy(float)
        pools, ests, gt_eps = session_sets(DATASET, house, cfg, ts, w, floor_w, rng)
        hdev = {}
        md += ["## " + house, ""
               "floor " + str(round(floor_w, 1)) + " W, sigma_off " + str(round(sig, 1)) + " W", ""
               "| device | n_sess | level W | sd W | dwell s | margin (sd) | verdict |",
               "|---|---|---|---|---|---|---|"]
        for dev in ENROLLED[house]:
            est = ests.get(dev)
            pool = pools.get(dev)
            if est is None:
                hdev[dev] = {"n_sessions": int(len(pool)), "level_w": None,
                             "verdict": "no-separable-level"}
                md.append("| " + dev + " | " + str(len(pool)) + " | - | - | - | - | no separable level |")
                continue
            v, margin = verdict_for(est["mu_w"], floor_w, sig)
            hdev[dev] = {
                "n_sessions": int(len(pool)),
                "level_w": round(est["mu_w"], 1),
                "sd_w": round(est["sd_w"], 1),
                "dwell_s": round(est["dwell_s"], 1),
                "margin_sd": round(margin, 2),
                "verdict": v,
            }
            md.append("| " + dev + " | " + str(len(pool)) + " | " + str(round(est["mu_w"], 1))
                      + " | " + str(round(est["sd_w"], 1)) + " | " + str(round(est["dwell_s"]))
                      + " | " + str(round(margin, 1)) + " | " + v + " |")
        pr = pairwise(DATASET, house, cfg, ts, w, floor_w, ests, gt_eps)
        out["houses"][house] = {
            "floor_w": round(floor_w, 2),
            "sigma_off_w": round(sig, 2),
            "devices": hdev,
            "pairs": pr,
        }
        md += ["", "| pair | n_overlaps | pred sum W | obs p50 W | ratio p50 |",
               "|---|---|---|---|---|"]
        for r in pr:
            if r["n_overlaps"] == 0:
                md.append("| " + r["pair"] + " | 0 | - | - | - |")
            else:
                md.append("| " + r["pair"] + " | " + str(r["n_overlaps"]) + " | "
                          + str(r["pred_sum_w"]) + " | " + str(r["obs_p50_w"]) + " | "
                          + str(r["ratio_p50"]) + " |")
        md.append("")
    # written predictions (H04 transfer), frozen before any score exists
    preds = []
    for house in HOUSES:
        for dev, d in out["houses"][house]["devices"].items():
            if d.get("verdict") in (None, "no-separable-level"):
                preds.append(house + "/" + dev + ": NOT separable from the floor by the "
                             "session estimate - H04 predicted to transfer (FHMM "
                             "cannot lift it); expect poor recall, not a tuning target.")
            elif d["verdict"] == "sub-noise":
                preds.append(house + "/" + dev + ": level within 2 sigma_off of the floor "
                             "- marginal; expect intermittent claims.")
            else:
                preds.append(house + "/" + dev + ": clear at " + str(d["margin_sd"])
                             + " sigma_off above the floor - FHMM should separate it from ambient.")
    out["predictions"] = preds
    md += ["## Written predictions (frozen pre-run)", ""] + ["- " + p for p in preds]
    os.makedirs("docs/reports/fhmm", exist_ok=True)
    with open("docs/reports/fhmm/mechanism_check.json", "w") as fh:
        json.dump(f.jsonable(out), fh, indent=1)
    with open("docs/reports/fhmm/mechanism_check.md", "w") as fh:
        fh.write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()