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

# (symbol, conditions, footprint, note). Conditions: n = pad count, tht, span (mm, +-0.02),
# pad = (w, h) of the IPC pads, drill, package / device (lib/part_map.csv columns).
RULES = [
    # --- resistors
    ("R", dict(tht=False, span=1.73, pad=(0.889, 0.889)), "Resistor_SMD:R_0603_1608Metric", "0603 (Proteus pads 1.73 mm apart)"),
    ("R", dict(tht=False, span=1.60, pad=(0.939, 0.99)), "Resistor_SMD:R_0603_1608Metric", "0603"),
    ("R", dict(tht=False, span=2.00, pad=(0.939, 1.447)), "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder", "0805"),
    ("R", dict(tht=False, span=2.13, pad=(1.016, 1.27)), "tube_psu:R_0805_2012Metric_Proteus2.13", "0805 (Proteus pads 2.13 mm apart)"),
    ("R", dict(tht=False, span=2.90, pad=(1.143, 1.803)), "Resistor_SMD:R_1206_3216Metric", "1206"),
    ("R", dict(tht=False, span=0.975, pad=(0.35, 2.0)), "tube_psu:R_0508_1220Metric_KRL2012", "KRL2012 0508 shunt, long-side terminals"),
    ("R", dict(tht=True, span=5.00, pad=(1.524, 1.524)), "Resistor_THT:R_Radial_Power_L13.0mm_W9.0mm_P5.00mm", "TWW10 10 W wirewound, vertical"),
    # --- capacitors
    ("C", dict(tht=False, span=1.60, pad=(0.939, 0.99)), "Capacitor_SMD:C_0603_1608Metric", "0603"),
    ("C", dict(tht=False, span=3.00, pad=(1.143, 1.803)), "Capacitor_SMD:C_1206_3216Metric", "1206 (3.0 mm pad spacing)"),
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
    ("C_Polarized", dict(tht=True, span=5.00, drill=1.016), "Capacitor_THT:CP_Radial_D12.5mm_P5.00mm", "12.5 mm radial electrolytic, P5"),
    ("C_Polarized", dict(tht=True, span=3.50), "Capacitor_THT:CP_Radial_D8.0mm_P3.50mm", "8 mm radial electrolytic, P3.5"),
    ("C_Polarized", dict(tht=False, span=4.50), "tube_psu:CP_Elec_6.3x7.7_EEEFTE221XAP", "EEEFTE221XAP SMD electrolytic, Proteus pads"),
    # --- diodes
    ("D", dict(span=4.10), "tube_psu:D_SMA_AC", "SMA (ES1A, S1M), pads A/C"),
    ("D_Schottky", dict(span=2.60), "tube_psu:D_SOD-323_AC", "SOD-323 (ZLLS400TA), pads A/C"),
    ("C3D02060A", dict(), "tube_psu:TO-220-2_Vertical_AK", "TO-220-2, pads A/K"),
    ("TBS22K", dict(), "tube_psu:D_Bridge_TBS", "TBS SMD bridge, Proteus land pattern"),
    # --- transistors
    ("ADR380", dict(), "tube_psu:SOT-23_Proteus", "SOT-23, Proteus pad numbering (REF1 ISL21010)"),
    ("Q_NMOS_DGS", dict(), "tube_psu:SOT-23_Proteus", "SOT-23, Proteus pad numbering (Q9 2N7000)"),
    ("Q_NMOS_SGD", dict(), "tube_psu:LFPAK56_Proteus", "LFPAK56, three source pads numbered 1, 2 = G, 3 = D tab"),
    ("Q_NMOS_GDS", dict(span=5.08), "Package_TO_SOT_THT:TO-220-3_Vertical", "TO-220(F), 1=G 2=D 3=S"),
    ("Q_NMOS_GDS", dict(span=10.92), "Package_TO_SOT_THT:TO-247-3_Vertical", "TO-247, 1=G 2=D 3=S (KiCad pitch 5.45, Proteus 5.461)"),
    # --- ICs
    ("TLV316IDBVR", dict(), "tube_psu:SOT-23-5_Proteus", "SOT-23-5, Proteus pad rows 2.39 mm apart"),
    ("TPS73033", dict(), "tube_psu:SOT-23-5_Proteus", "SOT-23-5, Proteus pad rows 2.39 mm apart"),
    ("ADC121S101", dict(), "tube_psu:SOT-23-6_Proteus", "SOT-23-6, Proteus pad rows 2.39 mm apart"),
    ("LMH6658", dict(), "Package_SO:TSSOP-8_3x3mm_P0.65mm", "TSSOP-8 (device OPA2353UA; the pads are TSSOP, not SO-8)"),
    ("SI8271", dict(), "tube_psu:SOIC-8_3.9x4.9mm_P1.27mm_Proteus", "SOIC-8, Proteus pad rows 5.5 mm apart"),
    ("SI8274", dict(), "tube_psu:SOIC-16_3.9x9.9mm_P1.27mm_Proteus", "SOIC-16, Proteus pad rows 5.4 mm apart"),
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
    ("HEADER_2X25_50MIL", dict(), "Connector_PinHeader_1.27mm:PinHeader_2x25_P1.27mm_Vertical", "2x25 1.27 mm header"),
    ("CONN_01X03", dict(), "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical", "1x3 2.54 mm (FCI 66226-003)"),
    ("PIN", dict(n=2), "tube_psu:Terminal_2x1_P5.00mm_D2.0mm_Drill1.4mm", "blade terminal, two holes both pad 1"),
]

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
    "D_Bridge_TBS": dict(ipc="DB1", descr="Taiwan Semiconductor TBS bridge rectifier (SMD, pads 1-4)"),
    # SOT-23 with Proteus pad numbering: pad 1 sits alone on one side (JEDEC pin 3), pads 2 and 3 are
    # JEDEC pins 1 and 2 (chirality verified by the fit on the bottom-side parts REF1 / Q9)
    "SOT-23_Proteus": dict(base="Package_TO_SOT_SMD:SOT-23", renumber={"3": "1", "1": "2", "2": "3"}, ipc="REF1",
                           descr="SOT-23 with Proteus pad numbering: pad 1 = JEDEC pin 3 (single side), "
                                 "pad 2 = JEDEC pin 1, pad 3 = JEDEC pin 2; Proteus pad positions"),
    "LFPAK56_Proteus": dict(base="Package_TO_SOT_SMD:LFPAK56", renumber={"1": "1", "2": "1", "3": "1", "4": "2", "5": "3"},
                            ipc="Q1", descr="LFPAK56 (BUK9Y15-60E): source pads 1,2,3 all numbered 1, gate 4 -> 2, "
                                           "drain tab 5 -> 3; Proteus pad positions"),
    "SOT-23-5_Proteus": dict(base="Package_TO_SOT_SMD:SOT-23-5", ipc="U2",
                             descr="SOT-23-5, Proteus pad positions (rows 2.39 mm apart)"),
    "SOT-23-6_Proteus": dict(base="Package_TO_SOT_SMD:SOT-23-6", ipc="AD1",
                             descr="SOT-23-6, Proteus pad positions (rows 2.39 mm apart)"),
    "SOIC-8_3.9x4.9mm_P1.27mm_Proteus": dict(base="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", ipc="DRV3",
                                             descr="SOIC-8, Proteus pad positions (rows 5.5 mm apart)"),
    "SOIC-16_3.9x9.9mm_P1.27mm_Proteus": dict(base="Package_SO:SOIC-16_3.9x9.9mm_P1.27mm", ipc="DRV5",
                                              descr="SOIC-16, Proteus pad positions (rows 5.4 mm apart)"),
    "SOIC-16W_7.5x10.3mm_P1.27mm_Proteus": dict(base="Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm", ipc="ISO1",
                                                descr="SOIC-16W, Proteus pad positions (rows 9.4 mm apart)"),
    "DFN-8-1EP_P0.95mm_IXDD60xD2": dict(ipc="DRV4", descr="IXYS IXDD604/609 D2 package: 8 pads 0.45 x 1.2 at 0.95 mm pitch, "
                                                           "rows 4.5 mm apart, thermal pad 9 (2.6 x 3.1)"),
    "Transformer_EF20_2x5_P3.81mm": dict(ipc="TR1", body=(14.0, 22.0), descr="EF20 auxiliary transformer, pads 1-10"),
    "Transformer_EF25_2x5_P5.08mm_8pin": dict(ipc="TR2", body=(17.0, 28.0),
                                              descr="EF25 heater transformer, pads 1,2,4,5,6,7,9,10 (body from the Proteus silk)"),
    "Transformer_ETD34_4x3pads": dict(ipc="TR3", descr="ETD34 transformer, pins 1-4 with three 2.5 mm pads each"),
    "L_RM8_Proteus": dict(ipc="L1", rotate=45.0,
                          descr="RM8 PFC choke: winding pads pri1/pri2 (2.54 mm), bobbin pins 1/2 (1.905 mm, no net); "
                                "footprint frame rotated 45 deg against the board"),
    "L_CommonMode_SCF20-05-550": dict(ipc="CM1", body=(15.0, 25.0), descr="Common-mode choke SCF20-05-550 (VAC T60405-R6131-X204), "
                                                                           "4 pins (body from the Proteus silk)"),
    "Relay_Songle_SRD_5pin": dict(ipc="RL1", descr="Songle relay, pads 1-5"),
    "Terminal_2x1_P5.00mm_D2.0mm_Drill1.4mm": dict(ipc="GND", descr="Blade wire terminal, two holes both pad 1"),
}


if __name__ == "__main__":
    footprints.run(RULES, PROJECT)
