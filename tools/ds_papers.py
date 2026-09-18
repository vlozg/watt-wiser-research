
import json, urllib.request, urllib.parse, re, time

def get(url, timeout=45):
    req = urllib.request.Request(url, headers={"User-Agent":"research/1.0 (mailto:research@example.com)"})
    with urllib.request.urlopen(req, timeout=timeout) as r: return json.load(r)
def abstract(w):
    idx = w.get("abstract_inverted_index")
    if not idx: return "(no abstract)"
    pos = {}
    for word, ps in idx.items():
        for p in ps: pos[p] = word
    return " ".join(pos[k] for k in sorted(pos))

TITLES = ["REDD: A public data set for energy disaggregation research",
          "AMPds: A public dataset for single-family electricity use",
          "BLUED: A Fully Labeled Public Dataset for Event-Based Non-Intrusive Load Monitoring Research",
          "PLAID: a public dataset of high-resolution electrical appliance measurements",
          "WHITED-A Worldwide Household and Industry Transient Energy Data Set",
          "COOLL: Controlled On/Off Loads Library",
          "The UK-DALE dataset, domestic appliance-level electricity demand and whole-house demand from five UK homes",
          "REFIT: Electrical Load Measurements Cleansed",
          "iAWE: Indian data for advanced analytics"]
for ti in TITLES:
    q = urllib.parse.quote(ti)
    try:
        j = get(f"https://api.openalex.org/works?search={q}&per-page=1&mailto=research@example.com")
    except Exception as e:
        print(f"\n{ti[:62]}: ERR {repr(e)[:40]}"); continue
    if not j.get("results"): print(f"\n{ti[:62]}: no result"); continue
    w = j["results"][0]
    print("\n" + "="*92)
    print((w.get("title") or "")[:88], "|", w.get("publication_year"))
    print("  " + abstract(w)[:900])
    time.sleep(0.3)
