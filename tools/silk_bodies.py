#!/usr/bin/env python3
"""Footprint bodies of the IPC-built footprints from the Proteus silk screen (stdlib only).

Proteus draws the body of each part as a silk outline. For the footprints that
tools/gen_footprints.py builds from the IPC pads (RM8 chokes, EF20 / EF25 / ETD34 transformers,
common-mode chokes, relay, bridge) the body comes from that outline (spec key `body_poly`, board
coordinates of the spec's `ipc` refdes). This script measures the outlines:

  closed   the smallest closed silk polyline that encloses the centre of the part's pads
           (RM8 octagon, the rectangles of the transformers / chokes / relay);
  box      the bounding box of the silk draws longer than 1 mm inside the pad box + 1.5 mm
           (DB1: Proteus draws the four sides of the body with gaps at the pad corners).

For every other part on the same footprint the outline is measured too and compared with the
reference outline moved onto that part's pads (rigid fit of the pads, mirror allowed): the
footprint body must fit every part within TOL.

  python3 tools/silk_bodies.py           print the measured body_poly values
  python3 tools/silk_bodies.py --check   fail unless tools/gen_footprints.py carries exactly
                                         these values and every part fits
"""
import collections
import importlib.util
import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "p2k"))  # proteus2kicad
from p2k import board, gerber  # noqa: E402

TOL = 0.05   # mm, vertex distance of the fitted outline (silk coordinates are 0.1 um, pads 1 um)
SILK = {"top": "Top Silk Screen", "bottom": "Bottom Silk Screen"}

# footprint (spec name in tools/gen_footprints.py PROJECT) -> (mode, parts); the first part is the
# spec's `ipc` refdes
BODIES = {
    "L_RM8_Proteus": ("closed", ["L1", "L2", "L3"]),
    "Transformer_EF20_2x5_P3.81mm": ("closed", ["TR1"]),
    "Transformer_EF25_2x5_P5.08mm_8pin": ("closed", ["TR2"]),
    "Transformer_ETD34_4x3pads": ("closed", ["TR3"]),
    "L_CommonMode_SCF20-05-550": ("closed", ["CM1", "CM4"]),
    "Relay_Songle_SRD_5pin": ("closed", ["RL1"]),
    "D_Bridge_TBS": ("box", ["DB1"]),
}


def _k(x, y):
    return (round(x, 3), round(y, 3))


def pads_by_refdes():
    recs = json.load(open(board.path("reference", "ipc356_pads.json")))["pads"]
    out = collections.defaultdict(list)
    for p in recs:
        if p["kind"] == "pad":
            out[p["refdes"]].append(p)
    return out


def silk_draws(side):
    g = gerber.parse(board.path(board.config().CADCAM, f"tube_power_5_1_X2 - CADCAM {SILK[side]}.GBR"))
    return [d for d in g.of(gerber.Draw) if d.ap.function != "Profile"
            and math.hypot(d.x2 - d.x1, d.y2 - d.y1) > 1e-6]


def cycles(draws):
    """Closed polylines of the silk: connected components of the draw graph in which every
    vertex has degree 2. Returns [[(x, y), ...]] (not repeated at the end)."""
    adj = collections.defaultdict(set)
    for d in draws:
        a, b = _k(d.x1, d.y1), _k(d.x2, d.y2)
        if a != b:
            adj[a].add(b)
            adj[b].add(a)
    seen, out = set(), []
    for start in adj:
        if start in seen:
            continue
        comp, stack = [], [start]
        seen.add(start)
        while stack:
            v = stack.pop()
            comp.append(v)
            for w in adj[v]:
                if w not in seen:
                    seen.add(w)
                    stack.append(w)
        if len(comp) < 3 or any(len(adj[v]) != 2 for v in comp):
            continue
        ring, prev = [comp[0]], None
        while True:
            nxt = [w for w in adj[ring[-1]] if w != prev][0] if prev else sorted(adj[ring[-1]])[0]
            if nxt == ring[0]:
                break
            prev = ring[-1]
            ring.append(nxt)
        out.append(simplify(ring))
    return out


def simplify(ring):
    """Drop vertices on a straight line (Proteus splits long sides)."""
    pts = list(ring)
    changed = True
    while changed and len(pts) > 3:
        changed = False
        for i in range(len(pts)):
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % len(pts)]
            cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            if abs(cross) / max(math.dist(a, c), 1e-9) < 0.01:
                del pts[i]
                changed = True
                break
    # start at the lowest-left vertex, counter-clockwise (stable output)
    if area(pts) < 0:
        pts.reverse()
    i = min(range(len(pts)), key=lambda i: (pts[i][1], pts[i][0]))
    return pts[i:] + pts[:i]


def area(pts):
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1])) / 2


def inside(pt, poly):
    x, y = pt
    c = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


