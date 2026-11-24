#!/usr/bin/env python3
"""Footprints of 5.2 parts that the KiCad standard library does not have as needed, stdlib only.

Writes lib/tube_psu_next_parts.pretty/ (library nickname tube_psu_next_parts in kicad_next/fp-lib-table).
Kept apart from tools/next/gen_next_footprints.py (transformers, toroids, heatsink helper, lib/tube_psu_next.pretty).

  SOIC-16W_7.5x10.3mm_P1.27mm_Slot8.0_T_ISO1       board-specific ISO1 variant: the slot as a T (cross slot past the
      pin 8 / 9 end; trial placement step 3)
  SOIC-16W_7.5x10.3mm_P1.27mm_Slot8.0 / _Slot11.1   KiCad SOIC-16W + milled creepage slot (Edge.Cuts) under
      the body, for the isolators that straddle a reinforced barrier: ISO1 (primary <-> heater 8.0 mm),
      U11 (primary <-> UART 8.0 mm), ISO2 (primary <-> DAB secondary 11.1 mm). Pads, silk, fab and the
      3D model are the KiCad library footprint's; the courtyard grows over the slot ends.
  PG-DSO-12_3.9x9.9mm_P1.27mm   Infineon PG-DSO-12 (ICE5AR0680AG, PWM2): KiCad SOIC-16 narrow with SO-16
      positions 5, 6, 11, 12 removed and the pads renumbered 1-12 (datasheet figure 39: e 1.27, b1 3.81 BSC)
  CP_Radial_*_H<height>mm        KiCad CP_Radial footprints with a 3D model of the real can height (the
      library models are 8 / 10 / 12.5 mm tall; the 5.2 parts are 18-50 mm)
  TO-220-2_Vertical_KA           SICD1 / SICD2 (C3D02060A): the 5.1 TO-220-2_Vertical_AK with pin 1 named K,
      pin 2 named A (data sheet pin-out; stage 16a)
  forks of lib/tube_psu.pretty footprints that have no (or a missing) 3D model: same name, pads and
      graphics, model from lib/tube_psu_next.3dshapes (lib/tube_psu.pretty is the frozen 5.1 library)

KiCad library footprints are read from the KiCad 10 AppImage ($KICAD_MOUNT, set by
tools/p2k/bin/kicad_env.sh): run as  tools/p2k/bin/kicad_env.sh python3 tools/next/gen_next_footprints_parts.py
3D models: tools/next/gen_next_3d.py (CadQuery) -> lib/tube_psu_next.3dshapes.

Usage: python3 tools/next/gen_next_footprints_parts.py [--check]
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "lib", "tube_psu_next_parts.pretty")


def f(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def text(kind, value, x, y, layer, size=1.0):
    head = f'(property "{kind}" "{value}"' if kind in ("Reference", "Value") else f'(fp_text user "{value}"'
    return (f"\t{head}\n\t\t(at {f(x)} {f(y)} 0)\n\t\t(layer \"{layer}\")\n"
            f"\t\t(effects\n\t\t\t(font\n\t\t\t\t(size {f(size)} {f(size)})\n\t\t\t\t(thickness 0.15)\n"
            f"\t\t\t)\n\t\t)\n\t)\n")


def rect(x0, y0, x1, y1, layer, width):
    xy = " ".join(f"(xy {f(x)} {f(y)})" for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)))
    return (f"\t(fp_poly\n\t\t(pts\n\t\t\t{xy}\n\t\t)\n\t\t(stroke\n\t\t\t(width {f(width)})\n"
            f"\t\t\t(type solid)\n\t\t)\n\t\t(fill no)\n\t\t(layer \"{layer}\")\n\t)\n")


def line(x0, y0, x1, y1, layer, width):
    return (f"\t(fp_line\n\t\t(start {f(x0)} {f(y0)})\n\t\t(end {f(x1)} {f(y1)})\n\t\t(stroke\n"
            f"\t\t\t(width {f(width)})\n\t\t\t(type solid)\n\t\t)\n\t\t(layer \"{layer}\")\n\t)\n")


def smd(num, x, y, w, h):
    return (f"\t(pad \"{num}\" smd roundrect\n\t\t(at {f(x)} {f(y)})\n\t\t(size {f(w)} {f(h)})\n"
            f"\t\t(layers \"F.Cu\" \"F.Mask\" \"F.Paste\")\n\t\t(roundrect_rratio 0.25)\n\t)\n")


def footprint(name, descr, tags, body, ref_y, val_y):
    return (f"(footprint \"{name}\"\n\t(version 20260206)\n\t(generator \"tube_psu_next_parts\")\n"
            f"\t(layer \"F.Cu\")\n\t(descr \"{descr}\")\n\t(tags \"{tags}\")\n"
            + text("Reference", "REF**", 0, ref_y, "F.SilkS") + text("Value", name, 0, val_y, "F.Fab")
            + "\t(attr smd)\n" + body + text("user", "${REFERENCE}", 0, 0, "F.Fab", 0.8) + ")\n")


MODEL_DIR = "${KIPRJMOD}/../lib/tube_psu_next.3dshapes"
LIB51 = os.path.join(ROOT, "lib", "tube_psu.pretty")


def kicad_fp(lib, name):
    mount = os.environ.get("KICAD_MOUNT")
    if not mount:
        sys.exit("gen_next_footprints_parts: KICAD_MOUNT not set - run through tools/p2k/bin/kicad_env.sh")
    return open(os.path.join(mount, "share", "kicad", "footprints", lib + ".pretty", name + ".kicad_mod")).read()


def blocks(text):
    """Split a .kicad_mod into its head line, top-level child blocks (text incl. newline) and the tail."""
    lines = text.splitlines(keepends=True)
    head, kids, cur, depth = lines[0], [], "", 0
    for ln in lines[1:-1]:
        cur += ln
        depth += ln.count("(") - ln.count(")")      # no parentheses inside strings in these files
        if depth == 0:
            kids.append(cur)
            cur = ""
    assert cur == "" and lines[-1].strip() == ")", "unexpected footprint layout"
    return head, kids, lines[-1]


def model_block(name, dx=0.0, dy=0.0):
    return (f"\t(model \"{MODEL_DIR}/{name}.step\"\n\t\t(offset\n\t\t\t(xyz {f(dx)} {f(-dy)} 0)\n\t\t)\n"
            f"\t\t(scale\n\t\t\t(xyz 1 1 1)\n\t\t)\n\t\t(rotate\n\t\t\t(xyz 0 0 0)\n\t\t)\n\t)\n")


def derive(src, name, descr_add, drop=lambda b: False, add=(), model=None):
    """Copy a footprint: rename, append to descr, drop blocks, add blocks before the models, replace the
    models by `model` (a block) if given."""
    head, kids, tail = blocks(src)
    old = re.match(r'\(footprint "([^"]+)"', head).group(1)
    head = head.replace(f'"{old}"', f'"{name}"', 1)
    out = []
    for b in kids:
        if drop(b):
            continue
        if model is not None and b.startswith("\t(model"):
            continue
        if b.startswith("\t(descr"):
            b = b.rstrip()[:-2] + f" - {descr_add}\")\n"
        if b.startswith('\t(property "Value"'):
            b = b.replace(f'"Value" "{old}"', f'"Value" "{name}"')
        if b.startswith("\t(generator ") and not b.startswith('\t(generator "tube_psu'):
            b = '\t(generator "tube_psu_next_parts")\n'
        if b.startswith("\t(model") and add:
            out.extend(add)
            add = ()
        out.append(b)
    out.extend(add)
    if model is not None:
        out.append(model)
    return head + "".join(out) + tail


# --- SOIC-16W with a creepage slot ------------------------------------------------------------------
# KiCad SOIC-16W: pads 2.05 x 0.6 at x = +-4.65 -> pad row gap 7.25 mm (< 8.0 / 11.1 mm creepage).
# Slot 1.5 mm wide on x = 0 from -ys to +ys (design review 2026-11-23, findings 10 F2 / 14 F3: was 1.0 mm = JLC's
# minimum non-plated slot; JLC mills to +-0.2 mm and IEC 60664-1 ignores a groove narrower than 1.0 mm at PD2, so
# 1.5 mm keeps >= 1.3 mm after tolerance; pad rows stay 2.875 mm from the slot edge). Shortest surface path
# from the inner corner of an end pad (3.625, 4.745) around the slot tip to the other row:
# 2 * sqrt(3.625^2 + (ys - 4.745)^2) (+ half the tip arc), computed exactly by tools/next/check_footprints.py.
SOIC_SLOTS = {"8.0": 7.25, "11.1": 9.75}      # required creepage (mm) -> slot half length ys (mm)
SOIC_SLOT_W = 1.5


def slot_lines(xc, y0, y1, w):
    r = w / 2
    a, b = y0 + r, y1 - r
    def ln(x0, y0_, x1, y1_):
        return (f"\t(fp_line\n\t\t(start {f(x0)} {f(y0_)})\n\t\t(end {f(x1)} {f(y1_)})\n\t\t(stroke\n"
                f"\t\t\t(width 0.05)\n\t\t\t(type solid)\n\t\t)\n\t\t(layer \"Edge.Cuts\")\n\t)\n")
    def arc(x0, y0_, xm, ym, x1, y1_):
        return (f"\t(fp_arc\n\t\t(start {f(x0)} {f(y0_)})\n\t\t(mid {f(xm)} {f(ym)})\n\t\t(end {f(x1)} {f(y1_)})\n"
                f"\t\t(stroke\n\t\t\t(width 0.05)\n\t\t\t(type solid)\n\t\t)\n\t\t(layer \"Edge.Cuts\")\n\t)\n")
    return (ln(xc - r, a, xc - r, b) + arc(xc - r, b, xc, y1, xc + r, b)
            + ln(xc + r, b, xc + r, a) + arc(xc + r, a, xc, y0, xc - r, a))


def poly(pts, layer, width):
    xy = " ".join(f"(xy {f(x)} {f(y)})" for x, y in pts)
    return (f"\t(fp_poly\n\t\t(pts\n\t\t\t{xy}\n\t\t)\n\t\t(stroke\n\t\t\t(width {f(width)})\n"
            f"\t\t\t(type solid)\n\t\t)\n\t\t(fill no)\n\t\t(layer \"{layer}\")\n\t)\n")


def split_silk(b, gap):
    """A horizontal F.SilkS line crossing x = 0 -> two lines leaving +-gap free over the slot."""
    m = re.search(r"\(start (\S+) (\S+)\)\s*\(end (\S+) (\S+)\)", b)
    x0, y0, x1, y1 = map(float, m.groups())
    if '"F.SilkS"' not in b or y0 != y1 or not (min(x0, x1) < 0 < max(x0, x1)):
        return [b]
    lo, hi = min(x0, x1), max(x0, x1)
    out = []
    for a, c in ((lo, -gap), (gap, hi)):
        out.append(b[:m.start()] + f"(start {f(a)} {f(y0)})\n\t\t(end {f(c)} {f(y0)})" + b[m.end():])
    return out


def soic16w_slot(creep):
    ys, w = SOIC_SLOTS[creep], SOIC_SLOT_W
    src = kicad_fp("Package_SO", "SOIC-16W_7.5x10.3mm_P1.27mm")
    head, kids, tail = blocks(src)
    kids2 = []
    for b in kids:
        if '(layer "F.CrtYd")' in b:
            continue
        kids2.extend(split_silk(b, w / 2 + 0.3) if b.startswith("\t(fp_line") else [b])
    src = head + "".join(kids2) + tail
    cx, cy, sx, sy = 5.93, 5.4, w / 2 + 0.25, ys + 0.25     # library courtyard x / y, slot extension
    court = poly([(-cx, -cy), (-sx, -cy), (-sx, -sy), (sx, -sy), (sx, -cy), (cx, -cy), (cx, cy), (sx, cy),
                  (sx, sy), (-sx, sy), (-sx, cy), (-cx, cy)], "F.CrtYd", 0.05)
    note = ('\t(fp_text user "slot %s (creepage %s)"\n\t\t(at 0 %s 90)\n\t\t(layer "F.Fab")\n\t\t(effects\n'
            '\t\t\t(font\n\t\t\t\t(size 0.5 0.5)\n\t\t\t\t(thickness 0.08)\n\t\t\t)\n\t\t)\n\t)\n'
            % (f"{w:g}x{2 * ys:g}", creep, f(-ys + 2.5)))
    return derive(src, f"SOIC-16W_7.5x10.3mm_P1.27mm_Slot{creep}",
                  f"{w:g} x {2 * ys:g} mm milled slot (Edge.Cuts) between the pad rows for {creep} mm reinforced "
                  "creepage on the PCB (tube_psu_next_parts, check_footprints.py)",
                  add=(slot_lines(0, -ys, ys, w), court, note))


# Board-specific variant for ISO1 (trial placement step 3, user decision 2026-11-19): the slot continues as a T
# - a cross slot of the same width past the pin-8 / pin-9 end, towards the pin 1-8 side - so that the surface path from the
# primary pins 5-8 to the heater pins next to that end (TR2 pad 10, WP4) goes round the cross slot. One closed
# Edge.Cuts outline (KiCad rejects two overlapping slot outlines as self-intersecting; a separate slot would
# leave a 1 x 1 mm web). Footprint coordinates: stem x = +-w/2 from the tip at y = -7.25 to the bar, bar
# y = 9.25 - w ... 9.25 from x = -11.35 (10.85 mm past the pin 1-8 pad row side) to x = 3.15; outer ends rounded by
# the cutter (r = w/2), the two inner corners are drawn sharp (the cutter leaves r >= w/2 there, i.e. more slot).
# Width 1.5 mm since 2026-11-23 (was 1.0, y 8.25 ... 9.25): the bar grows towards ISO1 only, its edge at TR2 pad 10
# (y = 9.25) stays where it was.
# ISO1 is placed at 180 deg: board x = x0 - x, y = y0 - y.
SOIC_T = {"ISO1": dict(creep="8.0", bar_y0=9.25 - SOIC_SLOT_W, bar_y1=9.25, bar_x0=-11.35, bar_x1=3.15)}


def edge_line(x0, y0, x1, y1):
    return (f"\t(fp_line\n\t\t(start {f(x0)} {f(y0)})\n\t\t(end {f(x1)} {f(y1)})\n\t\t(stroke\n"
            f"\t\t\t(width 0.05)\n\t\t\t(type solid)\n\t\t)\n\t\t(layer \"Edge.Cuts\")\n\t)\n")


def edge_arc(x0, y0, xm, ym, x1, y1):
    return (f"\t(fp_arc\n\t\t(start {f(x0)} {f(y0)})\n\t\t(mid {f(xm)} {f(ym)})\n\t\t(end {f(x1)} {f(y1)})\n"
            f"\t\t(stroke\n\t\t\t(width 0.05)\n\t\t\t(type solid)\n\t\t)\n\t\t(layer \"Edge.Cuts\")\n\t)\n")


def soic16w_slot_t(ref):
    t = SOIC_T[ref]
    ys, w = SOIC_SLOTS[t["creep"]], SOIC_SLOT_W
    r = w / 2
    y0, y1, x0, x1 = t["bar_y0"], t["bar_y1"], t["bar_x0"], t["bar_x1"]
    assert abs((y1 - y0) - w) < 1e-9 and y0 > ys
    src = kicad_fp("Package_SO", "SOIC-16W_7.5x10.3mm_P1.27mm")
    head, kids, tail = blocks(src)
    kids2 = []
    for b in kids:
        if '(layer "F.CrtYd")' in b:
            continue
        kids2.extend(split_silk(b, w / 2 + 0.3) if b.startswith("\t(fp_line") else [b])
    src = head + "".join(kids2) + tail
    ym = (y0 + y1) / 2
    outline = (edge_arc(-r, -ys + r, 0, -ys, r, -ys + r) + edge_line(r, -ys + r, r, y0)
               + edge_line(r, y0, x1 - r, y0) + edge_arc(x1 - r, y0, x1, ym, x1 - r, y1)
               + edge_line(x1 - r, y1, x0 + r, y1) + edge_arc(x0 + r, y1, x0, ym, x0 + r, y0)
               + edge_line(x0 + r, y0, -r, y0) + edge_line(-r, y0, -r, -ys + r))
    cx, cy, sx, sy, m = 5.93, 5.4, w / 2 + 0.25, ys + 0.25, 0.25
    court = poly([(-cx, -cy), (-sx, -cy), (-sx, -sy), (sx, -sy), (sx, -cy), (cx, -cy), (cx, cy), (sx, cy),
                  (sx, y1 + m), (-sx, y1 + m), (-sx, cy), (-cx, cy)], "F.CrtYd", 0.05)   # body + stem only: the bar runs
    # under the edge of the neighbouring transformer (TR2), the board edge clearance keeps copper off it
    note = ('\t(fp_text user "T slot %s (creepage %s)"\n\t\t(at 0 %s 90)\n\t\t(layer "F.Fab")\n\t\t(effects\n'
            '\t\t\t(font\n\t\t\t\t(size 0.5 0.5)\n\t\t\t\t(thickness 0.08)\n\t\t\t)\n\t\t)\n\t)\n'
            % (f"{w:g}", t["creep"], f(-ys + 2.5)))
    return derive(src, f"SOIC-16W_7.5x10.3mm_P1.27mm_Slot{t['creep']}_T_{ref}",
                  f"board-specific for {ref}: {w:g} mm milled T slot (Edge.Cuts) - the slot between the pad rows "
                  f"(tip at y = {-ys:g}) plus a cross slot y {y0:g} ... {y1:g}, x {x0:g} ... {x1:g} past the pin 8 / 9 end, "
                  f"for {t['creep']} mm reinforced creepage to the parts next to that end (tube_psu_next_parts, "
                  "check_footprints.py)", add=(outline, court, note))


# --- Infineon PG-DSO-12 (ICE5AR0680AG) ------------------------------------------------------------------
# Datasheet V2.3 figure 39: body D 9.8-10.0 x E1 3.8-4.0 mm, lead span E 5.8-6.2 mm, b 0.35-0.51, L 0.39-0.89,
# e 1.27 mm, b1 = 3.81 mm (BSC) from pin 4 to pin 5 (and 9 to 8) = an SO-16 narrow (JEDEC MS-012 AC) body with
# two lead positions missing per side. Not KiCad's Infineon_PG-DSO-12-9 / -11 (7.5 mm exposed-pad packages).
# KiCad SOIC-16 pad -> PG-DSO-12 pin (None = no pad): left column 1-8 top to bottom, right 9-16 bottom to top.
# Pins 5-8 (DRAIN) sit at the pin-5/6 end; the nearest other pads are 4 (CS) and 9 (NC) across the 3.81 mm
# gap (3.21 mm copper to copper).
DSO12_MAP = {1: 1, 2: 2, 3: 3, 4: 4, 5: None, 6: None, 7: 5, 8: 6,
             9: 7, 10: 8, 11: None, 12: None, 13: 9, 14: 10, 15: 11, 16: 12}


def pg_dso12():
    src = kicad_fp("Package_SO", "SOIC-16_3.9x9.9mm_P1.27mm")
    head, kids, tail = blocks(src)
    out = []
    for b in kids:
        m = re.match(r'\t\(pad "(\d+)"', b)
        if m:
            new = DSO12_MAP[int(m.group(1))]
            if new is None:
                continue
            b = b.replace(f'(pad "{m.group(1)}"', f'(pad "{new}"', 1)
        if b.startswith("\t(descr"):
            b = ('\t(descr "Infineon PG-DSO-12, 12 pins, SO-16 narrow body (JEDEC MS-012 AC) with lead positions 5, 6, '
                 '11, 12 empty (ICE5AR0680AG datasheet V2.3 figure 39)")\n')
        if b.startswith("\t(tags"):
            b = '\t(tags "PG-DSO-12 DSO-12 ICE5AR0680AG CoolSET SOIC-16 narrow")\n'
        out.append(b)
    return derive(head + "".join(out) + tail, "PG-DSO-12_3.9x9.9mm_P1.27mm",
                  "pads = KiCad SOIC-16_3.9x9.9mm_P1.27mm without 5, 6, 11, 12, renumbered 1-12, 5-8 = DRAIN; "
                  "3D model = KiCad SOIC-16 (16 leads drawn) (tube_psu_next_parts)")


# --- electrolytics: KiCad footprint, model of the real height ----------------------------------------
# (refdes, part): C19/C30 KCXE5002W680MF 10x50, C102 KCXE1802E560MF 10x18, C29 (C28/C37/C56 Proteus pads)
# ERT826M2WI45RRS0F-R 12.5x45, C31/C32 10ZLH1500MEFCT78X20 8x20 (JLC package strings, 2026-11-18)
CP_VARIANTS = {   # name -> (source library or None for lib/tube_psu.pretty, source name, model)
    "CP_Radial_D10.0mm_P5.00mm_H50mm": ("Capacitor_THT", "CP_Radial_D10.0mm_P5.00mm", "CP_Radial_D10.0mm_P5.00mm_H50mm"),
    "CP_Radial_D10.0mm_P5.00mm_H18mm": ("Capacitor_THT", "CP_Radial_D10.0mm_P5.00mm", "CP_Radial_D10.0mm_P5.00mm_H18mm"),
    "CP_Radial_D12.5mm_P5.00mm_H45mm": ("Capacitor_THT", "CP_Radial_D12.5mm_P5.00mm", "CP_Radial_D12.5mm_P5.00mm_H45mm"),
    "CP_Radial_D12.5mm_P5.00mm_Proteus_H45mm": (None, "CP_Radial_D12.5mm_P5.00mm_Proteus", "CP_Radial_D12.5mm_P5.00mm_H45mm"),
    "CP_Radial_D8.0mm_P3.50mm_H20mm": ("Capacitor_THT", "CP_Radial_D8.0mm_P3.50mm", "CP_Radial_D8.0mm_P3.50mm_H20mm"),
}


def cp_variant(name):
    lib, src_name, mdl = CP_VARIANTS[name]
    src = kicad_fp(lib, src_name) if lib else open(os.path.join(LIB51, src_name + ".kicad_mod")).read()
    h = re.search(r"_H(\d+)mm", name).group(1)
    return derive(src, name, f"3D model with the real can height {h} mm (tube_psu_next_parts)",
                  model=model_block(mdl))


# --- forks of 5.1 footprints without a usable 3D model -----------------------------------------------
FORKS = {   # 5.1 footprint name -> model name in lib/tube_psu_next.3dshapes
    "D_Bridge_TBS": "D_Bridge_TBS",
    "L_CommonMode_SCF20-05-550": "L_CommonMode_SCF20-05-550",
    "R_0508_1220Metric_KRL2012": "R_0508_1220Metric_KRL2012",     # 5.1 model path missing in KiCad 10
    "Relay_Songle_SRD_5pin": "Relay_Songle_SRD_5pin",
    "Terminal_2x1_P5.00mm_D2.0mm_Drill1.4mm": "Terminal_Blade_2x1_P5.00mm",
    "Transformer_EF25_2x5_P5.08mm_8pin": "Transformer_EF25_2x5_P5.08mm_8pin",
}


def fork(name):
    src = open(os.path.join(LIB51, name + ".kicad_mod")).read()
    return derive(src, name, "5.2 copy with a 3D model (tube_psu_next_parts; pads = lib/tube_psu.pretty)",
                  model=model_block(FORKS[name]))


# --- J2 socket (owner 2026-11-24, findings 04 F1) -----------------------------------------------------
# XKB X1321FV-2x25-C43D24 (LCSC C2881768): female 2x25 1.27 mm straight THT socket; drawing X-X1321FV-2x25-C43D24
# rev A0: P.C.B layout hole 0.70 mm, pin 0.45 mm, insulator 4.3 mm, tail 2.4 mm, body 3.0 x 32.15 mm. Pad positions
# stay those of the 5.1 / Proteus footprint (pad 2 at +1.27 mm, the geometry the 5.1 board mated with); drill
# 0.5 -> 0.70 mm, pad 0.812 -> 1.02 mm (annular ring 0.16 mm; with 1.0 mm the fab check of jlc_fab.py measured
# 0.149 mm, below JLC's 0.15 mm), inner-layer pads only where connected.
SOCKET_DRILL, SOCKET_PAD = 0.7, 1.02


def j2_socket():
    src = open(os.path.join(LIB51, "PinHeader_2x25_P1.27mm_Vertical_Proteus.kicad_mod")).read()
    src = src.replace("(size 0.812 0.812)", f"(size {f(SOCKET_PAD)} {f(SOCKET_PAD)})")
    src = src.replace("(drill 0.5)", f"(drill {f(SOCKET_DRILL)})")
    src = src.replace("(remove_unused_layers no)", "(remove_unused_layers yes)\n\t\t(keep_end_layers yes)")
    model = ('\t(model "${KICAD10_3DMODEL_DIR}/Connector_PinSocket_1.27mm.3dshapes/PinSocket_2x25_P1.27mm_Vertical.step"\n'
             '\t\t(offset\n\t\t\t(xyz 1.27 0 0)\n\t\t)\n\t\t(scale\n\t\t\t(xyz 1 1 1)\n\t\t)\n'
             '\t\t(rotate\n\t\t\t(xyz 0 0 0)\n\t\t)\n\t)\n')
    return derive(src, "PinSocket_2x25_P1.27mm_Vertical_XKB_X1321FV",
                  "5.2 J2 female socket XKB X1321FV-2x25-C43D24 (C2881768): drill 0.70 mm per the drawing, pad 1.02 mm, "
                  "pad positions of the 5.1 footprint, inner pads only where connected (tube_psu_next_parts)",
                  model=model)


# --- SiC boost diodes SICD1 / SICD2 (design review 2026-11-24, finding 13 F1; stage 16a) ---------------------
# Wolfspeed C3D02060A (data sheet Rev. 10, Oct 2024, p 6 "Package Dimensions & Pin-Out", TO-220-2): pin 1 =
# CATHODE, pin 2 = ANODE, 3 (case / tab) = CATHODE; pin 1 is the left lead seen from the front (moulded side,
# leads down). The 5.1 footprint tube_psu:TO-220-2_Vertical_AK named the pin-1 pad "A": a diode fitted as its
# outline shows (tab on local -y) puts its cathode into pad A. This copy names the pin-1 pad (rectangular, local
# (0, 0)) "K" and the pin-2 pad (round, (5.08, 0)) "A"; drills, pad sizes, graphics and the KiCad TO-220-2 model
# are those of the 5.1 footprint, so outline, pad names and the real part agree.
def to220_2_ka():
    src = open(os.path.join(LIB51, "TO-220-2_Vertical_AK.kicad_mod")).read()
    for a, b in (('(pad "A" thru_hole rect', '(pad "@K" thru_hole rect'),
                 ('(pad "K" thru_hole circle', '(pad "A" thru_hole circle'), ('(pad "@K"', '(pad "K"')):
        if src.count(a) != 1:
            sys.exit(f"gen_next_footprints_parts: TO-220-2_Vertical_AK: '{a}' not found once")
        src = src.replace(a, b)
    src = src.replace("pads A (pin 1) / K (pin 2, tab), Proteus pad positions",
                      "pads K (pin 1, cathode = tab) / A (pin 2, anode) as Wolfspeed C3D02060A, Proteus pad positions")
    return derive(src, "TO-220-2_Vertical_KA",
                  "5.2 copy with the pad names of the C3D02060A pin-out: pin 1 K (rect), pin 2 A (tube_psu_next_parts)")


FOOTPRINTS = {"PG-DSO-12_3.9x9.9mm_P1.27mm": pg_dso12,      # name -> function returning the .kicad_mod text
              "PinSocket_2x25_P1.27mm_Vertical_XKB_X1321FV": j2_socket,
              "TO-220-2_Vertical_KA": to220_2_ka}
for _c in SOIC_SLOTS:
    FOOTPRINTS[f"SOIC-16W_7.5x10.3mm_P1.27mm_Slot{_c}"] = (lambda c=_c: soic16w_slot(c))
for _r in SOIC_T:
    FOOTPRINTS[f"SOIC-16W_7.5x10.3mm_P1.27mm_Slot{SOIC_T[_r]['creep']}_T_{_r}"] = (lambda r=_r: soic16w_slot_t(r))
for _n in CP_VARIANTS:
    FOOTPRINTS[_n] = (lambda n=_n: cp_variant(n))
for _n in FORKS:
    FOOTPRINTS[_n] = (lambda n=_n: fork(n))


def main(argv):
    os.makedirs(OUT, exist_ok=True)
    bad = []
    for name, fn in FOOTPRINTS.items():
        path = os.path.join(OUT, name + ".kicad_mod")
        text_ = fn()
        if "--check" in argv:
            if not os.path.exists(path) or open(path).read() != text_:
                bad.append(name)
            continue
        with open(path, "w") as fh:
            fh.write(text_)
    if "--check" in argv:
        print("gen_next_footprints_parts: " + ("out of date: " + ", ".join(bad) if bad else
                                                f"lib/tube_psu_next_parts.pretty up to date ({len(FOOTPRINTS)})"))
        return 1 if bad else 0
    print(f"gen_next_footprints_parts: wrote {len(FOOTPRINTS)} footprints to lib/tube_psu_next_parts.pretty")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
