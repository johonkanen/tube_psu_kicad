#!/usr/bin/env python3
"""Routing stage 4k of tube_power 5.2 (2026-11-22): PFC boost diodes SICD1 / SICD2 (moved and turned by the user) back
into their pours - the outlines of the DC+ pour 29 and of the two PFC drain pours 10 / 1 on F.Cu re-shaped, two
B.Cu links of PFC_DRAIN_2 between through-hole pads (L1 - SICD2 A - Q6 drain).

    tools/p2k/bin/kipy tools/next/route_s4k_hs_sicd.py [--dry-run OUT.kicad_pcb]

Incremental edit of the board of stage 4j (HEAD 5bc390d), same conventions as route_s4j_drv5_hs.py; NOT
re-runnable on its own result (refuses when routing/s4k_added.json exists). The rebuild scripts stay frozen.
The turn-off branch D30 / R53 of Q19 is NOT placed by this script (README "Stage 4k": no legal place found).
Writes kicad_next/routing/moves_s4k.json (empty), deleted_s4k.json, s4k_added.json. Zones are refilled by kicad-cli.
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
D1, D2, DCP = "/05 PFC/PFC_DRAIN_1", "/05 PFC/PFC_DRAIN_2", "DC+"
DELNETS = {}
DEL = []
DELVIA = []
MOVE = []
ADD = [
    # PFC_DRAIN_2 on B.Cu between through-hole pads (no via): SICD2 A - Q6 drain (the DC+ strip of the cathode now
    # lies between them on F.Cu), and L1 - SICD2 A beside the 1.5 mm F.Cu neck between the cathode pad and the AC2 pour
    ("t", D2, B, 2.4, [(3.09, -3.82), (4.6, -2.436), (11.389, -2.436)]),
    ("t", D2, B, 2.0, [(-0.102, 3.342), (-0.3, 2.5), (-0.3, -1.6), (1.9, -3.82), (3.09, -3.82)]),
]
RULEAREA = []
ZONE = {}
DELZONE = []
NEWZONE = []
WS1 = "SICD1 turned by the user (A now (11.8, -21.4), K (11.8, -26.48)): the old anode lobe goes to DC+, new anode lobe north of it"
WS2 = "SICD2 turned by the user (A now (3.09, -3.82), K (3.09, 1.26)): DC+ strip from the peninsula of DB1 / C73 north to the cathode, drain pour west of it"
# zone, first vertex of the replaced run, last vertex of the run (both replaced), new vertices, why
RESHAPE = [
    ("Proteus F.Cu pour 29", (9.545, -21.757), (13.355, -30.044),
     [(9.545, -19.1), (12.8, -19.1), (14.1, -20.4), (14.1, -24.3), (9.4, -24.3), (9.4, -28.7), (10.75, -30.044)], WS1),
    ("Proteus F.Cu pour 29", (8.91, -5.946), (1.925, -4.041),
     [(8.91, -6.2), (7.9, -5.2), (7.9, 1.0), (6.5, 2.4), (2.3, 2.4), (2.3, 0.8), (5.4, 0.8), (5.4, -6.1), (1.925, -6.1)], WS2),
    ("Proteus F.Cu pour 10", (8.714, -28.712), (8.133, -21.724),
     [(8.2, -25.7), (8.2, -23.1), (12.9, -23.1), (12.9, -21.0), (12.2, -20.3), (10.7, -20.3), (9.3, -21.724)], WS1),
    ("Proteus F.Cu pour 1", None, None,
     [(0.0, 6.06), (-0.554, 5.442), (-0.554, 4.838), (-4.364, 1.03), (-4.364, -0.147), (-2.5, -2.039), (1.6, -2.039),
      (2.2, -2.6), (2.2, -5.0), (4.2, -5.0), (4.2, -1.0), (2.3, -1.0), (1.1, 0.0), (1.1, 6.06)], WS2),
]
# pad cut-outs (zone holes) of the old pad positions and of pads no longer inside the outline: zone, centre
DROPHOLE = [("Proteus F.Cu pour 10", (11.5, -26.73)), ("Proteus F.Cu pour 29", (11.5, -21.65)),
            ("Proteus F.Cu pour 29", (3.8, -4.98)), ("Proteus F.Cu pour 1", (3.8, 0.1)), ("Proteus F.Cu pour 1", (11.389, -2.436))]


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
            print(f"s4k: {ref} pad {pad.GetNumber()} {pad.GetNetname()} at ({mm(q.x)}, {mm(q.y)})")
    pcbnew.SaveBoard(path, b)
    b = pcbnew.LoadBoard(path)
    lid = {b.GetLayerName(l): l for l in b.GetEnabledLayers().CuStack()}
    for a in ADD:
        code = b.GetNetcodeFromNetname(a[1])
        if code <= 0:
            sys.exit(f"s4k: no net {a[1]}")
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
    for name in dict.fromkeys(r[0] for r in RESHAPE):
        z = byname[name]
        ol = z.Outline()
        pts = [(ol.Outline(0).CPoint(k).x / 1e6, ol.Outline(0).CPoint(k).y / 1e6) for k in range(ol.Outline(0).PointCount())]
        old = [[round(x, 4), round(y, 4)] for x, y in pts]
        holes = []
        for h in range(ol.HoleCount(0)):
            hh = ol.Hole(0, h)
            hp = [(hh.CPoint(k).x / 1e6, hh.CPoint(k).y / 1e6) for k in range(hh.PointCount())]
            cx, cy = sum(p[0] for p in hp) / len(hp), sum(p[1] for p in hp) / len(hp)
            if any(n == name and abs(cx - c[0]) < 0.3 and abs(cy - c[1]) < 0.3 for n, c in DROPHOLE):
                DELETED.append(dict(kind="zone hole", zone=name, centre=[round(cx, 3), round(cy, 3)],
                                    why="pad cut-out of a pad that is no longer there / no longer inside the outline"))
            else:
                holes.append(hp)
        whys = []
        for n, first, last, new, why in RESHAPE:
            if n != name:
                continue
            whys.append(why)
            if first is None:
                pts = list(new)
                continue
            idx = lambda q: [k for k, p in enumerate(pts) if abs(p[0] - q[0]) < 0.003 and abs(p[1] - q[1]) < 0.003]  # noqa: E731
            i, j = idx(first), idx(last)
            if len(i) != 1 or len(j) != 1 or i[0] >= j[0]:
                sys.exit(f"s4k: reshape {name}: vertices {first} / {last} not found once in this order")
            pts = pts[:i[0]] + list(new) + pts[j[0] + 1:]
        ol.RemoveAllContours()
        ol.NewOutline()
        for x, y in pts:
            ol.Append(nm(x), nm(y))
        for hp in holes:
            hi = ol.NewHole()
            for x, y in hp:
                ol.Append(nm(x), nm(y), 0, hi)
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)     # as before (solid)
        DELETED.append(dict(kind="zone outline", zone=name, net=z.GetNetname(), why="; ".join(whys),
                            new=[[round(x, 4), round(y, 4)] for x, y in pts], old=old, holes_kept=len(holes)))
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
    with open(os.path.join(os.path.dirname(path), "s4k.json"), "w") as f:
        json.dump(dict(deleted=DELETED, added=ADDED, moves=MOVES, warn=WARN), f)


def main(argv):
    if os.path.exists(LOCK):
        sys.exit("s4k: the board is open in KiCad; close it first")
    if os.path.exists(os.path.join(RT, "s4k_added.json")) and "--dry-run" not in argv:
        sys.exit("s4k: routing/s4k_added.json exists - this block is on the board already (not re-runnable)")
    tmp = tempfile.mkdtemp(prefix=".s4k_", dir=ROOT)
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
            sys.exit("s4k: edit failed, the board is unchanged")
        r = subprocess.run([CLI, "pcb", "drc", "--format", "json", "--refill-zones", "--save-board",
                            "-o", os.path.join(tmp, "refill.json"), pcb], capture_output=True, text=True)
        if r.returncode:
            sys.exit("s4k: zone refill failed, the board is unchanged\n" + r.stdout[-1500:] + r.stderr[-1500:])
        with open(os.path.join(tmp, "s4k.json")) as f:
            j = json.load(f)
        for w in j["warn"]:
            print("s4k: WARNING " + w)
        print(f"s4k: deleted {len(j['deleted'])}, added {len(j['added'])}, moved {len(j['moves'])}")
        if "--dry-run" in argv:
            out = os.path.abspath(argv[argv.index("--dry-run") + 1])
            shutil.copy(pcb, out)
            print(f"s4k: dry run in {out}, the board is unchanged")
            return 0
        shutil.copy(pcb, BOARD)
        note = "routing stage 4k (2026-11-22), tools/next/route_s4k_hs_sicd.py - incremental edit of the board, not a rebuild"
        for name, key in (("deleted_s4k.json", "deleted"), ("s4k_added.json", "added"), ("moves_s4k.json", "moves")):
            items = j[key]
            with open(os.path.join(RT, name), "w") as f:
                json.dump({"note": note, key: items}, f, indent=1)
        print("s4k: wrote the board and routing/*_s4k.json")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    if "--edit" in sys.argv:
        edit(sys.argv[sys.argv.index("--edit") + 1])
        sys.exit(0)
    sys.exit(main(sys.argv[1:]))
