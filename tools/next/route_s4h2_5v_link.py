#!/usr/bin/env python3
"""Routing stage 4h2 of tube_power 5.2 (2026-11-22): 5V link on B.Cu under DRV5 moved away from the pads of C11.

    tools/p2k/bin/kipy tools/next/route_s4h2_5v_link.py [--dry-run OUT.kicad_pcb]

Incremental edit of the board of stage 4h (HEAD 2f4424a), same conventions as route_s4h_drv5_low.py; NOT
re-runnable on its own result (refuses when routing/s4h2_added.json exists). The rebuild scripts stay frozen.
The names s4i (script, routing/*_s4i.json) are left free for the driver-input block, which is not on the board:
see README "Stage 4i".
Writes kicad_next/routing/moves_s4h2.json, deleted_s4h2.json, s4h2_added.json. Zones are refilled by kicad-cli.
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
F, B, I2 = "F", "B", "2"
nm = lambda v: int(round(v * 1e6))  # noqa: E731
mm = lambda v: round(v / 1e6, 4)  # noqa: E731
DELETED, ADDED, MOVES, WARN = [], [], [], []
#TB0
V5 = "5V"
W5 = "5V link on B.Cu south of pin 9 of DRV5: 0.35 mm from the pads of C11 (U1A- node), re-drawn 0.15 mm further north"
DELNETS = {}
DEL = [
    (V5, B, 9.0, -54.6, 9.0, -55.15, W5), (V5, B, 9.0, -55.15, 5.6, -55.15, W5), (V5, B, 5.6, -55.15, 5.2, -54.75, W5),
]
DELVIA = []
MOVE = []
ADD = [
    # via (9.0, -54.6) -> south -> west under the body -> the kept track x 5.2: edge 0.52 mm from the pads of C11,
    # 0.21 mm from pin 9 (GND) of DRV5
    ("t", V5, B, 0.25, [(9.0, -54.6), (9.0, -54.98), (5.43, -54.98), (5.2, -54.75)]),
]
ZONE = {}
DELZONE = []
NEWZONE = []
#TB1


def edit(path):
    b = pcbnew.LoadBoard(path)
    lid = {b.GetLayerName(l): l for l in b.GetEnabledLayers().CuStack()}
    near = lambda p, x, y: abs(p[0] - x) <= 0.005 and abs(p[1] - y) <= 0.005  # noqa: E731
    tracks = []
    for t in b.GetTracks():
        via = t.Type() == pcbnew.PCB_VIA_T
        s, e = t.GetStart(), t.GetEnd()
        tracks.append([t, via, t.GetNetname(), None if via else t.GetLayer(), (s.x / 1e6, s.y / 1e6), (e.x / 1e6, e.y / 1e6),
                       0 if via else t.GetWidth() / 1e6])
    for net, lay, x0, y0, x1, y1, why in DEL:
        hit = [r for r in tracks if not r[1] and r[2] == net and r[3] == lid[LAYER[lay]]
               and ((near(r[4], x0, y0) and near(r[5], x1, y1)) or (near(r[4], x1, y1) and near(r[5], x0, y0)))]
        if not hit:
            WARN.append(f"delete: no segment {net} {lay} ({x0}, {y0}) - ({x1}, {y1})")
        for r in hit:
            DELETED.append(dict(kind="segment", net=net, layer=LAYER[lay], start=[round(v, 4) for v in r[4]],
                                end=[round(v, 4) for v in r[5]], width=round(r[6], 4), why=why))
            b.Delete(r[0])
            tracks.remove(r)
    for r in list(tracks):
        if r[2] in DELNETS:
            if r[1]:
                DELETED.append(dict(kind="via", net=r[2], at=[round(v, 4) for v in r[4]], why=DELNETS[r[2]]))
            else:
                DELETED.append(dict(kind="segment", net=r[2], layer=b.GetLayerName(r[3]), start=[round(v, 4) for v in r[4]],
                                    end=[round(v, 4) for v in r[5]], width=round(r[6], 4), why=DELNETS[r[2]]))
            b.Delete(r[0])
            tracks.remove(r)
    for net, x, y, why in DELVIA:
        hit = [r for r in tracks if r[1] and r[2] == net and near(r[4], x, y)]
        if not hit:
            WARN.append(f"delvia: no via {net} ({x}, {y})")
        for r in hit:
            DELETED.append(dict(kind="via", net=net, at=[x, y], why=why))
            b.Delete(r[0])
            tracks.remove(r)
    for ref, x, y, rot, to_side, why in MOVE:
        fp = b.FindFootprintByReference(ref)
        p = fp.GetPosition()
        side = "B" if fp.IsFlipped() else "F"
        MOVES.append(dict(ref=ref, frm=dict(x=mm(p.x), y=mm(p.y), rot=fp.GetOrientationDegrees(), side=side),
                          to=dict(x=x, y=y, rot=rot, side=to_side), why=why))
        if side != to_side:
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fp.SetPosition(pcbnew.VECTOR2I(nm(x), nm(y)))
        fp.SetOrientationDegrees(rot)
        if side != to_side:                      # texts of a part flipped to the front must not stay mirrored
            for it in list(fp.GetFields()) + [g for g in fp.GraphicalItems() if g.Type() == pcbnew.PCB_TEXT_T]:
                it.SetMirrored(to_side == "B")
        for pad in fp.Pads():
            q = pad.GetPosition()
            print(f"s4h2: {ref} pad {pad.GetNumber()} {pad.GetNetname()} at ({mm(q.x)}, {mm(q.y)})")
    pcbnew.SaveBoard(path, b)
    b = pcbnew.LoadBoard(path)
    lid = {b.GetLayerName(l): l for l in b.GetEnabledLayers().CuStack()}
    for a in ADD:
        code = b.GetNetcodeFromNetname(a[1])
        if code <= 0:
            sys.exit(f"s4h2: no net {a[1]}")
        if a[0] == "v":
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(pcbnew.VECTOR2I(nm(a[2]), nm(a[3])))
            v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            v.SetWidth(pcbnew.F_Cu, nm(a[4]))
            v.SetDrill(nm(a[5]))
            v.SetNetCode(code)
            b.Add(v)
            ADDED.append(dict(kind="via", net=a[1], at=[a[2], a[3]], size=[a[4], a[5]]))
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
                ADDED.append(dict(kind="segment", net=n, layer=LAYER[lay], start=list(p), end=list(q), width=w))

    def outline(z, pts):
        ol = z.Outline()
        ol.RemoveAllContours()
        ol.NewOutline()
        for x, y in pts:
            ol.Append(nm(x), nm(y))

    byname = {z.GetZoneName(): z for z in b.Zones()}
    for name, layer, why in DELZONE:
        hit = [z for z in b.Zones() if z.GetZoneName() == name and b.GetLayerName(z.GetLayer()) == layer]
        if len(hit) != 1:
            WARN.append(f"delzone: {len(hit)} zones {name} on {layer}")
        for z in hit:
            o = z.Outline().Outline(0)
            DELETED.append(dict(kind="zone", zone=name, net=z.GetNetname(), layer=layer, why=why,
                                outline=[[mm(o.CPoint(k).x), mm(o.CPoint(k).y)] for k in range(o.PointCount())]))
            b.Delete(z)
    for name, net, like, pts in NEWZONE:           # (before the outline of `like` is changed: only settings are read)
        src = byname[like]
        z = pcbnew.ZONE(b)
        z.SetLayer(pcbnew.F_Cu)
        z.SetNetCode(b.GetNetcodeFromNetname(net))
        z.SetZoneName(name)
        z.SetAssignedPriority(src.GetAssignedPriority())
        z.SetLocalClearance(src.GetLocalClearance())
        z.SetMinThickness(src.GetMinThickness())
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)     # solid, as the 5.1 power pours (pour 29)
        z.SetIslandRemovalMode(src.GetIslandRemovalMode())
        outline(z, pts)
        b.Add(z)
        ADDED.append(dict(kind="zone", zone=name, net=net, layer="F.Cu", outline=pts))
    for name, (pts, why) in ZONE.items():
        z = byname[name]
        o = z.Outline().Outline(0)
        DELETED.append(dict(kind="zone outline", zone=name, net=z.GetNetname(), why=why, new=pts,
                            old=[[mm(o.CPoint(k).x), mm(o.CPoint(k).y)] for k in range(o.PointCount())]))
        outline(z, pts)
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)     # one thermal spoke only reached the TO-220 pads
    for z in b.Zones():
        if not z.GetIsRuleArea():
            z.UnFill()
    pcbnew.SaveBoard(path, b)
    with open(os.path.join(os.path.dirname(path), "s4h2.json"), "w") as f:
        json.dump(dict(deleted=DELETED, added=ADDED, moves=MOVES, warn=WARN), f)


def main(argv):
    if os.path.exists(LOCK):
        sys.exit("s4h2: the board is open in KiCad; close it first")
    if os.path.exists(os.path.join(RT, "s4h2_added.json")) and "--dry-run" not in argv:
        sys.exit("s4h2: routing/s4h2_added.json exists - this block is on the board already (not re-runnable)")
    tmp = tempfile.mkdtemp(prefix=".s4h2_", dir=ROOT)
    try:
        for ext in (".kicad_pcb", ".kicad_dru"):
            shutil.copy(os.path.join(PROJ, NAME + ext), tmp)
        with open(os.path.join(PROJ, NAME + ".kicad_pro")) as f:
            pro = json.load(f)
        rs = pro["board"]["design_settings"]["rule_severities"]
        for k in rs:
            rs[k] = "ignore"                       # refill only
        with open(os.path.join(tmp, NAME + ".kicad_pro"), "w") as f:
            json.dump(pro, f, indent=2)
        pcb = os.path.join(tmp, NAME + ".kicad_pcb")
        r = subprocess.run([sys.executable, "-u", os.path.abspath(__file__), "--edit", pcb])
        if r.returncode:
            sys.exit("s4h2: edit failed, the board is unchanged")
        r = subprocess.run([CLI, "pcb", "drc", "--format", "json", "--refill-zones", "--save-board",
                            "-o", os.path.join(tmp, "refill.json"), pcb], capture_output=True, text=True)
        if r.returncode:
            sys.exit("s4h2: zone refill failed, the board is unchanged\n" + r.stdout[-1500:] + r.stderr[-1500:])
        with open(os.path.join(tmp, "s4h2.json")) as f:
            j = json.load(f)
        for w in j["warn"]:
            print("s4h2: WARNING " + w)
        print(f"s4h2: deleted {len(j['deleted'])}, added {len(j['added'])}, moved {len(j['moves'])}")
        if "--dry-run" in argv:
            out = os.path.abspath(argv[argv.index("--dry-run") + 1])
            shutil.copy(pcb, out)
            print(f"s4h2: dry run in {out}, the board is unchanged")
            return 0
        shutil.copy(pcb, BOARD)
        note = "routing stage 4h2 (2026-11-22), tools/next/route_s4h2_5v_link.py - incremental edit of the board, not a rebuild"
        for name, key in (("deleted_s4h2.json", "deleted"), ("s4h2_added.json", "added"), ("moves_s4h2.json", "moves")):
            with open(os.path.join(RT, name), "w") as f:
                json.dump({"note": note, key: j[key]}, f, indent=1)
        print("s4h2: wrote the board and routing/*_s4h2.json")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    if "--edit" in sys.argv:
        edit(sys.argv[sys.argv.index("--edit") + 1])
        sys.exit(0)
    sys.exit(main(sys.argv[1:]))
