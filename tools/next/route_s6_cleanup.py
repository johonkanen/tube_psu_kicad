#!/usr/bin/env python3
"""Clean-up pass (stage 6) of the first complete draft of tube_power 5.2 (2026-11-22): clearance markers and
dangling track ends (see README "First draft (2026-11-22)").

    tools/p2k/bin/kipy tools/next/route_s6_cleanup.py --group NAME[,NAME...] [--dry-run OUT.kicad_pcb]

Incremental edit, same conventions as route_s4l_neck_toff.py; NOT re-runnable (a group that is listed in
routing/s6_added.json is refused). The rebuild scripts stay frozen. Appends to kicad_next/routing/moves_s6.json,
deleted_s6.json, s6_added.json. Zones are refilled by kicad-cli.

Entries: ADD ("t", net, layer key, width, [points]) / ("v", net, x, y, pad, drill); DEL (net, layer key, x0, y0, x1, y1,
why); DELVIA (net, x, y, why); MOVE (ref, x, y, rot, side, why); PRUNE (net, layer key, x, y) = delete the stub
that ends free at (x, y) back to the next junction (see prune()).
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
    # A: the five clearance markers (net class gap 0.2 mm, 0.16 ... 0.175 mm on the board)
    "clr": dict(DEL=[
        ("EPWM5A_ISO", I2, -50.9, -54.947, -48.937, -54.947, "diagonal 0.09 mm further from the EPWM6A_ISO via"),
        ("EPWM5A_ISO", I2, -48.937, -54.947, -48.2, -54.21, "diagonal 0.09 mm further from the EPWM6A_ISO via"),
        ("EPWM5A_ISO", I2, -48.2, -54.21, -48.2, -53.605, "diagonal 0.09 mm further from the EPWM6A_ISO via"),
        ("5V", B, -59.7, -37.649, -59.7, -25.585, "0.045 mm west past the pads of D9 and D28 pad A (y -33.0 ... -26.5)"),
        ("Net-(C11-Pad1)", F, 28.4, 7.7, 29.7, 7.7, "via 0.05 mm east (gap to the +1V65_BIAS diagonal)"),
        ("Net-(C11-Pad1)", I2, 29.3, 7.7, 28.4, 7.7, "via 0.05 mm east (gap to the +1V65_BIAS diagonal)"),
    ], DELVIA=[
        ("GND", 27.1, 5.1, "0.05 mm east (gap to the PFC_PWM2 track x 26.6)"),
        ("Net-(C11-Pad1)", 28.4, 7.7, "0.05 mm east (gap to the +1V65_BIAS diagonal)"),
        ("GND", 4.45, -56.9, "0.05 mm south (gap to R106 pad 1)"),
    ], ADD=[
        ("t", "EPWM5A_ISO", I2, 0.152, [(-50.9, -54.947), (-48.85, -54.947), (-48.2, -54.297), (-48.2, -53.605)]),
        ("t", "5V", B, 0.152, [(-59.7, -37.649), (-59.7, -33.0), (-59.745, -32.955), (-59.745, -26.5), (-59.7, -26.455),
                               (-59.7, -25.585)]),
        ("v", "GND", 27.15, 5.1, 0.5, 0.3),
        ("t", "GND", F, 0.152, [(27.1, 5.1), (27.15, 5.1)]),
        ("v", "Net-(C11-Pad1)", 28.45, 7.7, 0.5, 0.3),
        ("t", "Net-(C11-Pad1)", F, 0.152, [(28.45, 7.7), (29.7, 7.7)]),
        ("t", "Net-(C11-Pad1)", I2, 0.203, [(29.3, 7.7), (28.45, 7.7)]),
        ("v", "GND", 4.45, -56.95, 0.5, 0.3),
    ]),
    # B: dangling track ends. DEL = copper that lies under / inside another track of its net (5.1 leftovers, zero
    # length pieces) or overshoots; PRUNE = a stub that ends in nothing, deleted back to the next junction / pad /
    # via with a second layer / zone fill; trimmed tracks are DEL + ADD.
    "dangling": dict(DEL=[
        ("DC+", F, 41.961, 16.944, 41.95, 16.944, "0.011 mm piece inside the two tracks at (41.95, 16.944)"),
        ("GATE1", B, 3.753, -29.576, 6.3, -29.576, "lies under the 0.4 mm track (3.753 ... 6.753, -29.576)"),
        ("GATE1", B, 6.3, -29.126, 7.124, -29.95, "trimmed to the end of the 0.4 mm track (0.64 mm overshoot north-west)"),
        ("HEATER_CURRENT", B, -11.2, -80.4, -11.2, -79.1, "lies under the 0.8 mm track x -11.2"),
        ("HEATER_CURRENT", I2, -1.5, -66.0, 0.4, -64.1, "lies under the 0.2 mm track, 0.28 mm overshoot"),
        ("15V", F, 15.259, -33.137, 15.24, -33.156, "0.027 mm piece at the end of the track x 15.24"),
        ("15V", B, 14.2, -36.233, 10.809, -36.233, "stub west of the via (13.67, -36.28); C79 pad 1 - via is the 0.4 mm track"),
        ("15V", B, 14.67, -36.278, 14.2, -36.233, "inside C79 pad 1 / the 0.4 mm track"),
        ("15V", B, -7.412, -67.702, -7.412, -64.726, "lies under the 0.4 mm track x -7.41"),
        ("5V_ISOL", F, 73.898, -35.211, 73.898, -35.211, "zero-length segment"),
        ("5V_ISOL", I2, 74.808, -47.962, 73.538, -47.962, "0.762 mm piece over the 0.3 mm lane y -48.0"),
        ("5V", I2, -23.9, -48.089, -21.011, -48.089, "lies under the 0.3 mm track y -48.09, 0.9 mm overshoot"),
        ("+1V65_BIAS", I2, 1.5, -54.5, 1.5, -60.8, "trimmed to the via (1.5, -54.9)"),
        ("EPWM5A_ISO", I2, -53.3, -65.1, -53.3, -64.1, "trimmed to the junction with the 0.4 mm track y -64.475"),
        ("Net-(DRV3-VDDA)", B, -23.9, -56.1, -19.4, -56.1, "4.5 mm x 0.762 mm stub to nothing off the end of the 0.4 mm track"),
        ("Net-(DRV3-VDDA)", B, -16.6, -58.699, -19.1, -56.199, "stub to nothing (5.1 leftover) from the pin 16 track"),
        ("DC+", F, 45.62, -41.95, 45.62, -44.6, "trimmed: the end stood in a round hole of 'Proteus F.Cu pour 29' (5.1 pad place), now it ends in the fill"),
        ("15V", F, 15.24, -33.156, 15.24, -35.018, "1.9 mm stub to nothing north of the via (15.24, -35.02)"),
        ("15V", F, 15.24, -35.018, 15.259, -35.037, "0.027 mm piece inside that via"),
        ("15V", B, -7.41, -67.7, -7.41, -63.3, "4.4 mm stub to nothing south of the via (-7.24, -62.24)"),
        ("15V", B, -7.41, -63.3, -7.21, -63.1, "4.4 mm stub to nothing south of the via (-7.24, -62.24)"),
        ("15V", B, -7.239, -62.235, -7.239, -63.119, "4.4 mm stub to nothing south of the via (-7.24, -62.24)"),
        ("5V_ISOL", F, 73.898, -35.211, 73.898, -38.0, "trimmed to the via (73.5, -37.3): 2.1 mm stub to nothing north of it"),
        ("5V", B, -23.3, -53.0, -23.2, -53.1, "rest of the stub from the via (-23.9, -53.036)"),
        ("5V", B, -23.3, -53.036, -23.3, -53.0, "rest of the stub from the via (-23.9, -53.036)"),
        ("5V", B, -23.3, -53.036, -23.9, -53.036, "rest of the stub from the via (-23.9, -53.036)"),
        ("5V", I2, -23.9, -53.036, -23.9, -48.089, "In2 lane to the via (-23.9, -53.036), which only fed the B.Cu stub"),
        ("HT_GND", B, -48.28, -59.29, -48.28, -59.875, "0.58 mm stub to nothing north of the junction"),
        ("15V", F, 13.156, 12.997, 11.256, 12.997, "1.9 mm stub to nothing west of the via (12.96, 13.14)"),
        ("Net-(AD1-SDATA)", B, -48.128, -57.487, -48.128, -58.02, "0.53 mm stub to nothing south of the via"),
        ("Net-(DRV2-OUTL)", B, 11.943, 6.657, 13.222, 5.378, "1.8 mm stub to nothing (the old place of R20)"),
    ], DELVIA=[
        ("15V", 15.24, -35.02, "only fed the F.Cu stub to nothing (connected on one layer after the stub is gone)"),
        ("5V", -23.9, -53.036, "only fed the B.Cu stub to nothing"),
    ], ADD=[
        ("t", "GATE1", B, 0.152, [(6.753, -29.576), (7.124, -29.95)]),
        ("t", "DC+", F, 0.75, [(45.62, -42.7), (45.62, -44.6)]),
        ("t", "5V_ISOL", F, 0.762, [(73.898, -37.3), (73.898, -38.0)]),
        ("t", "+1V65_BIAS", I2, 0.152, [(1.5, -54.9), (1.5, -60.8)]),
        ("t", "EPWM5A_ISO", I2, 0.152, [(-53.3, -64.475), (-53.3, -64.1)]),
    ], PRUNE=[
        ("15V", B, -10.074, -62.435), ("+3V3", I2, 7.2, -58.1), ("+3V3", I2, 16.8, -48.4), ("+3V3", I2, 6.6, -60.4),
        ("5V", B, -20.9, -53.1), ("PFC_PWM2", B, 14.1, 14.9),
    ]),
}


def prune(b, layer, net, x, y, g, DELETED, WARN):
    """Delete the stub of `net` that ends free at (x, y) on `layer`, segment by segment, back to the first point
    where anything else of the net touches (track junction, pad, zone fill, via that still joins two layers).
    A via left with copper on one layer only is deleted too and the walk goes on. Stops (warning) if another
    item touches a segment anywhere but at its far end."""
    code = b.GetNetcodeFromNetname(net)
    cu = list(b.GetEnabledLayers().CuStack())
    zones = [z for z in b.Zones() if not z.GetIsRuleArea() and z.GetNetCode() == code]
    pads = [p for fp in b.GetFootprints() for p in fp.Pads() if p.GetNetCode() == code]
    P = pcbnew.VECTOR2I(nm(x), nm(y))
    why = f"stub of {net} that ended in nothing at ({x}, {y})"

    def touching(shape, lay, skip):
        out = []
        for o in b.GetTracks():
            if o.GetNetCode() != code or any(o.m_Uuid == s.m_Uuid for s in skip):
                continue
            via = o.Type() == pcbnew.PCB_VIA_T
            if not via and o.GetLayer() != lay:
                continue
            if shape.Collide(o.GetEffectiveShape(lay) if via else o.GetEffectiveShape(), 0):
                out.append(o)
        out += [p for p in pads if p.IsOnLayer(lay) and shape.Collide(p.GetEffectiveShape(lay), 0)]
        return out

    def filled(lay, pt):
        return any(z.IsOnLayer(lay) and z.HitTestFilledArea(lay, pt, 0) for z in zones)

    while True:
        segs = [t for t in b.GetTracks() if t.Type() != pcbnew.PCB_VIA_T and t.GetNetCode() == code and t.GetLayer() == layer
                and (abs(t.GetStart().x - P.x) + abs(t.GetStart().y - P.y) <= 10000
                     or abs(t.GetEnd().x - P.x) + abs(t.GetEnd().y - P.y) <= 10000)]
        if len(segs) != 1:
            WARN.append(f"prune {net} at ({mm(P.x)}, {mm(P.y)}): {len(segs)} segments end here, stopped")
            return
        t = segs[0]
        s, e = t.GetStart(), t.GetEnd()
        near_s = abs(s.x - P.x) + abs(s.y - P.y) <= 10000
        far = pcbnew.VECTOR2I(e.x, e.y) if near_s else pcbnew.VECTOR2I(s.x, s.y)
        others = touching(t.GetEffectiveShape(), layer, [t])
        if filled(layer, P) or any(o.HitTest(P, 0) for o in others):
            WARN.append(f"prune {net} at ({mm(P.x)}, {mm(P.y)}): the end is not free, stopped")
            return
        if any(z.IsOnLayer(layer) and z.GetFilledPolysList(layer).Collide(t.GetEffectiveShape(), 0) for z in zones):
            WARN.append(f"prune {net} ({mm(s.x)}, {mm(s.y)}) - ({mm(e.x)}, {mm(e.y)}): runs through a zone fill of the net, stopped")
            return
        if any(not o.HitTest(far, 0) for o in others):
            WARN.append(f"prune {net} ({mm(s.x)}, {mm(s.y)}) - ({mm(e.x)}, {mm(e.y)}): touched away from its far end, stopped")
            return
        DELETED.append(dict(group=g, kind="segment", net=net, layer=b.GetLayerName(layer), start=[mm(s.x), mm(s.y)],
                            end=[mm(e.x), mm(e.y)], width=mm(t.GetWidth()), why=why))
        b.Delete(t)
        if filled(layer, far):
            return
        vias = [o for o in others if o.Type() == pcbnew.PCB_VIA_T]
        if vias and len(others) == 1:
            v = vias[0]
            on = [l for l in cu if filled(l, v.GetPosition()) or touching(v.GetEffectiveShape(l), l, [v])]
            if len(on) >= 2:
                return
            p = v.GetPosition()
            DELETED.append(dict(group=g, kind="via", net=net, at=[mm(p.x), mm(p.y)], why=why + " (via left on one layer)"))
            P = pcbnew.VECTOR2I(p.x, p.y)
            b.Delete(v)
            if not on:
                return
            layer = on[0]
            continue
        if len(others) != 1 or others[0].Type() != pcbnew.PCB_TRACE_T:
            return
        P = far


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
        for net, lay, x, y in G.get("PRUNE", []):
            prune(b, lid[LAYER[lay]], net, x, y, g, DELETED, WARN)
        for ref, x, y, rot, to_side, why in G.get("MOVE", []):
            fp = b.FindFootprintByReference(ref)
            p = fp.GetPosition()
            side = "B" if fp.IsFlipped() else "F"
            if side != to_side:
                sys.exit("s6: no side changes in this stage")
            MOVES.append(dict(group=g, ref=ref, frm=dict(x=mm(p.x), y=mm(p.y), rot=fp.GetOrientationDegrees(), side=side),
                              to=dict(x=x, y=y, rot=rot, side=to_side), why=why))
            fp.SetPosition(pcbnew.VECTOR2I(nm(x), nm(y)))
            fp.SetOrientationDegrees(rot)
            for pad in fp.Pads():
                q = pad.GetPosition()
                print(f"s6: {ref} pad {pad.GetNumber()} {pad.GetNetname()} at ({mm(q.x)}, {mm(q.y)})")
        for a in G.get("ADD", []):
            code = b.GetNetcodeFromNetname(a[1])
            if code <= 0:
                sys.exit(f"s6: no net {a[1]}")
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
    with open(os.path.join(os.path.dirname(path), "s6.json"), "w") as f:
        json.dump(dict(deleted=DELETED, added=ADDED, moves=MOVES, warn=WARN), f)


def main(argv):
    if os.path.exists(LOCK):
        sys.exit("s6: the board is open in KiCad; close it first")
    names = argv[argv.index("--group") + 1].split(",")
    files = (("deleted_s6.json", "deleted"), ("s6_added.json", "added"), ("moves_s6.json", "moves"))
    prev = {"deleted": [], "added": [], "moves": [], "groups": []}
    if os.path.exists(os.path.join(RT, "s6_added.json")):
        for name, key in files:
            with open(os.path.join(RT, name)) as f:
                d = json.load(f)
            prev[key] = d[key]
            prev["groups"] = d.get("groups", prev["groups"])
    dry = "--dry-run" in argv
    if not dry and any(g in prev["groups"] for g in names):
        sys.exit("s6: group already on the board (not re-runnable)")
    src = BOARD
    if "--from" in argv:                               # dry run on top of an earlier dry run
        src = os.path.abspath(argv[argv.index("--from") + 1])
    tmp = tempfile.mkdtemp(prefix=".s6_", dir=ROOT)
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
            sys.exit("s6: edit failed, the board is unchanged")
        r = subprocess.run([CLI, "pcb", "drc", "--format", "json", "--refill-zones", "--save-board",
                            "-o", os.path.join(tmp, "refill.json"), pcb], capture_output=True, text=True)
        if r.returncode:
            sys.exit("s6: zone refill failed, the board is unchanged\n" + r.stdout[-1500:] + r.stderr[-1500:])
        with open(os.path.join(tmp, "s6.json")) as f:
            j = json.load(f)
        for w in j["warn"]:
            print("s6: WARNING " + w)
        print(f"s6: {names}: deleted {len(j['deleted'])}, added {len(j['added'])}, moved {len(j['moves'])}")
        if dry:
            out = os.path.abspath(argv[argv.index("--dry-run") + 1])
            shutil.copy(pcb, out)
            print(f"s6: dry run in {out}, the board is unchanged")
            return 0
        shutil.copy(pcb, BOARD)
        note = "routing stage 6 (2026-11-22), tools/next/route_s6_cleanup.py - incremental edit of the board, not a rebuild"
        for name, key in files:
            with open(os.path.join(RT, name), "w") as f:
                json.dump({"note": note, "groups": prev["groups"] + names, key: prev[key] + j[key]}, f, indent=1)
        print("s6: wrote the board and routing/*_s6.json")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    if "--edit" in sys.argv:
        i = sys.argv.index("--edit")
        edit(sys.argv[i + 1], sys.argv[i + 2].split(","))
        sys.exit(0)
    sys.exit(main(sys.argv[1:]))
