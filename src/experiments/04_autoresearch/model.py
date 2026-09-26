"""Autoresearch iteration model - the ONLY file iterations may change.

v1 (i1 baseline): multi-house pretrained multi-output dilated CNN seq2seq.
Trains on source houses labelled channels only; the K calibration sessions
in ctx are accepted but not used yet (i2 will add calibration fine-tuning).
"""
from __future__ import annotations

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

SEED = 2026
EPOCHS = 5
BATCH = 512
LR = 1e-3
N_TRAIN_WINDOWS = 40_000
N_VAL_WINDOWS = 8_000
LAMBDA_BCE = 1.0
POSW_MAX = 50.0
CHANNELS = 64
PRED_BATCH = 1024


def _valid_starts(a: np.ndarray, w: int) -> np.ndarray:
    nan = np.isnan(a)
    c = np.concatenate([[0], np.cumsum(nan.astype(np.int64))])
    counts = c[w:] - c[:-w]
    return np.flatnonzero(counts == 0)


def _gather(a: np.ndarray, starts: np.ndarray, w: int) -> np.ndarray:
    return a[starts[:, None] + np.arange(w)[None, :]]


class Net(nn.Module):
    def __init__(self, n_dev: int, ch: int = CHANNELS):
        super().__init__()
        self.enc = nn.Sequential(
            nn.Conv1d(1, ch, 7, padding=3), nn.ReLU(),
            nn.Conv1d(ch, ch, 7, padding=12, dilation=4), nn.ReLU(),
            nn.Conv1d(ch, ch, 7, padding=48, dilation=16), nn.ReLU(),
        )
        self.head_power = nn.Conv1d(ch, n_dev, 7, padding=3)
        self.head_on = nn.Conv1d(ch, n_dev, 7, padding=3)

    def forward(self, x):  # x: (B, T, 1)
        z = self.enc(x.transpose(1, 2))
        p = torch.clamp(self.head_power(z), min=0.0).transpose(1, 2)
        o = self.head_on(z).transpose(1, 2)
        return p, o


def build_and_train(ctx: dict):
    meta = ctx['meta']
    devices = meta['devices']
    thr = meta['thresholds']
    w = meta['window']
    torch.manual_seed(SEED)
    rng = np.random.default_rng(SEED)

    max_w = {}
    for dev in devices:
        vals = [float(np.nanmax(h['train']['devices'][dev]))
                for h in ctx['pretrain'].values()]
        max_w[dev] = max(max(vals), 1.0)

    def build_pool(split: str, n_windows: int) -> dict:
        xs, ys, ms, ons = [], [], [], []
        starts_by_house = {h: _valid_starts(d[split]['mains'], w)
                           for h, d in ctx['pretrain'].items()}
        total = sum(len(s) for s in starts_by_house.values()) or 1
        for h, d in ctx['pretrain'].items():
            starts_all = starts_by_house[h]
            take = min(len(starts_all),
                       int(round(n_windows * len(starts_all) / total)))
            sel = rng.choice(starts_all, size=take, replace=False)
            xs.append(_gather(d[split]['mains'], sel, w))
            yl, ml, ol = [], [], []
            for dev in devices:
                yw = _gather(d[split]['devices'][dev], sel, w)
                m = ~np.isnan(yw)
                yl.append(np.clip(np.nan_to_num(yw, nan=0.0) / max_w[dev], 0, 1.5))
                ml.append(m)
                ol.append((np.nan_to_num(yw, nan=0.0) > thr[dev]) & m)
            ys.append(np.stack(yl, axis=-1))
            ms.append(np.stack(ml, axis=-1))
            ons.append(np.stack(ol, axis=-1))
        return {'x': np.concatenate(xs), 'ys': np.concatenate(ys),
                'ms': np.concatenate(ms), 'ons': np.concatenate(ons)}

    train = build_pool('train', N_TRAIN_WINDOWS)
    val = build_pool('val', N_VAL_WINDOWS)
    pos_w = torch.ones(len(devices), dtype=torch.float32)
    for j, dev in enumerate(devices):
        pos = int(train['ons'][:, :, j].sum())
        neg = int(train['ms'][:, :, j].sum()) - pos
        pos_w[j] = min(POSW_MAX, max(1.0, neg / max(pos, 1)))
    print('   per-device pos_weight:',
          {d: round(float(pos_w[j]), 1) for j, d in enumerate(devices)})

    def tens(a):
        return torch.from_numpy(np.ascontiguousarray(a, dtype='float32'))

    ds = torch.utils.data.TensorDataset(
        torch.from_numpy(train['x'][:, :, None].astype('float32')),
        torch.from_numpy(train['ys'].astype('float32')),
        torch.from_numpy(train['ms'].astype('float32')),
        torch.from_numpy(train['ons'].astype('float32')))
    dl = torch.utils.data.DataLoader(ds, batch_size=BATCH, shuffle=True,
        generator=torch.Generator().manual_seed(SEED))

    net = Net(len(devices))
    opt = torch.optim.Adam(net.parameters(), lr=LR)
    xva = torch.from_numpy(val['x'][:, :, None].astype('float32'))
    yva = torch.from_numpy(val['ys'].astype('float32'))
    mva = torch.from_numpy(val['ms'].astype('float32'))
    for epoch in range(EPOCHS):
        net.train()
        tot_mse = tot_bce = n_b = 0.0
        for xb, ysb, mb, onb in dl:
            opt.zero_grad()
            p, o = net(xb)
            diff = (p - ysb) * mb
            mse = (diff * diff).sum() / mb.sum().clamp(min=1.0)
            bce = (F.binary_cross_entropy_with_logits(
                o, onb, pos_weight=pos_w, reduction='none')
                * mb).sum() / mb.sum().clamp(min=1.0)
            loss = mse + LAMBDA_BCE * bce
            loss.backward()
            opt.step()
            tot_mse += float(mse.detach())
            tot_bce += float(bce.detach())
        with torch.no_grad():
            net.eval()
            pv, _ = net(xva)
            dv = (pv - yva) * mva
            val_mse = float((dv * dv).sum() / mva.sum().clamp(min=1.0))
        print(f'   epoch {epoch}: train_mse={tot_mse:.5f} bce={tot_bce:.5f}'
              f' val_mse_scaled={val_mse:.5f}')

    net.eval()

    @torch.no_grad()
    def predict(mains: np.ndarray) -> dict:
        t = len(mains)
        pad = w - 1
        x = np.pad(np.nan_to_num(mains.astype('float32'), nan=0.0),
                   (pad, pad), mode='edge')
        starts = np.arange(0, len(x) - w + 1, meta['stride'])
        acc = np.zeros((len(x), len(devices)), dtype='float64')
        cnt = np.zeros(len(x), dtype='float64')
        for i in range(0, len(starts), PRED_BATCH):
            b = starts[i:i + PRED_BATCH]
            xb = torch.from_numpy(_gather(x, b, w)[:, :, None])
            p, _ = net(xb)
            pn = p.numpy()  # (B, w, n_dev) - accumulate every device channel
            for k in range(pn.shape[0]):
                s0 = int(b[k])
                acc[s0:s0 + w] += pn[k]
                cnt[s0:s0 + w] += 1.0
        core = (acc / cnt[:, None])[pad:pad + t]
        return {dev: np.clip(core[:, j] * max_w[dev], 0.0, None).astype('float32')
                for j, dev in enumerate(devices)}

    return predict