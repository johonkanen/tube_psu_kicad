# Next prompt

Ready-to-paste prompt for the next agent session (Phase 2 – footprints).
Replaced at the end of every phase or session, see PLAN.md section 9.

```
Read PLAN.md and STATUS.md in /home/jari/dev/tube_psu_kicad (especially STATUS.md "Phase 0" and
"Phase 1 preparation" findings – pinout oddities REF1 / Q9 / Q1-Q2 / TBS22K, the TR2 centre taps,
the free wire pads, the unplated holes with copper rings – and the "Phase 1 transcription"
section), and the playbook tools/p2k/CONVERSION_PLAYBOOK.md section 3 "Phase 2 – footprints"
and section 4 (shared tools). Phase 1 is complete: all 11 sheets are drawn
(tools/sheets/sheetNN.py → kicad/NN_*.kicad_sch), tools/check_all.sh passes with
compare_netlists without --allow-missing (315/315 parts, 208/208 IPC nets complete, 0 wrong-net
pins) and ERC 0 errors / 23 expected warnings.

Phase 2 (PLAN.md section 3): footprints.
1. Look at how ac_psu did it (read only, do not modify ~/dev/ac_psu_kicad): its
   tools/gen_footprints.py, check_footprints.py, lib/footprint_map.csv, lib/*.pretty and the
   STATUS.md Phase 2 notes. Move the generic parts (fpgeom is already in p2k; footprint
   generation / fitting helpers) into the tools/p2k submodule with config keys instead of
   hard-coded values (commit + push there, bump the submodule here), keeping this board's
   specifics in tools/gen_footprints.py and p2k_config.py. Any shared-tool change needs the
   ac_psu regression (STATUS.md "Regression procedure").
2. tools/gen_footprints.py → lib/footprint_map.csv (refdes → footprint) and lib/tube_psu.pretty.
   Assign by symbol + IPC pad pattern (reference/ipc356_pads.json: pad count, span, size, drill,
   side); derive project footprints from KiCad footprints (renumber pads to the Proteus ids, move
   pad centres onto the Proteus positions) or build them from the IPC pads where KiCad has
   nothing. Special cases: the 12 PIN terminals (two THT holes both numbered 1), the EF25/EF20/
   ETD34 bobbins (TR2 pins 1,2,4,5,6,7,9,10; TR1 10 pins; TR3 pins with 3 pads each), the RM8
   chokes L1/L2/L3 (winding pads pri1/pri2 + two bobbin pins 1/2 without net), Q1/Q2 LFPAK with
   three source pads numbered 1, the SOT-23 parts with Proteus pin ids (Q9 1=D 2=G 3=S, REF1
   1=GND 2=VIN 3=VOUT – check whether the IPC pad positions match the datasheet order), the
   4-terminal shunts if any, C102 (UCS2G560MND9 snap-in), the SMD-on-bottom parts (438 bottom
   SMD pads). Decide with the user: KiCad pad sizes (default) vs Proteus pad sizes.
3. tools/check_footprints.py (or the shared p2k tool): per refdes, match pads by number and
   solve the rigid transform onto the IPC pad centres (fail > 0.05 mm); --pcbnew places each
   footprint with pcbnew and re-measures; writes reports/footprint_fit.csv (side, angle, KiCad
   position / orientation) for Phase 3. Negative-test it (shift a pad 0.1 mm, swap two pad
   numbers).
4. Fill the Footprint field of the symbols from the map (p2k.sch_builder.footprint(ref) reads
   lib/footprint_map.csv – check) by re-running all sheet scripts; add the steps to
   tools/check_all.sh; keep ERC/compare at 0 errors.
5. Board-only items for Phase 3 (note them, no decision needed yet): 4 free wire pads (nets
   Q14_DRAIN, 6V3 x2, Q13_DRAIN), 8 unplated 3.0 mm holes with 3.5 mm copper rings on every
   layer, 283 vias, copper graphics without net.

Rules: do not change the symbol library, the part map or the sheets without saying why in
STATUS.md (sheet scripts may be re-run to fill footprint fields); a pinout problem is reported,
not silently worked around (playbook principle 7). Tools: tools/p2k/bin/kicad-cli and
tools/p2k/bin/kipy mount the KiCad AppImage on demand; never run the AppImage with --version
(hangs). Use the scratchpad directory for temporary files. Commit here (not push) at each
completed step; keep STATUS.md and next_prompt.md current at each commit.

Verify state first: tools/check_all.sh. At handoff it printed
  pcbnew 10.0.7
  ipc356: nets=193, records=1165, refdes_raw=316, tht_records=502, smd_records=663, smd_top=225, smd_bottom=438, nc_pads=9, vias=283, free_pads=4, holes=8, parts=315
  check_sources: OK
  make_part_map: lib/part_map.csv up to date (315 parts)
  gen_symbols: lib/tube_psu.kicad_sym up to date (46 symbols)
  symbols: 30 part types, 315 refdes, 15 power symbols / symbols: OK
  erc: 0 errors, 23 warnings (reports/erc.rpt)   (20 permanent single-pin J2 labels, 3 ground_pin_not_ground on the Si8274/Si8271 high-side returns)
  compare: parts 315/315 present, 0 missing, 0 extra; pins compared 846, wrong-net pins 0; IPC nets touched 208, complete 208
  compare: per sheet (drawn/total) 1:49/49 2:20/20 3:29/29 4:27/27 5:35/35 6:47/47 7:46/46 8:15/15 9:23/23 10:18/18 11:6/6
  ALL CHECKS PASSED
(if tools/p2k is empty: git submodule update --init)

Done for this session when: lib/footprint_map.csv and lib/tube_psu.pretty exist for all 315
parts, every footprint fits the IPC pads within 0.05 mm (check in tools/check_all.sh,
negative-tested), the symbols carry their footprints, tools/check_all.sh passes, STATUS.md has a
"Phase 2" section (decisions, pinout findings confirmed or refuted against the pads, the
footprint_fit.csv summary), next_prompt.md is replaced with the Phase 3 prompt; committed (not
pushed); the session ends with that prompt.
```
