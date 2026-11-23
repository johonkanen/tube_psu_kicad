#!/usr/bin/env python3
"""Board queries for the 5.2 design review. Read-only: works on the JSON written by board_dump.py.

    python3 kicad_next/review/tools/bq.py DUMP.json COMMAND ...

Needs python3 with shapely (system python; NOT kipy). All numbers in mm, board coordinates
(x right, y down; the board has negative y, "north" = more negative y). Net names with spaces
or brackets must be quoted: "Net-(R143-Pad2)", "-100V BIAS". A net argument may be a glob
("DHB_*"), a bare refdes ("H4", "J4" = all pads of that footprint whatever their nets - use it for
mounting holes, which have no net; write "fp:GND", "fp:IN2", "fp:PE" where a terminal has the name of a net), a local net without its sheet path ("FLY_C" = "/01 AUX supply/FLY_C"), a refdes.pad ("Q19.2" = the net of that pad) or @CLASS (every net of a net class) or @DOMAIN.
Isolation domains: PRI = classes SIGNAL + PRIMARY_LV + HV_PRIMARY (mains-referenced, ground GND);
SEC = SECONDARY_LV + HV_SECONDARY (ISO_GND); HEATER (HT_GND); UART = UART_ISO (ISO_UART_GND); PE = PE_EARTH.

Commands
  fp REF[,REF..]             footprint: value, library footprint, position, side, rotation, every pad with net
  area X0 Y0 X1 Y1 [--touch] footprints whose origin lies in the box (sorted by x, y), with side and value;
                             --touch: footprints whose courtyard / body box overlaps the box, with that box
  nets [GLOB]                net names with net class, pad count, track length per layer, zone area per layer
  net NET [NET..]            one net in detail: pads, track widths per layer (length per width, the narrowest
                             segments with coordinates), vias, zone areas
  pads NET                   the pads of a net (ref.pad, position, layers)
  dist A B [--layer L]       smallest copper-to-copper distance between net (group) A and B on every layer
                             they share, with the two closest points (x, y). Pads, tracks, vias, zone fill.
  near NET [--within 1.5] [--layer L] [--other-class | --other-domain]
                             every other net with copper closer than --within to NET, per layer, smallest first
                             (--other-class: only nets of a different net class; --other-domain: only nets of
                             another isolation domain, see below)
  padgap REF.PAD REF.PAD     edge-to-edge distance of two pads (any layers) and centre distance
  neck NET LAYER X1 Y1 X2 Y2 widest copper "channel" that joins the two points inside the copper of NET on
                             LAYER (tracks + zone fill + pads + vias): the largest w such that the copper
                             shrunk by w/2 on every side still joins them. 0 = not joined on that layer.
  xsec NET LAYER x|y VALUE [LO HI]
                             copper of NET on LAYER cut by the line x=VALUE (or y=VALUE), optionally only
                             between LO and HI of the other coordinate: the pieces and their summed width
  loop P1 P2 P3 [...]        path length and enclosed area of the closed polygon through the points, each given
                             as "X Y" or as REF.PAD (pad centre) - for a quick estimate of a commutation or gate
                             loop: list the pads in the order the current passes them
  slots                      Edge.Cuts items inside the outline (isolation slots, cut-outs) with their boxes
  holes X0 Y0 X1 Y1          drilled holes (pads, vias, NPTH) in a box
  classes                    net classes with their nets

Pads and vias whose unconnected inner rings are removed ("remove_unused_layers") count on those layers
with their drill diameter only (the plated barrel) - so an inner-layer distance of e.g. 0.5 mm to such a
pad is the distance to the hole wall. `fp` prints "barrel only: <layers>" for such pads.

Limits: zone fill is the fill stored in the board file (check_next.sh refills in a temporary copy only);
distances are 2-D per layer (no layer-to-layer, no creepage along slots edges - a slot between two
points is NOT taken into account by dist / near); polygon approximation error <= 0.005 mm.
"""
import fnmatch
import json
import math
import sys
from collections import defaultdict

from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import nearest_points, unary_union


