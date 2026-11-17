#!/usr/bin/env python3
"""Footprint assignment and the project footprint library of tube_psu (stdlib only).

Writes (through the shared generator tools/p2k/p2k/footprints.py)
  lib/footprint_map.csv   refdes -> footprint for all 315 parts
  lib/tube_psu.pretty/    project footprints: derived from KiCad library footprints (pads
                          renumbered to the Proteus ids, pad centres moved onto the Proteus
                          positions) or built from the IPC-D-356A pads where KiCad has nothing

Usage: python3 tools/gen_footprints.py [--check]      (needs the KiCad AppImage mount)

This file holds what is decided for this board: RULES (symbol + IPC pad pattern -> footprint)
and PROJECT (the project footprint specs); the rule syntax and the spec keys are documented in
tools/p2k/p2k/footprints.py. Pad numbers always equal the IPC pin ids.

Pad sizes: p2k_config.py FOOTPRINT_PAD_SIZES ("kicad", the default chosen in Phase 2; "proteus"
switches every footprint to the Proteus pad sizes and drills). Two specs carry `ipc_sizes`
regardless of that key because the KiCad pads do not work on this board's pattern (see the
comments at the specs). tools/p2k check_footprints verifies every footprint against the IPC
pads (residual < 0.05 mm per pad) and reports the pad size / drill differences.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "p2k"))  # proteus2kicad
from p2k import footprints  # noqa: E402

# Phase 5 user decision (STATUS.md "Phase 5"): the Proteus pad sizes only on the parts whose KiCad
# pads collide with the Proteus copper (DRC with KiCad pads: short / clearance < 0.15 mm / solder-mask
# bridge / hole clearance; STATUS.md "Phase 4" per-refdes table). Every other part has the KiCad pads.
# The rules with `refdes=PROTEUS_PADS` come first; a refdes listed here must be taken by such a rule.
# U8 (not a DRC conflict) added in Phase 5: with KiCad's SOT-23-5 pads the zone fill loses 0.45 mm^2
# of Proteus copper (net #00372 beside U8-5, B.Cu; gerber round trip 'other' cluster, 3 tracks uncovered).
PROTEUS_PADS = frozenset("""
    U2 U3 U6 V2 V3 V4 AD1 AD2 Q9 REF1 DRV3 DRV5 C28 C37 C56 J2 R40 R79 R88 R109 C25 C92
    U8
