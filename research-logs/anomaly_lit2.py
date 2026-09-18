
import urllib.request, urllib.parse, time, xml.etree.ElementTree as ET

UA = {'User-Agent': 'Mozilla/5.0 (compatible; research-bot)'}

def arxiv(q, n=6):
    url = 'http://export.arxiv.org/api/query?' + urllib.parse.urlencode(
        {'search_query': q, 'start': 0, 'max_results': n, 'sortBy': 'relevance'})
    try:
        x = ET.fromstring(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45).read())
    except Exception as e:
        return [('ERR', str(e), '', '')]
    ns = {'a': 'http://www.w3.org/2005/Atom'}
    return [(e.find('a:title', ns).text.strip().replace('\n', ' '),
             (e.find('a:summary', ns).text or '').strip().replace('\n', ' ')[:340],
             e.find('a:published', ns).text[:7],
             e.find('a:id', ns).text) for e in x.findall('a:entry', ns)]

qs = ['all:"non-intrusive load monitoring" AND all:"fault detection"',
      'all:"non-intrusive load monitoring" AND all:"condition monitoring"',
      'all:"appliance" AND all:"electricity" AND all:"anomaly detection"']
for q in qs:
    print('=' * 100); print('QUERY:', q)
    for t, ab, d, i in arxiv(q):
        print(f'  [{d}] {t}')
        print(f'      {ab}')
    time.sleep(3)
