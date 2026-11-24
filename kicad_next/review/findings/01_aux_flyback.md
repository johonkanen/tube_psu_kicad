# Findings: 01 aux flyback  (reviewer: Claude Opus 5.5, 2026-11-24, commit 3e1e31e)

## Summary
The auxiliary flyback (PWM2 ICE5AR0680AG, TR1 EEL19) agrees with the ICE5AR datasheet: pin map, non-isolated mode
selection, 5V set point, RSel/ABM window, current limit, VCC window, start-up and LOVP divider all check out against
datasheet V2.3 limits. The layout meets its own constraints: drain copper with no inner-layer copper under it,
≥ 1.2 mm on the outer layers, TR1 slot in place, inner barrel distance ≥ 11.1 mm nominal.
**No blocker for ordering in the circuit itself.** Four things should be fixed before the order or the first build:
1. **R68** (12.1 kΩ 1206 bleeder on −100V BIAS) dissipates 0.53–0.59 W in a 0.25 W part, under C102. 5.1 had the same.
2. **The TR1 bobbin is not measured.** No calipers record of base outline, pin diameter or base creepage exists, and
   the footprint drills / row spacing depend on it.
3. **No single TR1 winding spec.** The spec is spread over EEL19_DESIGN.md 12.3 + 14.4 + 16.2, and the Summary / 12.3
   still say SN5 6 T and TEX-E 0.30.
4. **The wrong JLC package string of PWM2 is not in the fab notes.**

