#!/usr/bin/env python3
"""Independent cross-check of a JLCPCB file set in kicad_next/fab/ against the board and the parts table.

    python3 kicad_next/review/tools/fab_check.py [FAB_DIR]        (default kicad_next/fab; read-only, plain python3)

Needs the board dump: kicad_next/review/tools/rv setup. It does NOT use tools/next/jlc_fab.py, so it is a second
opinion on that script's output. What it prints (it never fails on purpose - read the lines marked "!!"):

  files      what is in the directory by kind (copper / mask / paste / silk / outline / drill / BOM / CPL / zip),
             the zip members against the files on disk (same names and sizes?), anything that looks like silkscreen
  age        is any fab file older than the board file or the parts table?
  drill      holes per diameter in the Excellon files against the board (vias + plated pad holes; NPTH = mounting
             holes), positions compared in the frame X = board x, Y = -board y; slots (routed holes) reported
  outline    number of draw operations in the Edge.Cuts Gerber and the bounding box against the board outline
  cpl        every CPL row against the board footprint: position (footprint anchor, Y negated), side, rotation as
             stored in the board (differences of +-90 / 180 may be deliberate JLC rotation corrections - listed)
  bom        every BOM designator against lib/jlc_parts_next.csv (LCSC number), designators in the BOM but not
             in the CPL and vice versa, board parts in neither (must all be explained by NOT_ASSEMBLED / DNP /
             consigned / missing / board-only)
"""
import collections
import csv
import glob
import json
import os
import re
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
BOARD = os.path.join(ROOT, "kicad_next", "tube_psu_5_2.kicad_pcb")
TABLE = os.path.join(ROOT, "lib", "jlc_parts_next.csv")


def refkey(r):
    head = r.rstrip("0123456789")
    return (head, int(r[len(head):] or 0))


def kind(name):
    n = name.lower()
    if n.endswith((".gtl", ".gbl")) or re.search(r"\.g\d+$", n) or re.search(r"\.gl\d+$", n) or "_cu." in n:
        return "copper"
    if n.endswith((".gts", ".gbs")) or "mask" in n:
        return "mask"
    if n.endswith((".gtp", ".gbp")) or "paste" in n:
        return "paste"
    if n.endswith((".gto", ".gbo")) or "silk" in n:
        return "SILK"
    if n.endswith((".gm1", ".gko")) or "edge" in n:
        return "outline"
    if n.endswith(".drl"):
        return "drill"
    if n.endswith(".zip"):
        return "zip"
    if n.endswith(".csv"):
        return "bom" if "bom" in n else "cpl" if ("cpl" in n or "pos" in n) else "csv"
    return "other"


def excellon(path):
    tools, cur, hits, slots = {}, None, [], 0
    for line in open(path):
        line = line.strip()
        m = re.match(r"T(\d+)C([\d.]+)", line)
        if m:
            tools[m.group(1)] = float(m.group(2))
            continue
        m = re.match(r"T(\d+)$", line)
        if m:
            cur = m.group(1)
            continue
        m = re.match(r"X(-?[\d.]+)Y(-?[\d.]+)(G85X(-?[\d.]+)Y(-?[\d.]+))?", line)
        if m and cur:
            if m.group(3):
                slots += 1
                hits.append((tools[cur], (float(m.group(1)) + float(m.group(4))) / 2, (float(m.group(2)) + float(m.group(5))) / 2, True))
            else:
                hits.append((tools[cur], float(m.group(1)), float(m.group(2)), False))
    return hits, slots


