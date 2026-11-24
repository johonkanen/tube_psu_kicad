#!/usr/bin/env python3
"""Stage 14d (one-shot, not re-runnable; run with tools/p2k/bin/kipy): Q1 drain tab vias 12 -> 16.

    tools/p2k/bin/kipy tools/next/route_s14d_q1_tab_vias.py [--dry-run OUT.kicad_pcb]

Design review 2026-11-24 (findings 06 F3): the Q1 (synchronous rectifier) tab, net Q14_DRAIN, had 12 vias in a 3 x 4
grid (x -49.8 / -48.6 / -47.4, y -66.3 ... -69.9); 5.1 had 16 (4 x 4). The fourth column x -51.0 is restored
(0.5 / 0.3, the 5.1 positions, where the imported F.Cu / B.Cu pours still have their via holes). The narrowest channel
(4.48 mm) is set by the heater barrier keep-out of ISO1 / TR2 (south, y -66.0) and the 6V3 / HT_GND pours (north):
no local outline change widens it, so the pours are not touched; no inner-layer copper is added.
Record: kicad_next/routing/moves_s14d.json.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s14_common  # noqa: E402


def edit(b, ed):
    for y in (-66.3, -67.5, -68.7, -69.9):
        ed.add_via("/06 Heaters/Q14_DRAIN", (-51.0, y), 0.5, 0.3)


if __name__ == "__main__":
    sys.exit(s14_common.main("s14d", __file__, edit, sys.argv[1:]))
