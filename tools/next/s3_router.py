#!/usr/bin/env python3
"""Scripted routing engine of tube_power 5.2 routing stage 3 (used by route_s3a_power.py; system python3 with
shapely + numpy, board access through tools/p2k/bin/kipy).

A route script hands a list of STEPS to run(); every step is data:

  ("track", net, layer, width, [(x, y), ...])            drawn copper (polyline)
  ("via",   net, x, y, diameter, drill)
  ("zone",  name, net, layer, [(x, y), ...], {options})  pour (name gets the prefix of the route script)
  ("auto",  net, start, target, {options})               routed by the local grid router (below)
  ("delete", net, layer, x0, y0, x1, y1, why)            remove one existing segment (end points, 5 um)
  ("delzone", zone name, why)                            remove a 5.1 pour
  ("move", ref, x, y, {rot, side}, why)                  move a footprint (absolute; logged in moves_<tag>.json)

start / target of "auto":  "REF.PAD" | (x, y, "F.Cu") | "net" (any copper of the net that is not joined to the
start inside the window) | "via:In1.GND" etc. (shortest track to a spot where a via lands in the filled zone of
the net on that layer; the via is added).  Options: layers ("F", "B", "FB"), w (width), via (diameter, drill),
margin (window round the two ends, mm), zone_cost, relax (see below).

The grid router (0.1 mm grid, 45 degree moves, turn penalty) keeps, by construction:
  * net class clearances of the .kicad_pro, the HV functional spacing 1.2 mm on outer layers (.kicad_dru)
  * between isolation domains: the largest spacing of the pair (outer creepage = inner-layer spacing) in plan
    view to the other domain's copper on ALL layers, no slot credit (so the same-layer rules and the stage-2
    layer-to-layer rule hold; the S2_* planes are left out, route_s2_planes.py re-cuts them afterwards)
  * 0.5 mm to the board edge and slots
Connections at a barrier part, where the slot credit is needed, are drawn ("track") and judged by
check_domains.py. Every piece of copper, drawn or routed, is measured against all other copper afterwards and
anything closer than its rule is reported (drawn copper is not moved).

Re-runnable: what a script added is recorded in kicad_next/routing/<tag>_added.json and removed first on the
next run; zones carry the tag as name prefix.
"""
import collections
import heapq
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PROJ = os.path.join(ROOT, "kicad_next")
NAME = "tube_psu_5_2"
BOARD = os.path.join(PROJ, NAME + ".kicad_pcb")
LOCK = os.path.join(PROJ, "~" + NAME + ".kicad_pcb.lck")
KIPY = os.path.join(ROOT, "tools", "p2k", "bin", "kipy")
CLI = os.path.join(ROOT, "tools", "p2k", "bin", "kicad-cli")
RSS_CAP_KB = 2_950_000

CLASS_DOMAIN = {"HV_PRIMARY": "PRI", "PRIMARY_LV": "PRI", "SIGNAL": "PRI", "HV_SECONDARY": "SEC",
                "SECONDARY_LV": "SEC", "HEATER": "HEATER", "UART_ISO": "UART", "PE_EARTH": "PE"}
HV = ("HV_PRIMARY", "HV_SECONDARY")
# plan-view spacing between two domains (= outer creepage = inner-layer spacing of the .kicad_dru)
DOMAIN_GAP = {("PRI", "SEC"): 11.1, ("HEATER", "PRI"): 8.0, ("PRI", "UART"): 8.0, ("SEC", "UART"): 8.4,
              ("HEATER", "SEC"): 5.2, ("HEATER", "UART"): 1.0, ("PE", "PRI"): 3.2, ("PE", "SEC"): 4.2,
              ("HOLE", "PRI"): 3.2, ("HOLE", "SEC"): 4.2,
              # no rule in the .kicad_dru (all earthed): functional spacing used by the router
              ("HEATER", "PE"): 1.0, ("HEATER", "HOLE"): 1.0, ("PE", "UART"): 1.0, ("HOLE", "UART"): 1.0}
HEATER_SEC_LV = 1.5
HV_OUTER = 1.2
# nets of one floating high-side gate driver: 0.2 mm between them on the outer layers (.kicad_dru "High-side
# driver group ...", user decision 2026-11-20) - keep in step with the rule file
HS_GROUPS = {'DRV3': ['/06 Heaters/HEATER_HI_GATE', '/06 Heaters/HEATER_HI_SOURCE', '/06 Heaters/HEATER_HI_DRV', 'Net-(DRV3-VDDA)', 'Net-(D35-K)', 'Net-(D11-K)'], 'DRV5': ['DHB_HI_GATE', 'DHB_HI_SOURCE', 'Net-(DRV5-VDDB)', 'Net-(D19-K)', 'Net-(D30-PadA)', 'Net-(Q19-G)'], 'DRV6': ['DHB_HI_GATE_SEC', 'DHB_HI_SOURCE_SEC', 'Net-(DRV6-VDDA)', 'Net-(D18-K)', 'Net-(D31-PadA)', 'Net-(Q21-G)']}
HS_OF = {n: k for k, v in HS_GROUPS.items() for n in v}
EDGE = 0.5
HARD_ZONES = False            # True: pours of HV nets and the S3A_* zones are not crossed by other nets (stage 3b)
RELAX_OWN_DOMAIN = False      # True: "relax" never shortens a spacing to another isolation domain (stage 3b)
RELAX_GAP = 0.2               # spacing to the parts / nets named in a step's "relax" (pin-pitch escapes)
GRID = 0.1
SLACK = 0.06                  # grid margin added to every spacing while routing
OUTER = ("F.Cu", "B.Cu")
LAYER_ALIAS = {"F": "F.Cu", "B": "B.Cu", "2": "In2.Signal_HV", "3": "In3.Power"}


def log(msg):
    print("s3: " + msg, flush=True)


