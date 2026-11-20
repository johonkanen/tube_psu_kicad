#!/usr/bin/env python3
"""Routing stage 3e of tube_power 5.2: the J2 control-card header (2 x 25, 1.27 mm) - escape stubs of the open
J2 pins and the open nets that end at J2 (system python3).

    python3 tools/next/route_s3e_j2.py [--dry-run OUT.kicad_pcb | --strip]

Everything here is drawn copper (step format: tools/next/s3_router.py). Plan, numbers and the reasons:
kicad_next/README.md "Stage 3e".

Order of a full rebuild (a drawn structure: after stage 3d, before the grid router of stage 3b):
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

Deleted 5.1 items stay deleted (kicad_next/routing/deleted_s3e.json; a second run finds nothing to delete), one
part is moved (R77, absolute: routing/moves_s3e.json), the copper added here (routing/s3e_added.json) is removed and
rebuilt on every run.

J2 geometry: pads 0.805 mm round on every layer, pitch 1.27 mm, so 0.465 mm between two pads of a column and
between the two columns. A 0.15 mm track fits only centred (0.1575 mm each side):
  * between two signal pads on any layer (SIGNAL class clearance 0.15 mm)
  * between two GND pads only on In2 (.kicad_dru "PRIMARY_LV inner layers 0.15 mm"; 0.2 mm on the outer layers)
The header is crossed at right angles through such a gap (GAP_y) and a pad of the far column is entered at 45
degrees from the crossing point between the columns (X_MID, GAP_y).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s3_router as R  # noqa: E402

F, B, I2 = "F", "B", "2"
V5 = (0.5, 0.3)        # signal via next to J2 (as the 5.1 vias there)
V6 = (0.6, 0.3)
WJ = 0.15              # track between two J2 pads
W, WI = 0.2, 0.1524    # F.Cu / B.Cu signal width; In2 lane width of the kept 5.1 bus


def dels(net, layer, why, *segs):
    return [("delete", net, layer, *s, why) for s in segs]


def t(net, layer, w, pts, **o):
    pts = [(round(x, 4), round(y, 4)) for x, y in pts]
    return ("track", net, layer, w, pts, o) if o else ("track", net, layer, w, pts)


def v(net, x, y, size=V5, **o):
    return ("via", net, round(x, 4), round(y, 4), *size, o) if o else ("via", net, round(x, 4), round(y, 4), *size)


# ================================================================================================ J2
XW, XE = 33.1357, 34.4057           # the two pad columns (odd pins west, even pins east)
X_MID = (XW + XE) / 2               # between the columns


def pin_y(n):
    return -22.1562 + 1.27 * ((n - 1) // 2)


def gap_y(n):
    """centre of the gap between pin n and the next pin of the same column (n + 2)"""
    return pin_y(n) + 0.635


# ---- analog lines (ADC inputs of the control card)
DHB, PFC1 = "DHB_I_MEAS", "PFC_I1_MEAS"
AUX, M5V = "/04 MCU connector/AUX_MEAS", "/04 MCU connector/5V_MEAS"
OLD_ESC = "5.1 escape (0.18 mm rules): ends short of the pin, drawn again"
ANALOG = [
    # pin 38 DHB_I_MEAS: the only way in from the west is between the GND pads 35 / 37 -> In2. Via west of the
    # column, north of the 5.1 GND track on B.Cu, 0.15 mm from the pad of R90
    *dels(DHB, F, OLD_ESC, (29.7272, -0.1, 32.3319, -0.1)),
    t(DHB, F, WI, [(29.7272, -0.1), (30.85, -0.1), (31.9, -1.15)]), v(DHB, 31.9, -1.15),
    t(DHB, I2, WJ, [(31.9, -1.15), (31.9, -0.6), (31.9 + gap_y(35) + 0.6, gap_y(35)), (X_MID, gap_y(35)),
                    (XE, pin_y(38))]),
    # pin 42 PFC_I1_MEAS: R96 pin 1 (B.Cu) -> via -> F.Cu through the gap 41 / 43 (PFC_I2_MEAS has the same gap
    # on B.Cu, the In4 / In3 planes between the two)
    *dels(PFC1, B, OLD_ESC, (30.988, 3.937, 31.5648, 4.5138)),
    t(PFC1, B, WI, [(30.988, 3.937), (31.351, 4.3), (32.1, 4.3)]), v(PFC1, 32.1, 4.3),
    t(PFC1, F, WJ, [(32.1, 4.3), (32.1 + 4.3 - gap_y(41), gap_y(41)), (X_MID, gap_y(41)), (XE, pin_y(42))]),
    # pin 43 AUX_MEAS: In2 through the gap 42 / 44, east to a via between the +3V3 and 15V tracks on F.Cu, B.Cu
    # to R132 pin 2. 5V_MEAS (pin 49) passes east of that via (drawn here; it was a stage-3b route at x 35.6,
    # across this path)
    t(AUX, I2, WJ, [(XW, pin_y(43)), (X_MID, gap_y(42)), (35.9, gap_y(42)), (36.53, gap_y(42) - 0.63), (36.53, 1.6)]),
    v(AUX, 36.53, 1.6), t(AUX, B, W, [(36.53, 1.6), (37.02, 1.11), (38.345, 1.11)]),
    t(M5V, I2, W, [(XW, pin_y(49)), (XW, 8.49), (34.535, 9.89), (36.8, 9.89), (37.4, 9.29), (37.4, -2.6),
                   (36.19, -3.81), (35.635, -3.81)]),
    v(M5V, 35.635, -3.81, V6), t(M5V, B, W, [(35.635, -3.81), (35.635, -3.91), (36.035, -4.31)]),
]

# ================================================================================================ bus round H4
# The 5.1 control bus on In2 (J2 -> DRV3 / ISO1 / relay driver) ran 1.5 mm past the centre of mounting hole H4,
# which is earthed in 5.2 (hole clearance 3.2 mm): its lanes were cut there. All nine lanes are drawn again as one
# bundle round the hole: west lane (kept 5.1, y_w) -> 45 degrees south-east (c = x - y) -> east above the hole
# (radius r from its centre) -> 45 degrees south-east -> the kept 5.1 lane (y_e) -> the kept diagonal bus.
HX, HY = 5.842, -40.132             # H4
R0, PITCH = 5.03, 0.3048            # innermost lane: its edge 3.2 mm from the ring of H4 (r 1.746), 3.45 mm from the hole
C0, CSTEP = 50.888, 0.431           # west diagonals: the kept 5.1 GPIO_BYPASS_RLY diagonal, then 0.3048 mm apart
LANES = [  # net, y of the west lane, its west end x, y of the east lane, its east end x
    ("GPIO_BYPASS_RLY", -52.3, -13.0, -41.6, 12.6),
    ("+3V3", -52.8, -13.1, -42.1, 12.9),
    ("HT_CLK", -53.2, -13.2, -42.672, 13.589),
    ("SYNCH_1", -53.677, -13.2081, -43.517, 14.102),
    ("HT_SDATA", -54.058, -13.33, -43.898, 14.229),
    ("SYNCH_2", -54.439, -13.457, -44.279, 14.483),
    ("$HT_CS", -55.328, -13.1722, -45.676, 14.141),
    ("EPWM5A", -55.753, -1.848, -46.101, 14.199),      # (its west lane is drawn by stage 3c up to x -1.848)
    ("EPWM6A", -56.388, -8.7428, -46.482, 14.351),
]
CUT = "5.1 lane of the control bus on In2, cut at mounting hole H4: drawn again in the bundle round the hole"
OLD_LANES = [
    *dels("GPIO_BYPASS_RLY", I2, CUT, (0.0, -50.888, 0.0, -48.1), (10.9, -41.6, 12.6, -41.6)),
    *dels("+3V3", I2, CUT, (-13.1, -52.8, -1.1, -52.8), (-1.1, -52.8, 0.7, -51.0), (10.9, -42.1, 12.9, -42.1)),
    *dels("HT_CLK", I2, CUT, (-13.2, -53.2, -0.9, -53.2), (-0.9, -53.2, 1.016, -51.284),
          (1.016, -51.284, 1.016, -48.084), (10.366, -43.434, 11.128, -42.672), (11.128, -42.672, 13.589, -42.672)),
    *dels("SYNCH_1", I2, CUT, (-13.2081, -53.677, -0.677, -53.677), (-0.677, -53.677, 1.783, -51.217),
          (1.783, -51.217, 1.783, -48.117), (10.8, -44.152, 11.435, -43.517), (11.435, -43.517, 14.102, -43.517)),
    *dels("HT_SDATA", I2, CUT, (-13.33, -54.058, -0.249, -54.058), (-0.249, -54.058, 2.164, -51.645),
          (2.164, -51.645, 2.164, -48.536), (11.054, -44.533, 11.689, -43.898), (11.689, -43.898, 14.229, -43.898)),
    *dels("SYNCH_2", I2, CUT, (-13.457, -54.439, 0.005, -54.439), (0.005, -54.439, 2.545, -51.899),
          (2.545, -51.899, 2.545, -48.755), (11.308, -44.914, 11.943, -44.279), (11.943, -44.279, 14.483, -44.279)),
    *dels("$HT_CS", I2, CUT, (0.259, -55.328, -13.1722, -55.328), (6.224, -45.676, 3.434, -48.466),
          (14.141, -45.676, 6.224, -45.676)),
    *dels("EPWM5A", I2, CUT, (3.81, -48.641, 6.35, -46.101), (6.35, -46.101, 14.199, -46.101)),
    *dels("EPWM6A", I2, CUT, (-1.0617, -56.388, -8.7428, -56.388), (-0.8077, -56.134, -1.0617, -56.388),
          (6.604, -46.482, 4.191, -48.895), (14.351, -46.482, 6.604, -46.482)),
]


def lane(k):
    net, yw, xw, ye, xe = LANES[k]
    r = R0 + PITCH * k
    cw = C0 + CSTEP * k                        # west diagonal y = x - cw
    yt = HY - r                                # above the hole
    ce = HX - HY + r * math.sqrt(2)            # east diagonal, tangent to the circle of radius r
    pts = [(xw, yw), (cw + yw, yw), (cw + yt, yt), (HX + r * math.tan(math.pi / 8), yt), (ce + ye, ye), (xe, ye)]
    if k == 0:                                 # GPIO_BYPASS_RLY: the 5.1 lane and its diagonal to (0, -50.888) stay
        pts = [(0.0, -50.888)] + pts[2:]
    return t(net, I2, WI, pts)


# Net-(C63-Pad1) and 5V come down from the north on the east side of the bundle. 5.1 had the 5V via (In2 lane ->
# B.Cu to DRV3) at (8.81, -47.45), 7.9 mm from the hole centre, and the C63 lane round its west side: no room for
# nine lanes between them and the hole. The via stands 1.4 mm further east now and its B.Cu track passes north
# of the +1V65_BIAS via at (7.9, -49.7); C63 comes straight down x 8.8 and turns outside the bundle.
C63, P5 = "Net-(C63-Pad1)", "5V"
MOVED = "5.1 5V via / track in the way of the bundle round H4: via 1.35 mm further east"
BUNDLE = [
    *OLD_LANES,
    *[lane(k) for k in range(len(LANES))],
    *dels(C63, I2, "5.1 C63 lane round the old 5V via, drawn again outside the bundle", (8.8, -51.9, 8.8, -48.7212),
          (8.8, -48.7212, 8.1788, -48.1), (8.1788, -48.1, 8.1788, -47.2212), (8.1788, -47.2212, 8.5, -46.9),
          (8.5, -46.9, 14.7, -46.9)),
    t(C63, I2, 0.2032, [(8.8, -51.9), (8.8, -48.24), (10.14, -46.9), (14.7, -46.9)]),
    ("delvia", P5, 8.8076, -47.454, MOVED),
    *dels(P5, I2, MOVED, (8.8076, -47.454, 10.7, -47.454)),
    *dels(P5, B, MOVED, (5.133, -48.267, 7.7, -48.267), (7.7, -48.267, 7.9044, -48.267),
          (7.9044, -48.267, 8.7174, -47.454), (8.7174, -47.454, 8.8076, -47.454)),
    v(P5, 10.154, -48.0, V6), t(P5, I2, 0.3048, [(10.154, -48.0), (10.7, -47.454)]),
    t(P5, B, 0.4, [(5.133, -48.267), (7.266, -50.4), (9.25, -50.4), (10.154, -49.496), (10.154, -48.0)]),
]

# ================================================================================================ DRV3 inputs
# EPWM5A / EPWM6A (J2 pins 5 / 3) end at DRV3 pins 1 / 2 on B.Cu, below the bus. Via sites: F.Cu has the heater
# switch node (HEATER_HI_SOURCE, 1.2 mm) north of y -56.1, B.Cu the anode pad of D11 east of x -14.8 and the
# floating supply Net-(DRV3-VDDA) at y -56.1 - what is left is x -20 ... -15.3 / y -54.3 ... -51.5, and the dead
# end of the 5.1 5V lane and a 5.1 GND stub ran through it on In2. Lane order from the north: (5V), EPWM6A,
# EPWM5A; vias from the west: 5V (stage 3a), EPWM6A, EPWM5A = pin order 3, 2, 1, so nothing crosses on B.Cu.
E5, E6 = "EPWM5A", "EPWM6A"
DEAD5V = ("dead end of the 5.1 5V lane on In2 (its B.Cu half from the bus is gone; open 5V link, README stage 3e): "
          "in the via sites of EPWM5A / EPWM6A")
OLD5A = "5.1 EPWM5A escape towards the old driver footprint (its via site is taken by the heater switch node)"
DRV3 = [
    *dels(P5, I2, DEAD5V, (-21.011, -48.089, -15.2096, -53.8904), (-15.2096, -53.8904, -15.2096, -55.1484),
          (-15.2096, -55.1484, -14.014, -56.344), (-14.014, -56.344, -11.679, -56.344)),
    *dels("GND", I2, "dangling 5.1 GND stub on In2 beside the 5V lane, in the via site of EPWM5A",
          (-21.3, -48.7, -15.997, -54.003)),
    *dels(E5, I2, OLD5A, (-14.351, -55.245, -14.055, -55.245), (-14.055, -55.245, -13.547, -55.753)),
    *dels(E5, B, OLD5A, (-16.51, -54.89, -16.155, -55.245), (-16.51, -53.289, -16.51, -54.89),
          (-17.9, -51.899, -16.51, -53.289)),
    t(E5, I2, WI, [(-13.547, -55.753), (-14.657, -55.753), (-16.51, -53.9)]), v(E5, -16.51, -53.9),
    t(E5, B, W, [(-16.51, -53.9), (-16.51, -51.6), (-16.632, -51.478), (-16.632, -50.175), (-14.4, -50.175)]),
    t(E6, I2, WI, [(-8.7428, -56.388), (-14.782, -56.388), (-18.602, -52.569)]), v(E6, -18.602, -52.569),
    t(E6, B, W, [(-18.602, -52.569), (-18.602, -51.9), (-17.902, -51.2), (-17.902, -50.0)]),
]

# ================================================================================================ ISO1 pin 7
# HT_SDATA. TR2 (heater domain, Q14_DRAIN) stands 6.7 mm north of pin 7: a via / inner copper is only possible
# south of y -56.6 (8.0 mm in plan view). F.Cu from the pad south-east between the HT_CLK track of pin 6 and the
# ground via of pin 8 (stage 3a keeps that ground track out of the way: "avoid" box) to a via at y -56.5, then In2
# west, round the vias of pins 3 - 5 under the primary pad row (8.7 mm from the heater-side pads) to the end of
# the kept 5.1 lane.
SDA = "HT_SDATA"
ISO1 = [
    t(SDA, F, W, [(-37.709, -58.02), (-36.62, -58.02), (-35.1, -56.5)], foreign_gap=4.0), v(SDA, -35.1, -56.5),
    t(SDA, I2, WI, [(-35.1, -56.5), (-36.9, -56.5), (-37.2, -56.2), (-37.2, -54.306), (-36.952, -54.058)]),
]

# ================================================================================================ DRV5 inputs
# B12 / PRI_DHB_HI (J2 pins 6 / 4) arrive at the vias (19.85 / 19.0, -46.4), DAB_DIS (stage 3b) west of them at
# x 17.8: the lanes turn west below pin 1 in that order from the north. B12 enters pin 1 from below,
# PRI_DHB_HI goes round its west end into pin 2, DAB_DIS (the south-most lane) has C120 / R129 on the west side.
# DAB_DIS -> pin 5: the east ends of pins 4 - 7 are inside the 5V link pin 3 - pin 8 of stage 3a, so 0.2 mm from
# R129 pin 1 between the capacitors (C94 / C118) to the west end of pin 5; the dead-time net (R127 - C118)
# beside it is drawn here too (0.2 mm; a 0.4 mm track of stage 3b does not fit next to it).
PRI_HI, B12, DIS, DT = "PRI_DHB_HI", "B12", "DAB_DIS", "Net-(DRV5-DT)"
OLD_D5 = "5.1 stub north of the via, towards the old driver footprint"
DRV5 = [
    *dels(PRI_HI, B, OLD_D5, (19.0, -49.12, 19.0, -46.4)), *dels(B12, B, OLD_D5, (19.854, -46.4, 19.854, -48.4)),
    t(B12, B, W, [(19.854, -46.4), (19.854, -47.9), (18.954, -48.8), (16.3, -48.8), (16.3, -49.45)]),
    t(PRI_HI, B, W, [(19.0, -46.4), (19.0, -47.42), (18.0, -48.42), (14.45, -48.42), (14.15, -48.72), (14.15, -50.72),
                     (15.55, -50.72)]),
    t(DIS, B, W, [(13.375, -50.33), (12.9, -50.69), (12.175, -51.2), (12.175, -54.0), (12.375, -54.2), (14.2, -54.2),
                  (14.53, -54.53), (15.55, -54.53)]),
    t(DT, B, W, [(13.45, -56.625), (12.05, -56.625), (11.75, -56.325), (11.75, -54.4), (11.5, -54.15),
                 (11.35, -53.875)]),    # the DAB_DIS track cuts C94 pin 2 / DRV5 pin 4 and R127 pin 2 off the B.Cu ground pour: a via each into the
    # planes (through the F.Cu DC+ pour, next to the hole of the 5V via of stage 3a)
    v("GND", 14.0, -53.26), t("GND", B, 0.3, [(13.0, -53.375), (14.0, -53.26), (15.55, -53.26)]),
    v("GND", 12.45, -55.0), t("GND", B, 0.3, [(12.45, -55.0), (13.45, -54.975)]),
]

# ================================================================================================ R77 / 5V link
# (stage 3f) R77, the pull-down of EPWM6A, had no via site at its 5.1 place (F.Cu: DC+ zone of Q11's tab, B.Cu:
# bootstrap node of D11) and its In2 leg at x -9.12 crossed the only lane left for 5V. It stands south of DRV3
# pin 2 now (beside R78, the pull-down of pin 1): pin 2 on the EPWM6A pad track, pin 1 on a via into the planes.
# 5V is the tenth lane of the bundle (0.25 mm, 0.53 mm outside EPWM6A, 0.28 mm from the +1V65_BIAS via at
# (4.5, -51.5)): via beside the end of the B.Cu track at (3.6, -49.8), west diagonal, lane y -56.82 north of
# EPWM6A, then down to the 5V via of stage 3a at DRV3 pin 3 (via order from the west 5V, EPWM6A, EPWM5A).
R77_WHY = ("pull-down of EPWM6A beside DRV3 pin 2 (as R78 at pin 1): no via site at the 5.1 place, and its In2 leg "
           "crossed the 5V lane to DRV3")
R77_OLD = "5.1 connection of R77 at its old place (In2 leg from the bus / pad stubs); R77 moved to DRV3 pin 2"
C5, Y5 = 55.08, -56.82                # 5V lane: west diagonal y = x - C5, west lane y
R77_5V = [
    ("move", "R77", -17.45, -47.1, dict(rot=90), R77_WHY),
    *dels(E6, I2, R77_OLD, (-8.7428, -56.388, -9.1238, -56.769), (-9.1238, -56.769, -9.1238, -63.119)),
    *dels(E6, B, R77_OLD, (-8.616, -62.611, -8.077, -62.611), (-9.1238, -63.119, -8.616, -62.611)),
    *dels("GND", B, R77_OLD, (-6.274, -62.611, -6.35, -62.611), (-6.426, -62.611, -6.35, -62.611),
          (-6.35, -62.535, -6.35, -62.611), (-6.35, -62.687, -6.35, -62.611)),
    t(E6, B, W, [(-17.902, -49.999), (-17.902, -48.6), (-17.45, -48.15), (-17.45, -47.925)]),
    v("GND", -17.45, -45.2, V6), t("GND", B, 0.3, [(-17.45, -46.275), (-17.45, -45.2)]),
    v(P5, 4.33, -50.75), t(P5, B, 0.4, [(3.6, -49.8), (4.33, -50.75)]),
    t(P5, I2, 0.25, [(4.33, -50.75), (C5 + Y5, Y5), (-15.58, Y5), (-19.7, -52.7), (-19.7, -51.29)]),
]

GROUPS = [("J2 analog escapes", ANALOG), ("control bus round H4", BUNDLE), ("DRV3 inputs", DRV3),
          ("ISO1 pin 7", ISO1), ("DRV5 inputs", DRV5), ("R77 / 5V link", R77_5V)]

if __name__ == "__main__":
    R.RELAX_OWN_DOMAIN = True
    R.HARD_ZONES = True
    R.run("s3e", GROUPS, sys.argv[1:])
