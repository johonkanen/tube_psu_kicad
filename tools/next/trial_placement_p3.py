#!/usr/bin/env python3
"""Placement step 3 on the TRIAL 5.2 board built from the 5.1 layout (run with tools/p2k/bin/kipy).

    tools/p2k/bin/kipy tools/next/reuse_51_board.py --no-report    step 0 (reuse of 5.1)
    tools/p2k/bin/kipy tools/next/trial_placement.py --no-report   step 1 (TR3, split caps, DRV5 / DRV6)
    tools/p2k/bin/kipy tools/next/trial_placement_p2.py --no-report   step 2 (UART island, Q19 / Q21 slot, TR1 / PWM2)
    tools/p2k/bin/kipy tools/next/trial_placement_p3.py [--no-report] [--check]   step 3 (this script)

Input:  kicad_next/trial_from_51/tube_psu_5_2_trial_p2.kicad_pcb (step 2)
Output: tube_psu_5_2_trial_p3.kicad_pcb (+ .kicad_pro / .kicad_dru copies), drc_p3.json (the split-pass DRC of
        reuse_51_board.run_drc), placement_p3.json (moves, slot, keep-outs, deleted copper with positions so the
        routing can redo it, geometry for the drawings), then tools/next/trial_report.py (REPORT.md section
        "After placement step 3", zoom_p3_*.png). --check: build only and print the new courtyard overlaps / pad
        shorts of the moved and added parts and the parts still outside the board (no DRC, nothing written).
        kicad_next/tube_psu_5_2.kicad_pcb is not touched.

Step 3 (moves as data below; nothing is routed, only copper that violates or is orphaned is deleted):
 1. Heater barrier at ISO1 / TR2 (primary <-> heater 8.0 mm): ISO1 gets its board-specific footprint with a T slot
    (FOOTPRINTS) - the footprint slot plus a 1.0 mm cross slot past its top end, between the ISO1 primary pins 5-8
    and the heater pins TR2 pad 10 / WP4 (Q14_DRAIN); WP4
    1 mm up; the primary via / inner tracks within 8.0 mm of the TR2 pad 10 / WP4 barrels deleted (inner layers have
    no slot credit); pour keep-outs at the slot, between the TR2 pin rows and below the heater island; the relay
    driver Q9 / C35 / R44 / R32 (bottom side, 5.6 ... 8 mm below the heater island and 3.0 mm from the PE pad of
    C82) moved under the relay RL1; primary copper left within 8.0 mm of the island's bottom edge deleted.
 2. PE (Y capacitors) <-> primary 3.2 mm: C85 1.6 mm up (pad 2 PE to RL1 pin 1), primary tracks / vias within
    3.2 mm of a PE pad and PE tracks within 3.2 mm of a primary pad deleted, a pour keep-out of 3.25 mm around the
    PE pads / tracks (all copper layers) and of the creepage distance around the earthed mounting holes H1-H8;
    tracks / vias inside the mounting-hole spacing deleted (among them the two B.Cu tracks of the step-2 notes);
    the pads inside it moved (R47 / R48 at H7, R14 at H4, C102 turned at H8).
 3. The 5.2 parts still in the off-board grid placed next to their circuits (NEW; side F / B), each inside its own
    isolation domain; parts without a sensible free place are listed in UNPLACED with the reason.
 4. Leftovers of step 2: reference texts moved off the slots / the board edge (TEXTS).
Copper rules for every moved part (as steps 1 / 2): copper touching an old pad is deleted, copper of another net
within 1.0 mm of a new pad is deleted (1.25 mm for a HV net pad; 0.3 mm for the added parts, which are placed
between the 5.1 tracks). Zones are refilled by the DRC.
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
import reuse_51_board as R  # noqa: E402
import trial_placement as T  # noqa: E402  (near, nm, track_points, group_box)
import trial_placement_p2 as P2  # noqa: E402  (add_slot, check, seg_hits_box, domains, COPPER, INNER, SPACING)

NAME3 = R.NAME + "_p3"
OUT3 = os.path.join(R.OUTDIR, NAME3 + ".kicad_pcb")
nm, mm = T.nm, R.mm

# --- 5.1 parts moved (board mm, KiCad orientation in degrees; the side is kept) ---------------------------
PLACE = {
    # 2. Y capacitor C85: pad 2 (PE) 3.4 mm from RL1 pin 1 (RL1-COM): 1.6 mm up
    "C85": (-50.147, -40.6, -90.0),
    # 1. relay driver from between the heater island and the PE pad of C82 to the free bottom side under RL1,
    #    next to the coil pins / D9 (Q9 drain towards D9 anode, gate parts left of it)
    "Q9": (-62.6, -31.9, 0.0),
    "C35": (-65.3, -31.9, 90.0),
    "R44": (-63.55, -28.4, -90.0),
    "R32": (-65.3, -26.9, 90.0),
    # 2. pads inside the mounting-hole spacing (H1-H8 earthed: primary 3.2 mm, secondary 4.2 mm creepage); see GROUPS
    "R68": (75.165, 11.2, 0.0),      # -100 V bleeder (bottom) 2.3 mm down, between C102's new pads (left is too close to the DC+ fly lead)
    "C102": (77.0, 13.85, 90.0),     # turned about its body centre (77, 11.35): pads at x 77, 7.2 mm from H8 (4.2 +
                                     # ring 1.75 + pad 1.0 = 6.95 needed), 15.7 mm from the DC+ fly lead
}
# --- 5.2 parts taken from the off-board grid: ref: (x, y, orientation, side) -------------------------------
NEW = {
    "C118": (11.35, -53.1, -90.0, "B"),
    "C119": (69.26, -48.8, 0.0, "B"),
    "C120": (12.55, -48.83, 180.0, "B"),
    "C121": (-22.98, -46.4, 0.0, "B"),
    "C122": (-0.05, -62.3, 90.0, "B"),
    "C123": (2.1, -54.4, 0.0, "B"),
    "C124": (8.8, -60.8, 0.0, "B"),
    "C125": (0.4, -58.4, -90.0, "B"),
    "C126": (30.11, 10.0, -90.0, "B"),
    "C127": (29.51, 13.4, 0.0, "B"),
    "C128": (27.77, -29.6, 180.0, "B"),
    "C129": (25.02, -27.26, 90.0, "B"),
    "C130": (23.02, 5.44, -90.0, "B"),
    "C131": (16.73, 6.04, -90.0, "B"),
    "C132": (41.73, -9.11, 0.0, "B"),
    "C133": (43.08, -4.31, -90.0, "B"),
    "C138": (47.2, -3.8, -90.0, "F"),
    "C139": (49.3, 0.03, -90.0, "B"),
    "C140": (54.24, -3.27, 90.0, "F"),
    "D35": (-14.47, -65.71, 90.0, "B"),
    "R125": (56.0, -19.9, -90.0, "B"),
    "R126": (52.0, -9.3, 0.0, "F"),
    "R127": (13.45, -55.8, -90.0, "B"),
    "R128": (66.26, -49.1, 180.0, "B"),
    "R129": (12.55, -50.33, 180.0, "B"),
    "R130": (-22.98, -47.9, 0.0, "B"),
    "R131": (26.82, -22.94, -90.0, "B"),
    "R132": (39.17, 1.11, 180.0, "B"),
    "R133": (38.73, -7.61, 0.0, "B"),
    "R134": (41.73, -7.61, 0.0, "B"),
    "R135": (36.98, -4.61, 180.0, "B"),
    "R138": (48.77, -2.98, -90.0, "B"),
    "R139": (51.17, -2.67, 180.0, "B"),
    "R140": (47.2, -3.58, 90.0, "B"),
    "R141": (45.7, -3.58, 90.0, "B"),
    "R142": (37.26, 3.8, 90.0, "B"),
    "R143": (23.05, -87.42, -90.0, "B"),
    "R144": (23.05, -82.66, -90.0, "B"),
    "R145": (23.05, -77.84, -90.0, "B"),
    "R146": (24.25, -74.28, 0.0, "B"),
    "R147": (76.1, -59.52, -90.0, "B"),
    "R148": (76.1, -54.76, -90.0, "B"),
    "R149": (76.1, -49.94, -90.0, "B"),
    "R150": (78.2, -46.37, 0.0, "B"),
    "R151": (40.7, 15.86, 0.0, "B"),
    "R152": (45.46, 15.86, 0.0, "B"),
    "R153": (47.83, 12.26, 90.0, "B"),
    "R154": (53.95, -6.28, 90.0, "F"),
    "R155": (-11.14, -86.38, 90.0, "B"),
    "R156": (-14.7, -87.88, 180.0, "B"),
    "R157": (-8.0, -86.38, -90.0, "B"),
    "R158": (-8.0, -81.61, -90.0, "B"),
    "U9": (27.77, -26.6, -90.0, "B"),
    "U10": (40.3, -3.4, 90.0, "B"),
}
UNPLACED = {   # ref: reason (stays in the off-board grid)
}
GROUPS = {  # name: (refs, dx, dy) - rigid translation with the group's own copper
    "WP4 (Q14_DRAIN wire pad) away from the new slot": (["WP4"], 0.0, -1.0),
    # 2. pads inside the mounting-hole spacing: both AC-measurement divider rows 0.9 mm up (R47 / R48 pads 3.4 mm from
    #    the H7 ring, was 2.5 ... 2.9; R50 / R51 sit 2.1 mm above them), the Q5 gate resistors 0.45 mm down (R14 pad 2
    #    3.29 mm from the H4 ring, was 2.84; R1 / R43 sit right below it)
    "AC-measurement dividers at H7": (["R47", "R48", "R50", "R51"], 0.0, -0.9),
    "DRV1 gate resistors at H4": (["R14", "R1", "R43"], 0.0, 0.45),
}
# --- 1. ISO1 footprint variant with a T slot (user decision 2026-11-19; follow-up of step 3) ----------------
# ISO1 (rot 180 at -42.359, -54.845): primary pins 1-8 at x -37.7 (pin 8 GND y -59.29 ... pin 5 y -55.48), slot
# x -42.86 ... -41.86. TR2 pad 10 (Q14_DRAIN, heater) at (-36.4, -66.08), WP4 at (-42.8, -66.4): 5.4 / 5.2 mm from
# pin 8. The board-specific footprint tube_psu_next_parts:SOIC-16W_7.5x10.3mm_P1.27mm_Slot8.0_T_ISO1
# (gen_next_footprints_parts.py SOIC_T, checked by check_footprints.py BOARD_VARIANTS) continues the slot past the
# pin 8 / 9 end into a cross slot x -45.51 ... -31.01, y -64.10 ... -63.10 (one outline, no web), so the surface
# path pin 8 -> pad 10 goes round the right end of the bar (>= 10 mm); to the left the bar and the stem are one cut.
FOOTPRINTS = {"ISO1": "tube_psu_next_parts:SOIC-16W_7.5x10.3mm_P1.27mm_Slot8.0_T_ISO1"}
HS_Y0, HS_Y1 = -64.095, -63.095
SLOTS = {   # name: (outline for the drawings, rectangles of new slot area: copper crossing them is deleted, width)
    "ISO1 T slot (footprint variant): cross bar + stem extension": (
        [(-45.509, HS_Y0), (-31.009, HS_Y0), (-31.009, HS_Y1), (-41.859, HS_Y1), (-41.859, -62.095), (-42.859, -62.095),
         (-42.859, HS_Y1), (-45.509, HS_Y1)],
        [(-45.509, HS_Y0, -31.009, HS_Y1), (-42.859, HS_Y1, -41.859, -62.095)], 1.0),
}
# --- copper-pour keep-outs (rule areas, every copper layer) ------------------------------------------------
KEEPOUTS = {
    "heater barrier pour keep-out: ISO1 primary pins / new slot / TR2 pad 10": (-47.5, -66.0, -27.0, -59.0),
    "heater barrier pour keep-out: between the TR2 pin rows": (-35.0, -91.3, -25.1, -62.0),
    "heater barrier pour keep-out: below the heater island (ISO1 pin 16, C59, R91 / R117)": (-60.5, -50.0, -40.0, -41.8),
}
HOLE_KEEPOUT = {"PRI": 1.75 + 3.25, "SEC": 1.75 + 4.25}   # radius of the pour keep-out round a mounting hole (ring 3.5)
HOLE_DOMAIN = {"H1": "PRI", "H2": "PRI", "H4": "PRI", "H6": "PRI", "H7": "PRI", "H3": "SEC", "H5": "SEC", "H8": "SEC"}
PE_KEEPOUT = 3.25    # pour keep-out round the PE pads and PE tracks (PE-PRI basic creepage 3.2 mm)
# --- copper deleted by rule (logged with the reason) ---------------------------------------------------------
HEATER_SPACING = 8.0
HEATER_BARRELS = [("TR2", "10"), ("WP4", "1")]   # inner layers: primary copper within 8.0 mm of these pads
HEATER_BOXES = [(-62.0, -52.0, -36.0, -36.0)]    # primary tracks / vias within 8.0 mm of heater copper, same layer
PE_SPACING = {"PRI": 3.2, "SEC": 4.2}
DELETE = [   # explicit: (net, layer, point on the track, reason)
    ("Net-(AD1-VA)", "B.Cu", (-50.5, -50.4), "heater track within 8.0 mm of R27 pad 1 (RL1-COM, mains)"),
    ("Net-(AD1-VA)", "B.Cu", (-53.3, -51.2), "heater track within 8.0 mm of R27 pad 1 (RL1-COM, mains)"),
    ("Net-(AD1-VA)", "B.Cu", (-54.148, -53.2), "heater track within 8.0 mm of R27 pad 1 (RL1-COM, mains)"),
]
# --- reference texts moved off a slot / the board edge: ref: (x, y, angle) ------------------------------------
TEXTS = {
    "J4": (14.3, -86.8, 90.0),
    "ISO2": (63.4, -33.3, 0.0),
    "ISO1": (-45.7, -48.7, 0.0),
    "U11": (-3.2, -84.5, 0.0),
    "C13": (-44.2, -61.3, 90.0),     # bottom side, was on the new slot
}
NEW_CLEAR = 0.3   # added parts are placed between the 5.1 tracks: only copper inside the net class clearance goes
HV_CLEAR = 1.25   # copper of another net this close to a new pad of a HV net is deleted (HV functional 1.2 mm)


def add_keepout_poly(b, name, pts):
    z = pcbnew.ZONE(b)
    z.SetIsRuleArea(True)
    z.SetZoneName(name)
    z.SetDoNotAllowZoneFills(True)
    z.SetDoNotAllowTracks(False)
    z.SetDoNotAllowVias(False)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    ls = pcbnew.LSET()
    for l in P2.COPPER:
        ls.AddLayer(l)
    z.SetLayerSet(ls)
    o = z.Outline()
    o.NewOutline()
    for px, py in pts:
        o.Append(nm(px), nm(py))
    b.Add(z)
    return z


def circle(x, y, r, n=32):
    import math
    return [(round(x + r * math.cos(2 * math.pi * k / n), 4), round(y + r * math.sin(2 * math.pi * k / n), 4)) for k in range(n)]


def on_layer(t, layer):
    return t.IsOnLayer(layer) if t.Type() == pcbnew.PCB_VIA_T else t.GetLayer() == layer


def pad_near(pad, t, clr_mm, layers):
    """pad copper within clr of the track / via on one of the layers both are on"""
    for layer in layers:
        if pad.IsOnLayer(layer) and on_layer(t, layer) and \
                pad.GetEffectiveShape(layer).Collide(t.GetEffectiveShape(layer), nm(clr_mm)):
            return True
    return False


def tt_near(a, t, clr_mm):
    for layer in P2.COPPER:
        if on_layer(a, layer) and on_layer(t, layer) and \
                a.GetEffectiveShape(layer).Collide(t.GetEffectiveShape(layer), nm(clr_mm)):
            return True
    return False


def in_box(t, box):
    x0, y0, x1, y1 = box
    return any(x0 <= mm(p.x) <= x1 and y0 <= mm(p.y) <= y1 for p in T.track_points(t))


def offboard(b, fps):
    edge = b.GetBoardEdgesBoundingBox()
    return sorted(r for r, fp in fps.items() if not edge.Contains(fp.GetPosition()))


def build(write=True):
    b = pcbnew.LoadBoard(P2.OUT2)
    fps = {fp.GetReference(): fp for fp in b.GetFootprints()}
    dom_of = P2.domains()
    with open(os.path.join(R.OUTDIR, R.NAME + "_p2.kicad_pro")) as f:
        cls_of = {p["pattern"]: p["netclass"] for p in json.load(f)["net_settings"]["netclass_patterns"]}
    comps = R.netlist()[0] if FOOTPRINTS else {}
    swapped = {}
    for ref, fpid in FOOTPRINTS.items():   # same pads: nets by pad number, tracks stay
        old = fps[ref]
        new = R.replace_fp(b, old, fpid, ref)
        R.set_fields(new, comps[ref])
        onet = {p.GetNumber(): p.GetNet() for p in old.Pads()}
        for p in new.Pads():
            q = next(o for o in old.Pads() if o.GetNumber() == p.GetNumber())
            if abs(q.GetPosition().x - p.GetPosition().x) > 2000 or abs(q.GetPosition().y - p.GetPosition().y) > 2000:
                sys.exit(f"trial_placement_p3: {ref} pad {p.GetNumber()} of {fpid} is not at the old pad")
            p.SetNet(onet[p.GetNumber()])
        swapped[ref] = dict(old=old.GetFPIDAsString(), new=fpid)
        b.Remove(old)
        fps[ref] = new
    tracks = list(b.GetTracks())
    rec = {"footprints": swapped, "place": {}, "new": {}, "groups": {}, "deleted": collections.Counter(), "deleted_by_ref": collections.Counter(),
           "deleted_items": [], "slots": {}, "keepouts": {}, "texts": {}, "unplaced": dict(UNPLACED)}
    off0 = offboard(b, fps)
    moved = set(PLACE) | set(NEW) | {r for refs, _, _ in GROUPS.values() for r in refs}
    for r in moved | set(UNPLACED) | set(TEXTS):
        if r not in fps:
            sys.exit(f"trial_placement_p3: {r} not on the step-2 board")
    for r in NEW:
        if r not in off0:
            sys.exit(f"trial_placement_p3: {r} is not in the off-board grid")
    missing = [r for r in off0 if r not in NEW and r not in UNPLACED]
    if missing:
        sys.exit(f"trial_placement_p3: off-board parts neither in NEW nor in UNPLACED: {missing}")
    pads_by_net = collections.defaultdict(list)
    for ref, fp in fps.items():
        for p in fp.Pads():
            pads_by_net[p.GetNetCode()].append((ref, p))

    def tdom(t):
        return dom_of.get(t.GetNetname(), "")

    # --- rigid groups: the group's own copper (as steps 1 / 2)
    at = collections.defaultdict(list)
    for t in tracks:
        for pt in T.track_points(t):
            at[(pt.x // T.EPS, pt.y // T.EPS)].append(t)

    def neighbours(t):
        out = []
        for pt in T.track_points(t):
            kx, ky = pt.x // T.EPS, pt.y // T.EPS
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for u in at.get((kx + dx, ky + dy), ()):
                        if u is not t and u.GetNetCode() == t.GetNetCode() and any(
                                abs(q.x - pt.x) <= T.EPS and abs(q.y - pt.y) <= T.EPS for q in T.track_points(u)):
                            out.append(u)
        return out

    internal = {}
    for gname, (refs, dx, dy) in GROUPS.items():
        gfps = [fps[r] for r in refs]
        box = T.group_box(gfps)
        gpads = [p for fp in gfps for p in fp.Pads()]
        nets = {p.GetNetCode() for p in gpads if p.GetNetCode() > 0}
        cand = [t for t in tracks if t.GetNetCode() in nets]
        inside = lambda t: all(box.Contains(pt) for pt in T.track_points(t))  # noqa: E731

        def foreign(t):
            for ref, p in pads_by_net.get(t.GetNetCode(), ()):
                if ref not in refs and t.GetBoundingBox().Intersects(p.GetBoundingBox()) and R.overlaps(p, t):
                    return True
            return False
        seen = {}
        todo = []
        for p in gpads:
            pb = p.GetBoundingBox()
            for t in cand:
                if t.GetBoundingBox().Intersects(pb) and R.overlaps(p, t) and inside(t) and not foreign(t):
                    seen[t.m_Uuid.AsString()] = t
                    todo.append(t)
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

    on_board = [r for r in moved if r not in off0]
    before = set(P2.check(b, fps, on_board))
    kill = {}

    def mark(t, why, ref, force=False):
        k = t.m_Uuid.AsString()
        if k not in kill and (force or k not in internal):
            kill[k] = (t, why, ref)

    # copper on the old pads of the moved 5.1 parts
    for r in sorted(on_board):
        for p in fps[r].Pads():
            pb = p.GetBoundingBox()
            for t in tracks:
                if t.GetBoundingBox().Intersects(pb) and R.overlaps(p, t):
                    mark(t, "touches old pad of moved part", r)

    # --- move
    for ref, (x, y, rot) in PLACE.items():
        fp = fps[ref]
        old = (mm(fp.GetPosition().x), mm(fp.GetPosition().y), fp.GetOrientationDegrees())
        fp.SetPosition(pcbnew.VECTOR2I(nm(x), nm(y)))
        fp.SetOrientationDegrees(rot)
        rec["place"][ref] = dict(old=old, new=(x, y, rot), side="B" if fp.IsFlipped() else "F")
    for ref, (x, y, rot, side) in NEW.items():
        fp = fps[ref]
        old = (mm(fp.GetPosition().x), mm(fp.GetPosition().y), fp.GetOrientationDegrees())
        fp.SetPosition(pcbnew.VECTOR2I(nm(x), nm(y)))
        if (side == "B") != fp.IsFlipped():
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fp.SetOrientationDegrees(rot)
        rec["new"][ref] = dict(old=old, new=(x, y, rot), side=side)
    for gname, (refs, dx, dy) in GROUPS.items():
        v = pcbnew.VECTOR2I(nm(dx), nm(dy))
        for r in refs:
            fps[r].Move(v)
    for t in tracks:
        g = internal.get(t.m_Uuid.AsString())
        if g:
            _, dx, dy = GROUPS[g]
            t.Move(pcbnew.VECTOR2I(nm(dx), nm(dy)))

    def live():
        return [t for t in tracks if t.m_Uuid.AsString() not in kill]

    # copper of another net within 1.0 mm (HV net: 1.25 mm) of a new pad of a moved / added part
    for r in sorted(moved):
        for p in fps[r].Pads():
            clr = HV_CLEAR if cls_of.get(p.GetNetname(), "").startswith("HV_") else NEW_CLEAR if r in NEW else T.CLEAR_NEW
            pb = p.GetBoundingBox()
            pb.Inflate(nm(clr))
            for t in live():
                if t.GetNetCode() == p.GetNetCode() or not t.GetBoundingBox().Intersects(pb):
                    continue
                c = max(clr, HV_CLEAR) if cls_of.get(t.GetNetname(), "").startswith("HV_") else clr
                if T.near(p, t, nm(c)):
                    mark(t, f"within {c:g} mm of a new pad of a moved part", r)

    # copper moved with a group: where it now comes too close to a pad of another net it is deleted itself, other
    # copper of another net too close to it is deleted (HV net involved: 1.25 mm, else 0.25 mm)
    def hv(n):
        return cls_of.get(n, "").startswith("HV_")
    gpads = [(r, p) for r, fp in fps.items() if r not in off0 or r in NEW for p in fp.Pads() if p.GetNetCode() > 0]
    for gt in [t for t in tracks if t.m_Uuid.AsString() in internal]:
        gname = internal[gt.m_Uuid.AsString()].split(" ")[0]
        gb = gt.GetBoundingBox()
        gb.Inflate(nm(HV_CLEAR))
        for r, p in gpads:
            if p.GetNetCode() == gt.GetNetCode() or not gb.Intersects(p.GetBoundingBox()):
                continue
            c = HV_CLEAR if hv(gt.GetNetname()) or hv(p.GetNetname()) else 0.25
            if pad_near(p, gt, c, P2.COPPER):
                mark(gt, f"moved with its group to within {c:g} mm of a pad of another net", r, force=True)
                break
        if gt.m_Uuid.AsString() in kill:
            continue
        for t in live():
            if t.m_Uuid.AsString() in internal or t.GetNetCode() == gt.GetNetCode() or not gb.Intersects(t.GetBoundingBox()):
                continue
            c = HV_CLEAR if hv(gt.GetNetname()) or hv(t.GetNetname()) else 0.25
            if tt_near(gt, t, c):
                mark(t, f"within {c:g} mm of copper moved with a group", gname)

    # explicit deletions
    for net, layer, (px, py), why in DELETE:
        hit = False
        pt = pcbnew.VECTOR2I(nm(px), nm(py))
        for t in live():
            if t.GetNetname() == net and t.Type() != pcbnew.PCB_VIA_T and b.GetLayerName(t.GetLayer()) == layer and \
                    t.HitTest(pt, nm(0.05)):
                mark(t, why, net)
                hit = True
        if not hit:
            sys.exit(f"trial_placement_p3: DELETE {net} {layer} ({px}, {py}): no track there")

    all_pads = [(r, p) for r, fp in fps.items() if r not in off0 or r in NEW for p in fp.Pads()]
    # 1. heater: primary copper on the inner layers within 8.0 mm of the heater barrels at the new slot
    for r, n in HEATER_BARRELS:
        p = next(q for q in fps[r].Pads() if q.GetNumber() == n)
        pb = p.GetBoundingBox()
        pb.Inflate(nm(HEATER_SPACING))
        for t in live():
            if tdom(t) == "PRI" and t.GetBoundingBox().Intersects(pb) and pad_near(p, t, HEATER_SPACING - 0.01, P2.INNER):
                mark(t, f"primary copper within {HEATER_SPACING:g} mm of a heater barrel (inner layer)", f"{r}.{n}")
    # 1. heater: primary tracks / vias within 8.0 mm of heater copper on the same layer, inside the boxes
    hpads = [(r, p) for r, p in all_pads if dom_of.get(p.GetNetname(), "") == "HEATER"]
    for box in HEATER_BOXES:
        htr = [t for t in live() if tdom(t) == "HEATER"]
        for t in live():
            if tdom(t) != "PRI" or not in_box(t, box):
                continue
            tb = t.GetBoundingBox()
            tb.Inflate(nm(HEATER_SPACING))
            hit = next((r for r, p in hpads if tb.Intersects(p.GetBoundingBox())
                        and pad_near(p, t, HEATER_SPACING - 0.01, P2.COPPER)), None)
            if hit is None:
                hit = next((h.GetNetname() for h in htr if tb.Intersects(h.GetBoundingBox())
                            and tt_near(h, t, HEATER_SPACING - 0.01)), None)
            if hit is not None:
                mark(t, f"primary copper within {HEATER_SPACING:g} mm of the heater island", hit)
    # 2. PE pads / mounting holes: primary / secondary tracks and vias inside the basic spacing
    pe_pads = [(r, p) for r, p in all_pads if dom_of.get(p.GetNetname(), "") == "PE"]
    holes = [(r, p) for r, p in all_pads if r in HOLE_DOMAIN]
    for t in live():
        s = PE_SPACING.get(tdom(t))
        if s is None:
            continue
        tb = t.GetBoundingBox()
        tb.Inflate(nm(s))
        for r, p in pe_pads:
            if tb.Intersects(p.GetBoundingBox()) and pad_near(p, t, s - 0.01, P2.COPPER):
                mark(t, f"within {s:g} mm of a PE pad", r)
                break
        for r, p in holes:
            if not tb.Intersects(p.GetBoundingBox()):
                continue
            hole = p.GetEffectiveHoleShape()
            if pad_near(p, t, s - 0.01, P2.COPPER) or any(
                    on_layer(t, l) and hole.Collide(t.GetEffectiveShape(l), nm(s - 0.01)) for l in P2.COPPER):
                mark(t, f"within {s:g} mm of a mounting hole (earthed)", r)
                break
    # 2. PE tracks within 3.2 mm of a primary pad
    ppads = [(r, p) for r, p in all_pads if dom_of.get(p.GetNetname(), "") == "PRI"]
    for t in live():
        if tdom(t) != "PE":
            continue
        tb = t.GetBoundingBox()
        tb.Inflate(nm(PE_SPACING["PRI"]))
        for r, p in ppads:
            if tb.Intersects(p.GetBoundingBox()) and pad_near(p, t, PE_SPACING["PRI"] - 0.01, P2.COPPER):
                mark(t, f"PE track within {PE_SPACING['PRI']:g} mm of a primary pad", r)
                break

    # slots: copper crossing a slot (+ 0.3 mm board edge clearance)
    for name, (poly, rects, width) in SLOTS.items():
        for x0, y0, x1, y1 in rects:
            sb = pcbnew.BOX2I(pcbnew.VECTOR2I(nm(x0 - 0.3), nm(y0 - 0.3)), pcbnew.VECTOR2L(nm(x1 - x0 + 0.6), nm(y1 - y0 + 0.6)))
            for t in live():
                if not t.GetBoundingBox().Intersects(sb):
                    continue
                pts = T.track_points(t)
                w = t.GetWidth(pcbnew.F_Cu) / 2 if t.Type() == pcbnew.PCB_VIA_T else t.GetWidth() / 2
                if len(pts) == 2:
                    hit = P2.seg_hits_box(pts[0].x, pts[0].y, pts[1].x, pts[1].y, sb.GetLeft() - w, sb.GetTop() - w,
                                          sb.GetRight() + w, sb.GetBottom() + w)
                else:
                    c = pts[0]
                    hit = sb.GetLeft() - w <= c.x <= sb.GetRight() + w and sb.GetTop() - w <= c.y <= sb.GetBottom() + w
                if hit:
                    mark(t, "crosses a new slot", name)
            for r, p in all_pads:   # a pad in the slot cannot be fixed by deleting copper
                if any(p.IsOnLayer(l) for l in P2.COPPER) and p.GetBoundingBox().Intersects(sb):
                    sys.exit(f"trial_placement_p3: pad {r}.{p.GetNumber()} in the slot '{name}'")
        rec["slots"][name] = dict(poly=poly, rects=rects, width=width)

    # pour keep-outs
    def keep(name, pts, what="no copper pour"):
        add_keepout_poly(b, name, pts)
        xs, ys = [q[0] for q in pts], [q[1] for q in pts]
        rec["keepouts"][name] = dict(x0=min(xs), y0=min(ys), x1=max(xs), y1=max(ys), pts=[list(q) for q in pts],
                                     layers="all copper", what=what)
    for name, (x0, y0, x1, y1) in KEEPOUTS.items():
        keep(name, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    for r, d in sorted(HOLE_DOMAIN.items()):
        c = fps[r].GetPosition()
        keep(f"mounting hole {r} pour keep-out ({'primary 3.2' if d == 'PRI' else 'secondary 4.2'} mm creepage)",
             circle(mm(c.x), mm(c.y), HOLE_KEEPOUT[d]))
    # PE copper (pads and the PE tracks that stay) + 3.25 mm
    pe = pcbnew.SHAPE_POLY_SET()
    for r, p in pe_pads:
        layer = next(l for l in P2.COPPER if p.IsOnLayer(l))
        p.TransformShapeToPolygon(pe, layer, nm(PE_KEEPOUT), nm(0.02), pcbnew.ERROR_OUTSIDE)
    for t in live():
        if tdom(t) == "PE":
            t.TransformShapeToPolygon(pe, t.GetLayer(), nm(PE_KEEPOUT), nm(0.02), pcbnew.ERROR_OUTSIDE)
    pe.Simplify()
    for i in range(pe.OutlineCount()):
        o = pe.Outline(i)
        o.Simplify(nm(0.05))
        pts = [(mm(o.CPoint(k).x), mm(o.CPoint(k).y)) for k in range(o.PointCount())]
        keep(f"PE pour keep-out {i + 1} (PE pads / tracks + {PE_KEEPOUT:g} mm)", pts)

    # reference texts
    for ref, (x, y, ang) in TEXTS.items():
        t = fps[ref].Reference()
        rec["texts"][ref] = dict(old=(mm(t.GetPosition().x), mm(t.GetPosition().y)), new=(x, y, ang))
        t.SetPosition(pcbnew.VECTOR2I(nm(x), nm(y)))
        t.SetTextAngleDegrees(ang)

    old = {(k, n): a for k, n, a in before}
    rec["check"] = [f"{k} {n}" + (f" {a} mm2" if a else "") + (f" (step 2: {old[(k, n)]})" if (k, n) in old else "")
                    for k, n, a in P2.check(b, fps, moved) if old.get((k, n), -1) < a - 0.05]
    rec["offboard"] = offboard(b, fps)
    for t, why, r in kill.values():
        kind = "via" if t.Type() == pcbnew.PCB_VIA_T else "segment"
        rec["deleted"][f"{kind}: {why}"] += 1
        rec["deleted_by_ref"][r] += 1
        pts = [(mm(q.x), mm(q.y)) for q in T.track_points(t)]
        rec["deleted_items"].append(dict(kind=kind, net=t.GetNetname(), layer=b.GetLayerName(t.GetLayer()) if kind == "segment" else "via",
                                         pts=pts, width=mm(t.GetWidth(pcbnew.F_Cu) if kind == "via" else t.GetWidth()),
                                         why=why, ref=r))
        b.Remove(t)
    rec["deleted"] = dict(rec["deleted"])
    rec["deleted_by_ref"] = dict(rec["deleted_by_ref"].most_common())
    if not write:
        if "--save" in sys.argv:   # scratch copy for a look (no project files)
            pcbnew.SaveBoard(sys.argv[sys.argv.index("--save") + 1], b)
        return rec

    # the step-2 project file; the rules are the current 5.2 rules (kicad_next/tube_psu_5_2.kicad_dru: Q19 / Q21 slot
    # rule and same-footprint pad gap rule of 2026-11-19)
    shutil.copy(os.path.join(R.OUTDIR, P2.NAME2 + ".kicad_pro"), os.path.join(R.OUTDIR, NAME3 + ".kicad_pro"))
    shutil.copy(os.path.join(R.PROJ, "tube_psu_5_2.kicad_dru"), os.path.join(R.OUTDIR, NAME3 + ".kicad_dru"))
    pro_path = os.path.join(R.OUTDIR, NAME3 + ".kicad_pro")
    with open(pro_path) as f:
        pro = json.load(f)
    pro.setdefault("meta", {})["filename"] = NAME3 + ".kicad_pro"
    with open(pro_path, "w") as f:
        json.dump(pro, f, indent=2)
        f.write("\n")
    pcbnew.SaveBoard(OUT3, b)
    with open(OUT3) as f:
        s = f.read()
    s = re.sub(r"\t\t\(stackup\n.*?\n\t\t\)\n", "", s, flags=re.S)
    s = s.replace("\t(setup\n", "\t(setup\n" + make_board.STACKUP, 1)
    with open(OUT3, "w") as f:
        f.write(s)
    return rec


def main(argv):
    if not os.path.exists(P2.OUT2):
        sys.exit("trial_placement_p3: run tools/next/trial_placement_p2.py first (step-2 board missing)")
    path = os.path.join(R.OUTDIR, "placement_p3.json")
    if "--dump" in argv:
        comps, _, _ = R.netlist()
        with open(path) as f:
            rec = json.load(f)
        rec["geometry"] = R.dump(pcbnew.LoadBoard(OUT3), comps)
        with open(path, "w") as f:
            json.dump(rec, f, indent=1, sort_keys=True)
        return 0
    if "--check" in argv:
        rec = build(write=False)
        print("\n".join(rec["check"]) or "no new courtyard overlaps / pad shorts of the moved and added parts")
        print("deleted:", rec["deleted"])
        print("by part:", rec["deleted_by_ref"])
        print("still off-board:", rec["offboard"])
        return 0
    rec = build()
    rec["moves"] = dict(place={k: list(v) for k, v in PLACE.items()}, new={k: list(v) for k, v in NEW.items()},
                        groups={k: dict(refs=v[0], dx=v[1], dy=v[2]) for k, v in GROUPS.items()})
    with open(path, "w") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
    subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, sys.argv[1]); import reuse_51_board as R; "
                    "R.run_drc(name=sys.argv[2], out_json='drc_p3.json')", HERE, NAME3], check=True)
    for f in ("fp-info-cache", NAME3 + ".kicad_prl"):
        if os.path.exists(os.path.join(R.OUTDIR, f)):
            os.remove(os.path.join(R.OUTDIR, f))
    subprocess.run([sys.executable, os.path.abspath(__file__), "--dump"], check=True)
    print(f"trial_placement_p3: {os.path.relpath(OUT3, R.ROOT)}: moved {len(PLACE)} parts + {len(GROUPS)} groups, "
          f"placed {len(NEW)} new parts; deleted {rec['deleted']}")
    if "--no-report" not in argv:
        env = {k: v for k, v in os.environ.items() if k not in ("PYTHONHOME", "PYTHONPATH")}
        subprocess.run(["python3", os.path.join(HERE, "trial_report.py")], check=True, env=env)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
