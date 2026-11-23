# Findings: 10 isolation_creepage  (reviewer: Claude Opus 5.5, 2026-11-23, commit 01a1adf)

Board, `.kicad_dru` and `check_domains.py` are unchanged since `ecf0024` (`git log ecf0024..HEAD` on those
files is empty). `reports/next/drc.json` is newer than the board (`drc_summary.py`: 133 courtyard overlaps,
2 pth_inside_courtyard, 2 starved_thermal, 0 unconnected, 0 parity). No KiCad DRC was started for this review.
Scratch scripts (independent shapely checks on `/tmp/tube_psu_review_1000/b52.json`) are in the session
scratchpad: `c3.py` (plan view / layer to layer + own slot-path solver), `c5.py` (slot paths), `c6.py` (slots),
`d2.py` (screw heads), `d7.py` (1.2 mm exemptions), `h82.py` (8.2 mm re-check).

## Summary
On the copper the 5.2 board meets every number it set itself. Both checks agree on that: the project checker
(`check_domains.py` exit 0, 5 slots, 0 accepted pairs) and an independent re-implementation (own item build, own
visibility-graph path round the slots, every pair of domains on every pair of layers). It is much better than
5.1 at every barrier (the 5.08 mm DC+ ↔ ISO_GND weak spot is gone, inner layers ≥ 11.1 / 8.0 mm, the UART
island and the isolators have slots, mounting-hole keep-off went from 0.8 mm to 3.2 mm).
None of this blocks the order. Three things should be fixed before ordering, all small:
(1) the mounting-hole keep-off is measured from the 3.5 mm copper ring, and any metal M3 head, washer or
standoff is larger than that, so the earthed screws break basic insulation to primary copper at H4 / H6 / H7
(1.5 to 2.2 mm instead of 3.2 mm);
(2) three of the creepage slots are exactly 1.0 mm wide, but JLC mills non-plated slots to ±0.2 mm and
IEC 60664-1 ignores a gap narrower than 1.0 mm at PD2;
(3) with the heater tied to the −100 V bias, the primary ↔ heater working voltage is 410 Vrms, not 333 Vrms,
so reinforced creepage is 8.2 mm, not 8.0 mm. About 25 spots on the board are at 8.03 to 8.19 mm.
The heatsinks' potential and insulation are still not defined (CANNOT VERIFY).

