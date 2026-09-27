"""B1 m1: cross-house event miner over the ctx['pretrain'] pool.

Pre-registered bet B1 (milestone m1, .auto/ideas.md): mine per-device
switch events from every pretraining house (submeter supervision is
allowed in pretraining houses, never in house_1), and extract for each
event the AGGREGATE window around it - the raw signal a deployed model
sees - baseline-subtracted and resampled to a fixed 128-sample
signature. Cached content-addressed on the pool manifest + miner
version. house_1 is never mined; its calib marks become enrollment
queries at inference (m3).

Multi-channel canonical devices use the union mask (same rule as
bench_v3.refit_gt). Threshold sanity: thr <= 0.5 * p50_on_W where p50
exists (mirrors bench_v3.refit_channels); entries without p50 keep
their declared threshold. Deterministic capping: at most
MAX_PER_HOUSE_DEVICE events per house-device, seeded by the tag.
"""

from __future__ import annotations

import json
import zlib
from pathlib import Path

import numpy as np

import bench_v2 as v2

MINER_VERSION = 'v1'
N_WIN = 128
WIN_BEFORE_S = 60.0
WIN_AFTER_S = 60.0
BASELINE_GAP_S = 10.0
MAX_PER_HOUSE_DEVICE = 200
DEVICES = ('kettle', 'microwave', 'fridge', 'washing_machine', 'dishwasher')
DEV_ID = {d: i for i, d in enumerate(DEVICES)}
_CACHE = (Path(__file__).resolve().parent / 'cache' /
          ('b1_events_' + MINER_VERSION + '.npz'))


def channel_thresholds(ds: str, house: str) -> dict:
    """{channel: (thr_watts, sane)} for canonical-mapped channels."""
    import bench_v3 as v3
    canon = v3._canon_map(ds, house)
    out: dict = {}
    if ds == 'refit':
        for _dev, chans in v3.refit_channels(house).items():
            for ch, t, sane in chans:
                if ch in canon:
                    out[ch] = (float(t), bool(sane))
        return out
    raw = json.loads((v3.GOLD / 'thresholds.json').read_text())
    for ch, m in raw.get(ds, {}).get(house, {}).items():
        if m.get('canonical') not in DEV_ID:
            continue
        thr = m.get('thr_on_W', m.get('thr_used_w'))
        p50 = m.get('p50_on_W')
        if thr is None:
            continue
        sane = True if p50 is None else (float(thr) <= 0.5 * float(p50))
        out[ch] = (float(thr), sane)
    return out


def event_signature(mains: np.ndarray, ts_us: np.ndarray,
                    s_us: int, e_us: int):
    """Fixed-length baseline-subtracted aggregate window for one event."""
    lo_us = s_us - int(WIN_BEFORE_S * 1e6)
    hi_us = e_us + int(WIN_AFTER_S * 1e6)
    lo = max(int(np.searchsorted(ts_us, lo_us)), 0)
    hi = min(int(np.searchsorted(ts_us, hi_us)), len(ts_us))
    if hi - lo < 4:
        return None
    w = mains[lo:hi]
    blo = int(np.searchsorted(ts_us[lo:hi], s_us - int(BASELINE_GAP_S * 1e6)))
    base_seg = w[:max(blo, 1)]
    base_seg = base_seg[np.isfinite(base_seg)]
    base = float(np.median(base_seg)) if len(base_seg) else 0.0
    sig = np.nan_to_num(w - base, nan=0.0).astype('float32')
    x = np.linspace(0.0, 1.0, len(sig))
    return np.interp(np.linspace(0.0, 1.0, N_WIN), x, sig).astype('float32')


