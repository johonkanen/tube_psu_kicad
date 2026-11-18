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


# Full-load cases for the EEL19 transformer (2026-11-17), run only for options with
# "full_cases" (or when named with --cases). full10 = every rail at its table 1.1 maximum at
# once (10.9 W incl. bleeders / fixed loads); full15 = the 15 W rating proposed in
# EEL19_DESIGN.md (15 V rails 0.3 A, 5 V rails 0.3 A, -5 V 0.2 A, -80 V 20 mA total);
# full15_325 = the same before the PFC runs.
FULL10 = dict(TABLE_MAX)
FULL15 = {"20V": 0.3, "5V": 0.3, "20V_ISO_SEC": 0.3, "5V_ISOL": 0.3, "-5V_SEC": 0.2, "-100V BIAS": 0.0134}
FULL_CASES = [
    {"name": "full10", "loads": dict(FULL10), "title": "every rail at its table 1.1 maximum (about 10.9 W)"},
    {"name": "full15", "loads": dict(FULL15), "title": "15 W rating: 15 V rails 0.3 A, 5 V rails 0.3 A, -5 V 0.2 A, -80 V 20 mA"},
    {"name": "full15_325", "loads": dict(FULL15), "vin": 325.0, "title": "full15 at DC+ = 325 V"},
]


# Wide input range (2026-11-18, EEL19_DESIGN.md section 14, ICE5AR0680AG): 20 W = the full15
# pattern scaled by 1.37 (15 V rails 0.41 A, 5 V rails 0.41 A, -5 V 0.27 A, -80 V 18.2 mA on top of
# the bleeder; with the preloads, bleeders and fixed loads 20.1 W), at 100 / 200 / 400 / 450 V DC+;
# full20_100_csmin = full20_100 with the minimum current limit VCS_N 0.72 V; nom100 / nom450 =
# nominal loads at the input extremes; full15_100 = 15 W at 100 V. Run for options with "wide_cases".
FULL20 = {"20V": 0.41, "5V": 0.41, "20V_ISO_SEC": 0.41, "5V_ISOL": 0.41, "-5V_SEC": 0.27, "-100V BIAS": 0.0182}
WIDE_CASES = [
    {"name": "full20", "loads": dict(FULL20), "title": "20 W at 400 V"},
    {"name": "full20_100", "loads": dict(FULL20), "vin": 100.0, "title": "20 W at DC+ = 100 V"},
    {"name": "full20_200", "loads": dict(FULL20), "vin": 200.0, "title": "20 W at DC+ = 200 V"},
    {"name": "full20_450", "loads": dict(FULL20), "vin": 450.0, "title": "20 W at DC+ = 450 V"},
    {"name": "full20_100_csmin", "loads": dict(FULL20), "vin": 100.0, "ice": {"vcs_n": 0.72},
     "title": "20 W at 100 V with the minimum current limit VCS_N 0.72 V"},
    {"name": "full15_100", "loads": dict(FULL15), "vin": 100.0, "title": "15 W at DC+ = 100 V"},
    {"name": "nom100", "loads": dict(NOM), "vin": 100.0, "title": "nominal at DC+ = 100 V"},
    {"name": "nom450", "loads": dict(NOM), "vin": 450.0, "title": "nominal at DC+ = 450 V"},
    # switch-loss bound with a 2 ns gate RC (the 10 ns model RC overstates the turn-off overlap)
    {"name": "full20_100_fast", "loads": dict(FULL20), "vin": 100.0, "ice": {"tgate": 2e-9},
     "title": "full20_100 with a 2 ns gate RC"},
    {"name": "full20_450_fast", "loads": dict(FULL20), "vin": 450.0, "ice": {"tgate": 2e-9},
     "title": "full20_450 with a 2 ns gate RC"},
]


def all_cases():
    return cases() + FULL_CASES + WIDE_CASES


def option_cases(opt, names=None):
    """Load cases of one option: the 16 standard cases, plus FULL_CASES when the option asks
    for them (and WIDE_CASES for "wide_cases"); `names` (from --cases) selects from all of them."""
    if names:
        pool = all_cases()
    else:
        pool = cases() + (FULL_CASES if opt.get("full_cases") else []) + (WIDE_CASES if opt.get("wide_cases") else [])
    return [c for c in pool if not names or c["name"] in names]


