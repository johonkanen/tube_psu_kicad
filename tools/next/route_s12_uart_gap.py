#!/usr/bin/env python3
"""Stage 12 (2026-11-23): wider gap between the UART nets TX and RX on the primary side, J2 - U11 (user decision:
12 Mbaud; see README "Stage 12").

    tools/p2k/bin/kipy tools/next/route_s12_uart_gap.py --group NAME[,NAME...] [--dry-run OUT.kicad_pcb] [--from PCB]

Incremental edit, same conventions and code as route_s8_c95_dc.py / route_s11_j4.py; NOT re-runnable (a group that
is listed in routing/s12_added.json is refused). Appends to kicad_next/routing/moves_s12.json, deleted_s12.json,
s12_added.json. Zones are refilled by kicad-cli.

Entries: ADD ("t", net, layer key, width, [points]) / ("v", net, x, y, pad, drill) / ("z", ...); DEL (net, layer key,
x0, y0, x1, y1, why); DELALL (net, layer key, why): every segment of the net on that layer; DELVIA (net, x, y, why);
MOVE / REPLACE as in stage 11.
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

TX, RX = "/04 MCU connector/TX", "/04 MCU connector/RX"
W = 0.152                       # track width as routed (stage 3b)
D = 0.76                        # centre distance of the pair = 0.608 mm edge to edge (was 0.34 on In3, 0.35 - 0.5 on B.Cu)


def r4(pts):
    return [(round(x, 4), round(y, 4)) for x, y in pts]


def meet(p, d, q, e):
    """intersection of the line through p with direction d and the line through q with direction e"""
    den = d[0] * e[1] - d[1] * e[0]
    t = ((q[0] - p[0]) * e[1] - (q[1] - p[1]) * e[0]) / den
    return (p[0] + t * d[0], p[1] + t * d[1])


def offset(pts, dist):
    """the polyline `pts` moved by `dist` to the side (dy, -dx) of its direction, corners mitred"""
    lines = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        dx, dy = x1 - x0, y1 - y0
        n = (dx * dx + dy * dy) ** 0.5
        lines.append(((x0 + dy / n * dist, y0 - dx / n * dist), (dx, dy)))
    out = [lines[0][0]]
    for (p, d), (q, e) in zip(lines, lines[1:]):
        out.append(meet(p, d, q, e))
    last = lines[-1]
    out.append((pts[-1][0] + last[0][0] - pts[-2][0], pts[-1][1] + last[0][1] - pts[-2][1]))
    return out


# In3, J2 end (east) to U11 end (north-west). TX keeps its line except (1) the first 6 mm: from its via north-west
# to y -28.45 and west there (was y -28.1, then a step south to y -27.54 beside the RX via: via 0.22 mm from the
# track, now 0.57 mm; the RX via cannot move south, +3V3 tracks on In2), and (2) the 45 degree step between
# y -32.02 and y -34.92, moved 4.23 mm east (x 8.3 ... 5.4, was 4.07 ... 1.17) so that RX, which goes round the
# outside, clears the gate pad of Q5 (pad 1, GATE1). North of y -32.02 TX cannot move: vias of Net-(DRV1-OUTL) /
# PFC_PWM1 at (9.40, -32.75) / (10.32, -32.79), 0.35 mm from the track. RX is the outer track everywhere (south,
# then west): it moves out by 0.42 mm - towards the +3V3 zone edge / C28 (x 15 ... 35) and towards pad 1 of L2
# (AC1, the 50 Hz side; TX stays where it was beside pad 2 = PFC_DRAIN_1). RX keeps y -27.2 on its first 5 mm.
TX3 = [(46.1, -28.1), (45.75, -28.45), (39.76, -28.45), (35.34, -32.87), (14.83, -32.87), (13.98, -32.02), (8.3, -32.02),
       (5.4, -34.92), (-7.83, -34.92), (-8.18, -35.27), (-8.18, -54.32), (-5.0, -57.5)]
RX_VIA_E = (45.3, -27.55)       # not moved
_o = offset(TX3[2:], D)
RX_VIA_W = (round(meet(_o[-1], (1, -1), (0, -57.5), (1, 0))[0], 4), -57.5)   # was (-5.75, -57.5); on the 45 degree line
RX3 = r4([RX_VIA_E, (44.95, -27.2), meet(_o[0], (1, 1), (0, -27.2), (1, 0))] + _o[1:-1] + [RX_VIA_W])
# B.Cu at J2: RX is the western track; its two north-south legs and the two 45 degree legs move out to the pitch D.
# The first 45 degree leg from the J2 pad was 0.78 mm from TX already.
_o = offset([(38.1, -9.6), (38.1, -11.8), (40.6, -14.3), (40.6, -19.5), (46.1, -25.0)], D)
RXB_E = r4([(34.4057, -8.1862), (35.5862, -8.1862), meet(_o[0], (0, 1), (35.5862, -8.1862), (1, -1))] + _o[1:-1]
           + [meet(_o[-1], (1, -1), (45.3, 0), (0, 1)), RX_VIA_E])
# B.Cu at U11: TX on x -5.2 (0.34 mm from the +3V3 track on x -4.68 at the island edge: cannot go east), RX on
# x -5.96 and round the WEST of the GND via of U11 pin 7 (-6.15, -74.83) - the lane between that via and the +3V3
# track is 1.07 mm, too narrow for two tracks 0.6 mm apart (was RX 0.22 mm from the via, 0.2 mm from TX).
XB = -5.2 - D
RXB_W = r4([RX_VIA_W, (XB, -57.5 - (XB - RX_VIA_W[0])), (XB, -73.0), (-6.85, -73.0 - (XB + 6.85)),
            (-6.85, -76.665), (-6.15, -77.365)])

GROUPS = {
    "gap": dict(DELALL=[
        (TX, I3, "re-drawn: y -28.45 at the J2 end, 45 degree step at L2 4.23 mm east"),
        (RX, I3, "re-drawn 0.76 mm from TX (was 0.34)"),
        (RX, B, "re-drawn 0.76 mm from TX (was 0.35 - 0.5), west of the GND via of U11 pin 7"),
    ], DELVIA=[
        (RX, -5.75, -57.5, "moved 0.32 mm west onto the new 45 degree line: 1.07 mm from the TX via"),
    ], ADD=[
        ("v", RX, RX_VIA_W[0], RX_VIA_W[1], 0.5, 0.3),
        ("t", TX, I3, W, TX3),
        ("t", RX, I3, W, RX3),
        ("t", RX, B, W, RXB_E),
        ("t", RX, B, W, RXB_W),
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
        for net, lay, why in G.get("DELALL", []):
            hit = [r for r in tracks if not r[1] and r[2] == net and r[3] == lid[LAYER[lay]]]
            if not hit:
                WARN.append(f"delall: no segment {net} {lay}")
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
        for ref, fpid, x, y, rot, to_side, why, *padnets in G.get("REPLACE", []):
            import reuse_51_board as R
            fp = b.FindFootprintByReference(ref)
            p = fp.GetPosition()
            side = "B" if fp.IsFlipped() else "F"
            if side != to_side:
                sys.exit("s12: no side changes in this stage")
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
            if padnets:                                  # new pinout / value / fields (as in the schematic)
                nets = {k: b.FindNet(v) for k, v in padnets[0]["pads"].items()}
                if any(v is None for v in nets.values()):
                    sys.exit("s12: REPLACE names a net that is not on the board")
                new.SetValue(padnets[0]["value"])
                for k, v in padnets[0]["fields"].items():
                    new.SetField(k, v)
            MOVES.append(dict(group=g, ref=ref, footprint=dict(frm=fp.GetFPIDAsString(), to=fpid),
                              frm=dict(x=mm(p.x), y=mm(p.y), rot=fp.GetOrientationDegrees(), side=side),
                              to=dict(x=x, y=y, rot=rot, side=to_side), why=why))
            for pad in new.Pads():
                pad.SetNet(nets[pad.GetNumber()])
                q = pad.GetPosition()
                print(f"s12: {ref} pad {pad.GetNumber()} {pad.GetNetname()} at ({mm(q.x)}, {mm(q.y)})")
            b.Delete(fp)
        for ref, x, y, rot, to_side, why in G.get("MOVE", []):
            fp = b.FindFootprintByReference(ref)
            p = fp.GetPosition()
            side = "B" if fp.IsFlipped() else "F"
            if side != to_side:
                sys.exit("s12: no side changes in this stage")
            MOVES.append(dict(group=g, ref=ref, frm=dict(x=mm(p.x), y=mm(p.y), rot=fp.GetOrientationDegrees(), side=side),
                              to=dict(x=x, y=y, rot=rot, side=to_side), why=why))
            fp.SetPosition(pcbnew.VECTOR2I(nm(x), nm(y)))
            fp.SetOrientationDegrees(rot)
            for pad in fp.Pads():
                q = pad.GetPosition()
                print(f"s12: {ref} pad {pad.GetNumber()} {pad.GetNetname()} at ({mm(q.x)}, {mm(q.y)})")
        for a in G.get("ADD", []):
            code = b.GetNetcodeFromNetname(a[1])
            if code <= 0:
                sys.exit(f"s12: no net {a[1]}")
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
                    sys.exit(f"s12: model zone {model} [{n}] not found")
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
    with open(os.path.join(os.path.dirname(path), "s12.json"), "w") as f:
        json.dump(dict(deleted=DELETED, added=ADDED, moves=MOVES, warn=WARN), f)


def main(argv):
    if os.path.exists(LOCK):
        sys.exit("s12: the board is open in KiCad; close it first")
    names = argv[argv.index("--group") + 1].split(",")
    files = (("deleted_s12.json", "deleted"), ("s12_added.json", "added"), ("moves_s12.json", "moves"))
    prev = {"deleted": [], "added": [], "moves": [], "groups": []}
    if os.path.exists(os.path.join(RT, "s12_added.json")):
        for name, key in files:
            with open(os.path.join(RT, name)) as f:
                d = json.load(f)
            prev[key] = d[key]
            prev["groups"] = d.get("groups", prev["groups"])
    dry = "--dry-run" in argv
    if not dry and any(g in prev["groups"] for g in names):
        sys.exit("s12: group already on the board (not re-runnable)")
    src = BOARD
    if "--from" in argv:                               # dry run on top of an earlier dry run
        src = os.path.abspath(argv[argv.index("--from") + 1])
    tmp = tempfile.mkdtemp(prefix=".s12_", dir=ROOT)
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
            sys.exit("s12: edit failed, the board is unchanged")
        r = subprocess.run([CLI, "pcb", "drc", "--format", "json", "--refill-zones", "--save-board",
                            "-o", os.path.join(tmp, "refill.json"), pcb], capture_output=True, text=True)
        if r.returncode:
            sys.exit("s12: zone refill failed, the board is unchanged\n" + r.stdout[-1500:] + r.stderr[-1500:])
        with open(os.path.join(tmp, "s12.json")) as f:
            j = json.load(f)
        for w in j["warn"]:
            print("s12: WARNING " + w)
        print(f"s12: {names}: deleted {len(j['deleted'])}, added {len(j['added'])}, moved {len(j['moves'])}")
        if dry:
            out = os.path.abspath(argv[argv.index("--dry-run") + 1])
            shutil.copy(pcb, out)
            print(f"s12: dry run in {out}, the board is unchanged")
            return 0
        shutil.copy(pcb, BOARD)
        note = "routing stage 12 (2026-11-23), tools/next/route_s12_uart_gap.py - incremental edit of the board, not a rebuild"
        for name, key in files:
            with open(os.path.join(RT, name), "w") as f:
                json.dump({"note": note, "groups": prev["groups"] + names, key: prev[key] + j[key]}, f, indent=1)
        print("s12: wrote the board and routing/*_s12.json")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    if "--print" in sys.argv:
        for k in ("TX3", "RX3", "RXB_E", "RXB_W", "RX_VIA_W"):
            print(k, globals()[k])
        sys.exit(0)
    if "--edit" in sys.argv:
        i = sys.argv.index("--edit")
        edit(sys.argv[i + 1], sys.argv[i + 2].split(","))
        sys.exit(0)
    sys.exit(main(sys.argv[1:]))
