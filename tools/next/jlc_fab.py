#!/usr/bin/env python3
"""JLCPCB fabrication + assembly file set of the tube_power 5.2 board (system python3 + shapely).

    python3 tools/next/jlc_fab.py            write kicad_next/fab/ (Gerbers, drill files, zip, BOM, CPL, notes)
    python3 tools/next/jlc_fab.py --check    regenerate into a temporary directory and fail unless kicad_next/fab/
                                             has the same content (the dates KiCad embeds are ignored)

Reads kicad_next/tube_psu_5_2.kicad_pcb and lib/jlc_parts_next.csv, never writes them: the Gerbers and drill
files come from tools/p2k/bin/kicad-cli (which does not save the board), the measurements from a read-only
pcbnew dump (tools/p2k/bin/kipy, LoadBoard only). Zones are plotted as stored in the board (no --check-zones:
that would refill in memory and plot something the checks of check_next.sh have not seen).

Plot options (JLC "How to generate Gerber and drill files in KiCad 8", read 2026-11-23): Gerber RS-274X with
Protel filename extensions, 4.6 mm, absolute origin (the board has no aux origin), vias tented (board setup),
X2 attributes left on (the guide does not ask to turn them off; they also carry the pad / net names the frame
check below uses). Drill: Excellon, PTH and NPTH in separate files, absolute origin, millimetres, decimal
format, oval holes in "alternate" mode, PDF drill maps. **No silkscreen layers**: the board is ordered without
silkscreen (the guide's F.Silkscreen / B.Silkscreen and "subtract soldermask from silkscreen" do not apply).

Assembly files follow the 5.1 tool tools/jlc_bom.py (same BOM / CPL columns, same coordinate frame: X = KiCad x,
Y = -KiCad y = the Gerber frame, footprint anchors = what `kicad-cli pcb export pos` writes). Rotation (stage 18c,
findings 14 F1): top side (KiCad orientation + correction) mod 360, bottom side (180 - KiCad orientation +
correction) mod 360 - the bottom-side rule and the corrections are those of the two common KiCad -> JLC tools
(kicad-jlcpcb-tools fabrication.py and JLCKicadTools cpl_fix_rotations.py, "Around 2022 July" note; both read
2026-11-24), NOT verified in JLC's placement preview. ROTATION_FIX holds the per-footprint corrections with
their source and confidence; ROTATION_CHECK.md lists every polarised / multi-pin part with the position its pin 1 /
cathode must have in the preview, to be ticked off there before paying.

Also written (stage 18c, findings 14 F4 F5 F7 F8): assembly drawings (F.Fab / B.Fab + outline, pads sketched,
refdes, bottom mirrored) as PDF, HAND_ASSEMBLY.md (every part JLC does not place, in soldering order),
ORDER_REMARK.md (ready-to-paste remarks for the PCB and the PCBA order), ROTATION_CHECK.md.

Checks made while generating (any failure -> exit status 1, nothing is hidden in the README):
  * every Gerber has the expected X2 file function, draws something and stays inside the board outline
  * the outline Gerber holds the board rectangle and every internal slot of the board
  * drill hits = vias + plated pad holes of the board; the NPTH file = the mounting holes H*
  * every board footprint is either in lib/jlc_parts_next.csv or board-only (H*, WP*), values / footprints agree
  * CPL frame = Gerber frame: pad flashes of the copper Gerbers against the CPL position of two-pad chip parts,
    plated-hole positions of the drill file against the board pads
"""
import collections
import csv
import fnmatch
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
NAME = "tube_psu_5_2"
PCB = os.path.join(ROOT, "kicad_next", NAME + ".kicad_pcb")
LOCK = os.path.join(ROOT, "kicad_next", "~" + NAME + ".kicad_pcb.lck")
PARTS = os.path.join(ROOT, "lib", "jlc_parts_next.csv")
OUT = os.path.join(ROOT, "kicad_next", "fab")
CLI = os.path.join(ROOT, "tools", "p2k", "bin", "kicad-cli")
KIPY = os.path.join(ROOT, "tools", "p2k", "bin", "kipy")

# canonical KiCad layer, Protel extension, X2 file function (the board's user names In1.GND ... only show in the file names)
LAYERS = [("F.Cu", "gtl", "Copper,L1,Top"), ("In1.Cu", "g1", "Copper,L2,Inr"), ("In2.Cu", "g2", "Copper,L3,Inr"),
          ("In3.Cu", "g3", "Copper,L4,Inr"), ("In4.Cu", "g4", "Copper,L5,Inr"), ("B.Cu", "gbl", "Copper,L6,Bot"),
          ("F.Mask", "gts", "Soldermask,Top"), ("B.Mask", "gbs", "Soldermask,Bot"),
          ("F.Paste", "gtp", "Paste,Top"), ("B.Paste", "gbp", "Paste,Bot"), ("Edge.Cuts", "gm1", "Profile,NP")]
ZIP = NAME + "_gerbers.zip"
BOM = NAME + "_bom.csv"
CPL = NAME + "_cpl.csv"
ASM_TOP = NAME + "-assembly_top.pdf"
ASM_BOT = NAME + "-assembly_bottom.pdf"
OWNED = ("README.md", "NOT_ASSEMBLED.md", "ROTATION_CHECK.md", "HAND_ASSEMBLY.md", "ORDER_REMARK.md")
MOUNT = re.compile(r"^H\d+$")
MOUNT_DRILL = 3.0

# JLC limits (kicad_next/README.md "JLC manufacturing limits", multilayer 1 oz; slot widths from
# jlcpcb.com/capabilities/pcb-capabilities read 2026-11-23)
JLC = {"track": 0.09, "space": 0.09, "via_drill": 0.15, "via_dia": 0.25, "drill": 0.15, "annular": 0.15,
       "annular_rec": 0.20, "npth": 0.50, "npth_ring": 0.45, "slot": 1.0, "edge": 0.20}

# Per-footprint rotation correction for JLC's part models (stage 18c). fnmatch pattern on the footprint name without
# the library prefix -> (degrees, source, confidence). First match wins. Source "table" = the "cpl_rotations_db.csv"
# of JLCKicadTools (github.com/matthewlai/JLCKicadTools, master, read 2026-11-24; kicad-jlcpcb-tools downloads the
# same table as its default corrections), "geometry" = not in that table, the correction of the table entry with the
# same KiCad pad geometry / pin-1 corner is used. NOTHING here has been seen in JLC's placement preview.
ROTATION_FIX = [
    ("SOT-23_Proteus", 270, "table ^SOT-23 (-90); pad geometry = KiCad SOT-23 (pads at -x / single pad +x), "
                            "JEDEC pin 1 = Proteus pad 2", "medium"),
    ("SOT-23*", 270, "table ^SOT-23 (-90); the _Proteus 5 / 6-pin footprints have KiCad's pad numbering and geometry",
     "medium"),
    ("SOIC-*", 270, "table ^SOIC- (270); the slotted SOIC-16W variants keep KiCad's SOIC-16W pads", "medium"),
    ("TSSOP-*", 270, "table ^TSSOP- (270)", "medium"),
    ("VSSOP-8_3x3mm_P0.65mm", 270, "table ^VSSOP-8_3.0x3.0mm_P0.65mm (270; KiCad's older name of the same footprint, "
                                   "not the generic ^VSSOP-8_ 180)", "medium"),
    ("PG-DSO-12_*", 270, "geometry: not in the table; pads as KiCad SOIC (columns at x -/+2.475, pin 1 top left) -> "
                         "the SOIC correction", "low"),
    ("CP_Elec_6.3x7.7*", 180, "table ^CP_Elec_6.3x7.7 (180)", "medium"),
    ("CP_Elec_5x5.4", 180, "geometry: not in the table; every CP_Elec size in the table (6.3x7.7, 8x5.4, 8x6.7, 8x10, "
                           "8x10.5, 10x10) has 180", "low"),
]


def rotation_fix(footprint):
    """(degrees, ROTATION_FIX entry or None) for a footprint id."""
    name = footprint.split(":", 1)[-1]
    for entry in ROTATION_FIX:
        if fnmatch.fnmatch(name, entry[0]):
            return entry[1], entry
    return 0, None


def cpl_rotation(rot, bottom, fix):
    """CPL rotation: top (rot + fix), bottom (180 - rot + fix), mod 360 (see the module docstring)."""
    return (((180 - rot) if bottom else rot) + fix) % 360


def compass(dx, dy):
    """8-point direction of a vector in the Gerber frame (y = north)."""
    v = math.hypot(dx, dy)
    if v < 1e-6:
        return "centre"
    ns = "north" if dy > 0.38 * v else "south" if dy < -0.38 * v else ""
    ew = "east" if dx > 0.38 * v else "west" if dx < -0.38 * v else ""
    return "-".join(s for s in (ns, ew) if s)


def polarity_pad(name, pads):
    """(what, pad number) of the pad that marks the orientation of a footprint: pin 1, cathode, +, gate."""
    nums = {p["num"] for p in pads}
    if name == "SOT-23_Proteus":
        return "pin 1 (JEDEC; Proteus pad 2)", "2"
    if name.startswith("D_") and "C" in nums:
        return "cathode (band)", "C"
    if name.startswith("CP_"):
        return "+ (pad 1)", "1"
    if name.startswith("LFPAK56"):
        return "gate = pin 4 (pad 2)", "2"
    if name.startswith("TO-252"):
        return "gate = pin 1", "1"
    if "1" not in nums:                              # e.g. TR3: bobbin pins 1 2 3 6 13-16 cut, no pad
        low = min((n for n in nums if n.isdigit()), key=int)
        return f"pin {low} (lowest pad present)", low
    return "pin 1", "1"


def refkey(r):
    head = r.rstrip("0123456789")
    return (head, int("0" + r[len(head):]))


def fmt(v, nd=4):
    s = f"{v:.{nd}f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


