# Findings: 05 PFC / EMI filter / inrush  (reviewer: Claude Opus 5.5, 2026-11-24, commit 3e1e31e)

## Summary
The circuit is the same as on the working 5.1 board: same connectivity, same values, same drive polarity. The new
UCC27511A drivers are wired correctly. I found **no blocker for ordering**. Four layout regressions against 5.1 are
worth fixing before ordering, and each fix is small:
1. Mains RES_IN to IN2 is 1.81 mm on F.Cu (5.1: 8.61 mm), because the IN2 pour was rerouted when PE moved.
2. The DC+ link at SICD1 is 1.34–1.44 mm on F.Cu plus a 1.0 mm B.Cu track (5.1: 5.45 mm). The drain neck from Q5
   to SICD1.A is 1.37 mm (5.1: 4.55 mm).
3. The 4.7 µF VDD capacitors of DRV1 / DRV2 are 2.5–4.2 mm from the driver pins (5.1: 0.5–0.7 mm).
4. The X-capacitor discharge takes 3.5–4.4 s, above the 2 s that IEC 62368-1 allows. This is the same as 5.1.

L1 / L2 still have no measured inductance (consigned parts, as 5.1). Stages 13a–13d do not touch this area, except
H4 / H7, which are now NPTH without a ring.

Where the board differs from the checklist numbers, I used the board:
- The SICD1 neck on F.Cu is 1.34 mm (widest channel) and 1.44–1.48 mm (cut width), not "about 1.25 mm".
- 5.1 had 5.45 mm at the same cut.

