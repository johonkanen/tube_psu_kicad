#!/usr/bin/env python3
"""Placement step 1 on the TRIAL 5.2 board built from the 5.1 layout (run with tools/p2k/bin/kipy).

    tools/p2k/bin/kipy tools/next/reuse_51_board.py --no-report   step 0: the trial board (reuse of 5.1)
    tools/p2k/bin/kipy tools/next/trial_placement.py [--no-report] step 1: the moves below + DRC + report

Input:  kicad_next/trial_from_51/tube_psu_5_2_trial.kicad_pcb (step 0, written by reuse_51_board.py)
Output: kicad_next/trial_from_51/tube_psu_5_2_trial_p1.kicad_pcb (+ .kicad_pro / .kicad_dru copies),
        drc_p1.json (same memory-bounded split-pass DRC as step 0), placement_p1.json (moves, copper
        bookkeeping, geometry for the drawings), then tools/next/trial_report.py (section "After placement
        step 1" in REPORT.md, zoom_p1_*.png). kicad_next/tube_psu_5_2.kicad_pcb is not touched.

Step 1 = user decisions of 2026-11-19 (the L1 / L2 part of it - upright toroids on the RM8 holes - is already
in step 0 through the footprint and reuse_51_board.NEW_ORIENTATION):

B. TR3 (EC42 two-chamber, footprint origin = core centre, primary pin row x - 20, secondary row x + 20, 12 mm
   barrier keep-out x -7 ... +5 under the divider) moves over the freed ETD34 + L3 area, as high as the top
   board edge allows (courtyard 0.55 mm inside it), its barrier band in line with the TO-row barrier between
   Q19 (primary) and Q21 (secondary). The pins land at x 29.5 / 69.5, y -86.8 / -81.8 / -56.8 / -51.8.
   - The DAB split capacitors go to "their" pins (NEXT_REVISION_PLAN phase 5, constraint 2): C47 / C54
     (DC+ / DHB_CAP / DHB_CURRENT) stacked left of primary pins 1 / 2 (DHB_CAP) in the old L3 area, the
     DHB_CAP pads facing each other next to the pins; C16 / C55 (420V / TRANS_SEC / ISO_GND) stacked right of
     secondary pins 9 / 10 (TRANS_SEC), between TR3 and C19, ISO_GND end towards Q8.
   - C89 (one of the 420V / ISO_GND 1210 bank) would sit 1.1 mm inside the TR3 courtyard: moved above C90.
   - The bottom-side gate-drive clusters must not sit under TR3's THT pins: DRV5 (primary) with its
     bootstrap / decoupling parts moves 4.5 mm left (out of the primary pin row); DRV6 (secondary) with its
     parts moves under the TR3 body between the barrier band and the secondary pin row (the only free
     bottom-side space on the secondary side: right of the row are C19's pins and the output terminals).
     Groups move rigidly: tracks / vias of the group's nets that only connect the group's own pads (inside
     the group's courtyard box + 1 mm) move with them; other copper touching a moved pad is deleted.
   - Copper (tracks / vias) of another net under or within 1.0 mm of a pad of a moved footprint at its new
     place is deleted, and every track / via inside TR3's 12 mm barrier band (the footprint's rule area);
     zones are refilled by the DRC.
"""
import collections
import json
import os
import re
import shutil
import subprocess
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_board  # noqa: E402
import reuse_51_board as R  # noqa: E402  (paths, run_drc, overlaps, dump, netlist)
import gen_next_footprints as gfp  # noqa: E402  (EC42_BAND)

NAME1 = R.NAME + "_p1"
OUT1 = os.path.join(R.OUTDIR, NAME1 + ".kicad_pcb")