# ------------------------------------------------------------------------------------------- dump (kipy)
def dump(board, out):
    """Read-only geometry dump of the board (run through kipy; LoadBoard, no save)."""
    import pcbnew
    b = pcbnew.LoadBoard(board)
    mm = lambda v: round(v / 1e6, 6)  # noqa: E731
    cu = [l for l in b.GetEnabledLayers().CuStack()]
    canon = {l: pcbnew.LSET.Name(l) if hasattr(pcbnew.LSET, "Name") else b.GetStandardLayerName(l) for l in cu}
    ERR = 1000      # nm, polygon approximation error (outside for copper: gaps are never over-stated)

    def polys(sps):
        res = []
        for i in range(sps.OutlineCount()):
            o = sps.Outline(i)
            ring = [[mm(o.CPoint(k).x), mm(o.CPoint(k).y)] for k in range(o.PointCount())]
            holes = []
            for h in range(sps.HoleCount(i)):
                hh = sps.Hole(i, h)
                holes.append([[mm(hh.CPoint(k).x), mm(hh.CPoint(k).y)] for k in range(hh.PointCount())])
            if len(ring) > 2:
                res.append([ring, holes])
        return res

    g = {"layers": [canon[l] for l in cu], "user_names": {canon[l]: b.GetLayerName(l) for l in cu},
         "fps": [], "pads": [], "tracks": [], "vias": [], "zones": [], "slots": [], "outline": []}
    edge = pcbnew.SHAPE_POLY_SET()
    if not b.GetBoardPolygonOutlines(edge, True):
        sys.exit("jlc_fab: the board outline is not a valid closed polygon")
    for i in range(edge.OutlineCount()):
        o = edge.Outline(i)
        g["outline"].append([[mm(o.CPoint(k).x), mm(o.CPoint(k).y)] for k in range(o.PointCount())])
        for h in range(edge.HoleCount(i)):
            hh = edge.Hole(i, h)
            g["slots"].append([[mm(hh.CPoint(k).x), mm(hh.CPoint(k).y)] for k in range(hh.PointCount())])
    def crt(fp):
        """courtyard bounding box (KiCad frame, mm) or None"""
        fp.BuildCourtyardCaches()
        sp = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd)
        if sp.OutlineCount() == 0:
            return None
        bb = sp.BBox()
        return [mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom())]

    kinds = {pcbnew.PAD_ATTRIB_PTH: "pth", pcbnew.PAD_ATTRIB_NPTH: "npth", pcbnew.PAD_ATTRIB_SMD: "smd"}
    for fp in b.GetFootprints():
        ref = fp.GetReference()
        g["fps"].append(dict(ref=ref, value=fp.GetValue(), fpid=fp.GetFPIDAsString(),
                             x=mm(fp.GetPosition().x), y=mm(fp.GetPosition().y), rot=fp.GetOrientationDegrees(),
                             bottom=fp.IsFlipped(), npads=len(fp.Pads()), dnp=fp.IsDNP(),
                             no_bom=fp.IsExcludedFromBOM(), no_pos=fp.IsExcludedFromPosFiles(), crt=crt(fp)))
        for p in fp.Pads():
            hole = None
            if p.HasHole():
                hs = pcbnew.SHAPE_POLY_SET()
                p.TransformHoleToPolygon(hs, 0, ERR, pcbnew.ERROR_OUTSIDE)
                hole = polys(hs)
            shapes = {}
            for l in cu:
                if p.IsOnLayer(l) and p.FlashLayer(l):
                    sp = pcbnew.SHAPE_POLY_SET()
                    p.TransformShapeToPolygon(sp, l, 0, ERR, pcbnew.ERROR_OUTSIDE)
                    shapes[canon[l]] = polys(sp)
            g["pads"].append(dict(ref=ref, num=p.GetNumber(), net=p.GetNetname(), kind=kinds.get(p.GetAttribute(), "other"),
                                  x=mm(p.GetPosition().x), y=mm(p.GetPosition().y),
                                  drill=[mm(p.GetDrillSize().x), mm(p.GetDrillSize().y)] if p.HasHole() else None,
                                  hole=hole, shapes=shapes))
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            g["vias"].append(dict(x=mm(t.GetPosition().x), y=mm(t.GetPosition().y), d=mm(t.GetWidth(cu[0])),
                                  drill=mm(t.GetDrillValue()), net=t.GetNetname(),
                                  layers=[canon[l] for l in cu if t.IsOnLayer(l)]))
        elif t.Type() == pcbnew.PCB_ARC_T:
            sp = pcbnew.SHAPE_POLY_SET()
            t.TransformShapeToPolygon(sp, t.GetLayer(), 0, ERR, pcbnew.ERROR_OUTSIDE)
            g["tracks"].append(dict(layer=canon[t.GetLayer()], net=t.GetNetname(), w=mm(t.GetWidth()), polys=polys(sp)))
        else:
            g["tracks"].append(dict(layer=canon[t.GetLayer()], net=t.GetNetname(), w=mm(t.GetWidth()),
                                    pts=[mm(t.GetStart().x), mm(t.GetStart().y), mm(t.GetEnd().x), mm(t.GetEnd().y)]))
    for z in b.Zones():
        if z.GetIsRuleArea():
            continue
        for l in z.GetLayerSet().CuStack():
            pp = polys(z.GetFilledPolysList(l))
            if pp:
                g["zones"].append(dict(layer=canon[l], net=z.GetNetname(), polys=pp))
    with open(out, "w") as f:
        json.dump(g, f)


# ------------------------------------------------------------------------------------------- Gerber / drill readers
def read_gerber(path):
    """File function, draw counts, coordinate extent (mm, aperture sizes not included) and the pad flashes."""
    info = dict(function="", d01=0, d03=0, regions=0, apertures=0, bbox=None, flashes=collections.defaultdict(list),
                size=os.path.getsize(path))
    x = y = 0.0
    pad = None
    xs, ys = [], []
    cmd = re.compile(r"^(?:G0?[123])?(?:X(-?\d+))?(?:Y(-?\d+))?(?:I-?\d+)?(?:J-?\d+)?D0?([123])\*$")
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line.startswith("%TF.FileFunction,"):
                info["function"] = line[len("%TF.FileFunction,"):].rstrip("*%")
            elif line.startswith("%FS") and line != "%FSLAX46Y46*%":
                raise ValueError(f"{path}: unexpected coordinate format {line}")
            elif line.startswith("%ADD"):
                info["apertures"] += 1
            elif line.startswith("%TO.P,"):
                a = line[len("%TO.P,"):].rstrip("*%").split(",")
                pad = (a[0], a[1])
            elif line.startswith("%TD"):
                pad = None
            elif line.startswith("G36"):
                info["regions"] += 1
            else:
                m = cmd.match(line)
                if not m:
                    continue
                if m.group(1) is not None:
                    x = int(m.group(1)) / 1e6
                if m.group(2) is not None:
                    y = int(m.group(2)) / 1e6
                xs.append(x)
                ys.append(y)
                if m.group(3) == "1":
                    info["d01"] += 1
                elif m.group(3) == "3":
                    info["d03"] += 1
                    if pad:
                        info["flashes"][pad].append((x, y))
    if xs:
        info["bbox"] = (min(xs), min(ys), max(xs), max(ys))
    return info


def read_drill(path):
    """{diameter mm: [(x, y) ...]} per tool, tools with the same diameter kept apart: [(dia, function, hits)]."""
    tools, order, cur, func = {}, [], None, ""
    metric = slots = False
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("; #@! TA.AperFunction,"):
                func = line.split(",", 1)[1]
            elif line == "METRIC":
                metric = True
            elif re.match(r"^T\d+C[\d.]+$", line):
                t, d = line[1:].split("C")
                tools[int(t)] = (float(d), func, [])
                order.append(int(t))
            elif re.match(r"^T\d+$", line):
                cur = int(line[1:])
            elif line.startswith(("G85", "M15", "G00")) or "G85" in line:
                slots = True
            else:
                m = re.match(r"^X(-?[\d.]+)Y(-?[\d.]+)$", line)
                if m and cur:
                    tools[cur][2].append((float(m.group(1)), float(m.group(2))))
    if not metric:
        raise ValueError(f"{path}: not a metric Excellon file")
    return [tools[t] for t in order], slots


def unmatched(a, b, tol=0.0011):
    """Holes (diameter, x, y) of a without a partner in b and the other way round (drill files have 3 decimals)."""
    def miss(p, q):
        grid = collections.defaultdict(list)
        for d, x, y in q:
            grid[(math.floor(x * 100), math.floor(y * 100))].append((d, x, y))
        res = []
        for d, x, y in p:
            near = [h for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                    for h in grid.get((math.floor(x * 100) + dx, math.floor(y * 100) + dy), [])]
            if not any(abs(h[0] - d) < 1e-6 and abs(h[1] - x) <= tol and abs(h[2] - y) <= tol for h in near):
                res.append((d, round(x, 4), round(y, 4)))
        return res
    return miss(a, b), miss(b, a)


# ------------------------------------------------------------------------------------------- measurements
def measure(g):
    """Smallest track / gap / hole / annular ring / slot of the board from the pcbnew dump (shapely)."""
    import numpy as np
    import shapely
    from shapely.geometry import LineString, Point, Polygon
    from shapely.ops import unary_union
    from shapely.strtree import STRtree

    def mk(pp):
        return unary_union([Polygon(ring, holes).buffer(0) for ring, holes in pp])

    m = {}
    out = Polygon(g["outline"][0])
    x0, y0, x1, y1 = out.bounds
    m["size"] = (x1 - x0, y1 - y0)
    m["bounds"] = (x0, y0, x1, y1)
    m["outline_is_rect"] = abs(out.area - (x1 - x0) * (y1 - y0)) < 1e-3

    # slots: width = shortest chord across the slot, measured from the middle of every straight edge >= 2 mm
    m["slots"] = []
    for ring in g["slots"]:
        poly = Polygon(ring)
        pts = list(poly.exterior.coords)
        widths = []
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            ln = math.hypot(bx - ax, by - ay)
            if ln < 2.0:
                continue
            mx, my, nx, ny = (ax + bx) / 2, (ay + by) / 2, -(by - ay) / ln, (bx - ax) / ln
            for s in (1, -1):
                if poly.contains(Point(mx + s * nx * 0.01, my + s * ny * 0.01)):
                    ray = LineString([(mx + s * nx * 1e-4, my + s * ny * 1e-4), (mx + s * nx * 50, my + s * ny * 50)])
                    hit = ray.intersection(poly.exterior)
                    if not hit.is_empty:
                        widths.append(Point(mx, my).distance(hit))
        bx0, by0, bx1, by1 = poly.bounds
        m["slots"].append(dict(width=round(min(widths), 3), bounds=(bx0, -by1, bx1, -by0), area=poly.area,
                               length=round(poly.length / 2 - min(widths), 1)))
    m["slots"].sort(key=lambda s: s["bounds"])

    # tracks / vias / holes
    tw = collections.Counter(t["w"] for t in g["tracks"])
    m["track_min"] = min(tw)
    m["track_min_n"] = tw[min(tw)]
    m["track_min_layers"] = sorted({t["layer"] for t in g["tracks"] if t["w"] == min(tw)}, key=g["layers"].index)
    m["tracks"] = len(g["tracks"])
    m["vias"] = collections.Counter((v["d"], v["drill"]) for v in g["vias"])
    m["via_layers"] = collections.Counter(len(v["layers"]) for v in g["vias"])
    rings = [((v["d"] - v["drill"]) / 2, f"via {fmt(v['d'])}/{fmt(v['drill'])} at ({fmt(v['x'], 3)}, {fmt(-v['y'], 3)})")
             for v in g["vias"]]
    m["via_ring_min"] = min(rings)
    pth = [p for p in g["pads"] if p["kind"] == "pth"]
    npth = [p for p in g["pads"] if p["kind"] == "npth"]
    m["pth_pads"], m["npth_pads"] = len(pth), len(npth)
    m["oval_holes"] = sum(1 for p in pth + npth if abs(p["drill"][0] - p["drill"][1]) > 1e-6)
    m["drill_min"] = min([v["drill"] for v in g["vias"]] + [min(p["drill"]) for p in pth])
    m["pad_drill_min"] = min(min(p["drill"]) for p in pth)
    m["npth_min"] = min(min(p["drill"]) for p in npth) if npth else None
    prings = []
    for p in pth:
        hole = mk(p["hole"])
        for layer, pp in p["shapes"].items():
            prings.append((round(mk(pp).exterior.distance(hole), 4) if mk(pp).geom_type == "Polygon"
                           else round(mk(pp).boundary.distance(hole), 4), f"{p['ref']}.{p['num']} {layer}"))
    m["pad_ring_min"] = min(prings)
    m["pad_ring_min_n"] = sum(1 for r, _ in prings if r < m["pad_ring_min"][0] + 0.002)
    m["npth_ring"] = sorted({round(mk(pp).exterior.distance(mk(p["hole"])), 2) for p in npth for pp in p["shapes"].values()})
    m["npth_ring_layers"] = sorted({l for p in npth for l in p["shapes"]}, key=g["layers"].index)

    # copper to copper, different nets, same layer
    best = {}                 # kind pair -> (distance, layer, a, b)
    edge_min = (9.0, "")
    cut = unary_union([out.exterior] + [Polygon(r).exterior for r in g["slots"]])
    for layer in g["layers"]:
        geoms, meta = [], []    # meta: (kind, net key, description, footprint ref)
        for p in g["pads"]:
            if layer in p["shapes"]:
                geoms.append(mk(p["shapes"][layer]))
                meta.append(("pad", p["net"] or f"<no net {p['ref']}.{p['num']}>", f"{p['ref']}.{p['num']}", p["ref"]))
        for t in g["tracks"]:
            if t["layer"] == layer:
                geoms.append(mk(t["polys"]) if "polys" in t else
                             LineString([t["pts"][:2], t["pts"][2:]]).buffer(t["w"] / 2, quad_segs=24))
                c = t["pts"] if "pts" in t else [0, 0, 0, 0]
                meta.append(("track", t["net"], f"track {fmt(t['w'])} {t['net']} ({fmt(c[0], 3)}, {fmt(-c[1], 3)})", None))
        for v in g["vias"]:
            if layer in v["layers"]:
                geoms.append(Point(v["x"], v["y"]).buffer(v["d"] / 2, quad_segs=32))
                meta.append(("via", v["net"], f"via {v['net']} ({fmt(v['x'], 3)}, {fmt(-v['y'], 3)})", None))
        for z in g["zones"]:
            if z["layer"] == layer:
                for ring, holes in z["polys"]:
                    geoms.append(Polygon(ring, holes).buffer(0))
                    meta.append(("zone", z["net"], f"zone {z['net']}", None))
        if not geoms:
            continue
        arr = np.array(geoms, dtype=object)
        d_edge = shapely.distance(arr, cut)
        k = int(np.argmin(d_edge))
        if d_edge[k] < edge_min[0]:
            edge_min = (round(float(d_edge[k]), 3), f"{meta[k][2]} {layer}")
        tree = STRtree(geoms)
        ia, ib = tree.query(arr, predicate="dwithin", distance=0.6)
        keep = [(i, j) for i, j in zip(ia.tolist(), ib.tolist()) if i < j and meta[i][1] != meta[j][1]]
        if not keep:
            continue
        ia, ib = np.array(keep).T
        dist = shapely.distance(arr[ia], arr[ib])
        for i, j, d in zip(ia.tolist(), ib.tolist(), dist.tolist()):
            a, b = sorted((meta[i], meta[j]), key=lambda t: ("pad", "track", "via", "zone").index(t[0]))
            kind = f"{a[0]} - {b[0]}"
            if a[0] == b[0] == "pad":
                kind = "pad - pad, same footprint" if a[3] == b[3] else "pad - pad, different footprints"
            if kind not in best or d < best[kind][0]:
                best[kind] = (round(d, 3), layer, a[2], b[2])
    m["space"] = dict(sorted(best.items(), key=lambda kv: kv[1][0]))
    m["edge_min"] = edge_min
    return m


