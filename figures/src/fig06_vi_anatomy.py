# fig06_vi_anatomy.py - Figure 6: reading a V-I trajectory, six archetypes annotated.
# Renders figures/fig06_vi_anatomy.png.

from _figcommon import FIG, gallery_records, plt

recs = gallery_records()

# ---------- anatomy ----------
pick = ["Water kettle", "Compact Fluorescent Lamp", "Laptop", "Microwave", "Vacuum", "Fridge"]
notes = {
 "Water kettle": "RESISTIVE\nI follows V exactly.\nA near-straight line\nthrough the origin.",
 "Compact Fluorescent Lamp": "NONLINEAR ELECTRONIC\nCurrent arrives in narrow\nspikes at the voltage peaks,\nbriefly reversing sign.\nNothing like the V shape.",
 "Laptop": "SWITCH-MODE SUPPLY\nCurrent flows only in short\nbursts near the peaks:\na rectifier plus a\nreservoir capacitor.",
 "Microwave": "TRANSFORMER\nStrongly asymmetric - the\nnegative half-cycle is\nbarely used. A lopsided\nloop, plus a switching step.",
 "Vacuum": "MOTOR (inductive)\nCurrent LAGS voltage, so the\nloop opens into an ellipse.\nEnclosed area = reactive\npower, not real power.",
 "Fridge": "MOTOR, much smaller\nSame ellipse as the vacuum\nbut a fraction of the current.\nA 60-100 W load is a\nthin sliver on this scale."}
bys = {r["name"]: r for r in recs}
fig, axs = plt.subplots(2, 3, figsize=(13.5, 7.8))
for ax, nm in zip(axs.ravel(), pick):
    r = bys.get(nm)
    if r is None: ax.text(0.5, 0.5, nm + "\n(not usable)", ha="center", transform=ax.transAxes); ax.axis("off"); continue
    for vs, is_ in r["cy"]: ax.plot(vs, is_, lw=0.9, alpha=0.5, color="#1f77b4")
    ax.set_title("%s   (%.0f W)" % (nm, r["p"]), fontsize=10, fontweight="bold")
    ax.text(0.02, 0.97, notes[nm], transform=ax.transAxes, va="top", ha="left", fontsize=7.4,
            bbox=dict(fc="white", ec="#999", alpha=0.88, pad=2.4))
    ax.axhline(0, color="#bbb", lw=0.6); ax.axvline(0, color="#bbb", lw=0.6)
    ax.set_xlabel("voltage (V)", fontsize=8); ax.set_ylabel("current (A)", fontsize=8)
fig.suptitle("Figure 6 — Reading a trajectory: six archetypes and what each shape means", fontsize=12.5, fontweight="bold", y=0.995)
fig.tight_layout(rect=[0, 0, 1, 0.965]); fig.savefig(FIG + "/fig06_vi_anatomy.png", bbox_inches="tight"); plt.close(fig)
print("fig06 done")
