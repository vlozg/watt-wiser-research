"""Shared helpers for the method comparison: rules vs FHMM vs seq2seq.

One harness for every method, so the numbers are comparable:
  - homes: the bench-v4 pool (20 development homes) plus its 7 unseen
    holdout homes, across UK-DALE, REFIT and ECO (.auto/pool_v4.json);
  - enrollment: bench v4's simulated button presses (K=5 marks per device,
    +-30 s press jitter, 60 s pre-roll; fridge = one passive 3 h window),
    drawn per seed from the pre-split history;
  - evaluation: the first 90 post-split days at 6 s, scored against the
    union of the device's sane submeter channels.

Methods (all see only the aggregate at run time):
  rules         autoresearch model.py, product-safe: the scorer's
                thresholds are withheld from the model (meta['thresholds']
                = {}), since a real home has no submeter to derive them
  rules_gt_thr  the same model as benchmarked, reading the scorer's
                thresholds (2 x thr = the submeter median draw)
  fhmm          fhmm_lib's factorial HMM, calibrated from the same marks
  seq2seq       dilated 1-D CNN trained across homes on the development
                homes' pre-split submeter data (no marks, no target-home
                labels); on the development homes it is a seen-home test
  zero          predicts 0 W everywhere - the reference every regression
                metric is read against

Metrics per (home, device): cycle-level precision/recall/F1 (bench v4's
scorer) and regression metrics chosen so an all-zero prediction cannot
look good: NDE (zero -> 1), energy accuracy EA (zero -> 0.5), total and
daily energy error (zero -> 1), plus plain MAE beside its all-zero value.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
RESULTS = ROOT / "data" / "results" / "method_compare"
sys.path.insert(0, str(ROOT / ".auto"))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "experiments" / "01_fhmm"))

import bench as v1  # noqa: E402

v1.CACHE_DIR = RESULTS / "cache"  # span caches live with these results
import bench_v2 as v2  # noqa: E402
import bench_v3 as v3  # noqa: E402
import bench_v4 as b4  # noqa: E402
import fhmm_lib as fl  # noqa: E402
import pool_v4 as p4  # noqa: E402
from wattwiser.experiments import evaluation as ev  # noqa: E402

DEVICES = b4.DEV_ORDER
CAD_S = 6.0
DAY_US = 86_400_000_000
SEEDS = (2026, 1, 2)
PRED_SEED = 2026  # the seed whose predictions are saved for the notebook
METHODS = ("rules", "rules_gt_thr", "fhmm", "seq2seq")
REFERENCE = "zero"
RULES_MODEL = ROOT / "src" / "experiments" / "04_autoresearch" / "model.py"
S2S_DIR = RESULTS / "seq2seq"
PRED_DIR = RESULTS / "preds"
METRICS_CSV = RESULTS / "metrics.csv"


# ---------------------------------------------------------------- homes

def home_list() -> list[dict]:
    """Every scored home: 20 development homes, then the 7 unseen ones."""
    pool = b4.load_pool()
    return ([{"tag": t, "group": "dev"} for t in pool["pool_houses"]]
            + [{"tag": t, "group": "unseen"} for t in pool["holdout"]])


def home_pairs(tag: str, group: str) -> dict:
    """{device: pair record} - frozen pool pairs, or the holdout's
    eligibility re-derived GT-only by pool_v4.eval_house (cached)."""
    if group == "dev":
        return b4.pairs_of(b4.load_pool(), tag)
    # one file per home: runner workers resolve homes in parallel
    cache = RESULTS / "holdout_pairs" / (tag.replace("/", "_") + ".json")
    if cache.exists():
        pairs = json.loads(cache.read_text())
    else:
        ds, house = tag.split("/", 1)
        pairs = p4.eval_house((ds, house)).get("pairs") or {}
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(pairs, indent=1, sort_keys=True))
    return {d: pairs[d] for d in DEVICES if d in pairs}


def _device_power(cmap_d: list, span_devs: dict) -> tuple[np.ndarray, np.ndarray]:
    """GT mask (union of sane channels above threshold) and GT watts (sum
    of the same channels) for one device over one span."""
    mask, used = p4._union_mask(cmap_d, span_devs, smooth=False)
    watts = np.zeros(len(mask), np.float32)
    for ch in used:
        watts += np.nan_to_num(span_devs[ch]).astype(np.float32)
    return mask, watts


def load_home(tag: str, group: str) -> dict:
    """Pre-split history + 90-day eval span for one home, with GT."""
    pairs = home_pairs(tag, group)
    plan = b4.make_plan(tag, pairs)
    ds, house = plan["ds"], plan["house"]
    pspan = v3.load_span(ds, house, plan["pre_lo"], plan["pre_hi"],
                         plan["pre_tag"], plan["chans"])
    espan = v3.load_span(ds, house, plan["ev_lo"], plan["ev_hi"],
                         "v4eval90d", plan["chans"])
    cmap = p4.canon_channels(ds, house)
    pre_mask, pre_w, gt_mask, gt_w = {}, {}, {}, {}
    for d in plan["devs"]:
        pre_mask[d], pre_w[d] = _device_power(cmap[d], pspan["devices"])
        gt_mask[d], gt_w[d] = _device_power(cmap[d], espan["devices"])
    return {"tag": tag, "group": group, "plan": plan,
            "ts_p": pspan["ts_us"], "feed_p": b4._fill(pspan["mains"]),
            "ts_e": espan["ts_us"], "feed_e": b4._fill(espan["mains"]),
            "mains_e": espan["mains"].astype(np.float32),
            "pre_mask": pre_mask, "pre_w": pre_w,
            "gt_mask": gt_mask, "gt_w": gt_w}


def calibrate(home: dict, seed: int) -> dict | None:
    """bench v4's simulated enrollment for one seed (same marks for all)."""
    plan = home["plan"]
    return b4._calib(home["ts_p"], home["feed_p"], home["pre_mask"],
                     plan["devs"], plan["thr"], seed)


