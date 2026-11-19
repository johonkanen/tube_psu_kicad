#!/usr/bin/env python3
"""REPORT.md + PNGs of the trial 5.2 board built from the 5.1 layout (system python with matplotlib).

    python3 tools/next/trial_report.py

Reads kicad_next/trial_from_51/{build.json, drc.json, drc_51.json, tube_psu_5_2_trial.kicad_pro}
(written by tools/next/reuse_51_board.py) and writes kicad_next/trial_from_51/REPORT.md and *.png.
The hand-written conclusions (rework estimate) are in REWORK below; the tables are generated.
"""
import collections
import json
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Polygon  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = os.path.join(ROOT, "kicad_next", "trial_from_51")
REALLY_CHANGED = ["TR1", "TR3", "L1", "L2", "DRV1", "DRV2", "DRV3", "DRV4", "DRV5", "DRV6", "ISO1", "ISO2",
                  "Q10", "Q11", "PWM2", "J4"]
CLASS_DOMAIN = {"HV_PRIMARY": "PRI", "PRIMARY_LV": "PRI", "SIGNAL": "PRI", "HV_SECONDARY": "SEC",
                "SECONDARY_LV": "SEC", "HEATER": "HEATER", "UART_ISO": "UART", "PE_EARTH": "PE", "Default": "?"}
DOM_COLOR = {"PRI": "#d04040", "SEC": "#e08a00", "HEATER": "#3a9a3a", "UART": "#3a70d0", "PE": "#30a0a0",
             "?": "#888888", "": "#888888"}
# fit search: part -> refs that are expected to move with it (its own loop parts)
FIT = {"TR3": ["C16", "C54", "C55", "C47", "C89", "C90", "C91", "C99", "C100", "C101"],
       "TR1": ["PWM2", "D7", "C45", "C3", "C14", "D14", "D8", "D6", "D29", "C102", "C40", "C44"],
       "L1": [], "L2": [], "ISO2": ["J4", "C98"], "J4": ["ISO2", "C98"]}
ISO_TYPES = {"creepage", "clearance", "hole_clearance"}
# where to zoom (name, x0, y0, x1, y1 in board mm) - filled from the footprint positions
ZOOM_REFS = {"tr3_dab": ["TR3", "DRV5", "DRV6", "Q19", "Q21"], "l1_l2_pfc": ["L1", "L2"],
             "tr1_iso2_j4": ["TR1", "PWM2", "ISO2", "J4"], "heater_iso1": ["ISO1", "TR2", "DRV3", "DRV4"]}


def load(name):
    with open(os.path.join(D, name)) as f:
        return json.load(f)


def net_domains():
    pro = load("tube_psu_5_2_trial.kicad_pro")
    return {p["pattern"]: CLASS_DOMAIN.get(p["netclass"], "?") for p in pro["net_settings"]["netclass_patterns"]}, \
           {p["pattern"]: p["netclass"] for p in pro["net_settings"]["netclass_patterns"]}


NET_RE = re.compile(r"\[([^\]]*)\]")
REF_RE = re.compile(r"\bof ([A-Za-z_]+\d+)\b|^Footprint ([A-Za-z_]+\d+)")
RULE_RE = re.compile(r"rule '([^']+)'|\(([^()]*?) rule\b|'([^']+)' rule")


def item_net(it):
    m = NET_RE.search(it["description"])
    return m.group(1) if m else ""


def item_ref(it):
    m = REF_RE.search(it["description"])
    return (m.group(1) or m.group(2)) if m else ""


def rule_of(v):
    m = RULE_RE.search(v["description"])
    return next((g for g in m.groups() if g), "") if m else ""


