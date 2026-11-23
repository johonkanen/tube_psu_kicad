"""OpenMagnetics (PyOpenMagnetics 1.7.41 / MKF) MAS model of the heater LLC transformer TR2.

Hand-placed coil (same approach as simulation/dab/om_dab.py in the repo): every AWG 30 strand
is an explicit MAS turn with cartesian coordinates, so MKF sees the real winding order

    PA  : primary portion A, 66 T x 6 parallel AWG 30, next to the centre leg
    S1/S2: centre-tapped secondary halves, litz 35 x 0.2 (Ns turns per half)
    PB  : primary portion B, 66 T x 2 parallel AWG 30, outermost

PA and PB are kept as two separate MAS windings (same turns) so that the 4 x 4 inductance
matrix can be used to solve how the current really shares between the parallel portions.

Coordinates (MKF convention): x = distance from the centre-leg axis, y = axial.
"""
from __future__ import annotations

import copy
import functools
import json
import math

import numpy as np

import PyOpenMagnetics as P

AWG30_CU = 0.2546e-3        # AWG 30 copper diameter
AWG30_OD = 0.279e-3         # single-build (grade 1) nominal OD, NEMA MW-1000 range 0.272 .. 0.287
TAPE = 0.055e-3             # one layer polyester tape 25 um + adhesive (assumption)
BOBBIN_NAME = "Bobbin EE 25 horizontal 10-pin 5.08mm (Norwe 10220-024)"
SHAPE = "E 25/13/7"         # = EF25 (IEC 61246 E 25/13/7)

_loaded = False


def load():
    global _loaded
    if not _loaded:
        P.load_databases({})
        _loaded = True


@functools.lru_cache(maxsize=None)
def _wire_json(name: str) -> str:
    load()
    if name == "AWG30":
        w = copy.deepcopy(P.find_wire_by_name("Round 0.25 - Grade 1"))
        w["name"] = "Round AWG 30 - Grade 1"
        w["conductingDiameter"] = {"nominal": AWG30_CU}
        w["outerDiameter"] = {"nominal": AWG30_OD}
        return json.dumps(w)
    if name == "LITZ35":
        w = copy.deepcopy(P.find_wire_by_name("Litz 30x0.2 - Grade 1 - Unserved"))
        od = P.get_wire_outer_diameter_bare_litz(0.2e-3, 35, 1, "IEC 60317")
        w["name"] = "Litz 35x0.2 - Grade 1 - Unserved"
        w["numberConductors"] = 35
        w["outerDiameter"] = {"nominal": od}
        return json.dumps(w)
    return json.dumps(P.find_wire_by_name(name))


def wire(name: str) -> dict:
    return json.loads(_wire_json(name))


def wire_od(name: str) -> float:
    od = wire(name)["outerDiameter"]
    return od.get("nominal") or od.get("maximum")


def make_core(material: str = "N97", gap: float = 0.0) -> dict:
    """gap = centre-leg grind (subtractive); 0 -> residual 10 um per leg."""
    load()
    res = {"type": "residual", "length": 10e-6}
    gp = [dict(res) for _ in range(3)]
    if gap > 0:
        gp[0] = {"type": "subtractive", "length": gap}
    core = {"functionalDescription": {"type": "two-piece set", "shape": SHAPE, "material": material,
                                      "numberStacks": 1, "gapping": gp}}
    return P.calculate_core_data(core, False)


def bobbin(radial_width: float | None = None) -> dict:
    """Norwe 10220-024 EE25 horizontal 10-pin 5.08 mm bobbin (MKF DB): column 8.9 x 8.9 mm,
    window 4.2 mm radial x 15.8 mm axial.  radial_width overrides the window width (to model
    a stack that overflows the nominal bobbin window: the core window allows 4.5 mm)."""
    load()
    b = copy.deepcopy(P.find_bobbin_by_name(BOBBIN_NAME))
    if radial_width:
        ww = b["processedDescription"]["windingWindows"][0]
        x0 = ww["coordinates"][0] - ww["width"] / 2
        ww["width"] = radial_width
        ww["coordinates"] = [x0 + radial_width / 2, ww["coordinates"][1]]
        ww["area"] = radial_width * ww["height"]
    return b


