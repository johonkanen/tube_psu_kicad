# Review checklist 03 – isolated measurements and digital isolators (AD1 / ISO1 heater side, AD2 / ISO2 420 V side)

You are reviewing **one part** of the tube_power 5.2 power-supply board, alone, from this file and the repository
`/home/jari/dev/tube_psu_kicad`. You are doing a design review, not a redesign.

**Rules (full text: `kicad_next/review/README.md`, "Common rules" – read that section first):**
read-only on the repository, the only file you write is `kicad_next/review/findings/03_isolated_measurements.md`; no
commit, no push; never touch `kicad_next/tube_psu_5_2.kicad_pcb` / `.kicad_pro` and never run a script that saves or
regenerates design files (`route_s*.py`, `update_board_parts.py`, `setup_project.py` / `make_board.py` / generators
without `--check`); stop if a KiCad lock file exists (`rv guard`); RAM under 3 GB – no board DRC, no
`check_next.sh` (use the existing reports); never `pkill -f`; never run the KiCad AppImage with `--version`; the
owner's name / e-mail stay out of web requests. **Acceptance bar: match the bench-verified 5.1 board and add
creepage – do not optimise beyond that.** Datasheet facts come from the datasheet you fetch now, not from memory.

## 1. Scope

Two output voltages are measured on their own isolated side by a 12-bit SPI ADC (ADC121S101, SOT-23-6) and read by
the FPGA through a six-channel digital isolator that also carries PWM signals across the barrier:

- **Heater side (ground HT_GND):** 6V3 → divider R54 15k / R55 6.8k → U2 (TLV316, gain 1 + R122 / R121) → R18 / C7 →
  **AD1**; supply 6V3 → D2 → D3 → **V3** MIC5205-3.3 → the "HT 3.3 V" net `Net-(AD1-VA)` (AD1 VA = reference, U2,
  ISO1 side 2). **ISO1** (CA-IS3761LW) carries $HT_CS, HT_CLK → AD1, AD1 SDATA → HT_SDATA, and SYNCH_1 / SYNCH_2 →
  EPWM5A_ISO / EPWM6A_ISO (the synchronous-rectifier gate commands for DRV4). Barrier primary ↔ heater: reinforced,
  8.0 mm creepage.
- **DAB secondary (ground ISO_GND):** 420V → R23 / R34 / R39 (3 × 1 MΩ) with R38 15k / C27 1.2 nF, reference leg
  ISO_GND → R118 – R120 (3 × 1 MΩ), U3 (TLV316 difference amplifier, R113 15k) → R13 / C5 → **AD2**; supply 5V_ISOL →
  **V2** MIC5205-3.3 → AD2_3V3. **ISO2** (CA-IS3761LW) carries $CUK_CS, CUK_CLK → AD2, SDATA → CUK_SDATA, EPWM2A /
  EPWM2B → ISO_SEC_DHB_HI / LO (DRV6 inputs) and, new in 5.2, DAB_DIS → DAB_DIS_SEC. Barrier primary ↔ DAB secondary:
  reinforced, 11.1 mm creepage (working voltage 552 Vrms / 778 Vpk).

5.1 used Si8661BD isolators; 5.2 uses the pin-compatible CA-IS3761LW (default-low outputs) in SOIC-16W footprints
with a milled slot under the body. ("CUK" in the net names is a leftover name for the anode / 420 V converter.)

- Sheet: `kicad_next/03_isolated_measurements.kicad_sch` (generator `tools/next/sheets/sheet03.py`, 29 parts) plus
  the dividers drawn on sheet 6 (R54, R55) and sheet 7 (R23, R34, R39, R38, C27, R118 – R120).
- Board: heater side at x −60 … −35, y −65 … −47 – ISO1 on F.Cu at (−42.4, −54.8) with a T-shaped slot, AD1 / U2 / V3
  on B.Cu at x −58 … −46; 420 V side at x 60 … 85, y −38 … −16 – ISO2 on F.Cu at (66.8, −26.6) with a 1.0 × 19.5 mm
  slot, AD2 / U3 / V2 on B.Cu at x 74 … 81, the 3 × 1 MΩ chains at (77 … 84, −22) F.Cu and (78 … 82, −23) B.Cu.

## 2. Read first

1. `tools/next/sheets/sheet03.py` (192 lines; notes at lines ≈ 182 – 190).
2. `kicad_next/CHANGES_5_2.md`: row "3a ISO1, ISO2" in section 3, row 3.3 (DAB_DIS through ISO2 channel C), "Open
   questions" item 2 (reinforced certificates pending).
