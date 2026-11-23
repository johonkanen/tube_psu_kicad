# Review checklist 02 – DAB gate drive (DRV5, DRV6, bootstraps, dead time, DAB_DIS, gate networks)

You are reviewing **one part** of the tube_power 5.2 power-supply board, alone, from this file and the repository
`/home/jari/dev/tube_psu_kicad`. You are doing a design review, not a redesign.

**Rules (full text: `kicad_next/review/README.md`, "Common rules" – read that section first):**
read-only on the repository, the only file you write is `kicad_next/review/findings/02_dab_gate_drive.md`; no commit,
no push; never touch `kicad_next/tube_psu_5_2.kicad_pcb` / `.kicad_pro` and never run a script that saves or
regenerates design files (`route_s*.py`, `update_board_parts.py`, `setup_project.py` / `make_board.py` / generators
without `--check`); stop if a KiCad lock file exists (`rv guard`); RAM under 3 GB – no board DRC, no
`check_next.sh` (use the existing reports); never `pkill -f`; never run the KiCad AppImage with `--version`; the
owner's name / e-mail stay out of web requests. **Acceptance bar: match the bench-verified 5.1 board and add
creepage – do not optimise beyond that.** Datasheet facts come from the datasheet you fetch now, not from memory.

## 1. Scope

The anode supply is a dual half bridge / DAB at about 140 kHz: primary bridge Q19 (high) / Q7 (low) on DC+ 400 V,
secondary bridge Q21 (high) / Q8 (low) on the 420V rail, all four STF7N60M2 (TO-220). This checklist covers how
their gates are driven. 5.1 used two Si8275BB; 5.2 uses two **UCC21520DWR** (isolated dual driver, SOIC-16W, 8 V
UVLO): **DRV5** on the primary (inputs PRI_DHB_HI = J2-4 and B12 = J2-6, supplies 5V / 15V, ground GND) and **DRV6**
on the secondary (inputs ISO_SEC_DHB_HI / ISO_SEC_DHB_LO from isolator ISO2, supplies 5V_ISOL / 15V_ISO_SEC, ground
ISO_GND). Each high side is bootstrapped (D19 / R41 / C92 for DRV5, D18 / R46 / C46 for DRV6). New in 5.2: hardware
dead-time resistors R127 / R128 10 k (100 ns) with C118 / C119, the DISABLE pin brought out as **DAB_DIS** (J2-18,
R129 pull-down, C120; through ISO2 channel C as DAB_DIS_SEC to DRV6), **DRV5 channels swapped** (A = high side),
**C95 as 0603** at DRV5 pins 11 / 9. Neither driver bridges an isolation barrier (both sides of each are in one
domain); the high-side channel floats on the switch node (0 ↔ 400 / 420 V at 140 kHz).

- Sheets: `kicad_next/02_dhb_gate_drive.kicad_sch` (generator `tools/next/sheets/sheet02.py`, 24 parts) and the gate
  networks on `07_dhb.kicad_sch` (`sheet07.py`).
- Refdes sheet 2: DRV5, DRV6, D18, D19, R41, R46, C46, C92, C43, C72, C93, C94, C95, C96, C118, C119, C120,
  R73 – R76 (input pull-downs), R127, R128, R129. Sheet 7 gate parts: Q19: R26 (40R on), R53 + D30 (3.3R off),
  R22 (10k G-S); Q7: R90, R92 + D34, R70; Q21: R57, R58 + D31, R56; Q8: R87, R88 + D32 (no G-S resistor).
- Nets: PRI_DHB_HI, B12, DAB_DIS, DAB_DIS_SEC, ISO_SEC_DHB_HI, ISO_SEC_DHB_LO, `Net-(DRV5-DT)`, `Net-(DRV6-DT)`,
  DHB_HI_GATE, DHB_LOW_GATE, `Net-(Q19-G)`, `Net-(Q7-G)`, `Net-(D30-PadA)`, `Net-(D34-PadA)`, `Net-(DRV5-VDDA)`,
  `Net-(D19-K)`, DHB_HI_SOURCE (primary switch node), and the `_SEC` / Q21 / Q8 / DRV6 / D18 / D31 / D32
  counterparts, DHB_HI_SOURCE_SEC.
