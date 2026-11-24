# Findings: 12 thermal and mechanical  (reviewer: Claude Opus 5.5, 2026-11-24, commit fdae703)

## Summary
The copper board can be ordered from a thermal / mechanical point of view: every part fits the outline. Holes, J2 and the
tall parts are where they were on 5.1, and no part is taller than the 50 mm of 5.1. There is no blocker in the copper.
The **primary heatsink is not buildable as one flat plate yet**, and the decision has a board option, so it should be
made before ordering:

1. The east row (Q6, SICD1, Q19, Q7) does not have coplanar tab faces. The IPA60R280CFD7 FullPAK faces of Q19 / Q7
   stand **≈ 0.5 – 2 mm further east** than the SICD1 / Q6 faces.
2. Only **≈ 2.4 mm** is free between the two rows before any insulating pad.
3. The H4 screw head stands in the plate's path.
4. Q5 / SICD1 and Q6 / SICD2 have opposing mounting holes 0.2 / 1.2 mm apart in y.

There is also one real collision the stage-13c copper check could not see: the **C102 can overlaps the 6 mm screw head
of H8** by 0.1 mm nominal, and by 0.6 mm with a 7 mm washer. Thermally nothing is shown above its rating at the 5.1
load. Open items:
- TR2 (model 4 – 6 W, open measurement).
- DB1 (2.1 W SMD, datasheet thermal data not obtained).
- The heater SR Q1 / Q2 copper, now about 1/3 of the 5.1 copper.
- TR1 at a 70 °C ambient.

The heatsink outlines, potentials and insulation are owner inputs. The list of what is needed is at the end.

