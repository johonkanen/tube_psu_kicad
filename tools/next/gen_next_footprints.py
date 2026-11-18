#!/usr/bin/env python3
"""Footprints for the next board revision (NEXT_REVISION.md items 1.2 and 2.2), stdlib only.

Writes lib/tube_psu_next.pretty/ - kept apart from lib/tube_psu.pretty, which tools/gen_footprints.py
generates for the 1:1 migration of tube_power_5_1 (tools/check_all.sh checks that library).

  Transformer_EEL19_V_4+6_FlyLeads   new TR1, aux flyback (simulation/flyback/EEL19_DESIGN.md 6a)
  Transformer_EC42x15_2Slot_2x8_P5mm new TR3, DAB (simulation/dab/DAB_TRANSFORMER.md 5, 8)
  L_Toroid_D31.5mm_H16.7mm_Flat_P16.7mm[_TieSlots]  L1 / L2 sendust PFC toroids, flat (NR 5.2)
  Heatsink_Plate_Keepout_L120mm      outline helper for the PFC + DAB bent-plate heatsink (NR 5.5)

3D models: lib/tube_psu_next.3dshapes/<name>.step (tools/next/gen_next_3d.py, CadQuery), referenced
project-relative as ${KIPRJMOD}/../lib/tube_psu_next.3dshapes/... (the project is kicad_next/).

Pin numbering follows the board's EF20 footprint: pins 1..n down the left row, then up the right
row (counter-clockwise seen from the top). Pins that are clipped at the bobbin base get no pad, only
a Fab marker. Dimensions are seller data - confirm with calipers before the layout is finished
(pin diameter -> drill, base outline -> courtyard).

Usage: python3 tools/next/gen_next_footprints.py [--check]
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "lib", "tube_psu_next.pretty")


def f(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def text(kind, value, x, y, layer, size=1.0):
    head = f'(property "{kind}" "{value}"' if kind in ("Reference", "Value") else f'(fp_text user "{value}"'
    return (f"\t{head}\n\t\t(at {f(x)} {f(y)} 0)\n\t\t(layer \"{layer}\")\n"
            f"\t\t(effects\n\t\t\t(font\n\t\t\t\t(size {f(size)} {f(size)})\n\t\t\t\t(thickness 0.15)\n"
            f"\t\t\t)\n\t\t)\n\t)\n")


def poly(pts, layer, width):
    xy = " ".join(f"(xy {f(x)} {f(y)})" for x, y in pts)
    return (f"\t(fp_poly\n\t\t(pts\n\t\t\t{xy}\n\t\t)\n\t\t(stroke\n\t\t\t(width {f(width)})\n"
            f"\t\t\t(type solid)\n\t\t)\n\t\t(fill no)\n\t\t(layer \"{layer}\")\n\t)\n")


def rect(x0, y0, x1, y1, layer, width):
    return poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], layer, width)


def line(x0, y0, x1, y1, layer, width):
    return (f"\t(fp_line\n\t\t(start {f(x0)} {f(y0)})\n\t\t(end {f(x1)} {f(y1)})\n\t\t(stroke\n"
            f"\t\t\t(width {f(width)})\n\t\t\t(type solid)\n\t\t)\n\t\t(layer \"{layer}\")\n\t)\n")


def circle(x, y, r, layer, width):
    return (f"\t(fp_circle\n\t\t(center {f(x)} {f(y)})\n\t\t(end {f(x + r)} {f(y)})\n\t\t(stroke\n"
            f"\t\t\t(width {f(width)})\n\t\t\t(type solid)\n\t\t)\n\t\t(fill no)\n\t\t(layer \"{layer}\")\n\t)\n")


def arc(x0, y0, xm, ym, x1, y1, layer, width):
    return (f"\t(fp_arc\n\t\t(start {f(x0)} {f(y0)})\n\t\t(mid {f(xm)} {f(ym)})\n\t\t(end {f(x1)} {f(y1)})\n"
            f"\t\t(stroke\n\t\t\t(width {f(width)})\n\t\t\t(type solid)\n\t\t)\n\t\t(layer \"{layer}\")\n\t)\n")


def slot(xc, y0, y1, w, layer="Edge.Cuts"):
    """Milled (non-plated) slot along y, x = xc +- w/2, rounded ends (tool diameter w), y0 < y1 are
    the outer ends of the rounded tips. An internal Edge.Cuts outline: KiCad's creepage check and
    the fab's routing both follow it."""
    r = w / 2
    a, b = y0 + r, y1 - r
    return (line(xc - r, a, xc - r, b, layer, 0.05) + arc(xc - r, b, xc, y1, xc + r, b, layer, 0.05)
            + line(xc + r, b, xc + r, a, layer, 0.05) + arc(xc + r, a, xc, y0, xc - r, a, layer, 0.05))


