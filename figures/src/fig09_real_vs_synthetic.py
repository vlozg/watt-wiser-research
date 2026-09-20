# fig09_real_vs_synthetic.py - Figure 9: real UK-DALE day vs the synthetic WattWiser generator.
# Renders figures/fig09_real_vs_synthetic.png.

import os

import pandas as pd
from _figcommon import FIG, ROOT, D, busiest_day, np, plt

t = np.loadtxt(D + "channel_1.dat")[:, 0]; agg = np.loadtxt(D + "channel_1.dat")[:, 1]
d0, _ = busiest_day(t, agg)
j0, j1 = np.searchsorted(t, d0 * 86400), np.searchsorted(t, d0 * 86400 + 86400)
rt = t[j0:j1]; rp = agg[j0:j1]; hr = (rt - rt[0]) / 3600.0

S = pd.read_csv(os.path.join(ROOT, "repo", "WattWiser", "data", "raw", "synthetic_shelly_data.csv"),
              usecols=["timestamp", "active_power_W", "kettle_power_W", "fridge_power_W", "microwave_power_W", "washing_machine_power_W"])
S["timestamp"] = pd.to_datetime(S["timestamp"])
d1 = S["timestamp"].dt.date.iloc[0]
S = S[S["timestamp"].dt.date == d1].reset_index(drop=True)
hs = (S["timestamp"] - S["timestamp"].iloc[0]).dt.total_seconds() / 3600.0
print("synthetic day", d1, "rows", len(S))

fig, ax = plt.subplots(2, 2, figsize=(13.5, 7.4), gridspec_kw={"height_ratios": [1.25, 1]})
ax[0, 0].plot(hr, rp, lw=0.6, color="#111"); ax[0, 0].set_ylim(0, 3400)
ax[0, 0].set_title("REAL  —  UK-DALE household, 24 h at 6 s", loc="left", fontsize=10, fontweight="bold")
ax[0, 0].set_ylabel("W"); ax[0, 0].set_xlabel("hours")
ax[0, 1].plot(hs, S["active_power_W"], lw=0.8, color="#111"); ax[0, 1].set_ylim(0, 3400)
ax[0, 1].set_title("SYNTHETIC  —  WattWiser dataset, 24 h at 5 s", loc="left", fontsize=10, fontweight="bold")
ax[0, 1].set_ylabel("W"); ax[0, 1].set_xlabel("hours")
for _, (col, nm) in enumerate([("kettle_power_W", "kettle"), ("fridge_power_W", "fridge"),
                             ("microwave_power_W", "microwave"), ("washing_machine_power_W", "washing")]):
    ax[1, 1].plot(hs, S[col], lw=0.7, label=nm)
ax[1, 1].set_title("SYNTHETIC ground truth: perfectly rectangular, exactly zero when off", loc="left", fontsize=9.5, fontweight="bold")
ax[1, 1].set_ylabel("W"); ax[1, 1].set_xlabel("hours"); ax[1, 1].legend(fontsize=7.5, ncol=4)
# real appliance truth for the same day
for c, col, nm in [(2, "#1f77b4", "fridge"), (3, "#ff7f0e", "dish_washer"), (4, "#d62728", "kettle"), (5, "#9467bd", "washing_machine"), (6, "#7f7f7f", "monitor")]:
    x = np.loadtxt(D + f"channel_{c}.dat")
    m = (x[:, 0] >= d0 * 86400) & (x[:, 0] < d0 * 86400 + 86400)
    if m.sum() < 100: continue
    ax[1, 0].plot((x[m, 0] - d0 * 86400) / 3600.0, x[m, 1], lw=0.7, color=col, label=nm)
ax[1, 0].set_title("REAL ground truth: ramps, cycling, standby, noise", loc="left", fontsize=9.5, fontweight="bold")
ax[1, 0].set_ylabel("W"); ax[1, 0].set_xlabel("hours"); ax[1, 0].legend(fontsize=7.5, ncol=5)
fig.suptitle("Figure 9 — What the synthetic dataset is missing: real loads are not rectangles", fontsize=12.3, fontweight="bold", y=0.995)
fig.text(0.5, 0.004, "Same time span, same axes. The synthetic generator draws every appliance as an ideal switch. Real appliances ramp, cycle, drift, and never return exactly to zero.",
         ha="center", fontsize=8, color="#555")
fig.tight_layout(rect=[0, 0.014, 1, 0.972]); fig.savefig(FIG + "/fig09_real_vs_synthetic.png", bbox_inches="tight"); plt.close(fig)
print("fig09 done")
