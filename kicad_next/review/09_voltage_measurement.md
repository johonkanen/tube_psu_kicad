# Review checklist 09 – primary-side voltage measurement chains: VAC (U8), DC link (U6), 15V and 5V monitors (U10)

You are reviewing **one part** of the tube_power 5.2 power-supply board, alone, from this file and the repository
`/home/jari/dev/tube_psu_kicad`. You are doing a design review, not a redesign.

**Rules (full text: `kicad_next/review/README.md`, "Common rules" – read that section first):**
read-only on the repository, the only file you write is `kicad_next/review/findings/09_voltage_measurement.md`; no
commit, no push; never touch `kicad_next/tube_psu_5_2.kicad_pcb` / `.kicad_pro` and never run a script that saves or
regenerates design files (`route_s*.py`, `update_board_parts.py`, `setup_project.py` / `make_board.py` / generators
without `--check`); stop if a KiCad lock file exists (`rv guard`); RAM under 3 GB – no board DRC, no
`check_next.sh` (use the existing reports); never `pkill -f`; never run the KiCad AppImage with `--version`; the
owner's name / e-mail stay out of web requests. **Acceptance bar: match the bench-verified 5.1 board and add
creepage – do not optimise beyond that.** Datasheet facts come from the datasheet you fetch now, not from memory.

## 1. Scope

Four voltages on the mains-referenced primary are scaled to 0 – 3.3 V for the FPGA card's muxed ADC B (via J2):

| Signal (J2 pin) | Source | Network | Scale |
|---|---|---|---|
| **VAC_MEAS** (47) | AC1 / AC2 = mains after the EMI filter (across C117) | difference amplifier **U8** (TLV316): AC1 → R47 + R48 + R79 (3 × 1 MΩ) → inverting input, feedback R49 12k ‖ C127 1 nF; AC2 → R50 + R51 + R52 (3 × 1 MΩ) → non-inverting input, R80 12k ‖ C126 1 nF to +1V65_BIAS; output → R65 100 Ω | 1.65 V + 0.004 × (V_AC2 − V_AC1): ± 412 V full scale |
| **DC_LINK_MEAS** (41) | DC+ against GND | difference amplifier **U6** (TLV316): DC+ → R16 + R15 + R10 (3 × 1 MΩ) → non-inverting input, R17 15k ‖ C130 1 nF to GND; GND → R112 + R111 + R109 (3 × 1 MΩ) → inverting input, feedback R82 15k ‖ C131 1 nF; output → R2 100 Ω | 0.005 × V_DC: 400 V = 2.0 V, full scale 660 V |
| **AUX_MEAS** (43) | 15V rail | R11 22k / R12 4.7k, C61 100 nF → follower **U10A** (TLV9062) → R132 100 Ω | 0.176 × V: 15 V = 2.64 V, full scale 18.7 V |
| **5V_MEAS** (49, new) | 5V rail | R133 15k / R134 10k 0.1 %, C132 100 nF → follower **U10B** → R135 100 Ω | 0.4 × V: 5 V = 2.0 V, full scale 8.25 V |

(Verify the table against the netlist – first item.) The PFC control uses VAC as its reference waveform (design
document p 13), the DC-link value closes the voltage loop and protects the bus. New in 5.2: R49 / R80 15k → 12k
(no clipping up to 264 Vrms), 1 nF feedback / bias-leg capacitors on U8 and U6 (HF feedthrough), R2 1k → 100 Ω and
C4 removed, AUX buffered by U10A with C61 1 nF → 100 nF, the 5V monitor, the bias buffer U9 (checklist 04).

- Sheets: U8 and its parts on `09_ac_measurement.kicad_sch` (`tools/next/sheets/sheet09.py`; the same sheet holds
  the PFC gate drivers – checklist 05); U6, U10 and their parts on `04_mcu_connector.kicad_sch` (`sheet04.py`,
  blocks "DC-link measurement", "15V measurement", "5V measurement").
- Refdes: U8, R47, R48, R79, R50, R51, R52, R49, R80, C126, C127, R65, C60; U6, R16, R15, R10, R17, C130, R112, R111,
  R109, R82, C131, R2; U10, R11, R12, C61, R132, R133, R134, C132, R135, C133.
