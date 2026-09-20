
import os

import numpy as np
import pandas as pd

df = pd.read_csv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'repo', 'WattWiser', 'data', 'raw', 'synthetic_shelly_data.csv'))
df["timestamp"] = pd.to_datetime(df["timestamp"])
AP=["kettle","fridge","microwave","washing_machine"]
df["base"] = df["active_power_W"] - df[[a+"_power_W" for a in AP]].sum(axis=1)

print("=== N. AUTOCORRELATION: is this a physical process or an i.i.d. draw? ===")
print(f"{'series':22s} {'lag1':>8s} {'lag2':>8s} {'lag12':>8s} {'lag288':>8s} {'lag17280':>9s}")
for c in ["voltage_V","frequency_Hz","active_power_W","base","power_factor"]:
    s = df[c]
    ac = [s.autocorr(l) for l in (1,2,12,288,17280)]
    print(f"{c:22s} " + " ".join(f"{v:8.3f}" for v in ac[:4]) + f" {ac[4]:9.3f}")

print("\n=== O. DISTRIBUTION SHAPE ===")
for c in ["voltage_V","frequency_Hz","power_factor","base"]:
    s = df[c]
    print(f"  {c:16s} skew {s.skew():7.3f} kurtosis {s.kurtosis():7.3f}")

print("\n=== P. DIURNAL PATTERN (mean by hour) ===")
df["hr"] = df["timestamp"].dt.hour
h = df.groupby("hr").agg(base=("base","mean"), V=("voltage_V","mean"), P=("active_power_W","mean"))
print("  hour |   base_W | voltage |  power_W")
for i,r in h.iterrows():
    print(f"  {int(i):>4} | {r['base']:8.1f} | {r['V']:7.2f} | {r['P']:8.1f}")
print(f"\n  base  peak/trough ratio: {h['base'].max()/h['base'].min():.3f}")
print(f"  power peak/trough ratio: {h['P'].max()/h['P'].min():.3f}")

print("\n=== Q. ARE APPLIANCE EVENTS TIME-OF-DAY PLAUSIBLE? ===")
for a in AP:
    on = df[df[a+"_on"]==1]
    print(f"  {a:17s} hour distribution: ", np.round(on['hr'].value_counts(normalize=True).sort_index().values,3)[:24].tolist())

print("\n=== R. NIGHT-TIME (02:00-05:00) ACTIVITY ===")
night = df[(df["hr"]>=2)&(df["hr"]<5)]
for a in AP:
    print(f"  {a:17s} night ON fraction: {night[a+'_on'].mean():.4f}  vs overall {df[a+'_on'].mean():.4f}")
