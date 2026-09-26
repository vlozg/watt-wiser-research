"""Rules + mining NILM (i26) on the v2 cycle protocol. Events are
level-excursion cycles: a step rise ends at the first fall whose post-
fall level returns to the pre-rise baseline (tol max(0.15x, 15 W)) -
this recovers kettle/microwave boils that first-fall pairing shredded
and compressor cycles that magnitude-stealing mispaired. Events are
mined from the PRE-span aggregate (unlabeled, mains only, FAQ-Q1 legal)
to pre-register bands; hour-scale chains are programs only if seed amp
is within +-20% of a wm/dw mark amp, the chain mean level is inside the
marks' own mean band [0.8x min, 1.25x max] (rejects flat 2 kW loads and
low-power junk), the chain span is inside the marks' span band, and the
event density matches the mark: the wm pump chatters ~0.4 events/min vs
the quiet dw ~0.03 (amplitude-identical heaters, calib-phase structure).
Burst/duty events classify against mark profiles; microwave-band events
inside named chains are suppressed (heater partial-duty draws mimic the
mw band); the fridge uses a mined duty cell only if it is regular
(cv <= 0.6); else its emission band is calibrated from the mined
small-sustained population (compressor-class window, amp <= 120 W):
the population's own p5/p95 amp/dur bands replace the thin passive-
window mark (3 pairs) whose amp sits below the true compressor mode.
Known limits: chain naming still amp/mean-gated (phase sequences i28b);
the population band still caps fridge recall at the extractor's
capture rate (~1/3 of compressor ON time). Pre-span rules only;
nothing is tuned on eval results."""
from __future__ import annotations

import numpy as np

BASE_N = 10            # mark-segment baseline samples (60 s)
SMOOTH_N = 5           # rolling-median smoothing (30 s at 6 s cadence)
STEP_H = 3             # +-18 s step-probe half window
AMP_MIN_W = 50.0
MAXSPAN_S = 7200.0
FALL_REL = (0.3, 3.0)  # pairing magnitude sanity gate
LEVEL_TOL = (0.15, 15.0)  # post-fall level-return tolerance (rel, abs W)
SPAN_ZERO_MAX = 0.5    # drop events whose span is mostly a recording gap
CHAIN_GAP_S = 600.0    # program chaining gap (= program merge_s)
PROG_SEED_FRAC = 0.5   # chain amp threshold (raw rolled p90) vs
# min(wm, dw) mark amp - raw, not event-based: the extractor misses
# heater blocks (4 of 9 marks) so an event-max seed would exclude them
PROG_MIN_S = 1800.0    # hour-scale chain
PROG_AMP_TOL = 0.20    # seed amp vs mark amp
PROG_DENS_HI = 0.75    # wm-like density floor vs wm marks' min density
PROG_DENS_LO = 2.0     # dw-like density ceiling vs dw marks' max density
PROG_HEAT_AMP_FRAC = 0.75  # program heat level vs min mark amp
PROG_HEAT_SHARE = 0.09     # min raw heat-time share of the chain span;
# extractor-independent: the level-return extractor misses heater blocks
# (4 of 9 marks show no heater-scale extracted event despite a ~2.2 kW
# core p90) while every mark's raw share is 0.120-0.405; a 2-min kettle
# boil in the shortest gated chain (31 min) is share 0.066 -> killed
PROG_SPAN_LO_WM = 0.35 # wm chain-span floor: soak pauses > the 600 s
# chain gap split the eventful part, and the GT protocol (merge 600 s)
# splits at the SAME boundary, so wm fragments are GT granularity
PROG_SPAN_LO_DW = 0.60 # dw floor: dw junk cluster sits at 0.35-0.55x
PROG_SPAN_HI = 1.25    # span ceiling vs max mark span
DUTY_AMP_W = (40.0, 300.0)
DUTY_DUR_S = (600.0, 2400.0)
DUTY_CELL_MIN = 300    # min events per (amp, dur) cell over the mined span
DUTY_CV_MAX = 0.6      # require regular (thermostat-like) recycling
FR_POP_AMP_HI = 120.0  # fallback population amp cap: domestic fridge
# compressor draw; keeps the mined compressor mode and excludes the
# sustained 95-300 W tail (laptops, heaters) that corrupts percentiles
FR_POP_MIN = 300       # min fallback-population events to calibrate a band
BURST_CLUSTER_MIN = 50  # mined burst cluster needed for a dur reference
REL_AMP = 0.20
REL_DUR = (1.0 / 3.0, 3.0)


