#!/usr/bin/env python3
"""PNGs of the outer layers of the 5.2 board for the review of routing stage 3a -> kicad_next/routing/ (python3).

    python3 tools/next/render_s3a.py [BOARD.kicad_pcb] [OUTDIR]

    s3a_F_Cu.png, s3a_B_Cu.png   kicad-cli plot of each outer layer + Edge.Cuts (both seen from the top, zones as
                                 stored in the board: run it on a filled board)
    s3a_power_nets.png           F.Cu and B.Cu side by side: all copper grey, the copper of stage 3a
                                 (routing/s3a_added.json + the S3A_* zones) coloured by net group, slots black,
                                 the TR3 barrier band and the regenerated PE pour keep-outs hatched
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
import render_inner_layers as ril  # noqa: E402

CLI, KIPY = ril.CLI, ril.KIPY
DPI = 250
# (label, colour, test on the net name)
GROUPS = [
    ("DC+ / mains", "#d62728", lambda n: n in ("DC+", "Net-(RL1-COM)") or n.startswith("/05 PFC/") and "PE" not in n),
    ("PE", "#17a3a3", lambda n: n.endswith("/PE")),
    ("PWM2 drain (FLY_C), clamp", "#c020c0", lambda n: "FLY_C" in n or n in ("Net-(D7-K)",)),
    ("switch nodes / split-capacitor midpoints", "#ff8c00",
     lambda n: any(k in n for k in ("HI_SOURCE", "DHB_CAP", "TRANS_SEC", "DHB_CURRENT", "HEATER_CURRENT", "TR1-"))),
    ("420V / -100 V", "#8c564b", lambda n: n in ("420V", "-100V BIAS")),
    ("grounds (GND, ISO_GND, HT_GND, ISO_UART_GND)", "#2ca02c", lambda n: n.endswith("GND")),
    ("supply rails and the rest", "#1f77b4", lambda n: True),
]


def group(net):
    return next(i for i, (_, _, f) in enumerate(GROUPS) if f(net))


def main(argv):
    board = os.path.abspath(argv[0]) if argv else os.path.join(ROOT, "kicad_next", "tube_psu_5_2.kicad_pcb")
    out = os.path.abspath(argv[1]) if len(argv) > 1 else os.path.join(ROOT, "kicad_next", "routing")
    with open(os.path.join(ROOT, "kicad_next", "routing", "s3a_added.json")) as f:
        added = json.load(f)["added"]
    with tempfile.TemporaryDirectory() as tmp:
        for canon in ("F.Cu", "B.Cu"):
            pdf = os.path.join(tmp, "l.pdf")
            subprocess.run([CLI, "pcb", "export", "pdf", "--layers", f"{canon},Edge.Cuts", "--mode-single",
                            "--scale", "0", "-o", pdf, board], check=True, capture_output=True)
            png = os.path.join(out, "s3a_" + canon.replace(".", "_"))
            subprocess.run(["pdftoppm", "-r", str(DPI), "-png", "-singlefile", pdf, png], check=True)
            ril.crop(png + ".png")
            print(os.path.relpath(png + ".png", ROOT))
        js, kj = os.path.join(tmp, "g.json"), os.path.join(tmp, "k.json")
        subprocess.run([KIPY, os.path.join(HERE, "check_domains.py"), "--dump", board, js], check=True, capture_output=True)
        subprocess.run([KIPY, "-c", ril.KEEPOUTS, board, kj], check=True, capture_output=True)
        with open(js) as f:
            g = json.load(f)
        with open(kj) as f:
            keepouts = json.load(f)
    overview(g, keepouts, added, os.path.join(out, "s3a_power_nets.png"))
    print(os.path.relpath(os.path.join(out, "s3a_power_nets.png"), ROOT))
    return 0


def overview(g, keepouts, added, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch, PathPatch
    from matplotlib.path import Path
    from shapely.geometry import LineString, Point, Polygon
    from shapely.ops import unary_union

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
    fig, axes = plt.subplots(1, 2, figsize=(34, 13))
    for ax, layer in zip(axes, g["outer"]):
        old, pads = [], []
        new = {}
        for z in g["zones"]:
            if z["layer"] == layer:
                if z["name"].startswith("S3A_"):
                    new.setdefault(group(z["net"]), []).append(mk(z["polys"]))
                else:
                    old.append(mk(z["polys"]))
        for p in g["pads"]:
            if layer in p["layers"]:
                pads.append(mk(p["polys"]))
        for t in g["tracks"]:
            if t["layer"] == layer:
                x0, y0, x1, y1 = t["pts"]
                geom = Point(x0, y0) if (x0, y0) == (x1, y1) else LineString([(x0, y0), (x1, y1)])
                old.append(geom.buffer(max(t["w"] / 2, 0.1), 4))
        for v in g["vias"]:
            if layer in v["layers"]:
                old.append(Point(v["x"], v["y"]).buffer(v["d"] / 2, 6))
        for a in added:
            if a["kind"] == "track" and a["layer"] == layer:
                new.setdefault(group(a["net"]), []).append(LineString([a["a"], a["b"]]).buffer(max(a["w"] / 2, 0.15), 4))
            elif a["kind"] == "via":
                new.setdefault(group(a["net"]), []).append(Point(a["x"], a["y"]).buffer(a["d"] / 2, 8))
        draw(ax, unary_union(old), fc="#d8d8d8", ec="none")
        draw(ax, unary_union(pads), fc="#a8a8a8", ec="none")
        for i, geoms in sorted(new.items()):
            draw(ax, unary_union(geoms), fc=GROUPS[i][1], ec="none", alpha=0.9)
        for k in keepouts:
            if layer in k["layers"] and len(k["pts"]) > 2 and (k["name"].startswith("S3A_KO") or "barrier" in k["name"]):
                draw(ax, Polygon(k["pts"]).buffer(0), fc="none", ec="#555555", lw=0.5, hatch="///", alpha=0.3)
        for s in g["slots"]:
            draw(ax, Polygon(s), fc="black", ec="black")
        ax.set_xlim(-73, 92.5)
        ax.set_ylim(20, -93)
        ax.set_aspect("equal")
        ax.set_xticks(range(-70, 95, 10))
        ax.set_yticks(range(-90, 21, 10))
        ax.grid(True, lw=0.3)
        ax.set_title(layer + " (seen from the top)", fontsize=14)
    fig.legend(handles=[Patch(fc=c, label=l) for l, c, _ in GROUPS]
               + [Patch(fc="#d8d8d8", label="kept 5.1 copper"), Patch(fc="#a8a8a8", label="pads"),
                  Patch(fc="white", ec="#555555", hatch="///", label="TR3 barrier band / PE pour keep-outs"),
                  Patch(fc="black", label="slot")], loc="lower center", ncol=6, fontsize=12)
    fig.suptitle("tube_power 5.2 routing stage 3a - power, HV and ground copper added (mm)", fontsize=16)
    fig.tight_layout(rect=(0, 0.06, 1, 0.97))
    fig.savefig(path, dpi=70)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
