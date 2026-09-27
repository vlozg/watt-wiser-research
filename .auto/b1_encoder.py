"""B1 m2: contrastive event encoder (numpy, deterministic) + retrieval gate.

Pre-registered bet B1 milestone m2 (.auto/ideas.md): a small encoder
mapping aggregate event signatures of the SAME device from DIFFERENT
houses close together, so enrollment (m3) can match house_1 calib marks
against eval windows by nearest-example. NumPy-only: fixed per-event
features + a linear projection trained with InfoNCE (positives =
same device different house; negatives = other devices; same-device-
same-house pairs neutral). Validation: leave-5-houses-out retrieval -
query events of held-out houses against galleries of the OTHER held-out
houses (cross-house invariance) and against K=5 same-house enrolled
marks (the actual m3 geometry). Encoder vs raw-feature baseline gate.

Saved to .auto/cache/b1_encoder_v1.npz with its standardization params.
"""

from __future__ import annotations

import zlib
from pathlib import Path

import numpy as np

ENC_VERSION = 'v1'
EMB_DIM = 64
TEMP = 0.1
EPOCHS = 300
BATCH = 2048
LR = 1e-3
WD = 1e-4
SEED = 0
K_ENROLL = 5
VAL_HOUSES = ('ukdale/house_3', 'refit/house_6', 'refit/house_7',
              'eco/house_01', 'redd/building_3')
_MAX_Q = 50
_CACHE = (Path(__file__).resolve().parent / 'cache' /
          ('b1_encoder_' + ENC_VERSION + '.npz'))


def _feat_rows(sig128: np.ndarray, peak: float, dur_s: float) -> np.ndarray:
    """One (128,) signature + scalars -> (72,) feature row."""
    thin = np.asarray(sig128, dtype='float32')[::2]
    pn = max(float(peak), 1.0)
    shape = np.clip(thin / pn, -2.0, 20.0)
    d = np.diff(thin)
    stats = np.asarray([
        peak / 1000.0,
        np.log1p(max(float(dur_s), 0.0)),
        thin.mean() / pn,
        thin.std() / pn,
        max(float(d.max()), 0.0) / pn,
        max(float(-d.min()), 0.0) / pn,
        float((thin ** 2).mean()) / (pn ** 2),
        float((thin > 0.1 * pn).mean()),
    ], dtype='float32')
    return np.concatenate([shape, stats])


def features(ev: dict) -> np.ndarray:
    """(N,128) signatures -> (N,72) fixed features (64 shape + 8 stats)."""
    return np.stack([
        _feat_rows(ev['sig'][i], ev['peak_w'][i], ev['dur_s'][i])
        for i in range(len(ev['sig']))
    ])


def feat_rows_batch(sigs, peaks, durs) -> np.ndarray:
    """Lists of (128,) signatures -> (n,72) features (model path)."""
    return np.stack([_feat_rows(s, p, d)
                     for s, p, d in zip(sigs, peaks, durs)])


def embed_segments(segs, cad_s: float, enc: tuple) -> np.ndarray:
    """Raw aggregate mark/candidate segments -> (n, EMB_DIM) embeddings.

    Each segment starts WIN_BEFORE_S (plus press jitter) before the
    event onset. Baseline = median of the first samples inside
    [WIN_BEFORE_S - BASELINE_GAP_S] (the miner's convention, minus the
    jitter slop); signature resampled to N_WIN like the miner.
    """
    import b1_events as be
    n_base = max(2, int(round((be.WIN_BEFORE_S - be.BASELINE_GAP_S)
                              / cad_s)))
    sigs, peaks, durs = [], [], []
    for seg in segs:
        seg = np.asarray(seg, dtype='float32')
        if len(seg) < 4:
            seg = np.zeros(be.N_WIN, dtype='float32')
        bs = seg[:min(n_base, len(seg))]
        bs = bs[np.isfinite(bs)]
        base = float(np.median(bs)) if len(bs) else 0.0
        sg = np.nan_to_num(seg - base, nan=0.0)
        x = np.linspace(0.0, 1.0, len(sg))
        sg = np.interp(np.linspace(0.0, 1.0, be.N_WIN), x,
                       sg).astype('float32')
        sigs.append(sg)
        peaks.append(float(sg.max()))
        durs.append(max(1.0, (len(seg) - 1) * cad_s - 2 * be.WIN_BEFORE_S))
    X = feat_rows_batch(sigs, peaks, durs)
    W, mu, sd = enc
    return _l2(((X - mu) / sd) @ W)


