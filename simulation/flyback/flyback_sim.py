"""ngspice transient model of the auxiliary flyback (sheet 1: PWM2 IW1818 + TR1 EF20).

The transformer is the full coupled-inductor model of one winding option: every winding
(or winding section) is an L element with the self-inductance from MKF's inductance matrix
(om_model.analyse), and every pair is coupled by K = M_ij / sqrt(L_i L_j) from the same
matrix, so all pairwise leakage inductances are those MKF computed from the winding
geometry. Each winding has its DC resistance (MKF, 60 degC) in series.

Circuit (schematic values unless marked):
- DC+ = 400 V (design doc: nominal DC link 400 V; 325 V before the PFC runs).
- IW1818: ideal switch (Ron 0.5 ohm, assumed), emitter to R8 || R9 = 1.245 ohm, collector
  node capacitance 30 pF (BJT + winding, assumed). Peak current: on-time = Lp * Ipk / Vin
  (exact for DCM, which the converter is in at every load case here).
- Snubber D7 (S1M, slow recovery modelled with TT = 2 us) -> R72 100R -> R45 1M || C12 470p -> DC+.
- Rectifiers D4, D5, D6, D8, D14, D29: one generic ES1-class model (Vf 0.94 V at 1 A,
  0.58 V at 1 mA, TT 20 ns, Cj 10 pF; assumed from the ES1 datasheet class). The
  breakdown voltage is set high on purpose, see FLYBACK_DESIGN.md (ES1A is a 50 V part).
- Output capacitors: schematic values, electrolytic ESR 0.15 ohm (C1, C2), 1 ohm (C102),
  ceramics 5 mohm (assumed). Capacitors >= 10 uF scaled by `cscale` (default 0.1) so the
  rails settle in a few ms; the DC voltages do not depend on it (checked, see the report).
- Loads: constant-current sinks per case + the 12.1k bleeders R124/R123/R68/R67 on the
  isolated rails + IW1818 Vcc 5 mA (assumed) on the 20V rail.
- Controller (behavioural model of the IW1818 primary-side regulation): the AUX_FB node
  (D6 anode) through the divider R64 || R81 (10.83k) / R84 || R85 (4.11k) || C50 22p is
  tracked during the flyback interval and held when the magnetising ampere-turns
  sum(N_k * i_k) fall below 0.5 At (the knee, i.e. when all rectifier currents have
  ended); the held Vsense is regulated to 1.536 V (PDF note "vsense nominal = 1.536 V")
  by a PI controller. Control u in [0, 1] is the power demand: u >= 0.12 -> f = 72 kHz,
  Ipk = 0.803 A * sqrt(u) (1 V / 1.245 ohm = "Isense pk = 1V"); u < 0.12 -> Ipk fixed at
  0.28 A and the frequency falls in proportion (PFM, assumed, datasheet: "adaptive
  multi-mode PWM/PFM control"). Valley switching (QR) is not modelled; it only moves the
  start of the next cycle.
"""
from __future__ import annotations

import math
import os
import re
import subprocess
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

VSENSE_REF = 1.536
R_TOP = 1 / (1 / 39e3 + 1 / 15e3)       # R64 || R81
R_BOT = 1 / (1 / 33e3 + 1 / 4.7e3)      # R84 || R85
KDIV = R_BOT / (R_TOP + R_BOT)
RSENSE = 2.49 / 2
IMAX = 1.0 / RSENSE
FMAX = 72e3
U0 = 0.12                                # PWM/PFM boundary (assumed)
BLEED = 12.1e3

