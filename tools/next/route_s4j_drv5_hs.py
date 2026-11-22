#!/usr/bin/env python3
"""Routing stage 4j of tube_power 5.2 (2026-11-22): rest of the high side of DRV5 - R22 at the Q19 gate / source pads,
bootstrap charge path D19 / R41 / C96 on B.Cu north-east of the FET column.

    tools/p2k/bin/kipy tools/next/route_s4j_drv5_hs.py [--dry-run OUT.kicad_pcb]

Incremental edit of the board of stage 4i (HEAD 09c2f5a), same conventions as route_s4i_drv5_in.py; NOT
re-runnable on its own result (refuses when routing/s4j_added.json exists). The rebuild scripts stay frozen.
See README "Stage 4j" for what is on the board and what is still open.
Writes kicad_next/routing/moves_s4j.json, deleted_s4j.json, s4j_added.json. Zones are refilled by kicad-cli.
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
V15, GND = "15V", "GND"
QG, SRC, VDDA, DK = "Net-(Q19-G)", "DHB_HI_SOURCE", "Net-(DRV5-VDDA)", "Net-(D19-K)"
WE = "old place of the part (moved to the high side of DRV5 / Q19)"
DELNETS = {}
DEL = [
    (QG, B, 41.229, -44.152, 41.534, -44.457, WE), (QG, B, 41.534, -44.457, 41.534, -45.708, WE),
    (DK, B, 19.65, -61.0, 20.137, -62.9, WE),
    (V15, B, 15.3, -63.3, 15.3, -61.4, WE), (V15, B, 16.6, -59.625, 16.2, -60.4, WE),
    (V15, B, 17.625, -51.0, 17.625, -58.6, WE), (V15, B, 17.625, -58.6, 16.6, -59.625, WE),
    (GND, B, 22.5, -46.5, 22.5, -44.3, "GND of C95 pin 1 into the B.Cu pour: 1.05 mm from the cathode pad of D19 (C95 keeps its GND via (23.637, -47.2))"),
]
DELVIA = []
# ref, x, y, rot, side ("F" / "B": flipped when it differs), why
MOVE = [
    ("R22", 15.5, -48.6, 90, "B", "gate-source resistor of Q19 east of the pin column, between the gate pad and the source pad"),
    ("R41", 18.0, -42.15, 180, "B", "bootstrap charge resistor, VDDA end towards C92"),
    ("D19", 23.4, -42.15, 0, "B", "bootstrap diode beside R41, anode on the 15V of C95 (via (25.562, -48.6) into In3)"),
    ("C96", 28.0, -42.6, 90, "B", "15V capacitor at the anode of D19"),
]
ADD = [
    ("t", QG, B, 0.3, [(12.75, -46.98), (15.5, -46.98), (15.5, -47.775)]),
    ("t", SRC, B, 0.3, [(15.5, -49.425), (15.5, -52.06), (12.75, -52.06)]),
    ("t", VDDA, B, 0.3, [(9.15, -44.95), (9.6, -44.5), (9.6, -44.2), (11.65, -42.15), (16.5375, -42.15)]),
    ("t", DK, B, 0.5, [(19.4625, -42.15), (21.35, -42.15)]),
    ("t", V15, B, 0.4, [(24.7, -42.15), (24.7, -45.6), (25.562, -46.462), (25.562, -47.2)]),
    ("t", V15, B, 0.4, [(25.45, -42.15), (26.56, -41.0375), (28.0, -41.0375)]),
]
RULEAREA = []
ZONE = {}
DELZONE = [("Proteus B.Cu pour 19", "B.Cu", "local 15V pour of the old place of D19 / C96 (x 13.6 - 17.6, y -63.2 ... -58.0): isolated once its feed track is gone")]
NEWZONE = []
#TB1
# Part 2 (--part2, run once after part 1 is on the board): C95 and C70 to the bridge, wider In3 15V link, leftovers.
PART2 = "--part2" in sys.argv
if PART2:
    DCP, CUR = "DC+", "DHB_CURRENT"
    WC = "old place of C95 (moved to the 15V via (17.625, -51.0))"
    DEL = [(GND, B, 22.438, -47.2, 23.637, -47.2, WC), (V15, B, 25.562, -47.2, 25.55, -47.25, WC)]
    DELVIA = [(GND, 23.637, -47.2, WC)]
    DELZONE = []
    MOVE = [
        ("C95", 19.2, -51.6, 180, "B", "15V decoupling of DRV5: 15V pad on the via (17.625, -51.0) of the In3 15V bridge, GND via (20.4, -50.65)"),
        ("C70", 19.7, -48.0, 0, "B", "second bridge capacitor under C67 (F.Cu), DC+ via in the pads, DHB_CURRENT on the kept via (22.6, -49.0)"),
    ]
    ADD = [
        ("t", V15, "3", 1.0, [(27.4, -44.3), (28.5, -44.3), (28.5, -46.9), (27.4, -46.9)]),
        ("t", V15, B, 0.5, [(17.625, -51.0), (17.6375, -51.6)]),
        ("v", GND, 20.4, -50.65, 0.5, 0.3),
        ("t", GND, B, 0.5, [(20.7625, -51.6), (20.4, -50.65)]),
        ("v", DCP, 18.3, -48.5, 0.6, 0.3),
        ("t", DCP, B, 0.6, [(18.225, -48.0), (18.3, -48.5)]),
        ("t", CUR, B, 0.8, [(21.175, -48.0), (21.9, -49.0), (22.6, -49.0)]),
    ]


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
            print(f"s4j: {ref} pad {pad.GetNumber()} {pad.GetNetname()} at ({mm(q.x)}, {mm(q.y)})")
    pcbnew.SaveBoard(path, b)
    b = pcbnew.LoadBoard(path)
    lid = {b.GetLayerName(l): l for l in b.GetEnabledLayers().CuStack()}
    for a in ADD:
        code = b.GetNetcodeFromNetname(a[1])
        if code <= 0:
            sys.exit(f"s4j: no net {a[1]}")
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
    for name, layer, pts, why in RULEAREA:
        z = pcbnew.ZONE(b)
        z.SetIsRuleArea(True)
        z.SetZoneName(name)
        z.SetDoNotAllowZoneFills(True)
        z.SetDoNotAllowTracks(False)
        z.SetDoNotAllowVias(False)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
        ls = pcbnew.LSET()
        ls.AddLayer(lid[layer])
        z.SetLayerSet(ls)
        outline(z, pts)
        b.Add(z)
        ADDED.append(dict(kind="rule area (no zone fill)", zone=name, layer=layer, outline=[list(p) for p in pts], why=why))
    for z in b.Zones():
        if not z.GetIsRuleArea():
            z.UnFill()
    pcbnew.SaveBoard(path, b)
    with open(os.path.join(os.path.dirname(path), "s4j.json"), "w") as f:
        json.dump(dict(deleted=DELETED, added=ADDED, moves=MOVES, warn=WARN), f)


def main(argv):
    if os.path.exists(LOCK):
        sys.exit("s4j: the board is open in KiCad; close it first")
    if PART2 and not os.path.exists(os.path.join(RT, "s4j_added.json")):
        sys.exit("s4j: part 1 is not on the board")
    if PART2 and "--dry-run" not in argv and "part 2" in open(os.path.join(RT, "s4j_added.json")).read(300):
        sys.exit("s4j: part 2 is on the board already (not re-runnable)")
    if os.path.exists(os.path.join(RT, "s4j_added.json")) and "--dry-run" not in argv and not PART2:
        sys.exit("s4j: routing/s4j_added.json exists - this block is on the board already (not re-runnable)")
    tmp = tempfile.mkdtemp(prefix=".s4j_", dir=ROOT)
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
        r = subprocess.run([sys.executable, "-u", os.path.abspath(__file__), "--edit", pcb] + (["--part2"] if PART2 else []))
        if r.returncode:
            sys.exit("s4j: edit failed, the board is unchanged")
        r = subprocess.run([CLI, "pcb", "drc", "--format", "json", "--refill-zones", "--save-board",
                            "-o", os.path.join(tmp, "refill.json"), pcb], capture_output=True, text=True)
        if r.returncode:
            sys.exit("s4j: zone refill failed, the board is unchanged\n" + r.stdout[-1500:] + r.stderr[-1500:])
        with open(os.path.join(tmp, "s4j.json")) as f:
            j = json.load(f)
        for w in j["warn"]:
            print("s4j: WARNING " + w)
        print(f"s4j: deleted {len(j['deleted'])}, added {len(j['added'])}, moved {len(j['moves'])}")
        if "--dry-run" in argv:
            out = os.path.abspath(argv[argv.index("--dry-run") + 1])
            shutil.copy(pcb, out)
            print(f"s4j: dry run in {out}, the board is unchanged")
            return 0
        shutil.copy(pcb, BOARD)
        note = "routing stage 4j (2026-11-22), tools/next/route_s4j_drv5_hs.py - incremental edit of the board, not a rebuild"
        for name, key in (("deleted_s4j.json", "deleted"), ("s4j_added.json", "added"), ("moves_s4j.json", "moves")):
            items = j[key]
            if PART2:
                with open(os.path.join(RT, name)) as f:
                    items = json.load(f)[key] + items
                note = note.replace(" - incremental", " (part 1 and part 2) - incremental")
            with open(os.path.join(RT, name), "w") as f:
                json.dump({"note": note, key: items}, f, indent=1)
        print("s4j: wrote the board and routing/*_s4j.json")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    if "--edit" in sys.argv:
        edit(sys.argv[sys.argv.index("--edit") + 1])
        sys.exit(0)
    sys.exit(main(sys.argv[1:]))