## Checklist results
| Item | Verdict | Evidence |
|---|---|---|
| A1 | PASS | `rv sch ref PWM2`: 1 VIN, 2 VERR, 3 FB, 4 CS, 5–8 DRAIN = FLY_C, 9 NC = `unconnected-(PWM2-NC-Pad9)` (no net), 10 GATE, 11 VCC = Net-(D10-K), 12 GND. Datasheet ICE5xRxxxxAG V2.3 (2020-02-03) figure 3 / table 2, p 4–5: the same pin numbers and names. Circuit = datasheet figure 2: VERR divider from 5V, FB RC, CS shunt, GATE pull-up from the bus, VIN divider. Datasheet source: Infineon V2.3, third-party mirror https://cdn.components.ru/media/PDF/8049294.pdf (42 pages, Infineon notice and edition 2020-02-03) |
| A2 | PASS | R138 ‖ R139 = 88.7·49.9/138.6 = 31.93 kΩ (0.1 %). Datasheet table 10 p 22: IERR_P_BIAS min 9.5 µA, VERR_P_BIAS max 0.24 V. 31.93 kΩ × 9.5 µA = **0.303 V > 0.24 V** (+26 %); typical 14 µA → 0.45 V. These are the numbers quoted in CHANGES 1.5 VERR (line 22) |
| A3 | PASS | VERR_REF 1.76 / 1.80 / 1.84 V (table 10) × (1 + 88.7/49.9 = 2.7776) gives **4.889 / 5.000 / 5.111 V**. Load regulation −86 mV (CHANGES line 23) gives a static worst case of 4.80–5.11 V; simulated 5V step −80 / +68 mV (EEL19_DESIGN.md 14.7). Limits used: ±5 % (4.75–5.25 V) for the card on J2 pin 2. No card-side spec exists in the repo (`J2_PINOUT.md` row 2 gives only "5V"). V4 headroom ≥ 1.5 V over 3.3 V |
| A4 | PASS | RSel 750k ±1 % = 742.5–757.5 kΩ, inside option 2 (720–790 kΩ, table 3 p 16). Isel 2.5–3.5 µA (table 13 p 24) gives VFB 1.856–2.651 V, inside VFB_P_BIAS1 max 1.80 V / VFB_P_BIAS2 min 2.76 V: **56 mV margin at the bottom**. τ = 750k × (10n + 2.2n) = 9.15 ms. The selection window runs from VCC 4.44 V to VCC_ON ≥ 15.3 V: ≥ 10.86 V × 20.6 µF / 5 mA = 44.7 ms = 4.9 τ, so FB reaches 99.2 % → 1.841 V, still > 1.80 V |
| A5 | PASS | Rcs = 1.37/2 = 0.685 Ω ±1 %. VCS_N 0.72/0.80/0.88 V (table 11 p 23) gives **1.040 / 1.168 / 1.298 A**. Simulated worst-case peak is 0.88 A at 100 V / 20 W (EEL19_DESIGN.md 14.6), 15 % below the minimum limit. Bpk at 1.298 A = 600 µH·1.298 A / (104·23.4 mm²) = **0.320 T** (0.336 T with Lp +5 %). TDK PC40 Bs at 100 °C is **380 mT** (TDK PC40 data via secondary copies: manualmachine.com/tdk/pc40/22194490-summary-manual, mhw-intl.com/?p=3270), not the 390 mT the document uses: 84–88 % of Bs. R8 / R9: FRC1206F1R37TS 250 mW (LCSC C3000600). At 0.37 A rms primary (100 V / 20 W, 14.1) each carries 0.185 A rms → 0.047 W (19 %) |
| A6 | PASS | Simulated VCC 13.8–14.9 V (14.6). VCC_OFF max 10.4 V (table 7 p 22), VCC_OVP min 24.0 V (table 15 p 25). C58 pad 1 = Net-(D10-K) in `rv sch ref C58` and on the board (`rv bq fp C58`: pad 1 (49.4, 8.2) Net-(D10-K); CP_Elec pad 1 = +). D10 reverse voltage ≤ VCC_ON max 16.5 V with 15V at 0 V. ZLLS400TA VR 40 V (LCSC C460267) → 41 % |
| A7 | PASS | 3 × 4.7 MΩ = 14.1 MΩ. At 450 V: 150 V per resistor; at the highest LOVP trip (510 V): 170 V. C37800 1206W4F4704T5E is rated 200 V / 250 mW (LCSC page). Power 4.8 mW each at 450 V. The datasheet gives no minimum start-up current, only a test condition (table 7: RStartUp 50 MΩ, VDRAIN 90 V ≈ 1.4 µA). At 60 V: (60 − ≈20 V)/14.1 MΩ = 2.8 µA = 2× the datasheet point. 60 V start simulated (EEL19_DESIGN.md 15) |
| A8 | PASS | Trip = VVIN_LOVP × (Rtop + R154)/R154, with VVIN_LOVP 2.75/2.85/2.95 V (table 14 p 25) and all resistors 1 % (C26119 1206W4F1005T5E 10 MΩ ±1 % 200 V; R154 C22823 1 %). Result: **457 / 483 / 510 V**. CHANGES says 460–505 V (small difference, see F9). Minimum trip 457 V > 450 V design maximum. **PFC OVP level: not found in the repository (unknown).** At 510 V, VDS ≈ 675–685 V (14.6), 115 V below 800 V. Per-resistor voltage at 510 V: 170 V ≤ 200 V. The BOM builds the LOVP variant: R151–R153 are in `kicad_next/fab/tube_psu_5_2_bom.csv` (C26119), not DNP |
| A9 | FAIL | VOR = 104/6 × (5.0 + 0.9) = 102 V (correct). Simulated VDS: 622 V at 450 V / 20 W = 78 % ✓. At the highest DC link that A8 allows (LOVP max ≈ 505–510 V): ≈ 675–685 V = **84–86 % > 80 %** (EEL19_DESIGN.md 14.6 "≈ 675 V at 505 V"). Clamp parts: C12 CC1206JKNPOCBN471 470 pF C0G **1 kV** (LCSC C107177) against ≈ 115–230 V clamp (fallback) ✓. R45 1206W4F1004T5E 200 V: ≈ 115 V, 13 mW ✓. R72 1206 0.25 W: ≈ 0.07–0.08 W (clamp total 0.08–0.09 W, 14.8) ✓. D7 S1M 1 kV (LCSC C64915): reverse ≈ DC+ + Vclamp ≤ 650 V ✓. Bench VDS measurement listed in E2 → F5 |
| A10 | PASS | V_R = Vout + VDC × Ns/104. At 450 V / 510 V: D4 (S15 16 T) 15.1 + 69.2 = 84 / 94 V. D5 (A15) 84 / 94 V. D14 (SN5 16 T) 16.3 + 69.2 = 86 / 95 V. D6 (A5 6 T) 31 / 34 V. D29 (S5) 31 / 35 V. ES1D **200 V, 1 A** (LCSC C116492) → ≥ 52 % margin. D8 (SHV 84 T): 84.4 + 363.5 = 448 V; 496 V at 510 V. US1M **1000 V, 1 A** (LCSC C412437) → 50 % margin, ≥ 600 V ✓. Average current ≤ 0.41 A at 20 W (14.9) < 1 A |
| A11 | FAIL | Turns from 14.4 + 16.2: P 52+52, A15 16, A5 6, S15 16, SN5 16, S5 6, SHV 84. The schematic pin use matches exactly: 1 A15 → D5, 2 GND, 3 A5 → D6, 5 SHV → D8 K, 7 S5 → D29, 8 SN5 → D14 K, 9 ISO_GND, 10 S15 → D4, 11 DC+, 12 FLY_C. Dots: P1 starts at FL_DC; S15 9 → 10, SN5 8 → 9, SHV 5 → 9, S5 9 → 7, A15 2 → 1, A5 2 → 3, all starts dotted, same direction. During flyback pins 1 / 3 / 7 / 10 are positive and pins 5 / 8 negative, so D8 / D14 conduct with the anode on the rail ✓. Rails: 0.98 V/T → 16 T ≈ 15 V, 84 T ≈ 82 V, sim 83 V ✓. **But no single winding spec exists**: 12.3 is the full table (S15 2 × TEX-E 0.30, S5+SN5 6+6 bundle, "−5V_SEC", buy list TEX-E 0.30); 14.4 replaces only the strands ("section 12.3 with only the strands changed"); 16.2 changes S15/SN5 and the order ("changes to 14.4 only"). The Summary (lines 16–113) still describes the −5 V / 6+6 build. 12.3 and 16.2 disagree on SN5 turns (6 vs 16) and strands → F3 |
| A12 | PASS | D8 A = −100V BIAS, K = TR1.5. C102 pad 1 = ISO_GND (+) in the schematic and on the board (`rv bq fp C102`: pad 1 (77.0, 13.85) ISO_GND). C102 KCXE1802E560MF 250 V (LCSC C22464691) against ≤ 84.4 V (34 %). C45 FM32X104K631EGG 630 V (LCSC C692295). D14 A = −15V_SEC. C40 CL31A226KAHNNNE 25 V against ≤ 16.25 V with R123 4.7k (EEL19_DESIGN.md 16.3) = 65 %. C44 1206B475K500NT 50 V. Board pads ISO_GND / −15V_SEC as in the schematic |
| A13 | FAIL | P = V²/R at the highest simulated rail voltage, against the LCSC rating. **R68 12.1k on −100V BIAS: 80.2–84.4 V → 0.53–0.59 W against 250 mW (1206W4F1212T5E, LCSC C247391) = 213–236 %.** The other bleeders / preloads: R124 2.61k at 16.41 V (17.34 V old build) → 0.103 (0.115) W = 41 (46) %. R125 2.2k at 15.20 V → 0.105 W = 42 %. R126 1k 0805 at 5.11 V → 26 mW = 21 % of 125 mW. R123 4.7k at 16.25 V → 56 mW = 22 %. R67 12.1k at 5.36 V → 2.4 mW. 5.1 had the same R68 12.1k 1206 on −100V BIAS (`rv sch51 ref R68`), and design document p 8 "12 kOhm resistors … for each output" → F1 |
| A14 | PASS | C1 / C2 EEEFTE221XAP: 600 mA rms at 100 kHz, 160 mΩ, 2000 h at 105 °C (LCSC C190724). Ripple ≈ 0.6 A at 20 W (14.9); scaled to 12 W continuous ≈ 0.36 A (≤ rating). C71 CGA1206X5R107M100NT 10 V (5 V/10 V = 50 %). C6 / C36 / C114 / C115 CL31A226KAHNNNE 25 V (20 %). Effective capacitance: C12891 ≈ 9 µF at 15 V (EEL19_DESIGN.md 16.4). The DC-bias curves of C12891 / C6119961 at 5 V were not fetched (see "Could not verify") |
| A15 | PASS | `rv sch cmp51 1`: R64, R81, R84, R85, R86, C50, N5V_OUT only in 5.1. `rv bq fp R64,R81,R84,R85,R86,C50`: "not on the board" ×6. No net AUX_FB in the board (`grep -c "IW1818\|AUX_FB"` board = 0). The only sheet mention is the note at 01_aux_supply.kicad_sch:11825 ("dropped in 5.2"). Nothing 5.1 needed is missing: the VCC chain, the clamp and all rectifiers / caps are kept |
| B1 | PASS | Basis = design document table 1.1 (p 5; no measured 5.2 card / driver currents in the repo): 15V 0.2 A + 5V 0.2 A + 15V_ISO_SEC 0.2 A + 5V_ISOL 0.2 A = 3 + 1 + 3 + 1 = 8.0 W; −15V 50 mA = 0.75 W; −80 V 10 mA = 0.8 W; sum 9.55 W. Preloads / bleeders at nominal rails: R125 0.10 + R126 0.025 + R124 0.087 + R123 0.05 + R67 0.002 + **R68 0.57** = **0.84 W**. **Total ≈ 10.4 W ≤ 12 W** (10 W in the design document p 5). Preloads / bleeders are ≈ 8 % of it, two thirds of that in R68. Simulated nominal Pin 6.5 W (section 15). Bench state ≈ 2 W measured (section 15) |
| B2 | PASS | Simulated ranges (EEL19_DESIGN.md 16.3): 15V 14.16–15.19 V; 15V_ISO_SEC 14.45–16.41 V (17.34 V in the old build); 5V_ISOL 4.71–5.32 V; −80 V 80.2–84.4 V. UCC21520 (DRV3 / DRV5 / DRV6), SLUSCJ9F rev. Nov 2024, table 6.3: VDD 9.2–25 V recommended (8 V UVLO), 30 V abs max; UVLO off ≤ 8.4 V. VCCI 3–18 V for 5V_ISOL. UCC27511 (DRV1 / DRV2), SLUSAW9F rec. op.: VDD 4.5–18 V, abs max 20 V. C2 25 V (69 % at 17.34 V), C43 CL10A105KB8NNNC 50 V, C72 1206B475K500NT 50 V. −80 V nominal per design doc p 5 ✓. MIC5205 (V2) input range: datasheet not fetched (5.36 V is far inside any 5 V LDO range, but stated as not verified) |
| B3 | PASS | Simulation with the schematic FB network (R140 4.7k + C138 10n, C139 2.2n, R141 750k) at 100 V and 450 V: EEL19_DESIGN.md 14.7 `step100` / `step450` (5V −80 / +68 mV and −75 / +61 mV, back within 1 % in < 0.1 ms, no ringing), `ccm100` (no subharmonic, 200 cycles), start-up vs OLP. Behavioural ngspice model, not the vendor model → the bench 5V load step remains in E2 |
| B4 | PASS | Board: FLY_C fill F.Cu 124.6 mm² + B.Cu 68.8 mm² = **1.93 cm²**, 10 vias 0.8/0.4 (`rv bq net FLY_C`). That is below the 2–3 cm² target (README line 623 says 1.92 cm²). RthJA 94 K/W for the 0680AG with minimum drain copper (datasheet table 5 p 21, JEDEC 2 oz single-sided). At 450 V the loss is dominated by the capacitive turn-on and barely depends on load: 0.17–0.65 W (14.8 table: 0.04 conduction + 0.12…0.60 switch + 0.02 controller). Tj = 50 °C + P × RthJA: at 94 K/W **66…111 °C** (pessimistic 10 ns model at min copper), realistic 0.3–0.45 W → 78–92 °C. With 1.93 cm² RthJA is below 94 K/W (the 70 K/W is an assumption, not a datasheet value) → ≤ 110 °C at 12 W. 20 W: 14.8 gives ≤ 93 °C at 70 K/W, ≤ 108 °C at 94 K/W |
| C1 | PASS | `rv bq near FLY_C --within 3.5`: nearest other copper on the outer layers is 1.200 mm (GND / FB / GATE / U10A). Inner layers: `rv bq xsec '*' In1.GND / In2 / In3 / In4 y −2 … 13, x 40 … 48`: only the FLY_C via barrels (0.774 mm chords at y 1 / 4), no other copper. Nearest inner copper is GND at (48.3, 2.2), 1.9 mm, outside the keep-out `S2_KO_PWM2_drain` (polygon x 39.1 … 58.6, y −2.6 … 14.6; pours forbidden, tracks / vias allowed). FB F.Cu (49.38, −0.74 → 2.0) runs ≈ 2.7 mm along the drain copper at 1.2 mm (negligible coupling: ≈ fF into 2.2 nF). PWM2-VIN on B.Cu partly lies under the F.Cu drain pour → F6 |
| C2 | PASS | Loop C15.2 → TR1.11 → TR1.12 → PWM2.5 → PWM2.4 → R9 → C15.1, through pad centres: **50 mm path, 65 mm²** (`rv bq loop`). 5.1 (C15 → TR1.4 → TR1.5 → PWM2.8 → PWM2.1 → R8 → C15): **34.6 mm, 32 mm²**. The loop closes locally: C15 GND via (50.1, 1.6), Rcs GND via (49.99, −4.1) and PWM2 pin 12 via (54.25, 2.9) all lie within 7 mm of each other on the In1 / In4 GND planes, which are solid there (x > 48.3). DC+ C15.2 → TR1.11 on B.Cu 0.6 mm (neck 0.59 mm). The loop is ≈ 2× 5.1 because of the fly-lead hole positions → F7 (note) |
| C3 | PASS | Distances from the pin pads: C139 2.4 mm (pin 3); C140 2.2 mm, R154 5.2 mm (pin 1); R139 2.6 mm, R138 4.6 mm (pin 2); R140 5.1, C138 5.8, R141 6.5 mm (pin 3; RSel and lag network, DC / sub-kHz nodes); R9 3.2 mm, R8 5.3 mm (pin 4); C51 GND 0.8 mm from pin 12, VCC 3.8 mm from pin 11 (through via 52.97, 2.9). VERR total track 7.5 mm, FB 12.0 mm. The Rcs GND return to pin 12 runs through the plane (vias 49.99, −4.1 → 54.25, 2.9), not a dedicated track. CHANGES 1.5 VERR says "divider at pin 1" where it means pin 2 (doc slip, F9) |
| C4 | PASS | `rv bq neck DC+ F.Cu 61.316 11.222 39.2 15.863` = 0.50 mm (≤ 0.37 A rms at 100 V / 20 W). `near DC+ --within 1.3` in this area: only PWM2-VIN on B.Cu 1.274 mm and FLY_C B.Cu 1.285 mm (≥ 1.2). Edge: DC+ F.Cu track at y 17.95 w 0.5 → copper at 18.20, Edge.Cuts at 18.70 → 0.50 mm ≥ 0.3. Chains: R114 / R115 / R116 F.Cu column x 39.2; non-adjacent nodes DC+ ↔ R114-Pad1 2.54 mm, R115-Pad1 ↔ GATE 5.30 mm, DC+ ↔ GATE 5.68 mm. R151–R153 B.Cu: R151-Pad2 ↔ VIN 4.55 mm, DC+ ↔ R152-Pad2 6.56 mm |
| C5 | PASS | Widths: TR1.1 → D5 0.6 mm, TR1.3 → D6 0.8 mm, TR1.10 → D4 0.5 mm, TR1.7 → D29 0.8 mm; SN5 / SHV through small pours (D14-K 12.8 mm², D8-K 6.6 mm²). These match the README "Flyback windings" row (line 611). First caps at the diode: C39 2.8 mm from D5 K (C1 ≈ 11 mm, 0.84 mm track). C3 / C2 at D4 (neck 2.4 / 7.6 mm). C6 / C36 / C71 3 mm from D6 K (via). C114 / C115 at D29 K (1.77 mm neck). C44 / C40 at D14 A (5.5 mm neck). C45 / C102 at D8 A (1.45 / 3.86 mm). Returns to TR1.2 / TR1.9 through ≥ 1.0 mm copper + planes |
| C6 | PASS | Slot x 62.92 … 64.12 (1.2 mm), y −14.28 … 13.73 (`rv bq slots`). `rv bq dist @PRI @SEC`: F.Cu 6.93 mm board-wide minimum (elsewhere); locally FLY_C ↔ ISO_GND 9.44 mm; B.Cu 8.77 mm. **Inner layers 11.114 mm** (TR1.11 barrel ↔ TR1.5 barrel, all four layers): ≥ 11.1 by 14 µm, see F8. padgap TR1.11–TR1.5 10.27 mm, TR1.2–TR1.9 11.02 mm (straight, both fenced by the slot; surface path 12.86 mm per README line 2154). KiCad creepage passes were reported clean today. Copper inside the band x 58.5 … 68.5 (other than TR1 pins): primary DC+ B.Cu / F.Cu feed to TR1.11 and GND near TR1.2 (x ≤ 61.8); secondary ISO_GND F.Cu pour x 66.42 … 68.5 and D14-K pour x ≥ 67.7. **Nothing crosses the slot**, but the literal band rule is not met → F10 (note) |
| C7 | CANNOT VERIFY | README line 2171 "Still to confirm with calipers: EEL19 4+6 bobbin base outline (15.8 × 22.5 is 5+5 data), pin diameter (drills 1.0 / 0.9 mm), seated height and the real base creepage between the rows". The only bobbin data is the seller's (EEL19_DESIGN.md 6a: 3.5 / 2.7 mm pitch, 12.5 mm rows). No measurement is recorded anywhere (grep "caliper" / "measured") → F2 |
| C8 | PASS | Datasheet figure 39 p 39 (Z8B00168485 rev 02): e 1.27, b 0.35–0.51, b1 3.81 BSC, D 9.8–10.0, E 5.8–6.2, E1 3.8–4.0, L 0.39–0.89, index at pin 1, bottom row 1-2-3-4-gap-5-6, top 7-8-gap-9…12 with 12 opposite 1. Footprint on the board (`rv bq fp PWM2`): pads 1.95 × 0.6 at pitch 1.27, rows 4.95 mm apart (SOIC-16 standard), pin 4 → 5 = 3.81 mm, pin 12 opposite pin 1, pin 7 opposite pin 6, no exposed pad. `rv bq padgap PWM2.4 PWM2.5` = 3.210 mm ≥ 3.0; PWM2.8–PWM2.9 3.210 mm |
| D1 | PASS | `rv sch bom 1`: every part has an LCSC number except TR1 (consigned, hand-wound) and the five faston terminals (consigned). Low stock / review: **R124 C245506 stock 75** (alternative C229516, 43); **PWM2 C17699638 public stock 3** (owner has 10 in JLC parts stock); C102 C22464691 386; C37800 (R114–R116) 1886; D10 C460267 5662 |
| D2 | FAIL | "BSOP-12-EP-300mil is wrong" appears only in `lib/jlc_parts_next.csv:162`, CHANGES line 21 and README line 2138. `kicad_next/fab/README.md` (where the order is prepared) lists PWM2 only for parts stock (line 205), anchor offset 0.42 mm (line 179) and "PG-DSO … check rotation" (line 172). It does not say that JLC's library package is wrong and the KiCad footprint is right → F4 |
| E1 | listed (not graded) | See "Bring-up" under F5 |
| E2 | listed (not graded) | See "Bring-up" under F5 |

