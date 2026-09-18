
import urllib.request, urllib.parse, json, time
UA = {'User-Agent': 'research-bot (mailto:research@example.com)'}

def oa(q, n=6, extra=''):
    url = 'https://api.openalex.org/works?' + urllib.parse.urlencode(
        {'search': q, 'per-page': n, 'sort': 'relevance_score:desc'}) + extra
    try:
        d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45))
    except Exception as e:
        return [('ERR ' + str(e), '', '')]
    out = []
    for w in d.get('results', []):
        out.append((w.get('title') or '', w.get('publication_year'), w.get('cited_by_count', 0)))
    return out

for q in ['non-intrusive load monitoring fault detection appliance',
          'appliance condition monitoring smart meter',
          'residential electricity feedback consumption savings meta-analysis',
          'always-on standby power residential consumption share']:
    print('=' * 100); print('QUERY:', q)
    for t, y, c in oa(q):
        print(f'  [{y}] cites={c:5d}  {t[:140]}')
    time.sleep(1)
