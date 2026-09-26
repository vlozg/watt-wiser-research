import re, sys, pathlib, html
d = pathlib.Path('.')
for f in sorted(d.glob('*.html')):
    t = f.read_text(encoding='utf-8', errors='replace')
    hrefs = re.findall(r'href=["\'](.*?)["\']', t)
    links = []
    for h in hrefs:
        hl = html.unescape(h)
        if any(k in hl for k in ('github.com', 'huggingface.co', 'zenodo.org', 'gitlab', 'codeocean', 'sourceforge')):
            if h not in links: links.append(h)
    print(f"{f.stem}: {len(t)//1024} KB | links: {links[:6] if links else 'NONE'}")