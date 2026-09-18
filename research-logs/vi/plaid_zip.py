
import urllib.request, struct, zlib, os, json, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root

URL = "https://ndownloader.figshare.com/files/18183113"  # submetered.zip (708 MB)
HDRS = {"User-Agent": "Mozilla/5.0", "Accept-Encoding": "identity"}

def head(url):
    req = urllib.request.Request(url, headers=HDRS, method="GET")
    req.add_header("Range", "bytes=0-0")
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, dict(r.headers)

def rng(url, a, b):
    req = urllib.request.Request(url, headers=HDRS)
    req.add_header("Range", f"bytes={a}-{b}")
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()

try:
    st, h = head(URL)
    print("status", st, "| content-range", h.get("Content-Range"), "| len", h.get("Content-Length"))
except Exception as e:
    print("HEAD failed:", repr(e)); sys.exit()

# find the real URL after redirect
req = urllib.request.Request(URL, headers=HDRS, method="GET")
req.add_header("Range", "bytes=0-0")
with urllib.request.urlopen(req, timeout=60) as r:
    REAL = r.geturl()
    total = int(r.headers.get("Content-Range","bytes 0-0/0").split("/")[-1] or 0)
print("resolved:", REAL[:110])
print("total bytes:", total)

TAIL = 262144
tail = rng(REAL, max(0, total-TAIL), total-1)
print("tail fetched:", len(tail))
i = tail.rfind(b"PK\x05\x06")
print("EOCD at tail offset:", i)
if i < 0:
    print("no EOCD in tail -> abort"); sys.exit()
cd_size, cd_off = struct.unpack("<II", tail[i+12:i+20])
print("central dir size", cd_size, "offset", cd_off)
if cd_off == 0xFFFFFFFF or cd_size == 0xFFFFFFFF:
    j = tail.rfind(b"PK\x06\x06")
    print("ZIP64 EOCD at", j)
    cd_size, cd_off = struct.unpack("<QQ", tail[j+40:j+56])
    print("zip64 cd size", cd_size, "offset", cd_off)

cd = rng(REAL, cd_off, cd_off+cd_size-1)
print("central dir fetched:", len(cd))

entries = []
p = 0
while True:
    p = cd.find(b"PK\x01\x02", p)
    if p < 0: break
    (method,) = struct.unpack("<H", cd[p+10:p+12])
    csize, usize = struct.unpack("<II", cd[p+20:p+28])
    nlen, elen, clen = struct.unpack("<HHH", cd[p+28:p+34])
    (lho,) = struct.unpack("<I", cd[p+42:p+46])
    name = cd[p+46:p+46+nlen].decode("utf-8", "replace")
    entries.append((name, method, csize, usize, lho))
    p += 46+nlen+elen+clen
print("entries parsed:", len(entries))

for e in entries[:6]:
    print("  ", e[0], "method", e[1], "csize", e[2], "usize", e[3])
json.dump([{"name":n,"method":m,"csize":c,"usize":u,"lho":o} for n,m,c,u,o in entries],
          open(os.path.join(ROOT, "research-logs", "vi", "plaid_cd.json"), "w"))
print("\nsaved index ->", len(entries), "members")
