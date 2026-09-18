
import urllib.request, urllib.parse, json, time
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36',
      'Accept': 'application/json'}
def s2(doi):
    url = f'https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=title,year,citationCount,abstract'
    try:
        return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45))
    except Exception as e:
        return {'err': str(e)}
for doi in ['10.1016/j.apenergy.2019.01.061', '10.1016/j.ecolecon.2020.106635']:
    d = s2(doi); print('=' * 100)
    if 'err' in d: print(doi, 'ERR', d['err']); continue
    print('TITLE:', d.get('title')); print('YEAR:', d.get('year'), '| CITES:', d.get('citationCount'))
    print('ABS  :', (d.get('abstract') or '(none)')[:1800])
    time.sleep(2)
