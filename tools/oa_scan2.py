
import json, urllib.request, urllib.parse, time, re

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "research/1.0 (mailto:research@example.com)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def abstract(w):
    idx = w.get("abstract_inverted_index")
    if not idx: return ""
    pos = {}
    for word, ps in idx.items():
        for p in ps: pos[p] = word
    return " ".join(pos[k] for k in sorted(pos))

PHRASES = [
    '"non-intrusive load monitoring"',
    '"energy disaggregation"',
    '"load disaggregation"',
    '"appliance load monitoring"',
    '"energy disaggregation" household',
]

works = {}
for ph in PHRASES:
    for yr in ["2014-2026"]:
        url = "https://api.openalex.org/works?" + urllib.parse.urlencode({
            "filter": f"title_and_abstract.search:{ph},publication_year:{yr}",
            "per_page": "200", "sort": "cited_by_count:desc", "mailto": "research@example.com"})
        try:
            d = get(url)
        except Exception as e:
            print("ERR", ph, repr(e)); continue
        for w in d.get("results", []):
            works[w["id"]] = w
        print(f"  {ph} -> {len(d.get('results',[]))} (total corpus {len(works)})")
        time.sleep(0.3)

print("TOTAL unique works:", len(works))

BUCKETS = {
 "TRANSFER / DOMAIN ADAPTATION": ["transfer learning","domain adaptation","domain shift","fine-tun","finetun","cross-domain"],
 "ONLINE / INCREMENTAL / CONTINUAL": ["online learning","incremental learn","continual learn","continuous learn","streaming learn","lifelong"],
 "ACTIVE LEARNING / USER FEEDBACK / HITL": ["active learning","user feedback","human-in-the-loop","human in the loop","interactive","user annotation","query strategy","crowdsourc"],
 "FEW-SHOT / META-LEARNING": ["few-shot","few shot","meta-learn","meta learn","siamese","prototypical network","matching network"],
 "FEDERATED / PRIVACY-PRESERVING": ["federated","differential privacy","homomorphic","privacy-preserving","secure aggregation"],
 "SEMI / SELF / UNSUPERVISED": ["semi-supervised","semi supervised","self-supervised","self supervised","unsupervised","contrastive","autoencoder","clustering"],
 "SYNTHETIC / SIMULATION / GAN": ["synthetic data","simulat","augment","gan","generative adversarial","data synthesis","digital twin"],
 "PERSONALIZATION / CROSS-HOUSE": ["personaliz","household-specific","household specific","cross-household","cross household","unseen house","generaliz","generaliz","per-home","new household","domain generalization"],
 "PRETRAIN / FOUNDATION / TRANSFORMER": ["pretrain","pre-train","foundation model","transformer","large language model","llm","bert","attention-based","attention based"],
 "EDGE / EMBEDDED / ON-DEVICE": ["edge device","embedded","on-device","on device","microcontroller","raspberry","tiny","quantiz","real-time deploy"],
}

out = {}
for name, kws in BUCKETS.items():
    hits = []
    for w in works.values():
        text = ((w.get("title") or "") + " " + abstract(w)).lower()
        if any(k in text for k in kws):
            hits.append(w)
    hits.sort(key=lambda w: -(w.get("cited_by_count") or 0))
    out[name] = hits
    print("\n" + "="*95)
    print(f"{name}    ({len(hits)} papers)")
    for w in hits[:10]:
        ab = abstract(w)
        print(f"  [{w.get('publication_year')}] c={w.get('cited_by_count')}  {w.get('doi')}")
        print(f"     {w.get('title')}")
        if ab: print(f"     ABS: {ab[:330]}")

json.dump({k: [{"t": w.get("title"), "y": w.get("publication_year"), "c": w.get("cited_by_count"),
                "doi": w.get("doi"), "abs": abstract(w)[:1200]} for w in v] for k, v in out.items()},
          open("projects/watt-wiser/research-logs/training-approaches-raw.json", "w"), indent=1)
