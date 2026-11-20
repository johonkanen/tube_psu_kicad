#!/usr/bin/env python3
"""Routing stage 2 of tube_power 5.2: the inner-layer planes (run with tools/p2k/bin/kipy).

    tools/p2k/bin/kipy tools/next/route_s2_planes.py            edit kicad_next/tube_psu_5_2.kicad_pcb in place
    tools/p2k/bin/kipy tools/next/route_s2_planes.py --dry-run OUT.kicad_pcb   write the result to OUT instead

Plan and reasons: kicad_next/README.md "Inner layers (routing stage 2)". Re-runnable: everything this script
made carries the zone-name prefix "S2_" and is removed first; the one-time clean-up of the 5.1 inner copper
(steps 2-4) finds nothing to do on a second run. The board is edited in a temporary project copy, the zones
are refilled there by kicad-cli with the project rules (pcbnew's own filler does not load the .kicad_dru), and
only then the result replaces the real board. Stops if KiCad has the board open (lock file).

Steps
 1. remove every zone / rule area named S2_*
 2. remove the 5.1 ground pours on In1 / In4 (nets GROUND_NETS; replaced by the S2 planes) and their thermal
    spoke stubs (segments of those nets up to SPOKE_MAX long)
 3. move the 5.1 signal routing from In4.GND to In2.Signal_HV (only while In2 holds no track: one-time) and
    delete the inner-layer segments that are closer than the inner-layer spacing, in plan view, to copper of
    another domain on any layer (5.1 routing at the barriers)
 2b. remove the 5.1 switching-node pours on In1 / In4 (SWITCH_POUR_NETS) with their spokes
 4. the 5.1 mains pours IN2 / RES_IN on In1 / In4 stay
 4b. outer-layer fixes of the layer-to-layer check (DELETE_TRACKS: PE track under R4-R6; MOVE / ADD_TRACKS: R102)
     Everything deleted is listed in kicad_next/routing/deleted_s2.json.
 5. keep-outs S2_KO_* (rule areas, inner layers, no zone fill): PWM2 drain, TR1 pin 2, and S2_KO_xlayer_*
    that hold the kept 5.1 inner pours back from copper of other domains on other layers
 6. planes and pours S2_<layer>_<net>_<n>: outline = REGION of the net (hand-drawn, inside the domain's side of
    every barrier line)
        - the barrier bands (BARRIERS centre line +- half width)
        - all copper of every other isolation domain on ALL six layers, grown by the inner-layer spacing of
          the pair (LIMITS, = .kicad_dru) + MARGIN
    so a plane keeps the inner-layer spacing in plan view to foreign copper on its own layer (what KiCad
    checks) and on every other layer (what KiCad cannot check; tools/next/check_domains.py "layer to layer").
    The script aborts if a REGION holds copper of another domain (a plane never gets its domain by luck).
 7. refill (kicad-cli pcb drc --refill-zones --save-board, all checks off, < 3 GB), copy the board back

After routing changes near a barrier: run again - the planes follow the copper.
"""
import collections
import json
import math
import os
import re
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
RSS_CAP_KB = 2_950_000        # kicad-cli is killed above this (3 GB limit of the project)
PREFIX = "S2_"

IN1, IN2, IN3, IN4 = pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu
INNER = [IN1, IN2, IN3, IN4]
COPPER = [pcbnew.F_Cu, IN1, IN2, IN3, IN4, pcbnew.B_Cu]

# ---------------------------------------------------------------------------------------------- domains
# net class -> isolation domain (setup_project.py / check_domains.py)
CLASS_DOMAIN = {"HV_PRIMARY": "PRI", "PRIMARY_LV": "PRI", "SIGNAL": "PRI", "HV_SECONDARY": "SEC",
                "SECONDARY_LV": "SEC", "HEATER": "HEATER", "UART_ISO": "UART", "PE_EARTH": "PE"}
HOLES = re.compile(r"^H[1-8]$")      # mounting holes: earthed, domain HOLE
# plan-view spacing between a plane of one domain and copper of another on any layer = the inner-layer
# spacing of tube_psu_5_2.kicad_dru (check_domains.py LIMITS, third column); SEC-HEATER: the HV value for all
LIMITS = {("PRI", "SEC"): 11.1, ("HEATER", "PRI"): 8.0, ("PRI", "UART"): 8.0, ("SEC", "UART"): 8.4,
          ("HEATER", "SEC"): 5.2, ("HEATER", "UART"): 1.0, ("PE", "PRI"): 3.2, ("PE", "SEC"): 4.2,
          ("HOLE", "PRI"): 3.2, ("HOLE", "SEC"): 4.2}
MARGIN = 0.15                 # added to every spacing (arc approximation of the grown shapes, rounding)
MAXERR = 0.02                 # arc approximation of the grown shapes, mm

