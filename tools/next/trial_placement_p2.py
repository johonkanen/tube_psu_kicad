#!/usr/bin/env python3
"""Placement step 2 on the TRIAL 5.2 board built from the 5.1 layout (run with tools/p2k/bin/kipy).

    tools/p2k/bin/kipy tools/next/reuse_51_board.py --no-report    step 0 (reuse of 5.1)
    tools/p2k/bin/kipy tools/next/trial_placement.py --no-report   step 1 (TR3, split caps, DRV5 / DRV6)
    tools/p2k/bin/kipy tools/next/trial_placement_p2.py [--no-report] [--check]   step 2 (this script)

Input:  kicad_next/trial_from_51/tube_psu_5_2_trial_p1.kicad_pcb (step 1)
Output: tube_psu_5_2_trial_p2.kicad_pcb (+ .kicad_pro / .kicad_dru copies), drc_p2.json (the split-pass DRC of
        reuse_51_board.run_drc), placement_p2.json (moves, slot, keep-out, deleted copper with positions so the
        routing can redo it, geometry for the drawings), then tools/next/trial_report.py (REPORT.md section
        "After placement step 2", zoom_p2_*.png). --check: build only and print the courtyard overlaps / pad
        shorts of the moved parts (no DRC, nothing written). kicad_next/tube_psu_5_2.kicad_pcb is not touched.

Step 2 (moves as data below; nothing is routed, only copper that violates or is orphaned is deleted):
 1. UART island (J4 isolated 4-pin header GND / 3V3 / TXD / RXD, U11 CA-IS3721HW slot footprint, C134 / C135, R136 / R137) at
    the top board edge left of TR3 (old L3 area, outside the heatsink L, so the cable reaches the edge): U11 at 0 deg
    with its primary pins 1-8 facing the primary Q10 / heater-LLC side and its 8 mm slot between, the island side
    (J4, cap, series resistors) between U11 and C47, next to H2. Primary copper: tracks / vias of a primary net
    within 8.0 mm of an island pad are deleted on every layer, and a copper-pour keep-out (rule area, all copper
    layers) covers the island + 8 mm. C47 / C54 move 1.2 mm right (towards the TR3 pins, still 1.9 mm from them) and
    the bottom-side current-measurement amplifier U1 with its parts (+ C87 on top) 8 mm down to make the 8 mm.
 2. Q19 / Q21 (TO row, heatsink): a 1.2 mm routed L-slot (board Edge.Cuts): between Q19 pin 1 and Q21 pin 3 at
    x = 51.4 (inside the TR3 barrier band x 42.5 ... 54.5) from under TR3 (y -62) down to the heatsink plate, then
    under the plate (y -37.5) to x 68.6, past the top of the ISO2 slot (ISO2 pins 1 / 2 vs Q21 / Q8); pour keep-outs
    where 5.1 pours bridge a barrier gap (under the plate, ISO2 / TR1 slot gap, TR1 slot end at the fly leads);
    Q19 / Q21 pads lose their unused inner-layer rings (like the TR1 barrier pads); inner-layer copper of the
    other domain within 11.1 mm of the Q19 / Q21 barrels is deleted; tracks / vias crossing the slot are deleted.
 3. ISO2 stays across the barrier (its slot already on it; the L-slot closes its top end); D4 (secondary 15 V rectifier) moves right of ISO2 out of
    the ISO2 slot, C2 0.6 mm right, C3 0.6 mm right; D5 (primary) 1 mm up on the primary side.
 4. TR1 stays at its 5.1 origin and is made free: PWM2 4.7 mm left (drain end away from TR1, room for the drain
    copper left of it), its CS resistors R8 / R9 above it, the clamp D7 / R72 left of the fly leads, C14 / D6 left,
    the secondary parts right of TR1 1.4 mm right, C102 1.85 mm right (11.1 mm to the DC+ fly lead).
 5. Gate-driver bootstrap / decoupling parts next to their pins, outside the SOIC-16W / SOIC-8 bodies
    (DRV5: C92 / C94 / C95, DRV6: C46 / C93 / R46, DRV3: C18 / C25 / C53 / D11 / R99 / R78, DRV4: DRV4 / Q1 / C17 / R63).
Copper rules for every moved part (as step 1): copper touching an old pad is deleted, copper of another net within
1.0 mm of a new pad is deleted, inner-layer copper of another isolation domain within the domain spacing of a moved
THT pad is deleted. Zones are refilled by the DRC.
"""
import collections
import json
import math
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
import trial_placement as T  # noqa: E402  (OUT1, near, nm, track_points, group_box)

