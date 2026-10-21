# Next prompt

Ready-to-paste prompt for the next agent session (Phase 0). Replaced at the end of every
phase, see PLAN.md section 9.

```
Read PLAN.md in /home/jari/dev/tube_psu_kicad and the playbook
/home/jari/dev/ac_psu_kicad/CONVERSION_PLAYBOOK.md. Use Opus 5.5.
Start Phase 0 (PLAN.md section 2) for the tube_power_5_1 Proteus -> KiCad 10.0.7 migration.
Sources are in source/ (PDF + page renders + text, CADCAM export of 2026-10-21 with the
IPC-D-356A netlist in source/cadcam/, the .pdsprj). Reuse the tools of
/home/jari/dev/ac_psu_kicad/tools (copy, adapt; the playbook section 4 says which are
generic). KiCad: ~/kicad/kicad-10.0.7-x86_64.AppImage (never run it with --version, it hangs;
use --appimage-mount, see ac_psu tools/kicad_env.sh).

First ask the user: re-export the CADCAM with Gerber X2 attributes enabled (recommended,
PLAN.md section 1 point 1), or classify the gerber objects geometrically?

Then: project layout, tools/bin wrappers, tools/ipc356.py adapted to this netlist (blank-refdes
vias/free pads/unplated holes, truncated terminal refdes restored from the PDF, a KiCad refdes
map for names with spaces or signs, GND=POWER alias, letter pin ids), reference tables,
README.md, STATUS.md, tools/check_all.sh.

Done when: tools/check_all.sh passes with the IPC parser self-check asserting 1165 records
(502 THT / 663 SMD), 283 vias, 8 unplated holes, 4 free pads, 315 refdes, 9 N/C; the
reference tables exist; STATUS.md has a Phase 0 section; next_prompt.md holds the Phase 1
preparation prompt; committed; the session ends with that prompt.
```