DOMAIN = {"SIGNAL": "PRI", "PRIMARY_LV": "PRI", "HV_PRIMARY": "PRI", "Default": "PRI",
          "SECONDARY_LV": "SEC", "HV_SECONDARY": "SEC", "HEATER": "HEATER", "UART_ISO": "UART", "PE_EARTH": "PE"}


class Board:
    def __init__(self, path):
        self.d = json.load(open(path))
        self.layers = self.d["layers"]
        self.fp = {f["ref"]: f for f in self.d["footprints"]}
        self.nc = self.d["netclass"]
        self._cu = {}

    def layer(self, name):
        if name in self.layers:
            return name
        m = [l for l in self.layers if l.lower().startswith(name.lower())]
        if len(m) != 1:
            sys.exit(f"layer {name!r}: one of {self.layers}")
        return m[0]

    def resolve(self, arg):
        """net argument -> list of net names"""
        allnets = set(self.nc)
        if arg.startswith("fp:") and arg[3:] in self.fp:
            return [arg]
        if arg in self.fp and not any(n == arg or n.rsplit("/", 1)[-1] == arg for n in allnets):
            return ["fp:" + arg]
        if arg.startswith("@"):
            r = [n for n, c in self.nc.items() if c == arg[1:] or DOMAIN.get(c) == arg[1:]]
        elif arg in allnets:
            r = [arg]
        elif "." in arg and arg.split(".")[0] in self.fp:
            ref, num = arg.split(".", 1)
            r = sorted({p["net"] for p in self.fp[ref]["pads"] if p["num"] == num and p["net"]})
        else:
            r = sorted(n for n in allnets if n.rsplit("/", 1)[-1] == arg) or sorted(fnmatch.filter(allnets, arg))
        if not r:
            sys.exit(f"no net matches {arg!r} (try: bq.py DUMP nets '*{arg}*')")
        return r

    def span(self, v):
        a, b = self.layers.index(v["layers"][0]), self.layers.index(v["layers"][1])
        return self.layers[min(a, b):max(a, b) + 1]

    def copper(self, net, layer):
        """shapely geometry of the copper of one net on one layer"""
        key = (net, layer)
        if key in self._cu:
            return self._cu[key]
        g = []
        if net.startswith("fp:"):
            # every pad of one footprint, whatever its net (mounting-hole rings, a whole connector, ...)
            for p in self.fp[net[3:]]["pads"]:
                if layer in p["layers"] and len(p["poly"]) >= 3:
                    g.append(Polygon(p["poly"]).buffer(0))
                elif p["drill"] and (layer in p.get("barrel_only", []) or not p["layers"]):
                    g.append(Point(p["x"], p["y"]).buffer(p["drill"] / 2, 16))
            u = unary_union(g) if g else None
            self._cu[key] = u
            return u
        for t in self.d["tracks"]:
            if t["net"] == net and t["layer"] == layer:
                pts = [(t["x1"], t["y1"]), (t["x2"], t["y2"])]
                if t.get("arc"):
                    pts.insert(1, (t["xm"], t["ym"]))
                g.append(LineString(pts).buffer(t["w"] / 2, 16))
        for v in self.d["vias"]:
            if v["net"] == net and layer in self.span(v):
                dia = v["drill"] if layer in v.get("barrel_only", []) else v["d"]
                g.append(Point(v["x"], v["y"]).buffer(dia / 2, 16))
        for f in self.d["footprints"]:
            for p in f["pads"]:
                if p["net"] == net and layer in p["layers"] and len(p["poly"]) >= 3:
                    g.append(Polygon(p["poly"]).buffer(0))
                elif p["net"] == net and layer in p.get("barrel_only", []) and p["plated"]:
                    # ring removed on this layer: the plated hole wall is the copper (largest drill dimension)
                    g.append(Point(p["x"], p["y"]).buffer(p["drill"] / 2, 16))
        for z in self.d["zones"]:
            if z["net"] == net and z["layer"] == layer:
                for rings in z["polys"]:
                    if len(rings[0]) >= 3:
                        g.append(Polygon(rings[0], [h for h in rings[1:] if len(h) >= 3]).buffer(0))
        u = unary_union(g) if g else None
        self._cu[key] = u
        return u

    def group(self, nets, layer):
        g = [c for c in (self.copper(n, layer) for n in nets) if c is not None and not c.is_empty]
        return unary_union(g) if g else None


