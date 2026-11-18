#!/usr/bin/env python3
"""TI vendor op-amp models (PLAN.md step 5): download, run in ngspice, characterise.

The models are not committed (TI copyright): `fetch()` downloads the zip from ti.com/lit/zip
into simulation/out/vendor/<part>/ (each in its own directory, treated as data: the .lib is only
.include'd by absolute path, ngspice never runs with that directory as cwd) and returns the
path of the .lib. ngspice runs them with `-D ngbehavior=psa` (PSpice compatibility).

    python3 simulation/spice/vendor_models.py          # fetch + characterise all, prints a table

Characterisation at +3.3 V / 0 V supply, inputs at 1.65 V: open-loop gain and phase (loop closed
at DC through 1 GH, opened at AC by 1 F), unity-gain frequency and phase margin as a follower,
open-loop output impedance Zo(f) (same DC loop, 1 A AC into OUT, no load), slew rate of a
follower (0.5 -> 2.8 V step, 10 k load). The results feed the two-pole macromodels of
circuits.OPAMPS_2P (used for the bias-buffer stability check, bias_buffer.py).
"""
import io
import math
import re
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIM = HERE.parent
VENDOR = SIM / "out" / "vendor"
WORK = SIM / "out" / "vendor_runs"

# part -> (zip id at ti.com/lit/zip, library file inside the zip, subckt, pin order)
# pin order: names of the subckt pins in the order (inp, inn, vcc, vee, out)
MODELS = {
    "TLV316": ("sbom975d", "tlv316.lib", "TLV316", ("inp", "inn", "vcc", "vee", "out")),
    "TLV9062": ("SBOMAG1", "tlv9062.lib", "TLV9062", ("inp", "inn", "vcc", "vee", "out")),
    # National 2005 transistor-level model, pin order -IN +IN VCC VEE OUT
    "LMH6643": ("snom136", "LMH6643.MOD", "LMH6643", ("inn", "inp", "vcc", "vee", "out")),
}


def fetch(part):
    zid, lib, _, _ = MODELS[part]
    d = VENDOR / part
    path = d / lib
    if path.exists():
        return path
    d.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(f"https://www.ti.com/lit/zip/{zid}", headers={"User-Agent": "Mozilla/5.0"})
    data = urllib.request.urlopen(req, timeout=60).read()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = [n for n in z.namelist() if Path(n).name.lower() == lib.lower()]
        if not names:
            raise SystemExit(f"{part}: {lib} not in {zid}.zip ({z.namelist()})")
        path.write_bytes(z.read(names[0]))
    return path


def instance(part, name, inp, inn, vcc, vee, out):
    """Subcircuit call line with the vendor pin order."""
    _, _, sub, order = MODELS[part]
    m = dict(inp=inp, inn=inn, vcc=vcc, vee=vee, out=out)
    return f"X{name} " + " ".join(m[p] for p in order) + f" {sub}"


def ngspice(cir_text, name):
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / f"{name}.cir").write_text(cir_text)
    r = subprocess.run(["ngspice", "-D", "ngbehavior=psa", "-b", f"{name}.cir"], cwd=WORK,
                       capture_output=True, text=True, timeout=900)
    (WORK / f"{name}.log").write_text(r.stdout + r.stderr)
    return r


def read(path):
    rows = [l.split() for l in Path(path).read_text().splitlines()[1:] if l.strip()]
    return [[float(x) for x in r] for r in rows]


def characterise(part):
    lib = fetch(part)
    inst = instance(part, "U", "inp", "inn", "vcc", "0", "out")
    head = f"* {part} characterisation\n.include {lib}\nVCC vcc 0 3.3\nVCM cm 0 1.65\n"
    # open loop gain / phase, and Zo
    cir = head + f"""{inst}
VIN inp cm DC 0 AC 1
LFB out inn 1G
CIN inn cm 1
RL out cm 10k
.control
set wr_singlescale
set wr_vecnames
ac dec 40 10 1G
wrdata {part}_aol.txt v(out) v(inn)
.endc
.end
"""
    ngspice(cir, f"{part}_aol")
    aol = [(r[0], complex(r[1], r[2]) - complex(r[3], r[4])) for r in read(WORK / f"{part}_aol.txt")]
    cir = head + f"""{inst}
VIN inp cm DC 0
LFB out inn 1G
CIN inn cm 1
IZ 0 out DC 0 AC 1
.control
set wr_singlescale
set wr_vecnames
ac dec 40 10 1G
wrdata {part}_zo.txt v(out)
.endc
.end
"""
    ngspice(cir, f"{part}_zo")
    zo = [(r[0], complex(r[1], r[2])) for r in read(WORK / f"{part}_zo.txt")]
    cir = head.replace("VCM cm 0 1.65", "") + f"""{instance(part, 'U', 'inp', 'out', 'vcc', '0', 'out')}
VIN inp 0 PULSE(0.5 2.8 1u 10n 10n 5u 20u)
RL out 0 10k
.control
set wr_singlescale
set wr_vecnames
tran 1n 4u
wrdata {part}_sr.txt v(out)
.endc
.end
"""
    ngspice(cir, f"{part}_sr")
    tr = read(WORK / f"{part}_sr.txt")
    t20 = next(t for t, v in tr if t > 1e-6 and v > 0.5 + 0.2 * 2.3)
    t80 = next(t for t, v in tr if t > 1e-6 and v > 0.5 + 0.8 * 2.3)
    sr = 0.6 * 2.3 / (t80 - t20)
    a0 = abs(aol[0][1])
    fu, ph_u = None, None
    for (f1, h1), (f2, h2) in zip(aol, aol[1:]):
        if abs(h1) >= 1 > abs(h2):
            x = math.log(abs(h1)) / (math.log(abs(h1)) - math.log(abs(h2)))
            fu = f1 * (f2 / f1) ** x
            ph_u = math.degrees(math.atan2(h2.imag, h2.real))
            break
    zo_at = {f: abs(min(zo, key=lambda r: abs(math.log(r[0] / f)))[1]) for f in (1e3, 1e5, 1e6, 1e7, 1e8)}
    return dict(part=part, a0_db=20 * math.log10(a0), gbw=fu, pm=180 + ph_u if ph_u is not None else None,
                sr=sr, zo=zo_at, aol=aol, zo_curve=zo)


def main():
    print("| part | A0 | unity-gain f | phase margin (follower, 10k) | slew | Zo 1k / 100k / 1M / 10M / 100M Hz |")
    print("|---|---|---|---|---|---|")
    for part in MODELS:
        c = characterise(part)
        z = " / ".join(f"{c['zo'][f]:.3g}" for f in (1e3, 1e5, 1e6, 1e7, 1e8))
        print(f"| {part} | {c['a0_db']:.1f} dB | {c['gbw'] / 1e6:.3g} MHz | {c['pm']:.1f} deg | "
              f"{c['sr'] / 1e6:.3g} V/us | {z} ohm |", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
