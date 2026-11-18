#!/usr/bin/env bash
# Checks of the tube_power 5.2 design in kicad_next/ (the 5.1 migration keeps tools/check_all.sh).
# Exit status is non-zero if any step fails. Reports: reports/next/ (git-ignored).
set -u
cd "$(dirname "$0")/../.."
[ -x tools/p2k/bin/kicad-cli ] || { echo "tools/p2k missing: git submodule update --init"; exit 1; }
mkdir -p reports/next
fail=0
step() { echo "== $1"; shift; "$@" || { echo "!! FAILED: $*"; fail=1; }; }
quiet() { "$@" 2>&1 | grep -v -e "Debug: Adding duplicate image handler" -e "^Warning"; return "${PIPESTATUS[0]}"; }

erc() {
    tools/p2k/bin/kicad-cli sch erc --severity-all -o reports/next/erc.rpt kicad_next/tube_psu_5_2.kicad_sch >/dev/null || return 1
    local errs warns
    errs=$(grep -c '; error' reports/next/erc.rpt)
    warns=$(grep -c '; warning' reports/next/erc.rpt)
    echo "erc: $errs errors, $warns warnings (reports/next/erc.rpt)"
    [ "$errs" -eq 0 ]
}

drc() {
    tools/p2k/bin/kicad-cli pcb drc --format json --severity-all -o reports/next/drc.json kicad_next/tube_psu_5_2.kicad_pcb >/dev/null || return 1
    python3 - <<'EOF'
import collections, json, sys
d = json.load(open("reports/next/drc.json"))
v = collections.Counter(x["type"] for x in d["violations"])
print(f"drc: {sum(v.values())} violations{' ' + str(dict(v)) if v else ''}, {len(d['unconnected_items'])} unconnected (reports/next/drc.json)")
sys.exit(1 if v or d["unconnected_items"] else 0)
EOF
}

step "5.2 symbol library up to date" python3 tools/next/gen_symbols.py --check
step "5.2 schematic regenerated from tools/next/sheets, up to date" python3 tools/next/gen_schematic.py --check
step "5.2 part footprints up to date" python3 tools/next/gen_next_footprints_parts.py --check
step "ERC" erc
step "Net classes: one isolation domain per net, project file up to date" python3 tools/next/setup_project.py --check
step "Board skeleton: 6 layers, JLC stackup, 5.1 outline and holes" quiet tools/p2k/bin/kipy tools/next/make_board.py --check
step "DRC of the board" drc
step "Design rules parse and act (test tracks)" quiet tools/p2k/bin/kipy tools/next/check_rules.py

echo
[ $fail -eq 0 ] && echo "ALL 5.2 CHECKS PASSED" || echo "SOME 5.2 CHECKS FAILED"
exit $fail
