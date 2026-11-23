# kicad_next – tube_power 5.2 (KiCad project `tube_psu_5_2`)

The next board revision, forked from the verified 5.1 migration in `kicad/` (which stays frozen and is
checked by `tools/check_all.sh`). What changes is in [../NEXT_REVISION.md](../NEXT_REVISION.md), the
phases and decisions D1–D6 in [../NEXT_REVISION_PLAN.md](../NEXT_REVISION_PLAN.md).
State: **phase 3 done (2026-11-18)** – footprints and 3D models for every part, creepage slots (section
"Footprints and 3D models" below); **phase 2 done (2026-11-18)** – schematic changes of NEXT_REVISION.md applied (item-by-item list, open
questions and the generated netlist diff 5.1 → 5.2: [CHANGES_5_2.md](CHANGES_5_2.md)); phase 1 (2026-11-17):
6-layer board skeleton, stackup, JLC rules, net classes per isolation domain, creepage / clearance rules.

## What is where

| Path | Content | Made by |
|---|---|---|
| `kicad_next/tube_psu_5_2.kicad_pro` | project: ERC settings (as 5.1), net classes + netclass patterns (one per net), board minimums (JLC) | copied from 5.1 once; classes / rules by `tools/next/setup_project.py` |
| `kicad_next/tube_psu_5_2.kicad_sch` + `01_…11_*.kicad_sch` | schematic (root + 11 sheets) | `tools/next/gen_schematic.py` (do not edit by hand while the scripts are the source) |
| `kicad_next/tube_psu_5_2.kicad_pcb` | **the 5.2 board** (since 2026-11-20): placement of trial step 3 (all 375 footprints, slots, keep-outs, the kept 5.1 copper), 5.1 outline, H1–H8, 6 copper layers, JLC stackup; not routed yet | skeleton by `tools/next/make_board.py`, then `tools/next/promote_trial_board.py` (kipy) once from the step-3 trial board; **from here on edited in KiCad / by the routing (phase 5/6), only checked** |
| `kicad_next/tube_psu_5_2.kicad_dru` | custom rules: JLC limits, HV functional spacing, creepage / clearance between domains | by hand (this file is the source) |
| `kicad_next/sym-lib-table`, `fp-lib-table` | `tube_psu_next` → `lib/tube_psu_next.kicad_sym` (used), `tube_psu` → `lib/tube_psu.kicad_sym` (5.1, reference); footprints `tube_psu` → `lib/tube_psu.pretty`, `tube_psu_next` → `lib/tube_psu_next.pretty`, `tube_psu_next_parts` → `lib/tube_psu_next_parts.pretty` | `gen_schematic.py` |
| `tools/next/sheets/sheetNN.py`, `_common.py` | sheet scripts, copies of `tools/sheets/` (sheet scripts unchanged; `_common.py` redirects output, symbol library, CSVs) | phase 2 edits these |
| `tools/next/gen_symbols.py` → `lib/tube_psu_next.kicad_sym` | 5.2 symbols (fork of `tools/gen_symbols.py`; identical output at the fork) | phase 2 adds ICE5AR (PWM2, replaced the iW1819), SI8621, UCC21520, … |
| `lib/part_map_next.csv`, `lib/footprint_map_next.csv`, `lib/jlc_parts_next.csv` | values, footprints, LCSC numbers per refdes – hand-edited forks of the 5.1 tables | by hand |
| `tools/next/check_next.sh` | all 5.2 checks (below) | – |
| `tools/next/gen_next_footprints.py` → `lib/tube_psu_next.pretty` | EEL19 / EC42 transformers, L1/L2 upright toroid on the 5.1 RM8 holes (`_Vertical_RM8_45deg` / `_315deg`, 2026-11-19; the flat toroid + `_TieSlots` unused), heatsink outline helper | phase 3 |
| `tools/next/gen_next_footprints_parts.py` → `lib/tube_psu_next_parts.pretty` | SOIC-16W with creepage slot (`_Slot8.0`, `_Slot11.1`), electrolytics with the real can height (`_H<n>mm`), copies of 5.1 footprints with a 3D model (reads KiCad library footprints from the AppImage: run through `tools/p2k/bin/kicad_env.sh`) | phase 3 |
| `tools/next/gen_next_3d.py` → `lib/tube_psu_next.3dshapes` | 16 simple STEP models (CadQuery venv, see below) | phase 3 |
| `tools/next/reuse_51_board.py` (kipy) → `kicad_next/trial_from_51/` step 0, `tools/next/trial_placement.py` (kipy) → step 1, `tools/next/trial_placement_p2.py` (kipy) → step 2, `tools/next/trial_placement_p3.py` (kipy) → step 3, `tools/next/trial_report.py` → `REPORT.md` | trial 5.2 board from the verified 5.1 layout (step 0: footprints / nets / copper reuse, L1 / L2 upright on the RM8 holes); step 1: TR3 / split caps / DRV5 / DRV6 moves as data (`PLACE` / `GROUPS`) + split-pass DRC; step 2: UART island at the top edge, Q19 / Q21 / ISO2 L-slot, ISO2 / D4 / D5, TR1 / PWM2 / C102 flyback re-place, gate-driver bootstrap / decoupling parts (`PLACE` / `AUTO` / `GROUPS` / `SLOTS` / `KEEPOUTS`, deleted copper listed in `placement_p2.json`); step 3: heater barrier slot at ISO1 / TR2 + pour keep-outs, relay driver Q9 moved under RL1, PE / mounting-hole keep-outs and C85, the 54 added parts placed from the off-board grid (`PLACE` / `NEW` / `GROUPS` / `FOOTPRINTS` / `SLOTS` / `KEEPOUTS` / `DELETE` / `TEXTS`, ISO1 with its board-specific T-slot footprint, mounting-hole pad moves, deleted copper listed in `placement_p3.json`); the latest step is checked by `check_domains.py` in check_next.sh, its DRC only by the placement scripts | phase 5 input |
| `tools/next/check_domains.py` [BOARD] | isolation-domain distance check of a board (check_next.sh: the real board; default: the latest trial step): straight same-layer distance between pads / tracks / vias / filled zone copper of two domains and the mounting holes (PE), limits = the `.kicad_dru` rules, slot credit only where a slot blocks the straight line (path round the slots), accepted pairs in its commented `ALLOW` list; ≈ 10 s, a few hundred MB – KiCad's creepage DRC does not list every pair | phase 5 / 6 |
| `tools/next/promote_trial_board.py` (kipy) | copies `trial_from_51/tube_psu_5_2_trial_p3.kicad_pcb` to the real board, 3D model paths back to `${KIPRJMOD}/../lib`, Description / LCSC fields from the schematic (refuses to overwrite a populated board without `--force`) | phase 5 start |
| `tools/next/route_s2_planes.py` (kipy), `tools/next/render_inner_layers.py` | routing stage 2: inner-layer planes / pours `S2_*` of the real board (re-runnable, section "Inner layers (routing stage 2)"); PNGs of the inner layers in `kicad_next/routing/` | phase 6 |
| `tools/next/route_s3a_power.py`, `tools/next/s3_router.py` (python3 + kipy), `tools/next/render_s3a.py` | routing stage 3a: power / HV / ground copper as data (drawn tracks, zones `S3A_*`, vias, connections routed by a local grid router that keeps the class, HV and domain spacings), re-runnable (`routing/s3a_added.json`), PE pour keep-outs `S3A_KO_PE_*`; PNGs `routing/s3a_*.png` (section "Power, HV and ground routing (stage 3a)") | phase 6 |
| `tools/next/route_s3c_cleanup.py` | routing stage 3c: kept 5.1 copper that breaks the 5.2 HV spacing deleted and drawn again, dangling 5.1 copper deleted (`routing/deleted_s3c.json`, `s3c_added.json`); runs between stage 3a and stage 3b (section "Clean-up of the kept 5.1 copper (stage 3c)") | phase 6 |
| `tools/next/route_s3d_iso2.py` | routing stage 3d: ISO2 / AD2 fan-out on both sides as drawn copper, the 420V sense divider as a row with its feed, R10 / R79 moved (`routing/moves_s3d.json`, `deleted_s3d.json`, `s3d_added.json`); runs between stage 3c and stage 3b (section "ISO2 / AD2 fan-out (stage 3d)") | phase 6 |
| `tools/next/route_s3e_j2.py` | routing stage 3e: the J2 header escapes and the open nets that end at J2 as drawn copper - analog lines, the control bus round mounting hole H4, the DRV3 / DRV5 inputs, HT_SDATA at ISO1 (`routing/deleted_s3e.json`, `s3e_added.json`, `moves_s3e.json`); runs between stage 3d and stage 3b (section "J2 escapes and J2 nets (stage 3e)") | phase 6 |
| `tools/next/check_board.py` | DRC of the real board without the creepage pass (> 3 GB on the populated board) + `--schematic-parity`: fails on any parity item, short or isolation-rule violation besides `ACCEPTED`; everything else counted (`reports/next/drc.json`, ≈ 2.3 GB, 10 s) | phase 5 |
| `tools/next/check_footprints.py` | footprint / pad / 3D / barrier-creepage check (kipy), `--dump` for `render_footprints.py` (PNGs) | phase 3 |
| `tools/next/netlist_diff.py` | netlist diff 5.1 → 5.2 (section of CHANGES_5_2.md) + check that the three CSVs cover every part | phase 2 |
| `kicad_next/CHANGES_5_2.md` | phase-2 change list per NR item, open questions, netlist diff | phase 2 |

How the fork avoids touching shared code: `p2k.sheetkit.sheet()` hard-codes `kicad/`, and
`p2k.sch_builder` reads `lib/<PROJECT>.kicad_sym` / `lib/footprint_map.csv` of `p2k_config.py`.
`tools/next/sheets/_common.py` therefore defines its own `sheet()` (output `kicad_next/` or
`$TUBE_PSU_NEXT_OUT`, project `tube_psu_5_2`), replaces `sch_builder.lib` / `sch_builder.footprint` at module
level and wraps `Sheet.save` to rename the library nickname `tube_psu_5_2:` → `tube_psu_next:`. Symbol
UUIDs are seeded as in 5.1, so unchanged parts keep their 5.1 UUIDs. `tools/p2k`, `tools/sheets/`,
`kicad/` and the 5.1 `lib/` files are unchanged.

## Regenerate / check

```
python3 tools/next/gen_symbols.py                 # lib/tube_psu_next.kicad_sym (after editing build())
python3 tools/next/gen_schematic.py               # kicad_next/*.kicad_sch from tools/next/sheets
python3 tools/next/setup_project.py               # net classes / domains / board minimums -> .kicad_pro
python3 tools/next/setup_project.py --list        # every net with its class
tools/next/check_next.sh                          # everything below, prints ALL 5.2 CHECKS PASSED
```

`check_next.sh` steps: symbol library up to date; schematic regenerated in a temporary directory equals
`kicad_next/` byte for byte; part footprints up to date; ERC (0 errors / 14 warnings after phase 2:
12 isolated_pin_label + 2 ground_pin_not_ground on the UCC21520 high-side VSSA); every net in
exactly one isolation domain and the project file up to date; board skeleton (6 layers, names / types,
stackup thicknesses, outline and H1–H8 equal to `kicad/tube_psu.kicad_pcb`); DRC 0 violations;
`check_rules.py` – kicad-cli silently drops a broken `.kicad_dru` rule, so 13 pairs of test tracks are
added to a temporary copy of the board and the DRC must report exactly the expected violation at each
(creepage 11.1 / 8.0 / 4.2 / 3.2 mm, inner-layer 11.1 / 8.0 mm, clearance 4.0 mm, HV functional 1.2 mm,
mounting hole; phase 2 adds 4 UART-island cases: 19 in total); `netlist_diff.py --check` (CHANGES_5_2.md netlist
section up to date, every part in the three CSVs with the schematic value / footprint). Phase 3 adds:
`gen_next_footprints.py --check`, `gen_next_footprints_parts.py --check`, `gen_next_3d.py --check` (only if
CadQuery is found at `$CQ_PYTHON` or `~/.venvs/cq/bin/python`, else skipped) and `check_footprints.py`.
Trial placement step 3 (2026-11-19) adds: 3 pad tests in `check_rules.py` (VSSOP-8 pads 0.15 mm apart: allowed
on low-voltage nets by the rule "Same-footprint pad gap, low-voltage classes", still a clearance violation on a
HV net; 22 tests in total); `check_footprints.py` also checks the board-specific footprint variants
(`BOARD_VARIANTS`: ISO1 with the T slot, non-convex slot outlines handled exactly); and `check_domains.py` on the
board (the latest trial board until 2026-11-20, now `kicad_next/tube_psu_5_2.kicad_pcb`) – every pair of copper items of two isolation domains on the same layer against the
clearance / creepage / inner-layer limits of the `.kicad_dru` (table `LIMITS`), with slot credit only where a
slot blocks the straight line; exit status 1 on any pair below its limit that is not in its `ALLOW` list (empty
since routing stage 4k; it held the Q19 / Q21 slot exception and the TR1 pin 2 / 9 barrels). Stage 1 of the routing (2026-11-20, the trial board
becomes the real board) replaces the plain DRC step (0 violations required, full creepage DRC) by `check_board.py`
and lets `make_board.py --check` accept internal Edge.Cuts slots inside the unchanged 5.1 outline.

## First draft (2026-11-22)

State after the clean-up pass `tools/next/route_s6_cleanup.py --group clr,dangling` (stage 6; incremental, not
re-runnable; `routing/deleted_s6.json`, `s6_added.json`, `moves_s6.json` (empty)): every connection of the netlist is
made, 0 shorts, 0 unconnected, `tools/next/check_next.sh` passes. This is the first complete draft, not a board
checked for ordering. No part moved in this pass. PNGs of all six copper layers of this state: `routing/s3a_F_Cu.png`,
`s3a_B_Cu.png`, `In1_GND.png` ... `In4_GND.png`, overviews `inner_domains.png`, `s3a_power_nets.png`
(`render_s3a.py`, `render_inner_layers.py`).

### DRC (check_board.py, without the creepage pass and without silkscreen checks)

| type | before | now | what is left and why |
|---|---|---|---|
| shorts / unconnected / parity | 0 | 0 | |
| clearance | 5 (7 with `--all-track-errors`) | 0 | Net class gaps 0.2 mm that were 0.16 ... 0.175 mm: EPWM5A_ISO In2 diagonal 0.09 mm further from the EPWM6A_ISO via (-48.89, -54.21); 5V on B.Cu 0.045 mm west (x -59.745, y -33.0 ... -26.5) past the pads of D9 and D28 pad A (two of the three pads were hidden behind the first marker); GND via (27.1, 5.1) -> (27.15, 5.1); Net-(C11-Pad1) via (28.4, 7.7) -> (28.45, 7.7); GND via (4.45, -56.9) -> (4.45, -56.95). The Net-(C11-Pad1) via now has 0.204 / 0.213 / 0.204 mm to the +1V65_BIAS track (F.Cu), R65 pad 2 and the Net-(C127-Pad1) track (B.Cu). |
| track_dangling | 26 | 0 | Pieces under / inside a wider track of the same net, zero-length segments, overshoots trimmed to the via / junction, and stubs to nothing (5.1 leftovers of moved parts) deleted back to the next junction, with two vias that only fed such a stub (15V (15.24, -35.02), 5V (-23.9, -53.036) with its In2 lane). The longest: a +3V3 In2 lane of 25 mm from (34.2, -28.6) to a free end at (16.8, -48.4), and a +3V3 In2 stub at the via (5.8, -60.1). The DC+ track of C47 ended in a round hole of 'Proteus F.Cu pour 29' at (45.62, -41.95); it now ends inside the fill at y -42.7. |
| courtyards_overlap | 132 | 132 | Classified by pad bounding boxes and F.Fab / B.Fab body boxes: 106 pairs stand at their 5.1 place (same relative place, side and turn; 17 of them with overlapping body boxes - film / electrolytic capacitors beside C86, C117, C37, C31 / C32 and the paralleled capacitors C99 / C100 / C101, C90 / C91 on the 420V rail. Correction (stage 7): those five were NOT as in 5.1 - change 5.6 made them 1210 (5.1: 1206) at the old 2.0 / 1.9 mm pitch, the bodies overlapped 0.5 / 0.6 mm; re-spaced in stage 7); 26 pairs are new or changed and courtyard-only (pads of two nets >= 0.238 mm apart, no body box overlap > 0.05 mm; same-net pads touch at C124 / R70, R90 / D34, R79 / R49, R90 / R70). No pair with a new pad or body collision, so no part was moved. |
| pth_inside_courtyard | 2 | 2 | Pin 1 of IN1 and pin 3 of CM1 inside the courtyard of the film capacitor C86 - as in 5.1 (the three parts are where they were). |
| starved_thermal | 2 | 2 | C102 pin 1 (ISO_GND, (77.0, 13.85)) on In1 and In4: the pin stands in a 1.5 mm neck of the ISO_GND plane, one spoke north and one south. The barrel joins both; bias capacitor, no current. Not changed (a solid connection of this pad was not tried to the end). |
| lib_footprint_mismatch | 2 | 2 | Q19 and Q21 (TO-220-3_Vertical): the board copies differ from the library footprint. Looked into in the verification: only the pad option 'remove unused inner-layer rings' differs (set on purpose, `trial_placement_p2.py`); ignored by `check_board.py` since stage 7. Packages: Q7 / Q8 / Q19 / Q21 (STF7N60M2) are TO-220, pin pitch 2.54 mm; only Q5 / Q6 are TO-247 - earlier notes that took Q7 / Q19 for TO-247 are wrong. |

### Not checked

* The creepage DRC pass of KiCad over the whole board (needs > 3 GB); the isolation distances are checked by
  `check_domains.py` only.
* Signal integrity of the UART pair: 82 mm on In3 between the pads of L2 and beside / under the power stages.
* The via-in-pad process. 71 vias lie in or touch an SMD pad of their own net (47 with the centre inside the pad):
  Q1 pad 3 (12), Q2 pad 3 (16), C73 pad 2 (10: 5 inside, 5 on the edge), C57 pad 2 (2), C89 pad 1 (2), R93 pad 2 (3),
  one via shared by C67 pad 1 / C70 pad 1 (18.3, -48.5) and one by D10 pad A / R142 pad 2 (36.8, 3.2), and one each
  at AD1 pad 3, AD2 pad 3, C125 pad 2, C139 pad 1, C22 pad 1, C27 pad 1, C68 pad 2, C79 pad 2, C80 pad 2, C95 pads 1
  and 2, DRV2 pad 1, DRV5 pad 11, Q9 pad 1, Q10 pad 1, R103 pad 1, R128 pad 1, R142 pad 1, R21 pad 1, R51 pad 2,
  R54 pad 2, R83 pad 1, R89 pad 1, U1 pad 4. Open: plugged vias at JLC or move them.
* Tight spots that pass: round DRV5 (x -10 ... 20, y -60 ... -40) the In2 control bus (nine lanes, 0.152 mm gaps
  for the 0.15 mm inner rule) and the four In3 lanes in the 15V window (0.158 mm) are at the rule by design; the
  +1V65_BIAS via (13.0, -44.076) is 0.164 mm from the $HT_CS and SYNCH_2 lanes. None was nudged (each lane has a
  neighbour on both sides). Pad gaps in that window were not listed.
* Assembly: the 26 courtyard-only pairs were not checked against real part bodies or a pick-and-place rule.

### Open inputs (user)

* Heatsink footprint and height against C73 (12.5, -14.0) and C87 (5.7, -59.4) on F.Cu.
* Measured body positions of L1 / L2.
* Bobbin measurements of the transformers.
* J2 pin 18.
* TR2 dot / turns.


## Stage 7: fixes after the draft verification (2026-11-22)

`tools/next/route_s7_fixes.py --group caps,r83,iso2` (incremental, not re-runnable; `routing/moves_s7.json`,
`deleted_s7.json`, `s7_added.json`). DRC after it: courtyards_overlap 132, pth_inside_courtyard 2, starved_thermal 2,
0 unconnected, 0 clearance, 0 dangling, 0 shorts; `check_next.sh` passes.

* **420V 1210 capacitors**: pitch 2.9 mm (body 2.5 mm, gap 0.4 mm; was 2.0 / 1.9 mm with 0.5 / 0.6 mm body overlap).
  F.Cu: C90 75.4 -> 74.7, C91 77.4 -> 77.6. B.Cu: C99 77.4 -> 78.3, C101 73.5 -> 72.5, C100 stays (75.4); y -75.425
  and the turn unchanged. All pads stay on the 420V / ISO_GND pours; under C101 two B.Cu patches (`S7_ISO_GND_B_C101`
  x 71.0 ... 73.2, `S7_420V_B_C101` x 71.0 ... 72.8) carry the pours 1.2 mm further west. The three courtyard pairs
  C90 / C91, C99 / C100, C100 / C101 still overlap (courtyard 3.29 mm wide, pitch 2.9); no courtyard pair with another
  part (the F side has 2.85 mm between the TR3 and C30 courtyards for a courtyard-clean pair, so not possible there).
* **R83 pad 2 (GND)**: there were three vias, not one - (17.96, -64.55) 0.5 / 0.3 on a 0.35 mm track and (17.25, -64.93),
  (18.55, -64.93) 0.6 / 0.3 on a 0.5 mm track that touched the first only by a 0.02 mm overlap. Now three 0.6 / 0.3
  vias on a 1.0 mm F.Cu bar (15.4 ... 18.55, y -64.73) that covers the lower half of the pad; south edge y -65.23
  as the via rings (UART island limit -65.255).
* **ISO2 pad 8 -> Net-(TR1-S15)**: a plain 0.3 mm shift east is not free (15V_ISO_SEC pad at x 72.5 ... 74.3,
  y -15.0 ... -13.8, 0.35 mm from the track). Instead the track leaves x 71.9 at y -15.9 on a diagonal straight into
  the D4 anode pad; the nearest point to ISO2 pad 8 moves from (71.9, -17.2) to (71.9, -15.9): straight distance
  9.68 -> about 10.35 mm, creepage round the slot 11.2 -> about 11.8 mm (estimate from the geometry, not re-measured).
* `check_board.py` ignores `lib_footprint_mismatch` (Q19 / Q21, see above).

Not done:

* **DC+ feed of C47** (89 mm, 55 mm of it a 1.5 mm track with 0.75 / 0.8 mm pieces at (45.62, -42.7 ... -47.3) -
  (41.5, -47.3)). Widening those pieces to 1.5 mm gives two `items_not_allowed` markers (a keep-out area there; which
  one was not looked up). A short path from the bridge was not found in the time: F.Cu is closed by the switch-node
  zone (x 12 ... 31, y -57.5 ... -52); on B.Cu the way south from C70 pad 1 (18.2, -48) passes between the 15V via
  (17.625, -51.0, In2 -> In3 change of the 15V bridge) and C70 pad 2 / the DHB_CURRENT vias (22.6, -49 / -50): 3.1 mm
  between via ring and pad corner, 0.7 mm left for a track at 1.2 mm HV spacing; In3 is closed by the 15V bridge
  (y -55.25 / x 17.6 / y -51.6 to x 24). It needs the 15V via / In2 diagonal (22.2, -46.4) - (17.6, -51.0) re-routed
  first (then B.Cu is free from y -53 to -72 at x 23.5 ... 27, and the south end can come up through vias at
  x >= 28.2 on the existing F.Cu track east of C47 pad 1; R146 on B.Cu at (24.25, -74.28) blocks vias in the pad).
* **C95** stays at (19.2, -51.6), 18 / 15 mm from DRV5 pins 11 / 9. B.Cu between the DRV5 pad rows is under the body
  of DRV5 (same side), not a place. B.Cu east of the pads: the high-side return (x 10.25 down to y -51.5, then y -52.06
  to Q19 pin 3) leaves 15V copper only x <= 8.8 north of y -53.5 (0.8 mm beside the pin pads); south of that are the
  gate track, the GND via (8.25, -54.345), the 5V via (9.0, -54.6), C11, R90, D34. F.Cu west of x 5: DC+ pour with
  a pocket x 3.0 ... 7.5, y -52.0 ... -49.5 that holds the 5V via (4.33, -50.75), and two 0603 parts at x 2.25 ... 4.5,
  y -56 ... -53.75; a 1206 (pads 4.45 x 1.8 mm plus 1.2 mm to DC+) does not fit. An 0603 might fit in the F.Cu pocket
  if the 5V via moves (estimate, not tried).

## Stage 7b: short DC+ connection to C47, C95 moved (2026-11-22)

`tools/next/route_s7b_c47_dc.py --group c95,r146,dc,old` (incremental, not re-runnable; `routing/moves_s7b.json`,
`deleted_s7b.json`, `s7b_added.json`). DRC before and after: courtyards_overlap 132, pth_inside_courtyard 2,
starved_thermal 2, 0 unconnected, 0 clearance, 0 dangling, 0 shorts; `check_next.sh` passes. This closes the two
"Not done" items of stage 7.

* **DC+ to C47 pad 1**: C70 pad 1 (B.Cu) -> 2.0 mm B.Cu south on x 18.3 (y -49.0 ... -51.2) -> 2.5 mm diagonal to
  (23.85, -56.75) -> 2.5 mm south on x 23.85 to y -70.9 -> three vias 0.8 / 0.4 at (22.95 / 23.85 / 24.75, -71.75)
  between the two pads of C47 -> F.Cu bar 2.2 mm (y -72.5) into the north edge of pad 1 (0.24 mm overlap over the
  bar length). About 25 mm from C70 pad 1, about 31 mm from Q19 pin 2 (F.Cu pour `S4B_DC+_F` 5.5 mm first); minimum
  width 2.0 mm. North end: the old via (18.3, -48.5) 0.6 / 0.3 plus two new 0.8 / 0.4 at (17.7 / 18.7, -50.0) from the
  F.Cu pour. Smallest spacings by construction 1.25 mm (R146 pads, TR3 pads 4 / 5 via the moved track, R22 track).
  The B.Cu GND pour opens along the path by the 1.2 mm rule.
* **Old feed deleted**: F.Cu (45.62, -42.7) ... (41.5, -47.3) - (41.5, -75.21) - (23.83, -75.21), 89 mm. Nothing
  else hung on it; unconnected stays 0 without it. The 0.4 mm F.Cu track from pad 1 south to the via (24.28, -88.08)
  (R143) stays.
* **DC bus to the bridge** is pour 29, not that track: bulk capacitors -> pour 29 -> (a) joint to `S4B_DC+_F` at
  y -44.6, x 14.5 ... 17.75 (about 3.2 mm) -> into the east side of Q19 pin 2 over about 1.2 mm of the pad height
  (the pour keeps 1.2 mm from the gate pad), and (b) pour 29 west of the pins, neck about 1.0 mm at x 9.75 ... 10.5,
  y -47 ... -48, into the west side of the pad over about 1.2 mm. Both zones connect solid. Widths read from a
  0.25 mm raster of the fill (estimates).
* **DHB_CURRENT to R146 pad 2** ran on B.Cu at x 25.28 in the middle of the corridor: via (25.28, -63.68) 0.8 / 0.4
  -> (26.85, -62.3) 0.6 / 0.3, F.Cu 0.4 mm into C54 pad 2, B.Cu 0.4 mm on x 26.85 (1.25 mm from the TR3 pads 4 / 5)
  to the pad.
* **15V**: the In3 bridge already started in the In3 east block at (24.0, -50.4), so the via (17.625, -51.0) and its
  In2 branch (24.897, -43.39) - (23.561, -43.39) - (22.225, -44.726) - (22.225, -46.4) - (17.625, -51.0) were a second
  feed and the pad of C95 only: deleted with the In3 stub. There is no In2 -> In3 change at the bridge any more; the
  In3 plane block feeds it. Negative control on a copy: without the piece (24.0, -51.6) - (17.625, -51.6) DRC shows
  1 unconnected (15V), with it 0.
* **C95**: B.Cu (19.2, -51.6) rot 180 -> B.Cu (18.9, -60.6) rot -90, south of the F.Cu switch-node zone. 15V pad
  north with a via in pad (18.9, -58.85) 0.6 / 0.3 on a new 1.0 mm In3 spur (17.125, -55.25) - (18.9, -57.025) -
  (18.9, -58.85) of the bridge; own GND via (18.9, -61.7) 0.6 / 0.3 (old GND via (20.4, -50.65) deleted). Copper path
  to DRV5 pin 11 about 18 mm as before (spur 4.4 mm for 4.45 mm); straight line 14.0 mm (was 10.7); GND via to the
  GND via of pin 9 12.9 mm (was 12.7). The 15V via stands 0.95 mm south of the switch-node zone outline (the fill
  retreats locally to 1.2 mm), the GND via in the F.Cu DHB_CURRENT pour (2 mm of pour left south of it). A place
  closer to pin 11 was not found (stage 7 list).

## Stage 12: UART TX / RX gap on the primary side widened (2026-11-23)

User decision 2026-11-23 (12 Mbaud): the two nets `/04 MCU connector/TX` and `/04 MCU connector/RX` ran side by side
from J2 to U11 with 0.19 - 0.2 mm between the 0.152 mm tracks. `tools/next/route_s12_uart_gap.py` (one-shot,
`routing/*_s12.json`) re-draws them 0.76 mm centre to centre = **0.608 mm edge to edge**, same lane, same layers
(In3 and B.Cu), no new via. Length of TX per track-to-track gap, and the route lengths:

| | < 0.25 mm | 0.25 - 0.45 | 0.45 - 0.6 | 0.6 - 1.0 | ≥ 1.0 | TX length | RX length |
|---|---|---|---|---|---|---|---|
| before | 102.2 mm | 16.3 | 1.7 | 8.0 | 3.6 | 131.90 mm | 127.74 mm |
| after | 0 | 0 | 0 | 120.6 | 10.8 | 131.44 mm | 128.67 mm |

* **In3:** TX keeps its line; RX, the outer track, moves out by 0.42 mm (towards the +3V3 zone edge / C28 on
  x 15 ... 35, towards pad 1 of L2). Two changes of TX: at the J2 end it runs west on y -28.45 (was y -27.54 after
  a step towards the RX via), and the 45° step between y -32.02 and y -34.92 is 4.23 mm further east (x 8.3 ... 5.4)
  so that RX clears the gate pad of Q5 (GATE1, 1.64 mm; was 0.79 mm). TX cannot move north on y -32.02: vias of
  Net-(DRV1-OUTL) / PFC_PWM1 at (9.40, -32.75) / (10.32, -32.79), 0.35 mm.
