#!/usr/bin/env python3
"""Isolation-domain distance check of a 5.2 board (python3 + shapely; reads the board through tools/p2k/bin/kipy).

    python3 tools/next/check_domains.py [BOARD.kicad_pcb] [--all] [--json FILE]

Default board: the latest step of the trial board, kicad_next/trial_from_51/tube_psu_5_2_trial[_pN].kicad_pcb
(its .kicad_pro next to it gives the net classes).

Why: KiCad's creepage DRC does not list every pair (trial_from_51/REPORT.md, step 3 note 0; check_rules.py has
test spots where it reports nothing), and the full creepage DRC of the board needs about 2.5 GB. This script
measures the straight distance between every two copper items of different isolation domains on the same
layer - pads (true shapes), tracks, vias, the filled zone copper as stored in the board, and the mounting holes
H1-H8 as protective earth (the 6 mm head / standoff of the earthed M3 screw, a disc of HEAD_R round the hole centre,
on every layer; the holes have no copper since routing stage 13c) - and compares it with the limits of kicad_next/tube_psu_5_2.kicad_dru (README
"Isolation domains"; the table LIMITS below is a copy of the rules):

  outer layers  d < clearance                      -> violation (air, a slot does not help)
                clearance <= d < creepage          -> violation unless a milled slot (internal Edge.Cuts cut-out,
                                                      board polygons and footprint slots) blocks the straight
                                                      line; then the surface path round the slots (visibility
                                                      graph over the slot outlines) must reach the creepage
  inner layers  d < inner spacing (= outer creepage): violation, no slot credit

Layer to layer: KiCad checks nothing between two layers, and one prepreg (0.1 mm) is not reinforced insulation.
The second pass therefore measures every two copper items of different domains on two DIFFERENT layers in plan
view: if one of the layers is an inner layer the inner-layer spacing applies (no slot credit), F.Cu against B.Cu
is treated like two items on one outer layer. Pairs that also meet on a common layer (through-hole pads, vias)
are left to the same-layer pass; the two pad rows of one barrier part are left to check_footprints.py.

Zones are not refilled here: run it on a board saved after a DRC refill (the trial placement scripts do that).
Accepted pairs are listed in ALLOW with the reason; they are printed but do not fail the check. Exit status 1 if
any other pair is below its limit. Memory: a few hundred MB (pcbnew board load + shapely), no DRC run.
"""
import collections
import heapq
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
TRIAL = os.path.join(ROOT, "kicad_next", "trial_from_51")
KIPY = os.path.join(ROOT, "tools", "p2k", "bin", "kipy")

# net class -> isolation domain (tools/next/setup_project.py, kicad_dru header)
CLASS_DOMAIN = {"HV_PRIMARY": "PRI", "PRIMARY_LV": "PRI", "SIGNAL": "PRI", "HV_SECONDARY": "SEC",
                "SECONDARY_LV": "SEC", "HEATER": "HEATER", "UART_ISO": "UART", "PE_EARTH": "PE"}
