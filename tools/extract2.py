
import zipfile, re, os, sys

def paras(path):
    z = zipfile.ZipFile(path)
    xml = z.read("word/document.xml").decode("utf-8", "ignore")
    # mark table cell boundaries so tables stay readable
    xml = xml.replace("</w:tc>", " | </w:tc>").replace("</w:tr>", "\n</w:tr>")
    body = re.split(r"</w:p>", xml)
    out = []
    for p in body:
        txt = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p))
        txt = txt.replace("&#8217;","'").replace("&amp;","&").replace("&lt;","<").replace("&gt;",">").replace("&quot;",'"')
        txt = re.sub(r"[ \t]+", " ", txt).strip()
        if txt and txt != "|": out.append(re.sub(r"(\s*\|\s*)+$","",txt).strip())
    return out

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root
outdir = os.path.join(ROOT, "docs", "client", "brief-extract")
os.makedirs(outdir, exist_ok=True)
for src, dst in [
  (os.path.join(ROOT, "docs", "external", "AI_Engineer_Project_Brief.docx"), "brief.txt"),
  (os.path.join(ROOT, "docs", "external", "calibration.docx (filename not recorded)"), "calibration.txt"),
]:
    ps = paras(src)
    with open(os.path.join(outdir, dst), "w") as f:
        for i, t in enumerate(ps): f.write(f"[{i:03d}] {t}\n")
    print(dst, len(ps), "paragraphs,", sum(len(t) for t in ps), "chars")
