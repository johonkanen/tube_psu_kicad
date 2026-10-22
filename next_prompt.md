# Next prompt

Ready-to-paste prompt for the next agent session (Phase 1 transcription, sheets 5 and 1).
Replaced at the end of every phase or session, see PLAN.md section 9.

```
Read PLAN.md and STATUS.md in /home/jari/dev/tube_psu_kicad (especially STATUS.md "Phase 1
preparation" findings, the "Transcription rules" and "Phase 1 transcription" with the ERC
warnings, symbol changes, PWR_FLAG placement and the findings per sheet), and the playbook
tools/p2k/CONVERSION_PLAYBOOK.md section 3 (Phase 1 transcription). Use Fable 5.1.
Sheets 11, 2, 9, 8, 10, 4, 3, 6 and 7 are drawn (tools/sheets/sheetNN.py; board block helpers
si8274_cell, ixdd609_cell, lmh6658_diffamp, sh_value in tools/sheets/_common.py, iso_channel in
sheet03.py, gate_net in sheet07.py – read a few of them first, they show the drawing style).
Continue one sheet per turn: sheet 5 (PFC, 35 parts: mains input IN1/IN2/PE terminals, relay RL1
with Q9 bypass driver, common-mode chokes CM1/CM4 (symbol SCF20-05-550, windings P1(3)-P2(4) and
S1(1)-S2(2)), X/Y caps, bridge DB1 (TBS22K), PFC chokes L1/L2 (RM8_INDUCTOR, pins 1/2 are
no-connect bobbin pins), Q5/Q6 (C2M0160120D on the IRFP460 device, 1=G 2=D 3=S), SiC diodes
SICD1/2 (pins A/K), shunts R93/R21, R4/R5/R6 -> RES_IN), then sheet 1 (AUX supply, 49 parts).
Sheet 5 generates DC+ and GND: put their permanent PWR_FLAGs there and remove the temporary ones
on sheet 11 (STATUS.md "PWR_FLAG placement"); PE, AC1, AC2, RES_IN, IN2 nets: check which are
power symbols (PE is not in the 15-rail list -> label) and whether a flag is needed (terminals
are passive). Sheet 1 generates 20V, 5V, 5V_ISOL, 20V_ISO_SEC, ISO_GND, -5V_SEC, -100V BIAS:
flags there, remove the temporary ones on sheets 11 and 2.

Per sheet NN (= PDF page):
- Read source/schematic_pdf/hi-NN.png (200 dpi render; crop/zoom with PIL as needed) and
  source/schematic_pdf/schematic_text.txt; parts of the sheet: lib/part_map.csv (sheet == NN,
  with lib_id and value); pin -> net truth: reference/pin_nets_by_component.md; which nets
  reach other sheets (global labels) vs one-sheet nets (local labels): derive from
  reference/ipc356_pads.json (a list of pad dicts with refdes/pin/net) + lib/part_map.csv (a
  10-line script: for each pad, the sheet of its refdes; a net is global when its pads lie on
  more than one sheet).
- Write tools/sheets/sheetNN.py (from _common import *; p2k.sheetkit helpers; rebuilds
  kicad/NN_*.kicad_sch from scratch), run it with python3, render it with
  tools/p2k/bin/p2k render_sheet kicad/NN_*.kicad_sch and look at the PNG (crop the cells).
  Note vert2/horiz2 place the part centre; the pins are 3 grid units from it (centre = row + g(3)
  puts the top pin on the row). A pin or power-symbol point must be a wire END (split wires at
  it), a label anchored mid-wire gets the wire drawn through its box (use a stub). Symbol pin
  positions: print them with p2k.sch_builder.lib() (see the previous sessions' approach) before
  planning the geometry – e.g. Transformer-type symbols have pin 2 bottom-left.
- Check: tools/p2k/bin/p2k compare_netlists --allow-missing --sheet NN and tools/erc.sh.
  Target: 0 missing parts on that sheet, 0 compare errors, 0 ERC errors; explain any ERC
  warning in STATUS.md. Net names = IPC names (PDF aliases and lowercase spellings are listed
  in the rules; sheet 5 PDF: gate1/gate2 = GATE1/GATE2, "PFC drain 1" / "pfc drain 2" = PFC
  DRAIN 1 / PFC DRAIN 2, "PFC current 2+/3+" = PFC CURRENT 2+/3+, res_in = RES_IN, in2 = IN2,
  DC+/GND terminals = power nets). Then tools/check_all.sh.
- Do not change the symbol library, the part map or the tools without saying why in STATUS.md;
  a symbol or pinout problem is reported, not silently worked around (playbook principle 7).
  Known: a no_connect-type pin is dropped from the KiCad netlist – if the IPC has a net on such
  a pin, the pin type must be changed in tools/gen_symbols.py (as done for SI8274 pin 2). After
  a gen_symbols.py change run python3 tools/gen_symbols.py (check_all verifies the library is
  up to date) and re-run every sheet script that uses the symbol.
- Small leftover: none (sheet 4's V4 crossing was fixed in this session).

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
  erc: 0 errors, 28 warnings (reports/erc.rpt)   (20 permanent single-pin J2 labels, 5 isolated global labels of sheet 5, 3 ground_pin_not_ground on the Si8274/Si8271 high-side returns)
  compare: parts 231/315 present, 84 missing, 0 extra; pins compared 657, wrong-net pins 0
  compare: per sheet (drawn/total) 1:0/49 2:20/20 3:29/29 4:27/27 5:0/35 6:47/47 7:46/46 8:15/15 9:23/23 10:18/18 11:6/6
  ALL CHECKS PASSED
(if tools/p2k is empty: git submodule update --init)

Done for this session when: sheets 5 and 1 are drawn with 0 missing parts on them, 0 compare
errors and 0 ERC errors (then all 315 parts are present: run compare_netlists without
--allow-missing and switch tools/check_all.sh to that once it passes; every IPC net complete);
tools/check_all.sh passes; STATUS.md "Phase 1 transcription" is extended (sheets done,
compare/ERC output, warnings explained, PDF oddities found, flags moved); next_prompt.md is
replaced with the prompt for the next step (Phase 2 footprints, PLAN.md section 3); committed
(not pushed); the session ends with that prompt.
```