def _meta(plan: dict, seed: int, with_thr: bool) -> dict:
    return {"devices": list(plan["devs"]),
            "thresholds": dict(plan["thr"]) if with_thr else {},
            "device_class": {d: v2.DEVICE_CLASS[d] for d in plan["devs"]},
            "cadence_s": 6, "cadence_us": v1.CADENCE_US,
            "k_calib": v2.K_CALIB, "tau_onset_s": dict(v2.TAU_ONSET_S),
            "merge_s": dict(v2.MERGE_S), "duration_band": v2.DURATION_BAND,
            "press_jitter_s": v2.PRESS_JITTER_S, "pre_roll_s": v2.PRE_ROLL_S,
            "split_us": plan["split_us"], "seeds": [seed], "bench": "compare"}


# ---------------------------------------------------------------- rules

_RULES = None


def _rules_module():
    global _RULES
    if _RULES is None:
        spec = importlib.util.spec_from_file_location("ar_rules", RULES_MODEL)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["ar_rules"] = mod
        spec.loader.exec_module(mod)
        _RULES = mod
    return _RULES


def run_rules(home: dict, calib: dict, seed: int, with_thr: bool) -> dict:
    ctx = {"meta": _meta(home["plan"], seed, with_thr), "calib": calib,
           "pre": {"ts_us": home["ts_p"], "mains": home["feed_p"]},
           "pretrain": None}
    with contextlib.redirect_stdout(io.StringIO()):
        fn = _rules_module().build_and_train(ctx)
        pred = fn(home["feed_e"])
    return {d: np.nan_to_num(np.asarray(pred[d], np.float32))
            for d in home["plan"]["devs"]}


# ---------------------------------------------------------------- fhmm

def _floor_noise(w: np.ndarray) -> tuple[float, float]:
    """fhmm_lib.estimate_floor_noise on an in-memory series."""
    x = w[::7].astype(float)
    floor = float(np.percentile(x, 10))
    r = x - floor
    mad = float(np.median(np.abs(r - np.median(r))))
    return floor, float(max(1.4826 * mad, 1.0))