# rails: name -> (node, sign, schematic caps [(C, ESR)], bleeder)
RAILS = {
    "20V":         ("v20", +1, [(4.7e-6, 0.005), (220e-6, 0.15)], None),           # C39, C1
    "5V":          ("v5", +1, [(22e-6, 0.005), (22e-6, 0.005), (100e-6, 0.005)], None),  # C36, C6, C71
    "20V_ISO_SEC": ("vs20", +1, [(4.7e-6, 0.005), (220e-6, 0.15)], BLEED),         # C3, C2, R124
    "5V_ISOL":     ("vs5", +1, [(22e-6, 0.005), (22e-6, 0.005)], BLEED),          # C114, C115, R67
    "-5V_SEC":     ("vsn5", -1, [(4.7e-6, 0.005), (100e-6, 0.005)], BLEED),        # C44, C40, R123
    "-100V BIAS":  ("vshv", -1, [(100e-9, 0.01), (56e-6, 1.0)], BLEED),            # C45, C102, R68
}
# rectifier: rail -> (winding end node); positive rails: anode at the end node,
# negative rails: cathode at the end node
RECT = {"20V": "a1", "5V": "a3", "20V_ISO_SEC": "s10", "5V_ISOL": "s7", "-5V_SEC": "s8", "-100V BIAS": "s6"}
GROUND = {"20V": "0", "5V": "0", "20V_ISO_SEC": "iso", "5V_ISOL": "iso", "-5V_SEC": "iso", "-100V BIAS": "iso"}
NOMINAL_V = {"20V": 15.0, "5V": 5.0, "20V_ISO_SEC": 13.0, "5V_ISOL": 5.0, "-5V_SEC": 5.0, "-100V BIAS": 80.0}