## Checklist results
| Item | Verdict | Evidence |
|---|---|---|
| A1 | **FAIL** | Numerical integration over one mains period, GND(t) = min(0, 358·sin): 420V − GND → **552 Vrms / 778 Vpk** (README confirmed; worst pair). DC+ − ISO_GND 318 Vrms / 400 Vpk. DC+ − (−100V BIAS) = 500 + GND(t) → **410 Vrms, 500 Vpk, peak in the positive half wave** (GND = 0). DC+ − 420V 192 Vrms. **Primary ↔ heater with HT_GND at −100 V: DC+ − HT = 500 + GND(t) → 410 Vrms**, not √(318² + 100²) = 333 Vrms (README l. 2172, `.kicad_dru` l. 110–112: a DC offset adds linearly to the DC part, it does not add in quadrature) → reinforced 2 × 4.1 = **8.2 mm** (400 / 500 V rows 4.0 / 5.0 mm). See F3 |
| A2 | PASS | TI SLUP421, slide 17 ("Creepage – IEC60664-1 Table F.4"), PD2 MG III: 63 V 1.25, **400 V 4.0, 800 V 8.0, 1000 V 10.0 mm**; footnote "It is possible to use linear interpolation between the nearest two points"; "CPG for reinforced insulation shall be twice the CPG for basic". Interpolating 400–800 V gives 552 V → 5.52 → 11.04 → 11.1 mm, the same as the README's R10 rows (500 V 5.0 / 630 V 6.3 → 5.52). The 250 / 320 / 500 / 630 V rows are not in the fetched source (unconfirmed, but not needed for 552 V). URL https://www.ti.com/lit/pdf/slup421 |
| A3 | PASS | SLUP421 slide 6: IIIa 175 ≤ CTI < 400 "Most FR4 PCBs", IIIb 100 ≤ CTI < 175. Slide 17 has a single "III" column at PD2, so IIIa / IIIb give the same number. **The CTI of the JLC laminate itself could not be found**: no Nan Ya NP-155F datasheet with CTI was found; JLC's capabilities page names "Grade A laminates from suppliers including Nan Ya, KB, Shengyi" and gives no CTI. The numbers hold as long as CTI ≥ 100 |
| A4 | PASS | SLUP421 slide 15: ≤ 300 V, OVC II → 2500 V. Slide 16 (IEC 60664-1 F.2, PD2, ≤ 2000 m; IEC 62368-1 Table 10 in brackets): 2.5 kV 1.5 (1.8) mm, 4.0 kV 3.0 (3.8) mm; "for reinforced … one step higher" → 3.0 / 3.8 mm ≤ **4.0 mm** used. Altitude factor 1.0 at 2000 m |
| A5 | CANNOT VERIFY | IEC 60664-4:2005 is the standard (scope "fundamental frequency above 30 kHz up to 10 MHz"; Table 2 "Minimum values of creepage distances d for different frequency ranges", p. 33; Table 1 clearances). Only the free preview (contents) could be fetched (assets.vde-verlag.de preview PDF), not the table values. The 552 Vrms term is mains frequency; the 140 kHz part is a ≤ 420 V square wave across TR3. Not assessed numerically |
| A6 | PASS | `.kicad_dru` l. 1–216: no rule mentions mask or coating; README "Basis" uses PD2 uncoated; `check_domains.py` uses bare copper |
| A7 | PASS (note) | "ISO_GND always earthed" is in README l. 2171 / 2188–2193 and `.kicad_dru` l. 86–87 only. `grep -i "earth\|chassis"` over the `sh.text(...)` lines of `tools/next/sheets/sheet*.py` and `kicad_next/fab/README.md` finds nothing → not on the schematic and not in the build package (F9) |
| B1 | PASS (gaps listed) | Every row of the table has a clearance + creepage (outer) + inner rule with the stated values (`.kicad_dru` l. 89–216). **Pairs with no rule at all** (neither `.kicad_dru` nor `LIMITS`): PE ↔ HEATER, PE ↔ UART, mounting holes ↔ HEATER, mounting holes ↔ UART. SEC(LV) ↔ heater has no `(layer …)`, so its 1.0 mm also applies on the inner layers (covered). Mounting-hole rules have no layer clause: on the inner layers the **ring** is held at 2.0 mm (clearance) and the **hole** at 3.2 / 4.2 mm (hole_clearance). The README table says "3.2 / 4.2 mm (hole clearance)", so this matches, and the ring of an NPTH is floating on the inner layers. What the missing pairs should be: heater can sit at −100 V → 106 V to the earthed screws → basic, 1.6 mm (63 / 400 V rows interpolated); UART = PC ground → functional ≥ 1.0 mm. Found: PE ↔ heater 12.09 mm, PE ↔ UART 58.9 mm, H1 ↔ heater 3.14 mm, H2 ↔ UART 1.23 mm → met on copper (see D2 for screw heads) |
| B2 | PASS | `LIMITS` (check_domains.py l. 52–64) = `.kicad_dru` for all 11 pairs (inner HEATER–SEC_LV 1.0 and HEATER–UART 1.0 match the layer-less rules); `ALLOW = []` (l. 67). `check_rules.py` CASES l. 29–56 use values consistent with the rules (6.0 < 11.1, 7.0 < 8.0, 4.5 < 5.2, 1.2 < 1.5, 2.5 < 3.2, 8.0 < 8.4, hole 1.5 < 2.0). They are spot tests only: no case for PE–SEC, SEC–UART inner, SEC(HV)–heater inner, the secondary hole rule or the inner hole_clearance. `check_rules.py` l. 58–60 also records that KiCad 10's creepage DRC stays silent at some test spots, so `check_domains.py` is the real guard |
| B3 | PASS | Every exemption rule (same-footprint 0.15, PRIMARY_LV inner 0.15, HV-outer pad-pair / NC exemption, three HS groups) comes **before** all barrier rules in the file. The KiCad documentation as quoted on forum.kicad.info/t/47606 says "Later rules take precedence over earlier rules", and the KiCad developers' list msg43963 / msg43968 (2020) says "last one which matches wins". So no exemption can override a barrier rule. Even under max semantics nothing weakens: no barrier condition overlaps a later rule with a lower value (the PE / hole rules after them name disjoint classes). Exemption conditions: "PRIMARY_LV inner" names only the two primary classes; the HS groups name one domain's nets; "Same-footprint" can match two domains inside ISO1 / ISO2 / U11 (SIGNAL vs HEATER etc.) but is overridden by the later barrier rules |
| B4 | PASS (note) | `setup_project.py --check`: "232/232 nets in one domain class each (SIGNAL 110, PRIMARY_LV 5, HV_PRIMARY 43, SECONDARY_LV 28, HV_SECONDARY 14, HEATER 22, UART_ISO 9, PE_EARTH 1)". Spot checks (`rv bq classes`): Net-(D8-K) HV_SECONDARY, Net-(TR1-A15) SIGNAL, EPWM5A_ISO HEATER, DAB_DIS_SEC SECONDARY_LV, Net-(U11-B1) UART_ISO, HEATER_CURRENT SIGNAL, unconnected-(U11-NC-Pad10/11/15) UART_ISO, unconnected-(DRV6-NC-Pad7/12/13) SECONDARY_LV, Net-(C12-Pad2) / Net-(D7-K) / Net-(DRV3-VDDA) / Net-(R23-Pad2) / Net-(Q21-G) / −100V BIAS in HV classes, Net-(Q8-G) / DHB_LOW_GATE_SEC / GATE1 / GATE2 LV. Every C / D / Z part between an HV and a non-HV net was listed from the netlist (n52.xml). All of them are bulk / filter / Y caps or shunt-node caps (HEATER_CURRENT, DHB_CURRENT ≈ 0 V) or bootstrap diodes → no missing HV net. Note: Net-(TR1-A15) / Net-(TR1-S15) swing to ≈ −400·16/104 = −62 V (−69 V at 450 V) during the on-time (EEL19_DESIGN.md l. 61, 770) and are in LV classes – about 60 V, low concern |
| B5 | PASS | Netlist scan (n52.xml, net class → domain per pin): parts with pins in two domains = C65, C81, C82, C84, C85 (PRI/PE), ISO1, TR2 (PRI/HEAT), ISO2, TR1, TR3 (PRI/SEC), U11 (PRI/UART). DRV3 {PRI}, DRV5 {PRI}, DRV6 {SEC} |
| C1 | PASS | `python3 tools/next/check_domains.py kicad_next/tube_psu_5_2.kicad_pcb` → "7578 copper items on 6 layers, 5 slots, 918 pairs of two domains closer than their largest limit", "layer to layer: 212 pairs … 0 below the limit, 0 accepted", "no pair of two isolation domains below its limit", exit 0, 190 MB RSS |
| C2 | CANNOT VERIFY ((e) only) | (a) The DRC (`check_board.py` l. 76: `kicad-cli pcb drc` without `--refill-zones`) and `check_domains.py` both use the **stored** fill, and Gerbers are plotted from the stored fill, so what is checked is what is made (fab README: fab files from the same board). (b) `HOLES = ^H[1-8]$` only matches what exists; H5 missing is harmless. (c) `GetBoardPolygonOutlines` holes = 5 (L polygon and T slot included); my own polygonize of Edge.Cuts also finds 5 (areas 47.3 / 19.3 / 33.3 / 14.3 / 29.7 mm²). (d) Board edge: the outline is a rectangle, so a straight line between two copper items never leaves the board and any path over the edge is longer. F.Cu ↔ B.Cu is judged as plan distance on one layer, which is conservative (it ignores the 1.6 mm wall). U11 slot end is 6.10 mm from the top edge, TR1 slot end 5.03 mm from the bottom edge. (e) 3-D: no primary single-domain body is within 4 mm (plan) of secondary copper; R27 body 3.84 mm from HT_GND pad R117.2 (ceramic body). TR3 core over the secondary pins, heatsinks (D1), standoffs (D8) need heights that are not in the repository |
| C3 | PASS (explained) | Own script, all 36 layer pairs. Every pair below its limit involving an inner layer is the **plated barrel** of a through-hole pad whose outer pad is also on the outer layer with a milled slot (cutting all six layers) on the line: TR2.10 barrel ↔ ISO1.8 / GND pours (5.36 / 5.94, T slot), TR1.5 / TR1.9 / TR1.11 barrels (9.12 … 10.77, TR1 slot), Q21.3 barrel ↔ DC+ F.Cu pour 7.34 (L slot, path 38 mm), Q8.3 barrel ↔ ISO2.1 10.12 (L + ISO2 slots, path 13.7). Q21 / Q8 are not barrier parts but sit across the L slot, and no inner-layer *plane or track* of another domain is involved. Remaining: H4 ring ↔ PRI_DHB_HI In3 3.179 (see D2) |
| C4 | PASS (margins) | `rv bq dist`: PRI/SEC In1–In4 **11.114** (margin 0.014, TR1.11 DC+ barrel (61.74, 10.80) ↔ TR1.5 barrel (69.45, 2.79)); GND / ISO_GND planes 11.60 – 11.76. PRI/HEATER In1 / In4 **8.138** ((−37.06, −56.82) ↔ (−36.49, −64.94)), In2 / In3 8.277. PRI/UART In1 / In4 **8.054** (margin 0.054, (20.30, −78.76) ↔ (12.25, −78.76)), In2 / In3 9.109. SEC/UART ≥ 42.25, SEC/HEATER ≥ 89.5, PE/PRI inner 3.30 – 3.37 (≥ 3.2), PE/SEC 97. Barrel distances use the finished hole size; the copper wall is at the drilled size, which JLC drills about 0.1 – 0.15 mm larger, and inner registration is ± 0.1 mm (F5) |
| C5 | PASS | Own visibility-graph solver round the 5 slots (table F1). ISO2.8 ↔ 9: 7.25 straight / **12.65** path; ISO1: 7.25 / 8.99 (pins 1 ↔ 16 round the stem end); U11.1 ↔ 16: 7.25 / **8.99**; TR1.2 ↔ 9: 11.02 / 17.43; TR1.11 ↔ 5: 10.27 / 14.51; DC+ ↔ Q21 across the L slot: 6.93 / ≈ 38; FLY_C ↔ SEC F.Cu 9.44 straight (path ≥ 13.2); GND ISO2.8 ↔ Net-(TR1-S15) track: 10.41 / **11.30** (README "≈ 11.8, not re-measured" → 11.30, margin 0.20); TR1-A15 track (F) ↔ TR1.10 (B) 10.50 / **11.31**; heater ↔ GND at the T bar 5.36 / 10.38 (F/B), 7.00 / 9.39 (B/B). Every path ≥ creepage, every straight gap through a slot ≥ 4.0 (smallest 5.36). Overall minima: PRI–SECLV 11.300, PRI–SECHV 13.18, PRI–HEATER 8.99, PRI–UART 8.87 |
| C6 | **FAIL** | `rv bq slots` = Edge.Cuts `.gm1` (fab README l. 122–132, "3 slots exactly 1 mm"). Widths: ISO2 1.0, TR1 1.2, U11 1.0, T 1.0, L 1.2 mm. JLC capabilities page (read today): "minimum Non-Plated Slot Width is 1.0mm", tolerance **"Non-plated: ±0.2mm"**. SLUP421 slide 22: groove / cut-out counts only if X ≥ 1.0 mm at PD2 (IEC 60664-1 6.2). Copper to slot ≥ 0.30 mm (ISO_GND B.Cu pour at the L slot; TR1.11 pad 0.50). **FR-4 web < 2 mm**: Q21.1 hole 1.00 mm from the L slot, TR1.11 hole 1.00 mm from the TR1 slot, TR2.10 hole 1.16 mm from the T slot; L ↔ ISO2 slot web 2.85, ISO2 ↔ TR1 3.8. Slot nearest an edge: TR1 (5.03 mm) (F2, F8) |
| D1 | CANNOT VERIFY | No heatsink footprint on the board (`Heatsink_Plate_Keepout_L120mm` is not placed; README l. 2059 "plate = primary / earthed"). NEXT_REVISION 5.5 asks for "reinforced in total"; for the secondary plate nothing is written beyond "own secondary heatsink" (README l. 1428). Q21 / Q8 (rot 180) put their tab side at y −38.5, *south* of the L slot strip (y −40.4 … −39.2), over the "barrier pour keep-out … under the heatsink plate" (x 52.5 … 71, y −39.2 … −33). A 3 mm plate at y −38.5 … −35.5 is **3.59 mm** (plan) from primary GND B.Cu, and **1.09 mm** if the plate reaches y −33. The primary plate strip (x 5 … 13, y −66 … 8) is **7.2 mm** from U11.9 ISO_UART_GND (< 8.0 if the plate is at primary potential, fine if earthed). Tab potentials (from the board): Q5 / Q6 drain = PFC switch nodes, SICD1 / 2 K = DC+, DB1, Q7 drain = DHB_HI_SOURCE, Q19 drain = DC+ (STF FullPAK); Q21 drain 420V, Q8 drain = switch node (FullPAK). FullPAK isolation rating not fetched (F4) |
| D2 | **FAIL** | `d2.py` (centre-to-copper on F.Cu / B.Cu minus head radius): H4 PRI 4.98 mm from centre → ring 3.23, **6 mm head 1.98, 7 mm washer 1.48** (need 2.0 clearance / 3.2 creepage); H6 IN2 (mains) 1.98 / 1.48; H7 GND 1.98 / 1.48 (F and B); H3 420V / ISO_GND 2.97 / 2.47 (need 4.2 creepage); H8 −100 V / ISO_GND 2.97 / 2.47; H1 6V3 1.89 / 1.39; H2 ISO_UART_GND B.Cu −0.02 / −0.52 (touches), UART_TXD F.Cu 0.50 / 0.00. Bodies inside a 7 mm circle: U11 (H2), J4 (H2), L1 (H7), C102 (H8). Inner layers: H4 ↔ PRI_DHB_HI In3 3.179 from the ring, 3.429 from the hole wall (NPTH: inner ring floating) → rule (2.0 ring / 3.2 hole) met. The H4 ↔ DC+ figure in the checklist ("3.23") is DC+ at 3.227 from the ring on F.Cu (`rv bq near H4`) (F1) |
| D3 | PASS | No rule (B1). Required: H1 ↔ heater basic for 106 V → 1.6 mm; H2 ↔ UART functional 1.0 mm. Found from the ring: H1 ↔ 6V3 3.137 (all layers), HT_GND 3.227; H2 ↔ ISO_UART_GND 1.232 (B.Cu), UART_TXD 1.750 (F.Cu), 1.933 inner. Met on copper. With heads / washers see D2 |
| D4 | PASS | `rv bq dist @PE @PRI`: F 3.234, In1 3.346, In2 3.300, In3 3.367, In4 3.346, B 3.239 (≥ 3.2); @PE @SEC ≥ 96.9; @PE @HEATER ≥ 12.09; PE copper is B.Cu tracks only (`rv bq net "/05 PFC/PE"`); R4 / R5 / R6 (F.Cu, x −63.6) are 10.9 – 12.5 mm from any PE copper, no crossing |
| D5 | CANNOT VERIFY | Terminals are 2-pin 6.3 mm tab footprints (5 mm pitch, Ø 2.0 pad), identical in place to 5.1 (`rv bq51 fp P400V,GND,HT_6V3`). Different domains: only HT_6V3 / HT_GND (heater, possibly −100 V) ↔ H1: pad 3.137 mm from the ring. A receptacle on HT_6V3 (blade along y, pads −76.8 / −81.8; body ≈ to y −84.3 assumed) against a 6 mm screw head at H1 (edge y −84.5) leaves ≈ 0.2 mm (estimate). Same domain: P400V ↔ GND(ISO_GND) pad gap 3.31 mm, 5.3 mm pitch → with an uninsulated receptacle ≈ 3.6 mm thick (assumed) ≈ 1.7 mm air at 420 V (functional 1.2 met). N80V_OUT ↔ P5V_OUT 5.8 mm pitch. Insulated receptacles (≈ 7–9 mm) would collide at 5.3 mm pitch. No receptacle defined in the repository |
| D6 | PASS | `rv bq near @HV_PRIMARY / @HV_SECONDARY --within 0.49 --layer In1…In4` → "0 net/layer pairs" on all 8 queries. 5.1: `rv bq51 near DC+ --within 0.49 --layer In1` → **0.150 mm DC+ ↔ GND** at (21.03, 8.17), so 5.2 is better. Basis: SLUP421 slide 17 PD1 "all material groups" 400 V 1.0 / 800 V 2.4 mm is *surface* creepage. Inside the laminate it is solid insulation / a cemented joint, and functional insulation may also be justified by test (slide 26, IEC 60664-1 5.1.3.3 / 62368-1 B.4.4). 0.5 mm is a functional choice, not worse than 5.1; registration ± 0.1 mm not included |
| D7 | PASS | `d7.py`: every outer-layer pair < 1.2 mm with an HV net = 99 pad-pad + 170 same-HS-group + 8 NC-pad; **0 unexempted**. Examples: Q19 / Q21 / Q7 TO-220 pins 0.635 mm (part pitch, as 5.1), DC+ pour 0.500 mm to unconnected-(U11-NC-Pad8) (−5.99, −72.95), RES_IN 0.638 to RL1.2 (NC), HEATER_HI_GATE via 0.200 to HEATER_HI_SOURCE pour (group) |
| D8 | CANNOT VERIFY | Standoff height, chassis material under the board and lead protrusion are not in the repository. Needed: standoff height (≥ 4.0 mm clearance from any B.Cu pin tip / fillet of primary to chassis if the chassis is earthed metal; ≥ 2.0 basic). TR1 fly-lead pads 11 / 12 (DC+ / FLY_C) ↔ pin 5 (Net-(D8-K)) on B.Cu: pad gap 10.27, path 14.51 mm round the TR1 slot; fillets reduce this by ≈ 0.5 mm, still ≥ 11.1 |
| E1 | PASS | Table "Compared with 5.1": every barrier ≥ 5.1 or replaced by a slot path ≥ the requirement; the one smaller number (GND ↔ HT_GND In1 9.00 vs 10.37 mm) is still ≥ 8.0 |
| F1 | PASS | Table F1 below |
| F2 | PASS | List F2 below |

