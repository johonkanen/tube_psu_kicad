#!/usr/bin/env python3
"""Routing stage 3a of tube_power 5.2: power, high-voltage and ground connections (system python3).

    python3 tools/next/route_s3a_power.py [--dry-run OUT.kicad_pcb]
    tools/p2k/bin/kipy tools/next/route_s2_planes.py        afterwards: the planes follow the new copper

Engine and step format: tools/next/s3_router.py. Plan, widths and open points: kicad_next/README.md "Power, HV and
ground routing (stage 3a)". Re-runnable: the copper of the last run (kicad_next/routing/s3a_added.json) and the
zones / rule areas named S3A_* are removed first, then everything is built again from the tables below.
The signals (gate drives, SPI, Kelvin sense, analog, UART) are stage 3b.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s3_router as R  # noqa: E402

F, B = "F", "B"
FLY = "/01 AUX supply/FLY_C"
PE = "/05 PFC/PE"
CAP = "/07 DHB/DHB_CAP"
TSEC = "/07 DHB/TRANS_SEC"
SWS = "DHB_HI_SOURCE_SEC"
HHS = "/06 Heaters/HEATER_HI_SOURCE"
VP = (0.8, 0.4)        # via of the power / ground nets
VS = (0.6, 0.3)        # via of the low-current nets


def a(net, start, target, layers="FB", w=0.4, **o):
    return ("auto", net, start, target, dict(layers=layers, w=w, **o))


def gnd(pad, net="GND", plane="In1.GND", layers=None, w=0.4, **o):
    """SMD ground / supply pad -> short track -> via in the plane / pour of the net"""
    o.setdefault("via", VP)
    o.setdefault("margin", 3.5)
    return ("auto", net, pad, "via:" + plane, dict(layers=layers or "FB", w=w, via_cost=1e9, **o))


# ------------------------------------------------------------------------------------------------ flyback
# PWM2 (ICE5AR0680AG): drain copper = one F.Cu area round pins 5-8 with the strip to D7 / TR1 pin 12, the same
# on B.Cu, stitched; no inner copper (S2_KO_PWM2_drain). VCC (Net-(D10-K)) and the start-up / gate net cross
# the B.Cu area in one corridor (y 6.0 / 7.0), their vias sit under the package between the pin rows.
D10K, GATE = "Net-(D10-K)", "Net-(PWM2-GATE)"
OLD = "5.1 VCC track across the PWM2 drain area (dangling at both ends), VCC is routed on B.Cu"
FLYBACK = [
    ("delete", D10K, F, 46.88, 8.48, 46.0, 7.6, OLD), ("delete", D10K, F, 41.2, 7.6, 42.1, 7.6, OLD),
    ("delete", D10K, F, 46.0, 7.6, 44.2, 7.6, OLD), ("delete", D10K, F, 42.1, 7.6, 44.2, 7.6, OLD),
    # VCC: D10 cathode -> C58 -> C51 -> PWM2 pin 11
    ("via", D10K, 39.2, 4.6, *VS),
    ("track", D10K, F, 0.381, [(39.2, 4.561), (39.2, 4.6)]),
    ("track", D10K, B, 0.4, [(39.2, 4.6), (39.2, 6.5), (39.7, 7.0), (48.2, 7.0), (49.0, 7.6)]),
    ("track", D10K, B, 0.5, [(49.8, 8.5), (53.2, 8.5)]),
    ("track", D10K, B, 0.3, [(53.0, 8.2), (52.3, 7.5), (52.3, 3.6), (52.97, 2.9)]),
    ("via", D10K, 52.97, 2.9, *VS),
    ("track", D10K, F, 0.4, [(52.97, 2.9), (52.97, 4.2)]),
    # start-up chain R116 - R115 - R114 -> PWM2 pin 10 (GATE)
    ("track", GATE, F, 0.3, [(39.2, 5.94), (40.75, 6.0)]),
    ("via", GATE, 40.75, 6.0, *VS),
    ("track", GATE, B, 0.25, [(40.75, 6.0), (50.6, 6.0), (51.4, 5.2), (51.4, 3.2), (51.71, 2.9)]),
    ("via", GATE, 51.71, 2.9, *VS),
    ("track", GATE, F, 0.3, [(51.71, 2.9), (51.71, 4.2)]),
    # GND of pin 12 / C51
    ("via", "GND", 54.25, 2.9, *VS),
    ("track", "GND", F, 0.4, [(54.25, 2.9), (54.25, 4.2)]),
    ("track", "GND", B, 0.4, [(54.25, 2.9), (54.25, 5.0)]),
    # drain copper
    ("zone", "PWM2_drain_F", FLY, F, [(41.3, -1.4), (48.9, -1.4), (48.9, 6.9), (57.7, 6.9), (57.7, 13.4),
                                      (51.9, 13.4), (51.9, 10.4), (41.3, 10.4)], dict(clearance=0.5, spoke=1.0)),
    ("zone", "PWM2_drain_B", FLY, B, [(40.2, -0.9), (47.4, -0.9), (47.4, 9.0), (46.0, 9.0), (46.0, 13.7),
                                      (40.2, 13.7)], dict(clearance=0.5)),
] + [("via", FLY, x, y, *VP) for x in (42.6, 44.0) for y in (0.9, 2.4, 3.9)] + [
    ("via", FLY, 46.0, 2.2, *VP),
] + [("via", FLY, x, 9.5, *VP) for x in (42.2, 43.6, 45.0)] + [
    # clamp D7 - R72
    ("track", "Net-(D7-K)", F, 0.6, [(49.35, 12.6), (49.76, 15.3)]),
    # DC+ feed along the bottom edge: bulk capacitor track -> R116 / R151 -> clamp C12 / R45 -> TR1 fly lead 11
    ("track", "DC+", F, 0.762, [(27.27, 16.944), (27.83, 17.5), (37.3, 17.5), (38.7, 16.1), (39.2, 15.86), (41.95, 15.86)]),
    ("via", "DC+", 37.3, 17.5, 1.0, 0.5),
    ("track", "DC+", B, 0.6, [(37.3, 17.5), (38.9, 15.9)]),
    ("track", "DC+", F, 0.5, [(41.95, 16.944), (42.95, 17.95), (55.2, 17.95), (57.7, 16.572)]),
    ("track", "DC+", F, 1.0, [(60.7, 13.572), (61.32, 12.6), (61.32, 11.22)]),
    ("delete", "DC+", B, 56.4, -0.468, 56.032, -0.1, "5.1 DC+ stub at the old TR1 position"),
    a("DC+", "C15.2", "TR1.11", B, 0.6, foreign_gap=4.0),
    # current sense, windings on the primary side
    a("Net-(PWM2-CS)", "PWM2.4", "R9.1", F, 0.4, relax=("PWM2",)),
    a("Net-(PWM2-CS)", "R9.1", "R8.1", F, 0.4),
    a("Net-(TR1-A15)", "TR1.1", "D5.A", F, 0.6, margin=5, foreign_gap=4.0),
    a("Net-(TR1-A5)", "TR1.3", "D6.A", B, 0.8, foreign_gap=4.0),
    gnd("R9.2", layers=F), gnd("R8.2", layers=F), gnd("C138.2", layers=F), gnd("C140.2", layers=F),
    gnd("R154.2", layers=F), gnd("R141.2", layers=B), gnd("R139.2", layers=B), gnd("C139.2", layers=B),
    gnd("C58.2", layers=B), gnd("C15.1", layers=B, w=0.6),
    gnd("TR1.2", layers=B, w=0.6, margin=6, foreign_gap=4.0),
]

# ------------------------------------------------------------------------------------------------ DAB primary
OLD_TR3 = "5.1 pour of the old TR3 / L3 / split-capacitor position (connected to nothing, or in the way of DC+)"
DAB_PRI = [
    ("delzone", "Proteus F.Cu pour 22", OLD_TR3), ("delzone", "Proteus F.Cu pour 28", OLD_TR3),
    # switch node: Q7 pin 2 / Q19 pin 3 -> TR3 pins 7, 8 (strip above the TO row, below the TR3 barrier band)
    ("zone", "DHB_HI_SOURCE_F", "DHB_HI_SOURCE", F, [(28.3, -58.0), (39.4, -58.0), (39.4, -45.3), (44.05, -45.3),
                                                     (44.05, -40.95), (33.2, -40.95), (33.2, -50.6), (28.3, -50.6)],
     dict(clearance=0.5, spoke=1.2)),
    # DC+ from the high-side drain Q19 pin 2 to the split capacitor C47: north of the switch-node strip, west of
    # the TR3 barrier band (x 42.5), under TR3, along the top edge
    ("track", "DC+", F, 0.75, [(45.62, -41.95), (45.62, -44.6)]),
    ("track", "DC+", F, 0.8, [(45.62, -44.6), (45.62, -47.3), (41.5, -47.3)]),
    ("track", "DC+", F, 1.5, [(41.5, -47.3), (41.5, -88.6), (40.1, -90.0), (24.0, -90.0)]),
    # split-capacitor midpoint C47.2 / C54.1 / TR3 pins 1, 2
    ("zone", "DHB_CAP_F", CAP, F, [(20.35, -84.9), (27.5, -84.9), (27.5, -88.0), (30.7, -88.0), (30.7, -80.1),
                                   (20.35, -80.1)], dict(clearance=0.5, spoke=1.2)),
    # low side: Q7 source / C67 (5.1 pour 23) -> C54.2, in the area of the removed pour 22
    ("zone", "DHB_CURRENT_F", "DHB_CURRENT", F, [(20.35, -76.9), (25.75, -76.9), (25.75, -49.3), (28.2, -49.3),
                                                 (28.2, -47.6), (20.35, -47.6)], dict(clearance=0.5)),
    # balancing resistors under the capacitors (B.Cu): one via per capacitor terminal
    a("DC+", "R143.1", "C47.1", "FB", 0.4, via=VP), a(CAP, "R144.2", "C47.2", "FB", 0.4, via=VP),
    a(CAP, "R145.1", "C54.1", "FB", 0.4, via=VP), a("DHB_CURRENT", "R146.2", "C54.2", "FB", 0.4, via=VP),
]

# ------------------------------------------------------------------------------------------------ DAB secondary
DAB_SEC = [
    ("delzone", "Proteus F.Cu pour 26", OLD_TR3),
    # switch node: Q21 pin 3 -> TR3 pins 15, 16, right of the TR3 barrier band (x 54.5)
    ("track", SWS, F, 1.6, [(54.675, -46.215), (54.675, -46.5), (55.45, -47.275), (55.45, -64.0), (66.5, -75.05),
                            (69.5, -78.05), (69.5, -86.8)]),
    # split-capacitor midpoint TR3 pins 9, 10 / C16.2 / C55.1
    ("zone", "TRANS_SEC_F", TSEC, F, [(68.3, -58.0), (72.0, -58.0), (73.4, -56.95), (78.8, -56.95), (78.8, -52.25),
                                      (73.4, -52.25), (72.0, -50.6), (68.3, -50.6)], dict(clearance=0.5, spoke=1.2)),
    a("420V", "C16.1", "net", F, 1.2, margin=6),
    a("420V", "R147.1", "C16.1", "FB", 0.4, via=VP), a(TSEC, "R148.2", "C16.2", "FB", 0.4, via=VP),
    a(TSEC, "R149.1", "C55.1", "FB", 0.4, via=VP), a("ISO_GND", "R150.2", "C55.2", "FB", 0.4, via=VP),
]


def inner_end(net, pad, x, y, layers, w=0.3, **o):
    """the end of a kept 5.1 track on In2 at (x, y) -> In2 to the nearest via site -> outer layer -> pad"""
    o.setdefault("via", VS)
    o.setdefault("via_cost", 3.0)
    return [a(net, (x, y, "In2.Signal_HV"), pad, "2" + layers, w, **o)]


def pl(pad, net, plane="In3.Power", layers=B, **o):
    return gnd(pad, net, plane, layers, **o)


FG = dict(foreign_gap=4.0)         # connection at a barrier part: slot credit, judged by check_domains.py

# ------------------------------------------------------------------------------------------------ heater LLC
HC = "HEATER_CURRENT"
HEATER_LLC = [
    a(HHS, "Q11.3", "net", F, 1.0, margin=8),            # high-side source -> switch-node pour
    # high-side drain tab -> DC+ pour (the 5.1 pours have no pad connection, their spokes were segments)
    ("zone", "Q11_tab_DC", "DC+", F, [(-10.5, -67.5), (-8.0, -67.5), (-8.0, -62.2), (-10.5, -62.2)], dict(solid=True)),
    a(HC, "Q10.3", "R30.1", "FB", 0.8, via=VP, margin=4),  # low-side source -> shunt R30 (B.Cu)
    a(HC, "R158.2", "R30.1", "FB", 0.25, via=VS, margin=5),
    a(HC, (-13.3, -81.0, "B.Cu"), "net", "FB", 0.5, via=VP, margin=3),   # B.Cu pour 20 <-> F.Cu pour 24
]

# ------------------------------------------------------------------------------------------------ flyback secondary
FLY_SEC = [
    # 15 V secondary winding -> D4: right of the gap between the TR1 and ISO2 slots (>= 11.1 mm from D5 / ISO2)
    ("track", "Net-(TR1-S15)", F, 0.5, [(69.766, -11.025), (70.4, -11.6), (71.9, -11.6), (71.9, -17.2), (73.6, -18.9),
                                        (74.75, -19.2)], FG),
    a("Net-(TR1-S5)", "TR1.7", "D29.A", B, 0.8, **FG),
    gnd("TR1.9", "ISO_GND", layers=B, w=0.6, margin=8, **FG),
    a("-100V BIAS", "C102.2", "R68.2", B, 0.4),
    a("ISO_GND", "R68.1", "net", B, 0.4, margin=5),
    gnd("C45.1", "ISO_GND", layers=F),
]

# ------------------------------------------------------------------------------------------------ supply rails
RAILS = [
    # 15V (In3 pour: flyback output, spine below the TO row, DRV1 / DRV5 / DRV3)
    a("15V", "C14.1", "net", F, 0.4), pl("R125.1", "15V"),
    a("15V", "C18.1", "DRV3.11", B, 0.4), pl("C18.1", "15V"),
    a("15V", "C95.2", "DRV5.16", B, 0.4), pl("C95.2", "15V"),
    pl("DRV1.1", "15V"),
    a("15V", "DRV2.1", "net", B, 0.4),
    pl((-7.24, -62.24, "B.Cu"), "15V"), pl((-9.36, -61.72, "B.Cu"), "15V"),
    pl((14.67, -36.28, "B.Cu"), "15V"), pl((15.23, -38.87, "B.Cu"), "15V"), pl((15.24, -35.02, "F.Cu"), "15V", layers=F),
    a("15V", (-7.41, -67.7, "B.Cu"), "net", "FB", 0.4, via=VS, margin=6),
    a("15V", (2.6, -49.3, "B.Cu"), "net", "FB", 0.4, via=VS, margin=8),
    a("15V", (12.96, 14.14, "B.Cu"), "net", "FB", 0.4), a("15V", (13.85, 10.5, "B.Cu"), (13.16, 13.0, "F.Cu"), "FB", 0.4, via=VS),
    ("delete", "15V", F, 37.315, -1.4499, 37.315, 2.546, "5.1 15V stub that ended on the D10 anode pad (moved)"),
    a("15V", (37.315, -1.4499, "F.Cu"), "net", "FB", 0.4, via=VS, margin=8),
    # 5V (In3 pour at the flyback output and J2)
    pl("R126.1", "5V", layers=F), pl("D6.C", "5V"), pl("C6.2", "5V"), a("5V", "R138.1", "D6.C", B, 0.3),
    a("5V", "R133.1", "net", "FB", 0.3, via=VS),
    a("5V", "C94.1", "DRV5.3", B, 0.4), a("5V", "DRV5.3", "DRV5.8", B, 0.3, relax=("DRV5",)),
    *inner_end("5V", "DRV5.3", 14.86, -47.45, B, 0.3),
    a("5V", "DRV3.3", "C53.1", B, 0.4), *inner_end("5V", "C53.1", -23.9, -48.09, B, 0.3),
    a("5V", "DRV3.8", "C53.1", B, 0.3, relax=("DRV3",)),
    # +3V3 (In3 pour round J2)
    a("+3V3", "C129.1", "U9.5", B, 0.3), pl("U9.5", "+3V3", w=0.3, via=VS),
    a("+3V3", "C133.1", "U10.8", B, 0.2, relax=("U10",)), pl("C133.1", "+3V3", w=0.25, via=VS, margin=5, plane_inset=0.1),
    a("+3V3", "C124.1", "net", B, 0.3, margin=3),
    a("+3V3", "ISO1.1", "net", F, 0.3, relax=("ISO1",)),
    a("+3V3", "ISO2.1", "net", F, 0.3, relax=("ISO2",), **FG),
    a("+3V3", "U11.3", "C134.1", F, 0.3, relax=("U11",)),
    *inner_end("+3V3", "C98.1", 38.03, -26.87, F, 0.3, margin=5, **FG),
    # secondary: 15V_ISO_SEC / 5V_ISOL (In3 pours), AD2 supply
    pl("DRV6.11", "15V_ISO_SEC"), a("15V_ISO_SEC", "C43.2", "net", "FB", 0.4, margin=10),
    a("5V_ISOL", "C93.1", "DRV6.8", B, 0.4),     *inner_end("5V_ISOL", "C93.1", 74.81, -47.96, B, 0.3),
    a("5V_ISOL", (73.2, -37.3, "B.Cu"), "net", "FB", 0.4),
    *inner_end("5V_ISOL", (75.12, -40.72, "F.Cu"), 75.96, -39.58, F),
    a("AD2_3V3", "ISO2.16", "net", F, 0.3, relax=("ISO2",), **FG),
    # heater: 6V3 to DRV4 (In3 pour over the island), AD1 supply
    a("6V3", "C17.1", "DRV4.8", F, 0.5), a("6V3", "DRV4.6", "DRV4.8", F, 0.3, relax=("DRV4",)),
    pl("DRV4.8", "6V3", layers=F), pl("DRV4.1", "6V3", layers=F),
    a("6V3", (-55.95, -61.68, "F.Cu"), "net", "FB", 0.5, via=VP, margin=5),
    a("Net-(AD1-VA)", "ISO1.16", "net", F, 0.3, relax=("ISO1",)), a("Net-(AD1-VA)", "C59.1", "net", "FB", 0.3, via=VS),
    # UART island
    a("UART_3V3", "U11.14", "C135.1", F, 0.3, relax=("U11",)), a("UART_3V3", "C135.1", "J4.2", F, 0.3),
    a("ISO_UART_GND", "U11.16", "C135.2", F, 0.3, relax=("U11",)), a("ISO_UART_GND", "C135.2", "J4.1", F, 0.3, margin=5),
    a("ISO_UART_GND", "U11.9", "C135.2", "FB", 0.3, via=VS, relax=("U11",)),
]

# ------------------------------------------------------------------------------------------------ grounds
GROUNDS = [
    # GND -> In1 / In4 plane
    gnd("R78.1", layers=B), gnd("R94.2", layers=B), gnd("DRV3.5", layers=B, relax=("DRV3",)),
    gnd("DRV3.9", layers=B, relax=("DRV3",)), gnd("C18.2", layers=B),
    gnd("DRV5.14", layers=B, relax=("DRV5",)), gnd("C95.1", layers=B),
    gnd("C124.2", layers=B), gnd("C87.2", layers=F),
    gnd("C134.2", layers=F, relax=("U11",)), a("GND", "U11.1", "C134.2", F, 0.3, relax=("U11",)),
    gnd("U11.7", layers=F, relax=("U11",), margin=5),
    a("GND", "C97.2", "ISO1.2", F, 0.3, relax=("ISO1",)), gnd("C97.2", layers=F),
    gnd("ISO1.8", layers=F, relax=("ISO1",), margin=10, **FG),
    a("GND", "ISO2.8", "net", F, 0.4, relax=("ISO2",), margin=7, **FG),
    gnd("C98.2", layers=F, margin=7, **FG), gnd("R125.2", layers=B),
    gnd((56.5, -17.0, "F.Cu"), layers=F), gnd((20.9, -12.36, "B.Cu"), layers=B),
    gnd((-10.85, -70.17, "B.Cu"), layers=B),
    # relay driver under RL1 (no plane over the mains input): tracks
    a("GND", "Q9.3", "C35.2", B, 0.4), a("GND", "C35.2", "R32.2", B, 0.4),
    # ISO_GND -> plane
    gnd("C89.2", "ISO_GND", layers=F, w=0.6),
    gnd("C93.2", "ISO_GND", layers=B), gnd("R128.2", "ISO_GND", layers=B), gnd("C119.2", "ISO_GND", layers=B),
    gnd("DRV6.9", "ISO_GND", layers=B, relax=("DRV6",), **FG), gnd("DRV6.4", "ISO_GND", layers=B, relax=("DRV6",)),
    gnd("ISO2.9", "ISO_GND", layers=F, relax=("ISO2",), margin=7, **FG),
    gnd("C55.2", "ISO_GND", layers=F, w=1.0),
    # HT_GND
    gnd("ISO1.9", "HT_GND", layers=F, relax=("ISO1",), margin=6),
]

# ------------------------------------------------------------------------------------------------ mains / PE
RLC = "Net-(RL1-COM)"
MAINS = [
    a(RLC, "C85.1", "net", F, 1.0, margin=5), a(RLC, (-58.68, -43.88, "F.Cu"), "net", F, 1.0, margin=6),
    # PE: Y capacitors C84 / C65 / C81 / C82 / C85 (the link to the PE terminal: open, see README)
    ("track", PE, B, 1.0, [(-68.7, -6.3), (-68.7, -1.3)]),
    a(PE, "C65.2", "C84.2", B, 1.0, margin=5), a(PE, "C85.2", "C81.2", B, 1.0, margin=5),
    a(PE, (-53.4, -14.1, "B.Cu"), (-43.8, -14.1, "B.Cu"), B, 1.0, margin=5),
    a(PE, (-56.0, -11.5, "B.Cu"), (-56.0, -6.2, "B.Cu"), B, 1.0, margin=5),
    a(PE, (-43.3, -14.6, "B.Cu"), (-44.1, -26.75, "B.Cu"), B, 1.0, margin=5),
]

GROUPS = [("flyback primary", FLYBACK), ("flyback secondary", FLY_SEC), ("DAB primary", DAB_PRI),
          ("DAB secondary", DAB_SEC), ("heater LLC", HEATER_LLC), ("grounds", GROUNDS), ("supply rails", RAILS),
          ("mains / PE", MAINS)]

PE_KEEPOUT = 3.25     # pour keep-out round the PE pads and tracks (PE-PRI basic creepage 3.2 mm), all copper layers


def pe_keepouts(world, rt):
    """the placement's 'PE pour keep-out' rule areas, made again from the PE copper as routed"""
    from shapely.ops import unary_union
    cu = [g for l in world.layers for g, net, kind, ref in world.items[l] if net == PE and not kind.startswith("zone")]
    u = unary_union([g.buffer(PE_KEEPOUT, 16) for g in cu]).simplify(0.02)
    polys = list(u.geoms) if u.geom_type == "MultiPolygon" else [u]
    out = []
    for i, p in enumerate(sorted(polys, key=lambda q: q.bounds)):
        out.append(dict(kind="area", name=f"S3A_KO_PE_{i + 1} (PE pads / tracks + {PE_KEEPOUT:g} mm)", layers=world.layers,
                        pts=[[round(x, 4), round(y, 4)] for x, y in p.exterior.coords[:-1]],
                        holes=[[[round(x, 4), round(y, 4)] for x, y in r.coords[:-1]] for r in p.interiors]))
        b = p.bounds
        R.log(f"PE pour keep-out {i + 1}: x {b[0]:.1f} ... {b[2]:.1f}, y {b[1]:.1f} ... {b[3]:.1f}, {p.area:.0f} mm2")
    return out


if __name__ == "__main__":
    R.run("s3a", GROUPS, sys.argv[1:], drop_areas=("PE pour keep-out",), post=pe_keepouts)
