#!/usr/bin/env python3
"""ADC mux leakage with an INA296B current-sense amplifier driving the J2 pin (NEXT_REVISION.md 4.10).

Same switch model as mux_settling.py (TMUX1308 RON 350 ohm max, C_D 40 pF + 5 pF, the mux node
precharged to 0 V = previous channel, 1 pC charge injection not repeated here), but the source is
an INA296 output: the datasheet gives 1.1 MHz bandwidth at every gain, slew 5-8 V/us, max 1 nF
capacitive load, no output impedance curve - so the output stage is modelled as a follower whose
loop has GBW = 1.1 MHz and an open-loop output resistance RO (closed-loop Zout = RO / (1 + A(f)),
i.e. it rises to RO above 1.1 MHz). RO 50 / 200 ohm bracket it. Output network variants: the
present PFC_I network (100 ohm + 100 pF), DHB_I style (33 ohm, no C), and 100 ohm + 1 nF.

Leakage = remaining fraction of the step at the sample instant, in LSB for a 3.3 V difference
(14 bit ADS7056, 0-3.3 V). Run: python3 simulation/spice/mux_ina296.py (one ngspice at a time).
"""
import math, os, subprocess

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out", "mux_ina296")
os.makedirs(OUT, exist_ok=True)
RON, C_D, T_SW, V0 = 350.0, 45e-12, 1e-6, 3.0
LSB = 3.3 / 2 ** 14
DWELL = [0.2e-6, 0.4e-6, 0.7e-6, 1e-6, 1.5e-6, 2e-6, 3e-6, 5e-6]
GBW, A0 = 1.1e6, 1e5


def run(name, ro, rout, cout):
    c1 = A0 / (2 * math.pi * 1e3 * GBW)
    cap = f"Cout n_pin 0 {cout:g}\n" if cout else ""
    cir = f"""* INA296 output model + J2 network + TMUX1308
Vin n_in 0 DC {V0}
G1 0 x n_in n_pin_fb {A0 / 1e3:g}
R1 x 0 1k
C1 x 0 {c1:g}
E1 o 0 x 0 1
Ro o n_amp {ro:g}
Rfb n_amp n_pin_fb 1m
Rout n_amp n_pin {rout:g}
{cap}Smux n_pin n_x n_ctl 0 swmux
.model swmux sw(vt=0.5 vh=0 ron=1m roff=1e13)
Vctl n_ctl 0 PULSE(0 1 {T_SW:g} 1n 1n 1 2)
Ron n_x n_D {RON:g}
Cd n_D 0 {C_D:g}
.ic v(n_D)=0
.control
set wr_singlescale
set wr_vecnames
tran 1n {T_SW + 6e-6:g} 0 2n
wrdata {name}.txt v(n_D) v(n_pin)
.endc
.end
"""
    open(os.path.join(OUT, name + ".cir"), "w").write(cir)
    subprocess.run(["ngspice", "-b", "-o", name + ".log", name + ".cir"], cwd=OUT, check=True, capture_output=True)
    rows = [l.split() for l in open(os.path.join(OUT, name + ".txt")) if l.strip()]
    data = [[float(x) for x in r] for r in rows[1:]]
    at = lambda t: min(data, key=lambda r: abs(r[0] - t))
    v0 = at(T_SW * 0.9)[2]
    return [abs(v0 - at(T_SW + t)[1]) / v0 * 3.3 / LSB for t in DWELL]


print(f"INA296 model: follower GBW {GBW / 1e6:g} MHz, RO open loop; TMUX1308 RON {RON:g} ohm, C_D {C_D * 1e12:g} pF; "
      f"LSB = {LSB * 1e6:.0f} uV\n")
print("| output network | RO | " + " | ".join(f"{t * 1e6:g} us" for t in DWELL) + " |")
print("|---" * (len(DWELL) + 2) + "|")
for label, rout, cout in (("100 R + 100 pF (PFC_I today)", 100, 100e-12), ("33 R, no C (DHB_I today)", 33, None),
                          ("100 R + 1 nF", 100, 1e-9)):
    for ro in (50, 200):
        name = f"ina_{rout}_{int((cout or 0) * 1e12)}p_ro{ro}"
        lsb = run(name, ro, rout, cout)
        print(f"| {label} | {ro} | " + " | ".join(f"{x:.2f}" if x >= 0.01 else "0" for x in lsb) + " |", flush=True)
