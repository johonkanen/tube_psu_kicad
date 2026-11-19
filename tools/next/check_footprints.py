#!/usr/bin/env python3
"""Footprint and 3D-model check of the 5.2 design (run with tools/p2k/bin/kipy).

    tools/p2k/bin/kipy tools/next/check_footprints.py [--dump FILE.json]

1. Every part of the 5.2 schematic (kicad-cli netlist) has a footprint that loads in pcbnew, and its pad
   numbers equal the symbol's pin numbers (set comparison; unnumbered mechanical pads ignored).
2. Every footprint used, and every footprint in lib/tube_psu_next*.pretty, has a 3D model whose file
   exists (${KICAD10_3DMODEL_DIR} / ${KICAD9_3DMODEL_DIR} = the AppImage's 3dmodels, ${KIPRJMOD} = kicad_next).
   Model heights (max z of the STEP points) are listed for the tallest parts.
3. Barrier parts (pins in two isolation domains, tools/next/setup_project.py): the shortest surface path
   between the pads of the two domains, around the footprint's internal Edge.Cuts (creepage slots), must
   reach the creepage of kicad_next/tube_psu_5_2.kicad_dru for that domain pair. Visibility-graph
   calculation: pads as polygons (circles circumscribed, rounded rectangles as rectangles), slots as
   convex hulls of their outline with the arcs inscribed - both conservative.
4. KiCad's own creepage check: the barrier parts are placed on a temporary copy of the board with their
   nets and the DRC must report no creepage / clearance violation at them; the plain SOIC-16W (no slot)
   for ISO2 is the negative control and must be reported.
--dump writes the footprint geometry (pads, graphics) for tools/next/render_footprints.py.
"""
import heapq
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import setup_project  # noqa: E402

PROJ = os.path.join(ROOT, "kicad_next")
SCH = os.path.join(PROJ, "tube_psu_5_2.kicad_sch")
CLI = os.path.join(ROOT, "tools", "p2k", "bin", "kicad-cli")
MOUNT = os.environ.get("KICAD_MOUNT", "")
KICAD_FP = os.path.join(MOUNT, "share", "kicad", "footprints")
KICAD_3D = os.path.join(MOUNT, "share", "kicad", "3dmodels")
LIBS = {"tube_psu": "lib/tube_psu.pretty", "tube_psu_next": "lib/tube_psu_next.pretty",
        "tube_psu_next_parts": "lib/tube_psu_next_parts.pretty"}

# creepage between domains on the PCB surface (kicad_next/tube_psu_5_2.kicad_dru, README "Isolation domains")
CREEPAGE = {frozenset(("PRIMARY", "SECONDARY")): 11.1, frozenset(("PRIMARY", "HEATER")): 8.0,
            frozenset(("PRIMARY", "UART")): 8.0, frozenset(("SECONDARY", "UART")): 8.4,
            frozenset(("SECONDARY", "HEATER")): 5.2, frozenset(("HEATER", "UART")): 1.0,
            frozenset(("PRIMARY", "EARTH")): 3.2, frozenset(("SECONDARY", "EARTH")): 4.2}   # Y caps: basic
# board-specific footprint variants that no schematic part uses (swapped in by the trial placement,
# tools/next/trial_placement_p3.py): checked like the part's own footprint (pads, creepage, KiCad DRC)
BOARD_VARIANTS = {"ISO1": "tube_psu_next_parts:SOIC-16W_7.5x10.3mm_P1.27mm_Slot8.0_T_ISO1"}
NEG_CONTROL = ("ISO2", "Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm")   # must fail the KiCad creepage check
MM = 1e6


# --- netlist ------------------------------------------------------------------------------------------
def netlist():
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "net.xml")
        subprocess.run([CLI, "sch", "export", "netlist", "--format", "kicadxml", "-o", out, SCH],
                       check=True, capture_output=True)
        t = ET.parse(out)
    comps = {c.get("ref"): (c.findtext("footprint") or "") for c in t.find("components")}
    pins, netpins = {}, {}
    for n in t.find("nets"):
        netpins[n.get("name")] = []
        for nd in n.findall("node"):
            pins.setdefault(nd.get("ref"), {})[nd.get("pin")] = n.get("name")
            netpins[n.get("name")].append((nd.get("ref"), nd.get("pin")))
    return comps, pins, netpins