3. `simulation/FINDINGS.md` section 5 (AD2 bandwidth 8.86 kHz) and 11.2 (ranges).
4. `kicad_next/README.md`: "Footprints and 3D models" table rows "ISO1, U11" and "ISO2" (slot footprints, surface
   paths 8.85 / 12.50 mm); "ISO2 / AD2 fan-out, 420V divider, R10 / R79 (routing stage 3d)"; "Stage 7" bullet
   "ISO2 pad 8"; "Isolation domains and creepage / clearance (D6)" table.
5. `kicad_next/J2_PINOUT.md` rows 7 – 16 and 18.
6. Design document p 20 (synchronous-rectifier control) and p 28 – 31 (`rv pdf 28 31`) for the SPI ADC use.
7. Datasheets to fetch: Chipanalog **CA-IS3761LW** (CA-IS376x family: pinout, default state, VIOWM / VIORM / VIOTM,
   CTI / material group, package creepage, data rate, propagation delay, supply range, safety certificates),
   TI **ADC121S101** (supply = reference, SCLK range, input capacitance, timing), TI **TLV316**, Microchip
   **MIC5205-3.3YM5** (input range, dropout, output capacitor / ESR requirement, noise-bypass pin), ZLLS400TA.

## 3. How to extract facts

```sh
kicad_next/review/tools/rv guard && kicad_next/review/tools/rv setup
kicad_next/review/tools/rv sch sheet 3
kicad_next/review/tools/rv sch ref ISO1,ISO2,AD1,AD2,U2,U3,V2,V3
kicad_next/review/tools/rv sch cmp51 3
kicad_next/review/tools/rv sch net HEATER_VOLTAGE_MEAS CUK_CAP_MEAS2 CUK_CAP_MEAS- "Net-(AD1-VA)" AD2_3V3 "Net-(D3-K)"
kicad_next/review/tools/rv sch ref R23,R34,R39,R38,C27,R118,R119,R120,R54,R55
kicad_next/review/tools/rv sch bom 3
kicad_next/review/tools/rv bq fp ISO1,ISO2
kicad_next/review/tools/rv bq area -60 -66 -34 -46        # heater-side parts (side F / B)
kicad_next/review/tools/rv bq area 58 -40 86 -14          # 420 V side parts
kicad_next/review/tools/rv bq slots                       # ISO2 slot x 66.26 … 67.26, ISO1 T slot x -42.86 … -41.86 / y -64.09 … -63.09
kicad_next/review/tools/rv bq padgap ISO2.8 ISO2.9        # pad row to pad row across the slot
kicad_next/review/tools/rv bq near @SEC --within 11.1 --other-domain --layer F.Cu
kicad_next/review/tools/rv bq near @HEATER --within 8.0 --other-domain
kicad_next/review/tools/rv bq net 420V "Net-(R23-Pad2)" "Net-(R34-Pad2)" CUK_CAP_MEAS2
kicad_next/review/tools/rv bq near "Net-(R23-Pad2)" --within 1.3
kicad_next/review/tools/rv bq net "Net-(AD2-Vin)" "Net-(AD1-Vin)" "Net-(AD2-CLK)" "Net-(AD1-CLK)"
python3 tools/next/check_domains.py kicad_next/tube_psu_5_2.kicad_pcb     # project's own domain-distance check (read-only, ~10 s, a few hundred MB; needs no other kipy job running)
kicad_next/review/tools/rv section kicad_next/README.md 'ISO2 / AD2 fan-out'
```

`near … --other-domain` lists straight distances; pairs across a slot are shorter than their creepage path – for
those, the footprint surface-path numbers of the README and `check_domains.py` (which follows the slots) are the
evidence.

## 4. Checklist

### A. Isolators ISO1 / ISO2

- **A1 Pin map and direction.** `rv sch ref ISO1,ISO2` against the CA-IS3761 datasheet (5 forward + 1 reverse
  channel, wide body): 1 VDDA, 2 – 6 inputs (side 1), 7 output (side 1), 8 GNDA, 9 GNDB, 10 input (side 2),
  11 – 15 outputs (side 2), 16 VDDB; channel pairs 2↔15, 3↔14, 4↔13, 5↔12, 6↔11, 10→7. PASS: every signal enters
  on an input and leaves on the matching output; the datasheet has no enable pin on pins 7 / 10 for this variant
  (some six-channel isolators do) – confirm from the ordering table that "3761" is 5/1 without enable.
