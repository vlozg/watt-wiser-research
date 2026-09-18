#!/usr/bin/env python3
import sys, re, html, json, urllib.parse, subprocess, os, time

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'raw')
os.makedirs(OUT, exist_ok=True)

def fetch(q):
    url = 'https://www.bing.com/search?q=' + urllib.parse.quote(q) + '&count=20&setlang=en&cc=US'
    fn = os.path.join(OUT, 'bing_' + re.sub(r'\W+', '_', q)[:60] + '.html')
    subprocess.run(['curl','-sL','--max-time','35','-A',UA, url, '-o', fn], check=False)
    return open(fn, encoding='utf-8', errors='replace').read()

def parse(x):
    out = []
    for m in re.finditer(r'<li class="b_algo".*?(?=<li class="b_algo"|</ol>)', x, re.S):
        blk = m.group(0)
        a = re.search(r'<h2[^>]*>\s*<a[^>]*href="(http[^"]+)"[^>]*>(.*?)</a>', blk, re.S)
        if not a:
            continue
        url = html.unescape(a.group(1))
        title = html.unescape(re.sub(r'<[^>]+>', '', a.group(2))).strip()
        cap = ''
        for pat in (r'<p class="b_lineclamp[^"]*"[^>]*>(.*?)</p>', r'<p[^>]*>(.*?)</p>'):
            c = re.search(pat, blk, re.S)
            if c:
                cap = html.unescape(re.sub(r'<[^>]+>', '', c.group(1)))
                cap = re.sub(r'\s+', ' ', cap).strip()
                break
        out.append({'title': title, 'url': url, 'snippet': cap[:260]})
    return out

if __name__ == '__main__':
    for q in sys.argv[1:]:
        print('\n########## ' + q)
        try:
            res = parse(fetch(q))
            for r in res[:8]:
                print(f"  * {r['title']}\n    {r['url']}\n    {r['snippet']}")
            if not res:
                print('  (no parsed results)')
        except Exception as e:
            print('  ERR', e)
        time.sleep(1)
