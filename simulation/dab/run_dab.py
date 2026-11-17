"""DAB transformer TR3 replacement study: EC42x15 PC40 on the seller 2-chamber bobbin,
leakage = DAB series inductance (L3 removed).

    python3 simulation/dab/run_dab.py            # everything (~2-4 min, <1 GB RAM, 1 process)
    python3 simulation/dab/run_dab.py --quick    # sweep only, no gap / baseline / MAS

Writes out/results.json, out/results.md (tables used in DAB_TRANSFORMER.md) and
mas/tr3_dab_<option>.json (MAS: inputs with the 400 W operating point, magnetic, outputs).

Per option: MKF inductance matrix (Lm, leakage) -> 2.5-D correction of the leakage for the
ER geometry (fd_leakage.py, ratio 'er'/'pot' applied to MKF's value) -> DAB steady-state
waveform (dab_wave.py) with the corrected matrix, phase for 400 W at 400 V -> 420 V ->
MKF winding losses (litz, DC + skin + proximity with the real trapezoidal currents) and
core losses (iGSE / Steinmetz / Roshen, PC40) with the primary winding voltage -> rough
temperature rise.
"""
from __future__ import annotations

import copy
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dab_wave as dw  # noqa: E402
import fd_leakage as fd  # noqa: E402
import om_dab as m  # noqa: E402
import PyOpenMagnetics as P  # noqa: E402

OUT = os.path.join(HERE, "out")
MAS_DIR = os.path.join(HERE, "mas")
F_MAIN = 140e3            # DAB switching frequency (user, = PFC frequency)
F_SENS = 100e3            # sensitivity line only
V1, V2 = 200.0, 210.0     # half-bridge square amplitudes (400 V / 2, 420 V / 2)
POUT = 400.0
T_WIND = 80.0             # winding temperature for resistances (degC)
COSS_TR = 75.5e-12        # STF7N60M2 "Coss eq." time related, 0-480 V (ST DS9793)
C_WIND = 30e-12           # winding + layout capacitance per switch node (assumption)
C_LEG = 2 * COSS_TR + C_WIND
DEAD_TIMES = (100e-9, 150e-9, 200e-9)

L60 = m.litz_name(60, "0.1")
L90 = m.litz_name(90, "0.1")
L135 = m.litz_name(135, "0.071")
L180 = m.litz_name(180, "0.071")

ALIGN = {"div": ("high", "low"),      # both windings pushed to the divider (min leakage)
         "fl": ("low", "high"),       # pushed to the flanges (max leakage)
         "cen": ("centered", "centered"),
         "spr": ("spread", "spread")}  # turns spread over the chamber width (few layers)


def windings_new(np_, ns, wire_p=L60, wire_s=L60, align="div", assign=(1, 2), tpl=(None, None)):
    a = ALIGN[align]
    if assign != (1, 2):        # primary in chamber 2: 'towards the divider' flips
        a = (a[1], a[0])
    return [dict(name="PRI", turns=np_, wire=wire_p, side="primary", y=m.CHAMBERS[assign[0]], align=a[0], tpl=tpl[0]),
            dict(name="SEC", turns=ns, wire=wire_s, side="secondary", y=m.CHAMBERS[assign[1]], align=a[1], tpl=tpl[1])]


# ---------------------------------------------------------------------------------------
def fd_blocks(coil):
    """Per-layer rectangles (r0, r1, z0, z1, AT for 1 A primary) from the MKF coil."""
    turns = coil["turnsDescription"]
    fdesc = coil["functionalDescription"]
    n1 = fdesc[0]["numberTurns"]
    sign = {fdesc[0]["name"]: 1.0, fdesc[1]["name"]: -n1 / fdesc[1]["numberTurns"]}
    lay = {}
    for t in turns:
        lay.setdefault(t["layer"], []).append(t)
    out = []
    for ts in lay.values():
        od = ts[0]["dimensions"][0]
        x = ts[0]["coordinates"][0]
        ys = [t["coordinates"][1] for t in ts]
        out.append((x - od / 2, x + od / 2, min(ys) - od / 2, max(ys) + od / 2, len(ts) * sign[ts[0]["winding"]]))
    return out


def er_factor(coil, h=0.2e-3):
    r = fd.leakage(fd_blocks(coil), h)
    return r["er"] / r["pot"], r


