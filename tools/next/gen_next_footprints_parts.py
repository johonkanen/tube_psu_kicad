#!/usr/bin/env python3
"""Footprints of new 5.2 parts that the KiCad standard library does not have, stdlib only.

Writes lib/tube_psu_next_parts.pretty/ (library nickname tube_psu_next_parts in kicad_next/fp-lib-table).
Kept apart from tools/next/gen_next_footprints.py (transformer footprints, lib/tube_psu_next.pretty).

Currently empty: the only entry (SOIC-10_Batwing_iW1819 for the iW1819-00) was removed when PWM2 became the
ICE5AR4780BZS (NR 1.5), whose PG-DIP-7 is the KiCad standard Package_DIP:DIP-8-N6_W7.62mm. The helpers stay
for the next part that needs a footprint (add a function and a FOOTPRINTS entry).

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


FOOTPRINTS = {}      # name -> function returning the .kicad_mod text


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