### F1 table – barriers, requirement and smallest value found

| Barrier | Req. clr / creep / inner | Outer straight (smallest) | Outer round slot (smallest path) | Inner (same layer) | Layer to layer | Location of the minimum | Margin |
|---|---|---|---|---|---|---|---|
| PRI ↔ SEC | 4.0 / 11.1 / 11.1 | 6.93 (DC+ ↔ Q21, L slot) | **11.30** (ISO2.8 GND ↔ TR1-S15 track) | **11.114** (TR1.11 ↔ TR1.5 barrels) | 11.31 (F TR1-A15 track ↔ B TR1.10) | (63.09, −21.90)/(71.69, −16.04); (61.74, 10.80)/(69.45, 2.79) | path +0.20, inner +0.014 |
| PRI ↔ HEATER | 4.0 / 8.0 (8.2, F3) / 8.0 | 5.36 (ISO1.8 ↔ TR2.10, T bar) | **8.99** (ISO1.1 ↔ ISO1.16) | **8.138** | 8.029 (B GPIO_BYPASS_RLY ↔ F ISO1.16), 8.13 In1/In4 ↔ F | (−45.45, −42.1); (−37.06, −56.82) | +0.03 … +0.14 vs 8.0; −0.17 … −0.06 vs 8.2 |
| PRI ↔ UART | 4.0 / 8.0 / 8.0 | 7.25 (U11 rows, slot) | **8.87** (B GND pour ↔ U11.16), 8.99 (U11.1 ↔ 16) | **8.054** | ≥ 8.0 (checker) | (20.30, −78.76)/(12.25, −78.76) | inner +0.054 |
| SEC ↔ UART | 3.0 / 8.4 / 8.4 | 46.8 | – | 42.25 | – | – | large |
| SEC(HV) ↔ HEATER | 1.5 / 5.2 / 5.2 | 90.2 | – | 89.5 | – | – | large |
| PE ↔ PRI | 2.0 / 3.2 / 3.2 | 3.234 | – | 3.300 (In2) | – | (−46.70, 4.00)/(−46.70, 7.23) | +0.034 |
| PE ↔ SEC | 1.5 / 4.2 / 4.2 | 96.9 | – | 97.3 | – | – | large |
| Holes ↔ PRI | 2.0 / 3.2 / 3.2 (hole) | 3.227 from ring (H4 DC+, H6 IN2, H7 GND) | – | 3.179 ring / 3.429 hole (H4 In3) | – | H4 (5.84, −40.13) | +0.03 ring; **−1.7 with 7 mm washer** |
| Holes ↔ SEC | 1.5 / 4.2 / 4.2 | 4.222 (H3, H8) | – | – | – | H3, H8 | +0.02 ring; −1.7 with washer |
| Holes ↔ heater / UART | (no rule) 1.6 / 1.0 | 3.137 (H1) / 1.232 (H2) | – | 1.933 (H2) | – | H1, H2 | met on ring |

