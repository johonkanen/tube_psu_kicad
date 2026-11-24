#!/usr/bin/env python3
"""Stage 16a (one-shot, not re-runnable; run with tools/p2k/bin/kipy): SICD1 / SICD2 lead assignment (finding 13 F1).

    tools/p2k/bin/kipy tools/next/route_s16a_sicd_ka.py [--dry-run OUT.kicad_pcb]

Design review 2026-11-24, finding 13 F1 (blocker): Wolfspeed C3D02060A pin 1 = cathode, pin 2 = anode, case / tab =
cathode (data sheet Rev. 10, Oct 2024, p 6). tube_psu:TO-220-2_Vertical_AK named the pin-1 pad "A". Stage 4k turned
both diodes by 180 deg so that their outlines face the heatsink plate and kept the nets on the pad NAMES, so a diode
clamped tab-to-plate had its cathode on the PFC drain and its anode on DC+ (DC+ shorted through diode and FET when
Q5 / Q6 turn on).
  * Both diodes get tube_psu_next_parts:TO-220-2_Vertical_KA (same position / rotation; pin-1 pad, rect, named K;
    pin-2 pad named A). The pad sites keep their places; their nets swap:
      SICD1 (11.8, -21.4) south site: PFC_DRAIN_1 -> DC+;   (11.8, -26.48) north site: DC+ -> PFC_DRAIN_1
      SICD2 (3.09, -3.82) north site: PFC_DRAIN_2 -> DC+;   (3.09, 1.26) south site: DC+ -> PFC_DRAIN_2
  * SICD1 copper (as 5.1: drain north, cathode south between the DC+ island and the trunk):
      DC+ pour 29 gives up x 5.5..14.0, y -30.0..-23.0 (the old cathode lobe) and takes x 8.6..14.5, y -23.0..-18.6
      and x 7.4..9.6, y -20.0..-16.9 (the old anode lobe and the strip west of it: island C73.1 / DB1.2 / SICD2.K
      and the trunk now meet across the cathode pad);
      PFC_DRAIN_1 pour 10 gives up x 6.3..14.0, y -23.4..-19.0 and takes x 6.9..13.6, y -28.8..-23.4 (Q5.2 -> SICD1.A);
      B.Cu 2.0 mm DC+ link of stage 14c re-ended: island (10.2, -17.8) -> (11.8, -19.4) -> SICD1.K (11.8, -21.4)
      instead of the column x 8.4 to the old cathode site (which is the anode now).
  * SICD2 copper: DC+ pour 29 takes x 1.9..5.6, y -6.3..-1.8 (round the new cathode site, joined to the DB1 / C73
      peninsula) and gives up x 1.5..8.5, y -1.5..3.2 (the old cathode field); PFC_DRAIN_2 pour 1 gives up
      x -5..5, y -6..-0.7 and takes x 0.5..4.6, y -0.7..3.0 (L1.1 and SICD2.A in one pour);
      B.Cu PFC_DRAIN_2: L1.1 -> SICD2.A (3.09, 1.26) 2.4 mm, SICD2.A -> (4.4, 1.26) -> (8.1, -2.436) -> Q6.2 2.4 mm
      (replaces L1.1 -> (-0.3, 2.5) -> (-0.3, -1.6) -> old anode site 2.0 mm and old anode site -> Q6.2 2.4 mm).
  The zone fills keep their clearances (DC+ priority 55 above the drains 36 / 27). Outer layers only.
Record: kicad_next/routing/moves_s16a.json.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s14_common  # noqa: E402
import s15_common as S  # noqa: E402

DC = "DC+"
D1 = "/05 PFC/PFC_DRAIN_1"
D2 = "/05 PFC/PFC_DRAIN_2"


def replace_renamed(ed, ref):
    """S.replace_footprint for a footprint whose pad SITES stay but whose pad NAMES move between the sites"""
    import reuse_51_board as R
    P, b = ed.P, ed.b
    old = ed.footprint(ref)
    comps, pins, _ = S.netlist()
    c = comps[ref]
    new = R.load_fp(c["fpid"])
    b.Add(new)
    pos = old.GetPosition()
    new.SetPosition(pos)
    if old.IsFlipped():
        new.Flip(pos, P.FLIP_DIRECTION_LEFT_RIGHT)
    new.SetOrientation(old.GetOrientation())
    new.SetReference(ref)
    for src, dst in ((old.Reference(), new.Reference()), (old.Value(), new.Value())):
        dst.SetPosition(src.GetPosition())
        dst.SetTextAngle(src.GetTextAngle())
        dst.SetVisible(src.IsVisible())
        dst.SetLayer(src.GetLayer())
    new.SetValue(c["value"])
    new.SetLocked(old.IsLocked())
    new.SetPath(P.KIID_PATH(c["path"]))
    if hasattr(new, "SetSheetname"):
        new.SetSheetname(c["sheet"])
        new.SetSheetfile(c["sheetfile"])
    new.SetField("LCSC", c["lcsc"])
    new.GetField("LCSC").SetVisible(False)
    new.SetField("Description", c["descr"])
    new.GetField("Description").SetVisible(False)
    sites_old = {s14_common.r3(ed.pt(p.GetPosition())): (p.GetNumber(), p.GetNetname()) for p in old.Pads()}
    sites = {}
    for p in new.Pads():
        n = pins.get(ref, {}).get(p.GetNumber(), "")
        p.SetNet(b.FindNet(n))
        q = s14_common.r3(ed.pt(p.GetPosition()))
        if q not in sites_old:
            ed.fail(f"{ref}.{p.GetNumber()} at {q}: not an old pad site")
        sites[q] = dict(old=sites_old[q], new=(p.GetNumber(), n))
    if len(sites) != len(sites_old):
        ed.fail(f"{ref}: pad sites differ")
    ed.rec.append(dict(op="replace_footprint_renamed", ref=ref, old=old.GetFPIDAsString(), new=c["fpid"],
                       at=ed.pt(pos), rot=old.GetOrientationDegrees(),
                       sites=[dict(at=list(k), **v) for k, v in sites.items()]))
    b.Delete(old)
    return new


def zone_bool(ed, z, subs, adds, why):
    """subtract / add axis-parallel boxes (x0, y0, x1, y1) to a zone outline, edited in place"""
    P = ed.P
    old = ed.outline(z)
    ps = z.Outline()

    def box(bx):
        s = P.SHAPE_POLY_SET()
        s.NewOutline()
        for x, y in ((bx[0], bx[1]), (bx[2], bx[1]), (bx[2], bx[3]), (bx[0], bx[3])):
            s.Append(ed.MM(x), ed.MM(y))
        return s
    for bx in subs:
        ps.BooleanSubtract(box(bx))
    for bx in adds:
        ps.BooleanAdd(box(bx))
    if ps.OutlineCount() != len(old):
        ed.fail(f"{z.GetZoneName()}: {len(old)} -> {ps.OutlineCount()} outlines")
    ed.rec.append(dict(op="zone_outline", zone=z.GetZoneName(), net=z.GetNetname(),
                       layer=ed.b.GetLayerName(z.GetLayer()), old=old, new=ed.outline(z), subtract=subs, add=adds,
                       why=why))


def edit(b, ed):
    replace_renamed(ed, "SICD1")
    replace_renamed(ed, "SICD2")
    zdc = ed.zone("Proteus F.Cu pour 29", DC, "F.Cu")
    zone_bool(ed, zdc, [(5.5, -30.0, 14.0, -23.0), (1.5, -1.5, 8.5, 3.2)],
              [(8.6, -23.0, 14.5, -18.6), (7.4, -20.0, 9.6, -16.9), (1.9, -6.3, 5.6, -1.8)],
              "SICD1: cathode now on the south site (island <-> trunk across it), anode site north left to the drain; "
              "SICD2: cathode now on the north site (joined to the DB1 / C73 peninsula), old cathode field left")
    zone_bool(ed, ed.zone("Proteus F.Cu pour 10", D1, "F.Cu"), [(6.3, -23.4, 14.0, -19.0)],
              [(6.9, -28.8, 13.6, -23.4)], "Q5.2 -> SICD1.A on the north site")
    zone_bool(ed, ed.zone("Proteus F.Cu pour 1", D2, "F.Cu"), [(-5.0, -6.0, 5.0, -0.7)],
              [(0.5, -0.7, 4.6, 3.0)], "L1.1 and SICD2.A (south site) in one pour")
    # SICD1: B.Cu DC+ 2.0 mm link of stage 14c to the new cathode site
    ed.delete_track(DC, "B.Cu", (10.2, -17.8), (8.4, -19.6), 2.0)
    ed.delete_track(DC, "B.Cu", (8.4, -19.6), (8.4, -26.48), 2.0)
    ed.delete_track(DC, "B.Cu", (8.4, -26.48), (11.8, -26.48), 2.0)
    ed.add_path(DC, "B.Cu", [(10.2, -17.8), (11.8, -19.4), (11.8, -21.4)], 2.0)
    # SICD2: B.Cu PFC_DRAIN_2 to the new anode site
    ed.delete_track(D2, "B.Cu", (-0.102, 3.342), (-0.3, 2.5), 2.0)
    ed.delete_track(D2, "B.Cu", (-0.3, 2.5), (-0.3, -1.6), 2.0)
    ed.delete_track(D2, "B.Cu", (-0.3, -1.6), (1.9, -3.82), 2.0)
    ed.delete_track(D2, "B.Cu", (1.9, -3.82), (3.09, -3.82), 2.0)
    ed.delete_track(D2, "B.Cu", (3.09, -3.82), (4.6, -2.436), 2.4)
    ed.delete_track(D2, "B.Cu", (4.6, -2.436), (11.389, -2.436), 2.4)
    ed.add_track(D2, "B.Cu", (-0.102, 3.342), (3.09, 1.26), 2.4)
    ed.add_path(D2, "B.Cu", [(3.09, 1.26), (4.4, 1.26), (8.1, -2.436), (11.389, -2.436)], 2.4)


if __name__ == "__main__":
    sys.exit(s14_common.main("s16a", __file__, edit, sys.argv[1:]))
