#!/usr/bin/env python3
"""Run the TR1 winding options through OpenMagnetics and the ngspice flyback model.

    python3 simulation/flyback/run_flyback.py                    # all options, all cases
    python3 simulation/flyback/run_flyback.py current            # one option
    python3 simulation/flyback/run_flyback.py current --cases nom light
    python3 simulation/flyback/run_flyback.py --om-only          # magnetics only (fast)
    python3 simulation/flyback/run_flyback.py --report           # tables + plots from cached results

ngspice runs one at a time (memory rule). Results are cached per option/case in
out/results/ (delete a file to rerun it); the OpenMagnetics analysis in out/om/.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import flyback_sim as fs  # noqa: E402
import options as opts  # noqa: E402

OUT = os.path.join(HERE, "out")
MAS_DIR = os.path.join(HERE, "mas")

# loads in A on top of the bleeders (assumed, from design doc table 1.1: max 0.2 A on each
# 5 V / 15 V rail, -80 V 10 mA). "nominal" = half of the table on the low-voltage rails and
# -80 V at 10 mA total (6.6 mA bleeder + 3.4 mA).
TABLE_MAX = {"20V": 0.2, "5V": 0.2, "20V_ISO_SEC": 0.2, "5V_ISOL": 0.2, "-5V_SEC": 0.2, "-100V BIAS": 0.0134}
NOM = {"20V": 0.1, "5V": 0.1, "20V_ISO_SEC": 0.1, "5V_ISOL": 0.1, "-5V_SEC": 0.1, "-100V BIAS": 0.0034}
SHORT = {"20V": "20V", "5V": "5V", "20V_ISO_SEC": "S15", "5V_ISOL": "S5", "-5V_SEC": "SN5", "-100V BIAS": "SHV"}


def cases():
    c = [{"name": "nom", "loads": dict(NOM), "title": "nominal (half of table 1.1, -80 V 10 mA)"}]
    for r in NOM:
        ld = dict(NOM)
        ld[r] = 0.0
        c.append({"name": f"min_{SHORT[r]}", "loads": ld, "title": f"{r} bleeder only, others nominal"})
    for r in NOM:
        ld = dict(NOM)
        ld[r] = TABLE_MAX[r]
        c.append({"name": f"max_{SHORT[r]}", "loads": ld, "title": f"{r} at table 1.1 maximum, others nominal"})
    c.append({"name": "light", "loads": {r: 0.0 for r in NOM}, "title": "all rails bleeder only (+ IW1818 Vcc)"})
    c.append({"name": "nom325", "loads": dict(NOM), "vin": 325.0, "title": "nominal at DC+ = 325 V (PFC not running)"})
    return c


def om_analysis(name: str, force=False) -> dict:
    import om_model as m
    os.makedirs(os.path.join(OUT, "om"), exist_ok=True)
    path = os.path.join(OUT, "om", f"{name}.json")
    if os.path.exists(path) and not force:
        with open(path) as f:
            return json.load(f)
    opt = opts.get(name)
    t = time.time()
    res = m.analyse(opt)
    mag = res.pop("magnetic")
    res["om_seconds"] = time.time() - t
    with open(path, "w") as f:
        json.dump(res, f, indent=1)
    if opt.get("write_mas"):
        os.makedirs(MAS_DIR, exist_ok=True)
        doc = {"inputs": {"designRequirements": {
                   "name": f"TR1 {name}",
                   "magnetizingInductance": {"nominal": res["L"][0][0]},
                   "turnsRatios": [{"nominal": res["turns"][0] / n} for n in res["turns"][1:]],
                   "isolationSides": sorted({w["isolationSide"] for w in mag["coil"]["functionalDescription"]}),
                   "insulation": {"insulationType": "Reinforced", "pollutionDegree": "P2",
                                  "overvoltageCategory": "OVC-II", "cti": "Group IIIA",
                                  "altitude": {"maximum": 2000},
                                  "mainSupplyVoltage": {"nominal": 230, "maximum": 264},
                                  "standards": ["IEC 62368-1"]}},
                   "operatingPoints": []},
               "magnetic": mag,
               "outputs": [{"inductance": {"inductanceMatrix": [{"frequency": 72e3, "magnitude": {
                   a: {b: {"nominal": res["L"][i][j]} for j, b in enumerate(res["names"])}
                   for i, a in enumerate(res["names"])}}]}}],
               "_note": opt["title"] + " | written by simulation/flyback/run_flyback.py"}
        mag["manufacturerInfo"] = {"name": "tube_power_5_1", "reference": f"TR1 {name}"}
        with open(os.path.join(MAS_DIR, f"tr1_{name}.json"), "w") as f:
            json.dump(doc, f, indent=1)
    return res


def run_case(name: str, res: dict, case: dict, force=False, ic=None) -> dict:
    os.makedirs(os.path.join(OUT, "results"), exist_ok=True)
    path = os.path.join(OUT, "results", f"{name}__{case['name']}.json")
    if os.path.exists(path) and not force:
        with open(path) as f:
            return json.load(f)
    opt = opts.get(name)
    vin = case.get("vin", 400.0)
    # initial integrator state from the expected power (speeds up settling)
    pout = sum(case["loads"][r] * fs.NOMINAL_V[r] for r in case["loads"]) + 0.075 + 4 * 0.4e-3 * 5 + 80 ** 2 / 12.1e3
    pmax = 0.5 * res["L"][0][0] * fs.IMAX ** 2 * fs.FMAX
    case = dict(case)
    case["u0"] = min(1.0, max(0.02, pout / 0.75 / pmax))
    wave = os.path.join(OUT, "spice", f"{name}__{case['name']}_wave.txt") if case["name"] in ("nom", "max_S15") else None
    net = fs.netlist(res, opt["spice"], case, vin=vin, tstop=case.get("tstop", 9e-3), twin=1.5e-3,
                     wave_file=wave, ic=ic)
    t = time.time()
    vals = fs.run(net, f"{name}__{case['name']}")
    r = fs.summarise(vals)
    r["seconds"] = time.time() - t
    r["case"] = case
    with open(path, "w") as f:
        json.dump(r, f, indent=1)
    return r


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("options", nargs="*")
    ap.add_argument("--cases", nargs="*")
    ap.add_argument("--om-only", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args(argv)
    names = a.options or list(opts.OPTIONS)
    if a.report:
        import report
        report.main(names)
        return 0
    for n in names:
        res = om_analysis(n, force=a.force)
        print(f"[om] {n}: gap {res['gap'] * 1e3:.3f} mm, Lp {res['L'][0][0] * 1e6:.1f} uH, "
              f"build {res['geometry']['radial_build_mm']:.2f}/{res['geometry']['window_radial_mm']:.2f} mm", flush=True)
        if a.om_only:
            continue
        ic = None
        for c in cases():
            if a.cases and c["name"] not in a.cases:
                continue
            r = run_case(n, res, c, force=a.force, ic=ic)
            if c["name"] == "nom":
                ic = {k: r[k] for k in fs.RAILS if r.get(k)}
            print(f"  {n:>12} {c['name']:>8}: " + " ".join(f"{SHORT[k]}={r[k]:.3f}" for k in fs.RAILS if r.get(k) is not None)
                  + f" Vcol={r['vcol']:.0f} u={r['u']:.3f} drift5={r['5V drift'] * 1e3:.0f}mV ({r['seconds']:.0f}s)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
