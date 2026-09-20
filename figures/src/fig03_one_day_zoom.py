# fig03_one_day_zoom.py - Figure 3: one day unrolled, aggregate + ground truth with ON shading.
# Renders figures/fig03_one_day_zoom.png.

from _figcommon import COL, FIG, NAME, TH, busiest_week, np, plt, ukdale

t, ch = ukdale()
d0, t0 = busiest_week(t, ch)

# pick the busiest day of the week: most dishwasher+washing-machine ON-time,
# kettle ON-time as tie-break, so no panel is an empty flatline
bestd = None
for dd_ in range(7):
    a0, a1 = np.searchsorted(t, t0 + dd_ * 86400), np.searchsorted(t, t0 + (dd_ + 1) * 86400)
    if a1 - a0 < 12000: continue
    act = sum(int((ch[c][a0:a1] > TH).sum()) for c in [3, 5])
    kev = int((np.diff((ch[4][a0:a1] > TH).astype(np.int8)) == 1).sum())
    cand = (act, kev)
    if bestd is None or cand > bestd[1]: bestd = (dd_, cand)
print("fig03 day offset", bestd[0], "(activity,kettle-ON-samples)", bestd[1])
t0d = t0 + bestd[0] * 86400
j0, j1 = np.searchsorted(t, t0d), np.searchsorted(t, t0d + 86400)

fig, ax = plt.subplots(6, 1, figsize=(12.5, 9.4), sharex=True)
ax[0].plot(t[j0:j1], ch[1][j0:j1], lw=0.7, color="#111")
ax[0].set_title("AGGREGATE  —  can you tell what is on?", loc="left", fontsize=9.5, fontweight="bold")
ax[0].set_ylabel("W"); ax[0].set_ylim(0, np.percentile(ch[1][j0:j1], 99.95) * 1.15)
for k, c in enumerate([2, 3, 4, 5, 6]):
    a = ax[k + 1]; p = ch[c][j0:j1]; st = (p > TH)
    a.fill_between(t[j0:j1], 0, p, color=COL[c], lw=0, alpha=0.8)
    # shade ON intervals
    d = np.diff(st.astype(np.int8)); on = np.flatnonzero(d == 1) + 1; off = np.flatnonzero(d == -1) + 1
    if st[0]: on = np.r_[0, on]
    if st[-1] and len(on) > len(off): off = np.r_[off, len(st)]
    for s_, e_ in zip(on, off): a.axvspan(t[j0:j1][s_], t[j0:j1][min(e_, len(st) - 1)], color=COL[c], alpha=0.12, lw=0)
    a.set_ylabel("W"); a.set_title("GROUND TRUTH  —  " + NAME[c] + "   (ON " + f"{100 * st.mean():.1f}" + "% of the day, " + f"{len(on)}" + " events)", loc="left", fontsize=8.6, fontweight="bold", color=COL[c])
    a.set_ylim(0, max(60, np.percentile(p, 99.5) * 1.25))
ax[-1].set_xlabel("time")
fig.suptitle("Figure 3 — One day, unrolled: the aggregate is the sum, and the sum is what hides the parts", fontsize=12, fontweight="bold", y=0.997)
fig.text(0.5, 0.004, "UK-DALE, 24 h at 6 s. Shaded bands mark ON intervals. Notice the washing machine: long multi-stage cycles, exactly the kind of load a single step size cannot describe.",
         ha="center", fontsize=7.8, color="#555")
fig.tight_layout(rect=[0, 0.012, 1, 0.985]); fig.savefig(FIG + "/fig03_one_day_zoom.png", bbox_inches="tight"); plt.close(fig)
print("fig03 done")
