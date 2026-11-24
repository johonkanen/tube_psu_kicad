# Findings: 04 j2_uart_supplies  (reviewer: Claude Opus 5.5, 2026-11-24, commit 3e1e31e)

## Summary
The electrical part of this section is ready to order. The J2 pin map matches the netlist, J2_PINOUT.md and the
control card's own netlist. V4, REF1, U9 and U11 are wired to their datasheet pinouts. The REF1 pinout question is
settled: the SOT-23_Proteus pad renumbering puts lead 1 on IN, lead 2 on OUT and lead 3 on GND (same pads as 5.1).
The UART pair has a GND plane under it for its whole run, except at its own vias. It stays ≥ 14 mm from every DAB
primary net, which is better than 5.1 on the point that disturbed the 5.1 link.
**No item is a blocker as the files stand**, but two things should be settled before ordering:
- (F1) the J2 part: C69941 is a male header whose drawing asks for Ø0.60 mm holes, but the footprint has 0.5 mm holes.
  Its gender against the card's male right-angle header is also unresolved.
- (F2) the CA-IS3721HW certificates: VDE / UL / CQC / TÜV are still listed as "pending" for a barrier that the user can
  touch.

The rest are notes.

## Checklist results
| Item | Verdict | Evidence |
|---|---|---|
| A1 | PASS | `rv sch ref J2` / `rv sch sheet 4`: all 50 pins agree with `kicad_next/J2_PINOUT.md` "All pins" (e.g. 18 DAB_DIS, 24 RX, 26 TX, 37/39/40/46/48/50 GND, 38 DHB_I_MEAS, 41 DC_LINK_MEAS, 42 PFC_I1_MEAS, 43 AUX_MEAS, 44 PFC_I2_MEAS, 45 HEATER_I_MEAS, 47 VAC_MEAS, 49 5V_MEAS; 12 free pins as listed). |
| A2 | PASS | `rv sch cmp51 4`: J2 changes only at pins 18 (F16 → DAB_DIS), 37 (DHB_I → GND), 38 (CUK_CAP_MEAS_RAW → DHB_I_MEAS), 39 (HEATER_CAP_AD_MEAS → GND), 40 (AUX → GND), 42 (ADA4 → PFC_I1), 43 (PFC_I1 → AUX), 46/48/50 (→ GND), 49 (ADB0 → 5V_MEAS). All are covered by CHANGES_5_2.md:132 (4b) and :107 (3.3). 4b also records that the single-pin nets CUK_CAP_MEAS_RAW / HEATER_CAP_AD_MEAS are gone. |
| A3 | PASS | Card files read (`~/dev/ti60f225_tube_psu_control_card/reference/power_board_header.csv`, `mux_assignment.csv`, `pin_assignment.csv`), and the card netlist was exported from `hardware/control_card.kicad_sch` into the scratchpad. Card J1 pin n = power-board pin n±1, odd and even swapped (csv `card_pin,power_board_pin`; card J1-1 = +5V ↔ J2-2). Results: J2-24 ↔ card J1-23 = net RX → U1.A12 (HVIO, `RX,in`); J2-26 ↔ J1-25 = TX → U1.B5 (`TX,out`). The six grounded pins 37/39/40/46/48/50 ↔ card ADB6/ADB5/ADA5/ADA2/ADA1/ADA0 are TMUX1308 inputs only (U13.5, U13.4, U10.2, U10.13, U10.12, U10.5), so no card output drives a grounded pin. The PWM / SPI / relay pins come from SN74AVC4T774 B-ports; HT_SDATA / CUK_SDATA go straight to FPGA inputs. The card's "power_board_load" column still describes the 5.1 ADC use; the card / firmware map has to be updated (CHANGES 4b says so). See F3. |
| A4 | PASS | J2-18 ↔ card J1-17 = net `J1_P17` → FPGA ball **R3** (GPIOL_01, HVIO bank BL, 3.3 V), with no translator. Ti60 HVIO weak pull-up is 25 / 42 / 67 kΩ min / typ / max at 3.3 V (Efinix Ti60 DS, Table 15, https://www.efinixinc.com/docs-html/dsti60/topics/ref_dc_switch_ti60.html), and is on during reset / configuration (card `docs/ti60_requirements.md:113`). Worst case against R129 10 k: 3.3 × 10 / (10 + 25) = **0.94 V**. UCC21520 VENH min is **1.2 V** (SLUSCJ9F, Elec. Char., VINAH/VENH 1.2 / 1.8 / 2.0 V), so the drivers stay enabled (typical 0.63 V). ISO2 VI_C is also on DAB_DIS; CA-IS376x VIT+ ≥ 1.4 V, so it stays low too. Driven low: enabled. Driven 3.3 V high: DRV5 DISABLE high (both primary outputs low, SLUSCJ9F pin 5) and ISO2 C → DAB_DIS_SEC → DRV6 off, so both DAB drivers are off. Margin 0.26 V: a note, not a finding. |
| A5 | PASS | Board pull-downs to GND: R77 (EPWM6A), R78 (EPWM5A), R73 (PRI_DHB_HI), R74 (B12), R69 (PFC_PWM2), R71 (PFC_PWM1), R32 (GPIO_BYPASS_RLY), R129 (DAB_DIS) (`rv sch ref`). The card holds all translator outputs Hi-Z while unconfigured (XLAT_OE_N with R67 10 k to +1V8 on U19–U22 ~OE). The card also has R40 / R41 10 k pull-downs on EPWM2A / EPWM2B (card netlist). SYNCH_1/2, $HT_CS, HT_CLK, $CUK_CS, CUK_CLK go straight into ISO1 / ISO2 inputs with no pull-down on either board (the same as 5.1: `rv sch51 net EPWM2A SYNCH_1` shows only ISO / J2). CA-IS3761L truth table: "Open" input → default output **low** (CA-IS376x datasheet, section 8.2, Table 8-1, LCSC C528659). TX (A1) floating → B1 default high (CA-IS372x rev C, truth table), so RXD idles high. |
| A6 | PASS | Each analog pin is fed through ≤ 100 Ω from an op-amp output (`rv sch net`): 38 R42 33 Ω ← U1.7; 45 R35 33 Ω ← U1.1; 42 R96 100 Ω ← U4.1 + C88 100 pF; 44 R61 100 Ω ← U4.7 + C77 100 pF; 47 R65 100 Ω ← U8.1; 41 R2 100 Ω ← U6.1; 43 R132 100 Ω ← U10.1; 49 R135 100 Ω ← U10.7. C26 / C10 are "na" (DNP). U1, U4, U6, U8 and U10 all have V+ = +3V3 and V− = GND (`rv sch net +3V3`), so no output can leave 0 … 3.3 V. |
| A7 | PASS | J2-2 5V: F.Cu 1.016 mm track from the pin (34.41, −22.16) → (35.44, −22.16) → (37.1, −20.5) → (37.1, −11.1), plus the In3 5V pour (zone S2_In3_5V_1) at the pin (board JSON). C69941 rating **1.5 A** per contact (LCSC datasheet C69941, BOOMELE drawing "1.27-2xNA-H1.5MM", item 1-1). The card current is not stated in the card repository. **Assumption**: Ti60 card ≈ 1–1.5 W from 5 V (0.95 / 1.8 / 3.3 V bucks), i.e. ≤ 0.3 A, which is 20 % of the rating (≤ 70 %). Even 1 A would be 67 %. Returns go through pins 1, 35, 36 plus the six grounded analog pins. |
| A8 | CANNOT VERIFY | Same footprint, position and pin 1 as 5.1: `rv bq fp J2` / `rv bq51 fp J2` both give (33.135, −22.156), rot 0, pad 1 GND, pad 2 5V, drill **0.5 mm**. C69941 is a **male** straight header: brass pins 0.40 mm (drawn square), 3.00 mm above a 1.5 mm insulator, **recommended PCB hole Ø0.60**. The card's J1 is a **male right-angle** header (`control_card.pretty/PinHeader_2x25_P1.27mm_Horizontal_U25`: "Through hole angled pin header … 4.0mm pin length"), hand-soldered by the user. Two male headers cannot mate, so either J2 must be a 1.27 mm female socket, or the card's angled pins go straight into the J2 holes (then J2 must not be fitted). The part fitted on the bench 5.1 board is not recorded in the repository. See F1. Measurement to take: the 5.1 board's J2 (gender, pin cross-section, height) and the card's mating plan. |
| B1 | PASS | Max currents at the worst listed supply: U1 + U4 LMH6643, 4 × 4.0 mA (SNOS966Q, IS per channel max 4.00 mA) = 16 mA; U6, U8, U9 TLV316, 3 × 0.575 mA (TLV316 DS, IQ max 575 µA) = 1.7 mA; U10 TLV9062, 2 × 0.75 mA (SBOS839N, IQ max 750 µA) = 1.5 mA; REF1 5 µA + divider 2.5 V / 2.96 kΩ = 0.85 mA; ISO1 + ISO2 side A, 2 × 8.5 mA (CA-IS3761 IDDA max, 5 V DC worst row) = 17 mA; U11 side A 3.2 mA (CA-IS372x rev C 7.9.2, 10 Mbps max at 3.3 V) + 0.5 mA RX line charging; op-amp output loads and bias ≈ 2.6 mA. **Total ≈ 44 mA = 22 % of the 200 mA TPS73033** (SBVS054K, ROC IOUT 200 mA). Pdiss = 1.7 V × 44 mA = 75 mW; RθJA 182.3 °C/W (DBV-5) → +14 °C, so Tj ≈ 84 °C at 70 °C ambient (< 125 °C). |
| B2 | FAIL (note) | Pinout PASS: TPS730 DBV-5 fixed is 1 IN, 2 GND, 3 EN, 4 NC/NR, 5 OUT (SBVS054K, Fig. 4-1). Pads of `SOT-23-5_Proteus` in standard order (library pads 1–3 at x −1.18, 4–5 at x +1.20, same as KiCad SOT-23-5) carry 5V / GND / 5V / NR / +3V3 (`rv bq fp V4`). CIN C75 1 µF ≥ 1 µF. COUT: C68 1 µF local (2.5 mm), plus C62 2.2 µF and C76 1 µF through the +3V3 net, gives 4.2 µF ≥ 2.2 µF. **C74 100 nF on NR is above the recommended CNR range 0 … 10 nF** (SBVS054K 5.3 ROC, note 3: legacy chip only; the new chip has no NR pin, NC). This is the same as 5.1 (C74 unchanged in `rv sch cmp51 4`, same position in `rv bq51 fp C74`), so it is a note: slower soft start, no stability issue. |
| C1 | PASS | REF33xx DBZ: **1 IN, 2 OUT, 3 GND** (SBOS392I, Table 5-1, https://www.ti.com/lit/ds/sbos392d/sbos392d.pdf, fetched as rev I April 2026). Symbol pins: 1 GND, 2 VIN = +3V3, 3 VOUT. Footprint `lib/tube_psu.pretty/SOT-23_Proteus.kicad_mod` descr: "pad 1 = JEDEC pin 3 (single side), pad 2 = JEDEC pin 1, pad 3 = JEDEC pin 2". Pad positions confirm it: pad 1 (+0.9575, 0) is alone on one side; pads 2 (−0.9475, −0.94) and 3 (−0.9475, +0.94) are KiCad SOT-23 pin 1 and pin 2. On the board (B.Cu, y-mirrored), seen from the top, pad 2 → pad 3 → pad 1 runs clockwise, which is correct for a bottom part with leads 1-2-3. So **lead 1 = +3V3 (IN), lead 2 = VOUT (OUT), lead 3 = GND**. The pads are identical to 5.1 (`rv bq51 fp REF1`; ISL21010 has the same 1 IN / 2 OUT / 3 GND). VIN min VOUT + 0.2 = 2.7 V < 3.23 V. C69 100 nF vs "Capacitive load 0.1 … 10 µF" (SBOS392I Elec. Char.): exactly at the minimum (note, see F5). Q9 (same footprint) checked too: see "Outside scope". |
| C2 | PASS | 0603WAF parts = 1 % (`rv sch part R110,R3`). Ratio 1.96 / 2.96 = 0.6622; ratio error ±(1.00 / 2.96) × 2 % = ±0.68 %. REF3325 ±0.15 % initial. R131 drop ≈ 0.6 mA × 22 Ω = 13 mV (CHANGES 4.1). Bias ≈ 1.655 V × (1 ± 0.83 %) − 13 mV ± Vos(U9) ≈ 1.63 … 1.66 V. This exceeds ±1 % at the edge, but the offset is common to all channels and removed by the firmware zero calibration (CHANGES 4.1, NR 4.11). |
| C3 | PASS | `rv sch sheet 4`: U9 pin 1 = pin 4 = Net-(U9--) = R131 pin 1; R131 pin 2 = +1V65_BIAS. No capacitor on Net-(U9--). Capacitance on +1V65_BIAS: C48 100 n + C106 20 p + C107 20 p + C122 12 p + C123 5.6 p + C126 1 n = 101.06 nF, the ≈ 100 nF of FINDINGS 11.3 (vendor model PM 84°). TLV316 DBV pinout 1 OUT, 2 V−, 3 +IN, 4 −IN, 5 V+ (TLV316 DS, Pin Functions) = netlist = KiCad SOT-23-5 pads (`rv bq fp U9`). |
| C4 | PASS | `rv bq net +1V65_BIAS`: one net to U1 / U4 / U8 resistors; In2 / In3 legs lie between the In1 / In4 GND planes. Via (13.0, −44.076) is 0.164 mm from $HT_CS and SYNCH_2 (In2) (`rv bq near +1V65_BIAS --within 0.5`). Estimate: ≈ 50 fF × 3.3 V / 2 ns = 80 µA into ≈ 50 Ω (the 25 mm track inductance to C48 dominates at the edge), i.e. a ≈ 4 mV ns-wide spike. The op-amp + inputs see the node only through R103 33 k / R105 15 k / R60, R100 6.8 k with 5.6–20 pF (τ ≥ 136 ns), so it is negligible. There is no local 100 nF at U1 / U4 (only C122 / C123 / C106 / C107 pF caps): acceptable for this reason. |
| D1 | PASS | CA-IS372x rev C (Chinese, Chipanalog, LCSC C5337993: https://datasheet.lcsc.com/datasheet/pdf/7a41728767d8cfd8a0e142f700d570d7.pdf), Fig. 6-1 / Table 6-1: 1 GNDA, 3 VDDA, 4 VI1 (A in), 5 VO2 (A out, 3721), 7 GNDA, 9 GNDB, 12 VI2 (B in, 3721), 13 VO1 (B out), 14 VDDB, 16 GNDB, 2/6/8/10/11/15 NC ("may float"). Netlist identical (`rv sch ref U11`). Table 4-1: CA-IS3721**HW** = 1 + 1 channels, fail-safe **High**, 5.0 kVrms, WB SOIC-16. |
| D2 | PASS | Netlist: J2-26 TX → U11.4 A1 → U11.13 B1 → R137 → J4-4 UART_RXD; J4-2 UART_TXD → R136 → U11.12 B2 → U11.5 A2 → J2-24 RX. **Far end: its UART TX output to J4-2, its RX input to J4-4, its 3.3 V (2.375 … 5.5 V) to J4-6, ground to J4-1/3/5.** |
| D3 | PASS | At 3.3 V (rev C 7.10.2): DR 150 Mbps (≥ 24); tPLH/tPHL 13 ns max (latency only); **PWD 4.5 ns max = 5.4 % of 83.3 ns**; tsk(pp) 4.5 ns; tr / tf 4 ns max; output Zo ≈ 50 Ω ± 40 %. RXD out: (Zo ≤ 70 Ω + R137 47 Ω) × (40 pF cable [assumed 30–40 cm ribbon] + 10 pF far-end input) = 117 Ω × 50 pF = 5.9 ns = 7 % of the bit (≤ 10 %). A longer cable acts as a source-terminated line (≈ 97 Ω source into a ≈ 100 Ω ribbon pair), not as an RC. TXD in: 47 Ω × (2 pF CI + ≈ 2 pF track) = 0.2 ns. Primary side: 130 mm stripline ≈ 15 pF (0.92 ns / 61 Ω) + 2 pF; RX driven by U11 A2: 70 Ω × 25 pF = 1.75 ns (2 %). TX driven by the FPGA (≈ 40 Ω) gives 0.7 ns. |
| D4 | PASS | VDD2 = UART_3V3 with C135 100 nF (datasheet test circuit CBP 0.1 … 1 µF, rev C note 4 of Fig. 8-x). Side-2 current 3.2 mA max at 10 Mbps (7.9.2) + ≈ 1 mA cable charging = **≈ 4.2 mA from the far end**. Cable unplugged → A2 (RX) = default high (truth table "PD PU X Default", H part). Board off → VDDA PD → B1 (RXD) = default high. Abs max Vin at Bx: −0.5 … VDDB + 0.5 V (rev C 7.1), with no input clamp current given. In the intended wiring the far end's TXD driver and J4-6 come from the same 3.3 V rail, so B2 never sees TXD high with VDD2 = 0. The datasheet warns (truth table note 2) that a strongly driven input can back-power a floating VDD. A cable without pin 6 would put ≈ (3.3 − 0.5) / 47 Ω ≈ 60 mA into B2's ESD structure, so a bring-up note says "pin 6 must be connected" (F6). |
| D5 | PASS (note) | J4 has R136 / R137 47 Ω only, no TVS. CA-IS372x ESD HBM ±4 kV, CDM ±1 kV (rev C 7.2). The datasheet does not demand external protection. 5.1 had none either. Note only. |
| D6 | CANNOT VERIFY | Rev C 7.6: CLR 8 mm, CPG 8 mm, DTI 14 µm, CTI > 600 V, material group I, **VIOWM 1000 Vrms**, VIORM 1414 Vpk, **VIOTM 7070 Vpk**, VIOSM 6250 Vpk (production test 1.6 × = 10 kV), VISO 5000 Vrms. These meet the 318 Vrms reinforced need on paper, but the datasheet does **not** name the insulation "reinforced". **7.7 Safety certifications: VDE, CSA, UL, CQC, TÜV all "申请中" (application pending).** See F2. |
| D7 | PASS | `rv bq dist @UART @PRI`: F.Cu 7.250 mm (U11 pad rows across the slot only; `near` lists only U11 pads below 8.0 mm); In1 / In4 **8.054 mm** (12.25 / 20.30, y −78.76; checklist 8.05 confirmed); In2 / In3 9.109; B.Cu 8.234 mm. Nearest F.Cu primary other than U11: DC+ 8.014 mm from J4 pad 6. U11 slot (`rv bq slots`): x −0.75 … 0.75, y −85.25 … −70.75, **1.5 mm wide (stage 13b; the checklist's 1.0 mm is out of date)**. Path round the slot: 2 × √(3.625² + 2.505²) ≈ 8.8 mm (README 13b: 8.87 mm) ≥ 8.0. @UART ↔ @SEC ≥ 42.25 mm; ↔ @HEATER ≥ 38.6 mm. H2 (NPTH, no copper since stage 13c): hole wall ↔ UART copper 1.63 mm (B.Cu bus), 2.0 mm (F.Cu), 2.18 mm (inner) = 0.13 / 0.50 / 0.68 mm from a 6 mm head, below the 1.0 mm rule. README 13c and fab/README.md:214 require **insulating hardware at H2**: documented, a note (F7). |
| D8 | PASS | `rv bq near @UART --within 8.5 --other-domain`: only U11 pads (7.25), DC+ F.Cu 8.014, GND In1 / In4 8.054, DHB_CAP B.Cu 8.234. `rv bq xsec GND In1.GND y -80 0 25` and the same on In4: GND only from x 20.305. 15V / 5V / +3V3 on In3 at y −80: 0 pieces. No primary copper inside x ≈ 0.75 … 20.3 on any layer. |
| D9 | FAIL (note) | `rv bq net …`: R136 pad 1 is 2.33 mm and R137 2.13 mm from U11 pins 12 / 13; C135 pads are 2.41 / 2.40 mm from pins 14 / 16 (≤ 5 / ≤ 3 mm: PASS). Ground within ≈ 1 mm: RXD (3.7 mm F.Cu) ends between J4 pads 3 and 5 (pad 5 edge 0.8 mm from the track): ok. TXD (12.27 mm F.Cu) has the B.Cu ISO_UART_GND bus under it (x 10.05 / 10.2) only from y −80.2 onward. Its first ≈ 5.6 mm (R136 → x 7.625, y −77.2 … −79.6 → diagonal) has the nearest ground at the B.Cu leg x 6.25: 1.4 mm lateral + 1.5 mm through the board. The criterion is missed for 5.6 mm. Electrically small (5.6 mm ≈ 40 ps, loop ≈ 10 mm²), so a note (F8). |
| E1 | PASS | `rv bq net TX RX`: 0.152 mm on In3 / B.Cu (0.2 mm F.Cu stubs at U11); TX 1.50 + 81.50 + 48.43 = **131.43 mm**, RX 1.50 + 82.03 + 45.14 = **128.67 mm** (README 12: 131.44 / 128.67). `rv bq dist TX RX`: In3 0.434 mm at the via pair (−5.0 / −6.07, −57.5) (README: 0.43–0.57 at vias). The 0.465 mm on the other layers is the J2 pad-to-pad gap (34.35, −7.3/−7.8), fixed by the header. |
| E2 | PASS | `rv bq dist RX AC1 --layer In3` **0.983 mm** (AC1 pad ring at (−4.73, −33.10)); `rv bq dist TX PFC_DRAIN_1 --layer In3` **1.463 mm**; RX ↔ PFC_DRAIN_1 2.223 mm; TX ↔ AC1 1.743 mm. All ≥ 0.5 mm (inner functional rule). Nearer, but low dv/dt: Net-(DRV1-OUTL) and PFC_PWM1 via barrels 0.353 / 0.391 mm from TX (15 V / ≈ 10 ns: 15 fF × 1.5 V/ns = 23 µA, 1 mV). Coupling from L2 pin 2 (In3 ring r 1.3 mm, coplanar, In4 GND 0.2 mm below, In1 0.418 mm above): stripline C ≈ 1.16 pF/cm; mutual fraction ≈ 1 / (1 + (2.0 / 0.2)²) ≈ 1 % over ≈ 4 mm, giving ≈ 5 fF. Upper bound 30 fF × 400 V / 15 ns = 0.8 mA. Into the FPGA driver (≈ 50 Ω, the line is lumped at 15 ns) that is **≈ 40 mV (≤ 70 mV for 50 fF) = 1–2 % of 3.3 V**. That is far below the U11 input hysteresis (0.30 V min, VIT+ ≥ 1.4 V, VIT− ≤ 1.4 V, rev C 7.8.2) and the FPGA's 0.8 / 2.1 V levels. RX near AC1: AC1 moves at line frequency (X-cap filtered), negligible. B.Cu part: heater nets HEATER_LOW_DRV 2.1 mm, Net-(D33-K) 2.1 mm, Net-(D11-K) (bootstrap, rides the heater switch node) 2.36 mm, coplanar under In4: fraction ≈ 4 % over ≈ 2 mm gives < 1 fF, negligible. |
| E3 | PASS | Own sampling (board JSON + shapely, plane shrunk by the half track width, 0.1 mm steps): TX In3 81.50 mm, 80.50 covered by In4 GND; B.Cu 48.44 mm, 46.08 covered by In4. RX In3 82.03 / 81.03; B.Cu 45.14 / 42.86. **Every uncovered piece is ≤ 0.7 mm at the pair's own vias / antipads (−5.0…−6.4, −57.2…−57.9), (45.3…46.1, −27.1…−28.4), at J2 pads 24 / 26 and at the U11 fan-out vias.** In1 GND also covers 80.44 / 80.97 mm of the In3 runs. `rv bq xsec GND In4.GND x -8.5 -56 -34`: 22.0 mm solid; `y -34.5 -9 6`: 15.0 mm solid; `y -32.5 5 36`: gap at x 8.97–10.73 = the DRV1-OUTL / PFC_PWM1 via antipads, which are not under the pair (sampling above). |
| E4 | PASS | `rv bq xsec PFC_DRAIN_1 F.Cu y -34.5 -9 6`: x −3.881 … 5.161 (9.04 mm); `rv bq xsec GND In1.GND y -34.5 -9 6`: −9 … 6 solid. Plan-view overlap (own script): PFC_DRAIN_1 F.Cu pour over 9.04 mm of TX / 9.07 mm of RX (In1 between); DC+ F.Cu pour over 37.5 / 34.0 mm (In1, and for the B.Cu part also In4, between); GATE1 B.Cu crosses 0.54 mm (TX) / 2.39 mm (RX) where the pair is on In3 (In4 between); Net-(DRV1-OUTL) B.Cu 0.78 mm over TX (In4 between). No HV pour or gate track overlaps the pair without a GND plane in between. |
| E5 | PASS | In3: w 0.152, t 0.0152, In4 0.2 mm below (core Dk 4.6), In1 0.418 mm above (README Stackup). IPC-2141 asymmetric stripline: 80/√4.5 × ln(1.9 × 0.4152 / 0.1368) × (1 − 0.2 / (4 × 0.633)) ≈ **61 Ω**. B.Cu microstrip h 0.428: ≈ 95–100 Ω. Delay ≈ 7 ps/mm → **≈ 0.9 ns** one way. With 2.5–4 ns edges (U11 tr / tf; FPGA HVIO similar) the line is not strictly "< tr/6", but both drivers are near-matched (≈ 40–70 Ω into 61–100 Ω), so it settles in a few round trips (< 5 ns ≪ 83 ns). No termination needed. Crosstalk at 0.76 mm centre spacing: In3 NEXT ≈ ¼ / (1 + (0.76 / 0.2)²) ≈ 1.6 % (53 mV); B.Cu ≈ ¼ / (1 + (0.76 / 0.43)²) ≈ 6 % (0.2 V). Both are below the 0.3 V hysteresis / 1.2 V CMOS margin. |
| F1 | CANNOT VERIFY | `rv sch bom 4` / `rv sch part`: still open: **J4 C492405** stock and price not read (drawing fetched: XFCN PZ254V-11-06P, male 2.54 mm, 3 A, 500 VAC). **J2 C69941** gender / height / hole fit (F1). **U11** reinforced certificate (F2). REF1 changed part: checked here (C1, PASS; stock 13320 on 2026-11-18). |
| F2 | FAIL (note) | Probe points: +3V3 at C62 (20.1, −1.8) / C68 (35.0, −27.2), +1V65_BIAS at C48 (31.9, −30.8), all 0603 on B.Cu, reachable from below with the card fitted. Loop-back test: jumper J4-2 ↔ J4-4 with 3.3 V on J4-6 and GND on J4-1. No silkscreen: no pin-1 mark on J4 / J2 (given, bring-up note). **Stale text**: kicad_next/README.md:2328 ("4-pin header GND / 3V3 / TXD / RXD"), NEXT_REVISION_PLAN.md:102 ("4-pin header (GND / 3V3 …)"), NEXT_REVISION.md:83 (3b.3 "4-wire cable"), NEXT_REVISION.md:84 (3b.5 "never connect a non-isolated USB-UART to J4 while on mains", true only for 5.1 and not labelled so), tools/next/sheets/sheet04.py:5 docstring "J4 (RX / TX)". No document says J4 is on primary ground in 5.2. See F4. |

Counts: **PASS 24, FAIL 3 (all notes: B2, D9, F2), CANNOT VERIFY 3 (A8, D6, F1).**

## Findings (ranked, most severe first)

### F1 J2 part C69941 may not fit the 0.5 mm holes, and its gender against the card is unresolved
- Severity: **should fix** before ordering. It becomes a **blocker for ordering** if the card's angled pins are meant
  to plug into J2, because JLC fits J2: it is in `kicad_next/fab/tube_psu_5_2_bom.csv` and fab/README.md:161.
- What is wrong: the footprint `tube_psu:PinHeader_2x25_P1.27mm_Vertical_Proteus` has **0.5 mm** holes. The ordered
  BOOMELE C69941 has 0.40 mm (drawn square) pins, whose diagonal is 0.57 mm, and its drawing calls for **Ø0.60 mm**
  PCB holes. The card's J1 is a male right-angle 2×25 header, and C69941 is a male header, so they cannot mate unless
  one of them is a socket or the card is soldered straight into the J2 holes.
- Evidence: `rv bq fp J2` (drill 0.5); C69941 drawing (LCSC
  https://datasheet.lcsc.com/datasheet/pdf/56620d6fdc9613c4ee0c075be8ccf01e.pdf: "?0.40" pin, "ø0.60" P.C.B layout,
  1.5 A); card `hardware/lib/control_card.pretty/PinHeader_2x25_P1.27mm_Horizontal_U25.kicad_mod` descr (angled pin
  header, 4.0 mm pins); card `docs/manufacturing_checklist.md` §5 "J1 position, pitch, pin 1 and orientation match the
  power board – check"; lib/jlc_parts_next.csv review "J2 generic header: check gender / height".
- Smallest fix: look at how the 5.1 card mates with the 5.1 board. Then either take a 1.27 mm 2×25 **female** socket
  whose pin fits a 0.5 mm finished hole, or leave J2 unfitted (status `dnp`) if the card is soldered straight in.
  If a male header stays, choose one with ≤ 0.35 mm pins or widen the drill to 0.6 mm (pad 0.812 leaves a
  0.106 mm ring; JLC min 0.15 mm, so the pad has to grow too).
- Confidence: medium. High on the numbers (hole, drawing); unknown how 5.1 was actually built. Raised by one look at
  the 5.1 board.

### F2 CA-IS3721HW safety certificates "pending" for a user-accessible barrier
- Severity: **should fix** (a document / qualification gap, not a layout fault).
- What is wrong: U11 is the only barrier between the mains-referenced primary and the J4 cable, which the user can
  touch. The fetched datasheet lists VDE 0884-11, CSA, UL 1577, CQC and TÜV all as "申请中" (pending). It gives
  VIOWM 1000 Vrms, VIOTM 7070 Vpk, VIOSM 6250 Vpk, VISO 5 kVrms and 8 / 8 mm CLR / CPG, but never calls the insulation
  "reinforced".
- Evidence: CA-IS371x/2x datasheet rev C, sections 7.6 and 7.7 (LCSC C5337993 link above). CHANGES_5_2.md "Open
  questions" 2; lib/jlc_parts_next.csv U11 review "reinforced rating to confirm".
- Smallest fix: get Chipanalog's current VDE / UL certificate numbers for CA-IS3721HW and note them in CHANGES. If none
  exists, record the owner's acceptance. The certified fallback is the Si8621ED-B-IS (default high, same pinout,
  consigned).
- Confidence: high that the datasheet says pending. A newer English datasheet or certificate may exist (not found).

### F3 The DAB_DIS card pin is mis-named in the documents; the card map still shows 5.1 ADC use
- Severity: **should fix** (the documents will mislead the firmware / card update).
- What is wrong: CHANGES_5_2.md:107 (3.3) says J2-18 is "ball F16 on the card", Open question 4 says "card pin D15",
  and J2_PINOUT.md says F16. In the card netlist, J2-18 is card J1-17 = net `J1_P17` → FPGA ball **R3** (HVIO, bank BL),
  listed `out` in pin_assignment.csv, and power_board_header.csv calls it "spare". The csv's "power_board_load" column
  also still shows the 5.1 analog use (pin 37 DHB_I_MEAS, 40 AUX_MEAS, 43 PFC_I1_MEAS, 39 heater_cap). Electrically
  the board is safe (A4).
- Evidence: card netlist export (J1 pin 17 → U1.R3), `power_board_header.csv` rows `17,18,,spare,,D15` and
  `37,38,ADA6…`, CHANGES 3.3 / Open question 4.
- Smallest fix: one line in CHANGES / J2_PINOUT: "J2-18 = card J1-17 = Ti60 R3 (J1_P17, direct HVIO, weak pull-up
  25–67 kΩ during configuration)". Update the card's power_board_header.csv to DAB_DIS and to the 5.2 ADC map of
  CHANGES 4b.
- Confidence: high.

### F4 Stale J4 / UART text
- Severity: **note**.
- What is wrong: four documents still describe the 1×4 header or the non-isolated 5.1 warning (F2 row). NEXT_REVISION
  3b.5 should say that it applies to 5.1. On 5.2 a non-isolated USB-UART on J4 is acceptable through U11, with the
  certificate caveat of F2.
- Smallest fix: edit kicad_next/README.md:2328, NEXT_REVISION_PLAN.md:102, NEXT_REVISION.md:83–84 and the sheet04.py
  docstring.
- Confidence: high.

### F5 REF1 load capacitor at the datasheet minimum
- Severity: **note**.
- What is wrong: C69 100 nF on REF3325 OUT, against the allowed load capacitance 0.1 … 10 µF (SBOS392I). An X7R 0603
  at −10 % tolerance falls below the minimum. U9's input is high impedance, so a 1 µF part would remove the doubt
  with no other change.
- Smallest fix: C69 → 1 µF 0603 (C15849, already used for C68 / C76).
- Confidence: medium (the datasheet gives a range, not a stability plot below 0.1 µF).

### F6 J4 pin 6 must come from the far end's I/O rail
- Severity: **note** (bring-up / cable documentation).
- What is wrong: U11 B2 is rated Vin ≤ VDDB + 0.5 V. A cable without pin 6, or a far end that powers pin 6 from another
  rail than its TXD driver, drives ≈ 60 mA through R136 into B2's ESD diode and back-powers VDDB (datasheet truth
  table note 2).
- Smallest fix: a sentence in the J4 note of sheet 4 / CHANGES 3b.2: "pin 6 must be the far end's 3.3 V I/O supply;
  always connect it".
- Confidence: high on the rating, low on the probability.

### F7 H2 needs insulating hardware (documented)
- Severity: **note**.
- Evidence: UART copper is 0.13 mm (B.Cu) from a 6 mm head; fab/README.md:214 and README 13c say so. Contact would only
  bond ISO_UART_GND (the far end's ground, normally earth) to chassis: a functional, not a safety, issue.

### F8 TXD on the island has no near ground for 5.6 mm; TPS730 NR capacitor above the recommendation
- Severity: **note** (both).
- D9 (see table) and B2 (C74 100 nF > 10 nF recommended, identical to 5.1).

## Compared with 5.1
- **Better:**
  - The UART is isolated (reinforced on paper, F2). The cable ground is no longer primary GND, so DAB-generated
    primary ground bounce no longer appears in the cable reference.
  - 5.1 ran TX / RX 30 mm on B.Cu with only 10.4 / 12.0 mm to the DAB switch node (`rv bq51 dist RX DHB_HI_SOURCE`
    10.35 mm F.Cu). 5.2 keeps ≥ 14.1 mm to DHB_HI_SOURCE, ≥ 13.5 mm to Q19 gate and ≥ 14.6 mm to Q7 gate, with a GND
    plane adjacent on > 98 % of the run.
  - 0.6 mm TX ↔ RX spacing, a ground pin beside each signal at J4, 47 Ω series on the cable side, and default-high
    idle on both outputs.
  - +1V65_BIAS is buffered (U9).
  - The REF1 part is now the intended 2.5 V reference (5.1 had the 1.5 V ISL21010CFH315).
- **Equal:** V4 circuit, values and positions (C62 / C68 / C74 / C75 / C76); J2 footprint / position / pin 1; REF1
  pads; no pull-downs on the ISO1 / ISO2 inputs (covered by the CA-IS376xL default-low on an open input).
- **Worse:**
  - The primary-side route is 130 mm instead of 30 mm. It is shielded and passes ≈ 1–1.5 mm from the L2 pads
    (≈ 40 mV estimated spike, E2).
  - The island tracks have no ground plane (no planes allowed there).
  - H2 needs nylon hardware.

## Could not verify
- How J2 mates with the card on the built 5.1 board (gender, pin cross-section, stacking height): needs a look at the
  5.1 hardware (F1).
- CA-IS3721HW certificates: only the 2019 rev C Chinese datasheet could be fetched (F2).
- Control-card 5 V current: not in the card repository; 0.3 A assumed (A7).
- J4 C492405 stock / price (part page does not show it; the drawing was fetched).
- The coupling numbers of E2 / E5 / C4 are hand estimates, not field solutions. A scope check on the bench (RX at J2-24
  while the PFC switches at full load) would confirm them.

## Outside scope
- **Q9 (sheet 5, checklist 05 / 13):** on the same `SOT-23_Proteus` footprint, pad 1 = D, pad 2 = G, pad 3 = S, which
  gives physical lead 1 = G, lead 2 = S, lead 3 = D. That matches onsemi BSS138LT1G (C82045) Style 21 "1 Gate,
  2 Source, 3 Drain" (BSS138LT1/D Rev. 8). Correct; noted here because the caller asked.
- J2 courtyard overlaps with C10 / R35 / D10 and V4 / REF1 neighbour overlaps (drc.json) are unchanged from 5.1 (same
  coordinates on both boards). The C69941 body (≈ 3.0 × 32 mm) clears them by ≥ 0.08 mm on paper (checklist 12).
- The card's power_board_header.csv needs the 5.2 ADC map and DAB_DIS (card repository; F3).
