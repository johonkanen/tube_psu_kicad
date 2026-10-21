# Proteus → KiCad migration plan: tube_power_5_1 ("Tube power supply")

Goal: redraw the Proteus schematic in KiCad 10, then rebuild the PCB in KiCad from the
Proteus gerbers so that every pad, track, via and pour carries the net from the redrawn
schematic. Prove with scripted checks that the KiCad design is electrically identical to
the Proteus one.

This follows the generic playbook `~/dev/ac_psu_kicad/CONVERSION_PLAYBOOK.md`, proven on
`~/dev/ac_psu_kicad` (single_phase_inverter_psu_v3, 267 parts, 4 layers). Read it first;
this plan lists only what is specific to this board and where it differs from ac_psu.
The ac_psu tools (`~/dev/ac_psu_kicad/tools/`) are reused; the playbook's section 4 says
which are generic and which need adapting.

## 1. Inventory (checked 2026-10-21)

Source folder `C:\Users\jaarh\Sync\proteus_projektit\Projects\tube_power\tube_power_5_1\`
(`/mnt/c/...`), copies in `source/`:

| Item | Notes |
|---|---|
| `source/tube_power_5_1.pdsprj` | Main-folder project, saved 2020-10-03 (zip of binary `ROOT.DSN` / `ROOT.LYT` / `ROOT.CDB`). The `proteus_8/` copy is the same project opened in another Proteus version (user, 2026-10-21); not used. Only useful via `strings`. |
| `source/schematic_pdf/tube_power_5_1.PDF` | 11 sheets, printed 2026-10-15 from the same project (title block date 03/10/2020, "V5.1"). Text layer extracted to `schematic_text.txt`; page renders `hi-NN.png` (200 dpi). |
| `source/tube_power_5_1 - CADCAM.ZIP` → `source/cadcam/` | Re-exported 2026-10-21 07:38 from `tube_power_5_1.pdsprj` with Proteus 8.12 SP2. RS-274X, metric, `FSLAX45Y45`, 4 copper layers (Top, Inner 1, Inner 14, Bottom), silk/resist/paste both sides, Top/Bottom Assembly, Mechanical 1 (outline), drill as Excellon (`.DRL`) **and** as gerber, **IPC-D-356A netlist**, READ-ME (apertures, drill tools, stack-up). |
| Not used | `tube_power_5_1 - CADCAM.ZIP` of 2019 (overwritten by the re-export) and `tube_power_5_1_cleaned - CADCAM.ZIP` (2019-05-15): imperial RS-274X, no netlist, no outline, older layout than the 2020 project. |

Sheets (PDF page → title from the title block; one KiCad sub-sheet each):

| Page | Title | Main parts |
|---|---|---|
| 1 | AUX supply | PWM2 flyback controller, TR1 (EF20), output rails +15V/−5V/−80V/+5V/SEC GND |
| 2 | DHB gate drivers | DRV5, DRV6 (Si827x) |
| 3 | Isolated measurements | ISO1/ISO2 (Si8661), AD1/AD2, U2/U3 (TLV316), V2/V3 (MIC5205) |
| 4 | MCU connector | J2 (2×25, 50 pins), J4, REF1, V4 (TPS73033), U6, DC-link measurement |
| 5 | PFC | DB1 (TBS22k bridge), RL1, CM1/CM4, L1/L2, SICD1/SICD2 (C3D02060A), Q5/Q6/Q9, IN1/IN2/PE |
| 6 | Heaters | Q1/Q2/Q10/Q11, TR2 (E25), DRV3/DRV4/DRV9, D11 |
| 7 | DHB | Q7/Q8/Q19/Q21, TR3 (ETD34), L3, +400V terminal |
| 8 | Current meas circuit | U1 (LMH6656) |
| 9 | AC meas | DRV1/DRV2, U8 (TLV316) |
| 10 | (title to read from the page; PFC current measurement) | U4 (LMH6656) |
| 11 | Startup circuit | bulk caps C28/C29/C37/C56/C73, C14 |

Board (gerbers / READ-ME):

- Outline (Mechanical 1): rectangle 163.0 × 110.0 mm, corner (−71.9, −18.7) mm. The same
  rectangle is also drawn into each copper gerber (2 occurrences per file, cf. the ac_psu
  `Profile` draw) – skip it when reading copper.
- Stack-up: 4 layers, 0.036 mm copper, prepreg 0.32 / core 0.772 / prepreg 0.32 →
  ≈ 1.58 mm. Inner layers are named `Inner 1` and `Inner 14` (→ KiCad In1.Cu / In2.Cu).
- Copper: no arcs (no G02/G03); pours as G36 regions (Top 342, In1 262, In14 162,
  Bottom 327) with clear-polarity cut-outs (`%LPC%`: 37 / 12 / 10 / 25); pad flashes
  (Top 727, In1 502, In14 502, Bottom 940); no aperture macros on copper.
- Drill (Excellon, 15 tools, 502 hits = the 502 THT records of the IPC): 279 × 0.3 mm +
  4 × 0.381 mm vias, 8 × 3.0 mm **unplated** mounting holes, all others plated pad holes.

IPC-D-356A netlist (`tube_power_5_1 - CADCAM Netlist.IPC`, identical content to
`tube_power_5_1.IPC` in the source folder):

- 1165 records: 502 THT (`317`) + 663 SMD (`327`). 315 reference designators, 193 named
  nets (87 auto-named `#000xx`), 9 N/C pads, 20 single-pin nets (unused J2 pins F16, G15,
  K16, …, ADA0/1/2/4, ADB0, EPWM1A, CUK_CAP_MEAS_RAW, HEATER_CAP_AD_MEAS).
