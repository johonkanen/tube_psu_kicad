#!/usr/bin/env python3
"""Simple STEP models for the 5.2 footprints without a KiCad library model -> lib/tube_psu_next.3dshapes/.

Boxes / cylinders with the outer dimensions that matter for the 3D render and the enclosure height check
(not mechanical drawings). Model origin = footprint origin; KiCad's model y axis points up, so a
footprint point (x, y) is (x, -y) here. Dimensions: seller / datasheet data, marked "caliper" where a
measurement of the bought part is still needed (kicad_next/README.md, footprints and 3D).

Needs CadQuery (not in the KiCad AppImage):
    python3 -m venv ~/.venvs/cq && ~/.venvs/cq/bin/pip install cadquery
    ~/.venvs/cq/bin/python tools/next/gen_next_3d.py [--check]
The STEP header timestamp is fixed; OCC orders the colour (STYLED_ITEM) records by memory address, so
--check and the rewrite decision compare the geometry part plus the set of colours (same_model()).
tools/next/check_footprints.py (in check_next.sh) checks that every referenced model file exists.
"""
import os
import re
import sys

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_next_footprints as gfp  # noqa: E402  (toroid / heatsink / transformer parameters)

ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "lib", "tube_psu_next.3dshapes")

BLACK, GREY, COPPER, PIN, TAPE = (0.1, 0.1, 0.1), (0.45, 0.45, 0.48), (0.72, 0.45, 0.2), (0.85, 0.85, 0.85), (0.9, 0.8, 0.2)
SLEEVE, ALU, RELAY = (0.12, 0.15, 0.35), (0.8, 0.8, 0.82), (0.15, 0.25, 0.6)


def box(x0, y0, z0, x1, y1, z1):
    """Axis-aligned box from footprint coordinates (y down) -> model coordinates (y up)."""
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, -y1, z0))


def cyl(x, y, z0, z1, d):
    return cq.Workplane("XY").circle(d / 2).extrude(z1 - z0).translate((x, -y, z0))


def pins(pts, d, z0=-3.5, z1=0.5):
    w = None
    for x, y in pts:
        c = cyl(x, y, z0, z1, d)
        w = c if w is None else w.union(c)
    return w


# --- models: name -> list of (Workplane, rgb) -------------------------------------------------------
def eel19():
    """EEL19 vertical 4+6 with the TIW winding: envelope about 20 x 23 x 29.2 mm (seller); base 15.8 x 22.5
    (5+5 bobbin data) - caliper: 4+6 base outline, pin diameter, seated height."""
    xr = 6.25
    pp = [(-xr, y) for y in (-5.25, -1.75, 1.75)] + [(xr, 6.75 - 2.7 * k) for k in range(6) if k != 1]
    return [(box(-7.9, -11.25, 0.4, 7.9, 11.25, 3.4), BLACK),          # bobbin base
            (box(-7.5, -11.5, 3.4, 7.5, 11.5, 27.0), TAPE),             # winding + tape
            (box(-10.0, -5.0, 3.4, 10.0, 5.0, 29.2), GREY),             # core
            (pins(pp, 0.8), PIN),
            (pins([(-2.2, 15.5), (-7.0, 15.5)], 0.9, z1=3.0), PIN)]     # fly leads (sleeved)


def ec42():
    """EC42/15 two-chamber horizontal: 46 x 42 x 31.5 mm (bobbin drawing); winding D 30 on the x axis at
    z 16.5, core 43 x 42, core depth 15 assumed - caliper: core set, seated height, core-to-board gap."""
    used = [(-20.0, -17.5 + 5.0 * k) for k in (0, 1, 6, 7)] + [(20.0, -17.5 + 5.0 * k) for k in (0, 1, 6, 7)]
    wind = cq.Workplane("YZ").polygon(24, 30.0).extrude(30.3).translate((-15.15, 0, 16.5))   # 24-gon: STEP points reach z 31.5
    return [(box(-23.0, -20.0, 0.4, -18.0, 20.0, 5.0), BLACK), (box(18.0, -20.0, 0.4, 23.0, 20.0, 5.0), BLACK),
            (wind, TAPE), (box(-21.5, -21.0, 9.0, 21.5, 21.0, 24.0), GREY), (pins(used, 1.0), PIN)]


def toroid():
    t = gfp.TOROID
    ring = (cq.Workplane("XY").circle(t["od"] / 2).circle(t["id"] / 2).extrude(t["h"])
            .edges().fillet(2.0))
    return [(ring, COPPER), (pins([(x, y) for _, x, y in gfp.toroid_pads()], t["wire"], z1=3.0), COPPER)]


def toroid_v(rot):
    """Upright toroid (ring plane along x, standing on the board) with its two leads into the RM8 holes."""
    t = gfp.TOROID_V
    pads, (cx, cy) = gfp.toroid_v_geometry(rot)
    ro, ri = t["od"] / 2, t["id"] / 2
    ring = (cq.Workplane("XZ").circle(ro).circle(ri).extrude(t["w"] / 2, both=True)
            .edges().fillet(2.0).translate((cx, -cy, ro)))
    leads = None
    for _, x, y in pads:
        dx = min(abs(x - cx), ro - 0.5)
        z1 = ro - (ro * ro - dx * dx) ** 0.5 + 1.0          # up into the winding above the hole
        c = cyl(x, y, -3.5, z1, t["wire"])
        leads = c if leads is None else leads.union(c)
    return [(ring, COPPER), (leads, COPPER)]


