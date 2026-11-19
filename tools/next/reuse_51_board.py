#!/usr/bin/env python3
"""TRIAL 5.2 board that reuses the verified 5.1 placement and routing (run with tools/p2k/bin/kipy).

    tools/p2k/bin/kipy tools/next/reuse_51_board.py            build, refill + DRC, dump, report
    tools/p2k/bin/kipy tools/next/reuse_51_board.py --no-report  skip tools/next/trial_report.py

Output (kicad_next/trial_from_51/, a separate KiCad project; kicad_next/tube_psu_5_2.kicad_pcb is not
touched and tools/next/check_next.sh does not look at it):
    tube_psu_5_2_trial.kicad_pcb / .kicad_pro / .kicad_dru   board + copies of the 5.2 project / rules
    drc.json                       kicad-cli pcb drc --severity-all after a refill with the 5.2 rules, run in
                                   memory-bounded passes (run_drc; peak < 2.6 GB each)
    drc_51.json                    the same DRC of kicad/tube_psu.kicad_pcb with its own rules (baseline)
    build.json                     what this script did (footprints, nets, deleted copper, geometry
                                   for the report drawings)
    REPORT.md, *.png               tools/next/trial_report.py (system python, matplotlib)

Steps:
 1. kicad/tube_psu.kicad_pcb is loaded; the copper becomes 6 layers with the names / types and the
    JLC06161H-3313 stackup of make_board.py. 5.1 layer mapping (LAYER_MAP): F.Cu -> F.Cu,
    In1 -> In1.GND (L2), In2 -> In4.GND (L5), B.Cu -> B.Cu; In2.Signal_HV / In3.Power (L3 / L4) stay
    empty. Reason: 5.1 In1 is mostly GND planes (131 mm of track) and In2 carries 2 m of routing next
    to B.Cu; JLC's 4-layer stack has In1 / In2 one thin prepreg below F.Cu / above B.Cu, which is
    exactly where L2 / L5 sit in the 6-layer stack (0.0994 mm 3313 each), so every 5.1 layer keeps its
    reference plane distance to its outer layer, the copper stays symmetric about the centre (no
    bow / twist from an unbalanced build) and the free pair L3 / L4 is the adjacent 0.11 mm-prepreg
    pair in the middle - the natural place for the later signal / power-pour rework.
 2. Outline and H1-H8 are the 5.1 items (checked against kicad_next/tube_psu_5_2.kicad_pcb).
 3. Footprints by refdes against the 5.2 netlist (kicad-cli sch export netlist):
      unchanged footprint ID           kept as is (position, orientation, tracks)
      new ID, same pads (library copy with a 3D model / real can height)   replaced by the 5.2
                                       footprint at the same place; pad positions verified, tracks kept
      new ID, different pads ("changed")  5.2 footprint at the old position / rotation / side (rotation
                                       overridden by NEW_ORIENTATION: L1 / L2 upright toroids at 0 deg)
      not in 5.2 (removed)             deleted (board-only footprints WP1-WP4 are kept and re-netted)
      new in 5.2 (added)               placed off-board below the outline, one row block per sheet
    Every pad gets the net of the 5.2 netlist (renamed nets follow), fields value / path / sheet too.
 4. Copper: old net -> new net by the pads of kept footprints (majority; identical name preferred).
    Deleted: tracks / vias whose net has no 5.2 counterpart, and every segment / via that touches a
    pad of a changed or removed footprint or a pad whose 5.2 net differs from the mapped track net -
    except at a pad of a changed footprint that has a new pad at the same place with the mapped net
    (L1 / L2: the toroid leads sit in the RM8 winding holes, their tracks stay).
Placement step 1 (TR3, split caps, DRV5 / DRV6 groups) is tools/next/trial_placement.py on this board.
    Zones are kept and re-netted the same way (zones without a 5.2 net are deleted); kicad-cli refills
    them with the 5.2 rules (net classes of the copied .kicad_pro, clearances of the .kicad_dru).
"""
import collections
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import make_board  # noqa: E402  (COPPER, STACKUP, outline(), holes())

SRC = os.path.join(ROOT, "kicad", "tube_psu.kicad_pcb")
SHELL = os.path.join(ROOT, "kicad_next", "tube_psu_5_2.kicad_pcb")
PROJ = os.path.join(ROOT, "kicad_next")
SCH = os.path.join(PROJ, "tube_psu_5_2.kicad_sch")
OUTDIR = os.path.join(PROJ, "trial_from_51")
NAME = "tube_psu_5_2_trial"
OUT = os.path.join(OUTDIR, NAME + ".kicad_pcb")
CLI = os.path.join(ROOT, "tools", "p2k", "bin", "kicad-cli")
MOUNT = os.environ.get("KICAD_MOUNT", "")
KICAD_FP = os.path.join(MOUNT, "share", "kicad", "footprints")
LIBS = {"tube_psu": "lib/tube_psu.pretty", "tube_psu_next": "lib/tube_psu_next.pretty",
        "tube_psu_next_parts": "lib/tube_psu_next_parts.pretty"}
