# Review checklist 05 – mains input, EMI filter, inrush relay, bridgeless PFC, PFC gate drivers, DC-link capacitors

You are reviewing **one part** of the tube_power 5.2 power-supply board, alone, from this file and the repository
`/home/jari/dev/tube_psu_kicad`. You are doing a design review, not a redesign.

**Rules (full text: `kicad_next/review/README.md`, "Common rules" – read that section first):**
read-only on the repository, the only file you write is `kicad_next/review/findings/05_pfc_emi_inrush.md`; no commit,
no push; never touch `kicad_next/tube_psu_5_2.kicad_pcb` / `.kicad_pro` and never run a script that saves or
regenerates design files (`route_s*.py`, `update_board_parts.py`, `setup_project.py` / `make_board.py` / generators
without `--check`); stop if a KiCad lock file exists (`rv guard`); RAM under 3 GB – no board DRC, no
`check_next.sh` (use the existing reports); never `pkill -f`; never run the KiCad AppImage with `--version`; the
owner's name / e-mail stay out of web requests. **Acceptance bar: match the bench-verified 5.1 board and add
creepage – do not optimise beyond that.** Datasheet facts come from the datasheet you fetch now, not from memory.

## 1. Scope

Mains (230 V AC; terminals IN1 = line through the inrush path, IN2 = the other pole, PE) passes the inrush resistor
**R27** 47 Ω 10 W, bypassed by relay **RL1** (Songle SRD-05VDC, coil on 5V switched by Q9 from J2-17
GPIO_BYPASS_RLY), then a two-stage EMI filter (X2 C86 680 nF – common-mode choke CM1 – C38 470 nF – CM4 – C117
680 nF; Y capacitors C65, C81, C84, C85 2.2 nF to PE and C82 from GND to PE; discharge R4 – R6 3 × 470 k) and reaches
the **bridgeless dual-boost PFC**: AC1 → L2 → Q5 (drain = PFC_DRAIN_1) → SICD1 → DC+, AC2 → L1 → Q6 (PFC_DRAIN_2) →
SICD2 → DC+. Q5 / Q6 = C2M0160120D SiC MOSFETs (TO-247), SICD1 / SICD2 = C3D02060A SiC diodes (TO-220-2), sources
through 4 mΩ shunts R93 / R21 to GND. Bridge **DB1** (TBS22K) and the 47 nF capacitors C64 / C66 (AC1 / AC2 to GND)
give the return path and the pre-charge path. The PFC is designed for **discontinuous conduction at 230 V**
with a switching frequency below 150 kHz and is controlled by the FPGA (PFC_PWM1 = J2-19, PFC_PWM2 = J2-33) from
the measured C117 voltage and the shunt currents (design document p 11 – 15). DC link: **DC+ 400 V**, bulk
capacitors C28, C29, C37, C56 (4 × 82 µF 450 V) plus C73 2.2 µF 450 V MLCC. Gate drivers **DRV1 / DRV2 =
UCC27511A** (new in 5.2; 5.1: IXDD609) with split outputs: OUTH → R14 / R20 5 Ω, OUTL → R1 / R19 5 Ω, pull-downs
R43 / R7. Load on the DC link: DAB ≈ 400 W + heater LLC ≈ 65 – 95 W + auxiliary 12 W. New in 5.2 besides the
drivers: L1 / L2 documented as the sendust toroids that are really fitted (upright on the old RM8 holes, value
"TBD (measured)"), the single heatsink line (SICD1 / SICD2 moved), DC+ kept on the outer layers, new bulk
capacitor part.

- Sheets: `05_pfc.kicad_sch` (`tools/next/sheets/sheet05.py`, 35 parts), `11_startup.kicad_sch` (`sheet11.py`: the
  bulk capacitors, C73, C14), and DRV1 / DRV2 with R1, R7, R14, R19, R20, R43, R69, R71, C79, C80 on
  `09_ac_measurement.kicad_sch` (`sheet09.py`).
