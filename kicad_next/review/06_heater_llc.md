# Review checklist 06 – heater supply: half-bridge LLC (Q10 / Q11, DRV3, TR2) with synchronous rectifier (Q1 / Q2, DRV4)

You are reviewing **one part** of the tube_power 5.2 power-supply board, alone, from this file and the repository
`/home/jari/dev/tube_psu_kicad`. You are doing a design review, not a redesign.

**Rules (full text: `kicad_next/review/README.md`, "Common rules" – read that section first):**
read-only on the repository, the only file you write is `kicad_next/review/findings/06_heater_llc.md`; no commit,
no push; never touch `kicad_next/tube_psu_5_2.kicad_pcb` / `.kicad_pro` and never run a script that saves or
regenerates design files (`route_s*.py`, `update_board_parts.py`, `setup_project.py` / `make_board.py` / generators
without `--check`); stop if a KiCad lock file exists (`rv guard`); RAM under 3 GB – no board DRC, no
`check_next.sh` (use the existing reports); never `pkill -f`; never run the KiCad AppImage with `--version`; the
owner's name / e-mail stay out of web requests. **Acceptance bar: match the bench-verified 5.1 board and add
creepage – do not optimise beyond that.** Datasheet facts come from the datasheet you fetch now, not from memory.

## 1. Scope

The heater supply makes **6.3 V at 10 A nominal (9.5 A worst-case tube set; the owner now quotes 10 – 15 A, and
150 – 200 % of nominal while the filaments are cold)** from the 400 V DC link with a half-bridge LLC whose series
inductance is the leakage of the transformer (design document p 16 – 22, p 33). Primary: Q11 (high side, drain
DC+) and Q10 (low side, source through the 4 mΩ shunt R30 to GND), both **IPD60R280P7S** DPAK (5.1: IPA60R280CFD7
TO-220 FullPAK); driver **DRV3 = UCC21520DWR** (5.1: Si8271 + IXDD609), INA = EPWM5A (J2-5) → high side, INB =
EPWM6A (J2-3) → low side, bootstrap D11 / R99 / C25, dead-time R130 10 k, DISABLE tied to GND. Resonant tank: split
capacitor C49 ‖ C42 (DC+ → `HEATER_CAP_MEAS`) and C41 ‖ C22 (`HEATER_CAP_MEAS` → HEATER_CURRENT), **4 × 3.3 nF C0G
630 V 1206 = 13.2 nF** (5.1: 4 × 4.7 nF X7R, about 12.5 nF at the 200 V bias), balancing resistors R155 – R158
4 × 220 k, with the **TR2** (EF25, "64 / 2 / 2" turns per the schematic note, with the note "check primary turns!")
leakage of 42 µH → resonance ≈ 214 kHz; operating range 150 – 270 kHz (p 20). Secondary on the heater domain
(ground HT_GND, reinforced barrier to the primary, 8.0 mm): centre tap = 6V3 output, the two winding ends
(`Q13_DRAIN`, `Q14_DRAIN`) go through the synchronous rectifiers Q2 / Q1 (**BUK9Y15-60E** LFPAK56) to HT_GND;
their gates are driven by **DRV4 = UCC27524A** (5.1: IXDD604) supplied from the 6V3 output itself, commanded by
EPWM5A_ISO / EPWM6A_ISO from isolator ISO1 (J2-13 SYNCH_1 / J2-9 SYNCH_2). Output capacitors C31, C32 (1500 µF 10 V)
plus 10 µF ceramics; terminals HT_6V3 / HT_GND.

- Sheet: `kicad_next/06_heaters.kicad_sch`, generator `tools/next/sheets/sheet06.py` (238 lines, 53 parts).
- Refdes: Q10, Q11, DRV3, D11, R99, C25, C52, C18, C53, R130, C121, R77, R78, R24, R59, D35, R36 (high-side gate),
  R37, R31, D33, R66 (low-side gate), C20, C22, C41, C42, C49, R155 – R158, R30, TR2, WP1 – WP4 (wire pads of the
  heavy secondary), Q1, Q2, DRV4, R63, R28, R107, R108, R91, R117, C17, C8, C9, C23, C24, C33, C31, C32, R54, R55,
  HT_6V3, HT_GND.
