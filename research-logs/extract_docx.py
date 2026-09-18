import sys, zipfile, re, html, os
p = sys.argv[1]
z = zipfile.ZipFile(p)
names = z.namelist()
print('### MEDIA FILES:', [n for n in names if n.startswith('word/media')])
x = z.read('word/document.xml').decode('utf-8', 'ignore')
# paragraphs
x = x.replace('</w:p>', '\n')
x = re.sub(r'<w:tab[^>]*/>', '\t', x)
x = re.sub(r'<w:br[^>]*/>', '\n', x)
t = re.sub(r'<[^>]+>', '', x)
t = html.unescape(t)
lines = [re.sub(r'[ \t]+', ' ', l).strip() for l in t.split('\n')]
out = [l for l in lines]
print('\n'.join(out))
