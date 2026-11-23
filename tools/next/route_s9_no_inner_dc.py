#!/usr/bin/env python3
"""Stage 9 (one-shot, not re-runnable; run with tools/p2k/bin/kipy): no DC+ copper on inner layers.

    tools/p2k/bin/kipy tools/next/route_s9_no_inner_dc.py [--dry-run OUT.kicad_pcb]

User decision 2026-11-23: DC+ (and the power GND return) stay on F.Cu / B.Cu. Deletes the two DC+ items on
In3.Power: the 1.8 mm track (12.75, -49.52) - (18.7, -49.52) of stage 8 and the zone S4L_DC+_In3_neck of
stage 4l with its two vias (10.2 / 11.3, -17.5). Zones are refilled by kicad-cli. Record: kicad_next/routing/deleted_s9.json.
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
REC = os.path.join(PROJ, "routing", "deleted_s9.json")


def edit(path):
    import pcbnew
    mm = pcbnew.ToMM
    b = pcbnew.LoadBoard(path)
    deleted = []
    for t in list(b.GetTracks()):
        if t.GetNetname() == "DC+" and t.Type() != pcbnew.PCB_VIA_T and b.GetLayerName(t.GetLayer()) == "In3.Power":
            s, e = t.GetStart(), t.GetEnd()
            deleted.append(dict(kind="segment", net="DC+", layer="In3.Power", width=mm(t.GetWidth()),
                                start=[mm(s.x), mm(s.y)], end=[mm(e.x), mm(e.y)]))
            b.Delete(t)
    for z in list(b.Zones()):
        if z.GetZoneName() == "S4L_DC+_In3_neck":
            o = z.Outline().Outline(0)
            deleted.append(dict(kind="zone", net="DC+", layer="In3.Power", name=z.GetZoneName(),
                                outline=[[mm(o.CPoint(i).x), mm(o.CPoint(i).y)] for i in range(o.PointCount())]))
            b.Delete(z)
    for t in list(b.GetTracks()):                  # the two vias that fed the zone only (F.Cu side stays connected)
        if t.GetNetname() == "DC+" and t.Type() == pcbnew.PCB_VIA_T:
            p = t.GetPosition()
            if (round(mm(p.x), 2), round(mm(p.y), 2)) in ((10.2, -17.5), (11.3, -17.5)):
                deleted.append(dict(kind="via", net="DC+", at=[mm(p.x), mm(p.y)], size=mm(t.GetWidth(pcbnew.F_Cu)),
                                    drill=mm(t.GetDrillValue())))
                b.Delete(t)
    for z in b.Zones():
        if not z.GetIsRuleArea():
            z.UnFill()
    pcbnew.SaveBoard(path, b)
    with open(os.path.join(os.path.dirname(path), "s9.json"), "w") as f:
        json.dump(deleted, f)


def main(argv):
    if "--edit" in argv:
        return edit(argv[argv.index("--edit") + 1])
    if os.path.exists(os.path.join(PROJ, "~" + NAME + ".kicad_pcb.lck")):
        sys.exit("s9: the board is open in KiCad; close it first")
    dry = "--dry-run" in argv
    if not dry and os.path.exists(REC):
        sys.exit("s9: already on the board (not re-runnable)")
    tmp = tempfile.mkdtemp(prefix=".s9_", dir=ROOT)
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
            sys.exit("s9: edit failed, the board is unchanged")
        r = subprocess.run([CLI, "pcb", "drc", "--format", "json", "--refill-zones", "--save-board",
                            "-o", os.path.join(tmp, "refill.json"), pcb], capture_output=True, text=True)
        if r.returncode:
            sys.exit("s9: zone refill failed, the board is unchanged\n" + r.stdout[-1500:] + r.stderr[-1500:])
        with open(os.path.join(tmp, "s9.json")) as f:
            deleted = json.load(f)
        print(f"s9: deleted {len(deleted)}: " + ", ".join(d["kind"] for d in deleted))
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