## Checklist results
| Item | Verdict | Evidence |
|---|---|---|
| A1 | **FAIL** | `rv bq fp Q5,Q6,SICD1,SICD2,Q7,Q19` plus the KiCad library fab outlines, read from the AppImage share dir.<br>• `TO-220-3_Vertical`: body local y −3.15 … +1.25, tab −3.15 … −1.88. `TO-220F-3_Vertical`: −3.05 … +1.65. `TO-247-3_Vertical`: −2.33 … +2.70. `tube_psu:TO-220-2_Vertical_AK`: −3.15 … +1.25. So the back face is on −y, as the courtyard boxes confirm.<br>• Datasheets: Wolfspeed C2M0160120D Rev. 07 (Oct 2024) TO-247-3L table: A 4.83 – 5.21, A1 2.27 – 2.52, A2 1.91 – 2.16, D 20.75 – 21.05, L1 3.97 – 4.69. Infineon IPA60R280CFD7 Rev. 2.2 p 12, PG-TO220 FullPAK Z8B00003319: A 4.50 – 4.90, A1 2.34 – 2.85, A2 2.42 – 2.86, D 15.67 – 16.15, øP 3.00 – 3.30, Q 3.15 – 3.50; VISO 2500 Vrms (p 3). Wolfspeed C3D02060A Rev. 10 TO-220-2: P 4.19 – 4.70, Q 1.21 – 1.37, F 3.63 – 3.89 (labels not tied to the drawing in the text extract).<br>**West row, tabs face east:** Q5 TO-247, pins x 3.752, y −29.6 … −18.7, rot −90, back face x ≈ 6.0 – 6.3 (pin + A1), drain = PFC_DRAIN_1. SICD2 TO-220-2, pins x 3.09, y −3.82 … 1.26, back face x 6.24 (KiCad), cathode = DC+.<br>**East row, tabs face west:** Q6 TO-247, x 11.389, y −7.9 … 3.0, back face ≈ 8.87 – 9.12, PFC_DRAIN_2. SICD1 x 11.8, y −26.5 … −21.4, back face 8.65 (KiCad), DC+. Q19 FullPAK x 12.75, y −52.1 … −47.0, back face 9.60 (TO-220 footprint) / 9.70 (KiCad TO-220F) / ≈ 10.1 – 10.6 if the A1 / A2 values are lead-to-front, insulated, drain DC+. Q7 FullPAK, same x, y −63.3 … −58.3, insulated, drain = switch node.<br>**Result:** the west faces are coplanar within ≈ 0.2 mm. The east faces spread **≥ 0.95 mm** (8.65 → 9.60), up to ≈ 2 mm. Free gap between the rows: 6.27 → 8.65 = **2.4 mm** before pads. F1. |
| A2 | CANNOT VERIFY | `rv bq area 6.0 -66 9.7 8 --touch`, F.Cu parts: SICD2, DB1, Q5, C87, H4, Q6, SICD1, C73, Q7, Q19, and nothing else.<br>Notches the plate needs:<br>(a) DB1 x −1.34 … 8.39 and C73 x 8.57 … 16.43 together cover the whole gap (0.18 mm between them) over y −17.0 … −8.3. The plate needs ≥ 3.2 mm clear height there (TBS height 2.6 assumed, README; 2220 ≈ 2.5 – 2.8). This is the same as on 5.1: DB1 and C73 are at the same place (`rv bq51 fp DB1,C73`).<br>(b) The H4 screw head (6 mm, nylon) needs a cut-out ≥ 7 mm wide at y −43.6 … −36.6 and ≥ 3 mm high. This is new: the 5.1 plate ended at Q5.<br>(c) C87 0603, x 4.17 … 7.22, y −60.2 … −58.6: ≥ 1.2 mm clear height. New: on 5.1 it was at y −67.4.<br>No drawing to check against. |
| A3 | **FAIL** | No document fixes the plate potential. README "Footprints and 3D models" says "plate = primary / earthed" (either). NEXT_REVISION 5.5 asks for a reinforced chain; RESOLUTIONS 10 F4 is "open – owner". H4 now has nylon hardware (RESOLUTIONS owner decisions; README stage 13c: PFC_DRAIN_1 pour 1.98 mm from the 6 mm head), so the screw is no longer an earthed item next to the plate. F3. |
| A4 | **FAIL** | NEXT_REVISION.md:196 (5.5) and NEXT_REVISION_PLAN.md:67-73 give only the principle (rated pads + shoulder washers on bare tabs, FullPAK + pad on Q8 / Q21). They name no pad material, thickness or rating. The text also still describes **one plate with Q8 / Q21 on it**, which contradicts the given "Q8 / Q21 have their own secondary heatsink" (README Stage 4a, review README rule 6). FullPAK isolation: IPA60R280CFD7 VISO 2500 Vrms, 1 min (Rev. 2.2 p 3). Bare tabs: Q5 / Q6 drain (PFC switch nodes), SICD1 / SICD2 cathode (DC+). F3. |
| A5 | **FAIL** | Hole on the body axis: the TO-247 hole is on pin 2, the TO-220-2 hole midway between its pins.<br>• Q5 y −24.115 vs SICD1 y −23.94: **Δy 0.18 mm**.<br>• Q6 y −2.436 vs SICD2 y −1.28: **Δy 1.16 mm**.<br>• Q7 / Q19 have nothing opposite.<br>Heights: the TO-247 body is 21 mm tall (D) and the FullPAK / TO-220 about 16 mm, so the holes are 2.5 – 3.5 mm apart vertically at equal seating. Two screws with insulating shoulder washers collide; a through bolt needs coaxial holes (set by the seating heights). No clip or bolt scheme is documented. F3. |
| A6 | **FAIL** | Per-face spread, from the A1 numbers: west ≈ 0.2 mm (OK); east **0.95 mm (KiCad models) to ≈ 2 mm (FullPAK datasheet, depending on which of A1 / A2 is lead-to-back)**, above the 0.5 mm the leads can take. Bare-tab devices also need pads (≈ 0.2 – 0.3 mm), the FullPAKs do not: that adds another 0.2 – 0.3 mm to the Q19 / Q7 air gap. F1. |
| A7 | PASS (as 5.1, checklist criterion not met) | Script on `b52.json` (THT pad ↔ B.Cu SMD pad):<br>• Q7.1 → R92.2 0.15 mm, same net; → R92.1 (Net-(D34-PadA)) 0.52 mm; Q7.2 → R70.2 GND 0.88.<br>• Q19.1 → R26.2 0.20, same net; → R26.1 (DHB_HI_GATE) 0.57; → D30.C 0.75.<br>• Q5.1 → R1.2 0.46, same net.<br>• Q6.1 → R19.2 **0.06**, → R20.2 0.22; Q6.3 → R21.1 0.19.<br>All other-net pairs are ≥ 0.52 mm. SMD bodies within 1.0 mm of a THT pad edge exist (R92, R26, R90), but the 5.1 board, built and soldered, has the same pattern at Q6 (0.06 / 0.19 / 0.22 mm, identical in `b51.json`) and Q7.3 → R83.1 0.19 mm. |
| B1 | CANNOT VERIFY | Q21 / Q8 pins at y −41.95, rot 180, tabs face south: tab face y ≈ −38.8, bodies straddle the L-cut-out arm (y −40.4 … −39.2).<br>Plan distances from a 3 mm sink, x 51.9 … 74.2, y −38.8 … −35.8:<br>• primary F.Cu copper **4.45 mm** (ISO2 pad 1, +3V3);<br>• B.Cu primary GND pour 3.89 mm (matters only for screws through the board).<br>So a secondary sink ≤ 3.4 mm thick keeps 4.0 mm clearance. It must not touch the board within 11.1 mm of primary copper (ISO2 primary row, C98), so it can only be held by the tabs or by feet inside the secondary area. The 5.1 sink size is not in the repository: on 5.1 Q7 / Q19 / Q21 / Q8 stood in one row (y −41.95, tabs south, `rv bq51 fp Q7,Q19`), and ISO2 was moved next to it in 5.2. |
| B2 | PASS (note) | TR3 centre (49.5, −69.3), body 46 × 42 × 31.5 mm. Centre to H2 42.6 mm, to H3 41.3 mm; the north edge between H2 and H3 (80 mm) is not cut. The L-cut-out (`rv bq slots`: x 50.81 … 52.02, y −62 … −40.4, plus arm y −40.4 … −39.2) lies south of TR3 (body ends at y −47.8) and cuts only the path to the board centre, not the path to H2 / H3. The mass (≈ 100 – 150 g) is assumed, not measured. Recommendation (note): a bead of RTV / adhesive under the TR3 bobbin or core to the board, and the cables tied, for transport shock. |
| C1 | PASS | README "Footprints and 3D models" and footprint suffixes: C19 / C30 50 mm (Ymin KCXE D10×50, `lib/jlc_parts_next.csv`); C28 / C29 / C37 / C56 45 mm (D12.5×45); TR3 31.5; L1 / L2 31.5 (upright toroid); TR1 29.2; R27 26; TO-247 ≈ 25 with leads; CM1 / CM4 25; TR2 ≈ 22 (assumed); C31 / C32 20; C102 18; the vertical control card ≈ 38 (C2). 5.1 had 50 mm cans at C19 / C30 (39 µF EKXJ…MJ50S, same 50 mm length). Nothing is taller than 50 mm. No enclosure height is documented in the repository. |
| C2 | PASS (placement); mating height open | J2 has the same position and pin field as 5.1 (`rv bq51 fp J2` and `rv bq fp J2`: (33.135, −22.156), box 31.52 … 36.02 / −23.34 … 9.51). F.Cu parts within x 26 … 42 are identical on both boards except value / size changes (R114 – R116 0805 → 1206); the only tall neighbours are the 45 mm cans at x ≤ 29.45, as on 5.1.<br>Card (`~/dev/ti60f225_tube_psu_control_card/hardware/control_card.kicad_pcb`, read-only):<br>• outline 32.5 × 33.8 mm;<br>• J1 = `PinHeader_2x25_P1.27mm_Horizontal_U25` (male right-angle, "4.0mm pin length", plastic x 1.77 … 2.77 local, pins to 6.77), so the card **stands perpendicular** to the power board;<br>• the card edge is 0.32 mm inside the header plastic, so the card's lower edge sits ≈ 4.3 + 0.3 = 4.6 mm above the board, and its top at ≈ 38 mm.<br>The XKB drawing (contact depth) could not be fetched; LCSC C2881768 page: insulator 4.3 mm only. |
| C3 | CANNOT VERIFY | L2 body ≈ x −30.8 … 0.7, y −51.2 … −31.2; L1 ≈ x −30.9 … 0.7, y −3.2 … 16.8 (courtyards −1 mm).<br>Within 3 mm:<br>• L2: Q5 (overlaps in x by 1 mm over y −32.4 … −30.2), C117 (y gap ≈ 0.9 mm), CM4, C64, H4 (body 1.9 mm from H4's 6 mm head in plan).<br>• L1: C117, C66, CM4, SICD2 (front face x 1.84, 1.1 mm from L1's +x end at 15.75 mm height), H7.<br>Q5, C117, CM4, C64, C66 are at their 5.1 places (`rv bq51 fp`), where the toroids are built. SICD2 moved: on 5.1 its tab face was at x 0.65, now its front face is at 1.84, so it is 1.2 mm further from L1 than on 5.1.<br>H7 vs L1: at x 0.37 (head edge) the ring is 12.7 mm above the board, so no contact.<br>L1 body edge is 2.0 mm inside the south edge; a +3 mm error would overhang 1 mm.<br>The real positions are an open owner measurement. |
| C4 | **FAIL** (note) | Script (pad / courtyard to every Edge.Cuts item):<br>• SMD within 1.0 mm of the outline: **R163** (B.Cu 1206 bleeder, stage 15b) pad 0.52 mm from the east edge (x 91.15), courtyard 0.21 mm;<br>• SMD within 1.0 mm of a slot: **C13** (0603 MLCC, B.Cu) pad 0.70 mm from the ISO1 T-slot;<br>• THT within 1 mm (not stress-sensitive): TR1 0.50 mm (own slot), Q21 / Q8 0.55 mm (L-arm), TR2 0.85 mm, J4 1.45 mm (top edge).<br>All 2220 MLCCs are ≥ 7.7 mm from any edge / slot (C16 7.72, C55 12.0, C47 15.7, C54 19.5, C73 29.7). J4 (1×6 vertical header at x 11.4, y −89 … −76.3) mates from above, usable with the board mounted. F7. |
| D1 | PASS | `rv bq fp H…` vs `rv bq51 fp H…`: H1 (−67.029, −87.522), H2 (6.922, −87.522), H3 (86.971, −87.522), H4 (5.842, −40.132), H6 (−67.029, 14.477), H7 (3.371, 14.477), H8 (84.232, 14.477). Identical; H5 absent in 5.2 (5.1: (87.148, −29.813)). Footprint is now `tube_psu_next:MountingHole_3.0mm_NPTH` without ring (stage 13c). `check_next.sh` passed today (task statement; `drc_summary.py`: report newer than the board). |
| D2 | **FAIL** | Courtyards / pads within r 4 mm of each centre: H1, H3, H4, H6 none; H2 U11 courtyard 2.19 / J4 2.66; H7 L1 courtyard 1.66; H8 C102 courtyard 1.94.<br>Real bodies:<br>• **C102** (D10 can, centre (77.0, 11.35)) is 7.88 mm from the H8 centre, so its sleeve is 2.88 mm from the centre: **inside a 6 mm head (r 3.0) by 0.12 mm, by 0.62 mm for a 7 mm washer**, more with the can tolerance.<br>• J4 housing (x 10.13 … 12.67) is 0.21 mm from a 6 mm head at H2 and overlaps a 7 mm washer by 0.29 mm.<br>• U11 body edge (y −83.15) is 1.37 mm from the H2 head.<br>• H4: no body within 4 mm (copper 1.93 – 2.08 mm from the head, nylon accepted, stage 13c).<br>• H7: L1 is 12.7 mm above the board at the head edge.<br>F2, F9. |
| D3 | PASS (note) | Spans: H1–H2 74 mm, H2–H3 80 mm (TR3 between), H3–H8 102 mm (east edge without H5; C19 / C30 50 mm cans and terminals between), H6–H7 70 mm, H7–H8 81 mm; H4 inside. H5 removal is the owner's decision "does not droop" (README Stage 10). Whether the primary plate is fixed to the chassis or only to the board is open (F3). Heavy parts and their nearest holes: TR3 → H2 / H3 ≈ 42 mm; L2 → H4 ≈ 12 mm; L1 → H7 ≈ 18 mm; TR2 → H1 ≈ 38 mm. |
| E1 | CANNOT VERIFY | Table in F-section "Loss budget" below. No part is shown above its rating at the 5.1 load (≈ 130 W continuous, design document p 33). TR2, L1 / L2, DB1 and the PFC FET losses are not established. Three hottest by loss: **TR2 (model 4 – 6 W vs bench "slightly warm", open)**, **Q1 / Q2 (1.4 – 3.1 W each at 10 – 15 A, on about 1/3 of the 5.1 copper)**, **DB1 (2.1 W at 540 W, 0.8 W at 130 – 200 W, SMD)**. |
| E2 | PASS | DB1 has the same place, rotation and copper as 5.1: `rv bq51 fp DB1` = (3.525, −12.15) rot 0. AC1 F.Cu pour 218.0 mm² (5.1 221.8), AC2 169.5 (169.7). Loss 2 × 1.11 A × 0.95 V ≈ 2.1 W at 540 W (findings 05 A9; VF 950 mV at 2 A, Tj ≤ 150 °C from jlcpcb.com/partdetail/18530313-TBS22KTP/C17401133). The MCC datasheet (RthJA) could not be fetched (mccsemi.com 404). |
| E3 | PASS (losses small) | `rv bq net`:<br>• HEATER_HI_SOURCE (Q10 tab) F.Cu 195.1 mm² in 12 pieces, 4 vias (5.1 242.7 mm²): below the "≥ 2 cm² with thermal vias to L2 – L6" of NEXT_REVISION 5.4, but Q10 / Q11 lose 0.16 – 0.22 W each (findings 06 B6).<br>• FLY_C (PWM2 drain) F.Cu 124.6 + B.Cu 68.8 = **1.93 cm²** vs the 2 – 3 cm² of CHANGES 1.5; PWM2 0.3 – 0.6 W, Tj ≤ 110 °C at 50 °C ambient (EEL19_DESIGN 14.8, findings 01 B4), ≈ 130 °C at 70 °C ambient with 94 K/W, below Tj max 150 °C. Q11 DC+ piece not re-measured. |
| E4 | PASS | Q6 front face (x 14.09, plastic side; the tab faces the plate) to the C37 / C56 cans (body x ≈ 16.9 / 16.45): 2.4 – 2.8 mm. Same positions as 5.1 (`rv bq51 area 26 -26 42 12` identical cans; Q6 identical). SICD1 front face 13.05 → C28 / C56 ≈ 3.4 mm. Q19 / Q7 front 14.0 – 14.4 have no can in their y range. C19 / C30 ↔ TR3 courtyard gap 2.85 mm (README); TR3 ΔT ≈ 17 K (DAB_TRANSFORMER 3.3). C31 / C32 beside Q1 / Q2 and C1 / C2 / C102 at TR1 are as in findings 01 / 06. Bulk capacitors ripple: findings 05 A10, 1.35 A (100 Hz) per bank vs 0.63 A per can at 120 Hz × 4 cans. |
| F1 | **FAIL** (note) | `drc_summary.py courtyards_overlap` = **135** (README: 132 first draft + C79 / C80 + C141 − stage-14g pair). Script: 86 pairs identical to 5.1 (same relative place, rotation, footprint). New pairs with a body gap < 0.3 mm or a pad under a body:<br>• **R53 / D30 0.15 mm** (B.Cu 0805 / SOD-323 body);<br>• C92 / R26 0.27 mm;<br>• **R114 / R115 / R116** (1206 at 3.5 mm pitch, were 0805 on 5.1): body gap 0.30 mm, but the 1.75 mm pads overlap (same net), so each pad runs 0.44 mm under the neighbour's body.<br>As-5.1 pairs < 0.2 mm: U4 / R94 0.17, U4 / C76 0.19. JLC's current minimum spacing was not looked up. F8. |
| F2 | CANNOT VERIFY | IN1 pad 1 (−64.2, −16.1) and CM1 pad 3 (−51.185, −9.194): pad edges 0.2 / 0.05 mm inside the nominal 11.5 mm body of C86 (x −63.40 … −51.90). Same three parts and places as 5.1 (`rv bq51 fp C86,IN1,CM1`). The LCSC page for C2888216 returned "Part not found", so the Dongtong MKP62 body width is unknown. |
| F3 | PASS | Census: F.Cu 61 THT + 97 SMD, **B.Cu 222 SMD** (checklist 216 + R159 – R163 + C141). B.Cu parts above 1210 size: C58 (5×5.4 electrolytic), DRV3 / DRV5 / DRV6 (SOIC-16W), D6 / D11 / D18 / D19 / D29 (SMA), R21 / R30 / R93 (KRL2012), U1 / U4 / U10 (3×3). C58 is the only one that may need glue or the first reflow pass; JLC decides. |
| F4 | PASS | Zone settings in the board file: 70 zones `connect_pads yes` (outer pours, solid), 17 `thru_hole_only` (In1 / In4 GND, In3 15V / 5V / 6V3, HT_GND, ISO_GND planes: relief on THT, gap 0.3, spokes 0.6 – 0.8 mm). 5.1 had all 85 zones solid and was hand-soldered (`kicad/tube_psu.kicad_pcb`). So the 5.2 THT pins are solid on the outer pours as on 5.1 and relieved on the inner planes, which is better. `starved_thermal` 2 = C102 pad 1 on In1 / In4 (one spoke; solid on the outer layers; known). WP1 – WP4 4.0 mm pads in the 6V3 / HT pours as 5.1. |
| F5 | PASS (content) | Every footprint except WP1 – WP4 has `${REFERENCE}` on F.Fab / B.Fab (script over the board file, 376 / 380). Every THT footprint has ≥ 2 fab items. Own transformer footprints carry pin / clip / PRI / SEC texts on F.Fab. Electrolytic / diode library footprints carry polarity on Fab. Whether the fab package contains an assembly drawing is open finding 14 F5 (checklist 14). |