- Nets: AC1, AC2, `Net-(R47-Pad2)`, `Net-(R48-Pad2)`, `Net-(R50-Pad2)`, `Net-(R51-Pad2)`, `Net-(U8-+)`, `Net-(U8--)`,
  `Net-(C127-Pad1)` (U8 output), VAC_MEAS; DC+, `Net-(R15-Pad1)`, `Net-(R10-Pad1)`, `Net-(U6-+)`, `Net-(R111-Pad1)`,
  `Net-(R109-Pad1)`, `Net-(U6--)`, `Net-(C131-Pad2)` (U6 output), DC_LINK_MEAS; `Net-(U10A-+)`, `Net-(U10A--)`,
  AUX_MEAS, `Net-(U10B-+)`, `Net-(U10B--)`, 5V_MEAS; +1V65_BIAS, +3V3.
- Board (all near J2, south-centre): the first two 1 MΩ of each VAC leg R47 / R48 / R50 / R51 on B.Cu at (1 … 4, 6 … 9)
  next to L1 / Q6; U8 with R79, R52, R49, R80, C126, C127, R65 at x 30 … 36, y 7 … 15; U6 on B.Cu at (20, 1) with
  R16 / R15 on F.Cu at (16, 2 … 4), R10 B.Cu (19, 5), R112 / R111 / R109 at (15 … 17, −3 … 0); U10 on B.Cu at (40, −3)
  with its dividers at x 37 … 43, y −9 … 1.

## 2. Read first

1. `tools/next/sheets/sheet09.py` (73 lines) and the three measurement blocks of `tools/next/sheets/sheet04.py`
   (notes at lines ≈ 166, 187, 263).
2. `kicad_next/CHANGES_5_2.md` section "4. Measurements" rows 4.2, 4.3, 4.4, 4.5 / 4c.2, 4b "5V_MEAS".
3. `NEXT_REVISION.md` section 4 rows 4.2 – 4.5 and section 4c (mux interface rules 1 – 5, dwell times).
4. `simulation/FINDINGS.md` sections 1 (line coupling into the bias), 2 (VAC), 3 (DC link), 9 (mux leakage), 10
   (ranges), 11.1, 11.2, 11.5 (5.2 results).
5. `kicad_next/README.md`: "ISO2 / AD2 fan-out, 420V divider, R10 / R79 (routing stage 3d)" (R10 / R79 moves),
   "J2 escapes and J2 nets (routing stage 3e)", "Stage 5b" (U6 output, Net-(R51-Pad2) on In2), "First draft" DRC
   row "clearance" (Net-(C11-Pad1) via next to R65 / Net-(C127-Pad1)).
6. Design document p 13 (`rv pdf 13`).
7. Datasheets to fetch: TI **TLV316** (input common-mode range, output swing, GBW 10 MHz, Ib), TI **TLV9062**
   (RRIO, Ib, Vos), the 1 MΩ 0805 resistor actually ordered (`rv sch part R47` → LCSC number: rated working
   voltage and overload voltage), C0G 1 nF 0603.

## 3. How to extract facts