- Board: DRV5 on **B.Cu** at (2.3, −49.9), inputs (pins 1 – 8) on x −2.35, outputs (9 – 16) on x 6.95, 5 mm west of
  the pin column of Q19 (pins at x 12.75, y −46.98 G / −49.52 D / −52.06 S) and Q7 (y −58.26 G / −60.80 D /
  −63.34 S); gate parts on B.Cu at x 9 … 17, y −60 … −42. DRV6 on B.Cu at (61.0, −57.0), Q21 at (60, −42), Q8 at
  (71, −42), its gate parts at x 56 … 75, y −67 … −44.

## 2. Read first

1. `kicad_next/CHANGES_5_2.md` section "3. Gate drivers" rows 3.1, 3.1b, 3.1c, 3.2, 3.3, "3a DRV6 input side"; row 2.7
   (dead time); "Open questions" 4 and 5.
2. `tools/next/sheets/sheet02.py` (47 lines) and the gate-network part of `tools/next/sheets/sheet07.py`.
3. `kicad_next/README.md` sections (use `rv section kicad_next/README.md 'Stage 4f'` etc.): "Stage 4f" (channel
   swap), "Stage 4g", "Stage 4h", "Stage 4i", "Stage 4j" (R22, bootstrap charge path, C95, C70), "Stage 4l step B"
   (D30 / R53), "Stage 8" (C95 0603), and for DRV6 "TR3 secondary finish on pins 11 / 12, heater gate parts at
   their FETs", "Stage 5c".
4. `kicad_next/tube_psu_5_2.kicad_dru`: rules "HV functional, outer layers" and "High-side driver group DRV5 /
   DRV6" (lines ≈ 59 – 82) – inside one floating driver group 0.2 mm is allowed.
5. `simulation/dab/DAB_SIMULATION.md` section 3 "Recommendations" (dead time 150 ns, start-up) and 2.8.
6. Design document p 23 – 27 (`rv pdf 23 27`), p 25 for the start-up with the bootstrap.
7. Datasheets to fetch: TI **UCC21520** (SLUSCJ9, latest revision; pin functions, DT equation, DISABLE, recommended
   layout, absolute maximums, switching characteristics), ST **STF7N60M2** (Qg, Vgs(th), Vgs max, Ciss),
   **S1M** (LCSC C64915) and **ZLLS400TA**, Chipanalog **CA-IS3761LW** (propagation delay / skew, default state).

## 3. How to extract facts

```sh
kicad_next/review/tools/rv guard && kicad_next/review/tools/rv setup
kicad_next/review/tools/rv sch sheet 2
kicad_next/review/tools/rv sch ref DRV5,DRV6
kicad_next/review/tools/rv sch cmp51 2                  # the 5.1 -> 5.2 pin / part changes of the sheet
kicad_next/review/tools/rv sch net DHB_HI_GATE "Net-(Q19-G)" "Net-(D30-PadA)" DHB_LOW_GATE "Net-(Q7-G)" "Net-(Q8-G)" "Net-(Q21-G)"
kicad_next/review/tools/rv sch net DAB_DIS DAB_DIS_SEC B12 PRI_DHB_HI ISO_SEC_DHB_HI ISO_SEC_DHB_LO
kicad_next/review/tools/rv sch bom 2
kicad_next/review/tools/rv bq fp DRV5,Q19,Q7,C95,C96,C92,R41,D19,R26,R53,D30,R22,R90,R92,D34,R70
kicad_next/review/tools/rv bq fp DRV6,Q21,Q8,C46,C72,C43,R46,D18,R57,R58,D31,R56,R87,R88,D32
kicad_next/review/tools/rv bq net DHB_HI_GATE "Net-(Q19-G)" DHB_LOW_GATE "Net-(Q7-G)" "Net-(DRV5-VDDA)" "Net-(D19-K)"
kicad_next/review/tools/rv bq net DHB_HI_GATE_SEC "Net-(Q21-G)" DHB_LOW_GATE_SEC "Net-(Q8-G)" "Net-(DRV6-VDDA)"
kicad_next/review/tools/rv bq padgap DRV5.11 C95.2      # decoupling distance at VDDB
kicad_next/review/tools/rv bq padgap DRV5.9 C95.1
kicad_next/review/tools/rv bq padgap DRV5.16 C92.2      # bootstrap capacitor at VDDA / VSSA
kicad_next/review/tools/rv bq padgap DRV5.14 C92.1
kicad_next/review/tools/rv bq padgap DRV5.11 DRV5.14    # 15 V pin to the floating channel, with NC pads 12 / 13 between
kicad_next/review/tools/rv bq near DHB_HI_SOURCE --within 1.3 --layer B.Cu
kicad_next/review/tools/rv bq near "Net-(Q19-G)" --within 1.3
kicad_next/review/tools/rv bq near DHB_HI_SOURCE_SEC --within 1.3 --layer B.Cu
kicad_next/review/tools/rv bq51 fp DRV5,Q19,Q7,C95,C92  # where the same parts are on the 5.1 board
python3 kicad_next/review/tools/drc_summary.py courtyards_overlap -5 -62 20 -40
kicad_next/review/tools/rv section kicad_next/README.md 'Stage 4f'
```

