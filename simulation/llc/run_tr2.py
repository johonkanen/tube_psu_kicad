"""TR2 (heater LLC, EF25) check with OpenMagnetics + hand cross-checks.

python3 run_tr2.py [geom] [leak] [sens] [lm] [loss]     (default: all)
Writes out/<step>.json and mas/tr2_ns<k>.json.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

import numpy as np

import om_tr2 as m
import fd2d_leakage as fd
import PyOpenMagnetics as P

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
MAS = os.path.join(HERE, "mas")
os.makedirs(OUT, exist_ok=True)
os.makedirs(MAS, exist_ok=True)

MU0 = 4e-7 * math.pi
NP = 66
F_R = 220e3            # owner: LLC resonance 220 kHz
L_MEAS = 42e-6         # owner: leakage referred to the primary
CR = 18.8e-9           # repo: C49 || C42 and C41 || C22, 4 x 4.7 nF C0G, the halves in parallel for AC
VIN = 400.0
VO = 6.3               # rail name 6V3 (repo); heater voltage
IO = 15.0              # owner: bench-verified 15 A secondary (taken as the dc output current)
VSR = 0.3              # assumed: BUK9Y15-60E ~15 mOhm x 1.3 (hot) x 15 A + track
T_WIND = 100.0
RHO_CU20 = 1.0 / 58.0e6
ALPHA = 0.00393


def save(name, obj):
    with open(os.path.join(OUT, name + ".json"), "w") as f:
        json.dump(obj, f, indent=1, default=lambda o: float(o) if isinstance(o, (np.floating,)) else str(o))


# ------------------------------------------------------------------------------------------
def step_geom():
    res = {}
    for ns in (1, 2):
        coil, rep = m.build_coil(ns=ns)
        try:
            ff = P.calculate_filling_factor(coil)
        except Exception as e:  # noqa
            ff = f"error: {e}"
        cu = (528 * math.pi / 4 * m.AWG30_CU ** 2 + 2 * ns * 35 * math.pi / 4 * 0.2e-3 ** 2) * 1e6
        od2 = (528 * m.AWG30_OD ** 2 + 2 * ns * (math.pi / 4) * m.wire_od("LITZ35") ** 2) * 1e6
        rep.update({"mkf_filling_factor": ff, "copper_mm2": cu, "copper_fill_norwe": cu / (4.2 * 15.8),
                    "od2_area_mm2": od2, "od2_fill_norwe": od2 / (4.2 * 15.8)})
        # variants: no nesting, round litz
        for tag, kw in (("no_nesting_round_litz", dict(pitch_factor=1.0, litz_thk=None, radial_width=6e-3)),
                        ("nesting_round_litz", dict(pitch_factor=0.866, litz_thk=None, radial_width=6e-3)),
                        ("no_nesting_pressed_litz", dict(pitch_factor=1.0, radial_width=6e-3))):
            _, r2 = m.build_coil(ns=ns, **kw)
            rep["stack_" + tag + "_mm"] = r2["stack_mm"]
        res[f"ns{ns}"] = rep
        print(ns, json.dumps(rep, default=str))
    save("geom", res)


# ------------------------------------------------------------------------------------------
def mag_for(ns, material="N97", gap=0.0, **kw):
    coil, rep = m.build_coil(ns=ns, **kw)
    return {"core": m.make_core(material, gap), "coil": coil}, rep


def step_leak():
    res = {"hand": {}}
    w = 2 * math.pi * F_R
    res["hand"]["f_r_42uH_18n8_kHz"] = 1 / (2 * math.pi * math.sqrt(L_MEAS * CR)) / 1e3
    res["hand"]["f_r_42uH_9n4_kHz"] = 1 / (2 * math.pi * math.sqrt(L_MEAS * CR / 2)) / 1e3
    res["hand"]["L_for_220k_with_18n8_uH"] = 1 / (w ** 2 * CR) * 1e6
    res["hand"]["C_for_220k_with_42uH_nF"] = 1 / (w ** 2 * L_MEAS) * 1e9
    for ns in (1, 2):
        mag, rep = mag_for(ns)
        t = time.time()
        L = m.inductance_matrix(mag, F_R)
        d = {"L_matrix_uH": (L * 1e6).tolist(), "t_s": time.time() - t}
        for case in ("S1", "series", "both"):
            Le, kA, kB, _ = m.leak_parallel_primary(L, case)
            d[f"mkf_{case}_uH"] = Le * 1e6
            d[f"mkf_{case}_kA"] = kA.real
        # magnetizing-current split (secondary open)
        Lo = L[np.ix_([0, 3], [0, 3])]
        d["kA_open"] = (Lo[1, 1] - Lo[0, 1]) / (Lo[0, 0] + Lo[1, 1] - 2 * Lo[0, 1])
        d["L_PA_PB_leak_uH"] = (Lo[0, 0] + Lo[1, 1] - 2 * Lo[0, 1]) * 1e6
        for src in (0, 3):
            lk = P.calculate_leakage_inductance(mag, F_R, src)["leakageInductancePerWinding"]
            d[f"mkf_leakage_from_{m.NAMES[src]}_uH"] = [x["nominal"] * 1e6 for x in lk]
        # independent FD check
        for h in (0.1e-3, 0.05e-3):
            for case in ("S1", "series"):
                r = fd.balanced_leakage(mag["coil"], case, h)
                d[f"fd_h{h*1e3:.2f}_{case}"] = {k: {"L_uH": v[0] * 1e6, "kA": float(v[1])} for k, v in r.items()}
        # 1-D (Dowell-type, full-height layers) hand estimate with the same build and split
        mlt = rep["MLT_mm"]
        a1, a2 = rep["PA"]["build_mm"], rep["PB"]["build_mm"]
        s, g = rep["S"]["build_mm"], rep["tape_each_mm"]
        def f1d(k):
            return (mlt["PA"] * (a1 / 3) * k ** 2 + 0.5 * (mlt["PA"] + mlt["S1"]) * g * k ** 2
                    + mlt["S1"] * s / 3 * (k ** 2 - k * (1 - k) + (1 - k) ** 2)
                    + 0.5 * (mlt["S1"] + mlt["PB"]) * g * (1 - k) ** 2 + mlt["PB"] * a2 / 3 * (1 - k) ** 2)
        ks = np.linspace(0, 1, 1001)
        kmin = ks[np.argmin([f1d(k) for k in ks])]
        d["hand_1d_full_height_uH"] = MU0 * NP ** 2 / (rep["window_axial_mm"] * 1e-3) * f1d(kmin) * 1e-6 * 1e6
        d["hand_1d_kA"] = float(kmin)
        n_eff = {"S1": NP / ns, "series": NP / (2 * ns)}
        for case in ("S1", "series"):
            d[f"ext_sec_L_to_reach_42uH_{case}_nH"] = (L_MEAS - d[f"mkf_{case}_uH"] * 1e-6) / n_eff[case] ** 2 * 1e9
        res[f"ns{ns}"] = d
        # MAS file (magnetic + operating point added later by step_loss)
        with open(os.path.join(MAS, f"tr2_ns{ns}_magnetic.json"), "w") as f:
            json.dump({"magnetic": mag}, f)
        print(ns, json.dumps({k: v for k, v in d.items() if k != "L_matrix_uH"}, default=str)[:3000])
    save("leak", res)


# ------------------------------------------------------------------------------------------
def step_sens():
    res = {}
    base = dict()
    cases = [("baseline (3 tape, pressed litz 1.25, nesting, sec centred)", {}),
             ("1 tape layer each side", dict(tape_layers=1)),
             ("6 tape layers each side", dict(tape_layers=6)),
             ("round litz 1.67 mm", dict(litz_thk=None, radial_width=6e-3)),
             ("no nesting (layer pitch = OD)", dict(pitch_factor=1.0, radial_width=6e-3)),
             ("+0.25 mm extra gap each side of S", dict(extra_gap=0.25e-3, radial_width=6e-3)),
             ("+0.5 mm extra gap each side of S", dict(extra_gap=0.5e-3, radial_width=6e-3)),
             ("+1.0 mm extra gap each side of S", dict(extra_gap=1.0e-3, radial_width=8e-3)),
             ("secondary at one end of the window", dict(sec_y_offset="end")),
             ("S1 block then S2 block (not bifilar)", dict(sec_order="block"))]
    for ns in (1, 2):
        rows = []
        for name, kw in cases:
            kw = dict(kw)
            if kw.get("sec_y_offset") == "end":
                odr = m.wire_od("LITZ35")
                wdt = math.pi / 4 * odr ** 2 / 1.25e-3
                kw["sec_y_offset"] = 7.9e-3 - ns * wdt
            try:
                mag, rep = mag_for(ns, **kw)
            except ValueError as e:
                rows.append({"case": name, "error": str(e)}); continue
            L = m.inductance_matrix(mag, F_R)
            r = {"case": name, "stack_mm": rep["stack_mm"]}
            for case in ("S1", "series"):
                Le, kA, _, _ = m.leak_parallel_primary(L, case)
                r[f"{case}_uH"] = Le * 1e6
                r[f"{case}_kA"] = kA.real
            rows.append(r)
            print(ns, json.dumps(r))
        res[f"ns{ns}"] = rows
    save("sens", res)


# ------------------------------------------------------------------------------------------
def step_lm():
    res = {}
    coil, rep = m.build_coil(ns=2)
    for mat in ("N97", "N87", "3C95"):
        rows = []
        for g in (0.0, 0.05e-3, 0.1e-3, 0.2e-3, 0.3e-3, 0.5e-3, 0.7e-3, 1.0e-3):
            mag = {"core": m.make_core(mat, g), "coil": coil}
            L = m.inductance_matrix(mag, 100e3)
            Lo = L[np.ix_([0, 3], [0, 3])]
            Lpar = 1 / np.linalg.inv(Lo).sum()
            # hand: L = N^2 / (Rgap + Rcore), no fringing, mu_i = 2000
            ae = mag["core"]["processedDescription"]["effectiveParameters"]["effectiveArea"]
            le = mag["core"]["processedDescription"]["effectiveParameters"]["effectiveLength"]
            rg = max(g, 20e-6) / (MU0 * 52.2e-6)
            rc = le / (MU0 * 2000 * ae)
            rows.append({"gap_mm": g * 1e3, "Lm_mkf_uH": Lpar * 1e6, "Lm_hand_nofringe_uH": NP ** 2 / (rg + rc) * 1e6})
        res[mat] = rows
        print(mat, json.dumps(rows))
    save("lm", res)


# ------------------------------------------------------------------------------------------
def fha_freq(M_need, Lr, Cr, Lm, Rac):
    """Lowest-to-highest scan: frequency (Hz) above the gain peak where the FHA gain = M_need."""
    fr = 1 / (2 * math.pi * math.sqrt(Lr * Cr))
    fs = np.linspace(0.3 * fr, 3 * fr, 20000)
    w = 2 * np.pi * fs
    Zs = 1j * w * Lr + 1 / (1j * w * Cr)
    Zp = 1 / (1 / (1j * w * Lm) + 1 / Rac)
    M = np.abs(Zp / (Zs + Zp))
    ipk = int(np.argmax(M))
    sel = np.where(M[ipk:] <= M_need)[0]
    return (float(fs[ipk + sel[0]]) if len(sel) else None), float(fs[ipk]), float(M[ipk]), fr


def waveforms(ns, f, Vm, Lm, kA_load, kA_mag, n=256):
    T = 1 / f
    t = np.linspace(0, T, n + 1)
    nr = NP / ns
    ipk = math.pi * IO / (2 * nr)
    iL = ipk * np.sin(2 * np.pi * f * t)
    im_pk = Vm / (4 * f * Lm)
    im = np.where(t < T / 2, -im_pk + 4 * im_pk * t / T, 3 * im_pk - 4 * im_pk * t / T)
    v = np.where(t < T / 2, Vm, -Vm)
    cur = {"PA": kA_load * iL + kA_mag * im,
           "S1": -nr * np.maximum(iL, 0),
           "S2": -nr * np.minimum(iL, 0),
           "PB": (1 - kA_load) * iL + (1 - kA_mag) * im}
    return t, cur, v, ipk, im_pk


def winding_losses(mag, f, t, currents, temperature=T_WIND, sign=1.0):
    P.set_settings({"inputsTrimHarmonics": False, "harmonicAmplitudeThresholdQuickMode": False})
    exc = []
    for nme in m.NAMES:
        i = currents[nme] * (sign if nme.startswith("S") else 1.0)
        exc.append({"name": nme, "frequency": f,
                    "current": {"waveform": {"data": list(map(float, i)), "time": list(map(float, t))}}})
    op = {"name": "llc", "conditions": {"ambientTemperature": 40.0}, "excitationsPerWinding": exc}
    wl = P.calculate_winding_losses(mag, op, temperature)
    per = {}
    for k, p in enumerate(wl["windingLossesPerWinding"]):
        o = (p.get("ohmicLosses") or {}).get("losses", 0.0)
        sk = sum((p.get("skinEffectLosses") or {}).get("lossesPerHarmonic") or [])
        pr = sum((p.get("proximityEffectLosses") or {}).get("lossesPerHarmonic") or [])
        per[m.NAMES[k]] = {"dc": o, "skin": sk, "prox": pr, "total": o + sk + pr}
    P.reset_settings()
    return wl["windingLosses"], per, op


def core_losses(core, coil, f, t, v, lm, temperature=100.0):
    dt = np.diff(t)
    lam = np.concatenate([[0.0], np.cumsum(0.5 * (v[1:] + v[:-1]) * dt)])
    i = lam / lm
    i = i - 0.5 * (i.max() + i.min())
    op = {"name": "llc", "conditions": {"ambientTemperature": temperature}, "excitationsPerWinding": [
        {"name": "PA", "frequency": f,
         "current": {"waveform": {"data": list(map(float, i)), "time": list(map(float, t))}},
         "voltage": {"waveform": {"data": list(map(float, v)), "time": list(map(float, t))}}}]}
    inputs = {"designRequirements": {"magnetizingInductance": {"nominal": lm}, "turnsRatios": []},
              "operatingPoints": [op]}
    simple = P.wind({"bobbin": coil["bobbin"], "functionalDescription": [dict(coil["functionalDescription"][0], numberParallels=1)]},
                    1, [1], [0], [[0, 0]])
    out = {}
    for model in ("IGSE", "STEINMETZ", "ROSHEN"):
        try:
            cl = P.calculate_core_losses(core, simple, inputs, {"coreLosses": model, "reluctance": "ZHANG"})
            out[model] = cl.get("coreLosses")
            if model == "IGSE":
                out["Bpk_T"] = cl.get("magneticFluxDensityPeak")
                out["T_core_mkf_C"] = cl.get("maximumCoreTemperature")
                out["raw_keys"] = list(cl.keys())
        except Exception as e:  # noqa
            out[model] = f"error: {e}"
    return out


def rdc_hand(rep, ns, T=T_WIND):
    k = 1 + ALPHA * (T - 20)
    a30 = math.pi / 4 * m.AWG30_CU ** 2
    alitz = 35 * math.pi / 4 * 0.2e-3 ** 2
    mlt = rep["MLT_mm"]
    return {"PA": NP * mlt["PA"] * 1e-3 * RHO_CU20 * k / (6 * a30),
            "PB": NP * mlt["PB"] * 1e-3 * RHO_CU20 * k / (2 * a30),
            "S1": ns * mlt["S1"] * 1e-3 * RHO_CU20 * k / alitz,
            "S2": ns * mlt["S2"] * 1e-3 * RHO_CU20 * k / alitz}


def step_loss():
    leak = json.load(open(os.path.join(OUT, "leak.json")))
    lmres = json.load(open(os.path.join(OUT, "lm.json")))
    res = {}
    # skin depth: MKF vs hand
    sd = {}
    for T in (20.0, 100.0):
        hand = math.sqrt(RHO_CU20 * (1 + ALPHA * (T - 20)) / (math.pi * F_R * MU0))
        try:
            cur = {"processed": {"label": "Sinusoidal", "effectiveFrequency": F_R, "peak": 1.0, "rms": 0.707, "offset": 0.0, "peakToPeak": 2.0}}
            mk = P.calculate_effective_skin_depth("copper", cur, T)
        except Exception as e:  # noqa
            mk = f"error: {e}"
        sd[f"{T:.0f}C"] = {"hand_mm": hand * 1e3, "mkf_mm": (mk * 1e3 if isinstance(mk, float) else mk)}
    res["skin_depth_220k"] = sd
    print("skin", sd)

    def gap_for(mat, lm_target):
        rows = lmres[mat]
        gs = [r["gap_mm"] for r in rows]; ls = [r["Lm_mkf_uH"] for r in rows]
        # Lm decreasing with gap; interpolate on log
        for a, b in zip(range(len(rows) - 1), range(1, len(rows))):
            if ls[a] >= lm_target >= ls[b]:
                fr_ = (math.log(ls[a]) - math.log(lm_target)) / (math.log(ls[a]) - math.log(ls[b]))
                return (gs[a] + fr_ * (gs[b] - gs[a])) * 1e-3
        return None

    for ns in (1, 2):
        lk = leak[f"ns{ns}"]
        kA_load = lk["mkf_S1_kA"]
        kA_mag = lk["kA_open"]
        nr = NP / ns
        Vm_needed = nr * (VO + VSR)
        Vm = min(Vm_needed, 1.2 * VIN / 2)   # cap (ns=1 cannot reach 6.3 V)
        Vm_used = Vm if ns == 2 else VIN / 2
        Rac = 8 * nr ** 2 / math.pi ** 2 * (VO / IO)
        d = {"n": nr, "Vm_needed_for_6V3_V": Vm_needed, "Vm_used_V": Vm_used,
             "gain_needed": Vm_needed / (VIN / 2), "Vo_at_gain1_V": VIN / 2 / nr - VSR, "Rac_ohm": Rac,
             "Q_42uH_18n8": math.sqrt(L_MEAS / CR) / Rac, "kA_load": kA_load, "kA_mag": kA_mag}
        # FHA operating frequency for the needed gain (ns = 2 only meaningful)
        fha = {}
        for lab, Lr, Cr in (("42uH_18n8_C0G", L_MEAS, CR), ("42uH_12n46_bench220k", L_MEAS, 1 / ((2 * math.pi * F_R) ** 2 * L_MEAS)),
                            ("model_S1_18n8", lk["mkf_S1_uH"] * 1e-6, CR)):
            for lm in (200e-6, 400e-6):
                fsel, fpk, Mpk, fr = fha_freq(min(Vm_needed / (VIN / 2), 5), Lr, Cr, lm, Rac)
                fha[f"{lab}_Lm{lm*1e6:.0f}"] = {"f_r_kHz": fr / 1e3, "f_op_kHz": (fsel / 1e3 if fsel else None),
                                                "gain_peak": Mpk, "f_peak_kHz": fpk / 1e3}
        d["fha"] = fha
        Ae = 51.84e-6
        d["Bpk_hand_220k_T"] = Vm_used / (4 * F_R * NP * Ae)
        d["f_for_0p3T_kHz"] = Vm_used / (4 * NP * Ae * 0.3) / 1e3
        cases = {}
        for mat, gap, lm_lab in (("N97", 0.0, "ungapped"), ("N97", 0.2e-3, "gap0.2"), ("N97", 1.0e-3, "gap1.0"),
                                 ("N87", 0.0, "ungapped"), ("3C95", 0.0, "ungapped")):
            if True:
                mag, rep = mag_for(ns, mat, gap or 0.0)
                L = m.inductance_matrix(mag, F_R)
                Lo = L[np.ix_([0, 3], [0, 3])]
                lm_mkf = 1 / np.linalg.inv(Lo).sum()
                for f, flab in ((F_R, "220k"),):
                    t, cur, v, ipk, impk = waveforms(ns, f, Vm_used, lm_mkf, kA_load, kA_mag)
                    c = {"material": mat, "gap_mm": (gap or 0) * 1e3, "Lm_mkf_uH": lm_mkf * 1e6,
                         "Ipk_load_A": ipk, "Im_pk_A": impk,
                         "Irms": {k: float(np.sqrt(np.mean(vv[:-1] ** 2))) for k, vv in cur.items()}}
                    c["Ipri_rms_total_A"] = float(np.sqrt(np.mean((cur["PA"] + cur["PB"])[:-1] ** 2)))
                    tt = time.time()
                    if mat == "N97":
                        # winding losses; check the secondary sign convention (MMF balance)
                        # MAS / MKF convention: secondary load current positive (opposing MMF);
                        # verified in diag_sign.py (field drops vs. the open-secondary case)
                        tot_m, per_m, op = winding_losses(mag, f, t, cur, sign=-1.0)
                        tot_p, per_p, _ = winding_losses(mag, f, t, cur, sign=1.0)
                        c["winding_loss_W"] = tot_m
                        c["winding_loss_per"] = per_m
                        c["winding_loss_W_wrong_sign_diagnostic"] = tot_p
                        c["t_winding_s"] = time.time() - tt
                        rh = rdc_hand(rep, ns)
                        c["Rdc_hand_100C_ohm"] = rh
                        c["Pdc_hand_W"] = {k: rh[k] * c["Irms"][k] ** 2 for k in rh}
                        try:
                            c["Rdc_mkf_100C_ohm"] = [float(x) for x in P.calculate_dc_resistance_per_winding(mag["coil"], T_WIND)]
                        except Exception as e:  # noqa
                            c["Rdc_mkf_100C_ohm"] = f"error: {e}"
                        if lm_lab == "ungapped":
                            mas = {"inputs": {"designRequirements": {"magnetizingInductance": {"nominal": lm_mkf},
                                                                     "turnsRatios": [{"nominal": nr}, {"nominal": nr}, {"nominal": 1.0}],
                                                                     "leakageInductance": [{"nominal": L_MEAS}]},
                                              "operatingPoints": [op]},
                                   "magnetic": mag}
                            with open(os.path.join(MAS, f"tr2_ns{ns}_N97_ungapped_220k.json"), "w") as fh:
                                json.dump(mas, fh)
                    cl = core_losses(mag["core"], mag["coil"], f, t, v, lm_mkf)
                    c["core"] = cl
                    if "winding_loss_W" in c and isinstance(cl.get("IGSE"), float):
                        ptot = c["winding_loss_W"] + cl["IGSE"]
                        c["P_total_W"] = ptot
                        try:
                            c["T_mkf_core_Rth_total_at_40C_amb"] = P.calculate_temperature_from_core_thermal_resistance(
                                dict(mag["core"]), ptot)
                        except Exception as e:  # noqa
                            c["T_mkf_core_Rth_total_at_40C_amb"] = f"error: {e}"
                        c["dT_mclyman_25cm2_K"] = (ptot * 1e3 / 25.0) ** 0.833
                    cases[f"{mat}_{lm_lab}_{flab}"] = c
                    print(ns, mat, lm_lab, json.dumps({k: v for k, v in c.items() if k not in ("winding_loss_per",)}, default=str)[:1500])
                    if "winding_loss_per" in c:
                        print("   per", json.dumps(c["winding_loss_per"]))
        d["cases"] = cases
        res[f"ns{ns}"] = d
    save("loss", res)


if __name__ == "__main__":
    m.load()
    steps = sys.argv[1:] or ["geom", "leak", "sens", "lm", "loss"]
    for s in steps:
        t0 = time.time()
        globals()["step_" + s]()
        print(f"== {s} done in {time.time() - t0:.0f} s", flush=True)
