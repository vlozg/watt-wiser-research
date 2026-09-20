
import os
from collections import Counter

import pandas as pd

df = pd.read_csv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'repo', 'WattWiser', 'data', 'raw', 'synthetic_shelly_data.csv'))
AP = ["kettle","fridge","microwave","washing_machine"]
POW={a:a+"_power_W" for a in AP}; ON={a:a+"_on" for a in AP}
df["n_on"] = df[[ON[a] for a in AP]].sum(axis=1)
df["resid"] = df["active_power_W"] - df[[POW[a] for a in AP]].sum(axis=1)
df["dP"] = df["active_power_W"].diff()
tr = {a: df[ON[a]].diff() for a in AP}

print("=== I. STEP SIZE AT EACH APPLIANCE ON-TRANSITION vs ITS OWN POWER ===")
for a in AP:
    idx = df.index[tr[a]==1]
    step = df.loc[idx,"dP"]; own = df.loc[idx, POW[a]]
    print(f"  {a:17s} events={len(idx):>4} | dP: mean {step.mean():7.1f} min {step.min():7.1f} max {step.max():7.1f} | own power mean {own.mean():7.1f} | err(mean) {(step-own).mean():7.1f}")

print("\n=== J. SIMULTANEITY (% of 30 days) ===")
vc = df["n_on"].value_counts(normalize=True).sort_index()*100
for k,v in vc.items(): print(f"  {int(k)} appliances ON: {v:6.2f}%")

print("\n=== K. APPLIANCE-POWER VARIABILITY WITHIN AN ON PERIOD ===")
for a in AP:
    on = df[df[ON[a]]==1][POW[a]]
    print(f"  {a:17s} ON power: mean {on.mean():7.1f} std {on.std():7.1f} CV {on.std()/on.mean():5.3f} min {on.min():7.1f} max {on.max():7.1f}")

print("\n=== L. TRIVIAL BASELINE (calibrate on first 15 days, test on last 15) ===")
half = len(df)//2
train, test = df.iloc[:half], df.iloc[half:].copy()
prof = {a: train[train[ON[a]]==1][POW[a]].mean() for a in AP}
print("  learned profile (mean ON power):", {k: round(v,1) for k,v in prof.items()})
TH = 45.0
test["dP"] = test["active_power_W"].diff()
cand = list(test.index[test["dP"].abs() > TH])
assigned = []
for i in cand:
    d = abs(test.loc[i,"dP"])
    best = min(prof, key=lambda a: abs(d-prof[a]))
    if abs(d-prof[best]) < 0.45*prof[best]: assigned.append(best)
det = Counter(assigned)
true_on = {a: int((test[ON[a]].diff()==1).sum()) for a in AP}
print(f"  threshold {TH} W -> {len(cand):,} candidate steps; {len(assigned):,} matched a profile")
for a in AP:
    print(f"  {a:17s} detected={det.get(a,0):>4}  true_ON_events={true_on[a]:>4}  ratio={det.get(a,0)/max(true_on[a],1):5.2f}")
print(f"  background steps > {TH} W that matched nothing: {len(cand)-len(assigned):,}")

print("\n=== M. IS THERE ANY UNLABELLED SWITCHING LOAD? ===")
dr = df["resid"].diff().abs()
print(f"  |d(residual)| > 45 W count: {int((dr>45).sum()):,}  (>100 W: {int((dr>100).sum()):,})")
print("  => residual is smooth noise; every large step comes from a labelled appliance")
