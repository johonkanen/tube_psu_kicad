#!/usr/bin/env python3
"""Read-only dump of a KiCad board to JSON for the review helper bq.py.

Run with the KiCad python (never saves the board):

    tools/p2k/bin/kipy kicad_next/review/tools/board_dump.py [BOARD.kicad_pcb] OUT.json

Default board: kicad_next/tube_psu_5_2.kicad_pcb. For the 5.1 reference board pass
kicad/tube_psu.kicad_pcb. Takes a few seconds and about 300 MB of RAM. All lengths in mm,
board coordinates as in the PCB editor (x to the right, y DOWN; this board has negative y).

JSON content:
  layers      copper layer names in stack order
  outline     bounding box of Edge.Cuts [x0, y0, x1, y1]
  footprints  ref, value, fp (library id), x, y, rot, side (F/B), bbox (courtyard or body),
              pads: num, net, x, y, shape size (w, h), drill (0 = SMD), layers (copper layers with a pad
              shape), barrel_only (layers where the unconnected pad ring is removed - "remove_unused_layers" -
              so only the plated hole wall is there), poly (pad outline on its first copper layer)
  tracks      net, layer, w, x1, y1, x2, y2 (arcs are stored as chords with "arc": true and mid point)
  vias        net, x, y, d (pad diameter), drill, layers [top, bottom], barrel_only (as for pads)
  zones       net, name, layer, prio, polys = filled copper as list of [outer, hole, hole, ...] rings
  edge        Edge.Cuts segments / circles (slots and outline), as polylines
  holes       every drilled hole (pads and vias): x, y, d, plated, ref
  netclass    net -> net class name (isolation domain class)
"""
import json
import sys

import pcbnew

MM = 1e-6


def ring(chain):
    return [[round(chain.CPoint(i).x * MM, 4), round(chain.CPoint(i).y * MM, 4)] for i in range(chain.PointCount())]


