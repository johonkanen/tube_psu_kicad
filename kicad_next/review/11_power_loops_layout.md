# Review checklist 11 – power loops, return paths and copper cross-sections of the whole board (compared with 5.1)

You are reviewing **one aspect** of the tube_power 5.2 power-supply board, alone, from this file and the repository
`/home/jari/dev/tube_psu_kicad`. You are doing a design review, not a redesign.

**Rules (full text: `kicad_next/review/README.md`, "Common rules" – read that section first):**
read-only on the repository, the only file you write is `kicad_next/review/findings/11_power_loops_layout.md`; no
commit, no push; never touch `kicad_next/tube_psu_5_2.kicad_pcb` / `.kicad_pro` and never run a script that saves or
regenerates design files (`route_s*.py`, `update_board_parts.py`, `setup_project.py` / `make_board.py` / generators
without `--check`); stop if a KiCad lock file exists (`rv guard`); RAM under 3 GB – no board DRC, no
`check_next.sh` (use the existing reports); never `pkill -f`; never run the KiCad AppImage with `--version`; the
owner's name / e-mail stay out of web requests. **Acceptance bar: match the bench-verified 5.1 board and add
creepage – do not optimise beyond that.** For this checklist that means: **every loop and every current path is
judged against the same loop / path on the 5.1 board** (`kicad/tube_psu.kicad_pcb`, 4 layers), which is known to
work at full load.

## 1. Scope

The board (163 × 110 mm, 6 layers: F.Cu 1 oz, In1.GND, In2.Signal_HV, In3.Power, In4.GND 0.5 oz each, B.Cu 1 oz;
stackup JLC06161H-7628D: F.Cu – 0.43 mm – In1 – 0.2 – In2 – 0.2 – In3 – 0.2 – In4 – 0.43 mm – B.Cu) carries four
switching converters that share the 400 V DC link:

| Converter | Switching loop (current path) | rms / peak current, frequency | Position |
|---|---|---|---|
| PFC leg 1 | Q5 drain → SICD1 → DC+ → C73 → GND → R93 → Q5 source | ≈ 2 – 4 A rms, ≈ 10 A peak (DCM), < 150 kHz | x 0 … 16, y −32 … −12 |
| PFC leg 2 | Q6 drain → SICD2 → DC+ → C73 → GND → R21 → Q6 source | same | x 0 … 16, y −15 … 6 |
| DAB primary | Q19 (DC+) → switch node → Q7 → DHB_CURRENT → C67 / C70 → DC+; power path through TR3 primary and C47 / C54 | 2.4 A rms, 140 kHz | x 9 … 32, y −76 … −40 |
| DAB secondary | Q21 (420V) → switch node → Q8 → ISO_GND → C55 / C16 (or the 100 nF row) → 420V | 2.3 A rms, 140 kHz | x 52 … 80, y −84 … −38 |
| Heater LLC primary | Q11 (DC+) → switch node → Q10 → HEATER_CURRENT → C20 → DC+; tank C42 / C49 / C41 / C22 – TR2 | ≈ 0.5 – 0.8 A rms, 150 – 270 kHz | x −26 … −6, y −90 … −45 |
| Heater secondary | TR2 secondary ends → Q1 / Q2 → HT_GND; centre tap → 6V3 → C31 / C32 → load | 10 – 15 A dc, ≈ 12 A rms per FET | x −70 … −38, y −90 … −60 |
| Flyback | C15 → TR1 primary (fly leads) → PWM2 drain → R8 / R9 → GND | ≈ 0.4 A rms, 1.2 A peak, 100 kHz | x 36 … 72, y −22 … 18 |

