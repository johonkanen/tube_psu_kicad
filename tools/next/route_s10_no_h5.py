#!/usr/bin/env python3
"""Stage 10 (one-shot, not re-runnable; run with tools/p2k/bin/kipy): mounting hole H5 removed.

    tools/p2k/bin/kipy tools/next/route_s10_no_h5.py [--dry-run OUT.kicad_pcb]

User decision 2026-11-23: the hole H5 at (87.15, -29.81) on the east edge is not used and the board does not droop
without it. Deletes the footprint H5 and its rule area 'mounting hole H5 pour keep-out (secondary 4.2 mm creepage)'.
Zones are refilled by kicad-cli. Record: kicad_next/routing/deleted_s10.json.
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
REC = os.path.join(PROJ, "routing", "deleted_s10.json")


def edit(path):
    import pcbnew
    mm = pcbnew.ToMM
    b = pcbnew.LoadBoard(path)
    deleted = []
    fp = b.FindFootprintByReference("H5")
    p = fp.GetPosition()
    deleted.append(dict(kind="footprint", ref="H5", fpid=fp.GetFPIDAsString(), at=[mm(p.x), mm(p.y)]))
    b.Delete(fp)
    for z in list(b.Zones()):
        if z.GetIsRuleArea() and z.GetZoneName().startswith("mounting hole H5 "):
            deleted.append(dict(kind="rule area", name=z.GetZoneName()))
            b.Delete(z)
    assert len(deleted) == 2, deleted
    for z in b.Zones():
        if not z.GetIsRuleArea():
            z.UnFill()
    pcbnew.SaveBoard(path, b)
    with open(os.path.join(os.path.dirname(path), "s10.json"), "w") as f:
        json.dump(deleted, f)


def main(argv):
    if "--edit" in argv:
        return edit(argv[argv.index("--edit") + 1])
    if os.path.exists(os.path.join(PROJ, "~" + NAME + ".kicad_pcb.lck")):
        sys.exit("s10: the board is open in KiCad; close it first")
    dry = "--dry-run" in argv
    if not dry and os.path.exists(REC):
        sys.exit("s10: already on the board (not re-runnable)")
    tmp = tempfile.mkdtemp(prefix=".s10_", dir=ROOT)
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
            sys.exit("s10: edit failed, the board is unchanged")
        r = subprocess.run([CLI, "pcb", "drc", "--format", "json", "--refill-zones", "--save-board",
                            "-o", os.path.join(tmp, "refill.json"), pcb], capture_output=True, text=True)
        if r.returncode:
            sys.exit("s10: zone refill failed, the board is unchanged\n" + r.stdout[-1500:] + r.stderr[-1500:])
        with open(os.path.join(tmp, "s10.json")) as f:
            deleted = json.load(f)
        print(f"s10: deleted {len(deleted)}: " + ", ".join(d["kind"] for d in deleted))
        if dry:
            shutil.copy(pcb, os.path.abspath(argv[argv.index("--dry-run") + 1]))
        else:
            shutil.copy(pcb, BOARD)
            with open(REC, "w") as f:
                json.dump(dict(deleted=deleted), f, indent=1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
