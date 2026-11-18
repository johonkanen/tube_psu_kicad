"""Waveform figure for DAB_SIMULATION.md: 400 W forward and 0 W at 150 ns dead time.

    python3 simulation/dab/dab_spice_plot.py      # ~30 s, writes simulation/dab/dab_spice_waves.png
Uses the phi solved by dab_spice.py (out/spice_results.json).
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dab_spice as ds  # noqa: E402


def main():
    R = json.load(open(os.path.join(ds.OUT, "spice_results.json")))
    tabs = ds.cap_tables(True)
    sc = [r for r in R["scan"].values() if r.get("V2") == 420.0 and abs(r["dt"] - 150e-9) < 1e-12]
    r0 = min(sc, key=lambda r: abs(r["P_out"]))
    cases = [("400 W", R["full"]["150ns_fwd"]["phi"], 400.0), (f"{r0['P_out']:.0f} W", r0["phi"], 0.0)]
    fig, ax = plt.subplots(4, 2, figsize=(12, 10), sharex="col")
    for col, (name, phi, P) in enumerate(cases):
        cfg = ds.base_cfg(phi=phi, dt=150e-9, P_est=P, esl=0.7e-9)
        d, meta = ds.run_case(cfg, tabs)
        t = d["time"]
        t = (t - t[0]) * 1e6
        ax[0, col].plot(t, d["v(swp)"] - d["v(dcur)"], label="primary node (Q7 Vds)")
        ax[0, col].plot(t, d["v(sws)"] - d["v(iso)"], label="secondary node (Q8 Vds)")
        ax[0, col].set_ylabel("V")
        ax[0, col].set_title(f"{name}, phi = {phi:.2f} deg, DT 150 ns")
        ax[0, col].legend(loc="upper right", fontsize=8)
        ax[1, col].plot(t, d["i(vi1)"], label="i1 primary")
        ax[1, col].plot(t, d["i(vi2)"], label="i2 secondary")
        ax[1, col].plot(t, d["i(vi1)"] + ds.N_RATIO * d["i(vi2)"], label="i_m (pri-referred)")
        ax[1, col].set_ylabel("A")
        ax[1, col].legend(loc="upper right", fontsize=8)
        for q, s in (("q19", "swp"), ("q7", "dcur")):
            ax[2, col].plot(t, d[f"v({q}_g)"] - d[f"v({s})"], label=f"{q.upper()} Vgs")
        for q, s in (("q21", "sws"), ("q8", "iso")):
            ax[2, col].plot(t, d[f"v({q}_g)"] - d[f"v({s})"], "--", label=f"{q.upper()} Vgs")
        ax[2, col].set_ylabel("V")
        ax[2, col].legend(loc="upper right", fontsize=7, ncol=2)
        gain = ds.R_SHUNT * 15e3 / 330
        ax[3, col].plot(t, d["i(lsh)"], label="I(R83) true")
        ax[3, col].plot(t, d["v(dcur)"] / ds.R_SHUNT, alpha=0.6, label="V(R83)/4 mOhm (with 0.7 nH)")
        ax[3, col].plot(t, (d["v(aout)"] - d["v(bias)"]) / gain, label="DHB_I amp output / 0.182 V/A")
        ax[3, col].set_ylabel("A")
        ax[3, col].set_xlabel("us")
        ax[3, col].set_ylim(-4, 6)
        ax[3, col].legend(loc="upper right", fontsize=7)
    for a_ in ax.flat:
        a_.grid(alpha=0.3)
    fig.tight_layout()
    out = os.path.join(HERE, "dab_spice_waves.png")
    fig.savefig(out, dpi=90)
    print("wrote", out)


if __name__ == "__main__":
    main()