def leakage_split(coil):
    """Primary share of the leakage for two side-by-side windings from the geometry:
    (a1/3 + g/2) / (a1/3 + a2/3 + g), a = axial width of each winding block, g = axial gap.
    (The split from MKF's matrix, L11 - L12/n, is numerically fragile: a 1 % error in L22
    moves it by tens of %. It decides how the no-load magnetizing current divides between
    the two bridges, i.e. the ZVS of each bridge at light load.)"""
    ext = {}
    for t in coil["turnsDescription"]:
        y, od = t["coordinates"][1], t["dimensions"][0]
        lo, hi = ext.get(t["winding"], (1e9, -1e9))
        ext[t["winding"]] = (min(lo, y - od / 2), max(hi, y + od / 2))
    names = [f["name"] for f in coil["functionalDescription"]]
    (p0, p1), (s0, s1) = ext[names[0]], ext[names[1]]
    a1, a2 = p1 - p0, s1 - s0
    g = max(s0 - p1, p0 - s1, 0.0)
    return (a1 / 3 + g / 2) / (a1 / 3 + a2 / 3 + g)


def corrected_matrix(L, lsc_best, n, split):
    """2x2 matrix with MKF's open-circuit primary inductance L11, the corrected leakage
    lsc_best, the real turns ratio n = Ns/Np and the geometric leakage split."""
    L = np.array(L, float)
    lm = L[0, 0] - split * lsc_best
    return np.array(dw.coupled_L(lsc_best, lm, n, split))


def resample(w, n=256):
    tu = np.linspace(0, w["T"], n + 1)
    return tu, {k: np.interp(tu, w["t"], w[k]) for k in ("i1", "i2", "vb1", "vc1")}


def winding_losses(mag, f, tu, currents: dict, temperature=T_WIND, fringing=True):
    P.set_settings({"inputsTrimHarmonics": False, "harmonicAmplitudeThresholdQuickMode": False,
                    "magneticFieldIncludeFringing": fringing})
    exc = [{"name": n, "frequency": f, "current": {"waveform": {"data": list(map(float, i)), "time": list(map(float, tu))}}}
           for n, i in currents.items()]
    op = {"name": "dab", "conditions": {"ambientTemperature": 40.0}, "excitationsPerWinding": exc}
    wl = P.calculate_winding_losses(mag, op, temperature)
    per = {}
    for k, p in enumerate(wl["windingLossesPerWinding"]):
        o = (p.get("ohmicLosses") or {}).get("losses", 0.0)
        sk = sum((p.get("skinEffectLosses") or {}).get("lossesPerHarmonic") or [])
        pr = sum((p.get("proximityEffectLosses") or {}).get("lossesPerHarmonic") or [])
        per[list(currents)[k]] = {"dc": o, "skin": sk, "prox": pr, "total": o + sk + pr}
    P.reset_settings()
    return wl["windingLosses"], per


def core_losses(core, coil, f, tu, v, i, lm):
    """Core losses from the winding voltage. The current passed to MKF is the magnetizing
    current integral(v)/Lm (zero mean): with the load current MKF sometimes derives B from
    the current (seen on the ETD34 baseline: 1.99 T)."""
    name = coil["functionalDescription"][0]["name"]
    dt = np.diff(tu)
    lam = np.concatenate([[0.0], np.cumsum(0.5 * (v[1:] + v[:-1]) * dt)])
    i = lam / lm
    i = i - 0.5 * (i.max() + i.min())
    op = {"name": "dab", "conditions": {"ambientTemperature": 40.0}, "excitationsPerWinding": [
        {"name": name, "frequency": f,
         "current": {"waveform": {"data": list(map(float, i)), "time": list(map(float, tu))}},
         "voltage": {"waveform": {"data": list(map(float, v)), "time": list(map(float, tu))}}}]}
    inputs = {"designRequirements": {"magnetizingInductance": {"nominal": lm}, "turnsRatios": []},
              "operatingPoints": [op]}
    out = {}
    for model in ("IGSE", "STEINMETZ", "ROSHEN"):
        try:
            cl = P.calculate_core_losses(core, coil, inputs, {"coreLosses": model, "reluctance": "ZHANG"})
        except Exception:
            simple = P.wind({"bobbin": coil["bobbin"], "functionalDescription": [coil["functionalDescription"][0]]},
                            1, [1], [0], [[0, 0]])
            cl = P.calculate_core_losses(core, simple, inputs, {"coreLosses": model, "reluctance": "ZHANG"})
        out[model] = cl.get("coreLosses")
        if model == "IGSE":
            out["Bpk"] = cl.get("magneticFluxDensityPeak")
            out["T_core_mkf"] = cl.get("maximumCoreTemperature")
    return out


