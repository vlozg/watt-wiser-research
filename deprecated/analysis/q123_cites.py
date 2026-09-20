
import json
import time
import urllib.parse
import urllib.request


def fetch(url):
    with urllib.request.urlopen(url, timeout=25) as r:
        return json.load(r)
def by_doi(doi):
    try:
        js = fetch('https://api.openalex.org/works/https://doi.org/' + doi)
        ven = ((js.get('primary_location') or {}).get('source') or {}).get('display_name') or '-'
        print('DOI %s ->' % doi)
        print('   ', js.get('title'))
        print('    %s | %s | %d cites' % (js.get('publication_year'), ven, js.get('cited_by_count', 0)))
    except Exception as e:
        print('DOI', doi, '->', str(e)[:70])
def srch(q):
    try:
        js = fetch('https://api.openalex.org/works?filter=title.search:' + urllib.parse.quote(q) + '&sort=cited_by_count:desc&per-page=5')
        print('-- ' + q + ' (%d results)' % js.get('meta', {}).get('count', 0))
        for w in js.get('results', [])[:3]:
            doi = (w.get('doi') or 'no-doi').replace('https://doi.org/', '')
            ven = ((w.get('primary_location') or {}).get('source') or {}).get('display_name') or '-'
            print('   %s | %s | %d cites | %s | %s' % (w.get('publication_year'), (w.get('title') or '')[:100], w.get('cited_by_count', 0), doi[:44], ven[:34]))
    except Exception as e:
        print('--', q, '->', str(e)[:70])
by_doi('10.1109/tsg.2023.3261271'); time.sleep(3)
by_doi('10.1016/j.heliyon.2024.e30666'); time.sleep(3)
by_doi('10.1109/cccs.2019.8888140'); time.sleep(3)
srch('appliance fault detection smart meter'); time.sleep(3)
srch('fault detection non-intrusive load')