NAME2 = R.NAME + "_p2"
OUT2 = os.path.join(R.OUTDIR, NAME2 + ".kicad_pcb")

# --- 1. UART island -----------------------------------------------------------------------------------
ISLAND = ["J4", "U11", "C134", "C135", "R136", "R137"]   # U12 / C136 / C137 LDO removed 2026-11-19 (3V3 from the minimodule)
# --- the moves (board mm, KiCad orientation in degrees) ------------------------------------------------
PLACE = {   # ref: (x, y, orientation) - absolute
    # 1. UART island (top edge, x -6 ... 13.8)
    "U11": (0.0, -78.0, 0.0),        # pins 1-8 (primary) at x -4.65, pins 9-16 (island) at x 4.65, slot x 0
    "J4": (11.4, -89.0, 0.0),        # 1x4: pin 1 (ISO_UART_GND) at the top edge, pins down to y -81.4
    "C47": (23.05, -86.5, -90.0),    # 0.55 mm right (courtyard to the TR3 courtyard): 8.1 mm from J4
    "C54": (23.05, -78.5, -90.0),
    # 2. -
    # 3. TR1 secondary rectifier out of the ISO2 slot
    "D4": (76.8, -19.2, 180.0),
    "C2": (78.07, -12.53, -90.0),
    "C3": (73.25, -12.89, -90.0),
    # 4. flyback: TR1 free, C102 11.1 mm from the DC+ fly lead
    "PWM2": (49.8, 2.2, -90.0),
    "R9": (50.45, -3.1, 180.0),
    "R8": (50.45, -5.4, 180.0),
    "D7": (51.4, 12.4, 0.0),
    "R72": (48.3, 15.5, 0.0),
    "C14": (52.4, -13.5, 0.0),
    "D5": (58.75, -20.91, -90.0),    # primary 15 V rectifier 1 mm up: 11.1 mm to TR1 pin 10 through the slot gap
    "D6": (51.6, -6.25, 0.0),
    "C58": (49.4, 6.0, 90.0),
    "C51": (53.7, 6.8, 90.0),
    "C102": (74.5, 11.35, 0.0),
    # 5. DRV4: SOIC-8 turned 90 deg between C32 and Q1 (the 5.1 DFN was 2 mm narrower)
    "DRV4": (-54.75, -68.35, 90.0),  # turned: pins 5-8 on top (OUTA towards Q1 gate, VDD)
}
# two-pad parts placed by centre + axis; the orientation (0 / 180 or 90 / -90) is picked so that the pads land
# next to the pins they belong to: ref: (x, y, "h" | "v", {pad: (ref, pad)})
AUTO = {
    # 1. UART island
    "C135": (7.0, -81.2, "v", {"1": ("U11", "14"), "2": ("U11", "16")}),
    "R137": (7.6, -78.2, "h", {"1": ("U11", "13"), "2": ("J4", "4")}),
    "R136": (7.6, -76.4, "h", {"1": ("U11", "12"), "2": ("J4", "3")}),
    "C134": (-7.3, -81.0, "v", {"1": ("U11", "3"), "2": ("U11", "1")}),
    # 5. DRV5 (bottom, rot 0, pins 1-8 x 15.55, 9-16 x 24.85)
    "C94": (13.0, -52.6, "v", {"1": ("DRV5", "3"), "2": ("DRV5", "4")}),
    "C95": (24.0, -47.2, "h", {"1": ("DRV5", "14"), "2": ("DRV5", "16")}),
    "C92": (25.3, -60.9, "h", {"1": ("DRV5", "9"), "2": ("DRV5", "11")}),
    # DRV6 (bottom, rot 180, pins 1-8 x 65.66, 9-16 x 56.36)
    "C46": (57.0, -63.75, "h", {"1": ("DRV6", "14"), "2": ("DRV6", "16")}),
    "R46": (62.0, -63.74, "h", {"1": ("D18", "C"), "2": ("DRV6", "16")}),
    "C93": (65.6, -50.6, "h", {"1": ("DRV6", "8"), "2": ("DRV6", "4")}),
    # DRV3 (bottom, rot 90, pins 1-8 y -50, 9-16 y -59.3)
    "C25": (-14.3, -59.6, "v", {"1": ("DRV3", "16"), "2": ("DRV3", "14")}),
    "R99": (-10.7, -58.3, "h", {"1": ("D11", "C"), "2": ("DRV3", "16")}),
    "D11": (-11.5, -55.0, "h", {"A": ("C18", "1"), "C": ("R99", "1")}),
    "C18": (-24.5, -61.9, "h", {"1": ("DRV3", "11"), "2": ("DRV3", "9")}),
    "C53": (-19.8, -47.6, "h", {"1": ("DRV3", "3"), "2": ("DRV3", "4")}),
    "R78": (-14.4, -51.0, "v", {"2": ("DRV3", "1"), "1": ("DRV3", "4")}),
    # DRV4 (top, SOIC-8)
    "R63": (-54.0, -73.3, "h", {"1": ("Q1", "2"), "2": ("DRV4", "7")}),
    "C17": (-56.7, -73.8, "v", {"1": ("DRV4", "8"), "2": ("DRV4", "3")}),
}
GROUPS = {  # name: (refs, dx, dy) - rigid translation with the group's own copper
    "U1 current-measurement amplifier (bottom) + C87": (
        ["U1", "R101", "R102", "R103", "R104", "R105", "R106", "R29", "C63", "C11", "R89", "C87"], 0.0, 8.0),
    "TR1 secondary rectifiers right of TR1": (["D14", "C45", "D8"], 1.4, 0.0),
    "TR1 -15 V caps right of TR1": (["C40", "C44"], 0.4, 0.0),
}
# --- 2. routed slots (board Edge.Cuts, closed polygons) -------------------------------------------------
SLOT_W = 1.2
SX0, SX1 = 51.415 - SLOT_W / 2, 51.415 + SLOT_W / 2     # Q19 pin 1 x 48.155 | Q21 pin 3 x 54.675
HY0, HY1 = -40.4, -40.4 + SLOT_W   # horizontal leg just below the Q21 / Q8 pins (pad edge y -40.95), in front of the plate
SLOTS = {   # name: (outline polygon, rectangles it is made of) - JLC mills it with the slot cutter
    # vertical leg between Q19 and Q21 from under TR3 (inside its 12 mm barrier band) down to the TO pins, then
    # along the row under the Q21 / Q8 pins (0.55 mm from their pads, in front of the heatsink plate face at y -38.8)
    # to x 68.6, past the top end of the ISO2 slot (x 66.76, y -36.35; 2.85 mm bridge to it), so the ISO2 primary
    # pins 1 / 2 see Q21 / Q8 only around the slot
    "Q19 / Q21 / ISO2 barrier slot (L)": (
        [(SX0, -62.0), (SX1, -62.0), (SX1, HY0), (68.6, HY0), (68.6, HY1), (SX0, HY1)],
        [(SX0, -62.0, SX1, HY1), (SX0, HY0, 68.6, HY1)]),
}
# --- copper-pour keep-outs (rule areas, every copper layer) --------------------------------------------
UART_SPACING = 8.0
KEEPOUT_PAD = UART_SPACING        # island pads bounding box + this
KEEPOUTS = {   # more copper-pour keep-outs (rule areas, every copper layer): the 5.1 pours that reach a barrier gap
    "barrier pour keep-out: Q21 / Q8 to ISO2 under the heatsink plate": (52.5, -39.2, 71.0, -33.0),
    "barrier pour keep-out: bridge between the L-slot and the ISO2 slot": (60.5, -33.0, 73.0, -26.0),
    "barrier pour keep-out: gap between the ISO2 and TR1 slots": (56.5, -23.0, 73.5, -9.5),
    "barrier pour keep-out: around the TR1 slot end at the fly leads": (57.5, 4.0, 77.0, 18.4),
}
PAD_INNER_REMOVE = ["Q19", "Q21"]  # THT pads without unused inner-layer rings (barrier pads, as TR1)
BARRIER_THT = ["Q19", "Q21", "C102"]  # inner-layer copper of the other domain within the spacing is deleted
FLY_LEADS = [("TR1", "11"), ("TR1", "12")]   # TR1 primary fly leads: other-domain copper within 11.1 mm, every layer
# inner-layer barrier bands (no creepage credit for the slots there): copper of either domain closer than half the
# spacing to the barrier line is deleted, so the two sides stay 11.1 mm apart: (x line, y0, y1, half width)
INNER_BANDS = {"ISO2 slot line (inner layers)": (66.76, -39.0, -14.0, 5.55)}
CLASS_DOMAIN = {"HV_PRIMARY": "PRI", "PRIMARY_LV": "PRI", "SIGNAL": "PRI", "HV_SECONDARY": "SEC",
                "SECONDARY_LV": "SEC", "HEATER": "HEATER", "UART_ISO": "UART", "PE_EARTH": "PE"}
