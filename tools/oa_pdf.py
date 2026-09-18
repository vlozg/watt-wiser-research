
import urllib.request, urllib.parse, re, sys, time
from pypdf import PdfReader
import io

def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"})
    with urllib.request.urlopen(req, timeout=timeout) as r: return r.read()

def pdftext(url):
    b = fetch(url)
    rd = PdfReader(io.BytesIO(b))
    return "\n".join((p.extract_text() or "") for p in rd.pages)

def hits(text, kws, limit=10, maxlen=430):
    text = re.sub(r"\s+", " ", text)
    parts = re.split(r"(?<=[.!?])\s+", text)
    out = []
    for s in parts:
        if not (40 < len(s) < 600): continue
        if not re.search(r"\d", s): continue
        if any(k.lower() in s.lower() for k in kws): out.append(s.strip())
        if len(out) >= limit: break
    return out

KWS = ["transfer","fine-tun","domain adaptation","cross-domain","unseen","new house","household",
       "labeled","labelled","active learning","few-shot","generaliz","personaliz","percentage","%"]

for label, u in [("Neural NILM (2015) arXiv:1507.06594","https://arxiv.org/pdf/1507.06594"),
                 ("Feeder online learning arXiv:1701.04389","https://arxiv.org/pdf/1701.04389")]:
    try:
        t = pdftext(u)
    except Exception as e:
        print(f"\n=== {label}: FAIL {repr(e)[:90]}"); continue
    print("\n" + "="*90); print(f"=== {label}  ({len(t)} chars)")
    for s in hits(t, KWS, 10): print("   *", s[:430])

print("\n\n### arXiv preprint search for key titles ###")
TITLES = ["Transfer Learning for Non-Intrusive Load Monitoring",
          "Transferability of Neural Network Approaches for Low-rate Energy Disaggregation",
          "An active learning framework for the low-frequency Non-Intrusive Load Monitoring problem",
          "Unsupervised Domain Adaptation for Nonintrusive Load Monitoring",
          "Pre-Trained Models for Non-Intrusive Appliance Load Monitoring"]
for ti in TITLES:
    q = urllib.parse.quote(f'ti:"{ti}"')
    url = f"http://export.arxiv.org/api/query?search_query={q}&max_results=3"
    try:
        x = fetch(url).decode("utf-8","ignore")
    except Exception as e:
        print(f"  {ti[:60]}: ERR {repr(e)[:60]}"); continue
    ids = re.findall(r"<id>(http://arxiv.org/abs/[^<]+)</id>", x)
    ttl = re.findall(r"<title>([^<]+)</title>", x)
    print(f"  {ti[:65]}")
    if len(ids) <= 1: print("      (none)")
    for i, a in zip(ids[1:], ttl[1:]): print(f"      {a.strip()[:80]} -> {i}")
    time.sleep(1.2)