HOLES = re.compile(r"^H[1-8]$")     # mounting holes: earthed screws, domain HOLE (rules "Mounting hole - ...")
HEAD_R = 3.0                         # radius of the screw head / standoff (6 mm) round the hole centre (stage 13c)
# (domain A, domain B): (outer clearance, outer creepage, inner spacing) in mm; None = no rule
LIMITS = {
    ("PRI", "SEC"): (4.0, 11.1, 11.1),          # reinforced, 552 Vrms
    ("HEATER", "PRI"): (4.0, 8.2, 8.2),         # reinforced, 410 Vrms with the heater at -100 V (8.0 until stage 13d)
    ("PRI", "UART"): (4.0, 8.0, 8.0),
    ("SEC", "UART"): (3.0, 8.4, 8.4),
    ("HEATER", "SEC_HV"): (1.5, 5.2, 5.2),      # functional, net class HV_SECONDARY
    ("HEATER", "SEC_LV"): (1.0, 1.5, 1.0),      # functional, net class SECONDARY_LV
    ("HEATER", "UART"): (1.0, None, 1.0),
    ("PE", "PRI"): (2.0, 3.2, 3.2),             # basic
    ("PE", "SEC"): (1.5, 4.2, 4.2),
    ("HOLE", "PRI"): (2.0, 3.2, 3.2),           # basic, from the 6 mm head (HEAD_R) on every layer: 6.2 mm from the centre
    ("HOLE", "SEC"): (1.5, 4.2, 4.2),           # 7.2 mm from the centre
    ("HOLE", "UART"): (1.0, None, 1.0),         # functional (UART island at H2)
}
# Accepted pairs: (regex item A, regex item B, regex layer, smallest accepted distance mm, reason). A pair is
# accepted if both descriptions match (in either order), the layer matches and the distance is not smaller.
# Since stage 13c: the holes where fixed parts stand nearer to the head than the limit (kicad_dru rules "Mounting hole Hn
# ... (achieved, insulating hardware)", README stage 13c): the copper holds the value below, the hole needs insulating
# hardware (nylon screw / standoff or insulating washers).
_NYLON = "insulating hardware (nylon) at this hole, README stage 13c"
ALLOW = [(r"^hole H4$", r".", r".", 1.9, "H4: DRV5 / R14 / C92 / L2 pads and the In2 control bus within 6.2 mm; " + _NYLON),
         (r"^hole H7$", r".", r".", 2.0, "H7: R47 / R48 pads (B.Cu) and the In2 Net-(R48-Pad2) track; " + _NYLON),
         (r"^hole H8$", r".", r".", 3.2, "H8: C102 pad 1 (ISO_GND) 6.23 mm from the centre; " + _NYLON),
         (r"^hole H2$", r".", r".", 0.1, "H2: J4 pads / ground bus of the UART island; " + _NYLON)]
BARRIERS = {"TR1", "TR2", "TR3", "ISO1", "ISO2", "U11"}      # setup_project.py BARRIERS: two domains in one footprint
EPS = 1e-6


# ------------------------------------------------------------------------------------------- dump (kipy)
def dump(board, out):
    import pcbnew
    b = pcbnew.LoadBoard(board)
    mm = lambda v: round(v / 1e6, 4)  # noqa: E731
    cu = [l for l in b.GetEnabledLayers().CuStack()]
    name = {l: b.GetLayerName(l) for l in cu}
    outer = [name[cu[0]], name[cu[-1]]]

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

    g = {"layers": [name[l] for l in cu], "outer": outer, "pads": [], "tracks": [], "vias": [], "zones": [], "slots": []}
    edge = pcbnew.SHAPE_POLY_SET()
    if not b.GetBoardPolygonOutlines(edge, True):
        sys.exit("check_domains: the board outline is not a valid closed polygon")
    for i in range(edge.OutlineCount()):
        for h in range(edge.HoleCount(i)):
            hh = edge.Hole(i, h)
            g["slots"].append([[mm(hh.CPoint(k).x), mm(hh.CPoint(k).y)] for k in range(hh.PointCount())])
    ebb = b.GetBoardEdgesBoundingBox()
    for fp in b.GetFootprints():
        ref = fp.GetReference()
        if not ebb.Contains(fp.GetPosition()):
            continue                      # parts parked outside the board
        for p in fp.Pads():
            hole = None
            if p.HasHole():
                hs = pcbnew.SHAPE_POLY_SET()
                p.TransformHoleToPolygon(hs, 0, 5000, pcbnew.ERROR_INSIDE)
                hole = polys(hs)
            by_shape = collections.defaultdict(list)
            for l in cu:
                if p.IsOnLayer(l) and p.FlashLayer(l):
                    sp = pcbnew.SHAPE_POLY_SET()
                    p.TransformShapeToPolygon(sp, l, 0, 5000, pcbnew.ERROR_INSIDE)
                    by_shape[json.dumps(polys(sp))].append(name[l])
                elif hole:
                    by_shape[json.dumps(hole)].append(name[l])     # barrel only (no ring on this layer)
            for shape, layers in by_shape.items():
                g["pads"].append(dict(ref=ref, num=p.GetNumber(), net=p.GetNetname(), layers=layers,
                                      polys=json.loads(shape), hole=hole if HOLES.match(ref) else None))
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            g["vias"].append(dict(x=mm(t.GetPosition().x), y=mm(t.GetPosition().y), d=mm(t.GetWidth(cu[0])),
                                  net=t.GetNetname(), layers=[name[l] for l in cu if t.IsOnLayer(l)]))
        else:
            g["tracks"].append(dict(layer=name[t.GetLayer()], net=t.GetNetname(), w=mm(t.GetWidth()),
                                    pts=[mm(t.GetStart().x), mm(t.GetStart().y), mm(t.GetEnd().x), mm(t.GetEnd().y)]))
    for z in b.Zones():
        if z.GetIsRuleArea():
            continue
        for l in z.GetLayerSet().CuStack():
            pp = polys(z.GetFilledPolysList(l))
            if pp:
                g["zones"].append(dict(layer=name[l], net=z.GetNetname(), name=z.GetZoneName(), polys=pp))
    with open(out, "w") as f:
        json.dump(g, f)


