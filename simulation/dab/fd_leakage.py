"""Independent cross-check of the side-by-side leakage inductance: axisymmetric
finite-difference magnetostatics (no OpenMagnetics).

Why: MKF computes the leakage from the 2-D field in the core window (centre leg <-> outer
leg) and multiplies by the turn length, i.e. it treats the whole turn as if it were inside
the core. On an ER/EC core the outer legs and plates only cover the band |y| < D/2 = 7.65 mm
(about 40-55 % of a turn's circumference); outside that band the leakage field of two
side-by-side windings closes through air and the inductance per unit length is lower.

Two axisymmetric problems are solved for the same winding blocks (smeared current density,
primary +N1*I, secondary -N1*I ampere-turns):
  'pot'  ferrite centre leg, plates and a closed outer ring at r >= E/2 (= in-band 2-D view,
         what MKF assumes for the whole turn)
  'rod'  only the centre leg + the part of the plates above it (r < F/2, |z| < B):
         the out-of-band section of an ER core
and the energy is combined element by element with the in-band fraction of a turn of
radius r: f_in(r) = (2/pi) asin(min(1, (D/2)/r)).  L = 2W/I^2.

Formulation: psi = r*A_phi; d/dr(nu/r dpsi/dr) + d/dz(nu/r dpsi/dz) = -J; psi = 0 on the
axis and on the outer box. W = 1/2 int A J dV = pi * sum(psi * J) * h^2.
"""
from __future__ import annotations

import math

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

MU0 = 4e-7 * math.pi
MUR = 2300.0

# core (m): centre-leg radius, outer ring inner radius, outer radius, half window, half height
RC, RO, RA, ZW, ZB = 0.0076, 0.01525, 0.021, 0.0155, 0.0215
DEPTH_HALF = 0.00765


def solve(blocks, kind="pot", h=0.2e-3, rmax=0.06, zmax=0.07, core=(RC, RO, RA, ZW, ZB)):
    """blocks: list of (r0, r1, z0, z1, ampere_turns) rectangles (m, A).
    Returns (W_pot_or_rod per cell array, r grid, J grid) for 1 A reference already in AT."""
    rc, ro, ra, zw, zb = core
    nr = int(round(rmax / h))
    nz = int(round(2 * zmax / h))
    r = (np.arange(nr) + 0.5) * h                 # cell centres (no node on the axis)
    z = -zmax + (np.arange(nz) + 0.5) * h
    R, Z = np.meshgrid(r, z, indexing="ij")
    ferr = (R < rc) & (np.abs(Z) < zb)
    if kind == "pot":
        ferr |= (np.abs(Z) >= zw) & (np.abs(Z) < zb) & (R < ra)
        ferr |= (R >= ro) & (R < ra) & (np.abs(Z) < zb)
    nu = np.where(ferr, 1 / (MU0 * MUR), 1 / MU0)
    J = np.zeros_like(R)
    for (r0, r1, z0, z1, at) in blocks:
        msk = (R >= r0) & (R < r1) & (Z >= z0) & (Z < z1)
        area = msk.sum() * h * h
        J[msk] += at / area
    idx = np.arange(nr * nz).reshape(nr, nz)
    rows, cols, vals = [], [], []
    diag = np.zeros((nr, nz))
    # r faces between i and i+1 at r = (i+1)*h
    nuf = 0.5 * (nu[:-1, :] + nu[1:, :])
    rf = (np.arange(nr - 1) + 1.0)[:, None] * h
    c = nuf / rf / h / h
    rows += [idx[:-1, :].ravel(), idx[1:, :].ravel()]
    cols += [idx[1:, :].ravel(), idx[:-1, :].ravel()]
    vals += [c.ravel(), c.ravel()]
    diag[:-1, :] -= c
    diag[1:, :] -= c
    # axis: psi ~ c r^2, so the flux term nu/r dpsi/dr at r = 0 is 2 c nu = 8 nu psi0 / h^2
    diag[0, :] -= 8 * nu[0, :] / h ** 3
    # outer r boundary psi = 0 at distance h/2
    diag[-1, :] -= nu[-1, :] / rmax / h / (0.5 * h)
    # z faces
    nuz = 0.5 * (nu[:, :-1] + nu[:, 1:])
    cz = nuz / R[:, :-1] / h / h
    rows += [idx[:, :-1].ravel(), idx[:, 1:].ravel()]
    cols += [idx[:, 1:].ravel(), idx[:, :-1].ravel()]
    vals += [cz.ravel(), cz.ravel()]
    diag[:, :-1] -= cz
    diag[:, 1:] -= cz
    diag[:, 0] -= nu[:, 0] / R[:, 0] / h / (0.5 * h)
    diag[:, -1] -= nu[:, -1] / R[:, -1] / h / (0.5 * h)
    rows.append(idx.ravel())
    cols.append(idx.ravel())
    vals.append(diag.ravel())
    A = sp.csc_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
                      shape=(nr * nz, nr * nz))
    psi = spla.spsolve(A, -J.ravel()).reshape(nr, nz)
    w = math.pi * psi * J * h * h                  # energy per cell (J), 1/2 int A.J dV
    return w, R, J


def leakage(blocks_primary_at1, h=0.2e-3, core=(RC, RO, RA, ZW, ZB), depth_half=DEPTH_HALF):
    """blocks given for I = 1 A primary current (ampere-turns = turns, secondary negative).
    Returns dict of L (H) for pot, rod and the ER combination."""
    wp, R, J = solve(blocks_primary_at1, "pot", h, core=core)
    wr, _, _ = solve(blocks_primary_at1, "rod", h, core=core)
    fin = (2 / math.pi) * np.arcsin(np.minimum(1.0, depth_half / R))
    W = {"pot": wp.sum(), "rod": wr.sum(), "er": (fin * wp + (1 - fin) * wr).sum()}
    return {k: 2 * v for k, v in W.items()}   # I = 1 A -> L = 2W


def blocks_from_report(rep, n1):
    """Winding rectangles (r0, r1, z0, z1, AT) from om_dab.build_coil() report; the turns of a
    partial last layer are smeared over the whole layer width (small error)."""
    out = []
    for k, w in enumerate(rep["windings"]):
        x0 = w["x0_mm"] * 1e-3
        x1 = x0 + w["build_mm"] * 1e-3
        od = w["od_mm"] * 1e-3
        y0, y1 = w["region_mm"][0] * 1e-3, w["region_mm"][1] * 1e-3
        out.append((x0, x1, y0, y1, w["turns"], od, w["turns_per_layer"]))
    return out


if __name__ == "__main__":
    # textbook check: two long side-by-side windings in a pot core vs mu0 N^2 MLT (a1/3+a2/3+g)/h
    N = 20
    b = [(0.0089, 0.0125, -0.0139, -0.0045, N), (0.0089, 0.0125, 0.0015, 0.0115, -N)]
    for hh in (0.4e-3, 0.2e-3, 0.1e-3):
        print(hh, {k: round(v * 1e6, 2) for k, v in leakage(b, hh).items()})
