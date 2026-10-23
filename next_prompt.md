# Next prompt

Ready-to-paste prompt for the next agent session (Phase 3 – PCB).
Replaced at the end of every phase or session, see PLAN.md section 9.

```
Read PLAN.md and STATUS.md in /home/jari/dev/tube_psu_kicad (especially STATUS.md "Phase 0"
"Findings that matter for Phase 2/3", "Phase 2 – footprints" – decisions, the footprint table,
the footprint_fit.csv summary, the pad size / drill differences and the open user decisions – and
the "Shared tools" regression procedure), and the playbook tools/p2k/CONVERSION_PLAYBOOK.md
sections 3 "Phase 3 – PCB", 4 (shared tools) and 5 (pitfalls: pours, thermal reliefs, Flip before
Add, KIID seeds). Phases 0–2 are complete: 11 sheets drawn, 315/315 parts, every IPC net complete,
ERC 0 errors / 23 expected warnings, every symbol carries a footprint, all 315 footprints fit the
IPC pads within 0.039 mm (reports/footprint_fit.csv has kicad_x / kicad_y / kicad_orientation per
part), tools/check_all.sh passes.

Phase 3 (PLAN.md section 5): the PCB.
1. Look at how ac_psu did it (read only: ~/dev/ac_psu_kicad tools/build_pcb.py, gerber_to_tracks.py,
   assign_nets.py, pours_to_zones.py, board_common.py, check_board.py, drc.py, make_pcb.sh and its
   STATUS.md "Phase 3"). Move the generic parts into the tools/p2k submodule with config keys
   (design rules, layer stack, mounting-hole / free-pad footprints, accepted DRC types, no-net pins
   such as the RM8 bobbin pins) – commit + push there, bump the submodule here; any shared-tool
   change needs the ac_psu regression (STATUS.md "Regression procedure"; note that ac_psu_kicad is
   being worked on in parallel – run its checks in a worktree or clean clone of its HEAD, commit
   there on a branch, never push it). Board specifics stay in tools/make_pcb.sh / p2k_config.py.
2. build_pcb: kicadxml netlist export, board with the outline from "Mechanical 1" (163 × 110 mm at
   (−71.9, −18.7)), 4 copper layers (Top Copper, Inner  1, Inner 14, Bottom Copper → F.Cu, In1.Cu,
   In2.Cu, B.Cu; pour outlines on User.1–4, p2k_config.py COPPER), one footprint per symbol placed
   with the Phase 2 recipe (position (x, −y), top SetOrientationDegrees(angle), bottom Flip(pos,
   LEFT_RIGHT) then (180 + angle) % 360), symbol path links for DRC parity, pad nets from the
   netlist. Board-only items: the 8 unplated 3.0 mm holes with 3.5 mm copper rings on every copper
   layer (NPTH footprint with no-net copper pads, at the IPC "hole" records), the 4 free wire pads
   (plated, 2.55 mm drill / 4.0 mm pad, nets Q14_DRAIN, 6V3 ×2, Q13_DRAIN – board-only footprints
   or plain pads; decide with the user, default: one-pad footprints with the net), the 283 vias
   (0.3 / 0.381 drills), copper graphics without net (NonConductor draws). Design rules from the
   measured Proteus gaps (not stricter than the copper as built); board thickness from the Proteus
   stack if known, else ≈1.58 mm.
3. gerber_to_tracks (X2 aperture functions: Conductor draws = tracks, ViaPad flashes = vias,
   regions = pours), assign_nets (nets from the pads, 0 shorts / 0 opens after zone fill),
   pours_to_zones; check_board (pads, 283 vias, 8 holes, 4 free pads vs IPC within 0.05 mm, nets
   1:1) and drc (0 shorts, 0 unconnected, 0 parity issues; accepted violation types listed with
   reasons – courtyard overlaps are normal on a Proteus placement). Expect the first DRC to flag
   KiCad pads larger than Proteus' that reach Proteus tracks → per footprint, decide with the user
   whether to switch to the Proteus sizes (p2k_config.py FOOTPRINT_PAD_SIZES = "proteus" switches
   all footprints; `ipc_sizes=True` on a PROJECT spec in tools/gen_footprints.py switches one –
   then re-run gen_footprints.py and the sheet scripts). The KiCad drills smaller than Proteus
   (Q5/Q6 TO-247 1.5 vs 1.651, C_Disc 1.0 vs 1.016, C64/C66 1.0 vs 1.066, J4 1.0 vs 1.016) are
   listed in STATUS.md – ask the user.
4. Add every step to tools/check_all.sh (make_pcb.sh regenerates the board; check_board, DRC);
   keep ERC / compare / footprint checks at 0 errors. Negative-test check_board (moved via,
   wrong net on a pad).
5. STATUS.md "Phase 3" (design rules chosen, accepted DRC types with reasons, user decisions,
   check outputs), next_prompt.md → Phase 4 (independent verification: gerber_roundtrip,
   ipc356_diff, fresh-session review).

Rules: do not change the symbol library, the part map, the sheets or the footprint rules without
saying why in STATUS.md (sheet scripts may be re-run); a pinout or layout problem is reported, not
silently worked around (playbook principle 7). Tools: tools/p2k/bin/kicad-cli and tools/p2k/bin/kipy
mount the KiCad AppImage on demand (`kipy -m p2k.TOOL` for shared tools that need pcbnew; board
scripts put tools/p2k on sys.path themselves); never run the AppImage with --version (hangs). Use
the scratchpad directory for temporary files. Commit here (not push) at each completed step; keep
STATUS.md and next_prompt.md current at each commit.

Verify state first: tools/check_all.sh. At handoff it printed
  pcbnew 10.0.7
  ipc356: nets=193, records=1165, refdes_raw=316, tht_records=502, smd_records=663, smd_top=225, smd_bottom=438, nc_pads=9, vias=283, free_pads=4, holes=8, parts=315
  check_sources: OK
  make_part_map: lib/part_map.csv up to date (315 parts)
  gen_symbols: lib/tube_psu.kicad_sym up to date (46 symbols)
  symbols: 30 part types, 315 refdes, 15 power symbols / symbols: OK
  erc: 0 errors, 23 warnings (reports/erc.rpt)
  compare: parts 315/315 present, 0 missing, 0 extra; pins compared 846, wrong-net pins 0; IPC nets touched 208, complete 208
  gen_footprints: 315 parts, 43 footprints (22 project), up to date
  check_footprints: pcbnew placement of 315 parts, worst pad offset 0.039 mm
  check_footprints: 315/315 parts fitted, 870 pads, 43 footprints, worst residual 0.039 mm (limit 0.05)
  ALL CHECKS PASSED
(if tools/p2k is empty: git submodule update --init)

Done for this session when: kicad/tube_psu.kicad_pcb is rebuilt by tools/make_pcb.sh from the
schematic and the gerbers, check_board and drc pass (0 shorts, 0 unconnected, 0 parity issues,
every accepted DRC type explained), both are in tools/check_all.sh and it passes, STATUS.md has a
"Phase 3" section, next_prompt.md is replaced with the Phase 4 prompt; committed (not pushed); the
session ends with that prompt.
```