# Barrier lines: (domain A, domain B, half width of the band without planes, centre line). The lines follow
# the slots and barrier bands of the outer layers; a plane region must lie on its own side.
BARRIERS = [
    ("PRI", "SEC", 5.6, [   # TR3 barrier band centre, L-slot (x 51.4 / y -39.8), ISO2 slot, TR1 slot
        (48.5, -92.0), (48.5, -62.5), (51.4, -61.0), (51.4, -39.8), (66.75, -39.8), (66.75, -15.5),
        (63.55, -14.5), (63.55, 20.0)]),
    ("PRI", "HEATER", 4.05, [   # below the heater island, ISO1 slot stem + T bar, between the TR2 pin rows
        (-73.0, -46.0), (-42.36, -46.0), (-42.36, -63.6), (-30.05, -63.6), (-30.05, -92.0)]),
]

# ---------------------------------------------------------------------------------------------- 5.1 copper
GROUND_NETS = ("GND", "ISO_GND", "HT_GND")
SPOKE_MAX = 1.5               # mm: 5.1 thermal spokes of the removed ground pours (imported as segments)
# 5.1 pours of switching nodes on In1 / In4 (user decision 2026-11-20, 6): removed with their spokes, the
# ground planes take the area. The mains pours IN2 / RES_IN stay.
SWITCH_POUR_NETS = ("/05 PFC/PFC_DRAIN_1", "/05 PFC/PFC_DRAIN_2", "/06 Heaters/Q13_DRAIN", "/06 Heaters/Q14_DRAIN",
                    "/05 PFC/L2_PRI2", "DHB_HI_SOURCE_SEC")
DELETED_LOG = os.path.join(PROJ, "routing", "deleted_s2.json")   # every piece of copper this script deleted

# Outer-layer fixes of the layer-to-layer check (user decision 2026-11-20, 2).
# (a) 5.1 PE track on B.Cu under the mains discharge resistors R4 / R5 / R6 (F.Cu): deleted, PE is routed again
#     in stage 3. (net, layer, x0, y0, x1, y1)
DELETE_TRACKS = [
    ("/05 PFC/PE", pcbnew.B_Cu, -58.4, -3.8, -66.2, -3.8),
    ("/05 PFC/PE", pcbnew.B_Cu, -68.7, -1.3, -66.3, -3.7),
    ("/05 PFC/PE", pcbnew.B_Cu, -66.2, -3.8, -68.7, -6.3),
    ("/05 PFC/PE", pcbnew.B_Cu, -66.3, -3.7, -66.2, -3.7),
    ("/05 PFC/PE", pcbnew.B_Cu, -66.2, -3.7, -66.2, -3.8),
    # (b) old connections of R102 (moved, below)
    ("Net-(C63-Pad1)", pcbnew.B_Cu, 6.3, -65.3728, 6.3, -63.9),
    ("Net-(C63-Pad1)", pcbnew.B_Cu, 6.3272, -65.4, 6.3, -65.3728),
    ("Net-(U1B--)", pcbnew.B_Cu, 4.6, -64.0, 4.6, -65.4),
]
# (b) R102 (B.Cu, feedback resistor across C63) was 7.4 mm in plan view from U11 pin 9 (UART island, F.Cu; 8.0 mm
#     rule). 0.7 mm further down is taken by C63, so it stands upright right of C63 (clear of the U1 / C63 courtyards):
#     absolute position, pad 2 up.
MOVE = {"R102": (8.1, -64.1, "2")}            # ref: (x, y, number of the pad with the smaller y)
ADD_TRACKS = [                                 # (net, layer, width, points)
    ("Net-(U1B--)", pcbnew.B_Cu, 0.152, [(8.1, -64.925), (8.025, -65.0), (4.6, -65.0), (4.6, -64.0)]),
    ("Net-(C63-Pad1)", pcbnew.B_Cu, 0.152, [(8.1, -63.275), (7.475, -63.9), (6.275, -63.9)]),
]

# ---------------------------------------------------------------------------------------------- keep-outs
# name -> (layers, list of polygons); rule areas "no zone fill"; circles as ("circle", x, y, r)
KEEPOUTS = {
    # NEXT_REVISION_PLAN phase 5 (8): no inner-layer copper on the PWM2 drain (FLY_C, 0 <-> 620 V at 100 kHz):
    # the reserved drain copper F.Cu x 40.6...47.7 / y -2...6.6, the strip y 7.2...10.6 to D7 / TR1 pin 12 and
    # the B.Cu part x 40.6...46.3 / y 6.6...14 (trial REPORT.md step 3 note 4), + 0.6 mm
    "S2_KO_PWM2_drain": (INNER, [[(40.0, -2.6), (48.3, -2.6), (48.3, 6.4), (58.6, 6.4), (58.6, 14.6), (40.0, 14.6)]]),
    # TR1 pin 2 (GND) barrel is 11.01 mm from pin 9 (ISO_GND): nothing may connect to pin 2 on an inner layer
    # (its inner ring would then stay), check_board.py ACCEPTED / check_domains.py ALLOW
    "S2_KO_TR1_pin2": (INNER, [("circle", 57.3, -6.0, 2.2)]),
}

# ---------------------------------------------------------------------------------------------- planes
# (layer, net, domain, [rectangles x0, y0, x1, y1 or polygons], thermal spoke width)
R_GND = [(-27.0, -91.4, -4.4, -34.0),        # heater LLC primary, DRV3
         (-4.4, -65.2, 44.0, -34.0),         # U1, DRV5, DAB primary bridge (below the UART island keep-out)
         (20.3, -91.4, 44.0, -65.2),         # C47 / C54, TR3 primary side (right of the UART island keep-out)
         (-40.0, -59.0, -27.0, -35.0),       # arm to ISO1's primary side / C97 (as the 5.1 plane)
         (2.0, -34.0, 64.0, 19.0)]           # PFC switches / bulk caps, control (J2), flyback primary