def _roll_median(x: np.ndarray, n: int) -> np.ndarray:
    pad = n // 2
    xp = np.pad(x, pad, mode='edge')
    win = np.lib.stride_tricks.sliding_window_view(xp, n)
    return np.median(win, axis=1).astype('float32')


def _runs(on: np.ndarray):
    d = np.diff(np.concatenate([[0], on.astype(np.int8), [0]]))
    return list(zip(np.flatnonzero(d == 1).tolist(),
                    np.flatnonzero(d == -1).tolist()))


def _extract_events(sig: np.ndarray, cad_s: float):
    """Level-excursion events: a rise (> AMP_MIN_W over +-18 s) ends at
    the FIRST fall within MAXSPAN_S whose magnitude is within FALL_REL of
    the rise AND whose post-fall level returns to the pre-rise baseline
    within max(rel x amp, abs) - the physical end of the excursion.
    Intervening small steps (fridge off during a boil) no longer shred
    events, and far-future same-magnitude falls cannot steal them.
    Events whose span is mostly a recording gap are dropped."""
    n = len(sig)
    fut = np.concatenate([sig[STEP_H:], np.full(STEP_H, sig[-1])])
    past = np.concatenate([np.full(STEP_H, sig[0]), sig[:-STEP_H]])
    stp = fut - past
    is_rise = stp > AMP_MIN_W
    is_fall = stp < -AMP_MIN_W
    r_idx = np.flatnonzero(is_rise & ~np.concatenate([[False], is_rise[:-1]]))
    f_idx = np.flatnonzero(is_fall & ~np.concatenate([[False], is_fall[:-1]]))
    base_roll = _roll_median(sig, 11)
    zc = np.cumsum(sig <= 0.5, dtype=np.int32)
    on_l, off_l, amp_l = [], [], []
    for i in r_idx.tolist():
        a = float(stp[i])
        b = float(base_roll[max(i - 6, 0)])
        tol = max(LEVEL_TOL[0] * a, LEVEL_TOL[1])
        j0 = int(np.searchsorted(f_idx, i + STEP_H))
        j1 = int(np.searchsorted(f_idx, i + MAXSPAN_S / cad_s, side='right'))
        if j0 >= j1:
            continue
        idx = f_idx[j0:j1]
        mags = -stp[idx]
        ok = ((mags >= FALL_REL[0] * a) & (mags <= FALL_REL[1] * a)
              & (np.abs(sig[np.minimum(idx + STEP_H, n - 1)] - b) <= tol))
        if not ok.any():
            continue
        jb = int(idx[int(np.flatnonzero(ok)[0])])
        if jb - i > 0 and (int(zc[jb]) - int(zc[i])) / (jb - i) > SPAN_ZERO_MAX:
            continue
        on_l.append(i)
        off_l.append(jb)
        amp_l.append(a)
    return (np.asarray(on_l, dtype=np.int64),
            np.asarray(off_l, dtype=np.int64),
            np.asarray(amp_l, dtype=np.float64))


def _chains(ev_on: np.ndarray, ev_off: np.ndarray, mg: int):
    """[a0, a1) slices of maximal event chains: consecutive events with
    gap (next on - prev off) <= mg samples join one chain. O(N) pass."""
    out = []
    a0 = 0
    n = len(ev_on)
    for i in range(1, n + 1):
        if i == n or ev_on[i] - ev_off[i - 1] > mg:
            out.append((a0, i))
            a0 = i
    return out


def _pband(vals: np.ndarray):
    if len(vals) == 0:
        return (0.0, 0.0)
    return (float(np.percentile(vals, 5)), float(np.percentile(vals, 95)))