def window(b: dict):
    ww = b["processedDescription"]["windingWindows"][0]
    xc, yc = ww["coordinates"]
    return xc - ww["width"] / 2, xc + ww["width"] / 2, yc - ww["height"] / 2, yc + ww["height"] / 2


def turn_length(x: float, b: dict) -> float:
    """Rectangular column 2a x 2a with rounded-corner turns at radius x."""
    a = b["processedDescription"]["columnWidth"]
    return 8 * a + 2 * math.pi * (x - a)


def strand_portion(name, turns, par, x0, y0, y1, pitch_factor, wname="AWG30"):
    """A primary portion wound as a flat ribbon of `par` strands per turn, layer by layer.
    Returns (list of (winding, parallel, turn, x, y, od)), radial build, layers."""
    od = wire_od(wname)
    width = y1 - y0
    tpl = int(math.floor(width / (par * od) + 1e-9))
    nl = math.ceil(turns / tpl)
    pitch = od * pitch_factor
    items = []
    t = 0
    for li in range(nl):
        k = min(tpl, turns - t)
        x = x0 + od / 2 + li * pitch
        blk = k * par * od
        ys = y0 + (width - blk) / 2
        for j in range(k):
            for p in range(par):
                y = ys + od / 2 + (j * par + p) * od
                items.append((name, p, t, x, y, od, li))
            t += 1
    build = od + (nl - 1) * pitch
    return items, build, nl, tpl