def _l2(z: np.ndarray) -> np.ndarray:
    return z / np.maximum(np.linalg.norm(z, axis=1, keepdims=True), 1e-9)


def train_encoder(Xtr: np.ndarray, dev: np.ndarray, house: np.ndarray
                  ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """InfoNCE linear encoder; returns (W, mu, sd)."""
    mu = Xtr.mean(0, keepdims=True)
    sd = np.maximum(Xtr.std(0, keepdims=True), 1e-6)
    X = (Xtr - mu) / sd
    rng = np.random.default_rng(SEED)
    W = rng.normal(0.0, 1.0 / np.sqrt(X.shape[1]), (X.shape[1], EMB_DIM))
    mW = np.zeros_like(W)
    vW = np.zeros_like(W)
    n = len(X)
    for ep in range(EPOCHS):
        idx = rng.choice(n, size=min(BATCH, n), replace=False)
        Xb, db, hb = X[idx], dev[idx], house[idx]
        Z = _l2(Xb @ W)
        S = (Z @ Z.T) / TEMP
        np.fill_diagonal(S, -1e9)
        pos = (db[:, None] == db[None, :]) & (hb[:, None] != hb[None, :])
        pos_fb = ((db[:, None] == db[None, :]) & (hb[:, None] == hb[None, :])
                  & ~np.eye(len(idx), dtype=bool))
        pos = np.where(pos.any(1)[:, None], pos, pos_fb)
        neg = db[:, None] != db[None, :]
        allowed = pos | neg
        logits = np.where(allowed, S, -1e9)
        lse = _logsumexp(logits)
        p = np.exp(logits - lse[:, None])
        p[~allowed] = 0.0
        posp = np.maximum((p * pos).sum(1), 1e-12)
        wpos = (p * pos) / posp[:, None]
        g = np.where(allowed, p, 0.0) - np.where(pos, wpos, 0.0)
        dZ = (g @ Z) / TEMP
        dW = Xb.T @ dZ + WD * W
        mW = 0.9 * mW + 0.1 * dW
        vW = 0.999 * vW + 0.001 * dW * dW
        W -= LR * mW / (np.sqrt(vW) + 1e-8)
    return W, mu[0], sd[0]


def _logsumexp(a: np.ndarray) -> np.ndarray:
    m = a.max(1, keepdims=True)
    return (m + np.log(np.exp(a - m).sum(1, keepdims=True)))[:, 0]


def retrieval(ev: dict, X: np.ndarray, mode: str,
              per_device_cap: int = _MAX_Q) -> dict:
    """Top-1 device retrieval on held-out houses.

    mode 'cross': gallery = events of other held-out houses (invariance).
    mode 'enroll': gallery = K_ENROLL random same-house marks per device
    (the m3 geometry). Hit = nearest neighbour has the right device.
    """
    tags = ev['house_tags'][ev['house']]
    val = np.isin(tags, VAL_HOUSES)
    rng = np.random.default_rng(SEED + 1)
    out = {}
    for d, name in enumerate(ev['device_names']):
        qidx = np.where(val & (ev['dev'] == d))[0]
        if len(qidx) > per_device_cap:
            qidx = np.sort(rng.choice(qidx, size=per_device_cap, replace=False))
        hits = 0
        tried = 0
        for i in qidx:
            if mode == 'cross':
                # Gallery = every event of the other held-out houses. A
                # hit means the NEAREST neighbour carries the right
                # device, so the gallery must contain the positives (same
                # device, other houses) alongside other devices as
                # distractors. The old ev['dev'] != d filter kept only
                # distractors, so no hit was possible and the reported
                # 'cross-house invariance 0.000' was that artifact, not a
                # measurement (owner-directed fix). Enroll mode already
                # galleries same-device + other-device events.
                gal = np.where(val
                               & (ev['house'] != ev['house'][i]))[0]
            else:
                hs = ev['house'][i]
                same = np.where(val & (ev['dev'] == d) & (ev['house'] == hs)
                                & (np.arange(len(ev['dev'])) != i))[0]
                if len(same) == 0:
                    continue
                take = min(K_ENROLL, len(same))
                parts = [np.sort(rng.choice(same, size=take, replace=False))]
                for dd in range(len(ev['device_names'])):
                    if dd == d:
                        continue
                    oth = np.where(val & (ev['dev'] == dd)
                                   & (ev['house'] == hs))[0]
                    if len(oth) == 0:
                        continue
                    t2 = min(K_ENROLL, len(oth))
                    parts.append(np.sort(rng.choice(oth, size=t2,
                                                    replace=False)))
                gal = np.concatenate(parts)
            if len(gal) == 0:
                continue
            sims = X[gal] @ X[i]
            j = gal[int(np.argmax(sims))]
            hits += int(ev['dev'][j] == d)
            tried += 1
        out[str(name)] = (hits / tried) if tried else float('nan')
    return out


if __name__ == '__main__':
    import b1_events as be
    import bench_v3 as v3
    ev = be.mine_pool(v3.make_pretrain_ctx())
    X = features(ev)
    hidx = ev['house']
    is_val = np.isin(np.asarray(ev['house_tags'])[hidx], VAL_HOUSES)
    W, mu, sd = train_encoder(X[~is_val], ev['dev'][~is_val],
                              hidx[~is_val])
    Xenc = _l2(((X - mu) / sd) @ W)
    Xraw = (X - mu) / sd
    print('--- B1 m2 retrieval gate (held-out houses: '
          + ', '.join(VAL_HOUSES) + ')')
    for mode in ('cross', 'enroll'):
        for label, XX in (('raw', Xraw), ('enc', Xenc)):
            r = retrieval(ev, XX, mode)
            vals = [v for v in r.values() if np.isfinite(v)]
            print(f'   {mode:6s} {label}: mean={np.mean(vals):.3f} '
                  + ' '.join(f'{k}={v:.3f}' for k, v in r.items()))
    _CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez(_CACHE, W=W, mu=mu, sd=sd,
             val_houses=np.asarray(VAL_HOUSES),
             enc_version=np.asarray(ENC_VERSION))
    print('   saved ->', _CACHE.name)


def load_or_train_encoder(pretrain_ctx: dict) -> tuple:
    """Frozen deterministic encoder: load cache, else mine + train + save.

    pretrain_ctx is the model's ctx['pretrain'] - pool data enters the
    model only through ctx; the artifact is a deterministic function of
    that same pool (seed 0), so loading the cache is equivalent to
    recomputing it.
    """
    if _CACHE.exists():
        z = np.load(_CACHE, allow_pickle=False)
        return z['W'], z['mu'], z['sd']
    import b1_events as be
    ev = be.mine_pool(pretrain_ctx)
    X = features(ev)
    hidx = ev['house']
    is_val = np.isin(np.asarray(ev['house_tags'])[hidx], VAL_HOUSES)
    W, mu, sd = train_encoder(X[~is_val], ev['dev'][~is_val],
                              hidx[~is_val])
    _CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez(_CACHE, W=W, mu=mu, sd=sd,
             val_houses=np.asarray(VAL_HOUSES),
             enc_version=np.asarray(ENC_VERSION))
    return W, mu, sd
