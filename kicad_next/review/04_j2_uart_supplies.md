# Review checklist 04 – control-card connector J2, +3V3 regulator, bias reference, isolated UART (U11, J4)

You are reviewing **one part** of the tube_power 5.2 power-supply board, alone, from this file and the repository
`/home/jari/dev/tube_psu_kicad`. You are doing a design review, not a redesign.

**Rules (full text: `kicad_next/review/README.md`, "Common rules" – read that section first):**
read-only on the repository, the only file you write is `kicad_next/review/findings/04_j2_uart_supplies.md`; no
commit, no push; never touch `kicad_next/tube_psu_5_2.kicad_pcb` / `.kicad_pro` and never run a script that saves or
regenerates design files (`route_s*.py`, `update_board_parts.py`, `setup_project.py` / `make_board.py` / generators
without `--check`); stop if a KiCad lock file exists (`rv guard`); RAM under 3 GB – no board DRC, no
`check_next.sh` (use the existing reports); never `pkill -f`; never run the KiCad AppImage with `--version`; the
owner's name / e-mail stay out of web requests. **Acceptance bar: match the bench-verified 5.1 board and add
creepage – do not optimise beyond that.** Datasheet facts come from the datasheet you fetch now, not from memory.

## 1. Scope

The power board is controlled by an FPGA card plugged onto **J2** (2 × 25 pins, 1.27 mm pitch, through-hole, at
(33.1, −22.2) … (34.4, 8.3) on F.Cu). J2 carries: 5V and GND to the card (pins 1, 2, 35, 36), 3.3 V logic PWM
outputs of the card (PFC, heater LLC, DAB, synchronous rectifier), two SPI ports for the isolated ADCs, the relay
GPIO, DAB_DIS, the UART pair, and eight analog outputs of the board to the card's two muxed 14-bit ADCs (0 – 3.3 V).
Everything on J2 is on the **mains-referenced primary ground**. This checklist covers J2 as an interface, and the
small circuits of sheet 4 that serve it:

