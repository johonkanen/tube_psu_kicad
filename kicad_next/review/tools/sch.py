#!/usr/bin/env python3
"""Schematic / parts queries for the 5.2 design review (read-only, plain python3).

Works on a KiCad XML netlist. Export one first (about 1 s, light; writes only OUT.xml):

    tools/p2k/bin/kicad-cli sch export netlist --format kicadxml -o /tmp/rv/n52.xml kicad_next/tube_psu_5_2.kicad_sch
    tools/p2k/bin/kicad-cli sch export netlist --format kicadxml -o /tmp/rv/n51.xml kicad/tube_psu.kicad_sch      # 5.1

("Warning: schematic has annotation errors" is printed for both and is harmless: refdes like
P400V / GND / IN1 are not R1-style.)

    python3 kicad_next/review/tools/sch.py NET.xml COMMAND ...

Commands
  sheets                 sheet names with part counts
  sheet N|NAME           every part of one sheet (N = 1..11 or a part of the sheet name):
                         ref, value, footprint, and pin=net for every pin
  ref REF[,REF..]        one part: value, footprint, sheet, LCSC field, pin number / pin name = net
  net NAME [NAME..]      the pins on a net (glob allowed; a local net may be given without its sheet path),
                         with net class
  bom N|NAME             the parts of one sheet joined with lib/jlc_parts_next.csv:
                         ref, value, footprint, lcsc, mpn, library_type, stock_at_check, status, review, note
  kind PREFIX            every part whose refdes starts with PREFIX + number (C, R, D, Q, U, DRV, ...) on all
                         sheets: value, footprint, its nets, and the LCSC / MPN / status / stock / review / note
                         columns of lib/jlc_parts_next.csv, "|"-separated (for rating tables)
  check                  netlist against lib/jlc_parts_next.csv: every part has a row, value / footprint / LCSC
                         field agree; status counts; refdes without an LCSC number
  part REF[,REF..]       the full rows of REF in lib/jlc_parts_next.csv, lib/part_map_next.csv and
                         lib/footprint_map_next.csv (the three hand-maintained 5.2 tables)
  cmp OTHER.xml N|NAME   differences of one sheet against another netlist (e.g. 5.1): parts only here /
                         only there / value or footprint changed / pin nets changed. Sheet = the sheet in
                         THIS netlist; parts are matched by refdes. The 5.1 KiCad netlist already uses the
                         5.2 rail names (15V, 15V_ISO_SEC, +1V65_BIAS; the Proteus / PDF names are 20V,
                         20V_ISO_SEC, +2V5_BIAS). Renamed in 5.2: -5V_SEC -> -15V_SEC, PFC drain nets, FLY_C.
"""
import csv
import fnmatch
import os
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


class Net:
    def __init__(self, path):
        t = ET.parse(path).getroot()
        self.comp = {}
        for c in t.find("components"):
            sp = c.find("sheetpath")
            lcsc = ""
            for f in c.iter("field"):
                if f.get("name") == "LCSC":
                    lcsc = f.text or ""
            self.comp[c.get("ref")] = {"value": c.findtext("value") or "", "fp": c.findtext("footprint") or "",
                                       "sheet": (sp.get("names") if sp is not None else "/").strip("/"),
                                       "lcsc": lcsc, "pins": {}, "dnp": c.find("property[@name='dnp']") is not None}
        self.nets = {}
        self.cls = {}
        for n in t.find("nets"):
            name = n.get("name")
            self.cls[name] = n.get("class") or ""
            self.nets[name] = []
            for nd in n:
                ref, pin = nd.get("ref"), nd.get("pin")
                self.nets[name].append((ref, pin, nd.get("pinfunction") or ""))
                if ref in self.comp:
                    self.comp[ref]["pins"][pin] = (name, nd.get("pinfunction") or "")
        self.sheets = sorted({c["sheet"] for c in self.comp.values()})

    def sheet(self, key):
        m = [s for s in self.sheets if s[:2] == f"{int(key):02d}"] if key.isdigit() else \
            [s for s in self.sheets if key.lower() in s.lower()]
        if len(m) != 1:
            sys.exit(f"sheet {key!r}: one of {self.sheets}")
        return m[0]

    def resolve(self, arg):
        r = [n for n in self.nets if n == arg or n.rsplit("/", 1)[-1] == arg] or fnmatch.filter(self.nets, arg)
        if not r:
            sys.exit(f"no net matches {arg!r}")
        return sorted(r)


