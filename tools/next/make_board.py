#!/usr/bin/env python3
"""Board skeleton of tube_power 5.2: kicad_next/tube_psu_5_2.kicad_pcb (run with tools/p2k/bin/kipy).

    tools/p2k/bin/kipy tools/next/make_board.py           write the skeleton (refuses to overwrite)
    tools/p2k/bin/kipy tools/next/make_board.py --force   overwrite an existing board (loses edits!)
    tools/p2k/bin/kipy tools/next/make_board.py --check   check the committed board: 6 copper layers with
                                                          the names / types below, the JLC stackup, the
                                                          5.1 outline and mounting holes H1-H8 unchanged
                                                          (added Edge.Cuts shapes must be internal slots)

The skeleton holds only what is fixed (NEXT_REVISION_PLAN.md D3): the 5.1 board outline (Edge.Cuts) and
the eight mounting holes copied from kicad/tube_psu.kicad_pcb (locked), the 6-layer copper set and the
JLC06161H-7628D stackup (D5: 1 oz outer, 0.5 oz inner, 1.6 mm). Footprints are placed in phase 5; after
that the board is edited in KiCad and only --check is run (it does not compare bytes).
Design rules / net classes live in kicad_next/tube_psu_5_2.kicad_pro and tube_psu_5_2.kicad_dru
(tools/next/setup_project.py).
"""
import os
import re
import sys

import pcbnew

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "kicad", "tube_psu.kicad_pcb")
OUT = os.path.join(ROOT, "kicad_next", "tube_psu_5_2.kicad_pcb")
HOLES = [f"H{i}" for i in range(1, 9)]

# (layer id, user name, type) - NEXT_REVISION_PLAN.md phase 1 task 2
COPPER = [
    (pcbnew.F_Cu, "F.Cu", pcbnew.LT_SIGNAL),     # L1 parts + power copper, signals
    (pcbnew.In1_Cu, "In1.GND", pcbnew.LT_POWER),  # L2 GND planes, one per domain
    (pcbnew.In2_Cu, "In2.Signal_HV", pcbnew.LT_SIGNAL),  # L3 signals / HV routing
    (pcbnew.In3_Cu, "In3.Power", pcbnew.LT_MIXED),       # L4 power pours (DC+, 15V, +3V3, ...)
    (pcbnew.In4_Cu, "In4.GND", pcbnew.LT_POWER),  # L5 GND planes, one per domain
    (pcbnew.B_Cu, "B.Cu", pcbnew.LT_SIGNAL),     # L6 bottom parts + signals
]

# JLC06161H-7628D (JLC order form "Layer Stackup", 6 layers, 1 oz outer / 0.5 oz inner, read by the user
# 2026-11-23; was JLC06161H-3313 until then): two plies of 7628 (0.218 + 0.2104 mm, one KiCad dielectric of
# 0.4284 mm) between the outer layers and the GND planes, for the 400 V DC+ copper on F.Cu / B.Cu. Special
# stackup: no economic PCB assembly. Dk: 7628 4.4 (JLC calculator guide),
# core (Nan Ya NP-155F) 4.6; solder mask 0.6 mil (0.015 mm) over copper, Dk 3.8 (JLC calculator guide).
# Loss tangent 0.02 is a generic FR-4 value (not published per stackup by JLC).
STACKUP = """\t\t(stackup
\t\t\t(layer "F.SilkS" (type "Top Silk Screen"))
\t\t\t(layer "F.Paste" (type "Top Solder Paste"))
\t\t\t(layer "F.Mask" (type "Top Solder Mask") (thickness 0.015) (material "LPI") (epsilon_r 3.8) (loss_tangent 0))
\t\t\t(layer "F.Cu" (type "copper") (thickness 0.035))
\t\t\t(layer "dielectric 1" (type "prepreg") (thickness 0.4284) (material "7628 x2 (0.218 + 0.2104)") (epsilon_r 4.4) (loss_tangent 0.02))
\t\t\t(layer "In1.Cu" (type "copper") (thickness 0.0152))
\t\t\t(layer "dielectric 2" (type "core") (thickness 0.2) (material "NP-155F core") (epsilon_r 4.6) (loss_tangent 0.02))
\t\t\t(layer "In2.Cu" (type "copper") (thickness 0.0152))
\t\t\t(layer "dielectric 3" (type "prepreg") (thickness 0.2028) (material "7628") (epsilon_r 4.4) (loss_tangent 0.02))
\t\t\t(layer "In3.Cu" (type "copper") (thickness 0.0152))
\t\t\t(layer "dielectric 4" (type "core") (thickness 0.2) (material "NP-155F core") (epsilon_r 4.6) (loss_tangent 0.02))
\t\t\t(layer "In4.Cu" (type "copper") (thickness 0.0152))
\t\t\t(layer "dielectric 5" (type "prepreg") (thickness 0.4284) (material "7628 x2 (0.2104 + 0.218)") (epsilon_r 4.4) (loss_tangent 0.02))
\t\t\t(layer "B.Cu" (type "copper") (thickness 0.035))
\t\t\t(layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.015) (material "LPI") (epsilon_r 3.8) (loss_tangent 0))
\t\t\t(layer "B.Paste" (type "Bottom Solder Paste"))
\t\t\t(layer "B.SilkS" (type "Bottom Silk Screen"))
\t\t\t(copper_finish "ENIG")
\t\t\t(dielectric_constraints no)
\t\t)
"""
# copper / dielectric thickness per stackup position, for --check (mm)
EXPECT = [("F.Cu", 0.035), ("dielectric 1", 0.4284), ("In1.Cu", 0.0152), ("dielectric 2", 0.2),
          ("In2.Cu", 0.0152), ("dielectric 3", 0.2028), ("In3.Cu", 0.0152), ("dielectric 4", 0.2),
          ("In4.Cu", 0.0152), ("dielectric 5", 0.4284), ("B.Cu", 0.035)]