""".split())

# (symbol, conditions, footprint, note). Conditions: n = pad count, tht, span (mm, +-0.02),
# pad = (w, h) of the IPC pads, drill, package / device (lib/part_map.csv columns), refdes.
RULES = [
    # --- resistors
    ("R", dict(tht=False, span=1.73, pad=(0.889, 0.889), refdes=PROTEUS_PADS), "tube_psu:R_0603_1608Metric_Proteus1.73",
     "0603 (Proteus pads 1.73 mm apart), Proteus pad size"),
    ("R", dict(tht=False, span=1.73, pad=(0.889, 0.889)), "Resistor_SMD:R_0603_1608Metric", "0603 (Proteus pads 1.73 mm apart)"),
    ("R", dict(tht=False, span=1.60, pad=(0.939, 0.99)), "Resistor_SMD:R_0603_1608Metric", "0603"),
    ("R", dict(tht=False, span=2.00, pad=(0.939, 1.447), refdes=PROTEUS_PADS), "tube_psu:R_0805_2012Metric_Proteus",
     "0805, Proteus pad size"),
    ("R", dict(tht=False, span=2.00, pad=(0.939, 1.447)), "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder", "0805"),
    ("R", dict(tht=False, span=2.13, pad=(1.016, 1.27)), "tube_psu:R_0805_2012Metric_Proteus2.13", "0805 (Proteus pads 2.13 mm apart)"),
    ("R", dict(tht=False, span=2.90, pad=(1.143, 1.803)), "Resistor_SMD:R_1206_3216Metric", "1206"),
    ("R", dict(tht=False, span=0.975, pad=(0.35, 2.0)), "tube_psu:R_0508_1220Metric_KRL2012", "KRL2012 0508 shunt, long-side terminals"),
    ("R", dict(tht=True, span=5.00, pad=(1.524, 1.524)), "Resistor_THT:R_Radial_Power_L13.0mm_W9.0mm_P5.00mm", "TWW10 10 W wirewound, vertical"),
    # --- capacitors
    ("C", dict(tht=False, span=1.60, pad=(0.939, 0.99)), "Capacitor_SMD:C_0603_1608Metric", "0603"),
    ("C", dict(tht=False, span=3.00, pad=(1.143, 1.803)), "Capacitor_SMD:C_1206_3216Metric", "1206 (3.0 mm pad spacing)"),
    ("C", dict(tht=False, span=3.15, pad=(1.016, 1.524), refdes=PROTEUS_PADS), "tube_psu:C_1206_3216Metric_Proteus3.15",
     "1206, Proteus pad size"),
    ("C", dict(tht=False, span=3.15, pad=(1.016, 1.524)), "Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder", "1206"),
    ("C", dict(tht=False, span=5.20, pad=(1.397, 5.257)), "Capacitor_SMD:C_2220_5750Metric_Pad1.97x5.40mm_HandSolder", "2220"),
    ("C", dict(tht=True, span=7.50, pad=(1.524, 1.524)), "Capacitor_THT:C_Disc_D12.5mm_W5.0mm_P7.50mm", "Y2 2n2 disc (DEBB), P7.5"),
    ("C", dict(tht=True, span=10.00, pad=(1.778, 1.778)), "Capacitor_THT:C_Rect_L13.0mm_W5.0mm_P10.00mm_FKS3_FKP3_MKS4",
     "Kemet R46 X2 film P10 (WCAP-FTXX package)"),
    ("C", dict(tht=True, span=22.50, package="11X15 X2 CAP 22.5MM RASTER"), "Capacitor_THT:C_Rect_L26.5mm_W11.5mm_P22.50mm_MKS4",
     "X2 film P22.5, 11 mm wide"),
    ("C", dict(tht=True, span=22.50, package="X2 W6MM CAP 22.5MM RASTER"), "Capacitor_THT:C_Rect_L26.5mm_W6.0mm_P22.50mm_MKS4",
     "X2 film P22.5, 6 mm wide"),
    ("C_Polarized", dict(tht=True, span=5.00, drill=0.812), "Capacitor_THT:CP_Radial_D10.0mm_P5.00mm", "10 mm radial electrolytic, P5"),
    ("C_Polarized", dict(tht=True, span=5.00, drill=1.016, refdes=PROTEUS_PADS), "tube_psu:CP_Radial_D12.5mm_P5.00mm_Proteus",
     "12.5 mm radial electrolytic, P5, Proteus pad size"),
    ("C_Polarized", dict(tht=True, span=5.00, drill=1.016), "Capacitor_THT:CP_Radial_D12.5mm_P5.00mm", "12.5 mm radial electrolytic, P5"),
    ("C_Polarized", dict(tht=True, span=3.50), "Capacitor_THT:CP_Radial_D8.0mm_P3.50mm", "8 mm radial electrolytic, P3.5"),
    ("C_Polarized", dict(tht=False, span=4.50), "tube_psu:CP_Elec_6.3x7.7_EEEFTE221XAP", "EEEFTE221XAP SMD electrolytic, Proteus pads"),
    # --- diodes
    ("D", dict(span=4.10), "tube_psu:D_SMA_AC", "SMA (ES1A, S1M), pads A/C"),
    ("D_Schottky", dict(span=2.60), "tube_psu:D_SOD-323_AC", "SOD-323 (ZLLS400TA), pads A/C"),
    ("C3D02060A", dict(), "tube_psu:TO-220-2_Vertical_AK", "TO-220-2, pads A/K"),
    ("TBS22K", dict(), "tube_psu:D_Bridge_TBS", "TBS SMD bridge, Proteus land pattern"),
    # --- transistors
    ("ADR380", dict(refdes=PROTEUS_PADS), "tube_psu:SOT-23_Proteus", "SOT-23, Proteus pad numbering (REF1 ISL21010)"),
    ("Q_NMOS_DGS", dict(refdes=PROTEUS_PADS), "tube_psu:SOT-23_Proteus", "SOT-23, Proteus pad numbering (Q9 2N7000)"),
    ("Q_NMOS_SGD", dict(), "tube_psu:LFPAK56_Proteus", "LFPAK56, three source pads numbered 1, 2 = G, 3 = D tab"),
    ("Q_NMOS_GDS", dict(span=5.08), "Package_TO_SOT_THT:TO-220-3_Vertical", "TO-220(F), 1=G 2=D 3=S"),
    ("Q_NMOS_GDS", dict(span=10.92), "Package_TO_SOT_THT:TO-247-3_Vertical", "TO-247, 1=G 2=D 3=S (KiCad pitch 5.45, Proteus 5.461)"),
    # --- ICs
    ("TLV316IDBVR", dict(refdes=PROTEUS_PADS), "tube_psu:SOT-23-5_Proteus", "SOT-23-5, Proteus pad rows 2.39 mm apart, Proteus pad size"),
    ("TPS73033", dict(refdes=PROTEUS_PADS), "tube_psu:SOT-23-5_Proteus", "SOT-23-5, Proteus pad rows 2.39 mm apart, Proteus pad size"),
    ("ADC121S101", dict(refdes=PROTEUS_PADS), "tube_psu:SOT-23-6_Proteus", "SOT-23-6, Proteus pad rows 2.39 mm apart"),
    ("LMH6658", dict(), "Package_SO:TSSOP-8_3x3mm_P0.65mm", "TSSOP-8 (device OPA2353UA; the pads are TSSOP, not SO-8)"),
    ("SI8271", dict(refdes=PROTEUS_PADS), "tube_psu:SOIC-8_3.9x4.9mm_P1.27mm_Proteus", "SOIC-8, Proteus pad rows 5.5 mm apart"),
    ("SI8275", dict(refdes=PROTEUS_PADS), "tube_psu:SOIC-16_3.9x9.9mm_P1.27mm_Proteus", "SOIC-16, Proteus pad rows 5.4 mm apart, Proteus pad size"),
    ("SI8275", dict(), "tube_psu:SOIC-16_3.9x9.9mm_P1.27mm_Proteus_KiCadPads", "SOIC-16, Proteus pad rows 5.4 mm apart"),
    ("SI8661", dict(), "tube_psu:SOIC-16W_7.5x10.3mm_P1.27mm_Proteus", "SOIC-16W, Proteus pad rows 9.4 mm apart"),
    ("IXDD604", dict(), "tube_psu:DFN-8-1EP_P0.95mm_IXDD60xD2", "IXYS D2 DFN-8 with thermal pad 9, Proteus land pattern"),
    ("IXDD609", dict(), "tube_psu:DFN-8-1EP_P0.95mm_IXDD60xD2", "IXYS D2 DFN-8 with thermal pad 9, Proteus land pattern"),
    ("IW1818", dict(), "Package_DIP:DIP-8-N6_W7.62mm", "DIP-8 without pin 6"),
    # --- magnetics, relay, connectors, terminals
    ("EF20", dict(), "tube_psu:Transformer_EF20_2x5_P3.81mm", "EF20, pads 1-10"),
    ("EF25_8PIN", dict(), "tube_psu:Transformer_EF25_2x5_P5.08mm_8pin", "EF25, pads 1,2,4,5,6,7,9,10"),
    ("ETD34_TRAN_1P1S", dict(), "tube_psu:Transformer_ETD34_4x3pads", "ETD34, pins 1-4 with three pads each"),
    ("RM8_INDUCTOR", dict(), "tube_psu:L_RM8_Proteus", "RM8 choke: winding pads pri1/pri2, bobbin pins 1/2 (no net); 45 deg on the board"),
    ("SCF20-05-550", dict(), "tube_psu:L_CommonMode_SCF20-05-550", "common-mode choke, 4 pins"),
    ("SONGLE_RELAY", dict(), "tube_psu:Relay_Songle_SRD_5pin", "Songle relay, pads 1-5"),
    ("HEADER_2X25_50MIL", dict(refdes=PROTEUS_PADS), "tube_psu:PinHeader_2x25_P1.27mm_Vertical_Proteus", "2x25 1.27 mm header"),
    ("CONN_01X03", dict(), "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical", "1x3 2.54 mm (FCI 66226-003)"),
    ("PIN", dict(n=2), "tube_psu:Terminal_2x1_P5.00mm_D2.0mm_Drill1.4mm", "blade terminal, two holes both pad 1"),
]

# Footprint bodies from the Proteus silk screen (Phase 5 decision 3a): outline polygons in board
# coordinates of the spec's `ipc` part, measured and checked by tools/silk_bodies.py (do not edit by
# hand: run it and copy its output). Fab = outline, silk = outline with gaps at the pads, courtyard =
# convex hull of outline and pads + 0.25 mm.
SILK_BODY = {
    "L_RM8_Proteus": [(-12.992, -17.377), (-4.407, -17.341), (-0.869, -13.802), (-0.833, -5.253), (-8.484, 2.398), (-17.069, 2.362), (-20.572, -1.14), (-20.608, -9.725)],
    "Transformer_EF20_2x5_P3.81mm": [(56.658, -6.517), (70.628, -6.517), (70.628, 15.327), (56.658, 15.327)],
    "Transformer_EF25_2x5_P5.08mm_8pin": [(-38.7, 62.08), (-21.7, 62.08), (-21.7, 90.08), (-38.7, 90.08)],
    "Transformer_ETD34_4x3pads": [(35.25, 49.114), (62.25, 49.114), (62.25, 88.614), (35.25, 88.614)],
    "L_CommonMode_SCF20-05-550": [(-52.685, 3.695), (-37.685, 3.695), (-37.685, 28.695), (-52.685, 28.695)],
    "Relay_Songle_SRD_5pin": [(-70.308, 22.151), (-53.03, 22.151), (-53.03, 37.905), (-70.308, 37.905)],
    "D_Bridge_TBS": [(-0.85, 8.8), (7.75, 8.8), (7.75, 15.5), (-0.85, 15.5)],
}

# Project footprints (spec keys: see p2k.footprints). `ipc` = refdes whose IPC pads give the
# pad centres; the footprint is built for the top side and mirrored by placement when needed.
PROJECT = {
    "R_0805_2012Metric_Proteus2.13": dict(base="Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder", ipc="R63",
                                         descr="0805 resistor, Proteus pad centres 2.13 mm apart"),
    # KiCad's 0508 pads (0.95 wide, 1.15 apart) would be 0.025 mm apart at the Proteus centres: the
    # Proteus pads (0.35 x 2.0) are the only ones that work here -> ipc_sizes regardless of the mode
    "R_0508_1220Metric_KRL2012": dict(base="Resistor_SMD:R_0508_1220Metric", ipc="R21", ipc_sizes=True,
                                      descr="KRL2012 0508 shunt resistor (long-side terminals), Proteus land pattern"),
    # Proteus pads are 0.65 x 2.7 strips; KiCad's 3.5 x 1.6 pads do not resemble them (as on ac_psu)
    "CP_Elec_6.3x7.7_EEEFTE221XAP": dict(base="Capacitor_SMD:CP_Elec_6.3x7.7", ipc="C1", ipc_sizes=True,
                                         descr="Panasonic EEE-FTE221XAP, Proteus land pattern"),
    "D_SMA_AC": dict(base="Diode_SMD:D_SMA", renumber={"1": "C", "2": "A"}, ipc="D4",
                     descr="SMA diode, pads C/A, Proteus pad positions"),
    "D_SOD-323_AC": dict(base="Diode_SMD:D_SOD-323_HandSoldering", renumber={"1": "C", "2": "A"}, ipc="D10",
                         descr="SOD-323 diode, pads C/A, Proteus pad positions"),
    # C3D02060A TO-220-2: pin 1 = anode, pin 2 = cathode (tab). The two-pad pattern is symmetric, so
    # the geometry cannot confirm the order; the nets come from the IPC either way.
    "TO-220-2_Vertical_AK": dict(base="Package_TO_SOT_THT:TO-220-2_Vertical", renumber={"1": "A", "2": "K"}, ipc="SICD1",
                                 descr="TO-220-2 diode, pads A (pin 1) / K (pin 2, tab), Proteus pad positions"),
    "D_Bridge_TBS": dict(ipc="DB1", body_poly=SILK_BODY["D_Bridge_TBS"],
                         descr="Taiwan Semiconductor TBS bridge rectifier (SMD, pads 1-4), body from the Proteus silk"),
    # Phase 3 DRC (STATUS.md "Phase 3 - pad sizes"), narrowed in Phase 5: ipc_sizes=True (Proteus pad
    # sizes) on the footprints of the PROTEUS_PADS parts, whose KiCad pads short or come closer than
    # 0.15 mm to Proteus tracks/vias; the other parts of these packages use the KiCad pads.
    "CP_Radial_D12.5mm_P5.00mm_Proteus": dict(base="Capacitor_THT:CP_Radial_D12.5mm_P5.00mm", ipc="C28", ipc_sizes=True,
                                              descr="12.5 mm radial electrolytic P5, Proteus pads (1.524 mm, drill 1.016)"),
    "R_0603_1608Metric_Proteus1.73": dict(base="Resistor_SMD:R_0603_1608Metric", ipc="R40", ipc_sizes=True,
                                          descr="0603 resistor, Proteus pads 0.889 x 0.889, 1.73 mm apart"),
    "R_0805_2012Metric_Proteus": dict(base="Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder", ipc="R79", ipc_sizes=True,
                                      descr="0805 resistor, Proteus pads 0.94 x 1.448, 2.0 mm apart"),
    "C_1206_3216Metric_Proteus3.15": dict(base="Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder", ipc="C25",
                                          ipc_sizes=True, descr="1206 capacitor, Proteus pads 1.016 x 1.524, 3.15 mm apart"),
    "PinHeader_2x25_P1.27mm_Vertical_Proteus": dict(base="Connector_PinHeader_1.27mm:PinHeader_2x25_P1.27mm_Vertical", ipc="J2",
                                                    ipc_sizes=True, descr="2x25 1.27 mm header, Proteus pads 0.812 mm, drill 0.5"),
    # SOT-23 with Proteus pad numbering: pad 1 sits alone on one side (JEDEC pin 3), pads 2 and 3 are
    # JEDEC pins 1 and 2 (chirality verified by the fit on the bottom-side parts REF1 / Q9)
    "SOT-23_Proteus": dict(base="Package_TO_SOT_SMD:SOT-23", renumber={"3": "1", "1": "2", "2": "3"}, ipc="REF1",
                           ipc_sizes=True, descr="SOT-23 with Proteus pad numbering: pad 1 = JEDEC pin 3 (single side), "
                                 "pad 2 = JEDEC pin 1, pad 3 = JEDEC pin 2; Proteus pad positions"),
    "LFPAK56_Proteus": dict(base="Package_TO_SOT_SMD:LFPAK56", renumber={"1": "1", "2": "1", "3": "1", "4": "2", "5": "3"},
                            ipc="Q1", descr="LFPAK56 (BUK9Y15-60E): source pads 1,2,3 all numbered 1, gate 4 -> 2, "
                                           "drain tab 5 -> 3; Proteus pad positions"),
    "SOT-23-5_Proteus": dict(base="Package_TO_SOT_SMD:SOT-23-5", ipc="U2", ipc_sizes=True,
                             descr="SOT-23-5, Proteus pad positions (rows 2.39 mm apart)"),
    "SOT-23-6_Proteus": dict(base="Package_TO_SOT_SMD:SOT-23-6", ipc="AD1", ipc_sizes=True,
                             descr="SOT-23-6, Proteus pad positions (rows 2.39 mm apart)"),
    "SOIC-8_3.9x4.9mm_P1.27mm_Proteus": dict(base="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", ipc="DRV3", ipc_sizes=True,
                                             descr="SOIC-8, Proteus pad positions (rows 5.5 mm apart)"),
    "SOIC-16_3.9x9.9mm_P1.27mm_Proteus": dict(base="Package_SO:SOIC-16_3.9x9.9mm_P1.27mm", ipc="DRV5", ipc_sizes=True,
                                              descr="SOIC-16, Proteus pad positions (rows 5.4 mm apart)"),
    "SOIC-16_3.9x9.9mm_P1.27mm_Proteus_KiCadPads": dict(base="Package_SO:SOIC-16_3.9x9.9mm_P1.27mm", ipc="DRV6",
                                                        descr="SOIC-16, Proteus pad positions (rows 5.4 mm apart), "
                                                              "KiCad pad size"),
    "SOIC-16W_7.5x10.3mm_P1.27mm_Proteus": dict(base="Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm", ipc="ISO1",
                                                descr="SOIC-16W, Proteus pad positions (rows 9.4 mm apart)"),
    "DFN-8-1EP_P0.95mm_IXDD60xD2": dict(ipc="DRV4", descr="IXYS IXDD604/609 D2 package: 8 pads 0.45 x 1.2 at 0.95 mm pitch, "
                                                           "rows 4.5 mm apart, thermal pad 9 (2.6 x 3.1)"),
    "Transformer_EF20_2x5_P3.81mm": dict(ipc="TR1", body_poly=SILK_BODY["Transformer_EF20_2x5_P3.81mm"],
                                         descr="EF20 auxiliary transformer, pads 1-10 (body from the Proteus silk)"),
    "Transformer_EF25_2x5_P5.08mm_8pin": dict(ipc="TR2", body_poly=SILK_BODY["Transformer_EF25_2x5_P5.08mm_8pin"],
                                              descr="EF25 heater transformer, pads 1,2,4,5,6,7,9,10 (body from the Proteus silk)"),
    "Transformer_ETD34_4x3pads": dict(ipc="TR3", body_poly=SILK_BODY["Transformer_ETD34_4x3pads"],
                                      descr="ETD34 transformer, pins 1-4 with three 2.5 mm pads each (body from the Proteus silk)"),
    "L_RM8_Proteus": dict(ipc="L1", rotate=45.0, body_poly=SILK_BODY["L_RM8_Proteus"],
                          descr="RM8 PFC choke: winding pads pri1/pri2 (2.54 mm), bobbin pins 1/2 (1.905 mm, no net); "
                                "footprint frame rotated 45 deg against the board"),
    "L_CommonMode_SCF20-05-550": dict(ipc="CM1", body_poly=SILK_BODY["L_CommonMode_SCF20-05-550"],
                                      descr="Common-mode choke SCF20-05-550 (VAC T60405-R6131-X204), "
                                            "4 pins (body from the Proteus silk)"),
    "Relay_Songle_SRD_5pin": dict(ipc="RL1", body_poly=SILK_BODY["Relay_Songle_SRD_5pin"],
                                  descr="Songle relay, pads 1-5 (body from the Proteus silk)"),
    "Terminal_2x1_P5.00mm_D2.0mm_Drill1.4mm": dict(ipc="GND", descr="Blade wire terminal, two holes both pad 1"),
    # Board-only items (no symbol; placed by p2k.build_pcb at the IPC 'hole' / 'free_pad' records)
    "MountingHole_3.0mm_NPTH_Ring3.5mm": dict(board_only=True, pad=(3.5, 3.0), plated=False,
                                              descr="Unplated 3.0 mm hole with a 3.5 mm copper ring on every layer, no net"),
    "WirePad_D4.0mm_Drill2.55mm": dict(board_only=True, pad=(4.0, 2.55), plated=True,
                                       descr="Plated 2.55 mm wire pad (transformer winding wire), 4.0 mm pad"),
}


if __name__ == "__main__":
    footprints.run(RULES, PROJECT)