def load_fp(fpid):
    lib, name = fpid.split(":", 1)
    path = os.path.join(ROOT, LIBS[lib]) if lib in LIBS else os.path.join(KICAD_FP, lib + ".pretty")
    return pcbnew.FootprintLoad(path, name)


def resolve(path):
    for var, val in (("${KICAD10_3DMODEL_DIR}", KICAD_3D), ("${KICAD9_3DMODEL_DIR}", KICAD_3D), ("${KIPRJMOD}", PROJ)):
        path = path.replace(var, val)
    return os.path.normpath(path)


_height = {}


def step_height(path):
    if path not in _height:
        z = -1e9
        if path.endswith((".step", ".stp")):
            for m in re.finditer(r"CARTESIAN_POINT\('[^']*',\(([^)]*)\)\)", open(path, errors="ignore").read()):
                v = m.group(1).split(",")
                if len(v) == 3:
                    z = max(z, float(v[2]))
        _height[path] = z
    return _height[path]


# --- geometry -----------------------------------------------------------------------------------------
def pad_poly(p):
    """Pad copper outline (footprint coordinates, mm): circles circumscribed (16-gon), others as their
    rotated bounding rectangle - both never larger than the real gap is small."""
    c, s = p.GetPosition(), p.GetSize(pcbnew.F_Cu)
    cx, cy, w, h = c.x / MM, c.y / MM, s.x / MM, s.y / MM
    a = -math.radians(p.GetOrientation().AsDegrees())
    if p.GetShape(pcbnew.F_Cu) == pcbnew.PAD_SHAPE_CIRCLE:
        r = w / 2 / math.cos(math.pi / 16)
        return [(cx + r * math.cos(2 * math.pi * k / 16), cy + r * math.sin(2 * math.pi * k / 16)) for k in range(16)]
    pts = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    return [(cx + x * math.cos(a) - y * math.sin(a), cy + x * math.sin(a) + y * math.cos(a)) for x, y in pts]


def hull(pts):
    pts = sorted(set((round(x, 6), round(y, 6)) for x, y in pts))
    if len(pts) < 3:
        return pts
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]          # counter-clockwise


def edge_obstacles(fp):
    """Internal Edge.Cuts of the footprint -> convex polygons (one per connected outline)."""
    segs = []
    for g in fp.GraphicalItems():
        if g.GetLayer() != pcbnew.Edge_Cuts:
            continue
        if g.GetShape() == pcbnew.SHAPE_T_ARC:
            st, md, en = g.GetStart(), g.GetArcMid(), g.GetEnd()
            c = g.GetCenter()
            r = math.hypot(st.x - c.x, st.y - c.y) / MM
            a0 = math.atan2(st.y - c.y, st.x - c.x)
            a1 = math.atan2(en.y - c.y, en.x - c.x)
            am = math.atan2(md.y - c.y, md.x - c.x)
            sweep = (a1 - a0) % (2 * math.pi)
            if (am - a0) % (2 * math.pi) > sweep:
                sweep -= 2 * math.pi
            pts = [(c.x / MM + r * math.cos(a0 + sweep * k / 12), c.y / MM + r * math.sin(a0 + sweep * k / 12)) for k in range(13)]
        else:
            pts = [(g.GetStart().x / MM, g.GetStart().y / MM), (g.GetEnd().x / MM, g.GetEnd().y / MM)]
        segs.append(pts)
    groups = []
    for pts in segs:            # group by shared end points
        ends = {(round(pts[0][0], 3), round(pts[0][1], 3)), (round(pts[-1][0], 3), round(pts[-1][1], 3))}
        hit = [g for g in groups if g[0] & ends]
        merged = [set(ends), list(pts)]
        for g in hit:
            merged[0] |= g[0]
            merged[1] += g[1]
            groups.remove(g)
        groups.append(merged)
    out = []
    for g in groups:
        ring = ring_of([s_ for s_ in segs if (round(s_[0][0], 3), round(s_[0][1], 3)) in g[0]])
        out.append(hull(g[1]) if ring is None or is_convex(ring) else NonConvex(ring))
    return out


