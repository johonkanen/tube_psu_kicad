#!/usr/bin/env python3
"""Stage 13b (one-shot, not re-runnable; run with tools/p2k/bin/kipy): creepage slots of ISO1 / ISO2 / U11 1.0 -> 1.5 mm.

    tools/p2k/bin/kipy tools/next/route_s13b_slots.py [--dry-run OUT.kicad_pcb]

Design review 2026-11-23 (findings 10 C6 / F2, 14 B3 / F3): the milled slots under ISO2 and U11 and the T slot at
ISO1 / TR2 were 1.0 mm wide = JLC's minimum non-plated slot, milled to +-0.2 mm; IEC 60664-1 ignores a groove
narrower than 1.0 mm at PD2. The slots are Edge.Cuts shapes of the footprints made by
tools/next/gen_next_footprints_parts.py (SOIC_SLOT_W = 1.5 since this stage; the T bar grows towards ISO1 only).
This script copies the graphic items (Edge.Cuts slot, courtyard, silk, fab) of the regenerated library footprints
into the three board footprints at their place; pads, fields, nets and copper are not touched. TR1 and the L
cut-out (1.2 mm) stay. Zones are refilled by kicad-cli. Record: kicad_next/routing/moves_s13b.json.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJ = os.path.join(ROOT, "kicad_next")
NAME = "tube_psu_5_2"
BOARD = os.path.join(PROJ, NAME + ".kicad_pcb")
CLI = os.path.join(ROOT, "tools", "p2k", "bin", "kicad-cli")
REC = os.path.join(PROJ, "routing", "moves_s13b.json")
REFS = ["ISO1", "ISO2", "U11"]


def edit(path):
    import pcbnew
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import reuse_51_board as R
    b = pcbnew.LoadBoard(path)
    rec = dict(footprints=[])
    # all library footprints placed and their graphic items listed first: after the first Duplicate() pcbnew 10's
    # SWIG wrapper returns GraphicalItems() of a later loaded footprint as an untyped SwigPyObject
    jobs = []
    for ref in REFS:
        fp = b.FindFootprintByReference(ref)
        new = R.load_fp(fp.GetFPIDAsString())
        b.Add(new)
        new.SetPosition(fp.GetPosition())
        if fp.IsFlipped():
            new.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        new.SetOrientation(fp.GetOrientation())
        if not R.same_pads(R.pad_sig(fp), R.pad_sig(new)):
            sys.exit(f"s13b: {ref} pads differ from the library footprint")
        jobs.append((ref, fp, new, list(fp.GraphicalItems()), list(new.GraphicalItems())))
    for ref, fp, new, old, items in jobs:
        for it in old:
            fp.Remove(it)
        for it in items:
            fp.Add(it.Duplicate())
        rec["footprints"].append(dict(ref=ref, fpid=fp.GetFPIDAsString(), replaced=len(old), added=len(items)))
    for ref, fp, new, old, items in jobs:
        b.Delete(new)
    for z in b.Zones():
        if not z.GetIsRuleArea():
            z.UnFill()
    pcbnew.SaveBoard(path, b)
    with open(os.path.join(os.path.dirname(path), "s13b.json"), "w") as f:
        json.dump(rec, f)


def main(argv):
    if "--edit" in argv:
        return edit(argv[argv.index("--edit") + 1])
    if os.path.exists(os.path.join(PROJ, "~" + NAME + ".kicad_pcb.lck")):
        sys.exit("s13b: the board is open in KiCad; close it first")
    dry = "--dry-run" in argv
    if not dry and os.path.exists(REC):
        sys.exit("s13b: already on the board (not re-runnable)")
    tmp = tempfile.mkdtemp(prefix=".s13b_", dir=ROOT)
    try:
        shutil.copy(os.path.join(PROJ, NAME + ".kicad_dru"), tmp)
        pcb = os.path.join(tmp, NAME + ".kicad_pcb")
        shutil.copy(BOARD, pcb)
        with open(os.path.join(PROJ, NAME + ".kicad_pro")) as f:
            pro = json.load(f)
        rs = pro["board"]["design_settings"]["rule_severities"]
        for k in rs:
            rs[k] = "ignore"                       # refill only
        with open(os.path.join(tmp, NAME + ".kicad_pro"), "w") as f:
            json.dump(pro, f, indent=2)
        if subprocess.run([sys.executable, "-u", os.path.abspath(__file__), "--edit", pcb]).returncode:
            sys.exit("s13b: edit failed, the board is unchanged")
        r = subprocess.run([CLI, "pcb", "drc", "--format", "json", "--refill-zones", "--save-board",
                            "-o", os.path.join(tmp, "refill.json"), pcb], capture_output=True, text=True)
        if r.returncode:
            sys.exit("s13b: zone refill failed, the board is unchanged\n" + r.stdout[-1500:] + r.stderr[-1500:])
        with open(os.path.join(tmp, "s13b.json")) as f:
            rec = json.load(f)
        print("s13b: " + ", ".join(f"{r['ref']} {r['replaced']} -> {r['added']} graphic items" for r in rec["footprints"]))
        if dry:
            shutil.copy(pcb, os.path.abspath(argv[argv.index("--dry-run") + 1]))
        else:
            shutil.copy(pcb, BOARD)
            with open(REC, "w") as f:
                json.dump(rec, f, indent=1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
