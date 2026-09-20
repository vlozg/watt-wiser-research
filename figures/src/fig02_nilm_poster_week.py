# fig02_nilm_poster_week.py - Figure 2: the NILM poster (one aggregate, five ground truths).
# Renders figures/fig02_nilm_poster_week.png.

from _figcommon import COL, FIG, NAME, busiest_week, np, plt, ukdale

t, ch = ukdale()
d0, t0 = busiest_week(t, ch)
i0, i1 = np.searchsorted(t, t0), np.searchsorted(t, t0 + 7 * 86400)

fig, ax = plt.subplots(6, 1, figsize=(12.5, 9.4), sharex=True)
ax[0].plot(t[i0:i1], ch[1][i0:i1], lw=0.55, color="#111")
ax[0].set_ylabel("W"); ax[0].set_title("AGGREGATE  (what the meter sees)  —  channel_1", loc="left", fontsize=9.5, fontweight="bold")
ax[0].set_ylim(0, np.percentile(ch[1][i0:i1], 99.95) * 1.12)
ax[0].axhspan(0, 30, color="red", alpha=0.13, zorder=0)
ax[0].text(0.002, 0.06, "blind below 30 VA (Shelly floor)", transform=ax[0].transAxes, fontsize=7.5, color="#a00")
for k, c in enumerate([2, 3, 4, 5, 6]):
    a = ax[k + 1]
    a.fill_between(t[i0:i1], 0, ch[c][i0:i1], color=COL[c], lw=0, alpha=0.85)
    a.set_ylabel("W"); a.set_title("GROUND TRUTH  —  " + NAME[c], loc="left", fontsize=8.6, fontweight="bold", color=COL[c])
    a.set_ylim(0, max(60, np.percentile(ch[c][i0:i1], 99.5) * 1.25))
ax[-1].set_xlabel("time")
fig.suptitle("Figure 2 — The NILM poster: one aggregate signal, five appliances hiding inside it", fontsize=12, fontweight="bold", y=0.997)
fig.text(0.5, 0.004, "UK-DALE, 7 days at 6 s. The top trace is what a whole-home meter records. The five below are the answer, obtained with separate clamps on each appliance.",
         ha="center", fontsize=7.8, color="#555")
fig.tight_layout(rect=[0, 0.012, 1, 0.985]); fig.savefig(FIG + "/fig02_nilm_poster_week.png", bbox_inches="tight"); plt.close(fig)
print("fig02 done")