- Nets: `HEATER_HI_SOURCE` (switch node), `HEATER_CAP_MEAS` (capacitor mid point = transformer return),
  HEATER_CURRENT (low-side source / shunt top), `HEATER_HI_DRV`, `HEATER_HI_GATE`, `HEATER_LOW_DRV`,
  `HEATER_LOW_GATE`, `Net-(DRV3-VDDA)`, `Net-(D11-K)`, `Net-(D35-K)`, EPWM5A, EPWM6A; heater side: 6V3, HT_GND,
  `Q13_DRAIN`, `Q14_DRAIN`, `HEATER_SYNC_GATE_1/2`, EPWM5A_ISO, EPWM6A_ISO, `Net-(DRV4-OUTA/B)`.
- Board: north-west. Primary part x −26 … −6, y −90 … −45: Q11 (−13.8, −74.8), Q10 (−13.7, −63.1) on F.Cu, resonant
  capacitors on F.Cu along the top edge at (−16 … −8, −86), R30 (−11, −80) and DRV3 (−21, −55) on B.Cu. TR2 at
  (−30, −76): primary pins 1 / 2 / 4 / 5 on x −23.7, secondary pins 6 / 7 / 9 / 10 on x −36.4. Heater island
  x −70 … −38, y −90 … −60: wire pads WP1 – WP4 on x −42.8, Q2 (−53.2, −84.0), Q1 (−49.2, −69.1), DRV4 (−55, −68),
  C31 / C32 (−64, −76 / −68), terminals at x −68.

## 2. Read first

1. Design document p 16 – 22 and p 33 (`rv pdf 16 22`, `rv pdf 33`): requirement, transformer iterations (64 : 2 flat
   wound), resonance 220 kHz, control range, SR control by fixed conduction time, start-up current (100 A spike).
2. `tools/next/sheets/sheet06.py` (notes at lines ≈ 85 – 99, 155, 195 – 196, 236).
3. `kicad_next/CHANGES_5_2.md`: row "3a heater" (DRV3 / DRV9), "3a DRV4", rows 2.9 LLC and 2.8 LLC, row 5.4, the
   section "Transformer pins and winding tables" (TR2 table and the paragraph on dots), "Open questions" 9, 12.
4. `simulation/dab/DAB_SIMULATION.md` section 4 "Heater LLC: not simulated, data missing".
5. `NEXT_REVISION.md` rows 5.4 and "3a DRV3 + DRV9 / DRV4".
6. `kicad_next/README.md`: "Current and width" row "Heater LLC primary"; "Stage 3a.2" and "Stage 3a.3" (Q8 pin 2
   and the heater balancing chain); "User placement 2026-11-21, transformer pins" → "TR3 secondary finish on pins
   11 / 12, heater gate parts at their FETs"; "Stage 3f" (R77, 5V lane to DRV3); "Footprints" table row TR2.
7. Datasheets to fetch: Infineon **IPD60R280P7S** (and IPA60R280CFD7 for the comparison of Qrr / trr), TI
   **UCC21520**, TI **UCC27524A** (UVLO, input thresholds, enable pins), Nexperia **BUK9Y15-60E**, Holy Stone
   **C1206N332J631T** (C0G 630 V: rated AC voltage / current vs frequency), Rubycon **10ZLH1500MEFCT78X20** (ripple
   current), Samsung CL31A106KBHNNNE, Susumu KRL2012 4 mΩ, S1M, ZLLS400TA.

## 3. How to extract facts