## Checklist results
| Item | Verdict | Evidence |
|---|---|---|
| A1 | PASS | `rv sch sheet 5`: L2 1=AC1 / 2=PFC_DRAIN_1; L1 1=PFC_DRAIN_2 / 2=AC2; SICD1/2 K=DC+; Q5.3 / Q6.3 → R93 / R21 4m → GND; DB1 1=AC2, 3=AC1, 2=DC+, 4=GND; C64/C66 AC1/AC2→GND. `rv sch cmp51 5`: only the renamed drain nets (Net-(L2-2)/Net-(L1-1) → PFC_DRAIN_1/2), the L1/L2 symbol (RM8 pri1/pri2 → pads 1/2) and footprint-library changes. DB1 uses the same footprint `D_Bridge_TBS` and pin nets as 5.1 (`rv bq51 fp DB1`), so 1/3 = AC, 2 = +, 4 = −, as on the working board. I could not fetch the TBS22K package drawing itself (JLC page only). |
| A2 | PASS | Path IN1 → RES_IN → R27 (pad 2 RES_IN, pad 1 RL1-COM) → COM; NO = RES_IN; NC unconnected (`rv sch sheet 5`). First-cycle peak 325 V / 47 Ω = 6.9 A. Energy in R27 ≈ ½·328 µF·325² = 17.3 J. Ohmite TWM/TWW series sheet (digikey copy https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/7182/twm-tww-series.pdf, p1): TWW10 is 10 W, 750 V, short-time overload "TWW: 10× rated power for 5 s" = 500 J, so 17 J is about 3.5 %. Input current at 540 W, η 0.92: 2.55 A rms. Songle SRD datasheet (LCSC C35449 pdf, UL listing table): 10 A 250 VAC (15 A NO), so the contact runs at 26 % of rating. **Relay never closes:** 2.55² × 47 = 305 W in R27 at full load, ≈ 47 W at 1 A. Nothing protects against this (no fuse, no thermal fuse), as 5.1 – note F10. |
| A3 | **FAIL** | Circuit: 5V → RL1.4, RL1.5 → Q9.D; D9 A = Q9-D → D28 → K = 5V (flyback path correct); GPIO → R44 2.2k → gate, C35 100 n; R32 2.2k on the J2 side. Gate time constant 0.22 ms. Coil (SRD datasheet, coil table, 5 V "L" type 0.36 W): 71.4 mA, 70 Ω. BSS138LT1G (onsemi BSS138LT1/D Rev. 15): VGS(th) 0.85–1.5 V, rDS(on) ≤ 10 Ω at VGS 2.75 V, ID 200 mA. At 3.0 V gate the drop is ≤ 0.71 V, so the coil gets ≥ 4.3 V, above the 75 % (3.75 V) pick-up voltage, and Q9 dissipates 51 mW. Turn-off drain ≈ 5 V + 2 Schottky drops ≪ 50 V. Pads (`rv bq fp Q9`): pad 1 D alone at (−61.64, −31.9), pads 2 G and 3 S on the two-lead side. Footprint descr "pad 1 = JEDEC pin 3, pad 2 = pin 1, pad 3 = pin 2", BSS138 SOT-23: 1 G, 2 S, 3 D, so the pads match. **FAIL** because the schematic value is still `2n7000` (`rv sch part Q9`: value 2n7000, mpn BSS138LT1G). A hand builder working from the schematic would fit a 2N700x, whose threshold can reach 2.5–3 V. See F7. |
| A4 | **FAIL** | C86 + C38 + C117 = 1.83 µF. R4–R6 = 1.41 MΩ from RES_IN to IN2 at the terminal side, and they discharge C86 through R27, C38 / C117 through the chokes. τ = 2.58 s, so 325 → 60 V (1.69 τ) takes 4.4 s. Adding the VAC divider R47/R48 + R50–R52 (6 MΩ AC1–AC2 through the U8 bias, sheet 9) gives τ = 2.09 s and 3.5 s. Both exceed the 2 s of IEC 62368-1 for pluggable type A. Same as 5.1 (no value change in `rv sch cmp51 5`). Resistor voltage: 230/3 = 77 Vrms (108 V pk) each. UNI-ROYAL datasheet (LCSC C17997): 1206 max working voltage 200 V, overload 400 V – OK. X2 class: C86 / C117 C2888216 Dongtong MKP62-275V684KP22.5 X2 275 V (jlcpcb.com/partdetail/C2888216); C38 C3297747 KEMET R46 X2 275 V; C64 / C66 C3298405 TDK B32921 X2 305 V (LCSC product pages) – all ≥ 275 VAC. See F5. |
| A5 | PASS | C65, C81, C82, C84, C85 = C96522 TDK CS45-E2GA222M-NKA, X1/Y2 300/440 VAC (LCSC product page / datasheet). Leakage per 2.2 nF at 230 V 50 Hz is 0.159 mA. With one pole live: C85 (or C84) + C81 (or C65) = 0.32 mA, plus C82 (GND→PE, which sees the half-wave negative mains through DB1) ≈ 0.1 mA, so ≈ 0.4 mA total; ≈ 0.6 mA with the neutral open. This is far below the 3.5 mA allowed for PE-connected equipment. |
| A6 | PASS | Values are unchanged against 5.1 (`rv sch cmp51 5`: no value changes besides L1/L2). Figure 3.1 of the design document (p 12) itself shows C86 680n, C38 **470nF**, C117 680n; the "three 680 nF" on p 15 is text only. CM1 / CM4 KEMET SCF20-05-550 (KEMET LF0012_SCF 11/12/2019, Table 1): 5 A rated, 5.5 mH min, 28 mΩ. 5 A / 2.55 A = 1.96 ≥ 1.5. |
| A7 | PASS | Wolfspeed C2M0160120D Rev. 07 Oct 2024 (assets.wolfspeed.com …C2M0160120D_data_sheet.pdf, p1–2): VDS 1200 V (bus 400–450 V); ID 12 A at TC 100 °C; IDM 40 A; VGS op −5/20 V, VGS max −10/+25 V; VGS(th) 2.0–4 V (2.4 V typ at 150 °C); RDS(on) 160/196 mΩ is specified at VGS 20 V only, so the 15 V drive carries an RDS(on) penalty (curves only, not quantified here); Crss 5 pF, Ciss 606 pF, RG(int) 6.5 Ω, Qg 40 nC. Peak current from my DCM/CCM calculation (L = 200 µH as the 5.1 schematic, f 133 kHz as p 15, 540 W, η 0.95): 4.6 A, with partial CCM over 65 % of the half-cycle, which agrees with p 12 ("partial continuous conduction over 400 W"). Off state 0 V through 5 Ω + 6.5 Ω: in a boost the drain dv/dt happens at the device's own turn-off, or as slow DCM ringing, so I see no Miller turn-on risk. Drive levels are the same as 5.1 (15 V / 0 V). Note F8: the gate resistance is 5 Ω each way, where 5.1 had 2.5 Ω (R1 ‖ R14 on one output). |
| A8 | PASS | Wolfspeed C3D02060A Rev. 10 Oct 2024 (assets.wolfspeed.com/uploads/2020/12/C3D02060A.pdf, p1–2): VRRM 600 V; IF 4 A at TC 135 °C, 2 A at TC 161 °C; IFSM 15 A at TC 110 °C (10 ms); IF,max 110 A (10 µs); VF 1.5/1.7 V at 2 A. Per diode at 540 W (L 200 µH): average 0.71 A, rms 1.52 A over the full line cycle (2.15 A rms within its own half-cycle), peak 4.6 A. With the plate at +30 K (p 34; TC ≈ 100–110 °C in a 70 °C rack) this is inside the ratings. Inrush (relay open): DB1 (2 diodes, ≈ 0.95 V each) carries most of it. The L2 / SICD1 → DC+ path is in parallel on the upper side (τ = L/R ≈ 64 µs at 3 mH, negligible against 10 ms), so the SiC diodes can share part of the 6.9 A peak; 6.9 A < IFSM 15 A either way. The return is through the DB1 low diode, because the SiC body diode needs ≈ 3 V. Same part as 5.1. |
| A9 | CANNOT VERIFY | The MCC datasheet could not be fetched (mccsemi.com URL empty). jlcpcb.com/partdetail/…/C17401133 (TBS22K-TP): 2.2 A average rectified current, 800 V, VF 950 mV at 2 A, IFSM 90 A, TJ ≤ 150 °C. Inrush 6.9 A ≪ 90 A. Return current at 540 W: each low-side diode carries the input current of its half-cycle, 1.11 A average, which equals a bridge loaded with 2.22 A, **at the 2.2 A rating**. Loss ≈ 2 × 1.11 × 0.95 ≈ 2.1 W in the SMD package under the heatsink line; ≈ 0.8 W at the realistic 130–200 W continuous load (p 33). I could not read the derating curve. Cooling copper: AC1 pour 218 mm², AC2 170 mm² (F.Cu), the DC+ island, and pad 4 in the C73/R93 GND via field to In1/In4. Same part and place as 5.1. Note F9. |
| A10 | PASS | Man Yue ERT826M2WI45RRS0F-R (LCSC C51890374 product page; spec "RT series" v01 2023-06-14, §4.16): 82 µF 450 V, **1.574 A at 100 kHz**, 105 °C, 5000 h. Frequency factor 0.40 at 120 Hz (6.8–180 µF) gives 0.63 A at 100–120 Hz; ambient factor 1.73 at 85 °C. 100 Hz ripple: ΔVpp = 540 / (2π·100·328 µ·400) = 6.6 V. 100 Hz current = 1.35 A/√2 = 0.95 A total, 0.24 A per capacitor. HF: the PFC diode current, minus its DC and 100 Hz parts, gives ≈ 1.4 A; adding the DAB and LLC gives ≈ 1.8 A, or ≈ 0.45 A per capacitor. Normalised per capacitor: √((0.24/0.40)² + 0.45²) = 0.75 A against 1.574 A at 105 °C (48 %). Bus in normal operation ≤ 400 + 3.3 V plus the PFC overshoot set by firmware. Surge voltage 500 V. Nothing on the board limits DC+ above 450 V except the PFC firmware OVP; the flyback line-OVP (483 V, checklist 01) sits above the capacitor rating. |
| A11 | PASS (as 5.1) | LCSC C445674 product page: "2.2uF ±10% 450V X6S 2220", TDK C5750X6S2W225KT000N, so it is the 450 V type. Voltage stress 400/450 = 89 %. **I could not get the effective capacitance at 400 V**: product.tdk.com returned 403, and the TDK catalogue on LCSC has no DC-bias curve. |
| A12 | PASS | TI UCC27511A SLUSD95A (rev. Jan 2024, ti.com/lit/ds/symlink/ucc27511a.pdf), Fig. 4-1 / Table 4-1: 1 VDD, 2 OUTH, 3 OUTL, 4 GND, 5 IN−, 6 IN+. `rv sch ref DRV1,DRV2`: VDD = 15V, OUTH → R14 / R20 5 Ω, OUTL → R1 / R19 5 Ω → GATE1/2, GND, IN− = GND, IN+ = PFC_PWM1/2 with R71 / R69 10k to GND, R43 / R7 10k gate pull-down. VDD abs max 20 V, recommended 4.5–18 V (15 V rail OK, provided the 15V rail stays below 18 V – checklist 01). VIH max 2.4 V, VIL min 1.0 V, so 3.3 V logic is compatible. Peak current ≈ 15 V/(5 + 6.5 Ω RG,int) ≈ 1.3 A, well under the 4 A / 8 A. 5.1 IXDD609 had IN = PWM, EN = 15 V, so it was non-inverting, the same as now (`rv sch cmp51 9`). |
| A13 | CANNOT VERIFY | Gate power ≤ Qg·V·f = 40 nC·15 V·133 kHz = 80 mW in total. R14 gets ≈ 5/(5 + 6.5 + 1.5) × 40 mW ≈ 15 mW and R1 ≈ 17 mW, against a 1206 at 0.25 W (< 10 %): PASS. The bypass needs 20·Qg/ΔV = 1.6 µF. C79 / C80 = C6119856 "4.7uF ±10% 25V X5R 0603" (LCSC page; HRE spec CGA0603X5R475K250JT has **no DC-bias curve**), so I cannot show the effective capacitance at 15 V. A 0603 25 V X5R typically keeps 25–35 %, about 1.2–1.6 µF, which would be marginal. |
| A14 | PASS | Gate current ≈ 1.3 A × 4 mΩ = 5 mV (≤ 12 mV even at 3 A), negligible for the gate. The sampling-after-edge scheme of p 13 is unchanged. |
| B1 | CANNOT VERIFY (pads PASS) | `rv bq fp L1,L2`: L2 1 = AC1 (−6.028, −31.801), 2 = PFC_DRAIN_1 (−0.075, −37.755); L1 1 = PFC_DRAIN_2 (−0.102, 3.342), 2 = AC2 (−6.056, −2.611); pad pitch 8.42 mm diagonal; 2.6 / 1.3 mm pads for 0.8 mm wire. Body position "±3 mm, confirm on the built board" (README L2151, open input L122): no measurement is recorded. Courtyards within 3 mm (`rv bq area … --touch`): L2: Q5 (overlaps by 1 mm at x 0.76–1.74), C117, CM4, C38, C81, C82, H4, R14/R1, DRV5 (B.Cu). L1: C117 (overlap 0.5 mm), CM4, C38, C66, SICD2 (DRC overlap), H7, R47/R48/R50/R51 (B.Cu). The toroid end next to Q5 / SICD2 (heatsink) is where a 3 mm error matters. |
| B2 | CANNOT VERIFY | `grep -rn "sendust\|L at 0 A\|measured L"`: only NEXT_REVISION.md:192/205, fab/NOT_ASSEMBLED.md:16–17 ("listing 3 mH at 0 A – measure"). There is no measured value, the value field is "TBD (measured)", and the A7/A8 calculation therefore uses the 5.1 schematic's 200 µH. See F6. |
| B3 | PASS | SICD1.A is in the PFC_DRAIN_1 F.Cu pour (4.4 mm of the pad outline touches copper; `conn.py`). Neck Q5.2 → SICD1.A: `rv bq neck PFC_DRAIN_1 F.Cu 11.8 -21.4 3.752 -24.1` = **1.37 mm** (5.1 `Net-(L2-2)` 4.55 mm). Q5.2 → L2.2 2.59 mm. SICD2.A: F.Cu pour + B.Cu 2.0 mm to L1.1 and 2.4 mm to Q6.2. SICD1.K is solid in the DC+ pour; SICD2.K is on the DC+ island (≈ 1.9–2.9 mm of its outline, channel 1.60 mm to DB1.2; 5.1 2.97 mm). All are ≥ 1.0 mm. The 1.37 mm drain neck carries ≈ 1.5 A rms / 4.6 A pk: rule 3.25·1.37^0.725 = 4.0 A, more than 2 × 1.52 A. It is narrower than 5.1 (see F2). |
| B4 | **FAIL** | Island C73.1 / DB1.2 / SICD2.K → DC+ trunk: `rv bq neck DC+ F.Cu 9.863 -14.0 20.2 -17.2` = **1.34 mm**; `xsec DC+ F.Cu x 13.2 -24 -17` = 1.441 mm (x 13.0: 1.484, x 13.5: 1.531); the south side `xsec x 14.5 -12 -9` = 0. In parallel: B.Cu DC+ 1.0 mm track (10.2, −18.65) → (13.6, −18.65) → (14.7, −19.75) → (14.7, −22.1), 2 vias 0.8/0.4 on the island side ((10.2 / 11.3, −18.55)) and 3 vias at x 14.7. Total ≈ 2.4 mm. 5.1: `rv bq51 xsec DC+ F.Cu x 13.2 -24 -17` = **5.451 mm** + 0.643 mm at x 14.5 (`rv bq51 neck … 11.5 -21.65 9.863 -14.0` 3.14 mm). Current: SICD2 avg 0.71 A + 100 Hz, rms ≤ 1.5–2.2 A. Part of SICD1's HF current also crosses it, because C73 is on the island and SICD1.K is on the trunk side. DB1's whole charging current crosses it with the PFC off. Capacity: 3.25·1.34^0.725 + 3.25·1.0^0.725 ≈ 7.2 A, which is ≥ 2 × 2.2 A, so the current test passes. It **fails "not narrower than 5.1"** (2.4 vs 5.45 + 0.64 mm). The DAB / LLC load current does not use the neck: SICD1.K → C56 is 7.99 mm, and the loads are north. See F2. |
| B5 | PASS | `rv bq net DC+`: tracks and zones on F.Cu / B.Cu only (zone fill only F.Cu; inner layers have just the pad rings). Power GND, outer layers: C73.2 / DB1.4 / R93.2 are on one B.Cu GND pour with ≈ 15 vias in C73.2 / the R93 field to In1/In4. B.Cu channel to C28.2 is 1.57 mm (5.1 2.72 mm). R21.2 → C73.2 is 1.55 mm (5.1 1.55 mm). **C56.2 and C37.2 have no outer-layer GND copper.** The F.Cu outline is free, B.Cu has 0.15 mm only, and they connect solidly to In1.GND / In4.GND (full ring, `ring.py`). That is the same as 5.1, where they connected only on In1.Cu. 5.2 has two GND planes where 5.1 had one, so the total return is not worse. Documented reason: README Stage 9 keeps the In1 / In4 GND planes. The wording "DC+ and its GND return are kept on F.Cu / B.Cu" is not literally true for C56 / C37 (note F11). |
| B6 | PASS | `rv bq fp C28,C29,C37,C56` vs `rv bq51 fp …`: same positions, rot 0, pad 1 = DC+, pad 2 = GND on all four. Footprints `CP_Radial_D12.5mm_P5.00mm…H45mm`, pitch 5.0. ERT is 12.5 × 45 mm (LCSC page "D12.5xL45mm"). Height against the enclosure belongs to checklist 12. |
| B7 | PASS | `rv sch bom 5`, `rv sch bom 11`: C64 / C66 on AC1 / AC2 are TDK B32921 X2 305 VAC film; on DC+ the only MLCC here is C73 (450 V 2220, as designed). No 1206 500 V part is left on AC1 / AC2 / DC+ in these sheets (C14 4.7 µF is on 15V). |
| C1 | PASS | `rv bq loop`. Loop 1, 5.2: Q5.2 SICD1.A SICD1.K (13.3, −18.6 neck) C73.1 C73.2 R93.2 R93.1 Q5.3: 52.6 mm / 66 mm²; 5.1 (Q5.2 … SICD1.K C73.1 …): 46.3 mm / 73 mm², ratio 1.14. Loop 2: 5.2 50.5 mm / 60.7 mm², 5.1 44.3 mm / 92.2 mm², ratio 1.14. C73 is in both loops. Loop 1 now passes through the 1.34 mm + 1.0 mm DC+ neck and the 1.37 mm drain neck, so its inductance is higher than the plan-view numbers suggest (F2). |
| C2 | PASS (with pad-pad exceptions) | `rv bq near PFC_DRAIN_1 --within 1.3`: DC+ F.Cu 1.200, GATE1 1.200, AC1 1.202, DC+ B.Cu 1.250 (the inner 0.5 mm values are to GND plane barrels). `near PFC_DRAIN_2`: DC+ **1.052 mm on every layer** (L1.1 pad corner (1.198, 2.042) ↔ SICD2.K pad (2.170, 1.639): pad to pad, which the `.kicad_dru` "HV functional, outer layers" rule exempts); GND B.Cu 1.065, AC2 B.Cu 1.158, Net-(R50-Pad2) 1.185 (pads). 5.1: L1-1 ↔ DC+ F.Cu 0.726 mm, L2-2 ↔ DC+ 0.930 mm (`rv bq51 dist`), so this is better than 5.1. Pour areas: PFC_DRAIN_1 119.7 mm² F.Cu (5.1 160 F.Cu + 160 In1); PFC_DRAIN_2 35.5 mm² + 18 mm of 2.0 / 2.4 mm B.Cu (5.1 111 + 111 mm²), so the switch nodes are smaller than 5.1. GND planes In1 / In4 sit between the pours and In2 / In3. |
| C3 | PASS | Copper along each pad outline (+0.1 mm), from my own shapely script on the stored fill. L2.2 8.5/8.8 mm, L1.1 6.2 F + 2.0 B, Q5.2 12.5/12.5, Q6.2 3.0 (B.Cu 2.4 mm track), SICD1.A 4.4, SICD1.K 6.9/6.9, SICD2.A 4.1 F + 6.6 B, SICD2.K 2.95, C28.1 / C37.1 / C56.1 6.45/6.45, C29.1 9.8/9.8, Q5.3 11.0 B, Q6.3 9.9 B. All pads touch the pour directly. The 0.1524 mm "spoke" tracks in `rv bq net` are leftovers inside solid pours, so they do not limit anything. Every pad is ≥ 0.6 mm and equal to or better than 5.1 (where the 5.1 pads were also solid). |
| C4 | **FAIL** | Gate loops: DRV1 → Q5 gate 8.8 mm, DRV2 → Q6 gate 7.1 mm (≤ 15 mm). `rv bq loop` DRV1.2 R14 Q5.1 Q5.3 R93.2 DRV1.4: 47.8 mm / 95 mm² vs 5.1 49.1 mm / 104 mm²; DRV2: 47.8 mm vs 50.5 mm, so equal to or better than 5.1. VDD bypass: `rv bq padgap DRV1.1 C79.1` = **2.54 mm**, DRV1.4–C79.2 **3.54 mm**, DRV2.1–C80.1 **4.24 mm**, DRV2.4–C80.2 2.34 mm. DRV2's VDD runs pin 1 → via (13.2, 8.75) → 0.4 mm F.Cu ≈ 5 mm → via (12.96, 13.14) → C80.1, and DRV1's goes through vias (10.715, −34.75) / (13.67, −36.28). 5.1 (`rv bq51 padgap`): DRV1.1–C79.1 0.54 mm, DRV2.1–C80.1 0.74 mm. This fails "≤ 3 mm" and is worse than 5.1. TI SLUSD95A §9 asks for 0.1 µF "as close as possible" plus a bulk capacitor. See F4. |
| C5 | **FAIL** | `rv bq dist RES_IN IN2`: **F.Cu 1.814 mm** at RES_IN pour corner (−61.41, −11.46) ↔ IN2 pour (−59.98, −10.34); inner layers ≥ 8.6 mm. 5.1: F.Cu 8.61 mm. The IN2 pour got a new arm at x ≈ −60.3 … −56.5 up to y −10.4 (towards CM1.3), because PE moved to (−46.6, 0.5). Other pole pairs: RL1-COM–IN2 6.78, L1_PRI2–L2_PRI2 6.46, AC1–AC2 F.Cu **2.000** (= 5.1 2.000) and B.Cu **0.700** (R47 / R50 0805 pads of the VAC divider, = 5.1 0.700, checklist 09), all cross pairs ≥ 10 mm. RES_IN is the smallest, below 2.5 mm, and worse than 5.1. See F1. |
| C6 | PASS | `rv bq net PE`: B.Cu tracks 1.0 mm (45.7 mm) and 2.03 mm (11.1 mm); pads C65.2, C81.2, C82.2, C84.2, C85.2 and PE.1 ×2, so all five Y capacitors are connected (DRC unconnected 0). `rv bq dist fp:PE @PRI` ≥ 3.234 mm on every layer. `rv bq near PE --within 3.3 --other-domain`: smallest 3.230 mm (In2 GND), F.Cu IN2 3.234, RL1-COM 3.234, L2_PRI2 3.243, L1_PRI2 3.270, B.Cu GND 3.239. This meets ≥ 3.2 mm creepage / 2.0 mm clearance. |
| C7 | PASS (facts for checklist 12) | Body x-ranges (`rv bq fp`): Q5 0.76–6.38 (rot −90), SICD2 1.55–6.54 (rot −90), DB1 −1.35–8.40 (SMD F.Cu), C73 8.58–16.43 (SMD F.Cu), SICD1 8.36–13.35 (rot 90), Q6 8.76–14.38 (rot 90). The two vertical rows face each other across x ≈ 6.4–8.4, and DB1 / C73 lie in and beside that gap, so where a straight heatsink can stand depends on the tab side (checklist 12). The SICDs are flipped against 5.1 (5.1 SICD1 rot −90 at x 9.96–14.95, SICD2 rot 90 at 0.36–5.35), so their tabs now face the same way as Q5 / Q6. DB1 cooling copper: AC1 / AC2 pours 218 / 170 mm², the DC+ island, and pad 4 in the GND via field. |
| C8 | PASS | `rv bq xsec GND In1.GND y -20 -72 0` = 0, In4 = 0, y 0 / 5 / 10 / −10 / −25 / −30 / −32 = 0. In1 GND reaches x −40 only at y −46 … −34 (under L2 and C82; C82 is the GND–PE capacitor itself). `rv bq dist L1_PRI2 GND`: In1 1.95 mm to the plane edge at C81.1, which does not overlap. No plane lies under IN1 / IN2 / RL1 / CM1 / CM4 / C86 / C38 / C117 / C84 / C85 / C65. Small In1 GND pieces next to the Q9 / RL1 driver (RES_IN to In1 GND 1.31 mm at (−62.7, −33.1)) are signal ground, not a plane. |
| C9 | CANNOT VERIFY | `drc_summary.py pth_inside_courtyard`: IN1 pad 1 and CM1 pad 3 inside the C86 courtyard ("as in 5.1"). `courtyards_overlap -72 -48 22 14`: C86–IN1, C86–R6, C81–C82, C81–C38, Q5–DB1, SICD2–L1, C56–C73, R47–R48, R50–R51 and others. The C86 / C117 part C2888216 (Dongtong MKP62-275V684KP22.5): jlcpcb.com gives no body size, so I cannot say whether the 26.5 × 11.5 mm outline is real. |
| D1 | PASS | `rv sch net`: Q5.3 "PFC CURRENT 2+" → R33 → U4A → R96 → PFC_I1_MEAS J2-42 (5.1 J2-43); Q6.3 "PFC CURRENT 3+" → R62 → U4B → R61 → PFC_I2_MEAS J2-44 (= 5.1). PFC_PWM1 J2-19 → DRV1 → Q5, PFC_PWM2 J2-33 → DRV2 → Q6 (= 5.1; `rv sch cmp51 10`: only U4 value). Pairing is unchanged: PWM1 ↔ I1, PWM2 ↔ I2. J2_PINOUT.md rows 17 / 19 / 33 / 42 / 44 agree. |
| D2 | PASS | J2-17 → R44 → Q9 gate; R32 2.2k to GND at the J2 pin. With the FPGA unconfigured, the gate is held low and the relay stays open, so the board runs through R27. Firmware: keep the PFC, DAB and heater loads off until the relay has closed (R27 at full load = 305 W, A2). R32 loads the FPGA pin with 1.5 mA at 3.3 V. |
| E1 | PASS (notes) | First power-up through an isolation transformer / variac with the PFC off: DC+ ≈ 325 V via DB1 + R27; the flyback starts ≈ 60 V. Before closing the relay, check that DC+ settles at √2·Vin, that R27 cools between tries (17 J per charge), and that DB1 / SICD stay cool. Close RL1 only after DC+ ≥ 90 % of peak, then enable the PFC with a soft-start and an OVP < 440 V in firmware (A10). |
| E2 | CANNOT VERIFY | Open measurements: L1 / L2 L(0 A) and L(4–5 A); toroid body position; heatsink fit over DB1 / C73; DB1 and R27 temperatures; C73 effective capacitance; relay pick-up at 3.0 V gate. |

