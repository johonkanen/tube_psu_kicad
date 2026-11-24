#!/usr/bin/env python3
"""Helpers of the stage-15 one-shot scripts (tools/next/route_s15*.py; owner decisions 2026-11-24).

The frame is s14_common (board copy in a temporary directory, refill with kicad-cli, --dry-run OUT, record in
kicad_next/routing/moves_<TAG>.json). Stage 15 adds new parts to the board, which s14_common's Editor cannot do:
    add_footprint(ed, ref, pos, rot, back=True)
loads the library footprint the schematic names for REF (kicad-cli netlist of kicad_next/tube_psu_5_2.kicad_sch),
places it, takes value / LCSC / description / symbol path / sheet from the netlist and gives every pad its net
(the same fields tools/next/update_board_parts.py keeps in step), and records the operation;
    remove_footprint(ed, ref)
deletes a board footprint (its copper is the caller's business).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

_NET = None


def netlist():
    global _NET
    if _NET is None:
        import reuse_51_board as R
        _NET = R.netlist()
    return _NET


def add_footprint(ed, ref, pos, rot, back=True):
    import reuse_51_board as R
    P, b = ed.P, ed.b
    if b.FindFootprintByReference(ref) is not None:
        ed.fail(f"{ref} is already on the board")
    comps, pins, _ = netlist()
    if ref not in comps:
        ed.fail(f"{ref} is not in the schematic")
    c = comps[ref]
    fp = R.load_fp(c["fpid"])
    b.Add(fp)                                      # on the board before Flip (pcbnew 10)
    fp.SetReference(ref)
    fp.SetValue(c["value"])
    fp.SetPosition(ed.v(pos))
    if back:
        fp.Flip(ed.v(pos), P.FLIP_DIRECTION_LEFT_RIGHT)
    fp.SetOrientationDegrees(rot)
    fp.SetPath(P.KIID_PATH(c["path"]))
    if hasattr(fp, "SetSheetname"):
        fp.SetSheetname(c["sheet"])
        fp.SetSheetfile(c["sheetfile"])
    fp.SetField("LCSC", c["lcsc"])
    fp.GetField("LCSC").SetVisible(False)
    fp.SetField("Description", c["descr"])
    fp.GetField("Description").SetVisible(False)
    for p in fp.Pads():
        n = pins.get(ref, {}).get(p.GetNumber(), "")
        ni = b.FindNet(n) if n else None
        if n and ni is None:
            ed.fail(f"{ref}.{p.GetNumber()}: net {n} not on the board")
        if ni is not None:
            p.SetNet(ni)
    pads = {p.GetNumber(): [round(x, 3) for x in ed.pt(p.GetPosition())] for p in fp.Pads()}
    ed.rec.append(dict(op="add_footprint", ref=ref, fpid=c["fpid"], at=pos, rot=rot, side="B" if back else "F",
                       value=c["value"], pads=pads))
    return fp


def remove_footprint(ed, ref):
    fp = ed.footprint(ref)
    ed.rec.append(dict(op="remove_footprint", ref=ref, fpid=fp.GetFPIDAsString(), at=ed.pt(fp.GetPosition()),
                       rot=fp.GetOrientationDegrees(), side="B" if fp.IsFlipped() else "F"))
    ed.b.Delete(fp)


def pad_xy(ed, ref, num):
    f = ed.footprint(ref)
    p = [q for q in f.Pads() if q.GetNumber() == num][0]
    return tuple(round(x, 4) for x in ed.pt(p.GetPosition()))


def delete_tracks_in(ed, net, layer, box):
    """delete every track of NET on LAYER with both ends inside box = (x0, y0, x1, y1); returns the count"""
    P = ed.P
    n = 0
    for t in list(ed.b.GetTracks()):
        if t.Type() != P.PCB_TRACE_T or t.GetNetname() != net or ed.b.GetLayerName(t.GetLayer()) != layer:
            continue
        s, e = ed.pt(t.GetStart()), ed.pt(t.GetEnd())
        if all(box[0] <= q[0] <= box[2] and box[1] <= q[1] <= box[3] for q in (s, e)):
            ed.rec.append(dict(op="delete_track", net=net, layer=layer, start=list(map(lambda v: round(v, 4), s)),
                               end=list(map(lambda v: round(v, 4), e)), width=ed.mm(t.GetWidth())))
            ed.b.Delete(t)
            n += 1
    return n


def sync_fields(ed, ref):
    """value / LCSC / description of a board footprint from the schematic netlist (as update_board_parts.py)"""
    comps, _, _ = netlist()
    c, fp = comps[ref], ed.footprint(ref)
    old = fp.GetValue()
    fp.SetValue(c["value"])
    fp.SetField("LCSC", c["lcsc"])
    fp.GetField("LCSC").SetVisible(False)
    fp.SetField("Description", c["descr"])
    fp.GetField("Description").SetVisible(False)
    ed.rec.append(dict(op="fields", ref=ref, old_value=old, value=c["value"], lcsc=c["lcsc"]))