```sh
kicad_next/review/tools/rv guard && kicad_next/review/tools/rv setup
kicad_next/review/tools/rv sch sheet 6
kicad_next/review/tools/rv sch ref DRV3,DRV4,TR2,Q1,Q2,Q10,Q11
kicad_next/review/tools/rv sch cmp51 6                  # driver, FET, capacitor, pin changes against 5.1
kicad_next/review/tools/rv sch net HEATER_HI_SOURCE HEATER_CAP_MEAS HEATER_CURRENT Q13_DRAIN Q14_DRAIN 6V3 HT_GND
kicad_next/review/tools/rv sch net EPWM5A EPWM6A EPWM5A_ISO EPWM6A_ISO SYNCH_1 SYNCH_2
kicad_next/review/tools/rv sch bom 6
kicad_next/review/tools/rv sch part C22,C31,Q10,TR2
kicad_next/review/tools/rv bq area -26 -91 -5 -44       # primary part
kicad_next/review/tools/rv bq area -71 -91 -37 -58      # heater island
kicad_next/review/tools/rv bq fp TR2,WP1,WP2,WP3,WP4,Q1,Q2,Q10,Q11,DRV3,DRV4
kicad_next/review/tools/rv bq nets '*HEATER*'
kicad_next/review/tools/rv bq net HEATER_HI_SOURCE HEATER_CAP_MEAS HEATER_CURRENT
kicad_next/review/tools/rv bq net HEATER_HI_DRV HEATER_HI_GATE HEATER_LOW_DRV HEATER_LOW_GATE "Net-(DRV3-VDDA)"
kicad_next/review/tools/rv bq net Q13_DRAIN Q14_DRAIN
kicad_next/review/tools/rv bq net 6V3
kicad_next/review/tools/rv bq net HT_GND
kicad_next/review/tools/rv bq neck DC+ F.Cu -13.838 -73.55 -10.3 -84.925    # Q11 drain tab -> C42 pad 1 (DC+ island of the tank)
kicad_next/review/tools/rv bq neck DC+ F.Cu -13.838 -73.55 20.2 -17.2       # Q11 drain tab -> bulk capacitor C56 on F.Cu alone
kicad_next/review/tools/rv bq neck HEATER_HI_SOURCE F.Cu -13.737 -61.812 -23.7 -66.08   # Q10 tab -> TR2 pin 1
kicad_next/review/tools/rv bq neck HEATER_CAP_MEAS F.Cu -23.7 -86.4 -10.3 -87.875       # TR2 pin 5 -> capacitor mid point (C42 pad 2)
kicad_next/review/tools/rv bq neck Q13_DRAIN F.Cu -36.4 -86.4 -53.165 -85.125           # TR2 pin 6 -> Q2 drain tab
kicad_next/review/tools/rv bq neck Q14_DRAIN F.Cu -36.4 -66.08 -49.2 -68.0              # TR2 pin 10 -> Q1 drain tab
kicad_next/review/tools/rv bq xsec 6V3 B.Cu x -60 -90 -60       # 6V3 copper across a north-south cut at x -60
kicad_next/review/tools/rv bq xsec 6V3 In3.Power x -60 -90 -60
kicad_next/review/tools/rv bq near HEATER_HI_SOURCE --within 1.3
kicad_next/review/tools/rv bq near HEATER_CAP_MEAS --within 1.3
kicad_next/review/tools/rv bq near @HEATER --within 8.0 --other-domain
kicad_next/review/tools/rv bq padgap TR2.1 TR2.10       # primary pin to secondary pin
kicad_next/review/tools/rv bq padgap C42.1 C42.2
kicad_next/review/tools/rv bq51 fp Q10,Q11,DRV3,TR2,C22,C41,C42,C49
kicad_next/review/tools/rv section kicad_next/CHANGES_5_2.md 'Transformer pins and winding tables'
kicad_next/review/tools/rv section simulation/dab/DAB_SIMULATION.md '^## 4'
```

## 4. Checklist

### A. Operating point and tank (calculations to do)

- **A1 Resonance.** fr = 1 / (2π √(Lr · Cr)) with Lr = 42 µH (leakage, measured on the 5.1 transformer per CHANGES
  2.9 – find where the 42 µH comes from and whether it is a measurement) and Cr = 4 × 3.3 nF = 13.2 nF (the two
  split halves are in parallel for AC). PASS: 210 – 220 kHz with C0G ± 5 %; state the spread with ± 10 % leakage
  and whether 150 – 270 kHz still brackets it as in 5.1.
- **A2 Capacitor stress at 15 A (CHANGES 2.9: "not calculated yet").** Primary current: I_pri,rms ≈ (π / (2√2)) ·
  I_out · (Ns / Np) + magnetising part, with Ns / Np = 2 / 64; at 10 A, 15 A and the 20 A cold-filament case.
  Each 3.3 nF part carries a quarter of it; AC voltage on the mid point V_pk = I_pk / (2π f Cr); DC + AC on each
  capacitor = 200 V ± V_pk. Compare with the Holy Stone C0G 630 V datasheet (allowed AC voltage / current /
  self-heating at 150 – 270 kHz) and with what the 5.1 X7R parts saw. PASS: peak ≤ 630 V with margin, rms current
  per part within the datasheet's limit (if the datasheet gives none, use ΔT from ESR/tan δ ≤ 20 K and say so).
- **A3 Value change 4.7 nF X7R → 3.3 nF C0G did what it says.** `rv sch ref C22,C41,C42,C49` = 3.3n; parts table
  `rv sch part C22` = C105987 C1206N332J631T C0G 630 V; CHANGES 2.9, the sheet note (sheet06.py:85) and
  DAB_SIMULATION.md section 4 agree. PASS: one consistent value everywhere; flag "stock / price not read".
