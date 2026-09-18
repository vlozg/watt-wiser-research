
import json, urllib.request, urllib.parse, re, time

store = json.load(open("projects/watt-wiser/research-logs/training-approaches-key.json"))
print("### OA availability ###")
for doi, v in store.items():
    print(f"  {doi}  OA={(v.get('oa') or 'NONE')}")

def fetch(url, timeout=40):
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    try: return raw.decode("utf-8", "ignore")
    except Exception: return ""

def sentences(text, kws, limit=14):
    text = re.sub(r"\s+", " ", text)
    parts = re.split(r"(?<=[.!?])\s+", text)
    out = []
    for s in parts:
        if len(s) < 40 or len(s) > 500: continue
        if not re.search(r"\d", s): continue
        if any(k.lower() in s.lower() for k in kws):
            out.append(s.strip())
        if len(out) >= limit: break
    return out

KWS = ["transfer","fine-tun","finetun","domain","generaliz","generaliz","personaliz","unseen","new house","target domain","labelled","labeled","active learning","few-shot","few shot","improve","MAE","F1","accuracy"]

for doi, v in store.items():
    u = v.get("oa")
    if not u: continue
    try:
        t = fetch(u)
    except Exception as e:
        print(f"\n--- {doi} FETCH-FAIL {repr(e)[:80]}"); continue
    ss = sentences(t, KWS)
    if not ss: continue
    print("\n" + "="*90)
    print(f"{doi}  [{v['y']}]  {v['t'][:80]}")
    for s in ss[:12]:
        print("   *", s[:420])
    time.sleep(0.4)
