# Next prompt

Ready-to-paste prompt for the next agent session (Phase 1 transcription, sheets 3, 6, 7, ...).
Replaced at the end of every phase or session, see PLAN.md section 9.

```
Read PLAN.md and STATUS.md in /home/jari/dev/tube_psu_kicad (especially STATUS.md "Phase 1
preparation" findings, the "Transcription rules" and "Phase 1 transcription" with the ERC
warnings, symbol changes, PWR_FLAG placement, findings so far and the "Sheet 3 – in progress"
notes), and the playbook tools/p2k/CONVERSION_PLAYBOOK.md section 3 (Phase 1 transcription).
Use Fable 5.1.
Sheets 11, 2, 9, 8, 10 and 4 are drawn (tools/sheets/sheet11.py, sheet02.py, sheet09.py,
sheet08.py, sheet10.py, sheet04.py; board block helpers si8274_cell, ixdd609_cell,
lmh6658_diffamp, sh_value in tools/sheets/_common.py – read them first, they show the drawing
style). Continue one sheet per turn: sheet 3 (Isolated measurements, 29 parts – nothing drawn yet;
the analysis and a suggested geometry are in STATUS.md "Sheet 3 – in progress": two identical
ISO/ADC/op-amp/regulator channels, write a channel function in sheet03.py), then sheet 6
(Heaters, 47 parts), then sheet 7 (DHB, 46 parts) if the session allows (order: 3 → 6 → 7 → 5 → 1).
Small leftover: redraw V4 on sheet 4 without the GND/EN wire crossing (STATUS.md says how).

Per sheet NN (= PDF page):
- Read source/schematic_pdf/hi-NN.png (200 dpi render; crop/zoom with PIL as needed) and
  source/schematic_pdf/schematic_text.txt; parts of the sheet: lib/part_map.csv (sheet == NN,
  with lib_id and value); pin -> net truth: reference/pin_nets_by_component.md; which nets
  reach other sheets (global labels) vs one-sheet nets (local labels): derive from
  reference/ipc356_pads.json + lib/part_map.csv (a 10-line script: for each pad, the sheet of
  its refdes; a net is global when its pads lie on more than one sheet).
- Write tools/sheets/sheetNN.py (from _common import *; p2k.sheetkit helpers; rebuilds
  kicad/NN_*.kicad_sch from scratch), run it with python3, render it with
  tools/p2k/bin/p2k render_sheet kicad/NN_*.kicad_sch and look at the PNG (crop the cells).
  Note vert2/horiz2 place the part centre; the pins are 3 grid units from it (centre = row + g(3)
  puts the top pin on the row).
- Check: tools/p2k/bin/p2k compare_netlists --allow-missing --sheet NN and tools/erc.sh.
  Target: 0 missing parts on that sheet, 0 compare errors, 0 ERC errors; explain any ERC
  warning in STATUS.md. Net names = IPC names (PDF aliases and lowercase spellings are listed
  in the rules). Then tools/check_all.sh.
- PWR_FLAGs: when you draw the sheet that generates a rail (sheet 5: DC+, GND; sheet 1: 20V, 5V,
  5V_ISOL, 20V_ISO_SEC, ISO_GND; sheet 6: terminals HT_6V3/HT_GND – check whether 6V3 and HT_GND
  need a flag), put the flag there and remove the temporary one (sheets 11, 2 – see STATUS.md
  "PWR_FLAG placement"). +3V3 and +2V5_BIAS are settled on sheet 4.
- Do not change the symbol library, the part map or the tools without saying why in STATUS.md;
  a symbol or pinout problem is reported, not silently worked around (playbook principle 7).
  Known: a no_connect-type pin is dropped from the KiCad netlist – if the IPC has a net on such
  a pin, the pin type must be changed in tools/gen_symbols.py (as done for SI8274 pin 2). The
  SI8661 channel-E pins were corrected the same way (STATUS.md "Symbol changes").

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
  erc: 0 errors, 45 warnings (reports/erc.rpt)   (20 permanent single-pin J2 labels, 23 isolated global labels of undrawn sheets, 2 ground_pin_not_ground on the Si8274 high-side returns)
  compare: parts 109/315 present, 206 missing, 0 extra; pins compared 331, wrong-net pins 0
  compare: per sheet (drawn/total) 1:0/49 2:20/20 3:0/29 4:27/27 5:0/35 6:0/47 7:0/46 8:15/15 9:23/23 10:18/18 11:6/6
  ALL CHECKS PASSED
(if tools/p2k is empty: git submodule update --init)

Done for this session when: sheets 3 and 6 (at least) are drawn with 0 missing parts on them,
0 compare errors and 0 ERC errors; tools/check_all.sh passes; STATUS.md "Phase 1 transcription"
is extended (sheets done, compare/ERC output, warnings explained, PDF oddities found, flags
moved); next_prompt.md is replaced with the prompt for the next sheets; committed (not pushed);
the session ends with that prompt.
```