# TR1 creepage slot (2026-11-18, simulation/flyback/EEL19_DESIGN.md 12.6): primary <-> isolated is
# REINFORCED, 552 Vrms -> 11.1 mm creepage (kicad_next/README.md); the pad rows are only 10.8 mm
# apart edge to edge. Slot 1.2 mm wide on the row midline, from 3.25 mm above the top isolated
# pad to 2.5 mm below the fly-lead pads, so FL_DC (9.2 mm direct to pad 5) is also fenced off.
EEL19_SLOT = {"x": 0.0, "y0": -10.0, "y1": 18.0, "w": 1.2}
# Phase 3 (2026-11-18): fly-lead holes moved 1.5 mm down (y 14.0 -> 15.5) and the slot extended to
# y 18.0: the inner layers have no slot credit (kicad_dru "PRI-SEC inner layers" = 11.1 mm straight),
# and FL_DC's barrel was 10.1 mm from pin 5's barrel; now 11.2 mm (pads on the inner layers removed
# where unused - remove_unused_layers - so the barrels set the inner-layer distance).

# TR3 barrier keep-out band (rule area, all copper layers) under the 5 mm divider (x -3.5 .. 1.5):
# 12 mm wide >= 11.1 mm, centred on the divider; the pin rows (x = +-20) stay 13 / 15 mm outside it.
EC42_BAND = {"x0": -7.0, "x1": 5.0}

# L1 / L2 sendust PFC toroids (NR 5.2, seller data): OD 31.5 x H 16.7 mm (+-0.3), mounted flat, two
# leads. Lead spacing 16.7 mm is a guess from the seller drawing - CONFIRM WITH CALIPERS, then change
# "pitch" (and the name) here. Lead holes sit under the rim (lead_y from the toroid centre), so the
# courtyard stays a D 32.5 mm circle; drill for a <= 1.2 mm wire, pad 3.0 mm.
TOROID = {"od": 31.5, "h": 16.7, "id": 13.0, "pitch": 16.7, "lead_y": 11.8, "drill": 1.5, "pad": 3.0,
          "court_d": 32.5, "wire": 1.0,
          # optional cable-tie hold-down: one slot inside the toroid hole, two outside the rim (x axis)
          "tie_w": 1.5, "tie_l": 4.0, "tie_r": 18.5}

# PFC + DAB heatsink (NR 5.5, D3): a new bent aluminium plate, redesigned in the placement. The 5.1
# board has no holes or pads for the bracket (only H1-H8; H4 sits next to the TO row), so this is only
# an outline helper: plate footprint L x T on the board side of the TO-220 / TO-247 tabs, the 4.0 mm
# clearance and 11.1 mm creepage keep-off lines to secondary copper (the plate is primary / earthed -
# README "Consequences of D6"), no pads, board-only. Length / thickness from the placement.
HEATSINK = {"l": 120.0, "t": 3.0, "h": 30.0}


