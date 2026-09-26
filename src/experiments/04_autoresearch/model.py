"""Autoresearch iteration model - the ONLY file iterations may change.

v1 (i1 baseline): multi-house pretrained multi-output dilated CNN seq2seq.

v2 (i1b training stability): input scaled to kW, power head clamped, grad
clip, LR 3e-4, 12 epochs, predict NaN guard. (Evidence: v1 collapsed to
all-zero output with unnormalized inputs.)

v3 (i2 whole-net calib fine-tune, DISCARDED): lifted kettle/washing_machine
episode F1 but overfit 25 calib windows - retention MSE 11x worse, MAE 2x.

v4 (i9 output-scale calibration, DISCARDED): least-scales all came out ~1.0
because microwave/fridge/washing_machine heads output EXACTLY 0W on their own
calib ON windows (measured), while the ON head is alive (sigmoid max 1.0) but
DISCARDED in predict. Output calibration cannot revive dead heads.

v5 (head-role separation): three coupled fixes for the dead-head pathology.
(1) power head = softplus (clamp(min=0) is a dead-ReLU trap: once a channel's
pre-activation goes negative its gradient through the clamp is zero forever;
softplus is differentiable everywhere). (2) MSE masked to device-ON positions
only - the power head fits AMPLITUDE where it matters; the tiny fridge targets
(90/2048 = 0.044) no longer drown in a full-span MSE. (3) detection routes
through the already-alive ON head: predict watts = max_w * core_power *
gate(sigmoid(on_logit) > gate_thr_d), with gate_thr_d and an amplitude scale
calibrated per device from the K=5 target-house calib sessions (ON/OFF sigmoid
quantiles; ON-position median watts). All calibration data is house_1
PRE-SPLIT - no eval leakage.
"""
from __future__ import annotations

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