def build_coil(ns: int = 1, tape_layers: int = 3, pitch_factor: float = 0.866,
               radial_width: float | None = 4.5e-3, sec_order: str = "bifilar",
               sec_y_offset: float = 0.0, extra_gap: float = 0.0, litz_thk: float | None = 1.25e-3,
               na: int = 66, pa_par: int = 6, nb: int = 66, pb_par: int = 2, ribbon_a: int | None = None):
    """MAS coil: PA (66 x 6), tape, S1/S2 (ns turns each, litz 35x0.2, one layer), tape, PB (66 x 2).
    pitch_factor < 1 models nesting of the strand layers (0.866 = orthocyclic).
    extra_gap: additional radial distance added on both sides of the secondary (sensitivity)."""
    load()
    b = bobbin(radial_width)
    xi, xo, yb, yt = window(b)
    tape = tape_layers * TAPE + extra_gap
    items = []
    rep = {}
    pa, bpa, nla, tpla = strand_portion("PA", na, pa_par, xi, yb, yt, pitch_factor)
    items += pa
    x = xi + bpa + tape
    # secondary layer
    od_round = wire_od("LITZ35")
    # pressed litz: radial thickness litz_thk, axial width keeps the bundle area (pi/4 od^2)
    thk_s = litz_thk or od_round
    od_s = (math.pi / 4 * od_round ** 2 / thk_s) if litz_thk else od_round   # axial width
    if sec_order == "bifilar":
        seq = [("S1" if k % 2 == 0 else "S2", k // 2) for k in range(2 * ns)]
    else:  # S1 block then S2 block
        seq = [("S1", k) for k in range(ns)] + [("S2", k) for k in range(ns)]
    tot = len(seq) * od_s
    ys = sec_y_offset - tot / 2
    xs = x + thk_s / 2
    for k, (wn, t) in enumerate(seq):
        items.append((wn, 0, t, xs, ys + od_s / 2 + k * od_s, (thk_s, od_s), 0))
    if nb:
        x += thk_s + tape
        pb, bpb, nlb, tplb = strand_portion("PB", nb, pb_par, x, yb, yt, pitch_factor)
        items += pb
        x_end = x + bpb
    else:
        x += thk_s
        bpb, nlb, tplb = 0.0, 0, 0
        x_end = x
    if x_end > xo + 1e-9:
        raise ValueError(f"stack {(x_end - xi) * 1e3:.3f} mm exceeds the window {(xo - xi) * 1e3:.2f} mm")
    rep = {"PA": {"layers": nla, "turns_per_layer": tpla, "build_mm": bpa * 1e3},
           "S": {"build_mm": thk_s * 1e3, "litz_round_od_mm": od_round * 1e3, "litz_axial_width_mm": od_s * 1e3,
                 "axial_extent_mm": tot * 1e3},
           "PB": {"layers": nlb, "turns_per_layer": tplb, "build_mm": bpb * 1e3},
           "tape_each_mm": tape * 1e3, "stack_mm": (x_end - xi) * 1e3,
           "window_radial_mm": (xo - xi) * 1e3, "window_axial_mm": (yt - yb) * 1e3,
           "norwe_window_radial_mm": 4.2, "pitch_factor": pitch_factor}
    rep["fits_norwe_4p2"] = rep["stack_mm"] <= 4.2 + 1e-9
    rep["fits_core_4p5"] = rep["stack_mm"] <= 4.5 + 1e-9

    # MAS structures
    winding_defs = [("PA", na, pa_par, "AWG30", "primary"), ("S1", ns, 1, "LITZ35", "secondary"),
                    ("S2", ns, 1, "LITZ35", "secondary")] + ([("PB", nb, pb_par, "AWG30", "primary")] if nb else [])
    func = [{"name": n, "numberTurns": nt, "numberParallels": par, "wire": wire(wn), "isolationSide": side}
            for n, nt, par, wn, side in winding_defs]
    turns, layers, sections = [], [], []
    # layers: group by (winding portion, layer index) ; secondary = one layer with two windings
    by_layer = {}
    for (wn, p, t, xx, yy, od, li) in items:
        key = ("SEC", 0) if wn in ("S1", "S2") else (wn, li)
        by_layer.setdefault(key, []).append((wn, p, t, xx, yy, od))
    sec_names = {"PA": "Section PA", "PB": "Section PB", "SEC": "Section S"}
    nturns = {n: nt for n, nt, *_ in winding_defs}
    npar = {n: par for n, _, par, *_ in winding_defs}
    for key, its in by_layer.items():
        lname = f"{key[0]} layer {key[1]}"
        sname = sec_names[key[0]]
        xc = its[0][3]
        od = its[0][5] if not isinstance(its[0][5], tuple) else its[0][5][0]
        pw = []
        for wn in sorted({i[0] for i in its}):
            props = []
            for p in range(npar[wn]):
                cnt = sum(1 for i in its if i[0] == wn and i[1] == p)
                props.append(cnt / nturns[wn])
            pw.append({"winding": wn, "parallelsProportion": props})
        layers.append({"coordinateSystem": "cartesian", "coordinates": [xc, 0.0, 0.0],
                       "dimensions": [od, yt - yb], "fillingFactor": min(1.0, len(its) * od / (yt - yb)), "name": lname,
                       "orientation": "overlapping", "partialWindings": pw, "section": sname,
                       "turnsAlignment": "centered", "type": "conduction",
                       "windingStyle": "windByConsecutiveParallels"})
        for (wn, p, t, xx, yy, od_) in its:
            dims = list(od_) if isinstance(od_, tuple) else [od_, od_]
            turns.append({"coordinateSystem": "cartesian", "coordinates": [xx, yy],
                          "crossSectionalShape": "rectangular" if isinstance(od_, tuple) else "round",
                          "dimensions": dims, "layer": lname, "length": turn_length(xx, b),
                          "name": f"{wn} parallel {p} turn {t}", "orientation": "clockwise", "parallel": p,
                          "rotation": 0.0, "section": sname, "winding": wn})
    for sname, wns in (("Section PA", ["PA"]), ("Section S", ["S1", "S2"])) + ((("Section PB", ["PB"]),) if nb else ()):
        its = [i for i in items if i[0] in wns]
        rx = lambda i: (i[5][0] if isinstance(i[5], tuple) else i[5]) / 2
        x0 = min(i[3] - rx(i) for i in its)
        x1 = max(i[3] + rx(i) for i in its)
        sections.append({"coordinateSystem": "cartesian", "coordinates": [(x0 + x1) / 2, 0.0, 0.0],
                         "dimensions": [x1 - x0, yt - yb],
                         "fillingFactor": sum((i[5][0] * i[5][1]) if isinstance(i[5], tuple) else i[5] ** 2 for i in its) / ((x1 - x0) * (yt - yb)),
                         "group": "Default group", "layersOrientation": "overlapping", "margin": [0.0, 0.0],
                         "name": sname,
                         "partialWindings": [{"winding": w, "parallelsProportion": [1.0] * npar[w]} for w in wns],
                         "type": "conduction", "windingStyle": "windByConsecutiveParallels"})
    coil = {"bobbin": b, "functionalDescription": func,
            "groupsDescription": [{"coordinateSystem": "cartesian", "coordinates": [(xi + xo) / 2, (yb + yt) / 2],
                                   "dimensions": [xo - xi, yt - yb], "name": "Default group",
                                   "partialWindings": [{"winding": f["name"], "parallelsProportion": [1.0] * f["numberParallels"]} for f in func],
                                   "sectionsOrientation": "overlapping", "type": "wound"}],
            "sectionsDescription": sections, "layersDescription": layers, "turnsDescription": turns}
    # mean turn lengths per winding (for hand checks)
    rep["MLT_mm"] = {wn: float(np.mean([t["length"] for t in turns if t["winding"] == wn]) * 1e3)
                     for wn in ("PA", "S1", "S2", "PB")}
    rep["window_area_mm2"] = (xo - xi) * (yt - yb) * 1e6
    return coil, rep


NAMES = ["PA", "S1", "S2", "PB"]


def inductance_matrix(mag: dict, freq: float) -> np.ndarray:
    names = [f["name"] for f in mag["coil"]["functionalDescription"]]
    lm = P.calculate_inductance_matrix(mag, freq, {})["magnitude"]
    L = np.array([[lm[a][b]["nominal"] for b in names] for a in names])
    return 0.5 * (L + L.T)


def leak_parallel_primary(L: np.ndarray, shorted: str, R=None, w=None):
    """PA || PB driven (common voltage), secondary configuration `shorted`:
       'S1'     : only S1 shorted, S2 open  (one rectifier half conducting = operation)
       'series' : S1 and S2 in series shorted (secondary ends shorted, CT open)
       'both'   : S1 and S2 each shorted (ends and CT tied)
    Returns (L_eff, kA, kB) with kA/kB the complex share of the primary current in PA / PB.
    With R (vector of winding resistances) and w the solve is done with impedances."""
    Z = 1j * (w or 1.0) * L.astype(complex)
    if R is not None:
        Z = Z + np.diag(R)
    # unknown currents [IA, I1, I2, IB]; constraints build a linear system
    # V = Z I ; VA = VB = V0 (=1) ; secondary per case
    A, rhs = [], []
    if shorted == "S1":
        A.append(Z[1]); rhs.append(0)            # V1 = 0
        A.append([0, 0, 1, 0]); rhs.append(0)    # I2 = 0 (open)
    elif shorted == "both":
        A.append(Z[1]); rhs.append(0)
        A.append(Z[2]); rhs.append(0)
    elif shorted == "series":
        A.append(Z[1] + Z[2]); rhs.append(0)     # V1 + V2 = 0
        A.append([0, 1, -1, 0]); rhs.append(0)   # I1 = I2
    A.append(Z[0]); rhs.append(1)
    A.append(Z[3]); rhs.append(1)
    I = np.linalg.solve(np.array(A, complex), np.array(rhs, complex))
    Ip = I[0] + I[3]
    Zin = 1 / Ip
    Leff = (Zin.imag / (w or 1.0))
    return Leff, I[0] / Ip, I[3] / Ip, I


def leak_general(L: np.ndarray, prim: str, sec: str, turns=None):
    """Short-circuit inductance referred to the full primary for the three documented builds.
    L order: PA, S1, S2[, PB].  prim: 'flat' (PA only), 'series' (PA + PB in series, equal
    current), 'parallel' (PA || PB, split from the matrix).  sec: 'S1' (S1 shorted, S2 open),
    'series' (secondary ends shorted, CT open), 'both' (each half shorted)."""
    if prim == "parallel":
        return leak_parallel_primary(L, sec)[0]
    c = np.array([1.0, 0, 0] + ([1.0] if prim == "series" else ([0.0] if L.shape[0] == 4 else [])))
    if sec == "S1":
        S = [np.array([0, 1.0, 0] + [0.0] * (L.shape[0] - 3))]
    elif sec == "series":
        S = [np.array([0, 1.0, 1.0] + [0.0] * (L.shape[0] - 3))]
    else:
        S = [np.array([0, 1.0, 0] + [0.0] * (L.shape[0] - 3)), np.array([0, 0, 1.0] + [0.0] * (L.shape[0] - 3))]
    Lpp = c @ L @ c
    Lps = np.array([c @ L @ s for s in S])
    Lss = np.array([[a @ L @ b for b in S] for a in S])
    return Lpp - Lps @ np.linalg.solve(Lss, Lps)
