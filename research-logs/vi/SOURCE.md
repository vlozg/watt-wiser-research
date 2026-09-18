# Source note

The PLAID paper formerly stored here (`vi_paper.pdf`, 1.1 MB) was removed from the repo
per policy: no third-party published PDFs in git history. Re-download if needed:

- **PLAID dataset (2018 version used):** Figshare, DOI 10.6084/m9.figshare.10084619 -
  https://doi.org/10.6084/m9.figshare.10084619
- **Open-access dataset paper** (acquisition rig + BLUED clamp critique): PMC7015894 -
  https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7015894/
- Claims/figures traced from these sources: `docs/research/vi-trajectory-hardware.md`

## Contents

- `plaid_samples/` - 16 PLAID 30 kHz V-I captures + metadata (gitignored; re-fetch via
  `plaid_fetch.py`)
- `plaid_cd.json` - zip central-directory dump of the upstream PLAID archive
- `plaid_fetch.py`, `plaid_zip.py` - fetch + inspect scripts