- **A4 Balancing resistors.** R155 + R156 across the upper pair, R157 + R158 across the lower pair, 220 k each:
  100 V and 45 mW per resistor at 400 V; the lower chain ends on HEATER_CURRENT (not GND) – it adds
  400 V / 880 k ≈ 0.45 mA DC… through which path? (R155 – R158 are in series DC+ → HEATER_CURRENT → R30 → GND: the DC
  current flows through the shunt: 0.45 mA × 4 mΩ, negligible.) PASS: voltage per resistor ≤ the 1206 part's
  rating (C17956, 200 V), mid point settles to DC+ / 2, time constant R·C stated (start-up: firmware must wait).
- **A5 Transformer turns ("64 vs 66", "check primary turns!").** The schematic note says 64 / 2 / 2 with a warning;
  another working document reportedly says 66. Search the repository (`grep -rn "66" simulation/ STATUS.md
  NEXT_REVISION*.md kicad_next/*.md | grep -i "turn\|TR2\|prim"`) and the design document p 19 – 20 (32:1 ratio,
  64 / 2). Calculate the output voltage for both: V_out ≈ (V_DC / 2) · (Ns / Np) · M with M ≈ 1 at resonance:
  400 / 2 · 2 / 64 = 6.25 V, with 66 turns 6.06 V, minus SR drops (2 × … mΩ × 15 A). PASS: one documented turns
  number that is the number on the working 5.1 transformer; otherwise CANNOT VERIFY + finding "count / measure
  the turns ratio of the 5.1 transformer before winding".
- **A6 Winding sense / dots.** CHANGES "Transformer pins and winding tables": dots as the schematic implies, "not
  stated in the 5.1 documents – check against the 5.1 transformer before winding"; Q2 (driven by EPWM5A_ISO)
  must conduct while Q11 (EPWM5A) is on. Verify the chain in the netlist: J2-5 EPWM5A → DRV3 INA → OUTA → Q11
  (high side); J2-13 SYNCH_1 → ISO1 pin 3 → pin 14 EPWM5A_ISO → DRV4 INB → OUTB → R28 → `HEATER_SYNC_GATE_2` → Q2
  whose drain is `Q13_DRAIN` = TR2 pins 6 + 7. With Q11 on, primary pins 1 + 2 are positive against 4 + 5; for Q2
  to conduct, pins 6 + 7 must be negative against the centre tap. PASS: the document's statement is consistent
  with the netlist; and the SR pairing is the same as in 5.1 (`rv sch51 sheet 6`).
- **A7 Transformer loss / temperature model vs bench (known open point).** The design document reports the core
  "slightly warm" at full load (p 33). Find any TR2 loss model in the repository (`ls simulation`,
  `grep -rln "TR2" simulation`). PASS if a model exists and agrees with the bench statement; otherwise
  CANNOT VERIFY: say what must be measured (core and winding temperature at 10 A and 15 A after 30 min).
- **A8 ZVS and the P7 body diode (CHANGES 5.4, open question 9).** 5.1 used CFD7 (fast diode), 5.2 the P7 (standard
  body diode, lower cost, DPAK). From the two datasheets: Qrr, trr, Coss(er), RDS(on), dv/dt ruggedness.
  Hard commutation occurs in capacitive mode (below resonance at overload, cold filaments, first pulses).
  DAB_SIMULATION.md 4 lists the firmware mitigations ("start ≥ 2 × fr and sweep down" etc.). Is the 270 kHz
  maximum of the design document (1.26 × fr) compatible with that advice? PASS: a written start-up / overload
  strategy exists that keeps the bridge inductive, and the hardware allows it (HEATER_I measured at each edge);
  otherwise a "should fix" with the smallest fix named in the documents (IPD60R360PFD7S in the same footprint).
- **A9 Magnetising current and dead time.** ZVS needs I_mag,pk ≥ 2 · Coss(tr) · V_DC / t_dead. Hardware dead time
  100 ns (R130 10 k), firmware dead time for the LLC (find it; the DAB uses 150 ns). Lm of TR2 is not in the
  repository (DAB_SIMULATION.md 4 "data needed"). PASS only if Lm is documented; else CANNOT VERIFY with the
  measurement to take (Lm, Lleak at 100 kHz).

### B. Primary half bridge and driver DRV3