HOLES = set(make_board.HOLES)

# 5.1 layer -> 6-layer board (see docstring; applied in remap_layers: only In2 moves)
LAYER_MAP = {pcbnew.F_Cu: pcbnew.F_Cu, pcbnew.In1_Cu: pcbnew.In1_Cu, pcbnew.In2_Cu: pcbnew.In4_Cu,
             pcbnew.B_Cu: pcbnew.B_Cu}
MM = 1e6
TOL = 2000  # nm, pad position / size match of library copies
# changed footprints placed at another orientation than the 5.1 part (default: the 5.1 orientation).
# L1 / L2: the upright-toroid footprints are drawn in board orientation with origin = the 5.1 RM8 origin;
# at 0 deg their pads 1 / 2 land on the RM8 winding holes pri1 / pri2 (lib: gen_next_footprints.py TOROID_V)
NEW_ORIENTATION = {"L1": 0.0, "L2": 0.0}


# 5.1 refdes -> 5.2 refdes (NR 1.13: the -5 V terminal became the -15 V terminal)
REF_RENAME_51 = {"N5V_OUT": "N15V_OUT"}

def mm(v):
    return round(v / MM, 3)


# --- netlist ------------------------------------------------------------------------------------------
def netlist():
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "net.xml")
        subprocess.run([CLI, "sch", "export", "netlist", "--format", "kicadxml", "-o", out, SCH],
                       check=True, capture_output=True)
        t = ET.parse(out)
    comps = {}
    for c in t.find("components"):
        props = {p.get("name"): p.get("value") for p in c.findall("property")}
        sp = c.find("sheetpath")
        comps[c.get("ref")] = dict(fpid=c.findtext("footprint") or "", value=c.findtext("value") or "",
                                   sheet=props.get("Sheetname", ""), sheetfile=props.get("Sheetfile", ""),
                                   path=sp.get("tstamps") + c.findtext("tstamps"),
                                   lcsc=props.get("LCSC", ""))
    pins, nets = collections.defaultdict(dict), []
    for n in t.find("nets"):
        nets.append(n.get("name"))
        for nd in n.findall("node"):
            pins[nd.get("ref")][nd.get("pin")] = n.get("name")
    return comps, pins, nets


def load_fp(fpid):
    lib, name = fpid.split(":", 1)
    path = os.path.join(ROOT, LIBS[lib]) if lib in LIBS else os.path.join(KICAD_FP, lib + ".pretty")
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        sys.exit(f"reuse_51_board: cannot load footprint {fpid} ({path})")
    fp.SetFPID(pcbnew.LIB_ID(pcbnew.UTF8(lib), pcbnew.UTF8(name)))
    return fp


def pad_sig(fp):
    """pad number -> list of (x, y, size x, size y, drill x, drill y) in board coordinates"""
    out = collections.defaultdict(list)
    for p in fp.Pads():
        out[p.GetNumber()].append((p.GetPosition().x, p.GetPosition().y, p.GetSizeX(), p.GetSizeY(),
                                   p.GetDrillSizeX(), p.GetDrillSizeY()))
    return {k: sorted(v) for k, v in out.items()}


def same_pads(a, b):
    if set(a) != set(b):
        return False
    for k in a:
        if len(a[k]) != len(b[k]):
            return False
        for u, v in zip(a[k], b[k]):
            if any(abs(x - y) > TOL for x, y in zip(u, v)):
                return False
    return True


