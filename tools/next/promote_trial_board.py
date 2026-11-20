#!/usr/bin/env python3
"""Promote the latest trial board to the real 5.2 board (run with tools/p2k/bin/kipy).

    tools/p2k/bin/kipy tools/next/promote_trial_board.py           refuses if the real board already has footprints
    tools/p2k/bin/kipy tools/next/promote_trial_board.py --force   overwrite it (loses edits made in KiCad!)

Input:  kicad_next/trial_from_51/tube_psu_5_2_trial_p3.kicad_pcb (placement step 3, zones refilled by its DRC)
Output: kicad_next/tube_psu_5_2.kicad_pcb - from here on the board is edited (routing, phase 5/6) and only checked.

What changes against the trial file (everything else is copied as is: placement, slots, keep-outs, copper):
  * 3D model paths: the trial project sits one directory deeper; any ${KIPRJMOD}/../../lib/ path written by
    reuse_51_board.set_fields goes back to ${KIPRJMOD}/../lib/ (the p3 board of 2026-11-20 had none left)
  * footprint fields from the 5.2 schematic (kicad-cli netlist): Description, and LCSC also where it is empty,
    so that the DRC schematic parity (check_board.py) is clean, as after "Update PCB from Schematic"
Value, symbol path, sheet name / file and pad nets were already set by reuse_51_board.py from the same netlist.
"""
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import pcbnew

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "kicad_next", "trial_from_51", "tube_psu_5_2_trial_p3.kicad_pcb")
OUT = os.path.join(ROOT, "kicad_next", "tube_psu_5_2.kicad_pcb")
SCH = os.path.join(ROOT, "kicad_next", "tube_psu_5_2.kicad_sch")
CLI = os.path.join(ROOT, "tools", "p2k", "bin", "kicad-cli")


def netlist_fields():
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "n.xml")
        subprocess.run([CLI, "sch", "export", "netlist", "--format", "kicadxml", "-o", out, SCH],
                       check=True, capture_output=True)
        t = ET.parse(out)
    comps = {}
    for c in t.find("components"):
        f = {e.get("name"): (e.text or "") for e in c.find("fields")}
        comps[c.get("ref")] = {"Description": c.findtext("description") or "", "LCSC": f.get("LCSC")}
    return comps


def main():
    old = pcbnew.LoadBoard(OUT)
    if len(old.GetFootprints()) > 8 and "--force" not in sys.argv:     # the skeleton has only H1-H8
        sys.exit(f"promote_trial_board: {os.path.relpath(OUT, ROOT)} already has {len(old.GetFootprints())} "
                 "footprints (use --force to overwrite)")
    comps = netlist_fields()
    b = pcbnew.LoadBoard(SRC)
    models = fields = 0
    for fp in b.GetFootprints():
        for m in fp.Models():
            if "${KIPRJMOD}/../../lib/" in m.m_Filename:
                m.m_Filename = m.m_Filename.replace("${KIPRJMOD}/../../lib/", "${KIPRJMOD}/../lib/")
                models += 1
        c = comps.get(fp.GetReference())
        if c is None:
            continue
        for name in ("Description", "LCSC"):
            want = c[name]
            if want is None:
                continue
            if not fp.HasField(name) or fp.GetFieldText(name) != want:
                fp.SetField(name, want)
                fields += 1
    missing = sorted(set(comps) - {fp.GetReference() for fp in b.GetFootprints()})
    if missing:
        sys.exit(f"promote_trial_board: schematic parts not on the trial board: {missing}")
    b.Save(OUT)
    print(f"promote_trial_board: {os.path.relpath(SRC, ROOT)} -> {os.path.relpath(OUT, ROOT)}: "
          f"{len(b.GetFootprints())} footprints, {models} 3D model paths fixed, {fields} fields set")
    return 0


if __name__ == "__main__":
    sys.exit(main())
