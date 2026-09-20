
import os

import pandas as pd

df = pd.read_csv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'repo', 'WattWiser', 'data', 'raw', 'synthetic_shelly_data.csv'))
AP = ["kettle","fridge","microwave","washing_machine"]
POW={a:a+"_power_W" for a in AP}; ON={a:a+"_on" for a in AP}
df["resid"] = df["active_power_W"] - df[[POW[a] for a in AP]].sum(axis=1)
df["dP"] = df["active_power_W"].diff()
df["dR"] = df["resid"].diff()

print("=== G. DOES THE BASE LOAD EVER STEP? (residual diffs) ===")
print("  |dR| describe:\n", df["dR"].abs().describe().to_string())
print("  largest 5 |dR|:", df["dR"].abs().nlargest(5).round(2).tolist())

# transitions
trans = {}
for a in AP: trans[a] = df[ON[a]].diff()
df["n_trans"] = sum((trans[a]!=0).astype(int) for a in AP)
quiet = df[df["n_trans"]==0]
print("\n=== H. |dP| WHEN *NO* APPLIANCE SWITCHES (pure base-load drift) ===")
print(quiet["dP"].abs().describe().to_string())
print("  P99.9:", quiet["dP"].abs().quantile(0.999).round(2), " max:", quiet["dP"].abs().max().round(2))

print("\n=== I. STEP SIZE AT EACH APPLIANCE ON-TRANSITION vs ITS OWN POWER ===")
for a in AP:
    idx = df.index[trans[a]==1]
    step = df.loc[idx,"dP"]
    own  = df.loc[idx,POW[a]]
    n_on = df.loc[idx,"n_on"]
    print(f"  {a:17s} events={len(idx):>4}  |dP|=mean {step.mean():7.1f} min {step.min():7.1f}  own power mean {own.mean():7.1f}  | coincident others ON: {(n_on>1).sum()}")

print("\n=== J. SIMULTANEITY ===")
print(df["n_on"].value_counts(normalize=True).sort_index().round(4).to_string())

print("\n=== K. TRIVIAL BASELINE: threshold dP, match to nearest calibrated profile ===")
half = len(df)//2
train, test = df.iloc[:half], df.iloc[half:].copy()
prof = {}
for a in AP:
    on = train[train[ON[a]]==1][POW[a]]
    prof[a] = on.mean()
print("  calibration profiles (mean ON power):", {k: round(v,1) for k,v in prof.items()})

TH = 45.0
tp={a:0 for a in AP}; fp={a:0 for a in AP}; fn={a:0 for a in AP}
for a in AP:
    k = test[ON[a]].diff()
    tp[a] = int((k==1).sum()); fn[a] = int((k==-1).sum())
# detect steps in test
cand = test.index[test["dP"].abs() > TH]
assign = {}
for i in cand:
    d = test.loc[i,"dP"]
    best = min(prof, key=lambda a: abs(abs(d)-prof[a]))
    if abs(abs(d)-prof[best]) < 0.45*prof[best]:
        assign[i]=best
from collections import Counter

det = Counter(assign.values())
print(f"  threshold {TH} W -> {len(cand):,} candidate steps, {len(assign):,} matched to a profile")
print("  detected counts:", dict(det))
print("  true ON events in test half:", {a: tp[a] for a in AP})
print("  base-load drift steps above threshold:", int((test['dP'].abs()>TH).sum()) - len(cand) + len(cand))
print("\n  --- precision/recall (counts) ---")
for a in AP:
    d = det.get(a,0); t = tp[a]
    print(f"  {a:17s} detected={d:>5} true={t:>5} ratio={d/max(t,1):.2f}")