## Findings (ranked, most severe first)

### F1 The east-row tab faces are not coplanar; a single flat plate cannot touch Q19 / Q7
- Severity: **should fix**. Decide before ordering: the smallest board fix is a placement move, otherwise the bracket
  carries it.
- What is wrong:
  - The west row (Q5, SICD2) has its back faces at x ≈ 6.0 – 6.3.
  - The east row has SICD1 at 8.65, Q6 at ≈ 8.9 – 9.1, and the IPA60R280CFD7 FullPAKs Q19 / Q7 at 9.6 – 9.7 by the KiCad
    models (≈ 10.1 – 10.6 if the FullPAK leads sit nearer the front).
  - A plate between the rows can be at most ≈ 2.4 mm thick. With insulating pads on the four bare-tab devices it drops
    to ≈ 1.9 – 2.0 mm. A plate pressed against SICD1 / Q6 then leaves a **≈ 1.2 – 2.3 mm air gap** at Q19 / Q7: the
    FullPAKs carry no pad, which adds the pad thickness to the gap.
  - The TO-220 footprint also under-states the FullPAK body: front face at 1.65 mm (KiCad TO-220F) vs the courtyard's
    1.5 mm.
- Evidence:
  - Pin columns from `rv bq fp Q5,Q6,SICD1,SICD2,Q7,Q19`.
  - Back-face offsets from the KiCad 10.0.7 library fab layers: TO-220 3.15, TO-220F 3.05, TO-247 2.33 mm. They agree
    with the courtyard boxes.
  - IPA60R280CFD7 Rev. 2.2 p 12: A 4.50 – 4.90, A1 2.34 – 2.85, A2 2.42 – 2.86.
  - C2M0160120D Rev. 07 TO-247-3L: A1 2.27 – 2.52.
  - On 5.1 only Q5 / Q6 faced this gap (2.8 mm). The 5.1 SICD1 / SICD2 tabs faced away from it (`rv bq51 fp SICD1,SICD2`:
    tab faces x 14.65 / 0.65).
