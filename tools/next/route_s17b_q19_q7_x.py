#!/usr/bin/env python3
"""Stage 17b (one-shot, not re-runnable; run with tools/p2k/bin/kipy): Q19 / Q7 pin column x 12.75 -> 11.60.

    tools/p2k/bin/kipy tools/next/route_s17b_q19_q7_x.py [--dry-run OUT.kicad_pcb]

Design review 2026-11-24, finding 12 F1 (owner approval 2026-11-24): the IPA60R280CFD7 FullPAK back faces of Q19 / Q7
(pin column - A2 nominal 2.64) go onto the plane of SICD1's padded tab (9.215 - 0.25 = 8.965): pins x 12.75 -> 11.60,
back face 10.11 -> 8.96. Same y, rot 90 (tab west).

What has to give way (the strip between the DRV5 pads and the FET pads shrinks from 3.78 to 2.63 mm):
  * DRV5 group 0.85 mm west: DRV5 (2.3 -> 1.45), C95, R127, the three In3 vias of PRI_DHB_HI / B12 / DAB_DIS at x -4.1,
    the 15V / GND / 5V vias at the east pins and every B.Cu track end in the box x -6.0 .. 9.75, y -55.35 .. -44.4
    (rubber band; the PRI / B12 bends, the GND via of C94, the U1A+ via (4.3, -55.25) and the In2 5V via (4.33, -50.75)
    stay, the 5V link under the body goes to x 4.7); inner-layer track ends follow their vias. C94 0.35 mm west (pads
    0.2 mm off pins 3 / 4); C118 (dead time, beside the NC pin 7) turned 90 deg next to R127, its GND by B.Cu round to
    the R127 GND pad (the 15V track x -6.75 keeps its 1.2 mm to D11). Without the shift R26 (needs 0.2 mm to C92, its
    courtyard off the Q19 pin-1 hole) does not fit west of the gate pad, C92 cannot go west (NC pin 13 0.5 mm, H4), and
    R26 east of the pins makes the gate loop longer.
  * High side (B.Cu only, no via in a group net): C92 (9.15, -46.525) -> (8.38, -46.79) (VDDA pad 3.46 mm from the H4
    hole edge, rule 3.4), R26 (10.85, -46.0) -> (10.05, -46.23); DHB_HI_GATE pin 15 -> through the pad gaps of C92 and R26
    -> R26.1 -> the kept 0.25 mm track y -45.69 to D30; return Q19.3 -> x 9.2 (1.2 mm off the DC+ pad) -> C92.1; pin 14
    -> C92.1; VDDA C92.2 -> y -44.25 -> R41.2. R22, D30, R53, R41 and the +1V65_BIAS via (13.0, -44.076) stay.
  * Low side: R90 (10.6, -56.6) -> (10.0, -56.6) (courtyard off the Q7 pin-1 hole), R70 (10.4, -59.6) -> (9.6, -59.3)
    (its GND pad overlaps the GND pad of C124); the GND via of C124 (9.575, -61.8) -> 0.6 / 0.3 in its pad (9.05, -60.8),
    GND via (8.9, -58.23) removed (R70.1 stands there).
  * In3 window: BIAS / DAB_DIS / B12 corners chamfered round the Q19 pin-1 barrel (0.5 mm HV inner clearance).
  * In3 15V strip widened west from x 9.5 to 8.35 over y -60.6 .. -46.9 and to 7.4 over y -60.7 .. -57.7 (round the
    C124 GND via), because the moved pad rings eat its middle.
  * Commutation loop kept: C67 (19.7, -48.0) -> (18.55, -48.0), its DHB_CURRENT vias (22.6, -49 / -50) -> (21.45, ...),
    the In2 return (1.2 mm) and the In2 lanes C63 / 5V / Net-(C11-Pad1) east of the pins 1.15 mm west with the FETs,
    switch-node strip outline east edge 16.6 -> 15.45 south of the arm; C70 stays (B.Cu), its DC+ via (18.3, -48.5) ->
    (17.93, -48.5) in its pad, F.Cu -> B.Cu DC+ via (17.7, -50.0) -> (17.6, -49.5), (18.7, -50.0) removed (C67.2 moved next to them).
  * F.Cu zones S4B_DC+_F / S3A_DHB_HI_SOURCE_F / S3A_DHB_CURRENT_F west edges 11.8 -> 10.65, S4B_DC+_F east edge
    18.9 -> 18.2, S4B_DHB_CURRENT_F west edge 20.35 -> 19.2; rule area S14H_KO (DRV5) 0.85 mm west.
Record: kicad_next/routing/moves_s17b.json.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s14_common  # noqa: E402
from s14_common import r3  # noqa: E402

DX = -0.85       # DRV5 group
HS, HG, VA, QG = "DHB_HI_SOURCE", "DHB_HI_GATE", "Net-(DRV5-VDDA)", "Net-(Q19-G)"
LG, Q7G, DC, DI = "DHB_LOW_GATE", "Net-(Q7-G)", "DC+", "DHB_CURRENT"
BIAS, DAB, B12 = "+1V65_BIAS", "DAB_DIS", "B12"
C63, C11 = "Net-(C63-Pad1)", "Net-(C11-Pad1)"


def tracks(ed, net, layer, box):
    """track segments of NET on LAYER with both ends in box"""
    P = ed.P
    out = []
    for t in ed.b.GetTracks():
        if t.Type() != P.PCB_TRACE_T or t.GetNetname() != net or ed.b.GetLayerName(t.GetLayer()) != layer:
            continue
        s, e = ed.pt(t.GetStart()), ed.pt(t.GetEnd())
        if all(box[0] <= q[0] <= box[2] and box[1] <= q[1] <= box[3] for q in (s, e)):
            out.append(t)
    return out


def delete_in(ed, net, layer, box, n=None):
    ts = tracks(ed, net, layer, box)
    if n is not None and len(ts) != n:
        ed.fail(f"delete_in {net} {layer} {box}: {len(ts)} segments, expected {n}")
    for t in ts:
        ed.rec.append(dict(op="delete_track", net=net, layer=layer, start=list(r3(ed.pt(t.GetStart()))),
                           end=list(r3(ed.pt(t.GetEnd()))), width=round(ed.mm(t.GetWidth()), 4)))
        ed.b.Delete(t)


def set_outline_pts(ed, name, pts, why):
    z = ed.zone(name)
    if len(ed.outline(z)) != 1 or len(ed.outline(z)[0]) != 1:
        ed.fail(f"{name}: not a single plain outline")
    ed.set_outline(z, [[[list(p) for p in pts]]], why)


def shift_group(ed):
    """DRV5 group 0.85 mm west (rubber band: track ends in the box move, the far ends stay)"""
    P, b = ed.P, ed.b
    for ref in ("DRV5", "C95", "R127"):
        f = ed.footprint(ref)
        x, y = ed.pt(f.GetPosition())
        ed.move_footprint(ref, (round(x + DX, 4), round(y, 4)))
    ed.move_footprint("C94", (-4.9, -48.63))
    vias = [("15V", (6.6, -51.805)), ("GND", (8.25, -54.345)), ("5V", (9.68, -54.45)),
            ("PRI_DHB_HI", (-4.1, -45.455)), (B12, (-4.1, -46.725)), (DAB, (-4.1, -50.535))]
    moved = []
    for net, at in vias:
        new = (round(at[0] + DX, 4), at[1])
        ed.move_via(net, at, new)
        moved.append((net, r3(at)))
    keep = {r3(p) for p in [(-5.75, -49.405), (-5.0, -45.455), (-5.2, -46.725),
                            (4.3, -55.25), (4.33, -50.75)]}
    # C94 0.35 mm west, its pads 0.2 mm off the moved pins 3 / 4 (same nets, but no pad on pad)
    # the 5V link under the body: its In2 via (4.33, -50.75) stays (In2 control bus west of it); the vertical goes to
    # x 4.7, 0.35 mm off the moved pins 9 - 11 and 0.26 mm off the U1A+ via (4.3, -55.25)
    special = {r3((-4.55, -47.855)): (-4.9, -47.855), r3((-4.55, -49.405)): (-4.9, -49.405),
               r3((5.2, -51.62)): (4.7, -51.62), r3((5.2, -54.75)): (4.7, -54.75), r3((5.43, -54.98)): (4.93, -54.98)}
    box = (-6.0, -55.35, 9.75, -44.4)
    n = 0
    for t in list(b.GetTracks()):
        if t.Type() != P.PCB_TRACE_T:
            continue
        lay = b.GetLayerName(t.GetLayer())
        for get, put in ((t.GetStart, t.SetStart), (t.GetEnd, t.SetEnd)):
            q = r3(ed.pt(get()))
            if lay == "B.Cu":
                hit = box[0] <= q[0] <= box[2] and box[1] <= q[1] <= box[3] and q not in keep
            else:
                hit = (t.GetNetname(), q) in moved
            if hit:
                nq = special.get(q, (round(q[0] + DX, 4), q[1])) if lay == "B.Cu" else (round(q[0] + DX, 4), q[1])
                put(ed.v(nq))
                n += 1
                ed.rec.append(dict(op="move_track_end", net=t.GetNetname(), layer=lay, old=list(q), new=list(nq)))
    print(f"s17b: {n} track ends of the DRV5 group moved")


def edit(b, ed):
    for ref, at in (("Q19", (12.75, -46.98)), ("Q7", (12.75, -58.26)), ("DRV5", (2.3, -49.9))):
        if r3(ed.pt(ed.footprint(ref).GetPosition())) != at:
            ed.fail(f"{ref} not at {at}")

    # ---- 1. copper that is laid again (deleted before the group shift) ----
    delete_in(ed, HS, "B.Cu", (6.9, -52.2, 12.8, -47.9), 6)
    delete_in(ed, HS, "B.Cu", (12.7, -52.1, 15.55, -52.0), 1)          # R22.2 leg end at the old pad
    delete_in(ed, HG, "B.Cu", (6.9, -46.8, 12.1, -44.9), 6)
    delete_in(ed, VA, "B.Cu", (6.9, -45.5, 11.7, -42.1), 4)
    delete_in(ed, QG, "B.Cu", (10.8, -47.25, 13.25, -46.9), 2)
    delete_in(ed, LG, "B.Cu", (9.45, -55.65, 11.5, -53.65), 4)
    delete_in(ed, Q7G, "B.Cu", (10.2, -58.8, 14.65, -57.55), 3)
    delete_in(ed, "GND", "B.Cu", (9.5, -61.85, 10.25, -60.45), 2)
    delete_in(ed, "15V", "In3.Power", (6.5, -51.9, 10.4, -51.7), 1)
    ed.delete_via("GND", (9.575, -61.8))
    ed.add_via("GND", (9.05, -60.8), 0.6, 0.3)            # in the GND pad of C124 (R70.2 overlaps it), 1.25 mm off Q7.2
    # C118 (dead time) stands beside the NC pin 7: turned 90 deg next to R127, GND track round to the R127 GND pad (the 15V track x -6.75
    # west of it keeps 1.2 mm to D11 and cannot give way)
    delete_in(ed, "Net-(DRV5-DT)", "B.Cu", (-4.2, -53.15, -4.15, -51.75), 1)
    delete_in(ed, "GND", "B.Cu", (-5.85, -53.15, -5.8, -51.75), 1)
    ed.delete_via("GND", (8.9, -58.23))

    # ---- 2. DRV5 group 0.85 mm west ----
    shift_group(ed)
    z = ed.zone("S14H_KO DRV5 output side: no GND fill round NC pads 12 / 13, >= 1.5 mm from pad 14")
    ed.set_outline(z, [[[[4.4 + DX, -51.3], [9.6 + DX, -51.3], [9.6 + DX, -46.2], [4.4 + DX, -46.2]]]],
                   "with DRV5 0.85 mm west")

    # ---- 3. the FET column and the parts round it ----
    ed.move_footprint("Q19", (11.6, -46.98))
    ed.move_footprint("Q7", (11.6, -58.26))
    ed.move_footprint("C92", (8.38, -46.79))
    ed.move_footprint("R26", (10.05, -46.23))
    ed.move_footprint("R90", (10.0, -56.6))
    ed.move_footprint("R70", (9.6, -59.3))
    ed.move_footprint("C67", (18.55, -48.0))
    ed.move_footprint("C118", (-4.95, -53.3), 90)
    ed.add_track("Net-(DRV5-DT)", "B.Cu", (-5.025, -51.805), (-4.95, -52.475), 0.25)
    ed.add_path("GND", "B.Cu", [(-4.95, -54.125), (-5.9, -54.125), (-5.9, -52.6), (-6.4, -52.1)], 0.3)

    # high side, B.Cu only
    ed.add_track(HS, "B.Cu", (6.1, -47.995), (8.38, -48.365), 0.5)
    ed.add_path(HS, "B.Cu", [(8.38, -48.365), (9.2, -49.0), (9.2, -50.0), (9.45, -50.75), (10.044, -51.377),
                             (10.6, -52.06), (11.6, -52.06)], 0.3)
    ed.add_track(HS, "B.Cu", (15.5, -52.06), (11.6, -52.06), 0.3)
    ed.add_track(HG, "B.Cu", (6.1, -46.725), (7.4, -46.725), 0.4)
    ed.add_path(HG, "B.Cu", [(7.4, -46.725), (7.9, -46.23), (10.05, -46.23), (10.05, -45.23)], 0.25)
    ed.add_path(HG, "B.Cu", [(10.05, -45.23), (11.4, -45.69), (12.09, -45.69)], 0.25)
    ed.add_track(VA, "B.Cu", (6.1, -45.455), (8.38, -45.215), 0.4)
    ed.add_path(VA, "B.Cu", [(8.38, -45.215), (8.9, -44.8), (9.15, -44.25), (9.95, -44.25), (11.65, -42.55)], 0.25)
    ed.add_track(QG, "B.Cu", (10.05, -47.23), (11.6, -46.98), 0.4)
    ed.add_track(QG, "B.Cu", (11.6, -46.98), (13.2, -47.2), 0.3)

    # low side
    ed.add_track(LG, "B.Cu", (8.65, -53.72), (9.4, -53.72), 0.2)
    ed.add_path(LG, "B.Cu", [(9.4, -53.72), (10.0, -54.32), (10.0, -55.6), (11.45, -54.9)], 0.3)
    ed.add_track(Q7G, "B.Cu", (10.0, -57.6), (11.6, -58.26), 0.4)
    ed.add_track(Q7G, "B.Cu", (14.6, -58.3), (11.6, -58.26), 0.3)
    ed.add_track(Q7G, "B.Cu", (9.6, -58.475), (10.0, -57.6), 0.3)
    ed.add_track("15V", "In3.Power", (5.75, -51.805), (9.6, -51.805), 0.5)

    # ---- 4. In3 window: corners round the Q19.1 barrel ----
    delete_in(ed, BIAS, "In3.Power", (5.9, -46.6, 11.2, -44.2), 3)
    ed.add_path(BIAS, "In3.Power", [(11.13, -44.276), (11.13, -45.815), (10.445, -46.5), (6.0, -46.5)], 0.152)
    delete_in(ed, DAB, "In3.Power", (0.4, -46.2, 10.9, -43.6), 3)
    ed.add_path(DAB, "In3.Power", [(10.82, -43.634), (10.82, -45.695), (10.365, -46.15), (0.5, -46.15)], 0.152)
    delete_in(ed, B12, "In3.Power", (-3.1, -45.9, 10.6, -43.0), 3)
    ed.add_path(B12, "In3.Power", [(10.51, -43.025), (10.51, -45.575), (10.285, -45.8), (-3.0, -45.8)], 0.152)
    z = ed.zone("S2_In3_15V_1", "15V", "In3.Power")
    old = ed.outline(z)
    ps = z.Outline()
    s = ed.P.SHAPE_POLY_SET()
    s.NewOutline()
    for x, y in ((8.35, -60.6), (9.5, -60.6), (9.5, -46.9), (8.35, -46.9)):
        s.Append(ed.MM(x), ed.MM(y))
    ps.BooleanAdd(s)
    s = ed.P.SHAPE_POLY_SET()           # round the west of the GND via of C124 (9.05, -60.8) into the band y < -60.6
    s.NewOutline()
    for x, y in ((7.4, -60.7), (8.4, -60.7), (8.4, -57.7), (7.4, -57.7)):
        s.Append(ed.MM(x), ed.MM(y))
    ps.BooleanAdd(s)
    if ps.OutlineCount() != len(old):
        ed.fail("In3 15V: outline count changed")
    ed.rec.append(dict(op="zone_outline", zone="S2_In3_15V_1", net="15V", layer="In3.Power", add=[[8.35, -60.6, 9.5, -46.9], [7.4, -60.7, 8.4, -57.7]],
                       why="strip beside the moved Q19 / Q7 pad rings widened west"))

    # ---- 5. commutation loop: C67, its vias, the In2 return and the In2 lanes east of the pins ----
    delete_in(ed, DC, "B.Cu", (18.2, -48.55, 18.35, -47.95), 1)
    ed.move_via(DC, (18.3, -48.5), (17.93, -48.5))          # in the C70.1 pad, 1.22 mm off the moved C67.2
    # F.Cu S4B_DC+_F -> B.Cu feed of C47: (17.7, -50.0) -> (17.6, -49.5); (18.7, -50.0) removed (0.7 mm from the moved C67.2)
    ed.move_via(DC, (17.7, -50.0), (17.6, -49.5))
    ed.delete_via(DC, (18.7, -50.0))
    delete_in(ed, DI, "B.Cu", (21.1, -49.05, 22.65, -47.95), 2)
    ed.move_via(DI, (22.6, -49.0), (21.45, -49.0))
    ed.move_via(DI, (22.6, -50.0), (21.45, -50.0))
    ed.add_track(DI, "B.Cu", (21.175, -48.0), (21.45, -49.0), 0.8)
    delete_in(ed, DI, "In2.Signal_HV", (12.7, -63.4, 22.65, -48.95), 7)
    ed.add_path(DI, "In2.Signal_HV", [(11.6, -63.34), (13.15, -63.34), (14.35, -62.14), (16.25, -62.14), (16.25, -52.3),
                                      (20.05, -52.3), (21.45, -50.9), (21.45, -49.0)], 1.2)
    delete_in(ed, C63, "In2.Signal_HV", (7.0, -53.8, 14.75, -46.85), 4)
    ed.add_path(C63, "In2.Signal_HV", [(14.7, -46.9), (13.5, -48.1), (13.5, -53.3), (13.05, -53.75), (7.1, -53.75)], 0.203)
    delete_in(ed, "5V", "In2.Signal_HV", (9.9, -54.25, 15.2, -47.15), 3)
    ed.add_path("5V", "In2.Signal_HV", [(15.118, -47.2), (13.968, -48.35), (13.968, -53.8), (13.568, -54.2), (9.93, -54.2)],
                0.305)
    delete_in(ed, C11, "In2.Signal_HV", (8.3, -55.6, 16.45, -47.85), 4)
    ed.add_path(C11, "In2.Signal_HV", [(16.4, -47.9), (14.65, -49.65), (14.65, -55.05), (14.15, -55.55), (8.35, -55.55)], 0.2)

    # ---- 6. F.Cu zones ----
    set_outline_pts(ed, "S4B_DC+_F", [(10.65, -50.45), (18.2, -50.45), (18.2, -44.6), (12.85, -44.6), (12.85, -48.6),
                                      (10.65, -48.6)], "with the Q19 pins and C67 1.15 mm west")
    set_outline_pts(ed, "S4B_DHB_CURRENT_F", [(19.2, -50.6), (25.75, -50.6), (25.75, -49.3), (28.2, -49.3), (28.2, -46.1),
                                              (24.0, -46.1), (24.0, -46.5), (19.2, -46.5)], "C67.2 1.15 mm west")
    set_outline_pts(ed, "S3A_DHB_HI_SOURCE_F", [(10.65, -61.75), (15.45, -61.75), (15.45, -57.6), (27.9, -57.6),
                                                (27.9, -58.0), (31.0, -58.0), (31.0, -50.6), (27.9, -50.6), (27.9, -52.0),
                                                (15.45, -52.0), (15.45, -51.65), (10.65, -51.65)],
                    "strip between the pins and the arm 1.15 mm west with the FETs")
    set_outline_pts(ed, "S3A_DHB_CURRENT_F", [(10.65, -64.15), (25.75, -64.15), (25.75, -59.2), (17.9, -59.2),
                                              (17.9, -62.95), (10.65, -62.95)], "Q7.3 1.15 mm west")


if __name__ == "__main__":
    sys.exit(s14_common.main("s17b", __file__, edit, sys.argv[1:]))