SEED = 2026
EPOCHS = 12
BATCH = 512
LR = 3e-4
INPUT_SCALE = 1000.0  # mains watts -> kW on the network input
GRAD_CLIP = 1.0
N_TRAIN_WINDOWS = 40_000
N_VAL_WINDOWS = 8_000
LAMBDA_BCE = 1.0
POSW_MAX = 50.0
CHANNELS = 64
PRED_BATCH = 1024
GATE_MIN, GATE_MAX = 0.05, 0.95  # clamp for calibrated gate thresholds
AMP_MIN, AMP_MAX = 0.5, 4.0      # clamp for calibrated amplitude scale


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
        # softplus: non-negative like the old clamp(min=0) but with a nonzero
        # gradient everywhere, so a channel cannot die through the clamp.
        p = torch.clamp(F.softplus(self.head_power(z)), max=1.5).transpose(1, 2)
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
            xs.append(_gather(d[split]['mains'], sel, w) / INPUT_SCALE)
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
    ova = torch.from_numpy(val['ons'].astype('float32'))
    for epoch in range(EPOCHS):
        net.train()
        tot_mse = tot_bce = 0.0
        for xb, ysb, mb, onb in dl:
            opt.zero_grad()
            p, o = net(xb)
            # amplitude head: fit watts ONLY where the device is ON
            m_on = mb * onb
            diff = (p - ysb) * m_on
            mse = (diff * diff).sum() / m_on.sum().clamp(min=1.0)
            bce = (F.binary_cross_entropy_with_logits(
                o, onb, pos_weight=pos_w, reduction='none')
                * mb).sum() / mb.sum().clamp(min=1.0)
            loss = mse + LAMBDA_BCE * bce
            loss.backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(), GRAD_CLIP)
            opt.step()
            tot_mse += float(mse.detach())
            tot_bce += float(bce.detach())
        with torch.no_grad():
            net.eval()
            pv, _ = net(xva)
            dv_on = (pv - yva) * mva * ova
            dv_full = (pv - yva) * mva
            val_on = float((dv_on * dv_on).sum() / (mva * ova).sum().clamp(min=1.0))
            val_full = float((dv_full * dv_full).sum() / mva.sum().clamp(min=1.0))
        print(f'   epoch {epoch}: train_mse_on={tot_mse:.5f} bce={tot_bce:.5f}'
              f' val_mse_on={val_on:.5f} val_mse_full={val_full:.5f}')

    # ---- calibrate per-device gate + amplitude from target-house calib ----
    gate_thr = np.zeros(len(devices), dtype='float32')
    amp_scale = np.ones(len(devices), dtype='float32')
    for j, dev in enumerate(devices):
        cw = ctx['calib'][dev]
        xm = torch.from_numpy(
            (cw['mains_win'].astype('float32') / INPUT_SCALE)[:, :, None])
        dw = cw['device_win'].astype('float32')
        m = np.isfinite(dw)
        with torch.no_grad():
            pc, oc = net(xm)
        sig = torch.sigmoid(oc[:, :, j]).numpy()
        pw = pc[:, :, j].numpy() * max_w[dev]
        dwz = np.nan_to_num(dw, nan=0.0)
        on = m & (dwz > thr[dev])
        off = m & ~(dwz > thr[dev])
        on_q = np.percentile(sig[on], [5, 50, 95]) if on.any() else None
        off_q = np.percentile(sig[off], [50, 95]) if off.any() else None
        if on_q is not None and off_q is not None:
            gt = float(np.clip((on_q[0] + off_q[1]) / 2.0, GATE_MIN, GATE_MAX))
        else:
            gt = 0.5
        gate_thr[j] = gt
        med_pred = float(np.median(pw[on])) if on.any() else 0.0
        med_true = float(np.median(dw[on])) if on.any() else 0.0
        r = float(np.clip(med_true / med_pred, AMP_MIN, AMP_MAX))             if med_pred > 1.0 else 1.0
        amp_scale[j] = r
        sq = lambda a, q: f'{np.percentile(a, q):.2f}' if len(a) else 'nan'
        print(f'   calib-gate {dev}: sigON p05/p50/p95='
              f'{sq(sig[on], 5)}/{sq(sig[on], 50)}/{sq(sig[on], 95)}'
              f' sigOFF p50/p95={sq(sig[off], 50)}/{sq(sig[off], 95)}'
              f' gate={gt:.2f}'
              f' | amp med_pred={med_pred:.0f}W med_true={med_true:.0f}W'
              f' r={r:.2f} (x{max_w[dev]:.0f})')
    print('   gate_thr:', {d: round(float(gate_thr[j]), 2)
                           for j, d in enumerate(devices)})

    net.eval()

    @torch.no_grad()
    def predict(mains: np.ndarray) -> dict:
        t = len(mains)
        pad = w - 1
        x = np.pad(np.nan_to_num(mains.astype('float32'), nan=0.0) / INPUT_SCALE,
                   (pad, pad), mode='edge')
        starts = np.arange(0, len(x) - w + 1, meta['stride'])
        acc = np.zeros((len(x), len(devices)), dtype='float64')
        cnt = np.zeros(len(x), dtype='float64')
        for i in range(0, len(starts), PRED_BATCH):
            b = starts[i:i + PRED_BATCH]
            xb = torch.from_numpy(_gather(x, b, w)[:, :, None])
            p, o = net(xb)
            g = (torch.sigmoid(o).numpy() > gate_thr[None, None, :])                 .astype('float32')
            pg = p.numpy() * g          # gate kills off-segments per device
            for k in range(pg.shape[0]):
                s0 = int(b[k])
                acc[s0:s0 + w] += pg[k]
                cnt[s0:s0 + w] += 1.0
        safe = np.where(cnt[:, None] > 0, acc / np.maximum(cnt, 1.0)[:, None], 0.0)
        core = safe[pad:pad + t]
        return {dev: np.clip(core[:, j] * max_w[dev] * amp_scale[j],
                             0.0, None).astype('float32')
                for j, dev in enumerate(devices)}

    return predict