### F2 – not covered by any automatic check
- Screw heads, washers, standoffs at H1 – H8 (D2): checked here by hand; hardware not defined (owner).
- Heatsinks, both plates (D1): potential, insulation pads, plate outline and height not defined (owner, checklist 12).
- Blade receptacles on the terminals (D5): type / width not defined (owner).
- Lead protrusion / standoff height under the board (D8): owner.
- Slot width tolerance (C6): not in any check (`check_domains.py` uses nominal outlines).
- Mounting holes ↔ heater / UART and PE ↔ heater / UART (B1): no rule, checked by hand here.
- Barrel vs drilled-hole diameter and inner-layer registration (C4): not in any check.
- IEC 60664-4 > 30 kHz (A5): not assessed.
- Transformer internals (TR1 / TR2 / TR3 margins, tape, core over the pins) and isolator / driver certificates: checklists 01, 03, 04, 06, 07.

## Findings (ranked, most severe first)

### F1 Mounting-hole keep-off is measured from the 3.5 mm ring, but the earthed screw hardware is larger
- Severity: **should fix**
- What is wrong: H1 – H8 are NPTH 3.0 mm with a 0.25 mm copper ring (Ø 3.5). The PE keep-off (3.2 mm primary, 4.2 mm secondary) is held from that ring. An M3 head is 5.5 – 6 mm, a washer 7 mm, a hex standoff about 6.4 mm across corners. Measured from that metal, creepage to primary copper is 1.98 mm at H4 (PFC_DRAIN_1 / DC+ / DRV5-VDDA), H6 (mains IN2) and H7 (GND) with a 6 mm head, and 1.48 mm with a 7 mm washer. Requirement: basic 3.2 mm creepage / 2.0 mm clearance. Even a 5.5 mm head leaves 2.23 mm < 3.2. On the secondary side, H3 / H8 have 2.97 / 2.47 mm against 4.2. Solder mask gets no credit (README basis, A6). H2: a 6 mm head reaches ISO_UART_GND on B.Cu (−0.02 mm) and the U11 / J4 bodies.
- Evidence: `python3 d2.py` (scratchpad) – lines "H4 … top PRI r=4.98 ring 3.23 6mm 1.98 7mm 1.48", "H6 … 1.98 / 1.48", "H7 … 1.98 / 1.48", "H3 … 2.97 / 2.47"; `rv bq near H4 --within 4.3` (DC+ F.Cu 3.227 mm from the ring).
- Smallest fix: a build note in the README / fab notes: insulating (nylon) washers under the heads and nylon standoffs (or nylon screws). The board is earthed through the PE terminal, so the screws do not need to make contact. The alternative is to grow the keep-off by about 1.75 mm round H3, H4, H6, H7, H8, which is more layout work.
- Confidence: high on the geometry; medium on relevance, because the hardware the owner will use is not in the repository. Still far better than 5.1 (H4 ↔ copper 0.75 – 1.35 mm there).