def om_analysis(name: str, force=False) -> dict:
    import om_model as m
    os.makedirs(os.path.join(OUT, "om"), exist_ok=True)
    path = os.path.join(OUT, "om", f"{name}.json")
    if os.path.exists(path) and not force:
        with open(path) as f:
            return json.load(f)
    opt = opts.get(name)
    if opt.get("om_from"):
        # same windings as another option (e.g. the ICE5AR controller variants): reuse its MKF result
        res = om_analysis(opt["om_from"], force=force)
        with open(path, "w") as f:
            json.dump(dict(res, name=name), f, indent=1)
        return res
    t = time.time()
    res = m.analyse(opt)
    mag = res.pop("magnetic")
    res["om_seconds"] = time.time() - t
    with open(path, "w") as f:
        json.dump(res, f, indent=1)
    if opt.get("write_mas"):
        os.makedirs(MAS_DIR, exist_ok=True)
        lmag = res["L"][0][0]
        if opt.get("core"):        # EEL19: the whole (split) primary, as the LCR meter reads it
            pn = [i for i, a in enumerate(res["names"]) if a in ("P", "P1", "P2")]
            lmag = sum(res["L"][i][j] for i in pn for j in pn)
        doc = {"inputs": {"designRequirements": {
                   "name": f"TR1 {name}",
                   "magnetizingInductance": {"nominal": lmag},
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
    if opt.get("controller") == "ice5ar":
        return run_case_ice(name, opt, res, case, path, vin, ic)
    pout = fs.expected_pout(case)
    if opt.get("rsense"):
        # EEL19 options: own sense resistor and knee threshold; u0 from the total primary
        # inductance, PI gain scaled so the loop gain (kp * Pmax / P) matches the EF20 model
        case["rsense"] = opt["rsense"]
        case["knee_at"] = opt.get("knee_at", fs.KNEE_AT)
        names_ = res["names"]
        lp = sum(res["L"][i][j] for i, a in enumerate(names_) for j, b in enumerate(names_)
                 if a in ("P", "P1", "P2") and b in ("P", "P1", "P2"))
        pmax = 0.5 * lp * (1.0 / opt["rsense"]) ** 2 * fs.FMAX
        pref = 0.5 * 462e-6 * fs.IMAX ** 2 * fs.FMAX          # EF20 model: 10.7 W
        case["u0"] = min(1.0, max(0.01, pout / 0.85 / pmax))
        kp = 2.0 * min(3.0, max(0.05, pout / 5.0)) * pref / pmax
        case["kp"], case["ki"] = kp, 1000.0 * kp
    else:
        pmax = 0.5 * res["L"][0][0] * fs.IMAX ** 2 * fs.FMAX
        case["u0"] = min(1.0, max(0.01, pout / 0.75 / pmax))
        case["kp"], case["ki"] = fs.pi_gains(case)
    wave = os.path.join(OUT, "spice", f"{name}__{case['name']}_wave.txt") if case["name"] in ("nom", "max_S15", "full10", "full15") else None
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


def run_case_ice(name, opt, res, case, path, vin, ic):
    """One load case with the ICE5AR4780BZS model (ice5ar_sim.py). The FB compensation
    capacitors and the ABM entry blanking time are scaled with the output capacitors (cscale
    0.1), so the loop keeps its shape and the cases settle in the same 9-40 ms runs; the
    DC levels do not depend on either."""
    import ice5ar_sim as ice
    # batch runs: the slower FB network ice.BATCH_COMP (R1/C1/C2 only; same RSel, divider and ABM
    # option, hence the same DC gain and levels), scaled with the output capacitors. The schematic
    # network (R140 4.7k + C138 10n, C139 2.2n) scaled by 0.1 puts the loop crossover near the
    # switching frequency and limit-cycles; it is verified with the real capacitors in ice5ar_checks.py.
    case["comp"] = {**(opt.get("comp") or {}), **ice.BATCH_COMP}
    # power-stage variant (ICE5AR0680AG: RDS(on), Co(er)) and sense resistor of the option; a
    # case's own "ice" entries (e.g. the minimum current limit) override the option's
    if opt.get("ice") or case.get("ice"):
        case["ice"] = {**(opt.get("ice") or {}), **(case.get("ice") or {})}
    if opt.get("rcs"):
        case["rcs"] = opt["rcs"]
    n = case["name"]
    wave = os.path.join(OUT, "spice", f"{name}__{n}_wave.txt") if (n in ("nom", "max_S15", "full10", "full15")
                                                                    or n.startswith("full20")) else None
    net = ice.netlist(res, opt["spice"], case, vin=vin,
                      tstop=case.get("tstop", 40e-3 if n == "idle" else 20e-3 if n == "light" else 12e-3 if n.startswith("min") else 9e-3),
                      twin=case.get("twin", 10e-3 if n == "idle" else 5e-3 if n == "light" else 1.5e-3),
                      wave_file=wave, ic=ic)
    t = time.time()
    vals = fs.run(net, f"{name}__{n}")
    r = ice.summarise(vals)
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
    if "abm" in r:          # ICE5AR model
        print(f"  {n:>12} {c:>8}: " + " ".join(f"{SHORT[k]}={r[k]:.3f}" for k in fs.RAILS if r.get(k) is not None)
              + f" Vds={r['vcol']:.0f} FB={r['fb']:.2f} f={r['fsw'] / 1e3:.0f}k ABM={r['abm']:.2f} Pin={r['pin']:.2f}"
              f" drift20={r['20V drift'] * 1e3:.0f}mV ({r['seconds']:.0f}s)", flush=True)
        return
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
    sel_of = {n: option_cases(opts.get(n), a.cases) for n in names}
    pool = Pool(a.jobs)
    t0 = time.time()
    try:
        # pass 1: the nominal case of every option (its rail voltages are the initial
        # conditions of that option's other cases); pass 2: all other cases, longest first
        noms = [(n, om[n], c, a.force, None) for n in names for c in sel_of[n] if c["name"] == "nom"]
        for (n, _, c, _, _), r in zip(noms, pool.map(run_case, noms)):
            show(n, c["name"], r)
        ics = {}
        for n in names:
            p = os.path.join(OUT, "results", f"{n}__nom.json")
            if os.path.exists(p):
                with open(p) as f:
                    r = json.load(f)
                ics[n] = {k: r[k] for k in fs.RAILS if r.get(k)}
        rest = [(n, om[n], c, a.force, ics.get(n)) for n in names for c in sel_of[n] if c["name"] != "nom"]
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
