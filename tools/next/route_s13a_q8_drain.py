#!/usr/bin/env python3
"""Stage 13a (one-shot, not re-runnable; run with tools/p2k/bin/kipy): Q8 drain link of the DAB secondary node.

    tools/p2k/bin/kipy tools/next/route_s13a_q8_drain.py [--dry-run OUT.kicad_pcb]

Design review 2026-11-23 (findings 07 D2 / F4, 11 E4 / F1): DHB_HI_SOURCE_SEC (2.2 A rms) reached Q8 pin 2 through
ONE 1.0/0.5 via at (62.8, -49.2) and 0.75 mm exits at Q8.2 (B.Cu) and Q21.3 (F.Cu). This stage
  * adds three 0.8/0.4 vias beside it: one on the B.Cu 1.0 mm track x 62.8 at y -48.1 (joined on F.Cu by a 1.2 mm
    stub from the old via; a longer stub would cut the F.Cu 420V pour between Q21.2 and C16) and two at
    (62.0 / 61.2, -49.6) on the F.Cu 1.2 mm track (joined on B.Cu by a 1.0 / 0.8 mm piece from the old via);
  * moves the In3 15V_ISO_SEC link (via (62.5, -43.8) -> In3 plane) 1.2 mm west (x 61.2 -> 60.0) to make room
    for the vias (0.5 mm inner HV clearance);
  * widens the B.Cu exit at Q8.2 to 1.0 mm from y -43.6 (between the Q8 pads the 1.2 mm HV rule to Q8.1 / Q8.3
    leaves no room for more than the 0.75 mm piece);
  * widens the F.Cu exit at Q21.3 to 1.2 mm, centre moved 0.225 mm west (x 54.45) to keep 1.2 mm to Q21.2 (420V).
Zones are refilled by kicad-cli. Record: kicad_next/routing/moves_s13a.json.
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
REC = os.path.join(PROJ, "routing", "moves_s13a.json")
NET = "DHB_HI_SOURCE_SEC"

# (net, layer, start, end, width) to delete / add
SEC15 = "15V_ISO_SEC"
DELETE = [(NET, "B.Cu", (68.88, -41.95), (68.88, -44.4), 0.75),
          (NET, "F.Cu", (54.675, -41.95), (54.675, -44.6), 0.75),
          (SEC15, "In3.Power", (62.5, -46.0), (61.2, -47.3), 0.5),
          (SEC15, "In3.Power", (61.2, -47.3), (61.2, -50.5), 0.5)]
ADD = [(NET, "B.Cu", (68.88, -41.95), (68.88, -43.6), 0.75),
       (NET, "B.Cu", (68.88, -43.6), (68.88, -44.4), 1.0),
       (NET, "F.Cu", (54.45, -41.95), (54.45, -44.6), 1.2),
       (NET, "F.Cu", (54.45, -44.6), (54.675, -44.6), 1.2),
       (NET, "F.Cu", (62.8, -49.2), (62.8, -48.1), 1.2),
       (NET, "B.Cu", (62.8, -49.2), (62.4, -49.6), 1.0),
       (NET, "B.Cu", (62.4, -49.6), (62.0, -49.6), 1.0),
       (NET, "B.Cu", (62.0, -49.6), (61.2, -49.6), 0.8),
       (SEC15, "In3.Power", (62.5, -46.0), (60.0, -48.5), 0.5),
       (SEC15, "In3.Power", (60.0, -48.5), (60.0, -50.5), 0.5)]
VIAS = [((62.8, -48.1), 0.8, 0.4), ((62.0, -49.6), 0.8, 0.4), ((61.2, -49.6), 0.8, 0.4)]


def edit(path):
    import pcbnew
    mm, MM = pcbnew.ToMM, pcbnew.FromMM
    b = pcbnew.LoadBoard(path)
    rec = dict(deleted=[], added=[], vias=[])
    for nn, lay, s, e, w in DELETE:
        hit = [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_TRACE_T and t.GetNetname() == nn
               and b.GetLayerName(t.GetLayer()) == lay and abs(mm(t.GetWidth()) - w) < 1e-3
               and {(round(mm(t.GetStart().x), 2), round(mm(t.GetStart().y), 2)),
                    (round(mm(t.GetEnd().x), 2), round(mm(t.GetEnd().y), 2))} == {(round(s[0], 2), round(s[1], 2)), (round(e[0], 2), round(e[1], 2))}]
        if len(hit) != 1:
            sys.exit(f"s13a: segment {lay} {s} {e} found {len(hit)} times")
        b.Delete(hit[0])
        rec["deleted"].append(dict(net=nn, layer=lay, start=s, end=e, width=w))
    for nn, lay, s, e, w in ADD:
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(pcbnew.VECTOR2I(MM(s[0]), MM(s[1])))
        t.SetEnd(pcbnew.VECTOR2I(MM(e[0]), MM(e[1])))
        t.SetWidth(MM(w))
        t.SetLayer(b.GetLayerID(lay))
        t.SetNet(b.FindNet(nn))
        b.Add(t)
        rec["added"].append(dict(net=nn, layer=lay, start=s, end=e, width=w))
    for p, d, h in VIAS:
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(pcbnew.VECTOR2I(MM(p[0]), MM(p[1])))
        v.SetWidth(MM(d))
        v.SetDrill(MM(h))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(b.FindNet(NET))
        b.Add(v)
        rec["vias"].append(dict(at=p, size=d, drill=h))
    for z in b.Zones():
        if not z.GetIsRuleArea():
            z.UnFill()
    pcbnew.SaveBoard(path, b)
    with open(os.path.join(os.path.dirname(path), "s13a.json"), "w") as f:
        json.dump(rec, f)


def main(argv):
    if "--edit" in argv:
        return edit(argv[argv.index("--edit") + 1])
    if os.path.exists(os.path.join(PROJ, "~" + NAME + ".kicad_pcb.lck")):
        sys.exit("s13a: the board is open in KiCad; close it first")
    dry = "--dry-run" in argv
    if not dry and os.path.exists(REC):
        sys.exit("s13a: already on the board (not re-runnable)")
    tmp = tempfile.mkdtemp(prefix=".s13a_", dir=ROOT)
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
            sys.exit("s13a: edit failed, the board is unchanged")
        r = subprocess.run([CLI, "pcb", "drc", "--format", "json", "--refill-zones", "--save-board",
                            "-o", os.path.join(tmp, "refill.json"), pcb], capture_output=True, text=True)
        if r.returncode:
            sys.exit("s13a: zone refill failed, the board is unchanged\n" + r.stdout[-1500:] + r.stderr[-1500:])
        with open(os.path.join(tmp, "s13a.json")) as f:
            rec = json.load(f)
        print(f"s13a: {len(rec['deleted'])} segments replaced, {len(rec['added'])} added, {len(rec['vias'])} vias")
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
