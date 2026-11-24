#!/usr/bin/env python3
"""Stage 15a (one-shot, not re-runnable; run with tools/p2k/bin/kipy): DRV6 VDDB decoupling capacitor C141.

    tools/p2k/bin/kipy tools/next/route_s15a_drv6_cap.py [--dry-run OUT.kicad_pcb]

Owner decision 2026-11-24 (findings 02 F1, 11 F8): DRV6 (UCC21520, B.Cu, 180 deg) had no capacitor at VDDB (pin 11,
15V_ISO_SEC); the nearest, C43, stood 11.9 mm away. New C141 100 nF X7R 0603 on B.Cu west of the pin row, standing
north-south at x 54.6 between pin 11 (y -55.102) and pin 9 (VSSB, ISO_GND, y -52.562): pad 1 (15V_ISO_SEC) north,
pad 2 (ISO_GND) south, each joined to its pin by a 0.4 mm B.Cu track (45 deg out of the east half of the pad - the TR3 barrier keep-out
for tracks / vias ends at x 54.5 - then straight east onto the pin, where the existing 1.6 mm stubs to the plane vias
at x 57.957 start). The barrier slot edge is at x 52.015.
Record: kicad_next/routing/moves_s15a.json.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s14_common  # noqa: E402
import s15_common as S  # noqa: E402

X = 54.6


def edit(b, ed):
    S.add_footprint(ed, "C141", (X, -53.832), 270.0, back=True)
    p1, p2 = S.pad_xy(ed, "C141", "1"), S.pad_xy(ed, "C141", "2")
    if not (abs(p1[0] - X) < 0.01 and abs(p1[1] + 54.607) < 0.01 and abs(p2[1] + 53.057) < 0.01):
        ed.fail(f"C141 pads at {p1} / {p2}, expected pad 1 north (y -54.607), pad 2 south (y -53.057)")
    S.pad_xy(ed, "DRV6", "11")
    # tracks leave from the east half of the pads: the TR3 barrier keep-out (tracks / vias) ends at x 54.5
    ed.add_path("15V_ISO_SEC", "B.Cu", [(X + 0.25, p1[1]), (X + 0.745, -55.102), (56.357, -55.102)], 0.4)
    ed.add_path("ISO_GND", "B.Cu", [(X + 0.25, p2[1]), (X + 0.745, -52.562), (56.357, -52.562)], 0.4)


if __name__ == "__main__":
    sys.exit(s14_common.main("s15a", __file__, edit, sys.argv[1:]))
