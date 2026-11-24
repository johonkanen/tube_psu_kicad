#!/usr/bin/env python3
"""Stage 15f (one-shot, not re-runnable; run with tools/p2k/bin/kipy): J2 becomes the female 2x25 1.27 mm socket.

    tools/p2k/bin/kipy tools/next/route_s15f_j2_socket.py [--dry-run OUT.kicad_pcb]

Owner decision 2026-11-24 (findings 04 F1): J2 = XKB X1321FV-2x25-C43D24 (C2881768); the footprint
tube_psu_next_parts:PinSocket_2x25_P1.27mm_Vertical_XKB_X1321FV keeps every pad position of the old
tube_psu:PinHeader_2x25_P1.27mm_Vertical_Proteus, drill 0.5 -> 0.70 mm and pad 0.812 -> 1.0 mm (ring 0.15 mm),
inner-layer pads only on connected layers (outer pads kept). With 1.0 mm pads on the 1.27 mm grid (0.27 mm between
pads) no outer-layer track fits between two pins; three spots had one:
  * PFC_I1_MEAS (via (32.1, 4.3) -> pad 42 on F.Cu between pads 41 / 43): the same path moved to In3 (+3V3 plane
    layer); on In3 pads 41 / 43 have no copper (not connected there), hole walls 0.21 mm from the 0.15 mm track
    (min_hole_clearance 0.2 mm), pad 42 gets its In3 pad.
  * PFC_I2_MEAS (B.Cu (31.115, 2.39) -> between pads 41 / 43 -> pad 44): B.Cu stub ends in a new via (31.115, 2.1)
    (0.25 mm below the F.Cu DC_LINK_MEAS track at y 2.7), In3 x 31.4 down, between holes 43 / 45 at y 5.149 to pad 44;
    pad 44 -> C77 on B.Cu unchanged.
  * DAB_DIS (F.Cu 0.4 mm diagonal to pad 18 passing pad 16 at 0.12 mm): the vertical at x 35.725 runs on to y -12.85,
    the diagonal goes from there to the pad-18 centre (0.37 mm from pad 16); the parallel 0.2 mm diagonal is deleted.
Record: kicad_next/routing/moves_s15f.json.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s14_common  # noqa: E402
import s15_common as S  # noqa: E402


def edit(b, ed):
    S.replace_footprint(ed, "J2")
    # PFC_I1_MEAS: F.Cu between pads 41 / 43 -> In3
    pts = [(32.1, 4.3), (32.5212, 3.8788), (33.7707, 3.8788), (34.4057, 3.2438)]
    for a, c in zip(pts, pts[1:]):
        ed.delete_track("PFC_I1_MEAS", "F.Cu", a, c, 0.15)
    ed.add_path("PFC_I1_MEAS", "In3.Power", pts, 0.15)
    # PFC_I2_MEAS: B.Cu between pads 41 / 43 -> via + In3 between holes 43 / 45
    ed.delete_track("PFC_I2_MEAS", "B.Cu", (31.115, 2.3938), (31.115, -0.889), 0.152)
    ed.delete_track("PFC_I2_MEAS", "B.Cu", (32.6, 3.8788), (31.115, 2.3938), 0.152)
    ed.delete_track("PFC_I2_MEAS", "B.Cu", (33.7707, 3.8788), (32.6, 3.8788), 0.152)
    ed.delete_track("PFC_I2_MEAS", "B.Cu", (34.4057, 4.5138), (33.7707, 3.8788), 0.152)
    ed.add_track("PFC_I2_MEAS", "B.Cu", (31.115, -0.889), (31.115, 2.1), 0.152)
    ed.add_via("PFC_I2_MEAS", (31.115, 2.1), 0.5, 0.3)
    ed.add_path("PFC_I2_MEAS", "In3.Power", [(31.115, 2.1), (31.4, 2.385), (31.4, 4.55), (32.0, 5.1488),
                                              (33.7707, 5.1488), (34.4057, 4.5138)], 0.15)
    # DAB_DIS: diagonal to pad 18 away from pad 16
    ed.delete_track("DAB_DIS", "F.Cu", (35.725, -13.43), (34.425, -12.13), 0.4)
    ed.delete_track("DAB_DIS", "F.Cu", (35.725, -17.53), (35.725, -13.43), 0.4)
    ed.delete_track("DAB_DIS", "F.Cu", (35.805, -13.65), (34.405, -12.25), 0.2)
    ed.add_path("DAB_DIS", "F.Cu", [(35.725, -17.53), (35.725, -12.85), (34.405, -11.996)], 0.4)


if __name__ == "__main__":
    sys.exit(s14_common.main("s15f", __file__, edit, sys.argv[1:]))
