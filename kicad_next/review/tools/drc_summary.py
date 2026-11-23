#!/usr/bin/env python3
"""Summary of the last DRC / ERC reports written by tools/next/check_next.sh (read-only, plain python3).

    python3 kicad_next/review/tools/drc_summary.py                 counts per type, age against the board
    python3 kicad_next/review/tools/drc_summary.py TYPE [X0 Y0 X1 Y1]
                                                                   the items of one type (e.g. courtyards_overlap,
                                                                   starved_thermal), optionally only in a box
    python3 kicad_next/review/tools/drc_summary.py erc             the ERC report lines grouped by type

Reads reports/next/drc.json (check_board.py: DRC WITHOUT the creepage pass, with schematic parity) and
reports/next/erc.rpt. These are git-ignored outputs of the last check_next.sh run: if the script says the
report is OLDER than the board or does not exist, do not trust it - ask for / wait for a check_next.sh run
(2.3 GB; one KiCad DRC job at a time on this machine) instead of starting one yourself without `rv guard`.
Item positions are board coordinates in mm.
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DRC = os.path.join(ROOT, "reports", "next", "drc.json")
ERC = os.path.join(ROOT, "reports", "next", "erc.rpt")
BOARD = os.path.join(ROOT, "kicad_next", "tube_psu_5_2.kicad_pcb")


def age(path, src):
    if not os.path.exists(path):
        return "MISSING"
    return "newer than its source (ok)" if os.path.getmtime(path) >= os.path.getmtime(src) else "OLDER than its source - stale"


def main():
    a = sys.argv[1:]
    if a and a[0] == "erc":
        if not os.path.exists(ERC):
            sys.exit("reports/next/erc.rpt missing")
        cur, sheet, by = None, "/", defaultdict(list)
        for line in open(ERC):
            m = re.match(r"\[(\w+)\]: (.*)", line)
            if line.startswith("***** Sheet"):
                sheet, cur = line.split("Sheet", 1)[1].strip(), None
            elif line.startswith(" **"):
                cur = None
            elif m:
                cur = m.group(1)
                by[cur].append([f"sheet {sheet}", m.group(2).strip()])
            elif cur and line.strip().startswith("@"):
                by[cur][-1].append(line.strip())
        for t, items in by.items():
            print(f"{t}: {len(items)}")
            for it in items:
                print("    " + " | ".join(it))
        return
    if not os.path.exists(DRC):
        sys.exit("reports/next/drc.json missing (written by tools/next/check_board.py)")
    d = json.load(open(DRC))
    print(f"reports/next/drc.json: {age(DRC, BOARD)}; date {d.get('date')}, KiCad {d.get('kicad_version')}")
    if os.path.exists(ERC):
        print(f"reports/next/erc.rpt: {age(ERC, os.path.join(ROOT, 'kicad_next', 'tube_psu_5_2.kicad_sch'))}; "
              f"{sum(1 for l in open(ERC) if '; error' in l)} errors, {sum(1 for l in open(ERC) if '; warning' in l)} warnings")
    if not a:
        for key in ("violations", "unconnected_items", "schematic_parity"):
            items = d.get(key, [])
            c = Counter((v["type"], v.get("severity", ""), "excluded" if v.get("excluded") else "") for v in items)
            print(f"{key}: {len(items)}")
            for (t, sev, ex), n in sorted(c.items(), key=lambda x: -x[1]):
                print(f"   {n:4}  {t}  {sev} {ex}")
        return
    box = list(map(float, a[1:5])) if len(a) >= 5 else None
    n = 0
    for key in ("violations", "unconnected_items", "schematic_parity"):
        for v in d.get(key, []):
            if v["type"] != a[0]:
                continue
            its = v.get("items", [])
            pos = [(i["pos"]["x"], i["pos"]["y"]) for i in its if "pos" in i]
            if box and not any(min(box[0], box[2]) <= x <= max(box[0], box[2]) and min(box[1], box[3]) <= y <= max(box[1], box[3]) for x, y in pos):
                continue
            n += 1
            print(f"{v['description']}" + (" [excluded]" if v.get("excluded") else ""))
            for i in its:
                p = i.get("pos", {})
                print(f"     ({p.get('x', 0):.2f}, {p.get('y', 0):.2f})  {i.get('description', '')}")
    print(f"{n} item(s) of type {a[0]}")


if __name__ == "__main__":
    main()