### F2 Three creepage slots are exactly 1.0 mm wide, and JLC holds ±0.2 mm on non-plated slots
- Severity: **should fix** (cheap; before ordering)
- What is wrong: the ISO2 slot (x 66.26 … 67.26), the U11 slot (x −0.5 … 0.5) and the T slot at ISO1 / TR2 (bar y −64.09 … −63.09, stem x −42.86 … −41.86) are 1.0 mm nominal. JLC: "minimum Non-Plated Slot Width is 1.0mm", tolerance "Non-plated: ±0.2mm". IEC 60664-1 6.2 (SLUP421 slide 22): at PD2 a cut-out counts only if X ≥ 1.0 mm, otherwise creepage is measured straight across it. Without the slot credit, ISO2 is 7.25 mm against 11.1, U11 7.25 against 8.0, and heater ↔ GND at the T bar 5.36 against 8.0. The fab README (item 7) already flags "JLC may ask or widen".
- Evidence: `rv bq slots` (widths above); https://jlcpcb.com/capabilities/pcb-capabilities (read 2026-11-23); `kicad_next/fab/README.md` l. 104, 132, 213.
- Smallest fix: widen the three slots to 1.4 – 1.5 mm (1.0 + tolerance + margin). Pad rows of the isolators are 7.25 mm apart, so a 1.5 mm slot still leaves ≥ 2.8 mm to each pad row. For the T bar, check the TR2.10 hole web (1.16 mm now, about 0.9 mm after widening; see F8). Re-run `check_domains.py` and the creepage DRC.
- Confidence: high (both numbers from fetched sources); medium on whether JLC actually mills undersize (a 1.0 mm tool is usually ≥ 1.0 mm).

