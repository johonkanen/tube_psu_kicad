#!/usr/bin/env python3
"""Routing stage 5c of tube_power 5.2 (2026-11-22): the last three open connections (DHB_LOW_GATE_SEC, UART TX / RX)
(see README "Stage 5c").

    tools/p2k/bin/kipy tools/next/route_s5c_last.py --group NAME[,NAME...] [--dry-run OUT.kicad_pcb]

Incremental edit, same conventions as route_s4l_neck_toff.py; NOT re-runnable (a group that is listed in
routing/s5c_added.json is refused). The rebuild scripts stay frozen. Appends to kicad_next/routing/moves_s5c.json,
deleted_s5c.json, s5c_added.json. Zones are refilled by kicad-cli.

Entries: ADD ("t", net, layer key, width, [points]) / ("v", net, x, y, pad, drill); DEL (net, layer key, x0, y0, x1, y1,
why); DELVIA (net, x, y, why); MOVE (ref, x, y, rot, side, why).
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

def pair(pts, h):
    """Two lanes at -h / +h from a centre polyline (mitred corners). +h is the side n = (-dy, dx) of the direction."""
    out = []
    for sg in (-1, 1):
        lines = []
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            L = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
            dx, dy = (x1 - x0) / L, (y1 - y0) / L
            ox, oy = -dy * h * sg, dx * h * sg
            lines.append(((x0 + ox, y0 + oy), (dx, dy)))
        res = [lines[0][0]]
        for (p, d), (q, e) in zip(lines, lines[1:]):
            den = d[0] * e[1] - d[1] * e[0]
            t = ((q[0] - p[0]) * e[1] - (q[1] - p[1]) * e[0]) / den
            res.append((p[0] + d[0] * t, p[1] + d[1] * t))
        (x0, y0), (x1, y1) = pts[-2], pts[-1]
        p, d = lines[-1]
        res.append((p[0] + (x1 - x0), p[1] + (y1 - y0)))
        out.append([(round(x, 3), round(y, 3)) for x, y in res])
    return out


# centre line of the TX / RX pair on In3 (pitch 0.34 mm: RX is the -h lane = north / west, TX the +h lane)
UC = [(44.3, -27.37), (40.6, -27.37), (35.27, -32.7), (14.9, -32.7), (14.05, -31.85), (4.0, -31.85), (1.1, -34.75),
      (-7.9, -34.75), (-8.35, -35.2), (-8.35, -54.2)]
URX, UTX = pair(UC, 0.17)

LG, TX, RX = "DHB_LOW_GATE_SEC", "/04 MCU connector/TX", "/04 MCU connector/RX"
GROUPS = {
    # DRV6 pin 10 (low-side gate output, secondary) - D32 cathode / R87 (gate network of Q8). Pin 10 is closed in on
    # B.Cu (high-side group), F.Cu (DHB_HI_SOURCE_SEC track) and In2 (DAB_DIS_SEC / 5V_ISOL / ISO_GND lanes). Via east
    # of the pin, one 0.3 mm lane on In3 inside the 15V_ISO_SEC plane (the fill gives way; the plane stays in one
    # piece round both ends), between TR3 pins 9 and 10, via south of D32, B.Cu into the cathode pad.
    "lowgate": dict(ADD=[
        ("t", LG, B, 0.3, [(56.357, -53.832), (58.3, -53.832)]),
        ("v", LG, 58.3, -53.832, 0.6, 0.3),
        ("t", LG, I3, 0.3, [(58.3, -53.832), (58.568, -54.1), (71.0, -54.1), (72.5, -52.6), (72.5, -50.3)]),
        ("v", LG, 72.5, -50.3, 0.6, 0.3),
        ("t", LG, B, 0.3, [(72.5, -50.3), (73.3, -49.5), (73.3, -48.45), (73.73, -48.02)]),
    ]),
    # UART TX / RX: 5.1 B.Cu ends at (40.6, -19.5) / (40.1, -19.503) - U11 pins 4 / 5. B.Cu south-east (RX stub of 5.1
    # cut back), vias south of the In2 +3V3 lane, In3 pair (no pour of another net on the way: gap 5V / 15V planes,
    # corridor y -32.7 between the +3V3 plane and the 15V band, between the two pads of L2, x -8.35 west of the DRV5
    # input parts, under the In2 control bus), vias south of the bus (in the F.Cu DC+ pour, which gives way), B.Cu
    # between the 15V track x -6.75 and the +3V3 track x -4.68, vias west of the pins, F.Cu to the pins.
    "uart": dict(DEL=[
        (RX, B, 40.1, -19.503, 48.66, -28.063, "5.1 stub towards the old place of ISO2, cut back to the new via"),
    ], ADD=[
        ("t", RX, B, 0.152, [(40.1, -19.503), (45.3, -24.703), (45.3, -27.55)]),
        ("t", TX, B, 0.152, [(40.6, -19.5), (46.1, -25.0), (46.1, -28.1)]),
        ("v", RX, 45.3, -27.55, 0.5, 0.3),
        ("v", TX, 46.1, -28.1, 0.5, 0.3),
        ("t", RX, I3, 0.152, [(45.3, -27.55), (44.95, -27.2)] + URX + [(-8.52, -54.73), (-5.75, -57.5)]),
        ("t", TX, I3, 0.152, [(46.1, -28.1), (44.86, -28.1)] + UTX + [(-8.18, -54.32), (-5.0, -57.5)]),
        ("v", RX, -5.75, -57.5, 0.5, 0.3),
        ("v", TX, -5.0, -57.5, 0.5, 0.3),
        ("t", RX, B, 0.152, [(-5.75, -57.5), (-5.55, -57.7), (-5.55, -76.765), (-6.15, -77.365)]),
        ("t", TX, B, 0.152, [(-5.0, -57.5), (-5.2, -57.7), (-5.2, -78.035), (-5.8, -78.635), (-6.15, -78.635)]),
        ("v", RX, -6.15, -77.365, 0.5, 0.3),
        ("v", TX, -6.15, -78.635, 0.5, 0.3),
        ("t", RX, F, 0.2, [(-6.15, -77.365), (-4.65, -77.365)]),
        ("t", TX, F, 0.2, [(-6.15, -78.635), (-4.65, -78.635)]),
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
        for net, x, y, why in G.get("DELVIA", []):
            hit = [r for r in tracks if r[1] and r[2] == net and near(r[4], x, y)]
            if not hit:
                WARN.append(f"delvia: no via {net} ({x}, {y})")
            for r in hit:
                DELETED.append(dict(group=g, kind="via", net=net, at=[x, y], why=why))
                b.Delete(r[0])
                tracks.remove(r)
        for ref, x, y, rot, to_side, why in G.get("MOVE", []):
            fp = b.FindFootprintByReference(ref)
            p = fp.GetPosition()
            side = "B" if fp.IsFlipped() else "F"
            if side != to_side:
                sys.exit("s5c: no side changes in this stage")
            MOVES.append(dict(group=g, ref=ref, frm=dict(x=mm(p.x), y=mm(p.y), rot=fp.GetOrientationDegrees(), side=side),
                              to=dict(x=x, y=y, rot=rot, side=to_side), why=why))
            fp.SetPosition(pcbnew.VECTOR2I(nm(x), nm(y)))
            fp.SetOrientationDegrees(rot)
            for pad in fp.Pads():
                q = pad.GetPosition()
                print(f"s5c: {ref} pad {pad.GetNumber()} {pad.GetNetname()} at ({mm(q.x)}, {mm(q.y)})")
        for a in G.get("ADD", []):
            code = b.GetNetcodeFromNetname(a[1])
            if code <= 0:
                sys.exit(f"s5c: no net {a[1]}")
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
    with open(os.path.join(os.path.dirname(path), "s5c.json"), "w") as f:
        json.dump(dict(deleted=DELETED, added=ADDED, moves=MOVES, warn=WARN), f)


def main(argv):
    if os.path.exists(LOCK):
        sys.exit("s5c: the board is open in KiCad; close it first")
    names = argv[argv.index("--group") + 1].split(",")
    files = (("deleted_s5c.json", "deleted"), ("s5c_added.json", "added"), ("moves_s5c.json", "moves"))
    prev = {"deleted": [], "added": [], "moves": [], "groups": []}
    if os.path.exists(os.path.join(RT, "s5c_added.json")):
        for name, key in files:
            with open(os.path.join(RT, name)) as f:
                d = json.load(f)
            prev[key] = d[key]
            prev["groups"] = d.get("groups", prev["groups"])
    dry = "--dry-run" in argv
    if not dry and any(g in prev["groups"] for g in names):
        sys.exit("s5c: group already on the board (not re-runnable)")
    src = BOARD
    if "--from" in argv:                               # dry run on top of an earlier dry run
        src = os.path.abspath(argv[argv.index("--from") + 1])
    tmp = tempfile.mkdtemp(prefix=".s5c_", dir=ROOT)
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
            sys.exit("s5c: edit failed, the board is unchanged")
        r = subprocess.run([CLI, "pcb", "drc", "--format", "json", "--refill-zones", "--save-board",
                            "-o", os.path.join(tmp, "refill.json"), pcb], capture_output=True, text=True)
        if r.returncode:
            sys.exit("s5c: zone refill failed, the board is unchanged\n" + r.stdout[-1500:] + r.stderr[-1500:])
        with open(os.path.join(tmp, "s5c.json")) as f:
            j = json.load(f)
        for w in j["warn"]:
            print("s5c: WARNING " + w)
        print(f"s5c: {names}: deleted {len(j['deleted'])}, added {len(j['added'])}, moved {len(j['moves'])}")
        if dry:
            out = os.path.abspath(argv[argv.index("--dry-run") + 1])
            shutil.copy(pcb, out)
            print(f"s5c: dry run in {out}, the board is unchanged")
            return 0
        shutil.copy(pcb, BOARD)
        note = "routing stage 5c (2026-11-22), tools/next/route_s5c_last.py - incremental edit of the board, not a rebuild"
        for name, key in files:
            with open(os.path.join(RT, name), "w") as f:
                json.dump({"note": note, "groups": prev["groups"] + names, key: prev[key] + j[key]}, f, indent=1)
        print("s5c: wrote the board and routing/*_s5c.json")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    if "--edit" in sys.argv:
        i = sys.argv.index("--edit")
        edit(sys.argv[i + 1], sys.argv[i + 2].split(","))
        sys.exit(0)
    sys.exit(main(sys.argv[1:]))
