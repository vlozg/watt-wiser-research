"""Regenerate raw_manifest.json from the current data/raw/ tree (file names + byte sizes).

Run after the user re-stages or re-uploads a dataset zip, so the verification in
download_<dataset>.py tracks the new baseline.
"""
import json
import os

from wattwiser import RAW, human

DATASETS = [
    ('ukdale', 'ukdale-full'),
    ('refit', 'REFIT'),
    ('eco', 'ECO'),
    ('greend', 'GREEND_0-2_300615'),
    ('redd', 'redd'),
    ('ampds2', 'AMPds2'),
]

out = {"_meta": {"generated_by": "src/pipelines/00_download_dataset/make_manifest.py"}}
for key, dirname in DATASETS:
    root = os.path.join(RAW, dirname)
    if not os.path.isdir(root):
        raise SystemExit("missing: %s" % root)
    sizes = {}
    for r, _dirs, files in os.walk(root):
        for f in files:
            full = os.path.join(r, f)
            sizes[os.path.relpath(full, root)] = os.path.getsize(full)
    out[key] = sizes
    out["_meta"]["%s_bytes" % key] = sum(sizes.values())
    out["_meta"]["%s_files" % key] = len(sizes)
    print("%-8s %6d files %10s" % (key, len(sizes), human(sum(sizes.values()))))
dst = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw_manifest.json")
with open(dst, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, sort_keys=True)
print("wrote %s" % dst)