* **B.Cu at J2:** the RX legs on x 37.6 / 40.1 are on x 37.34 / 39.84 (TX on 38.1 / 40.6).
* **B.Cu at U11:** TX stays on x -5.2 (0.34 mm from the +3V3 track on x -4.68 at the island edge), RX is on x -5.96
  and passes **west** of the GND via of U11 pin 7 (-6.15, -74.83): the lane between that via and the +3V3 track is
  1.07 mm, too narrow for both tracks with 0.6 mm between them (RX was 0.22 mm from the via, now 0.32 mm on its
  other side; the via stands between the two tracks for 2.8 mm).
* **Not 0.6 mm, at the vias only** (each under 1 mm long): J2 end, via to via 0.47 mm and TX track (B.Cu) to RX via
  0.47 mm - the RX via (45.3, -27.55) cannot move south, +3V3 tracks on In2; U11 end of In3, via (-5.0, -57.5) /
  (-6.07, -57.5): via to via 0.57 mm, TX track to RX via 0.43 mm on In3, 0.57 mm on B.Cu.

Measured on the final board (plan view, `check_domains.py --dump` geometry):

* In2 tracks parallel above the In3 part (same direction, centre distance < 0.5 mm, > 5 mm): only **+3V3**, 5.0 mm
  (x 39.9 ... 44.95, the 0.3 / 0.508 mm tracks on y -26.87, 0.33 mm beside RX on y -27.2; 3.8 mm before). Shorter:
  PFC_PWM1 (0.4 mm, y -32.79) 1.3 mm straight above TX at x 14.8 ... 16.1 (0.08 mm off centre), as before.
* L2 (the pair passes between its pads on In3, y -34.92 / -34.16): TX to pad 2 (PFC_DRAIN_1) 1.46 mm (unchanged),
  RX to pad 1 (AC1) 0.98 mm (was 1.40); the pads are through-hole, the same on every layer. F.Cu: 9.0 mm of each
  track lie under the PFC_DRAIN_1 pour (x -3.9 ... 5.1; 8.4 - 8.7 mm before), the In1 GND plane is solid between
  them (before: 0.55 mm of RX under a gap of the plane); the AC1 pour is 0.58 mm (RX) / 1.34 mm (TX) away in plan
  view. B.Cu: the GATE1 track crosses under the pair (TX 0.55 mm, RX 1.4 mm of track above it; 2.25 / 2.46 mm
  before), In4 GND plane between. In2 / In3: no PFC copper within 4 mm except the L2 / Q5 pads. The B.Cu part of
  the pair has no PFC net within 4 mm on any layer.

Unconnected 0, 0 shorts, clearance 0, dangling 0, parity 0, DRC 137 items as before; `check_next.sh` passes.

## Stage 11: J4 as 1×6 header, UART island re-routed (2026-11-23)

User decision 2026-11-23: the UART link runs at 12 Mbaud, single-ended, between two FPGA boards, so J4 gets a ground
pin beside each signal: **1 ISO_UART_GND, 2 UART_TXD (in), 3 ISO_UART_GND, 4 UART_RXD (out), 5 ISO_UART_GND,
6 UART_3V3 (in)** (was 1×4: GND / 3V3 / TXD / RXD). Symbol `CONN_01X06`, footprint `PinHeader_1x06_P2.54mm_Vertical`,
part XFCN PZ254V-11-06P C492405 (part page read 2026-11-23; stock and price not shown there). Schematic from
`sheets/sheet04.py`; board by `tools/next/route_s11_j4.py` (one-shot, `routing/*_s11.json`):

* J4 stays at (11.4, -89.0), rot 0: pin 1 at y -89.0, pin 6 at y -76.3 (two pins further south). Pads end at x 12.25;
  nearest primary copper in plan view: the DHB_CAP B.Cu track on x 20.68 - 8.23 mm from pin 6, 8.33 mm from pin 5;
  the island keep-out edge x 20.25 is 8.00 mm from the pads. `check_domains.py` passes.
* RXD (R137 - pin 4) is unchanged, 3.7 mm. TXD: F.Cu 0.2 mm from R136 round the west of pins 4 / 3 on x 9.9 to pin 2,
  12.3 mm from R136. The order 3V3 / RXD / TXD at U11 (pins 14 / 13 / 12) is the reverse of the order at J4 (pins 6 /
  4 / 2), so UART_3V3 goes on B.Cu, 0.3 mm, from a via in C135 pad 1 (7.0, -80.425) to pin 6, 6.1 mm.
* Ground (the island is a pour keep-out on every layer, no plane): B.Cu 0.3 mm bus on x 10.05 joining pins 1 / 3 / 5,
  directly under the F.Cu TXD lane, tied to the ground via of U11 pin 16 / C135 (6.25, -81.275); U11 pin 9 keeps its
  B.Cu link to that via. The 12 Mbaud signals have a ground pin beside them in the cable but no ground plane under
  the 4 - 12 mm of track on the island.

Unconnected 0, 0 shorts, clearance 0, dangling 0, parity 0, DRC 137 items as before (courtyards_overlap 133,
pth_inside_courtyard 2, starved_thermal 2); `check_next.sh` passes. Older text in this file says 4-pin header.

## Stage 10: mounting hole H5 removed (2026-11-23)

User decision 2026-11-23: H5 at (87.15, -29.81) on the east edge is not used and the board does not droop without it.
`tools/next/route_s10_no_h5.py` (one-shot, `routing/deleted_s10.json`) deletes the footprint and its pour keep-out
(secondary 4.2 mm); the ISO_GND pours fill the freed area. Seven holes are left (H1 - H4, H6 - H8;
`make_board.py --check` compares these with 5.1). No track was moved; the 420V detour round H5 (stage 3 text below)
is still there and could be shortened. Older text in this file says H1 - H8.

## Stage 9: no DC+ on inner layers (2026-11-23)

User decision 2026-11-23: DC+ and its GND return are kept on F.Cu / B.Cu, not on inner layers (the In1 / In4 GND
planes of the stackup are unchanged). `tools/next/route_s9_no_inner_dc.py` (one-shot, `routing/deleted_s9.json`)
deletes the only two DC+ items on In3 and the two vias that fed nothing else:

* the 1.8 mm In3 track (12.75, -49.52) - (18.7, -49.52) into Q19 pin 2 of stage 8 (2): the DC+ entry of Q19 is the
  F.Cu one again, 0.9 + 0.9 mm (5.1: about 2.3 mm);
* zone `S4L_DC+_In3_neck` of stage 4l and the vias (10.2 / 11.3, -17.5): the neck at SICD1 is F.Cu about 1.25 mm +
  B.Cu 1.0 mm track = 2.25 mm (was 4.45 mm with In3; 0.75 - 0.8 mm before stage 4l).

DC+ copper now: F.Cu, B.Cu and vias only. GND besides the planes: nine 0.15 mm signal-ground pieces on In2
(x -62 ... -42, y -42 ... -33), no power current. Unconnected 0, 0 shorts, clearance 0, dangling 0, DRC 137 items
as before (courtyards_overlap 133, pth_inside_courtyard 2, starved_thermal 2); `check_next.sh` passes.

## Stage 8: C95 as 0603 at DRV5 pins 11 / 9, DC+ into Q19 pin 2 on In3 (2026-11-22)

`tools/next/route_s8_c95_dc.py --group c95,old` and `--group dc` (incremental, not re-runnable; `routing/moves_s8.json`,
`deleted_s8.json`, `s8_added.json`). DRC before: courtyards_overlap 132, pth_inside_courtyard 2, starved_thermal 2,
0 unconnected, 0 clearance, 0 dangling, 0 shorts, 0 parity. After: courtyards_overlap 133 (new pair C95 / DRV5, 0.39 mm:
the 0603 stands 0.21 mm beside the pin pads), the rest unchanged; `check_next.sh` passes.

* **C95 4.7u 1206 -> 0603** (user decision, CHANGES_5_2.md row 3.1c): `lib/part_map_next.csv`,
  `lib/footprint_map_next.csv`, `lib/jlc_parts_next.csv` (C6119856, 4.7 uF X5R 25 V, the part of C17 / C52 / C79 / C80;
  was C29823 X7R 50 V), schematic regenerated. `update_board_parts.py` does not change a footprint id, so the script
  replaces the footprint (entry `REPLACE`: library footprint at the new place, fields / path / pad nets kept);
  `update_board_parts.py C95` afterwards only set the LCSC field. Compared with the board before: no other pad,
  track or via changed its net.
* **Place**: B.Cu (8.66, -53.72) rot -90, standing north-south east of the DRV5 pin row. Pad 2 (15V) at
  (8.66, -52.945), pad 1 (GND) at (8.66, -54.495); both 0.21 mm east of the pin pads (edge x 7.975 / 8.185).
  15V: 0.5 mm B.Cu track pin 11 -> (8.5, -51.805) -> into the pad, 1.2 mm between the pad edges (2.7 mm pad centre
  to pad centre along the track); the via in the pad of pin 11 stays as the feed from the In3 strip. GND: pad 1
  lies beside pin 9 on its GND via (8.25, -54.345) (ring overlaps the pad) with a 0.4 mm track, 0.2 mm between the pad
  edges (1.7 mm centre to centre). The 15V pad's north-east corner is 1.24 mm from the high-side return on x 10.25,
  the 15V track 1.25 mm (rule 1.2 mm) - the capacitor cannot go further north or east.
* **Re-routed for it**: (a) DHB_LOW_GATE leaves pin 10 on a diagonal and runs on y -53.72 between the two pads of
  C95 (pad gap 0.65 mm, track 0.2 mm for 1.6 mm, 0.225 mm to each pad; SIGNAL class 0.15 mm), then 0.3 mm
  (10.0, -53.72) - (10.6, -54.32) - R90 pad 1 - D34 pad C. (b) 5V via (9.0, -54.6) -> (9.68, -54.45) with its In2
  track; its B.Cu track runs x 9.5 -> y -55.285 south of the GND pad (0.215 mm to the pad and to C11 pad 1) and
  joins the old line y -54.98 at x 7.6. (c) R90 (10.25, -56.6) -> (10.6, -56.6), 0.35 mm east, for the 5V track on
  x 9.5 (its Q7 gate tracks still end inside pad 2).
* **Old place** (18.9, -60.6): 15V via (18.9, -58.85), In3 spur (17.125, -55.25) - (18.9, -57.025) - (18.9, -58.85)
  and GND via (18.9, -61.7) deleted; nothing else used them.

* **DC+ into Q19 pin 2** (drain; pads oval 1.905 x 2.0 at 2.54 mm pitch). Measured on a 0.1 mm raster of the fill:

  | layer | before | after |
  |---|---|---|
  | F.Cu, east (`S4B_DC+_F`) | 0.9 mm (y -50.0 ... -49.2) | 0.9 mm |
  | F.Cu, west (pour 29) | 0.9 mm (same rows) | 0.9 mm |
  | In3 | - | 1.8 mm track (0.5 oz copper) |
  | B.Cu, In2 | - | - |
  | sum | 1.8 mm | 3.6 mm (2.7 mm counted as 1 oz copper) |

  5.1 (`kicad/tube_psu.kicad_pcb`): one F.Cu entry about 2.3 mm wide (pour 29 from the north, pins in a row east-west),
  0.2 ... 0.5 mm beside the source / gate pads; nothing on the other layers.
  - **F.Cu is limited by the pads, not by the necks**: with 1.2 mm to the gate and source pads the pour can touch the
    drain pad over about 1.0 mm of its height on each side (geometry: 2 x 0.51 mm). The west way has two necks in
    parallel in front of that (1.0 mm at x 9.6 ... 10.5, y -47.8 ... -47.1, and 0.6 mm at x 7.6 ... 8.6,
    y -48.9 ... -48.3, round a hole in the fill at (8.9, -47.5)), together wider than the entry - not changed.
  - **B.Cu is not possible** with moves <= 2 mm: the pad is enclosed on B.Cu by the high-side group - east by
    gate track y -47.2 / R22 (15.5, -48.6) / source track x 15.5, y -52.06, west by the driver loop (R26 pad 2,
    C92 pad 1, return on x 10.25). The gate-source resistor has to cross the DC+ line on one side of the column,
    and the group may not use an inner layer. It would need R22 on the west side (between R26 pad 2 and C92 pad 1,
    5 mm away) - not done.
  - **In3** (group `dc`): 1.8 mm track (12.75, -49.52) - (18.7, -49.52) from the pin east to the three existing DC+
    vias (17.7 / 18.7, -50.0) 0.8 / 0.4 and (18.3, -48.5) 0.6 / 0.3 (F.Cu pour `S4B_DC+_F`, B.Cu run to C70 / C47).
    In3 east of the column was empty there; 0.69 mm to the outlines of the gate / source pads (1.09 mm to their
    holes; inner-layer HV spacing 0.5 mm), 0.68 mm to the 15V bridge on y -51.6. The In3 15V strip (x 9.5 ... 13.5) passes the pad on its west side and
    is 1.7 mm wide there (was 2.0; the DC+ pad has a ring on In3 now). First DC+ copper on an inner layer of this
    board: 400 V to the In4 GND plane through the In3 / In4 dielectric (stackup section) - not assessed further.
    In2 is closed east of the pin by `Net-(C63-Pad1)` on x 14.65.

## Inner layers (routing stage 2, 2026-11-20)

Made by `tools/p2k/bin/kipy tools/next/route_s2_planes.py` on the real board (re-runnable: everything it makes is
named `S2_*` and is removed and rebuilt; it stops if KiCad's lock file `~tube_psu_5_2.kicad_pcb.lck` exists; the
zones are refilled by kicad-cli with the project rules, 2.2 GB). Pictures: `python3 tools/next/render_inner_layers.py`
→ `routing/In1_GND.png`, `In2_Signal_HV.png`, `In3_Power.png`, `In4_GND.png`, `routing/inner_domains.png` (all
copper by isolation domain). Output of the two runs that changed 5.1 copper: `routing/route_s2_planes_first_run.log` (3bdf54c) and
`routing/route_s2_planes_second_run.log` (user decisions of 2026-11-20); every deleted zone / segment is listed in
`routing/deleted_s2.json` (net, layer, end points, reason) for the re-routing in stage 3.

### Per layer

| Layer | Content | Filled |
|---|---|---|
| In1.GND (L2) | **GND** plane: heater-LLC primary / DRV3 / U1 / DRV5 / DAB primary bridge (x −27 … 44, y < −34, round the UART island keep-out), arm to ISO1's primary side (x −40 … −27), PFC switches / bulk caps / control / flyback primary (x 2 … 64, y > −34). **ISO_GND** plane: right of the TR3 band (x > 54.5) and right of the ISO2 / TR1 slots. **HT_GND** plane: heater island incl. the AD1 / ISO1 heater side. Kept 5.1 pours (higher priority, outside the plane regions): the mains pours IN2, RES_IN | GND 5653, ISO_GND 2244, HT_GND 918 mm² |
| In2.Signal_HV (L3) | **no pour**: signal layer. Holds the 5.1 signal routing that the trial board had on In4 (399 segments, 1.66 m, 44 nets – the J2 bus to the gate drivers / isolators), moved here so that L5 is a plane. Free for the rest, incl. TX / RX from J2 pins 24 / 26 to U11 (primary copper, ≥ 8.0 mm from the island: the UART keep-out only stops pours, check_domains.py checks the tracks) | – |
| In3.Power (L4) | primary: **15V** (flyback output D5 / C39 / C1 → link round the Q21 spacing → spine y −39 … −33.6 → DRV1, DRV5 pin 16, D19 / C96, DRV3 pin 11 / C18 / C52), **5V** (flyback output C6 / C36 / C71 / D6 → J2 pin 2, V4, C75), **+3V3** (control / measurement area round J2, x 15 … 42). Secondary: **15V_ISO_SEC** (flyback output / P15V_OUT → lane x 72.4 … 76.5 → DRV6 supply), **5V_ISOL** (output block at P5V_OUT). Heater: **6V3** over the island (parallel to the B.Cu pour) | 15V 658, 5V 239, +3V3 980, 15V_ISO_SEC 572, 5V_ISOL 191, 6V3 686 mm² |
| In4.GND (L5) | **GND**, **ISO_GND**, **HT_GND** planes with the same outlines as In1. Kept 5.1 pour: IN2 | GND 5653, ISO_GND 2244, HT_GND 918 mm² |

Not done, with the reason:
- **No GND plane left of x 2 / below y −34 and none over the mains input** (IN1 / IN2, RL1, CM1, CM4, X / Y capacitors,
  L1 / L2): a plane of the bridge's negative output under the nets in front of the common-mode chokes is a
  capacitive bypass of the input filter (≈ 0.36 pF/mm² through the 0.1 mm prepreg). The 5.1 planes stopped there too.
- **No DC+ pour on In3**: the DC-link loops are closed by the F.Cu DC+ pour over the In1 GND plane (0.0994 mm);
  DC+ on In3 would put 400 V 0.11 mm above the signal layer In2 without a shield between.
- **No ISO_UART_GND plane**: four ground pads on a 20 × 26 mm island that is a pour keep-out on all layers.
- **+1V65_BIAS, −15V_SEC, 420V, −100 V**: no In3 pour (few pins, or F.Cu pours exist); tracks in the next stages.
- The pours reach through-hole pins and vias only: SMD supply / ground pads get their vias in routing stage 3.

Zone settings: priority 0 (below every kept 5.1 pour, 26 … 84), clearance 0.2 mm (net-class clearances of the
`.kicad_pro` apply where larger: 0.5 mm to HV nets), minimum width 0.2 mm, islands always removed, pad connection
"thermal relief for through-hole pads" (hand-soldered THT power pins; vias are connected solid by KiCad): gap
0.3 mm, spokes 0.6 mm (HT_GND / 6V3: 0.8 mm).

### Barrier gaps

The planes are split on all four inner layers along the same lines as the outer layers:

| Barrier | Line (centre) | Gap without planes |
|---|---|---|
| primary ↔ DAB secondary | TR3 band centre x 48.5 (top edge … y −62.5) → L-slot x 51.4 / y −39.8 → ISO2 slot x 66.75 → TR1 slot x 63.55 → bottom edge | ≥ 11.2 mm (line ± 5.6); wider wherever copper of the other domain is closer to the line, e.g. GND ends 11.25 mm left of the Q21 / Q8 / ISO2 pins 9–16 / TR1 pins 7–10, ISO_GND 11.25 mm right of Q19 / ISO2 pins 1–8 / C98 / TR1 pins 1–5 and the fly leads |
| primary ↔ heater | y −46 below the island → ISO1 slot x −42.36 → T bar y −63.6 → between the TR2 pin rows x −30.05 → top edge | ≥ 8.1 mm (line ± 4.05), wider at the pins as above |
| primary ↔ UART island | the existing all-layer pour keep-out (island + 8 mm) | no plane inside |

plus the existing all-layer pour keep-outs of the placement (TR3 band x 42.5 … 54.5, ISO2 / TR1 slot gaps, heater,
PE, mounting holes) and two new inner-layer keep-outs: `S2_KO_PWM2_drain` (no inner copper under the FLY_C drain
area x 40 … 48.3 / y −2.6 … 14.6 and the strip to D7 / TR1 pin 12 – NEXT_REVISION_PLAN phase 5 (8)) and
`S2_KO_TR1_pin2` (r 2.2 mm: nothing connects to TR1 pin 2 on an inner layer, so its inner ring is gone and the
accepted 11.01 mm pin 2 / pin 9 pair no longer shows up).

A plane cannot get its domain by accident: each one is drawn inside a hand-written region (`PLANES`) on its own side
of the barrier lines (`BARRIERS`), and the script aborts if a region contains any copper of another domain.

### Layer to layer (distance through insulation)

