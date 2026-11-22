#!/usr/bin/env python3
"""Stage 8 (2026-11-22): C95 becomes an 0603 beside DRV5 pins 11 / 9 (user-approved footprint / BOM change), and DC+
gets a second way into the drain pin of Q19 on In3 (see README "Stage 8").

    tools/p2k/bin/kipy tools/next/route_s8_c95_dc.py --group NAME[,NAME...] [--dry-run OUT.kicad_pcb] [--from PCB]

Incremental edit, same conventions and code as route_s8_c95_dc.py; NOT re-runnable (a group that is listed in
routing/s8_added.json is refused). Appends to kicad_next/routing/moves_s8.json, deleted_s8.json, s8_added.json.
Zones are refilled by kicad-cli.

Entries: ADD ("t", net, layer key, width, [points]) / ("v", net, x, y, pad, drill) / ("z", ...); DEL (net, layer key,
x0, y0, x1, y1, why); DELVIA (net, x, y, why); MOVE (ref, x, y, rot, side, why); REPLACE (ref, footprint id, x, y,
rot, side, why): the footprint is replaced by the library footprint of the new id (the schematic must already name
it) at the new place; reference, value, symbol path, sheet, fields and the pad nets (by pad number) are kept.
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

sys.path.insert(0, HERE)

C95 = (8.66, -53.72)        # 0603 standing north-south 0.21 mm east of the DRV5 pin pads; 15V pad north, GND pad south
GAP_Y = C95[1]              # the gate track of pin 10 runs between the two pads (pad gap 0.65 mm, track 0.2 mm)

GROUPS = {
    # 1: C95 1206 at (18.9, -60.6) -> 0603 at DRV5 pins 11 / 9 on B.Cu. 15V pad (2) north, 1.2 mm of 0.5 mm track from
    # the pad of pin 11 (15V copper has to stay x <= 8.8 beside the high-side return on x 10.25: its NE corner is
    # 1.24 mm from that track); GND pad (1) south beside pin 9 on the GND via (8.25, -54.345). In the way: the gate
    # track of pin 10 (now 0.2 mm between the pads of C95), the 5V via (9.0, -54.6) and its B.Cu track on y -54.98
    # (via 0.68 mm east, track round the south of the GND pad), R90 (0.35 mm east for that track).
    "c95": dict(DELVIA=[
        ("5V", 9.0, -54.6, "under the GND pad of the new C95; moved to (9.68, -54.45)"),
    ], DEL=[
        ("5V", B, 9.0, -54.6, 9.0, -54.98, "to the moved via"),
        ("5V", B, 9.0, -54.98, 5.43, -54.98, "re-drawn round the GND pad of C95"),
        ("5V", I2, 9.4, -54.2, 9.0, -54.6, "to the moved via"),
        ("5V", I2, 14.718, -54.2, 9.4, -54.2, "re-drawn to the moved via"),
        ("DHB_LOW_GATE", B, 6.95, -53.075, 8.6, -53.075, "gate track re-drawn between the pads of C95"),
        ("DHB_LOW_GATE", B, 8.6, -53.075, 9.75, -54.1, "same"),
        ("DHB_LOW_GATE", B, 9.75, -54.1, 10.25, -54.6, "same"),
        ("DHB_LOW_GATE", B, 10.25, -54.6, 10.25, -55.6, "same"),
        ("DHB_LOW_GATE", B, 10.25, -55.6, 10.95, -54.9, "R90 moved"),
        ("DHB_LOW_GATE", B, 10.95, -54.9, 11.45, -54.9, "R90 moved"),
    ], REPLACE=[
        ("C95", "Capacitor_SMD:C_0603_1608Metric", C95[0], C95[1], -90.0, "B",
         "0603 at DRV5 pins 11 / 9 (no 1206 place within reach)"),
    ], MOVE=[
        ("R90", 10.6, -56.6, 90.0, "B", "0.35 mm east: room for the 5V track on x 9.5 between C95 and R90 pad 1"),
    ], ADD=[
        ("t", "15V", B, 0.5, [(6.95, -51.805), (8.5, -51.805), (8.5, -52.9)]),
        ("t", "GND", B, 0.4, [(8.25, -54.345), (8.66, -54.495)]),
        ("t", "DHB_LOW_GATE", B, 0.2, [(7.3, -53.075), (7.945, GAP_Y), (9.5, GAP_Y)]),
        ("t", "DHB_LOW_GATE", B, 0.3, [(9.5, GAP_Y), (10.0, GAP_Y), (10.6, -54.32), (10.6, -55.6), (11.45, -54.9)]),
        ("v", "5V", 9.68, -54.45, 0.6, 0.3),
        ("t", "5V", I2, 0.305, [(14.718, -54.2), (9.93, -54.2), (9.68, -54.45)]),
        ("t", "5V", B, 0.25, [(9.68, -54.45), (9.5, -54.63), (9.5, -55.085), (9.3, -55.285), (7.905, -55.285),
                              (7.6, -54.98), (5.43, -54.98)]),
    ]),
    # 2: what was left at the old place of C95 (the pads went with the footprint)
    "old": dict(DELVIA=[
        ("15V", 18.9, -58.85, "via in the 15V pad of C95 at its old place"),
        ("GND", 18.9, -61.7, "GND via of C95 at its old place"),
    ], DEL=[
        ("15V", I3, 17.125, -55.25, 18.9, -57.025, "In3 spur to the old C95"),
        ("15V", I3, 18.9, -57.025, 18.9, -58.85, "same"),
    ]),
    # 3: DC+ into Q19 pin 2 on In3 (0.5 mm HV spacing on an inner layer instead of 1.2 mm): 1.8 mm from the pin east
    # to the three existing DC+ vias (17.7 / 18.7, -50.0), (18.3, -48.5) of the F.Cu pour / B.Cu run.
    "dc": dict(ADD=[
        ("t", "DC+", I3, 1.8, [(12.75, -49.52), (18.7, -49.52)]),
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
        for ref, fpid, x, y, rot, to_side, why in G.get("REPLACE", []):
            import reuse_51_board as R
            fp = b.FindFootprintByReference(ref)
            p = fp.GetPosition()
            side = "B" if fp.IsFlipped() else "F"
            if side != to_side:
                sys.exit("s8: no side changes in this stage")
            new = R.load_fp(fpid)
            b.Add(new)                                   # on the board before Flip (pcbnew 10)
            pos = pcbnew.VECTOR2I(nm(x), nm(y))
            new.SetPosition(pos)
            if to_side == "B":
                new.Flip(pos, pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
            new.SetOrientationDegrees(rot)
            new.SetReference(ref)
            new.SetValue(fp.GetValue())
            new.SetPath(fp.GetPath())
            new.SetLocked(fp.IsLocked())
            if hasattr(new, "SetSheetname"):
                new.SetSheetname(fp.GetSheetname())
                new.SetSheetfile(fp.GetSheetfile())
            for f in fp.GetFields():
                name = f.GetName()
                if name not in ("Reference", "Value", "Footprint"):
                    new.SetField(name, f.GetText())
                    if not f.IsVisible():
                        new.GetField(name).SetVisible(False)
            nets = {q.GetNumber(): q.GetNet() for q in fp.Pads()}
            MOVES.append(dict(group=g, ref=ref, footprint=dict(frm=fp.GetFPIDAsString(), to=fpid),
                              frm=dict(x=mm(p.x), y=mm(p.y), rot=fp.GetOrientationDegrees(), side=side),
                              to=dict(x=x, y=y, rot=rot, side=to_side), why=why))
            for pad in new.Pads():
                pad.SetNet(nets[pad.GetNumber()])
                q = pad.GetPosition()
                print(f"s8: {ref} pad {pad.GetNumber()} {pad.GetNetname()} at ({mm(q.x)}, {mm(q.y)})")
            b.Delete(fp)
        for ref, x, y, rot, to_side, why in G.get("MOVE", []):
            fp = b.FindFootprintByReference(ref)
            p = fp.GetPosition()
            side = "B" if fp.IsFlipped() else "F"
            if side != to_side:
                sys.exit("s8: no side changes in this stage")
            MOVES.append(dict(group=g, ref=ref, frm=dict(x=mm(p.x), y=mm(p.y), rot=fp.GetOrientationDegrees(), side=side),
                              to=dict(x=x, y=y, rot=rot, side=to_side), why=why))
            fp.SetPosition(pcbnew.VECTOR2I(nm(x), nm(y)))
            fp.SetOrientationDegrees(rot)
            for pad in fp.Pads():
                q = pad.GetPosition()
                print(f"s8: {ref} pad {pad.GetNumber()} {pad.GetNetname()} at ({mm(q.x)}, {mm(q.y)})")
        for a in G.get("ADD", []):
            code = b.GetNetcodeFromNetname(a[1])
            if code <= 0:
                sys.exit(f"s8: no net {a[1]}")
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
                    sys.exit(f"s8: model zone {model} [{n}] not found")
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
    with open(os.path.join(os.path.dirname(path), "s8.json"), "w") as f:
        json.dump(dict(deleted=DELETED, added=ADDED, moves=MOVES, warn=WARN), f)


def main(argv):
    if os.path.exists(LOCK):
        sys.exit("s8: the board is open in KiCad; close it first")
    names = argv[argv.index("--group") + 1].split(",")
    files = (("deleted_s8.json", "deleted"), ("s8_added.json", "added"), ("moves_s8.json", "moves"))
    prev = {"deleted": [], "added": [], "moves": [], "groups": []}
    if os.path.exists(os.path.join(RT, "s8_added.json")):
        for name, key in files:
            with open(os.path.join(RT, name)) as f:
                d = json.load(f)
            prev[key] = d[key]
            prev["groups"] = d.get("groups", prev["groups"])
    dry = "--dry-run" in argv
    if not dry and any(g in prev["groups"] for g in names):
        sys.exit("s8: group already on the board (not re-runnable)")
    src = BOARD
    if "--from" in argv:                               # dry run on top of an earlier dry run
        src = os.path.abspath(argv[argv.index("--from") + 1])
    tmp = tempfile.mkdtemp(prefix=".s8_", dir=ROOT)
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
            sys.exit("s8: edit failed, the board is unchanged")
        r = subprocess.run([CLI, "pcb", "drc", "--format", "json", "--refill-zones", "--save-board",
                            "-o", os.path.join(tmp, "refill.json"), pcb], capture_output=True, text=True)
        if r.returncode:
            sys.exit("s8: zone refill failed, the board is unchanged\n" + r.stdout[-1500:] + r.stderr[-1500:])
        with open(os.path.join(tmp, "s8.json")) as f:
            j = json.load(f)
        for w in j["warn"]:
            print("s8: WARNING " + w)
        print(f"s8: {names}: deleted {len(j['deleted'])}, added {len(j['added'])}, moved {len(j['moves'])}")
        if dry:
            out = os.path.abspath(argv[argv.index("--dry-run") + 1])
            shutil.copy(pcb, out)
            print(f"s8: dry run in {out}, the board is unchanged")
            return 0
        shutil.copy(pcb, BOARD)
        note = "routing stage 8 (2026-11-22), tools/next/route_s8_c95_dc.py - incremental edit of the board, not a rebuild"
        for name, key in files:
            with open(os.path.join(RT, name), "w") as f:
                json.dump({"note": note, "groups": prev["groups"] + names, key: prev[key] + j[key]}, f, indent=1)
        print("s8: wrote the board and routing/*_s8.json")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    if "--edit" in sys.argv:
        i = sys.argv.index("--edit")
        edit(sys.argv[i + 1], sys.argv[i + 2].split(","))
        sys.exit(0)
    sys.exit(main(sys.argv[1:]))
