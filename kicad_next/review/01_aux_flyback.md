# Review checklist 01 – auxiliary flyback supply (PWM2, TR1, sheet 1)

You are reviewing **one part** of the tube_power 5.2 power-supply board, alone, from this file and the repository
`/home/jari/dev/tube_psu_kicad`. You are doing a design review, not a redesign.

**Rules (full text: `kicad_next/review/README.md`, "Common rules" – read that section first):**
read-only on the repository, the only file you write is `kicad_next/review/findings/01_aux_flyback.md`; no commit, no
push; never touch `kicad_next/tube_psu_5_2.kicad_pcb` / `.kicad_pro` and never run a script that saves or
regenerates design files (`route_s*.py`, `update_board_parts.py`, `setup_project.py` / `make_board.py` / generators
without `--check`); stop if a KiCad lock file exists (`rv guard`); RAM under 3 GB – no board DRC, no
`check_next.sh` (use the existing reports); never `pkill -f`; never run the KiCad AppImage with `--version`; the
owner's name / e-mail stay out of web requests. **Acceptance bar: match the bench-verified 5.1 board and add
creepage – do not optimise beyond that.** Datasheet facts come from the datasheet you fetch now, not from memory.

## 1. Scope

The auxiliary supply starts from the DC link (DC+ 400 V nominal, design range 100 – 450 V, bench start from 60 V)
and makes every low-voltage rail of the board with one flyback: primary-side **15V** (gate drivers) and **5V**
(regulated rail; control card, logic), and across the reinforced barrier **15V_ISO_SEC**, **5V_ISOL**,
**−15V_SEC** and **−100V BIAS** (tube bias, nominal about −80 … −84 V). 5.1 used an IW1818 primary-side-regulated
controller on an EF20 (design document p 7 – 10: 10 W, 52 T primary, 72 kHz, 806 mA peak, 520 V peak drain). 5.2
replaces both: **PWM2 = Infineon ICE5AR0680AG** (CoolSET, 800 V CoolMOS, fixed 100 kHz current mode, PG-DSO-12,
error amplifier regulates the primary 5V rail through VERR) and **TR1 = EEL19 vertical 4+6, Lp 600 µH, primary on
fly leads**, sized for 12 W continuous / 20 W peak (`simulation/flyback/EEL19_DESIGN.md` sections 12 – 16;
`kicad_next/CHANGES_5_2.md` section 1).

- Sheet: `kicad_next/01_aux_supply.kicad_sch`, generator `tools/next/sheets/sheet01.py` (57 parts).
- Refdes: PWM2, TR1; D4, D5, D6, D14, D29 (ES1D), D7 (S1M clamp), D8 (US1M), D10; R8, R9 (Rcs), R45 / R72 / C12 (RCD
  clamp), R114 – R116 (start-up to GATE), R151 – R154 / C140 (line OVP on VIN), R138 / R139 (VERR), R140 / R141 /
  C138 / C139 (FB, RSel), R142 / C51 / C58 (VCC), R125 / R126 (preloads), R67 / R68 / R123 / R124 (bleeders),
  C1, C2, C3, C6, C36, C39, C40, C44, C45, C71, C102, C114, C115, C15, terminals P15V_OUT, P5V_OUT, N15V_OUT,
  N80V_OUT, SEC_GND.
- Nets: `FLY_C` (drain), DC+, `Net-(PWM2-*)`, `Net-(TR1-*)`, `Net-(D10-K)` (VCC), 15V, 5V, 15V_ISO_SEC, 5V_ISOL,
  −15V_SEC, "-100V BIAS", ISO_GND.
- Board area: x 36 … 88, y −22 … 18 (south-east corner). PWM2 at (49.8, 2.2) on F.Cu, TR1 at (63.5, −4.3) with its
  1.2 mm barrier slot at x ≈ 63.5 (y −14 … 14); primary pins 1 – 3 at x 57.3, isolated pins 5 – 10 at x 69.8, fly-lead
  holes 11 (DC+) / 12 (FLY_C) at y 11.2; secondary rectifiers and terminals at x 72 … 88.

## 2. Read first (in this order)

1. `kicad_next/CHANGES_5_2.md` section "1. Auxiliary flyback (sheet 1)" (rows 1.1 – 1.11, C102) and "Open questions"
   items 1 and 14.