def _fridge_passive(seg: np.ndarray) -> dict | None:
    """Fridge level from the passive 3 h window: median of the upward
    steps in a compressor-sized band. The original fhmm_lib fridge profile
    reads GT duty intervals, which a real home does not have."""
    s = np.asarray(seg, float)
    if len(s) < 10:
        return None
    step = s[2:] - s[:-2]
    ups = step[(step >= 30.0) & (step <= 400.0)]
    if len(ups) < 3:
        return None
    mu = float(np.median(ups))
    dwell = 1200.0  # typical compressor ON time; no labels to fit it from
    return {"mu_w": mu, "sd_w": max(8.0, fl.FROZEN["sigma_floor_w"]),
            "p_on_stay": 1.0 - 1.0 / max(dwell / CAD_S, 1.0), "dwell_s": dwell}


def run_fhmm(home: dict, calib: dict) -> dict:
    devs = home["plan"]["devs"]
    floor, sigma_off = _floor_noise(home["feed_p"])
    roll_us = int(v2.PRE_ROLL_S * 1e6)
    mu = np.zeros((1, len(devs)), np.float32)
    sd = np.zeros((1, len(devs)), np.float32)
    p_on = np.zeros((1, len(devs)), np.float32)
    for i, d in enumerate(devs):
        c = calib[d]
        if d == "fridge":
            est = _fridge_passive(c["mains_seg"][0]) if c["mains_seg"] else None
        else:
            m = np.asarray(c["marks_us"], np.int64).reshape(-1, 2)
            # marks carry the protocol's 60 s pre-roll on both sides; trim it
            on, off = m[:, 0] + roll_us, m[:, 1] - roll_us
            keep = off > on + 12_000_000
            sess = pd.DataFrame({"t_on_us": np.where(keep, on, m[:, 0]),
                                 "t_off_us": np.where(keep, off, m[:, 1])})
            est = fl.estimate_device_params(home["ts_p"], home["feed_p"],
                                            floor, sess, CAD_S)
        if est is None:  # mirror of the fhmm notebook's never-claims fallback
            mu[0, i], sd[0, i] = floor, fl.FROZEN["sigma_floor_w"]
            p_on[0, i] = 1.0 - CAD_S / 3600.0
        else:
            mu[0, i], sd[0, i], p_on[0, i] = est["mu_w"], est["sd_w"], est["p_on_stay"]
    params = {"mu": mu, "sd": sd, "p_on_stay": p_on,
              "sigma_off": np.array([sigma_off], np.float32), "floor_w": floor}
    ts = home["ts_e"]
    dec = fl.decode_batch(ts, home["feed_e"], int(ts[0]), int(ts[-1]),
                          list(devs), params, CAD_S)
    return {d: fl.pred_power_series(dec, 0, i, float(mu[0, i])).astype(np.float32)
            for i, d in enumerate(devs)}


# ---------------------------------------------------------------- seq2seq

S2S = {"win": 512, "stride": 256, "ch": 24, "dilations": (2, 4, 8, 16, 32),
       "n_on": 1500, "n_rand": 1500, "epochs": 6, "batch": 128,
       "lr": 1e-3, "seed": 0, "scale_w": 1000.0}


def _s2s_net():
    import torch
    from torch import nn

    class Block(nn.Module):
        """Dilated residual block; batch norm keeps the residual sum from
        growing layer to layer (an unnormalized stack collapsed to a
        constant output in the first trial)."""

        def __init__(self, ch, dil):
            super().__init__()
            self.conv = nn.Conv1d(ch, ch, 5, padding=2 * dil, dilation=dil)
            self.bn = nn.BatchNorm1d(ch)

        def forward(self, x):
            return x + torch.nn.functional.leaky_relu(self.bn(self.conv(x)), 0.1)

    ch = S2S["ch"]
    # linear head: the loss sees the raw output; s2s_predict clamps at 0
    return nn.Sequential(nn.Conv1d(1, ch, 9, padding=4), nn.BatchNorm1d(ch),
                         nn.LeakyReLU(0.1),
                         *[Block(ch, d) for d in S2S["dilations"]],
                         nn.Conv1d(ch, 1, 1))