# --- board -----------------------------------------------------------------------------------------
def remap_layers(b):
    """4 -> 6 copper layers: move In2 items to In4, then names / types of make_board.COPPER."""
    b.SetCopperLayerCount(6)
    ls = b.GetEnabledLayers()
    for layer, _, _ in make_board.COPPER:
        ls.AddLayer(layer)
    b.SetEnabledLayers(ls)
    moved = collections.Counter()
    for t in b.GetTracks():
        if t.Type() != pcbnew.PCB_VIA_T and t.GetLayer() == pcbnew.In2_Cu:
            t.SetLayer(pcbnew.In4_Cu)
            moved["tracks"] += 1
    for z in b.Zones():
        ls = z.GetLayerSet()
        if ls.Contains(pcbnew.In2_Cu):
            ls.RemoveLayer(pcbnew.In2_Cu)
            ls.AddLayer(pcbnew.In4_Cu)
            z.SetLayerSet(ls)
            moved["zones"] += 1
    for d in b.GetDrawings():
        if d.GetLayer() == pcbnew.In2_Cu:
            d.SetLayer(pcbnew.In4_Cu)
            moved["drawings"] += 1
    for fp in b.GetFootprints():
        for item in list(fp.GraphicalItems()):
            if item.GetLayer() == pcbnew.In2_Cu:
                item.SetLayer(pcbnew.In4_Cu)
                moved["fp graphics"] += 1
        for p in fp.Pads():
            ls = p.GetLayerSet()
            # SMD / custom pads restricted to In2 (none expected); through-hole pads use all copper
            if ls.Contains(pcbnew.In2_Cu) and not ls.Contains(pcbnew.In1_Cu):
                ls.RemoveLayer(pcbnew.In2_Cu)
                ls.AddLayer(pcbnew.In4_Cu)
                p.SetLayerSet(ls)
                moved["pads"] += 1
    for layer, name, ltype in make_board.COPPER:
        b.SetLayerName(layer, name)
        b.SetLayerType(layer, ltype)
    b.GetDesignSettings().SetBoardThickness(pcbnew.FromMM(1.6))
    return dict(moved)


def replace_fp(b, old, fpid, ref):
    new = load_fp(fpid)
    b.Add(new)  # on the board before Flip (pcbnew 10)
    pos = old.GetPosition()
    new.SetPosition(pos)
    if old.IsFlipped():
        new.Flip(pos, pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    if ref in NEW_ORIENTATION:
        new.SetOrientationDegrees(NEW_ORIENTATION[ref])
    else:
        new.SetOrientation(old.GetOrientation())
    new.SetReference(ref)
    for src, dst in ((old.Reference(), new.Reference()), (old.Value(), new.Value())):
        dst.SetPosition(src.GetPosition())
        dst.SetTextAngle(src.GetTextAngle())
        dst.SetVisible(src.IsVisible())
    new.SetLocked(old.IsLocked())
    return new


def set_fields(fp, c):
    fp.SetValue(c["value"])
    fp.SetPath(pcbnew.KIID_PATH(c["path"]))
    if hasattr(fp, "SetSheetname"):
        fp.SetSheetname(c["sheet"])
        fp.SetSheetfile(c["sheetfile"])
    if c["lcsc"]:
        fp.SetField("LCSC", c["lcsc"])
    for m in fp.Models():
        # the trial project sits one directory deeper than kicad_next/
        m.m_Filename = m.m_Filename.replace("${KIPRJMOD}/../lib/", "${KIPRJMOD}/../../lib/")


def courtyards(fp):
    out = []
    for layer in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
        poly = fp.GetCourtyard(layer)
        for i in range(poly.OutlineCount()):
            o = poly.Outline(i)
            out.append([[mm(o.CPoint(k).x), mm(o.CPoint(k).y)] for k in range(o.PointCount())])
    return out


def courtyard_box(fp):
    bb = None
    for layer in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
        poly = fp.GetCourtyard(layer)
        if poly.OutlineCount():
            r = poly.BBox()
            bb = r if bb is None else bb.Merge(r) or bb
    return bb if bb is not None else fp.GetBoundingBox(False)


def place_added(b, added, comps, edge_bb):
    """off-board grid below the outline, one row block per sheet (sheet order of the schematic)"""
    x0 = edge_bb.GetX()
    xmax = edge_bb.GetRight()
    y = edge_bb.GetBottom() + pcbnew.FromMM(15)
    gap = pcbnew.FromMM(2.0)
    by_sheet = collections.defaultdict(list)
    for ref, fp in added.items():
        by_sheet[comps[ref]["sheet"]].append((ref, fp))
    out = {}
    for sheet in sorted(by_sheet):
        label = pcbnew.PCB_TEXT(b)
        label.SetText(f"5.2 added parts: {sheet}")
        label.SetLayer(pcbnew.Cmts_User)
        label.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(2), pcbnew.FromMM(2)))
        label.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
        label.SetPosition(pcbnew.VECTOR2I(x0, y))
        b.Add(label)
        y += pcbnew.FromMM(4)
        x, row_h = x0, 0
        for ref, fp in sorted(by_sheet[sheet], key=lambda r: (re.sub(r"\d", "", r[0]), int(re.sub(r"\D", "", r[0]) or 0))):
            bb = courtyard_box(fp)
            w, h = bb.GetWidth(), bb.GetHeight()
            if x + w > xmax and x > x0:
                x, y, row_h = x0, y + row_h + gap, 0
            # move the courtyard box's top-left corner to (x, y)
            fp.Move(pcbnew.VECTOR2I(x - bb.GetX(), y - bb.GetY()))
            out[ref] = (sheet, mm(fp.GetPosition().x), mm(fp.GetPosition().y))
            x += w + gap
            row_h = max(row_h, h)
        y += row_h + pcbnew.FromMM(6)
    return out