```sh
kicad_next/review/tools/rv guard && kicad_next/review/tools/rv setup
kicad_next/review/tools/rv sch sheet 9
kicad_next/review/tools/rv sch ref U8,U6,U10
kicad_next/review/tools/rv sch ref R47,R48,R79,R50,R51,R52,R49,R80,C126,C127,R65
kicad_next/review/tools/rv sch ref R16,R15,R10,R17,C130,R112,R111,R109,R82,C131,R2
kicad_next/review/tools/rv sch ref R11,R12,C61,R132,R133,R134,C132,R135,C133
kicad_next/review/tools/rv sch cmp51 9
kicad_next/review/tools/rv sch cmp51 4
kicad_next/review/tools/rv sch part R47,R16,U8,U10,C126
kicad_next/review/tools/rv bq fp R47,R48,R79,R50,R51,R52,U8,R16,R15,R10,R112,R111,R109,U6,U10
kicad_next/review/tools/rv bq net "Net-(R47-Pad2)" "Net-(R48-Pad2)" "Net-(R50-Pad2)" "Net-(R51-Pad2)"
kicad_next/review/tools/rv bq net "Net-(R15-Pad1)" "Net-(R10-Pad1)" "Net-(R111-Pad1)" "Net-(R109-Pad1)"
kicad_next/review/tools/rv bq net "Net-(U8-+)" "Net-(U8--)" "Net-(U6-+)" "Net-(U6--)" "Net-(U10A-+)" "Net-(U10B-+)"
kicad_next/review/tools/rv bq net VAC_MEAS DC_LINK_MEAS AUX_MEAS 5V_MEAS
kicad_next/review/tools/rv bq near "Net-(R48-Pad2)" --within 1.3
kicad_next/review/tools/rv bq near "Net-(R51-Pad2)" --within 1.3
kicad_next/review/tools/rv bq near "Net-(R47-Pad2)" --within 1.3
kicad_next/review/tools/rv bq near "Net-(R15-Pad1)" --within 1.3
kicad_next/review/tools/rv bq near "Net-(U8--)" --within 0.5
kicad_next/review/tools/rv bq padgap R47.1 R47.2
kicad_next/review/tools/rv bq classes | grep -E "^HV_PRIMARY"
kicad_next/review/tools/rv bq51 fp R47,R48,R79,R50,R51,R52,U8,R16,R15,R10,U6
kicad_next/review/tools/rv section simulation/FINDINGS.md '^## 2\.'
kicad_next/review/tools/rv section simulation/FINDINGS.md '11.2 Ranges'
```

## 4. Checklist

### A. VAC measurement (U8)

- **A1 Topology and gain.** From the netlist: which mains node goes to which input, where the bias enters (R80 from
  +1V65_BIAS to the non-inverting input), feedback R49. Transfer: V_out = 1.65 V + (R49 / 3 MΩ) × (V_AC2 − V_AC1)
  = 1.65 V + 0.004 × ΔV. PASS: gain 0.004 on both legs (R49 = R80 = 12 k, 3 × 1 MΩ each), sign documented (which
  mains half-wave gives V_out > 1.65 V) and equal to 5.1 (`rv sch cmp51 9`: only R49 / R80 values, C126 / C127 and
  the output net name changed).