def _s2s_input(win: np.ndarray) -> np.ndarray:
    """Per-window baseline removal: subtract the window's 10th percentile,
    so the net sees steps above the local floor, not the home's base load."""
    base = np.percentile(win, 10, axis=-1, keepdims=True)
    return np.clip((win - base) / S2S["scale_w"], 0.0, 15.0).astype(np.float32)


def s2s_training_windows(home: dict, device: str, rng) -> tuple:
    """Balanced windows from one home's pre-split span: half centred on
    device-ON samples, half uniformly random."""
    x, y, m = home["feed_p"], home["pre_w"][device], home["pre_mask"][device]
    L = S2S["win"]
    n = len(x)
    if n < 2 * L:
        return None
    on_idx = np.flatnonzero(m)
    starts = []
    if len(on_idx):
        c = rng.choice(on_idx, size=S2S["n_on"])
        starts.append(np.clip(c - rng.integers(0, L, size=len(c)), 0, n - L))
    starts.append(rng.integers(0, n - L, size=S2S["n_rand"]))
    st = np.concatenate(starts)
    idx = st[:, None] + np.arange(L)[None, :]
    return _s2s_input(x[idx]), (y[idx] / S2S["scale_w"]).astype(np.float32)


def s2s_train(X: np.ndarray, Y: np.ndarray, log=print):
    import torch
    torch.manual_seed(S2S["seed"])
    net = _s2s_net()
    opt = torch.optim.AdamW(net.parameters(), lr=S2S["lr"])
    loss_fn = torch.nn.SmoothL1Loss(beta=0.05)
    Xt = torch.from_numpy(X[:, None, :])
    Yt = torch.from_numpy(Y[:, None, :])
    g = torch.Generator().manual_seed(S2S["seed"])
    for ep in range(S2S["epochs"]):
        perm = torch.randperm(len(Xt), generator=g)
        tot = 0.0
        for b in range(0, len(perm), S2S["batch"]):
            j = perm[b:b + S2S["batch"]]
            opt.zero_grad()
            loss = loss_fn(net(Xt[j]), Yt[j])
            loss.backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            opt.step()
            tot += float(loss.detach()) * len(j)
            if ep == 0 and b == 50 * S2S["batch"]:
                log(f"      first 50 batches done ({len(perm) // S2S['batch']} per epoch)")
        log(f"      epoch {ep + 1}/{S2S['epochs']}: loss {tot / len(Xt):.5f}")
    return net


def s2s_path(device: str) -> Path:
    return S2S_DIR / f"{device}.pt"


def s2s_predict(net, feed: np.ndarray) -> np.ndarray:
    """Overlapping windows, keeping only each window's central half."""
    import torch
    L, S = S2S["win"], S2S["stride"]
    q = (L - S) // 2
    n = len(feed)
    pad = np.concatenate([np.full(q, feed[0]), feed,
                          np.full(L + S, feed[-1])]).astype(np.float32)
    starts = np.arange(0, n, S)
    out = np.zeros(len(starts) * S, np.float32)
    net.eval()
    with torch.no_grad():
        for b in range(0, len(starts), 256):
            st = starts[b:b + 256]
            idx = st[:, None] + np.arange(L)[None, :]
            xb = torch.from_numpy(_s2s_input(pad[idx])[:, None, :])
            yb = net(xb)[:, 0, q:q + S].numpy()
            out[b * S:(b + len(st)) * S] = yb.reshape(-1)
    return (np.maximum(out[:n], 0.0) * S2S["scale_w"]).astype(np.float32)


def load_s2s(device: str):
    import torch
    p = s2s_path(device)
    if not p.exists():
        return None
    net = _s2s_net()
    net.load_state_dict(torch.load(p, map_location="cpu"))
    return net