## Findings (ranked, most severe first)

### F1 Mains RES_IN to IN2 only 1.81 mm on F.Cu (5.1: 8.61 mm)
- Severity: **should fix**
- What is wrong: The IN2 F.Cu pour was given a new arm (x ≈ −60.3 … −56.5, up to y −10.4) when PE moved to (−46.6, 0.5). Its top-left corner (−59.98, −10.34) comes within 1.81 mm of the RES_IN pour corner (−61.41, −11.46). This is line-to-neutral before any fuse or filter, with no MOV, so the gap sees mains transients. It is below the 2.5 mm functional creepage the checklist uses and far below 5.1.
- Evidence: `kicad_next/review/tools/rv bq dist RES_IN IN2` → F.Cu 1.814 mm; `rv bq51 dist "/05 PFC/RES_IN" "/05 PFC/IN2"` → 8.610 mm.
- Smallest fix: chamfer or pull back the IN2 pour corner at (−60, −10.3), or the RES_IN pour corner at (−61.4, −11.5), to ≥ 2.5 mm (better ≥ 3 mm). The arm only has to reach CM1.3 at (−51.2, −9.2).
- Confidence: high (geometry). The required value depends on how the owner classifies L–N functional insulation (IEC 62368-1 allows a fault test instead), but the regression against 5.1 is certain.

