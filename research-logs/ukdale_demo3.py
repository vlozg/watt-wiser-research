
import numpy as np, collections, os

d = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'research-logs', 'sakunrasilka_nilm-test2') + os.sep
labels = dict(l.split() for l in open(d+'labels.dat'))
t1 = np.loadtxt(d+'channel_1.dat')[:, 0]
data = {}
for ch in range(1, 7):
    a = np.loadtxt(f'{d}channel_{ch}.dat')
    data[ch] = a[:, 1] if len(a) == len(t1) else np.interp(t1, a[:, 0], a[:, 1])

s5 = sum(data[ch] for ch in range(2, 7))
resid = data[1] - s5
print('agg-minus-sum residual: min %.1f max %.1f std %.3f' % (resid.min(), resid.max(), resid.std()))
print('=> channel_1 is the SUM of the 5 monitored channels, not a real mains meter reading.')
print('   (a real whole-home meter would carry ~40+ unmonitored loads on top)')

TH = 15.0
st = {ch: (data[ch] > TH) for ch in range(2, 7)}
nm = {ch: labels[str(ch)] for ch in range(2, 7)}

print()
print('--- how many appliances are ON at the same instant ---')
ncon = sum(st[ch].astype(int) for ch in range(2, 7))
dist = collections.Counter(ncon.tolist()); tot = len(ncon)
for k in sorted(dist):
    print(f'  {k} appliances on: {100*dist[k]/tot:6.2f}% of time  ({dist[k]:8d} samples)')
print(f'  -> 2 or more simultaneously ON: {100*sum(v for k,v in dist.items() if k>=2)/tot:.1f}% of the time')

ket = st[4]
others = sum(st[ch].astype(int) for ch in range(2, 7) if ch != 4)
kk = others[ket]
print(f'  -> when the KETTLE runs, another appliance is also on {100*(kk>=1).mean():.1f}% of that time')

print()
print('--- would the Shelly see these transitions? ---')
bands = [(0,30,'invisible (<30 VA floor)'), (30,230,'visible, +/-5% (30-230 W)'), (230,1e9,'accurate (>230 W)')]
trans = {}
for ch in range(2, 7):
    p = data[ch]
    idx = np.flatnonzero(np.diff(st[ch].astype(np.int8)) != 0)
    trans[ch] = np.abs(np.diff(p)[idx])
for ch in sorted(nm):
    stp = trans[ch]; n = len(stp); row = []
    for lo, hi, lab in bands:
        c = int(((stp >= lo) & (stp < hi)).sum())
        row.append(f'{lab}: {100*c/n:5.1f}%')
    print(f'{nm[ch]:16s} ' + ' | '.join(row))

print()
print('--- step-size overlap (confusability of the small loads) ---')
for ch in sorted(nm):
    p10, p50, p90 = np.percentile(trans[ch], [10, 50, 90])
    print(f'  {nm[ch]:16s} p10={p10:6.0f}  median={p50:6.0f}  p90={p90:7.0f} W   (n={len(trans[ch])})')

print()
print('--- fridge compressor ON-duration (why a 30-60 s baseline is unsound) ---')
f = st[2].astype(np.int8)
idx = np.flatnonzero(np.diff(f) != 0)
dur = np.diff(t1[idx])
on_dur = dur[0::2] if f[idx[0]] == 0 else dur[1::2]
on_dur = on_dur[on_dur > 0]
print(f'  n={len(on_dur)}  median={np.median(on_dur):.0f}s  p10={np.percentile(on_dur,10):.0f}s  p90={np.percentile(on_dur,90):.0f}s  max={on_dur.max():.0f}s')
print(f'  fraction of fridge cycles longer than a 60 s window: {100*(on_dur>60).mean():.0f}%')
