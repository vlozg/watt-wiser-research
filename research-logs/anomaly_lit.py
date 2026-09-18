
import urllib.request, urllib.parse, json, re, time, xml.etree.ElementTree as ET

def arxiv(q, n=8):
    url = 'http://export.arxiv.org/api/query?' + urllib.parse.urlencode(
        {'search_query': q, 'start': 0, 'max_results': n, 'sortBy': 'relevance'})
    try:
        x = ET.fromstring(urllib.request.urlopen(url, timeout=40).read())
    except Exception as e:
        return [('ERR', str(e), '', '')]
    ns = {'a': 'http://www.w3.org/2005/Atom'}
    out = []
    for e in x.findall('a:entry', ns):
        out.append((e.find('a:title', ns).text.strip().replace('\n', ' '),
                    (e.find('a:summary', ns).text or '').strip().replace('\n', ' ')[:300],
                    e.find('a:published', ns).text[:7],
                    e.find('a:id', ns).text))
    return out

for q in ['all:"non-intrusive load monitoring" AND all:"fault detection"',
          'all:"non-intrusive load monitoring" AND all:"condition monitoring"',
          'all:"appliance" AND all:"anomaly detection" AND all:"smart meter"']:
    print('=' * 100); print('QUERY:', q)
    for t, ab, d, i in arxiv(q):
        print(f'  [{d}] {t}')
        print(f'      {ab}')
    time.sleep(3)
