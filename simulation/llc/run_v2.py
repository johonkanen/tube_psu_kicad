"""Follow-up run with the 2021 design document: 64 T, Lm 320 uH (calibrated gap), best-fit
build from fit3.py, effective resonant capacitance 12.5 nF (5.1 X7R as built) and the
recommended C0G 4 x 3.3 nF = 13.2 nF (5.2).

python3 run_v2.py <best_fit_json_index_or_-1>
Writes out/v2.json.
"""
from __future__ import annotations

import json
import math
import sys
import warnings

import numpy as np

import llc_sim as sim
import om_tr2 as m
import run_tr2 as r1
import PyOpenMagnetics as P

warnings.filterwarnings("ignore")
m.load()
NP = 64
AE = 51.84e-6
LM_DOC = 320e-6
CASES_C = {"5.1 X7R eff 12.5n": 12.46e-9, "5.2 C0G 4x3.3n = 13.2n": 13.2e-9,
           "5.2 BOM C0G 4x4.7n = 18.8n": 18.8e-9, "doc 22n": 22e-9}


def best_geometry():
    rows = json.load(open("out/fit3.json"))
    mode = sys.argv[1] if len(sys.argv) > 1 else "S1"
    rows.sort(key=lambda r: r["rms_log_err_" + mode])
    return rows[0], mode


def coil_kw(r):
    odr = m.wire_od("LITZ35")
    lt = 1.25e-3 if r["litz"].startswith("pressed") else None
    wdt = (math.pi / 4 * odr ** 2 / lt) if lt else odr
    return dict(tape_layers=r["tape_layers"], pitch_factor=r["pitch"], litz_thk=lt, sec_order=r["sec_order"],
                radial_width=4.7e-3, sec_y_offset=(7.9e-3 - 2 * wdt if r["sec_pos"] == "end" else 0.0))


def core_for(kind, g, mat="N97"):
    res = {"type": "residual", "length": 10e-6}
    gp = ([{"type": "subtractive", "length": g}, dict(res), dict(res)] if kind == "centre"
          else [{"type": "additive", "length": g} for _ in range(3)])
    return P.calculate_core_data({"functionalDescription": {"type": "two-piece set", "shape": m.SHAPE, "material": mat,
                                                            "numberStacks": 1, "gapping": gp}}, False)


