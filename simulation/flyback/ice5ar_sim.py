"""ngspice model of the auxiliary flyback with the Infineon ICE5AR4780BZS (CoolSET, 800 V CoolMOS,
fixed 100 kHz peak-current mode) in place of the iW1819 / IW1818 PSR controller.

Option key: an option with "controller": "ice5ar" (options.py) is run through this module by
run_flyback.py; every other option still uses flyback_sim.py unchanged (the iW1819 results stay
reproducible). Transformer (full MKF inductance matrix), rectifiers, output capacitors, loads,
preloads and the RCD clamp (D7 / R72 100R / R45 1M || C12 470p) are the same as in flyback_sim.py.
Datasheet: ICE5ARxxxxBZS V2.3 (2020-02-03); values typical unless noted.

Power stage changes
- Switch: CoolMOS as a smooth conductance 1/RDS(on) (gate through a 10 ns RC, datasheet rise /
  fall 30 ns). RDS(on) 4.13 ohm at 25 degC, 8.69 ohm at 125 degC (datasheet, ID 0.4 A); the model
  uses the hot value (ICE["ron"] = 8.7) for the losses. Drain node capacitance: Co(er) 3 pF (VDS 0-500 V)
  + 10 pF transformer / layout (assumed; the iW1819 model had 30 pF for BJT + winding).
- Current sense Rcs = 0.8 ohm (CS limit 0.80 V -> 1.0 A, as Rsense 1.0 ohm / 1.00 V before), internal
  CS filter 10 kohm / 1 pF (block diagram), leading-edge blanking 220 ns (70-365 ns).
- Regulation: divider RF2 = R138 88.7k (5V rail -> VERR) / RF1 = R139 49.9k (VERR -> GND) into the transconductance error
  amplifier (VERR_REF 1.80 V, GERR_M 2.8 mA/V, 9.2 mA/V in Active Burst Mode, source / sink
  150 uA, output range 0.05-3.15 V) that drives the FB pin. The AUX_FB / Vsense divider of the
  PSR controller is gone; A5 feeds only the 5V rail.
- FB pin: compensation network of the datasheet's non-isolated application (figure 2): C2 FB-GND,
  R1 + C1 in series FB-GND, optional RSel FB-GND (ABM option). Assumed: the internal 15 kohm FB
  pull-up (RFB) is disconnected in the non-isolated configuration (otherwise it would load the
  150 uA amplifier: holding FB at 1.95 V would take 90 uA of the 85 uA minimum sink current).

Controller (behavioural, smooth logic as in flyback_sim.py: every state is a capacitor voltage)
- Oscillator 100 kHz (optional jitter +-4 %, period 4 ms), switch-on at the start of each cycle.
- Peak current mode: switch-off when V1 = VCS * GPWM (2.03) + VPWM (0.50 V) [+ MCOMP 50 mV/us *
  (ton - 0.4 T), only for ton > 40 % of T] reaches VFB, or when VCS reaches the current limit
  (VCS_N 0.80 V; the propagation delay is compensated in the IC, modelled as an ideal comparator),
  both after the blanking time; maximum duty 0.75.
- Digital frequency reduction: f = 100 kHz for VFB >= 1.70 V, linear to 43 kHz at VFB = 1.35 V,
  43 kHz below (figure 8). The frequency is latched once per cycle.
- Active Burst Mode (option 2: VFB_EBLP 0.93 V / VCS_BLP 0.22 V; option 3 (default): VFB_EBHP 1.03 V /
  VCS_BHP 0.27 V; option 1: no ABM): entered when VFB stays below the entry level for tFB_BEB
  (36 ms; scaled with the capacitor scale in the batch runs, see run_flyback.py); in ABM the
  converter switches at 83 kHz with the peak current fixed at VCS_BxP / Rcs while VFB rises above
  VFB_BOn (1.95 V, non-isolated) and stops when VFB falls below VFB_BOff (1.55 V); ABM is left when
  VFB exceeds VFB_LB (2.73 V).
- VCC: from the 15V rail through R142 10R and D10 (ZLLS400 Schottky): VCC = V(15V) - ~0.35 V; UVLO
  16.0 / 10.0 V and OVP 25.5 V are checked on the result. case["startup"] (ice5ar_checks.py)
  simulates the start from 0 V: VCC capacitor (C58 22u + C51) charged to VCC_ON, 1.5 mA IC
  current, soft start (CS limit 0.30 V + 0.15 V per 3 ms), the 15V rail taking over VCC. The fixed load on 15V
  is 7.8 mA (the 9.5 mA calibrated estimate minus the IW1818's ~3.2 mA plus the ICE5AR's
  ~0.9 mA IVCC_Normal + ~0.6 mA gate drive).
"""
from __future__ import annotations