### F2 SICD1 area: DC+ neck 1.34 mm F.Cu + 1.0 mm B.Cu (5.1: 5.45 + 0.64 mm); drain neck Q5 → SICD1.A 1.37 mm (5.1: 4.55 mm)
- Severity: **should fix**
- What is wrong: The PFC_DRAIN_1 pour, which now reaches south to SICD1.A after SICD1 was turned 180° (Stage 4a), cuts the DC+ copper between the island (C73.1, DB1.2, SICD2.K) and the trunk down to one F.Cu channel and the 1.0 mm B.Cu track with 2 / 3 vias (Stage 9 removed In3). This link carries all of SICD2's output, DB1's charging current, and C73's share of SICD1's HF current. The same cut squeezes the Q5 → SICD1.A drain copper to 1.37 mm. Both numbers pass the README current rule with factor 2 (≈ 7.2 A and 4.0 A capacity against ≈ 2.2 A and 1.5 A rms). They are 2.4× and 3.3× narrower than 5.1, and they sit inside commutation loop 1, so they add inductance between SICD1 and C73.
- Evidence: `rv bq neck DC+ F.Cu 9.863 -14.0 20.2 -17.2` = 1.34; `rv bq xsec DC+ F.Cu x 13.2 -24 -17` = 1.441 vs `rv bq51 …` = 5.451; `rv bq neck PFC_DRAIN_1 F.Cu 11.8 -21.4 3.752 -24.1` = 1.37 vs `rv bq51 neck "Net-(L2-2)" F.Cu 11.503 -26.727 3.752 -24.1` = 4.55; B.Cu tracks (10.2, −18.65)–(14.7, −22.1) 1.0 mm.
- Smallest fix: widen the B.Cu DC+ link. Trim the B.Cu GND pour edge at y ≈ −17 between x 9 and 14 so the track can grow to ≈ 2 mm, and add 2–3 vias at each end. Optionally add a second DC+ link at the south side of the island towards the trunk near (14.5, −10.5), where 5.1 had 0.64 mm. If the owner accepts the current-rule margin as sufficient, record the decision in the README instead.
- Confidence: high for the geometry, medium for the electrical impact (no loop-inductance measurement).