Gate-loop length: add the track lengths that `rv bq net` prints for driver OUT → gate resistor → gate pin and for
the return (source pin → VSSx pin), plus pad-centre distances from `rv bq fp`. Loop area is best judged from the
coordinates of those segments (same layer, how far apart forward and return path run).

## 4. Checklist

### A. Schematic against the UCC21520 datasheet and against 5.1

- **A1 Pin map.** `rv sch ref DRV5,DRV6` against the datasheet pin table (DW package): 1 INA, 2 INB, 3 VCCI, 4 GND,
  5 DISABLE, 6 DT, 7 NC, 8 VCCI, 9 VSSB, 10 OUTB, 11 VDDB, 12 / 13 NC, 14 VSSA, 15 OUTA, 16 VDDA. PASS: every pin
  agrees; both VCCI pins (3 and 8) are wired; the NC pins have no net.
- **A2 Channel swap of DRV5 (CHANGES 3.1b).** PASS if all of these hold: INA (pin 1) = PRI_DHB_HI = J2-4; OUTA (15) =
  DHB_HI_GATE → R26 → Q19 gate; VDDA (16) = bootstrap node (R41, C92); VSSA (14) = DHB_HI_SOURCE = Q19 source = Q7
  drain; INB (2) = B12 = J2-6; OUTB (10) = DHB_LOW_GATE → R90 → Q7 gate; VDDB (11) = 15V; VSSB (9) = GND; and
  `kicad_next/J2_PINOUT.md` rows 4 and 6 say the same. Compare with 5.1 (`rv sch cmp51 2`): J2-4 still switches
  the high side and J2-6 the low side, i.e. **the firmware-visible function of each J2 pin is unchanged**. FAIL
  if the swap exchanged the meaning of J2-4 / J2-6.
- **A3 DRV6 mapping.** INA = ISO_SEC_DHB_HI (ISO2 pin 15) → OUTA → Q21 (high, on 420V); INB = ISO_SEC_DHB_LO
  (ISO2 pin 14) → OUTB → Q8 (low). Follow both back through ISO2 to J2 (EPWM2A = J2-10 → ISO2 pin 2, EPWM2B =
  J2-12 → pin 3) and state which J2 pin drives which secondary FET; compare with 5.1. PASS: same assignment as
  5.1, or the difference is documented in CHANGES.
- **A4 Dead-time pin.** R127 / R128 10 k with C118 / C119 100 pF on DT. Check the datasheet DT equation and the
  allowed resistor range, the recommended capacitor on DT, and what the datasheet says about the DT pin left
  with a large capacitance. PASS: DT ≈ 100 ns nominal with the datasheet tolerance stated, below the 150 ns
  firmware dead time (CHANGES 2.7) over tolerance, capacitor within the datasheet recommendation.