## Findings (ranked, most severe first)

### F1 R68 (−100V BIAS bleeder) runs at 2.1–2.4× its power rating, under C102
- Severity: **should fix** (a rating exceeded on paper; same as 5.1)
- What is wrong: R68 12.1 kΩ 1206 (UNI-ROYAL 1206W4F1212T5E, 250 mW) sits across −100V BIAS ↔ ISO_GND. At the simulated
  80.2–84.4 V it dissipates **0.53–0.59 W**. It is on B.Cu at (75.2, 11.2), directly under the body of C102 (56 µF 250 V
  electrolytic, F side, body x 72–82, y 6.4–16.4). C102's base therefore sits over a > 0.5 W hot spot. The 5.1 board had
  the identical part (`rv sch51 ref R68`), so this does not make 5.2 worse than 5.1, but it was never inside the rating.
- Evidence: P = 84.4² / 12 100 = 0.589 W; LCSC C247391 page: 250 mW, 200 V. `rv bq fp R68,C102` for the positions.
  The simulations use 12.1k as the −80 V bleeder (EEL19_DESIGN.md 14.6: −80 V 80.2–84.3 V).
- Smallest fix: keep 12.1 kΩ (the simulated cross regulation assumes it) and use a 1 W part. Options: a 2512
  12.1 kΩ 1 W (footprint change, ≈ 59 %), or two 1206 24.3 kΩ in parallel plus a second site (still 0.29 W each, so
  2512 preferred). If possible move it out from under C102. A larger R68 needs a re-simulation of the bleeder-only
  −80 V case.
