# fig01_resolution_ladder.py - Figure 1: one house, five instruments (sampling-rate ladder).
# Renders figures/fig01_resolution_ladder.png.

from _figcommon import FIG, D, P, busiest_day, np, plt

t = np.loadtxt(D + "channel_1.dat")[:, 0]
agg = np.loadtxt(D + "channel_1.dat")[:, 1]

d0, spread = busiest_day(t, agg)
t0 = d0 * 86400
i0, i1 = np.searchsorted(t, t0), np.searchsorted(t, t0 + 86400)
print("busiest day index", d0, "spread", round(spread), "W")


def decimate(x, y, secs):
    b = (x // secs).astype(np.int64); ub, inv = np.unique(b, return_inverse=True)
    s = np.bincount(inv, weights=y); n = np.bincount(inv)
    return ub.astype(float) * secs, s / np.maximum(n, 1)


# use an 18:00 -> 24:00 evening window: dinner, kettle, washing machine
a, b = t0 + 17 * 3600, t0 + 23 * 3600
j0, j1 = np.searchsorted(t, a), np.searchsorted(t, b)
st, sp = t[j0:j1], agg[j0:j1]
YL = float(np.percentile(sp, 99.9)) * 1.15
print("window max", sp.max(), "ylim", round(YL))

fig, ax = plt.subplots(5, 1, figsize=(11.5, 10.6))
panels = [(6, "6 s  —  UK-DALE / this slice", "#1f77b4", "every appliance transition is a clean step"),
        (60, "60 s  —  REFIT, typical smart meter, Shelly local API", "#2ca02c", "short events (kettle ~3 min) survive; brief ones blur"),
        (900, "900 s (15 min)  —  AMI / utility billing interval", "#ff7f0e", "individual events are gone; you see only the envelope"),
        (3600, "3600 s (1 h)  —  the edge of uselessness", "#d62728", "one number per hour; disaggregation is not defined here")]
for axx, (secs, lab, col, note) in zip(ax, panels):
    x, y = decimate(st, sp, secs)
    axx.step(x, y, where="post", lw=1.0, color=col)
    axx.set_xlim(st[0], st[-1]); axx.set_ylim(0, YL); axx.set_ylabel("W")
    axx.set_title(lab, loc="left", fontsize=9.5, fontweight="bold")
    axx.text(0.995, 0.90, note, transform=axx.transAxes, ha="right", va="top", fontsize=7.8,
             color=col, style="italic", bbox=dict(fc="white", ec=col, lw=0.6, alpha=0.85, pad=1.6))

# waveform panel: find the ON part of the record
w = np.loadtxt(P + "Water_kettle__1811.csv", delimiter=",")
fs = 30000.0; cyc = int(fs / 60)
env = np.abs(w[:, 0]).reshape(-1, cyc).max(axis=1)
on = int(np.argmax(env)); s0 = max(0, on - 1) * cyc
seg = w[s0:s0 + 3 * cyc]
tw = np.arange(len(seg)) / fs * 1000
ax[4].plot(tw, seg[:, 1], lw=0.9, color="#333", label="voltage (V)   [col 1]")
ax[4].plot(tw, seg[:, 0] * 40, lw=0.9, color="#d62728", label="current (A) x40   [col 0]")
ax[4].set_title("30 000 Hz  —  PLAID waveform capture (3 mains cycles, 60 Hz). What FFT, harmonics and V-I trajectories need", loc="left", fontsize=9.5, fontweight="bold")
ax[4].set_xlabel("milliseconds"); ax[4].legend(loc="lower right", fontsize=7.6, ncol=2, framealpha=0.9)
ax[4].set_ylim(-600, 600)
for a_ in ax[:-1]: a_.set_xticklabels([])
fig.suptitle("Figure 1 — One house, five instruments: what you can see depends entirely on the sampling rate", fontsize=11.8, fontweight="bold", y=0.996)
fig.text(0.5, 0.004, "Panels 1-4 are the SAME evening window of the same UK-DALE day, aggregated to a coarser interval. The last panel is a different instrument entirely.",
         ha="center", fontsize=8, color="#555")
fig.tight_layout(rect=[0, 0.014, 1, 0.985]); fig.savefig(FIG + "/fig01_resolution_ladder.png", bbox_inches="tight"); plt.close(fig)
print("fig01 done")
