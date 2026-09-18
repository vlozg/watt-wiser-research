import subprocess, re, urllib.parse, time, sys
def get(u): return subprocess.run(['curl','-sL','--max-time','40','-A','Mozilla/5.0',u],capture_output=True,text=True).stdout
def arxiv(q, n=5):
    url='http://export.arxiv.org/api/query?search_query='+urllib.parse.quote(q,safe='')+'&start=0&max_results=%d&sortBy=relevance'%n
    x=get(url)
    for e in re.findall(r'<entry>(.*?)</entry>',x,re.S):
        t=re.search(r'<title>(.*?)</title>',e,re.S); s=re.search(r'<summary>(.*?)</summary>',e,re.S)
        a=re.search(r'<id>(.*?)</id>',e)
        print('  T:',re.sub(r'\s+',' ',t.group(1)).strip() if t else '')
        print('    ',a.group(1) if a else '')
        print('    ',re.sub(r'\s+',' ',s.group(1)).strip()[:600] if s else '')
    return
def absid(aid):
    x=get('http://export.arxiv.org/api/query?id_list='+aid)
    t=re.search(r'<entry>.*?<title>(.*?)</title>',x,re.S); s=re.search(r'<summary>(.*?)</summary>',x,re.S)
    print('  T:',re.sub(r'\s+',' ',t.group(1)).strip() if t else aid)
    print('   ',re.sub(r'\s+',' ',s.group(1)).strip() if s else '')
print('=== Batra 2019 reproducible SOTA ===')
absid('1908.00941')
print()
print('=== search: NILM generalization to unseen houses ===')
arxiv('all:"energy disaggregation" AND all:generalization unseen houses transfer')
print()
print('=== search: sampling rate effect on NILM performance ===')
arxiv('all:"load disaggregation" AND all:"sampling rate" performance')