- Confidence: high on the arithmetic and the part rating; medium on the operating voltage (simulated, not measured).
  A bench reading of −80 V on N80V_OUT plus a thermocouple on R68 on 5.1 would settle it.

### F2 TR1 bobbin dimensions not measured: footprint drills, base outline and base creepage unconfirmed
- Severity: **should fix — measure before ordering** (if a pin does not fit, TR1 cannot be mounted)
- What is wrong: the footprint uses seller data (3.5 / 2.7 mm pitch, 12.5 mm rows) with drills 1.0 / 0.9 mm and the
  5+5 base outline 15.8 × 22.5 mm. The base creepage between the rows (≥ 11.1 mm needed, EEL19_DESIGN.md 12.5) is also
  unmeasured. README line 2171 lists all of this as open.
- Evidence: README line 2171; EEL19_DESIGN.md 6a / 12.5; no record in the repo (grep "caliper", "measured").
- Smallest fix: measure the bought bobbin and record the results next to README line 2171:
  - pin diameter / cross-section (drill = pin + 0.3 mm);
  - the pitch of both rows over the full row (cumulative error);
  - the row-to-row distance;
  - base outline and standoff positions;
  - surface creepage between the rows across the base.
  Then regenerate the footprint only if a number differs.
- Confidence: high that it is unrecorded; the size of the risk is unknown until measured.

