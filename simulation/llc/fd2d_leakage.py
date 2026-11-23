"""Independent cross-check of the TR2 leakage (no OpenMagnetics): 2-D planar finite-difference
magnetostatics, A_z formulation, ferrite mu_r = 2000, on two cross-sections of the EF25
(E 25/13/7) core:

  'window' : x-y section through the core window (centre leg |x| < 3.625 mm, outer leg
             8.95 .. 12.55 mm, yokes |y| > 8.95 mm). Currents of the right window +, the left
             window -  -> A_z odd in x, A_z = 0 on x = 0, solved for x >= 0. This is the 2-D view
             MKF uses for the whole turn.
  'end'    : section through an end turn (the part of the turn outside the core, in front of /
             behind the centre leg): the coordinate across the wire is the distance from the
             centre-leg face; ferrite only on one side (leg + yokes form a wall at u < 0 for
             |y| < 12.55 mm). Open boundary far away.

Energy per unit length W'(cell) is combined with the length of each conductor element that
lies inside the window (2 x 7.2 mm = core depth on both sides) and outside it (rest of the
turn): L = 2 * sum(W'_win * l_in + W'_end * l_out) / I^2 for I = 1 A on the primary side.

The conductors are given as rectangles with their ampere-turns (strand layers smeared over
their axial extent, each litz turn as a square of its OD).
"""
from __future__ import annotations

import math

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

MU0 = 4e-7 * math.pi
MUR = 2000.0
# EF25 (MKF E 25/13/7 nominal): A 25.05, B 12.55 (half height), C 7.2 (depth), D 8.95 (half
# window height), E 17.9 (between outer legs), F 7.25 (centre leg)
XC, XO, XA, YW, YB, DEPTH = 3.625e-3, 8.95e-3, 12.525e-3, 8.95e-3, 12.55e-3, 7.2e-3
COL = 4.45e-3                 # bobbin column half width (turns measured from the axis)


def solve(blocks, kind, h=0.05e-3, pad=12e-3):
    """blocks: (x0, x1, y0, y1, AT) with x = distance from the centre axis (window) - the same x
    is used as 'distance from axis' for the end section, where the leg face is at XC."""
    xmax = XA + pad
    ymax = YB + pad
    nx = int(round(xmax / h))
    ny = int(round(2 * ymax / h))
    x = (np.arange(nx) + 0.5) * h
    y = -ymax + (np.arange(ny) + 0.5) * h
    X, Y = np.meshgrid(x, y, indexing="ij")
    if kind == "window":
        fer = (X < XC) & (np.abs(Y) < YB)
        fer |= (np.abs(Y) >= YW) & (np.abs(Y) < YB) & (X < XA)
        fer |= (X >= XO) & (X < XA) & (np.abs(Y) < YB)
        x_dirichlet_left = True
    else:
        # end section: ferrite wall for x < XC (leg + yokes, |y| < YB); left side (x -> 0) is
        # inside ferrite; nothing at x > XC
        fer = (X < XC) & (np.abs(Y) < YB)
        x_dirichlet_left = False
    nu = np.where(fer, 1 / (MU0 * MUR), 1 / MU0)
    J = np.zeros_like(X)
    for (x0, x1, y0, y1, at) in blocks:
        m = (X >= x0) & (X < x1) & (Y >= y0) & (Y < y1)
        if m.sum() == 0:
            # tiny block: put it in the nearest cell
            i = min(nx - 1, int((0.5 * (x0 + x1)) / h)); j = min(ny - 1, int((0.5 * (y0 + y1) + ymax) / h))
            m = np.zeros_like(X, bool); m[i, j] = True
        J[m] += at / (m.sum() * h * h)
    idx = np.arange(nx * ny).reshape(nx, ny)
    rows, cols, vals = [], [], []
    diag = np.zeros((nx, ny))
    nuf = 2 * nu[:-1, :] * nu[1:, :] / (nu[:-1, :] + nu[1:, :])
    c = nuf / h / h
    rows += [idx[:-1, :].ravel(), idx[1:, :].ravel()]
    cols += [idx[1:, :].ravel(), idx[:-1, :].ravel()]
    vals += [c.ravel(), c.ravel()]
    diag[:-1, :] -= c
    diag[1:, :] -= c
    if x_dirichlet_left:
        diag[0, :] -= nu[0, :] / h / (0.5 * h)      # A = 0 at x = 0
    # (else: Neumann at x = 0, inside ferrite - field parallel, fine for the end section)
    diag[-1, :] -= nu[-1, :] / h / (0.5 * h)
    nuz = 2 * nu[:, :-1] * nu[:, 1:] / (nu[:, :-1] + nu[:, 1:])
    cz = nuz / h / h
    rows += [idx[:, :-1].ravel(), idx[:, 1:].ravel()]
    cols += [idx[:, 1:].ravel(), idx[:, :-1].ravel()]
    vals += [cz.ravel(), cz.ravel()]
    diag[:, :-1] -= cz
    diag[:, 1:] -= cz
    diag[:, 0] -= nu[:, 0] / h / (0.5 * h)
    diag[:, -1] -= nu[:, -1] / h / (0.5 * h)
    rows.append(idx.ravel()); cols.append(idx.ravel()); vals.append(diag.ravel())
    A = sp.csc_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
                      shape=(nx * ny, nx * ny))
    Az = spla.spsolve(A, -J.ravel()).reshape(nx, ny)
    wcell = 0.5 * Az * J * h * h            # energy per unit length per cell (J/m)
    return wcell, X, Y


