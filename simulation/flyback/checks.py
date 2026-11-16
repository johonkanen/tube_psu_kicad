#!/usr/bin/env python3
"""Single-run checks (one ngspice at a time), results in out/checks/<name>.json:

    python3 simulation/flyback/checks.py cscale     # current nom with unscaled capacitors (cscale = 1, 30 ms)
    python3 simulation/flyback/checks.py d8bv200    # current nom with D8 breaking down at 200 V (ES1D rating)
"""
from __future__ import annotations

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import flyback_sim as fs  # noqa: E402
import options as opts  # noqa: E402
import run_flyback as rf  # noqa: E402

CHECKS = {
    "cscale": dict(option="current", case="nom", cscale=1.0, tstop=30e-3),
    "d8bv200": dict(option="current", case="nom", bv={"-100V BIAS": 200.0}, tstop=12e-3),
}


def main(names):
    os.makedirs(os.path.join(fs.OUT, "checks"), exist_ok=True)
    for n in names:
        cfg = CHECKS[n]
        res = rf.om_analysis(cfg["option"])
        opt = opts.get(cfg["option"])
        case = dict(next(c for c in rf.cases() if c["name"] == cfg["case"]))
        case["name"] = f"{cfg['case']}_{n}"
        if "bv" in cfg:
            case["bv"] = cfg["bv"]
        pout = fs.expected_pout(case)
        case["u0"] = min(1.0, pout / 0.75 / (0.5 * res["L"][0][0] * fs.IMAX ** 2 * fs.FMAX))
        case["kp"], case["ki"] = fs.pi_gains(case)
        net = fs.netlist(res, opt["spice"], case, cscale=cfg.get("cscale", 0.1), tstop=cfg["tstop"], twin=1.5e-3)
        t = time.time()
        r = fs.summarise(fs.run(net, f"check_{n}"))
        r["seconds"] = time.time() - t
        r["case"] = case
        r["config"] = {k: v for k, v in cfg.items()}
        with open(os.path.join(fs.OUT, "checks", f"{n}.json"), "w") as f:
            json.dump(r, f, indent=1)
        print(f"{n}: " + " ".join(f"{rf.SHORT[k]}={r[k]:.3f}({r[k + ' drift'] * 1e3:+.0f}mV)" for k in fs.RAILS)
              + f" pin={r['pin']:.2f} W VrD8={r['-100V BIAS vrev']:.0f} V ({r['seconds']:.0f}s)", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:] or list(CHECKS))
