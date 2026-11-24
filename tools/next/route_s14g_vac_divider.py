#!/usr/bin/env python3
"""Stage 14g (one-shot, not re-runnable; run with tools/p2k/bin/kipy): VAC divider pad gaps R47 / R48 <-> R50 / R51.

    tools/p2k/bin/kipy tools/next/route_s14g_vac_divider.py [--dry-run OUT.kicad_pcb]

Design review 2026-11-24 (findings 09 F2, 05 F3): the AC1 leg R47 / R48 (y 8.6) and the AC2 leg R50 / R51 (y 6.5) are
0805s 0.70 mm apart pad to pad on B.Cu (AC1-AC2 and the two intermediate node pairs; same as 5.1). Moving R47 / R48
0.5 mm south is not possible as such: R48 pad 1 and R47 pad 2 would come nearer than the achieved H7 limit (3.5 mm
from the hole wall = 5.0 mm from the centre, kicad_dru "Mounting hole H7 ..."), and R50 cannot go north (L1 pad 1,
PFC_DRAIN_2, 1.16 mm). So:
  * R47 (0.8, 8.6) -> (-0.2, 9.15) (south 0.55, west 1.0: its pads still overlap R50's in x, pad 2 stays >= 5.0 mm
    from the H7 centre);
  * R48 (4.3, 8.6) -> (4.9, 8.7) (south 0.1, east 0.6 so that its pad 1 clears R50 pad 2 diagonally; pad 1 5.08 mm
    from the H7 centre);
  * R51 (4.3, 6.5) -> (4.3, 6.05) (north 0.45; its In2 via (5.6, 6.3) stays inside pad 2);
  * the short links re-drawn: R47.2 -> R48.1, R50.2 -> R51.1, R48.2 -> via (6.4, 8.6); AC1 reaches R47.1 on its old
    track, shortened to start at the R47.1 centre (-1.2, 9.5); old 0.15 mm pad stubs removed.
All three pairs then 1.25 mm apart (>= 1.2 mm HV rule for two footprints). Record: kicad_next/routing/moves_s14g.json.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s14_common  # noqa: E402


def edit(b, ed):
    ed.move_footprint("R47", (-0.2, 9.15), 0.0)
    ed.move_footprint("R48", (4.9, 8.7), 0.0)
    ed.move_footprint("R51", (4.3, 6.05), 0.0)
    ed.delete_track("AC1", "B.Cu", (-0.2, 8.6), (-1.1, 9.5), 0.3)
    ed.delete_track("AC1", "B.Cu", (-1.1, 9.5), (-3.5, 9.5), 0.3)
    ed.add_track("AC1", "B.Cu", (-1.2, 9.5), (-3.5, 9.5), 0.3)
    ed.delete_track("Net-(R47-Pad2)", "B.Cu", (1.8, 8.6), (3.3, 8.6))
    ed.add_track("Net-(R47-Pad2)", "B.Cu", (0.8, 9.15), (3.9, 8.7), 0.25)
    ed.delete_track("Net-(R50-Pad2)", "B.Cu", (3.3, 6.5), (1.8, 6.5))
    ed.add_track("Net-(R50-Pad2)", "B.Cu", (1.8, 6.5), (3.3, 6.05), 0.25)
    ed.delete_track("Net-(R48-Pad2)", "B.Cu", (5.3272, 8.6), (6.2, 8.6))
    ed.delete_track("Net-(R48-Pad2)", "B.Cu", (5.3, 8.6), (6.2, 8.6))
    ed.delete_track("Net-(R48-Pad2)", "B.Cu", (5.3, 8.6), (6.4, 8.6), 0.3)
    ed.add_track("Net-(R48-Pad2)", "B.Cu", (5.9, 8.7), (6.4, 8.6), 0.3)
    ed.delete_track("Net-(R51-Pad2)", "B.Cu", (5.3, 6.5), (6.1, 6.5))
    ed.delete_track("Net-(R51-Pad2)", "B.Cu", (6.1, 6.5), (5.3272, 6.5))


if __name__ == "__main__":
    sys.exit(s14_common.main("s14g", __file__, edit, sys.argv[1:]))
