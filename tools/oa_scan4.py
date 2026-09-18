
import json, urllib.request, time

MORE = ["10.1109/icassp.2019.8682486","10.1109/tsg.2015.2494592","10.1109/access.2016.2557460",
 "10.1145/3427771.3429390","10.1016/j.artint.2014.07.010","10.1109/tsg.2018.2826844",
 "10.1109/tsg.2022.3189598","10.1109/tsg.2019.2924862","10.1109/tsg.2020.2967220",
 "10.1109/tpwrs.2018.2800535","10.1145/2821650.2821672","10.1109/tce.2019.2891160"]

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

store = json.load(open("projects/watt-wiser/research-logs/training-approaches-key.json"))
print("### ALREADY-STORED KEY PAPERS ###")
for doi, v in store.items():
    print("\n" + "-"*88)
    print(f"[{v['y']}] c={v['c']} | {doi}")
    print(f"T: {v['t']}")
    print(f"A: {(v['abs'] or '(no abstract)')[:1150]}")

print("\n\n### ADDITIONAL ###")
for doi in MORE:
    try:
        w = get(f"https://api.openalex.org/works/doi:{doi}?mailto=research@example.com")
    except Exception as e:
        print("ERR", doi, repr(e)); continue
    ab = abstract(w)
    store[doi] = {"t": w.get("title"), "y": w.get("publication_year"), "c": w.get("cited_by_count"),
                  "abs": ab, "oa": (w.get("open_access") or {}).get("oa_url"),
                  "venue": ((w.get("primary_location") or {}).get("source") or {}).get("display_name")}
    print("\n" + "-"*88)
    print(f"[{w.get('publication_year')}] c={w.get('cited_by_count')} | {doi}")
    print(f"T: {w.get('title')}")
    print(f"A: {(ab or '(no abstract)')[:1150]}")
    time.sleep(0.25)

json.dump(store, open("projects/watt-wiser/research-logs/training-approaches-key.json","w"), indent=1)
print("\nSAVED", len(store), "papers")
