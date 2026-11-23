"""Calibrate the core model to the documented Lm = 320 uH at '1 mm gap' with 64 T (doc p.19)."""
import json, math, warnings, numpy as np, om_tr2 as m, PyOpenMagnetics as P
warnings.filterwarnings("ignore")
m.load()
coil, _ = m.build_coil(ns=2, na=64, nb=64)
MU0 = 4e-7 * math.pi
def core(mat, kind, g):
    res = {"type": "residual", "length": 10e-6}
    if kind == "centre":
        gp = [{"type": "subtractive", "length": g}, dict(res), dict(res)]
    else:   # spacer of thickness g: every leg gets g
        gp = [{"type": "additive", "length": g} for _ in range(3)]
    c = {"functionalDescription": {"type": "two-piece set", "shape": m.SHAPE, "material": mat, "numberStacks": 1, "gapping": gp}}
    return P.calculate_core_data(c, False)
def lm(c):
    L = m.inductance_matrix({"core": c, "coil": coil}, 100e3)
    Lo = L[np.ix_([0, 3], [0, 3])]
    return 1 / np.linalg.inv(Lo).sum()
out = {}
for mat in ("N97", "N87", "3C95", "PC95"):
    for kind in ("centre", "spacer"):
        rows = []
        for g in (0.25e-3, 0.5e-3, 0.75e-3, 1.0e-3, 1.25e-3, 1.5e-3, 2.0e-3):
            rows.append((g * 1e3, lm(core(mat, kind, g)) * 1e6))
        out[f"{mat}_{kind}"] = rows
        # gap for 320 uH (log interpolation)
        gs, ls = zip(*rows)
        g320 = float(np.interp(math.log(320), np.log(ls[::-1]), gs[::-1]))
        out[f"{mat}_{kind}_gap_for_320uH_mm"] = g320
        print(mat, kind, [(a, round(b)) for a, b in rows], "-> 320 uH at %.2f mm" % g320, flush=True)
# hand: L = N^2 / (Rg + Rc), with a fringing factor (McLyman) F = 1 + g/sqrt(Ae) ln(2G/g)
Ae, le, G = 52.2e-6, 54.5e-3, 2 * 8.95e-3
for g in (1.0e-3,):
    F = 1 + g / math.sqrt(Ae) * math.log(2 * G / g)
    Rg_c = g / (MU0 * Ae * F)
    Rc = le / (MU0 * 2000 * Ae)
    out["hand_centre_1mm_uH"] = 64 ** 2 / (Rg_c + Rc) * 1e6
    out["hand_centre_1mm_nofringe_uH"] = 64 ** 2 / (g / (MU0 * Ae) + Rc) * 1e6
    # spacer: centre-leg gap g in series with the two outer legs in parallel (each area Ae/2 -> combined Ae, gap g)
    out["hand_spacer_1mm_uH"] = 64 ** 2 / (2 * Rg_c + Rc) * 1e6
    out["hand_fringe_factor"] = F
print({k: v for k, v in out.items() if k.startswith("hand")})
json.dump(out, open("out/lm_cal.json", "w"), indent=1)
