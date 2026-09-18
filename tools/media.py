
import zipfile, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root
DOCS = [("BRIEF", os.path.join(ROOT, "docs", "external", "AI_Engineer_Project_Brief.docx")),
        ("CAL",   os.path.join(ROOT, "docs", "external", "calibration.docx (filename not recorded)"))]
outdir = os.path.join(ROOT, "docs", "client", "brief-extract", "media")
os.makedirs(outdir, exist_ok=True)

for tag, p in DOCS:
    z = zipfile.ZipFile(p)
    names = z.namelist()
    media = [n for n in names if n.startswith("word/media/")]
    try:
        rels = z.read("word/_rels/document.xml.rels").decode("utf-8", "ignore")
        order = re.findall(r'media/([^"]+)', rels)
    except Exception:
        order = []
    print(f"=== {tag}: {len(media)} media, document-order = {order}")
    for n in media:
        d = z.read(n)
        base = f"{tag}_{os.path.basename(n)}"
        open(os.path.join(outdir, base), "wb").write(d)
        print(f"    {base:22s} {len(d):>9,} bytes")