SPACING = {frozenset(("PRI", "SEC")): 11.1, frozenset(("PRI", "UART")): 8.0, frozenset(("PRI", "HEATER")): 8.0,
           frozenset(("SEC", "UART")): 8.4, frozenset(("SEC", "HEATER")): 5.2}
INNER = [pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu]
COPPER = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu]
nm, mm = T.nm, R.mm


def domains():
    with open(os.path.join(R.OUTDIR, R.NAME + "_p1.kicad_pro")) as f:
        pro = json.load(f)
    return {p["pattern"]: CLASS_DOMAIN.get(p["netclass"], "") for p in pro["net_settings"]["netclass_patterns"]}


def dist_pad_track(pad, t, layers):
    """min distance (mm) between a pad and a track / via on any of the given layers (None if no common layer)"""
    best = None
    for layer in layers:
        if not pad.IsOnLayer(layer):
            continue
        if t.Type() == pcbnew.PCB_VIA_T:
            if not t.IsOnLayer(layer):
                continue
        elif t.GetLayer() != layer:
            continue
        a = pad.GetEffectiveShape(layer)
        b = t.GetEffectiveShape(layer)
        for d in (0.0, 1.0, 2.0, 4.0, 6.0, 8.0, 10.0, 11.1, 12.0):
            if a.Collide(b, nm(d)):
                best = d if best is None else min(best, d)
                break
    return best