### F3 L–N spacing also at AC1 / AC2 (2.0 mm F.Cu, 0.70 mm B.Cu at R47 / R50) – equal to 5.1
- Severity: **note**
- What is wrong: These are below 2.5 mm but identical to 5.1, so they do not fail the acceptance bar. The 0.70 mm is between two 1 MΩ 0805 divider pads of opposite poles (checklist 09).
- Evidence: `rv bq dist AC1 AC2` → F.Cu 2.000 (−7.456, −13 / −11), B.Cu 0.700 (0.15, 7.9 / 7.2); 5.1 identical.
- Smallest fix: none required. If F1 is fixed, consider moving R47 / R50 apart at the same time.
- Confidence: high.

### F4 DRV1 / DRV2 VDD capacitors 2.5–4.2 mm from the driver pins (5.1: 0.5–0.7 mm)
- Severity: **should fix**
- What is wrong: The new SOT-23-6 drivers were placed on the old IXDD609 origins, but C79 / C80 stayed where they were. VDD now reaches the capacitor through vias and up to ≈ 5 mm of 0.4 mm track (DRV2). The 1.3 A gate-current edges then flow through ≈ 8–10 nH, against TI's 0.1 µF "as close as possible".
- Evidence: `rv bq padgap DRV1.1 C79.1` 2.536 mm, `DRV2.1 C80.1` 4.240 mm, `DRV1.4 C79.2` 3.536 mm; 5.1: 0.541 / 0.740 mm. TI SLUSD95A §9 (power supply recommendations).
- Smallest fix: move C79 / C80 next to pins 1 / 4 on B.Cu (≤ 1 mm), or add a 100 nF 0603 directly across pins 1–4 of each driver.
- Confidence: medium. The driver will very probably work (UVLO 3.45–4.35 V is far below 15 V), but this is a measurable step back from 5.1.

