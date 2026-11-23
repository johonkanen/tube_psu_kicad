#!/usr/bin/env python3
"""Stage 13d (one-shot, not re-runnable; run with tools/p2k/bin/kipy): primary <-> heater 8.0 -> 8.2 mm.

    tools/p2k/bin/kipy tools/next/route_s13d_heater_8v2.py [--dry-run OUT.kicad_pcb]

Design review 2026-11-23 (findings 10 A1 / F3): with HT_GND at the -100 V bias the primary <-> heater working voltage
is 410 Vrms (the DC shift adds linearly), reinforced creepage 8.2 mm (kicad_dru "PRI-HEATER ...", check_domains.py
LIMITS). About 25 places were at 8.03 - 8.19 mm. This stage
  1. moves three tracks north of ISO1 pin 16 (Net-(AD1-VA), heater) by 0.15 - 0.2 mm: the In2 5V and GND lanes
     (y -41.9 / -41.55 -> -41.80 / -41.48; the GND lane is held 3.2 mm from the PE pad C82.2), the B.Cu GPIO_BYPASS_RLY track (y -42.0 -> -41.8) with its via
     (-39.15, -45.3) -> (-39.0, -45.15) and the GND via (-41.7, -41.25) -> (-41.5, -41.05) that the GPIO track passes;
  2. refills, dumps the copper (check_domains.py --dump) and adds pour keep-outs (rule areas, no zone fill, one layer
     each) where an inner plane of one domain (In1 / In4 GND and HT_GND, In3 6V3) comes nearer than 8.2 mm (+ KO_MARGIN)
     in plan view to copper of the other domain on any layer: keep-out = plane fill (grown 0.1 mm) intersected with the
     other domain's copper grown by 8.2 + KO_MARGIN (system python3 + shapely, --ko mode of this script);
  3. refills again.
Record: kicad_next/routing/moves_s13d.json.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJ = os.path.join(ROOT, "kicad_next")
NAME = "tube_psu_5_2"
BOARD = os.path.join(PROJ, NAME + ".kicad_pcb")
CLI = os.path.join(ROOT, "tools", "p2k", "bin", "kicad-cli")
KIPY = os.path.join(ROOT, "tools", "p2k", "bin", "kipy")
REC = os.path.join(PROJ, "routing", "moves_s13d.json")
LIMIT, KO_MARGIN = 8.2, 0.07
PLANES = {"S2_In1_HT_GND_1": "HEATER", "S2_In4_HT_GND_1": "HEATER", "S2_In3_6V3_1": "HEATER",
          "S2_In1_GND_1": "PRI", "S2_In4_GND_1": "PRI"}

# (net, layer, start, end, width) to delete / add; vias: (net, old position, new position)
DELETE = [("5V", "In2.Signal_HV", (-38.5, -44.449), (-41.0, -41.949), 0.15),
          ("5V", "In2.Signal_HV", (-41.0, -41.9), (-48.6, -41.9), 0.15),
          ("5V", "In2.Signal_HV", (-48.6, -41.9), (-48.35, -40.6), 0.15),
          ("GND", "In2.Signal_HV", (-41.7, -41.25), (-42.0, -41.55), 0.15),
          ("GND", "In2.Signal_HV", (-42.0, -41.55), (-47.9, -41.55), 0.15),
          ("GND", "In2.Signal_HV", (-47.9, -41.55), (-47.95, -40.6), 0.15),
          ("GND", "B.Cu", (-37.6, -37.15), (-41.7, -41.25), 0.15),
          ("GPIO_BYPASS_RLY", "B.Cu", (-47.65, -39.8), (-45.45, -42.0), 0.2),
          ("GPIO_BYPASS_RLY", "B.Cu", (-45.45, -42.0), (-42.45, -42.0), 0.2),
          ("GPIO_BYPASS_RLY", "B.Cu", (-42.45, -42.0), (-39.15, -45.3), 0.2),
          ("GPIO_BYPASS_RLY", "In2.Signal_HV", (-39.15, -45.3), (-37.85, -45.3), 0.2)]
# In2 lanes: 5V >= 8.2 mm from ISO1.16 needs y >= -41.825, GND >= 3.2 mm from the PE pad C82.2 needs y <= -41.455,
# 0.15 mm between them (PRIMARY_LV inner): 5V -41.80, GND -41.48 (margins 0.025 / 0.025 / 0.02 mm)
ADD = [("5V", "In2.Signal_HV", (-38.5, -44.449), (-41.149, -41.8), 0.15),
       ("5V", "In2.Signal_HV", (-41.149, -41.8), (-48.6, -41.8), 0.15),
       ("5V", "In2.Signal_HV", (-48.6, -41.8), (-48.35, -40.6), 0.15),
       ("GND", "In2.Signal_HV", (-41.5, -41.05), (-41.93, -41.48), 0.15),
       ("GND", "In2.Signal_HV", (-41.93, -41.48), (-47.9, -41.48), 0.15),
       ("GND", "In2.Signal_HV", (-47.9, -41.48), (-47.95, -40.6), 0.15),
       ("GND", "B.Cu", (-37.6, -37.15), (-41.5, -41.05), 0.15),
       ("GPIO_BYPASS_RLY", "B.Cu", (-47.65, -39.8), (-45.65, -41.8), 0.2),
       ("GPIO_BYPASS_RLY", "B.Cu", (-45.65, -41.8), (-42.35, -41.8), 0.2),
       ("GPIO_BYPASS_RLY", "B.Cu", (-42.35, -41.8), (-39.0, -45.15), 0.2),
       ("GPIO_BYPASS_RLY", "In2.Signal_HV", (-39.0, -45.15), (-38.85, -45.3), 0.2),
       ("GPIO_BYPASS_RLY", "In2.Signal_HV", (-38.85, -45.3), (-37.85, -45.3), 0.2)]
VIAS = [("GPIO_BYPASS_RLY", (-39.15, -45.3), (-39.0, -45.15)),
        ("GND", (-41.7, -41.25), (-41.5, -41.05))]


def r2(p):
    return (round(p[0], 2), round(p[1], 2))


def edit_tracks(path):
    import pcbnew
    mm, MM = pcbnew.ToMM, pcbnew.FromMM
    b = pcbnew.LoadBoard(path)
    rec = dict(deleted=[], added=[], vias=[])
    for nn, lay, s, e, w in DELETE:
        hit = [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_TRACE_T and t.GetNetname() == nn
               and b.GetLayerName(t.GetLayer()) == lay and abs(mm(t.GetWidth()) - w) < 1e-3
               and {r2((mm(t.GetStart().x), mm(t.GetStart().y))), r2((mm(t.GetEnd().x), mm(t.GetEnd().y)))} == {r2(s), r2(e)}]
        if len(hit) != 1:
            sys.exit(f"s13d: segment {nn} {lay} {s} {e} found {len(hit)} times")
        b.Delete(hit[0])
        rec["deleted"].append(dict(net=nn, layer=lay, start=s, end=e, width=w))
    for nn, lay, s, e, w in ADD:
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(pcbnew.VECTOR2I(MM(s[0]), MM(s[1])))
        t.SetEnd(pcbnew.VECTOR2I(MM(e[0]), MM(e[1])))
        t.SetWidth(MM(w))
        t.SetLayer(b.GetLayerID(lay))
        t.SetNet(b.FindNet(nn))
        b.Add(t)
        rec["added"].append(dict(net=nn, layer=lay, start=s, end=e, width=w))
    for nn, old, new in VIAS:
        hit = [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() == nn
               and r2((mm(t.GetPosition().x), mm(t.GetPosition().y))) == r2(old)]
        if len(hit) != 1:
            sys.exit(f"s13d: via {nn} {old} found {len(hit)} times")
        hit[0].SetPosition(pcbnew.VECTOR2I(MM(new[0]), MM(new[1])))
        rec["vias"].append(dict(net=nn, old=old, new=new))
    for z in b.Zones():
        if not z.GetIsRuleArea():
            z.UnFill()
    pcbnew.SaveBoard(path, b)
    with open(os.path.join(os.path.dirname(path), "s13d_tracks.json"), "w") as f:
        json.dump(rec, f)


def keepouts(dump_json, pro, out_json):
    """system python3 + shapely: keep-out polygons for the planes in PLANES"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import check_domains as cd
    from shapely.geometry import LineString, Point, Polygon
    from shapely.ops import unary_union
    with open(dump_json) as f:
        g = json.load(f)
    with open(pro) as f:
        p = json.load(f)
    cls = {x["pattern"]: x["netclass"] for x in p["net_settings"]["netclass_patterns"]}
    dom = lambda n: cd.CLASS_DOMAIN.get(cls.get(n, ""), "")  # noqa: E731

    def mk(pp):
        return unary_union([Polygon(r, h).buffer(0) for r, h in pp])
    copper = {"PRI": [], "HEATER": []}
    for q in g["pads"]:
        d = dom(q["net"])
        if d in copper:
            copper[d].append(mk(q["polys"]))
    for t in g["tracks"]:
        d = dom(t["net"])
        if d in copper:
            x0, y0, x1, y1 = t["pts"]
            copper[d].append(LineString([(x0, y0), (x1, y1)]).buffer(t["w"] / 2) if (x0, y0) != (x1, y1)
                             else Point(x0, y0).buffer(t["w"] / 2))
    for v in g["vias"]:
        d = dom(v["net"])
        if d in copper:
            copper[d].append(Point(v["x"], v["y"]).buffer(v["d"] / 2))
    for z in g["zones"]:
        d = dom(z["net"])
        if d in copper:
            copper[d].append(mk(z["polys"]))
    grown = {d: unary_union(v).buffer(LIMIT + KO_MARGIN, 32) for d, v in copper.items()}
    other = {"PRI": "HEATER", "HEATER": "PRI"}
    out = []
    for z in g["zones"]:
        if z["name"] not in PLANES:
            continue
        fill = mk(z["polys"])
        ko = fill.buffer(0.1).intersection(grown[other[PLANES[z["name"]]]])
        ko = ko.buffer(0.02).buffer(-0.02).simplify(0.005)
        parts = [ko] if ko.geom_type == "Polygon" else list(getattr(ko, "geoms", []))
        for k in parts:
            if k.geom_type != "Polygon" or k.area < 1e-4:
                continue
            k = k.buffer(0.01)          # simplify / rounding margin
            out.append(dict(zone=z["name"], layer=z["layer"], area=round(k.area, 4),
                            pts=[[round(x, 4), round(y, 4)] for x, y in list(k.exterior.coords)[:-1]]))
    with open(out_json, "w") as f:
        json.dump(out, f)


