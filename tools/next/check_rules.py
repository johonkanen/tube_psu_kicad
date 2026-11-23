#!/usr/bin/env python3
"""Functional test of the 5.2 design rules (run with tools/p2k/bin/kipy).

kicad-cli does not report syntax errors in a .kicad_dru (a broken rule is silently dropped), so this
test proves that the rules parse and act: it writes the empty board skeleton (make_board.write) and copies kicad_next/tube_psu_5_2.{kicad_pro,
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
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_board  # noqa: E402
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
    ("420V", "HT_GND", "F", 4.5, {"creepage"}),                    # SEC(HV)-HEATER functional creepage 5.2
    ("ISO_GND", "HT_GND", "F", 1.2, {"creepage"}),                 # SEC(LV)-HEATER creepage 1.5
    ("ISO_GND", "HT_GND", "F", 2.0, set()),
    ("DC+", "GND", "F", 1.0, {"clearance"}),                       # HV functional outer 1.2
    ("DC+", "GND", "In2", 0.6, set()),                             # HV class clearance 0.5 inner
    ("/05 PFC/PE", "GND", "F", 2.5, {"creepage"}),                 # PE-PRI basic creepage 3.2
    ("GND", "ISO_UART_GND", "In2", 7.0, {"clearance"}),            # PRI-UART inner 8.0 (5.2 island)
    ("UART_3V3", "HT_GND", "F", 0.8, {"clearance"}),               # HEATER-UART functional 1.0
    ("+3V3", "UART_3V3", "F", 7.0, {"creepage"}),                   # PRI-UART reinforced creepage 8.0
    ("ISO_GND", "ISO_UART_GND", "F", 8.0, {"creepage"}),           # SEC-UART reinforced creepage 8.4
    ("DHB_HI_GATE", "DHB_HI_SOURCE", "F", 0.3, set()),              # one high-side driver group: 0.2 (not 1.2 / 0.5)
    ("DHB_HI_GATE", "DC+", "F", 1.0, {"clearance"}),               # ... but towards DC+ the 1.2 stays
    ("DHB_HI_GATE", "/06 Heaters/HEATER_HI_SOURCE", "F", 1.0, {"clearance"}),   # ... and between two groups
    ("DHB_HI_GATE", "DHB_LOW_GATE", "F", 1.0, {"clearance"}),      # ... and towards the low side
    ("Net-(R109-Pad1)", "GND", "F", 0.3, set()),                    # GND leg of the DC-link difference amplifier: SIGNAL (3c)
    ("Net-(R10-Pad1)", "GND", "F", 1.0, {"clearance"}),            # ... the DC+ leg stays HV (1.2)
    ("5V", "GND", "In2", 0.16, set()),                              # PRIMARY_LV on inner layers: 0.15 (stage 3d)
    ("5V", "GND", "F", 0.16, {"clearance"}),                       # ... outer layers keep the class clearance 0.2
    ("5V", "DC+", "In2", 0.3, {"clearance"}),                      # ... and a HV net its 0.5 on the inner layers
]
# The four extra slots (5.2 UART cases): KiCad 10 reported no creepage violation for test tracks at
# (-10, -70) and (75, -50) (clearance works there; not understood - the creepage cases sit at (-10, -15) /
# (75, 0), where it is reported). A wrong rule still shows up as a FAIL, a silent slot only as a false FAIL.
SLOTS = [(x, y) for y in (-70, -40, -10, 15) for x in (-55, -30, 30, 55)] + [(-10, -70), (75, -50), (-10, -15), (75, 0)] + [(-5, -25), (15, -25), (-42.5, 5), (42.5, 5)] + [(-30, -84), (30, -84), (55, -84)]
assert len(CASES) <= len(SLOTS), "add test positions to SLOTS"
# Mounting holes (no copper ring since stage 13c; the earthed screw has a 6 mm head): (hole, net, layer, distance of the
# track edge from the hole CENTRE mm, side of the hole, expected). One test per hole (spots are matched by distance; the
# side keeps the track away from the other test spots and the board edge). General rules: primary
# 6.2 mm, secondary 7.2 mm, UART 4.0 mm from the centre; per-hole rules hold what the board achieves (H4 4.9, H7 5.0,
# H8 6.2, H2 3.1 mm from the centre). The skeleton board has the 5.1 holes, H5 included. KiCad reports an NPTH
# without copper as hole_clearance and creepage (from the hole wall), on inner layers too.
HC = {"hole_clearance", "creepage"}
HOLE_TESTS = [("H6", "GND", "F", 5.9, "N", HC),                       # primary 6.2 > 5.9
              ("H1", "GND", "In3", 6.4, "S", set()),                  # ... 6.4 passes, inner layer as well
              ("H3", "ISO_GND", "B", 6.9, "S", HC),                   # secondary 7.2 > 6.9
              ("H5", "ISO_GND", "F", 7.4, "N", set()),
              ("H4", "GND", "In2", 4.6, "S", HC),                     # H4 achieved 4.9 > 4.6
              ("H7", "GND", "B", 5.2, "N", set()),                    # H7 achieved 5.0 < 5.2
              ("H8", "ISO_GND", "F", 6.0, "E", HC),                   # H8 achieved 6.2 > 6.0
              ("H2", "ISO_UART_GND", "B", 2.9, "S", {"hole_clearance"})]   # H2 achieved 3.1 > 2.9 (no creepage rule)


# Pads of one fine-pitch footprint (VSSOP-8, pad gap 0.15 mm; U10): (nets on odd / even pads, position, expected).
# Low-voltage classes: rule "Same-footprint pad gap, low-voltage classes" allows 0.15 mm; a HV net keeps its class
# clearance (0.5 mm) - the control that the rule does not open the gap for HV nets.
PAD_FP = ("Package_SO", "VSSOP-8_3x3mm_P0.65mm")
PAD_TESTS = [("+3V3", "GND", (8, -12), set()),
             ("ISO_GND", "5V_ISOL", (8, 3), set()),
             ("DC+", "GND", (78, -25), {"clearance"})]
# A HV track next to the pad row of a footprint, edge-to-edge gap mm (stage 3c): (pad net, track net, position, gap,
# expected). The pad of a no-connect pin is left out of "HV functional, outer layers" (class clearance 0.5 stays);
# the same track next to a pad with a net still fails.
NC_TESTS = [("unconnected-(PADTEST4-NC-Pad1)", "DC+", (-42.5, -25), 0.8, set()),
            ("GND", "DC+", (42.5, -25), 0.8, {"clearance"}),
            ("unconnected-(PADTEST6-NC-Pad1)", "DC+", (-42.5, -55), 0.3, {"clearance"})]


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
        for ext in ("kicad_pro", "kicad_dru"):
            shutil.copy(os.path.join(SRC, f"tube_psu_5_2.{ext}"), tmp)
        pcb = os.path.join(tmp, "tube_psu_5_2.kicad_pcb")
        make_board.write(pcb, quiet=True)   # empty skeleton (outline, H1-H8, layers, stackup), not the routed board
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
        hpos = {fp.GetReference(): fp.GetPosition() for fp in b.GetFootprints() if fp.GetReference().startswith("H")}
        for ref, na, layer, dist, side, exp in HOLE_TESTS:
            hx, hy = hpos[ref].x / 1e6, hpos[ref].y / 1e6
            o = dist + 0.15                                               # 0.3 mm track: edge at dist from the centre
            if side == "E":                                               # vertical track east of the hole
                t = pcbnew.PCB_TRACK(b)
                t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(hx + o), pcbnew.FromMM(hy - 3)))
                t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(hx + o), pcbnew.FromMM(hy + 3)))
                t.SetWidth(pcbnew.FromMM(0.3))
                t.SetLayer(L[layer])
                t.SetNet(net(na))
                b.Add(t)
                spot = (hx + dist / 2, hy)
            else:
                sgn = 1 if side == "S" else -1
                track(b, net(na), L[layer], hx - 3, hy + sgn * o, hx + 3)
                spot = (hx, hy + sgn * dist / 2)
            spots.append((spot, f"{na} {dist} mm from the centre of {ref} on {layer}", exp))
        lib = os.path.join(os.environ.get("KICAD_MOUNT", ""), "share", "kicad", "footprints", PAD_FP[0] + ".pretty")
        for i, (na, nb, (x, y), exp) in enumerate(PAD_TESTS):
            fp = pcbnew.FootprintLoad(lib, PAD_FP[1])
            fp.SetReference(f"PADTEST{i + 1}")
            fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
            for p in fp.Pads():
                p.SetNet(net(na if int(p.GetNumber()) % 2 else nb))
            b.Add(fp)
            spots.append(((x, y), f"{PAD_FP[1]} pads {na} / {nb} (gap 0.15 mm)", exp))
        for i, (na, nb, (x, y), gap, exp) in enumerate(NC_TESTS):
            fp = pcbnew.FootprintLoad(lib, PAD_FP[1])
            fp.SetReference(f"PADTEST{len(PAD_TESTS) + i + 1}")
            fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
            for p in fp.Pads():
                p.SetNet(net(na))
            b.Add(fp)
            yt = max(p.GetBoundingBox().GetBottom() for p in fp.Pads()) / 1e6 + gap + 0.15
            track(b, net(nb), L["F"], x - 3, yt, x + 3)
            spots.append(((x, y), f"{nb} track {gap} mm from {PAD_FP[1]} pads on {na}", exp))
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
