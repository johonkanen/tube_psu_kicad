#!/usr/bin/env python3
"""Stage 17a (one-shot, not re-runnable; run with tools/p2k/bin/kipy): SICD2 pin column x 3.09 -> 3.40.

    tools/p2k/bin/kipy tools/next/route_s17a_sicd2_x.py [--dry-run OUT.kicad_pcb]

Design review 2026-11-24, finding 12 F1 (owner approval 2026-11-24): every device of the primary heatsink line sits
flat on one plate. Nominal back faces (pin column +- lead-centre-to-back: TO-220-2 C3D02060A V 2.585, TO-247
C2M0160120D A1 2.40): west row Q5 6.152, SICD2 5.675 -> 5.985 with the move (0.17 mm from Q5's plane instead of
0.48); slot SICD2 <-> Q6 (8.989) 3.31 -> 3.00 mm.
  * SICD2 (tube_psu_next_parts:TO-220-2_Vertical_KA, rot -90) 0.31 mm east, same y: K (DC+) (3.09, -3.82) ->
    (3.40, -3.82), A (PFC_DRAIN_2) (3.09, 1.26) -> (3.40, 1.26).
  * B.Cu PFC_DRAIN_2 (2.4 mm, stage 16a) re-ended at the new anode: L1.1 -> SICD2.A, SICD2.A -> (4.4, 1.26) ->
    (8.1, -2.436) -> Q6.2 (the first bend stays, the stub shortens by 0.31 mm).
  * The F.Cu pours (DC+ pour 29 round the cathode, PFC_DRAIN_2 pour 1 round the anode) keep their outlines; the
    refill follows the pads (solid connection, 1.2 mm HV clearance from the fill rule).
Record: kicad_next/routing/moves_s17a.json.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s14_common  # noqa: E402

D2 = "/05 PFC/PFC_DRAIN_2"


def edit(b, ed):
    f = ed.footprint("SICD2")
    if s14_common.r3(ed.pt(f.GetPosition())) != (3.09, -3.82):
        ed.fail("SICD2 not at (3.09, -3.82)")
    ed.move_footprint("SICD2", (3.40, -3.82))
    ed.delete_track(D2, "B.Cu", (-0.102, 3.342), (3.09, 1.26), 2.4)
    ed.delete_track(D2, "B.Cu", (3.09, 1.26), (4.4, 1.26), 2.4)
    ed.add_track(D2, "B.Cu", (-0.102, 3.342), (3.40, 1.26), 2.4)
    ed.add_track(D2, "B.Cu", (3.40, 1.26), (4.4, 1.26), 2.4)


if __name__ == "__main__":
    sys.exit(s14_common.main("s17a", __file__, edit, sys.argv[1:]))
