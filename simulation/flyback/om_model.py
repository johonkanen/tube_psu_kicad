"""OpenMagnetics (PyOpenMagnetics / MKF) model of the auxiliary flyback transformer TR1 (EF20).

Builds the MAS `magnetic` (core + bobbin + coil with explicit section / layer / turn
geometry) for one winding option, and asks MKF for the inductance matrix (self and mutual
inductances, from which every leakage inductance follows), the DC resistance of each
winding, and later (losses.py) the winding and core losses for simulated waveforms.

Why the turns are placed here and not with PyOpenMagnetics.wind(): wind() (1.7.41) ignores
per-intersection insulation thickness (set_intersection_insulation has no effect on the
result; every intersection becomes one 25 um layer), splits the radial height by the
`proportion` argument instead of by the layers actually needed, and it cannot wind two
windings bifilar in one layer. The turns are therefore laid out by `build_coil()` with the
same field names MKF's own winder produces (sections / layers / turns, cartesian, x = radial
distance from the core centre, y = axial position), and MKF does all the electromagnetics.
`validate_against_wind()` checks the hand layout against wind() for a case wind() can do.

Geometry sources:
- Core: EF20 = MKF shape "E 20/10/6" (alias "EF 20"), material N87 (assumed; the real
  material is not documented). Gap fitted so that AL = 171 nH (PDF sheet 1 note
  "TR1 : core 171nh").
- Bobbin: Norwe 09987-106 "EE 20 vertical 10-pin 3.81 mm" from the MKF database. Its pin
  pitch 3.81 mm and row distance 10.16 mm match the board footprint
  Transformer_EF20_2x5_P3.81mm. Winding window 12.6 mm (axial) x 3.4 mm (radial).
"""
from __future__ import annotations

import copy
import functools
import json
import math

import numpy as np

import PyOpenMagnetics as P

BOBBIN_NAME = "Bobbin EE 20 vertical 10-pin 3.81mm (Norwe 09987-106)"
SHAPE = "E 20/10/6"
MATERIAL = "N87"          # assumption
AL_TARGET = 171e-9        # PDF note "TR1 : core 171nh"
LP_TARGET = AL_TARGET * 52 ** 2   # 462 uH primary self-inductance (secondaries open)
TAPE = 0.055e-3           # polyester tape 25 um film + adhesive, per layer (3M 1350F-1 class), assumption
FREQ = 72e3               # IW1818 maximum PWM frequency (datasheet product summary)

_loaded = False


def load():
    global _loaded
    if not _loaded:
        P.load_databases({})
        _loaded = True


@functools.lru_cache(maxsize=None)
def wire(name: str) -> dict:
    load()
    return P.find_wire_by_name(name)


def wire_od(name: str) -> float:
    w = wire(name)
    return w["outerDiameter"]["nominal"]


@functools.lru_cache(maxsize=None)
def bobbin() -> dict:
    load()
    return P.find_bobbin_by_name(BOBBIN_NAME)


def window():
    """(x_inner, x_outer, y_bottom, y_top) of the bobbin winding window in m."""
    ww = bobbin()["processedDescription"]["windingWindows"][0]
    xc, yc = ww["coordinates"][0], ww["coordinates"][1]
    return xc - ww["width"] / 2, xc + ww["width"] / 2, yc - ww["height"] / 2, yc + ww["height"] / 2


# mean turn length: MKF's own winder gives L = 29.000 mm at x = 3.6455 mm and a slope of
# exactly 2*pi (rectangular column + round corners); used for the hand-placed turns.
_L0, _X0 = 29.00004419683565e-3, 3.6455e-3


def turn_length(x: float) -> float:
    return _L0 + 2 * math.pi * (x - _X0)


def make_core(gap: float) -> dict:
    load()
    core = {"functionalDescription": {
        "type": "two-piece set", "shape": SHAPE, "material": MATERIAL, "numberStacks": 1,
        "gapping": [{"type": "subtractive", "length": gap},
                    {"type": "residual", "length": 1e-5},
                    {"type": "residual", "length": 1e-5}]}}
    return P.calculate_core_data(core, False)


# ---------------------------------------------------------------------------------------
# Option description
#
# option = {
#   "name": str, "title": str,
#   "sections": [  # radial order, innermost first
#       {"windings": [(name, turns, parallels, wire_name, side), ...],
#        "mode": "consecutive" | "bifilar",
#        "margin": (bottom, top) in m, "align": "centered" | "spread" | "bottom",
#        "tape_after": number of tape layers after the section},
#   ],
#   "spice": {winding: (dot_node, other_node)},   # see flyback_sim.py
# }
# Winding names are unique; a winding split into two places (sandwich) is two windings
# connected in series in the circuit.
# ---------------------------------------------------------------------------------------


