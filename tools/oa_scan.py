
import json, urllib.request, urllib.parse, time

QUERIES = [
  "non-intrusive load monitoring transfer learning",
  "NILM domain adaptation cross-household generalization",
  "energy disaggregation online learning incremental learning",
  "non-intrusive load monitoring active learning user feedback",
  "energy disaggregation few-shot meta-learning",
  "non-intrusive load monitoring deep learning generalization unseen house",
  "non-intrusive load monitoring semi-supervised learning",
  "energy disaggregation personalization individual household",
  "appliance load monitoring synthetic data training augmentation",
  "energy disaggregation pretrained model foundation transformer",
]

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "research/1.0 (mailto:research@example.com)"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.load(r)

def abstract(w):
    idx = w.get("abstract_inverted_index")
    if not idx: return ""
    pos = {}
    for word, ps in idx.items():
        for p in ps: pos[p] = word
    return " ".join(pos[k] for k in sorted(pos))

allout = {}
for q in QUERIES:
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode({
        "search": q, "per_page": "14", "sort": "cited_by_count:desc", "mailto": "research@example.com"})
    try:
        d = get(url)
    except Exception as e:
        print("ERR", q, repr(e)); continue
    rows = []
    for w in d.get("results", []):
        rows.append({
            "title": w.get("title"), "year": w.get("publication_year"),
            "cites": w.get("cited_by_count"), "doi": w.get("doi"),
            "venue": (w.get("primary_location") or {}).get("source", {}) and ((w.get("primary_location") or {}).get("source") or {}).get("display_name"),
            "abs": abstract(w),
        })
    allout[q] = rows
    time.sleep(0.25)

with open("projects/watt-wiser/research-logs/training-approaches-raw.json", "w") as f:
    json.dump(allout, f, indent=1)

seen = {}
for q, rows in allout.items():
    print("=" * 95)
    print("QUERY:", q)
    for r in rows:
        key = (r["title"] or "")[:60].lower()
        if key in seen:
            print(f"   (dup) {r['year']} c={r['cites']} {r['title'][:85]}")
            continue
        seen[key] = True
        print(f"   {r['year']} c={str(r['cites']).rjust(4)} {r['doi']}")
        print(f"        {r['title']}")
