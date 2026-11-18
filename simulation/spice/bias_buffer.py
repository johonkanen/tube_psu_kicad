#!/usr/bin/env python3
"""5.2 bias buffer U9 (TLV316 follower, R131 22R, C48 100n): stability and bias-node impedance.

kicad_next/CHANGES_5_2.md 4.1: REF3325 -> R110 1.00k / R3 1.96k + C128 100n -> U9 + input;
U9 output -> R131 22R -> +1V65_BIAS (C48 100n); feedback taken from the U9 output pin (before
the 22R). Loads on the bias node: the + legs of the four current amplifiers and VAC (DC 2.66 kOhm
to ground in parallel, from the 5.2 netlist via extract.bias_network).

The single-pole macromodel of run_ac.py has a resistive Zo and no second pole, so it cannot show
a stability problem. Three op-amp models are compared:
  macro1   the run_ac.py macromodel (A0 100 dB, GBW 10 MHz, Zo 250 ohm)
  macro2   + a second pole at 30 MHz (the TI model's 74 deg follower phase margin at its 16.5 MHz
           unity-gain frequency puts it at ~57 MHz; 30 MHz is the conservative choice) + Zo 250 ohm
  vendor   TI TLV316 PSpice model (sbom975d, Green-Williams-Lis, Zo(f), slew, rails), ngspice psa
Feedback variants:
  as built      IN- = U9 output pin
  from bias     IN- = bias node (after the 22R)                       - for comparison
  split RC      IN- = bias node through 100k, and U9 output through 1n  (DC from the bias node,
                HF from the output pin: removes the 22R drop and the load-dependent bias)
Results: loop gain T(f) (series voltage injection at IN-), unity-gain frequency, phase
margin, gain margin; follower step (10 mV on the + input) overshoot at the U9 output and the
bias node; 1 mA load step on the bias node; |Z| of the bias node at 50 Hz / 10 kHz / 1 MHz and
the resulting VAC (3.012 MOhm from AC2) coupling into the bias.

    python3 simulation/spice/bias_buffer.py          # -> out/5.2/bias_buffer_results.md
"""
import cmath
import math
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["MEAS_SIM_REV"] = "5.2"
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import circuits as C  # noqa: E402
import extract as X  # noqa: E402
import vendor_models as V  # noqa: E402

WORK = C.OUT / "bias_buffer"
P2 = 30e6
R_VAC = 3.012e6        # VAC + leg (3 x 1M + 12k) from AC2 into the bias node


def opamp(model, inp, inn, out):
    m = C.OPAMPS["TLV316IDBVR"]
    if model == "vendor":
        return V.instance("TLV316", "U9", inp, inn, "vcc", "0", out)
    c1 = m["a0"] / (2 * math.pi * m["gbw"] * 1e3)
    lines = [f"G1 0 xa {inp} {inn} {m['a0'] / 1e3:.10g}", "R1 xa 0 1k", f"C1 xa 0 {c1:.10g}"]
    if model == "macro2":
        lines += ["E2 xb 0 xa 0 1", "R2 xb xc 1k", f"C2 xc 0 {1 / (2 * math.pi * 1e3 * P2):.10g}",
                  "E3 xo 0 xc 0 1"]
    else:
        lines += ["E3 xo 0 xa 0 1"]
    lines += [f"RO xo {out} {m['rout']:.10g}"]
    return "\n".join(lines)


def circuit(model, fb, mode):
    """mode: 'loop' (T), 'step' (transient), 'zout' (bias-node impedance)."""
    nl = X.Netlist()
    b = X.bias_network(nl)
    r_load = 1.0 / sum(1.0 / r for r in b["loads"].values())
    vdiv = b["vdiv"]
    inn = "inn"
    lines = [f"* U9 bias buffer, {model}, feedback {fb}, {mode}", "VCC vcc 0 3.3"]
    if model == "vendor":
        lines.insert(1, f".include {V.fetch('TLV316')}")
    if mode == "step":
        lines.append(f"VDIV inp 0 PWL(0 {vdiv:.6g} 10u {vdiv:.6g} 10.01u {vdiv + 0.01:.6g})")
        lines.append("ILOAD bias 0 PWL(0 0 60u 0 60.01u 1m)")
    else:
        lines.append(f"VDIV inp 0 DC {vdiv:.6g}")
    lines += [opamp(model, "inp", inn, "out"),
              f"R131 out bias {b['r_buf']:g}", f"C48 bias 0 {b['c_bias']:g}",
              f"RLOAD bias 0 {r_load:.6g}"]
    fbsrc = {"as built": "out", "from bias": "bias"}.get(fb)
    if mode == "loop":
        # Middlebrook voltage injection in series with IN- (IN- draws no current, so
        # T = -v(return) / v(IN-) is exact); the DC loop stays closed
        if fbsrc:
            lines += [f"VINJ {inn} {fbsrc} DC 0 AC 1"]
        else:
            lines += ["VINJ inn fbn DC 0 AC 1", "RF bias fbn 100k", "CF out fbn 1n"]
    else:
        if fbsrc:
            lines += [f"RFB {fbsrc} {inn} 1m"]
        else:
            lines += ["RF bias inn 100k", "CF out inn 1n"]
        if mode == "zout":
            lines += ["IZ 0 bias DC 0 AC 1"]
    if model == "vendor":
        # the vendor model's operating point needs a start (gmin / source stepping fail)
        lines += [".options reltol=1e-4"]
    lines += [".control", "set wr_singlescale", "set wr_vecnames"]
    if mode == "loop":
        probe = "v(fbn)" if not fbsrc else f"v({fbsrc})"
        lines += ["ac dec 50 10 300meg", f"wrdata loop.txt {probe} v(inn)"]
    elif mode == "zout":
        lines += ["ac dec 20 10 100meg", "wrdata zout.txt v(bias)"]
    else:
        lines += ["tran 2n 120u 0 5n", "wrdata step.txt v(out) v(bias)"]
    lines += [".endc", ".end", ""]
    return "\n".join(lines)


