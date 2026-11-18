"""ngspice switching model of the 5.2 DAB (dual half bridge) with the new TR3 (option B 20:21,
TIW-litz secondary).

    python3 simulation/dab/dab_spice.py --only full,load,mismatch,lm,shunt,startup,coss,scan,scan2,scanlm,lm200
        (all studies ~2.5 h with 2 ngspice processes, ~12 MB each; results are merged into
        out/spice_results.json, so studies can be run one by one)
    python3 simulation/dab/dab_spice.py --report  # out/spice_results.md from the JSON
See DAB_SIMULATION.md for the results.

Circuit (kicad_next/tube_psu_5_2.kicad_sch, sheets 02 / 07 / 08, read via kicad-cli netlist):
  primary   Q19 (high, DC+ -> DHB_HI_SOURCE) / Q7 (low, -> DHB_CURRENT), split caps C47 / C54 1 uF
            (DC+ / DHB_CAP / DHB_CURRENT), C67 + C70 100 nF DC+ -> DHB_CURRENT, R83 4 mOhm
            DHB_CURRENT -> GND (+ ESL). Bus: 400 V PFC bulk behind ESR + ESL/trace.
  secondary Q21 (high, 420V -> DHB_HI_SOURCE_SEC) / Q8 (low, -> ISO_GND), split caps C16 / C55
            1 uF, 6 x 100 nF + C19 / C30 68 uF on 420V. Load: constant voltage (420 V source).
  TR3       coupled inductors from the OpenMagnetics run (mas/tr3_dab_B_42uH_TIW.json /
            out/results_tiw.json): Lm 307 uH (gap 0.34 mm), Lsc 40.4 uH primary-referred, split
            47.4 % primary, n = 21/20, R_ac(140 kHz) 70 / 74 mOhm (MKF Pcu with the real
            currents), core loss as 24 kOhm across the primary (1.5 W), winding self-capacitance
            from MKF (Albach) 5 / 7 pF, interwinding 2 x 1.5 pF (hand estimate, 5 mm divider).
  gates     UCC21520 as ideal PWM, 1 Ohm output, 15 V (low side) / 14.2 V (bootstrap high side),
            R90/R26/R57/R87 40R on, || 3.3R + ZLLS400 off, 10k gate pull-down, RG(int) 7.2 Ohm.
  MOSFET    STF7N60M2 (ST DocID024894: ST's own SPICE model could not be downloaded, st.com
            blocks scripted access): level-1 channel (Vth 3 V, Kp 2.5 A/V^2) + drift R
            (R_on 1.3 Ohm at Tj ~ 75 C), Coss / Crss as charge tables digitised from Fig. 8,
            Coss below 50 V scaled so that Q(0..480 V) = Co(tr) 75.5 pF x 480 V (the small-
            signal curve alone gives 46 pF), Cgs 260 pF, body diode Vsd/trr/Qrr per Table 8.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import struct
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dab_wave as dw  # noqa: E402

OUT = os.path.join(HERE, "out")

# ---------------------------------------------------------------- parameters
F_SW = 140e3
N_RATIO = 21 / 20
LSC = 40.44e-6
LM = 307e-6
SPLIT = 0.474
R_W = (0.070, 0.074)          # winding R_ac at 140 kHz (MKF Pcu / Irms^2)
R_CORE = 24e3
C_SELF = (5e-12, 7e-12)
C_IW = 1.5e-12                 # interwinding, per end (2 x)
C_NODE = 10e-12                # layout per switch node (5 pF to each rail)
C_SPLIT = 1e-6
ESR_SPLIT, ESL_SPLIT = 15e-3, 8e-9
R_SHUNT = 4e-3
VTH = 3.0
R_ON = 1.3
VG_LO, VG_HI = 15.0, 14.2

# STF7N60M2 Fig. 8, typical (V, pF)
COSS_PTS = [(0.1, 2200), (0.3, 2000), (1, 1600), (2, 1300), (5, 900), (8, 750), (10, 600),
            (15, 250), (20, 150), (30, 100), (40, 65), (50, 38), (70, 28), (100, 16), (200, 14),
            (300, 12), (500, 11), (600, 10.5)]
CRSS_PTS = [(0.1, 200), (1, 150), (5, 80), (10, 40), (20, 5), (30, 2.5), (50, 1.1), (100, 0.7),
            (600, 0.7)]
COTR = 75.5e-12


def _curve(pts, v):
    lv = np.log10([p[0] for p in pts])
    lc = np.log10([p[1] for p in pts])
    return 10 ** np.interp(np.log10(np.clip(v, pts[0][0], pts[-1][0])), lv, lc) * 1e-12


def cap_tables(scale_to_cotr=True):
    """Charge tables (V, Q[nC]) for Cds (= Coss - Crss) and Cgd (= Crss)."""
    v = np.concatenate([[0.0], np.logspace(-1, math.log10(600), 160)])
    coss = _curve(COSS_PTS, v)
    crss = _curve(CRSS_PTS, v) * np.where(v < 30, 2.8, 1.0)   # Qgd 4.3 nC (Table 6)
    if scale_to_cotr:
        q480 = np.trapezoid(coss[v <= 480], v[v <= 480])
        lo = v < 50
        qlo = np.trapezoid(coss[lo], v[lo])
        k = 1 + (COTR * 480 - q480) / qlo
        coss = np.where(lo, coss * k, coss)
    cds = np.maximum(coss - crss, 5e-12)

    def q(c):
        qq = np.concatenate([[0.0], np.cumsum(0.5 * (c[1:] + c[:-1]) * np.diff(v))])
        # negative side: constant C (junction, diode conducts there anyway); far positive linear
        vv = np.concatenate([[-50.0], v, [5000.0]])
        qq = np.concatenate([[-50 * c[0]], qq, [qq[-1] + (5000 - 600) * c[-1]]])
        return vv, qq * 1e9
    t = {"ds": q(cds), "gd": q(crss), "coss": (v, coss), "crss": (v, crss)}
    t["fit"] = fit_smooth(t)
    return t


def _lor(p, v):
    out = p[0] * np.ones_like(v)
    for i in range(3):
        out = out + p[1 + 2 * i] / (1 + (v / p[2 + 2 * i]) ** 2)
    return out


def fit_smooth(tabs):
    """Smooth charge functions (continuous derivatives: the table pwl made ngspice fail at hard
    commutations): C(v) = C0 + sum A_i / (1 + (v/v_i)^2)  ->  Q(v) = C0 v + sum A_i v_i atan(v/v_i),
    fitted in log space to the tables above, then scaled so that Q(480 V) equals the table."""
    from scipy.optimize import least_squares
    out = {}
    for key, ckey in (("ds", "coss"), ("gd", "crss")):
        v, c = tabs[ckey]
        if key == "ds":
            c = np.maximum(c - tabs["crss"][1], 5e-12)
        m = v > 0.09
        sc = np.array([1e-12, 1e-12, 1, 1e-12, 1, 1e-12, 1])
        p0 = np.array([c[-1], c[0] * 0.4, 1, c[0] * 0.4, 8, c[0] * 0.05, 40]) / sc
        lo = np.array([1e-13, 0, 0.3, 0, 0.3, 0, 0.3]) / sc
        hi = np.array([1e-10, 1e-8, 300, 1e-8, 300, 1e-8, 300]) / sc
        r = least_squares(lambda q: np.log(_lor(q * sc, v[m])) - np.log(c[m]), p0, bounds=(lo, hi))
        p = r.x * sc
        x = np.linspace(0, 480, 20001)
        q480 = np.trapezoid(_lor(p, x), x)
        qt = np.interp(480, *tabs[key]) * 1e-9
        p[1::2] *= (qt - p[0] * 480) / (q480 - p[0] * 480)
        out[key] = p
    return out


def q_expr(p, vexpr):
    """ngspice expression for Q in nC."""
    terms = [f"{p[0]*1e9:.6g}*({vexpr})"]
    for i in range(3):
        a, vk = p[1 + 2 * i], p[2 + 2 * i]
        if a > 0:
            terms.append(f"{a*vk*1e9:.6g}*atan(({vexpr})/{vk:.6g})")
    return " + ".join(terms)


def q_eval(p, v):
    return 1e9 * (p[0] * v + sum(p[1 + 2 * i] * p[2 + 2 * i] * math.atan(v / p[2 + 2 * i]) for i in range(3)))


def qtab_eval(tab, x):
    return float(np.interp(x, tab[0], tab[1]))


def pwl_str(tab):
    return ", ".join(f"{a:.6g},{b:.6g}" for a, b in zip(*tab))


# ---------------------------------------------------------------- netlist
MODELS = """
.model NCH nmos level=1 vto={vth} kp=2.5 lambda=0.002
.model DBODY d is=2e-10 n=1.4 rs=0.06 tt=250n bv=650
.model DSCH d is=2e-6 n=1.05 rs=0.3
"""


def mosfet(name, d, s, drv, vg, ton, toff, T, on0, tabs, ic):
    """Flat MOSFET + gate network. drv pulse: on edge at ton, off edge at toff (mod T)."""
    p = name
    tr = 10e-9     # driver edge (5 ns made ngspice fail with the body-diode TT)
    if vg == 0:
        src = "DC 0"
    elif on0:   # on at t = 0: start high, first edge = off
        td = toff % T
        pw = (ton - toff) % T - tr
        src = f"PULSE({vg} 0 {td:.6e} {tr} {tr} {pw:.6e} {T:.6e})"
    else:
        td = ton % T
        pw = (toff - ton) % T - tr
        src = f"PULSE(0 {vg} {td:.6e} {tr} {tr} {pw:.6e} {T:.6e})"
    vgs0 = vg if on0 else 0.0
    vds0 = ic["vds"]
    lines = [
        f"* --- {name}",
        f"V{p}drv {p}_drv {s} {src}",
        f"R{p}drv {p}_drv {p}_d1 1",
        f"R{p}on {p}_d1 {p}_ge 40",
        f"R{p}off {p}_ge {p}_da 3.3",
        f"D{p}off {p}_da {p}_d1 DSCH",
        f"R{p}pd {p}_ge {s} 10k",
        f"R{p}gi {p}_ge {p}_g 7.2",
        f"C{p}gs {p}_g {s} 260p ic={vgs0}",
        f"R{p}dr {d} {p}_dx {R_ON - 1 / (2.5 * (VG_LO - VTH)):.4f}",
        f"V{p}ich {p}_dx {p}_di 0",
        f"M{p} {p}_di {p}_g {s} {s} NCH",
        f"V{p}idi {s} {p}_ka 0",
        f"D{p}b {p}_ka {d} DBODY",
        # Cds charge table
        f"B{p}qds {p}_qds 0 V={q_expr(tabs['fit']['ds'], f'v({d},{s})')}",
        f"V{p}sds {p}_qds {p}_xds 0",
        f"C{p}qds {p}_xds 0 1n ic={q_eval(tabs['fit']['ds'], vds0):.6g}",
        f"F{p}ds {d} {s} V{p}sds 1",
        # Cgd charge table
        f"B{p}qgd {p}_qgd 0 V={q_expr(tabs['fit']['gd'], f'v({d},{p}_g)')}",
        f"V{p}sgd {p}_qgd {p}_xgd 0",
        f"C{p}qgd {p}_xgd 0 1n ic={q_eval(tabs['fit']['gd'], vds0 - vgs0):.6g}",
        f"F{p}gd {d} {p}_g V{p}sgd 1",
    ]
    return "\n".join(lines)


def initial_state(cfg):
    """Steady state of the ideal circuit (dab_wave) at the sim start t0 (an instant far from
    every edge). Returns t0 (in waveform time, 0 = primary high-side command on) and states."""
    T = 1 / cfg["f"]
    v1, v2 = cfg["V1"] / 2, cfg["V2"] / 2
    L = dw.coupled_L(cfg["Lsc"], cfg["Lm"], N_RATIO, SPLIT)
    R = (R_W[0] + R_ON + ESR_SPLIT, R_W[1] + R_ON + ESR_SPLIT)
    w = dw.waveform(L, cfg["f"], cfg["phi"], V1=v1, V2=v2, R=R, C=(2 * C_SPLIT, 2 * C_SPLIT), npts=1440)
    td = (cfg["phi"] % 360) / 360 * T
    edges = np.array([0, T / 2, td % T, (td + T / 2) % T, T])
    cand = np.linspace(0, T, 721)[:-1]
    dist = np.min(np.abs(((cand[:, None] - edges[None, :]) + T / 2) % T - T / 2), axis=1)
    t0 = cand[np.argmax(dist)]
    k = np.argmin(np.abs(w["t"] - t0))
    pri_hi = (t0 % T) < T / 2
    sec_hi = ((t0 - td) % T) < T / 2
    return t0, dict(i1=w["i1"][k], i2=w["i2"][k], vc1=w["vc1"][k], vc2=w["vc2"][k],
                    pri_hi=pri_hi, sec_hi=sec_hi, td=td)


def netlist(cfg, tabs, rawfile):
    T = 1 / cfg["f"]
    V1, V2 = cfg["V1"], cfg["V2"]
    dt = cfg["dt"]
    t0, s = initial_state(cfg)
    td = s["td"]
    # gate commands in waveform time; shifted so that sim t = 0 <-> waveform t0
    sh = lambda t: (t - t0) % T
    P_est = cfg.get("P_est", 0.0)
    idc1 = P_est / V1
    idc2 = -P_est / V2
    l1 = cfg["Lm"] + SPLIT * cfg["Lsc"]
    l2 = N_RATIO ** 2 * (cfg["Lm"] + (1 - SPLIT) * cfg["Lsc"])
    k = N_RATIO * cfg["Lm"] / math.sqrt(l1 * l2)
    vmid1 = V1 / 2 + s["vc1"]
    vmid2 = V2 / 2 + s["vc2"]
    sw1 = V1 if s["pri_hi"] else 0.0
    sw2 = cfg.get("V2_0", V2) if s["sec_hi"] else 0.0
    c47 = cfg.get("c47", C_SPLIT)
    c54 = cfg.get("c54", C_SPLIT)
    vmid1_ic = cfg.get("vmid1_ic", vmid1)
    sub = []
    a = sub.append
    a(f"* DAB 5.2 switching model, phi = {cfg['phi']:.3f} deg, DT = {dt*1e9:.0f} ns")
    a(MODELS.format(vth=VTH))
    # ---- primary bus and shunt
    a(f"Vbus bus_src 0 {V1}")
    a(f"Rbus bus_src bus_a {cfg.get('Rbus', 0.1)}")
    a(f"Lbus bus_a dcp {cfg.get('Lbus', 60e-9)} ic={idc1}")
    a(f"Rsh dcur sh_a {R_SHUNT}")
    a(f"Lsh sh_a 0 {cfg['esl']} ic={idc1}")
    a("Cdec dcp dec_a 200n ic=" + f"{V1}")
    a("Rdec dec_a dec_b 5m")
    a("Ldec dec_b dcur 2n ic=0")
    a(f"C47 dcp c47a {c47} ic={V1 - vmid1_ic}")
    a(f"R47 c47a c47b {ESR_SPLIT}")
    a(f"L47 c47b capp {ESL_SPLIT} ic=0")
    a(f"C54 capp c54a {c54} ic={vmid1_ic}")
    a(f"R54 c54a c54b {ESR_SPLIT}")
    a(f"L54 c54b dcur {ESL_SPLIT} ic=0")
    a(f"Cn1a swp dcp {C_NODE/2} ic={sw1 - V1}")
    a(f"Cn1b swp dcur {C_NODE/2} ic={sw1}")
    # ---- secondary
    if cfg.get("startup"):
        a(f"Cbulk p420 bulk_a 136u ic={cfg['V2_0']}")
        a("Rbulk bulk_a iso 0.15")
        if cfg.get("Rload"):
            a(f"Rload p420 iso {cfg['Rload']}")
    else:
        a(f"Vout out_src iso {V2}")
        a(f"Rout out_src out_a {cfg.get('Rout', 0.05)}")
        a(f"Lout out_a p420 50n ic={idc2}")
    v2_0 = cfg.get("V2_0", V2)
    a(f"Cdec2 p420 dec2_a 600n ic={v2_0}")
    a("Rdec2 dec2_a dec2_b 3m")
    a("Ldec2 dec2_b iso 2n ic=0")
    vmid2_ic = cfg.get("vmid2_ic", vmid2)
    a(f"C16 p420 c16a {cfg.get('c16', C_SPLIT)} ic={v2_0 - vmid2_ic}")
    a(f"R16 c16a c16b {ESR_SPLIT}")
    a(f"L16 c16b caps {ESL_SPLIT} ic=0")
    a(f"C55 caps c55a {cfg.get('c55', C_SPLIT)} ic={vmid2_ic}")
    a(f"R55 c55a c55b {ESR_SPLIT}")
    a(f"L55 c55b iso {ESL_SPLIT} ic=0")
    a(f"Cn2a sws p420 {C_NODE/2} ic={sw2 - v2_0}")
    a(f"Cn2b sws iso {C_NODE/2} ic={sw2}")
    a(f"Riso iso 0 {cfg.get('riso', 10e3)}")
    # ---- transformer: dot at the bridge midpoint on both windings
    i1_0 = cfg.get("i1_ic", s["i1"])
    i2_0 = cfg.get("i2_ic", s["i2"])
    a(f"Rw1 swp w1a {R_W[0]}")
    a(f"Vi1 w1a w1b 0")
    a(f"L1 w1b capp {l1} ic={i1_0}")
    a(f"Rw2 sws w2a {R_W[1]}")
    a(f"Vi2 w2a w2b 0")
    a(f"L2 w2b caps {l2} ic={i2_0}")
    a(f"K12 L1 L2 {k:.9f}")
    a(f"Rcore swp capp {R_CORE}")
    a(f"Cs1 swp capp {C_SELF[0]} ic={sw1 - vmid1_ic}")
    a(f"Cs2 sws caps {C_SELF[1]} ic={sw2 - vmid2_ic}")
    a(f"Ciw1 swp sws {C_IW} ic={sw1 - sw2}")
    a(f"Ciw2 capp caps {C_IW} ic={vmid1_ic - vmid2_ic}")
    # ---- switches. Primary: high on [dt, T/2), low on [T/2 + dt, T). Secondary delayed by td.
    sd = cfg.get("dt_sec", dt)
    td = td + 0.1e-9    # ngspice: nearly coincident pulse breakpoints of the two bridges -> timestep too small
    p_hi, p_lo = s["pri_hi"], not s["pri_hi"]
    q_hi, q_lo = s["sec_hi"], not s["sec_hi"]
    a(mosfet("Q19", "dcp", "swp", None, VG_HI, sh(dt), sh(T / 2), T, p_hi, tabs, {"vds": V1 - sw1}))
    a(mosfet("Q7", "swp", "dcur", None, VG_LO, sh(T / 2 + dt), sh(0), T, p_lo, tabs, {"vds": sw1}))
    if cfg.get("sec_off"):
        # secondary gates held off (diode rectifier), e.g. start-up
        a(mosfet("Q21", "p420", "sws", None, 0.0, sh(td + sd), sh(td + T / 2), T, False, tabs, {"vds": v2_0 - sw2}))
        a(mosfet("Q8", "sws", "iso", None, 0.0, sh(td + T / 2 + sd), sh(td), T, False, tabs, {"vds": sw2}))
    else:
        a(mosfet("Q21", "p420", "sws", None, VG_HI, sh(td + sd), sh(td + T / 2), T, q_hi, tabs, {"vds": v2_0 - sw2}))
        a(mosfet("Q8", "sws", "iso", None, VG_LO, sh(td + T / 2 + sd), sh(td), T, q_lo, tabs, {"vds": sw2}))
    # ---- DHB_I amplifier (sheet 08, U1B LMH6643): 330R / 15k || 12p both legs, 33R out
    a("Vbias bias 0 1.65")
    a("R104 dcur ap 330")
    a("R105 ap bias 15k")
    a("C122 ap bias 12p")
    a("R101 0 an 330")
    a("R102 an aout 15k")
    a("C63 an aout 12p")
    a("Gop 0 opi ap an 1")                     # Aol 1e5, GBW 57 MHz
    a("Rop opi 0 1e5")
    a(f"Cop opi 0 {1 / (2 * math.pi * 57e6):.4e}")
    a("Bop aout 0 V=max(0.04, min(3.26, v(opi)))")
    # ---- analysis
    ncyc = cfg["ncyc"]
    nsave = cfg.get("nsave", 2)
    tstop = ncyc * T
    tsave = (ncyc - nsave) * T
    a(".options method=gear reltol=1e-3 abstol=1e-7 vntol=1e-4 chgtol=1e-15 itl4=200 maxord=2 rshunt=1e9")
    a(f".tran {cfg.get('tstep', 0.2e-9):.3e} {tstop:.6e} {tsave:.6e} {cfg.get('tmax', 1e-9):.3e} uic")
    vecs = ["v(dcp)", "v(swp)", "v(capp)", "v(dcur)", "v(p420)", "v(sws)", "v(caps)", "v(iso)",
            "i(vi1)", "i(vi2)", "i(lsh)", "i(vbus)", "v(aout)", "v(bias)"]
    if not cfg.get("startup"):
        vecs.append("i(vout)")
    for q, s_ in (("q19", "swp"), ("q7", "dcur"), ("q21", "sws"), ("q8", "iso")):
        vecs += [f"v({q}_g)", f"i(v{q}ich)", f"i(v{q}idi)"]
    a(".save " + " ".join(vecs))
    a(".control")
    a("set filetype=binary")
    a("run")
    a(f"write {rawfile} " + " ".join(vecs))
    a("quit")
    a(".endc")
    a(".end")
    # optional damping of the parasitic nH inductors (cfg rpar; off by default: with uic it
    # made the start fail)
    extra = []
    for ln in sub:
        f_ = ln.split()
        if cfg.get("rpar") and f_ and f_[0][0] == "L" and f_[0] not in ("L1", "L2"):
            try:
                val = float(f_[3])
            except ValueError:
                continue
            if val < 200e-9:
                extra.append(f"Rp{f_[0]} {f_[1]} {f_[2]} {cfg['rpar']}")
    idx = sub.index(".save " + " ".join(vecs))
    sub[idx:idx] = extra
    meta = dict(t0=t0, td=td, T=T, tsave=tsave, ncyc=ncyc)
    return "\n".join(sub) + "\n", meta


# ---------------------------------------------------------------- raw reader
def read_raw(path):
    with open(path, "rb") as f:
        data = f.read()
    hdr_end = data.index(b"Binary:\n") + len(b"Binary:\n")
    hdr = data[:hdr_end].decode("latin1").splitlines()
    nvar = npts = 0
    names = []
    for i, ln in enumerate(hdr):
        if ln.startswith("No. Variables:"):
            nvar = int(ln.split(":")[1])
        elif ln.startswith("No. Points:"):
            npts = int(ln.split(":")[1])
        elif ln.startswith("Variables:"):
            for j in range(nvar):
                names.append(hdr[i + 1 + j].split()[1].lower())
    arr = np.frombuffer(data[hdr_end:hdr_end + 8 * nvar * npts], dtype="<f8").reshape(npts, nvar)
    return {n: arr[:, k].copy() for k, n in enumerate(names)}


def run_case(cfg, tabs):
    """ngspice with uic is touchy at the very first steps (timestep too small at ~2 ps for some
    initial states): retry with a smaller initial step, then with a tiny phase / timing change."""
    tries = [{}, {"tstep": 0.02e-9}, {"tstep": 0.05e-9, "phi": cfg["phi"] + 1e-3}, {"tstep": 0.01e-9, "tmax": 0.5e-9}]
    err = None
    for t_ in tries:
        try:
            return _run_case(dict(cfg, **t_), tabs)
        except RuntimeError as e:
            err = e
    raise err


def _run_case(cfg, tabs):
    with tempfile.TemporaryDirectory(dir=cfg.get("tmp")) as td_:
        raw = os.path.join(td_, "o.raw")
        net, meta = netlist(cfg, tabs, raw)
        cir = os.path.join(td_, "c.cir")
        with open(cir, "w") as f:
            f.write(net)
        r = subprocess.run(["ngspice", "-b", cir], capture_output=True, text=True, timeout=3600)
        if not os.path.exists(raw):
            raise RuntimeError("ngspice failed:\n" + r.stdout[-3000:] + r.stderr[-2000:])
        d = read_raw(raw)
    tend = meta["ncyc"] * meta["T"]
    if d["time"][-1] < tend * (1 - 1e-6):
        msg = [ln for ln in r.stdout.splitlines() + r.stderr.splitlines() if "too small" in ln or "rror" in ln]
        raise RuntimeError(f"ngspice stopped at {d['time'][-1]*1e6:.2f} us of {tend*1e6:.2f}: " + " | ".join(msg[:3]))
    return d, meta


# ---------------------------------------------------------------- post-processing
def _mean(t, y):
    return float(np.trapezoid(y, t) / (t[-1] - t[0]))


def _rms(t, y):
    return math.sqrt(_mean(t, y * y))


def cross(t, y, level, rising=True, after=None):
    yy = y - level
    idx = np.where((yy[:-1] < 0) & (yy[1:] >= 0))[0] if rising else np.where((yy[:-1] > 0) & (yy[1:] <= 0))[0]
    out = []
    for i in idx:
        tc = t[i] + (t[i + 1] - t[i]) * (-yy[i]) / (yy[i + 1] - yy[i])
        if after is None or tc >= after:
            out.append(tc)
    return out


SW = {  # name: (drain node, source node, gate vec)
    "Q19": ("dcp", "swp"), "Q7": ("swp", "dcur"), "Q21": ("p420", "sws"), "Q8": ("sws", "iso")}


def analyse(d, meta, cfg):
    t = d["time"]
    T = meta["T"]
    # use exactly the last full period
    tb = t[-1] - T
    m = t >= tb - 1e-12
    tt = t[m]
    g = {k: v[m] for k, v in d.items()}
    V1, V2 = cfg["V1"], cfg["V2"]
    res = {}
    p_in = _mean(tt, -g["i(vbus)"] * V1)        # ngspice: source current flows + -> - inside
    res["P_in"] = p_in
    if "i(vout)" in g:
        res["P_out"] = _mean(tt, g["i(vout)"] * V2)   # power absorbed by the 420 V source
    i1, i2 = g["i(vi1)"], g["i(vi2)"]
    res.update(I1rms=_rms(tt, i1), I1pk=float(np.max(np.abs(i1))), I2rms=_rms(tt, i2),
               I2pk=float(np.max(np.abs(i2))))
    im = i1 + N_RATIO * i2
    res["Im_pk"] = float(np.max(np.abs(im - im.mean())))
    res["Im_dc"] = float(_mean(tt, im))
    vw1 = g["v(swp)"] - g["v(capp)"]
    vw2 = g["v(sws)"] - g["v(caps)"]
    res.update(Vw1_pk=float(np.max(np.abs(vw1))), Vw2_pk=float(np.max(np.abs(vw2))))
    res["Vmid1_avg"] = _mean(tt, g["v(capp)"] - g["v(dcur)"])
    res["Vmid2_avg"] = _mean(tt, g["v(caps)"] - g["v(iso)"])
    res["Vcap1_pp"] = float(np.ptp(g["v(capp)"] - g["v(dcur)"]))
    res["Vcap2_pp"] = float(np.ptp(g["v(caps)"] - g["v(iso)"]))
    # interwinding (hot ends, GND = ISO_GND at DC)
    res["Vpri_sec_pk"] = float(np.max(np.abs(g["v(swp)"] - g["v(sws)"])))
    dv1 = np.diff(g["v(swp)"]) / np.diff(tt)
    dv2 = np.diff(g["v(sws)"]) / np.diff(tt)
    res["dvdt1_max"] = float(np.max(np.abs(dv1))) * 1e-9   # V/ns
    res["dvdt2_max"] = float(np.max(np.abs(dv2))) * 1e-9
    sw = {}
    for q, (dn, sn) in SW.items():
        ql = q.lower()
        vds = g[f"v({dn})"] - g[f"v({sn})"]
        vgs = g[f"v({ql}_g)"] - g[f"v({sn})"]
        ich = g[f"i(v{ql}ich)"]
        idi = g[f"i(v{ql}idi)"]
        vdc = V1 if q in ("Q19", "Q7") else V2
        r = {}
        on = cross(tt, vgs, VTH, True)
        off = cross(tt, vgs, VTH, False)
        if on:
            ton = on[0]
            r["vds_on"] = float(np.interp(ton, tt, vds))
            r["id_on"] = float(np.interp(ton, tt, ich - idi))   # drain->source current at turn-on
            # turn-on energy: vds*ich over [ton - 5 ns, ton + 80 ns]
            w = (tt >= ton - 5e-9) & (tt <= ton + 80e-9)
            r["Eon_uJ"] = float(np.trapezoid(np.clip(vds[w], 0, None) * ich[w], tt[w])) * 1e6
        vg = VG_HI if q in ("Q19", "Q21") else VG_LO
        offs = cross(tt, vgs, 0.9 * vg, False)
        if off and offs:
            toff = off[0]
            t_cmd = max([x for x in offs if x <= toff] or [offs[0]])
            r["id_off"] = float(np.interp(t_cmd, tt, ich - idi))   # drain->source at the off command
            # turn-off energy: from the start of the gate fall over the dead time
            w = (tt >= t_cmd) & (tt <= t_cmd + cfg["dt"])
            r["Eoff_uJ"] = float(np.trapezoid(np.clip(vds[w], 0, None) * np.clip(ich[w], 0, None), tt[w])) * 1e6
            # node transition: time from Vth (off) until this switch's Vds reaches 95 % of Vdc
            c = cross(tt, vds, 0.95 * vdc, True, after=toff)
            r["t_swing_ns"] = (c[0] - toff) * 1e9 if c and c[0] - toff < T / 4 else None
        r["Pch"] = _mean(tt, vds * ich)
        r["Pdiode"] = _mean(tt, -vds * idi) if True else 0.0
        r["Ich_rms"] = _rms(tt, ich)
        sw[q] = r
    res["sw"] = sw
    # shunt / amplifier
    ish = g["i(lsh)"]           # current dcur -> GND through R83 (+ESL)
    vsh = g["v(dcur)"]
    aout = g["v(aout)"] - g["v(bias)"]
    gain = R_SHUNT * 15e3 / 330
    res["shunt"] = dict(I_avg=_mean(tt, ish), I_pp=float(np.ptp(ish)), I_rms=_rms(tt, ish),
                        Vsh_pp_mV=float(np.ptp(vsh)) * 1e3, Vsh_ideal_pp_mV=float(np.ptp(ish)) * R_SHUNT * 1e3,
                        Iamp_avg=_mean(tt, aout) / gain, Iamp_pp=float(np.ptp(aout)) / gain,
                        Iamp_err_max=float(np.max(np.abs(aout / gain - ish))))
    return res, (tt, g)


# ---------------------------------------------------------------- studies
def base_cfg(**kw):
    c = dict(f=F_SW, V1=400.0, V2=420.0, Lsc=LSC, Lm=LM, phi=23.6, dt=150e-9, esl=0.7e-9,
             ncyc=80, nsave=2)
    c.update(kw)
    return c


def phi_ideal(P, V1=400.0, V2=420.0, Lm=LM, f=F_SW):
    L = dw.coupled_L(LSC, Lm, N_RATIO, SPLIT)
    R = (R_W[0] + R_ON, R_W[1] + R_ON)
    sgn = 1 if P >= 0 else -1
    if abs(P) < 1:
        return 0.0
    # phase_for_power returns positive phi for positive P only; reverse = mirror (swap roles)
    if sgn > 0:
        ph = dw.phase_for_power(L, f, P=abs(P), V1=V1 / 2, V2=V2 / 2, R=R, C=(2 * C_SPLIT, 2 * C_SPLIT))
    else:
        fn = lambda x: dw.summary(dw.waveform(L, f, -x, V1=V1 / 2, V2=V2 / 2, R=R, C=(2e-6, 2e-6), npts=180))["P2"] + abs(P)
        from scipy.optimize import brentq
        ph = -brentq(fn, 0.5, 89.5, xtol=1e-3)
    return ph


def solve_phi(cfg, P_target, tabs, iters=3):
    """Secant on phi so that the power into the 420 V source is P_target (negative = reverse:
    power into DC+)."""
    ph0 = phi_ideal(P_target, cfg["V1"], cfg["V2"], cfg["Lm"], cfg["f"])
    ph1 = ph0 * 1.08 if ph0 else 1.0
    hist = []

    def P_of(ph):
        c = dict(cfg, phi=ph, P_est=P_target)
        d, meta = run_case(c, tabs)
        res, _ = analyse(d, meta, c)
        p = res["P_out"]
        hist.append((ph, p))
        return p, res, (d, meta, c)
    p0, r0, x0 = P_of(ph0)
    if abs(p0 - P_target) < max(0.01 * abs(P_target), 1.5):
        return ph0, r0, x0, hist
    p1, r1, x1 = P_of(ph1)
    best = (ph1, r1, x1)
    for _ in range(iters):
        if abs(p1 - P_target) < max(0.01 * abs(P_target), 1.5) or p1 == p0:
            break
        ph2 = ph1 + (P_target - p1) * (ph1 - ph0) / (p1 - p0)
        ph0, p0 = ph1, p1
        ph1 = ph2
        p1, r1, x1 = P_of(ph1)
        best = (ph1, r1, x1)
    return best[0], best[1], best[2], hist


def strip(res):
    return json.loads(json.dumps(res, default=float))


def study_full(tabs, pool):
    """400 W both directions, dead time sweep: phi, currents, ZVS, losses."""
    out = {}
    jobs = {}
    for dt in (100e-9, 150e-9, 200e-9, 250e-9):
        for P in (400.0, -400.0):
            cfg = base_cfg(dt=dt)
            jobs[(dt, P)] = pool.submit(solve_phi, cfg, P, tabs)
    for (dt, P), j in jobs.items():
        ph, res, _, hist = j.result()
        res["phi"] = ph
        res["phi_ideal"] = phi_ideal(P)
        res["hist"] = hist
        out[f"{dt*1e9:.0f}ns_{'fwd' if P > 0 else 'rev'}"] = strip(res)
        print("full", dt, P, f"phi {ph:.2f}", f"Pout {res['P_out']:.1f}", flush=True)
    return out


def study_load(tabs, pool, phi400, key="load", V2=420.0, Lm=LM, dts=(100e-9, 150e-9, 200e-9, 250e-9),
               loads=(0.0, 40.0, 100.0, 200.0, 400.0), dirs=(1, -1)):
    """ZVS vs load: phi solved in SPICE for each power (0 W included: with dead time, phi = 0
    does not give zero power)."""
    out = {}
    jobs = {}
    for dt in dts:
        for sg in dirs:
            for P in loads:
                if P == 0 and sg < 0:
                    continue
                Pt = sg * P
                cfg = base_cfg(dt=dt, V2=V2, Lm=Lm, phi=0.0, P_est=Pt)
                jobs[(dt, Pt)] = pool.submit(solve_phi, cfg, Pt, tabs)
    for (dt, Pt), j in jobs.items():
        ph, res, (d, meta, cfg), _ = j.result()
        cfg = dict(cfg, phi=ph)
        res["phi"] = cfg["phi"]
        out[f"{dt*1e9:.0f}ns_{Pt:+.0f}W"] = strip(res)
        print(key, dt, Pt, f"phi {cfg['phi']:.2f}", f"Pout {res['P_out']:.1f}",
              {q: round(r.get('vds_on', float('nan')), 1) for q, r in res['sw'].items()}, flush=True)
    return out


def study_shunt(tabs, pool):
    out = {}
    jobs = {}
    for esl in (0.0, 0.5e-9, 1.0e-9):
        cfg = base_cfg(esl=max(esl, 1e-13), phi=out_phi400, nsave=2)
        jobs[esl] = pool.submit(lambda c: (c, run_case(c, tabs)), cfg)
    waves = {}
    for esl, j in jobs.items():
        cfg, (d, meta) = j.result()
        res, (tt, g) = analyse(d, meta, cfg)
        out[f"{esl*1e9:.1f}nH"] = strip(res["shunt"])
        waves[esl] = (tt, g)
    return out, waves


def study_startup(tabs, pool):
    """(a) 420 V rail at 0 V, DAB starts at 140 kHz (secondary gates off = diode doubler) and
    at higher frequency; (b) split-cap imbalance (C47/C54 +-10 %) at no load."""
    out = {}
    jobs = {}
    for f in (140e3, 280e3, 420e3):
        for v20 in (0.0, 200.0):
            cfg = base_cfg(f=f, phi=0.0, startup=True, sec_off=True, V2_0=v20, ncyc=int(f / 140e3 * 14),
                           nsave=int(f / 140e3 * 14) - 1, P_est=0.0, vmid2_ic=v20 / 2, i1_ic=0.0, i2_ic=0.0,
                           vmid1_ic=200.0)
            jobs[("start", f, v20)] = pool.submit(lambda c: (c, run_case(c, tabs)), cfg)
    # split-cap imbalance: C47 1.1 uF, C54 0.9 uF, midpoint charged as a capacitive divider
    cfg = base_cfg(phi=0.0, c47=1.1e-6, c54=0.9e-6, vmid1_ic=400 * 1.1 / 2.0, i1_ic=0.0, i2_ic=0.0,
                   vmid2_ic=210.0, ncyc=140, nsave=139, P_est=0.0)
    jobs[("imb",)] = pool.submit(lambda c: (c, run_case(c, tabs)), cfg)
    raw = {}
    for key, j in jobs.items():
        cfg, (d, meta) = j.result()
        t = d["time"]
        i1, i2 = d["i(vi1)"], d["i(vi2)"]
        r = {"I1pk": float(np.max(np.abs(i1))), "I2pk": float(np.max(np.abs(i2)))}
        sw = {}
        for q, (dn, sn) in SW.items():
            ql = q.lower()
            idi = d[f"i(v{ql}idi)"]
            ich = d[f"i(v{ql}ich)"]
            sw[q] = {"Ich_pk": float(np.max(np.abs(ich))), "Idiode_pk": float(np.max(np.abs(idi))),
                     "Idiode_rev_pk": float(-np.min(idi))}   # negative diode current = recovery
        r["sw"] = sw
        if key[0] == "start":
            r["V420_end"] = float(d["v(p420)"][-1] - d["v(iso)"][-1])
            r["I1rms"] = _rms(t, i1)
        else:
            im = i1 + N_RATIO * i2
            # per-period average magnetizing current (DC offset) envelope
            T = 1 / cfg["f"]
            nper = int((t[-1] - t[0]) / T)
            avg = []
            for kp in range(nper):
                w = (t >= t[0] + kp * T) & (t < t[0] + (kp + 1) * T)
                avg.append(_mean(t[w], im[w]))
            r["Im_dc_per_period"] = avg
            r["Im_dc_max"] = float(np.max(np.abs(avg)))
            r["Im_pk_total"] = float(np.max(np.abs(im)))
            vm = d["v(capp)"] - d["v(dcur)"]
            r["Vmid1_start"], r["Vmid1_end"] = float(vm[0]), float(vm[-1])
        out["_".join(str(x) for x in key)] = r
        raw[key] = d
        print("startup", key, r["I1pk"], flush=True)
    return out, raw


def study_coss(tabs_small, pool, phi400_150):
    """Sensitivity: small-signal Coss curve (46 pF time-related) instead of Co(tr)."""
    out = {}
    jobs = {}
    for dt in (100e-9, 150e-9):
        for P in (0.0, 40.0, 400.0):
            cfg = base_cfg(dt=dt, P_est=P)
            jobs[(dt, P)] = pool.submit(solve_phi, cfg, P, tabs_small)
    for (dt, P), j in jobs.items():
        ph, res, _, _ = j.result()
        res["phi"] = ph
        out[f"{dt*1e9:.0f}ns_{P:.0f}W"] = strip(res)
    return out


PHI_SCAN = {
    420.0: tuple(np.round(np.concatenate([np.arange(-6.0, -2.0, 0.5), np.arange(-2.0, 2.0, 0.25),
                                          np.arange(2.0, 6.01, 0.5)]), 2)),
    399.0: tuple(np.round(np.arange(-14.0, 2.01, 0.5), 2)),
    441.0: tuple(np.round(np.arange(-2.0, 14.01, 0.5), 2)),
    412.0: tuple(np.round(np.arange(-8.0, 4.01, 0.5), 2)),
    428.0: tuple(np.round(np.arange(-4.0, 8.01, 0.5), 2)),
}


def study_scan(tabs, pool, V2s=(420.0, 399.0, 441.0), dts=(100e-9, 150e-9, 200e-9, 250e-9),
               phis=None, Lm=LM, ncyc=40):
    """Light load: P(phi) is not smooth near phi = 0 (dead-time effects), so scan phi instead
    of solving for a power. Each point: P_out, Vds at turn-on of the 4 switches, node swing."""
    out = {}
    jobs = {}
    for V2 in V2s:
        for dt in dts:
            for ph in (phis or PHI_SCAN[V2]):
                cfg = base_cfg(dt=dt, V2=V2, Lm=Lm, phi=float(ph), ncyc=ncyc, P_est=20.0 * ph)
                jobs[(V2, dt, float(ph))] = pool.submit(lambda c: (c, run_case(c, tabs)), cfg)
    for (V2, dt, ph), j in jobs.items():
        try:
            cfg, (d, meta) = j.result()
        except RuntimeError as e:
            out[f"{V2:.0f}V_{dt*1e9:.0f}ns_{ph:+.2f}"] = {"error": str(e)[:300]}
            continue
        res, _ = analyse(d, meta, cfg)
        r = {"V2": V2, "dt": dt, "phi": ph, "P_out": res["P_out"], "P_in": res["P_in"], "I1rms": res["I1rms"],
             "Im_pk": res["Im_pk"],
             "vds_on": {q: x.get("vds_on") for q, x in res["sw"].items()},
             "t_swing": {q: x.get("t_swing_ns") for q, x in res["sw"].items()},
             "i_off": {q: x.get("id_off") for q, x in res["sw"].items()},
             "Eon_uJ": {q: x.get("Eon_uJ") for q, x in res["sw"].items()}}
        out[f"{V2:.0f}V_{dt*1e9:.0f}ns_{ph:+.2f}"] = strip(r)
    return out


out_phi400 = 23.6


def main():
    global out_phi400
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="full,load,mismatch,lm,shunt,startup,coss,scan,scan2,scanlm,lm200")
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--report", action="store_true", help="only rebuild out/spice_results.md")
    a = ap.parse_args()
    if a.report:
        R = json.load(open(os.path.join(OUT, "spice_results.json")))
        open(os.path.join(OUT, "spice_results.md"), "w").write(report(R))
        return
    which = set(a.only.split(","))
    os.makedirs(OUT, exist_ok=True)
    tabs = cap_tables(True)
    tabs_small = cap_tables(False)
    resf = os.path.join(OUT, "spice_results.json")
    R = json.load(open(resf)) if os.path.exists(resf) else {}
    with ThreadPoolExecutor(max_workers=min(a.jobs, 2)) as pool:
        if "full" in which:
            R["full"] = study_full(tabs, pool)
            json.dump(R, open(resf, "w"), indent=1)
        phi400 = {}
        for kk, v in R.get("full", {}).items():
            dt = float(kk.split("ns")[0]) * 1e-9
            sg = 1 if kk.endswith("fwd") else -1
            phi400[(dt, sg)] = v["phi"] / v["phi_ideal"]
        if "full" in R:
            out_phi400 = R["full"]["150ns_fwd"]["phi"]
        if "load" in which:
            R["load"] = study_load(tabs, pool, phi400)
            json.dump(R, open(resf, "w"), indent=1)
        if "mismatch" in which:
            R["mismatch"] = {}
            for V2 in (399.0, 441.0):
                R["mismatch"][f"{V2:.0f}V"] = study_load(tabs, pool, phi400, key=f"mm{V2:.0f}", V2=V2,
                                                         dts=(150e-9, 200e-9, 250e-9),
                                                         loads=(0.0, 40.0, 100.0, 400.0))
                json.dump(R, open(resf, "w"), indent=1)
        if "lm" in which:
            R["lm"] = {}
            for lm in (250e-6, 400e-6):
                R["lm"][f"{lm*1e6:.0f}uH"] = study_load(tabs, pool, phi400, key=f"lm{lm*1e6:.0f}", Lm=lm,
                                                        dts=(150e-9, 200e-9), loads=(0.0, 40.0, 400.0), dirs=(1,))
                json.dump(R, open(resf, "w"), indent=1)
        if "shunt" in which:
            R["shunt"], waves = study_shunt(tabs, pool)
            np.savez_compressed(os.path.join(OUT, "spice_shunt_waves.npz"),
                                **{f"{k*1e9:.1f}_{n}": v for k, (tt, g) in waves.items()
                                   for n, v in (("t", tt), ("ish", g["i(lsh)"]), ("vsh", g["v(dcur)"]),
                                                ("aout", g["v(aout)"]), ("i1", g["i(vi1)"]))})
            json.dump(R, open(resf, "w"), indent=1)
        if "startup" in which:
            R["startup"], _ = study_startup(tabs, pool)
            json.dump(R, open(resf, "w"), indent=1)
        if "scan" in which:
            R["scan"] = study_scan(tabs, pool)
            json.dump(R, open(resf, "w"), indent=1)
        if "scan2" in which:   # +-2 % mismatch
            R["scan2"] = study_scan(tabs, pool, V2s=(412.0, 428.0), dts=(150e-9, 200e-9))
            json.dump(R, open(resf, "w"), indent=1)
        if "scanlm" in which:
            R["scan_lm"] = {}
            for lm in (200e-6, 250e-6, 400e-6):
                R["scan_lm"][f"{lm*1e6:.0f}uH"] = study_scan(tabs, pool, V2s=(420.0, 441.0), dts=(150e-9,), Lm=lm)
                json.dump(R, open(resf, "w"), indent=1)
        if "lm200" in which:   # proposed gap: 400 W both directions + the -5 % scan at Lm 200 uH
            out = {}
            jobs = {P: pool.submit(solve_phi, base_cfg(dt=150e-9, Lm=200e-6), P, tabs) for P in (400.0, -400.0)}
            for P, j in jobs.items():
                ph, res, _, _ = j.result()
                res["phi"] = ph
                out[f"150ns_{'fwd' if P > 0 else 'rev'}"] = strip(res)
            R["lm200_full"] = out
            R["scan_lm"]["200uH"].update(study_scan(tabs, pool, V2s=(399.0,), dts=(150e-9,), Lm=200e-6))
            R["scan_lm"]["200uH_100ns"] = study_scan(tabs, pool, V2s=(420.0,), dts=(100e-9,), Lm=200e-6)
            json.dump(R, open(resf, "w"), indent=1)
        if "coss" in which:
            R["coss_small_signal"] = study_coss(tabs_small, pool, out_phi400)
            json.dump(R, open(resf, "w"), indent=1)
    open(os.path.join(OUT, "spice_results.md"), "w").write(report(R))
    print("wrote", resf)



# ---------------------------------------------------------------- report tables
def _f(x, nd=1):
    return "–" if x is None else f"{x:.{nd}f}"


def report(R):
    L = []
    a = L.append
    if "full" in R:
        a("### 400 W, 400 V -> 420 V, both directions\n")
        a("| dead time | dir | phi deg (ideal) | P_in W | P_out W | eff % | I1rms / I1pk A | I2rms / I2pk A | "
          "i at edge pri / sec A | Vds at turn-on Q19 / Q7 / Q21 / Q8 V | Eoff per switch uJ | Pch+Pdiode pri / sec W |")
        a("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for k, r in R["full"].items():
            sw = r["sw"]
            eff = 100 * r["P_out"] / r["P_in"] if r["P_in"] > 0 else 100 * r["P_in"] / r["P_out"]
            a(f"| {k.split('_')[0]} | {k.split('_')[1]} | {r['phi']:.2f} ({r['phi_ideal']:.2f}) | {r['P_in']:.0f} | {r['P_out']:.0f} | "
              f"{abs(eff):.1f} | {r['I1rms']:.2f} / {r['I1pk']:.2f} | {r['I2rms']:.2f} / {r['I2pk']:.2f} | "
              f"{_f(sw['Q7'].get('id_off'),2)} / {_f(sw['Q8'].get('id_off'),2)} | "
              + " / ".join(_f(sw[q].get('vds_on')) for q in ("Q19", "Q7", "Q21", "Q8")) + " | "
              + " / ".join(_f(sw[q].get('Eoff_uJ'), 2) for q in ("Q19", "Q7", "Q21", "Q8")) + " | "
              f"{sw['Q19']['Pch']+sw['Q19']['Pdiode']+sw['Q7']['Pch']+sw['Q7']['Pdiode']:.2f} / "
              f"{sw['Q21']['Pch']+sw['Q21']['Pdiode']+sw['Q8']['Pch']+sw['Q8']['Pdiode']:.2f} |")
        a("")

    def load_table(D, title):
        a(f"### {title}\n")
        a("| case | phi deg | P_out W | Vds at turn-on Q19 / Q7 / Q21 / Q8 V | node swing Q19 / Q7 / Q21 / Q8 ns | "
          "i_off Q7 / Q8 A | Im pk A | I1rms A |")
        a("|---|---|---|---|---|---|---|---|")
        for k, r in D.items():
            sw = r["sw"]
            a(f"| {k} | {r['phi']:.2f} | {r['P_out']:.0f} | "
              + " / ".join(_f(sw[q].get('vds_on')) for q in ("Q19", "Q7", "Q21", "Q8")) + " | "
              + " / ".join(_f(sw[q].get('t_swing_ns'), 0) for q in ("Q19", "Q7", "Q21", "Q8")) + " | "
              f"{_f(sw['Q7'].get('id_off'),2)} / {_f(sw['Q8'].get('id_off'),2)} | {r['Im_pk']:.2f} | {r['I1rms']:.2f} |")
        a("")
    if "load" in R:
        load_table(R["load"], "ZVS vs load, 420 V")
    for k, D in R.get("mismatch", {}).items():
        load_table(D, f"ZVS vs load, output {k}")
    for k, D in R.get("lm", {}).items():
        load_table(D, f"ZVS vs load, Lm {k}")
    if "coss_small_signal" in R:
        load_table(R["coss_small_signal"], "Sensitivity: small-signal Coss curve (Q 0..480 V = 22 nC instead of 36 nC)")
    def scan_table(S, title):
        a(f"### {title}\n")
        a("Hard switching = Vds at turn-on above 20 V (5 % of the rail) on any switch; partial = 2…20 V. "
          "Eon = the largest per-edge turn-on energy (Coss discharge + body-diode recovery of the partner).\n")
        a("| output | dead time | phi at P = 0 deg | worst Vds_on at P ≈ 0 V (switch) | node swing at P ≈ 0 ns (max) | "
          "P range with hard switching W | P range with partial ZVS W | max Eon uJ (at P W) |")
        a("|---|---|---|---|---|---|---|---|")
        groups = {}
        for k, r in S.items():
            if "error" in r:
                continue
            groups.setdefault((r["V2"], r["dt"]), []).append(r)
        for (V2, dt), rs in sorted(groups.items()):
            rs.sort(key=lambda r: r["phi"])
            P = np.array([r["P_out"] for r in rs])
            ph = np.array([r["phi"] for r in rs])
            worst = [max((v if v is not None else 999), 0) for v in
                     (max((x if x is not None else 999) for x in r["vds_on"].values()) for r in rs)]
            # phi at P = 0: first sign change
            ph0 = None
            for i in range(len(P) - 1):
                if P[i] <= 0 <= P[i + 1] or P[i] >= 0 >= P[i + 1]:
                    ph0 = ph[i] + (0 - P[i]) * (ph[i + 1] - ph[i]) / (P[i + 1] - P[i]) if P[i + 1] != P[i] else ph[i]
                    break
            i0 = int(np.argmin(np.abs(P)))
            r0 = rs[i0]
            wq = max(r0["vds_on"], key=lambda q: (r0["vds_on"][q] if r0["vds_on"][q] is not None else 999))
            sw0 = max((x or 0) for x in r0["t_swing"].values())
            hard = [P[i] for i in range(len(rs)) if worst[i] > 20]
            part = [P[i] for i in range(len(rs)) if 2 < worst[i] <= 20]
            eons = [(max((x or 0) for x in r["Eon_uJ"].values()), r["P_out"]) for r in rs]
            em = max(eons)
            rng = lambda L: f"{min(L):.0f} … {max(L):.0f}" if L else "none"
            a(f"| {V2:.0f} V | {dt*1e9:.0f} ns | {_f(ph0, 2)} | {_f(r0['vds_on'][wq])} ({wq}, P {r0['P_out']:.0f}) | {sw0:.0f} | "
              f"{rng(hard)} | {rng(part)} | {em[0]:.2f} ({em[1]:.0f}) |")
        a(f"\nScanned P range per row: about {min(r['P_out'] for r in S.values() if 'error' not in r):.0f} … "
          f"{max(r['P_out'] for r in S.values() if 'error' not in r):.0f} W.\n")
    if "scan" in R:
        scan_table(R["scan"], "Light-load phi scans (Lm 307 uH)")
    if "scan2" in R:
        scan_table(R["scan2"], "Light-load phi scans, +-2 % output mismatch")
    for k, S in R.get("scan_lm", {}).items():
        scan_table(S, f"Light-load phi scans, Lm {k}")
    if "shunt" in R:
        a("### DHB shunt R83 / DHB_I amplifier, 400 W forward, 150 ns\n")
        a("| ESL | I_avg A | I pk-pk A | V_R83 pk-pk mV (ideal R only) | amp: I_avg A | amp: I pk-pk A | amp max error A |")
        a("|---|---|---|---|---|---|---|")
        for k, r in R["shunt"].items():
            a(f"| {k} | {r['I_avg']:.3f} | {r['I_pp']:.2f} | {r['Vsh_pp_mV']:.1f} ({r['Vsh_ideal_pp_mV']:.1f}) | "
              f"{r['Iamp_avg']:.3f} | {r['Iamp_pp']:.2f} | {r['Iamp_err_max']:.2f} |")
        a("")
    if "startup" in R:
        a("### Start-up\n")
        a("| case | I1pk A | I2pk A | Q19/Q7 channel pk A | Q21/Q8 diode pk A | diode reverse (recovery) pk A | notes |")
        a("|---|---|---|---|---|---|---|")
        for k, r in R["startup"].items():
            sw = r["sw"]
            note = f"V420 end {r['V420_end']:.1f} V" if "V420_end" in r else \
                f"Im DC max {r['Im_dc_max']:.2f} A, Im pk {r['Im_pk_total']:.2f} A, Vmid1 {r['Vmid1_start']:.0f} -> {r['Vmid1_end']:.0f} V"
            a(f"| {k} | {r['I1pk']:.2f} | {r['I2pk']:.2f} | {sw['Q19']['Ich_pk']:.2f} / {sw['Q7']['Ich_pk']:.2f} | "
              f"{sw['Q21']['Idiode_pk']:.2f} / {sw['Q8']['Idiode_pk']:.2f} | "
              f"{max(sw[q]['Idiode_rev_pk'] for q in sw):.2f} | {note} |")
        a("")
    return "\n".join(L)


if __name__ == "__main__":
    main()