Energy storage: bulk capacitors C28, C56, C37, C29 in a column at x ≈ 20 (y −30 … 9), C73 at (12.5, −14). **Decisions
in force:** DC+ and its power-GND return run on F.Cu / B.Cu only (In1 / In4 stay GND planes, In3 holds the 15V / 5V /
+3V3 / 6V3 pours and signal lanes, In2 is a signal / HV-routing layer without pours); all primary power
semiconductors stand in one heatsink line at x 5 … 13; no switch node on an inner layer. Known weak points to
confirm or refute: **DC+ entry into Q19's drain pad 0.9 + 0.9 mm (5.1 ≈ 2.3 mm); DC+ neck at SICD1 ≈ 1.25 mm F.Cu +
1.0 mm B.Cu (5.1 ≈ 3 mm); tight gaps round D30 / R53 / R41**. The local loops are also items of checklists 02, 05,
06, 07; this checklist does the **systematic comparison with 5.1 and the shared paths between the converters**
(DC+ tree, GND returns, planes, vias, thermal spokes).

## 2. Read first

1. `kicad_next/README.md` (use `rv section`): "Power, HV and ground routing (routing stage 3a)" incl. the table
   "Current and width" and "What was routed"; "Inner layers (routing stage 2)" (per-layer content, what was not
   done and why); "Stackup" (consequences of 7628D for loops that return through a plane); "Stage 4a", "4b", "4d",
   "4g", "4h", "4j", "4k", "4l" (DAB primary under the heatsink line); "Stage 7b", "Stage 8", "Stage 9".
2. `kicad_next/routing/` PNGs: `s3a_F_Cu.png`, `s3a_B_Cu.png`, `In1_GND.png`, `In2_Signal_HV.png`, `In3_Power.png`,
   `In4_GND.png`, `s3a_power_nets.png` (view them with the Read tool; they may predate the last stages – check the
   file dates against the board with `ls -la kicad_next/routing/*.png kicad_next/tube_psu_5_2.kicad_pcb`).
3. `simulation/dab/DAB_SIMULATION.md` 2.1 (rms currents), design document p 12 – 13, 20 – 22, 25, 33 – 34
   (`rv pdf 33 34`: what was hot on 5.1).
4. Checklists 05, 06, 07 sections "Layout" in this directory, and – if they exist – their findings files in
   `kicad_next/review/findings/` (leads only; verify yourself).

## 3. How to extract facts

