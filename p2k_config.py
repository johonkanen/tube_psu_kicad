"""proteus2kicad configuration of the tube_power_5_1 board (tools in tools/p2k, see its README).

Plain Python; every value here is specific to this board. Coordinates in mm, IPC frame (Y up).
"""

PROJECT = "tube_psu"  # KiCad project / library name

# Sources (relative to the repo root). The CADCAM export with Gerber X2 attributes.
CADCAM = "source/cadcam"
IPC = "source/cadcam/tube_power_5_1_X2 - CADCAM Netlist.IPC"

# --- Schematic skeleton (make_skeleton) ----------------------------------------------

# (Proteus page, sheet name, file) - names from the PATH field of the PDF title blocks
SHEETS = [
    (1, "AUX supply", "01_aux_supply.kicad_sch"),
    (2, "DHB gate drive", "02_dhb_gate_drive.kicad_sch"),
    (3, "Isolated measurements", "03_isolated_measurements.kicad_sch"),
    (4, "MCU connector", "04_mcu_connector.kicad_sch"),
    (5, "PFC", "05_pfc.kicad_sch"),
    (6, "Heaters", "06_heaters.kicad_sch"),
    (7, "DHB", "07_dhb.kicad_sch"),
    (8, "Current measurement", "08_current_measurement.kicad_sch"),
    (9, "AC measurement", "09_ac_measurement.kicad_sch"),
    (10, "PFC current measurement", "10_pfc_current_measurement.kicad_sch"),  # untitled in the PDF
    (11, "Startup", "11_startup.kicad_sch"),
]
SCH_TITLE = "Tube power supply"
SCH_COMPANY = "Tube power supply"
SCH_REV = "V5.1"
SCH_COMMENT = "Redrawn from Proteus tube_power_5_1"
SCH_NOTE = ("Tube power supply V5.1 - redrawn from Proteus. One sheet per Proteus PDF page.\n"
            "Net names follow the IPC-D-356A netlist (reference/pins_by_net.md).")

# --- IPC-D-356A fix-ups (ipc356) -----------------------------------------------------

# Truncated refdes (6 chars) -> full Proteus refdes. The terminals are named after their
# rail; full names from the schematic PDF (sheet 1 AUX supply). Each terminal has two
# holes, both pin 1. Each truncated name is unique on this board, so no coordinates needed.
TRUNCATED_REFDES = {
    "+15V O": "+15V OUT",
    "+5V OU": "+5V OUT",
    "-5V OU": "-5V OUT",
    "-80V O": "-80V OUT",
    "SEC GN": "SEC GND",
}
# Expected net per restored refdes (checked by ipc356 --check).
TRUNCATED_NETS = {
    "+15V OUT": "20V_ISO_SEC",
    "+5V OUT": "5V_ISOL",
    "-5V OUT": "-5V_SEC",
    "-80V OUT": "-100V BIAS",
    "SEC GND": "ISO_GND",
}

# Full Proteus refdes -> KiCad refdes (no spaces, no leading sign). Every script that
# compares against the IPC goes through this table (ipc356_pads.json carries it).
KICAD_REFDES = {
    "+15V OUT": "P15V_OUT",
    "+5V OUT": "P5V_OUT",
    "-5V OUT": "N5V_OUT",
    "-80V OUT": "N80V_OUT",
    "SEC GND": "SEC_GND",
    "+400V": "P400V",
}

NET_ALIASES = {
    "GND=POWER": "GND",
}

# Blank-refdes records: a net and one of these drills = via, a net and another drill =
# free pad (the 4 wire pads, 2.55 mm), no net = hole (unplated 3.0 mm mounting holes).
VIA_DRILLS = (0.3, 0.381)
FREE_PAD_DRILLS = (2.55,)
HOLE_DRILLS = (3.0,)
HOLES_PLATED = False

# Expected counts in the Proteus file (PLAN.md section 1).
EXPECTED_IPC = {
    "nets": 193,          # NNAME declarations
    "records": 1165,
    "refdes_raw": 316,    # distinct refdes fields, incl. the blank one of vias/holes/free pads
    "tht_records": 502,   # 317 records (component THT pads + vias + free pads + holes)
    "smd_records": 663,   # 327 records
    "smd_top": 225,
    "smd_bottom": 438,
    "nc_pads": 9,
    "vias": 283,
    "free_pads": 4,
    "holes": 8,
    "parts": 315,         # named refdes after the truncation fix-up
}

# --- Gerbers (check_sources, later the PCB tools) ------------------------------------

# Proteus copper gerber name -> KiCad copper layer, User layer for the pour outlines.
COPPER = [
    ("Top Copper", "F.Cu", "User.1"),
    ("Inner  1", "In1.Cu", "User.2"),
    ("Inner 14", "In2.Cu", "User.3"),
    ("Bottom Copper", "B.Cu", "User.4"),
]
DRILL_PLATED = "Drill TOP-BOT Plated"
DRILL_NONPLATED = "Drill TOP-BOT NonPlated"
OUTLINE = "Mechanical 1"
OUTLINE_RECT = (-71.9, -18.7, 163.0, 110.0)  # x, y, width, height
