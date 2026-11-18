#!/usr/bin/env python3
"""Footprints of new 5.2 parts that the KiCad standard library does not have, stdlib only.

Writes lib/tube_psu_next_parts.pretty/ (library nickname tube_psu_next_parts in kicad_next/fp-lib-table).
Kept apart from tools/next/gen_next_footprints.py (transformer footprints, lib/tube_psu_next.pretty).

  SOIC-10_Batwing_iW1819   PWM2 iW1819-00 (Renesas 10-lead SOIC batwing): pins 1-4 / 7-10 at 1.27 mm,
                           pins 5 / 6 = wide collector leads 3.175 mm from pins 4 / 7, rows 5.6 mm
                           apart (pad centres), body 8.6 x 3.9 mm. Pad geometry taken from the LCSC /
                           EasyEDA land pattern of C17225733 (SOIC-10_L8.6-W3.9-P1.27-LS6.0-BL); the
                           Renesas datasheet (Rev. 1.5) has no package drawing - confirm against the
                           Renesas package outline before the layout (phase 3). The datasheet's creepage
                           note: 1.47 mm minimum between the HV (collector) and LV pins; slot if more
                           is needed (10.16.1).

Usage: python3 tools/next/gen_next_footprints_parts.py [--check]
"""
import os
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


def iw1819():
    xr = 5.6 / 2                                    # pad-centre row offset
    ys = {1: -3.4925, 2: -2.2225, 3: -0.9525, 4: 0.3175, 5: 3.4925}
    body = ""
    for n, y in ys.items():
        w, h = (1.30, 1.87) if n == 5 else (1.30, 0.59)
        body += smd(n, -xr, y, w, h)                # left row 1..5 downwards
        body += smd(11 - n, xr, y, w, h)            # right row 10..6 downwards (10 opposite 1)
    bx, by = 3.9 / 2, 8.6 / 2
    body += rect(-bx, -by, bx, by, "F.Fab", 0.1)
    body += line(-bx + 0.8, -by, -bx, -by + 0.8, "F.Fab", 0.1)
    body += line(-bx, -by - 0.12, bx, -by - 0.12, "F.SilkS", 0.12)
    body += line(-bx, by + 0.12, bx, by + 0.12, "F.SilkS", 0.12)
    body += line(-xr - 0.65, -by - 0.12, -bx, -by - 0.12, "F.SilkS", 0.12)   # pin-1 mark
    body += rect(-xr - 0.95, -by - 0.35, xr + 0.95, by + 0.35, "F.CrtYd", 0.05)
    return footprint("SOIC-10_Batwing_iW1819",
                     "Renesas iW1819 10-lead SOIC batwing (pins 5/6 wide collector leads), 1.27 mm pitch, rows "
                     "5.6 mm; land pattern after LCSC C17225733, to be confirmed against the Renesas outline",
                     "SOIC-10 batwing iW1819", body, -by - 1.4, by + 1.4)


FOOTPRINTS = {"SOIC-10_Batwing_iW1819": iw1819}


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
