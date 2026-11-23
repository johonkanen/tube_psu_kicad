# Review checklist 08 – shunt current measurement chains (R93 / R21 / R83 / R30 → U4 / U1 → J2)

You are reviewing **one part** of the tube_power 5.2 power-supply board, alone, from this file and the repository
`/home/jari/dev/tube_psu_kicad`. You are doing a design review, not a redesign.

**Rules (full text: `kicad_next/review/README.md`, "Common rules" – read that section first):**
read-only on the repository, the only file you write is `kicad_next/review/findings/08_current_measurement.md`; no
commit, no push; never touch `kicad_next/tube_psu_5_2.kicad_pcb` / `.kicad_pro` and never run a script that saves or
regenerates design files (`route_s*.py`, `update_board_parts.py`, `setup_project.py` / `make_board.py` / generators
without `--check`); stop if a KiCad lock file exists (`rv guard`); RAM under 3 GB – no board DRC, no
`check_next.sh` (use the existing reports); never `pkill -f`; never run the KiCad AppImage with `--version`; the
owner's name / e-mail stay out of web requests. **Acceptance bar: match the bench-verified 5.1 board and add
creepage – do not optimise beyond that.** Datasheet facts come from the datasheet you fetch now, not from memory.

## 1. Scope

Four converter currents are measured with **4 mΩ shunts (Susumu KRL2012, 0508 wide-terminal) in the source / return
path to the primary GND** and amplified by difference amplifiers around the mid-scale bias **+1V65_BIAS**, so that
both current directions are measured (the DAB is bidirectional; the PFC control uses AC current, design document
p 13 – 14). The outputs go to the FPGA card's muxed 14-bit ADCs (0 – 3.3 V) through J2:

| Channel | Shunt (position) | Amplifier | Input R / feedback | Gain, scale | Output network | J2 pin |
|---|---|---|---|---|---|---|
| PFC leg Q5 | R93 (3.8, −16.1) B.Cu, net "PFC CURRENT 2+" | U4A | R33 330 / R60 6.8k to bias; R97 330 to GND / R98 6.8k feedback; C106 / C113 20 pF | 20.6 → 82 mV/A, ± 20 A | R96 100 Ω + C88 100 pF | 42 PFC_I1_MEAS |
| PFC leg Q6 | R21 (14.5, −8.0) B.Cu, "PFC CURRENT 3+" | U4B | R62 / R100; R94 / R95; C107 / C112 20 pF | same | R61 100 Ω + C77 100 pF | 44 PFC_I2_MEAS |
| DAB primary | R83 (15.9, −64.0) F.Cu, DHB_CURRENT | U1B | R104 330 / R105 15k; R101 330 / R102 15k; C122 / C63 12 pF | 45.5 → 182 mV/A, ± 9 A | R42 33 Ω (C26 not fitted) | 38 DHB_I_MEAS |
| Heater LLC primary | R30 (−10.7, −80.4) B.Cu, HEATER_CURRENT | U1A | R106 330 / R103 33k; R29 330 / R89 33k; C123 / C11 5.6 pF | 100 → 0.4 V/A, ± 4.1 A | R35 33 Ω (C10 not fitted) | 45 HEATER_I_MEAS |

