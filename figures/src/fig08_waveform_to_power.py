# fig08_waveform_to_power.py - Figure 8: the bridge from raw waveform to metered watts
# (PLAID vacuum off-on capture: 12 idle cycles, motor inrush decaying to the running plateau).
# Renders figures/fig08_waveform_to_power.png.

from _figcommon import CYC, FIG, P, np, plt

f = P + "Vacuum__1757.csv"
w = np.loadtxt(f, delimiter=","); i, v = w[:, 0], w[:, 1]
n = len(i) // CYC
I = i[:n * CYC].reshape(n, CYC); V = v[:n * CYC].reshape(n, CYC)
clean = np.abs(V).max(axis=1) < 400
pc = np.array([np.mean(V[k] * I[k]) for k in range(n)])
secs = np.arange(n) / 60.0
k0 = int(np.flatnonzero(clean)[np.argmax(np.abs(pc[clean]))])
k3 = max(0, min(n - 3, k0 - 1))
fig, ax = plt.subplots(4, 1, figsize=(12.5, 10.0))
t3 = np.arange(3 * CYC) / 30000 * 1000
ax[0].plot(t3, V[k3:k3 + 3].ravel(), lw=1.0, color="#333", label="voltage (V)")
a2 = ax[0].twinx(); a2.plot(t3, I[k3:k3 + 3].ravel(), lw=1.0, color="#d62728", label="current (A)")
a2.set_ylabel("current (A)", color="#d62728"); a2.grid(False); a2.spines["top"].set_visible(False)
ax[0].set_title("(a) raw hardware capture — 30 000 samples per second, 3 cycles", loc="left", fontsize=9.5, fontweight="bold")
ax[0].set_xlabel("ms"); ax[0].set_ylabel("voltage (V)")
h1, l1 = ax[0].get_legend_handles_labels(); h2, l2 = a2.get_legend_handles_labels()
ax[0].legend(h1 + h2, l1 + l2, fontsize=8, ncol=2, loc="upper right")
ax[1].plot(np.arange(CYC) / 30000 * 1000, V[k0], lw=1.1, color="#333", label="voltage (V)")
b2 = ax[1].twinx(); b2.plot(np.arange(CYC) / 30000 * 1000, I[k0], lw=1.1, color="#d62728", label="current (A)")
b2.set_ylabel("current (A)", color="#d62728"); b2.grid(False); b2.spines["top"].set_visible(False)
ax[1].axvline(0, color="#0a0", ls=":", lw=1)
ax[1].set_title("(b) one mains cycle. Current peaks 0.6 ms AFTER voltage = 14 deg lag => a motor. This is what a V-I trajectory encodes", loc="left", fontsize=9.5, fontweight="bold")
ax[1].set_xlabel("ms"); ax[1].set_ylabel("voltage (V)")
h1, l1 = ax[1].get_legend_handles_labels(); h2, l2 = b2.get_legend_handles_labels()
ax[1].legend(h1 + h2, l1 + l2, fontsize=8, ncol=2, loc="upper right")
ax[2].plot(secs, pc / 1000.0, lw=1.1, color="#2ca02c")
ax[2].set_title("(c) one multiply + one average per cycle = WATTS. 30 000 Hz collapses to 60 Hz here, irreversibly", loc="left", fontsize=9.5, fontweight="bold")
ax[2].set_xlabel("seconds"); ax[2].set_ylabel("kW")
ax[3].plot(secs, pc / 1000.0, lw=0.9, color="#bbb", label="60 Hz — what panel (c) has")
for dt_, c_, lab in [(1, "#1f77b4", "1 s"), (5, "#ff7f0e", "5 s  (the synthetic dataset)")]:
    nb = max(1, int(60 * dt_)); x = np.arange(n) // nb * nb / 60.0
    u, idx = np.unique(x, return_index=True)
    y = np.array([pc[j:j + nb].mean() for j in idx])
    ax[3].plot(u, y / 1000.0, marker="o", ms=4, lw=1.1, color=c_, label=lab)
ax[3].set_title("(d) the same record as a meter would report it — the entire input to NILM", loc="left", fontsize=9.5, fontweight="bold")
ax[3].set_xlabel("seconds"); ax[3].set_ylabel("kW"); ax[3].legend(fontsize=8, ncol=4)
ax[3].annotate("60 s cannot even be drawn:\nthis capture is %.1f s long" % (n / 60.0), xy=(0.62, 0.58), xycoords="axes fraction",
   ha="center", fontsize=9, color="#c44e52", fontweight="bold")
fig.suptitle("Figure 8 — The bridge: how a waveform becomes a number, and what is destroyed at each step  [PLAID vacuum]", fontsize=12, fontweight="bold", y=0.996)
fig.text(0.5, 0.004, "Panels (a)-(c) exist only on hardware that exports the raw waveform; a Shelly EM starts at panel (d). Waveform archives are seconds long, smart-meter archives are years long - no public dataset gives you both.", ha="center", fontsize=7.8, color="#555")
fig.tight_layout(rect=[0, 0.012, 1, 0.98]); fig.savefig(FIG + "/fig08_waveform_to_power.png", bbox_inches="tight"); plt.close(fig)
print("fig08 done")
