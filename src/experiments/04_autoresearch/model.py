"""Rules-first NILM v0 on the v2 cycle protocol: pair aggregate power
steps into events, match amplitude/duration against profiles built from
aggregate-only calibration marks (FAQ Q1; fridge = passive window),
merge program-device events into cycles. Pauses the v23 NN line (runs
10-27 optimized the v1 episode metric, verified unlearnable).
Known v0 limits: same-wattage devices confuse on amplitude (kettle vs
wm/dw heater steps); no interference handling (H06); no phase models."""
from __future__ import annotations

import numpy as np

BASE_N = 10            # pre-onset baseline samples (60 s)
SMOOTH_N = 5           # rolling-median smoothing (30 s at 6 s cadence)
STEP_H = 3             # +-18 s step-probe half window
AMP_MIN_W = 50.0       # minimum credible switch-on step (below fridge amp)
REL_AMP = 0.20         # profile amplitude tolerance (+-20%)
REL_DUR = (1.0 / 3.0, 3.0)
MAXSPAN_S = 7200.0     # max rise->fall pairing distance
FALL_REL = (0.4, 2.5)  # paired fall amplitude vs rise


def _roll_median(x: np.ndarray, n: int) -> np.ndarray:
    pad = n // 2
    xp = np.pad(x, pad, mode='edge')
    win = np.lib.stride_tricks.sliding_window_view(xp, n)
    return np.median(win, axis=1).astype('float32')


def _runs(on: np.ndarray):
    d = np.diff(np.concatenate([[0], on.astype(np.int8), [0]]))
    return list(zip(np.flatnonzero(d == 1).tolist(),
                    np.flatnonzero(d == -1).tolist()))


def _profile_from_marks(cal: dict, cad_s: float, roll_s: float,
                        dev_class: str) -> dict:
    """Amplitude/duration/mean-power profile from calibration marks only.
    Marks carry a pre/post roll (the session records before switch-on):
    non-passive stats use the rolled-off core. Amplitude estimator is
    per class: burst = ON-plateau median (flat boil / mw burst),
    program = p90 (heater level), duty/passive = recurring rise/fall
    pairs 10-40 min apart with matched amplitude (the compressor).
    Known limit: a small cycling load near 50 W can outnumber
    compressor pairs in a 3 h window; periodicity scan is backlog idea 5."""
    if cal['passive'] or dev_class == 'duty':
        w = cal['mains_seg'][0].astype('float64')
        base = float(np.percentile(w, 20))
        fut = np.concatenate([w[STEP_H:], np.full(STEP_H, w[-1])])
        past = np.concatenate([np.full(STEP_H, w[0]), w[:-STEP_H]])
        stp = fut - past
        # Recurring rise/fall pairs = the compressor's duty cycle.
        def pair_fallback():
            up = stp > 40.0
            dn = stp < -40.0
            ri = np.flatnonzero(up & ~np.concatenate([[False], up[:-1]]))
            fi = np.flatnonzero(dn & ~np.concatenate([[False], dn[:-1]]))
            mn_s, mx_s = 10 * 60 / cad_s, 40 * 60 / cad_s
            p_amp, p_dt = [], []
            for i in ri:
                j = int(np.searchsorted(fi, i))
                if j < len(fi) and mn_s <= fi[j] - i <= mx_s \
                        and abs(stp[fi[j]] + stp[i]) <= 0.25 * stp[i]:
                    p_amp.append(float(stp[i]))
                    p_dt.append(float(fi[j] - i))
            if len(p_amp) >= 2:
                return float(np.median(p_amp)), float(np.median(p_dt)) * cad_s
            a = max(float(np.percentile(w, 85)) - base, 30.0)
            onm = w > base + 0.5 * a
            durs = [(b - a2) * cad_s for a2, b in _runs(onm) if b - a2 >= 2]
            return a, float(np.median(durs)) if durs else 1200.0

        amp, dur = pair_fallback()
        on = w > base + 0.5 * amp
        onlvl = w[on]
        mean_w = float(onlvl.mean() - base) if len(onlvl) else amp
        return {'amp': amp, 'dur_s': dur, 'mean_w': max(mean_w, 30.0)}
    rn = int(round(roll_s / cad_s))
    amps, durs, means = [], [], []
    for seg in cal['mains_seg']:
        s = seg.astype('float64')
        base = float(np.median(s[:BASE_N]))
        core = s[rn:-rn] if len(s) > 2 * rn + 4 else s
        hi = max(float(np.percentile(core, 90)) - base, 30.0)
        if dev_class == 'burst':
            onm = core > base + 0.5 * hi
            amps.append(max(float(np.median(core[onm])) - base, 30.0)
                        if onm.any() else hi)
        else:
            amps.append(hi)
        durs.append(len(core) * cad_s)
        means.append(max(float(core.mean()) - base, 30.0))
    return {'amp': float(np.median(amps)), 'dur_s': float(np.median(durs)),
            'mean_w': float(np.median(means))}


