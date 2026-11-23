# Review checklist 14 – fabrication and assembly package for JLCPCB (`kicad_next/fab/`)

You are reviewing **one aspect** of the tube_power 5.2 power-supply board, alone, from this file and the repository
`/home/jari/dev/tube_psu_kicad`. You are doing a design review, not a redesign. **Run this checklist last**, when
the board is frozen and `kicad_next/fab/` is complete.

**Rules (full text: `kicad_next/review/README.md`, "Common rules" – read that section first):**
read-only on the repository, the only file you write is `kicad_next/review/findings/14_fab_assembly_package.md`;
no commit, no push; **do not write into `kicad_next/fab/`** and do not run `tools/next/jlc_fab.py` without
`--check` (it regenerates the package); never touch `kicad_next/tube_psu_5_2.kicad_pcb` / `.kicad_pro` and never
run a script that saves or regenerates design files (`route_s*.py`, `update_board_parts.py`, `setup_project.py` /
`make_board.py` / generators without `--check`); stop if a KiCad lock file exists (`rv guard`); RAM under 3 GB –
no full-board creepage DRC; `tools/next/check_next.sh` (2.3 GB, ≈ 2 min) only if `reports/next/drc.json` is older
than the board **and** no other KiCad job runs (`pgrep -af "kicad-cli|kipy|check_next"`); never `pkill -f`; never
run the KiCad AppImage with `--version`; the owner's name / e-mail / account stay out of web requests – **do not
upload anything to JLCPCB or any online Gerber viewer**. **Acceptance bar: match the bench-verified 5.1 board and
add creepage – do not optimise beyond that.** Manufacturer capability facts come from pages you fetch now (URL,
date), not from memory.

## 1. Scope

The board is ordered from JLCPCB as a **6-layer, 1.6 mm, FR-4, stackup JLC06161H-7628D, 1 oz outer / 0.5 oz inner,
ENIG, vias epoxy-filled and capped (via-in-pad process), no silkscreen**, 163.1 × 110.1 mm with five internal
milled slots, and assembled by JLC (**standard PCBA, both sides**; the special stackup excludes economic PCBA) from
the parts in `lib/jlc_parts_next.csv`; 33 parts are not fitted by JLC (consigned / missing / DNP: power
semiconductors, transformers, toroids, shunts, terminals, …) and are soldered by the owner. The package directory
`kicad_next/fab/` is produced by `tools/next/jlc_fab.py` (read its header) and at the time of writing contains:
six copper Gerbers (`-F_Cu.gtl`, `-In1_GND.g1`, `-In2_Signal_HV.g2`, `-In3_Power.g3`, `-In4_GND.g4`, `-B_Cu.gbl`),
mask (`.gts`, `.gbs`), paste (`.gtp`, `.gbp`), outline with slots (`-Edge_Cuts.gm1`), Excellon `-PTH.drl` /
`-NPTH.drl` with PDF drill maps, `tube_psu_5_2_gerbers.zip` (13 members), `tube_psu_5_2_bom.csv` (102 lines / 330
parts), `tube_psu_5_2_cpl.csv` (330 rows), `NOT_ASSEMBLED.md`, `README.md` (order parameters, measured limits, open
items). **The names and counts may have changed – re-read the directory.** Your job is to establish, independently
of the generator script, that this package (a) describes exactly the reviewed board, (b) is complete and
unambiguous for the manufacturer, (c) is manufacturable within JLC's published limits for the chosen options,
(d) will be assembled with the right parts in the right orientation, and (e) tells the owner everything that must
be chosen by hand on the order form and done by hand after delivery.

What a complete package for this board must contain (use as the reference list):

1. Copper Gerbers for all six layers, unambiguous layer order (file extensions / names JLC maps to L1 … L6), same
   origin and units in all files.
2. Solder mask top and bottom (vias tented or as the fill / cap process requires), **no silkscreen files**, paste
   layers (optional for the fab, used for a stencil / the PCBA).
3. Board outline including every internal slot and the L-shaped cut-out; plated and non-plated drill files
   (mounting holes NPTH), oval holes handled, drill map for people.
4. One zip for upload that holds exactly the fabrication files (no BOM / CPL / notes inside).
5. Assembly BOM (comment, designators, footprint, LCSC number) and CPL (designator, mid X / Y, layer, rotation) in
   JLC's column format, in the same coordinate frame as the Gerbers, with rotation corrections where JLC's part
   library differs from KiCad's convention – or an explicit statement that rotations must be fixed in JLC's
   placement preview.
