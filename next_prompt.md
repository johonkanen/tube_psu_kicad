# Next prompt

Ready-to-paste prompt for the next agent session (Phase 5 – clean-up, user decisions first).
Replaced at the end of every phase or session, see PLAN.md section 9.

```
Read PLAN.md and STATUS.md in /home/jari/dev/tube_psu_kicad (especially "Phase 4 – independent
verification": the two new checks, the reviewed findings, the per-refdes pad-size table and the "Open user
decisions" list) and the playbook tools/p2k/CONVERSION_PLAYBOOK.md sections 3 "Phase 5" and 4. Phases 0–4
are complete: the schematic (315/315 parts, 208/208 IPC nets, ERC 0 errors), the footprints (fit
≤ 0.037 mm), the generated board kicad/tube_psu.kicad_pcb (tools/make_pcb.sh, byte-identical rebuild,
0 shorts / 0 opens / 0 unconnected / 0 parity) and the independent verification against the Proteus
CADCAM files: p2k ipc356_diff (1165/1165 records, 193 nets 1:1, 0 mismatches) and p2k gerber_roundtrip
(0 unexplained copper clusters, 0 uncovered draws/flashes, 502/502 drills incl. the Excellon
cross-check). Every remaining difference is a pad shape / KiCad pad clearance or a recorded decision.

Phase 5 (optional clean-up) – ASK THE USER FIRST, then implement only what was decided:
1. Pad sizes of the 143 parts on Proteus pads (STATUS.md Phase 4 table): keep all (default), narrow the
   Proteus pads to the 22 DRC-conflicting refdes (U2 U3 U6 V2 V3 V4, AD1 AD2, Q9 REF1, DRV3, DRV5, C28 C37
   C56, J2, R40, R79 R88 R109, C25 C92 – a `refdes` condition in tools/gen_footprints.py RULES), or
   FOOTPRINT_PAD_SIZES = "proteus" everywhere. After a change: tools/gen_footprints.py, all
   tools/sheets/sheetNN.py, kipy -m p2k.check_footprints --pcbnew, tools/make_pcb.sh, tools/check_all.sh.
2. KiCad drills smaller than Proteus (Q5/Q6 TO-247 1.5 vs 1.651, C_Disc + J4 1.0 vs 1.016, C64/C66 1.0 vs
   1.067): keep (DRILL_SMALLER in p2k_config.py) or Proteus drills (derived footprints with ipc_sizes or
   a drill override; then remove the DRILL_SMALLER entries so the checks enforce it).
3. SICD1/SICD2 (TO-220-2): body side and pin 1 – the Proteus silk puts the body/tab line on the other side
   of the pin row than KiCad's TO-220-2_Vertical (coordinates in STATUS.md). Needs the physical part or
   the built board; if the footprint is mirrored, re-check pin-1 mark, body side and courtyard.
4. C102 outline (UCS2G560MND9 on a 10 mm / 5 mm-pitch footprint), free pads WP1–WP4 as board-only
   footprints vs plain pads, RM8 footprint body from the Proteus silk (19.7 mm RM outline, not centred on
   the pads; would remove the 3 accepted courtyard errors H4/L2, C64-1/L2, C66-1/L1), other IPC-built
   bodies from the silk (EF20/EF25/ETD34, CM chokes, relay, bridge), silk/refdes positions (199 + 199
   warnings), the 18 floating NonConductor copper lines (keep / move to silk), the 6 dangling stubs and
   the one-layer GND via, the stale layout values (24 parts, STATUS.md Phase 1).
5. ac_psu_kicad: the local branches p2k-footprints → p2k-pcb → p2k-phase4 carry the shared-tool moves and
   pass check_all.sh + regen_check.sh; merging/pushing them is the user's call.
6. When the user starts editing the board in KiCad: stop regenerating it (remove the make_pcb --check step
   from tools/check_all.sh, say so in STATUS.md); the IPC diff and the gerber round trip keep working on
   the edited board and will then show the intended differences.

Rules: do not change the symbol library, the part map, the sheets, the footprint rules or the board
generation without saying why in STATUS.md; a problem in the original design is reported, not silently
fixed (playbook principle 7). Shared-tool changes go into tools/p2k (proteus2kicad) with the ac_psu
regression (STATUS.md "Regression procedure"; ac_psu is worked on in parallel – use a git worktree on a
local branch based on p2k-phase4, never touch its main checkout, never push it, leave .git/config
submodule.tools/p2k.url as https://github.com/johonkanen/proteus2kicad.git, remove the worktree by
rm -rf + git worktree prune). Tools: tools/p2k/bin/kicad-cli and tools/p2k/bin/kipy mount the KiCad
AppImage on demand (`kipy -m p2k.TOOL`, `p2k TOOL`); never run the AppImage with --version (hangs). Use
the scratchpad directory for temporary files. Commit here (not push) at each completed step; keep
STATUS.md and next_prompt.md current at each commit.

Verify state first: tools/check_all.sh (≈ 6 min; the round trip alone ≈ 2.5 min). At handoff it ended with
  drc: 562 violations, 0 shorts, 0 unconnected, 0 parity issues (reports/drc.json)
  ipc356_diff: Proteus 1165 records, KiCad 1149; matched 1165 (870 pads incl. 15 N/C, 283 vias (16 stacked duplicate via records on matched vias), 8 holes, 4 free pads), worst position offset 0.038 mm (limit 0.05)
  ipc356_diff: 193 Proteus nets mapped 1:1 onto KiCad nets, 0 mismatches
  roundtrip: F.Cu   XOR   65.91 mm^2, beyond 0.05 mm: only Proteus   4.73, only KiCad  37.74 mm^2; clusters >= 0.01 mm^2: 134 pad shape, 10 clearance; draws/flashes off the other copper: 0 Proteus, 0 KiCad
  roundtrip: In1.Cu XOR   82.65 mm^2, beyond 0.05 mm: only Proteus   4.35, only KiCad  57.90 mm^2; clusters >= 0.01 mm^2: 90 pad shape, 13 clearance; draws/flashes off the other copper: 0 Proteus, 0 KiCad
  roundtrip: In2.Cu XOR   93.59 mm^2, beyond 0.05 mm: only Proteus   5.05, only KiCad  68.61 mm^2; clusters >= 0.01 mm^2: 99 pad shape, 18 clearance; draws/flashes off the other copper: 0 Proteus, 0 KiCad
  roundtrip: B.Cu   XOR  109.22 mm^2, beyond 0.05 mm: only Proteus   8.40, only KiCad  66.06 mm^2; clusters >= 0.01 mm^2: 281 pad shape, 12 clearance; draws/flashes off the other copper: 0 Proteus, 0 KiCad
  roundtrip: drills 0 mismatches, 16 stacked duplicate Proteus records; KiCad drill smaller, accepted (DRILL_SMALLER): 12x 1.016->1.0, 4x 1.0668->1.0, 6x 1.651->1.5; report reports/roundtrip/roundtrip.txt, overlays reports/roundtrip/*.png
  ALL CHECKS PASSED
(full output in STATUS.md "Phase 4 – Last verification"; if tools/p2k is empty: git submodule update --init)

Done for this session when: the decided clean-ups are implemented in the generators (not by hand in the
board), tools/make_pcb.sh rebuilt the board, tools/check_all.sh passes with the accepted DRC counts
updated, STATUS.md has a "Phase 5" section (what was decided, what changed, the new check output) and
next_prompt.md is replaced ("done" if nothing is left); committed (not pushed); the session ends with
that prompt.
```