### F5 X-capacitor discharge 3.5–4.4 s (> 2 s, IEC 62368-1) – as 5.1
- Severity: **should fix** (a rating exceeded on paper; unchanged from 5.1)
- What is wrong: 1.83 µF of X capacitance discharges through R4–R6 = 1.41 MΩ (plus 6 MΩ of the VAC divider), so τ = 2.1–2.6 s and the time to 60 V is 3.5–4.4 s.
- Evidence: values from `rv sch sheet 5` and sheet 9; 1.69 τ calculation in A4.
- Smallest fix: R4–R6 470k → 200k (same 1206 part family; 77 Vrms each, 29 mW each). Then R = 600 kΩ (546 kΩ with the divider), τ = 1.0 s, 1.7 s to 60 V.
- Confidence: high for the arithmetic. Whether the 2 s rule applies depends on how the amplifier is plugged in (owner decision).

### F6 L1 / L2 inductance not recorded
- Severity: **should fix** (document) – not a blocker: consigned parts, same as the working 5.1
- What is wrong: The value is "TBD (measured)". The listing says 3 mH at 0 A, while the design document and 5.1 schematic say 200 µH. DCM vs CCM, the peak current (A7: 4.6 A at 200 µH) and the FPGA timing all depend on it.
- Evidence: `rv sch sheet 5` L1 / L2 value; `grep -rn "sendust\|L at 0 A"` finds no measurement.
- Smallest fix: measure L(0 A) and L(≈ 5 A DC bias) on the fitted toroids and put the value into `lib/part_map_next.csv`, NEXT_REVISION 5.2 and the fab NOT_ASSEMBLED row.
- Confidence: high.