- **A2 Range (CHANGES 4.3).** 230 V + 10 % = 253 Vrms → 358 V peak → ± 1.43 V → 0.22 … 3.08 V; 264 Vrms → 373 V →
  0.16 … 3.14 V. TLV316 output swing at 3.3 V into 100 Ω + mux (datasheet: mV from the rails at light load) and
  its input common-mode range (inputs sit at 1.65 V × 3 M / 3.012 M ≈ 1.64 V ± 1.4 mV… recompute: the + input
  node = bias + (AC2 − bias) × 12 k / 3.012 M). PASS: no clipping at 264 Vrms; surge / transient above full
  scale only saturates (state the input current: 2.5 kV / 3 MΩ < 1 mA → clamp diodes of the op-amp: check the
  datasheet's input-current limit of 10 mA).
- **A3 HF filter (CHANGES 4.2).** C127 across R49 and C126 across R80: pole 1 / (2π · 12 k · 1 nF) = 13.3 kHz on both
  legs (balanced). FINDINGS 2 / 11.1. Phase lag at 50 Hz (0.2°) and at the PFC control bandwidth. PASS: equal
  time constants on both legs (C0G 5 % parts: `rv sch part C126`), no capacitor directly on the op-amp output
  before R65.
- **A4 Resistor chains: voltage and creepage.** Each 1 MΩ 0805 sees up to 373 V / 3 = 124 V peak (88 Vrms)
  continuously and one third of a mains transient (2.5 kV / 3 ≈ 830 V per resistor for a surge – overload
  rating?). `rv sch part R47` → LCSC part → rated working voltage (0805 thick film typically 150 V) and
  maximum overload voltage. `rv bq padgap R47.1 R47.2` (0805 pad gap ≈ 0.9 – 1.0 mm for up to 124 V – pad pairs
  are exempt from the 1.2 mm rule). PASS: working voltage ≤ rating with 264 Vrms; note the surge figure.
  Compare with 5.1 (same parts: `rv sch51 ref R47`).
- **A5 Chain layout.** The first two resistors of each leg stand at (1 … 4, 6 … 9) next to L1 / Q6; the third (R79 at
  (35, 15), R52 at (30, 12)) is at U8 – so the nets `Net-(R48-Pad2)` and `Net-(R51-Pad2)` (at ⅓ of the mains
  voltage, 1 MΩ source impedance) run ≈ 30 mm across the board (README "Stage 5b": Net-(R51-Pad2) on In2).
  `rv bq net "Net-(R48-Pad2)" "Net-(R51-Pad2)"`, `rv bq near "Net-(R48-Pad2)" --within 1.3`, the same for R51,
  R47, R50. The four intermediate nodes are in net class HV_PRIMARY (`rv bq classes | grep -E "^HV_PRIMARY"`), so
  the 1.2 mm outer / 0.5 mm inner functional rule applies to them; `Net-(R48-Pad2)` runs 36 mm and
  `Net-(R51-Pad2)` 32 mm on In2. PASS: ≥ 0.5 mm (inner) / 1.2 mm (outer) from every other net, and from each other
  where they are different legs (the two legs are up to ⅔ × 373 V apart); not worse than 5.1
  (`rv bq51 near "Net-(R48-Pad2)" --within 0.6`). Also pickup: 30 mm of MΩ-impedance track next to which
  switching nets? (GATE2, PFC_DRAIN_2, PWM lanes: list those within 1 mm on the same or the adjacent layer and
  whether a plane separates them; the 13 kHz filter removes it only if the pickup is common to both legs.)
- **A6 Summing nodes.** `rv bq net "Net-(U8-+)" "Net-(U8--)"`, `rv bq near "Net-(U8--)" --within 0.5`. PASS: R79 /
  R52 / R49 / R80 / C126 / C127 within ≈ 5 mm of U8 pins 3 / 4, both nodes of similar length, not next to the
  DRV2 gate drive (12, 10) or the DC+ pour.
- **A7 Line coupling into the bias (FINDINGS 1, 11.3).** With the U9 buffer the residual coupling is 7.3 · 10⁻⁶ V/V
  (29 mA on PFC_I at line frequency). Check that the + leg really returns to the **buffered** +1V65_BIAS node
  (after R131) and that C126 does not form a path that defeats the buffer. PASS: as simulated; note the figure
  for the firmware.

### B. DC-link measurement (U6)

- **B1 Topology and gain.** DC+ → 3 MΩ → + input with R17 15k ‖ C130 to GND; GND → 3 MΩ → − input with R82 15k ‖ C131
  feedback. V_out = 0.005 × V_DC (no bias). 400 V → 1.99 V; 450 V → 2.24 V; flyback LOVP 483 V → 2.40 V; full
  scale 660 V. PASS: as stated; the − leg's 3 MΩ to GND (R112 pin 1 = GND) exists so that both inputs see the
  same source impedance; equal to 5.1 except C130 / C131 added, R2 100 Ω, C4 removed (`rv sch cmp51 4`).
- **B2 Filter and mux interface (CHANGES 4.4).** Pole 1 / (2π · 15 k · 1 nF) = 10.6 kHz on both legs; output R2
  100 Ω, no capacitor at the pin (C4 removed). PASS: C4 is neither in the netlist nor on the board
  (`rv bq fp C4` → not on the board); rule 1 of NEXT_REVISION 4c met.
- **B3 Resistor stress.** 400 – 450 V / 3 = 133 – 150 V dc per 1 MΩ 0805 (R16, R15, R10) – at or above a 150 V rating;
  5.1 the same. `rv sch part R16` → rated voltage. PASS if ≤ the part's rated working voltage at 450 V,
  otherwise finding "should fix": same footprint part with ≥ 200 V rating (0805 high-voltage series) or note
  "as 5.1" with the over-stress ratio. Power 20 mW each.
- **B4 Chain layout.** R16 / R15 on F.Cu at (16, 2 … 4), R10 on B.Cu (19, 5) (moved in stage 3d), the GND-leg chain
  R112 / R111 / R109 at (15 … 17, −3 … 0). `rv bq near "Net-(R15-Pad1)" --within 1.3`, `rv bq net "Net-(R10-Pad1)"`.
  PASS: DC+ end ≥ 1.2 mm from everything but its own pad pair, intermediate nodes (267 V, 133 V) ≥ 0.5 mm inner /
  1.2 mm outer from GND and signal copper (they are in class HV_PRIMARY: `rv bq classes | grep HV_PRIMARY`
  lists `Net-(R10-Pad1)`, `Net-(R15-Pad1)`), the low-voltage end short.
- **B5 Where DC+ is sensed.** R16 pad 1 at (15.5, 5.4) taps the DC+ pour between the bulk capacitors (x ≈ 20) and
  Q6 / SICD2. The − reference is the GND at R112 (15, −3). With ≈ 3 – 4 A rms PFC return current in the GND copper
  nearby, the IR error is µV × 0.005 – irrelevant; ripple seen = the true bus ripple. PASS / note.

### C. 15V and 5V monitors (U10)

- **C1 AUX_MEAS.** 15V × 4.7 / 26.7 = 0.176 → 2.64 V at 15.0 V; 15V range 14.2 – 15.5 V (flyback cross regulation) →
  2.50 – 2.73 V; full scale 18.7 V. C61 100 nF: τ = (22k ‖ 4.7k) · 100 n = 0.39 ms. PASS: values in netlist;
  CHANGES 4.5 says "C61 1n → 100n" while NEXT_REVISION 4.5 says "→ 1 µF" (for the unbuffered option) – the
  buffered design with 100 nF is the documented final choice: confirm the board / BOM carry 100 nF
  (`rv sch part C61`) and record the two-document difference as a documentation note.
- **C2 5V_MEAS.** 5V × 10 / 25 = 0.4 → 2.000 V; 0.1 % resistors (`rv sch part R133,R134`); C132 100 nF, τ = 6 kΩ ·
  100 nF = 0.6 ms (NEXT_REVISION.md section 4b says 1.6 ms, the sheet note 0.6 ms: recompute and report which text
  is wrong). The 5V rail is the regulated flyback output (5.00 V ± 2.2 %): the monitor lets the firmware see
  flyback faults. PASS: ratio and accuracy (0.1 % resistors + TLV9062 Vos ≤ 1.6 mV → < 0.1 %).
- **C3 TLV9062 use.** Dual RRIO on +3V3 (C133), both as followers: input range includes 2.0 – 2.73 V, output swing
  near 3.3 V irrelevant; **input above the supply**: if +3V3 is absent while 15V / 5V are present (V4 fault,
  start-up order: the flyback brings 15V and 5V up together and V4 follows 5V within ms), the dividers drive
  the inputs to 2.6 V / 2.0 V through 3.9 k / 6 k: current into the ESD diodes ≤ 0.7 mA – within the datasheet's
  input-current limit (10 mA typical abs-max)? PASS with the datasheet figure.
- **C4 Output resistors and J2.** R132 / R135 100 Ω at the op-amp or at J2; rule 1 of 4c. PASS.
- **C5 Pinout / footprint.** TLV9062IDGKR = VSSOP-8 on `Package_SO:VSSOP-8_3x3mm_P0.65mm` (`rv bq fp U10`): pins
  1 OUT A, 2 −A, 3 +A, 4 V−, 5 +B, 6 −B, 7 OUT B, 8 V+ – matches the netlist (follower: pin 1 = pin 2, pin 7 =
  pin 6). The README mentions a special DRC rule for VSSOP-8 pads 0.15 mm apart ("Same-footprint pad gap,
  low-voltage classes"). PASS: land pattern within the TI drawing; pad gap ≥ JLC's minimum solder-mask web or
  mask opening defined as a gang opening (note for checklist 14).

### D. Common

- **D1 Verify the table of section 1** row by row from `rv sch ref ...` and `kicad_next/J2_PINOUT.md` (pins 41, 43,
  47, 49). PASS: all four as written; corrections go into the findings.
- **D2 Mux-leakage rules (NEXT_REVISION 4c).** Every output: op-amp → ≤ 100 Ω → J2, ≤ 100 pF at the pin, no large
  capacitor behind a large resistor. FINDINGS 11.5 gives < 0.02 LSB for VAC / DC_LINK and ≈ 0 for AUX / 5V at
  ≥ 2 µs dwell. PASS: netlist agrees with what was simulated (R65 100, R2 100, R132 100, R135 100; no
  output capacitors).
- **D3 Supply decoupling.** U8: C60 2.2 µF (36, 11); U6: which capacitor (C62 2.2 µF at (20, −2)?); U10: C133
  (43, −4). `rv bq padgap U8.5 C60.1`, `rv bq padgap U6.5 C62.1`, `rv bq padgap U10.8 C133.1`. PASS: each op-amp
  has ≥ 100 nF within 5 mm of its V+ pin.
- **D4 TLV316 footprint.** U6 / U8 are on the 5.1 "Proteus" SOT-23-5 footprint (`tube_psu:SOT-23-5_Proteus`), U9 on
  the KiCad SOT-23-5. Pin order 1 OUT, 2 V−, 3 +IN, 4 −IN, 5 V+ in the netlist = TI DBV pinout. PASS: pad
  numbering of the Proteus footprint equals the standard SOT-23-5 numbering (`rv bq fp U6` pad positions: pads
  1 – 3 on one side, 4 – 5 on the other, pin 1 next to the pin-1 corner of the standard pattern mirrored for
  B.Cu) – same as on the working 5.1 board (`rv bq51 fp U6`).
- **D5 Output routing to J2.** `rv bq net VAC_MEAS DC_LINK_MEAS AUX_MEAS 5V_MEAS` and `rv bq near VAC_MEAS --within
  0.3`. PASS: short (they are all within 15 mm of J2), not parallel to PWM lanes within 0.3 mm for > 10 mm.
- **D6 5.1 → 5.2 changes present on the board.** C126, C127, C130, C131, C132, C133, R132 – R135, U10 placed and
  routed (`rv bq fp C126,C127,C130,C131,C132,C133,R132,R133,R134,R135,U10`); C4 gone; R2 = 100 Ω, R49 = R80 = 12 k
  in the BOM (`rv sch bom 9`, `rv sch bom 4`).

### E. Bring-up notes for the findings

- **E1** Expected readings with no mains and DC+ from a bench supply: VAC = 1.65 V (ADC ≈ mid-scale), DC_LINK =
  0.005 × V, AUX ≈ 2.64 V, 5V ≈ 2.00 V – a quick check of the whole chain and the J2 map.
- **E2** Scale factors for the firmware: VAC 0.004 V/V (was 0.005 in 5.1 with 15 k: firmware constant must
  change!), DC link 0.005, AUX 0.176, 5V 0.4. State prominently that **the VAC gain changed 5.1 → 5.2** and where
  that is documented for the firmware.

## 5. Out of scope / given

- REF1 / U9 bias generation, +3V3, J2 mechanics (checklist 04); current channels (08); isolated measurements (03);
  the PFC drivers on sheet 9 (05).
- Given: gains and filter values of CHANGES 4.2 – 4.5; AUX buffered (not the 1 µF option); 5V monitor added;
  ADC channel map; no silkscreen; via-in-pad accepted (R51 pad 2).

## 6. Findings format

Write `kicad_next/review/findings/09_voltage_measurement.md` exactly in the format of
`kicad_next/review/README.md` "Common findings format": summary; one table row per item above (A1 … E2) with
**PASS / FAIL / CANNOT VERIFY** and the evidence (file:line, command + output lines, calculation with inputs, or
datasheet document / page / URL); ranked findings with severity (**blocker for ordering / should fix / note**),
what is wrong, evidence, smallest fix, confidence; "Compared with 5.1"; "Could not verify"; "Outside scope".
"Looks fine" without evidence is not acceptable.
