# fig05_vi_gallery.py - Figure 5: V-I trajectory gallery, one panel per PLAID capture.
# Renders figures/fig05_vi_gallery.png.

from _figcommon import FIG, gallery_records, plt

recs = gallery_records()

# ---------- gallery ----------
order = sorted(recs, key=lambda r: -r["p"])
nr, nc = 4, 4
fig, axs = plt.subplots(nr, nc, figsize=(13, 13))
for ax, r in zip(axs.ravel(), order):
    for vs, is_ in r["cy"]: ax.plot(vs, is_, lw=0.7, alpha=0.55, color="#1f77b4")
    ax.set_title("%s\n%.0f W" % (r["name"], r["p"]), fontsize=9, fontweight="bold")
    ax.axhline(0, color="#bbb", lw=0.6); ax.axvline(0, color="#bbb", lw=0.6)
    ax.set_xlabel("voltage (V)", fontsize=7.5); ax.set_ylabel("current (A)", fontsize=7.5); ax.tick_params(labelsize=7)
for ax in axs.ravel()[len(order):]: ax.axis("off")
fig.suptitle("Figure 5 — V-I trajectories: the fingerprint of a load (PLAID, real measurements, 30 kHz)", fontsize=12.5, fontweight="bold", y=0.997)
fig.text(0.5, 0.004, "Each loop = one 60 Hz mains cycle: voltage on x, current on y. Shape is set by the PHYSICS of the load, not its size. "
  "Straight line = resistive. Open ellipse = stored energy (motor). Burst near the peak = switch-mode supply. Lopsided = rectified.", ha="center", fontsize=8.2, color="#555")
fig.tight_layout(rect=[0, 0.012, 1, 0.985]); fig.savefig(FIG + "/fig05_vi_gallery.png", bbox_inches="tight"); plt.close(fig)
print("fig05 done")