- **A5 DISABLE.** DAB_DIS: J2-18 → DRV5 pin 5 and ISO2 pin 4 → pin 13 → DRV6 pin 5; R129 10 k to GND, C120 1 nF.
  Check DISABLE polarity and thresholds in the datasheet (high = outputs off), its internal pull, the filter
  time constant R129 × C120 against the datasheet's recommendation, and the state of DRV6 when the primary is
  unpowered or ISO2's side 1 is unpowered (CA-IS3761**L** = default low → DRV6 **enabled**). PASS: default
  (J2-18 not driven) = both drivers enabled, as 5.1's EN-tied-high, and with the PWM inputs pulled down
  (R73 – R76) both bridges are off; note in the findings that the secondary driver cannot be disabled if the
  isolator input side loses power, and whether that is worse than 5.1 (it is not if 5.1 had no disable).
- **A6 Input levels.** PWM inputs are 3.3 V logic from the FPGA (J2) on DRV5 and CA-IS3761 outputs at AD2_3V3 /
  5V_ISOL level on DRV6 (find the ISO2 side-2 supply: `rv sch ref ISO2` pin 16) with VCCI = 5V / 5V_ISOL. PASS:
  input high threshold of the UCC21520 at VCCI 5 V is met by 3.3 V logic with margin (datasheet VINAH), the
  pull-downs R73 – R76 hold the inputs low with the connector unplugged.
- **A7 Supplies and UVLO.** VCCI 5V (C94) and 5V_ISOL (C93); VDDB 15V (C95 4.7 µF 0603, C96 1 µF) and 15V_ISO_SEC
  (C72 4.7 µF, C43 1 µF). Datasheet: VDD recommended range and UVLO thresholds of the plain UCC21520 (8 V class).
  PASS: 15V 14.2 – 15.5 V and 15V_ISO_SEC up to 17.4 V (bleeder-only case of the flyback,
  `simulation/flyback/EEL19_DESIGN.md` 13.2) are inside the recommended VDD range and below the absolute
  maximum; UVLO well below the lowest rail.
- **A8 Bootstrap network.** D19 / D18 are **S1M** (1000 V standard recovery, LCSC C64915) with R41 / R46 2 Ω and
  C92 / C46 1 µF X7R 50 V. Calculate: charge per cycle (Qg of the STF7N60M2 at 15 V + driver quiescent current /
  140 kHz), droop on 1 µF, refresh time available at the smallest low-side on-time, peak charging current
  15 V / 2 Ω through the diode. Check the UCC21520 datasheet's bootstrap-diode recommendation (fast recovery)
  against a standard-recovery S1M at 140 kHz: reverse-recovery charge × 400 V × f as a loss and as a discharge
  of C92. **5.1 used the same S1M / 2 Ω / 1 µF** (`rv sch51 ref D19,R41,C92`) and works – so the verdict is PASS
  if nothing is worse than 5.1, with a note quantifying the recovery loss; FAIL only if a 5.2 change (driver
  type, UVLO, layout) makes the old network insufficient.
- **A9 C95 0603 X5R 25 V on the 15V rail (CHANGES 3.1c; known open point: derating not calculated).** Fetch the
  datasheet / DC-bias curve of CGA0603X5R475K250JT (LCSC C6119856) or, if no curve exists, of a comparable
  4.7 µF 25 V X5R 0603. Calculate the effective capacitance at 15 V and compare with the 1206 X7R 50 V of 5.1 and
  with the datasheet's minimum VDD bypass recommendation; add C96 1 µF 1206 (where is it? `rv bq fp C96` – it is
  at (28, −43), some 20 mm from the pins). PASS: effective capacitance at the pins (C95 derated) ≥ 10 × the
  charge delivered per switching event divided by the allowed droop (state the numbers), and ≥ the datasheet
  minimum. Otherwise a finding with the smallest fix (e.g. a higher-voltage or larger-value 0603 from the JLC
  list, same footprint).
- **A10 Gate networks.** Turn-on 40 Ω (R26 / R90 / R57 / R87), turn-off 3.3 Ω + ZLLS400TA (R53 + D30 etc.), G-S 10 k
  (R22 / R70 / R56; none on Q8). `rv sch51 net "Net-(Q8-G)"` shows 5.1 had none on Q8 either. Check: diode
  direction (anode towards the gate side: `Net-(D30-PadA)` – R53 – gate; cathode on the driver output), peak
  currents 15 V / 40 Ω and 15 V / 3.3 Ω against the driver's 4 A / 6 A and the diode's peak rating, resistor power
  = Qg × Vdrive × f split by resistance (0805 parts), Vgs max of the FET. PASS: identical values and topology
  to 5.1 (`rv sch51 sheet 7`), every part inside its ratings. Note the missing Q8 pull-down as "as 5.1".