def refkey(r):
    head = r.rstrip("0123456789")
    return (head, int(r[len(head):] or 0))


def pinkey(p):
    return (0, int(p)) if p.isdigit() else (1, p)


def pins_str(c):
    out = []
    for p in sorted(c["pins"], key=pinkey):
        n, fn = c["pins"][p]
        fn = fn.split("_")[0] if fn else ""
        out.append(f"{p}{'(' + fn + ')' if fn and fn != p else ''}={n}")
    return "  ".join(out)


def jlc():
    rows = {}
    with open(os.path.join(ROOT, "lib", "jlc_parts_next.csv")) as f:
        for r in csv.DictReader(l for l in f if not l.startswith("#")):
            rows[r["refdes"]] = r
    return rows


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    N = Net(sys.argv[1])
    cmd, a = sys.argv[2], sys.argv[3:]
    if cmd == "sheets":
        for s in N.sheets:
            print(f"{s:28} {sum(1 for c in N.comp.values() if c['sheet'] == s)} parts")
    elif cmd == "sheet":
        s = N.sheet(a[0])
        print(f"== sheet {s}")
        for r in sorted((r for r, c in N.comp.items() if c["sheet"] == s), key=refkey):
            c = N.comp[r]
            print(f"{r:9} {c['value']:22} {c['fp'].split(':')[-1][:38]:38} {pins_str(c)}")
    elif cmd == "ref":
        for r in ",".join(a).split(","):
            c = N.comp.get(r)
            if not c:
                print(f"{r}: not in the netlist")
                continue
            print(f"{r}  {c['value']}  {c['fp']}  sheet {c['sheet']}  LCSC {c['lcsc'] or '-'}")
            for p in sorted(c["pins"], key=pinkey):
                n, fn = c["pins"][p]
                print(f"   {p:>4} {fn:22} {n}  [{N.cls.get(n, '')}]")
    elif cmd == "net":
        for arg in a:
            for n in N.resolve(arg):
                print(f"{n} [{N.cls[n]}]: " + "  ".join(f"{r}.{p}" + (f"({fn.split('_')[0]})" if fn and fn.split('_')[0] != p else "")
                                                        for r, p, fn in sorted(N.nets[n], key=lambda x: refkey(x[0]))))
    elif cmd == "bom":
        s, J = N.sheet(a[0]), jlc()
        print("ref,value,footprint,lcsc,mpn,library_type,stock_at_check,status,review,note")
        for r in sorted((r for r, c in N.comp.items() if c["sheet"] == s), key=refkey):
            c, j = N.comp[r], J.get(r, {})
            print(",".join([r, c["value"], c["fp"].split(":")[-1]] + [j.get(k, "?") for k in
                  ("lcsc", "mpn", "library_type", "stock_at_check", "status", "review", "note")]))
    elif cmd == "kind":
        J = jlc()
        pre = a[0]
        print("ref | value | footprint | nets (pin=net) | lcsc | mpn | status | stock_at_check | review | note")
        for r in sorted((r for r in N.comp if r.rstrip("0123456789") == pre), key=refkey):
            c, j = N.comp[r], J.get(r, {})
            nets = "  ".join(f"{p}={c['pins'][p][0].rsplit('/', 1)[-1]}" for p in sorted(c["pins"], key=pinkey)) if len(c["pins"]) <= 4 \
                else f"{len(c['pins'])} pins"
            print(" | ".join([r, c["value"], c["fp"].split(":")[-1], nets] + [j.get(k, "?") for k in
                  ("lcsc", "mpn", "status", "stock_at_check", "review", "note")]))
    elif cmd == "check":
        # netlist against lib/jlc_parts_next.csv: every part has a row; value / footprint / LCSC field agree
        J, bad = jlc(), 0
        for r in sorted(N.comp, key=refkey):
            c, j = N.comp[r], J.get(r)
            if j is None:
                print(f"{r}: no row in lib/jlc_parts_next.csv"); bad += 1; continue
            if j["value"] != c["value"]:
                print(f"{r}: value netlist {c['value']!r} != csv {j['value']!r}"); bad += 1
            if j["footprint"] != c["fp"]:
                print(f"{r}: footprint netlist {c['fp']!r} != csv {j['footprint']!r}"); bad += 1
            if (j["lcsc"] or "") != (c["lcsc"] or ""):
                print(f"{r}: LCSC field netlist {c['lcsc']!r} != csv {j['lcsc']!r}"); bad += 1
        extra = sorted(set(J) - set(N.comp), key=refkey)
        if extra:
            print("rows in the csv without a part in the netlist: " + " ".join(extra)); bad += len(extra)
        from collections import Counter
        print(f"{len(N.comp)} parts in the netlist, {len(J)} csv rows, {bad} difference(s); status: "
              + ", ".join(f"{k} {v}" for k, v in Counter(j['status'] for j in J.values()).most_common()))
        groups = Counter((j["lcsc"], j["mpn"]) for j in J.values() if j["lcsc"])
        print(f"{len(groups)} different LCSC numbers; without LCSC number: "
              + " ".join(sorted((r for r, j in J.items() if not j['lcsc']), key=refkey)))
    elif cmd == "part":
        for r in ",".join(a).split(","):
            for fn in ("jlc_parts_next.csv", "part_map_next.csv", "footprint_map_next.csv"):
                with open(os.path.join(ROOT, "lib", fn)) as f:
                    for i, row in enumerate(csv.DictReader(l for l in f if not l.startswith("#"))):
                        if row["refdes"] == r:
                            print(f"lib/{fn}: " + "; ".join(f"{k}={v}" for k, v in row.items() if v))
    elif cmd == "cmp":
        O, s = Net(a[0]), N.sheet(a[1])
        here = {r for r, c in N.comp.items() if c["sheet"] == s}
        osheet = [t for t in O.sheets if t[:2] == s[:2]]
        there = {r for r, c in O.comp.items() if osheet and c["sheet"] == osheet[0]}
        print(f"== {s}: only in THIS netlist: {' '.join(sorted(here - set(O.comp), key=refkey)) or '-'}")
        print(f"== only in OTHER (same sheet number): {' '.join(sorted(there - set(N.comp), key=refkey)) or '-'}")
        moved = sorted((r for r in here & set(O.comp) if r not in there), key=refkey)
        if moved:
            print(f"== on another sheet in OTHER: {' '.join(moved)}")
        for r in sorted(here & set(O.comp), key=refkey):
            c, o = N.comp[r], O.comp[r]
            d = []
            if c["value"] != o["value"]:
                d.append(f"value {o['value']} -> {c['value']}")
            if c["fp"] != o["fp"]:
                a, b = o["fp"].split(":")[-1], c["fp"].split(":")[-1]
                d.append(f"fp {a} -> {b}" if a != b else f"fp library {o['fp'].split(':')[0]} -> {c['fp'].split(':')[0]} (same name {a})")
            for p in sorted(set(c["pins"]) | set(o["pins"]), key=pinkey):
                x, y = c["pins"].get(p, ("-",))[0], o["pins"].get(p, ("-",))[0]
                if x.rsplit("/", 1)[-1] != y.rsplit("/", 1)[-1]:
                    d.append(f"pin {p}: {y} -> {x}")
            if d:
                print(f"{r:8} " + "; ".join(d))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    import signal
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)   # quiet with | head
    main()
