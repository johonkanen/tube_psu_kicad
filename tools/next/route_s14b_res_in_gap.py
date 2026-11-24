#!/usr/bin/env python3
"""Stage 14b (one-shot, not re-runnable; run with tools/p2k/bin/kipy): mains RES_IN <-> IN2 gap on F.Cu.

    tools/p2k/bin/kipy tools/next/route_s14b_res_in_gap.py [--dry-run OUT.kicad_pcb]

Design review 2026-11-24 (findings 05 F1): the north-west corner (-60.0, -10.4) of the IN2 F.Cu pour arm
'S3A_IN2_neutral' came 1.81 mm from the RES_IN pour corner (-61.41, -11.46) (5.1: 8.61 mm). The corner is chamfered
(-60.0, -8.2) - (-58.1, -10.4); the bend of the arm stays >= 3.0 mm wide (2.5 mm before). Nothing else changes.
Record: kicad_next/routing/moves_s14b.json.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s14_common  # noqa: E402


def edit(b, ed):
    z = ed.zone("S3A_IN2_neutral", "/05 PFC/IN2", "F.Cu")
    old = ed.outline(z)
    want = [[-60.0, -10.4], [-50.2, -10.4], [-50.2, -7.9], [-56.2, -7.9], [-56.2, 2.6], [-60.0, 2.6]]
    if len(old) != 1 or len(old[0]) != 1 or sorted(map(tuple, old[0][0])) != sorted(map(tuple, want)):
        ed.fail(f"unexpected outline {old}")
    ed.set_outline(z, [[[(-60.0, -8.2), (-58.1, -10.4), (-50.2, -10.4), (-50.2, -7.9), (-56.2, -7.9), (-56.2, 2.6),
                         (-60.0, 2.6)]]], "chamfer: >= 3 mm to the RES_IN pour corner (-61.41, -11.46)")


if __name__ == "__main__":
    sys.exit(s14_common.main("s14b", __file__, edit, sys.argv[1:]))