class NonConvex(list):
    """Closed outline that is not convex (the T slot of the board-specific ISO1 footprint): vertex ring, arcs
    inscribed. blocked() tests it exactly instead of through its convex hull (which would cover the pads)."""


def ring_of(segs):
    """Ordered vertex ring of a closed chain of segments (each a point list), None if it does not close."""
    key = lambda q: (round(q[0], 3), round(q[1], 3))  # noqa: E731
    left = [list(s_) for s_ in segs]
    ring = left.pop(0)
    while left:
        end = key(ring[-1])
        nxt = next((s_ for s_ in left if key(s_[0]) == end or key(s_[-1]) == end), None)
        if nxt is None:
            return None
        left.remove(nxt)
        ring += (nxt if key(nxt[0]) == end else nxt[::-1])[1:]
    if key(ring[0]) != key(ring[-1]):
        return None
    return ring[:-1]


def is_convex(ring):
    sign = 0
    n = len(ring)
    for i in range(n):
        o, a, b = ring[i], ring[(i + 1) % n], ring[(i + 2) % n]
        c = (a[0] - o[0]) * (b[1] - a[1]) - (a[1] - o[1]) * (b[0] - a[0])
        if abs(c) > 1e-9:
            if sign and (c > 0) != (sign > 0):
                return False
            sign = c
    return True


def inside(pt, ring, tol=1e-6):
    """Strictly inside the polygon (points within tol of its boundary are outside)."""
    x, y = pt
    n = len(ring)
    for i in range(n):
        c = seg_closest(pt, ring[i], ring[(i + 1) % n])
        if math.hypot(c[0] - x, c[1] - y) <= tol:
            return False
    hit = False
    for i in range(n):
        (x0, y0), (x1, y1) = ring[i], ring[(i + 1) % n]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            hit = not hit
    return hit


def blocked_nonconvex(p, q, ring):
    """Segment p-q passes through the interior of the polygon: cut it at every crossing / touching point of the
    outline and test the middle of each piece."""
    dx, dy = q[0] - p[0], q[1] - p[1]
    ts = [0.0, 1.0]
    n = len(ring)
    for i in range(n):
        a, b = ring[i], ring[(i + 1) % n]
        ex, ey = b[0] - a[0], b[1] - a[1]
        den = dx * ey - dy * ex
        if abs(den) > 1e-12:
            t = ((a[0] - p[0]) * ey - (a[1] - p[1]) * ex) / den
            u = ((a[0] - p[0]) * dy - (a[1] - p[1]) * dx) / den
            if -1e-9 <= t <= 1 + 1e-9 and -1e-9 <= u <= 1 + 1e-9:
                ts.append(min(1.0, max(0.0, t)))
        else:                                   # parallel: the end points of the edge projected on p-q
            l2 = dx * dx + dy * dy
            if l2 > 0:
                for v in (a, b):
                    t = ((v[0] - p[0]) * dx + (v[1] - p[1]) * dy) / l2
                    if 0 < t < 1:
                        ts.append(t)
    ts = sorted(set(ts))
    for t0, t1 in zip(ts, ts[1:]):
        if (t1 - t0) * math.hypot(dx, dy) > 1e-5:
            tm = (t0 + t1) / 2
            if inside((p[0] + tm * dx, p[1] + tm * dy), ring):
                return True
    return False


def blocked(p, q, polys):
    """Segment p-q passes through the interior of a convex (ccw) polygon (Cyrus-Beck)."""
    for poly in polys:
        if isinstance(poly, NonConvex):
            if blocked_nonconvex(p, q, poly):
                return True
            continue
        t0, t1, n = 0.0, 1.0, len(poly)
        dx, dy = q[0] - p[0], q[1] - p[1]
        ok = True
        for i in range(n):
            a, b = poly[i], poly[(i + 1) % n]
            nx, ny = (b[1] - a[1]), -(b[0] - a[0])       # outward normal of a ccw polygon
            ln = math.hypot(nx, ny) or 1.0
            num = (nx * (p[0] - a[0]) + ny * (p[1] - a[1])) / ln + 1e-6   # > 0: outside (with tolerance)
            den = (nx * dx + ny * dy) / ln
            if abs(den) < 1e-12:
                if num > 0:
                    ok = False
                    break
                continue
            t = -num / den
            if den < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
            if t0 >= t1:
                ok = False
                break
        if ok and (t1 - t0) * math.hypot(dx, dy) > 1e-5:
            return True
    return False


