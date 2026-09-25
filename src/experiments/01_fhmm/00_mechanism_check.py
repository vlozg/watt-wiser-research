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
import fhmm_lib as fhmm  # noqa: E402

from wattwiser.experiments.data_loader import gold_parquet_path, load_power_series  # noqa: E402

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
FROZEN_COVER = fhmm.FROZEN["interference_max_cover"]


def calibration_inputs(dataset, house, cfg, ts, w, floor_w, rng):
    """Per-device calibration inputs: simulated presses, estimated emission
    params from valid sessions (or the fridge passive-profile windows), and
    the evaluation GT episodes - all from the pre-split span only."""
    # flow: per device -> (press pool, emission params, GT episodes); the fridge
    #   uses its duty intervals as the pool and the passive profile as params
    split = cfg["split_us"]
    press_pools, param_estimates, gt_eps = {}, {}, {}
    for device in ENROLLED[house]:
        rule = cfg["devices"][device]
        gt_eps[device] = fhmm.evaluation_gt_episodes(dataset, house, device, rule, None, split)
        if device == "fridge":
            param_estimates[device] = fhmm.fridge_passive_params(dataset, house, rule, floor_w,
                                                8.0, split, CAD)  # sigma_off_w unused inside
            press_pools[device] = gt_eps[device]
            continue
        presses = fhmm.simulated_presses(dataset, house, device, split)
        press_pools[device] = presses
        others = {o: p for o, p in press_pools.items() if o != device and len(p)}
        if len(presses) == 0:
            param_estimates[device] = None
            continue
        k = min(20, len(presses))
        valid, attempts = fhmm.sample_valid_sessions(presses, k, rng, others,
                                                  FROZEN_COVER)
        param_estimates[device] = fhmm.estimate_device_params(ts, w, floor_w, valid, CAD)
    return press_pools, param_estimates, gt_eps


def verdict_for(mu_w, floor_w, sigma_off_w):
    """Separability verdict: clear at >= 4 sigma_off_w above the floor,
    marginal at >= 2, else sub-noise."""
    # flow: (level, floor, noise width) -> margin in sigmas -> verdict
    margin = (mu_w - floor_w) / sigma_off_w
    if margin >= 4.0:
        v = "clear"
    elif margin >= 2.0:
        v = "marginal"
    else:
        v = "sub-noise"
    return v, margin