def matrix(sources, kind, h=0.05e-3, pad=12e-3):
    """sources: list of block lists (one per winding, for 1 A in that winding).
    Returns (Mcell_ij as list of per-cell arrays A_i*J_j*h^2, X)."""
    xmax = XA + pad; ymax = YB + pad
    nx = int(round(xmax / h)); ny = int(round(2 * ymax / h))
    x = (np.arange(nx) + 0.5) * h; y = -ymax + (np.arange(ny) + 0.5) * h
    X, Y = np.meshgrid(x, y, indexing="ij")
    Js = []
    for blocks in sources:
        J = np.zeros_like(X)
        for (x0, x1, y0, y1, at) in blocks:
            m = (X >= x0) & (X < x1) & (Y >= y0) & (Y < y1)
            J[m] += at / (m.sum() * h * h)
        Js.append(J)
    A = _operator(X, Y, kind, h, nx, ny, xmax)
    lu = spla.splu(A)
    Az = [lu.solve(-J.ravel()).reshape(nx, ny) for J in Js]
    n = len(sources)
    return [[Az[i] * Js[j] * h * h for j in range(n)] for i in range(n)], X


def _operator(X, Y, kind, h, nx, ny, xmax):
    if kind == "window":
        fer = (X < XC) & (np.abs(Y) < YB)
        fer |= (np.abs(Y) >= YW) & (np.abs(Y) < YB) & (X < XA)
        fer |= (X >= XO) & (X < XA) & (np.abs(Y) < YB)
    else:
        fer = (X < XC) & (np.abs(Y) < YB)
    nu = np.where(fer, 1 / (MU0 * MUR), 1 / MU0)
    idx = np.arange(nx * ny).reshape(nx, ny)
    rows, cols, vals = [], [], []
    diag = np.zeros((nx, ny))
    nuf = 2 * nu[:-1, :] * nu[1:, :] / (nu[:-1, :] + nu[1:, :])
    c = nuf / h / h
    rows += [idx[:-1, :].ravel(), idx[1:, :].ravel()]; cols += [idx[1:, :].ravel(), idx[:-1, :].ravel()]
    vals += [c.ravel(), c.ravel()]
    diag[:-1, :] -= c; diag[1:, :] -= c
    if kind == "window":
        diag[0, :] -= nu[0, :] / h / (0.5 * h)
    diag[-1, :] -= nu[-1, :] / h / (0.5 * h)
    nuz = 2 * nu[:, :-1] * nu[:, 1:] / (nu[:, :-1] + nu[:, 1:])
    cz = nuz / h / h
    rows += [idx[:, :-1].ravel(), idx[:, 1:].ravel()]; cols += [idx[:, 1:].ravel(), idx[:, :-1].ravel()]
    vals += [cz.ravel(), cz.ravel()]
    diag[:, :-1] -= cz; diag[:, 1:] -= cz
    diag[:, 0] -= nu[:, 0] / h / (0.5 * h); diag[:, -1] -= nu[:, -1] / h / (0.5 * h)
    rows.append(idx.ravel()); cols.append(idx.ravel()); vals.append(diag.ravel())
    return sp.csc_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
                         shape=(nx * ny, nx * ny))


def inductance_matrices(coil, names=("PA", "S1", "S2", "PB"), h=0.05e-3):
    """4x4 matrices (H): 'mkf_like' (window field x full turn length), 'combined' (window field
    on 2 x DEPTH of each turn, end-turn field on the rest)."""
    srcs = [blocks_from_coil(coil, {n: 1.0}) for n in names]
    Mw, X = matrix(srcs, "window", h)
    Me, _ = matrix(srcs, "end", h)
    lt = turn_len(X); lin = 2 * DEPTH; lout = np.maximum(lt - lin, 0)
    n = len(names)
    out = {}
    for key in ("mkf_like", "combined", "end_only"):
        L = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if key == "mkf_like":
                    L[i, j] = (Mw[i][j] * lt).sum()
                elif key == "end_only":
                    L[i, j] = (Me[i][j] * lt).sum()
                else:
                    L[i, j] = (Mw[i][j] * lin).sum() + (Me[i][j] * lout).sum()
        out[key] = 0.5 * (L + L.T)
    return out


