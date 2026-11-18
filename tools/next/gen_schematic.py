#!/usr/bin/env python3
"""Write the tube_power 5.2 schematic into kicad_next/ (project tube_psu_5_2) from the forked sheet scripts.

    python3 tools/next/gen_schematic.py           regenerate kicad_next/*.kicad_sch (+ lib tables)
    python3 tools/next/gen_schematic.py --check   regenerate into a temporary directory and fail unless
                                                  it equals the committed kicad_next/*.kicad_sch
    python3 tools/next/gen_schematic.py --diff51  report whether kicad_next/ still equals the 5.1
                                                  schematic in kicad/ (after the project / library
                                                  renames) - true right after the fork (phase 1)

Steps: the root sheet tube_psu_5_2.kicad_sch is derived from the 5.1 root kicad/tube_psu.kicad_sch
(project name replaced, ROOT_EDITS applied); a sub-sheet that does not exist yet in kicad_next/ is
bootstrapped from kicad/ (only its header / title block survives: every script clears and redraws it);
then tools/next/sheets/sheetNN.py draw the sheets (symbols from lib/tube_psu_next.kicad_sym, values /
footprints / LCSC from lib/*_next.csv). The 5.1 scripts in tools/sheets/ and kicad/ are not touched.
"""
import filecmp
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHEETS_DIR = os.path.join(ROOT, "tools", "next", "sheets")
OUT = os.path.join(ROOT, "kicad_next")
SRC51 = os.path.join(ROOT, "kicad")
PROJECT = "tube_psu_5_2"
SUBSHEETS = ["01_aux_supply", "02_dhb_gate_drive", "03_isolated_measurements", "04_mcu_connector", "05_pfc",
             "06_heaters", "07_dhb", "08_current_measurement", "09_ac_measurement",
             "10_pfc_current_measurement", "11_startup"]
# Text replacements on the 5.1 root sheet (old, new). Phase 2: title block rev, notes, new sheets.
ROOT_EDITS = [('(project "tube_psu"', f'(project "{PROJECT}"')]

SYM_LIB_TABLE = """(sym_lib_table
\t(version 7)
\t(lib (name "tube_psu_next")(type "KiCad")(uri "${KIPRJMOD}/../lib/tube_psu_next.kicad_sym")(options "")(descr "5.2 project symbols (tools/next/gen_symbols.py), used by the 5.2 sheets"))
\t(lib (name "tube_psu")(type "KiCad")(uri "${KIPRJMOD}/../lib/tube_psu.kicad_sym")(options "")(descr "5.1 migration symbols (frozen, reference only)"))
)
"""
FP_LIB_TABLE = """(fp_lib_table
\t(version 7)
\t(lib (name "tube_psu")(type "KiCad")(uri "${KIPRJMOD}/../lib/tube_psu.pretty")(options "")(descr "5.1 project footprints, pad numbers = IPC pin ids (tools/gen_footprints.py)"))
\t(lib (name "tube_psu_next")(type "KiCad")(uri "${KIPRJMOD}/../lib/tube_psu_next.pretty")(options "")(descr "5.2 footprints (tools/next/gen_next_footprints.py)"))
\t(lib (name "tube_psu_next_parts")(type "KiCad")(uri "${KIPRJMOD}/../lib/tube_psu_next_parts.pretty")(options "")(descr "5.2 part footprints not in the KiCad library (tools/next/gen_next_footprints_parts.py)"))
)
"""


def write_root(out):
    with open(os.path.join(SRC51, "tube_psu.kicad_sch")) as f:
        s = f.read()
    for old, new in ROOT_EDITS:
        s = s.replace(old, new)
    with open(os.path.join(out, f"{PROJECT}.kicad_sch"), "w") as f:
        f.write(s)


def generate(out):
    os.makedirs(out, exist_ok=True)
    write_root(out)
    for name in SUBSHEETS:
        dst = os.path.join(out, name + ".kicad_sch")
        if not os.path.exists(dst):
            shutil.copy(os.path.join(SRC51, name + ".kicad_sch"), dst)
    env = dict(os.environ, TUBE_PSU_NEXT_OUT=out)
    for name in sorted(f for f in os.listdir(SHEETS_DIR) if f.startswith("sheet") and f.endswith(".py")):
        r = subprocess.run([sys.executable, os.path.join(SHEETS_DIR, name)], cwd=ROOT, env=env,
                           capture_output=True, text=True)
        if r.returncode:
            sys.stderr.write(r.stdout + r.stderr)
            raise SystemExit(f"gen_schematic: {name} failed")


def files(d):
    return sorted(f for f in os.listdir(d) if f.endswith(".kicad_sch"))


def main(argv):
    if "--check" in argv:
        with tempfile.TemporaryDirectory() as tmp:
            for f in files(OUT):
                shutil.copy(os.path.join(OUT, f), tmp)   # headers / title blocks of the sub-sheets
            generate(tmp)
            bad = [f for f in files(tmp) if not os.path.exists(os.path.join(OUT, f))
                   or not filecmp.cmp(os.path.join(tmp, f), os.path.join(OUT, f), shallow=False)]
        if bad:
            print("gen_schematic: kicad_next/ is out of date (run tools/next/gen_schematic.py):", ", ".join(bad))
            return 1
        print(f"gen_schematic: kicad_next/ up to date ({len(files(OUT))} sheets)")
        return 0
    if "--diff51" in argv:
        diff = []
        for name in ["tube_psu"] + SUBSHEETS:
            with open(os.path.join(SRC51, name + ".kicad_sch")) as f:
                a = f.read()
            with open(os.path.join(OUT, (PROJECT if name == "tube_psu" else name) + ".kicad_sch")) as f:
                b = f.read().replace(f'(project "{PROJECT}"', '(project "tube_psu"').replace('"tube_psu_next:', '"tube_psu:')
            if a != b:
                diff.append(name)
        print("gen_schematic: kicad_next/ = 5.1 schematic apart from the project / library names" if not diff
              else "gen_schematic: differs from 5.1: " + ", ".join(diff))
        return 0
    generate(OUT)
    for name, text in (("sym-lib-table", SYM_LIB_TABLE), ("fp-lib-table", FP_LIB_TABLE)):
        with open(os.path.join(OUT, name), "w") as f:
            f.write(text)
    print(f"gen_schematic: wrote kicad_next/ ({len(files(OUT))} sheets)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