# ------------------------------------------------------------------------------------------- check (python3)
def latest_trial():
    best = None
    for f in os.listdir(TRIAL):
        m = re.fullmatch(r"tube_psu_5_2_trial(?:_p(\d+))?\.kicad_pcb", f)
        if m and (best is None or int(m.group(1) or 0) > best[0]):
            best = (int(m.group(1) or 0), os.path.join(TRIAL, f))
    if best is None:
        sys.exit("check_domains: no trial board in kicad_next/trial_from_51")
    return best[1]


def net_classes(board):
    with open(os.path.splitext(board)[0] + ".kicad_pro") as f:
        pro = json.load(f)
    return {p["pattern"]: p["netclass"] for p in pro["net_settings"]["netclass_patterns"]}


def pair_key(ka, kb):
    """LIMITS key and limits for two item kinds (domain, or SEC_HV / SEC_LV where the rule needs the class)"""
    for a, b in ((ka, kb), (kb, ka)):
        for x, y in ((a, b), (a[:3] if a.startswith("SEC") else a, b[:3] if b.startswith("SEC") else b)):
            if (x, y) in LIMITS:
                return (x, y), LIMITS[(x, y)]
    return None, None


def main(argv):
    from shapely.geometry import LineString, Point, Polygon
    from shapely.ops import nearest_points, unary_union
    from shapely.strtree import STRtree

    args = [a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or argv[i - 1] != "--json")]
    board = os.path.abspath(args[0]) if args else latest_trial()
    cls = net_classes(board)
    with tempfile.TemporaryDirectory() as tmp:
        js = os.path.join(tmp, "g.json")
        r = subprocess.run([KIPY, os.path.abspath(__file__), "--dump", board, js], capture_output=True, text=True)
        if r.returncode or not os.path.exists(js):
            sys.exit("check_domains: board dump failed\n" + r.stdout[-2000:] + r.stderr[-2000:])
        with open(js) as f:
            g = json.load(f)
    outer = set(g["outer"])

    def kind(net):
        c = cls.get(net, "")
        d = CLASS_DOMAIN.get(c, "")
        return {"HV_SECONDARY": "SEC_HV", "SECONDARY_LV": "SEC_LV"}.get(c, d)

    def mk(pp):
        return unary_union([Polygon(ring, holes).buffer(0) for ring, holes in pp])

    # items per layer: (geometry, kind, description)
    items = collections.defaultdict(list)
    nodom = set()
    ALL = frozenset(g["layers"])
    span = collections.defaultdict(set)      # (ref, pad number, net) -> every layer the pad has copper / a barrel on
    for p in g["pads"]:
        span[(p["ref"], p["num"], p["net"])].update(p["layers"])
    for p in g["pads"]:
        if HOLES.match(p["ref"]):
            hole = mk(p["hole"]) if p["hole"] else mk(p["polys"])
            head = Point(hole.centroid.x, hole.centroid.y).buffer(HEAD_R, 64)
            for l in g["layers"]:
                # the earthed screw head / standoff (6 mm) on every layer: outer layers clearance / creepage, inner
                # layers plan distance (stage 13c; before: the 3.5 mm copper ring outside, the hole inside)
                items[l].append((head, "HOLE", f"hole {p['ref']}", ALL, p["ref"]))
            continue
        if not p["net"]:
            continue
        k = kind(p["net"])
        if not k:
            nodom.add(p["net"])
            continue
        geom = mk(p["polys"])
        for l in p["layers"]:
            items[l].append((geom, k, f"pad {p['ref']}.{p['num']} [{p['net']}]",
                             frozenset(span[(p["ref"], p["num"], p["net"])]), p["ref"]))
    for t in g["tracks"]:
        k = kind(t["net"])
        if not k:
            nodom.add(t["net"])
            continue
        x0, y0, x1, y1 = t["pts"]
        geom = (Point(x0, y0) if (x0, y0) == (x1, y1) else LineString([(x0, y0), (x1, y1)])).buffer(t["w"] / 2, 8)
        items[t["layer"]].append((geom, k, f"track [{t['net']}] ({x0}, {y0})-({x1}, {y1})", frozenset([t["layer"]]), None))
    for v in g["vias"]:
        k = kind(v["net"])
        if not k:
            nodom.add(v["net"])
            continue
        geom = Point(v["x"], v["y"]).buffer(v["d"] / 2, 8)
        for l in v["layers"]:
            items[l].append((geom, k, f"via [{v['net']}] ({v['x']}, {v['y']})", frozenset(v["layers"]), None))
    for z in g["zones"]:
        k = kind(z["net"])
        if not k:
            nodom.add(z["net"])
            continue
        for ring, holes in z["polys"]:
            items[z["layer"]].append((Polygon(ring, holes).buffer(0), k, f"zone [{z['net']}] '{z['name']}'",
                                      frozenset([z["layer"]]), None))

    slots = [Polygon(s).buffer(0) for s in g["slots"] if len(s) > 2]
    cores = [s.buffer(-0.01) for s in slots]          # a path may run along a slot edge
    core_tree = STRtree(cores) if cores else None
    slot_nodes = [[(x, y) for x, y in s.simplify(0.01).exterior.coords[:-1]] for s in slots]

    def blocked(a, b):
        if core_tree is None:
            return False
        seg = LineString([a, b])
        return any(cores[i].intersects(seg) and cores[i].intersection(seg).length > 1e-4 for i in core_tree.query(seg))

    def surface_path(ga, gb, limit):
        """shortest path from ga to gb round the slots (visibility graph over the slot outline points within reach)"""
        near = unary_union([ga, gb]).buffer(limit)
        nodes = [n for i, s in enumerate(slots) if s.intersects(near) for n in slot_nodes[i]]

        def reach(geom, n):
            q = nearest_points(geom, Point(n))[0]
            return None if blocked((q.x, q.y), n) else Point(n).distance(geom)
        best = float("inf")
        dist = {}
        end = {}
        for i, n in enumerate(nodes):
            da, db = reach(ga, n), reach(gb, n)
            if da is not None:
                dist[i] = da
            if db is not None:
                end[i] = db
        heap = [(d, i) for i, d in dist.items()]
        heapq.heapify(heap)
        done = set()
        while heap:
            d, i = heapq.heappop(heap)
            if i in done or d >= min(best, limit):
                continue
            done.add(i)
            if i in end:
                best = min(best, d + end[i])
            for j, m in enumerate(nodes):
                if j in done:
                    continue
                nd = d + ((nodes[i][0] - m[0]) ** 2 + (nodes[i][1] - m[1]) ** 2) ** 0.5
                if nd < dist.get(j, float("inf")) and nd < limit and not blocked(nodes[i], m):
                    dist[j] = nd
                    heapq.heappush(heap, (nd, j))
        return best

    viol, accepted = [], []
    stats = collections.Counter()
    for layer in g["layers"]:
        by = collections.defaultdict(list)
        for it in items[layer]:
            by[it[1]].append(it)
        kinds = sorted(by)
        for ia, ka in enumerate(kinds):
            for kb in kinds[ia + 1:]:
                key, lim = pair_key(ka, kb)
                if lim is None:
                    continue
                clr, creep, inner = lim
                reach = max(x for x in (clr, creep) if x) if layer in outer else inner
                A, B = by[ka], by[kb]
                tree = STRtree([b_[0] for b_ in B])
                for ga, _, da, _, _ in A:
                    for j in tree.query(ga.buffer(reach)):
                        gb, _, db, _, _ = B[j]
                        d = ga.distance(gb)
                        if d >= reach - EPS:
                            continue
                        stats[(key, layer)] += 1
                        what, need, path = None, None, None
                        if layer not in outer:
                            what, need = "inner spacing", inner
                        elif d < clr - EPS:
                            what, need = "clearance", clr
                        elif creep and d < creep - EPS:
                            pa, pb = nearest_points(ga, gb)
                            if not blocked((pa.x, pa.y), (pb.x, pb.y)):
                                what, need = "creepage", creep
                            else:
                                path = surface_path(ga, gb, creep)
                                if path < creep - EPS:
                                    what, need = "creepage round a slot", creep
                        if what is None:
                            continue
                        rec = dict(pair="-".join(key), layer=layer, what=what, need=need, d=round(d, 3),
                                   path=None if path is None else round(path, 3), a=da, b=db)
                        ok = next((why for ra, rb, rl, dmin, why in ALLOW
                                   if re.search(rl, layer) and d >= dmin - EPS and
                                   ((re.search(ra, da) and re.search(rb, db)) or (re.search(ra, db) and re.search(rb, da)))), None)
                        if ok:
                            rec["accepted"] = ok
                            accepted.append(rec)
                        else:
                            viol.append(rec)

    # ---- layer to layer (distance through insulation): copper of two domains on two different layers ----
    # KiCad checks nothing between layers. README "Isolation domains": the dielectrics (0.2 mm cores, 0.2 / 0.43 mm prepreg) are not
    # reinforced solid insulation, so copper of one domain must not overlap copper of another domain on any other
    # layer - and "overlap" is taken with the same plan-view spacing as on one layer, because a plane edge under a
    # pad of the other domain is only a prepreg away from it:
    #   one of the two layers is an inner layer   plan distance >= the inner-layer spacing, no slot credit
    #   F.Cu <-> B.Cu                             as two items on one outer layer (clearance, creepage round slots)
    # A pair is skipped when the two items also meet on a common layer (a through-hole pad or a via has copper /
    # a barrel on every layer: the same-layer pass above has judged that pair, with the outer-layer slot credit),
    # and for the two pad rows of one barrier part (TR1-TR3, ISO1, ISO2, U11: check_footprints.py checks their
    # slots). ALLOW applies as on one layer.
    xviol, xacc = [], []
    xstats = collections.Counter()
    trees = {}
    for layer in g["layers"]:
        by = collections.defaultdict(list)
        for it in items[layer]:
            by[it[1]].append(it)
        trees[layer] = {k: (v, STRtree([i[0] for i in v])) for k, v in by.items()}
    for ia, la in enumerate(g["layers"]):
        for lb in g["layers"][ia + 1:]:
            both_outer = la in outer and lb in outer
            for ka, (A, _) in trees[la].items():
                for kb, (B, tree) in trees[lb].items():
                    key, lim = pair_key(ka, kb)
                    if lim is None:
                        continue
                    clr, creep, inner = lim
                    reach = max(x for x in (clr, creep) if x) if both_outer else inner
                    for ga, _, da, sa, ra in A:
                        if lb in sa:
                            continue
                        for j in tree.query(ga.buffer(reach)):
                            gb, _, db, sb, rb = B[j]
                            if la in sb or (ra and ra == rb and ra in BARRIERS):
                                continue
                            d = ga.distance(gb)
                            if d >= reach - EPS:
                                continue
                            xstats[(key, la, lb)] += 1
                            what, need, path = None, None, None
                            if not both_outer:
                                what, need = "layer-to-layer spacing", inner
                            elif d < clr - EPS:
                                what, need = "layer-to-layer clearance", clr
                            elif creep and d < creep - EPS:
                                pa, pb = nearest_points(ga, gb)
                                if not blocked((pa.x, pa.y), (pb.x, pb.y)):
                                    what, need = "layer-to-layer creepage", creep
                                else:
                                    path = surface_path(ga, gb, creep)
                                    if path < creep - EPS:
                                        what, need = "layer-to-layer creepage round a slot", creep
                            if what is None:
                                continue
                            rec = dict(pair="-".join(key), layer=f"{la} / {lb}", what=what, need=need, d=round(d, 3),
                                       path=None if path is None else round(path, 3), a=da, b=db)
                            ok = next((why for xa, xb, rl, dmin, why in ALLOW
                                       if (re.search(rl, la) or re.search(rl, lb) or re.search(rl, f"{la} / {lb}"))
                                       and d >= dmin - EPS and
                                       ((re.search(xa, da) and re.search(xb, db)) or (re.search(xa, db) and re.search(xb, da)))), None)
                            if ok:
                                rec["accepted"] = ok
                                xacc.append(rec)
                            else:
                                xviol.append(rec)
    viol += xviol
    accepted += xacc

    def line(v):
        act = f"{v['d']:.2f} mm" + (f" straight, {v['path']:.2f} mm round the slot" if v["path"] is not None else "")
        return f"  {v['pair']:11s} {v['layer']:14s} {v['what']} {v['need']} mm: {act}: {v['a']} | {v['b']}"

    print(f"check_domains: layer to layer: {sum(xstats.values())} pairs of two domains on two different layers closer "
          f"than their limit in plan view, {len(xviol)} below the limit, {len(xacc)} accepted")

    rel = os.path.relpath(board, ROOT)
    print(f"check_domains: {rel}: {sum(len(v) for v in items.values())} copper items on {len(g['layers'])} layers, "
          f"{len(slots)} slots, {sum(stats.values())} pairs of two domains closer than their largest limit")
    if nodom:
        print(f"check_domains: FAIL nets without an isolation domain: {sorted(nodom)[:10]}")
    by_pair = collections.Counter((v["pair"], v["what"]) for v in viol)
    if accepted:
        acc = collections.Counter((v["pair"], v["accepted"]) for v in accepted)
        for (pair, why), n in sorted(acc.items()):
            dmin = min(v["d"] for v in accepted if v["pair"] == pair and v["accepted"] == why)
            print(f"check_domains: accepted {pair}: {n} pairs, smallest {dmin:.2f} mm - {why}")
    if viol:
        print("check_domains: BELOW THE LIMIT: " + ", ".join(f"{p} {w} {n}" for (p, w), n in sorted(by_pair.items())))
        seen = set()
        shown = 0
        for v in sorted(viol, key=lambda v: (v["pair"], v["d"])):
            k = (v["pair"], v["layer"], v["a"], v["b"])
            if k in seen:
                continue
            seen.add(k)
            if "--all" in argv or shown < 40:
                print(line(v))
            shown += 1
        if shown > 40 and "--all" not in argv:
            print(f"  ... {shown - 40} more (--all)")
    else:
        print("check_domains: no pair of two isolation domains below its limit" + (" (besides the accepted ones)" if accepted else ""))
    if "--json" in argv:
        with open(argv[argv.index("--json") + 1], "w") as f:
            json.dump(dict(board=rel, violations=viol, accepted=accepted), f, indent=1)
    return 1 if viol or nodom else 0


if __name__ == "__main__":
    if "--dump" in sys.argv:
        i = sys.argv.index("--dump")
        dump(sys.argv[i + 1], sys.argv[i + 2])
        sys.exit(0)
    sys.exit(main(sys.argv[1:]))
