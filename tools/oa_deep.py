
import urllib.request, re, io, sys, time
from pypdf import PdfReader

def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36","Accept":"application/pdf,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r: return r.read()

def txt(u):
    rd = PdfReader(io.BytesIO(fetch(u)))
    return "\n".join((p.extract_text() or "") for p in rd.pages)

TARGETS = [
 ("Todic 2023 — Active learning for low-freq NILM",
  "https://strathprints.strath.ac.uk/85002/7/Todic_etal_AE_2023_An_active_learning_framework_for_the_low_frequency_Non_Intrusive_Load_Monitoring_problem.pdf",
  ["5%","15%","query pool","acquisition","uncertainty","entropy","margin","random sampling","F1","MAE",
   "UK-DALE","REFIT","dataset","house","transfer","fine-tun","retrain","label","conclusion"]),
 ("Transfer Learning for NILM (TSG 2019)",
  "http://eprints.lincoln.ac.uk/id/eprint/36753/1/NILM_paper.pdf",
  ["transfer","seq2point","ATL","CTL","UK-DALE","REDD","REFIT","appliance transfer","cross-domain",
   "MAE","F1","improv","latent","fine-tun","conclusion"]),
]

for label, u, kws in TARGETS:
    try: t = txt(u)
    except Exception as e:
        print(f"\n=== {label}: FAIL {repr(e)[:100]}"); continue
    t2 = re.sub(r"\s+", " ", t)
    print("\n" + "#"*92)
    print(f"### {label}   ({len(t2)} chars extracted)")
    parts = re.split(r"(?<=[.!?])\s+", t2)
    seen = set(); n = 0
    for s in parts:
        if not (45 < len(s) < 520): continue
        if not re.search(r"\d", s): continue
        if not any(k.lower() in s.lower() for k in kws): continue
        key = s[:50]
        if key in seen: continue
        seen.add(key); n += 1
        print("   *", s[:440])
        if n >= 22: break
    time.sleep(0.5)
