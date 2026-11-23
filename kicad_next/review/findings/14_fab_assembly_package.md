# Findings: 14 fab_assembly_package  (reviewer: Claude Opus 5.5, 2026-11-23, commit 01a1adf)

## Summary
The package faithfully describes the reviewed board: `jlc_fab.py --check` reports "up to date (19 files)", the drill
hits, CPL positions and BOM all match the board and the parts table, and the fab files are newer than the board
(md5 `ab69e7f12f06492d72e78d6bd49cb22b`, committed). The **bare-board Gerbers can be uploaded** once the
transformer pin drills are confirmed with calipers (F2). The package does not say this; the fact is in
`kicad_next/README.md` only. **The PCBA order is not ready**. Rotations are raw KiCad angles and have not been
checked. JLC's own engineers check polarity against the silkscreen, and this board has none (F1). Fiducials and rails
are required for standard PCBA and are not addressed (F4). There is no assembly drawing and no hand-assembly sheet
(F5). The three 1.0 mm slots meet JLC's nominal minimum, but JLC's ±0.2 mm tolerance can make them narrower than the
1 mm creepage groove width (F3).

**E1 go / no-go list**
1. Blocks uploading the Gerbers: (a) measure the EEL19 (TR1, drills 1.0 / 0.9 mm) and EC42 (TR3, drill 1.2 mm) bobbin
   pin diameters, because a wrong drill cannot be fixed after fabrication (F2). (b) The owner should decide about the
   1.0 mm slots (F3) and the NPTH copper rings (F6) before the file is final. Neither is a hard blocker.
2. Blocks the PCBA order but not the bare-board order: rotation / polarity check of all 67 polarised or multi-pin
   parts (F1, list below); fiducial / edge-rail option (F4); missing-part decisions (14 parts) and the stock of
   C105987 / C492405; the THT-by-JLC decision for 24 parts.
3. In JLC's web preview / order form: select stackup JLC06161H-7628D; outer 1 oz / inner 0.5 oz; ENIG; epoxy filled &
   capped vias; silkscreen none; "remove order number"; edge rails + fiducials "added by JLCPCB"; paste the remark
   text from F7; check every part in the F1 list in the placement preview, including the bottom side and the anchor
   offsets of the THT parts / TO-252 / LFPAK (F8).
4. Buy or measure before the boards arrive: the consigned and missing parts (NOT_ASSEMBLED.md, 33); 4 mΩ vs 5 mΩ shunt
   decision; caliper items of `kicad_next/README.md:2073`; an assembly drawing for the hand-fitted parts (F5).