- Smallest fix (one of):
  1. A stepped bracket, about 1 – 2 mm thicker over y −66 … −44 (only C87 and the H4 head are opposite).
  2. A gap pad / aluminium spacer of the measured thickness on Q19 / Q7.
  3. On the board: move the Q19 / Q7 pin column from x 12.75 to ≈ 11.7 – 11.9. This re-routes the DAB primary, which
     is the expensive option.
  
  Measure the real lead-to-back distance of the three packages first.
- Confidence: medium. The column positions are certain. The package lead-to-back distances come from KiCad models and
  datasheet tables whose drawing labels could not be read. Calipers on one device of each package settle it.

### F2 The C102 can collides with a 6 mm screw head at H8
- Severity: **should fix**
- What is wrong: C102 (Ymin KCXE 56 µF 250 V, D10 × 18) is centred at (77.0, 11.35). Its sleeve is 2.88 mm from the
  H8 centre (84.232, 14.477), which is inside the 6 mm head / standoff that the stage-13c rules assume (r 3.0) by
  0.12 mm nominal, and by 0.62 mm with a 7 mm washer, plus the can's diameter tolerance. Stage 13c checked copper only.
  On 5.1, C102 at (72.657, 11.347) was 6.6 mm clear. H8 is one of the four holes with nylon hardware, so the head is
  insulating, but it still cannot seat against the can. The can is at the −100 V BIAS terminal potential; the sleeve is
  not rated insulation.