6. A list of parts **not** assembled by JLC with the reason and who fits them, including the through-hole parts
   JLC would solder by hand at extra cost.
7. The order parameters that are chosen by hand: layers, thickness, **stackup JLC06161H-7628D**, copper weights,
   surface finish, via process, material Tg, min hole / track class, slot / milling remarks, "remove order
   number" / mark position, silkscreen none, PCBA sides, standard PCBA, tooling holes / fiducials, panel = single.
8. An assembly drawing or equivalent (no silkscreen on this board!): refdes, polarity and pin 1 for the parts the
   owner fits by hand, and the special instructions (transformer pins to cut, insulation pads, hole plugging …).
9. A statement of which checks the package passed (DRC counts, parity, the generator's own checks) and the git
   revision / board checksum it was made from.

## 2. Read first

1. `kicad_next/fab/README.md` completely, `kicad_next/fab/NOT_ASSEMBLED.md`.
2. `tools/next/jlc_fab.py` header (≈ 40 lines) and its `ROTATION_FIX` table; `tools/jlc_bom.py` (the 5.1 tool it
   follows).
3. `kicad_next/README.md` sections "Stackup", "JLC manufacturing limits", "First draft" (DRC table, "Not checked":
   via-in-pad list, tight spots), "Regenerate / check"; `tools/next/check_next.sh`.
4. Memory of decisions (README "Common rules" 6): no silkscreen; via-in-pad fine on 6 layers; stackup 7628D.
5. External (fetch): JLCPCB "PCB capabilities" (multilayer: track / space, drill, annular ring, hole-to-hole,
   slot / milling minimum, copper-to-edge, min solder-mask web, via-in-pad / epoxy fill rules, impedance stackups
   incl. JLC06161H-7628D), JLCPCB "PCB assembly capabilities" (standard vs economic, double-sided, minimum
   spacing, fiducials / tooling holes, edge rails, hand-solder THT), "How to generate Gerber and drill files in
   KiCad", "How to generate BOM and CPL", the notes on CPL rotation.

## 3. How to extract facts

```sh
kicad_next/review/tools/rv guard && kicad_next/review/tools/rv setup
ls -la kicad_next/fab/
git log --oneline -5 -- kicad_next/fab kicad_next/tube_psu_5_2.kicad_pcb lib/jlc_parts_next.csv   # was the package made after the last board / table change?
git status --short kicad_next/fab kicad_next/tube_psu_5_2.kicad_pcb lib/                          # uncommitted differences
python3 kicad_next/review/tools/fab_check.py             # independent cross-check: files, zip, age, drill vs board, outline, CPL vs board, BOM vs parts table
python3 kicad_next/review/tools/drc_summary.py           # last DRC / ERC counts and whether the report is newer than the board
python3 kicad_next/review/tools/parts_table.py board     # board fields vs parts table (the BOM is built from them)
unzip -l kicad_next/fab/tube_psu_5_2_gerbers.zip
head -30 kicad_next/fab/tube_psu_5_2-PTH.drl
grep -c "^X" kicad_next/fab/tube_psu_5_2-PTH.drl
head -12 kicad_next/fab/tube_psu_5_2-F_Cu.gtl            # X2 attributes: FileFunction, SameCoordinates, format
for f in kicad_next/fab/*.g*; do printf "%-48s " "$(basename $f)"; grep -m1 "TF.FileFunction" "$f"; done
head -5 kicad_next/fab/tube_psu_5_2_bom.csv
head -5 kicad_next/fab/tube_psu_5_2_cpl.csv
kicad_next/review/tools/rv bq slots                      # the slots that must be in the outline file
kicad_next/review/tools/rv bq nets '*' | wc -l
kicad_next/review/tools/rv bq net GND | grep vias        # via sizes in use
python3 tools/next/jlc_fab.py --check                    # regenerates into a temp dir and compares (runs kicad-cli plot jobs: only when no other KiCad job runs)
```

`fab_check.py` compares in the frame X = board x, Y = −board y. It reports, it does not judge: lines starting with
`!!` need an explanation. For anything it does not cover (mask openings, paste apertures, copper content of a
Gerber) parse the Gerber yourself in python (RS-274X is text: apertures `%ADD…`, flashes `D03`, draws `D01`,
regions `G36 / G37`) or compare against the board dump (`rv dir` → `b52.json`). Do not use online viewers.

## 4. Checklist

### A. The package describes the reviewed board

- **A1 Freshness.** `fab_check.py` section "age", `git log` / `git status` lines above. PASS: every fab file is
  newer than `tube_psu_5_2.kicad_pcb` and `lib/jlc_parts_next.csv`, all are committed, and `kicad_next/fab/README.md`
  names the git revision or board checksum it was generated from (if it does not: documentation finding –
  smallest fix: one line with `git rev-parse --short HEAD` and the board md5).
- **A2 Generator self-check.** `python3 tools/next/jlc_fab.py --check` passes (run only with no other KiCad job).
  PASS: "same content"; FAIL if the committed package differs from a fresh generation.
- **A3 Design checks behind it.** `drc_summary.py`: report newer than the board; 0 unconnected, 0 schematic-parity
  items, violations only of the documented types (courtyards_overlap 133, pth_inside_courtyard 2,
  starved_thermal 2 at the time of writing); ERC 0 errors (15 warnings: 12 isolated_pin_label + 3
  ground_pin_not_ground; the README text says 14 / 2 – known documentation mismatch). If the report is older
  than the board, run `tools/next/check_next.sh` once (rules above) and quote its last line. PASS: "ALL 5.2
  CHECKS PASSED" on the board that the package was generated from.
- **A4 Zone fills as plotted.** The generator plots zones "as stored in the board" (no refill). Are the stored
  fills current – i.e. was the board saved after the last refill, and does a refill in a copy change nothing?
  `check_board.py` refills in a temporary copy and reports violations of that copy; a difference between the
  stored and the refilled copper would mean the Gerbers show copper the DRC did not see. Evidence: the README's
  statement, or compare zone areas of the dump (`rv bq nets GND` → mm² per layer) with the numbers in
  `kicad_next/README.md` "Per layer" (GND 5653 → now 5527 mm² after later stages) – better: find in
  `tools/next/check_board.py` whether it writes the refilled copy somewhere you can dump with
  `tools/p2k/bin/kipy kicad_next/review/tools/board_dump.py COPY.kicad_pcb /tmp/copy.json` and diff the zone
  polygons. PASS: stored fill = refilled fill (area difference < 0.1 mm² per zone) or CANNOT VERIFY with the
  reason.

### B. Fabrication files

- **B1 Layer set and order.** `fab_check.py` "files"; the `TF.FileFunction` loop: Copper,L1,Top … Copper,L6,Bot in
  the files `.gtl, .g1, .g2, .g3, .g4, .gbl`. JLC's rule for inner-layer file names / order (fetch their Gerber
  guide: `.g1 / .g2 …` or `.gl2 / .gl3 …`, and that the **stack order is taken from the names, In1 = L2**).
  PASS: six copper files whose names JLC maps to L1 … L6 in the board's order F.Cu, In1.GND, In2.Signal_HV,
  In3.Power, In4.GND, B.Cu; the fab README states the layer order explicitly for the order form remark.