Rule used: **plan-view spacing between copper of two domains on two different layers = the inner-layer spacing of
the pair** (11.1 / 8.0 / 8.4 / 5.2 / 3.2 / 4.2 mm), no slot credit, whatever the two layers are. How it is met:
the outline of every `S2_*` zone is its region minus all copper of every other domain on **all six layers** (pads,
tracks, vias, stored zone fills, mounting holes) grown by that spacing + 0.15 mm – so the same outline is legal on
its own layer (KiCad's inner-layer rules) and against every other layer (which KiCad does not check). The kept 5.1
inner pours (IN2, RES_IN) get the same treatment through per-layer keep-outs `S2_KO_xlayer_*` (slivers at the PE
pads). Run the script again after routing near a barrier: the planes
follow the copper.

Check: `check_domains.py` has a second pass "layer to layer" (in `check_next.sh`): every two copper items of two
domains on two different layers; inner layer involved → inner-layer spacing in plan view, F.Cu ↔ B.Cu → as two
items on one outer layer (clearance, creepage round slots); pairs that also meet on a common layer (through-hole
pads, vias) are judged there, and the two pad rows of one barrier part by `check_footprints.py`. Before this
stage the board had 270 such pairs below the limit, now 0, and `ALLOW` holds only the Q19 / Q21 slot rule.

### 5.1 inner copper

- **Removed:** the 5.1 ground pours on In1 / In4 (GND ×3 on In1 and ×3 on In4, ISO_GND ×1 + ×1, HT_GND ×1 + ×1; 6695 mm²
  filled) and their 131 thermal-spoke segments – replaced by the `S2_*` planes (16 793 mm², one GND plane per layer
  instead of three pieces).
- **Moved:** 399 signal segments In4 → In2 (above).
- **Deleted:** 36 inner-layer segments at the barriers that were closer in plan view than the inner-layer spacing
  to copper of another domain on another layer (10 Q14_DRAIN spokes at TR2 pad 10 / WP4, and the ISO2 fan-out on
  both sides: EPWM2A / EPWM2B, CUK_CLK / CUK_SDATA, +3V3, AD2 SPI, ISO_SEC_DHB_HI, AD2_3V3, 5V_ISOL, ISO_GND) – these
  pins are fanned out on the outer layers, where the slots count.
- **Removed (decision 6):** the 5.1 switching-node pours on the ground-plane layers – PFC_DRAIN_1, PFC_DRAIN_2,
  L2_PRI2, Q13_DRAIN, Q14_DRAIN on In1 (707 mm² filled) and L2_PRI2, Q13_DRAIN, Q14_DRAIN, DHB_HI_SOURCE_SEC on In4
  (647 mm²) – with their 98 spoke segments. The planes took the freed area inside their regions: GND In1
  5496 → 5653 mm² (under the PFC drains), HT_GND 683 → 918 mm² on both layers, ISO_GND In4 2035 → 2244 mm²
  (L2_PRI2 lies outside the GND region, nothing replaces it).
- **Kept:** the mains pours IN2 (In1, In4) and RES_IN (In1) with their spokes.
- **Outer layers (decision 2):** the five 5.1 PE segments on B.Cu under R4 / R5 / R6 are deleted (PE is routed again
  in stage 3; the "PE pour keep-out" rule areas of the placement were computed from the old PE tracks and must be
  re-made then). R102 (B.Cu, across C63) stood 7.4 mm in plan view from U11 pin 9; 0.7 mm further down is taken by
  C63, so it now stands upright right of C63 at (8.1, −64.1) with pad 2 up, re-connected by five short B.Cu segments
  (U1B− along y −65.0 to the old track at x 4.6, C63 pad 1 directly): 8.2 mm from U11 pin 9.

Numbers: unconnected 355 (stage 1) → 351 (3bdf54c) → 353 now: GND 37 → 30, HT_GND 2 → 1, 15V 17 → 16, 15V_ISO_SEC
4 → 3; + 6 for the nets of the deleted barrier segments and + 2 for the deleted PE track. The 5.1 planes already
joined the through-hole pins; the remaining ground items are SMD pads without a via yet. `check_board.py`: no parity
item, no short, no isolation-rule violation.

### Decisions (user, 2026-11-20)

1. **No smaller through-insulation spacing.** The full inner-layer spacing applies in plan view between any two
   layers, also across the 0.55 mm cores and F.Cu ↔ B.Cu.
2. **The 33 F.Cu ↔ B.Cu pairs of the first run are fixed, not accepted** (PE track, R102 – above); the two OPEN
   entries are gone from `check_domains.py` `ALLOW`, as is the TR1 pin 2 / 9 entry (nothing connects to pin 2 on an
   inner layer any more; `S2_KO_TR1_pin2` keeps it so).
3. **No inner-layer slot credit at ISO1 / TR2 pad 10** (the Q19 / Q21 rule stays the only exception).
4. **The 5.1 signal routing stays on In2.**
5. **Plane clearance at the isolators and TR1 is accepted.** GND ends 2.1 … 2.4 mm from ISO2's primary pads, 2.1 mm
   from ISO1 pin 8 and 1.0 … 1.3 mm from TR1 pins 1 / 2; ISO_GND starts 2.0 … 2.8 mm from ISO2's secondary pads and
   does not reach TR1 pin 9.
6. **No switching-node pours on the inner layers** (removed, above); the mains pours IN2 / RES_IN stay.

### To do in routing stage 3

(Stage 3a, 2026-11-20: the ground / supply vias, PE as far as it can go, the PE pour keep-outs and the power part of
the deleted copper are done – next section. Left of this list: the ISO2 signal fan-out, stage 3b.)

- Ground pins at the barriers (ISO2 pins 8 / 9, ISO1 pin 8, TR1 pins 2 / 9, C98 …): short outer-layer track to a
  via in the plane (TR1 pin 2: no inner-layer connection at the pin itself).
- Vias for the SMD ground / supply pads into the planes and In3 pours.
- Route again what `routing/deleted_s2.json` lists: the ISO2 fan-out on both sides (outer layers), PE (≥ 3.2 mm in
  plan view from primary copper on both outer layers, then re-make the PE pour keep-outs), and the connections the
  removed switching-node pours made on In1 / In4 (they remain joined on F.Cu / B.Cu where the 5.1 outer pours exist).

## Power, HV and ground routing (routing stage 3a, 2026-11-20)

```
python3 tools/next/route_s3a_power.py            # tracks / vias / zones S3A_* of stage 3a (removes its last run first)
tools/p2k/bin/kipy tools/next/route_s2_planes.py # the planes follow the new copper
python3 tools/next/render_s3a.py                 # routing/s3a_F_Cu.png, s3a_B_Cu.png, s3a_power_nets.png
```

`route_s3a_power.py` is a table of steps per net group; `s3_router.py` applies it to a copy of the board (kipy),
refills with kicad-cli (2.2 GB) and writes the board back (stops on KiCad's lock file). Step kinds: drawn copper
(`track`, `via`, `zone`), `auto` (a 0.1 mm grid router between a pad / point and a pad, the rest of the net, or a via
into the plane / pour of the net) and `delete` / `delzone` for 5.1 leftovers (logged in `routing/deleted_s3a.json`).
The router blocks, by construction: the net-class clearances, the HV functional 1.2 mm on the outer layers, the
largest spacing of a domain pair in plan view against the other domain's copper on **all** layers (no slot credit,
`S2_*` planes left out because `route_s2_planes.py` re-cuts them), 0.5 mm to the edge / slots, the TR3 barrier band
(rule area "no tracks / vias"). Connections at a barrier part that need the slot credit carry `foreign_gap=4.0`
(clearance only) and are judged by `check_domains.py`. Everything added is listed in `routing/s3a_added.json`
(330 segments, 86 vias) and is removed and rebuilt on the next run; signals are stage 3b.

### Current and width

Rule of thumb used (IPC-2221 curve fitted, in the range IPC-2152 gives for a board with planes; ΔT ≈ 20 K):
1 oz outer **I ≈ 3.25 · w^0.725 A**, 0.5 oz inner **I ≈ 0.98 · w^0.725 A** (w in mm); via 0.8 / 0.4 mm ≈ 1 A,
0.6 / 0.3 mm ≈ 0.7 A.

| width (mm) | 0.3 | 0.4 | 0.5 | 0.75 | 1.0 | 1.5 | 1.6 | 2.0 |
|---|---|---|---|---|---|---|---|---|
| outer 1 oz (A) | 1.4 | 1.7 | 2.0 | 2.6 | 3.3 | 4.4 | 4.6 | 5.4 |
| inner 0.5 oz (A) | 0.4 | 0.5 | 0.6 | 0.8 | 1.0 | 1.3 | 1.4 | 1.6 |

| Path | Current | Copper of stage 3a | Good for |
|---|---|---|---|
| DAB primary, DC+ → C47 (one split-capacitor half; `DAB_SIMULATION.md`: I1 2.4 A rms, half per capacitor) | 1.2 A rms | F.Cu track Q19 pin 2 → y −47.3 → x 41.5 (west of the TR3 band) → y −75.21 → west between the pin places 3 / 4 → C47.1 (2026-11-21, 55 mm; was along the top edge, 69 mm): 1.5 mm, 0.75 / 0.8 mm for the 9 mm at the TO-220 pins (pin pitch, switch-node strip) | 4.4 A (2.6 A at the pins) |
| DAB primary switch node Q7.2 / Q19.3 → TR3 pins 7 / 8 | 2.4 A rms | zone `S3A_DHB_HI_SOURCE_F` (≥ 2.1 mm strip above the TO row + 11 × 12.7 mm at the pins) and the kept 5.1 track 1.5 mm | > 5 A |
| DAB primary low side Q7.3 / C67 → C54.2, midpoint C47.2 / C54.1 / TR3 pins 4 / 5 (2026-11-21, was 1 / 2) | 1.2 A / 2.4 A rms | zones `S3A_DHB_CURRENT_F` (5.4 mm wide, 1.7 mm neck to the 5.1 pour at C67; 14.5 mm long from C54.2, was 29 mm), `S3A_DHB_CAP_F` | > 4.7 A |
| DAB secondary switch node Q21.3 → TR3 pins 11 / 12 (2026-11-21, was 15 / 16, then 13 / 14) | 2.3 A rms | F.Cu track 1.6 mm, east of the TR3 band, 30.9 mm to pin 11 (was 37.5 mm to pin 13, 46 mm to pin 15) | 4.6 A |
| DAB secondary midpoint TR3 pins 9 / 10 / C16.2 / C55.1; 420V → C16.1; ISO_GND ← C55.2 | 2.3 / 1.2 A rms | zone `S3A_TRANS_SEC_F`; 2026-11-21 (C16 / C55 swapped): zone `S3A_420V_C16_F` 5.4 mm wide from the pad into the 420V band of Q21 pin 2 (was a 1.2 mm track to the pour east of the capacitors); zone `S3A_ISO_GND_C55_F` into the 5.1 ISO_GND pour + 3 vias 0.8 / 0.4 to the planes | > 3 A (3 vias) |
| Flyback primary: DC+ feed → R116 / R151 / C12 / R45 → TR1 fly lead 11; C15 → TR1 pin 11 | ≈ 0.1 A dc, ≤ 0.4 A rms, 1.2 A peak | F.Cu 0.76 mm along the bottom edge, 0.5 mm below R72 (1.3 mm to its pads, 0.5 mm to the edge), 1.0 mm at the pin; B.Cu 0.6 mm from C15 | ≥ 2 A |
| PWM2 drain (FLY_C) | same | zones `S3A_PWM2_drain_F` / `_B` + 10 vias 0.8 / 0.4 (below) | – |
| Flyback windings: TR1.3 → D6 (5 V), TR1.1 → D5 (15 V), TR1.7 → D29 (5V_ISOL), TR1.10 → D4 (15V_ISO_SEC) | 0.6 – 0.8 A rms (NR 1.11) | 0.8 / 0.6 / 0.8 / 0.5 mm | 2.0 – 2.8 A |
| Heater LLC primary: Q11 drain tab → DC+ pour, Q11.3 → switch node, Q10.3 → shunt R30 | ≈ 0.5 A rms | 2026-11-21 (Q10 / Q11 swapped): zone `S3A_Q11_tab_DC` (3.5 × 5.9 mm, tab → DC+ neck), zone `S3A_HHS_F` (Q10 tab – TR2 pins 1 / 2 – 2.5 mm column west of Q11 – Q11.3), 0.8 mm F.Cu + via 0.8 / 0.4 + 0.8 mm B.Cu | ≥ 1 A (the via) |
| Supply pins (15V, 5V, +3V3, 5V_ISOL, 15V_ISO_SEC, 6V3 at DRV4), ground pins | < 0.3 A each | 0.3 – 0.5 mm stub + via 0.8 / 0.4 (0.6 / 0.3 at fine-pitch parts) into the In3 pour / In1 + In4 plane | 0.7 – 1 A per via |
| PE (Y-capacitor currents only) | mA | B.Cu 1.0 mm (kept 5.1 pieces 2.0 mm) | 3.3 A |

Not touched: mains input / filter / bridge, PFC switch / diode / bulk loops and the DC+ distribution are the kept 5.1
pours and tracks (no power item of those nets was open besides the ones below).

### What was routed

- **Flyback primary (PWM2).** Drain copper: one F.Cu area round pins 5–8 (x 41.3 … 48.9, y −1.4 … 10.4) with the strip
  y 6.9 … 10.4 to D7 anode / TR1 pin 12, and B.Cu x 40.2 … 47.4, y −0.9 … 13.7, stitched with 7 + 3 vias; no inner copper
  (`S2_KO_PWM2_drain`). **Filled area 127.5 mm² (F) + 64.3 mm² (B) = 1.92 cm²** (target 2–3 cm², estimate 1.9). What limits
  it: HV 1.2 mm to R114 / R115 (left), R45 / D7 cathode (below), PWM2 pins 4 / 9 and the U10 / R132 pads (B, top); the
  B.Cu area is in two pieces (30.9 + 33.4 mm²) because VCC (D10 cathode → C58 / C51 → pin 11) and the start-up / gate net
  (R114 → pin 10) have to cross it – one 3.2 mm corridor on B.Cu at y 6.0 / 7.0 (the gate track passes between the pads
  of C58); their vias and the GND via of pin 12 sit under the package between the pin rows. The 5.1 VCC track across
  the area (F.Cu, dangling) is deleted. The area proper is ≥ 14 mm from the TR1 slot; only the strip runs to the
  fly-lead pin 12 (its end 5.2 mm from the slot, as the pin). PWM2 pins 2 / 3 (VERR / FB) are ≥ 2.5 mm from it, their
  parts R140 / R141 / C138 / C139 1.2 … 1.5 mm from its upper edge (HV functional spacing, nothing closer). Clamp D7 – R72 0.6 mm; CS pin → R9 / R8 0.4 mm; sense
  resistors, C15, C58, C51, C138 – C140, R139, R141, R154 each with a via to the GND planes; TR1 pin 2 by a 0.6 mm B.Cu
  track to a via outside `S2_KO_TR1_pin2` (no inner connection at the pin).
- **Flyback secondary.** TR1.10 → D4 east of the gap between the TR1 and ISO2 slots (x 71.9: 11.1 mm round the slots to
  ISO2 pin 8 / D5), TR1.7 → D29, TR1 pin 9 → via in the ISO_GND plane, C102 – R68 (−100 V), R68 / C45 grounds.
- **DAB primary.** The 5.1 pours 22 (DHB_CAP) and 28 (switch node) stood where TR3 / L3 / the split capacitors were:
  deleted, replaced by the zones of the table. DC+ cannot leave Q19 pin 2 northwards (TR3 barrier band from y −47.8)
  and the switch node has to pass between it and the pins, so DC+ runs 1.2 mm above the switch-node strip (y −47.3,
  0.5 mm under the band), turns north at x 41.5 (0.25 mm west of the band) and reaches C47.1 round TR3 pins 1 / 2
  along the top edge (≈ 69 mm; the loop it adds carries only the transformer current – < 0.1 µH against 40 µH
  leakage; the switching loop Q19 – Q7 – C67 is unchanged). Balancing resistors R143 – R146: one via per capacitor
  terminal.
- **DAB secondary.** The 5.1 pour 26 (TRANS_SEC at the old TR3) deleted. Switch node Q21.3 → TR3 15 / 16 as a 1.6 mm
  track east of the band; TRANS_SEC zone at TR3 9 / 10; 420V to C16.1; R147 – R150 vias.
- **Heater LLC.** Q11 tab to the DC+ pour (the 5.1 pours have no pad connection – their spokes were segments, and
  the ones of moved parts are gone), Q11.3 to the switch-node pour, Q10.3 → R30, R158 → R30, HEATER_CURRENT pours
  F ↔ B.
- **Grounds.** 25 vias 0.8 / 0.4: DRV3 / DRV5 / DRV6 ground pins and their capacitors, U1 / U11 primary side, ISO1 pin 8
  (4.8 mm F.Cu track to a via ≥ 8 mm from the heater barrels), ISO1 pin 2 / C97, ISO2 pin 8 / C98 and pin 9, ISO1 pin 9
  (HT_GND), C55 / C89 / C93 / C119 / R128 (ISO_GND), the 5.1 GND pours that had lost their plane spokes. The relay
  driver's ground pads (Q9 / C35 / R32) are joined to each other only (see open points).
- **Supply rails.** 15V / 5V / +3V3 / 15V_ISO_SEC / 5V_ISOL / 6V3 pins to their In3 pour or to the kept 5.1 track of
  the net (28 vias); where the 5.1 feed is a track on In2 its end is taken to the nearest free via site on In2 (5V
  at DRV3 and DRV5, 5V_ISOL at DRV6, +3V3 at ISO2 / C98). UART island: U11 secondary side, C135, J4 pins 1 / 2 (J4 is 1×6 since stage 11: 3V3 on pin 6, ground on 1 / 3 / 5).
- **PE.** The Y capacitors are joined again on B.Cu, 1.0 mm, ≥ 3.2 mm in plan view from primary pads / tracks on both
  outer layers: C84 – C65 direct, C84 → (−56, −6.2) → (−56, −11.5) → (−53.4, −14.1) → (−43.8, −14.1) → C81 / C82, C85 → C81;
  the two PE terminal pins are joined. The placement's four "PE pour keep-out" rule areas are replaced by
  `S3A_KO_PE_1` (PE terminal, 97 mm²) and `S3A_KO_PE_2` (Y capacitors and their tracks, 589 mm²) = PE copper + 3.25 mm
  on all six layers, made from the PE copper of each run. **The PE terminal is not connected to the Y capacitors**
  (open point 1).

Checks after the last run: `check_board.py` no parity item, no short, no isolation-rule violation (clearance markers
140 → 143: three at the ends of kept 5.1 tracks that are 0.13 … 0.18 mm from a neighbour where the new segment
starts; dangling tracks 145 → 124, dangling vias 22 → 20); `check_domains.py` same-layer and layer-to-layer clean,
`ALLOW` unchanged (Q19 / Q21). Planes after the re-cut: GND 5619 mm², ISO_GND 2227 mm², HT_GND 914 mm² per layer
(5653 / 2244 / 918 before). **Unconnected 353 → 204; in the power / HV / ground nets 189 → 40.**

### Open points (decisions) and what is left in the power / HV / ground nets (state of 5ebfa00)

Points 1, 2, 4 (neck), 5 and 6 are closed by stage 3a.2 below; 3 and the via of R155 are still open.

1. **PE terminal ↔ Y capacitors cannot be routed.** The discharge chain RES_IN – R6 – R5 – R4 – IN2 (F.Cu, 1206, pad
   gaps 1.7 … 1.9 mm) lies between the PE terminal and everything else, with the RES_IN and IN2 pours on both sides:
   PE needs 3.2 + w + 3.2 mm between two primary pads in plan view on every layer, and a chain node is copper on
   both sides of every gap. (5.1 crossed under the resistors; decision 2 of stage 2 forbids that.) Choices: one of
   R4 – R6 as a part with ≥ 7.4 mm between its pads (axial through-hole, PE crosses under its body); the PE terminal
   east of the chain; or the Y capacitors earthed through a mounting hole. 1 item open (PE.1 ↔ track at (−56, −6.2)).
2. **Mains neutral: CM1 pin 3 is cut off from the IN2 pour** (was so before this stage). The PE pads of C84 (−50.9, −1.1)
   and C65 (−42.4, −1.2) stand 8.5 mm apart between CM1 pin 3 and the pour: 2 × (1.0 + 3.2) mm closes the gap to
   0.1 mm on every layer. Needs C84 or C65 moved by ≥ 3 mm (or the neutral taken round the east side of C65),
   together with point 1. 1 item (IN2 pour in two pieces).
3. **DAB secondary: Q8 pin 2 is not joined to the switch node** (Q21.3 / TR3 15 / 16). 5.1 did that with the In4 pour
   removed by decision 6. On the outer layers the 420V pour (F) and Q8's gate parts R87 / R88 / D32 / D34 / C43
   (B) lie between the pin and everything else; the slot is 1.5 mm below the pins. Choices: a ≥ 3 mm track on In2
   (14 mm long, ≈ 15 pF to the planes; In2 is the HV routing layer of the stackup, but it is a switching node on
   an inner layer), or moving the gate parts > 2 mm and taking the 420V band to B.Cu. 1 item (R56.2 ↔ Q8.2).
4. **Heater LLC split capacitors have no DC+** (was so before this stage): the DC+ pour island at C42.1 / C49.1 / C20.1
   is 1.3 mm from the main pour; C134 (U11 decoupling) stands in the neck between the Q10 tab and U11 – with 1.2 mm
   on both sides 0 mm is left, and there is no via site (R155 – R158 under the capacitors). Needs C134 moved ≈ 2.5 mm
   (e.g. to the bottom side); then the neck is 1.9 mm. Same spot: R155 pin 1 (DC+) has no legal via site next to
   C42.1 (via in pad, or R155 1.5 mm down). 2 items.
5. **Relay driver under RL1 (Q9 / C35 / R32): 5V and GND cannot reach it** (as GPIO_BYPASS_RLY, stage 3b): the strip
   between 8 mm from the heater island and the PE keep-out of C82 is 0 … 1.7 mm high and the PE tracks close every
   other way on all layers. Depends on points 1 / 2. 2 items.
6. Small: the PWM2 drain area is 1.92 cm², at the lower end – 0.1 cm² more on B.Cu if `S2_KO_PWM2_drain` and the
   area go 0.9 mm further left (to 1.2 mm from the 15V track at x 37.8).

Left for stage 3b in these nets (gate-drive loops, sense dividers, analog supplies, 5.1 fragments on In2), 33
items: bootstrap / driver returns HEATER_HI_SOURCE (4), DHB_HI_SOURCE (2), DHB_HI_SOURCE_SEC (2) and D11 anode (15V);
dividers 420V – R23, AC1 / AC2 – R47 / R50; In2 Kelvin tracks DHB_CURRENT (2) / HEATER_CURRENT (3); +3V3 of U1
(C125, C87, two In2 pieces) and of U11 (with TX / RX on In2); AD2_3V3 and 5V at their In2 ends, DRV6 pin 3 (5V_ISOL),
C103.2 and four 0.15 mm ISO_GND fragments at DRV6, the 15V_ISO_SEC stub at ISO2, one GND via next to an In2 end,
two 5V fragments at DRV3.

### Stage 3a.2 (2026-11-20): placement fixes for the open points (user decisions)

Same scripts: the moves are `("move", ref, x, y, {rot, side}, why)` steps of `route_s3a_power.py`, logged in
`routing/moves_s3a.json`; `S2_KO_PWM2_drain` changed in `route_s2_planes.py`.

| Part | From | To | Why |
|---|---|---|---|
| PE (earth terminal, 2 pins) | (−68.7, −3.8), F | (−46.6, 0.5), F, same rotation – pins at (−46.6, −2.0) / (−46.6, 3.0) | east of the discharge chain R4 – R6: between the PE pads of C84 and C65 (the area right of the chain is under C86). ≥ 3.3 mm to the C84.1 / C65.1 pads, 0.1 … 0.2 mm between its courtyard and those of C84 / C65 / CM1 |
| C134 (U11 decoupling) | (−7.3, −81.0), F | (−5.2, −81.2), **B**, same rotation (2.1 mm + side) | out of the DC+ neck between the Q10 tab and U11 |

The PE terminal spot is confirmed by the user (2026-11-20): the earth wire has a connector on both ends and can be
extended.

**C84 / C65 were not moved:** with the terminal between them PE no longer runs west of CM1 pin 3 (the 5.1 PE track
(−50.9, −1.1) → (−56, −6.2) → (−56, −11.5) → (−53.4, −14.1) and its stub to the old terminal are deleted), so the
neutral passes west of C84 instead of between the two PE pads.

- **PE:** B.Cu 1.0 mm C84.2 – terminal – C65.2, the two terminal pins, C65.2 → x −44.2 (3.8 mm from CM1 pin 4) →
  (−43.8, −14.1) → C81 / C82, C85 → C81. One keep-out `S3A_KO_PE_1` (485 mm², PE copper + 3.25 mm, all layers) replaces
  the two of 5ebfa00. Two dangling ends of the 5.1 IN2 track CM1.3 – C84.1 (inside the PE spacing) are deleted.
- **Mains neutral:** zone `S3A_IN2_neutral` (F.Cu, 64 mm²): CM1 pin 3 → 2.5 mm bar west → 3.8 mm bar south into the
  IN2 pour at C86.2, 5.3 mm from the centre of C84's PE pad, 1.4 mm from the RES_IN pour.
- **Relay driver (Q9 / C35 / R32):** 5V and GND on **In2**, 0.15 mm, round the north end of the PE net: along
  y −41.9 / −41.55 (8.1 mm from the heater island), through the 1.3 mm gap between C85 pin 1 (0.5 mm inner-layer
  clearance) and the PE pad of C82 (3.2 mm), then between the pads of C85 (y −38.7 / −38.3) and by a via each to
  B.Cu. Both are drawn in the gap, with no via and nothing on B.Cu there: **GPIO_BYPASS_RLY has B.Cu through the gap**
  (HV functional 1.2 mm to C85 pin 1 leaves 0.58 mm; a 0.15 mm test route from the In2 end to R44.2 succeeds with the
  router's margins – not kept, stage 3b). The last 7.5 mm of the 5.1 GPIO_BYPASS_RLY track on In2 lay in these lanes
  and are deleted (`deleted_s3a.json`).
- **Heater LLC DC+:** zone `S3A_DC_neck_Q10_U11` (F.Cu, 1.15 × 9 mm ≈ 2.9 A) joins the DC+ pour to the island at
  C42.1 / C49.1 / C20.1. U11's primary-side vias (GND pins 1 / 7, +3V3 pin 3; 0.6 / 0.3) stand 0.2 mm left of the pads so
  that the neck keeps 1.2 mm to them; C134 is fed from the pin 1 / pin 3 vias on B.Cu.
- **PWM2 drain:** B.Cu area and `S2_KO_PWM2_drain` 0.9 mm further left below the VCC / gate corridor (x 39.3 / 39.1,
  y > 8.3 / 7.4; above it the U10 / R132 pads and the VCC via set the edge). **127.5 + 69.1 mm² = 1.97 cm².**

Checks: `check_board.py`, `check_domains.py` (ALLOW: Q19 / Q21), `check_next.sh` pass; courtyard overlaps unchanged
(131); 357 segments / 91 vias from the script. **Unconnected 204 → 199, in the power / HV / ground nets 40 → 35**
(353 / 189 before stage 3a). Planes: GND 5611, ISO_GND 2227, HT_GND 913 mm² per layer.

Still open after 3a.2 (both done in stage 3a.3 below):
- **Point 3 (Q8 pin 2 ↔ switch node) – not done, it cascades.** Moving only Q8's gate parts does not open a path:
  Q21 pin 2 (420V) is enclosed by the link (Q21.3 – link – Q8.2) and the slot, so either 420V or the link has to
  change layer at Q21, where B.Cu is full of Q21's gate parts (R56 above pin 2, R57 / R58 / D31) and inner copper is
  ruled out (switch node; 11.1 mm to Q19). The smallest fix found: R88 / R87 2.5 mm east (x 72.3 / 74.1), **D32 ≈ 6 mm**
  to (72.9, −48) where it is 0.03 mm short of the courtyards of C119 / R149, the dangling 5.1 15V_ISO_SEC stub at
  x 63.5 deleted; then B.Cu 1.0 mm Q8.2 → y −46.5 → x 63.2 → via at (63.2, −49.6) → F.Cu 1.2 mm along y −49.6 above
  the 420V band (which loses 1.4 of 5.6 mm) to the switch-node track at x 55.45. Needs the decision (D32 > 3 mm,
  three gate parts and their 5.1 tracks, 420V band narrowed).
- **R155 pin 1 (DC+ end of the heater balancing chain):** no legal via site – its pad lies under C42.1 / C20.1 and
  every free DC+ spot on F.Cu is within 1.2 mm of R157 / R158 pads on B.Cu. Needs R155 – R158 re-placed (4 parts).
- Stage 3b, 33 items as listed above (the +3V3 feed of U11 now ends at the via of pin 3).

### Stage 3a.3 (2026-11-20): Q8 pin 2 and the heater balancing chain (user decisions)

| Part (all B.Cu, rotation kept unless noted) | From | To | Why |
|---|---|---|---|
| R88 | (69.73, −44.93) | (72.23, −44.93) | Q8's gate parts make room on B.Cu for the switch-node link |
| R87 | (71.51, −44.93) | (74.01, −44.93) | same |
| D32 | (66.78, −46.31), 0° | (72.85, −48.02), 180° (anode over R88) | same; 0.03 mm clear of the C119 and R149 courtyards |
| R155 | (−11.14, −86.38) | (−8.0, −86.38) | balancing chain: its DC+ pad over the free DC+ copper right of C20 |
| R157 | (−8.0, −86.38) | (−11.14, −86.38) | swaps with R155 |
| R156 | (−14.7, −87.88) | (−9.57, −89.9) | lies above R155 / R157 (pads 0.5 mm from the board edge) |
| R158 | (−8.0, −81.61) | (−13.3, −81.61) | left of the shunt R30, on the HEATER_CURRENT copper |

**Stage 3b step 0 (2026-11-20, user: no HV at the board edge):** the chain moved 1.5 mm inward – final places R155
(−8.0, −84.88), R157 (−11.14, −84.88), R156 (−9.57, −88.4; pads 2.0 mm from the top edge, reference text back on the
board), R158 (−13.5, −81.61); vias DC+ (−8.4, −82.0), CAP_MEAS (−12.7, −88.4), HEATER_CURRENT (−15.8, −81.6). The table
above and the list below give the 3a.3 places; `routing/moves_s3a.json` holds the first and the final place.

- **Q8 pin 2 → switch node:** B.Cu 0.75 mm at the pins, 1.0 mm north to y −46.5 and west above C43 to x 62.8, via
  1.0 / 0.5 at (62.8, −49.2), F.Cu 1.2 mm along y −49.6 above the 420V band to the Q21 – TR3 track (x 55.45); no inner
  copper. Good for 3.3 A (2.3 A rms). Deleted: the nine 5.1 gate segments at the old places of R87 / R88 / D32 and
  the dangling 15V_ISO_SEC stub above C43. C43 is now fed by a via at its pad and a 0.5 mm track on In3 into the
  In3 pour (the F.Cu track of 5ebfa00 through the 420V band is gone).
- **420V band (F.Cu, Q21 pin 2 → east):** 3.4 … 3.6 mm between the link and the gate pad of Q21 (x 60 … 64), 5.1 mm
  east of x 65; one 2.1 mm neck (1.5 mm long) at the supply via of C43. Smallest width 2.1 mm ≈ 5.6 A against
  ≈ 1.6 A rms.
- **Heater balancing chain:** DC+ – R155 (via 0.6 / 0.3 at (−8.4, −82.8) in the DC+ island) – R156 – HEATER_CAP_MEAS (via at
  (−12.6, −89.6) into the F.Cu pour) – R157 – R158 – HEATER_CURRENT (R158.2 on the B.Cu copper of the shunt R30, via
  0.8 / 0.4 at (−15.6, −81.6) to the F.Cu pour). All B.Cu, 0.4 mm, ≥ 1.2 mm between the chain nodes and to other nets.
- Checks: `check_board.py`, `check_domains.py` (ALLOW: Q19 / Q21), `check_next.sh` pass; courtyard overlaps
  unchanged (131); one more silk-to-edge marker (R156 at the top edge, 15 → 16). 370 segments / 93 vias from the
  script. **Unconnected 199 → 196, in the power / HV / ground nets 35 → 33.**

Left for stage 3b from this step (signals): Q8's gate loop – Net-(Q8-G) (Q8.1 – R88.2 – R87.2), Net-(D32-PadA)
(D32.A – R88.1), DHB_LOW_GATE_SEC (DRV6.10 – R87.1 – D32.C). The 33 items left in the power / HV / ground nets are
the stage-3b list above (bootstrap / driver returns, dividers, In2 Kelvin tracks, U1 / U11 +3V3, small fragments).

## Signal routing (routing stage 3b, first pass, 2026-11-20) – not finished

```
python3 tools/next/route_s3b_signals.py --strip   # full rebuild: take this stage's copper off first,
python3 tools/next/route_s3e_j2.py --strip        # (stage 3e, since 2026-11-20)
python3 tools/next/route_s3d_iso2.py --strip      # (and that of stages 3d / 3c, since 2026-11-20)
python3 tools/next/route_s3c_cleanup.py --strip
python3 tools/next/route_s3a_power.py             # so that the stage-3a router does not see it
python3 tools/next/route_s3c_cleanup.py           # stage 3c, section below
python3 tools/next/route_s3d_iso2.py              # stage 3d: ISO2 / AD2 fan-out (drawn), section below
python3 tools/next/route_s3e_j2.py                # stage 3e: J2 escapes and the J2 nets (drawn), section below
python3 tools/next/route_s3b_signals.py
tools/p2k/bin/kipy tools/next/route_s2_planes.py
```

`route_s3b_signals.py`: one connection per row of `TABLE` (group, net, start, end, layers, width, options), generated
from the unconnected list after stage 3a (842d301) and edited from there; routed in table order by the grid router
of `s3_router.py` on F.Cu / B.Cu / In2 (switch nodes: outer layers only), via 0.6 / 0.3, width 0.2 mm (gate-drive
nets 0.4, supply / HV 0.3). New engine switches used here: `RELAX_OWN_DOMAIN` (the pin-pitch relaxation of a part
never applies to copper of another isolation domain), `HARD_ZONES` (pours of HV nets and the `S3A_*` zones are
neither crossed nor pushed back by a signal track), an `avoid` box that keeps ISO2's primary-side tracks out of the
gap between the TR1 and ISO2 slots. Copper of the run: `routing/s3b_added.json` (438 segments – 247 B.Cu, 102 F.Cu,
89 In2 – and 52 vias).

| group | rows | routed |
|---|---|---|
| supply, ground and switch-node leftovers | 32 | 20 |
| gate drives | 80 | 56 |
| current sense and analog | 46 | 35 |
| SPI and control | 32 | 16 |
| UART | 6 | 5 |
| ground repairs (pads cut off by the tracks above) | 2 | 2 |

**Unconnected 196 → 65.** `check_board.py`, `check_domains.py` (ALLOW: Q19 / Q21), `check_next.sh` pass; courtyard
overlaps 131 (unchanged), no short, no hole or rule-area marker. Clearance markers 142 → 170, dangling tracks
120 → 89, dangling vias 20 → 13. Planes In1 / In4: GND 5607 → 5578, ISO_GND 2224 → 2218, HT_GND 913 → 909 mm² (via
antipads only; no track on In1 / In4).

**This is a legal first pass, not a reviewed layout:** the router joins each open pair by the cheapest legal path.
It does not pair Kelvin tracks, does not keep a gate track beside its return, and does not look at what runs
under an analog track. Not done: the 64 rows that found no legal path (`report` in `s3b_added.json`), the
clean-up of 5.1 dangling copper (many open rows start on those stubs), Q8's gate loop review.

**Stage 3b.2, item 1 (2026-11-20, user decision):** `.kicad_dru` rules "High-side driver group DRV3 / DRV5 / DRV6,
outer layers": 0.2 mm between two nets of the same floating high-side driver (DRV3: HEATER_HI_GATE / _SOURCE / _DRV,
Net-(DRV3-VDDA), Net-(D35-K), Net-(D11-K); DRV5: DHB_HI_GATE / _SOURCE, Net-(DRV5-VDDB), Net-(D19-K), Net-(D30-PadA),
Net-(Q19-G); DRV6: DHB_HI_GATE_SEC / _SOURCE_SEC, Net-(DRV6-VDDA), Net-(D18-K), Net-(D31-PadA), Net-(Q21-G)); nothing
else changes. `check_rules.py` proves it with four pairs (inside a group 0.3 mm passes; towards DC+, another group
and the low side 1.0 mm still fails; 26 tests, 31 since stage 3c). The router has the same lists (`s3_router.HS_GROUPS`); stage 3b
re-run with them: 137 of 196 rows + 2, **unconnected 62**, clearance markers 170 → 136 (142 before stage 3b; 94
HV functional, 4 inside a driver group below 0.2 mm), dangling tracks 86, vias 13, planes GND 5581 / ISO_GND 2218 /
HT_GND 909 mm². The numbers of the first pass above are those of 89608a5. Still to do from the user's list of
2026-11-20: gate loops drawn by hand (incl. Q8 and the low sides), J2 escape stubs, ISO2 fan-out, Kelvin pairs,
analog review, TX / GPIO_BYPASS_RLY, dangling clean-up, render review.

Open points (of 89608a5; 1 is decided as above):
1. **HV functional rule inside one gate-drive domain.** The + 28 clearance markers are almost all "HV functional
   1.2 mm" between nets of the same floating high-side driver (gate / source / bootstrap supply, ≤ 20 V apart) at
   1.27 mm pin pitch; most of the 142 older ones are the same. A tight gate loop and this rule exclude each other.
   Recommendation: a `.kicad_dru` exception per driver group (DRV3: HEATER_HI_*, Net-(DRV3-VDDA), Net-(D35-K);
   DRV5: DHB_HI_GATE / DHB_HI_SOURCE / Net-(DRV5-VDDB) …; DRV6 likewise) with 0.2 mm, then route the gate loops
   by hand-drawn steps next to their returns.
2. **J2 (1.27 mm header) escapes** need drawn stubs on a 0.025 mm grid (a 0.15 mm track only fits centred between
   two pads); the 0.1 mm grid router fails there (J2.38 / 42 / 43 and the SPI rows).
3. **ISO2 fan-out** (EPWM2A / B, DAB_DIS, CUK_*, AD2 SPI, both sides) is still open: outer layers only at the slot,
   and the primary side may not use the gap between the slots.

## Clean-up of the kept 5.1 copper (routing stage 3c, 2026-11-20)

```
python3 tools/next/route_s3b_signals.py --strip   # full rebuild of stages 3a - 3e
python3 tools/next/route_s3e_j2.py --strip
python3 tools/next/route_s3d_iso2.py --strip
python3 tools/next/route_s3c_cleanup.py --strip
python3 tools/next/route_s3a_power.py
python3 tools/next/route_s3c_cleanup.py           # this stage: sees the copper of 3a
python3 tools/next/route_s3d_iso2.py              # stage 3d (next section): sees 3a and 3c, 3b sees all three
python3 tools/next/route_s3e_j2.py                # stage 3e
python3 tools/next/route_s3b_signals.py
tools/p2k/bin/kipy tools/next/route_s2_planes.py
python3 tools/next/check_board.py --all-track-errors   # every clearance error of a track, not only the first
```

The kept 5.1 copper was drawn for 5.1's rules (0.18 mm everywhere, thermal spokes as track segments). Stage 3c
removes the 5.1 tracks / vias that break the 5.2 HV functional spacing (1.2 mm, outer layers) and draws them
again, and it removes dangling 5.1 copper. `route_s3c_cleanup.py` is a step table like stage 3a (new step kind
`delvia`); what it deletes stays deleted (`routing/deleted_s3c.json`, 104 segments and 10 vias), what it adds
(`routing/s3c_added.json`, 39 segments and 5 vias) is rebuilt on every run. Three 5.1 items are replaced in the data
of stage 3a instead (`deleted_s3a.json`). No part was moved (`routing/moves_s3c.json` is empty).

KiCad's DRC reports only the first clearance error of each track; `check_board.py --all-track-errors` lists all
(171 instead of 136 at 40991f4). Both counts are given below.

### Rule changes (each with a test pair in `check_rules.py`, 31 tests)

1. **No-connect pads are left out of "HV functional, outer layers"** (`.kicad_dru`: not when one item is a pad
   on a net `unconnected-*`). Pins 12 / 13 of the UCC21520 (DRV3 / DRV5 / DRV6) lie between the two output
   channels and have no internal connection; a pad of them carries no voltage of its own, and the pad row itself
   is on 1.27 mm pitch (0.67 mm between pads). The net class clearance stays (0.5 mm for a HV net). Tests: DC+
   track 0.8 mm from pads on an `unconnected-` net passes, 0.8 mm from the same pads on GND fails (1.2 mm), 0.3 mm
   from the no-connect pads fails (0.5 mm). `s3_router.py` has the same exception.
2. **`Net-(R109-Pad1)` and `Net-(R111-Pad1)` are SIGNAL nets, not HV_PRIMARY** (`setup_project.py`). They are the
   return leg of the DC-link difference amplifier U6: GND – R112 – R111 – R109 – U6 pin 4 (inverting input, 15 k
   feedback R82 from the output, 0 … 3.3 V). Both ends of the 3 MΩ string are within 0 … 3.3 V, so every node of
   it is; the HV leg is DC+ – R16 – R15 – R10 – U6 pin 3 and keeps its class. Tests: `Net-(R109-Pad1)` 0.3 mm
   from GND passes, `Net-(R10-Pad1)` 1.0 mm from GND fails. Now HV_PRIMARY 43, PRIMARY_LV 5, SIGNAL 110.
3. **No exception for the nodes inside the HV dividers.** Voltages between neighbours (schematic):

   | Divider | Chain | Between adjacent nodes |
   |---|---|---|
   | DC link (U6) | DC+ 400 … 450 V – R16 – `Net-(R15-Pad1)` – R15 – `Net-(R10-Pad1)` – R10 – U6 pin 3 (≈ 1 V) | 133 … 150 V per 1 MΩ; `Net-(R10-Pad1)` is 133 … 150 V above U6's inputs and GND |
   | 420V (U3) | 420V – R23 – `Net-(R23-Pad2)` 280 V – R34 – `Net-(R34-Pad2)` 140 V – R39 – CUK_CAP_MEAS2 (≈ 1 V) | 140 V per 1 MΩ |
   | Mains (U8) | AC1 / AC2 (≤ 358 V peak to GND) – R47 / R50 – R48 / R51 – R79 / R52 – U8 inputs (1.65 V) | ≤ 120 V peak per 1 MΩ; the last node is ≤ 120 V peak from U8's inputs and the 15 V rail |
   | Balancing R143 – R150, R155 – R158 | half of DC+ / 420V per pair | 100 … 210 V |

   None of these pairs is low-voltage, so the 1.2 mm stays for all of them and the copper has to move (open
   point 1 below).

### What was done

- **TO-220 pins (Q7, Q19, Q21, Q8):** 5.1's spoke segments inside the pads deleted (10); tracks leave a pin 0.75 mm
  wide (1.21 mm to both neighbours on 2.54 mm pitch): switch node Q7 pin 2 → Q19 pin 3 on F.Cu (was 1.78 mm, 0.57 mm
  above Q7's gate pad) now 0.75 mm at the pins and 1.15 mm along y −44.75 inside the zone `S3A_DHB_HI_SOURCE_F`,
  1.22 mm from the gate pad and from the DC+ track of stage 3a; Q19 pin 3 and Q7 pin 1 on B.Cu 0.75 mm; switch node
  at Q21 pin 3 0.75 mm past the 420V pin, then 1.6 mm; R56's two tracks 0.3 mm along the upper half of its pads
  (1.3 mm above the 420V pin instead of 0.8 / 0.97 mm).
- **DAB gate tracks:** high-side gate track to DRV5 routed again (was 0.94 mm from the low-side gate track,
  1.17 mm from D34); the one at DRV6 pin 6 0.7 mm wide (1.21 mm).
- **Bulk capacitors C37 / C56 (DC+ pin, through-hole) on B.Cu:** +3V3, GND and +1V65_BIAS ran 0.36 … 1.1 mm past
  the pins. +3V3: the two B.Cu links are deleted, C62 / U6 and C76 / U4 each have a via into the In3 +3V3 pour.
  GND: 0.1 mm lower at C62. +1V65_BIAS: round the west side of C56 (through the GND pour, ≥ 1.2 mm).
- **AC-sense divider (R79, vias of R48 / R51):** the 15V track flyback → DRV2 lay between the pads of R79
  (0.16 … 0.4 mm from the divider nodes): now along the bottom edge on B.Cu (y 17.6) and a short piece on In2 (two vias 0.6 / 0.3).
- **15V via at C70 (DC+ pad 0.9 mm):** 0.8 mm further east on the same tracks.
- **DRV3:** via of the old driver footprint 0.12 mm from pin 10 deleted; the 1.27 mm bootstrap-return track ends
  0.6 mm earlier (was 0.17 mm from pin 15); stubs at R24 / R59, D11 / R99 deleted.
- **420V sense track of R23** (0.15 mm, 0.4 … 0.5 mm from the vias of AD2, dangling 6 mm before R23): deleted, not
  routed again (open point 1).
- **Dangling stubs** next to TR1 pin 5 / D8 (−100 V winding), the via of R10, and 15V_ISO_SEC 1.15 mm from R39
  (0.45 mm wide now).
- **Near-short:** the end of the kept EPWM5A track on In2 stood 0.025 mm from the HEATER_CURRENT via at
  (0.4, −56.1): 0.95 mm shorter.
- **In stage 3a's data:** the 5.1 15V via 0.11 mm from the D10 anode pad moved 0.44 mm, the 5.1 15V track beside
  DRV2 (0.13 mm from pins 2 / 3) drawn again 0.1 mm further right, the GND stub at U4 0.3 mm wide.
- **In stage 3b's data:** rows that started on deleted copper changed (DRV3 pin 14, R36, D11); the 420V row is
  gone; `relax` taken off the 15V row at D11 (it let the track pass 0.27 mm from the bootstrap node at D11's
  cathode); two rows moved up (DRV5 pin 5, U10 pin 2) so that they are routed before their neighbours close the pin.
- **Dangling 5.1 copper:** 31 segments (69 mm) and 8 vias deleted that no open connection starts on – not an
  end point of an unconnected item of the DRC and not within 0.3 mm of a start / end point of a route script.
  Kept: 65 dangling segments that are such anchors, and the escape of AD2 pin 4 (later ISO2 / AD2 fan-out).

### Numbers

| | 40991f4 (before) | after stage 3c |
|---|---|---|
| unconnected | 62 | **59** |
| clearance markers, first error per track (default) | 136 | **42** |
| – HV functional 1.2 mm | 94 | 21 |
| – inside a high-side driver group (0.2 mm) | 4 | 0 |
| – PRIMARY_LV class 0.2 mm | 30 | 20 |
| – other classes (SECONDARY_LV, HEATER, SIGNAL, footprint, HV class) | 8 | 1 |
| clearance markers, all errors (`--all-track-errors`) | 171 (HV 127, PRIMARY_LV 32, driver group 4, other 8) | **51** (HV 28, PRIMARY_LV 22, HEATER 1) |
| dangling tracks / vias | 86 / 13 | 72 / 6 |
| courtyard overlaps | 131 | 131 |
| planes In1 / In4: GND / ISO_GND / HT_GND (mm²) | 5581 / 2218 / 909 | 5582 / 2218 / 909 |
| stage 3b rows routed | 137 of 196 + 2 | 140 of 196 |

`check_board.py`, `check_domains.py` (same layer and layer to layer; ALLOW: Q19 / Q21) and `check_next.sh` pass.
Deleted in total: 104 segments (207 mm) and 10 vias in `deleted_s3c.json`, 2 segments and 1 via more in
`deleted_s3a.json`. The remaining dangling items: 65 kept anchors of open connections, the AD2 pin 4 escape, a few
ends of stage-3a / 3c copper inside a pour; the 6 vias are the ISO2-side ends of EPWM2A / B, $CUK_CS and the AD2 SPI
nets (ISO2 fan-out). A rebuild is not bit-identical: the plane vias of stage 3a land in the plane fill as it is at
that moment, which carries the antipads of the last stage-3b run - between two consecutive rebuilds two ground
vias of stage 3a and five pieces of stage 3b moved by ≤ 2 mm, all counts stayed the same.

### Left, and open points

1. **HV dividers: the remaining 27 HV markers (all errors) are inside the three sense dividers**, between a
   divider node and its neighbour node or the amplifier input, 0.38 … 1.19 mm at 120 … 150 V:
   R23 / R34 / R39 (the link R23.2 → R34.1 runs diagonally through the 0.7 mm gap between the pads of two 1206
   resistors placed side by side; R34.1 is 1.15 mm from the CUK_CAP_MEAS2 via), R10 / U6 (R10 pin 1 is 0.61 mm from
   U6 pin 4, pad to pad; its via 0.88 mm from R109 pin 2 and 1.05 mm from R16 pin 2), R79 / R49 / U8 (via of
   `Net-(R48-Pad2)` 0.79 mm from R49 pin 2). No track can fix these: the parts stand closer than 1.2 mm. And
   **R23 pin 1 has no 420V**: between the AD2 vias (x 80.3 … 80.5) and the 4.2 mm keep-off of mounting hole H5
   there is no 1.2 mm path on F.Cu, R113 on the bottom side leaves no via site at R23, and In2 has 1.25 mm between
   the AD2_3V3 via and the AD2-CS track (0.2 + 2 × 0.5 mm needed, without margin). Choices:
   (a) re-place each divider as a straight row with ≥ 1.2 mm between unlike pads (R23 / R34 / R39 ≈ 3 mm, with
   the 420V feed from the east; R10 0.5 … 1 mm from U6; R79 / R49) – part moves of 1 … 4 mm, more than this stage
   may do; (b) a graded rule for adjacent divider nodes only (IEC 60664-1 Table F.5, printed wiring, PD2: 0.4 mm
   at 160 V – to be checked against the standard), which clears the markers but not the 420V feed of R23.
   Recommendation: (a) for R23 / R34 / R39 together with the ISO2 / AD2 fan-out (the area is redrawn there
   anyway), (b) = accept as they are for R10 and R79.
2. **PRIMARY_LV class clearance 0.2 mm against 5.1's 0.18 mm:** 22 markers (all errors) are kept 5.1 tracks / vias
   0.156 … 0.19 mm from a neighbour (5V and $HT_CS on In2, +1V65_BIAS, GND vias), at ≤ 15 V. Not cheap (parallel
   runs of 5 … 15 mm on In2). JLC needs 0.09 mm. Recommendation: accept them, or set the PRIMARY_LV class clearance
   to 0.15 mm for inner layers.
3. `DHB_LOW_GATE_SEC` (stage 3b) 1.15 mm from R149 pin 2 at the pad of D32: goes with Q8's
   gate loop.
4. The heater low-side gate (Q10 pin 1) is open again: the route of the first pass was only possible with
   `relax` (0.38 mm from the switch-node pin Q10.2); DAB_DIS at DRV5 pin 5 is open too (shut in by the DT track).
   In exchange D11 anode (15V, 20 mm round D11 - a first-pass route, to be drawn with the gate loops),
   HEATER_LOW_DRV, U8's C127 and others are routed now (140 of 196 rows). Gate loops are the next stage.
5. `relax` in stage 3b rows lowers the spacing to **every** pad of the named part, also to a HV pad of another
   net. Stage 3c found and fixed the two cases that showed (D11, Q10); the next stages should name nets, not
   parts, where a part has a HV pin.

## ISO2 / AD2 fan-out, 420V divider, R10 / R79 (routing stage 3d, 2026-11-20)

```
python3 tools/next/route_s3b_signals.py --strip   # full rebuild of stages 3a - 3e
python3 tools/next/route_s3e_j2.py --strip
python3 tools/next/route_s3d_iso2.py --strip
python3 tools/next/route_s3c_cleanup.py --strip
python3 tools/next/route_s3a_power.py
python3 tools/next/route_s3c_cleanup.py
python3 tools/next/route_s3d_iso2.py              # this stage: drawn copper, before the grid router of stage 3b
python3 tools/next/route_s3e_j2.py                # stage 3e (next section)
python3 tools/next/route_s3b_signals.py
tools/p2k/bin/kipy tools/next/route_s2_planes.py
python3 tools/next/render_inner_layers.py && python3 tools/next/render_s3a.py     # PNGs in routing/
```

`route_s3d_iso2.py` is a step table like stage 3a (`--dry-run OUT.kicad_pcb`, `--strip`, any other option is
refused). All of it is drawn copper; only the two long DAB_DIS runs away from ISO2 are routed by the grid router.
5.1 copper it deletes stays deleted (`routing/deleted_s3d.json`: 59 segments, 12 vias), moves are absolute
(`routing/moves_s3d.json`), what it adds is rebuilt on every run (`routing/s3d_added.json`: 155 segments - F.Cu 128 mm,
In2 160 mm, B.Cu 25 mm - and 22 vias; two B.Cu pour keep-outs `S3D_KO_*`). The rows of these nets are gone from the
stage 3b table (196 -> 175 rows); stage 3a no longer routes ISO2 pins 8 / 9 / 16 and stage 3c no longer redraws the
15V_ISO_SEC stub; its 15V hop past R79 is drawn instead of routed (below).

### Rule change (user decision)

**PRIMARY_LV clearance 0.15 mm on the inner layers** (`.kicad_dru` rule "PRIMARY_LV inner layers 0.15 mm": a
PRIMARY_LV net against a PRIMARY_LV or SIGNAL net, tracks / vias / pads; zone fills, the outer layers (0.2 mm), HV
nets and other domains unchanged). It covers 5.1's In2 runs at 0.156 ... 0.19 mm, <= 15 V. `s3_router.World.gap` has
the same exception; `check_rules.py` proves it with three pairs (5V / GND 0.16 mm on In2 passes, on F.Cu fails,
5V / DC+ 0.3 mm on In2 still fails; 34 tests). Clearance markers 42 -> 27 (all errors 51 -> 36).
**Other classes:** one marker of the same kind is left in the HEATER class (EPWM5A_ISO track 0.162 mm from the
EPWM6A_ISO via on In2 at (-48.9, -54.2)); SECONDARY_LV and SIGNAL have none. Not changed.

### Part moves

| Part | From | To | Move | Why |
|---|---|---|---|---|
| R39 | (76.9, -24.4), 90° | (76.9, -22.3), 180° | 2.1 mm | 420V divider as a straight row, CUK_CAP_MEAS2 end west |
| R34 | (79.1, -24.4), -90° | (80.7, -22.3), 180° | 2.6 mm | row, 3.8 mm pitch (the 0805 courtyards do not overlap) |
| R23 | (81.2, -24.4), -90° | (84.5, -22.3), 180° | 3.9 mm | row; 420V end east, pad 6.8 mm from the centre of H5 |
| R10 (B.Cu) | (18.6, 4.0) | (18.7, 4.6) | 0.61 mm | pin 1 (133 ... 150 V) 1.2 mm from U6's input tracks and R109 |
| R79 (B.Cu) | (35.2, 14.7) | (34.8, 14.6) | 0.41 mm | room for the via of pin 1 on its right side |

Courtyard overlaps 131 -> 130. No other part moved.

- **420V divider:** 420V - R23 - 280 V - R34 - 140 V - R39 - CUK_CAP_MEAS2 in one line at y -22.3; unlike nodes of
  two parts are >= 1.9 mm apart pad to pad (0.6 mm between the two pads of one node), the node links are 0.2 mm tracks
  from pad centre to pad centre. **420V feed:** F.Cu 0.2 mm, 24 mm, from the 420V pour at (85.9, -43.1) south,
  between AD2's vias and the 4.2 mm keep-off of mounting hole H5 (an arc of radius 6.2 mm round the hole: 4.33 mm
  from its ring), into pin 1 from the north; >= 1.26 mm from every other net. AD2's SPI vias had to leave the strip east of
  its pins for that (below). CUK_CAP_MEAS2 (about 1 V): F.Cu west of the 140 V node, a via between the SPI lanes,
  B.Cu to the 5.1 via at U3 pin 3. CUK_CAP_MEAS- (R113 - R120): B.Cu round R120 pin 1, the In2 hop of stage 3b
  under the new place of R23 is gone.
- **R10:** via of `Net-(R10-Pad1)` at (17.7, 3.5), 1.2 mm clear of R109 pin 2, R16 pin 2, C131 pin 1 and R10 pin 2;
  the U6 "-" track enters R82 at x 20.7, the U6 "+" track leaves R10 pin 2 at its centre line.
- **R79:** the only legal via site next to pin 1 is 0.15 x 0.2 mm large (R49 pin 2 / R79 pin 2 above, the DC+
  track on F.Cu below, the 15V via of stage 3c on the right): via 0.5 / 0.3 at (35.85, 15.56) with R79 0.4 mm
  further left: 1.25 mm from the 15V via, 1.31 mm from the DC+ track, 1.32 mm from R79 pin 2. Because of the
  0.05 mm margin the 15V hop of stage 3c ((32.1, 15.5) - In2 - (36.9, 14.1)) is drawn copper now - as an `auto` row
  it moved by 0.1 mm when it was routed with R79 at its new place. See open point 2.

HV functional markers (all errors) 28 -> 1: the last one is `DHB_LOW_GATE_SEC` at D32 (Q8's gate loop).

### ISO2 fan-out

Rules used: (1) **no via closer than 11.1 mm in plan view to copper of the other domain** - a via has a ring on the
inner layers; `check_domains.py` does not ask for this (a via also stands on F.Cu, where the slot counts), the
5.1 vias at x 60.8 (9.4 mm) and 73.1 / 74.4 (9.7 ... 11.0 mm) are deleted; (2) between a pad and its via only F.Cu;
(3) nothing in the gap between the TR1 and ISO2 slots except the first 1.9 mm of pin 8's ground; (4) In2 lanes over
the GND / ISO_GND planes, no track on In1 / In4.

**Primary side (pins 2 - 8).** C98 and D5 leave a 3.2 mm corridor west of the pin row. All seven nets go through
it as one F.Cu bundle (0.2 mm, 0.35 ... 0.55 mm pitch) in pin order, pins 2 / 3 first down the 0.98 mm channel
between C98 and the pins. Vias 0.5 / 0.3 (the 5.1 In2 lanes are 0.51 mm apart):

| Pin, net | F.Cu | via | In2 |
|---|---|---|---|
| 8 GND | 6.5 mm | (57.35, -24.5) into the planes | - |
| 7 CUK_SDATA | 6.8 mm | (56.55, -24.5) | 9.5 mm new, to the 5.1 lane end at x 47.5 |
| 6 CUK_CLK | 7.0 mm | (55.8, -24.5) | 3.0 mm new, 5.1 lane end at x 53.1 |
| 5 $CUK_CS | 3.6 mm | (58.55, -25.97) | 1.7 mm new end of the 5.1 lane |
| 4 DAB_DIS | 4.1 mm | (57.85, -26.5) | new lane y -26.05 north of the CS lane, then beside the bus to J2 pin 18 (25 mm, the last 7.7 mm on F.Cu) |
| 3 EPWM2B | 9.7 mm | (54.65, -24.32) | 5.1 lane, 3.4 mm shorter |
| 2 EPWM2A | 11.1 mm | (54.2, -24.82) | 5.1 lane, 3.6 mm shorter |

The lanes arrive in the order SDATA, CLK, 2B, 2A, CS (south to north), the pins leave in the order SDATA, CLK, CS,
DIS, 2B, 2A: CS and DAB_DIS get their vias in the middle of the bundle, 2A / 2B pass north of them and cross the CS /
DAB_DIS lanes on F.Cu. The three southern vias stand in a row north of the 15V pour (its strip y -23.8 ... -23.0 is
the link D5 cathode - C39, 0.7 A). Eastmost primary via edge x 58.8 = 11.58 mm from the secondary pads. Pin 8 no
longer runs past C98 (stage 3a had it at x 60.6 across the corridor).

**Secondary side (pins 9 - 16).** The 5.1 15V_ISO_SEC track on F.Cu (x 72.5 ... 75.2, y -42.8 ... -24.7; a dead end
since stage 3c, the rail is the In3 pour) walled the pins in: deleted (10 segments).

| Pin, net | F.Cu | via | then |
|---|---|---|---|
| 10 AD2-SDATA | 3.1 mm straight east | 0.5 / 0.3 at (74.55, -23.43) | In2 17.6 mm, via (81.05, -35.3) north-east of AD2, B.Cu 3.0 mm to pin 5 |
| 11 AD2-CLK | 3.1 mm | (74.55, -24.70) | In2 15.0 mm to the 5.1 via (80.45, -34.5) at pin 4 |
| 12 AD2-CS | 3.1 mm | (74.55, -25.97) | In2 10.5 mm, via (78.8, -32.75) under AD2, B.Cu 0.9 mm to pin 6 |
| 13 DAB_DIS_SEC | 5.1 mm | 0.6 / 0.3 at (76.3, -26.75) | In2 lane x 74.5 / 75.1 north, then the grid router to DRV6 pin 5 (36 mm In2, via, 0.6 mm B.Cu) |
| 14 ISO_SEC_DHB_LO | 5.0 mm, south of C103 | (75.57, -27.4) | In2 13.2 mm (x 74.9 / 75.5) to the 5.1 lane end (75.4, -40.0) |
| 15 ISO_SEC_DHB_HI | 4.6 mm, between the pads of C103 | (75.57, -28.8) | In2 11.0 mm (x 75.3 / 75.9) to the 5.1 lane end (76.7, -39.1) |
| 16 AD2_3V3 | 5.7 mm (C103 pin 1 on the way) | (75.9, -32.0) | B.Cu 3.2 mm north to the 5.1 track of V2 pin 5 (the 5.1 In2 link across the gate lanes is deleted) |
| 9 ISO_GND | 5.4 mm, south of the divider row | 0.6 / 0.3 at (76.51, -20.36) between the pads of D4 | planes |

C103 pin 2 goes by a 2.8 mm F.Cu track to R38 pin 2 (its 5.1 via at x 73.1 was not in a plane; this was an open
connection). The SPI vias stand in the 0.15 mm window between the 11.1 mm line (x 74.23 + via radius) and the
5V_ISOL track on B.Cu (x 75.08): 11.17 mm from the primary pads, 0.28 mm from that track. The SPI lanes are 1.27 mm
apart side by side on In2 between In1 (ISO_GND) and In3 / In4, the eastmost one 6.0 mm from the centre of H5.
**AD2's vias:** only CLK keeps its place east of the pins; SDATA's is 0.8 mm further north-east and CS's under the
package, so that the strip between AD2 and H5 is free for the 420V feed (a via east of pin 5 / 6 leaves < 1.2 mm).
In2 lane order (CS, CLK, SDATA from the west) and pin order differ, so SDATA's B.Cu stub crosses the CLK lane.

**B.Cu pour keep-outs** (rule areas, rebuilt by the script): `S3D_KO_ISO2_pri_B` - the 5.1 GND pour reached x 64.0,
0.9 mm past the primary pads towards the slot, which pushed every secondary In2 track and the In3 lane to x 75.2;
`S3D_KO_ISO2_sec_B` - the island of the 5.1 ISO_GND pour under C103, which hung on the deleted via.

### Numbers

| | 95af98e (before) | rule change (b979b0c) | after stage 3d |
|---|---|---|---|
| unconnected | 59 | 59 | **43** |
| clearance markers, first error per track | 42 | 27 | **7** |
| - HV functional 1.2 mm | 21 | 21 | 1 |
| - PRIMARY_LV class | 20 | 5 | 5 (outer layers) |
| - HEATER class | 1 | 1 | 1 |
| clearance markers, all errors | 51 (HV 28, PRIMARY_LV 22, HEATER 1) | 36 (28 / 7 / 1) | **9** (1 / 7 / 1) |
| dangling tracks / vias | 72 / 6 | 72 / 6 | 59 / 0 |
| courtyard overlaps | 131 | 131 | 130 |
| planes In1 / In4: GND / ISO_GND / HT_GND (mm²) | 5582 / 2218 / 909 | same | 5577 / 2225 / 909 |
| In3 pours: 15V / 5V / +3V3 / 15V_ISO_SEC / 5V_ISOL / 6V3 (mm²) | 658 / 239 / 980 / 572 / 191 / 686 (stage 2) | - | 645 / 232 / 969 / 554 / 190 / 681 |
| stage 3b rows routed | 140 of 196 | - | 134 of 175 |

`check_board.py`, `check_domains.py` (same layer and layer to layer; ALLOW: Q19 / Q21 only) and `check_next.sh`
pass. Nothing of this stage is on In1 / In4, no switch node on an inner layer, TR1 pin 2 untouched. The 16 closed
connections: the 13 at ISO2 / AD2, the 420V feed of R23, C103 pin 2 and `Net-(U6--)` at C131 (stage 3b finds the
path now that R10 has moved).

### Left, and open points

1. **In3 15V_ISO_SEC lane at ISO2** (the supply of DRV6): the lane is 2.1 mm wide there (x 74.4 ... 76.5) and the
   vias of ISO_SEC_DHB_HI / _LO stand in it (they cannot move: 5V_ISOL on B.Cu to the west, R38 on F.Cu to the east),
   which leaves 0.67 mm west and 0.43 mm east of each for 1 mm - about 0.7 A at 0.5 oz, against < 0.1 A average.
   The dead 5.1 F.Cu track that used to run in parallel is gone. If more is wanted: a 15V_ISO_SEC track on B.Cu
   from D4 to DRV6, or the 5V_ISOL track on B.Cu 0.5 mm further west (then the two vias and the lane move).
2. **R79:** legal, but with 0.05 mm of margin at the via. Cleaner: R49 0.5 mm to the left as well (one more
   part), or a via in the pad of R79 pin 1 (the vias of this stack-up are filled and capped) - not done, both are
   outside what was approved. Recommendation: move R49 with the analog review.
3. **420V divider placement.** It works where it is, but the 420 V line now runs 24 mm past the ADC to a divider
   that sits between ISO2 and the 15 V output. With R23 / R34 / R39 at the 420V pour (y about -41, 16 mm north) the
   high-voltage part would be 3 mm long and only the 1 V node would travel. Bigger move than approved; recommended
   for the next placement touch.
4. `DHB_LOW_GATE_SEC` 1.15 mm from R149 pin 2 (Q8's gate loop), DAB_DIS at DRV5 pin 5, PWM2 FB / VERR / VIN, the J2
   escapes (pins 38 / 42 / 43), TX / RX, the Kelvin pairs: later stages, unchanged.
5. A rebuild is still not bit-identical (plane vias of stage 3a, the +3V3 feed of C98): this stage draws its own
   copper for ISO2 pins 8 / 9 / 16, but the two stage-3a routes next to it (ISO2 pin 1 / C98) are found by the grid
   router and moved by 1 mm in this rebuild (the +3V3 via is now at (58.4, -29.4) next to C98, the In2 feed ends
   there). The fan-out does not depend on where they land.

## J2 escapes and J2 nets (routing stage 3e, 2026-11-20)

```
python3 tools/next/route_s3b_signals.py --strip   # full rebuild of stages 3a - 3e
python3 tools/next/route_s3e_j2.py --strip
python3 tools/next/route_s3d_iso2.py --strip
python3 tools/next/route_s3c_cleanup.py --strip
python3 tools/next/route_s3a_power.py
python3 tools/next/route_s3c_cleanup.py
python3 tools/next/route_s3d_iso2.py
python3 tools/next/route_s3e_j2.py                # this stage: drawn copper, before the grid router of stage 3b
python3 tools/next/route_s3b_signals.py
tools/p2k/bin/kipy tools/next/route_s2_planes.py
python3 tools/next/render_inner_layers.py && python3 tools/next/render_s3a.py     # PNGs in routing/
```

`route_s3e_j2.py` is a step table like stage 3d (`--dry-run OUT.kicad_pcb`, `--strip`, any other option is
refused); all of it is drawn copper, no `auto` step, no `relax`. 5.1 copper it deletes stays deleted
(`routing/deleted_s3e.json`: 58 segments, 220 mm, and 1 via), no part is moved (`routing/moves_s3e.json` is empty),
what it adds is rebuilt on every run (`routing/s3e_added.json`: 119 segments - In2 311 mm, B.Cu 52 mm, F.Cu 9 mm -
and 10 vias). The rows of these nets are gone from the stage 3b table (175 -> 150 rows). Changed in the data of
the earlier stages: stage 3a keeps the ground track of ISO1 pin 8 out of the via site of pin 7 (`avoid` box), stage
3c ends its EPWM5A lane where the bundle below turns (x -1.848).

### Escape geometry at J2

Pads 0.805 mm round on every layer, pitch 1.27 mm: 0.465 mm between two pads of a column and between the two
columns. A 0.15 mm track fits only centred, 0.1575 mm each side:

- between two signal pads on any layer (SIGNAL class clearance 0.15 mm);
- between two GND pads **only on In2** (rule "PRIMARY_LV inner layers 0.15 mm" of stage 3d; 0.2 mm on the outer
  layers leaves no room - this is why the 5.1 escape of pin 38 between the grounded pins 35 / 37 was cut).

The header is crossed at right angles through the gap between two rows (y of the gap = pin y + 0.635), a pad of
the far column is entered at 45 degrees from the crossing point between the columns (x 33.7707). The script has
the pin positions as functions (`pin_y`, `gap_y`), the tracks are written from them.

| Pin, net | Route | Length |
|---|---|---|
| 38 DHB_I_MEAS (R42 / C26) | 5.1 F.Cu track, via 0.5 / 0.3 at (31.9, -1.15) west of the column, **In2** through the gap 35 / 37 (both GND) into pin 38 | F.Cu 2.6 mm new, In2 3.6 mm |
| 42 PFC_I1_MEAS (R96 / C88) | B.Cu 1.3 mm from R96 pin 1, via (32.1, 4.3), **F.Cu** through the gap 41 / 43 into pin 42 | F.Cu 2.7 mm |
| 43 AUX_MEAS (R132) | **In2** through the gap 42 / 44, east to a via at (36.53, 1.6) between the +3V3 and 15V tracks on F.Cu, B.Cu 2.0 mm to R132 pin 2 | In2 5.6 mm |
| 49 5V_MEAS (R135) | In2 round the south end of the header and north along x 37.4 to a via at (35.64, -3.81) and B.Cu to R135 pin 2: drawn here, 0.9 mm east of the AUX_MEAS via (the stage-3b lane at x 35.6 lay across the path of AUX_MEAS) | In2 19.4 mm |

PFC_I2_MEAS has the gap 41 / 43 on B.Cu, PFC_I1_MEAS on F.Cu (In1 ... In4 between the two), AUX_MEAS crosses
PFC_I1_MEAS between the columns on In2 under the In1 ground plane. All four lines run over the In1 / In4 ground
planes (In2 between In1 GND and the In3 +3V3 pour), away from the PWM lanes, which leave J2 north of pin 19.

### Control bus round mounting hole H4

The nine lanes of the 5.1 control bus on In2 (J2 -> DRV3 / ISO1 / relay driver: GPIO_BYPASS_RLY, +3V3, HT_CLK,
SYNCH_1, HT_SDATA, SYNCH_2, $HT_CS, EPWM5A, EPWM6A) passed 1.5 mm from the centre of H4, which is earthed in 5.2
(hole clearance 3.2 mm): they were cut there, and stage 3b got two of them through on a detour. All nine are drawn
again as one bundle, 0.1524 mm wide on 0.3048 mm pitch, same order everywhere: the kept west lane -> 45 degrees
south-east -> east above the hole -> 45 degrees south-east (tangent) -> the kept east lane -> the kept diagonal bus.
Innermost lane (GPIO_BYPASS_RLY) 5.03 mm from the hole centre: its edge 3.2 mm from the ring of H4 (the stricter
measure of `s3_router.py`), 3.45 mm from the hole wall; outermost (EPWM6A) 7.47 mm.

Nine lanes did not fit between the hole and the 5.1 5V via at (8.81, -47.45) with the `Net-(C63-Pad1)` lane round
it (2.7 mm, 2.9 mm needed): the **5V via stands 1.35 mm further east** at (10.15, -48.0) (0.6 / 0.3), its B.Cu
track passes north of the +1V65_BIAS via at (7.9, -49.7), and the C63 lane comes straight down x 8.8 and turns
outside the bundle. This also clears the 5.1 marker "5V via 0.166 mm from the +1V65_BIAS track".

### DRV3, DRV5, ISO1

- **DRV3 inputs (EPWM5A pin 1, EPWM6A pin 2).** Via sites: F.Cu has the heater switch node north of y -56.1
  (1.2 mm), B.Cu the anode pad of D11 and the floating supply `Net-(DRV3-VDDA)`; what is left is x -20 ... -15.3 /
  y -54.3 ... -51.5. The dead end of the 5.1 5V lane and a dangling 5.1 GND stub on In2 ran through it: deleted
  (5 segments). EPWM5A: In2 lane -> via (-16.51, -53.9) -> B.Cu 6.0 mm to pin 1 and on to R78 pin 2. EPWM6A: In2
  lane west along y -56.39 and south-west to a via at (-18.6, -52.57) -> B.Cu 2.9 mm to pin 2. Vias from the west:
  5V (stage 3a), EPWM6A, EPWM5A = pin order 3, 2, 1.
- **DRV5 inputs.** B12 / PRI_DHB_HI arrive at the 5.1 vias (19.85 / 19.0, -46.4), DAB_DIS (stage 3b) west of
  them; pin 1 (B12) lies south of pin 2 (PRI_DHB_HI), so the lanes turn west below pin 1 in the order B12,
  PRI_DHB_HI, DAB_DIS from the north: B12 enters pin 1 from below (B.Cu 6.1 mm), PRI_DHB_HI goes round its west
  end into pin 2 (9.8 mm, 0.275 mm from the pads on both sides). The stage-3b route of PRI_DHB_HI (east end of pin
  2) had shut pin 1 in. **DAB_DIS -> pin 5:** the east ends of pins 4 - 7 are inside the 5V link pin 3 - pin 8 of
  stage 3a, so 0.2 mm on B.Cu from R129 pin 1 between C94 and C118 to the west end of pin 5 (7.9 mm); the
  dead-time net R127 - C118 beside it is drawn here as well (0.2 mm, 4.4 mm; a 0.4 mm track of stage 3b does not
  fit next to it). That track cuts C94 pin 2 / DRV5 pin 4 and R127 pin 2 off the B.Cu ground pour: **two ground
  vias** 0.5 / 0.3 at (14.0, -53.26) and (12.45, -55.0) into the planes, through the F.Cu DC+ pour next to the
  hole of the 5V via of stage 3a.
- **HT_SDATA at ISO1 pin 7.** TR2 (heater domain) stands 6.7 mm north of the pin, a via is only possible south of
  y -56.6 (8.0 mm in plan view): F.Cu 3.2 mm south-east between the HT_CLK track of pin 6 and the ground via of
  pin 8 to a via at (-35.1, -56.5), In2 4.5 mm west and round the vias of pins 3 - 5 under the primary pad row (8.7
  mm from the heater-side pads) to the end of the kept 5.1 lane.

### Numbers

| | 8fa3b1b (before) | after stage 3e |
|---|---|---|
| unconnected | 43 | **29** |
| clearance markers, first error per track | 7 (HV 1, PRIMARY_LV 5, HEATER 1) | **6** (1 / 4 / 1) |
| clearance markers, all errors | 9 (1 / 7 / 1) | 8 (1 / 6 / 1) |
| dangling tracks / vias | 59 / 0 | 37 / 0 |
| courtyard overlaps | 130 | 130 |
| planes In1 / In4: GND / ISO_GND / HT_GND (mm²) | 5577 / 2225 / 909 | 5574 / 2225 / 909 |
| In3 pours: 15V / 5V / +3V3 / 15V_ISO_SEC / 5V_ISOL / 6V3 (mm²) | 645 / 232 / 969 / 554 / 190 / 681 | 644 / 232 / 967 / 554 / 190 / 681 |
| stage 3b rows routed | 134 of 175 | 125 of 150 |

`check_board.py`, `check_domains.py` (same layer and layer to layer; ALLOW: Q19 / Q21 only) and `check_next.sh`
pass. Nothing of this stage is on In1 / In4, no switch node on an inner layer, TR1 pin 2 untouched, no via near
the PRI / SEC barrier. The 14 closed connections: DHB_I_MEAS, PFC_I1_MEAS, AUX_MEAS, the six open bus lanes
(SYNCH_1, SYNCH_2, HT_CLK, GPIO_BYPASS_RLY, EPWM5A, EPWM6A; $HT_CS and HT_SDATA were joined by stage 3b before
on a detour, the +3V3 lane is joined now and its open end is C125), EPWM5A at DRV3, HT_SDATA at ISO1, B12, DAB_DIS at DRV5 pin 5, the +3V3 lane to U1 (stage 3b finds it now).

### Left, and open points

1. **UART TX / RX (J2 pins 26 / 24 -> U11 pins 4 / 5) and the +3V3 feed of U11 pin 3: not routed.** U11 lies
   north of the control bus, J2 pins 24 / 26 south of the pins the bus leaves from, and primary copper may not
   come closer than 8.0 mm to the UART island (x -4.4 ... 20.3 for y < -65.3). On In2 alone there is no path:
   south-west of the bus the lanes end at H4 / the PFC choke pin L2.2 and would still have to cross the bus at
   DRV3; north-east of it they have to cross every lane that goes north into the U1 block (C63, C11, +1V65_BIAS,
   +3V3, HEATER_CURRENT). Choices: (a) TX / RX as two more inner lanes of the H4 bundle (the bundle and the 5V via
   move out by 0.6 mm), In2 south of the bus to x about -4, two vias each south of the bus (outside the F.Cu DC+
   pour) and B.Cu north through the empty strip x -6.5 ... -4.4 to vias beside U11 pins 4 / 5, with the +3V3 of
   U11 as a third B.Cu track from a via on the +3V3 bus lane; at J2 the two lines leave pins 24 / 26 on an outer
   layer, because the C63 lane (x 29.6) closes In2 west of the header; (b) move U11 / J4. Recommendation: (a), as
   its own stage with the bundle redrawn for eleven lanes. The 5.1 stubs of TX / RX on B.Cu (to x 40.6 / 48.7,
   towards the old UART place) are still there.
2. *(Done in stage 3f, see below.)* **R77 (pull-down of EPWM6A) and the 5V link bus -> DRV3: both open, one decision.** R77 sits at (-8.0, -62.6)
   on B.Cu; its 5.1 connection is an In2 leg (x -9.12) from the bus plus a via that no longer exists: every via
   site at R77 is in the F.Cu DC+ zone of Q11's tab (`S3A_Q11_tab_DC`), and B.Cu is closed by the bootstrap node of
   D11 and the 15V tracks. The 5V of DRV3 / the relay driver / ISO1 came through the same bus (5.1: B.Cu from the
   via at the bundle to x -11.7, where D11 stands now). 5V has to be the lane north of EPWM6A (pin order 3, 2, 1
   at DRV3), and exactly there the leg of R77 crosses. **Recommendation: move R77 next to DRV3 pin 2** (beside R78,
   about 10 mm - more than this stage may do); then the leg goes, 5V is drawn as the tenth lane (0.25 mm; room for
   it is kept: 0.6 mm between EPWM6A and the +1V65_BIAS lane) with a via beside the end of its B.Cu track at
   (3.6, -49.8). Without the move 5V needs a 15 mm loop round the R77 via. The dead 5.1 5V lane at DRV3 is
   deleted; the live lane ends at (-21.0, -48.1).
3. **DAB_DIS, branch to DRV5** is still the stage-3b route: 59 mm with 5 vias (it has to cross the +3V3 trunk
   north-east of J2). To be drawn with one F.Cu hop. GPIO_BYPASS_RLY west of the bus (38 mm B.Cu through the gap
   at C85, 1 via) and the short stubs at ISO1 pins 3 - 6 are stage-3b routes that look right.
4. `+3V3` at C125 / C87 (U1 block) and `Net-(R51-Pad2)` are not J2 nets: unchanged (open).
5. Two more holes in the F.Cu DC+ pour (the ground vias at DRV5). The pour is the feed of the heater bridge only
   (about 4.5 mm of copper is left beside the column of holes at x 12 ... 14); if that is not wanted, DAB_DIS has
   to reach pin 5 by an In2 hop instead (two vias as well).
6. A rebuild is still not bit-identical in stage 3a / 3b (plane vias); stages 3c, 3d and 3e reproduce exactly.

### Stage 3f: R77 moved, 5V lane to DRV3 (2026-11-20)

Open point 2, with the move approved by the user. Drawn in the group "R77 / 5V link" of
`tools/next/route_s3e_j2.py` (applied on the current board, then `route_s2_planes.py`; no full rebuild).

- **R77** moved from (-7.21, -62.61, 180 deg) to (-17.45, -47.1, 90 deg) on B.Cu, 18.6 mm (logged in
  `routing/moves_s3e.json`): south of DRV3 pin 2, beside R78. Pin 2 on a 0.2 mm B.Cu track from the pad of DRV3
  pin 2, pin 1 on a GND via (0.6 / 0.3) at (-17.45, -45.2) into the planes. Its 5.1 In2 leg (x -9.12) and the pad
  stubs at the old place are deleted (`routing/deleted_s3e.json`).
- **5V** is the tenth lane of the H4 bundle on In2, 0.25 mm: via (0.5 / 0.3) at (4.33, -50.75) beside the end of
  the B.Cu track at (3.6, -49.8), west diagonal y = x - 55.08 (0.33 mm from the EPWM6A lane, 0.28 mm from the
  +1V65_BIAS via at (4.5, -51.5)), lane y -56.82 north of EPWM6A to x -15.58, then down to the 5V via of stage 3a
  at DRV3 pin 3 (-19.7, -51.29). The 5V of DRV3, the relay driver and ISO1 hangs on that via (kept In2 lane
  y -48.09); no 5V connection is open.

| | before | after |
|---|---|---|
| unconnected | 29 | **27** |
| clearance markers, first error per track | 6 | 6 (the same six) |
| dangling tracks / vias | 37 / 0 | 34 / 0 |
| courtyard overlaps | 130 | 130 |

`check_next.sh`, `check_board.py`, `check_domains.py` pass (ALLOW: Q19 / Q21 only); nothing on In1 / In4, no
`relax`. Left: open points 1, 3 - 6 above. The full rebuild in the documented order was not run with this group.

## User placement 2026-11-21, transformer pins

The user moved six parts by hand in KiCad. They are data now – `kicad_next/routing/moves_user.json`, read by
`route_s3a_power.py` as the `move` steps of its first group "user placement", so every rebuild puts the parts
there again (edit the JSON to change a place):

| Part | Before | Now | What |
|---|---|---|---|
| C16 | (76.1, −58.6), −90° | (76.1, −50.6), 90° | DAB secondary split capacitors swapped and turned: TRANS_SEC pads face each other at TR3 pins 9 / 10, the 420V pad at the bridge end |
| C55 | (76.1, −50.6), −90° | (76.1, −58.6), 90° | same |
| C47 | (23.05, −86.5), −90° | (22.88, −71.71), −90° | DAB primary split capacitors 14.8 mm nearer to the bridge |
| C54 | (23.05, −78.5), −90° | (22.88, −63.71), −90° | same |
| Q10 | (−12.872, −75.321), 90° | (−13.737, −63.072), −90° | heater half-bridge FETs swapped and turned |
| Q11 | (−12.771, −63.583), 90° | (−13.838, −74.810), −90° | same |

**Transformer pins** (winding tables: [CHANGES_5_2.md](CHANGES_5_2.md) "Transformer pins and winding tables",
`simulation/dab/DAB_TRANSFORMER.md` 5): TR3 primary start (dot) 1 + 2 → **4 + 5** (DHB_CAP, beside C47 / C54),
finish 7 + 8; secondary start (dot) 9 + 10, finish 15 + 16 → 13 + 14 (commit 6c3a9bf) → **11 + 12** (switch node,
user decision of the same day: subsection "TR3 secondary finish on pins 11 / 12 …" below). TR2 unchanged (its pins
were the nearest already). The footprint has pads only on the used pins: `gen_next_footprints.py`, then

```
tools/p2k/bin/kipy tools/next/update_board_parts.py [--check] [REF ...]   # default TR2 TR3
```

= "update PCB from schematic" for single parts: replaces the board footprint by the library one if its pads
differ (place / rotation / side / fields kept) and sets the pad nets from the netlist; no copper is touched.

### Re-route after the user placement (2026-11-21)

Full rebuild in the documented order (3b / 3e / 3d / 3c `--strip`, 3a, 3c, 3d, 3e, 3b, planes) with changed step
data in `route_s3a_power.py` (and three rows of `route_s3b_signals.py`); stages 3c / 3d / 3e came out unchanged.
The 13 tracks / vias and the zone outline the user had moved with the parts are deleted once and built again by the
scripts (`routing/deleted_user_moves.json`, with 12 pieces of old stage-3a copper at C16 / C55 that KiCad had
re-netted to the swapped pads).

- **DAB primary.** DC+ as the user drew it: 1.5 mm from x 41.5 west along y −75.21 (between the pin places 3 and 4,
  1.46 mm from pin 4) to C47.1 – 55 mm from Q19 pin 2 instead of 69 mm. `S3A_DHB_CAP_F` = the user's outline, 0.4 mm
  wider at pins 4 / 5 (10.7 × 7.9 mm, 2.7 mm between the capacitor pads and the pins). `S3A_DHB_CURRENT_F` ends at
  C54.2 (y −62.1). The balancing resistors R143 – R146 stay 14.8 mm north of the capacitors on B.Cu (their place
  under the new capacitor position is taken by C92 / R41 / DRV5): 0.4 mm links by the router – DC+ down F.Cu x 24.3
  into the feed, DHB_CAP down the west edge (x 20.7) to C47.2 / C54.1, DHB_CURRENT to a via above C54.2. Kelvin
  track DHB_CURRENT (stage 3b) starts at C54.2.
- **DAB secondary.** Switch node 1.6 mm: x 55.45 to y −60.25, 45° to (67, −71.8), pins 13 / 14 (pins 11 / 12 and
  another path since the next subsection). C16.1 sits in the
  420V band of Q21 pin 2, C55.2 in the ISO_GND pour (table above). **R147 – R150 keep their places but swap their
  ends** (sheet 7: R150 + R149 across C16, R148 + R147 across C55 – R147.1 = ISO_GND, R150.2 = 420V), so every
  resistor end is under its capacitor pad again; no part moved.
- **Heater.** Q11's DC+ tab is 2.1 mm from the neck to C42 / C49 / C20 and joined to it and to the DC+ pour by
  `S3A_Q11_tab_DC` (priority 91). Switch node: one area from Q10's tab to TR2 pins 1 / 2 and up a column west of
  Q11 to Q11 pin 3. HEATER_CURRENT: Q10.3 → via (−12.8, −68.6) between the tabs → B.Cu under Q11 → R30.1; the
  B ↔ F via of the HEATER_CURRENT pours moved to (−17.8, −82.8) (the old place is 0.25 mm from Q11 pin 3).
  (Superseded by the next subsection: the gate parts are at their FETs now.)
  **Gate parts stayed where they were** (R24 / R36 / D35 at Q10 now, R37 / R31 / D33 at Q11): the high-side gate is
  drawn – B.Cu under Q11, via (−17.6, −78.3) in the switch-node column, F.Cu between the DC+ tab (1.4 mm) and pin 3
  to pin 1, beside its return, ≈ 21 mm; the low-side gate (router, 7 mm) and HEATER_LOW_DRV (In2 from DRV3 pin 10 to
  a new via east of R31) are routed. Both gates were open before.

| | eb497bb | user edit | now |
|---|---|---|---|
| shorts | 0 | 11 | **0** |
| unconnected | 27 | 39 | **24** |
| clearance markers (first error per track) | 6 | 65 | 6 (5 the same, the sixth is the same 5V track at D9's other pad) |
| dangling tracks / vias | 34 / 0 | 43 / – | 33 / 0 |
| courtyard overlaps | 130 | 130 | 130 |

`check_next.sh`, `check_board.py`, `check_domains.py` pass (ALLOW: Q19 / Q21 only); no switch-node copper and no
new track on an inner layer besides In2 signals, nothing new on In1 / In4, no new `relax`; 356 segments / 96 vias
from stage 3a, 404 / 44 from stage 3b. Stage 3b: 126 of 149 rows (the open ones are those of eb497bb less the two
heater gates).

Open / for a decision (state of 2744443; 1 and 2 are done in the next subsection):
1. ~~TR3 secondary finish on 11 + 12 instead of 13 + 14~~ – done.
2. ~~Heater gate parts at the wrong FET since the swap~~ – done.
3. **R143 – R146** are 14.8 mm from C47 / C54 now (µA only – cosmetic); a place under the capacitors needs C92 / R41
   moved.
4. The loop ISO_GND C55.2 → Q8 pin 3 runs through the planes (≈ 22 mm, was ≈ 12 mm with C55 at the bridge end);
   420V Q21 pin 2 → C16.1 is ≈ 22 mm in the band (was ≈ 43 mm).

### TR3 secondary finish on pins 11 / 12, heater gate parts at their FETs (2026-11-21)

Two follow-ups the user approved. 13 parts moved, all on B.Cu; the moves are in
`kicad_next/routing/moves_user.json` (entries with `"by": "agent"`, applied by `route_s3a_power.py` with the user's
own six), R158 is a `move` step of stage 3a as before. TR3: `gen_symbols.py`, `sheets/sheet07.py`,
`gen_next_footprints.py`, `gen_next_3d.py`, then `update_board_parts.py`; full rebuild in the documented order.

| Part | Before | Now | mm | What |
|---|---|---|---|---|
| R75 | (70.646, −61.496) | (73.2, −61.496) | 2.55 | pull-downs of DRV6's inputs stood on pin place 11: east of the pin column, pads 1.28 mm from the pin pad |
| R76 | (70.646, −60.226) | (73.2, −60.226) | 2.55 | same |
| C72 | (68.325, −65.3), 180° | (66.1, −65.0), 90° | 2.25 | stood on pin place 12: west of it and turned, pads 1.3 mm from the pin pad, 15V_ISO_SEC pad beside D18's anode |
| D18 | (62.45, −66.8) | (61.65, −66.8) | 0.8 | room for C72 between its anode pad and pin 12 |
| R24, R59, R36, D35 | at Q10 (old place of Q11) | each (−1.067, −11.227) | 11.28 | high-side gate group moved exactly as Q11 was: R24 (−19.424, −73.794), R59 (−19.403, −76.334), R36 (−17.445, −79.153), D35 (−15.537, −76.937) |
| R37, R31, D33, R66 | at Q11 (old place of Q10) | each (−0.865, +7.0) | 7.05 | low-side gate group: R37 (−10.893, −65.1), R31 (−8.861, −65.1), D33 (−9.907, −67.632), R66 (−11.165, −70.064). Q10 itself moved (−0.865, +12.249); C52 / R99 stand on the last 5 mm, so the group stops 5.2 mm short and ends at Q10's gate pin instead of beside the tab |
| R158 | (−13.5, −81.61) | (−13.5, −82.0) | 0.39 | its HEATER_CURRENT pad 1.39 mm from the high-side gate via |

**TR3 secondary finish 11 + 12** (stage 3a group "DAB secondary", stage 3d group "DRV6 inputs").
- Switch node, F.Cu 1.6 mm: x 55.45 to y −56.1, 45° over DRV6 to (61.15, −61.8), east into pin 11, up the pin column
  to pin 12. **Q21 pin 3 → first pin 30.9 mm (was 37.5 mm to pin 13), second pin 35.9 mm (was 42.5 mm): 6.6 mm
  less, not the 10 mm of the pin pitch.** The straight 45° line from Q21 to pin 11 would be 26 mm, but it runs over
  the via sites of DRV6 pins 3 / 4 / 5 (5V_ISOL, ISO_GND, DAB_DIS_SEC) and the 1.2 mm HV rule keeps every via of
  another net 2.3 mm from the track centre; the path taken turns as early as the 15V_ISO_SEC via of DRV6 pin 11
  allows (1.3 mm).
- DRV6 inputs ISO_SEC_DHB_HI / LO: the 5.1 lane ends ran through pin place 11 and are deleted (KiCad had given the
  two In2 pieces and the via at (68.34, −61.45) the switch-node net when the pad came on top of them – deleted under
  both names). In2 lanes 0.4 mm from the ends of the 5.1 lanes (x 79.4 / 78.1), between the pads of pins 10 and 11
  (LO 0.65 mm from pin 10 = TRANS_SEC, HI 0.75 mm from pin 11; inner-layer rule 0.5 mm), to vias under DRV6 at
  (64.0, −59.45) / (62.8, −59.45): 1.25 mm from the switch-node track on F.Cu. R76 taps LO by a via on its lane
  (73.6, −58.85; 1.34 mm from the TRANS_SEC area), R75 taps HI by a via south of it and a 3.1 mm In2 stub. Their
  ISO_GND ends go to R147 pin 1 (was open in 2744443).
- C72: one via per pad between its pads – 15V_ISO_SEC (66.6, −64.9) into the In3 pour, ISO_GND (65.6, −64.75) into
  the planes – and 0.6 mm to D18's anode. The 5.1 via and tracks of the old place are deleted.
- No switch-node copper on an inner layer (the pin barrels as before), nothing new on In1 / In4.

**Heater gate loops** (stage 3a group "heater LLC", all drawn; the rows are gone from stage 3b).
- **High side.** HEATER_HI_DRV: DRV3 pin 15 → B.Cu column x −20.8 between TR2 and the FETs (1.28 mm from the 15V pad
  of C18) → R24 / R59, 16.8 mm to R24 (19.3 mm to R59); it was open in 2744443. Its return on the same layer: a 0.5 mm switch-node track
  between the pads of R24 / R59 (x −19.42, 1.4 mm beside it), stitched to the F.Cu switch-node area at both ends,
  ending on R36 pin 2 at Q11's source pin. DRV3 pin 14 and C25 pin 2 each have a via into the tab copper of Q10.
  Gate: R24 pin 2 east round D35's cathode to the node R36 pin 1 / D35 anode, via (−14.6, −78.3), F.Cu between the DC+
  tab (1.4 mm) and the source pin to pin 1. **D35 anode → gate pin 5.5 mm (was 21 mm)**, R24 pin 2 → gate pin
  12.5 mm (was 29 mm); the net has 15.4 mm of track (was 31.0 mm).
- **Low side.** HEATER_LOW_DRV lands on a via north of R37 / R31 at (−9.2, −62.95) (In2 lane y −62.95 from DRV3 pin 10,
  19 mm; the via in the DC+ neck at (−6.2, −70.7) is gone). Gate: R37 pin 2 → D33 anode → R66 pin 1 in one line, via
  (−12.3, −67.63) beside the HEATER_CURRENT via of the source pin, F.Cu into pin 1. **R37 pin 2 → gate pin 3.7 mm
  (was 7 mm)**; the net has 5.3 mm of track (was 10.7 mm). R66 pin 2 on the GND via east of the gate pin.
- HEATER_CURRENT trunk on B.Cu at x −11.2 below y −72.6 (2.9 mm from the high-side gate node), its branch to the
  via at (−17.8, −82.8) 1.3 mm clear of R36. C52 pin 2 (GND, under Q10's tab) hung on the B.Cu GND pour that the
  gate parts cut up: track and via at (−9.3, −60.7).
- DRV3 group rule: inside the group ≥ 0.2 mm; towards DC+, HEATER_CURRENT, 15V and GND ≥ 1.2 mm on the outer layers
  (smallest: 1.23 mm GND via of C52 ↔ R99 pin 1, 1.24 mm the same via ↔ Q10's tab, 1.25 mm gate via ↔ DC+ tab).

| | 2744443 | now |
|---|---|---|
| shorts | 0 | **0** |
| unconnected | 24 | **22** (HEATER_HI_DRV at DRV3 pin 15 and ISO_GND of R75 / R76 closed) |
| clearance markers (first error per track) | 6 | 6 (the same six tracks; 8 = 8 with `--all-track-errors`) |
| dangling tracks / vias | 33 / 0 | 32 / 0 |
| courtyard overlaps | 130 | 130 (the same pairs) |

`check_next.sh`, `check_board.py`, `check_domains.py` pass (ALLOW: Q19 / Q21 only); `check_footprints.py`: TR3
PRI-SEC 37.55 mm. No new `relax`. Stage 3a 390 segments / 104 vias (221 of 222 steps), 3d 176 / 26, 3b 365 / 41
(109 of 130 rows: the 21 open ones are rows that were open before).

Open / for a decision:
1. The switch node is 6.6 mm shorter, not 10 mm (above). The rest needs DRV6's input-side vias moved out of the
   45° line (pins 3 / 4 / 5 under the package, past the HV gate track of pin 15) – a re-layout of DRV6's fan-out.
2. HEATER_HI_DRV is 16.8 mm long (driver → gate resistors), the price of gate resistors at the FET with the FETs
   swapped: before the swap DRV3 pin 15 was 4 mm from R24. Turning the group or moving R24 / R59 back to DRV3 would
   shorten it and lengthen the gate track by the same amount.
3. The 5.1 15V stub on B.Cu at x −7.41 (y −67.7 … −63.3, dangling, 0.55 mm east of R31) is still there.
4. Points 3 and 4 of the list above are unchanged.

### Stage 3g (2026-11-21): +3V3 of U11 drawn, UART TX / RX designed but not on the board

Group "U11 +3V3" of `tools/next/route_s3e_j2.py` (applied on the current board, then `route_s2_planes.py`; no full
rebuild): **+3V3 from C134 pin 1 (on the via of U11 pin 3) to C125 pin 1**, B.Cu 0.2 mm, 25.9 mm, no via, down the
strip west of the UART island at x -4.68 (copper edge 8.2 mm from the secondary pads of U11 at x 3.625). Still open
in +3V3: the bus lane (y -52.8) to C125 - a via does not fit on the lane inside the bundle (0.3 mm pitch) - and
C125 to the U1 block (via at (5.8, -60.1)).

**TX / RX (open point 1 of stage 3e) are not routed.** The route was laid out and dry-run as two inner lanes of the
H4 bundle; it stops at one place, so nothing of it is on the board and the 5.1 stubs on B.Cu are still there.
What was found (for the next block):

- J2: In2 is open west of the header between the C63 lane (x 29.6) and the west pad column. F.Cu from pins 24 / 26
  through the gaps 21 / 23 and 23 / 25 to vias at (31.3, -8.82) / (31.3, -7.55), In2 north at x 30.65 / 30.2
  (between the C63 via (29.6, -12.2) and the GND via (31.62, -11.43), under the F.Cu piece of PFC_PWM1): no
  warning in the dry run.
- **Blocker: the neck at C56 pin 2** (GND, THT, (25.2, -17.2), pad 1.52 mm on every layer). Between that pad and
  GPIO_BYPASS_RLY (x - y = 44.7) there is 0.87 mm; PFC_PWM1 (5.1 lane on In2, from J2 pin 19) uses it, and TX / RX
  from pins 24 / 26 have to be on the bus side of PFC_PWM1. Two 0.15 mm lanes fit there (x - y = 44.265 / 43.83,
  gaps 0.155 / 0.155 / 0.17 mm), three do not. PFC_PWM1 cannot go round the other side of the pad on In2 (the
  `PFC CURRENT 3+` track at y -14.6 crosses) or on F.Cu (inside the DC+ pour "Proteus F.Cu pour 29"). Choices:
  PFC_PWM1 through the neck on B.Cu above the two In2 lanes (two more vias in a gate-drive PWM line), or move C56
  (more than 1 mm), or TX / RX on B.Cu past the neck.
- North-west of the neck the corridor between PFC_PWM1 (x - y = 44.8) and the bus is 3.4 mm wide: diagonals
  x - y = 47.8 / 47.37 (west of the +3V3 via (24.72, -23.96), 0.79 mm from the DC+ pad of C28 at (19.9, -30.2)),
  jog at x 17.6 / 17.2, x - y = 51.85 / 51.42 between the GND via (16.85, -36.28) and the 15V vias (15.24, -35.02)
  / (14.63, -38.27), then vertical at x 11.177 / 10.872 (r 5.335 / 5.03 from H4) into the bundle.
- Bundle: the nine lanes go out by two pitches (0.61 mm) round the hole only; the west diagonals stay, TX / RX
  take diagonals inside the GPIO_BYPASS_RLY one (x - y = 50.457 / 50.026) to lanes y -51.87 / -51.44. The C63
  lane turns at (8.8, -49.1) -> (11.0, -46.9). The 5V via needs a new site: (11.0, -48.3) is 0.09 mm from the GND
  pad of C120, and the first 1.15 mm of the kept 5V lane y -47.454 has to be drawn again from x 11.85.
- U11 end: vias at (-5.52, -51.6) (RX; 0.43 mm from the GPIO lane is too close, hence y -51.6) and (-4.2, -50.7)
  (TX), south of the F.Cu DC+ pour (edge y -53.5); B.Cu north at x -5.52 / -5.1 (east of the GND via of pin 7 at
  (-6.15, -74.83)), vias at (-6.15, -77.365) / (-6.15, -78.635), F.Cu 1.5 mm to pins 5 / 4. No warning there.

| | before | after |
|---|---|---|
| unconnected | 22 | **21** |
| clearance markers, first error per track | 6 | 6 (the same six) |
| courtyard overlaps | 130 | 130 |

## Stage 4a: single primary heatsink line (user placement 2026-11-22)

**The rebuild scripts are frozen from here** (`route_s3a` ... `route_s3e`, `route_s3b_signals.py`,
`route_s2_planes.py`: do not run them any more). **The board file is the source of truth**; work goes on
incrementally, one script per block that loads the board, edits it and saves. Block A:

```
tools/p2k/bin/kipy tools/next/route_s4_dab_primary.py [--dry-run OUT.kicad_pcb]   # not re-runnable on its own result
```

The user moved four parts in KiCad so that all primary power semiconductors (Q5, Q6, SICD1, SICD2, DB1, Q7, Q19)
stand in one line x 5 ... 13 on one heatsink; Q21 / Q8 keep their own secondary heatsink
(`routing/moves_user.json`, the four entries dated 2026-11-22):

| Part | Before | Now |
|---|---|---|
| Q19 | (48.16, -41.95), 180° | (12.75, -46.98), 90° |
| Q7 | (36.88, -41.95), 180° | (12.75, -58.26), 90° |
| SICD1 | (11.5, -26.73), -90° | (11.8, -21.4), 90° |
| SICD2 | (3.8, 0.1), 90° | (3.09, -3.82), -90° |

Pin column x 12.75 (pads x 11.75 ... 13.75): Q19 gate -46.98, DC+ -49.52, switch node -52.06; Q7 gate -58.26, switch
node -60.80, DHB_CURRENT -63.34. Block A only brings the board back to 0 shorts (`routing/deleted_s4.json` 138 items,
`routing/s4_added.json` 61, `routing/moves_s4.json` 7):

- **Dead copper.** Tracks of the old Q7 / Q19 pins at x 34 ... 48 / y -42 (gate ends, switch-node tracks on F.Cu / B.Cu),
  the pad spokes of the old Q7 / Q19 / SICD1 / SICD2 pads, `S3A_DHB_HI_SOURCE_F` cut back to TR3 pins 7 / 8
  (x 28.3 ... 31.0, y -58.0 ... -50.6). The pad of the old Q7 pin 3 joined the In2 sense line, R83 and the two DHB_CURRENT
  pours: a via 0.6 / 0.3 with an F.Cu cross stands there now (31.795, -41.95). The 1.5 mm DC+ feed of C47 pin 1 still
  starts at the old Q19 place (x 45.6 / 41.5): left for block B.
- **In2 bundle.** Twelve lanes do not fit between H4 (innermost lane r 5.03) and the pad of Q19 pin 1 (corner 8.35 mm
  from the hole centre; 0.5 mm HV clearance on inner layers): the nine bus lanes stay, SYNCH_1 ... EPWM6A re-stacked
  at 0.3048 mm pitch from HT_CLK (y -42.977 ... -45.176, EPWM6A 0.78 mm from the pad), the +1V65_BIAS via moved from
  0.68 mm at the gate pad to (12.4, -44.076) between SYNCH_2 and $HT_CS. **5V, Net-(C63-Pad1), Net-(C11-Pad1) and the
  DHB_CURRENT sense line cross the pin column on In2 through the gap between Q19 pin 3 and Q7 pin 1** (pads y -53.01 /
  -57.31): verticals x 14.65 / 15.118 / 15.8 east of the pins, lanes y -53.75 (C63, 0.64 mm from the switch-node pad),
  -54.2 (5V), -55.55 (C11), -56.5 (sense). 5V: via (9.0, -54.6) west of the column, B.Cu x 9.0 to the kept track at
  (9.25, -50.4); the 5V via of stage 3e at (10.15, -48.0) is gone. DRV5 pin 3 hangs on the lane by a via in its pad
  (15.25, -51.99). Nothing new on In1 / In3 / In4.
- **DRV5 small parts off the pins** (all B.Cu; DRV5 itself not moved): C118 beside R127 in the gap (dead-time net
  complete), C94 2.3 mm west on the new 5V track, C120 / R129 south of DRV5 on the DAB_DIS track, D19 3.55 mm east
  with R41 and C96 at it, 15V from a via at the end of the kept In2 15V lane under DRV5 (17.625, -51.0). These are
  **interim places**.

| | 06889d7 | user edit | now |
|---|---|---|---|
| shorts | 0 | 24 | **0** |
| unconnected | 21 | 33 | 33 |
| clearance markers (first error per track) | 6 | 95 | 6 (none at the DAB primary; not compared one by one with the six of 06889d7) |
| courtyard overlaps | 130 | 129 | 133 (the interim places of C118 / C94 / D19 / C96 / R41) |
| dangling tracks / vias | 32 / 0 | 38 / – | 31 / 0 |

`check_next.sh`, `check_board.py`, `check_domains.py` pass. `check_domains.py` reports 0 accepted pairs: the Q19 / Q21
slot exception (rule 'PRI-SEC inner layers, Q19/Q21 across the barrier slot', ALLOW) is not used any more.

**Left (block B and later):**
1. **DRV5 has to be re-laid** - it is on the wrong side now: inputs (pins 1 - 8, x 15.55) face the FET pins 0.78 mm
   away (pad to pad is legal, a track to pins 1 - 4 from the west is not: 1.2 mm to DC+ / switch node), outputs face
   TR3. Turned by 180° the outputs face the FETs, but Q19 is G - D - S from the south and the driver is source - gate -
   VDDB from the south, so gate and source cross once (C92 across the gate track, or the gate under the body), and
   the strip between the pins and the pads is 1.6 mm. Open because of it: PRI_DHB_HI -> pin 2 (its old loop ran
   0.3 mm from the DC+ pin: deleted), DAB_DIS -> pin 5.
2. Gate parts R26 / R53 / D30 / R22 (Q19) and R90 / R92 / D34 / R70 (Q7) are still at x 28 ... 42 / y -44 ... -50,
   25 - 30 mm from the FETs: both gates open.
3. DAB primary power not routed: DC+ to Q19 pin 2, switch node Q19 pin 3 / Q7 pin 2 -> TR3 pins 7 + 8 (17 mm), Q7 pin 3
   -> C54 pin 2 / R83, C92 pin 1. C67 / C70 not moved (still at (26.8, -43), DHB_CURRENT side on its pour only).
4. SICD1 / SICD2: the 5.1 pours (`Proteus F.Cu pour 29` DC+, `pour 10` / `pour 1` PFC drains) have the relief of the
   old pads in their outlines; the four pads were held only by the 0.152 mm spokes of the old pads. Spokes deleted,
   the four pads are open: pour outlines to be re-cut at the new pads.
5. Via in the pad of DRV5 pin 3 (goes with point 1).

## Stage 4b: DAB primary power on F.Cu (2026-11-22)

```
tools/p2k/bin/kipy tools/next/route_s4b_dab_primary.py [--dry-run OUT.kicad_pcb]   # not re-runnable on its own result
```

Block B, power part only (`routing/deleted_s4b.json` 11, `routing/s4b_added.json` 21, `routing/moves_s4b.json` 1).
**DRV5 and its gate / bootstrap parts are not re-laid yet** (see "Left").

- **What C67 / C70 decouple (netlist):** both are DC+ <-> DHB_CURRENT, i.e. Q19 drain to Q7 source *before* the shunt
  R83 (DHB_CURRENT -> GND). They close the HF commutation loop DC+ - Q19 - switch node - Q7 - DHB_CURRENT directly;
  C47 / C54 (DC+ - DHB_CAP - DHB_CURRENT, 1 u each) are the split-capacitor leg for TR3 pins 4 + 5 and lie in parallel
  with the same two rails. R83 only carries the input current of the bridge.
- **Switch node** `S3A_DHB_HI_SOURCE_F` (F.Cu only, 107 mm2, solid pads): Q7 pin 2 -> strip x 15.0 ... 16.55 east of the
  pin column -> Q19 pin 3 -> arm y -57.55 ... -52.0 (5.5 mm) -> TR3 pins 7 / 8. No switch-node copper on an inner layer.
- **DHB_CURRENT** crossed that arm (C54 pin 2 at y -61, R83 at y -42). `S3A_DHB_CURRENT_F` is now the south part
  (Q7 pin 3 -> C54 pin 2), `S4B_DHB_CURRENT_F` the north part (C67 pin 2), tied to 'Proteus F.Cu pour 23' / R83 by a
  1.0 mm F.Cu track (22.0, -46.9) ... (29.2, -46.75). South and north are joined **on In2**: 1.2 mm from the
  through-hole pad of Q7 pin 3, x 17.4 under the switch-node strip, y -52.3, two vias 0.8 / 0.4 at (22.6, -50.0 / -49.0).
  The whole DC current of the bridge to the shunt runs through this In2 track and the two vias.
- **C67** (26.77, -43.7) -> (19.7, -48.0) F.Cu, 0 deg: pin 1 in the new DC+ zone `S4B_DC+_F` (5.5 mm from Q19 pin 2),
  pin 2 in the north zone. **C70 not moved**: beside C67 its DC+ pad would be 0.3 mm from the 15V via (17.625, -51.0)
  of the interim DRV5 layout.
- DC+ at Q19 pin 2 and C47 pin 1 checked by net (DRC connectivity): Q19 pin 2 is in 'Proteus F.Cu pour 29'; the
  1.5 mm track (41.5, -47.3) - (41.5, -75.21) - (23.83, -75.21) is the only DC+ feed of C47 pin 1 - **kept, not stale**.
- PRI_DHB_HI / B12 vias (19.0 / 19.854, -46.4) moved to y -45.0 (pad edge of R73 / R74): 1.1 mm from C67 pin 1.
  The F.Cu sense track C54 pin 2 -> via (19.7, -57.873) lay in the arm: deleted; the In2 sense lane (y -56.5) now
  taps the In2 return at (17.4, -56.5) - not a Kelvin tap at C54 any more.

| | 4a | 4b |
|---|---|---|
| shorts | 0 | 0 |
| unconnected | 33 | 30 |
| clearance markers | 6 | 6 (the same six, none here) |
| courtyard overlaps / dangling | 133 / 31 | 132 / 32 (B.Cu stub of the old PRI_DHB_HI via) |

**Left (block B, not done):**
1. DRV5 re-lay (both gates, R22, PRI_DHB_HI -> pin 2, DAB_DIS -> pin 5 still open). Worked out, not on the board:
   DRV5 on B.Cu turned 180 deg at about (21.2, -54.9) puts pin 15 (low gate) at y -58.08 beside Q7 pin 1 and
   pins 9 / 10 / 11 at y -50.5 / -51.7 / -53.0. Limits: east pads must stay 1.2 mm off the TR3 pads (centre x <= 21.4),
   so only 1.8 mm remain between the FET pads and the driver pads - C92 does not fit there; HG and VDDB have to leave
   under the body; a track past the DC+ pad needs x >= 15.1 on B.Cu. R73 / R74 / C95 and the vias of C95, the 5V via in
   the pad of the old pin 3 and the 15V via (17.625, -51.0) stand where the high-side parts have to go; PRI_DHB_HI / B12 /
   DAB_DIS then enter under the body from the north in the window x 21.3 ... 24.6.
2. The 5V via (15.25, -51.99) and the GND via (12.45, -55.0) cut the switch-node fill at Q19 pin 3 (it joins the
   strip south of the pad, about 1 mm neck): both go with the DRV5 re-lay. C70 to the bridge after that.
3. R83 is 17 mm from Q7 pin 3, so the low-side gate return (driver GND -> R83 -> DHB_CURRENT -> source) is long
   whatever DRV5 does; moving R83 to Q7 pin 3 / C54 pin 2 would also take the bridge current off In2.
4. In2 lanes x 14.65 / 15.118 / 15.8 and y -53.75 ... -56.5 still lie under the switch-node copper in plan view
   (In1 GND between them); not moved.
5. SICD1 / SICD2 pour outlines (4 pads open).

## Stage 4d: shunt R83 at Q7 pin 3 (2026-11-22)

```
tools/p2k/bin/kipy tools/next/route_s4d_shunt_u1.py [--dry-run OUT.kicad_pcb]   # not re-runnable on its own result
```

Block D1 of the DRV5 re-lay (user decision 2026-11-22: DRV5 goes to the bottom side west of the Q7 / Q19 pin column,
B.Cu x 2 ... 11.3 / y -66 ... -44, block D2). **Only part 1 of D1 is on the board: R83. The U1 block is not moved**
(`routing/moves_s4d.json` 1, `routing/deleted_s4d.json` 26, `routing/s4d_added.json` 13).

- **R83** B.Cu (29.99, -42.0) -> **F.Cu (15.9, -64.04), 90 deg**, pads lying east-west (2.0 x 0.35 mm): pin 1
  (DHB_CURRENT, y -63.55) inside `S3A_DHB_CURRENT_F`, pin 2 (GND, y -64.525) south of the zone, 0.53 mm inside the
  8 mm line of the UART island (y -65.255). Bottom side was not possible without moving C96 (its 15V pad lies at
  x 14.2 ... 15.5 beside the pin). Power path: Q7 pin 3 -> 1.15 mm of the F.Cu zone (0.9 mm wide beside R83: the zone
  keeps 0.5 mm from the GND pad; about 0.6 mOhm, outside the measurement) -> R83 -> GND: F.Cu 0.35 mm along the pad
  to **three vias** at its east end, (17.96, -64.55) 0.5 / 0.3 (kept via of C96) and new (17.25 / 18.55, -64.93)
  0.6 / 0.3, all solid in In1 / In4 (the B.Cu GND pour does not reach them). The bridge input current is off In2.
- **C67 return** (HF loop): unchanged zone `S4B_DHB_CURRENT_F` -> vias (22.6, -50 / -49) -> In2 1.2 mm x 17.4 -> y -62.14 ->
  now turns to Q7 pin 3 at x 15.5 / 14.3 (was 17.4 / 16.2) to stay off the Kelvin via. It ends in the through-hole pad
  of Q7 pin 3, 1.15 mm before R83 pin 1.
- **Kelvin tap**: via 0.5 / 0.3 at (16.5, -63.75), half in the inner edge of R83 pin 1 (between the two pads), ->
  In2 0.2 mm lane y -64.8 south of Q7 pin 3 (0.4 mm from its pad, 2.95 mm from the switch-node pad of pin 2) -> the kept
  via (2.3, -63.3) of R104, 15.3 mm. The old lane (In2 y -56.5 / x 7.2, tapped on the In2 return) is deleted. There is no
  separate ground-sense net in the schematic: R101 pin 2 is plain GND at the plane.
- **Old place**: the 1.0 mm F.Cu tie of stage 4b, the pad spokes and 'Proteus B.Cu pour 23' are deleted. C70 pin 2 /
  'Proteus F.Cu pour 23' / the via (31.795, -41.95) hang on the rest of the old In2 sense line (0.254 mm, ends on the In2
  return at (22.6, -49.6)) - interim until C70 moves to the bridge.

| | 4b | 4d |
|---|---|---|
| shorts | 0 | 0 |
| unconnected | 30 | 30 (same nets) |
| clearance markers | 6 | 6 (the same six) |
| courtyard overlaps / dangling | 132 / 32 | 132 / 32 |

**Left of D1 (not done):**
1. **U1 block** (U1, C11, C63, C122, C123, C124, C125, C87 on F.Cu, R29, R89, R101 ... R106) still stands in
   B.Cu x -0.5 ... 10 / y -65.3 ... -52.6, C94 / C118 (DRV5) too. The place proposed for it, south of Q7 (y < -66,
   x 0 ... 20), is inside 'UART island pour keep-out (8 mm)' (x -4.4 ... 20.25, y < -65.255): no primary copper there.
   Free B.Cu beside the block is only the strip x -6.2 ... -0.6 / y -65 ... -57 (15V track x -6.75, +3V3 track
   x -4.68); the block is 10.5 x 13.8 mm as laid, and the In2 bus (y -52.3 ... -56.8 at x < -1.4) lies north of the
   strip. It needs a new compact layout (both sides) or another place - not decided.
2. When U1 moves, the Kelvin lane y -64.8 goes with it (it is the only new copper in the D2 window, on In2).
3. C96 / D19 / R41 untouched (interim); the tap via stands between the pads of C96 on B.Cu.

## Stage 4f: DRV5 channels swapped (2026-11-22)

User decision 2026-11-22 (CHANGES_5_2.md row 3.1b): DRV5 goes to the bottom side west of the Q7 / Q19 pin column, so
its pin order has to match the FET order. Schematic (`tools/next/sheets/sheet02.py`, `boot_side="A"`):

| DRV5 | before | now |
|---|---|---|
| 1 INA | B12 (low-side command, R74) | PRI_DHB_HI (R73) |
| 2 INB | PRI_DHB_HI (R73) | B12 (R74) |
| 14 VSSA / 15 OUTA / 16 VDDA | GND / DHB_LOW_GATE / 15V | DHB_HI_SOURCE / DHB_HI_GATE / `Net-(DRV5-VDDA)` (bootstrap D19 / R41 / C92) |
| 9 VSSB / 10 OUTB / 11 VDDB | DHB_HI_SOURCE / DHB_HI_GATE / `Net-(DRV5-VDDB)` | GND / DHB_LOW_GATE / 15V (C95, C96) |

Pins 3 – 8 unchanged. UCC21520 datasheet SLUSCJ9F: the two output drivers are equal ("two low-side drivers, two
high-side drivers, or a half-bridge driver", 1500 VDC functional isolation between them, DT / DISABLE act on both);
TI's half-bridge example has the high side on channel A, as DRV6 and DRV3 here. The bootstrap net is
`Net-(DRV5-VDDA)` now: `.kicad_dru` "High-side driver group DRV5", `HS_GROUPS` in `s3_router.py` and `HV_NETS` in
`setup_project.py` follow. The In3 15V plane row above still names DRV5 pin 16 - 15V is pin 11 now.

Board (`update_board_parts.py DRV5`, then `tools/next/route_s4f_drv5_swap.py`, `routing/deleted_s4f.json`): the pad
nets of DRV5 follow the schematic, the board net `Net-(DRV5-VDDB)` (C92 pin 2, R41 pin 2, 13 tracks) is renamed, and
the 22 B.Cu segments that ended on pins 1, 9, 10, 11, 14, 15, 16 with the old net are cut back to the first junction
(pin 2 had no copper). **DRV5 is not moved and not routed** - that is the next block. pcbnew's save had taken the
ground stub of pin 14 (segment + via 23.25, -51.99) along to DHB_HI_SOURCE; the script puts the via back on GND.

Left open by the cut (unconnected 30 -> 38, 0 shorts, 0 parity items): all eight swapped pins of DRV5 (1 PRI_DHB_HI,
2 B12, 9 GND, 10 DHB_LOW_GATE, 11 15V, 14 DHB_HI_SOURCE, 15 DHB_HI_GATE, 16 bootstrap). Five new clearance markers
(6 -> 11), all at DRV5's old place and gone when it is re-laid: pin 16 (now HV) 0.35 / 0.15 mm from the 15V track / via
that fed it, pins 15 / 16 0.94 / 0.86 mm from a DHB_CURRENT via, pin 14 0.175 mm from its old ground via.

## Stage 4g: DRV5 west of the Q19 pins, high-side loop (2026-11-22) – not finished

`tools/next/route_s4g_drv5.py` (incremental, not re-runnable; `routing/moves_s4g.json`, `deleted_s4g.json`,
`s4g_added.json`). Unconnected 38 -> 37, clearance markers 11 -> 6 (the five of stage 4f are gone), 0 shorts, no H4
marker.

| part | from | to | why |
|---|---|---|---|
| DRV5 | B.Cu (20.2, -53.895) | B.Cu (2.3, -49.9) rot 0 | pins 9 – 16 at x 5.9 – 8.0 facing the FET column: 16 / 15 / 14 at y -45.5 / -46.7 / -48.0, 11 / 10 / 9 at y -51.8 / -53.1 / -54.3 |
| C92 | B.Cu (25.3, -60.9) | B.Cu (9.15, -46.525) rot -90 | bootstrap capacitor on pins 16 / 14 |
| R26 | B.Cu (39.5, -46.7) | B.Cu (10.85, -46.0) rot -90 | gate resistor between pin 15 and the gate pad of Q19 |
| C94 | B.Cu (10.7, -52.6) | B.Cu (-4.55, -48.63) rot 90 | 5V decoupling on pins 3 / 4, GND via (-5.75, -49.405) |
| R103 | B.Cu (4.5, -53.864) | F.Cu (3.3, -55.55) rot 180 | was under the new body; top side west of the heatsink strip |
| C123 | B.Cu (2.1, -54.4) | F.Cu (3.3, -54.05) rot 0 | as R103 |

Done:
* High side on B.Cu only: pin 15 -> R26 -> gate pad of Q19 (about 9.0 mm pin centre to pad centre, R26 included);
  return Q19 pin 3 -> west -> north at x 10.25 (1.25 mm from the DC+ pad) -> C92 pin 1 -> pin 14, about 8.8 mm;
  bootstrap loop pin 16 -> C92 -> pin 14 about 7 mm. The 10 mm loop target is not met (out + return about 18 mm).
  Nearest high-side copper to H4: C92 pin 2 / pin 16, 5.0 mm from the hole centre. No VDDA copper on In2 any more.
* 5V: kept via (4.33, -50.75) of the west In2 feed -> pin 3 -> pin 8 under the body; the link to the east In2 lane
  (via (9.0, -54.6)) runs on B.Cu y -55.15 south of pin 9 and under the body (0.35 mm from the pads of C11).
* GND: via (8.25, -54.345) at pin 9. U1A+: via (4.3, -55.25) in pin 1 of R106 / R103; bias via (1.5, -54.9) on the
  In2 lane x 1.5.
* Deleted: the dead-end B.Cu 15V track through the window (it fed nothing), the old copper of DRV5 pins 3 / 6 / 8,
  its GND via (23.25, -51.99) and 5V via (15.25, -51.99), the old gate / bootstrap tracks of C92 and R26.

Still open:
* **15V of pin 11**: the In3 15V plane starts at x 9.5; between the pads (x 8.0) and the 1.2 mm zone of the source
  return (x 10.25) only 0.9 mm of B.Cu is left for the low side, so the 15V via, C95 and the exit of pin 10 do not fit
  beside each other yet. Low side (R90, D34, R92, R70, C95) not moved, pin 10 open.
* **+1V65_BIAS** to R103 / C123 / R105 / C122 (was open before this stage too): its old B.Cu hop ran through the
  high-side strip (deleted). The In2 lane ends at (12.4, -44.076) inside the bus; it has to cross HT_CS / EPWM5A /
  EPWM6A on another layer. Proposal: B.Cu east of the Q19 pins (x 15), west again at y -54.65 between Q19 pin 3
  and the gate pad of Q7.
* PRI_DHB_HI, B12, DAB_DIS (pins 1, 2, 5), DT parts R127 / C118, R73 / R74, C120 / R129: not moved, open.
* R22, D30, R53, D19, R41 still at their old places east of the column; clean-up there and C70 not done.
* New courtyard overlaps: C92 / DRV5, C92 / R26, R106 / DRV5.

## Stage 4h: DRV5 low side, 15V of pin 11, dead-time parts (2026-11-22) – not finished

`tools/next/route_s4h_drv5_low.py` (incremental, not re-runnable; `routing/moves_s4h.json`, `deleted_s4h.json`,
`s4h_added.json`). Unconnected 37 -> 32, clearance markers 6 -> 6, 0 shorts.

| part | from | to (all B.Cu) | why |
|---|---|---|---|
| R90 | (35.836, -46.746) rot -90 | (10.25, -56.6) rot 90 | gate resistor: pin 1 (-55.6) from pin 10, pin 2 (-57.6) to the gate pad of Q7 |
| D34 | (34.79, -49.397) rot 180 | (12.75, -54.9) rot 0 | turn-off diode in the pin-column gap (cathode west, on DHB_LOW_GATE) |
| R92 | (33.804, -46.746) rot -90 | (14.6, -57.3) rot 90 | turn-off resistor east of the gate pad of Q7 |
| R70 | (28.7, -45.036) rot -90 | (10.4, -59.6) rot 90 | gate-source resistor, GND on pin 2 of C124 (GND via (9.575, -61.8)) |
| R127 | (13.45, -55.8) rot -90 | (-5.0, -51.805) rot 180 | dead-time resistor at pin 6 |
| C118 | (12.15, -55.8) rot -90 | (-5.0, -53.1) rot 180 | dead-time capacitor beside R127 |

Done:
* **15V of pin 11**: via 0.5 / 0.3 in the pad (6.6, -51.805), In3 track 0.5 mm to (10.3, -51.805) inside the 15V plane
  (2.9 mm to the plane edge at x 9.5). No B.Cu copper in the 0.9 mm squeeze.
* **Low-side gate** on B.Cu: pin 10 -> east at y -53.075 to x 8.6 -> between the 5V via and the source return to
  (10.25, -54.6) -> R90 -> gate pad of Q7: about 9.5 mm pin centre to pad centre (4.9 mm to R90, R90 2.0, 2.6 to the
  pad). Turn-off branch R90 pin 1 -> D34 -> R92 -> gate pad about 9.5 mm. Nearest switch-node copper: source return
  track 1.9 mm, Q19 pin 3 pad 1.7 mm (track) / 1.4 mm (pad of D34); Q7 pin 2 pad 1.4 mm; DC+ more than 3 mm. The
  return enters the planes at the GND via (8.25, -54.345), 1.3 mm from pin 9.
* Dead time: pin 6 -> R127 / C118 (2.6 mm), their GND on the GND via of C94 (-5.75, -49.405).
* Deleted: all old copper of DHB_LOW_GATE, Net-(D34-PadA), Net-(Q7-G) east of the column, GND via (12.45, -55.0) and
  the GND stubs of C118 / R127 / R70 at their old places.

Still open:
* **C95 (4.7 uF 1206, 15V decoupling of pins 11 / 9) is not moved**: it is still at (24.0, -47.2), about 17 mm from
  the pins through the planes. No legal place was found beside the pins: east of the pads only x 8.0 - 8.8 is free
  (1.2 mm to the source return), a part cannot sit under the body on the same side, and vias for a top-side
  place at x < 5 land in the In2 bus. Candidates: a smaller footprint (0603) east of pin 9 / south of y -52, or C95
  on B.Cu east of the column at x 15 - 16.8.
* R22, D30, R53, D19, R41, C96 (rest of the high side), R73 / R74 / C120 / R129 and PRI_DHB_HI, B12, DAB_DIS to pins
  1 / 2 / 5, +1V65_BIAS to the U1 block, clean-up east of the column (15V via (17.625, -51.0) and its B.Cu track, old
  stubs), C70: not started. The GND track of R127 / C118 (x -5.8, y -53.1 ... -49.4) lies west of pin 5: DAB_DIS has
  to arrive by a via between it and the pad or the track is moved.
* The 5V link on B.Cu y -55.15 (0.35 mm from the pads of C11) is unchanged.
* New courtyard overlaps: R90 / R70, R90 / D34, R92 / D34, R127 / DRV5, R127 / C118, C118 / DRV5.
* Switch-node zone `S3A_DHB_HI_SOURCE_F` at Q19 pin 3 after the refill: filled x 11.8 ... 16.4 at y -51.8 (4.6 mm),
  6 mm wide from y -52.5 to -56 (unchanged by this stage; the 15V via (17.625, -51.0) is still there).

## Stage 4i: driver inputs of DRV5 – blocker found (stage 4h2), solved by a window in the In3 15V strip (2026-11-22)

On the board (`tools/next/route_s4h2_5v_link.py`, incremental, not re-runnable; `routing/deleted_s4h2.json`,
`s4h2_added.json`, `moves_s4h2.json` (empty)): the 5V link on B.Cu under DRV5 runs at y -54.98 instead of -55.15
(via (9.0, -54.6) -> (9.0, -54.98) -> (5.43, -54.98) -> kept track x 5.2): edge 0.52 mm from the pads of C11 (was
0.35), 0.21 mm from pin 9. Unconnected 32 -> 32, clearance markers unchanged, 0 shorts. No part moved. The names
`s4i` (script, `routing/*_s4i.json`) are free for the input block.

Not on the board: PRI_DHB_HI, B12, DAB_DIS to pins 1 / 2 / 5 (R73, R74, C120, R129 not moved). Findings (from the
coordinates of the board, not from a routing run):

* All three start at J2 (pins 4, 6, 18), east of the FET column; no part of them is west of it. PRI_DHB_HI / B12
  come down the In2 diagonal as its two south-east lanes (after `Net-(C11-Pad1)`, before the 0.254 mm +3V3 lane) to
  the vias (19.0, -45.0) / (19.854, -45.0); DAB_DIS comes on In2 from (33.625, -30.13) to the via (27.425, -45.43).
  Pins 1 / 2 / 5 lie north-west of the control bus, so each signal has to cross the pin column x 9.5 - 13.5 and
  the whole bus.
* Crossing the column x 9.5 - 13.5: In3 is the 15V plane strip there (free only at x < 9.5 and x 13.5 - 21); F.Cu
  is DC+ (pour 29, `S4B_DC+_F`); B.Cu north of the gate pad has 3.26 mm between the pad of C92 (VDDA) and the ring
  of H4, 1.2 + 3.2 + track needed; In2 north of the gate pad: EPWM6A edge y -45.25, gate pad + 0.5 mm at y -45.53,
  0.28 mm left, 0.45 mm needed for one 0.152 mm lane; In2 north of the bus: GPIO_BYPASS_RLY is at 5.03 mm from H4.
* In2 gap between Q19 pin 3 and the gate pad of Q7 (lanes C63 -53.75, 5V -54.2, C11 -55.55): two more lanes fit
  south of the C11 lane (y -55.88 / -56.19), but they end inside the corner of the C11 lane (x 7.9, y -55.1 ...
  -57.2) and enter only from x 16.05 - 16.2 east of it; PRI_DHB_HI / B12 leave their pocket between the C11 lane
  and the +3V3 lane end (16.8, -48.4) through a 0.41 mm gap (0.45 needed).
* +1V65_BIAS has the same problem (its lane ends at (12.4, -44.076) over the 15V strip, between Q19-G copper on
  B.Cu and DC+ on F.Cu: no via possible there); the B.Cu proposal of stage 4g (y -54.65) is now taken by D34.
* R22 / D30 / R53 / D19 / R41 / C96, C95, C70 and the clean-up east of the column were not started: C120 / R129 and
  the two input vias stand where those parts or C70 would go, and the 15V via (17.625, -51.0) with its B.Cu track
  still feeds D19 / C96.

Ways out considered: (1) re-lay the In2 bus section x 5.7 - 15.7 with the four extra lanes in it; (2) open the In3
15V strip for an In3 crossing; (3) take the four signals round the north of H4 on In2. **Decision: (2).**

### Stage 4i on the board: In3 window, PRI_DHB_HI / B12 / DAB_DIS / +1V65_BIAS routed

`tools/next/route_s4i_drv5_in.py` (incremental, not re-runnable; `routing/moves_s4i.json`, `deleted_s4i.json`,
`s4i_added.json`). Unconnected 32 -> 28 (the four nets closed), clearance markers 6 -> 6, 0 shorts, no H4 marker.

* **Window**: rule area `S4I_KO_In3_15V_window` (no zone fill, In3 only), rectangle x 9.3 ... 13.7, y -46.9 ... -42.0.
  It cuts the 15V strip (x 9.5 - 13.5) over its full width: no neck is left beside it. Band north of the gate pad of
  Q19 chosen, not the gap Q19 pin 3 / gate pad of Q7: the lanes end at pins 1 / 2 / 5 (y -45.5 ... -50.5) and come
  from the north-east, and the south gap is used by the 15V bridge below. North of the window the strip is a tab of
  the north band (y > -42.0).
* **15V of the south half** (strip south of y -46.9, pin 11 of DRV5, the band y -65 ... -60.6 with DRV3 / C18 / C52):
  In3 track 1.0 mm from the east block of the plane (24.0, -50.4) -> (24.0, -51.6) -> (17.625, -51.6) -> (17.625,
  -54.75) -> (12.0, -55.25) into the strip between Q19 pin 3 and the gate pad of Q7, 0.5 mm stub to the via (17.625,
  -51.0). DAB_DIS leaves its via (27.425, -45.43) on In3 through the east block, so the block is joined round the
  east of that via by a 0.5 mm In3 track (27.6, -44.6) -> (28.2, -44.6) -> (28.2, -46.6) -> (27.6, -46.6): the feed of
  the south half is north band -> east block -> 0.5 mm link (and whatever plane is left beside the lane) -> 1.0 mm
  track. Checked by DRC: no 15V item unconnected; with the last piece of the bridge removed on a copy the DRC
  reports the split (28 -> 29). The bridge lies under the switch-node pour `S3A_DHB_HI_SOURCE_F` (F.Cu; In1 between).
* **Lanes** (0.152 mm, In3; rows in the column chosen in the gaps between the In2 lanes above, none directly under
  one; verticals x 10.2 ... 11.13 cross the In2 bus at 45 degrees; west of x 10 the rows cross it at 45 degrees):
  * PRI_DHB_HI: kept via (19.0, -45.0) -> north -> row y -42.386 -> x 10.2 south -> row -45.455 -> via (-4.1, -45.455)
    -> B.Cu to pin 1 and R73. In3 27.8 mm. Edge 4.93 mm from the centre of H4, 1.66 mm from the gate pad.
  * B12: kept via (19.854, -45.0) -> round the south of the PRI_DHB_HI via -> x 18.5 north -> row -42.825 -> x 10.51
    -> row -45.8 -> via (-4.1, -46.725) -> pin 2 and R74. In3 29.3 mm. H4 5.42 mm, gate pad 1.24 mm.
  * DAB_DIS: kept via (27.425, -45.43) -> row -45.85 -> x 18.15 north -> row -43.434 -> x 10.82 -> row -46.15 to x 0.5
    -> diagonal -> via (-4.1, -50.535) -> pin 5, C120, R129. In3 37.6 mm. H4 5.94 mm, gate pad 0.86 mm. The branch to
    ISO2 pin 4 is untouched; the B.Cu piece from that via towards the old place of DRV5 is deleted.
  * +1V65_BIAS: new via (14.6, -44.076) on its In2 lane (0.164 mm to SYNCH_2 / $HT_CS on In2; its F.Cu antipad
    takes x 13.15 - 16.05 of the DC+ pour, the pour column to Q19 pin 2 keeps x 16.05 - 17.5) -> row -44.076 -> x 11.13
    (0.544 mm from the gate pad) -> row -46.5 to x 6.0 -> diagonal to (1.5, -51.0) -> x 1.5 south to the kept via
    (1.5, -54.9) at R103 / C123. In3 21.1 mm. H4 6.29 mm. The In2 lane end x 12.4 - 14.6 is deleted.
* Parts (all B.Cu): R73 (18.8, -44.663) rot 90 -> (-6.875, -45.2) rot 0; R74 (20.3, -44.663) rot 90 -> (-6.875, -46.9)
  rot 0; C120 (15.3, -46.45) -> (-7.0, -49.45) rot -90; R129 (16.6, -46.45) -> (-8.5, -49.45) rot -90. Their GND on the
  via of C94 (-5.75, -49.405). R127 / C118 got their own GND via (-6.9, -51.55); the GND track x -5.8 is deleted (DAB_DIS
  passes there on B.Cu).

Still open: R22, D30, R53, D19, R41, C96 to the high side (the pocket east of the column is free now apart from the
vias (19.0, -45.0) / (19.854, -45.0)), C70, C95, clean-up east of the column (15V via (17.625, -51.0) and its B.Cu
track still feed D19 / C96).

## Stage 4j: R22, bootstrap charge path, C95, C70 at the DAB primary (2026-11-22) – turn-off branch open

`tools/next/route_s4j_drv5_hs.py` (incremental, two parts: plain run, then `--part2`; neither re-runnable;
`routing/moves_s4j.json`, `deleted_s4j.json`, `s4j_added.json`). Unconnected 28 -> 26, clearance markers 6 -> 6,
0 shorts, dangling tracks 30 -> 30.

| part | from | to (all B.Cu) | why |
|---|---|---|---|
| R22 | (40.365, -44.152) rot 180 | (15.5, -48.6) rot 90 | gate-source resistor east of the Q19 pins: pin 1 from the gate pad at y -46.98, pin 2 to the source pad at y -52.06 |
| R41 | (21.6, -62.9) rot 0 | (18.0, -42.15) rot 180 | bootstrap charge resistor, VDDA end west |
| D19 | (17.6, -61.0) rot 180 | (23.4, -42.15) rot 0 | bootstrap diode, cathode on R41 |
| C96 | (16.4, -63.6) rot 0 | (28.0, -42.6) rot 90 | 15V capacitor at the anode of D19 (GND pad in the B.Cu pour) |
| C95 | (24.0, -47.2) rot 0 | (19.2, -51.6) rot 180 | 15V pad on the via (17.625, -51.0) of the In3 15V bridge, new GND via (20.4, -50.65) |
| C70 | F.Cu (26.774, -41.8) rot 0 | B.Cu (19.7, -48.0) rot 0 | under C67, pad for pad |

* **R22**: gate pad -> east on y -46.98 -> R22 (x 15.5, 1.6 mm from the DC+ pad) -> south on x 15.5 -> west on y -52.06 to the
  source pad; 0.3 mm tracks, 1.44 mm from the DC+ pad. Loop gate pad - R22 - source pad about 10.5 mm.
* **Bootstrap charge path** (B.Cu only, no via in a group net): 15V via (25.562, -48.6) of the In3 east block -> B.Cu
  0.4 mm north on x 25.562 / 24.7 (6.8 mm) -> D19 -> R41 -> one 0.3 mm VDDA track on y -42.15 west across the column
  north of the In3 window and of the +1V65_BIAS via (1.5 mm from its pad), diagonal (11.65, -42.15) - (9.6, -44.2) to pin 2
  of C92: 8.7 mm, nearest point 5.4 mm from the centre of H4 (by hand, creepage not run). D19 anode pad to C92 about 16 mm. The GND
  pour on B.Cu is opened along the row by the 1.2 mm rule.
* **C95**: 15V path pin 11 -> via in pad -> In3 strip -> bridge (12.0, -55.25) ... (17.625, -51.6) -> via (17.625, -51.0)
  in the pad of C95, about 18 mm; GND via (20.4, -50.65) -> In1 / In4 -> GND via (8.25, -54.345) at pin 9, 12.7 mm.
  About 9 mm shorter than from the old place; nothing closer is legal without a via through the switch-node pour or a
  part under the body (stage 4h).
* **C70** on B.Cu under C67: DC+ pad joined to the DC+ pad of C67 by one via 0.6 / 0.3 in both pads (18.3, -48.5) - the
  only position with 0.5 mm to the +3V3 and 15V lanes on In2; DHB_CURRENT pad by 0.8 mm B.Cu to the kept via
  (22.6, -49.0). Both capacitors: Q19 pin 2 -> F.Cu pour 5.5 mm -> pad; C70 adds the via (1.6 mm).
* **15V**: second In3 path 1.0 mm round the east of the DAB_DIS via ((27.4, -44.3) - (28.5, -44.3) - (28.5, -46.9) -
  (27.4, -46.9)) beside the 0.5 mm link. In1 (GND) under the In3 15V bridge is solid: only the antipads of Q19 pin 3 and
  of the 15V via (17.625, -51.0) (amap, x 9 ... 26, y -57 ... -50).
* Deleted: old B.Cu copper of R22, D19 / R41 / C96 (15V track x 17.625 from the via (17.625, -51.0), which stays, pour
  `Proteus B.Cu pour 19`), GND track (22.5, -46.5 ... -44.3), GND via (23.637, -47.2) and stubs of C95.

Still open:
* **Turn-off branch D30 / R53 not moved** (still at (40.5, -49.5) / (41.5, -46.7); DHB_HI_GATE at D30 and Net-(Q19-G) at
  R53 unconnected). DHB_HI_GATE exists on B.Cu only in the pocket pin 15 - gap under C92 - pin 1 of R26, closed by VDDA
  (pin 16 - C92 pin 2, 0.41 mm between the pads), C92 pin 2 / R26 pin 2 (0.24 mm apart), R26 pin 2 / gate pad (0.2 mm),
  the DC+ pad (1.2 mm) and the source return (x 10.25, C92 pin 1 / pin 14). No 1.0 mm pad of D30 fits in the pocket; a
  via out of it lands in the In3 lanes (rows -45.455 ... -46.5) and the In2 bus (0.5 mm needed); north of pin 16 is the
  H4 zone. Ways out: move C92 / R26 (R26 0.6 mm east is not possible, C92 further north is H4), a smaller D30 / R53
  between R26 and C92 after moving R26 pin 1 south, or drop the branch.
* Dangling in the area: +1V65_BIAS In2 at (1.5, -54.5) (older, not touched).

## Stage 4k: SICD1 / SICD2 back in their pours, Q19 / Q21 slot exception dropped (2026-11-22) – turn-off branch still open

`tools/next/route_s4k_hs_sicd.py` (incremental, not re-runnable; `routing/moves_s4k.json` (empty), `deleted_s4k.json`,
`s4k_added.json`). Unconnected 26 -> 22 (the four SICD items), clearance markers 6 -> 6, 0 shorts.

**SICD1 / SICD2** (moved and turned by 180° by the user: anode and cathode changed sides, so each pad stood in the
other net's pour). F.Cu outlines of pour 29 (DC+), pour 10 (PFC_DRAIN_1) and pour 1 (PFC_DRAIN_2) re-shaped, outlines
1.2 mm apart as before (the fill also keeps the 1.2 mm of "HV functional, outer layers"; zone settings unchanged:
solid pad connection, clearance 0.15 mm, priorities 55 / 36 / 27). The pad cut-outs (zone holes) of the old pad
positions are removed.
* **SICD1** (A (11.8, -21.4), K (11.8, -26.48)): the old anode lobe x 9.4 – 14.6, y -30.0 ... -24.3 now belongs to DC+ and
  joins the DC+ trunk to the east over its whole height (K solid in the pour). Pour 10 ends at x 8.2 and has a new lobe
  x 8.2 – 12.9, y -23.1 ... -20.3 round the anode (solid). PFC_DRAIN_1 copper 122.3 -> 119.7 mm².
* **SICD2** (A (3.09, -3.82), K (3.09, 1.26)): the nets cross (L1 north-west, Q6 east, the DC+ peninsula of DB1 / C73
  south, the cathode in the middle). DC+: strip 2.5 mm wide (x 5.4 – 7.9) from the peninsula north to a field round the
  cathode (x 2.3 – 7.9, y 0.8 ... 2.4); the peninsula tip is cut back to y -6.1 below the anode. Pour 1 is now only the
  L1 pad, the column west of the cathode and the anode pad (neck between the cathode pad and the AC2 pour about 1.5 mm);
  the arm to Q6 is gone from F.Cu. PFC_DRAIN_2 on B.Cu between through-hole pads, no via: SICD2 A -> Q6 drain 2.4 mm wide
  (8.8 mm), L1 -> SICD2 A 2.0 mm wide (9.3 mm, parallel to the F.Cu neck). PFC_DRAIN_2 copper: F.Cu 90.7 -> 35.5 mm²,
  B.Cu 0 -> about 40 mm². Nothing of the two drain nets on an inner layer.
* **Weak point, not solved**: the DC+ peninsula (DB1 pin 2, C73 pin 1, now also the SICD2 cathode strip) reaches the
  DC+ trunk only through a neck about 0.9 mm wide and 1.5 mm long at (12.8 ... 14.0, -18.8), between the 1.2 mm zone of
  the new anode pad of SICD1 (corner (12.8, -20.4)) and of the GND pour 30 of C73 (corner (13.2, -17.1)). It is there
  since the user move (the pad pushes the fill back), not made by this stage. Way out: cut the south-west corner of pour 30
  back to the GND pad of C73 (neck about 1.5 mm) or move SICD1 0.6 mm south.

**Q19 / Q21 slot exception removed**: rule 'PRI-SEC inner layers, Q19/Q21 across the barrier slot' deleted from
`tube_psu_5_2.kicad_dru`, `ALLOW` in `check_domains.py` is empty (0 accepted pairs before and after; `check_rules.py`
had no test of it, 34 / 34 as before).

**Turn-off branch D30 / R53 of Q19: not placed** (parts still at (40.5, -49.5) / (41.5, -46.7), 2 unconnected items).
Tried on paper against the dump of the board, with C92 / R26 / R22 free to move; the limits on B.Cu are:
* West of the pins (x 8.2 – 11.55 between the driver pins and the gate pad): C92 and R26 fill it; north of pin 16 every
  primary pad must stay 4.95 mm from the centre of H4 (ring 1.75 + creepage 3.2), i.e. y <= -43.9 at x 9.0 and
  y <= -41.8 at x 10.5; south of pin 14 the NC pins and pin 11 (15V, 1.2 mm) leave x 8.5 – 10.0, y -50.3 ... -48.6.
* East of the pins: the +1V65_BIAS via (14.6, -44.076) and the PRI_DHB_HI via (19.0, -45.0) each keep group copper
  1.45 mm from their centre, the DC+ pad of C70 starts at x 17.65 (y <= -46.65), R41 pin 2 (VDDA) ends at y -43.03,
  the gate track runs on y -46.98. What is left is a band y -46.6 ... -45.6 (1.0 mm high), x 13.95 – 16.45 (2.5 mm): D30
  (SOD-323, 3.6 mm over the pads) does not fit; R53 (0805, 3.2 mm over the pads, 1.4 mm high) does not fit either.
* With R26 turned (gate-driver end north) R53 fits upright north of the gate pad at (12.5, -44.2) (1.25 mm from the bias
  via, 0.25 mm from R26), but D30 then has to lie between R53 pin 1 and the H4 circle / the VDDA track on y -42.15: no
  3.6 mm there.
* Not checked on the board (only by this geometry): an 0603 R53 + SOD-523 D30 (1.9 mm over the pads) in the east band, the
  DHB_HI_GATE track 0.25 mm on y -45.7 past the gate pad (0.2 mm) with R26 turned; or moving the +1V65_BIAS via
  (14.6, -44.076) / R41 by 1.5 mm, which opens x 14 – 17.5, y -46.6 ... -43.3 for the two parts as they are.
The gate loop is unchanged (out about 9.0 mm, return about 8.8 mm).

## Stage 4l: DC+ neck at SICD1 widened, turn-off branch D30 / R53 of Q19 placed (2026-11-22)

`tools/next/route_s4l_neck_toff.py` (incremental, step A plain run, step B `--stepB`; neither re-runnable;
`routing/moves_s4l.json`, `deleted_s4l.json`, `s4l_added.json`). Step A: unconnected 22 -> 22, clearance markers
6 -> 6, 0 shorts.

**What the neck carries.** The PFC is a bridgeless dual boost: DB1 is on AC1 / AC2 with pin 2 on DC+ and pin 4 on GND
(DB1 + is DC+ itself, not a rectified-mains net; the upper diodes only carry inrush / bypass current, the lower ones the
line-frequency return). On the peninsula side of the neck are DB1 pin 2, C73 pin 1 (2.2 µF DC+ - GND) and the cathode of
SICD2 (strip x 5.4 – 7.9); on the trunk side SICD1 K, the bulk capacitors C56 / C28 / C37 / C29 and everything else on
DC+. There is no other DC+ copper between the two sides (no DC+ via or track in the area before this stage), so the neck
carried the whole boost-diode current of the PFC_DRAIN_2 phase (L1 / Q6 / SICD2) to the bulk capacitors, plus the
inrush pulse of DB1; C73 only takes the HF part.

**Measured** (amap of the refilled copper, 0.1 mm grid): before, F.Cu only, 0.75 – 0.8 mm (y -18.3 ... -19.1 at
x 12.0 – 13.0). After:
* F.Cu about 1.25 mm (throat between (13.2, -17.9) and the corner (12.7, -19.05) of the 1.2 mm zone of the anode pad):
  GND pour 30 cut back to the pad edge of C73 pin 2 (south edge y -17.1 -> -16.7, south-west corner chamfered
  (13.2, -16.3) - (13.6, -16.7)); pad 2 of C73 and all 15 GND vias stay in the pour. Hard limit on F.Cu is the pad of
  C73 (1.2 mm) against the anode pad of SICD1: at most about 1.5 mm.
* B.Cu 1.0 mm track (10.2, -18.65) - (13.6, -18.65) - (14.7, -19.75) - (14.7, -22.1), 1.2 mm from the B.Cu GND tracks of
  the C73 vias and 1.25 mm from the anode pad (B.Cu had no copper there; GND pour 24 gives way by the 1.2 mm rule).
* In3 zone `S4L_DC+_In3_neck` (x 9.7 – 15.1, y -22.7 ... -16.9, priority above the +3V3 plane, which gives way from
  x 15.0 to 15.6 along 4 mm): 2.9 mm wide north of the anode pad, 2.2 mm at the turn round the pad corner (0.5 mm from
  the pad), 0.5 oz.
* Vias 0.8 / 0.4: four in the peninsula ((10.2 / 11.3, -17.5 / -18.55)), three in the trunk ((14.7, -19.9 / -21.0 /
  -22.1), 1.5 mm from the anode pad).
Sum 1.25 + 1.0 + 2.2 = 4.45 mm of copper width, about 3.3 mm counted as 1 oz (In3 is 0.5 oz). SICD1 not moved; pour 10
(anode lobe) not changed (its edge is 0.1 mm outside the pad; the pad is the limit).

### Stage 4l step B: turn-off branch D30 / R53

`route_s4l_neck_toff.py --stepB`. Unconnected 22 -> 20 (DHB_HI_GATE at D30, Net-(Q19-G) at R53), clearance markers
6 -> 6, 0 shorts, dangling 30 -> 30. Footprints unchanged (SOD-323, 0805). All parts on B.Cu:

| part | from | to | why |
|---|---|---|---|
| +1V65_BIAS via 0.5 / 0.3 | (14.6, -44.076) | (13.0, -44.076) | west along its own In2 lane (between SYNCH_2 and $HT_CS, 0.164 mm as before); In2 lane 1.6 mm longer, In3 lane 1.6 mm shorter. Its F.Cu antipad now lies in the antipad of the gate pad: the DC+ pour north-east of the pins is 1.25 mm wider |
| R41 | (18.0, -42.15) rot 180 | (13.0, -42.05) rot 180 | the via between its pads (1.21 mm to each pad), VDDA pad on the old diagonal to C92; Net-(D19-K) 0.5 mm track on y -41.6 to D19 (6.5 mm, 1.39 mm from the 15V track on y -39.58). R41 cannot go north (15V track) or east (D19) |
| R26 | (10.85, -46.0) rot -90 | same place, rot 90 | DHB_HI_GATE end north, gate end 0.2 mm beside the gate pad |
| D30 | (40.548, -49.486) rot 0 | (15.0, -44.98) rot -90 | cathode south (15.0, -46.28), anode north |
| R53 | (41.534, -46.708) rot -90 | (16.4, -43.95) rot 90 | pin 1 north beside the anode, pin 2 (gate) south; 1.23 mm from the DC+ pad of C70, 1.65 mm from the PRI_DHB_HI via |

* DHB_HI_GATE: pin 15 -> y -46.725 -> between C92 pin 2 and the gate pad of R26 -> R26 pin 1 (0.4 mm); from there 0.25 mm
  on y -45.69 north of the gate pad (0.21 mm) and south of the bias via (1.24 mm) to the cathode of D30.
* Gate track to R22 moved from y -46.98 to y -47.2 (1.22 mm from the DC+ pad of Q19); R53 pin 2 joins it on x 16.2
  (1.3 mm from the DC+ pad of C70).
* Lengths (centre lines): turn-on pin 15 -> R26 -> gate pad about 8.7 mm (was 9.0), return unchanged about 8.8 mm.
  Turn-off branch gate pad -> gate track -> R53 -> D30 -> R26 pin 1 about 16.7 mm (21.5 mm to pin 15).
* DC+ pour at Q19 pin 2 unchanged (about 1.0 mm high at the east edge of the pad, limited by the gate pad; 4.5 mm high
  from x 15.0).
* New courtyard overlap R41 / D30 (0.375 mm between the pads); the old leftover track of Net-(D30-PadA) at
  (41.5, -49.2 ... -47.7) is deleted.

## Stage 5a: small signal nets closed (2026-11-22)

`tools/next/route_s5a_signals.py --group pwm2,p3v3` and `--group hc` (incremental, not re-runnable;
`routing/moves_s5a.json` (empty), `deleted_s5a.json`, `s5a_added.json`). Unconnected 20 -> 12, clearance markers
6 -> 6 (the same six), 0 shorts. No part moved. Aim of this stage: every connection made and rule-clean, not optimised.

* **Net-(PWM2-VERR)**: R138 pad 2 - R139 pad 1 on B.Cu, 0.2 mm, y -1.82 between the GND pads of R139 and C15 (3.5 mm).
* **Net-(PWM2-FB)**: R140 pad 1 - C139 pad 1 on B.Cu (2.9 mm); via 0.6 / 0.3 at (49.38, -0.745) in the edge of C139
  pad 1; F.Cu 0.2 mm under the body of PWM2 (x 49.38 north, y 2.4 north of the GND via (50.1, 1.605), down to pin 3;
  7.3 mm). The FLY_C pours on F.Cu / B.Cu give way by the 1.2 mm rule beside the via and the tracks.
* **Net-(PWM2-VIN)**: R153 pad 2 on B.Cu east on y 10.6, diagonal to x 55.15 (1.27 mm from TR1 pin 12, FLY_C), south
  east of C51 to a via 0.6 / 0.3 at (55.15, 3.7) (1.27 mm from the B.Cu DC+ track of C15); F.Cu on x 55.15 to pin 1
  from the east. B.Cu 13.3 mm, F.Cu 4.5 mm. The crossing of the F.Cu FLY_C pour (y 7 ... 10.25) is on B.Cu.
* **Net-(D10-PadA)**: via 0.5 / 0.3 at (36.8, 3.2), in the anode pad of D10 (F.Cu) and in pad 2 of R142 (B.Cu). The
  anode pad is closed in on F.Cu (+3V3 west, 15V on the other three sides) and the In2 lanes of AUX_MEAS (x 36.53)
  and 5V_MEAS (x 37.4) were 0.72 mm apart under it, so the AUX_MEAS lane now runs at x 36.2 under the pad
  ((35.0, 3.879) - (36.2, 2.679) - (36.2, 1.93) - its via (36.53, 1.6)).
* **+3V3** (both items): C125 pad 1 -> B.Cu 1.3 mm -> via (0.8, -60.2) -> In3 0.25 mm on y -59.8 to the kept via
  (5.8, -60.1) of the U1 block (5.3 mm), and In3 on y -59.4 / diagonal / x -12.5 (18.1 mm) to a new via (-12.5, -52.6)
  on the In2 bus lane y -52.8. In3 has no pour there (the 15V plane starts at y -60.55). The +3V3 lane is the second
  lane of the bundle, so the outer lane GPIO_BYPASS_RLY (y -52.3) steps to y -51.9 from x -13.4 to -11.7 round the
  via; the via is west of the B.Cu 15V track (x -11.6) and 2.3 mm from the F.Cu DC+ pour.
* **HEATER_CURRENT**: the open item was a 0.3 mm In2 stub at R30 pad 1 (under the gate pad of Q11, joined to
  nothing); deleted.

Not closed in this stage:

* **TX / RX** to U11 pins 4 / 5: not started (findings of stage 3g still apply; In3 not tried).
* **Net-(Q9-D)** Q9 pad 1 - D9 anode: the B.Cu track of GPIO_BYPASS_RLY (x -60.15, y -31 ... -38.1, and its diagonal
  north-west) runs between the two pads; F.Cu above is the Net-(RL1-COM) pour (mains), so no via pair there. Way
  out: round the south end of the GPIO track (y -38.1) or GPIO_BYPASS_RLY onto In2 earlier.
* **Net-(C131-Pad2)** C131 pad 2 - R82 pad 2: on B.Cu R82 pad 2 is fenced by Net-(U6-+) (x 21.3, y 4.865) and
  Net-(U6--) (x 20.7); the way north of R17 needs y >= 7.2 (GND pad of R17) and y <= 6.97 (1.2 mm from the DC+ pad
  at y 8.25). Needs a via pair or the south end of the kept track (22.1, -0.365).
* **Net-(R51-Pad2)**: In2 track end (29.2, 16.5) to R51 pad 2 (5.3, 6.5), 24 mm apart, HV_PRIMARY; not looked at.

## Stage 5b: local connections closed (2026-11-22)

`tools/next/route_s5b_local.py --group u9`, `drv2`, `dt`, `c131`, `q9d`, `r51,gnd21,d32` (incremental, not
re-runnable; `routing/moves_s5b.json`, `deleted_s5b.json`, `s5b_added.json`). Unconnected 12 -> 3, clearance markers
6 -> 5, 0 shorts. One part moved (R131). Aim as in stage 5a: every connection made and rule-clean, not optimised.

* **Net-(U9--) / Net-(U9-+)** (B.Cu): the +1V65_BIAS lane x 27.9 ran between R131 and U9 pin 4. R131 turned and moved
  0.9 mm ((26.82, -22.94) rot -90 -> (27.65, -23.3) rot 180): pad 2 west of the lane (joined to it), pad 1 east,
  straight north of pin 4. The lane via (27.9, -26.4) is 0.25 mm further north (27.9, -26.15) (In2 lane and F.Cu link
  lengthened) so pin 1 - pin 4 passes on y -26.7 under the body. U9-+: pin 3 east, x 29.5 north, y -25.8 north of the
  second +1V65_BIAS via (31.1, -26.4), x 31.75 south to R3 pad 1; the +3V3 lane there steps south 1.6 mm further east.
* **Net-(DRV2-OUTH)**: pin 2 was closed in by the B.Cu 15V link pin 1 - via (14.06, 10.6). The link is on F.Cu now
  (new via (13.2, 8.75) in the edge of pin 1, 0.4 mm), OUTH leaves south-east and runs on x 14.737 to R20 pad 1
  (B.Cu, 0.3 mm, 6.2 mm).
* **Net-(DRV6-DT)**: via (66.95, -55.1) east of pin 6, F.Cu 0.2 mm on x 66.95, via (66.9, -49.3) in R128 pad 1. The gap
  between the 5V_ISOL via and TR3 pin 9 (TRANS_SEC, 1.2 mm) was 0.02 mm short, so that via moved 0.25 mm south-west
  along its In2 diagonal to (66.3, -51.675). B.Cu under DRV6 is taken by DHB_HI_GATE_SEC, In2 by the DAB_DIS_SEC and
  5V_ISOL diagonals, In3 by the 15V_ISO_SEC plane.
* **Net-(C131-Pad2)** (output of U6, B.Cu 0.152 mm, 13 mm): the Net-(U6-+) link R10 pad 2 - R17 pad 1 drops to y 5.1
  west of R17; the output runs on y 6.7 (1.4 mm south of the DC+ pad of C29), through the gap between the pads of
  R17 (y 5.7), between the pads of C130 (y 5.44), east of C130 (x 23.85) and west on y 3.7 to R82 pad 2.
* **Net-(Q9-D)**: via (-62.4, -31.9) under Q9 (west of the F.Cu Net-(RL1-COM) pour), In3 0.25 mm diagonal to the
  through-hole pin 5 of RL1 (7.7 mm; In3 has no pour and no other track there). On B.Cu both GPIO_BYPASS_RLY
  (x -60.15, then east on y -39.4) and 5V (x -59.7) run between Q9 and D9.
* **Net-(R51-Pad2)** (HV_PRIMARY): In2 0.152 mm from the lane end (11.578, 16.478) on x 9.7 between the Net-(R48-Pad2)
  lane (x 8.6) and the PFC_PWM2 lane (x 10.594), diagonal 0.54 mm from the R48 via to a via (5.6, 6.3) in the corner
  of R51 pad 2 (1.2 mm from R51 pad 1 and R48 pad 2).
* **GND pour 'Proteus B.Cu pour 21'**: one via to the GND planes in each island, (42.1, -29.6) and (35.3, -27.5).
* **D32 clearance marker**: the last 0.14 mm segment of the DHB_LOW_GATE_SEC track (inside the D32 cathode pad,
  1.15 mm from R149 pad 2) deleted.

Not closed in this stage:

* **TX / RX** to U11 pins 4 / 5: not started (next block).
* **DHB_LOW_GATE_SEC** DRV6 pin 10 - D32 / R87 (Q8 gate network): pin 10 is on the west pin row. B.Cu: closed in by
  the high-side group (DHB_HI_GATE_SEC under the body of DRV6, D31 / R57 / R58, the DHB_HI_SOURCE_SEC pour y -46).
  F.Cu: the DHB_HI_SOURCE_SEC track (x 54.75 ... 56.5 over the pin row, y -49 ... -50 east). In2: the DAB_DIS_SEC lane
  (via (64.157, -56.272) - x 65.657 - diagonal to (74.657, -42.372)), the 5V_ISOL diagonal / y -48 lane and the
  ISO_SEC_DHB_LO / HI diagonals (crossing y -59 near x 73); the target (73.81, -47.72) lies in the wedge between the
  DAB_DIS_SEC diagonal and the 5V_ISOL lane. In3: 15V_ISO_SEC plane. A via east of pin 10 at about (58.3, -53.83)
  fits on all layers (not placed); the In2 lanes of DAB_DIS_SEC / 5V_ISOL have to be re-drawn first.

## Stage 5c: the last three connections closed (2026-11-22)

`tools/next/route_s5c_last.py --group lowgate` and `--group uart` (incremental, not re-runnable;
`routing/moves_s5c.json` (empty), `deleted_s5c.json`, `s5c_added.json`). Unconnected 3 -> 0, clearance markers 5 -> 5
(the same five), 0 shorts. No part moved, no zone outline changed. Aim as in stage 5a: every connection made and
rule-clean, not optimised.

* **DHB_LOW_GATE_SEC** (DRV6 pin 10 - D32 cathode / R87): B.Cu 0.3 mm from the pin to a via 0.6 / 0.3 at
  (58.3, -53.832) (1.5 mm east of the F.Cu DHB_HI_SOURCE_SEC track), **In3 0.3 mm, 17.2 mm, inside the 15V_ISO_SEC
  plane**: y -54.1 between TR3 pins 9 and 10 (0.95 mm from the pad of pin 9), diagonal to x 72.5, via (72.5, -50.3)
  (1.2 mm rule to the 420V pad of C16 on F.Cu kept), B.Cu 2.4 mm into the west edge of the D32 cathode pad (1.3 mm
  from R149 pad 2). No In2 lane re-drawn, no rule area: the plane fill gives way round the lane (slot about 0.7 mm
  wide, 14 mm long); the plane is still one outline (531 -> 518 mm2) and the DRC lists no 15V_ISO_SEC item.
  Return in the ISO_GND planes In1 / In4.
* **UART TX / RX** (J2 pins 26 / 24 - U11 pins 4 / 5; 0.152 mm, pitch 0.34 mm on In3, RX the north / west lane):
  * B.Cu from the 5.1 ends (40.6, -19.5) / (40.1, -19.503) south-east (the 5.1 RX stub to (48.66, -28.063) cut back),
    then south on x 46.1 / 45.3 to vias 0.5 / 0.3 at (46.1, -28.1) (TX) and (45.3, -27.55) (RX), south of the In2
    +3V3 lane y -26.87.
  * In3 82 mm, nowhere through a pour of another net: gap between the 5V and 15V planes (y -27.2 / -27.54), diagonal
    to the corridor y -32.53 / -32.87 between the +3V3 plane and the 15V band (x 35 ... 15), y -31.68 / -32.02 past the
    vias of Net-(DRV1-OUTL) / PFC_PWM1 (x 9.4 / 10.4), diagonal to y -34.58 / -34.92 **between the two pads of L2**
    (1.40 mm from the AC1 pad, 1.46 mm from the PFC_DRAIN_1 pad; more than 7 mm from H4), south on x -8.52 / -8.18
    west of the DRV5 input parts and under the In2 control bus, diagonals to vias 0.5 / 0.3 at (-5.75, -57.5) (RX)
    and (-5.0, -57.5) (TX) south of the bus (5V lane y -56.75). The F.Cu DC+ pour gives way round the two vias
    (1.2 mm); it stays in one piece.
  * B.Cu south on x -5.55 (RX) / -5.2 (TX) between the 15V track (x -6.75) and the +3V3 track of stage 3g (x -4.68),
    east of the GND via of pin 7 (-6.15, -74.83; 0.22 mm), to vias (-6.15, -77.365) / (-6.15, -78.635), F.Cu 0.2 mm,
    1.5 mm to pins 5 / 4. TX copper edge x -5.12: 0.75 mm outside the UART island keep-out (x -4.375), 8.75 mm from
    the island-side pads of U11 (x 3.625).
  * Lengths from the 5.1 ends: RX 113 mm, TX 116 mm, three via pairs.

Open: nothing in the unconnected list. Not looked at in this stage (first complete draft): the UART pair runs on In3
between the pads of the PFC inductor L2 and 82 mm beside / under power stages (GND plane In1 above, In4 below);
the low-side gate lane of DRV6 is 17 mm on an inner layer.

## Footprints and 3D models (phase 3, 2026-11-18)

Regenerate: `python3 tools/next/gen_next_footprints.py`, `tools/p2k/bin/kicad_env.sh python3
tools/next/gen_next_footprints_parts.py`, then (CadQuery: `python3 -m venv ~/.venvs/cq && ~/.venvs/cq/bin/pip
install cadquery`) `~/.venvs/cq/bin/python tools/next/gen_next_3d.py`; edit the footprint map
`lib/footprint_map_next.csv` (and the footprint column of `lib/jlc_parts_next.csv`), `python3
tools/next/gen_schematic.py`, `python3 tools/next/netlist_diff.py --update`. Drawings: `tools/p2k/bin/kipy
tools/next/check_footprints.py --dump reports/next/footprints.json && python3 tools/next/render_footprints.py
reports/next/footprints.json reports/next/footprints/`.

**Audit against the ordered parts** (JLC API package string of every LCSC number in `lib/jlc_parts_next.csv`,
2026-11-18): all 98 LCSC numbers match their footprint's package / pin count / pitch – UCC21520DWR, CA-IS3761LW,
CA-IS3721HW SOIC-16-300mil = SOIC-16W (all 16 leads present; UCC21520 pins 7 / 12 / 13 are NC and keep their
pads), IPD60R280P7S TO-252-3 = KiCad TO-252-2 (1 G, 2 D tab, 3 S), 1210 630 V, US1M / ES1D SMA (not SMAF),
XC6206 SOT-23-3L (1 GND, 2 VOUT, 3 VIN), TLV9062 VSSOP-8, ICE5AR DIP-7 = DIP-8-N6 (pin 6 absent; replaced 2026-11-19 by the ICE5AR0680AG PG-DSO-12, see the table below – its JLC package string "BSOP-12-EP-300mil" is wrong), electrolytics
D × L / pitch (C102 10×18 P5, C19/C30 10×50 P5, C28/29/37/56 12.5×45 P5, C31/32 8×20 P3.5, C58 5×5.4 SMD), FTDI
header 1×6 2.54. LMH6643 (VSSOP-8) stays on the 5.1 `TSSOP-8_3x3mm_P0.65mm` (same 3 × 3 body / pitch; pads
1.1 mm vs 1.6 mm long – fine for reflow, user-accepted). **Fixed:** L1 / L2 had no footprint; ISO1 / ISO2 / U11 had
no slot; 3D: the 5.1 KRL2012 shunt model path does not exist in KiCad 10, six 5.1 footprints had no model (DB1,
CM1/CM4, RL1, the 12 blade terminals, TR2), the transformers had none, and the KiCad CP_Radial models are 8 /
10 / 12.5 mm tall against 18–50 mm parts. No UCC21520 crosses a barrier: DRV5 (input 5V / GND, A = DAB primary
high side, B = GND), DRV3 (input 5V / GND, A = heater bridge high side, B = GND) and DRV6 (input 5V_ISOL /
ISO_GND, both outputs secondary) are each in one domain (`check_footprints.py` asserts that exactly the
`setup_project.py` BARRIERS parts – plus the Y caps to PE – have pins in two domains).

| Part(s) | Footprint | What |
|---|---|---|
| L1, L2 | `tube_psu_next:L_Toroid_D31.5mm_W16.7mm_Vertical_RM8_45deg` (L1) / `…_315deg` (L2) | **Upright** toroid (on edge, ring plane along x = the board's long axis), as the chokes are mounted on the built 5.1 board (user decision and photo 2026-11-19). Pads 1 / 2 (Ø 1.3 / 2.6 mm, 0.8 mm wire) = the RM8 winding holes pri1 / pri2 of `tube_psu:L_RM8_Proteus` (8.42 mm apart on a diagonal); the 5.1 RM8s sit at +45° (L1) / −45° (L2), so there is one footprint per RM8 rotation with origin = the 5.1 RM8 origin, placed at **0°** on the 5.1 RM8 position (pads land on the 5.1 holes and keep their tracks). Body 31.5 × 16.7 mm, centre (−12, ±8) mm from the pad midpoint (`TOROID_V` body_dx / body_dy): the toroid's +x end stops at the PFC heatsink / H7 standoff and the body sits on the outer side of the pad pair (L1 towards the bottom board edge, L2 towards −y), read off the photo – **±3 mm, confirm on the built board**. L1's courtyard ends 1.0 mm inside the board edge (no overhang: in the photo the left toroid is flush with the edge, the top only appears to overhang by perspective). Courtyard body + 1.0 mm (33.5 × 18.7) plus a tab over the pad outside the body. 3D: ring standing on the board (31.5 high) with the two leads. The flat-lying `L_Toroid_D31.5mm_H16.7mm_Flat_P16.7mm` (+ `_TieSlots`) stays in the library, unused |
| ISO1, U11 | `tube_psu_next_parts:SOIC-16W_7.5x10.3mm_P1.27mm_Slot8.0` | KiCad SOIC-16W + 1.0 × 14.5 mm milled slot (Edge.Cuts) on the body axis: surface path **8.85 mm** ≥ 8.0 (primary ↔ heater / UART); pad rows alone 7.25 mm |
| ISO2 | `…_Slot11.1` | 1.0 × 19.5 mm slot: **12.50 mm** ≥ 11.1 (primary ↔ DAB secondary) |
| TR1 | `Transformer_EEL19_V_4+6_FlyLeads` | slot 1.2 × **28 mm** (y −10 … +18); **fly-lead holes moved 1.5 mm down to y 15.5** and the barrier pads without unused inner-layer rings (`remove_unused_layers`): the inner layers get no slot credit (11.1 mm straight-line rule) and FL_DC's barrel was 10.1 mm from pin 5's (now 11.2 mm). Surface path **12.86 mm** (supersedes the 13.18 mm of EEL19_DESIGN.md 12.6, which used exact circles and the old hole position) |
| TR3 | `Transformer_EC42x15_2Slot_2x8_P5mm` | PCB creepage pin row ↔ row 37.6 mm – no slot. Added a **12 mm barrier keep-out** (rule area: no tracks / vias / pours on all six layers) under the divider (x −7 … +5). The core counts as primary and sits over the pin rows: secondary pin wraps ↔ core is a transformer item (3 tape layers on the secondary core plate or a core cap, DAB_TRANSFORMER.md 8) – Fab note in the footprint |
| TR2 | (5.1 EF25, copied) | heater barrier 10.37 mm ≥ 8.0 – no slot |
| heatsink | `tube_psu_next:Heatsink_Plate_Keepout_L120mm` | outline helper only: the 5.1 board has no bracket holes or pads (only H1–H8; H4 sits beside the TO row), so the plate footprint (120 × 3 mm, parameters in `HEATSINK`) with 4.0 mm / 11.1 mm keep-off lines to secondary copper (plate = primary / earthed); board-only, no BOM / CPL. Bracket feet and holes come out of the placement |
| C19/C30, C102, C29, C28/C37/C56, C31/C32 | `tube_psu_next_parts:CP_Radial_…_H50mm / _H18mm / _H45mm / _Proteus_H45mm / D8 _H20mm` | library pads, 3D model with the real height |
| DB1, CM1/CM4, R21/R30/R83/R93, RL1, terminals, TR2 | `tube_psu_next_parts:<5.1 name>` | 5.1 pads unchanged, 3D model added |
| PWM2 | `tube_psu_next_parts:PG-DSO-12_3.9x9.9mm_P1.27mm` | ICE5AR0680AG (2026-11-19): KiCad SOIC-16 narrow with SO-16 pads 5, 6, 11, 12 removed, renumbered 1–12 (datasheet figure 39: e 1.27, b1 3.81 mm = pin 4 → 5); DRAIN 5–8 ↔ CS 4 / NC 9 copper gap 3.21 mm; stock SOIC-16 3D model (16 leads drawn) |

**3D models:** every used footprint has a model that resolves (KiCad library models via
`${KICAD10_3DMODEL_DIR}` in the 10.0.7 AppImage; own models via `${KIPRJMOD}/../lib/tube_psu_next.3dshapes/`).
Own STEP models (boxes / cylinders, outer dimensions only): EEL19 20 × 23 × 29.2, EC42 46 × 42 × 31.5 (winding
Ø 30, core depth 15 assumed), toroid Ø 31.5 / 13 × 16.7 (flat and upright), electrolytics, blade terminal (6.3 mm tab, 9 mm),
TBS bridge (height 2.6 assumed), SCF20 choke 15.5 × 25 × 25 (KEMET max), Songle relay 15.3 high, EF25 (22 mm
assumed), KRL2012 shunt, heatsink plate (30 mm assumed). Tallest parts: C19/C30 50 mm, C28/29/37/56 45 mm,
TR3 31.5, TR1 29.2, R27 26 (library model), TO-247 25.4, CM1/CM4 25. R27 (TWW10, no LCSC) keeps the KiCad
`R_Radial_Power_L13.0mm_W9.0mm_P5.00mm` model.

**Still to confirm with calipers** (then change the generator constants and rerun): EEL19 4+6 bobbin base
outline (15.8 × 22.5 is 5+5 data), pin diameter (drills 1.0 / 0.9 mm), seated height and the real base
creepage between the rows; EC42 set: pin diameter (drill 1.2), base 46 × 40, core depth, seated height and
the core-plate height above the board at the secondary pins (≥ 4.0 mm clearance or tape); toroids L1 / L2: body
position relative to the RM8 holes on the built board (photo estimate ±3 mm), OD / width with the winding; EF25
(TR2) height; TBS bridge height; heatsink plate size from the placement.

## Stackup (D5) – JLC06161H-7628D, 6 layers, 1.6 mm, 1 oz outer / 0.5 oz inner

User decision 2026-11-23 (was JLC06161H-3313: one 0.0994 mm 3313 ply under the outer layers, 0.55 mm cores,
0.1088 mm 2116 between In2 / In3). Reason: the 400 V DC+ copper on F.Cu / B.Cu lies over the In1 / In4 GND planes;
7628D puts two plies of 7628 (0.428 mm) there instead of one thin ply - about 0.9 kV/mm instead of 4 kV/mm, and no
single-ply defect path. Thicknesses from the "Layer Stackup" table of JLC's order form (read by the user,
2026-11-23). **Special stackup: JLC does not offer economic PCB assembly with it** (standard assembly only).
Solder-mask 0.6 mil over copper, Dk 3.8, 7628 Dk 4.4 (JLC calculator guide); core Dk 4.6 and laminate Nan Ya
NP-155F are carried over from the 3313 table (not re-read for this stackup). Loss tangent 0.02 is a generic FR-4
figure. Finished thickness 1.6 mm nominal (the layers below sum to 1.590 mm + mask). Surface finish ENIG; vias
epoxy-filled and capped by default.

| # | Layer | KiCad name / type | Use | Thickness | Dk |
|---|---|---|---|---|---|
| | F.Mask | – | LPI mask | 0.015 | 3.8 |
| L1 | F.Cu | F.Cu, signal | parts + power copper, signals | 0.035 (1 oz) | |
| | prepreg 7628 ×2 (0.218 + 0.2104) | dielectric 1 | | 0.4284 | 4.4 |
| L2 | In1.Cu | In1.GND, power | GND planes, one per domain | 0.0152 (0.5 oz) | |
| | core | dielectric 2 | | 0.2 | 4.6 |
| L3 | In2.Cu | In2.Signal_HV, signal | signals / HV routing | 0.0152 | |
| | prepreg 7628 ×1 | dielectric 3 | | 0.2028 | 4.4 |
| L4 | In3.Cu | In3.Power, mixed | power pours (15V, +3V3, …), signal lanes; no DC+ (stage 9) | 0.0152 | |
| | core | dielectric 4 | | 0.2 | 4.6 |
| L5 | In4.Cu | In4.GND, power | GND planes, one per domain | 0.0152 | |
| | prepreg 7628 ×2 (0.2104 + 0.218) | dielectric 5 | | 0.4284 | 4.4 |
| L6 | B.Cu | B.Cu, signal | bottom parts + signals | 0.035 (1 oz) | |
| | B.Mask | – | LPI mask | 0.015 | 3.8 |

Consequences against 3313: outer copper is 4.3 times further from its plane (higher inductance of loops that
return through the plane, about 4 times less plane capacitance; not calculated - the DAB gate and power loops run
side by side on one layer); In2 HV routing is 0.2 mm of core from In1 (was 0.55 mm) and 0.2 mm of prepreg from In3
(was 0.11 mm). Distances between isolation domains are checked in plan view and do not depend on the stackup.
Text of the earlier stages in this file quotes the 3313 thicknesses (0.0994 / 0.1088 / 0.55 mm) as they were then.

## JLC manufacturing limits (jlcpcb.com/capabilities/pcb-capabilities, multilayer, read 2026-11-17)

| Item | JLC | Used | Where |
|---|---|---|---|
| track / space (1 oz outer) | 0.09 / 0.09 mm | 0.10 / 0.10 | kicad_pro minimums |
| via drill / diameter | 0.15 / 0.25 mm | same (annular 0.05) | kicad_pro |
| min drill | 0.15 mm | 0.15 | kicad_pro |
| PTH annular ring | 0.15 min (0.20 recommended) | 0.15 | `.kicad_dru` rule |
| NPTH min | 0.50 mm | 0.50 | `.kicad_dru` |
| hole-to-hole: pads (different nets) / vias | 0.45 / 0.20 mm | 0.45 / 0.20 | `.kicad_dru` / kicad_pro |
| hole to copper | – (not listed) | 0.20 | kicad_pro (assumption) |
| copper to routed edge | ≥ 0.20 mm | 0.30 | kicad_pro |
| silk line / text height | 0.15 / 1.0 mm | 0.15 / 1.0 | kicad_pro |
| inner 0.5 oz track / space | not listed | as outer | – |

Net classes (clearance / track / via; mm): Default and SIGNAL 0.15 / 0.2 / 0.6-0.3, PRIMARY_LV 0.2 (inner layers 0.15 to
PRIMARY_LV / SIGNAL nets, `.kicad_dru` rule of routing stage 3d) / 0.5,
SECONDARY_LV 0.2 / 0.3, HEATER 0.2 / 1.0, UART_ISO 0.15 / 0.2, HV_PRIMARY and HV_SECONDARY 0.5 / 1.0 / 1.0-0.5
(inner-layer functional spacing for ≤ 500 V; outer layers 1.2 mm by rule), PE_EARTH 0.5 / 1.5. Widths are
starting values; phase 6 sizes the power paths from the currents (D5 copper).

## Isolation domains and creepage / clearance (D6)

Domains are found from the schematic by `setup_project.py` (flood fill from GND / ISO_GND / HT_GND, not
through the barrier parts TR1, TR2, TR3, ISO1, ISO2; no other part bridges two domains in the 5.1
netlist). Count after phase 2: primary 156 nets (HV_PRIMARY 43, PRIMARY_LV 5, SIGNAL 108; after the ICE5AR0680AG change and NR 2.8; since routing stage 3c 158 nets: HV_PRIMARY 43, PRIMARY_LV 5, SIGNAL 110), DAB secondary 42
(HV_SECONDARY 14, SECONDARY_LV 28), heater 22, UART island 12 (ground ISO_UART_GND, barrier U11), PE 1.

### Basis

- IEC 62368-1 (insulation clauses 5.4) with the tables shared with IEC 60664-1: creepage = IEC 60664-1
  Table F.5 (Ed. 2: F.4) = IEC 62368-1 Table 17 for basic insulation, **PD2, material group III** (FR-4 with
  CTI ≥ 175 is IIIa; IIIa and IIIb share one column at PD2, so the choice between them does not change
  the number), linear interpolation allowed; **reinforced = 2 × basic** creepage. Anchor rows used
  (MG III, PD2): 250 V 2.5 mm, 320 V 3.2 mm, 400 V 4.0 mm, 500 V 5.0 mm, 630 V 6.3 mm, 800 V 8.0 mm,
  1000 V 10.0 mm (400 / 800 / 1000 V confirmed in TI SLUP421 p. 17; the others are the R10 rows of the same
  table – check against the standard).
- Clearance: mains 230 V + 10 %, **OVC II → 2500 V** transient (IEC 60664-1 Table F.1). IEC 60664-1 Table
  F.2 (case A, PD2): 1.5 kV 0.5 mm, 2.5 kV 1.5 mm, 4.0 kV 3.0 mm; reinforced = one impulse step higher
  (5.1.6) → 2.5 kV → 4 kV → **3.0 mm**. IEC 62368-1 Table 10 gives larger basic values (1.8 mm at 2.5 kV,
  3.8 mm at 4 kV per TI SLUP421), so **4.0 mm** is used for every reinforced primary barrier. The peak
  working voltages (≤ 0.9 kV) need less than the transient value. Altitude ≤ 2000 m: factor 1.0 (Table A.2).
- Working voltage = rms (creepage) / peak (clearance) between any two points of the two domains, with the
  mains-referenced primary: GND = negative bridge output, which follows the negative mains half-wave,
  i.e. GND(t) = min(0, v_mains), v̂ = 253 V·√2 = 358 V; DC+ = GND + 400 V.
- Inner layers: KiCad cannot check distance through insulation, and the JLC laminate has no
  cemented-joint qualification, so **no reduction is claimed**: inner-layer spacing between domains =
  the outer creepage value (conservative; the barrier width is set by the outer creepage anyway).
  Layer to layer: IEC 62368-1 reinforced solid insulation needs ≥ 0.4 mm (or a qualified thin-sheet
  build – **verify the clause** in the edition used); with JLC06161H-7628D (2026-11-23) the cores are 0.2 mm,
  L3–L4 is one 0.2028 mm 7628 ply, and L1–L2 / L5–L6 are two 7628 plies (0.428 mm, not a qualified build)
  → **copper of two domains must never overlap on any pair of layers** (no layer pair is relied on). Phase 5/6: barrier keep-out on all six layers.

### Working voltages and numbers

| Barrier | Grade | Working voltage (assumption) | Creepage | Clearance | Inner layers |
|---|---|---|---|---|---|
| Primary ↔ DAB secondary (TR3, TR1, ISO2, heatsink) | reinforced | 420V rail vs GND: 420 + 358·\|sin\| in the negative half-wave → **552 Vrms, 778 Vpk** (ISO_GND earthed through the amplifier chassis) | 2 × 5.52 = **11.1 mm** | **4.0 mm** | 11.1 mm |
| Primary ↔ heater (TR2, ISO1) | reinforced | DC+ vs HT_GND (earthed, or at the −100 V bias): **318–333 Vrms, ≤ 500 Vpk** | 2 × 3.33 = 6.7 → **8.0 mm** | **4.0 mm** | 8.0 mm |
| Primary ↔ UART island (Si8621BD) | reinforced, user-touchable | as heater (PC ground = earth): 318 Vrms | 6.4 → **8.0 mm** (plan target) | **4.0 mm** | 8.0 mm |
| DAB secondary ↔ UART | reinforced (ES3 to touchable) | 420 V DC → 420 Vrms | 2 × 4.2 = **8.4 mm** | 3.0 mm (1500 V transient behind reinforced insulation → 1.5 mm, margin) | 8.4 mm |
| DAB secondary ↔ heater | functional (user 2026-11-17: heater tied to −100V BIAS or to signal ground via 100 Ω) | to 420V: up to 520 V; to ISO_GND / LV secondary: ≤ 115 V | **5.2 mm** to HV_SECONDARY, **1.5 mm** to SECONDARY_LV | 1.5 / 1.0 mm | 5.2 mm / – |
| Heater ↔ UART | functional | ELV | – | 1.0 mm | 1.0 mm |
| PE (Y caps) ↔ primary / secondary | basic | 318 / 420 Vrms | **3.2 / 4.2 mm** | 2.0 / 1.5 mm | 3.2 / 4.2 mm |
| Mounting holes H1–H8 (screws bonded to the earthed chassis, user 2026-11-17) ↔ primary / secondary | basic (PE) | 318 / 420 Vrms | **3.2 / 4.2 mm** | 2.0 / 1.5 mm | 3.2 / 4.2 mm (hole clearance) |
| Inside a domain: HV nets (DC+, mains, switch nodes, 420V, −100 V) | functional | ≤ 500 V | – | outer 1.2 mm (tracks / zones; pad pairs exempt), inner 0.5 mm | 0.5 mm |

**Former exception, DAB bridge Q19 (primary) ↔ Q21 (secondary)** (user 2026-11-19, removed in routing stage 4k,
2026-11-22): while the two TO-220s sat side by side across a 1.2 mm L-shaped barrier slot, their drill barrels were
checked on the inner layers at 4.0 mm instead of 11.1 mm (rule "PRI-SEC inner layers, Q19/Q21 across the barrier
slot"). Q19 stands in the single primary heatsink line since stage 4a, the rule had no pair left and is gone from
`tube_psu_5_2.kicad_dru` and from `ALLOW` in `check_domains.py`: every primary ↔ secondary pair on the inner layers
is checked at 11.1 mm.

**Alternative if ISO_GND may float** (IEC 62368-1 5.4.1.8: a floating circuit is assumed earthed at the
point giving the highest working voltage): with the 420V rail earthed, −80/−100 V vs DC+ reaches
900 Vpk / ≈ 800 Vrms → reinforced creepage 2 × 8.0 = **16 mm**, clearance unchanged (4.0 mm; required
withstand still set by the 2500 V transient). The rules use the 11.1 mm case; **the user must confirm
that the secondary is always tied to the earthed amplifier chassis** (confirmed by the user 2026-11-17, so 11.1 mm stays) – otherwise change 11.1 → 16.0 in
`tube_psu_5_2.kicad_dru` and `check_rules.py`.

Uncertain / to verify: the IEC 62368-1 table and clause numbers above are from the TI summary and memory
of the standard, not from a copy of it – check them against the edition used for the product; the
> 30 kHz content of the DAB switch nodes across the barrier (IEC 62368-1 / IEC 60664-4 creepage at high
frequency) has not been assessed – the dominant 552 Vrms term is mains-frequency, the HF part is the
DAB square wave (≤ 420 V) on top.

### Consequences found while setting the rules (for phases 2–5)

- **SOIC-16W isolators** (ISO1 / ISO2 Si8661BD, UART Si8621BD): pad row to pad row ≈ 7–8 mm < 11.1 / 8.0 mm →
  a **slot under each isolator** (Edge.Cuts, KiCad's creepage check follows it) or the rule fails there.
  **Done in phase 3** (`_Slot8.0` / `_Slot11.1` footprints, section "Footprints and 3D models").
  Check that the Si8661BD reinforced rating (VIOWM / IEC 62368-1 certificate) covers 552 Vrms.
- **EEL19 TR1 footprint** (`Transformer_EEL19_V_4+6_FlyLeads`): pad rows 12.5 mm apart, pad edge to pad
  edge ≈ 10.8 mm < 11.1 mm → slot between the rows or a wider row pitch; and the bobbin's 3 + 3 mm
  margin construction (6 mm) is below 11.1 mm creepage for this working voltage (NEXT_REVISION_PLAN.md
  "Consequences of D6"). EC42 TR3: rows 40 mm apart – fine on the board.
- Mounting holes have a copper ring on every layer with no net; H4 (5.8, −40.1) sits inside the board –
  3.2 / 4.2 mm keep-off around it (screws earthed via the chassis).
- Heatsink: the shared PFC + DAB bracket must keep 11.1 mm creepage / 4.0 mm clearance from secondary
  copper unless it is treated as secondary or split (plan, D6).

## Prompt of phase 2 (schematic changes) – done 2026-11-18, see CHANGES_5_2.md

```
Phase 2 of tube_power 5.2 in /home/jari/dev/tube_psu_kicad. Read NEXT_REVISION_PLAN.md (phase 2 table,
D1-D6, "Consequences of D6"), NEXT_REVISION.md (NR items), kicad_next/README.md (how the fork works) and
STATUS.md "Phase 1 of 5.2". Edit only the 5.2 sources: tools/next/sheets/*.py, tools/next/gen_symbols.py,
lib/part_map_next.csv, lib/footprint_map_next.csv, lib/jlc_parts_next.csv, tools/next/setup_project.py
(HV_NETS, GROUNDS: add the UART island ground, e.g. ISO_UART_GND), kicad_next/*.kicad_dru if needed.
Never touch kicad/, tools/sheets/, the 5.1 lib files, tools/p2k or ~/dev/ac_psu_kicad; never run the
KiCad AppImage with --version.

Work sheet by sheet (NEXT_REVISION_PLAN.md phase 2 table): TR1 -> EEL19 4+6 + fly leads and PWM2 ->
iW1819-00 (new symbols, Vcc / Vsense / Rsense rechecked, preloads, D8/D4/D5 ratings, C102); sheet 2 R40/R25
DNP; sheet 4 J2 channel map + UART island (CA-IS3721HW, 4-pin header GND / 3V3 / TXD / RXD powered from the minimodule; nets in a new UART domain);
measurement fixes (bias buffer, VAC / DC_LINK Cf, R49/R80, AUX + 5V_MEAS followers); sheet 7 TR3 -> EC42
two-chamber option B 20:21, L3 removed; sheets 8 / 10 LMH6643 with feedback caps on both legs; sheet 5
L1/L2 toroids; LCSC field for every new part; root title block rev V5.2 (gen_schematic.py ROOT_EDITS).
New footprints go to lib/tube_psu_next.pretty (tools/next/gen_next_footprints.py) and the map
lib/footprint_map_next.csv. After each sheet: python3 tools/next/gen_schematic.py, then
tools/next/check_next.sh (drop the "--diff51" step once the schematic differs from 5.1, keep ERC 0
errors, every net in one domain - setup_project.py --check fails on a part bridging two domains unless it
is listed in BARRIERS). Exit: ERC clean, a netlist diff 5.1 -> 5.2 (kicad-cli sch export netlist of
kicad/ and kicad_next/) reviewed item by item against NEXT_REVISION.md, STATUS.md section "Phase 2 of 5.2",
tools/check_all.sh still ALL CHECKS PASSED. Open questions for the user from phase 1: ISO_GND always
earthed via the amplifier (11.1 mm) or floating (16 mm)? Mounting screws earthed? Heater elevation?
Commit locally with explicit paths, do not push.
```