- **A11 Miller immunity.** With 3.3 Ω + Schottky turn-off and dv/dt of the switch node (take dv/dt from
  DAB_SIMULATION.md or 400 V / 20 ns as a bound), estimate the induced gate voltage Crss × dv/dt × Rg,off
  against Vgs(th) min of the STF7N60M2. PASS: below threshold with margin; same as 5.1 otherwise note.
- **A12 Dead time vs propagation mismatch.** Primary path: FPGA → DRV5 (one driver, matched channels). Secondary
  path: FPGA → ISO2 (CA-IS3761LW channel-to-channel skew) → DRV6. Sum the worst-case pulse-width distortion and
  channel skew of isolator and driver and compare with (150 ns firmware dead time − 100 ns hardware DT).
  PASS: effective dead time at the gates stays positive and ≥ the hardware 100 ns in the worst case; state the
  numbers and the datasheet rows used.

### B. Layout – primary driver DRV5 (B.Cu, x −4 … 17, y −62 … −40)

- **B1 Decoupling at the pins.** C95 at pins 11 / 9 (documented: 1.2 mm / 0.2 mm pad gaps), C94 at pin 3 / 4 (and
  pin 8?), C92 at pins 16 / 14. `rv bq padgap ...`. PASS: VDDB bypass ≤ 3 mm from pins 11 and 9 with its own GND
  via next to pin 9; bootstrap capacitor ≤ 5 mm from pins 16 / 14; a VCCI capacitor within 5 mm of pin 3 **or**
  pin 8 and both pins fed (`rv bq net 5V`: is pin 8 connected by copper, not only in the netlist? –
  unconnected would show in the DRC report: `python3 kicad_next/review/tools/drc_summary.py` must show
  unconnected_items 0).
- **B2 High-side gate loop.** OUTA (pin 15) → R26 → Q19 gate, return Q19 source (pin 3) → VSSA (pin 14).
  `rv bq net DHB_HI_GATE "Net-(Q19-G)"`, `rv bq near DHB_HI_SOURCE --within 1.3 --layer B.Cu`. PASS: the return
  runs beside or under the gate path on the same or the facing layer (README "Stage 4g": return on x 10.25, then
  y −52.06), total loop path ≤ ≈ 40 mm, **gate and source tracks do not cross the DC+ entry of Q19 pin 2 with
  less than 1.2 mm**, and the loop is not longer than on 5.1 by more than a factor 2 (`rv bq51 net DHB_HI_GATE`,
  `rv bq51 fp DRV5,Q19`) – or the README records the owner's acceptance.
- **B3 Low-side gate loop.** OUTB (pin 10) → R90 → Q7 gate; return Q7 source (DHB_CURRENT, through shunt R83 to
  GND) → VSSB (pin 9, GND). The shunt is inside the gate loop by design (design document p 13 describes this for
  the PFC). PASS: the GND return from R83 to pin 9 / C95 is a short, wide path (plane vias at both ends:
  `rv bq net GND` near (8.25, −54.3) and (15 … 18.5, −64.7)); DHB_LOW_GATE (0.2 mm between the C95 pads for
  1.6 mm) carries ≤ 4.5 A peak for ≤ 20 ns – state why that is acceptable or not.
- **B4 Turn-off branches.** D30 / R53 (Q19) at (15 … 16, −45 … −44), D34 / R92 (Q7) at (13 … 15, −57 … −55) – known
  tight spot "D30 / R53 / R41". `rv bq near "Net-(D30-PadA)" --within 0.6`, `rv bq padgap D30.A R53.1`,
  `python3 kicad_next/review/tools/drc_summary.py courtyards_overlap 8 -47 18 -40`. PASS: every gap ≥ 0.2 mm
  inside the high-side group and ≥ 1.2 mm to copper outside the group on B.Cu (`rv bq near "Net-(D19-K)"
  --within 1.3`), no body overlap (0805 body 2.0 × 1.25, SOD-323 1.7 × 1.25, 1206 3.2 × 1.6 at the positions from
  `rv bq fp`), parts can be placed and reflowed on the bottom side next to the Q19 through-hole pins
  (≥ 0.5 mm from the TO-220 pad edges for hand soldering of the TO-220 after SMT).