- Nets: `RES_IN`, `IN2`, `Net-(RL1-COM)`, `L1_PRI2`, `L2_PRI2`, AC1, AC2, `PE`, `PFC_DRAIN_1`, `PFC_DRAIN_2`,
  "PFC CURRENT 2+" (Q5 source), "PFC CURRENT 3+" (Q6 source), GATE1, GATE2, PFC_PWM1, PFC_PWM2, DC+, GND,
  GPIO_BYPASS_RLY.
- Board: mains input and filter in the west half, x −70 … −2, y −46 … 12 (IN1 (−67, −16), IN2 (−67, 8), PE (−47, 0),
  RL1 (−61, −30), R27 (−59, −44), CM1 (−45, −16), CM4 (−24, −18)); chokes L2 at (−6, −39) and L1 at (−7, 4) (bodies
  31.5 × 16.7 mm upright); the heatsink line x 0 … 14: Q5 (3.8, −29.6), SICD1 (11.8, −21.4), DB1 (3.5, −12.2, SMD),
  C73 (12.5, −14.0), SICD2 (3.1, −3.8), Q6 (11.4, 3.0); shunts R93 (3.8, −16.1) and R21 (14.5, −8.0) on B.Cu;
  drivers DRV1 (12.5, −33.6) and DRV2 (11.7, 10.1) on B.Cu; bulk capacitors in a column at x ≈ 20, y −30 … 9.

## 2. Read first

1. Design document p 11 – 15 (`rv pdf 11 15`): topology, DCM choice, current measurement in the source, EMI filter
   (−65 dB at the switching frequency, three 680 nF X capacitors), and p 33 – 34 (inductor, thermal result).
2. `tools/next/sheets/sheet05.py`, `sheet11.py`, the driver part of `sheet09.py` (notes at the end of each).
3. `kicad_next/CHANGES_5_2.md`: section 3 row "3a DRV1, DRV2"; section 5 rows 5.2, 5.2b, 5.6; "Open questions" 8, 10.
4. `NEXT_REVISION.md` section 5 rows 5.2, 5.2b, 5.5, 5.6 and 3a (driver choice).
5. `kicad_next/README.md`: "Stage 4a" (heatsink line, SICD moves, pour outlines re-cut), "Stage 4k", "Stage 4l"
   (DC+ neck at SICD1), "Stage 9" (no DC+ on inner layers: neck 2.25 mm), "Power, HV and ground routing" –
   "Open points" 1, 2, 5 (PE / Y capacitors / relay driver) and "Stage 3a.2", table row L1 / L2 in "Footprints and
   3D models", "Inner layers" (no GND plane under the mains input).
6. `kicad_next/J2_PINOUT.md` rows 17, 19, 33.
7. Datasheets to fetch: Wolfspeed **C2M0160120D** and **C3D02060A**, TI **UCC27511A**, MCC **TBS22K** (or the TBS
   series), Songle **SRD-05VDC-SL-C**, KEMET **SCF20-05-550** (rated current, inductance), Ohmite **TWW10J47RE**,
   Man Yue **ERT826M2WI45RRS0F-R** (82 µF 450 V: ripple current at 100 Hz and 100 kHz, life), TDK
   **C5750X6S2W225K** (DC bias at 400 V), the X2 / Y parts by their LCSC numbers (`rv sch bom 5`), BSS138.

## 3. How to extract facts

