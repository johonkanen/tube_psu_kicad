# Next prompt

Ready-to-paste prompt for the next agent session (Phase 5 – clean-up, in progress).
Replaced at the end of every phase or session, see PLAN.md section 9.

```
Read PLAN.md and STATUS.md in /home/jari/dev/tube_psu_kicad (especially "Phase 5 – clean-up": the user
decisions and the steps done so far) and the playbook tools/p2k/CONVERSION_PLAYBOOK.md sections 3
"Phase 5" and 4. The user decisions are recorded in STATUS.md "Phase 5"; do not ask again.

Continue Phase 5 with the first step that STATUS.md does not list as done:
  3a footprint bodies / courtyards from the Proteus silk (tools/silk_bodies.py measures them, spec key
     body_poly in p2k.footprints), 3c NonConductor copper lines -> silk, 3d dangling stubs / one-layer GND
     via removed (config keys + both Phase 4 checks), stale layout values checked, 3b refdes placement
     (generator step in tools/make_pcb.sh).
All in the generators (not by hand in the board); after a change: tools/gen_footprints.py, the sheet
scripts, kipy -m p2k.check_footprints --pcbnew, tools/make_pcb.sh, tools/check_all.sh. Every board change
must keep ipc356_diff and gerber_roundtrip passing; update their accepted lists / config keys where a
deliberate difference results and say so in STATUS.md.

Rules: a problem in the original design is reported, not silently fixed. Shared-tool changes go into
tools/p2k (proteus2kicad, branch main) with the ac_psu regression (STATUS.md "Regression procedure";
ac_psu in a git worktree on a local branch based on p2k-phase4, never its main checkout, never push it,
leave .git/config submodule.tools/p2k.url = https://github.com/johonkanen/proteus2kicad.git, remove the
worktree with rm -rf + git worktree prune). Temporary files in build/tmp (excluded from git). Never run
the KiCad AppImage with --version. Commit here (not push) after each step; keep STATUS.md and
next_prompt.md current at each commit.
```