- Records with **blank refdes**: 283 vias (net, 0.3 / 0.381 mm drill), 4 free plated pads
  2.55 mm drill / 4.0 mm pad with a net (at x = −42.8 mm, y = 66.4 / 74.0 / 79.2 /
  86.8 mm; two on the same net – probably wire/screw pads), 8 unplated 3.0 mm holes
  without net. (ac_psu had vias with refdes `VIA`; `ipc356.py` must take blank refdes.)
- SMD sides: 438 pads on the bottom (A16, 170 parts), 225 on top (A01, 91 parts); THT
  parts all from the top. The bottom side carries most SMD parts – the bottom placement
  recipe (playbook, pitfalls) is used a lot.
- **Truncated refdes** (6 characters), terminals named after their net – restore by
  coordinate from the PDF: `+15V O` (+15V OUT), `+5V OU`, `-5V OU`, `-80V O`, `HT_6V3`,
  `HT_GND`, `SEC GN` (SEC GND); also short terminal names `+400V`, `GND`, `PE`, `IN1`, `IN2`.
  KiCad refdes cannot sensibly contain spaces or start with +/−: define a refdes map
  (e.g. `SEC GND` → `SEC_GND`, `+15V OUT` → `T_15V_OUT`) used by every comparison.
- Pin ids: numbers for most parts; diodes `A`/`C`, SiC diodes SICD1/2 `A`/`K`; the PFC
  chokes L1–L3 `1`, `2`, `pri1`, `pri2`; J2 is a 50-pin connector with IPC pins 1–50 (the PDF labels
  them A1…, B1… by signal – map by position), TR1 10 pins, TR2 8, TR3 12, RL1 5, DB1 4, CM1/CM4 4.
- Power nets: only `GND=POWER` carries the Proteus `=POWER` suffix (alias → `GND`).
  Other rails are ordinary named nets: 5V, +3V3, +2V5_BIAS, 20V, 20V_ISO_SEC, 6V3, 420V,
  −100V, −5V_SEC, 5V_ISOL, ISO_GND, HT_GND, AD2_3V3, …; `$HT_CS`, `$CUK_CS` start with `$`.
- Component counts (IPC): R 124, C 112, D 20, Q 11, DRV 7, U 6, TR 3, L 3, V 3, J 2, CM 2,
  ISO 2, AD 2, SICD 2, IN 2, DB 1, RL 1, PWM 1, REF 1, PE 1, terminals 7.