def surface_cm2(which, build_mm):
    """Rough outer surface of the wound part (cm2): core box + the winding outside the core
    band (about 55 % of the circumference for EC42, 60 % for ETD34)."""
    if which == "new":
        a, h, d, lw, frac = 42.0, 43.0, 15.3, 30.3, 0.55
        dw_ = 2 * (8.9 + build_mm)
    else:
        a, h, d, lw, frac = 34.2, 34.6, 11.1, 23.4, 0.6
        dw_ = 2 * (6.8 + build_mm)
    return (2 * (a * h + a * d + h * d) + frac * math.pi * dw_ * lw) / 100.0


def temp_rise(p_w, area_cm2):
    """McLyman natural convection: dT = (P[mW] / A[cm2])^0.833."""
    return (p_w * 1e3 / area_cm2) ** 0.833


# ---------------------------------------------------------------------------------------
def evaluate(name, wds, f=F_MAIN, which="new", gap_kind="none", gap=0.0, L3=0.0, extra=None,
             fd_on=True, losses=True, keep=False, k_fixed=None):
    res = m.analyse(wds, f, which, gap_kind, gap, T_WIND)
    L = np.array(res["L"])
    coil = res["magnetic"]["coil"]
    if k_fixed is not None:
        k, fdr = k_fixed, None
    elif which == "new" and fd_on:
        k, fdr = er_factor(coil)
    else:
        k, fdr = 1.0, None
    lsc_best = res["Lsc"] * k
    n = wds[1]["turns"] / wds[0]["turns"]
    if which == "new":
        split = leakage_split(coil)
        Lc = corrected_matrix(L, lsc_best, n, split)
    else:       # baseline: MKF matrix as is (L3 dominates the series inductance)
        split = None
        Lc = L
    R = res["Rdc"]
    out = {"name": name, "f": f, "Np": wds[0]["turns"], "Ns": wds[1]["turns"], "wire_p": wds[0]["wire"],
           "wire_s": wds[1]["wire"], "gap_kind": gap_kind, "gap_mm": gap * 1e3,
           "Lm_uH": res["Lm"] * 1e6, "Lsc_mkf_uH": res["Lsc"] * 1e6, "er_factor": k,
           "Lsc_uH": lsc_best * 1e6, "L3_uH": L3 * 1e6, "Lseries_uH": (lsc_best + L3) * 1e6,
           "k_mkf": res["k"], "leak_split_pri": split, "Rdc_80C": R, "geometry": res["geometry"], "fd": fdr}
    if extra:
        out.update(extra)
    out["Pmax_ideal_W"] = V1 * V2 / n / (8 * f * (lsc_best + L3))     # at phi = 90 deg
    ph = dw.phase_for_power(Lc, f, POUT, V1=V1, V2=V2, L3=L3, R=R)
    out["phi_deg"] = ph
    if ph is None:
        return out
    w = dw.waveform(Lc, f, ph, V1=V1, V2=V2, L3=L3, R=R, npts=1024)
    s = dw.summary(w)
    out.update({k2: float(v) for k2, v in s.items()})
    # no-load (phi = 0) edge currents for the ZVS check
    w0 = dw.waveform(Lc, f, 0.0, V1=V1, V2=V2, L3=L3, R=R, npts=256)
    s0 = dw.summary(w0)
    out["noload_i1_edge"] = s0["i1_at_pri_edge"]
    out["noload_i2_edge"] = s0["i2_at_sec_edge"]
    out["Bpk_hand"] = V1 / (4 * f * wds[0]["turns"] * (m.make_core(which)["processedDescription"]["effectiveParameters"]["effectiveArea"]))
    if not losses:
        return out
    tu, rs = resample(w)
    cur = {"PRI": rs["i1"], "SEC": rs["i2"]}
    pcu_raw, _ = winding_losses(res["magnetic"], f, tu, cur)
    # MKF's gap-fringing term reacts to the individual winding currents (it adds ~1.5 W for
    # a 0.7 mm centre gap with the load currents, but 0.01 W with the magnetizing current
    # alone). Physically the gap MMF is the net ampere-turns N*Im (the load ampere-turns
    # cancel around any loop through the gap), so: winding losses without the fringing
    # term + the fringing increment of the magnetizing current alone.
    pcu_nf, per = winding_losses(res["magnetic"], f, tu, cur, fringing=False)
    if which == "new":
        im = rs["i1"] + n * rs["i2"]
        z = 0 * im
        pf_on, _ = winding_losses(res["magnetic"], f, tu, {"PRI": im, "SEC": z})
        pf_off, _ = winding_losses(res["magnetic"], f, tu, {"PRI": im, "SEC": z}, fringing=False)
        p_fr = pf_on - pf_off
        out["Im_pk"] = float(np.max(np.abs(im)))
    else:
        p_fr = pcu_raw - pcu_nf
    pcu = pcu_nf + p_fr
    out["Pcu_mkf_raw_W"] = pcu_raw
    out["Pcu_fringing_W"] = p_fr
    # primary winding voltage = bridge - split cap - L3 drop - R1 i1 (the core flux next to
    # the primary follows it; with side-by-side windings the secondary half sees the
    # secondary voltage, of nearly the same volt-seconds)
    vT = np.interp(tu, w["t"], w["vt1"])
    vT -= np.mean(vT[:-1])
    vT[-1] = vT[0]
    cl = core_losses(res["magnetic"]["core"], coil, f, tu, vT, rs["i1"], res["Lm"])
    out["Pcu_W"] = pcu
    out["Pcu_per"] = per
    out["Pcore_W"] = cl["IGSE"]
    out["Pcore_models"] = {k2: cl[k2] for k2 in ("IGSE", "STEINMETZ", "ROSHEN")}
    out["Bpk_T"] = cl["Bpk"]
    out["T_core_mkf"] = cl["T_core_mkf"]
    build = max(wd["build_with_tape_mm"] for wd in res["geometry"]["windings"])
    area = surface_cm2(which, build)
    out["P_total_W"] = pcu + cl["IGSE"]
    out["surface_cm2"] = area
    out["dT_K"] = temp_rise(out["P_total_W"], area)
    if keep:
        out["_magnetic"] = res["magnetic"]
        out["_wave"] = {"t": tu.tolist(), "i1": rs["i1"].tolist(), "i2": rs["i2"].tolist(), "v1": vT.tolist()}
        out["_L"] = Lc.tolist()
    return out


