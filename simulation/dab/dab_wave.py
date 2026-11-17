"""Steady-state DAB (dual half bridge) waveforms, exact piecewise-linear solution.

Circuit (kicad/07_dhb.kicad_sch): primary half bridge Q7/Q8 on DC+ = 400 V with split caps
C47/C54 (1 uF each -> 2 uF in series with the winding for AC), optional series L3, the
transformer as its 2x2 inductance matrix (from MKF), secondary winding to the secondary
half bridge Q19/Q21 with split caps C16/C55 (2 uF for AC) on the 420 V output.
Bridge voltages are ideal +-Vdc/2 squares (dead time neglected), the secondary lags by phi.

States x = [i1, i2, vc1, vc2]; i1 = current from the primary bridge midpoint into the
primary dot, i2 = current from the secondary bridge midpoint into the secondary dot (both
windings have the dot at the bridge midpoint, the other end at the split-cap midpoint):
   M d[i1,i2]/dt = [vb1 - vc1 - R1 i1, vb2 - vc2 - R2 i2]   (vb2 drives the winding the
   same way as vb1; with phi > 0 power flows primary -> secondary)
   dvc1/dt = i1 / C1,  dvc2/dt = i2 / C2
Power to the secondary bridge: P2 = -mean(vb2 * i2).

ZVS (no dead-time dynamics, current at the switching instant):
   primary edge (vb1 -> +): the current out of the midpoint i1 must be < 0;
   secondary edge (vb2 -> +): the current out of its midpoint i2 must be < 0 as well
   (a negative current flows into the node and charges it up before the upper switch).
"""
from __future__ import annotations

import math

import numpy as np
from scipy.linalg import expm
from scipy.optimize import brentq

C_SPLIT = 2e-6       # C47 || C54 (and C16 || C55) for AC


def _system(L, L3=0.0, R=(0.0, 0.0), C=(C_SPLIT, C_SPLIT)):
    L = np.array(L, float)
    M = L.copy()
    M[0, 0] += L3
    Mi = np.linalg.inv(M)
    A = np.zeros((4, 4))
    A[0:2, 0:2] = -Mi @ np.diag(R)
    A[0:2, 2:4] = -Mi
    A[2, 0] = 1 / C[0]
    A[3, 1] = 1 / C[1]
    B = np.zeros((4, 2))
    B[0:2, :] = Mi
    return A, B


def _step(A, B, u, dt):
    n = A.shape[0]
    Ab = np.zeros((n + 1, n + 1))
    Ab[:n, :n] = A
    Ab[:n, n] = B @ u
    E = expm(Ab * dt)
    return E[:n, :n], E[:n, n]


def waveform(L, f, phi_deg, V1=200.0, V2=210.0, L3=0.0, R=(0.0, 0.0), C=(C_SPLIT, C_SPLIT), npts=720):
    """Periodic steady state. Returns dict t, i1, i2, vb1, vb2, vc1, vc2 over one period."""
    A, B = _system(L, L3, R, C)
    T = 1 / f
    td = (phi_deg % 360) / 360 * T
    # intervals with constant bridge voltages
    edges = sorted({0.0, T / 2, td % T, (td + T / 2) % T, T})

    def u_at(t):
        s1 = 1.0 if (t % T) < T / 2 else -1.0
        s2 = 1.0 if ((t - td) % T) < T / 2 else -1.0
        return np.array([V1 * s1, V2 * s2])

    # one-period map x(T) = Phi x0 + g
    Phi, g = np.eye(4), np.zeros(4)
    for a, b in zip(edges[:-1], edges[1:]):
        if b - a <= 0:
            continue
        E, h = _step(A, B, u_at(0.5 * (a + b)), b - a)
        Phi, g = E @ Phi, E @ g + h
    x0 = np.linalg.solve(np.eye(4) - Phi, g)
    # sample: uniform grid plus the edges
    tt = np.unique(np.concatenate([np.linspace(0, T, npts + 1), edges]))
    xs = np.zeros((len(tt), 4))
    x = x0.copy()
    xs[0] = x
    for k in range(1, len(tt)):
        a, b = tt[k - 1], tt[k]
        E, h = _step(A, B, u_at(0.5 * (a + b)), b - a)
        x = E @ x + h
        xs[k] = x
    vb = np.array([u_at(t + 1e-15) for t in tt])
    # primary winding terminal voltage (after L3): vb1 - vc1 - R1 i1 - L3 di1/dt, exact di/dt
    dx = xs @ A.T + vb @ B.T
    vt1 = vb[:, 0] - xs[:, 2] - R[0] * xs[:, 0] - L3 * dx[:, 0]
    return {"t": tt, "i1": xs[:, 0], "i2": xs[:, 1], "vc1": xs[:, 2], "vc2": xs[:, 3],
            "vb1": vb[:, 0], "vb2": vb[:, 1], "vt1": vt1, "T": T, "td": td}