### F3 Primary ↔ heater working voltage is 410 Vrms (heater on the −100 V bias), so reinforced creepage is 8.2 mm, not 8.0 mm
- Severity: **should fix** (basis / document; about 25 spots 0.01 – 0.17 mm short)
- What is wrong: README l. 2172 and `.kicad_dru` l. 110–112 take √(318² + 100²) = 333 Vrms. DC+ − HT_GND = 400 + 100 + GND(t) when HT_GND = −100 V (ISO_GND earthed). The 100 V is a DC shift and adds linearly: rms = **410 V**, peak 500 V (positive half wave). Basic is 4.1 mm (400 / 500 V rows 4.0 / 5.0, interpolation allowed, SLUP421 slide 17), reinforced 8.2 mm. The board was laid out to 8.0. Below 8.2: inner In1 / In4 8.130 – 8.138 (HT_GND planes ↔ ISO1 primary pads, GND planes ↔ ISO1.16, RL1-COM F.Cu pour ↔ HT_GND In1 at (−60.56, −46.76)); F.Cu ↔ B.Cu 8.029 (GPIO_BYPASS_RLY track (−45.45, −42.0) ↔ ISO1.16). All slot paths are ≥ 8.99 and pass.
- Evidence: calculation in A1 (numpy over one period, 358 V peak mains); `python3 h82.py` (scratchpad) list; `rv bq dist @PRI @HEATER` (In1 8.138).
- Smallest fix: correct the README / `.kicad_dru` comment and either (a) state that the heater reference must not go below about −30 V relative to the earthed secondary (−30 V gives 343 Vrms → 6.9 mm, so 8.0 mm holds), or (b) raise the PRI-HEATER limit to 8.2 mm in `.kicad_dru`, `LIMITS` and `check_rules.py`, then pull back the HT_GND / GND In1 / In4 plane edges and the GPIO_BYPASS_RLY track by 0.1 – 0.2 mm.
- Confidence: high on the arithmetic; medium on how much it matters (inner layers carry no surface creepage, and the margin is 2 %).