def measure(mode, pads, draws, rings):
    xs, ys = [p["x_mm"] for p in pads], [p["y_mm"] for p in pads]
    if mode == "closed":
        c = (sum(xs) / len(xs), sum(ys) / len(ys))
        hits = [r for r in rings if inside(c, r)]
        if not hits:
            return None
        return min(hits, key=lambda r: abs(area(r)))
    x0, x1, y0, y1 = min(xs) - 1.5, max(xs) + 1.5, min(ys) - 1.5, max(ys) + 1.5
    sel = [d for d in draws if math.hypot(d.x2 - d.x1, d.y2 - d.y1) > 1.0
           and all(x0 <= x <= x1 and y0 <= y <= y1 for x, y in ((d.x1, d.y1), (d.x2, d.y2)))]
    if not sel:
        return None
    bx = [v for d in sel for v in (d.x1, d.x2)]
    by = [v for d in sel for v in (d.y1, d.y2)]
    return [_k(min(bx), min(by)), _k(max(bx), min(by)), _k(max(bx), max(by)), _k(min(bx), max(by))]


def rigid_fit(src, dst):
    """Rotation (+ optional mirror in x) and translation mapping the points src onto dst (least
    squares). Returns (fn, residual)."""
    best = None
    for mirror in (False, True):
        s = [(-x if mirror else x, y) for x, y in src]
        cs = (sum(p[0] for p in s) / len(s), sum(p[1] for p in s) / len(s))
        cd = (sum(p[0] for p in dst) / len(dst), sum(p[1] for p in dst) / len(dst))
        sxx = sum((a[0] - cs[0]) * (b[0] - cd[0]) + (a[1] - cs[1]) * (b[1] - cd[1]) for a, b in zip(s, dst))
        sxy = sum((a[0] - cs[0]) * (b[1] - cd[1]) - (a[1] - cs[1]) * (b[0] - cd[0]) for a, b in zip(s, dst))
        th = math.atan2(sxy, sxx)
        co, si = math.cos(th), math.sin(th)

        def fn(p, mirror=mirror, cs=cs, cd=cd, co=co, si=si):
            x, y = (-p[0] if mirror else p[0]) - cs[0], p[1] - cs[1]
            return (cd[0] + co * x - si * y, cd[1] + si * x + co * y)
        res = max(math.dist(fn(a), b) for a, b in zip(src, dst))
        if best is None or res < best[1]:
            best = (fn, res)
    return best


def main():
    check = "--check" in sys.argv
    pads = pads_by_refdes()
    draws = {side: silk_draws(side) for side in SILK}
    rings = {side: cycles(draws[side]) for side in SILK}
    errors, measured = [], {}
    for fp, (mode, parts) in BODIES.items():
        polys = {}
        for ref in parts:
            side = "bottom" if pads[ref][0]["side"] == "bottom" else "top"
            poly = measure(mode, pads[ref], draws[side], rings[side])
            if poly is None:
                errors.append(f"{fp}: no silk outline found for {ref}")
                continue
            polys[ref] = poly
        ref0 = parts[0]
        if ref0 not in polys:
            continue
        measured[fp] = polys[ref0]
        for ref in parts[1:]:
            if ref not in polys:
                continue
            # pads matched by pin id (the footprints with several parts have unique pin ids)
            src = [(p["x_mm"], p["y_mm"]) for p in sorted(pads[ref0], key=lambda p: p["pin"])]
            dst = [(p["x_mm"], p["y_mm"]) for p in sorted(pads[ref], key=lambda p: p["pin"])]
            fn, res = rigid_fit(src, dst)
            moved = [fn(v) for v in polys[ref0]]
            worst = max(min(math.dist(m, v) for v in polys[ref]) for m in moved)
            worst = max(worst, max(min(math.dist(m, v) for m in moved) for v in polys[ref]))
            line = f"{fp}: {ref} outline vs {ref0}'s moved onto its pads: worst vertex {worst:.3f} mm (pad fit {res:.3f} mm)"
            print("silk_bodies: " + line)
            if worst > TOL or len(polys[ref]) != len(moved):
                errors.append(line)
    gf = os.path.join(board.root(), "tools", "gen_footprints.py")
    spec = importlib.util.spec_from_file_location("gen_footprints", gf)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for fp, poly in measured.items():
        have = mod.PROJECT.get(fp, {}).get("body_poly")
        want = [tuple(p) for p in poly]
        txt = "[" + ", ".join(f"({x}, {y})" for x, y in want) + "]"
        if not check:
            print(f"silk_bodies: {fp}: body_poly={txt}")
        if have is None or [tuple(p) for p in have] != want:
            errors.append(f"{fp}: tools/gen_footprints.py body_poly differs from the silk: {txt}")
    for e in errors:
        print("silk_bodies: ERROR " + e)
    print(f"silk_bodies: {len(measured)} footprint bodies from the Proteus silk, "
          f"{sum(len(p) for _, p in BODIES.values())} parts" + (", up to date" if check and not errors else ""))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
