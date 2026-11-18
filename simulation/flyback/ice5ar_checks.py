#!/usr/bin/env python3
"""Single-run checks of the ICE5AR4780BZS model with the real (unscaled) output capacitors and
the real FB compensation network; results in out/checks/ice_<name>.json, slow waveforms in
out/checks/ice_<name>.txt (columns: t, then (t, value) pairs of 5V, 15V, 15V_ISO_SEC, 5V_ISOL,
-5V, -80V, FB, ABM, enable).

    python3 simulation/flyback/ice5ar_checks.py step        # nom, 5V load step 0.1 -> 0.2 -> 0.1 A
    python3 simulation/flyback/ice5ar_checks.py light idle  # burst-mode ripple with real capacitors
    python3 simulation/flyback/ice5ar_checks.py --list
    python3 simulation/flyback/ice5ar_checks.py step --jobs 2

Options: --comp r1=..,c1=..,c2=..,rsel=..,abm=..  (overrides ice5ar_sim.COMP for this run; the
tag gets a suffix), --option <name> (default eel19_tiw_sandwich_s_pre3_ice).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import flyback_sim as fs  # noqa: E402
import ice5ar_sim as ice  # noqa: E402
import options as opts  # noqa: E402
import run_flyback as rf  # noqa: E402

CHECKS = {
    # 5V regulated rail: +0.1 A at 14 ms, back at 24 ms
    "step": dict(case="nom", tstop=34e-3, step={"rail": "5V", "di": 0.1, "t1": 14e-3, "t2": 24e-3}),
    # all rails nom -> full15 -> nom (large step)
    "stepfull": dict(case="nom", tstop=34e-3, stepall=True, t1=14e-3, t2=24e-3),
    # light-load / burst behaviour with the real capacitors (ABM blanking 36 ms is cut to 3 ms)
    "light": dict(case="light", tstop=80e-3, twin=40e-3, t_beb=3e-3),
    "idle": dict(case="idle", tstop=80e-3, twin=40e-3, t_beb=3e-3),
    "min_20V": dict(case="min_20V", tstop=60e-3, twin=30e-3, t_beb=3e-3),
    # start-up from 0 V (VCC at VCC_ON, soft start, real capacitors) against the OLP timer
    "startup": dict(case="nom", tstop=60e-3, twin=5e-3, startup=True),
    "startup_full15": dict(case="full15", tstop=60e-3, twin=5e-3, startup=True),
    "light325": dict(case="light", vin=325.0, tstop=80e-3, twin=40e-3, t_beb=3e-3),
    # wide input range (EEL19_DESIGN.md 14, ICE5AR0680AG options): start-up at DC+ = 100 V against the
    # OLP timer, CCM operation at 100 V with the real capacitors and FB network (cycle-by-cycle
    # peak current from the saved primary current -> subharmonic check), load step at 100 V
    # (save_step: decimated storage, the full-resolution 80 ms start-up needed > 1.7 GB)
    "startup100": dict(case="nom100", tstop=60e-3, twin=5e-3, startup=True, save_step=0.5e-6),
    "startup100_full15": dict(case="full15_100", tstop=70e-3, twin=5e-3, startup=True, save_step=0.5e-6),
    "startup100_full20": dict(case="full20_100", tstop=70e-3, twin=5e-3, startup=True, save_step=0.5e-6),
    "startup100_full20_csmin": dict(case="full20_100_csmin", tstop=80e-3, twin=5e-3, startup=True, save_step=0.5e-6),
    "startup100_full15_csmin": dict(case="full15_100", tstop=70e-3, twin=5e-3, startup=True, save_step=0.5e-6,
                                    ice={"vcs_n": 0.72}),
    "startup450_full20": dict(case="full20_450", tstop=60e-3, twin=5e-3, startup=True, save_step=0.5e-6),
    "ccm100": dict(case="full20_100", tstop=30e-3, twin=2e-3, ipk_wave=True),
    "ccm200": dict(case="full20_200", tstop=30e-3, twin=2e-3, ipk_wave=True),
    "light_lean": dict(case="light", tstop=80e-3, twin=40e-3, t_beb=3e-3, save_step=0.5e-6),
    "step_lean": dict(case="nom", tstop=34e-3, step={"rail": "5V", "di": 0.1, "t1": 14e-3, "t2": 24e-3}, save_step=0.5e-6),
    "step100": dict(case="nom100", tstop=40e-3, stepall=True, t1=14e-3, t2=27e-3, target="FULL20", save_step=0.5e-6),
    "step450": dict(case="nom450", tstop=40e-3, stepall=True, t1=14e-3, t2=27e-3, target="FULL20", save_step=0.5e-6),
}


def parse_comp(s):
    out = {}
    for kv in (s or "").split(","):
        if kv:
            k, v = kv.split("=")
            out[k] = None if v == "none" else (int(v) if k == "abm" else float(v))
    return out


def run_check(n, option, comp, extra_tag=""):
    cfg = CHECKS[n]
    res = rf.om_analysis(option)
    opt = opts.get(option)
    case = dict(next(c for c in rf.all_cases() if c["name"] == cfg["case"]))
    case["loads"] = dict(case["loads"])
    case["preload"] = opt.get("preload")
    case["comp"] = {**(opt.get("comp") or {}), **comp}
    case["comp_scale"] = 1.0
    if opt.get("ice") or case.get("ice") or cfg.get("ice"):   # ICE5AR0680AG options (power stage, Rcs)
        case["ice"] = {**(opt.get("ice") or {}), **(case.get("ice") or {}), **(cfg.get("ice") or {})}
    if opt.get("rcs"):
        case["rcs"] = opt["rcs"]
    vin = cfg.get("vin", case.get("vin", 400.0))
    if "t_beb" in cfg:
        case["t_beb"] = cfg["t_beb"]
    if cfg.get("step"):
        case["step"] = cfg["step"]
    if cfg.get("save_step"):
        case["save_step"] = cfg["save_step"]
    tag = f"ice_{n}{extra_tag}"
    case["name"] = tag
    nom = os.path.join(fs.OUT, "results", f"{option}__nom.json")
    ic = None
    if os.path.exists(nom):
        r0 = json.load(open(nom))
        ic = {k: r0[k] for k in fs.RAILS if r0.get(k)}
    if cfg.get("startup"):
        case["startup"] = True
        case["vfb0"], case["abm0"] = 2.25, 0          # FB after the RSel detection (Isel x 750k)
        ic = {k: 0.0 for k in fs.RAILS}
    os.makedirs(os.path.join(fs.OUT, "checks"), exist_ok=True)
    wave = os.path.join(fs.OUT, "checks", f"{tag}.txt")
    ipkw = os.path.join(fs.OUT, "checks", f"{tag}_ipk.txt") if cfg.get("ipk_wave") else None
    net = ice.netlist(res, opt["spice"], case, cscale=1.0, tstop=cfg["tstop"], twin=cfg.get("twin", 4e-3),
                      vin=vin, ic=ic, save_file=None if ipkw else wave, wave_file=ipkw)
    if cfg.get("stepall"):
        # every rail steps from nom to full15 at t1 and back at t2
        import re
        for rail, (node, sign, caps, bleed) in fs.RAILS.items():
            di = getattr(rf, cfg.get("target", "FULL15"))[rail] - case["loads"][rail]
            net = re.sub(rf"(BL_{node} \S+ \S+ I = )([0-9.e+-]+)( \*)",
                         lambda m: f"{m.group(1)}({m.group(2)} + {di} * stp(time - {cfg['t1']}, 2e-6) * stp({cfg['t2']} - time, 2e-6)){m.group(3)}", net)
    t = time.time()
    vals = fs.run(net, f"check_{tag}")
    r = ice.summarise(vals)
    r["seconds"] = time.time() - t
    r["case"] = case
    r["config"] = {k: v for k, v in cfg.items()}
    r.update(analyse_wave(wave, cfg))
    if ipkw:
        r.update(analyse_ipk(ipkw, res))
    with open(os.path.join(fs.OUT, "checks", f"{tag}.json"), "w") as f:
        json.dump(r, f, indent=1)
    print(f"{tag}: " + " ".join(f"{rf.SHORT[k]}={r[k]:.3f}[{r[k + ' min']:.3f}..{r[k + ' max']:.3f}]" for k in fs.RAILS)
          + f" FB={r['fb']:.2f} ABM={r['abm']:.2f} Pin={r['pin']:.2f} W ({r['seconds']:.0f}s)", flush=True)
    for k, v in r.items():
        if k.startswith("w_"):
            print(f"   {k} = {v}")
    return r


def analyse_wave(path, cfg):
    """Step: undershoot / overshoot and settling of every rail; burst: period and ripple."""
    out = {}
    if not os.path.exists(path):
        return out
    d = np.loadtxt(path)
    t = d[:, 0]
    cols = d[:, 1::2]
    names = ["5V", "20V", "20V_ISO_SEC", "5V_ISOL", "-5V_SEC", "-100V BIAS", "fb", "abm", "ena"]
    if cfg.get("startup"):
        names.append("vcc")
    w = {n: cols[:, k] for k, n in enumerate(names)}
    if cfg.get("startup"):
        over = t[w["fb"] > 2.73]
        out["w_fb_above_olp_ms"] = round(float(over[-1] * 1e3), 2) if len(over) else 0.0
        out["w_fb_first_below_olp_ms"] = round(float(t[np.argmax(w["fb"] < 2.73)] * 1e3), 2) if np.any(w["fb"] < 2.73) else None
        out["w_vcc_min"] = round(float(np.min(w["vcc"])), 2)
        out["w_vcc_min_at_ms"] = round(float(t[np.argmin(w["vcc"])] * 1e3), 2)
        out["w_vcc_end"] = round(float(w["vcc"][-1]), 2)
        for n in names[:6]:
            v = w[n]
            fin = np.mean(v[t > t[-1] - 3e-3])
            out[f"w_{n}_t95_ms"] = round(float(t[np.argmax(v > 0.95 * fin)] * 1e3), 2)
            out[f"w_{n}_overshoot_pct"] = round(float((np.max(v) / fin - 1) * 100), 1)
        return out
    st = cfg.get("step") or ({"t1": cfg["t1"], "t2": cfg["t2"]} if cfg.get("stepall") else None)
    if st:
        t1, t2 = st["t1"], st["t2"]
        for n in names[:6]:
            v = w[n]
            pre = np.mean(v[(t > t1 - 2e-3) & (t < t1)])
            mid = np.mean(v[(t > t2 - 2e-3) & (t < t2)])
            post = np.mean(v[(t > t[-1] - 2e-3)])
            a = (t >= t1) & (t < t2)
            b = t >= t2
            out[f"w_{n}"] = {"before": round(float(pre), 4), "loaded": round(float(mid), 4), "after": round(float(post), 4),
                             "dip_on_step": round(float(np.min(v[a]) - pre), 4), "peak_on_release": round(float(np.max(v[b]) - mid), 4)}
            # settling: last time after each edge that |v - final| > 1 % of nominal
            tol = 0.01 * fs.NOMINAL_V[n]
            for lab, sel, fin in (("settle_on", a, mid), ("settle_off", b, post)):
                idx = np.where(sel & (np.abs(v - fin) > tol))[0]
                out[f"w_{n}"][lab + "_ms"] = round(float((t[idx[-1]] - (t1 if lab == "settle_on" else t2)) * 1e3), 2) if len(idx) else 0.0
        fb = w["fb"]
        out["w_fb"] = {"before": round(float(np.mean(fb[(t > t1 - 2e-3) & (t < t1)])), 3),
                       "loaded": round(float(np.mean(fb[(t > t2 - 2e-3) & (t < t2)])), 3),
                       "max": round(float(np.max(fb[t > t1])), 3), "min": round(float(np.min(fb[t > t1])), 3)}
    else:
        tw = t >= t[-1] - cfg.get("twin", 4e-3)
        ena = w["ena"][tw]
        tt = t[tw]
        on = np.where((ena[1:] > 0.5) & (ena[:-1] <= 0.5))[0]
        out["w_bursts"] = int(len(on))
        if len(on) > 1:
            out["w_burst_period_ms"] = round(float(np.mean(np.diff(tt[on])) * 1e3), 3)
        out["w_abm_fraction"] = round(float(np.mean(w["abm"][tw])), 3)
        for n in names[:6]:
            v = w[n][tw]
            out[f"w_{n}_pp_mV"] = round(float((np.max(v) - np.min(v)) * 1e3), 1)
    return out


def analyse_ipk(path, res):
    """Cycle-by-cycle primary peak current and on-time from the saved window (wrdata of i(L*),
    v(col), v(gate)): a subharmonic oscillation shows as alternating peaks / on-times."""
    d = np.loadtxt(path)
    t = d[:, 0]
    cols = d[:, 1::2]
    names = res["names"]
    ip = cols[:, names.index("P1") if "P1" in names else 0]
    gate = cols[:, len(names) + 1]
    on = np.where((gate[1:] > 0.5) & (gate[:-1] <= 0.5))[0]
    off = np.where((gate[1:] <= 0.5) & (gate[:-1] > 0.5))[0]
    pk, ton, imin = [], [], []
    for a in on:
        b = off[off > a]
        if not len(b):
            break
        b = b[0]
        pk.append(float(np.max(ip[a:b + 1])))
        imin.append(float(ip[min(a + 30, b)]))           # ~0.3 us after turn-on (after the edge spike)
        ton.append(float(t[b] - t[a]))
    pk, ton = np.array(pk), np.array(ton)
    if len(pk) < 4:
        return {"w_cycles": int(len(pk))}
    alt = np.abs(np.diff(pk))
    return {"w_cycles": int(len(pk)), "w_ipk_mean": round(float(pk.mean()), 4), "w_ipk_min": round(float(pk.min()), 4),
            "w_ipk_max": round(float(pk.max()), 4), "w_ipk_cycle_to_cycle_max": round(float(alt.max()), 4),
            "w_ton_mean_us": round(float(ton.mean() * 1e6), 3), "w_ton_min_us": round(float(ton.min() * 1e6), 3),
            "w_ton_max_us": round(float(ton.max() * 1e6), 3), "w_i_after_turn_on_mean": round(float(np.mean(imin)), 4)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("checks", nargs="*")
    ap.add_argument("--option", default="eel19_tiw_sandwich_s_pre3_ice")
    ap.add_argument("--comp", default="")
    ap.add_argument("--tag", default="")
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args(argv)
    if a.list:
        for k, v in CHECKS.items():
            print(k, v)
        return 0
    comp = parse_comp(a.comp)
    tag = a.tag or ("_" + "_".join(f"{k}{v}" for k, v in comp.items()) if comp else "")
    names = a.checks or ["step"]
    if a.jobs > 1:
        pool = rf.Pool(a.jobs)
        try:
            pool.map(run_check, [(n, a.option, comp, tag) for n in names])
        finally:
            pool.close()
    else:
        for n in names:
            run_check(n, a.option, comp, tag)
    return 0


if __name__ == "__main__":
    sys.exit(main())
