#!/usr/bin/env python3
"""Generate lib/tube_psu_next.kicad_sym, the 5.2 symbol library (fork of tools/gen_symbols.py, p2k.symgen).

The 5.2 symbols diverge from the 5.1 migration library lib/tube_psu.kicad_sym (which tools/gen_symbols.py
keeps frozen); edit build() below for 5.2 symbols. Library nickname in kicad_next: tube_psu_next.

Pin numbers equal the Proteus/IPC pin ids; pin names of the box symbols are the Proteus
pin names from the device pinouts in ROOT.DSN (STATUS.md "Phase 1 preparation"). Simple
symbols are copied from the KiCad 10 standard library (flattened, pins renumbered).
Power symbols carry the IPC net names of the rails drawn as Proteus power terminals.

Run:  tools/next/gen_symbols.py           (needs the AppImage mount for the std libs)
      tools/next/gen_symbols.py --check   (fail if lib/tube_psu_next.kicad_sym is not up to date)
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools", "p2k"))  # proteus2kicad
from p2k import symgen  # noqa: E402
from p2k.symgen import *  # noqa: E402,F401,F403
from p2k.symgen import _pin  # noqa: E402
from p2k.sexpr import dump, parse  # noqa: E402

LIB = os.path.join(ROOT, "lib", "tube_psu_next.kicad_sym")

GROUNDS = ["GND", "ISO_GND", "HT_GND", "ISO_UART_GND"]       # ISO_UART_GND: 5.2 UART island (NR 3b)
SUPPLIES = ["DC+", "420V", "15V", "15V_ISO_SEC", "6V3", "5V", "5V_ISOL", "+3V3", "AD2_3V3",
            "+1V65_BIAS", "-5V_SEC", "-100V BIAS", "UART_5V", "UART_3V3"]

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
        from_std("Device", "Filter_EMI_LL_1423", "SCF20-05-550", "CM",
                 desc="Common-mode choke, windings 1-2 (top) and 3-4 (bottom), Proteus ids as drawn in the PDF",
                 pins={"2": "1", "3": "2", "1": "3", "4": "4"}, names={"1": "1", "2": "2", "3": "3", "4": "4"}),
        from_std("Device", "Transformer_1P_1S", "ETD34_TRAN_1P1S", "TR",
                 desc="DHB transformer ETD34, P1=1 P2=2 S1=3 S2=4 (3 top-right as in Proteus)",
                 pins={"1": "1", "2": "2", "3": "4", "4": "3"}, names={"1": "P1", "2": "P2", "3": "S1", "4": "S2"}),
        from_std("Connector", "TestPoint", "PIN", "TP", "PIN",
                 desc="Proteus PIN terminal (blade connector: footprint has two pads numbered 1)"),
        from_std("Connector_Generic", "Conn_01x03", "CONN_01X03", "J", desc="3-pin connector (66226-003)"),
        from_std("Amplifier_Operational", "MCP6L91T-EOT", "TLV316IDBVR", "U",
                 desc="Op-amp SOT-23-5, Proteus 1=OP 2=V- 3=+IN 4=-IN 5=V+"),
        from_std("Amplifier_Operational", "LM2904", "LMH6658", "U",
                 desc="Dual op-amp TSSOP-8 (Proteus device OPA2353UA), standard dual pinout"),
        # --- 5.2 additions (NEXT_REVISION.md items in the descriptions) ---
        from_std("Amplifier_Operational", "LM2904", "LMH6643", "U",
                 desc="Dual op-amp LMH6643MMX VSSOP-8, standard dual pinout (drop-in for the LMH6658, NR 4.10b)"),
        from_std("Amplifier_Operational", "LM2904", "TLV9062", "U",
                 desc="Dual RRIO op-amp TLV9062IDGKR VSSOP-8, standard dual pinout (AUX / 5V_MEAS followers, NR 4b/4c)"),
        from_std("Device", "L", "L_TOROID", "L", desc="PFC choke on a sendust toroid, two leads (NR 5.2)"),
        from_std("Connector_Generic", "Conn_01x06", "CONN_01X06", "J",
                 desc="6-pin 2.54 mm header, FTDI TTL-232R-3V3 pinout (NR 3b)"),
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
        # OUTA and OUTB are one output on two pins (tied together on sheet 9): OUTB is passive
        # so that ERC does not report Output-Output (STATUS.md, Phase 1 transcription).
        box("IXDD609", "DRV", [(1, "VCC", PI), (8, "VCC", PI), (2, "IN", IN), (3, "EN", IN)],
            [(7, "OUTA", OUT), (6, "OUTB", PAS), (4, "GND", PI), (5, "GND", PI), (9, "TAB", PAS)],
            desc="9 A gate driver DFN-8 with thermal pad"),
        box("IW1818", "PWM", [(5, "Vcc", PI), (4, "Vsense", IN), (2, "I_sense", IN), (1, "E", PAS)],
            [(8, "C", PAS), (7, "C", PAS), None, (3, "GND", PI)],
            desc="Flyback controller with integrated switch, 7-pin (no pin 6)"),
        box("SI8271", "DRV", [(2, "VDD1", PI), (1, "Vin", IN), (4, "EN", IN), (3, "GND1", PI)],
            [(8, "VDD2", PI), (7, "OUT+", OUT), (6, "OUT-", OUT), (5, "GND2", PI)],
            desc="Isolated single gate driver SOIC-8"),
        # The schematic says SI8274 (PWM input, DT resistor pin 6) but the fitted part is the
        # dual-input Si8275 (user, 2026-11-17): pin 1 VIA, pin 2 VIB (the Proteus wires to pin 2,
        # DRV5-2 PRI_DHB_HI / DRV6-2 ISO_SEC_DHB_LO, are its B input), pin 6 NC. Pin 6 keeps the
        # Proteus dead-time resistor (R40 / R25), harmless on the Si8275, so it is passive.
        box("SI8275", "DRV", [(3, "VDDI", PI), (8, "VDDI", PI), (1, "VIA", IN), (5, "EN", IN), (6, "NC6", PAS),
                              (4, "GNDI", PI), (2, "VIB", IN), (7, "NC7", NC)],
            [(16, "VDDA", PI), (15, "VOA", OUT), (14, "GNDA", PI), (13, "NC13", NC), (12, "NC12", NC),
             (11, "VDDB", PI), (10, "VOB", OUT), (9, "GNDB", PI)],
            desc="Isolated dual gate driver with enable, SOIC-16 (Si8275, no overlap protection)"),
        box("SI8661", "ISO",
            [(1, "VDD1", PI), (2, "VI_A", IN), (3, "VI_B", IN), (4, "VI_C", IN), (5, "VI_D", IN),
             (6, "VI_E", IN), (7, "VO_F", OUT), (8, "GND1", PI)],
            [(16, "VDD2", PI), (15, "VO_A", OUT), (14, "VO_B", OUT), (13, "VO_C", OUT), (12, "VO_D", OUT),
             (11, "VO_E", OUT), (10, "VI_F", IN), (9, "GND2", PI)],
            desc="6-channel digital isolator SOIC-16 wide (5 fwd A-E / 1 rev F; SO16W pinout of the DSN)"),
        box("SONGLE_RELAY", "RL", [(4, "C1", PAS), (5, "C2", PAS)], [(1, "COM", PAS), (2, "NC", PAS), (3, "NO", PAS)],
            desc="Power relay SPDT, Proteus ids 1=COM 2=NC 3=NO 4/5=coil"),
        box("EF20", "TR", [(i, str(i), PAS) for i in (1, 2, 3, 4, 5)], [(i, str(i), PAS) for i in (10, 9, 8, 7, 6)],
            desc="EF20 auxiliary flyback transformer, 10 pins"),
        box("EF25_8PIN", "TR", [(i, str(i), PAS) for i in (1, 2, 4, 5)], [(i, str(i), PAS) for i in (10, 9, 7, 6)],
            desc="EF25 heater transformer, pins 1 2 4 5 6 7 9 10"),
    ]
    # --- 5.2 additions -------------------------------------------------------------------------------
    syms += [
        # ICE5AR4780BZS (Infineon datasheet V2.3, PG-DIP-7, NR 1.5): fixed-frequency CoolSET with integrated
        # 800 V CoolMOS in cascode; 1 VERR (error-amplifier input, non-isolated mode), 2 FB (compensation /
        # ABM selection RSel), 3 CS, 4 GATE (cascode gate: start-up resistor from the bus), 5 DRAIN,
        # 7 VCC, 8 GND; pin 6 absent.
        # (left pin order GATE / VCC / VERR / FB / CS: lets the sheet-1 networks leave the pins without crossings)
        box("ICE5AR", "PWM", [(4, "GATE", PAS), (7, "VCC", PI), (1, "VERR", IN), (2, "FB", PAS), (3, "CS", IN)],
            [(5, "DRAIN", PAS), None, None, None, (8, "GND", PI)],
            desc="Fixed-frequency 100 kHz current-mode CoolSET, 800 V CoolMOS, error amplifier, DIP-7 (ICE5AR4780BZS, NR 1.5)"),
        # UCC21520 (TI SLUSCJ9): same SOIC-16W pin positions as the Si8275 (5 = DISABLE, 6 = DT).
        # (left pin order as on the 5.1 SI8275 symbol, so the sheet-2 driver cell keeps its geometry)
        box("UCC21520", "DRV", [(3, "VCCI", PI), (8, "VCCI", PI), (1, "INA", IN), (5, "DIS", IN), (6, "DT", PAS),
                                (4, "GND", PI), (2, "INB", IN), (7, "NC", NC)],
            [(16, "VDDA", PI), (15, "OUTA", OUT), (14, "VSSA", PI), (13, "NC", NC), (12, "NC", NC),
             (11, "VDDB", PI), (10, "OUTB", OUT), (9, "VSSB", PI)],
            desc="Isolated dual gate driver 4 A / 6 A, 5.7 kVrms reinforced, SOIC-16W (UCC21520DWR, NR 3a)"),
        box("UCC27511A", "DRV", [(1, "VDD", PI), (6, "IN+", IN), (5, "IN-", IN)],
            [(2, "OUTH", OUT), (3, "OUTL", OUT), None, (4, "GND", PI)],
            desc="Single low-side gate driver 4 A / 8 A, split outputs, SOT-23-6 (UCC27511ADBVR, NR 3a)"),
        box("UCC27524A", "DRV", [(6, "VDD", PI), (1, "ENA", IN), (2, "INA", IN), (4, "INB", IN), (8, "ENB", IN)],
            [(7, "OUTA", OUT), (5, "OUTB", OUT), None, (3, "GND", PI)],
            desc="Dual 5 A low-side gate driver, SOIC-8 (UCC27524ADR, NR 3a)"),
        # Si8621 WB SOIC-16 pinout (Skyworks datasheet 5.): A1 in -> B1 out, B2 in -> A2 out; CA-IS3721HW
        # (Chipanalog, default high) has the same pinout.
        box("SI8621", "U", [(3, "VDD1", PI), (4, "A1", IN), (5, "A2", OUT), (1, "GND1", PI), (7, "GND1", PI),
                            (2, "NC", NC), (6, "NC", NC), (8, "NC", NC)],
            [(14, "VDD2", PI), (13, "B1", OUT), (12, "B2", IN), (16, "GND2", PI), (9, "GND2", PI),
             (10, "NC", NC), (11, "NC", NC), (15, "NC", NC)],
            desc="2-channel digital isolator 1 fwd / 1 rev, WB SOIC-16 (Si8621xD / CA-IS3721HW, NR 3b)"),
        box("XC6206", "U", [(3, "VIN", PI)], [(2, "VOUT", PO)], bottom=[(1, "GND", PI)],
            desc="3.3 V LDO SOT-23 (XC6206P332MR: 1 = GND, 2 = VOUT, 3 = VIN)"),
        # TR1 on the EEL19 4+6 bobbin (EEL19_DESIGN.md 6a, footprint Transformer_EEL19_V_4+6_FlyLeads):
        # 11 / 12 = fly leads FL_DC / FL_C, 1 A15 finish, 2 GND, 3 A5 finish; 5 SHV, 7 S5, 8 SN5, 9 ISO_GND,
        # 10 S15; bobbin pins 4 and 6 are clipped (no pad, no pin).
        # (pin positions as on the 5.1 EF20 symbol: 1, 2, 3, FL_DC, FL_C down the left, 10, 9, 8, 7, 5 right)
        box("EEL19_4P6", "TR", [(1, "A15", PAS), (2, "AGND", PAS), (3, "A5", PAS), (11, "FL_DC", PAS),
                                (12, "FL_C", PAS)],
            [(10, "S15", PAS), (9, "SGND", PAS), (8, "SN5", PAS), (7, "S5", PAS), (5, "SHV", PAS)],
            desc="Aux flyback transformer EEL19 vertical 4+6 with fly-lead primary (NR 1.1)"),
        # TR3 on the EC42/15 two-chamber bobbin (DAB_TRANSFORMER.md 5): two pins per winding end.
        box("EC42_2CH", "TR", [(1, "P_START", PAS), (2, "P_START", PAS), None, (7, "P_FIN", PAS), (8, "P_FIN", PAS)],
            [(9, "S_START", PAS), (10, "S_START", PAS), None, (15, "S_FIN", PAS), (16, "S_FIN", PAS)],
            desc="DAB transformer EC42/15 two-chamber, option B 20:21 (NR 2.1); dots on 1+2 / 9+10"),
    ]
    l, r = header(range(1, 51))
    syms.append(box("HEADER_2X25_50MIL", "J", l, r, show_pin_names=False, desc="MCU connector 2x25, 50 mil"))

    syms.append(rename(std_symbol("power", "PWR_FLAG"), "PWR_FLAG"))
    syms += [power(n, True) for n in GROUNDS] + [power(n, False) for n in SUPPLIES]
    return syms


def run(argv=None):
    """p2k.symgen.run with the 5.2 library path (symgen.run writes lib/<PROJECT>.kicad_sym of p2k_config.py)."""
    argv = sys.argv[1:] if argv is None else argv
    rel = os.path.relpath(LIB, ROOT)
    symgen.STD = symgen.std_lib_dir()
    lib = [Sym("kicad_symbol_lib"), [Sym("version"), Sym("20251024")], [Sym("generator"), "tube_psu_gen_symbols"],
           [Sym("generator_version"), "10.0"], *build()]
    if "--check" in argv:
        current = load(LIB) if os.path.exists(LIB) else None
        if current != parse(dump(lib)):
            print(f"gen_symbols: {rel} is out of date, run tools/next/gen_symbols.py")
            return 1
        print(f"gen_symbols: {rel} up to date ({len(lib) - 4} symbols)")
        return 0
    save(LIB, lib)
    print(f"wrote {rel}: {len(lib) - 4} symbols")
    return 0


if __name__ == "__main__":
    sys.exit(run())
