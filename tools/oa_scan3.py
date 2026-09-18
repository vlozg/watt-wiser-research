
import json, urllib.request, urllib.parse, time

D = json.load(open("projects/watt-wiser/research-logs/training-approaches-raw.json"))
for name in ["SEMI / SELF / UNSUPERVISED","SYNTHETIC / SIMULATION / GAN","PERSONALIZATION / CROSS-HOUSE","PRETRAIN / FOUNDATION / TRANSFORMER","EDGE / EMBEDDED / ON-DEVICE"]:
    hits = D.get(name, [])
    print("="*95); print(f"{name}   ({len(hits)} papers)")
    for w in hits[:9]:
        print(f"  [{w['y']}] c={w['c']}  {w['doi']}")
        print(f"     {w['t']}")
        if w['abs']: print(f"     ABS: {w['abs'][:300]}")

KEY = ["10.1016/j.apenergy.2023.121078","10.1109/tsg.2019.2938068","10.1109/tii.2021.3065934",
 "10.1109/tsg.2021.3115910","10.1109/tgcn.2021.3087702","10.1109/tim.2023.3246504",
 "10.1016/j.ijepes.2018.07.026","10.1109/tgcn.2022.3167392","10.3390/en16020991",
 "10.1109/tpwrs.2018.2800535","10.1109/access.2020.3003778","10.1109/cccs.2019.8888140",
 "10.3390/s22155872","10.3390/s22082926","10.1109/access.2022.3145982"]

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent":"research/1.0 (mailto:research@example.com)"})
    with urllib.request.urlopen(req, timeout=45) as r: return json.load(r)
def abstract(w):
    idx = w.get("abstract_inverted_index")
    if not idx: return ""
    pos = {}
    for word, ps in idx.items():
        for p in ps: pos[p] = word
    return " ".join(pos[k] for k in sorted(pos))

print("\n\n" + "#"*95)
print("FULL ABSTRACTS — core papers")
store = {}
for doi in KEY:
    try:
        w = get(f"https://api.openalex.org/works/doi:{doi}?mailto=research@example.com")
    except Exception as e:
        print("ERR", doi, repr(e)); continue
    ab = abstract(w)
    store[doi] = {"t": w.get("title"), "y": w.get("publication_year"), "c": w.get("cited_by_count"),
                  "abs": ab, "oa": (w.get("open_access") or {}).get("oa_url"), "venue": ((w.get("primary_location") or {}).get("source") or {}).get("display_name")}
    print("\n" + "-"*90)
    print(f"[{w.get('publication_year')}] c={w.get('cited_by_count')} | {doi}")
    print(f"T: {w.get('title')}")
    print(f"V: {store[doi]['venue']}  OA: {store[doi]['oa']}")
    print(f"A: {ab}")
    time.sleep(0.25)

json.dump(store, open("projects/watt-wiser/research-logs/training-approaches-key.json","w"), indent=1)
