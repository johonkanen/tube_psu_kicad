#!/usr/bin/env python3
"""Channel-to-channel leakage of the control-card ADC mux, seen from the power board.

Control card (ti60f225_tube_psu_control_card, hardware/sheets/adc.kicad_sch): every J2 analog
pin goes straight (no R/C on the card) to a TMUX1308 source pin; the mux output D drives an
OPA365 follower, then 33 R / 680 p into the ADS7056 (0..3.3 V, 14 bit). The buffer isolates
the ADC kickback, so what limits the channel separation is the mux D node: when the mux
switches, D (C_D(ON) + OPA365 input) still holds the previous channel's voltage and must be
recharged through RON from the power-board output network of the new channel. Whatever has
not settled when the ADC samples is leakage of the previous channel into this one.

Model per channel (the power-board output network from simulation/out/spice/cN.cir, run
simulation/run_sim.py first) + switch + RON + C_D:
  * step run: D precharged to 0 V, the channel at its operating point V0; leakage(t) =
    (V0 - v(D)) / V0 = fraction of the previous channel's voltage still present.
  * injection run: D precharged to V0, the mux injects Q_INJ at the switch instant.
Variants of the power-board network are the candidate fixes. ngspice runs one at a time.

Run:  python3 simulation/spice/mux_settling.py
"""
import math, os, re, shutil, subprocess

SIM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(SIM, "out", "spice")
OUT = os.path.join(SIM, "out", "mux")
os.makedirs(OUT, exist_ok=True)
shutil.copy(os.path.join(SRC, "opamp_macro.lib"), OUT)

# TMUX1308 at VDD 3.3 V (TI SCDS426E, as quoted in the control card's CONVERSION_PLAN.md)
RON = 350.0          # ohm, max (typ 120)
C_D = 40e-12 + 5e-12  # C_D(ON) 40 pF + OPA365 input / trace (assumed 5 pF)
Q_INJ = 1e-12        # charge injection 1 pC (|-1 pC|)
LSB = 3.3 / 2 ** 14
T_SW = 1e-6
DWELL = [0.2e-6, 0.4e-6, 1e-6, 2e-6, 5e-6, 10e-6, 20e-6]


def body(cid):
    txt = open(os.path.join(SRC, f"{cid}.cir")).read()
    txt = txt[:txt.index(".control")]
    return re.sub(r"\s+AC 1\b", "", txt)


def sub(net, old, new):
    assert old in net, old
    return net.replace(old, new)


def run(name, net, out, mode):
    inj = (f"Iinj 0 n_D PULSE(0 {Q_INJ / 1e-9:g} {T_SW:g} 0.1n 0.1n 1n)\n" if mode == "inj" else "")
    cir = f"""{net}
Smux {out} n_x n_ctl 0 swmux
.model swmux sw(vt=0.5 vh=0 ron=1m roff=1e13)
Vctl n_ctl 0 PULSE(0 1 {T_SW:g} 1n 1n 1 2)
Ron n_x n_D {RON:g}
Cd n_D 0 {C_D:g}
Rhold n_D n_pre 1e12
Vpre n_pre 0 DC 0
{inj}
.include opamp_macro.lib
.control
set wr_singlescale
set wr_vecnames
tran 1n {T_SW + 21e-6:g} 0 2n
wrdata {name}.txt v(n_D) v({out})
.endc
.end
"""
    if mode == "inj":
        # precharge D to the channel's operating point: first an op to get V0
        open(os.path.join(OUT, f"{name}_op.cir"), "w").write(
            f"{net}\n.include opamp_macro.lib\n.control\nop\nprint v({out})\n.endc\n.end\n")
        r = subprocess.run(["ngspice", "-b", f"{name}_op.cir"], cwd=OUT, capture_output=True, text=True)
        v0 = float(re.search(r"v\(" + re.escape(out) + r"\)\s*=\s*(\S+)", r.stdout, re.I).group(1))
        cir = cir.replace("Vpre n_pre 0 DC 0", f"Vpre n_pre 0 DC {v0:g}")
    open(os.path.join(OUT, f"{name}.cir"), "w").write(cir)
    subprocess.run(["ngspice", "-b", "-o", f"{name}.log", f"{name}.cir"], cwd=OUT, check=True,
                   capture_output=True)
    rows = [l.split() for l in open(os.path.join(OUT, f"{name}.txt")) if l.strip()]
    data = [[float(x) for x in r] for r in rows[1:]]
    return data  # t, v(D), v(out)


def at(data, t):
    return min(data, key=lambda r: abs(r[0] - t))


def leakage(name, net, out):
    d = run(name + "_step", net, out, "step")
    v0 = at(d, T_SW * 0.5)[2]                     # channel output before the switch
    s = [abs(v0 - at(d, T_SW + t)[1]) / v0 for t in DWELL]
    di = run(name + "_inj", net, out, "inj")
    vi = at(di, T_SW * 0.5)[1]
    inj = [abs(at(di, T_SW + t)[1] - vi) / LSB for t in DWELL]
    return v0, s, inj


def lsb_fs(frac):
    """Leakage fraction -> LSB for a full-scale (3.3 V) previous-channel difference."""
    return frac * 3.3 / LSB