def f2(v):
    return f"{v:.3f}"


def cmd_fp(B, a):
    for ref in ",".join(a).split(","):
        f = B.fp.get(ref)
        if not f:
            print(f"{ref}: not on the board")
            continue
        print(f"{ref}  {f['value']}  {f['fp']}  at ({f['x']}, {f['y']}) rot {f['rot']} side {f['side']}"
              f"  courtyard/body box {f['bbox']}{'  DNP' if f['dnp'] else ''}")
        paste_only = [p for p in f["pads"] if not p["layers"] and not p["drill"]]
        if paste_only:
            print(f"   ({len(paste_only)} paste / aperture pads without copper not listed)")
        for p in f["pads"]:
            if not p["layers"] and not p["drill"]:
                continue
            kind = "SMD" if not p["drill"] else f"drill {p['drill']}" + ("" if p["plated"] else " NPTH")
            print(f"   pad {p['num'] or '-':>4}  ({p['x']:9.3f}, {p['y']:9.3f})  {p['w']}x{p['h']}  {kind:12}  "
                  f"{'/'.join(p['layers']) if len(p['layers']) < 3 else ('all Cu' if not p.get('barrel_only') else '/'.join(p['layers']))}"
                  f"  {p['net']}  [{B.nc.get(p['net'], '')}]"
                  + (f"  barrel only: {'/'.join(p['barrel_only'])}" if p.get("barrel_only") else ""))


def cmd_area(B, a):
    touch = opt(a, "--touch", flag=True)
    x0, y0, x1, y1 = map(float, a[:4])
    x0, x1, y0, y1 = min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)
    for f in sorted(B.d["footprints"], key=lambda f: (f["x"], f["y"])):
        bb = f["bbox"]
        hit = (bb[0] <= x1 and bb[2] >= x0 and bb[1] <= y1 and bb[3] >= y0) if touch else (x0 <= f["x"] <= x1 and y0 <= f["y"] <= y1)
        if hit and touch:
            print(f"{f['ref']:10} {f['side']} box ({bb[0]:7.2f}, {bb[1]:7.2f}) .. ({bb[2]:7.2f}, {bb[3]:7.2f})  {f['value']:22} {f['fp'].split(':')[-1]}")
        elif hit:
            print(f"{f['ref']:10} {f['side']} ({f['x']:8.2f}, {f['y']:8.2f}) rot {f['rot']:6.1f}  {f['value']:24} {f['fp']}")


def net_stats(B, n):
    tl, za = defaultdict(float), defaultdict(float)
    for t in B.d["tracks"]:
        if t["net"] == n:
            tl[t["layer"]] += t["len"]
    for z in B.d["zones"]:
        if z["net"] == n:
            for r in z["polys"]:
                if len(r[0]) >= 3:
                    za[z["layer"]] += Polygon(r[0], [h for h in r[1:] if len(h) >= 3]).buffer(0).area
    return tl, za


def cmd_nets(B, a):
    pat = a[0] if a else "*"
    npads = defaultdict(int)
    for f in B.d["footprints"]:
        for p in f["pads"]:
            npads[p["net"]] += 1
    for n in sorted(fnmatch.filter(B.nc, pat)):
        tl, za = net_stats(B, n)
        print(f"{n:28} [{B.nc[n]:13}] pads {npads[n]:3}  tracks " +
              (", ".join(f"{l} {v:.1f}" for l, v in tl.items()) or "-") + "  zones mm2 " +
              (", ".join(f"{l} {v:.0f}" for l, v in za.items()) or "-"))


def cmd_pads(B, a):
    for n in B.resolve(a[0]):
        print(f"{n} [{B.nc.get(n)}]")
        for f in B.d["footprints"]:
            for p in f["pads"]:
                if p["net"] == n:
                    print(f"   {f['ref']}.{p['num']:4} {f['side']} ({p['x']:9.3f}, {p['y']:9.3f})  "
                          f"{'all Cu' if len(p['layers']) > 2 else '/'.join(p['layers'])}  {f['value']}")


