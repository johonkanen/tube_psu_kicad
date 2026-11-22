#!/usr/bin/env python3
"""Routing stage 4a of tube_power 5.2 (2026-11-22): the DAB primary after the user placement of 2026-11-22
(Q19 / Q7 / SICD1 / SICD2 on the single primary heatsink line x 5 ... 13).

    tools/p2k/bin/kipy tools/next/route_s4_dab_primary.py [--dry-run OUT.kicad_pcb]

From this stage on the rebuild scripts (route_s3a ... route_s3e, route_s2_planes) are FROZEN: the board file is
the source of truth. This script is an incremental edit of the board as it was after the user's edit (HEAD
06889d7 + four footprint moves); it is the record of block A and is NOT re-runnable on its own result (a second
run finds nothing to delete and would add the copper twice - it refuses when routing/s4_added.json exists).

Block A = back to 0 shorts:
  1. dead copper of Q7 / Q19 / SICD1 / SICD2 at their old places, and copper on the new Q7 / Q19 pins
  2. In2 control bundle: the lanes south of SYNCH_2 are re-stacked north of Q19 pin 1 (0.5 mm HV inner-layer
     clearance to the gate pad); 5V, Net-(C63-Pad1), Net-(C11-Pad1) and the DHB_CURRENT sense line cross the pin
     column through the gap between Q19 pin 3 and Q7 pin 1 (y -53.0 ... -57.3)
  3. DRV5's small parts off the pin column (interim places - DRV5 itself is not re-laid here, see README 4a)
Writes kicad_next/routing/moves_s4.json, deleted_s4.json, s4_added.json. Zones are refilled by kicad-cli with the
project rules (as route_s2_planes.py step 7).
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
F, B, I2 = "F", "B", "2"

nm = lambda v: int(round(v * 1e6))  # noqa: E731
mm = lambda v: round(v / 1e6, 4)  # noqa: E731
DELETED, ADDED, MOVES, WARN = [], [], [], []

E6, E5, CS, S1, S2, SD = "EPWM6A", "EPWM5A", "$HT_CS", "SYNCH_1", "SYNCH_2", "HT_SDATA"
BIAS, C63, C11, P5, DHBI = "+1V65_BIAS", "Net-(C63-Pad1)", "Net-(C11-Pad1)", "5V", "DHB_CURRENT"
SW, DCP, DIS, DT, PRI = "DHB_HI_SOURCE", "DC+", "DAB_DIS", "Net-(DRV5-DT)", "PRI_DHB_HI"
D1, D2 = "/05 PFC/PFC_DRAIN_1", "/05 PFC/PFC_DRAIN_2"

OLDQ = "copper of Q7 / Q19 at their old place (x 34 ... 48, y -42): the FETs stand on the primary heatsink line now"
SPOKE = "pad spokes of a pad that is not there any more"
PINS = "on / too near the new Q19 / Q7 pins (x 12.75)"
LANE = "In2 lane through the new pin column: drawn again round it"

# ---- 1. deletions: (net, layer, x0, y0, x1, y1, why)
DEL = [
    # old Q19 / Q7 place
    ("Net-(Q19-G)", B, 46.015, -45.708, 48.155, -43.568, OLDQ), ("Net-(Q19-G)", B, 48.155, -43.568, 48.155, -41.95, OLDQ),
    ("Net-(Q19-G)", B, 41.534, -45.708, 46.015, -45.708, OLDQ),
    ("Net-(Q7-G)", B, 36.875, -41.95, 36.875, -44.707, OLDQ), ("Net-(Q7-G)", B, 36.875, -44.707, 35.836, -45.746, OLDQ),
    (SW, F, 34.335, -41.34, 34.335, -41.95, OLDQ), (SW, F, 34.335, -42.56, 34.335, -41.95, OLDQ),
    (SW, F, 34.335, -44.75, 43.075, -44.75, OLDQ), (SW, F, 34.335, -41.95, 34.335, -44.75, OLDQ),
    (SW, F, 42.465, -41.95, 43.075, -41.95, OLDQ), (SW, F, 43.075, -41.95, 43.075, -44.75, OLDQ),
    (SW, F, 43.075, -42.56, 43.075, -41.95, OLDQ), (SW, F, 43.075, -41.34, 43.075, -41.95, OLDQ),
    (SW, B, 41.315, -41.95, 43.075, -41.95, OLDQ), (SW, B, 39.502, -43.763, 41.315, -41.95, OLDQ),
    (SW, B, 39.502, -44.152, 39.502, -43.763, OLDQ),
    (DCP, F, 45.615, -41.34, 45.615, -41.95, SPOKE), (DCP, F, 45.615, -42.56, 45.615, -41.95, SPOKE),
    (DHBI, F, 31.185, -41.95, 31.795, -41.95, SPOKE), (DHBI, F, 31.795, -42.56, 31.795, -41.95, SPOKE),
    (DHBI, F, 31.795, -41.34, 31.795, -41.95, SPOKE), (DHBI, B, 31.185, -41.95, 31.795, -41.95, SPOKE),
    (DHBI, B, 31.795, -41.34, 31.795, -41.95, SPOKE), (DHBI, B, 31.795, -42.56, 31.795, -41.95, SPOKE),
    # old SICD1 / SICD2 pads
    *[(D1, F, x, y, 11.503, -21.647, SPOKE) for x, y in ((10.919, -21.647), (11.503, -21.063), (11.503, -22.231), (12.087, -21.647))],
    *[(DCP, F, x, y, 11.503, -26.727, SPOKE) for x, y in ((10.919, -26.727), (11.503, -26.143), (11.503, -27.311), (12.087, -26.727))],
    *[(D2, F, x, y, 3.8, -4.98, SPOKE) for x, y in ((3.216, -4.98), (3.8, -4.396), (3.8, -5.564), (4.384, -4.98))],
    *[(DCP, F, x, y, 3.8, 0.1, SPOKE) for x, y in ((3.216, 0.1), (3.8, 0.684), (3.8, -0.484), (4.384, 0.1))],
    # In2 bundle lanes re-stacked north of Q19 pin 1
    (S1, I2, 8.304, -46.076, 10.864, -43.517, LANE), (S1, I2, 10.864, -43.517, 14.102, -43.517, LANE), (S1, I2, 14.102, -43.517, 22.865, -34.754, LANE),
    (SD, I2, 8.431, -46.381, 10.914, -43.898, LANE), (SD, I2, 10.914, -43.898, 14.229, -43.898, LANE), (SD, I2, 14.229, -43.898, 23.246, -34.881, LANE),
    (S2, I2, 8.557, -46.686, 10.964, -44.279, LANE), (S2, I2, 10.964, -44.279, 14.483, -44.279, LANE), (S2, I2, 14.483, -44.279, 23.627, -35.135, LANE),
    (BIAS, B, 10.4, -45.1, 12.4, -45.1, "via 0.68 mm from Q19 pin 1 (HV 1.2 mm): via moved into the re-stacked bundle"),
    (BIAS, I2, 12.4, -45.1, 14.2, -45.1, LANE), (BIAS, I2, 14.2, -45.1, 27.1, -32.2, LANE),
    (CS, I2, 8.683, -46.991, 9.998, -45.676, LANE), (CS, I2, 9.998, -45.676, 14.141, -45.676, LANE), (CS, I2, 27.7, -32.117, 14.141, -45.676, LANE),
    (E5, I2, 8.809, -47.296, 10.004, -46.101, LANE), (E5, I2, 10.004, -46.101, 14.199, -46.101, LANE), (E5, I2, 14.199, -46.101, 28.1, -32.2, LANE),
    (E6, I2, 8.935, -47.6, 10.054, -46.482, LANE), (E6, I2, 10.054, -46.482, 14.351, -46.482, LANE), (E6, I2, 28.491, -32.342, 14.351, -46.482, LANE),
    (C63, I2, 8.8, -48.24, 10.14, -46.9, LANE), (C63, I2, 8.8, -51.9, 8.8, -48.24, LANE), (C63, I2, 10.14, -46.9, 14.7, -46.9, LANE),
    (C63, I2, 5.75, -54.95, 8.8, -51.9, LANE),
    (P5, I2, 10.154, -48.0, 10.7, -47.454, LANE), (P5, I2, 10.7, -47.454, 14.864, -47.454, LANE), (P5, I2, 14.864, -47.454, 15.118, -47.2, LANE),
    (P5, I2, 14.86, -47.45, 14.86, -47.49, LANE), (P5, I2, 14.86, -47.49, 14.16, -48.19, LANE), (P5, I2, 14.16, -48.19, 14.16, -51.39, LANE),
    (P5, B, 10.154, -49.496, 10.154, -48.0, LANE), (P5, B, 9.25, -50.4, 10.154, -49.496, LANE),
    (P5, B, 14.16, -51.39, 14.76, -51.99, PINS), (P5, B, 13.2, -51.99, 14.8, -51.99, PINS), (P5, B, 13.0, -51.825, 13.0, -51.79, PINS),
    (P5, B, 13.0, -51.79, 13.2, -51.99, PINS),
    (C11, I2, 15.1, -47.9, 16.4, -47.9, LANE), (C11, I2, 15.1, -47.9, 15.1, -51.4, LANE), (C11, I2, 15.1, -51.4, 13.8, -52.7, LANE),
    (C11, I2, 13.8, -52.7, 10.3, -52.7, LANE), (C11, I2, 10.3, -52.7, 7.9, -55.1, LANE),
    (DHBI, I2, 10.1, -59.3, 9.5, -59.9, LANE), (DHBI, I2, 17.6, -59.3, 10.1, -59.3, LANE), (DHBI, I2, 18.8, -58.1, 17.6, -59.3, LANE),
    (DHBI, I2, 8.2, -59.8, 9.5, -59.8, LANE), (DHBI, I2, 18.8, -52.0, 18.8, -58.1, LANE), (DHBI, I2, 7.2, -58.8, 8.2, -59.8, LANE),
    ("+3V3", I2, 16.8, -48.4, 15.6, -48.4, "dangling 5.1 stub in the way of the C11 / 5V lanes"),
    # DRV5 input side: copper on / within 1.2 mm of the new pins
    (DIS, B, 13.325, -48.63, 14.125, -47.83, PINS), (DIS, B, 13.325, -48.83, 13.325, -48.63, PINS), (DIS, B, 13.375, -50.33, 13.425, -50.33, PINS),
    (DIS, B, 13.375, -50.33, 12.9, -50.69, PINS), (DIS, B, 13.425, -50.33, 13.425, -49.03, PINS), (DIS, B, 12.9, -50.69, 12.175, -51.2, PINS),
    (DIS, B, 12.175, -51.2, 12.175, -54.0, PINS), (DIS, B, 12.175, -54.0, 12.375, -54.2, PINS), (DIS, B, 12.375, -54.2, 14.2, -54.2, PINS),
    (DIS, B, 14.2, -54.2, 14.53, -54.53, PINS), (DIS, B, 14.53, -54.53, 15.55, -54.53, PINS), (DIS, B, 14.125, -47.83, 16.425, -47.83, PINS),
    (DT, B, 13.45, -56.625, 12.05, -56.625, PINS), (DT, B, 12.05, -56.625, 11.75, -56.325, PINS), (DT, B, 11.75, -56.325, 11.75, -54.4, PINS),
    (DT, B, 11.75, -54.4, 11.5, -54.15, PINS), (DT, B, 11.5, -54.15, 11.35, -53.875, PINS),
    (PRI, B, 14.15, -50.72, 15.55, -50.72, PINS), (PRI, B, 14.15, -48.72, 14.15, -50.72, PINS), (PRI, B, 14.45, -48.42, 14.15, -48.72, PINS),
    (PRI, B, 18.0, -48.42, 14.45, -48.42, PINS), (PRI, B, 19.0, -47.42, 18.0, -48.42, PINS), (PRI, B, 19.0, -46.4, 19.0, -47.42, PINS),
    ("GND", B, 13.0, -53.375, 14.0, -53.26, PINS), ("GND", B, 14.0, -53.26, 15.55, -53.26, PINS),
    ("GND", B, 10.424, -55.55, 10.5, -55.55, SPOKE), ("GND", B, 10.5, -55.627, 10.5, -55.55, SPOKE), ("GND", B, 10.5, -55.474, 10.5, -55.55, SPOKE),
    ("GND", B, 10.576, -55.55, 10.5, -55.55, SPOKE), ("GND", B, 10.5, -55.63, 8.9, -57.23, "GND track of C96 (moved)"),
    ("GND", B, 8.9, -57.23, 8.9, -58.23, "GND track of C96 (moved)"),
    ("15V", B, 10.424, -58.7, 10.5, -58.7, SPOKE), ("15V", B, 10.5, -58.776, 10.5, -58.7, SPOKE), ("15V", B, 10.5, -58.624, 10.5, -58.7, SPOKE),
    ("15V", B, 10.576, -58.7, 10.5, -58.7, SPOKE), ("15V", B, 11.924, -61.0, 12.0, -61.0, SPOKE), ("15V", B, 12.0, -60.924, 12.0, -61.0, SPOKE),
    ("15V", B, 12.0, -61.076, 12.0, -61.0, SPOKE), ("15V", B, 12.076, -61.0, 12.0, -61.0, SPOKE), ("15V", B, 12.225, -58.7, 10.5, -58.7, PINS),
    ("15V", B, 12.5, -58.425, 12.5, -60.775, PINS), ("15V", B, 12.5, -58.425, 12.225, -58.7, PINS),
    ("Net-(D19-K)", B, 16.1, -61.0, 18.7, -61.0, "old D19 - R41 link (both moved)"),
]
DELVIA = [
    (BIAS, 12.4, -45.1, "0.68 mm from Q19 pin 1"), (P5, 10.154, -48.0, LANE), (P5, 14.16, -51.39, PINS),
    ("GND", 14.0, -53.26, PINS), ("15V", 12.5, -58.425, "inside the pad of Q7 pin 1"),
]

# ---- 2. footprint moves: ref, x, y, rot, why
INTERIM = " (interim place: DRV5 block is to be re-laid, README stage 4a)"
MOVE = [
    ("C120", 15.3, -46.45, -90, "stood on Q19 pin 2: south of DRV5 on the DAB_DIS track" + INTERIM),
    ("R129", 16.6, -46.45, -90, "stood on Q19 pin 2: south of DRV5 on the DAB_DIS track" + INTERIM),
    ("C118", 12.15, -55.8, -90, "pad overlapped Q19 pin 3: beside R127 in the gap between Q19 pin 3 and Q7 pin 1"),
    ("C94", 10.7, -52.6, 90, "stood on Q19 pin 3: 2.3 mm west of the pin column, on the 5V track" + INTERIM),
    ("D19", 17.6, -61.0, 180, "anode pad on Q7 pin 2: 3.55 mm east" + INTERIM),
    ("R41", 21.6, -62.9, 0, "room for D19: north-east of its cathode, pad 2 on the kept VDDB track" + INTERIM),
    ("C96", 16.4, -63.6, 0, "its 15V via was inside Q7 pin 1: follows D19's anode" + INTERIM),
]

# ---- 3. new copper: ("t", net, layer, width, pts) / ("v", net, x, y, dia, drill)
ADD = [
    # re-stacked bundle (0.3048 pitch from HT_CLK y -42.672; +1V65_BIAS via between SYNCH_2 and $HT_CS)
    ("t", S1, I2, 0.1524, [(8.304, -46.076), (11.403, -42.977), (14.642, -42.977), (22.865, -34.754)]),
    ("t", SD, I2, 0.1524, [(8.431, -46.381), (11.53, -43.282), (14.845, -43.282), (23.246, -34.881)]),
    ("t", S2, I2, 0.1524, [(8.557, -46.686), (11.657, -43.586), (15.176, -43.586), (23.627, -35.135)]),
    ("t", BIAS, B, 0.1524, [(10.4, -45.1), (11.424, -44.076), (12.4, -44.076)]),
    ("v", BIAS, 12.4, -44.076, 0.5, 0.3),
    ("t", BIAS, I2, 0.1524, [(12.4, -44.076), (15.224, -44.076), (27.1, -32.2)]),
    ("t", CS, I2, 0.1524, [(8.683, -46.991), (11.108, -44.566), (15.251, -44.566), (27.7, -32.117)]),
    ("t", E5, I2, 0.1524, [(8.809, -47.296), (11.234, -44.871), (15.429, -44.871), (28.1, -32.2)]),
    ("t", E6, I2, 0.1524, [(8.935, -47.6), (11.359, -45.176), (15.657, -45.176), (28.491, -32.342)]),
    # through the gap Q19 pin 3 / Q7 pin 1 (In2): C63 y -53.75, 5V -54.2, C11 -55.55, DHB_CURRENT sense -56.5
    ("t", C63, I2, 0.203, [(14.7, -46.9), (14.65, -46.95), (14.65, -53.3), (14.2, -53.75), (7.1, -53.75), (5.75, -55.1)]),
    ("t", P5, I2, 0.305, [(15.118, -47.2), (15.118, -53.8), (14.718, -54.2), (9.4, -54.2), (9.0, -54.6)]),
    ("v", P5, 9.0, -54.6, 0.6, 0.3),
    ("v", P5, 15.25, -51.99, 0.5, 0.3),                                          # DRV5 pin 3 (via in the pad, on the lane)
    ("t", P5, B, 0.4, [(9.0, -54.6), (9.0, -50.65), (9.25, -50.4)]),
    ("t", P5, B, 0.3, [(9.0, -51.825), (10.3, -51.825)]),                       # C94 pin 1
    ("t", C11, I2, 0.2, [(16.4, -47.9), (15.8, -48.5), (15.8, -55.05), (15.3, -55.55), (8.35, -55.55), (7.9, -55.1)]),
    ("t", DHBI, I2, 0.254, [(9.5, -56.5), (18.8, -56.5)]),
    ("t", DHBI, I2, 0.254, [(18.8, -52.0), (18.8, -57.873)]),
    ("v", DHBI, 31.795, -41.95, 0.6, 0.3),
    # ('Proteus F.Cu pour 23' has the relief of the old pad in its outline: a cross from the via into the pour)
    ("t", DHBI, F, 0.5, [(30.8, -41.95), (32.3, -41.95)]), ("t", DHBI, F, 0.5, [(31.795, -42.9), (31.795, -41.0)]),                                       # In2 sense line / R83 / pours: was the pad of Q7 pin 3
    # DRV5 small parts
    ("t", DIS, B, 0.4, [(15.3, -47.83), (16.425, -47.83)]),
    ("t", DIS, B, 0.3, [(15.3, -47.83), (15.3, -47.225)]),
    ("t", DIS, B, 0.3, [(16.6, -47.75), (16.6, -47.275)]),
    ("t", DT, B, 0.2, [(12.15, -56.575), (13.45, -56.625)]),
    ("t", "GND", B, 0.3, [(12.15, -55.025), (12.45, -55.0)]),
    ("t", "GND", B, 0.3, [(15.3, -45.675), (16.6, -45.625)]),
    ("v", "15V", 17.625, -51.0, 0.6, 0.3),                                       # end of the kept In2 15V lane, under DRV5
    ("t", "15V", B, 0.4, [(17.625, -51.0), (17.625, -58.6), (16.6, -59.625), (16.2, -60.4)]),
    ("v", "GND", 17.96, -64.55, 0.5, 0.3),                                       # C96 pin 2
    ("t", "15V", B, 0.5, [(15.3, -63.3), (15.3, -61.4)]),
    ("t", "Net-(D19-K)", B, 0.5, [(19.65, -61.0), (20.1375, -62.9)]),
    ("t", "Net-(DRV5-VDDB)", B, 0.4, [(21.6, -61.0), (21.812, -61.6)]),
]
# zone outline changes: name -> new outline
ZONE = {"S3A_DHB_HI_SOURCE_F": ([(28.3, -58.0), (31.0, -58.0), (31.0, -50.6), (28.3, -50.6)],
                                "switch-node area reached to the old Q7 / Q19 pins (x 44): cut back to TR3 pins 7 / 8")}


def edit(path):
    b = pcbnew.LoadBoard(path)
    lid = {b.GetLayerName(l): l for l in b.GetEnabledLayers().CuStack()}
    near = lambda p, x, y: abs(p[0] - x) <= 0.005 and abs(p[1] - y) <= 0.005  # noqa: E731
    # plain tuples first: (item, is via, net, layer, start, end, width)
    tracks = []
    for t in b.GetTracks():
        via = t.Type() == pcbnew.PCB_VIA_T
        s, e = t.GetStart(), t.GetEnd()
        tracks.append([t, via, t.GetNetname(), None if via else t.GetLayer(), (s.x / 1e6, s.y / 1e6), (e.x / 1e6, e.y / 1e6),
                       0 if via else t.GetWidth() / 1e6])
    for net, lay, x0, y0, x1, y1, why in DEL:
        hit = [r for r in tracks if not r[1] and r[2] == net and r[3] == lid[LAYER[lay]]
               and ((near(r[4], x0, y0) and near(r[5], x1, y1)) or (near(r[4], x1, y1) and near(r[5], x0, y0)))]
        if not hit:
            WARN.append(f"delete: no segment {net} {lay} ({x0}, {y0}) - ({x1}, {y1})")
        for r in hit:
            DELETED.append(dict(kind="segment", net=net, layer=LAYER[lay], start=[round(v, 4) for v in r[4]],
                                end=[round(v, 4) for v in r[5]], width=round(r[6], 4), why=why))
            b.Delete(r[0])
            tracks.remove(r)
    for net, x, y, why in DELVIA:
        hit = [r for r in tracks if r[1] and r[2] == net and near(r[4], x, y)]
        if not hit:
            WARN.append(f"delvia: no via {net} ({x}, {y})")
        for r in hit:
            DELETED.append(dict(kind="via", net=net, at=[x, y], why=why))
            b.Delete(r[0])
            tracks.remove(r)
    for ref, x, y, rot, why in MOVE:
        fp = b.FindFootprintByReference(ref)
        p = fp.GetPosition()
        MOVES.append(dict(ref=ref, frm=dict(x=mm(p.x), y=mm(p.y), rot=fp.GetOrientationDegrees(), side="B" if fp.IsFlipped() else "F"),
                          to=dict(x=x, y=y, rot=rot, side="B" if fp.IsFlipped() else "F"), why=why))
        fp.SetPosition(pcbnew.VECTOR2I(nm(x), nm(y)))
        fp.SetOrientationDegrees(rot)
    # (as s3_router.kipy_apply: save and load again between deleting / moving and adding)
    pcbnew.SaveBoard(path, b)
    b = pcbnew.LoadBoard(path)
    lid = {b.GetLayerName(l): l for l in b.GetEnabledLayers().CuStack()}
    for a in ADD:
        code = b.GetNetcodeFromNetname(a[1])
        if code <= 0:
            sys.exit(f"s4: no net {a[1]}")
        if a[0] == "v":
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(pcbnew.VECTOR2I(nm(a[2]), nm(a[3])))
            v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            v.SetWidth(pcbnew.F_Cu, nm(a[4]))
            v.SetDrill(nm(a[5]))
            v.SetNetCode(code)
            b.Add(v)
            ADDED.append(dict(kind="via", net=a[1], at=[a[2], a[3]], size=[a[4], a[5]]))
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
                ADDED.append(dict(kind="segment", net=n, layer=LAYER[lay], start=list(p), end=list(q), width=w))
    for z in b.Zones():
        if z.GetZoneName() in ZONE:
            pts, why = ZONE[z.GetZoneName()]
            o = z.Outline().Outline(0)
            DELETED.append(dict(kind="zone outline", zone=z.GetZoneName(), net=z.GetNetname(), why=why, new=pts,
                                old=[[mm(o.CPoint(k).x), mm(o.CPoint(k).y)] for k in range(o.PointCount())]))
            ol = z.Outline()
            ol.RemoveAllContours()
            ol.NewOutline()
            for x, y in pts:
                ol.Append(nm(x), nm(y))
    for z in b.Zones():                     # stale fills off (a via in the old fill of another net would take that net)
        if not z.GetIsRuleArea():
            z.UnFill()
    pcbnew.SaveBoard(path, b)
    with open(os.path.join(os.path.dirname(path), "s4.json"), "w") as f:
        json.dump(dict(deleted=DELETED, added=ADDED, moves=MOVES, warn=WARN), f)


def main(argv):
    if os.path.exists(LOCK):
        sys.exit("s4: the board is open in KiCad; close it first")
    if os.path.exists(os.path.join(RT, "s4_added.json")) and "--dry-run" not in argv:
        sys.exit("s4: routing/s4_added.json exists - this block is on the board already (not re-runnable)")
    tmp = tempfile.mkdtemp(prefix=".s4_", dir=ROOT)
    try:
        for ext in (".kicad_pcb", ".kicad_dru"):
            shutil.copy(os.path.join(PROJ, NAME + ext), tmp)
        with open(os.path.join(PROJ, NAME + ".kicad_pro")) as f:
            pro = json.load(f)
        rs = pro["board"]["design_settings"]["rule_severities"]
        for k in rs:
            rs[k] = "ignore"                       # refill only
        with open(os.path.join(tmp, NAME + ".kicad_pro"), "w") as f:
            json.dump(pro, f, indent=2)
        pcb = os.path.join(tmp, NAME + ".kicad_pcb")
        r = subprocess.run([sys.executable, "-u", os.path.abspath(__file__), "--edit", pcb])
        if r.returncode:
            sys.exit("s4: edit failed, the board is unchanged")
        r = subprocess.run([CLI, "pcb", "drc", "--format", "json", "--refill-zones", "--save-board",
                            "-o", os.path.join(tmp, "refill.json"), pcb], capture_output=True, text=True)
        if r.returncode:
            sys.exit("s4: zone refill failed, the board is unchanged\n" + r.stdout[-1500:] + r.stderr[-1500:])
        with open(os.path.join(tmp, "s4.json")) as f:
            j = json.load(f)
        for w in j["warn"]:
            print("s4: WARNING " + w)
        print(f"s4: deleted {len(j['deleted'])}, added {len(j['added'])}, moved {len(j['moves'])}")
        if "--dry-run" in argv:
            out = os.path.abspath(argv[argv.index("--dry-run") + 1])
            shutil.copy(pcb, out)
            print(f"s4: dry run in {out}, the board is unchanged")
            return 0
        shutil.copy(pcb, BOARD)
        note = "routing stage 4a (2026-11-22), tools/next/route_s4_dab_primary.py - incremental edit of the board, not a rebuild"
        for name, key in (("deleted_s4.json", "deleted"), ("s4_added.json", "added"), ("moves_s4.json", "moves")):
            with open(os.path.join(RT, name), "w") as f:
                json.dump({"note": note, key: j[key]}, f, indent=1)
        print("s4: wrote the board and routing/*_s4.json")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    if "--edit" in sys.argv:
        edit(sys.argv[sys.argv.index("--edit") + 1])
        sys.exit(0)
    sys.exit(main(sys.argv[1:]))
