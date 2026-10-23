"""proteus2kicad configuration of the tube_power_5_1 board (tools in tools/p2k, see its README).

Plain Python; every value here is specific to this board. Coordinates in mm, IPC frame (Y up).
"""

PROJECT = "tube_psu"  # KiCad project / library name

# --- Footprints (gen_footprints) -----------------------------------------------------

# Pad sizes of the footprints: "kicad" = KiCad library pad sizes and drills (the default chosen
# in Phase 2, pad centres always on the Proteus positions), "proteus" = every footprint gets
# the Proteus pad sizes and drills (KiCad library footprints are replaced by derived project
# footprints). Switch here, re-run tools/gen_footprints.py and the sheet scripts.
FOOTPRINT_PAD_SIZES = "kicad"

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

# --- PCB (p2k.build_pcb, gerber_to_tracks, assign_nets, pours_to_zones, check_board, drc) ---

# Proteus stack (CADCAM READ-ME): 4 x 0.036 Cu, 0.32 prepreg / 0.772 core / 0.32 prepreg.
PCB_THICKNESS = 1.556  # mm, without the 2 x 0.01 mm solder resist
# Design rules from the Proteus copper as built (STATUS.md "Phase 3", measured gaps), in mm.
PCB_RULES = dict(
    min_track=0.15,       # thinnest conductor draw 0.1524 (6 mil)
    min_via=0.5,          # vias 0.5/0.3 (279) and 1.016/0.381 (4)
    min_annular=0.1,      # (0.5 - 0.3) / 2
    min_drill=0.3,
    clearance=0.15,       # smallest different-net gap 0.1524 (6 mil, pours/pads/tracks; tools/measure_gaps.py)
    hole_clearance=0.15,  # via drills: 0.1 annular + >= 0.1564 gap
    hole_to_hole=0.25,    # smallest drill-to-drill 0.335
    edge_clearance=0.5,   # copper to outline >= 0.90
    track=0.254,          # Default netclass
    via=0.5,
    via_drill=0.3,
)
# Board-only footprints (lib/tube_psu.pretty, tools/gen_footprints.py PROJECT).
HOLE_FOOTPRINT = "tube_psu:MountingHole_3.0mm_NPTH_Ring3.5mm"   # 8 unplated holes, copper ring, no net
HOLE_VALUE = "MountingHole_3.0mm"
FREE_PAD_FOOTPRINT = "tube_psu:WirePad_D4.0mm_Drill2.55mm"      # 4 plated wire pads with a net
FREE_PAD_VALUE = "WirePad_2.55mm"
FREE_PAD_PREFIX = "WP"
# --- Phase 4 checks (p2k.gerber_roundtrip, p2k.ipc356_diff) ---------------------------

# The Proteus IPC / drill gerber has 16 extra via records stacked on 12 positions of a GND via
# array (x = 2.7 / 3.8 / 4.8, y = 12.3 .. 15.3; one drill hole each, STATUS.md "Phase 3" finding):
# 283 records, 267 board vias. Both checks expect exactly this many shared records.
STACKED_VIAS = 16
# KiCad footprint drills smaller than the Proteus drill, kept so far (OPEN USER DECISION, see
# STATUS.md; Phase 3 chose KiCad library drills where DRC did not force a change). Listed here so
# the checks report them instead of failing; remove an entry to make the check fail again.
DRILL_SMALLER = {
    (1.651, 1.5): "Q5/Q6 TO-247-3_Vertical (KiCad 1.5 mm, Proteus 1.651 = 65 mil)",
    (1.016, 1.0): "C65/C81/C82-2/C84/C85 C_Disc_D12.5mm and J4 PinHeader_1x03 (KiCad 1.0, Proteus 1.016 = 40 mil)",
    (1.067, 1.0): "C64/C66 C_Rect_L13.0mm_W5.0mm_P10.00mm (KiCad 1.0, Proteus 1.0668 = 42 mil)",
}
# Excellon drill file of the earlier RS-274X export of the same board: cross-check against the
# X2 drill gerbers (positions and diameters 1:1).
DRILL_EXCELLON = "source/cadcam_rs274x/tube_power_5_1 - CADCAM Drill.DRL"
# ROUNDTRIP tolerances stay at the defaults (res 0.025, tol 0.05, min_area 0.01, overlay_res 0.1, drill_tol 0.005).

# Error-severity DRC types that remain by design ({type: reason}, see STATUS.md "Phase 3").
DRC_ACCEPTED = {
    "courtyards_overlap": "KiCad courtyards vs the Proteus placement",
    "pth_inside_courtyard": "KiCad courtyards vs the Proteus placement",
    "npth_inside_courtyard": "mounting hole H4 inside the RM8 choke L2's pad-box courtyard (Proteus placement)",
}
