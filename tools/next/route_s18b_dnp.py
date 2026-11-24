#!/usr/bin/env python3
"""Stage 18b (2026-11-24, findings 14 F10): C10 / C26 "Do not populate" on the board (run with tools/p2k/bin/kipy).

    tools/p2k/bin/kipy tools/next/route_s18b_dnp.py [--check]

One-shot record, like the route_s*.py scripts: never re-run it on a later board (it is idempotent, but the
schematic is the source of the attributes from here on).

The sheet generator (tools/next/sheets/_common.py, `_mark_dnp`) now gives every part whose status in
lib/jlc_parts_next.csv is `dnp` the symbol attributes dnp yes / in_bom no / in_pos_files no. KiCad's schematic
parity check compares "Do not populate" and "Exclude from bill of materials" of symbol and footprint, so the two
board footprints get the same attributes: DNP, exclude from BOM, exclude from position files. Attributes only:
no position, pad, net, track, via or zone is touched (update_board_parts.py does not carry footprint attributes).
The project file is kept as it was (pcbnew's Save re-sorts it). Stops on KiCad's lock file.
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PROJ = os.path.join(ROOT, "kicad_next")
BOARD = os.path.join(PROJ, "tube_psu_5_2.kicad_pcb")
PRO = os.path.join(PROJ, "tube_psu_5_2.kicad_pro")
LOCK = os.path.join(PROJ, "~tube_psu_5_2.kicad_pcb.lck")
REFS = ("C10", "C26")


def main(argv):
    check = "--check" in argv
    if os.path.exists(LOCK):
        sys.exit("route_s18b_dnp: the board is open in KiCad (lock file) - close it first")
    b = pcbnew.LoadBoard(BOARD)
    changes = []
    for ref in REFS:
        fp = b.FindFootprintByReference(ref)
        if fp is None:
            sys.exit(f"route_s18b_dnp: {ref} not on the board")
        for name, get, put in (("DNP", fp.IsDNP, fp.SetDNP),
                               ("exclude from BOM", fp.IsExcludedFromBOM, fp.SetExcludedFromBOM),
                               ("exclude from position files", fp.IsExcludedFromPosFiles, fp.SetExcludedFromPosFiles)):
            if not get():
                changes.append(f"{ref}: {name} False -> True")
                put(True)
    for c in changes:
        print("route_s18b_dnp: " + c)
    if check:
        print(f"route_s18b_dnp: {len(changes)} differences" if changes else "route_s18b_dnp: up to date")
        return 1 if changes else 0
    if not changes:
        print("route_s18b_dnp: nothing to do")
        return 0
    with open(PRO, "rb") as f:
        keep = f.read()
    b.Save(BOARD)
    with open(PRO, "wb") as f:
        f.write(keep)
    print(f"route_s18b_dnp: wrote {os.path.relpath(BOARD, ROOT)} ({len(changes)} changes)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
