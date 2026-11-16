"""Tables and plots from the cached results of run_flyback.py.

Writes out/report.md (full tables), results.md (committed summary tables), and the PNGs
geometry_<option>.png and crossreg.png.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import flyback_sim as fs  # noqa: E402
import options as opts  # noqa: E402
import run_flyback as rf  # noqa: E402

OUT = os.path.join(HERE, "out")
RAILS = list(fs.RAILS)
EFFECTIVE = ["P", "A15", "A5", "S15", "S5", "SN5", "SHV"]
# effective winding -> original windings in series
COMBINE = {"P": [["P"], ["P1", "P2"]], "A15": [["A15"], ["A5", "A15x"]], "A5": [["A5"]],
           "S15": [["S15"], ["S5", "S15x"]], "S5": [["S5"]], "SN5": [["SN5"]],
           "SHV": [["SHV"], ["SN5", "SHVx"]]}
RAIL_OF = {"A15": "20V", "A5": "5V", "S15": "20V_ISO_SEC", "S5": "5V_ISOL", "SN5": "-5V_SEC", "SHV": "-100V BIAS"}
# KiCad net names since commit 46a60f9 (the scripts keep the Proteus labels internally)
DISPLAY = {"20V": "15V", "20V_ISO_SEC": "15V_ISO_SEC"}


def dn(rail):
    return DISPLAY.get(rail, rail)


def dc(case):
    return case.replace("_20V", "_15V")


COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]


def effective(res):
    """Inductance matrix of the effective windings (series sections combined)."""
    names = res["names"]
    L = np.array(res["L"])
    N = np.array(res["turns"])
    T = np.zeros((len(EFFECTIVE), len(names)))
    for i, e in enumerate(EFFECTIVE):
        for alt in COMBINE[e]:
            if all(a in names for a in alt):
                for a in alt:
                    T[i, names.index(a)] = 1
                break
    Le = T @ L @ T.T
    Ne = T @ N
    return Le, Ne


def leakage_table(res):
    Le, Ne = effective(res)
    Lr = Le * Ne[0] ** 2 / np.outer(Ne, Ne)
    d = np.diag(Lr)
    return d[:, None] + d[None, :] - 2 * Lr      # short-circuit inductance referred to the 52 T primary


def load(name):
    om = json.load(open(os.path.join(OUT, "om", f"{name}.json")))
    res = {}
    for c in rf.cases():
        p = os.path.join(OUT, "results", f"{name}__{c['name']}.json")
        if os.path.exists(p):
            res[c["name"]] = json.load(open(p))
    return om, res


def spread(res, rail, exclude=("nom325",)):
    v = [r[rail] for k, r in res.items() if k not in exclude and r.get(rail) is not None]
    return (min(v), max(v)) if v else (None, None)


def geometry_png(name, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle
    import om_model as m
    opt = opts.get(name)
    coil, rep = m.build_coil(opt)
    xi, xo, yb, yt = m.window()
    fig, ax = plt.subplots(figsize=(3.3, 5.0), dpi=110)
    ax.add_patch(Rectangle((xi * 1e3, yb * 1e3), (xo - xi) * 1e3, (yt - yb) * 1e3, fill=False, lw=0.8, ec="#52514e"))
    order = rep["order"]
    for t in coil["turnsDescription"]:
        k = order.index(t["winding"])
        x, y = t["coordinates"][0] * 1e3, t["coordinates"][1] * 1e3
        r = t["dimensions"][0] * 1e3 / 2
        ax.add_patch(Circle((x, y), r * 0.92, color=COLORS[k % len(COLORS)], lw=0))
    for s in coil["sectionsDescription"]:
        if s["type"] == "insulation":
            x = (s["coordinates"][0] - s["dimensions"][0] / 2) * 1e3
            ax.add_patch(Rectangle((x, yb * 1e3), s["dimensions"][0] * 1e3, (yt - yb) * 1e3, color="#d8d5c8", lw=0))
        elif s.get("margin") and max(s["margin"]) > 0:
            x = (s["coordinates"][0] - s["dimensions"][0] / 2) * 1e3
            for (y0, h) in ((yb, s["margin"][0]), (yt - s["margin"][1], s["margin"][1])):
                ax.add_patch(Rectangle((x, y0 * 1e3), s["dimensions"][0] * 1e3, h * 1e3, color="#efe7a8", lw=0))
    # labels: one per winding at its first turn's radius, above the window
    seen = {}
    for t in coil["turnsDescription"]:
        seen.setdefault(t["winding"], t["coordinates"][0] * 1e3)
    for i, (w, x) in enumerate(seen.items()):
        ax.text(x, yt * 1e3 + 0.35 + 0.75 * (i % 2), w, rotation=90, ha="center", va="bottom", fontsize=6.5, color="#0b0b0b")
    ax.set_xlim(xi * 1e3 - 0.2, xo * 1e3 + 0.2)
    ax.set_ylim(yb * 1e3 - 0.3, yt * 1e3 + 2.6)
    ax.set_aspect("equal")
    ax.set_xlabel("radius from core centre (mm)", fontsize=7)
    ax.set_ylabel("axial position (mm)", fontsize=7)
    ax.tick_params(labelsize=6)
    ax.set_title(name, fontsize=8)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def crossreg_png(names, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 3, figsize=(8.4, 4.6), dpi=100)
    data = {n: load(n)[1] for n in names}
    for ax, rail in zip(axes.flat, RAILS):
        for i, n in enumerate(names):
            res = data[n]
            if "nom" not in res:
                continue
            vals = [r[rail] for k, r in res.items() if k != "nom325"]
            lo, hi = min(vals), max(vals)
            ax.plot([i, i], [lo, hi], color=COLORS[i], lw=6, solid_capstyle="round")
            ax.plot([i], [res["nom"][rail]], "o", ms=5, color="#0b0b0b")
        ax.set_title(dn(rail) + " (V, magnitude)", fontsize=8)
        ax.set_xticks(range(len(names)))
        ax.set_xticklabels([n.replace("_", "\n") for n in names], fontsize=5.5)
        ax.tick_params(axis="y", labelsize=6.5)
        ax.grid(axis="y", color="#e6e4dc", lw=0.6)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    fig.suptitle("Rail voltage range over all load cases at 400 V (bar), nominal case (dot)", fontsize=9)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main(names):
    lines = ["# Flyback TR1 options – simulation results", "",
             "Generated by `python3 simulation/flyback/run_flyback.py --report` "
             "(OpenMagnetics 1.7.41 inductance matrix, ngspice 47 transient). Voltages are rail magnitudes in V.", ""]
    summary = []
    for n in names:
        p = os.path.join(OUT, "om", f"{n}.json")
        if not os.path.exists(p):
            continue
        om, res = load(n)
        lk = leakage_table(om)
        g = om["geometry"]
        lines += [f"## {n}", "", opts.get(n)["title"], "",
                  f"Gap {om['gap'] * 1e3:.3f} mm, Lp {om['L'][0][0] * 1e6 if om['names'][0] == 'P' else effective(om)[0][0][0] * 1e6:.1f} uH, "
                  f"radial build {g['radial_build_mm']:.2f} of {g['window_radial_mm']:.2f} mm "
                  f"({'fits' if g['fits'] else 'DOES NOT FIT'}).", "",
                  "Short-circuit (leakage) inductance between the effective windings, referred to the 52 T primary, uH (OpenMagnetics):", "",
                  "| | " + " | ".join(EFFECTIVE) + " |", "|---" * (len(EFFECTIVE) + 1) + "|"]
        for i, a in enumerate(EFFECTIVE):
            lines.append(f"| {a} | " + " | ".join(f"{lk[i][j] * 1e6:.1f}" for j in range(len(EFFECTIVE))) + " |")
        lines += ["", "DC resistance at 60 degC (OpenMagnetics): " +
                  ", ".join(f"{a} {r:.3f} ohm" for a, r in zip(om["names"], om["Rdc"])), ""]
        if res:
            lines += ["| case | " + " | ".join(dn(x) for x in RAILS) + " | Vcol pk | u | f kHz | Pin W |",
                      "|---" * (len(RAILS) + 5) + "|"]
            for c in rf.cases():
                r = res.get(c["name"])
                if not r:
                    continue
                lines.append(f"| {dc(c['name'])} | " + " | ".join(f"{r[x]:.2f}" for x in RAILS) +
                             f" | {r['vcol']:.0f} | {r['u']:.3f} | {r['fsw'] / 1e3:.1f} | {r['pin']:.2f} |")
            lines.append("")
        row = {"name": n, "lk_P": {e: lk[0][i] * 1e6 for i, e in enumerate(EFFECTIVE)},
               "lk_A5": {e: lk[2][i] * 1e6 for i, e in enumerate(EFFECTIVE)}, "res": res, "om": om}
        summary.append(row)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "report.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    # committed summary
    s = ["# TR1 options – summary tables", "",
         "Generated by `run_flyback.py --report`. Leakage: OpenMagnetics; rail voltages: ngspice. "
         "Full tables per case: `out/report.md` (not committed). Calibrated model (2026-11-16): "
         "15V fixed load 9.5 mA + AUX_MEAS divider, iW1819-type multi-mode light-load control, ES1D rectifiers; "
         "16 load cases at 400 V (incl. `idle`, the calibration point) + nom325.", "",
         "## Leakage inductance referred to the 52 T primary (uH)", "",
         "| option | P–A5 | P–S15 | P–S5 | P–SN5 | P–SHV | A5–S15 | A5–S5 | A5–SN5 | A5–SHV | build mm |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in summary:
        s.append(f"| {r['name']} | " + " | ".join(f"{r['lk_P'][e]:.1f}" for e in ("A5", "S15", "S5", "SN5", "SHV")) + " | " +
                 " | ".join(f"{r['lk_A5'][e]:.1f}" for e in ("S15", "S5", "SN5", "SHV")) +
                 f" | {r['om']['geometry']['radial_build_mm']:.2f} |")
    s += ["", "## Rail voltage, nominal case and min–max over the load cases at 400 V (V, magnitude)", "",
          "| option | " + " | ".join(dn(x) for x in RAILS) + " | Vcol max |", "|---" * (len(RAILS) + 2) + "|"]
    for r in summary:
        res = r["res"]
        if "nom" not in res:
            continue
        cells = []
        for x in RAILS:
            lo, hi = spread(res, x)
            cells.append(f"{res['nom'][x]:.2f} ({lo:.2f}–{hi:.2f})")
        vmax = max(v["vcol"] for k, v in res.items())
        s.append(f"| {r['name']} | " + " | ".join(cells) + f" | {vmax:.0f} |")
    s += ["", "## Limits and targets", "",
          "15V (primary gate rail, Proteus 20V): AUX_MEAS = 0.176 x V(15V) (R11 22k / R12 4.7k) feeds a 3.3 V ADC, "
          "so V(15V) must stay below 18.7 V in every case. Targets: 15 V for both gate rails, 5 V for the 5 V rails, 80 V bias.", "",
          "| option | 15V max (≤ 18.7 V) | 15V idle (measured 15.5 V on the current build) | 15V_ISO_SEC min–max (target 15) | 5V max | 5V_ISOL min–max | -5V min–max | -100V BIAS min–max |",
          "|---|---|---|---|---|---|---|---|"]
    for r in summary:
        res = r["res"]
        if "nom" not in res:
            continue
        v20 = max(v["20V"] for v in res.values())
        flag = "OK" if v20 <= 18.7 else "**EXCEEDS**"
        def mm(x):
            lo, hi = spread(res, x, exclude=())
            return f"{lo:.2f}–{hi:.2f}"
        idle = f"{res['idle']['20V']:.2f}" if "idle" in res else "–"
        s.append(f"| {r['name']} | {v20:.2f} {flag} | {idle} | {mm('20V_ISO_SEC')} | {max(v['5V'] for v in res.values()):.2f} | "
                 f"{mm('5V_ISOL')} | {mm('-5V_SEC')} | {mm('-100V BIAS')} |")
    s += ["", "## Rectifier peak reverse voltage, max over the load cases at 400 V (V, 50 ns filtered; ES1D = 200 V)", "",
          "| option | D5 (15V) | D6 (5V) | D4 (15V_ISO_SEC) | D29 (5V_ISOL) | D14 (-5V_SEC) | D8 (-100V BIAS) | Vcol max | snubber R45 W (nom) |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in summary:
        res = r["res"]
        if "nom" not in res:
            continue
        def vr(x):
            v = [c.get(x + " vrev") for k, c in res.items() if k != "nom325" and c.get(x + " vrev") is not None]
            return f"{max(v):.0f}" + (" **> 200**" if max(v) > 200 else "") if v else "–"
        s.append(f"| {r['name']} | " + " | ".join(vr(x) for x in RAILS) +
                 f" | {max(v['vcol'] for v in res.values()):.0f} | {res['nom']['pr45']:.3f} |")
    s += ["", "## Spread (max − min over the load cases at 400 V), V", "",
          "| option | " + " | ".join(dn(x) for x in RAILS) + " |", "|---" * (len(RAILS) + 1) + "|"]
    for r in summary:
        res = r["res"]
        if "nom" not in res:
            continue
        s.append(f"| {r['name']} | " + " | ".join(f"{spread(res, x)[1] - spread(res, x)[0]:.2f}" for x in RAILS) + " |")
    with open(os.path.join(HERE, "results.md"), "w") as f:
        f.write("\n".join(s) + "\n")
    for r in summary:
        geometry_png(r["name"], os.path.join(HERE, f"geometry_{r['name']}.png"))
    done = [r["name"] for r in summary if "nom" in r["res"]]
    if done:
        crossreg_png(done, os.path.join(HERE, "crossreg.png"))
    print("\n".join(s))
