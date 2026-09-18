
import json, urllib.request, re, io, sys, time
from pypdf import PdfReader

def get(url, timeout=45):
    req = urllib.request.Request(url, headers={"User-Agent":"research/1.0 (mailto:research@example.com)"})
    with urllib.request.urlopen(req, timeout=timeout) as r: return json.load(r)
def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36","Accept":"application/pdf,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r: return r.read()

import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root
dois = list(json.load(open(os.path.join(ROOT, "research-logs", "training-approaches-key.json"))).keys())

DS = ["UK-?DALE","UKDALE","REFIT","REDD","AMPds","PLAID","WHITED","BLUED","iAWE","HUE","DRED",
      "Pecan","SynD","COOLL","LILACD","Tracebase","MORED"]
RATE = [r"\d+(?:\.\d+)?\s*k?Hz", r"\d+\s*s(?:ec)?\b", r"\d+\s*min", r"\d+\s*second", r"1\s*Hz", r"low[- ]rate"]

print("### OA full-text availability sweep ###")
found = {}
for doi in dois:
    try: w = get("https://api.openalex.org/works/doi:" + doi + "?mailto=research@example.com")
    except Exception as e: continue
    for loc in w.get("locations", []):
        u = loc.get("pdf_url")
        if u and loc.get("is_oa"):
            found.setdefault(doi, []).append(u)
    time.sleep(0.2)

print(f"    {len(found)} of {len(dois)} papers have an OA pdf_url\n")
print("### Extracted evidence ###")
for doi, urls in found.items():
    got = False
    for u in urls[:3]:
        try:
            rd = PdfReader(io.BytesIO(fetch(u)))
            t = re.sub(r"\s+"," "," ".join((p.extract_text() or "") for p in rd.pages))
        except Exception: continue
        if len(t) < 3000: continue
        ds = sorted({m for d in DS for m in re.findall(d, t, re.I)})
        rt = sorted({m.strip() for p in RATE for m in re.findall(p, t, re.I)})
        print(f"\n  {doi}\n     via {u[:88]}\n     DATA {ds}\n     RATE {rt[:14]}")
        got = True; break
    if not got: print(f"\n  {doi}\n     (no usable OA pdf)")
