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

if __name__ == "__main__":
    sys.exit(main())