```sh
kicad_next/review/tools/rv guard && kicad_next/review/tools/rv setup
kicad_next/review/tools/rv sch sheet 5
kicad_next/review/tools/rv sch sheet 11
kicad_next/review/tools/rv sch ref DRV1,DRV2,R1,R14,R19,R20,R43,R7,R69,R71,C79,C80
kicad_next/review/tools/rv sch cmp51 5
kicad_next/review/tools/rv sch cmp51 9                  # shows the IXDD609 -> UCC27511A pin changes
kicad_next/review/tools/rv sch bom 5
kicad_next/review/tools/rv sch bom 11
kicad_next/review/tools/rv sch net AC1 AC2 PE RES_IN IN2 "Net-(RL1-COM)" L1_PRI2 L2_PRI2
kicad_next/review/tools/rv bq area -72 -48 22 14        # every footprint of the PFC / filter area
kicad_next/review/tools/rv bq fp Q5,Q6,SICD1,SICD2,DB1,C73,R93,R21,L1,L2
kicad_next/review/tools/rv bq net PFC_DRAIN_1 PFC_DRAIN_2 "PFC CURRENT 2+" "PFC CURRENT 3+" GATE1 GATE2
kicad_next/review/tools/rv bq net DC+                   # widths per layer, vias, pour pieces
kicad_next/review/tools/rv bq neck DC+ F.Cu 11.8 -26.48 9.863 -14.0     # SICD1 cathode -> C73 pad 1 (the documented neck)
kicad_next/review/tools/rv bq neck DC+ F.Cu 11.8 -26.48 20.2 -17.2      # SICD1 cathode -> bulk capacitor C56
kicad_next/review/tools/rv bq neck DC+ F.Cu 3.09 1.26 20.4 -3.8         # SICD2 cathode -> bulk capacitor C37
kicad_next/review/tools/rv bq xsec DC+ F.Cu y -17.5 0 30
kicad_next/review/tools/rv bq xsec DC+ B.Cu y -17.5 0 30
kicad_next/review/tools/rv bq neck GND F.Cu 15.137 -14.0 25.2 -17.2     # C73 GND pad -> GND pin of bulk capacitor C56 on F.Cu
kicad_next/review/tools/rv bq neck GND B.Cu 14.975 -8.0 25.4 -3.8       # shunt R21 GND pad -> GND pin of C37 on B.Cu
kicad_next/review/tools/rv bq pads GND | grep -E "C28|C29|C37|C56|C73|R93|R21|DB1|C64|C66"
kicad_next/review/tools/rv bq near PFC_DRAIN_1 --within 1.3
kicad_next/review/tools/rv bq near PFC_DRAIN_2 --within 1.3
kicad_next/review/tools/rv bq near AC1 --within 1.3 --layer F.Cu
kicad_next/review/tools/rv bq dist fp:PE @PRI           # PE terminal and Y-capacitor PE pads against primary copper
kicad_next/review/tools/rv bq near PE --within 3.3 --other-domain
kicad_next/review/tools/rv bq net PE
kicad_next/review/tools/rv bq padgap Q5.1 Q5.2
kicad_next/review/tools/rv bq51 net DC+                 # 5.1 for comparison
kicad_next/review/tools/rv bq51 fp Q5,Q6,SICD1,SICD2,C73,DB1
kicad_next/review/tools/rv section kicad_next/README.md 'Stage 9'
kicad_next/review/tools/rv section kicad_next/README.md 'Stage 4l'
```

## 4. Checklist

### A. Schematic against the design intent and 5.1

- **A1 Topology.** `rv sch sheet 5` against the design document figure 3.1 (p 12): L2 between AC1 and Q5 drain,
  L1 between AC2 and Q6 drain, both SiC diode cathodes on DC+, both sources through 4 mΩ to GND, DB1 with its AC
  pins on AC1 / AC2 (the sheet note says the symbol pin names are swapped against the nets: pin 1 = AC2,
  pin 3 = AC1 – harmless for a bridge, confirm with the TBS22K pinout: 1 / 3 are the AC pins, 2 = +, 4 = −),
  C64 / C66 from AC1 / AC2 to GND. PASS: same connectivity as 5.1 (`rv sch cmp51 5` shows only renamed drain nets,
  the L1 / L2 symbol change and footprint libraries).
- **A2 Inrush path.** IN1 → `RES_IN` → R27 → `Net-(RL1-COM)`; relay COM–NO shorts R27 when energised; NC unused.
  Calculate the first-cycle peak: 325 V / 47 Ω ≈ 6.9 A into 328 µF + filter capacitors, energy in R27
  ≈ ½ C V² = 17 J per charge, against the TWW10 pulse rating; relay contact rating (10 A 250 VAC) vs the input
  rms current at full load (≈ 2.3 – 2.6 A at 230 V; calculate from 500 – 550 W and the efficiency you assume).
  PASS: R27 single-pulse energy within the datasheet / wirewound rule-of-thumb limit; relay contact current
  ≤ 50 % of rating. Note what happens if the relay never closes (firmware fault): R27 at full load =
  I² × 47 Ω ≈ 270 W – is there any protection (no fuse, no thermal fuse is on the board; 5.1 had none)? Record as
  a note with "as 5.1".
