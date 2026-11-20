#!/usr/bin/env python3
"""Routing stage 3c of tube_power 5.2: clean-up of the copper kept from the 5.1 board (system python3).

    python3 tools/next/route_s3c_cleanup.py [--dry-run OUT.kicad_pcb | --strip]

The kept 5.1 tracks / vias were drawn for 5.1's rules (7 mil everywhere). This step removes the ones that break
the 5.2 high-voltage functional spacing (1.2 mm on the outer layers, tube_psu_5_2.kicad_dru) or a net class
clearance and draws them again with the engine of stage 3a / 3b (tools/next/s3_router.py), and it removes
dangling 5.1 copper that no open connection starts on. Plan and list: kicad_next/README.md "Stage 3c".

Order of a full rebuild (this step sees the copper of stage 3a, stage 3d = the ISO2 / AD2 fan-out sees both, and
stage 3b all three):
    python3 tools/next/route_s3b_signals.py --strip
    python3 tools/next/route_s3d_iso2.py --strip
    python3 tools/next/route_s3c_cleanup.py --strip
    python3 tools/next/route_s3a_power.py
    python3 tools/next/route_s3c_cleanup.py
    python3 tools/next/route_s3d_iso2.py
    python3 tools/next/route_s3b_signals.py
    tools/p2k/bin/kipy tools/next/route_s2_planes.py

Step format: s3_router.py. Deleted 5.1 items stay deleted (kicad_next/routing/deleted_s3c.json, a second run finds
nothing to delete); the copper added here (routing/s3c_added.json) is removed and rebuilt on every run.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s3_router as R  # noqa: E402

F, B, I2 = "F", "B", "2"
VS = (0.6, 0.3)
HS, SWS = "DHB_HI_SOURCE", "DHB_HI_SOURCE_SEC"
HHS = "/06 Heaters/HEATER_HI_SOURCE"
HHG = "/06 Heaters/HEATER_HI_GATE"

SPOKE = "5.1 thermal-spoke segment inside its own pad, 0.9 mm from the next pin of the TO-220 / part"
WIDE = "5.1 track wider than the pin pitch allows (< 1.2 mm to the next pin); drawn again 0.75 mm at the pins"
DANGLE = "dangling 5.1 stub inside the 1.2 mm HV spacing of another net"


def dels(net, layer, why, *segs):
    return [("delete", net, layer, *s, why) for s in segs]


def plane(net, pad, layer="In3.Power", layers="B", w=0.3, **o):
    """pad -> short track -> via in the pour of the net on an inner layer"""
    return ("auto", net, pad, "via:" + layer, dict(layers=layers, w=w, via=VS, via_cost=1e9, margin=3.5, **o))


def re(net, start, hint, layers, w, **o):
    """route `start` to the rest of the net near `hint` (the s3b row convention)"""
    opt = dict(layers=layers, w=w, via=VS, margin=3.0, via_cost=20.0, zone_cost=10.0)
    opt.update(o)
    opt["window"] = [hint] + list(opt.get("window", []))
    return ("auto", net, start, "net", opt)


# ------------------------------------------------------------------------------------------------ DAB primary
# Q7 (low side) / Q19 (high side), TO-220 on 2.54 mm: a track leaves a pin 0.75 mm wide (1.21 mm to both
# neighbours). The 5.1 switch-node track Q7 pin 2 -> Q19 pin 3 (1.78 mm, 0.57 mm above the gate pad of Q7) is
# drawn again inside the zone S3A_DHB_HI_SOURCE_F: 1.15 mm along y -44.75, 1.22 mm from the gate pad of Q7 and
# from the end of the 1.5 mm DC+ track of stage 3a (y -47.3).
FG = dict(foreign_gap=4.0)         # copper at the barrier parts Q19 / Q21 (slot between them): judged by check_domains.py
DAB_PRI = [
    *dels(HS, F, SPOKE, (33.7254, -41.9499, 34.335, -41.9499), (34.9446, -41.9499, 34.335, -41.9499),
          (43.6846, -41.9499, 43.075, -41.9499)),
    *dels("DC+", F, SPOKE, (45.0054, -41.9499, 45.615, -41.9499), (46.2246, -41.9499, 45.615, -41.9499)),
    *dels("DHB_CURRENT", F, SPOKE, (32.4046, -41.9499, 31.795, -41.9499)),
    *dels("DHB_CURRENT", B, SPOKE, (32.4046, -41.9499, 31.795, -41.9499)),
    *dels(HS, F, WIDE, (34.335, -41.9499, 34.335, -43.517), (34.335, -43.517, 35.224, -44.406),
          (35.224, -44.406, 35.315, -44.406), (35.315, -44.406, 37.3543, -44.406), (37.3543, -44.406, 41.297, -44.406),
          (41.297, -44.406, 42.8641, -42.8389), (42.8641, -42.8389, 43.075, -41.9499)),
    ("track", HS, F, 0.75, [(34.335, -41.95), (34.335, -44.75)], FG),
    ("track", HS, F, 1.15, [(34.335, -44.75), (43.075, -44.75)], FG),
    ("track", HS, F, 0.75, [(43.075, -41.95), (43.075, -44.75)], FG),
    *dels(HS, B, WIDE, (41.315, -41.9499, 43.075, -41.9499)),
    ("track", HS, B, 0.75, [(41.315, -41.95), (43.075, -41.95)], FG),
    *dels("Net-(Q7-G)", B, WIDE, (36.875, -41.9499, 36.875, -44.707)),
    ("track", "Net-(Q7-G)", B, 0.75, [(36.875, -41.95), (36.875, -44.707)]),
    # high-side gate track (to DRV5) 0.94 mm from the low-side gate track / 1.17 mm from D34: routed again
    *dels("DHB_HI_GATE", B, "5.1 high-side gate track < 1.2 mm from the low-side gate track and D34",
          (39.049, -49.486, 36.935, -51.6), (36.935, -51.6, 36.2175, -51.6), (36.2175, -51.6, 35.2175, -52.6)),
    re("DHB_HI_GATE", (39.049, -49.486, "B.Cu"), (35.2175, -52.6), B, 0.5),
]

# ------------------------------------------------------------------------------------------------ DAB secondary
DAB_SEC = [
    *dels("420V", F, SPOKE, (56.6054, -41.9499, 57.215, -41.9499), (57.8246, -41.9499, 57.215, -41.9499)),
    *dels("ISO_GND", B, SPOKE, (67.0208, -41.9499, 66.335, -41.9499)),
    # switch node at Q21 pin 3: 0.75 mm past the 420V pin, then the 1.6 mm of stage 3a
    *dels(SWS, F, WIDE, (54.675, -46.215, 54.675, -41.9499)),
    ("track", SWS, F, 0.75, [(54.675, -41.95), (54.675, -44.6)], FG),
    ("track", SWS, F, 1.6, [(54.675, -44.6), (54.675, -46.215)], FG),
    # gate-source resistor R56 (10 k) above Q21 pin 2 (420V): its two 0.76 mm tracks pass 0.8 / 0.97 mm above the
    # pin; 0.3 mm tracks along the upper half of its pads (1.3 mm)
    *dels(SWS, B, "5.1 track to R56 0.8 mm above Q21 pin 2 (420V)", (56.5708, -44.025, 56.1263, -44.025),
          (56.1263, -44.025, 55.377, -44.025)),
    ("track", SWS, B, 0.3, [(55.377, -44.025), (55.65, -44.3), (56.45, -44.3)], FG),
    *dels("Net-(Q21-G)", B, "5.1 track to R56 0.97 mm above Q21 pin 2 (420V)", (59.247, -44.025, 58.298, -44.025)),
    ("track", "Net-(Q21-G)", B, 0.3, [(58.3, -44.3), (59.522, -44.3)], FG),
    # 420V sense feed of the divider R23 - R34 - R39: the 5.1 track (0.15 mm, F.Cu, x 79.6) ran 0.4 ... 0.5 mm
    # past the vias of AD2 and ended in the air 6 mm from R23 (the connection was open already). Deleted, NOT
    # routed again: between the AD2 vias (x 80.3 ... 80.5) and the 4.2 mm keep-off of mounting hole H5 there is
    # no 1.2 mm path on F.Cu, no via site at R23 (R113 on the bottom side) and 1.25 mm on In2 - README "Stage 3c",
    # open point 1 (divider re-placement). Tried: R23.1 -> pour, F / B / In2, window 8 mm: no route.
    *dels("420V", F, "5.1 420V sense track 0.4 ... 0.5 mm from the AD2 vias, dangling at R23",
          (79.6, -31.8, 79.6, -45.9), (79.6, -45.9, 79.5, -45.9)),
    # high-side gate track 1.18 mm from DRV6 pin 6 (dead-time pin): 0.7 mm wide
    *dels("DHB_HI_GATE_SEC", B, "5.1 gate track 1.18 mm from DRV6 pin 6; drawn again 0.7 mm wide",
          (63.093, -54.693, 62.3, -53.9)),
    ("track", "DHB_HI_GATE_SEC", B, 0.7, [(63.093, -54.693), (62.3, -53.9)], FG),
    # 15V_ISO_SEC 1.15 mm from R39 pin 1 (divider node)
    *dels("15V_ISO_SEC", F, "5.1 track 1.15 mm from the divider node at R39 pin 1; drawn again 0.45 mm wide",
          (74.99, -24.721, 75.244, -24.975), (75.244, -24.975, 75.244, -28.658)),
    # (not drawn again since stage 3d: the whole 5.1 track is a dead end and is deleted there, route_s3d_iso2.py)
]

# ------------------------------------------------------------------------------------------------ flyback secondary
FLY_SEC = [
    *dels("ISO_GND", F, DANGLE + " (TR1 pin 5, -100 V winding)", (70.6226, 0.834, 69.0986, 0.834),
          (68.0826, 0.834, 69.0986, 0.834)),
    *dels("-100V BIAS", F, DANGLE + " (D8 cathode)", (76.1535, 4.179, 77.2296, 4.179)),
]

# ------------------------------------------------------------------------------------------------ heater driver DRV3
HEATER = [
    ("delvia", HHS, -23.8, -58.0, "5.1 via of the old driver footprint, 0.12 mm from DRV3 pin 10 (low-side output)"),
    *dels("Net-(DRV3-VDDA)", B, DANGLE + " (DRV3 pin 10)", (-24.6, -56.8, -23.9, -56.1)),
    *dels(HHG, B, "5.1 stub at R24 (old gate route), 0.14 mm from R59", (-16.907, -63.583, -16.886, -63.583),
          (-16.907, -62.567, -16.907, -63.583), (-16.886, -63.583, -16.886, -63.4687),
          (-16.886, -63.4687, -16.907, -62.567)),
    # the 1.27 mm bootstrap-return track ended between DRV3 pins 14 / 15 (0.17 mm from pin 15): 0.6 mm shorter
    *dels(HHS, B, "5.1 track end 0.17 mm from DRV3 pin 15; drawn again 0.6 mm shorter",
          (-18.3, -61.1, -18.3, -67.3)),
    *dels(HHS, B, "5.1 stub of the old driver footprint between DRV3 pins 14 / 15", (-18.7264, -60.3, -18.7264, -59.9)),
    ("track", HHS, B, 1.27, [(-18.3, -67.3), (-18.3, -61.7)]),
    *dels("15V", B, DANGLE + " (D11 cathode / R99, bootstrap)", (-11.933, -53.677, -14.723, -53.677),
          (-11.933, -53.677, -12.954, -54.698), (-10.832, -60.3968, -10.3838, -60.3968),
          (-10.3838, -60.3968, -9.5708, -61.2098)),
]

# ------------------------------------------------------------------------------------------------ analog front ends
ANALOG = [
    # +3V3 / GND of U6's decoupling C62 0.36 / 1.09 mm from the DC+ pin of the bulk capacitor C37 (B.Cu). The
    # +3V3 link C76 - C62 has no legal path on B.Cu (0.8 mm between C37 pin 1 and C62 pin 2): both capacitors get a
    # via into the +3V3 pour on In3 instead; the GND tracks leave C62 pin 2 0.1 mm lower
    *dels("+3V3", B, "5.1 +3V3 track 0.36 mm from C37 pin 1 (DC+); C62 / C76 now by vias into the In3 +3V3 pour",
          (19.3, -1.8, 19.6, -1.8), (19.6, -1.8, 20.4, -2.6), (20.4, -2.6, 21.3, -2.6), (21.3, -2.6, 24.5, -5.8),
          (24.5, -5.8, 24.5, -8.6), (24.5, -8.7, 24.5, -8.6), (24.5, -9.3, 24.5, -8.7)),
    ("track", "+3V3", B, 0.2, [(19.3, -1.6), (19.58, -0.75)]),
    ("via", "+3V3", 19.58, -0.75, *VS),
    plane("+3V3", "C76.1"),
    *dels("GND", B, "5.1 GND track 1.09 mm from C37 pin 1 (DC+)", (20.3254, -1.2254, 20.9, -1.8),
          (20.9, -1.8, 23.4, -1.8)),
    ("track", "GND", B, 0.3, [(20.3254, -1.2254), (20.75, -1.55)]),
    ("track", "GND", B, 0.15, [(20.9, -1.7), (23.3, -1.7), (23.4, -1.8)]),
    *dels("GND", B, DANGLE + " (via of the DC-link divider node R10 pin 1)", (16.1, 2.7, 16.4, 3.0),
          (16.1, 1.3, 16.1, 2.7), (15.7, 0.9, 16.1, 1.3)),
    # +1V65_BIAS and +3V3 between the DC+ pin of the bulk capacitor C56 and C107 / R100 (0.46 / 0.81 mm)
    *dels("+1V65_BIAS", B, "5.1 +1V65_BIAS track 0.46 mm from C56 pin 1 (DC+)", (21.0084, -14.9564, 21.0084, -15.6084),
          (21.0084, -15.6084, 21.5, -16.1), (21.5, -16.1, 21.5, -17.4), (21.5, -17.4, 21.9, -17.8),
          (21.9, -17.8, 22.7, -17.8)),
    # (the +3V3 link U4 pin 8 -> via at (26.3, -19.3) has no other path on B.Cu or In2: deleted, both ends are on
    # the In3 +3V3 pour - U4 / C76 by the via above)
    *dels("+3V3", B, "5.1 +3V3 link 0.81 mm from C56 pin 1 (DC+); replaced by the In3 +3V3 pour",
          (23.749, -10.414, 21.844, -12.319), (21.844, -12.319, 21.844, -15.444), (21.844, -15.444, 21.844, -16.7),
          (21.844, -16.7, 22.144, -17.0), (22.144, -17.0, 23.4, -17.0), (23.4, -17.0, 25.2, -18.8),
          (25.2, -18.8, 26.8, -18.8), (24.62, -10.414, 23.749, -10.414)),
    # +1V65_BIAS C107 -> R60 / C106 / R100: round the west side of C56 pin 1 (through the GND pour), 1.2 mm from it
    ("auto", "+1V65_BIAS", "C107.1", "R60.1", dict(layers="B", w=0.2, via=VS, margin=3.0, zone_cost=2.0,
                                                    window=[(17.2, -19.8)], relax=("C107", "R60"))),
    # 15V (flyback -> DRV2) between the pads of R79, 0.16 ... 0.4 mm from the AC-sense divider nodes
    *dels("15V", B, "5.1 15V track 0.16 ... 0.4 mm from the AC-sense divider nodes (R79 pin 1, vias of R48 / R51)",
          (20.6, 14.8, 36.2, 14.8), (36.2, 14.8, 37.8, 13.2)),
    # (drawn since stage 3d - the grid router found this path first; the via of R79 pin 1 stands 1.25 mm from the
    # second via here, so its place must not depend on the state of the board)
    ("track", "15V", B, 0.4, [(20.6, 14.8), (21.2, 15.4), (21.2, 17.6), (21.3, 17.7), (30.5, 17.7), (32.1, 16.1),
                              (32.1, 15.5)]),
    ("via", "15V", 32.1, 15.5, *VS),
    ("track", "15V", I2, 0.4, [(32.1, 15.5), (33.5, 14.1), (36.9, 14.1)]),
    ("via", "15V", 36.9, 14.1, *VS),
    ("track", "15V", B, 0.4, [(36.9, 14.1), (37.7, 13.3)]),
    # 15V via 0.9 mm from C70 pin 1 (DC+, F.Cu): 0.8 mm further east on the same In2 / B.Cu tracks
    # EPWM5A (In2): the end of the kept track stood 0.025 mm from the HEATER_CURRENT via at (0.4, -56.1); it ends
    # where the stage-3e bundle round H4 turns south-east (x -1.848; 0.95 mm shorter until stage 3e)
    *dels("EPWM5A", I2, "5.1 track end 0.025 mm from the HEATER_CURRENT via; drawn again 0.95 mm shorter",
          (-13.547, -55.753, 0.347, -55.753)),
    ("track", "EPWM5A", I2, 0.1524, [(-13.547, -55.753), (-1.848, -55.753)]),      # (to the bundle of stage 3e)
    ("delvia", "15V", 26.841, -39.58, "5.1 15V via 0.9 mm from C70 pin 1 (DC+); moved 0.8 mm east"),
    ("via", "15V", 27.65, -39.58, 1.0, 0.4),
    ("track", "15V", B, 0.762, [(26.841, -39.58), (27.65, -39.58)]),
]

# ------------------------------------------------------------------------------------------------ dangling 5.1 copper
# Dangling tracks / vias of the 5.1 layout (ends that led to parts which moved or went) that no open connection
# starts on: not an end point of an unconnected item of the DRC and not within 0.3 mm of a start / end point of
# route_s3a_power.py / route_s3b_signals.py. List made from the board after stage 3b (kept: 70 dangling segments
# that are such anchors - the hand-drawn structures of the next stages start on them). Also kept: the escape of
# AD2 pin 4 (AD2-CLK: B.Cu stub, via, In2 stub) - the ratsnest starts on the pad, but it is the start of the 5.1
# route to ISO2 (ISO2 / AD2 fan-out, a later stage).
STUB = "dangling 5.1 track, no open connection starts on it"
VSTUB = "dangling 5.1 via (copper on one layer only), no open connection starts on it"
DANGLING = [
    *dels("+1V65_BIAS", I2, STUB, (4.5, -59.5, 5.2, -58.8)),
    *dels("/06 Heaters/HEATER_LOW_GATE", B, STUB, (-11.779, -75.321, -11.6, -75.5), (-11.0, -75.5, -11.6, -75.5)),
    *dels("15V", B, STUB, (10.8091, -36.233, 10.2151, -35.639)),
    *dels("15V", F, STUB, (49.463, -15.737, 49.463, -16.466)),
    *dels("15V", I2, STUB, (13.125, -51.0, 13.125, -57.8), (13.125, -57.8, 12.5, -58.425)),
    *dels("15V_ISO_SEC", I2, STUB, (66.689, -60.563, 66.689, -64.119), (77.475, -42.7931, 77.475, -50.502)),
    *dels("5V", I2, STUB, (17.159, -45.159, 17.159, -46.3)),
    *dels("5V_ISOL", B, STUB, (73.2628, -33.611, 72.958, -33.3062), (72.958, -33.3062, 72.958, -32.849)),
    *dels("5V_ISOL", I2, STUB, (78.745, -40.899, 78.745, -51.772), (73.8978, -34.5762, 73.8978, -35.2112),
          (77.426, -39.58, 78.745, -40.899), (75.9576, -39.58, 77.426, -39.58)),
    *dels("DC+", B, STUB, (2.784, -4.9858, 3.8, -4.98)),
    *dels("DHB_CURRENT", I2, STUB, (9.5, -51.9, 9.5, -56.5)),
    *dels("GND", B, STUB, (-10.225, -80.4, -10.225, -79.1)),
    *dels("GND", F, STUB, (49.7332, -4.8332, 49.7332, -3.5332), (60.766, -27.2356, 60.766, -27.515)),
    *dels("HT_GND", F, STUB, (-48.9, -57.1, -48.9, -58.6708), (-50.033, -55.967, -48.9, -57.1),
          (-50.033, -52.102, -50.033, -55.967)),
    *dels("Net-(AD1-VA)", F, STUB, (-49.9314, -50.4004, -48.509, -50.4004)),
    *dels("Net-(Q9-D)", B, STUB, (-53.5, -42.3564, -56.352, -39.5044), (-56.352, -39.5044, -56.352, -35.903)),
    *dels("Net-(U10A-+)", B, STUB, (37.9115, -0.0885, 35.83, 1.993)),
    *dels("PFC_PWM2", B, STUB, (12.2061, 14.9, 12.6061, 15.3), (12.6061, 15.3, 13.7, 15.3),
          (13.7, 15.3, 14.1, 14.9)),
    ("delvia", "GND", 60.766, -27.515, VSTUB),
    ("delvia", "Net-(C63-Pad1)", 5.75, -60.3, VSTUB),
    ("delvia", "15V_ISO_SEC", 77.475, -42.7931, VSTUB),
    ("delvia", "AD2_3V3", 73.9, -30.9, VSTUB),
    ("delvia", "5V_ISOL", 73.2628, -33.611, VSTUB),
    ("delvia", "5V_ISOL", 73.8978, -35.2112, VSTUB),
    ("delvia", "5V", 17.159, -46.3, VSTUB),
    ("delvia", "Net-(AD1-VA)", -48.509, -50.4004, VSTUB),
]

GROUPS = [("DAB primary", DAB_PRI), ("DAB secondary", DAB_SEC), ("flyback secondary", FLY_SEC),
          ("heater driver", HEATER), ("analog front ends", ANALOG), ("dangling 5.1 copper", DANGLING)]

if __name__ == "__main__":
    R.RELAX_OWN_DOMAIN = True
    R.HARD_ZONES = True
    R.run("s3c", GROUPS, sys.argv[1:])