def collide(pad, t, clr_mm, layers):
    for layer in layers:
        if not pad.IsOnLayer(layer):
            continue
        if t.Type() == pcbnew.PCB_VIA_T:
            if not t.IsOnLayer(layer):
                continue
        elif t.GetLayer() != layer:
            continue
        if pad.GetEffectiveShape(layer).Collide(t.GetEffectiveShape(layer), nm(clr_mm)):
            return True
    return False


def collide_2d(pad, t, clr_mm):
    """pad (any of its copper layers, projected) within clr of the track / via (on its own layer)"""
    pl = [l for l in COPPER if pad.IsOnLayer(l)]
    if not pl:
        return False
    a = pad.GetEffectiveShape(pl[0])
    tl = pcbnew.F_Cu if t.Type() == pcbnew.PCB_VIA_T else t.GetLayer()
    return a.Collide(t.GetEffectiveShape(tl), nm(clr_mm))


def auto_orient(fp, x, y, axis, want, fps):
    """place a 2-pad part at (x, y) with its axis h / v, choosing the orientation that puts each pad nearest
    to its target pin"""
    best = None
    for rot in ((0.0, 180.0) if axis == "h" else (90.0, -90.0)):
        fp.SetPosition(pcbnew.VECTOR2I(nm(x), nm(y)))
        fp.SetOrientationDegrees(rot)
        cost = 0.0
        for pnum, (tref, tpad) in want.items():
            p = next(q for q in fp.Pads() if q.GetNumber() == pnum)
            tp = next(q for q in fps[tref].Pads() if q.GetNumber() == tpad)
            cost += math.hypot(p.GetPosition().x - tp.GetPosition().x, p.GetPosition().y - tp.GetPosition().y)
        if best is None or cost < best[0]:
            best = (cost, rot)
    fp.SetOrientationDegrees(best[1])
    return best[1]


def seg_hits_box(ax, ay, bx, by, x0, y0, x1, y1):
    """segment a-b intersects the box (Liang-Barsky clipping)"""
    t0, t1 = 0.0, 1.0
    dx, dy = bx - ax, by - ay
    for p, q in ((-dx, ax - x0), (dx, x1 - ax), (-dy, ay - y0), (dy, y1 - ay)):
        if p == 0:
            if q < 0:
                return False
            continue
        r = q / p
        if p < 0:
            t0 = max(t0, r)
        else:
            t1 = min(t1, r)
        if t0 > t1:
            return False
    return True


