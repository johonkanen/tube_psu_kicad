#!/usr/bin/env python3
"""PNG drawings of the 5.2 footprints (pads, Edge.Cuts slots, courtyard, fab, keep-out notes) from the
geometry dump of check_footprints.py, with matplotlib (system python, not the KiCad AppImage).

    tools/p2k/bin/kipy tools/next/check_footprints.py --dump reports/next/footprints.json
    python3 tools/next/render_footprints.py reports/next/footprints.json reports/next/footprints/
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Arc, Circle, Polygon  # noqa: E402

COL = {"F.Fab": "#888888", "F.SilkS": "#2a7f2a", "F.CrtYd": "#d070d0", "Edge.Cuts": "#d4a000",
       "Cmts.User": "#3070d0", "F.Cu": "#c83737"}
COL.update({"F.Silkscreen": COL["F.SilkS"], "F.Courtyard": COL["F.CrtYd"], "User.Comments": COL["Cmts.User"]})


def draw(name, d, out):
    fig, ax = plt.subplots(figsize=(6, 6))
    for g in d["graphics"]:
        c = COL.get(g["l"])
        if c is None:
            continue
        lw = 2.0 if g["l"] == "Edge.Cuts" else 0.8
        if g["t"] == "line":
            (x0, y0), (x1, y1) = g["p"]
            ax.plot([x0, x1], [y0, y1], color=c, lw=lw)
        elif g["t"] == "poly":
            ax.add_patch(Polygon(g["p"], closed=True, fill=False, ec=c, lw=lw))
        elif g["t"] == "circle":
            ax.add_patch(Circle(g["c"], g["r"], fill=False, ec=c, lw=lw))
        elif g["t"] == "arc":
            xs, ys = zip(*g["p"])
            ax.plot(xs, ys, color=c, lw=lw)
    for p in d["pads"]:
        ax.add_patch(Polygon(p["poly"], closed=True, fc=COL["F.Cu"], ec="none", alpha=0.75))
        cx = sum(x for x, _ in p["poly"]) / len(p["poly"])
        cy = sum(y for _, y in p["poly"]) / len(p["poly"])
        if p["drill"]:
            ax.add_patch(Circle((cx, cy), p["drill"] / 2, fc="white", ec="none"))
        if p["n"]:
            ax.text(cx, cy, p["n"], ha="center", va="center", fontsize=6)
    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.invert_yaxis()
    ax.grid(True, lw=0.3, alpha=0.5)
    ax.set_title(name, fontsize=8)
    ax.set_xlabel("mm (pads red, Edge.Cuts slot yellow, courtyard magenta, Cmts.User blue)", fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(out, name.split(":")[1] + ".png"), dpi=130)
    plt.close(fig)


def main(argv):
    data = json.load(open(argv[0]))
    os.makedirs(argv[1], exist_ok=True)
    for name, d in sorted(data.items()):
        draw(name, d, argv[1])
    print(f"render_footprints: {len(data)} PNGs in {argv[1]}")


if __name__ == "__main__":
    main(sys.argv[1:])
