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
| `kicad_next/tube_psu_5_2.kicad_pcb` | board skeleton: 5.1 outline, H1–H8, 6 copper layers, JLC stackup; no footprints yet | `tools/next/make_board.py` once; then edited in KiCad (phase 5+) |
| `kicad_next/tube_psu_5_2.kicad_dru` | custom rules: JLC limits, HV functional spacing, creepage / clearance between domains | by hand (this file is the source) |
| `kicad_next/sym-lib-table`, `fp-lib-table` | `tube_psu_next` → `lib/tube_psu_next.kicad_sym` (used), `tube_psu` → `lib/tube_psu.kicad_sym` (5.1, reference); footprints `tube_psu` → `lib/tube_psu.pretty`, `tube_psu_next` → `lib/tube_psu_next.pretty`, `tube_psu_next_parts` → `lib/tube_psu_next_parts.pretty` | `gen_schematic.py` |
| `tools/next/sheets/sheetNN.py`, `_common.py` | sheet scripts, copies of `tools/sheets/` (sheet scripts unchanged; `_common.py` redirects output, symbol library, CSVs) | phase 2 edits these |
| `tools/next/gen_symbols.py` → `lib/tube_psu_next.kicad_sym` | 5.2 symbols (fork of `tools/gen_symbols.py`; identical output at the fork) | phase 2 adds ICE5AR (PWM2, replaced the iW1819), SI8621, UCC21520, … |
| `lib/part_map_next.csv`, `lib/footprint_map_next.csv`, `lib/jlc_parts_next.csv` | values, footprints, LCSC numbers per refdes – hand-edited forks of the 5.1 tables | by hand |
| `tools/next/check_next.sh` | all 5.2 checks (below) | – |
| `tools/next/gen_next_footprints.py` → `lib/tube_psu_next.pretty` | EEL19 / EC42 transformers, L1/L2 upright toroid on the 5.1 RM8 holes (`_Vertical_RM8_45deg` / `_315deg`, 2026-11-19; the flat toroid + `_TieSlots` unused), heatsink outline helper | phase 3 |
| `tools/next/gen_next_footprints_parts.py` → `lib/tube_psu_next_parts.pretty` | SOIC-16W with creepage slot (`_Slot8.0`, `_Slot11.1`), electrolytics with the real can height (`_H<n>mm`), copies of 5.1 footprints with a 3D model (reads KiCad library footprints from the AppImage: run through `tools/p2k/bin/kicad_env.sh`) | phase 3 |
| `tools/next/gen_next_3d.py` → `lib/tube_psu_next.3dshapes` | 16 simple STEP models (CadQuery venv, see below) | phase 3 |
| `tools/next/reuse_51_board.py` (kipy) → `kicad_next/trial_from_51/` step 0, `tools/next/trial_placement.py` (kipy) → step 1, `tools/next/trial_report.py` → `REPORT.md` | trial 5.2 board from the verified 5.1 layout (step 0: footprints / nets / copper reuse, L1 / L2 upright on the RM8 holes); step 1: TR3 / split caps / DRV5 / DRV6 moves as data (`PLACE` / `GROUPS`) + split-pass DRC; not checked by check_next.sh | phase 5 input |
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

## Stackup (D5) – JLC06161H-3313, 6 layers, 1.6 mm, 1 oz outer / 0.5 oz inner

Values from JLC's impedance-calculator stackup table (jlcpcb.com/impedance, read 2026-11-17); solder-mask
0.6 mil over copper, Dk 3.8 (JLC calculator guide); laminate Nan Ya NP-155F (JLC 4–8 layer default).
Loss tangent 0.02 is a generic FR-4 figure (not published per stackup). Finished thickness 1.6 mm nominal
(the layers below sum to 1.538 mm + mask; JLC tolerance ±10 %). Surface finish ENIG (JLC: no HASL on
≥ 6 layers; vias epoxy-filled and capped by default).

| # | Layer | KiCad name / type | Use | Thickness | Dk |
|---|---|---|---|---|---|
| | F.Mask | – | LPI mask | 0.015 | 3.8 |
| L1 | F.Cu | F.Cu, signal | parts + power copper, signals | 0.035 (1 oz) | |
| | prepreg 3313 ×1 (RC 57 %) | dielectric 1 | | 0.0994 | 4.1 |
| L2 | In1.Cu | In1.GND, power | GND planes, one per domain | 0.0152 (0.5 oz) | |
| | core | dielectric 2 | | 0.55 | 4.6 |
| L3 | In2.Cu | In2.Signal_HV, signal | signals / HV routing | 0.0152 | |
| | prepreg 2116 ×1 | dielectric 3 | | 0.1088 | 4.16 |
| L4 | In3.Cu | In3.Power, mixed | power pours (DC+, 15V, +3V3, …) | 0.0152 | |
| | core | dielectric 4 | | 0.55 | 4.6 |
| L5 | In4.Cu | In4.GND, power | GND planes, one per domain | 0.0152 | |
| | prepreg 3313 ×1 | dielectric 5 | | 0.0994 | 4.1 |
| L6 | B.Cu | B.Cu, signal | bottom parts + signals | 0.035 (1 oz) | |
| | B.Mask | – | LPI mask | 0.015 | 3.8 |

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

Net classes (clearance / track / via; mm): Default and SIGNAL 0.15 / 0.2 / 0.6-0.3, PRIMARY_LV 0.2 / 0.5,
SECONDARY_LV 0.2 / 0.3, HEATER 0.2 / 1.0, UART_ISO 0.15 / 0.2, HV_PRIMARY and HV_SECONDARY 0.5 / 1.0 / 1.0-0.5
(inner-layer functional spacing for ≤ 500 V; outer layers 1.2 mm by rule), PE_EARTH 0.5 / 1.5. Widths are
starting values; phase 6 sizes the power paths from the currents (D5 copper).

## Isolation domains and creepage / clearance (D6)

Domains are found from the schematic by `setup_project.py` (flood fill from GND / ISO_GND / HT_GND, not
through the barrier parts TR1, TR2, TR3, ISO1, ISO2; no other part bridges two domains in the 5.1
netlist). Count after phase 2: primary 156 nets (HV_PRIMARY 43, PRIMARY_LV 5, SIGNAL 108; after the ICE5AR0680AG change and NR 2.8), DAB secondary 42
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
  build – **verify the clause** in the edition used); L1–L2 / L5–L6 have one 0.0994 mm 3313 ply and
  L3–L4 one 0.1088 mm 2116 ply → **copper of two domains must never overlap on any pair of layers**
  (only the 0.55 mm cores would pass 0.4 mm). Phase 5/6: barrier keep-out on all six layers.

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
DNP; sheet 4 J2 channel map + UART island (Si8621BD, LDO, FTDI 6-pin header; nets in a new UART domain);
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