### F7 Q9 schematic value still `2n7000` (BOM orders BSS138LT1G)
- Severity: **should fix** (misleading document)
- What is wrong: The schematic and the fab BOM comment say 2n7000 while the LCSC number is the logic-level BSS138. A 2N700x has a threshold up to 2.5–3 V and is not fully on at a 3.0 V gate.
- Evidence: `rv sch part Q9` (value 2n7000, mpn BSS138LT1G, review "value 2n7000 -> BSS138"). BSS138LT1/D Rev. 15: VGS(th) ≤ 1.5 V, rDS(on) ≤ 10 Ω at 2.75 V.
- Smallest fix: value `BSS138` in `lib/part_map_next.csv` (refdes Q9).
- Confidence: high.

### F8 Gate resistance doubled against 5.1 (5 Ω on / 5 Ω off; 5.1 2.5 Ω both ways)
- Severity: **note**
- What is wrong: On 5.1, R14 and R1 (5 Ω each) were both fed from IXDD609 OUTA, so the gate saw 2.5 Ω. Now each switching direction has 5 Ω. Turn-off becomes about 25 % slower (≈ 0.58 A against 0.75 A of plateau current with RG,int 6.5 Ω), adding ≈ 0.5–0.7 W of turn-off loss per active switch at 540 W. Turn-on is mostly at zero current in DCM. EMI is slightly better. CHANGES 3a does not mention this.
- Evidence: `rv sch cmp51 9` (R1 / R14 pin 1 both Net-(DRV1-OUTA) on 5.1, values unchanged at 5R); C2M0160120D Rev. 07 RG(int) 6.5 Ω, Qgd 17 nC.
- Smallest fix: none needed. If 5.1 behaviour is wanted, R1 / R19 (turn-off) could be 2.2–2.7 Ω.
- Confidence: medium (estimate, no switching measurement).

### F9 DB1 runs at its 2.2 A average rating at the 540 W design load
- Severity: **note** (as 5.1)
- What is wrong: The bridge's low-side diodes carry the whole line-frequency return current (1.11 A average each, which equals a 2.22 A bridge load), about 2 W in an SMD body under the heatsink line. The realistic continuous load (130–200 W, p 33) puts it at ≈ 40 %.
- Evidence: A9 calculation; TBS22K-TP JLC page (2.2 A, 0.95 V at 2 A, 90 A IFSM).
- Smallest fix: none for 5.2. Measure the DB1 temperature at bring-up (E2).
- Confidence: medium (no derating curve).