RSS_CAP_KB = 2_950_000   # keep the run under 3 GB (task limit); kicad-cli is killed above this


def cli(args):
    """run kicad-cli, polling its resident memory; returns (returncode, peak RSS kB)"""
    pr = subprocess.Popen([CLI] + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    peak = 0
    while pr.poll() is None:
        try:
            pids = [pr.pid] + [int(x) for x in subprocess.run(["pgrep", "-P", str(pr.pid)], capture_output=True,
                                                               text=True).stdout.split()]
            for pid in pids:
                with open(f"/proc/{pid}/status") as f:
                    rss = next((int(l.split()[1]) for l in f if l.startswith("VmRSS:")), 0)
                peak = max(peak, rss)
        except (OSError, ValueError):
            pass
        if peak > RSS_CAP_KB:
            pr.kill()
            sys.exit(f"reuse_51_board: kicad-cli {' '.join(args[:2])} above {RSS_CAP_KB} kB, killed")
        try:
            pr.wait(1.0)
        except subprocess.TimeoutExpired:
            pass
    return pr.returncode, peak


def project_copy(tmp, severities=None, zones_on=None, name=NAME):
    """copy of the trial board / project / rules in tmp; severities: {check: severity} (others 'ignore'
    when given); zones_on: keep only the copper zones on this layer (None = all)"""
    for ext in (".kicad_pro", ".kicad_dru", ".kicad_pcb"):
        shutil.copy(os.path.join(OUTDIR, name + ext), tmp)
    pro_path = os.path.join(tmp, name + ".kicad_pro")
    if severities is not None:
        with open(pro_path) as f:
            pro = json.load(f)
        rs = pro["board"]["design_settings"]["rule_severities"]
        for k in rs:
            rs[k] = severities.get(k, "ignore")
        with open(pro_path, "w") as f:
            json.dump(pro, f, indent=2)
    pcb = os.path.join(tmp, name + ".kicad_pcb")
    if zones_on is not None:
        # in a fresh interpreter: after a LoadBoard / SaveBoard / del of a board in a deleted temporary
        # project, the next pcbnew.LoadBoard in the same process can return a bare SwigPyObject
        subprocess.run([sys.executable, "-c", "import sys, pcbnew\n"
                        "b = pcbnew.LoadBoard(sys.argv[1])\n"
                        "for z in list(b.Zones()):\n"
                        "    if not z.GetIsRuleArea() and not z.GetLayerSet().Contains(int(sys.argv[2])):\n"
                        "        b.Remove(z)\n"
                        "pcbnew.SaveBoard(sys.argv[1], b)\n", pcb, str(zones_on)],
                       check=True, capture_output=True)
    return pcb


def run_drc(name=NAME, out_json="drc.json"):
    """kicad-cli's creepage test on the whole board needs > 3 GB (the 5.1 pours on F / B / In1 / In4);
    the DRC is therefore split into passes, each a separate kicad-cli run (peak about 2.5 GB):
      0  refill the zones with the 5.2 rules, save the board (all checks off)
      1  every check except creepage, whole board
      2  creepage only, copper zones of F.Cu only (creepage rules are outer-layer only; tracks / pads complete)
      3  creepage only, copper zones of B.Cu only
    drc.json = pass 1 + the creepage violations of passes 2 / 3 (duplicates by item uuids removed)."""
    peaks = {}
    with tempfile.TemporaryDirectory() as tmp:
        pcb = project_copy(tmp, severities={}, name=name)
        rc, peaks["refill"] = cli(["pcb", "drc", "--format", "json", "--refill-zones", "--save-board",
                                   "-o", os.path.join(tmp, "d.json"), pcb])
        if rc != 0:
            sys.exit("reuse_51_board: zone refill failed")
        shutil.copy(pcb, os.path.join(OUTDIR, name + ".kicad_pcb"))
    with tempfile.TemporaryDirectory() as tmp:
        pcb = project_copy(tmp, name=name)
        pro_path = os.path.join(tmp, name + ".kicad_pro")
        with open(pro_path) as f:
            pro = json.load(f)
        pro["board"]["design_settings"]["rule_severities"]["creepage"] = "ignore"
        with open(pro_path, "w") as f:
            json.dump(pro, f, indent=2)
        out = os.path.join(tmp, "main.json")
        rc, peaks["main"] = cli(["pcb", "drc", "--format", "json", "--severity-all", "-o", out, pcb])
        with open(out) as f:
            drc = json.load(f)
    seen = set()
    for pname, layer in (("creepage F.Cu", pcbnew.F_Cu), ("creepage B.Cu", pcbnew.B_Cu)):
        with tempfile.TemporaryDirectory() as tmp:
            pcb = project_copy(tmp, severities={"creepage": "error"}, zones_on=layer, name=name)
            out = os.path.join(tmp, "c.json")
            rc, peaks[pname] = cli(["pcb", "drc", "--format", "json", "--severity-all", "-o", out, pcb])
            with open(out) as f:
                c = json.load(f)
        for v in c["violations"]:
            if v["type"] != "creepage":
                continue
            key = tuple(sorted(i.get("uuid", "") for i in v["items"]))
            if key not in seen:
                seen.add(key)
                drc["violations"].append(v)
    drc["passes"] = {k: f"peak RSS {v // 1024} MB" for k, v in peaks.items()}
    with open(os.path.join(OUTDIR, out_json), "w") as f:
        json.dump(drc, f, indent=1)
    print("reuse_51_board: DRC passes " + ", ".join(f"{k} {v // 1024} MB" for k, v in peaks.items()))


def overlaps(pad, t):
    layers = [pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In1_Cu, pcbnew.In4_Cu] if t.Type() == pcbnew.PCB_VIA_T else [t.GetLayer()]
    for layer in layers:
        if pad.IsOnLayer(layer) and pad.GetEffectiveShape(layer).Collide(t.GetEffectiveShape(layer), 0):
            return True
    return False


def main(argv):
    comps, pins, nets52 = netlist()
    nets52_set = set(nets52)
    b = pcbnew.LoadBoard(SRC)
    rec = {"layer_map": {"F.Cu": "F.Cu", "In1.Cu": "In1.Cu (In1.GND, L2)", "In2.Cu": "In4.Cu (In4.GND, L5)",
                         "B.Cu": "B.Cu"}}
    # 5.1 zone fill area per zone (for the pull-back measure), before anything changes
    zone51 = {}
    for z in b.Zones():
        zone51[z.m_Uuid.AsString()] = z.CalculateFilledArea() / 1e12 if z.IsFilled() else 0.0
    rec["moved"] = remap_layers(b)

    # --- outline / holes = 5.2 shell
    shell = pcbnew.LoadBoard(SHELL)
    if make_board.outline(b) != make_board.outline(shell) or make_board.holes(b) != make_board.holes(shell):
        sys.exit("reuse_51_board: 5.1 outline / holes differ from kicad_next/tube_psu_5_2.kicad_pcb")
    del shell

    # --- refdes renamed in 5.2 (same footprint, same place): rename the 5.1 footprint first
    for fp in b.GetFootprints():
        if fp.GetReference() in REF_RENAME_51:
            fp.SetReference(REF_RENAME_51[fp.GetReference()])

    # --- old pad nets (before any change), keyed by (ref, pad number, position)
    old_fps = {fp.GetReference(): fp for fp in b.GetFootprints()}
    old_padnet = {}
    for ref, fp in old_fps.items():
        for p in fp.Pads():
            old_padnet[(ref, p.GetNumber(), p.GetPosition().x, p.GetPosition().y)] = p.GetNetname()

    # --- footprints
    status = {}
    removed, added = [], {}
    for ref, fp in old_fps.items():
        if ref in HOLES:
            status[ref] = "hole"
        elif ref not in comps and fp.GetAttributes() & pcbnew.FP_BOARD_ONLY:
            status[ref] = "board only"   # WP1-WP4 free wire pads of 5.1: kept, pads re-netted by the map
        elif ref not in comps:
            status[ref] = "removed"
            removed.append(ref)
    changed, libonly = [], []
    newfps = {}
    for ref, c in comps.items():
        if ref not in old_fps:
            fp = load_fp(c["fpid"])
            fp.SetReference(ref)
            b.Add(fp)
            added[ref] = fp
            status[ref] = "added"
            newfps[ref] = fp
            continue
        old = old_fps[ref]
        if old.GetFPIDAsString() == c["fpid"]:
            status[ref] = "unchanged"
            newfps[ref] = old
            continue
        new = replace_fp(b, old, c["fpid"], ref)
        if same_pads(pad_sig(old), pad_sig(new)):
            status[ref] = "library copy"
            libonly.append(ref)
        else:
            status[ref] = "changed"
            changed.append(ref)
        newfps[ref] = new
    rec["changed_detail"] = {}
    for ref in changed:
        o, n = old_fps[ref], newfps[ref]
        ob, nb = courtyard_box(o), courtyard_box(n)
        rec["changed_detail"][ref] = dict(
            old=o.GetFPIDAsString(), new=comps[ref]["fpid"], x=mm(o.GetPosition().x), y=mm(o.GetPosition().y),
            rot=o.GetOrientationDegrees(), side="B" if o.IsFlipped() else "F",
            old_court=[mm(ob.GetWidth()), mm(ob.GetHeight())], new_court=[mm(nb.GetWidth()), mm(nb.GetHeight())])

    rec["old_courtyards"] = {ref: dict(side="B" if old_fps[ref].IsFlipped() else "F", court=courtyards(old_fps[ref]))
                             for ref in removed + changed}

    # --- net mapping old -> new from the pads of kept footprints
    votes = collections.defaultdict(collections.Counter)
    for ref, st in status.items():
        if st not in ("unchanged", "library copy"):
            continue
        for p in newfps[ref].Pads():
            key = (ref, p.GetNumber(), p.GetPosition().x, p.GetPosition().y)
            o = old_padnet.get(key)
            n = pins.get(ref, {}).get(p.GetNumber(), "")
            if o:
                votes[o][n] += 1
    netmap, ambiguous = {}, {}
    old_nets = {n for n in (b.GetNetsByName().keys()) if str(n)}
    for o in sorted(str(n) for n in old_nets):
        v = votes.get(o)
        if v and o in v and o in nets52_set:
            netmap[o] = o
        elif v:
            best, cnt = v.most_common(1)[0]
            netmap[o] = best or None
            if len(v) > 1:
                ambiguous[o] = dict(v)
        elif o in nets52_set:
            netmap[o] = o
        else:
            netmap[o] = None
    rec["renamed"] = {o: n for o, n in netmap.items() if n and n != o}
    rec["unmapped_nets"] = sorted(o for o, n in netmap.items() if n is None)
    rec["split_nets"] = ambiguous

    # pads that make tracks go: every pad of a removed or changed footprint (old geometry) - except a pad of a
    # changed footprint that has a new pad at the same place with the same net (L1 / L2 toroid leads in the RM8
    # holes): its tracks stay
    kill_pads, kept_pads = [], []
    for ref in removed + changed:
        new_at = [(q, pins.get(ref, {}).get(q.GetNumber(), "")) for q in newfps[ref].Pads()] if ref in changed else []
        for p in old_fps[ref].Pads():
            pp = p.GetPosition()
            hit = next(((q, n) for q, n in new_at if abs(q.GetPosition().x - pp.x) <= TOL
                        and abs(q.GetPosition().y - pp.y) <= TOL), None)
            if hit and hit[1] and hit[1] == (netmap.get(p.GetNetname()) or ""):
                kept_pads.append((ref, p.GetNumber(), hit[0]))
            else:
                kill_pads.append(p)
    rec["kept_pads"] = [(r, n, q.GetNumber()) for r, n, q in kept_pads]
    kept_new = {(r, q.GetNumber()) for r, _, q in kept_pads}

    # --- delete removed footprints (after their pads were recorded), old copies of replaced ones
    netinfo = {}

    def net(name):
        if not name:
            return b.FindNet(0)
        if name not in netinfo:
            ni = b.FindNet(name)
            if ni is None:
                ni = pcbnew.NETINFO_ITEM(b, name)
                b.Add(ni)
            netinfo[name] = ni
        return netinfo[name]

    # --- re-net pads from the 5.2 netlist, collect pads whose net changed vs the mapped old net
    netchg_pads = []
    for ref, fp in newfps.items():
        set_fields(fp, comps[ref])
        for p in fp.Pads():
            n = pins.get(ref, {}).get(p.GetNumber(), "")
            if status[ref] in ("unchanged", "library copy"):
                o = old_padnet.get((ref, p.GetNumber(), p.GetPosition().x, p.GetPosition().y), "")
                if (netmap.get(o) or "") != n:
                    netchg_pads.append((ref, p.GetNumber(), o, n, p))
            p.SetNet(net(n))
    for ref, st in status.items():
        if st == "board only":
            for p in old_fps[ref].Pads():
                p.SetNet(net(netmap.get(p.GetNetname()) or ""))
    rec["pad_net_changes"] = [(r, num, o, n) for r, num, o, n, _ in netchg_pads]

    # --- copper cleanup
    deleted = collections.Counter()
    deleted_by_ref = collections.Counter()
    checks = [(p, "removed/changed fp " + p.GetParentFootprint().GetReference()) for p in kill_pads] + \
             [(p, "net changed " + r) for r, _, _, _, p in netchg_pads]
    boxes = [(p, why, p.GetBoundingBox()) for p, why in checks]
    new_boxes = [(p, "under changed fp " + ref, p.GetBoundingBox()) for ref in changed for p in newfps[ref].Pads()
                 if (ref, p.GetNumber()) not in kept_new]
    kill = []
    for t in b.GetTracks():
        o = t.GetNetname()
        if netmap.get(o) is None and o:
            kill.append((t, "net gone"))
            continue
        # touching (any overlap) an old pad of a removed / changed part or a pad whose net changed, or
        # lying under a new pad of a changed footprint (would short it)
        hit = None
        tb = t.GetBoundingBox()
        for p, why, bb in boxes + new_boxes:
            if bb.Intersects(tb) and overlaps(p, t):
                hit = why
                break
        if hit:
            kill.append((t, hit))
    for t, why in kill:
        kind = "via" if t.Type() == pcbnew.PCB_VIA_T else "segment"
        reason, _, ref = why.rpartition(" ") if why != "net gone" else (why, "", "(net gone: " + t.GetNetname() + ")")
        deleted[f"{kind}: {reason}"] += 1
        deleted_by_ref[ref] += 1
        b.Remove(t)
    for t in b.GetTracks():
        n = netmap.get(t.GetNetname())
        if n:
            t.SetNet(net(n))
    zones_deleted, zones_renet = [], []
    for z in list(b.Zones()):
        if z.GetIsRuleArea():
            continue
        o = z.GetNetname()
        n = netmap.get(o) if o else ""
        if o and n is None:
            zones_deleted.append(o)
            b.Remove(z)
            continue
        if n and n != o:
            zones_renet.append((o, n))
        if n:
            z.SetNet(net(n))
    for ref in removed:
        b.Remove(old_fps[ref])
    for ref in changed + libonly:
        b.Remove(old_fps[ref])
    # nets of 5.1 that no pad / track / zone uses any more are dropped by the save; 5.2 nets without
    # copper are created so the netclass patterns see them
    for n in nets52:
        net(n)

    edge_bb = b.GetBoardEdgesBoundingBox()
    rec["added_placement"] = place_added(b, added, comps, edge_bb)
    rec["status"] = status
    rec["counts"] = dict(collections.Counter(status.values()))
    rec["changed"], rec["library_copy"], rec["removed"], rec["added"] = changed, libonly, removed, sorted(added)
    rec["deleted_copper"] = dict(deleted)
    rec["deleted_by_ref"] = dict(deleted_by_ref.most_common())
    rec["zones_deleted"], rec["zones_renet"] = zones_deleted, zones_renet

    # --- write the trial project
    os.makedirs(OUTDIR, exist_ok=True)
    shutil.copy(os.path.join(PROJ, "tube_psu_5_2.kicad_dru"), os.path.join(OUTDIR, NAME + ".kicad_dru"))
    with open(os.path.join(PROJ, "tube_psu_5_2.kicad_pro")) as f:
        pro = json.load(f)
    pro.setdefault("meta", {})["filename"] = NAME + ".kicad_pro"
    with open(os.path.join(OUTDIR, NAME + ".kicad_pro"), "w") as f:
        json.dump(pro, f, indent=2)
        f.write("\n")
    with open(os.path.join(PROJ, "fp-lib-table")) as f:
        tbl = f.read().replace("${KIPRJMOD}/../lib/", "${KIPRJMOD}/../../lib/")
    with open(os.path.join(OUTDIR, "fp-lib-table"), "w") as f:
        f.write(tbl)
    pcbnew.SaveBoard(OUT, b)
    with open(OUT) as f:
        s = f.read()
    s = re.sub(r"\t\t\(stackup\n.*?\n\t\t\)\n", "", s, flags=re.S)
    s = s.replace("\t(setup\n", "\t(setup\n" + make_board.STACKUP, 1)
    with open(OUT, "w") as f:
        f.write(s)
    del b

    # --- refill zones with the 5.2 rules + DRC (kicad-cli loads the copied project / rules)
    run_drc()
    if os.path.exists(os.path.join(OUTDIR, "fp-info-cache")):
        os.remove(os.path.join(OUTDIR, "fp-info-cache"))

    # --- baseline: the same DRC on the 5.1 board with its own project (copied to a temporary directory so
    #     kicad/ is not touched)
    base = os.path.join(OUTDIR, "drc_51.json")
    with tempfile.TemporaryDirectory() as tmp:
        for ext in (".kicad_pcb", ".kicad_pro", ".kicad_dru"):
            src = os.path.join(ROOT, "kicad", "tube_psu" + ext)
            if os.path.exists(src):
                shutil.copy(src, tmp)
        cli(["pcb", "drc", "--format", "json", "--severity-all", "-o", base, os.path.join(tmp, "tube_psu.kicad_pcb")])

    # --- geometry dump for the report drawings (from the refilled board)
    b = pcbnew.LoadBoard(OUT)
    if make_board.outline(b) != make_board.outline(pcbnew.LoadBoard(SHELL)):
        sys.exit("reuse_51_board: outline changed")
    rec["geometry"] = dump(b, comps)
    rec["zone_fill"] = []
    for z in b.Zones():
        if z.GetIsRuleArea():
            continue
        u = z.m_Uuid.AsString()
        rec["zone_fill"].append(dict(net=z.GetNetname(), layers=[b.GetLayerName(l) for l in z.GetLayerSet().CuStack()],
                                     area51=round(zone51.get(u, 0.0), 1), area52=round(z.CalculateFilledArea() / 1e12, 1)))
    with open(os.path.join(OUTDIR, "build.json"), "w") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
    print(f"reuse_51_board: {os.path.relpath(OUT, ROOT)}: " + ", ".join(f"{k} {v}" for k, v in sorted(rec["counts"].items())))
    print(f"reuse_51_board: changed footprints ({len(changed)}): {' '.join(sorted(changed))}")
    print(f"reuse_51_board: deleted copper {dict(deleted)}; zones deleted {zones_deleted}")
    if "--no-report" not in argv:
        # system python (matplotlib / shapely), without the AppImage's PYTHONHOME / PYTHONPATH
        env = {k: v for k, v in os.environ.items() if k not in ("PYTHONHOME", "PYTHONPATH")}
        subprocess.run(["python3", os.path.join(HERE, "trial_report.py")], check=True, env=env)
    return 0


def dump(b, comps):
    """outline, tracks per layer, courtyards and positions of the footprints (board coordinates, mm)"""
    g = {"edge": [], "tracks": collections.defaultdict(list), "vias": [], "fps": {}, "zones": collections.defaultdict(list)}
    for d in b.GetDrawings():
        if d.GetLayer() == pcbnew.Edge_Cuts:
            if d.GetShapeStr() in ("Line", "Segment"):
                g["edge"].append([[mm(d.GetStart().x), mm(d.GetStart().y)], [mm(d.GetEnd().x), mm(d.GetEnd().y)]])
            else:
                poly = pcbnew.SHAPE_POLY_SET()
                d.TransformShapeToPolygon(poly, pcbnew.Edge_Cuts, 0, 10000, pcbnew.ERROR_INSIDE)
                for i in range(poly.OutlineCount()):
                    o = poly.Outline(i)
                    pts = [[mm(o.CPoint(k).x), mm(o.CPoint(k).y)] for k in range(o.PointCount())]
                    g["edge"] += [[pts[k], pts[(k + 1) % len(pts)]] for k in range(len(pts))]
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            g["vias"].append([mm(t.GetPosition().x), mm(t.GetPosition().y)])
        else:
            g["tracks"][b.GetLayerName(t.GetLayer())].append(
                [mm(t.GetStart().x), mm(t.GetStart().y), mm(t.GetEnd().x), mm(t.GetEnd().y), mm(t.GetWidth())])
    for z in b.Zones():
        if z.GetIsRuleArea():
            continue
        for layer in z.GetLayerSet().CuStack():
            fp = z.GetFilledPolysList(layer)
            for i in range(fp.OutlineCount()):
                o = fp.Outline(i)
                step = max(1, o.PointCount() // 400)
                g["zones"][b.GetLayerName(layer)].append(
                    dict(net=z.GetNetname(), pts=[[mm(o.CPoint(k).x), mm(o.CPoint(k).y)] for k in range(0, o.PointCount(), step)]))
    for fp in b.GetFootprints():
        ref = fp.GetReference()
        crt = courtyards(fp)
        pads = []
        for p in fp.Pads():
            pads.append([mm(p.GetPosition().x), mm(p.GetPosition().y), mm(p.GetBoundingBox().GetWidth()),
                         mm(p.GetBoundingBox().GetHeight()), p.GetNetname()])
        g["fps"][ref] = dict(x=mm(fp.GetPosition().x), y=mm(fp.GetPosition().y), side="B" if fp.IsFlipped() else "F",
                             court=crt, pads=pads, sheet=comps.get(ref, {}).get("sheet", ""),
                             fpid=fp.GetFPIDAsString())
    return g


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