- **B1 UCC21520 pin use.** `rv sch ref DRV3` against the datasheet: INA EPWM5A, INB EPWM6A, VCCI 5V on pins 3 and 8
  (C53), GND pin 4, **DISABLE pin 5 tied to GND** (always enabled; compare with 5.1 – the Si8271 had no disable),
  DT pin 6 R130 10 k ‖ C121 100 p, VSSB pin 9 GND, OUTB pin 10 → low-side network, VDDB pin 11 15V (C52 4.7 µF
  0603, C18 10 µF 1206), VSSA pin 14 = switch node, OUTA pin 15 → high-side network, VDDA pin 16 = bootstrap.
  PASS: all as listed; pull-downs R78 (EPWM5A) and R77 (EPWM6A) present.
- **B2 Overlap protection vs LLC drive.** With the DT pin programmed, the UCC21520 inserts ≥ 100 ns dead time and
  blocks overlap. An LLC needs complementary ≈ 50 % signals: confirm in the datasheet that complementary inputs
  with firmware dead time > DT pass unchanged and that minimum input pulse width is far below 1.8 µs (half period
  at 270 kHz). PASS.
- **B3 Gate networks.** High side: `HEATER_HI_DRV` → R24 10 Ω → gate; turn-off: gate → D35 (anode at the gate) →
  `Net-(D35-K)` → R59 3.3 Ω → `HEATER_HI_DRV`; R36 10 k gate – source. Low side: R37 10 Ω, R31 3.3 Ω + D33,
  R66 10 k. Check diode directions in the netlist (`rv sch ref D35,D33,R59,R31`), peak currents vs UCC21520
  4 A / 6 A and ZLLS400 peak rating, resistor power Qg × 15 V × 270 kHz (IPD60R280P7S Qg) per package size
  (R24 1206, R37 0805). PASS: same values as the 5.1 networks (`rv sch51 ref R24,R59,R37,R31`), ratings respected;
  R59 / R31 orientation note of CHANGES open question 12 is electrically irrelevant.
- **B4 Bootstrap.** D11 S1M (standard recovery) / R99 2 Ω / C25 1 µF at up to 270 kHz: as checklist 02 item A8 but
  with the LLC's guaranteed ≈ 50 % low-side on-time. PASS: equal to 5.1 (`rv sch51 ref D11,R99,C25`); note the
  recovery loss number at 270 kHz.
- **B5 Bypass C20 and the shunt.** C20 100 nF 630 V 1210 sits between DC+ and **HEATER_CURRENT** (Q10 source), so
  the HF bridge loop Q11 – Q10 – C20 does not include the shunt R30, and the shunt sees the tank / supply current
  only. Confirm against 5.1 (`rv sch51 ref C20`) and the design intent (resonant current is measured:
  HEATER_I). PASS: unchanged from 5.1.
- **B6 FET ratings and cooling (DPAK on copper instead of TO-220 FullPAK).** Losses: conduction I_rms² × RDS(on)
  at 100 °C (0.28 Ω × ≈ 1.8) with I_rms from A2 (≈ 0.5 – 0.7 A per switch incl. magnetising current) → tens of mW
  to ≈ 0.2 W; switching ≈ 0 in ZVS. Copper for cooling: NEXT_REVISION 5.4 asks "≥ 2 cm² of L1 copper with
  thermal vias". Q11 tab = DC+ zone `S3A_Q11_tab_DC` (3.5 × 5.9 mm ≈ 0.2 cm²?), Q10 tab = switch-node zone:
  `rv bq net HEATER_HI_SOURCE` (F.Cu ≈ 195 mm²), `rv bq net DC+` pieces near (−14, −74). PASS: Tj rise
  = P × RthJA(for the actual copper, datasheet figure) ≤ 40 K; note the copper area found against the 2 cm²
  target.

### C. Synchronous rectifier and output

- **C1 DRV4 = UCC27524A.** `rv sch ref DRV4` against the datasheet (D package): 1 ENA, 2 INA, 3 GND, 4 INB, 5 OUTB,
  6 VDD, 7 OUTA, 8 ENB. PASS: ENA / ENB = 6V3, VDD = 6V3 (C17 4.7 µF within 3 mm: `rv bq padgap DRV4.6 C17.1`),
  GND = HT_GND, INA = EPWM6A_ISO → OUTA → R63 → `HEATER_SYNC_GATE_1` (Q1), INB = EPWM5A_ISO → OUTB → R28 →
  `HEATER_SYNC_GATE_2` (Q2); pull-downs R117 / R91 8.2 k on the inputs, R108 / R107 1 k on the gates.