def pad(num, x, y, size, drill, shape="circle", inner=True):
    """Through-hole pad; inner=False removes the annular ring on the inner layers where no track
    connects (KiCad remove_unused_layers, outer layers kept) - for the barrier pads of TR1, whose rows
    are closer than the 11.1 mm inner-layer spacing (the barrels are not)."""
    opt = "" if inner else "\t\t(remove_unused_layers yes)\n\t\t(keep_end_layers yes)\n"
    return (f"\t(pad \"{num}\" thru_hole {shape}\n\t\t(at {f(x)} {f(y)})\n\t\t(size {f(size)} {f(size)})\n"
            f"\t\t(drill {f(drill)})\n\t\t(layers \"*.Cu\" \"*.Mask\")\n{opt}\t)\n")


def footprint(name, descr, tags, body, ref_y, val_y):
    return (f"(footprint \"{name}\"\n\t(version 20260206)\n\t(generator \"tube_psu_next\")\n"
            f"\t(layer \"F.Cu\")\n\t(descr \"{descr}\")\n\t(tags \"{tags}\")\n"
            + text("Reference", "REF**", 0, ref_y, "F.SilkS") + text("Value", name, 0, val_y, "F.Fab")
            + "\t(attr through_hole)\n" + body + text("user", "${REFERENCE}", 0, 0, "F.Fab") + ")\n")


MODEL_DIR = "${KIPRJMOD}/../lib/tube_psu_next.3dshapes"


def model(name, dx=0.0, dy=0.0, rz=0.0):
    """3D model reference (STEP from tools/next/gen_next_3d.py); offset in mm, KiCad's model y is up."""
    return (f"\t(model \"{MODEL_DIR}/{name}.step\"\n\t\t(offset\n\t\t\t(xyz {f(dx)} {f(-dy)} 0)\n\t\t)\n"
            f"\t\t(scale\n\t\t\t(xyz 1 1 1)\n\t\t)\n\t\t(rotate\n\t\t\t(xyz 0 0 {f(rz)})\n\t\t)\n\t)\n")


def footprint_x(name, descr, tags, body, ref_y, val_y, attr="through_hole", models=""):
    """footprint() with a free attribute line and 3D models appended after the graphics."""
    t = footprint(name, descr, tags, body, ref_y, val_y)
    t = t.replace("\t(attr through_hole)\n", f"\t(attr {attr})\n")
    return t[:-2] + models + ")\n"


def keepout(pts, name):
    """Rule area (no tracks, vias, copper pour) on all six copper layers of the 5.2 board."""
    xy = " ".join(f"(xy {f(x)} {f(y)})" for x, y in pts)
    return (f"\t(zone\n\t\t(net 0)\n\t\t(net_name \"\")\n\t\t(layers \"F.Cu\" \"In1.Cu\" \"In2.Cu\" \"In3.Cu\" \"In4.Cu\" \"B.Cu\")\n"
            f"\t\t(name \"{name}\")\n\t\t(hatch edge 0.5)\n\t\t(connect_pads\n\t\t\t(clearance 0)\n\t\t)\n"
            f"\t\t(min_thickness 0.25)\n\t\t(filled_areas_thickness no)\n"
            f"\t\t(keepout\n\t\t\t(tracks not_allowed)\n\t\t\t(vias not_allowed)\n\t\t\t(pads allowed)\n"
            f"\t\t\t(copperpour not_allowed)\n\t\t\t(footprints allowed)\n\t\t)\n"
            f"\t\t(placement\n\t\t\t(enabled no)\n\t\t\t(sheetname \"\")\n\t\t)\n"
            f"\t\t(fill\n\t\t\t(thermal_gap 0.5)\n\t\t\t(thermal_bridge_width 0.5)\n\t\t)\n"
            f"\t\t(polygon\n\t\t\t(pts\n\t\t\t\t{xy}\n\t\t\t)\n\t\t)\n\t)\n")


def clipped(x, y, label):
    """Bobbin pin that is clipped flush with the base: no pad, Fab marker only."""
    return circle(x, y, 0.4, "F.Fab", 0.1) + text("user", label, x, y + 1.0, "F.Fab", 0.5)