# --- the moves (board mm, KiCad orientation in degrees) ------------------------------------------------
PLACE = {   # ref: (x, y, orientation) - absolute
    "TR3": (49.5, -69.3, 0.0),
    "C47": (22.5, -86.5, -90.0),     # pad 1 DC+ up, pad 2 DHB_CAP down (towards C54 / pins 1-2)
    "C54": (22.5, -78.5, -90.0),     # pad 1 DHB_CAP up, pad 2 DHB_CURRENT down
    "C16": (76.1, -58.6, -90.0),     # pad 1 420V up, pad 2 TRANS_SEC down (towards C55 / pins 9-10)
    "C55": (76.1, -50.6, -90.0),     # pad 1 TRANS_SEC up, pad 2 ISO_GND down (towards Q8)
    "C89": (75.4, -80.6, -90.0),     # 420V / ISO_GND 1210, out of the TR3 courtyard, above C90
}
GROUPS = {  # name: (refs, dx, dy) - rigid translation, bottom side
    "DRV5 primary gate drive": (["DRV5", "C92", "C94", "C95", "C96", "D19", "R41"], -4.5, 0.0),
    "DRV6 secondary gate drive": (["DRV6", "C46", "R46", "D18", "C93", "C72", "R75", "R76"], -8.5, -4.6),
}
EPS = 1000  # nm, endpoint coincidence
CLEAR_NEW = 1.0  # mm: copper of another net this close to a moved pad is deleted (HV functional rule 1.2 mm)


def near(pad, t, clr):
    layers = [pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In1_Cu, pcbnew.In4_Cu] if t.Type() == pcbnew.PCB_VIA_T else [t.GetLayer()]
    for layer in layers:
        if pad.IsOnLayer(layer) and pad.GetEffectiveShape(layer).Collide(t.GetEffectiveShape(layer), clr):
            return True
    return False


def nm(v):
    return int(round(v * R.MM))


def track_points(t):
    if t.Type() == pcbnew.PCB_VIA_T:
        return [t.GetPosition()]
    return [t.GetStart(), t.GetEnd()]


def group_box(fps):
    bb = None
    for fp in fps:
        r = R.courtyard_box(fp)
        if bb is None:
            bb = pcbnew.BOX2I(r.GetPosition(), r.GetSize())
        else:
            bb.Merge(r)
    bb.Inflate(nm(1.0))
    return bb


def main(argv):
    if not os.path.exists(R.OUT):
        sys.exit("trial_placement: run tools/next/reuse_51_board.py first (step 0 board missing)")
    if "--dump" in argv:        # second interpreter (see below): geometry of the refilled step-1 board
        comps, _, _ = R.netlist()
        path = os.path.join(R.OUTDIR, "placement_p1.json")
        with open(path) as f:
            rec = json.load(f)
        rec["geometry"] = R.dump(pcbnew.LoadBoard(OUT1), comps)
        with open(path, "w") as f:
            json.dump(rec, f, indent=1, sort_keys=True)
        return 0
    rec = build()
    rec["moves"] = dict(place={k: list(v) for k, v in PLACE.items()},
                        groups={k: dict(refs=v[0], dx=v[1], dy=v[2]) for k, v in GROUPS.items()})
    with open(os.path.join(R.OUTDIR, "placement_p1.json"), "w") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
    # the DRC passes load board copies with pcbnew; in this process (after build()'s SaveBoard) LoadBoard
    # comes back as a bare SwigPyObject, so they run in a fresh interpreter
    subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, sys.argv[1]); import reuse_51_board as R; "
                    "R.run_drc(name=sys.argv[2], out_json='drc_p1.json')", HERE, NAME1], check=True)
    for f in ("fp-info-cache", NAME1 + ".kicad_prl"):
        if os.path.exists(os.path.join(R.OUTDIR, f)):
            os.remove(os.path.join(R.OUTDIR, f))

    # pcbnew.LoadBoard after a SaveBoard in this process returns a bare SwigPyObject -> fresh interpreter
    subprocess.run([sys.executable, os.path.abspath(__file__), "--dump"], check=True)
    grp = ", ".join("%s (%d parts, %d copper items moved)" % (k, len(v[0]), rec["groups"][k]["tracks_moved"])
                    for k, v in GROUPS.items())
    print(f"trial_placement: {os.path.relpath(OUT1, R.ROOT)}: moved {len(PLACE)} parts + {grp}; deleted {rec['deleted']}")
    if "--no-report" not in argv:
        # system python (matplotlib / shapely), without the AppImage's PYTHONHOME / PYTHONPATH
        env = {k: v for k, v in os.environ.items() if k not in ("PYTHONHOME", "PYTHONPATH")}
        subprocess.run(["python3", os.path.join(HERE, "trial_report.py")], check=True, env=env)
    return 0


