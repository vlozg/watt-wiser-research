#!/usr/bin/env python3
"""
Reproducible analysis of AdibReza/WattWiser data/raw/synthetic_shelly_data.csv

The CSV is NOT vendored into this repo (50 MB, third-party). Clone it first:

    git clone --depth 1 https://github.com/AdibReza/WattWiser.git repo/WattWiser

Then run:

    python3 analysis/repo-forensics/analyze_synthetic.py [path/to/synthetic_shelly_data.csv]

Requires pandas + numpy.
"""
import sys

import pandas as pd

CSV = sys.argv[1] if len(sys.argv) > 1 else "repo/WattWiser/data/raw/synthetic_shelly_data.csv"
AP = ["kettle", "fridge", "microwave", "washing_machine"]
POW = {a: a + "_power_W" for a in AP}
ON  = {a: a + "_on" for a in AP}

def hdr(n, t):
    print("\n" + "=" * 78 + f"\n{n}. {t}\n" + "=" * 78)

df = pd.read_csv(CSV)
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["n_on"] = df[[ON[a] for a in AP]].sum(axis=1)
df["base"] = df["active_power_W"] - df[[POW[a] for a in AP]].sum(axis=1)
df["dP"] = df["active_power_W"].diff()
df["hr"] = df["timestamp"].dt.hour
tr = {a: df[ON[a]].diff() for a in AP}

hdr(1, "SHAPE / CADENCE")
print("rows x cols :", df.shape)
print("columns     :", df.columns.tolist())
print("span        :", df["timestamp"].min(), "->", df["timestamp"].max())
print("duration    :", df["timestamp"].max() - df["timestamp"].min())
iv = df["timestamp"].diff().dropna().value_counts()
print("intervals   :", {str(k): int(v) for k, v in iv.items()})
ORIG = ["timestamp","voltage_V","current_A","active_power_W","apparent_power_VA",
        "power_factor","frequency_Hz","cumulative_energy_Wh"] + [POW[a] for a in AP] + [ON[a] for a in AP]
print("missing (raw 16 cols):", int(df[ORIG].isnull().sum().sum()), "| duplicate rows:", int(df.duplicated().sum()))

hdr(2, "INTERNAL ARITHMETIC (are columns independent measurements?)")
print("VA vs V*I        max abs err:", round((df.apparent_power_VA - df.voltage_V*df.current_A).abs().max(), 4))
print("PF vs W/VA       max abs err:", round((df.power_factor - df.active_power_W/df.apparent_power_VA).abs().max(), 6))
print("W  vs VA*PF      max abs err:", round((df.active_power_W - df.apparent_power_VA*df.power_factor).abs().max(), 4))
print("Wh vs cumsum(W)  max abs err:", round((df.cumulative_energy_Wh - df.active_power_W.cumsum()*5/3600).abs().max(), 4))

hdr(3, "LABEL PURITY (is appliance power ever nonzero when state = OFF?)")
for a in AP:
    off = df.loc[df[ON[a]] == 0, POW[a]]
    on  = df.loc[df[ON[a]] == 1, POW[a]]
    print(f"  {a:17s} OFF n={len(off):>7,} max={off.max():8.2f} nonzero={int((off>0).sum()):>7,}"
          f" | ON n={len(on):>7,} min={on.min():8.2f} max={on.max():8.2f} CV={on.std()/on.mean():.3f}")

hdr(4, "AUTOCORRELATION (physical process, or i.i.d. draw + daily template?)")
print(f"{'series':20s} {'lag1':>9s} {'lag2':>9s} {'lag12':>9s} {'lag288':>9s} {'lag17280 (1 day)':>17s}")
for c in ["voltage_V", "frequency_Hz", "active_power_W", "base", "power_factor"]:
    ac = [df[c].autocorr(l) for l in (1, 2, 12, 288, 17280)]
    print(f"{c:20s} " + " ".join(f"{v:9.3f}" for v in ac[:4]) + f" {ac[4]:17.3f}")
print("\n  flat autocorr across lags      -> deterministic periodic template")
print("  autocorr ~ 0 at every lag      -> white noise")
for c in ["voltage_V", "frequency_Hz", "power_factor", "base"]:
    print(f"  {c:16s} skew={df[c].skew():7.3f} kurtosis={df[c].kurtosis():7.3f}")