- **B2 No silkscreen; mask; paste.** No `.gto / .gbo` in the directory or the zip. Mask files present for both
  sides; vias tented (no mask openings on vias: count mask flashes vs pads – e.g. number of `D03` flashes in
  `.gts` ≈ number of F.Cu pads from the dump, not + 393 vias), mounting-hole rings open or covered as intended.
  Paste: no apertures on THT pads, on DNP parts (C10, C26 – are they pasted? harmless), on the 13 + 4 paste-only
  pads of LFPAK / DPAK (windowed paste) as in the footprints. PASS: as described; note what JLC does with paste
  files in the zip (ignored for fab).
- **B3 Outline and slots.** `fab_check.py` "outline" and `rv bq slots`: the profile file contains the board
  rectangle and all five internal features (ISO2 slot 1.0 × 19.5, TR1 slot 1.2 × 28, U11 slot 1.0 × 14.5, the
  heater T slot 1.0 mm wide, the L-shaped cut-out 1.2 mm wide). JLC: minimum milled slot width (fetch; typically
  1.0 mm for routed slots, 0.5 – 0.65 mm for plated drilled slots), inner corner radius, whether **non-plated
  internal slots must be drawn on the outline layer or in the drill file**, and whether such cut-outs need a
  remark on the order ("internal slots / cut-outs are intentional – creepage"). PASS: all five present as closed
  contours, widths ≥ JLC's minimum, and the fab README tells the owner to add the remark; line width of the
  outline file stated (the cut follows the line centre: 0.1 mm line → slots are as drawn).