- Evidence: `rv bq fp C102,H8`; distance √(7.232² + 3.127²) = 7.88 mm − 5.0 (can radius) = 2.88 mm < 3.0 mm.
- Smallest fix: move C102 ≈ 0.6 – 1.0 mm away from H8 (west / north) if its pads, the 7.2 mm secondary hole rule and
  the TR1 pins allow; or specify an M3 nylon screw with a ≤ 5.0 mm head and no washer at H8 (5.0 mm head → 0.38 mm
  clear nominal).
- Confidence: high for the geometry, medium for the can diameter (KCXE outline not fetched: D10 nominal used).

### F3 The primary heatsink is not defined: potential, insulation, H4 in its path, opposing holes; documents disagree on Q8 / Q21
- Severity: **should fix** (owner input before the bracket is made; no copper change needed)
- What is wrong:
  - (a) The plate potential is not fixed ("primary / earthed", README), and RESOLUTIONS 10 F4 is open.
  - (b) No pad / washer material, thickness or rating is named for the bare tabs (Q5 / Q6 drain, SICD1 / SICD2 cathode).
  - (c) The plate now runs from Q7 (y −66) to Q6 (y +5.8) and passes **H4** (head 6 mm at y −43.1 … −37.1, within the
    gap x 2.8 … 8.8). It needs a cut-out or must be raised there, which 5.1 did not need.
  - (d) The mounting holes of **Q5 / SICD1 (Δy 0.18 mm)** and **Q6 / SICD2 (Δy 1.16 mm)** face each other across the
    plate at 2.5 – 3.5 mm different heights. Two screws with shoulder washers collide; either a common insulated
    through-bolt with seating heights set so the holes are coaxial, or spring clips.
  - (e) NEXT_REVISION 5.5 / NEXT_REVISION_PLAN D3 still describe one bracket that also carries Q8 / Q21, against the
    given separate secondary heatsink (README Stage 4a).
