# fig07_harmonics.py - Figure 7: harmonic spectra of the PLAID loads (4x4 grid, sorted by THD).
# Renders figures/fig07_harmonics.png.

import glob
import json
import os

from _figcommon import CYC, FIG, ROOT, P, np, plt

META = json.load(open(os.path.join(ROOT, "research-logs", "plaid", "metadata_submetered.json")))


def stable_cycles(path, ncyc=40):
    pid = os.path.basename(path).split("__")[1][:-4]
    status = META.get(pid, {}).get("appliance", {}).get("status", "")
    w = np.loadtxt(path, delimiter=",")
    if w.ndim == 1: w = w.reshape(-1, 2)
    i, v = w[:, 0], w[:, 1]
    n = len(i) // CYC
    if n < 10: return None, None
    I = i[:n * CYC].reshape(n, CYC); V = v[:n * CYC].reshape(n, CYC)
    env = np.abs(I).max(axis=1); clean = np.abs(V).max(axis=1) < 400
    if "off-on" in status: lo, hi = int(n * 0.5), n
    elif "on-off" in status: lo, hi = 0, int(n * 0.5)
    else: lo, hi = 0, n
    e = env[lo:hi].copy(); g = clean[lo:hi]
    if e.size == 0: return None, None
    sel = lo + np.flatnonzero((e > 0.5 * e.max()) & g)
    if len(sel) < 6: sel = lo + np.flatnonzero(g)
    if len(sel) < 6: return None, None
    if len(sel) > ncyc: sel = sel[np.linspace(0, len(sel) - 1, ncyc).astype(int)]
    return V[sel], I[sel]


def sync_avg(V, I):
    """align each cycle on the rising voltage zero-crossing, then average"""
    A = []; B = []
    for vv, ii in zip(V, I):
        z = np.flatnonzero((vv[:-1] < 0) & (vv[1:] >= 0))
        if len(z) == 0: continue
        s = z[0]
        A.append(np.roll(vv, -s)); B.append(np.roll(ii, -s))
    if len(A) < 4: return None, None, 0
    return np.mean(A, axis=0), np.mean(B, axis=0), len(A)


recs = []
for f in sorted(glob.glob(P + "*.csv")):
    nm = os.path.basename(f).split("__")[0].replace("_", " ")
    V, I = stable_cycles(f)
    if V is None: continue
    av, ai, n = sync_avg(V, I)
    if av is None: continue
    p = float(np.mean(av * ai))
    if p < 0.5: continue
    recs.append({"name": nm, "v": av, "i": ai, "p": p, "n": n, "V": V, "I": I})
print("records for spectra:", len(recs))


def spectrum(ai, nh=25):
    seg = ai - ai.mean()
    F = np.abs(np.fft.rfft(seg))
    if F[1] <= 0: return None, None
    db = 20 * np.log10(np.maximum(F[:nh + 1], 1e-12) / F[1])
    thd = np.sqrt(np.sum(F[2:nh + 1] ** 2)) / F[1] * 100
    return db, thd


for r in recs:
    r["db"], r["thd"] = spectrum(r["i"])
recs = [r for r in recs if r["db"] is not None]
recs.sort(key=lambda r: -r["thd"])
print("sorted by THD:", ", ".join("%s %.0f%%" % (r["name"], r["thd"]) for r in recs))

fig, axs = plt.subplots(4, 4, figsize=(13.5, 11.2))   # 4x4: show ALL usable captures, kettle included
for ax, r in zip(axs.ravel(), recs):
    k = np.arange(len(r["db"]))
    ax.bar(k, r["db"], color="#4c72b0", width=0.78)
    ax.bar([2, 4, 6, 8, 10, 12], [r["db"][j] if j < len(r["db"]) else -90 for j in [2, 4, 6, 8, 10, 12]],
           color="#c44e52", width=0.78)
    ax.set_ylim(-80, 4); ax.set_xlim(-0.8, 25.8); ax.tick_params(labelsize=7)
    ax.set_title("%s  (%.0f W)" % (r["name"], r["p"]), fontsize=9.5, fontweight="bold")
    ax.set_ylabel("dB rel. fundamental", fontsize=7.5)
    ax.text(0.97, 0.90, "THD %.0f%%" % (r["thd"]), transform=ax.transAxes, ha="right", fontsize=8.5,
            fontweight="bold", color="#c44e52", bbox=dict(fc="white", ec="#c44e52", alpha=0.9, pad=1.6))
for ax in axs.ravel()[len(recs):]: ax.axis("off")
for ax in axs.ravel()[-4:]:
    if ax.has_data(): ax.set_xlabel("harmonic order (x 60 Hz)", fontsize=7.5)
fig.suptitle("Figure 7 — Harmonic spectra: the same loads in the frequency domain (FFT of a synchronously-averaged mains cycle)", fontsize=12.3, fontweight="bold", y=0.995)
fig.text(0.5, 0.006, "Red bars mark EVEN harmonics, which should be absent from any symmetric load. Panels sorted by total harmonic distortion (THD). A resistive element dumps everything into the fundamental; "
  "electronics scatter it up the spectrum. This is the visual language of speech spectrograms, applied to mains current.", ha="center", fontsize=7.9, color="#555")
fig.tight_layout(rect=[0, 0.018, 1, 0.962]); fig.savefig(FIG + "/fig07_harmonics.png", bbox_inches="tight"); plt.close(fig)
print("fig07 done")