import math

import numpy as np

import flyback_sim as fs

ICE = dict(
    fosc=100e3, fmin=43e3, f_abm=83e3, vfb_fhi=1.70, vfb_flo=1.35, jitter=0.0, tjit=4e-3,
    gpwm=2.03, vpwm=0.50, mcomp=0.050, dmax=0.75,           # mcomp in V/us
    vcs_n=0.80, tleb=220e-9,
    vcs_bxp={2: 0.22, 3: 0.27}, vfb_eb={2: 0.93, 3: 1.03}, vfb_lb=2.73, vfb_bon=1.95, vfb_boff=1.55,
    t_beb=36e-3,
    gm=2.8e-3, gm_bm=9.2e-3, iea=150e-6, vref=1.80, vfb_min=0.05, vfb_max=3.15,
    ron=8.7, coss=3e-12, cstray=10e-12,
    vcc_on=16.0, vcc_off=10.0, vcc_ovp=25.5, vf_d10=0.35,
    t_olp=54e-3, t_olp_min=30e-3, vfb_olp=2.73, tss_step=3e-3,
)
RCS = 0.8
VCC_LOAD = 7.8e-3
# FB / VERR network of the 5.2 schematic (kicad_next, commit 009a237, CHANGES_5_2.md 1.5):
# R138 88.7k (5V -> VERR) / R139 49.9k (VERR -> GND) -> 5.000 V; R140 4.7k + C138 10n in series
# FB-GND, C139 2.2n FB-GND, RSel R141 750k (ABM option 2). rfb: internal 15 kohm FB pull-up to
# 3.3 V, None = disconnected in the non-isolated configuration (assumed, see the docstring).
COMP = dict(rf2=88.7e3, rf1=49.9e3, r1=4.7e3, c1=10e-9, c2=2.2e-9, rsel=750e3, abm=2, rfb=None)
# FB network used in the scaled-capacitor batch runs (run_flyback.py): the DC levels depend only on
# RSel, gm and the divider; this slower network keeps the scaled loop well below fsw
BATCH_COMP = dict(r1=4.7e3, c1=2.2e-6, c2=22e-9)
# VCC path of the schematic: 15V -> R142 10R -> D10 (ZLLS400 Schottky) -> VCC, C58 22u + C51 4.7u
VCC_PATH = dict(r=10.0, cvcc=22e-6 + 4.7e-6 * 0.6, icc=1.5e-3)


def p_of_vfb(vfb, lp, vin, p=ICE, rcs=RCS):
    """Normal-mode input power (W) at a given VFB (DCM): 1/2 Lp Ipk^2 f(VFB)."""
    f = p["fmin"] + (p["fosc"] - p["fmin"]) * min(1.0, max(0.0, (vfb - p["vfb_flo"]) / (p["vfb_fhi"] - p["vfb_flo"])))
    ipk = max((vfb - p["vpwm"]) / p["gpwm"] / rcs, vin * p["tleb"] / lp)
    ipk = min(ipk, p["vcs_n"] / rcs)
    return 0.5 * lp * ipk ** 2 * f


def vfb_of_p(pin, lp, vin, p=ICE, rcs=RCS):
    lo, hi = 0.3, 2.2
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if p_of_vfb(mid, lp, vin, p, rcs) < pin:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def expected_pout(case: dict) -> float:
    p = 0.0
    for rail, (node, sign, caps, bleed) in fs.RAILS.items():
        v = fs.NOMINAL_V[rail]
        p += case["loads"].get(rail, 0.0) * v + (v * v / bleed if bleed else 0.0)
        pre = (case.get("preload") or {}).get(rail)
        p += v * v / pre if pre else 0.0
    comp = {**COMP, **(case.get("comp") or {})}
    return p + case.get("vcc", VCC_LOAD) * 15.0 + 15.0 ** 2 / fs.R_AUX_MEAS + 25.0 / (comp["rf1"] + comp["rf2"])


