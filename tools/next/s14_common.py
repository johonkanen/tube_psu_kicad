#!/usr/bin/env python3
"""Shared frame of the stage-14 one-shot scripts (tools/next/route_s14*.py; design review 2026-11-24).

Each stage script defines   edit(b, ed)   (b = pcbnew BOARD, ed = Editor below) and calls
    s14_common.main(TAG, __file__, edit, sys.argv[1:])
The frame copies the board into a temporary directory next to the project, runs edit() there (a kipy subprocess),
unfills the zones, saves, refills with kicad-cli (rule severities set to ignore: refill only), and copies the
board back - or, with --dry-run OUT.kicad_pcb, writes the result to OUT and leaves the board alone. The record of
what was changed goes to kicad_next/routing/moves_<TAG>.json (its existence makes the stage not re-runnable).
Run with tools/p2k/bin/kipy.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJ = os.path.join(ROOT, "kicad_next")
NAME = "tube_psu_5_2"
BOARD = os.path.join(PROJ, NAME + ".kicad_pcb")
CLI = os.path.join(ROOT, "tools", "p2k", "bin", "kicad-cli")


def r3(p):
    return (round(p[0], 3), round(p[1], 3))


class Editor:
    """Small, checked edit operations; every one is appended to self.rec."""

    def __init__(self, b, tag):
        import pcbnew
        self.P, self.b, self.tag = pcbnew, b, tag
        self.mm, self.MM = pcbnew.ToMM, pcbnew.FromMM
        self.rec = []

    def fail(self, msg):
        sys.exit(f"{self.tag}: {msg}")

    def v(self, p):
        return self.P.VECTOR2I(self.MM(p[0]), self.MM(p[1]))

    def pt(self, v):
        return (self.mm(v.x), self.mm(v.y))

    def find_track(self, net, layer, s, e, w=None):
        P = self.P
        hit = [t for t in self.b.GetTracks() if t.Type() == P.PCB_TRACE_T and t.GetNetname() == net
               and self.b.GetLayerName(t.GetLayer()) == layer
               and (w is None or abs(self.mm(t.GetWidth()) - w) < 1e-3)
               and {r3(self.pt(t.GetStart())), r3(self.pt(t.GetEnd()))} == {r3(s), r3(e)}]
        if len(hit) != 1:
            self.fail(f"segment {net} {layer} {s} {e} found {len(hit)} times")
        return hit[0]

    def delete_track(self, net, layer, s, e, w=None):
        t = self.find_track(net, layer, s, e, w)
        self.rec.append(dict(op="delete_track", net=net, layer=layer, start=s, end=e, width=self.mm(t.GetWidth())))
        self.b.Delete(t)

    def add_track(self, net, layer, s, e, w):
        t = self.P.PCB_TRACK(self.b)
        t.SetStart(self.v(s))
        t.SetEnd(self.v(e))
        t.SetWidth(self.MM(w))
        t.SetLayer(self.b.GetLayerID(layer))
        n = self.b.FindNet(net)
        if n is None:
            self.fail(f"net {net} missing")
        t.SetNet(n)
        self.b.Add(t)
        self.rec.append(dict(op="add_track", net=net, layer=layer, start=s, end=e, width=w))

    def add_path(self, net, layer, pts, w):
        for s, e in zip(pts, pts[1:]):
            self.add_track(net, layer, s, e, w)

    def find_via(self, net, at):
        P = self.P
        hit = [t for t in self.b.GetTracks() if t.Type() == P.PCB_VIA_T and t.GetNetname() == net
               and r3(self.pt(t.GetPosition())) == r3(at)]
        if len(hit) != 1:
            self.fail(f"via {net} {at} found {len(hit)} times")
        return hit[0]

    def add_via(self, net, at, d=0.8, drill=0.4):
        P = self.P
        v = P.PCB_VIA(self.b)
        v.SetPosition(self.v(at))
        v.SetWidth(self.MM(d))
        v.SetDrill(self.MM(drill))
        v.SetLayerPair(P.F_Cu, P.B_Cu)
        v.SetNet(self.b.FindNet(net))
        self.b.Add(v)
        self.rec.append(dict(op="add_via", net=net, at=at, size=d, drill=drill))

    def delete_via(self, net, at):
        v = self.find_via(net, at)
        self.rec.append(dict(op="delete_via", net=net, at=at))
        self.b.Delete(v)

    def move_via(self, net, old, new):
        v = self.find_via(net, old)
        v.SetPosition(self.v(new))
        self.rec.append(dict(op="move_via", net=net, old=old, new=new))

    def zone(self, name, net=None, layer=None):
        hit = [z for z in self.b.Zones() if z.GetZoneName() == name and (net is None or z.GetNetname() == net)
               and (layer is None or self.b.GetLayerName(z.GetLayer()) == layer)]
        if len(hit) != 1:
            self.fail(f"zone {name} {net} {layer} found {len(hit)} times")
        return hit[0]

    def outline(self, z):
        o = z.Outline()
        out = []
        for i in range(o.OutlineCount()):
            rings = [o.Outline(i)] + [o.Hole(i, k) for k in range(o.HoleCount(i))]
            out.append([[list(r3(self.pt(r.CPoint(k)))) for k in range(r.PointCount())] for r in rings])
        return out

    def set_outline(self, z, polys, why=""):
        """polys: [[outer ring, hole ring, ...], ...], rings as lists of (x, y) mm"""
        old = self.outline(z)
        ps = z.Outline()                 # edited in place (a new SHAPE_POLY_SET handed to SetOutline crashes)
        ps.RemoveAllContours()
        for rings in polys:
            ps.NewOutline()
            for x, y in rings[0]:
                ps.Append(self.MM(x), self.MM(y))
            for h in rings[1:]:
                ps.NewHole()
                o = ps.OutlineCount() - 1
                for x, y in h:          # aHole = -1 would mean the OUTER ring (bug of the first 14a run)
                    ps.Append(self.MM(x), self.MM(y), o, ps.HoleCount(o) - 1)
        self.rec.append(dict(op="zone_outline", zone=z.GetZoneName(), net=z.GetNetname(),
                             layer=self.b.GetLayerName(z.GetLayer()), old=old, new=polys, why=why))

    def add_keepout(self, name, layer, ring, why=""):
        """rule area on one layer, no zone fill (tracks / vias / pads allowed)"""
        P = self.P
        z = P.ZONE(self.b)
        z.SetIsRuleArea(True)
        z.SetLayer(self.b.GetLayerID(layer))
        z.SetDoNotAllowZoneFills(True)
        z.SetDoNotAllowTracks(False)
        z.SetDoNotAllowVias(False)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
        z.SetZoneName(name)
        o = z.Outline()
        o.NewOutline()
        for x, y in ring:
            o.Append(self.MM(x), self.MM(y))
        self.b.Add(z)
        self.rec.append(dict(op="add_keepout", name=name, layer=layer, ring=ring, why=why))

    def footprint(self, ref):
        f = self.b.FindFootprintByReference(ref)
        if f is None:
            self.fail(f"footprint {ref} missing")
        return f

    def move_footprint(self, ref, new, rot=None):
        f = self.footprint(ref)
        old, orot = self.pt(f.GetPosition()), f.GetOrientationDegrees()
        f.SetPosition(self.v(new))
        if rot is not None:
            f.SetOrientationDegrees(rot)
        self.rec.append(dict(op="move_footprint", ref=ref, old=old, old_rot=orot, new=new,
                             new_rot=f.GetOrientationDegrees()))


def _edit(path, script, tag):
    import importlib.util
    import pcbnew
    spec = importlib.util.spec_from_file_location("stage", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    b = pcbnew.LoadBoard(path)
    ed = Editor(b, tag)
    mod.edit(b, ed)
    for z in b.Zones():
        if not z.GetIsRuleArea():
            z.UnFill()
    pcbnew.SaveBoard(path, b)
    with open(os.path.join(os.path.dirname(path), "rec.json"), "w") as f:
        json.dump(ed.rec, f)


def main(tag, script, _edit_fn, argv):
    if "--edit" in argv:
        return _edit(argv[argv.index("--edit") + 1], os.path.abspath(script), tag)
    if os.path.exists(os.path.join(PROJ, "~" + NAME + ".kicad_pcb.lck")):
        sys.exit(f"{tag}: the board is open in KiCad; close it first")
    rec_path = os.path.join(PROJ, "routing", f"moves_{tag}.json")
    dry = "--dry-run" in argv
    src = BOARD
    if "--from" in argv:                     # dry runs on top of another dry run
        src = os.path.abspath(argv[argv.index("--from") + 1])
    if not dry and os.path.exists(rec_path):
        sys.exit(f"{tag}: already on the board (not re-runnable)")
    tmp = tempfile.mkdtemp(prefix=f".{tag}_", dir=ROOT)
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
        if subprocess.run([sys.executable, "-u", os.path.abspath(__file__), "--edit", pcb,
                           os.path.abspath(script), tag]).returncode:
            sys.exit(f"{tag}: edit failed, the board is unchanged")
        r = subprocess.run([CLI, "pcb", "drc", "--format", "json", "--refill-zones", "--save-board",
                            "-o", os.path.join(tmp, "refill.json"), pcb], capture_output=True, text=True)
        if r.returncode:
            sys.exit(f"{tag}: zone refill failed, the board is unchanged\n" + r.stdout[-1500:] + r.stderr[-1500:])
        with open(os.path.join(tmp, "rec.json")) as f:
            rec = json.load(f)
        ops = {}
        for x in rec:
            ops[x["op"]] = ops.get(x["op"], 0) + 1
        print(f"{tag}: " + ", ".join(f"{k} {n}" for k, n in ops.items()))
        if dry:
            shutil.copy(pcb, os.path.abspath(argv[argv.index("--dry-run") + 1]))
        else:
            shutil.copy(pcb, BOARD)
            with open(rec_path, "w") as f:
                json.dump(dict(stage=tag, script=os.path.relpath(os.path.abspath(script), ROOT), ops=rec), f, indent=1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    if len(sys.argv) >= 5 and sys.argv[1] == "--edit":
        _edit(sys.argv[2], sys.argv[3], sys.argv[4])
