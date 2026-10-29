#!/usr/bin/env python3
"""Part values on the board = schematic values (stdlib only).

The Proteus layout (ROOT.LYT) carries stale values for 24 parts (STATUS.md "Phase 1 preparation");
the schematic values (ROOT.DSN = the PDF, lib/part_map.csv `value`) are authoritative. The KiCad
symbols carry the schematic value and p2k.build_pcb copies the symbol value into the footprint
(DRC schematic parity also compares them). This check makes it explicit:

  - every footprint of kicad/tube_psu.kicad_pcb with a symbol has Value = lib/part_map.csv value;
  - the parts whose Proteus layout value differs from the schematic value are listed (expected:
    STALE_LAYOUT_VALUES parts) and carry the schematic value.

Usage: python3 tools/check_values.py
"""
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "p2k"))  # proteus2kicad
from p2k import board, pdsprj, sexpr  # noqa: E402

STALE_LAYOUT_VALUES = 24   # STATUS.md "Phase 1 preparation" (C10, C26, R2, R3, R18, ...)


def main():
    with open(board.path("lib", "part_map.csv")) as f:
        pm = {r["refdes"]: r for r in csv.DictReader(l for l in f if not l.startswith("# "))}
    pcb = sexpr.load(board.path("kicad", f"{board.config().PROJECT}.kicad_pcb"))
    on_board = {}
    for fp in sexpr.find_all(pcb, "footprint"):
        props = {p[1]: p[2] for p in sexpr.find_all(fp, "property")}
        on_board[props["Reference"]] = props["Value"]
    errors = []
    for ref, row in pm.items():
        if ref not in on_board:
            errors.append(f"{ref}: not on the board")
        elif on_board[ref] != row["value"]:
            errors.append(f"{ref}: board value {on_board[ref]!r}, schematic {row['value']!r}")
    proteus = {row["proteus_refdes"] or ref: ref for ref, row in pm.items()}
    lyt = pdsprj.lyt_parts(board.path("source", "tube_power_5_1.pdsprj"), set(proteus))
    stale = sorted((proteus[p], rec["value"]) for p, rec in lyt.items() if rec["value"] != pm[proteus[p]]["value"])
    if len(stale) != STALE_LAYOUT_VALUES:
        errors.append(f"{len(stale)} parts with a stale Proteus layout value, expected {STALE_LAYOUT_VALUES}")
    print(f"check_values: {len(pm)} parts, board value = schematic value for "
          f"{sum(1 for r in pm if on_board.get(r) == pm[r]['value'])}")
    print(f"check_values: {len(stale)} parts with a stale Proteus layout value carry the schematic value: "
          + ", ".join(f"{r} {on_board.get(r)} (layout {v})" for r, v in stale))
    for e in errors:
        print("check_values: ERROR " + e)
    print("check_values: " + ("FAILED" if errors else "OK"))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
