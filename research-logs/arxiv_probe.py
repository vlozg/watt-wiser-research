
import urllib.request, urllib.parse
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36',
      'Accept': 'application/atom+xml,application/xml,text/xml,*/*'}
def try_url(u):
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30)
        b = r.read()
        return f'{r.status} len={len(b)} entries={b.count(b"<entry")}'
    except Exception as e:
        return 'ERR ' + str(e)

base = 'https://export.arxiv.org/api/query?'
variants = {
 'plus-quoted': base + 'search_query=all%3A%22non-intrusive+load+monitoring%22&max_results=3',
 'pct20-quoted': base + 'search_query=all%3A%22non-intrusive%20load%20monitoring%22&max_results=3',
 'plain-words': base + 'search_query=all%3Anon-intrusive+load+monitoring&max_results=3',
 'and-quoted': base + 'search_query=all%3A%22non-intrusive%20load%20monitoring%22%20AND%20all%3A%22fault%22&max_results=3',
 'ab-query': base + 'search_query=abs%3A%22load%20disaggregation%22&max_results=3',
}
for k, v in variants.items():
    print(f'{k:16s} {try_url(v)}')
