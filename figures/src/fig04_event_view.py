# fig04_event_view.py - Figure 4: reading the data the way an algorithm does (steps, not shapes).
# Renders figures/fig04_event_view.png.

from _figcommon import COL, FIG, NAME, TH, np, plt, ukdale

t, ch = ukdale()

# ---------- the event / dP view ----------
plt.rcParams.update({"font.size": 11})   # fig 4 only: larger text
fig, ax = plt.subplots(2, 2, figsize=(13, 8.2))
# (a) zoom on a kettle event
p = ch[1]; d = np.abs(np.diff(p)); c = 4
st = (ch[c] > TH); idx = np.flatnonzero(np.diff(st.astype(np.int8)) == 1)
k = idx[len(idx) // 2]
w0, w1 = max(0, k - 150), min(len(p), k + 250)
ax[0, 0].plot(t[w0:w1] - t[k], p[w0:w1], color="#111", lw=1.1, label="aggregate")
ax[0, 0].plot(t[w0:w1] - t[k], ch[c][w0:w1], color=COL[c], lw=1.1, label="kettle (truth)")
ax[0, 0].axvline(0, color="#0a0", ls="--", lw=1)
ym = p[w0:w1].max()
ax[0, 0].annotate("the step\nyou must detect", xy=(0, ym * 0.93), xytext=(0.03, 0.84),
                  textcoords="axes fraction", arrowprops=dict(arrowstyle="->", color="#0a0"), fontsize=10.5, color="#080")
ax[0, 0].set_title("(a) what an 'event' looks like", loc="left", fontsize=12, fontweight="bold")
ax[0, 0].set_xlabel("seconds around the event"); ax[0, 0].set_ylabel("W"); ax[0, 0].legend(fontsize=10.5, loc="upper right")
# (b) histogram of aggregate |dP|
dd = np.abs(np.diff(p))
ax[0, 1].hist(dd[dd < 600], bins=120, color="#555")
ax[0, 1].axvline(30, color="red", ls="--", lw=1.2, label="30 VA Shelly floor")
ax[0, 1].set_yscale("log"); ax[0, 1].legend(fontsize=10.5, loc="upper right")
ax[0, 1].set_title("(b) every step the meter takes, 70.7 days", loc="left", fontsize=12, fontweight="bold")
ax[0, 1].set_xlabel("|change in aggregate power| (W)"); ax[0, 1].set_ylabel("count (log)")
# (c) per-appliance step distributions - the confusion
for c in [2, 3, 4, 5, 6]:
    st = (ch[c] > TH); ix = np.flatnonzero(np.diff(st.astype(np.int8)) != 0)
    s = np.abs(np.diff(ch[c])[ix])
    if len(s) > 12: ax[1, 0].hist(s, bins=np.logspace(0.5, 4, 45), histtype="step", lw=1.5, color=COL[c], label=NAME[c])
ax[1, 0].set_xscale("log")
ax[1, 0].axvspan(0, 30, color="red", alpha=0.10)
ax[1, 0].set_title("(c) step sizes overlap: this is the whole problem", loc="left", fontsize=9.5, fontweight="bold")
ax[1, 0].set_xlabel("size of the step this appliance makes (W)"); ax[1, 0].set_ylabel("count"); ax[1, 0].legend(fontsize=10.5)
# (d) simultaneity
nc = sum((ch[c] > TH).astype(int) for c in [2, 3, 4, 5, 6])
import collections

cnt = collections.Counter(nc.tolist()); tot = len(nc)
ks = sorted(cnt); vals = [100 * cnt[k] / tot for k in ks]
bars = ax[1, 1].bar([str(k) for k in ks], vals, color=["#4c72b0", "#55a868", "#c44e52", "#8172b3", "#937860"][:len(ks)])
for kk, vv in zip(ks, vals): ax[1, 1].text(str(kk), vv + 0.8, f"{vv:.1f}%", ha="center", fontsize=10.5)
ax[1, 1].set_title("(d) how often appliances overlap", loc="left", fontsize=12, fontweight="bold")
ax[1, 1].set_xlabel("number of monitored appliances ON at once"); ax[1, 1].set_ylabel("% of time")
ax[1, 1].text(0.98, 0.86, "2 or more ON: " + f"{sum(v for k, v in cnt.items() if k >= 2) * 100 / tot:.1f}" + "% of the time",
              transform=ax[1, 1].transAxes, ha="right", fontsize=10.5, color="#c44e52", fontweight="bold")
fig.suptitle("Figure 4 — Reading the data the way an algorithm does: steps, not shapes", fontsize=14, fontweight="bold", y=0.995)
fig.tight_layout(rect=[0, 0, 1, 0.975]); fig.savefig(FIG + "/fig04_event_view.png", bbox_inches="tight"); plt.close(fig)
print("fig04 done")
