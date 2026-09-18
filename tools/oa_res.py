
import urllib.request, re, io, sys, json, time
from pypdf import PdfReader

def get(url, timeout=45):
    req = urllib.request.Request(url, headers={"User-Agent":"research/1.0 (mailto:research@example.com)"})
    with urllib.request.urlopen(req, timeout=timeout) as r: return json.load(r)
def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36","Accept":"application/pdf,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r: return r.read()
def abstract(w):
    idx = w.get("abstract_inverted_index")
    if not idx: return ""
    pos = {}
    for word, ps in idx.items():
        for p in ps: pos[p] = word
    return " ".join(pos[k] for k in sorted(pos))

print("### FULL ABSTRACT — Transfer Learning for NILM (TSG 2019) ###")
w = get("https://api.openalex.org/works/doi:10.1109/tsg.2019.2938068?mailto=research@example.com")
print(abstract(w))

u = "https://strathprints.strath.ac.uk/85002/7/Todic_etal_AE_2023_An_active_learning_framework_for_the_low_frequency_Non_Intrusive_Load_Monitoring_problem.pdf"
rd = PdfReader(io.BytesIO(fetch(u)))
t = re.sub(r"\s+", " ", "\n".join((p.extract_text() or "") for p in rd.pages))

print("\n\n### Todic 2023 — results-bearing sentences ###")
parts = re.split(r"(?<=[.!?])\s+", t)
n = 0
for s in parts:
    if not (50 < len(s) < 520): continue
    low = s.lower()
    if not re.search(r"\d", s): continue
    if ("f1" in low or "mae" in low or "accuracy" in low or "improv" in low or "% of" in low
        or "labelled" in low or "labeled" in low or "query" in low or "sampling strategy" in low
        or "random" in low or "acquisition function" in low):
        print("   *", s[:430]); n += 1
    if n >= 26: break