class Geo:
    def __init__(self, g):
        self.g = g
        self.pads = []  # (x, y, ref)
        for ref, fp in g["fps"].items():
            for p in fp["pads"]:
                self.pads.append((p[0], p[1], ref))
        self.grid = collections.defaultdict(list)
        for x, y, ref in self.pads:
            self.grid[(int(x // 10), int(y // 10))].append((x, y, ref))

    def nearest_ref(self, x, y):
        best = (1e9, "")
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for px, py, ref in self.grid.get((int(x // 10) + dx, int(y // 10) + dy), ()):
                    d = (px - x) ** 2 + (py - y) ** 2
                    if d < best[0]:
                        best = (d, ref)
        if not best[1]:
            best = min(((px - x) ** 2 + (py - y) ** 2, ref) for px, py, ref in self.pads)
        return best[1]


def court_overlaps(fps, refs):
    """ref -> [(other, side of other, overlap mm2)] for courtyard intersections (shapely)"""
    from shapely.geometry import Polygon as SPoly
    from shapely.ops import unary_union

    def poly(f):
        return unary_union([SPoly(c).buffer(0) for c in f["court"] if len(c) > 2])
    polys = {r: poly(f) for r, f in fps.items()}
    out = {}
    for r in refs:
        if r not in polys:
            continue
        P, res = polys[r], []
        for o, Q in polys.items():
            if o != r and P.intersects(Q):
                a = P.intersection(Q).area
                if a > 0.05:
                    res.append((o, fps[o]["side"], round(a, 1)))
        out[r] = sorted(res, key=lambda x: -x[2])
    return out


def fit_search(build, ref, keep_out_refs=(), reach=25.0, step=1.0):
    """slide the new courtyard of ref over the board (rotations 0 / 90 deg about its origin) and find the
    position with the least same-side courtyard overlap against the parts that stay (5.2 parts minus
    keep_out_refs, which are expected to move with it); returns (overlap at 5.1 place, best overlap,
    dx, dy, rot, blockers at the best place)"""
    from shapely import affinity
    from shapely.geometry import Polygon as SPoly, box
    from shapely.ops import unary_union
    g = build["geometry"]
    fps = g["fps"]
    me = fps[ref]
    P0 = unary_union([SPoly(c).buffer(0) for c in me["court"] if len(c) > 2])
    ex = [p for seg in g["edge"] for p in seg]
    board = box(min(p[0] for p in ex), min(p[1] for p in ex), max(p[0] for p in ex), max(p[1] for p in ex))
    others = []
    for r, f in fps.items():
        if r == ref or r in keep_out_refs or not f["court"]:
            continue
        thru = any(p[2] > 1.2 and p[3] > 1.2 for p in f["pads"]) and r.startswith(("H",))
        if f["side"] != me["side"] and not thru:
            continue
        Q = unary_union([SPoly(c).buffer(0) for c in f["court"] if len(c) > 2])
        if Q.intersects(board):
            others.append((r, Q))

    from shapely.strtree import STRtree
    tree = STRtree([Q for _, Q in others])

    def cost(P):
        if not board.contains(P):
            return 1e9, []
        hits = [(others[k][0], P.intersection(others[k][1]).area) for k in tree.query(P, predicate="intersects")]
        hits = [(r, a) for r, a in hits if a > 0.05]
        return sum(a for _, a in hits), hits
    c0, h0 = cost(P0)
    best = (c0, 0.0, 0.0, 0, h0)
    n = int(reach / step)
    for rot in (0, 90):
        Pr = affinity.rotate(P0, rot, origin=(me["x"], me["y"])) if rot else P0
        for i in range(-n, n + 1):
            for j in range(-n, n + 1):
                P = affinity.translate(Pr, i * step, j * step)
                c, h = cost(P)
                if c < best[0] - 1e-6 or (abs(c - best[0]) < 1e-6 and (i * i + j * j) * step * step < best[1] ** 2 + best[2] ** 2):
                    best = (c, i * step, j * step, rot, h)
    return round(c0, 1), round(best[0], 1), best[1], best[2], best[3], sorted(best[4], key=lambda x: -x[1])


def clusters(points, radius=8.0):
    """single-linkage clusters of (x, y, payload)"""
    n = len(points)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    grid = collections.defaultdict(list)
    for i, (x, y, _) in enumerate(points):
        grid[(int(x // radius), int(y // radius))].append(i)
    for i, (x, y, _) in enumerate(points):
        cx, cy = int(x // radius), int(y // radius)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in grid.get((cx + dx, cy + dy), ()):
                    if j > i and (points[j][0] - x) ** 2 + (points[j][1] - y) ** 2 <= radius ** 2:
                        parent[find(i)] = find(j)
    out = collections.defaultdict(list)
    for i in range(n):
        out[find(i)].append(points[i])
    return sorted(out.values(), key=len, reverse=True)


def main():
    build, drc = load("build.json"), load("drc.json")
    base = load("drc_51.json") if os.path.exists(os.path.join(D, "drc_51.json")) else None
    dom, cls = net_domains()
    geo = Geo(build["geometry"])
    fps = build["geometry"]["fps"]
    vio = drc["violations"]
    types = collections.Counter(v["type"] for v in vio)
    sev = collections.defaultdict(collections.Counter)
    for v in vio:
        sev[v["type"]][v["severity"]] += 1
    base_types = collections.Counter(v["type"] for v in base["violations"]) if base else collections.Counter()

    # --- isolation violations
    iso = []
    for v in vio:
        if v["type"] not in ISO_TYPES:
            continue
        its = v["items"]
        nets = [item_net(i) for i in its]
        doms = [dom.get(n, "") for n in nets]
        rule = rule_of(v)
        pair = "-".join(sorted(d for d in doms if d)) if len(set(doms)) > 1 else (doms[0] if doms else "")
        x = sum(i["pos"]["x"] for i in its) / len(its)
        y = sum(i["pos"]["y"] for i in its) / len(its)
        refs = [item_ref(i) or geo.nearest_ref(i["pos"]["x"], i["pos"]["y"]) for i in its]
        layer = "THT pad/hole"
        for it in its:
            m = re.search(r" on ([A-Za-z0-9.]+)", it["description"])
            if m:
                layer = m.group(1)
                break
        kinds = "/".join(sorted({i["description"].split(" ")[0] for i in its}))
        iso.append(dict(type=v["type"], rule=rule, pair=pair, cross=len(set(d for d in doms if d)) > 1, x=x, y=y,
                        refs=refs, nets=nets, layer=layer, kinds=kinds, desc=v["description"]))
    ex = [p for seg in build["geometry"]["edge"] for p in seg]
    bx0, bx1 = min(p[0] for p in ex), max(p[0] for p in ex)
    by0, by1 = min(p[1] for p in ex), max(p[1] for p in ex)
    for i in iso:
        i["offboard"] = not (bx0 <= i["x"] <= bx1 and by0 <= i["y"] <= by1)
    offboard = [i for i in iso if i["cross"] and i["offboard"]]
    cross = [i for i in iso if i["cross"] and not i["offboard"]]
    same = [i for i in iso if not i["cross"]]
    geo.offboard = offboard

    # --- unconnected by sheet
    unc = drc["unconnected_items"]
    unc_sheet = collections.Counter()
    unc_net = collections.Counter()
    for u in unc:
        r = item_ref(u["items"][0]) or geo.nearest_ref(u["items"][0]["pos"]["x"], u["items"][0]["pos"]["y"])
        unc_sheet[fps.get(r, {}).get("sheet", "?") or "?"] += 1
        unc_net[item_net(u["items"][0])] += 1

    # --- courtyards
    def pairs(viols):
        out = set()
        for v in viols:
            if v["type"] == "courtyards_overlap":
                out.add(frozenset(item_ref(i) for i in v["items"]))
        return out
    cy = pairs(vio)
    cy_base = pairs(base["violations"]) if base else set()
    cy_new = cy - cy_base
    changed_coll = {r: sorted(next(iter(p - {r})) for p in cy if r in p and len(p) == 2) for r in REALLY_CHANGED}
    changed_coll_new = {r: sorted(next(iter(p - {r})) for p in cy_new if r in p and len(p) == 2) for r in REALLY_CHANGED}
    geo.overlaps = court_overlaps(fps, REALLY_CHANGED)
    geo.shorts = collections.defaultdict(set)
    for v in vio:
        if v["type"] == "shorting_items":
            refs = [item_ref(i) for i in v["items"]]
            for r in refs:
                if r in REALLY_CHANGED:
                    geo.shorts[r].update(x for x in refs if x and x != r)

    for f in os.listdir(D):
        if f.startswith("zoom_") and f.endswith(".png"):
            os.remove(os.path.join(D, f))
    draw(build, iso, unc, cy, cy_new, drc)
    write_report(build, drc, base, types, sev, base_types, iso, cross, same, unc, unc_sheet, unc_net,
                 cy, cy_base, cy_new, changed_coll, changed_coll_new, geo)
    if os.path.exists(os.path.join(D, "placement_p1.json")) and os.path.exists(os.path.join(D, "drc_p1.json")):
        write_p1(build, drc, base)
    if os.path.exists(os.path.join(D, "placement_p2.json")) and os.path.exists(os.path.join(D, "drc_p2.json")):
        write_p2()
    if os.path.exists(os.path.join(D, "placement_p3.json")) and os.path.exists(os.path.join(D, "drc_p3.json")):
        write_p3()


# ------------------------------------------------------------------------------------------- drawing
def base_axes(g, title, figsize=(16, 11.5), box=None):
    fig, ax = plt.subplots(figsize=figsize)
    for (x0, y0), (x1, y1) in g["edge"]:
        ax.plot([x0, x1], [y0, y1], color="#c9a000", lw=1.2)
    ax.set_aspect("equal")
    ax.invert_yaxis()
    ax.set_title(title, fontsize=11)
    if box:
        ax.set_xlim(box[0], box[2])
        ax.set_ylim(box[3], box[1])
    else:
        xs = [p[0][0] for p in g["edge"]] + [p[1][0] for p in g["edge"]]
        ys = [p[0][1] for p in g["edge"]] + [p[1][1] for p in g["edge"]]
        ax.set_xlim(min(xs) - 3, max(xs) + 3)
        ax.set_ylim(max(ys) + 3, min(ys) - 3)
    ax.tick_params(labelsize=7)
    return fig, ax


def draw_copper(ax, g, dom, layers=("F.Cu", "B.Cu", "In1.Cu", "In4.Cu"), alpha=0.35):
    for layer in layers:
        for z in g["zones"].get(layer, []):
            if len(z["pts"]) > 2:
                ax.add_patch(Polygon(z["pts"], closed=True, fc=DOM_COLOR.get(dom.get(z["net"], ""), "#888"),
                                     ec="none", alpha=alpha * 0.45))
        for x0, y0, x1, y1, w in g["tracks"].get(layer, []):
            ax.plot([x0, x1], [y0, y1], color="#555555" if layer in ("F.Cu", "B.Cu") else "#9a9a9a",
                    lw=max(0.3, w * 0.9), alpha=0.6, solid_capstyle="round")


def draw_fps(ax, g, dom, highlight=(), labels=True, label_set=None, fs=3.5):
    for ref, fp in g["fps"].items():
        hl = ref in highlight
        for c in fp["court"]:
            ax.add_patch(Polygon(c, closed=True, fill=False, ec="#c000c0" if hl else "#999999",
                                 lw=1.4 if hl else 0.4, ls="-" if fp["side"] == "F" else "--"))
        for x, y, w, h, net in fp["pads"]:
            ax.add_patch(plt.Rectangle((x - w / 2, y - h / 2), w, h, fc=DOM_COLOR.get(dom.get(net, ""), "#aaa"),
                                       ec="none", alpha=0.8))
        if labels and (label_set is None or ref in label_set or hl):
            ax.text(fp["x"], fp["y"], ref, fontsize=max(7, fs + 2) if hl else fs, ha="center", va="center",
                    color="#900090" if hl else "#333333", weight="bold" if hl else "normal", clip_on=True)


def legend_dom(ax):
    from matplotlib.lines import Line2D
    h = [Line2D([0], [0], marker="s", ls="", color=c, label=d) for d, c in DOM_COLOR.items() if d not in ("?", "")]
    return h


def draw(build, iso, unc, cy, cy_new, drc):
    dom, _ = net_domains()
    g = build["geometry"]
    from matplotlib.lines import Line2D
    # 1. isolation overview
    fig, ax = base_axes(g, "Trial 5.2 board (5.1 layout): isolation violations between domains "
                           "(x clearance, o creepage; colour = domain pair); copper tinted by domain")
    draw_copper(ax, g, dom)
    draw_fps(ax, g, dom, highlight=REALLY_CHANGED, label_set=set())
    pcol = {"PRI-SEC": "#ff0000", "HEATER-PRI": "#00a000", "PRI-UART": "#0050ff", "SEC-UART": "#8000ff",
            "HEATER-SEC": "#ff8000", "PE-PRI": "#00b0b0", "PE-SEC": "#00b0b0"}
    for i in iso:
        if not i["cross"]:
            continue
        ax.plot(i["x"], i["y"], marker="x" if i["type"] != "creepage" else "o", ms=5, mfc="none",
                color=pcol.get(i["pair"], "#000"), mew=1.0)
    hs = [Line2D([0], [0], marker="o", ls="", mfc="none", color=c, label=p) for p, c in pcol.items() if p != "PE-SEC"]
    ax.legend(handles=hs + legend_dom(ax), loc="lower left", fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(os.path.join(D, "isolation.png"), dpi=130)
    plt.close(fig)

    # 2. courtyards + changed footprints
    fig, ax = base_axes(g, "Courtyards (dashed = bottom side); magenta = the 16 really changed footprints at their 5.1 "
                           "place; blue = new courtyard overlaps vs 5.1; grey line = unrouted")
    draw_fps(ax, g, dom, highlight=REALLY_CHANGED)
    for u in unc:
        a, b = u["items"][0]["pos"], u["items"][-1]["pos"]
        ax.plot([a["x"], b["x"]], [a["y"], b["y"]], color="#777777", lw=0.3, alpha=0.6)
    for v in drc["violations"]:
        if v["type"] == "courtyards_overlap" and frozenset(item_ref(i) for i in v["items"]) in cy_new:
            a, b = v["items"][0]["pos"], v["items"][1]["pos"]
            ax.plot([(a["x"] + b["x"]) / 2], [(a["y"] + b["y"]) / 2], "o", ms=6, mfc="none", color="#0050ff")
    # include the off-board added parts
    xs = [fp["x"] for fp in g["fps"].values()]
    ys = [fp["y"] for fp in g["fps"].values()]
    ax.set_ylim(max(ys) + 8, min(ys) - 8)
    ax.set_xlim(min(xs) - 8, max(xs) + 8)
    fig.tight_layout()
    fig.savefig(os.path.join(D, "courtyards.png"), dpi=130)
    plt.close(fig)

    # 3. zooms
    for name, refs in ZOOM_REFS.items():
        pts = [p for r in refs if r in g["fps"] for c in g["fps"][r]["court"] for p in c]
        if not pts:
            continue
        box = (min(p[0] for p in pts) - 10, min(p[1] for p in pts) - 10, max(p[0] for p in pts) + 10,
               max(p[1] for p in pts) + 10)
        fig, ax = base_axes(g, f"{name}: copper by domain, courtyards (magenta = changed), "
                               "isolation violations (x clearance / o creepage), blue squares = new courtyard overlaps",
                            figsize=(12, 12 * (box[3] - box[1]) / (box[2] - box[0]) + 0.6), box=box)
        draw_copper(ax, g, dom, alpha=0.5)
        draw_fps(ax, g, dom, highlight=REALLY_CHANGED,
                 label_set={r for r, fp in g["fps"].items() if box[0] < fp["x"] < box[2] and box[1] < fp["y"] < box[3]}, fs=6)
        for i in iso:
            if i["cross"] and box[0] < i["x"] < box[2] and box[1] < i["y"] < box[3]:
                ax.plot(i["x"], i["y"], marker="x" if i["type"] != "creepage" else "o", ms=7, mfc="none",
                        color=pcol.get(i["pair"], "#000"), mew=1.2)
        for v in drc["violations"]:
            if v["type"] == "courtyards_overlap" and frozenset(item_ref(i) for i in v["items"]) in cy_new:
                a, b = v["items"][0]["pos"], v["items"][1]["pos"]
                ax.plot([(a["x"] + b["x"]) / 2], [(a["y"] + b["y"]) / 2], "s", ms=8, mfc="none", color="#0050ff")
        fig.tight_layout()
        fig.savefig(os.path.join(D, f"zoom_{name}.png"), dpi=120)
        plt.close(fig)


# ------------------------------------------------------------------------------------------- report
def layer_overlaps(build):
    from shapely.geometry import Polygon as SPoly
    from shapely.ops import unary_union
    dom, _ = net_domains()
    z = build["geometry"]["zones"]
    per = {}
    for layer, items in z.items():
        d = collections.defaultdict(list)
        for it in items:
            if len(it["pts"]) > 2:
                d[dom.get(it["net"], "?")].append(SPoly(it["pts"]).buffer(0))
        per[layer] = {k: unary_union(v) for k, v in d.items()}
    rows = []
    layers = ["F.Cu", "In1.GND", "In4.GND", "B.Cu"]
    for i, a in enumerate(layers):
        for b in layers[i + 1:]:
            for da, pa in per.get(a, {}).items():
                for db, pb in per.get(b, {}).items():
                    if da == db or "?" in (da, db):
                        continue
                    ar = pa.intersection(pb).area
                    if ar > 1:
                        rows.append([f"{a} / {b}", f"{da} / {db}", round(ar)])
    return sorted(rows, key=lambda r: -r[2])


def table(rows, head):
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def write_report(build, drc, base, types, sev, base_types, iso, cross, same, unc, unc_sheet, unc_net,
                 cy, cy_base, cy_new, changed_coll, changed_coll_new, geo):
    g = build["geometry"]
    L = []
    w = L.append
    w("# Trial 5.2 board from the 5.1 layout – DRC and rework estimate")
    w("")
    w("Generated by `tools/next/trial_report.py` from the board that `tools/p2k/bin/kipy tools/next/reuse_51_board.py` "
      "builds (`kicad_next/trial_from_51/tube_psu_5_2_trial.kicad_pcb`, its own project with copies of the 5.2 "
      "`.kicad_pro` / `.kicad_dru`). The real 5.2 board `kicad_next/tube_psu_5_2.kicad_pcb` (empty shell) is not "
      f"touched. DRC: KiCad {drc.get('kicad_version', '')}, `--severity-all`, zones refilled with the 5.2 rules first. "
      "kicad-cli's creepage test on the whole board needs more than 3 GB, so the DRC runs in passes (refill; every "
      "check except creepage; creepage with only the F.Cu zones; creepage with only the B.Cu zones – the creepage "
      "rules are outer-layer only) and `drc.json` merges them: "
      + ", ".join(f"{k} {v}" for k, v in drc.get("passes", {}).items()) + ".")
    w("")
    w("## What the script did")
    w("")
    w("**Layer mapping** (6-layer JLC06161H-3313 stack of `make_board.py`; only 4 layers carry copper for now):")
    w("")
    w(table([["F.Cu", "F.Cu (L1)", "outer, 1 oz"], ["In1.Cu (GND planes, 131 mm of track)", "In1.GND (L2)",
              "0.0994 mm below F.Cu"], ["–", "In2.Signal_HV (L3)", "**empty**"], ["–", "In3.Power (L4)", "**empty**"],
             ["In2.Cu (2.0 m of routing + pours)", "In4.GND (L5)", "0.0994 mm above B.Cu"], ["B.Cu", "B.Cu (L6)", "outer, 1 oz"]],
            ["5.1 layer", "trial layer", "note"]))
    w("")
    w("Why: in JLC's 4-layer stack the 5.1 In1 / In2 sit one thin prepreg under F.Cu / over B.Cu – the same place as "
      "L2 / L5 of the 6-layer stack – so each 5.1 inner layer keeps its outer-layer neighbour and reference distance, "
      "the copper stays symmetric about the centre (warp), and the two free layers L3 / L4 are the adjacent pair in "
      "the middle (0.11 mm 2116 prepreg between them) for the later signal / power-pour rework. "
      "Note: the stack's L1–L2 and L5–L6 prepregs are 0.0994 mm, so 5.1 copper of two domains overlapping across "
      "F.Cu/In1 or In4/B.Cu is not reinforced solid insulation (README D6) – KiCad does not check that.")
    w("")
    c = build["counts"]
    w(f"**Footprints** (5.2 netlist by refdes): unchanged {c.get('unchanged', 0)}, library copy with identical pads "
      f"(new 3D model / can height, tracks kept) {c.get('library copy', 0)}, **changed {c.get('changed', 0)}**, "
      f"removed {c.get('removed', 0)}, added {c.get('added', 0)} (placed off-board below the outline, grouped by sheet), "
      f"mounting holes {c.get('hole', 0)}, board-only free pads WP1–WP4 {c.get('board only', 0)} (kept, re-netted).")
    w("")
    w(f"- changed (new 5.2 footprint at the 5.1 position / rotation / side; L1 / L2 at 0°, `reuse_51_board.NEW_ORIENTATION`): {', '.join(sorted(build['changed']))}")
    w(f"- removed: {', '.join(sorted(build['removed']))}")
    w(f"- added: {', '.join(build['added'])}")
    w("")
    rows = []
    for r, d in sorted(build["changed_detail"].items()):
        rows.append([r, d["old"].split(":")[1], d["new"].split(":")[1], f"{d['x']}, {d['y']}", d["rot"], d["side"],
                     f"{d['old_court'][0]} × {d['old_court'][1]}", f"{d['new_court'][0]} × {d['new_court'][1]}"])
    w(table(rows, ["ref", "5.1 footprint", "5.2 footprint", "pos (mm)", "rot", "side", "5.1 courtyard", "5.2 courtyard"]))
    w("")
    w(f"**Nets**: {len(build['renamed'])} 5.1 copper nets renamed through the pads of kept footprints "
      f"({', '.join(f'{o} → {n}' for o, n in sorted(build['renamed'].items()))}); nets with no 5.2 counterpart "
      f"(copper deleted): {', '.join(build['unmapped_nets']) or 'none'}. Split nets (pads of one 5.1 net now on several "
      f"5.2 nets; tracks follow the majority, the minority pads lose their touching segments): "
      f"{'; '.join(f'{o}: {v}' for o, v in build['split_nets'].items()) or 'none'}. "
      f"Pads of kept footprints whose net differs from the mapped 5.1 net: {len(build['pad_net_changes'])}.")
    w("")
    dc = build["deleted_copper"]
    w(f"**Copper deleted**: {sum(dc.values())} items ({', '.join(f'{k} {v}' for k, v in sorted(dc.items()))}); "
      f"by part: {', '.join(f'{k} {v}' for k, v in list(build['deleted_by_ref'].items())[:25])}. "
      f"Zones deleted (net gone): {', '.join(build['zones_deleted']) or 'none'}; re-netted: "
      f"{', '.join(f'{o} → {n}' for o, n in build['zones_renet']) or 'none'}.")
    w("")

    w("## DRC result by type")
    w("")
    rows = [[t, n, ", ".join(f"{s} {k}" for s, k in sev[t].items()), base_types.get(t, 0)] for t, n in types.most_common()]
    rows.append(["**unconnected items**", len(unc), "", len(base["unconnected_items"]) if base else ""])
    w(table(rows, ["violation type", "trial 5.2", "severity", "5.1 board (own rules)"]))
    w("")
    w("The 5.1 column is the same DRC on `kicad/tube_psu.kicad_pcb` with its own project rules (`drc_51.json`): the "
      "Proteus migration already had courtyard / silk overlaps, so only the difference is caused by 5.2.")
    w("")

    w("## Isolation (domain-to-domain custom rules)")
    w("")
    by_pair = collections.defaultdict(collections.Counter)
    for i in cross:
        by_pair[i["pair"]][f"{i['type']} {i['layer']}"] += 1
    rows = [[p, sum(v.values()), ", ".join(f"{k} {n}" for k, n in v.most_common())]
            for p, v in sorted(by_pair.items(), key=lambda x: -sum(x[1].values()))]
    w(f"**{len(cross)} clearance / creepage violations between two isolation domains on the board** (of {len(iso)} "
      f"clearance / hole-clearance / creepage violations; {len(same)} are inside one domain – HV functional 1.2 mm on "
      f"the outer layers, net-class clearances – and {len(geo.offboard)} are between the added parts in the "
      "off-board grid, ignored here).")
    w("")
    w(table(rows, ["domain pair", "count", "by type / layer (first item)"]))
    w("")
    by_rule = collections.defaultdict(collections.Counter)
    n_rule = collections.Counter()
    for i in iso:
        if i["offboard"]:
            continue
        r = i["rule"] or re.sub(r"\s*\(.*", "", i["desc"])
        if "netclass" in i["desc"]:
            r = "net class clearance (" + re.search(r"netclass '([^']+)'", i["desc"]).group(1) + ")"
        n_rule[(r, i["type"])] += 1
        for sh in {g["fps"].get(ref, {}).get("sheet", "") or "board-only items" for ref in i["refs"]}:
            by_rule[(r, i["type"])][sh] += 1
    rows = [[r, t, n, ", ".join(f"{k} {c}" for k, c in by_rule[(r, t)].most_common(3))]
            for (r, t), n in n_rule.most_common()]
    w("All clearance / hole-clearance / creepage violations on the board by rule (sheets of the parts involved):")
    w("")
    w(table(rows, ["rule", "type", "count", "top sheets"]))
    w("")
    w("**Hot spots** (violations chained within 3 mm; refs = parts owning or nearest to the items):")
    w("")
    rows = []
    for cl in clusters([(i["x"], i["y"], i) for i in cross], 3.0)[:25]:
        its = [p[2] for p in cl]
        refs = collections.Counter(r for i in its for r in i["refs"] if r)
        sheets = collections.Counter(g["fps"].get(r, {}).get("sheet", "?") for r in refs.elements())
        pairs = collections.Counter(i["pair"] for i in its)
        layers = collections.Counter(i["layer"] for i in its)
        cx = sum(p[0] for p in cl) / len(cl)
        cyy = sum(p[1] for p in cl) / len(cl)
        ext = f"{max(p[0] for p in cl) - min(p[0] for p in cl):.0f} × {max(p[1] for p in cl) - min(p[1] for p in cl):.0f}"
        kinds = collections.Counter(k for i in its for k in i["kinds"].split("/"))
        rows.append([len(cl), f"{cx:.0f}, {cyy:.0f}", ext, ", ".join(f"{k} {n}" for k, n in kinds.most_common()), ", ".join(f"{p} {n}" for p, n in pairs.most_common()),
                     ", ".join(f"{lname} {n}" for lname, n in layers.most_common()),
                     ", ".join(r for r, _ in refs.most_common(8)), ", ".join(s for s, _ in sheets.most_common(2))])
    w(table(rows, ["n", "centre x, y (mm)", "extent (mm)", "item kinds", "domain pairs", "layers", "parts", "sheets"]))
    w("")
    by_sheet = collections.Counter()
    for i in cross:
        for r in set(i["refs"]):
            by_sheet[g["fps"].get(r, {}).get("sheet", "?")] += 1
    w("By sheet of the parts involved (a violation counts once per sheet of each of its two items): "
      + ", ".join(f"{s} {n}" for s, n in by_sheet.most_common()) + ".")
    w("")
    w("![isolation](isolation.png)")
    w("")

    w("## Unrouted connections")
    w("")
    w(f"{len(unc)} unconnected items (ratsnest lines). By sheet (of the first item's part):")
    w("")
    w(table([[s, n] for s, n in unc_sheet.most_common()], ["sheet", "unrouted"]))
    w("")
    w("Nets with most unrouted connections: " + ", ".join(f"{n or '(none)'} {k}" for n, k in unc_net.most_common(15)) + ".")
    w("")

    w("## Footprint collisions of the changed parts (courtyard overlaps)")
    w("")
    w(f"Courtyard overlaps: {len(cy)} pairs on the trial board, {len(cy_base)} on the 5.1 board, **{len(cy_new)} new**.")
    w("")
    rows = []
    for r in REALLY_CHANGED:
        d = build["changed_detail"].get(r)
        if not d:
            rows.append([r, "(footprint unchanged)", "", "", "", ""])
            continue
        side = d["side"]
        same = [f"{o} {a}" for o, sd, a in geo.overlaps.get(r, []) if sd == side]
        other = [o for o, sd, a in geo.overlaps.get(r, []) if sd != side]
        rows.append([r, f"{d['new'].split(':')[1]} ({side})", ", ".join(same) or "–",
                     ", ".join(changed_coll_new[r]) or "–", ", ".join(sorted(geo.shorts.get(r, ()))) or "–",
                     ", ".join(other) or "–"])
    w("Courtyard intersections computed from the footprint courtyards (mm² of overlap, same side = a real body "
      "collision); 'new in DRC' = KiCad courtyards_overlap pairs not present on the 5.1 board; 'pad shorts' = "
      "copper of the new footprint touching another part's pad (KiCad shorting_items); 'other side' = parts on "
      "the opposite side under the courtyard (only a problem where THT leads / solder joints land on them).")
    w("")
    w(table(rows, ["ref", "5.2 footprint (side)", "same-side overlap (mm²)", "new in DRC", "pad shorts",
                   "other side under it"]))
    w("")
    w("### Does the new part fit near its 5.1 place?")
    w("")
    w("The 5.2 courtyard is slid over a ±25 mm window (1 mm steps, 0° / 90° about the 5.1 origin) and the "
      "same-side courtyard overlap with every part that stays is summed (mounting holes count on both sides; "
      "the parts of the power stage that move with the part are excluded, listed per row). The 5.1 footprint "
      "of a removed part (L3) no longer blocks anything.")
    w("")
    rows = []
    for ref, mates in FIT.items():
        if ref not in build["geometry"]["fps"]:
            continue
        c0, c, dx, dy, rot, hits = fit_search(build, ref, mates)
        rows.append([ref, ", ".join(mates) or "–", c0 if c0 < 1e8 else "crosses the board edge",
                     c if c < 1e8 else "no position inside the board", f"{dx:+.0f}, {dy:+.0f}" if c < 1e8 else "–", rot,
                     ", ".join(f"{r} {a:.0f}" for r, a in hits[:6]) or "free"])
    w(table(rows, ["ref", "moves with it (excluded)", "overlap at 5.1 place (mm²)", "best overlap (mm²)",
                   "best shift dx, dy (mm)", "rot", "still blocked by (mm²)"]))
    w("")
    oc = build.get("old_courtyards", {})
    if "L3" in oc and "TR3" in oc:
        from shapely.geometry import Polygon as SPoly
        from shapely.ops import unary_union
        etd = unary_union([SPoly(c).buffer(0) for c in oc["TR3"]["court"] if len(c) > 2])
        l3 = unary_union([SPoly(c).buffer(0) for c in oc["L3"]["court"] if len(c) > 2])
        ec = unary_union([SPoly(c).buffer(0) for c in build["geometry"]["fps"]["TR3"]["court"] if len(c) > 2])
        free = etd.union(l3)
        bx = free.bounds
        w(f"**TR3 EC42 vs ETD34 + L3:** 5.1 courtyards ETD34 {etd.area:.0f} mm² + L3 {l3.area:.0f} mm² "
          f"(union bounding box {bx[2] - bx[0]:.1f} × {bx[3] - bx[1]:.1f} mm at x {bx[0]:.1f}…{bx[2]:.1f}, "
          f"y {bx[1]:.1f}…{bx[3]:.1f}); EC42 courtyard {ec.area:.0f} mm² "
          f"({ec.bounds[2] - ec.bounds[0]:.1f} × {ec.bounds[3] - ec.bounds[1]:.1f} mm). At the 5.1 origin "
          f"{ec.difference(free).area:.0f} mm² of the EC42 courtyard lie outside the freed ETD34 + L3 area.")
        w("")
    w("![courtyards](courtyards.png)")
    w("")
    for name in ZOOM_REFS:
        if os.path.exists(os.path.join(D, f"zoom_{name}.png")):
            w(f"![{name}](zoom_{name}.png)")
            w("")
    w("## Zone fill: how far the pours are pulled back by the 5.2 rules")
    w("")
    zf = build["zone_fill"]
    tot51 = sum(z["area51"] for z in zf)
    tot52 = sum(z["area52"] for z in zf)
    w(f"Filled copper of the kept 5.1 zones: {tot51:.0f} mm² in 5.1, {tot52:.0f} mm² refilled with the 5.2 rules "
      f"({100 * (tot52 - tot51) / tot51 if tot51 else 0:+.0f} %). The zone filler applies the domain clearances "
      "(4.0 / 11.1 / 8.0 mm…) itself, so pours cause few DRC markers – the cost shows up as lost copper instead. "
      "Largest losses:")
    w("")
    rows = sorted(zf, key=lambda z: z["area52"] - z["area51"])[:15]
    w(table([[z["net"], "/".join(z["layers"]), z["area51"], z["area52"],
              f"{100 * (z['area52'] - z['area51']) / z['area51']:+.0f} %" if z["area51"] else "–"] for z in rows],
            ["zone net", "layer", "5.1 mm²", "5.2 mm²", "change"]))
    w("")
    w("## Copper of two domains overlapping on different layers (solid insulation)")
    w("")
    w("README D6: the 0.0994 / 0.1088 mm prepregs are not reinforced solid insulation, so copper of two domains must "
      "not overlap on any pair of layers. KiCad does not check this; overlap of the refilled zone copper "
      "(polygons decimated to ≤ 400 points, tracks not counted):")
    w("")
    w(table(layer_overlaps(build), ["layers", "domain pair", "overlap mm²"]))
    w("")
    w(REWORK)
    with open(os.path.join(D, "REPORT.md"), "w") as f:
        f.write("\n".join(L) + "\n")
    print(f"trial_report: wrote {os.path.relpath(os.path.join(D, 'REPORT.md'), ROOT)}")


REWORK = """## Rework estimate

Written after reviewing the numbers of the first trial (commit d3f1063, L1 / L2 still the flat-lying toroid
footprint at the RM8 place); the tables above are regenerated, this text is not. Since 2026-11-19 L1 / L2 are the
upright toroids on the RM8 holes (item 6 is superseded) and TR3 / the split caps / DRV5 / DRV6 have a first
placement (item 1): see **After placement step 1** at the end.

**Overall.** 273 of the 315 5.1 parts stay where they are with their tracks (243 unchanged footprints + 30 library
copies with identical pads); 31 footprints changed (the 16 listed parts plus 15 passives that only grew a size:
1206 → 1210 630 V caps, 0805 → 1206 start-up resistors, C58 → SMD electrolytic – all fit in place, no new
collisions); 11 parts removed, 58 added (off-board grid). 644 of the 3672 5.1 copper items (17.5 %) were deleted
because they ended on a changed / removed part or a re-netted pad; the 5.1 pours refill to −9 % copper. The 5.1
layout already has one primary / secondary barrier line (red / orange in `isolation.png`) and per-domain GND
planes on In1 / In4 that are stacked domain-on-domain (no zone copper of two domains overlaps across layers), so
most of the board survives; the rework is concentrated in five spots along the barriers.

**Can stay as built (only local nudges):**
- PFC power stage and mains input (sheet 05) apart from L1 / L2: 22 PE-PRI basic markers (3.2 mm creepage at the
  Y caps / RL1 / CM1 / C85 pads) – pad-spacing fixes or a short slot.
- Measurement and MCU-connector centre (sheets 08 / 09 / 10, J2 and its filters): a few net-class / HV-functional
  clearances, mounting-hole spacings at H2 / H5 / H6 (3.2 / 4.2 mm creepage from the earthed screws).
- Heater power stage (Q13 / Q14, TR2 primary) and the secondary DAB rectifier / output side (C19 / C30 / C28 / C29 /
  C37 / C56, outputs on the right edge): no isolation markers apart from the barrier spots below.
- Q10 / Q11 (TO-220 → DPAK at the same place): no collision, only their 30 segments to reconnect.
- DRV1 / DRV2 (DFN → SOT-23-6): fit in place, ~30 segments each to re-route.
- 126 'HV functional 1.2 mm' (07 DHB 53) and ~55 net-class clearances inside one domain: track nudges, mostly in
  the gate-drive areas.

**Needs re-placement and re-routing:**
1. **DAB transformer TR3 (EC42) – top right.** The EC42 courtyard (47 × 43 mm, 2020 mm²) is 3 mm taller than the
   whole ETD34 + L3 space (53 × 40 mm); at the 5.1 origin 825 mm² lie outside it. On the top side it fits at the
   5.1 origin only if the split caps C16 / C55 (secondary) and C54 (primary) move – which the plan wants anyway
   (C47 / C54 at the primary pins, C16 / C55 at the secondary pins). Its 16 THT pins land in the bottom-side gate
   drive cluster: DRV5 / DRV6 (now SOIC-16W), their bootstrap / decoupling parts and D18 / D30 / D31 / D34 / R26 /
   R41 / R46 / R53 / R57 / R58 / R90 / R92 sit under the courtyard (pad shorts with DRV5 / C92 / C95, mask
   bridges). → Re-place TR3 + split caps and move DRV5 / DRV6 with ~20 parts out from under it (they go next to
   their MOSFETs anyway), keep the 12 mm keep-out under the divider free, re-route both half-bridge loops
   (DHB_CAP, DHB_HI_SOURCE / TRANS_SEC, DHB_HI_SOURCE_SEC; ~90 segments deleted around TR3 / DRV5 / DRV6).
2. **TO-247 row on the heatsink (Q7 / Q19 primary next to Q21 / Q8 secondary, y ≈ −42).** 38 PRI-SEC markers at
   Q19 / Q21: the Q19 gate pin and the Q21 source pin are 6.5 mm apart (4.6 mm pad edge to pad edge) – enough for
   the 4.0 mm clearance, not for 11.1 mm creepage, and secondary tracks on In4 run 5–10 mm from the Q19 barrels
   (inner rule 11.1 mm). → A milled slot between Q19 and Q21 (long enough to give 11.1 mm around it) or ≥ 6.5 mm
   more spacing in the row, and no secondary copper on In1 / In4 within 11.1 mm of the primary barrels. The
   heatsink is primary / earthed, so the secondary devices need reinforced insulation to the plate. The
   remaining markers there are HV-functional 1.2 mm nudges of the gate tracks (R22 / R53 / R57 / R58).
3. **J4 / UART island – right centre.** J4 is now the isolated FTDI header (UART island behind U11, which is still
   off-board) but sits inside primary copper: 258 PRI-UART markers (8 mm creepage, 8 mm inner clearance and hole
   clearance to ~150 primary vias). It also overlaps the larger ISO2. → Move J4 + U11 to a board edge, U11's 8 mm
   slot on the island boundary, island copper (ISO_UART_GND / UART nets) separate, primary vias and pours pulled
   back 8 mm (all layers).
4. **ISO2 (Slot 11.1) / TR1 outputs – right centre.** 18 PRI-SEC markers at (65, −21): the primary 15 V rectifier
   D5 and the secondary 15V_ISO_SEC rectifier D4 sit side by side, the ISO2 slot cuts into D4's pad
   (copper-edge clearance) and J4. → Put ISO2 across the barrier line and split the TR1 output rectifiers to their
   domain sides.
5. **Flyback TR1 (EEL19) + PWM2 – bottom right.** EEL19 courtyard 16.9 × 30.1 vs EF20 14.6 × 22.4: collides with
   PWM2 (33 mm²; PWM2 is a new DSO-12) and 8 small parts (D7, D8, D14, C3, C14, C40, C44, C45); 55 segments deleted
   around TR1. The fit search finds TR1 free at its 5.1 origin once these ~12 loop parts move. 14 PRI-SEC markers
   at C102 (secondary −100 V bias cap) next to the primary fly-lead pins at y ≈ 11. → Re-place PWM2, clamp and
   rectifier parts around the EEL19, move C102 (or the fly-lead side) to keep 11.1 mm.
6. **(superseded 2026-11-19: upright toroids on the RM8 holes, see step 1)** **PFC chokes L1 / L2 (toroids Ø 32.6 mm courtyard vs RM8 22 × 22).** L1 crosses the board edge at its 5.1
   place and within ±25 mm never gets below 225 mm² overlap (CM4, C117, C66); L2 overlaps 191 mm² in place (C117,
   C64, Q5, CM4); H4 / H7 mounting holes fall inside the courtyards; the toroid lead pads short R19 / R51 on the
   bottom. → Re-place the PFC input block (L1, L2, C117, CM4, C64 / C66, Q5 / Q6 surroundings) or mount the
   toroids vertically / use the `_TieSlots` variant elsewhere; this is the largest mechanical change on the
   primary side.
7. **Heater barrier ISO1 / TR2 – top left.** 36 HEATER-PRI markers (28 at (−37, −63)): heater-side tracks / vias /
   WP4 within 8 mm of primary vias and pours at ISO1 and TR2. ISO1's slot footprint fits in place. → Local re-route
   and pour pull-back along an 8 mm barrier between TR2 / ISO1; DRV3 (now SOIC-16W, collides with C18 / C25 / C53 /
   D11 / R99) and DRV4 (SOIC-8, collides with Q1 / C17 / R63) need their bootstrap / decoupling parts re-placed.
8. **Added parts (58)**: U9 (bias buffer), U10 (AUX op-amp), U11 (UART isolator), U12, R125–R154, C118–C140, D35 –
   most of the 287 unrouted connections; the C47 / C54 / C16 / C55 balancing resistors R143–R150 go with TR3.

**For reinforced isolation (beyond moving parts):**
- Slots: ISO1 / ISO2 / U11 and TR1 already carry theirs in the footprint; add one between Q19 and Q21 on the TO
  row (or regroup the row), consider one at the Y caps / RL1 (PE-PRI basic) – no other slot is needed if the
  barrier is drawn along the five spots above.
- Pulled-back pours: the zone filler already applies the 4.0 / 8.0 / 11.1 mm domain clearances on every layer
  (the PRI GND pours lose up to 44 % at the barriers); creepage is not applied by the filler, so the outer-layer
  pour edges at J4, ISO1 / TR2 and TR1 / C102 must be drawn back by hand (≥ 11.1 / 8.0 mm along the surface).
- Re-routed tracks: no track crosses a barrier (nets never change domain); the work is moving primary vias / tracks
  out of the 8 mm (UART, heater) and 11.1 mm (secondary) inner-layer bands – In1 / In4 have no creepage credit –
  mainly around J4 / ISO2, the TO row and TR1.
- Layer-to-layer: the L1–L2 / L5–L6 prepregs (0.0994 mm) are not reinforced solid insulation. The refilled
  pours never overlap across layers between domains; tracks were not checked – do this in the 6-layer rework
  (barrier keep-out on all six layers, README D6).

**Scope.** Roughly 60–65 % of the board area (left and centre: PFC except the chokes, measurements, MCU connector,
heater power stage, secondary output edge) can be kept as routed. About a third needs re-placement and re-routing:
the top-right DAB transformer / gate-drive block, the right-centre barrier strip (TO row, ISO2, J4 + U11, TR1 /
PWM2), the L1 / L2 choke area and the ISO1 / TR2 spot – about 60–80 parts moved plus the 58 added, and on the order
of 700–900 track segments re-drawn (the 644 deleted plus the barrier spots). The 5.1 layout is a usable starting point,
not a drop-in: the L1 / L2 toroids and the TR3 / gate-driver stack-up are the decisions to make first, because
they set where the rest of the barrier can run. Then In2 / In3 (empty here) take the re-routed signals and the
power pours.
"""

# ------------------------------------------------------------------------------------------- placement step 1
FIRST_TRIAL = "d3f1063"   # commit of the first trial (flat L1 / L2 toroids, nothing moved)
P1_ZOOM = {"tr3_dab": ["TR3", "C16", "C55", "C47", "C54", "Q7", "Q8", "DRV5"],
           "l1_l2_pfc": ["L1", "L2"]}


def summary(drc, g, dom):
    """counts for the delta table: violation types, cross-domain isolation by pair (on the board), unconnected,
    courtyard pairs"""
    ex = [p for seg in g["edge"] for p in seg]
    bx0, bx1 = min(p[0] for p in ex), max(p[0] for p in ex)
    by0, by1 = min(p[1] for p in ex), max(p[1] for p in ex)
    pairs = collections.Counter()
    for v in drc["violations"]:
        if v["type"] not in ISO_TYPES:
            continue
        its = v["items"]
        if not its:
            continue
        doms = {dom.get(item_net(i), "") for i in its} - {""}
        x = sum(i["pos"]["x"] for i in its) / len(its)
        y = sum(i["pos"]["y"] for i in its) / len(its)
        if len(doms) > 1 and bx0 <= x <= bx1 and by0 <= y <= by1:
            pairs["-".join(sorted(doms))] += 1
    cy = sorted(sorted(item_ref(i) for i in v["items"]) for v in drc["violations"] if v["type"] == "courtyards_overlap")
    return dict(types=dict(collections.Counter(v["type"] for v in drc["violations"])), iso=dict(pairs),
                unconnected=len(drc["unconnected_items"]), courtyard_pairs=cy)


def first_trial_summary(dom):
    """summary of the first trial (git FIRST_TRIAL), cached in first_trial_summary.json"""
    path = os.path.join(D, "first_trial_summary.json")
    if os.path.exists(path):
        return load("first_trial_summary.json")
    import subprocess
    show = lambda f: json.loads(subprocess.run(["git", "-C", ROOT, "show", f"{FIRST_TRIAL}:kicad_next/trial_from_51/{f}"],  # noqa: E731
                                               check=True, capture_output=True, text=True).stdout)
    s = summary(show("drc.json"), show("build.json")["geometry"], dom)
    s["commit"] = FIRST_TRIAL
    with open(path, "w") as f:
        json.dump(s, f, indent=1)
    return s


def iso_points(drc, dom):
    out = []
    for v in drc["violations"]:
        if v["type"] not in ISO_TYPES:
            continue
        its = v["items"]
        if not its:
            continue
        doms = [dom.get(item_net(i), "") for i in its]
        ds = {d for d in doms if d}
        out.append(dict(type=v["type"], x=sum(i["pos"]["x"] for i in its) / len(its),
                        y=sum(i["pos"]["y"] for i in its) / len(its), cross=len(ds) > 1, pair="-".join(sorted(ds))))
    return out


def area_violations(drc, box):
    c = collections.Counter()
    for v in drc["violations"]:
        its = v["items"]
        if not its:
            continue
        x = sum(i["pos"]["x"] for i in its) / len(its)
        y = sum(i["pos"]["y"] for i in its) / len(its)
        if box[0] <= x <= box[2] and box[1] <= y <= box[3]:
            c[v["type"]] += 1
    nu = 0
    for u in drc["unconnected_items"]:
        if any(box[0] <= i["pos"]["x"] <= box[2] and box[1] <= i["pos"]["y"] <= box[3] for i in u["items"]):
            nu += 1
    return c, nu


def refs_box(g, refs, margin=3.0):
    pts = [p for r in refs if r in g["fps"] for c in g["fps"][r]["court"] for p in c]
    return (min(p[0] for p in pts) - margin, min(p[1] for p in pts) - margin,
            max(p[0] for p in pts) + margin, max(p[1] for p in pts) + margin)


def under_pins(g, ref):
    """parts on the other side whose courtyard contains a THT pad of ref (pad + 0.5 mm)"""
    from shapely.geometry import Polygon as SPoly, box
    from shapely.ops import unary_union
    me = g["fps"][ref]
    pads = [box(x - w / 2 - 0.5, y - h / 2 - 0.5, x + w / 2 + 0.5, y + h / 2 + 0.5) for x, y, w, h, _ in me["pads"]]
    out = []
    for r, f in g["fps"].items():
        if r == ref or f["side"] == me["side"] or not f["court"]:
            continue
        P = unary_union([SPoly(c).buffer(0) for c in f["court"] if len(c) > 2])
        if any(P.intersects(q) for q in pads):
            out.append(r)
    return sorted(out)


def write_p1(build0, drc0, base):
    dom, _ = net_domains()
    p1, drc1 = load("placement_p1.json"), load("drc_p1.json")
    g0, g1 = build0["geometry"], p1["geometry"]
    s_first = first_trial_summary(dom)
    s0, s1 = summary(drc0, g0, dom), summary(drc1, g1, dom)
    moved = sorted(set(p1["place"]) | {r for v in p1["groups"].values() for r in v["refs"]})

    # drawings
    pcol = {"PRI-SEC": "#ff0000", "HEATER-PRI": "#00a000", "PRI-UART": "#0050ff", "SEC-UART": "#8000ff",
            "HEATER-SEC": "#ff8000", "PE-PRI": "#00b0b0", "PE-SEC": "#00b0b0"}
    iso1 = iso_points(drc1, dom)
    cy_new1 = {frozenset(p) for p in s1["courtyard_pairs"]} - {frozenset(p) for p in s0["courtyard_pairs"]}
    for f in os.listdir(D):
        if f.startswith("zoom_p1_") and f.endswith(".png"):
            os.remove(os.path.join(D, f))
    for name, refs in P1_ZOOM.items():
        bx = refs_box(g1, refs, 8.0)
        fig, ax = base_axes(g1, f"step 1 {name}: copper by domain, courtyards (magenta = moved / L1 / L2, dashed = "
                                "bottom), isolation violations (x clearance / o creepage), blue squares = courtyard "
                                "overlaps new vs step 0",
                            figsize=(12, 12 * (bx[3] - bx[1]) / (bx[2] - bx[0]) + 0.6), box=bx)
        draw_copper(ax, g1, dom, alpha=0.5)
        hl = set(moved) | {"L1", "L2"}
        draw_fps(ax, g1, dom, highlight=hl,
                 label_set={r for r, fp in g1["fps"].items() if bx[0] < fp["x"] < bx[2] and bx[1] < fp["y"] < bx[3]}, fs=6)
        for i in iso1:
            if i["cross"] and bx[0] < i["x"] < bx[2] and bx[1] < i["y"] < bx[3]:
                ax.plot(i["x"], i["y"], marker="x" if i["type"] != "creepage" else "o", ms=7, mfc="none",
                        color=pcol.get(i["pair"], "#000"), mew=1.2)
        for v in drc1["violations"]:
            if v["type"] == "courtyards_overlap" and frozenset(item_ref(i) for i in v["items"]) in cy_new1:
                a, b = v["items"][0]["pos"], v["items"][1]["pos"]
                ax.plot([(a["x"] + b["x"]) / 2], [(a["y"] + b["y"]) / 2], "s", ms=8, mfc="none", color="#0050ff")
        if name == "tr3_dab":   # TR3 barrier band and pin rows
            t = g1["fps"]["TR3"]
            ax.axvspan(t["x"] - 7.0, t["x"] + 5.0, ymin=0, ymax=1, color="#00a0a0", alpha=0.08)
        fig.tight_layout()
        fig.savefig(os.path.join(D, f"zoom_p1_{name}.png"), dpi=120)
        plt.close(fig)

    L = []
    w = L.append
    w("")
    w("## After placement step 1")
    w("")
    w("User decisions of 2026-11-19, applied reproducibly: **A** (L1 / L2) in the footprint and in step 0 "
      "(`reuse_51_board.py`, `NEW_ORIENTATION`), **B** (TR3, split caps, gate-drive clusters) by "
      "`tools/p2k/bin/kipy tools/next/trial_placement.py` (moves as data in `PLACE` / `GROUPS`) on the step-0 board → "
      "`tube_psu_5_2_trial_p1.kicad_pcb`, DRC `drc_p1.json` (same split passes: "
      + ", ".join(f"{k} {v}" for k, v in drc1.get("passes", {}).items()) + "), `placement_p1.json`.")
    w("")
    w("**A. L1 / L2 – upright toroids on the RM8 holes.** Footprints `tube_psu_next:L_Toroid_D31.5mm_W16.7mm_Vertical_RM8_45deg` "
      "(L1) / `…_315deg` (L2) (`gen_next_footprints.py` `TOROID_V`): pads 1 / 2 = the 5.1 RM8 winding holes pri1 / pri2, origin = "
      "the 5.1 RM8 origin, placed at 0° on the RM8 position, so the step-0 board keeps the 5.1 tracks on both leads "
      f"(kept pads: {', '.join(f'{r} {n}→{q}' for r, n, q in build0.get('kept_pads', [])) or 'none'}). Body 31.5 × 16.7 mm "
      "standing on edge, ring plane along x (photo), centre (−12, ±8) mm from the pad midpoint (outer side of the pad pair, "
      "+x end at the heatsink / H7), courtyard body + 1 mm.")
    w("")
    rows = []
    for r in ("L1", "L2"):
        f = g1["fps"][r]
        xs = [p[0] for c in f["court"] for p in c]
        ys = [p[1] for c in f["court"] for p in c]
        ov = court_overlaps(g1["fps"], [r])[r]
        rows.append([r, f"{f['x']}, {f['y']}", f"x {min(xs):.1f} … {max(xs):.1f}, y {min(ys):.1f} … {max(ys):.1f}",
                     ", ".join(f"{p[0]} ({p[4]})" for p in [(round(q[0], 2), q[1], q[2], q[3], q[4]) for q in f["pads"]]),
                     ", ".join(f"{o} {a}" for o, sd, a in ov if sd == f["side"]) or "–",
                     ", ".join(o for o, sd, a in ov if sd != f["side"]) or "–"])
    w(table(rows, ["ref", "origin (mm)", "courtyard", "pads x (net)", "same-side overlap (mm²)", "other side under it"]))
    w("")
    w("**B. Moves** (absolute place of single parts; rigid shift of the bottom-side gate-drive groups – their own "
      "tracks / vias move with them):")
    w("")
    rows = [[r, d["side"], f"{d['old'][0]}, {d['old'][1]} / {d['old'][2]:g}°", f"{d['new'][0]}, {d['new'][1]} / {d['new'][2]:g}°"]
            for r, d in sorted(p1["place"].items())]
    for gname, d in p1["groups"].items():
        rows.append([gname + ": " + ", ".join(d["refs"]), "B", "–", f"shift {d['dx']:+g}, {d['dy']:+g} mm "
                     f"({d['tracks_moved']} copper items moved along)"])
    w(table(rows, ["part / group", "side", "step 0 (x, y / rot)", "step 1"]))
    w("")
    dl = p1["deleted"]
    w(f"Copper deleted by step 1: {sum(dl.values())} items ({', '.join(f'{k} {v}' for k, v in sorted(dl.items()))}); "
      f"by part: {', '.join(f'{k} {v}' for k, v in p1['deleted_by_ref'].items())}.")
    w("")
    w("### DRC delta")
    w("")
    keys = sorted(set(s_first["types"]) | set(s0["types"]) | set(s1["types"]),
                  key=lambda k: -max(s_first["types"].get(k, 0), s1["types"].get(k, 0)))
    rows = []
    for k in keys:
        a, b, c = s_first["types"].get(k, 0), s0["types"].get(k, 0), s1["types"].get(k, 0)
        rows.append([k, a, b, c, f"{c - a:+d}"])
    a, b, c = (sum(x["iso"].values()) for x in (s_first, s0, s1))
    rows.append(["**isolation, between two domains (on the board)**", a, b, c, f"{c - a:+d}"])
    for pr in sorted(set(s_first["iso"]) | set(s1["iso"])):
        a, b, c = s_first["iso"].get(pr, 0), s0["iso"].get(pr, 0), s1["iso"].get(pr, 0)
        rows.append([f"  {pr}", a, b, c, f"{c - a:+d}"])
    a, b, c = s_first["unconnected"], s0["unconnected"], s1["unconnected"]
    rows.append(["**unconnected items**", a, b, c, f"{c - a:+d}"])
    w(table(rows, [f"type", f"first trial ({s_first.get('commit', '')}, flat L1 / L2)", "step 0 (upright L1 / L2)",
                   "step 1 (+ TR3 / caps / DRV moves)", "step 1 − first"]))
    w("")
    cyf = {frozenset(p) for p in s_first["courtyard_pairs"]}
    cy1 = {frozenset(p) for p in s1["courtyard_pairs"]}
    gone = sorted("/".join(sorted(p)) for p in cyf - cy1)
    new = sorted("/".join(sorted(p)) for p in cy1 - cyf)
    w(f"Courtyard-overlap pairs: first trial {len(cyf)}, step 1 {len(cy1)}; resolved ({len(gone)}): {', '.join(gone) or '–'}; "
      f"new ({len(new)}): {', '.join(new) or '–'}.")
    w("")
    w("### What remains around TR3 and L1 / L2")
    w("")
    rows = []
    for name, refs in (("TR3 + split caps + DRV5 / DRV6", ["TR3", "C16", "C55", "C47", "C54", "DRV5", "DRV6"]),
                       ("L1", ["L1"]), ("L2", ["L2"])):
        bx = refs_box(g1, refs, 3.0)
        c1, n1 = area_violations(drc1, bx)
        cf, nf = area_violations(drc0, bx)
        rows.append([name, f"x {bx[0]:.0f} … {bx[2]:.0f}, y {bx[1]:.0f} … {bx[3]:.0f}",
                     ", ".join(f"{k} {n}" for k, n in cf.most_common()) + f"; unconnected {nf}",
                     ", ".join(f"{k} {n}" for k, n in c1.most_common()) + f"; unconnected {n1}"])
    w(table(rows, ["area", "box (mm)", "step 0", "step 1"]))
    w("")
    order = ["TR3"] + sorted(set(p1["place"]) - {"TR3"})
    ov = court_overlaps(g1["fps"], order)
    rows = []
    for r in order:
        side = g1["fps"][r]["side"]
        rows.append([r, side, ", ".join(f"{o} {a}" for o, sd, a in ov[r] if sd == side) or "–",
                     (", ".join(under_pins(g1, r)) or "none") if r == "TR3" else "– (SMD)"])
    for gname, d in p1["groups"].items():
        ovg = court_overlaps(g1["fps"], d["refs"])
        inner = sorted({f"{r}/{o}" if r < o else f"{o}/{r}" for r in d["refs"] for o, sd, a in ovg[r]
                        if sd == "B" and o in d["refs"]})
        outer = sorted({f"{r}/{o} {a}" for r in d["refs"] for o, sd, a in ovg[r] if sd == "B" and o not in d["refs"]})
        rows.append([gname, "B", "inside the group (5.1 SOIC-16 → 5.2 SOIC-16W): " + (", ".join(inner) or "–")
                     + "; with others: " + (", ".join(outer) or "–"), "–"])
    w(table(rows, ["part", "side", "same-side courtyard overlap (mm²)", "bottom-side parts under its THT pins"]))
    w("")
    w("![tr3 step 1](zoom_p1_tr3_dab.png)")
    w("")
    w("![l1 l2 step 1](zoom_p1_l1_l2_pfc.png)")
    w("")
    w(P1_NOTES)
    with open(os.path.join(D, "REPORT.md"), "a") as f:
        f.write("\n".join(L) + "\n")
    print("trial_report: appended 'After placement step 1'")


P1_NOTES = """### Notes on step 1

Written after reviewing the step-1 numbers (2026-11-19); the tables above are regenerated, this text is not.

**L1 / L2 orientation (photo).** In the photo of the built 5.1 board the board's long axis runs top–bottom, mains
input at the top (= KiCad left edge, IN1 / IN2 / PE), the heatsink plate lower left (= KiCad TO row at y ≈ −42).
Mapping: photo down = KiCad +x, photo left = KiCad +y (bottom edge). The two taped toroids stand on edge with their
ring planes along the photo's vertical, i.e. **along KiCad x** (the board's long axis); the left one (= L1, at the
KiCad bottom edge y = 18.75) and the right one (= L2) flank the two common-mode chokes (CM1 / CM4, KiCad y −8 … −34),
their lower (+x) ends stop just short of the heatsink / H7 standoff, right where the RM8 pri1 / pri2 holes are –
the leads come down from the lower +x side of each ring. Hence: body centre 12 mm towards −x and 8 mm outwards (L1
+y, L2 −y) from the pad pair; this is also the only place near the RM8s where an upright 31.5 × 16.7 body is free
(the fit scan over the offsets gives ≤ 5 mm² overlap only here; at the pad midpoint it would hit Q5 / Q6, C117,
CM4, H4 / H7). L1's courtyard ends 1.0 mm inside the bottom edge – the photo shows the toroid flush with the edge;
its top only appears to overhang by perspective, so no overhang is drawn. The body position is a photo estimate
(±3 mm): measure it on the built board. Step 0 already resolves all L1 / L2 collisions of the first trial except
small courtyard touches (SICD2 4.8, C117 1.3 / 1.5, H7 0.4 mm²), keeps the 5.1 tracks on all four leads, and the
L1 / L2 area has no new DRC items (the remaining ones there are the 5.1 PE-PRI / clearance items of the PFC block).

**TR3 / split caps / gate drive (B).** TR3 at (49.5, −69.3), 0°, winding axis along x (plan phase 5.6): pin rows
x 29.5 (primary) / 69.5 (secondary), courtyard 0.55 mm inside the top edge; its 12 mm barrier band x 42.5 … 54.5
continues the primary / secondary line of the TO row (Q19 gate pad x 48.2 | Q21 source pad x 54.7), so one straight
barrier runs from the top edge through TR3 down to the heatsink. Why not further right / at the 5.1 origin: the
secondary split caps then have no F.Cu room next to pins 9 / 10 (C19 / the output terminals take x ≥ 79), and the
EC42 numbering puts the secondary cap pins 9 / 10 at the TO-row end, so C16 / C55 belong at x ≈ 76, y −59 … −47
(TRANS_SEC pads 6 mm from the pins, ISO_GND end towards Q8, 420V end towards C19). C47 / C54 sit in the old L3
area next to primary pins 1 / 2 (DHB_CAP pads facing each other 2.6 mm apart); their DC+ / DHB_CURRENT ends need
a run to the TO row (C67 / C70 stay there as the HF decoupling of the primary half-bridge). C89 moved above C90.
DRV5 + 6 parts moved 4.5 mm left (out of the primary pin row, still left of Q7); DRV6 + 7 parts moved under the
TR3 body between the band and the secondary row (the only free bottom-side room on the secondary side). No
bottom-side part is under a TR3 pin; TR3, the split caps and C89 have no courtyard overlap left; the TR3-area
shorts / mask bridges dropped from 12 / 12 to 5 / 4 (the rest are the DRV5 / DRV6 groups' own 5.1-SOIC-16 →
SOIC-16W overlaps: C92 / C94 / C95 at DRV5, C46 / C93 at DRV6 – their bootstrap / decoupling parts must be
re-placed around the wider package) and the TR3-area clearances from 38 to 23.

**What remains around TR3:** (1) the TO-row barrier (rework item 2): the Q19 gate track and the Q21 / Q8 copper
are within 11.1 mm across x ≈ 51 (creepage marker Q19 gate ↔ DRV6 pad 9 now that DRV6 sits right of the band) –
needs the Q19 / Q21 slot or more spacing in the row, unchanged by this step; (2) a 5.1 DHB_HI_SOURCE_SEC F.Cu
track and the primary DHB_HI_SOURCE F.Cu pour near the band, a primary +3V3 via inside the 420V pour at x ≈ 71
(5.1 leftovers to delete when routing); (3) 59 unconnected items in the TR3 box (both half-bridge loops, the
split caps, the moved gate-drive groups' outside connections – 58 copper items were deleted by the moves,
63 moved along with the groups); (4) the gate-drive groups are now further from the TO row (DRV6 ≈ 10 mm above
Q21 / Q8, under the transformer – check the EC42 stray field at the driver, or move DRV6 + its parts into the
row once the TO row is regrouped); (5) the 5.1 F.Cu pours around the old C16 / C55 / TR3 area still follow the
old shapes and must be redrawn for the new pins.
"""

# ------------------------------------------------------------------------------------------- placement step 2
P2_AREAS = {   # name: (title, refs that span the zoom box, margin)
    "uart_island": ("UART island J4 / U11 / U12 (top edge)", ["U11", "J4", "C47", "U12", "C137", "H2"], 9.0),
    "to_row_slot": ("TO row Q19 / Q21 slot", ["Q7", "Q19", "Q21", "Q8", "ISO2"], 4.0),
    "iso2_tr1": ("ISO2, D4 / D5, TR1, PWM2, C102", ["ISO2", "TR1", "PWM2", "C102", "D4", "R8", "R72"], 3.0),
    "drv5_drv6": ("DRV5 / DRV6 gate drive (bottom)", ["DRV5", "DRV6", "C95", "C92", "C46", "C93", "C94"], 4.0),
    "drv3_drv4": ("DRV3 / DRV4 (heater)", ["DRV3", "DRV4", "C18", "C25", "D11", "R99", "C53", "R63", "C17", "Q1"], 4.0),
}
P2_COL = {"PRI-SEC": "#ff0000", "HEATER-PRI": "#00a000", "PRI-UART": "#0050ff", "SEC-UART": "#8000ff",
          "HEATER-SEC": "#ff8000", "PE-PRI": "#00b0b0", "PE-SEC": "#00b0b0"}


def area_iso(drc, box, dom):
    c = collections.Counter()
    for i in iso_points(drc, dom):
        if i["cross"] and box[0] <= i["x"] <= box[2] and box[1] <= i["y"] <= box[3]:
            c[i["pair"]] += 1
    return c


def cy_pairs_in(drc, refs):
    out = set()
    for v in drc["violations"]:
        if v["type"] == "courtyards_overlap":
            p = frozenset(item_ref(i) for i in v["items"])
            if p & set(refs):
                out.add(p)
    return out


def shorts_of(drc, refs):
    out = set()
    for v in drc["violations"]:
        if v["type"] in ("shorting_items", "solder_mask_bridge"):
            rr = [item_ref(i) for i in v["items"]]
            if set(rr) & set(refs):
                out.add((v["type"], "/".join(sorted(r or "?" for r in rr))))
    return out


def write_p2():
    dom, _ = net_domains()
    p1, drc1 = load("placement_p1.json"), load("drc_p1.json")
    p2, drc2 = load("placement_p2.json"), load("drc_p2.json")
    g1, g2 = p1["geometry"], p2["geometry"]
    s1, s2 = summary(drc1, g1, dom), summary(drc2, g2, dom)
    moved = sorted(set(p2["place"]) | {r for v in p2["groups"].values() for r in v["refs"]})
    iso2 = iso_points(drc2, dom)
    cy_new = {frozenset(p) for p in s2["courtyard_pairs"]} - {frozenset(p) for p in s1["courtyard_pairs"]}
    for f in os.listdir(D):
        if f.startswith("zoom_p2_") and f.endswith(".png"):
            os.remove(os.path.join(D, f))
    boxes = {}
    for name, (title, refs, margin) in P2_AREAS.items():
        bx = refs_box(g2, refs, margin)
        boxes[name] = bx
        fig, ax = base_axes(g2, f"step 2 – {title}",
                            figsize=(12, 12 * (bx[3] - bx[1]) / (bx[2] - bx[0]) + 0.6), box=bx)
        draw_copper(ax, g2, dom, alpha=0.5)
        draw_fps(ax, g2, dom, highlight=set(moved),
                 label_set={r for r, fp in g2["fps"].items() if bx[0] < fp["x"] < bx[2] and bx[1] < fp["y"] < bx[3]}, fs=6)
        for d in p2["deleted_items"]:
            for x, y in d["pts"]:
                if bx[0] < x < bx[2] and bx[1] < y < bx[3]:
                    ax.plot(x, y, "+", ms=4, color="#606060", mew=0.6)
        for sl in p2["slots"].values():
            ax.add_patch(Polygon(sl["poly"], closed=True, fc="#000000", ec="#000000"))
        for k in p2["keepouts"].values():
            ax.add_patch(plt.Rectangle((k["x0"], k["y0"]), k["x1"] - k["x0"], k["y1"] - k["y0"], fill=False, ec="#00a0c0",
                                       ls="--", lw=1.2))
        for i in iso2:
            if i["cross"] and bx[0] < i["x"] < bx[2] and bx[1] < i["y"] < bx[3]:
                ax.plot(i["x"], i["y"], marker="x" if i["type"] != "creepage" else "o", ms=7, mfc="none",
                        color=P2_COL.get(i["pair"], "#000"), mew=1.2)
        for v in drc2["violations"]:
            if v["type"] == "courtyards_overlap" and frozenset(item_ref(i) for i in v["items"]) in cy_new:
                a, b = v["items"][0]["pos"], v["items"][1]["pos"]
                ax.plot([(a["x"] + b["x"]) / 2], [(a["y"] + b["y"]) / 2], "s", ms=8, mfc="none", color="#0050ff")
        if "TR3" in g2["fps"]:   # TR3 barrier band (x -7 ... +5 about the core centre, over the TR3 courtyard)
            t = g2["fps"]["TR3"]
            ax.add_patch(plt.Rectangle((t["x"] - 7.0, t["y"] - 21.5), 12.0, 43.0, fc="#00a0a0", ec="none", alpha=0.08))
        fig.tight_layout()
        fig.savefig(os.path.join(D, f"zoom_p2_{name}.png"), dpi=120)
        plt.close(fig)

    L = []
    w = L.append
    w("")
    w("## After placement step 2")
    w("")
    w("Applied by `tools/p2k/bin/kipy tools/next/trial_placement_p2.py` (moves as data: `PLACE`, `AUTO` = two-pad parts "
      "placed by centre / axis with the orientation that puts each pad next to its pin, `GROUPS`, `SLOTS`, the UART "
      "pour keep-out) on the step-1 board → `tube_psu_5_2_trial_p2.kicad_pcb`, DRC `drc_p2.json` (same split passes: "
      + ", ".join(f"{k} {v}" for k, v in drc2.get("passes", {}).items()) + "), `placement_p2.json` (moves, slot, "
      "keep-out and every deleted track / via with net, layer and end points, so the routing can redo it). Nothing "
      "is routed.")
    w("")
    w("**Moves**")
    w("")
    rows = [[r, d["side"], f"{d['old'][0]}, {d['old'][1]} / {d['old'][2]:g}°", f"{d['new'][0]}, {d['new'][1]} / {d['new'][2]:g}°"]
            for r, d in sorted(p2["place"].items())]
    for gname, d in p2["groups"].items():
        rows.append([gname + ": " + ", ".join(d["refs"]), "–", "–", f"shift {d['dx']:+g}, {d['dy']:+g} mm "
                     f"({d['tracks_moved']} copper items moved along)"])
    w(table(rows, ["part / group", "side", "step 1 (x, y / rot)", "step 2"]))
    w("")
    for name, sl in p2["slots"].items():
        w(f"**Slot** {name}: Edge.Cuts polygon {', '.join(f'({x:.2f}, {y:.2f})' for x, y in sl['poly'])} "
          f"({sl['width']} mm wide; legs " + ", ".join(f"x {r[0]:.2f} … {r[2]:.2f} / y {r[1]:.2f} … {r[3]:.2f}" for r in sl["rects"]) + ").")
    for name, k in p2["keepouts"].items():
        w(f"**Keep-out** {name}: rule area x {k['x0']:.1f} … {k['x1']:.1f}, y {k['y0']:.1f} … {k['y1']:.1f}, {k['layers']}, "
          f"{k['what']}.")
    w(f"**Pads without unused inner-layer rings:** {', '.join(p2['pads_inner_removed'])} (KiCad 'remove unconnected "
      "layers, keep start / end').")
    w("")
    dl = p2["deleted"]
    w(f"**Copper deleted by step 2:** {sum(dl.values())} items ({', '.join(f'{k} {v}' for k, v in sorted(dl.items()))}); "
      f"by part: {', '.join(f'{k} {v}' for k, v in p2['deleted_by_ref'].items())}. Nets of the deleted copper (to re-route): "
      + ", ".join(f"{n} {c}" for n, c in collections.Counter(d["net"] for d in p2["deleted_items"]).most_common(25)) + ".")
    w("")
    w("### DRC delta step 1 → step 2")
    w("")
    keys = sorted(set(s1["types"]) | set(s2["types"]), key=lambda k: -max(s1["types"].get(k, 0), s2["types"].get(k, 0)))
    rows = [[k, s1["types"].get(k, 0), s2["types"].get(k, 0), f"{s2['types'].get(k, 0) - s1['types'].get(k, 0):+d}"] for k in keys]
    a, b = sum(s1["iso"].values()), sum(s2["iso"].values())
    rows.append(["**isolation, between two domains (on the board)**", a, b, f"{b - a:+d}"])
    for pr in sorted(set(s1["iso"]) | set(s2["iso"])):
        a, b = s1["iso"].get(pr, 0), s2["iso"].get(pr, 0)
        rows.append([f"  {pr}", a, b, f"{b - a:+d}"])
    a, b = s1["unconnected"], s2["unconnected"]
    rows.append(["**unconnected items**", a, b, f"{b - a:+d}"])
    w(table(rows, ["type", "step 1", "step 2", "delta"]))
    w("")
    c1 = {frozenset(p) for p in s1["courtyard_pairs"]}
    c2 = {frozenset(p) for p in s2["courtyard_pairs"]}
    gone = sorted("/".join(sorted(p)) for p in c1 - c2)
    new = sorted("/".join(sorted(p)) for p in c2 - c1)
    w(f"Courtyard-overlap pairs: step 1 {len(c1)}, step 2 {len(c2)}; resolved ({len(gone)}): {', '.join(gone) or '–'}; "
      f"new ({len(new)}): {', '.join(new) or '–'}.")
    w("")
    w("### Per area (step 1 → step 2)")
    w("")
    rows = []
    for name, (title, refs, margin) in P2_AREAS.items():
        bx = boxes[name]
        i1, i2 = area_iso(drc1, bx, dom), area_iso(drc2, bx, dom)
        v1, n1 = area_violations(drc1, bx)
        v2, n2 = area_violations(drc2, bx)
        prs = sorted(set(i1) | set(i2))
        area_refs = [r for r, fp in g2["fps"].items() if bx[0] < fp["x"] < bx[2] and bx[1] < fp["y"] < bx[3]]
        cyA, cyB = cy_pairs_in(drc1, area_refs), cy_pairs_in(drc2, area_refs)
        shA, shB = shorts_of(drc1, area_refs), shorts_of(drc2, area_refs)
        rows.append([title, f"x {bx[0]:.0f} … {bx[2]:.0f}, y {bx[1]:.0f} … {bx[3]:.0f}",
                     ", ".join(f"{p} {i1.get(p, 0)} → {i2.get(p, 0)}" for p in prs) or "–",
                     f"{len(cyA)} → {len(cyB)}", f"{sum(1 for t, _ in shA if t == 'shorting_items')} → "
                     f"{sum(1 for t, _ in shB if t == 'shorting_items')}",
                     f"{v1.get('clearance', 0)} → {v2.get('clearance', 0)}", f"{v1.get('creepage', 0)} → {v2.get('creepage', 0)}",
                     f"{n1} → {n2}"])
    w(table(rows, ["area", "box (mm)", "isolation violations by domain pair", "courtyard pairs", "shorts",
                   "clearance (all)", "creepage (all)", "unconnected"]))
    w("")
    w("Zooms: copper by domain (red primary, orange secondary, green heater, blue UART), courtyards (magenta = moved by "
      "step 2, dashed = bottom side), cross-domain isolation violations (x clearance / o creepage, coloured by pair), blue "
      "squares = courtyard overlaps new vs step 1, black = new slot, cyan dashed = pour keep-outs, grey + = end points of "
      "deleted copper, light band = TR3 barrier band.")
    w("")
    for name, (title, _, _) in P2_AREAS.items():
        w(f"![{title}](zoom_p2_{name}.png)")
        w("")
    w(P2_NOTES)
    with open(os.path.join(D, "REPORT.md"), "a") as f:
        f.write("\n".join(L) + "\n")
    print("trial_report: appended 'After placement step 2'")


P2_NOTES = """### Notes on step 2

Written after reviewing the step-2 numbers (2026-11-19); the tables above are regenerated, this text is not.

**1. UART island – top edge, x −6 … 14, next to H2.** Candidates checked: (a) the old J4 place (x 49 … 61, y −30)
is not at an edge – it lies inside the heatsink L next to the control card on J2, the 5.1 cable ran over the board;
(b) the bottom edge next to J2's end (x 25 … 40), closest to the UART signals (TX / RX = J2 pins 26 / 24 at
x 34.4, y −7 / −8): C29 (DC+ electrolytic) and the DC+ start-up chain R114 … R116 are 16 mm apart, so after 8 mm
on each side nothing is left, and the AC-measurement amplifier U8 group sits there; (c) the bottom edge left of L1:
mains input filter; (d) the right edge: secondary outputs (8.4 mm SEC-UART, and U11's primary side cannot reach
primary copper there); (e) the top-left edge: heater island parts. The old L3 area left of TR3 was freed by step 1;
it is outside the heatsink L (in the photo the board's right edge, open), so the cable reaches the edge, and the
only neighbours are primary: Q10 / C22 / C42 / C49 on the left – faced by U11's primary pins 1–8, with the U11
8 mm slot between – and C47 / C54 on the right (C47 / C54 0.55 mm closer to the TR3 pins, J4 8.1 mm from them).
J4 stands at the top edge (pin 1 ISO_UART_GND at y −89, 2.4 mm from the edge) right of H2, U12 / C135–C137 /
R136 / R137 between U11 and J4 below H2's screw head (Ø 5.5 mm). The bottom-side U1 current-measurement amplifier
(12 parts + C87 on top) moved 8 mm down with its own copper (12 In4 segments of EPWM5A / EPWM6A / +3V3 /
HEATER_CURRENT / DHB_CURRENT it landed on were deleted). Primary copper within 8 mm of an island pad: 6
segments deleted; pour keep-out over the island + 8 mm on all six layers (no solid-insulation overlap either).
Cost: TX / RX run about 80 mm from J2 to U11's primary pins (In2 / In3 routing). PRI-UART 259 → 0.

**2. Q19 / Q21 – L-slot.** The heatsink footprint (`gen_next_footprints.py` `heatsink()`) is only an outline
helper (plate 120 × 3 mm on the tab side, keep-off lines, no pads / holes): the 5.1 board has no bracket holes,
the plate is held by the TO screws, and its hole pattern is the TO-row pitch (Q7 / Q19 / Q21 / Q8 at x 36.9 /
48.2 / 59.8 / 71.4), so the TO parts stay. The tabs face +y; the plate face is at y −38.8. A 1.2 mm milled slot
fits without touching the plate: vertical leg at x 51.4 (between Q19 pin 1 and Q21 pin 3, pad edges 1.8 mm away,
inside the TR3 barrier band x 42.5 … 54.5) from y −62 (under TR3, where the band forbids copper anyway) down to
the pins, then a horizontal leg in front of the plate face under the Q21 / Q8 pins (0.55 mm from their pads) to
x 68.6, past the top of the ISO2 slot (2.85 mm bridge). Outer-layer creepage Q19 ↔ Q21 now goes round the slot
(≥ 16 mm), and the ISO2 primary pins 1 / 2 (+3V3 / EPWM2A, 9.6 mm from the Q21 gate before) see Q21 / Q8 only
round the slot end. Five inner-layer secondary / primary items within 11.1 mm of the Q19 / Q21 barrels were
deleted, the Q19 / Q21 pads lost their unused inner rings. **Remaining (24 of the 26 PRI-SEC items): KiCad
checks the plated barrels themselves on the inner layers** (Q19 pin 1 ↔ Q21 pin 1 10.5 mm, pin 1 ↔ pin 3 5.4 mm
hole edge to hole edge) and the DRU gives no slot credit there. The slot does cut the laminate between the
barrels (the through-laminate path goes round the slot ends like the surface path), so this needs a decision:
(a) a DRU exception for barrels separated by a through-board slot (as for TR1's barrier pads, but with the slot
argued as the barrier), or (b) 5.7 mm more pitch between Q19 and Q21 – a new plate hole pattern, which the fixed
plate does not allow. **User decision 2026-11-19: (a).** `tube_psu_5_2.kicad_dru` rule "PRI-SEC inner layers,
Q19/Q21 across the barrier slot": inner-layer clearance / hole clearance 4.0 mm (reinforced air clearance across
the slot) for Q19 ↔ Q21 pairs only; the laminate path round the slot ends has the same plan geometry as the
outer surface path that the 11.1 mm creepage rule checks (with the larger outer pads), and that check passes.
DRC re-run with the rule: Q19 ↔ Q21 24 → 0 (PRI-SEC 26 → 2, the TR1 pin 2 / 9 barrels). The re-run's
creepage pass also reported 2 old 5.1 B.Cu tracks at mounting holes (H4 ↔ 15V 2.2 mm of 3.2, H5 ↔
CUK_CAP_MEAS- 3.45 mm of 4.2) that the first run had not listed – unrelated to the rule, fixed when routing.

**3. ISO2 / D4 / D5.** ISO2 stays: its slot already sits on the barrier line between TR1's slot and the TO row,
and the L-slot now closes its top end. D4 (secondary 15V_ISO_SEC rectifier) moved out of the ISO2 slot to the
right of ISO2 (x 76.8, y −19.2, cathode next to C2 / P15V_OUT), C2 / C3 0.6 mm right; D5 (primary 15 V) stays
left of the barrier, 1 mm up for 11.1 mm to TR1 pin 10 through the 2.5 mm gap between the ISO2 and TR1 slots.
The 5.1 F.Cu pours that bridged that gap (TR1-A15, TR1-S15, 15V, 15V_ISO_SEC) and the B.Cu GND / ISO_GND pours at
the slot bridge are held off by pour keep-outs; 9 In4 items of the 5.1 ISO2 routing inside an 11.1 mm inner band
on the ISO2 slot line were deleted. Area: PRI-SEC 58 → 2 (the 2 are TR1 pin 2 GND ↔ pin 9 ISO_GND barrels
on the inner layers, already on step 1: the TR1 footprint keeps pin 2's inner ring where a GND pour connects –
keep In1 / In4 GND off pin 2 when routing).

**4. TR1 / PWM2 / flyback.** TR1 stays at its 5.1 origin and is free (no courtyard overlap, no part under its
pins: D6 moved 1.5 mm left off pin 2). PWM2 4.7 mm left (its courtyard ends at TR1's), drain pins 5–8 at the
left end (x 45.4 … 46.6) facing away from the TR1 slot and the FB / VERR pins; CS resistors R8 / R9 above it,
VCC caps C58 / C51 (bottom) right of the drain end, clamp D7 / R72 left of the FLY_C fly lead. Drain copper room
as placed: F.Cu x 41 … 46 between R114–R116 and the drain pins plus a strip along y 8 … 10.5 to D7 / TR1 pin 12,
about 0.8 cm² per outer layer, i.e. **≈ 1.5 cm² F + B – short of the 2–3 cm² of NEXT_REVISION_PLAN phase 5 (8)**:
gain it by moving the start-up chain R114–R116 1–2 mm left or C58 off the drain end on B.Cu when routing. The
secondary parts right of TR1 moved 0.4 / 1.4 mm right, C102 1.85 mm right (pad 1 13.2 mm from the DC+ fly
lead, barrel to barrel ≥ 11.1 mm); 3 secondary segments within 11.1 mm of the fly leads deleted and the pours
at the TR1 slot end held off.

**5. Gate drivers.** All bootstrap / decoupling parts sit outside the SOIC bodies next to their pins (orientation
picked per part so that each pad faces its pin): DRV5 C94 left of pins 3 / 4, C95 below pins 14 / 16, C92 above
pins 9 / 11; DRV6 C46 / R46 above pins 14 / 16 (C46 just right of the TR3 band), C93 below pin 8 (VCCI); DRV3
C25 / R99 / D11 / R78 right of the package (pins 16 / 14 / 1), C18 above pins 9 / 11, C53 below pins 3 / 4;
DRV4 turned 90° between C32 and Q1 (pins 5–8 on top: OUTA towards the Q1 gate, VDD), R63 / C17 above it. The
DRV-area shorts 23 → 0, mask bridges 22 → 0, courtyard pairs with the drivers resolved (no new pair on the board).

**Remaining after step 2** (beyond the routing itself, unconnected 303 → 346, dangling 78 → 110): the Q19 / Q21
barrels (24) are resolved by decision (a) above; TR1 pin 2 / 9 inner barrels (2); HEATER-PRI 36 at ISO1 / TR2 and PE-PRI 22 at the PFC
Y caps / RL1 (not in this step); PWM2 drain area (above); C2 / R123 courtyard touch 0.76 mm² (5.1 pair, was
0.55); 17 silk-to-edge warnings at the new slot / U11 / J4 (reference texts to move); `lib_footprint_mismatch`
Q19 / Q21 (board pads without unused inner rings – put it in a footprint copy if kept).
"""

# ------------------------------------------------------------------------------------------- placement step 3
P3_AREAS = {   # name: (title, refs that span the zoom box, margin)
    "heater_iso1": ("Heater barrier ISO1 / TR2 pad 10 / WP4, relay driver under RL1", ["ISO1", "WP4", "R27", "C97", "Q9", "C35", "C85"], 4.0),
    "pe_ycaps": ("PFC Y caps / RL1 / CM1 (PE)", ["RL1", "C85", "C81", "C82", "C84", "C65", "CM1", "PE"], 3.0),
    "flyback": ("Flyback control parts at PWM2, U10", ["PWM2", "R116", "R126", "R151", "R135", "D7", "C132"], 3.0),
    "heater_split": ("Heater LLC split-cap balancing R155-R158, D35, DRV3 dead time", ["C41", "R158", "D35", "R130", "C121", "Q10"], 3.0),
    "dab_pri": ("DAB primary: balancing R143-R146, DRV5 dead time / DAB_DIS, U1 parts", ["C47", "R146", "DRV5", "C118", "C120", "C122", "C125"], 3.0),
    "dab_sec": ("DAB secondary: balancing R147-R150, DRV6 dead time", ["C16", "C55", "R150", "DRV6", "C119"], 3.0),
    "analog": ("U9 bias buffer, U8 / U6 filter capacitors", ["U9", "R131", "C128", "C126", "C127", "C130", "C131"], 3.0),
}


P3_FIRST = "6d8c3a9"   # first step-3 commit (separate board slot with a 1 x 1 mm web, hole pads not moved)


def p3_first_summary(dom):
    """summary of the first step-3 result (git P3_FIRST), cached in step3_first_summary.json"""
    path = os.path.join(D, "step3_first_summary.json")
    if os.path.exists(path):
        return load("step3_first_summary.json")
    import subprocess
    show = lambda f: json.loads(subprocess.run(["git", "-C", ROOT, "show", f"{P3_FIRST}:kicad_next/trial_from_51/{f}"],  # noqa: E731
                                               check=True, capture_output=True, text=True).stdout)
    drc, pl = show("drc_p3.json"), show("placement_p3.json")
    s = summary(drc, pl["geometry"], dom)
    s["holes"] = hole_count(drc)
    s["deleted"] = sum(pl["deleted"].values())
    s["commit"] = P3_FIRST
    with open(path, "w") as f:
        json.dump(s, f, indent=1)
    return s


def hole_count(drc):
    return sum(1 for v in drc["violations"] if v["type"] in ISO_TYPES and "Mounting hole" in rule_of(v))


def write_p3():
    dom, _ = net_domains()
    p2, drc2 = load("placement_p2.json"), load("drc_p2.json")
    p3, drc3 = load("placement_p3.json"), load("drc_p3.json")
    g2, g3 = p2["geometry"], p3["geometry"]
    s2, s3 = summary(drc2, g2, dom), summary(drc3, g3, dom)
    moved = sorted(set(p3["place"]) | set(p3["new"]) | {r for v in p3["groups"].values() for r in v["refs"]})
    iso3 = iso_points(drc3, dom)
    cy_new = {frozenset(p) for p in s3["courtyard_pairs"]} - {frozenset(p) for p in s2["courtyard_pairs"]}
    for f in os.listdir(D):
        if f.startswith("zoom_p3_") and f.endswith(".png"):
            os.remove(os.path.join(D, f))
    boxes = {}
    for name, (title, refs, margin) in P3_AREAS.items():
        bx = refs_box(g3, refs, margin)
        boxes[name] = bx
        fig, ax = base_axes(g3, f"step 3 – {title}",
                            figsize=(12, 12 * (bx[3] - bx[1]) / (bx[2] - bx[0]) + 0.6), box=bx)
        draw_copper(ax, g3, dom, alpha=0.5)
        draw_fps(ax, g3, dom, highlight=set(moved),
                 label_set={r for r, fp in g3["fps"].items() if bx[0] < fp["x"] < bx[2] and bx[1] < fp["y"] < bx[3]}, fs=6)
        for d in p3["deleted_items"]:
            for x, y in d["pts"]:
                if bx[0] < x < bx[2] and bx[1] < y < bx[3]:
                    ax.plot(x, y, "+", ms=4, color="#606060", mew=0.6)
        for sl in list(p2["slots"].values()) + list(p3["slots"].values()):
            ax.add_patch(Polygon(sl["poly"], closed=True, fc="#000000", ec="#000000"))
        for k in p2["keepouts"].values():
            ax.add_patch(plt.Rectangle((k["x0"], k["y0"]), k["x1"] - k["x0"], k["y1"] - k["y0"], fill=False, ec="#a0c8d0",
                                       ls="--", lw=0.8))
        for k in p3["keepouts"].values():
            ax.add_patch(Polygon(k["pts"], closed=True, fill=False, ec="#00a0c0", ls="--", lw=1.2))
        for i in iso3:
            if i["cross"] and bx[0] < i["x"] < bx[2] and bx[1] < i["y"] < bx[3]:
                ax.plot(i["x"], i["y"], marker="x" if i["type"] != "creepage" else "o", ms=7, mfc="none",
                        color=P2_COL.get(i["pair"], "#000"), mew=1.2)
        for v in drc3["violations"]:
            if v["type"] == "courtyards_overlap" and frozenset(item_ref(i) for i in v["items"]) in cy_new:
                a, b = v["items"][0]["pos"], v["items"][1]["pos"]
                ax.plot([(a["x"] + b["x"]) / 2], [(a["y"] + b["y"]) / 2], "s", ms=8, mfc="none", color="#0050ff")
        fig.tight_layout()
        fig.savefig(os.path.join(D, f"zoom_p3_{name}.png"), dpi=120)
        plt.close(fig)

    L = []
    w = L.append
    w("")
    w("## After placement step 3")
    w("")
    w("Applied by `tools/p2k/bin/kipy tools/next/trial_placement_p3.py` (moves as data: `PLACE` = 5.1 parts moved, `NEW` = "
      "5.2 parts taken from the off-board grid with their side, `GROUPS`, `SLOTS`, `KEEPOUTS`, the deletion rules and "
      "`DELETE`, `TEXTS`) on the step-2 board → `tube_psu_5_2_trial_p3.kicad_pcb`, DRC `drc_p3.json` (same split passes: "
      + ", ".join(f"{k} {v}" for k, v in drc3.get("passes", {}).items()) + "), `placement_p3.json` (moves, slot, "
      "keep-outs and every deleted track / via with net, layer and end points, so the routing can redo it). Nothing "
      "is routed.")
    w("")
    w("**5.1 parts moved**")
    w("")
    rows = [[r, d["side"], f"{d['old'][0]}, {d['old'][1]} / {d['old'][2]:g}°", f"{d['new'][0]}, {d['new'][1]} / {d['new'][2]:g}°"]
            for r, d in sorted(p3["place"].items())]
    for gname, d in p3["groups"].items():
        rows.append([gname + ": " + ", ".join(d["refs"]), "–", "–", f"shift {d['dx']:+g}, {d['dy']:+g} mm "
                     f"({d['tracks_moved']} copper items moved along)"])
    w(table(rows, ["part / group", "side", "step 2 (x, y / rot)", "step 3"]))
    w("")
    w(f"**5.2 parts placed from the off-board grid** ({len(p3['new'])}; still off-board: "
      f"{', '.join(p3['offboard']) or 'none'})")
    w("")
    rows = []
    for r, d in sorted(p3["new"].items(), key=lambda kv: (re.sub(r"\d", "", kv[0]), int(re.sub(r"\D", "", kv[0])))):
        fp = g3["fps"][r]
        nets = ", ".join(f"{n.split('/')[-1]}" for n in dict.fromkeys(pd[4] for pd in fp["pads"]))
        rows.append([r, fp.get("sheet", ""), d["side"], f"{d['new'][0]}, {d['new'][1]} / {d['new'][2]:g}°", nets])
    w(table(rows, ["ref", "sheet", "side", "x, y / rot", "nets"]))
    w("")
    if p3["unplaced"]:
        w("**Not placed** (left in the off-board grid): " + "; ".join(f"{r}: {why}" for r, why in sorted(p3["unplaced"].items())) + ".")
        w("")
    for r, d in sorted(p3.get("footprints", {}).items()):
        w(f"**Footprint swapped** {r}: `{d['old']}` → `{d['new']}` (same pads, tracks kept).")
    for name, sl in p3["slots"].items():
        w(f"**New slot area** {name}: {', '.join(f'({x:.2f}, {y:.2f})' for x, y in sl['poly'])} "
          f"({sl['width']} mm wide).")
    kk = p3["keepouts"]
    for name, k in kk.items():
        if not name.startswith(("mounting hole", "PE pour")):
            w(f"**Keep-out** {name}: rule area x {k['x0']:.1f} … {k['x1']:.1f}, y {k['y0']:.1f} … {k['y1']:.1f}, {k['layers']}, "
              f"{k['what']}.")
    nh = sum(1 for n in kk if n.startswith("mounting hole"))
    npe = sum(1 for n in kk if n.startswith("PE pour"))
    w(f"**Keep-outs round earthed parts** (all copper layers, no copper pour): {nh} circles round the mounting holes "
      f"(radius 5.0 mm primary side H1 / H2 / H4 / H6 / H7, 6.0 mm secondary side H3 / H5 / H8 = ring + creepage), "
      f"{npe} polygon(s) = PE pads and PE tracks + 3.25 mm.")
    w("**Reference texts moved:** " + ", ".join(f"{r} → ({d['new'][0]}, {d['new'][1]})" for r, d in sorted(p3["texts"].items())) + ".")
    w("")
    dl = p3["deleted"]
    w(f"**Copper deleted by step 3:** {sum(dl.values())} items ({', '.join(f'{k} {v}' for k, v in sorted(dl.items()))}); "
      f"by part / reason key: {', '.join(f'{k} {v}' for k, v in p3['deleted_by_ref'].items())}. Nets of the deleted copper "
      "(to re-route): "
      + ", ".join(f"{n} {c}" for n, c in collections.Counter(d["net"] for d in p3["deleted_items"]).most_common(40)) + ".")
    w("")
    w("### DRC delta step 2 → step 3")
    w("")
    keys = sorted(set(s2["types"]) | set(s3["types"]), key=lambda k: -max(s2["types"].get(k, 0), s3["types"].get(k, 0)))
    rows = [[k, s2["types"].get(k, 0), s3["types"].get(k, 0), f"{s3['types'].get(k, 0) - s2['types'].get(k, 0):+d}"] for k in keys]
    a, b = sum(s2["types"].values()), sum(s3["types"].values())
    rows.append(["**all violations**", a, b, f"{b - a:+d}"])
    a, b = sum(s2["iso"].values()), sum(s3["iso"].values())
    rows.append(["**isolation, between two domains (on the board)**", a, b, f"{b - a:+d}"])
    for pr in sorted(set(s2["iso"]) | set(s3["iso"]) | {"HEATER-PRI", "PE-PRI", "PRI-SEC", "PRI-UART"}):
        a, b = s2["iso"].get(pr, 0), s3["iso"].get(pr, 0)
        rows.append([f"  {pr}", a, b, f"{b - a:+d}"])
    a, b = hole_count(drc2), hole_count(drc3)
    rows.append(["**mounting-hole rules (H1–H8 as PE)**", a, b, f"{b - a:+d}"])
    a, b = s2["unconnected"], s3["unconnected"]
    rows.append(["**unconnected items**", a, b, f"{b - a:+d}"])
    w(table(rows, ["type", "step 2", "step 3", "delta"]))
    w("")
    c2 = {frozenset(p) for p in s2["courtyard_pairs"]}
    c3 = {frozenset(p) for p in s3["courtyard_pairs"]}
    gone = sorted("/".join(sorted(p)) for p in c2 - c3)
    new = sorted("/".join(sorted(p)) for p in c3 - c2)
    w(f"Courtyard-overlap pairs: step 2 {len(c2)}, step 3 {len(c3)}; resolved ({len(gone)}): {', '.join(gone) or '–'}; "
      f"new ({len(new)}): {', '.join(new) or '–'}.")
    w("")
    f0 = p3_first_summary(dom)
    w(f"### Step 3 follow-up: DRC delta {P3_FIRST} → now")
    w("")
    keys = sorted(set(f0["types"]) | set(s3["types"]), key=lambda k: -max(f0["types"].get(k, 0), s3["types"].get(k, 0)))
    rows = [[k, f0["types"].get(k, 0), s3["types"].get(k, 0), f"{s3['types'].get(k, 0) - f0['types'].get(k, 0):+d}"]
            for k in keys if f0["types"].get(k, 0) != s3["types"].get(k, 0)]
    a, b = sum(f0["types"].values()), sum(s3["types"].values())
    rows.append(["**all violations**", a, b, f"{b - a:+d}"])
    a, b = sum(f0["iso"].values()), sum(s3["iso"].values())
    rows.append(["**isolation, between two domains**", a, b, f"{b - a:+d}"])
    a, b = f0["holes"], hole_count(drc3)
    rows.append(["**mounting-hole rules**", a, b, f"{b - a:+d}"])
    a, b = f0["unconnected"], s3["unconnected"]
    rows.append(["**unconnected items**", a, b, f"{b - a:+d}"])
    a, b = f0["deleted"], sum(p3["deleted"].values())
    rows.append(["copper items deleted by step 3", a, b, f"{b - a:+d}"])
    w(table(rows, ["type (only those that changed)", P3_FIRST, "now", "delta"]))
    w("")
    c0 = {frozenset(p) for p in f0["courtyard_pairs"]}
    w(f"Courtyard pairs {len(c0)} → {len(c3)}; new: {', '.join(sorted('/'.join(sorted(p)) for p in c3 - c0)) or '–'}; "
      f"resolved: {', '.join(sorted('/'.join(sorted(p)) for p in c0 - c3)) or '–'}.")
    w("")
    w("### Per area (step 2 → step 3)")
    w("")
    rows = []
    for name, (title, refs, margin) in P3_AREAS.items():
        bx = boxes[name]
        i2, i3 = area_iso(drc2, bx, dom), area_iso(drc3, bx, dom)
        v2, n2 = area_violations(drc2, bx)
        v3, n3 = area_violations(drc3, bx)
        prs = sorted(set(i2) | set(i3))
        area_refs = [r for r, fp in g3["fps"].items() if bx[0] < fp["x"] < bx[2] and bx[1] < fp["y"] < bx[3]]
        cyA, cyB = cy_pairs_in(drc2, area_refs), cy_pairs_in(drc3, area_refs)
        shA, shB = shorts_of(drc2, area_refs), shorts_of(drc3, area_refs)
        rows.append([title, f"x {bx[0]:.0f} … {bx[2]:.0f}, y {bx[1]:.0f} … {bx[3]:.0f}",
                     ", ".join(f"{p} {i2.get(p, 0)} → {i3.get(p, 0)}" for p in prs) or "–",
                     f"{len(cyA)} → {len(cyB)}", f"{sum(1 for t, _ in shA if t == 'shorting_items')} → "
                     f"{sum(1 for t, _ in shB if t == 'shorting_items')}",
                     f"{v2.get('clearance', 0)} → {v3.get('clearance', 0)}", f"{v2.get('creepage', 0)} → {v3.get('creepage', 0)}",
                     f"{v2.get('hole_clearance', 0)} → {v3.get('hole_clearance', 0)}", f"{n2} → {n3}"])
    w(table(rows, ["area", "box (mm)", "isolation violations by domain pair", "courtyard pairs", "shorts",
                   "clearance (all)", "creepage (all)", "hole clearance", "unconnected"]))
    w("")
    w("Zooms: as step 2 (magenta = moved / placed by step 3, dashed courtyard = bottom side, black = slots, cyan dashed = "
      "step-3 pour keep-outs, pale = step-2 keep-outs, grey + = end points of deleted copper).")
    w("")
    for name, (title, _, _) in P3_AREAS.items():
        w(f"![{title}](zoom_p3_{name}.png)")
        w("")
    w(P3_NOTES)
    with open(os.path.join(D, "REPORT.md"), "a") as f:
        f.write("\n".join(L) + "\n")
    print("trial_report: appended 'After placement step 3'")


P3_NOTES = """### Notes on step 3

Written after reviewing the step-3 numbers (2026-11-19); the tables above are regenerated, this text is not.

**0. KiCad's creepage DRC does not list every pair.** Step 2 reported one B.Cu pair below the heater island
(Net-(AD1-VA) ↔ 5V, 5.62 mm), but the GND / Q9 gate tracks and the Q9 / C35 / R44 / R32 pads next to that 5V track
are 6.0 … 7.9 mm from the same heater track / R91 / R117 pads and were not listed. The areas of this step were
therefore also checked with a straight-line same-layer scan of pads, tracks, vias and the refilled zone copper
(scratch script, no slot credit, pad bounding boxes): after step 3 the only heater ↔ primary pairs under 8.0 mm
are the ones with a slot between them (the two ISO1 pin rows; ISO1 pins 6–8 ↔ TR2 pad 10 / WP4 / the Q14_DRAIN
and GND pours across the new slot), and no PE pad / track is closer than 3.2 mm (round-pad distance) to primary
copper. "0 creepage violations" in the tables means "none reported", not a proof – that scan is now
`tools/next/check_domains.py` (true pad shapes, slot credit by the path round the slots; follow-up below).

**1. Heater barrier at ISO1 / TR2 (HEATER-PRI 36 → 0).** Three spots, three fixes:
(a) *Top end of ISO1.* The ISO1 primary pins 5–8 (x −37.7, pin 8 = GND at y −59.3) look straight at the heater
pins TR2 pad 10 (5.4 mm) and WP4 (5.2 mm) and at the Q14_DRAIN pours (4.0 mm): the ISO1 footprint slot ends at
y −62.1 and only separates its own pin rows. ISO1 now has a board-specific footprint
(`SOIC-16W_7.5x10.3mm_P1.27mm_Slot8.0_T_ISO1`, follow-up below) whose slot is a T: the stem between the pin rows
runs on into a 1.0 mm cross slot x −45.5 … −31.0, y −64.1 … −63.1, 0.8 mm below TR2 pad 10. The surface path pin 8
→ pad 10 goes round the right end of the bar (12.0 mm, pin 7 12.8 mm, pin 8 → WP4 17.6 mm; to the left stem and bar are one cut). WP4 moved 1.0 mm
up with its spokes (pad edge 1.3 mm from the slot). Inner layers get no slot credit, so the primary copper within
8.0 mm of the pad 10 / WP4 barrels went: the GND via at ISO1 pin 8 and three In4 HT_SDATA segments (pin 8 / pin 7
must be fanned out downwards). Pour keep-out x −47.5 … −27.0, y −66 … −59 on all layers (heater pours stay above
the slot, primary pours 8 mm from pad 10 where the slot does not shield), and one between the TR2 pin rows
(Q14_DRAIN / HEATER_HI_SOURCE pours were 6.6 mm apart). *Rejected:* a board slot drawn over the footprint slot –
KiCad reports two overlapping Edge.Cuts outlines as a self-intersecting outline (tested); a separate board slot
1 mm above the ISO1 slot end (the first step-3 version) – works, but leaves a 1 × 1 mm web between two slots; a
separate slot right of the ISO1 slot end – the gap between the slots leaves a 7.9 mm path; moving ISO1 2.7 mm
down – all 16 pins lose their routing and the heater side comes closer to the mains copper below (spot b).
(b) *Below the heater island (bottom side).* The relay driver Q9 / C35 / R44 / R32 with its 5V / GND / gate tracks
sat 5.6 … 8 mm below ISO1 pin 16 / C59 / R91 / R117 and at the same time 3.0 mm above the PE pad of C82: the
primary strip left between "8 mm from the heater" and "3.2 mm from PE" is 0 … 1.7 mm high there. The four parts
moved to the free bottom side under the relay RL1 between its coil pins and D9 / D28 (Q9 drain 2.7 mm from D9's
anode, ≥ 1.9 mm from the mains pins of RL1 – HV functional 1.2 mm); their copper and 6 more primary segments within
8 mm of the island were deleted; GPIO_BYPASS_RLY (In4) now needs a ≈ 20 mm longer run to R44 / R32. Pour keep-out
x −60.5 … −40, y −50 … −41.8 (the RL1-COM mains pour was 4.1 mm from C59). Three heater Net-(AD1-VA) B.Cu segments
7.4 … 7.7 mm from R27 pad 1 (RL1-COM) deleted: re-route them above y −52.6. *Rejected:* shifting the Q9 group
down (blocked by the PE pad of C82) or the heater parts up (packed island).
(c) *TR2.* Nothing to move: the pin rows are 10.4 mm apart; only the pours were too close (keep-out).

**2. PE ↔ primary at the Y capacitors / RL1 (PE-PRI 22 → 0).** C85 1.6 mm up: its PE pad is now 3.4 mm from RL1
pin 1 (was 2.58 mm; moving it right is blocked by C81 / C82). Six 2 mm wide PE B.Cu segments passing CM1 pads 2 / 3 /
4 and RL1 pin 1 at 1.4 … 3.0 mm, the IN2 F.Cu sense track 3.06 mm from C65's PE pad and the GPIO_BYPASS_RLY via at
C82 were deleted (PE net to re-route ≥ 3.2 mm from the CM1 pins, e.g. 1.0 mm wide or 1 mm further left). The zone
filler only keeps the 2.0 mm clearance, so a pour keep-out of PE copper + 3.25 mm (all layers, 4 polygons) holds
the IN2 / L1_PRI2 / RL1-COM / RES_IN / GND pours back; it is computed from the PE pads and the PE tracks that are
left, so it must be re-made when PE is routed. *Rejected:* a slot at the Y caps (the pad pairs are THT discs with
7.5 mm pitch, there is no pad pair that needs one once the pours are held off); moving C65 / CM1.
Mounting holes (PE): keep-out circles round H1–H8 (pours were 2.95 mm from the rings), and all tracks inside the
hole spacing deleted – the two B.Cu tracks of the step-2 notes (H4 ↔ 15V, 2 segments; H5 ↔ CUK_CAP_MEAS-, 4
segments) and 22 more: 19 In4 segments (GPIO_BYPASS_RLY, +3V3, HT_CLK, HT_SDATA, SYNCH_1, SYNCH_2 next to H4;
Net-(R48-Pad2) / Net-(R51-Pad2) next to H7; Net-(AD2-CLK) next to H5), 2 F.Cu 420V segments at H5 (4.12 of 4.2 mm)
and the B.Cu track between R47 and R48 at H7. The pads inside the hole spacing moved in the follow-up (below): mounting-hole
markers 48 → 0.

**3. The 54 added parts are all on the board** (none left in the grid, no new courtyard pair, no pad short, no
isolation marker; placed by a nearest-free-spot search, 0.3 mm from foreign copper, 1.25 mm for HV net pads, so no
5.1 track was deleted for them):
- *Heater LLC split-cap balancing R155–R158* (bottom side under C42 / C49 / C22, DC+ pad of R155 under C42's DC+
  pad; chain DC+ → HEATER_CAP_MEAS → HEATER_CURRENT, all pads ≥ 1.25 mm from other copper, 12 mm from the UART
  island). *DAB primary R143–R146* bottom side under C47 / C54 (same order as the caps), *DAB secondary R147–R150*
  bottom side under C16 / C55. Bottom side because the top side next to the 1210 caps is taken by TR3 / J4 / Q10;
  each chain needs one via per cap terminal.
- *Dead-time parts:* R127 / C118 and R129 / C120 (DAB_DIS) left of DRV5 pins 5 / 6, R128 / C119 below DRV6 pin 6
  (secondary side, 6 mm from the pin – nothing closer is free under TR3), R130 / C121 below DRV3 pin 6. D35 (heater
  high-side turn-off diode) between R36 and R59.
- *Flyback (PWM2):* C140 / R154 (VIN) and C138 on top above pins 1–4, R138 / R139 (VERR), C139 / R140 / R141 (FB)
  on the bottom side under pins 1–4; the line-OVP chain R151–R153 on the bottom side from R116's DC+ pad along the
  board edge to R153 (VIN run of ≈ 13 mm to pin 1 – low impedance at the pin through C140); R142 under D10;
  bleeders R125 (15V, bottom, at D5) and R126 (5V, top, above R8).
- *Analog:* U9 + C128 / C129 / R131 at R3 / R110 (bottom), U10 + C132 / C133 / R132–R135 under R11 / R12
  (bottom, AUX_MEAS divider; outputs 6 / 13 mm from J2 pins 43 / 49), C122–C125 at U1, C126 / C127 at U8, C130 / C131
  at U6.

**4. Leftovers of step 2.** *PWM2 drain copper:* the added parts keep x 40.6 … 47.7, y −2 … 6.6 free on both outer
layers and the strip y 7.2 … 10.6 to D7 / TR1 pin 12 on F.Cu. Room as placed: F.Cu ≈ 0.5 cm² at the pins + 0.5 cm²
strip, B.Cu ≈ 0.5 cm² under it + 0.4 cm² below (x 40.6 … 46.3, y 6.6 … 14, where the 5.1 GND pour has to give
way) = **≈ 1.9 cm²**, i.e. the lower end of the 2–3 cm² target without moving anything; moving R114–R116 1 mm left
would add only ≈ 0.08 cm² per layer (a 5.1 track at x 36.7 limits it) and C58 cannot move right (C51), so neither
was moved. *Texts:* J4, ISO2, ISO1, U11 and C13 references moved off the slots / the edge (silk-to-edge 17 → 14 at 6d8c3a9, 15 after the follow-up: the extra one is a single-item marker at the board corner x −71.9 / y 18.7, not traced yet);
the rest are footprint silk lines that cross a slot (Q21 / Q8 / TR3 over the L-slot, TR1, TR2 over the new slot,
one line each of ISO1 / ISO2 / U11) – fix in the footprints.

**Remaining after step 3** (beyond routing – unconnected items and dangling tracks from the deleted copper):
PRI-SEC 2 (TR1 pin 2 / 9 inner barrels, as step 2, on the `check_domains.py` allow list); footprint silk lines over
slots (TR2 over the T bar, Q21 / Q8 / TR3 / TR1, one line each of ISO1 / ISO2 / U11); HV-functional / net-class
clearances inside one domain (routing).

### Step 3 follow-up (2026-11-19, user decisions on the first step-3 result 6d8c3a9)

1. **T slot instead of slot + web.** `gen_next_footprints_parts.py` `SOIC_T` generates
   `tube_psu_next_parts:SOIC-16W_7.5x10.3mm_P1.27mm_Slot8.0_T_ISO1`: one closed Edge.Cuts outline = the 8.0 mm slot
   plus the cross slot (footprint x −11.35 … 3.15, y 8.25 … 9.25; ISO1 sits at 180°). The schematic / footprint map
   keep the plain `_Slot8.0` for ISO1 (steps 0–2 stay reproducible); step 3 swaps the footprint on the board
   (`FOOTPRINTS`, same pads, tracks kept). `check_footprints.py` checks the variant through `BOARD_VARIANTS` (pads,
   8.85 mm pin-row path, KiCad DRC) – its slot obstacles used to be convex hulls, a T is not convex, so non-convex
   outlines are now tested exactly. The board has 5 internal cut-outs instead of 6, no web; surface path ISO1 pin 8
   → TR2 pad 10 = 12.0 mm (8.0 needed), computed round the real slot outline. Courtyard of the
   variant = body + stem only (the bar runs 6 mm under the edge of TR2's body; TR2 silk crosses it).
2. **Pads at the mounting holes (14 markers → 0).** R47 / R48 and the row above them R50 / R51 0.9 mm up (R48 pad
   1 3.4 mm from the H7 ring; the group's two vias ended up 1.1 mm from R19 pad 1 and were deleted, with two In4
   stubs); R14 with R1 / R43 0.45 mm down (R14 pad 2 3.29 mm from the H4 ring); C102 turned 90° about its body
   centre (pads at x 77.0, y 8.85 / 13.85: 7.2 / 7.3 mm from H8 where 6.95 mm is needed, 15.7 mm from the DC+ fly
   lead) and the −100 V bleeder R68 (bottom) 2.3 mm down between the new C102 pads – 2 mm to the left it would be
   10.99 mm round the TR1 slot from the DC+ fly lead (found by `check_domains.py`). L2 pad 2 is 3.3 … 3.5 mm from
   the H4 ring (round pad; the 2.99 mm of the first report was a bounding-box figure) – not moved.
3. **`tools/next/check_domains.py`** (in `check_next.sh`): straight same-layer distance between all copper of two
   isolation domains (true pad shapes, tracks, vias, filled zones, holes as PE) against the `.kicad_dru` limits,
   slot credit only where a slot blocks the straight line (then the path round the slots counts), `ALLOW` list for
   the Q19 / Q21 slot rule and the TR1 pin 2 / 9 barrels. On this board: no pair below its limit; on the step-2
   board it lists 163 HEATER-PRI creepage pairs where KiCad's DRC listed 16.
4. **U10 pad gap.** `.kicad_dru` rule "Same-footprint pad gap, low-voltage classes" (0.15 mm between pads of one
   footprint unless a HV or PE net is involved; `A.Parent == B.Parent`), proven by three pad tests in
   `check_rules.py` (without the rule both low-voltage tests fail). The step-3 project now copies the current
   `kicad_next/tube_psu_5_2.kicad_dru`.
5. **Accepted:** the split-cap balancing resistors on the bottom side under their capacitors, and the 22 extra
   track segments deleted inside the mounting-hole spacing. Via room at the balancing chains with 1.2 mm HV spacing
   to all other copper (0.8 mm via, within 1 mm of the capacitor's top copper and 2 mm of the resistor pad): free
   area 2.2 mm² (R155 DC+, the tightest) … 18 mm² at 11 of the 12 chain ends; the twelfth, R158 pad 2
   (HEATER_CURRENT), needs no via – R30 pad 1 of the same net is 3 mm away on the bottom side.
"""

if __name__ == "__main__":
    sys.exit(main())
