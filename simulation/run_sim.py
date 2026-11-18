#!/usr/bin/env python3
"""Measurement-circuit simulations: ngspice .ac references vs hVHDL_ode models (PLAN.md).

Runs separately (not from tools/check_all.sh):

    python3 simulation/run_sim.py                  # everything: 9 circuits x 4 bands
    python3 simulation/run_sim.py '*c5*'           # VUnit test pattern (one circuit)
    python3 simulation/run_sim.py --no-spice ...   # reuse out/spice (no ngspice run)
    python3 simulation/run_sim.py --compile        # compile only
    python3 simulation/run_sim.py --rev 5.2        # board 5.2 (kicad_next/): 10 circuits,
                                                   # output simulation/out/5.2/

Steps: golden check of the netlist extraction against INVENTORY.md (spice/extract.py),
regenerate vhdl/meas_params_pkg.vhd (gen_params.py), the compare.py analytic self-test,
the ngspice references (spice/run_ac.py, one ngspice at a time), then VUnit with NVC, one
simulation at a time (-p 1 is forced: memory rule), and compare.py as post_run.
Output: simulation/out/ (report.md, <id>_bode.png; vunit_out/ holds the .dat files).
"""
import os
import sys
from pathlib import Path

SIM = Path(__file__).resolve().parent
sys.path.insert(0, str(SIM))
sys.path.insert(0, str(SIM / "spice"))
ODE = SIM / "hVHDL_ode"

argv = sys.argv[1:]
if "--rev" in argv:
    i = argv.index("--rev")
    os.environ["MEAS_SIM_REV"] = argv[i + 1]
    argv = argv[:i] + argv[i + 2:]
no_spice = "--no-spice" in argv
argv = [a for a in argv if a != "--no-spice"]
# memory rule: never several simulations at once
clean = []
skip = False
for a in argv:
    if skip:
        skip = False
        continue
    if a in ("-p", "--num-threads"):
        skip = True
        continue
    if a.startswith("--num-threads=") or (a.startswith("-p") and a[2:].isdigit()):
        continue
    clean.append(a)
argv = clean + ["-p", "1"]
sys.argv = sys.argv[:1]          # circuits.py reads --rev from the environment only now
import circuits as C  # noqa: E402
if "-o" not in argv and "--output-path" not in argv:
    argv += ["--output-path", str(C.OUT / "vunit_out")]
os.environ.setdefault("VUNIT_SIMULATOR", "nvc")

if not (ODE / "ode_solvers/ode_pkg.vhd").exists():
    raise SystemExit("simulation/hVHDL_ode missing: git submodule update --init simulation/hVHDL_ode")

import compare  # noqa: E402
import extract  # noqa: E402
import gen_params  # noqa: E402

listing = any(a in ("-l", "--list", "--files", "-h", "--help") for a in argv)
if not listing:
    if extract.main(["--check"]) != 0:
        raise SystemExit("netlist extraction does not match INVENTORY.md")
    gen_params.main([])
    if not compare.analytic_selftest():
        raise SystemExit("compare.py self-test failed")
    if not no_spice and "--compile" not in argv:
        import run_ac
        run_ac.main([])

from vunit import VUnit  # noqa: E402

VU = VUnit.from_argv(argv=argv)
VU.add_vhdl_builtins()

ode = VU.add_library("ode")
for f in ("write_pkg.vhd", "ode_solvers/real_vector_pkg.vhd", "ode_solvers/linalg_pkg.vhd",
          "ode_solvers/ode_pkg.vhd"):
    ode.add_source_files(ODE / f)

meas = VU.add_library("meas")
meas.add_source_files(SIM / "vhdl/meas_models_pkg.vhd")
meas.add_source_files(SIM / "vhdl/meas_circuit_tb.vhd")
meas.add_source_files(C.PARAMS_VHD)
tb = meas.test_bench("meas_circuit_tb")
for i, c in enumerate(C.CIRCUITS, start=1):
    for b, band in enumerate(C.BANDS):
        tb.add_config(name=f"{c['id']}_{band['name']}", generics=dict(g_circuit=i, g_band=b))


def post_run(results):
    report = results.get_report()
    paths = [Path(t.path) for t in report.tests.values()]
    if not paths:
        return
    ok, _ = compare.compare(paths)
    if not ok:
        sys.exit(1)


VU.main(post_run=post_run)