R_ISO = [(54.5, -91.4, 92.0, -39.8),         # TR3 secondary, DAB secondary bridge, 420 V output
         (66.75, -39.8, 92.0, 19.0)]         # AD2 / ISO2 secondary side, flyback secondaries, outputs
R_HT = [(-72.0, -91.4, -35.0, -63.6),        # heater rectifier / output
        (-60.5, -63.6, -42.36, -50.0)]       # AD1 / ISO1 heater side
PLANES = [
    (IN1, "GND", "PRI", R_GND, 0.6),
    (IN1, "ISO_GND", "SEC", R_ISO, 0.6),
    (IN1, "HT_GND", "HEATER", R_HT, 0.8),
    (IN4, "GND", "PRI", R_GND, 0.6),
    (IN4, "ISO_GND", "SEC", R_ISO, 0.6),
    (IN4, "HT_GND", "HEATER", R_HT, 0.8),
    # In3: power pours, each from its source to the clusters of its loads
    (IN3, "15V", "PRI", [(47.0, -25.0, 60.0, -15.6),       # flyback 15 V output (D5, C39, C1)
                         [(38.0, -33.7), (44.0, -33.7), (47.5, -30.2), (51.0, -30.2), (51.0, -24.9),
                          (47.0, -24.9), (47.0, -27.6), (43.5, -27.6)],   # link, outside 11.1 mm round Q21
                         (9.0, -39.0, 51.0, -33.6),        # spine below the TO row: DRV1 (C79)
                         (21.5, -51.0, 28.0, -39.0),       # DRV5 pin 16 / C95
                         (9.5, -62.8, 13.5, -39.0),        # D19 / C96
                         (-25.0, -65.0, 13.5, -60.6)],     # DRV3 pin 11 / C18 / C52 / D11
     0.6),
    (IN3, "5V", "PRI", [(43.0, -14.6, 56.0, -2.9),         # flyback 5 V output (D6, C6 / C36 / C71)
                        (43.0, -27.0, 46.2, -14.6),
                        (33.0, -27.0, 46.2, -21.3)],       # J2 pin 2, V4 input, C75
     0.6),
    (IN3, "+3V3", "PRI", [(15.0, -20.6, 42.3, -3.2),       # control / measurement area round J2
                          (15.0, -3.2, 39.4, 15.0),        # (left of the PWM2 drain keep-out)
                          (15.0, -32.0, 32.3, -20.6)],
     0.6),
    (IN3, "15V_ISO_SEC", "SEC", [(72.4, -21.5, 90.6, -12.6),     # flyback 15 V secondary output, P15V_OUT
                                 (72.4, -49.0, 76.5, -12.6),     # lane north
                                 (55.0, -68.0, 76.5, -49.0)],    # DRV6 supply (pin 11, C72, D18)
     0.6),
    (IN3, "5V_ISOL", "SEC", [(72.4, -8.2, 90.6, 3.2)], 0.6),     # flyback 5 V secondary output, P5V_OUT
    (IN3, "6V3", "HEATER", [(-72.0, -91.4, -39.5, -63.6)], 0.8), # heater output, parallel to the B.Cu pour
]
MIN_AREA = 15.0               # mm2: smaller outline pieces are dropped
OPENING = 0.25                # mm: outline slivers narrower than 2 x this are removed
ZONE_CLEARANCE = 0.2
ZONE_MIN_WIDTH = 0.2
THERMAL_GAP = 0.3


def nm(v):
    return int(round(v * 1e6))


def mm(v):
    return round(v / 1e6, 4)


def log(msg):
    print("route_s2_planes: " + msg, flush=True)


# ---------------------------------------------------------------------------------------------- geometry
def poly_of(shape):
    """SHAPE_POLY_SET of a rectangle (x0, y0, x1, y1), a point list or ("circle", x, y, r)"""
    p = pcbnew.SHAPE_POLY_SET()
    if shape[0] == "circle":
        _, x, y, r = shape
        n = 72                                    # circumscribed polygon: never smaller than the circle
        p.NewOutline()
        for k in range(n):
            a = 2 * math.pi * k / n
            p.Append(nm(x + r / math.cos(math.pi / n) * math.cos(a)), nm(y + r / math.cos(math.pi / n) * math.sin(a)))
        return p
    if len(shape) == 4 and not isinstance(shape[0], (tuple, list)):
        x0, y0, x1, y1 = shape
        shape = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    p.NewOutline()
    for x, y in shape:
        p.Append(nm(x), nm(y))
    return p


def union(shapes):
    u = pcbnew.SHAPE_POLY_SET()
    for s in shapes:
        u.BooleanAdd(poly_of(s))
    return u


def grown(p, d):
    q = pcbnew.SHAPE_POLY_SET(p)
    q.Inflate(nm(d), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, nm(MAXERR))
    return q


