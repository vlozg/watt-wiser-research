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
capture rate (~1/3 of compressor ON time). Dishwasher cycles come from
a sustained-run detector on a 30 s grid: the dw marks hold 2-5 events
per ~100 min cycle (60-110 W pump draws, heater blocks ~54-58 min
apart) so event chaining cannot assemble a dw cycle - the marks
themselves fail the chain detector - and the dw idle sits below the
swinging house base. The detector merges heater plateaus (>= 0.75x min
mark amp) across 1.25x the marks' own max heater gap and gates the
merged run on mark-derived run-basis bands (span/amp/mean/heat-share/
idle-level/density). The chain detector keeps naming wm only: dw chain
names drop when the sustained path is active, and a chattery chain that
only the dw gates admit is junk by the marks' own quiet density.
Pre-span rules only; nothing is tuned on eval results."""
from __future__ import annotations

import numpy as np
import pandas as pd

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
# --- dw sustained-run detector (30 s grid) ---
# The dw calibration marks hold only 2-5 events per ~100 min cycle: tiny
# 60-110 W pump draws with heater blocks 54-58 min apart (wash heater,
# then final-rinse heater), so event chaining at the 600 s program gap
# cannot assemble a dw cycle - the marks themselves fail the chain
# detector. The dw idle draw is equally invisible: 60-110 W sits below
# the 150-500 W swinging house base, and any local baseline absorbs it
# (the mark runs' non-heater median is 0-72 W above a trailing p10).
# What IS visible is the raw heater signature, so dw detection merges
# heater-level plateaus on a coarse grid and gates the merged run.
DW30_GRID_S = 30.0     # coarse grid for the sustained-run detector
KET_MARK_MIN = 3       # kettle marks that must hold an isolated run
KET_ISO_AMP_W = 1000.0  # other-run level that breaks kettle isolation
KET_ISO_WIN_S = 600.0  # +- window for the kettle isolation test
DW_BASE_WIN = 240      # 2 h trailing p10 baseline: a single ~100 min dw
                       # cycle is ~8% of the window, so it cannot absorb
                       # the baseline the way shorter windows would
DW_BASE_MIN = 120      # min baseline samples before it is trusted
DW_RUN_MIN_S = 1200.0  # ignore heater runs < 20 min (cooking bursts);
                       # the marks' merged runs are 76-81.5 min
FFILL_LIMIT = 10       # frozen bench protocol: max mains gap ffill
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


def _dw30_grid(mains: np.ndarray, cad_s: float) -> np.ndarray:
    """Excitation signal on the DW30_GRID_S grid: smooth, downsample,
    subtract a trailing 2 h p10 baseline (bfilled over the head). The
    baseline is deliberately a LOW quantile over a LONG window - shorter
    or median baselines flip to the dw's own idle level whenever local
    duty exceeds their quantile share (i29 lesson on rolling medians)."""
    s6 = pd.Series(mains).ffill(limit=FFILL_LIMIT).fillna(0.0)
    sig6 = _roll_median(s6.to_numpy(dtype='float32'), SMOOTH_N)
    stride = max(1, int(round(DW30_GRID_S / cad_s)))
    sig30 = _roll_median(sig6, stride)[::stride]
    base = (pd.Series(sig30).rolling(DW_BASE_WIN, min_periods=DW_BASE_MIN)
            .quantile(0.10).bfill().to_numpy())
    return np.nan_to_num(sig30 - base, nan=0.0).astype('float32')


def _merge_runs(runs, gap_n: int):
    out = []
    for a, b in runs:
        if out and a - out[-1][1] <= gap_n:
            out[-1] = (out[-1][0], b)
        else:
            out.append((a, b))
    return out


def _iso_clear(exc: np.ndarray, a: int, b: int, iso_amp: float,
               iso_win: float) -> bool:
    """True when no run >= iso_amp falls within +-iso_win s of the run
    [a, b) on the coarse grid (the run's own excitation extent does not
    count against it)."""
    pad = int(iso_win / DW30_GRID_S) + 2
    k0 = max(0, a - pad)
    k1 = min(len(exc), b + pad)
    a_s = a * DW30_GRID_S
    b_s = b * DW30_GRID_S
    for c, d in _runs(exc[k0:k1] >= iso_amp):
        c_s = (k0 + c) * DW30_GRID_S
        d_s = (k0 + d) * DW30_GRID_S
        if d_s <= a_s or c_s >= b_s:
            if d_s > a_s - iso_win and c_s < b_s + iso_win:
                return False
    return True


def _dw30_runs(exc: np.ndarray, ev30_sorted: np.ndarray, prof: dict) -> list:
    """Merged heater runs passing the mark-derived run-basis gates (see
    _dw30_profile). A run is heater plateaus (exc >= heat) merged across
    gaps <= merge_n grid steps; each candidate is gated on span, heater
    p90, mean level, heat-time share, idle level (median exc below the
    heater threshold) and extracted-event density - the density gate is
    what separates the quiet dw from the chattering wm (a ceiling for
    dw; when the profile carries 'dens_lo', also a floor for wm so
    quiet heater lookalikes fail). Returns [a, b) grid-step pairs."""
    out = []
    mask = exc >= prof['heat']
    if not mask.any():
        return out
    for a, b in _merge_runs(_runs(mask), prof['merge_n']):
        span_s = (b - a) * DW30_GRID_S
        if span_s < DW_RUN_MIN_S:
            continue
        if not prof['span_band'][0] <= span_s <= prof['span_band'][1]:
            continue
        seg = exc[a:b]
        if float(np.percentile(seg, 90)) < prof['amp_lo']:
            continue
        mean = float(seg.mean())
        if not prof['mean_band'][0] <= mean <= prof['mean_band'][1]:
            continue
        hs = float((seg >= prof['heat']).mean())
        if not prof['hs_band'][0] <= hs <= prof['hs_band'][1]:
            continue
        below = seg[seg < prof['heat']]
        idle = float(np.median(below)) if len(below) else 0.0
        if idle > prof['idle_hi']:
            continue
        ne = (int(np.searchsorted(ev30_sorted, b))
              - int(np.searchsorted(ev30_sorted, a)))
        dens = ne / (span_s / 60.0)
        if dens > prof['dens_hi']:
            continue
        if 'dens_lo' in prof and dens < prof['dens_lo']:
            continue
        out.append((a, b))
    return out


def _dw30_profile(exc: np.ndarray, cal: dict, mark_dw: dict,
                  wm_amp: float, roll_s: float, ev30_sorted: np.ndarray,
                  t0_us: int, cad_s: float):
    """Derive the dw run-basis gate bands from the calibration marks on
    the 30 s grid. Every mark window must produce a merged heater run;
    the runs' own stats (span, heater p90, mean level, heat-time share,
    idle median, event density) set the bands with the same margin
    conventions as _profile_from_marks (0.6/1.25 span, 0.8/1.25 mean,
    0.75/1.75 heat share, 2x ceilings for idle and density). The heater
    merge gap is 1.25x the marks' own max intra-window heater gap. The
    emission extension is half the gap between the marks' GT-core span
    (window minus the roll pads) and their run span: the run starts at
    the first heater block while the GT cycle starts at the mask rise,
    so a symmetric extension keeps onsets inside the 600 s matching
    tolerance while bringing the emitted span back to the cycle length."""
    heat = PROG_HEAT_AMP_FRAC * min(wm_amp, mark_dw['amp'])
    per = []
    max_gap = 0.0
    for lo_us, hi_us in cal['marks_us']:
        j0 = max(0, int((lo_us - t0_us) / 1e6 / DW30_GRID_S))
        j1 = max(j0 + 2, int((hi_us - t0_us) / 1e6 / DW30_GRID_S))
        blocks = _runs(exc[j0:j1] >= heat)
        if not blocks:
            print('   dw sustained profile: a mark window has no heater '
                  'blocks; sustained detector disabled')
            return None
        for k in range(len(blocks) - 1):
            max_gap = max(max_gap, (blocks[k + 1][0] - blocks[k][1])
                          * DW30_GRID_S)
        per.append((j0, j1))
    if max_gap > 0:
        merge_n = max(1, int(round(1.25 * max_gap / DW30_GRID_S)))
    else:
        merge_n = int(round(4200.0 / DW30_GRID_S))
    spans, p90s, means, hss, idles, denss = [], [], [], [], [], []
    for (lo_us, hi_us), (j0, j1) in zip(cal['marks_us'], per):
        merged = _merge_runs(_runs(exc[j0:j1] >= heat), merge_n)
        a, b = max(merged, key=lambda r: r[1] - r[0])
        seg = exc[j0 + a:j0 + b]
        span_s = (b - a) * DW30_GRID_S
        below = seg[seg < heat]
        ne = (int(np.searchsorted(ev30_sorted, float(j0 + b)))
              - int(np.searchsorted(ev30_sorted, float(j0 + a))))
        spans.append(span_s)
        p90s.append(float(np.percentile(seg, 90)))
        means.append(float(seg.mean()))
        hss.append(float((seg >= heat).mean()))
        idles.append(float(np.median(below)) if len(below) else 0.0)
        denss.append(ne / (span_s / 60.0))
    cycle_s = [(hi_us - lo_us) / 1e6 - 2.0 * roll_s
               for lo_us, hi_us in cal['marks_us']]
    ext_s = max(0.0, 0.5 * (float(np.mean(cycle_s))
                            - float(np.mean(spans))))
    prof = {'heat': heat,
            'merge_n': merge_n,
            'span_band': (0.6 * min(spans), 1.25 * max(spans)),
            'amp_lo': min(p90s),
            'mean_band': (0.8 * min(means), 1.25 * max(means)),
            'hs_band': (0.75 * min(hss), 1.75 * max(hss)),
            'idle_hi': 2.0 * max(idles),
            'dens_hi': 2.0 * max(denss),
            'ext6': int(round(ext_s / cad_s)),
            'emit_w': mark_dw['mean_w']}
    print('   dw sustained profile: span=%.0f-%.0fmin amp>=%.0fW '
          'mean=%.0f-%.0fW hs=%.2f-%.2f idle<=%.0fW dens<=%.3f/min '
          'heater_gap_merge=%dmin ext=%.1fmin'
          % (prof['span_band'][0] / 60, prof['span_band'][1] / 60,
             prof['amp_lo'], prof['mean_band'][0], prof['mean_band'][1],
             prof['hs_band'][0], prof['hs_band'][1], prof['idle_hi'],
             prof['dens_hi'], merge_n * DW30_GRID_S / 60, ext_s / 60))
    return prof


def _wm30_profile(exc: np.ndarray, cal: dict, mark_wm: dict,
                  dw_amp: float, roll_s: float, ev30_sorted: np.ndarray,
                  t0_us: int, cad_s: float):
    """Derive the wm run-basis gate bands from the calibration marks on
    the 30 s grid (same margin conventions as _dw30_profile: 0.6/1.25
    span, 0.8/1.25 mean, 0.75/1.75 heat share, 2x ceilings for idle and
    density). Two wm-specific differences. (1) A density FLOOR at 0.75x
    the marks' min run density: the wm pump chatter (400-700 W draws
    every 1-3 min inside the cycle) is what separates a wm heater
    sequence from quiet heater lookalikes - dw30 runs sit at <=0.184
    events/min while the wm mark runs hold 0.27-0.58/min, so the floor
    rejects every dw30 run by construction. (2) The emission extension
    is ASYMMETRIC: the wm heats at the very start of the cycle (the
    mark runs begin ~3 min after the GT mask rise) but keeps pumping
    below the heater threshold for ~45 min after the heater ends, so
    the run needs a small back-extension to the mask rise and a large
    forward one to the cycle end - the dw30 symmetric half-gap
    extension would place the onset half a cycle early. The merge gap
    is 1.25x the marks' max intra-window heater gap."""
    heat = PROG_HEAT_AMP_FRAC * min(mark_wm['amp'], dw_amp)
    pad_n = int(round(roll_s / DW30_GRID_S))
    per = []
    max_gap = 0.0
    for lo_us, hi_us in cal['marks_us']:
        j0 = max(0, int((lo_us - t0_us) / 1e6 / DW30_GRID_S))
        j1 = max(j0 + 2, int((hi_us - t0_us) / 1e6 / DW30_GRID_S))
        blocks = _runs(exc[j0:j1] >= heat)
        if not blocks:
            print('   wm sustained profile: a mark window has no heater '
                  'blocks; sustained detector disabled')
            return None
        for k in range(len(blocks) - 1):
            max_gap = max(max_gap, (blocks[k + 1][0] - blocks[k][1])
                          * DW30_GRID_S)
        per.append((j0, j1))
    if max_gap > 0:
        merge_n = max(1, int(round(1.25 * max_gap / DW30_GRID_S)))
    else:
        merge_n = int(round(4200.0 / DW30_GRID_S))
    spans, p90s, means, hss, idles, denss, oss, oes = (
        [], [], [], [], [], [], [], [])
    for j0, j1 in per:
        a, b = max(_merge_runs(_runs(exc[j0:j1] >= heat), merge_n),
                   key=lambda r: r[1] - r[0])
        seg = exc[j0 + a:j0 + b]
        span_s = (b - a) * DW30_GRID_S
        below = seg[seg < heat]
        ne = (int(np.searchsorted(ev30_sorted, float(j0 + b)))
              - int(np.searchsorted(ev30_sorted, float(j0 + a))))
        spans.append(span_s)
        p90s.append(float(np.percentile(seg, 90)))
        means.append(float(seg.mean()))
        hss.append(float((seg >= heat).mean()))
        idles.append(float(np.median(below)) if len(below) else 0.0)
        denss.append(ne / (span_s / 60.0))
        # run offsets inside the GT cycle core (window minus the roll
        # pads): run start vs core start, core end vs run end - the
        # emission extension targets
        oss.append((a - pad_n) * DW30_GRID_S)
        oes.append((j1 - pad_n - j0 - b) * DW30_GRID_S)
    ext_back_s = float(np.mean(oss))
    ext_fwd_s = float(np.mean(oes))
    prof = {'heat': heat,
            'merge_n': merge_n,
            'span_band': (0.6 * min(spans), 1.25 * max(spans)),
            'amp_lo': min(p90s),
            'mean_band': (0.8 * min(means), 1.25 * max(means)),
            'hs_band': (0.75 * min(hss), 1.75 * max(hss)),
            'idle_hi': 2.0 * max(idles),
            'dens_hi': 2.0 * max(denss),
            'dens_lo': 0.75 * min(denss),
            'ext_back6': int(round(ext_back_s / cad_s)),
            'ext_fwd6': int(round(ext_fwd_s / cad_s)),
            'emit_w': mark_wm['mean_w']}
    print('   wm sustained profile: span=%.0f-%.0fmin amp>=%.0fW '
          'mean=%.0f-%.0fW hs=%.2f-%.2f idle<=%.0fW dens=%.3f-%.3f/min '
          'heater_gap_merge=%dmin ext_back=%.1fmin ext_fwd=%.1fmin'
          % (prof['span_band'][0] / 60, prof['span_band'][1] / 60,
             prof['amp_lo'], prof['mean_band'][0], prof['mean_band'][1],
             prof['hs_band'][0], prof['hs_band'][1], prof['idle_hi'],
             prof['dens_lo'], prof['dens_hi'],
             merge_n * DW30_GRID_S / 60, ext_back_s / 60, ext_fwd_s / 60))
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
        if (ok[0] == 'dishwasher'
                and density > PROG_DENS_LO
                * mark['dishwasher']['dens_band'][1]):
            # dw marks are quiet (0.012-0.092 events/min): a chattery
            # chain that fails the wm gates is junk, not a dw cycle
            return None
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

    # dw sustained-run detector: profile derived from the marks on the
    # 30 s grid, then the pre-span mining print (structure check)
    stride = max(1, int(round(DW30_GRID_S / cad_s)))
    ev30 = np.sort(ev_on // stride)
    exc30 = _dw30_grid(np.asarray(ctx['pre']['mains'], dtype='float32'),
                       cad_s)
    dw30 = _dw30_profile(exc30, ctx['calib']['dishwasher'],
                         mark['dishwasher'], mark['washing_machine']['amp'],
                         roll_s, ev30, int(ctx['pre']['ts_us'][0]), cad_s)
    if dw30 is not None:
        dw_runs = _dw30_runs(exc30, ev30, dw30)
        print(f'   dw sustained runs: {len(dw_runs)} pass run-basis '
              f'gates ({len(dw_runs) / days:.3f}/day)')

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
    named_spans = []  # spans claimed by a program name (wm/dw territory)
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
        if d == 'dishwasher' and dw30 is not None:
            d = None  # the sustained-run detector owns dw
        if d is not None:
            prog_named[d] += 1
            named_spans.append((s_i, e_i))
    print(f'   mined program chains: {prog_total} pass structure, named '
          f'wm={prog_named["washing_machine"]} dw={prog_named["dishwasher"]}')
    if dw30 is None:
        print('   dw sustained detector disabled (mark windows produced '
              'no heater runs)')

    # wm sustained-run detector: the wm marks' heater blocks fuse into
    # one run per cycle at the mark-derived merge; gated like the dw
    # runs plus the pump-chatter density floor, with the ASYMMETRIC
    # emission extension (the wm heats at the cycle start, then pumps
    # below the heater threshold ~45 min). Candidates inside dw30 runs
    # or a named program chain are already owned.
    wm30 = _wm30_profile(exc30, ctx['calib']['washing_machine'],
                         mark['washing_machine'],
                         mark['dishwasher']['amp'], roll_s, ev30,
                         int(ctx['pre']['ts_us'][0]), cad_s)
    if wm30 is not None:
        dw_spans6 = ([(a * stride, b * stride) for a, b in dw_runs]
                     if dw30 is not None else [])
        wm_cands = []
        for a, b in _dw30_runs(exc30, ev30, wm30):
            a6, b6 = a * stride, b * stride
            if any(c0 < b6 and a6 < c1 for c0, c1 in dw_spans6):
                continue
            dup = False
            for c0, c1 in named_spans:
                if c0 < b6 and a6 < c1:
                    dup = True
                    break
            if dup:
                continue
            wm_cands.append((a6, b6))
        print(f'   wm sustained runs: {len(wm_cands)} net-new '
              f'candidates ({len(wm_cands) / days:.3f}/day)')

    # kettle sustained-run detector: a real kettle draw is one isolated
    # flat run on the coarse grid - thr = 0.75x mark amp (the dw run
    # convention), span inside the burst REL_DUR band of the mark dur,
    # run-mean excitation inside the mark REL_AMP band. All five mark
    # windows show no other >=1 kW run within +-10 min, so the
    # isolation gate is mark-supported; draws stacked on other loads
    # inflate the run mean past the amp band (3 of 5 mark runs sit at
    # 3.3-4.2 kW), leaving those to the event path. The run path only
    # ADDS draws whose rise/fall pairing broke (mid-draw level
    # changes), i.e. runs no admitted burst event overlaps.
    ket = mark['kettle']
    ket_thr = PROG_HEAT_AMP_FRAC * ket['amp']
    ket_span = (REL_DUR[0] * ket['dur_s'], REL_DUR[1] * ket['dur_s'])
    ket_amp_band = ((1.0 - REL_AMP) * ket['amp'],
                    (1.0 + REL_AMP) * ket['amp'])
    ket_ok = np.flatnonzero(
        (np.abs(ev_amp - ket['amp']) / ket['amp'] <= REL_AMP)
        & (ev_dur >= REL_DUR[0] * dur_ref['kettle'])
        & (ev_dur <= REL_DUR[1] * dur_ref['kettle']))
    t0 = int(ctx['pre']['ts_us'][0])
    ket_marks = 0
    for lo_us, hi_us in ctx['calib']['kettle']['marks_us']:
        j0 = max(0, int((lo_us - t0) / 1e6 / DW30_GRID_S))
        j1 = max(j0 + 2, int((hi_us - t0) / 1e6 / DW30_GRID_S))
        hit = False
        for a, b in _runs(exc30[j0:j1] >= ket_thr):
            if not ket_span[0] <= (b - a) * DW30_GRID_S <= ket_span[1]:
                continue
            if _iso_clear(exc30, j0 + a, j0 + b, KET_ISO_AMP_W,
                          KET_ISO_WIN_S):
                hit = True
                break
        ket_marks += int(hit)
    print(f'   kettle sustained marks: {ket_marks}/'
          f'{len(ctx["calib"]["kettle"]["marks_us"])} windows hold an '
          'isolated in-band run')
    ket_prof = None
    if ket_marks >= KET_MARK_MIN:
        cands = []
        for a, b in _runs(exc30 >= ket_thr):
            span_s = (b - a) * DW30_GRID_S
            if not ket_span[0] <= span_s <= ket_span[1]:
                continue
            mean_w = float(exc30[a:b].mean())
            if not ket_amp_band[0] <= mean_w <= ket_amp_band[1]:
                continue
            if not _iso_clear(exc30, a, b, KET_ISO_AMP_W, KET_ISO_WIN_S):
                continue
            a6 = a * stride
            b6 = b * stride
            k = int(np.searchsorted(ev_on[ket_ok], b6 - 1,
                                    side='right')) - 1
            if k >= 0 and ev_off[ket_ok[k]] > a6:
                continue
            dup = False
            for c0, c1 in named_spans:
                if c0 < b6 and a6 < c1:
                    dup = True
                    break
            if dup:
                continue
            cands.append((a6, b6, mean_w))
        print(f'   kettle sustained runs: {len(cands)} net-new '
              f'candidates ({len(cands) / days:.2f}/day)')
        ket_prof = {'thr': ket_thr, 'span_band': ket_span,
                    'amp_band': ket_amp_band, 'iso_amp': KET_ISO_AMP_W,
                    'iso_win': KET_ISO_WIN_S}

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

    # fridge run-basis gates: compressor draws below the extractor's amp
    # floor or with broken rise/fall pairing never become events; on the
    # coarse grid they are isolated flat runs inside the fridge band.
    # Run amp window 0.8x passive-mark amp (same lo margin as every mean
    # band) to the population amp top; isolation level 3x the mark amp -
    # the smallest session-ratio level above the band top (2.1x) - with
    # the kettle isolation window convention.
    if fridge_band is not None:
        fr_amp = mark['fridge']['amp']
        fridge_band['fr_run'] = {'amp_lo': 0.8 * fr_amp,
                                 'amp_hi': fridge_band['amp'][1],
                                 'iso_amp': 3.0 * fr_amp,
                                 'iso_win': KET_ISO_WIN_S}
        fr_ok = ((ev_amp >= fridge_band['amp'][0])
                 & (ev_amp <= fridge_band['amp'][1])
                 & (ev_dur >= fridge_band['dur'][0])
                 & (ev_dur <= fridge_band['dur'][1]))
        fr_on = ev_on[fr_ok] / stride
        fr_off = ev_off[fr_ok] / stride
        fr_cands = 0
        for a, b in _merge_runs(
                _runs((exc30 >= fridge_band['fr_run']['amp_lo'])
                      & (exc30 <= fridge_band['fr_run']['amp_hi'])), 1):
            span_s = (b - a) * DW30_GRID_S
            if not fridge_band['dur'][0] <= span_s \
                    <= fridge_band['dur'][1]:
                continue
            if not _iso_clear(exc30, a, b, fridge_band['fr_run']['iso_amp'],
                              fridge_band['fr_run']['iso_win']):
                continue
            k = int(np.searchsorted(fr_on, b, side='left')) - 1
            if k >= 0 and fr_off[k] > a:
                continue
            fr_cands += 1
        print(f'   fridge run-basis: {fr_cands} net-new '
              f'candidates ({fr_cands / days:.2f}/day)')

    def predict(filled) -> dict:
        f = np.asarray(filled, dtype='float32')
        sig = _roll_median(f, SMOOTH_N)
        base_roll = _roll_median(sig, 11)
        on, off, amp = _extract_events(sig, cad_s)
        out = {d: np.zeros(len(f), dtype='float32') for d in devices}
        if len(on) == 0:
            return out
        dur = (off - on) * cad_s

        # 0) dw sustained runs (see _dw30_runs): emit the run span
        # extended by the mark-derived ext on each side so onsets stay
        # inside the 600 s matching tolerance of the GT cycle's mask
        # rise (the run starts at the first heater block; the GT cycle
        # starts at the fill valve).
        stride = max(1, int(round(DW30_GRID_S / cad_s)))
        if dw30 is not None or ket_prof is not None                 or wm30 is not None or fridge_band is not None:
            exc_e = _dw30_grid(f, cad_s)
        if dw30 is not None or wm30 is not None:
            ev30_e = np.sort(on // stride)
        dw_owned6 = []
        if dw30 is not None:
            for a30, b30 in _dw30_runs(exc_e, ev30_e, dw30):
                dw_owned6.append((stride * a30, stride * b30))
                i0 = max(0, stride * a30 - dw30['ext6'])
                i1 = min(len(f), stride * b30 + dw30['ext6'])
                seg = out['dishwasher'][i0:i1]
                out['dishwasher'][i0:i1] = np.maximum(
                    seg, dw30['emit_w'])

        # 1) program chains emit spans; their events stay burst-eligible
        ev_in_named = np.zeros(len(on), dtype=bool)
        named_spans = []
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
            if d == 'dishwasher' and dw30 is not None:
                # the sustained-run detector owns dw; keep the mw
                # suppression over the chain span (dw heater partial-
                # duty draws sit in the mw amp band)
                ev_in_named[a0:a1] = True
                named_spans.append((on[a0], off[a1 - 1]))
                continue
            out[d][on[a0]:off[a1 - 1]] = mark[d]['mean_w']
            ev_in_named[a0:a1] = True
            named_spans.append((on[a0], off[a1 - 1]))

        # 1b) wm sustained runs (see _wm30_profile): the marks' heater
        # blocks fuse into one run per cycle; gated on span, heater p90,
        # mean, heat share, idle and the pump-chatter density FLOOR that
        # rejects quiet heater lookalikes (every dw30 run sits below it
        # by construction). Emission extends the run asymmetrically: a
        # small back-extension to the GT mask rise (the wm heats at the
        # cycle start) and a large forward one over the pump/spin tail
        # that draws below the heater threshold. Runs inside dw30
        # territory or a named program chain are already owned.
        if wm30 is not None:
            for a30, b30 in _dw30_runs(exc_e, ev30_e, wm30):
                a6 = stride * a30
                b6 = stride * b30
                owned = False
                for c0, c1 in dw_owned6:
                    if c0 < b6 and a6 < c1:
                        owned = True
                        break
                if owned:
                    continue
                dup = False
                for c0, c1 in named_spans:
                    if c0 < b6 and a6 < c1:
                        dup = True
                        break
                if dup:
                    continue
                i0 = max(0, a6 - wm30['ext_back6'])
                i1 = min(len(f), b6 + wm30['ext_fwd6'])
                seg = out['washing_machine'][i0:i1]
                out['washing_machine'][i0:i1] = np.maximum(
                    seg, wm30['emit_w'])

        # 2) every event classifies independently (burst / duty bands).
        # Program heaters emit partial-duty draws (amp 1.3-1.9 kW) inside
        # named chains that mimic the microwave band - suppress mw there.
        # Kettle is separated by duration, fridge by amplitude, so their
        # classification stays chain-blind.
        p = mark['kettle']
        dr = dur_ref.get('kettle', p['dur_s'])
        ok = ((np.abs(amp - p['amp']) / p['amp'] <= REL_AMP)
              & (dur >= REL_DUR[0] * dr) & (dur <= REL_DUR[1] * dr))
        ket_ok_idx = np.flatnonzero(ok)
        for k in ket_ok_idx:
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
        fr_ok_idx = np.flatnonzero(ok)
        for k in fr_ok_idx:
            i0 = int(k)
            seg = out['fridge'][on[i0]:off[i0]]
            out['fridge'][on[i0]:off[i0]] = np.maximum(seg, amp[i0])
        # 3) kettle sustained runs: draws whose rise/fall pairing broke
        # (mid-draw level changes) never become events; on the coarse
        # grid they are one isolated flat run. Emit runs the burst
        # classifier does not already own (no admitted kettle event or
        # named chain overlaps), with the build-time gates.
        if ket_prof is not None:
            for a, b in _runs(exc_e >= ket_prof['thr']):
                span_s = (b - a) * DW30_GRID_S
                if not ket_prof['span_band'][0] <= span_s \
                        <= ket_prof['span_band'][1]:
                    continue
                mean_w = float(exc_e[a:b].mean())
                if not ket_prof['amp_band'][0] <= mean_w \
                        <= ket_prof['amp_band'][1]:
                    continue
                a6 = a * stride
                b6 = b * stride
                if not _iso_clear(exc_e, a, b, ket_prof['iso_amp'],
                                  ket_prof['iso_win']):
                    continue
                dup = False
                for c0, c1 in named_spans:
                    if c0 < b6 and a6 < c1:
                        dup = True
                        break
                if dup:
                    continue
                k = int(np.searchsorted(on[ket_ok_idx], b6 - 1,
                                        side='right')) - 1
                if k >= 0 and off[ket_ok_idx[k]] > a6:
                    continue
                seg = out['kettle'][a6:b6]
                out['kettle'][a6:b6] = np.maximum(seg, mean_w)
        # 4) fridge run-basis: the event path misses compressor cycles
        # whose draw sits below the extractor's amp floor or whose
        # rise/fall pairing broke; on the coarse grid they are isolated
        # flat runs in the fridge band. Emit runs no admitted fridge
        # event already owns, with the build-time gates.
        if fridge_band is not None:
            fb = fridge_band['fr_run']
            for a, b in _merge_runs(
                    _runs((exc_e >= fb['amp_lo']) & (exc_e <= fb['amp_hi'])),
                    1):
                span_s = (b - a) * DW30_GRID_S
                if not fridge_band['dur'][0] <= span_s \
                        <= fridge_band['dur'][1]:
                    continue
                if not _iso_clear(exc_e, a, b, fb['iso_amp'], fb['iso_win']):
                    continue
                a6 = a * stride
                b6 = b * stride
                k = int(np.searchsorted(on[fr_ok_idx], b6 - 1,
                                        side='right')) - 1
                if k >= 0 and off[fr_ok_idx[k]] > a6:
                    continue
                w = float(np.median(exc_e[a:b]))
                seg = out['fridge'][a6:b6]
                out['fridge'][a6:b6] = np.maximum(seg, w)
        return out

    return predict