def eel19():
    """EEL19 vertical bobbin 4+6 (seller: 4-pin row pitch 3.5 mm, 6-pin row pitch 2.7 mm, rows
    12.5 mm apart). Left row = primary side: 1 A15 finish (15V), 2 GND, 3 A5 finish (AUX_FB),
    pin 4 = P1-P2 crossover post, clipped, no pad. Right row = isolated, upwards from the bottom:
    5 SHV (-80 V), pin 6 spare (clipped, no pad), 7 S5 (5V_ISOL), 8 SN5 (-5V_SEC), 9 ISO_GND,
    10 S15 (15V_ISO_SEC). Fly leads below the body at the pin-4 end: 11 = FL_DC (P1 start, DC+),
    12 = FL_C (P2 finish, collector)."""
    xr = 12.5 / 2
    body = ""
    # body: bobbin base 15.8 x 22.5 mm (5+5 EEL19 bobbin data; confirm the 4+6 base)
    bx, by = 15.8 / 2, 22.5 / 2
    body += rect(-bx, -by, bx, by, "F.Fab", 0.1)
    s = 0.12
    body += line(-bx - s, -by - s, bx + s, -by - s, "F.SilkS", 0.12)
    body += line(bx + s, -by - s, bx + s, by + s, "F.SilkS", 0.12)
    body += line(bx + s, by + s, -bx - s, by + s, "F.SilkS", 0.12)
    body += line(-bx - s, by + s, -bx - s, -by - s, "F.SilkS", 0.12)
    body += line(-bx - 0.8, -5.25, -bx - 0.8, -3.75, "F.SilkS", 0.2)          # pin-1 mark
    # courtyard: body + 0.5 mm, extended down over the fly-lead pads
    c = 0.5
    flx, fly, flp = (-2.2, -7.0), 15.5, 2.2
    # (and over the creepage slot, which runs down past the fly-lead pads)
    sl = EEL19_SLOT
    cx1 = max(max(flx) + flp / 2, sl["x"] + sl["w"] / 2) + 0.25
    cy1 = max(fly + flp / 2, sl["y1"]) + 0.25
    body += poly([(-bx - c, -by - c), (bx + c, -by - c), (bx + c, by + c),
                  (cx1, by + c), (cx1, cy1),
                  (min(flx) - flp / 2 - 0.25, cy1), (min(flx) - flp / 2 - 0.25, by + c),
                  (-bx - c, by + c)], "F.CrtYd", 0.05)
    # primary row (x = -6.25): 1, 2, 3 with pads, 4 clipped
    for i, y in enumerate((-5.25, -1.75, 1.75)):
        body += pad(i + 1, -xr, y, 1.8, 1.0, "rect" if i == 0 else "circle", inner=False)
    body += clipped(-xr, 5.25, "4 clip (crossover)")
    # isolated row (x = +6.25), bottom to top: 5..10, pin 6 clipped
    ys = [6.75 - 2.7 * k for k in range(6)]
    for k, y in enumerate(ys):
        n = 5 + k
        body += clipped(xr, y, "6 clip") if n == 6 else pad(n, xr, y, 1.6, 0.9, inner=False)
    # fly-lead holes (sleeved leads, 0.4-0.5 mm tinned ends)
    body += pad(11, flx[0], fly, flp, 1.2, inner=False)
    body += pad(12, flx[1], fly, flp, 1.2, inner=False)
    body += text("user", "FL_DC", flx[0], fly + 2.0, "F.Fab", 0.6) + text("user", "FL_C", flx[1], fly + 2.0, "F.Fab", 0.6)
    # reinforced-insulation slot between the primary and the isolated side (EEL19_SLOT)
    sl = EEL19_SLOT
    body += slot(sl["x"], sl["y0"], sl["y1"], sl["w"])
    body += text("user", "slot 1.2 (creepage)", sl["x"] + 1.6, sl["y1"] - 1.0, "F.Fab", 0.5)
    descr = ("EEL19 vertical bobbin 4+6 (pitch 3.5 / 2.7 mm, rows 12.5 mm), aux flyback TR1 for the next "
             "revision: pads 1-3 primary-side aux, pin 4 crossover (clipped, no pad), pads 5, 7-10 isolated, "
             "pin 6 spare (clipped), pads 11/12 fly leads FL_DC/FL_C; 1.2 x 28 mm milled slot (Edge.Cuts) between "
             "the rows for 11.1 mm reinforced creepage; body 15.8 x 22.5 mm, height about 29.2 mm "
             "(tube_psu_next, simulation/flyback/EEL19_DESIGN.md 6a; confirm dims with calipers)")
    return footprint_x("Transformer_EEL19_V_4+6_FlyLeads", descr, "transformer EEL19 flyback fly-lead", body,
                       -by - 1.5, sl["y1"] + 1.5, models=model("Transformer_EEL19_V_4p6"))