- **A3 Relay driver.** 5V → coil (RL1 pins 4 / 5) → Q9 drain; D9 + D28 in series across the coil (anode at the
  drain, cathode at 5V); GPIO_BYPASS_RLY (3.3 V logic) → R44 2.2 k → gate with C35 100 nF to GND; R32 2.2 k from
  the J2 pin to GND (pull-down; loads the FPGA pin with 1.5 mA). Coil current (SRD-05VDC ≈ 70 – 90 mA, datasheet)
  on the 5V rail of the flyback; gate voltage 3.3 V: compare with Vgs(th) max and the RDS(on) test condition of
  the part actually ordered (BSS138LT1G, LCSC C82045 – the schematic value still says 2n7000, review flag in the
  parts table); turn-on delay R44 × C35; drain voltage at turn-off = 5 V + two Schottky drops. PASS: the FET is
  fully on at 3.0 V gate drive (3.3 V − tolerance) with the coil current, at the datasheet's worst-case
  threshold; the SOT-23 footprint pad numbers match the ordered part (symbol pins 1 = D, 2 = G, 3 = S on the
  "Proteus" SOT-23 footprint – `rv sch ref Q9`, `rv bq fp Q9` against the BSS138 package drawing: gate and
  source on the two-lead side, drain on the single lead). FAIL if a 2N7000-class threshold (up to 3 V) could
  be fitted from the schematic value, or the pads do not match the package.
- **A4 X capacitors and discharge.** C86 + C38 + C117 (680 n + 470 n + 680 n) and R4 + R5 + R6 = 1.41 MΩ from
  `RES_IN` to `IN2`: τ = R × C_total. Where do the resistors sit relative to the relay / R27 (they discharge C86
  directly; C38 / C117 through the chokes – fine)? PASS: the terminal voltage falls below 60 V within the time
  the standard used by the document demands (IEC 62368-1: 2 s for pluggable equipment type A – calculate
  325 V → 60 V needs 1.69 τ); resistor voltage 108 V rms each ≤ the 1206 part's rating; X2 class and voltage
  rating of the three LCSC parts ≥ 275 VAC.
- **A5 Y capacitors and earth leakage.** C65, C81 (line side of CM4), C84, C85 (input side), C82 (GND → PE), each
  2.2 nF: Y1 or Y2 class and rated voltage of the LCSC part; touch / leakage current = 2π f C V per line
  (≈ 0.16 mA per 2.2 nF at 230 V) and the role of C82 (bridge negative to PE: sees the mains half-wave voltage).
  PASS: every part is a safety-rated Y capacitor (Y2 ≥ 250 VAC or Y1); total earth leakage stated.
- **A6 EMI filter vs the documented design.** Values equal to 5.1 and to p 15 (three 680 nF mentioned; the board
  has 680 n / 470 n / 680 n – explain from the document or 5.1 BOM). CM1 / CM4 SCF20-05-550: rated current ≥ the
  input rms current with margin. PASS: unchanged from 5.1, choke current rating ≥ 1.5 × input rms.
- **A7 SiC MOSFET ratings.** C2M0160120D: VDS 1200 V vs 400 – 450 V bus; ID vs the DCM peak current (find the
  design peak: L = 200 µH per the 5.1 schematic, f < 150 kHz, p 12 – 13; I_pk ≈ V_in,pk × t_on / L); gate drive
  15V / 0 V vs the datasheet's recommended +20 / −5 V and RDS(on) at VGS = 15 V; gate threshold at 150 °C vs a
  0 V off state with 5 Ω off resistor (dv/dt immunity, Crss × dv/dt × R). PASS: same drive levels as 5.1 (15 V
  rail, 0 V off), ratings respected; note the RDS(on) penalty at 15 V.