```sh
kicad_next/review/tools/rv guard && kicad_next/review/tools/rv setup
kicad_next/review/tools/rv bq nets '*' | grep -E "HV_PRIMARY|HV_SECONDARY"      # which HV nets have copper on which layers
kicad_next/review/tools/rv bq net DC+                    # widths per layer, narrowest segments, vias, pour pieces
kicad_next/review/tools/rv bq net GND
kicad_next/review/tools/rv bq net ISO_GND
kicad_next/review/tools/rv bq net 420V
kicad_next/review/tools/rv bq pads DC+                   # every DC+ pad with position (sources and sinks of the DC link)
kicad_next/review/tools/rv bq loop Q19.2 Q19.3 Q7.2 Q7.3 C67.2 C67.1                    # DAB primary HF loop (pad-centre polygon)
kicad_next/review/tools/rv bq51 loop Q19.2 Q19.3 Q7.2 Q7.3 C67.2 C67.1                  # the same on 5.1
kicad_next/review/tools/rv bq loop Q5.2 SICD1.A SICD1.K C73.1 C73.2 R93.2 R93.1 Q5.3   # PFC leg 1
kicad_next/review/tools/rv bq51 loop Q5.2 SICD1.A SICD1.K C73.1 C73.2 R93.2 R93.1 Q5.3
kicad_next/review/tools/rv bq loop Q6.2 SICD2.A SICD2.K C73.1 C73.2 R21.2 R21.1 Q6.3   # PFC leg 2
kicad_next/review/tools/rv bq51 loop Q6.2 SICD2.A SICD2.K C73.1 C73.2 R21.2 R21.1 Q6.3
kicad_next/review/tools/rv bq loop Q21.2 Q21.3 Q8.2 Q8.3 C55.2 C55.1 C16.2 C16.1       # DAB secondary through the split capacitors
kicad_next/review/tools/rv bq51 loop Q21.2 Q21.3 Q8.2 Q8.3 C55.2 C55.1 C16.2 C16.1
kicad_next/review/tools/rv bq loop Q11.2 Q11.3 Q10.2 Q10.3 C20.2 C20.1                 # heater bridge
kicad_next/review/tools/rv bq51 loop Q11.2 Q11.3 Q10.2 Q10.3 C20.2 C20.1
kicad_next/review/tools/rv bq neck DC+ F.Cu 12.75 -49.52 20.2 -17.2      # Q19 drain <-> bulk capacitor C56 (F.Cu alone)
kicad_next/review/tools/rv bq51 neck DC+ F.Cu 45.615 -41.949 20.2 -17.2
kicad_next/review/tools/rv bq neck DC+ F.Cu 11.8 -26.48 9.863 -14.0      # SICD1 cathode <-> C73
kicad_next/review/tools/rv bq51 neck DC+ F.Cu 11.5 -21.65 9.863 -14.0
kicad_next/review/tools/rv bq neck DC+ F.Cu -13.838 -73.55 20.2 -17.2    # heater bridge Q11 tab <-> bulk capacitor
kicad_next/review/tools/rv bq neck DC+ F.Cu 61.316 11.222 20.4 -3.8      # flyback fly lead <-> bulk capacitor C37
kicad_next/review/tools/rv bq xsec DC+ F.Cu y -40 -15 50                 # DC+ copper across a horizontal cut between the PFC and the DAB
kicad_next/review/tools/rv bq xsec DC+ B.Cu y -40 -15 50
kicad_next/review/tools/rv bq xsec GND B.Cu y -40 -15 50
kicad_next/review/tools/rv bq xsec GND In1.GND y -40 -45 60
kicad_next/review/tools/rv bq xsec GND In1.GND x 2 -91 19                # the plane edge towards the mains filter
kicad_next/review/tools/rv bq pads GND | grep -E "C28|C29|C37|C56|C73|R93|R21|R83|R30|DB1|C67|C70|C20|C15"
kicad_next/review/tools/rv bq fp Q5,Q6,Q7,Q19,Q21,Q8,Q10,Q11,SICD1,SICD2,C73,C67,C70,C20,C15,C28,C56,C37,C29
kicad_next/review/tools/rv bq51 fp Q5,Q6,Q7,Q19,Q21,Q8,Q10,Q11,SICD1,SICD2,C73,C67,C70,C20,C15,C28,C56,C37,C29
kicad_next/review/tools/rv bq51 net DC+
kicad_next/review/tools/rv bq51 net GND
python3 kicad_next/review/tools/drc_summary.py starved_thermal
ls -la kicad_next/routing/*.png kicad_next/tube_psu_5_2.kicad_pcb
```

Method notes:
- `loop` connects pad centres by straight lines: a first-order estimate of path length and area, good for the
  5.1 / 5.2 comparison, not the real copper path. Where forward and return path lie on different layers one above
  the other, the effective loop area is path length × layer distance (0.43 mm F.Cu ↔ In1, 1.6 mm F.Cu ↔ B.Cu) –
  say which case applies.
- `neck` gives the widest channel on **one layer**; results ≈ 0.9 mm from a TO-220 pin are usually the pad entry
  itself (pads 1.9 × 2.0 mm at 2.54 mm pitch with the 1.2 mm HV rule to the neighbour pads). Follow layer changes
  with the via list of `rv bq net`.
- Current capacity rule of the project (README "Current and width", ΔT ≈ 20 K): 1 oz outer I ≈ 3.25 · w^0.725 A,
  0.5 oz inner I ≈ 0.98 · w^0.725 A (w in mm); via 0.8 / 0.4 ≈ 1 A, 0.6 / 0.3 ≈ 0.7 A. You may check this fit against
  IPC-2221 / IPC-2152 figures from a fetched source.