# ---------------------------------------------------------------- metrics

def event_metrics(pred_w: np.ndarray, home: dict, device: str) -> dict:
    ts, thr = home["ts_e"], home["plan"]["thr"][device]
    gt = v2.cycles_from_mask(home["gt_mask"][device], ts, device)
    pe = v2.cycles_from_mask(pred_w > thr, ts, device)
    sc = ev.score_episodes(pe, gt, v2.TAU_ONSET_S[device] * 1e6,
                           v2.DURATION_BAND)
    return {"f1": float(sc["f1"]), "precision": float(sc["precision"]),
            "recall": float(sc["recall"]), "n_pred": int(len(pe)),
            "n_gt": int(len(gt))}


def regression_metrics(pred_w: np.ndarray, home: dict, device: str) -> dict:
    """Energy-first regression metrics. On a device that is OFF 99% of the
    time, MAE rewards predicting 0, so every metric here is either
    normalized by the device's own energy (all-zero -> a fixed, bad value)
    or reported beside its all-zero reference."""
    y = home["gt_w"][device].astype(np.float64)
    yh = np.maximum(np.nan_to_num(pred_w.astype(np.float64)), 0.0)
    ts = home["ts_e"]
    h = CAD_S / 3600.0
    e_true, e_pred = y.sum() * h, yh.sum() * h
    err = yh - y
    day = (ts - ts[0]) // DAY_US
    e_d = np.bincount(day, weights=y) * h
    eh_d = np.bincount(day, weights=yh) * h
    on = home["gt_mask"][device]
    sy, sy2 = y.sum(), (y ** 2).sum()
    return {
        "energy_true_kwh": e_true / 1000.0,
        "energy_pred_kwh": e_pred / 1000.0,
        "mae_w": float(np.abs(err).mean()),
        "mae_zero_w": float(y.mean()),
        "mae_on_w": float(np.abs(err[on]).mean()) if on.any() else float("nan"),
        "nde": float((err ** 2).sum() / sy2) if sy2 > 0 else float("nan"),
        "ea": float(1.0 - np.abs(err).sum() / (2.0 * sy)) if sy > 0 else float("nan"),
        "total_energy_err": float(abs(e_pred - e_true) / e_true) if e_true > 0 else float("nan"),
        "daily_energy_err": (float(np.abs(eh_d - e_d).mean() / e_d.mean())
                             if e_d.mean() > 0 else float("nan")),
    }


def score(pred_w: np.ndarray, home: dict, device: str) -> dict:
    return {**event_metrics(pred_w, home, device),
            **regression_metrics(pred_w, home, device)}


# ---------------------------------------------------------------- results

def pred_file(tag: str) -> Path:
    return PRED_DIR / (tag.replace("/", "_") + ".npz")


def save_preds(home: dict, preds: dict, calib: dict | None) -> None:
    """One compressed file per home: eval mains, GT and every method's
    prediction (seed PRED_SEED), float16 W."""
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    arr = {"ts_us": home["ts_e"],
           "mains": home["mains_e"].astype(np.float16),
           "devices": np.array(home["plan"]["devs"]),
           "thr": np.array([home["plan"]["thr"][d] for d in home["plan"]["devs"]])}
    for d in home["plan"]["devs"]:
        arr["gt_" + d] = home["gt_w"][d].astype(np.float16)
        if calib is not None and d in calib:
            arr["marks_" + d] = np.asarray(calib[d]["marks_us"], np.int64).reshape(-1, 2)
    for (m, d), w in preds.items():
        arr[f"pred_{m}_{d}"] = np.asarray(w, np.float16)
    np.savez_compressed(pred_file(home["tag"]), **arr)


def load_preds(tag: str) -> dict:
    z = np.load(pred_file(tag), allow_pickle=False)
    return {k: z[k] for k in z.files}


def load_metrics() -> pd.DataFrame:
    return pd.read_csv(METRICS_CSV)