def band(line, half):
    p = pcbnew.SHAPE_POLY_SET()
    for (x0, y0), (x1, y1) in zip(line, line[1:]):
        n = math.hypot(x1 - x0, y1 - y0)
        ux, uy = -(y1 - y0) / n * half, (x1 - x0) / n * half
        p.BooleanAdd(poly_of([(x0 + ux, y0 + uy), (x1 + ux, y1 + uy), (x1 - ux, y1 - uy), (x0 - ux, y0 - uy)]))
    for x, y in line:
        p.BooleanAdd(poly_of(("circle", x, y, half)))
    p.Simplify()
    return p


def area(p):
    return p.Area() / 1e12


def chain_pts(c):
    return [(c.CPoint(k).x, c.CPoint(k).y) for k in range(c.PointCount())]


# ---------------------------------------------------------------------------------------------- board data
def net_domains():
    with open(os.path.join(PROJ, NAME + ".kicad_pro")) as f:
        pro = json.load(f)
    return {p["pattern"]: CLASS_DOMAIN.get(p["netclass"], "") for p in pro["net_settings"]["netclass_patterns"]}


def domain_copper(b, dom):
    """{domain: SHAPE_POLY_SET} of all copper (pads on every layer, tracks, vias, stored zone fills) in plan
    view, every layer merged; zones named S2_* are left out (they are being rebuilt)"""
    raw = collections.defaultdict(pcbnew.SHAPE_POLY_SET)
    e = nm(MAXERR)
    ebb = b.GetBoardEdgesBoundingBox()
    for fp in b.GetFootprints():
        ref = fp.GetReference()
        if not ebb.Contains(fp.GetPosition()):
            continue
        for p in fp.Pads():
            d = "HOLE" if HOLES.match(ref) else dom.get(p.GetNetname(), "")
            if not d:
                continue
            for l in COPPER:
                if p.IsOnLayer(l):
                    p.TransformShapeToPolygon(raw[d], l, 0, e, pcbnew.ERROR_OUTSIDE)
            if p.HasHole():
                p.TransformHoleToPolygon(raw[d], 0, e, pcbnew.ERROR_OUTSIDE)
    for t in b.GetTracks():
        d = dom.get(t.GetNetname(), "")
        if d:
            layer = pcbnew.F_Cu if t.Type() == pcbnew.PCB_VIA_T else t.GetLayer()
            t.TransformShapeToPolygon(raw[d], layer, 0, e, pcbnew.ERROR_OUTSIDE)
    for z in b.Zones():
        if z.GetIsRuleArea() or z.GetZoneName().startswith(PREFIX):
            continue
        d = dom.get(z.GetNetname(), "")
        if d:
            for l in z.GetLayerSet().CuStack():
                raw[d].BooleanAdd(z.GetFilledPolysList(l))
    for p in raw.values():
        p.Simplify()
    return raw


def limit(a, b):
    return LIMITS.get((a, b), LIMITS.get((b, a)))


# ---------------------------------------------------------------------------------------------- steps
def remove_s2(b):
    n = 0
    for z in list(b.Zones()):
        if z.GetZoneName().startswith(PREFIX):
            b.Delete(z)
            n += 1
    log(f"step 1: removed {n} S2_* zones / rule areas")


def remove_51_grounds(b):
    zones = [z for z in b.Zones() if not z.GetIsRuleArea() and z.GetNetname() in GROUND_NETS
             and z.GetZoneName().startswith("Proteus ") and z.GetLayerSet().Contains(IN1) | z.GetLayerSet().Contains(IN4)]
    for z in zones:
        layer = [b.GetLayerName(l) for l in z.GetLayerSet().CuStack()][0]
        bb = z.GetBoundingBox()
        log(f"step 2: removed 5.1 zone '{z.GetZoneName()}' [{z.GetNetname()}] {layer} "
            f"x {mm(bb.GetLeft())}...{mm(bb.GetRight())} y {mm(bb.GetTop())}...{mm(bb.GetBottom())}, "
            f"filled {area(z.GetFilledPolysList(z.GetLayerSet().CuStack()[0])):.0f} mm2")
        b.Delete(z)
    spokes = collections.Counter()
    for t in list(b.GetTracks()):
        if (t.Type() != pcbnew.PCB_VIA_T and t.GetLayer() in (IN1, IN4) and t.GetNetname() in GROUND_NETS
                and t.GetLength() <= nm(SPOKE_MAX)):
            spokes[(b.GetLayerName(t.GetLayer()), t.GetNetname())] += 1
            b.Delete(t)
    if not zones and not spokes:
        log("step 2: no 5.1 ground pour / spoke left on In1 / In4")
    for (layer, net), n in sorted(spokes.items()):
        log(f"step 2: removed {n} thermal-spoke segments [{net}] {layer} (<= {SPOKE_MAX} mm)")


def foreign(raw, d, extra):
    """all copper of the other domains, each grown by its spacing to domain d + extra (plan view, all layers)"""
    f = pcbnew.SHAPE_POLY_SET()
    for o, shape in raw.items():
        if o != d and limit(d, o):
            f.BooleanAdd(grown(shape, limit(d, o) + extra))
    return f


DELETED = []


def deleted(kind, **kw):
    DELETED.append(dict(kind=kind, **kw))