- **C2 Supply range of the SR driver.** VDD = the 6.3 V output itself: UCC27524A UVLO rising / falling (datasheet)
  vs the output during soft start; below UVLO the outputs are held low → rectification by the body diodes of
  Q1 / Q2 (15 A × ≈ 0.8 V ≈ 12 W in an LFPAK56 during the ramp – for how long? design document p 20 – 22: pulse
  width ramp). Input thresholds with VDD 6.3 V and 3.3 V logic from ISO1 (side 2 runs on the 3.3 V LDO V3).
  Compare the UVLO with the IXDD604 of 5.1. PASS: SR active from ≤ 5 V output; input high level 3.3 V ≥ VIH max;
  the body-diode phase is not longer than on 5.1 or is harmless thermally (state energy).
- **C3 Gate drive level 6.3 V for BUK9Y15-60E.** Logic-level FET: RDS(on) at VGS = 5 V from the datasheet; conduction
  loss per FET at 15 A output: each conducts half cycles, I_rms ≈ I_out × π / 4 ≈ 0.785 × I_out → 11.8 A rms →
  P = I² × RDS(on)(100 °C). R63 / R28 4.7 Ω with Qg at 6.3 V and 270 kHz. PASS: loss per FET ≤ ≈ 2.5 W at 15 A with
  the copper it has (C6), VDS rating 60 V ≫ 2 × 6.3 V + ringing.
- **C4 Output capacitor ripple current.** Full-wave rectified sine into the capacitor bank: I_C,rms ≈ 0.483 × I_out
  (≈ 4.8 A at 10 A, 7.2 A at 15 A) at 2 × fsw ≈ 430 kHz. Bank: C31 + C32 (Rubycon ZLH 1500 µF 10 V 8 × 20: rated
  ripple from the datasheet, impedance at 100 kHz) and C8, C9, C23, C24, C33 (10 µF X5R 1206: effective value at
  6.3 V, ESR). Split the current by impedance at 430 kHz. PASS: electrolytic share ≤ their rated ripple current;
  ceramic share ≤ ≈ 2 A rms per 1206 part (or the manufacturer's figure). This is the same bank as 5.1
  (`rv sch cmp51 6` shows only the can height change) – so FAIL only if the 5.2 replacement part (10ZLH1500M…,
  "EEU-FR1A152L not stocked → Rubycon") has a lower ripple rating than the 5.1 part; otherwise note the margin
  at 15 A.
- **C5 Secondary conductor path.** The secondary is "two heavy turns with a centre tap; its ends and the tap are
  soldered to the wire pads next to the row as on 5.1" (WP1 = Q13_DRAIN, WP2 / WP3 = 6V3, WP4 = Q14_DRAIN; pins
  6 + 7 and 9 + 10 carry the same nets). For 15 A dc out: each drain path carries 11.8 A rms, the 6V3 path 15 A dc.
  `rv bq neck Q13_DRAIN F.Cu ...`, `rv bq net Q13_DRAIN Q14_DRAIN` (F.Cu + B.Cu zones 166 / 104 mm² each, vias),
  `rv bq net 6V3` (B.Cu 475 mm², In3 681 mm² (0.5 oz), F.Cu 65 mm²), `rv bq xsec 6V3 B.Cu x -60 -90 -60`,
  `rv bq net HT_GND` (F.Cu 370 mm² + In1 / In4 planes 909 mm² each). PASS: every part of the path WP → Q drain,
  Q source → HT_GND → terminal, WP2 / 3 → 6V3 → terminal has a cross-section good for 15 A at ΔT ≤ 30 K by the
  README rule (outer 1 oz: I ≈ 3.25 · w^0.725, i.e. 15 A needs ≈ 8 mm of 1 oz or the equivalent in parallel layers;
  inner 0.5 oz counts 0.3), with enough vias where the current changes layer (0.8 / 0.4 via ≈ 1 A per README:
  count them – `rv bq net 6V3` prints the via count) – and is not narrower than on 5.1
  (`rv bq51 net 6V3`, `rv bq51 xsec 6V3 B.Cu x -60 -90 -60`).
- **C6 SR FET cooling.** Q1 / Q2 drain tabs on the `Q14_DRAIN` / `Q13_DRAIN` pours (README: 12 / 16 vias in the tab
  pads). PASS: copper area per FET ≥ 1 cm² per layer on two layers, vias under / at the tab.
