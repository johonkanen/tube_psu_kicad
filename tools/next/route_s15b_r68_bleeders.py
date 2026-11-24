#!/usr/bin/env python3
"""Stage 15b (one-shot, not re-runnable; run with tools/p2k/bin/kipy): -100V BIAS bleeder R68 -> six 1206 in parallel.

    tools/p2k/bin/kipy tools/next/route_s15b_r68_bleeders.py [--dry-run OUT.kicad_pcb]

Owner decision 2026-11-24 (findings 01 F1): R68 12.1k 1206 dissipated 0.53-0.59 W (simulated rail 80.2-84.4 V) on
B.Cu under the body of C102. Now R68 + R159 ... R163 = six 73.2k 1206 (12.2k total, +0.8 %), 97 mW each at 84.4 V.
R68 leaves (75.165, 11.2) (its two B.Cu tracks to C102 are deleted). The six stand on B.Cu in the strip between
the P5V_OUT terminal row (y 1.2) and the N80V_OUT terminal row (y 7.0), under the F.Cu -100V BIAS pour, away from
C102 (body x 72-82, y 6.4-16.4) and under D8 only (F.Cu, a 1 A diode carrying the 10-20 mA rail current):
  R68 / R159 / R160 / R161 north-south at y 4.3, x 72.7 / 75.3 / 77.9 / 80.5 (pitch 2.6 mm), pad 1 (ISO_GND) north in
    the B.Cu ISO_GND pour, pad 2 (-100V BIAS) south, dropping to a 0.5 mm B.Cu bus at y 7.0;
  R162 / R163 east-west at y 4.35, x 83.95 / 88.56 (their courtyards stay clear of the 1.4 mm terminal holes, which a
    north-south 1206 between the rows cannot), the -100V BIAS pads facing each other (x 85.41 / 87.10) and joined,
    with a drop from x 86.26 to the bus; the ISO_GND pad of R162 (x 82.49) in the pour, the one of R163 (x 90.02,
    beyond the pour) on a 0.6 / 0.3 mm via in the pad to the In1 / In4 ISO_GND planes. Pad 2 of R163 is 1.26 mm from
    the B.Cu 5V_ISOL track at y 1.2 (HV functional 1.2 mm).
The bus runs x 72.7 ... 88.4 at y 7.0 through the two N80V_OUT terminal pads (83.4 / 88.4, 7.0); its edge is 7.23 mm
from the H8 centre (secondary limit 7.2 mm). The pads of the north-south row stay outside the C102 body circle
(D 10 mm round (77, 11.35); nearest pad corner R160 5.11 mm from its centre). R68 pad 1 is 1.25 mm from the TR1 pin-5 pad (Net-(D8-K)).
Record: kicad_next/routing/moves_s15b.json.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s14_common  # noqa: E402
import s15_common as S  # noqa: E402

VERT = (("R68", 72.7), ("R159", 75.3), ("R160", 77.9), ("R161", 80.5))      # north-south, y 4.3
HOR = (("R162", 83.95, 0.0), ("R163", 88.56, 180.0))                          # east-west, y 4.35
YV, YH, YBUS = 4.3, 4.35, 7.0
NET = "-100V BIAS"


def edit(b, ed):
    # old R68 tracks: ISO_GND R68.1 -> C102.1, -100V BIAS C102.2 -> R68.2 (both B.Cu)
    if S.delete_tracks_in(ed, "ISO_GND", "B.Cu", (73.5, 11.0, 76.2, 13.6)) != 3:
        ed.fail("expected three ISO_GND segments R68.1 -> C102.1")
    if S.delete_tracks_in(ed, NET, "B.Cu", (76.8, 8.8, 77.1, 10.6)) != 3:
        ed.fail("expected three -100V BIAS segments C102.2 -> R68.2")
    ed.move_footprint("R68", (VERT[0][1], YV), 270.0)
    S.sync_fields(ed, "R68")
    for ref, x in VERT[1:]:
        S.add_footprint(ed, ref, (x, YV), 270.0, back=True)
    for ref, x in VERT:
        p1, p2 = S.pad_xy(ed, ref, "1"), S.pad_xy(ed, ref, "2")
        if not (abs(p1[0] - x) < 0.01 and p1[1] < p2[1]):
            ed.fail(f"{ref}: pad 1 {p1} / pad 2 {p2}: pad 1 should be north")
        ed.add_track(NET, "B.Cu", p2, (x, YBUS), 0.5)
    for ref, x, rot in HOR:
        S.add_footprint(ed, ref, (x, YH), rot, back=True)
    a1, a2 = S.pad_xy(ed, "R162", "1"), S.pad_xy(ed, "R162", "2")
    c1, c2 = S.pad_xy(ed, "R163", "1"), S.pad_xy(ed, "R163", "2")
    if not (a1[0] < a2[0] < c2[0] < c1[0] and abs(a2[1] - YH) < 0.01):
        ed.fail(f"R162 {a1} {a2} / R163 {c1} {c2}: expected the -100V pads (2) facing each other")
    xm = round((a2[0] + c2[0]) / 2, 3)
    ed.add_track(NET, "B.Cu", a2, c2, 0.5)
    ed.add_track(NET, "B.Cu", (xm, YH), (xm, YBUS), 0.5)
    ed.add_track(NET, "B.Cu", (VERT[0][1], YBUS), (88.4, YBUS), 0.5)
    ed.add_via("ISO_GND", c1, 0.6, 0.3)          # R163 pad 1: the B.Cu pour does not reach it; via in pad to In1 / In4


if __name__ == "__main__":
    sys.exit(s14_common.main("s15b", __file__, edit, sys.argv[1:]))