def _wire_sequence(sec):
    """List of (winding, parallel, turn, od) in winding order along the layers."""
    seq = []
    ws = sec["windings"]
    if sec.get("mode", "consecutive") == "bifilar":
        nmax = max(w[1] for w in ws)
        for t in range(nmax):
            for (name, n, par, wn, side) in ws:
                if t < n:
                    for p in range(par):
                        seq.append((name, p, t, wire_od(wn)))
    else:
        for (name, n, par, wn, side) in ws:
            for t in range(n):
                for p in range(par):
                    seq.append((name, p, t, wire_od(wn)))
    return seq


def build_coil(option: dict) -> tuple[dict, dict]:
    """Return (coil_json, report). report: radial build, per-section layers, fits."""
    load()
    xi, xo, yb, yt = window()
    x = xi
    sections, layers, turns = [], [], []
    func = {}
    rep = {"sections": []}
    for si, sec in enumerate(option["sections"]):
        mb, mt = sec.get("margin", (0.0, 0.0))
        y0, y1 = yb + mb, yt - mt
        width = y1 - y0
        seq = _wire_sequence(sec)
        # fill layers
        lay = []
        cur, used = [], 0.0
        for item in seq:
            od = item[3]
            if cur and used + od > width + 1e-9:
                lay.append(cur)
                cur, used = [], 0.0
            cur.append(item)
            used += od
        if cur:
            lay.append(cur)
        sec_name = f"S{si} " + "+".join(w[0] for w in sec["windings"])
        x_start = x
        names_in_sec = [w[0] for w in sec["windings"]]
        for li, items in enumerate(lay):
            th = max(it[3] for it in items)
            xc = x + th / 2
            tot = sum(it[3] for it in items)
            align = sec.get("align", "centered")
            if align == "spread" and len(items) > 1:
                gap = (width - tot) / (len(items) - 1)
                pos, y = [], y0
                for it in items:
                    pos.append(y + it[3] / 2)
                    y += it[3] + gap
            else:
                if align == "bottom":
                    y = y0
                else:
                    y = y0 + (width - tot) / 2
                pos = []
                for it in items:
                    pos.append(y + it[3] / 2)
                    y += it[3]
            lname = f"{sec_name} layer {li}"
            # parallels proportion per winding present in this layer
            pw = []
            for wname in names_in_sec:
                n, par = next((w[1], w[2]) for w in sec["windings"] if w[0] == wname)
                cnt = [0] * par
                for it in items:
                    if it[0] == wname:
                        cnt[it[1]] += 1
                if sum(cnt):
                    pw.append({"winding": wname, "parallelsProportion": [c / n for c in cnt]})
            layers.append({"coordinateSystem": "cartesian", "coordinates": [xc, (y0 + y1) / 2, 0.0],
                           "dimensions": [th, width], "fillingFactor": tot / width,
                           "name": lname, "orientation": "overlapping", "partialWindings": pw,
                           "section": sec_name, "turnsAlignment": align if align != "bottom" else "innerOrTop",
                           "type": "conduction", "windingStyle": "windByConsecutiveParallels"})
            for it, yy in zip(items, pos):
                turns.append({"coordinateSystem": "cartesian", "coordinates": [xc, yy],
                              "crossSectionalShape": "round", "dimensions": [it[3], it[3]],
                              "layer": lname, "length": turn_length(xc),
                              "name": f"{it[0]} parallel {it[1]} turn {it[2]}",
                              "orientation": "clockwise", "parallel": it[1], "rotation": 0.0,
                              "section": sec_name, "winding": it[0]})
            x += th
        sec_th = x - x_start
        sections.append({"coordinateSystem": "cartesian", "coordinates": [x_start + sec_th / 2, (y0 + y1) / 2, 0.0],
                         "dimensions": [sec_th, width], "fillingFactor": 1.0, "group": "Default group",
                         "layersOrientation": "overlapping", "margin": [mb, mt], "name": sec_name,
                         "partialWindings": [{"winding": w[0], "parallelsProportion": [1.0] * w[2]} for w in sec["windings"]],
                         "type": "conduction", "windingStyle": "windByConsecutiveParallels"})
        for (name, n, par, wn, side) in sec["windings"]:
            func[name] = {"name": name, "numberTurns": n, "numberParallels": par, "wire": wire(wn),
                          "isolationSide": side}
        rep["sections"].append({"name": sec_name, "layers": len(lay), "thickness_mm": sec_th * 1e3,
                                "width_mm": width * 1e3,
                                "fill_last_layer": sum(it[3] for it in lay[-1]) / width})
        nt = sec.get("tape_after", 0)
        if nt:
            th = nt * TAPE
            iname = f"I{si} tape x{nt}"
            sections.append({"coordinateSystem": "cartesian", "coordinates": [x + th / 2, 0.0, 0.0],
                             "dimensions": [th, yt - yb], "fillingFactor": 1.0, "group": "Default group",
                             "layersOrientation": "overlapping", "margin": None, "name": iname,
                             "partialWindings": [], "type": "insulation"})
            layers.append({"coordinateSystem": "cartesian", "coordinates": [x + th / 2, 0.0, 0.0],
                           "dimensions": [th, yt - yb], "fillingFactor": 1.0, "name": iname + " layer 0",
                           "orientation": "overlapping", "partialWindings": [], "section": iname,
                           "turnsAlignment": "spread", "type": "insulation"})
            x += th
    order = []
    for sec in option["sections"]:
        for w in sec["windings"]:
            order.append(w[0])
    coil = {"bobbin": bobbin(),
            "functionalDescription": [func[n] for n in order],
            "groupsDescription": [{"coordinateSystem": "cartesian", "coordinates": [(xi + xo) / 2, 0.0],
                                   "dimensions": [xo - xi, yt - yb], "name": "Default group",
                                   "partialWindings": [{"winding": n, "parallelsProportion": [1.0] * func[n]["numberParallels"]}
                                                       for n in order],
                                   "sectionsOrientation": "overlapping", "type": "wound"}],
            "sectionsDescription": sections, "layersDescription": layers, "turnsDescription": turns}
    rep["radial_build_mm"] = (x - xi) * 1e3
    rep["window_radial_mm"] = (xo - xi) * 1e3
    rep["fits"] = x <= xo + 1e-9
    rep["order"] = order
    return coil, rep


