#!/usr/bin/env python3
"""Stage 14e (one-shot, not re-runnable; run with tools/p2k/bin/kipy): Q21 gate track away from the DRV6 input side.

    tools/p2k/bin/kipy tools/next/route_s14e_q21_gate.py [--dry-run OUT.kicad_pcb]

Design review 2026-11-24 (findings 02 F3 / C1): DHB_HI_GATE_SEC (0 <-> 435 V) ran as a B.Cu diagonal under the DRV6
body to (62.957, -54.882), 1.211 mm from the DT pad 6 and 1.254 mm from DAB_DIS_SEC (5.1: about 2.4 mm). Re-routed
(reviewer's suggestion): diagonal from (57.657, -60.182) only to (60.3, -57.539), then north along x 60.3 to
(60.3, -50.1) and into the old track at (59.949, -49.749). B.Cu only (high-side group, no inner layer).
Record: kicad_next/routing/moves_s14e.json.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s14_common  # noqa: E402

N = "DHB_HI_GATE_SEC"


def edit(b, ed):
    ed.delete_track(N, "B.Cu", (57.657, -60.182), (62.957, -54.882), 0.4)
    ed.delete_track(N, "B.Cu", (63.093, -54.693), (62.3, -53.9), 0.7)
    ed.delete_track(N, "B.Cu", (62.3, -53.9), (62.3, -52.1), 0.762)
    ed.delete_track(N, "B.Cu", (62.3, -52.1), (59.949, -49.749), 0.762)
    ed.add_track(N, "B.Cu", (57.657, -60.182), (60.3, -57.539), 0.4)
    ed.add_path(N, "B.Cu", [(60.3, -57.539), (60.3, -50.1), (59.949, -49.749)], 0.762)


if __name__ == "__main__":
    sys.exit(s14_common.main("s14e", __file__, edit, sys.argv[1:]))
