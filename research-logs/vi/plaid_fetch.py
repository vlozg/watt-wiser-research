
import json, urllib.request, struct, zlib, os, collections, time

BASE = "https://ndownloader.figshare.com/files/18183113"
HDRS = {"User-Agent":"Mozilla/5.0","Accept-Encoding":"identity"}
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root
CD   = json.load(open(os.path.join(ROOT, "research-logs", "vi", "plaid_cd.json")))
META = json.load(open(os.path.join(ROOT, "research-logs", "plaid", "metadata_submetered.json")))
OUT  = os.path.join(ROOT, "research-logs", "vi", "plaid_samples")
os.makedirs(OUT, exist_ok=True)

def resolve():
    q = urllib.request.Request(BASE, headers=HDRS); q.add_header("Range","bytes=0-0")
    with urllib.request.urlopen(q, timeout=60) as r: return r.geturl()

def rng(url, a, b, tries=3):
    for k in range(tries):
        try:
            q = urllib.request.Request(url, headers=HDRS); q.add_header("Range", f"bytes={a}-{b}")
            with urllib.request.urlopen(q, timeout=180) as r: return r.read()
        except Exception as e:
            if k == tries-1: raise
            time.sleep(2)
            url = resolve()

byt = collections.defaultdict(list)
for m in CD:
    n = m["name"]
    if not n.endswith(".csv"): continue
    pid = n.split("/")[-1][:-4]
    md = META.get(pid)
    if not md: continue
    t = md["appliance"]["type"].strip()
    if t: byt[t].append((m["csize"], pid, m["lho"], m["method"]))

WANT = ["Water kettle","Coffee maker","Heater","Fridge","Hairdryer","Vacuum",
        "Washing Machine","Microwave","Laptop","Compact Fluorescent Lamp",
        "Incandescent Light Bulb","Fan","Air Conditioner","Soldering Iron","Blender","Hair Iron"]

REAL = resolve()
saved, t0 = [], time.time()
for t in WANT:
    if t not in byt: continue
    csize, pid, lho, method = sorted(byt[t])[0]
    try:
        hdr = rng(REAL, lho, lho+1023)
        nlen, elen = struct.unpack("<HH", hdr[26:30])
        dstart = lho + 30 + nlen + elen
        blob = rng(REAL, dstart, dstart+csize-1)
        raw = zlib.decompress(blob, -15) if method == 8 else blob
        p = f"{OUT}/{t.replace(' ','_')}__{pid}.csv"
        open(p,"wb").write(raw)
        saved.append({"type":t,"id":pid,"bytes":len(raw),"path":p})
        print("  ok  %-30s id=%-5s %8d B" % (t,pid,len(raw)))
    except Exception as e:
        print("  FAIL %-30s %s" % (t, repr(e)[:70]))
        REAL = resolve()

json.dump(saved, open(f"{OUT}/index.json","w"), indent=1)
print("\nsaved %d in %.0fs -> %s" % (len(saved), time.time()-t0, OUT))
