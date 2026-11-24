# Findings: 09 voltage measurement  (reviewer: Claude Opus 5.5, 2026-11-24, commit 3e1e31e)

## Summary
The four primary-side voltage chains (VAC / U8, DC_LINK / U6, AUX / U10A, 5V_MEAS / U10B) are correct in the netlist
and on the board. Gains, filters, output resistors, the J2 pins and the pinouts all match CHANGES 4.2–4.5 / 4b and
the TI datasheets. The layout equals 5.1 or is better (the HV intermediate nodes went from 0.16 mm / 0.42 mm to
≥ 0.5 mm from 15V / DC+). **Nothing here blocks ordering.** One documentation item should be fixed before
bring-up: the VAC scale changed from 0.005 to 0.004 V/V, and no firmware row in CHANGES / NEXT_REVISION says so. The
remaining findings are notes: cross-leg pad gaps of 0.7 mm in the VAC chain (the same as 5.1), the DC-link 0805s
at their 150 V rating at 450 V (the same as 5.1), two wrong lines in NEXT_REVISION.md, and the checklist's input
common-mode figure. The board has changed since the checklist was written (stages 13a–13d), but none of those
changes touches these parts. Every coordinate in the checklist for this area matches the board as it is now.

## Checklist results
| Item | Verdict | Evidence |
|---|---|---|
| A1 | PASS | `rv sch ref U8,R47,…`: AC1 → R47 → R48 → R79 → U8 pin 4 (−IN, `Net-(U8--)`); AC2 → R50 → R51 → R52 → U8 pin 3 (+IN, `Net-(U8-+)`); R80 12k + C126 1n from `+1V65_BIAS` to + input; R49 12k ‖ C127 1n from output (`Net-(C127-Pad1)`, pin 1) to − input; R65 100R → VAC_MEAS. V+ = (AC2·12k + Vb·3M)/3.012M, Vout = V+(1 + 12k/3M) − AC1·12k/3M = **Vb + 0.004·(V_AC2 − V_AC1)** (exact for matched legs). Sign: **Vout > Vb when AC2 > AC1**, the same as FINDINGS.md 10 ("1.65 V + 0.005·(V(AC2) − V(AC1))", 5.1). `rv sch cmp51 9`: only R49 / R80 15k→12k, C126 / C127 new, and the output net renamed `Net-(R49-Pad1)` → `Net-(C127-Pad1)`. Simulation: 0.0040072 (FINDINGS 11.1; +0.18 % from the 22 Ω bias source, 11.3) |
| A2 | PASS | Output: 253 Vrms → 358 V pk → ±1.43 V; 264 Vrms → 373 V pk → ±1.49 V around Vb 1.642 V (FINDINGS 11.2) → 0.15…3.13 V. TLV316 (TI SBOS752A, Sep 2016, §7.7 p 8, https://www.ti.com/lit/ds/symlink/tlv316.pdf): swing 35 mV from the rails at RL = 10 kΩ. The load is R49 12k ‖ (R65 + mux, high Z at DC) ≈ 12 kΩ → the usable range is 0.035…3.265 V, so no clipping at 264 Vrms (simulated clip at 400 V pk / 283 Vrms, FINDINGS 11.2). **Input common mode (correction to the checklist):** in the bridgeless PFC each line swings between ≈ −1 V and +V_pk against GND, so V+ = Vb + (AC2 − Vb)·12k/3.012M runs from 1.64 V to **3.12 V** at 373 V pk (not "1.64 V ± 1.4 mV"). That is inside VCM = (V−) − 0.2 … (V+) + 0.2 V (§7.7), but it crosses the RRIO input transition (CMRR 90 dB below (V+) − 1.4 V, 75 dB over the full range): ≤ 1.5 V × 10^(−75/20) ≈ 0.27 mV ≈ 1.3 LSB ≈ 67 mV of line, negligible. Surge: 2.5 kV / 3 MΩ = 0.83 mA into the input clamps, well inside the 10 mA abs-max (§7.1 p 6, note 2) |
| A3 | PASS | C127 across R49, C126 across R80 (netlist above): 1/(2π·12 k·1 nF) = 13.26 kHz on both legs; simulated 13.3 kHz (FINDINGS 11.1). Parts: C126 / C127 = C106246 CC0603JRNPO9BN102, 1 nF ±5 % NP0 50 V (LCSC page https://www.lcsc.com/product-detail/C106246.html); R49 / R80 C22790 1 %. Phase lag at 50 Hz: atan(50/13.26 k) = 0.22° (12 µs). No capacitor on the output node before R65 (`Net-(C127-Pad1)` pads: R65.2, C127.1, U8.1, R49.1 only) |
| A4 | PASS | R47 … R52 = C17514 Uniroyal 0805W8F1004T5E (`rv sch part R47`). Uniroyal thick-film data sheet V.3 (12 Feb 2019), §7 Ratings p 4/9 (https://datasheet.lcsc.com/datasheet/pdf/0a975aaa49b7c97f38a963127be4a823.pdf?productCode=C17514): 0805 max working voltage 150 V, max overload 300 V, dielectric withstanding 500 V. Each leg sees 0…373 V pk (half-wave against GND, see A2) → ≤ 124 V pk per resistor, ≈ 62 Vrms → inside 150 V. Surge: 2.5 kV / 3 ≈ 830 V per resistor if a 2.5 kV differential surge reached AC1/AC2. That is above the 300 V overload rating; the same in 5.1 (`rv bq51 fp R47…`: same parts) — note only. Pad gap `rv bq padgap R47.1 R47.2` = 0.800 mm (own pad pair) |
| A5 | FAIL (note) | `rv bq near` (1.3 mm): `Net-(R48-Pad2)` / `Net-(R51-Pad2)` are 0.502 mm apart on In2 (inner rule 0.5 mm met), ≥ 0.5 mm from GND / +3V3 on In1/In3/In4, 0.861 mm from 15V on In2, 1.229 mm from the F.Cu DC+ pour (R52.1), 1.249 mm from 15V. **But the pads of the two legs are 0.700 mm apart on B.Cu:** AC1 (R47.1) – AC2 (R50.1), `Net-(R47-Pad2)` – `Net-(R50-Pad2)`, `Net-(R48-Pad2)` – `Net-(R51-Pad2)` (`rv bq dist AC1 AC2` → B.Cu 0.700 mm at (0.15, 7.90)/(0.15, 7.20)). The checklist bar of 1.2 mm between legs is not met. The project rule exempts pad-to-pad gaps (`.kicad_dru` "HV functional, outer layers", `!(A.Type == 'Pad' && B.Type == 'Pad')`; README "Isolation domains" row "pad pairs exempt"), so DRC is clean, and 5.1 is identical (`rv bq51 near "Net-(R50-Pad2)"` → 0.700 mm). → F2. Also R50.2 / AC2 are 1.185 / 1.158 mm from the L1 pad 1 (PFC_DRAIN_2, new toroid footprint), pad-to-pad. Pickup: the two legs run as a pair (29 mm within 1 mm of each other on In2, so pickup is common to both legs). In1 GND lies under 57 of the 68 mm. The only switching net within 1 mm is PFC_PWM2 on In2 (0.618 mm over 1.9 mm, 3.3 V logic); Net-(DRV2-OUTL) is 1.30 mm away on B.Cu. Better than 5.1: there `Net-(R48-Pad2)` was 0.159 mm from 15V and `Net-(R51-Pad2)` 0.419 mm from DC+ (`rv bq51 near … --within 0.6`) |
| A6 | PASS | `rv bq net`: `Net-(U8-+)` ≈ 5.0 mm (F 3.0 + B 2.0, 2 vias), `Net-(U8--)` ≈ 8.8 mm (B.Cu). All of R79 (34.8, 14.6), R52 (30.0, 12.4), R49 (32.8, 13.9), R80 (32.1, 11.6), C126 (30.1, 10.0), C127 (29.5, 13.4) lie within 4.5 mm of U8 (33.1, 11.6). `rv bq near "Net-(U8--)" --within 0.5`: only GND 0.20, own output 0.225, +3V3 0.372, 15V 0.400 mm (all DC). U8 is 21 mm from DRV2 (12, 10); the DC+ pour comes no closer than 1.229 mm, and only to R52.1 (the ⅓-mains node) |
| A7 | PASS | `rv sch net +1V65_BIAS`: R80.1 and C126.1 are on `+1V65_BIAS`, which is driven by U9 through R131 22R (R131.1 = `Net-(U9--)` = U9 output and feedback, R131.2 = `+1V65_BIAS`), with C48 100n on the bias side. C126 returns to the same buffered node; there is no path to the REF1 divider (`Net-(U9-+)`). As simulated (FINDINGS 11.3): 7.3·10⁻⁶ V/V → 2.4 mV pk on the bias at 325 V pk = 29 mA on PFC_I, 13 mA DHB_I, 6 mA HEATER_I at line frequency (firmware may subtract k·VAC) |
| B1 | PASS | DC+ → R16 → R15 → R10 → U6 pin 3, R17 15k ‖ C130 1n to GND; GND → R112 → R111 → R109 → pin 4, R82 15k ‖ C131 1n feedback; R2 100R → DC_LINK_MEAS. V+ = DC·15k/3.015M, Vout = V+·(3.015M/3M) = **0.005·V_DC**: 400 V → 2.00 V, 450 V → 2.25 V, 483 V → 2.415 V, full scale 3.3/0.005 = 660 V (sim 652 V with 0.04 V headroom, FINDINGS 11.2). R112.1 = GND (equal source impedance). `rv sch cmp51 4`: only R2 1k → 100R, C130 / C131 new, C4 gone, and the output net renamed |
| B2 | PASS | 1/(2π·15 k·1 nF) = 10.61 kHz on both legs (sim 10.6 kHz). `rv sch ref C4` → "not in the netlist"; `rv bq fp C4` → "not on the board". DC_LINK_MEAS pads = J2.41 and R2.1 only → rule 1 of NEXT_REVISION 4c met |
| B3 | PASS (at limit) | 400 V / 3 = 133 V, 450 V / 3 = 150 V per 0805 (R16, R15, R10) against 150 V max working voltage (Uniroyal V.3 §7). RCWV = √(0.125 W·1 MΩ) = 354 V, so the 150 V maximum is the limit. ≤ the rating at 450 V. Up to the flyback LOVP trip of 483 V (CHANGES 1.x, R140 / R141) it is 161 V (+7 %), short-term and below the 300 V overload rating. P = 133²/1 M = 18 mW (450 V: 22.5 mW) of 125 mW. 5.1 used the same parts. → F3 (note) |
| B4 | PASS | `rv bq classes`: `Net-(R15-Pad1)`, `Net-(R10-Pad1)` are HV_PRIMARY. `rv bq near "Net-(R15-Pad1)" --within 1.3`: own pad pairs 0.730 / 0.800 mm, GATE2 1.061 mm (= Q6 pad 1, pad-to-pad, exempt; 5.1 identical 1.061 mm). `Net-(R10-Pad1)` (133 V): ≥ 0.5 mm on the inner layers, R82.1 (`Net-(U6--)`) 0.675 mm pad-to-pad, DC+ 1.200 mm (5.1: GND 0.457, DC+ 0.535, U6− 0.564 mm, so better now). The low-voltage legs are short (`Net-(R111-Pad1)` 2.0 mm, `Net-(R109-Pad1)` 1.5 mm). Positions as in the checklist: R16 / R15 F.Cu (15.5, 4.4) / (16.3, 1.9), R10 B.Cu (18.7, 4.6), R112 / R111 / R109 at (15.4 / 17.4, −3.1 … 0.4) |
| B5 | PASS (note) | R16.1 (DC+, F.Cu) at (15.5, 5.4) and the − reference R112.1 (GND, B.Cu) at (15.4, −2.1), 7.5 mm apart. The return-current IR drop in the GND copper between them is mV at most → × 1 (difference input) against 0.005·400 V = 2 V. Negligible, as the checklist says |
| C1 | PASS | R11 22k / R12 4.7k / C61 100n (C14663 X7R) → U10 pin 3; follower pin 1 = pin 2; R132 100R → AUX_MEAS (J2-43). 15 × 4.7/26.7 = 0.1760 → 2.640 V at 15.0 V; 14.2–15.5 V → 2.50–2.73 V; full scale 18.75 V (sim 18.5 V). τ = (22k ‖ 4.7k)·100 n = 3.87 k·100 n = 0.387 ms (411 Hz; sim 411 Hz, FINDINGS 11.1). Board / BOM: C61 = 100n (`rv sch bom 4`, `parts_table.py board` 0 differences). NEXT_REVISION 4.5 and 4b still say 1 µF → F4 (documentation) |
| C2 | PASS | R133 15k 0.1 % (C318137 Viking AR03BTCX1502) / R134 10k 0.1 % (C95204 Yageo RT0603BRD0710KL), C132 100n → U10 pin 5, follower pin 7 = pin 6, R135 100R → 5V_MEAS (J2-49). 10/25 = 0.400 → 2.000 V at 5.00 V, full scale 8.25 V. **τ = (15k ‖ 10k)·100 nF = 6 kΩ·100 nF = 0.60 ms (265 Hz).** The sheet note (sheet04.py:187 "tau 6k * 100n = 0.6 ms") and the simulation (265 Hz, FINDINGS 11.1) agree. **NEXT_REVISION.md section 4b ("6 kΩ · 100 nF → 1.6 ms") is wrong** → F4. Accuracy: divider ratio ≤ ±0.08 % (0.1 % parts), TLV9062 Vos ≤ ±1.6 mV at 25 °C / ±2 mV over temperature (SBOS839N §6.10) = ±0.08 / 0.1 % of 2.0 V → about ±0.18 % worst case, plus the ADC reference. The checklist's "< 0.1 %" is a little optimistic; it is still far better than the ±2.2 % rail tolerance |
| C3 | PASS | TLV9062 (TI SBOS839N, Mar 2017 – rev. Jul 2026, https://www.ti.com/lit/ds/symlink/tlv9062.pdf): VCM (V−) − 0.1 … (V+) + 0.1 V (§6.10 p 13), so 2.0–2.73 V is inside the range on 3.3 V. Abs-max input current ±10 mA, inputs diode-clamped to the rails (§6.1 p 10, note 2). With +3V3 absent: AUX node 2.64 V through 3.87 kΩ → ≤ (2.64 − ≈0.5)/3.87 k ≈ 0.55 mA; 5V node 2.0 V through 6 kΩ → ≈ 0.25 mA. Both ≪ 10 mA |
| C4 | PASS | R132 (39.2, 1.1) and R135 (37.0, −4.6) sit next to U10 (40.3, −3.4) at the op-amp, 100R each. AUX_MEAS pads = J2.43, R132.2; 5V_MEAS pads = J2.49, R135.2. No capacitor on either net |
| C5 | PASS (note) | Datasheet Fig. 5-6 / Table 5-3 (SBOS839N p 5–6), DGK: 1 OUT1, 2 IN1−, 3 IN1+, 4 V−, 5 IN2+, 6 IN2−, 7 OUT2, 8 V+. Netlist: 1 = 2 = `Net-(U10A--)`, 3 = `Net-(U10A-+)`, 4 = GND, 5 = `Net-(U10B-+)`, 6 = 7 = `Net-(U10B--)`, 8 = +3V3, as it should be. Board `rv bq fp U10`: pads 1–4 in one row, 5–8 in the other, pad 1 opposite pad 8. Land pattern DGK0008A (p ≈ 60): 8 × 1.4 × 0.45 mm, 0.65 pitch, (4.4) between rows. KiCad footprint: 1.625 × 0.5 mm, rows 4.225 mm apart, gap between pads 0.15 mm. The footprint covers TI's land pattern; the 0.15 mm gap is allowed only on low-voltage nets ("Same-footprint pad gap" DRU rule). The solder-mask web between those pads is for checklist 14 |
| D1 | PASS | Every row of the section 1 table matches `rv sch ref` and `kicad_next/J2_PINOUT.md` (pins 41 DC_LINK_MEAS / R2.1, 43 AUX_MEAS / R132.2, 47 VAC_MEAS / R65.1, 49 5V_MEAS / R135.2). One addition: AUX moved from J2-40 (5.1) to J2-43 (`rv sch cmp51 4`), as recorded in CHANGES 4b |
| D2 | PASS | Output networks R65 / R2 / R132 / R135 = 100R (C22775). Each output net has only J2 + resistor pads, so 0 pF of added capacitance. VAC / DC_LINK: TLV316 + 100 Ω with Cf inside the loop; AUX / 5V: TLV9062 follower + 100 Ω. This is exactly what FINDINGS 11.5 simulated (0.02 LSB / 0 LSB at ≥ 0.4 µs) |
| D3 | PASS | `rv bq padgap`: U8.5–C60.1 (2.2 µF) 0.680 mm; U6.5–C62.1 (2.2 µF) 0.710 mm; U10.8–C133.1 (100 nF) 1.080 mm. All ≥ 100 nF within 5 mm of V+ |
| D4 | PASS | TI SBOS752A §6 (p 3): DBV 1 OUT, 2 V−, 3 +IN, 4 −IN, 5 V+. Netlist U6 / U8 pins agree (A1, B1). `rv bq fp U6,U8` against `rv bq51 fp U6,U8`: the same footprint `tube_psu:SOT-23-5_Proteus`, the same position / rotation / pad coordinates (U8 rot 0 B.Cu: pads 1–3 at x 31.912, 4–5 at x 34.299, pad 4 opposite 3, pad 5 opposite 1, which is the standard SOT-23-5 pattern). Identical to the working 5.1 board |
| D5 | PASS | Lengths: VAC_MEAS 2.2 mm (B.Cu), DC_LINK_MEAS ≈ 10.1 mm, AUX_MEAS ≈ 7.1 mm, 5V_MEAS ≈ 20.1 mm (19.4 mm on In2 between the In1 / In3 planes; above the checklist's 15 mm hint, but shielded). `rv bq near <net> --within 0.3` lists only the other MEAS outputs (PFC_I1/I2_MEAS 0.155–0.158 mm at the J2 fan-out), HEATER_I_MEAS 0.256 mm, +3V3 planes, `Net-(C11-Pad1)` (= U1 output, low impedance, 1.2 mm parallel), `Net-(D10-PadA)` (0 mm parallel within 0.5 mm). No PWM lane |
| D6 | PASS | `rv bq fp C126,C127,C130,C131,C132,C133,R132,R133,R134,R135,U10` → all 11 on the board and routed (DRC unconnected 0, `drc_summary.py`). C4 is neither in the netlist nor on the board. `rv sch bom 9/4`: R49 / R80 12k C22790, R2 100R C22775, C61 100n. `parts_table.py board`: 0 field differences |
| E1 | PASS | Bench readings with no mains and DC+ from a supply: VAC = Vb ≈ **1.642 V** (not 1.650: bias divider 1.6554 V − 13.6 mV over R131, ±14 mV tolerance, FINDINGS 11.2); DC_LINK = 0.005·V; AUX ≈ 2.64 V at 15.0 V; 5V_MEAS ≈ 2.00 V |
| E2 | FAIL | Scale factors: VAC **0.004 V/V (5.1: 0.005 with 15k)**, DC_LINK 0.005, AUX 0.1760, 5V 0.400. The VAC gain appears only as "(gain 0.004, pole 13.3 kHz)" in CHANGES_5_2.md:130 (row 4.3), in the sheet 9 note (sheet09.py:72) and in simulation/FINDINGS.md 10 / 11.1. The firmware rows do not mention it: CHANGES_5_2.md:136 (4.9 "firmware": HEATER_I, AD2 only), NEXT_REVISION.md:100 (4.9) and NEXT_REVISION.md:135 (firmware bullet: channel map only). J2_PINOUT.md gives no scale factors. → F1 |

25 items: 23 PASS (three with notes: B3, B5, C5), 2 FAIL (A5 at note level, E2), 0 CANNOT VERIFY.

## Findings (ranked, most severe first)

### F1 VAC scale change 0.005 → 0.004 is not flagged as a firmware action
- Severity: **should fix** (a document that will mislead the builder / firmware)
- What is wrong: R49 / R80 15k → 12k changes VAC_MEAS from 0.005 to 0.004 V/V (−20 %). The documents list the firmware
  changes (CHANGES 4.9, NEXT_REVISION 4.9, NEXT_REVISION 4b "Firmware: update the channel map …"), but none of them
  names the VAC scale. 5.1 firmware run on 5.2 would read the line as 20 % low. The PFC voltage reference
  amplitude, brown-in / brown-out and line-OVP thresholds would all be off by that amount.
- Evidence: `grep -n firmware kicad_next/CHANGES_5_2.md NEXT_REVISION.md` → CHANGES_5_2.md:136, NEXT_REVISION.md:100,
  :135 (no VAC). The gain is only in CHANGES_5_2.md:130 "(gain 0.004, pole 13.3 kHz)". Calculation in A1.
- Smallest fix: one line in CHANGES 4.9 / NEXT_REVISION 4b "Firmware": "VAC_MEAS scale 0.005 → **0.004 V/V**
  (ADB1, ±412 V full scale, zero = +1V65_BIAS ≈ 1.642 V); also the bias line term 7.3·10⁻⁶ V/V (FINDINGS 11.3)".
  Optionally a scale column in J2_PINOUT.md (VAC 0.004, DC_LINK 0.005, AUX 0.1760, 5V 0.400).
- Confidence: high.

### F2 VAC chain: the two legs' pads are 0.70 mm apart on B.Cu (AC1–AC2 full line voltage), the same as 5.1
- Severity: **note** (equal to the bench-verified 5.1; permitted by the project's pad-pair exemption)
- What is wrong: R47 / R48 (AC1 leg, y 8.6) and R50 / R51 (AC2 leg, y 6.5) are separate 0805s 2.1 mm apart.
  The pad edge gaps are AC1–AC2 0.700 mm (up to 373 V pk at 264 Vrms), `Net-(R47-Pad2)`–`Net-(R50-Pad2)` 0.700 mm, and
  `Net-(R48-Pad2)`–`Net-(R51-Pad2)` 0.700 mm, all bare pads on B.Cu. The DRC passes only because pad-to-pad gaps are
  exempt from the 1.2 mm outer HV rule. That exemption is meant for gaps "set by the parts, e.g. TO-220 / TO-247 pin
  pitch" (`.kicad_dru` lines 53–55), not for two separate footprints. 5.1: identical (0.700 mm). This is functional insulation
  (line–line after the EMI filter, behind the fuse), so the board does not get less safe; it just does not get the
  extra creepage that 5.2 aims for. Nearby, also pad-to-pad: R50.2 / AC2 R50.1 are 1.185 / 1.158 mm from L1 pad 1
  (PFC_DRAIN_2, the new toroid footprint).
- Evidence: `rv bq dist AC1 AC2` → B.Cu 0.700 mm at (0.15, 7.90) / (0.15, 7.20); `rv bq51 near "Net-(R50-Pad2)"
  --within 1.3` → 0.700 mm; `rv bq near AC2 --within 1.3 --layer B.Cu` → PFC_DRAIN_2 1.158 mm.
- Smallest fix (optional, owner's choice): move R47 and R48 0.5 mm south (y 8.6 → 9.1; free B.Cu down to the H7
  keep-off at y ≈ 12.4, `rv bq area -2 8 8 13 --touch`) and re-attach their 1.5 mm link and the via at (6.4, 8.6).
  That gives 1.2 mm between all three leg pairs. Otherwise leave it as it is (as 5.1).
- Confidence: high on the geometry; the severity is a judgement under the acceptance bar.

### F3 DC-link divider 0805s at 100 % of their 150 V rating at 450 V (the same as 5.1)
- Severity: **note**
- What is wrong: R16 / R15 / R10 (1 MΩ 0805, Uniroyal 0805W8F1004T5E, 150 V max working voltage) carry 133 V at
  400 V and 150 V at 450 V, and 161 V just before the flyback LOVP trip at 483 V. That is inside the rating up to
  450 V, at the limit, and short-term 7 % above it in an over-voltage fault (overload rating 300 V). It is the same
  in 5.1, and `lib/jlc_parts_next.csv` notes it ("0805 rated 150 V").
- Evidence: Uniroyal data sheet V.3 §7 Ratings p 4/9 (URL in A4); B3 calculation.
- Smallest fix: none needed under the acceptance bar. If margin is wanted, use a 4 × 750 kΩ chain or a ≥ 200 V
  (high-voltage series) 0805 in the same footprint (the gain would need the R17 / R82 ratio kept).
- Confidence: high.

### F4 NEXT_REVISION.md has two wrong numbers for the AUX / 5V monitors
- Severity: **note** (documentation; CHANGES_5_2.md, the sheet and the board are right)
- What is wrong: (a) NEXT_REVISION 4.5 ("C61 1 nF → **1 µF**") and 4b ("mux-leakage fixes … 4.5 (AUX, C61 1 µF) –
  both already in the list") describe the unbuffered option. As built, AUX is buffered by U10A with C61 = 100 nF
  (CHANGES 4.5 / 4c.2, sheet04.py:166, board / BOM). (b) NEXT_REVISION 4b "100 nF across the 10 kΩ (6 kΩ · 100 nF →
  **1.6 ms**)" should say **0.6 ms** (15k ‖ 10k = 6 kΩ; sheet04.py:187 says 0.6 ms; the simulation shows 265 Hz,
  FINDINGS 11.1).
- Evidence: NEXT_REVISION.md section 4 row 4.5, section 4b 5V_MEAS bullet; `rv sch ref C61,C132`; calculation in C2.
- Smallest fix: change 4.5 to "→ 100 nF + U10A follower (decided, CHANGES 4.5 / 4c.2)" and "1.6 ms" to "0.6 ms".
- Confidence: high.

### F5 DC-link summing node routed 0.32 mm from the GATE2 pad (new in 5.2)
- Severity: **note**
- What is wrong: the new C131 (feedback capacitor) sits at (16.7, 6.0). Its `Net-(U6--)` track runs north at x 16.03
  (y 2.6 … 4.6) and passes 0.318 mm from R20 pad 2 (GATE2, the Q6 turn-on gate, 0 → 15 V edges). Estimated coupling
  ≈ 0.04 pF against Cf = 1 nF: 15 V × 0.04 pF / 1 nF ≈ 0.6 mV (≈ 3 LSB) of spike per edge, decaying with
  R82·C131 = 15 µs. Rising and falling edges cancel on average. It is small next to a 2 V signal used for a slow
  voltage loop, but it is a pickup path that 5.1 did not have (5.1: nothing switching within 1 mm of `Net-(U6--)`).
- Evidence: `rv bq near "Net-(U6--)" --within 0.4` → GATE2 0.318 mm B.Cu at (15.93, 2.60) / (15.61, 2.60);
  `rv bq51 near "Net-(U6--)" --within 1.0` → no GATE2.
- Smallest fix: none required. If the bench shows PFC-synchronous spikes on DC_LINK_MEAS, re-route that 2 mm piece
  0.5 mm further east or put C131 west of U6 next to R109.
- Confidence: medium (the capacitance is an estimate, not a field solve).

### F6 Checklist correction: the VAC input common mode swings to 3.12 V
- Severity: **note**
- What is wrong: the checklist (A2) says the U8 inputs sit at ≈ 1.64 V ± 1.4 mV. In the bridgeless PFC each line
  goes from ≈ −1 V to +V_pk against GND (DB1 return), so V+ = Vb + 0.003984·(V_AC2 − Vb) reaches 3.12 V at 373 V pk.
  That is inside the TLV316 rail-to-rail VCM (to (V+) + 0.2 V) but 0.18 V from V+, and it crosses the input-pair
  transition at about (V+) − 1.4 V. The resulting error is ≤ 0.27 mV (CMRR 75 dB), negligible. The inputs reach
  (V+) + 0.5 V only at ≈ 540 V pk, beyond output clipping.
- Evidence: A2 calculation; SBOS752A §7.7.
- Smallest fix: none (design fine). FINDINGS 11.2 could add one line on the input common-mode range.
- Confidence: high on the arithmetic; medium on the PFC line-to-GND waveform (taken from the bridgeless topology, not
  from a simulation).

## Compared with 5.1
- **Equal:** topology, divider parts (1 MΩ 0805 C17514), placement of every chain resistor and of U6 / U8 (identical
  coordinates and footprint: `rv bq51 fp R47,…,U6,U8`), the DC-link scale 0.005, the AUX divider, the J2 pins for VAC /
  DC_LINK, the 0.7 mm cross-leg pad gaps (F2), and the 150 V-rating margin (F3).
- **Better:** HF feedthrough (VAC −33 / −50 dB at 1 / 50 MHz against +22 dB in 5.1; DC_LINK feedthrough fixed, FINDINGS
  11.1); no VAC clipping above 330 V pk (now 400 V pk); mux leakage on DC_LINK (254 LSB → 0.02) and AUX (505 LSB → 0) by
  R2 100 Ω / C4 removed / the U10A buffer; bias line coupling 4.7·10⁻⁵ → 7.3·10⁻⁶ V/V; HV intermediate nodes are
  now ≥ 0.5 mm from other nets (5.1: `Net-(R48-Pad2)` 0.159 mm from 15V, `Net-(R51-Pad2)` 0.419 mm from the DC+ pour,
  `Net-(R10-Pad1)` 0.457 mm from GND); new 5V monitor.
- **Worse:** only F5 (a new 0.32 mm neighbour of the U6 summing node; negligible by estimate). The VAC scale change
  (F1) is intended, but firmware must follow it.

## Could not verify
- The real line-to-GND waveform of AC1 / AC2 under PFC operation (used for the common-mode and per-resistor stress
  figures in A2 / A4 / F6). It comes from the bridgeless topology, not from a simulation in the repository.
- The GATE2 → `Net-(U6--)` coupling capacitance (F5) is a hand estimate; only a bench measurement (DC_LINK_MEAS at
  the J2 pin during PFC switching) settles it.
- Whether a 2.5 kV differential surge can reach AC1 / AC2 at full amplitude (it depends on the EMI filter / varistor,
  checklist 05). The 830 V-per-resistor figure is the unclamped worst case.
- I did not run a DRC, `check_next.sh` or the creepage passes (as instructed). I used `reports/next/drc.json`
  (2026-11-24 06:40, newer than the board: 0 unconnected, 137 violations = courtyard / pth-in-courtyard /
  starved-thermal only).

## Outside scope
- **12 (thermal / mechanical):** courtyard overlaps involving these parts are in the DRC report (R47/R48, R50/R51,
  R15/R16, R111/R109, R79/U8, R79/R49, U8/R49, C60/U8, R82/U6, R109/U6, C62/U6). They are inherited 5.1 placements
  and part of the accepted 133 courtyard items.
- **05 / 10:** L1 pad 1 (PFC_DRAIN_2) is 1.158 mm from the R50 AC2 pad and 1.185 mm from R50.2, pad-to-pad, just
  below the 1.2 mm outer HV figure (new toroid footprint).
- **04 / docs:** the NEXT_REVISION 4c per-channel table still names LMH6658 / INA296 for the current channels (5.2 has
  LMH6643), and 4c rule 4 dwell times were updated per FINDINGS 11.5; check that the control-card documents use
  A ≥ 2 µs / B ≥ 3 µs before HEATER_I.
- **03 / 13:** the 420 V divider resistors R23 / R34 / R39 are noted as "at the limit" of the same 150 V 0805
  rating (`lib/jlc_parts_next.csv` note on C17514).
- **14:** U10 VSSOP-8 pads are 0.15 mm apart. Check the solder-mask web or gang opening in the fab output.
- **13:** R133 (C318137) stock at check time was 3509, enough but the lowest of these parts.