# =============================================================================================== kipy side
def kipy_extra(board, out):
    """outline, pad centres / kinds, rule areas"""
    import pcbnew
    b = pcbnew.LoadBoard(board)
    mm = lambda v: round(v / 1e6, 4)  # noqa: E731
    edge = pcbnew.SHAPE_POLY_SET()
    b.GetBoardPolygonOutlines(edge, True)
    g = dict(outline=[], pads=[], areas=[])
    for i in range(edge.OutlineCount()):
        o = edge.Outline(i)
        g["outline"].append([[mm(o.CPoint(k).x), mm(o.CPoint(k).y)] for k in range(o.PointCount())])
    ebb = b.GetBoardEdgesBoundingBox()
    for fp in b.GetFootprints():
        if not ebb.Contains(fp.GetPosition()):
            continue
        for p in fp.Pads():
            g["pads"].append(dict(ref=fp.GetReference(), num=p.GetNumber(), net=p.GetNetname(),
                                  x=mm(p.GetPosition().x), y=mm(p.GetPosition().y),
                                  tht=bool(p.HasHole()), smd=p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD,
                                  side="B" if fp.IsFlipped() else "F"))
    zones = list(b.Zones())
    for fp in b.GetFootprints():
        zones += list(fp.Zones())
    for z in zones:
        if z.GetIsRuleArea():
            o = z.Outline()
            g["areas"].append(dict(name=z.GetZoneName(), layers=[b.GetLayerName(l) for l in z.GetLayerSet().CuStack()],
                                   no_fill=z.GetDoNotAllowZoneFills(), no_tracks=z.GetDoNotAllowTracks(),
                                   no_vias=z.GetDoNotAllowVias(),
                                   pts=[[mm(o.Outline(0).CPoint(k).x), mm(o.Outline(0).CPoint(k).y)]
                                        for k in range(o.Outline(0).PointCount())]))
    with open(out, "w") as f:
        json.dump(g, f)


def kipy_apply(board, job):
    """remove what the last run added, then add tracks / vias / zones / rule areas of this run"""
    import pcbnew
    with open(job) as f:
        j = json.load(f)
    b = pcbnew.LoadBoard(board)
    nm = lambda v: int(round(v * 1e6))  # noqa: E731
    lid = {b.GetLayerName(l): l for l in b.GetEnabledLayers().CuStack()}
    key = lambda x, y: (round(x * 200), round(y * 200))  # noqa: E731   5 um

    def tkey(t):
        s, e = key(t.GetStart().x / 1e6, t.GetStart().y / 1e6), key(t.GetEnd().x / 1e6, t.GetEnd().y / 1e6)
        return (t.GetNetname(), b.GetLayerName(t.GetLayer()), min(s, e), max(s, e))

    old_t = set()
    old_v = set()
    for r in j["remove"]:
        if r["kind"] == "track":
            s, e = key(*r["a"]), key(*r["b"])
            old_t.add((r["net"], r["layer"], min(s, e), max(s, e)))
        elif r["kind"] == "via":
            old_v.add((r["net"], key(r["x"], r["y"])))
    n_rm = 0
    for t in list(b.GetTracks()):
        if t.Type() == pcbnew.PCB_VIA_T:
            if (t.GetNetname(), key(t.GetPosition().x / 1e6, t.GetPosition().y / 1e6)) in old_v:
                b.Delete(t)
                n_rm += 1
        elif tkey(t) in old_t:
            b.Delete(t)
            n_rm += 1
    for z in list(b.Zones()):
        if z.GetZoneName().startswith(j["prefix"]) or any(z.GetZoneName().startswith(p) for p in j["drop_areas"]):
            b.Delete(z)
            n_rm += 1
    pcbnew.SaveBoard(board, b)
    b = pcbnew.LoadBoard(board)
    lid = {b.GetLayerName(l): l for l in b.GetEnabledLayers().CuStack()}
    missing = []
    gone = []
    moved = []
    for a in j["add"]:
        if a["kind"] == "move":
            fp = b.FindFootprintByReference(a["ref"])
            was = dict(x=round(fp.GetPosition().x / 1e6, 4), y=round(fp.GetPosition().y / 1e6, 4),
                       rot=fp.GetOrientationDegrees(), side="B" if fp.IsFlipped() else "F")
            to = dict(x=a["x"], y=a["y"], rot=a.get("rot", was["rot"]), side=a.get("side", was["side"]))
            if (abs(was["x"] - to["x"]) > 1e-3 or abs(was["y"] - to["y"]) > 1e-3 or was["side"] != to["side"]
                    or abs((was["rot"] - to["rot"] + 180) % 360 - 180) > 1e-3):
                if was["side"] != to["side"]:
                    fp.Flip(fp.GetPosition(), False)
                fp.SetPosition(pcbnew.VECTOR2I(nm(to["x"]), nm(to["y"])))
                fp.SetOrientationDegrees(to["rot"])
                moved.append(dict(ref=a["ref"], frm=was, to=to, why=a["why"]))
    for a in j["add"]:
        if a["kind"] == "delzone":
            for z in list(b.Zones()):
                if z.GetZoneName() == a["name"] and not z.GetIsRuleArea():
                    bb = z.GetBoundingBox()
                    gone.append(dict(kind="zone", zone=a["name"], net=z.GetNetname(),
                                     layer=[b.GetLayerName(l) for l in z.GetLayerSet().CuStack()][0],
                                     bbox=[round(v / 1e6, 2) for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())],
                                     reason=a["why"]))
                    b.Delete(z)
        if a["kind"] == "delete":
            s, e = key(*a["a"]), key(*a["b"])
            want = (a["net"], a["layer"], min(s, e), max(s, e))
            hit = [t for t in b.GetTracks() if t.Type() != pcbnew.PCB_VIA_T and tkey(t) == want]
            for t in hit:
                gone.append(dict(kind="segment", net=a["net"], layer=a["layer"], start=a["a"], end=a["b"],
                                 width=round(t.GetWidth() / 1e6, 4), reason=a.get("why", "")))
                b.Delete(t)
            if not hit:
                missing.append(a)
    if any(a["kind"] in ("delete", "delzone", "move") for a in j["add"]):
        pcbnew.SaveBoard(board, b)
        b = pcbnew.LoadBoard(board)
        lid = {b.GetLayerName(l): l for l in b.GetEnabledLayers().CuStack()}
    for a in j["add"]:
        code = b.GetNetcodeFromNetname(a.get("net", "")) if a.get("net") else 0
        if a["kind"] == "track":
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(pcbnew.VECTOR2I(nm(a["a"][0]), nm(a["a"][1])))
            t.SetEnd(pcbnew.VECTOR2I(nm(a["b"][0]), nm(a["b"][1])))
            t.SetWidth(nm(a["w"]))
            t.SetLayer(lid[a["layer"]])
            t.SetNetCode(code)
            b.Add(t)
        elif a["kind"] == "via":
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(pcbnew.VECTOR2I(nm(a["x"]), nm(a["y"])))
            v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            v.SetWidth(pcbnew.F_Cu, nm(a["d"]))
            v.SetDrill(nm(a["drill"]))
            v.SetNetCode(code)
            b.Add(v)
        elif a["kind"] in ("zone", "area"):
            z = pcbnew.ZONE(b)
            z.SetZoneName(a["name"])
            ls = pcbnew.LSET()
            for l in a["layers"]:
                ls.AddLayer(lid[l])
            z.SetLayerSet(ls)
            if a["kind"] == "area":
                z.SetIsRuleArea(True)
                z.SetDoNotAllowZoneFills(True)
                z.SetDoNotAllowTracks(False)
                z.SetDoNotAllowVias(False)
                z.SetDoNotAllowPads(False)
                z.SetDoNotAllowFootprints(False)
            else:
                o = a.get("opt", {})
                z.SetNetCode(code)
                z.SetAssignedPriority(int(o.get("priority", 90)))
                z.SetLocalClearance(nm(o.get("clearance", 0.2)))
                z.SetMinThickness(nm(o.get("min_width", 0.25)))
                z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL if o.get("solid") else
                                   pcbnew.ZONE_CONNECTION_THT_THERMAL)    # SMD pads / vias solid, THT pins relieved
                z.SetThermalReliefGap(nm(0.3))
                z.SetThermalReliefSpokeWidth(nm(o.get("spoke", 0.8)))
                z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
                z.SetFillMode(pcbnew.ZONE_FILL_MODE_POLYGONS)
            ol = z.Outline()
            ol.NewOutline()
            for x, y in a["pts"]:
                ol.Append(nm(x), nm(y))
            for h, hole in enumerate(a.get("holes", [])):
                ol.NewHole()
                for x, y in hole:
                    ol.Append(nm(x), nm(y), -1, h)
            b.Add(z)
    if any(a["kind"] not in ("delete", "delzone", "move") for a in j["add"]):
        # stale fills off: on loading, KiCad gives a via standing in the old fill of another net that net
        for z in b.Zones():
            if not z.GetIsRuleArea():
                z.UnFill()
    pcbnew.SaveBoard(board, b)
    print(json.dumps(dict(removed=n_rm, delete_missing=missing, gone=gone, moved=moved)))