# ---------------------------------------------------------------------------------------
def gap_curve(wds, kind, gaps, k_er, f=F_MAIN):
    """Lm, leakage, no-load edge currents, 400 W metrics over gap length."""
    rows = []
    for g in gaps:
        r = evaluate(f"{kind}{g * 1e3:.3f}", wds, f, gap_kind=kind if g > 0 else "none", gap=g, fd_on=False,
                     losses=False, k_fixed=k_er)
        rows.append({k: r.get(k) for k in ("gap_mm", "Lm_uH", "Lsc_mkf_uH", "noload_i1_edge", "noload_i2_edge",
                                           "phi_deg", "I1rms", "i1_at_pri_edge", "i2_at_sec_edge")})
    return rows


def lm_for_zvs(wds, k_er, t_dead, f=F_MAIN, nfrac=0.5):
    """Required Lm (open-circuit primary inductance) so that at no load (phi = 0) both
    bridges commutate in t_dead: |edge current| >= C_LEG * Vdc / t_dead on each side.
    Uses the ungapped matrix scaled to Lm (leakage kept, as MKF shows it barely moves)."""
    res = m.analyse(wds, f, "new", "none", 0.0, T_WIND)
    lsc = res["Lsc"] * k_er
    n = wds[1]["turns"] / wds[0]["turns"]
    i_req = (C_LEG * 2 * V1 / t_dead, C_LEG * 2 * V2 / t_dead)
    split = leakage_split(res["magnetic"]["coil"])

    def margin(lm):
        Lx = dw.coupled_L(lsc, lm, n, split)
        s0 = dw.summary(dw.waveform(Lx, f, 0.0, V1=V1, V2=V2, R=res["Rdc"], npts=256))
        return min(-s0["i1_at_pri_edge"] / i_req[0], -s0["i2_at_sec_edge"] / i_req[1]), s0
    lo, hi = 50e-6, 5e-3
    for _ in range(40):
        mid = math.sqrt(lo * hi)
        if margin(mid)[0] >= 1.0:
            lo = mid
        else:
            hi = mid
    mg, s0 = margin(lo)
    return {"t_dead_ns": t_dead * 1e9, "I_req_pri": i_req[0], "I_req_sec": i_req[1], "Lm_req_uH": lo * 1e6,
            "i1_edge": s0["i1_at_pri_edge"], "i2_edge": s0["i2_at_sec_edge"], "leak_split_pri": split,
            "Im_pk_hand": V1 / (4 * f * lo)}