- For custom geometry (e.g. total copper cross-section of all layers along a path) load the dump
  (`kicad_next/review/tools/rv dir` → `b52.json`, `b51.json`) in python3 with shapely as `bq.py` does.

## 4. Checklist

### A. DC-link distribution (DC+ and its return)

- **A1 DC+ map.** From `rv bq net DC+` and `rv bq pads DC+` draw (in words / a table) the DC+ tree: bulk capacitors
  (C28 (19.9, −30.2), C56 (20.2, −17.2), C37 (20.4, −3.8), C29 (19.9, 9.3)) ← SICD1.K (11.8, −26.5), SICD2.K (3.1, 1.3),
  DB1.2 (7.2, −9.6); → Q19.2 (12.75, −49.5) / C67 / C70 / C47; → Q11.2 (−13.8, −73.6) / C20 / C42 / C49; → TR1.11
  (61.3, 11.2) / C15 / R45 / C12 / R116 / R151; → R16 (sense). For each branch: layers used, narrowest width
  (`neck`), via groups. PASS: every branch is on F.Cu / B.Cu only (no In-layer track or zone on DC+), and its
  narrowest cross-section carries the branch rms current with factor ≥ 1.5 by the project rule.
- **A2 Branch currents.** PFC diodes → capacitors: ≈ 1.35 A average, 2 – 3 A rms HF; capacitors → DAB: 1.0 A dc at 400 W
  + 2.4 A rms HF closed locally by C67 / C70 / C47; capacitors → heater bridge: 0.16 – 0.25 A dc; → flyback 0.03 –
  0.05 A dc. The **100 Hz ripple current** of the load (≈ 1.3 A rms at 540 W) flows capacitors ↔ PFC, the DAB's dc
  + audio-frequency load current flows capacitors → Q19. PASS: numbers stated with their derivation and used in
  A1, A3, A4.
- **A3 Q19 drain entry (known weak point).** `rv bq neck DC+ F.Cu 12.75 -49.52 20.2 -17.2` vs
  `rv bq51 neck DC+ F.Cu 45.615 -41.949 20.2 -17.2`. Two 0.9 mm entries on F.Cu (east from zone `S4B_DC+_F`, west
  from pour 29 with its own ≈ 1.0 mm neck at x 9.6 … 10.5), nothing on B.Cu or inner layers. Compute resistance
  and dissipation of the entries at 1.7 A rms, the temperature rise (very short neck between a large pour and a
  soldered TO-220 pin → heat-sunk at both ends), and the partial inductance added to the DAB commutation loop
  (≈ 1 nH per mm of 0.9 mm wide trace over a plane 0.43 mm away – estimate). PASS: carries 1.7 A rms with factor
  ≥ 1.5 (rule: 0.9 mm ≈ 3.0 A each); verdict on "worse than 5.1 but acceptable" or "should fix" with the smallest
  fix (README "Stage 8" names it).
- **A4 SICD1 neck (known weak point).** `rv bq neck DC+ F.Cu 11.8 -26.48 9.863 -14.0`, `rv bq xsec DC+ F.Cu y -17.5 0
  30`, `rv bq xsec DC+ B.Cu y -17.5 0 30` and the 5.1 equivalents. Which current flows here: only SICD1's diode
  current to C73 / the capacitors (the direct way SICD1.K → C28 / C56 is a wide pour: `rv bq neck DC+ F.Cu 11.8
  -26.48 20.2 -17.2` ≈ 8 mm), or also DAB / heater supply current? PASS: the neck is not in series with the
  main path SICD1 → bulk capacitors, and as a branch to C73 it carries its HF current share (≤ 2 A rms) with
  factor ≥ 1.5; compare with 5.1 (≈ 3.1 mm).