def _mean(t, y):
    return np.trapezoid(y, t) / (t[-1] - t[0])


def _mean_vi(t, v, i):
    """mean(v*i) with v piecewise constant: v[k] is the value on the segment [t[k], t[k+1]]."""
    dt = np.diff(t)
    return float(np.sum(v[:-1] * 0.5 * (i[:-1] + i[1:]) * dt) / (t[-1] - t[0]))


def summary(w):
    t = w["t"]
    p2 = -_mean_vi(t, w["vb2"], w["i2"])
    p1 = _mean_vi(t, w["vb1"], w["i1"])
    i1r = math.sqrt(_mean(t, w["i1"] ** 2))
    i2r = math.sqrt(_mean(t, w["i2"] ** 2))
    # currents at the switching instants (just after the rising edges)
    k1 = 0
    k2 = int(np.argmin(np.abs(t - w["td"])))
    return {"P1": p1, "P2": p2, "I1rms": i1r, "I2rms": i2r,
            "I1pk": float(np.max(np.abs(w["i1"]))), "I2pk": float(np.max(np.abs(w["i2"]))),
            "i1_at_pri_edge": float(w["i1"][k1]), "i2_at_sec_edge": float(w["i2"][k2]),
            "vc1_pp": float(np.ptp(w["vc1"])), "vc2_pp": float(np.ptp(w["vc2"]))}


def phase_for_power(L, f, P=400.0, **kw):
    """Phase shift (deg) giving P at the secondary (lowest solution, 0..90 deg)."""
    fn = lambda ph: summary(waveform(L, f, ph, npts=180, **kw))["P2"] - P
    lo, hi = 0.5, 89.5
    if fn(hi) < 0:
        return None
    return brentq(fn, lo, hi, xtol=1e-3)


def ideal_power(V1, V2r, f, Ls, phi_deg):
    """Textbook DAB power with square voltages of amplitude V1 and V2r (referred)."""
    ph = math.radians(phi_deg)
    return V1 * V2r * ph * (math.pi - ph) / (2 * math.pi ** 2 * f * Ls)


def coupled_L(Lsc, Lm, n, split=0.5):
    """2x2 matrix for a transformer with magnetizing Lm (primary side), primary-referred
    leakage Lsc split 'split' to the primary, turns ratio n = Ns/Np."""
    l1 = split * Lsc
    l2 = (1 - split) * Lsc
    return [[Lm + l1, n * Lm], [n * Lm, n * n * (Lm + l2)]]


if __name__ == "__main__":
    # check against the textbook formula: 26:28, Ls = 70 uH, 83.3 kHz, 25 deg -> ~400 W
    n = 28 / 26
    L = coupled_L(1e-9, 50e-3, n)
    for f, ph in ((83.3e3, 25.0), (140e3, 50.0)):
        s = summary(waveform(L, f, ph, L3=70e-6, C=(1, 1)))
        print(f, ph, "sim P2 %.1f W  formula %.1f W" % (s["P2"], ideal_power(200, 210 / n, f, 70e-6, ph)),
              "I1rms %.2f" % s["I1rms"])