def seg_rec(b, t, reason):
    return dict(net=t.GetNetname(), layer=b.GetLayerName(t.GetLayer()), start=[mm(t.GetStart().x), mm(t.GetStart().y)],
                end=[mm(t.GetEnd().x), mm(t.GetEnd().y)], width=mm(t.GetWidth()), reason=reason)


def write_deleted():
    """merge what this run deleted into kicad_next/routing/deleted_s2.json (a re-run deletes nothing and keeps it)"""
    old = []
    if os.path.exists(DELETED_LOG):
        with open(DELETED_LOG) as f:
            old = json.load(f)["deleted"]
    seen = {json.dumps(x, sort_keys=True) for x in old}
    new = [x for x in DELETED if json.dumps(x, sort_keys=True) not in seen]
    if new or not os.path.exists(DELETED_LOG):
        os.makedirs(os.path.dirname(DELETED_LOG), exist_ok=True)
        with open(DELETED_LOG, "w") as f:
            json.dump(dict(note="copper deleted by tools/next/route_s2_planes.py (routing stage 2); segments: mm, "
                                "to be routed again in stage 3 where the net still needs them", deleted=old + new),
                      f, indent=1)
            f.write("\n")
    log(f"{len(new)} deleted items added to {os.path.relpath(DELETED_LOG, ROOT)} ({len(old) + len(new)} in total)")


def remove_switch_pours(b):
    """user decision 2026-11-20 (6): no switching-node pour on the ground-plane layers"""
    n = 0
    for z in list(b.Zones()):
        if z.GetIsRuleArea() or z.GetNetname() not in SWITCH_POUR_NETS or not z.GetZoneName().startswith("Proteus "):
            continue
        ls = [l for l in z.GetLayerSet().CuStack()]
        if not ls or ls[0] not in (IN1, IN4):
            continue
        bb = z.GetBoundingBox()
        rec = dict(zone=z.GetZoneName(), net=z.GetNetname(), layer=b.GetLayerName(ls[0]),
                   bbox=[mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom())],
                   filled_mm2=round(area(z.GetFilledPolysList(ls[0])), 1),
                   reason="5.1 switching-node pour on a ground-plane layer (user decision 2026-11-20)")
        deleted("zone", **rec)
        log(f"step 2b: removed 5.1 zone '{rec['zone']}' [{rec['net']}] {rec['layer']}, filled {rec['filled_mm2']} mm2")
        b.Delete(z)
        n += 1
    spokes = collections.Counter()
    for t in list(b.GetTracks()):
        if t.Type() != pcbnew.PCB_VIA_T and t.GetLayer() in (IN1, IN4) and t.GetNetname() in SWITCH_POUR_NETS:
            deleted("segment", **seg_rec(b, t, "thermal spoke of a removed 5.1 switching-node pour"))
            spokes[(b.GetLayerName(t.GetLayer()), t.GetNetname())] += 1
            b.Delete(t)
    for (layer, net), k in sorted(spokes.items()):
        log(f"step 2b: removed {k} spoke segments [{net}] {layer}")
    if not n and not spokes:
        log("step 2b: no 5.1 switching-node pour / spoke left on In1 / In4")


def near(a, b_, tol=0.002):
    return abs(a[0] - b_[0]) <= tol and abs(a[1] - b_[1]) <= tol


def outer_fixes(b):
    """user decision 2026-11-20 (2): DELETE_TRACKS, MOVE, ADD_TRACKS - all by absolute coordinates, so a second
    run finds nothing to do"""
    n = 0
    for t in list(b.GetTracks()):
        if t.Type() == pcbnew.PCB_VIA_T:
            continue
        s_, e_ = (mm(t.GetStart().x), mm(t.GetStart().y)), (mm(t.GetEnd().x), mm(t.GetEnd().y))
        for net, layer, x0, y0, x1, y1 in DELETE_TRACKS:
            if t.GetNetname() == net and t.GetLayer() == layer and (
                    (near(s_, (x0, y0)) and near(e_, (x1, y1))) or (near(s_, (x1, y1)) and near(e_, (x0, y0)))):
                why = ("5.1 PE track on B.Cu under R4 / R5 / R6 on F.Cu (layer-to-layer PE-PRI)" if "PE" in net
                       else "old connection of R102 (moved away from U11 pin 9)")
                deleted("segment", **seg_rec(b, t, why))
                log(f"step 4b: deleted segment [{net}] {b.GetLayerName(layer)} {s_}-{e_}: {why}")
                b.Delete(t)
                n += 1
                break
    for ref, (x, y, up) in MOVE.items():
        fp = b.FindFootprintByReference(ref)
        pos = (mm(fp.GetPosition().x), mm(fp.GetPosition().y))
        pads = {p.GetNumber(): p for p in fp.Pads()}
        other = next(k for k in pads if k != up)
        if near(pos, (x, y)) and pads[up].GetPosition().y < pads[other].GetPosition().y:
            log(f"step 4b: {ref} already at ({x}, {y})")
            continue
        fp.SetPosition(pcbnew.VECTOR2I(nm(x), nm(y)))
        for deg in (90.0, 270.0):
            fp.SetOrientationDegrees(deg)
            if pads[up].GetPosition().y < pads[other].GetPosition().y:
                break
        log(f"step 4b: moved {ref} {pos} -> ({x}, {y}) / {fp.GetOrientationDegrees():g} deg, pads "
            + ", ".join(f"{k} ({mm(p.GetPosition().x)}, {mm(p.GetPosition().y)})" for k, p in sorted(pads.items())))
    have = {(t.GetNetname(), t.GetLayer(), mm(t.GetStart().x), mm(t.GetStart().y), mm(t.GetEnd().x), mm(t.GetEnd().y))
            for t in b.GetTracks() if t.Type() != pcbnew.PCB_VIA_T}
    for net, layer, w, pts in ADD_TRACKS:
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if (net, layer, x0, y0, x1, y1) in have or (net, layer, x1, y1, x0, y0) in have:
                continue
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(pcbnew.VECTOR2I(nm(x0), nm(y0)))
            t.SetEnd(pcbnew.VECTOR2I(nm(x1), nm(y1)))
            t.SetWidth(nm(w))
            t.SetLayer(layer)
            t.SetNetCode(b.GetNetcodeFromNetname(net))
            b.Add(t)
            n += 1
            log(f"step 4b: added segment [{net}] {b.GetLayerName(layer)} ({x0}, {y0})-({x1}, {y1})")
    if not n:
        log("step 4b: outer-layer fixes already in place")