def _profile_from_marks(cal: dict, cad_s: float, roll_s: float,
                        dev_class: str, dev: str = '') -> dict:
    """Amplitude/duration/mean-power profile from calibration marks only.
    Marks carry a pre/post roll: non-passive stats use the rolled-off
    core. Amplitude per class: burst = ON-plateau median, program = p90
    (heater level), duty/passive = recurring rise/fall pairs 10-40 min
    apart with matched amplitude (the compressor)."""
    if cal['passive'] or dev_class == 'duty':
        w = cal['mains_seg'][0].astype('float64')
        base = float(np.percentile(w, 20))
        fut = np.concatenate([w[STEP_H:], np.full(STEP_H, w[-1])])
        past = np.concatenate([np.full(STEP_H, w[0]), w[:-STEP_H]])
        stp = fut - past

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
    amps, durs, means, dens = [], [], [], []
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
    prof = {'amp': float(np.median(amps)), 'dur_s': float(np.median(durs)),
            'mean_w': float(np.median(means))}
    if dev_class == 'program':
        # Phase structure from the same marks: event density separates
        # the pump-chattering wm (~0.4 events/min) from the quiet dw
        # (~0.03); mean/span bands come from the marks' own spread.
        for seg in cal['mains_seg']:
            sig = _roll_median(seg.astype('float32'), SMOOTH_N)
            on, off, amp = _extract_events(sig, cad_s)
            dens.append(len(on) / (len(seg) * cad_s / 60.0))
        prof['dens_band'] = (min(dens), max(dens))
        prof['mean_band'] = (0.8 * min(means), 1.25 * max(means))
        # the chain span runs first-event to last-event and can miss the
        # program's quiet tail (dw marks put the heater at ~0.19 of the
        # span with sparse late events); the wm floor is lower still
        # because soak pauses split wm chains at the GT merge boundary
        lo = PROG_SPAN_LO_WM if dev == 'washing_machine' else PROG_SPAN_LO_DW
        prof['span_band'] = (lo * min(durs), PROG_SPAN_HI * max(durs))
    return prof


def _name_program(seed_amp: float, span_s: float, mean_lvl: float,
                  density: float, heat_share: float, mark: dict):
    """Name an hour-scale chain. Gates from the calib marks only: chain
    amp (raw rolled p90 over the chain span - the same statistic the
    marks' amp uses) within +-20% of the mark amp, chain mean inside
    the marks' own mean band [0.8x min, 1.25x max], chain span inside
    the marks' span
    band, and raw heat-time (level >= 0.75x mark amp) over >= 9% of the
    chain span - a kettle boil is 2 min in a >= 31 min chain (<= 6.6%)
    and cannot seed a program name. The mean bands overlap (wm floor 440 W < dw ceiling
    698 W), so when both marks admit a chain the disjoint density
    bands decide: the wm pump chatters (marks 0.34-0.68 events/min)
    vs the quiet dw (0.02-0.05) - dw-quiet <= 2x the dw mark max,
    wm-chattery >= 0.75x the wm mark min, else unnamed."""
    if heat_share < PROG_HEAT_SHARE:
        return None
    ok = []
    for d in ('washing_machine', 'dishwasher'):
        p = mark[d]
        if abs(seed_amp - p['amp']) / p['amp'] > PROG_AMP_TOL:
            continue
        if not p['mean_band'][0] <= mean_lvl <= p['mean_band'][1]:
            continue
        if not p['span_band'][0] <= span_s <= p['span_band'][1]:
            continue
        ok.append(d)
    if len(ok) == 1:
        return ok[0]
    if len(ok) == 2:
        # both marks admit the chain (the mean bands overlap 440-698 W):
        # the disjoint density bands decide
        if density <= PROG_DENS_LO * mark['dishwasher']['dens_band'][1]:
            return 'dishwasher'
        if density >= PROG_DENS_HI * mark['washing_machine']['dens_band'][0]:
            return 'washing_machine'
    return None


