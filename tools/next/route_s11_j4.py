#!/usr/bin/env python3
"""Stage 11 (2026-11-23): J4 becomes a 1x6 header (user decision: 12 Mbaud single-ended UART link between two FPGA
boards, a ground pin beside each signal) and the UART island is re-routed (see README "Stage 11").

    tools/p2k/bin/kipy tools/next/route_s11_j4.py --group NAME[,NAME...] [--dry-run OUT.kicad_pcb] [--from PCB]

Incremental edit, same conventions and code as route_s8_c95_dc.py; NOT re-runnable (a group that is listed in
routing/s11_added.json is refused). Appends to kicad_next/routing/moves_s11.json, deleted_s11.json, s11_added.json.
Zones are refilled by kicad-cli.

Entries: ADD ("t", net, layer key, width, [points]) / ("v", net, x, y, pad, drill) / ("z", ...); DEL (net, layer key,
x0, y0, x1, y1, why); DELVIA (net, x, y, why); MOVE (ref, x, y, rot, side, why); REPLACE (ref, footprint id, x, y,
rot, side, why[, dict(pads={pad: net}, value=..., fields={...})]): the footprint is replaced by the library footprint
of the new id (the schematic must already name it) at the new place; reference, symbol path, sheet and fields are
kept; value, fields and pad nets are kept (by pad number) or taken from the dict when the part itself changes (J4).
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

TXD, RXD = "/04 MCU connector/UART_TXD", "/04 MCU connector/UART_RXD"
V33, UGND = "UART_3V3", "ISO_UART_GND"
JX, JY, P = 11.4, -89.0, 2.54   # J4 pin 1 stays at (11.4, -89.0); pin n at y -89.0 + 2.54 (n - 1), pin 6 at y -76.3
XW = 9.9                        # F.Cu TXD lane west of the J4 pads (pad edge x 10.55)
XG = 10.05                      # B.Cu ground bus west of the J4 pads, under the TXD lane

GROUPS = {
    # J4 1x4 -> 1x6 in place: 1 GND, 2 TXD in, 3 GND, 4 RXD out, 5 GND, 6 3V3 in (was 1 GND, 2 3V3, 3 TXD, 4 RXD).
    # RXD (R137.2 -> pin 4) stays as routed. TXD: F.Cu from R136 round the west of pins 4 / 3 to pin 2. The order of
    # 3V3 / RXD / TXD at U11 (pins 14 / 13 / 12) is the reverse of the order at J4 (pins 6 / 4 / 2), so UART_3V3 goes
    # to pin 6 on B.Cu from a via in C135 pad 1. The three ground pins: B.Cu bus on x 10.05 (the island is a pour
    # keep-out, no ground plane), tied to the ground via of U11 pin 16 / C135 (6.25, -81.275); U11 pin 9 keeps its
    # B.Cu link to that via.
    "j4": dict(DEL=[
        (V33, F, 10.1, -84.86, 11.1, -85.86, "3V3 moved from pin 2 to pin 6"),
        (V33, F, 10.1, -83.56, 10.1, -84.86, "same"),
        (V33, F, 7.0, -80.46, 10.1, -83.56, "same"),
        (V33, F, 7.0, -80.425, 7.0, -80.46, "same (stub in C135 pad 1)"),
        (UGND, F, 7.0, -81.975, 7.0, -83.4, "ground of J4 now on B.Cu (the TXD lane takes x 9.9 on F.Cu)"),
        (UGND, F, 7.0, -83.4, 10.1, -86.5, "same"),
        (UGND, F, 10.1, -86.5, 10.1, -87.7, "same"),
        (UGND, F, 10.1, -87.7, 10.8, -88.4, "same"),
        (TXD, F, 7.625, -79.62, 11.225, -83.22, "TXD moved from pin 3 to pin 2"),
    ], REPLACE=[
        ("J4", "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical", JX, JY, 0.0, "F",
         "1x6: a ground pin beside each signal (12 Mbaud)", dict(pads={"1": UGND, "2": TXD, "3": UGND, "4": RXD, "5": UGND, "6": V33}, value="UART 1x6",
              fields={"LCSC": "C492405", "Description":
                      "6-pin 2.54 mm UART header: GND, TXD in, GND, RXD out, GND, 3V3 in (NR 3b.2, 2026-11-23)"})),
    ], ADD=[
        ("t", TXD, F, 0.2, [(7.625, -79.62), (XW, -81.895), (XW, -85.5), (10.86, JY + P), (JX, JY + P)]),
        ("v", V33, 7.0, -80.425, 0.6, 0.3),                                     # in C135 pad 1
        ("t", V33, B, 0.3, [(7.0, -80.425), (11.125, JY + 5 * P), (JX, JY + 5 * P)]),
        ("t", UGND, B, 0.3, [(JX, JY), (XG, JY + 1.35), (XG, JY + 2 * P), (XG, -80.19), (JX, JY + 4 * P)]),
        ("t", UGND, B, 0.3, [(XG, JY + 2 * P), (JX, JY + 2 * P)]),
        ("t", UGND, B, 0.3, [(6.25, -81.275), (7.4, -82.425), (XG, -82.425)]),
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
        for ref, fpid, x, y, rot, to_side, why, *padnets in G.get("REPLACE", []):
            import reuse_51_board as R
            fp = b.FindFootprintByReference(ref)
            p = fp.GetPosition()
            side = "B" if fp.IsFlipped() else "F"
            if side != to_side:
                sys.exit("s11: no side changes in this stage")
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
                    sys.exit("s11: REPLACE names a net that is not on the board")
                new.SetValue(padnets[0]["value"])
                for k, v in padnets[0]["fields"].items():
                    new.SetField(k, v)
            MOVES.append(dict(group=g, ref=ref, footprint=dict(frm=fp.GetFPIDAsString(), to=fpid),
                              frm=dict(x=mm(p.x), y=mm(p.y), rot=fp.GetOrientationDegrees(), side=side),
                              to=dict(x=x, y=y, rot=rot, side=to_side), why=why))
            for pad in new.Pads():
                pad.SetNet(nets[pad.GetNumber()])
                q = pad.GetPosition()
                print(f"s11: {ref} pad {pad.GetNumber()} {pad.GetNetname()} at ({mm(q.x)}, {mm(q.y)})")
            b.Delete(fp)
        for ref, x, y, rot, to_side, why in G.get("MOVE", []):
            fp = b.FindFootprintByReference(ref)
            p = fp.GetPosition()
            side = "B" if fp.IsFlipped() else "F"
            if side != to_side:
                sys.exit("s11: no side changes in this stage")
            MOVES.append(dict(group=g, ref=ref, frm=dict(x=mm(p.x), y=mm(p.y), rot=fp.GetOrientationDegrees(), side=side),
                              to=dict(x=x, y=y, rot=rot, side=to_side), why=why))
            fp.SetPosition(pcbnew.VECTOR2I(nm(x), nm(y)))
            fp.SetOrientationDegrees(rot)
            for pad in fp.Pads():
                q = pad.GetPosition()
                print(f"s11: {ref} pad {pad.GetNumber()} {pad.GetNetname()} at ({mm(q.x)}, {mm(q.y)})")
        for a in G.get("ADD", []):
            code = b.GetNetcodeFromNetname(a[1])
            if code <= 0:
                sys.exit(f"s11: no net {a[1]}")
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
                    sys.exit(f"s11: model zone {model} [{n}] not found")
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
    with open(os.path.join(os.path.dirname(path), "s11.json"), "w") as f:
        json.dump(dict(deleted=DELETED, added=ADDED, moves=MOVES, warn=WARN), f)


def main(argv):
    if os.path.exists(LOCK):
        sys.exit("s11: the board is open in KiCad; close it first")
    names = argv[argv.index("--group") + 1].split(",")
    files = (("deleted_s11.json", "deleted"), ("s11_added.json", "added"), ("moves_s11.json", "moves"))
    prev = {"deleted": [], "added": [], "moves": [], "groups": []}
    if os.path.exists(os.path.join(RT, "s11_added.json")):
        for name, key in files:
            with open(os.path.join(RT, name)) as f:
                d = json.load(f)
            prev[key] = d[key]
            prev["groups"] = d.get("groups", prev["groups"])
    dry = "--dry-run" in argv
    if not dry and any(g in prev["groups"] for g in names):
        sys.exit("s11: group already on the board (not re-runnable)")
    src = BOARD
    if "--from" in argv:                               # dry run on top of an earlier dry run
        src = os.path.abspath(argv[argv.index("--from") + 1])
    tmp = tempfile.mkdtemp(prefix=".s11_", dir=ROOT)
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
            sys.exit("s11: edit failed, the board is unchanged")
        r = subprocess.run([CLI, "pcb", "drc", "--format", "json", "--refill-zones", "--save-board",
                            "-o", os.path.join(tmp, "refill.json"), pcb], capture_output=True, text=True)
        if r.returncode:
            sys.exit("s11: zone refill failed, the board is unchanged\n" + r.stdout[-1500:] + r.stderr[-1500:])
        with open(os.path.join(tmp, "s11.json")) as f:
            j = json.load(f)
        for w in j["warn"]:
            print("s11: WARNING " + w)
        print(f"s11: {names}: deleted {len(j['deleted'])}, added {len(j['added'])}, moved {len(j['moves'])}")
        if dry:
            out = os.path.abspath(argv[argv.index("--dry-run") + 1])
            shutil.copy(pcb, out)
            print(f"s11: dry run in {out}, the board is unchanged")
            return 0
        shutil.copy(pcb, BOARD)
        note = "routing stage 11 (2026-11-23), tools/next/route_s11_j4.py - incremental edit of the board, not a rebuild"
        for name, key in files:
            with open(os.path.join(RT, name), "w") as f:
                json.dump({"note": note, "groups": prev["groups"] + names, key: prev[key] + j[key]}, f, indent=1)
        print("s11: wrote the board and routing/*_s11.json")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    if "--edit" in sys.argv:
        i = sys.argv.index("--edit")
        edit(sys.argv[i + 1], sys.argv[i + 2].split(","))
        sys.exit(0)
    sys.exit(main(sys.argv[1:]))