def seg_closest(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    l2 = dx * dx + dy * dy
    t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l2))
    return (a[0] + t * dx, a[1] + t * dy)


def poly_to_point(poly, p, obst):
    """Shortest visible straight distance from a polygon (its boundary) to point p."""
    best = math.inf
    cands = list(poly) + [seg_closest(p, poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly))]
    for c in cands:
        d = math.hypot(c[0] - p[0], c[1] - p[1])
        if d < best and not blocked(c, p, obst):
            best = d
    return best


def poly_to_poly(pa, pb, obst):
    best = math.inf
    for p in pa:
        best = min(best, poly_to_point(pb, p, obst))
    for p in pb:
        best = min(best, poly_to_point(pa, p, obst))
    return best


def creepage(group_a, group_b, obst):
    """Shortest surface path between two sets of pad polygons around the obstacles."""
    nodes = [v for poly in obst for v in poly]
    best = min(poly_to_poly(a, b, obst) for a in group_a for b in group_b)
    dist = [min(poly_to_point(a, v, obst) for a in group_a) for v in nodes]
    heap = [(d, i) for i, d in enumerate(dist) if d < math.inf]
    heapq.heapify(heap)
    done = set()
    while heap:
        d, i = heapq.heappop(heap)
        if i in done or d >= best:
            continue
        done.add(i)
        v = nodes[i]
        best = min(best, d + min(poly_to_point(b, v, obst) for b in group_b))
        for j, w in enumerate(nodes):
            if j not in done and not blocked(v, w, obst):
                nd = d + math.hypot(v[0] - w[0], v[1] - w[1])
                if nd < dist[j]:
                    dist[j] = nd
                    heapq.heappush(heap, (nd, j))
    return best


# --- checks -------------------------------------------------------------------------------------------
def models_of(fp):
    out = []
    for m in fp.Models():
        path = resolve(m.m_Filename)
        out.append((m.m_Filename, path, os.path.exists(path)))
    return out


def kicad_drc(barrier, comps, pins, netpins):
    """Place the barrier parts (and the negative control) on a copy of the board; DRC creepage / clearance."""
    place = {"TR3": (-40, -62), "TR1": (5, -65), "ISO1": (35, -75), "ISO2": (65, -75), "U11": (35, -45),
             "TR2": (65, -40), NEG_CONTROL[0] + "_noslot": (-40, -10), "ISO1_variant": (30, -10)}   # >= 25 mm apart, clear of H1-H8
    items = [(r, comps[r]) for r in sorted(barrier)] + [(NEG_CONTROL[0] + "_noslot", NEG_CONTROL[1])] \
        + [(r + "_variant", f) for r, f in sorted(BOARD_VARIANTS.items())]
    xs = [place[r] for r, _ in items]
    assert len(items) <= len(xs)
    with tempfile.TemporaryDirectory(dir=ROOT, prefix=".fpcheck_") as tmp:
        for ext in ("kicad_pcb", "kicad_pro", "kicad_dru"):
            shutil.copy(os.path.join(PROJ, f"tube_psu_5_2.{ext}"), tmp)
        pcb = os.path.join(tmp, "tube_psu_5_2.kicad_pcb")
        b = pcbnew.LoadBoard(pcb)
        nets = {}
        spots = {}
        for (ref, fpid), (x, y) in zip(items, xs):
            src = ref.split("_")[0]
            fp = load_fp(fpid)
            fp.SetReference(ref)
            fp.SetPosition(pcbnew.VECTOR2I(int(x * MM), int(y * MM)))
            for p in fp.Pads():
                n = pins[src].get(p.GetNumber())
                if n is None:
                    continue
                if n not in nets:
                    nets[n] = pcbnew.NETINFO_ITEM(b, n)
                    b.Add(nets[n])
                p.SetNet(nets[n])
            b.Add(fp)
            spots[ref] = (x, y)
        pcbnew.SaveBoard(pcb, b)
        rpt = os.path.join(tmp, "drc.json")
        subprocess.run([CLI, "pcb", "drc", "--format", "json", "--severity-all", "-o", rpt, pcb],
                       check=True, capture_output=True)
        viol = json.load(open(rpt))["violations"]
    hits = {r: set() for r in spots}
    for v in viol:
        if v["type"] not in ("creepage", "clearance"):
            continue
        p = v["items"][0]["pos"]
        r = min(spots, key=lambda k: (p["x"] - spots[k][0]) ** 2 + (p["y"] - spots[k][1]) ** 2)
        hits[r].add(v["type"])
        if os.environ.get("FPCHECK_VERBOSE"):
            print("  drc", r, v["type"], v["description"], [(i["description"], i["pos"]) for i in v["items"]])
    return hits