def zvs_vs_load(L, R, f=F_MAIN, loads=(0, 25, 50, 100, 200, 300, 400), v2s=(210.0,)):
    """Edge currents vs output power (gapped matrix). ZVS needs i1 <= -I_req_pri and
    i2 <= -I_req_sec (C_LEG * Vdc / t_dead)."""
    rows = []
    for v2 in v2s:
        for p in loads:
            ph = 0.0 if p == 0 else dw.phase_for_power(L, f, p, V1=V1, V2=v2, R=R)
            if ph is None:
                rows.append({"V2": v2, "P": p, "phi": None})
                continue
            s = dw.summary(dw.waveform(L, f, ph, V1=V1, V2=v2, R=R, npts=512))
            rows.append({"V2": v2, "P": p, "phi": ph, "i1_edge": s["i1_at_pri_edge"], "i2_edge": s["i2_at_sec_edge"],
                         "I1rms": s["I1rms"]})
    return rows


def gap_for_lm(wds, kind, lm_target, f=F_MAIN):
    """Gap length giving the primary open-circuit inductance lm_target (secant on 1/L)."""
    coil, _ = m.build_coil(wds)

    def lm(g):
        return m.inductance_matrix({"core": m.make_core("new", kind, g), "coil": coil}, f)[0, 0]
    g0, g1 = 0.05e-3, 0.3e-3
    y0, y1 = 1 / lm(g0), 1 / lm(g1)
    for _ in range(12):
        g2 = min(3e-3, max(1e-6, g0 + (1 / lm_target - y0) * (g1 - g0) / (y1 - y0)))
        y2 = 1 / lm(g2)
        if abs(y2 * lm_target - 1) < 1e-3:
            break
        g0, y0, g1, y1 = g1, y1, g2, y2
    return g2