def lp_matrix(coil: dict, gap: float) -> float:
    """Primary self-inductance (secondaries open, what an LCR meter reads) from MKF's
    inductance matrix for the full coil."""
    mag = {"core": make_core(gap), "coil": coil}
    n0 = coil["functionalDescription"][0]["name"]
    return P.calculate_inductance_matrix(mag, FREQ, {})["magnitude"][n0][n0]["nominal"]


def fit_gap(coil: dict, lp_target: float) -> float:
    """Gap length (m) for which the primary self-inductance (sum of the primary sections in
    series when the primary is split) equals lp_target. Secant on 1/L, which is close to
    linear in the gap length."""
    load()
    names = [f["name"] for f in coil["functionalDescription"]]
    prim = [i for i, f in enumerate(coil["functionalDescription"]) if f["name"] in ("P", "P1", "P2")]

    def lp(g):
        if len(prim) == 1:
            return lp_matrix(coil, g)
        mag = {"core": make_core(g), "coil": coil}
        m = P.calculate_inductance_matrix(mag, FREQ, {})["magnitude"]
        pn = [names[i] for i in prim]
        return sum(m[a][b]["nominal"] for a in pn for b in pn)

    g0, g1 = 0.25e-3, 0.40e-3
    y0, y1 = 1 / lp(g0), 1 / lp(g1)
    for _ in range(8):
        g2 = g0 + (1 / lp_target - y0) * (g1 - g0) / (y1 - y0)
        y2 = 1 / lp(g2)
        if abs(y2 * lp_target - 1) < 2e-3:
            return round(g2, 7)
        g0, y0, g1, y1 = g1, y1, g2, y2
    return round(g2, 7)