- **V4** TPS73033 LDO 5V → **+3V3** (the board's analog / logic supply: op-amps, isolator primary sides, REF1);
- **REF1** REF3325 (2.5 V) → R110 1.00k / R3 1.96k → **U9** TLV316 follower → R131 22 Ω → **+1V65_BIAS** (C48), the
  mid-scale bias of all four current channels and of VAC (new buffer in 5.2);
- the **isolated UART**: TX (J2-26, FPGA out) → U11 A1 → B1 → R137 47 Ω → J4 pin 4 (RXD out); J4 pin 2 (TXD in) →
  R136 47 Ω → U11 B2 → A2 → RX (J2-24, FPGA in). **U11 = CA-IS3721HW** (2-channel, default high, SOIC-16W with a
  slot), side 2 powered from **J4 pin 6** (3.3 V from the other end). **J4** = 1×6 2.54 mm header at (11.4, −89.0):
  1 GND, 2 TXD in, 3 GND, 4 RXD out, 5 GND, 6 3V3 in, on its own island ISO_UART_GND at the top edge
  (x 3 … 20, y −91 … −66). Link speed **12 Mbaud**, single-ended, between two FPGA boards. 5.1 had a non-isolated
  3-pin header on primary ground. Barrier primary ↔ UART: reinforced, 8.0 mm creepage, 4.0 mm clearance.

The DC-link / VAC / AUX / 5V measurement amplifiers that are also drawn on sheet 4 (U6, U10) belong to
checklist 09; the current amplifiers to 08.

- Sheet: `kicad_next/04_mcu_connector.kicad_sch`, generator `tools/next/sheets/sheet04.py` (313 lines; `J2_PINS`
  table; UART at the end).
- Refdes here: J2, J4, U11, R136, R137, C134, C135, V4, C62, C68, C74, C75, C76, REF1, C69, R110, R3, C128, U9, C129,
  R131, C48.
- Nets: +3V3, 5V, GND, +1V65_BIAS, `Net-(REF1-VOUT)`, `Net-(U9-+)`, `Net-(U9--)`, TX, RX (primary side),
  UART_TXD, UART_RXD, UART_3V3, ISO_UART_GND, `Net-(U11-B1)`, `Net-(U11-B2)` (class UART_ISO), every J2 net.
- Board: J2 column x 33.1 / 34.4, y −22.2 … 8.3; V4 / REF1 / U9 on B.Cu at x 28 … 41, y −31 … −23; U11 on F.Cu at
  (0, −78) with a 1.0 × 14.5 mm slot (x −0.5 … 0.5, y −85.25 … −70.75); TX / RX run ≈ 130 mm from J2 on B.Cu and In3
  (between the pads of L2 at (−6, −32) / (0, −38)) to U11.

## 2. Read first

1. `kicad_next/J2_PINOUT.md` (91 lines, complete pin table).
2. `kicad_next/CHANGES_5_2.md` sections "3b. Isolated serial port" (3b.1 – 3b.4), "4. Measurements" rows 4.1, 4.8, 4b;
   "Open questions" 2, 3, 6.
3. `NEXT_REVISION.md` sections "3b", "4b", "4c" (ADC mux interface rules for every analog J2 pin).
4. `tools/next/sheets/sheet04.py`.
5. `kicad_next/README.md` sections "Stage 12" (TX / RX gap, distances to L2 and PFC copper), "Stage 11" (J4 1×6,
   island routing), "J2 escapes and J2 nets (routing stage 3e)" incl. "Escape geometry at J2", "Stage 3g".
6. `simulation/FINDINGS.md` 11.3 (bias buffer stability), 11.5 (mux leakage).
7. The control card, if present (read-only, outside this repository): `~/dev/ti60f225_tube_psu_control_card/`
   `reference/power_board_header.csv`, `reference/mux_assignment.csv`, `reference/pin_assignment.csv`.
8. Design document p 28 – 32 (`rv pdf 28 32`).
9. Datasheets to fetch: Chipanalog **CA-IS3721HW** (CA-IS372x: pinout, default state, data rate, propagation delay,
   pulse-width distortion, supply range and current vs data rate, VIOWM, certificates), TI **TPS73033**
   (dropout, output capacitor, NR pin, current limit), TI **REF3325** (input range, load / line regulation,
   output capacitor), TI **TLV316**, the header parts C69941 (J2) and C492405 (J4).

## 3. How to extract facts

```sh
kicad_next/review/tools/rv guard && kicad_next/review/tools/rv setup
kicad_next/review/tools/rv sch sheet 4
kicad_next/review/tools/rv sch ref J2                   # all 50 pins with nets and net classes
kicad_next/review/tools/rv sch ref U11,J4,V4,REF1,U9
kicad_next/review/tools/rv sch cmp51 4                  # 5.1 -> 5.2 differences of the sheet, incl. J2 pin moves
kicad_next/review/tools/rv sch51 ref J2                 # the 5.1 pin map
kicad_next/review/tools/rv sch net +3V3 +1V65_BIAS      # every consumer
kicad_next/review/tools/rv sch bom 4
kicad_next/review/tools/rv bq fp J2,J4,U11,R136,R137,C134,C135,V4,REF1,U9,R131,C48
kicad_next/review/tools/rv bq net TX RX                 # layers, lengths, vias of the UART pair on the primary side
kicad_next/review/tools/rv bq dist TX RX                # gap between the two, per layer
kicad_next/review/tools/rv bq near TX --within 1.0 --layer In3
kicad_next/review/tools/rv bq near RX --within 1.0 --layer In3
kicad_next/review/tools/rv bq dist RX AC1 --layer In3   # known point: 0.98 mm to the AC1 pad of L2
kicad_next/review/tools/rv bq dist TX PFC_DRAIN_1 --layer In3
kicad_next/review/tools/rv bq dist @UART @PRI           # island to primary copper, per layer
kicad_next/review/tools/rv bq dist @UART @SEC
kicad_next/review/tools/rv bq near @UART --within 8.5 --other-domain
kicad_next/review/tools/rv bq net UART_TXD UART_RXD UART_3V3 ISO_UART_GND
kicad_next/review/tools/rv bq net +1V65_BIAS
kicad_next/review/tools/rv bq net +3V3
kicad_next/review/tools/rv section kicad_next/README.md 'Stage 12'
kicad_next/review/tools/rv section kicad_next/README.md 'Stage 11'
```

To see which planes lie above / below a piece of the TX / RX route, cut the planes at the track's coordinate, e.g.
`kicad_next/review/tools/rv bq xsec GND In4.GND x -8.5 -56 -34` (GND plane on In4 along the In3 run at x ≈ −8.5) and
`kicad_next/review/tools/rv bq xsec GND In1.GND y -32.5 5 36`.

## 4. Checklist

### A. J2 pin map and signal ranges

- **A1 Pin table = netlist.** `rv sch ref J2` against `kicad_next/J2_PINOUT.md` "All pins" (50 rows). PASS: identical.
- **A2 Changes against 5.1.** `rv sch cmp51 4` / `rv sch51 ref J2`. Expected and documented (CHANGES 4b, 3.3):
  PFC_I1_MEAS 43 → 42, DHB_I_MEAS 37 → 38, AUX_MEAS 40 → 43, new 5V_MEAS on 49, new DAB_DIS on 18, spare analog pins
  37 / 39 / 40 / 46 / 48 / 50 tied to GND. PASS: no other pin changed function; every moved pin is listed in
  CHANGES; FAIL for any undocumented move.
- **A3 Against the control card.** If `~/dev/ti60f225_tube_psu_control_card/reference/power_board_header.csv` is
  readable: compare pin by pin (ball names of J2_PINOUT.md column 2, ADC channel names ADA0 – 6 / ADB0 – 6,
  direction). PASS: every 5.2 net lands on a card pin of the right kind (PWM-capable output, ADC mux input,
  UART RX / TX the right way round: J2-24 is the FPGA **input**), and the six grounded analog pins are mux inputs
  on the card, not outputs or supplies. **A card pin that drives a J2 pin which 5.2 now ties to GND (37, 39, 40,
  46, 48, 50) is a blocker.** If the card files are not readable: CANNOT VERIFY, list what to compare.
- **A4 J2-18 DAB_DIS (known open input).** The owner still has to assign the card pin (ball F16). PASS if the
  board is safe with the pin floating, driven low, or driven high: R129 10 k pull-down → drivers enabled; state
  what a 3.3 V high does (both DAB drivers off) and that an un-configured FPGA pin (weak pull-up of typically
  tens of kΩ – check the FPGA family named in the card repository) cannot lift the 10 k pull-down above the
  UCC21520 DISABLE threshold.
- **A5 Power-up states.** For every card output on J2 (PWM pins 3 – 6, 10, 12, 19, 33; SYNCH 9 / 13; relay 17; SPI
  7, 8, 14, 15; TX 26): what holds it while the FPGA is unconfigured or the card is unplugged? PASS: every PWM
  has a pull-down on the board (R77, R78, R73, R74, R69, R71; EPWM2A / 2B and SYNCH_1 / 2 go straight into ISO1 /
  ISO2 inputs – check the isolator's behaviour with a floating input and whether a pull-down is needed, as 5.1
  had none: `rv sch51 net EPWM2A`), relay off (R32).
- **A6 Analog outputs: range and source impedance.** For pins 38, 41, 42, 43, 44, 45, 47, 49 take the series
  resistor / capacitor at the pin from `rv sch ref J2` + the driving net and check NEXT_REVISION 4c rule 1:
  driven by an op-amp through ≤ 100 Ω with ≤ 100 pF at the pin. PASS: all eight follow the rule (C10 / C26 are
  DNP "na"); no output can exceed 3.3 V + 0.3 V into the card's mux (every amplifier runs from +3V3) or go
  below −0.3 V.
- **A7 5V and GND pins.** Card supply current (find it in the card repository or state the assumption) through
  one 1.27 mm pin (J2-2) and return through pins 1, 35, 36 plus the six grounded analog pins. Pin rating of the
  header part (C69941 datasheet, typically 1 A per pin for 1.27 mm). PASS: 5V pin current ≤ 70 % of the pin
  rating; the 5V track / pour into pin 2 (`rv bq net 5V`) is ≥ 0.5 mm.
- **A8 Header part and orientation (review flag "check gender / height").** J2 is a through-hole 2×25 1.27 mm
  **pin header** on F.Cu with pin 1 at (33.135, −22.156) and the even row at x 34.405. Compare with 5.1
  (`rv bq51 fp J2` – same position, same pin 1?) and with the card's mating connector. PASS: same footprint
  position / rotation / pin numbering as 5.1 (the card is unchanged) and the LCSC part is a male header of
  the mating height used on 5.1; otherwise CANNOT VERIFY with the measurement to take.

### B. +3V3 regulator V4

- **B1 Load budget.** Sum the +3V3 consumers from `rv sch net +3V3` with datasheet supply currents: U1 + U4
  (LMH6643, 2 × dual), U6, U8, U9 (TLV316), U10 (TLV9062), REF1 + its 3 kΩ divider, ISO1 / ISO2 / U11 side 1 at
  their data rates (12 Mbaud on U11; SPI clocks on ISO1 / ISO2), bias loads. PASS: ≤ 60 % of the TPS73033
  rated current, dissipation (5 V − 3.3 V) × I within SOT-23-5 limits at 70 °C ambient (design document p 34).
- **B2 Application circuit.** Pins 1 IN (5V), 2 GND, 3 EN (tied to 5V), 4 NR (C74 100 nF), 5 OUT; C75 1 µF in,
  C62 2.2 µF / C68 / C76 1 µF out. PASS: capacitor values meet the datasheet minimums, the NR capacitor value is
  allowed (start-up time with 100 nF stated), footprint pin order = datasheet DBV pinout
  (`rv bq fp V4` pads vs `rv sch ref V4`; the footprint is the 5.1 "Proteus" SOT-23-5 – same as 5.1).

### C. Bias reference REF1 / U9 (CHANGES 4.1, 4.8)

- **C1 REF1.** REF3325AIDBZR on +3V3: datasheet minimum input voltage for 2.5 V out at the divider load
  (2.5 V / 2.96 kΩ = 0.85 mA), pinout of the DBZ package vs the footprint pads (CHANGES 4.8 says "same SOT-23
  pinout 1 IN / 2 OUT / 3 GND as the ISL21010, the Proteus-numbered footprint stays" while the netlist shows
  REF1 pin 1 = GND, 2 = VIN (+3V3), 3 = VOUT). **Resolve this**: compare the symbol pin numbers
  (`rv sch ref REF1`), the pad numbers and positions of `tube_psu:SOT-23_Proteus` (`rv bq fp REF1`) and the
  datasheet package drawing, and say which physical lead gets which net. PASS: physical lead 1 = IN, 2 = OUT,
  3 = GND per the datasheet; FAIL (blocker) if the reference would be mounted with swapped pins. Also C69
  100 nF on the output against the datasheet's allowed load capacitance.
- **C2 Divider and bias value.** 2.5 V × 1.96 / 2.96 = 1.655 V; tolerance from REF3325 accuracy and the resistor
  tolerances (`rv sch part R110,R3`). PASS: bias within 1.65 V ± 1 % or the error is covered by the firmware
  zero calibration (CHANGES 4.1 says common to all channels).
- **C3 Buffer.** U9 + input on the divider with C128 100 nF, output → R131 22 Ω → +1V65_BIAS with C48 100 nF,
  feedback from the op-amp output pin (pin 1 = pin 4, `Net-(U9--)`). FINDINGS 11.3 shows PM 84° with the vendor
  model and **oscillation if the feedback is taken from the bias node**. PASS: the netlist takes the feedback
  before R131 (R131 pin 1 = U9 output net, pin 2 = +1V65_BIAS), no other capacitor hangs directly on the U9
  output, and the total capacitance on +1V65_BIAS (C48 + C122 + C123 + C126 + C106 + C107 …: `rv sch net
  +1V65_BIAS`) is what the simulation assumed (≈ 100 nF).
- **C4 Bias distribution.** `rv bq net +1V65_BIAS`: one net to U1, U4, U8 (30 – 60 mm). PASS: routed away from the
  switch nodes (the README notes a bias via 0.16 mm from $HT_CS / SYNCH_2 lanes near (13.0, −44.1) under the DAB
  primary: judge the coupling – digital edges into a 22 Ω / 100 nF node – and say whether a local capacitor at
  U1 / U4 exists: C122 / C123 are 12 p / 5.6 p only).

### D. Isolated UART

- **D1 U11 pin map.** `rv sch ref U11` against the CA-IS3721 datasheet (wide body, one forward + one reverse
  channel): 1 / 7 GND1, 3 VDD1, 4 A1 (in), 5 A2 (out), 12 B2 (in), 13 B1 (out), 14 VDD2, 9 / 16 GND2, others NC.
  PASS: agrees; the "H" variant is default-high on **both** outputs (FPGA RX idles high with no cable, RXD out
  idles high with the board unpowered on side 1).
- **D2 Direction end to end.** FPGA TX = J2-26 → A1 → B1 → R137 → J4-4 "RXD out"; J4-2 "TXD in" → R136 → B2 → A2 →
  J2-24 = FPGA RX. The J4 names are from the point of view of **the other device** (CHANGES 3b.2). PASS: the
  netlist does this; the findings state in one line what the far-end FPGA must connect to pins 2 and 4.
- **D3 12 Mbaud budget.** Bit time 83.3 ns. From the datasheet: maximum data rate, propagation delay, pulse-width
  distortion (PWD) and part-to-part skew at 3.3 V. Add the RC of R136 / R137 47 Ω with the cable / pin
  capacitance (state the assumption, e.g. 30 cm ribbon ≈ 30 – 50 pF) and of 130 mm of 0.152 mm track on the primary
  side. PASS: data rate rating ≥ 24 Mbps, PWD ≤ 10 % of the bit time, RC time constant ≤ 10 % of the bit time.
- **D4 Side-2 supply from J4 pin 6.** U11 VDD2 = UART_3V3 with C135 100 nF; supply current of side 2 at 12 Mbaud;
  behaviour with the cable unplugged (side 2 unpowered → A2 default high: PASS) and with the cable plugged but
  this board off (side 1 unpowered → B1 default high: PASS). Check the datasheet's absolute maximum on B2 when
  VDD2 = 0 and the far end drives TXD high (current into the input through R136 47 Ω).
  PASS: no absolute-maximum violation in any power sequence, or the 47 Ω limits the current to the datasheet's
  allowed input current.
- **D5 ESD / hot-plug on J4.** J4 is user-accessible. 47 Ω series only, no TVS (5.1 had none either, but 5.1 was
  not isolated and not meant for a cable). Note, not FAIL, unless the datasheet demands protection.
- **D6 Isolation rating (known open point: certificate).** As checklist 03 item A5 but for the CA-IS3721HW and the
  UART barrier (318 Vrms reinforced, user-touchable far end): VIOWM, VIOTM, certificate status from the fetched
  datasheet. PASS: reinforced rating ≥ 318 Vrms with certificate; "pending" → CANNOT VERIFY + finding.
- **D7 Slot and island distances.** `rv bq dist @UART @PRI`, `rv bq near @UART --within 8.5 --other-domain`,
  `rv bq slots`. PASS: on inner layers ≥ 8.0 mm straight everywhere (expect ≈ 8.05 mm on In1 / In4 at x 12.2 /
  20.3); on outer layers ≥ 4.0 mm clearance and ≥ 8.0 mm creepage, the only sub-8 mm straight pair being the two
  pad rows of U11 across its slot (7.25 mm straight, 8.85 mm round the slot per README); island to the DAB
  secondary ≥ 8.4 mm; island to the board edge and to mounting hole H2 at (6.9, −87.5) – the hole is earthed
  chassis: `rv bq dist H2 @UART` – state the distance and which rule applies (README table has no row
  "UART ↔ mounting hole"; ISO_UART_GND is the far end's ground, normally earth: note).
- **D8 No copper under the island.** `rv bq near J4 --within 8.0`, `rv bq xsec GND In1.GND y -80 0 25`,
  `rv bq xsec GND In4.GND y -80 0 25`, the same for `15V`, `5V`, `+3V3` on In3. PASS: no primary plane or track
  on any layer inside x ≈ 4 … 20, y −91 … −66 except what belongs to the island.
- **D9 Island routing at 12 Mbaud.** README "Stage 11": TXD 12.3 mm on F.Cu, UART_3V3 on B.Cu, ground as a 0.3 mm
  B.Cu bus under the TXD lane, no plane. `rv bq net UART_TXD UART_RXD ISO_UART_GND`. PASS: each signal has a
  ground conductor within ≈ 1 mm for its whole length on the island (track or adjacent header pin); R136 / R137
  at U11 (≤ 5 mm from pins 12 / 13); C135 ≤ 3 mm from pins 14 / 16.

### E. TX / RX on the primary side (J2 → U11, ≈ 130 mm) – known weak point

- **E1 Geometry as documented.** `rv bq net TX RX`, `rv bq dist TX RX`. PASS: 0.152 mm tracks, ≥ 0.6 mm edge to
  edge except at the four layer-change vias (README "Stage 12": 0.43 – 0.57 mm there), route lengths
  ≈ 131.4 / 128.7 mm.
- **E2 Distance to PFC nodes.** `rv bq dist RX AC1 --layer In3` (documented 0.98 mm to the through-hole pad of L2
  pin 1), `rv bq dist TX PFC_DRAIN_1 --layer In3` (documented 1.46 mm to L2 pin 2, the PFC switch node:
  0 ↔ 400 V in ≈ 10 – 20 ns), `rv bq near TX --within 1.0 --layer In3`, `rv bq near RX --within 1.0 --layer In3`.
  Functional insulation inside the primary domain: inner-layer rule 0.5 mm for ≤ 500 V. PASS on spacing if
  ≥ 0.5 mm. **Then estimate the coupling**: capacitance from the L2 pin-2 barrel / pad stack to 1.5 mm of TX
  track (order 10 – 50 fF) × dv/dt (400 V / 15 ns) into the driver impedance of the FPGA pin (≈ 25 – 50 Ω) and
  the 3.3 V input threshold of U11 – give the induced spike in volts and compare with the input hysteresis /
  noise margin from the datasheet. PASS: spike ≤ 20 % of the logic swing; otherwise finding with the smallest
  fix (e.g. series resistor + small capacitor at U11 pin 4, or a glitch filter in the far-end receiver for RX
  which is driven by U11 A2 near the far end of the run).
- **E3 Reference planes.** Along the In3 part: In4 GND plane below and In2 above (signal layer; README says only
  +3V3 runs parallel 5 mm). `rv bq xsec GND In4.GND y -32.5 5 36`, `rv bq xsec GND In4.GND x -8.5 -56 -34`,
  `rv bq xsec GND In1.GND y -34.5 -9 6`. PASS: a GND plane on In4 is continuous under the pair for the whole
  In3 run (gaps listed with coordinates); where the pair is on B.Cu the In4 plane is above it.
- **E4 What crosses or lies over the pair.** From README "Stage 12" list: PFC_DRAIN_1 pour on F.Cu over 9 mm of
  the pair (In1 GND plane between), GATE1 crossing on B.Cu (In4 between), 15V / 5V plane gap corridor. Verify two
  of these statements with `rv bq xsec PFC_DRAIN_1 F.Cu y -34.5 -9 6` and `rv bq xsec GND In1.GND y -34.5 -9 6`.
  PASS: a solid GND plane lies between the pair and every HV pour / gate track that overlaps it in plan view.
- **E5 Signal integrity at 12 Mbaud.** Track 0.152 mm on In3 between In2 (0.203 mm prepreg above) and In4 (0.2 mm
  core below): estimate Z0 (≈ 50 – 60 Ω stripline-like) and the one-way delay (≈ 0.9 ns for 130 mm); rise time
  of the FPGA output ≈ 1 – 3 ns → electrically short for 12 Mbaud; no termination needed. PASS: delay < 1/6 of the
  rise time × … – state the numbers and the conclusion plainly; crosstalk TX ↔ RX at 0.6 mm over 120 mm with
  h ≈ 0.2 mm: estimate (few %) and compare with the margin.

### F. Parts and bring-up

- **F1** `rv sch bom 4`: J4 "stock / price not read" (C492405), J2 "check gender / height", U11 "reinforced rating to
  confirm", REF1 changed part. List what is still open.
- **F2** Bring-up notes: +3V3 and +1V65_BIAS test points (where can they be probed? C48, C62 pads on B.Cu); UART
  loop-back test (jumper J4-2 ↔ J4-4 with 3.3 V on pin 6); warning from NEXT_REVISION 3b.5 is obsolete for 5.2
  (isolated) – check no document still tells the builder that J4 is on primary ground or 4-pin (README "Stage 11"
  admits "older text in this file says 4-pin header": list the stale places as a documentation finding).

## 5. Out of scope / given

- U6 (DC link), U10 (AUX / 5V monitors), U8 (VAC): checklist 09. U1 / U4: 08. ISO1 / ISO2 and the SPI ADCs: 03.
  DRV5 DISABLE behaviour: 02. Whole-board creepage basis: 10.
- Given: J4 1×6 with ground pins beside each signal, 12 Mbaud; U11 = CA-IS3721HW powered from J4 pin 6 (no LDO);
  ball-named J2 pins 20 – 23, 25, 27 – 32, 34 are unused on the card (owner 2026-11-20); the ADC channel map of
  CHANGES 4b; no silkscreen (so **no pin-1 mark on J4 / J2** – mention in bring-up notes, not a finding); via-in-pad.

## 6. Findings format

Write `kicad_next/review/findings/04_j2_uart_supplies.md` exactly in the format of `kicad_next/review/README.md`
"Common findings format": summary; one table row per item above (A1 … F2) with **PASS / FAIL / CANNOT VERIFY** and
the evidence (file:line, command + output lines, calculation with inputs, or datasheet document / page / URL);
ranked findings with severity (**blocker for ordering / should fix / note**), what is wrong, evidence, smallest fix,
confidence; "Compared with 5.1"; "Could not verify"; "Outside scope". "Looks fine" without evidence is not
acceptable.
