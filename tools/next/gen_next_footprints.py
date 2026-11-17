#!/usr/bin/env python3
"""Footprints for the next board revision (NEXT_REVISION.md items 1.2 and 2.2), stdlib only.

Writes lib/tube_psu_next.pretty/ - kept apart from lib/tube_psu.pretty, which tools/gen_footprints.py
generates for the 1:1 migration of tube_power_5_1 (tools/check_all.sh checks that library).

  Transformer_EEL19_V_4+6_FlyLeads   new TR1, aux flyback (simulation/flyback/EEL19_DESIGN.md 6a)
  Transformer_EC42x15_2Slot_2x8_P5mm new TR3, DAB (simulation/dab/DAB_TRANSFORMER.md 5)

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


def pad(num, x, y, size, drill, shape="circle"):
    return (f"\t(pad \"{num}\" thru_hole {shape}\n\t\t(at {f(x)} {f(y)})\n\t\t(size {f(size)} {f(size)})\n"
            f"\t\t(drill {f(drill)})\n\t\t(layers \"*.Cu\" \"*.Mask\")\n\t)\n")


def footprint(name, descr, tags, body, ref_y, val_y):
    return (f"(footprint \"{name}\"\n\t(version 20260206)\n\t(generator \"tube_psu_next\")\n"
            f"\t(layer \"F.Cu\")\n\t(descr \"{descr}\")\n\t(tags \"{tags}\")\n"
            + text("Reference", "REF**", 0, ref_y, "F.SilkS") + text("Value", name, 0, val_y, "F.Fab")
            + "\t(attr through_hole)\n" + body + text("user", "${REFERENCE}", 0, 0, "F.Fab") + ")\n")


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
    flx, fly, flp = (-2.2, -7.0), 14.0, 2.2
    body += poly([(-bx - c, -by - c), (bx + c, -by - c), (bx + c, by + c),
                  (max(flx) + flp / 2 + 0.25, by + c), (max(flx) + flp / 2 + 0.25, fly + flp / 2 + 0.25),
                  (min(flx) - flp / 2 - 0.25, fly + flp / 2 + 0.25), (min(flx) - flp / 2 - 0.25, by + c),
                  (-bx - c, by + c)], "F.CrtYd", 0.05)
    # primary row (x = -6.25): 1, 2, 3 with pads, 4 clipped
    for i, y in enumerate((-5.25, -1.75, 1.75)):
        body += pad(i + 1, -xr, y, 1.8, 1.0, "rect" if i == 0 else "circle")
    body += clipped(-xr, 5.25, "4 clip (crossover)")
    # isolated row (x = +6.25), bottom to top: 5..10, pin 6 clipped
    ys = [6.75 - 2.7 * k for k in range(6)]
    for k, y in enumerate(ys):
        n = 5 + k
        body += clipped(xr, y, "6 clip") if n == 6 else pad(n, xr, y, 1.6, 0.9)
    # fly-lead holes (sleeved leads, 0.4-0.5 mm tinned ends)
    body += pad(11, flx[0], fly, flp, 1.2)
    body += pad(12, flx[1], fly, flp, 1.2)
    body += text("user", "FL_DC", flx[0], fly + 2.0, "F.Fab", 0.6) + text("user", "FL_C", flx[1], fly + 2.0, "F.Fab", 0.6)
    descr = ("EEL19 vertical bobbin 4+6 (pitch 3.5 / 2.7 mm, rows 12.5 mm), aux flyback TR1 for the next "
             "revision: pads 1-3 primary-side aux, pin 4 crossover (clipped, no pad), pads 5, 7-10 isolated, "
             "pin 6 spare (clipped), pads 11/12 fly leads FL_DC/FL_C; body 15.8 x 22.5 mm, height about 29.2 mm "
             "(tube_psu_next, simulation/flyback/EEL19_DESIGN.md 6a; confirm dims with calipers)")
    return footprint("Transformer_EEL19_V_4+6_FlyLeads", descr, "transformer EEL19 flyback fly-lead", body,
                     -by - 1.5, fly + 3.5)


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
    descr = ("EC42/15 PC40 two-chamber bobbin 2 x 8 pins, pitch 5.0 mm, rows 40 mm, DAB transformer TR3 for "
             "the next revision: pads 1+2 / 7+8 primary (chamber 1, 10.4 mm), 9+10 / 15+16 secondary "
             "(chamber 2, 12.4 mm), pins 3-6 / 11-14 clipped; body 46 x 42 mm, seated height 31.5 mm "
             "(tube_psu_next, simulation/dab/DAB_TRANSFORMER.md 5; confirm dims with calipers)")
    return footprint("Transformer_EC42x15_2Slot_2x8_P5mm", descr, "transformer EC42 DAB two-chamber", body,
                     -by - 1.5, by + 1.5)


def main():
    files = {"Transformer_EEL19_V_4+6_FlyLeads.kicad_mod": eel19(),
             "Transformer_EC42x15_2Slot_2x8_P5mm.kicad_mod": ec42()}
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