def fmt(frac):
    if frac <= 0:
        return "0"
    l = lsb_fs(frac)
    return f"{20 * math.log10(frac):.0f} dB / {l:.3g}" if l >= 0.01 else f"{20 * math.log10(frac):.0f} dB / <0.01"


CASES = []


def case(label, cid, out, edit=None):
    net = body(cid)
    if edit:
        net = edit(net)
    CASES.append((label, cid, net, out))


# --- as built -----------------------------------------------------------------------------
case("PFC_I1/I2 (100 R + 100 p)", "c1", "n_PFC_I1_MEAS")
case("DHB_I (33 R, C26 na)", "c3", "n_DHB_I_MEAS")
case("HEATER_I (33 R, C10 na)", "c4", "n_HEATER_I_MEAS")
case("VAC (100 R, no C)", "c5", "n_VAC_MEAS")
case("DC_LINK (1 k + 1 n)", "c6", "n_DC_LINK_MEAS")
case("AUX (22k/4.7k + 1 n)", "c7", "n_AUX_MEAS")

# --- candidate fixes ----------------------------------------------------------------------
def vac_cf(net, rout=100, cout=None):
    net = sub(net, "R80 n_1V65_BIAS n_Net__U8 15000", "R80 n_1V65_BIAS n_Net__U8 15000\nCF80 n_1V65_BIAS n_Net__U8 1n")
    net = sub(net, "R49 n_Net__R49_Pad1 n_Net__U8_1 15000", "R49 n_Net__R49_Pad1 n_Net__U8_1 15000\nCF49 n_Net__R49_Pad1 n_Net__U8_1 1n")
    net = sub(net, "R65 n_VAC_MEAS n_Net__R49_Pad1 100", f"R65 n_VAC_MEAS n_Net__R49_Pad1 {rout}" + (f"\nCOUT n_VAC_MEAS 0 {cout}" if cout else ""))
    return net


def dcl(net, cf=None, r2=1000, c4="1e-09"):
    if cf:
        net = sub(net, "R17 n_Net__U6 0 15000", f"R17 n_Net__U6 0 15000\nCF17 n_Net__U6 0 {cf}")
        net = sub(net, "R82 n_Net__U6_1 n_Net__R2_Pad2 15000", f"R82 n_Net__U6_1 n_Net__R2_Pad2 15000\nCF82 n_Net__U6_1 n_Net__R2_Pad2 {cf}")
    net = sub(net, "R2 n_DC_LINK_MEAS n_Net__R2_Pad2 1000", f"R2 n_DC_LINK_MEAS n_Net__R2_Pad2 {r2}")
    return sub(net, "C4 0 n_DC_LINK_MEAS 1e-09", f"C4 0 n_DC_LINK_MEAS {c4}" if c4 else "* C4 removed")


case("VAC fix: Cf 1n (R80/R49), R65 100 R, no C", "c5", "n_VAC_MEAS", lambda n: vac_cf(n))
case("VAC fix: Cf 1n + R65 1 k / 1 n", "c5", "n_VAC_MEAS", lambda n: vac_cf(n, 1000, "1n"))
case("VAC fix: Cf 1n + R65 100 R / 10 n", "c5", "n_VAC_MEAS", lambda n: vac_cf(n, 100, "10n"))
case("DC_LINK fix: Cf 1n, R2 100 R, C4 removed", "c6", "n_DC_LINK_MEAS", lambda n: dcl(n, "1n", 100, None))
case("DC_LINK fix: Cf 1n, R2 100 R, C4 10 n", "c6", "n_DC_LINK_MEAS", lambda n: dcl(n, "1n", 100, "1e-08"))
case("AUX fix: C61 100 n", "c7", "n_AUX_MEAS", lambda n: sub(n, "C61 0 n_AUX_MEAS 1e-09", "C61 0 n_AUX_MEAS 1e-07"))
case("AUX fix: C61 1 u", "c7", "n_AUX_MEAS", lambda n: sub(n, "C61 0 n_AUX_MEAS 1e-09", "C61 0 n_AUX_MEAS 1e-06"))
case("DHB_I with C26 1 n fitted", "c3", "n_DHB_I_MEAS", lambda n: sub(n, "* C26 na not fitted (GND, DHB_I_MEAS)", "C26 0 n_DHB_I_MEAS 1n"))

print(f"TMUX1308 RON {RON:g} ohm (max), C_D {C_D * 1e12:g} pF, injection {Q_INJ * 1e12:g} pC; "
      f"1 LSB = {LSB * 1e6:.0f} uV (14 bit, 3.3 V)")
print("\nLeakage of the previous channel at the sample instant (dB of the voltage difference / "
      "LSB for a 3.3 V difference), and charge-injection error (LSB)\n")
print("| channel network | " + " | ".join(f"{t * 1e6:g} us" for t in DWELL) + " | injection @1 us / 5 us |")
print("|---" * (len(DWELL) + 2) + "|")
for label, cid, net, out in CASES:
    name = re.sub(r"\W+", "_", label).strip("_").lower()[:40]
    v0, s, inj = leakage(name, net, out)
    print(f"| {label} | " + " | ".join(fmt(x) for x in s)
          + f" | {inj[DWELL.index(1e-6)]:.2f} / {inj[DWELL.index(5e-6)]:.2f} |", flush=True)
