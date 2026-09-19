"""Appliance-label canonicalization + gold slice writing.

canonical_label() maps raw appliance names (any spelling) onto the five
WattWiser target types; None = labeled but outside the client targets.
Each extract_<dataset>.py owns its dataset's extraction in extract_labels();
--labels writes data/gold/appliance_map_<dataset>.json, and the labels.py
driver merges all six into data/gold/appliance_map.json for the gold layer.
"""
import json
import re
from datetime import datetime, timezone

from wattwiser.paths import GOLD
from wattwiser.util import ensure

GOLD_DIR = GOLD  # familiar alias from the pre-package days
TARGETS = ['kettle', 'fridge', 'microwave', 'washing_machine', 'dishwasher']

# ordered: first match wins; patterns are matched against a normalized label
CANONICAL_RULES = [
    (r'kettle', 'kettle'),
    (r'microwave', 'microwave'),
    (r'(?:fridge|freezer)', 'fridge'),
    (r'(?:washing machine|washer dryer|clothes washer)', 'washing_machine'),
    (r'(?:dish ?washer)', 'dishwasher'),
]


def canonical_label(label):
    """Raw name -> canonical target type, or None when outside the targets.

    Dataset labels mix spellings: 'washing machine', 'washing_machine',
    'Washer Dryer' - normalize separators/spacing first.
    """
    low = re.sub(r'[_-]+', ' ', (label or '').strip().lower())
    low = re.sub(r'\s+', ' ', low)
    for pat, name in CANONICAL_RULES:
        if re.search(pat, low):
            return name
    return None


def h5_metadata(node):
    """NILMTK store building metadata dict from a pytables node's 'metadata' attr."""
    import ast
    md = node._v_attrs.metadata
    if not isinstance(md, dict):
        md = ast.literal_eval(str(md))
    return md


def write_slice(dataset, buildings):
    """Write one dataset's label map to data/gold/appliance_map_<dataset>.json."""
    ensure(GOLD_DIR)
    out = GOLD_DIR + '/appliance_map_%s.json' % dataset
    with open(out, 'w', encoding='utf-8') as fh:
        json.dump({
            '_meta': {'generated_by': 'extract_%s.py --labels' % dataset,
                      'generated_utc': datetime.now(timezone.utc).isoformat(timespec='seconds')},
            dataset: buildings,
        }, fh, indent=1)
    return out