def turn_len(x):
    return 8 * COL + 2 * math.pi * np.maximum(x - COL, 0.0)


def leakage(blocks, h=0.05e-3):
    """blocks for 1 A total primary current. Returns dict (H): 'mkf_like' = window W' x full
    turn length (what a window-only 2-D model gives), 'combined' = window W' on 2 x DEPTH, end
    W' on the rest of the turn, plus 'end_only' = end W' x full length."""
    ww, X, _ = solve(blocks, "window", h)
    we, _, _ = solve(blocks, "end", h)
    lt = turn_len(X)
    lin = 2 * DEPTH
    return {"mkf_like": 2 * (ww * lt).sum(),
            "combined": 2 * ((ww * lin).sum() + (we * np.maximum(lt - lin, 0)).sum()),
            "end_only": 2 * (we * lt).sum(),
            "in_window_fraction_of_MLT": float(lin / np.average(lt, weights=np.abs(ww) + 1e-30))}


def blocks_from_coil(coil, currents):
    """currents: dict winding -> current (A) per winding (split equally over its parallels).
    Strand layers are smeared over their axial extent; litz turns kept as squares."""
    par = {f["name"]: f["numberParallels"] for f in coil["functionalDescription"]}
    groups = {}
    for t in coil["turnsDescription"]:
        groups.setdefault((t["winding"], t["layer"]), []).append(t)
    out = []
    for (wn, ln), ts in groups.items():
        i_strand = currents.get(wn, 0.0) / par[wn]
        od = ts[0]["dimensions"][0]
        xs = ts[0]["coordinates"][0]
        if wn.startswith("S"):
            for t in ts:
                x, y = t["coordinates"]
                dx, dy = t["dimensions"]
                out.append((x - dx / 2, x + dx / 2, y - dy / 2, y + dy / 2, i_strand))
        else:
            ys = [t["coordinates"][1] for t in ts]
            out.append((xs - od / 2, xs + od / 2, min(ys) - od / 2, max(ys) + od / 2, i_strand * len(ts)))
    return out


def balanced_leakage(coil, case="S1", h=0.05e-3, k_fixed=None):
    """Primary-referred short-circuit inductance for PA || PB (66 T each) with the secondary
    shorted, from balanced current sets only (no magnetizing field, no ill-conditioning).
    case 'S1': S1 carries -66/Ns A, S2 open; 'series': S1 and S2 each -66/(2Ns)... no: in series
    the secondary has 2Ns turns and both halves carry -66/(2Ns) A per turn-count Ns each.
    The PA / PB split k (share of PA) minimises the energy (Thomson), or is fixed by k_fixed.
    Returns dict per length model: (L, k)."""
    ns = {f["name"]: f["numberTurns"] for f in coil["functionalDescription"]}["S1"]
    if case == "S1":
        sec = {"S1": -66.0 / ns}
    else:
        sec = {"S1": -66.0 / (2 * ns), "S2": -66.0 / (2 * ns)}
    c0 = blocks_from_coil(coil, dict(sec, PB=1.0))          # k = 0: all in PB
    c1 = blocks_from_coil(coil, dict(sec, PA=1.0))          # k = 1: all in PA
    Mw, X = matrix([c0, c1], "window", h)
    Me, _ = matrix([c0, c1], "end", h)
    lt = turn_len(X); lin = 2 * DEPTH; lout = np.maximum(lt - lin, 0)
    out = {}
    for key in ("mkf_like", "combined", "end_only"):
        def w(i, j):
            if key == "mkf_like":
                return (Mw[i][j] * lt).sum()
            if key == "end_only":
                return (Me[i][j] * lt).sum()
            return (Mw[i][j] * lin).sum() + (Me[i][j] * lout).sum()
        W00, W11, W01 = w(0, 0), w(1, 1), 0.5 * (w(0, 1) + w(1, 0))
        # L(k) = (1-k)^2 W00 + k^2 W11 + 2k(1-k) W01   (= 2 * energy at 1 A, since w() = A*J*l)
        a = W00 + W11 - 2 * W01
        k = (W00 - W01) / a if k_fixed is None else k_fixed
        out[key] = ((1 - k) ** 2 * W00 + k ** 2 * W11 + 2 * k * (1 - k) * W01, k)
    return out
