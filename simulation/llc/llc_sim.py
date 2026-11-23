"""Time-domain steady state of the heater LLC (ideal half bridge, Lr - Cr - Lm with an ideal
centre-tapped rectifier clamped to n*(Vo + drop)).  No OpenMagnetics: this is the circuit
check for gain / frequency / magnetizing current at the switching edge.

Lr = primary-referred leakage seen while ONE secondary half conducts (the other open);
Cr = the total resonant capacitance (two split halves in parallel for AC).
"""
from __future__ import annotations

import math

import numpy as np

N = 32.0           # 64 : 2 per half
R_SEC = 0.023      # SR (BUK9Y15-60E hot ~19.5 mOhm) + winding + leads (assumed)
R_PRI = 0.8        # primary: 2 x 0.28 Ohm FET (one conducts) hot + winding 0.2 Ohm (damps the start transient)


def run_period(f, Vin, Lr, Cr, Lm, Vcl, n_per=4000, periods=400):
    """Returns dict with Io, current at the switching edge, rms primary, peak Cr ripple, and
    the conduction time of one rectifier half."""
    T = 1 / f
    dt = T / n_per
    ir = im = vc = 0.0
    for p in range(periods):
        rec = p == periods - 1
        if rec:
            irs, ims, vcs, cond = np.zeros(n_per), np.zeros(n_per), np.zeros(n_per), np.zeros(n_per, bool)
        for k in range(n_per):
            vsw = Vin / 2 if k < n_per // 2 else -Vin / 2
            d = ir - im
            con = False
            if abs(d) > 1e-12:
                s = 1.0 if d > 0 else -1.0
                ir_n = ir + (vsw - vc - s * Vcl - R_PRI * ir) / Lr * dt
                im_n = im + s * Vcl / Lm * dt
                if (ir_n - im_n) * s <= 0:
                    ir_n = im_n = 0.5 * (ir_n + im_n)
                else:
                    con = True
                ir, im = ir_n, im_n
            else:
                vm = Lm / (Lr + Lm) * (vsw - vc)
                if abs(vm) >= Vcl:
                    s = 1.0 if vm > 0 else -1.0
                    ir = ir + (vsw - vc - s * Vcl - R_PRI * ir) / Lr * dt
                    im = im + s * Vcl / Lm * dt
                    con = True
                else:
                    ir = im = ir + (vsw - vc - R_PRI * ir) / (Lr + Lm) * dt
            vc += ir / Cr * dt
            if rec:
                irs[k], ims[k], vcs[k], cond[k] = ir, im, vc, con
    Io = N * np.mean(np.abs(irs - ims))
    # conduction time of the first half-cycle's rectifier pulse
    half = cond[: n_per // 2]
    tc = half.sum() * dt
    return {"Io": float(Io), "i_sw_A": float(irs[n_per // 2 - 1]), "im_pk_A": float(np.max(np.abs(ims))),
            "Ipri_rms": float(np.sqrt(np.mean(irs ** 2))), "vc_pp": float(vcs.max() - vcs.min()),
            "Ipri_pk": float(np.max(np.abs(irs))), "t_cond_us": tc * 1e6,
            "Isec_pk": float(N * np.max(np.abs(irs - ims))), "wave": (irs, ims, vcs)}


def freq_for_load(Io_target, Vin, Lr, Cr, Lm, Vo=6.3, fmin=150e3, fmax=270e3, n_per=1000, periods=800):
    """Bisection on f (load current falls with rising f above the gain peak). None if the target
    cannot be reached inside [fmin, fmax]."""
    Vcl = N * (Vo + R_SEC * Io_target * 1.23)
    lo = run_period(fmin, Vin, Lr, Cr, Lm, Vcl, n_per, periods)
    hi = run_period(fmax, Vin, Lr, Cr, Lm, Vcl, n_per, periods)
    if lo["Io"] < Io_target:
        return None, lo, "not reachable: Io at fmin = %.1f A" % lo["Io"]
    if hi["Io"] > Io_target:
        return fmax, hi, "already above target at fmax (Io %.1f A)" % hi["Io"]
    a, b = fmin, fmax
    for _ in range(18):
        c = 0.5 * (a + b)
        r = run_period(c, Vin, Lr, Cr, Lm, Vcl, n_per, periods)
        if r["Io"] > Io_target:
            a = c
        else:
            b = c
    r = run_period(0.5 * (a + b), Vin, Lr, Cr, Lm, Vcl, n_per, periods)
    return 0.5 * (a + b), r, "ok"