def build_and_train(ctx: dict):
    meta = ctx['meta']
    devices = meta['devices']
    cad_s = meta['cadence_us'] / 1e6
    class_of = meta['device_class']
    merge_n = {d: int(round(meta['merge_s'][d] / cad_s)) for d in devices}
    prof = {d: _profile_from_marks(ctx['calib'][d], cad_s,
                                   float(meta.get('pre_roll_s', 0.0)),
                                   class_of[d])
            for d in devices}

    def predict(filled) -> dict:
        sig = _roll_median(np.asarray(filled, dtype='float32'), SMOOTH_N)
        n = len(sig)
        fut = np.concatenate([sig[STEP_H:], np.full(STEP_H, sig[-1])])
        past = np.concatenate([np.full(STEP_H, sig[0]), sig[:-STEP_H]])
        stp = fut - past
        is_rise = stp > AMP_MIN_W
        is_fall = stp < -AMP_MIN_W
        rise_e = is_rise & ~np.concatenate([[False], is_rise[:-1]])
        fall_e = is_fall & ~np.concatenate([[False], is_fall[:-1]])
        r_idx = np.flatnonzero(rise_e)
        f_idx = np.flatnonzero(fall_e)
        events = []  # (on, off, amp) sorted by on
        for k, i in enumerate(r_idx):
            j = int(np.searchsorted(f_idx, i + STEP_H))
            if j >= len(f_idx) or (f_idx[j] - i) * cad_s > MAXSPAN_S:
                continue
            amp = float(stp[i])
            if not FALL_REL[0] * amp <= -stp[f_idx[j]] <= FALL_REL[1] * amp:
                continue
            events.append((int(i), int(f_idx[j]), amp))
        if not events:
            return {d: np.zeros(n, dtype='float32') for d in devices}
        ev_on = np.array([e[0] for e in events])
        ev_off = np.array([e[1] for e in events])

        def extend_cycle(on0: int, off0: int, mg: int):
            # Absorb surrounding events into the program cluster in both
            # directions: pump/fill steps precede the heater, so the
            # cycle onset is the cluster start, not the seed event.
            start, end = on0, off0
            while True:
                k = int(np.searchsorted(ev_on, end, side='right'))
                if k < len(ev_on) and ev_on[k] <= end + mg:
                    end = max(end, int(ev_off[k]))
                    continue
                kb = int(np.searchsorted(ev_on, start, side='left')) - 1
                if kb >= 0 and ev_on[kb] < start and ev_off[kb] >= start - mg:
                    start = int(ev_on[kb])
                    continue
                return start, end

        out = {d: np.zeros(n, dtype='float32') for d in devices}
        for (i, off, amp) in events:
            best = None
            for d in devices:
                p = prof[d]
                da = abs(amp - p['amp']) / p['amp']
                if da <= REL_AMP and (best is None or da < best[0]):
                    best = (da, d)
            if best is None:
                continue
            d = best[1]
            if class_of[d] == 'program':
                start, end = extend_cycle(i, off, merge_n[d])
            else:
                start, end = i, off
            dur = (end - start) * cad_s
            if not REL_DUR[0] * prof[d]['dur_s'] <= dur <= REL_DUR[1] * prof[d]['dur_s']:
                continue
            val = prof[d]['mean_w'] if class_of[d] == 'program' else amp
            seg = out[d][start:end]
            out[d][start:end] = np.maximum(seg, val)
        return out

    print('   rules v0 profiles: ' + '; '.join(
        f"{d} amp={prof[d]['amp']:.0f}W dur={prof[d]['dur_s'] / 60:.1f}min"
        for d in devices))
    return predict