def add_keepouts(path, ko_json):
    import pcbnew
    MM = pcbnew.FromMM
    b = pcbnew.LoadBoard(path)
    with open(ko_json) as f:
        kos = json.load(f)
    for i, k in enumerate(kos, 1):
        z = pcbnew.ZONE(b)
        z.SetIsRuleArea(True)
        z.SetLayer(b.GetLayerID(k["layer"]))
        z.SetDoNotAllowZoneFills(True)
        z.SetDoNotAllowTracks(False)
        z.SetDoNotAllowVias(False)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
        z.SetZoneName(f"S13D_KO PRI-HEATER 8.2 mm: {k['zone']} {i}")
        o = z.Outline()
        o.NewOutline()
        for x, y in k["pts"]:
            o.Append(pcbnew.VECTOR2I(MM(x), MM(y)))
        b.Add(z)
    for z in b.Zones():
        if not z.GetIsRuleArea():
            z.UnFill()
    pcbnew.SaveBoard(path, b)


def refill(tmp, pcb):
    r = subprocess.run([CLI, "pcb", "drc", "--format", "json", "--refill-zones", "--save-board",
                        "-o", os.path.join(tmp, "refill.json"), pcb], capture_output=True, text=True)
    if r.returncode:
        sys.exit("s13d: zone refill failed, the board is unchanged\n" + r.stdout[-1500:] + r.stderr[-1500:])


