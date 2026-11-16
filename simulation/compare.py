#!/usr/bin/env python3
"""VHDL (hVHDL_ode) frequency response vs the ngspice .ac reference (PLAN.md step 4).

For each circuit: the Welch H1 estimate (hVHDL_ode python/freq_response.py) of every band's
meas.dat, used from the band's f_lo to f_hi where the coherence is > 0.95, stitched, and
compared with the ngspice response. The testbench drives a first-order-hold input and
samples y at the sample instants, so the estimate is the discrete response
    H_d(f) = sum_k H(f + k fs) sinc^2((f + k fs) / fs)
which is what the reference is turned into before the comparison (H beyond the .ac range,
> 50 MHz, taken as 0; at most k = +-3; the k = 0 term alone is within 0.07 dB at fs / 20).

Checks (circuits.LIMITS): RMS dB / deg error, DC gain VHDL vs ngspice, -3 dB frequency VHDL
vs ngspice, bias node vs 1.65 V. Reported, not part of pass/fail: the ngspice DC gain vs the
ideal transfer of the schematic values (a design property, not a simulation error).

Writes out/report.md, out/<id>_bode.png, out/<id>_vhdl.csv (test_plot.py format).

    python3 simulation/compare.py <vunit output path>        (run_sim.py calls compare())
    python3 simulation/compare.py --analytic-selftest         (no VHDL / ngspice needed)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SIM = Path(__file__).resolve().parent
sys.path.insert(0, str(SIM))
sys.path.insert(0, str(SIM / "hVHDL_ode/python"))
import circuits as C  # noqa: E402
from freq_response import freq_response  # noqa: E402

OUT = SIM / "out"
SPICE = OUT / "spice"
K_ALIAS = 3
BLUE, ORANGE = "#2a78d6", "#eb6834"       # categorical slots 1 / 2 (dataviz palette)


# ------------------------------------------------------------------ reading
def read_dat(path):
    config = {}
    with open(path) as fh:
        for line in fh:
            if line.startswith("#CONFIG"):
                key, _, value = line[len("#CONFIG"):].strip().partition("=")
                config[key] = value
            elif not line.startswith("#"):
                break
    data = pd.read_csv(path, comment="#", sep=r"\s+")
    return config, data


def read_spice(cid):
    df = pd.read_csv(SPICE / f"{cid}_spice.csv", comment="#")
    f = df["frequency"].to_numpy()
    h = 10 ** (df["magnitude_db"].to_numpy() / 20) * np.exp(1j * np.deg2rad(df["phase_deg"].to_numpy()))
    op = json.loads((SPICE / f"{cid}_op.json").read_text())
    return f, h, op


# ------------------------------------------------------------------ reference handling
class Response:
    """Interpolated H(f) from tabulated (f, H): log f vs dB / unwrapped phase.
    Below the first point: the first value; above the last: 0 (or the last, hold=True)."""

    def __init__(self, f, h, hold_above=False):
        self.lf = np.log10(f)
        self.db = 20 * np.log10(np.abs(h))
        self.ph = np.unwrap(np.angle(h))
        self.hold_above = hold_above

    def __call__(self, f):
        f = np.asarray(f, dtype=float)
        neg = f < 0
        lf = np.log10(np.maximum(np.abs(f), 10 ** self.lf[0]))
        db = np.interp(lf, self.lf, self.db)
        ph = np.interp(lf, self.lf, self.ph)
        h = 10 ** (db / 20) * np.exp(1j * ph)
        if not self.hold_above:
            h = np.where(lf > self.lf[-1] + 1e-12, 0.0, h)
        return np.where(neg, np.conj(h), h)


def discrete_reference(resp, f, fs, k_max=K_ALIAS):
    """H_d(f) = sum_k H(f + k fs) sinc^2((f + k fs)/fs) of a first-order-hold input."""
    hd = np.zeros(len(f), dtype=complex)
    for k in range(-k_max, k_max + 1):
        fk = f + k * fs
        hd += resp(fk) * np.sinc(fk / fs) ** 2
    return hd


def f_3db(f, h, h_dc):
    """First frequency where |H| falls below |H_dc| / sqrt(2) (log interpolation); None."""
    level = 20 * np.log10(abs(h_dc)) - 20 * np.log10(np.sqrt(2))
    db = 20 * np.log10(np.abs(h))
    below = np.nonzero(db < level)[0]
    if len(below) == 0:
        return None
    i = below[0]
    if i == 0:
        return float(f[0])
    x0, x1 = np.log10(f[i - 1]), np.log10(f[i])
    return float(10 ** (x0 + (level - db[i - 1]) * (x1 - x0) / (db[i] - db[i - 1])))


def rms_errors(h, href):
    r = h / href
    return (float(np.sqrt(np.mean((20 * np.log10(np.abs(r))) ** 2))),
            float(np.sqrt(np.mean(np.angle(r, deg=True) ** 2))))


# ------------------------------------------------------------------ one circuit
def vhdl_bands(dats):
    """[(band index, config, f, H, coherence)] for the band .dat files of one circuit."""
    out = []
    for dat in dats:
        cfg, data = read_dat(dat)
        b = int(cfg["band"])
        band = C.BANDS[b]
        fs, nper = band["fs"], band["nperseg"]
        f, h, coh = freq_response(data["B_u0"], data["B_y0"], fs=fs, nperseg=nper,
                                  window="hann", deskew=0.0)
        out.append((b, cfg, f, h, coh))
    return sorted(out, key=lambda x: x[0])


def check_circuit(cid, bands, spice=None):
    """bands: output of vhdl_bands(); spice: (f, H, op) or None (read out/spice)."""
    c = C.BY_ID[cid]
    lim = C.LIMITS
    f_sp, h_sp, op = spice or read_spice(cid)
    resp = Response(f_sp, h_sp)
    rows, sel_f, sel_h, sel_ref, sel_hc, cfg0 = [], [], [], [], [], None
    for b, cfg, f, h, coh in bands:
        cfg0 = cfg0 or cfg
        band = C.BANDS[b]
        top = band["f_hi"] if b > 0 else band["f_hi"] * (1 + 1e-9)
        m = (f >= band["f_lo"]) & (f < top) & (coh > lim["coherence"])
        href = discrete_reference(resp, f[m], band["fs"])
        e_db, e_deg = rms_errors(h[m], href) if m.any() else (np.nan, np.nan)
        rows.append(dict(band=b, fs=band["fs"], bins=int(m.sum()),
                         bins_total=int(((f >= band["f_lo"]) & (f < top)).sum()),
                         e_db=e_db, e_deg=e_deg))
        sel_f.append(f[m])
        sel_h.append(h[m])
        sel_ref.append(href)
        # the k = 0 hold factor removed: the -3 dB frequency, plots and the saved response
        sel_hc.append(h[m] / np.sinc(f[m] / band["fs"]) ** 2)
    f_v, h_v, h_r, h_c = (np.concatenate(x) for x in (sel_f, sel_h, sel_ref, sel_hc))
    order = np.argsort(f_v)
    f_v, h_v, h_r, h_c = f_v[order], h_v[order], h_r[order], h_c[order]
    e_db, e_deg = rms_errors(h_v, h_r)

    dc_vhdl = (float(cfg0["dc_y1"]) - float(cfg0["dc_y0"])) / float(cfg0["dc_du"])
    dc_sp, dc_ideal = op["dc_gain"], op["expected_dc_gain"]
    f3_sp = f_3db(f_sp, h_sp, dc_sp)
    f3_v = f_3db(f_v, h_c, dc_vhdl)
    f_lo, f_hi = float(f_v[0]), float(f_v[-1])
    if f3_sp is None and f3_v is None:
        f3_ok = True
    elif f3_sp is None or f3_v is None:
        # a crossing just past the compared band on one side only
        f3_ok = False
    else:
        f3_ok = abs(f3_v / f3_sp - 1) <= lim["f3db_rel"]
    res = dict(id=cid, title=c["title"], group=c["group"], unit=c["input"]["unit"],
               dc_ideal=dc_ideal, dc_spice=dc_sp, dc_vhdl=dc_vhdl,
               dc_rel=dc_vhdl / dc_sp - 1, spice_vs_ideal=dc_sp / dc_ideal - 1,
               f3_spice=f3_sp, f3_vhdl=f3_v, e_db=e_db, e_deg=e_deg, bands=rows,
               f_lo=f_lo, f_hi=f_hi, bins=len(f_v),
               bias_spice=op.get("bias_op"), out_op=op["out_op"],
               bias_vhdl=float(cfg0["dc_bias"]) if c["ref"] == "bias" else None)
    checks = dict(rms=e_db <= lim["rms_db"] and e_deg <= lim["rms_deg"],
                  dc=abs(res["dc_rel"]) <= lim["dc_gain_rel"], f3=f3_ok)
    if c["ref"] == "bias":
        checks["bias"] = (abs(res["bias_spice"] / C.BIAS_VOLTAGE - 1) <= lim["bias_rel"]
                          and abs(res["bias_vhdl"] / C.BIAS_VOLTAGE - 1) <= lim["bias_rel"])
    res["checks"] = checks
    res["passed"] = all(checks.values())
    res["_plot"] = (f_sp, h_sp, f_v, h_c, h_r * h_c / h_v)
    return res


# ------------------------------------------------------------------ output
def save_vhdl_response(res):
    f_sp, h_sp, f_v, h_v, h_r = res["_plot"]
    with open(OUT / f"{res['id']}_vhdl.csv", "w") as fo:
        fo.write("#FREQRESPONSE\n")
        fo.write(f"#CONFIG label={res['id']} hVHDL_ode (Welch H1, stitched bands)\n")
        fo.write("frequency,magnitude_db,phase_deg\n")
        ph = np.rad2deg(np.unwrap(np.angle(h_v)))
        for f, m, p in zip(f_v, 20 * np.log10(np.abs(h_v)), ph):
            fo.write(f"{f:.10g},{m:.10g},{p:.10g}\n")


def plot(res, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    f_sp, h_sp, f_v, h_v, h_r = res["_plot"]
    fig, ax = plt.subplots(4, 1, sharex=True, figsize=(9, 9),
                           gridspec_kw=dict(height_ratios=[3, 3, 1.4, 1.4]))
    ax[0].semilogx(f_sp, 20 * np.log10(np.abs(h_sp)), color=BLUE, lw=2, label="ngspice .ac")
    ax[0].semilogx(f_v, 20 * np.log10(np.abs(h_v)), "o", color=ORANGE, ms=2.5, mew=0,
                   label="hVHDL_ode, Welch H1")
    ph_sp = np.rad2deg(np.unwrap(np.angle(h_sp)))
    ph_v = np.angle(h_v / Response(f_sp, h_sp)(f_v), deg=True) + np.interp(
        np.log10(f_v), np.log10(f_sp), ph_sp)
    ax[1].semilogx(f_sp, ph_sp, color=BLUE, lw=2)
    ax[1].semilogx(f_v, ph_v, "o", color=ORANGE, ms=2.5, mew=0)
    r = h_v / h_r
    ax[2].semilogx(f_v, 20 * np.log10(np.abs(r)), "o", color=ORANGE, ms=2.5, mew=0)
    ax[3].semilogx(f_v, np.angle(r, deg=True), "o", color=ORANGE, ms=2.5, mew=0)
    unit = "V/A" if res["unit"] == "A" else "V/V"
    ax[0].set_ylabel(f"|H| [dB {unit}]")
    ax[1].set_ylabel("phase [deg]")
    ax[2].set_ylabel("error [dB]")
    ax[3].set_ylabel("error [deg]")
    ax[3].set_xlabel("frequency [Hz]")
    ax[2].set_ylim(-1, 1)
    ax[3].set_ylim(-10, 10)
    for b in C.BANDS[1:]:
        for a in ax:
            a.axvline(b["f_hi"], color="#c3c2b7", lw=0.8)
    for a in ax:
        a.grid(True, which="both", color="#e4e3df", lw=0.6)
        a.spines[["top", "right"]].set_visible(False)
    ax[0].set_title(f"{res['id']}: {res['title']}  -  {'pass' if res['passed'] else 'FAIL'}, "
                    f"{res['e_db']:.3f} dB / {res['e_deg']:.2f} deg RMS", fontsize=10)
    ax[0].legend(frameon=False, fontsize=9)
    ax[0].set_xlim(0.8, 6e7)
    fig.tight_layout()
    fig.savefig(path, dpi=80)
    plt.close(fig)


def fmt_f(f):
    if f is None:
        return "none"
    for s, d in (("MHz", 1e6), ("kHz", 1e3)):
        if f >= d:
            return f"{f / d:.4g} {s}"
    return f"{f:.4g} Hz"


def report(results, path):
    lim = C.LIMITS
    lines = ["# Measurement-circuit simulations: hVHDL_ode vs ngspice", "",
             "Generated by `simulation/run_sim.py` (compare.py). Limits: RMS error "
             f"<= {lim['rms_db']} dB / {lim['rms_deg']} deg where coherence > {lim['coherence']}, "
             f"DC gain <= {100 * lim['dc_gain_rel']:.1f} %, -3 dB frequency <= {100 * lim['f3db_rel']:.0f} %, "
             f"bias node {C.BIAS_VOLTAGE} V <= {100 * lim['bias_rel']:.1f} % (both simulators).", "",
             "| circuit | DC gain ideal | ngspice | VHDL | VHDL vs ngspice | ngspice vs ideal | "
             "-3 dB ngspice | -3 dB VHDL | RMS dB | RMS deg | compared band (bins) | result |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        u = "V/A" if r["unit"] == "A" else ""
        lines.append(
            f"| {r['id']} {r['title']} | {r['dc_ideal']:.6g} {u} | {r['dc_spice']:.6g} | "
            f"{r['dc_vhdl']:.6g} | {100 * r['dc_rel']:+.3f} % | {100 * r['spice_vs_ideal']:+.3f} % | "
            f"{fmt_f(r['f3_spice'])} | {fmt_f(r['f3_vhdl'])} | {r['e_db']:.3f} | {r['e_deg']:.2f} | "
            f"{fmt_f(r['f_lo'])} - {fmt_f(r['f_hi'])} ({r['bins']}) | "
            f"{'pass' if r['passed'] else 'FAIL ' + ','.join(k for k, v in r['checks'].items() if not v)} |")
    lines += ["", "Per band (RMS dB / deg, bins with coherence > limit / bins in band):", ""]
    lines.append("| circuit | " + " | ".join(
        f"band {i}: fs {fmt_f(b['fs']).replace('Hz', 'S/s')}, {fmt_f(b['f_lo'])} - {fmt_f(b['f_hi'])}"
        for i, b in enumerate(C.BANDS)) + " |")
    lines.append("|---" * (len(C.BANDS) + 1) + "|")
    for r in results:
        cells = [f"{b['e_db']:.3f} / {b['e_deg']:.2f} ({b['bins']}/{b['bins_total']})" for b in r["bands"]]
        lines.append(f"| {r['id']} | " + " | ".join(cells) + " |")
    bias = [r for r in results if r["bias_spice"] is not None]
    if bias:
        lines += ["", "Bias node (+1V65_BIAS): " + ", ".join(
            f"{r['id']} ngspice {r['bias_spice']:.4f} V / VHDL {r['bias_vhdl']:.4f} V" for r in bias) + "."]
    lines += ["", "Operating points (ngspice, output at the input DC level): " + ", ".join(
        f"{r['id']} {r['out_op']:.3f} V" for r in results) + ".", "",
        "Bode plots: `out/<id>_bode.png`.", ""]
    Path(path).write_text("\n".join(lines))


def compare(vunit_out, ids=None):
    """Find the meas.dat of every circuit/band under the VUnit output path (or a list of
    test output paths), check, report."""
    dats = {}
    roots = [vunit_out] if isinstance(vunit_out, (str, Path)) else vunit_out
    for dat in (d for root in roots for d in Path(root).rglob("meas.dat")):
        cfg, _ = read_dat_config(dat)
        dats.setdefault(cfg["circuit"], []).append(dat)
    results, passed = [], True
    for c in C.CIRCUITS:
        if (ids and c["id"] not in ids) or c["id"] not in dats:
            continue
        res = check_circuit(c["id"], vhdl_bands(dats[c["id"]]))
        save_vhdl_response(res)
        plot(res, OUT / f"{c['id']}_bode.png")
        results.append(res)
        passed &= res["passed"]
        print(f"{c['id']}: {'pass' if res['passed'] else 'FAIL'}  DC {res['dc_vhdl']:.6g} vs "
              f"{res['dc_spice']:.6g} ({100 * res['dc_rel']:+.3f} %), -3 dB {fmt_f(res['f3_vhdl'])} vs "
              f"{fmt_f(res['f3_spice'])}, {res['e_db']:.3f} dB / {res['e_deg']:.2f} deg RMS "
              f"({fmt_f(res['f_lo'])} - {fmt_f(res['f_hi'])}, {res['bins']} bins)")
    if results:
        report(results, OUT / "report.md")
        print(f"report: {OUT / 'report.md'}")
    return passed and bool(results), results


def read_dat_config(path):
    config = {}
    with open(path) as fh:
        for line in fh:
            if not line.startswith("#CONFIG"):
                break
            key, _, value = line[len("#CONFIG"):].strip().partition("=")
            config[key] = value
    return config, None


# ------------------------------------------------------------------ self-test
def analytic_selftest():
    """compare.py against an analytic H(s) of circuit 7 (R11 / R12 || C61 from the schematic):
    a first-order-hold simulation of the exact discretisation (scipy) must pass, an 8 %
    pole shift must fail the -3 dB check, a 1 dB gain error the RMS check."""
    from scipy import signal
    sys.path.insert(0, str(SIM / "spice"))
    import extract as X
    nl = X.Netlist()
    c = C.BY_ID["c7"]
    p = X.circuit_params(nl, c)
    r1, r2, c1 = p["in_p"][0], p["ref_p"], p["c_ref_p"]
    k, wp = r2 / (r1 + r2), (r1 + r2) / (r1 * r2 * c1)
    f_sp = np.logspace(np.log10(C.AC_START), np.log10(C.AC_STOP), 50 * 8 + 1)
    op = dict(dc_gain=k, expected_dc_gain=X.expected_dc_gain(nl, c), out_op=20 * k, bias_op=None)

    def h_of(kk, w):
        return lambda f: kk / (1 + 2j * np.pi * f / w)

    def bands_for(kk, w):
        out = []
        rng = np.random.default_rng(1)
        for b, band in enumerate(C.BANDS):
            fs, n = band["fs"], band["nperseg"] * band["windows"]
            u = rng.uniform(-1, 1, n)
            sysd = signal.cont2discrete(([kk * w], [1, w]), 1 / fs, method="foh")
            y = signal.lfilter(sysd[0].ravel(), sysd[1], u)
            f, h, coh = freq_response(u, y, fs=fs, nperseg=band["nperseg"], window="hann")
            out.append((b, dict(band=str(b), dc_y0="0", dc_y1=str(kk), dc_du="1", dc_bias="0"), f, h, coh))
        return out

    ok = True
    h_ref = h_of(k, wp)(f_sp)
    for name, kk, w, expect in (("exact", k, wp, True), ("pole -8 %", k, wp * 0.92, False),
                                ("gain +1 dB", k * 10 ** (1 / 20), wp, False)):
        res = check_circuit("c7", bands_for(kk, w), spice=(f_sp, h_ref, op))
        good = res["passed"] == expect
        ok &= good
        print(f"  {name:11} -> {'pass' if res['passed'] else 'FAIL'} ({res['checks']}), "
              f"{res['e_db']:.4f} dB / {res['e_deg']:.3f} deg, -3 dB {fmt_f(res['f3_vhdl'])} vs "
              f"{fmt_f(res['f3_spice'])}: {'as expected' if good else 'UNEXPECTED'}")
    print("compare.py analytic self-test", "OK" if ok else "FAILED")
    return ok


if __name__ == "__main__":
    if "--analytic-selftest" in sys.argv:
        sys.exit(0 if analytic_selftest() else 1)
    ok, _ = compare(sys.argv[1] if len(sys.argv) > 1 else OUT / "vunit_out")
    sys.exit(0 if ok else 1)