- **B4 Drill files.** `fab_check.py` "drill": hits per diameter equal the board (582 plated, 7 non-plated at the
  time of writing), every board hole found at its position. Plus: units / format header (METRIC, decimal),
  smallest drill 0.3 mm (vias 0.5 / 0.3, 0.6 / 0.3; README limit 0.15) – finished vs drilled size convention at JLC
  (they treat the file value as finished size for PTH: fetch), annular ring of the smallest vias (0.5 − 0.3) / 2 =
  0.10 mm vs JLC's multilayer minimum (README table says 0.05 for vias; pads 0.15 – J2: 0.812 pad / 0.5 drill =
  0.156 mm), hole-to-hole spacing (J2 1.27 mm pitch, 0.5 mm drills → 0.77 mm web), NPTH 3.0 mm with a 3.5 mm
  copper ring 0.25 mm from the hole edge (JLC: copper to NPTH edge ≥ 0.2 mm?). PASS: all within the fetched
  limits; list the three tightest.
- **B5 Copper limits.** Track / space: inner layers at 0.152 mm tracks with 0.152 mm gaps (the control bus round
  DRV5), outer 0.1524 mm; JLC multilayer minimum 0.09 mm (1 oz outer), inner 0.5 oz? Copper-to-board-edge and
  copper-to-slot ≥ 0.3 mm (project) vs JLC's ≥ 0.2 – 0.3 mm for routed edges: `rv bq near` cannot measure to
  Edge.Cuts – use the `kicad_next/fab/README.md` section "Measured against the JLC limits" and verify two of its
  numbers yourself from the dump (e.g. smallest via-to-via hole distance, smallest track width:
  `rv bq nets '*'` → then `rv bq net NET` for a 0.15 mm net). PASS: every measured minimum ≥ the fetched JLC
  limit for 6 layers / 1 oz / 0.5 oz.
- **B6 Via-in-pad / filled vias.** Given decision: fine on 6 layers at JLC (filled and capped by default). Check
  only that the order parameters in the fab README select the process that makes this true for **this** stackup
  and that nothing contradicts it (e.g. "tented vias" selected in the mask files is compatible with epoxy
  fill + cap: JLC option names – fetch). PASS: README names the exact option; else documentation finding.
- **B7 Stackup and impedance.** JLC06161H-7628D exists for 1.6 mm / 6 layers / 1 oz outer + 0.5 oz inner (fetch the
  stackup table; the README quotes thicknesses "read by the user"). No controlled impedance is required – the
  order must still **select this stackup explicitly** (default for 6 layers may be another). PASS: the stackup
  code and its layer thicknesses on JLC's page equal `kicad_next/README.md` "Stackup" and the board file's stackup
  (`grep -n "thickness" kicad_next/tube_psu_5_2.kicad_pcb | head -20`).
- **B8 Fiducials, tooling, edge rails.** Double-sided PCBA at JLC needs fiducials / tooling holes or lets JLC add
  them on rails (fetch the current rule); the board has parts within ≈ 1 – 2 mm of the edges (terminals, C30)
  and no silkscreen. Does the board have fiducials (`grep -c -i fiducial kicad_next/tube_psu_5_2.kicad_pcb`)?
  PASS: the fab README says how fiducials / rails are handled ("added by JLC" with the option name), or the
  board carries three global fiducials per assembled side.

### C. Assembly files

- **C1 CPL = board.** `fab_check.py` "cpl": every row at its footprint anchor (X = x, Y = −y) on the right side;
  330 rows = BOM designators. JLC column names (Designator, Mid X, Mid Y, Layer, Rotation) and units.
  PASS: all rows match; no board-only item (H*, WP*) and no non-assembled part in the CPL.
