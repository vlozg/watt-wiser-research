import sys, urllib.parse, subprocess, re, json, time
def arxiv(q, n=12, sort='relevance'):
    url = ('https://export.arxiv.org/api/query?search_query=' + urllib.parse.quote(q) +
           '&start=0&max_results=%d&sortBy=%s' % (n, sort))
    x = subprocess.run(['curl','-sL','--max-time','40',url], capture_output=True, text=True).stdout
    out=[]
    for e in re.findall(r'<entry>(.*?)</entry>', x, re.S):
        t = re.search(r'<title>(.*?)</title>', e, re.S)
        s = re.search(r'<summary>(.*?)</summary>', e, re.S)
        p = re.search(r'<published>(\d{4})', e)
        aid = re.search(r'<id>(.*?)</id>', e)
        out.append({'title': re.sub(r'\s+',' ',t.group(1)).strip() if t else '',
                    'year': p.group(1) if p else '',
                    'url': aid.group(1) if aid else '',
                    'abs': re.sub(r'\s+',' ',s.group(1)).strip()[:300] if s else ''})
    return out
if __name__=='__main__':
    for q in sys.argv[1:]:
        print('\n########## arXiv: '+q)
        for r in arxiv(q):
            print(f"  [{r['year']}] {r['title']}\n    {r['url']}\n    {r['abs'][:230]}")
        time.sleep(3)