def main():
    best, mode = best_geometry()
    kw = coil_kw(best)
    out = {"best_fit": best, "fit_mode": mode}
    # owner build (6 + 2 strands, 64 T), and the 66 T variant
    res_leak = {}
    for lab, na in (("64T", 64), ("66T", 66)):
        coil, rep = m.build_coil(ns=2, na=na, pa_par=6, nb=na, pb_par=2, **kw)
        L = m.inductance_matrix({"core": m.make_core("N97", 0), "coil": coil}, 220e3)
        d = {s: m.leak_general(L, "parallel", s) * 1e6 for s in ("S1", "series", "both")}
        _, kA, _, _ = m.leak_parallel_primary(L, "S1")
        Lo = L[np.ix_([0, 3], [0, 3])]
        d["kA_load"] = kA.real
        d["kA_mag"] = (Lo[1, 1] - Lo[0, 1]) / (Lo[0, 0] + Lo[1, 1] - 2 * Lo[0, 1])
        d["stack_mm"] = rep["stack_mm"]
        res_leak[lab] = d
    out["leak"] = res_leak
    print("leak", json.dumps(res_leak))
    Lop = res_leak["64T"]["S1"] * 1e-6          # what the circuit sees in a half cycle (model)
    # scale the model to the measured 42 uH under the fitted measurement mode
    meas_mode = sys.argv[2] if len(sys.argv) > 2 else "series"   # how the 42 uH was measured (hypothesis)
    out["meas_mode"] = meas_mode
    scale = 42.0 / res_leak["64T"][meas_mode]
    Lop_cal = Lop * scale
    out["Lop_model_uH"] = Lop * 1e6
    out["Lop_calibrated_uH"] = Lop_cal * 1e6
    out["measure_mode_ratio_S1_over_series"] = res_leak["64T"]["S1"] / res_leak["64T"]["series"]

    # item 3: resonances
    res3 = {}
    for cl, C in CASES_C.items():
        res3[cl] = {"f_42uH_kHz": 1 / (2 * math.pi * math.sqrt(42e-6 * C)) / 1e3,
                    "f_Lop_cal_kHz": 1 / (2 * math.pi * math.sqrt(Lop_cal * C)) / 1e3,
                    "half_period_Lop_cal_us": math.pi * math.sqrt(Lop_cal * C) * 1e6}
    out["resonance"] = res3

    # item 5: gain / frequency / ZVS (time domain), Lm 320 uH
    gain = {}
    for cl in ("5.1 X7R eff 12.5n", "5.2 C0G 4x3.3n = 13.2n", "5.2 BOM C0G 4x4.7n = 18.8n", "doc 22n"):
        C = CASES_C[cl]
        for Vin in (380.0, 400.0, 420.0):
            for Io in (6.5, 10.0, 15.0):
                f, rr, note = sim.freq_for_load(Io, Vin, Lop_cal, C, LM_DOC)
                rr.pop("wave", None)
                gain[f"{cl} | {Vin:.0f} V | {Io} A"] = {"f_kHz": (f / 1e3 if f else None), "note": note,
                                                       **{k: float(v) for k, v in rr.items()}}
                print(cl, Vin, Io, note, f and round(f / 1e3, 1), {k: round(float(v), 3) for k, v in rr.items()}, flush=True)
    out["gain"] = gain

    # item 4 / 6: losses with the real gap (calibrated to 320 uH)
    loss = {}
    gaps = [("centre 1.78 mm (MKF -> 320 uH)", "centre", 1.78e-3), ("spacer 0.84 mm (MKF -> 320 uH)", "spacer", 0.84e-3),
            ("centre 1.0 mm literal (MKF 455 uH; currents from 320 uH)", "centre", 1.0e-3)]
    coil, rep = m.build_coil(ns=2, na=64, pa_par=6, nb=64, pb_par=2, **kw)
    kA_l, kA_m = res_leak["64T"]["kA_load"], res_leak["64T"]["kA_mag"]
    for glab, kind, g in gaps:
        core = core_for(kind, g)
        mag = {"core": core, "coil": coil}
        for cl in ("5.1 X7R eff 12.5n", "5.2 C0G 4x3.3n = 13.2n"):
            C = CASES_C[cl]
            for Io in (10.0, 15.0):
                pts = []
                f_op, rr, note = sim.freq_for_load(Io, 400.0, Lop_cal, C, LM_DOC)
                if f_op:
                    pts.append(("operating %.0f kHz" % (f_op / 1e3), f_op, "sim"))
                pts += [("corner 150 kHz", 150e3, "ideal"), ("corner 220 kHz", 220e3, "ideal")]
                for plab, f, kind_w in pts:
                    if cl != "5.1 X7R eff 12.5n" and kind_w == "ideal":
                        continue          # corners do not depend on C
                    key = f"{glab} | {cl} | {Io} A | {plab}"
                    if kind_w == "sim":
                        Vcl = sim.N * (6.3 + sim.R_SEC * Io * 1.23)
                        w = sim.run_period(f, 400.0, Lop_cal, C, LM_DOC, Vcl, 2000, 800)
                        irs, ims, _ = w["wave"]
                        t = np.linspace(0, 1 / f, len(irs) + 1)
                        irs = np.append(irs, irs[0]); ims = np.append(ims, ims[0])
                        il = irs - ims
                        vm = LM_DOC * np.gradient(ims, t)
                    else:
                        Vm = sim.N * (6.3 + sim.R_SEC * Io * 1.23)
                        T = 1 / f
                        t = np.linspace(0, T, 513)
                        ipk = math.pi * Io / (2 * sim.N)
                        il = ipk * np.sin(2 * np.pi * f * t)
                        impk = Vm / (4 * f * LM_DOC)
                        ims = np.where(t < T / 2, -impk + 4 * impk * t / T, 3 * impk - 4 * impk * t / T)
                        vm = np.where(t < T / 2, Vm, -Vm)
                    cur = {"PA": kA_l * il + kA_m * ims, "PB": (1 - kA_l) * il + (1 - kA_m) * ims,
                           "S1": -sim.N * np.maximum(il, 0), "S2": -sim.N * np.minimum(il, 0)}
                    # MAS convention for the loss call: run_tr2.winding_losses(sign=-1) flips the secondaries
                    tot, per, op = r1.winding_losses(mag, f, t, cur, sign=-1.0)
                    lam = np.concatenate([[0.0], np.cumsum(0.5 * (vm[1:] + vm[:-1]) * np.diff(t))])
                    bpk = 0.5 * (lam.max() - lam.min()) / (NP * AE)
                    cl_ = r1.core_losses(core, coil, f, t, vm, LM_DOC)
                    cl_.pop("raw_keys", None)
                    ptot = tot + (cl_["IGSE"] if isinstance(cl_.get("IGSE"), float) else 0)
                    d = {"f_kHz": f / 1e3, "winding_W": tot, "per": per, "core": cl_, "Bpk_voltsec_T": bpk,
                         "Im_pk_A": float(np.max(np.abs(ims))), "Ipri_rms": float(np.sqrt(np.mean((cur["PA"] + cur["PB"])[:-1] ** 2))),
                         "Isec_half_rms": float(np.sqrt(np.mean(cur["S1"][:-1] ** 2))), "P_total_W": ptot,
                         "dT_mkf_Rth_K": P.calculate_temperature_from_core_thermal_resistance(core, ptot) - 25.0,
                         "dT_mclyman_K": (ptot * 1e3 / 25.0) ** 0.833}
                    loss[key] = d
                    print(key, "Pw %.2f (PA %.2f PB %.2f S %.2f) core %.2f Bpk %.3f Im %.2f Ipri %.2f Isec %.1f Ptot %.2f dT %.0f-%.0f" % (
                        tot, per["PA"]["total"], per["PB"]["total"], per["S1"]["total"] + per["S2"]["total"],
                        cl_.get("IGSE", float("nan")), bpk, d["Im_pk_A"], d["Ipri_rms"], d["Isec_half_rms"], ptot,
                        d["dT_mclyman_K"], d["dT_mkf_Rth_K"]), flush=True)
                    print("    per", json.dumps({k: {q: round(v, 3) for q, v in x.items()} for k, x in per.items()}))
    out["loss"] = loss
    json.dump(out, open("out/v2.json", "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