def polys(ps, unfracture=False):
    if unfracture:
        # KiCad stores zone fills "fractured" (holes joined to the outline by slits); undo on a copy
        ps = pcbnew.SHAPE_POLY_SET(ps)
        ps.Unfracture()
    out = []
    for i in range(ps.OutlineCount()):
        rings = [ring(ps.Outline(i))]
        for h in range(ps.HoleCount(i)):
            rings.append(ring(ps.Hole(i, h)))
        out.append(rings)
    return out


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    board_path = "kicad_next/tube_psu_5_2.kicad_pcb" if len(args) == 1 else args[0]
    out_path = args[-1]
    b = pcbnew.LoadBoard(board_path)
    cu = [l for l in b.GetEnabledLayers().CuStack()]
    lname = {l: b.GetLayerName(l) for l in cu}
    d = {"board": board_path, "layers": [lname[l] for l in cu]}
    bb = b.GetBoardEdgesBoundingBox()
    d["outline"] = [round(v * MM, 3) for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())]

    fps, holes = [], []
    for fp in b.GetFootprints():
        ref = fp.GetReference()
        try:
            cy = fp.GetCourtyard(pcbnew.F_CrtYd if fp.GetLayer() == pcbnew.F_Cu else pcbnew.B_CrtYd)
            cb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False)
        except Exception:
            cb = fp.GetBoundingBox(False)
        pads = []
        for p in fp.Pads():
            pl = [lname[l] for l in cu if p.IsOnLayer(l) and p.FlashLayer(l)]
            bare = [lname[l] for l in cu if p.IsOnLayer(l) and not p.FlashLayer(l)]
            first = next((l for l in cu if p.IsOnLayer(l)), None)
            poly = []
            if first is not None:
                ps = pcbnew.SHAPE_POLY_SET()
                p.TransformShapeToPolygon(ps, first, 0, 5000, pcbnew.ERROR_INSIDE)
                if ps.OutlineCount():
                    poly = ring(ps.Outline(0))
            pos = p.GetPosition()
            sz = p.GetSize(first if first is not None else pcbnew.F_Cu)
            dr = p.GetDrillSize()
            pads.append({"num": p.GetNumber(), "net": p.GetNetname(), "x": round(pos.x * MM, 4), "y": round(pos.y * MM, 4),
                         "w": round(sz.x * MM, 3), "h": round(sz.y * MM, 3), "drill": round(max(dr.x, dr.y) * MM, 3),
                         "drill2": round(min(dr.x, dr.y) * MM, 3), "layers": pl, "barrel_only": bare, "poly": poly,
                         "plated": p.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH})
            if dr.x > 0:
                holes.append({"x": pads[-1]["x"], "y": pads[-1]["y"], "d": pads[-1]["drill"], "d2": pads[-1]["drill2"],
                              "plated": pads[-1]["plated"], "ref": ref + "." + p.GetNumber(), "net": p.GetNetname()})
        pos = fp.GetPosition()
        fps.append({"ref": ref, "value": fp.GetValue(), "fp": fp.GetFPID().GetUniStringLibId(),
                    "x": round(pos.x * MM, 4), "y": round(pos.y * MM, 4), "rot": fp.GetOrientationDegrees(),
                    "side": "F" if fp.GetLayer() == pcbnew.F_Cu else "B",
                    "bbox": [round(v * MM, 3) for v in (cb.GetLeft(), cb.GetTop(), cb.GetRight(), cb.GetBottom())],
                    "dnp": bool(fp.IsDNP()), "pads": pads})
    d["footprints"] = fps

    tracks, vias = [], []
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            pos = t.GetPosition()
            vias.append({"net": t.GetNetname(), "x": round(pos.x * MM, 4), "y": round(pos.y * MM, 4),
                         "d": round(t.GetWidth(pcbnew.F_Cu) * MM, 3), "drill": round(t.GetDrillValue() * MM, 3),
                         "layers": [b.GetLayerName(t.TopLayer()), b.GetLayerName(t.BottomLayer())],
                         "barrel_only": [lname[l] for l in cu if t.IsOnLayer(l) and not t.FlashLayer(l)]})
            holes.append({"x": vias[-1]["x"], "y": vias[-1]["y"], "d": vias[-1]["drill"], "d2": vias[-1]["drill"],
                          "plated": True, "ref": "via", "net": t.GetNetname()})
        else:
            s, e = t.GetStart(), t.GetEnd()
            rec = {"net": t.GetNetname(), "layer": b.GetLayerName(t.GetLayer()), "w": round(t.GetWidth() * MM, 4),
                   "x1": round(s.x * MM, 4), "y1": round(s.y * MM, 4), "x2": round(e.x * MM, 4), "y2": round(e.y * MM, 4),
                   "len": round(t.GetLength() * MM, 4)}
            if t.Type() == pcbnew.PCB_ARC_T:
                m = t.GetMid()
                rec["arc"] = True
                rec["xm"], rec["ym"] = round(m.x * MM, 4), round(m.y * MM, 4)
            tracks.append(rec)
    d["tracks"], d["vias"], d["holes"] = tracks, vias, holes

    zones = []
    for z in b.Zones():
        for l in cu:
            if not z.IsOnLayer(l):
                continue
            rec = {"net": z.GetNetname(), "name": z.GetZoneName(), "layer": lname[l], "prio": z.GetAssignedPriority(),
                   "keepout": bool(z.GetIsRuleArea()), "polys": [] if z.GetIsRuleArea() else polys(z.GetFilledPolysList(l), True),
                   "outline": polys(z.Outline())}
            zones.append(rec)
    d["zones"] = zones

    edge = []
    for dr in list(b.GetDrawings()) + [g for fp in b.GetFootprints() for g in fp.GraphicalItems()]:
        if dr.GetLayer() != pcbnew.Edge_Cuts or not hasattr(dr, "GetShape"):
            continue
        ps = pcbnew.SHAPE_POLY_SET()
        if dr.GetShape() == pcbnew.SHAPE_T_POLY:
            ps = dr.GetPolyShape()
        else:
            dr.TransformShapeToPolygon(ps, pcbnew.Edge_Cuts, 0, 5000, pcbnew.ERROR_INSIDE, True)
        s, e = dr.GetStart(), dr.GetEnd()
        edge.append({"shape": dr.SHAPE_T_asString(), "x1": round(s.x * MM, 4), "y1": round(s.y * MM, 4),
                     "x2": round(e.x * MM, 4), "y2": round(e.y * MM, 4), "w": round(dr.GetWidth() * MM, 3),
                     "poly": ring(ps.Outline(0)) if ps.OutlineCount() else []})
    d["edge"] = edge

    nc = {}
    for code, net in b.GetNetsByNetcode().items():
        if code:
            nc[net.GetNetname()] = net.GetNetClassName()
    d["netclass"] = nc
    json.dump(d, open(out_path, "w"))
    print(f"{board_path}: {len(fps)} footprints, {len(tracks)} track segments, {len(vias)} vias, {len(zones)} zone layers, "
          f"{len(edge)} edge items, layers {d['layers']} -> {out_path}")


if __name__ == "__main__":
    main()