2. `tools/next/sheets/sheet01.py` (245 lines; the `sh.text` notes at lines ≈ 183 – 243 state the design values).
3. `simulation/flyback/EEL19_DESIGN.md`: "Summary" (line 16), section 14 "100–450 V input with ICE5AR0680AG"
   (14.4 winding spec, 14.6 – 14.9), section 15 "Bench start-up from a 60 V lab supply", section 16 "−5 V rail → −15 V",
   section 12.5 / 12.6 (isolation of the build, PCB slot). `rv headings simulation/flyback/EEL19_DESIGN.md`.
4. Design document p 7 – 10 (`rv pdf 7 10`) and the output table on p 5: what the supply has to deliver.
5. `kicad_next/README.md`: table row "TR1" and "PWM2" in "Footprints and 3D models"; the rows "Flyback primary",
   "PWM2 drain", "Flyback windings" in "Current and width"; `S2_KO_PWM2_drain` in "Barrier gaps"; "Stage 5a".
6. `OPTIONAL_IMPROVEMENTS.md` section 1 (what was deliberately not done).
7. Datasheets to fetch: Infineon **ICE5AR0680AG** (CoolSET 5th generation fixed frequency, datasheet V2.3 or newer);
   ES1D, US1M, S1M (the LCSC parts in `rv sch bom 1`); Panasonic **EEEFTE221XAP**; Ymin **KCXE** 56 µF 250 V.

## 3. How to extract facts

```sh
kicad_next/review/tools/rv guard && kicad_next/review/tools/rv setup
kicad_next/review/tools/rv sch sheet 1                 # every part: value, footprint, pin=net
kicad_next/review/tools/rv sch ref PWM2,TR1            # pin names and nets, net classes
kicad_next/review/tools/rv sch cmp51 1                 # what differs from the 5.1 sheet
kicad_next/review/tools/rv sch bom 1                   # LCSC number, MPN, stock, status per part
kicad_next/review/tools/rv sch part R68,C102,D8        # full rows of the parts tables
kicad_next/review/tools/rv bq fp PWM2,TR1              # pad positions; "barrel only" = no inner ring
kicad_next/review/tools/rv bq area 36 -22 88 18        # every footprint of the area with side (F/B)
kicad_next/review/tools/rv bq net FLY_C                # drain copper: zone area per layer, vias
kicad_next/review/tools/rv bq near FLY_C --within 3.5  # what is close to the 620 V switching node
kicad_next/review/tools/rv bq net "Net-(PWM2-CS)" "Net-(PWM2-FB)" "Net-(PWM2-VERR)" "Net-(PWM2-VIN)" "Net-(D10-K)"
kicad_next/review/tools/rv bq dist FLY_C @SEC          # drain node to the isolated side (domain SEC), per layer
kicad_next/review/tools/rv bq padgap TR1.11 TR1.5      # fly-lead DC+ hole to the nearest isolated pin (pad edge to pad edge)
kicad_next/review/tools/rv bq padgap PWM2.4 PWM2.5     # CS pad to DRAIN pad
kicad_next/review/tools/rv bq neck DC+ F.Cu 61.316 11.222 39.2 15.863   # DC+ feed width, fly lead 11 to R116
kicad_next/review/tools/rv bq slots                    # Edge.Cuts slots (TR1: x 62.92 … 64.12)
kicad_next/review/tools/rv section simulation/flyback/EEL19_DESIGN.md '^## 15'
kicad_next/review/tools/rv pdf 7 10
```

Rated values are not in the schematic value field for most passives: read the LCSC part (`mpn`, `note` columns of
`rv sch bom 1`) and fetch its datasheet / LCSC page.

## 4. Checklist

### A. Schematic against the datasheet application circuit and the design intent