- **A2 Default state.** The "L" suffix = outputs low when the input side is unpowered or open. List each channel
  and what low means: ISO1 – $HT_CS low (ADC selected), HT_CLK low, SYNCH_1 / SYNCH_2 low → DRV4 inputs low → SR
  FETs off; ISO2 – EPWM2A / 2B low → DRV6 inputs low → Q21 / Q8 off; DAB_DIS low → DRV6 **enabled**; CS / CLK low.
  PASS: no default state turns a power switch on. Compare with the Si8661**BD** default (5.1) from its
  datasheet ordering guide. Unused input ISO1 pin 2 is tied to GND and its output pin 15 is open – PASS.
- **A3 Supplies.** Side 1 +3V3 with C97 (ISO1) / C98 (ISO2); side 2 `Net-(AD1-VA)` 3.3 V (C59 / C104 / C83) and
  AD2_3V3 (C103 / C105 / C57). PASS: supply range of the CA-IS3761 covers 3.3 V on both sides, a 100 nF is within
  3 mm of each VDD / GND pin pair (`rv bq fp C97,C98,C103,C59` vs the ISO pins 1 / 8 and 16 / 9).
- **A4 Speed and skew.** SPI clock used by the FPGA for the ADC121S101 (datasheet fSCLK 10 – 20 MHz for the
  1 Msps grade): round-trip delay CLK out → isolator → ADC → SDATA → isolator must fit the half period; PWM
  channel-to-channel skew for the DAB (140 kHz, dead time 150 ns) and SR timing. PASS: 2 × t_pd(max) + ADC
  t_ACC < the SCLK period budget at the clock the firmware uses (find it in the design document p 28 – 31 or state
  the assumption), data rate rating ≥ 2 × SCLK; skew ≤ 50 ns (the dead-time margin of checklist 02).
- **A5 Isolation rating vs the barrier (known open point: certificates).** From the fetched datasheet: VIOWM,
  VIORM, VIOTM, VISO, external creepage / clearance of the wide-body package, CTI, and the certification status
  (VDE / UL / CQC). Requirements (README "Working voltages and numbers"): ISO2 552 Vrms / 778 Vpk reinforced;
  ISO1 318 – 333 Vrms reinforced. PASS: VIOWM ≥ 552 Vrms for reinforced insulation **and** a certificate
  number is given in the datasheet; if the datasheet still says "pending", verdict CANNOT VERIFY and a finding
  that names the document to obtain. Package creepage ≥ 8 mm: note that the package itself is below 11.1 mm –
  the README's position on that (the slot fixes the PCB path, not the package path) must be stated and judged.
- **A6 Slot footprints.** `lib/tube_psu_next_parts.pretty/SOIC-16W_7.5x10.3mm_P1.27mm_Slot11.1.kicad_mod` and
  `…_Slot8.0_T_ISO1.kicad_mod`: slot width 1.0 mm, lengths 19.5 / 14.5 mm (+ T bar for ISO1). Recalculate the
  shortest surface path pad row → round the slot end → pad row (documented 12.50 mm for ISO2, 8.85 mm for the
  Slot8.0 type) from the pad and slot coordinates (`rv bq fp ISO2`, `rv bq slots`). PASS: ≥ 11.1 mm (ISO2) and
  ≥ 8.0 mm (ISO1); slot ≥ 1.0 mm wide (IEC: a groove narrower than 1 mm does not count at PD2); JLC can mill a
  1.0 mm slot (README "JLC manufacturing limits" has no slot row – look up JLC's minimum slot width and state
  it); the remaining web of FR-4 at the slot ends does not weaken the board next to a mounting hole or edge.
- **A7 Nothing but the isolator crosses.** `rv bq near @SEC --within 11.1 --other-domain`, `rv bq near @HEATER
  --within 8.0 --other-domain` and `check_domains.py`. PASS: `check_domains.py` exits 0 with 0 pairs below the
  limit and 0 accepted pairs; every pair that `near` lists below 11.1 / 8.0 mm is separated by a slot and
  explained (give the list). The "Stage 7" note estimates 10.35 mm straight / 11.8 mm round the slot for
  `Net-(TR1-S15)` ↔ ISO2 pad 8 "not re-measured": re-measure it (`rv bq dist "Net-(TR1-S15)" ISO2.8 --layer F.Cu`
  plus the slot geometry).

