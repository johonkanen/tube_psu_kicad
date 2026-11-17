#!/usr/bin/env python3
"""Generate lib/part_map.csv: refdes -> PDF page, symbol, value, Proteus device and package.

Sources (STATUS.md "Phase 1 preparation"):
  refdes   reference/ipc356_pads.json (`refdes` = KiCad name, `refdes_proteus` = Proteus name)
  value    schematic value from ROOT.DSN in source/tube_power_5_1.pdsprj (= the PDF; the layout
           values in ROOT.LYT are stale for 24 parts)
  device, package   layout record in ROOT.LYT
  sheet    PDF page whose text layer has the refdes; PAGE_OVERRIDES for the ambiguous ones
  lib_id   SYMBOL_BY_DEVICE (Proteus device -> lib/tube_psu.kicad_sym symbol)

  tools/make_part_map.py           write lib/part_map.csv
  tools/make_part_map.py --check   fail if lib/part_map.csv is not up to date
"""
import csv
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "p2k"))  # proteus2kicad
from p2k import board, pdftext, pdsprj  # noqa: E402

PRJ = board.path("source", "tube_power_5_1.pdsprj")
PDF = board.path("source", "schematic_pdf", "tube_power_5_1.PDF")
OUT = board.path("lib", "part_map.csv")
LIB = board.config().PROJECT

C, CP, R = "C", "C_Polarized", "R"
SYMBOL_BY_DEVICE = {
    "0603 CAPACITOR": C, "06031A101JAT2A": C, "1206 CAP": C, "12061C103KAT2A": C,
    "C2220C102FZGACTU": C, "C5750X6S2W225K250KA": C, "R463F247000N0K": C, "X2": C, "Y2 2N2 CAPACITOR": C,
    "EEEFTE221XAP": CP, "EEU-FR1A152L": CP, "EKXJ451ELL390MJ50S": CP, "UCS2G560MND9": CP, "UPZ2W820MNY9": CP,
    "0603 RESISTOR": R, "0805 RES": R, "1206 RESISTOR": R, "9C06031A1213FKHFT": R, "9C12063A1212FKHFT": R,
    "KRL2012-C-R004-F-T1": R, "RES": R, "RES 1206": R, "TWW10": R,
    "ES1A": "D", "S1M": "D", "ZLLS400TA": "D_Schottky", "C3D02060A": "C3D02060A",
    "IRFBE20": "Q_NMOS_GDS", "IRFP460": "Q_NMOS_GDS", "BUK9Y15-60E": "Q_NMOS_SGD", "BSS138": "Q_NMOS_DGS",
    "TBS22K": "TBS22K", "SCF20-05-550": "SCF20-05-550", "ETD34 TRAN 1P1S": "ETD34_TRAN_1P1S",
    "EF20": "EF20", "EF25_8PIN": "EF25_8PIN", "RM8 INDUCTOR": "RM8_INDUCTOR", "SONGLE RELAY": "SONGLE_RELAY",
    "PIN": "PIN", "66226-003": "CONN_01X03", "50 PIN HEADER 50TH": "HEADER_2X25_50MIL",
    "TLV316IDBVR": "TLV316IDBVR", "OPA2353UA": "LMH6658", "TPS73033": "TPS73033", "ADR380": "ADR380",
    "ADC121S101": "ADC121S101", "IXDD604D2TR": "IXDD604", "IXDD609D2TR": "IXDD609", "IW1818": "IW1818",
    "SI8271": "SI8271", "SI8274": "SI8275", "SI8661": "SI8661",
}

# Fitted part differs from the schematic value (KiCad refdes -> value on the symbol / board).
# DRV5 / DRV6: the schematic (and layout) say SI8274; the populated part is the dual-input Si8275
# (user, 2026-11-17), which matches the board wiring (pin 2 carries the B input).
FITTED_VALUES = {"DRV5": "SI8275BB", "DRV6": "SI8275BB"}  # B = 8 V UVLO, no deglitch

# Refdes whose PDF text-layer hits are ambiguous or missing (resolved on the page renders):
PAGE_OVERRIDES = {
    "C15": 1,      # page 4 "C15" is a J2 signal label (FPGA ball name)
    "C16": 7,      # page 4 "C16" likewise
    "C91": 7,      # refdes not printed in the PDF; 420V-ISO_GND 100n, the only 420V page is 7
    "GND": 7,      # terminal next to +400V; "GND" is a net label on most pages
    "HT_GND": 6,   # terminal; page 3 has HT_GND net labels only
    "V2": 3,       # page 1 mentions V1/V2/V3 in the hand notes
    "V3": 3,
}

FIELDS = ["refdes", "sheet", "lib_id", "value", "device", "package", "proteus_refdes"]


def build():
    ipc = json.load(open(board.path("reference", "ipc356_pads.json")))
    kicad = {}
    for p in ipc["pads"]:
        if p["kind"] == "pad":
            kicad[p["refdes_proteus"]] = p["refdes"]
    refs = set(kicad)
    values = pdsprj.dsn_values(PRJ, refs)
    parts = pdsprj.lyt_parts(PRJ, refs)
    pages = pdftext.refdes_pages(pdftext.pdf_words(PDF), refs)
    errors = []
    rows = []
    for ref in sorted(refs):
        page = PAGE_OVERRIDES.get(ref)
        if page is None:
            if len(pages[ref]) != 1:
                errors.append(f"{ref}: PDF pages {pages[ref]} (add to PAGE_OVERRIDES)")
                continue
            page = pages[ref][0]
        dev = parts[ref]["device"]
        if dev not in SYMBOL_BY_DEVICE:
            errors.append(f"{ref}: no symbol for Proteus device {dev!r}")
            continue
        rows.append({"refdes": kicad[ref], "sheet": page, "lib_id": f"{LIB}:{SYMBOL_BY_DEVICE[dev]}",
                     "value": FITTED_VALUES.get(kicad[ref], values[ref]), "device": dev, "package": parts[ref]["package"],
                     "proteus_refdes": ref if ref != kicad[ref] else ""})
    for ref in sorted(set(PAGE_OVERRIDES) - refs):
        errors.append(f"PAGE_OVERRIDES: {ref} is not an IPC refdes")
    if errors:
        sys.exit("make_part_map:\n  " + "\n  ".join(errors))
    key = lambda r: (r["sheet"], [(0, int(t), "") if t.isdigit() else (1, 0, t)
                                  for t in __import__("re").findall(r"\d+|\D+", r["refdes"])])
    rows.sort(key=key)
    buf = io.StringIO()
    buf.write("# Generated by tools/make_part_map.py - do not edit. sheet = Proteus PDF page;"
              " value = schematic value (ROOT.DSN, FITTED_VALUES override); device/package = Proteus layout record\n")
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue(), rows


def main():
    text, rows = build()
    rel = os.path.relpath(OUT, board.root())
    if "--check" in sys.argv:
        if not os.path.exists(OUT) or open(OUT).read() != text:
            print(f"make_part_map: {rel} is out of date, run tools/make_part_map.py")
            return 1
        print(f"make_part_map: {rel} up to date ({len(rows)} parts)")
        return 0
    open(OUT, "w").write(text)
    print(f"wrote {rel}: {len(rows)} parts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
