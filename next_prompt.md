# Next prompt

Ready-to-paste prompt for the next agent session (Phase 1 transcription, first sheets).
Replaced at the end of every phase or session, see PLAN.md section 9.

```
Read PLAN.md and STATUS.md in /home/jari/dev/tube_psu_kicad (especially STATUS.md "Phase 1
preparation" with the findings and the "Transcription rules"), and the playbook
tools/p2k/CONVERSION_PLAYBOOK.md section 3 (Phase 1 transcription). Use Fable 5.1.
Phase 1 preparation is done. Transcribe the Proteus schematic into KiCad, one sheet per turn,
starting with sheet 11 (Startup, 6 parts), then sheet 2 (DHB gate drive, 20 parts); continue
with sheet 9 and 8 if the session allows (order in STATUS.md).

Per sheet NN (= PDF page):
- Read source/schematic_pdf/hi-NN.png (200 dpi render; crop/zoom with PIL as needed) and
  source/schematic_pdf/schematic_text.txt; parts of the sheet: lib/part_map.csv (sheet == NN,
  with lib_id and value); pin -> net truth: reference/pin_nets_by_component.md.
- Write tools/sheets/sheetNN.py (from _common import *; p2k.sheetkit helpers; rebuilds
  kicad/NN_*.kicad_sch from scratch), run it with python3, render it with
  tools/p2k/bin/p2k render_sheet kicad/NN_*.kicad_sch and look at the PNG.
- Check: tools/p2k/bin/p2k compare_netlists --allow-missing --sheet NN and tools/erc.sh.
  Target: 0 missing parts on that sheet, 0 compare errors, 0 ERC errors; explain any ERC
  warning in STATUS.md. Net names = IPC names (PDF aliases and lowercase spellings are listed
  in the rules). Then tools/check_all.sh.
- Do not change the symbol library, the part map or the tools without saying why in STATUS.md;
  a symbol or pinout problem is reported, not silently worked around (playbook principle 7).

Tools: tools/p2k/bin/kicad-cli and tools/p2k/bin/kipy mount the KiCad AppImage on demand;
never run the AppImage with --version (hangs). Shared tool changes go into the tools/p2k
submodule (commit + push there, bump here) and need the ac_psu regression (STATUS.md
"Regression procedure"); prefer board helpers in tools/sheets/_common.py.

Verify state first: tools/check_all.sh. At handoff it printed
  pcbnew 10.0.7
  ipc356: nets=193, records=1165, refdes_raw=316, tht_records=502, smd_records=663, smd_top=225, smd_bottom=438, nc_pads=9, vias=283, free_pads=4, holes=8, parts=315
  check_sources: OK
  make_part_map: lib/part_map.csv up to date (315 parts)
  gen_symbols: lib/tube_psu.kicad_sym up to date (46 symbols)
  symbols: 30 part types, 315 refdes, 15 power symbols / symbols: OK
  erc: 0 errors, 0 warnings (reports/erc.rpt)
  compare: parts 0/315 present, 315 missing, 0 extra; ... compare: OK
  ALL CHECKS PASSED
(if tools/p2k is empty: git submodule update --init)

Done for this session when: sheets 11 and 2 (at least) are drawn with 0 missing parts on them,
0 compare errors and 0 ERC errors; tools/check_all.sh passes; STATUS.md has a "Phase 1
transcription" section (sheets done, compare/ERC output, warnings explained, PDF oddities
found); next_prompt.md is replaced with the prompt for the next sheets; committed; the session
ends with that prompt.
```
