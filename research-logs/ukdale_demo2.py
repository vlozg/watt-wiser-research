
import numpy as np, collections, datetime, os

d = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'research-logs', 'sakunrasilka_nilm-test2') + os.sep
labels = dict(l.split() for l in open(d+'labels.dat'))
t1 = np.loadtxt(d+'channel_1.dat')[:,0]
data = {ch: np.loadtxt(f'{d}channel_{ch}.dat')[:,1] for ch in range(1,7)}

# confirm the 'aggregate' is just a sum
s5 = sum(data[ch] for ch in range(2,7))
resid = data[1] - s5
print('agg-minus-sum residual: min %.1f max %.1f std %.3f  -> aggregate channel is synthetic, not a real meter'
      % (resid.min(), resid.max(), resid.std()))

TH = 15.0
st = {ch: (data[ch] > TH) for ch in range(2,7)}
nm = {ch: labels[str(ch)] for ch in range(2,7)}

# simultaneous ON-state analysis
print()
print('--- how many appliances are ON at the same instant ---')
ncon = sum(st[ch].astype(int) for ch in range(2,7))
dist = collections.Counter(ncon.tolist())
tot = len(ncon)
for k in sorted(dist):
    lab = {0:'nothing measurable on',1:'exactly 1 on',2:'2 on',3:'3 on',4:'4 on',5:'5 on'}.get(k, f'{k} on')
    print(f'  {lab:22s} {100*dist[k]/tot:6.2f}% of time   ({dist[k]:8d} samples)')
print(f'  -> 2 or more appliances simultaneously ON: {100*sum(v for k,v in dist.items() if k>=2)/tot:.1f}% of the time')

# kettle specifically
ket = st[4]
others = sum(st[ch].astype(int) for ch in range(2,7) if ch != 4)
kk = others[ket]
if kk.sum():
    print(f'  -> when the KETTLE is on, {100*(kk>=1).mean():.1f}% of the time at least one other appliance is also on')

# visibility ladder vs Shelly limits
print()
print('--- would the Shelly even SEE these transitions? (30 VA floor, +/-5% below ~230 W) ---')
bands = [(0,30,'invisible  (<30 VA floor)'),(30,230,'visible but +/-5% (30-230 W)'),(230,1e9,'accurate (>230 W)')]
trans = {}
for ch in range(2,7):
    p = data[ch]; idx = np.flatnonzero(np.diff(st[ch].astype(np.int8)) != 0)
    trans[ch] = np.abs(np.diff(p)[idx])
for ch in sorted(nm):
    stp = trans[ch]; n = len(stp)
    row = []
    for lo,hi,lab in bands:
        c = int(((stp>=lo)&(stp<hi)).sum())
        row.append(f'{lab}: {100*c/n:5.1f}%')
    print(f'{nm[ch]:16s} ' + ' | '.join(row))

# confusability of the small appliances
print()
print('--- step-size overlap between appliances (the confusability test) ---')
small = [ch for ch in range(2,7) if np.median(trans[ch]) < 500]
print('appliances whose typical step is under 500 W:', [nm[c] for c in small])
for ch in small:
    p10,p50,p90 = np.percentile(trans[ch],[10,50,90])
    print(f'  {nm[ch]:16s} p10={p10:6.0f}  median={p50:6.0f}  p90={p90:6.0f} W')

# fridge duty cycle -> why a 30-60 s baseline is useless
f = st[2].astype(np.int8)
idx = np.flatnonzero(np.diff(f)!=0)
dur = np.diff(t1[idx])
on_dur = dur[0::2] if f[idx[0]]==0 else dur[1::2]
print()
print('--- fridge ON-duration (compressor cycles) ---')
print(f'  n={len(on_dur)}  median={np.median(on_dur):.0f}s  p10={np.percentile(on_dur,10):.0f}s  p90={np.percentile(on_dur,90):.0f}s')
print(f'  a 30-60 second baseline window is shorter than {100*(on_dur>60).mean():.0f}% of fridge cycles')
