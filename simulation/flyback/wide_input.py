#!/usr/bin/env python3
"""Design space of TR1 on the EEL19 for a 100-450 V DC input (EEL19_DESIGN.md section 14),
controller ICE5AR0680AG (100 kHz peak-current mode, CCM with slope compensation allowed).

The winding structure is the TIW build `eel19_tiw_sandwich_s_pre3` (P1 | S15 | SHV | S5+SN5 | A5 |
A15 | P2, TEX-E secondaries). Only the primary changes: turns per half (Vor = Np x 0.935 V/turn,
the secondary turns 16 / 84 / 6 / 6 / 6 / 16 and with them the cross regulation stay), wire, and Lp
(gap fitted by MKF as before, spacer gap).

Candidates: options.eel19_wide(nh, lp_uh, wire, sec), name eel19w_n<nh>_l<lp>_a<awg>[_t]; "_t" = thin
strands (TEX-E 0.20 for every isolated winding, AWG32 for the aux windings), see options.WIDE_SEC.

For each candidate and operating point (Vin, Pout) the ideal flyback waveforms are synthesised
(no leakage; CCM or DCM from Lp and the power; 100 kHz, or with rcs the ICE5 frequency reduction):
- primary P1 = P2: Imin -> Ipk ramp during D*T, zero during the off-time;
- secondary k during the off-time: alpha_k * (Np / N_k) * i_mag(t), alpha_k = N_k I_k / sum(N_j I_j),
  so every winding carries its DC load current and the ampere-turns add up to the magnetising
  ampere-turns (the field MKF sees, gap fringing included, is the real one);
and MKF (PyOpenMagnetics, same models as losses.py) gives the winding losses (DC + skin +
proximity with gap fringing, 60 degC) and the core loss (iGSE, PC40) of the real coil geometry.
ΔT from the section 5 surface formula ΔT = (P[mW] / 19.6 cm²)^0.833.

    python3 simulation/flyback/wide_input.py check                    # synthetic vs simulated losses (full15, today's design)
    python3 simulation/flyback/wide_input.py sweep [nh,lp,awg[,t] ...] # 20 W at 100/200/400/450 V, printed
    python3 simulation/flyback/wide_input.py table <candidate> ...     # Rcs, Bpk at the limit, ΔT -> out/wide/table.json
    python3 simulation/flyback/wide_input.py derate <candidate> [rcs|flux] [p_hi]   # Pmax vs DC+ -> out/wide/derate.json

Results are cached in out/wide/ (delete to rerun). One MKF process, no ngspice.
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import flyback_sim as fs  # noqa: E402
import om_model as m  # noqa: E402
import options as opts  # noqa: E402
import run_flyback as rf  # noqa: E402

OUT = os.path.join(HERE, "out", "wide")
F = 100e3
VT = 0.935                 # V per turn during the off-time (5V + D6 drop on the 6 T A5 winding)
AE = 23.4e-6               # EEL19 Ae (seller / catalogue)
B_LIM = 0.32               # T, Bpk allowed at the maximum current limit (PC40 Bsat ~0.39 T at 100 degC)
AREA_CM2 = 19.6            # transformer surface (section 5)
DT_LIM = 60.0              # K: 50 degC ambient + 60 K = 110 degC surface, 10 K below the TEX-E 120 degC class
VCS_MIN, VCS_TYP, VCS_MAX = 0.72, 0.80, 0.88
ETA = 0.86                 # Pout / Pin used for the synthetic waveforms (the simulations give the real one)
RDS_HOT = 1.27             # ICE5AR0680AG RDS(on) at 125 degC
COER = 24e-12              # Co(er) 0-500 V
C_EXT = 10e-12             # transformer / layout capacitance at the drain (assumed, as section 13)
RTH_JA = 94.0              # K/W, minimum drain copper (datasheet); ~70 K/W with ~2-3 cm2 drain copper (assumed)


# ---------------------------------------------------------------------------------------
# loads: the full15 pattern scaled; fixed parts (preloads, bleeders, VCC, dividers) on top
# ---------------------------------------------------------------------------------------
VNOM = {"20V": 15.0, "5V": 5.0, "20V_ISO_SEC": 15.0, "5V_ISOL": 5.0, "-5V_SEC": 5.0, "-100V BIAS": 82.0}
WIND = {"20V": "A15", "5V": "A5", "20V_ISO_SEC": "S15", "5V_ISOL": "S5", "-5V_SEC": "SN5", "-100V BIAS": "SHV"}
PRELOAD = opts.PRELOAD_EEL
BLEED = {"20V_ISO_SEC": 12.1e3, "5V_ISOL": 12.1e3, "-5V_SEC": 12.1e3, "-100V BIAS": 12.1e3}
FIXED_I = {"20V": 7.8e-3 + 15.0 / fs.R_AUX_MEAS, "5V": 5.0 / 138.6e3}


def rail_currents(pout: float) -> dict:
    """DC current of every rail for a total output power pout (W): the full15 load pattern
    (run_flyback.FULL15) scaled, plus the fixed loads."""
    fixed = {r: FIXED_I.get(r, 0.0) + (VNOM[r] / PRELOAD[r] if r in PRELOAD else 0.0)
             + (VNOM[r] / BLEED[r] if r in BLEED else 0.0) for r in VNOM}
    p_fixed = sum(VNOM[r] * fixed[r] for r in VNOM)
    p_var = sum(VNOM[r] * rf.FULL15[r] for r in VNOM)
    k = max(0.0, (pout - p_fixed) / p_var)
    return {r: fixed[r] + k * rf.FULL15[r] for r in VNOM}


# ---------------------------------------------------------------------------------------
# candidates: TIW sandwich_s with a modified primary
# ---------------------------------------------------------------------------------------
cand_name = opts.wide_name          # eel19w_n<turns per half>_l<Lp uH>_a<AWG>
register = opts.register_wide      # options.eel19_wide: sandwich_s with the modified primary


# ---------------------------------------------------------------------------------------
# operating point
# ---------------------------------------------------------------------------------------
def f_of_vfb(vfb):
    """ICE5 frequency reduction (datasheet figure 8): 100 kHz above VFB 1.70 V, 43 kHz below 1.35 V."""
    return 43e3 + (100e3 - 43e3) * min(1.0, max(0.0, (vfb - 1.35) / 0.35))


def _op_at_f(np_tot, lp, vin, pin, f):
    vor = np_tot * VT
    T = 1.0 / f
    ipk_dcm = math.sqrt(2 * pin / (lp * f))
    ton, toff = lp * ipk_dcm / vin, lp * ipk_dcm / vor
    if ton + toff <= T:
        mode, d, imin, ipk = "DCM", ton / T, 0.0, ipk_dcm
    else:
        mode = "CCM"
        d = vor / (vor + vin)
        iavg_on = pin / vin / d
        di = vin * d * T / lp
        imin, ipk = iavg_on - di / 2, iavg_on + di / 2
        toff = (1 - d) * T
    irms = math.sqrt(d * (ipk ** 2 + ipk * imin + imin ** 2) / 3)
    return {"mode": mode, "D": d, "imin": imin, "ipk": ipk, "irms": irms, "toff": toff, "vor": vor, "pin": pin, "f": f}


def vfb_of(op, rcs):
    """FB voltage of the PWM comparator at turn-off (equation 4, slope compensation above 40 % duty)."""
    return 2.03 * op["ipk"] * rcs + 0.50 + 0.050 * max(0.0, (op["D"] - 0.4) / op["f"] * 1e6)


def operating_point(np_tot: float, lp: float, vin: float, pout: float, eta=ETA, f=F, rcs=None) -> dict:
    """Ideal waveform parameters: mode, D, Imin, Ipk, Irms of the primary, toff, f. With rcs the
    switching frequency follows the ICE5 frequency reduction (FB from the peak current)."""
    pin = pout / eta
    if not rcs:
        return _op_at_f(np_tot, lp, vin, pin, f)
    lo, hi = 43e3, 100e3
    if f_of_vfb(vfb_of(_op_at_f(np_tot, lp, vin, pin, hi), rcs)) >= hi:
        op = _op_at_f(np_tot, lp, vin, pin, hi)
    else:
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            if f_of_vfb(vfb_of(_op_at_f(np_tot, lp, vin, pin, mid), rcs)) > mid:
                lo = mid
            else:
                hi = mid
        op = _op_at_f(np_tot, lp, vin, pin, 0.5 * (lo + hi))
    op["vfb"] = vfb_of(op, rcs)
    op["rcs"] = rcs
    return op


def waveforms(om: dict, op: dict, pout: float, vin: float, lp: float, npts=400):
    f = op["f"]
    names, turns = om["names"], om["turns"]
    np_tot = sum(n for k, n in zip(names, turns) if k in ("P1", "P2", "P"))
    T = 1.0 / f
    t = np.linspace(0, T, npts, endpoint=False)
    ton = op["D"] * T
    ip = np.where(t < ton, op["imin"] + (op["ipk"] - op["imin"]) * t / max(ton, 1e-12), 0.0)
    im = np.where(t < ton, ip, np.maximum(0.0, op["ipk"] - op["vor"] / lp * (t - ton)))
    if op["mode"] == "CCM":
        im = np.where(t < ton, ip, op["ipk"] - (op["ipk"] - op["imin"]) * (t - ton) / (T - ton))
    ioff = np.where(t >= ton, im, 0.0)
    ic = rail_currents(pout)
    nk = {WIND[r]: dict(zip(names, turns))[WIND[r]] for r in ic}
    at = {WIND[r]: nk[WIND[r]] * ic[r] for r in ic}
    tot = sum(at.values())
    cur = {}
    for n in names:
        if n in ("P1", "P2", "P"):
            cur[n] = ip
        else:
            cur[n] = at[n] / tot * np_tot / nk[n] * ioff
    v = np.where(t < ton, vin, np.where(ioff > 1e-6, -op["vor"], 0.0))
    return t, cur, v


def losses(name: str, vin: float, pout: float, eta=ETA, force=False, rcs=None) -> dict:
    """Synthetic-waveform MKF losses at (vin, pout); rcs: frequency reduction from the peak current
    (None = fixed 100 kHz)."""
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{name}__{int(vin)}V_{pout:.1f}W" + (f"_rcs{rcs:.3f}" if rcs else "") + ".json")
    if os.path.exists(path) and not force:
        return json.load(open(path))
    import PyOpenMagnetics as P
    om = rf.om_analysis(name)
    opt = opts.get(name)
    m.use_core(opt.get("core"))
    coil, rep = m.build_coil(opt)
    core = m.make_core(om["gap"], opt.get("gap_kind", "subtractive"))
    names = om["names"]
    lp = sum(om["L"][i][j] for i, a in enumerate(names) for j, b in enumerate(names) if a in ("P1", "P2") and b in ("P1", "P2"))
    np_tot = sum(n for k, n in zip(names, om["turns"]) if k in ("P1", "P2"))
    op = operating_point(np_tot, lp, vin, pout, eta, rcs=rcs)
    t, cur, v = waveforms(om, op, pout, vin, lp)
    F = op["f"]
    tt = list(map(float, np.append(t, 1.0 / F)))
    exc = [{"name": n, "frequency": F,
            "current": {"waveform": {"data": list(map(float, np.append(cur[n], cur[n][0]))), "time": tt}}} for n in names]
    exc[0]["voltage"] = {"waveform": {"data": list(map(float, np.append(v, v[0]) * om["turns"][0] / np_tot)), "time": tt}}
    P.set_settings({"inputsTrimHarmonics": False, "harmonicAmplitudeThresholdQuickMode": False})
    wl = P.calculate_winding_losses({"core": core, "coil": coil},
                                    {"name": "op", "conditions": {"ambientTemperature": 40.0}, "excitationsPerWinding": exc}, 60.0)
    per, ohm = {}, {}
    for k, p in enumerate(wl.get("windingLossesPerWinding") or []):
        o_ = (p.get("ohmicLosses") or {}).get("losses", 0.0)
        tot = o_
        for key in ("skinEffectLosses", "proximityEffectLosses"):
            tot += sum((p.get(key) or {}).get("lossesPerHarmonic") or [])
        per[p.get("name", names[k])] = tot
        ohm[p.get("name", names[k])] = o_
    # core: one-winding coil with the full primary turns (as losses.py)
    simple = P.wind({"bobbin": m.bobbin(), "functionalDescription": [
        {"name": "P", "numberTurns": int(np_tot), "numberParallels": 1, "wire": m.wire(opts.W34), "isolationSide": "primary"}]},
        1, [1], [0], [[0, 0]])
    op1 = {"name": "op", "conditions": {"ambientTemperature": 40.0}, "excitationsPerWinding": [
        {"name": "P", "frequency": F, "current": {"waveform": {"data": list(map(float, np.append(cur[names[0]], cur[names[0]][0]))), "time": tt}},
         "voltage": {"waveform": {"data": list(map(float, np.append(v, v[0]))), "time": tt}}}]}
    inputs = {"designRequirements": {"magnetizingInductance": {"nominal": lp}, "turnsRatios": []}, "operatingPoints": [op1]}
    try:
        cl = P.calculate_core_losses(core, simple, inputs, {"coreLosses": "IGSE", "reluctance": "ZHANG"})
        pcore, bac = cl.get("coreLosses"), cl.get("magneticFluxDensityAcPeak")
    except Exception as e:  # noqa: BLE001
        pcore, bac = None, str(e)
    # hand flux: Bpk at the operating peak, Bac from the ripple
    bpk = lp * op["ipk"] / (np_tot * AE)
    bac_hand = lp * (op["ipk"] - op["imin"]) / 2 / (np_tot * AE)
    pw = float(wl.get("windingLosses"))
    ptot = pw + (pcore or 0.0)
    r = {"name": name, "vin": vin, "pout": pout, "eta": eta, "lp": lp, "np": np_tot, "gap": om["gap"], **op,
         "winding_W": pw, "winding_ohmic_W": sum(ohm.values()), "per_winding_W": per, "core_W": pcore,
         "bac_mkf": bac, "bpk": bpk, "bac": bac_hand, "total_W": ptot,
         "dT": (ptot * 1e3 / AREA_CM2) ** 0.833, "fits": rep["fits"], "build_mm": rep["radial_build_mm"],
         "rms": {n: float(np.sqrt(np.mean(cur[n] ** 2))) for n in names},
         "rdc": dict(zip(names, om["Rdc"]))}
    json.dump(r, open(path, "w"), indent=1)
    return r


# ---------------------------------------------------------------------------------------
# switch, stresses, current limit
# ---------------------------------------------------------------------------------------
def switch_loss(op: dict, vin: float, ron=RDS_HOT):
    """CoolMOS: conduction (hot RDS(on)) + capacitive turn-on (CCM: at Vin + Vor; DCM: on average
    at Vin, fixed frequency, random point of the ring) + turn-off overlap (~10 ns effective)."""
    f = op.get("f", F)
    pc = op["irms"] ** 2 * ron
    von = vin + op["vor"] if op["mode"] == "CCM" else vin
    pcap = 0.5 * (COER + C_EXT) * von ** 2 * f
    pon = 0.5 * von * op["imin"] * 30e-9 * f            # CCM: hard turn-on overlap, 30 ns rise
    poff = 0.5 * (vin + op["vor"] + 60) * op["ipk"] * 10e-9 * f
    return {"cond": pc, "cap": pcap, "on": pon, "off": poff, "total": pc + pcap + pon + poff}


def rcs_for(ipk_100: float, margin=1.10, slope=0.0):
    """Rcs so that the minimum current limit (VCS_N 0.72 V, Rcs +1 %) covers margin x the 100 V
    full-power peak; slope: CS-referred slope-compensation voltage at turn-off (conservative: if the
    ramp also reaches the current-limit comparator)."""
    return (VCS_MIN - slope) / (margin * ipk_100) / 1.01


def slope_check(op: dict, vin: float, lp: float, rcs: float, f=F):
    """Subharmonic stability in CCM: the CS-referred compensation slope (MCOMP 50 mV/us / GPWM
    2.03 = 24.6 mV/us, 41 mV/us min -> 20 mV/us) must exceed (m2 - m1) / 2 of the sensed current."""
    m1 = vin / lp * rcs * 1e-6            # V/us
    m2 = op["vor"] / lp * rcs * 1e-6
    need = max(0.0, (m2 - m1) / 2)
    return {"m1": m1, "m2": m2, "need_mV_us": need * 1e3, "have_mV_us": 41.0 / 2.03,
            "ok": op["mode"] == "DCM" or op["D"] < 0.5 or 41.0 / 2.03 >= need * 1e3}


# ---------------------------------------------------------------------------------------
SWEEP = [  # (turns per half, Lp uH, wire)
    (52, 600, "32"),                                  # today's design
    (52, 900, "32"),
    (64, 900, "32"), (64, 1200, "32"),
    (70, 1000, "32"), (70, 1400, "32"),
    (76, 1000, "32"), (76, 1200, "32"), (76, 1600, "32"), (76, 1200, "31"),
    (82, 1400, "32"), (82, 1800, "32"),
]


def evaluate(nh, lp_uh, wire="32", sec="std", vins=(100, 200, 400, 450), pout=20.0):
    n = register(nh, lp_uh, wire, sec)
    rows = {}
    for vin in vins:
        r = losses(n, vin, pout)
        rows[vin] = r
    return n, rows


def pmax_at(name, vin, p_lo=10.0, p_hi=20.0, rcs=None, p_cap=None):
    """Highest Pout (W) with ΔT <= DT_LIM, from losses at p_lo and p_hi (loss ~ a + b P^2 fit)."""
    a = losses(name, vin, p_lo, rcs=rcs)
    b = losses(name, vin, p_hi, rcs=rcs)
    if b["dT"] <= DT_LIM:
        return p_hi, b
    plim = (DT_LIM ** (1 / 0.833)) * AREA_CM2 / 1e3          # W of loss allowed
    # P_loss = c0 + c2 * P^2
    c2 = (b["total_W"] - a["total_W"]) / (p_hi ** 2 - p_lo ** 2)
    c0 = a["total_W"] - c2 * p_lo ** 2
    p = math.sqrt(max(0.0, (plim - c0) / c2))
    r = losses(name, vin, round(p, 1), rcs=rcs)
    # refine: secant on the total loss through the last two points (the quadratic fit is a few % off)
    pa, la = p_hi, b["total_W"]
    for _ in range(3):
        pb, lb = round(p, 1), r["total_W"]
        if abs(lb / plim - 1) < 0.01 or pb == pa:
            break
        p = pb + (plim - lb) * (pb - pa) / (lb - la)
        pa, la = pb, lb
        r = losses(name, vin, round(p, 1), rcs=rcs)
    return round(p, 1), r


def design_row(name, pout=20.0):
    """One candidate at pout: Rcs from the 100 V peak, Bpk at the maximum current limit, losses /
    ΔT at 100-450 V (fixed 100 kHz and with the frequency reduction of that Rcs), stresses."""
    om = rf.om_analysis(name)
    names = om["names"]
    lp = sum(om["L"][i][j] for i, a in enumerate(names) for j, b in enumerate(names) if a in ("P1", "P2") and b in ("P1", "P2"))
    np_tot = sum(n for k, n in zip(names, om["turns"]) if k in ("P1", "P2"))
    op100 = operating_point(np_tot, lp, 100.0, pout)
    rcs = rcs_for(op100["ipk"])
    ilim_max = VCS_MAX / (rcs * 0.99)
    row = {"name": name, "np": np_tot, "vor": np_tot * VT, "lp_uH": lp * 1e6, "gap_mm": om["gap"] * 1e3, "rcs": rcs,
           "ilim_min": VCS_MIN / (rcs * 1.01), "ilim_max": ilim_max, "bpk_lim": lp * ilim_max / (np_tot * AE),
           "vds_450": 450 + np_tot * VT + 60, "vr_d8_450": 450 * 84 / np_tot + 82, "vr_d5_450": 450 * 16 / np_tot + 15,
           "slope100": slope_check(op100, 100.0, lp, rcs)}
    for vin in (100, 200, 400, 450):
        a = losses(name, vin, pout)
        b = losses(name, vin, pout, rcs=round(rcs, 3))
        row[vin] = {"fixed100k": {k: a[k] for k in ("mode", "D", "ipk", "irms", "bpk", "winding_W", "winding_ohmic_W", "core_W", "dT")},
                    "freq_red": {k: b[k] for k in ("mode", "D", "ipk", "irms", "bpk", "winding_W", "winding_ohmic_W", "core_W", "dT", "f")},
                    "switch": switch_loss(b, vin)}
    return row


def lp_np(name):
    om = rf.om_analysis(name)
    names = om["names"]
    lp = sum(om["L"][i][j] for i, a in enumerate(names) for j, b in enumerate(names) if a in ("P1", "P2") and b in ("P1", "P2"))
    return lp, sum(n for k, n in zip(names, om["turns"]) if k in ("P1", "P2"))


def rcs_flux_min(lp, np_tot):
    """Lowest Rcs for which Bpk at the maximum current limit (0.88 V / (0.99 Rcs)) stays <= B_LIM."""
    return VCS_MAX / 0.99 / (B_LIM * np_tot * AE / lp)


def p_current_limit(lp, np_tot, vin, rcs, margin=1.10):
    """Output power at which the peak current reaches the minimum current limit / margin."""
    ilim = VCS_MIN / (rcs * 1.01) / margin
    lo, hi = 1.0, 60.0
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        if operating_point(np_tot, lp, vin, mid, rcs=rcs)["ipk"] < ilim:
            lo = mid
        else:
            hi = mid
    return lo


def ensure(n):
    """Register a candidate from its name eel19w_n<nh>_l<lp>_a<awg>[_<sec>]."""
    if n not in opts.OPTIONS:
        parts = n.split("_")[1:]
        register(int(parts[0][1:]), float(parts[1][1:]), parts[2][1:], parts[3] if len(parts) > 3 else "std")
    return n


def main(argv=None):
    argv = argv or sys.argv[1:]
    cmd = argv[0] if argv else "sweep"
    if cmd == "check":
        # today's design at full15 / 400 V: synthetic waveforms vs the simulated ICE5AR waveforms
        n = register(52, 600, "32")
        r = losses(n, 400, 15.0, eta=0.86)
        print(json.dumps({k: r[k] for k in ("mode", "D", "ipk", "irms", "winding_W", "core_W", "per_winding_W")}, indent=1))
        return 0
    if cmd == "sweep":
        sel = SWEEP
        if len(argv) > 1:
            sel = [tuple([int(x.split(",")[0]), float(x.split(",")[1])] + x.split(",")[2:]) for x in argv[1:]]
        out = {}
        for spec in sel:
            n, rows = evaluate(*spec)
            out[n] = rows
            for vin, r in rows.items():
                sw = switch_loss(r, vin)
                print(f"{n:24s} {vin:4.0f} V: {r['mode']} D={r['D']:.2f} Ipk={r['ipk']:.3f} Irms={r['irms']:.3f} "
                      f"Bpk={r['bpk']:.3f} wind={r['winding_W']:.2f} (ohm {r['winding_ohmic_W']:.2f}) core={r['core_W']:.3f} "
                      f"dT={r['dT']:.0f} sw={sw['total']:.2f} fits={r['fits']} build={r['build_mm']:.2f}", flush=True)
        return 0
    if cmd == "table":
        # python3 wide_input.py table <candidate> ... : design rows (json) -> out/wide/table.json
        rows = {}
        for n in argv[1:]:
            ensure(n)
            r = design_row(n)
            rows[n] = r
            print(f"{n}: Vor {r['vor']:.0f} V, Lp {r['lp_uH']:.0f} uH, gap {r['gap_mm']:.3f} mm, Rcs {r['rcs']:.3f}, "
                  f"Ilim {r['ilim_min']:.2f}-{r['ilim_max']:.2f} A, Bpk(lim) {r['bpk_lim']:.3f} T, VDS450 ~{r['vds_450']:.0f} V, "
                  f"D8 {r['vr_d8_450']:.0f} V | " + " | ".join(
                      f"{v} V: {r[v]['freq_red']['mode']} {r[v]['freq_red']['f'] / 1e3:.0f} kHz Ipk {r[v]['freq_red']['ipk']:.3f} "
                      f"dT {r[v]['freq_red']['dT']:.0f} ({r[v]['fixed100k']['dT']:.0f}) sw {r[v]['switch']['total']:.2f}"
                      for v in (100, 200, 400, 450)), flush=True)
        p = os.path.join(OUT, "table.json")
        old = json.load(open(p)) if os.path.exists(p) else {}
        old.update(rows)
        json.dump(old, open(p, "w"), indent=1)
        return 0
    if cmd == "derate":
        # python3 wide_input.py derate <candidate> [rcs] [p_hi]: Pmax (ΔT <= 60 K) vs DC+ -> out/wide/derate.json
        n = argv[1]
        ensure(n)
        lp, np_tot = lp_np(n)
        # rcs: given, or "flux" = the lowest Rcs the flux limit allows (the most the core can deliver)
        rcs = rcs_flux_min(lp, np_tot) if len(argv) > 2 and argv[2] == "flux" else (float(argv[2]) if len(argv) > 2 else None)
        rcs = round(rcs, 3) if rcs else rcs
        p_hi = float(argv[3]) if len(argv) > 3 else 20.0
        vins = (100, 125, 150, 200, 300, 400, 450)
        row = {"rcs": rcs, "p": {}, "p_thermal": {}, "p_climit": {}, "mode": {}, "dT": {}, "ipk": {}, "bpk": {},
               "bpk_lim": lp * VCS_MAX / (0.99 * rcs) / (np_tot * AE) if rcs else None}
        for vin in vins:
            pth, r = pmax_at(n, vin, p_hi=p_hi, rcs=rcs)
            pcl = p_current_limit(lp, np_tot, vin, rcs) if rcs else None
            p = min(pth, pcl) if pcl else pth
            row["p"][vin], row["p_thermal"][vin], row["p_climit"][vin] = p, pth, pcl
            row["mode"][vin], row["dT"][vin] = r["mode"], r["dT"]
            row["ipk"][vin], row["bpk"][vin] = r["ipk"], r["bpk"]
            print(f"{n} {vin} V: Pmax {p:.1f} W (thermal {pth} W at dT {r['dT']:.0f} K, current limit "
                  f"{(pcl or 0):.1f} W; {r['mode']}, f {r['f'] / 1e3:.0f} kHz, Ipk {r['ipk']:.3f} A, Bpk {r['bpk']:.3f} T)", flush=True)
        n = n + (f"@{rcs:.3f}" if rcs else "")
        path = os.path.join(OUT, "derate.json")
        d = json.load(open(path)) if os.path.exists(path) else {"vins": list(vins), "rows": {}}
        d["rows"][n] = row
        json.dump(d, open(path, "w"), indent=1)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