def ec42():
    """EC42/15 two-chamber horizontal bobbin, 2 x 8 pins, 5.0 mm pitch, rows 40 mm apart (bobbin
    drawing: 46 x 40 mm base, seated height 31.5 mm; core A 42 mm). Left row (pins 1..8, top to
    bottom) = chamber 1 (10.4 mm, primary), right row (9..16, bottom to top) = chamber 2 (12.4 mm,
    secondary). DAB_TRANSFORMER.md 5: two pins per winding end - 1+2 primary start (DHB_CAP),
    7+8 primary finish (bridge), 9+10 secondary start (C16/C55 midpoint), 15+16 secondary finish
    (bridge); pins 3-6 and 11-14 clipped, no pads."""
    xr = 20.0
    used = {1, 2, 7, 8, 9, 10, 15, 16}
    body = ""
    bx, by = 46.0 / 2, 42.0 / 2           # pin bases 46 mm along the axis, core 42 mm across
    body += rect(-bx, -20.0, bx, 20.0, "F.Fab", 0.1)                     # bobbin base 46 x 40
    body += rect(-43.0 / 2, -by, 43.0 / 2, by, "F.Fab", 0.1)             # core 2F 43 x A 42
    body += rect(-30.3 / 2, -15.0, 30.3 / 2, 15.0, "F.Fab", 0.1)          # flanges (30.3 long, dia 30)
    # divider 5 mm: chamber 1 (10.4) from -13.9 to -3.5, divider -3.5..1.5, chamber 2 (12.4) 1.5..13.9
    body += line(-3.5, -15.0, -3.5, 15.0, "F.Fab", 0.1)
    body += line(1.5, -15.0, 1.5, 15.0, "F.Fab", 0.1)
    s = 0.12
    body += line(-bx - s, -by - s, bx + s, -by - s, "F.SilkS", 0.12)
    body += line(bx + s, -by - s, bx + s, by + s, "F.SilkS", 0.12)
    body += line(bx + s, by + s, -bx - s, by + s, "F.SilkS", 0.12)
    body += line(-bx - s, by + s, -bx - s, -by - s, "F.SilkS", 0.12)
    body += line(-bx - 1.0, -17.5 - 0.8, -bx - 1.0, -17.5 + 0.8, "F.SilkS", 0.2)   # pin-1 mark
    body += text("user", "PRI", -xr + 4.0, 0, "F.SilkS") + text("user", "SEC", xr - 4.0, 0, "F.SilkS")
    body += rect(-bx - 0.5, -by - 0.5, bx + 0.5, by + 0.5, "F.CrtYd", 0.05)
    for k in range(8):
        y = -17.5 + 5.0 * k
        for n, x in ((1 + k, -xr), (16 - k, xr)):
            if n in used:
                body += pad(n, x, y, 2.4, 1.2, "rect" if n == 1 else "circle")
            else:
                body += clipped(x, y, f"{n} clip")
    # barrier band under the divider (DAB_TRANSFORMER.md 8): no copper of either domain on any layer, so
    # the primary / secondary planes split under the transformer at >= 11.1 mm (README: inner layers use
    # the outer creepage, no domain overlap between layers). The PCB path pin row to pin row is 40 mm.
    b = EC42_BAND
    body += keepout([(b["x0"], -by - 0.5), (b["x1"], -by - 0.5), (b["x1"], by + 0.5), (b["x0"], by + 0.5)],
                    "TR3 barrier")
    body += rect(b["x0"], -by - 0.5, b["x1"], by + 0.5, "Cmts.User", 0.1)
    body += text("user", "barrier 12 mm (no copper)", (b["x0"] + b["x1"]) / 2, by - 2.0, "Cmts.User", 0.8)
    # core = primary-side part; secondary pin wraps (9/10, 15/16) sit under the secondary core plate
    body += text("user", "core = PRI: tape SEC core plate", xr - 6.0, by - 2.0, "F.Fab", 0.7)
    descr = ("EC42/15 PC40 two-chamber bobbin 2 x 8 pins, pitch 5.0 mm, rows 40 mm, DAB transformer TR3 for "
             "the next revision: pads 1+2 / 7+8 primary (chamber 1, 10.4 mm), 9+10 / 15+16 secondary "
             "(chamber 2, 12.4 mm), pins 3-6 / 11-14 clipped; body 46 x 42 mm, seated height 31.5 mm "
             "(tube_psu_next, simulation/dab/DAB_TRANSFORMER.md 5; confirm dims with calipers)")
    return footprint_x("Transformer_EC42x15_2Slot_2x8_P5mm", descr, "transformer EC42 DAB two-chamber", body,
                       -by - 1.5, by + 1.5, models=model("Transformer_EC42x15_2Slot"))