def netlist(res: dict, spice_map: dict, case: dict, cscale=0.1, tstop=9e-3, twin=1.5e-3,
            vin=400.0, wave_file: str | None = None, ic: dict | None = None, save_file: str | None = None) -> str:
    """case keys used: loads, preload, vcc, rcs, comp (dict overriding COMP), ice (dict overriding
    ICE), comp_scale (factor on C1 / C2, default = cscale so the loop scales with the output
    capacitors), t_beb, vfb0 / abm0 (initial FB voltage / ABM state), step (load step:
    {"rail", "di", "t1", "t2"})."""
    p = {**ICE, **(case.get("ice") or {})}
    comp = {**COMP, **(case.get("comp") or {})}
    rcs = case.get("rcs", RCS)
    names, L, R = res["names"], np.array(res["L"]), res["Rdc"]
    lp = sum(L[i][j] for i, a in enumerate(names) for j, b in enumerate(names)
             if a in ("P", "P1", "P2") and b in ("P", "P1", "P2"))
    prim0 = next(n for n in names if n in ("P", "P1"))
    out = [f"* flyback {res['name']} case {case['name']} (ICE5AR4780BZS model)"]
    out.append(f"Vin dcp 0 {vin}")
    out.append("Riso iso 0 1Meg")
    out.append("Ciso iso 0 20p")
    for i, n in enumerate(names):
        d, o = spice_map[n]
        out.append(f"L{n} {d} x{n} {L[i][i]:.6e}")
        out.append(f"R{n} x{n} {o} {R[i]:.5f}")
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            k = L[i][j] / math.sqrt(L[i][i] * L[j][j])
            out.append(f"K{names[i]}_{names[j]} L{names[i]} L{names[j]} {k:.9f}")
    cdrain = p["coss"] + p["cstray"]
    out += [f"Ccol col 0 {cdrain:.3e} IC={vin}",
            "Rgf gate gf 1k", "Cgf gf 0 10p",
            f"Bsw col es I = v(col,es) * (min(1, max(0, v(gf))) / {p['ron']} + 1e-8)",
            f"Rsense es 0 {rcs}",
            "Rcsf es csf 10k", "Ccsf csf 0 1p",          # internal CS filter
            "D7 col sn1 DS1M", ".model DS1M D(IS=5n N=1.8 RS=0.04 CJO=15p TT=2u BV=1200)",
            "R72 sn1 sn2 100", "R45 sn2 dcp 1Meg", "C12 sn2 dcp 470p"]
    vcc_load = case.get("vcc", VCC_LOAD)
    step = case.get("step")
    for rail, (node, sign, caps, bleed) in fs.RAILS.items():
        end, g = fs.RECT[rail], fs.GROUND[rail]
        bv = (case.get("bv") or {}).get(rail, fs.BV_DEFAULT)
        soft = " NBV=5" if bv < fs.BV_DEFAULT else ""
        out.append(f".model DES1_{node} D(IS=2n N=1.7 RS=0.06 CJO=10p M=0.33 TT=20n BV={bv} IBV=10u{soft})")
        out.append(f"D_{node} {end} {node} DES1_{node}" if sign > 0 else f"D_{node} {node} {end} DES1_{node}")
        pre = (case.get("preload") or {}).get(rail)
        il_tot = case["loads"].get(rail, 0.0) + (fs.NOMINAL_V[rail] / bleed if bleed else 0.0) \
            + (vcc_load + fs.NOMINAL_V[rail] / fs.R_AUX_MEAS if rail == "20V" else 0.0) \
            + (fs.NOMINAL_V[rail] / pre if pre else 0.0) \
            + (5.0 / (comp["rf1"] + comp["rf2"]) if rail == "5V" else 0.0)
        cs_rail = min(cscale, max(0.03, cscale * il_tot / 0.1)) if fs.NOMINAL_V[rail] < 50 else \
            min(cscale, max(0.03, cscale * il_tot / 0.01))
        if cscale >= 1.0:
            cs_rail = 1.0
        for ci, (c, esr) in enumerate(caps):
            cv = c * (cs_rail if c >= 10e-6 else 1.0)
            v0 = (ic or {}).get(rail, fs.NOMINAL_V[rail]) * sign
            out.append(f"C_{node}{ci} {node} e_{node}{ci} {cv:.4e} IC={v0:.3f}")
            out.append(f"R_{node}{ci} e_{node}{ci} {g} {esr}")
        if bleed:
            out.append(f"Rb_{node} {node} {g} {bleed}")
        if pre:
            out.append(f"Rpre_{node} {node} {g} {pre}")
        il = case["loads"].get(rail, 0.0)
        if rail == "20V":
            il += vcc_load
            out.append(f"Raux_meas {node} 0 {fs.R_AUX_MEAS}")
        if rail == "5V":
            out += [f"Rf2 {node} verr {comp['rf2']}", f"Rf1 verr 0 {comp['rf1']}"]
        ilx = f"{il}"
        if step and step["rail"] == rail:
            ilx = f"({il} + {step['di']} * stp(time - {step['t1']}, 2e-6) * stp({step.get('t2', 1.0)} - time, 2e-6))"
        if il > 0 or (step and step["rail"] == rail):
            vn = fs.NOMINAL_V[rail]
            if sign > 0:
                out.append(f"BL_{node} {node} {g} I = {ilx} * min(1, max(0, v({node},{g}) / {0.2 * vn}))")
            else:
                out.append(f"BL_{node} {g} {node} I = {ilx} * min(1, max(0, v({g},{node}) / {0.2 * vn}))")
    for rail, (node, sign, caps, bleed) in fs.RAILS.items():
        end = fs.RECT[rail]
        vr = f"v({node})-v({end})" if sign > 0 else f"v({end})-v({node})"
        out += [f"Bvr_{node} xvr_{node} 0 V = {vr}", f"Rvr_{node} xvr_{node} vrf_{node} 1k", f"Cvr_{node} vrf_{node} 0 50p"]

    # ---- controller ----
    out.append(".func stp(x, w) = 0.5 * (1 + tanh(x / w))")
    abm_opt = comp.get("abm", 3)
    cscale_comp = case.get("comp_scale", min(1.0, cscale))
    pin0 = expected_pout(case) / 0.85
    vfb0 = case.get("vfb0", vfb_of_p(pin0, lp, vin, p, rcs))
    abm0 = case.get("abm0", 0)
    if abm_opt in (2, 3):
        veb, vbxp = p["vfb_eb"][abm_opt], p["vcs_bxp"][abm_opt]
        pabm = p_of_vfb(veb, lp, vin, p, rcs)
        if "abm0" not in case and pin0 < pabm:
            abm0 = 1
        if abm0:
            vfb0 = case.get("vfb0", 0.5 * (p["vfb_bon"] + p["vfb_boff"]))
    vfb0 = min(p["vfb_max"], max(p["vfb_min"], vfb0))
    # FB network (C1 / C2 scaled with the output capacitors unless comp_scale is given)
    c1, c2 = comp["c1"] * cscale_comp, comp["c2"] * cscale_comp
    out += [f"C2 fb 0 {c2:.4e} IC={vfb0:.4f}", f"R1 fb n1 {comp['r1']}", f"C1 n1 0 {c1:.4e} IC={vfb0:.4f}"]
    if comp.get("rsel"):
        out.append(f"Rsel fb 0 {comp['rsel']}")
    out.append("Rfbleak fb 0 1e9")
    if comp.get("rfb"):
        out += ["Vref33 vref33 0 3.3", f"Rfb vref33 fb {comp['rfb']}"]
    # error amplifier (transconductance, current in mA as a node voltage)
    gmx = f"({p['gm']} + {p['gm_bm'] - p['gm']} * v(abm))"
    imax = p["iea"]
    out += [f"Bia ia 0 V = 1e3 * min({imax}, max({-imax}, {gmx} * ({p['vref']} - v(verr))))",
            f"Bea 0 fb I = 1e-3 * (max(0, v(ia)) * stp({p['vfb_max']} - v(fb), 0.01) + min(0, v(ia)) * stp(v(fb) - {p['vfb_min']}, 0.01))"]
    # ABM state
    if abm_opt in (2, 3):
        t_beb_ms = case.get("t_beb", p["t_beb"] * cscale_comp) * 1e3
        out += [f"Btb 0 tb I = 1e-6 * stp({veb} - v(fb), 0.005) - 1e-4 * stp(v(fb) - {veb}, 0.005) * v(tb)",   # 1 V/ms below the entry level
                "Ctb tb 0 1n IC=0",
                f"Babm 0 abm I = 1e-3 * (stp(v(tb) - {t_beb_ms}, 0.01) * (1 - v(abm)) - stp(v(fb) - {p['vfb_lb']}, 0.005) * v(abm))",
                f"Cabm abm 0 1n IC={abm0}",
                f"Ben 0 en I = 1e-3 * (stp(v(fb) - {p['vfb_bon']}, 0.005) * (1 - v(en)) - stp({p['vfb_boff']} - v(fb), 0.005) * v(en))",
                f"Cen en 0 1n IC={0 if abm0 else 1}",
                "Bena ena 0 V = 1 - v(abm) * (1 - v(en))"]
        vlim = f"({p['vcs_n']} + {vbxp - p['vcs_n']} * v(abm))"
    else:
        out += ["Vabm abm 0 0", "Vena ena 0 1"]
        vlim = f"{p['vcs_n']}"
    startup = case.get("startup")
    if startup:
        # soft start: CS peak limit 0.30 V + 0.15 V every 3 ms (VSS11 / VSS_S1, tSS 12 ms), and
        # the VCC capacitor (charged to VCC_ON by the start-up cell) supplying the IC until the
        # 15V rail takes over through R142 / D10
        ss = (f"(0.30 + 0.15 * (stp(time - {p['tss_step']}, 2e-6) + stp(time - {2 * p['tss_step']}, 2e-6) + "
              f"stp(time - {3 * p['tss_step']}, 2e-6)) + 0.05 * stp(time - {4 * p['tss_step']}, 2e-6))")
        vlim = f"min({vlim}, {ss})"
        vp = {**VCC_PATH, **(case.get("vcc_path") or {})}
        out += [f"Rvcc v20 dvcc {vp['r']}", "Dvcc dvcc vcc DSCH", ".model DSCH D(IS=5u N=1.05 RS=0.3 CJO=20p)",
                f"Cvcc vcc 0 {vp['cvcc']:.4e} IC={p['vcc_on']}", f"Bicc vcc 0 I = {vp['icc']} * stp(v(vcc) - 3, 0.1)"]
    # frequency (kHz), latched once per cycle
    jit = f" * (1 + {p['jitter']} * sin(6.2831853 * time / {p['tjit']}))" if p["jitter"] else ""
    fn = f"({p['fmin'] / 1e3} + {(p['fosc'] - p['fmin']) / 1e3} * min(1, max(0, (v(fb) - {p['vfb_flo']}) / {p['vfb_fhi'] - p['vfb_flo']})))"
    f0 = p["f_abm"] / 1e3 if abm0 else min(p["fosc"], max(p["fmin"], p["fmin"] + (p["fosc"] - p["fmin"]) * (vfb0 - p["vfb_flo"]) / (p["vfb_fhi"] - p["vfb_flo"]))) / 1e3
    out += [f"Bfr fr 0 V = (v(abm) * {p['f_abm'] / 1e3} + (1 - v(abm)) * {fn}){jit}",
            "Bfl 0 fsw I = 1.0 * stp(v(q) - 0.5, 0.005) * (v(fr) - v(fsw))", f"Cfl fsw 0 1n IC={f0:.3f}",
            # oscillator (as flyback_sim.py), fsw in kHz
            "Bph 0 ph I = 0.98e-6 * v(fsw) - 0.1 * stp(v(q) - 0.5, 0.005) * v(ph)", "Cph ph 0 1n IC=0.5",
            "Bqr qr 0 V = stp(v(ph) - 0.99 + 0.98 * min(1, max(0, v(q))), 1m)",
            "Rq qr q 1k", "Cq q 0 2p IC=0",
            # on-time timer 1 V/us from the end of the reset pulse
            "Btr 0 tr I = 1e-3 * stp(100 - v(tr), 1) - 1.0 * stp(v(q) - 0.5, 0.005) * v(tr)", "Ctr tr 0 1n IC=50",
            # PWM comparator input V1 (with slope compensation above 40 % duty)
            f"Bv1 v1 0 V = {p['gpwm']} * v(csf) + {p['vpwm']} + {p['mcomp']} * max(0, v(tr) - 400 / v(fsw))",
            f"Boff off 0 V = min(1, stp(v(tr) - {p['tleb'] * 1e6}, 0.005) * max(stp(v(v1) - v(fb), 0.002), stp(v(csf) - {vlim}, 0.002))"
            f" + stp(v(tr) - {p['dmax'] * 1e3} / v(fsw), 0.005))",
            # gate latch: set during the oscillator reset pulse (if enabled), reset by the comparator
            # (+ a weak regenerative term so the latch is bistable; the gate is thresholded at 0.5)
            "Blat 0 lat I = 1e-3 * (stp(v(q) - 0.5, 0.005) * v(ena) * (1 - v(lat)) - v(off) * v(lat))"
            " + 1e-4 * (stp(v(lat) - 0.5, 0.05) - v(lat))", "Clat lat 0 1p IC=0",
            "Bgate gate 0 V = stp(v(lat) - 0.5, 0.02) * stp(0.5 - v(q), 0.005)",
            # switch dissipation (conduction + capacitive turn-on + turn-off overlap)
            f"Bpsw psw 0 V = v(col,es) * v(col,es) * (min(1, max(0, v(gf))) / {p['ron']} + 1e-8)"]
    t0 = tstop - twin
    meas = []
    for rail, (node, sign, caps, bleed) in fs.RAILS.items():
        meas.append(f"meas tran V_{node} avg vr_{node} from={t0} to={tstop}")
        meas.append(f"meas tran V1_{node} avg vr_{node} from={t0} to={t0 + twin / 2}")
        meas.append(f"meas tran V2_{node} avg vr_{node} from={t0 + twin / 2} to={tstop}")
        meas.append(f"meas tran VMIN_{node} min vr_{node} from={t0} to={tstop}")
        meas.append(f"meas tran VMAX_{node} max vr_{node} from={t0} to={tstop}")
        meas.append(f"meas tran VRMAX_{node} max vrev_{node} from={t0} to={tstop}")
        meas.append(f"meas tran VRF_{node} max v(vrf_{node}) from={t0} to={tstop}")
    meas += [f"meas tran VCOL max v(col) from={t0} to={tstop}",
             f"meas tran VCLAMP avg vclamp from={t0} to={tstop}",
             f"meas tran FBAVG avg v(fb) from={t0} to={tstop}",
             f"meas tran FBLO min v(fb) from={t0} to={tstop}",
             f"meas tran FBHI max v(fb) from={t0} to={tstop}",
             f"meas tran VERRAVG avg v(verr) from={t0} to={tstop}",
             f"meas tran ABMF avg v(abm) from={t0} to={tstop}",
             f"meas tran ENAF avg v(ena) from={t0} to={tstop}",
             f"meas tran FSWAVG avg v(fsw) from={t0} to={tstop}",
             f"meas tran DUTYAVG avg v(gate) from={t0} to={tstop}",
             f"meas tran IPRI max i(L{prim0}) from={t0} to={tstop}",
             f"meas tran PIN avg pin from={t0} to={tstop}",
             f"meas tran PSWAVG avg v(psw) from={t0} to={tstop}",
             f"meas tran PRCS avg prcs from={t0} to={tstop}",
             f"meas tran PR72 avg pr72 from={t0} to={tstop}",
             f"meas tran PR45 avg pr45 from={t0} to={tstop}"]
    out.append(".options method=gear reltol=1e-3 abstol=1e-9 vntol=1e-5 itl4=50")
    out.append(".control")
    sv = ["v(col)", "v(sn1)", "v(sn2)", "v(dcp)", "v(es)", "v(gf)", "v(fb)", "v(verr)", "v(abm)", "v(ena)", "v(fsw)", "v(psw)",
          "i(Vin)", "v(gate)"]
    sv += [f"v({fs.RAILS[r][0]})" for r in fs.RAILS] + ["v(iso)"] + [f"v({e})" for e in fs.RECT.values()]
    sv += [f"v(vrf_{fs.RAILS[r][0]})" for r in fs.RAILS]
    sv += [f"i(L{n})" for n in names]
    if startup:
        sv.append("v(vcc)")
    out.append("save " + " ".join(sv))
    out.append(f"tran 10n {tstop} {t0 if not save_file else case.get('tsave', 0)} 10n uic")
    out += ["let pin = -v(dcp)*i(vin)", "let vclamp = v(sn2)-v(dcp)", "let pr45 = vclamp*vclamp/1e6",
            "let pr72 = (v(sn1)-v(sn2))*(v(sn1)-v(sn2))/100",
            f"let prcs = v(es)*v(es)/{rcs}"]
    for rail, (node, sign, caps, bleed) in fs.RAILS.items():
        g = "0" if fs.GROUND[rail] == "0" else "v(iso)"
        out.append(f"let vr_{node} = v({node})-{g}" if sign > 0 else f"let vr_{node} = {g}-v({node})")
        end = fs.RECT[rail]
        out.append(f"let vrev_{node} = v({node})-v({end})" if sign > 0 else f"let vrev_{node} = v({end})-v({node})")
    out += meas
    if wave_file:
        out.append("linearize " + " ".join(f"i(L{n})" for n in names) + " v(col) v(gate)")
        out.append(f"wrdata {wave_file} " + " ".join(f"i(L{n})" for n in names) + " v(col) v(gate)")
    if save_file:
        # slow signals for plots (step response, burst ripple, start-up), decimated by linearize
        x = " v(vcc)" if startup else ""
        out.append(f"linearize vr_v5 vr_v20 vr_vs20 vr_vs5 vr_vsn5 vr_vshv v(fb) v(abm) v(ena){x}")
        out.append(f"wrdata {save_file} vr_v5 vr_v20 vr_vs20 vr_vs5 vr_vsn5 vr_vshv v(fb) v(abm) v(ena){x}")
    out.append(".endc")
    out.append(".end")
    return "\n".join(out) + "\n"