- Evidence: A2 – A5 rows; `rv bq fp H4`; NEXT_REVISION.md:196; NEXT_REVISION_PLAN.md:33, 67-73; RESOLUTIONS.md row 10 F4.
- Smallest fix: the owner decides (a) – (d). The list "Dimensions the owner must confirm" below is the input. Update
  NEXT_REVISION 5.5 / PLAN D3 to "primary plate (Q5, Q6, SICD1, SICD2, Q7, Q19) + separate secondary sink (Q8, Q21)".
- Confidence: high (it is the absence of a definition).

### F4 Heater SR Q1 / Q2 copper about 1/3 of 5.1 while dissipating 1.4 – 3 W
- Severity: **note** (bench check). RESOLUTIONS records 06 F3 as fixed by the 16 vias, and the no-inner-switch-node
  rule is given.
- What is wrong:
  - Q14_DRAIN (Q1 tab): F.Cu 104.1 + B.Cu 104.4 mm², 16 vias. 5.1: 151 mm² on each of four layers.
  - Q13_DRAIN (Q2): 166 + 166 mm². 5.1: 178 × 4.
  - The 5.1 board had the same FETs and was benched to 15 A. 5.2 Q1 has ≈ 34 % and Q2 ≈ 47 % of the 5.1 drain copper.
  - Loss per FET ≈ 1.4 W at 10 A to ≈ 3.1 W at 15 A (findings 06 C3, RDS(on) not datasheet-verified).
- Evidence: `rv bq net Q14_DRAIN`, `rv bq51 net Q14_DRAIN`, same for Q13_DRAIN.
- Smallest fix: none before ordering. Measure the Q1 / Q2 case temperature at 15 A. Limit the heater current if hot.
- Confidence: medium.

### F5 TR1 at a 70 °C ambient has almost no margin at the 20 W design point
- Severity: **note**
- What is wrong: EEL19_DESIGN 14.8 gives ΔT 44 – 48 K at 20 W and "surface ≤ 98 °C at 50 °C ambient" against the
  120 °C TEX-E class. At the 70 °C rack ambient of the design document (p 34) this becomes ≈ 118 °C, a 2 K margin.
  At 15 W it is 104 °C; nominal (0.53 W) is +16 K.
- Evidence: simulation/flyback/EEL19_DESIGN.md:1601-1620.
- Smallest fix: none. State the 70 °C limit as ≤ 15 W auxiliary load, or measure.
- Confidence: medium (the ΔT formula is rough).

### F6 Secondary heatsink: thickness limit ≈ 3.4 mm towards ISO2, and Q21 / Q8 need it above ≈ 200 W
- Severity: **note**
- What is wrong:
  - The tabs face south (y −38.8). ISO2's primary pad 1 is 4.45 mm from the back of a 3 mm sink, so a sink thicker
    than ≈ 3.4 mm, or one with feet on the board within 11.1 mm of primary copper, breaks the PRI–SEC rules.
  - Thermal: per FET ≈ 1.1 – 1.2 W at 400 W, from RDS(on) 0.237 / 0.28 Ω at 25 °C and 0.54 Ω typ at 150 °C
    (Rev. 2.2 p 4) with I_rms 1.57 – 1.63 A per switch (DAB_SIMULATION 2.1). Total 6.2 – 6.9 W (2.9). Free air
    (RthJA 80 K/W) gives ≈ 165 °C at 70 °C ambient, above Tj max 150 °C, so the sink is required at 400 W. At the 5.1
    continuous 130 W, the loss is ≈ 0.13 W per FET: free air is fine.
- Evidence: script distance (B1 row); IPA60R280CFD7 Rev. 2.2 pp 3 – 4 (RthJC 5.31 K/W, RthJA 80 K/W leaded,
  Tj −55 … 150 °C).
