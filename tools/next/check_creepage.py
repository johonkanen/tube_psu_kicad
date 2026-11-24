#!/usr/bin/env python3
"""KiCad creepage DRC of the real 5.2 board in four layer-split passes (system python3, about 8 minutes).

    python3 tools/next/check_creepage.py [--keep]

The creepage test of the whole board at once needs more than 3 GB, so it is not part of check_next.sh
(check_board.py runs the DRC with creepage ignored; check_domains.py checks the distances between isolation domains
on all layers). This script runs KiCad's own creepage test (outer layers only, paths round slots) as four separate
kicad-cli runs, each about 2.5 GB, one after the other:

    prisec_F   rule "PRI-SEC reinforced creepage" only      zones / tracks of F.Cu only
    rest_F     every other rule of the .kicad_dru           zones / tracks of F.Cu only
    prisec_B   as prisec_F                                   zones / tracks of B.Cu only
    rest_B     as rest_F                                     zones / tracks of B.Cu only

Pads, vias, the outline and rule areas stay in every pass; all DRC severities are "ignore" except creepage. Each
pass works on a copy of the project in a temporary directory next to kicad_next/ (so ${KIPRJMOD}/../lib resolves);
the real board is only read. A watchdog kills a pass above CAP kB (then the result is "killed", not 0).
Writes reports/next/creepage.json (one record per pass, the violations included) and fails (exit 1) on any creepage
violation or killed pass. --keep leaves the temporary directories for inspection.

First run of this script: 2026-11-24 (the same method was used from a scratch script on 2026-11-22 / 23).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJ = os.path.join(ROOT, "kicad_next")
NAME = "tube_psu_5_2"
CLI = os.path.join(ROOT, "tools", "p2k", "bin", "kicad-cli")
KIPY = os.path.join(ROOT, "tools", "p2k", "bin", "kipy")
REPORT = os.path.join(ROOT, "reports", "next", "creepage.json")
LOCK = os.path.join(PROJ, "~" + NAME + ".kicad_pcb.lck")
CAP = 2_900_000          # kB resident, whole process tree
SPLIT = "PRI-SEC reinforced creepage"
STRIP = """import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
L = b.GetLayerID(sys.argv[2])
tr = [t for t in b.Tracks() if t.Type() != pcbnew.PCB_VIA_T and t.GetLayer() != L]
zs = [z for z in b.Zones() if not z.GetIsRuleArea() and not z.GetLayerSet().Contains(L)]
for z in zs:
    b.Remove(z)
for t in tr:
    b.Remove(t)
print('removed', len(zs), 'zones', len(tr), 'tracks')
pcbnew.SaveBoard(sys.argv[1], b)
"""


def tree(pid):
    r = [pid]
    for c in subprocess.run(["pgrep", "-P", str(pid)], capture_output=True, text=True).stdout.split():
        r += tree(int(c))
    return r


def one_pass(tag, only, layer, keep):
    """only = True: the SPLIT rule alone; False: every rule but SPLIT (file order kept)."""
    tmp = tempfile.mkdtemp(prefix=".drc_creep_" + tag + "_", dir=ROOT)
    try:
        for f in (NAME + ".kicad_pcb", "fp-lib-table", "sym-lib-table"):
            shutil.copy(os.path.join(PROJ, f), tmp)
        with open(os.path.join(PROJ, NAME + ".kicad_pro")) as f:
            pro = json.load(f)
        rs = pro["board"]["design_settings"]["rule_severities"]
        for k in rs:
            rs[k] = "ignore"
        rs["creepage"] = "error"
        with open(os.path.join(tmp, NAME + ".kicad_pro"), "w") as f:
            json.dump(pro, f, indent=2)
        with open(os.path.join(PROJ, NAME + ".kicad_dru")) as f:
            parts = re.split(r"(?m)^(?=\(rule )", f.read())
        names = [re.match(r'\(rule "([^"]+)"', p).group(1) for p in parts[1:]]
        if SPLIT not in names:
            sys.exit(f"check_creepage: rule '{SPLIT}' not in the .kicad_dru")
        kept = [p for p, n in zip(parts[1:], names) if (n == SPLIT) == only]
        with open(os.path.join(tmp, NAME + ".kicad_dru"), "w") as f:
            f.write(parts[0] + "".join(kept))
        pcb = os.path.join(tmp, NAME + ".kicad_pcb")
        r = subprocess.run([KIPY, "-c", STRIP, pcb, layer], capture_output=True, text=True)
        if r.returncode:
            sys.exit("check_creepage: layer strip failed\n" + r.stdout[-500:] + r.stderr[-1500:])
        out = os.path.join(tmp, "creep.json")
        t0 = time.time()
        pr = subprocess.Popen([CLI, "pcb", "drc", "--format", "json", "--severity-all", "-o", out, pcb],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        peak, killed = 0, False
        while pr.poll() is None:
            now = 0
            for pid in tree(pr.pid):
                try:
                    with open(f"/proc/{pid}/status") as f:
                        for line in f:
                            if line.startswith("VmRSS:"):
                                now += int(line.split()[1])
                except OSError:
                    pass
            peak = max(peak, now)
            if peak > CAP:
                for pid in reversed(tree(pr.pid)):
                    try:
                        os.kill(pid, 9)
                    except OSError:
                        pass
                killed = True
                break
            time.sleep(0.5)
        viol = None
        if not killed and os.path.exists(out):
            with open(out) as f:
                d = json.load(f)
            viol = [v for v in d["violations"] if v["type"] == "creepage"]
        return dict(tag=tag, layer=layer, rules=len(kept), peak_mb=peak // 1024, secs=round(time.time() - t0, 1),
                    killed=killed, rc=pr.returncode, creepage=None if viol is None else len(viol), violations=viol)
    finally:
        if not keep:
            shutil.rmtree(tmp, ignore_errors=True)


def main(argv):
    if os.path.exists(LOCK):
        sys.exit("check_creepage: the board is open in KiCad; close it first")
    busy = subprocess.run(["pgrep", "-f", "bin/kicad-cli pcb drc"], capture_output=True, text=True).stdout.split()
    if busy:
        sys.exit("check_creepage: another kicad-cli DRC is running (one heavy job at a time)")
    res = []
    for tag, only, layer in (("prisec_F", True, "F.Cu"), ("rest_F", False, "F.Cu"),
                             ("prisec_B", True, "B.Cu"), ("rest_B", False, "B.Cu")):
        r = one_pass(tag, only, layer, "--keep" in argv)
        res.append(r)
        print(f"check_creepage: {tag}: {r['rules']} rules, zones / tracks of {layer}: "
              + ("KILLED by the RAM watchdog" if r["killed"] else f"{r['creepage']} creepage violations")
              + f" ({r['peak_mb']} MB, {r['secs']} s)", flush=True)
        for v in (r["violations"] or [])[:20]:
            print("check_creepage:   " + v["description"] + " | "
                  + " || ".join(i["description"] for i in v["items"]))
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w") as f:
        json.dump(res, f, indent=1)
    bad = [r for r in res if r["killed"] or r["creepage"] is None or r["creepage"]]
    print("check_creepage: " + ("OK - no creepage violation in the four passes" if not bad
                                else f"{len(bad)} pass(es) with violations or without result"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