def run(model, fb, mode):
    tag = f"{model}_{fb.replace(' ', '_')}_{mode}"
    d = WORK / tag
    d.mkdir(parents=True, exist_ok=True)
    (d / "c.cir").write_text(circuit(model, fb, mode))
    cmd = ["ngspice", "-b", "c.cir"]
    if model == "vendor":
        cmd[1:1] = ["-D", "ngbehavior=psa"]
    r = subprocess.run(cmd, cwd=d, capture_output=True, text=True, timeout=900)
    (d / "c.log").write_text(r.stdout + r.stderr)
    out = d / {"loop": "loop.txt", "zout": "zout.txt", "step": "step.txt"}[mode]
    if not out.exists():
        raise SystemExit(f"ngspice failed: {d / 'c.log'}")
    return V.read(out)


def margins(rows):
    t = [(r[0], -complex(r[1], r[2]) / complex(r[3], r[4])) for r in rows]
    fu = pm = gm = None
    for (f1, h1), (f2, h2) in zip(t, t[1:]):
        if fu is None and abs(h1) >= 1 > abs(h2):
            fu = f1 * (f2 / f1) ** (math.log(abs(h1)) / (math.log(abs(h1)) - math.log(abs(h2))))
            pm = 180 + math.degrees(cmath.phase(h2))
        if gm is None and h1.imag < 0 <= h2.imag and h2.real < 0:
            gm = -20 * math.log10(abs(h2))
    # unwrapped phase for PM (avoid the +-180 wrap)
    if fu is not None:
        ph, prev = None, 0.0
        for f, h in t:
            p = math.degrees(cmath.phase(h))
            p += 360 * round((prev - p) / 360)
            prev = p
            if f >= fu:
                ph = p
                break
        pm = 180 + ph
    return fu, pm, gm


def step_metrics(rows):
    def seg(t0, t1, col):
        return [(r[0], r[col]) for r in rows if t0 <= r[0] < t1]
    res = {}
    for name, col in (("out", 1), ("bias", 2)):
        s = seg(10e-6, 60e-6, col)
        v0 = seg(9e-6, 10e-6, col)[-1][1]
        vf = s[-1][1]
        pk = max(v for _, v in s)
        res[name] = 100 * (pk - vf) / (vf - v0)
    s = seg(60e-6, 120e-6, 2)
    v0 = seg(59e-6, 60e-6, 2)[-1][1]
    vmin = min(v for _, v in s)
    res["load_dip_mV"] = 1e3 * (v0 - vmin)
    res["load_final_mV"] = 1e3 * (v0 - s[-1][1])
    return res


def zout_at(rows, f):
    r = min(rows, key=lambda x: abs(math.log(x[0] / f)))
    return abs(complex(r[1], r[2]))


def main():
    lines = ["# 5.2 bias buffer U9 – stability (generated by simulation/spice/bias_buffer.py)", "",
             "TLV316 follower, R131 22R, C48 100n, bias loads 2.66 kOhm (DC). T = loop gain broken at "
             "IN-. Step: 10 mV on the + input (overshoot in % of the step at the U9 output and at the "
             "bias node). Load: 1 mA step out of the bias node (dip, final error). |Z| of the bias node, "
             "and the VAC coupling into the bias = |Z(50 Hz)| / 3.012 MOhm.", "",
             "| model | feedback | unity-gain f | phase margin | gain margin | step overshoot out / bias | "
             "1 mA load dip / final | Z bias 50 Hz / 10 kHz / 1 MHz | VAC coupling 50 Hz |",
             "|---|---|---|---|---|---|---|---|---|"]
    for model in ("macro1", "macro2", "vendor"):
        for fb in ("as built", "from bias", "split RC"):
            fu, pm, gm = margins(run(model, fb, "loop"))
            st = step_metrics(run(model, fb, "step"))
            z = run(model, fb, "zout")
            z50, z10k, z1m = (zout_at(z, f) for f in (50, 1e4, 1e6))
            gm_s = f"{gm:.1f} dB" if gm is not None else "none (< 300 MHz)"
            fu_s = f"{fu / 1e6:.3g} MHz" if fu else "n/a (no OP)"
            pm_s = f"{pm:.1f} deg" if fu else "n/a"
            line = (f"| {model} | {fb} | {fu_s} | {pm_s} | {gm_s} | "
                    f"{st['out']:.1f} % / {st['bias']:.1f} % | {st['load_dip_mV']:.2f} / "
                    f"{st['load_final_mV']:.3f} mV | {z50:.3g} / {z10k:.3g} / {z1m:.3g} ohm | "
                    f"{z50 / R_VAC:.2e} |")
            print(line, flush=True)
            lines.append(line)
    lines += ["", "VAC coupling x 325 V peak = bias ripple; divide by the channel gain for the "
              "equivalent current (PFC 82.4 mV/A, DHB 0.182 V/A, HEATER 0.4 V/A).", ""]
    (C.OUT / "bias_buffer_results.md").write_text("\n".join(lines))
    print(f"-> {C.OUT / 'bias_buffer_results.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