- **A1 PWM2 pin map.** `rv sch ref PWM2` against the ICE5AR0680AG datasheet pin table (PG-DSO-12): 1 VIN, 2 VERR,
  3 FB, 4 CS, 5 – 8 DRAIN, 9 NC, 10 GATE, 11 VCC, 12 GND. PASS: every pin number / name / net agrees with the
  datasheet and with the non-isolated application circuit (datasheet figure "non-isolated flyback with integrated
  error amplifier"); pin 9 has no net.
- **A2 Non-isolated mode selection.** CHANGES row "1.5 VERR": before VCC_ON the IC sources IERR_P_BIAS out of VERR and
  selects the mode from the VERR voltage. Recalculate with datasheet min / max: R138 ‖ R139 × IERR_P_BIAS(min) must
  exceed VERR_P_BIAS(max). PASS: > threshold with margin at the datasheet extremes (documented: 31.9 kΩ × 9.5 µA
  = 0.30 V > 0.24 V); FAIL if the datasheet numbers differ from those quoted in CHANGES.
- **A3 5V set point.** 5V = VERR_REF × (1 + R138 / R139) with 88.7 k / 49.9 k 0.1 %. PASS: 5.00 V nominal and the
  tolerance band (VERR_REF min / max from the datasheet) stays inside what the control card and the logic accept
  (state the limits you used; J2 pin 2 feeds the card, V4 TPS73033 needs headroom for 3.3 V).
- **A4 FB / RSel network.** R140 4.7k + C138 10n, C139 2.2n, R141 750k on FB. Check against the datasheet: RSel range
  for the chosen burst option (CHANGES row "1.5 ABM": option 2, 720 – 790 kΩ) and the limit on the FB capacitance for
  the ABM selection timing. PASS: 750 kΩ 1 % inside one option window over tolerance; τ = R141 × (C138 + C139)
  leaves the documented margin to the VCC charge time.
- **A5 Current sense.** Rcs = R8 ‖ R9 = 0.685 Ω. Recalculate the peak-current limit window from VCS_N min / max
  (datasheet) and compare with the simulated worst-case peak (EEL19_DESIGN.md 14.6 / 14.7: 0.88 A at 100 V / 20 W)
  and with core saturation (Bpk at the max limit, 14.4). PASS: needed peak < minimum limit; Bpk at maximum limit
  below the Bsat used in the document (0.39 T at 100 °C for PC40 – check that figure in a TDK PC40 datasheet).
  Also: R8 / R9 power at the rms primary current vs the 1206 rating.
- **A6 VCC supply.** 15V → R142 10R → D10 → pin 11 with C51 4.7 µF + C58 22 µF 35 V. Check VCC range in operation
  (15V rail 14.4 – 15.5 V minus the diode) against VCC_OFF / VCC_OVP, C58 polarity (`rv sch ref C58`, pad 1 = +),
  and that D10 (ZLLS400TA, 40 V Schottky) sees ≤ its rating when VCC is at VCC_ON 16 V and the 15V rail is at 0 V.
  PASS: inside the datasheet window with margin; polarity right on the board (`rv bq fp C58` pad 1 on
  `Net-(D10-K)`).
- **A7 Start-up chain to GATE.** R116 → R115 → R114 (3 × 4.7 MΩ 1206) from DC+ to pin 10. Check the datasheet's
  start-up resistor recommendation, the voltage per resistor at 450 V against the part's rated working voltage
  (LCSC C37800), and the documented claim "starts from 60 V" (EEL19_DESIGN.md 15). PASS: ≤ rated voltage per
  resistor with 450 V on the chain; start-up current ≥ the datasheet requirement at 60 V.
- **A8 Line OVP on VIN.** R151 – R153 3 × 10 MΩ, R154 178 k, C140 470 p. Recalculate the trip voltage with the
  datasheet VVIN_LOVP min / typ / max and 1 % resistors. PASS: trip above the highest normal DC link (PFC
  regulation + ripple + PFC OVP; find the PFC OVP level in the firmware notes or state it as unknown) and below
  the level where VDS exceeds 800 V − margin; voltage per 10 MΩ resistor ≤ its rating. Note the documented DNP
  option (R151 – R153 not fitted = LOVP off) and say which variant the BOM builds (`rv sch bom 1`).
- **A9 RCD clamp and VDS.** D7 S1M, R72 100R, R45 1 MΩ ‖ C12 470 p. CHANGES row "1.5 clamp" predicts VDS ≈ 570 – 600 V
  at 400 V, ≈ 630 V at 430 V and keeps the 5.1 clamp. Check the arithmetic (VOR from the turns in A11, leakage
  energy), C12 voltage rating (LCSC part) against the clamp voltage + DC+, R45 voltage and power. PASS: predicted
  VDS ≤ 80 % of 800 V at the highest DC link allowed by A8, and every clamp part inside its ratings. The planned
  bench measurement ("measure VDS on the first board") must be in the bring-up notes of your findings.
- **A10 Rectifier ratings.** For D4, D5, D6, D14, D29 (ES1D 200 V) and D8 (US1M 1000 V): V_R = V_out + V_in,max × Ns/Np
  with the turns of A11 at 450 V (and at the LOVP trip), plus ringing margin; average current vs rating. PASS:
  ≥ 30 % voltage margin for each; D8 ≥ 600 V as NEXT_REVISION 1.9 demands.
- **A11 Turns, rails and the transformer spec.** Take the winding table from EEL19_DESIGN.md 14.4 and 16
  (P 104 T in two halves on the fly leads, A5 6 T, A15 16 T, S5 6 T, SN5 16 T, S15 16 T, SHV 84 T – confirm from the
  document) and compare with the schematic pin use: TR1 1 = A15 → D5, 2 = GND, 3 = A5 → D6, 5 = SHV → D8,
  7 = S5 → D29, 8 = SN5 → D14, 9 = ISO_GND, 10 = S15 → D4, 11 = DC+, 12 = FLY_C. PASS: each rail voltage follows
  from the turns (5.9 V per 6 T reference), winding polarity / dots are consistent for the negative rails (D8 and
  D14 conduct into the winding: anode on the rail), and one document in the repo is the single winding
  specification a winder can follow (name it; FAIL if two documents disagree on turns or pins).
- **A12 Negative rails.** "-100V BIAS": D8 anode on the rail, cathode on TR1 pin 5, C102 polarity (pad 1 = + must
  be ISO_GND: `rv sch ref C102`, `rv bq fp C102`), C45 100 nF 630 V. −15V_SEC: D14, C40 22 µF 25 V, C44.
  PASS: polarities right in schematic and on the board; C102 250 V vs the highest bias voltage (bleeder-only
  case in EEL19_DESIGN.md), C40 / C44 voltage rating ≥ 25 V for a rail that reaches −16.8 V.
- **A13 Bleeders and preloads – dissipation.** For R68 (12.1 k on −100V BIAS), R124 (2.61 k on 15V_ISO_SEC),
  R125 (2.2 k on 15V), R126 (1 k on 5V), R123 (4.7 k on −15V_SEC), R67 (12.1 k on 5V_ISOL): P = V² / R at the
  highest rail voltage of the simulations against the footprint's rated power (1206 0.25 W, 0805 0.125 W unless
  the LCSC part says otherwise) and rated voltage. PASS: ≤ 60 % of rated power each. **Do the R68 number
  explicitly** (≈ 82 – 84 V across 12.1 kΩ in a 1206) and compare with what 5.1 had (`rv sch51 ref R68`,
  design document p 9).
