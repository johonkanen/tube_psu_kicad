#!/usr/bin/env python3
"""Netlist diff 5.1 -> 5.2 and CSV coverage check of the 5.2 schematic.

    python3 tools/next/netlist_diff.py            print the diff (markdown) and the CSV check
    python3 tools/next/netlist_diff.py --update   also rewrite the generated section of kicad_next/CHANGES_5_2.md
    python3 tools/next/netlist_diff.py --check    fail if the CSV check finds a problem or CHANGES_5_2.md is stale

Both netlists come from kicad-cli (sch export netlist, kicadxml) of kicad/tube_psu.kicad_sch (5.1, frozen)
and kicad_next/tube_psu_5_2.kicad_sch. Parts are matched by refdes (added / removed / value, symbol or
footprint changed). Nets are compared as sets of (refdes, pin): a 5.2 net is matched to the 5.1 net it
has the same name as, else to the one it shares the most pins of unchanged parts with, so a net that only
got a new auto-name is reported as renamed, not as removed + added; the report
lists removed and added nets and, for matched nets, the pins that joined or left (pins of removed / added
parts are summarised per part instead). CSV check: every 5.2 part has a row in lib/part_map_next.csv,
lib/footprint_map_next.csv and lib/jlc_parts_next.csv with the schematic value and footprint, and no CSV row
is left for a part that is no longer in the schematic.
"""
import collections
import csv
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CLI = os.path.join(ROOT, "tools", "p2k", "bin", "kicad-cli")
SCH51 = os.path.join(ROOT, "kicad", "tube_psu.kicad_sch")
SCH52 = os.path.join(ROOT, "kicad_next", "tube_psu_5_2.kicad_sch")
CHANGES = os.path.join(ROOT, "kicad_next", "CHANGES_5_2.md")
BEGIN, END = "<!-- netlist_diff.py begin -->", "<!-- netlist_diff.py end -->"


def netlist(sch):
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "net.xml")
        subprocess.run([CLI, "sch", "export", "netlist", "--format", "kicadxml", "-o", out, sch],
                       check=True, capture_output=True)
        t = ET.parse(out)
    parts = {}
    for c in t.find("components"):
        ref = c.get("ref")
        if ref.startswith("#"):
            continue
        lib = c.find("libsource")
        parts[ref] = {"value": (c.findtext("value") or ""), "footprint": (c.findtext("footprint") or ""),
                      "symbol": lib.get("part") if lib is not None else ""}
    nets = {}
    for n in t.find("nets"):
        pins = frozenset((nd.get("ref"), nd.get("pin")) for nd in n.findall("node") if not nd.get("ref").startswith("#"))
        if pins:
            nets[n.get("name")] = pins
    return parts, nets


def short(name):
    return name.rsplit("/", 1)[-1] if name.startswith("/") else name


def diff(p51, n51, p52, n52):
    out = []
    removed = sorted(set(p51) - set(p52), key=sortkey)
    added = sorted(set(p52) - set(p51), key=sortkey)
    out.append(f"Parts: 5.1 {len(p51)}, 5.2 {len(p52)}; removed {len(removed)}, added {len(added)}.\n")
    out.append("**Removed parts:** " + (", ".join(f"{r} ({p51[r]['value']})" for r in removed) or "none") + "\n")
    out.append("**Added parts:** " + (", ".join(f"{r} ({p52[r]['value']})" for r in added) or "none") + "\n")
    out.append("**Changed parts** (value / symbol / footprint, 5.1 -> 5.2):\n")
    out.append("| Ref | Value | Symbol | Footprint |\n|---|---|---|---|")
    for r in sorted(set(p51) & set(p52), key=sortkey):
        a, b = p51[r], p52[r]
        if a == b:
            continue
        cell = lambda k: f"{a[k]} -> {b[k]}" if a[k] != b[k] else ""
        out.append(f"| {r} | {cell('value')} | {cell('symbol')} | {cell('footprint').replace('|', '/')} |")
    out.append("")
    # nets: same name first; the rest is matched to the unmatched 5.1 net with the largest overlap of
    # "stable" pins (parts in both revisions with the same symbol, so pin numbers mean the same)
    gone_parts, new_parts = set(removed), set(added)
    stable = {r for r in set(p51) & set(p52) if p51[r]["symbol"] == p52[r]["symbol"]}
    matched = {n: n for n in n52 if n in n51}
    free51 = set(n51) - set(matched)
    by_pin51 = {p: n for n in free51 for p in n51[n] if p[0] in stable}
    new_nets = []
    for n, ps in n52.items():
        if n in matched:
            continue
        cnt = collections.Counter(by_pin51[p] for p in ps if p in by_pin51)
        if cnt:
            matched[n] = cnt.most_common(1)[0][0]
        else:
            new_nets.append(n)
    used51 = set(matched.values())
    lost_nets = sorted(n for n in n51 if n not in used51)
    renamed, changed = [], []
    for n, m in sorted(matched.items(), key=lambda x: short(x[0])):
        a, b = n51[m], n52[n]
        join = sorted((p for p in b - a if p[0] not in new_parts), key=pinkey)
        leave = sorted((p for p in a - b if p[0] not in gone_parts), key=pinkey)
        newp = sorted({p[0] for p in b - a if p[0] in new_parts}, key=sortkey)
        gonep = sorted({p[0] for p in a - b if p[0] in gone_parts}, key=sortkey)
        if short(n) != short(m):
            renamed.append(f"{m} -> {n}")
        if join or leave or newp or gonep:
            bits = []
            if join:
                bits.append("+" + " ".join(f"{r}.{p}" for r, p in join))
            if leave:
                bits.append("-" + " ".join(f"{r}.{p}" for r, p in leave))
            if newp:
                bits.append("new parts " + " ".join(newp))
            if gonep:
                bits.append("removed parts " + " ".join(gonep))
            name = n if short(n) == short(m) else f"{m} -> {n}"
            changed.append(f"| {name} | {'; '.join(bits)} |")
    dup = [m for m, c in collections.Counter(matched.values()).items() if c > 1]
    out.append(f"Nets: 5.1 {len(n51)}, 5.2 {len(n52)} (with at least one part pin).\n")
    out.append("**5.1 nets gone** (no pin left in any 5.2 net): " + (", ".join(lost_nets) or "none") + "\n")
    out.append("**New 5.2 nets** (only new part pins): " + (", ".join(sorted(new_nets, key=short)) or "none") + "\n")
    if dup:
        out.append("**5.1 nets split in 5.2:** " + ", ".join(sorted(dup)) + "\n")
    out.append("**Renamed nets** (same pins, new name): " + ("; ".join(renamed) or "none") + "\n")
    out.append("**Changed connections** (+ pin joined, - pin left; pins of added / removed parts summarised):\n")
    out.append("| Net (5.2) | Change |\n|---|---|")
    out += changed
    out.append("")
    return "\n".join(out)


