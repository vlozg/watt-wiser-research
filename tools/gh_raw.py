
import urllib.request, re, time

def raw(url, timeout=45):
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r: return r.read().decode("utf-8","ignore")

DS = ["UK-?DALE","UKDALE","REFIT","REDD","AMPds","PLAID","WHITED","BLUED","iAWE","HUE","DRED",
      "Pecan","SynD","COOLL","LILACD","Tracebase","MORED","Dataport"]

REPOS = ["ch-shin/awesome-nilm","klemenjak/nilm-papers-with-code","MingjunZhong/transferNILM",
         "MingjunZhong/seq2point-nilm","JackKelly/neuralnilm","OdysseasKr/neural-disaggregator"]

for repo in REPOS:
    txt = None
    for fn in ["README.md","readme.md","Readme.md","README.rst","README"]:
        for br in ["master","main"]:
            try:
                txt = raw(f"https://raw.githubusercontent.com/{repo}/{br}/{fn}")
                break
            except Exception: continue
        if txt: break
    print(f"\n{'='*95}\n### {repo}")
    if not txt: print("    no README reachable"); continue
    hits = [ln.strip() for ln in txt.splitlines() if any(re.search(d, ln, re.I) for d in DS)]
    print(f"    README {len(txt)} chars; {len(hits)} dataset-bearing lines")
    for h in hits[:30]: print("     |", re.sub(r"\|","|",h)[:160])
    time.sleep(0.3)