def toroid_name(ties=False):
    t = TOROID
    return f"L_Toroid_D{t['od']:g}mm_H{t['h']:g}mm_Flat_P{t['pitch']:g}mm" + ("_TieSlots" if ties else "")


def toroid_pads():
    """Lead hole positions (pad 1 left, pad 2 right) relative to the toroid centre = footprint origin."""
    t = TOROID
    return [(1, -t["pitch"] / 2, t["lead_y"]), (2, t["pitch"] / 2, t["lead_y"])]


def npth_slot(x, y, w, l):
    """Non-plated oval hole w x l (long axis along y) - a cable-tie slot."""
    return (f"\t(pad \"\" np_thru_hole oval\n\t\t(at {f(x)} {f(y)})\n\t\t(size {f(w)} {f(l)})\n"
            f"\t\t(drill oval {f(w)} {f(l)})\n\t\t(layers \"*.Cu\" \"*.Mask\")\n\t)\n")


def toroid(ties=False):
    """Flat-mounted toroid, origin = toroid centre, two lead holes under the rim (TOROID)."""
    t = TOROID
    ro, ri = t["od"] / 2, t["id"] / 2
    body = circle(0, 0, ro, "F.Fab", 0.1) + circle(0, 0, ri, "F.Fab", 0.1)
    body += circle(0, 0, ro + 0.15, "F.SilkS", 0.12)
    rc = max(t["court_d"] / 2, max((x * x + y * y) ** 0.5 for _, x, y in toroid_pads()) + t["pad"] / 2 + 0.25)
    body += circle(0, 0, rc, "F.CrtYd", 0.05)
    for n, x, y in toroid_pads():
        body += pad(n, x, y, t["pad"], t["drill"], "rect" if n == 1 else "circle")
    body += text("user", f"leads P{t['pitch']:g} - confirm with calipers", 0, -ri - 2.0, "F.Fab", 0.7)
    if ties:
        body += npth_slot(0, 0, t["tie_w"], t["tie_l"])
        for x in (-t["tie_r"], t["tie_r"]):
            body += npth_slot(x, 0, t["tie_w"], t["tie_l"])
        cx = t["tie_r"] + t["tie_w"] / 2 + 0.25
        body += rect(-cx, -t["tie_l"] / 2 - 0.25, cx, t["tie_l"] / 2 + 0.25, "F.CrtYd", 0.05)
        body += text("user", "cable tie through centre + rim slots", 0, ri + 1.2, "F.Fab", 0.6)
    else:
        body += text("user", "hold-down: RTV / glue (or _TieSlots variant)", 0, ri + 1.2, "F.Fab", 0.6)
    descr = (f"Sendust toroid OD {t['od']:g} x H {t['h']:g} mm (+-0.3) mounted flat, 2 leads at {t['pitch']:g} mm "
             f"spacing under the rim (guess from the seller drawing - confirm with calipers), drill {t['drill']:g} mm, "
             f"courtyard D {2 * rc:g} mm; hold-down " + ("by cable tie (3 NPTH slots)" if ties else "by RTV / glue") +
             " (L1 / L2 PFC chokes, tube_psu_next NR 5.2)")
    return footprint_x(toroid_name(ties), descr, "inductor toroid sendust PFC flat", body, -rc - 1.2, rc + 1.2,
                       models=model(toroid_name()))


