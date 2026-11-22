#!/usr/bin/env python3
"""Routing stage 4d of tube_power 5.2 (2026-11-22): shunt R83 to Q7 pin 3 (block D1, part 1).

    tools/p2k/bin/kipy tools/next/route_s4d_shunt_u1.py [--dry-run OUT.kicad_pcb]

Incremental edit of the board of stage 4b (HEAD 1ac3f19), same conventions as route_s4b_dab_primary.py; NOT
re-runnable on its own result (refuses when routing/s4d_added.json exists). The rebuild scripts stay frozen.

What it does (README "Stage 4d"):
  1. R83 (4 mOhm, DHB_CURRENT -> GND) from B.Cu (29.99, -42.0) to F.Cu (15.9, -64.04), pads lying east-west:
     pin 1 inside the F.Cu zone S3A_DHB_CURRENT_F 1.15 mm east of Q7 pin 3, pin 2 (GND) south of the zone with
     three GND vias at its east end (one of them is the kept via of C96).
  2. Kelvin tap: via in the inner edge of R83 pin 1 -> In2 lane y -64.8 south of Q7 pin 3 -> the kept via
     (2.3, -63.3) of R104. The old In2 sense lane (y -56.5, x 7.2) is deleted. The In2 return of C67 keeps its
     way to Q7 pin 3 but turns north 1.9 mm earlier, so that it does not touch the tap via.
  3. the 1.0 mm F.Cu tie of stage 4b to the old place of R83 and the pad spokes of the old place are deleted
     (C70 pin 2 / 'Proteus F.Cu pour 23' stay on the net by the old In2 sense line, 0.254 mm - interim).
The U1 block is NOT moved by this script (see README).
Writes kicad_next/routing/moves_s4d.json, deleted_s4d.json, s4d_added.json. Zones are refilled by kicad-cli.
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
R83_ROT = 90
DELETED, ADDED, MOVES, WARN = [], [], [], []
DHBI, GND = "DHB_CURRENT", "GND"
OLD = "old place of R83 (29.99, -42.0): pad spoke / link"
TIE = "1.0 mm F.Cu tie of stage 4b to the old place of R83"
SENSE = "old In2 sense lane (tapped the In2 return at (17.4, -56.5)): replaced by the Kelvin lane y -64.8"
RET = "In2 return of C67 turns north at x 14.3 (off the Kelvin via (16.5, -63.75))"

DEL = [
    (GND, B, 29.424, -42.0, 29.5, -42.0, OLD), (GND, B, 29.5, -42.076, 29.5, -42.0, OLD),
    (GND, B, 29.576, -42.0, 29.5, -42.0, OLD), (GND, B, 29.5, -41.924, 29.5, -42.0, OLD),
    (DHBI, B, 31.795, -41.95, 31.745, -42.0, OLD), (DHBI, B, 30.475, -42.076, 30.475, -42.0, OLD),
    (DHBI, B, 30.475, -41.924, 30.475, -42.0, OLD), (DHBI, B, 30.551, -42.0, 30.475, -42.0, OLD),
    (DHBI, B, 30.399, -42.0, 30.475, -42.0, OLD), (DHBI, B, 31.745, -42.0, 30.475, -42.0, OLD),
    (DHBI, F, 22.0, -46.9, 22.6, -45.9, TIE), (DHBI, F, 22.6, -45.9, 25.6, -45.9, TIE),
    (DHBI, F, 25.6, -45.9, 26.3, -46.75, TIE), (DHBI, F, 26.3, -46.75, 29.2, -46.75, TIE),
    (DHBI, I2, 27.55, -49.6, 21.2, -49.6, SENSE), (DHBI, I2, 21.2, -49.6, 18.8, -52.0, SENSE),
    (DHBI, I2, 18.8, -52.0, 18.8, -56.5, SENSE), (DHBI, I2, 9.5, -56.5, 18.8, -56.5, SENSE),
    (DHBI, I2, 9.5, -56.5, 7.2, -58.8, SENSE), (DHBI, I2, 7.2, -58.8, 7.2, -61.5, SENSE),
    (DHBI, I2, 7.2, -61.5, 5.4, -63.3, SENSE), (DHBI, I2, 5.4, -63.3, 2.8, -63.3, SENSE),
    (DHBI, I2, 2.8, -63.3, 2.3, -63.3, SENSE),
    (DHBI, I2, 12.75, -63.34, 16.2, -63.34, RET), (DHBI, I2, 16.2, -63.34, 17.4, -62.14, RET),
]
DELVIA = []
# ref, x, y, rot, side ("F" / "B": flipped when it differs), why
MOVE = [
    ("R83", 15.9, -64.0375, R83_ROT, "F",
     "shunt to Q7 pin 3: pin 1 in the F.Cu zone S3A_DHB_CURRENT_F 1.15 mm east of the pin, pin 2 (GND) south of "
     "it with three GND vias; bridge current no longer on In2, low-side gate return 17 mm shorter"),
]
ADD = [
    # C70 / 'Proteus F.Cu pour 23' stay on the net: the rest of the old sense line ends on the In2 return
    ("t", DHBI, I2, 0.254, [(27.55, -49.6), (22.6, -49.6)]),
    # In2 return of C67 (HF loop), Q7 pin 3 -> north at x 14.3 -> the kept vertical x 17.4
    ("t", DHBI, I2, 1.2, [(12.75, -63.34), (14.3, -63.34), (15.5, -62.14), (17.4, -62.14)]),
    # Kelvin tap in the inner edge of R83 pin 1, In2 lane south of Q7 pin 3 to the kept via of R104
    ("v", DHBI, 16.5, -63.75, 0.5, 0.3),
    ("t", DHBI, I2, 0.2, [(16.5, -63.75), (15.45, -64.8), (3.8, -64.8), (2.3, -63.3)]),
    # GND of R83 pin 2: along the pad to the kept via (17.96, -64.55) and two new vias
    ("t", GND, F, 0.35, [(15.1, -64.525), (17.3, -64.525)]),
    ("t", GND, F, 0.35, [(17.3, -64.525), (17.96, -64.55)]),
    ("t", GND, F, 0.5, [(17.25, -64.93), (18.55, -64.93)]),
    ("v", GND, 17.25, -64.93, 0.6, 0.3), ("v", GND, 18.55, -64.93, 0.6, 0.3),
]
ZONE = {}
# 5.1 pour round pin 1 of R83 at its old place: nothing of the net is left on B.Cu there (isolated fill)
DELZONE = [("Proteus B.Cu pour 23", "B.Cu", OLD)]
NEWZONE = []


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
            print(f"s4d: {ref} pad {pad.GetNumber()} {pad.GetNetname()} at ({mm(q.x)}, {mm(q.y)})")
    pcbnew.SaveBoard(path, b)
    b = pcbnew.LoadBoard(path)
    lid = {b.GetLayerName(l): l for l in b.GetEnabledLayers().CuStack()}
    for a in ADD:
        code = b.GetNetcodeFromNetname(a[1])
        if code <= 0:
            sys.exit(f"s4d: no net {a[1]}")
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
    with open(os.path.join(os.path.dirname(path), "s4d.json"), "w") as f:
        json.dump(dict(deleted=DELETED, added=ADDED, moves=MOVES, warn=WARN), f)


def main(argv):
    if os.path.exists(LOCK):
        sys.exit("s4d: the board is open in KiCad; close it first")
    if os.path.exists(os.path.join(RT, "s4d_added.json")) and "--dry-run" not in argv:
        sys.exit("s4d: routing/s4d_added.json exists - this block is on the board already (not re-runnable)")
    tmp = tempfile.mkdtemp(prefix=".s4d_", dir=ROOT)
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
            sys.exit("s4d: edit failed, the board is unchanged")
        r = subprocess.run([CLI, "pcb", "drc", "--format", "json", "--refill-zones", "--save-board",
                            "-o", os.path.join(tmp, "refill.json"), pcb], capture_output=True, text=True)
        if r.returncode:
            sys.exit("s4d: zone refill failed, the board is unchanged\n" + r.stdout[-1500:] + r.stderr[-1500:])
        with open(os.path.join(tmp, "s4d.json")) as f:
            j = json.load(f)
        for w in j["warn"]:
            print("s4d: WARNING " + w)
        print(f"s4d: deleted {len(j['deleted'])}, added {len(j['added'])}, moved {len(j['moves'])}")
        if "--dry-run" in argv:
            out = os.path.abspath(argv[argv.index("--dry-run") + 1])
            shutil.copy(pcb, out)
            print(f"s4d: dry run in {out}, the board is unchanged")
            return 0
        shutil.copy(pcb, BOARD)
        note = "routing stage 4d (2026-11-22), tools/next/route_s4d_shunt_u1.py - incremental edit of the board, not a rebuild"
        for name, key in (("deleted_s4d.json", "deleted"), ("s4d_added.json", "added"), ("moves_s4d.json", "moves")):
            with open(os.path.join(RT, name), "w") as f:
                json.dump({"note": note, key: j[key]}, f, indent=1)
        print("s4d: wrote the board and routing/*_s4d.json")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    if "--edit" in sys.argv:
        edit(sys.argv[sys.argv.index("--edit") + 1])
        sys.exit(0)
    sys.exit(main(sys.argv[1:]))