- **A14 Output capacitors.** C1 / C2 (EEEFTE221XAP 220 µF 25 V) ripple current at 12 W / 20 W against the datasheet
  rating (CHANGES row 1.11 says "at the rating" at 20 W); C6 / C36 / C71 on 5V and C114 / C115 on 5V_ISOL: voltage
  rating and DC-bias derating of the actual LCSC parts (C71 is "100u" in a 1206 – read its part). PASS: ripple
  current ≤ rating at the continuous load (12 W); effective capacitance stated; no part above 80 % of its rated
  voltage.
- **A15 What changed and what was removed.** `rv sch cmp51 1`: the IW1818 knee-sense parts R64, R81, R84, R85, R86,
  C50 and net AUX_FB are gone, nothing else that 5.1 needed is missing, and no leftover of the old circuit
  (a pad, a net stub, a note) remains on sheet or board (`rv bq fp R64` must say "not on the board").

### B. Performance against 5.1 and the requirement

- **B1 Power budget.** Sum the loads of every rail in 5.2 (gate drivers at their switching frequencies, control
  card on 5V – find its current in `STATUS.md` / the card documents or state the assumption, isolated side,
  bias, preloads and bleeders) and compare with the 12 W continuous design point and the design document's 10 W
  (p 5, p 8). PASS: continuous load ≤ 12 W with the preloads included; say how much of it the preloads / bleeders
  are.