def main(argv):
    if "--edit" in argv:
        return edit_tracks(argv[argv.index("--edit") + 1])
    if "--ko" in argv:
        i = argv.index("--ko")
        return keepouts(argv[i + 1], argv[i + 2], argv[i + 3])
    if "--add" in argv:
        i = argv.index("--add")
        return add_keepouts(argv[i + 1], argv[i + 2])
    if os.path.exists(os.path.join(PROJ, "~" + NAME + ".kicad_pcb.lck")):
        sys.exit("s13d: the board is open in KiCad; close it first")
    dry = "--dry-run" in argv
    if not dry and os.path.exists(REC):
        sys.exit("s13d: already on the board (not re-runnable)")
    tmp = tempfile.mkdtemp(prefix=".s13d_", dir=ROOT)
    try:
        shutil.copy(os.path.join(PROJ, NAME + ".kicad_dru"), tmp)
        pcb = os.path.join(tmp, NAME + ".kicad_pcb")
        shutil.copy(BOARD, pcb)
        with open(os.path.join(PROJ, NAME + ".kicad_pro")) as f:
            pro = json.load(f)
        with open(os.path.join(tmp, "classes.kicad_pro"), "w") as f:
            json.dump(pro, f)                      # net classes for the keep-out step
        rs = pro["board"]["design_settings"]["rule_severities"]
        for k in rs:
            rs[k] = "ignore"                       # refill only
        with open(os.path.join(tmp, NAME + ".kicad_pro"), "w") as f:
            json.dump(pro, f, indent=2)
        me = os.path.abspath(__file__)
        if subprocess.run([sys.executable, "-u", me, "--edit", pcb]).returncode:
            sys.exit("s13d: track edit failed, the board is unchanged")
        refill(tmp, pcb)
        js, ko = os.path.join(tmp, "g.json"), os.path.join(tmp, "ko.json")
        r = subprocess.run([KIPY, os.path.join(ROOT, "tools", "next", "check_domains.py"), "--dump", pcb, js],
                           capture_output=True, text=True)
        if r.returncode or not os.path.exists(js):
            sys.exit("s13d: dump failed\n" + r.stderr[-1500:])
        env = {k: v for k, v in os.environ.items() if k not in ("PYTHONHOME", "PYTHONPATH", "LD_LIBRARY_PATH")}
        if subprocess.run(["python3", me, "--ko", js, os.path.join(tmp, "classes.kicad_pro"), ko], env=env).returncode:
            sys.exit("s13d: keep-out step failed (system python3 with shapely)")
        if subprocess.run([sys.executable, "-u", me, "--add", pcb, ko]).returncode:
            sys.exit("s13d: adding the keep-outs failed")
        refill(tmp, pcb)
        with open(os.path.join(tmp, "s13d_tracks.json")) as f:
            rec = json.load(f)
        with open(ko) as f:
            rec["keepouts"] = json.load(f)
        print(f"s13d: {len(rec['deleted'])} segments replaced by {len(rec['added'])}, {len(rec['vias'])} vias moved, "
              f"{len(rec['keepouts'])} keep-outs: " + ", ".join(f"{k['zone']} {k['area']:.3f} mm2" for k in rec["keepouts"]))
        if dry:
            shutil.copy(pcb, os.path.abspath(argv[argv.index("--dry-run") + 1]))
        else:
            shutil.copy(pcb, BOARD)
            with open(REC, "w") as f:
                json.dump(rec, f, indent=1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
