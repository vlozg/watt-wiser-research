import sys, zipfile, os, shutil
# Usage: python3 dump_media.py <path-to-calibration-docx>
# The calibration docx stays untracked under docs/external/; its filename is
# intentionally not recorded in this tracked script.
p = sys.argv[1]
out = "projects/watt-wiser/research-logs/docx_media"
os.makedirs(out, exist_ok=True)
z = zipfile.ZipFile(p)
for n in z.namelist():
    if n.startswith('word/media/'):
        dst = os.path.join(out, os.path.basename(n))
        with z.open(n) as f, open(dst, 'wb') as o:
            shutil.copyfileobj(f, o)
        print(dst, os.path.getsize(dst))