- Smallest fix: give the secondary sink as ≤ 3 mm plate behind the tabs, held by the tabs / clips, no board contact
  south of y −38.8.
- Confidence: medium (plan distances; the sink height above the board is unknown).

### F7 R163 (new bleeder) 0.52 mm from the east board edge
- Severity: **note** (checklist 14 / order remark)
- What is wrong: R163 (B.Cu 1206, ISO_GND / −100V BIAS) pad edge is 0.52 mm and its courtyard 0.21 mm from the milled
  east edge. If JLC adds V-scored rails on that edge (14 F4: rails / fiducials open), the part is in the scoring stress
  zone. C13 (0603 MLCC) is 0.70 mm from the ISO1 T-slot; that slot is milled, not scored, so the stress is low.
- Evidence: edge-distance script; `rv bq fp R163,C13`.
- Smallest fix: in the order remark, no V-cut on the east edge (mouse bites or rails on the north / south edges only);
  or move R163 0.5 mm west.
- Confidence: high for the distance, low that it matters with milled rails.

### F8 Courtyard pairs below 0.2 mm body gap / shared pads
- Severity: **note**
- What is wrong: R53 / D30 (B.Cu, Q19 turn-off branch, stage 4l) body gap 0.15 mm. R114 / R115 / R116 (1206,
  PWM2 start-up / sense divider on DC+) have overlapping same-net pads that reach 0.44 mm under the neighbouring body
  (5.1: 0805 at the same 3.5 mm pitch, pads separate).
- Evidence: courtyard script (F1 row); `rv bq fp R114,R115,R116`, `rv bq51 fp R114,R115,R116`.
- Smallest fix: none needed for function. Check the JLC placement preview, or nudge D30 0.1 mm.
- Confidence: medium (body sizes are nominal).

### F9 H2 washer overlaps the J4 housing
- Severity: **note**
- What is wrong: a 7 mm washer at H2 overlaps the J4 1×6 housing (x ≥ 10.13) by 0.29 mm. A 6 mm head clears it by
  0.21 mm.
- Evidence: `rv bq fp H2,J4`.
- Smallest fix: no washer under the H2 nylon screw head, or a ≤ 6 mm head.
- Confidence: high.

### Loss budget (E1)
| Part | Loss (source) | Path | Estimate at 70 °C ambient |
|---|---|---|---|
| Q5 / Q6 C2M0160120D | not established. 05 F: +0.5 – 0.7 W turn-off from the 5 Ω gate change | plate, pad | as 5.1 ("semiconductors at 100 °C in a 70 °C rack", p 34); RthJC 0.9 / 1.0 K/W (Rev. 07 p 2), Tj max 150 °C |
| SICD1 / SICD2 C3D02060A | ≈ 0.71 A avg × 1.5 V ≈ 1.1 W each at 540 W (05 A8) | plate (new; tabs now face it) | RthJC 3.8 K/W typ (Rev. 10 p 2), Tj max 175 °C: ≈ sink + 6 K |
| Q7 / Q19, Q21 / Q8 IPA60R280CFD7 | ≈ 1.1 – 1.2 W each at 400 W (F6); ≈ 0.13 W at 130 W | plates | sink + 1.2 × (5.31 + ≈ 1) ≈ sink + 8 K; Tj max 150 °C |
| DB1 TBS22K | 2.1 W at 540 W, 0.8 W at 130 – 200 W | pads → AC / DC+ / GND pours (as 5.1) | RthJA not obtained |
| Q1 / Q2 BUK9Y15-60E | 1.4 – 3.1 W each (06 C3) | 208 / 332 mm² drain copper | not computable (F4) |
| Q10 / Q11 IPD60R280P7S | 0.16 – 0.22 W (06 B6) | DPAK copper | ≤ +33 K (06) |
| PWM2 ICE5AR0680AG | 0.3 – 0.6 W | 1.93 cm² drain copper | ≤ 130 °C at 94 K/W (E3) |
| TR1 | 0.53 W nominal, 1.86 – 2.06 W at 20 W | air | ≈ 118 °C surface at 20 W (F5) |
| TR2 | model 4 – 6 W vs bench "slightly warm" (TR2_OPENMAGNETICS; p 33) | air | **open measurement** |
| TR3 | 2.2 W, ΔT ≈ 17 K (DAB_TRANSFORMER 3.3) | air | ≈ 87 °C |
| L1 / L2, CM1 / CM4 | not established (L1 / L2 values to measure) | air | as 5.1 (same chokes) |
| R27 | 0 W, relay closed | – | – |
| R68, R159 – R163 | 97 mW each in 250 mW 1206 (stage 15b) | B.Cu strip, 20 mm | fine |
| R4 – R6 | 39 mW (stage 15c) | – | fine |
| Shunts R83 / R93 / R21 / R30 | R83: 2.31² × 5 mΩ = 27 mW; others ≤ 0.25 W per 08 F | KRL2012, 1 W | fine |
| DRV5 / DRV6 UCC21520 | ≈ 2 × 18 nC × 15 V × 140 kHz = 76 mW gate + quiescent ≈ 0.1 – 0.15 W | SOIC-16W | fine |
| V4 LDO, preloads R124 / R125 | not computed | – | – |

