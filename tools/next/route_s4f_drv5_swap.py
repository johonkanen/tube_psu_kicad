#!/usr/bin/env python3
"""Stage 4f of tube_power 5.2 (2026-11-22): the channel swap of DRV5 on the board (no routing, no part moved).

    tools/p2k/bin/kipy tools/next/update_board_parts.py DRV5          (first: pad nets of DRV5 from the schematic)
    tools/p2k/bin/kipy tools/next/route_s4f_drv5_swap.py [--dry-run OUT.kicad_pcb]

Schematic change (CHANGES_5_2.md 3.1b): DRV5 channel A (pins 14 / 15 / 16, INA pin 1) is the high side, channel B
(pins 9 / 10 / 11, INB pin 2) the low side. Incremental edit, same conventions as route_s4d_shunt_u1.py; NOT
re-runnable on its own result (refuses when routing/deleted_s4f.json exists). The rebuild scripts stay frozen.

What it does:
  1. the bootstrap net changed its name with the pin: every pad / track / via / zone of the board still on
     'Net-(DRV5-VDDB)' goes to 'Net-(DRV5-VDDA)' (C92 pin 2, R41 pin 2 and their copper - nothing is moved)
  2. copper that ends on one of the swapped pins of DRV5 (1, 2, 9, 10, 11, 14, 15, 16) with another net than the pin
     has now would be a short: it is deleted from the pin back to the first junction (a pad, a via, a branch or
     the end of the chain), and nothing else
  0. pcbnew's save in update_board_parts.py took the ground stub of pin 14 (segment + via 23.25, -51.99, nothing
     else of GND on it) along to the pin's new net DHB_HI_SOURCE: both are put back on GND first (RESTORE) - the via
     is a ground via into the planes and stays, the segment is cut by step 2
Writes kicad_next/routing/deleted_s4f.json. Zones are refilled by kicad-cli. DRV5 is re-laid by the next block.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PROJ = os.path.join(ROOT, "kicad_next")
NAME = "tube_psu_5_2"
BOARD = os.path.join(PROJ, NAME + ".kicad_pcb")
LOCK = os.path.join(PROJ, "~" + NAME + ".kicad_pcb.lck")
CLI = os.path.join(ROOT, "tools", "p2k", "bin", "kicad-cli")
RT = os.path.join(PROJ, "routing")
REF = "DRV5"
PINS = ("1", "2", "9", "10", "11", "14", "15", "16")
OLD_NET, NEW_NET = "Net-(DRV5-VDDB)", "Net-(DRV5-VDDA)"
# pin -> net after the swap (the schematic; update_board_parts.py has to have put them on the pads)
EXPECT = {"1": "PRI_DHB_HI", "2": "B12", "9": "GND", "10": "DHB_LOW_GATE", "11": "15V",
          "14": "DHB_HI_SOURCE", "15": "DHB_HI_GATE", "16": NEW_NET}
# copper whose net pcbnew changed with the pad on save (uuid -> net it has to keep)
RESTORE = {"d7d52dec-c064-4ab5-b7f4-d16732a51134": "GND", "ea07596e-245a-4ca1-afa6-7aedf64a0dc6": "GND"}
mm = lambda v: round(pcbnew.ToMM(v), 4)  # noqa: E731


def edit(path):
    b = pcbnew.LoadBoard(path)
    fp = b.FindFootprintByReference(REF)
    pads = {p.GetNumber(): p for p in fp.Pads()}
    for n, net in EXPECT.items():
        if pads[n].GetNetname() != net:
            sys.exit(f"s4f: {REF}.{n} is on '{pads[n].GetNetname()}', not '{net}' - run update_board_parts.py {REF} first")
    restored = []
    for t in b.GetTracks():
        want = RESTORE.get(t.m_Uuid.AsString())
        if want and t.GetNetname() != want:
            restored.append(f"{t.GetClass()} ({mm(t.GetStart().x)}, {mm(t.GetStart().y)}) {t.GetNetname()} -> {want}")
            t.SetNet(b.FindNet(want))
    renamed = []
    old, new = b.FindNet(OLD_NET), b.FindNet(NEW_NET)
    if old is not None:
        for f in b.GetFootprints():
            for p in f.Pads():
                if p.GetNetname() == OLD_NET:
                    p.SetNet(new)
                    renamed.append(f"{f.GetReference()}.{p.GetNumber()}")
        nt = 0
        for t in b.GetTracks():
            if t.GetNetname() == OLD_NET:
                t.SetNet(new)
                nt += 1
        for z in b.Zones():
            if z.GetNetname() == OLD_NET:
                z.SetNet(new)
                renamed.append("zone " + z.GetZoneName())
        renamed.append(f"{nt} tracks / vias")

    tracks = [t for t in b.GetTracks()]
    all_pads = [p for f in b.GetFootprints() for p in f.Pads()]

    def at(pt, net, layer, skip):
        """other copper of the net at pt: (segments ending there, vias, pads)"""
        segs = [t for t in tracks if t not in skip and t.Type() != pcbnew.PCB_VIA_T and t.GetNetname() == net
                and t.IsOnLayer(layer) and (t.GetStart() == pt or t.GetEnd() == pt)]
        vias = [t for t in tracks if t not in skip and t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() == net
                and t.IsOnLayer(layer) and t.HitTest(pt)]
        pds = [p for p in all_pads if p.GetNetname() == net and p.IsOnLayer(layer) and p.HitTest(pt)]
        return segs, vias, pds

    deleted, gone, opened = [], [], []
    for n in PINS:
        pad = pads[n]
        net = pad.GetNetname()
        pad_layer = pcbnew.B_Cu if pad.IsOnLayer(pcbnew.B_Cu) else pcbnew.F_Cu     # SMD pad: one copper layer
        for t in tracks:
            if t in gone or t.GetNetname() == net or not t.IsOnLayer(pad_layer):
                continue
            if t.Type() == pcbnew.PCB_VIA_T:
                if pad.HitTest(t.GetPosition()):
                    sys.exit(f"s4f: via of {t.GetNetname()} in {REF}.{n} - not handled")
                continue
            if not (pad.HitTest(t.GetStart()) or pad.HitTest(t.GetEnd())):
                continue
            tnet, layer = t.GetNetname(), t.GetLayer()
            cur, far = t, (t.GetEnd() if pad.HitTest(t.GetStart()) else t.GetStart())
            if pad.HitTest(t.GetStart()) and pad.HitTest(t.GetEnd()):
                far = None
            n0 = len(deleted)
            while True:
                gone.append(cur)
                deleted.append(dict(kind="segment", net=tnet, layer=cur.GetLayerName(),
                                    start=[mm(cur.GetStart().x), mm(cur.GetStart().y)],
                                    end=[mm(cur.GetEnd().x), mm(cur.GetEnd().y)], width=mm(cur.GetWidth()),
                                    why=f"ended on {REF} pin {n}, which is on {net} after the channel swap"))
                if far is None:
                    stop = "inside the pad"
                    break
                segs, vias, pds = at(far, tnet, layer, gone)
                if pds:
                    stop = "pad " + ", ".join(f"{p.GetParentFootprint().GetReference()}.{p.GetNumber()}" for p in pds)
                    break
                if vias:
                    stop = "via"
                    break
                if len(segs) != 1:
                    stop = "branch" if segs else "open end / T on another track"
                    break
                cur = segs[0]
                far = cur.GetEnd() if cur.GetStart() == far else cur.GetStart()
            end = [mm(far.x), mm(far.y)] if far is not None else None
            opened.append(dict(pin=f"{REF}.{n}", pin_net_now=net, cut_net=tnet, segments=len(deleted) - n0,
                               cut_back_to=end, stopped_at=stop))
    for t in gone:
        b.Remove(t)
    pcbnew.SaveBoard(path, b)
    with open(os.path.join(os.path.dirname(path), "s4f.json"), "w") as f:
        json.dump(dict(restored=restored, renamed=renamed, cuts=opened, deleted=deleted), f)


def main(argv):
    if os.path.exists(LOCK):
        sys.exit("s4f: the board is open in KiCad; close it first")
    if os.path.exists(os.path.join(RT, "deleted_s4f.json")) and "--dry-run" not in argv:
        sys.exit("s4f: routing/deleted_s4f.json exists - this block is on the board already (not re-runnable)")
    tmp = tempfile.mkdtemp(prefix=".s4f_", dir=ROOT)
    try:
        for ext in (".kicad_pcb", ".kicad_dru"):
            shutil.copy(os.path.join(PROJ, NAME + ext), tmp)
        with open(os.path.join(PROJ, NAME + ".kicad_pro")) as f:
            pro = json.load(f)
        rs = pro["board"]["design_settings"]["rule_severities"]
        for k in rs:
            rs[k] = "ignore"                       # refill only
        with open(os.path.join(tmp, NAME + ".kicad_pro"), "w") as f:
            json.dump(pro, f, indent=2)
        pcb = os.path.join(tmp, NAME + ".kicad_pcb")
        r = subprocess.run([sys.executable, "-u", os.path.abspath(__file__), "--edit", pcb])
        if r.returncode:
            sys.exit("s4f: edit failed, the board is unchanged")
        r = subprocess.run([CLI, "pcb", "drc", "--format", "json", "--refill-zones", "--save-board",
                            "-o", os.path.join(tmp, "refill.json"), pcb], capture_output=True, text=True)
        if r.returncode:
            sys.exit("s4f: zone refill failed, the board is unchanged\n" + r.stdout[-1500:] + r.stderr[-1500:])
        with open(os.path.join(tmp, "s4f.json")) as f:
            j = json.load(f)
        for x in j["restored"]:
            print("s4f: net put back: " + x)
        print(f"s4f: {OLD_NET} -> {NEW_NET}: " + ", ".join(j["renamed"]))
        for c in j["cuts"]:
            print(f"s4f: cut {c['cut_net']} at {c['pin']} (now {c['pin_net_now']}): {c['segments']} segments, "
                  f"back to {c['cut_back_to']} ({c['stopped_at']})")
        print(f"s4f: deleted {len(j['deleted'])} segments")
        if "--dry-run" in argv:
            out = os.path.abspath(argv[argv.index("--dry-run") + 1])
            shutil.copy(pcb, out)
            print(f"s4f: dry run in {out}, the board is unchanged")
            return 0
        shutil.copy(pcb, BOARD)
        note = ("stage 4f (2026-11-22), tools/next/route_s4f_drv5_swap.py - DRV5 channels swapped in the schematic; "
                "copper that ended on a swapped pin with the old net, cut back to the first junction")
        with open(os.path.join(RT, "deleted_s4f.json"), "w") as f:
            json.dump({"note": note, "restored": j["restored"], "renamed": j["renamed"], "cuts": j["cuts"], "deleted": j["deleted"]}, f, indent=1)
        print("s4f: wrote the board and routing/deleted_s4f.json")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    if "--edit" in sys.argv:
        edit(sys.argv[sys.argv.index("--edit") + 1])
        sys.exit(0)
    sys.exit(main(sys.argv[1:]))