# =============================================================================================== world
class World:
    def __init__(self, g, x, classes):
        from shapely.geometry import Polygon
        from shapely.ops import unary_union
        self.layers = g["layers"]
        self.cls = classes
        self.items = collections.defaultdict(list)      # layer -> [(geom, net, kind)]
        self.pads = collections.defaultdict(list)        # "REF.NUM" -> [extra pad dict]
        self.smd = []                                    # (geom, net) SMD pads (no via inside)
        self.zone = collections.defaultdict(list)        # (layer, net) -> [geom]
        self.zname = {}

        def mk(pp):
            return unary_union([Polygon(ring, holes).buffer(0) for ring, holes in pp])

        tht = {}
        for p in x["pads"]:
            self.pads[f"{p['ref']}.{p['num']}"].append(p)
            tht[(p["ref"], p["num"])] = p["tht"]
        for p in g["pads"]:
            geom = mk(p["polys"])
            net = p["net"]
            kind = "hole" if p["ref"][0] == "H" and p["ref"][1:].isdigit() else "pad"
            if not tht.get((p["ref"], p["num"]), False):
                self.smd.append((geom, net, p["layers"][0]))
            elif kind == "pad":
                kind = "pad-tht"       # on every layer: a pair with it is judged on the common layer
            for l in p["layers"]:
                self.items[l].append((geom, net, kind, p["ref"]))
        from shapely.geometry import LineString, Point
        for t in g["tracks"]:
            x0, y0, x1, y1 = t["pts"]
            geom = (LineString([(x0, y0), (x1, y1)]) if (x0, y0) != (x1, y1) else Point(x0, y0)).buffer(t["w"] / 2, 8)
            self.items[t["layer"]].append((geom, t["net"], "track", ""))
        for v in g["vias"]:
            geom = Point(v["x"], v["y"]).buffer(v["d"] / 2, 16)
            for l in v["layers"]:
                self.items[l].append((geom, v["net"], "via", ""))
        for z in g["zones"]:
            for ring, holes in z["polys"]:              # one item per filled island
                geom = Polygon(ring, holes).buffer(0)
                self.zone[(z["layer"], z["net"])].append(geom)
                self.items[z["layer"]].append((geom, z["net"], "zone:" + z["name"], ""))
        self.slots = unary_union([Polygon(s).buffer(0) for s in g["slots"]]) if g["slots"] else None
        outline = unary_union([Polygon(o).buffer(0) for o in x["outline"]])
        self.board = outline if self.slots is None else outline.difference(self.slots)
        self.areas = x["areas"]
        self._tree = {}

    # ---------------------------------------------------------------------------------- rules
    def domain(self, net, kind="", ref=""):
        if kind == "hole":
            return "HOLE"
        return CLASS_DOMAIN.get(self.cls.get(net, ""), "")

    def gap(self, net, layer, o_net, o_kind):
        """required copper-to-copper spacing between `net` on `layer` and another item on the same layer"""
        da, db = self.domain(net), self.domain(o_net, o_kind)
        ca, cb = self.cls.get(net, ""), self.cls.get(o_net, "")
        if da and db and da != db:
            if {da, db} == {"HEATER", "SEC"} and "SECONDARY_LV" in (ca, cb):
                return HEATER_SEC_LV
            return DOMAIN_GAP.get((da, db), DOMAIN_GAP.get((db, da), 0.2))
        if layer in OUTER and net in HS_OF and HS_OF[net] == HS_OF.get(o_net):
            return 0.2
        if layer in OUTER and (ca in HV or cb in HV):
            return HV_OUTER
        c = {"HV_PRIMARY": 0.5, "HV_SECONDARY": 0.5, "PE_EARTH": 0.5, "PRIMARY_LV": 0.2, "SECONDARY_LV": 0.2,
             "HEATER": 0.2}
        return max(c.get(ca, 0.15), c.get(cb, 0.15), 0.2 if not o_net else 0)

    def add(self, layer, geom, net, kind):
        self.items[layer].append((geom, net, kind, ""))
        self._tree.pop(layer, None)

    def tree(self, layer):
        from shapely.strtree import STRtree
        if layer not in self._tree:
            self._tree[layer] = STRtree([i[0] for i in self.items[layer]])
        return self._tree[layer]

    def near(self, layer, box):
        from shapely.geometry import box as mkbox
        return [self.items[layer][k] for k in self.tree(layer).query(mkbox(*box))]

    # ---------------------------------------------------------------------------------- checks
    def violations(self, net, layer, geom, what, relax=(), fgap=None):
        """every other-net item closer to geom than its rule: [(distance, need, description)]"""
        out = []
        b = geom.bounds
        mydom = self.domain(net)
        for l in self.layers:
            for og, on, ok, oref in self.near(l, (b[0] - 12, b[1] - 12, b[2] + 12, b[3] + 12)):
                if on == net:
                    continue
                od = self.domain(on, ok)
                foreign = bool(mydom and od and od != mydom)
                if ok.startswith("zone:") and ("S2_" in ok or not foreign or mydom == "PE"):
                    continue        # refilled by KiCad with the rules / re-cut by route_s2_planes.py / PE keep-outs
                if l != layer and (not foreign or ok in ("pad-tht", "via", "hole")):
                    continue        # through items are met on the own layer
                need = self.gap(net, layer if l == layer else "inner", on, ok)
                if (oref in relax or on in relax) and not (RELAX_OWN_DOMAIN and foreign):
                    need = min(need, RELAX_GAP)
                if fgap and foreign and l in OUTER and layer in OUTER:
                    need = min(need, fgap)       # slot credit claimed: judged by check_domains.py
                d = geom.distance(og)
                if d < need - 1e-3:
                    out.append((round(d, 3), need, f"{what} [{net}] {layer} <-> {ok} {oref} [{on}] {l}"))
        if not self.board.contains(geom.buffer(0.3 - 1e-3)):
            out.append((0, 0.3, f"{what} [{net}] {layer} <-> board edge / slot"))
        return out


