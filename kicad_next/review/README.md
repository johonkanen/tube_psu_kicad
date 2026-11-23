# Design review of tube_power 5.2 – checklists

Fourteen checklists, one per design part. Each is written to be handed **alone** to one fresh reviewer agent
(Opus, empty context) that knows nothing about the project: the checklist file plus the repository is all it gets.
The reviewer does an evidence-based review of that one part and writes one findings file. Nothing in this
directory changes the design.

Written 2026-11-23 against the board of commit `ecf0024` (fully routed, 0 unconnected, `check_next.sh` passing; the
fab package of commit `7413e4a` was made from the same board).
If the board or the schematic changed since, the coordinates and counts quoted in the checklists are hints, not
facts: the reviewer re-reads them with the helper commands.

## Index

| File | Design part | Sheets / area |
|---|---|---|
| [01_aux_flyback.md](01_aux_flyback.md) | Auxiliary flyback: PWM2 ICE5AR0680AG, TR1 EEL19, six output rails, preloads | sheet 1; x 36 … 88, y −22 … 18 |
| [02_dab_gate_drive.md](02_dab_gate_drive.md) | DAB gate drive: DRV5 (primary), DRV6 (secondary), bootstraps, dead time, DAB_DIS, gate networks of Q7 / Q19 / Q8 / Q21 | sheet 2 + gate parts of sheet 7 |
| [03_isolated_measurements.md](03_isolated_measurements.md) | Isolated ADC chains AD1 (heater 6.3 V) and AD2 (420 V), ISO1 / ISO2, LDOs V2 / V3, the 420 V dividers | sheet 3 + dividers of sheets 6 / 7 |
| [04_j2_uart_supplies.md](04_j2_uart_supplies.md) | Control-card connector J2, +3V3 LDO V4, bias reference REF1 / U9, isolated UART U11 / J4 (12 Mbaud) | sheet 4 (without U6 / U10) |
| [05_pfc_emi_inrush.md](05_pfc_emi_inrush.md) | Mains input, EMI filter, inrush relay, bridgeless dual-boost PFC, PFC gate drivers DRV1 / DRV2, DC-link capacitors | sheets 5, 11, drivers of sheet 9 |
| [06_heater_llc.md](06_heater_llc.md) | Heater half-bridge LLC: Q10 / Q11, DRV3, TR2, resonant capacitors, synchronous rectifier Q1 / Q2 / DRV4, 6V3 output | sheet 6 |
| [07_dab_power_stage.md](07_dab_power_stage.md) | DAB / dual half bridge 400 V ↔ 420 V: Q7 / Q19 / Q8 / Q21, split capacitors, TR3, 420V output | sheet 7 (power part) |
| [08_current_measurement.md](08_current_measurement.md) | Four shunt current chains: R93 / R21 (PFC), R83 (DAB), R30 (heater) → U4 / U1 LMH6643 → J2 | sheets 8, 10 |
| [09_voltage_measurement.md](09_voltage_measurement.md) | Primary-side voltage chains: VAC (U8), DC link (U6), 15V / 5V monitors (U10) → J2 | sheet 9 (U8), sheet 4 (U6, U10) |
| [10_isolation_creepage.md](10_isolation_creepage.md) | Isolation domains, creepage / clearance, slots, inner layers, layer to layer, mounting holes, PE – whole board | board + `.kicad_dru` |
| [11_power_loops_layout.md](11_power_loops_layout.md) | Commutation loops, gate loops, DC-link and return paths, copper width vs current, compared with 5.1 – whole board | board, 5.1 board |
| [12_thermal_mechanical.md](12_thermal_mechanical.md) | Heatsink line, tall parts, mounting holes, connectors, courtyard overlaps, hand-soldered parts | board, 3D models |
| [13_bom_parts.md](13_bom_parts.md) | Every part: rating / derating, footprint vs ordered part, LCSC number, stock, consigned parts | `lib/*_next.csv`, schematic |
| [14_fab_assembly_package.md](14_fab_assembly_package.md) | Fabrication / assembly package for JLCPCB (`kicad_next/fab/`) | `kicad_next/fab/` |

## How to run one checklist

1. Start **one fresh Opus agent per checklist file**, working directory `/home/jari/dev/tube_psu_kicad`.
   Its whole prompt: "Do the design review described in `kicad_next/review/NN_name.md`. Follow the rules in that
   file. Write your findings to `kicad_next/review/findings/NN_name.md` and report the three most important
   findings."
