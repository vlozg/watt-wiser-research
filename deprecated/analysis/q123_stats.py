
import csv
import json
import os
import urllib.parse
import urllib.request

import numpy as np

W = 3.6e6  # J per kWh
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root

print("=== PART 1: UK-DALE slice (research_logs) ===")
base = os.path.join(ROOT, 'research-logs', 'sakunrasilka_nilm-test2') + os.sep
labels = open(base + 'labels.dat').read().strip()
print("labels:", labels.replace("\n", " | "))

def load_dat(path):
    raw = open(path, 'rb').read()
    n4 = len(raw) // 12
    n8 = len(raw) // 16
    a4 = np.frombuffer(raw[:n4*12], dtype=np.dtype([('t','<i8'),('v','<f4')]))
    a8 = np.frombuffer(raw[:n8*16], dtype=np.dtype([('t','<i8'),('v','<f8')]))
    ok4 = float(np.mean((a4['v'] >= -1) & (a4['v'] <= 20000))) if n4 else 0
    ok8 = float(np.mean((a8['v'] >= -1) & (a8['v'] <= 20000))) if n8 else 0
    if ok8 > ok4:
        return a8['t'].astype(np.int64), a8['v'].astype(np.float64)
    return a4['t'].astype(np.int64), a4['v'].astype(np.float64)

ch = {}
for c in range(1, 7):
    t, v = load_dat(base + 'channel_%d.dat' % c)
    ch[c] = (t, v)
N = min(len(v) for t, v in ch.values())
print("records per channel:", {c: len(v) for c, (t, v) in ch.items()})
print("using common N =", N)
dts = []
for c in range(1, 7):
    t, v = ch[c]
    dts.append(float(np.median(np.diff(t[:100000]))))
print("median dt (ns):", set(int(d) for d in dts))
DT = dts[0] / 1e9
days = (ch[1][0][N-1] - ch[1][0][0]) / 1e9 / 86400.0
print("dt(s)=%.2f  days=%.2f" % (DT, days))

names = {1: 'aggregate(sum)', 2: 'fridge', 3: 'dish_washer', 4: 'kettle', 5: 'washing_machine', 6: 'monitor'}
tot_named = 0.0
stats = {}
for c in range(2, 7):
    v = ch[c][1][:N]
    e = v.sum() * DT / W
    tot_named += e
    on = v > 5.0
    duty = on.mean()
    mon = float(np.median(v[on])) if on.sum() else 0.0
    stats[c] = (e, duty, mon)
print("%-18s %9s %7s %6s %9s %8s" % ("appliance", "kWh/70d", "duty%", "W_on", "kWh/yr", "share%"))
for c in range(2, 7):
    e, duty, mon = stats[c]
    print("%-18s %9.1f %7.1f %6.0f %9.0f %8.1f" % (names[c], e, duty*100, mon, e*365.0/days, 100*e/tot_named))
k = stats[4][0]
print("kettle vs 10 W router annualized: kettle %.0f kWh/yr, router 87.6 kWh/yr" % (k*365.0/days))

print()
print("=== PART 2: synthetic Shelly CSV (unnamed residual) ===")
p = os.path.join(ROOT, 'repo', 'WattWiser', 'data', 'raw', 'synthetic_shelly_data.csv')
f = open(p)
hdr = next(csv.reader(f))
ia = hdr.index('active_power_W')
ik = hdr.index('kettle_power_W'); ifr = hdr.index('fridge_power_W')
imw = hdr.index('microwave_power_W'); iwm = hdr.index('washing_machine_power_W')
ap_cols = [ik, ifr, imw, iwm]
sums = np.zeros(6); rows = 0
series = [[] for _ in range(6)]
for r in csv.reader(f):
    try:
        vals = [float(r[ia]), float(r[ik]), float(r[ifr]), float(r[imw]), float(r[iwm])]
    except ValueError:
        continue
    base_w = vals[0] - (vals[1] + vals[2] + vals[3] + vals[4])
    all6 = vals + [base_w]
    sums += np.array(all6); rows += 1
    for i in range(6):
        series[i].append(all6[i])
print("rows:", rows)
tot = sums[0]
lbl = ['whole_house', 'kettle', 'fridge', 'microwave', 'washing_machine', 'BASE (unnamed)']
for i in range(6):
    print("%-18s %9.1f kWh/30d  %6.1f%% of total" % (lbl[i], sums[i]/W, 100*sums[i]/tot))
b = np.array(series[5])
print("BASE: mean %.1f W, p5 %.1f W, p95 %.1f W" % (b.mean(), np.percentile(b, 5), np.percentile(b, 95)))
for i, nm in enumerate(['kettle', 'fridge', 'microwave', 'washing_machine'], start=1):
    s = np.array(series[i]); d = np.abs(np.diff(s))
    print("%-16s median |dP| = %.0f W" % (nm, np.median(d[d > 0.5]) if (d > 0.5).any() else 0))

print()
print("=== PART 3: OpenAlex verification ===")
def oa(q, n=2):
    url = 'https://api.openalex.org/works?filter=title.search:' + urllib.parse.quote(q) + '&sort=cited_by_count:desc&per-page=4'
    try:
        with urllib.request.urlopen(url, timeout=25) as r:
            js = json.load(r)
        print("-- " + q)
        for w in js.get('results', [])[:n]:
            doi = (w.get('doi') or 'no-doi').replace('https://doi.org/', '')
            ven = ((w.get('primary_location') or {}).get('source') or {}).get('display_name') or '-'
            print("   %s | %s | %d cites | %s | %s" % (str(w.get('publication_year')), (w.get('title') or '')[:78], w.get('cited_by_count', 0), doi[:44], ven[:38]))
    except Exception as e:
        print("-- " + q + " -> ERROR " + str(e)[:90])
for q in [
    "open set recognition non-intrusive load monitoring",
    "novel appliance detection energy disaggregation",
    "appliance fault detection non-intrusive load monitoring",
    "user feedback energy disaggregation",
    "context-aware non-intrusive load monitoring",
    "appliance usage survey prior energy disaggregation",
]:
    oa(q)
