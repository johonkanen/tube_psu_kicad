# Next prompt

Ready-to-paste prompt for the next agent session (Phase 1 preparation). Replaced at the end
of every phase, see PLAN.md section 9.

```
Read PLAN.md and STATUS.md in /home/jari/dev/tube_psu_kicad, and the playbook
/home/jari/dev/ac_psu_kicad/CONVERSION_PLAYBOOK.md (Phase 1 preparation). Use Opus 5.5.
Phase 0 is done. Start the Phase 1 preparation (PLAN.md section 3) for the tube_power_5_1
Proteus -> KiCad 10.0.7 migration. Do not transcribe sheets yet (that is the Fable sessions).

Read first: STATUS.md "Findings that matter for Phase 1" (terminal refdes map, net names with
spaces, L1-L3 pins without net, letter pin ids), reference/pin_nets_by_component.md and
reference/ipc356_pads.json (column `refdes` = KiCad refdes, `refdes_proteus`, `refdes_raw`),
source/schematic_pdf/schematic_text.txt and hi-NN.png (11 sheets).
Tools: the shared proteus2kicad repo is the submodule tools/p2k (a git clone of
https://github.com/johonkanen/proteus2kicad; board values in p2k_config.py, keys in
tools/p2k/README.md). Run tools with tools/p2k/bin/p2k <tool> (system python3) or
tools/p2k/bin/kipy -m p2k.<tool> (pcbnew); tools/p2k/bin/kicad-cli. Never run the AppImage
with --version (hangs). KiCad symbol libraries are in the mount at <mount>/share/kicad/symbols
(mount path in /tmp/p2k_kicad_mount.<uid>).
Move (do not copy) the ac_psu Phase 1 tools from /home/jari/dev/ac_psu_kicad/tools into
tools/p2k/p2k/: check_symbols.py, compare_netlists.py, make_skeleton.py, and the generic part of
gen_symbols.py (the symbol list itself is board data: keep it in each board repo, e.g.
tools/symbols.py, and let the shared generator read it). Replace hard-coded ac_psu names/paths
with p2k_config.py keys (document new keys in tools/p2k/README.md); grep for ac_psu refdes/net
names first. ac_psu is the regression test (STATUS.md "Regression procedure"): switch its
tools to the moved versions on its branch p2k-submodule (or main if the user has merged it),
bump its submodule, and require its tools/check_all.sh and tools/regen_check.sh to pass with
its committed files unchanged. Commit in tools/p2k and push to origin main; commit the
submodule bumps in both repos (do not push ac_psu without asking).

Verify state first: tools/check_all.sh. At handoff it printed
  pcbnew 10.0.7
  ipc356: nets=193, records=1165, refdes_raw=316, tht_records=502, smd_records=663, smd_top=225, smd_bottom=438, nc_pads=9, vias=283, free_pads=4, holes=8, parts=315
  check_sources: OK
  ALL CHECKS PASSED
(if tools/p2k is empty: git submodule update --init)

Steps:
1. lib/part_map.csv: refdes -> sheet (PDF page), symbol, value, part number for all 315 parts
   (IPC refdes list decides; values from the PDF text layer/renders, part numbers from
   `strings` of ROOT.DSN inside source/tube_power_5_1.pdsprj).
2. tools/gen_symbols.py -> lib/tube_psu.kicad_sym: KiCad std symbols flattened with pins
   renumbered to the IPC ids, box symbols with Proteus pin names for ICs/transformers/chokes/
   relay/bridge/J2/terminals (two pads numbered 1); power symbols for the rails. --check.
   Decide power symbols vs global labels per rail (ERC multiple_net_names, playbook pitfalls).
3. tools/check_symbols.py: symbol pin set == IPC pin set per refdes (L1-L3 pins 1/2 without
   net are still pins).
4. tools/compare_netlists.py (pad-set comparison, --sheet N, terminal refdes via the KiCad
   names already in ipc356_pads.json).
5. Test how KiCad 10 handles net labels with spaces (`PFC DRAIN 1`, `-100V BIAS`) and `$`; if
   needed define a net-name map and record it in STATUS.md.
6. tools/make_skeleton.py: kicad/tube_psu.kicad_pro, sym/fp-lib-tables, root sheet with 11
   hierarchical sheets (titles from PLAN.md section 1; read page 10's title from the render).
7. Transcription rules in STATUS.md (power symbols, label spelling = IPC, global vs local
   labels, N/C pins, single-pin nets, grid 1.27 mm, sheet order of PLAN.md section 3).
8. Add the new checks (symbols up to date, symbol pins vs IPC, ERC, compare) to
   tools/check_all.sh.

Done when: all 315 parts in lib/part_map.csv with symbol and value; symbol library generated and
check_symbols passes for all parts; the empty skeleton passes ERC and compare (0 parts drawn,
0 errors); tools/check_all.sh passes; STATUS.md has the Phase 1 preparation section and the
transcription rules; next_prompt.md holds the Fable prompt for the first sheet(s) (sheet 11
startup, then 2 DHB gate drivers); committed; the session ends with that prompt.
```
