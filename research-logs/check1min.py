
import csv, statistics, os
p=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'research-logs', 'kaggle_1min', 'household_power_1min.csv')
rows=list(csv.DictReader(open(p)))
print('rows:', len(rows), 'cols:', list(rows[0].keys()))
print('first ts:', rows[0]['timestamp'], ' last ts:', rows[-1]['timestamp'])
bad=0; diffs=[]
for r in rows[:5000]:
    comps=sum(float(r[c]) for c in r if c.endswith('_w') and c!='total_w')
    diffs.append(float(r['total_w'])-comps)
print('total_w minus sum(components): mean %.2f  std %.2f  (0.00 would mean it is a pure sum)' % (statistics.mean(diffs), statistics.pstdev(diffs)))
vals=[float(r['fridge_w']) for r in rows]
print('fridge_w distinct values:', len(set(vals)), 'of', len(vals), '-> looks synthetic/simulated' if len(set(vals))<len(vals)*0.5 else '-> looks measured')
