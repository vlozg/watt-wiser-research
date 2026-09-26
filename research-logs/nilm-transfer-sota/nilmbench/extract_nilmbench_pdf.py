from pypdf import PdfReader
r = PdfReader('nilmbench2026_buildsys.pdf')
txt = chr(10).join((p.extract_text() or '') for p in r.pages)
open('pdf.txt', 'w').write(txt)
print('PAGES', len(r.pages), 'CHARS', len(txt))
