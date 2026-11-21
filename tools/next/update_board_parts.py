#!/usr/bin/env python3
""""Update PCB from schematic" for single parts of the real 5.2 board (run with tools/p2k/bin/kipy).

    tools/p2k/bin/kipy tools/next/update_board_parts.py [--check] REF [REF ...]      (default: TR2 TR3)

For every REF of kicad_next/tube_psu_5_2.kicad_pcb:
  * if the pads of the board footprint differ from the library footprint of the same id (number, position, size,
    drill), the footprint is replaced by the library one at the same position / rotation / side; reference and
    value text places, lock state and all fields are kept, 3D model paths are the library's
  * every pad gets the net of the 5.2 netlist (kicad-cli sch export netlist), Value / Description / LCSC / symbol
    path / sheet follow the schematic
Nothing else on the board is touched: no copper is moved or deleted (copper on a pad that changed its net or
went away shows up in check_board.py as a short / dangling track and is the routing scripts' business).
The project file is left as it is. Idempotent; --check writes nothing and fails if something would change. Stops on KiCad's lock file.

First use 2026-11-21: TR3 pins re-assigned (primary start 1+2 -> 4+5, secondary finish 15+16 -> 13+14).
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import reuse_51_board as R  # noqa: E402  (netlist(), load_fp(), pad_sig(), same_pads())

BOARD = os.path.join(R.PROJ, "tube_psu_5_2.kicad_pcb")
LOCK = os.path.join(R.PROJ, "~tube_psu_5_2.kicad_pcb.lck")
DEFAULT = ["TR2", "TR3"]


def main(argv):
    check = "--check" in argv
    refs = [a for a in argv if not a.startswith("-")] or DEFAULT
    if os.path.exists(LOCK) and not check:
        sys.exit("update_board_parts: the board is open in KiCad (lock file) - close it first")
    comps, pins, _ = R.netlist()
    b = pcbnew.LoadBoard(BOARD)
    changes = []
    for ref in refs:
        fp = b.FindFootprintByReference(ref)
        if fp is None or ref not in comps:
            sys.exit(f"update_board_parts: {ref} is not on the board / in the schematic")
        c = comps[ref]
        fpid = fp.GetFPIDAsString()
        if fpid != c["fpid"]:
            sys.exit(f"update_board_parts: {ref} footprint id {fpid} != schematic {c['fpid']} (not handled here)")
        new = R.load_fp(fpid)
        b.Add(new)                                   # on the board before Flip (pcbnew 10)
        pos = fp.GetPosition()
        new.SetPosition(pos)
        if fp.IsFlipped():
            new.Flip(pos, pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        new.SetOrientation(fp.GetOrientation())
        if R.same_pads(R.pad_sig(fp), R.pad_sig(new)):
            b.Delete(new)
        else:
            old_pads = sorted({p.GetNumber() for p in fp.Pads() if p.GetNumber()}, key=lambda s: (len(s), s))
            new_pads = sorted({p.GetNumber() for p in new.Pads() if p.GetNumber()}, key=lambda s: (len(s), s))
            changes.append(f"{ref}: footprint replaced from the library, pads {','.join(old_pads)} -> {','.join(new_pads)}")
            new.SetReference(ref)
            for src, dst in ((fp.Reference(), new.Reference()), (fp.Value(), new.Value())):
                dst.SetPosition(src.GetPosition())
                dst.SetTextAngle(src.GetTextAngle())
                dst.SetVisible(src.IsVisible())
                dst.SetLayer(src.GetLayer())
            new.SetLocked(fp.IsLocked())
            new.SetValue(fp.GetValue())
            new.SetPath(fp.GetPath())
            if hasattr(new, "SetSheetname"):
                new.SetSheetname(fp.GetSheetname())
                new.SetSheetfile(fp.GetSheetfile())
            for f in fp.GetFields():
                name = f.GetName()
                if name not in ("Reference", "Value", "Footprint"):
                    new.SetField(name, f.GetText())
                    if not f.IsVisible():
                        new.GetField(name).SetVisible(False)
            b.Delete(fp)
            fp = new
        if fp.GetValue() != c["value"]:
            changes.append(f"{ref}: value {fp.GetValue()} -> {c['value']}")
            fp.SetValue(c["value"])
        if c["lcsc"] and (not fp.HasField("LCSC") or fp.GetFieldText("LCSC") != c["lcsc"]):
            changes.append(f"{ref}: LCSC -> {c['lcsc']}")
            fp.SetField("LCSC", c["lcsc"])
        if not fp.HasField("Description") or fp.GetFieldText("Description") != c["descr"]:
            changes.append(f"{ref}: Description -> {c['descr']}")
            fp.SetField("Description", c["descr"])
            fp.GetField("Description").SetVisible(False)
        if fp.GetPath().AsString() != pcbnew.KIID_PATH(c["path"]).AsString():
            changes.append(f"{ref}: symbol path")
            fp.SetPath(pcbnew.KIID_PATH(c["path"]))
        for p in fp.Pads():
            n = pins.get(ref, {}).get(p.GetNumber(), "")
            if p.GetNetname() != n:
                changes.append(f"{ref}.{p.GetNumber()}: net '{p.GetNetname()}' -> '{n}'")
                ni = b.FindNet(n) if n else b.FindNet(0)
                if ni is None:
                    ni = pcbnew.NETINFO_ITEM(b, n)
                    b.Add(ni)
                p.SetNet(ni)
    for c_ in changes:
        print("update_board_parts: " + c_)
    if check:
        print(f"update_board_parts: {len(changes)} differences" if changes else "update_board_parts: up to date")
        return 1 if changes else 0
    if changes:
        if os.path.exists(LOCK):
            sys.exit("update_board_parts: the board was opened in KiCad meanwhile - not written")
        pro = os.path.join(R.PROJ, "tube_psu_5_2.kicad_pro")
        with open(pro, "rb") as f:                   # pcbnew's Save rewrites (re-sorts) the project file: keep it
            keep = f.read()
        b.Save(BOARD)
        with open(pro, "wb") as f:
            f.write(keep)
        print(f"update_board_parts: wrote {os.path.relpath(BOARD, R.ROOT)} ({len(changes)} changes)")
    else:
        print("update_board_parts: nothing to do")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
