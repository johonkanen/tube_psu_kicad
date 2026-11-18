#!/usr/bin/env python3
"""Tables for the 100-450 V input study with the ICE5AR0680AG (EEL19_DESIGN.md section 14): the
synthetic-waveform design sweep (wide_input.py, out/wide/), the derating, the ngspice cases of the
chosen design (run_flyback.py, ICE5AR model with the 0680AG power stage) and the real-capacitor checks
(ice5ar_checks.py, tag _0680). Writes wide_results.md.

    python3 simulation/flyback/wide_report.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import flyback_sim as fs  # noqa: E402
import options as opts  # noqa: E402
import run_flyback as rf  # noqa: E402

OUT = os.path.join(HERE, "out")
RAILS = list(fs.RAILS)
DN = {"20V": "15V", "5V": "5V", "20V_ISO_SEC": "15V_ISO_SEC", "5V_ISOL": "5V_ISOL", "-5V_SEC": "−5V", "-100V BIAS": "−80V"}
TA = 50.0
P_CTRL = 14.4 * 1.5e-3
RTH = {"min Cu 94 K/W": 94.0, "≈ 3 cm² drain Cu ≈ 70 K/W (assumed)": 70.0}


def f2(x, d=2):
    return "–" if x is None else f"{x:.{d}f}"


def load(name):
    res = {}
    for c in rf.all_cases():
        p = os.path.join(OUT, "results", f"{name}__{c['name']}.json")
        if os.path.exists(p):
            res[c["name"]] = json.load(open(p))
    return res


def sweep_table():
    p = os.path.join(OUT, "wide", "table.json")
    if not os.path.exists(p):
        return []
    rows = json.load(open(p))
    s = ["## Design sweep at 20 W (synthetic waveforms, MKF winding + iGSE core losses)", "",
         "Rcs from the 100 V peak (minimum limit 0.72 V / Rcs ≥ 1.1 × Ipk), Bpk at the maximum limit 0.88 V / Rcs; "
         "ΔT with the ICE5 frequency reduction for that Rcs (fixed 100 kHz in brackets); VDS ≈ 450 V + Vor + 60 V.", "",
         "| candidate | Np | Vor V | Lp µH | gap mm (MKF) | Rcs Ω | Bpk at limit T | 100 V: mode, Ipk A, ΔT K | 200 V | 400 V | 450 V | "
         "winding W (100 / 400 V) | switch W (100 / 450 V) | VDS 450 V | D8 V_R 450 V |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for n, r in rows.items():
        cells = []
        for v in ("100", "200", "400", "450"):
            q = r[v]["freq_red"]
            cells.append(f"{q['mode']} {q['f'] / 1e3:.0f} kHz, {q['ipk']:.2f}, **{q['dT']:.0f}** ({r[v]['fixed100k']['dT']:.0f})")
        s.append(f"| {n} | {r['np']:.0f} | {r['vor']:.0f} | {r['lp_uH']:.0f} | {r['gap_mm']:.2f} | {r['rcs']:.3f} | "
                 f"{r['bpk_lim']:.3f} | " + " | ".join(cells) +
                 f" | {r['100']['freq_red']['winding_W']:.2f} / {r['400']['freq_red']['winding_W']:.2f} | "
                 f"{r['100']['switch']['total']:.2f} / {r['450']['switch']['total']:.2f} | {r['vds_450']:.0f} | {r['vr_d8_450']:.0f} |")
    return s + [""]


def derate_table():
    p = os.path.join(OUT, "wide", "derate.json")
    if not os.path.exists(p):
        return []
    d = json.load(open(p))
    s = ["## Maximum continuous output power vs DC+ (synthetic waveforms)", "",
         "Pmax = min(thermal: ΔT ≤ 60 K at 50 °C ambient; current limit: Ipk ≤ minimum limit 0.72 V / (1.01 Rcs) / 1.1). "
         "`@flux` rows use the lowest Rcs for which Bpk at the maximum limit stays ≤ 0.32 T (what the core can deliver "
         "with that Lp); cells: Pmax W (thermal / current-limit W, mode and ΔT at the thermal limit point).", "",
         "| candidate @ Rcs Ω | Bpk at max limit T | " + " | ".join(f"{v} V" for v in d["vins"]) + " |",
         "|---|---|" + "---|" * len(d["vins"])]
    for n, r in d["rows"].items():
        s.append(f"| {n} | {f2(r.get('bpk_lim'), 3)} | " + " | ".join(
            f"**{r['p'][str(v)]:.1f}** ({r['p_thermal'][str(v)]:.1f} / {f2(r['p_climit'][str(v)], 1)}, {r['mode'][str(v)]}, "
            f"{r['dT'][str(v)]:.0f} K)" for v in d["vins"]) + " |")
    return s + [""]


def spice_tables(name):
    res = load(name)
    if not res:
        return []
    s = [f"## {name} – ngspice (ICE5AR model, 0680AG power stage) every case", "",
         "| case | DC+ V | " + " | ".join(DN[r] for r in RAILS) + " | FB V | f kHz | duty | Pin W | Ipk A | VDS pk V | "
         "D8 V_R V | VCC V | drift 15V mV |",
         "|---|---|" + "---|" * (len(RAILS) + 8)]
    for c in rf.all_cases():
        n = c["name"]
        if n not in res:
            continue
        r = res[n]
        cells = [f"{r[k]:.{1 if k == '-100V BIAS' else 2}f}" for k in RAILS]
        vcc = f"{r['vcc_min']:.1f}–{r['vcc_max']:.1f}" + (f" **{r['vcc_flag']}**" if r.get("vcc_flag") else "")
        s.append(f"| {n} | {c.get('vin', 400):.0f} | " + " | ".join(cells) +
                 f" | {r['fb']:.2f} | {r['fsw'] / 1e3:.0f} | {r['duty']:.2f} | {r['pin']:.2f} | {r['ipri']:.3f} | {r['vcol']:.0f} | "
                 f"{f2(r.get('-100V BIAS vrev'), 0)} | {vcc} | {r['20V drift'] * 1e3:+.0f} |")
    s.append("")
    std = [c["name"] for c in rf.cases()]
    s += ["Range over the 16 standard cases (400 V + nom325): " + ", ".join(
        f"{DN[k]} {min(res[c][k] for c in std if c in res):.2f}–{max(res[c][k] for c in std if c in res):.2f}"
        for k in RAILS if any(c in res for c in std)) + ".", ""]
    # losses
    s += ["Losses (switch from the model incl. its 10 ns gate-RC turn-off overlap = upper bound; windings / core: "
          "losses.py on the simulated currents, MKF upper bound):", "",
          "| case | Pin W | Pout W | switch W | Rcs W | clamp W | winding W | core W | Bpk T (MKF) | Tj CoolMOS °C (" + " / ".join(RTH) + ") |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for c in rf.all_cases():
        n = c["name"]
        if n not in res or not (n.startswith("full") or n.startswith("nom")):
            continue
        r = res[n]
        lp = os.path.join(OUT, "losses", f"{name}.json" if n == "nom" else f"{name}__{n}.json")
        lo = json.load(open(lp)) if os.path.exists(lp) else {}
        pout = sum(r[k] * (c["loads"].get(k, 0)) for k in RAILS)
        pic = r["psw"] + P_CTRL
        tj = " / ".join(f"{TA + rth * pic:.0f}" for rth in RTH.values())
        s.append(f"| {n} | {r['pin']:.2f} | {pout:.1f} (loads only) | {r['psw']:.3f} | {r['prcs']:.3f} | {r['pr72'] + r['pr45']:.3f} | "
                 f"{f2(lo.get('winding_losses_W'))} | {f2(lo.get('core_losses_W_IGSE'), 3)} | {f2(lo.get('B_peak_T'), 3)} | {tj} |")
    return s + [""]


def checks(tag="_0680"):
    d = os.path.join(OUT, "checks")
    if not os.path.isdir(d):
        return []
    fs_ = sorted(f for f in os.listdir(d) if f.startswith("ice_") and f.endswith(f"{tag}.json"))
    if not fs_:
        return []
    s = ["## Checks with the real capacitors and the real FB network (`ice5ar_checks.py --tag _0680`)", ""]
    for f in fs_:
        r = json.load(open(os.path.join(d, f)))
        s.append(f"- **{f[:-5]}** ({r['config']}): " +
                 ", ".join(f"{DN[k]} {r[k]:.3f} [{r[k + ' min']:.3f}–{r[k + ' max']:.3f}]" for k in RAILS) +
                 f"; FB {r['fb']:.2f} V, Pin {r['pin']:.2f} W, VDS {r['vcol']:.0f} V")
        for k, v in r.items():
            if k.startswith("w_"):
                s.append(f"  - {k[2:]}: {v}")
    return s + [""]


def main():
    s = ["# TR1 for 100–450 V DC+ with the ICE5AR0680AG – result tables", "",
         "Generated by `python3 simulation/flyback/wide_report.py` (EEL19_DESIGN.md section 14). Voltages are "
         "magnitudes; 15V = net `20V` in the scripts.", ""]
    s += sweep_table()
    s += derate_table()
    for n in opts.WIDE_ICE_OPTIONS:
        s += spice_tables(n)
    s += checks()
    with open(os.path.join(HERE, "wide_results.md"), "w") as f:
        f.write("\n".join(s) + "\n")
    print("wrote wide_results.md")


if __name__ == "__main__":
    main()
