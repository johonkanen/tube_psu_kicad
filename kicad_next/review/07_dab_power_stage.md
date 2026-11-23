# Review checklist 07 – DAB / dual half bridge power stage 400 V ↔ 420 V (Q7 / Q19, Q8 / Q21, split capacitors, TR3)

You are reviewing **one part** of the tube_power 5.2 power-supply board, alone, from this file and the repository
`/home/jari/dev/tube_psu_kicad`. You are doing a design review, not a redesign.

**Rules (full text: `kicad_next/review/README.md`, "Common rules" – read that section first):**
read-only on the repository, the only file you write is `kicad_next/review/findings/07_dab_power_stage.md`; no commit,
no push; never touch `kicad_next/tube_psu_5_2.kicad_pcb` / `.kicad_pro` and never run a script that saves or
regenerates design files (`route_s*.py`, `update_board_parts.py`, `setup_project.py` / `make_board.py` / generators
without `--check`); stop if a KiCad lock file exists (`rv guard`); RAM under 3 GB – no board DRC, no
`check_next.sh` (use the existing reports); never `pkill -f`; never run the KiCad AppImage with `--version`; the
owner's name / e-mail stay out of web requests. **Acceptance bar: match the bench-verified 5.1 board and add
creepage – do not optimise beyond that.** Datasheet facts come from the datasheet you fetch now, not from memory.

## 1. Scope

The anode supply: **400 V DC link → 420 V (design document: 410 V, 1 A; 400 W; up to 3 A peak), isolated,
bidirectional**, as a dual half bridge (the documents say DHB and DAB for the same circuit) at about 140 kHz,
phase-shift controlled by the FPGA (design document p 23 – 27). Primary half bridge Q19 (high, drain DC+) / Q7 (low,
source through shunt R83 4 mΩ to GND) with the split capacitor C47 (DC+ → `DHB_CAP`) / C54 (`DHB_CAP` →
DHB_CURRENT), each 1 µF 630 V X7R 2220; the transformer primary lies between the switch node DHB_HI_SOURCE and
`DHB_CAP`. Secondary half bridge Q21 (high, drain 420V) / Q8 (low, source ISO_GND) with C16 (420V → `TRANS_SEC`) /
C55 (`TRANS_SEC` → ISO_GND); output capacitors C19, C30 (68 µF 450 V) and six 100 nF 630 V; terminals P400V
(420V) and GND (ISO_GND). All four switches STF7N60M2 (TO-220). **New in 5.2: TR3 = EC42/15 PC40 two-chamber
transformer 20 : 21 whose leakage (≈ 41 µH) is the series inductance – the external inductor L3 (70 µH) of 5.1 is
removed**; magnetising inductance ≈ 200 µH by gap, set by measurement; balancing resistors R143 – R150 (8 × 220 k)
across the four split capacitors; 100 nF parts now 630 V 1210; C19 / C30 39 → 68 µF; Q19 / Q7 moved into the single
primary heatsink line at x 12.75 with DC+ on the outer layers only; Q21 / Q8 keep their own secondary heatsink.
Simulated operating point (`simulation/dab/DAB_SIMULATION.md`): 400 W, primary current 2.4 A rms, secondary
2.3 A rms, dead time 150 ns.

- Sheet: `kicad_next/07_dhb.kicad_sch`, generator `tools/next/sheets/sheet07.py` (245 lines, 53 parts). Gate
  networks and drivers are checklist 02; the 420 V sense dividers R23 / R34 / R39 / R38 / C27 / R118 – R120
  checklist 03; shunt amplifier checklist 08.
- Refdes here: Q7, Q19, Q8, Q21, C47, C54, C16, C55, R143 – R150, C67, C70, R83, TR3, C19, C30, C89, C90, C91, C99,
  C100, C101, P400V, GND (terminal).
- Nets: DC+, DHB_HI_SOURCE, `DHB_CAP`, DHB_CURRENT, GND; 420V, DHB_HI_SOURCE_SEC, `TRANS_SEC`, ISO_GND;
  `Net-(R143-Pad2)`, `Net-(R145-Pad2)`, `Net-(R147-Pad2)`, `Net-(R149-Pad2)`.