### B. 420 V measurement (AD2)

- **B1 Divider and gain.** + leg: 420V – 3 MΩ – node CUK_CAP_MEAS2 – R38 15k ‖ C27 to ISO_GND; − leg: ISO_GND – 3 MΩ –
  node CUK_CAP_MEAS- – R113 15k to the U3 output. Calculate the transfer (expected 15 k / 3 M = 0.005 → 420 V =
  2.10 V, full scale 3.3 V = 660 V), compare with the PDF note quoted in `sheet04.py` for the DC link ("663 / 3V3")
  and FINDINGS 11.2. PASS: 420 V + 10 % and the highest transient the firmware must see stay below
  full scale; resolution stated (V / LSB at 12 bit).
- **B2 Resistor stress.** 420 V / 3 → 140 V per 1 MΩ 0805 (R23, R34, R39): rated working voltage of the LCSC part
  (`rv sch part R23`), power 20 mW. PASS: ≤ rated voltage with the 420V rail at its maximum (use 450 V);
  the 5.1 part was the same (`rv sch51 ref R23`).
- **B3 Creepage along the chain.** `rv bq fp R23,R34,R39`, `rv bq near "Net-(R23-Pad2)" --within 1.3`,
  `rv bq near 420V --within 1.3 --layer F.Cu`. PASS: functional spacing ≥ 1.2 mm between any two nodes of the
  chain that are not the two pads of one resistor, and from the 420 V end to ISO_GND / low-voltage copper;
  nothing low-voltage routed under the resistor bodies on the same layer.
- **B4 Amplifier and filter.** U3 TLV316 on AD2_3V3: input common mode (≈ 2.1 V at 420 V) inside the range at
  3.3 V supply, output swing to 3.3 V − margin, R13 1k / C5 1 nF against the ADC121S101 sampling input
  (datasheet: source impedance / sampling capacitor, track time). Bandwidth 8.86 kHz (FINDINGS 5) is
  accepted – check only that the control model value is still right for the 5.2 values (unchanged from 5.1:
  `rv sch cmp51 3` shows no value change). PASS: settled to < 1 LSB within the acquisition time at the
  sample rate used.
- **B5 Reference = supply.** The ADC121S101 uses VA as reference: V2 MIC5205-3.3 accuracy (± %) and noise set the
  420 V measurement accuracy. MIC5205 needs an output capacitor inside an ESR window (datasheet stability
  section): C57 2.2 µF ceramic 0603 + 100 nF – check. PASS: output capacitor value / ESR meets the datasheet
  stability condition (if the datasheet requires ≥ some ESR for ceramics, say so), C34 470 pF on the bypass
  pin allowed, V_in 5V_ISOL (4.8 – 5.35 V) − dropout > 3.3 V.

### C. Heater voltage measurement (AD1)

- **C1 Divider and gain.** 6V3 × R55 / (R54 + R55) × (1 + R122 / R121) (6.8k / 15k divider, 6.8k / 15k feedback).
  Expected ≈ 6.3 V → 2.86 V, full scale 3.3 V ≈ 7.3 V. PASS: the highest heater voltage that must be measured
  (soft start overshoot, no-load) is below full scale, or the clipping level is documented; same values as 5.1.
- **C2 Supply chain.** 6V3 → D2 → D3 (two ZLLS400 in series) → C13 → V3 → 3.3 V. Calculate V3 input at 6.3 V and at
  the lowest heater voltage at which the measurement (and the SR drive through ISO1 side 2!) must work: ISO1
  side 2 and AD1 are dead until 6V3 exceeds ≈ 3.3 V + dropout + 2 diode drops. PASS: document the 6V3 level at
  which EPWM5A_ISO / EPWM6A_ISO become valid and check with checklist 06's start-up (SR FETs conduct through
  their body diodes until then) – same as 5.1, so PASS unless a 5.2 change (UCC27524A UVLO 4.x V on 6V3 vs the
  old IXDD604) alters the sequence; state the result.
- **C3 Why two diodes.** State the purpose found in the documents (hold-up of the measurement supply against
  6V3 ripple / reverse blocking) or mark as unknown; check D2 / D3 reverse voltage and the C13 1 µF hold-up.
  Not a FAIL item unless a rating is exceeded.
- **C4 U2 / R18 / C7** as B4 for the heater channel (R18 100 Ω, C7 1 nF).