def heatsink():
    h = gfp.HEATSINK
    return [(box(-h["l"] / 2, 0, 0, h["l"] / 2, h["t"], h["h"]), ALU)]


def cp(d, h, p):
    """Radial electrolytic: can D x H centred between the leads (pad 1 at the origin)."""
    lead = 0.8 if d >= 10 else 0.6
    return [(cyl(p / 2, 0, 0.5, h - 0.4, d), SLEEVE), (cyl(p / 2, 0, h - 0.4, h, d - 0.6), ALU),
            (pins([(0, 0), (p, 0)], lead), PIN)]


MODELS = {
    "Transformer_EEL19_V_4p6": eel19,
    "Transformer_EC42x15_2Slot": ec42,
    gfp.toroid_name(): toroid,
    f"Heatsink_Plate_Keepout_L{gfp.HEATSINK['l']:g}mm": heatsink,
    "CP_Radial_D10.0mm_P5.00mm_H50mm": lambda: cp(10.0, 50.0, 5.0),      # C19 / C30 KCXE5002W680MF 10 x 50
    "CP_Radial_D10.0mm_P5.00mm_H18mm": lambda: cp(10.0, 18.0, 5.0),      # C102 KCXE1802E560MF 10 x 18
    "CP_Radial_D12.5mm_P5.00mm_H45mm": lambda: cp(12.5, 45.0, 5.0),      # C28/29/37/56 ERT826M2WI45RRS0F-R
    "CP_Radial_D8.0mm_P3.50mm_H20mm": lambda: cp(8.0, 20.0, 3.5),        # C31 / C32 10ZLH1500MEFCT78X20
    # forks of lib/tube_psu.pretty (body outlines = the footprints' Fab rectangles)
    "D_Bridge_TBS": lambda: [(box(-4.375, -3.35, 0, 4.225, 3.35, 2.6), BLACK)],          # height 2.6 assumed
    "L_CommonMode_SCF20-05-550": lambda: [(box(-7.75, -12.5, 0, 7.75, 12.5, 25.0), BLACK),  # KEMET 15.5 x 25 x 25 max
                                          (pins([(-6, -7), (6, -7), (-6, 7), (6, 7)], 0.8), PIN)],
    "R_0508_1220Metric_KRL2012": lambda: [(box(-0.625, -1.0, 0, 0.625, 1.0, 0.55), BLACK),   # KRL2012 1.25 x 2.0 x 0.55
                                          (box(-0.625, -1.0, 0, -0.4, 1.0, 0.56), PIN),
                                          (box(0.4, -1.0, 0, 0.625, 1.0, 0.56), PIN)],
    "Relay_Songle_SRD_5pin": lambda: [(box(-8.8745, -8.003, 0, 8.4035, 7.751, 15.3), RELAY)],  # SRD height 15.3
    "Terminal_Blade_2x1_P5.00mm": lambda: [(box(-3.5, -1.0, 0, 3.5, 1.0, 1.0), PIN),        # 6.3 mm blade tab
                                           (box(-3.15, -0.4, 1.0, 3.15, 0.4, 9.0), PIN),
                                           (pins([(-2.5, 0), (2.5, 0)], 1.2, z1=0.1), PIN)],
    "Transformer_EF25_2x5_P5.08mm_8pin": lambda: [(box(-8.65, -13.84, 0.4, 8.35, 14.16, 4.0), BLACK),
                                                  (box(-8.0, -12.5, 4.0, 7.7, 12.5, 22.0), GREY)],  # height 22 assumed
    # L1 / L2 upright on the 5.1 RM8 holes (2026-11-19); last in the dict: OCC numbers the assembly
    # occurrences per process, so models added in front would renumber (and rewrite) every later file
    **{gfp.toroid_v_name(r): (lambda r=r: toroid_v(r)) for r in gfp.TOROID_V["variants"]},
}


def export(name, parts):
    assy = cq.Assembly(name=name)
    for i, (wp, rgb) in enumerate(parts):
        assy.add(wp, name=f"{name}_{i}", color=cq.Color(*rgb))
    path = os.path.join(OUT, name + ".step")
    tmp = path + ".tmp"
    assy.export(tmp, "STEP")
    t = open(tmp).read()
    os.remove(tmp)
    t = re.sub(r"FILE_NAME\('[^']*','[^']*'", f"FILE_NAME('{name}.step','2026-11-18T00:00:00'", t, count=1)
    return path, t


def key(t):
    """Geometry records (everything before the colour presentation) + the sorted colour values."""
    i = t.find("MECHANICAL_DESIGN_GEOMETRIC_PRESENTATION_REPRESENTATION")
    return t[:i], sorted(re.findall(r"COLOUR_RGB\([^;]*;", t))


def same_model(path, t):
    return os.path.exists(path) and key(open(path).read()) == key(t)


def main(argv):
    os.makedirs(OUT, exist_ok=True)
    bad = []
    for name, fn in MODELS.items():
        path, t = export(name, fn())
        if "--check" in argv:
            if not same_model(path, t):
                bad.append(name)
            continue
        if not same_model(path, t):
            open(path, "w").write(t)
    if "--check" in argv:
        print("gen_next_3d: " + (f"out of date: {bad}" if bad else f"{len(MODELS)} models up to date"))
        return 1 if bad else 0
    print(f"gen_next_3d: wrote {len(MODELS)} STEP models to {os.path.relpath(OUT, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