- Board: primary bridge at x 9 … 32, y −76 … −40 – Q19 pins at (12.75, −46.98 G / −49.52 D / −52.06 S), Q7 pins at
  (12.75, −58.26 G / −60.80 D / −63.34 S), R83 (15.9, −64.0) F.Cu, C67 / C70 (19.7, −48.0) F / B, C47 (22.9, −71.7),
  C54 (22.9, −63.7), balancing resistors on B.Cu at (23 … 24, −88 … −74). TR3 at (49.5, −69.3), body box x 26 … 73,
  y −91 … −48: primary pins 4 / 5 at (29.5, −71.8 / −66.8) = `DHB_CAP`, 7 / 8 at (29.5, −56.8 / −51.8) = switch node;
  secondary pins 9 / 10 at (69.5, −51.8 / −56.8) = `TRANS_SEC`, 11 / 12 at (69.5, −61.8 / −66.8) = secondary switch
  node; a 12 mm barrier keep-out band under the bobbin divider (x 42.5 … 54.5). Secondary bridge: Q21 pins at
  (59.76 G / 57.22 D / 54.68 S, −41.95), Q8 pins at (71.42 G / 68.88 D / 66.34 S, −41.95), C16 (76.1, −50.6),
  C55 (76.1, −58.6), R147 – R150 on B.Cu under them, output capacitors and terminals at x 72 … 89, y −84 … −44.

## 2. Read first

1. Design document p 23 – 27 and p 33 (`rv pdf 23 27`): topology, 26 : 29 turns and external inductor of the old
   design, start-up with a half-length first pulse, thermal result.
2. `simulation/dab/DAB_SIMULATION.md`: sections 1, 2.1 (400 W waveforms / rms), 2.2 – 2.4 (ZVS, light load, gap / Lm),
   2.5 (transformer voltage stress), 2.8 (start-up and the split capacitors), 3 (recommendations), 5 (caveats).
3. `simulation/dab/DAB_TRANSFORMER.md`: sections 1, 3.3 (options A / B), 4 (gap), 5 (winding specification), 6 (what
   to measure on the first sample), 8 (reinforced isolation of the transformer).
4. `kicad_next/CHANGES_5_2.md` section "2. DAB transformer (sheet 7)" rows 2.1 – 2.8 and "Transformer pins and winding
   tables" (TR3 table); section 5 rows 5.2b, 5.6.
5. `tools/next/sheets/sheet07.py` (notes at lines ≈ 194 – 197, 242).
6. `kicad_next/README.md`: "Current and width" (the five DAB rows), "Stage 4a" (heatsink line), "Stage 4b: DAB
   primary power on F.Cu", "Stage 4d: shunt R83 at Q7 pin 3", "Stage 4k", "Stage 7" (420 V 1210 pitch, R83 vias),
   "Stage 7b" (DC+ to C47, DC bus into Q19 pin 2), "Stage 8" (table "DC+ into Q19 pin 2"), "Stage 9";
   "Stage 3a.3" (Q8 pin 2); "TR3 secondary finish on pins 11 / 12"; "Footprints" row TR3.
7. Datasheets to fetch: ST **STF7N60M2**; PSA **FS55X105K631EHG** (1 µF 630 V X7R 2220: DC-bias curve, ripple
   current / self-heating, AC voltage limit) and **FM32X104K631EGG**; Ymin **KCXE5002W680MF** (voltage rating,
   ripple current); TDK **PC40** material and an EC42/15 (EC42) core datasheet; Susumu KRL2012 4 mΩ.

## 3. How to extract facts

