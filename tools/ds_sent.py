
import urllib.request, re, io, sys
from pypdf import PdfReader

def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36","Accept":"application/pdf,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r: return r.read()
def txt(u):
    return re.sub(r"\s+", " ", " ".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(fetch(u))).pages))

DATASET_RE = re.compile(r"(UK[- ]?DALE|UKDALE|REFIT|REDD|AMPds|PLAID|WHITED|BLUED|COOLL|iAWE|IAME|iAWE|Pecan|SynD|Tracebase|DRED|HUE)", re.I)

TARGETS = [
 ("Todic 2023 (active learning)", "https://strathprints.strath.ac.uk/85002/7/Todic_etal_AE_2023_An_active_learning_framework_for_the_low_frequency_Non_Intrusive_Load_Monitoring_problem.pdf"),
 ("Neural NILM (2015)", "https://arxiv.org/pdf/1507.06594"),
]
for label, u in TARGETS:
    t = txt(u)
    parts = re.split(r"(?<=[.!?])\s+", t)
    print("\n" + "#"*95); print("### " + label)
    seen = set(); n = 0
    for s in parts:
        if not (45 < len(s) < 620): continue
        if not DATASET_RE.search(s): continue
        k = s[:55]
        if k in seen: continue
        seen.add(k); n += 1
        print("   *", s.strip()[:520])
        if n >= 30: break
