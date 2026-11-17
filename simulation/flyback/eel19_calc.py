#!/usr/bin/env python3
"""Hand calculations for the EEL19 transformer (EEL19_DESIGN.md section 2).

    python3 simulation/flyback/eel19_calc.py        # prints the tables, writes out/eel19_calc.json

Power budget at 10 / 15 W, peak current, Bpk (regulation limit and OCP), on / reset times
(DCM and the Tr/Tp margin to the IW1818's CC limit), gap for a ground centre leg and for a
spacer (MKF reluctance models + the classical estimate), reflected voltage, collector and
rectifier stress, copper fill. Every number that the ngspice / OpenMagnetics runs produce
(leakage, rail voltages, losses) is in eel19_results.md instead.
"""
from __future__ import annotations

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

MU0 = 4e-7 * math.pi
NP, NA5, NA15, NS15, NS5, NSHV = 104, 6, 16, 16, 6, 84
LP = 600e-6
RS = 1.0                      # R8 = R9 = 2.0 ohm in parallel
VIPK_HIGH, VOCP, VIPK_LOW = 1.00, 1.15, 0.23   # iW1819 datasheet (same family)
FMAX = 72e3
AE, VE = 23.4e-6, 1450e-9          # catalogue Ae, Ve
LE = 62.1e-3
VKNEE_A5 = 1.536 / 0.2753     # Vsense divider unchanged -> 5.58 V at the A5 knee
VF = 0.9                      # ES1x at a few hundred mA peak (average-ish)

# loads (A) on top of bleeders etc.; rail -> (V, I)
RAILS = {"15V": 15.0, "5V": 5.0, "15V_ISO_SEC": 15.0, "5V_ISOL": 5.0, "-5V_SEC": 5.0, "-80V": 80.0}
CASES = {
    "nom (5.1 W)": {"15V": 0.1, "5V": 0.1, "15V_ISO_SEC": 0.1, "5V_ISOL": 0.1, "-5V_SEC": 0.1, "-80V": 0.0034},
    "full10": {"15V": 0.2, "5V": 0.2, "15V_ISO_SEC": 0.2, "5V_ISOL": 0.2, "-5V_SEC": 0.2, "-80V": 0.0134},
    "full15": {"15V": 0.3, "5V": 0.3, "15V_ISO_SEC": 0.3, "5V_ISOL": 0.3, "-5V_SEC": 0.2, "-80V": 0.0134},
}
FIXED = {"15V": 9.5e-3 + 15 / 26.7e3 + 15 / 3.3e3,      # IW1818 + Si827x, AUX_MEAS, 3.3k preload
         "5V": 5.58 / 14.94e3 + 5 / 1e3,                 # Vsense divider, 1k preload
         "15V_ISO_SEC": 15 / 12.1e3, "5V_ISOL": 5 / 12.1e3, "-5V_SEC": 5 / 12.1e3, "-80V": 80 / 12.1e3}


def budget(loads):
    pout = sum(RAILS[r] * (loads[r] + FIXED[r]) for r in RAILS)
    prect = sum(VF * (loads[r] + FIXED[r]) for r in RAILS)
    pcu = 0.03 * pout                       # winding losses ~3 % (MKF at nom: ~1-2 %)
    pleak = 0.04 * pout                     # leakage energy to the clamp / ringing (~4 %)
    ptrans = pout + prect + pcu + pleak     # energy the magnetising inductance must deliver
    return pout, ptrans


def gaps():
    import om_model as m
    import PyOpenMagnetics as P
    m.load()
    m.use_core("EEL19")
    al = LP / NP ** 2
    out = {"AL_nH": al * 1e9}
    for kind in ("subtractive", "spacer"):
        res = {}
        for model in ("ZHANG", "PARTRIDGE", "MUEHLETHALER"):
            lo, hi = 0.05e-3, 3e-3
            for _ in range(40):                       # bisection on the gap reluctance (+ core)
                g = math.sqrt(lo * hi)
                c = m.make_core(g, kind)
                rr = [P.calculate_gap_reluctance(x, model)["reluctance"] for x in c["functionalDescription"]["gapping"]]
                rcore = LE / (MU0 * 2300 * AE)          # PC40 mu_i 2300
                L = NP ** 2 / (rr[0] + 1 / (1 / rr[1] + 1 / rr[2]) + rcore)
                if L > LP:
                    lo = g
                else:
                    hi = g
            res[model] = round(g * 1e3, 3)
        out[kind] = res
    # classical: lg = mu0 Ae N^2 / L x fringing factor F (1.5 at ~0.9 mm centre gap, 1.35 at ~0.45 mm)
    lg0 = MU0 * AE * NP ** 2 / LP
    out["ideal_centre_gap_mm_without_fringing"] = lg0 * 1e3
    out["ideal_spacer_mm_without_fringing"] = lg0 / 1.5 * 1e3
    return out


