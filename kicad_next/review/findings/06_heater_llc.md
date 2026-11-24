# Findings: 06 heater LLC  (reviewer: Claude Opus 5.5, 2026-11-24, commit 3e1e31e)

## Summary
Nothing found that stops ordering. The circuit is right. Pin use of DRV3 / DRV4, the gate networks, the bootstrap and
the SR pairing all match the datasheets and 5.1. The tank value is consistent across the documents, and the barrier
measures 10.42 mm at TR2.

Three things are worse than 5.1 and should be fixed or documented before ordering:
- **F1:** the HEATER_I sense track starts at the Q10 source via. It does not start at the shunt pad. About 12.5 mm of
  0.8 mm B.Cu (≈ 7 mΩ, more than the 4 mΩ shunt) is now inside the measurement.
- **F2:** the firmware's fixed SR conduction time (2.65 µs) and the 150 kHz frequency floor were tuned on 5.1. The
  new 13.2 nF C0G tank and the open leakage question (42 vs ≈ 59 µH) move the resonant half period to 2.34 – 2.77 µs.
  The wrong end of that range causes reverse SR current at first power-up.
- **F3:** Q14_DRAIN copper (Q1 drain) is 4.48 mm on two layers. 5.1 had 7.7 mm on four layers, and the tab has 12 vias
  instead of 16. It still meets the 15 A width rule.

Nine items are CANNOT VERIFY. The Infineon, Nexperia, Rubycon, IHHEC and IXYS datasheets could not be fetched in this
session (403 / JavaScript pages), and some items need the real transformer.