def main():
    fab = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "kicad_next", "fab")
    if not os.path.isdir(fab):
        sys.exit(f"{fab}: no such directory (the fab package does not exist yet)")
    cache = subprocess.check_output([os.path.join(HERE, "rv"), "dir"], text=True).strip()
    dump = os.path.join(cache, "b52.json")
    if not os.path.exists(dump):
        sys.exit("board dump missing: run kicad_next/review/tools/rv setup")
    d = json.load(open(dump))
    fps = {f["ref"]: f for f in d["footprints"]}
    table = {r["refdes"]: r for r in csv.DictReader(l for l in open(TABLE) if not l.startswith("#"))}

    # ---- files
    files = sorted(os.listdir(fab))
    by = collections.defaultdict(list)
    for f in files:
        by[kind(f)].append(f)
    print("== files")
    for k in ("copper", "mask", "paste", "SILK", "outline", "drill", "zip", "bom", "cpl", "csv", "other"):
        if by[k]:
            print(f"   {k:8} {len(by[k])}: {' '.join(by[k])}")
    if len(by["copper"]) != len(d["layers"]):
        print(f"!! {len(by['copper'])} copper Gerbers for a board with {len(d['layers'])} copper layers {d['layers']}")
    if by["SILK"]:
        print("!! silkscreen files present (the board is ordered without silkscreen)")
    for z in by["zip"]:
        with zipfile.ZipFile(os.path.join(fab, z)) as zf:
            names = {i.filename: i.file_size for i in zf.infolist()}
        print(f"   {z}: {len(names)} members")
        for n, size in sorted(names.items()):
            p = os.path.join(fab, n)
            if not os.path.exists(p):
                print(f"!!    {n} is in the zip but not in the directory")
            elif os.path.getsize(p) != size:
                print(f"!!    {n}: size in the zip {size} != on disk {os.path.getsize(p)} (zip is stale?)")
            if kind(n) in ("SILK", "bom", "cpl", "other"):
                print(f"!!    {n}: unexpected kind '{kind(n)}' inside the Gerber zip")
        need = set(by["copper"] + by["mask"] + by["outline"] + by["drill"])
        for n in sorted(need - set(names)):
            print(f"!!    {n} is not in the zip")

    # ---- age
    print("== age")
    src = max(os.path.getmtime(BOARD), os.path.getmtime(TABLE))
    old = [f for f in files if os.path.getmtime(os.path.join(fab, f)) < src]
    print("   every fab file is newer than the board and the parts table" if not old else
          f"!! older than the board / parts table (regenerate): {' '.join(old)}")

    # ---- drill
    print("== drill (frame: X = board x, Y = -board y)")
    want_pth = collections.Counter()
    want_npth = collections.Counter()
    pos_pth, pos_npth = [], []
    for h in d["holes"]:
        (want_pth if h["plated"] else want_npth)[round(h["d"], 3)] += 1
        (pos_pth if h["plated"] else pos_npth).append((h["x"], -h["y"], h["d"], h["ref"]))
    for f in by["drill"]:
        hits, slots = excellon(os.path.join(fab, f))
        got = collections.Counter(round(h[0], 3) for h in hits)
        npth = "npth" in f.lower() or "non" in f.lower()
        want = want_npth if npth else want_pth
        print(f"   {f}: {len(hits)} hits, {slots} routed slots; board: {sum(want.values())} {'non-plated' if npth else 'plated'} holes")
        for dia in sorted(set(got) | set(want)):
            flag = "  " if got[dia] == want[dia] else "!!"
            print(f"{flag}    d {dia:6.3f}: file {got[dia]:4}  board {want[dia]:4}")
        pts = pos_npth if npth else pos_pth
        hitset = collections.defaultdict(list)
        for dia, x, y, _ in hits:
            hitset[(round(x, 1), round(y, 1))].append((x, y, dia))
        miss = 0
        for x, y, dia, ref in pts:
            near = [h for dx in (-0.1, 0, 0.1) for dy in (-0.1, 0, 0.1) for h in hitset.get((round(x + dx, 1), round(y + dy, 1)), [])
                    if abs(h[0] - x) < 0.02 and abs(h[1] - y) < 0.02]
            if not near:
                miss += 1
                if miss <= 8:
                    print(f"!!    no hit at ({x:.3f}, {y:.3f}) d {dia} for {ref}")
        print(f"   {len(pts) - miss} of {len(pts)} board holes found at their position in {f}")

    # ---- outline
    print("== outline")
    x0, y0, x1, y1 = d["outline"]
    for f in by["outline"]:
        txt = open(os.path.join(fab, f)).read()
        m = re.search(r"%FSLAX(\d)(\d)Y", txt)
        div = 10 ** int(m.group(2)) if m else 1e6
        xs = [int(v) / div for v in re.findall(r"X(-?\d+)", txt)]
        ys = [int(v) / div for v in re.findall(r"Y(-?\d+)", txt)]
        print(f"   {f}: {len(re.findall(r'D01', txt))} draws, {len(re.findall(r'G0[23]', txt))} arcs; box x {min(xs):.2f} .. {max(xs):.2f}, "
              f"y {min(ys):.2f} .. {max(ys):.2f}")
        print(f"   board outline box x {x0} .. {x1}, y(negated) {-y1} .. {-y0}; internal Edge.Cuts items in the board: "
              f"{len(d['edge'])} (slots: kicad_next/review/tools/rv bq slots)")

    # ---- CPL
    print("== cpl")
    cpl = {}
    for f in by["cpl"]:
        for r in csv.DictReader(open(os.path.join(fab, f))):
            cpl[r["Designator"]] = r
        print(f"   {f}: {len(cpl)} rows, columns {list(r.keys())}")
    bad = 0
    rots = collections.Counter()
    for ref, r in sorted(cpl.items(), key=lambda x: refkey(x[0])):
        f = fps.get(ref)
        if f is None:
            print(f"!!    {ref}: in the CPL, not on the board")
            continue
        x, y = float(r["Mid X"].replace("mm", "")), float(r["Mid Y"].replace("mm", ""))
        side = "F" if r["Layer"].lower().startswith("t") else "B"
        if abs(x - f["x"]) > 0.01 or abs(y + f["y"]) > 0.01 or side != f["side"]:
            bad += 1
            if bad <= 15:
                print(f"!!    {ref}: CPL ({x}, {y}) {r['Layer']}  board anchor ({f['x']}, {-f['y']}) side {f['side']}")
        dr = (float(r["Rotation"]) - f["rot"]) % 360
        rots[round(dr) % 360] += 1
    print(f"   {len(cpl) - bad} of {len(cpl)} CPL rows at the board footprint anchor (X = x, Y = -y) on the right side")
    print(f"   CPL rotation minus board rotation (deg: count): {dict(sorted(rots.items()))}  "
          "(all 0 = raw KiCad angles, no JLC rotation corrections applied)")

    # ---- BOM
    print("== bom")
    bom = {}
    for f in by["bom"]:
        rows = list(csv.DictReader(open(os.path.join(fab, f))))
        for r in rows:
            for ref in r["Designator"].split(","):
                bom[ref.strip()] = r
        print(f"   {f}: {len(rows)} lines, {len(bom)} designators, columns {list(rows[0].keys()) if rows else []}")
    lcol = next((c for c in (list(next(iter(bom.values())).keys()) if bom else []) if "lcsc" in c.lower()), None)
    for ref, r in sorted(bom.items(), key=lambda x: refkey(x[0])):
        t = table.get(ref)
        if t is None:
            print(f"!!    {ref}: in the BOM, not in lib/jlc_parts_next.csv")
        elif lcol and r[lcol] != t["lcsc"]:
            print(f"!!    {ref}: BOM {r[lcol]!r} != table {t['lcsc']!r}")
        elif t["status"] in ("dnp", "missing", "consigned"):
            print(f"!!    {ref}: in the BOM although its table status is {t['status']}")
    only_bom, only_cpl = sorted(set(bom) - set(cpl), key=refkey), sorted(set(cpl) - set(bom), key=refkey)
    if only_bom:
        print(f"!!    in the BOM, not in the CPL: {' '.join(only_bom)}")
    if only_cpl:
        print(f"!!    in the CPL, not in the BOM: {' '.join(only_cpl)}")
    rest = sorted(set(fps) - set(bom), key=refkey)
    groups = collections.defaultdict(list)
    for ref in rest:
        t = table.get(ref)
        groups["board-only (no table row)" if t is None else f"status {t['status']}" + ("" if t["lcsc"] else ", no LCSC")].append(ref)
    print(f"   {len(rest)} board footprints are not in the BOM:")
    for g, refs in sorted(groups.items()):
        flag = "!!" if g.startswith(("status exact", "status equivalent", "status changed")) and "no LCSC" not in g else "  "
        print(f"{flag}    {g} ({len(refs)}): {' '.join(refs)}")
    tht = [ref for ref in bom if ref in fps and any(p["drill"] for p in fps[ref]["pads"])]
    print(f"   through-hole parts in the BOM ({len(tht)}): {' '.join(sorted(tht, key=refkey))}")
    for side in "FB":
        print(f"   SMD parts in the BOM on side {side}: {sum(1 for ref in bom if ref in fps and fps[ref]['side'] == side and ref not in tht)}")


if __name__ == "__main__":
    main()