```sh
kicad_next/review/tools/rv guard && kicad_next/review/tools/rv setup
kicad_next/review/tools/rv sch sheet 7
kicad_next/review/tools/rv sch ref TR3,Q7,Q19,Q8,Q21,C47,C54,C16,C55
kicad_next/review/tools/rv sch cmp51 7
kicad_next/review/tools/rv sch bom 7
kicad_next/review/tools/rv sch part C47,C19,TR3,Q7
kicad_next/review/tools/rv bq fp TR3,Q19,Q7,Q21,Q8,C47,C54,C16,C55,R83,C67,C70,C19,C30
kicad_next/review/tools/rv bq net DHB_HI_SOURCE DHB_CAP DHB_CURRENT
kicad_next/review/tools/rv bq net DHB_HI_SOURCE_SEC TRANS_SEC 420V
kicad_next/review/tools/rv bq neck DC+ F.Cu 12.75 -49.52 20.2 -17.2        # Q19 drain -> bulk capacitor C56 on F.Cu (known: 0.9 + 0.9 mm entry)
kicad_next/review/tools/rv bq neck DC+ F.Cu 12.75 -49.52 18.225 -48.0      # Q19 drain -> C67 pad 1
kicad_next/review/tools/rv bq neck DC+ B.Cu 18.225 -48.0 23.85 -70.9       # C70 pad 1 -> the vias at C47 (B.Cu run of stage 7b)
kicad_next/review/tools/rv bq neck DHB_HI_SOURCE F.Cu 12.75 -52.06 29.5 -56.8   # Q19 source -> TR3 pin 7
kicad_next/review/tools/rv bq neck DHB_HI_SOURCE F.Cu 12.75 -60.8 29.5 -56.8    # Q7 drain -> TR3 pin 7
kicad_next/review/tools/rv bq neck DHB_CAP F.Cu 22.88 -69.073 29.5 -71.8        # C47 pad 2 -> TR3 pin 4
kicad_next/review/tools/rv bq neck DHB_CURRENT F.Cu 12.75 -63.34 22.88 -61.072  # Q7 source -> C54 pad 2
kicad_next/review/tools/rv bq neck DHB_CURRENT F.Cu 12.75 -63.34 21.175 -48.0   # Q7 source -> C67 pad 2 on F.Cu alone
kicad_next/review/tools/rv bq neck 420V F.Cu 57.215 -41.949 76.1 -47.962        # Q21 drain -> C16 pad 1
kicad_next/review/tools/rv bq neck 420V F.Cu 57.215 -41.949 86.898 -61.983      # Q21 drain -> C19 +
kicad_next/review/tools/rv bq neck TRANS_SEC F.Cu 69.5 -51.8 76.1 -53.237       # TR3 pin 9 -> C16 pad 2
kicad_next/review/tools/rv bq neck ISO_GND F.Cu 66.335 -41.949 76.1 -61.237     # Q8 source -> C55 pad 2 on F.Cu alone
kicad_next/review/tools/rv bq near DHB_HI_SOURCE --within 1.3
kicad_next/review/tools/rv bq near DHB_HI_SOURCE_SEC --within 1.3
kicad_next/review/tools/rv bq near DC+ --within 1.25 --layer F.Cu
kicad_next/review/tools/rv bq padgap Q19.2 Q19.3
kicad_next/review/tools/rv bq padgap TR3.8 TR3.9        # primary row to secondary row
kicad_next/review/tools/rv bq near @SEC --within 11.1 --other-domain
kicad_next/review/tools/rv bq51 fp Q19,Q7,Q21,Q8,C47,C54,C16,C55,TR3,L3,C67,C70,R83
kicad_next/review/tools/rv bq51 neck DC+ F.Cu 45.615 -41.949 20.2 -17.2    # 5.1: Q19 drain -> the same bulk capacitor
python3 kicad_next/review/tools/drc_summary.py courtyards_overlap 8 -91 90 -38
kicad_next/review/tools/rv section kicad_next/README.md 'Stage 8'
kicad_next/review/tools/rv section simulation/dab/DAB_SIMULATION.md '^## 3'
```

`neck` works on one layer. Where a path changes layer (DC+ to C47: F.Cu pour → vias → B.Cu → vias → F.Cu bar), judge
each piece and count the vias (`rv bq net DC+` lists them; README rule: via 0.8 / 0.4 ≈ 1 A, 0.6 / 0.3 ≈ 0.7 A).
Copper current rule used by the project (README "Current and width", ΔT ≈ 20 K): 1 oz outer I ≈ 3.25 · w^0.725 A,
0.5 oz inner I ≈ 0.98 · w^0.725 A (w in mm).

## 4. Checklist

### A. Schematic and operating point

- **A1 Connectivity against the design intent.** `rv sch sheet 7` vs design document figure 5.x (p 24) and
  DAB_SIMULATION.md section 1: primary winding between DHB_HI_SOURCE (TR3 7 + 8) and `DHB_CAP` (4 + 5); secondary
  between DHB_HI_SOURCE_SEC (11 + 12) and `TRANS_SEC` (9 + 10); no part left in series (L3 gone, net TRANS_PRI
  gone: `rv sch net '*TRANS_PRI*'` must find nothing). PASS: as described; `rv sch cmp51 7` shows only the
  documented changes.
- **A2 Dots / winding sense.** CHANGES "Transformer pins and winding tables": both windings wound in the same
  direction, starts (dots) on 4 + 5 (`DHB_CAP`) and 9 + 10 (`TRANS_SEC`), finishes on the switch nodes. For a DAB
  the sign only shifts the phase reference by 180° (firmware), but it must match what the control expects
  from 5.1: in 5.1 which end of each winding was on the switch node (`rv sch51 ref TR3,L3`)? PASS: the phase
  relation "primary switch node high ↔ secondary switch node high = in phase at zero phase shift" is the same as
  in 5.1, or the difference is written down for the firmware. Also: the switch nodes are on the winding
  **finishes** (outer layers) – note the EMI / capacitive coupling consequence stated in the document, if any.