# =============================================================================================== router
DIRS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]


class Router:
    def __init__(self, world):
        self.w = world
        self.out = []          # added items
        self.report = []       # per step
        self.warn = []

    # ------------------------------------------------------------------ explicit copper
    def track(self, net, layer, width, pts, what="track", relax=(), fgap=None):
        from shapely.geometry import LineString
        layer = LAYER_ALIAS.get(layer, layer)
        for a, b in zip(pts, pts[1:]):
            if math.hypot(a[0] - b[0], a[1] - b[1]) < 1e-4:
                continue
            geom = LineString([a, b]).buffer(width / 2, 8)
            for v in self.w.violations(net, layer, geom, what, relax, fgap):
                self.warn.append(v)
            self.w.add(layer, geom, net, "track")
            self.out.append(dict(kind="track", net=net, layer=layer, w=width, a=[round(a[0], 4), round(a[1], 4)],
                                 b=[round(b[0], 4), round(b[1], 4)]))

    def via(self, net, x, y, d, drill, what="via", relax=(), fgap=None):
        from shapely.geometry import Point
        geom = Point(x, y).buffer(d / 2, 16)
        seen = set()
        for l in self.w.layers:
            for v in self.w.violations(net, l, geom, what, relax, fgap):
                if v[2].split("<->")[1] not in seen:
                    seen.add(v[2].split("<->")[1])
                    self.warn.append(v)
        for l in self.w.layers:
            self.w.add(l, geom, net, "via")
        self.out.append(dict(kind="via", net=net, x=round(x, 4), y=round(y, 4), d=d, drill=drill))

    # ------------------------------------------------------------------ grid
    def _mask(self, geom, X, Y):
        import shapely
        if geom is None or geom.is_empty:
            import numpy as np
            return np.zeros(X.shape, bool)
        return shapely.contains_xy(geom, X, Y)

    def _blocked(self, net, layer, half, box, relax=(), fgap=None):
        """(hard obstacle geometry, soft geometry) for a track / via of half width `half` of `net` on `layer`"""
        from shapely.ops import unary_union
        w = self.w
        mydom = w.domain(net)
        hard, soft = [], []
        pad = 12.0 if mydom else 1.5
        for l in w.layers:
            for og, on, ok, oref in w.near(l, (box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad)):
                if on == net:
                    continue
                od = w.domain(on, ok)
                foreign = bool(mydom and od and od != mydom)
                if l != layer and (not foreign or ok in ("pad-tht", "via", "hole")):
                    continue
                if ok.startswith("zone:"):
                    if "S2_" in ok or (foreign and mydom == "PE"):
                        continue                       # planes: re-cut by route_s2_planes.py; PE: pour keep-outs
                    if not foreign:
                        if l == layer:
                            if HARD_ZONES and (ok.startswith("zone:S3A_") or w.cls.get(on, "") in HV):
                                hard.append(og.buffer(w.gap(net, layer, on, ok) + half + SLACK, 4))   # never cut / push back a HV or stage-3a pour
                            else:
                                soft.append(og)
                        continue
                need = w.gap(net, layer if l == layer else "inner", on, ok)
                if (oref in relax or on in relax) and not (RELAX_OWN_DOMAIN and foreign):
                    need = min(need, RELAX_GAP)
                if fgap and foreign and l in OUTER and layer in OUTER:
                    need = min(need, fgap)
                hard.append(og.buffer(need + half + SLACK, 8))
        return unary_union(hard) if hard else None, unary_union(soft) if soft else None

    def auto(self, net, start, target, opt):
        import numpy as np
        from shapely.geometry import Point, box as mkbox
        from shapely.ops import unary_union
        w = self.w
        width = opt.get("w", 0.3)
        vd, vdrill = opt.get("via", (0.8, 0.4))
        allow = [LAYER_ALIAS[c] for c in opt.get("layers", "FB")]
        relax = tuple(opt.get("relax", ()))
        fgap = opt.get("foreign_gap")
        what = f"auto {start} -> {target}"

        def endpoint(e):
            """-> (x, y, [layers], geometry or None)"""
            if isinstance(e, str) and e != "net" and not e.startswith("via:"):
                ps = w.pads[e]
                if not ps:
                    raise SystemExit(f"s3: no pad {e}")
                p = ps[0]
                if p["net"] != net:
                    raise SystemExit(f"s3: pad {e} is on [{p['net']}], not [{net}]")
                ls = allow if p["tht"] else [LAYER_ALIAS[p["side"]]]
                geom = None
                for og, on, ok, oref in w.near(ls[0], (p["x"] - 0.01, p["y"] - 0.01, p["x"] + 0.01, p["y"] + 0.01)):
                    if ok.startswith("pad") and on == net and og.contains(Point(p["x"], p["y"])):
                        geom = og
                return p["x"], p["y"], ls, geom
            x, y, l = e
            return x, y, [LAYER_ALIAS.get(l, l)], None

        sx, sy, sl, sgeom = endpoint(start)
        pts = [(sx, sy)]
        tgt_pad = None
        if isinstance(target, str) and (target == "net" or target.startswith("via:")):
            pass
        else:
            tgt_pad = endpoint(target)
            pts.append(tgt_pad[:2])
        for wp in opt.get("window", []):
            pts.append(wp)
        m = opt.get("margin", 4.0)
        x0, y0 = min(p[0] for p in pts) - m, min(p[1] for p in pts) - m
        x1, y1 = max(p[0] for p in pts) + m, max(p[1] for p in pts) + m
        nx, ny = int(round((x1 - x0) / GRID)) + 1, int(round((y1 - y0) / GRID)) + 1
        xs, ys = x0 + GRID * np.arange(nx), y0 + GRID * np.arange(ny)
        X, Y = np.meshgrid(xs, ys, indexing="ij")
        box = (x0, y0, x1, y1)
        inside = self._mask(w.board.buffer(-(EDGE + width / 2)), X, Y)
        from shapely.geometry import Polygon
        free, cost, own = {}, {}, {}
        for l in allow:
            hard, soft = self._blocked(net, l, width / 2, box, relax, fgap)
            f = inside & ~self._mask(hard, X, Y)
            for ar in w.areas:                         # rule areas "no tracks" (TR3 barrier band)
                if ar["no_tracks"] and l in ar["layers"]:
                    f &= ~self._mask(Polygon(ar["pts"]).buffer(width / 2 + SLACK), X, Y)
            for kx0, ky0, kx1, ky1 in opt.get("avoid", []) + opt.get("avoid_on", {}).get(l, []):
                f &= ~((X >= kx0) & (X <= kx1) & (Y >= ky0) & (Y <= ky1))
            c = np.ones(X.shape)
            c[self._mask(soft, X, Y)] = opt.get("zone_cost", 4.0)
            mine = [og for og, on, ok, oref in w.near(l, box) if on == net and not ok.startswith("zone:S2_")]
            o = self._mask(unary_union(mine) if mine else None, X, Y)
            c[o] = 0.6
            free[l], cost[l], own[l] = f, c, o
        # via sites
        via_ok = None
        need_via = len(allow) > 1 or (isinstance(target, str) and target.startswith("via:"))
        if need_via:
            via_ok = self._mask(w.board.buffer(-(EDGE + vd / 2)), X, Y)
            for l in w.layers:
                hard, _ = self._blocked(net, l, vd / 2, box, relax, fgap)
                via_ok &= ~self._mask(hard, X, Y)
            smd = [og.buffer(vd / 2 + 0.1) for og, on, ol in w.smd if og.intersects(mkbox(*box))]
            via_ok &= ~self._mask(unary_union(smd) if smd else None, X, Y)
            # holes of the own net (vias, pins): no second hole on or next to one
            holes = [og.buffer(vd / 2 + 0.25) for og, on, ok, oref in w.near(w.layers[0], box)
                     if on == net and ok in ("via", "pad-tht")]
            via_ok &= ~self._mask(unary_union(holes) if holes else None, X, Y)
            for ar in w.areas:
                if ar["no_vias"]:
                    via_ok &= ~self._mask(Polygon(ar["pts"]).buffer(vd / 2 + SLACK), X, Y)
            for a in w.areas:
                if a["name"] == "S2_KO_TR1_pin2" and net == "GND":
                    from shapely.geometry import Polygon
                    via_ok &= ~self._mask(Polygon(a["pts"]).buffer(vd / 2 + 0.3), X, Y)
            for kx0, ky0, kx1, ky1 in opt.get("no_via", []):
                via_ok &= ~((X >= kx0) & (X <= kx1) & (Y >= ky0) & (Y <= ky1))
        # start
        si, sj = int(round((sx - x0) / GRID)), int(round((sy - y0) / GRID))
        # target masks per layer
        tmask = {}
        end_via = False
        if isinstance(target, str) and target.startswith("via:"):
            end_via = True
            zl = target[4:]
            zl = LAYER_ALIAS.get(zl, zl)
            zg = w.zone.get((zl, net), [])
            if not zg:
                raise SystemExit(f"s3: {what}: no filled zone of [{net}] on {zl}")
            zin = unary_union(zg).buffer(-(vd / 2 + opt.get("plane_inset", 0.25)))
            tm = via_ok & self._mask(zin, X, Y)
            # a via / pin of the net that already stands in that fill is as good: end there, no new via
            have = [og.buffer(-0.1) for og, on, ok, oref in w.near(w.layers[0], box)
                    if on == net and ok in ("via", "pad-tht") and zin.contains(og.centroid)]
            reuse = self._mask(unary_union(have) if have else None, X, Y)
            for l in sl:
                tmask[l] = tm | reuse
        elif target == "net":
            pass
        else:
            tx, ty, tl, tgeom = tgt_pad
            for l in tl:
                if l not in allow:
                    continue
                if tgeom is not None:
                    core = tgeom.buffer(-min(width / 2, 0.25))
                    tm = self._mask(core, X, Y) if not core.is_empty else np.zeros(X.shape, bool)
                else:
                    tm = np.zeros(X.shape, bool)
                ti, tj = int(round((tx - x0) / GRID)), int(round((ty - y0) / GRID))
                tm[ti, tj] = True
                tmask[l] = tm
        if target == "net":
            tmask = self._other_islands(net, allow, own, X, Y, box, (si, sj), sl)
        if not any(tm.any() for tm in tmask.values()):
            self.warn.append((0, 0, f"{what}: no target cell in the window"))
            self.report.append(dict(step=what, net=net, ok=False))
            return False
        # A* over (layer, i, j, dir)
        lidx = {l: k for k, l in enumerate(allow)}
        tb = [np.argwhere(tmask[l]) for l in allow if l in tmask and tmask[l].any()]
        tb = np.vstack(tb)
        bi0, bj0, bi1, bj1 = tb[:, 0].min(), tb[:, 1].min(), tb[:, 0].max(), tb[:, 1].max()

        def h(i, j):
            dx = max(bi0 - i, 0, i - bi1)
            dy = max(bj0 - j, 0, j - bj1)
            return 0.6 * (max(dx, dy) + 0.414 * min(dx, dy))

        via_cost = opt.get("via_cost", 30.0)
        turn = opt.get("turn", 1.5)
        heap = []
        best = {}
        for l in sl:
            if l in lidx:
                st = (lidx[l], si, sj, 8)
                best[st] = 0.0
                heapq.heappush(heap, (h(si, sj), 0.0, st, None))
        prev = {}
        goal = None
        fl = [free[l] for l in allow]
        cl = [cost[l] for l in allow]
        ol = [own[l] for l in allow]
        tml = [tmask.get(l) for l in allow]
        # the start cell and own copper are always passable (the track leaves its own pad)
        while heap:
            f, gc, st, pv = heapq.heappop(heap)
            if best.get(st, 1e18) < gc - 1e-9:
                continue
            if st in prev:
                continue
            prev[st] = pv
            k, i, j, d = st
            if tml[k] is not None and tml[k][i, j]:
                goal = st
                break
            for nd, (di, dj) in enumerate(DIRS):
                if d != 8:
                    dd = min((nd - d) % 8, (d - nd) % 8)
                    if dd > 2:
                        continue
                else:
                    dd = 0
                ni, nj = i + di, j + dj
                if ni < 0 or nj < 0 or ni >= nx or nj >= ny:
                    continue
                if not (fl[k][ni, nj] or ol[k][ni, nj]):
                    continue
                step = (1.0 if di == 0 or dj == 0 else 1.4142) * cl[k][ni, nj] + turn * dd
                ns = (k, ni, nj, nd)
                ng = gc + step
                if ng < best.get(ns, 1e18) - 1e-9:
                    best[ns] = ng
                    heapq.heappush(heap, (ng + h(ni, nj), ng, ns, st))
            if via_ok is not None and len(allow) > 1 and via_ok[i, j]:
                for k2 in range(len(allow)):
                    if k2 != k and (fl[k2][i, j] or ol[k2][i, j]):
                        ns = (k2, i, j, 8)
                        ng = gc + via_cost
                        if ng < best.get(ns, 1e18) - 1e-9:
                            best[ns] = ng
                            heapq.heappush(heap, (ng + h(i, j), ng, ns, st))
        if goal is None:
            near = min(prev, key=lambda st: h(st[1], st[2])) if prev else None
            got = (f", {len(prev)} states, got as far as ({x0 + near[1] * GRID:.1f}, {y0 + near[2] * GRID:.1f}) "
                   f"on {allow[near[0]]}, target box ({x0 + bi0 * GRID:.1f}, {y0 + bj0 * GRID:.1f}) ... "
                   f"({x0 + bi1 * GRID:.1f}, {y0 + bj1 * GRID:.1f})") if near else ""
            self.warn.append((0, 0, f"{what}: NO ROUTE (window {x0:.1f},{y0:.1f} ... {x1:.1f},{y1:.1f}){got}"))
            self.report.append(dict(step=what, net=net, ok=False))
            return False
        path = []
        st = goal
        while st is not None:
            path.append(st)
            st = prev[st]
        path.reverse()
        # to polylines per layer + vias
        length = 0.0
        nvia = 0
        cur = [(sx, sy)]
        curl = path[0][0]

        def flush():
            nonlocal cur, length
            # drop collinear points
            pp = [cur[0]]
            for q in cur[1:]:
                if len(pp) >= 2:
                    ax, ay = pp[-1][0] - pp[-2][0], pp[-1][1] - pp[-2][1]
                    bx, by = q[0] - pp[-1][0], q[1] - pp[-1][1]
                    if abs(ax * by - ay * bx) < 1e-9 and ax * bx + ay * by > 0:
                        pp[-1] = q
                        continue
                if math.hypot(q[0] - pp[-1][0], q[1] - pp[-1][1]) > 1e-6:
                    pp.append(q)
            if len(pp) > 1:
                self.track(net, allow[curl], width, pp, what, relax, fgap)
                length += sum(math.hypot(a[0] - b[0], a[1] - b[1]) for a, b in zip(pp, pp[1:]))
            cur = []

        for (k, i, j, d) in path:
            p = (round(x0 + i * GRID, 4), round(y0 + j * GRID, 4))
            if k != curl:
                flush()
                self.via(net, p[0], p[1], vd, vdrill, what, relax, fgap)
                nvia += 1
                curl = k
                cur = [p]
            else:
                cur.append(p)
        last = cur[-1] if cur else None
        flush()
        if end_via and last is not None and not reuse[path[-1][1], path[-1][2]]:
            self.via(net, last[0], last[1], vd, vdrill, what, relax, fgap)
            nvia += 1
        self.report.append(dict(step=what, net=net, ok=True, w=width, length=round(length, 2), vias=nvia,
                                layers=sorted({allow[s[0]] for s in path})))
        return True

    def _other_islands(self, net, allow, own, X, Y, box, start, sl):
        """target masks: own copper not joined to the start inside the window"""
        import numpy as np
        w = self.w
        from shapely.geometry import box as mkbox
        # connectivity over geometry: items of the net on all layers in the window (+ 3 mm)
        bb = mkbox(box[0] - 3, box[1] - 3, box[2] + 3, box[3] + 3)
        nodes = []
        for l in w.layers:
            for og, on, ok, oref in w.near(l, bb.bounds):
                if on == net:
                    nodes.append((l, og, ok))
        n = len(nodes)
        par = list(range(n))

        def find(a):
            while par[a] != a:
                par[a] = par[par[a]]
                a = par[a]
            return a

        for a in range(n):
            la, ga, ka = nodes[a]
            for b in range(a + 1, n):
                lb, gb, kb = nodes[b]
                if (la == lb and ga.intersects(gb)) or (la != lb and ga is gb):
                    ra, rb = find(a), find(b)
                    if ra != rb:
                        par[ra] = rb
        from shapely.geometry import Point
        sp = Point(X[start], Y[start])
        mine = {find(a) for a in range(n) if nodes[a][0] in sl and nodes[a][1].buffer(0.02).contains(sp)}
        from shapely.ops import unary_union
        tm = {}
        for l in allow:
            other = [g.buffer(-0.03) for a, (ll, g, k) in enumerate(nodes) if ll == l and find(a) not in mine]
            other = [g for g in other if not g.is_empty]
            tm[l] = self._mask(unary_union(other) if other else None, X, Y)
        return tm