## Checklist results
| Item | Verdict | Evidence |
|---|---|---|
| A1 | FAIL (documentation only) | `fab_check.py` "age": "every fab file is newer than the board and the parts table". Fab files 2026-11-23 20:48; board 19:32:34; `jlc_parts_next.csv` 19:32:26. `git status` shows no difference in fab/, board or lib/. Last commits: board `ecf0024`, fab `7413e4a`. **But** `kicad_next/fab/README.md` names neither a git revision nor the board checksum (F9) |
| A2 | PASS | `python3 tools/next/jlc_fab.py --check` → "jlc_fab: kicad_next/fab/ up to date (19 files)", exit 0, 6.9 s, max RSS 288 MB |
| A3 | PASS | `drc_summary.py`: drc.json 2026-11-23T20:35 is "newer than its source (ok)", KiCad 10.0.7. Violations 137 = courtyards_overlap 133 + pth_inside_courtyard 2 + starved_thermal 2. unconnected 0, schematic_parity 0. ERC: 0 errors, 15 warnings. I did not rerun `check_next.sh` (the report is current; caller's instruction) |
| A4 | CANNOT VERIFY | No refill was done (it would be a KiCad job; three other reviewers run in parallel). Mitigation: `tools/next/check_board.py:76-77` calls `kicad-cli pcb drc` **without** `--refill-zones`, so the DRC checked the stored fill. The generator also plots the stored fill (`jlc_fab.py` header). The Gerbers therefore show the copper the DRC saw. Note: the checklist says check_board "refills in a temporary copy"; it copies the board, it does not refill |
| B1 | PASS | `TF.FileFunction` loop: gtl Copper,L1,Top; g1 L2,Inr; g2 L3,Inr; g3 L4,Inr; g4 L5,Inr; gbl L6,Bot (fab README table lines 27-32, `jlc_fab.py` LAYERS). JLC "Suggested naming patterns" (https://jlcpcb.com/help/article/suggested-naming-patterns, fetched 2026-11-23): GTL / GBL / GTS / GBS / GKO-GM1, and ".G1 and .G2 files … for internal signal layers". **No JLC page fetched states how the order of more than two inner layers is derived.** The X2 L2…L5 attributes and the numeric suffixes agree, so there is no ambiguity, but a layer-order line belongs in the remark (F7) |
| B2 | PASS | No .gto / .gbo in the directory or the zip (13 members: 6 Cu, 2 mask, 2 paste, gm1, 2 drl). Mask flashes = copper pads exactly: F 262 SMD + 196 THT/NPTH = 458 = `.gts` flashes; B 534 + 196 = 730 = `.gbs` flashes. Only 2 of 393 via centres coincide with a mask opening (vias in pads), so the vias are tented. Paste: 0 THT pads have paste. F paste 292 = SMD pads + windowed LFPAK / DPAK apertures; B paste 534 = 534 SMD pads. C10 / C26 pads (top) **have paste** (note, F10). JLC makes its own stencil for PCBA (fab README line 12) |
| B3 | PASS (with F3) | `Edge_Cuts.gm1`: rectangle (0.1 mm line) + 5 closed internal contours (0.05 mm line): L cut-out 1.2 mm (x 50.815–52.015 / y 39.2–40.4), ISO2 1.0 × 19.5, TR1 1.2 × 28.0, U11 1.0 × 14.5, ISO1 T slot 1.0. `rv bq slots` gives the same features. JLC capabilities (https://jlcpcb.com/capabilities/pcb-capabilities, fetched 2026-11-23): "The minimum Non-Plated Slot Width is 1.0mm, please draw the slot outline in the mechanical layer (GM1 or GKO)" → correct layer, widths ≥ min. Same page: "Non-plated: ±0.2mm" slot tolerance (F3) and "Rectangular holes and slots without rounded corners are not supported" (the L cut-out and the T junction have square corners; the router rounds them, harmless, note). Fab README open item 7 tells the owner to add the remark |
| B4 | FAIL (NPTH ring only) | `fab_check.py` drill: 582 / 582 PTH and 7 / 7 NPTH at their positions, per-diameter counts equal. Headers: `METRIC`, `FORMAT={-:-/ absolute / metric / decimal}`. JLC page (same URL/date): multilayer drill 0.15–6.3 mm, tolerance +0.13/−0.08; "Via diameter should be 0.1mm (0.15mm preferred) larger than Via hole size"; PTH annular ring multilayer "absolute minimum 0.15 mm"; via hole-to-hole 0.2 mm; pad hole-to-hole 0.45 mm; "NPTH pad annular ring ≧0.45mm"; "NPTH to Track 0.2mm". Three tightest (from b52.json): **J2 annular ring 0.156 mm** (0.812 / 0.5) vs 0.15; **via 0.5/0.3 ring 0.10 mm** (dia − hole = 0.2 vs 0.1 required); **via-via hole edge 0.335 mm** (ISO_GND vias at (82.174, −36.532)/(81.666, −36.913)) vs 0.2. Pad hole-to-hole 0.769 mm (J2.35/J2.37) vs 0.45. **NPTH: H1–H8 rings 3.5 mm on 3.0 mm holes = 0.25 mm, no net, all six layers (`rv bq fp H1`) vs ≥ 0.45 mm** (F6) |
| B5 | PASS | Own check from b52.json: narrowest track 0.15 mm (8 B.Cu + 3 F.Cu + 26 In2 = 37 segments, same as the README). JLC "Multilayer: 0.09 / 0.09 mm"; the page gives no separate 0.5 oz inner-layer value, and 0.15 is 1.7 × the published figure. Copper to routed edge 0.3 mm (README) vs "≧0.2 mm" (same page). Min gap 0.15 mm (README table) vs 0.09 |
| B6 | PASS | Fab README line 77: "epoxy filled and capped, JLC's default on 6 layers". JLC page: "This process is the default for 6-layer and above multilayer boards"; option names "Epoxy Filled & Capped" / "Copper paste Filled&Capped" / "Plugged". Tented mask openings do not conflict with it |
| B7 | PASS | JLC impedance page (https://jlcpcb.com/impedance, fetched 2026-11-23) lists JLC06161H-7628D: Cu 0.035, 7628 ×2 0.218 + 0.2104, core 0.2, 7628 0.2028, core 0.2, 7628 ×2 0.2104 + 0.218, Cu 0.035. Equal to `kicad_next/README.md:2092-2106` and the board stackup (`tube_psu_5_2.kicad_pcb:56-112`: 0.035 / 0.4284 / 0.0152 / 0.2 / 0.0152 / 0.2028 / 0.0152 / 0.2 / 0.0152 / 0.4284 / 0.035). The fab README says the stackup must be selected explicitly (line 72) |
| B8 | FAIL | `grep -c -i fiducial kicad_next/tube_psu_5_2.kicad_pcb` → 0. JLC PCBA capabilities (https://jlcpcb.com/capabilities/pcb-assembly-capabilities, fetched 2026-11-23): Standard PCBA "Fiducials: Necessary", "Edge Rails: Necessary". JLC help (https://jlcpcb.com/help/article/how-to-add-edge-rails-fiducials-for-pcb-assembly-order): "Edge rails and fiducials are required for standard PCB assembly"; rail ≥ 5 mm; boards ship with rails unless removal is paid. JLC assembly T&C (https://jlcpcb.com/help/article/terms-and-conditions-of-jlcpcb-assembly-service) §5.5: "Tooling holes, Edge rails and Fiducials are required … we will help to add or modify them by default"; DFM note 3: component body ≥ 2.5 mm from the board edge. On this board, 14 placed parts have their courtyard closer than 2.5 mm (J4 0.53, RL1 1.35, C30 1.38, C19 1.46, R143 1.60 mm …). The fab README only lists "tooling holes" as "owner's choice" (line 85) (F4) |
| C1 | PASS | `fab_check.py` cpl: "330 of 330 CPL rows at the board footprint anchor (X = x, Y = −y) on the right side". Columns Designator, Mid X, Mid Y, Layer, Rotation; Layer Top 117 / Bottom 213. JLC "pick-place-file-for-pcb-assembly" (fetched 2026-11-23): those columns, mm, positive rotation counter-clockwise, "Top / Bottom". No H*/WP* or not-assembled part in the CPL |
| C2 | FAIL (documentation) | JLC defines Mid X/Y as "the component centroid" (same page). Offset of the anchor from the **pad bounding-box centre** (own script on b52.json, > 0.05 mm): every THT part (anchor = pin 1): J2 15.25, C86/C117/C38 11.25, J4 6.35, C64/C66 5.0, C65… 3.75, CP_Radial D12.5/D10 2.50, D8 1.75 mm; SMD **TO-252-2 (Q10, Q11) 0.84 mm**, **LFPAK56_Proteus (Q1, Q2) 0.36 mm**. The fab README's list (line 179: PWM2 0.42, SOT-23(-5)_Proteus 0.23–0.31 mm) comes from a mean-of-pad-centres method. By bounding box those parts are centred (PWM2 pads x 45.355…54.245 → centre 49.80 = anchor; Q9 pads x −63.547/−61.642 → centre −62.59 vs anchor −62.60). So the list names parts that are fine and leaves out the ones that are off (F8) |
| C3 | CANNOT VERIFY | `fab_check.py`: CPL − board rotation = 0 for all 330. JLC FAQ part 2 (https://jlcpcb.com/help/article/39-pcb-assembly-faqs-part-2, fetched 2026-11-23): "our engineers will review and fix the rotation and polarity"; "Zero orientation for PCB library should match the component orientation in the packaging (tape/reel)"; FAQ 10: "we will judge them according to your silk layer". **None of the fetched JLC pages states the bottom-side convention.** The Proteus-numbered footprints have the same **geometry** as the KiCad standard at 0° (Q9 / REF1 SOT-23: two pads at −x, single pad at +x; U2 SOT-23-5: pads 1-3 in the −x column; D_SMA_AC / D_SOD-323_AC: cathode pad "C" at −x at 0°, like KiCad pad 1 = K; C1 CP_Elec pad 1 (+) at −x; C58 standard). The same corrections as for standard KiCad footprints therefore apply, but only the pad *names* differ (A/C, Proteus 1/2/3), which can mislead someone who reads pin numbers. Full risk list in F1 |
| C4 | PASS | `fab_check.py` bom: 102 lines, 330 designators, columns Comment / Designator / Footprint / LCSC Part #. Not in BOM: 11 board-only + 17 consigned + 2 dnp + 14 missing = 44, as required. `NOT_ASSEMBLED.md` lists the same 33 parts with reasons. `parts_table.py board`: "0 field difference(s)" |
| C5 | PASS (open item) | Fab README lines 145-163: 24 THT parts / 107 pins, decision = "owner's decision" (open item 6). J2 / J4 / RL1 / all THT are on top; 213 SMD sit on the bottom. JLC's FAQ says THT is wave-soldered, which is not possible over a populated bottom side, so expect hand / selective soldering (note) |
| C6 | CANNOT VERIFY | The fetched JLC PCBA pages give no weight / size limit for second-side parts. Bottom-side large parts in the CPL: C58 (CP_Elec_5x5.4), D6 D11 D18 D19 D29 (SMA), DRV3 DRV5 DRV6 (SOIC-16W), C15 C70 C99 C100 C101 (1210). All are small SMD; none is heavy by usual reflow-on-underside standards (not a JLC-sourced fact) |
| C7 | PASS (note) | `parts_table.py board`: "C10: DNP attribute on the board False vs table status 'dnp'", same for C26. Both are absent from BOM / CPL. Their top paste apertures exist (B2) → solder bumps on bare pads (F10) |
| C8 | PASS (list) | `parts_table.py`: not read C105987 (C22 C41 C42 C49) and C492405 (J4). Low: C17699638 PWM2 public stock 3 (10 bought into the owner's private stock), C1534140 CM1/CM4 20, C245506 R124 75, C913388 C19/C30 103. Basic 38 / extended 64 LCSC numbers (fab README line 138). The extended loading fee applies per extended number |
| D1 | FAIL | Fab README lines 67-85 give layers, size, thickness, stackup, copper, finish, silkscreen, via covering, slots, track / hole class, PCBA. **Missing values:** material Tg (JLC page names no standard Tg; give the value the form offers or "default"); edge rails / fiducials (F4); "remove order number" left open ("check what JLC offers"); gold fingers / castellated / edge plating = no; confirm production file (recommend **yes** because of the rotation risk). The order-form field list itself could not be fetched (JS page) |
| D2 | FAIL | There is no ready-to-paste remark. README line 76 says "tell JLC in the order remark" and open item 7 says "confirm in the order remark", but the text itself is not given (F7) |
| D3 | FAIL | `ls kicad_next/fab` has no assembly drawing. `git ls-tree origin/renders` for tube_psu_5_2 holds only 3D PNGs and copper SVGs. The board has F.Fab / B.Fab content (`grep -c F.Fab` → 1091). 5.1's CADCAM had "Top Assembly.GBR" / "Bottom Assembly.GBR" (`source/cadcam/… READ-ME.TXT`), so 5.2 is worse than 5.1 here (F5) |
| D4 | FAIL | No single hand-assembly sheet. `NOT_ASSEMBLED.md` gives status / reason only. TR1 pins 4 / 6 clipped is only in `CHANGES_5_2.md:18`; TR3 unused bobbin pins, TR2 → WP1–WP4, insulation pads, heatsink-before-soldering, J4 pinout and the UART warning are not in fab/ (F5) |
| D5 | FAIL | Fab README "Open items" 1-12 cover missing parts, stock, rotations, THT, slots, annular ring, NPTH ring, silkscreen and stackup. **Missing:** the caliper items of `kicad_next/README.md:2073-2078` (EEL19 pin diameter vs drills 1.0 / 0.9 mm, EC42 pin diameter vs drill 1.2 mm, seated heights, core-plate clearance), which are not fixable after fabrication (F2). No other findings files existed in `kicad_next/review/findings/` when I read the directory, so I carried no blockers from other reviews |
| D6 | PASS (note) | See "Compared with 5.1" |
| E1 | PASS | Delivered in the Summary |

## Findings (ranked, most severe first)

### F1 Rotations and polarity are unverified, and JLC's polarity check needs a silkscreen this board does not have
- Severity: **blocker for ordering** (PCBA only, procedural: must be done in JLC's placement preview before paying; the bare board is not affected)
- What is wrong: the CPL carries raw KiCad angles (`ROTATION_FIX` empty, CPL − board = 0 for 330 rows), including the
  213 bottom-side parts. No JLC page I fetched states the bottom-side rotation convention. JLC's FAQ says engineers
  judge polarity "according to your silk layer", and there is none, so the engineer review has nothing to compare
  against. Only the owner's preview check stands between a wrong angle and a dead board.
- Evidence: `python3 kicad_next/review/tools/fab_check.py` → "{0: 330} … no JLC rotation corrections applied";
  https://jlcpcb.com/help/article/39-pcb-assembly-faqs-part-2 (FAQ 2, 3, 10), fetched 2026-11-23.
- The list to check in the preview, sorted by JLC risk (side, KiCad rotation):
  1. SOT-23 family, Proteus pad names (geometry = KiCad standard): AD1 B 270, AD2 B 0 (SOT-23-6_Proteus); U2 B 0, U3 B 90, U6 B 180, U8 B 0, U9 B 270, V2 B 90, V3 B 0, V4 B 180 (SOT-23-5_Proteus / SOT-23-5); Q9 B 0, REF1 B 0 (SOT-23_Proteus, single pad = Proteus "1"); DRV1 B 270, DRV2 B 180 (SOT-23-6).
  2. Gate drivers / isolators / ICs: DRV3 B 90, DRV5 B 0, DRV6 B 180 (SOIC-16W); ISO1 T 180, ISO2 T 0, U11 T 0 (SOIC-16W slot); DRV4 T 90 (SOIC-8); PWM2 T 270 (PG-DSO-12, pins 6–7 gap); U1 B 90, U4 B 0 (TSSOP-8); U10 B 90 (VSSOP-8).
  3. Power SMD: Q1 T 270, Q2 T 90 (LFPAK56_Proteus, pads "1,1,1,2,3"); Q10 T 270, Q11 T 270 (TO-252-2, anchor 0.84 mm off).
  4. Diodes (cathode pad "C" at −x at 0°): SMA: D4 T 180, D5 T 270, D7 T 0, D8 T 0, D14 T 0, D6 B 0, D11 B 180, D18 B 0, D19 B 0, D29 B 180; SOD-323: D10 T 180, D2 B 90, D3 B 180, D9 B 90, D28 B 90, D30 B 270, D31 B 180, D32 B 180, D33 B 180, D34 B 0, D35 B 90.
  5. Electrolytics: C1 T 0, C2 T 270 (CP_Elec_6.3x7.7), C58 B 90 (CP_Elec_5x5.4); radial THT C19 T 180, C30 T 0, C28 C29 C37 C56 T 0, C31 C32 T 0, C102 T 90.
  6. THT multi-pin: J2 T 0 (2×25, pin 1 end), J4 T 0 (1×6, pin 1 = GND), RL1 T 0, CM1 CM4 T 0.
- Smallest fix: before paying, check each line above in JLC's preview on both sides. Enter only verified offsets into
  `ROTATION_FIX` and regenerate. Choose "confirm production file: yes" so the final placement image comes back for
  approval. A board-side alternative is a polarity mark on F.Fab/B.Fab plus a "Fab layers as silkscreen" PDF uploaded
  with the order; this is the owner's decision.
- Confidence: high that the check is needed (JLC's FAQ text). Medium on bottom-side behaviour (JLC does not publish it).

### F2 Transformer pin drills are not confirmed and the package's open items do not mention them
- Severity: **blocker for ordering** (bare board: a wrong drill cannot be fixed after fabrication)
- What is wrong: `kicad_next/README.md:2073-2078` says "Still to confirm with calipers": EEL19 (TR1) pin diameter
  for drills 1.0 / 0.9 mm and the base outline; EC42 (TR3) pin diameter for drill 1.2 mm, seated height, and core-plate
  clearance ≥ 4 mm at the secondary pins. None of this is in `kicad_next/fab/README.md` "Open items" (1-12), which is
  the document the owner will order from.
- Evidence: `rv section kicad_next/README.md 'Stackup'` region, lines 2073-2078; fab README lines 181-219.
- Smallest fix: add one open item to the fab README / generator text: "measure EEL19 and EC42 bobbin pins (drills
  1.0 / 0.9 / 1.2 mm) and the EC42 core-plate height before upload".
- Confidence: high that the item is missing; whether the drills are actually wrong is unknown.

### F3 Three slots are exactly 1.0 mm; JLC's tolerance is ±0.2 mm and 1 mm is the creepage groove width
- Severity: **should fix**
- What is wrong: the ISO2 slot (1.0 × 19.5), U11 slot (1.0 × 14.5) and ISO1 T slot (1.0) equal JLC's minimum
  non-plated slot width, and JLC states "Non-plated: ±0.2mm". A slot that comes out 0.8 mm is narrower than X = 1.0 mm
  (IEC 60664-1, PD2; the board's creepage basis is PD2, `kicad_next/README.md:2144-2147`). Across a groove narrower
  than X, creepage is counted straight across, so the slot's creepage credit at the isolators is not guaranteed.
  The TR1 slot and the L cut-out are 1.2 mm.
- Evidence: `Edge_Cuts.gm1` (X−500000…X500000 = 1.0 mm U11; X66257000…X67257000 = 1.0 mm ISO2; X−42859000…X−41859000 =
  1.0 mm ISO1); https://jlcpcb.com/capabilities/pcb-capabilities fetched 2026-11-23: "minimum Non-Plated Slot Width is
  1.0mm", "Non-plated: ±0.2mm", "±0.1mm(Precision) and ±0.2mm(Regular) for CNC routing". The IEC X value is from the
  general rule, not from a copy of the standard fetched now.
- Smallest fix: widen the three slots to 1.2 mm (the same width already used for TR1 / L). Checklist 10 must confirm
  the pads and creepage paths still fit. The alternative is a remark "slots 1.0 mm minimum finished width, do not
  narrow".
- Confidence: medium. JLC's figure is a width tolerance for non-plated slots; how the router performs in practice
  (tool = 1.0 mm) is not documented. Whether the design needs the slot as a groove credit is checklist 10's call.

### F4 Fiducials / edge rails: required for standard PCBA, the board has none, the README does not say how they are handled
- Severity: **should fix** (documentation; JLC adds them by default)
- What is wrong: 0 fiducials on the board. JLC requires fiducials and rails for standard PCBA and adds them by default
  if missing (T&C §5.5). 14 placed parts are < 2.5 mm from the edge (J4 0.53 mm, RL1, C30, C19, bottom R143 / R151 /
  R152 / R156 …), so rails are needed anyway. Rails change the delivered size (+≥ 5 mm per railed side) and stay
  on unless removal is paid. The fab README lists only "tooling holes … owner's choice".
- Evidence: B8 row (URLs, fetched 2026-11-23); own edge-distance script on b52.json (courtyard box to outline box).
- Smallest fix: one row in "Order parameters": "Edge rails / fiducials: added by JLCPCB (board has none; parts within
  2.5 mm of the edge); rails stay on unless removal is ordered". Board-side global fiducials would need 3.35 mm of
  free edge and are not required.
- Confidence: high.

### F5 No assembly drawing and no hand-assembly sheet for a board without silkscreen
- Severity: **should fix**
- What is wrong: about 33 hand-fitted parts plus rework, with no refdes, polarity or pin-1 marks on the board and no
  F.Fab / B.Fab plot in the package. 5.1's CADCAM shipped Top / Bottom Assembly Gerbers. Hand-assembly notes (TR1 pins
  4/6 clipped, TR3 unused bobbin pins, TR2 to WP1-WP4, insulation pads, heatsink before soldering the TO parts, J4
  pinout, UART warning, 4 vs 5 mΩ shunt) are spread over CHANGES_5_2.md / README or missing.
- Evidence: D3 / D4 rows.
- Smallest fix: the owner exports F.Fab+Edge.Cuts and B.Fab+Edge.Cuts (mirrored) PDFs with `kicad-cli pcb export pdf`
  into fab/ (outside the zip), and adds a short "HAND_ASSEMBLY.md" with the list above.
- Confidence: high.

### F6 NPTH mounting-hole copper rings 0.25 mm vs JLC's 0.45 mm
- Severity: **should fix** (low impact)
- What is wrong: H1 H2 H3 H4 H6 H7 H8 (`MountingHole_3.0mm_NPTH_Ring3.5mm`) have a 3.5 mm no-net copper pad on a 3.0 mm
  NPTH on all six layers, a 0.25 mm ring. JLC asks "NPTH pad annular ring ≧0.45mm" (room for the sealing film) and
  "NPTH to Track 0.2mm". JLC is likely to pull the copper back or query it. A pull-back of 0.2 mm would leave a 0.05 mm
  sliver, and a loose sliver on an HV board is unwanted debris. Electrically nothing depends on the ring (no net; the
  screw head bonds to the chassis; the isolation rule measures from the hole), so losing it is harmless.
- Evidence: `rv bq fp H1` → "3.5x3.5 drill 3.0 NPTH all Cu []"; https://jlcpcb.com/capabilities/pcb-capabilities
  fetched 2026-11-23.
- Smallest fix: use a ring-less `MountingHole_3.0mm` footprint (copper-free), or enlarge the pad to ≥ 3.9 mm if
  checklist 10 accepts the 0.2 mm smaller hole clearance. Otherwise add to the remark: "copper rings at the 3.0 mm
  NPTH may be removed".
- Confidence: medium (JLC's handling is not documented beyond the limit).

### F7 No ready-to-paste order remark
- Severity: **should fix**
- What is wrong: several items depend on the remark (slots, no silkscreen, NPTH, layer order, vias in pads), but no
  text exists. Proposed text:
  "6-layer, stackup JLC06161H-7628D. Layer order: GTL = L1, G1 = L2, G2 = L3, G3 = L4, G4 = L5, GBL = L6. No silkscreen
  on purpose (no silkscreen files). The 5 internal milled cut-outs in GM1 are intentional creepage slots: non-plated,
  do not plate or narrow; 3 are 1.0 mm wide. 7 non-plated 3.0 mm mounting holes. Vias in SMD pads are intentional:
  epoxy filled and capped. Please remove the order number (no silkscreen)."
- Evidence: fab README lines 76, 213, 215 refer to a remark without giving it.
- Smallest fix: add the text to the README generator.
- Confidence: high.

### F8 The README's "anchor off centre" list is wrong
- Severity: **should fix** (documentation; it points the preview check at the wrong parts)
- What is wrong: the list (README line 179) uses the mean of pad centres. By pad bounding box, PWM2 and the
  SOT-23(-5)_Proteus parts are centred. The real offsets are TO-252 Q10 / Q11 0.84 mm, LFPAK Q1 / Q2 0.36 mm, and all
  24 THT parts (anchor = pin 1, up to 15.25 mm for J2). JLC wants the "component centroid".
- Evidence: C2 row; own script on b52.json.
- Smallest fix: compute the offset from the pad bounding box (or the courtyard centre) in `jlc_fab.py` and name these
  parts; optionally correct the CPL to the bounding-box centre.
- Confidence: high for the numbers. How much JLC's engineers already correct THT anchors is unknown.

### F9 Package does not name its source revision / board checksum
- Severity: **note**
- Smallest fix: one README line "made from commit `ecf0024`, board md5 ab69e7f12f06492d72e78d6bd49cb22b".
- Confidence: high.

### F10 C10 / C26 (dnp) not flagged DNP on the board; pasted pads
- Severity: **note**
- What is wrong: they are not in the BOM / CPL (correct for JLC, which follows the BOM / CPL), but the board's DNP
  attribute is False, and their top paste apertures are in `.gtp` (pads at (35.475/33.925, −10.0) and
  (27.6, −2.875/−1.325) Gerber frame). Result: solder bumps on bare pads, harmless.
- Smallest fix: set the DNP / exclude-from-BOM / exclude-from-position attributes (only via the project's generator, not
  by hand). Paste can stay.
- Confidence: high.

### F11 BOM merges designators per LCSC number (16 lines with two or more texts per cell)
- Severity: **note** (acceptable)
- What is wrong: e.g. `0603WAF1000T5E / 100R / 100` and footprint `R_0805_…HandSolder / R_0805_…Proteus`. JLC rules
  (https://jlcpcb.com/help/article/advice-for-bom-and-cpl-files-preparation, fetched 2026-11-23): each designator only
  once (met), ≤ 200 designators per line (max here 21), and "If multiple different values or specifications exist
  under the same BOM designation, please carefully verify the details". So mixed texts are anticipated, not
  forbidden. Matching is by LCSC number (JLC KiCad guide). One risk: T&C §4.2 says "If the component in the BOM does not
  match the footprint, this part will not be populated", so in every one of the 16 lines all variants are the same
  package (0603 / 0805 / 1206 / SOT-23-5 / SOIC-16W / radial D12.5).
- Smallest fix: none needed; optionally write the plain package ("0805") in the Footprint column.
- Confidence: medium (JLC's BOM import behaviour itself not tested).

## Compared with 5.1
- 5.1 (Proteus CADCAM, `source/cadcam/tube_power_5_1_X2 - CADCAM READ-ME.TXT`): 4 layers, silkscreen top / bottom,
  **Top / Bottom Assembly** Gerbers and an IPC netlist. KiCad 5.1 board: 0 fiducials, as on 5.2.
- 5.2: 6 layers, a special stackup (standard PCBA only), 5 milled slots, filled / capped vias, no silkscreen, 213 bottom
  SMD. **Better:** independent self-check (`--check`), drill / CPL / BOM cross-checked against the board, explicit
  measured-limits table. **Worse:** no assembly drawing (F5) and no silk reference for JLC's polarity review (F1).
  **Equal:** no fiducials (F4); rotations unverified in both (`tools/jlc_bom.py` `ROTATION_FIX` is also empty, STATUS.md:1506).

## Could not verify
- A4: stored zone fill vs refill. Needs a refill in a copy (KiCad job), which I skipped with other reviewers running.
- C3: JLC's bottom-side rotation convention and the zero orientation of each LCSC part's model. No JLC page states it;
  only the placement preview shows it.
- C6: JLC's size / weight limits for second-side parts. Not published on the fetched pages.
- B1: how JLC orders more than two inner layers. Not stated on the fetched pages (the remark in F7 closes this).
- D1: JLC's current order-form field list (JS page; not fetched); Tg / ENIG thickness options not published on the
  capabilities page.
- F3: JLC's real slot router tool and achieved width; the IEC X = 1 mm value is from the general rule, not from the
  standard fetched now.
- Whether the Gerbers import cleanly in JLC's viewer / DFM (not uploaded, by rule).

## Outside scope
- C1 `CP_Elec_6.3x7.7_EEEFTE221XAP` pads print as 0.65 × 2.7 mm in `rv bq fp C1`, which is unusually narrow for a
  6.3 mm electrolytic. Checklist 13 should look at the footprint against the Panasonic land pattern.
- The slot-width / groove credit (F3) and the NPTH ring (F6) also concern checklist 10.
- The checklist text says check_board.py refills zones in its copy; it does not (`check_board.py:76-77`). Fix the
  README / checklist wording.