### F3 No single TR1 winding specification; the Summary and 12.3 still show the superseded −5 V build
- Severity: **should fix** (a document that will mislead the winder)
- What is wrong: the build that the schematic needs (SN5 16 T in the S15 layer, pin 8 → 9) is only in EEL19_DESIGN.md
  16.2, written as a delta: "changes to 14.4 only". 14.4 is itself a delta: "section 12.3 with only the strands
  changed". 12.3 is titled "(winding spec)" and lists:
  - S5 + SN5 6 + 6 T in a 6-strand bundle;
  - S15 2 × TEX-E 0.30;
  - a buy list with TEX-E 0.30;
  - "−5V_SEC".

  The Summary (lines 16–113) also describes the −5 V build. A winder who follows "12.3 winding spec" winds SN5 with
  6 turns, and the −15V_SEC rail comes out at ≈ −5 V.
- Evidence: EEL19_DESIGN.md 12.3 table (lines ≈ 739–750), 14.4 line 1335, 16.2 "Winding spec (changes to 14.4 only…)".
  The pins and dots are consistent across all three (A11), so only the text is the problem.
- Smallest fix: one consolidated table (P1 | S15+SN5 | SHV | S5 | A5 | A15 | P2, turns, wire, start/finish pins, dots,
  Lp 600 µH ± 5 %, hipot) at the top of EEL19_DESIGN.md or in a short TR1_WINDING.md. Mark 12.3 / 14.4 as superseded.
