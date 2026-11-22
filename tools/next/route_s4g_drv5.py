#!/usr/bin/env python3
"""Routing stage 4g of tube_power 5.2 (2026-11-22): DRV5 to the bottom side west of the Q19 pins.

    tools/p2k/bin/kipy tools/next/route_s4g_drv5.py [--dry-run OUT.kicad_pcb]

Incremental edit of the board of stage 4f (HEAD 11037bb), same conventions as route_s4d_shunt_u1.py; NOT
re-runnable on its own result (refuses when routing/s4g_added.json exists). The rebuild scripts stay frozen.
See README "Stage 4g" for what is on the board and what is still open.
Writes kicad_next/routing/moves_s4g.json, deleted_s4g.json, s4g_added.json. Zones are refilled by kicad-cli.
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
V15, V5, GND, BIAS, UAP = "15V", "5V", "GND", "+1V65_BIAS", "Net-(U1A-+)"
DT, VDDA, HS, HG, QG = "Net-(DRV5-DT)", "Net-(DRV5-VDDA)", "DHB_HI_SOURCE", "DHB_HI_GATE", "Net-(Q19-G)"
W15 = "dead-end B.Cu 15V track through the new place of DRV5 (dangling before; 15V is taken from the In3 plane)"
WB = "+1V65_BIAS lane through the high-side strip / under DRV5 (was open towards R103 already): to be re-drawn"
WU = "U1A+ / bias copper of R103, C123 at their old place under DRV5"
W5 = "B.Cu 5V link through the new place of DRV5: re-drawn under the body"
WO = "copper of DRV5 at its old place east of the FET column"
WP = "old gate / bootstrap copper of the high side east of the column (C92, R26 moved; no VDDA on In2 any more)"
DEL = [
    (V15, B, 2.6, -49.3, 2.6, -51.2, W15), (V15, B, 2.6, -49.3, 6.6, -45.3, W15),
    (V15, B, 2.6, -51.2, 0.123, -53.677, W15), (V15, B, 6.6, -45.3, 8.6, -45.3, W15),
    (V15, B, 8.6, -45.3, 10.6, -43.3, W15), (V15, B, 15.231, -38.871, 10.802, -43.3, W15),
    (BIAS, B, 1.325, -54.4, 4.325, -51.4, WU), (BIAS, B, 4.5, -51.5, 4.5, -53.0, WU),
    (BIAS, I2, 4.5, -51.5, 1.5, -54.5, WU),
    (BIAS, B, 7.9, -49.7, 9.3, -48.3, WB), (BIAS, B, 9.3, -48.3, 9.3, -46.2, WB),
    (BIAS, B, 9.3, -46.2, 10.4, -45.1, WB), (BIAS, B, 10.4, -45.1, 11.424, -44.076, WB),
    (BIAS, B, 11.424, -44.076, 12.4, -44.076, WB),
    (BIAS, I2, 5.2, -54.5, 7.9, -51.8, WB), (BIAS, I2, 5.2, -58.8, 5.2, -54.5, WB),
    (BIAS, I2, 7.9, -51.8, 7.9, -49.7, WB),
    (UAP, B, 2.875, -54.389, 4.075, -54.389, WU), (UAP, B, 2.875, -54.4, 2.875, -54.389, WU),
    (UAP, B, 4.075, -54.389, 4.175, -54.489, WU), (UAP, B, 4.5, -54.727, 4.5, -56.0, WU),
    (V5, B, 3.6, -49.8, 4.33, -50.75, W5), (V5, B, 3.6, -49.8, 5.133, -48.267, W5),
    (V5, B, 5.133, -48.267, 7.266, -50.4, W5), (V5, B, 7.266, -50.4, 9.25, -50.4, W5),
    (V5, B, 9.0, -50.65, 9.25, -50.4, W5), (V5, B, 9.0, -51.825, 10.3, -51.825, W5),
    (V5, B, 9.0, -54.6, 9.0, -50.65, W5),
    (V5, B, 15.55, -51.94, 16.05, -51.94, WO), (V5, B, 15.55, -51.99, 15.55, -51.94, WO),
    (V5, B, 16.05, -51.94, 17.05, -52.94, WO), (V5, B, 17.05, -52.94, 17.05, -57.54, WO),
    (V5, B, 17.05, -57.54, 16.35, -58.24, WO),
    (DT, B, 12.15, -56.575, 13.45, -56.625, WO), (DT, B, 14.25, -56.525, 13.65, -56.525, WO),
    (DT, B, 14.95, -55.825, 14.25, -56.525, WO), (DT, B, 15.55, -55.8, 15.55, -55.825, WO),
    (DT, B, 15.55, -55.825, 14.95, -55.825, WO),
    (HS, B, 23.725, -60.9, 24.025, -60.6, WP),
    (VDDA, B, 26.875, -60.9, 26.913, -60.9, WP), (VDDA, B, 26.913, -60.9, 27.312, -61.3, WP),
    (VDDA, B, 27.312, -61.3, 27.312, -62.1, WP), (VDDA, I2, 27.312, -62.1, 24.913, -62.1, WP),
    (VDDA, I2, 24.913, -62.1, 23.312, -63.7, WP), (VDDA, B, 23.312, -63.7, 23.312, -63.1, WP),
    (VDDA, B, 23.312, -63.1, 21.812, -61.6, WP), (VDDA, B, 21.6, -61.0, 21.812, -61.6, WP),
    (VDDA, B, 21.6, -61.0, 21.6, -59.4, WP), (VDDA, B, 21.6, -59.4, 21.6, -58.5, WP),
    (VDDA, B, 21.6, -56.2, 21.6, -58.5, WP),
    (HG, B, 35.218, -52.6, 35.218, -53.318, WP), (HG, B, 36.017, -52.5, 35.517, -52.5, WP),
    (HG, B, 39.017, -49.5, 36.017, -52.5, WP), (HG, B, 39.049, -49.486, 39.017, -49.5, WP),
    (HG, B, 39.248, -49.486, 39.049, -49.486, WP), (HG, B, 39.248, -49.486, 39.502, -49.232, WP),
    (HG, B, 39.502, -49.232, 39.502, -47.708, WP),
    (QG, B, 39.502, -45.708, 40.81, -45.708, WP), (QG, B, 40.81, -45.708, 41.534, -45.708, WP),
]
DELVIA = [(BIAS, 4.5, -51.5, WU), (BIAS, 7.9, -49.7, WB), (BIAS, 12.4, -44.076, WB),
          (V5, 15.25, -51.99, WO), (GND, 23.25, -51.99, WO),
          (VDDA, 27.312, -62.1, WP), (VDDA, 23.312, -63.7, WP)]
# ref, x, y, rot, side ("F" / "B": flipped when it differs), why
MOVE = [
    ("DRV5", 2.3, -49.9, 0, "B", "west of the Q19 pins: outputs (pins 9-16) face the FET column at x 5.9-8.0"),
    ("R103", 3.3, -55.55, 180, "F", "was under the new body of DRV5; top side west of the heatsink strip (x < 5)"),
    ("C123", 3.3, -54.05, 0, "F", "was under the new body of DRV5; top side beside R103"),
    ("C94", -4.55, -48.63, 90, "B", "5V decoupling at pins 3 / 4 of DRV5 (input side, west of the pads)"),
    ("C92", 9.15, -46.525, -90, "B", "bootstrap capacitor directly on pins 16 / 14"),
    ("R26", 10.85, -46.0, -90, "B", "gate resistor between pin 15 and the gate pad of Q19"),
]
ADD = [
    # 5V: kept via (4.33, -50.75) of the west In2 feed -> pin 3 -> pin 8 under the body; C94 at pins 3 / 4
    ("t", V5, B, 0.3, [(4.33, -50.75), (1.575, -47.995), (-0.7, -47.995), (-2.35, -47.995)]),
    ("t", V5, B, 0.3, [(-0.7, -47.995), (-0.7, -54.345), (-2.35, -54.345)]),
    ("t", V5, B, 0.3, [(-2.35, -47.995), (-4.55, -47.855)]),
    ("t", GND, B, 0.3, [(-2.35, -49.265), (-4.55, -49.405), (-5.75, -49.405)]),
    ("v", GND, -5.75, -49.405, 0.5, 0.3),
    # 5V link of the east In2 lane (kept via (9.0, -54.6)) to the west feed: south of pin 9, then under the body
    ("t", V5, B, 0.25, [(9.0, -54.6), (9.0, -55.15), (5.6, -55.15), (5.2, -54.75), (5.2, -51.62), (4.33, -50.75)]),
    # U1A+ / bias of R103, C123 on the top side (via in pin 1 of R103 / R106, bias via on the In2 lane x 1.5)
    ("v", UAP, 4.3, -55.25, 0.5, 0.3),
    ("t", UAP, B, 0.2, [(4.3, -55.25), (4.461, -56.0)]),
    ("t", UAP, F, 0.2, [(4.3, -55.25), (4.125, -55.55)]),
    ("t", UAP, F, 0.2, [(4.125, -55.55), (4.075, -54.05)]),
    ("v", BIAS, 1.5, -54.9, 0.5, 0.3),
    ("t", BIAS, F, 0.2, [(1.5, -54.9), (2.475, -55.55)]),
    ("t", BIAS, F, 0.2, [(1.5, -54.9), (2.35, -54.05), (2.525, -54.05)]),
    # low side: GND of pin 9 to the planes
    ("v", GND, 8.25, -54.345, 0.5, 0.3),
    ("t", GND, B, 0.4, [(6.95, -54.345), (8.25, -54.345)]),
    # high side: bootstrap capacitor, gate resistor, source return west of the DC+ pad
    ("t", VDDA, B, 0.4, [(6.95, -45.455), (8.6, -45.2)]),
    ("t", HS, B, 0.5, [(6.95, -47.995), (9.15, -48.1)]),
    ("t", HS, B, 0.5, [(9.15, -48.1), (9.6, -48.5), (10.25, -49.15), (10.25, -51.5), (10.8, -52.06), (12.75, -52.06)]),
    ("t", HG, B, 0.4, [(6.95, -46.725), (9.9, -46.725), (10.4, -47.0), (10.85, -47.0)]),
    ("t", QG, B, 0.4, [(10.85, -45.0), (11.6, -45.0), (12.4, -45.8), (12.75, -46.98)]),
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
            print(f"s4g: {ref} pad {pad.GetNumber()} {pad.GetNetname()} at ({mm(q.x)}, {mm(q.y)})")
    pcbnew.SaveBoard(path, b)
    b = pcbnew.LoadBoard(path)
    lid = {b.GetLayerName(l): l for l in b.GetEnabledLayers().CuStack()}
    for a in ADD:
        code = b.GetNetcodeFromNetname(a[1])
        if code <= 0:
            sys.exit(f"s4g: no net {a[1]}")
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
    with open(os.path.join(os.path.dirname(path), "s4g.json"), "w") as f:
        json.dump(dict(deleted=DELETED, added=ADDED, moves=MOVES, warn=WARN), f)


def main(argv):
    if os.path.exists(LOCK):
        sys.exit("s4g: the board is open in KiCad; close it first")
    if os.path.exists(os.path.join(RT, "s4g_added.json")) and "--dry-run" not in argv:
        sys.exit("s4g: routing/s4g_added.json exists - this block is on the board already (not re-runnable)")
    tmp = tempfile.mkdtemp(prefix=".s4g_", dir=ROOT)
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
            sys.exit("s4g: edit failed, the board is unchanged")
        r = subprocess.run([CLI, "pcb", "drc", "--format", "json", "--refill-zones", "--save-board",
                            "-o", os.path.join(tmp, "refill.json"), pcb], capture_output=True, text=True)
        if r.returncode:
            sys.exit("s4g: zone refill failed, the board is unchanged\n" + r.stdout[-1500:] + r.stderr[-1500:])
        with open(os.path.join(tmp, "s4g.json")) as f:
            j = json.load(f)
        for w in j["warn"]:
            print("s4g: WARNING " + w)
        print(f"s4g: deleted {len(j['deleted'])}, added {len(j['added'])}, moved {len(j['moves'])}")
        if "--dry-run" in argv:
            out = os.path.abspath(argv[argv.index("--dry-run") + 1])
            shutil.copy(pcb, out)
            print(f"s4g: dry run in {out}, the board is unchanged")
            return 0
        shutil.copy(pcb, BOARD)
        note = "routing stage 4g (2026-11-22), tools/next/route_s4g_drv5.py - incremental edit of the board, not a rebuild"
        for name, key in (("deleted_s4g.json", "deleted"), ("s4g_added.json", "added"), ("moves_s4g.json", "moves")):
            with open(os.path.join(RT, name), "w") as f:
                json.dump({"note": note, key: j[key]}, f, indent=1)
        print("s4g: wrote the board and routing/*_s4g.json")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    if "--edit" in sys.argv:
        edit(sys.argv[sys.argv.index("--edit") + 1])
        sys.exit(0)
    sys.exit(main(sys.argv[1:]))