def analyse(option: dict, gap: float | None = None, temperature=60.0) -> dict:
    """Inductance matrix, leakage, coupling, DC resistances, geometry report."""
    load()
    coil, rep = build_coil(option)
    if gap is None:
        gap = option.get("gap") or fit_gap(coil, option.get("lp", LP_TARGET))
    core = make_core(gap)
    mag = {"core": core, "coil": coil}
    names = rep["order"]
    lm = P.calculate_inductance_matrix(mag, FREQ, {})["magnitude"]
    L = np.array([[lm[a][b]["nominal"] for b in names] for a in names])
    L = 0.5 * (L + L.T)
    N = np.array([f["numberTurns"] for f in coil["functionalDescription"]], float)
    rdc = P.calculate_dc_resistance_per_winding(coil, temperature)
    # leakage between every pair, referred to winding 0 (the first primary section):
    # Lsc_ij = L'_ii + L'_jj - 2 L'_ij with L' = L * N0^2 / (Ni Nj)
    Lr = L * (N[0] ** 2) / np.outer(N, N)
    d = np.diag(Lr)
    Lsc = d[:, None] + d[None, :] - 2 * Lr
    k = L / np.sqrt(np.outer(np.diag(L), np.diag(L)))
    eig = np.linalg.eigvalsh(L)
    return {"name": option["name"], "gap": gap, "names": names, "turns": N.tolist(),
            "L": L.tolist(), "Lsc_ref0": Lsc.tolist(), "k": k.tolist(),
            "Rdc": [float(r) for r in rdc], "temperature": temperature,
            "min_eig": float(eig.min()), "geometry": rep, "magnetic": mag}


def mas_document(option: dict, res: dict, inputs: dict | None = None) -> dict:
    """MAS JSON (inputs + magnetic + outputs summary) for writing to disk."""
    mag = copy.deepcopy(res["magnetic"])
    mag["manufacturerInfo"] = {"name": "tube_power_5_1 TR1", "reference": option["name"]}
    outputs = [{"inductance": {"magnetizingInductance": {"magnetizingInductance": {"nominal": res["L"][0][0]}},
                               "inductanceMatrix": [{"frequency": FREQ, "magnitude": {
                                   a: {b: {"nominal": res["L"][i][j]} for j, b in enumerate(res["names"])}
                                   for i, a in enumerate(res["names"])}}]},
                "windingLosses": {"dcResistancePerWinding": res["Rdc"]} if False else None}]
    doc = {"inputs": inputs or {}, "magnetic": mag,
           "outputs": [{"inductance": outputs[0]["inductance"]}]}
    return doc


def validate_against_wind() -> dict:
    """Same 2-winding EF20 coil laid out by MKF's wind() and by build_coil(): compare the
    leakage inductance (MKF energy method on both)."""
    load()
    P.set_settings({"coilDelimitAndCompact": False, "coilEqualizeMargins": False,
                    "coilWindEvenIfNotFit": True, "coilTryRewind": False})
    w = "Round 34.0 - Heavy Build"
    fd = [{"name": "PRI", "numberTurns": 52, "numberParallels": 3, "wire": w, "isolationSide": "primary"},
          {"name": "SHV", "numberTurns": 42, "numberParallels": 3, "wire": w, "isolationSide": "secondary"}]
    c = P.wind({"bobbin": bobbin(), "functionalDescription": fd}, 1, [0.5, 0.5], [0, 1], [[0.003, 0.003], [0.003, 0.003]])
    core = make_core(0.3e-3)
    lk_wind = P.calculate_leakage_inductance({"core": core, "coil": c}, FREQ, 0)["leakageInductancePerWinding"][1]["nominal"]
    # wind() places one 25 um insulation section between the two sections and centres the
    # sections radially in their proportion; reproduce its radial positions
    xs = sorted({round(l["coordinates"][0], 9) for l in c["layersDescription"] if l["type"] == "conduction"})
    opt = {"name": "val", "sections": [
        {"windings": [("PRI", 52, 3, w, "primary")], "margin": (0.003, 0.003), "align": "centered"},
        {"windings": [("SHV", 42, 3, w, "secondary")], "margin": (0.003, 0.003), "align": "centered"}]}
    coil, rep = build_coil(opt)
    # shift the hand layout so the layers sit at the same radii as wind()'s
    xl = sorted({round(l["coordinates"][0], 9) for l in coil["layersDescription"]})
    shift = dict(zip(xl, xs)) if len(xl) == len(xs) else None
    if shift:
        for t in coil["turnsDescription"]:
            t["coordinates"][0] = shift[round(t["coordinates"][0], 9)]
        for l in coil["layersDescription"]:
            l["coordinates"][0] = shift[round(l["coordinates"][0], 9)]
    lk_hand = P.calculate_leakage_inductance({"core": core, "coil": coil}, FREQ, 0)["leakageInductancePerWinding"][1]["nominal"]
    P.reset_settings()
    return {"leakage_wind_uH": lk_wind * 1e6, "leakage_hand_uH": lk_hand * 1e6,
            "layers_wind": len(xs), "layers_hand": len(xl), "same_radii": bool(shift)}


if __name__ == "__main__":
    print(json.dumps(validate_against_wind(), indent=1))
