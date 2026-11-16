#!/usr/bin/env python3
"""What-if ngspice runs of the fixes proposed in simulation/FINDINGS.md.

Builds variants of the reference netlists simulation/out/spice/cN.cir (run
simulation/run_sim.py first), runs ngspice one at a time into simulation/out/whatif/ and
prints the tables used in FINDINGS.md.

Run:  python3 simulation/spice/whatif_fixes.py
"""
import math, os, re, shutil, subprocess, sys

SIM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(SIM, "out", "spice")
OUT = os.path.join(SIM, "out", "whatif")
os.makedirs(OUT, exist_ok=True)
shutil.copy(os.path.join(SRC, "opamp_macro.lib"), OUT)
FREQS = [50, 1e3, 10e3, 100e3, 1e6, 10e6, 20e6, 50e6]


def body(cid):
    txt = open(os.path.join(SRC, f"{cid}.cir")).read()
    return txt[:txt.index(".control")]


def run(name, netlist, src, outs):
    """AC from source `src` (AC 1 set on it) to the nodes `outs` -> {node: [(f, mag, deg)]}."""
    lines = []
    for ln in netlist.splitlines():
        ln = re.sub(r"\s+AC 1\b", "", ln)
        if ln.split() and ln.split()[0] == src:
            ln += " AC 1"
        lines.append(ln)
    vecs = " ".join(f"v({o})" for o in outs)
    cir = "\n".join(lines) + f"""
.control
set wr_singlescale
set wr_vecnames
ac dec 50 1 5e7
wrdata {name}.txt {vecs}
.endc
.end
"""
    open(os.path.join(OUT, f"{name}.cir"), "w").write(cir)
    subprocess.run(["ngspice", "-b", "-o", f"{name}.log", f"{name}.cir"], cwd=OUT, check=True,
                   capture_output=True)
    rows = [l.split() for l in open(os.path.join(OUT, f"{name}.txt")) if l.strip()]
    hdr, data = rows[0], [[float(x) for x in r] for r in rows[1:]]
    res = {}
    for o in outs:
        i = hdr.index(f"v({o})".lower()) if f"v({o})".lower() in hdr else hdr.index(f"v({o})")
        res[o] = [(r[0], math.hypot(r[i], r[i + 1]), math.degrees(math.atan2(r[i + 1], r[i])))
                  for r in data]
    return res


def at(resp, f):
    return min(resp, key=lambda r: abs(math.log(r[0] / f)))


def f3db(resp):
    g0 = resp[0][1]
    for f, m, _ in resp:
        if m < g0 / math.sqrt(2):
            return f
    return None


def table(title, variants, node, scale=1.0, unit=""):
    print(f"\n### {title}  ({node}, x{scale:g} {unit})")
    print("| variant | " + " | ".join(f"{f:g} Hz" for f in FREQS) + " | -3 dB |")
    for vname, resp in variants:
        r = resp[node]
        cells = [f"{20*math.log10(at(r, f)[1]*scale):.1f} dB" for f in FREQS]
        fc = f3db(r)
        print(f"| {vname} | " + " | ".join(cells) + (f" | {fc/1e3:.1f} kHz |" if fc else " | none |"))


def sub(net, old, new):
    assert old in net, old
    return net.replace(old, new)


def buffered_bias_iso(net, riso="22"):
    """Follower -> Riso -> +2V5_BIAS with C48 kept on the bias node; 100n added on the divider."""
    net = sub(net, "R110 n_2V5_BIAS n_Net__REF1_VOUT 220", "R110 n_BIAS_DIV n_Net__REF1_VOUT 220")
    net = sub(net, "R3 n_2V5_BIAS 0 470", f"R3 n_BIAS_DIV 0 470\nCDIV n_BIAS_DIV 0 100n\nXBUF n_BIAS_DIV n_BUF_FB n_BUF_O opamp_TLV316IDBVR\nRISO n_BUF_O n_2V5_BIAS {riso}\nRFB n_2V5_BIAS n_BUF_FB 1k")
    return re.sub(r"VREF1 (\S+) 0 DC \S+", rf"VREF1 \1 0 DC {1.65*690/470:.6f}", net)


def buffered_bias(net):
    """REF1 divider unloaded, TLV316-class follower drives +2V5_BIAS; C48 moved to the divider."""
    net = sub(net, "R110 n_2V5_BIAS n_Net__REF1_VOUT 220", "R110 n_BIAS_DIV n_Net__REF1_VOUT 220")
    net = sub(net, "R3 n_2V5_BIAS 0 470", "R3 n_BIAS_DIV 0 470")
    net = sub(net, "C48 n_2V5_BIAS 0 1e-07", "C48 n_BIAS_DIV 0 1e-07\nXBUF n_BIAS_DIV n_2V5_BIAS n_2V5_BIAS opamp_TLV316IDBVR")
    return re.sub(r"VREF1 (\S+) 0 DC \S+", rf"VREF1 \1 0 DC {1.65*690/470:.6f}", net)


