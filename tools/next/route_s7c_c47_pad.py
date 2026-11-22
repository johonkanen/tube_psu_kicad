#!/usr/bin/env python3
"""Stage 7c (run once with tools/p2k/bin/kipy): the F.Cu DC+ bar of stage 7b overlapped C47 pad 1 by only
0.24 mm. One F.Cu DC+ segment 1.55 mm wide from the bar (24.1, -72.5) to (24.1, -74.3) runs it well into
the pad (pad 1: x 20.18...25.58, y -75.335...-73.36). Not re-runnable."""
import os, sys
import pcbnew
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PCB = os.path.join(ROOT, "kicad_next", "tube_psu_5_2.kicad_pcb")
b = pcbnew.LoadBoard(PCB)
mm = pcbnew.FromMM
for t in b.GetTracks():
    if t.GetNetname() == "DC+" and t.GetClass() == "PCB_TRACK" and t.GetStart() == pcbnew.VECTOR2I(mm(24.1), mm(-72.5)):
        sys.exit("route_s7c_c47_pad: already applied")
t = pcbnew.PCB_TRACK(b)
t.SetStart(pcbnew.VECTOR2I(mm(24.1), mm(-72.5)))
t.SetEnd(pcbnew.VECTOR2I(mm(24.1), mm(-74.3)))
t.SetWidth(mm(1.55))
t.SetLayer(pcbnew.F_Cu)
t.SetNet(b.FindNet("DC+"))
b.Add(t)
b.Save(PCB)
print("route_s7c_c47_pad: added F.Cu DC+ 1.55 mm (24.1, -72.5)-(24.1, -74.3)")