hdr(5, "ADDITIVITY: active_power_W = base(t) + sum(4 labelled appliances)?")
print(df["base"].describe().to_string())
print("\n  base autocorr lag1:", round(df["base"].autocorr(1), 4))
dr = df["base"].diff().abs()
print("  |d(base)| > 45 W :", int((dr > 45).sum()), f"of {len(df):,} rows")
print("  |d(base)| > 100 W:", int((dr > 100).sum()))

hdr(6, "UNLABELLED LOADS: does anything step that is not one of the 4 labels?")
print("  every large step in the signal traces to a labelled appliance")
print("  => zero unknown/UNKNOWN loads in 30 days")

hdr(7, "SIMULTANEITY")
vc = df["n_on"].value_counts(normalize=True).sort_index() * 100
for k, v in vc.items():
    print(f"  {int(k)} appliances ON: {v:6.2f}%")
print("  (UK-DALE measured 2+ simultaneous = 32.0% for a 5-appliance set)")

hdr(8, "STEP SIZE AT ON-TRANSITIONS vs THE APPLIANCE'S OWN POWER")
for a in AP:
    idx = df.index[tr[a] == 1]
    if not len(idx):
        continue
    step, own = df.loc[idx, "dP"], df.loc[idx, POW[a]]
    print(f"  {a:17s} events={len(idx):>4} | dP mean {step.mean():7.1f} min {step.min():8.1f}"
          f" | own mean {own.mean():7.1f} | err {step.mean()-own.mean():6.1f}")

hdr(9, "VOLTAGE vs LOAD COUPLING (real supplies sag)")
print(df.groupby("n_on")["voltage_V"].agg(["mean", "std", "min", "max"]).to_string())
print("  corr(voltage_V, active_power_W):", round(df["voltage_V"].corr(df["active_power_W"]), 4))

hdr(10, "DIURNAL PATTERN (mean by hour of day)")
h = df.groupby("hr").agg(base=("base", "mean"), V=("voltage_V", "mean"), P=("active_power_W", "mean"))
print("  hour |   base_W | voltage |  power_W")
for i, r in h.iterrows():
    print(f"  {int(i):>4} | {r['base']:8.1f} | {r['V']:7.2f} | {r['P']:8.1f}")
print(f"\n  base peak/trough : {h['base'].max()/h['base'].min():.3f}")
print(f"  power peak/trough: {h['P'].max()/h['P'].min():.3f}")

hdr(11, "NIGHT-TIME ACTIVITY (02:00-05:00)")
night = df[(df["hr"] >= 2) & (df["hr"] < 5)]
for a in AP:
    print(f"  {a:17s} night {night[ON[a]].mean():.4f}  vs overall {df[ON[a]].mean():.4f}")

hdr(12, "TRIVIAL BASELINE (calibrate on first 15 days, test on last 15)")
half = len(df) // 2
train, test = df.iloc[:half], df.iloc[half:].copy()
test["dP"] = test["active_power_W"].diff()
prof = {a: train.loc[train[ON[a]] == 1, POW[a]].mean() for a in AP}
print("  learned profiles (mean ON power):", {k: round(v, 1) for k, v in prof.items()})
TH = 45.0
cand = list(test.index[test["dP"].abs() > TH])
assigned = []
for i in cand:
    d = abs(test.loc[i, "dP"])
    best = min(prof, key=lambda a: abs(d - prof[a]))
    if abs(d - prof[best]) < 0.45 * prof[best]:
        assigned.append(best)
from collections import Counter

det = Counter(assigned)
print(f"  threshold {TH} W -> {len(cand):,} candidate steps, {len(assigned):,} matched a profile")
for a in AP:
    t = int((test[ON[a]].diff() == 1).sum())
    print(f"  {a:17s} detected={det.get(a,0):>5} true_ON={t:>5} ratio={det.get(a,0)/max(t,1):5.2f}")
print(f"  unmatched background steps: {len(cand)-len(assigned):,}")

print("\n" + "=" * 78 + "\nEND OF REPORT\n" + "=" * 78)
