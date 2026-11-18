"""OpenMagnetics (PyOpenMagnetics 1.7.41 / MKF) models of the DAB transformer TR3.

Two magnetics are described here in MAS form (core + bobbin + coil with explicit section /
layer / turn geometry, the same hand-placed layout approach as simulation/flyback/om_model.py,
because MKF's wind() cannot place windings into the chambers of a sectioned bobbin with the
fill and alignment wanted here):

- NEW: "EC42*15" PC40 (seller drawing, round centre leg = ER family) as a custom MKF shape
  (family "er"): A 42.0, B 21.5 (half height), C 15.3 (depth), D 15.5 (half window height),
  E 30.5 (between outer legs), F 15.2 (centre leg). MKF gives Ae 187.0 mm2, le 98.8 mm,
  Ve 18.47 cm3 (the DB shape "ER 42/22/15" gives 172.7 mm2 / 100.6 mm / 17.37 cm3; not used).
  Bobbin: seller 2-chamber bobbin, modelled as one winding window x 8.9..15.0 mm (tube OD
  17.8, flange OD 30.0), y -13.9..+13.9 mm (27.8 mm inner) with a 5.0 mm divider at
  y = -3.5..+1.5 mm: chamber 1 (10.4 mm, pins 1-8) y -13.9..-3.5, chamber 2 (12.4 mm,
  pins 9-16) y +1.5..+13.9. The core midplane (y = 0, where a centre-leg grind sits) lies
  under the divider. One window (with the divider in `dividers`) instead of two windows
  because MKF's field grid covers windingWindows[0] only.
- BASELINE: existing ETD34 (DB "ETD 34/17/11", PC40 assumed) on the Norwe 90642-186
  vertical bobbin, 26 T primary inside / 28 T secondary outside (assumed layout), plus
  L3 = 70 uH on RM8 (assumed design, see run_dab.py).

Coordinates (MKF convention): x = radial distance from the centre-leg axis, y = axial.
"""
from __future__ import annotations

import copy
import functools
import json
import math

import numpy as np

import PyOpenMagnetics as P

MATERIAL = "PC40"
TAPE = 0.055e-3            # 25 um polyester + adhesive per layer (as in the flyback work)
TAPE_LAYERS = 3            # over each winding
RESIDUAL_GAP = 5e-6        # per mating face of an ungapped, lapped pair (assumption)

# custom core shape (seller drawing)
SHAPE_NEW = {"family": "er", "type": "custom", "name": "EC42x15 (seller, ER 42/21.5/15.3)",
             "aliases": [], "magneticCircuit": "open", "familySubtype": None,
             "dimensions": {k: {"nominal": v} for k, v in
                            dict(A=0.0420, B=0.0215, C=0.0153, D=0.0155, E=0.0305, F=0.0152).items()}}

# new bobbin geometry (m)
X_TUBE = 0.0089            # tube outer radius (OD 17.8)
X_FLANGE = 0.0150          # flange radius (OD 30.0)
Y_IN = 0.0139              # half inner winding length (27.8 / 2)
CHAMBERS = {1: (-0.0139, -0.0035), 2: (0.0015, 0.0139)}   # 10.4 mm / 12.4 mm
DIVIDER = (-0.0035, 0.0015)

_loaded = False


def load():
    global _loaded
    if not _loaded:
        P.load_databases({})
        _loaded = True


# Reinforced-insulated litz for the isolated winding (2026-11-18, DAB_TRANSFORMER.md 8):
# 135 x 0.071 mm strands (same copper as the served litz) with an IEC 62368-1 Annex J
# reinforced jacket - taped (Elektrisola EFOLIT, >= 3 tape layers) or triple extruded FEP / PFA /
# ETFE (New England Wire NEWind, Rubadue TCA3 litz). Overall diameter assumed 1.55 mm (bundle
# about 1.1 mm + 2 x 0.2 mm jacket; EFOLIT lists 1.5 mm as its smallest reinforced OD) -
# confirm with the quote. Built on MKF's served 135 x 0.071 record (strand data for the
# losses), only the outer diameter changes.
TIW_LITZ = {"Litz 135x0.071 - Reinforced TIW jacket (OD 1.55)": ("Litz 135x0.071 - Grade 1 - Single Served", 1.55e-3)}


@functools.lru_cache(maxsize=None)
def wire(name: str) -> dict:
    load()
    if name in TIW_LITZ:
        base, od = TIW_LITZ[name]
        w = json.loads(json.dumps(P.find_wire_by_name(base)))
        w["name"] = name
        w["outerDiameter"] = {"nominal": od, "maximum": od}
        w["coating"] = dict(w.get("coating") or {}, type="insulated", numberLayers=3, breakdownVoltage=6000.0)
        return w
    return P.find_wire_by_name(name)


def wire_od(name: str) -> float:
    od = wire(name)["outerDiameter"]
    return od.get("nominal") or od.get("maximum")


def litz_name(n: int, d: str) -> str:
    return f"Litz {n}x{d} - Grade 1 - Single Served"