- **A8 SiC diodes.** C3D02060A = **2 A** 600 V. In a DCM boost each diode carries the average output current of
  its half-cycle and peaks equal to the inductor peak. Calculate average and rms / repetitive peak diode current
  at full load (≈ 540 W / 400 V = 1.35 A average total, i.e. per diode 1.35 A average over its conducting
  half cycle) and compare with IF(avg) at the case temperature, IFRM and IFSM (inrush: with the relay open the
  bulk capacitors charge through **DB1**, not through the SiC diodes – confirm from the schematic). PASS:
  within the datasheet at the heatsink temperature assumed (design document p 34: +30 K on the plate); same part
  as 5.1.
- **A9 Bridge DB1.** TBS22K (SMD, 2 A 800 V class – read the datasheet): carries the return current of the
  bridgeless boost every half cycle (one bridge diode conducts the full line-frequency current of the active
  boost leg, in parallel with C64 / C66 for HF) and the inrush charge. PASS: average / rms current and IFSM
  (inrush 6.9 A peak limited by R27) inside the rating with its thermal path (SMD part **under the heatsink
  line** – see C6 and checklist 12).
- **A10 DC-link capacitors.** 4 × 82 µF = 328 µF: 100 Hz ripple voltage ΔV = P / (2π f C V) at 540 W; 100 Hz ripple
  current per capacitor and the HF ripple (PFC DCM + DAB + LLC) against the Man Yue datasheet ratings; voltage
  margin 450 V vs 400 V + ripple + PFC overshoot + the flyback line-OVP trip (483 V!, checklist 01) – i.e. the
  capacitors, not the flyback, limit the bus. PASS: ripple current ≤ rating at 105 °C derated for ambient,
  peak bus voltage in normal operation ≤ 430 V, statement what limits the bus above 450 V (PFC firmware OVP).
- **A11 C73 2.2 µF 450 V X6S MLCC on a 400 V bus** (CHANGES open question 10, "left as is"). Fetch the TDK DC-bias
  curve: effective capacitance at 400 V; rated 450 V with no derating margin. PASS only as "equal to 5.1";
  record the effective capacitance and the 89 % voltage stress as a note; FAIL if the LCSC part is not the
  450 V type.
- **A12 Gate drivers DRV1 / DRV2 (IXDD609 → UCC27511A).** Datasheet pinout DBV-6: 1 VDD, 2 OUTH, 3 OUTL, 4 GND,
  5 IN−, 6 IN+. `rv sch ref DRV1,DRV2`. PASS: IN+ = PFC_PWMx with 10 k pull-down (R71 / R69), IN− = GND, OUTH →
  5 Ω → gate, OUTL → 5 Ω → gate, VDD = 15V with C79 / C80 4.7 µF; VDD abs max ≥ 18 V > 15.5 V; input threshold
  compatible with 3.3 V logic; peak currents 15 V / 5 Ω = 3 A within the driver's 4 A / 8 A; output polarity the
  same as the 5.1 circuit (non-inverting: `rv sch cmp51 9`, IXDD609 with EN tied to 15V).
- **A13 Gate resistor power and C79 / C80.** P = Qg(15 V) × 15 V × f for the C2M0160120D split over R14 / R1 (1206).
  C79 / C80 are 4.7 µF X5R 25 V 0603 (same part as C95, LCSC C6119856): effective capacitance at 15 V bias
  (curve as in checklist 02 A9). PASS: resistor dissipation ≤ 50 % of rating; effective VDD bypass ≥ 20 × Qg / ΔV
  with ΔV = 0.5 V.
- **A14 Shunt in the gate loop.** Source → R93 / R21 → GND, driver GND at the plane: the gate current flows through
  the shunt (design document p 13 accepts this; the ADC samples after the edge). PASS: 4 mΩ × 3 A = 12 mV –
  negligible for the gate; the kelvin sense of the shunt is checklist 08.

### B. What changed 5.1 → 5.2 (explicit)

