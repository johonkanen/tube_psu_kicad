# Next prompt

Ready-to-paste prompt for the next agent session (Phase 4 – independent verification).
Replaced at the end of every phase or session, see PLAN.md section 9.

```
Read PLAN.md (section 6) and STATUS.md in /home/jari/dev/tube_psu_kicad (especially "Phase 3 – PCB":
steps, design rules, the Phase 3 pad-size change, remaining DRC items, findings such as the stacked
duplicate vias, and the "Shared tools" regression procedure), and the playbook
tools/p2k/CONVERSION_PLAYBOOK.md sections 3 "Phase 4", 4 (shared tools) and 5 (pitfalls). Phases 0–3 are
complete: schematic (315/315 parts, 208/208 IPC nets, ERC 0 errors), footprints (fit ≤ 0.037 mm) and
kicad/tube_psu.kicad_pcb rebuilt by tools/make_pcb.sh from the schematic and the Proteus gerbers
(shared tools p2k.build_pcb / gerber_to_tracks / assign_nets / pours_to_zones; check_board, assign_nets
--check, DRC 0 shorts / 0 unconnected / 0 parity). You are the independent reviewer: do not trust the
earlier sessions' claims, verify them.

Phase 4 (PLAN.md section 6):
1. Move ac_psu's gerber_roundtrip.py and ipc356_diff.py (read only: ~/dev/ac_psu_kicad tools/, and its
   STATUS.md "Phase 4") into the tools/p2k submodule (proteus2kicad) with config keys instead of board
   values (tolerances, raster grid, expected differences, deviation hooks like p2k.check_board's
   added / extra_vias); commit + push there, bump the submodule here. Shared-tool changes need the
   ac_psu regression: ac_psu_kicad is worked on in parallel – use a git worktree on a local branch based
   on its branch p2k-pcb (which already carries the Phase 2/3 tool moves), never touch its main checkout,
   never push it; its tools/check_all.sh and tools/regen_check.sh must pass with its committed files
   unchanged (STATUS.md "Regression procedure"). Note: a worktree shares .git/config – do not leave
   submodule.tools/p2k.url changed in the main repo.
2. This board's specifics: 283 IPC via records on 267 board vias (16 stacked duplicates – STATUS.md
   finding), 4 free pads (board-only WP1–WP4 with nets), 8 unplated 3.0 mm holes with 3.5 mm copper
   rings (H1–H8, NonPlated drill gerber), the renamed terminals (KICAD_REFDES in p2k_config.py; kicad-cli
   ipcd356 truncates refdes and long net names), RM8 bobbin pins without net, NonConductor copper graphics.
   gerber_roundtrip: copper XOR per layer with 0.05 mm tolerance, centre-line coverage of every draw and
   flash both ways, drills (plated + NonPlated; the RS-274X Excellon in source/cadcam_rs274x/ as an
   optional cross-check); classify the difference clusters (pad shape / clearance / zone fill / other =
   finding). ipc356_diff: kicad-cli pcb export ipcd356 vs the Proteus file – every pad/via/hole/free pad
   within 0.05 mm, side, THT/SMD, nets 1:1 by pad sets, N/C equal. Add both to tools/check_all.sh.
3. Review: read the generating scripts and config, spot-check the easy-to-get-wrong places (thermal
   reliefs, floating NonConductor graphics, mounting holes with copper rings, free pads, bottom-side
   parts, multi-pad pins (terminals, TR3, LFPAK Q1/Q2), the 45°/315° RM8 chokes, single-pin nets), the
   Phase 3 pad-size change (143 parts on Proteus pads: is each change forced by a DRC conflict?), and
   confirm or refute every earlier finding in STATUS.md.
4. Negative-test every new check (move a track, change a net, shift a pad 0.1 mm, delete a via, change a
   drill) and confirm it fails.
5. STATUS.md "Phase 4" (results, reviewed findings, open user decisions), next_prompt.md → Phase 5
   (clean-up, user decisions first) or "done".

Open user decisions (do not change without asking; list them again at the end): the Phase 3 pad-size
change (Proteus pads on 10 footprints / 143 parts, reversible – STATUS.md "Phase 3 – pad sizes"), the
KiCad drills smaller than Proteus (Q5/Q6 TO-247 1.5 vs 1.651, C_Disc 1.0 vs 1.016, C64/C66 1.0 vs 1.066,
J4 1.0 vs 1.016), C102's outline, the SICD pin-1 assumption, free pads as one-pad footprints vs plain
pads, mounting hole H4 inside the RM8 choke L2's area.

Rules: do not change the symbol library, the part map, the sheets, the footprint rules or the board
generation without saying why in STATUS.md; a problem in the original design is reported, not silently
fixed (playbook principle 7). Tools: tools/p2k/bin/kicad-cli and tools/p2k/bin/kipy mount the KiCad
AppImage on demand (`kipy -m p2k.TOOL`); never run the AppImage with --version (hangs). Use the
scratchpad directory for temporary files. Commit here (not push) at each completed step; keep STATUS.md
and next_prompt.md current at each commit.

Verify state first: tools/check_all.sh. At handoff it printed
  pcbnew 10.0.7
  ipc356: nets=193, records=1165, refdes_raw=316, tht_records=502, smd_records=663, smd_top=225, smd_bottom=438, nc_pads=9, vias=283, free_pads=4, holes=8, parts=315
  check_sources: OK
  make_part_map: lib/part_map.csv up to date (315 parts)
  gen_symbols: lib/tube_psu.kicad_sym up to date (46 symbols)
  symbols: 30 part types, 315 refdes, 15 power symbols
  erc: 0 errors, 23 warnings (reports/erc.rpt)
  compare: parts 315/315 present, 0 missing, 0 extra; pins compared 846, wrong-net pins 0; IPC nets touched 208, complete 208
  compare: per sheet (drawn/total) 1:49/49 2:20/20 3:29/29 4:27/27 5:35/35 6:47/47 7:46/46 8:15/15 9:23/23 10:18/18 11:6/6
  gen_footprints: 315 parts, 44 footprints (29 project), up to date
  check_footprints: pcbnew placement of 315 parts, worst pad offset 0.038 mm
  check_footprints: 315/315 parts fitted, 870 pads, 44 footprints, worst residual 0.037 mm (limit 0.05)
  build_pcb: 315 footprints placed (0 excluded from board), 8 mounting holes, 4 free pads, 208 nets, 4 outline segments
  gerber_to_tracks: 3412 tracks, 267 vias (IPC 283, 16 stacked duplicate via records merged), 85 pour outlines on User.1-4
  assign_nets: stage A (no pours): 510 groups, 0 shorts, 52 orphans, 32 opens
  assign_nets: stage B (with pours): 216 groups, 0 shorts, 0 orphans, 0 opens
  pours_to_zones: 85 pours -> 85 zones; 161 holes closed by the stroke, 847 holes kept
  make_pcb: board rebuilt from scratch, byte-identical
  check_board: 327 footprints, 870 pads, worst pad offset 0.038 mm (limit 0.05), 193 IPC nets mapped 1:1, 8 mounting holes, 4 free pads
  check_board: 3412 tracks, 267 vias, 85 zones
  assign_nets: after zone fill: 216 groups, 0 shorts, 0 orphans, 0 opens, 0 items with a foreign net
  assign_nets: OK (report reports/assign_nets.txt)
  drc: 562 violations, 0 shorts, 0 unconnected, 0 parity issues (reports/drc.json)
  drc:    149 error    courtyards_overlap  accepted: KiCad courtyards vs the Proteus placement
  drc:      6 error    pth_inside_courtyard  accepted: KiCad courtyards vs the Proteus placement
  drc:      1 error    npth_inside_courtyard  accepted: mounting hole H4 inside the RM8 choke L2's pad-box courtyard (Proteus placement)
  drc:    199 warning  silk_overlap
  drc:    199 warning  silk_over_copper
  drc:      6 warning  track_dangling
  drc:      1 warning  via_dangling
  drc:      1 warning  silk_edge_clearance
  ALL CHECKS PASSED
(if tools/p2k is empty: git submodule update --init)

Done for this session when: gerber_roundtrip and ipc356_diff are shared tools, in tools/check_all.sh and
pass here (every remaining difference classified and explained), ac_psu regression OK, every new check
negative-tested, the review is written to STATUS.md "Phase 4" with every earlier finding confirmed or
refuted, next_prompt.md is replaced; committed (not pushed); the session ends with that prompt.
```
