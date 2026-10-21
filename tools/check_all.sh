#!/usr/bin/env bash
# Run every verification step. Exit status is non-zero if any step fails.
# Each phase adds its steps here (PLAN.md section 2.5, playbook principle 5).
set -u
cd "$(dirname "$0")/.."
fail=0
step() { echo "== $1"; shift; "$@" || { echo "!! FAILED: $*"; fail=1; }; }

step "KiCad environment" tools/bin/kipy -c "import pcbnew; v = pcbnew.GetBuildVersion(); print('pcbnew', v); assert v.startswith('10.0.7'), v"
step "IPC-D-356A parser self-check" python3 tools/ipc356.py --check
step "Gerber X2 export vs IPC (pads, vias, drills, outline)" python3 tools/check_sources.py

echo
[ $fail -eq 0 ] && echo "ALL CHECKS PASSED" || echo "SOME CHECKS FAILED"
exit $fail