### F4 Heatsink potentials and insulation are not defined; the secondary plate stands over the primary side of the L slot
- Severity: **should fix** (definition / document; possibly layout)
- What is wrong: Q21 / Q8 face their tabs south (y −38.5), so a plate on them lies over x 52 … 74, y ≥ −38.5. That is beyond the L-slot strip and over the "barrier pour keep-out under the heatsink plate". If the plate is at, or floats with, the secondary, it is 3.59 mm (plan, 3 mm plate) from primary GND B.Cu, and 1.09 mm if it reaches y −33. The required clearance is 4.0 mm and the FullPAK rating is unverified. The primary plate (x 5 … 13 down to Q7 at y −66) is 7.2 mm from U11.9 ISO_UART_GND: fine if the plate is earthed, short of 8.0 if it floats at a primary tab potential (SICD1 / SICD2 / DB1 tabs are bare).
- Evidence: `python3 c2e.py` / `d1.py` (scratchpad); board zone "barrier pour keep-out: Q21 / Q8 to ISO2 under the heatsink plate" (x 52.5 … 71, y −39.2 … −33); README l. 1428, 2059, 2213; NEXT_REVISION 5.5.
- Smallest fix: write down, in the README "Isolation domains", each plate's potential (primary plate: earthed via H4 / chassis, or floating), the tab insulation (FullPAK on Q7 / Q8 / Q19 / Q21; rated pads + shoulder washers on Q5 / Q6 / SICD / DB1), the outline and the minimum height above the board. Then check plate ↔ other-domain copper ≥ 4.0 mm in 3-D (≥ 11.1 creepage if the plate touches the board).
- Confidence: medium (the geometry is an assumption, because no plate drawing exists).

### F5 Inner-layer margins of 0.014 / 0.054 mm are measured to the finished hole, not to the copper barrel
- Severity: **note**
- What is wrong: PRI/SEC 11.114 mm (TR1.11 ↔ TR1.5 barrels) and PRI/UART 8.054 mm are measured with the finished drill diameter. The barrel's outer copper is at the drilled diameter (JLC typically drills 0.1 – 0.15 mm over the finished size; plated-hole tolerance +0.13 / −0.08). Inner registration is ± 0.1 mm. Real copper-to-copper is about 11.0 / 7.95 mm. Inside the laminate there is no surface creepage, so the 11.1 / 8.0 inner targets are self-imposed and conservative.
- Evidence: `rv bq dist @PRI @SEC` (In1–In4 11.114 at (61.74, 10.80)/(69.45, 2.79)); `rv bq dist @PRI @UART` (In1 / In4 8.054).
- Smallest fix: none needed for the order; optionally state in the README that inner values are to the finished hole.
- Confidence: high.

### F6 No rule for mounting holes / PE ↔ heater and UART
- Severity: **note**
- What is wrong: `.kicad_dru` and `LIMITS` have no pair for HOLE / PE ↔ HEATER / UART, so a future change near H1 / H2 is unchecked. The values now (H1 ↔ 6V3 3.14 mm, H2 ↔ ISO_UART_GND 1.23 mm) meet a sensible 1.6 mm (basic, heater at −100 V) / 1.0 mm (functional).
- Evidence: `.kicad_dru` l. 206–216 name only primary / secondary classes; `check_domains.py` l. 52–64.
- Smallest fix: add "Mounting hole – heater" (clearance 1.5, creepage 1.6) and "Mounting hole – UART" (1.0) to both files.
- Confidence: high.

### F7 Isolator datasheet facts (for the creepage basis)
- Severity: **note**
- What is wrong / found: ISO1 / ISO2 = CA-IS3761LW. Datasheet CA-IS376x 修订版 B (2019, p. 7, 7.6): W package CLR 8 mm, CPG 8 mm, CTI > 600 V, material group I, VIOWM 1000 Vrms, VIORM 1414 Vpk; p. 8 7.7: VDE / CSA (IEC 62368-1) / UL / CQC all "申请中" (pending) in that revision. U11 = CA-IS3721HW, CA-IS372x Version 1.02 (2022-09-06): SOIC16-W CLR / CPG 8 mm (p. 8), CTI > 600, MG I, VIOWM 1000 Vrms; CQC "SOP16-W: Reinforced insulation, 1000 VRMS maximum working voltage" (p. 9). Package body creepage needed for 552 Vrms reinforced at MG I = 2 × 2.76 = 5.5 mm ≤ 8 mm. UCC21520 (SLUSCJ9F, Nov 2024): CLR / CPG > 8 mm, CTI > 600 V, used as functional only (both sides one domain). README l. 2203 still names Si8661BD / Si8621BD. The reinforced certificate of CA-IS3761LW belongs to checklist 03.
- Evidence: https://static.chipdip.ru/lib/883/DOC017883050.pdf; https://tellur-el.ru/upload/iblock/8f8/w6g3uwhscr832bchk0dubqicf3m5lfq6.pdf; https://www.ti.com/lit/ds/symlink/ucc21520.pdf
- Smallest fix: update the README isolator names; checklist 03 to confirm the current CA-IS3761 certificate.
- Confidence: medium (the CA-IS376x revision fetched is older than v1.04 / v1.05).

