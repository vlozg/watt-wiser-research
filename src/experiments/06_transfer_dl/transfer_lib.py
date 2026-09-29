"""Transfer-learning plumbing for experiment 06 - see README.md.

Standalone: experiments never import across src/experiments/ directories
(AGENTS.md). The frozen protocol - pool, homes, splits, simulated marks,
scoring - comes straight from the bench modules in .auto/, as it does for
05_method_compare. The home loader and the seq2seq net below are copies of
05's definitions, kept identical in architecture so checkpoints written by
either experiment load in the other; if one changes, load_net() says so.

Deployment parity is inherited from the frozen bench: a target home contributes
only its K=5 marks, its own pre-span history and (as a *donor*) its pre-split
labels. Holdout homes are never donors.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data" / "results" / "transfer_dl"
PRETRAIN = OUT / "pretrain"          # 06's own checkpoints (canonical)
# weights written by 05_method_compare's `train` stage: a data file, not code,
# loadable because the architecture below is the same
COMPARE_NETS = ROOT / "data" / "results" / "method_compare" / "seq2seq"

sys.path.insert(0, str(ROOT / ".auto"))
sys.path.insert(0, str(ROOT / "src"))

import bench as v1  # noqa: E402

v1.CACHE_DIR = OUT / "cache"         # span caches live with these results
import bench_v3 as v3  # noqa: E402
import bench_v4 as b4  # noqa: E402
import pool_v4 as p4  # noqa: E402

DEVICES = b4.DEV_ORDER


# ---------------------------------------------------------------- homes

def home_list() -> list[dict]:
    """Every scored home: 20 development homes, then the 7 holdout ones."""
    pool = b4.load_pool()
    return ([{"tag": t, "group": "dev"} for t in pool["pool_houses"]]
            + [{"tag": t, "group": "unseen"} for t in pool["holdout"]])


def donor_homes(exclude=(), group="dev"):
    """Development homes usable as donors; the holdout is never a donor."""
    bad = set(exclude)
    return [h for h in home_list() if h["group"] == group and h["tag"] not in bad]


def home_pairs(tag: str, group: str) -> dict:
    """{device: pair record} - frozen pool pairs, or the holdout's
    eligibility re-derived GT-only by pool_v4.eval_house (cached per home)."""
    if group == "dev":
        return b4.pairs_of(b4.load_pool(), tag)
    cache = OUT / "holdout_pairs" / (tag.replace("/", "_") + ".json")
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
    plan = b4.make_plan(tag, home_pairs(tag, group))
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
            "pre_mask": pre_mask, "pre_w": pre_w,
            "gt_mask": gt_mask, "gt_w": gt_w}


def load_homes(home_recs, log=print):
    """Load each donor home once (kept resident across devices)."""
    homes = []
    for h in home_recs:
        try:
            homes.append(load_home(h["tag"], h["group"]))
        except Exception as exc:                      # a home may be unreadable
            log(f"  skip {h['tag']}: {type(exc).__name__}: {exc}")
    return homes


# ---------------------------------------------------------------- seq2seq

# Same values as 05_method_compare's S2S. backbone_capacity_review.md explains
# why this configuration is both undertrained and short-sighted.
S2S = {"win": 512, "stride": 256, "ch": 24, "dilations": (2, 4, 8, 16, 32),
       "n_on": 1500, "n_rand": 1500, "epochs": 6, "batch": 128,
       "lr": 1e-3, "seed": 0, "scale_w": 1000.0}


def s2s_net():
    import torch
    from torch import nn

    class Block(nn.Module):
        """Dilated residual block; batch norm keeps the residual sum from
        growing layer to layer (an unnormalized stack collapsed to a
        constant output)."""

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


def s2s_input(win: np.ndarray) -> np.ndarray:
    """Per-window baseline removal: subtract the window's 10th percentile,
    so the net sees steps above the local floor, not the home's base load."""
    base = np.percentile(win, 10, axis=-1, keepdims=True)
    return np.clip((win - base) / S2S["scale_w"], 0.0, 15.0).astype(np.float32)


def s2s_training_windows(home: dict, device: str, rng) -> tuple | None:
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
    return s2s_input(x[idx]), (y[idx] / S2S["scale_w"]).astype(np.float32)


def build_windows(homes, device, seed, log=print):
    """Training windows for one device from loaded donor homes.

    Returns (X, Y, used_tags) or None when no donor carries this device.
    """
    rng = np.random.default_rng(seed)
    xs, ys, used, carry = [], [], [], 0
    for home in homes:
        if device not in home["plan"]["devs"]:
            continue
        carry += 1
        got = s2s_training_windows(home, device, rng)
        if got is None:                    # pre-span shorter than 2 windows
            continue
        xs.append(got[0])
        ys.append(got[1])
        used.append(home["tag"])
    log(f"  {device}: {carry} homes carry it, {len(used)} yielded windows, "
        f"{sum(len(x) for x in xs)} windows")
    if not xs:
        return None
    return np.concatenate(xs), np.concatenate(ys), used


def s2s_train(X: np.ndarray, Y: np.ndarray, log=print):
    import torch
    torch.manual_seed(S2S["seed"])
    net = s2s_net()
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
        log(f"      epoch {ep + 1}/{S2S['epochs']}: loss {tot / len(Xt):.5f}")
    return net


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
            xb = torch.from_numpy(s2s_input(pad[idx])[:, None, :])
            yb = net(xb)[:, 0, q:q + S].numpy()
            out[b * S:(b + len(st)) * S] = yb.reshape(-1)
    return (np.maximum(out[:n], 0.0) * S2S["scale_w"]).astype(np.float32)


def save_net(net, device, directory=PRETRAIN):
    import torch
    directory.mkdir(parents=True, exist_ok=True)
    torch.save(net.state_dict(), directory / f"{device}.pt")
    return directory / f"{device}.pt"


def load_net(device, directory=None):
    """The cross-home backbone for a device, or None if not trained yet.

    Preference order: an explicit directory, then 06's own pretrain/, then the
    nets 05_method_compare's `train` stage wrote (same architecture).
    """
    import torch
    for d in ([Path(directory)] if directory else []) + [PRETRAIN, COMPARE_NETS]:
        path = d / f"{device}.pt"
        if not path.exists():
            continue
        net = s2s_net()
        try:
            net.load_state_dict(torch.load(path, map_location="cpu"))
        except RuntimeError as exc:
            raise RuntimeError(
                f"{path} does not match the current s2s_net() architecture - "
                f"the checkpoint predates a change to the net definition, so "
                f"retrain before using it ({str(exc).splitlines()[0]})") from exc
        net.eval()
        return net
    return None
