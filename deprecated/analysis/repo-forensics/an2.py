
import os

import pandas as pd

df = pd.read_csv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'repo', 'WattWiser', 'data', 'raw', 'synthetic_shelly_data.csv'))
df["timestamp"] = pd.to_datetime(df["timestamp"])

AP = ["kettle","fridge","microwave","washing_machine"]
POW = {a: a+"_power_W" for a in AP}; ON = {a: a+"_on" for a in AP}
S = df[[POW[a] for a in AP]].sum(axis=1)
df["resid"] = df["active_power_W"] - S

print("=== A. ADDITIVITY: active_power_W - sum(4 appliances) ===")
print(df["resid"].describe().to_string())
print("resid min/max:", df["resid"].min(), df["resid"].max())
print("\nCorrelation resid vs active_power_W:", df["resid"].corr(df["active_power_W"]).round(4))
print("resid autocorr lag1:", df["resid"].autocorr(1).round(4))
print("\nresid by number of appliances ON:")
df["n_on"] = df[[ON[a] for a in AP]].sum(axis=1)
print(df.groupby("n_on")["resid"].agg(["count","mean","std","min","max"]).to_string())

print("\n=== B. Is appliance power ever nonzero when state=OFF? ===")
for a in AP:
    off = df[df[ON[a]]==0][POW[a]]
    on  = df[df[ON[a]]==1][POW[a]]
    print(f"  {a:17s} OFF: n={len(off):>7,} max={off.max():9.2f} nonzero={int((off>0).sum()):>7,} | ON: n={len(on):>7,} min={on.min():8.2f} max={on.max():8.2f} mean={on.mean():8.2f}")

print("\n=== C. INTERNAL CONSISTENCY ===")
df["VA_calc"] = df["voltage_V"]*df["current_A"]
df["PF_calc"] = df["active_power_W"]/df["apparent_power_VA"]
print("  VA  vs V*I   max abs err:", (df["apparent_power_VA"]-df["VA_calc"]).abs().max().round(4))
print("  PF  vs W/VA  max abs err:", (df["power_factor"]-df["PF_calc"]).abs().max().round(6))
df["P_from_VA_PF"] = df["apparent_power_VA"]*df["power_factor"]
print("  W   vs VA*PF  max abs err:", (df["active_power_W"]-df["P_from_VA_PF"]).abs().max().round(4))

print("\n=== D. cumulative_energy_Wh == cumsum(W)*5/3600 ? ===")
ce = (df["active_power_W"].cumsum()*5/3600)
print("  max abs err:", (df["cumulative_energy_Wh"]-ce).abs().max().round(4))

print("\n=== E. VOLTAGE vs LOAD coupling (real homes sag) ===")
print(df.groupby("n_on")["voltage_V"].agg(["mean","std","min","max"]).to_string())
print("  corr(voltage_V, active_power_W):", df["voltage_V"].corr(df["active_power_W"]).round(4))

print("\n=== F. STEP SIZE at kettle transitions vs kettle power ===")
d = df["active_power_W"].diff(); k = df["kettle_on"].diff()
up = df[(k==1)]; dn = df[(k==-1)]
print(f"  kettle 0->1: n={len(up)}, dP mean={up['active_power_W'].diff().mean():.1f}  (approx)")
print(f"  number of kettle ON events in 30 days: {int((k==1).sum())}")
for a in AP:
    kk = df[ON[a]].diff()
    print(f"  {a:17s} events={int((kk==1).sum()):>6,}  on-fraction={df[ON[a]].mean():.4f}")