def netlist(res: dict, spice_map: dict, case: dict, cscale=0.1, tstop=16e-3, twin=2e-3,
            vin=400.0, wave_file: str | None = None, ic: dict | None = None) -> str:
    names, L, N, R = res["names"], np.array(res["L"]), res["turns"], res["Rdc"]
    lp = sum(L[i][j] for i, a in enumerate(names) for j, b in enumerate(names)
             if a in ("P", "P1", "P2") and b in ("P", "P1", "P2"))
    out = [f"* flyback {res['name']} case {case['name']}"]
    out.append(f"Vin dcp 0 {vin}")
    out.append("Riso iso 0 1Meg")
    out.append("Ciso iso 0 20p")   # primary-secondary capacitance (assumed)
    # transformer
    for i, n in enumerate(names):
        d, o = spice_map[n]
        out.append(f"L{n} {d} x{n} {L[i][i]:.6e}")
        out.append(f"R{n} x{n} {o} {R[i]:.5f}")
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            k = L[i][j] / math.sqrt(L[i][i] * L[j][j])
            out.append(f"K{names[i]}_{names[j]} L{names[i]} L{names[j]} {k:.9f}")
    # switch, sense, snubber
    out += [f"Ccol col 0 30p IC={vin}",
            # switch: conductance follows the gate through a 10 ns RC (smooth for the solver)
            "Rgf gate gf 1k", "Cgf gf 0 10p",
            "Bsw col es I = v(col,es) * (2 * min(1, max(0, v(gf))) + 1e-8)",
            f"Rsense es 0 {RSENSE}",
            "D7 col sn1 DS1M", ".model DS1M D(IS=5n N=1.8 RS=0.04 CJO=15p TT=2u BV=1200)",
            "R72 sn1 sn2 100", "R45 sn2 dcp 1Meg", "C12 sn2 dcp 470p",
            ".model DES1 D(IS=2n N=1.7 RS=0.06 CJO=10p M=0.33 TT=20n BV=2000)"]
    # rectifiers, caps, loads
    for rail, (node, sign, caps, bleed) in RAILS.items():
        end, g = RECT[rail], GROUND[rail]
        if sign > 0:
            out.append(f"D_{node} {end} {node} DES1")
        else:
            out.append(f"D_{node} {node} {end} DES1")
        for ci, (c, esr) in enumerate(caps):
            cv = c * (cscale if c >= 10e-6 else 1.0)
            v0 = (ic or {}).get(rail, NOMINAL_V[rail]) * sign
            out.append(f"C_{node}{ci} {node} e_{node}{ci} {cv:.4e} IC={v0:.3f}")
            out.append(f"R_{node}{ci} e_{node}{ci} {g} {esr}")
        if bleed:
            out.append(f"Rb_{node} {node} {g} {bleed}")
        il = case["loads"].get(rail, 0.0)
        if rail == "20V":
            il += 5e-3                     # IW1818 Vcc (assumed)
        if il > 0:
            # constant current, rolled off below 20 % of nominal so start-up is clean
            vn = NOMINAL_V[rail]
            if sign > 0:
                out.append(f"BL_{node} {node} {g} I = {il} * min(1, max(0, v({node},{g}) / {0.2 * vn}))")
            else:
                out.append(f"BL_{node} {g} {node} I = {il} * min(1, max(0, v({g},{node}) / {0.2 * vn}))")
    # Vsense divider on AUX_FB (D6 anode = a3)
    out += [f"Rtop a3 vsd {R_TOP:.1f}", f"Rbot vsd 0 {R_BOT:.1f}", "C50 vsd 0 22p"]
    # magnetising ampere-turns
    terms = " + ".join(f"{N[i]}*i(L{n})" for i, n in enumerate(names))
    out.append(f"Bmmf mmf 0 V = {terms}")
    # Logic as smooth behavioural sources (stp = smooth step) charging small capacitors:
    # every state is a capacitor voltage, so the solver never sees a hard switch.
    out.append(".func stp(x, w) = 0.5 * (1 + tanh(x / w))")
    # knee flag: set while the switch is on, cleared when mmf < 0.5 At with the switch off
    out += ["Bfl 0 flag I = 1e-3 * (stp(v(gf) - 0.5, 0.05) * (1 - v(flag))"
            " - stp(0.5 - v(gf), 0.05) * stp(0.5 - v(mmf), 0.05) * v(flag))",
            "Cflag flag 0 10p IC=0",
            "Btrk trk 0 V = stp(v(flag) - 0.5, 0.01) * stp(0.2 - v(gf), 0.01)",
            "Bsh 0 hold I = 1e-2 * v(trk) * (v(vsd) - v(hold))",
            f"Chold hold 0 100p IC={VSENSE_REF}"]
    # PI controller (time constants chosen for a stable loop with the scaled caps)
    kp, ki = case.get("kp", 2.0), case.get("ki", 2000.0)
    u0 = case.get("u0", 0.4)
    out += [f"Bint 0 ui I = 1e-6 * {ki} * ({VSENSE_REF} - v(hold))",
            f"Cint ui 0 1e-6 IC={u0:.4f}", "Rint ui 0 1e9",
            f"Bu u 0 V = min(1, max(0.004, v(ui) + {kp} * ({VSENSE_REF} - v(hold))))",
            # u is latched once per cycle (during the oscillator reset pulse), as a digital
            # controller would: the on-time cannot interact with the sampling
            "Bul 0 ul I = 1.0 * stp(v(q) - 0.5, 0.005) * (v(u) - v(ul))", f"Cul ul 0 1n IC={u0:.4f}",
            f"Bf fsw 0 V = v(ul) >= {U0} ? {FMAX} : {FMAX} * v(ul) / {U0}",
            f"Bipk ipk 0 V = v(ul) >= {U0} ? {IMAX} * sqrt(v(ul)) : {IMAX * math.sqrt(U0)}",
            f"Bd duty 0 V = min(0.6, {lp:.6e} * v(ipk) / {vin} * v(fsw))",
            # oscillator: ramp 0.01 -> 0.99 at 0.98 V per period, reset (q = 1) with hysteresis
            "Bph 0 ph I = 0.98e-9 * v(fsw) - 0.1 * stp(v(q) - 0.5, 0.005) * v(ph)", "Cph ph 0 1n IC=0.5",
            "Bqr qr 0 V = stp(v(ph) - 0.99 + 0.98 * min(1, max(0, v(q))), 1m)",   # Schmitt: threshold falls as q rises
            "Rq qr q 1k", "Cq q 0 2p IC=0",
            "Bgate gate 0 V = stp(v(ph) - 0.012, 1m) * stp(0.98 * v(duty) - (v(ph) - 0.01), 1m) * stp(0.5 - v(q), 0.005)"]
    t0 = tstop - twin
    tstep = 10e-9
    meas = []
    for rail, (node, sign, caps, bleed) in RAILS.items():
        g = GROUND[rail]
        expr = f"vr_{node}"
        meas.append(f"meas tran V_{node} avg {expr} from={t0} to={tstop}")
        meas.append(f"meas tran V1_{node} avg {expr} from={t0} to={t0 + twin / 2}")
        meas.append(f"meas tran V2_{node} avg {expr} from={t0 + twin / 2} to={tstop}")
    meas += [f"meas tran VCOL max v(col) from={t0} to={tstop}",
             f"meas tran VCLAMP avg vclamp from={t0} to={tstop}",
             f"meas tran U avg v(ul) from={t0} to={tstop}",
             f"meas tran UMIN min v(ul) from={t0} to={tstop}",
             f"meas tran UMAX max v(ul) from={t0} to={tstop}",
             f"meas tran HOLD avg v(hold) from={t0} to={tstop}",
             f"meas tran FSW avg v(fsw) from={t0} to={tstop}",
             f"meas tran IPK avg v(ipk) from={t0} to={tstop}",
             f"meas tran PIN avg pin from={t0} to={tstop}",
             f"meas tran PR45 avg pr45 from={t0} to={tstop}"]
    out.append(".options method=gear reltol=1e-3 abstol=1e-9 vntol=1e-5 itl4=50")
    out.append(".control")
    sv = ["v(col)", "v(sn2)", "v(dcp)", "v(u)", "v(ul)", "v(hold)", "v(fsw)", "v(ipk)", "v(vsd)", "v(a3)", "i(Vin)", "v(gate)"]
    sv += [f"v({RAILS[r][0]})" for r in RAILS] + ["v(iso)"]
    sv += [f"i(L{n})" for n in names]
    out.append("save " + " ".join(sv))
    out.append(f"tran {tstep} {tstop} {t0} {tstep} uic")
    out += ["let pin = -v(dcp)*i(vin)", "let vclamp = v(sn2)-v(dcp)", "let pr45 = vclamp*vclamp/1e6"]
    for rail, (node, sign, caps, bleed) in RAILS.items():
        g = "0" if GROUND[rail] == "0" else "v(iso)"
        out.append(f"let vr_{node} = v({node})-{g}" if sign > 0 else f"let vr_{node} = {g}-v({node})")
    out += meas
    if wave_file:
        # one switching period of every winding current at the end, for MKF losses
        out.append("linearize " + " ".join(f"i(L{n})" for n in names) + " v(col) v(gate)")
        out.append(f"wrdata {wave_file} " + " ".join(f"i(L{n})" for n in names) + " v(col) v(gate)")
    out.append(".endc")
    out.append(".end")
    return "\n".join(out) + "\n"


