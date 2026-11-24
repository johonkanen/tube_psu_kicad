#!/usr/bin/env python3
"""Stage 15g (one-shot, not re-runnable; run with tools/p2k/bin/kipy): J2 socket pads 1.0 -> 1.02 mm.

    tools/p2k/bin/kipy tools/next/route_s15g_j2_pads.py [--dry-run OUT.kicad_pcb]

After stage 15f the fab check of tools/next/jlc_fab.py measured the annular ring of the 1.0 mm / 0.70 mm J2 pads as
0.149 mm (polygon approximation), i.e. "below the JLC minimum 0.15 mm". The footprint
PinSocket_2x25_P1.27mm_Vertical_XKB_X1321FV now has 1.02 mm pads (ring 0.16 mm, pad gap 0.25 mm); this stage puts
the library footprint on the board again (same place, fields and nets from the netlist) and refills. One track
moves: the F.Cu HEATER_I_MEAS run west of pads 45-49 at x 32.4 (0.149 mm from pads 47 / 49 with the larger pads)
goes to x 32.36 (0.19 mm).
Record: kicad_next/routing/moves_s15g.json.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s14_common  # noqa: E402
import s15_common as S  # noqa: E402


def edit(b, ed):
    S.replace_footprint(ed, "J2")
    n = "HEATER_I_MEAS"
    for a, c in (((32.4, 8.1), (32.4, 8.9)), ((32.4, 7.5), (32.4, 6.5195)), ((32.1, 7.8), (32.4, 7.5)),
                 ((32.4, 6.5195), (33.1357, 5.7838)), ((32.4, 8.9), (33.5, 10.0)), ((32.1, 7.8), (32.4, 8.1))):
        ed.delete_track(n, "F.Cu", a, c, 0.152)
    ed.add_path(n, "F.Cu", [(32.1, 7.8), (32.36, 7.54), (32.36, 6.5195), (33.1357, 5.7838)], 0.152)
    ed.add_path(n, "F.Cu", [(32.1, 7.8), (32.36, 8.06), (32.36, 8.94), (33.5, 10.0)], 0.152)


if __name__ == "__main__":
    sys.exit(s14_common.main("s15g", __file__, edit, sys.argv[1:]))