- **C7 Terminals and thermal relief.** HT_6V3 / HT_GND blade terminals (2 × 1, 5 mm pitch, 1.4 mm drill) at 15 A:
  rating of the terminal part (consigned / which part? `rv sch part HT_6V3`), and the pad connection – thermal
  spokes 0.8 mm (README "Zone settings": HT_GND / 6V3 spokes 0.8 mm) × 4 × layers: is that enough for 15 A?
  (`rv bq net 6V3` narrowest tracks; `python3 kicad_next/review/tools/drc_summary.py starved_thermal`.)
  PASS: spoke cross-section summed over the connected layers ≥ 6 mm of 1 oz equivalent, or solid connection.
- **C8 Heater voltage sense.** R54 / R55 tap 6V3 at (−55, −62) (checklist 03 covers the chain). Here only: the tap is
  not inside the high-current path between WP2 / WP3 and C31 / C32 such that it sees I × R drops – note.

### D. Layout of the primary part

- **D1 HF loop.** Q11 drain (DC+ tab) → Q11 → switch node → Q10 → HEATER_CURRENT → C20 → DC+. Coordinates from
  `rv bq fp Q10,Q11,C20`: C20 at (−12, −83), Q11 tab (−13.8, −73.6), Q10 source pad (−16.0, −68.1). Path length and
  area; compare with 5.1 (`rv bq51 fp Q10,Q11,C20`; TO-220 there). PASS: loop path ≤ 60 mm and not larger than
  1.5 × 5.1's.
- **D2 DC+ feed of the heater bridge and the tank (known history: "LLC split capacitors had no DC+", stage 3a
  point 4 / 3a.2).** `rv bq neck DC+ F.Cu -13.838 -73.55 -10.3 -84.925` (tab → C42), and the feed from the bulk
  capacitors: on which layers and how wide (`rv bq net DC+`: tracks at x ≈ −8.4 … −8.0, y −83 … −72 are 0.4 – 0.6 mm
  B.Cu; zone piece F.Cu [−8.8, −81.6 … −7.6, −72.5]). Current ≈ 0.25 – 0.5 A dc + HF ripple. PASS: ≥ 0.5 mm
  continuous for ≤ 1 A rms, ≥ 1.2 mm to other nets on outer layers, connected by copper (not only by the DRC
  ratsnest: `python3 kicad_next/review/tools/drc_summary.py` → unconnected 0).
- **D3 Switch node and tank mid point.** `rv bq near HEATER_HI_SOURCE --within 1.3`, `rv bq near HEATER_CAP_MEAS
  --within 1.3`. The mid point swings 200 V ± V_pk (A2) at 214 kHz, the switch node 0 – 400 V. PASS: ≥ 1.2 mm to
  nets outside the high-side group on outer layers (rule "High-side driver group DRV3" allows 0.2 mm inside the
  group: HEATER_HI_GATE, HEATER_HI_SOURCE, HEATER_HI_DRV, `Net-(DRV3-VDDA)`, `Net-(D35-K)`, `Net-(D11-K)`),
  resonant capacitor pad-to-pad gap (`rv bq padgap C42.1 C42.2`) ≥ 1.5 mm for 400 V between DC+ and
  HEATER_CURRENT across two parts, and distance of the capacitor row to the **top board edge** (y −91.35) and to
  the UART island (x ≥ 4) stated.