- **B2 Cross regulation.** From EEL19_DESIGN.md 13.2 / 14.6 / 16: the min / max of each rail over the load cases.
  PASS: 15V stays inside the UCC21520 / UCC27511 VDD window and above the 8 V UVLO with margin; 15V_ISO_SEC
  (documented up to 17.4 V bleeder-only) below the absolute maximum of DRV6 VDDA/VDDB and of C43 / C72 / C2;
  5V_ISOL inside the MIC5205 / CA-IS3761 input ranges; the bias rail inside what the amplifier needs (−80 V
  nominal, p 5).
- **B3 Loop and burst mode.** The FB compensation values are called "start values" in CHANGES (row "1.5 FB").
  Find the simulation evidence (EEL19_DESIGN.md 13.4, 14.7, `simulation/flyback/ice5ar_results.md`). PASS: a step
  response / stability result exists for the schematic values at 100 V and 450 V; otherwise CANNOT VERIFY with
  the bench test that closes it (5V load step).
- **B4 Thermal of PWM2.** EEL19_DESIGN.md 14.8 assumes ≈ 70 K/W with 2 – 3 cm² of drain copper. Measure the drain
  copper actually on the board (`rv bq net FLY_C`: F.Cu + B.Cu area, via count) and redo Tj = Ta + P × RthJA with
  the datasheet RthJA for the stated copper. PASS: Tj ≤ 110 °C at 450 V / 12 W continuous at the ambient the
  document uses; note the 20 W case separately.

### C. Layout of the part

- **C1 Drain node copper.** `rv bq net FLY_C`, `rv bq near FLY_C --within 3.5`. PASS: one compact area on F.Cu and
  B.Cu joined by vias, **no inner-layer copper of any net under it** (keep-out `S2_KO_PWM2_drain`; check with
  `rv bq xsec GND In1.GND y 5 40 48` and the same for In4.GND / In3.Power nets – expect no copper in x 40 … 48,
  y −2.6 … 14.6), ≥ 1.2 mm to other nets on outer layers, and FB / VERR / CS tracks not running along it.
- **C2 Primary switching loop.** C15 (100 nF 630 V, B.Cu at (53, −0)) → TR1 fly lead 11 → primary → fly lead 12 →
  PWM2 drain → CS → R8 / R9 → GND → C15. Trace it with `rv bq net DC+` / `FLY_C` / `"Net-(PWM2-CS)"` / pads.
  PASS: the loop is closed locally (C15 GND return and Rcs GND within ≈ 15 mm of PWM2 pin 12, not through the
  board-wide plane only); compare the loop size with 5.1 (`rv bq51 fp PWM2,TR1,C15,R8`).
- **C3 Kelvin and small-signal placement.** Rcs GND returns to pin 12; C51 at pin 11 / 12; R138 / R139 at pin 2;
  R140 / C138 / C139 / R141 at pin 3; R154 / C140 at pin 1 (CHANGES row "1.5 layout"). PASS: each within ≈ 5 mm of
  its pin (`rv bq fp ...` distances), VERR and FB nodes short (`rv bq net "Net-(PWM2-VERR)"`: total track length).
- **C4 DC+ feed and HV dividers.** DC+ arrives along the south edge (documented: 0.76 mm F.Cu, 0.5 mm from the board
  edge). `rv bq neck DC+ F.Cu 61.316 11.222 39.2 15.863`, `rv bq near DC+ --within 1.3 --layer F.Cu`. PASS:
  ≥ 0.5 mm wide for ≤ 0.4 A rms, ≥ 1.2 mm to other nets on outer layers, copper-to-edge ≥ 0.3 mm
  (README "JLC manufacturing limits"); the chains R114 – R116 and R151 – R153 have ≥ 1.2 mm between non-adjacent
  nodes.
- **C5 Secondary rectifier loops.** For each output: winding pin → diode → capacitor → return pin (ISO_GND pin 9 or
  GND pin 2). PASS: track widths ≥ the README "Flyback windings" row (0.5 – 0.8 mm for 0.6 – 0.8 A rms) and the
  first capacitor of each rail (C39 / C1, C6 / C36, C3 / C2, C114 / C115, C44 / C40, C45 / C102) sits at its diode,
  not at the terminal.
