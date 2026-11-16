#!/usr/bin/env python3
"""Run the TR1 winding options through OpenMagnetics and the ngspice flyback model.

    python3 simulation/flyback/run_flyback.py                    # all options, all cases
    python3 simulation/flyback/run_flyback.py current            # one option
    python3 simulation/flyback/run_flyback.py current --cases nom light
    python3 simulation/flyback/run_flyback.py --om-only          # magnetics only (fast)
    python3 simulation/flyback/run_flyback.py --report           # tables + plots from cached results

ngspice runs in a pool (--jobs, default 8, total RAM budget 3 GB). Results are cached per option/case in
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
    c.append({"name": "light", "loads": {r: 0.0 for r in NOM}, "title": "all rails bleeder only (+ 15V fixed load, AUX_MEAS)"})
    # calibration point: the board idling (measured 15V = 15.5 V, user 2026-11-16). Estimated
    # idle loads: 5V = MCU board on J2 + Si827x input sides (0.02-0.1 A, 0.05 A used),
    # 15V_ISO_SEC = DRV6 VDDB 2 mA, 5V_ISOL = DRV6 VDDI + AD2 LDO/ADC/op-amps 5 mA
    c.append({"name": "idle", "loads": {**{r: 0.0 for r in NOM}, "5V": 0.05, "20V_ISO_SEC": 0.002, "5V_ISOL": 0.005},
              "title": "board idle (calibration point, measured 15V 15.5 V)"})
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
    case = dict(case)
    if opt.get("preload"):
        case["preload"] = opt["preload"]
    pout = fs.expected_pout(case)
    pmax = 0.5 * res["L"][0][0] * fs.IMAX ** 2 * fs.FMAX
    case["u0"] = min(1.0, max(0.01, pout / 0.75 / pmax))
    case["kp"], case["ki"] = fs.pi_gains(case)
    wave = os.path.join(OUT, "spice", f"{name}__{case['name']}_wave.txt") if case["name"] in ("nom", "max_S15") else None
    net = fs.netlist(res, opt["spice"], case, vin=vin, tstop=case.get("tstop", 40e-3 if case["name"] == "idle" else 20e-3 if case["name"] == "light" else 12e-3 if case["name"].startswith("min") else 9e-3),
                     # idle / light hunt slowly between the light-load modes (limit cycle of
                     # +-0.5 V on 15V at idle): average over a long window, as a DMM would
                     twin=case.get("twin", 10e-3 if case["name"] == "idle" else 5e-3 if case["name"] == "light" else 1.5e-3),
                     wave_file=wave, ic=ic)
    t = time.time()
    vals = fs.run(net, f"{name}__{case['name']}")
    r = fs.summarise(vals)
    r["seconds"] = time.time() - t
    r["case"] = case
    with open(path, "w") as f:
        json.dump(r, f, indent=1)
    return r


RAM_BUDGET = 3.0e9          # total for all simulations (user rule, 2026-11-16)
RAM_PER_RUN = 0.25e9        # assumed per ngspice run before it is seen (idle/light ~0.2-0.3 GB, others ~0.1 GB)


def ngspice_rss() -> float:
    """Total resident memory of all ngspice processes (bytes), from /proc."""
    tot = 0
    for d in os.listdir("/proc"):
        if not d.isdigit():
            continue
        try:
            with open(f"/proc/{d}/comm") as f:
                if f.read().strip() != "ngspice":
                    continue
            with open(f"/proc/{d}/statm") as f:
                tot += int(f.read().split()[1]) * os.sysconf("SC_PAGE_SIZE")
        except OSError:
            pass
    return tot


class Pool:
    """Up to `jobs` ngspice runs at once (threads, each starting its own ngspice subprocess
    and parsing only its own log). A new run starts only while the measured ngspice memory
    plus RAM_PER_RUN for each started-but-unseen run stays below RAM_BUDGET; peak memory and
    wall time are recorded."""

    def __init__(self, jobs):
        import threading
        self.jobs = max(1, jobs)
        self.lock = threading.Lock()
        self.starting = 0
        self.peak = 0.0
        self.stop = threading.Event()
        self.mon = threading.Thread(target=self._monitor, daemon=True)
        self.mon.start()

    def _monitor(self):
        while not self.stop.wait(0.5):
            self.peak = max(self.peak, ngspice_rss())

    def admit(self):
        while True:
            with self.lock:
                if ngspice_rss() + (self.starting + 1) * RAM_PER_RUN <= RAM_BUDGET:
                    self.starting += 1
                    return
            time.sleep(1.0)

    def started(self):
        with self.lock:
            self.starting = max(0, self.starting - 1)

    def map(self, fn, tasks):
        from concurrent.futures import ThreadPoolExecutor

        def wrap(t):
            self.admit()
            import threading
            threading.Timer(3.0, self.started).start()   # ngspice has allocated by then
            return fn(*t)
        with ThreadPoolExecutor(max_workers=self.jobs) as ex:
            return list(ex.map(wrap, tasks))         # results in task order (deterministic)

    def close(self):
        self.stop.set()


def show(n, c, r):
    print(f"  {n:>12} {c:>8}: " + " ".join(f"{SHORT[k]}={r[k]:.3f}" for k in fs.RAILS if r.get(k) is not None)
          + f" Vcol={r['vcol']:.0f} VrD8={r['-100V BIAS vrev']:.0f} u={r['u']:.3f} drift20={r['20V drift'] * 1e3:.0f}mV ({r['seconds']:.0f}s)", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("options", nargs="*")
    ap.add_argument("--cases", nargs="*")
    ap.add_argument("--om-only", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--jobs", type=int, default=8, help="parallel ngspice runs (default 8, RAM budget 3 GB)")
    a = ap.parse_args(argv)
    names = a.options or list(opts.OPTIONS)
    if a.report:
        import report
        report.main(names)
        return 0
    om = {}
    for n in names:
        res = om_analysis(n, force=a.force)
        om[n] = res
        print(f"[om] {n}: gap {res['gap'] * 1e3:.3f} mm, Lp {res['L'][0][0] * 1e6:.1f} uH, "
              f"build {res['geometry']['radial_build_mm']:.2f}/{res['geometry']['window_radial_mm']:.2f} mm", flush=True)
    if a.om_only:
        return 0
    sel = [c for c in cases() if not a.cases or c["name"] in a.cases]
    pool = Pool(a.jobs)
    t0 = time.time()
    try:
        # pass 1: the nominal case of every option (its rail voltages are the initial
        # conditions of that option's other cases); pass 2: all other cases, longest first
        noms = [(n, om[n], c, a.force, None) for n in names for c in sel if c["name"] == "nom"]
        for (n, _, c, _, _), r in zip(noms, pool.map(run_case, noms)):
            show(n, c["name"], r)
        ics = {}
        for n in names:
            p = os.path.join(OUT, "results", f"{n}__nom.json")
            if os.path.exists(p):
                with open(p) as f:
                    r = json.load(f)
                ics[n] = {k: r[k] for k in fs.RAILS if r.get(k)}
        rest = [(n, om[n], c, a.force, ics.get(n)) for n in names for c in sel if c["name"] != "nom"]
        weight = {"idle": 0, "light": 1}
        order = sorted(range(len(rest)), key=lambda i: (weight.get(rest[i][2]["name"], 2 if rest[i][2]["name"].startswith("min") else 3), i))
        out = pool.map(run_case, [rest[i] for i in order])
        res_by = {order[k]: out[k] for k in range(len(order))}
        for i, (n, _, c, _, _) in enumerate(rest):
            show(n, c["name"], res_by[i])
    finally:
        pool.close()
    print(f"[pool] {len(noms) + len(rest)} cases, jobs {a.jobs}, wall {time.time() - t0:.0f} s, "
          f"peak ngspice memory {pool.peak / 1e6:.0f} MB", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
