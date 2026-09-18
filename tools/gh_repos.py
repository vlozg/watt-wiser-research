
import json, urllib.request, re, base64, time

def gh(url):
    req = urllib.request.Request(url, headers={"User-Agent":"research/1.0","Accept":"application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=45) as r: return json.load(r)

def readme(repo):
    for br in ("main","master"):
        try:
            d = gh(f"https://api.github.com/repos/{repo}/readme")
        except Exception as e:
            return f"ERR {repr(e)[:50]}"
        try:
            return base64.b64decode(d["content"]).decode("utf-8","ignore")
        except Exception as e:
            return f"ERR {repr(e)[:50]}"
    return "none"

DS = ["UK-?DALE","UKDALE","REFIT","REDD","AMPds","PLAID","WHITED","BLUED","iAWE","HUE","DRED",
      "Pecan","SynD","EMBED","COOLL","LILACD","Tracebase","MORED","Dataport","Smart\\*","SMART"]

REPOS = ["ch-shin/awesome-nilm","klemenjak/nilm-papers-with-code","MingjunZhong/transferNILM",
         "MingjunZhong/seq2point-nilm","JackKelly/neuralnilm","OdysseasKr/neural-disaggregator",
         "nilmtk/nilmtk"]
for repo in REPOS:
    try:
        meta = gh("https://api.github.com/repos/" + repo)
    except Exception as e:
        print(f"\n### {repo}: NOT FOUND ({repr(e)[:50]})"); continue
    stars = meta.get("stargazers_count"); desc = (meta.get("description") or "")[:90]
    txt = readme(repo)
    print(f"\n{'='*95}\n### {repo}  [{stars} stars]  {desc}")
    if txt.startswith("ERR"): print("   ", txt); continue
    # find lines mentioning datasets
    hits = []
    for ln in txt.splitlines():
        if any(re.search(d, ln, re.I) for d in DS): hits.append(ln.strip())
    print(f"    README {len(txt)} chars; {len(hits)} dataset-bearing lines")
    for h in hits[:28]: print("     |", h[:150])
    time.sleep(0.4)