def sortkey(r):
    import re
    m = re.match(r"([A-Z_]+)(\d+)$", r)
    return (m.group(1), int(m.group(2))) if m else (r, 0)


def pinkey(p):
    return (sortkey(p[0]), p[1])


def csv_check(p52):
    def rows(name):
        with open(os.path.join(ROOT, "lib", name), newline="", encoding="utf-8") as f:
            return {r["refdes"]: r for r in csv.DictReader(l for l in f if not l.startswith("#"))}
    pm, fm, jl = rows("part_map_next.csv"), rows("footprint_map_next.csv"), rows("jlc_parts_next.csv")
    problems = []
    for r, p in sorted(p52.items(), key=lambda x: sortkey(x[0])):
        for name, tab in (("part_map_next", pm), ("footprint_map_next", fm), ("jlc_parts_next", jl)):
            if r not in tab:
                problems.append(f"{r}: no row in {name}.csv")
        if r in pm and pm[r]["value"] != p["value"]:
            problems.append(f"{r}: schematic value {p['value']!r} != part_map_next {pm[r]['value']!r}")
        if r in fm and fm[r]["footprint"] != p["footprint"]:
            problems.append(f"{r}: schematic footprint {p['footprint']!r} != footprint_map_next {fm[r]['footprint']!r}")
        if r in jl and r in fm and jl[r]["footprint"] != fm[r]["footprint"]:
            problems.append(f"{r}: jlc_parts_next footprint {jl[r]['footprint']!r} != footprint_map_next")
    for name, tab in (("part_map_next", pm), ("footprint_map_next", fm), ("jlc_parts_next", jl)):
        for r in sorted(set(tab) - set(p52), key=sortkey):
            problems.append(f"{r}: row in {name}.csv but not in the schematic")
    return problems


def main(argv):
    p51, n51 = netlist(SCH51)
    p52, n52 = netlist(SCH52)
    text = diff(p51, n51, p52, n52)
    problems = csv_check(p52)
    for pr in problems:
        print("netlist_diff: CSV: " + pr, file=sys.stderr)
    section = f"{BEGIN}\n{text}\n{END}"
    doc = open(CHANGES, encoding="utf-8").read() if os.path.exists(CHANGES) else ""
    if "--update" in argv:
        if BEGIN in doc:
            doc = doc[:doc.index(BEGIN)] + section + doc[doc.index(END) + len(END):]
        else:
            doc += "\n" + section + "\n"
        with open(CHANGES, "w", encoding="utf-8") as f:
            f.write(doc)
        print("netlist_diff: updated kicad_next/CHANGES_5_2.md")
    elif "--check" in argv:
        stale = section not in doc
        if stale:
            print("netlist_diff: kicad_next/CHANGES_5_2.md netlist section is stale (run tools/next/netlist_diff.py --update)")
        print(f"netlist_diff: {len(p52)} parts, CSV check {'OK' if not problems else str(len(problems)) + ' problems'}")
        return 1 if stale or problems else 0
    else:
        print(text)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