2. The reviewer is **read-only** on the repository. The only file it writes is
   `kicad_next/review/findings/<same file name as the checklist>.md` (plus scratch files outside the repo).
3. The reviewer runs `kicad_next/review/tools/rv guard` and `rv setup` first (section "Helper tools").

### Order, and what can run in parallel

RAM is the limit: a KiCad DRC of this board needs about 2.3 GB, so **at most one agent at a time may run a
KiCad DRC job** (`tools/next/check_next.sh`, `tools/next/check_board.py`, any `kicad-cli pcb drc`). Only the
reviewers of **10** and **14** may need one, and only if `reports/next/drc.json` is older than the board
(`python3 kicad_next/review/tools/drc_summary.py` tells). Everybody else reads the existing reports.
The helper dumps (`rv setup`) are light (< 300 MB, < 10 s) and are shared through one cache directory.

| Wave | Checklists | Why this order |
|---|---|---|
| 1 (may run together, no DRC) | 01, 02, 03, 04, 05, 06, 07, 08, 09 | the circuit parts; independent of each other. If RAM is short run them 3 at a time |
| 2 (one after the other if a DRC is needed) | 10, then 11, then 12 | whole-board reviews; they profit from the wave-1 findings files (optional input, see below) |
| 3 | 13 | parts; uses the "parts" notes of the wave-1 findings if they exist |
| 4 (last, after the fab package exists) | 14 | needs `kicad_next/fab/` complete and the board frozen |

A whole-board reviewer (10 – 14) **may** read finished findings files of earlier waves in
`kicad_next/review/findings/` as leads, but must verify each lead itself and must not copy a verdict.

## Common rules (every reviewer)

1. **Read-only.** Do not change, regenerate, reformat or "fix" anything in the repository. Write only your own
   findings file. No `git add`, no commit, no push, no stash, no checkout of other revisions in this working tree
   (use `git show REV:path` to read history).
2. **Never touch the board or project file**: `kicad_next/tube_psu_5_2.kicad_pcb`, `.kicad_pro`, `.kicad_prl`,
   and never run a script that saves them or regenerates design files:
   `tools/next/route_s*.py`, `s3_router.py`, `update_board_parts.py`, `promote_trial_board.py`, `reuse_51_board.py`,
   `trial_placement*.py`, `setup_project.py` without `--check` / `--list`, `make_board.py` without `--check`,
   `gen_schematic.py` / `gen_symbols.py` / `gen_next_footprints*.py` / `gen_next_3d.py` / `netlist_diff.py`
   without `--check`. Scripts under `kicad_next/review/tools/` are read-only by construction.
3. **KiCad GUI is assumed closed.** If a lock file exists (`kicad_next/~*.lck` or `kicad_next/*.lck`), stop and
   report it. `rv guard` checks this.
4. **RAM: stay under 3 GB.** No full-board creepage DRC (`kicad-cli pcb drc` with the creepage pass needs > 3 GB;
   `check_board.py` runs the DRC without it). Run `tools/next/check_next.sh` only if you are the reviewer of 10 or
   14, only if the reports are stale, and only if no other KiCad job runs:
   `pgrep -af "kicad-cli|kipy|check_next"` must show none (lines of your own shell wrapper do not count).
   **Never `pkill -f`** (it kills other sessions' jobs). **Never run the KiCad AppImage with `--version`** (it starts
   the GUI and hangs). Run KiCad jobs one at a time, in the foreground.
5. **Acceptance bar (set by the owner): 5.2 must match the performance of the working, bench-verified 5.1 board
   and add creepage. Do not optimise beyond that.** A finding is something that is wrong, worse than 5.1,
   unsafe, unbuildable, or undocumented and risky. "Could be better" is at most a note.
