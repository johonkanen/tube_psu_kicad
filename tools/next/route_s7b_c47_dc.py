#!/usr/bin/env python3
"""Stage 7b (2026-11-22): short, wide DC+ connection from the DAB bridge (Q19 / C67 / C70) to C47 on B.Cu; C95 and
the DHB_CURRENT link of R146 moved out of its way (see README "Stage 7b").

    tools/p2k/bin/kipy tools/next/route_s7b_c47_dc.py --group NAME[,NAME...] [--dry-run OUT.kicad_pcb] [--from PCB]

Incremental edit, same conventions and code as route_s7_fixes.py; NOT re-runnable (a group that is listed in
routing/s7b_added.json is refused). Appends to kicad_next/routing/moves_s7b.json, deleted_s7b.json, s7b_added.json.
Zones are refilled by kicad-cli.

Entries: ADD ("t", net, layer key, width, [points]) / ("v", net, x, y, pad, drill) / ("z", net, layer key, name,
model zone name, [outline points]); DEL (net, layer key, x0, y0, x1, y1, why); DELVIA (net, x, y, why);
MOVE (ref, x, y, rot, side, why).
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

C95_ROT = -90.0

GROUPS = {
    # 1: C95 off the B.Cu way south of C70 pad 1. The In3 15V bridge starts in the In3 east block at (24.0, -50.4), so
    # the via (17.625, -51.0) and its In2 branch were only a second feed and the pad of C95: all deleted. C95 stands
    # south of the F.Cu switch-node zone, 15V via in pad on a new In3 spur of the bridge, own GND via.
    "c95": dict(DELVIA=[
        ("15V", 17.625, -51.0, "In2 -> In3 change at the old C95 pad; in the way of DC+ on B.Cu"),
        ("GND", 20.4, -50.65, "GND via of C95 at its old place"),
    ], DEL=[
        ("15V", B, 17.625, -51.0, 17.637, -51.6, "C95 pad stub"),
        ("15V", I3, 17.625, -51.6, 17.625, -51.0, "In3 stub to the deleted via"),
        ("15V", I2, 22.225, -46.4, 17.625, -51.0, "In2 branch that only fed the deleted via"),
        ("15V", I2, 22.225, -44.726, 22.225, -46.4, "same"),
        ("15V", I2, 23.561, -43.39, 22.225, -44.726, "same"),
        ("15V", I2, 24.897, -43.39, 23.561, -43.39, "same"),
        ("GND", B, 20.762, -51.6, 20.4, -50.65, "C95 GND stub"),
    ], MOVE=[
        ("C95", 18.9, -60.6, C95_ROT, "B", "out of the B.Cu DC+ path; 15V pad north on a new In3 spur, GND pad south"),
    ], ADD=[
        ("t", "15V", I3, 1.0, [(17.125, -55.25), (18.9, -57.025), (18.9, -58.85)]),
        ("v", "15V", 18.9, -58.85, 0.6, 0.3),
        ("v", "GND", 18.9, -61.7, 0.6, 0.3),
    ]),
    # 2: DHB_CURRENT to R146 pad 2 ran on B.Cu at x 25.28 in the middle of the corridor: via and track 1.57 mm east
    # (1.25 mm from the TR3 pads 4 / 5).
    "r146": dict(DELVIA=[
        ("DHB_CURRENT", 25.28, -63.68, "moved east, see ADD"),
    ], DEL=[
        ("DHB_CURRENT", F, 25.28, -63.68, 25.28, -61.78, "to the moved via"),
        ("DHB_CURRENT", B, 25.28, -73.88, 25.28, -63.68, "in the DC+ corridor"),
        ("DHB_CURRENT", B, 25.68, -74.28, 25.28, -73.88, "same"),
        ("DHB_CURRENT", B, 25.712, -74.28, 25.68, -74.28, "same"),
    ], ADD=[
        ("v", "DHB_CURRENT", 26.85, -62.3, 0.6, 0.3),
        ("t", "DHB_CURRENT", F, 0.4, [(26.85, -62.3), (25.2, -61.3)]),
        ("t", "DHB_CURRENT", B, 0.4, [(26.85, -62.3), (26.85, -73.0), (25.9, -73.95), (25.712, -74.28)]),
    ]),
    # 3: DC+ on B.Cu: C70 pad 1 -> south 2.0 mm -> diagonal and south 2.5 mm -> three vias between the pads of C47
    # (B.Cu 1.25 mm north of the R146 pads) -> F.Cu bar into the north edge of C47 pad 1. Two more vias 0.8 / 0.4
    # F.Cu pour <-> B.Cu south of the C67 / C70 pads.
    "dc": dict(ADD=[
        ("v", "DC+", 17.7, -50.0, 0.8, 0.4),
        ("v", "DC+", 18.7, -50.0, 0.8, 0.4),
        ("t", "DC+", B, 2.0, [(18.3, -49.0), (18.3, -51.2)]),
        ("t", "DC+", B, 2.5, [(18.3, -51.2), (23.85, -56.75), (23.85, -70.9)]),
        ("v", "DC+", 22.95, -71.75, 0.8, 0.4),
        ("v", "DC+", 23.85, -71.75, 0.8, 0.4),
        ("v", "DC+", 24.75, -71.75, 0.8, 0.4),
        ("t", "DC+", F, 2.2, [(23.35, -72.5), (24.9, -72.5)]),
    ]),
    # 4: the old feed (89 mm, 0.75 ... 1.5 mm) from pour 29 at (45.62, -42.7) round the east of TR3's primary pins
    "old": dict(DEL=[
        ("DC+", F, 45.62, -42.7, 45.62, -44.6, "old long feed of C47, replaced by the B.Cu path"),
        ("DC+", F, 45.62, -44.6, 45.62, -47.3, "same"),
        ("DC+", F, 45.62, -47.3, 41.5, -47.3, "same"),
        ("DC+", F, 41.5, -47.3, 41.5, -75.21, "same"),
        ("DC+", F, 41.5, -75.21, 23.83, -75.21, "same"),
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
                sys.exit("s7b: no side changes in this stage")
            MOVES.append(dict(group=g, ref=ref, frm=dict(x=mm(p.x), y=mm(p.y), rot=fp.GetOrientationDegrees(), side=side),
                              to=dict(x=x, y=y, rot=rot, side=to_side), why=why))
            fp.SetPosition(pcbnew.VECTOR2I(nm(x), nm(y)))
            fp.SetOrientationDegrees(rot)
            for pad in fp.Pads():
                q = pad.GetPosition()
                print(f"s7b: {ref} pad {pad.GetNumber()} {pad.GetNetname()} at ({mm(q.x)}, {mm(q.y)})")
        for a in G.get("ADD", []):
            code = b.GetNetcodeFromNetname(a[1])
            if code <= 0:
                sys.exit(f"s7b: no net {a[1]}")
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
                    sys.exit(f"s7b: model zone {model} [{n}] not found")
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
    with open(os.path.join(os.path.dirname(path), "s7b.json"), "w") as f:
        json.dump(dict(deleted=DELETED, added=ADDED, moves=MOVES, warn=WARN), f)


def main(argv):
    if os.path.exists(LOCK):
        sys.exit("s7b: the board is open in KiCad; close it first")
    names = argv[argv.index("--group") + 1].split(",")
    files = (("deleted_s7b.json", "deleted"), ("s7b_added.json", "added"), ("moves_s7b.json", "moves"))
    prev = {"deleted": [], "added": [], "moves": [], "groups": []}
    if os.path.exists(os.path.join(RT, "s7b_added.json")):
        for name, key in files:
            with open(os.path.join(RT, name)) as f:
                d = json.load(f)
            prev[key] = d[key]
            prev["groups"] = d.get("groups", prev["groups"])
    dry = "--dry-run" in argv
    if not dry and any(g in prev["groups"] for g in names):
        sys.exit("s7b: group already on the board (not re-runnable)")
    src = BOARD
    if "--from" in argv:                               # dry run on top of an earlier dry run
        src = os.path.abspath(argv[argv.index("--from") + 1])
    tmp = tempfile.mkdtemp(prefix=".s7b_", dir=ROOT)
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
            sys.exit("s7b: edit failed, the board is unchanged")
        r = subprocess.run([CLI, "pcb", "drc", "--format", "json", "--refill-zones", "--save-board",
                            "-o", os.path.join(tmp, "refill.json"), pcb], capture_output=True, text=True)
        if r.returncode:
            sys.exit("s7b: zone refill failed, the board is unchanged\n" + r.stdout[-1500:] + r.stderr[-1500:])
        with open(os.path.join(tmp, "s7b.json")) as f:
            j = json.load(f)
        for w in j["warn"]:
            print("s7b: WARNING " + w)
        print(f"s7b: {names}: deleted {len(j['deleted'])}, added {len(j['added'])}, moved {len(j['moves'])}")
        if dry:
            out = os.path.abspath(argv[argv.index("--dry-run") + 1])
            shutil.copy(pcb, out)
            print(f"s7b: dry run in {out}, the board is unchanged")
            return 0
        shutil.copy(pcb, BOARD)
        note = "routing stage 7b (2026-11-22), tools/next/route_s7b_c47_dc.py - incremental edit of the board, not a rebuild"
        for name, key in files:
            with open(os.path.join(RT, name), "w") as f:
                json.dump({"note": note, "groups": prev["groups"] + names, key: prev[key] + j[key]}, f, indent=1)
        print("s7b: wrote the board and routing/*_s7b.json")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    if "--edit" in sys.argv:
        i = sys.argv.index("--edit")
        edit(sys.argv[i + 1], sys.argv[i + 2].split(","))
        sys.exit(0)
    sys.exit(main(sys.argv[1:]))