def summarise(vals: dict) -> dict:
    vals = dict(vals)
    for a, b in (("fbavg", "fb"), ("fblo", "fbmin"), ("fbhi", "fbmax"), ("verravg", "verr"), ("abmf", "abm"),
                 ("enaf", "ena"), ("pswavg", "psw"), ("dutyavg", "duty"), ("fswavg", "fsw")):
        if a in vals:
            vals[b] = vals.pop(a)
    r = fs.summarise(vals)
    for rail, (node, *_rest) in fs.RAILS.items():
        r[rail + " min"] = vals.get(f"vmin_{node}")
        r[rail + " max"] = vals.get(f"vmax_{node}")
    for k in ("fb", "fbmin", "fbmax", "verr", "abm", "ena", "duty", "ipri", "psw", "prcs", "pr72"):
        r[k] = vals.get(k)
    if r.get("fsw") is not None:
        r["fsw"] *= 1e3                       # kHz node -> Hz
    if r.get("20V") is not None:
        r["vcc"] = r["20V"] - ICE["vf_d10"]
        r["vcc_min"] = (r.get("20V min") or r["20V"]) - ICE["vf_d10"]
        r["vcc_max"] = (r.get("20V max") or r["20V"]) - ICE["vf_d10"]
        r["vcc_flag"] = ("UVLO" if r["vcc_min"] < ICE["vcc_off"] else "") + ("OVP" if r["vcc_max"] > ICE["vcc_ovp"] else "")
    return r
