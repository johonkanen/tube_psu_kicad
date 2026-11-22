#!/usr/bin/env python3
"""Routing stage 4b of tube_power 5.2 (2026-11-22): DAB primary POWER stage on the single heatsink line.

    tools/p2k/bin/kipy tools/next/route_s4b_dab_primary.py [--dry-run OUT.kicad_pcb]

Incremental edit of the board of stage 4a (HEAD 9ae37fc), same conventions as route_s4_dab_primary.py; NOT
re-runnable on its own result (refuses when routing/s4b_added.json exists). The rebuild scripts stay frozen.

What it does (F.Cu power, DRV5 and its parts are NOT touched - see README stage 4b for what is left):
  1. switch node DHB_HI_SOURCE: zone S3A_DHB_HI_SOURCE_F becomes one F.Cu shape Q19 pin 3 / Q7 pin 2 (strip east
     of the pin column, x ... 16.6) -> arm y -57.6 ... -52.0 -> TR3 pins 7 / 8. Outer layer only.
  2. DHB_CURRENT: S3A_DHB_CURRENT_F is cut in two by that arm: south part (Q7 pin 3 -> C54 pin 2) and a new north
     part S4B_DHB_CURRENT_F (C67 / C70 pin 2 -> 'Proteus F.Cu pour 23' -> R83). The two are joined on In2 by a
     1.2 mm track that starts in the through-hole pad of Q7 pin 3 and runs UNDER the switch-node strip (x 17.4)
     to two vias beside C67 pin 2 - the return of the HF loop lies under its forward conductor.
  3. C67 (DC+ <-> DHB_CURRENT, 100n 1210) from (26.8, -43.7) to the bridge: F.Cu (19.7, -48.0), pin 1 in a new DC+
     zone S4B_DC+_F at Q19 pin 2, pin 2 in the north DHB_CURRENT zone. C70 stays (no room beside C67 while the
     15V via (17.625, -51.0) of the interim DRV5 layout stands). PRI_DHB_HI / B12 vias 1.4 mm north, off C67.
  4. the 0.2 mm F.Cu sense track C54 pin 2 -> via (19.7, -57.873) lay in the switch-node arm: deleted with its
     via; the In2 sense lane joins the new In2 return at (17.4, -56.5).
Writes kicad_next/routing/moves_s4b.json, deleted_s4b.json, s4b_added.json. Zones are refilled by kicad-cli.
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
SW, DCP, DHBI = "DHB_HI_SOURCE", "DC+", "DHB_CURRENT"
PRI, B12 = "PRI_DHB_HI", "B12"
VIA = "through via 1.1 mm from C67 pin 1 (DC+) on F.Cu: moved 1.4 mm north to the pad of R73 / R74"
ARM = "in the F.Cu switch-node arm Q19 / Q7 -> TR3 (1.2 mm HV spacing)"

DEL = [
    (DHBI, F, 22.88, -61.072, 22.9, -61.072, ARM), (DHBI, F, 22.9, -61.072, 19.7, -57.873, ARM),
    (DHBI, I2, 19.7, -57.873, 18.8, -57.873, ARM),
    (DHBI, I2, 18.8, -52.0, 18.8, -57.873, "sense lane shortened to the y -56.5 lane (its via is gone)"),
    (PRI, I2, 19.0, -46.4, 19.0, -44.5, VIA), (B12, I2, 19.854, -44.154, 19.854, -46.4, VIA),
]
DELVIA = [(DHBI, 19.7, -57.873, ARM), (PRI, 19.0, -46.4, VIA), (B12, 19.854, -46.4, VIA)]
MOVE = [
    ("C67", 19.7, -48.0, 0, "DC+ decoupling to the half bridge: pin 1 in the DC+ zone at Q19 pin 2 (5 mm), pin 2 on "
                            "the DHB_CURRENT return (In2 under the switch-node strip to Q7 pin 3)"),
]
ADD = [
    ("t", DHBI, I2, 0.254, [(18.8, -52.0), (18.8, -56.5)]),
    # HF return Q7 pin 3 (through-hole pad) -> under the switch-node strip -> vias beside C67 pin 2
    ("t", DHBI, I2, 1.2, [(12.75, -63.34), (16.2, -63.34), (17.4, -62.14), (17.4, -52.3), (21.2, -52.3), (22.6, -50.9),
                          (22.6, -49.0)]),
    ("v", DHBI, 22.6, -50.0, 0.8, 0.4), ("v", DHBI, 22.6, -49.0, 0.8, 0.4),
    # north DHB_CURRENT zone into 'Proteus F.Cu pour 23' (R83)
    # (north of the GND via (23.637, -47.2) / 15V via (25.562, -48.6) of C95, which split the zone fill)
    ("t", DHBI, F, 1.0, [(22.0, -46.9), (22.6, -45.9), (25.6, -45.9), (26.3, -46.75), (29.2, -46.75)]),
    # PRI_DHB_HI / B12 vias off C67 (In2 lane ends shortened; B.Cu: in the pad edge of R73 / R74 pin 2)
    ("v", PRI, 19.0, -45.0, 0.5, 0.3), ("t", PRI, I2, 0.1524, [(19.0, -44.5), (19.0, -45.0)]),
    ("t", PRI, B, 0.1524, [(18.8, -45.489), (19.0, -45.0)]),
    ("v", B12, 19.854, -45.0, 0.5, 0.3), ("t", B12, I2, 0.1524, [(19.854, -44.154), (19.854, -45.0)]),
    ("t", B12, B, 0.1524, [(20.3, -45.489), (19.854, -45.0)]),
]
# zone outline changes: name -> (new outline, why); new zones: (name, net, copy settings from, outline)
ZONE = {
    "S3A_DHB_HI_SOURCE_F": ([(11.8, -61.75), (16.6, -61.75), (16.6, -57.6), (27.9, -57.6), (27.9, -58.0), (31.0, -58.0),
                             (31.0, -50.6), (27.9, -50.6), (27.9, -52.0), (16.6, -52.0), (16.6, -51.65), (11.8, -51.65)],
                            "switch node Q19 pin 3 / Q7 pin 2 -> TR3 pins 7 / 8 as one F.Cu shape"),
    "S3A_DHB_CURRENT_F": ([(11.8, -64.15), (25.75, -64.15), (25.75, -59.2), (17.9, -59.2), (17.9, -62.95), (11.8, -62.95)],
                          "south part only (Q7 pin 3 -> C54 pin 2): the switch-node arm crosses the old shape"),
}
NEWZONE = [
    ("S4B_DHB_CURRENT_F", DHBI, "S3A_DHB_CURRENT_F",
     [(20.35, -50.6), (25.75, -50.6), (25.75, -49.3), (28.2, -49.3), (28.2, -46.1), (24.0, -46.1), (24.0, -46.5), (20.35, -46.5)]),
    ("S4B_DC+_F", DCP, "S3A_DHB_CURRENT_F",
     [(11.8, -50.45), (18.9, -50.45), (18.9, -44.6), (14.0, -44.6), (14.0, -48.6), (11.8, -48.6)]),
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
    for net, x, y, why in DELVIA:
        hit = [r for r in tracks if r[1] and r[2] == net and near(r[4], x, y)]
        if not hit:
            WARN.append(f"delvia: no via {net} ({x}, {y})")
        for r in hit:
            DELETED.append(dict(kind="via", net=net, at=[x, y], why=why))
            b.Delete(r[0])
            tracks.remove(r)
    for ref, x, y, rot, why in MOVE:
        fp = b.FindFootprintByReference(ref)
        p = fp.GetPosition()
        side = "B" if fp.IsFlipped() else "F"
        MOVES.append(dict(ref=ref, frm=dict(x=mm(p.x), y=mm(p.y), rot=fp.GetOrientationDegrees(), side=side),
                          to=dict(x=x, y=y, rot=rot, side=side), why=why))
        fp.SetPosition(pcbnew.VECTOR2I(nm(x), nm(y)))
        fp.SetOrientationDegrees(rot)
    pcbnew.SaveBoard(path, b)
    b = pcbnew.LoadBoard(path)
    lid = {b.GetLayerName(l): l for l in b.GetEnabledLayers().CuStack()}
    for a in ADD:
        code = b.GetNetcodeFromNetname(a[1])
        if code <= 0:
            sys.exit(f"s4b: no net {a[1]}")
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
    with open(os.path.join(os.path.dirname(path), "s4b.json"), "w") as f:
        json.dump(dict(deleted=DELETED, added=ADDED, moves=MOVES, warn=WARN), f)


def main(argv):
    if os.path.exists(LOCK):
        sys.exit("s4b: the board is open in KiCad; close it first")
    if os.path.exists(os.path.join(RT, "s4b_added.json")) and "--dry-run" not in argv:
        sys.exit("s4b: routing/s4b_added.json exists - this block is on the board already (not re-runnable)")
    tmp = tempfile.mkdtemp(prefix=".s4b_", dir=ROOT)
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
            sys.exit("s4b: edit failed, the board is unchanged")
        r = subprocess.run([CLI, "pcb", "drc", "--format", "json", "--refill-zones", "--save-board",
                            "-o", os.path.join(tmp, "refill.json"), pcb], capture_output=True, text=True)
        if r.returncode:
            sys.exit("s4b: zone refill failed, the board is unchanged\n" + r.stdout[-1500:] + r.stderr[-1500:])
        with open(os.path.join(tmp, "s4b.json")) as f:
            j = json.load(f)
        for w in j["warn"]:
            print("s4b: WARNING " + w)
        print(f"s4b: deleted {len(j['deleted'])}, added {len(j['added'])}, moved {len(j['moves'])}")
        if "--dry-run" in argv:
            out = os.path.abspath(argv[argv.index("--dry-run") + 1])
            shutil.copy(pcb, out)
            print(f"s4b: dry run in {out}, the board is unchanged")
            return 0
        shutil.copy(pcb, BOARD)
        note = "routing stage 4b (2026-11-22), tools/next/route_s4b_dab_primary.py - incremental edit of the board, not a rebuild"
        for name, key in (("deleted_s4b.json", "deleted"), ("s4b_added.json", "added"), ("moves_s4b.json", "moves")):
            with open(os.path.join(RT, name), "w") as f:
                json.dump({"note": note, key: j[key]}, f, indent=1)
        print("s4b: wrote the board and routing/*_s4b.json")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    if "--edit" in sys.argv:
        edit(sys.argv[sys.argv.index("--edit") + 1])
        sys.exit(0)
    sys.exit(main(sys.argv[1:]))
