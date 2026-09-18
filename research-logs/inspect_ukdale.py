
import glob, os, datetime
d = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'research-logs', 'sakunrasilka_nilm-test2') + os.sep
labels = dict(l.split() for l in open(d+'labels.dat'))
for f in sorted(glob.glob(d+'channel_*.dat'), key=lambda x:int(''.join(c for c in os.path.basename(x) if c.isdigit()))):
    ts=[]; ps=[]
    for line in open(f):
        p=line.split()
        if len(p)<2: continue
        ts.append(float(p[0])); ps.append(float(p[1]))
    ch=int(''.join(c for c in os.path.basename(f) if c.isdigit()))
    dts=[ts[i+1]-ts[i] for i in range(min(2000,len(ts)-1))]
    import statistics
    print(f'{os.path.basename(f):14s} {labels.get(str(ch),"?"):22s} n={len(ts):7d}  {datetime.datetime.utcfromtimestamp(ts[0]):%Y-%m-%d %H:%M} -> {datetime.datetime.utcfromtimestamp(ts[-1]):%Y-%m-%d %H:%M}  dt_median={statistics.median(dts):.1f}s  Pmin={min(ps):.0f} Pmax={max(ps):.0f} Pmean={statistics.mean(ps):.0f}')
