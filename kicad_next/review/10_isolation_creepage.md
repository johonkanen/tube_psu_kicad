# Review checklist 10 – isolation domains, creepage and clearance of the whole board

You are reviewing **one aspect** of the tube_power 5.2 power-supply board, alone, from this file and the repository
`/home/jari/dev/tube_psu_kicad`. You are doing a design review, not a redesign.

**Rules (full text: `kicad_next/review/README.md`, "Common rules" – read that section first):**
read-only on the repository, the only file you write is `kicad_next/review/findings/10_isolation_creepage.md`; no
commit, no push; never touch `kicad_next/tube_psu_5_2.kicad_pcb` / `.kicad_pro` and never run a script that saves or
regenerates design files (`route_s*.py`, `update_board_parts.py`, `setup_project.py` / `make_board.py` / generators
without `--check`); stop if a KiCad lock file exists (`rv guard`); RAM under 3 GB – **no full-board creepage DRC**;
`tools/next/check_next.sh` (2.3 GB) only if `reports/next/drc.json` is stale **and** no other KiCad job runs
(`pgrep -af "kicad-cli|kipy|check_next"`); never `pkill -f`; never run the KiCad AppImage with `--version`; the
owner's name / e-mail stay out of web requests. **Acceptance bar: match the bench-verified 5.1 board and add
creepage – do not optimise beyond that.** Standard / datasheet facts come from documents you fetch now, not from
memory; where the standard itself cannot be fetched (IEC texts are not free) say so and cite the secondary source.

## 1. Scope

"More creepage" is the one thing 5.2 must add to 5.1. The board has five isolation domains, found from the
schematic by `tools/next/setup_project.py` and encoded as net classes:

| Domain | Net classes | Ground | What |
|---|---|---|---|
| Primary (mains-referenced) | SIGNAL, PRIMARY_LV, HV_PRIMARY | GND = bridge negative, follows the mains | PFC, DC link, DAB primary, heater LLC primary, flyback primary, **all control logic and J2** |
| DAB secondary | SECONDARY_LV, HV_SECONDARY | ISO_GND (tied to the earthed amplifier chassis) | 420V, −100 V bias, isolated ± 15 V / 5 V, AD2 |
| Heater | HEATER | HT_GND (earthed or at the bias) | 6V3 output, SR, AD1 |
| UART island | UART_ISO | ISO_UART_GND (far-end ground) | J4, U11 side 2 |
| Protective earth | PE_EARTH (net PE) + the seven mounting holes H1 – H4, H6 – H8 (no net; screws bonded to the chassis) | – | Y capacitors, chassis |

Barrier parts (the only parts with pins in two domains): TR1, TR2, TR3, ISO1, ISO2, U11, and the Y capacitors to PE.
Required distances (README "Isolation domains and creepage / clearance (D6)", rules in
`kicad_next/tube_psu_5_2.kicad_dru`):

| Pair | Grade | Clearance (outer) | Creepage (outer) | Inner layers and layer to layer (plan view) |
|---|---|---|---|---|
| Primary ↔ DAB secondary | reinforced, 552 Vrms / 778 Vpk | 4.0 mm | 11.1 mm | 11.1 mm, no slot credit |
| Primary ↔ heater | reinforced, ≤ 333 Vrms | 4.0 | 8.0 | 8.0 |
| Primary ↔ UART | reinforced | 4.0 | 8.0 | 8.0 |
| DAB secondary ↔ UART | reinforced | 3.0 | 8.4 | 8.4 |
| DAB secondary (HV) ↔ heater | functional | 1.5 | 5.2 | 5.2 |
| DAB secondary (LV) ↔ heater | functional | 1.0 | 1.5 | – |
| Heater ↔ UART | functional | 1.0 | – | 1.0 |
| PE / mounting holes ↔ primary | basic | 2.0 | 3.2 | 3.2 |
| PE / mounting holes ↔ DAB secondary | basic | 1.5 | 4.2 | 4.2 |
| Inside a domain, HV nets | functional ≤ 500 V | 1.2 (tracks / zones; pad pairs exempt) | – | 0.5 |