def move_signals(b, dom):
    """5.1 routing on In4.GND (the 5.1 layer In2) -> In2.Signal_HV; segments of nets that keep a 5.1 pour on
    In4 (its thermal spokes) stay. Then, once: inner-layer segments closer in plan view than the inner-layer
    spacing to copper of another domain on any layer are deleted (5.1 routing at the barriers; to be routed
    again on the outer layers, where the slots count)"""
    if any(t.Type() != pcbnew.PCB_VIA_T and t.GetLayer() == IN2 for t in b.GetTracks()):
        left = sum(1 for t in b.GetTracks() if t.Type() != pcbnew.PCB_VIA_T and t.GetLayer() == IN4)
        log(f"step 3: In2.Signal_HV already holds tracks - nothing moved ({left} segments on In4.GND)")
        return
    keep = {z.GetNetname() for z in b.Zones() if not z.GetIsRuleArea() and z.GetLayerSet().Contains(IN4)}
    moved = collections.Counter()
    length = 0
    for t in b.GetTracks():
        if t.Type() != pcbnew.PCB_VIA_T and t.GetLayer() == IN4 and t.GetNetname() not in keep:
            t.SetLayer(IN2)
            moved[t.GetNetname()] += 1
            length += t.GetLength()
    stay = collections.Counter(t.GetNetname() for t in b.GetTracks()
                               if t.Type() != pcbnew.PCB_VIA_T and t.GetLayer() == IN4)
    log(f"step 3: moved {sum(moved.values())} segments ({mm(length):.0f} mm, {len(moved)} nets) In4.GND -> "
        f"In2.Signal_HV; staying on In4.GND (spokes of kept 5.1 pours): {dict(stay)}")
    raw = domain_copper(b, dom)
    near = {d: foreign(raw, d, 0.03) for d in ("PRI", "SEC", "HEATER", "UART")}
    gone = collections.Counter()
    for t in list(b.GetTracks()):
        d = dom.get(t.GetNetname(), "")
        if t.Type() == pcbnew.PCB_VIA_T or t.GetLayer() not in INNER or d not in near:
            continue
        tp = pcbnew.SHAPE_POLY_SET()
        t.TransformShapeToPolygon(tp, t.GetLayer(), 0, nm(MAXERR), pcbnew.ERROR_INSIDE)
        tp.BooleanIntersection(near[d])
        if area(tp) > 0:
            log(f"step 3: deleted segment [{t.GetNetname()}] {b.GetLayerName(t.GetLayer())} "
                f"({mm(t.GetStart().x)}, {mm(t.GetStart().y)})-({mm(t.GetEnd().x)}, {mm(t.GetEnd().y)}): inside the "
                f"layer-to-layer spacing of another domain")
            gone[t.GetNetname()] += 1
            deleted("segment", **seg_rec(b, t, "inner-layer segment inside the layer-to-layer spacing of another domain"))
            b.Delete(t)
    log(f"step 3: {sum(gone.values())} inner-layer segments deleted at the barriers, nets to route again: {dict(gone)}")


def kept_51(b):
    for z in b.Zones():
        if z.GetIsRuleArea() or z.GetZoneName().startswith(PREFIX):
            continue
        for l in z.GetLayerSet().CuStack():
            if l in INNER:
                log(f"step 4: kept 5.1 zone '{z.GetZoneName()}' [{z.GetNetname()}] {b.GetLayerName(l)} "
                    f"priority {z.GetAssignedPriority()}")


def rule_area(b, name, layers, p, i=0):
    """rule area 'no zone fill' on layers from outline i (with its holes) of the SHAPE_POLY_SET p"""
    z = pcbnew.ZONE(b)
    z.SetIsRuleArea(True)
    z.SetZoneName(name)
    z.SetDoNotAllowZoneFills(True)
    z.SetDoNotAllowTracks(False)
    z.SetDoNotAllowVias(False)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    ls = pcbnew.LSET()
    for l in layers:
        ls.AddLayer(l)
    z.SetLayerSet(ls)
    o = z.Outline()
    o.NewOutline()
    for x, y in chain_pts(p.Outline(i)):
        o.Append(x, y)
    for h in range(p.HoleCount(i)):
        o.NewHole()
        for x, y in chain_pts(p.Hole(i, h)):
            o.Append(x, y, -1, h)
    b.Add(z)


