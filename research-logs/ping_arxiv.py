
import urllib.request, urllib.parse, ssl
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36',
      'Accept': 'application/atom+xml,application/xml,text/xml,*/*'}
for base in ['https://export.arxiv.org/api/query?', 'http://export.arxiv.org/api/query?']:
    url = base + urllib.parse.urlencode({'search_query': 'all:electron', 'max_results': 1})
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30)
        print(base, '->', r.status, len(r.read()))
    except Exception as e:
        print(base, '-> ERR', e)