def build():
    """apply the moves to the step-0 board and save the step-1 project; returns the bookkeeping"""
    b = pcbnew.LoadBoard(R.OUT)
    fps = {fp.GetReference(): fp for fp in b.GetFootprints()}
    tracks = list(b.GetTracks())
    rec = {"place": {}, "groups": {}, "deleted": collections.Counter(), "deleted_by_ref": collections.Counter()}

    # pads by net (for "touches a pad outside the group")
    pads_by_net = collections.defaultdict(list)
    for ref, fp in fps.items():
        for p in fp.Pads():
            pads_by_net[p.GetNetCode()].append((ref, p))

    moved_refs = set(PLACE) | {r for refs, _, _ in GROUPS.values() for r in refs}
    for r in moved_refs:
        if r not in fps:
            sys.exit(f"trial_placement: {r} not on the step-0 board")

    # endpoint index of the tracks
    at = collections.defaultdict(list)
    for t in tracks:
        for pt in track_points(t):
            at[(pt.x // EPS, pt.y // EPS)].append(t)

    def neighbours(t):
        out = []
        for pt in track_points(t):
            kx, ky = pt.x // EPS, pt.y // EPS
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for u in at.get((kx + dx, ky + dy), ()):
                        if u is not t and u.GetNetCode() == t.GetNetCode() and any(
                                abs(q.x - pt.x) <= EPS and abs(q.y - pt.y) <= EPS for q in track_points(u)):
                            out.append(u)
        return out

    def touching(pads, pool):
        out = []
        for p in pads:
            pb = p.GetBoundingBox()
            for t in pool:
                if t.GetBoundingBox().Intersects(pb) and R.overlaps(p, t):
                    out.append(t)
        return out

    # 1. rigid copper of the groups
    internal = {}          # track uuid -> group name
    for gname, (refs, dx, dy) in GROUPS.items():
        gfps = [fps[r] for r in refs]
        box = group_box(gfps)
        gpads = [p for fp in gfps for p in fp.Pads()]
        nets = {p.GetNetCode() for p in gpads if p.GetNetCode() > 0}
        cand = [t for t in tracks if t.GetNetCode() in nets]
        inside = lambda t: all(box.Contains(pt) for pt in track_points(t))  # noqa: E731

        def foreign(t):
            for ref, p in pads_by_net.get(t.GetNetCode(), ()):
                if ref not in refs and t.GetBoundingBox().Intersects(p.GetBoundingBox()) and R.overlaps(p, t):
                    return True
            return False
        start = [t for t in touching(gpads, cand) if inside(t) and not foreign(t)]
        seen = {t.m_Uuid.AsString(): t for t in start}
        todo = list(start)
        while todo:
            t = todo.pop()
            for u in neighbours(t):
                k = u.m_Uuid.AsString()
                if k not in seen and inside(u) and not foreign(u):
                    seen[k] = u
                    todo.append(u)
        for k in seen:
            internal[k] = gname
        rec["groups"][gname] = dict(refs=refs, dx=dx, dy=dy, tracks_moved=len(seen))

    # 2. copper touching an old pad of a moved part and not moving with a group -> delete
    old_pads = [(r, p) for r in moved_refs for p in fps[r].Pads()]
    kill = {}
    for r, p in old_pads:
        pb = p.GetBoundingBox()
        for t in tracks:
            k = t.m_Uuid.AsString()
            if k in internal or k in kill:
                continue
            if t.GetBoundingBox().Intersects(pb) and R.overlaps(p, t):
                kill[k] = (t, "touches old pad of moved part", r)

    # 3. move
    for ref, (x, y, rot) in PLACE.items():
        fp = fps[ref]
        old = (R.mm(fp.GetPosition().x), R.mm(fp.GetPosition().y), fp.GetOrientationDegrees())
        fp.SetPosition(pcbnew.VECTOR2I(nm(x), nm(y)))
        fp.SetOrientationDegrees(rot)
        rec["place"][ref] = dict(old=old, new=(x, y, rot), side="B" if fp.IsFlipped() else "F")
    for gname, (refs, dx, dy) in GROUPS.items():
        v = pcbnew.VECTOR2I(nm(dx), nm(dy))
        for r in refs:
            fps[r].Move(v)
    for t in tracks:
        g = internal.get(t.m_Uuid.AsString())
        if g:
            _, dx, dy = GROUPS[g]
            t.Move(pcbnew.VECTOR2I(nm(dx), nm(dy)))

    # 4. copper of another net under / within CLEAR_NEW of a new pad of a moved part -> delete
    clr = nm(CLEAR_NEW)
    for r in sorted(moved_refs):
        for p in fps[r].Pads():
            pb = p.GetBoundingBox()
            pb.Inflate(clr)
            for t in tracks:
                k = t.m_Uuid.AsString()
                if k in kill or t.GetNetCode() == p.GetNetCode():
                    continue
                if t.GetBoundingBox().Intersects(pb) and near(p, t, clr):
                    kill[k] = (t, f"within {CLEAR_NEW:g} mm of a new pad of a moved part", r)
    # 5. TR3 barrier band (rule area of the footprint: no tracks / vias) -> delete what lies in it
    tr3 = fps["TR3"]
    cx, cy = R.mm(tr3.GetPosition().x), R.mm(tr3.GetPosition().y)
    band = pcbnew.BOX2I(pcbnew.VECTOR2I(nm(cx + gfp.EC42_BAND["x0"]), nm(cy - 21.5)),
                        pcbnew.VECTOR2L(nm(gfp.EC42_BAND["x1"] - gfp.EC42_BAND["x0"]), nm(43.0)))
    for t in tracks:
        k = t.m_Uuid.AsString()
        if k not in kill and t.GetBoundingBox().Intersects(band):
            kill[k] = (t, "in the TR3 barrier band", "TR3")
    for t, why, r in kill.values():
        kind = "via" if t.Type() == pcbnew.PCB_VIA_T else "segment"
        rec["deleted"][f"{kind}: {why}"] += 1
        rec["deleted_by_ref"][r] += 1
        b.Remove(t)

    # 5. write the step-1 project and run the DRC
    for ext in (".kicad_pro", ".kicad_dru"):
        shutil.copy(os.path.join(R.OUTDIR, R.NAME + ext), os.path.join(R.OUTDIR, NAME1 + ext))
    pro_path = os.path.join(R.OUTDIR, NAME1 + ".kicad_pro")
    with open(pro_path) as f:
        pro = json.load(f)
    pro.setdefault("meta", {})["filename"] = NAME1 + ".kicad_pro"
    with open(pro_path, "w") as f:
        json.dump(pro, f, indent=2)
        f.write("\n")
    pcbnew.SaveBoard(OUT1, b)
    with open(OUT1) as f:
        s = f.read()
    s = re.sub(r"\t\t\(stackup\n.*?\n\t\t\)\n", "", s, flags=re.S)
    s = s.replace("\t(setup\n", "\t(setup\n" + make_board.STACKUP, 1)
    with open(OUT1, "w") as f:
        f.write(s)
    rec["deleted"] = dict(rec["deleted"])
    rec["deleted_by_ref"] = dict(rec["deleted_by_ref"].most_common())
    return rec


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