def add_keepouts(b, dom, raw):
    for name, (layers, shapes) in KEEPOUTS.items():
        for i, s in enumerate(shapes):
            rule_area(b, name if len(shapes) == 1 else f"{name}_{i + 1}", layers, poly_of(s))
        log(f"step 5: keep-out {name} on {', '.join(b.GetLayerName(l) for l in layers)}")
    # the kept 5.1 inner pours get the layer-to-layer spacing too: no fill of such a pour where copper of
    # another domain on any layer is closer in plan view than the inner-layer spacing (+ MARGIN)
    near = {}
    for z in list(b.Zones()):
        d = dom.get(z.GetNetname(), "")
        if z.GetIsRuleArea() or z.GetZoneName().startswith(PREFIX) or not d:
            continue
        for l in z.GetLayerSet().CuStack():
            if l not in INNER:
                continue
            if d not in near:
                near[d] = foreign(raw, d, MARGIN)
            ko = pcbnew.SHAPE_POLY_SET(z.Outline())
            ko.BooleanIntersection(near[d])
            ko.Simplify()
            n = 0
            for i in range(ko.OutlineCount()):
                piece = pcbnew.SHAPE_POLY_SET()
                piece.AddOutline(ko.Outline(i))
                if area(piece) < 0.02:
                    continue
                n += 1
                short = z.GetNetname().split("/")[-1].replace(" ", "_")
                rule_area(b, f"{PREFIX}KO_xlayer_{b.GetLayerName(l).split('.')[0]}_{short}_{n}", [l], ko, i)
            if n:
                log(f"step 5: keep-out {PREFIX}KO_xlayer_* ({n}) on {b.GetLayerName(l)}: 5.1 pour "
                    f"'{z.GetZoneName()}' [{z.GetNetname()}] held {area(ko):.1f} mm2 back from copper of other "
                    f"domains on other layers")


def add_planes(b, dom, raw):
    edge = pcbnew.SHAPE_POLY_SET()
    if not b.GetBoardPolygonOutlines(edge, True):
        sys.exit("route_s2_planes: the board outline is not a closed polygon")
    bands = {(a, c): band(line, half) for a, c, half, line in BARRIERS}
    forbidden = {}
    for d in ("PRI", "SEC", "HEATER", "UART"):
        f = foreign(raw, d, MARGIN)
        for (a, c), p in bands.items():
            if d in (a, c):
                f.BooleanAdd(p)
        forbidden[d] = f
    summary = []
    for layer, net, d, region, spoke in PLANES:
        lname = b.GetLayerName(layer)
        if dom.get(net) != d:
            sys.exit(f"route_s2_planes: net {net} is not in domain {d}")
        reg = union(region)
        # the region must be on its own side: no copper of any other domain inside it
        for o, shape in raw.items():
            if o in (d, "HOLE", "PE") or not limit(d, o):
                continue
            x = pcbnew.SHAPE_POLY_SET(reg)
            x.BooleanIntersection(shape)
            if area(x) > 0.01:
                bb = x.BBox()
                sys.exit(f"route_s2_planes: region of {net} on {lname} holds {area(x):.2f} mm2 of {o} copper "
                         f"(x {mm(bb.GetLeft())}...{mm(bb.GetRight())}, y {mm(bb.GetTop())}...{mm(bb.GetBottom())})")
        out = pcbnew.SHAPE_POLY_SET(reg)
        out.BooleanIntersection(edge)
        out.BooleanSubtract(forbidden[d])
        out.Deflate(nm(OPENING), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, nm(MAXERR))
        out.Inflate(nm(OPENING), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, nm(MAXERR))
        out.BooleanIntersection(reg)
        out.BooleanSubtract(forbidden[d])
        out.Simplify()
        n = 0
        total = 0.0
        for i in range(out.OutlineCount()):
            piece = pcbnew.SHAPE_POLY_SET()
            piece.AddOutline(out.Outline(i))
            a = area(piece)
            for h in range(out.HoleCount(i)):
                hp = pcbnew.SHAPE_POLY_SET()
                hp.AddOutline(out.Hole(i, h))
                a -= area(hp)
            if a < MIN_AREA:
                continue
            n += 1
            total += a
            z = pcbnew.ZONE(b)
            z.SetLayer(layer)
            z.SetNetCode(b.GetNetcodeFromNetname(net))
            z.SetZoneName(f"{PREFIX}{lname.split('.')[0]}_{net}_{n}")
            z.SetAssignedPriority(0)              # below every kept 5.1 pour (26 ... 84)
            z.SetLocalClearance(nm(ZONE_CLEARANCE))
            z.SetMinThickness(nm(ZONE_MIN_WIDTH))
            z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)   # THT pins: thermal relief; vias: solid
            z.SetThermalReliefGap(nm(THERMAL_GAP))
            z.SetThermalReliefSpokeWidth(nm(spoke))
            z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
            z.SetFillMode(pcbnew.ZONE_FILL_MODE_POLYGONS)
            o = z.Outline()
            o.NewOutline()
            for x, y in chain_pts(out.Outline(i)):
                o.Append(x, y)
            for h in range(out.HoleCount(i)):
                o.NewHole()
                for x, y in chain_pts(out.Hole(i, h)):
                    o.Append(x, y, -1, h)
            b.Add(z)
        summary.append((lname, net, d, n, total))
        log(f"step 6: {lname:14s} {net:12s} ({d}): {n} outline piece(s), {total:.0f} mm2")
    return summary


