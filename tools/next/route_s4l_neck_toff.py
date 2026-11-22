#!/usr/bin/env python3
"""Routing stage 4l of tube_power 5.2 (2026-11-22), two steps:

  step A (plain run): DC+ neck between the peninsula of DB1 / C73 / SICD2-K and the DC+ trunk at (12.8 ... 14.0, -18.8)
         widened - south-west corner of GND pour 30 cut back, parallel DC+ paths on In3 (zone) and B.Cu (track)
         with 4 + 3 stitching vias.
  step B (--stepB): turn-off branch D30 / R53 of Q19 (see README "Stage 4l").

    tools/p2k/bin/kipy tools/next/route_s4l_neck_toff.py [--stepB] [--dry-run OUT.kicad_pcb]

Incremental edit, same conventions as route_s4k_hs_sicd.py; NOT re-runnable (step A refuses when
routing/s4l_added.json exists, step B when it holds a "stepB" marker). The rebuild scripts stay frozen.
Writes kicad_next/routing/moves_s4l.json, deleted_s4l.json, s4l_added.json (step B appends). Zones are refilled by
kicad-cli.
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
DELETED, ADDED, MOVES, WARN = [], [], [], []
DCP = "DC+"
STEPB = "--stepB" in sys.argv
DELNETS = {}
DEL = []
DELVIA = []
MOVE = []
ADD = []
RULEAREA = []
ZONE = {}
DELZONE = []
NEWZONE = []          # name, net, layer key, settings copied from zone, outline
RESHAPE = []
DROPHOLE = []
if not STEPB:
    WN = "DC+ neck (12.8 ... 14.0, -18.8) between the peninsula of DB1 / C73 / SICD2-K and the DC+ trunk"
    # west vias in the F.Cu peninsula, east vias in the trunk east of the anode pad of SICD1 (1.5 mm from the pad)
    for x, y in ((10.2, -17.5), (11.3, -17.5), (10.2, -18.55), (11.3, -18.55), (14.7, -19.9), (14.7, -21.0), (14.7, -22.1)):
        ADD.append(("v", DCP, x, y, 0.8, 0.4))
    # B.Cu: 1.0 mm, 1.25 mm below the B.Cu GND tracks of the C73 vias (ends y -16.4) and 1.25 mm above the anode pad of SICD1
    ADD.append(("t", DCP, B, 1.0, [(10.2, -18.65), (13.6, -18.65), (14.7, -19.75), (14.7, -22.1)]))
    NEWZONE.append(("S4L_DC+_In3_neck", DCP, I3, "Proteus F.Cu pour 29",
                    [(9.7, -16.9), (13.4, -16.9), (15.1, -18.6), (15.1, -22.7), (13.3, -22.7), (13.3, -19.9), (9.7, -19.9)]))
    # GND pour 30 (pad 2 of C73 and its 15 GND vias): south edge back to the pad edge y -16.7, south-west corner chamfered
    RESHAPE.append(("Proteus F.Cu pour 30", None, None,
                    [(17.1, -16.7), (17.1, -11.0), (13.2, -11.0), (13.2, -16.3), (13.6, -16.7)], WN))
else:
    pass

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
            print(f"s4l: {ref} pad {pad.GetNumber()} {pad.GetNetname()} at ({mm(q.x)}, {mm(q.y)})")
    pcbnew.SaveBoard(path, b)
    b = pcbnew.LoadBoard(path)
    lid = {b.GetLayerName(l): l for l in b.GetEnabledLayers().CuStack()}
    for a in ADD:
        code = b.GetNetcodeFromNetname(a[1])
        if code <= 0:
            sys.exit(f"s4l: no net {a[1]}")
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
    for name, net, lay, like, pts in NEWZONE:           # (before the outline of `like` is changed: only settings are read)
        src = byname[like]
        z = pcbnew.ZONE(b)
        z.SetLayer(lid[LAYER[lay]])
        z.SetNetCode(b.GetNetcodeFromNetname(net))
        z.SetZoneName(name)
        z.SetAssignedPriority(src.GetAssignedPriority() + 40)   # above the In3 plane zones
        z.SetLocalClearance(src.GetLocalClearance())
        z.SetMinThickness(src.GetMinThickness())
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)     # solid, as the 5.1 power pours (pour 29)
        z.SetIslandRemovalMode(src.GetIslandRemovalMode())
        outline(z, pts)
        b.Add(z)
        ADDED.append(dict(kind="zone", zone=name, net=net, layer=LAYER[lay], outline=pts))
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
                sys.exit(f"s4l: reshape {name}: vertices {first} / {last} not found once in this order")
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
    with open(os.path.join(os.path.dirname(path), "s4l.json"), "w") as f:
        json.dump(dict(deleted=DELETED, added=ADDED, moves=MOVES, warn=WARN), f)


def main(argv):
    if os.path.exists(LOCK):
        sys.exit("s4l: the board is open in KiCad; close it first")
    prev = {}
    if os.path.exists(os.path.join(RT, "s4l_added.json")):
        for name, key in (("deleted_s4l.json", "deleted"), ("s4l_added.json", "added"), ("moves_s4l.json", "moves")):
            with open(os.path.join(RT, name)) as f:
                prev[key] = json.load(f)
    done_b = bool(prev) and prev["added"].get("stepB")
    if "--dry-run" not in argv and ((not STEPB and prev) or (STEPB and (not prev or done_b))):
        sys.exit("s4l: this step is on the board already (not re-runnable), or step B before step A")
    tmp = tempfile.mkdtemp(prefix=".s4l_", dir=ROOT)
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
            sys.exit("s4l: edit failed, the board is unchanged")
        r = subprocess.run([CLI, "pcb", "drc", "--format", "json", "--refill-zones", "--save-board",
                            "-o", os.path.join(tmp, "refill.json"), pcb], capture_output=True, text=True)
        if r.returncode:
            sys.exit("s4l: zone refill failed, the board is unchanged\n" + r.stdout[-1500:] + r.stderr[-1500:])
        with open(os.path.join(tmp, "s4l.json")) as f:
            j = json.load(f)
        for w in j["warn"]:
            print("s4l: WARNING " + w)
        print(f"s4l: deleted {len(j['deleted'])}, added {len(j['added'])}, moved {len(j['moves'])}")
        if "--dry-run" in argv:
            out = os.path.abspath(argv[argv.index("--dry-run") + 1])
            shutil.copy(pcb, out)
            print(f"s4l: dry run in {out}, the board is unchanged")
            return 0
        shutil.copy(pcb, BOARD)
        note = "routing stage 4l (2026-11-22), tools/next/route_s4l_neck_toff.py - incremental edit of the board, not a rebuild"
        for name, key in (("deleted_s4l.json", "deleted"), ("s4l_added.json", "added"), ("moves_s4l.json", "moves")):
            items = (prev[key][key] if STEPB else []) + j[key]
            d = {"note": note, key: items}
            if STEPB:
                d["stepB"] = True
            with open(os.path.join(RT, name), "w") as f:
                json.dump(d, f, indent=1)
        print("s4l: wrote the board and routing/*_s4l.json")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    if "--edit" in sys.argv:
        edit(sys.argv[sys.argv.index("--edit") + 1])
        sys.exit(0)
    sys.exit(main(sys.argv[1:]))