- **B1 L1 / L2 as upright toroids on the RM8 holes** (CHANGES 5.2). `rv bq fp L1,L2`: pads 1 / 2 on the old RM8
  winding holes, 8.42 mm apart on a diagonal; body 31.5 × 16.7 mm placed from a photo, "±3 mm – confirm on the
  built board" (README; open input "Measured body positions of L1 / L2"). PASS: the pads carry the right nets
  (L2: 1 = AC1, 2 = PFC_DRAIN_1; L1: 1 = PFC_DRAIN_2, 2 = AC2), pad / drill (2.6 / 1.3 mm) fits the 0.8 mm wire;
  CANNOT VERIFY for the body position unless a measurement is recorded – then list which neighbours are within
  3 mm of the courtyard (`rv bq area` around each body box).
- **B2 Inductance value "TBD (measured)".** The schematic and BOM carry no value. Find any measured value in the
  repository (`grep -rn "sendust\|L at 0 A" --include=*.md .`). PASS if a measured L at 0 A and at peak current
  exists and the DCM / peak-current calculation of A7 uses it; otherwise CANNOT VERIFY and a "should fix:
  record the measured value before ordering" finding (the parts are consigned and the same as on the working
  5.1 board, so it is not a blocker).
- **B3 SICD1 / SICD2 moved into the heatsink line; pours re-cut** (README "Stage 4a", "4k"). `rv bq fp SICD1,SICD2`
  and `rv bq net PFC_DRAIN_1 PFC_DRAIN_2`: each anode joins its drain pour and each cathode the DC+ pour with
  solid copper or spokes of adequate total width. PASS: connection width (sum of spokes or solid neck,
  `rv bq neck PFC_DRAIN_1 F.Cu 11.8 -21.4 3.752 -24.1`) ≥ 1.0 mm for ≈ 2 – 3 A rms.
- **B4 DC+ neck at SICD1** (known weak point: F.Cu ≈ 1.25 mm + B.Cu 1.0 mm track = 2.25 mm after "Stage 9" removed
  the In3 copper). Re-measure with the `neck` / `xsec` commands above; follow the B.Cu track and its vias
  (`rv bq net DC+`: vias near (10 … 12, −27 … −17)). Current through the neck: SICD1 diode current (A8) at HF plus
  whatever of the DAB / LLC load current takes this way from the bulk capacitors (trace the pour: is the neck in
  the path Q19 ↔ bulk capacitors, or only SICD1 ↔ capacitors?). PASS: neck ≥ the width needed by README's rule
  (1 oz outer I ≈ 3.25 · w^0.725 A) for the rms current with factor 2 margin, and not narrower than the same spot
  on 5.1 (`rv bq51 fp SICD1,C73` gives the 5.1 pad positions: SICD1.K (11.5, -21.65), C73.1 (9.863, -14.0);
  then `rv bq51 neck DC+ F.Cu 11.5 -21.65 9.863 -14.0`).
- **B5 No DC+ / power GND on inner layers.** `rv bq net DC+` shows tracks and zone fill on F.Cu / B.Cu only; the
  power GND return between shunts, DB1 pin 4, C73 and the bulk capacitors: is it on the outer-layer GND pours or
  does it rely on the In1 / In4 planes through vias? (`rv bq neck GND F.Cu ...` between R93 pad 2 (use
  `rv bq fp R93`), DB1.4 (7.2, −14.7), C73.2 (15.137, −14.0) and the bulk-capacitor GND pins.) PASS: DC+ has no
  inner-layer copper; every PFC power return has an outer-layer path ≥ 2 mm wide or a documented reason
  (the decision says "DC+ and its power-GND return on outer layers"; In1 / In4 remain GND planes in parallel).
- **B6 New bulk capacitor part.** Footprint `CP_Radial_D12.5mm_P5.00mm…_H45mm`: 12.5 × 45 mm, pitch 5.0, and the
  real can height against the enclosure / heatsink (checklist 12); polarity on the board (`rv bq fp C28,C29,C37,C56`:
  pad 1 = DC+). PASS: all four the same orientation as 5.1 (`rv bq51 fp C28,C29,C37,C56`) with pad 1 on DC+.
- **B7 100 nF 630 V 1210 (CHANGES 5.6)**: C15, C20, C67, C70 on DC+ belong to other checklists; here only check that
  no 5.1-era 1206 500 V part is left on AC1 / AC2 / DC+ in this area (`rv sch bom 5`, `rv sch bom 11`).