- **C6 Barrier at TR1 (local view; the whole-board creepage review is checklist 10).** `rv bq slots`,
  `rv bq near FLY_C --within 12 --other-domain`, `rv bq padgap TR1.11 TR1.5`, `rv bq padgap TR1.2 TR1.9`
  (pad edges; `rv bq dist NETA NETB` gives whole-net distances per layer with the two closest points). PASS: on outer layers the straight distance primary ↔ secondary is ≥ 4.0 mm
  (clearance) everywhere and the path round the slot ≥ 11.1 mm (README table row TR1: 12.86 mm); on inner layers
  ≥ 11.1 mm straight between any primary and secondary copper including the plated barrels (the pads have no
  inner rings); nothing of either side under the transformer body crosses x 58.5 … 68.5 on any layer except the
  transformer's own pins.
- **C7 Footprint against the real bobbin.** README "Still to confirm with calipers" lists the EEL19 4+6 base outline,
  pin diameter (drills 1.0 / 0.9 mm) and the fly-lead holes (1.2 mm). PASS only if a measurement of the bought
  bobbin is recorded somewhere in the repository; otherwise CANNOT VERIFY and a finding "measure before ordering"
  with the exact dimensions needed.
- **C8 PG-DSO-12 footprint.** `lib/tube_psu_next_parts.pretty/PG-DSO-12_3.9x9.9mm_P1.27mm.kicad_mod` against the
  datasheet package drawing (CHANGES row 1.5 quotes figure 39: e 1.27, b1 3.81 mm between pin 4 and pin 5; no
  exposed pad). PASS: pad pitch, row spacing, pad length, the two gaps and the pin-1 corner agree with the
  drawing; `rv bq padgap PWM2.4 PWM2.5` ≥ 3.0 mm.

### D. Parts of this sheet (details of sourcing belong to checklist 13)

- **D1** `rv sch bom 1`: every part has an LCSC number or is knowingly consigned (TR1 is wound by hand). List the
  parts with `review` text or low stock (R124 2.61 k: "stock 75"; PWM2: 10 pcs bought by the owner).
- **D2** The JLC package string of PWM2 is documented as wrong ("BSOP-12-EP-300mil"). State in the findings what
  the assembly house has to be told (footprint is right, their library is not), or FAIL if this is not written
  where the order is prepared (`kicad_next/fab/` notes, if they exist).

### E. Bring-up risks to list in the findings (not PASS / FAIL)

- **E1** First power-up sequence for this supply alone from a current-limited 60 V bench supply: which rails to
  probe, expected VCC / 5V timing (CHANGES rows "1.5 VCC", "1.5 start-up"), what an open-loop / wrong-mode start
  looks like (auto-restart).
- **E2** Measurements the documents postpone to the first board: VDS at 400 / 430 V, drain copper temperature, LOVP
  trip, 5V load step, bleeder-only rail voltages. Check there is a test point or terminal for each (terminals
  P15V_OUT, P5V_OUT, N15V_OUT, N80V_OUT, SEC_GND; primary 15V / 5V at J2 pin 2 or a capacitor pad).

## 5. Out of scope / given

- The choice of the ICE5AR0680AG, the EEL19 4+6 with fly leads, 600 µH, the preload values and the −15 V rail are
  decisions (CHANGES 1.1, 1.5, 1.7, 1.13). Review their implementation, not the choice.
- The winding construction and its reinforced insulation (TIW, tape) are a transformer-build topic; only check
  that one consistent specification exists (A11).
- Whole-board creepage (checklist 10), DC-link routing outside this area (11), mechanical height of TR1 / C102
  (12), sourcing (13). No silkscreen. Via-in-pad is accepted.

## 6. Findings format

Write `kicad_next/review/findings/01_aux_flyback.md` exactly in the format of `kicad_next/review/README.md`
"Common findings format": summary; one table row per item above (A1 … E2) with **PASS / FAIL / CANNOT VERIFY** and
the evidence (file:line, command + output lines, calculation with inputs, or datasheet document / page / URL);
ranked findings with severity (**blocker for ordering / should fix / note**), what is wrong, evidence, smallest fix,
confidence; "Compared with 5.1"; "Could not verify"; "Outside scope". "Looks fine" without evidence is not
acceptable.
