import sys, urllib.parse, subprocess, re, json, time, html

def get(url):
    return subprocess.run(['curl','-sL','--max-time','40','-A','Mozilla/5.0 (research)',url],
                          capture_output=True, text=True).stdout

def openalex(q, n=8):
    url = 'https://api.openalex.org/works?search=' + urllib.parse.quote(q) + '&per-page=%d&sort=cited_by_count:desc' % n
    try:
        j = json.loads(get(url))
    except Exception as e:
        return [{'err': str(e)}]
    out=[]
    for w in j.get('results', []):
        out.append({'title': w.get('title'),
                    'year': w.get('publication_year'),
                    'cites': w.get('cited_by_count'),
                    'venue': (w.get('primary_location') or {}).get('source',{}).get('display_name') if (w.get('primary_location') or {}).get('source') else None,
                    'doi': w.get('doi')})
    return out

if __name__ == '__main__':
    for q in sys.argv[1:]:
        print('\n########## OpenAlex: ' + q)
        for r in openalex(q):
            if 'err' in r:
                print('  ERR', r['err']); continue
            print(f"  [{r['year']}] (cited {r['cites']}) {r['title']}\n      {r['venue']} | {r['doi']}")
        time.sleep(2)