- **B5 Bootstrap charge path.** 15V → D19 (23, −42) → R41 (13, −42) → C92 (9, −47) → pin 16; return C92 pad 1 →
  switch node → Q7 → shunt → GND. D19 stands ≈ 14 mm from the driver. PASS: track widths ≥ 0.3 mm for the 7.5 A
  peak / mA average (state), `Net-(D19-K)` (HV side of the diode, swings with the switch node) keeps 1.2 mm to
  non-group copper on outer layers, and the D19 anode has a 15V bypass nearby (C96 at (28, −43)).
- **B6 Floating group against everything else.** Group nets: DHB_HI_GATE, DHB_HI_SOURCE, `Net-(DRV5-VDDA)`,
  `Net-(D19-K)`, `Net-(D30-PadA)`, `Net-(Q19-G)`. For each: `rv bq near NET --within 1.3 --layer B.Cu` and
  `--layer F.Cu`. PASS: nothing outside the group closer than 1.2 mm on outer layers (pad-to-pad pairs of one
  footprint are exempt by rule – list them and give the gap); on inner layers ≥ 0.5 mm, and **no group net on an
  inner layer at all** (`rv bq nets 'DHB_HI*'` shows only F.Cu / B.Cu tracks).
- **B7 Driver pins 11 ↔ 14 (15 V ↔ switch node, 400 V).** `rv bq padgap DRV5.11 DRV5.14` (3 pitches) with the NC pads
  12 / 13 between them. Check the datasheet statement on the NC pins and on channel-to-channel isolation
  (functional, 1500 V DC) and its layout recommendation for the space between the two output channels.
  PASS: pads 12 / 13 have no track, no via, no pour connected or passing between them on B.Cu
  (`rv bq near "unconnected-(DRV5-NC-Pad12)" --within 0.7`), and nothing but the package pads reduces the
  pin 11 ↔ pin 14 distance.
- **B8 Inputs under the heatsink line.** PRI_DHB_HI, B12, DAB_DIS run on In2 / In3 past H4 and the Q19 pins
  (README "Stage 4i": window in the In3 15V strip). `rv bq net PRI_DHB_HI B12 DAB_DIS`, `rv bq near PRI_DHB_HI
  --within 1.0 --other-class`. PASS: ≥ 0.5 mm to HV_PRIMARY copper on inner layers, a GND plane (In1 or In4)
  between these lanes and the F.Cu / B.Cu switch-node copper wherever they overlap in plan view (compare the
  lane coordinates with `rv bq xsec GND In1.GND y -50 -5 20`), series / pull-down parts (R73, R74) at the driver.

### C. Layout – secondary driver DRV6 (B.Cu, x 54 … 76, y −68 … −42)

- **C1** Same as B1 for DRV6: C72 / C43 at pins 11 / 9, C93 at pins 3 / 8, C46 at pins 16 / 14 (`rv bq padgap
  DRV6.11 C72.2`, `DRV6.16 C46.2`). Same PASS criteria.
- **C2** Same as B2 / B3 for Q21 (gate parts R57 / R58 / D31 / R56 at (57 … 60, −49 … −44)) and Q8 (R87 / R88 / D32 at
  (72 … 74, −48 … −45)). Q21 is ≈ 15 mm and Q8 ≈ 18 mm from DRV6: give the loop path lengths and compare with 5.1
  (`rv bq51 fp DRV6,Q21,Q8`). README "Stage 5c" routed DHB_LOW_GATE_SEC as a 0.3 mm In3 lane of 17 mm inside the
  15V_ISO_SEC plane. PASS: gate and return paths are paired (the In3 lane has ISO_GND plane on In4 under it for
  its whole length: `rv bq net DHB_LOW_GATE_SEC`, `rv bq xsec ISO_GND In4.GND y -54.1 55 76`), width ≥ 0.3 mm,
  loop not worse than 2 × the 5.1 loop or accepted in the README.