### D. Layout

- **D1 Analog input routing.** `rv bq net "Net-(AD2-Vin)" "Net-(AD1-Vin)" CUK_CAP_MEAS2 CUK_CAP_MEAS-`. PASS: the
  high-impedance nodes (15 kΩ level) are short (≤ 15 mm), not parallel to SPI clock or PWM lanes on the same or
  the adjacent layer for more than 5 mm, and C27 / R38 sit at U3, not at the 1 MΩ chain.
- **D2 420 V sense feed.** README stage 3d laid "the 420V sense divider as a row with its feed". `rv bq net 420V`
  (narrowest segments) and the feed to R23 pad 1. PASS: ≥ 1.2 mm to ISO_GND / LV copper on outer layers, the feed
  does not run on an inner layer under the low-voltage AD2 circuit without ≥ 0.5 mm spacing and a plane between.
- **D3 Ground of the ADC side.** AD2 / U3 / V2 sit over the ISO_GND planes (In1 / In4) and AD1 / U2 / V3 over HT_GND:
  `rv bq xsec ISO_GND In1.GND y -33 70 86`, `rv bq xsec HT_GND In1.GND y -57 -60 -44`. PASS: continuous plane
  under each ADC group; each decoupling capacitor has its own via to the plane.
- **D4 Heater island currents.** The heater side carries 10 – 15 A in HT_GND / 6V3 a few centimetres away. Check
  where AD1's HT_GND reference and the R54 / R55 divider tap the rails (`rv bq fp R54,R55`, `rv bq net
  HEATER_VOLTAGE_MEAS`): at the output terminals / output capacitors, or in the middle of the SR current path?
  PASS: sense point at the output side of C31 / C32 or documented as equal to 5.1 (`rv bq51 fp R54,R55,AD1`).
- **D5 Courtyard / assembly.** `python3 kicad_next/review/tools/drc_summary.py courtyards_overlap 58 -40 86 -14` and
  `… -60 -66 -34 -46`. PASS: no overlap of real bodies; SOT-23 / 0603 parts placeable on B.Cu.

### E. 5.1 → 5.2 changes touching this part

- **E1** Si8661BD → CA-IS3761LW: electrical differences that matter (default state, supply current, speed,
  input thresholds at 3.3 V, output drive into 8.2 k pull-downs R91 / R117 on sheet 6). PASS with the datasheet
  rows quoted.
- **E2** ISO2 channel C newly used for DAB_DIS: pin 4 was GND, pin 13 was open in 5.1 (`rv sch cmp51 3`). PASS:
  routed on the board (`rv bq net DAB_DIS DAB_DIS_SEC`), and J2-18 → ISO2 pin 4 does not load the DRV5 DISABLE
  filter (R129 / C120) in a harmful way.
- **E3** Slots added under ISO1 / ISO2: see A6; additionally the 5.1 board's copper that passed under the
  isolators is gone (`rv bq near ISO2.8 --within 1.0` shows only its own tracks).

### F. Bring-up notes for the findings

- **F1** How to verify each ADC without high voltage: inject a DC level at the divider tap; expected codes.
- **F2** Sequence dependence: AD1 / ISO1 side 2 only live when the heater output is up; AD2 / ISO2 side 2 only when
  5V_ISOL is up (flyback). What the FPGA reads before that (SDATA default low).

## 5. Out of scope / given

- DRV6 and the gate signals after ISO2 (checklist 02); DRV4 / SR timing (06); the UART isolator U11 (04);
  whole-board creepage rules and their basis (10); the J2 pin map (04).
- Given: CA-IS3761LW with default-low outputs; reinforced barrier numbers 11.1 / 8.0 mm; ISO_GND earthed through the
  amplifier chassis; AD2 bandwidth as is; no silkscreen; via-in-pad accepted (AD1 / AD2 pad 3, C57 pad 2).

## 6. Findings format

Write `kicad_next/review/findings/03_isolated_measurements.md` exactly in the format of
`kicad_next/review/README.md` "Common findings format": summary; one table row per item above (A1 … F2) with
**PASS / FAIL / CANNOT VERIFY** and the evidence (file:line, command + output lines, calculation with inputs, or
datasheet document / page / URL); ranked findings with severity (**blocker for ordering / should fix / note**),
what is wrong, evidence, smallest fix, confidence; "Compared with 5.1"; "Could not verify"; "Outside scope".
"Looks fine" without evidence is not acceptable.
