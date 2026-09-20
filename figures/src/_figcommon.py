# Shared boot for the per-figure generator scripts in this directory.
# One script per figure: each figNN_*.py renders exactly its own
# figures/figNN_*.png and nothing else - there are no superseding layers, so
# rerunning any or all scripts reproduces the shipped PNGs exactly.
# Data pipelines shared by more than one figure live here; single-figure
# data code stays inside its own script.

import os

os.environ.setdefault("MPLCONFIGDIR", "/tmp/mplcfg"); os.makedirs("/tmp/mplcfg", exist_ok=True)
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root
D = os.path.join(ROOT, "research-logs", "sakunrasilka_nilm-test2") + os.sep  # UK-DALE slice
P = os.path.join(ROOT, "research-logs", "vi", "plaid_samples") + os.sep  # PLAID 30 kHz captures
FIG = os.path.join(ROOT, "figures"); os.makedirs(FIG, exist_ok=True)
plt.rcParams.update({"figure.dpi": 118, "savefig.dpi": 118, "font.size": 9, "axes.grid": True,
    "grid.alpha": 0.25, "axes.axisbelow": True, "axes.spines.top": False, "axes.spines.right": False})
CYC = 500  # samples per 60 Hz mains cycle at 30 kHz

NAME = {2: "fridge", 3: "dish_washer", 4: "kettle", 5: "washing_machine", 6: "monitor"}
COL = {2: "#1f77b4", 3: "#ff7f0e", 4: "#d62728", 5: "#9467bd", 6: "#7f7f7f"}
TH = 15.0  # W - appliance ON threshold on the 6 s UK-DALE channels


def ukdale():
    """channel_1..6 truncated to the common window -> (t, {channel: W array})"""
    raw = {c: np.loadtxt(D + f"channel_{c}.dat") for c in range(1, 7)}
    tend = min(raw[c][-1, 0] for c in raw)
    n = min((raw[c][:, 0] <= tend).sum() for c in raw)
    t = raw[1][:n, 0]
    ch = {c: raw[c][:n, 1] for c in range(1, 7)}
    assert all(len(ch[c]) == n for c in ch), "still ragged"
    print("truncated to common window:", n, "samples,", round((t[-1] - t[0]) / 86400, 2), "days")
    return t, ch


def busiest_week(t, ch):
    """busiest 7-day span (aggregate spread) -> (day index, start seconds)"""
    day = (t // 86400).astype(np.int64)
    best = None
    for d in np.unique(day)[:-7]:
        m = (day >= d) & (day < d + 7)
        if m.sum() < 90000: continue
        r = np.percentile(ch[1][m], 99.7) - np.percentile(ch[1][m], 5)
        if best is None or r > best[1]: best = (d, r)
    print("week", best[0], "-", best[0] + 7)
    return best[0], best[0] * 86400


def busiest_day(t, agg):
    """busiest single day (aggregate spread, needs >=14000 samples) -> (day index, spread)"""
    day = (t // 86400).astype(np.int64)
    best = None
    for d in np.unique(day)[:-1]:
        m = day == d
        if m.sum() < 14000: continue
        r = np.percentile(agg[m], 99.5) - np.percentile(agg[m], 5)
        if best is None or r > best[1]: best = (d, r)
    return best[0], best[1]


def gallery_records():
    """PLAID captures -> usable V-I cycle records for the fig 5/6 gallery (raw 500-sample cycles)."""
    import glob
    import json
    META = json.load(open(os.path.join(ROOT, "research-logs", "plaid", "metadata_submetered.json")))

    def cycles_for(path, ncyc=12):
        pid = os.path.basename(path).split("__")[1][:-4]
        status = META.get(pid, {}).get("appliance", {}).get("status", "")
        w = np.loadtxt(path, delimiter=",")
        if w.ndim == 1: w = w.reshape(-1, 2)
        i, v = w[:, 0], w[:, 1]
        n = len(i) // CYC
        if n < 8: return []
        env = np.abs(i[:n * CYC]).reshape(n, CYC).max(axis=1)
        gv = np.abs(v[:n * CYC]).reshape(n, CYC).max(axis=1) < 400
        # window the record according to the captured transition
        if "off-on" in status:  lo, hi = int(n * 0.35), n
        elif "on-off" in status: lo, hi = 0, int(n * 0.65)
        else:                    lo, hi = 0, n
        e = env[lo:hi].copy(); g = gv[lo:hi]
        if e.size == 0: return []
        keep = (e > 0.30 * e.max()) & g
        idx = np.flatnonzero(keep)
        if len(idx) < 3:
            idx = np.flatnonzero(g)
            if len(idx) == 0: return []
        if len(idx) > ncyc: idx = idx[np.linspace(0, len(idx) - 1, ncyc).astype(int)]
        return [(v[(lo + c) * CYC:(lo + c + 1) * CYC], i[(lo + c) * CYC:(lo + c + 1) * CYC]) for c in idx]

    recs = []
    for f in sorted(glob.glob(P + "*.csv")):
        nm = os.path.basename(f).split("__")[0].replace("_", " ")
        cy = cycles_for(f)
        if len(cy) < 3: continue
        recs.append({"name": nm, "cy": cy, "p": float(np.mean([np.mean(a * b) for a, b in cy]))})
    recs = [r for r in recs if r["p"] > 0.5]
    print("usable:", len(recs), "->", ", ".join("%s(%.0fW)" % (r["name"], r["p"]) for r in sorted(recs, key=lambda x: -x["p"])))
    return recs