- **A5 GND return of each power loop on the outer layers.** For each loop of section 1 find the return copper
  between the shunt GND pad / low-side source and the bypass capacitor's GND pad: `rv bq pads GND | grep …`,
  `rv bq neck GND B.Cu 14.975 -8.0 25.4 -3.8` (shunt R21 GND pad → GND pin of C37; a result of 0 means "not joined on
  that layer alone"), the same on F.Cu and for the other shunts / capacitors. GND on F.Cu is only ≈ 137 mm² in
  four pieces; B.Cu has ≈ 1700 mm² in 20 pieces; the planes In1 / In4 are solid (5527 mm² each). PASS: each power
  return has (a) a continuous outer-layer path **or** (b) a via group into In1 / In4 at both ends sized for the
  current (count the vias within 3 mm of each end: `rv bq net GND` prints via sizes; positions need the dump),
  and (c) the README's statement "DC+ and its GND return are kept on F.Cu / B.Cu" is true as written or the
  findings say precisely where the return relies on the planes (then judge: a plane return under an outer-layer
  DC+ pour is electrically the better loop; thermally 0.5 oz).
- **A6 Bulk capacitors.** Four cans in a column 13 mm apart, feeding left (PFC), up (DAB, heater), right (flyback).
  Thermal-relief spokes at their pins: `rv bq net DC+` shows 0.152 mm tracks (kept 5.1 spokes, 15 mm in total);
  `python3 kicad_next/review/tools/drc_summary.py starved_thermal`. Ripple current ≈ 1 – 1.5 A rms per capacitor.
  PASS: each capacitor pin is joined by ≥ 4 spokes of ≥ 0.15 mm **plus** the plane spokes on other layers, i.e.
  ≥ what 5.1 has (`rv bq51 net DC+`), or solid.
- **A7 Common impedance between converters.** Do the DAB's 140 kHz return current and the PFC's switching return
  share a narrow GND or DC+ piece (e.g. the x 9 … 13 strip under the heatsink line between y −44 and −30)?
  `rv bq xsec DC+ F.Cu y -40 -15 50`, `rv bq xsec GND B.Cu y -40 -15 50`. PASS: the DC+ / GND cross-section
  between the PFC area and the DAB area is ≥ 5 mm of 1 oz equivalent (or ≥ 5.1's: `rv bq51 xsec DC+ F.Cu y -40 -15
  50` – note 5.1's DAB bridge sat at y −42, x 30 … 50, i.e. the cut must be chosen between the capacitors and
  the bridge for each board).

### B. Commutation loops – 5.1 against 5.2 (table)

- **B1** Fill this table with `rv bq loop …` / `rv bq51 loop …` (pad-centre estimate) and with the real copper path
  (layers, widths) from `rv bq net`:

  | Loop | 5.1 path / area | 5.2 path / area | forward and return on the same layer? plane under it? | verdict |
  |---|---|---|---|---|
  | PFC leg 1, PFC leg 2, DAB primary, DAB secondary, heater bridge, flyback primary (C15 – TR1.11 – TR1.12 – PWM2 drain – R8 – GND – C15) | | | | |

  PASS per loop: 5.2 path ≤ 1.5 × and area ≤ 2 × the 5.1 value, **or** the return runs on the adjacent plane
  directly under the forward path (then the plan-view area is not the loop area – state the effective area).
  A first run of the estimate gives for the DAB primary ≈ 40 mm / 60 mm² on 5.2 against ≈ 41 mm / 9 mm² on 5.1
  (C67 / C70 are 15 mm north of Q7's source on 5.2): examine this one with the real copper – where does
  DHB_CURRENT run from Q7 pin 3 (12.75, −63.34) to C67 / C70 pad 2 (21.2, −48.0) (`rv bq net DHB_CURRENT`: F.Cu
  pieces, **a 1.2 mm track of 22.7 mm on In2**, B.Cu 0.4 mm)? Estimate the loop inductance (≈ 10 nH per cm of
  loop with ≈ 3 mm spacing; less over a plane) and the turn-off overshoot L · di/dt for 3 – 4 A in ≈ 20 ns. FAIL
  (should fix) if the HF loop is closed only through the In2 track or is > 3 × the 5.1 inductance without a
  plane-assisted return; smallest fix = a 100 nF 630 V 1210 from DC+ to DHB_CURRENT next to Q7 pin 3 / Q19 pin 2
  (is there room on B.Cu at (14 … 18, −62 … −52)? `rv bq area 13 -63 19 -51`).
- **B2 DAB secondary.** Estimate ≈ 74 mm / 37 mm² (5.2) vs ≈ 112 mm / 157 mm² (5.1) through C16 / C55: better than
  5.1 – confirm with the copper (420V pour, ISO_GND return through In1 / In4 planes: `rv bq neck ISO_GND F.Cu
  66.335 -41.949 76.1 -61.237` = not joined on F.Cu alone). PASS.
- **B3 Heater bridge.** Estimate ≈ 60 mm / 23 mm² (5.2, DPAK) vs ≈ 37 mm / 21 mm² (5.1, TO-220): path 1.6 × longer.
  Real path: C20 (−12, −83) ↔ Q11 tab (−13.8, −73.6) ↔ Q11 source (−16.1, −79.9) ↔ Q10 tab ↔ Q10 source
  (−16.0, −68.1) ↔ back to C20 pad 2 (HEATER_CURRENT). Currents are small (< 1 A) and the bridge is soft-switched.
  PASS unless the return from Q10 source to C20 is a thin or inner-layer track (`rv bq net HEATER_CURRENT`: B.Cu
  22.8 mm, In2 22.7 mm – which part is the power return and which the sense line?).
- **B4 PFC legs.** Estimate 51 mm / 49 mm² and 50 mm / 61 mm² (5.2) vs 46 mm / 73 mm² and 44 mm / 92 mm² (5.1):
  about equal. Confirm with the copper: Q5 / Q6 source → shunt on B.Cu → GND → C73 pad 2 (F.Cu, 10 vias) and
  SICD cathode → DC+ → C73 pad 1 (through the 1.3 mm neck for leg 1). PASS.

### C. Gate-drive loops (cross-check of checklists 02, 05, 06)

- **C1** For each of the eight gates (Q5, Q6, Q7, Q19, Q21, Q8, Q10, Q11) and the two SR gates (Q1, Q2): driver output
  pin → gate resistor → gate pin, and source pin → driver return pin; path length of both (from `rv bq net` of
  the gate nets and `rv bq loop DRV5.15 R26.1 R26.2 Q19.1 Q19.3 DRV5.14` style estimates), the same for 5.1.
  PASS per gate: ≤ 2 × 5.1's path or ≤ 30 mm, return on the same layer beside the gate track or on the plane
  directly below (B.Cu ↔ In4: 0.43 mm).
- **C2 Shunt inside the gate loop** (Q5, Q6, Q7, Q10: source → shunt → GND → driver GND): as on 5.1 by design.
  Check that the driver's GND pin / VDD capacitor returns to the plane close to the **shunt's GND pad** (within
  ≈ 15 mm), not across a plane cut. PASS / note per driver (DRV1, DRV2, DRV5 low side, DRV3 low side).
- **C3 Floating driver groups** stay on outer layers, 1.2 mm from other nets: covered in 02 / 06; here only the
  count: `rv bq nets '*HI_SOURCE*'`, `rv bq nets '*HI_GATE*'`, `rv bq nets 'Net-(DRV?-VDDA)'` show no inner-layer
  copper. PASS.

### D. Planes, layer use and return paths of signals

- **D1 Plane integrity.** In1 / In4 GND plane: one piece each (5527 mm²), split only at the barriers and absent
  under the mains filter (x < 2 below y −34 … by design) and under the PWM2 drain. Slots / antipad rows:
  the through-hole pin column of the heatsink line (x 12.75, y −64 … −46) and the J2 header (2 × 25 pins at
  x 33.1 / 34.4) perforate the planes: `rv bq xsec GND In1.GND x 12.75 -66 -44`, `rv bq xsec GND In1.GND x 33.8
  -24 10`. PASS: no slot longer than ≈ 15 mm cut across the return path of a fast signal or gate loop; list the
  long antipad rows and what crosses them (the nine-lane control bus on In2 round DRV5, the analog lines to J2).
- **D2 In2 – the layer without its own reference pour.** In2 lies 0.2 mm under In1 (GND) and 0.2 mm above In3
  (power pours with gaps: 15V, 5V, +3V3 "window in the In3 15V strip"). Long In2 nets: the control bus,
  HEATER_CURRENT / DHB_CURRENT sense lines, `Net-(R48-Pad2)` / `Net-(R51-Pad2)` (⅓ mains voltage), 5V (101 mm of
  track on In2!), 15V (21 mm), GND (25 mm), DHB_CURRENT 1.2 mm × 22.7 mm. `rv bq nets '*' | grep "In2"` (list),
  then for the power-ish ones (`5V`, `15V`, DHB_CURRENT) `rv bq net 5V`: width vs current (5V feeds the control
  card: how many mA through which width on 0.5 oz?). PASS: every In2 supply track carries its current with
  factor ≥ 2 by the 0.5 oz rule and has ≤ 50 mV drop (R = ρ L / (w · 17.5 µm)); no In2 track is the only return of
  a switching loop.
- **D3 In3 power pours.** 15V 592 mm², 5V 232 mm², +3V3 980 mm², 15V_ISO_SEC, 5V_ISOL, 6V3 681 mm². The 15V "spine"
  from the flyback (x 50 … 56, y −20) to DRV1, DRV5, DRV3: `rv bq net 15V` (In3 zone pieces, In2 / F.Cu / B.Cu
  tracks, narrowest). Peak gate currents are local (bypass capacitors at each driver); dc ≈ 50 – 100 mA.
  PASS: no neck < 0.5 mm in the 15V / 5V distribution; each driver has its bypass within 3 mm (checklists 02 /
  05 / 06) – only list drivers whose nearest ≥ 1 µF capacitor is > 5 mm away.
- **D4 Stackup consequence.** With 7628D the outer layers are 0.43 mm from their plane (3313: 0.1 mm): loops that
  close through the plane have ≈ 4 × the inductance per length of the earlier stackup, and outer-layer power
  pours couple ≈ 4 × less to the plane. README says "not calculated". Give the order of magnitude for the two
  loops that rely on the plane most (from B1 / A5) and say whether any conclusion of the earlier routing
  stages (written for 0.1 mm) no longer holds. Note unless it changes a B-item verdict.
- **D5 Switch-node copper area and what lies under / over it.** For PFC_DRAIN_1 (F.Cu 120 mm²), PFC_DRAIN_2
  (35 mm² + B.Cu track), DHB_HI_SOURCE (F.Cu 121 mm²), DHB_HI_SOURCE_SEC (tracks), HEATER_HI_SOURCE (F.Cu 195 mm²),
  FLY_C (F.Cu 125 + B.Cu 69 mm²): compare with 5.1 areas (`rv bq51 nets '*'` → the 5.1 names of these nets:
  `Net-(L2-2)`, `Net-(L1-1)`, DHB_HI_SOURCE, …) and list signal nets routed under each on In2 / In3 without a
  GND plane between (In1 is between F.Cu and In2 everywhere the plane exists). PASS: areas ≤ 2 × 5.1 or
  justified (heatsinking of DPAK / PWM2), no unshielded signal under a switch node.

### E. High-current paths

- **E1 Heater secondary 15 A.** Cross-check checklist 06 C5 with whole-path numbers: winding end (WP1 / WP4, TR2
  pins 6 + 7 / 9 + 10) → Q2 / Q1 drain: `rv bq neck Q13_DRAIN F.Cu -36.4 -86.4 -53.165 -85.125` (≈ 7.1 mm),
  `Q14_DRAIN` (≈ 4.5 mm) plus the same on B.Cu and the vias; source → HT_GND planes; centre tap WP2 / WP3 → 6V3
  (B.Cu 475 mm² + In3 681 mm²: `rv bq xsec 6V3 B.Cu x -60 -90 -60`, `… In3.Power …`) → C31 / C32 → terminal
  HT_6V3; return terminal HT_GND. 5.1: `rv bq51 xsec 6V3 B.Cu x -60 -90 -60` (22.9 mm vs 22.6 mm). PASS: every
  section ≥ the 5.1 cross-section (5.1 ran 10 A; the owner now wants 10 – 15 A: give the estimated ΔT at 15 A for
  the narrowest section: Q14_DRAIN 4.5 mm × 2 layers at 12 A rms).
- **E2 420 V output and −100 V bias, auxiliary outputs.** Low currents (≤ 3 A peak on 420V, mA elsewhere):
  `rv bq neck 420V F.Cu 57.215 -41.949 86.898 -61.983` (0.92 mm = the Q21 pad entry), terminals. PASS trivial;
  note the Q21 drain entry like A3.
- **E3 Mains input path.** IN1 → R27 / RL1 → CM1 → CM4 → L1 / L2: ≈ 2.5 A rms. `rv bq net RES_IN IN2 AC1 AC2 L1_PRI2
  L2_PRI2 "Net-(RL1-COM)"` (kept 5.1 pours incl. IN2 / RES_IN pours on In1 / In4 – mains on the "GND plane"
  layers by design, README "Per layer"). PASS: narrowest section ≥ 1.5 mm or ≥ 5.1's.
- **E4 Vias in power paths.** List every power path that changes layer and its via count / size: DC+ → C47 (3 + 3),
  R83 GND (3 × 0.6 / 0.3 for 2.4 A rms), C73 pad 2 (10), Q1 / Q2 tabs (12 / 16), DHB_HI_SOURCE_SEC (1 × 1.0 / 0.5 – in
  the power path?), 6V3 / HT_GND, PFC_DRAIN_2 F ↔ B. PASS: via groups ≥ 1.5 × the rms current by the README via
  rule; single vias in a > 1 A path are findings.
- **E5 Thermal-relief spokes and starved thermals.** `drc_summary.py starved_thermal`: C102 pin 1 (ISO_GND, no
  current). Power pads on spokes: bulk capacitors, L1 / L2, terminals, TO-247 / TO-220 pins in kept 5.1 pours
  (0.152 mm spokes). PASS: per pad total spoke width × layers ≥ the pin current by the rule; same as 5.1.

### F. Summary deliverable

- **F1** The B1 table completed, a second table "path, current, narrowest cross-section 5.1 / 5.2, capacity by the
  rule, margin", and the ranked list of places where 5.2 is worse than 5.1 with the smallest fix for each.
- **F2** What must be measured on the first board (VDS overshoot of Q19 / Q7 and Q5 / Q6, temperature of the Q19
  drain entry and the SICD1 neck with a thermal camera at 400 W).

## 5. Out of scope / given

- Creepage / clearance (checklist 10); component ratings (01 – 09, 13); heatsink mechanics (12); EMI filter design.
- Given – do not re-litigate: DC+ and power GND on outer layers only, In1 / In4 GND planes; single primary
  heatsink line and the part positions that follow from it; DRV5 on the bottom side west of the pin column;
  C95 0603; stackup 7628D; no silkscreen; via-in-pad is fine (do not list via-in-pad as a finding).
  You may still report that a given decision costs X nH or Y K – as a note with numbers.

## 6. Findings format

Write `kicad_next/review/findings/11_power_loops_layout.md` exactly in the format of
`kicad_next/review/README.md` "Common findings format": summary; one table row per item above (A1 … F2) with
**PASS / FAIL / CANNOT VERIFY** and the evidence (file:line, command + output lines, calculation with inputs);
ranked findings with severity (**blocker for ordering / should fix / note**), what is wrong, evidence, smallest
fix, confidence; "Compared with 5.1" (the two tables); "Could not verify"; "Outside scope". "Looks fine" without
evidence is not acceptable.