def add_slot(b, pts):
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_POLY)
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(nm(0.05))
    s.SetFilled(False)
    s.SetPolyPoints([pcbnew.VECTOR2I(nm(px), nm(py)) for px, py in pts])
    b.Add(s)
    return s


def add_keepout(b, name, x0, y0, x1, y1):
    z = pcbnew.ZONE(b)
    z.SetIsRuleArea(True)
    z.SetZoneName(name)
    z.SetDoNotAllowZoneFills(True)
    z.SetDoNotAllowTracks(False)
    z.SetDoNotAllowVias(False)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    ls = pcbnew.LSET()
    for l in COPPER:
        ls.AddLayer(l)
    z.SetLayerSet(ls)
    o = z.Outline()
    o.NewOutline()
    for px, py in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        o.Append(nm(px), nm(py))
    b.Add(z)
    return z


def court_poly(fp):
    side = pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd
    return fp.GetCourtyard(side)


def check(b, fps, moved):
    """courtyard overlaps (same side, area > 0.01 mm2) and pad-to-pad copper contacts of the moved parts"""
    out = []
    for r in sorted(moved):
        fp = fps[r]
        cr = court_poly(fp)
        if cr.OutlineCount() == 0:
            continue
        for o, ofp in fps.items():
            if o == r or ofp.IsFlipped() != fp.IsFlipped():
                continue
            oc = court_poly(ofp)
            if oc.OutlineCount() == 0 or not cr.BBox().Intersects(oc.BBox()):
                continue
            inter = pcbnew.SHAPE_POLY_SET(cr)
            inter.BooleanIntersection(oc)
            a = inter.Area() / 1e12
            if a > 0.01:
                out.append(("courtyard", "/".join(sorted((r, o))), round(a, 2)))
        for p in fp.Pads():
            for o, ofp in fps.items():
                if o == r:
                    continue
                for q in ofp.Pads():
                    if q.GetNetCode() == p.GetNetCode() and p.GetNetCode() > 0:
                        continue
                    if not p.GetBoundingBox().Intersects(q.GetBoundingBox()):
                        continue
                    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
                        if p.IsOnLayer(layer) and q.IsOnLayer(layer) and \
                                p.GetEffectiveShape(layer).Collide(q.GetEffectiveShape(layer), 0):
                            out.append(("pad short", f"{r}.{p.GetNumber()} / {o}.{q.GetNumber()}", 0))
                            break
    return sorted(set(out))