def cmd_net(B, a):
    for arg in a:
        for n in B.resolve(arg):
            print(f"== {n} [{B.nc.get(n)}]")
            pads = [f"{f['ref']}.{p['num']}" for f in B.d["footprints"] for p in f["pads"] if p["net"] == n]
            print(f"   pads ({len(pads)}): {' '.join(pads)}")
            by = defaultdict(lambda: defaultdict(float))
            segs = defaultdict(list)
            for t in B.d["tracks"]:
                if t["net"] == n:
                    by[t["layer"]][t["w"]] += t["len"]
                    segs[t["layer"]].append(t)
            for l in B.layers:
                if l in by:
                    print(f"   tracks {l}: " + ", ".join(f"w {w} mm: {ln:.2f} mm" for w, ln in sorted(by[l].items())))
                    wmin = min(by[l])
                    for t in sorted((t for t in segs[l] if t["w"] == wmin), key=lambda t: -t["len"])[:3]:
                        print(f"        narrowest w {wmin}: ({t['x1']}, {t['y1']}) -> ({t['x2']}, {t['y2']}) len {t['len']:.2f}")
            vs = [v for v in B.d["vias"] if v["net"] == n]
            if vs:
                kinds = defaultdict(int)
                for v in vs:
                    kinds[(v["d"], v["drill"], "-".join(v["layers"]))] += 1
                print("   vias: " + ", ".join(f"{c} x {k[0]}/{k[1]} {k[2]}" for k, c in kinds.items()))
                if len(vs) <= 12:
                    print("        at " + " ".join(f"({v['x']}, {v['y']})" for v in vs))
            _, za = net_stats(B, n)
            for l in B.layers:
                if l in za:
                    c = [z for z in B.d["zones"] if z["net"] == n and z["layer"] == l]
                    bbs = []
                    for z in c:
                        for r in z["polys"]:
                            xs, ys = [p[0] for p in r[0]], [p[1] for p in r[0]]
                            bbs.append(f"[{min(xs):.1f},{min(ys):.1f} .. {max(xs):.1f},{max(ys):.1f}]")
                    print(f"   zone fill {l}: {za[l]:.1f} mm2 in {len(bbs)} piece(s) {' '.join(bbs[:8])}{' ...' if len(bbs) > 8 else ''}")


def opt(a, name, default=None, flag=False):
    if name in a:
        i = a.index(name)
        if flag:
            a.pop(i)
            return True
        v = a[i + 1]
        del a[i:i + 2]
        return v
    return False if flag else default


def cmd_dist(B, a):
    lay = opt(a, "--layer")
    A, Bn = B.resolve(a[0]), B.resolve(a[1])
    Bn = [n for n in Bn if n not in A]
    print(f"A = {A if len(A) < 6 else str(len(A)) + ' nets'}   B = {Bn if len(Bn) < 6 else str(len(Bn)) + ' nets'}")
    for l in ([B.layer(lay)] if lay else B.layers):
        ga, gb = B.group(A, l), B.group(Bn, l)
        if ga is None or gb is None:
            print(f"   {l:14} -  (one side has no copper here)")
            continue
        pa, pb = nearest_points(ga, gb)
        print(f"   {l:14} {ga.distance(gb):7.3f} mm   A ({pa.x:.3f}, {pa.y:.3f})  B ({pb.x:.3f}, {pb.y:.3f})")