def main():
    rep = {}
    vt = VKNEE_A5 / NA5
    vor = vt * NP
    imax, iocp, imin = VIPK_HIGH / RS, VOCP / RS, VIPK_LOW / RS
    pmax = 0.5 * LP * imax ** 2 * FMAX
    rep["volts_per_turn_knee"] = vt
    rep["Vor"] = vor
    rep["Ipk_max_A"], rep["Ipk_ocp_A"], rep["Ipk_min_A"] = imax, iocp, imin
    rep["Pmax_magnetising_W"] = pmax
    rep["Bpk_at_Ipk_max_T"] = LP * imax / (NP * AE)
    rep["Bpk_at_OCP_T"] = LP * iocp / (NP * AE)
    print(f"V/turn at the knee {vt:.3f} V, Vor {vor:.1f} V; Ipk max {imax:.2f} A (VIPK(HIGH)), OCP {iocp:.2f} A, "
          f"Ipk min {imin:.2f} A; Pmax (1/2 Lp Imax^2 fmax) {pmax:.1f} W")
    print(f"Bpk at Ipk max {rep['Bpk_at_Ipk_max_T']:.3f} T, at OCP {rep['Bpk_at_OCP_T']:.3f} T (PC40 Bsat ~0.39 T at 100 degC)")
    rep["cases"] = {}
    for vin in (400.0, 325.0):
        for name, loads in CASES.items():
            pout, ptr = budget(loads)
            ipk = math.sqrt(2 * ptr / (LP * FMAX))
            ton = LP * ipk / vin
            tr = LP * ipk / vor
            tring = math.pi * math.sqrt(LP * 60e-12)          # half ring period with ~60 pF on the collector
            d = dict(pout=pout, ptrans=ptr, ipk=ipk, ipk_rel=ipk / imax, u=ptr / pmax, ton_us=ton * 1e6, tr_us=tr * 1e6,
                     tr_over_tp=tr * FMAX, t_used_us=(ton + tr + tring) * 1e6, dcm=(ton + tr + tring) < 1 / FMAX,
                     bpk=LP * ipk / (NP * AE), irms_p=ipk * math.sqrt(ton * FMAX / 3))
            rep["cases"][f"{name} @ {vin:.0f} V"] = d
            print(f"{name:>12} @ {vin:.0f} V: Pout {pout:5.2f} W, Ptrans {ptr:5.2f} W, Ipk {ipk:.3f} A ({100 * ipk / imax:.0f} % of max), "
                  f"ton {ton * 1e6:.2f} us, Tr {tr * 1e6:.2f} us, Tr/Tp {tr * FMAX:.2f}, period used {d['t_used_us']:.1f} of 13.9 us, "
                  f"Bpk {d['bpk']:.3f} T, Irms(P) {d['irms_p']:.3f} A")
    # stresses (on-time plateau; ringing on top, see the ngspice results)
    for vin in (400.0, 420.0):
        rep[f"stress_{vin:.0f}"] = s = {
            "Vcol_plateau": vin + vor,
            "D8_VR": vin * NSHV / NP + 80 + VF,
            "D4_D5_VR": vin * 16 / NP + 15 + VF,
            "D6_D29_D14_VR": vin * 6 / NP + 5 + VF,
            "Vsense_neg": -vin * NA5 / NP * 0.2753,
        }
        print(f"DC+ {vin:.0f} V: collector plateau {s['Vcol_plateau']:.0f} V (+ leakage spike), D8 V_R {s['D8_VR']:.0f} V, "
              f"D4/D5 {s['D4_D5_VR']:.0f} V, D6/D14/D29 {s['D6_D29_D14_VR']:.0f} V, VSENSE during ton {s['Vsense_neg']:.2f} V")
    g = gaps()
    rep["gap"] = g
    print(f"AL {g['AL_nH']:.1f} nH; ground centre leg (mm): {g['subtractive']}; spacer, all legs (mm): {g['spacer']}; "
          f"ideal (no fringing) centre {g['ideal_centre_gap_mm_without_fringing']:.3f} mm / spacer "
          f"{g['ideal_spacer_mm_without_fringing']:.3f} mm")
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    with open(os.path.join(HERE, "out", "eel19_calc.json"), "w") as f:
        json.dump(rep, f, indent=1)


if __name__ == "__main__":
    main()