def pairwise_overlap_check(dataset, house, cfg, ts, w, floor_w, param_estimates, gt_eps):
    """Observed joint level over overlapping GT episodes vs the emission sum."""
    # flow: per device pair -> overlapping GT stretches -> observed joint watts
    #   above floor -> vs the predicted sum of the two levels
    rows = []
    for a, b in itertools.combinations(ENROLLED[house], 2):
        ea, eb = gt_eps[a], gt_eps[b]
        if param_estimates.get(a) is None or param_estimates.get(b) is None or len(ea) == 0 or len(eb) == 0:
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
                    # overlaps shorter than 1 minute are skipped
                    continue
                i0 = int(np.searchsorted(ts, lo_i, side="left"))
                i1 = int(np.searchsorted(ts, hi_i, side="right"))
                if i1 - i0 < 5:
                    continue
                obs.append(float(np.mean(w[i0:i1])) - floor_w)
                # observed joint watts above the floor during the overlap
        if not obs:
            rows.append({"house": house, "pair": a + "+" + b, "n_overlaps": 0})
            continue
        obs = np.array(obs)
        pred_sum = param_estimates[a]["mu_w"] + param_estimates[b]["mu_w"]
        # the additive prediction: the two claimed levels simply add
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
    rng = np.random.default_rng(fhmm.FROZEN["seed_base"])
    out = {"houses": {}, "excluded": {h + "/" + d: note
                                      for (h, d), note in EXCLUDED_NOTE.items()}}
    # flow: per house: floor/noise -> calibration inputs -> device verdicts +
    #   pair additivity -> frozen written predictions -> JSON + markdown
    md = ["# FHMM mechanism check (Phase 0, plan section 7)", ""
          "Frozen before any FHMM run. How to read the tables below:", ""
          "- Ground truth (GT): the hand-annotated device cycle marks; a press is "
          "one cycle read as a simulated start/stop button press.",
          "- Parity rule: calibration windows come from GT marks; the aggregate "
          "supplies the watts; submeters are never a model input.",
          "- floor / sigma_off: the aggregate's always-on base level (10th-percentile "
          "watts) and the noise width around it (1.4826 x MAD), estimated over the "
          "pre-split span.",
          "- margin: a device's mean ON level minus the floor, in sigmas of the "
          "noise. >= 4 clear, >= 2 marginal, else sub-noise: not separable from "
          "background.",
          "- Pair tables: when two devices run together, the predicted sum of their "
          "levels vs the observed median level - how close the additive model is.", ""]
    for house in HOUSES:
        cfg = fhmm.house_config(DATASET, house)
        floor_noise = fhmm.estimate_floor_noise(DATASET, house, cfg["split_us"])
        floor_w, sigma_off_w = floor_noise["floor_w"], floor_noise["sigma_off_w"]
        mains = load_power_series(gold_parquet_path(DATASET, house, "mains"))
        ts = mains["ts_us"].to_numpy(np.int64)
        w = mains["w"].to_numpy(float)
        press_pools, param_estimates, gt_eps = calibration_inputs(DATASET, house, cfg, ts, w, floor_w, rng)
        # all calibration facts land before any scoring exists (frozen order)
        device_reports = {}
        md += ["## " + house, ""
               "floor " + str(round(floor_w, 1)) + " W, sigma_off " + str(round(sigma_off_w, 1)) + " W", ""
               "| device | n_sess | level W | sd W | dwell s | margin (sd) | verdict |",
               "|---|---|---|---|---|---|---|"]
        for device in ENROLLED[house]:
            param_est = param_estimates.get(device)
            presses = press_pools.get(device)
            if param_est is None:
                device_reports[device] = {"n_sessions": int(len(presses)), "level_w": None,
                             "verdict": "no-separable-level"}
                md.append("| " + device + " | " + str(len(presses)) + " | - | - | - | - | no separable level |")
                continue
            v, margin = verdict_for(param_est["mu_w"], floor_w, sigma_off_w)
            device_reports[device] = {
                "n_sessions": int(len(presses)),
                "level_w": round(param_est["mu_w"], 1),
                "sd_w": round(param_est["sd_w"], 1),
                "dwell_s": round(param_est["dwell_s"], 1),
                "margin_sd": round(margin, 2),
                "verdict": v,
            }
            md.append("| " + device + " | " + str(len(presses)) + " | " + str(round(param_est["mu_w"], 1))
                      + " | " + str(round(param_est["sd_w"], 1)) + " | " + str(round(param_est["dwell_s"]))
                      + " | " + str(round(margin, 1)) + " | " + v + " |")
        pr = pairwise_overlap_check(DATASET, house, cfg, ts, w, floor_w, param_estimates, gt_eps)
        # additivity: does mu_a + mu_b predict the observed joint level?
        out["houses"][house] = {
            "floor_w": round(floor_w, 2),
            "sigma_off_w": round(sigma_off_w, 2),
            "devices": device_reports,
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
        for device, report in out["houses"][house]["devices"].items():
            if report.get("verdict") in (None, "no-separable-level"):
                preds.append(house + "/" + device + ": NOT separable from the floor by the "
                             "session estimate - H04 predicted to transfer (FHMM "
                             "cannot lift it); expect poor recall, not a tuning target.")
            elif report["verdict"] == "sub-noise":
                preds.append(house + "/" + device + ": level within 2 sigma_off of the floor "
                             "- marginal; expect intermittent claims.")
            else:
                preds.append(house + "/" + device + ": clear at " + str(report["margin_sd"])
                             + " sigma_off above the floor - FHMM should separate it from ambient.")
    out["predictions"] = preds
    md += ["## Written predictions (frozen pre-run)", ""] + ["- " + p for p in preds]
    os.makedirs("docs/reports/fhmm", exist_ok=True)
    with open("docs/reports/fhmm/mechanism_check.json", "w") as fh:
        json.dump(fhmm.jsonable(out), fh, indent=1)
    with open("docs/reports/fhmm/mechanism_check.md", "w") as fh:
        fh.write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()