#!/usr/bin/env python3
"""Routing stage 4i of tube_power 5.2 (2026-11-22): inputs of DRV5 (PRI_DHB_HI, B12, DAB_DIS) and +1V65_BIAS across the FET
column on In3 through a window in the 15V strip; R73, R74, C120, R129 to the input pins.

    tools/p2k/bin/kipy tools/next/route_s4i_drv5_in.py [--dry-run OUT.kicad_pcb]

Incremental edit of the board of stage 4h2 (HEAD 6f78212), same conventions as route_s4d_shunt_u1.py; NOT
re-runnable on its own result (refuses when routing/s4i_added.json exists). The rebuild scripts stay frozen.
See README "Stage 4i" for what is on the board and what is still open.
Writes kicad_next/routing/moves_s4i.json, deleted_s4i.json, s4i_added.json. Zones are refilled by kicad-cli.
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
PRI, B12, DIS, BIAS = "PRI_DHB_HI", "B12", "DAB_DIS", "+1V65_BIAS"
WE = "old place east of the FET column (part moved to the input pins of DRV5 on the west side)"
WB = "In2 lane end of +1V65_BIAS over the 15V strip (tapped at the new via (14.6, -44.076), crosses on In3)"
WG = "GND of R127 / C118 to the via of C94: in the way of DAB_DIS at pin 5 (own GND via (-6.9, -51.55) instead)"
DELNETS = {}
DEL = [
    (PRI, B, 18.8, -45.527, 19.0, -45.727, WE), (PRI, B, 18.8, -45.489, 19.0, -45.0, WE),
    (PRI, B, 19.0, -45.727, 19.0, -46.4, WE), (B12, B, 20.3, -45.489, 19.854, -45.0, WE),
    (DIS, B, 15.3, -47.83, 15.3, -47.225, WE), (DIS, B, 15.3, -47.83, 16.425, -47.83, WE),
    (DIS, B, 16.425, -47.83, 17.825, -46.43, WE), (DIS, B, 16.6, -47.75, 16.6, -47.275, WE),
    (DIS, B, 17.825, -46.43, 17.825, -44.83, WE), (DIS, B, 17.825, -44.83, 17.925, -44.73, WE),
    (DIS, B, 17.925, -44.73, 17.925, -44.33, WE), (DIS, B, 17.925, -44.33, 17.825, -44.23, WE),
    (DIS, B, 17.825, -44.23, 17.825, -43.33, WE), (DIS, B, 17.825, -43.33, 18.225, -42.93, WE),
    (DIS, B, 18.225, -42.93, 22.225, -42.93, WE), (DIS, B, 22.225, -42.93, 23.225, -43.93, WE),
    (DIS, B, 23.225, -43.93, 23.225, -44.73, WE), (DIS, B, 23.225, -44.73, 23.925, -45.43, WE),
    (DIS, B, 23.925, -45.43, 27.425, -45.43, WE),
    (GND, B, 15.3, -45.675, 16.6, -45.625, WE),
    (GND, B, 18.876, -43.8, 18.8, -43.8, WE), (GND, B, 18.8, -43.724, 18.8, -43.8, WE),
    (GND, B, 18.8, -43.876, 18.8, -43.8, WE), (GND, B, 18.724, -43.8, 18.8, -43.8, WE),
    (GND, B, 20.3, -43.876, 20.3, -43.8, WE), (GND, B, 20.376, -43.8, 20.3, -43.8, WE),
    (GND, B, 20.3, -43.724, 20.3, -43.8, WE), (GND, B, 20.224, -43.8, 20.3, -43.8, WE),
    (BIAS, I2, 12.4, -44.076, 15.224, -44.076, WB),
    (GND, B, -5.825, -51.805, -5.75, -49.405, WG),
]
DELVIA = []
# ref, x, y, rot, side ("F" / "B": flipped when it differs), why
MOVE = [
    ("R73", -6.875, -45.2, 0, "B", "pull-down of PRI_DHB_HI at pin 1 of DRV5 (west of the input pins)"),
    ("R74", -6.875, -46.9, 0, "B", "pull-down of B12 at pin 2 of DRV5"),
    ("C120", -7.0, -49.45, -90, "B", "DAB_DIS filter capacitor at pin 5 of DRV5"),
    ("R129", -8.5, -49.45, -90, "B", "DAB_DIS pull-down at pin 5 of DRV5"),
]
LW = 0.152
ADD = [
    # 15V: the south half of the In3 strip is fed from the east block of the plane round the south of Q19
    ("t", V15, "3", 1.0, [(24.0, -50.4), (24.0, -51.6), (17.625, -51.6), (17.625, -54.75), (17.125, -55.25), (12.0, -55.25)]),
    ("t", V15, "3", 0.5, [(17.625, -51.6), (17.625, -51.0)]),
    # east taps
    ("v", BIAS, 14.6, -44.076, 0.5, 0.3),
    ("t", BIAS, I2, LW, [(15.224, -44.076), (14.6, -44.076)]),
    # DAB_DIS leaves its kept via (27.425, -45.43) on In3 through the east block of the 15V plane; the block is
    # joined again round the east of that via
    ("t", V15, "3", 0.5, [(27.6, -44.6), (28.2, -44.6), (28.2, -46.6), (27.6, -46.6)]),
    # the four lanes on In3 through the window
    ("t", PRI, "3", LW, [(19.0, -45.0), (19.0, -43.7), (17.686, -42.386), (10.4, -42.386), (10.2, -42.586), (10.2, -45.255),
                         (10.0, -45.455), (-4.1, -45.455)]),
    ("t", B12, "3", LW, [(19.854, -45.0), (19.354, -45.5), (18.75, -45.5), (18.5, -45.25), (18.5, -43.7), (17.625, -42.825),
                         (10.71, -42.825), (10.51, -43.025), (10.51, -45.6), (10.31, -45.8), (-3.0, -45.8),
                         (-3.925, -46.725), (-4.1, -46.725)]),
    ("t", DIS, "3", LW, [(27.425, -45.43), (27.005, -45.85), (18.4, -45.85), (18.15, -45.6), (18.15, -44.525), (17.059, -43.434), (11.02, -43.434), (10.82, -43.634), (10.82, -45.95),
                         (10.62, -46.15), (0.5, -46.15), (-3.885, -50.535), (-4.1, -50.535)]),
    ("t", BIAS, "3", LW, [(14.6, -44.076), (11.33, -44.076), (11.13, -44.276), (11.13, -46.3), (10.93, -46.5), (6.0, -46.5),
                          (1.5, -51.0), (1.5, -54.9)]),
    # west side: vias beside the input pins, B.Cu to the pins and the parts
    ("v", PRI, -4.1, -45.455, 0.5, 0.3), ("v", B12, -4.1, -46.725, 0.5, 0.3), ("v", DIS, -4.1, -50.535, 0.5, 0.3),
    ("v", GND, -6.9, -51.55, 0.5, 0.3),
    ("t", PRI, B, 0.2, [(-2.35, -45.455), (-4.1, -45.455), (-5.0, -45.455), (-6.05, -45.2)]),
    ("t", B12, B, 0.2, [(-2.35, -46.725), (-4.1, -46.725), (-5.2, -46.725), (-6.05, -46.9)]),
    ("t", DIS, B, 0.2, [(-2.35, -50.535), (-4.1, -50.535), (-6.3, -50.535), (-6.7, -50.225), (-8.5, -50.25)]),
    ("t", GND, B, 0.3, [(-7.7, -45.2), (-7.7, -46.9), (-7.7, -47.9), (-7.0, -48.6)]),
    ("t", GND, B, 0.3, [(-8.5, -48.65), (-7.0, -48.65), (-6.25, -49.405), (-5.75, -49.405)]),
    ("t", GND, B, 0.3, [(-5.825, -51.805), (-6.9, -51.55)]),
]
# rule areas "no zone fill": name, layer, outline, why
RULEAREA = [
    ("S4I_KO_In3_15V_window", "In3.Power",
     [(13.7, -42.0), (9.3, -42.0), (9.3, -46.9), (13.7, -46.9)],
     "window in the In3 15V strip (x 9.5 - 13.5) for the lanes PRI_DHB_HI, B12, DAB_DIS, +1V65_BIAS"),
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
            print(f"s4i: {ref} pad {pad.GetNumber()} {pad.GetNetname()} at ({mm(q.x)}, {mm(q.y)})")
    pcbnew.SaveBoard(path, b)
    b = pcbnew.LoadBoard(path)
    lid = {b.GetLayerName(l): l for l in b.GetEnabledLayers().CuStack()}
    for a in ADD:
        code = b.GetNetcodeFromNetname(a[1])
        if code <= 0:
            sys.exit(f"s4i: no net {a[1]}")
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
    with open(os.path.join(os.path.dirname(path), "s4i.json"), "w") as f:
        json.dump(dict(deleted=DELETED, added=ADDED, moves=MOVES, warn=WARN), f)


def main(argv):
    if os.path.exists(LOCK):
        sys.exit("s4i: the board is open in KiCad; close it first")
    if os.path.exists(os.path.join(RT, "s4i_added.json")) and "--dry-run" not in argv:
        sys.exit("s4i: routing/s4i_added.json exists - this block is on the board already (not re-runnable)")
    tmp = tempfile.mkdtemp(prefix=".s4i_", dir=ROOT)
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
            sys.exit("s4i: edit failed, the board is unchanged")
        r = subprocess.run([CLI, "pcb", "drc", "--format", "json", "--refill-zones", "--save-board",
                            "-o", os.path.join(tmp, "refill.json"), pcb], capture_output=True, text=True)
        if r.returncode:
            sys.exit("s4i: zone refill failed, the board is unchanged\n" + r.stdout[-1500:] + r.stderr[-1500:])
        with open(os.path.join(tmp, "s4i.json")) as f:
            j = json.load(f)
        for w in j["warn"]:
            print("s4i: WARNING " + w)
        print(f"s4i: deleted {len(j['deleted'])}, added {len(j['added'])}, moved {len(j['moves'])}")
        if "--dry-run" in argv:
            out = os.path.abspath(argv[argv.index("--dry-run") + 1])
            shutil.copy(pcb, out)
            print(f"s4i: dry run in {out}, the board is unchanged")
            return 0
        shutil.copy(pcb, BOARD)
        note = "routing stage 4i (2026-11-22), tools/next/route_s4i_drv5_in.py - incremental edit of the board, not a rebuild"
        for name, key in (("deleted_s4i.json", "deleted"), ("s4i_added.json", "added"), ("moves_s4i.json", "moves")):
            with open(os.path.join(RT, name), "w") as f:
                json.dump({"note": note, key: j[key]}, f, indent=1)
        print("s4i: wrote the board and routing/*_s4i.json")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    if "--edit" in sys.argv:
        edit(sys.argv[sys.argv.index("--edit") + 1])
        sys.exit(0)
    sys.exit(main(sys.argv[1:]))