def cli(args):
    """kicad-cli with its resident memory watched; returns (returncode, peak RSS kB)"""
    pr = subprocess.Popen([CLI] + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    peak = 0
    while pr.poll() is None:
        try:
            pids = [pr.pid] + [int(x) for x in subprocess.run(["pgrep", "-P", str(pr.pid)], capture_output=True,
                                                               text=True).stdout.split()]
            for pid in pids:
                with open(f"/proc/{pid}/status") as f:
                    peak = max(peak, next((int(l.split()[1]) for l in f if l.startswith("VmRSS:")), 0))
        except (OSError, ValueError):
            pass
        if peak > RSS_CAP_KB:
            pr.kill()
            sys.exit(f"route_s2_planes: kicad-cli above {RSS_CAP_KB} kB, killed")
        try:
            pr.wait(timeout=0.2)
        except subprocess.TimeoutExpired:
            pass
    return pr.returncode, peak


def edit(path):
    """steps 1-6 on the board copy (run in a fresh interpreter, see main)"""
    b = pcbnew.LoadBoard(path)
    dom = net_domains()
    remove_s2(b)
    remove_51_grounds(b)
    remove_switch_pours(b)
    move_signals(b, dom)
    kept_51(b)
    outer_fixes(b)
    raw = domain_copper(b, dom)
    add_keepouts(b, dom, raw)
    add_planes(b, dom, raw)
    pcbnew.SaveBoard(path, b)
    with open(os.path.join(os.path.dirname(path), "deleted.json"), "w") as f:
        json.dump(DELETED, f)


def report(path):
    b = pcbnew.LoadBoard(path)
    for z in b.Zones():
        if z.GetZoneName().startswith(PREFIX) and not z.GetIsRuleArea():
            l = z.GetLayerSet().CuStack()[0]
            f = z.GetFilledPolysList(l)
            log(f"filled {z.GetZoneName():28s} {area(f):8.0f} mm2 in {f.OutlineCount()} island(s)")


def main(argv):
    if os.path.exists(LOCK):
        sys.exit(f"route_s2_planes: {os.path.relpath(LOCK, ROOT)} exists - the board is open in KiCad; close it first")
    tmp = tempfile.mkdtemp(prefix=".s2_", dir=ROOT)
    try:
        for ext in (".kicad_pcb", ".kicad_dru"):
            shutil.copy(os.path.join(PROJ, NAME + ext), tmp)
        with open(os.path.join(PROJ, NAME + ".kicad_pro")) as f:
            pro = json.load(f)
        rs = pro["board"]["design_settings"]["rule_severities"]
        for k in rs:
            rs[k] = "ignore"                       # refill only: no check needs memory
        with open(os.path.join(tmp, NAME + ".kicad_pro"), "w") as f:
            json.dump(pro, f, indent=2)
        pcb = os.path.join(tmp, NAME + ".kicad_pcb")
        # each pcbnew pass in its own interpreter (a second LoadBoard in one process is not reliable)
        r = subprocess.run([sys.executable, "-u", os.path.abspath(__file__), "--edit", pcb])
        if r.returncode:
            sys.exit("route_s2_planes: edit failed, the board is unchanged")
        rc, peak = cli(["pcb", "drc", "--format", "json", "--refill-zones", "--save-board",
                        "-o", os.path.join(tmp, "refill.json"), pcb])
        if rc != 0:
            sys.exit("route_s2_planes: zone refill failed, the board is unchanged")
        log(f"step 7: zones refilled by kicad-cli (peak RSS {peak // 1024} MB)")
        subprocess.run([sys.executable, "-u", os.path.abspath(__file__), "--report", pcb], check=True)
        if "--dry-run" in argv:
            keep = os.path.abspath(argv[argv.index("--dry-run") + 1])
            shutil.copy(pcb, keep)
            log(f"dry run: result in {keep}, the board is unchanged")
            return 0
        if os.path.exists(LOCK):
            sys.exit("route_s2_planes: the board was opened in KiCad meanwhile - not written")
        shutil.copy(pcb, BOARD)
        log(f"wrote {os.path.relpath(BOARD, ROOT)}")
        with open(os.path.join(tmp, "deleted.json")) as f:
            DELETED.extend(json.load(f))
        write_deleted()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    if "--edit" in sys.argv:
        edit(sys.argv[sys.argv.index("--edit") + 1])
        sys.exit(0)
    if "--report" in sys.argv:
        report(sys.argv[sys.argv.index("--report") + 1])
        sys.exit(0)
    sys.exit(main(sys.argv[1:]))