def build(write=True):
    b = pcbnew.LoadBoard(T.OUT1)
    fps = {fp.GetReference(): fp for fp in b.GetFootprints()}
    dom_of = domains()
    tracks = list(b.GetTracks())
    rec = {"place": {}, "groups": {}, "deleted": collections.Counter(), "deleted_by_ref": collections.Counter(),
           "deleted_items": [], "slots": {}, "keepouts": {}, "pads_inner_removed": PAD_INNER_REMOVE}
    moved = set(PLACE) | set(AUTO) | {r for refs, _, _ in GROUPS.values() for r in refs}
    for r in moved | set(ISLAND):
        if r not in fps:
            sys.exit(f"trial_placement_p2: {r} not on the step-1 board")
    pads_by_net = collections.defaultdict(list)
    for ref, fp in fps.items():
        for p in fp.Pads():
            pads_by_net[p.GetNetCode()].append((ref, p))

    # endpoint index (rigid group copper, as step 1)
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
        start = []
        for p in gpads:
            pb = p.GetBoundingBox()
            for t in cand:
                if t.GetBoundingBox().Intersects(pb) and R.overlaps(p, t) and inside(t) and not foreign(t):
                    start.append(t)
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

    before = set(check(b, fps, moved | set(ISLAND)))   # overlaps that the step-1 board already has
    kill = {}

    def mark(t, why, ref):
        k = t.m_Uuid.AsString()
        if k not in kill and k not in internal:
            kill[k] = (t, why, ref)

    # copper on the old pads of moved single parts
    for r in sorted(set(PLACE) | set(AUTO)):
        for p in fps[r].Pads():
            pb = p.GetBoundingBox()
            for t in tracks:
                if t.GetBoundingBox().Intersects(pb) and R.overlaps(p, t):
                    mark(t, "touches old pad of moved part", r)
    # group copper touching an old pad but not moving with the group
    for gname, (refs, _, _) in GROUPS.items():
        for r in refs:
            for p in fps[r].Pads():
                pb = p.GetBoundingBox()
                for t in tracks:
                    if t.GetBoundingBox().Intersects(pb) and R.overlaps(p, t):
                        mark(t, "touches old pad of moved part", r)

    # move
    for ref, (x, y, rot) in PLACE.items():
        fp = fps[ref]
        old = (mm(fp.GetPosition().x), mm(fp.GetPosition().y), fp.GetOrientationDegrees())
        fp.SetPosition(pcbnew.VECTOR2I(nm(x), nm(y)))
        fp.SetOrientationDegrees(rot)
        rec["place"][ref] = dict(old=old, new=(x, y, rot), side="B" if fp.IsFlipped() else "F")
    for ref, (x, y, axis, want) in AUTO.items():
        fp = fps[ref]
        old = (mm(fp.GetPosition().x), mm(fp.GetPosition().y), fp.GetOrientationDegrees())
        rot = auto_orient(fp, x, y, axis, want, fps)
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

    # Q19 / Q21: no unused inner-layer rings
    for r in PAD_INNER_REMOVE:
        for p in fps[r].Pads():
            p.SetUnconnectedLayerMode(pcbnew.UNCONNECTED_LAYER_MODE_REMOVE_EXCEPT_START_AND_END)

    live = [t for t in tracks if t.m_Uuid.AsString() not in kill]
    # copper of another net within 1.0 mm of a new pad of a moved part
    for r in sorted(moved):
        for p in fps[r].Pads():
            pb = p.GetBoundingBox()
            pb.Inflate(nm(T.CLEAR_NEW))
            for t in live:
                if t.GetNetCode() == p.GetNetCode() or not t.GetBoundingBox().Intersects(pb):
                    continue
                if T.near(p, t, nm(T.CLEAR_NEW)):
                    mark(t, f"within {T.CLEAR_NEW:g} mm of a new pad of a moved part", r)

    def tdom(t):
        return dom_of.get(t.GetNetname(), "")

    # UART island: primary copper within 8 mm of an island pad (every layer, projected)
    ipads = [(r, p) for r in ISLAND for p in fps[r].Pads() if dom_of.get(p.GetNetname(), "") == "UART"]
    for t in live:
        if tdom(t) != "PRI":
            continue
        tb = t.GetBoundingBox()
        for r, p in ipads:
            pb = p.GetBoundingBox()
            pb.Inflate(nm(UART_SPACING))
            if tb.Intersects(pb) and collide_2d(p, t, UART_SPACING - 0.01):
                mark(t, "primary copper within 8.0 mm of the UART island", r)
                break
    # barrier THT pads: inner-layer copper of the other domain within the domain spacing
    for r in BARRIER_THT + [x for x in sorted(moved) if x not in BARRIER_THT]:
        for p in fps[r].Pads():
            pd = dom_of.get(p.GetNetname(), "")
            if not pd or p.GetAttribute() != pcbnew.PAD_ATTRIB_PTH:
                continue
            for t in live:
                td = tdom(t)
                if not td or td == pd:
                    continue
                s = SPACING.get(frozenset((pd, td)))
                if s is None:
                    continue
                pb = p.GetBoundingBox()
                pb.Inflate(nm(s))
                if not t.GetBoundingBox().Intersects(pb):
                    continue
                # the barrel goes through every layer: test against the drill on the inner layers
                hole = p.GetEffectiveHoleShape()
                for layer in INNER:
                    on = t.IsOnLayer(layer) if t.Type() == pcbnew.PCB_VIA_T else t.GetLayer() == layer
                    if on and hole.Collide(t.GetEffectiveShape(layer), nm(s - 0.01)):
                        mark(t, f"other domain within {s:g} mm of a barrier barrel (inner layer)", r)
                        break

    # copper moved with a group that now lies on copper of another net: the other copper is deleted
    gmoved = [t for t in tracks if t.m_Uuid.AsString() in internal]
    for g in gmoved:
        gb = g.GetBoundingBox()
        gl = [l for l in COPPER if (g.IsOnLayer(l) if g.Type() == pcbnew.PCB_VIA_T else g.GetLayer() == l)]
        for t in live:
            if t.m_Uuid.AsString() in internal or t.GetNetCode() == g.GetNetCode() or not gb.Intersects(t.GetBoundingBox()):
                continue
            for l in gl:
                on = t.IsOnLayer(l) if t.Type() == pcbnew.PCB_VIA_T else t.GetLayer() == l
                if on and g.GetEffectiveShape(l).Collide(t.GetEffectiveShape(l), nm(0.2)):
                    mark(t, "under copper moved with a group", internal[g.m_Uuid.AsString()].split(" ")[0])
                    break
    # TR1 fly leads (primary, only partly behind the TR1 slot): other-domain copper within 11.1 mm on every layer
    for r, n in FLY_LEADS:
        p = next(q for q in fps[r].Pads() if q.GetNumber() == n)
        pd = dom_of.get(p.GetNetname(), "")
        for t in live:
            td = tdom(t)
            if td and td != pd and SPACING.get(frozenset((pd, td))) and collide_2d(p, t, SPACING[frozenset((pd, td))] - 0.01):
                mark(t, "other domain within 11.1 mm of a TR1 fly lead", f"{r}.{n}")
    # inner-layer barrier bands
    for name, (xl, y0, y1, hw) in INNER_BANDS.items():
        box = pcbnew.BOX2I(pcbnew.VECTOR2I(nm(xl - hw), nm(y0)), pcbnew.VECTOR2L(nm(2 * hw), nm(y1 - y0)))
        for t in live:
            if tdom(t) not in ("PRI", "SEC") or not t.GetBoundingBox().Intersects(box):
                continue
            if any(t.IsOnLayer(l) if t.Type() == pcbnew.PCB_VIA_T else t.GetLayer() == l for l in INNER):
                pts = T.track_points(t)
                hit = seg_hits_box(pts[0].x, pts[0].y, pts[-1].x, pts[-1].y, box.GetLeft(), box.GetTop(), box.GetRight(),
                                   box.GetBottom())
                if hit:
                    mark(t, "inside an inner-layer barrier band", name.split(" ")[0])
    rec["inner_bands"] = {k: dict(x=v[0], y0=v[1], y1=v[2], half_width=v[3]) for k, v in INNER_BANDS.items()}

    # slots: copper crossing a slot (+ 0.3 mm board edge clearance)
    for name, (poly, rects) in SLOTS.items():
        for x0, y0, x1, y1 in rects:
            sb = pcbnew.BOX2I(pcbnew.VECTOR2I(nm(x0 - 0.3), nm(y0 - 0.3)), pcbnew.VECTOR2L(nm(x1 - x0 + 0.6), nm(y1 - y0 + 0.6)))
            for t in live:
                if not t.GetBoundingBox().Intersects(sb):
                    continue
                pts = T.track_points(t)
                w = t.GetWidth(pcbnew.F_Cu) / 2 if t.Type() == pcbnew.PCB_VIA_T else t.GetWidth() / 2
                if len(pts) == 2:
                    hit = seg_hits_box(pts[0].x, pts[0].y, pts[1].x, pts[1].y, sb.GetLeft() - w, sb.GetTop() - w,
                                       sb.GetRight() + w, sb.GetBottom() + w)
                else:
                    c = pts[0]
                    hit = sb.GetLeft() - w <= c.x <= sb.GetRight() + w and sb.GetTop() - w <= c.y <= sb.GetBottom() + w
                if hit:
                    mark(t, "crosses a new slot", name)
        add_slot(b, poly)
        rec["slots"][name] = dict(poly=poly, rects=rects, width=SLOT_W)
    for name, (x0, y0, x1, y1) in KEEPOUTS.items():
        add_keepout(b, name, x0, y0, x1, y1)
        rec["keepouts"][name] = dict(x0=x0, y0=y0, x1=x1, y1=y1, layers="all copper", what="no copper pour")

    # UART island pour keep-out: island pads' bounding box + 8 mm, every copper layer
    xs, ys = [], []
    for r, p in ipads:
        bb = p.GetBoundingBox()
        xs += [mm(bb.GetLeft()), mm(bb.GetRight())]
        ys += [mm(bb.GetTop()), mm(bb.GetBottom())]
    edge = b.GetBoardEdgesBoundingBox()
    k = (max(min(xs) - KEEPOUT_PAD, mm(edge.GetLeft())), max(min(ys) - KEEPOUT_PAD, -91.35),
         max(xs) + KEEPOUT_PAD, max(ys) + KEEPOUT_PAD)
    add_keepout(b, "UART island pour keep-out (8 mm)", *k)
    rec["keepouts"]["UART island pour keep-out (8 mm)"] = dict(x0=k[0], y0=k[1], x1=k[2], y1=k[3],
                                                                layers="all copper", what="no copper pour")

    old = {(k, n): a for k, n, a in before}
    rec["check"] = [f"{k} {n}" + (f" {a} mm2" if a else "") + (f" (step 1: {old[(k, n)]})" if (k, n) in old else "")
                    for k, n, a in check(b, fps, moved | set(ISLAND)) if old.get((k, n), -1) < a - 0.05]
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
        return rec

    for ext in (".kicad_pro", ".kicad_dru"):
        shutil.copy(os.path.join(R.OUTDIR, R.NAME + ext), os.path.join(R.OUTDIR, NAME2 + ext))
    pro_path = os.path.join(R.OUTDIR, NAME2 + ".kicad_pro")
    with open(pro_path) as f:
        pro = json.load(f)
    pro.setdefault("meta", {})["filename"] = NAME2 + ".kicad_pro"
    with open(pro_path, "w") as f:
        json.dump(pro, f, indent=2)
        f.write("\n")
    pcbnew.SaveBoard(OUT2, b)
    with open(OUT2) as f:
        s = f.read()
    s = re.sub(r"\t\t\(stackup\n.*?\n\t\t\)\n", "", s, flags=re.S)
    s = s.replace("\t(setup\n", "\t(setup\n" + make_board.STACKUP, 1)
    with open(OUT2, "w") as f:
        f.write(s)
    return rec