6. **Given decisions – do not re-litigate** (they are recorded in `kicad_next/README.md` / `CHANGES_5_2.md`;
   check that each was *implemented correctly*, not whether it was wise):
   - no silkscreen on 5.2: ignore silk DRC items; silk layers are left out of the fab output;
   - DC+ and its power-GND return are routed on F.Cu / B.Cu only; In1 / In4 are GND planes (README "Stage 9");
   - one primary heatsink line: Q5, Q6, SICD1, SICD2, DB1, Q7, Q19 at x 5 … 13 (README "Stage 4a"); Q8 / Q21 have
     their own secondary heatsink;
   - DRV5 channels swapped: A = high side, B = low side (CHANGES 3.1b);
   - C95 is an 0603 at DRV5 pins 11 / 9 (CHANGES 3.1c);
   - mounting hole H5 removed, seven holes left (README "Stage 10");
   - J4 is a 1×6 header: GND, TXD in, GND, RXD out, GND, 3V3 in; 12 Mbaud (README "Stage 11");
   - heater resonant capacitors 4 × 3.3 nF C0G 630 V (5.1: 4.7 nF X7R, derated to about 2/3 at 200 V bias) (CHANGES 2.9);
   - stackup JLC06161H-7628D (README "Stackup");
   - via-in-pad is fine at JLC on 6-layer boards (filled and capped by default) – no action, do not list the vias;
   - the Proteus / PDF nets 20V, 20V_ISO_SEC, +2V5_BIAS are 15V, 15V_ISO_SEC, +1V65_BIAS in KiCad (the rail *is* 15 V);
   - the ISO_GND secondary is always tied to the earthed amplifier chassis (creepage basis 11.1 mm, README
     "Isolation domains").
7. **Evidence, not impressions.** Every verdict needs a file:line, a command with its output, a calculation
   with its inputs, or a datasheet page. "Looks fine" is not a verdict. **Datasheet facts must come from the
   datasheet fetched in this session** (manufacturer site, or LCSC / JLC part page for the exact LCSC number),
   never from memory; quote document number / revision, page or table, and the URL. If a datasheet cannot be
   fetched, the item is CANNOT VERIFY.
8. **Privacy.** The owner's name and e-mail address stay out of web requests (search terms, headers, forms).
   Search for part numbers only.
9. **Stay in scope.** Each checklist names its part. Problems seen elsewhere go into a short "outside scope"
   list at the end of the findings, with the checklist that owns them.
10. **Known weak points** listed in a checklist are to be confirmed or refuted with evidence, like every other
    item – and the review has to look beyond them.

## Helper tools (`kicad_next/review/tools/`, all read-only, all tested 2026-11-23)