- Confidence: high.

### F4 The wrong JLC package string of PWM2 is not in the order notes
- Severity: **should fix** (order document)
- What is wrong: JLC lists C17699638 as "BSOP-12-EP-300mil". The real package is a 3.9 mm SO body without exposed pad
  (datasheet figure 39), which is what the KiCad footprint has. `kicad_next/fab/README.md` does not say this, so the
  placement preview will show JLC's (wrong) model. The 0.42 mm anchor offset is correct, and the note should say so:
  the anchor is the body centre, because the pads are removed asymmetrically from SO-16; the pad centroid is at
  x 50.22 against anchor 49.8.
- Evidence: grep "BSOP" → only lib/jlc_parts_next.csv:162, CHANGES:21, README:2138. fab/README lines 172, 179, 205.
- Smallest fix: one line in fab/README "Before ordering", for example: "PWM2: JLC's package string BSOP-12-EP-300mil
  is wrong. The part is PG-DSO-12 = SO-16 narrow body with 2 positions per side empty, no EP. Footprint and CPL anchor
  (= body centre) are right; check pin 1 in the preview against datasheet figure 3."
- Confidence: high.

### F5 VDS at the upper LOVP trip ≈ 675–685 V (84–86 % of 800 V); clamp only simulated
- Severity: **note** (no rating exceeded; the 80 % guideline is exceeded only at a bus above the 450 V design range)
- What is wrong: with LOVP fitted the converter runs up to 457–510 V DC+, where the simulated VDS is ≈ 675–685 V. The
  real leakage inductance (model 3.1 µH "P with all others shorted", 12.3) and therefore the clamp voltage are unmeasured.
- Evidence: EEL19_DESIGN.md 14.6 (622 V at 450 V; ≈ 675 V at 505 V); A8 trip calculation 457 / 483 / 510 V.
- Smallest fix: none before ordering. Do the bench measurement, and use the documented fallback (R45 2 × 100 kΩ,
  C12 1 nF 1 kV) if VDS > 650 V at 450 V.
- Confidence: medium (behavioural model).
- **Bring-up (E1 / E2):**
  1. Run TR1 + PWM2 alone from a current-limited 60 V supply on DC+, with no control card and nothing driving the 5V
     rail (a back-fed 5V changes the VERR mode detection only harmlessly, but keep it clean).
  2. Expect VCC to ramp in two steps to 16 V. Datasheet eq. 1 with C ≈ 25 µF: tA = 1.1 V·C/0.09–0.35 mA ≈ 0.08–0.5 s
     (SCP up to 1.9 V), then tB = 14.9 V·C/1–5 mA ≈ 0.075–0.37 s. Then a 12 ms soft start, and the rails within ≈ 17 ms
     (section 15).
  3. Probe VCC (C51 / C58), 5V (C6 / C36 / C71 or J2 pin 2), 15V (C1 / C39), VERR (R139), FB (C139) and the isolated
     terminals P15V_OUT / N15V_OUT / N80V_OUT / P5V_OUT against SEC_GND.
  4. Wrong mode or open loop: FB sits above 2.73 V, OLP trips after 30–54 ms, and the IC goes into odd-skip auto-restart.
     The rails then come up in repeating bursts and 5V never settles.
  5. Then measure:
     - VDS at 400 / 430 / 450 V with a ≥ 1 kV differential probe at D7 anode / TR1.12 (FLY_C pads) against GND
       (C15.1 / R8.2);
     - drain copper temperature (IR / thermocouple on the F.Cu FLY_C pour, 41–47 × −1…13);
     - the LOVP trip (raise DC+ slowly to ≈ 510 V, watch VIN on C140);
     - a 5V load step 0.1 ↔ 0.2 A;
     - the bleeder-only rail voltages (15V_ISO_SEC, −15V_SEC, −80 V);
     - the R68 temperature (F1).
  6. No dedicated test points and no silkscreen: use the assembly drawing to find the pads.