def main(argv):
    if not os.path.exists(T.OUT1):
        sys.exit("trial_placement_p2: run tools/next/trial_placement.py first (step-1 board missing)")
    path = os.path.join(R.OUTDIR, "placement_p2.json")
    if "--dump" in argv:
        comps, _, _ = R.netlist()
        with open(path) as f:
            rec = json.load(f)
        rec["geometry"] = R.dump(pcbnew.LoadBoard(OUT2), comps)
        with open(path, "w") as f:
            json.dump(rec, f, indent=1, sort_keys=True)
        return 0
    if "--check" in argv:
        rec = build(write=False)
        print("\n".join(rec["check"]) or "no courtyard overlaps / pad shorts of the moved parts")
        print("deleted:", rec["deleted"])
        print("by part:", rec["deleted_by_ref"])
        print("orientations:", {r: d["new"][2] for r, d in rec["place"].items() if r in AUTO})
        return 0
    rec = build()
    rec["moves"] = dict(place={k: list(v) for k, v in PLACE.items()},
                        auto={k: [v[0], v[1], v[2]] for k, v in AUTO.items()},
                        groups={k: dict(refs=v[0], dx=v[1], dy=v[2]) for k, v in GROUPS.items()})
    with open(path, "w") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
    subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, sys.argv[1]); import reuse_51_board as R; "
                    "R.run_drc(name=sys.argv[2], out_json='drc_p2.json')", HERE, NAME2], check=True)
    for f in ("fp-info-cache", NAME2 + ".kicad_prl"):
        if os.path.exists(os.path.join(R.OUTDIR, f)):
            os.remove(os.path.join(R.OUTDIR, f))
    subprocess.run([sys.executable, os.path.abspath(__file__), "--dump"], check=True)
    print(f"trial_placement_p2: {os.path.relpath(OUT2, R.ROOT)}: moved {len(PLACE) + len(AUTO)} parts + "
          f"{len(GROUPS)} groups; deleted {rec['deleted']}")
    if "--no-report" not in argv:
        env = {k: v for k, v in os.environ.items() if k not in ("PYTHONHOME", "PYTHONPATH")}
        subprocess.run(["python3", os.path.join(HERE, "trial_report.py")], check=True, env=env)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