| Tool | What it does |
|---|---|
| `rv` | front end: `rv guard` (lock file, running KiCad jobs, free RAM), `rv setup` (exports the 5.2 and 5.1 netlists with `kicad-cli sch export netlist` and dumps both boards with `kipy board_dump.py` into `${TMPDIR:-/tmp}/tube_psu_review_<uid>/`; rebuilt only when a source is newer), `rv sch …` / `rv sch51 …`, `rv bq …` / `rv bq51 …`, `rv pdf FIRST [LAST]` (text of pages of the owner's design document), `rv section FILE 'REGEX'` / `rv headings FILE` (one section of a long Markdown file with line numbers) |
| `sch.py` | netlist queries: `sheets`, `sheet N` (every part with value, footprint, pin = net), `ref R1,R2`, `net NAME`, `bom N` (sheet parts joined with `lib/jlc_parts_next.csv`), `kind C` (all parts of one refdes prefix with nets and the parts-table columns), `check` (netlist against the parts table), `part REF` (rows of the three parts tables), `cmp OTHER.xml N` (differences of one sheet against 5.1; `rv sch cmp51 N`) |
| `board_dump.py` | (kipy, never saves) board → JSON: footprints / pads with nets and true pad outlines, tracks, vias, **stored** zone fills (un-fractured), Edge.Cuts items, holes, net classes |
| `bq.py` | board queries on that JSON (python3 + shapely): `fp`, `area`, `nets`, `net` (widths per layer, narrowest segments, vias, zone areas), `pads`, `dist A B` (smallest copper distance per layer with the two points), `near NET --within D [--other-class | --other-domain]`, `padgap`, `neck NET LAYER x1 y1 x2 y2` (widest copper channel between two points on one layer), `xsec NET LAYER x|y VALUE [LO HI]` (copper width across a cut line), `loop P1 P2 P3 …` (path length and enclosed area of a polygon through points or REF.PAD pads – a quick loop estimate), `slots`, `holes`, `classes` |
| `drc_summary.py` | counts / items of the last `reports/next/drc.json` and `erc.rpt`, and whether they are newer than the board |
| `parts_table.py` | `lib/jlc_parts_next.csv` grouped by LCSC number (lowest stock first), the `review` remarks, parts without LCSC number, one-number-two-values check; `parts_table.py board`: Value / footprint / LCSC / DNP of every board footprint against the table |
| `fab_check.py` | independent cross-check of `kicad_next/fab/`: file kinds, zip members, age, drill hits per diameter and position against the board, outline, CPL rows against footprint anchors and sides, BOM against the parts table, what is not assembled |

```sh
kicad_next/review/tools/rv guard
kicad_next/review/tools/rv setup
kicad_next/review/tools/rv sch sheet 6            # parts and nets of sheet 6
kicad_next/review/tools/rv sch part C95           # its rows in lib/jlc_parts_next.csv, part_map_next.csv, footprint_map_next.csv
kicad_next/review/tools/rv bq fp Q19,C95          # position, side, pads, nets, net classes
kicad_next/review/tools/rv bq net DC+             # track widths per layer, vias, pour areas
kicad_next/review/tools/rv bq neck DC+ F.Cu 12.75 -49.52 20.0 -40.0   # widest F.Cu channel from Q19 pin 2 into the DC+ pour
kicad_next/review/tools/rv bq dist RX AC1 --layer In3                 # smallest distance of two nets on a layer
kicad_next/review/tools/rv bq loop Q19.2 Q19.3 Q7.2 Q7.3 C67.2 C67.1  # path length / area of a loop through pad centres
kicad_next/review/tools/rv bq area 0 -66 16 8 --touch                 # every courtyard that overlaps a box
kicad_next/review/tools/rv bq51 fp Q19            # the same queries on the 5.1 board
kicad_next/review/tools/rv pdf 16 22              # design document, heater chapter
kicad_next/review/tools/rv section kicad_next/README.md 'Stage 9'
python3 kicad_next/review/tools/drc_summary.py
```

Things to know about the helpers:

- **Coordinates** are KiCad board coordinates in mm: x to the right, **y down**; this board lies at
  x −72 … 91, y −91 … 19, so "north" / "top edge" is y ≈ −91. The documents use the same numbers.
- Net names with spaces or brackets need quotes: `"Net-(R143-Pad2)"`, `"-100V BIAS"`, `"PFC CURRENT 2+"`.
  Sheet-local nets have a path (`/01 AUX supply/FLY_C`); the helpers accept the bare name (`FLY_C`).
  `@CLASS` means every net of a net class (`@HV_PRIMARY`, `@UART_ISO`), `@PRI` / `@SEC` / `@HEATER` / `@UART` / `@PE`
  every net of an isolation domain; a bare refdes (`H4`) means all pads of that footprint (for mounting holes, which
  have no net; write `fp:GND`, `fp:IN2`, `fp:PE` for the terminals that carry the name of a net).
- **Net class = isolation domain / voltage class**: SIGNAL + PRIMARY_LV + HV_PRIMARY are the mains-referenced primary
  (ground GND); SECONDARY_LV + HV_SECONDARY the DAB secondary (ISO_GND); HEATER (HT_GND); UART_ISO (ISO_UART_GND);
  PE_EARTH. `rv bq classes` lists them.
- **Through-hole pads whose unconnected inner rings are removed** count on those layers as the plated hole only
  (`fp` prints "barrel only: …"). An inner-layer distance of 0.5 mm to such a pad is to the hole wall.
- `dist` / `near` are straight 2-D distances per layer. They know nothing about slots (creepage round a slot is
  longer) and nothing about layer-to-layer spacing. The project's own check for that is
  `python3 tools/next/check_domains.py kicad_next/tube_psu_5_2.kicad_pcb` (read-only, a few hundred MB, part of
  `check_next.sh`).
- `neck` and `xsec` look at **one layer**; a path that changes layer through vias has to be judged piece by piece
  (`rv bq net NET` lists the vias).
- Zone copper is the fill **stored in the board file**. `check_next.sh` refills only in a temporary copy.
- The 5.1 KiCad netlist / board already use the names 15V, 15V_ISO_SEC, +1V65_BIAS; on the 5.1 board every net is
  in class Default and there are four copper layers (F.Cu, In1.Cu, In2.Cu, B.Cu).
- The helpers print plain text and never write into the repository. `python3 kicad_next/review/tools/bq.py` and
  `sch.py` without arguments print their full command reference. A wrong argument count gives a Python traceback,
  not a hint – check the reference.
- In a shell, never paste checklist text into a here-document or `eval`: the checklists contain back-ticks and
  `<`, `>` characters. Run the commands of the fenced `sh` blocks one line at a time.
- `rv guard` lists every process whose command line contains `kicad-cli`, `kipy` or `check_next`, including shell
  wrappers of other sessions – read the lines before deciding that a KiCad job is running.

## Where things are (for every reviewer)

| What | Where |
|---|---|
| 5.2 schematic (generated; 11 sheets) | `kicad_next/tube_psu_5_2.kicad_sch`, `kicad_next/01_aux_supply.kicad_sch` … `11_startup.kicad_sch`; **source** = `tools/next/sheets/sheet01.py` … `sheet11.py` (values come from `lib/part_map_next.csv`, footprints from `lib/footprint_map_next.csv`, LCSC from `lib/jlc_parts_next.csv`); the notes on the sheets are the `sh.text(...)` lines |
| 5.2 board | `kicad_next/tube_psu_5_2.kicad_pcb` – 6 layers F.Cu / In1.GND / In2.Signal_HV / In3.Power / In4.GND / B.Cu, 163.1 × 110.1 mm, fully routed; rules `kicad_next/tube_psu_5_2.kicad_dru`; PNGs of the layers in `kicad_next/routing/` |
| What changed 5.1 → 5.2 and why | `kicad_next/CHANGES_5_2.md` (table per sheet, row numbers "NR x.y"; generated netlist diff at the end), `NEXT_REVISION.md` (the change list with reasons), `NEXT_REVISION_PLAN.md` (phases, decisions D1 – D6), `OPTIONAL_IMPROVEMENTS.md` (deliberately not done) |
| Layout history and numbers | `kicad_next/README.md` (2200+ lines: use `rv headings` / `rv section`): "First draft", "Stage 7 … 12" (newest first), "Inner layers", "Power, HV and ground routing" with the table "Current and width", "Stage 4a … 4l" (DAB primary), "Footprints and 3D models", "Stackup", "JLC manufacturing limits", "Isolation domains and creepage / clearance (D6)" |
| Control-card connector | `kicad_next/J2_PINOUT.md` |
| 5.1 (the working reference) | `kicad/tube_psu.kicad_sch`, `kicad/tube_psu.kicad_pcb`, `STATUS.md`, `reference/pins_by_net.md` |
| Simulations | `simulation/FINDINGS.md` (measurement chains, ADC mux), `simulation/dab/DAB_SIMULATION.md`, `simulation/dab/DAB_TRANSFORMER.md`, `simulation/flyback/EEL19_DESIGN.md`, `simulation/flyback/FLYBACK_DESIGN.md` |
| Design intent | the owner's 2021 design document `/mnt/c/Users/jaarh/Sync/tube_amp_power.pdf` (35 pages; `rv pdf N`): p 5 output table, p 7 – 10 auxiliary supply, p 11 – 15 PFC / current measurement / EMI filter, p 16 – 22 heater LLC, p 23 – 27 DHB, p 28 – 32 FPGA control, p 33 – 34 test results and thermal. It describes the 5.1 generation (IW1818 flyback on EF20, ETD34 + external inductor DHB) |
| Project checks | `tools/next/check_next.sh` (what each step does: its own text and README "Regenerate / check"); outputs in `reports/next/` (git-ignored) |

## Common findings format

Every findings file `kicad_next/review/findings/NN_name.md` has exactly these parts:

```markdown
# Findings: NN name  (reviewer: <model>, date, commit <git rev-parse --short HEAD>)

## Summary
Three to six lines: is this part ready for ordering? The blockers, if any.

## Checklist results
| Item | Verdict | Evidence |
|---|---|---|
| A1 | PASS / FAIL / CANNOT VERIFY | file:line, or the command and the relevant output lines, or the calculation with its inputs, or datasheet (document number, revision, page / table, URL) |
| … one row per checklist item, in the order of the checklist; no item left out … |

## Findings (ranked, most severe first)
### F1 <short title>
- Severity: **blocker for ordering** / **should fix** / **note**
- What is wrong: one or two sentences, with refdes / net / coordinates
- Evidence: as above (enough for the owner to reproduce it in one command)
- Smallest fix: the least change that removes the problem (value, part, a track, a document line) – not a redesign
- Confidence: high / medium / low, and what would raise it

## Compared with 5.1
What is better, equal, worse than the 5.1 board for this part (the acceptance bar), with evidence.

## Could not verify
Items that need a measurement, a datasheet that could not be fetched, or information that is not in the repository –
and exactly what is missing.

## Outside scope
Things noticed that belong to another checklist (name it).
```

Severity: **blocker for ordering** = the board would not work, would be unsafe, or cannot be built / assembled
as it is; **should fix** = works but worse than 5.1, a rating exceeded on paper, a document that will mislead
the builder; **note** = everything else worth a line. A verdict of FAIL needs a finding; a finding may also come
from outside the checklist items.
