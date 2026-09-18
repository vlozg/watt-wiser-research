import sys, urllib.parse, subprocess, re, json, time

def get(url):
    return subprocess.run(['curl','-sL','--max-time','40','-A','Mozilla/5.0 (research)',url],
                          capture_output=True, text=True).stdout

def oa_title(q, n=4):
    url = ('https://api.openalex.org/works?filter=title.search:' + urllib.parse.quote(q) +
           '&per-page=%d&sort=cited_by_count:desc' % n)
    try:
        j = json.loads(get(url))
    except Exception as e:
        return []
    out=[]
    for w in j.get('results', []):
        out.append((w.get('publication_year'), w.get('cited_by_count'), w.get('title'),
                    (w.get('primary_location') or {}).get('source',{}).get('display_name') if (w.get('primary_location') or {}).get('source') else '', w.get('doi')))
    return out

def arxiv_abs(aid):
    x = get('http://export.arxiv.org/api/query?id_list=' + aid)
    t = re.search(r'<entry>.*?<title>(.*?)</title>', x, re.S)
    s = re.search(r'<summary>(.*?)</summary>', x, re.S)
    return (re.sub(r'\s+',' ',t.group(1)).strip() if t else aid,
            re.sub(r'\s+',' ',s.group(1)).strip() if s else '')

TITLES = [
 "Nonintrusive appliance load monitoring",
 "Non-Intrusive Load Monitoring Approaches for Disaggregated Energy Sensing",
 "Neural NILM deep neural networks applied to energy disaggregation",
 "Towards reproducible state-of-the-art energy disaggregation",
 "Non-Intrusive Load Monitoring past present and future",
 "energy disaggregation low sampling rate",
 "A low-complexity energy disaggregation method",
 "PLAID aggregated load identification dataset",
 "WHITED dataset",
 "EMBED aggregated electricity consumption dataset",
]
for q in TITLES:
    print('\n#### ' + q)
    for y,c,t,v,d in oa_title(q):
        print(f'  [{y}] (cited {c}) {t}\n      {v} | {d}')
    time.sleep(1.5)

print('\n\n===== KEY ABSTRACT: How good is good enough? =====')
t,s = arxiv_abs('1510.08713')
print(t); print(s)