- **C2 Anchor vs body centre.** JLC places by the part centre. The CPL uses the **footprint anchor**; for most
  KiCad SMD footprints anchor = centre, but the kept 5.1 "Proteus" footprints and custom ones may have the anchor
  on pin 1 or off-centre: for each footprint type in the CPL compare anchor (`rv bq fp REF` first line: "at
  (x, y)") with the centre of its pad bounding box (pads listed below it). List every footprint type whose
  offset exceeds 0.1 mm: candidates `SOT-23_Proteus`, `SOT-23-5_Proteus`, `SOT-23-6_Proteus`, `D_SMA_AC`,
  `D_SOD-323_AC`, `LFPAK56_Proteus`, `C_1206_3216Metric_Proteus3.15`, `R_0805_2012Metric_Proteus…`,
  `CP_Elec_6.3x7.7_EEEFTE221XAP`, `PG-DSO-12`, `TO-252-2` (anchor at the pad-pattern centre, body offset),
  `R_0508_1220Metric_KRL2012`. PASS: offsets ≤ 0.1 mm, or the CPL corrects them, or the fab README tells the owner
  to check these in JLC's placement preview (name them).
- **C3 Rotations (the generator says: NOT verified, `ROTATION_FIX` empty).** `fab_check.py` shows CPL rotation −
  board rotation = 0 for all rows. JLC's library zero-orientation differs from KiCad's for several packages
  (fetch JLC's CPL / rotation notes; typical offenders: SOT-23 family, SOIC / SOP, electrolytic SMD, diodes with
  tape orientation, DPAK, LFPAK, the SO-12) **and bottom-side parts are mirrored** (JLC expects the rotation as
  seen from the bottom? fetch their statement). Build a table per footprint type in the CPL: KiCad zero
  orientation (pin 1 where), JLC's expected zero for that LCSC part's package if documented, resulting
  correction. PASS is not achievable from documents alone: the realistic verdict is **CANNOT VERIFY →
  finding "rotations must be checked part by part in JLC's placement preview before paying; list of polarised /
  multi-pin parts to look at"** – deliver that list complete (every diode, electrolytic, IC, transistor, with
  side), sorted by JLC risk.
- **C4 BOM = parts table.** `fab_check.py` "bom": each designator's LCSC number equals the table; no part with
  status dnp / missing / consigned in the BOM; the 44 board footprints not in the BOM are exactly: 11 board-only
  (H*, WP*), 17 consigned, 14 missing, 2 DNP. JLC BOM columns (Comment, Designator, Footprint, LCSC Part #).
  PASS: as stated; `kicad_next/fab/NOT_ASSEMBLED.md` lists the same 33 parts with reasons.
- **C5 Through-hole parts in the BOM.** 24 THT parts with LCSC numbers are in the BOM (electrolytics, X / Y
  capacitors, CM chokes, J2, J4, relay): JLC solders these by hand / wave at extra cost and only if the part is
  in their THT assembly range; tall parts (45 – 50 mm cans) and the 2 × 25 1.27 mm header. PASS: the fab README
  states the owner's decision per part (JLC fits it / owner fits it) – if it only says "owner's decision", list
  it as an open item, not a failure. Check also: J2 and J4 on the **top** side with pins through to the bottom,
  where 213 SMD parts sit – wave soldering is impossible, so hand solder only: note.
- **C6 Parts on both sides, reflow order.** 93 SMD on top, 213 on bottom in the BOM. Heavy parts on the first-
  reflowed side (JLC decides; large parts on the bottom may drop): bottom-side C58 (5 × 5.4 electrolytic), SMA
  diodes (D6, D11, D18, D19, D29), 1206 / 1210 / 2220 capacitors (which side? `rv bq fp C47,C70,C99`). PASS: no
  bottom part outside JLC's double-sided assembly limits (fetch: maximum weight / size on the second side), or
  noted for the order remark.
- **C7 DNP handling.** C10, C26 (value "na"): not in the BOM, not in the CPL; the board's DNP attribute is **not**
  set on them (`parts_table.py board`) – harmless for JLC (they follow BOM / CPL) but the paste layer has their
  apertures: note only.
- **C8 Minimum order quantities and extended parts.** From the BOM: number of unique lines (102), basic vs
  extended (from the table), lines where JLC's minimum order or attrition (0402 / 0603: +N pieces) exceeds the
  stock (R124: 75 pcs; CM1 / CM4: 20). PASS / list for the owner.

### D. Human-facing documentation in the package

- **D1 Order parameters complete.** `kicad_next/fab/README.md` "Order parameters to select by hand": compare with
  item 7 of the reference list in section 1 and with JLC's current order form fields (fetch a description of
  the form or their capability page): base material FR-4 Tg (which? TG155 is standard for 6 layers), layers 6,
  dimensions 163.1 × 110.1, quantity, thickness 1.6, **impedance control: yes → JLC06161H-7628D**, outer copper
  1 oz, inner 0.5 oz, via covering (epoxy filled & capped), surface finish ENIG (thickness option), **silkscreen
  none / colour irrelevant**, solder-mask colour, min via hole / track class, gold fingers no, castellated no,
  edge plating no, "confirm production file" yes, mark on PCB: remove / specify location (**no silkscreen → where
  does JLC put the order number?** – the "remove mark" option). PASS: every field that affects the product is
  given a value; list missing ones.
