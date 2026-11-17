#!/usr/bin/env python3
"""Functional test of the 5.2 design rules (run with tools/p2k/bin/kipy).

kicad-cli does not report syntax errors in a .kicad_dru (a broken rule is silently dropped), so this
test proves that the rules parse and act: it copies kicad_next/tube_psu_5_2.{kicad_pcb,kicad_pro,
kicad_dru} into a temporary directory, adds pairs of test tracks on nets of the 5.2 schematic (their
net classes come from the project's netclass patterns), runs the KiCad DRC and compares the violation
types found at each test spot with the expected ones.

    tools/p2k/bin/kipy tools/next/check_rules.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

import pcbnew

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "kicad_next")
CLI = os.path.join(ROOT, "tools", "p2k", "bin", "kicad-cli")
L = {"F": pcbnew.F_Cu, "B": pcbnew.B_Cu, "In1": pcbnew.In1_Cu, "In2": pcbnew.In2_Cu, "In3": pcbnew.In3_Cu}

# (net A, net B, layer, edge-to-edge gap mm, expected violation types at this spot)
CASES = [
    ("DC+", "420V", "F", 6.0, {"creepage"}),                      # PRI-SEC creepage 11.1 > 6 > clearance 4
    ("DC+", "420V", "F", 11.5, set()),
    ("GND", "ISO_GND", "In1", 6.0, {"clearance"}),                 # PRI-SEC inner 11.1
    ("GND", "ISO_GND", "In1", 11.5, set()),
    ("GND", "ISO_GND", "B", 3.5, {"clearance", "creepage"}),        # PRI-SEC clearance 4.0
    ("+3V3", "HT_GND", "F", 7.0, {"creepage"}),                    # PRI-HEATER creepage 8.0
    ("+3V3", "HT_GND", "In3", 7.0, {"clearance"}),                 # PRI-HEATER inner 8.0
    ("+3V3", "HT_GND", "F", 8.5, set()),
    ("420V", "HT_GND", "F", 3.0, {"creepage"}),                    # SEC-HEATER basic creepage 4.2
    ("DC+", "GND", "F", 1.0, {"clearance"}),                       # HV functional outer 1.2
    ("DC+", "GND", "In2", 0.6, set()),                             # HV class clearance 0.5 inner
    ("/05 PFC/PE", "GND", "F", 2.5, {"creepage"}),                 # PE-PRI basic creepage 3.2
]
SLOTS = [(x, y) for y in (-70, -40, -10) for x in (-55, -30, 30, 55)]
HOLE_TEST = ("GND", "F", 4.0, {"clearance", "creepage"})          # 4 mm from the H4 ring: 6.4 mm rule


def track(b, net, layer, x1, y, x2, w=0.3):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x1), pcbnew.FromMM(y)))
    t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x2), pcbnew.FromMM(y)))
    t.SetWidth(pcbnew.FromMM(w))
    t.SetLayer(layer)
    t.SetNet(net)
    b.Add(t)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        for ext in ("kicad_pcb", "kicad_pro", "kicad_dru"):
            shutil.copy(os.path.join(SRC, f"tube_psu_5_2.{ext}"), tmp)
        pcb = os.path.join(tmp, "tube_psu_5_2.kicad_pcb")
        b = pcbnew.LoadBoard(pcb)
        nets = {}

        def net(name):
            if name not in nets:
                n = pcbnew.NETINFO_ITEM(b, name)
                b.Add(n)
                nets[name] = n
            return nets[name]

        spots = []
        for (na, nb, layer, gap, exp), (x, y) in zip(CASES, SLOTS):
            track(b, net(na), L[layer], x - 3, y, x + 3)
            track(b, net(nb), L[layer], x - 3, y + gap + 0.3, x + 3)   # 0.3 mm track width
            spots.append(((x, y + gap / 2), f"{na} / {nb} on {layer}, gap {gap} mm", exp))
        h4 = next(fp for fp in b.GetFootprints() if fp.GetReference() == "H4").GetPosition()
        hx, hy = h4.x / 1e6, h4.y / 1e6
        na, layer, gap, exp = HOLE_TEST
        yy = hy + 1.75 + gap + 0.15
        track(b, net(na), L[layer], hx - 3, yy, hx + 3)
        spots.append(((hx, hy + 2.5), f"{na} {gap} mm from the H4 ring on {layer}", exp))
        pcbnew.SaveBoard(pcb, b)
        rpt = os.path.join(tmp, "drc.json")
        subprocess.run([CLI, "pcb", "drc", "--format", "json", "--severity-all", "-o", rpt, pcb],
                       check=True, capture_output=True)
        with open(rpt) as f:
            viol = json.load(f)["violations"]
    found = [set() for _ in spots]
    other = []
    for v in viol:
        if v["type"] in ("lib_footprint_issues", "track_dangling"):   # test tracks end in the air
            continue
        p = v["items"][0]["pos"]
        d, i = min(((p["x"] - sx) ** 2 + (p["y"] - sy) ** 2, i) for i, ((sx, sy), _, _) in enumerate(spots))
        if d > 15 ** 2:
            other.append(v["type"] + ": " + v["description"])
        else:
            found[i].add(v["type"])
    bad = 0
    for (pos, what, exp), got in zip(spots, found):
        ok = got == exp
        bad += not ok
        print(f"check_rules: {'ok  ' if ok else 'FAIL'} {what}: expected {sorted(exp) or 'none'}, got {sorted(got) or 'none'}")
    for o in other:
        print("check_rules: unexpected " + o)
    print(f"check_rules: {len(spots) - bad}/{len(spots)} rule tests passed" + (f", {len(other)} unexpected" if other else ""))
    return 1 if bad or other else 0


if __name__ == "__main__":
    sys.exit(main())