def build_and_train(ctx: dict):
    meta = ctx['meta']
    devices = meta['devices']
    cad_s = float(meta['cadence_us']) / 1e6
    class_of = meta['device_class']
    mg = int(round(meta['merge_s']['washing_machine'] / cad_s))
    roll_s = float(meta.get('pre_roll_s', 0.0))
    mark = {d: _profile_from_marks(ctx['calib'][d], cad_s, roll_s,
                                   class_of[d], d)
            for d in devices}
    print('   mark profiles: ' + '; '.join(
        f"{d} amp={mark[d]['amp']:.0f}W dur={mark[d]['dur_s'] / 60:.1f}min "
        f"mean={mark[d]['mean_w']:.0f}W"
        + (f" dens={mark[d]['dens_band'][0]:.2f}-{mark[d]['dens_band'][1]:.2f}/min"
           if 'dens_band' in mark[d] else '') for d in devices))
    seed_thr = PROG_SEED_FRAC * min(mark['washing_machine']['amp'],
                                    mark['dishwasher']['amp'])
    heat_thr = PROG_HEAT_AMP_FRAC * min(mark['washing_machine']['amp'],
                                        mark['dishwasher']['amp'])

    # ---- mine the PRE-span aggregate (unlabeled, mains only) ----
    sig = _roll_median(np.asarray(ctx['pre']['mains'], dtype='float32'),
                       SMOOTH_N)
    ev_on, ev_off, ev_amp = _extract_events(sig, cad_s)
    ev_dur = (ev_off - ev_on) * cad_s
    days = len(sig) * cad_s / 86400
    print(f'   mined {len(ev_on)} level-excursion events from {days:.0f} '
          'pre-span days')

    # mined burst dur references: p50 dur of events in each mark amp band
    dur_ref = {}
    for d in ('kettle', 'microwave'):
        p = mark[d]
        m = np.abs(ev_amp - p['amp']) / p['amp'] <= REL_AMP
        if int(m.sum()) >= BURST_CLUSTER_MIN:
            dur_ref[d] = float(np.percentile(ev_dur[m], 50))
            print(f'   mined {d} cluster: n={int(m.sum())} '
                  f'dur_p50={dur_ref[d] / 60:.1f}min (mark '
                  f'{p["dur_s"] / 60:.1f}min)')
        else:
            dur_ref[d] = p['dur_s']

    # program chains in the mined stream (structure check)
    prog_named = {'washing_machine': 0, 'dishwasher': 0}
    prog_total = 0
    br_sig = _roll_median(sig, 11)
    for a0, a1 in _chains(ev_on, ev_off, mg):
        s_i, e_i = ev_on[a0], ev_off[a1 - 1]
        span = float((e_i - s_i) * cad_s)
        br = float(br_sig[max(s_i - 6, 0)])
        # amp reference = raw rolled p90 over the chain span, the same
        # statistic the marks' amp is computed from; the extractor's
        # event max misses heater blocks (4 of 9 marks)
        p90 = float(np.percentile(sig[s_i:e_i], 90)) - br
        if p90 < seed_thr or span < PROG_MIN_S:
            continue
        prog_total += 1
        lvl = float(sig[s_i:e_i].mean()) - br
        dens = (a1 - a0) / (span / 60.0)
        hshare = float((sig[s_i:e_i] >= heat_thr).mean())
        d = _name_program(p90, span, lvl, dens, hshare, mark)
        if d is not None:
            prog_named[d] += 1
    print(f'   mined program chains: {prog_total} pass structure, named '
          f'wm={prog_named["washing_machine"]} dw={prog_named["dishwasher"]}')

    # fridge: most-regular (amp x dur) duty cell among mined events
    dm = ((ev_amp >= DUTY_AMP_W[0]) & (ev_amp <= DUTY_AMP_W[1])
          & (ev_dur >= DUTY_DUR_S[0]) & (ev_dur <= DUTY_DUR_S[1]))
    fridge_band = None
    if int(dm.sum()) >= DUTY_CELL_MIN:
        cells: dict = {}
        for k in np.flatnonzero(dm):
            key = (int(ev_amp[k] // 10.0), int(ev_dur[k] // 300.0))
            cells.setdefault(key, []).append(int(k))
        cand = []
        for ks in cells.values():
            if len(ks) < DUTY_CELL_MIN:
                continue
            ks = np.asarray(ks, dtype=np.int64)
            a50 = float(np.percentile(ev_amp[ks], 50))
            d50 = float(np.percentile(ev_dur[ks], 50))
            iv = np.diff(np.sort(ev_on[ks])) * cad_s
            cv = (float(iv.std() / iv.mean())
                  if len(iv) >= 3 and iv.mean() > 0 else 9.9)
            cand.append((cv, a50, d50, ks))
        cand.sort(key=lambda t: t[0])
        if cand and cand[0][0] <= DUTY_CV_MAX:
            cv, a50, _, ks = cand[0]
            n_cell = len(ks)
            fridge_band = {'amp': _pband(ev_amp[ks]),
                           'dur': _pband(ev_dur[ks]), 'n': n_cell, 'cv': cv}
            print(f'   fridge mined cell: a50={a50:.0f}W '
                  f'amp_band={fridge_band["amp"][0]:.0f}-'
                  f'{fridge_band["amp"][1]:.0f}W '
                  f'dur_band={fridge_band["dur"][0] / 60:.0f}-'
                  f'{fridge_band["dur"][1] / 60:.0f}min n={n_cell} cv={cv:.3f}')
    if fridge_band is None:
        # no regular cell: calibrate the emission band from the mined
        # small-sustained population itself (compressor-class window,
        # amp capped at FR_POP_AMP_HI). The passive-window mark rests on
        # 3 pairs whose amp sits below the population mode.
        fpop = dm & (ev_amp <= FR_POP_AMP_HI)
        if int(fpop.sum()) >= FR_POP_MIN:
            fridge_band = {'amp': _pband(ev_amp[fpop]),
                           'dur': _pband(ev_dur[fpop]),
                           'n': int(fpop.sum())}
            print(f'   fridge fallback: population band '
                  f'amp={fridge_band["amp"][0]:.0f}-'
                  f'{fridge_band["amp"][1]:.0f}W '
                  f'dur={fridge_band["dur"][0] / 60:.0f}-'
                  f'{fridge_band["dur"][1] / 60:.0f}min '
                  f'n={fridge_band["n"]}')
        else:
            print('   fridge mined cell: none regular enough; '
                  'fallback = passive-window pairs')

    def predict(filled) -> dict:
        f = np.asarray(filled, dtype='float32')
        sig = _roll_median(f, SMOOTH_N)
        base_roll = _roll_median(sig, 11)
        on, off, amp = _extract_events(sig, cad_s)
        out = {d: np.zeros(len(f), dtype='float32') for d in devices}
        if len(on) == 0:
            return out
        dur = (off - on) * cad_s

        # 1) program chains emit spans; their events stay burst-eligible
        ev_in_named = np.zeros(len(on), dtype=bool)
        for a0, a1 in _chains(on, off, mg):
            s_i, e_i = on[a0], off[a1 - 1]
            span = float((e_i - s_i) * cad_s)
            br = float(base_roll[max(s_i - 6, 0)])
            p90 = float(np.percentile(sig[s_i:e_i], 90)) - br
            if p90 < seed_thr or span < PROG_MIN_S:
                continue
            lvl = float(sig[s_i:e_i].mean()) - br
            dens = (a1 - a0) / (span / 60.0)
            hshare = float((sig[s_i:e_i] >= heat_thr).mean())
            d = _name_program(p90, span, lvl, dens, hshare, mark)
            if d is None:
                continue
            out[d][on[a0]:off[a1 - 1]] = mark[d]['mean_w']
            ev_in_named[a0:a1] = True

        # 2) every event classifies independently (burst / duty bands).
        # Program heaters emit partial-duty draws (amp 1.3-1.9 kW) inside
        # named chains that mimic the microwave band - suppress mw there.
        # Kettle is separated by duration, fridge by amplitude, so their
        # classification stays chain-blind.
        p = mark['kettle']
        dr = dur_ref.get('kettle', p['dur_s'])
        ok = ((np.abs(amp - p['amp']) / p['amp'] <= REL_AMP)
              & (dur >= REL_DUR[0] * dr) & (dur <= REL_DUR[1] * dr))
        for k in np.flatnonzero(ok):
            i0 = int(k)
            seg = out['kettle'][on[i0]:off[i0]]
            out['kettle'][on[i0]:off[i0]] = np.maximum(seg, amp[i0])
        # microwave: the mark window is the GT cycle span plus fixed 60 s
        # pre/post rolls (calibration protocol), so the rolled-off mark
        # core IS the cycle and dur_s is its median length. The mark
        # events are sustained 0.6-0.8 min excursions, so emit the event
        # span itself gated on the event duration (same REL_DUR band as
        # every burst device): duty-chunked heater lookalikes live in
        # 100-400 s events whose 30-60 s plateaus pass a run-level gate
        # but whose event duration fails this one.
        p = mark['microwave']
        mw_dr = p['dur_s']
        ok = ((np.abs(amp - p['amp']) / p['amp'] <= REL_AMP)
              & ~ev_in_named
              & (dur >= REL_DUR[0] * mw_dr) & (dur <= REL_DUR[1] * mw_dr))
        for k in np.flatnonzero(ok):
            i0 = int(k)
            seg = out['microwave'][on[i0]:off[i0]]
            out['microwave'][on[i0]:off[i0]] = np.maximum(seg, amp[i0])
        if fridge_band is not None:
            ok = ((amp >= fridge_band['amp'][0])
                  & (amp <= fridge_band['amp'][1])
                  & (dur >= fridge_band['dur'][0])
                  & (dur <= fridge_band['dur'][1]))
        else:
            p = mark['fridge']
            ok = ((np.abs(amp - p['amp']) / p['amp'] <= REL_AMP)
                  & (dur >= REL_DUR[0] * p['dur_s'])
                  & (dur <= REL_DUR[1] * p['dur_s']))
        for k in np.flatnonzero(ok):
            i0 = int(k)
            seg = out['fridge'][on[i0]:off[i0]]
            out['fridge'][on[i0]:off[i0]] = np.maximum(seg, amp[i0])
        return out

    return predict