def cmd_near(B, a):
    within = float(opt(a, "--within", "1.5"))
    lay = opt(a, "--layer")
    other = opt(a, "--other-class", flag=True)
    otherdom = opt(a, "--other-domain", flag=True)
    A = B.resolve(a[0])
    cls = {B.nc.get(n) for n in A if not n.startswith("fp:")}
    doms = {DOMAIN.get(c) for c in cls}
    rows = []
    for l in ([B.layer(lay)] if lay else B.layers):
        ga = B.group(A, l)
        if ga is None:
            continue
        env = ga.buffer(within + 0.01).bounds
        for n in B.nc:
            if n in A or (other and B.nc[n] in cls) or (otherdom and DOMAIN.get(B.nc[n]) in doms) or (n in sum(([p["net"] for p in B.fp[a[3:]]["pads"]] for a in A if a.startswith("fp:")), [])):
                continue
            g = B.copper(n, l)
            if g is None or g.is_empty:
                continue
            b = g.bounds
            if b[0] > env[2] or b[2] < env[0] or b[1] > env[3] or b[3] < env[1]:
                continue
            dd = ga.distance(g)
            if dd <= within:
                pa, pb = nearest_points(ga, g)
                rows.append((dd, l, n, pa, pb))
    for dd, l, n, pa, pb in sorted(rows, key=lambda r: r[0]):
        print(f"   {dd:6.3f} mm  {l:14} {n:28} [{B.nc[n]:13}]  at ({pa.x:.2f}, {pa.y:.2f}) / ({pb.x:.2f}, {pb.y:.2f})")
    print(f"{len(rows)} net/layer pairs within {within} mm of {A if len(A) < 6 else str(len(A)) + ' nets'}")


def find_pad(B, s):
    ref, num = s.split(".", 1)
    ps = [p for p in B.fp[ref]["pads"] if p["num"] == num]
    if not ps:
        sys.exit(f"{s}: no such pad")
    return ps


def cmd_padgap(B, a):
    pa, pb = find_pad(B, a[0]), find_pad(B, a[1])
    ga = unary_union([Polygon(p["poly"]).buffer(0) for p in pa])
    gb = unary_union([Polygon(p["poly"]).buffer(0) for p in pb])
    print(f"{a[0]} [{pa[0]['net']}] - {a[1]} [{pb[0]['net']}]: edge to edge {ga.distance(gb):.3f} mm, "
          f"centres {math.hypot(pa[0]['x'] - pb[0]['x'], pa[0]['y'] - pb[0]['y']):.3f} mm"
          f"  (layers {pa[0]['layers'][:1]}{'..' if len(pa[0]['layers']) > 1 else ''} / {pb[0]['layers'][:1]}{'..' if len(pb[0]['layers']) > 1 else ''})")


def cmd_neck(B, a):
    nets, l = B.resolve(a[0]), B.layer(a[1])
    p1, p2 = Point(float(a[2]), float(a[3])), Point(float(a[4]), float(a[5]))
    g = B.group(nets, l)
    if g is None:
        sys.exit("no copper of that net on that layer")

    def joined(w):
        s = g.buffer(-w / 2, 8) if w > 0 else g
        parts = list(s.geoms) if hasattr(s, "geoms") else [s]
        tol = w / 2 + 0.05
        for part in parts:
            if not part.is_empty and part.distance(p1) <= tol and part.distance(p2) <= tol:
                return True
        return False

    if g.distance(p1) > 0.05 or g.distance(p2) > 0.05:
        print(f"warning: a point is not on the copper (distances {g.distance(p1):.3f} / {g.distance(p2):.3f} mm)")
    if not joined(0):
        print(f"{nets} on {l}: the two points are NOT joined by copper on this layer alone (0)")
        return
    lo, hi = 0.0, 60.0
    while hi - lo > 0.01:
        mid = (lo + hi) / 2
        if joined(mid):
            lo = mid
        else:
            hi = mid
    print(f"{nets if len(nets) < 4 else len(nets)} on {l}: widest channel joining ({p1.x}, {p1.y}) and ({p2.x}, {p2.y}) = {lo:.2f} mm"
          f"  (1 oz outer: 35 um, inner 0.5 oz: 17.5 um)")


def cmd_xsec(B, a):
    nets, l, axis, val = B.resolve(a[0]), B.layer(a[1]), a[2], float(a[3])
    lo, hi = (float(a[4]), float(a[5])) if len(a) >= 6 else (-1000.0, 1000.0)
    g = B.group(nets, l)
    if g is None:
        sys.exit("no copper of that net on that layer")
    line = LineString([(val, lo), (val, hi)]) if axis == "x" else LineString([(lo, val), (hi, val)])
    cut = g.intersection(line)
    parts = [p for p in (cut.geoms if hasattr(cut, "geoms") else [cut]) if p.length > 0]
    tot = 0.0
    for p in sorted(parts, key=lambda p: p.bounds):
        b = p.bounds
        print(f"   {axis}={val}: from {b[1] if axis == 'x' else b[0]:.3f} to {b[3] if axis == 'x' else b[2]:.3f}  width {p.length:.3f}")
        tot += p.length
    print(f"{nets if len(nets) < 4 else len(nets)} on {l} cut at {axis}={val}: {len(parts)} piece(s), total width {tot:.3f} mm")