# 1. bias coupling: AC2 -> current-channel outputs and bias node
cur = ["n_PFC_I1_MEAS", "n_DHB_I_MEAS", "n_HEATER_I_MEAS", "n_2V5_BIAS", "n_VAC_MEAS"]
base5 = body("c5")
b0 = run("bias_base", base5, "V_c5", cur)
b1 = run("bias_buf", buffered_bias(base5), "V_c5", cur)
print("## Bias coupling from AC2 (V/V) at 50 Hz")
for n in cur:
    print(f"{n}: base {at(b0[n], 50)[1]:.3e}  buffered {at(b1[n], 50)[1]:.3e}")

# 2. VAC_MEAS filter
def vac_fix(net, cf, cout, rout):
    net = sub(net, "R80 n_2V5_BIAS n_Net__U8 15000", f"R80 n_2V5_BIAS n_Net__U8 15000\nCF80 n_2V5_BIAS n_Net__U8 {cf}")
    net = sub(net, "R49 n_Net__R49_Pad1 n_Net__U8_1 15000", f"R49 n_Net__R49_Pad1 n_Net__U8_1 15000\nCF49 n_Net__R49_Pad1 n_Net__U8_1 {cf}")
    net = sub(net, "R65 n_VAC_MEAS n_Net__R49_Pad1 100", f"R65 n_VAC_MEAS n_Net__R49_Pad1 {rout}\nCOUT n_VAC_MEAS 0 {cout}")
    return net
v = [("as built", run("vac_base", base5, "V_c5", ["n_VAC_MEAS"])),
     ("Cf 1n across R80+R49", run("vac_cf", vac_fix(base5, "1n", "1p", 100), "V_c5", ["n_VAC_MEAS"])),
     ("Cf 1n + R65 1k / 1n out", run("vac_cf_rc", vac_fix(base5, "1n", "1n", 1000), "V_c5", ["n_VAC_MEAS"])),
     ("+ buffered bias, C48 at buffer input", run("vac_all", vac_fix(buffered_bias(base5), "1n", "1n", 1000), "V_c5", ["n_VAC_MEAS"])),
     ("+ buffered bias, 22R + C48 at output", run("vac_all_iso", vac_fix(buffered_bias_iso(base5), "1n", "1n", 1000), "V_c5", ["n_VAC_MEAS"]))]
b2 = run("bias_buf_iso", buffered_bias_iso(base5), "V_c5", cur)
print("## Bias coupling, buffer + 22R + C48 at output (V/V)")
for n in cur:
    print(f"{n}: 50 Hz {at(b2[n], 50)[1]:.3e}  1 MHz {at(b2[n], 1e6)[1]:.3e}  (base 1 MHz {at(b0[n], 1e6)[1]:.3e})")
table("VAC_MEAS", v, "n_VAC_MEAS")
for name, r in v:
    print(f"{name}: phase at 50 Hz {at(r['n_VAC_MEAS'], 50)[2]:.2f} deg")

# 3. DC_LINK_MEAS
base6 = body("c6")
def dcl_fix(net, cf):
    net = sub(net, "R17 n_Net__U6 0 15000", f"R17 n_Net__U6 0 15000\nCF17 n_Net__U6 0 {cf}")
    return sub(net, "R82 n_Net__U6_1 n_Net__R2_Pad2 15000", f"R82 n_Net__U6_1 n_Net__R2_Pad2 15000\nCF82 n_Net__U6_1 n_Net__R2_Pad2 {cf}")
d = [("as built", run("dcl_base", base6, "V_c6", ["n_DC_LINK_MEAS"])),
     ("Cf 1n across R17+R82", run("dcl_cf", dcl_fix(base6, "1n"), "V_c6", ["n_DC_LINK_MEAS"]))]
table("DC_LINK_MEAS", d, "n_DC_LINK_MEAS")

# 4. AD2 balance
base8 = body("c8")
a = [("as built", run("ad2_base", base8, "V_c8", ["n_Net__AD2_Vin"])),
     ("C 1n2 across R113", run("ad2_bal", sub(base8, "R113 n_CUK_CAP_MEAS n_Net__R113_Pad2 15000",
        "R113 n_CUK_CAP_MEAS n_Net__R113_Pad2 15000\nCF113 n_CUK_CAP_MEAS n_Net__R113_Pad2 1.2n"), "V_c8", ["n_Net__AD2_Vin"]))]
table("AD2 Vin", a, "n_Net__AD2_Vin")