- **C3** The secondary floating group (DHB_HI_GATE_SEC, DHB_HI_SOURCE_SEC, `Net-(DRV6-VDDA)`, `Net-(D18-K)`,
  `Net-(D31-PadA)`, `Net-(Q21-G)`) against everything else: as B6, with `rv bq near DHB_HI_SOURCE_SEC --within 1.3`.
- **C4** ISO2 → DRV6 inputs: ISO_SEC_DHB_HI / LO / DAB_DIS_SEC with R75 / R76 at (73, −61). PASS: pull-downs at the
  driver end or within 15 mm, lanes not parallel to the 420 V switch node (DHB_HI_SOURCE_SEC F.Cu track of 31 mm
  east of the TR3 band) for more than ≈ 10 mm on an adjacent layer without a plane between.

### D. What changed 5.1 → 5.2 (explicit)

- **D1** Si8275BB → UCC21520DWR on both: pin-for-pin? `rv sch cmp51 2` lists pin 5 (5V → DAB_DIS), pin 6
  (NC → DT). PASS: no other functional pin difference between the two datasheets is left unhandled (UVLO class,
  input logic levels, output polarity, deglitch / minimum pulse width vs the shortest PWM pulse the firmware
  makes during soft start – design document p 25 "half length first pulse").
- **D2** R25 / R40 removed, R127 – R129, C118 – C120 added: present in schematic, board and BOM (`rv sch bom 2`,
  `rv bq fp R127,R128,R129,C118,C119,C120`).
- **D3** Footprint change SOIC-16 narrow (5.1) → SOIC-16W 7.5 mm: `rv bq fp DRV5` pad pitch 1.27, row distance
  9.3 mm between pad centres; compare with the datasheet land pattern (DW0016B). PASS: within the datasheet
  land pattern tolerances.
- **D4** ERC: `python3 kicad_next/review/tools/drc_summary.py erc` shows `ground_pin_not_ground` on pin 14 (VSSA) of
  DRV5 and DRV6 (and DRV3 on sheet 6). README "Regenerate / check" documents **2** such warnings and 14 in total;
  the report has 3 and 15. PASS for the circuit (VSSA is the switch node by design); record the count mismatch
  as a documentation finding.

### E. Bring-up notes for the findings (not PASS / FAIL)

- **E1** Which signals to probe first with DC+ at 0 V: 15 V at pins 11 / 16 (bootstrap charges only when Q7 has
  been on), the DT pin voltage, DISABLE low. Is there any accessible point for the gate signals on the bottom
  side under the heatsink line once the heatsink is mounted?
- **E2** Firmware-facing facts to hand over: J2-4 high side, J2-6 low side, J2-18 high = all four gates off,
  hardware dead time 100 ns, minimum firmware dead time, bootstrap pre-charge (low side on first).

## 5. Out of scope / given

- The power loop of the bridges, split capacitors, TR3 (checklist 07); shunt R83 and DHB_I measurement (08);
  ISO2 as a barrier part and creepage (03, 10); thermal / heatsink (12).
- Given: UCC21520 for all bridges; DRV5 channel swap; C95 as 0603 at the pins; DRV6 input side stays on the
  secondary behind ISO2; DAB_DIS pull-down (enabled by default); no silkscreen; via-in-pad accepted (C95 pads,
  DRV5 pad 11).

## 6. Findings format

Write `kicad_next/review/findings/02_dab_gate_drive.md` exactly in the format of `kicad_next/review/README.md`
"Common findings format": summary; one table row per item above (A1 … E2) with **PASS / FAIL / CANNOT VERIFY** and
the evidence (file:line, command + output lines, calculation with inputs, or datasheet document / page / URL);
ranked findings with severity (**blocker for ordering / should fix / note**), what is wrong, evidence, smallest fix,
confidence; "Compared with 5.1"; "Could not verify"; "Outside scope". "Looks fine" without evidence is not
acceptable.
