#!/usr/bin/env python3
"""Stage 13c (one-shot, not re-runnable; run with tools/p2k/bin/kipy): mounting holes without copper ring, keep-off
from a 6 mm screw head.

    tools/p2k/bin/kipy tools/next/route_s13c_holes.py [--dry-run OUT.kicad_pcb]

Design review 2026-11-23 (findings 10 D2 / F1, 14 B4 / F6):
  * H1-H4, H6-H8 (tube_psu:MountingHole_3.0mm_NPTH_Ring3.5mm, 0.25 mm no-net copper ring on all six layers) become
    tube_psu_next:MountingHole_3.0mm_NPTH (same place, same 3.0 mm NPTH, no copper; tools/next/gen_next_footprints.py);
  * the pour keep-outs round the holes grow so that the pours keep basic insulation from a 6 mm earthed screw head /
    standoff (radius 3.0 mm): primary 3.2 mm -> 6.2 mm from the centre, secondary 4.2 mm -> 7.2 mm. The 32-gon is
    drawn on radius R_KO (flats at R_KO * cos(5.625 deg)). Where fixed pads of parts are nearer than that, the
    keep-out is not grown past them (it would only cut pour without raising the minimum): H8 (C102 pad 1 at 6.23 mm)
    stays at 6.3 mm, H4 (DRV5 / R14 / C92 / L2 pads at 5.03 - 5.08 mm, the In2 control bus at 4.95 mm) and H1 / H2
    (no primary / secondary copper within 8 mm; H2 = UART island, J4 pad 1 at 3.68 mm) keep their keep-outs;
  * H2: the B.Cu ISO_UART_GND bus of J4 moved 0.15 mm east (2.98 -> 3.13 mm from the centre); the J4 pads (3.68 mm)
    stay the limit, so H2 needs an insulating washer / nylon screw (README stage 13c).
Zones are refilled by kicad-cli. Record: kicad_next/routing/moves_s13c.json.
"""
import json
import math
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
REC = os.path.join(PROJ, "routing", "moves_s13c.json")
HOLES = ["H1", "H2", "H3", "H4", "H6", "H7", "H8"]
HOLE_FPID = "tube_psu_next:MountingHole_3.0mm_NPTH"
# hole -> (keep-out vertex radius mm, new zone name)
R_KO = {"H3": (7.3, "mounting hole H3 pour keep-out (6 mm head + secondary 4.2 mm)"),
        "H6": (6.3, "mounting hole H6 pour keep-out (6 mm head + primary 3.2 mm)"),
        "H7": (6.3, "mounting hole H7 pour keep-out (6 mm head + primary 3.2 mm)"),
        "H8": (6.3, "mounting hole H8 pour keep-out (6 mm head + 3.3 mm; C102 pad 1 at 6.23 mm, secondary 4.2 not reached)")}
# (net, layer, start, end, width) to delete / add
GNDU = "ISO_UART_GND"
DELETE = [(GNDU, "B.Cu", (11.4, -89.0), (10.05, -87.65), 0.3),          # J4 ground bus past H2: 2.98 mm from the centre,
          (GNDU, "B.Cu", (10.05, -87.65), (10.05, -83.92), 0.3)]        # i.e. touching a 6 mm head
ADD = [(GNDU, "B.Cu", (11.4, -89.0), (10.2, -87.8), 0.3),                # 0.15 mm further east (0.2 mm to J4 pad 2)
       (GNDU, "B.Cu", (10.2, -87.8), (10.2, -84.07), 0.3),
       (GNDU, "B.Cu", (10.2, -84.07), (10.05, -83.92), 0.3)]


def edit(path):
    import pcbnew
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import reuse_51_board as R
    mm, MM = pcbnew.ToMM, pcbnew.FromMM
    b = pcbnew.LoadBoard(path)
    rec = dict(footprints=[], keepouts={}, deleted=[], added=[])
    centre = {}
    for ref in HOLES:
        old = b.FindFootprintByReference(ref)
        new = R.load_fp(HOLE_FPID)
        new.SetReference(ref)
        new.SetPosition(old.GetPosition())
        new.SetLocked(old.IsLocked())
        b.Add(new)
        centre[ref] = old.GetPosition()
        rec["footprints"].append(dict(ref=ref, at=[mm(old.GetPosition().x), mm(old.GetPosition().y)],
                                      old=old.GetFPIDAsString(), new=HOLE_FPID))
        b.Delete(old)
    for z in list(b.Zones()):
        if not z.GetIsRuleArea():
            continue
        for ref, (r, nm) in R_KO.items():
            if z.GetZoneName().startswith(f"mounting hole {ref} pour keep-out"):
                c = centre[ref]
                o = z.Outline().Outline(0)
                n = o.PointCount()
                r0 = math.hypot(o.CPoint(0).x - c.x, o.CPoint(0).y - c.y)
                pts = []
                for i in range(n):
                    p = o.CPoint(i)
                    a = math.atan2(p.y - c.y, p.x - c.x)
                    pts.append(pcbnew.VECTOR2I(int(c.x + MM(r) * math.cos(a)), int(c.y + MM(r) * math.sin(a))))
                z.Outline().RemoveAllContours()
                z.Outline().NewOutline()
                for p in pts:
                    z.Outline().Append(p)
                rec["keepouts"][ref] = dict(old_name=z.GetZoneName(), new_name=nm, r_old=round(mm(r0), 3), r_new=r, points=n)
                z.SetZoneName(nm)
    for nn, lay, s, e, w in DELETE:
        hit = [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_TRACE_T and t.GetNetname() == nn
               and b.GetLayerName(t.GetLayer()) == lay and abs(mm(t.GetWidth()) - w) < 1e-3
               and {(round(mm(t.GetStart().x), 2), round(mm(t.GetStart().y), 2)),
                    (round(mm(t.GetEnd().x), 2), round(mm(t.GetEnd().y), 2))} == {(round(s[0], 2), round(s[1], 2)), (round(e[0], 2), round(e[1], 2))}]
        if len(hit) != 1:
            sys.exit(f"s13c: segment {nn} {lay} {s} {e} found {len(hit)} times")
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
    for z in b.Zones():
        if not z.GetIsRuleArea():
            z.UnFill()
    pcbnew.SaveBoard(path, b)
    with open(os.path.join(os.path.dirname(path), "s13c.json"), "w") as f:
        json.dump(rec, f)


def main(argv):
    if "--edit" in argv:
        return edit(argv[argv.index("--edit") + 1])
    if os.path.exists(os.path.join(PROJ, "~" + NAME + ".kicad_pcb.lck")):
        sys.exit("s13c: the board is open in KiCad; close it first")
    dry = "--dry-run" in argv
    if not dry and os.path.exists(REC):
        sys.exit("s13c: already on the board (not re-runnable)")
    tmp = tempfile.mkdtemp(prefix=".s13c_", dir=ROOT)
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
            sys.exit("s13c: edit failed, the board is unchanged")
        r = subprocess.run([CLI, "pcb", "drc", "--format", "json", "--refill-zones", "--save-board",
                            "-o", os.path.join(tmp, "refill.json"), pcb], capture_output=True, text=True)
        if r.returncode:
            sys.exit("s13c: zone refill failed, the board is unchanged\n" + r.stdout[-1500:] + r.stderr[-1500:])
        with open(os.path.join(tmp, "s13c.json")) as f:
            rec = json.load(f)
        print(f"s13c: {len(rec['footprints'])} hole footprints replaced, keep-outs {rec['keepouts']}, "
              f"{len(rec['deleted'])} segments replaced by {len(rec['added'])}")
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
