
import urllib.request, urllib.parse, json, time
UA = {'User-Agent': 'research-bot (mailto:research@example.com)'}

def rebuild(inv):
    if not inv: return ''
    pos = {}
    for w, ids in inv.items():
        for i in ids: pos[i] = w
    return ' '.join(pos[k] for k in sorted(pos))

def find(title):
    url = 'https://api.openalex.org/works?' + urllib.parse.urlencode({'search': title, 'per-page': 1})
    d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45))
    r = d['results'][0]
    return r

for t in ["Can non-intrusive load monitoring be used for identifying an appliance's anomalous behaviour",
          "Evaluation of Non-intrusive Load Monitoring Algorithms for Appliance-level Anomaly Detection",
          "Real-time Feedback and Electricity Consumption: A Field Experiment Assessing the Potential for Savings and Persistence",
          "Prices, information and nudges for residential electricity conservation: A meta-analysis"]:
    r = find(t)
    print('=' * 100)
    print('TITLE :', r.get('title'))
    print('YEAR  :', r.get('publication_year'), '| CITES:', r.get('cited_by_count'), '| DOI:', r.get('doi'))
    print('ABS   :', rebuild(r.get('abstract_inverted_index'))[:1700] or '(no abstract)')
    time.sleep(1)