## Compared with 5.1
- **Equal:**
  - Mounting-hole positions (D1).
  - J2 position and neighbourhood (C2).
  - DB1 place and copper (E2).
  - Q5 / Q6 places and their B.Cu gate parts (A7).
  - The bulk capacitor neighbourhood of the plate (E4).
  - Tallest part 50 mm (C1).
  - THT pads solid on the outer pours (F4).
- **Better:**
  - Inner planes relieve THT pins (F4).
  - DAB loss at 400 W 6 – 7 W vs 11 – 12 W simulated for the STF7N60M2 (DAB_SIMULATION 2.9).
  - SICD2 1.2 mm further from L1 (C3).
  - Mounting holes without copper, nylon at H2 / H4 / H7 / H8.
- **Worse / new:**
  - One plate now spans Q7 … Q6 and meets H4 and C87; the east row is not coplanar (F1, F3).
  - The C102 can is against the H8 head (F2).
  - Heater SR copper about 1/3 (F4).
  - PWM2 drain copper 1.93 cm² (new part; target 2 – 3 cm²).
  - ISO2 next to the secondary sink area (F6).
  - R163 at the edge (F7).

## Could not verify
- Heatsink outlines, thickness, height above the board, fixing (chassis or board), potential, pad / washer
  material: not in the repository (owner).
- Lead-to-back distance of the TO-220 FullPAK / TO-220-2 / TO-247 packages. The drawing labels could not be tied to
  the dimension tables in the text extracts, so the KiCad models were used.
- TBS22K datasheet (height, RthJA): the mccsemi.com URL returned 404; only the JLC part page was read.
- XKB X1321FV-2x25-C43D24 drawing: the LCSC PDF link returned only a title. Contact depth and mating height against
  the card's 4.0 mm right-angle pins are unknown (owner check, RESOLUTIONS 04 F1).
- C86 (C2888216) body size: LCSC "part not found".
- TDK C5750X6S2W225K and the 2220 heights; the Ymin KCXE can tolerance.
- TR2 temperature, L1 / L2 positions and losses, TR3 mass: owner measurements.
- PFC FET loss at 540 W: no simulation in the repository.
- JLC minimum component spacing (F1 / F8); which side JLC reflows first (F3).
- The 3-D renders on `origin/renders` were not viewed: they may predate the stage-13 – 15 changes, and the geometry
  above comes from the board dump.

## Dimensions the owner must confirm before ordering
1. **Package faces:** calipers on one C2M0160120D, one C3D02060A and one IPA60R280CFD7: lead centreline to the back
   (metal / flat) face, and body thickness (F1). Decide: stepped bracket, Q19 / Q7 spacer, or move the Q19 / Q7 column.
2. **Primary plate:**
   - thickness (≤ 2.4 mm minus pads between the rows);
   - y extent;
   - bottom-edge height above the board;
   - the cut-outs: ≥ 3.2 mm clear over y −17 … −8.3 (DB1 / C73), a ≥ 7 mm cut-out at y −43.6 … −36.6 for the H4
     nylon screw head, ≥ 1.2 mm over C87 at y −60.2 … −58.6;
   - how it is fixed (chassis bracket or board) and where its feet stand.
3. **Plate potential** (earthed / floating / primary) and the insulation of Q5, Q6, SICD1, SICD2: pad part, thickness,
   rating, shoulder washers; FullPAK Q7 / Q19 directly or with grease.
4. **Device fixing:** clips, or one insulated through-bolt per opposing pair. Set the seating heights so the holes of
   Q5 / SICD1 (Δy 0.18 mm) and Q6 / SICD2 (Δy 1.16 mm) are coaxial; seating height of each TO part above the board.
5. **Secondary sink (Q21 / Q8):** thickness (≤ 3.4 mm behind the tabs at y −38.8), height, potential, no board contact
   within 11.1 mm of primary copper.
6. **H8 / C102:** the can diameter and the H8 screw-head / washer size (F2); H2 head / washer vs J4 (F9).
7. From the README caliper list:
   - EEL19 4+6 bobbin base, pin diameter, seated height;
   - EC42 pin diameter, base, core depth, seated height, core-plate height above the secondary pins;
   - L1 / L2 body positions, OD / width;
   - EF25 (TR2) height;
   - TBS bridge height.
8. J2: socket contact depth and card mating height / orientation against the card's right-angle J1 (pins 4.0 mm
   beyond the plastic; the card edge then sits ≈ 4.6 mm above the board).

## Outside scope
- Checklist 14:
  - fiducials / rails and no V-cut on the east edge (F7);
  - assembly drawing (14 F5);
  - the TO-220 footprint for the FullPAK under-states the front by ≈ 0.1 – 0.4 mm (courtyard only).
- Checklist 13: the C86 / C117 generic X2 body size (C2888216 not found at LCSC); the TBS22K MCC datasheet.
- Checklist 10: plate potential vs the PRI–SEC / PRI–PE rules, shared with F3; the secondary sink near the ISO2
  primary row (F6).
- Documents: NEXT_REVISION 5.5 / PLAN D3 (shared plate with Q8 / Q21) contradict README Stage 4a; the kicad_dru H7
  comment still quotes 5.18 mm (README stage 14g says so already).