def run(net: str, tag: str) -> dict:
    os.makedirs(os.path.join(OUT, "spice"), exist_ok=True)
    path = os.path.join(OUT, "spice", f"{tag}.cir")
    with open(path, "w") as f:
        f.write(net)
    ng = os.environ.get("NGSPICE", "ngspice")
    p = subprocess.run([ng, "-b", path], capture_output=True, text=True, timeout=3600)
    log = p.stdout + p.stderr
    with open(path[:-4] + ".log", "w") as f:
        f.write(log)
    vals = {}
    for m in re.finditer(r"^(\w+)\s*=\s*([-+0-9.eE]+)", log, re.M):
        vals[m.group(1).lower()] = float(m.group(2))
    if not vals:
        raise RuntimeError(f"ngspice produced no measurements, see {path[:-4]}.log")
    return vals


def summarise(vals: dict) -> dict:
    r = {}
    for rail, (node, *_rest) in RAILS.items():
        r[rail] = vals.get(f"v_{node}")
        r[rail + " drift"] = vals.get(f"v2_{node}", 0) - vals.get(f"v1_{node}", 0)
    for k in ("vcol", "vclamp", "u", "umin", "umax", "hold", "fsw", "ipk", "pin", "pr45"):
        r[k] = vals.get(k)
    return r