def cmd_loop(B, a):
    """perimeter and enclosed area of a closed polygon through the given points / pads"""
    pts = []
    i = 0
    while i < len(a):
        if "." in a[i] and a[i].split(".")[0] in B.fp:
            p = find_pad(B, a[i])[0]
            pts.append((p["x"], p["y"], a[i]))
            i += 1
        else:
            pts.append((float(a[i]), float(a[i + 1]), ""))
            i += 2
    if len(pts) < 3:
        sys.exit("loop: at least three points (x y pairs or REF.PAD)")
    per = area = 0.0
    for k, (x, y, name) in enumerate(pts):
        x2, y2, _ = pts[(k + 1) % len(pts)]
        seg = math.hypot(x2 - x, y2 - y)
        per += seg
        area += x * y2 - x2 * y
        print(f"   ({x:8.3f}, {y:8.3f}) {name:10} -> {seg:6.2f} mm")
    print(f"loop through {len(pts)} points: path {per:.1f} mm, enclosed area {abs(area) / 2:.1f} mm2 "
          f"(plan view, straight lines between the points - an estimate of the loop, not the copper path)")


def cmd_slots(B, a):
    x0, y0, x1, y1 = B.d["outline"]
    print(f"outline box ({x0}, {y0}) .. ({x1}, {y1})  = {x1 - x0:.2f} x {y1 - y0:.2f} mm")
    for e in B.d["edge"]:
        xs = [p[0] for p in e["poly"]] or [e["x1"], e["x2"]]
        ys = [p[1] for p in e["poly"]] or [e["y1"], e["y2"]]
        on_outline = (abs(min(xs) - x0) < 0.3 or abs(max(xs) - x1) < 0.3 or abs(min(ys) - y0) < 0.3 or abs(max(ys) - y1) < 0.3)
        if on_outline and e["shape"] in ("S_SEGMENT", "S_ARC", "Line", "Arc"):
            continue
        print(f"   {e['shape']:10} box ({min(xs):.2f}, {min(ys):.2f}) .. ({max(xs):.2f}, {max(ys):.2f})  "
              f"{max(xs) - min(xs):.2f} x {max(ys) - min(ys):.2f} mm")


def cmd_holes(B, a):
    x0, y0, x1, y1 = map(float, a[:4])
    x0, x1, y0, y1 = min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)
    for h in sorted(B.d["holes"], key=lambda h: (h["x"], h["y"])):
        if x0 <= h["x"] <= x1 and y0 <= h["y"] <= y1:
            print(f"   ({h['x']:8.3f}, {h['y']:8.3f}) d {h['d']}{'x' + str(h['d2']) if h['d2'] != h['d'] else ''} "
                  f"{'PTH ' if h['plated'] else 'NPTH'} {h['ref']:10} {h['net']}")


def cmd_classes(B, a):
    by = defaultdict(list)
    for n, c in B.nc.items():
        by[c].append(n)
    for c in sorted(by):
        print(f"{c} ({len(by[c])}): " + ", ".join(sorted(by[c])))


CMDS = {"fp": cmd_fp, "area": cmd_area, "nets": cmd_nets, "net": cmd_net, "pads": cmd_pads, "dist": cmd_dist,
        "near": cmd_near, "padgap": cmd_padgap, "neck": cmd_neck, "xsec": cmd_xsec, "slots": cmd_slots,
        "holes": cmd_holes, "classes": cmd_classes, "loop": cmd_loop}

if __name__ == "__main__":
    import signal
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)   # quiet with | head
    if len(sys.argv) < 3 or sys.argv[2] not in CMDS:
        sys.exit(__doc__)
    CMDS[sys.argv[2]](Board(sys.argv[1]), sys.argv[3:])