### F8 FR-4 web between slots and plated holes is 1.0 – 1.16 mm
- Severity: **note**
- What is wrong: Q21.1 hole 1.00 mm from the L slot, TR1.11 hole 1.00 mm from the TR1 slot, TR2.10 hole 1.16 mm from the T slot. Thin webs crack under lead force or assembly, but this is mechanical, not a creepage loss.
- Evidence: `python3 c6.py` (scratchpad).
- Smallest fix: none required; keep it in mind if F2 widens the slots (do not go below about 0.8 mm).
- Confidence: high.

### F9 "ISO_GND always earthed" is not where the builder will read it
- Severity: **note**
- What is wrong: the 11.1 mm basis depends on it (else 16 mm, README l. 2188). It is in README / `.kicad_dru` only: not on a schematic sheet note, not in `kicad_next/fab/README.md`.
- Smallest fix: one `sh.text` note on sheet 7 (secondary) and one line in the fab / build notes.
- Confidence: high.

### F10 Terminal receptacles and the HT_6V3 ↔ H1 corner
- Severity: **note** (same as 5.1)
- What is wrong: with a receptacle on HT_6V3 and a 6 mm screw head at H1 the estimated gap is ≈ 0.2 mm. The heater may sit at −100 V against the earthed screw. P400V ↔ GND receptacles ≈ 1.7 mm apart (assumed uninsulated, 3.6 mm thick).
- Evidence: D5; `rv bq dist fp:HT_6V3 H1` 3.137 mm.
- Smallest fix: insulated receptacles on HT_6V3 / HT_GND or a nylon washer at H1 (see F1).
- Confidence: low (receptacle dimensions assumed).

## Compared with 5.1
| Barrier / item | 5.1 (`rv bq51`) | 5.2 | Verdict |
|---|---|---|---|
| GND ↔ ISO_GND | F 7.22 / In1 6.72 / In2 6.80 / B 6.72 mm, no slots | F 7.25 straight but 12.65 path (ISO2 slot), In1–In4 11.60 – 11.76, B 9.27 | better |
| DC+ ↔ ISO_GND | **F 5.08** (NEXT_REVISION 1.4 weak spot), inner 10.05 – 10.12 | F 7.78, inner 12.40 – 13.84, B 10.37 | better |
| DC+ ↔ 420V | F 9.24, inner / B 9.70 | F 9.46 (L slot, path ≈ 38), inner 37.7, B 34.3 | better |
| PRI ↔ SEC (whole domains) | – (Default classes) | min path 11.30, inner 11.114 | meets 11.1 |
| GND ↔ HT_GND | F 7.35, In1 10.37, In2 11.46, B 6.94 | F 7.25 (path ≥ 8.99), In1 9.00, In2 10.71, B 8.33 | better outside, In1 smaller but ≥ 8.0 |
| Isolators ISO1 / ISO2 | no slots | slots, paths 8.99 / 12.65 | better |
| UART | J4 not isolated | U11 island, path ≥ 8.87, inner 8.054 | new barrier |
| Mounting holes | H4 0.75 – 1.35 mm to copper (In2 GPIO_BYPASS_RLY 0.745, F Net-(L2-2) 1.348), H6 ↔ IN2 2.31 | ≥ 3.18 (ring) everywhere | better (but F1) |
| HV inner spacing | DC+ ↔ GND 0.150 mm on In1 | ≥ 0.5 mm all HV nets, all inner layers | better |
| Terminals | positions as 5.2 | unchanged | equal |

## Could not verify
- CTI of the JLC laminate (no Nan Ya NP-155F datasheet with CTI found; JLC page gives no CTI).
- IEC 60664-4 Table 1 / Table 2 values (> 30 kHz): standard not freely available; preview has the contents only.
- IEC 62368-1 clause texts (clause numbers in the README come from SLUP421 / memory, as the README says).
- Heatsink outlines, heights, potentials and tab insulation (D1); STF7N60M2 FullPAK isolation voltage (datasheet not fetched).
- Mounting hardware (screw head, washer, standoff material / height) (D2, D8), and the blade receptacle type (D5).
- Current CA-IS3761 certificate (fetched revision B lists all certificates as pending).
- KiCad 10 rule precedence: no official KiCad 10 page could be fetched (docs.kicad.org advanced page 404). The verdict rests on the forum-quoted documentation sentence and the developers' list, and it holds under either semantics because of the rule order.

## Outside scope
- Courtyard / body clashes with a 7 mm circle at H2 (U11, J4), H7 (L1), H8 (C102); L1 courtyard 1.66 mm from H7's centre → checklist 12.
- Insulated 6.3 mm receptacles do not fit at 5.3 mm pitch (P400V / GND) → checklist 12.
- README isolator part names (Si8661BD / Si8621BD vs CA-IS3761LW / CA-IS3721HW) → checklists 03 / 04.
- Net-(TR1-A15) / Net-(TR1-S15) swing ≈ 62 – 69 V peak in LV classes → checklist 01.
- DC+ pour runs up to U11's primary pin row (0.5 mm to NC pad 8 at (−5.99, −72.95)) → checklist 04 / 11 (why DC+ is there; floating NC pad between DC+ and GND pad 7).
