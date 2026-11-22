#!/usr/bin/env python3
"""Routing stage 5b of tube_power 5.2 (2026-11-22): open signal connections closed one group at a time
(see README "Stage 5b").

    tools/p2k/bin/kipy tools/next/route_s5b_local.py --group NAME[,NAME...] [--dry-run OUT.kicad_pcb]

Incremental edit, same conventions as route_s4l_neck_toff.py; NOT re-runnable (a group that is listed in
routing/s5b_added.json is refused). The rebuild scripts stay frozen. Appends to kicad_next/routing/moves_s5b.json,
deleted_s5b.json, s5b_added.json. Zones are refilled by kicad-cli.

Entries: ADD ("t", net, layer key, width, [points]) / ("v", net, x, y, pad, drill); DEL (net, layer key, x0, y0, x1, y1,
why); DELVIA (net, x, y, why); MOVE (ref, x, y, rot, side, why).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PROJ = os.path.join(ROOT, "kicad_next")
NAME = "tube_psu_5_2"
BOARD = os.path.join(PROJ, NAME + ".kicad_pcb")
LOCK = os.path.join(PROJ, "~" + NAME + ".kicad_pcb.lck")
CLI = os.path.join(ROOT, "tools", "p2k", "bin", "kicad-cli")
RT = os.path.join(PROJ, "routing")
LAYER = {"F": "F.Cu", "B": "B.Cu", "2": "In2.Signal_HV", "3": "In3.Power"}
F, B, I2, I3 = "F", "B", "2", "3"
nm = lambda v: int(round(v * 1e6))  # noqa: E731
mm = lambda v: round(v / 1e6, 4)  # noqa: E731

P1V65, P3V3 = "+1V65_BIAS", "+3V3"
U9N, U9P = "Net-(U9--)", "Net-(U9-+)"
GROUPS = {
    # U9 (TLV316, B.Cu): inverting node R131 pad 1 - pin 4 - pin 1 and non-inverting node pin 3 - R3 pad 1. The
    # B.Cu +1V65_BIAS lane x 27.9 ran between R131 and pin 4: R131 turned (pads west / east) and moved 0.9 mm so the
    # lane passes between its pads; the lane via (27.9, -26.4) 0.25 mm north so pin 1 - pin 4 fits under the body.
    # U9-+ runs east of pin 4 and north of the +1V65_BIAS via (31.1, -26.4); the +3V3 lane there steps east later.
    "u9": dict(MOVE=[
        ("R131", 27.65, -23.3, 180.0, "B", "pad 1 (Net-(U9--)) east of the +1V65_BIAS lane, straight north of U9 pin 4"),
    ], DEL=[
        (P1V65, B, 27.9, -22.0, 27.9, -26.4, "lane between the pads of the turned R131, via 0.25 mm north"),
        (P1V65, B, 26.82, -22.115, 26.8, -22.115, "old pad stub of R131"),
        (P1V65, B, 26.8, -22.115, 27.4, -21.515, "old pad stub of R131"),
        (P1V65, F, 31.1, -26.4, 27.9, -26.4, "via 0.25 mm north"),
        (P3V3, B, 31.6, -25.3, 32.105, -25.805, "+3V3 lane steps south 1.6 mm further east (room for Net-(U9-+))"),
        (P3V3, B, 32.105, -25.805, 34.2, -25.805, "+3V3 lane steps south 1.6 mm further east (room for Net-(U9-+))"),
    ], DELVIA=[
        (P1V65, 27.9, -26.4, "0.25 mm north: pin 1 - pin 4 of U9 passes south of it"),
    ], ADD=[
        ("t", P1V65, B, 0.152, [(27.9, -22.0), (27.65, -22.4), (27.65, -24.0), (27.9, -24.25), (27.9, -26.15)]),
        ("t", P1V65, B, 0.2, [(27.65, -23.3), (26.825, -23.3)]),
        ("v", P1V65, 27.9, -26.15, 0.5, 0.3),
        ("t", P1V65, I2, 0.152, [(27.9, -26.4), (27.9, -26.15)]),
        ("t", P1V65, F, 0.152, [(31.1, -26.4), (28.15, -26.4), (27.9, -26.15)]),
        ("t", U9N, B, 0.2, [(28.475, -23.3), (28.72, -23.6), (28.72, -25.462)]),
        ("t", U9N, B, 0.2, [(26.82, -27.738), (26.82, -26.95), (27.07, -26.7), (28.47, -26.7), (28.72, -26.45), (28.72, -25.462)]),
        ("t", P3V3, B, 0.152, [(31.6, -25.3), (33.2, -25.3), (33.705, -25.805), (34.2, -25.805)]),
        ("t", U9P, B, 0.2, [(28.72, -27.738), (28.72, -27.4), (29.2, -27.4), (29.5, -27.1), (29.5, -26.1), (29.8, -25.8),
                            (31.75, -25.8), (31.75, -27.3), (31.4, -27.65), (31.075, -27.8)]),
    ]),
    # DRV2 pin 2 (OUTH) - R20 pad 1: the pin was closed in by the B.Cu 15V link pin 1 - via (14.06, 10.6) on x 13.95.
    # That link is now on F.Cu (new via in the edge of pin 1), and OUTH leaves the pin to the south-east.
    "drv2": dict(DEL=[
        ("15V", B, 13.95, 9.1, 13.95, 10.5, "15V link of DRV2 pin 1 onto F.Cu (way out for OUTH)"),
        ("15V", B, 12.868, 9.126, 13.868, 9.126, "15V link of DRV2 pin 1 onto F.Cu (way out for OUTH)"),
    ], ADD=[
        ("v", "15V", 13.2, 8.75, 0.6, 0.3),
        ("t", "15V", B, 0.4, [(12.868, 9.126), (13.2, 8.75)]),
        ("t", "15V", F, 0.4, [(13.2, 8.75), (13.2, 9.74), (14.06, 10.6)]),
        ("t", "Net-(DRV2-OUTH)", B, 0.3, [(12.868, 10.076), (13.5, 10.0), (14.1, 9.4), (14.737, 8.76), (14.737, 5.391)]),
    ]),
    # DRV6 pin 6 (DT) - R128 pad 1. The gap between the 5V_ISOL via (66.475, -51.5) and TR3 pin 9 (TRANS_SEC, 1.2 mm)
    # is 0.02 mm too narrow on B.Cu / F.Cu, In2 is crossed by the DAB_DIS_SEC and 5V_ISOL diagonals, In3 is the
    # 15V_ISO_SEC plane, and under DRV6 runs DHB_HI_GATE_SEC. The 5V_ISOL via moves 0.25 mm south-west along its In2
    # diagonal (onto the B.Cu track pin 8 - C93); DT: via east of pin 6, F.Cu on x 66.95 (C93 is on B.Cu), via in
    # R128 pad 1.
    "dt": dict(DEL=[
        ("5V_ISOL", I2, 69.975, -48.0, 66.475, -51.5, "5V_ISOL via 0.25 mm south-west (room for DT past TR3 pin 9)"),
        ("5V_ISOL", B, 66.475, -51.5, 66.475, -50.9, "5V_ISOL via 0.25 mm south-west (room for DT past TR3 pin 9)"),
    ], DELVIA=[
        ("5V_ISOL", 66.475, -51.5, "0.25 mm south-west (room for DT past TR3 pin 9)"),
    ], ADD=[
        ("t", "5V_ISOL", I2, 0.3, [(69.975, -48.0), (66.3, -51.675)]),
        ("v", "5V_ISOL", 66.3, -51.675, 0.6, 0.3),
        ("t", "5V_ISOL", B, 0.4, [(66.3, -51.675), (66.357, -51.675)]),
        ("t", "Net-(DRV6-DT)", B, 0.25, [(65.657, -55.102), (66.95, -55.102)]),
        ("v", "Net-(DRV6-DT)", 66.95, -55.102, 0.5, 0.3),
        ("t", "Net-(DRV6-DT)", F, 0.2, [(66.95, -55.102), (66.95, -49.35), (66.9, -49.3)]),
        ("v", "Net-(DRV6-DT)", 66.9, -49.3, 0.5, 0.3),
        ("t", "Net-(DRV6-DT)", B, 0.25, [(66.9, -49.3), (67.085, -49.1)]),
    ]),
    # C131 pad 2 - R82 pad 2 (output of U6). The fence was the Net-(U6-+) track R10 pad 2 - R17 pad 1 on y 5.6, which
    # ran into the gap between the pads of R17. It now drops to y 5.1 west of R17 (1.2 mm from R10 pad 1), and the
    # output runs on y 6.7 (1.4 mm south of the DC+ pad of C29), through the gap between the pads of R17, between the
    # pads of C130, east of C130 and back west on y 3.7 to R82 pad 2.
    "c131": dict(DEL=[
        ("Net-(U6-+)", B, 18.7, 5.6, 20.95, 5.6, "U6-+ link drops south before R17 (gap between the R17 pads for the output)"),
        ("Net-(U6-+)", B, 20.95, 5.6, 21.4, 5.15, "U6-+ link drops south before R17 (gap between the R17 pads for the output)"),
        ("Net-(U6-+)", B, 21.4, 5.15, 21.4, 4.875, "U6-+ link drops south before R17 (gap between the R17 pads for the output)"),
    ], ADD=[
        ("t", "Net-(U6-+)", B, 0.152, [(18.7, 5.6), (20.1, 5.6), (20.6, 5.1), (21.175, 5.1), (21.4, 4.875)]),
        ("t", "Net-(C131-Pad2)", B, 0.152, [(16.73, 6.815), (16.845, 6.7), (20.0, 6.7), (20.5, 6.2), (20.5, 5.9), (20.7, 5.7),
                                             (22.0, 5.7), (22.26, 5.44), (23.6, 5.44), (23.85, 5.19), (23.85, 3.95),
                                             (23.6, 3.7), (22.7, 3.7), (22.3, 3.3), (22.125, 3.0)]),
    ]),
    # Q9 pad 1 (drain) - RL1 pin 5 / D9 anode. On B.Cu the GPIO_BYPASS_RLY track (x -60.15, then east on y -39.4)
    # and the 5V track (x -59.7) both run between them. Via under the body of Q9, west of the F.Cu Net-(RL1-COM) pour
    # (1.2 mm), and In3 (no pour, no other track here) straight to the through-hole pin 5 of RL1.
    "q9d": dict(ADD=[
        ("t", "Net-(Q9-D)", B, 0.25, [(-61.642, -31.9), (-62.4, -31.9)]),
        ("v", "Net-(Q9-D)", -62.4, -31.9, 0.5, 0.3),
        ("t", "Net-(Q9-D)", I3, 0.25, [(-62.4, -31.9), (-58.4, -35.9), (-56.351, -35.902)]),
    ]),
    # Net-(R51-Pad2) (DC+ divider node, HV_PRIMARY): In2 lane end (11.578, 16.478) - R51 pad 2. In2 between the
    # Net-(R48-Pad2) lane (x 8.6, 0.5 mm) and the PFC_PWM2 lane (x 10.594): x 9.7, then a diagonal 0.54 mm from
    # the R48 via (6.4, 8.6) to a via in the corner of R51 pad 2 (1.2 mm from R51 pad 1 and R48 pad 2; F.Cu is empty
    # there, north of the heatsink strip).
    "r51": dict(ADD=[
        ("t", "Net-(R51-Pad2)", I2, 0.152, [(11.578, 16.478), (9.7, 14.6), (9.7, 10.6), (5.6, 6.5), (5.6, 6.3)]),
        ("v", "Net-(R51-Pad2)", 5.6, 6.3, 0.5, 0.3),
    ]),
    # GND pour 'Proteus B.Cu pour 21': two islands (north / south of the Net-(REF1-VOUT) track); one via to the GND
    # planes in each
    "gnd21": dict(ADD=[
        ("v", "GND", 42.1, -29.6, 0.5, 0.3),
        ("v", "GND", 35.3, -27.5, 0.5, 0.3),
    ]),
    # D32 cathode: the last 0.14 mm of the DHB_LOW_GATE_SEC track ended 1.15 mm from R149 pad 2 (HV functional 1.2 mm);
    # the segment before it already ends inside the pad of D32
    "d32": dict(DEL=[
        ("DHB_LOW_GATE_SEC", B, 73.81, -47.72, 73.91, -47.82, "redundant end inside the D32 pad, 1.15 mm from R149 pad 2"),
    ]),
}


def edit(path, names):
    DELETED, ADDED, MOVES, WARN = [], [], [], []
    b = pcbnew.LoadBoard(path)
    lid = {b.GetLayerName(l): l for l in b.GetEnabledLayers().CuStack()}
    near = lambda p, x, y: abs(p[0] - x) <= 0.005 and abs(p[1] - y) <= 0.005  # noqa: E731
    for g in names:
        G = GROUPS[g]
        tracks = []
        for t in b.GetTracks():
            via = t.Type() == pcbnew.PCB_VIA_T
            s, e = t.GetStart(), t.GetEnd()
            tracks.append([t, via, t.GetNetname(), None if via else t.GetLayer(), (s.x / 1e6, s.y / 1e6),
                           (e.x / 1e6, e.y / 1e6), 0 if via else t.GetWidth() / 1e6])
        for net, lay, x0, y0, x1, y1, why in G.get("DEL", []):
            hit = [r for r in tracks if not r[1] and r[2] == net and r[3] == lid[LAYER[lay]]
                   and ((near(r[4], x0, y0) and near(r[5], x1, y1)) or (near(r[4], x1, y1) and near(r[5], x0, y0)))]
            if not hit:
                WARN.append(f"delete: no segment {net} {lay} ({x0}, {y0}) - ({x1}, {y1})")
            for r in hit:
                DELETED.append(dict(group=g, kind="segment", net=net, layer=LAYER[lay], start=[round(v, 4) for v in r[4]],
                                    end=[round(v, 4) for v in r[5]], width=round(r[6], 4), why=why))
                b.Delete(r[0])
                tracks.remove(r)
        for net, x, y, why in G.get("DELVIA", []):
            hit = [r for r in tracks if r[1] and r[2] == net and near(r[4], x, y)]
            if not hit:
                WARN.append(f"delvia: no via {net} ({x}, {y})")
            for r in hit:
                DELETED.append(dict(group=g, kind="via", net=net, at=[x, y], why=why))
                b.Delete(r[0])
                tracks.remove(r)
        for ref, x, y, rot, to_side, why in G.get("MOVE", []):
            fp = b.FindFootprintByReference(ref)
            p = fp.GetPosition()
            side = "B" if fp.IsFlipped() else "F"
            if side != to_side:
                sys.exit("s5b: no side changes in this stage")
            MOVES.append(dict(group=g, ref=ref, frm=dict(x=mm(p.x), y=mm(p.y), rot=fp.GetOrientationDegrees(), side=side),
                              to=dict(x=x, y=y, rot=rot, side=to_side), why=why))
            fp.SetPosition(pcbnew.VECTOR2I(nm(x), nm(y)))
            fp.SetOrientationDegrees(rot)
            for pad in fp.Pads():
                q = pad.GetPosition()
                print(f"s5b: {ref} pad {pad.GetNumber()} {pad.GetNetname()} at ({mm(q.x)}, {mm(q.y)})")
        for a in G.get("ADD", []):
            code = b.GetNetcodeFromNetname(a[1])
            if code <= 0:
                sys.exit(f"s5b: no net {a[1]}")
            if a[0] == "v":
                v = pcbnew.PCB_VIA(b)
                v.SetPosition(pcbnew.VECTOR2I(nm(a[2]), nm(a[3])))
                v.SetViaType(pcbnew.VIATYPE_THROUGH)
                v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                v.SetWidth(pcbnew.F_Cu, nm(a[4]))
                v.SetDrill(nm(a[5]))
                v.SetNetCode(code)
                b.Add(v)
                ADDED.append(dict(group=g, kind="via", net=a[1], at=[a[2], a[3]], size=[a[4], a[5]]))
            else:
                _, n, lay, w, pts = a
                for p, q in zip(pts, pts[1:]):
                    t = pcbnew.PCB_TRACK(b)
                    t.SetStart(pcbnew.VECTOR2I(nm(p[0]), nm(p[1])))
                    t.SetEnd(pcbnew.VECTOR2I(nm(q[0]), nm(q[1])))
                    t.SetWidth(nm(w))
                    t.SetLayer(lid[LAYER[lay]])
                    t.SetNetCode(code)
                    b.Add(t)
                    ADDED.append(dict(group=g, kind="segment", net=n, layer=LAYER[lay], start=list(p), end=list(q), width=w))
    for z in b.Zones():
        if not z.GetIsRuleArea():
            z.UnFill()
    pcbnew.SaveBoard(path, b)
    with open(os.path.join(os.path.dirname(path), "s5b.json"), "w") as f:
        json.dump(dict(deleted=DELETED, added=ADDED, moves=MOVES, warn=WARN), f)


def main(argv):
    if os.path.exists(LOCK):
        sys.exit("s5b: the board is open in KiCad; close it first")
    names = argv[argv.index("--group") + 1].split(",")
    files = (("deleted_s5b.json", "deleted"), ("s5b_added.json", "added"), ("moves_s5b.json", "moves"))
    prev = {"deleted": [], "added": [], "moves": [], "groups": []}
    if os.path.exists(os.path.join(RT, "s5b_added.json")):
        for name, key in files:
            with open(os.path.join(RT, name)) as f:
                d = json.load(f)
            prev[key] = d[key]
            prev["groups"] = d.get("groups", prev["groups"])
    dry = "--dry-run" in argv
    if not dry and any(g in prev["groups"] for g in names):
        sys.exit("s5b: group already on the board (not re-runnable)")
    src = BOARD
    if "--from" in argv:                               # dry run on top of an earlier dry run
        src = os.path.abspath(argv[argv.index("--from") + 1])
    tmp = tempfile.mkdtemp(prefix=".s5b_", dir=ROOT)
    try:
        shutil.copy(os.path.join(PROJ, NAME + ".kicad_dru"), tmp)
        pcb = os.path.join(tmp, NAME + ".kicad_pcb")
        shutil.copy(src, pcb)
        with open(os.path.join(PROJ, NAME + ".kicad_pro")) as f:
            pro = json.load(f)
        rs = pro["board"]["design_settings"]["rule_severities"]
        for k in rs:
            rs[k] = "ignore"                       # refill only
        with open(os.path.join(tmp, NAME + ".kicad_pro"), "w") as f:
            json.dump(pro, f, indent=2)
        r = subprocess.run([sys.executable, "-u", os.path.abspath(__file__), "--edit", pcb, ",".join(names)])
        if r.returncode:
            sys.exit("s5b: edit failed, the board is unchanged")
        r = subprocess.run([CLI, "pcb", "drc", "--format", "json", "--refill-zones", "--save-board",
                            "-o", os.path.join(tmp, "refill.json"), pcb], capture_output=True, text=True)
        if r.returncode:
            sys.exit("s5b: zone refill failed, the board is unchanged\n" + r.stdout[-1500:] + r.stderr[-1500:])
        with open(os.path.join(tmp, "s5b.json")) as f:
            j = json.load(f)
        for w in j["warn"]:
            print("s5b: WARNING " + w)
        print(f"s5b: {names}: deleted {len(j['deleted'])}, added {len(j['added'])}, moved {len(j['moves'])}")
        if dry:
            out = os.path.abspath(argv[argv.index("--dry-run") + 1])
            shutil.copy(pcb, out)
            print(f"s5b: dry run in {out}, the board is unchanged")
            return 0
        shutil.copy(pcb, BOARD)
        note = "routing stage 5b (2026-11-22), tools/next/route_s5b_local.py - incremental edit of the board, not a rebuild"
        for name, key in files:
            with open(os.path.join(RT, name), "w") as f:
                json.dump({"note": note, "groups": prev["groups"] + names, key: prev[key] + j[key]}, f, indent=1)
        print("s5b: wrote the board and routing/*_s5b.json")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    if "--edit" in sys.argv:
        i = sys.argv.index("--edit")
        edit(sys.argv[i + 1], sys.argv[i + 2].split(","))
        sys.exit(0)
    sys.exit(main(sys.argv[1:]))
