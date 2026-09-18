import sys, json, subprocess, re, html
def topic(tid, maxposts=25):
    x = subprocess.run(['curl','-sL','--max-time','40','-A','Mozilla/5.0',
        f'https://community.home-assistant.io/t/{tid}.json?include_raw=1'],capture_output=True,text=True).stdout
    try: j=json.loads(x)
    except: return None
    title=j.get('title')
    posts=j.get('post_stream',{}).get('posts',[])[:maxposts]
    out=[]
    for p in posts:
        b=re.sub(r'<[^>]+>','',p.get('cooked',''))
        b=html.unescape(b); b=re.sub(r'\s+',' ',b)
        out.append((p.get('username'), b))
    return title, out
for tid in sys.argv[1:]:
    r = topic(tid)
    print('\n' + '='*70)
    if not r: print(tid, 'FAILED'); continue
    t, posts = r
    print('TOPIC', tid, '::', t)
    for u,b in posts:
        if len(b) < 120: continue
        print(f'  @{u}: {b[:600]}')