### F10 R27 has no protection if the relay does not close
- Severity: **note** (as 5.1)
- What is wrong: R27 would dissipate ≈ 300 W at full load and ≈ 47 W at 1 A; the board has no fuse or thermal fuse.
- Evidence: A2.
- Smallest fix: firmware interlock (no load before RL1 closes; trip if DC+ sags), as on 5.1.
- Confidence: high.

### F11 Stage 9 wording vs the bulk-capacitor GND return
- Severity: **note** (document)
- What is wrong: README Stage 9 says "DC+ and its GND return are kept on F.Cu / B.Cu". C56.2 / C37.2 have no outer GND copper and return only through In1 / In4, as C56 / C37 did on 5.1 through In1. The B.Cu return C73 / R93 / DB1 → C28.2 is 1.57 mm (5.1 2.72 mm).
- Evidence: `ring.py` (In1 / In4 full ring, B.Cu 0.15 mm at C56.2 / C37.2); `rv bq neck GND B.Cu 15.137 -14.0 24.9 -30.2` 1.57 vs `bq51` 2.72.
- Smallest fix: one sentence in the README Stage 9 ("bulk-capacitor GND pins return through the In1 / In4 planes as on 5.1").
- Confidence: high.

### F12 DC+ trunk between the north and south bulk capacitors narrowed to 2.66 mm (5.1 ≈ 6.9–7.6 mm)
- Severity: **note**
- What is wrong: At y −14.5 the F.Cu DC+ pour between C56 and C37 / C29 is 2.66 mm in two channels. The HV 1.2 mm clearance round the U4 / C106 vias (21.0, −13.8), (21.4, −12.3) and (24.9, −15.4) narrows it, and it has no B.Cu copper. It carries the south capacitors' ripple share (≤ ≈ 1.5 A rms), against a rule capacity of 6.6 A.
- Evidence: `rv bq xsec DC+ F.Cu y -14.5 16.5 27` 2.655 mm vs `rv bq51 …` 7.617 mm; `rv bq xsec DC+ B.Cu y -14 0 30` = 0.
- Smallest fix: none required. If F2 is reworked, consider a B.Cu DC+ strip from C56.1 to C37.1.
- Confidence: high (geometry).

## Compared with 5.1
- **Equal**: schematic connectivity and all values of sheets 5 / 11 (`rv sch cmp51 5`), bulk-capacitor positions and polarity, Q5 / Q6 / DB1 / C73 / shunt positions, the inrush / relay circuit, the Y-capacitor scheme, PWM ↔ current-channel pairing, AC1–AC2 spacing (2.0 / 0.7 mm), commutation-loop geometry (path ×1.14, area equal or smaller), gate-loop geometry, X-discharge time.
- **Better**: switch-node pours are smaller (PFC_DRAIN_1 120 mm² against 2 × 160 mm²; PFC_DRAIN_2 35 mm² + track against 2 × 111 mm²); drain-to-DC+ spacing is 1.05 / 1.2 mm (5.1 0.73 / 0.93 mm); PE ≥ 3.23 mm from all primary copper; two inner GND planes; the driver VDD has a 2 V margin to its abs max (UCC27511A 20 V).
- **Worse**: RES_IN–IN2 1.81 mm (8.61 mm), F1. DC+ link at SICD1 ≈ 2.4 mm (≈ 6.1 mm) and drain neck 1.37 mm (4.55 mm), F2. VDD capacitor distance 2.5–4.2 mm (0.5–0.7 mm), F4. Gate resistance 5 Ω (2.5 Ω), F8. DC+ trunk 2.66 mm (7.6 mm), F12. Outer GND return to C28 1.57 mm (2.72 mm), F11.

## Could not verify
- TBS22K datasheet (MCC URL returned nothing): pinout drawing, derating / thermal curve. I used the JLC part page only.
- TDK C5750X6S2W225K DC-bias curve: effective capacitance of C73 at 400 V (product.tdk.com 403).
- C6119856 (C79 / C80) DC-bias curve: the HRE spec has none.
- C2888216 (C86 / C117) body dimensions, needed for C9.
- RDS(on) of C2M0160120D at VGS 15 V (curves only in the datasheet, not read off).
- Measured inductance of L1 / L2 and the real toroid body positions (no data in the repository).
- The Songle SRD contact rating per ordering code (the datasheet lists 7 / 10 / 15 A variants; UL table 10 A 250 VAC NO used).
- ZLLS400TA ratings for D9 / D28: not fetched by me; the 71 mA flyback current is trivially small.

## Outside scope
- Checklist 12: L1 / L2 courtyard overlaps Q5 (1 mm) and SICD2 / C117; toroid ±3 mm body position next to the heatsink line. The facing tab rows at x 6.4–8.4 with DB1 / C73 beneath them (C7 facts). C56–C73 courtyard overlap.
- Checklist 09: R47 / R50 (AC1 / AC2 1 MΩ 0805) pads 0.70 mm apart.
- Checklist 01: the 15V rail must stay below 18 V (UCC27511A recommended max) at light load; the flyback line-OVP 483 V is above the 450 V bulk-capacitor rating.
- Checklist 13: R93 / R21 4 mΩ not at JLC (5 mΩ option changes the current gain +25 %); CM1 / CM4 stock 20.
