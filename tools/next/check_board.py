#!/usr/bin/env python3
"""DRC + schematic parity of the real 5.2 board, cheap enough for check_next.sh (system python3).

    python3 tools/next/check_board.py [--all]

Runs kicad-cli pcb drc --schematic-parity on kicad_next/tube_psu_5_2.kicad_pcb with every check on except the
creepage test: the creepage DRC of the populated board needs > 3 GB (reuse_51_board.run_drc splits it into
passes); creepage / clearance between isolation domains is checked by check_domains.py instead (cheaper and it
does not miss pairs). The DRC runs on a copy of the project in a temporary directory next to kicad_next/ (same
depth, so the ${KIPRJMOD}/../lib library paths resolve) with the creepage severity set to ignore. About 2.3 GB,
10 s. Writes reports/next/drc.json.

Fails (exit 1) on:
  * any schematic parity item (missing / extra footprint, net, value, footprint id or field mismatch)
  * any short (shorting_items)
  * any violation of an isolation-domain rule of tube_psu_5_2.kicad_dru that is not in ACCEPTED
Everything else (clearances inside a domain, courtyards, silk, dangling copper, unconnected items while the
board is being routed) is counted and printed, not failed.
"""
import collections
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJ = os.path.join(ROOT, "kicad_next")
NAME = "tube_psu_5_2"
CLI = os.path.join(ROOT, "tools", "p2k", "bin", "kicad-cli")
REPORT = os.path.join(ROOT, "reports", "next", "drc.json")
# isolation-domain rules of the .kicad_dru (rule names start with these)
DOMAIN_RULES = ("PRI-SEC", "PRI-HEATER", "SEC-UART", "SEC(HV)-HEATER", "SEC(LV)-HEATER", "HEATER-UART",
                "PE-PRI", "PE-SEC", "Mounting hole")
# DRC checks that only concern silkscreen / text: ignored, the board has no silkscreen
SILK_CHECKS = ("silk_overlap", "silk_over_copper", "silk_edge_clearance", "nonmirrored_text_on_back_layer",
               "text_thickness", "text_height")
# accepted domain-rule violations: (rule name, regex on the joined item descriptions, reason)
ACCEPTED = [
    # (empty since routing stage 2, 2026-11-20: the TR1 pin 2 GND / pin 9 ISO_GND inner barrels no longer show,
    # pin 2 has no inner-layer connection - keep it that way, an inner GND pad on pin 2 fails here again)
]


def main(argv):
    tmp = tempfile.mkdtemp(prefix=".drc_", dir=ROOT)
    try:
        for f in os.listdir(PROJ):
            if f.endswith(".kicad_sch") or f in (NAME + ".kicad_pcb", NAME + ".kicad_dru", "fp-lib-table",
                                                 "sym-lib-table"):
                shutil.copy(os.path.join(PROJ, f), tmp)
        with open(os.path.join(PROJ, NAME + ".kicad_pro")) as f:
            pro = json.load(f)
        sev = pro["board"]["design_settings"]["rule_severities"]
        sev["creepage"] = "ignore"
        # the 5.2 board is ordered without silkscreen (user, 2026-11-20): silk / text checks are noise
        for k in SILK_CHECKS:
            sev[k] = "ignore"
        with open(os.path.join(tmp, NAME + ".kicad_pro"), "w") as f:
            json.dump(pro, f, indent=2)
        out = os.path.join(tmp, "drc.json")
        r = subprocess.run([CLI, "pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity",
                            "-o", out, os.path.join(tmp, NAME + ".kicad_pcb")], capture_output=True, text=True)
        if r.returncode or not os.path.exists(out):
            print("check_board: kicad-cli drc failed\n" + r.stdout[-2000:] + r.stderr[-2000:])
            return 1
        os.makedirs(os.path.dirname(REPORT), exist_ok=True)
        shutil.copy(out, REPORT)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    with open(REPORT) as f:
        d = json.load(f)
    bad = []
    parity = d.get("schematic_parity", [])
    for x in parity:
        bad.append(f"parity {x['type']}: {x['description']} | "
                   + " || ".join(i["description"] for i in x["items"]))
    types = collections.Counter(x["type"] for x in d["violations"])
    accepted = collections.Counter()
    for x in d["violations"]:
        items = " || ".join(i["description"] for i in x["items"])
        if x["type"] == "shorting_items":
            bad.append(f"short: {x['description']} | {items}")
            continue
        m = re.search(r"rule '([^']+)'", x["description"])
        if not m or not m.group(1).startswith(DOMAIN_RULES):
            continue
        for rule, pat, why in ACCEPTED:
            if m.group(1) == rule and pat.search(items):
                accepted[why] += 1
                break
        else:
            bad.append(f"{x['type']}: {x['description']} | {items}")
    print(f"check_board: {os.path.relpath(os.path.join(PROJ, NAME + '.kicad_pcb'), ROOT)}: "
          f"{sum(types.values())} DRC items without creepage ({', '.join(f'{k} {n}' for k, n in types.most_common(8))}"
          f"{', ...' if len(types) > 8 else ''}), {len(d['unconnected_items'])} unconnected, "
          f"{len(parity)} schematic parity items (reports/next/drc.json)")
    for why, n in accepted.items():
        print(f"check_board: accepted {n}: {why}")
    for i, b in enumerate(bad):
        if i < 40 or "--all" in argv:
            print("check_board: FAIL " + b)
    if len(bad) > 40 and "--all" not in argv:
        print(f"check_board: ... {len(bad) - 40} more (--all)")
    print("check_board: " + ("OK - no parity item, no short, no isolation-rule violation besides the accepted ones"
                             if not bad else f"{len(bad)} failing items"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