- **A3 Turns ratio and voltage.** 20 : 21 with 400 V in: matched secondary voltage 420 V (DAB_SIMULATION.md "DC+
  tracks V420 · 20 / 21" at light load). Design document used 26 : 29 for 410 V with an external inductor.
  PASS: the simulation shows 400 W at 400 → 420 V with phase shift ≈ 24° and rms currents ≈ 2.4 / 2.3 A (quote the
  table); state the voltage range of DC+ and 420V over which ZVS holds (2.2 – 2.4).
- **A4 Series inductance = leakage (CHANGES 2.4: "no jumper position").** Power P = V1 · V2' · φ(π − φ) / (2π² f L)
  for a half-bridge DAB with half the rail voltages applied: recompute P at φ = 24° with L = 41 µH (use the
  formula variant of DAB_SIMULATION.md) and the maximum power at φ = 90°. Leakage tolerance ± (10 … 30) %
  (DAB_TRANSFORMER.md 7). PASS: 400 W reachable with φ ≤ 45° at +30 % leakage, and the 3 A peak load of the design
  document (≈ 1.2 kW peak?) – state what peak power the 41 µH allows and compare with what 70 µH + 5.1 leakage
  allowed (5.1 was more limited, so PASS if ≥ 5.1). There is **no fallback pad for an external inductor**: if
  the first wound sample has much lower leakage (e.g. 25 µH), what happens (higher peak currents at the same
  power, lower φ) – note with the mitigation in DAB_TRANSFORMER.md 6.
- **A5 Split capacitors.** C47 / C54 and C16 / C55: 1 µF 630 V X7R at 200 / 210 V DC bias: effective capacitance from
  the DC-bias curve; ripple voltage on the mid point ΔV = I_pk / (2π f · 2C_eff) (the two halves act in parallel
  for AC); resonance of 2 C_eff with (Lleak) and with Lm – must be far below 140 kHz yet the start-up
  oscillation the design document mentions (p 25) must be damped; rms current per capacitor = half the winding
  current (1.2 A) against the part's ripple rating / self-heating (X7R at 140 kHz: ESR, ΔT). PASS: ΔV ≤ 10 % of
  the half-rail voltage, peak voltage ≤ 500 V, rms current within the manufacturer's limit or ΔT ≤ 20 K; same
  part family and value as 5.1 (`rv sch51 ref C47,C16`).
- **A6 Balancing resistors (CHANGES 2.8).** R143 + R144 across C47, R145 + R146 across C54, R150 + R149 across C16,
  R148 + R147 across C55; R147 pin 1 = ISO_GND, R150 pin 2 = 420V (the pairs follow the capacitor above them after
  C16 / C55 were swapped). `rv sch ref R143,R144,R145,R146,R147,R148,R149,R150`. PASS: each capacitor has exactly
  one 440 k chain across it; 100 – 105 V and ≤ 25 mW per resistor (200 V 1206 part C17956); the lower primary
  chain ends on DHB_CURRENT (through the shunt to GND – 0.45 mA through 4 mΩ, negligible) – confirm that this is
  intended and equal for both sides (secondary: ISO_GND directly); time constant 440 k × 1 µF = 0.44 s vs the
  firmware "enable ≥ 2 s after the split caps are centred".
- **A7 MOSFET stress.** STF7N60M2 (600 V; RDS(on), ID, Coss(er/tr), Qrr from the datasheet): rms current per switch
  ≈ I_winding / √2 ≈ 1.7 A → conduction loss at 100 °C; ZVS turn-on in the simulated range, hard-switching
  energies at light load (DAB_SIMULATION.md 2.3: 30 – 40 µJ edges → × 140 kHz = 4 – 6 W if it happened
  continuously – what do the recommendations say about avoiding it?). VDS: 400 / 420 V + overshoot ≤ 480 V =
  80 % of 600 V. PASS: loss per switch ≤ ≈ 4 W on the heatsink, VDS margin ≥ 20 %, same devices as 5.1.
- **A8 Output capacitors.** C19 / C30 68 µF (5.1: 39 µF): voltage rating of KCXE5002W680MF – the parts table note says
  450 V; decode the part number from the fetched datasheet (the "2W" code) – vs 420 V + ripple + overshoot at
  load dump (bidirectional converter: energy can also be returned to DC+). HF ripple current: the DAB secondary
  half bridge draws its current from C16 / C55 and the 6 × 100 nF; what flows in the electrolytics (≈ the 140 kHz
  ripple residue + audio-frequency load current up to 3 A peak)? PASS: rated voltage ≥ 450 V and ≥ 420 V × 1.05,
  ripple current within rating; more capacitance than 5.1 (control-loop note: plant changed, firmware gain).
- **A9 Bypass C67 / C70 and the shunt.** 100 nF 630 V from DC+ to **DHB_CURRENT** on both sides of the board at
  (19.7, −48.0): the HF loop Q19 – Q7 – C67 / C70 excludes the shunt R83. In 5.2 Q7's source (12.75, −63.34) is
  15 mm south of them: see C2. Schematic PASS if as 5.1.
- **A10 Light load, start-up, protection (firmware-facing).** Collect from DAB_SIMULATION.md 3 the conditions the
  hardware relies on: dead time 150 ns (not ≥ 250 ns), frequency soft start 420 → 140 kHz, enable ≥ 2 s after the
  capacitors are centred, DC+ tracking or burst below ≈ 150 W, DAB_DIS. PASS: each is recorded in one place a
  firmware writer will read (name the file and line); otherwise documentation finding.

### B. Transformer TR3 (new part)

- **B1 One specification.** The winding specification is DAB_TRANSFORMER.md section 5 (option B 20 : 21, litz
  135 × 0.071, two chambers). The parts table says "gap 0.35 mm" (`rv sch part TR3`), CHANGES row "2.1 gap" and
  the sheet note say Lm ≈ 200 µH, ≈ 0.66 – 0.68 mm centre-leg grind (or 0.335 mm spacer under all legs).
  PASS: every document gives the same turns, wire, pins, gap target and the rule "set by measuring Lm
  170 – 210 µH"; FAIL (documentation, should fix) for each place that still carries the old 300 µH / 0.34 – 0.35 mm
  figure without saying "spacer under all legs".
- **B2 Flux density and core loss.** B_pk = V · t / (N · Ae): half-bridge → ± 200 V across 20 turns for half a
  period at 140 kHz: B_pk = 200 V / (4 · f · N · Ae) with Ae of EC42/15 from the core datasheet. Core loss from
  PC40 curves at 100 °C × Ve; winding loss from DAB_TRANSFORMER.md 3. Compare with the "1 W core loss" design
  rule of the design document (p 25) and the 25 K rise measured on 5.1 (p 33). PASS: B_pk ≤ 150 mT, total loss
  ≤ ≈ 4 W, the document's own temperature estimate ≤ 60 K rise.
- **B3 Saturation at start-up / flux walk.** DC blocking is by the split capacitors on both sides, so no DC flux;
  at start-up (p 25: half-length first pulse) and with the magnetising inductance of 200 µH: peak magnetising
  current = 200 V · t_on / Lm at the lowest frequency used (140 kHz → 3.6 µs → 3.6 A?? – recompute: V = 200 V,
  T/2 = 3.57 µs, ΔI = V · T/2 / Lm = 3.57 A peak-to-peak, ± 1.8 A). Check this against the simulation's
  magnetising current (2.4) and the gap's saturation current (N · I · … ). PASS: I_sat ≥ 2 × the peak of
  (load + magnetising) current; the magnetising current is **much larger than in 5.1** (530 µH, 0.7 A peak, p 25)
  – confirm the added conduction loss is in the A7 / B2 numbers.
- **B4 Footprint against the real bobbin.** `rv bq fp TR3`: 2 × 8 pins, 5.0 mm pitch, rows 40 mm apart, pads only
  on pins 4, 5, 7, 8, 9, 10, 11, 12, drill 1.2 mm. README "Still to confirm with calipers": pin diameter, base
  46 × 40, core depth, seated height. Unused pins "cut" – but the bobbin's unused pins still exist physically:
  are there **holes** for them (no), so they must be removed before mounting: is that written in an assembly
  note? PASS if a measurement of the bought bobbin is recorded and the cut-pin instruction exists; otherwise
  CANNOT VERIFY + "measure before ordering" with the dimensions needed.
- **B5 Barrier under TR3.** README: PCB creepage row ↔ row 37.6 mm, a 12 mm keep-out band on all six layers at
  x 42.5 … 54.5; "the core counts as primary and sits over the pin rows: secondary pin wraps ↔ core is a
  transformer item (3 tape layers on the secondary core plate or a core cap)". `rv bq padgap TR3.8 TR3.9`,
  `rv bq near @SEC --within 11.1 --other-domain` (expect only slot-separated pairs elsewhere),
  `rv bq xsec GND In1.GND y -70 40 58` and `rv bq xsec ISO_GND In1.GND y -70 40 58` (no plane in the band).
  PASS: no copper of any net on any layer inside the band; primary copper ends ≥ 5.55 mm west and secondary
  copper ≥ 5.55 mm east of the band centre x 48.5 on every layer (≥ 11.1 mm between them); the core-to-secondary
  insulation requirement is in the transformer specification (DAB_TRANSFORMER.md 8).
- **B6 Copper under the transformer body.** Switch-node and `DHB_CAP` copper under the primary chamber, `TRANS_SEC`
  and the 31 mm 1.6 mm track of DHB_HI_SOURCE_SEC east of the band: what runs **under the core** (which is
  floating / "primary")? Clearance from board copper to the core bottom = bobbin stand-off (README: "core-plate
  height above the board at the secondary pins ≥ 4.0 mm clearance or tape"). PASS: the stand-off dimension is
  known and ≥ 4.0 mm to secondary copper, or tape is specified; else CANNOT VERIFY.

### C. Layout – primary bridge (compare with 5.1 everywhere)

- **C1 DC+ into Q19 drain (known weak point: 0.9 + 0.9 mm on F.Cu, 5.1 ≈ 2.3 mm).** Re-measure:
  `rv bq neck DC+ F.Cu 12.75 -49.52 20.2 -17.2`, `rv bq neck DC+ F.Cu 12.75 -49.52 18.225 -48.0`,
  `rv bq padgap Q19.2 Q19.3`, `rv bq51 neck DC+ F.Cu 45.615 -41.949 20.2 -17.2`. The drain pad is through-hole
  on F.Cu and B.Cu, inner rings removed; B.Cu at the pad is enclosed by the high-side driver group (README
  "Stage 8"). Current into the drain: Q19 conducts half of each period → ≈ 1.7 A rms, 1.2 A average at 400 W;
  HF content closes through C67 / C70 and C47. Length of the 0.9 mm entries ≈ 1 mm each. Calculate the
  dissipation and temperature rise of two 0.9 mm × ≈ 1.5 mm necks in 1 oz copper at 1.7 A rms (R = ρ L / (w t)),
  and the added loop inductance compared with 5.1's single 2.3 mm entry. PASS: neck current density ≤ the README
  rule with factor ≥ 1.5 (0.9 mm ≈ 3.0 A each by the rule), dissipation < 10 mW; record "narrower than 5.1 but
  within the rule" as a note, or FAIL with the smallest fix if not (README "Stage 8" names one: R22 to the west
  side to open B.Cu).
- **C2 Primary commutation loop.** Q19 drain (12.75, −49.52) → Q19 → switch node → Q7 → Q7 source (12.75, −63.34) →
  DHB_CURRENT pour → C67 / C70 pad 2 (21.2, −48.0) → pad 1 (18.2, −48.0) → DC+ → Q19 drain.
  `rv bq neck DHB_CURRENT F.Cu 12.75 -63.34 21.175 -48.0` (is there a continuous F.Cu path, or does the return
  use the In2 1.2 mm track of 22.7 mm that `rv bq net DHB_CURRENT` shows, or B.Cu?). Give the loop's path length
  and area and the layers used, and the same for 5.1 (`rv bq51 fp Q19,Q7,C67,C70`: FETs side by side at
  x 36.9 / 48.2, y −41.9). PASS: the HF loop does not run through an inner layer over more than a via
  (decision "no switch-node / DC+ on inner layers"; DHB_CURRENT on In2 is a power return on a signal layer –
  judge and report), loop inductance estimate ≤ 2 × 5.1's, VDS overshoot estimate L · di/dt with di/dt from the
  STF7N60M2 turn-off at 3 A within A7's margin.
- **C3 Switch node to TR3.** Zone `S4B`/`S3A_DHB_HI_SOURCE_F` F.Cu ≈ 121 mm² from the pin column to TR3 pins 7 / 8
  (17 mm). `rv bq neck DHB_HI_SOURCE F.Cu 12.75 -52.06 29.5 -56.8` and from Q7 pin 2. 2.4 A rms. PASS: ≥ 2 mm
  everywhere, ≥ 1.2 mm to other nets on F.Cu, and the area is not larger than needed (it radiates: compare
  with 5.1's switch-node copper `rv bq51 net DHB_HI_SOURCE`).
- **C4 Capacitor mid point and DC+ to C47.** `DHB_CAP`: C47 pad 2 / C54 pad 1 / TR3 pins 4 + 5 as one F.Cu area
  (≈ 57 mm²) – `rv bq neck DHB_CAP F.Cu 22.88 -69.073 29.5 -71.8`. DC+ to C47 pad 1: F.Cu pour → 3 vias at
  (17.7 / 18.7, −50.0), (18.3, −48.5) → B.Cu 2.0 – 2.5 mm to (23.85, −70.9) → three vias 0.8 / 0.4 at
  (22.95 / 23.85 / 24.75, −71.75) → F.Cu bar into pad 1 (README "Stage 7b" / 7c). Current 1.2 A rms.
  `rv bq neck DC+ B.Cu 18.225 -48.0 23.85 -70.9`. PASS: ≥ 2.0 mm on B.Cu, via groups ≥ 2 × the current by the
  via rule, 1.2 mm spacing kept (README: 1.25 mm to R146 pads / TR3 pads 4, 5), and the B.Cu DC+ run does not
  cross under the F.Cu switch-node zone without a GND plane between (it does cross y −57.5 … −52: In1 / In4
  planes there? `rv bq xsec GND In4.GND y -55 15 30`) – capacitive coupling DC+ ↔ switch node is harmless,
  note only.
- **C5 Low-side return.** Q7 source → R83 (15.9, −64.0) → GND: R83 pad 2 has three 0.6 / 0.3 vias on a 1.0 mm bar
  to the planes (README "Stage 7"). The full bridge current returns through the shunt: 2.4 A rms through
  3 vias (≈ 0.7 A each by the rule = 2.1 A). `rv bq net GND` vias near (15.4 … 18.6, −64.7). And Q7 source →
  C54 pad 2: `rv bq neck DHB_CURRENT F.Cu 12.75 -63.34 22.88 -61.072`. PASS: via capacity ≥ 1.5 × the rms
  current, or a finding with the smallest fix (add vias / widen the bar; note the UART-island limit at
  y −65.255 that the README cites).
- **C6 Spacing around the pin column.** `rv bq near DC+ --within 1.25 --layer F.Cu`, `rv bq near DHB_HI_SOURCE
  --within 1.3`: 400 V between DC+ pad and source pad of Q19 at 2.54 mm pitch = 0.635 mm pad gap (TO-220
  standard, pad-pair exempt); the In3 15V strip passes 0.5 mm from the drain / source barrels (inner-layer
  functional spacing 0.5 mm for 400 V – hole wall to plane). PASS: every non-pad-pair gap ≥ 1.2 mm outer /
  ≥ 0.5 mm inner; list the 0.5 mm inner-layer spots (drain barrel ↔ In1 GND plane, ↔ In3 15V, ↔ In4 GND) and
  state whether 0.5 mm FR-4 between a 400 V switching barrel and a plane is acceptable under the README's own
  basis ("Inside a domain: HV nets … inner 0.5 mm") and equal to or better than 5.1 (`rv bq51 near DHB_HI_SOURCE
  --within 0.8`).

### D. Layout – secondary bridge and output

- **D1 Secondary commutation loop.** Q21 drain (57.2, −41.9) ← 420V; Q8 source (66.3, −41.9) → ISO_GND; HF bypass:
  which capacitor closes Q21 – Q8 directly? C89 – C91 / C99 – C101 are at (72 … 78, −81 … −75), 35 – 40 mm away; C16 / C55
  (split) at (76, −51 / −59) close it through 420V → C16 → `TRANS_SEC` → C55 → ISO_GND (two 1 µF in series).
  `rv bq neck 420V F.Cu 57.215 -41.949 76.1 -47.962`, `rv bq neck ISO_GND F.Cu 66.335 -41.949 76.1 -61.237`
  (0 = not joined on F.Cu alone → the return uses the In1 / In4 ISO_GND planes). Compare with 5.1
  (`rv bq51 fp Q21,Q8,C16,C55,C89,C90`). PASS: loop path ≤ 1.5 × 5.1's, or a 100 nF 630 V within ≈ 15 mm of both
  Q21 drain and Q8 source; otherwise "should fix: move one of the six 100 nF next to the bridge" (smallest fix).
- **D2 Secondary switch node.** DHB_HI_SOURCE_SEC: Q21 pin 3 / Q8 pin 2 → 1.6 mm F.Cu track 31 mm → TR3 pins 11 / 12
  (2.3 A rms; README "good for 4.6 A"). README "Stage 3a.3": Q8 pin 2 joined how? `rv bq net DHB_HI_SOURCE_SEC`
  (F.Cu 1.6 mm 33 mm, 1.2 mm 7.5 mm, 0.75 mm 2.7 mm; B.Cu 1.0 mm 10.9 mm; one 1.0 / 0.5 via at (62.8, −49.2)).
  PASS: the power path Q8.2 ↔ Q21.3 ↔ TR3 is ≥ 1.0 mm everywhere and its single via (if in the power path) is
  good for 2.3 A rms (a 1.0 / 0.5 via ≈ 1.2 A by the README scale → FAIL if it carries the full current alone);
  no part of the node on an inner layer; ≥ 1.2 mm to other nets.
- **D3 `TRANS_SEC` and output rail.** `rv bq neck TRANS_SEC F.Cu 69.5 -51.8 76.1 -53.237`; 420V pour 427 mm² to the
  terminals; the 420V "detour round H5" that README "Stage 10" says is still there. PASS: ≥ 2 mm for 1.2 – 2.3 A.
- **D4 The six 100 nF 1210 on 420V (CHANGES 5.6, README "Stage 7").** Pitch 2.9 mm, courtyards overlap by design.
  `rv bq fp C89,C90,C91,C99,C100,C101`, `python3 kicad_next/review/tools/drc_summary.py courtyards_overlap 70 -86
  80 -72`. PASS: body gap ≥ 0.3 mm (1210 body 2.5 mm wide incl. tolerance 2.5 ± 0.2 → check the part's
  datasheet), pads of 420V and ISO_GND ≥ 1.2 mm apart between neighbours.
- **D5 Terminals.** P400V and GND (ISO_GND) blade terminals: `rv bq dist P400V fp:GND` (a bare refdes = all pads of that footprint) or pad positions
  (`rv bq fp P400V,GND`): creepage 420 V functional / user-accessible wiring; distance to the board edge and
  to H3 (87.0, −87.5) / the removed H5 area. PASS: ≥ 4 mm between the two terminals' copper.

### E. 5.1 → 5.2 changes touching this part (explicit)

- **E1** L3 removed – no pad, no net stub left (`rv bq fp L3` → not on the board; `rv sch net '*TRANS_PRI*'`).
- **E2** TR3 pins re-assigned 2026-11-21 (4 + 5 / 7 + 8 / 9 + 10 / 11 + 12): symbol, footprint pads, board nets and
  the winding table agree (`rv sch ref TR3`, `rv bq fp TR3`, CHANGES table). The parts-table / STEP model are not
  electrical. PASS: identical pin ↔ net in all four.
- **E3** C16 / C55 swapped and turned by the owner; balancing-resistor nets follow (A6). PASS: C16 pad 1 = 420V,
  pad 2 = `TRANS_SEC`; C55 pad 1 = `TRANS_SEC`, pad 2 = ISO_GND on the board.
- **E4** Q19 / Q7 moved 25 – 35 mm west into the heatsink line: everything in section C. Dead copper of the old
  positions removed: `rv bq near DC+ --within 0.3 --layer F.Cu` near (36 … 48, −42) shows nothing unexpected;
  `python3 kicad_next/review/tools/drc_summary.py` reports 0 dangling tracks (the type would be listed).
- **E5** 100 nF 630 V 1210 on DC+ / 420V; C19 / C30 68 µF with the 50 mm can: footprints
  `CP_Radial_D10.0mm_P5.00mm_H50mm`, polarity pad 1 = 420V (`rv bq fp C19,C30`).
- **E6** The Q19 / Q21 barrier-slot exception was removed (README "Former exception"): the `.kicad_dru` has no rule
  "Q19/Q21 across the barrier slot" (`grep -n "Q19" kicad_next/tube_psu_5_2.kicad_dru`), and the L-shaped slot at
  (50.8 … 68.6, −62.0 … −39.2) (`rv bq slots`: the polygon) – is it still needed, does it weaken the board
  between TR3 (heavy) and the Q21 / Q8 heatsink? Note for checklist 12.

### F. Bring-up notes for the findings

- **F1** What to measure on the first TR3 sample before soldering it in (DAB_TRANSFORMER.md 6): Lm, leakage from
  both sides, resonance with the split capacitors, hi-pot primary ↔ secondary ↔ core.
- **F2** First power: DC+ from a current-limited supply, secondary unloaded, frequency soft start, watch the
  split-capacitor mid points centre (≥ 2 s), DHB_I zero calibration; expected no-load magnetising current.

## 5. Out of scope / given

- Gate drivers, gate networks, bootstrap, dead time, DAB_DIS (checklist 02); DHB_I measurement chain (08); 420 V
  measurement (03); whole-board creepage basis (10); heatsink mechanics and Q21 / Q8 insulation to their heatsink
  (12); sourcing of STF7N60M2 and the transformer parts (13).
- Given: EC42/15 two-chamber 20 : 21 with leakage as series inductance and no L3 position; Lm ≈ 200 µH set by
  measurement; balancing resistors; single primary heatsink line; DC+ and power GND on outer layers only (In1 /
  In4 GND planes stay); no silkscreen; via-in-pad accepted (R83 pad 1, C89 pad 1, the shared via of C67 / C70 pad 1).

## 6. Findings format

Write `kicad_next/review/findings/07_dab_power_stage.md` exactly in the format of `kicad_next/review/README.md`
"Common findings format": summary; one table row per item above (A1 … F2) with **PASS / FAIL / CANNOT VERIFY** and
the evidence (file:line, command + output lines, calculation with inputs, or datasheet document / page / URL);
ranked findings with severity (**blocker for ordering / should fix / note**), what is wrong, evidence, smallest fix,
confidence; "Compared with 5.1"; "Could not verify"; "Outside scope". "Looks fine" without evidence is not
acceptable.
