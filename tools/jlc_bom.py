#!/usr/bin/env python3
"""JLCPCB assembly files from the board and lib/jlc_parts.csv.

    python3 tools/jlc_bom.py            writes build/jlc/tube_psu_bom.csv and build/jlc/tube_psu_cpl.csv

BOM (JLC format): Comment, Designator, Footprint, LCSC Part # - one line per (value, footprint,
LCSC) group; Comment is the schematic value, or the MPN where the value is stale (status changed). Parts without an LCSC number (status consigned / missing / dnp in lib/jlc_parts.csv)
are left out of both files and listed on stdout; consigned parts go to JLC separately or are
fitted by hand.

CPL (JLC format): Designator, Mid X, Mid Y, Layer, Rotation. Positions are the footprint
anchors of kicad/tube_psu.kicad_pcb in mm, X = KiCad x, Y = -KiCad y (the Gerber frame: the
board has no aux origin, the Gerbers use absolute coordinates with Y up). Layer is Top/Bottom.
Rotation is the KiCad orientation (counter-clockwise, as shown in pcbnew, also for bottom-side
parts) plus the correction from ROTATION_FIX.

ROTATION_FIX: JLC's part models do not always have pin 1 where the KiCad footprint has it, so
some packages come out rotated in JLC's placement preview. Typical offenders (add them here
after checking the preview, do not guess):
  - SOT-23 / SOT-23-5 / SOT-23-6 (often 180 deg); note tube_psu:SOT-23_Proteus uses Proteus pad
    numbering, so its pin 1 is not JEDEC pin 1
  - SOIC / TSSOP / MSOP (often 270 or 90 deg)
  - diodes SOD-323 / SMA (180 deg if the cathode band is on the other side)
  - SMD electrolytics (CP_Elec, 180 deg)
  - DFN / LFPAK (90 deg)
Keys are footprint names (with or without the library prefix) or fnmatch patterns; values are
degrees added for top-side parts and subtracted for bottom-side parts (mirrored view).
The table is empty: no correction has been verified against JLC's preview yet.
"""
import csv
import fnmatch
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "p2k"))
from p2k.sexpr import load  # noqa: E402

PCB = os.path.join(ROOT, "kicad", "tube_psu.kicad_pcb")
PARTS = os.path.join(ROOT, "lib", "jlc_parts.csv")
OUT = os.path.join(ROOT, "build", "jlc")

ROTATION_FIX = {
    # "tube_psu:SOT-23_Proteus": 180,
    # "*SOIC-16*": 270,
}


def rotation_fix(footprint):
    name = footprint.split(":", 1)[-1]
    for pat, deg in ROTATION_FIX.items():
        if fnmatch.fnmatch(footprint, pat) or fnmatch.fnmatch(name, pat):
            return deg
    return 0


def child(node, head):
    return next((n for n in node[1:] if isinstance(n, list) and n and n[0] == head), None)


def footprints(path=PCB):
    """{ref: (footprint, x, y, rot, layer, attrs)} of the board's footprints."""
    out = {}
    for fp in load(path)[1:]:
        if not (isinstance(fp, list) and fp and fp[0] == "footprint"):
            continue
        props = {p[1]: p[2] for p in fp[1:] if isinstance(p, list) and p and p[0] == "property"}
        at = child(fp, "at")
        attr = child(fp, "attr")
        x, y = float(at[1]), float(at[2])
        rot = float(at[3]) if len(at) > 3 else 0.0
        out[props.get("Reference", "")] = (str(fp[1]), x, y, rot, str(child(fp, "layer")[1]),
                                          set(map(str, attr[1:])) if attr else set())
    return out


def load_parts(path=PARTS):
    with open(path, newline="", encoding="utf-8") as f:
        return {r["refdes"]: r for r in csv.DictReader(l for l in f if not l.startswith("#"))}


def fmt(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


def main():
    fps = footprints()
    parts = load_parts()
    os.makedirs(OUT, exist_ok=True)
    groups = defaultdict(list)
    cpl, skipped, unknown = [], [], []
    for ref in sorted(fps):
        fpname, x, y, rot, layer, attrs = fps[ref]
        if "exclude_from_bom" in attrs or "board_only" in attrs:
            continue
        p = parts.get(ref)
        if p is None:
            unknown.append(ref)
            continue
        if not p["lcsc"]:
            skipped.append((ref, p["status"]))
            continue
        comment = p["mpn"] if p["status"] == "changed" else p["value"]  # schematic value stale
        groups[(comment, fpname.split(":", 1)[-1], p["lcsc"])].append(ref)
        bottom = layer == "B.Cu"
        r = (rot + (-1 if bottom else 1) * rotation_fix(fpname)) % 360
        cpl.append((ref, fmt(x), fmt(-y), "Bottom" if bottom else "Top", fmt(r)))
    key = lambda r: (r.rstrip("0123456789"), int("0" + r[len(r.rstrip("0123456789")):]))  # noqa: E731
    with open(os.path.join(OUT, "tube_psu_bom.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (val, fpn, lcsc), refs in sorted(groups.items(), key=lambda kv: key(sorted(kv[1], key=key)[0])):
            w.writerow([val, ",".join(sorted(refs, key=key)), fpn, lcsc])
    with open(os.path.join(OUT, "tube_psu_cpl.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        w.writerows(sorted(cpl, key=lambda r: key(r[0])))
    missing = [r for r in parts if r not in fps]
    print(f"jlc_bom: {len(cpl)} placements in {len(groups)} BOM lines -> {os.path.relpath(OUT, ROOT)}/")
    by = defaultdict(list)
    for ref, st in skipped:
        by[st].append(ref)
    for st, refs in sorted(by.items()):
        print(f"  not placed by JLC ({st}, {len(refs)}): {' '.join(sorted(refs, key=key))}")
    if unknown:
        print(f"  ERROR: board parts missing in lib/jlc_parts.csv: {' '.join(unknown)}")
    if missing:
        print(f"  ERROR: lib/jlc_parts.csv parts not on the board: {' '.join(missing)}")
    return 1 if unknown or missing else 0


if __name__ == "__main__":
    sys.exit(main())