# =============================================================================================== driver
def cli(args):
    pr = subprocess.Popen([CLI] + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    peak = 0
    while pr.poll() is None:
        try:
            pids = [pr.pid] + [int(x) for x in subprocess.run(["pgrep", "-P", str(pr.pid)], capture_output=True,
                                                               text=True).stdout.split()]
            for pid in pids:
                with open(f"/proc/{pid}/status") as f:
                    peak = max(peak, next((int(l.split()[1]) for l in f if l.startswith("VmRSS:")), 0))
        except (OSError, ValueError):
            pass
        if peak > RSS_CAP_KB:
            pr.kill()
            sys.exit(f"s3: kicad-cli above {RSS_CAP_KB} kB, killed")
        try:
            pr.wait(timeout=0.2)
        except subprocess.TimeoutExpired:
            pass
    return pr.returncode, peak


def net_classes():
    with open(os.path.join(PROJ, NAME + ".kicad_pro")) as f:
        pro = json.load(f)
    return {p["pattern"]: p["netclass"] for p in pro["net_settings"]["netclass_patterns"]}


def load_world(pcb, tmp):
    js, xs = os.path.join(tmp, "g.json"), os.path.join(tmp, "x.json")
    for args in ([KIPY, os.path.join(HERE, "check_domains.py"), "--dump", pcb, js],
                 [KIPY, os.path.abspath(__file__), "--extra", pcb, xs]):
        r = subprocess.run(args, capture_output=True, text=True)
        if r.returncode:
            sys.exit("s3: board dump failed\n" + r.stdout[-2000:] + r.stderr[-2000:])
    with open(js) as f:
        g = json.load(f)
    with open(xs) as f:
        x = json.load(f)
    return World(g, x, net_classes())


def run(tag, groups, argv, drop_areas=(), post=None):
    """groups: [(group name, [steps])]. Writes the board in place (or --dry-run OUT), records what it added."""
    if os.path.exists(LOCK):
        sys.exit(f"s3: {os.path.relpath(LOCK, ROOT)} exists - the board is open in KiCad; close it first")
    added_log = os.path.join(PROJ, "routing", f"{tag}_added.json")
    old = []
    if os.path.exists(added_log):
        with open(added_log) as f:
            old = json.load(f)["added"]
    prefix = tag.upper() + "_"
    tmp = tempfile.mkdtemp(prefix=".s3_", dir=ROOT)
    try:
        for ext in (".kicad_pcb", ".kicad_dru"):
            shutil.copy(os.path.join(PROJ, NAME + ext), tmp)
        with open(os.path.join(PROJ, NAME + ".kicad_pro")) as f:
            pro = json.load(f)
        rs = pro["board"]["design_settings"]["rule_severities"]
        for k in rs:
            rs[k] = "ignore"
        with open(os.path.join(tmp, NAME + ".kicad_pro"), "w") as f:
            json.dump(pro, f, indent=2)
        pcb = os.path.join(tmp, NAME + ".kicad_pcb")
        job = os.path.join(tmp, "job.json")

        def apply(add, remove):
            with open(job, "w") as f:
                json.dump(dict(prefix=prefix, drop_areas=list(drop_areas), remove=remove, add=add), f)
            r = subprocess.run([KIPY, os.path.abspath(__file__), "--apply", pcb, job], capture_output=True, text=True)
            if r.returncode:
                sys.exit("s3: apply failed\n" + r.stdout[-3000:] + r.stderr[-3000:])
            return json.loads(r.stdout.strip().splitlines()[-1])

        res = apply([], old)                      # strip the previous run
        log(f"removed {res['removed']} items of the previous {tag} run")
        if "--strip" in argv:                      # only take the copper of this script off the board
            if os.path.exists(LOCK):
                sys.exit("s3: the board was opened in KiCad meanwhile - not written")
            shutil.copy(pcb, BOARD)
            with open(added_log, "w") as f:
                json.dump(dict(note=f"copper added by tools/next/route_{tag}_*.py (stripped)", added=[], report=[]), f, indent=1)
                f.write("\n")
            log(f"stripped: wrote {os.path.relpath(BOARD, ROOT)}")
            return None
        pre = []
        for gname, steps in groups:
            for s in steps:
                if s[0] == "delete":
                    pre.append(dict(kind="delete", net=s[1], layer=LAYER_ALIAS.get(s[2], s[2]), a=[s[3], s[4]],
                                    b=[s[5], s[6]], why=s[7]))
                elif s[0] == "delzone":
                    pre.append(dict(kind="delzone", name=s[1], why=s[2]))
                elif s[0] == "move":
                    pre.append(dict(kind="move", ref=s[1], x=s[2], y=s[3], why=s[5], **s[4]))
        res = apply(pre, []) if pre else dict(gone=[], moved=[])
        gone, moved = res["gone"], res["moved"]
        for m in moved:
            log(f"moved {m['ref']} {m['frm']} -> {m['to']}: {m['why']}")
        for x in gone:
            log(f"deleted {x['kind']} [{x['net']}] {x['layer']} {x.get('zone', '')}{x.get('start', '')}: {x['reason']}")
        world = load_world(pcb, tmp)
        rt = Router(world)
        deletes = []
        zones = []
        summary = []
        for gname, steps in groups:
            n0 = len(rt.report)
            for s in steps:
                kind = s[0]
                if kind == "track":
                    _, net, layer, width, pts = s[:5]
                    o = s[5] if len(s) > 5 else {}
                    rt.track(net, layer, width, pts, f"track {gname}", o.get("relax", ()), o.get("foreign_gap"))
                    rt.report.append(dict(step=f"track {pts[0]} ... {pts[-1]}", net=net, ok=True, w=width, vias=0,
                                          length=round(sum(math.hypot(a[0] - b[0], a[1] - b[1])
                                                           for a, b in zip(pts, pts[1:])), 2),
                                          layers=[LAYER_ALIAS.get(layer, layer)]))
                elif kind == "via":
                    _, net, x, y, d, drill = s[:6]
                    o = s[6] if len(s) > 6 else {}
                    rt.via(net, x, y, d, drill, f"via {gname}", o.get("relax", ()), o.get("foreign_gap"))
                    rt.report.append(dict(step=f"via ({x}, {y})", net=net, ok=True, w=0, length=0, vias=1, layers=[]))
                elif kind == "zone":
                    _, name, net, layer, pts, o = s
                    zones.append(dict(kind="zone", name=prefix + name, net=net, layers=[LAYER_ALIAS.get(layer, layer)],
                                      pts=pts, opt=o))
                elif kind == "auto":
                    _, net, a, b, o = s
                    rt.auto(net, a, b, o)
                elif kind in ("delete", "delzone", "move"):
                    pass                                   # done before the board was read
                else:
                    sys.exit(f"s3: unknown step {s!r}")
            for r in rt.report[n0:]:
                r["group"] = gname
            summary.append(gname)
        extra = post(world, rt) if post else []
        res = apply(deletes + rt.out + zones + extra, [])
        rc, peak = cli(["pcb", "drc", "--format", "json", "--refill-zones", "--save-board",
                        "-o", os.path.join(tmp, "refill.json"), pcb])
        if rc != 0:
            sys.exit("s3: zone refill failed, the board is unchanged")
        log(f"zones refilled by kicad-cli (peak RSS {peak // 1024} MB)")
        # report
        by = collections.defaultdict(list)
        for r in rt.report:
            by[r["group"]].append(r)
        for gname in summary:
            rs_ = by[gname]
            ok = [r for r in rs_ if r["ok"]]
            log(f"group {gname}: {len(ok)}/{len(rs_)} steps, {sum(r['length'] for r in ok):.1f} mm, "
                f"{sum(r['vias'] for r in ok)} vias")
            for r in rs_:
                if not r["ok"]:
                    log(f"   FAILED {r['step']} [{r['net']}]")
        for d, need, txt in sorted(set(rt.warn), key=lambda v: v[2]):
            log(f"   WARN {txt}: {d} mm < {need} mm" if need else f"   WARN {txt}")
        log(f"{len(rt.out)} tracks / vias, {len(zones)} zones, {len(extra)} rule areas, {len(set(rt.warn))} warnings")
        if "--dry-run" in argv:
            keep = os.path.abspath(argv[argv.index("--dry-run") + 1])
            shutil.copy(pcb, keep)
            log(f"dry run: result in {keep}, the board is unchanged")
            return rt
        if os.path.exists(LOCK):
            sys.exit("s3: the board was opened in KiCad meanwhile - not written")
        shutil.copy(pcb, BOARD)
        dlog = os.path.join(PROJ, "routing", f"deleted_{tag}.json")
        oldg = []
        if os.path.exists(dlog):
            with open(dlog) as f:
                oldg = json.load(f)["deleted"]
        seen = {json.dumps(x, sort_keys=True) for x in oldg}
        newg = [x for x in gone if json.dumps(x, sort_keys=True) not in seen]
        if newg or not os.path.exists(dlog):
            with open(dlog, "w") as f:
                json.dump(dict(note=f"5.1 copper deleted by the {tag} route script (mm)", deleted=oldg + newg), f, indent=1)
                f.write("\n")
        mlog = os.path.join(PROJ, "routing", f"moves_{tag}.json")
        oldm = []
        if os.path.exists(mlog):
            with open(mlog) as f:
                oldm = json.load(f)["moves"]
        if moved or not os.path.exists(mlog):
            have = {m["ref"]: m for m in oldm}
            for m in moved:                       # a part moved twice keeps its first "from"
                if m["ref"] in have:
                    have[m["ref"]].update(to=m["to"], why=m["why"])
                else:
                    oldm.append(m)
            with open(mlog, "w") as f:
                json.dump(dict(note=f"footprints moved by the {tag} route script (mm, degrees)", moves=oldm), f, indent=1)
                f.write("\n")
        with open(added_log, "w") as f:
            json.dump(dict(note=f"copper added by tools/next/route_{tag}_*.py (removed and rebuilt on a re-run)",
                           added=rt.out, report=rt.report), f, indent=1)
            f.write("\n")
        log(f"wrote {os.path.relpath(BOARD, ROOT)} and {os.path.relpath(added_log, ROOT)}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return rt


if __name__ == "__main__":
    if "--extra" in sys.argv:
        i = sys.argv.index("--extra")
        kipy_extra(sys.argv[i + 1], sys.argv[i + 2])
    elif "--apply" in sys.argv:
        i = sys.argv.index("--apply")
        kipy_apply(sys.argv[i + 1], sys.argv[i + 2])