def heatsink():
    """Outline helper for the bent-plate heatsink (HEATSINK): origin = centre of the plate's device-side
    face, the plate extends to +y (away from the TO tabs). No pads; board-only."""
    h = HEATSINK
    lx, t = h["l"] / 2, h["t"]
    body = rect(-lx, 0, lx, t, "F.Fab", 0.1)
    body += rect(-lx, 0, lx, t, "F.SilkS", 0.12)
    body += rect(-lx - 0.5, -0.5, lx + 0.5, t + 0.5, "F.CrtYd", 0.05)
    for d, lbl in ((4.0, "4.0 clearance"), (11.1, "11.1 creepage")):
        body += rect(-lx - d, -d, lx + d, t + d, "Cmts.User", 0.1)
        body += text("user", f"no SEC copper: {lbl} (plate = PRI / earth)", 0, t + d - 0.8, "Cmts.User", 0.8)
    body += text("user", "TO tabs on this side (y < 0)", 0, -1.5, "F.Fab", 0.8)
    descr = (f"Outline helper for the PFC + DAB bent aluminium heatsink plate, {h['l']:g} x {h['t']:g} mm footprint "
             f"(height about {h['h']:g} mm); the 5.1 board has no bracket holes, so only the keep-off lines to "
             "secondary copper (4.0 mm clearance / 11.1 mm creepage, plate counted as primary) - bracket feet / holes "
             "from the placement (tube_psu_next NR 5.5)")
    name = f"Heatsink_Plate_Keepout_L{h['l']:g}mm"
    return footprint_x(name, descr, "heatsink bracket keepout", body, -2.5, t + 12.5,
                       attr="board_only exclude_from_pos_files exclude_from_bom",
                       models=model(name))


def main():
    files = {"Transformer_EEL19_V_4+6_FlyLeads.kicad_mod": eel19(),
             "Transformer_EC42x15_2Slot_2x8_P5mm.kicad_mod": ec42(),
             toroid_name() + ".kicad_mod": toroid(),
             toroid_name(True) + ".kicad_mod": toroid(True),
             f"Heatsink_Plate_Keepout_L{HEATSINK['l']:g}mm.kicad_mod": heatsink()}
    if "--check" in sys.argv:
        bad = [n for n, t in files.items()
               if not os.path.exists(os.path.join(OUT, n)) or open(os.path.join(OUT, n)).read() != t]
        print("gen_next_footprints: " + (f"out of date: {bad}" if bad else "up to date"))
        return 1 if bad else 0
    os.makedirs(OUT, exist_ok=True)
    for n, t in files.items():
        open(os.path.join(OUT, n), "w").write(t)
    print(f"gen_next_footprints: wrote {len(files)} footprints to {os.path.relpath(OUT, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
