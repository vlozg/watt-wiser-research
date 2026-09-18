
import json, urllib.request, urllib.parse, re, io, sys, time
from pypdf import PdfReader

DOIS = ["10.1016/j.apenergy.2023.121078","10.1109/tsg.2019.2938068","10.1109/icassp.2019.8682486",
        "10.1109/tii.2021.3065934","10.1109/tgcn.2021.3087702","10.1109/tim.2023.3246504",
        "10.1016/j.ijepes.2018.07.026","10.1109/tgcn.2022.3167392","10.1109/tsg.2021.3115910",
        "10.1109/access.2022.3145982"]

def get(url, timeout=45):
    req = urllib.request.Request(url, headers={"User-Agent":"research/1.0 (mailto:research@example.com)"})
    with urllib.request.urlopen(req, timeout=timeout) as r: return json.load(r)
def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"})
    with urllib.request.urlopen(req, timeout=timeout) as r: return r.read()

cands = {}
for doi in DOIS:
    try:
        w = get("https://api.openalex.org/works/doi:" + doi + "?mailto=research@example.com")
    except Exception as e:
        print("ERR", doi, repr(e)[:60]); continue
    print("\n" + "="*88); print(doi, "|", (w.get("title") or "")[:75])
    for loc in w.get("locations", []):
        src = (loc.get("source") or {}).get("display_name")
        pdf = loc.get("pdf_url"); land = loc.get("landing_page_url")
        is_oa = loc.get("is_oa")
        if pdf or is_oa:
            print(f"   oa={is_oa} src={src}")
            print(f"      pdf={pdf}")
            print(f"      land={land}")
            if pdf: cands.setdefault(doi, []).append(pdf)

print("\n\n### EXTRACT ###")
KWS = ["transfer","fine-tun","domain","unseen","new house","house-hold","household","labeled","labelled",
       "active learning","few-shot","generaliz","personaliz","improv","MAE","F1","%","labeling cost"]
for doi, urls in cands.items():
    for u in urls[:2]:
        try:
            b = fetch(u)
            rd = PdfReader(io.BytesIO(b))
            t = "\n".join((p.extract_text() or "") for p in rd.pages)
        except Exception as e:
            print(f"  {doi} {u[:60]} FAIL {repr(e)[:60]}"); continue
        if len(t) < 2000: continue
        t2 = re.sub(r"\s+", " ", t)
        parts = re.split(r"(?<=[.!?])\s+", t2)
        got = []
        for s in parts:
            if not (40 < len(s) < 600): continue
            if not re.search(r"\d", s): continue
            if any(k.lower() in s.lower() for k in KWS): got.append(s.strip())
            if len(got) >= 9: break
        print("\n--- " + doi + "  via " + u[:70])
        for s in got: print("   *", s[:420])
        break
    time.sleep(0.4)
