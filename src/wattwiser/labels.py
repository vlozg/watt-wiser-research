"""Appliance-label canonicalization + gold slice writing.

canonical_label() maps raw appliance names (any spelling) onto the five
WattWiser target types; None = labeled device outside those targets. The
gold layer keeps every labeled device (canonical or not) so analyses filter
on the canonical field instead of dropping anything at build time.
Each extract_<dataset>.py owns its dataset's extraction in extract_labels();
--labels writes data/gold/appliance_map_<dataset>.json, and the labels.py
driver merges all six into data/gold/appliance_map.json for the gold layer.
"""
from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime, timezone
from typing import Any

from wattwiser.paths import GOLD
from wattwiser.util import ensure

GOLD_DIR = GOLD  # familiar alias from the pre-package days
TARGETS: list[str] = ['kettle', 'fridge', 'microwave', 'washing_machine', 'dishwasher']

# ordered: first match wins; patterns are matched against a normalized label
CANONICAL_RULES: list[tuple[str, str]] = [
    (r'kettle', 'kettle'),
    (r'microwave', 'microwave'),
    (r'(?:fridge|freezer)', 'fridge'),
    (r'(?:washing machine|washer dryer|clothes washer)', 'washing_machine'),
    (r'(?:dish ?washer)', 'dishwasher'),
]


def canonical_label(label: str | None) -> str | None:
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


# --------------------------------------------------------------------------
# Label-map schema: the dataclass shapes behind data/gold/appliance_map*.json.
# Each extract_<dataset>.py builds these in extract_labels(); record() renders
# them to plain dicts for json.dump, so the on-disk JSON stays exactly as
# before the dataclass conversion.
# --------------------------------------------------------------------------

def _json_record(obj: Any) -> Any:
    """Dataclass -> plain dict/list for JSON, converting nested values too.

    A field declared with field(metadata={'omit_none': True}) is skipped from
    the JSON when its value is None (REFIT notes only exist when the
    spreadsheet has them); every other field is always emitted, even when None
    (canonical=None, greend room=None, refit brand=None), matching the
    pre-dataclass JSON.
    """
    if is_dataclass(obj) and not isinstance(obj, type):
        out: dict[str, Any] = {}
        for f in fields(obj):
            v = getattr(obj, f.name)
            if f.metadata.get('omit_none') and v is None:
                continue
            out[f.name] = _json_record(v)
        return out
    if isinstance(obj, dict):
        return {k: _json_record(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_record(v) for v in obj]
    return obj


@dataclass
class DeviceLabel:
    """One labeled device (channel, plug, meter or appliance) in a building."""
    label: str              # verbatim dataset label, whitespace-normalized (casing kept)
    canonical: str | None   # canonical target name when the device is one of the 5 client
                            # targets (kettle/fridge/microwave/washing_machine/dishwasher);
                            # None = labeled device outside those targets (kept, not dropped)


@dataclass
class BuildingLabels:
    """One building's slice of the merged appliance label map."""
    source: str             # where the labels were read from, project-relative
                            # (+#sheet name for the REFIT xlsx workbook)

    def record(self) -> dict[str, Any]:
        """JSON-ready dict for appliance_map*.json (see _json_record)."""
        return _json_record(self)


@dataclass
class UkdaleBuilding(BuildingLabels):
    channels: dict[str, DeviceLabel]    # labels.dat channel id -> label; '1' = mains aggregate


@dataclass
class ReddMeterLabel(DeviceLabel):
    count: int              # number of appliance records in the NILMTK metadata naming this meter


@dataclass
class ReddBuilding(BuildingLabels):
    site_meters: list[int]                  # meter ids of the whole-home mains
    meters: dict[str, ReddMeterLabel]       # NILMTK meter id -> label


@dataclass
class Ampds2MeterLabel(DeviceLabel):
    type: str | None        # NILMTK appliance 'type' (mostly 'unknown'/'light'/'sockets');
                            # the human name lives in 'description', abbrev in 'label'
    description: str | None # human-readable appliance name from the NILMTK metadata
    room: str | None        # room the appliance sits in, when the metadata states it


@dataclass
class Ampds2Building(BuildingLabels):
    site_meters: list[int]                          # meter ids of the whole-home mains
    meters: dict[str, list[Ampds2MeterLabel]]       # meter id -> appliances sharing that meter


@dataclass
class RefitApplianceLabel(DeviceLabel):
    brand: str | None       # brand from the House sheet; None when the sheet says 'Unknown'
    model: str | None       # model from the House sheet; None when the sheet says 'Unknown'
    notes: str | None = field(default=None, metadata={'omit_none': True})
                            # parenthesized spreadsheet notes; omitted from the JSON when absent


@dataclass
class RefitBuilding(BuildingLabels):
    appliances: dict[str, RefitApplianceLabel]  # spreadsheet row index -> appliance label


@dataclass
class EcoBuilding(BuildingLabels):
    plugs: dict[str, DeviceLabel]       # NN_doc.txt plug id ('01'..'20') -> label


@dataclass
class GreendMeterLabel(DeviceLabel):
    room: str | None        # room from the NILMTK yaml; None when the block has no room line


@dataclass
class GreendBuilding(BuildingLabels):
    house_name: str | None                      # building 'original_name' from the yaml; None when absent
    meters: dict[str, list[GreendMeterLabel]]   # meter id (k-th MAC column of the raw CSVs) -> labels


def h5_metadata(node: Any) -> dict[str, Any]:
    """NILMTK store building metadata dict from a pytables node's 'metadata' attr."""
    md = node._v_attrs.metadata
    if not isinstance(md, dict):
        md = ast.literal_eval(str(md))
    return md


def write_slice(dataset: str, buildings: dict[str, BuildingLabels]) -> str:
    """Write one dataset's label map to data/gold/appliance_map_<dataset>.json."""
    ensure(GOLD_DIR)
    out = GOLD_DIR + '/appliance_map_%s.json' % dataset
    with open(out, 'w', encoding='utf-8') as fh:
        json.dump({
            '_meta': {'generated_by': 'extract_%s.py --labels' % dataset,
                      'generated_utc': datetime.now(timezone.utc).isoformat(timespec='seconds')},
            dataset: {k: v.record() for k, v in buildings.items()},
        }, fh, indent=1)
    return out