# ---------------------------------------------------------------------------------------
def baseline(f=F_MAIN):
    """Existing ETD34 26:28 (concentric, primary inside, 60x0.1 litz assumed) + L3 70 uH RM8."""
    xi, xo, yb, yt = m.bobbin_window("old")
    wds = [dict(name="PRI", turns=26, wire=L60, side="primary", y=(yb, yt), align="centered", x0=xi),
           dict(name="SEC", turns=28, wire=L60, side="secondary", y=(yb, yt), align="centered",
                x0=xi + 2 * m.wire_od(L60) + m.TAPE_LAYERS * m.TAPE)]
    # ETD34 concentric: TR3 leakage from MKF (no ER correction), L3 separate
    r = evaluate("baseline ETD34 26:28 + L3 70uH", wds, f, which="old", gap_kind="none", L3=70e-6, fd_on=False,
                 keep=True)
    # L3 on RM8 (assumed design: 25 T Litz 40x0.1, PC40, gap fitted to 70 uH)
    m.load()
    l3w = m.litz_name(40, "0.1")
    bob = P.find_bobbin_by_name("Bobbin RM 8")
    coil = P.wind({"bobbin": bob, "functionalDescription": [
        {"name": "L3", "numberTurns": 25, "numberParallels": 1, "wire": m.wire(l3w), "isolationSide": "primary"}]},
        1, [1], [0], [[0, 0]])

    def rm8(g):
        c = {"functionalDescription": {"type": "two-piece set", "shape": "RM 8", "material": m.MATERIAL,
                                       "numberStacks": 1, "gapping": m.core_gapping("centre", g)}}
        return P.calculate_core_data(c, False)

    def l3(g):
        return P.calculate_inductance_matrix({"core": rm8(g), "coil": coil}, f, {})["magnitude"]["L3"]["L3"]["nominal"]
    g0, g1 = 0.4e-3, 1.0e-3
    y0, y1 = 1 / l3(g0), 1 / l3(g1)
    for _ in range(12):
        g2 = g0 + (1 / 70e-6 - y0) * (g1 - g0) / (y1 - y0)
        y2 = 1 / l3(g2)
        if abs(y2 * 70e-6 - 1) < 1e-3:
            break
        g0, y0, g1, y1 = g1, y1, g2, y2
    core = rm8(g2)
    wv = r["_wave"]
    tu = np.array(wv["t"])
    i1 = np.array(wv["i1"])
    vl = 70e-6 * np.gradient(i1, tu)
    mag = {"core": core, "coil": coil}
    pcu, _ = winding_losses(mag, f, tu, {"L3": i1})
    cl = core_losses(core, coil, f, tu, vl, i1, 70e-6)
    l3r = {"turns": 25, "wire": l3w, "gap_mm": g2 * 1e3, "Pcu_W": pcu, "Pcore_W": cl["IGSE"],
           "Pcore_models": {k: cl[k] for k in ("IGSE", "STEINMETZ", "ROSHEN")}, "Bpk_T": cl["Bpk"],
           "dT_K": temp_rise(pcu + cl["IGSE"], 2 * (23.2 * 16.4 + 23.2 * 9.6 + 16.4 * 9.6) / 100.0 * 1.2)}
    r["L3_design"] = l3r
    r["P_total_with_L3_W"] = r["P_total_W"] + pcu + cl["IGSE"]
    return r


# ---------------------------------------------------------------------------------------
def strip(r):
    return {k: v for k, v in r.items() if not k.startswith("_")}


def mas_doc(r, title):
    mag = copy.deepcopy(r["_magnetic"])
    mag["manufacturerInfo"] = {"name": "tube_power_5_1 TR3 (DAB)", "reference": title}
    wv = r["_wave"]
    op = {"name": f"400 W, 400 V -> 420 V, {r['f'] / 1e3:.0f} kHz, phi {r['phi_deg']:.1f} deg",
          "conditions": {"ambientTemperature": 40.0},
          "excitationsPerWinding": [
              {"name": "PRI", "frequency": r["f"],
               "current": {"waveform": {"data": wv["i1"], "time": wv["t"]}},
               "voltage": {"waveform": {"data": wv["v1"], "time": wv["t"]}}},
              {"name": "SEC", "frequency": r["f"],
               "current": {"waveform": {"data": wv["i2"], "time": wv["t"]}}}]}
    names = ["PRI", "SEC"]
    Lm = r["_L"]
    return {"inputs": {"designRequirements": {
                "magnetizingInductance": {"nominal": r["Lm_uH"] * 1e-6},
                "turnsRatios": [{"nominal": r["Np"] / r["Ns"]}],
                "leakageInductance": [{"nominal": r["Lsc_uH"] * 1e-6}],
                "name": "TR3 DAB, leakage = series inductance"},
                       "operatingPoints": [op]},
            "magnetic": mag,
            "outputs": [{"inductance": {"magnetizingInductance": {"magnetizingInductance": {"nominal": r["Lm_uH"] * 1e-6}},
                                        "leakageInductance": {"leakageInductancePerWinding": [
                                            {"nominal": r["Lsc_uH"] * 1e-6}]},
                                        "inductanceMatrix": [{"frequency": r["f"], "magnitude": {
                                            a: {b: {"nominal": Lm[i][j]} for j, b in enumerate(names)}
                                            for i, a in enumerate(names)}}]},
                         "windingLosses": {"windingLosses": r["Pcu_W"]},
                         "coreLosses": {"coreLosses": r["Pcore_W"], "magneticFluxDensityPeak": r["Bpk_T"]}}]}