### F6 PWM2-VIN (178 kΩ ‖ 470 pF node) routed under the F.Cu drain pour and 1.2 mm from the B.Cu drain copper
- Severity: **note**
- What is wrong: the VIN track runs on B.Cu (55.15, 3.7) → (55.15, 9.1) → (48.0, 10.6) → R153. 1.21 mm² of it lies
  directly under the F.Cu FLY_C pour (bounds 51.9…55.25 × 6.9…10.7; no inner plane in between because of the
  keep-out), and it comes within 1.2 mm of the B.Cu FLY_C copper at (45.75 / 46.95, 10.48). The 0–620 V, 100 kHz edges
  couple a few 0.01–0.1 pF into 470 pF, i.e. tens of mV up to ≈ 0.1 V. That is noise on VIN, which has only ≈ 0.1–0.2 V
  margin to the minimum threshold at 450 V (VIN 2.65 V vs 2.75 V). The 250 µs blanking and the 83 µs RC filter make a
  false trip unlikely.
- Evidence: shapely overlap of the VIN B.Cu tracks with the FLY_C F.Cu fill (b52.json); `rv bq near FLY_C` line
  "Net-(PWM2-VIN) 1.200 mm B.Cu at (45.75, 10.48)".
- Smallest fix: none needed for the first board. Watch for early LOVP trips during the LOVP bench test. If they occur,
  increase C140 (e.g. 1 nF, τ 180 µs).
- Confidence: low (coupling estimated, not simulated).

### F7 Primary switching loop ≈ 2× the 5.1 area
- Severity: **note**
- What is wrong: through pad centres the loop is 65 mm² / 50 mm (5.2) against 32 mm² / 34.6 mm (5.1), plus the fly
  leads themselves. This follows from the fly-lead holes at y 11.2 (part of the given TR1 decision).
- Evidence: `rv bq loop C15.2 TR1.11 TR1.12 PWM2.5 PWM2.4 R9.1 R9.2 C15.1` and the 5.1 equivalent (C2 row).
- Smallest fix: none for ordering. Keep the fly leads short and twisted, and include the aux supply in the EMI pre-scan.
- Confidence: medium (pad-centre estimate).

### F8 TR1 inner-layer barrel distance is 11.114 mm nominal, while README says 11.2 mm
- Severity: **note** (owned by checklist 10)
- What is wrong: FL_DC (TR1.11, drill 1.2) to pin 5 (drill 0.9) barrels measure 11.114 mm on In1–In4, against the
  11.1 mm inner-layer rule. README line 2154 says "now 11.2 mm". PTH holes are drilled ≈ 0.1 mm over the finished size,
  so the real barrel walls end up ≈ 0.1 mm closer (≈ 11.0 mm).
- Evidence: `rv bq dist @PRI @SEC` → In1…In4 11.114 mm between (61.740, 10.798) and (69.448, 2.790).
- Smallest fix: correct the README number to 11.11 mm. If the 11.1 mm inner rule is meant with tolerance, move FL_DC
  0.2 mm further away in the footprint generator (checklist 10 to decide).
- Confidence: high on the number; the tolerance interpretation is checklist 10's.

### F9 Small document inconsistencies in this part
- Severity: **note**
- What is wrong:
  - LOVP window: CHANGES 1.5 VIN / EEL19_DESIGN 14.9 say "≈ 460–505 V"; with 1 % resistors and VVIN_LOVP 2.75–2.95 V
    it is 457–510 V.
  - CHANGES 1.5 VERR ends "Layout: divider at pin 1"; VERR is pin 2.
  - EEL19_DESIGN uses PC40 Bsat 0.39 T at 100 °C; TDK PC40 data gives 0.38 T, so Bpk 0.32–0.336 T is 84–88 % of Bs.
  - The EEL19_DESIGN Summary still quotes the −5 V rail.
- Evidence: A3, A5, A8 rows.
- Smallest fix: edit the four lines.
- Confidence: high.

### F10 Secondary copper under the TR1 bobbin, inboard of the isolated pin row
- Severity: **note**
- What is wrong: the ISO_GND F.Cu pour reaches x 66.42 and the D14-K pour x 67.7, i.e. 2.5 mm inboard of the isolated
  pads (x 69.77, pad edge 68.97), under the bobbin where the bottom yoke of the (primary-potential) core sits. Nothing
  crosses the slot, and surface creepage passes. The core-to-secondary distance is to be covered by the 3-layer tape
  around the yoke and the hipot (EEL19_DESIGN.md 12.5), but this copper is closer to the core than the pins assumed there.