# ------------------------------------------------------------------------------------------- generation
def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit("jlc_fab: " + " ".join(os.path.relpath(c, ROOT) if os.path.isabs(c) else c for c in cmd) +
                 " failed\n" + r.stdout[-2000:] + r.stderr[-2000:])
    return r.stdout


def load_parts(path=PARTS):
    with open(path, newline="", encoding="utf-8") as f:
        return {r["refdes"]: r for r in csv.DictReader(l for l in f if not l.startswith("#"))}


def md_table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(str(c).replace("|", "/") for c in r) + " |" for r in rows]
    return "\n".join(out)


def generate(out):
    """Write the whole file set into `out`; returns (list of problems, summary lines)."""
    problems, summary = [], []
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):                       # only files this script owns
        if f.startswith(NAME) or f in OWNED:
            os.remove(os.path.join(out, f))

    # ---- 1. Gerbers and drill files (kicad-cli reads the board, it does not save it)
    run([CLI, "pcb", "export", "gerbers", "-o", out + os.sep, "-l", ",".join(l for l, _, _ in LAYERS),
         "--precision", "6", PCB])
    job = os.path.join(out, NAME + "-job.gbrjob")
    if os.path.exists(job):
        os.remove(job)                              # not part of what JLC asks for
    run([CLI, "pcb", "export", "drill", "-o", out + os.sep, "--format", "excellon", "--drill-origin", "absolute",
         "--excellon-zeros-format", "decimal", "--excellon-oval-format", "alternate", "--excellon-units", "mm",
         "--excellon-separate-th", "--generate-map", "--map-format", "pdf", PCB])
    gerbers = {}
    for layer, ext, _ in LAYERS:
        hits = [f for f in os.listdir(out) if f.endswith("." + ext)]
        if len(hits) != 1:
            sys.exit(f"jlc_fab: expected one .{ext} file for {layer}, found {hits}")
        gerbers[layer] = hits[0]
    drills = {"PTH": NAME + "-PTH.drl", "NPTH": NAME + "-NPTH.drl"}
    maps = [NAME + "-PTH-drl_map.pdf", NAME + "-NPTH-drl_map.pdf"]
    for f in list(drills.values()) + maps:
        if not os.path.exists(os.path.join(out, f)) or not os.path.getsize(os.path.join(out, f)):
            sys.exit(f"jlc_fab: {f} missing or empty")

    # ---- 2. board geometry (read-only pcbnew dump) and measurements
    with tempfile.TemporaryDirectory() as tmp:
        js = os.path.join(tmp, "g.json")
        r = subprocess.run([KIPY, os.path.abspath(__file__), "--dump", PCB, js], capture_output=True, text=True)
        if r.returncode or not os.path.exists(js):
            sys.exit("jlc_fab: board dump failed\n" + r.stdout[-2000:] + r.stderr[-2000:])
        with open(js) as f:
            g = json.load(f)
    if g["layers"] != [l for l, _, _ in LAYERS[:6]]:
        sys.exit(f"jlc_fab: copper layers of the board are {g['layers']}")
    m = measure(g)
    bx0, by0, bx1, by1 = m["bounds"]                # KiCad frame; Gerber frame: y -> -y
    gb = (bx0, -by1, bx1, -by0)

    # ---- 3. verify the Gerbers
    ginfo = {}
    for layer, ext, func in LAYERS:
        gi = ginfo[layer] = read_gerber(os.path.join(out, gerbers[layer]))
        if gi["function"] != func:
            problems.append(f"{gerbers[layer]}: file function {gi['function']!r}, expected {func!r}")
        if not gi["bbox"] or gi["d01"] + gi["d03"] + gi["regions"] == 0:
            problems.append(f"{gerbers[layer]}: draws nothing")
            continue
        x0, y0, x1, y1 = gi["bbox"]
        if x0 < gb[0] - 1e-6 or y0 < gb[1] - 1e-6 or x1 > gb[2] + 1e-6 or y1 > gb[3] + 1e-6:
            problems.append(f"{gerbers[layer]}: extent {gi['bbox']} outside the board outline {gb}")
    eb = ginfo["Edge.Cuts"]["bbox"]
    if eb and max(abs(a - b) for a, b in zip(eb, gb)) > 1e-6:
        problems.append(f"outline Gerber extent {eb} is not the board outline {gb}")
    # every slot of the board must be drawn in the outline Gerber: each slot vertex lies on a drawn coordinate set
    with open(os.path.join(out, gerbers["Edge.Cuts"])) as f:
        etxt = f.read()
    epts = {(int(a) / 1e6, int(b) / 1e6) for a, b in re.findall(r"X(-?\d+)Y(-?\d+)(?:I-?\d+J-?\d+)?D0[12]\*", etxt)}
    slots_found = 0
    for s in m["slots"]:
        sx0, sy0, sx1, sy1 = s["bounds"]
        inside = [p for p in epts if sx0 - 1e-6 <= p[0] <= sx1 + 1e-6 and sy0 - 1e-6 <= p[1] <= sy1 + 1e-6]
        if len(inside) >= 4:
            slots_found += 1
    if slots_found != len(m["slots"]):
        problems.append(f"outline Gerber shows {slots_found} of the {len(m['slots'])} board slots")

    # ---- 4. verify the drill files
    pth_tools, pth_slots = read_drill(os.path.join(out, drills["PTH"]))
    npth_tools, npth_slots = read_drill(os.path.join(out, drills["NPTH"]))
    pth_hits = [(d, x, y) for d, _, hits in pth_tools for x, y in hits]
    npth_hits = [(d, x, y) for d, _, hits in npth_tools for x, y in hits]
    board_pth = [(v["drill"], v["x"], -v["y"]) for v in g["vias"]] + \
                [(p["drill"][0], p["x"], -p["y"]) for p in g["pads"] if p["kind"] == "pth"]
    board_npth = [(p["drill"][0], p["x"], -p["y"]) for p in g["pads"] if p["kind"] == "npth"]
    for what, hits, board in (("PTH", pth_hits, board_pth), ("NPTH", npth_hits, board_npth)):
        a, b = unmatched(hits, board)
        if a or b or len(hits) != len(board):
            problems.append(f"{what} drill file differs from the board's holes: {len(hits)} hits / {len(board)} board holes, "
                            f"{len(a)} hits without a board hole, {len(b)} board holes without a hit, e.g. {(a + b)[:3]}")
    if pth_slots or npth_slots or m["oval_holes"]:
        problems.append("oval / slotted drill holes present: check the drill files by hand")
    mounts = sorted((f["ref"] for f in g["fps"] if MOUNT.match(f["ref"])), key=refkey)
    mount_holes = [(p["drill"][0], p["x"], -p["y"]) for p in g["pads"] if MOUNT.match(p["ref"]) and p["kind"] == "npth"]
    a, b = unmatched(npth_hits, mount_holes)
    if a or b or any(abs(d - MOUNT_DRILL) > 1e-6 for d, _, _ in npth_hits) or len(npth_hits) != len(mounts):
        problems.append(f"NPTH holes are not exactly the {len(mounts)} mounting holes at {MOUNT_DRILL} mm")

    # ---- 5. zip (what gets uploaded): Gerbers + drill files
    members = [gerbers[l] for l, _, _ in LAYERS] + list(drills.values())
    with zipfile.ZipFile(os.path.join(out, ZIP), "w", zipfile.ZIP_DEFLATED) as z:
        for f in members:
            zi = zipfile.ZipInfo(f, date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            with open(os.path.join(out, f), "rb") as fh:
                z.writestr(zi, fh.read())

    # ---- 6. BOM / CPL / NOT_ASSEMBLED
    parts = load_parts()
    fps = {f["ref"]: f for f in g["fps"]}
    if len(fps) != len(g["fps"]):
        problems.append("duplicate reference designators on the board")
    board_only = sorted((r for r in fps if r not in parts), key=refkey)
    bad_only = [r for r in board_only if not re.match(r"^(H|WP)\d+$", r)]
    if bad_only:
        problems.append("board parts missing in lib/jlc_parts_next.csv: " + " ".join(bad_only))
    gone = sorted((r for r in parts if r not in fps), key=refkey)
    if gone:
        problems.append("lib/jlc_parts_next.csv parts not on the board: " + " ".join(gone))
    tht = {p["ref"] for p in g["pads"] if p["kind"] == "pth"}
    groups = collections.defaultdict(list)          # LCSC number -> refs: one BOM line per JLC part
    texts = collections.defaultdict(list)           # LCSC number -> (comment, footprint) of each ref
    cpl, skipped = [], []
    for ref in sorted(set(fps) & set(parts), key=refkey):
        f, p = fps[ref], parts[ref]
        if p["footprint"] != f["fpid"]:
            problems.append(f"{ref}: footprint {f['fpid']} on the board, {p['footprint']} in the CSV")
        if p["value"] != f["value"]:
            problems.append(f"{ref}: value {f['value']!r} on the board, {p['value']!r} in the CSV")
        if bool(p["lcsc"]) != (p["status"] in ("exact", "equivalent", "changed")):
            problems.append(f"{ref}: status {p['status']} with LCSC number {p['lcsc']!r}")
        if (p["status"] == "dnp") != bool(f.get("dnp")) or (p["status"] == "dnp" and not (f["no_bom"] and f["no_pos"])):
            problems.append(f"{ref}: CSV status {p['status']}, board attributes DNP {f.get('dnp')} / exclude from BOM "
                            f"{f.get('no_bom')} / exclude from position files {f.get('no_pos')} (stage 18b: dnp <-> all three)")
        if not p["lcsc"]:
            skipped.append(ref)
            continue
        if f.get("no_bom") or f.get("no_pos"):
            problems.append(f"{ref}: has an LCSC number but is excluded from the BOM / position files on the board")
        comment = p["mpn"] if p["status"] == "changed" else p["value"]     # as tools/jlc_bom.py
        groups[p["lcsc"]].append(ref)
        texts[p["lcsc"]].append((comment, f["fpid"].split(":", 1)[-1]))
        rot = cpl_rotation(f["rot"], f["bottom"], rotation_fix(f["fpid"])[0]) % 360
        cpl.append((ref, fmt(f["x"]), fmt(-f["y"]), "Bottom" if f["bottom"] else "Top", fmt(rot)))
    with open(os.path.join(out, BOM), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for lcsc, refs in sorted(groups.items(), key=lambda kv: refkey(kv[1][0])):
            w.writerow([" / ".join(dict.fromkeys(t[0] for t in texts[lcsc])), ",".join(refs),
                        " / ".join(dict.fromkeys(t[1] for t in texts[lcsc])), lcsc])
    with open(os.path.join(out, CPL), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        w.writerows(cpl)
    multi = {l: r for l, r in groups.items() if len(set(texts[l])) > 1}

    # ---- 7. frame check: CPL against the copper Gerbers and the drill file
    flashes = collections.defaultdict(list)
    for layer in ("F.Cu", "B.Cu"):
        for (ref, _pin), pts in ginfo[layer]["flashes"].items():
            if ref in fps and (layer == "B.Cu") == fps[ref]["bottom"]:
                flashes[ref] += pts
    chip_ok, chip_bad = 0, []
    for ref, x, y, _side, _rot in cpl:
        f = fps[ref]
        pts = flashes.get(ref, [])
        if len(pts) != f["npads"] or ref in tht:
            continue                                 # custom-shape pads are regions, not flashes
        cx, cy = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
        d = math.hypot(cx - float(x), cy - float(y))
        name = f["fpid"].split(":", 1)[-1]
        if f["npads"] == 2 and re.match(r"^[RCL]_\d{4}_", name):
            if d < 0.002:
                chip_ok += 1
            else:
                chip_bad.append(f"{ref} {d:.3f}")
    if chip_bad or chip_ok < 100:
        problems.append(f"CPL frame check: {chip_ok} two-pad chip parts on their Gerber pads, off: {chip_bad[:10]}")
    pad_holes = [(p["drill"][0], p["x"], -p["y"]) for p in g["pads"] if p["kind"] == "pth"]
    tht_checked = len(pad_holes)
    tht_ok = tht_checked - len(unmatched(pad_holes, pth_hits)[0])
    if tht_ok != tht_checked:
        problems.append(f"drill frame check: {tht_ok} of {tht_checked} plated pad holes found in the PTH drill file")

    # ---- 7b. pad bounding-box centre of every footprint (Gerber frame) and its orientation pad (stage 18c, 14 F1 / F8)
    pads_of = collections.defaultdict(list)
    for p in g["pads"]:
        pads_of[p["ref"]].append(p)

    def pad_box(ref):
        """Bounding box of the copper of the named pads on the footprint's own outer layer (THT: that layer too)."""
        layer = "B.Cu" if fps[ref]["bottom"] else "F.Cu"
        xs, ys = [], []
        for p in pads_of[ref]:
            if not p["num"]:
                continue                             # paste-only / tab windows without a number
            for ring, _holes in p["shapes"].get(layer, []):
                xs += [q[0] for q in ring]
                ys += [-q[1] for q in ring]
        if not xs:
            return None
        return (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, max(xs) - min(xs), max(ys) - min(ys)

    centre, anchor_off = {}, []
    for ref in fps:
        box = pad_box(ref)
        if box is None:
            continue
        centre[ref] = box[:2]
    for ref, x, y, _side, _rot in cpl:
        cx, cy = centre[ref]
        dx, dy = cx - float(x), cy - float(y)
        if math.hypot(dx, dy) > 0.05:
            anchor_off.append((ref, fps[ref]["fpid"].split(":", 1)[-1], math.hypot(dx, dy), dx, dy, cx, cy))
    anchor_off.sort(key=lambda r: (-round(r[2], 2), refkey(r[0])))

    def orient(ref):
        """(what, pad, net, dx, dy) of the orientation pad relative to the pad-box centre, Gerber frame (y north)."""
        name = fps[ref]["fpid"].split(":", 1)[-1]
        what, num = polarity_pad(name, pads_of[ref])
        hits = [p for p in pads_of[ref] if p["num"] == num]
        if not hits:
            problems.append(f"{ref}: orientation pad {num!r} not found ({name})")
            return what, num, "", 0.0, 0.0
        px = sum(p["x"] for p in hits) / len(hits)
        py = -sum(p["y"] for p in hits) / len(hits)
        cx, cy = centre[ref]
        return what, num, hits[0]["net"], px - cx, py - cy

    def tab_dir(ref):
        """Direction of the tab / heatsink face of a vertical TO-220 / TO-247 (KiCad: body on local -y)."""
        a = math.radians(fps[ref]["rot"])
        return compass(-math.sin(a), math.cos(a))   # local (0, -1) -> KiCad (-sin, -cos) -> Gerber (-sin, +cos)

    def polarised(ref):
        name = fps[ref]["fpid"].split(":", 1)[-1]
        return len({p["num"] for p in pads_of[ref] if p["num"]}) > 2 or name.startswith(("D_", "CP_"))

    orient_refs = [c[0] for c in cpl if polarised(c[0])]
    edge_near = []                                   # placed parts with the courtyard < 2.5 mm from the board edge
    for c in cpl:
        cb = fps[c[0]].get("crt")
        if cb:
            d = min(cb[0] - bx0, cb[1] - by0, bx1 - cb[2], by1 - cb[3])
            if d < 2.5:
                edge_near.append((c[0], d))
    edge_near.sort(key=lambda r: r[1])

    # ---- 8. NOT_ASSEMBLED.md
    na = collections.defaultdict(list)
    for ref in skipped:
        p = parts[ref]
        na[(p["status"], p["value"], p["footprint"], "THT" if ref in tht else "SMD", p["review"], p["note"])].append(ref)
    order = {"missing": 0, "consigned": 1, "dnp": 2}
    na_rows = sorted(na.items(), key=lambda kv: (order.get(kv[0][0], 9), refkey(kv[1][0])))
    by_status = collections.Counter(parts[r]["status"] for r in fps if r in parts)
    tht_jlc = collections.defaultdict(list)
    for ref, *_ in cpl:
        if ref in tht:
            p = parts[ref]
            tht_jlc[(p["value"], fps[ref]["fpid"].split(":", 1)[-1], p["lcsc"], p["mpn"],
                     "Bottom" if fps[ref]["bottom"] else "Top")].append(ref)
    tht_rows = sorted(tht_jlc.items(), key=lambda kv: refkey(kv[1][0]))
    n_tht_jlc = sum(len(v) for v in tht_jlc.values())
    tht_pins = sum(1 for p in g["pads"] if p["kind"] == "pth" and p["ref"] in {r for v in tht_jlc.values() for r in v})
    txt = [f"# tube_power 5.2 - parts JLC does not fit", "",
           f"Generated by `tools/next/jlc_fab.py` from `kicad_next/{NAME}.kicad_pcb` and `lib/jlc_parts_next.csv`; "
           "do not edit by hand.", "",
           f"{len(skipped)} of the {len(parts)} parts have no LCSC number (status `missing` / `consigned` / `dnp`) and are "
           f"in neither `{BOM}` nor `{CPL}`. `missing` = wanted from JLC but not stocked: consign it, use JLC global "
           "sourcing, or fit it by hand. `consigned` = owner's part by design (custom magnetics, hardware). `dnp` = "
           "not fitted (KiCad \"Do not populate\" on symbol and footprint since stage 18b; their top paste apertures "
           "stay in the stencil, which leaves small solder bumps on the bare pads - harmless).", "",
           md_table(["Status", "Refdes", "Qty", "Value", "Footprint", "Type", "Review", "Note (CSV)"],
                    [(k[0], " ".join(refs), len(refs), k[1], k[2], k[3], k[4], k[5]) for k, refs in na_rows]), "",
           "## Board-only footprints (no part, not in the CSV)", "",
           md_table(["Refdes", "Footprint"],
                    [(" ".join(r for r in board_only if fps[r]["fpid"] == fid), fid)
                     for fid in sorted({fps[r]["fpid"] for r in board_only})]), ""]
    with open(os.path.join(out, "NOT_ASSEMBLED.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(txt))

    # ---- 9. README.md
    top = sum(1 for c in cpl if c[3] == "Top")
    bot = len(cpl) - top
    smd_top = sum(1 for c in cpl if c[3] == "Top" and c[0] not in tht)
    smd_bot = sum(1 for c in cpl if c[3] == "Bottom" and c[0] not in tht)
    no_stock = collections.defaultdict(list)
    reviews = collections.defaultdict(list)
    for ref in sorted(parts, key=refkey):
        p = parts[ref]
        if p["lcsc"] and not p["stock_at_check"].strip():
            no_stock[(p["lcsc"], p["mpn"], p["check_date"])].append(ref)
        if p["review"] and p["lcsc"]:
            reviews[(p["review"], p["lcsc"], p["mpn"])].append(ref)
    lib_types = collections.Counter(parts[c[0]]["library_type"] or "?" for c in cpl)
    lib_lines = collections.Counter(parts[refs[0]]["library_type"] or "?" for refs in groups.values())
    for lcsc, refs in groups.items():
        if len({parts[r]["mpn"] for r in refs}) > 1:
            problems.append(f"{lcsc}: different MPNs in the CSV for {' '.join(refs)}")
    dates = sorted({parts[c[0]]["check_date"] for c in cpl})
    sp = m["space"]
    overall = next(iter(sp.items()))
    not_same = next((kv for kv in sp.items() if "same footprint" not in kv[0]), overall)

    def verdict(val, lim, what="min"):
        return "ok" if val >= lim - 1e-9 else f"**BELOW the JLC {what} {fmt(lim)}**"

    slot_rows = []
    for i, s in enumerate(m["slots"], 1):
        b = s["bounds"]
        slot_rows.append((i, f"x {fmt(b[0], 2)} ... {fmt(b[2], 2)}, y {fmt(b[1], 2)} ... {fmt(b[3], 2)}",
                          fmt(s["width"], 3), verdict(s["width"], JLC["slot"]) +
                          (" (at the minimum)" if abs(s["width"] - JLC["slot"]) < 1e-6 else "")))
    narrow = [s for s in m["slots"] if s["width"] < JLC["slot"] - 1e-9]
    at_min = [s for s in m["slots"] if abs(s["width"] - JLC["slot"]) < 1e-6]
    file_rows = [(f"`{gerbers[l]}`", f"{l} ({g['user_names'].get(l, l)})" if g["user_names"].get(l, l) != l else l,
                  func, f"{ginfo[l]['apertures']} apertures, {ginfo[l]['d03']} flashes, {ginfo[l]['d01']} draws, "
                  f"{ginfo[l]['regions']} regions") for l, _, func in LAYERS]
    drill_rows = [("PTH", fmt(d, 3), len(h), fn.split(",")[-1]) for d, fn, h in pth_tools] + \
                 [("NPTH", fmt(d, 3), len(h), fn.split(",")[-1]) for d, fn, h in npth_tools]
    via_txt = ", ".join(f"{fmt(d)} / {fmt(dr)} mm x {n}" for (d, dr), n in sorted(m["vias"].items()))
    R = []
    A = R.append
    A(f"# tube_power 5.2 - JLCPCB fabrication and assembly files")
    A("")
    A(f"Generated by `python3 tools/next/jlc_fab.py` from `kicad_next/{NAME}.kicad_pcb` and `lib/jlc_parts_next.csv`; "
      "do not edit by hand (`--check` compares this directory with a fresh run, ignoring the dates KiCad embeds). "
      "Every number below is measured from the board by the script.")
    A("")
    A("## Files")
    A("")
    A(md_table(["File", "Content"], [
        (f"`{ZIP}`", f"**upload this to the PCB order**: the {len(LAYERS)} Gerbers + the two drill files below"),
        ("`*.gtl .g1 .g2 .g3 .g4 .gbl`", "copper L1 ... L6 (RS-274X, Protel extensions, mm 4.6, X2 attributes)"),
        ("`*.gts .gbs`", "solder mask top / bottom (vias tented: no mask opening on vias)"),
        ("`*.gtp .gbp`", "paste top / bottom (stencil; JLC makes its own for assembly)"),
        ("`*.gm1`", "board outline with the internal slots (Edge.Cuts)"),
        (f"`{drills['PTH']}`, `{drills['NPTH']}`", "Excellon drill files, plated / non-plated, mm, decimal, absolute origin"),
        (f"`{maps[0]}`, `{maps[1]}`", "drill maps (for people, not in the zip)"),
        (f"`{BOM}`", f"assembly BOM: Comment, Designator, Footprint, LCSC Part # ({len(groups)} lines, {len(cpl)} parts)"),
        (f"`{CPL}`", f"placement file: Designator, Mid X, Mid Y, Layer, Rotation ({len(cpl)} parts)"),
        ("`NOT_ASSEMBLED.md`", f"the {len(skipped)} parts JLC does not fit, with the reason"),
        ("`ROTATION_CHECK.md`", f"the {len(orient_refs)} polarised / multi-pin placed parts: where pin 1 / cathode / + must "
                                "appear in JLC's placement preview (tick list)"),
        (f"`{ASM_TOP}`, `{ASM_BOT}`", "assembly drawings: F.Fab / B.Fab + outline, pads sketched with their numbers, "
                                      "refdes; the bottom one mirrored (seen from below); not in the zip"),
        ("`HAND_ASSEMBLY.md`", "every part JLC does not place, in soldering order, with orientation and fitting notes"),
        ("`ORDER_REMARK.md`", "ready-to-paste remark texts for the PCB order and the PCBA order"),
        ("`README.md`", "this file")]))
    A("")
    A("**There are no silkscreen Gerbers on purpose** - the board is ordered without silkscreen. JLC's upload page may "
      "warn about missing silkscreen layers; that is expected.")
    A("")
    A("### Gerber layers")
    A("")
    A(md_table(["File", "KiCad layer", "X2 file function", "Content"], file_rows))
    A("")
    A(f"All layers lie inside the outline x {fmt(gb[0])} ... {fmt(gb[2])}, y {fmt(gb[1])} ... {fmt(gb[3])} mm (Gerber frame = "
      "KiCad x, -KiCad y; no aux origin). Zones are plotted as stored in the board (no refill).")
    A("")
    A("### Drill files")
    A("")
    A(md_table(["File", "Diameter mm", "Holes", "Kind"], drill_rows))
    A("")
    A(f"Plated: {len(pth_hits)} holes = {len(g['vias'])} vias + {m['pth_pads']} pad holes of the board. Non-plated: "
      f"{len(npth_hits)} holes = the mounting holes {' '.join(mounts)} at {MOUNT_DRILL:.1f} mm (H5 was removed). No oval / slotted drill "
      "holes: the slots are milled outline features in the `.gm1` file.")
    A("")
    A("## Order parameters to select by hand (JLCPCB)")
    A("")
    A(md_table(["Parameter", "Value"], [
        ("Base material / layers", "FR-4, **6 layers**"),
        ("Dimensions", f"**{fmt(m['size'][0], 2)} x {fmt(m['size'][1], 2)} mm**, single board, no panel (JLC adds the "
                       "assembly edge rails, see below)"),
        ("Thickness", "**1.6 mm**"),
        ("Stackup", "**JLC06161H-7628D** (\"specify stackup\" / impedance-stackup selector; special stackup: "
                    "**no economic PCB assembly, standard assembly only**)"),
        ("Impedance control", "not required (the stackup is chosen for the dielectric thickness, not for an impedance)"),
        ("Copper", "outer **1 oz**, inner **0.5 oz**"),
        ("Surface finish", "**ENIG**"),
        ("Silkscreen", "**none** - no silkscreen files are supplied; tell JLC in the order remark that this is intended"),
        ("Via covering", "via-in-pad: epoxy filled and capped, JLC's default on 6 layers (the board has vias in SMD pads; "
                         "see `kicad_next/README.md`); vias are tented in the mask Gerbers"),
        ("Slots / cut-outs", f"{len(m['slots'])} internal milled slots (creepage), non-plated"),
        ("Mounting holes", f"{len(mounts)} x {MOUNT_DRILL:.1f} mm non-plated"),
        ("Min track / space", f"{fmt(m['track_min'], 3)} / {fmt(overall[1][0], 3)} mm (see below)"),
        ("Min hole", f"{fmt(m['drill_min'], 3)} mm (via)"),
        ("Assembly", f"standard PCBA, **both sides** (top {top}, bottom {bot} parts in the CPL), `{BOM}` + `{CPL}`"),
        ("Edge rails / fiducials / tooling holes", "**added by JLCPCB** (PCBA options: tooling holes \"Added by JLCPCB\"; "
         "edge rails / fiducials \"Added by JLCPCB\" where the form offers it). The board has **no fiducials and no edge "
         f"rails**; {len(edge_near)} placed parts have their courtyard closer than 2.5 mm to the board edge (JLC assembly "
         f"T&C 2.3: {', '.join(f'{r} {fmt(d, 2)}' for r, d in edge_near)} mm), so rails "
         "are needed anyway. JLC adds 5 mm rails (normally on two sides) and fiducials on them; the boards ship **with the "
         "rails** unless removal is ordered (extra fee). Smallest pitch on the board 0.65 mm (TSSOP-8 / VSSOP-8), no "
         "QFN / BGA: no local fiducials needed"),
        ("Order number mark", "**\"Remove order number\"** (or the form's equivalent): the board has no silkscreen, a "
                              "marking would need one"),
        ("Confirm production file", "**yes** - the rotations are not verified (`ROTATION_CHECK.md`)"),
        ("Remark", "paste the texts of `ORDER_REMARK.md`")]))
    A("")
    A("Mask colour, delivery format, gold thickness and the other assembly options (bake, conformal coating ...) are the "
      "owner's choice; nothing in the design depends on them.")
    A("")
    A("## Measured against the JLC limits")
    A("")
    A("JLC column: `kicad_next/README.md` \"JLC manufacturing limits\" (multilayer, 1 oz, read 2026-11-17) and, for the slot "
      "width, jlcpcb.com/capabilities/pcb-capabilities read 2026-11-23. Gaps are measured between copper of different "
      "nets on one layer (pads true shape, tracks, vias, stored zone fill), accuracy about 0.002 mm.")
    A("")
    rows = [
        ("Board size", f"{fmt(m['size'][0], 2)} x {fmt(m['size'][1], 2)} mm" + ("" if m["outline_is_rect"] else " (not a rectangle)"),
         "max 656 x 586 (6 layers)", "ok"),
        ("Min track width", f"{fmt(m['track_min'], 3)} mm ({m['track_min_n']} of {m['tracks']} segments, "
         f"{', '.join(m['track_min_layers'])})", f"{fmt(JLC['track'])} mm", verdict(m["track_min"], JLC["track"])),
        ("Min copper gap, any two nets", f"{fmt(overall[1][0], 3)} mm ({overall[0]}: {overall[1][2]} / {overall[1][3]}, {overall[1][1]})",
         f"{fmt(JLC['space'])} mm", verdict(overall[1][0], JLC["space"])),
        ("Min copper gap outside one footprint's own pads", f"{fmt(not_same[1][0], 3)} mm ({not_same[0]}: {not_same[1][2]} / "
         f"{not_same[1][3]}, {not_same[1][1]})", f"{fmt(JLC['space'])} mm", verdict(not_same[1][0], JLC["space"])),
        ("Vias (diameter / drill)", via_txt + ", all through vias" if set(m["via_layers"]) == {6} else via_txt,
         f"{fmt(JLC['via_dia'])} / {fmt(JLC['via_drill'])} mm", verdict(min(d for d, _ in m["vias"]), JLC["via_dia"])),
        ("Min drill", f"{fmt(m['drill_min'], 3)} mm (via); smallest plated pad hole {fmt(m['pad_drill_min'], 3)} mm",
         f"{fmt(JLC['drill'])} mm", verdict(m["drill_min"], JLC["drill"])),
        ("Min via annular ring", f"{fmt(m['via_ring_min'][0], 3)} mm ({m['via_ring_min'][1]})", "0.05 mm (0.25 / 0.15 via)",
         verdict(m["via_ring_min"][0], 0.05)),
        ("Min PTH pad annular ring", f"{fmt(m['pad_ring_min'][0], 3)} mm ({m['pad_ring_min'][1]}; {m['pad_ring_min_n']} pad-layers "
         "at this value)", f"{fmt(JLC['annular'])} mm min, {fmt(JLC['annular_rec'])} recommended",
         verdict(m["pad_ring_min"][0], JLC["annular"]) +
         (" (below the recommended 0.20)" if JLC["annular"] - 1e-9 <= m["pad_ring_min"][0] < JLC["annular_rec"] - 1e-9 else "")),
        ("NPTH hole", f"{m['npth_pads']} x {fmt(m['npth_min'], 3)} mm", f"{fmt(JLC['npth'])} mm min", verdict(m["npth_min"], JLC["npth"])),
        ("Copper ring round the NPTH holes", (f"{', '.join(fmt(r, 3) for r in m['npth_ring'])} mm wide, starting at the hole edge, on "
         f"{', '.join(m['npth_ring_layers'])}") if m["npth_ring"] else "none",
         f"NPTH pad ring {fmt(JLC['npth_ring'])} mm (capabilities page, read 2026-11-23)",
         "ok" if not m["npth_ring"] or min(m["npth_ring"]) >= JLC["npth_ring"] else
         f"**narrower than JLC's {fmt(JLC['npth_ring'])} mm** (open item)"),
        ("Copper to board edge / slot", f"{fmt(m['edge_min'][0], 3)} mm ({m['edge_min'][1]})", f"{fmt(JLC['edge'])} mm",
         verdict(m["edge_min"][0], JLC["edge"])),
        ("Narrowest milled slot", f"{fmt(min(s['width'] for s in m['slots']), 3)} mm", f"{fmt(JLC['slot'], 1)} mm (non-plated slot)",
         verdict(min(s["width"] for s in m["slots"]), JLC["slot"]) + (f" ({len(at_min)} slots at the minimum)" if at_min else "")),
    ]
    A(md_table(["Item", "Board", "JLC", "Result"], rows))
    A("")
    A("Smallest gap per kind of copper pair (different nets, same layer):")
    A("")
    A(md_table(["Pair", "Gap mm", "Layer", "Between"], [(k, fmt(v[0], 3), v[1], f"{v[2]} / {v[3]}") for k, v in sp.items()]))
    A("")
    A(f"### Internal slots ({len(m['slots'])}, in `{gerbers['Edge.Cuts']}`)")
    A("")
    A(md_table(["#", "Extent (Gerber frame, mm)", "Width mm", f"vs JLC {fmt(JLC['slot'], 1)} mm"], slot_rows))
    A("")
    A(("**Slots narrower than the JLC minimum: " + str(len(narrow)) + ".** " if narrow else
       "No slot is narrower than JLC's minimum non-plated slot width. ") +
      (f"{len(at_min)} of them are exactly {fmt(JLC['slot'], 1)} mm wide, i.e. at the limit with no margin. " if at_min else "") +
      "The slot outlines are drawn with square corners where two straight edges meet (the L and T shaped slots); the "
      "router leaves its tool radius in inside corners.")
    A("")
    A("## Assembly")
    A("")
    A(f"* Board footprints {len(fps)} = {len(parts)} parts in `lib/jlc_parts_next.csv` + {len(board_only)} board-only "
      f"footprints ({' '.join(board_only)}).")
    A(f"* Parts by status: " + ", ".join(f"{s} {n}" for s, n in sorted(by_status.items(), key=lambda kv: -kv[1])) + ".")
    A(f"* In the BOM / CPL: **{len(cpl)} parts in {len(groups)} BOM lines (= LCSC numbers)** - top {top} "
      f"({smd_top} SMD + {top - smd_top} THT), bottom {bot} ({smd_bot} SMD + {bot - smd_bot} THT). JLC library type of the "
      f"placed parts (CSV, checked {dates[0]} ... {dates[-1]}): " +
      ", ".join(f"{t} {lib_types[t]} parts / {lib_lines[t]} LCSC numbers" for t in sorted(lib_types)) + ".")
    A(f"* Not in the BOM / CPL: **{len(skipped)} parts** (" +
      ", ".join(f"{s} {sum(1 for r in skipped if parts[r]['status'] == s)}" for s in ("missing", "consigned", "dnp")) +
      ") - `NOT_ASSEMBLED.md`.")
    if multi:
        A(f"* {len(multi)} BOM lines cover parts with different value texts or footprint names that use the same JLC part "
          "(Comment / Footprint then list each text, separated by \" / \"): " + ", ".join(sorted(multi)) + ".")
    A("* BOM: **one line per LCSC number** (the 5.1 tool `tools/jlc_bom.py` wrote one line per value / footprint / LCSC "
      "group; here a JLC part number never appears twice). Comment = schematic value, or the MPN where the CSV status "
      "is `changed` (as `tools/jlc_bom.py`).")
    A("* CPL frame: Mid X = KiCad x, Mid Y = -KiCad y in mm = the Gerber / drill frame (absolute origin, Y up; bottom-side "
      "X not mirrored), position = footprint anchor - the same as `kicad-cli pcb export pos`. Rotation 0 ... 360: top "
      "(KiCad orientation + correction), bottom (180 - KiCad orientation + correction), see \"Rotations\" below.")
    A(f"* Frame check (made on every run): {chip_ok} two-pad chip parts (R / C / L) have their CPL position on the centre of "
      f"their pad flashes in the copper Gerbers (same side as the CPL layer) within 0.002 mm; {tht_ok} of {tht_checked} plated pad "
      "holes of the board are at the same coordinates in the PTH drill file. **Origin and Y direction of CPL, Gerbers "
      "and drill files agree.**")
    A("")
    A("### Through-hole parts in the BOM (JLC solders these by hand / wave: extra cost, owner's decision)")
    A("")
    A(f"{n_tht_jlc} parts, {tht_pins} pins. To fit them yourself instead, delete their lines from `{BOM}` and `{CPL}` in "
      "JLC's BOM page (untick) - do not edit the generated files.")
    A("")
    A(md_table(["Refdes", "Qty", "Value", "Footprint", "LCSC", "MPN", "Side"],
               [(" ".join(refs), len(refs), k[0], k[1], k[2], k[3], k[4]) for k, refs in tht_rows]))
    A("")
    tht_na = sorted((r for r in skipped if r in tht), key=refkey)
    A(f"Through-hole parts JLC does not fit at all ({len(tht_na)}, see `NOT_ASSEMBLED.md`): {' '.join(tht_na)}.")
    A("")
    A("### Rotations: corrections from convention, NOT verified in JLC's preview")
    A("")
    A("CPL rotation = (KiCad orientation + correction) mod 360 on the top side, (180 - KiCad orientation + correction) "
      "mod 360 on the bottom side (stage 18c). The bottom-side rule and the corrections below are those of the two "
      "common KiCad -> JLC tools (kicad-jlcpcb-tools `fabrication.py`, JLCKicadTools `cpl_fix_rotations.py` / "
      "`cpl_rotations_db.csv`, read 2026-11-24); **none has been seen in JLC's placement preview**. Every polarised / "
      f"multi-pin part is listed in `ROTATION_CHECK.md` with the place its pin 1 / cathode / + must have: tick them off in "
      "the preview (top and bottom) before paying, and choose \"confirm production file\". A part that shows wrong in "
      "the preview: correct it there, then change `ROTATION_FIX` in `tools/next/jlc_fab.py` and regenerate.")
    A("")
    fix_rows = []
    for pat, deg, src, conf in ROTATION_FIX:
        refs = sorted((c[0] for c in cpl if rotation_fix(fps[c[0]]["fpid"])[1] == (pat, deg, src, conf)), key=refkey)
        fix_rows.append((f"`{pat}`", deg, len(refs), " ".join(refs), src, conf))
    no_fix = collections.defaultdict(list)
    for c in cpl:
        if rotation_fix(fps[c[0]]["fpid"])[1] is None and c[0] in orient_refs:
            no_fix[fps[c[0]]["fpid"].split(":", 1)[-1]].append(c[0])
    A(md_table(["Footprint pattern", "Correction deg", "Parts", "Refdes", "Source", "Confidence"], fix_rows))
    A("")
    A("Polarised / multi-pin footprints **without** a correction (0, no entry in the table; check these with the most "
      "care): " + "; ".join(f"`{n}` {' '.join(sorted(r, key=refkey))}" for n, r in sorted(no_fix.items())) + ".")
    A("")
    A(f"### Anchor not at the pad centre ({len(anchor_off)} placed parts)")
    A("")
    A("The CPL position is the footprint anchor (what `kicad-cli pcb export pos` writes; JLC's KiCad guide uses that "
      "file). JLC calls the column \"centroid\". These parts have their anchor more than 0.05 mm from the centre of "
      "the bounding box of their pads (copper on their own outer layer; for THT parts the anchor is pin 1). In the "
      "preview their JLC model may sit off the pads by this amount: drag it onto the pads, or replace Mid X / Mid Y by "
      "the pad-box centre given here. (The package body centre of TO-252 / LFPAK lies between the leads and the tab; the "
      "pad box is a close proxy, not the body.)")
    A("")
    A(md_table(["Refdes", "Footprint", "Offset mm", "Pad-box centre minus anchor (x / y) mm", "Pad-box centre (Mid X / Mid Y)"],
               [(r, n, fmt(d, 2), f"{fmt(dx, 2)} / {fmt(dy, 2)}", f"{fmt(cx, 3)} / {fmt(cy, 3)}")
                for r, n, d, dx, dy, cx, cy in anchor_off]))
    A("")
    A("## Open items before ordering")
    A("")
    n = 1
    miss = collections.defaultdict(list)
    for ref in skipped:
        if parts[ref]["status"] == "missing":
            miss[(parts[ref]["value"], parts[ref]["note"])].append(ref)
    A(f"{n}. **Parts with status `missing`** ({sum(len(v) for v in miss.values())}): decide per part - consign, global "
      "sourcing, substitute or hand-fit.")
    for (val, note), refs in sorted(miss.items(), key=lambda kv: refkey(kv[1][0])):
        A(f"   * {' '.join(refs)} ({val}): {note}")
    n += 1
    A(f"{n}. **Stock / price not read** for these LCSC numbers (CSV column `stock_at_check` empty) - look them up on the "
      "day of the order:")
    for (lcsc, mpn, date), refs in sorted(no_stock.items()):
        A(f"   * {lcsc} {mpn}: {' '.join(refs)} (row dated {date})")
    n += 1
    A(f"{n}. **All other stock figures are from {dates[0]} ... {dates[-1]}**, not from today: JLC's BOM page shows the "
      "current stock; parts flagged low in the review column below are the likely shortfalls.")
    n += 1
    A(f"{n}. **Review notes of the CSV** for parts that are in the BOM ({sum(len(v) for v in reviews.values())} parts):")
    for (rev, lcsc, mpn), refs in sorted(reviews.items(), key=lambda kv: refkey(kv[1][0])):
        A(f"   * {' '.join(refs)} ({lcsc} {mpn}): {rev}")
    n += 1
    A(f"{n}. **Rotations and bottom-side convention not verified** (section above): tick off `ROTATION_CHECK.md` in JLC's "
      "placement preview before paying.")
    n += 1
    A(f"{n}. **Through-hole parts in the BOM** ({n_tht_jlc} parts): decide whether JLC solders them (table above).")
    n += 1
    if at_min or narrow:
        A(f"{n}. **Slots at JLC's minimum width**: {len(at_min)} slots are {fmt(JLC['slot'], 1)} mm wide" +
          (f", {len(narrow)} are narrower" if narrow else "") + " - JLC may ask or widen; confirm in the order remark that they "
          "are creepage slots and must stay open.")
        n += 1
    if m["pad_ring_min"][0] < JLC["annular_rec"] - 1e-9:
        A(f"{n}. PTH pad annular ring {fmt(m['pad_ring_min'][0], 3)} mm is at JLC's absolute minimum ({fmt(JLC['annular'])}), below the "
          f"recommended {fmt(JLC['annular_rec'])} mm ({m['pad_ring_min'][1]}, {m['pad_ring_min_n']} pad-layers).")
        n += 1
    if m["npth_ring"] and min(m["npth_ring"]) < JLC["npth_ring"]:
        A(f"{n}. **Mounting holes {' '.join(mounts)}**: non-plated {fmt(MOUNT_DRILL, 1)} mm holes with a copper ring only "
          f"{fmt(min(m['npth_ring']), 3)} mm wide that starts at the hole edge ({', '.join(m['npth_ring_layers'])}; footprint "
          f"`MountingHole_3.0mm_NPTH_Ring3.5mm`). JLC asks for a ring of {fmt(JLC['npth_ring'])} mm round an NPTH pad and normally "
          "pulls copper back from a non-plated hole, so the ring may come out thinner or vanish. Nothing is soldered to "
          "it; decide whether that matters (the isolation rules treat the hole / ring as earthed) or tell JLC in the remark.")
        n += 1
    A(f"{n}. **Mounting hardware** (holes {' '.join(mounts)}: plain {fmt(MOUNT_DRILL, 1)} mm NPTH without copper since routing "
      "stage 13c; the M3 screws bond the board to the earthed chassis). Basic insulation from a **6 mm** head / standoff "
      "needs primary copper >= 6.2 mm and secondary copper >= 7.2 mm from the hole centre (on every layer). Met at H3 "
      "(secondary 7.26 mm) and H6 (primary 6.21 mm); H1 has no primary / secondary copper within 12 mm. **H2, H4, H7 and H8 "
      "need insulating hardware** (nylon screw and nylon standoff, or nylon washers under the head and the standoff): "
      "H4 primary 4.93 mm from the centre (head 1.93 mm instead of 3.2), H7 primary 5.08 mm (In2; R48 pad 5.18 mm on B.Cu), "
      "H8 secondary 6.27 mm (pour edges at the 6.3 mm keep-out; head 3.27 instead of 4.2; C102 pad 1 7.48 mm, can "
      "1.04 mm clear of a 6 mm head and 0.54 mm of a 7 mm washer since stage 16b), H2 UART island 3.13 mm (head 0.13 instead "
      "of 1.0; "
      "J4 pads 3.68 mm; the J4 housing is 3.21 mm from the centre: a 7 mm washer at H2 overlaps it by 0.29 mm, so no "
      "washer wider than 6.4 mm there). Metal heads, washers or standoffs wider than 6 mm reduce every figure "
      "(kicad_next/README.md stage 13c).")
    n += 1
    A(f"{n}. **No silkscreen**: there is no polarity / pin-1 / refdes marking on the board; JLC's assembly relies on the CPL "
      f"alone (`ROTATION_CHECK.md`), hand-fitted parts follow `HAND_ASSEMBLY.md` and the assembly drawings `{ASM_TOP}` / "
      f"`{ASM_BOT}`.")
    n += 1
    A(f"{n}. **SICD1 / SICD2 orientation** (stage 16a, finding 13 F1): before soldering, hold a C3D02060A over SICD1 / "
      "SICD2 with the tab to the heatsink plate: cathode (pin 1, also the tab) must be on the DC+ pad (footprint "
      "`TO-220-2_Vertical_KA`: pad K = pin 1, rectangular, DC+; KiCad board coordinates SICD1 K (11.8, -21.4), SICD2 K "
      "(3.40, -3.82) since stage 17a).")
    n += 1
    A(f"{n}. **Primary heatsink plate** (stages 17a / 17b, finding 12 F1; nominal datasheet lead-to-back distances, "
      "caliper check still open): nominal back faces west row Q5 6.15, SICD2 5.99; east row Q6 8.99, SICD1 9.22, "
      "Q19 / Q7 8.96 (KiCad x, mm). **Insulating pads only under Q5, Q6, SICD1, SICD2** (live tabs); Q19 / Q7 are "
      "FullPAKs and go on the plate without pad. With 0.25 mm pads the flat plate between the rows can be **2.34 mm "
      "(touching Q5 and Q6) to 2.56 mm (touching Q5, SICD1, Q19, Q7; Q6 leads pushed 0.22 mm)**, 2.5 mm suggested; "
      "SICD2 stays 0.17 mm off the plate (lead flex). **Cut-out for the H4 screw head** (6 mm head / standoff at "
      "(5.84, -40.13), plate side y -43.1 ... -37.1, at least 7 mm wide, or nylon head below the plate). **Notch at "
      "C87** (0603 on F.Cu, body x 4.9 ... 6.5, y -60.2 ... -58.6, 0.9 mm high) is still needed: the west face of "
      "the plate is at x 6.15 ... 6.4 there. Exposed F.Cu under the plate strip (x 6.15 ... 9.3): pad 1 of C87 "
      "(+3V3), pads 2 / 4 of DB1 (DC+ / GND), pad 1 of C73 (DC+) - as on 5.1 for DB1 / C73; the rest of the strip is "
      "DC+ / GND / PFC_DRAIN_1 pour under solder mask (mask is not insulation).")
    n += 1
    A(f"{n}. Stackup JLC06161H-7628D excludes economic assembly; confirm the stackup name in JLC's selector at order time "
      "(JLC renames / retires stackups).")
    n += 1
    A(f"{n}. Not checked by this script: the Gerbers were not viewed in JLC's own Gerber viewer, JLC's DFM result and "
      "the price are unknown, inner-layer 0.5 oz track / space limits are not listed by JLC (the outer-layer figures "
      "are used).")
    A("")
    with open(os.path.join(out, "README.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(R))

    # ---- 10. ROTATION_CHECK.md (stage 18c, findings 14 F1)
    def family(ref):
        name = fps[ref]["fpid"].split(":", 1)[-1]
        for k, pat in enumerate((r"SOIC|SSOP|DSO|SOT-23", r"LFPAK|TO-252", r"^D_", r"^CP_Elec", r"^CP_Radial",
                                 r".")):
            if re.search(pat, name):
                return k
        return 9

    def where(ref):
        what, num, net, dx, dy = orient(ref)
        d = compass(dx, dy)
        top_view = f"{what} **{d}** ({fmt(dx, 2)} / {fmt(dy, 2)} mm)"
        below = compass(-dx, dy) if fps[ref]["bottom"] else "-"
        name = fps[ref]["fpid"].split(":", 1)[-1]
        if name.startswith(("LFPAK56", "TO-252")):
            tab = "3" if name.startswith("LFPAK56") else "2"
            tp = [p for p in pads_of[ref] if p["num"] == tab]
            tdx = sum(p["x"] for p in tp) / len(tp) - centre[ref][0]
            tdy = -sum(p["y"] for p in tp) / len(tp) - centre[ref][1]
            top_view += f"; tab (drain) **{compass(tdx, tdy)}**"
            if fps[ref]["bottom"]:
                below += f"; tab {compass(-tdx, tdy)}"
        return num, net, top_view, below

    rows_rc = []
    for ref in sorted(orient_refs, key=lambda r: (family(r), fps[r]["fpid"], refkey(r))):
        f = fps[ref]
        num, net, top_view, below = where(ref)
        deg, _e = rotation_fix(f["fpid"])
        crot = next(c[4] for c in cpl if c[0] == ref)
        rows_rc.append(("[ ]", ref, f["fpid"].split(":", 1)[-1], parts[ref]["lcsc"], "Bottom" if f["bottom"] else "Top",
                        fmt(f["rot"] % 360), crot, deg, f"{num} ({net})", top_view, below))
    plain = collections.defaultdict(list)
    for c in cpl:
        if c[0] not in orient_refs:
            nm = fps[c[0]]["fpid"].split(":", 1)[-1]
            mt = re.match(r"^([RCL])_(\d{4})_", nm)
            plain[f"{mt.group(1)}_{mt.group(2)}" if mt else nm].append(c)
    RC = [f"# tube_power 5.2 - rotation / polarity check in JLC's placement preview", "",
          f"Generated by `tools/next/jlc_fab.py` from `kicad_next/{NAME}.kicad_pcb`; do not edit by hand. Stage 18c, "
          "findings 14 F1.", "",
          "**The board has no silkscreen** (on purpose): there is no pin-1 dot, polarity mark or refdes on the board, "
          "and JLC's engineers cannot compare against a legend. Judge pin 1 / cathode / + in the preview from the pad "
          "pattern (copper) and the position given here. The rotations in the CPL use the corrections of "
          "`ROTATION_FIX` (README \"Rotations\"), which come from the common KiCad -> JLC tools and are **not verified "
          "in JLC's preview**.", "",
          "How to read the table:", "",
          "* Directions are board directions in the **top view** (as the Gerbers are drawn: north = up = +Y of the "
          "CPL, east = right = +X). For bottom-side parts the top view looks *through* the board; the last column gives "
          "the same direction **seen from below** (east and west swapped), which is how a bottom view normally shows "
          "it - check which of the two JLC's bottom preview uses with one part first (e.g. the first bottom SOIC).",
          "* The marker is the pad that fixes the orientation: IC pin 1 (dot / bevel on the package), diode cathode "
          "(band), electrolytic + (on SMD cans the cut corners of the plastic base are on the + side, the dark mark on "
          "the top is -), LFPAK / DPAK gate pin and tab. The offset is from the centre of the part's pad pattern, "
          "in mm (x / y).",
          "* `CPL rot` is what JLC receives; `KiCad rot` the board orientation; `Corr.` the `ROTATION_FIX` value.",
          "* Proteus-numbered footprints (`*_Proteus`): the pad names differ from the data-sheet pin numbers on "
          "SOT-23_Proteus (JEDEC pin 1 = pad 2, the single pad = pad 1); the position given is the physical pin 1.", "",
          md_table(["OK", "Refdes", "Footprint", "LCSC", "Side", "KiCad rot", "CPL rot", "Corr.", "Marker pad (net)",
                    "Marker in the top view", "Seen from below (bottom parts)"], rows_rc), "",
          "## Two-pin parts without polarity", "",
          "No orientation to check (0 and 180 degrees are the same part); only that each sits centred on its two pads:", ""]
    for fam_name, cs in sorted(plain.items()):
        RC.append(f"* `{fam_name}`: {len(cs)} part{'s' if len(cs) > 1 else ''} (top {sum(1 for c in cs if c[3] == 'Top')}, bottom "
                  f"{sum(1 for c in cs if c[3] == 'Bottom')})")
    RC += ["", f"{len(rows_rc)} rows to tick + {sum(len(v) for v in plain.values())} non-polarised two-pin parts = "
           f"{len(cpl)} CPL rows.", ""]
    if len(rows_rc) + sum(len(v) for v in plain.values()) != len(cpl):
        problems.append("ROTATION_CHECK.md does not cover every CPL row")
    with open(os.path.join(out, "ROTATION_CHECK.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(RC))

    # ---- 11. assembly drawings (kicad-cli reads the board, it does not save it)
    common = ["--mode-single", "--scale", "0", "--exclude-value", "--sketch-pads-on-fab-layers",
              "--crossout-DNP-footprints-on-fab-layers", "--black-and-white", "--drill-shape-opt", "1"]
    run([CLI, "pcb", "export", "pdf", "-o", os.path.join(out, ASM_TOP), "-l", "F.Fab,Edge.Cuts"] + common + [PCB])
    run([CLI, "pcb", "export", "pdf", "-o", os.path.join(out, ASM_BOT), "-l", "B.Fab,Edge.Cuts", "--mirror"] + common + [PCB])
    for f in (ASM_TOP, ASM_BOT):
        if not os.path.exists(os.path.join(out, f)) or os.path.getsize(os.path.join(out, f)) < 10000:
            problems.append(f"{f} missing or empty")

    # ---- 12. HAND_ASSEMBLY.md (stage 18c, findings 14 F5)
    HAND_NOTES = {
        "C10 C26": "value `na`: **not fitted** (DNP since stage 18b). Their pads get paste from the stencil: small solder "
                   "bumps, harmless.",
        "DB1": "TBS22K bridge (MCC), not stocked at JLC: consign or fit by hand. Pads 1 AC2, 2 DC+, 3 AC1, 4 GND - the "
               "footprint, position and pad nets of the bench-verified 5.1 board. Under the primary heatsink strip "
               "(fab README open item: exposed DC+ / GND pads under the plate).",
        "GND HT_6V3 HT_GND IN1 IN2 N15V_OUT N80V_OUT P15V_OUT P400V P5V_OUT PE SEC_GND":
            "faston blade terminals (2 x 1 pins, 5.0 mm, drill 1.4 mm). Fit them before the tall parts.",
        "R27": "Ohmite TWW10 47 Ω 10 W radial (TWW10J47RE), not stocked at JLC: consign. No polarity. Stands upright.",
        "Q5 Q6": "C2M0160120D TO-247-3 (obsolete at Wolfspeed: 5.1 spares, or C3M0160120D, same pin-out 1 G / 2 D / "
                 "3 S, tab = drain). **0.25 mm insulating pad** under the tab (live, drain). Tab against the primary "
                 "plate.",
        "SICD1 SICD2": "C3D02060A TO-220-2 SiC diode (obsolete: 5.1 spares or a checked substitute). **Cathode = pin 1 "
                       "= tab, on the rectangular pad K = DC+**, tab to the plate (footprint `TO-220-2_Vertical_KA`, "
                       "stage 16a): hold a part over the site with its tab to the plate before soldering. **0.25 mm "
                       "insulating pad** under the tab (live).",
        "Q7 Q19": "IPA60R280CFD7 TO-220 FullPAK, **consigned** (owner's stock), pin 1 G / 2 D / 3 S. On the primary "
                  "plate **without** pad (insulated package); pins at x 11.60 (stage 17b) so the face is on the "
                  "plate plane.",
        "Q8 Q21": "IPA60R280CFD7 TO-220 FullPAK, **consigned**. Tab to the secondary plate south of the pair, no pad.",
        "TR1": "EEL19 4 + 6 custom flyback transformer (winding specification at the top of "
               "`simulation/flyback/EEL19_DESIGN.md`). **Bobbin pins 4 and 6 clipped** (no pad). Pin diameter "
               "checked by the owner against the drills (1.0 / 0.9 mm, 2026-11-27, findings 14 F2): square pins fit.",
        "TR2": "EF25 2 x 5 heater LLC transformer, 64 / 2 / 2 T, **pins 3 and 8 not fitted**. The two 2-turn secondary "
               "halves and the centre tap are heavy wires soldered to WP1 - WP4 (as 5.1): half 1 from pins 9 + 10 / WP4 "
               "(Q14_DRAIN) to the centre tap WP3 (6V3), half 2 from the centre tap WP2 (6V3) to pins 6 + 7 / WP1 "
               "(Q13_DRAIN); primary start 1 + 2, finish 4 + 5 (dots: kicad_next/CHANGES_5_2.md, TR2 table - check against "
               "the 5.1 transformer).",
        "TR3": "EC42/15 DAB transformer, 20 : 21 T. **Cut bobbin pins 1, 2, 3, 6, 13 - 16.** Gap by a tape spacer under "
               "all legs: start at about **0.83 mm (Lm ≈ 120 µH)**, tune on the bench for soft switching at light load "
               "(`simulation/dab/DAB_TRANSFORMER.md` 5 / 6 / 8). Pin diameter checked by the owner against the "
               "1.2 mm drill (2026-11-27, findings 14 F2). Check the core-plate clearance at the secondary pins "
               "(>= 4 mm, or tape) when fitting.",
        "L1 L2": "PFC chokes, sendust toroid OD 31.5 x 16.7 mm, **upright** as on the 5.1 board, ring plane along the "
                 "board's long axis, the two leads in the RM8 holes. Measure L at 0 A and at the PFC peak current "
                 "(value `TBD (measured)`).",
        "WP1 WP2 WP3 WP4": "wire pads (drill 2.55 mm) for the TR2 secondary: WP1 Q13_DRAIN, WP2 / WP3 6V3 (centre tap), "
                           "WP4 Q14_DRAIN - see TR2.",
        "H1 H2 H3 H4 H6 H7 H8": "plain 3.0 mm NPTH mounting holes, no copper (stage 13c). **H2, H4, H7, H8: nylon screw "
                                "and nylon standoff** (or nylon washers under head and standoff) - copper of other domains "
                                "is closer than a metal 6 mm head allows; **no washer wider than 6.4 mm at H2** (J4 "
                                "housing). H1, H3, H6: metal M3 allowed (they bond the board to the earthed chassis). "
                                "**H4 head under the primary plate: cut-out in the plate** (y -43.1 ... -37.1 KiCad, "
                                ">= 7 mm wide) or a nylon head below it.",
    }
    groups_hand = [
        ("1. Not fitted", ["C10 C26"]),
        ("2. SMD by hand (before any through-hole part)", ["DB1"]),
        ("3. Low through-hole parts", ["GND HT_6V3 HT_GND IN1 IN2 N15V_OUT N80V_OUT P15V_OUT P400V P5V_OUT PE SEC_GND",
                                       "R27"]),
        ("4. Heatsink-mounted semiconductors - fit the plates first", ["Q5 Q6", "SICD1 SICD2", "Q7 Q19", "Q8 Q21"]),
        ("5. Magnetics (last: tallest and heaviest)", ["L1 L2", "TR1", "TR2", "TR3", "WP1 WP2 WP3 WP4"]),
        ("6. Mounting hardware", ["H1 H2 H3 H4 H6 H7 H8"]),
    ]
    covered = [r for _g, keys in groups_hand for k in keys for r in k.split()]
    must = set(skipped) | set(board_only)
    if sorted(covered, key=refkey) != sorted(must, key=refkey) or len(covered) != len(set(covered)):
        problems.append("HAND_ASSEMBLY.md groups do not cover the parts JLC does not place exactly once: "
                        f"missing {sorted(must - set(covered), key=refkey)}, extra {sorted(set(covered) - must, key=refkey)}")

    def hand_orient(ref):
        name = fps[ref]["fpid"].split(":", 1)[-1]
        if ref in board_only or re.match(r"^(H|WP)\d+$", ref):
            return "-"
        if re.match(r"^TO-2(20|47)", name):
            return f"tab / back face **{tab_dir(ref)}**"
        nums = {p["num"] for p in pads_of[ref] if p["num"]}
        if len(nums) <= 2 and not name.startswith(("D_", "CP_")):
            return "no polarity" if not name.startswith("Terminal") else "-"
        what, num, net, dx, dy = orient(ref)
        return f"{what} ({net}) **{compass(dx, dy)}** of the centre"

    HA = [f"# tube_power 5.2 - hand assembly sheet", "",
          f"Generated by `tools/next/jlc_fab.py` from `kicad_next/{NAME}.kicad_pcb` and `lib/jlc_parts_next.csv`; "
          "do not edit by hand. Stage 18c, findings 14 F5.", "",
          f"Every part JLC does **not** place ({len(skipped)} parts without an LCSC number + {len(board_only)} board-only "
          f"footprints), in soldering order. **The board has no silkscreen**: use the assembly drawings `{ASM_TOP}` "
          f"(top) and `{ASM_BOT}` (bottom, mirrored = seen from below) for the positions; they show the Fab outline, "
          "the pads with their numbers and the refdes. Directions below are top-view board directions (north = up "
          "in the drawing). Pin 1 of a through-hole footprint is the square / rectangular pad.", ""]
    for title, keys in groups_hand:
        HA += [f"## {title}", ""]
        rows_h = []
        for k in keys:
            refs = k.split()
            r0 = refs[0]
            p = parts.get(r0)
            val = " / ".join(dict.fromkeys(parts[r]["value"] for r in refs)) if p else "-"
            fpn = " / ".join(dict.fromkeys(fps[r]["fpid"].split(":", 1)[-1] for r in refs))
            st = (p["status"] + (f" ({p['lcsc']})" if p and p["lcsc"] else "")) if p else "board-only"
            ors = sorted({hand_orient(r) for r in refs})
            orient_txt = ors[0] if len(ors) == 1 else "; ".join(f"{r}: {hand_orient(r)}" for r in refs)
            rows_h.append((" ".join(refs), len(refs), val, fpn, st, orient_txt, HAND_NOTES[k]))
        HA.append(md_table(["Refdes", "Qty", "Value", "Footprint", "Status", "Orientation", "Notes"], rows_h))
        HA.append("")
        if title.startswith("4."):
            HA += ["Primary plate (stages 17a / 17b; nominal data-sheet lead-to-back distances, caliper check open): flat "
                   "plate 2.34 ... 2.56 mm thick between the rows (2.5 mm suggested), insulating pads only under Q5, Q6, "
                   "SICD1, SICD2; notch at C87 and the H4 head cut-out (fab README open items). Clamp every part to its "
                   "plate, then solder the leads, so no lead is stressed.", ""]
    tht_bom_refs = sorted((r for v in tht_jlc.values() for r in v), key=refkey)
    HA += ["## Through-hole parts in the BOM (JLC fits them unless unticked)", "",
           f"{len(tht_bom_refs)} parts: {' '.join(tht_bom_refs)} (README \"Through-hole parts in the BOM\"). If they "
           "are unticked at the order, fit them after group 3 here. Orientation as `ROTATION_CHECK.md` (electrolytics: "
           "+ on the square pad). Notes:", "",
           "* **J2** (XKB X1321FV-2x25-C43D24, female 2 x 25, 1.27 mm): check mating height (4.3 mm insulator + card "
           "pin length) and orientation / pin 1 against the control card's male right-angle header before soldering.",
           "* **J4** (UART 1 x 6, 2.54 mm): 1 ISO_UART_GND, 2 TXD in, 3 ISO_UART_GND, 4 RXD out, 5 ISO_UART_GND, "
           "6 UART_3V3 in. Pin 6 must be the far end's 3.3 V I/O supply and must always be connected (findings 04 F6).",
           "* **C102** (56 µF 250 V): + on ISO_GND, - on -100V BIAS (negative rail): the square pad is + as on every "
           "electrolytic.", ""]
    with open(os.path.join(out, "HAND_ASSEMBLY.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(HA))

    # ---- 13. ORDER_REMARK.md (stage 18c, findings 14 F7)
    def slot_owner(s):
        x0, y0, x1, y1 = s["bounds"]
        best = None
        for r in ("ISO1", "ISO2", "U11", "TR1"):
            if r in fps:
                fx, fy = fps[r]["x"], -fps[r]["y"]
                d = math.hypot(max(x0 - fx, 0, fx - x1), max(y0 - fy, 0, fy - y1))
                if d < 8 and (best is None or d < best[0]):
                    best = (d, r)
        return best[1] if best else None

    slot_txt = []
    for w in sorted({s["width"] for s in m["slots"]}, reverse=True):
        ss = [s for s in m["slots"] if s["width"] == w]
        owners = [o for o in (slot_owner(s) for s in ss) if o]
        rest = len(ss) - len(owners)
        what = [f"at {', '.join(sorted(set(owners), key=refkey))}"] if owners else []
        if rest:
            what.append(f"{rest} {'other' if owners else ''} cut-out{'s' if rest > 1 else ''}".replace("  ", " "))
        slot_txt.append(f"{len(ss)} x {fmt(w, 2)} mm ({'; '.join(what)})")
    na_txt = " ".join(sorted(skipped, key=refkey))
    pcb_remark = (
        f"6-layer board, please use stackup JLC06161H-7628D (1.6 mm, outer 1 oz, inner 0.5 oz). Layer order: GTL = L1 "
        "(top), G1 = L2, G2 = L3, G3 = L4, G4 = L5, GBL = L6 (bottom); the Gerber X2 file attributes give the same "
        "order. NO SILKSCREEN IS INTENTIONAL: no silkscreen files are supplied, please do not add any marking and do not "
        "print an order number on the board (\"remove order number\" selected). "
        f"The {len(m['slots'])} internal cut-outs drawn in the outline file (GM1) are intentional milled creepage slots, "
        f"non-plated: {', '.join(slot_txt)}. Please do not plate, fill or narrow them; the widths are minimum finished "
        f"widths. The {len(mounts)} mounting holes ({MOUNT_DRILL:.1f} mm) are plain non-plated holes without copper. Vias "
        "inside SMD pads are intentional: epoxy filled and capped.")
    pcba_remark = (
        f"Standard PCBA, both sides: top {top} parts, bottom {bot} parts, as in the BOM / CPL. The board has NO "
        "SILKSCREEN on purpose, so there is no polarity or pin-1 mark: please take orientation from the CPL and the pad "
        "pattern; we check every polarised part in the placement preview and ask for the production file for confirmation. The board has NO "
        "FIDUCIALS and NO EDGE RAILS: please add edge rails and fiducials (added by JLCPCB); several parts are closer "
        "than 2.5 mm to the board edge. Place only the parts in the BOM / CPL. The following parts are NOT to be placed "
        f"(we fit them ourselves, leave their pads empty): {na_txt}; C10 and C26 are not fitted at all. PWM2 "
        "(C17699638, Infineon ICE5AR0680AG): the package is PG-DSO-12 (SO-16 narrow body with two positions per side "
        "empty, no exposed pad), not BSOP-12-EP; pin 1 as in the CPL.")
    OR = [f"# tube_power 5.2 - order remarks (JLCPCB)", "",
          f"Generated by `tools/next/jlc_fab.py` from `kicad_next/{NAME}.kicad_pcb` and `lib/jlc_parts_next.csv`; "
          "do not edit by hand. Stage 18c, findings 14 F7.", "",
          "The order-form parameters (layers, size, stackup, copper, finish, silkscreen none, via covering, rails / "
          "fiducials, order number, confirm production file) are in `README.md` section **\"Order parameters to select "
          "by hand\"** - one source, not repeated here. Below: the remark texts, ready to paste.", "",
          "## PCB order remark", "", "```text", pcb_remark, "```", "",
          "## PCBA order remark", "", "```text", pcba_remark, "```", "",
          "If the THT parts in the BOM are unticked at the order (README \"Through-hole parts in the BOM\"), add their "
          "refdes to the \"NOT to be placed\" sentence. Character count: PCB remark "
          f"{len(pcb_remark)}, PCBA remark {len(pcba_remark)} (JLC's remark field length limit was not checked).", ""]
    with open(os.path.join(out, "ORDER_REMARK.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OR))


    summary.append(f"jlc_fab: {len(LAYERS)} Gerbers, {len(pth_hits)} plated + {len(npth_hits)} non-plated holes, "
                   f"{len(m['slots'])} slots; BOM {len(groups)} lines / {len(cpl)} parts (top {top}, bottom {bot}), "
                   f"{len(skipped)} not assembled")
    summary.append(f"  min track {fmt(m['track_min'], 3)}, min gap {fmt(overall[1][0], 3)} ({overall[0]}), outside one footprint "
                   f"{fmt(not_same[1][0], 3)} ({not_same[0]}), min drill {fmt(m['drill_min'], 3)}, via ring {fmt(m['via_ring_min'][0], 3)}, "
                   f"PTH pad ring {fmt(m['pad_ring_min'][0], 3)}, copper-edge {fmt(m['edge_min'][0], 3)}, slots "
                   f"{' '.join(fmt(s['width'], 3) for s in m['slots'])} mm")
    summary.append(f"  frame check: {chip_ok} chip parts on their Gerber pads, {tht_ok}/{tht_checked} pad holes in the drill file")
    return problems, summary


# ------------------------------------------------------------------------------------------- --check
DATE_LINES = (re.compile(rb"^%TF\.CreationDate,.*$", re.M), re.compile(rb"^G04 Created by KiCad .*$", re.M),
              re.compile(rb"^; DRILL file .*$", re.M), re.compile(rb"^; #@! TF\.CreationDate,.*$", re.M),
              re.compile(rb"/CreationDate \(D:[^)]*\)"), re.compile(rb"/ModDate \(D:[^)]*\)"))


def normalised(data):
    for rx in DATE_LINES:
        data = rx.sub(b"<date>", data)
    return data


def content(d):
    """{file name: normalised bytes}; the zip is replaced by its normalised members."""
    res = {}
    for f in sorted(os.listdir(d)):
        p = os.path.join(d, f)
        if not os.path.isfile(p):
            continue
        if f.endswith(".zip"):
            with zipfile.ZipFile(p) as z:
                for n in sorted(z.namelist()):
                    res[f + ":" + n] = normalised(z.read(n))
        else:
            with open(p, "rb") as fh:
                res[f] = normalised(fh.read())
    return res


def main(argv):
    if len(argv) >= 3 and argv[0] == "--dump":
        dump(argv[1], argv[2])
        return 0
    if os.path.exists(LOCK):
        print(f"jlc_fab: {os.path.relpath(LOCK, ROOT)} exists - the board is open in KiCad; close it first")
        return 1
    if "--check" in argv:
        if not os.path.isdir(OUT):
            print("jlc_fab: kicad_next/fab/ does not exist (run tools/next/jlc_fab.py)")
            return 1
        with tempfile.TemporaryDirectory() as tmp:
            problems, _ = generate(tmp)
            new, old = content(tmp), content(OUT)
        bad = sorted(f for f in set(new) | set(old) if new.get(f) != old.get(f))
        # the zip must hold exactly the files next to it
        for f in [k for k in old if ":" in k]:
            if old.get(f.split(":", 1)[1]) != old[f]:
                bad.append(f + " (differs from the file next to the zip)")
        for p in problems:
            print("jlc_fab: " + p)
        if bad:
            print("jlc_fab: kicad_next/fab/ is out of date (run tools/next/jlc_fab.py): " + ", ".join(bad))
        if bad or problems:
            return 1
        print(f"jlc_fab: kicad_next/fab/ up to date ({len([f for f in old if ':' not in f])} files)")
        return 0
    # generate into a temporary directory first, so a failing run leaves kicad_next/fab/ alone
    with tempfile.TemporaryDirectory() as tmp:
        problems, summary = generate(tmp)
        for p in problems:
            print("jlc_fab: ERROR " + p)
        if problems:
            return 1
        os.makedirs(OUT, exist_ok=True)
        for f in os.listdir(OUT):
            if f.startswith(NAME) or f in OWNED:
                os.remove(os.path.join(OUT, f))
        for f in sorted(os.listdir(tmp)):
            shutil.copy(os.path.join(tmp, f), os.path.join(OUT, f))
    print("\n".join(summary))
    print(f"  -> {os.path.relpath(OUT, ROOT)}/ ({len(os.listdir(OUT))} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