def main(argv):
    if not MOUNT:
        sys.exit("check_footprints: KICAD_MOUNT not set (run with tools/p2k/bin/kipy)")
    comps, pins, netpins = netlist()
    dom = setup_project.domains({n: ps for n, ps in netpins.items()})
    bad = []
    cache, dump = {}, {}
    # 1 + 2: footprints, pads, models
    for ref in sorted(comps, key=lambda r: (re.sub(r"\d", "", r), int(re.sub(r"\D", "", r) or 0))):
        fpid = comps[ref]
        if not fpid:
            bad.append(f"{ref}: no footprint")
            continue
        if fpid not in cache:
            fp = load_fp(fpid)
            cache[fpid] = fp
        fp = cache[fpid]
        if fp is None:
            bad.append(f"{ref}: footprint {fpid} does not load")
            continue
        pads = {p.GetNumber() for p in fp.Pads() if p.GetNumber()}
        sym = set(pins.get(ref, {}))
        if pads != sym:
            bad.append(f"{ref} ({fpid}): pads without pin {sorted(pads - sym)}, pins without pad {sorted(sym - pads)}")
    lib_fps = {}
    for lib in ("tube_psu_next", "tube_psu_next_parts"):
        d = os.path.join(ROOT, LIBS[lib])
        for f in sorted(os.listdir(d)):
            if f.endswith(".kicad_mod"):
                fpid = f"{lib}:{f[:-10]}"
                lib_fps[fpid] = cache.get(fpid) or load_fp(fpid)
                if lib_fps[fpid] is None:
                    bad.append(f"{fpid} does not load")
    heights = []
    for fpid, fp in sorted({**cache, **lib_fps}.items()):
        if fp is None:
            continue
        ms = models_of(fp)
        if not ms:
            bad.append(f"{fpid}: no 3D model")
        for name, path, ok in ms:
            if not ok:
                bad.append(f"{fpid}: 3D model missing: {name}")
            else:
                heights.append((step_height(path), fpid))
    used = set(comps.values())
    print(f"check_footprints: {len(comps)} parts, {len(cache)} footprints used, {len(lib_fps)} in lib/tube_psu_next*.pretty; "
          f"pads = symbol pins, 3D models present" + (" - with problems below" if bad else ""))
    tall = sorted(((h, f) for h, f in heights if f in used), reverse=True)[:8]
    print("check_footprints: tallest models (mm): " + ", ".join(f"{f.split(':')[1]} {h:.1f}" for h, f in tall))
    # 3: barrier creepage
    multi = {}
    for ref, pp in pins.items():
        ds = {next(iter(dom[n])) for n in pp.values() if len(dom.get(n, ())) == 1}
        if len(ds) > 1:
            multi[ref] = ds
    if {r for r, ds in multi.items() if "EARTH" not in ds} != setup_project.BARRIERS:
        bad.append(f"parts with pins in two domains {sorted(multi)} != BARRIERS {sorted(setup_project.BARRIERS)}")
    for ref, fpid in sorted(BOARD_VARIANTS.items()):
        fp = lib_fps.get(fpid)
        if fp is None:
            bad.append(f"{ref}: board variant {fpid} does not load")
            continue
        pads = {p.GetNumber() for p in fp.Pads() if p.GetNumber()}
        if pads != set(pins.get(ref, {})):
            bad.append(f"{ref} board variant ({fpid}): pads {sorted(pads)} != symbol pins")
    for ref, fpid in [(r, comps[r]) for r in sorted(multi)] + sorted(BOARD_VARIANTS.items()):
        fp = cache.get(fpid) or lib_fps[fpid]
        obst = edge_obstacles(fp)
        groups = {}
        for p in fp.Pads():
            n = pins[ref].get(p.GetNumber())
            if n and len(dom.get(n, ())) == 1:
                groups.setdefault(next(iter(dom[n])), []).append(pad_poly(p))
        ds = sorted(groups)
        for i in range(len(ds)):
            for j in range(i + 1, len(ds)):
                req = CREEPAGE[frozenset((ds[i], ds[j]))]
                got = creepage(groups[ds[i]], groups[ds[j]], obst)
                ok = got >= req
                if not ok:
                    bad.append(f"{ref}: creepage {ds[i]}-{ds[j]} {got:.2f} mm < {req} mm")
                print(f"check_footprints: {'ok  ' if ok else 'FAIL'} {ref} {fpid.split(':')[1]}: {ds[i]}-{ds[j]} "
                      f"surface path {got:.2f} mm (required {req}){', slot' if obst else ''}")
    # 4: KiCad DRC on the placed barrier parts
    hits = kicad_drc(setup_project.BARRIERS, comps, pins, netpins)
    for r, h in sorted(hits.items()):
        exp = {"creepage"} if r.endswith("_noslot") else set()
        ok = (h == exp) if not exp else ("creepage" in h)
        if not ok:
            bad.append(f"KiCad DRC at {r}: {sorted(h) or 'none'} (expected {sorted(exp) or 'none'})")
        print(f"check_footprints: {'ok  ' if ok else 'FAIL'} KiCad DRC {r}: {sorted(h) or 'no creepage / clearance violation'}"
              + (" (negative control)" if exp else ""))
    if "--dump" in argv:
        for fpid, fp in {**cache, **lib_fps}.items():
            if fp is None or not (fpid.startswith("tube_psu_next") or fpid == NEG_CONTROL[1]):
                continue
            gr = []
            for g in fp.GraphicalItems():
                if g.GetClass() != "PCB_SHAPE":
                    continue
                lay = g.GetLayerName()
                if g.GetShape() == pcbnew.SHAPE_T_CIRCLE:
                    c = g.GetCenter()
                    gr.append({"t": "circle", "l": lay, "c": [c.x / MM, c.y / MM], "r": g.GetRadius() / MM})
                elif g.GetShape() == pcbnew.SHAPE_T_ARC:
                    gr.append({"t": "arc", "l": lay, "p": [[q.x / MM, q.y / MM] for q in (g.GetStart(), g.GetArcMid(), g.GetEnd())]})
                elif g.GetShape() == pcbnew.SHAPE_T_RECTANGLE:
                    a, c = g.GetStart(), g.GetEnd()
                    gr.append({"t": "poly", "l": lay, "p": [[a.x / MM, a.y / MM], [c.x / MM, a.y / MM], [c.x / MM, c.y / MM], [a.x / MM, c.y / MM]]})
                elif g.GetShape() == pcbnew.SHAPE_T_POLY:
                    o = g.GetPolyShape().Outline(0)
                    gr.append({"t": "poly", "l": lay, "p": [[o.CPoint(k).x / MM, o.CPoint(k).y / MM] for k in range(o.PointCount())]})
                else:
                    gr.append({"t": "line", "l": lay, "p": [[g.GetStart().x / MM, g.GetStart().y / MM], [g.GetEnd().x / MM, g.GetEnd().y / MM]]})
            dump[fpid] = {"graphics": gr, "pads": [{"n": p.GetNumber(), "poly": pad_poly(p),
                                                    "drill": p.GetDrillSize().x / MM if p.HasHole() else 0} for p in fp.Pads()]}
        json.dump(dump, open(argv[argv.index("--dump") + 1], "w"))
    for b_ in bad:
        print("check_footprints: FAIL " + b_)
    print("check_footprints: " + ("all footprint / 3D checks passed" if not bad else f"{len(bad)} problems"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