- **D2 Remarks for the fab.** Internal slots are intentional (creepage) and must not be plated; non-plated mounting
  holes with copper rings; no silkscreen on purpose; layer order; vias in pads are intentional. PASS: a
  ready-to-paste remark text exists in the README, or finding with the text to add.
- **D3 Assembly drawing without silkscreen.** The owner fits ≈ 33 + parts by hand (and reworks) on a board with no
  refdes or polarity marks. Is there an assembly drawing (PDF / SVG of F.Fab + B.Fab with refdes, polarity,
  pin 1) in the package or elsewhere (`ls kicad_next/fab`, `git ls-tree -r --name-only origin/renders`)? The
  board's F.Fab / B.Fab layers exist (`grep -c "F.Fab" kicad_next/tube_psu_5_2.kicad_pcb`). PASS: a drawing for
  both sides is part of the package; otherwise **should fix**: generate one (kicad-cli pcb export pdf / svg of
  the Fab layers – by the owner, not by you).
- **D4 Hand-assembly instructions.** One place that lists, for the owner: the 33 non-assembled parts with their
  orientation source; TR3 – cut the unused bobbin pins (only pins 4, 5, 7 – 12 have holes); TR1 – pins 4 / 6
  clipped, fly leads to pads 11 / 12; TR2 secondary to wire pads WP1 – WP4; insulation pads / FullPAK notes for
  the heatsink line; L1 / L2 upright with a hold-down; the heatsink is fitted before soldering the TO parts;
  shunt value actually fitted (4 mΩ vs 5 mΩ); the J4 pinout (no silk!); the UART warning. PASS: exists (name the
  file); else documentation finding with the list above as the smallest fix.
- **D5 Open items carried by the package.** The fab README's "Open items before ordering" must include everything
  the other review findings classify as **blocker for ordering** (read `kicad_next/review/findings/*.md` if
  present and list the blockers) plus its own: missing-part decisions, stock not read, rotations not verified,
  heatsink / mechanical confirmations (README "Still to confirm with calipers": EEL19 and EC42 bobbin pin
  diameters and outlines – **a wrong drill for a transformer pin is not fixable after fabrication**), J2 mating
  height, C86 / C117 / C38 body sizes. PASS: every such item is in the list or closed with evidence.
- **D6 5.1 comparison.** How was 5.1 ordered (STATUS.md / `tools/jlc_bom.py` / `source/cadcam`)? Differences that
  matter to the fab: 4 → 6 layers, stackup, slots, filled vias, no silkscreen, bottom-side SMD count. Note only.

### E. Final go / no-go list (deliverable)

- **E1** In the findings summary give a single ordered list: (1) what blocks uploading the Gerbers, (2) what
  blocks the PCBA order but not the bare-board order, (3) what the owner must do in JLC's web preview (rotations,
  stackup selection, remarks), (4) what must be bought / measured before the boards arrive.

## 5. Out of scope / given

- Whether the board is electrically right (checklists 01 – 12) and whether the parts are right (13) – here only that
  the package transmits the reviewed design faithfully and completely.
- Given: JLCPCB as manufacturer; JLC06161H-7628D; ENIG; no silkscreen (do not ask for one – ask for an assembly
  drawing instead); via-in-pad with JLC's default fill / cap on 6 layers is fine (do not list the 71 vias in
  pads); standard PCBA both sides; power parts consigned / hand-fitted.

## 6. Findings format

Write `kicad_next/review/findings/14_fab_assembly_package.md` exactly in the format of
`kicad_next/review/README.md` "Common findings format": summary (with the E1 list); one table row per item above
(A1 … E1) with **PASS / FAIL / CANNOT VERIFY** and the evidence (file:line, command + output lines, calculation
with inputs, or manufacturer page with URL and date); ranked findings with severity (**blocker for ordering /
should fix / note**), what is wrong, evidence, smallest fix, confidence; "Compared with 5.1"; "Could not verify";
"Outside scope". "Looks fine" without evidence is not acceptable.
