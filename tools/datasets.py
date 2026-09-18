
import json, urllib.request, re, time

def get(url, timeout=45):
    req = urllib.request.Request(url, headers={"User-Agent":"research/1.0 (mailto:research@example.com)"})
    with urllib.request.urlopen(req, timeout=timeout) as r: return json.load(r)

def abstract(w):
    idx = w.get("abstract_inverted_index")
    if not idx: return ""
    pos = {}
    for word, ps in idx.items():
        for p in ps: pos[p] = word
    return " ".join(pos[k] for k in sorted(pos))

import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root
KEY = os.path.join(ROOT, "research-logs", "training-approaches-key.json")
dois = list(json.load(open(KEY)).keys())

DS = ["UK-DALE","UKDALE","UK DALE","REFIT","REDD","AMPds","AMPDs","PLAID","WHITED","BLUED","iAWE",
      "IAWE","HUE","DRED","Pecan Street","PecanStreet","SynD","Smart*","EMBED","COOLL","LILACD",
      "Tracebase","TraceBase","MORED","ECO","Dataport","R AE","RAE"]
RATE = [r"\d+\s*Hz", r"\d+\s*kHz", r"\d+\s*minute", r"\d+\s*min", r"\d+\s*second", r"\d+\s*s\b",
        r"low[- ]frequency", r"low[- ]rate", r"high[- ]frequency", r"15[- ]minute", r"1\s*Hz",
        r"sampling rate", r"sample rate", r"sub[- ]?meter", r"submeter"]

rows = []
for doi in dois:
    try:
        w = get("https://api.openalex.org/works/doi:" + doi + "?mailto=research@example.com")
    except Exception as e:
        print("ERR", doi, repr(e)[:50]); continue
    a = abstract(w)
    title = (w.get("title") or "")[:70]
    ds = sorted({m for d in DS for m in re.findall(re.escape(d), a, re.I)})
    rt = sorted({m.strip() for p in RATE for m in re.findall(p, a, re.I)})
    rows.append((doi, title, ds, rt, len(a)))
    time.sleep(0.25)

print("=" * 100)
for doi, title, ds, rt, n in rows:
    print(f"\n{title}")
    print(f"   doi   {doi}   (abstract {n} chars)")
    print(f"   DATA  {ds if ds else '-- none named in abstract --'}")
    print(f"   RATE  {rt if rt else '-- none --'}")