def mine_pool(pretrain_ctx: dict) -> dict:
    """Mine all pool houses; cached on (MINER_VERSION, house list)."""
    import bench_v3 as v3
    tags = list(pretrain_ctx['houses'])
    manifest = (MINER_VERSION + '|' + ';'.join(tags)).encode()
    if _CACHE.exists():
        z = np.load(_CACHE, allow_pickle=False)
        if z['manifest_sig'].item() == manifest:
            return {k: z[k] for k in z.files}
        print('   b1_events: cache stale, remining')
    ev_dev, ev_house, ev_dur, ev_peak, ev_sig = [], [], [], [], []
    per_hd = {}
    for hi, tag in enumerate(tags):
        ds, house = tag.split('/', 1)
        thrs = channel_thresholds(ds, house)
        h = pretrain_ctx['load'](tag)
        ts, mains = h['ts_us'], h['mains']
        union: dict = {}
        for ch, dev in h['canonical'].items():
            if dev not in DEV_ID:
                continue
            t, sane = thrs.get(ch, (None, False))
            if t is None or not sane:
                continue
            w = h['channels'][ch]
            m = (~np.isnan(w)) & (np.nan_to_num(w) > t)
            if dev in union:
                union[dev] |= m
            else:
                union[dev] = m
        for dev in sorted(union):
            cyc = v2.cycles_from_mask(union[dev], ts, dev)
            if not len(cyc):
                continue
            rng = np.random.default_rng(
                (0 + zlib.crc32((tag + '/' + dev).encode())) % 2**32)
            n = len(cyc)
            if n > MAX_PER_HOUSE_DEVICE:
                idx = np.sort(rng.choice(n, size=MAX_PER_HOUSE_DEVICE,
                                         replace=False))
            else:
                idx = np.arange(n)
            kept = 0
            for i in idx:
                s_us = int(cyc['t_on_us'].iloc[i])
                e_us = int(cyc['t_off_us'].iloc[i])
                dur = (e_us - s_us) / 1e6
                if dur <= 0:
                    continue
                sg = event_signature(mains, ts, s_us, e_us)
                if sg is None:
                    continue
                ev_dev.append(DEV_ID[dev])
                ev_house.append(hi)
                ev_dur.append(dur)
                ev_peak.append(float(sg.max()))
                ev_sig.append(sg)
                kept += 1
            per_hd[tag + '/' + dev] = (n, kept)
        counts = {}
        for dev in sorted(union):
            n = len(v2.cycles_from_mask(union[dev], ts, dev))
            if n:
                counts[dev] = n
        print('   b1_events: ' + tag + ': '
              + ', '.join(f'{d}={n}c' for d, n in sorted(counts.items())))
    out = {
        'dev': np.asarray(ev_dev, dtype='int8'),
        'house': np.asarray(ev_house, dtype='int16'),
        'dur_s': np.asarray(ev_dur, dtype='float32'),
        'peak_w': np.asarray(ev_peak, dtype='float32'),
        'sig': np.asarray(ev_sig, dtype='float32'),
        'house_tags': np.asarray(tags),
        'device_names': np.asarray(DEVICES),
        'manifest_sig': np.asarray(manifest),
    }
    _CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(_CACHE, **out)
    print(f'   b1_events: mined {len(ev_dev)} events from {len(tags)} '
          f'houses -> {_CACHE.name}')
    for k in sorted(per_hd):
        n, kept = per_hd[k]
        print(f'      {k}: {n} cycles, kept {kept}')
    return out


if __name__ == '__main__':
    import bench_v3 as v3
    ev = mine_pool(v3.make_pretrain_ctx())
    names = [DEVICES[i] for i in ev['dev']]
    print('total events:', len(ev['dev']))
    for d in DEVICES:
        m = ev['dev'] == DEV_ID[d]
        p = ev['peak_w'][m]
        print(f'   {d:16s} n={m.sum():6d} '
              f'peak p10/p50/p90 = {np.percentile(p, 10):7.1f}/'
              f'{np.percentile(p, 50):7.1f}/{np.percentile(p, 90):7.1f} W '
              f'dur p50 = {np.median(ev["dur_s"][m]):7.0f} s')