### C. Layout

- **C1 Boost commutation loops.** Loop 1: Q5 drain → SICD1 → DC+ → C73 (or nearest bulk capacitor) → GND → R93 → Q5
  source. Loop 2 the same with Q6 / SICD2 / R21. Give each loop's path length and enclosed area from the
  coordinates (`rv bq fp`, `rv bq net`), and the same for 5.1 (`rv bq51 fp ...`). SICD1 moved to (11.8, −21.4)
  and SICD2 to (3.1, −3.8) on the heatsink line. PASS: each loop not larger than 1.5 × its 5.1 loop, C73 (the
  only HF capacitor on DC+ here) within both loops or a 100 nF 630 V part close to the second one.
- **C2 Switch-node copper.** `rv bq net PFC_DRAIN_1 PFC_DRAIN_2`, `rv bq near PFC_DRAIN_1 --within 1.3`.
  PFC_DRAIN_1 pour F.Cu ≈ 120 mm², PFC_DRAIN_2 ≈ 35 mm² + 18 mm of 2.0 – 2.4 mm B.Cu track. PASS: ≥ 1.2 mm to
  every other net on outer layers, no signal track of the measurement area routed under the pours without a
  plane between (the UART pair runs under PFC_DRAIN_1 with In1 GND between – checklist 04), pour areas not
  larger than needed (compare with 5.1: `rv bq51 nets '*L2-2*'`).
- **C3 Thermal-relief spokes in the power path.** The kept 5.1 pours connect several through-hole power pads by
  0.152 mm spokes (`rv bq net PFC_DRAIN_1`: 7.7 mm of 0.1524 mm track at L2 pad 2 (−0.07, −37.76); DC+ the same
  at the bulk-capacitor pins). For L1.1, L2.2, Q5.2, Q6.2, SICD1 / SICD2 pads and the bulk-capacitor pins:
  count spokes and width (`rv bq net NET` narrowest segments) and check whether the zone also touches the pad
  directly. PASS: total connection width per pad ≥ 0.6 mm (4 × 0.152) and equal to 5.1 (`rv bq51 net ...`);
  flag any pad with fewer spokes than on 5.1.
- **C4 Gate loops.** DRV1 (12.5, −33.6) → R14 / R1 → Q5 gate (3.75, −29.6); DRV2 (11.7, 10.1) → R20 / R19 → Q6 gate
  (11.4, 3.0); return through the shunt and GND to the driver's pin 4 / C79 / C80. `rv bq net GATE1 GATE2`
  (GATE1 has 6.3 mm of 1.0 mm track, GATE2 6.9 mm of 0.76 mm), `rv bq padgap DRV1.1 C79.1`. PASS: driver ≤ 15 mm
  from its gate, VDD capacitor ≤ 3 mm from pins 1 / 4, return under the gate track (GND plane on In4 directly
  under B.Cu), not longer than 5.1's loop (`rv bq51 fp DRV1,Q5`).
- **C5 Mains-side spacing.** Between the two poles (AC1 / L2_PRI2 side vs AC2 / L1_PRI2, RES_IN vs IN2) the README
  uses 1.2 mm functional spacing on outer layers; IEC 62368-1 asks basic-insulation-like spacing **before the
  fuse / between line and neutral** (functional insulation: the standard allows a fault test instead).
  `rv bq dist RES_IN IN2`, `rv bq dist AC1 AC2`, `rv bq dist L1_PRI2 L2_PRI2`. PASS: ≥ 2.5 mm creepage between
  the poles everywhere up to the PFC (state the smallest value and where), or equal to 5.1 with a note.
- **C6 PE and Y capacitors.** README stage 3a open points 1 / 2 and "Stage 3a.2" changed the PE routing.
  `rv bq net PE`, `rv bq near PE --within 3.3 --other-domain`, `rv bq dist fp:PE @PRI`. PASS: PE copper ≥ 3.2 mm
  creepage / 2.0 mm clearance from all primary copper on every layer (the Y-capacitor pads themselves excepted:
  their own pin spacing 7.5 mm), PE track ≥ 1.0 mm wide, every Y capacitor connected.