(Verify this table against the netlist – it is the reviewer's first item.) U1, U4 = **LMH6643** (5.1: LMH6658) dual
op-amp, VSSOP-8 on the TSSOP-8 3 × 3 mm footprint, supply +3V3. New in 5.2: the op-amp type, the bias buffer U9
(checklist 04), shunt-inductance compensation capacitors on both legs (C122, C123 new; C63 20 → 12 pF, C11
20 → 5.6 pF), local decoupling C124 / C125 at U1, the J2 pin moves (PFC_I1 → 42, DHB_I → 38), and the shunts' new
places next to Q7 / in the heatsink line.

- Sheets: `08_current_measurement.kicad_sch` (`tools/next/sheets/sheet08.py`, 19 parts: U1 and its parts),
  `10_pfc_current_measurement.kicad_sch` (`sheet10.py`, 18 parts: U4); the shunts themselves are drawn on sheets 5
  (R93, R21), 6 (R30) and 7 (R83).
- Board: U4 on B.Cu at (22.0, −11.0) with its parts at x 18 … 30, y −17 … −7; U1 on B.Cu at (5.4, −59.9) with its
  parts at x 0 … 9, y −64 … −54 (**under the primary heatsink line, between Q7 and DRV5**); output resistors at J2:
  R96 / C88 (30, 4 … 6), R61 / C77 (30, −1) / (36, 4), R42 (29, 0), R35 (31, 8).

## 2. Read first

1. Design document p 13 – 14 (`rv pdf 13 14`): shunt in the source, gate current visible, sample timing.
2. `tools/next/sheets/sheet08.py`, `sheet10.py` (short; notes at the end).
3. `kicad_next/CHANGES_5_2.md` section "4. Measurements" rows 4.6, 4.7, 4.9, 4.10b, 4.11, 4b; "Open questions" 7.
4. `NEXT_REVISION.md` section 4 rows 4.10b, 4.11 and sections 4b, 4c (mux interface rules, dwell times).
5. `simulation/FINDINGS.md` sections 1, 4, 6, 7, 9, and 11.1 – 11.5 (5.2 circuits: AC responses, ranges, shunt ESL
   compensation table, mux leakage) – `rv section simulation/FINDINGS.md '^## 11'`.
6. `simulation/dab/DAB_SIMULATION.md` 2.6 "DHB shunt R83: what the current measurement sees".
7. `kicad_next/README.md`: "Stage 4d: shunt R83 at Q7 pin 3", "Stage 7" (R83 vias), "J2 escapes and J2 nets
   (routing stage 3e)" (analog lines), "Stage 5a" / "5b" (small nets round U1), "First draft" → "Tight spots".
8. Datasheets to fetch: TI **LMH6643** (GBW, slew rate, input common-mode range and output swing at 2.7 – 3.3 V
   supply, Vos, Ib, supply current, capacitive-load drive), TI LMH6658 (for the comparison), Susumu **KRL2012**
   (4 mΩ: power rating, TCR, inductance, recommended land pattern with sense connections), and the 5 mΩ
   KRL2012E-M-R005 (LCSC C2073455).

## 3. How to extract facts

```sh
kicad_next/review/tools/rv guard && kicad_next/review/tools/rv setup
kicad_next/review/tools/rv sch sheet 8
kicad_next/review/tools/rv sch sheet 10
kicad_next/review/tools/rv sch ref U1,U4,R93,R21,R83,R30
kicad_next/review/tools/rv sch cmp51 8
kicad_next/review/tools/rv sch cmp51 10
kicad_next/review/tools/rv sch net "PFC CURRENT 2+" "PFC CURRENT 3+" DHB_CURRENT HEATER_CURRENT
kicad_next/review/tools/rv sch net PFC_I1_MEAS PFC_I2_MEAS DHB_I_MEAS HEATER_I_MEAS +1V65_BIAS
kicad_next/review/tools/rv sch bom 8
kicad_next/review/tools/rv sch bom 10
kicad_next/review/tools/rv sch part R83,U1,C63,C122
kicad_next/review/tools/rv bq fp R93,R21,R83,R30,U1,U4
kicad_next/review/tools/rv bq area 16 -18 31 -6         # U4 group
kicad_next/review/tools/rv bq area -1 -65 10 -53        # U1 group
kicad_next/review/tools/rv bq net "PFC CURRENT 2+" "PFC CURRENT 3+" DHB_CURRENT HEATER_CURRENT
kicad_next/review/tools/rv bq net "Net-(U4A-+)" "Net-(U4A--)" "Net-(U4B-+)" "Net-(U4B--)" "Net-(U1A-+)" "Net-(U1A--)" "Net-(U1B-+)" "Net-(U1B--)"
kicad_next/review/tools/rv bq net PFC_I1_MEAS PFC_I2_MEAS DHB_I_MEAS HEATER_I_MEAS
kicad_next/review/tools/rv bq net "Net-(C63-Pad1)" "Net-(C11-Pad1)" "Net-(C112-Pad1)" "Net-(C113-Pad1)"
kicad_next/review/tools/rv bq pads GND | grep -E "R97|R94|R101|R29|R93|R21|R83|R30|U1\.|U4\."
kicad_next/review/tools/rv bq near HEATER_CURRENT --within 0.6 --layer In2
kicad_next/review/tools/rv bq near DHB_CURRENT --within 0.6 --layer In2
kicad_next/review/tools/rv bq near "Net-(U1B-+)" --within 0.5
kicad_next/review/tools/rv bq near HEATER_I_MEAS --within 0.4
kicad_next/review/tools/rv bq padgap U1.8 C124.1        # decoupling at the op-amp supply pin
kicad_next/review/tools/rv bq padgap U4.8 C87.1
kicad_next/review/tools/rv bq51 fp R93,R21,R83,R30,U1,U4
kicad_next/review/tools/rv bq51 net DHB_CURRENT HEATER_CURRENT
python3 kicad_next/review/tools/drc_summary.py courtyards_overlap -1 -65 10 -53
kicad_next/review/tools/rv section simulation/FINDINGS.md '11.4 Shunt ESL'
```

To follow a sense track, `rv bq net NET` prints the narrowest segments with coordinates per layer and the vias;
the sense line is the 0.15 – 0.25 mm part, the power part is the pour / wide track of the same net.

## 4. Checklist

### A. Schematic and transfer functions

- **A1 The table of section 1.** Rebuild it from `rv sch sheet 8`, `rv sch sheet 10` and the shunt nets. For each
  channel: shunt → 330 Ω → non-inverting input with Rb to +1V65_BIAS (and C across Rb); inverting input: 330 Ω to
  **GND** and feedback R (‖ C) from the output; output through the series resistor to J2.
  V_out = 1.65 V + I · R_shunt · (R_fb / 330). PASS: table confirmed (values, pins, J2 pin numbers per
  `kicad_next/J2_PINOUT.md`), and **the sign**: positive V_out excursion for current flowing from the switch
  source into GND (PFC: Q conducting; DAB: Q7 conducting / positive power flow?; heater: Q10 conducting) –
  state the sign for each channel and that it equals 5.1 (`rv sch cmp51 8`, `rv sch cmp51 10` show no topology
  change).
- **A2 Which PFC channel is which.** "PFC CURRENT 2+" = Q5 source (leg AC1 / L2, PWM1) → U4A → **PFC_I1_MEAS**;
  "PFC CURRENT 3+" = Q6 source → U4B → **PFC_I2_MEAS**. The net numbers (2+, 3+) and the signal numbers (I1, I2)
  do not match by name – confirm by netlist and against 5.1; the J2 pin of PFC_I1 moved 43 → 42. PASS: same
  switch ↔ channel pairing as 5.1; the firmware note in CHANGES 4b (ADA4 = PFC_I1) is consistent.
- **A3 Ranges.** With 4 mΩ: ± 20 A (PFC), ± 9.1 A (DAB), ± 4.1 A (heater primary) for ± 1.65 V; LMH6643 output
  swing at 3.3 V supply into the mux load (datasheet: within ≈ 40 – 100 mV of the rails at light load) reduces
  that slightly. Compare with the peaks: PFC DCM peak (checklist 05: several A to ≈ 10 A), DAB peak (≈ 4 A at
  400 W, more in transients / at 3 A peak load), heater primary peak (≈ 0.75 A at 15 A out, × 2 cold start).
  FINDINGS 11.2 has the simulated ranges. PASS: every expected peak ≤ 80 % of full scale; resolution per LSB
  (14 bit, 201 µV) stated for each channel.
- **A4 Input common-mode range.** Both op-amp inputs sit at ≈ 1.65 V × 330 / (330 + R_fb) + … ≈ 1.57 – 1.63 V. LMH6643
  input common-mode range at V+ = 3.3 V (datasheet, 2.7 V and 5 V tables: CMVR typically from V− − 0.2 V to
  V+ − 1.2 … 1.3 V). PASS: 1.63 V + the largest signal excursion at the inputs ≤ CMVR(max) at 3.3 V over
  temperature; if the datasheet only specifies 2.7 V and 5 V, interpolate and say so.
- **A5 Bandwidth / noise gain.** Noise gain = 1 + R_fb / (330 ‖ …) ≈ 21.6 / 46.5 / 101; LMH6643 GBW (datasheet; the
  project uses 57 MHz) → closed-loop bandwidth ≈ 2.6 MHz / 1.2 MHz / 0.56 MHz, combined with the R_fb · C poles
  (6.8k · 20p = 1.17 MHz, 15k · 12p = 0.88 MHz, 33k · 5.6p = 0.86 MHz). Settling to 1 LSB after a switching edge
  vs the ADC sample position (NEXT_REVISION 4c rule 4: ADC A ≥ 2 µs, ADC B ≥ 3 µs before HEATER_I).
  PASS: consistent with FINDINGS 11.1 / 11.5; the 5.2 values are not slower than 5.1 in a way that breaks the
  140 kHz three-channel sampling (2.38 µs per channel).
- **A6 Shunt-ESL compensation (CHANGES 4.11, open question 7: "start values, tune on the bench").** FINDINGS 11.4:
  20 p / 12 p / 5.6 p give no spike up to 0.8 nH. Both legs must be balanced: C across Rb (bias leg) = C across
  R_fb. PASS: C106 = C113 = 20 p, C107 = C112 = 20 p, C122 = C63 = 12 p, C123 = C11 = 5.6 p in the netlist and the
  BOM (C0G); the capacitor on the + leg returns to +1V65_BIAS (not GND).
- **A7 Offset.** LMH6643 Vos max (datasheet at 25 °C and over temperature) referred to the shunt: Vos / 4 mΩ
  (≈ 0.86 A at 3.4 mV; 1.8 A at 7 mV) – larger than 5.1's LMH6658? Input bias current × 330 Ω mismatch.
  The documents rely on zero-current calibration at start-up (sheet note; CHANGES 4.10b). PASS: calibration is
  possible in every channel (a moment with zero current exists: PFC and DAB off before start; heater off), and
  the offset drift over temperature after calibration (TCVos × ΔT / 4 mΩ) is stated and compared with the
  control accuracy needed (PFC current loop: a few %; say what you assumed).
- **A8 Output networks vs the mux (NEXT_REVISION 4c).** PFC: 100 Ω + 100 pF; DAB / heater: 33 Ω, C26 / C10 "na"
  (footprints present, not fitted: `rv sch part C10,C26` status dnp). LMH6643 capacitive-load stability with
  100 pF behind 100 Ω and with the mux C_D 40 pF + trace behind 33 Ω. PASS: follows rule 1 of 4c; C10 / C26
  marked DNP in the BOM / assembly data.
- **A9 Decoupling (CHANGES 4.6).** U1: C124 100 nF + C125 1 µF at pin 8; U4: which capacitors? (C87 1 µF is listed
  on sheet 10 at (5.7, −59.4) – that is next to **U1**, not U4 at (22, −11): check which op-amp C87 really serves
  on the board and what decouples U4 pin 8: `rv bq padgap U4.8 C87.1`, `rv bq area 16 -18 31 -6`; a +3V3 capacitor of sheet 4, C76 at (24, −9), stands
  next to U4: `rv bq padgap U4.8 C76.1`.) PASS: each
  op-amp has ≥ 100 nF within 3 mm of pin 8 with a short GND return to pin 4. **FAIL (should fix) if U4 has no
  local capacitor** – compare with 5.1 first (`rv bq51 fp U4,C87`).
- **A10 5 mΩ shunt option.** The 4 mΩ KRL2012 is not available at JLC (parts table: "consign the 4 mΩ part or
  accept 5 mΩ: +25 % gain"). With 5 mΩ: ranges ± 16 A / ± 7.3 A / ± 3.3 A, ESL compensation τ changes (L / R),
  dissipation +25 %. PASS: the findings state which value the BOM builds (consigned 4 mΩ per the table) and
  that a silent substitution would shift every current scale; nothing else to do.
- **A11 Shunt dissipation and pulse load.** P = I_rms² · R: PFC leg ≈ (3 – 4 A rms)² · 4 mΩ ≈ 50 mW, DAB 2.4 A →
  23 mW, heater 0.7 A → 2 mW; inrush / fault peaks. KRL2012 rating (datasheet, ≈ 1 W class). PASS trivially;
  note the numbers.

### B. Layout – Kelvin connection and returns (the part that changed most)

- **B1 Kelvin take-off at each shunt.** For R93, R21, R83, R30: the + sense track must leave from the shunt's
  source-side pad (pad 1) itself, and the − reference of the amplifier (the 330 Ω "to GND": R97, R94, R101, R29)
  should see the shunt's GND pad potential, not a plane point centimetres away that carries power return
  current. `rv bq net "PFC CURRENT 2+"` etc. (sense track start coordinates vs `rv bq fp R93` pad 1), and
  `rv bq pads GND | grep -E "R97|R94|R101|R29|R93|R21|R83|R30"` for the positions of the two GND ends. Distances:
  R93 pad 2 (3.8, −15.6) ↔ R97 at U4 (≈ (22, −8)): ≈ 20 mm of GND plane; R83 pad 2 (15.9, −64.5) ↔ R101 (2, −58):
  ≈ 15 mm; R30 pad 2 (−10.2, −80.4) ↔ R29 (3, −58): ≈ 26 mm – all through the In1 / In4 planes that also carry the
  bridge return currents. Estimate the error: plane sheet resistance (0.5 oz: ≈ 1 mΩ / square, two planes) ×
  the share of the power current flowing between the two points, against 4 mΩ of signal. **Compare with 5.1**
  (`rv bq51 fp R93,R21,R83,R30,U1,U4`, `rv bq51 pads GND | grep -E "R97|R94|R101|R29"`): was the reference taken
  the same way (pseudo-differential to the plane)? PASS: same method as 5.1 and the distance shunt-GND ↔
  amplifier-GND is not more than ≈ 1.5 × 5.1's for each channel; otherwise finding with numbers (the smallest
  fix would be a dedicated sense-return track for the 330 Ω of that channel).
- **B2 Sense tracks on In2.** DHB_CURRENT has 15 mm of 0.2 mm + 15 mm of 0.254 mm on In2 **and 22.7 mm of 1.2 mm** on
  In2; HEATER_CURRENT 22.7 mm on In2; the PFC sense lines 14.6 / 17.7 mm on In2. `rv bq near HEATER_CURRENT --within
  0.6 --layer In2`, `rv bq near DHB_CURRENT --within 0.6 --layer In2`. These pass under / beside the DAB primary
  pin column (README "Stage 4a": lanes at y −53.75 … −56.5 between Q19 pin 3 and Q7 pin 1). PASS: each sense lane
  has GND plane directly above (In1) **and** the next signal layer below is not a switching net for more than
  5 mm (`rv bq xsec GND In1.GND` at the lane coordinates); the neighbours within 0.5 mm are quiet nets (5V,
  another sense line), not gate or PWM lanes; what is the 1.2 mm DHB_CURRENT track on In2 – a power return on
  the signal layer? (Report it to checklist 07 / 11 if it carries bridge current.)
- **B3 High-impedance nodes.** The eight summing nodes `Net-(U?x-+)` / `Net-(U?x--)`: 2 – 8 mm of track each
  (`rv bq net ...`). PASS: ≤ 10 mm each, both nodes of a pair of similar length (balance), ≥ 0.3 mm from
  switching or digital nets (`rv bq near "Net-(U1B-+)" --within 0.5`): the U1 group sits in the "tight spot"
  the README lists (control bus lanes at 0.152 mm gaps round DRV5, bias via 0.164 mm from $HT_CS / SYNCH_2).
- **B4 U1 under the heatsink line.** U1 at (5.4, −59.9) B.Cu with C87 on F.Cu at (5.7, −59.4) – a known open input
  ("heatsink footprint and height against C87"). Electrically: the switch-node copper of the DAB primary
  (F.Cu zone x 11.8 … 31, y −61.7 … −50.6) and the Q7 pins at x 12.75 are 5 – 7 mm from U1's inputs.
  `rv bq dist DHB_HI_SOURCE "Net-(U1B-+)"`, `rv bq dist DHB_HI_SOURCE "Net-(U1A-+)"`. Estimate capacitive
  injection: C (≈ 10 – 50 fF) × dv/dt (400 V / 20 ns) × node impedance (330 Ω ‖ R_fb ≈ 320 Ω) → mV at the input ×
  gain. PASS: a GND plane (In1) lies between the F.Cu switch node and the B.Cu amplifier everywhere
  (`rv bq xsec GND In1.GND y -58 -2 12`, `rv bq xsec GND In4.GND y -58 -2 12`), and the estimated spike after
  the amplifier is ≤ 1 % of full scale 1 µs after the edge; else note for the bench.
- **B5 Output lines to J2.** DHB_I_MEAS, HEATER_I_MEAS, PFC_I1 / I2: series resistor at the J2 end or at the
  op-amp? (R42 (29, 0), R35 (31, 8), R96 (30, 4), R61 (30, −1) are at J2; so the amplifier output drives
  30 – 70 mm of track before the resistor: `rv bq net "Net-(C63-Pad1)" "Net-(C11-Pad1)"` – length, layer.)
  LMH6643 driving ≈ 5 – 8 pF of trace directly: fine. Crosstalk: `rv bq near HEATER_I_MEAS --within 0.4` and the
  README "First draft" clearance list (Net-(C11-Pad1) via 0.204 mm from +1V65_BIAS / R65 / Net-(C127-Pad1)).
  PASS: analog output lines are not parallel to PWM / SPI lanes within 0.3 mm for more than 10 mm on the same
  layer, or the coupling estimate is ≤ 1 LSB at the sample time.
- **B6 Decoupling geometry.** `rv bq padgap U1.8 C124.1`, `C125`, `rv bq padgap U4.8 C76.1`. PASS as A9.
- **B7 Footprint.** LMH6643MMX is VSSOP-8 (3 × 3 mm body, 0.65 mm pitch, 4.9 mm lead span) on
  `Package_SO:TSSOP-8_3x3mm_P0.65mm` (pads 1.1 mm long; README: "user-accepted"). Check the land pattern
  against the TI package drawing (DGK): pad centre-to-centre across the body and pad length give toe / heel
  fillets ≥ 0.1 mm. PASS or note.
- **B8 Shunt land pattern.** `rv bq fp R83`: pads 0.35 × 2.0 mm, 0.975 mm apart (KRL2012: terminals on the long
  sides). Compare with the Susumu recommended land pattern for KRL2012 (pad width, gap, and whether separate
  sense lands are recommended). Via-in-pad at R83 pad 1, R93 pad 2, R21 pad 1 (accepted process): do the vias
  sit in the **current** path or in the sense path? PASS: pattern within the datasheet recommendation; sense
  via not shared with the power current.

### C. 5.1 → 5.2 changes (explicit)

- **C1** LMH6658 → LMH6643: same pinout (dual, 1 OUT A, 2 −, 3 +, 4 V−, 5 +, 6 −, 7 OUT B, 8 V+ – confirm from both
  datasheets), differences in GBW / slew / Vos / CMVR / supply current listed. PASS: no parameter makes a channel
  worse than 5.1 beyond what FINDINGS 11 already evaluated (HEATER_I gain error at noise gain 101: 5.1 0.18 %,
  now?).
- **C2** C122 / C123 added, C63 / C11 changed: present on the board next to their resistors (`rv bq fp C122,C123,C63,C11`,
  `rv bq fp R105,R103,R102,R89`).
- **C3** C124 / C125 added at U1 (A9).
- **C4** J2 pins: PFC_I1_MEAS on 42, DHB_I_MEAS on 38; pins 37, 43 (old places) now GND / AUX_MEAS
  (`rv sch ref J2` rows 37 – 45). PASS: the board routing agrees (no stub of the old route: the DRC report shows 0
  dangling – `python3 kicad_next/review/tools/drc_summary.py`).
- **C5** R83 moved to Q7 pin 3 (README "Stage 4d") and R93 / R21 follow the heatsink line: B1 per channel.

### D. Bring-up notes for the findings

- **D1** Zero calibration procedure and the expected raw offsets (± Vos × gain: up to ± 150 mV at gain 20.6 … ± 0.7 V
  at gain 100 → the heater channel can lose a third of its range to offset: state it).
- **D2** Bench tuning hooks: which capacitors to change for ESL tuning (FINDINGS 11.4), where to probe (output
  resistor pads at J2), and the line-frequency bias coupling figure (FINDINGS 11.3: 29 mA on PFC_I).

## 5. Out of scope / given

- The bias generator REF1 / U9 and the J2 pin table (checklist 04); voltage chains (09); power paths through the
  shunts (05, 06, 07, 11); the heatsink mechanics over U1 / C87 (12); shunt sourcing (13).
- Given: LMH6643 (the INA296 option was not taken); 4 mΩ consigned shunts; bidirectional measurement around
  1.65 V; ADC channel map of CHANGES 4b; C10 / C26 not fitted; the ESL capacitor values are bench start values;
  no silkscreen; via-in-pad accepted (R83 pad 1, R93 pad 2, R21 pad 1, R89 pad 1, R103 pad 1, U1 pad 4, C125 pad 2).

## 6. Findings format

Write `kicad_next/review/findings/08_current_measurement.md` exactly in the format of
`kicad_next/review/README.md` "Common findings format": summary; one table row per item above (A1 … D2) with
**PASS / FAIL / CANNOT VERIFY** and the evidence (file:line, command + output lines, calculation with inputs, or
datasheet document / page / URL); ranked findings with severity (**blocker for ordering / should fix / note**),
what is wrong, evidence, smallest fix, confidence; "Compared with 5.1"; "Could not verify"; "Outside scope".
"Looks fine" without evidence is not acceptable.