Differences from ac_psu that shape the plan:

1. **The gerbers carry no X2 attributes** (no `%TA.AperFunction`, no `%TO`, no
   `TF.SameCoordinates`), although they are RS-274X with regions. ac_psu's
   `gerber_to_tracks.py` tells tracks, via pads, component pads, non-conductor lines and the
   outline apart by aperture function. Two options:
   - **(recommended)** re-export the CADCAM once more with Gerber X2 enabled in Proteus'
     CADCAM output dialog (same project, nothing else changed) – then the ac_psu tools work
     as they are;
   - or classify geometrically: flash at an IPC via position = via pad, flash at an IPC
     component pad = component pad, D01 draw = track unless it is a pour edge stroke or the
     outline. Feasible, but one more source of error.
   Decide at the start of Phase 0 (ask the user).
2. Vias, free pads and mounting holes are blank-refdes records (see above); mounting holes
   are unplated (ac_psu: plated).
3. High-voltage board (420 V DC link, −80 V/−100 V rails, mains input): design rules must
   come from Proteus' copper (smallest gap between nets per region), and KiCad net classes
   for HV nets are useful for later edits. Phase 3 measures the actual minimum gaps from
   the gerbers per net pair and sets rules no stricter than the board as built.
4. Excellon drill available (ac_psu only had a drill gerber) – use it for the drill
   comparison; keep the drill gerber as a cross-check.

## 2. Phase 0 – skeleton and tooling (½ day)

1. Layout as in ac_psu: `source/` (done), `reference/`, `lib/`, `kicad/`, `tools/`,
   `reports/`. Copy from ac_psu: `tools/bin/`, `kicad_env.sh`, `sexpr.py`, `geom2d.py`,
   `gerber.py`, `fpgeom.py`, `sch_builder.py`, `render_sheet.py`, `erc.sh`, `check_all.sh`
   (trim to the steps that exist).
2. Ask the user about the Gerber X2 re-export (section 1, point 1).
3. `tools/ipc356.py` adapted: file name, blank-refdes records (vias / free pads / holes),
   `TRUNCATED_REFDES` for the terminals (positions from the IPC, names from the PDF),
   the KiCad refdes map for names with spaces/signs, `NET_ALIASES` (`GND=POWER` → `GND`),
   pin ids with letters (`A`/`C`/`K`, `pri1`/`pri2`). Outputs `reference/ipc356_pads.{json,csv}`,
   `pin_nets_by_component.md`, `pins_by_net.md`; `--check` asserts 1165 records,
   502 THT / 663 SMD, 283 vias, 8 holes, 4 free pads, 315 refdes, 9 N/C.
4. `tools/gerber.py`: check it reads these files (4.5 metric, no attributes; inner layer
   file names `Inner  1` / `Inner 14`); add an Excellon reader if the drill check uses it.
5. README.md, STATUS.md, `tools/check_all.sh`, next_prompt.md; commit.

Done when: the IPC parser counts match this inventory and the cheat sheet exists.

## 3. Phase 1 – schematic (1–2 days)

As in the playbook. Specific points:

- Part map (`lib/part_map.csv`) from the IPC refdes list + PDF text/values + `strings` of
  `ROOT.DSN` for part numbers. PDF-only names that are not parts: `V1 : …`, `V5.1` notes,
  `R6131` (text artefact) – the IPC refdes list decides.
- Custom symbols likely: TR1 (EF20, 10 pins), TR2 (E25, 8), TR3 (ETD34, 12), L1–L3 PFC
  chokes (pins 1/2/pri1/pri2), CM1/CM4 (SCF20 4-pin), RL1 (5-pin relay), DB1 (TBS22k),
  PWM2 (iW1818 – datasheet in the source folder), DRV1–DRV6/DRV9 (IXDD609, Si827x),
  ISO1/ISO2 (Si8661), AD1/AD2 (ADC121S101-type), J2 (2×25 MCU header), terminals.
