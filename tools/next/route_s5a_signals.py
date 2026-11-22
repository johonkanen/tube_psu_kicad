#!/usr/bin/env python3
"""Routing stage 5a of tube_power 5.2 (2026-11-22): open signal connections closed one group at a time
(see README "Stage 5a").

    tools/p2k/bin/kipy tools/next/route_s5a_signals.py --group NAME[,NAME...] [--dry-run OUT.kicad_pcb]

Incremental edit, same conventions as route_s4l_neck_toff.py; NOT re-runnable (a group that is listed in
routing/s5a_added.json is refused). The rebuild scripts stay frozen. Appends to kicad_next/routing/moves_s5a.json,
deleted_s5a.json, s5a_added.json. Zones are refilled by kicad-cli.

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

VERR, FB, VIN, D10A = "Net-(PWM2-VERR)", "Net-(PWM2-FB)", "Net-(PWM2-VIN)", "Net-(D10-PadA)"
P3V3 = "+3V3"
GPIO = "GPIO_BYPASS_RLY"
AUX = "/04 MCU connector/AUX_MEAS"
GROUPS = {
    # PWM2 (ICE5AR0680AG, F.Cu) and its B.Cu passives
    "pwm2": dict(ADD=[
        # VERR: R138 pad 2 - R139 pad 1, B.Cu between the GND pads of R139 (top y -2.195) and C15 (bottom y -1.45)
        ("t", VERR, B, 0.2, [(48.77, -2.155), (49.105, -1.82), (51.6, -1.82), (51.995, -2.215), (51.995, -2.67)]),
        # FB: R140 pad 1 - C139 pad 1 on B.Cu, via in the edge of C139 pad 1, F.Cu under the body of PWM2
        # (north of the GND via (50.1, 1.605), south of pin 9 and of the gate via) to pin 3
        ("t", FB, B, 0.2, [(47.2, -2.755), (47.75, -2.205), (47.75, -1.6), (48.6, -0.75), (49.3, -0.745)]),
        ("v", FB, 49.38, -0.745, 0.6, 0.3),
        ("t", FB, B, 0.2, [(49.3, -0.745), (49.38, -0.745)]),
        ("t", FB, F, 0.2, [(49.38, -0.745), (49.38, 2.0), (49.78, 2.4), (50.9, 2.4), (51.705, 1.595), (51.705, -0.275)]),
        # VIN: R153 pad 2 (B.Cu) east on y 10.6, south on x 55.15 (east of C51, 1.2 mm from TR1 pin 12 and from the
        # DC+ track of C15), via (55.15, 3.7), F.Cu on x 55.15 to pin 1 from the east
        ("t", VIN, B, 0.2, [(47.83, 10.797), (48.03, 10.6), (53.65, 10.6), (55.15, 9.1), (55.15, 3.7)]),
        ("v", VIN, 55.15, 3.7, 0.6, 0.3),
        ("t", VIN, F, 0.2, [(55.15, 3.7), (55.15, 0.3), (54.7, -0.15), (54.245, -0.15)]),
        # D10 anode (F.Cu) - R142 pad 2 (B.Cu): via in both pads. The pad is closed in on F.Cu (+3V3 west, 15V south /
        # east / north) and the In2 lanes of AUX_MEAS (x 36.53) and 5V_MEAS (x 37.4) are 0.72 mm apart under it, so
        # the AUX_MEAS lane moves 0.33 mm west (x 36.2) under the pad
        ("t", AUX, I2, 0.15, [(33.771, 3.879), (35.0, 3.879), (36.2, 2.679), (36.2, 1.93), (36.53, 1.6)]),
        ("v", D10A, 36.8, 3.2, 0.5, 0.3),
        ("t", D10A, F, 0.25, [(36.661, 3.2), (36.8, 3.2)]),
        ("t", D10A, B, 0.25, [(36.8, 3.2), (37.26, 2.975)]),
    ], DEL=[
        (AUX, I2, 33.771, 3.879, 35.9, 3.879, "AUX_MEAS In2 lane 0.33 mm west under D10 (room for the anode via)"),
        (AUX, I2, 35.9, 3.879, 36.53, 3.249, "AUX_MEAS In2 lane 0.33 mm west under D10 (room for the anode via)"),
        (AUX, I2, 36.53, 3.249, 36.53, 1.6, "AUX_MEAS In2 lane 0.33 mm west under D10 (room for the anode via)"),
    ]),
    # +3V3: C125 pad 1 (end of the B.Cu feed of U11) by a via and In3 (free of pours here, north of the 15V plane
    # edge y -60.55) to the via (5.8, -60.1) of the U1 block, and to a via on the In2 bus lane y -52.8 at x -12.5
    # (west of the B.Cu 15V track, 2.3 mm from the F.Cu DC+ pour). The lane is the second of the bundle: the outer
    # lane GPIO_BYPASS_RLY (y -52.3) steps 0.4 mm north round the via.
    "p3v3": dict(ADD=[
        ("t", P3V3, B, 0.2, [(0.4, -59.175), (0.8, -59.6), (0.8, -60.2)]),
        ("v", P3V3, 0.8, -60.2, 0.6, 0.3),
        ("t", P3V3, I3, 0.25, [(0.8, -60.2), (1.2, -59.8), (5.5, -59.8), (5.8, -60.1)]),
        ("t", GPIO, I2, 0.152, [(-20.0, -45.3), (-13.4, -51.9), (-11.7, -51.9), (-11.3, -52.3), (-1.412, -52.3)]),
        ("t", P3V3, I2, 0.152, [(-12.5, -52.8), (-12.5, -52.6)]),
        ("v", P3V3, -12.5, -52.6, 0.6, 0.3),
        ("t", P3V3, I3, 0.25, [(-12.5, -52.6), (-12.5, -55.5), (-8.6, -59.4), (0.0, -59.4), (0.8, -60.2)]),
    ], DEL=[
        (GPIO, I2, -20.0, -45.3, -13.0, -52.3, "GPIO_BYPASS_RLY lane 0.4 mm north round the +3V3 via (-12.5, -52.6)"),
        (GPIO, I2, -13.0, -52.3, -1.412, -52.3, "GPIO_BYPASS_RLY lane 0.4 mm north round the +3V3 via (-12.5, -52.6)"),
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
                sys.exit("s5a: no side changes in this stage")
            MOVES.append(dict(group=g, ref=ref, frm=dict(x=mm(p.x), y=mm(p.y), rot=fp.GetOrientationDegrees(), side=side),
                              to=dict(x=x, y=y, rot=rot, side=to_side), why=why))
            fp.SetPosition(pcbnew.VECTOR2I(nm(x), nm(y)))
            fp.SetOrientationDegrees(rot)
            for pad in fp.Pads():
                q = pad.GetPosition()
                print(f"s5a: {ref} pad {pad.GetNumber()} {pad.GetNetname()} at ({mm(q.x)}, {mm(q.y)})")
        for a in G.get("ADD", []):
            code = b.GetNetcodeFromNetname(a[1])
            if code <= 0:
                sys.exit(f"s5a: no net {a[1]}")
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
    with open(os.path.join(os.path.dirname(path), "s5a.json"), "w") as f:
        json.dump(dict(deleted=DELETED, added=ADDED, moves=MOVES, warn=WARN), f)


def main(argv):
    if os.path.exists(LOCK):
        sys.exit("s5a: the board is open in KiCad; close it first")
    names = argv[argv.index("--group") + 1].split(",")
    files = (("deleted_s5a.json", "deleted"), ("s5a_added.json", "added"), ("moves_s5a.json", "moves"))
    prev = {"deleted": [], "added": [], "moves": [], "groups": []}
    if os.path.exists(os.path.join(RT, "s5a_added.json")):
        for name, key in files:
            with open(os.path.join(RT, name)) as f:
                d = json.load(f)
            prev[key] = d[key]
            prev["groups"] = d.get("groups", prev["groups"])
    dry = "--dry-run" in argv
    if not dry and any(g in prev["groups"] for g in names):
        sys.exit("s5a: group already on the board (not re-runnable)")
    src = BOARD
    if "--from" in argv:                               # dry run on top of an earlier dry run
        src = os.path.abspath(argv[argv.index("--from") + 1])
    tmp = tempfile.mkdtemp(prefix=".s5a_", dir=ROOT)
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
            sys.exit("s5a: edit failed, the board is unchanged")
        r = subprocess.run([CLI, "pcb", "drc", "--format", "json", "--refill-zones", "--save-board",
                            "-o", os.path.join(tmp, "refill.json"), pcb], capture_output=True, text=True)
        if r.returncode:
            sys.exit("s5a: zone refill failed, the board is unchanged\n" + r.stdout[-1500:] + r.stderr[-1500:])
        with open(os.path.join(tmp, "s5a.json")) as f:
            j = json.load(f)
        for w in j["warn"]:
            print("s5a: WARNING " + w)
        print(f"s5a: {names}: deleted {len(j['deleted'])}, added {len(j['added'])}, moved {len(j['moves'])}")
        if dry:
            out = os.path.abspath(argv[argv.index("--dry-run") + 1])
            shutil.copy(pcb, out)
            print(f"s5a: dry run in {out}, the board is unchanged")
            return 0
        shutil.copy(pcb, BOARD)
        note = "routing stage 5a (2026-11-22), tools/next/route_s5a_signals.py - incremental edit of the board, not a rebuild"
        for name, key in files:
            with open(os.path.join(RT, name), "w") as f:
                json.dump({"note": note, "groups": prev["groups"] + names, key: prev[key] + j[key]}, f, indent=1)
        print("s5a: wrote the board and routing/*_s5a.json")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    if "--edit" in sys.argv:
        i = sys.argv.index("--edit")
        edit(sys.argv[i + 1], sys.argv[i + 2].split(","))
        sys.exit(0)
    sys.exit(main(sys.argv[1:]))