## Checklist results
| Item | Verdict | Evidence |
|---|---|---|
| A1 | PASS | fr = 1/(2π√(42 µH × 13.2 nF)) = **213.8 kHz**. C0G ±5 % gives 208.7 – 219.4 kHz; together with ±10 % leakage, 199 – 231 kHz. Both are inside 150 – 270 kHz, so 150 – 270 kHz still brackets fr. 5.1 (12.5 nF effective, inferred) gave 219.6 kHz; 5.2 is −2.7 %. The 42 µH comes from design document p 19 table 4.1 ("64 turn primary windings in parallel 42 µH") and the owner's statement (TR2_OPENMAGNETICS.md:21). It is a measurement on a test unit; the method (which secondary terminals were shorted) is not stated. If the operating leakage is 58.7 µH (TR2_OPENMAGNETICS.md:43-46), fr = 180.8 kHz, still inside the range. I re-checked every number in that file's resonance table (42 / 58.7 µH × 12.5 / 13.2 / 18.8 nF → 220 / 186, 214 / 181, 179 / 151 kHz): all correct. |
| A2 | CANNOT VERIFY | **Calculation** (n = 32, n·Vo ≈ 205 V, Lm 320 µH). Load part of the primary current: (π/2√2)·Io/n = 0.35 / 0.52 / 0.69 A rms at 10 / 15 / 20 A. Magnetising part, I_m,pk = n·Vo/(4·Lm·f): 0.98 / 1.02 / 1.07 A at 163 / 157 / 150 kHz, i.e. 0.57 / 0.59 / 0.62 A rms. Totals: **0.67 / 0.79 / 0.93 A rms**. Each 3.3 nF part carries ¼: **0.17 / 0.20 / 0.23 A rms**. Mid-point swing V_pk = I_pk/(2πf·13.2 nF): ≈ 97 V at 15 A (quadrature sum, I_pk 1.26 A), 135 V if the peaks add; ≈ 117 – 165 V at 20 A / 150 kHz. Per-part peak: 200 + 165 = 365 V (375 V at a 420 V bus), against a 630 V rating (LCSC C105987 page, fetched: IHHEC, 630 V, NP0, ±5 %). This agrees with the TR2 file's "200 V ± 98 V, 0.22 A rms". 5.1 X7R saw ×1.056 more swing (12.5 nF). **Not verifiable:** the datasheet PDF (lcsc.com/datasheet/C105987.pdf) returned an empty HTML shell, so there is no tan δ / AC current limit. With an assumed C0G tan δ of 0.1 % (not a datasheet value): ESR ≈ 0.31 Ω at 157 kHz, P ≈ 12 mW per part, so ΔT is small. |
| A3 | PASS | `rv sch ref` / sheet 6 show C22 / C41 / C42 / C49 = 3.3n. `rv sch part C22`: lcsc C105987, mpn C1206N332J631T, IHHEC, review "stock / price not read". sheet06.py:85, CHANGES_5_2.md:51 (row 2.9) and DAB_SIMULATION.md:323 all say 3.3 nF / 13.2 nF. Notes: DAB_SIMULATION.md:322 still opens with "4 × 4.7 nF, i.e. a split 18.8 nF" before the bracket, and `lib/part_map_next.csv` C22 has `device=12061C103KAT2A` (a 10 nF X7R part number, stale) – see F8. Stock / price not read (as the table says). |
| A4 | PASS | R155–R158 = 220k 1206 (sheet 6). Chain DC+ → R155 → R156 → HEATER_CAP_MEAS → R157 → R158 → HEATER_CURRENT. At 400 V: 0.455 mA, **100 V / 45 mW per resistor** (105 V at 420 V); the rating is 200 V (`rv sch part R155`: C17956 1206W4F2203T5E "200 V"; parts-table value, datasheet not fetched). The DC current returns through R30: 0.45 mA × 4 mΩ = 1.8 µV, negligible. Mid point: Thevenin 220 kΩ, C 13.2 nF, so τ = **2.9 ms**; it settles in ≈ 15 ms, far shorter than the DC-link ramp. The firmware should start the LLC only after the link is up. |
| A5 | CANNOT VERIFY | Schematic note "E25 : 64/2/2, check primary turns!" (sheet06.py:98). Design document p 19: 64 T / 2 T, 32 : 1. Owner 2026-11-23: **66 T** (TR2_OPENMAGNETICS.md:20). Grep finds 66 nowhere else. At M = 1: 400/2 × 2/64 = **6.25 V**; with 66 T, **6.06 V**. Rectifier and copper drops are ≈ 0.1–0.3 V at 15 A (RDS(on) not fetched). Either way the converter must boost (M ≈ 1.03 – 1.10), i.e. run below fr – consistent with "small boosting is desired" (p 18). No single number is documented as the one on the working 5.1 transformer: count / measure the turns ratio of the 5.1 TR2 before winding (F6). |
| A6 | PASS | Chain: J2-5 EPWM5A → DRV3.1 INA → OUTA (15) → HEATER_HI_DRV → R24 → Q11 (high side, drain DC+). J2-13 SYNCH_1 → ISO1.3 → ISO1.14 EPWM5A_ISO → DRV4.4 INB → OUTB (5) → R28 → HEATER_SYNC_GATE_2 → Q2, drain Q13_DRAIN = TR2.6 + 7 (`rv sch net`, sheet 6). CHANGES_5_2.md:81-97 puts the dots on 1+2 / 9+10 / centre tap. With Q11 on, pins 1+2 are +200 V against 4+5, so the dotted secondary ends are positive. 6+7 is then the negative end against the centre tap, so Q2 must conduct: consistent. 5.1 has the same pairing: 5.1 DRV4 (IXDD604) INB_3 = EPWM5A_ISO → OUTB_5 → R28 → GATE_2 → Q2 → Q13_DRAIN, and TR2 has the same pin nets (`rv sch51 ref DRV4,R28,Q2,TR2`). The physical dot is unverified (F2 bring-up). |
| A7 | CANNOT VERIFY | A model now exists: simulation/llc/TR2_OPENMAGNETICS.md:63-68 predicts 4 – 6 W (±50 %; 2.9 / 4.0 W with a spacer gap). The bench says "core slightly warm, LLC not perceivably heating" (design document p 33). They disagree, and the model itself calls its number implausible. To measure: core and winding temperature (thermocouple in the winding) at 10 A and 15 A after 30 min, and Lm / leakage per the TR2 file's three LCR readings. |
| A8 | CANNOT VERIFY | The P7 vs CFD7 Qrr / trr / Coss(er) / diode dv/dt could not be read: infineon.com part pages render by JavaScript, and LCSC / datasheets.com returned an empty shell or 403. A strategy is written (DAB_SIMULATION.md:347-353: start high and sweep down, raise f on overcurrent, check the sign of HEATER_I at each edge, fall back to IPD60R360PFD7S). **Analysis:** with the reflected load shorted (start-up, short circuit) the tank is Lr–Cr, inductive above fr = 181 – 231 kHz. The 270 kHz start of the design document (p 20) is above the worst case (231 kHz: 42 µH −10 %, C −5 %), so it is compatible, though less conservative than "≥ 2 × fr" (362 – 428 kHz). In steady state, FHA with Lm 320 µH, 13.2 nF and 10 – 30 A puts the peak-gain (ZVS boundary) frequency at **73 – 90 kHz**, far below the 150 kHz floor. Capacitive mode is therefore limited to start-up / short circuit below fr. HEATER_I edge sampling is degraded by F1. |
| A9 | CANNOT VERIFY | Lm is documented: 320 µH, 1 mm gap (design document p 19). The model gives 288 µH for a spacer gap (TR2 file:50-51). I_m at the edge = n·Vo/(4·Lm·f): **1.07 A at 150 kHz, 0.98 A at 163 kHz, 0.73 A at 214 kHz, 0.58 A at 270 kHz** (×1.11 for 288 µH). ZVS needs t_dead ≥ 2·Co(tr)·400 V / I_m, i.e. t_dead[ns] ≥ 0.75 · Co(tr)[pF] at 150 kHz and ≥ 1.38 · Co(tr)[pF] at 270 kHz, plus TR2 winding capacitance. Hardware DT: R130 10 k → 80 / 100 / 120 ns (UCC21520 SLUSCJ9F, 6.x Switching Characteristics, "Dead time, RDT = 10 kΩ"). The firmware LLC dead time is not in the repository: CHANGES_5_2.md:174 names it but gives no value, and the TR2 file:73-74 estimates ≈ 270 ns. Co(tr) of IPD60R280P7S was not fetched (the LCSC table only gives "Coss 14 pF", no condition). |
| B1 | PASS | `rv sch ref DRV3` against the UCC21520 DW pinout (SLUSCJ9F rev. F, Nov 2024, Fig. 5-1 / Table 5-1, https://www.ti.com/lit/ds/symlink/ucc21520.pdf): 1 INA EPWM5A, 2 INB EPWM6A, 3 / 8 VCCI 5V (C53), 4 GND, **5 DIS GND** ("enables if set low or left open … recommended to tie to ground"), 6 DT R130 10k ‖ C121 100p (≤ 1 nF recommended), 7 / 12 / 13 NC, 9 VSSB GND, 10 OUTB HEATER_LOW_DRV, 11 VDDB 15V (C18 10 µF at 3 mm; C52 4.7 µF is 13 mm away near D11), 14 VSSA switch node, 15 OUTA HEATER_HI_DRV, 16 VDDA bootstrap. Pull-downs R78 (EPWM5A) and R77 (EPWM6A) are present. UCC21520 (non-A) has the 8-V UVLO: on 8.5 / 8.9 V max, off 7.9 V typ, recommended VDD ≥ 9.2 V. VDDB = 15 V, VDDA ≈ 15 − VF(S1M) − R99 drop ≈ 13.5 – 14 V: OK. 5.1 Si8271 had EN = 5V (no disable). |
| B2 | PASS | SLUSCJ9F §8.4.2.2: "The output signals' dead time is always set to the longer of either the driver's programmed dead time or the input signal's own dead time. If both inputs are high simultaneously, both outputs will immediately be set low." Minimum pulse width tPWmin 20 ns; propagation 26 / 33 / 45 ns. The half period at 270 kHz is 1.85 µs ≫ 20 ns. VINH 1.2 / 1.8 / 2.0 V (5 V input from J2: OK). |
| B3 | PASS | Netlist: D35 A = HEATER_HI_GATE, K → R59 → HEATER_HI_DRV; D33 A = HEATER_LOW_GATE, K → R31 → HEATER_LOW_DRV. These are turn-off paths, correct. Values = 5.1 (`rv sch51 ref`): R24 10R 1206, R59 3.3R 1206, R37 10R 0805, R31 3.3R 0805, R66 10k. D35 is new (the Si8271 had split OUT+ / OUT−). Peaks: turn-on ≤ 15 V / 10 Ω = 1.5 A < 4 A source; turn-off ≤ (15 − 0.6) / 3.3 Ω ≈ 4.4 A < 6 A sink (SLUSCJ9F 6.x). ZLLS400: IF 0.52 A, IFPK 0.85 A, 12 A for a ≤ 100 µs rectangular pulse, IFSM 2.5 A / 10 ms (Diodes ZLLS400 datasheet, Absolute Maximum Ratings, fetched). The ns-long ≈ 4 A turn-off pulse is above IFPK on paper – the same as the bench-verified 5.1 D33 network (note F9). Resistor power: Qg·15 V·270 kHz = 18 nC × 15 × 270 k = **73 mW** in total (Qg "18nC@10V" from the LCSC C536813 table, not the datasheet). R24 1206 / R37 0805 have > 3× margin even at 2× Qg. CHANGES open question 12 (R99 orientation) is electrically irrelevant. |
| B4 | PASS | D11 S1M / R99 2R / C25 1u, the same as 5.1 (`rv sch51 ref D11,R99,C25`). The LLC has a guaranteed ≈ 50 % low-side on-time (≥ 1.85 µs). The S1M trr / recovery loss number could not be quoted (datasheet not fetched); the same part as 5.1. |
| B5 | PASS | C20 100n: DC+ – HEATER_CURRENT on both boards (`rv sch51 ref C20`). 1206 → 1210 630 V (CHANGES 5.6 / cmp51). The bridge HF loop Q11–Q10–C20 excludes R30. |
| B6 | CANNOT VERIFY | Loss per switch: I_rms = I_pri/√2 = 0.56 A at 15 A, 0.66 A at 20 A. With 280 mΩ (LCSC "280mΩ@10V") × an assumed 1.8 at 100 °C: **0.16 / 0.22 W**. ZVS switching loss ≈ 0. Copper: Q11 tab pad 37 mm² + zone `S3A_Q11_tab_DC` 20.6 mm² + a 27 mm² DC+ piece at C20 / C42, joined to pour 29 (994 mm²) through a neck. Q10 tab: switch-node zone `S3A_HHS_F` 124 mm² (F.Cu only). Both are **below the 2 cm² + thermal-via target** of NEXT_REVISION.md:194. Thermal vias are excluded by the given decisions (DC+ outer only, no switch node inside). RthJA could not be fetched. Even 150 K/W (pessimistic, not a datasheet value) gives ΔT ≈ 25 – 33 K ≤ 40 K. |
| C1 | PASS | `rv sch ref DRV4` against the UCC27524A D pinout (SLUSBP4C rev. C, Jun 2024, Fig. 4-1, https://www.ti.com/lit/ds/symlink/ucc27524a.pdf): 1 ENA 6V3, 2 INA EPWM6A_ISO, 3 GND HT_GND, 4 INB EPWM5A_ISO, 5 OUTB → R28 → GATE_2 (Q2), 6 VDD 6V3, 7 OUTA → R63 → GATE_1 (Q1), 8 ENB 6V3. Pull-downs R117 / R91 8.2k, gate R108 / R107 1k. `rv bq padgap DRV4.6 C17.1`: 2.10 mm edge, 3.39 mm centres. |
| C2 | PASS | SLUSBP4C §5.5 (D package): VON 3.91 / 4.2 / 4.5 V at 25 °C (3.7 – **4.65 V** over temperature); VOFF 3.4 / 3.9 / 4.4 V; "outputs held low during VDD-UVLO"; VIN_H 1.9 / 2.1 / **2.3 V** max ≤ 3.3 V from ISO1; ENx high or floating = enabled. So the SR is active from ≤ 4.65 V output. Below that, the body diodes rectify: e.g. 3000 µF charged to 4.65 V at 10 A takes ≈ 1.4 ms, ≈ 6 mJ per FET at ≈ 0.8 V (VSD assumed, not fetched) – harmless. IXDD604 UVLO / min VCC for the comparison was not fetched (note). ISO1 side 2 runs from the V3 LDO on 6V3, so below ≈ 3.5 V there is no SR command on either board. |
| C3 | CANNOT VERIFY | The BUK9Y15-60E datasheet could not be fetched (assets.nexperia.com 403, mirrors 403 / DNS). The JLC C7091976 table gives "10.8mΩ@10V", Qg 17.2 nC, 60 V, without conditions; RDS(on) at 5 – 6.3 V and its temperature factor are unknown. Per FET at 15 A: I_rms = 0.785 × 15 = **11.8 A**; at an assumed 15 mΩ × 1.5 (100 °C) = 22 mΩ, P ≈ 3.1 W, which exceeds the 2.5 W bar. At 10 A: 1.4 W. Same FET as 5.1 (bench to 15 A per the owner). VDS 60 V ≫ 2 × 6.3 V + ringing. R63 / R28 4.7 Ω: Qg·6.3 V·270 kHz ≈ 29 mW. |
| C4 | CANNOT VERIFY | I_C,rms ≈ 0.483 × Io = 4.8 / 7.2 A at 10 / 15 A, at 2 f ≈ 300 – 540 kHz. The Rubycon 10ZLH1500MEFCT78X20 and Panasonic EEU-FR1A152L ripple / impedance figures and the Samsung CL31A106KBHNNNE DC-bias / ESR were not fetched, so the share and the "replacement not lower rated" test cannot be done. The bank and its positions are identical to 5.1 (C8 / C9 / C23 / C33 / C24 / C31 / C32: same coordinates in `rv bq fp` / `rv bq51 fp`). |
| C5 | **FAIL** | **Q14_DRAIN (Q1 drain)** narrowest channel TR2.10 → Q1 tab: **4.48 mm F.Cu and 4.48 mm B.Cu**; 5.1: **7.68 mm F.Cu / 7.76 mm B.Cu / 7.76 mm In1**, plus a pour on In2 (`rv bq neck Q14_DRAIN …`, `rv bq51 neck …`). Pours: 104 mm² × 2 layers vs 5.1 151 mm² × 4. **12** tab vias vs 16 (`rv bq net Q14_DRAIN` / `rv bq51 net`). Reason: the zone top edge is now y −66.0 (ISO1 T-slot bar at y −64.09 … −62.59), 5.1 −63.25 (`rv bq xsec Q14_DRAIN F.Cu x -42`). Rule check (README: I = 3.25·w^0.725): 4.48 mm → 9.6 A per outer layer; 19 A for F + B against 11.8 A rms at 15 A (15.7 A at 20 A), so the width rule is met. F.Cu alone is below 11.8 A, so the path depends on B.Cu fed by 12 vias of 0.3 mm (≈ 9 A for ≈ 6 A share). The other paths are not narrower than 5.1: Q13_DRAIN 7.10 mm F / B (5.1 7.09 / 7.10, plus inner); 6V3 B.Cu 10.5 mm at x −50 / −45 and 22.6 mm at x −60 (5.1 the same), **plus** In3 22.5 mm (new); HT_GND F.Cu ≥ 11.7 mm (5.1 13.0) → 19 A. Finding F3. |
| C6 | PASS | Q1: Q14_DRAIN 104 mm² F + 104 mm² B (1.04 cm² per layer, just ≥ 1), 12 vias in the tab. Q2: Q13_DRAIN 166 mm² F + B, 16 vias. Q1 is borderline and worse than 5.1 (151 mm² × 4 layers, 16 vias); see F3. |
| C7 | PASS | HT_6V3 / HT_GND = `Terminal_2x1_P5.00mm_D2.0mm_Drill1.4mm`, two pads "1" each, the same footprint and place as 5.1. Spokes 0.8 mm (README:481); 0 starved_thermal in the island (`drc_summary.py starved_thermal`: only C102). 6V3 copper reaches the terminal on B.Cu + In3 (F.Cu 6V3 zone ends at x −46.6): 2 pads × 4 × 0.8 = 6.4 mm 1 oz + 6.4 × 0.3 (In3 0.5 oz) ≈ **8.3 mm equiv.** HT_GND: F.Cu + In1 + In4 ≈ 10.2 mm equiv. Both ≥ 6 mm. The terminal part is consigned, "blade (faston) terminals: hardware" (`rv sch part HT_6V3`); its current rating is unknown. |
| C8 | PASS (note) | R54 at (−55.1, −61.7), R55 (−52.9, −62.6): the north edge of the island, off the WP2 / WP3 (x −42.8, y −74 / −79) → C31 / C32 / terminal (x −64 … −68, y −64 … −82) current path. It sees part of the plane drop between WP and terminal (mV), not the terminal voltage. |
| D1 | **FAIL** (note) | `rv bq loop Q11.2 Q11.3 Q10.2 Q10.3 C20.2 C20.1`: **59.5 mm / 23.0 mm²**; 5.1 (TO-220): **36.7 mm / 20.6 mm²**. The path is 1.62 × 5.1 (bar 1.5 ×) and just under 60 mm; the enclosed area is only 1.12 ×. The pad-centre path overstates DPAK tabs. The LLC switches with ZVS. Finding F5 (note). |
| D2 | PASS | Q11 tab → C42 pad 1 on F.Cu: neck **1.85 mm**. Q11 tab → bulk C56 on F.Cu alone: **0.92 mm** (≥ 0.5 mm for ≈ 0.25 A dc + ripple). DC+ F.Cu cuts: 2.7 mm at y −78, 4.4 mm at y −70, 7.3 mm at y −60; no DC+ on B.Cu there. Unconnected 0 (`drc_summary.py`, report newer than board). Nearest foreign outer copper to the switch node: DC+ 1.20 mm. |
| D3 | PASS | `rv bq near HEATER_HI_SOURCE --within 1.3`: outside the DRV3 group, every outer-layer item is ≥ 1.200 mm (HEATER_CURRENT, CAP_MEAS, GND, 15V, DC+). Inside the group: HI_GATE 0.20, HI_DRV 0.40 mm (allowed). Inner layers: HEATER_LOW_DRV In2 0.65 mm, GND In1 / In4 and 15V In3 0.50 mm – these are to the via / TR2 barrels of the switch node, not to inner switch-node copper. `near HEATER_CAP_MEAS`: only GND In1 / In4 0.50 mm (barrel) and the switch node 1.20 mm. Cap pad gaps C42 / C49 / C41 / C22: **1.80 mm** each ≥ 1.5. HEATER_CAP_MEAS pour 25 is **0.95 mm from the top board edge** (y −91.35), identical to 5.1 (pour bbox −90.4); DC+ pour 5.81 mm, HEATER_CURRENT 5.75 mm. The cap row (x −17.3 … −6.8) is ≥ 10 mm west of the UART island (x ≥ 4). |
| D4 | PASS | Gate parts at the FETs: R24 / R59 / D35 / R36 at (−19.4 … −15.5, −73.8 … −79.2), B.Cu under Q11; R37 / R31 / D33 / R66 at (−11.2 … −8.9, −65 … −70), under Q10. `rv bq nets '*HEATER_HI*'`: F.Cu / B.Cu only. HEATER_HI_DRV 19.3 mm B.Cu, return = 0.5 mm switch-node B.Cu track 1.4 mm beside it (README:1436-1441). HEATER_LOW_DRV: In2 (−27.25, −59.95) → (−24.15, −63.05) → (−9.35, −63.05); In1 GND under it from x −25.10 to −9.69 (`rv bq xsec GND In1.GND y -63.05`), only the last 0.3 mm at the via is uncovered. Lengths: high side 34.7 mm vs 5.1 16.1 mm (2.2 ×), low side ≈ 33 mm vs 13.3 mm (DRV9 was local). Above 2 × 5.1, but accepted in README:1468-1470 ("the price of gate resistors at the FET with the FETs swapped"). |
| D5 | **FAIL** | The In2 HEATER_CURRENT sense track to R106 starts at **(−12.6, −68.3), inside the 0.8 mm via (−12.8, −68.6) at Q10's source**. It does not start at R30 pad 1 (−11.2, −80.4). Between the tap and the shunt are 12.46 mm of 0.8 mm B.Cu (segments (−12.8, −68.6) → (−12.8, −71.0) → (−11.2, −72.6) → (−11.2, −80.4)) ≈ **6 – 7.7 mΩ**, versus the 4 mΩ shunt. 5.1: the sense left R30 pad 1 by a 1.3 mm B.Cu stub to the via (−11.2, −79.1), then In2 → R106 (b51.json tracks). It was a Kelvin tap. Finding F1. |
| D6 | PASS | `rv bq padgap TR2.1 TR2.10` and `TR2.5 TR2.6`: **10.42 mm** ≥ 8.2 mm (the checklist's 8.0 is now 8.2 after stage 13d, README:207-224; the board governs). `rv bq near @HEATER --within 8.2 --other-domain`: only ISO1 pad rows (7.25 mm) and the T-slot bar region at TR2.10 (5.36 mm straight to GND), all slot-separated. check_domains.py was not re-run (instruction: the board passed the full gate today); README stage 13d: smallest PRI ↔ HEATER round a slot 8.32 mm, nothing below 8.2. |
| D7 | PASS | `drc_summary.py courtyards_overlap -71 -91 -5 -44`: 27 pairs in the area. In the heater part: WP2 / WP3 ↔ C8 / C33 / C9 / C23, C31 ↔ C32, R108 ↔ C31 / C32, C24 ↔ HT_GND / HT_6V3, R31 / R37 ↔ D33, C20 ↔ C42 / C22. All heater-island positions are identical to 5.1. No body collision: C31 / C32 8 mm cans at 8.4 mm pitch (0.4 mm gap); C20 body ends y −84.15, C42 body starts −84.8; Q11 / caps x ≥ −17.4 vs TR2 body x ≤ −21.4; WP pads (x −45.1 … −40.5) 1.5 mm from the TR2 body (x −39.0), so they are accessible. |
| E1 | PASS | As D4: the low-side path is longer than with the local 5.1 DRV9 at (−9.6, −66.2) (`rv bq51 fp DRV9`); the In2 lane has GND over it; accepted in the README. |
| E2 | PASS | `rv bq fp Q10,Q11`: Q11 tab (pad 2) = DC+, Q11.3 = switch node; Q10 tab = HEATER_HI_SOURCE, Q10.3 = HEATER_CURRENT, Q10.1 = HEATER_LOW_GATE. Same roles as the 5.1 netlist (Q11 D = DC+, Q10 S = HEATER_CURRENT). The physical places are swapped against 5.1 (5.1 Q10 at y −75, Q11 at −63). |
| E3 | PASS | EPWM5A_ISO → INB → OUTB → R28 → Q2 on both boards (A6). EPWM6A_ISO → INA → OUTA → R63 → Q1 on both. cmp51 shows only renumbering. 5.1 checked by pin names of the 5.1 symbol (IXDD604 DFN pinout datasheet not fetched). |
| E4 | PASS | C31 / C32 (−63.7, −76.3 / −67.9), pads 1.6 / 0.8 mm at 3.5 mm pitch; R30 (−10.71, −80.4) B.Cu, pads 0.35 × 2.0: identical in `rv bq fp` / `rv bq51 fp`. Only the library names differ. |
| E5 | PASS | reports/next/erc.rpt: 0 errors, **15 warnings**; ground_pin_not_ground on DRV5.14, DRV6.14 and **DRV3.14 (VSSA)** – by design. README:59 still says "14 warnings" (doc note, F8). |
| F1 | PASS | Bring-up notes written below (section "Bring-up notes"). |
| F2 | CANNOT VERIFY | Needs the real transformer: turns (64 / 66), Lm, leakage measured both ways (one half shorted / all three secondary terminals tied), dot orientation, core / winding temperature at 10 / 15 A. |

## Findings (ranked, most severe first)

### F1 HEATER_I sense tapped at the Q10 source via, not at the shunt
- Severity: **should fix**
- What is wrong: the In2 track HEATER_CURRENT → R106 (U1A input) starts in the via (−12.8, −68.6) at Q10 pin 3. The
  current of Q10 then flows 12.46 mm through 0.8 mm B.Cu (≈ 6 – 7.7 mΩ) to R30 pad 1 (−11.2, −80.4), so that copper
  is inside the measurement. The swap of Q10 / Q11 (user placement 2026-11-21) moved Q10's source 12 mm away from the
  shunt; on 5.1 it was 1.7 mm away and the sense left the shunt pad directly.
- Consequence: the Q10 part of the tank current reads ≈ 2.5 – 2.9× too high. The copper also adds its +0.39 %/K TCR.
  The HEATER channel range is ±4.0 A × 4 mΩ = ±16 mV (±2.8 A after offset; NEXT_REVISION.md:102). Q10's peak current
  of ≈ 1.3 – 1.8 A at 15 – 20 A out then gives 8 – 14 mV of copper drop on top of the shunt voltage, so HEATER_I
  clips at heavy load. An over-current limit with 5.1 thresholds would trip early, possibly capping the heater
  below 15 A. The "sign of HEATER_I at each edge" capacitive-mode check (DAB_SIMULATION.md:350) still sees the sign,
  but with the wrong scale.
- Evidence: `python3 -c` over /tmp/tube_psu_review_1000/b52.json tracks of HEATER_CURRENT: In2 (−3.8, −68.3) →
  (−12.6, −68.3); via (−12.8, −68.6) 0.8 / 0.4; B.Cu 0.8 mm (−12.8, −68.6) → (−12.8, −71.0) → (−11.2, −72.6) →
  (−11.2, −80.4) = R30.1. 5.1 (b51.json): B.Cu (−11.2, −80.4) → (−11.2, −79.1), via (−11.2, −79.1), In2 → (−1.5, −69.1)
  → R106. `rv bq net HEATER_CURRENT` lists the In2 22.7 mm and both vias.
- Smallest fix: move the sense start to R30 pad 1 as on 5.1. Add a via at about (−11.2, −79.1) beside the pad with a
  short B.Cu stub to pad 1, and run the In2 lane from it to the existing lane at (−3.8, −68.3), deleting the In2
  piece (−3.8, −68.3) → (−12.6, −68.3). Keep the Q10 source current on its B.Cu trunk. Checklist 08 should
  re-check the chain afterwards.
- Confidence: high for the geometry. Medium for the size of the error: it depends on how the tank current splits
  between Q10 and C20 / the bulk return, which was not simulated. A measured HEATER_I waveform against a current probe
  on the bench would confirm it.

### F2 Firmware timing and frequency floor were tuned on the 5.1 tank; 5.2's tank differs and Lr is uncertain
- Severity: **should fix** (bring-up / firmware document; no board change)
- What is wrong: the SR uses a fixed maximum conduction time of 2.65 µs (680 cycles), measured on 5.1 (design
  document p 21). That time is the resonant half period of the 5.1 tank, T/2 = π√(L·C) ⇒ L·C(5.1) ≈ 7.1·10⁻¹³ s².
  It contradicts "220 kHz" (T/2 = 2.27 µs) unless the operating leakage is ≈ 57 µH. This independently supports the
  TR2_OPENMAGNETICS.md 1.40 × hypothesis (58.7 µH, T/2 = 2.69 µs). 5.2 changes C from "≈ 12.5 nF" (inferred, X7R
  under bias) to a fixed 13.2 nF. The 5.2 half period is:
  - L = 58.7 µH: **2.77 µs**. The 2.65 µs SR window is 0.12 µs short: body-diode tail, harmless.
  - L = 42 µH (and then the 5.1 X7R only lost ≈ 10 %, C ≈ 16.9 nF): **2.34 µs**. The window is **0.31 µs too long**.
    The SR stays on after the current reverses, Vout drives the ≈ 41 – 58 nH secondary-referred leakage backwards,
    di ≈ 6.3 V × 0.31 µs / 41 nH ≈ 48 A, which is then cut by the SR, so there is a drain overshoot / avalanche risk on
    Q1 / Q2 (60 V).
  - Frequency floor: FHA (Lm 320 µH, 13.2 nF, 6.3 V + 0.3 V drop) needs ≈ 159 kHz at 400 V and 144 kHz at 380 V with
    64 T / 58.7 µH. With the owner's **66 T** it needs ≈ 150 kHz at 400 V and 137 kHz at 380 V. That is at or below
    the design document's 150 kHz floor (p 20), consistent with the TR2 file's gain table ("380 V, 15 A not
    reachable"). With 42 µH: 165 – 180 kHz, fine. The peak-gain / ZVS boundary is 73 – 90 kHz, so lowering the floor
    to ≈ 130 kHz is still inductive.
- Evidence: arithmetic above. Design document p 20 – 21 (`rv pdf 16 22`). TR2_OPENMAGNETICS.md:33-59 (table values
  re-computed: all correct). CHANGES_5_2.md:51.
- Smallest fix: add bring-up lines to CHANGES_5_2.md (open questions) / the firmware notes:
  1. Measure leakage both ways first (TR2 file:46-48).
  2. Start with the SR window ≤ 2.2 µs and lengthen it while watching the secondary current (Rogowski as in Fig 4.3)
     to just before reversal.
  3. Allow f_min down to ≈ 130 kHz.
  4. Keep the 270 kHz start.
- Confidence: medium. The arithmetic is certain; which Lr applies is open and needs the LCR measurement.

### F3 Q14_DRAIN (Q1 drain) copper is narrower than 5.1
- Severity: **should fix** (worse than 5.1; the width rule is still met)
- What is wrong: TR2.9 / 10 / WP4 → Q1 tab is 4.48 mm on F.Cu and B.Cu only, with 12 tab vias. 5.1 had 7.7 mm on F.Cu
  and B.Cu plus pours on both inner layers, and 16 vias. Two things cause it. The inner switching-node pours were
  removed by decision 6 (README:528-533, a given). The zone's north edge moved from y −63.25 to −66.0 beside the ISO1
  T-slot bar (y −64.09; stage 13b widened the bar towards ISO1 only, so the cut predates it). Q1 is also the hotter
  SR: at the owner's 10 – 15 A, its conduction loss is ≈ 1.4 – 3 W (RDS(on) not datasheet-verified, C3) on 1.04 cm²
  per layer.
- Evidence: `rv bq neck Q14_DRAIN F.Cu -36.4 -66.08 -49.2 -68.0` = 4.48 mm (B.Cu 4.48); `rv bq51 neck …` = 7.68
  (B.Cu 7.76, In1 7.76). `rv bq xsec Q14_DRAIN F.Cu x -42 -76 -62`: −70.95 … −65.57 vs 5.1 −70.95 … −63.25.
  `rv bq net Q14_DRAIN`: 12 vias, 104 mm² × 2; 5.1 16 vias, 151 mm² × 4. Q13_DRAIN is unchanged in width (7.10 mm).
  It still meets the README 15 A rule: 2 × 9.6 A ≥ 11.8 A rms. F.Cu alone does not.
- Smallest fix:
  1. Four more 0.5 / 0.3 vias in the Q1 tab (16, as Q2 and 5.1; via-in-pad is accepted).
  2. A Q14_DRAIN pour on In2.Signal_HV between TR2.9 / 10, WP4 and the Q1 tab. It is not a GND-plane layer; the node
     swings only 0 – 13 V. Keep the 8.2 mm to the primary as `check_domains.py` demands.
  3. If more is needed, pull the north edge of the small F.Cu 6V3 zone at WP3 (y −71.2) down a little; the WP pads
     are through-hole and B.Cu / In3 carry 6V3.
- Confidence: high for the measurements. Medium for the thermal consequence (needs the BUK9Y15-60E RDS(on) at
  6.3 V and a temperature reading at 15 A).

### F4 TR2 turns 64 vs 66 not settled in the design files
- Severity: **note** (document)
- What is wrong: sheet06.py:98 and CHANGES_5_2.md:86 say 64 T ("check primary turns!"); the owner said 66 T on
  2026-11-23 (TR2_OPENMAGNETICS.md:20). 66 T lowers the output by 3 % at a given frequency (6.25 → 6.06 V at M = 1)
  and pushes the needed frequency below the 150 kHz floor at 380 – 400 V (F2).
- Smallest fix: write the counted turns of the 5.1 transformer into the sheet note and the CHANGES TR2 table, plus the
  winding build: 6 strands / litz secondary / 2 strands in parallel.
- Confidence: high that the documents disagree.

### F5 Bridge HF loop path 1.62× 5.1
- Severity: **note**
- What is wrong: the loop through Q11.2 → Q11.3 → Q10.2 → Q10.3 → C20.2 → C20.1 is 59.5 mm / 23.0 mm² vs 36.7 mm /
  20.6 mm² on 5.1 (`rv bq loop …`, `rv bq51 loop …`). The area is almost equal; the path is long because DPAK tabs are
  large and Q10's source is now far from C20. Under ZVS the turn-on edge is soft. Accept, or look at the switch-node
  ringing at bring-up.
- Confidence: medium (the pad-centre estimate, not the copper path).

### F6 TR2 interwinding insulation vs the reinforced 8.2 mm board barrier
- Severity: **note** (the construction is a given; it is the same as 5.1)
- What is wrong: the board keeps a reinforced 8.2 mm PRI ↔ HEATER distance (README:2270, stage 13d). Inside TR2 the
  litz secondary is sandwiched between enamelled AWG 30 primary portions. The TR2 file:72 finds "radial stack
  4.31 mm against a 4.2 mm window; no room for reinforced insulation as wound". The board creepage protects nothing
  if the winding insulation is only functional.
- Smallest fix: state the TR2 insulation system in the winding spec (TIW secondary, or tape layers with margin), or
  record that the heater barrier is functional inside TR2 as on 5.1. The owner decides; checklist 10 should note it.
- Confidence: medium (it rests on the model's fit and the owner's build description).

### F7 Dead time vs ZVS undocumented
- Severity: **note**
- What is wrong: the firmware LLC dead time is not in the repository. Hardware DT 100 ns (80 – 120 ns, SLUSCJ9F) is
  only a floor. ZVS needs t_dead ≥ 2·Co(tr)·400 V / I_m with I_m = 1.07 A (150 kHz) … 0.58 A (270 kHz), i.e.
  0.75 – 1.38 ns per pF of Co(tr) (A9). Co(tr) of IPD60R280P7S was not fetched; the TR2 file estimates ≈ 270 ns.
- Smallest fix: take Co(tr) from the Infineon datasheet, set the firmware dead time ≥ the 270 kHz value, and check the
  switch node for ZVS at 270 kHz light load (the worst case).
- Confidence: medium.

### F8 Small documentation inconsistencies
- Severity: **note**
- DAB_SIMULATION.md:322 still reads "4 × 4.7 nF, i.e. a split 18.8 nF" before the 3.3 nF bracket.
- NEXT_REVISION.md:64 says "Q10 (high, Si8271) / Q11 (low, IXDD609)". Both netlists have Q11 = high side (drain DC+),
  Q10 = low side.
- lib/part_map_next.csv C22 (and presumably C41 / C42 / C49) `device=12061C103KAT2A` is a stale 10 nF X7R part
  number. The LCSC / MPN columns in jlc_parts_next.csv are correct (checklist 13).
- README:59 "14 warnings": erc.rpt has 15 (the third ground_pin_not_ground is DRV3.14).
- Checklist 06 says the PRI–HEATER barrier is 8.0 mm; the board / rules are 8.2 mm since stage 13d. The board
  governs, and it passes (10.42 mm at TR2).
- Confidence: high.

### F9 ZLLS400 turn-off peak above IFPK on paper (D35 new, D33 unchanged)
- Severity: **note**
- What is wrong: (15 − 0.6) V / 3.3 Ω ≈ 4.4 A peak for a few ns, against IFPK 0.85 A (12 A for ≤ 100 µs rectangular
  pulses). This is the bench-verified 5.1 D33 network; D35 copies it on the high side.
- Confidence: medium (Rg,int of IPD60R280P7S and the UCC21520 sink resistance reduce the peak; datasheet not fetched).

### F10 Q10 / Q11 tab copper below the NEXT_REVISION 5.4 target
- Severity: **note**
- What is wrong: Q11 ≈ 0.85 cm² local DC+ copper behind a neck, Q10 1.24 cm² switch node, F.Cu only, against "≥ 2 cm²
  with thermal vias". Thermal vias are impossible under the given rules (DC+ outer only, no inner switch node).
  Losses are only 0.16 – 0.22 W per FET, so ΔT is estimated ≤ 33 K even pessimistically. Check by touch / IR at 15 A.
- Confidence: medium.

## Bring-up notes (F1 / F2 of the checklist)
1. Before power: LCR on TR2 at 100 – 200 kHz: secondary open (Lm), one secondary half shorted (expect 55 – 60 µH if the
   TR2 file is right), all three secondary terminals tied (expect 42 µH). Count the turns (64 / 66). Check the dots
   against CHANGES_5_2.md:91-97.
2. First start from a current-limited DC supply (60 – 100 V on DC+), resistive load 1 – 2 Ω on HT_6V3, SR window short
   (≤ 2.2 µs), f = 270 kHz, sweeping down. Expected: Vout ≈ V_DC/2 × 2/64 × M; HEATER_I reads about 2.5 – 3× the true
   Q10 current until F1 is fixed.
3. Wrong SR polarity shows as low Vout, hot Q1 / Q2 and supply current in the "wrong" half cycle. Fix it by swapping
   the two primary ends (CHANGES) or SYNCH_1 / SYNCH_2 in firmware.
4. Lengthen the SR window on the Rogowski / current-probe trace until the reverse spike appears, then back off. Repeat
   at 400 V; check f_min against the 6.3 V target at 380 – 420 V (F2).
5. 30 min at 10 A and 15 A: TR2 winding / core temperature (A7), Q1 / Q2 case temperature (F3), Q10 / Q11 (F10).

## Compared with 5.1
- **Equal:**
  - Topology, tank topology and gate network values; bootstrap; C20; SR pairing and polarity (A6 / E3).
  - TR2 pins; wire pads; output bank parts and positions; terminals.
  - 6V3 / HT_GND outer copper (6V3 B.Cu 22.6 mm at x −60, 5.1 22.9; HT_GND F.Cu 11.7 – 24 mm vs 13 – 25 mm).
  - Q13_DRAIN width (7.1 mm F / B). HEATER_CAP_MEAS edge distance (0.95 mm).
- **Better:**
  - C0G tank: no bias drift. Balancing resistors.
  - One isolated driver with hardware dead time and overlap blocking (5.1: Si8271 high side + non-isolated IXDD609
    low side). UVLO-held SR driver.
  - 6V3 gains an In3 plane (22.5 mm at x −60). PRI ↔ HEATER barrier 10.42 mm with 8.2 mm rules.
- **Worse:**
  - HEATER_I Kelvin connection (F1).
  - Q14_DRAIN copper / vias (F3), and Q13_DRAIN loses its inner pours (decision 6).
  - Gate loops 2.2 – 2.5× longer (README-accepted, D4); HF loop path 1.6× (F5).
  - Q10 / Q11 standard-diode P7 instead of fast-diode CFD7 (a given; A8 analysis: capacitive mode only at start-up /
    short circuit below fr).

## Could not verify
- **Datasheets not fetchable in this session.** Infineon IPD60R280P7S and IPA60R280CFD7 (JS-rendered product pages,
  LCSC PDF empty, datasheets.com 403); Nexperia BUK9Y15-60E (assets.nexperia.com 403, mirrors 403 / DNS); IHHEC
  C1206N332J631T (LCSC PDF link returns HTML, no tan δ / AC rating); Rubycon 10ZLH1500MEFCT78X20 and Panasonic
  EEU-FR1A152L; Samsung CL31A106KBHNNNE; S1M; IXYS IXDD604 (DFN pinout, UVLO).
- **Fetched and used:** TI UCC21520 SLUSCJ9F rev. F; TI UCC27524A SLUSBP4C rev. C; Diodes ZLLS400 (absolute maximum /
  VF tables); LCSC C536813 and JLC C7091976 parameter tables (distributor values, no conditions; used only as
  flagged estimates).
- **Items affected:** A2 (current / heating limit), A8, A9 (Co(tr)), B6 (RthJA, RDS(on)(T)), C3 (RDS(on) at 5 – 6.3 V),
  C4 (ripple ratings), the IXDD604 comparison in C2 / E3, the S1M recovery number in B4.
- **Needs the real transformer or the bench:** primary turns, Lm, leakage measured both ways, dot orientation,
  winding / core temperature at 10 / 15 A (A5, A7, F2); the firmware LLC dead time, SR window and frequency limits
  (not in the repository).
- **Terminal rating:** HT_6V3 / HT_GND are consigned faston terminals with no part number.

## Outside scope
- Checklist 08: the HEATER_I amplifier range and offset with the F1 copper in series (re-check after the fix); the
  R106 / U1A input filter.
- Checklist 10: TR2 internal insulation vs the reinforced 8.2 mm board barrier (F6). HEATER_CAP_MEAS
  (≈ 200 ± 165 V) pour is 0.95 mm from the top board edge (as on 5.1).
- Checklist 13: lib/part_map_next.csv `device` column of C22 / C41 / C42 / C49 is stale (12061C103KAT2A). Datasheet
  ratings of C105987 (tan δ) and C432399 (ripple) still to be read.
- Checklist 11: switch-node / HF loop comparison with 5.1 (F5) and the Q14_DRAIN width (F3) appear in its scope too.
