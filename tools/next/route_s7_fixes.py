#!/usr/bin/env python3
"""Stage 7 (2026-11-22): fixes after the verification of the first complete draft of tube_power 5.2 (see README
"Stage 7: fixes after the draft verification").

    tools/p2k/bin/kipy tools/next/route_s7_fixes.py --group NAME[,NAME...] [--dry-run OUT.kicad_pcb] [--from PCB]

Incremental edit, same conventions as route_s6_cleanup.py; NOT re-runnable (a group that is listed in
routing/s7_added.json is refused). The rebuild scripts stay frozen. Appends to kicad_next/routing/moves_s7.json,
deleted_s7.json, s7_added.json. Zones are refilled by kicad-cli.

Entries: ADD ("t", net, layer key, width, [points]) / ("v", net, x, y, pad, drill) / ("z", net, layer key, name,
model zone name, [outline points]); DEL (net, layer key, x0, y0, x1, y1, why); DELVIA (net, x, y, why);
MOVE (ref, x, y, rot, side, why).
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

GROUPS = {
    # 1: the 420V 1210 capacitors (change 5.6: 1206 -> 1210 at the 5.1 pitch of 2.0 / 1.9 mm, bodies overlapped 0.5 / 0.6 mm)
    "caps": dict(MOVE=[
        ("C90", 74.7, -75.425, -90.0, "F", "1210 body 2.5 mm: pitch 2.0 -> 2.9 mm to C91 (body gap 0.4 mm)"),
        ("C91", 77.6, -75.425, -90.0, "F", "1210 body 2.5 mm: pitch 2.0 -> 2.9 mm to C90 (body gap 0.4 mm)"),
        ("C99", 78.3, -75.425, -90.0, "B", "1210 body 2.5 mm: pitch 2.0 -> 2.9 mm to C100 (body gap 0.4 mm)"),
        ("C101", 72.5, -75.425, -90.0, "B", "1210 body 2.5 mm: pitch 1.9 -> 2.9 mm to C100 (body gap 0.4 mm)"),
    ], ADD=[
        # C101 now reaches 1.1 mm west of the B.Cu pours: two patches so that both pads stay fully on pour copper
        ("z", "ISO_GND", B, "S7_ISO_GND_B_C101", "Proteus B.Cu pour 12", [(71.0, -74.657), (73.2, -74.657), (73.2, -73.3), (71.0, -73.3)]),
        ("z", "420V", B, "S7_420V_B_C101", "Proteus B.Cu pour 25", [(71.0, -77.6), (72.8, -77.6), (72.8, -76.076), (71.0, -76.076)]),
    ]),
    # 4: shunt R83 pad 2 -> GND planes: three vias 0.6 / 0.3 on a 1 mm bar (was 0.35 mm track, one via 0.5 / 0.3 and
    # two 0.6 / 0.3 joined by a 0.02 mm overlap). South edge y -65.23 = the via rings (UART island keep-out -65.255).
    "r83": dict(DELVIA=[
        ("GND", 17.96, -64.55, "0.5 / 0.3 via replaced by 0.6 / 0.3"),
    ], ADD=[
        ("v", "GND", 17.96, -64.55, 0.6, 0.3),
        ("t", "GND", F, 1.0, [(15.4, -64.73), (18.55, -64.73)]),
    ]),
    # 5: PRI-SEC creepage ISO2 pad 8 (GND) -> Net-(TR1-S15) round the north end of the ISO2 slot was 11.2 mm for 11.1:
    # the south end of the x 71.9 run leaves diagonally to the D4 anode pad from y -15.9 (a plain 0.3 mm shift east
    # is not free: 15V_ISO_SEC pad at x 72.5 ... 74.3, y -15.0 ... -13.8).
    "iso2": dict(DEL=[
        ("Net-(TR1-S15)", F, 71.9, -11.6, 71.9, -17.2, "corner (71.9, -17.2) was the nearest secondary copper to ISO2 pad 8"),
        ("Net-(TR1-S15)", F, 71.9, -17.2, 73.6, -18.9, "same"),
        ("Net-(TR1-S15)", F, 73.6, -18.9, 74.75, -19.2, "same"),
    ], ADD=[
        ("t", "Net-(TR1-S15)", F, 0.5, [(71.9, -11.6), (71.9, -15.9), (74.2, -18.2), (74.75, -19.2)]),
    ]),
    # 2 / 3 (DC+ feed of C47, C95): not done in this stage, see README "Stage 7".
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
                sys.exit("s7: no side changes in this stage")
            MOVES.append(dict(group=g, ref=ref, frm=dict(x=mm(p.x), y=mm(p.y), rot=fp.GetOrientationDegrees(), side=side),
                              to=dict(x=x, y=y, rot=rot, side=to_side), why=why))
            fp.SetPosition(pcbnew.VECTOR2I(nm(x), nm(y)))
            fp.SetOrientationDegrees(rot)
            for pad in fp.Pads():
                q = pad.GetPosition()
                print(f"s7: {ref} pad {pad.GetNumber()} {pad.GetNetname()} at ({mm(q.x)}, {mm(q.y)})")
        for a in G.get("ADD", []):
            code = b.GetNetcodeFromNetname(a[1])
            if code <= 0:
                sys.exit(f"s7: no net {a[1]}")
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
            elif a[0] == "z":                          # small zone, settings copied from a zone of the same net
                _, n, lay, name, model, pts = a
                m = [z for z in b.Zones() if z.GetZoneName() == model and z.GetNetname() == n]
                if len(m) != 1:
                    sys.exit(f"s7: model zone {model} [{n}] not found")
                z = pcbnew.ZONE(b)
                z.SetLayer(lid[LAYER[lay]])
                z.SetNetCode(code)
                z.SetZoneName(name)
                used = {q.GetAssignedPriority() for q in b.Zones() if not q.GetIsRuleArea()}
                z.SetAssignedPriority(min(k for k in range(m[0].GetAssignedPriority() + 1, 1000) if k not in used))
                z.SetLocalClearance(m[0].GetLocalClearance())
                z.SetMinThickness(m[0].GetMinThickness())
                z.SetPadConnection(m[0].GetPadConnection())
                z.SetThermalReliefGap(m[0].GetThermalReliefGap())
                z.SetThermalReliefSpokeWidth(m[0].GetThermalReliefSpokeWidth())
                z.SetIslandRemovalMode(m[0].GetIslandRemovalMode())
                o = z.Outline()
                o.NewOutline()
                for p in pts:
                    o.Append(nm(p[0]), nm(p[1]))
                b.Add(z)
                ADDED.append(dict(group=g, kind="zone", net=n, layer=LAYER[lay], name=name, settings_from=model,
                                  outline=[list(p) for p in pts]))
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
    with open(os.path.join(os.path.dirname(path), "s7.json"), "w") as f:
        json.dump(dict(deleted=DELETED, added=ADDED, moves=MOVES, warn=WARN), f)


def main(argv):
    if os.path.exists(LOCK):
        sys.exit("s7: the board is open in KiCad; close it first")
    names = argv[argv.index("--group") + 1].split(",")
    files = (("deleted_s7.json", "deleted"), ("s7_added.json", "added"), ("moves_s7.json", "moves"))
    prev = {"deleted": [], "added": [], "moves": [], "groups": []}
    if os.path.exists(os.path.join(RT, "s7_added.json")):
        for name, key in files:
            with open(os.path.join(RT, name)) as f:
                d = json.load(f)
            prev[key] = d[key]
            prev["groups"] = d.get("groups", prev["groups"])
    dry = "--dry-run" in argv
    if not dry and any(g in prev["groups"] for g in names):
        sys.exit("s7: group already on the board (not re-runnable)")
    src = BOARD
    if "--from" in argv:                               # dry run on top of an earlier dry run
        src = os.path.abspath(argv[argv.index("--from") + 1])
    tmp = tempfile.mkdtemp(prefix=".s7_", dir=ROOT)
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
            sys.exit("s7: edit failed, the board is unchanged")
        r = subprocess.run([CLI, "pcb", "drc", "--format", "json", "--refill-zones", "--save-board",
                            "-o", os.path.join(tmp, "refill.json"), pcb], capture_output=True, text=True)
        if r.returncode:
            sys.exit("s7: zone refill failed, the board is unchanged\n" + r.stdout[-1500:] + r.stderr[-1500:])
        with open(os.path.join(tmp, "s7.json")) as f:
            j = json.load(f)
        for w in j["warn"]:
            print("s7: WARNING " + w)
        print(f"s7: {names}: deleted {len(j['deleted'])}, added {len(j['added'])}, moved {len(j['moves'])}")
        if dry:
            out = os.path.abspath(argv[argv.index("--dry-run") + 1])
            shutil.copy(pcb, out)
            print(f"s7: dry run in {out}, the board is unchanged")
            return 0
        shutil.copy(pcb, BOARD)
        note = "routing stage 7 (2026-11-22), tools/next/route_s7_fixes.py - incremental edit of the board, not a rebuild"
        for name, key in files:
            with open(os.path.join(RT, name), "w") as f:
                json.dump({"note": note, "groups": prev["groups"] + names, key: prev[key] + j[key]}, f, indent=1)
        print("s7: wrote the board and routing/*_s7.json")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    if "--edit" in sys.argv:
        i = sys.argv.index("--edit")
        edit(sys.argv[i + 1], sys.argv[i + 2].split(","))
        sys.exit(0)
    sys.exit(main(sys.argv[1:]))
