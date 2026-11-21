#!/usr/bin/env python3
"""Routing stage 3d of tube_power 5.2: ISO2 / AD2 fan-out on both sides, the 420V sense divider R23 / R34 / R39
as a straight row with its 420V feed, R10 and R79 moved off their neighbours (system python3).

    python3 tools/next/route_s3d_iso2.py [--dry-run OUT.kicad_pcb | --strip]

Everything here is drawn copper (step format: tools/next/s3_router.py); only the two long DAB_DIS runs away from
ISO2 are left to the grid router. Plan, numbers and the reasons: kicad_next/README.md "Stage 3d".

Order of a full rebuild (this stage is a drawn structure: it runs before the grid router of stage 3b):
    python3 tools/next/route_s3b_signals.py --strip
    python3 tools/next/route_s3e_j2.py --strip
    python3 tools/next/route_s3d_iso2.py --strip
    python3 tools/next/route_s3c_cleanup.py --strip
    python3 tools/next/route_s3a_power.py
    python3 tools/next/route_s3c_cleanup.py
    python3 tools/next/route_s3d_iso2.py
    python3 tools/next/route_s3e_j2.py
    python3 tools/next/route_s3b_signals.py
    tools/p2k/bin/kipy tools/next/route_s2_planes.py

Deleted 5.1 items stay deleted (kicad_next/routing/deleted_s3d.json; a second run finds nothing to delete), the
part moves are absolute (routing/moves_s3d.json), the copper added here (routing/s3d_added.json) is removed and
rebuilt on every run.

Rules of this stage (besides the ones the engine checks):
  * no via closer than 11.1 mm in plan view to copper of the other domain (a via has a ring / barrel on the inner
    layers): primary vias at x <= 58.8, secondary vias at x >= 74.3 (the 5.1 vias at x 60.8 / 73.1 are deleted).
    Between the pads and the vias the nets are on F.Cu only, where the ISO2 slot counts (foreign_gap, judged by
    check_domains.py)
  * primary side: nothing in the gap between the TR1 and ISO2 slots (only the first 1.9 mm of pin 8's ground)
  * no track on In1 / In4; SPI on In2 over the GND / ISO_GND planes, no B.Cu or F.Cu run that cuts a plane
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s3_router as R  # noqa: E402

F, B, I2 = "F", "B", "2"
V5 = (0.5, 0.3)        # via of the signal nets at ISO2 / AD2 (as the 5.1 vias there: the In2 lanes are 0.51 mm apart)
V6 = (0.6, 0.3)
FG = dict(foreign_gap=4.0)        # F.Cu between an ISO2 pad and its via: slot credit, judged by check_domains.py
W, WI = 0.2, 0.1524               # F.Cu / B.Cu signal width; In2 lane width of the kept 5.1 bus


def dels(net, layer, why, *segs):
    return [("delete", net, layer, *s, why) for s in segs]


def t(net, layer, w, pts, **o):
    return ("track", net, layer, w, pts, o) if o else ("track", net, layer, w, pts)


def v(net, x, y, size=V5, **o):
    return ("via", net, x, y, *size, o) if o else ("via", net, x, y, *size)


# ================================================================================================ parts
ROW = "420V sense divider as a straight row (R39 - R34 - R23, 3.8 mm pitch): unlike nodes of two parts >= 1.2 mm apart"
MOVES = [
    ("move", "R39", 76.9, -22.3, dict(rot=180), ROW + "; CUK_CAP_MEAS2 end west"),
    ("move", "R34", 80.7, -22.3, dict(rot=180), ROW),
    ("move", "R23", 84.5, -22.3, dict(rot=180), ROW + "; 420V end east, 6.8 mm from mounting hole H5"),
    ("move", "R10", 18.7, 4.6, {}, "DC-link divider: R10 pin 1 (133 ... 150 V) 1.2 mm from the U6 input tracks and R109"),
    ("move", "R79", 34.8, 14.6, {}, "mains divider: room for the via of R79 pin 1 (<= 120 V peak) 1.2 mm from R49 / R79 "
                                    "pin 2, the 15V via and the DC+ track"),
]

# ================================================================================================ ISO2, primary side
E2A, E2B, DIS, CS, CLK, SDA = "EPWM2A", "EPWM2B", "DAB_DIS", "$CUK_CS", "CUK_CLK", "CUK_SDATA"
OLDVIA = "5.1 via 9.4 mm in plan view from ISO2's secondary pads (inner-layer ring inside the 11.1 mm barrier)"
LANE = "end of the kept 5.1 In2 lane, drawn again to the new via"
PRI = [
    ("delvia", E2A, 60.761, -29.7756, OLDVIA), ("delvia", E2B, 60.761, -28.5056, OLDVIA),
    ("delvia", CS, 57.4477, -25.9662, "5.1 via in the way of the fan-out (the lane ends 1.1 mm further east now)"),
    *dels(E2A, I2, LANE, (59.11, -28.6326, 59.11, -26.1045), (59.11, -26.1045, 57.8287, -24.8232),
          (57.8287, -24.8232, 46.5249, -24.8232)),
    *dels(E2B, I2, LANE, (46.9762, -24.3152, 58.0827, -24.3152)),
    *dels(CS, I2, LANE, (57.44767, -25.9662, 56.83747, -25.356)),
    *dels("GND", F, "dangling 5.1 stub across the fan-out channel between C98 and the pin row",
          (60.766, -27.2356, 60.5884, -27.2356), (60.5884, -27.2356, 59.623, -28.201)),
    # pads -> bundle between C98 pin 2 and D5 pin C, order = pin order (south to north): GND 8, 7, 6, 5, 4, 3, 2.
    # Pins 2 / 3 come down the 0.98 mm channel between C98 and the pin row. The vias stand north of the 15V pour
    # (the pour strip y -23.8 ... -23.0 is the link D5 cathode - C39) and south of the CS lane on In2.
    # pin 8 GND: south-most, via into the planes west of D5
    t("GND", F, W, [(62.107, -22.155), (60.9, -22.155), (60.25, -22.805), (60.25, -24.05), (59.77, -24.53),
                    (57.38, -24.53), (57.35, -24.5)], **FG),
    v("GND", 57.35, -24.5),
    # pin 7 CUK_SDATA, pin 6 CUK_CLK: round the corner of D5 pin C; their lanes come up to the vias
    t(SDA, F, W, [(62.107, -23.425), (60.95, -23.425), (60.7, -23.675), (60.7, -24.2), (59.85, -25.05),
                  (57.1, -25.05), (56.55, -24.5)], **FG),
    v(SDA, 56.55, -24.5), t(SDA, I2, WI, [(47.541, -23.241), (55.291, -23.241), (56.55, -24.5)]),
    t(CLK, F, W, [(62.107, -24.695), (60.9, -24.695), (60.195, -25.4), (56.7, -25.4), (55.8, -24.5)], **FG),
    v(CLK, 55.8, -24.5), t(CLK, I2, WI, [(53.1414, -23.7804), (55.0804, -23.7804), (55.8, -24.5)]),
    # pin 5 $CUK_CS, pin 4 DAB_DIS: vias in the middle of the bundle (their lanes are the two northern ones)
    t(CS, F, W, [(62.107, -25.965), (58.55, -25.965)], **FG),
    v(CS, 58.55, -25.965), t(CS, I2, WI, [(56.8375, -25.356), (57.941, -25.356), (58.55, -25.965)]),
    t(DIS, F, W, [(62.107, -27.235), (61.25, -27.235), (60.515, -26.5), (57.85, -26.5)], **FG),
    v(DIS, 57.85, -26.5), t(DIS, I2, W, [(57.85, -26.5), (57.4, -26.05), (46.8, -26.05)]),
    # pin 3 EPWM2B, pin 2 EPWM2A: north of those two vias, then south-west over the CS / DAB_DIS lanes to their own
    t(E2B, F, W, [(62.107, -28.505), (60.97, -28.505), (60.77, -28.305), (60.77, -27.475), (60.345, -27.05),
                  (57.385, -27.05), (54.65, -24.315)], **FG),
    v(E2B, 54.65, -24.3152), t(E2B, I2, WI, [(46.9762, -24.3152), (54.65, -24.3152)]),
    t(E2A, F, W, [(62.107, -29.775), (60.62, -29.775), (60.42, -29.575), (60.42, -27.62), (60.2, -27.4),
                  (56.777, -27.4), (54.2, -24.823)], **FG),
    v(E2A, 54.2, -24.8232), t(E2A, I2, WI, [(46.5249, -24.8232), (54.2, -24.8232)]),
    # DAB_DIS (new in 5.2: J2 pin 18 -> ISO2 -> DRV6): In2 lane north of the CS lane, then beside the bus to J2
    # pin 18 (the grid router; stage 3b joins DRV5 / C120 / R129 to the same pin afterwards)
    ("auto", DIS, (46.8, -26.05, "In2.Signal_HV"), "J2.18",
     dict(layers="2F", w=W, via=V6, margin=4.0, via_cost=40.0, zone_cost=10.0, relax=("J2",))),
]

# ================================================================================================ ISO2, secondary side
ACS, ACK, ASD = "Net-(AD2-CS)", "Net-(AD2-CLK)", "Net-(AD2-SDATA)"
HI, LO, DSEC = "ISO_SEC_DHB_HI", "ISO_SEC_DHB_LO", "DAB_DIS_SEC"
A3, IG, MEAS, MEASN = "AD2_3V3", "ISO_GND", "CUK_CAP_MEAS2", "CUK_CAP_MEAS-"
STUB15 = ("dead 5.1 15V_ISO_SEC track on F.Cu (its far end at (77.5, -42.8) lost its via and In2 track in stage 3c; the "
          "rail is the In3 pour): a wall between ISO2's secondary pins and everything east of them")
OLDSEC = "5.1 via 9.7 ... 11.0 mm in plan view from ISO2's primary pads (inside the 11.1 mm barrier), with its stub"
SPI51 = "5.1 SPI lane on In2 / escape at AD2, drawn again (AD2's vias moved out of the way of the 420V feed)"
SEC = [
    *dels("15V_ISO_SEC", F, STUB15, (77.475, -42.501, 77.475, -42.7931), (77.094, -42.12, 77.475, -42.501),
          (74.92, -42.12, 77.094, -42.12), (72.5, -39.7, 74.92, -42.12), (72.5, -33.058, 72.5, -39.7),
          (73.5726, -31.9854, 72.5, -33.058), (74.0146, -31.9854, 73.5726, -31.9854),
          (74.99, -31.01, 74.0146, -31.9854), (74.99, -28.912, 74.99, -31.01), (75.244, -28.658, 74.99, -28.912)),
    *dels(IG, F, OLDSEC, (73.72, -28.15, 73.085, -27.515), (73.085, -27.515, 73.085, -27.261)),
    ("delvia", IG, 73.085, -27.261, OLDSEC),
    *dels(ACK, F, OLDSEC, (73.085, -24.848, 72.9326, -24.6956)), ("delvia", ACK, 73.085, -24.848, OLDSEC),
    ("delvia", ACS, 73.085, -25.9656, OLDSEC),
    *dels(ASD, F, OLDSEC, (74.355, -25.356, 73.593, -24.594), (73.593, -24.594, 73.593, -23.991),
          (73.593, -23.991, 73.0276, -23.4256)), ("delvia", ASD, 74.355, -25.356, OLDSEC),
    *dels(ACK, I2, SPI51, (80.451, -34.5, 81.467, -33.484)),
    *dels(ACS, I2, SPI51, (80.324, -29.0898, 80.324, -29.1406), (80.324, -32.595, 80.324, -29.1406),
          (80.324, -28.924, 80.324, -29.0898), (77.3656, -25.9656, 80.324, -28.924)),
    *dels(ACS, B, SPI51, (80.324, -32.595, 79.6636, -32.595)), ("delvia", ACS, 80.324, -32.595, SPI51),
    *dels(ASD, I2, SPI51, (80.959, -33.0522, 80.959, -28.785), (80.959, -28.785, 77.53, -25.356),
          (80.451, -33.5602, 80.959, -33.0522)),
    *dels(ASD, B, SPI51, (79.6636, -33.5602, 80.451, -33.5602)), ("delvia", ASD, 80.451, -33.5602, SPI51),
    *dels(A3, F, "dangling 5.1 stub (its via went in stage 3c)", (73.3875, -30.3875, 73.9, -30.9)),
    *dels(A3, I2, "5.1 AD2_3V3 link on In2 across the lanes of the gate signals; AD2_3V3 comes on B.Cu now",
          (75.5, -32.5, 78.7238, -32.5)),
    *dels(A3, B, "stub to the deleted via", (78.7238, -31.5282, 78.7238, -32.5)),
    ("delvia", A3, 78.7238, -32.5, "5.1 via of the In2 link, where the AD2-CS via stands now"),
    # ---- SPI: pins 10 / 11 / 12 straight east on F.Cu to vias 11.17 mm from the primary pads, In2 lanes over the
    #      ISO_GND planes, AD2 from the east (CLK, SDATA) and from under the package (CS)
    t(ASD, F, W, [(71.407, -23.425), (74.55, -23.425)], **FG), v(ASD, 74.55, -23.425),
    t(ASD, I2, W, [(74.55, -23.425), (79.78, -23.425), (81.05, -24.695), (81.05, -35.3)]), v(ASD, 81.05, -35.3),
    t(ASD, B, W, [(81.05, -35.3), (81.05, -33.86), (80.75, -33.56), (79.6636, -33.56)]),
    t(ACK, F, W, [(71.407, -24.695), (74.55, -24.695)], **FG), v(ACK, 74.55, -24.695),
    t(ACK, I2, W, [(74.55, -24.695), (79.18, -24.695), (80.451, -25.966), (80.451, -34.5)]),
    t(ACS, F, W, [(71.407, -25.965), (74.55, -25.965)], **FG), v(ACS, 74.55, -25.965),
    t(ACS, I2, W, [(74.55, -25.965), (77.965, -25.965), (78.6, -26.6), (78.6, -32.55), (78.8, -32.75)]),
    v(ACS, 78.8, -32.75), t(ACS, B, W, [(78.8, -32.75), (78.955, -32.595), (79.6636, -32.595)]),
    # ---- gate signals: pin 15 between the pads of C103, pins 14 / 13 south of it, vias east of the 5V_ISOL track
    #      on B.Cu, In2 lanes north to the kept 5.1 lanes (x 74.5 ... 75.9: 11.3 mm from the primary pads)
    t(HI, F, W, [(71.407, -29.775), (72.3, -29.775), (73.125, -28.95), (75.2, -28.95), (75.35, -28.8),
                 (75.57, -28.8)], **FG),
    v(HI, 75.57, -28.8, V6),
    t(HI, I2, WI, [(75.57, -28.8), (75.3, -29.07), (75.3, -32.45), (75.9, -33.05), (75.9, -38.3),
                   (76.672, -39.072)]),
    t(LO, F, W, [(71.407, -28.505), (72.6, -28.505), (72.84, -28.265), (72.84, -27.7), (73.14, -27.4),
                 (75.57, -27.4)], **FG),
    v(LO, 75.57, -27.4, V6),
    t(LO, I2, WI, [(75.57, -27.4), (74.9, -28.07), (74.9, -32.65), (75.5, -33.25), (75.5, -39.91),
                   (75.405, -40.005)]),
    t(DSEC, F, W, [(71.407, -27.235), (72.2, -27.235), (72.685, -26.75), (76.3, -26.75)], **FG),
    v(DSEC, 76.3, -26.75, V6),
    t(DSEC, I2, WI, [(76.3, -26.75), (74.65, -26.75), (74.5, -26.9), (74.5, -32.85), (75.1, -33.45), (75.1, -39.2),
                     (74.7, -39.6), (74.7, -40.6)]),
    ("auto", DSEC, (74.7, -40.6, "In2.Signal_HV"), "DRV6.5",
     dict(layers="2B", w=W, via=V6, margin=5.0, via_cost=40.0, zone_cost=10.0, relax=("DRV6",))),
    # ---- supplies of the secondary side
    # pin 9: south of the divider row to the via between the pads of D4 (where stage 3a had it; 0.6 mm now)
    t(IG, F, 0.3, [(71.407, -22.155), (73.6, -22.155), (74.855, -20.9), (76.0, -20.9), (76.507, -20.393),
                   (76.507, -20.355)], **FG),
    v(IG, 76.507, -20.355, V6),
    t(IG, F, W, [(73.72, -28.175), (76.55, -28.175)], **FG),                             # C103 pin 2 -> R38 pin 2
    t(A3, F, 0.3, [(71.407, -31.045), (72.607, -31.045), (73.207, -30.445)], **FG),             # pin 16 -> C103 pin 1
    t(A3, F, 0.3, [(72.607, -31.045), (74.45, -31.045), (75.405, -32.0), (75.9, -32.0)], **FG),
    v(A3, 75.9, -32.0, V6), t(A3, B, 0.3, [(75.9, -32.0), (75.9, -35.2366)]),
]

# ================================================================================================ DRV6 inputs
# 2026-11-21: TR3's secondary finish (the switch node) is on pins 11 / 12, where R75 / R76 (pull-downs of DRV6's
# inputs) stood on B.Cu: they are 2.55 mm further east now (routing/moves_user.json). The gate signals come from the
# east on In2 (5.1 lanes x 78.1 / 79.4), tap their pull-down east of the pin column, pass between the pads of pins
# 10 and 11 (LO 0.65 mm from pin 10, HI 0.75 mm from pin 11, inner-layer rule 0.5 mm) and end on vias under DRV6:
# no via of these nets within 1.2 mm of the switch-node track on F.Cu (y -61.8) or of a transformer pin on an outer
# layer. LO's via is on its lane (1.34 mm from the TRANS_SEC area on F.Cu), HI's south of R75 with an In2 stub.
SWN = "DHB_HI_SOURCE_SEC"
D6_OLD = "5.1 end of the gate-signal lane at the old place of R75 / R76 (through the pin place 11 of TR3)"
RPD_OLD = "5.1 copper at the old place of R75 / R76 (0.7 mm from the pin place 11 of TR3, now the switch node)"
DRV6_IN = [
    *dels(HI, I2, D6_OLD, (68.975, -61.452, 68.34, -61.452), (70.88, -59.547, 68.975, -61.452)),
    ("delvia", HI, 68.34, -61.452, D6_OLD),
    # (the same three items under the net name KiCad gave them when the pad of pin 11 was put on top of them)
    *dels(SWN, I2, D6_OLD, (68.975, -61.452, 68.34, -61.452), (70.88, -59.547, 68.975, -61.452)),
    ("delvia", SWN, 68.34, -61.452, D6_OLD),
    *dels(LO, I2, D6_OLD, (68.7, -60.182, 69.605, -59.277)),
    *dels(IG, B, RPD_OLD, (71.3576, -61.496, 71.51, -61.496), (71.51, -61.3436, 71.51, -61.496),
          (71.51, -61.6484, 71.51, -61.496), (71.6624, -61.496, 71.51, -61.496), (71.3576, -60.226, 71.51, -60.226),
          (71.51, -60.0736, 71.51, -60.226), (71.51, -60.3784, 71.51, -60.226), (71.6624, -60.226, 71.51, -60.226)),
    # In2 lanes from the ends of the 5.1 lanes
    t(LO, I2, 0.4, [(78.105, -54.677), (73.932, -58.85), (65.0, -58.85), (64.4, -59.45), (64.0, -59.45)]),
    t(HI, I2, 0.4, [(79.38, -54.947), (74.677, -59.65), (66.2, -59.65), (65.65, -60.2), (63.55, -60.2), (62.8, -59.45)]),
    # DRV6 pins 2 / 1 -> vias under the package
    v(LO, 64.0, -59.45, V6), t(LO, B, 0.4, [(65.657, -60.182), (64.5, -60.182), (64.0, -59.68), (64.0, -59.45)]),
    v(HI, 62.8, -59.45, V6), t(HI, B, 0.4, [(65.657, -61.35), (63.0, -61.35), (62.8, -61.15), (62.8, -59.45)]),
    # pull-downs: R76 pin 2 -> via on the LO lane (B.Cu crosses the HI lane), R75 pin 2 -> via south of it, In2 stub
    v(LO, 73.6, -58.85, V6), t(LO, B, 0.3, [(72.375, -60.226), (73.6, -59.001), (73.6, -58.85)]),
    v(HI, 72.375, -62.75, V6), t(HI, B, 0.3, [(72.375, -61.496), (72.375, -62.75)]),
    t(HI, I2, 0.4, [(72.375, -62.75), (72.375, -59.65)]),
    # ISO_GND ends of R75 / R76 -> R147 pin 1 (its vias: stage 3a)
    t(IG, B, 0.3, [(74.025, -61.496), (74.025, -60.226)]), t(IG, B, 0.3, [(74.025, -60.98), (76.1, -60.98)]),
]

# ================================================================================================ 420V divider
N1, N2 = "Net-(R23-Pad2)", "Net-(R34-Pad2)"
OLDDIV = "5.1 link of the divider at the old places of R23 / R34 / R39"
DIVIDER = [
    *dels(N1, F, OLDDIV, (79.3, -25.4, 79.1, -25.4), (80.9, -23.4, 80.1, -24.2), (79.1, -25.4, 79.1, -25.275),
          (80.1, -24.6, 79.3, -25.4), (80.1, -24.2, 80.1, -24.6), (81.2, -23.4, 80.9, -23.4)),
    *dels(N2, F, OLDDIV, (76.9, -23.4, 79.1, -23.4)),
    *dels(MEAS, F, OLDDIV, (76.9, -27.1, 77.7, -27.1), (76.9, -25.4, 76.9, -27.1)),
    *dels(MEASN, B, "5.1 stub of the In2 hop that stage 3b made under the new place of R23",
          (82.4, -22.3, 83.3, -23.2), (82.1, -22.3, 82.4, -22.3)),
    t(N2, F, W, [(77.9, -22.3), (79.7, -22.3)]), t(N1, F, W, [(81.7, -22.3), (83.5, -22.3)]),
    # CUK_CAP_MEAS2 (about 1 V): F.Cu west of the 140 V node, via between the SPI lanes, B.Cu to U3 pin 3
    t(MEAS, F, W, [(75.9, -22.3), (75.6, -22.6), (75.6, -24.0), (76.93, -25.33)]), v(MEAS, 76.93, -25.33),
    t(MEAS, B, WI, [(76.93, -25.33), (76.93, -26.33), (77.7, -27.1)]),
    # CUK_CAP_MEAS- (R113 pin 1 -> R120 pin 2): B.Cu round R120 pin 1, no via under the divider
    t(MEASN, B, W, [(81.361, -26.6), (81.75, -26.6), (83.3, -25.05), (83.3, -22.7), (82.9, -22.3), (82.1, -22.3)]),
    # 420V: F.Cu from the pour, between AD2's vias and the 4.2 mm keep-off of mounting hole H5 (an arc of radius
    # 6.2 mm round the hole: 4.35 mm from its ring), into pin 1 from the north
    t("420V", F, W, [(85.9, -43.1), (85.9, -38.0), (83.9, -36.0), (82.3, -34.0), (81.529, -32.433),
                     (81.179, -31.491), (80.987, -30.504), (80.956, -29.499), (81.088, -28.503),
                     (81.379, -27.541), (81.822, -26.638), (82.405, -25.819), (83.113, -25.106),
                     (83.927, -24.515), (84.825, -24.064), (85.5, -23.4), (85.5, -22.3)]),
]

# ================================================================================================ R10 / R79
X10, UM6, UP6 = "Net-(R10-Pad1)", "Net-(U6--)", "Net-(U6-+)"
X79, UM8 = "Net-(R48-Pad2)", "Net-(U8--)"
OLD10, OLD79 = "5.1 copper at the old place of R10", "5.1 copper at the old place of R79"
R10_R79 = [
    *dels(X10, F, OLD10, (17.5, 1.9, 17.5, 3.0), (17.3, 1.9, 17.5, 1.9)),
    *dels(X10, B, OLD10, (17.5, 3.0, 18.6, 3.0)), ("delvia", X10, 17.5, 3.0, OLD10),
    *dels(UM6, B, "5.1 track 0.92 ... 1.12 mm from R10 pin 1", (20.5, 2.3398, 20.5, 3.0), (19.7, 1.5398, 20.5, 2.3398),
          (18.8316, 1.5398, 19.7, 1.5398)),
    *dels(UP6, B, OLD10, (18.7, 4.9, 21.4, 4.9), (18.6, 5.0, 18.7, 4.9)),
    v(X10, 17.7, 3.5), t(X10, B, W, [(17.7, 3.5), (18.4, 3.6)]), t(X10, F, W, [(17.7, 3.5), (17.7, 2.4), (17.3, 1.9)]),
    t(UM6, B, WI, [(18.8316, 1.5398), (20.2, 1.5398), (20.7, 2.04), (20.7, 3.0)]),
    t(UP6, B, WI, [(18.7, 5.6), (20.95, 5.6), (21.4, 5.15), (21.4, 4.875)]),
    *dels(X79, B, OLD79, (35.2, 15.4, 35.2, 15.7), (33.95, 15.4, 35.2, 15.4)), ("delvia", X79, 33.95, 15.4, OLD79),
    *dels(UM8, B, OLD79, (35.0, 13.9, 33.6272, 13.9), (35.2, 13.7, 35.0, 13.9)),
    v(X79, 35.85, 15.56), t(X79, B, W, [(35.85, 15.56), (35.3, 15.56)]),
    t(X79, I2, WI, [(33.95, 15.4), (34.11, 15.56), (35.85, 15.56)]),
    t(UM8, B, WI, [(33.6272, 13.9), (33.9, 13.627), (34.6, 13.627)]),
]

GROUPS = [("part moves", MOVES), ("ISO2 primary side", PRI), ("ISO2 secondary side", SEC), ("DRV6 inputs", DRV6_IN),
          ("420V divider", DIVIDER), ("R10 / R79", R10_R79)]


def keepouts(world, rt):
    """B.Cu: no pour between ISO2's primary pad row and its slot. The kept 5.1 GND pour reached 0.9 mm past the
    pads (x 64.0), which would push every secondary In2 track and the In3 15V_ISO_SEC lane another 0.9 mm east
    (11.1 mm in plan view, layer to layer). Rule areas S3D_KO_*, rebuilt on every run."""
    return [dict(kind="area", name="S3D_KO_ISO2_pri_B (no pour east of ISO2's primary pads)", layers=["B.Cu"],
                 pts=[[63.2, -32.6], [66.2, -32.6], [66.2, -21.6], [63.2, -21.6]]),
            # the island of the 5.1 ISO_GND pour under C103 hung on the deleted via at (73.1, -27.3): no fill there
            dict(kind="area", name="S3D_KO_ISO2_sec_B (no pour island under C103)", layers=["B.Cu"],
                 pts=[[72.7, -31.8], [74.38, -31.8], [74.38, -25.6], [72.7, -25.6]])]


if __name__ == "__main__":
    R.RELAX_OWN_DOMAIN = True
    R.HARD_ZONES = True
    R.run("s3d", GROUPS, sys.argv[1:], post=keepouts)
