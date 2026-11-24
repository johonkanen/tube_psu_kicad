#!/usr/bin/env python3
"""Stage 14c (one-shot, not re-runnable; run with tools/p2k/bin/kipy): DC+ link at SICD1, PFC_DRAIN_1 neck.

    tools/p2k/bin/kipy tools/next/route_s14c_sicd1_dc_link.py [--dry-run OUT.kicad_pcb]

Design review 2026-11-24 (findings 05 F2, 11): the DC+ island C73.1 / DB1.2 / SICD2.K joined the DC+ trunk through a
1.34 mm F.Cu channel and one 1.0 mm B.Cu track (10.2, -18.65) -> (13.6, -18.65) -> (14.7, -19.75) -> (14.7, -22.1).
That track cannot grow to 2 mm: between the SICD1 anode pad (B.Cu, PFC_DRAIN_1) and the C73.2 GND via cluster
(via (13.8, -16.4), 1.016 mm GND tracks) there is room for 1.1 mm of copper with 1.2 mm HV spacing on both sides.
Instead (outer layers only):
  * a second B.Cu DC+ link, 2.0 mm, west of SICD1: island (11.3 / 10.2, -17.8) -> (8.4, -19.6) -> (8.4, -26.48) -> SICD1.K
    (THT, sits in the F.Cu DC+ trunk pour); 1.4 mm from the SICD1 anode and Q5 pads;
  * two more island vias (10.2 / 11.3, -17.4); one more trunk-end via of the old link (14.7, -23.2);
  * PFC_DRAIN_1 F.Cu pour 10 outline opened towards the DC+ corner (8.2..9.4, -25.7..-23.1) and south to y -20.3
    (x 6.3..10.7); the fill keeps its 1.2 mm to DC+ / Q5.3 by itself;
  * correction of stage 14a: the HEATER_CURRENT B.Cu pour 20 outline had its 5.1 hole (octagon at (-12.87, -80.4))
    appended to the outer ring (s14_common.set_outline used aHole = -1 = outer ring; fixed); restored as
    rectangle x -14.0 .. -11.2, y -81.5 .. -79.3 with the octagon as a hole.
Record: kicad_next/routing/moves_s14c.json.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s14_common  # noqa: E402

DC = "DC+"


def edit(b, ed):
    ed.add_path(DC, "B.Cu", [(11.3, -17.8), (10.2, -17.8), (8.4, -19.6), (8.4, -26.48), (11.8, -26.48)], 2.0)
    for p in [(10.2, -17.4), (11.3, -17.4)]:
        ed.add_via(DC, p, 0.8, 0.4)
    ed.add_track(DC, "B.Cu", (14.7, -22.1), (14.7, -23.2), 1.0)
    ed.add_via(DC, (14.7, -23.2), 0.8, 0.4)
    z = ed.zone("Proteus F.Cu pour 10", "/05 PFC/PFC_DRAIN_1", "F.Cu")
    old = ed.outline(z)
    ring = [tuple(p) for p in old[0][0]]

    def idx(p):
        k = [i for i, q in enumerate(ring) if abs(q[0] - p[0]) < 0.02 and abs(q[1] - p[1]) < 0.02]
        if len(k) != 1:
            ed.fail(f"outline vertex {p} found {len(k)} times")
        return k[0]
    i0, i1 = idx((8.2, -25.7)), idx((12.9, -23.1))
    j0, j1 = idx((10.7, -20.3)), idx((-1.65, -21.72))
    if not (i0 < i1 < j0 < j1):
        ed.fail("unexpected vertex order")
    new = (ring[:i0 + 1] + [(9.4, -25.7), (9.4, -23.1)] + ring[i1:j0 + 1] + [(6.3, -20.3), (6.3, -21.72)]
           + ring[j1:])
    ed.set_outline(z, [[new] + old[0][1:]], "PFC_DRAIN_1 neck Q5 -> SICD1.A widened (fill keeps its clearances)")
    # correction of stage 14a (pour 20 hole merged into the outer ring)
    z = ed.zone("Proteus B.Cu pour 20", "HEATER_CURRENT", "B.Cu")
    o = ed.outline(z)
    rect = [(-14.0, -81.5), (-11.2, -81.5), (-11.2, -79.3), (-14.0, -79.3)]
    if len(o) != 1 or len(o[0]) != 1 or len(o[0][0]) != 12 or [tuple(p) for p in o[0][0][:4]] != rect:
        ed.fail(f"pour 20 outline not as left by stage 14a: {o}")
    ed.set_outline(z, [[rect, [tuple(p) for p in o[0][0][4:]]]], "stage 14a correction: octagon back as a hole")


if __name__ == "__main__":
    sys.exit(s14_common.main("s14c", __file__, edit, sys.argv[1:]))