def core_gapping(kind: str, length: float, columns: int = 3) -> list:
    """kind: 'none' (residual only), 'centre' (ground centre leg), 'spacer' (all legs)."""
    r = {"type": "residual", "length": RESIDUAL_GAP * 2}
    if kind == "none" or length <= 0:
        return [dict(r) for _ in range(columns)]
    if kind == "centre":
        return [{"type": "subtractive", "length": length}] + [dict(r) for _ in range(columns - 1)]
    if kind == "spacer":
        return [{"type": "additive", "length": length} for _ in range(columns)]
    raise ValueError(kind)


def make_core(which: str = "new", gap_kind: str = "none", gap: float = 0.0) -> dict:
    load()
    shape = SHAPE_NEW if which == "new" else "ETD 34/17/11"
    core = {"functionalDescription": {"type": "two-piece set", "shape": shape, "material": MATERIAL,
                                      "numberStacks": 1, "gapping": core_gapping(gap_kind, gap)}}
    return P.calculate_core_data(core, False)


@functools.lru_cache(maxsize=None)
def _bobbin_template() -> dict:
    load()
    return P.find_bobbin_by_name("Bobbin ETD 34 vertical 14-pin (Norwe 90642-186)")


@functools.lru_cache(maxsize=None)
def bobbin_new_json() -> str:
    import json
    b = copy.deepcopy(_bobbin_template())
    b["name"] = "EC42x15 2-chamber 8+8 pin 5.0 mm, rows 40 mm (seller)"
    b["manufacturerInfo"] = {"name": "seller (unbranded)", "reference": "EC42*15 2-slot bobbin"}
    b["distributorsInfo"] = None
    fd = b["functionalDescription"]
    fd["numberChambers"] = 2
    fd["pinout"] = None
    fd["family"] = "er"
    fd["dimensions"] = {}
    pd = b["processedDescription"]
    pd["pins"] = None
    pd["columnShape"] = "round"
    pd["columnWidth"] = X_TUBE
    pd["columnDepth"] = X_TUBE
    pd["columnThickness"] = X_TUBE - 0.0076          # from the ferrite (r 7.6) to the tube OD
    pd["wallThickness"] = 0.0155 - Y_IN              # core window edge to inner flange face
    pd["dividers"] = [{"coordinates": [0.0, (DIVIDER[0] + DIVIDER[1]) / 2, 0.0],
                       "thickness": DIVIDER[1] - DIVIDER[0], "height": X_FLANGE - X_TUBE,
                       "crossingSlot": None}]
    w = X_FLANGE - X_TUBE
    pd["windingWindows"] = [{"angle": None, "area": w * 2 * Y_IN, "column": None,
                             "coordinates": [X_TUBE + w / 2, 0.0], "height": 2 * Y_IN,
                             "radialHeight": None, "sectionsAlignment": None,
                             "sectionsOrientation": "contiguous", "shape": "rectangular",
                             "width": w, "windingOrder": None}]
    return json.dumps(b)


def bobbin(which: str = "new") -> dict:
    import json
    if which == "new":
        return json.loads(bobbin_new_json())
    return copy.deepcopy(_bobbin_template())


def bobbin_window(which: str = "new"):
    ww = bobbin(which)["processedDescription"]["windingWindows"][0]
    xc, yc = ww["coordinates"][0], ww["coordinates"][1]
    return xc - ww["width"] / 2, xc + ww["width"] / 2, yc - ww["height"] / 2, yc + ww["height"] / 2


def turn_length(x: float) -> float:
    return 2 * math.pi * x          # round tube


# ---------------------------------------------------------------------------------------
# Coil layout
#
# winding spec = dict(name, turns, wire, side, y=(y0, y1) axial region, x0 radial start,
#                     tpl = max turns per layer (None = as many as fit),
#                     align = 'centered' | 'low' | 'high' | 'spread'   (axial placement of
#                     the turns of a layer inside y; 'low' = towards smaller y),
#                     tape_after = tape layers over the winding)
# ---------------------------------------------------------------------------------------

