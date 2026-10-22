#!/usr/bin/env python3
"""Generate lib/tube_psu.kicad_sym, the project symbol library (helpers: p2k.symgen).

Pin numbers equal the Proteus/IPC pin ids; pin names of the box symbols are the Proteus
pin names from the device pinouts in ROOT.DSN (STATUS.md "Phase 1 preparation"). Simple
symbols are copied from the KiCad 10 standard library (flattened, pins renumbered).
Power symbols carry the IPC net names of the rails drawn as Proteus power terminals.

Run:  tools/gen_symbols.py           (needs the AppImage mount for the std libs)
      tools/gen_symbols.py --check   (fail if lib/tube_psu.kicad_sym is not up to date)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "p2k"))  # proteus2kicad
from p2k.symgen import *  # noqa: E402,F401,F403
from p2k.symgen import _pin, run  # noqa: E402

GROUNDS = ["GND", "ISO_GND", "HT_GND"]
SUPPLIES = ["DC+", "420V", "20V", "20V_ISO_SEC", "6V3", "5V", "5V_ISOL", "+3V3", "AD2_3V3",
            "+2V5_BIAS", "-5V_SEC", "-100V BIAS"]

NC = "no_connect"


def add_pins(sym, pins):
    """Append pins [(number, name, type, x, y, rot)] to the unit-1 body of a std symbol."""
    unit = next(s for s in find_all(sym, "symbol") if s[1].endswith("_1_1"))
    for num, name, etype, x, y, rot in pins:
        unit.append(_pin(num, name, etype, x, y, rot))
    return sym


def build():
    D_PINS = {"1": "C", "2": "A"}
    syms = [
        from_std("Device", "R", "R", "R", "R"),
        from_std("Device", "C", "C", "C", "C"),
        from_std("Device", "C_Polarized", "C_Polarized", "C", "C", desc="Polarized capacitor, pin 1 = +"),
        from_std("Device", "D", "D", "D", desc="Diode, pins A/C as in Proteus", pins=D_PINS),
        from_std("Device", "D_Schottky", "D_Schottky", "D", desc="Schottky diode, pins A/C", pins=D_PINS),
        from_std("Device", "D_Schottky", "C3D02060A", "SICD", desc="SiC Schottky diode TO-220-2, pins A/K",
                 pins={"1": "K", "2": "A"}),
        add_pins(from_std("Device", "L", "RM8_INDUCTOR", "L", desc="PFC choke on RM8 core: winding pri1-pri2; "
                          "pins 1 and 2 are unconnected bobbin pins (no net in Proteus)",
                          pins={"1": "pri1", "2": "pri2"}),
                 [("1", "NC", NC, 5.08, 1.27, 180), ("2", "NC", NC, 5.08, -1.27, 180)]),
        from_std("Device", "Q_NMOS", "Q_NMOS_GDS", "Q", desc="N-MOSFET TO-220/TO-247, Proteus ids 1=G 2=D 3=S",
                 pins={"G": "1", "D": "2", "S": "3"}, names={"1": "G", "2": "D", "3": "S"}),
        from_std("Device", "Q_NMOS", "Q_NMOS_SGD", "Q", desc="N-MOSFET LFPAK (BUK9Y15-60E), Proteus ids 1=S 2=G 3=D",
                 pins={"S": "1", "G": "2", "D": "3"}, names={"1": "S", "2": "G", "3": "D"}),
        from_std("Device", "Q_NMOS", "Q_NMOS_DGS", "Q", desc="N-MOSFET SOT-23 (BSS138/2N7000), Proteus ids 1=D 2=G 3=S",
                 pins={"D": "1", "G": "2", "S": "3"}, names={"1": "D", "2": "G", "3": "S"}),
        from_std("Device", "D_Bridge_+A-A", "TBS22K", "DB", desc="Bridge rectifier, Proteus ids 1=AC1 2=+ 3=AC2 4=DC-",
                 pins={"1": "2", "2": "1", "3": "4", "4": "3"}, names={"1": "AC1", "2": "+", "3": "AC2", "4": "-"}),
        from_std("Device", "Transformer_1P_1S", "SCF20-05-550", "CM",
                 desc="Common-mode choke, windings P1(3)-P2(4) and S1(1)-S2(2) (Proteus ids)",
                 pins={"1": "3", "2": "4", "3": "1", "4": "2"}, names={"3": "P1", "4": "P2", "1": "S1", "2": "S2"}),
        from_std("Device", "Transformer_1P_1S", "ETD34_TRAN_1P1S", "TR", desc="DHB transformer ETD34, P1=1 P2=2 S1=3 S2=4",
                 pins={"1": "1", "2": "2", "3": "3", "4": "4"}, names={"1": "P1", "2": "P2", "3": "S1", "4": "S2"}),
        from_std("Connector", "TestPoint", "PIN", "TP", "PIN",
                 desc="Proteus PIN terminal (blade connector: footprint has two pads numbered 1)"),
        from_std("Connector_Generic", "Conn_01x03", "CONN_01X03", "J", desc="3-pin connector (66226-003)"),
        from_std("Amplifier_Operational", "MCP6L91T-EOT", "TLV316IDBVR", "U",
                 desc="Op-amp SOT-23-5, Proteus 1=OP 2=V- 3=+IN 4=-IN 5=V+"),
        from_std("Amplifier_Operational", "LM2904", "LMH6658", "U",
                 desc="Dual op-amp TSSOP-8 (Proteus device OPA2353UA), standard dual pinout"),
    ]

    syms += [
        box("TPS73033", "V", [(1, "VIN", PI), (2, "GND", PI), (3, "EN", IN)], [(4, "NR", PAS), (5, "VOUT", PO), None],
            desc="LDO SOT-23-5 (TPS73033 / MIC5205), Proteus pin ids"),
        box("ADR380", "REF", [(2, "VIN", PI)], [(3, "VOUT", PO)], bottom=[(1, "GND", PI)],
            desc="Voltage reference SOT-23; Proteus pin ids 1=GND 2=VIN 3=VOUT (ADR380 datasheet: 1=VIN 2=VOUT 3=GND)"),
        box("ADC121S101", "AD", [(1, "VA", PI), (2, "GND", PI), (3, "Vin", IN)],
            [(6, "CS", IN), (5, "SDATA", OUT), (4, "CLK", IN)], desc="12-bit ADC SOT-23-6"),
        box("IXDD604", "DRV", [(6, "VCC", PI), (1, "ENA", IN), (2, "INA", IN), (3, "INB", IN), (4, "ENB", IN)],
            [(8, "OUTA", OUT), (5, "OUTB", OUT), None, (7, "GND", PI), (9, "TAB", PAS)],
            desc="Dual 4 A gate driver DFN-8 with thermal pad"),
        box("IXDD609", "DRV", [(1, "VCC", PI), (8, "VCC", PI), (2, "IN", IN), (3, "EN", IN)],
            [(7, "OUTA", OUT), (6, "OUTB", OUT), (4, "GND", PI), (5, "GND", PI), (9, "TAB", PAS)],
            desc="9 A gate driver DFN-8 with thermal pad"),
        box("IW1818", "PWM", [(5, "Vcc", PI), (4, "Vsense", IN), (2, "I_sense", IN), (1, "E", PAS)],
            [(8, "C", PAS), (7, "C", PAS), None, (3, "GND", PI)],
            desc="Flyback controller with integrated switch, 7-pin (no pin 6)"),
        box("SI8271", "DRV", [(2, "VDD1", PI), (1, "Vin", IN), (4, "EN", IN), (3, "GND1", PI)],
            [(8, "VDD2", PI), (7, "OUT+", OUT), (6, "OUT-", OUT), (5, "GND2", PI)],
            desc="Isolated single gate driver SOIC-8"),
        box("SI8274", "DRV", [(3, "VDD1", PI), (8, "VDD1", PI), (1, "PWM", IN), (5, "EN", IN), (6, "DT", IN),
                              (4, "GND1", PI), (2, "NC1", NC), (7, "NC2", NC)],
            [(16, "VDDA", PI), (15, "VOA", OUT), (14, "GNDA", PI), (13, "NC3", NC), (12, "NC4", NC),
             (11, "VDDB", PI), (10, "VOB", OUT), (9, "GNDB", PI)],
            desc="Isolated half-bridge gate driver SOIC-16"),
        box("SI8661", "ISO",
            [(1, "VDD1", PI), (2, "VI_A", IN), (3, "VI_B", IN), (4, "VI_C", IN), (5, "VI_D", IN),
             (6, "VO_E", OUT), (7, "VO_F", OUT), (8, "GND1", PI)],
            [(16, "VDD2", PI), (15, "VO_A", OUT), (14, "VO_B", OUT), (13, "VO_C", OUT), (12, "VO_D", OUT),
             (11, "VI_E", IN), (10, "VI_F", IN), (9, "GND2", PI)],
            desc="6-channel digital isolator SOIC-16 wide (4 fwd / 2 rev)"),
        box("SONGLE_RELAY", "RL", [(4, "C1", PAS), (5, "C2", PAS)], [(1, "COM", PAS), (2, "NC", PAS), (3, "NO", PAS)],
            desc="Power relay SPDT, Proteus ids 1=COM 2=NC 3=NO 4/5=coil"),
        box("EF20", "TR", [(i, str(i), PAS) for i in (1, 2, 3, 4, 5)], [(i, str(i), PAS) for i in (10, 9, 8, 7, 6)],
            desc="EF20 auxiliary flyback transformer, 10 pins"),
        box("EF25_8PIN", "TR", [(i, str(i), PAS) for i in (1, 2, 4, 5)], [(i, str(i), PAS) for i in (10, 9, 7, 6)],
            desc="EF25 heater transformer, pins 1 2 4 5 6 7 9 10"),
    ]
    l, r = header(range(1, 51))
    syms.append(box("HEADER_2X25_50MIL", "J", l, r, show_pin_names=False, desc="MCU connector 2x25, 50 mil"))

    syms.append(rename(std_symbol("power", "PWR_FLAG"), "PWR_FLAG"))
    syms += [power(n, True) for n in GROUNDS] + [power(n, False) for n in SUPPLIES]
    return syms


if __name__ == "__main__":
    sys.exit(run(build))