def mm(v):
    return round(v / 1e6, 4)


def outline(board):
    return sorted((s.GetShapeStr(), mm(s.GetStart().x), mm(s.GetStart().y), mm(s.GetEnd().x), mm(s.GetEnd().y))
                  for s in board.GetDrawings() if s.GetLayer() == pcbnew.Edge_Cuts)


def holes(board):
    out = {}
    for fp in board.GetFootprints():
        if fp.GetReference() in HOLES:
            out[fp.GetReference()] = (fp.GetFPIDAsString(), mm(fp.GetPosition().x), mm(fp.GetPosition().y),
                                      sorted((mm(p.GetSizeX()), mm(p.GetDrillSizeX()), p.GetAttribute())
                                             for p in fp.Pads()))
    return out


def write(out=OUT, quiet=False):
    """the skeleton board; check_rules.py / check_footprints.py also write it as their empty test board"""
    src = pcbnew.LoadBoard(SRC)
    b = pcbnew.BOARD()
    b.SetCopperLayerCount(6)
    for layer, name, ltype in COPPER:
        b.SetLayerName(layer, name)
        b.SetLayerType(layer, ltype)
    for s in src.GetDrawings():
        if s.GetLayer() == pcbnew.Edge_Cuts:
            c = s.Duplicate()
            c.SetLocked(True)
            b.Add(c)
    for fp in src.GetFootprints():
        if fp.GetReference() in HOLES:
            c = pcbnew.FOOTPRINT(fp)
            c.SetLocked(True)
            b.Add(c)
    b.GetDesignSettings().SetBoardThickness(pcbnew.FromMM(1.6))
    pcbnew.SaveBoard(out, b)
    # the stackup goes in as text (pcbnew's Python stackup API is incomplete); pcbnew re-reads and
    # re-saves it, so the file is in pcbnew's own format
    with open(out) as f:
        s = f.read()
    s = re.sub(r"\t\t\(stackup\n.*?\n\t\t\)\n", "", s, flags=re.S)
    s = s.replace("\t(setup\n", "\t(setup\n" + STACKUP, 1)
    with open(out, "w") as f:
        f.write(s)
    b = pcbnew.LoadBoard(out)
    pcbnew.SaveBoard(out, b)
    if not quiet:
        print(f"make_board: wrote {os.path.relpath(out, ROOT)}")


def check():
    errs = []
    b = pcbnew.LoadBoard(OUT)
    src = pcbnew.LoadBoard(SRC)
    if b.GetCopperLayerCount() != 6:
        errs.append(f"{b.GetCopperLayerCount()} copper layers, expected 6")
    for layer, name, ltype in COPPER:
        if b.GetLayerName(layer) != name or b.GetLayerType(layer) != ltype:
            errs.append(f"layer {pcbnew.LayerName(layer)}: name {b.GetLayerName(layer)} type {b.GetLayerType(layer)}")
    extra = [s for s in outline(b) if s not in set(outline(src))]
    if not set(outline(src)) <= set(outline(b)):
        errs.append("Edge.Cuts: the 5.1 outline is not complete")
    bb = src.GetBoardEdgesBoundingBox()
    for s in b.GetDrawings():     # added Edge.Cuts shapes = internal barrier slots: strictly inside the 5.1 outline
        if s.GetLayer() == pcbnew.Edge_Cuts and (s.GetShapeStr(), mm(s.GetStart().x), mm(s.GetStart().y),
                                                 mm(s.GetEnd().x), mm(s.GetEnd().y)) in extra:
            sb = s.GetBoundingBox()
            if not (bb.GetLeft() < sb.GetLeft() and sb.GetRight() < bb.GetRight()
                    and bb.GetTop() < sb.GetTop() and sb.GetBottom() < bb.GetBottom()):
                errs.append(f"Edge.Cuts {s.GetShapeStr()} at ({mm(s.GetStart().x)}, {mm(s.GetStart().y)}) "
                            "is not inside the 5.1 outline")
    if holes(b) != holes(src) or len(holes(b)) != 8:
        errs.append("mounting holes H1-H8 differ from 5.1")
    with open(OUT) as f:
        text = f.read()
    got = [(m.group(1), float(m.group(2))) for m in
           re.finditer(r'\(layer "([^"]+)"\s*\(type "(?:copper|prepreg|core)"\)\s*(?:\(color "[^"]*"\)\s*)?\(thickness ([\d.]+)\)', text)]
    if got != EXPECT:
        errs.append(f"stackup differs from JLC06161H-7628D: {got}")
    thick = mm(b.GetDesignSettings().GetBoardThickness())
    for e in errs:
        print("make_board: " + e)
    print(f"make_board: board skeleton {'OK' if not errs else 'FAILED'} (6 layers, stackup {thick} mm, "
          f"5.1 outline {len(outline(src))} segments + {len(extra)} internal slot shapes, holes {len(holes(b))})")
    return 1 if errs else 0


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(check())
    if os.path.exists(OUT) and "--force" not in sys.argv:
        sys.exit(f"make_board: {os.path.relpath(OUT, ROOT)} exists (use --force to overwrite)")
    write()
    sys.exit(check())
