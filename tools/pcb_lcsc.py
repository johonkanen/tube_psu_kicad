#!/usr/bin/env python3
"""Board step 6 of tools/make_pcb.sh: copy the schematic's LCSC field onto the footprints.

The sheet scripts give every symbol a hidden "LCSC" property from lib/jlc_parts.csv
(tools/sheets/_common.py); p2k.build_pcb copies only Value/Datasheet/Description, so without
this step the DRC schematic parity check reports "Missing symbol field 'LCSC'". The field is
added hidden on the footprint's Fab layer at the footprint anchor. Run with tools/p2k/bin/kipy
(the board file comes from P2K_PCB like the p2k steps, default kicad/tube_psu.kicad_pcb).
"""
import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "p2k"))
import pcbnew  # noqa: E402
from p2k import pcb  # noqa: E402


def main():
    pcbnew.KIID.SeedGenerator(3006)  # reproducible UUIDs (distinct seed per script)
    with open(os.path.join(ROOT, "lib", "jlc_parts.csv"), newline="", encoding="utf-8") as f:
        lcsc = {r["refdes"]: r["lcsc"] for r in csv.DictReader(l for l in f if not l.startswith("#"))}
    board = pcbnew.LoadBoard(pcb.board_file())
    n = 0
    for fp in sorted(board.Footprints(), key=lambda m: m.GetReference()):
        ref = fp.GetReference()
        if ref not in lcsc:
            continue
        fp.SetField("LCSC", lcsc[ref])
        fld = fp.GetField("LCSC")
        fld.SetVisible(False)
        fld.SetLayer(pcbnew.B_Fab if fp.IsFlipped() else pcbnew.F_Fab)
        fld.SetPosition(fp.GetPosition())
        if fp.IsFlipped():
            fld.SetMirrored(True)
        n += 1
    pcbnew.SaveBoard(pcb.board_file(), board)
    missing = sorted(set(lcsc) - {fp.GetReference() for fp in board.Footprints()})
    print(f"pcb_lcsc: LCSC field on {n} footprints" + (f", not on the board: {' '.join(missing)}" if missing else ""))
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
