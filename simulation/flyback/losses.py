"""Winding and core losses of an option from the simulated winding currents (OpenMagnetics).

Takes the last full switching period of the ngspice run (out/spice/<option>__<case>_wave.txt,
written for the cases nom and max_S15), builds a MAS operating point with the current
waveform of every winding and asks MKF for winding losses (DC + skin + proximity, Dowell /
Ferreira, at 60 degC) and core losses (iGSE, N87 assumed) with the peak flux density.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import om_model as m  # noqa: E402
import options as opts  # noqa: E402
import PyOpenMagnetics as P  # noqa: E402

OUT = os.path.join(HERE, "out")


def last_period(name, case="nom", npts=400):
    om = json.load(open(os.path.join(OUT, "om", f"{name}.json")))
    names = om["names"]
    d = np.loadtxt(os.path.join(OUT, "spice", f"{name}__{case}_wave.txt"))
    t = d[:, 0]
    cols = d[:, 1::2]          # wrdata: (t, value) pairs
    gate = cols[:, len(names) + 1]
    edges = np.where((gate[1:] > 0.5) & (gate[:-1] <= 0.5))[0]
    i0, i1 = edges[-2], edges[-1]
    tt = np.linspace(t[i0], t[i1], npts)
    cur = {n: np.interp(tt, t, cols[:, k]) for k, n in enumerate(names)}
    vcol = np.interp(tt, t, cols[:, len(names)])
    return om, tt - tt[0], cur, vcol


def analyse(name, case="nom", temperature=60.0, vin=None):
    if vin is None:                 # DC+ of the case (run_flyback cases; 400 V unless the case says otherwise)
        import run_flyback as rf
        vin = next((c.get("vin", 400.0) for c in rf.all_cases() if c["name"] == case), 400.0)
    om, tt, cur, vcol = last_period(name, case)
    opt = opts.get(name)
    m.use_core(opt.get("core"))             # EF20 (default) or EEL19
    coil, _ = m.build_coil(opt)
    core = m.make_core(om["gap"], opt.get("gap_kind", "subtractive"))
    mag = {"core": core, "coil": coil}
    f = 1.0 / tt[-1]
    exc = []
    names = om["names"]
    for n in names:
        i = cur[n]
        exc.append({"name": n, "frequency": f,
                    "current": {"waveform": {"data": list(map(float, i)), "time": list(map(float, tt))}}})
    # primary voltage (DC+ - collector) for the core: put it on the first primary winding,
    # scaled to that winding's share of the primary turns
    nprim = sum(om["turns"][k] for k, n in enumerate(names) if n in ("P", "P1", "P2"))
    vp = (vin - vcol) * om["turns"][0] / nprim
    exc[0]["voltage"] = {"waveform": {"data": list(map(float, vp)), "time": list(map(float, tt))}}
    op = {"name": case, "conditions": {"ambientTemperature": 40.0}, "excitationsPerWinding": exc}
    rms = {n: float(np.sqrt(np.mean(cur[n] ** 2))) for n in names}
    out = {"option": name, "case": case, "frequency": f, "rms": rms}
    try:
        # same harmonic set for every winding: with trimming on, MKF (1.7.41) keeps a
        # different number of harmonics per winding and then fails combining them
        P.set_settings({"inputsTrimHarmonics": False, "harmonicAmplitudeThresholdQuickMode": False})
        wl = P.calculate_winding_losses(mag, op, temperature)
        out["winding_losses_W"] = wl.get("windingLosses")
        per = {}
        for k, p in enumerate(wl.get("windingLossesPerWinding") or []):
            tot = (p.get("ohmicLosses") or {}).get("losses", 0.0)
            for key in ("skinEffectLosses", "proximityEffectLosses"):
                tot += sum((p.get(key) or {}).get("lossesPerHarmonic") or [])
            per[p.get("name", names[k])] = tot
        out["per_winding_W"] = per
    except Exception as e:  # report, do not hide
        out["winding_losses_error"] = str(e)
    # core losses: they depend only on the flux, so a plain one-winding coil that MKF's
    # thermal check accepts is used (the hand-placed coil trips its flange check)
    try:
        simple = P.wind({"bobbin": m.bobbin(), "functionalDescription": [
            {"name": "P", "numberTurns": nprim, "numberParallels": 1, "wire": m.wire("Round 34.0 - Heavy Build"),
             "isolationSide": "primary"}]}, 1, [1], [0], [[0, 0]])
        vfull = vin - vcol
        op1 = {"name": case, "conditions": {"ambientTemperature": 40.0}, "excitationsPerWinding": [
            {"name": "P", "frequency": f,
             "current": {"waveform": {"data": list(map(float, sum(cur[n] for n in names if n in ("P", "P1"))))
                                      , "time": list(map(float, tt))}},
             "voltage": {"waveform": {"data": list(map(float, vfull)), "time": list(map(float, tt))}}}]}
        inputs = {"designRequirements": {"magnetizingInductance": {"nominal": om["L"][0][0]}, "turnsRatios": []},
                  "operatingPoints": [op1]}
        for model in ("IGSE", "STEINMETZ", "ROSHEN"):
            cl = P.calculate_core_losses(core, simple, inputs, {"coreLosses": model, "reluctance": "ZHANG"})
            out[f"core_losses_W_{model}"] = cl.get("coreLosses")
            if model == "IGSE":
                out["B_peak_T"] = cl.get("magneticFluxDensityPeak")
                out["B_ac_peak_T"] = cl.get("magneticFluxDensityAcPeak")
                out["core_temperature_C"] = cl.get("maximumCoreTemperature")
    except Exception as e:
        out["core_losses_error"] = str(e)
    return out


if __name__ == "__main__":
    # python3 losses.py <option> [...] [--case full15]   (default case nom; the result file of
    # a case other than nom is out/losses/<option>__<case>.json)
    os.makedirs(os.path.join(OUT, "losses"), exist_ok=True)
    args = sys.argv[1:]
    case = "nom"
    if "--case" in args:
        i = args.index("--case")
        case = args[i + 1]
        del args[i:i + 2]
    for n in args or ["current"]:
        r = analyse(n, case)
        with open(os.path.join(OUT, "losses", f"{n}.json" if case == "nom" else f"{n}__{case}.json"), "w") as f:
            json.dump(r, f, indent=1)
        print(f"{n}: winding {r.get('winding_losses_W')} W, core iGSE {r.get('core_losses_W_IGSE')} / "
              f"Steinmetz {r.get('core_losses_W_STEINMETZ')} / Roshen {r.get('core_losses_W_ROSHEN')} W, "
              f"Bpk {r.get('B_peak_T')} T, errors: {r.get('winding_losses_error', '')} {r.get('core_losses_error', '')}", flush=True)
