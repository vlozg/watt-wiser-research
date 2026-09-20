"""Export the dataset EDA notebooks to PDF alongside their ipynb exports.

Runs `marimo export pdf` per notebook: the notebook is executed headless
(same engine as `make export-eda`), then rendered through nbconvert's
WebPDFExporter. Requires the playwright chromium browser once:
`playwright install chromium` (this script points PLAYWRIGHT_BROWSERS_PATH
at .scratch/pw-browsers unless one is already exported - a gitignored,
persistent cache location (on this box /tmp does not survive calls).

Usage:
    make eda-pdfs                          # all six shipped PDFs
    make eda-pdfs NOTEBOOK=06_ampds2_eda   # a single notebook
    python3 src/pipelines/02_fnd_eda_notebooks/export_pdfs.py [NAME ...]

PDF_SET lists the notebooks that ship a PDF in docs/reports/dataset_eda/;
the 02b localtime companion is ipynb-only, like the synthetic fixture 07.
"""

import os
import subprocess
import sys
import time

PDF_SET = [
    "01_ukdale_eda",
    "02_refit_eda",
    "03_redd_eda",
    "04_eco_eda",
    "05_greend_eda",
    "06_ampds2_eda",
]

NB_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(NB_DIR)))
OUT_DIR = os.path.join(ROOT, "docs", "reports", "dataset_eda")


def main() -> int:
    names = sys.argv[1:] or list(PDF_SET)
    unknown = [n for n in names if n not in PDF_SET]
    if unknown:
        print("unknown notebook(s): %s - choose from %s" % (", ".join(unknown), ", ".join(PDF_SET)))
        return 2
    env = dict(os.environ)
    env.setdefault("MPLCONFIGDIR", "/tmp/mplcfg")  # headless matplotlib
    env.setdefault("PLAYWRIGHT_BROWSERS_PATH", os.path.join(ROOT, ".scratch", "pw-browsers"))  # chromium home
    env.setdefault("XDG_CONFIG_HOME", "/tmp/xdg-config")  # read-only $HOME configs
    failures = []
    for name in names:
        src = os.path.join(NB_DIR, name + ".py")
        dst = os.path.join(OUT_DIR, name + ".pdf")
        print("=== pdf %s (%s)" % (name, time.strftime("%H:%M:%S")), flush=True)
        t0 = time.time()
        r = subprocess.run([sys.executable, "-m", "marimo", "export", "pdf", src, "-o", dst], cwd=ROOT, env=env)
        if r.returncode != 0:
            print("FAIL %s (exit %d)" % (name, r.returncode))
            failures.append(name)
        else:
            print("=== done %s in %.0fs -> %s" % (name, time.time() - t0, os.path.relpath(dst, ROOT)))
    if failures:
        print("failed: %s" % ", ".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