- **C7 Heatsink line electrical clearances.** Tabs of Q5 / Q6 (drain = switch node), SICD1 / SICD2 (cathode = DC+)
  face the heatsink at x ≈ 5 … 13. DB1 and C73 are SMD parts on F.Cu between them (known open input: heatsink
  footprint and height against C73 and DB1). From `rv bq fp Q5,SICD1,DB1,C73,SICD2,Q6` give the x-range of each
  body and say where a straight heatsink can stand. PASS / FAIL belongs to checklist 12; here list the
  facts and whether DB1 (dissipating ≈ 1 – 2 W, A9) has any copper area for cooling (`rv bq net DC+` /
  GND pours at its pads).
- **C8 No plane under the filter.** `rv bq xsec GND In1.GND y -20 -70 0` and the same for In4.GND. PASS: no GND
  plane under IN1 / IN2 / RL1 / CM1 / CM4 / the X and Y capacitors (README "Inner layers": none left of x 2 by
  design), so the filter is not bypassed capacitively.
- **C9 DRC items in the area.** `python3 kicad_next/review/tools/drc_summary.py pth_inside_courtyard` (IN1 pin 1 and
  CM1 pin 3 inside the courtyard of C86 – "as in 5.1") and `… courtyards_overlap -72 -48 22 14`. PASS: each is
  explained by real body dimensions (C86 26.5 × 11.5 mm footprint vs the generic-brand part "body size to
  verify" in the parts table) – CANNOT VERIFY if the body size of the LCSC part C2888216 is not confirmed.

### D. Firmware-facing

- **D1** PFC_PWM1 (J2-19) drives Q5 (AC1 leg, shunt R93 → "PFC CURRENT 2+" → PFC_I2_MEAS?) and PFC_PWM2 (J2-33)
  drives Q6 – establish from the netlist which current channel (PFC_I1_MEAS J2-42 / PFC_I2_MEAS J2-44) belongs
  to which switch (`rv sch net "PFC CURRENT 2+" "PFC CURRENT 3+"`, then sheet 10) and compare with 5.1.
  PASS: the pairing PWM ↔ current channel is the same as 5.1 after the J2 move of PFC_I1 (43 → 42).
- **D2** GPIO_BYPASS_RLY (J2-17): high = relay on. Default with the FPGA unconfigured: R32 holds the gate low →
  relay open → the board runs through R27. Note for firmware: load must stay off until the relay is closed.

### E. Bring-up notes for the findings

- **E1** First mains power-up through an isolation transformer / variac with the PFC off: DC+ ≈ 325 V through DB1 and
  R27; what to check before closing the relay; flyback starts at ≈ 60 V.
- **E2** Measurements the documents leave open: L1 / L2 inductance, body position, heatsink fit, temperature of
  DB1 and R27.

## 5. Out of scope / given

- The VAC measurement (U8) and DC-link measurement (U6): checklist 09. PFC current amplifiers U4: 08. DAB and
  heater stages that load DC+: 07, 06. Whole-board creepage basis incl. mounting holes: 10. Heatsink mechanics: 12.
  Sourcing of the consigned semiconductors: 13.
- Given: bridgeless DCM PFC with the existing magnetics and semiconductors (all as on the working 5.1 board);
  UCC27511A drivers; single heatsink line; DC+ and power GND on outer layers only; 4 × 82 µF 450 V; C73 as is;
  no silkscreen; via-in-pad accepted (C73 pad 2, R93 pad 2, R21 pad 1).

## 6. Findings format

Write `kicad_next/review/findings/05_pfc_emi_inrush.md` exactly in the format of `kicad_next/review/README.md`
"Common findings format": summary; one table row per item above (A1 … E2) with **PASS / FAIL / CANNOT VERIFY** and
the evidence (file:line, command + output lines, calculation with inputs, or datasheet document / page / URL);
ranked findings with severity (**blocker for ordering / should fix / note**), what is wrong, evidence, smallest fix,
confidence; "Compared with 5.1"; "Could not verify"; "Outside scope". "Looks fine" without evidence is not
acceptable.
