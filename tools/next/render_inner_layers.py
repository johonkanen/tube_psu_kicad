#!/usr/bin/env python3
"""PNGs of the inner layers of the 5.2 board for the routing review -> kicad_next/routing/ (system python3).

    python3 tools/next/render_inner_layers.py [BOARD.kicad_pcb] [OUTDIR]

    In1_GND.png, In2_Signal_HV.png, In3_Power.png, In4_GND.png   kicad-cli plot of each inner layer + Edge.Cuts, fitted to the page
                                                    (zones as stored in the board: run it on a filled board)
    inner_domains.png                               the four inner layers side by side, all copper coloured by
                                                    isolation domain (pads / barrels, tracks, vias, zone fills),
                                                    slots black, zone-fill keep-outs of the layer hatched
Needs pdftoppm (poppler-utils), matplotlib and shapely; geometry through check_domains.py --dump (kipy).
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import check_domains as cd  # noqa: E402

CLI = os.path.join(ROOT, "tools", "p2k", "bin", "kicad-cli")
KIPY = os.path.join(ROOT, "tools", "p2k", "bin", "kipy")
INNER = [("In1.Cu", "In1.GND"), ("In2.Cu", "In2.Signal_HV"), ("In3.Cu", "In3.Power"), ("In4.Cu", "In4.GND")]
DPI = 250
COLOR = {"PRI": "#c0392b", "SEC": "#e08a00", "HEATER": "#2e9e44", "UART": "#2f6fd6", "PE": "#17a3a3",
         "HOLE": "#707070", "": "#000000"}
LABEL = {"PRI": "primary (GND)", "SEC": "DAB secondary (ISO_GND)", "HEATER": "heater (HT_GND)",
         "UART": "UART island", "PE": "protective earth", "HOLE": "mounting holes (earthed)"}
KEEPOUTS = """
import pcbnew, sys, json
b = pcbnew.LoadBoard(sys.argv[1]); out = []
def add(z):
    o = z.Outline()
    for i in range(o.OutlineCount()):
        c = o.Outline(i)
        out.append(dict(layers=[b.GetLayerName(l) for l in z.GetLayerSet().CuStack()], name=z.GetZoneName(),
                        pts=[[c.CPoint(k).x / 1e6, c.CPoint(k).y / 1e6] for k in range(c.PointCount())]))
for z in b.Zones():
    if z.GetIsRuleArea() and z.GetDoNotAllowZoneFills(): add(z)
for fp in b.GetFootprints():
    for z in fp.Zones():
        if z.GetIsRuleArea() and z.GetDoNotAllowZoneFills(): add(z)