- Power symbols for the rails listed in section 1 (names = IPC net names). Decide early
  which named rails get power symbols vs global labels (KiCad ERC `multiple_net_names`
  when a label and a power symbol share a net).
- Sheet order (easiest first): 11 startup → 2 DHB gate drivers → 9 AC meas → 8 current
  meas → 10 → 4 MCU connector → 3 isolated measurements → 6 heaters → 7 DHB → 5 PFC →
  1 AUX supply. Compare and ERC after every sheet.

## 4. Phase 2 – footprints (½–1 day)

As in the playbook (`gen_footprints.py` rules by symbol + IPC pad pattern, rigid fit
≤ 0.05 mm, `reports/footprint_fit.csv`). Expected project footprints: the three
transformers, PFC chokes, CM chokes, relay, bridge, TO-220/TO-247 power parts (check
the actual packages from the pad patterns), J2, terminals, the 4 free 2.55 mm pads
(board-only footprints or plain pads – decide with the user), the 8 unplated 3 mm holes
(NPTH mounting holes). Many bottom-side SMD parts: check the mirror fit for the chiral
ones (SOT-23, SOIC).

## 5. Phase 3 – PCB (1–2 days)

`tools/make_pcb.sh` as in ac_psu: `build_pcb.py` (outline 163 × 110 mm, 4 layers,
≈1.58 mm stack, design rules from the measured Proteus gaps, footprints at the IPC
positions, NPTH holes, free pads) → `gerber_to_tracks.py` (X2 or geometric classification,
section 1) → `assign_nets.py` → `pours_to_zones.py`; checks `check_board.py` (pads, 283
vias, 8 holes, 4 free pads vs IPC) and `drc.py` (0 shorts, 0 unconnected, 0 parity; accepted
types listed with reasons). Expect the first DRC to flag KiCad pads that are larger than
Proteus' and reach Proteus tracks → user decision on Proteus pad sizes per footprint.

## 6. Phase 4 – verification (½ day)

Reuse `gerber_roundtrip.py` (copper XOR, coverage, drills – here also against the
Excellon file) and `ipc356_diff.py` (KiCad IPC-D-356 vs Proteus: blank-refdes vias/holes,
refdes map for the renamed terminals) unchanged apart from paths and the refdes map; then
the independent review and negative tests. Add both to `tools/check_all.sh`.

## 7. Risks and open points

- Gerber X2 attributes missing (section 1, point 1) – decide before Phase 3.
- Terminal refdes with spaces and signs – one refdes map used by every script.
- HV clearances: KiCad rules must not be stricter than the copper as built, or DRC drowns
  in errors; and must not be looser than what the board needs for later edits (net classes).
- Proteus pinouts may differ from manufacturer/KiCad pinouts (ac_psu: REF3025, SOT-23
  renumbering) – follow the IPC ids, report differences.
- Bottom-heavy SMD placement: most fits use the mirrored recipe.
- The PDF has hand notes (V1/V2/V3 turn counts, `R64 = 39k / v2 trans`, "check primary
  turns") – the IPC netlist decides connectivity; values from the PDF, noted where unclear.

## 8. Rough effort

| Phase | Effort |
|---|---|
| 0 tooling + IPC parser (tools copied from ac_psu) | ½ day |
| 1 schematic (11 sheets, 315 parts) | 1–2 days |
| 2 footprints + fit check | ½–1 day |
| 3 PCB build, nets, zones | 1 day (tools exist) |
| 4 verification | ½ day |

## 9. Model and session plan

As in the playbook section 6: Opus 5.5 for Phases 0, 1-preparation, 2, 3; Fable 5.1 for the
sheet transcription (one sheet per turn, compare after each) and for the Phase 4
independent review. One session per phase; each starts with `PLAN.md`, `STATUS.md` and
`tools/check_all.sh`, and ends by updating `STATUS.md`, replacing `next_prompt.md`
(ready-to-paste prompt, also as the last message in a fenced block) and committing.