- **D4 Gate loops.** DRV3 on B.Cu at (−21, −55); Q10 gate pad (−11.5, −68.1), Q11 gate pad (−11.6, −79.9): ≈ 16 mm
  and ≈ 27 mm away. `rv bq net HEATER_HI_DRV HEATER_HI_GATE HEATER_LOW_DRV HEATER_LOW_GATE` (HEATER_HI_DRV
  19 mm on B.Cu; HEATER_LOW_DRV 8.8 mm B.Cu + 19 mm on In2). Return paths: high side via `HEATER_HI_SOURCE` to
  pin 14, low side via GND plane to pin 9. PASS: gate resistors and turn-off diodes at the FETs (README: "heater
  gate parts at their FETs"), the high-side DRV track is paired with a switch-node return on the same or the
  adjacent layer (**no switch node on an inner layer**: `rv bq nets '*HEATER_HI*'` shows F.Cu / B.Cu only),
  HEATER_LOW_DRV on In2 has GND plane (In1) over it along its length (`rv bq xsec GND In1.GND` at its
  coordinates), loop lengths not more than 2 × 5.1's or accepted in the README.
- **D5 Kelvin sense of R30.** HEATER_CURRENT → R106 (sheet 8). `rv bq net HEATER_CURRENT`: the In2 sense track
  (22.7 mm) starts at the shunt pad, not at the Q10 source pour. (Detail: checklist 08.) PASS / note.
- **D6 Barrier at TR2.** `rv bq padgap TR2.1 TR2.10` (pin rows 12.7 mm apart, pads 2.29 mm → ≈ 10.4 mm; README:
  "heater barrier 10.37 mm ≥ 8.0 – no slot"), `rv bq near @HEATER --within 8.0 --other-domain`. PASS: only
  slot-separated pairs (ISO1 T slot, the slot bar at y −64 … −63) appear below 8.0 mm, and
  `python3 tools/next/check_domains.py kicad_next/tube_psu_5_2.kicad_pcb` exits 0 (run it only if no other
  KiCad job is running; ≈ 10 s, a few hundred MB).
- **D7 DPAK courtyards / wire pads / tall parts.** `python3 kicad_next/review/tools/drc_summary.py courtyards_overlap
  -71 -91 -5 -44`. PASS: no body collision; TR2 body box (`rv bq fp TR2`: x −39.0 … −21.1, y −90.4 … −62.1)
  clear of C20 / resonant capacitors / Q11 on F.Cu, wire pads accessible beside the bobbin.

### E. 5.1 → 5.2 changes touching this part (explicit)

- **E1** DRV3 Si8271 + DRV9 IXDD609 → one UCC21520: both gate outputs now come from DRV3; the low-side path is
  longer than with the local DRV9? (`rv bq51 fp DRV9,Q11,Q10`.) PASS as D4.
- **E2** Q10 / Q11 swapped and turned in the user placement of 2026-11-21: confirm the netlist roles on the board
  (`rv bq fp Q10,Q11`: Q11 tab = DC+, Q10 tab = HEATER_HI_SOURCE, Q10 source = HEATER_CURRENT).
- **E3** DRV4 IXDD604 (DFN) → UCC27524A (SOIC-8): pin mapping per C1; the two channels are **not** swapped relative to
  5.1 in function (which SYNCH pin drives which FET: `rv sch cmp51 6` lists DRV4 pin changes only as package
  renumbering – verify by following EPWM5A_ISO to its FET in both netlists).
- **E4** C31 / C32 footprint with the real can height (8 × 20 mm), R30 library change: pads unchanged
  (`rv bq fp C31,R30` vs `rv bq51 fp C31,R30`).
- **E5** ERC: `ground_pin_not_ground` on DRV3 pin 14 (VSSA) – by design; it is the third such warning (the README
  documents two / 14 warnings in total; the report shows 15). Documentation finding only.

### F. Bring-up notes for the findings

- **F1** First start with a resistive load: frequency high → down; what HEATER_I and the AD1 voltage should read;
  how to recognise a wrong SR polarity (output low, FETs hot) – fix by swapping the two primary ends
  (CHANGES) or the SYNCH signals in firmware.
- **F2** Items that need the real transformer: turns, Lm, leakage, dot orientation, core / winding temperature.

## 5. Out of scope / given

- AD1 / ISO1 / V3 measurement chain (checklist 03); HEATER_I amplifier U1A (08); whole-board creepage (10);
  DPAK / LFPAK assembly and BOM (13); the heater island copper against mounting holes H1 (12 / 10).
- Given: UCC21520 for the bridge, UCC27524A for the SR, IPD60R280P7S DPAK, 4 × 3.3 nF C0G, balancing resistors,
  TR2 construction and pins unchanged from 5.1, no silkscreen, via-in-pad accepted (Q1 / Q2 tab pads, Q10 pad 1,
  C22 pad 1).

## 6. Findings format

Write `kicad_next/review/findings/06_heater_llc.md` exactly in the format of `kicad_next/review/README.md`
"Common findings format": summary; one table row per item above (A1 … F2) with **PASS / FAIL / CANNOT VERIFY** and
the evidence (file:line, command + output lines, calculation with inputs, or datasheet document / page / URL);
ranked findings with severity (**blocker for ordering / should fix / note**), what is wrong, evidence, smallest fix,
confidence; "Compared with 5.1"; "Could not verify"; "Outside scope". "Looks fine" without evidence is not
acceptable.