def build_coil(windings: list[dict], which: str = "new") -> tuple[dict, dict]:
    load()
    xi, xo, yb, yt = bobbin_window(which)
    sections, layers, turns, func, rep = [], [], [], [], {"windings": []}
    for wi, w in enumerate(windings):
        od = wire_od(w["wire"])
        y0, y1 = w["y"]
        width = y1 - y0
        fit = int(math.floor(width / od + 1e-9))
        tpl = min(fit, w.get("tpl") or fit)
        n = w["turns"]
        nl = math.ceil(n / tpl)
        x = w.get("x0", xi)
        x_start = x
        sname = f"S{wi} {w['name']}"
        align = w.get("align", "centered")
        t = 0
        for li in range(nl):
            k = min(tpl, n - t)
            xc = x + od / 2
            tot = k * od
            if align == "spread" and k > 1:
                g = (width - tot) / (k - 1)
                pos = [y0 + od / 2 + j * (od + g) for j in range(k)]
            else:
                # the block of tpl turns is placed per 'align'; a partial last layer sits at
                # the same side as the block (low/high) or centred
                blk = tpl * od
                if align == "low":
                    ys = y0
                elif align == "high":
                    ys = y1 - blk
                else:
                    ys = y0 + (width - blk) / 2
                if k < tpl:
                    if align == "high":
                        ys = y1 - tot
                    elif align != "low":
                        ys = y0 + (width - tot) / 2
                pos = [ys + od / 2 + j * od for j in range(k)]
            lname = f"{sname} layer {li}"
            layers.append({"coordinateSystem": "cartesian", "coordinates": [xc, (y0 + y1) / 2, 0.0],
                           "dimensions": [od, width], "fillingFactor": tot / width, "name": lname,
                           "orientation": "overlapping",
                           "partialWindings": [{"winding": w["name"], "parallelsProportion": [k / n]}],
                           "section": sname, "turnsAlignment": "spread" if align == "spread" else "centered",
                           "type": "conduction", "windingStyle": "windByConsecutiveTurns"})
            for yy in pos:
                turns.append({"coordinateSystem": "cartesian", "coordinates": [xc, yy],
                              "crossSectionalShape": "round", "dimensions": [od, od], "layer": lname,
                              "length": turn_length(xc), "name": f"{w['name']} parallel 0 turn {t}",
                              "orientation": "clockwise", "parallel": 0, "rotation": 0.0,
                              "section": sname, "winding": w["name"]})
                t += 1
            x += od
        th = x - x_start
        tape = w.get("tape_after", TAPE_LAYERS) * TAPE
        sections.append({"coordinateSystem": "cartesian", "coordinates": [x_start + th / 2, (y0 + y1) / 2, 0.0],
                         "dimensions": [th, width], "fillingFactor": n * od * od / (th * width),
                         "group": "Default group", "layersOrientation": "overlapping",
                         "margin": [y0 - yb, yt - y1], "name": sname,
                         "partialWindings": [{"winding": w["name"], "parallelsProportion": [1.0]}],
                         "type": "conduction", "windingStyle": "windByConsecutiveTurns"})
        func.append({"name": w["name"], "numberTurns": n, "numberParallels": 1, "wire": wire(w["wire"]),
                     "isolationSide": w.get("side", "primary")})
        wire_area = n * od * od
        rep["windings"].append({"name": w["name"], "turns": n, "wire": w["wire"], "od_mm": od * 1e3,
                                "turns_per_layer": tpl, "layers": nl, "build_mm": th * 1e3,
                                "build_with_tape_mm": th * 1e3 + tape * 1e3,
                                "region_mm": [y0 * 1e3, y1 * 1e3], "x0_mm": x_start * 1e3,
                                "fits": x + tape <= xo + 1e-9,
                                "fill_factor_od2": wire_area / (width * (xo - xi)),
                                "copper_fill": n * wire(w["wire"])["numberConductors"] * math.pi
                                * (float(w["wire"].split("x")[1].split()[0]) * 1e-3) ** 2 / 4 / (width * (xo - xi))
                                if wire(w["wire"]).get("type") == "litz" else None})
    coil = {"bobbin": bobbin(which), "functionalDescription": func,
            "groupsDescription": [{"coordinateSystem": "cartesian", "coordinates": [(xi + xo) / 2, (yb + yt) / 2],
                                   "dimensions": [xo - xi, yt - yb], "name": "Default group",
                                   "partialWindings": [{"winding": f["name"], "parallelsProportion": [1.0]} for f in func],
                                   "sectionsOrientation": "contiguous" if which == "new" else "overlapping",
                                   "type": "wound"}],
            "sectionsDescription": sections, "layersDescription": layers, "turnsDescription": turns}
    rep["fits"] = all(r["fits"] for r in rep["windings"])
    return coil, rep


def inductance_matrix(mag: dict, freq: float) -> np.ndarray:
    names = [f["name"] for f in mag["coil"]["functionalDescription"]]
    lm = P.calculate_inductance_matrix(mag, freq, {})["magnitude"]
    L = np.array([[lm[a][b]["nominal"] for b in names] for a in names])
    return 0.5 * (L + L.T)


def leakage_sc(L: np.ndarray) -> float:
    """Primary-referred short-circuit inductance (secondary shorted), what an LCR meter reads."""
    return L[0, 0] - L[0, 1] ** 2 / L[1, 1]


def analyse(windings: list[dict], freq: float, which: str = "new", gap_kind="none", gap=0.0,
            temperature=80.0) -> dict:
    load()
    coil, rep = build_coil(windings, which)
    core = make_core(which, gap_kind, gap)
    mag = {"core": core, "coil": coil}
    L = inductance_matrix(mag, freq)
    lk = P.calculate_leakage_inductance(mag, freq, 0)["leakageInductancePerWinding"][1]["nominal"]
    rdc = P.calculate_dc_resistance_per_winding(coil, temperature)
    N = [w["turns"] for w in windings]
    return {"L": L.tolist(), "Lsc": leakage_sc(L), "Lleak_mkf": lk, "Lm": L[0, 0],
            "k": L[0, 1] / math.sqrt(L[0, 0] * L[1, 1]), "turns": N, "Rdc": [float(r) for r in rdc],
            "geometry": rep, "magnetic": mag, "gap_kind": gap_kind, "gap": gap}