- Evidence: shapely clip of all copper to x 58.5…68.5, y −16.1…14.0 (b52.json): F.Cu ISO_GND 18.5 mm² at x ≥ 66.42,
  F.Cu D14-K 1.9 mm² at x ≥ 67.73. Primary DC+ / GND copper at x ≤ 61.8.
- Smallest fix: optional — pull the ISO_GND / D14-K pours back to x ≥ 68.5 (pour keep-out), or keep it and include it
  in the hipot after the tape is applied.
- Confidence: medium (real core/base geometry unknown, see F2).

### F11 Two 2000 h electrolytics in warm spots
- Severity: **note**
- What is wrong:
  - C58 (22 µF 35 V, KNSCHA RVT, 2000 h at 105 °C, C2887274) sits on B.Cu half under PWM2: courtyard overlap in plan
    x 46.5–52.3, y 2.0–5.9, next to the drain copper.
  - C1 / C2 (2000 h at 105 °C) run at their ripple rating at 20 W.

  At a local 70 °C the Arrhenius estimate for C58 is ≈ 2000 × 2^3.5 ≈ 22 000 h.
- Evidence: `rv bq fp PWM2,C58`; LCSC pages C2887274, C190724.
- Smallest fix: none for ordering. Measure the board temperature at C58 during the drain-copper test. A 105 °C / 5000 h+
  part in the same 5 × 5.4 footprint is a BOM-only option.
- Confidence: low (temperature unknown).

## Compared with 5.1
- **Better:**
  - Controller margins are datasheet-backed: VERR mode detection 26 % margin, RSel inside option 2, Ilim min 15 %
    above the 100 V / 20 W peak.
  - 100–450 V range (5.1 ≈ 90 V start, 325–400 V).
  - LOVP added.
  - D8 1000 V (5.1 ES1A on a 448 V reverse stress).
  - D4 / D5 / D14 ES1D 200 V (5.1 schematic ES1A).
  - C40 25 V for −15 V.
  - Preloads on 15V / 5V.
  - VCC hold-up 22 µF.
  - The TR1 barrier has a 1.2 mm slot (5.1: no slot, EF20 rows 10.2 mm).
  - Inner-layer barrels without rings.
- **Equal:**
  - Clamp D7 / R72 / R45 / C12.
  - C15 100 nF (now 630 V 1210).
  - R68 / R67 12.1k bleeders. R68 is overloaded in both (F1).
  - VCC via D10 from 15V.
- **Worse:**
  - The primary switching loop area ≈ 2× (65 vs 32 mm², F7).
  - Simulated VDS 571 V at 400 V / 20 W vs 520 V design value on 5.1 (design doc table 2.1). That is at 2× the 5.1
    power, and still < 80 % at ≤ 450 V.
- 5.2 meets the acceptance bar for this part once F1–F4 are dealt with.

## Could not verify
- Real TR1 bobbin: pin diameter, base outline, standoffs, base creepage, core/yoke height above the board. Needs
  calipers (F2, F10).
- PFC OVP level (needed for the LOVP trip margin of A8): not found in the repository.
- Real leakage inductance → clamp voltage / VDS, D8 / D14 ringing, drain-copper temperature, LOVP trip, 5V load step,
  bleeder-only rail voltages, R68 / C58 temperatures. All need the first board (F5).
- DC-bias effective capacitance of C12891 (22 µF 25 V) and C6119961 (100 µF 10 V) at 5 V: the manufacturer curves
  were not fetched. Only the document's ≈ 9 µF at 15 V is quoted.
- Ripple-current rating of the Ymin KCXE 56 µF (not on the LCSC page; the rail current is only 10–18 mA, so low risk).
- MIC5205 (V2) input range: datasheet not fetched.
- TDK PC40 Bs: taken from two secondary copies of TDK data (380 mT at 100 °C), not from a tdk.com PDF.
- The ICE5AR datasheet V2.3 was read from a third-party mirror (cdn.components.ru). Content and edition match
  Infineon V2.3 2020-02-03.
- Card / gate-driver actual currents for B1: the design-document table 1.1 maxima were used.

## Outside scope
- **Checklist 12:** courtyard overlaps in this area in `reports/next/drc.json`: C40/C2, C40/C44, C114/D29, C45/D14,
  D5/C39, C71/C36, C6/C36, R115/R116, R115/R114, J2/D10, C2/R123, C39/C1, D14/C44, C14/C1.
- **Checklist 12:** two starved thermals on C102 pad 1 (ISO_GND) on In1 / In4.
- **Checklist 10:** the inner-layer TR1 barrel distance tolerance (F8).
- **Checklist 10:** the primary ↔ secondary surface path through the 2.6 mm gap between the TR1 slot (top y −14.28)
  and the ISO2 slot (bottom y −16.85), with the 15V parts D5 / C39 / C1 west and TR1-S15 / D4 east. Reported clean by
  today's creepage passes; worth a look as the tightest geometric spot of the TR1 barrier.
- **Checklist 14:** PWM2 rotation in JLC's preview (fab README "Rotations: NOT verified") together with F4.
- **Checklist 10:** DC+ F.Cu track 0.5 mm from the south board edge (y 17.95–18.2 vs edge 18.7). Fine for JLC; its
  distance to chassis / earthed hardware is checklist 10's.