json.dump(out, open(sys.argv[2], "w"))
"""


def main(argv):
    board = os.path.abspath(argv[0]) if argv else os.path.join(ROOT, "kicad_next", "tube_psu_5_2.kicad_pcb")
    out = os.path.abspath(argv[1]) if len(argv) > 1 else os.path.join(ROOT, "kicad_next", "routing")
    os.makedirs(out, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for canon, name in INNER:
            pdf = os.path.join(tmp, "l.pdf")
            subprocess.run([CLI, "pcb", "export", "pdf", "--layers", f"{canon},Edge.Cuts", "--mode-single",
                            "--scale", "0",       # autoscale: the board origin is off the page
                            "-o", pdf, board], check=True, capture_output=True)
            png = os.path.join(out, name.replace(".", "_"))
            subprocess.run(["pdftoppm", "-r", str(DPI), "-png", "-singlefile", pdf, png], check=True)
            crop(png + ".png")
            print(os.path.relpath(png + ".png", ROOT))
        js, kj = os.path.join(tmp, "g.json"), os.path.join(tmp, "k.json")
        subprocess.run([KIPY, os.path.join(HERE, "check_domains.py"), "--dump", board, js], check=True, capture_output=True)
        subprocess.run([KIPY, "-c", KEEPOUTS, board, kj], check=True, capture_output=True)
        with open(js) as f:
            g = json.load(f)
        with open(kj) as f:
            keepouts = json.load(f)
    overview(g, keepouts, cd.net_classes(board), os.path.join(out, "inner_domains.png"))
    print(os.path.relpath(os.path.join(out, "inner_domains.png"), ROOT))
    return 0


def crop(png):
    """cut the page down to the drawing (+ margin)"""
    import matplotlib.image as mpimg
    import numpy as np
    a = mpimg.imread(png)
    ink = np.argwhere(a[:, :, :3].min(axis=2) < 0.98)
    if len(ink):
        (y0, x0), (y1, x1) = ink.min(axis=0), ink.max(axis=0)
        m = 20
        mpimg.imsave(png, a[max(0, y0 - m):y1 + m, max(0, x0 - m):x1 + m])


def overview(g, keepouts, cls, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch, PathPatch
    from matplotlib.path import Path
    from shapely.geometry import LineString, Point, Polygon
    from shapely.ops import unary_union

    def dom(net):
        return cd.CLASS_DOMAIN.get(cls.get(net, ""), "")

    def draw(ax, geom, **kw):
        for p in (geom.geoms if hasattr(geom, "geoms") else [geom]):
            if p.geom_type != "Polygon" or p.is_empty:
                continue
            verts, codes = [], []
            for ring in [p.exterior] + list(p.interiors):
                c = list(ring.coords)
                verts += c
                codes += [Path.MOVETO] + [Path.LINETO] * (len(c) - 2) + [Path.CLOSEPOLY]
            ax.add_patch(PathPatch(Path(verts, codes), **kw))

    mk = lambda pp: unary_union([Polygon(r, h).buffer(0) for r, h in pp])  # noqa: E731
    xs = [x for s in g["slots"] for x, _ in s]
    fig, axes = plt.subplots(2, 2, figsize=(30, 21))
    for ax, (_, layer) in zip(axes.flat, INNER):
        zones, rest = {}, {}
        for z in g["zones"]:
            if z["layer"] == layer:
                zones.setdefault(dom(z["net"]), []).append(mk(z["polys"]))
                c = mk(z["polys"]).representative_point()
                ax.text(c.x, c.y, z["net"].split("/")[-1], fontsize=8, ha="center", va="center", zorder=5)
        for p in g["pads"]:
            if layer in p["layers"]:
                d = "HOLE" if cd.HOLES.match(p["ref"]) else dom(p["net"])
                rest.setdefault(d, []).append(mk(p["polys"]))
        for t in g["tracks"]:
            if t["layer"] == layer:
                x0, y0, x1, y1 = t["pts"]
                geom = Point(x0, y0) if (x0, y0) == (x1, y1) else LineString([(x0, y0), (x1, y1)])
                rest.setdefault(dom(t["net"]), []).append(geom.buffer(max(t["w"] / 2, 0.12), 4))
        for v in g["vias"]:
            if layer in v["layers"]:
                rest.setdefault(dom(v["net"]), []).append(Point(v["x"], v["y"]).buffer(v["d"] / 2, 6))
        for d, geoms in zones.items():
            draw(ax, unary_union(geoms), fc=COLOR[d], alpha=0.45, ec=COLOR[d], lw=0.6)
        for d, geoms in rest.items():
            draw(ax, unary_union(geoms), fc=COLOR[d], ec="none")
        for k in keepouts:
            if layer in k["layers"] and len(k["pts"]) > 2:
                draw(ax, Polygon(k["pts"]).buffer(0), fc="none", ec="#555555", lw=0.5, hatch="///", alpha=0.35)
        for s in g["slots"]:
            draw(ax, Polygon(s), fc="black", ec="black")
        ax.set_xlim(-73, 92.5)
        ax.set_ylim(20, -93)
        ax.set_aspect("equal")
        ax.set_xticks(range(-70, 95, 10))
        ax.set_yticks(range(-90, 21, 10))
        ax.grid(True, lw=0.3)
        ax.set_title(layer, fontsize=14)
    fig.legend(handles=[Patch(fc=COLOR[d], label=LABEL[d]) for d in LABEL]
               + [Patch(fc="white", ec="#555555", hatch="///", label="zone-fill keep-out"),
                  Patch(fc="black", label="slot")], loc="lower center", ncol=8, fontsize=12)
    fig.suptitle("tube_power 5.2 inner layers - copper by isolation domain (plan view from the top, mm)", fontsize=16)
    fig.tight_layout(rect=(0, 0.03, 1, 0.97))
    fig.savefig(path, dpi=80)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
