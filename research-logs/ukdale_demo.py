
import numpy as np, os, datetime, collections

d = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'research-logs', 'sakunrasilka_nilm-test2') + os.sep
labels = dict(l.split() for l in open(d+'labels.dat'))
chans = {}
for ch in range(1, 7):
    a = np.loadtxt(f'{d}channel_{ch}.dat')
    chans[ch] = (a[:,0], a[:,1])

# align on common timestamps
t1 = chans[1][0]
print('aggregate samples:', len(t1), 'span days:', (t1[-1]-t1[0])/86400)
sum_others = np.zeros(len(t1))
ok = True
for ch in range(2, 7):
    t, p = chans[ch]
    if len(t) != len(t1) or not np.allclose(t, t1):
        ok = False
        # resample by index if lengths differ
        p = np.interp(t1, t, p)
    sum_others += p
print('channels share identical timestamps:', ok)
agg = chans[1][1]
resid = agg - sum_others
print('aggregate vs sum(others): mean %.1f W | mean|resid| %.1f W | corr %.4f' % (
    resid.mean(), np.abs(resid).mean(), np.corrcoef(agg, sum_others)[0,1]))

# per-appliance on/off transitions at 6 s
TH = 15.0
names = {ch: labels.get(str(ch), str(ch)) for ch in range(2, 7)}
trans = {ch: [] for ch in names}
state = {ch: (chans[ch][1] > TH).astype(np.int8) for ch in names}
for ch in names:
    st = state[ch]
    idx = np.flatnonzero(np.diff(st) != 0)
    trans[ch] = idx

print()
print('--- transitions over %.0f days (threshold %.0f W) ---' % ((t1[-1]-t1[0])/86400, TH))
for ch in sorted(names):
    p = chans[ch][1]
    on = state[ch].sum()
    print(f'{names[ch]:16s} on={100*on/len(p):5.1f}% of time   transitions={len(trans[ch]):5d}   '
          f'({len([i for i in trans[ch] if state[ch][i]==0])} off->on, {len([i for i in trans[ch] if state[ch][i]==1])} on->off)')

# collision analysis: how many appliances change state per 6-s step
cnt = collections.Counter()
for ch in names:
    for i in trans[ch]:
        cnt[i] += 1
dist = collections.Counter(cnt.values())
tot = sum(dist.values())
print()
print('--- simultaneity at 6 s resolution (appliance ground truth) ---')
for k in sorted(dist):
    print(f'  {k} appliance(s) switching in the SAME 6-s sample: {dist[k]:5d}  ({100*dist[k]/tot:.1f}%)')
print('  total appliance transitions:', tot)

# same, widened to a 12-s window (a 1 Hz pipeline seeing neighbouring samples)
cnt2 = collections.Counter()
for ch in names:
    for i in trans[ch]:
        cnt2[i//2] += 1
dist2 = collections.Counter(cnt2.values()); tot2 = sum(dist2.values())
print()
print('--- simultaneity within a 12-second window ---')
for k in sorted(dist2):
    print(f'  {k} appliance(s) switching within 12 s: {dist2[k]:5d}  ({100*dist2[k]/tot2:.1f}%)')

# step-size separability per appliance (its own channel)
print()
print('--- per-appliance step magnitude |dP| (own channel) ---')
for ch in sorted(names):
    p = chans[ch][1]; idx = trans[ch]
    if len(idx) < 5: continue
    steps = np.abs(np.diff(p)[idx])
    steps = steps[steps > 5]
    print(f'{names[ch]:16s} n={len(steps):5d}  median={np.median(steps):7.0f} W  p10={np.percentile(steps,10):7.0f}  p90={np.percentile(steps,90):7.0f}')

# aggregate steps
dA = np.diff(agg)
big = np.abs(dA) > 30
print()
print('aggregate |dP|>30 W steps:', int(big.sum()), 'over %.0f days = %.1f/day' % ((t1[-1]-t1[0])/86400, big.sum()/((t1[-1]-t1[0])/86400)))