def fmt_row(r):
    def g(k, f="%.1f"):
        v = r.get(k)
        return "–" if v is None else f % v
    return (f"| {r['name']} | {r['Np']}:{r['Ns']} | {g('Lsc_mkf_uH', '%.0f')} | {g('Lsc_uH', '%.0f')} | "
            f"{g('Lm_uH', '%.0f')} | {g('Pmax_ideal_W', '%.0f')} | {g('phi_deg')} | {g('I1rms', '%.2f')} | {g('I1pk', '%.2f')} | "
            f"{g('Bpk_T', '%.3f')} | {g('Pcore_W', '%.2f')} | {g('Pcu_W', '%.2f')} | {g('P_total_W', '%.2f')} | "
            f"{g('dT_K', '%.0f')} | {'yes' if r['geometry']['fits'] else 'NO'} |")


HDR = ("| option | Np:Ns | Lsc MKF µH | Lsc best µH | Lm µH | Pmax W | φ° @400 W | I1rms A | I1pk A | Bpk T | "
       "Pcore W | Pcu W | total W | ΔT K | fits |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")


def main(quick=False):
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(MAS_DIR, exist_ok=True)
    m.load()
    results = {"assumptions": {"f_main": F_MAIN, "f_sens": F_SENS, "V1": V1, "V2": V2, "P": POUT,
                               "C_split": dw.C_SPLIT, "T_wind": T_WIND, "Coss_tr": COSS_TR, "C_wind": C_WIND}}
    md = []
    # 1. turns sweep, 60x0.1 both, windings at the divider
    pairs = [(16, 17), (17, 18), (18, 19), (19, 20), (20, 21), (21, 22), (22, 23), (23, 24), (24, 25), (25, 26),
             (26, 27), (26, 28)]
    sweep = []
    for np_, ns in pairs:
        r = evaluate(f"div {np_}:{ns}", windings_new(np_, ns, align="div"))
        sweep.append(strip(r))
        print(fmt_row(r), flush=True)
    results["sweep_div"] = sweep
    md += ["## Turns sweep (Litz 60x0.1 both, windings pushed to the divider, 140 kHz, ungapped)", "", HDR] + \
          [fmt_row(r) for r in sweep] + [""]
    # 2. winding position / litz / chamber assignment knobs at two turn counts
    knobs = []
    for np_, ns in ((20, 21), (24, 25)):
        for al in ("div", "cen", "spr", "fl"):
            r = evaluate(f"{al} {np_}:{ns}", windings_new(np_, ns, align=al))
            knobs.append(strip(r))
            print(fmt_row(r), flush=True)
        for wp, ws, tag in ((L90, L90, "90x0.1"), (L135, L135, "135x0.071")):
            r = evaluate(f"div {tag} {np_}:{ns}", windings_new(np_, ns, wp, ws, align="div"))
            knobs.append(strip(r))
            print(fmt_row(r), flush=True)
        r = evaluate(f"div swapped (PRI in 12.4) {np_}:{ns}", windings_new(np_, ns, align="div", assign=(2, 1)))
        knobs.append(strip(r))
        print(fmt_row(r), flush=True)
    results["knobs"] = knobs
    md += ["## Position / litz / chamber knobs", "", HDR] + [fmt_row(r) for r in knobs] + [""]
    if quick:
        json.dump(results, open(os.path.join(OUT, "results.json"), "w"), indent=1)
        open(os.path.join(OUT, "results.md"), "w").write("\n".join(md))
        return
    # 3. recommended options (filled in after looking at the sweep; see DAB_TRANSFORMER.md)
    # Litz 135x0.071 (OD 1.19-1.29 mm): 7 turns per layer in the 10.4 mm chamber, 9 in the
    # 12.4 mm one (8 / 9.6 would fit on paper; one turn of slack per layer for a hand wind)
    recs = {"A_70uH": dict(np_=25, ns=26, align="div", wp=L135, ws=L135, tpl=(7, 9)),
            "B_42uH": dict(np_=20, ns=21, align="div", wp=L135, ws=L135, tpl=(7, 9))}
    results["recommended"] = {}
    md += ["## Recommended options", ""]
    for key, rc in recs.items():
        wds = windings_new(rc["np_"], rc["ns"], rc["wp"], rc["ws"], align=rc["align"], tpl=rc["tpl"])
        r = evaluate(f"{key} {rc['np_']}:{rc['ns']}", wds, keep=True)
        k_er = r["er_factor"]
        r100 = evaluate(f"{key} @100 kHz", wds, f=F_SENS)
        # ZVS / gap
        zvs = [lm_for_zvs(wds, k_er, td) for td in DEAD_TIMES]
        gaps = []
        for z in zvs:
            gc = gap_for_lm(wds, "centre", z["Lm_req_uH"] * 1e-6)
            gs = gap_for_lm(wds, "spacer", z["Lm_req_uH"] * 1e-6)
            gaps.append({"t_dead_ns": z["t_dead_ns"], "centre_gap_mm": gc * 1e3, "spacer_mm": gs * 1e3})
        # gapped evaluation at the 150 ns design point (centre grind) and the spacer variant
        g150 = gaps[1]
        rg = evaluate(f"{key} gapped centre {g150['centre_gap_mm']:.3f} mm", wds, gap_kind="centre",
                      gap=g150["centre_gap_mm"] * 1e-3, keep=True)
        rs_ = evaluate(f"{key} spacer {g150['spacer_mm']:.3f} mm", wds, gap_kind="spacer",
                       gap=g150["spacer_mm"] * 1e-3)
        zl = zvs_vs_load(np.array(rg["_L"]), rg["Rdc_80C"], v2s=(200.0, 210.0, 220.0))
        curve = gap_curve(wds, "centre", [0, 0.05e-3, 0.1e-3, 0.2e-3, 0.3e-3, 0.5e-3, 0.8e-3, 1.2e-3], k_er)
        results["recommended"][key] = {"ungapped": strip(r), "at_100k": strip(r100), "zvs": zvs, "gaps": gaps,
                                       "gapped_centre": strip(rg), "gapped_spacer": strip(rs_), "gap_curve": curve,
                                       "zvs_vs_load": zl}
        json.dump(mas_doc(rg, f"{key} {rc['np_']}:{rc['ns']} gapped centre"),
                  open(os.path.join(MAS_DIR, f"tr3_dab_{key}.json"), "w"), indent=1)
        md += [f"### {key}", "", HDR, fmt_row(r), fmt_row(r100), fmt_row(rg), fmt_row(rs_), "",
               "| dead time ns | I_req pri A | I_req sec A | Lm req µH | centre gap mm | spacer mm |", "|---|---|---|---|---|---|"]
        for z, g in zip(zvs, gaps):
            md.append(f"| {z['t_dead_ns']:.0f} | {z['I_req_pri']:.2f} | {z['I_req_sec']:.2f} | {z['Lm_req_uH']:.0f} | "
                      f"{g['centre_gap_mm']:.3f} | {g['spacer_mm']:.3f} |")
        md += ["", "| gap mm | Lm µH | Lsc MKF µH | no-load i1 edge A | no-load i2 edge A | φ° | I1rms A |",
               "|---|---|---|---|---|---|---|"]
        for c in curve:
            md.append(f"| {c['gap_mm']:.2f} | {c['Lm_uH']:.0f} | {c['Lsc_mkf_uH']:.1f} | {c['noload_i1_edge']:.2f} | "
                      f"{c['noload_i2_edge']:.2f} | {c['phi_deg']:.1f} | {c['I1rms']:.2f} |")
        md += ["", f"ZVS vs load, gapped centre (Lm {rg['Lm_uH']:.0f} µH), edge currents (need <= -I_req):", "",
               "| Vout/2 V | P W | φ° | i1 edge A | i2 edge A | I1rms A |", "|---|---|---|---|---|---|"]
        for z in zl:
            if z["phi"] is None:
                md.append(f"| {z['V2']:.0f} | {z['P']} | – | – | – | – |")
            else:
                md.append(f"| {z['V2']:.0f} | {z['P']} | {z['phi']:.1f} | {z['i1_edge']:.2f} | {z['i2_edge']:.2f} | {z['I1rms']:.2f} |")
        md.append("")
        print(key, "done", flush=True)
    # 4. baseline
    b = baseline()
    results["baseline"] = strip(b)
    md += ["## Baseline (ETD34 26:28 concentric + L3 70 µH RM8)", "", HDR, fmt_row(b), "",
           "L3 design (assumed): " + json.dumps(b["L3_design"]), ""]
    json.dump(results, open(os.path.join(OUT, "results.json"), "w"), indent=1, default=float)
    open(os.path.join(OUT, "results.md"), "w").write("\n".join(md))
    print("written", os.path.join(OUT, "results.md"))


if __name__ == "__main__":
    main(quick="--quick" in sys.argv)
