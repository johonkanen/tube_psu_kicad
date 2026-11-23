#!/usr/bin/env python3
"""Views of the hand-maintained 5.2 parts table lib/jlc_parts_next.csv (read-only, plain python3).

    python3 kicad_next/review/tools/parts_table.py          the table grouped by LCSC number, lowest stock first:
                                                            LCSC | count | mpn | library_type | stock_at_check |
                                                            check_date | status | refdes; then every `review`
                                                            remark; the refdes without an LCSC number with their
                                                            status; and "CHECK" lines where one LCSC number is
                                                            used with different values or footprints
    python3 kicad_next/review/tools/parts_table.py board    board footprints against the table: Value field,
                                                            footprint id, LCSC field and the DNP attribute of every
                                                            footprint of kicad_next/tube_psu_5_2.kicad_pcb
                                                            (needs the board dump: kicad_next/review/tools/rv setup)

The board file is only read as text (for the LCSC property) and through the JSON dump of board_dump.py.
"""
import collections
import csv
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CSV = os.path.join(ROOT, "lib", "jlc_parts_next.csv")
BOARD = os.path.join(ROOT, "kicad_next", "tube_psu_5_2.kicad_pcb")


def rows():
    with open(CSV) as f:
        return list(csv.DictReader(l for l in f if not l.startswith("#")))


def refkey(r):
    head = r.rstrip("0123456789")
    return (head, int(r[len(head):] or 0))


def table():
    rs = rows()
    by = collections.defaultdict(list)
    for r in rs:
        by[r["lcsc"]].append(r)
    print("LCSC | n | mpn | library_type | stock_at_check | check_date | status | refdes")
    for l, g in sorted(by.items(), key=lambda x: (int(x[1][0]["stock_at_check"] or -1), x[0])):
        if l:
            r = g[0]
            print(f"{l} | {len(g)} | {r['mpn']} | {r['library_type']} | {r['stock_at_check'] or 'NOT READ'} | {r['check_date']} | "
                  f"{'/'.join(sorted({x['status'] for x in g}))} | {' '.join(x['refdes'] for x in g)}")
    print()
    n = 0
    for r in rs:
        if r["review"]:
            n += 1
            print(f"review {r['refdes']:8} {r['lcsc'] or '-':10} {r['review']}")
    print(f"{n} rows with a review remark")
    print()
    print("no LCSC number: " + " ".join(f"{r['refdes']}({r['status']})" for r in rs if not r["lcsc"]))
    print()
    for l, g in by.items():
        if not l:
            continue
        vals = {x["value"].lower().replace(" ", "") for x in g}
        fps = {x["footprint"].split(":")[-1].split("_Pad")[0].split("_Proteus")[0] for x in g}
        if len(vals) > 1 or len(fps) > 1:
            print(f"CHECK one LCSC number, different value / footprint: {l} {g[0]['mpn']}: "
                  + "; ".join(sorted({x['value'] + ' @ ' + x['footprint'].split(':')[-1] for x in g})))
    print(f"{len(rs)} rows, {len([l for l in by if l])} LCSC numbers, status: "
          + ", ".join(f"{k} {v}" for k, v in collections.Counter(r['status'] for r in rs).most_common()))


def board():
    tab = {r["refdes"]: r for r in rows()}
    cache = subprocess.check_output([os.path.join(HERE, "rv"), "dir"], text=True).strip()
    dump = os.path.join(cache, "b52.json")
    if not os.path.exists(dump):
        sys.exit("board dump missing: run kicad_next/review/tools/rv setup")
    d = json.load(open(dump))
    txt = open(BOARD).read()
    lcsc = {}
    for m in re.finditer(r'\n\t\(footprint "', txt):
        end = txt.find('\n\t(footprint "', m.end())
        blk = txt[m.start():end if end > 0 else len(txt)]
        ref = re.search(r'\(property "Reference" "([^"]*)"', blk)
        f = re.search(r'\(property "LCSC" "([^"]*)"', blk)
        if ref:
            lcsc[ref.group(1)] = f.group(1) if f else None
    n = 0
    for f in sorted(d["footprints"], key=lambda f: refkey(f["ref"])):
        r = tab.get(f["ref"])
        if r is None:
            if not f["ref"].startswith(("H", "WP")) or f["ref"].startswith("HT_"):
                print("on the board, not in the table:", f["ref"])
            continue
        if f["value"] != r["value"] or f["fp"] != r["footprint"] or (lcsc.get(f["ref"]) or "") != r["lcsc"]:
            n += 1
            print(f"{f['ref']}: board value {f['value']!r} fp {f['fp']!r} LCSC {lcsc.get(f['ref'])!r}  |  "
                  f"table {r['value']!r} {r['footprint']!r} {r['lcsc']!r}")
        if f["dnp"] != (r["status"] == "dnp"):
            print(f"{f['ref']}: DNP attribute on the board {f['dnp']} vs table status {r['status']!r}")
    print(f"{len(d['footprints'])} footprints on the board ({sum(1 for f in d['footprints'] if f['ref'] not in tab)} board-only: "
          f"mounting holes H*, wire pads WP*), {len(tab)} table rows, {n} field difference(s); table rows missing on the board: "
          f"{sorted(set(tab) - {f['ref'] for f in d['footprints']}, key=refkey) or 'none'}")


if __name__ == "__main__":
    import signal
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    if len(sys.argv) > 1 and sys.argv[1] == "board":
        board()
    elif len(sys.argv) > 1:
        sys.exit(__doc__)
    else:
        table()
