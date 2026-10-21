#!/usr/bin/env bash
# Run every verification step. Exit status is non-zero if any step fails.
# Each phase adds its steps here (PLAN.md section 2.5, playbook principle 5).
# The tools are the proteus2kicad submodule in tools/p2k; board values in p2k_config.py.
set -u
cd "$(dirname "$0")/.."
[ -x tools/p2k/bin/p2k ] || { echo "tools/p2k missing: git submodule update --init"; exit 1; }
fail=0
step() { echo "== $1"; shift; "$@" || { echo "!! FAILED: $*"; fail=1; }; }

step "KiCad environment" tools/p2k/bin/kipy -c "import pcbnew; v = pcbnew.GetBuildVersion(); print('pcbnew', v); assert v.startswith('10.0.7'), v"
step "IPC-D-356A parser self-check" tools/p2k/bin/p2k ipc356 --check
step "Gerber X2 export vs IPC (pads, vias, drills, outline)" tools/p2k/bin/p2k check_sources

echo
[ $fail -eq 0 ] && echo "ALL CHECKS PASSED" || echo "SOME CHECKS FAILED"
exit $fail
