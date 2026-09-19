"""Extract REDD NILMTK HDF5 store (6 US homes) to parquet.

Source: data/raw/redd/redd.h5. pandas read fails on its pytables metadata (written
by an old pandas), so conversion walks every Table node via pytables directly:
/buildingN/elec/meterM/table -> buildingN_elec_meterM.parquet, plus the NILMTK
cache tables (good_sections, total_energy). ts_us = index ns // 1000. Meter
attrs go to redd_meta.json. Source values are float32 and stored float32.
"""
import argparse, json, os, time
import numpy as np
import pandas as pd

from wattwiser import DATA, FND, RAW, done, ensure, load_manifest, log, record, save_manifest, stat_parquet, write_parquet
from wattwiser.labels import canonical_label, h5_metadata, write_slice

def extract(force=False):
    import tables
    name = 'redd'
    notes = ['source: data/raw/redd/redd.h5 (NILMTK pytables store); converted via pytables',
             'each /buildingN/elec/meterM/table -> ts_us (index ns -> us) + value_0 (float32, source dtype)',
             'nilmtk cache tables (good_sections/total_energy) included; meter attrs -> redd_meta.json']
    man = load_manifest(name, notes)
    outdir = os.path.join(FND, name)
    ensure(outdir)
    meta_out = {}
    with tables.open_file(os.path.join(RAW, 'redd', 'redd.h5'), 'r') as h:
        for node in h.walk_nodes('/', classname='Table'):
            path = node._v_pathname
            if not path.endswith('/table'):
                continue
            key = path.lstrip('/').replace('/table', '').replace('/', '_')
            if not force and done(man, key):
                continue
            t0 = time.time()
            arr = node.read()
            cols = list(node.description._v_names)
            idx = arr['index'].astype(np.int64) // 1000
            vals = arr['values_block_0']
            if vals.ndim == 2:
                vals = vals[:, 0]
            df = pd.DataFrame({'ts_us': idx, 'value_0': vals})
            out = os.path.join(outdir, key + '.parquet')
            write_parquet(df, out)
            st = stat_parquet(out)
            if st['rows'] != len(df):
                raise RuntimeError('row mismatch %s' % key)
            attrs = {k: str(node._v_attrs[k]) for k in node._v_attrs._v_attrnames
                     if not k.startswith(('NRT', 'pandas', 'TITLE', 'CLASS', 'VERSION', 'FLAVOR'))}
            meta_out[key] = attrs
            record(man, name, key, out, 'redd.h5:' + path, st, t0)
            log('%s: %d rows (%.0fs)' % (key, len(df), time.time() - t0))
        md = {}
        for node in h.walk_nodes('/'):
            nm = node._v_name or ''
            if 'meta' in nm.lower():
                try:
                    md[node._v_pathname] = str(node.read()) if isinstance(node, tables.Array) else str(node._v_attrs)
                except Exception as e:
                    md[node._v_pathname] = 'unreadable: %s' % e
    if md:
        meta_out['store_metadata'] = md
    with open(os.path.join(FND, name, 'redd_meta.json'), 'w') as fh:
        json.dump(meta_out, fh, indent=1, default=str)

def extract_labels():
    """Meter labels from the NILMTK store metadata (site meters + appliance types)."""
    import tables
    src = 'data/raw/redd/redd.h5'
    out = {}
    with tables.open_file(os.path.join(RAW, 'redd', 'redd.h5'), 'r') as h:
        for b in range(1, 7):
            md = h5_metadata(h.get_node('/building%d' % b))
            site = [k for k, v in md.get('elec_meters', {}).items() if v.get('site_meter')]
            meters = {}
            for a in md.get('appliances', []):
                for m in a.get('meters') or []:
                    label = str(a.get('type'))
                    e = meters.setdefault(str(m), {'label': label, 'canonical': canonical_label(label), 'count': 0})
                    e['count'] += 1
            out['building_%d' % b] = {'source': src, 'site_meters': site, 'meters': meters}
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--labels', action='store_true',
                    help='extract appliance labels only -> data/gold/appliance_map_redd.json')
    a = ap.parse_args()
    if a.labels:
        log('=== redd labels ===')
        log('wrote %s' % write_slice('redd', extract_labels()))
        log('=== done redd labels ===')
    else:
        log('=== redd extract ===')
        extract(force=a.force)
        log('=== done redd ===')