Slots (Edge.Cuts, milled) give creepage credit on the outer layers only: under ISO2 (1.0 × 19.5 mm at
x 66.3 … 67.3, y −36.4 … −16.9), under TR1 (1.2 × 28 mm at x 62.9 … 64.1, y −14.3 … 13.7), under U11 (1.0 × 14.5 mm at
x −0.5 … 0.5, y −85.3 … −70.8), the T-shaped heater slot at ISO1 (bar y −64.1 … −63.1 from x −45.5 to −31.0, stem
x −42.9 … −41.9 down to y −47.6), and an L-shaped polygon cut-out between TR3 and the secondary bridge (box
x 50.8 … 68.6, y −62.0 … −39.2). TR3 has no slot: a 12 mm keep-out band on all six layers (x 42.5 … 54.5). The stackup
(JLC06161H-7628D) has 0.2 mm cores and 0.2 – 0.43 mm prepregs, none of which is relied on as insulation between
domains: **copper of two domains must never overlap on any pair of layers**.

Your job: check that the basis is sound, that the rules implement it, that the project's checker really covers
every pair, and – independently of that checker – that the board meets the numbers, including the cases no rule
covers.

## 2. Read first

1. `kicad_next/README.md` section "Isolation domains and creepage / clearance (D6)" completely
   (`rv section kicad_next/README.md 'Isolation domains and creepage'` – basis, working voltages, the "Former
   exception", "Alternative if ISO_GND may float", "Uncertain / to verify", "Consequences").
2. `kicad_next/tube_psu_5_2.kicad_dru` (≈ 215 lines, every rule with its comment).
3. `tools/next/check_domains.py` header (lines 1 – 70: what it checks, `LIMITS`, `ALLOW`) and
   `tools/next/setup_project.py` (`BARRIERS`, `HV_NETS`, the flood fill).
4. `kicad_next/README.md`: "Inner layers (routing stage 2)" → "Barrier gaps", "Layer to layer", "Decisions";
   "Footprints and 3D models" rows ISO1 / U11, ISO2, TR1, TR3, TR2, heatsink; "Stackup"; "Stage 4k" (Q19 / Q21 slot
   exception dropped); "Stage 7" (ISO2 pad 8); "Stage 10" (H5 removed); "Stage 11" (J4 island).
5. `NEXT_REVISION_PLAN.md` phase 1 decision D6 and "Consequences of D6"; `NEXT_REVISION.md` row 5.5 (heatsink
   carries primary and secondary devices).
6. `simulation/flyback/EEL19_DESIGN.md` 12.5, 12.6; `simulation/dab/DAB_TRANSFORMER.md` 8 (transformer-internal
   insulation – for cross-reference only).
7. External: TI **SLUP421** (the README's source for the IEC 62368-1 / 60664-1 tables), datasheets of
   **CA-IS3761LW**, **CA-IS3721HW**, **UCC21520** (package creepage, CTI / material group), JLCPCB capabilities
   page (minimum slot width, milling tolerance), a laminate datasheet for the CTI of the JLC FR-4 (README names
   Nan Ya NP-155F).

## 3. How to extract facts

```sh
kicad_next/review/tools/rv guard && kicad_next/review/tools/rv setup
python3 kicad_next/review/tools/drc_summary.py          # is reports/next/drc.json newer than the board? counts
python3 tools/next/check_domains.py kicad_next/tube_psu_5_2.kicad_pcb    # the project's domain-distance check (read-only, ~10 s, a few hundred MB, no other kipy job at the same time)
python3 tools/next/check_domains.py kicad_next/tube_psu_5_2.kicad_pcb --json /tmp/check_domains_10.json   # violations / accepted pairs as JSON (it lists only pairs BELOW a limit - margins of passing pairs come from rv bq)
python3 tools/next/setup_project.py --list | head -40   # every net with its domain and class (prints only)
python3 tools/next/setup_project.py --check             # every net in exactly one domain; project file up to date
kicad_next/review/tools/rv bq classes
kicad_next/review/tools/rv bq slots                     # Edge.Cuts items inside the outline
kicad_next/review/tools/rv bq dist @PRI @SEC            # smallest straight distance per layer, with the two points
kicad_next/review/tools/rv bq dist @PRI @HEATER
kicad_next/review/tools/rv bq dist @PRI @UART
kicad_next/review/tools/rv bq dist @SEC @UART
kicad_next/review/tools/rv bq dist @SEC @HEATER
kicad_next/review/tools/rv bq dist @HEATER @UART
kicad_next/review/tools/rv bq dist @PE @PRI
kicad_next/review/tools/rv bq dist @PE @SEC
kicad_next/review/tools/rv bq dist @PE @HEATER
kicad_next/review/tools/rv bq near @SEC --within 11.1 --other-domain | head -60
kicad_next/review/tools/rv bq near @HEATER --within 8.0 --other-domain
kicad_next/review/tools/rv bq near @UART --within 8.4 --other-domain
for h in H1 H2 H3 H4 H6 H7 H8; do kicad_next/review/tools/rv bq near $h --within 4.3 | head -6; done   # mounting holes against everything
kicad_next/review/tools/rv bq fp H1,H2,H3,H4,H6,H7,H8
kicad_next/review/tools/rv bq fp TR1,TR2,TR3,ISO1,ISO2,U11
kicad_next/review/tools/rv bq padgap ISO2.8 ISO2.9
kicad_next/review/tools/rv bq padgap TR1.2 TR1.9
kicad_next/review/tools/rv bq padgap TR2.1 TR2.10
kicad_next/review/tools/rv bq padgap TR3.8 TR3.9
kicad_next/review/tools/rv bq near @HV_PRIMARY --within 0.49 --layer In1 | head -20     # HV nets against planes on inner layers (0.5 mm rule)
kicad_next/review/tools/rv bq near @HV_SECONDARY --within 0.49 --layer In1 | head -20
grep -n "(rule " kicad_next/tube_psu_5_2.kicad_dru
```

How the helpers relate to the rules: `dist` / `near` give the **straight** distance per layer between copper
(pads with their true shapes, tracks, vias, stored zone fill; plated holes without inner ring count with the drill
diameter). They do not follow slots and do not compare different layers. So: (a) on **inner layers** the straight
distance is the whole story – compare directly with the last column of the table; (b) on **outer layers** a
straight distance ≥ creepage passes outright, a distance between clearance and creepage needs a slot on the line
and a manual path round the slot end (coordinates from `rv bq slots`), below clearance is a violation;
(c) **layer to layer** you must compute yourself for a sample (see item C3) or trust `check_domains.py` after
reading its second pass. To write your own geometry test, load the dump the helpers use
(`kicad_next/review/tools/rv dir` → `b52.json`; format in `board_dump.py`; `bq.py` shows how to build shapely
geometry per net and layer).

## 4. Checklist

### A. Basis (numbers, assumptions)

- **A1 Working voltages.** README derives 552 Vrms / 778 Vpk primary ↔ secondary from GND(t) = min(0, v_mains) with
  253 Vrms mains and the 420V rail on earthed ISO_GND. Redo the calculation (rms of 420 + 358·|sin| over the
  negative half wave and 420 over the positive one; peak 420 + 358). Also check the pairs not on the 420V rail:
  DC+ (GND + 400 V) against **−100 V bias** (ISO_GND − 100 V): peak = 400 + 0 + 100 … in which half wave?
  PASS: 552 Vrms / 778 Vpk is the worst pair or the worst pair is stated; primary ↔ heater 318 – 333 Vrms confirmed.
- **A2 Creepage table values.** Fetch TI SLUP421 (or another citable reproduction of IEC 60664-1 Table F.4 / F.5 and
  IEC 62368-1 Table 17) and check the anchor rows the README uses for PD2, material group III: 250 V 2.5 mm,
  320 V 3.2, 400 V 4.0, 500 V 5.0, 630 V 6.3, 800 V 8.0 mm; interpolation 552 V → 5.52 mm; reinforced = × 2 →
  11.04 → 11.1 mm. PASS: rows confirmed from a fetched source (cite page); the README itself flags
  "check against the standard" – say what remains unconfirmed.
- **A3 Material group.** Group III(a / b) assumes CTI ≥ 100 / 175. Find the CTI of the laminate JLC uses for this
  stackup (laminate datasheet). PASS: CTI ≥ 175 documented, or the numbers still hold for IIIb (same column at
  PD2 per README – confirm).
- **A4 Clearance.** OVC II, 230 V mains → 2.5 kV impulse; reinforced → next step 4 kV → 3.0 mm (IEC 60664-1 Table
  F.2, inhomogeneous field, PD2) and IEC 62368-1's larger figure → 4.0 mm used. PASS: 4.0 mm ≥ the requirement
  of both standards as quoted in the fetched source for ≤ 2000 m altitude.
- **A5 Frequency.** The DAB switch nodes put a 140 kHz, ≤ 420 V square wave across the primary ↔ secondary barrier
  (TR3, and capacitively everywhere). IEC 60664-4 / IEC 62368-1 require larger clearances / creepage above
  30 kHz for the HF part. The README says "not assessed". Assess it roughly from a fetched source (e.g.
  creepage for 420 Vpk at 140 kHz ≈ a few mm; clearance ≈ < 1 mm) and state whether 11.1 / 4.0 mm cover it.
  PASS / CANNOT VERIFY with the source named.
- **A6 Pollution degree and coating.** PD2 without conformal coating; the board has **no silkscreen** (irrelevant)
  and solder mask (no credit taken). PASS: no rule takes credit for mask or coating.
- **A7 The assumption "ISO_GND always earthed".** Given (owner confirmed) – only check it is written where the
  amplifier builder will read it (README yes; a note for the fab / assembly package or the schematic sheet?).
  Documentation note, not FAIL.

### B. Rules implement the basis

- **B1 Rule file against the table of section 1.** Read every `(rule …)` of `tube_psu_5_2.kicad_dru`: layers,
  condition (class pairs), constraint values. PASS: each row of the table has a clearance rule, a creepage rule
  (outer) and an inner-layer rule with the stated values; no rule is weaker than the README; **list every pair of
  domains that has no rule at all** – expected gaps to examine: PE ↔ heater, PE ↔ UART, mounting holes ↔ heater,
  mounting holes ↔ UART (the hole rules name only primary and secondary classes), DAB secondary (LV) ↔ heater
  on inner layers. For each gap decide from the working voltage what the distance should be (heater and UART
  grounds are earthed or near earth → functional, ≥ 1 mm; but mounting holes are also where a metal screw head
  / washer larger than the copper ring sits: see D4).
- **B2 Same numbers in three places.** `.kicad_dru`, `LIMITS` in `check_domains.py`, and the tests in
  `tools/next/check_rules.py`. PASS: identical values for every pair; `ALLOW = []`.
- **B3 Exemptions inside the rules.** "HV functional, outer layers" exempts pad-to-pad pairs and
  `unconnected-*` pads; the three "High-side driver group" rules allow 0.2 mm inside a floating gate-driver
  group; "Same-footprint pad gap, low-voltage classes"; "PRIMARY_LV inner layers 0.15 mm". PASS: none of these
  can apply to a pair of two different isolation domains (read the conditions: they must be restricted to
  classes of one domain) – in particular the pad-to-pad exemption of the HV rule must not weaken a
  domain-to-domain rule (KiCad takes the largest matching clearance? or the first match by priority? – check
  the KiCad 10 documentation on custom-rule precedence and say which it is, because the answer decides
  whether a low-value rule later in the file can override a barrier rule).
- **B4 Net classification.** `python3 tools/next/setup_project.py --check` passes; `--list`: every net has exactly
  one domain. Spot-check 15 nets by hand from the netlist (`rv sch net NAME`): e.g. `Net-(D8-K)` (TR1 bias
  winding → HV_SECONDARY), `Net-(TR1-A15)` (primary aux → SIGNAL), EPWM5A_ISO (HEATER), DAB_DIS_SEC
  (SECONDARY_LV), `Net-(U11-B1)` (UART_ISO), HEATER_CURRENT (SIGNAL = primary), the unconnected pads of U11
  side 2 (UART_ISO) and of DRV6 (SECONDARY_LV). **HV classification:** which nets are HV_PRIMARY / HV_SECONDARY
  (`rv bq classes`) – is any net that carries > 60 V missing (candidates: `Net-(C12-Pad2)` and `Net-(D7-K)`
  (flyback clamp, DC+ + 100 V), `Net-(D8-K)`, the divider mid nodes, `Net-(DRV3-VDDA)`, `Net-(R23-Pad2)` …,
  `Net-(Q21-G)` (rides on the 420 V switch node), **`Net-(Q8-G)` / DHB_LOW_GATE_SEC (low side, LV – fine)**,
  GATE1 / GATE2 (LV), "-100V BIAS" (HV_SECONDARY))? PASS: every net above ≈ 60 V against its domain ground is
  in an HV class; list any that is not.
- **B5 Barrier parts.** Only TR1, TR2, TR3, ISO1, ISO2, U11 (+ Y capacitors C65, C81, C82, C84, C85 to PE) have pins
  in two domains: confirm from the netlist with a small script or by `rv sch ref` on each UCC21520 (DRV3, DRV5,
  DRV6: both sides in one domain). PASS.

### C. The project's checker and the reports

- **C1 `check_domains.py` passes now.** Run it. Expected: "no pair of two isolation domains below its limit",
  0 accepted pairs. PASS: exit status 0 on the current board (and note the counts it prints: copper items,
  slots = 5, pairs closer than their largest limit).
- **C2 What the checker does not see.** From its source: (a) it uses stored zone fills – are they current?
  (`drc_summary.py`: the DRC report is newer than the board and `check_board.py` refills only a copy; compare
  one zone outline against its fill if in doubt); (b) holes: non-plated holes and the mounting holes H1 – H8 as
  PE – H5 is gone: does the script still expect eight? (c) slots: "5 slots" – the board has the ISO2, TR1, U11
  slots, the heater T slot and the L-shaped polygon: is each recognised (non-convex T and polygon outline)?
  (d) Edge of the board: creepage round the **board edge** between two domains near an edge (e.g. UART island
  at the top edge, TR1 slot reaching y 13.7 with the edge at y 18.75, TR3 band at the top edge) – over the edge
  and along the other side is a creepage path too; clearance through air round the edge. (e) Component bodies
  and leads above the board (a clearance question the 2-D check cannot answer): list the places where a
  primary part's body or lead comes within 4 mm (in 3-D) of secondary copper or parts – candidates: TR3 core
  (primary) over the secondary pin row, the secondary heatsink of Q21 / Q8 next to the primary Q19 … no, Q19
  moved; C19 / C30 cans; D4 / D5; ISO2 area. PASS: each of (a) – (e) answered with evidence.
- **C3 Independent sample of the layer-to-layer rule.** Write a short script on `b52.json` (shapely): for the domain
  pair PRI / SEC build the union of all copper of PRI on all six layers and of SEC on all six layers and compute
  the plan-view distance; the same for PRI / HEATER and PRI / UART. Expected ≥ 11.1 / 8.0 / 8.0 mm **except** at
  the outer-layer pad rows of the barrier parts (slot credit) – list every location below the limit and
  explain it. PASS: only barrier-part pad rows (and tracks leaving them on the outer layers with a slot
  between) appear, and none of them involves an inner layer.
- **C4 Inner layers directly.** `rv bq dist @PRI @SEC` etc.: on In1 … In4 expect ≥ 11.1 mm (PRI / SEC; note 11.114 mm
  DC+ fly-lead barrel ↔ TR1 pin 5 barrel and 11.6 mm plane to plane), ≥ 8.0 mm (PRI / HEATER, PRI / UART: 8.05 mm),
  ≥ 8.4 (SEC / UART), ≥ 5.2 (SEC-HV / HEATER), PE ≥ 3.2 / 4.2. PASS: all met; margins below 0.1 mm listed with
  coordinates (manufacturing tolerance of inner-layer registration ≈ ± 0.1 mm is not accounted for – note).
- **C5 Outer layers directly.** For each pair take the `dist` result per outer layer: where it is below the
  creepage value, identify the slot and compute the path round it. Minimum set: ISO2 pad rows (7.25 mm straight;
  12.50 mm documented), ISO1 (7.25 → 8.85), U11 (7.25 → 8.85), TR1 pin 2 ↔ pin 9 (11.02 mm straight; 12.86 mm
  documented), DC+ / FLY_C copper ↔ ISO_GND at TR1 (`rv bq dist FLY_C @SEC --layer F.Cu`: 9.44 mm straight),
  GND ↔ `Net-(TR1-S15)` at ISO2 pad 8 (10.41 mm straight; README estimates 11.8 mm, "not re-measured"),
  heater ↔ GND at the T slot (`rv bq near @HEATER --within 8.0 --other-domain`: 5.36 mm straight at
  (−36.5, −64.9) / (−36.8, −59.6)). PASS: every such path ≥ its creepage **and** ≥ clearance in a straight line
  through the slot (air) – 4.0 mm; give the table.
- **C6 Slots are real.** `rv bq slots` vs the Gerber / drill output if it exists (`kicad_next/fab/`): each slot is
  a closed Edge.Cuts shape ≥ 1.0 mm wide (IEC: a groove < 1 mm is ignored at PD2), JLC's minimum routed slot
  width and corner radius respected, copper-to-slot-edge ≥ 0.3 mm (`near` of the nets beside each slot),
  remaining FR-4 web between slot ends and other holes / the board edge ≥ 2 mm. PASS: all five; flag the slot
  nearest to an edge.

### D. Cases outside the automated check

- **D1 Heatsinks.** One primary heatsink line at x 5 … 13 (Q5, Q6, SICD1, SICD2, DB1, Q7, Q19; README "Stage 4a";
  footprint helper `Heatsink_Plate_Keepout_L120mm` with 4.0 / 11.1 mm keep-off lines) and a separate secondary
  heatsink for Q21 / Q8 at (52 … 74, −43.5 … −38.5). Questions: is the primary heatsink earthed (PE) or floating /
  primary (NEXT_REVISION 5.5 treats the plate as "primary / earthed")? Tab potentials: Q5 / Q6 drain (switch node),
  SICD cathode (DC+), Q7 drain (switch node), Q19 drain (DC+) – TO-220 **FullPAK** (STF = isolated tab) for the
  DAB FETs, bare tabs for TO-247 / TO-220-2 → insulating pads. Secondary heatsink: Q21 drain = 420V, Q8 drain =
  switch node, FullPAK. Distances in plan view: secondary heatsink body ↔ primary copper / parts (the L-shaped
  cut-out and Q21 at x 52 – 62); primary heatsink ↔ H4 (earthed screw at (5.8, −40.1) in the middle of the line)
  ↔ UART island. PASS: a written statement of each heatsink's potential and insulation exists and the
  board-level distances heatsink ↔ other-domain copper meet the table (11.1 / 4.0 mm for a primary plate to
  secondary copper); otherwise CANNOT VERIFY + what the owner must define (ties to checklist 12).
- **D2 Mounting holes.** Seven holes with a 3.5 mm copper ring on every layer, no net, screws earthed.
  `for h in …; rv bq near $h --within 4.3`. PASS: ≥ 3.2 mm creepage / 2.0 mm clearance to primary and ≥ 4.2 / 1.5 mm
  to secondary copper on all layers (H4 ↔ DC+ on F.Cu ≈ 3.23 mm; ↔ PRI_DHB_HI on In3 ≈ 3.18 mm – **below 3.2?**
  check which limit applies on inner layers: `hole_clearance 3.2` is measured from the hole, the ring is
  copper without net: recompute from the hole edge and from the ring edge and report both).
  **Screw head / washer / standoff**: an M3 screw head is 5.5 – 6 mm, a washer 7 mm, a hex standoff 5 – 6 mm across:
  larger than the 3.5 mm ring. Distance from a 7 mm circle at each hole to the nearest copper **and component
  body** on the mounting side(s) (`rv bq area` around each hole). PASS: ≥ 2.0 mm clearance (primary) / 1.5 mm
  (secondary) from a 7 mm circle; list holes that fail with a 6 mm and with a 7 mm head.
- **D3 Mounting holes ↔ heater and UART (no rule).** H1 (−67.0, −87.5) is inside / beside the heater island, H2
  (6.9, −87.5) beside the UART island (≈ 1.75 mm from island copper on F.Cu: `rv bq dist H2 @UART`), H6 / H7 near
  the mains input. Decide the required distance (B1) and check. PASS / finding.
- **D4 PE net.** `rv bq dist @PE @PRI`, `@SEC`, `@HEATER`. Y capacitors C65, C81, C82, C84, C85: their own pad pair
  spacing is the part's (7.5 mm pitch). PASS: PE tracks ≥ 3.2 mm (creepage) from primary copper on every layer,
  including under the discharge resistors R4 – R6 (README stage 3a open point 1 forbade crossing under them).
- **D5 Terminals and user-accessible parts.** Blade terminals (6.3 mm tabs) IN1 / IN2 / PE, HT_6V3 / HT_GND, P400V /
  GND, P15V_OUT / N15V_OUT / P5V_OUT / N80V_OUT / SEC_GND; J4. Mating receptacles are wider than the pads
  (insulated or not): distance between neighbouring terminals of different domains / hazardous voltages in
  3-D: IN1 ↔ PE, IN2 ↔ PE, P400V ↔ GND (3.3 mm pad to pad), N80V_OUT ↔ P5V_OUT, HT terminals ↔ H1.
  `rv bq fp IN1,IN2,PE,P400V,GND,N80V_OUT,P5V_OUT` and `rv bq dist fp:IN1 fp:PE` etc. PASS: ≥ the table's
  clearance between terminals of different domains, with the receptacle width considered (state the
  receptacle width assumed, e.g. 7.9 mm for an uninsulated 6.3 mm receptacle).
- **D6 Inside the primary: 0.5 mm inner-layer functional spacing at 400 V.** `rv bq near @HV_PRIMARY --within 0.49
  --layer In1` (and In2, In3, In4) must be empty; at exactly 0.50 mm there are many pairs (plated barrels of
  400 V nets ↔ GND / 15V planes). Basis check: for functional insulation inside a circuit IEC 62368-1 allows
  smaller distances if a short-circuit of the insulation is not hazardous (fault test) – the README uses 0.5 mm
  for ≤ 500 V on inner layers (no pollution, PD1 inside the laminate). Compare with IEC 60664-1 Table F.4 for
  PD1 / printed wiring material (500 V: ≈ 0.5 – 1.3 mm depending on the column – look it up) and with what 5.1
  had (`rv bq51 near DC+ --within 0.49` on its inner layers). PASS: ≥ 0.5 mm everywhere, basis cited, not worse
  than 5.1; note registration tolerance.
- **D7 Outer-layer 1.2 mm HV rule and its exemptions.** Sample: `rv bq near DC+ --within 1.19 --layer F.Cu`,
  `--layer B.Cu`; `rv bq near DHB_HI_SOURCE --within 1.19`; `rv bq near 420V --within 1.19`. Everything listed
  must be a pad-to-pad pair, an `unconnected-*` pad, or inside one high-side group. PASS: list each sub-1.2 mm
  pair with its exemption; TO-220 pad gaps 0.635 mm at 400 V between drain and source pads of Q19 / Q21 are the
  part's own pitch (as 5.1).
- **D8 Solder side of through-hole barrier parts.** After soldering, the pins of TR1 / TR2 / TR3 / ISO-less parts
  protrude 1 – 2 mm on B.Cu with solder fillets wider than the pad: clearance pin tip ↔ chassis / standoffs under
  the board, and between the fly-lead joints (TR1 pads 11 / 12) and pin 5. Note what board-to-chassis spacing
  is assumed (standoff height) – CANNOT VERIFY without mechanical data; say what is needed.

### E. Compared with 5.1 (the purpose of the revision)

- **E1** For each barrier give the 5.1 value and the 5.2 value: primary ↔ secondary smallest distance per layer
  (`rv bq51` has no net classes – use explicit nets: `rv bq51 dist GND ISO_GND`, `rv bq51 dist DC+ ISO_GND`,
  `rv bq51 dist DC+ 420V`, `rv bq51 dist GND HT_GND`, `rv bq51 dist DC+ 6V3`), the known 5.1 weak spot "5.08 mm
  DC+ to ISO_GND" (NEXT_REVISION 1.4), isolators without slots, J4 not isolated. PASS: 5.2 ≥ 5.1 everywhere and
  ≥ the table; list the improvement per barrier in one table.

### F. Summary deliverable

- **F1** One table in the findings: barrier, required clearance / creepage / inner, smallest value found on the
  board per layer group (outer straight, outer round slot, inner, layer to layer), location (x, y), margin.
- **F2** A list "not covered by any automatic check" with what was done by hand and what remains for the owner
  (heatsink definition, screw heads, receptacles, transformer internals, isolator certificates – the latter two
  are checklists 01 / 03 / 04 / 07).

## 5. Out of scope / given

- Transformer-internal insulation (wire, tape, margins) and the isolator / driver certificates (checklists 01, 03,
  04, 06, 07 look at them per part); thermal / mechanical design of the heatsinks (12).
- Given: the numbers of the README table (11.1 / 8.0 / 8.4 / 5.2 / 3.2 / 4.2 mm, 4.0 mm clearance) **as targets** –
  you check their derivation (A) but a different opinion on the standard is a note unless a number is too
  small; ISO_GND earthed; no silkscreen; DC+ on outer layers only; H5 removed; stackup 7628D; via-in-pad.

## 6. Findings format

Write `kicad_next/review/findings/10_isolation_creepage.md` exactly in the format of
`kicad_next/review/README.md` "Common findings format": summary; one table row per item above (A1 … F2) with
**PASS / FAIL / CANNOT VERIFY** and the evidence (file:line, command + output lines, calculation with inputs, or
document / page / URL); ranked findings with severity (**blocker for ordering / should fix / note**), what is
wrong, evidence, smallest fix, confidence; "Compared with 5.1"; "Could not verify"; "Outside scope".
"Looks fine" without evidence is not acceptable.
