
import numpy as np, json, time, urllib.request, urllib.parse

base = 'projects/watt-wiser/research-logs/sakunrasilka_nilm-test2/'
W = 3.6e6

head = open(base + 'channel_4.dat', 'rb').read(60)
print('raw head:', head[:44])
istext = all(32 <= b < 127 or b in (9, 10, 13) for b in head[:40])
print('text-like:', istext)

def load(c):
    p = base + 'channel_%d.dat' % c
    if istext:
        a = np.loadtxt(p, ndmin=2)
        return a[:, 0], a[:, 1]
    raw = open(p, 'rb').read()
    best = None
    for rec in [(np.dtype([('t','<i8'),('v','<f4')]), 12), (np.dtype([('t','<i8'),('v','<f8')]), 16), (np.dtype([('t','<i4'),('v','<f4')]), 8)]:
        dt_, sz = rec
        n = len(raw) // sz
        a = np.frombuffer(raw[:n*sz], dtype=dt_)
        t, v = a['t'].astype(np.float64), a['v'].astype(np.float64)
        okv = float(np.mean((v >= -1) & (v <= 20000))) if n else 0
        d = np.diff(t[:100000])
        okdt = float(np.mean(np.abs(d - 6e9) < 1e8)) if n > 1 else 0
        score = okdt * 2 + okv
        if best is None or score > best[0]:
            best = (score, t, v)
    return best[1], best[2]

t1, v1 = load(1)
print('ch1 first rows:', t1[:3], v1[:3])

ch = {}
for c in range(1, 7):
    t, v = load(c)
    ch[c] = (t, v)
cstart = max(t[0] for t, v in ch.values())
cend = min(t[-1] for t, v in ch.values())
print('common window: %.2f days' % ((cend - cstart) / 86400.0))
N = {}
for c in range(1, 7):
    t, v = ch[c]
    m = (t >= cstart) & (t <= cend)
    N[c] = int(m.sum())
n = min(N.values())
print('in-window counts:', N, '-> using', n)
DT = float(np.median(np.diff(ch[1][0][:200000])))
unit = 1e9 if DT > 1e6 else 1.0
dt_s = DT / unit
days = (cend - cstart) / unit / 86400.0
print('dt(s)=%.2f days=%.2f' % (dt_s, days))

names = {2: 'fridge', 3: 'dish_washer', 4: 'kettle', 5: 'washing_machine', 6: 'monitor'}
tot = 0.0
st = {}
for c in range(2, 7):
    t, v = ch[c]
    m = (t >= cstart) & (t <= cend)
    v = v[m][:n]
    e = v.sum() * dt_s / W
    tot += e
    on = v > 5.0
    st[c] = (e, on.mean(), float(np.median(v[on])) if on.sum() else 0.0)
print('%-16s %9s %7s %6s %9s %7s' % ('appliance', 'kWh/win', 'duty%', 'W_on', 'kWh/yr', 'share%'))
for c in range(2, 7):
    e, duty, won = st[c]
    print('%-16s %9.1f %7.1f %6.0f %9.0f %7.1f' % (names[c], e, duty*100, won, e*365.0/days, 100*e/tot))
print('named total kWh/win: %.1f' % tot)
print('kettle annualized: %.0f kWh/yr  vs 10 W always-on router: 87.6 kWh/yr' % (st[4][0]*365.0/days))
ordsh = sorted(((100*st[c][0]/tot, names[c]) for c in range(2, 7)), reverse=True)
print('materiality ranking (share of named energy):', ', '.join('%s %.0f%%' % (nm, s) for s, nm in ordsh))

print()
print('=== OpenAlex retries ===')
def oa(q):
    url = 'https://api.openalex.org/works?filter=title.search:' + urllib.parse.quote(q) + '&sort=cited_by_count:desc&per-page=4'
    for attempt in range(2):
        try:
            with urllib.request.urlopen(url, timeout=25) as r:
                js = json.load(r)
            print('-- ' + q)
            for w in js.get('results', [])[:2]:
                doi = (w.get('doi') or 'no-doi').replace('https://doi.org/', '')
                ven = ((w.get('primary_location') or {}).get('source') or {}).get('display_name') or '-'
                print('   %s | %s | %d cites | %s | %s' % (w.get('publication_year'), (w.get('title') or '')[:76], w.get('cited_by_count', 0), doi[:44], ven[:36]))
            return
        except Exception as e:
            print('-- ' + q + ' -> ' + str(e)[:60])
            time.sleep(12)
    print('   (gave up)')
for q in ['appliance fault detection non-intrusive load monitoring',
          'context-aware non-intrusive load monitoring',
          'unknown appliances non-intrusive load monitoring',
          'new appliance detection smart meter',
          'occupancy information energy disaggregation']:
    oa(q); time.sleep(4)
