# tube_power 5.2 – optional improvements (after layout)

Improvements that are **not** in the 5.2 schematic. Each one has been looked at during the design and kept out
on purpose: the present design meets the requirement without it. Revisit them once the board is placed and
routed (phase 5/6 of [NEXT_REVISION_PLAN.md](NEXT_REVISION_PLAN.md)), when the real space, copper areas and
thermal paths are known, or after the first board has been measured.

Columns: **When** = what would make it worth doing; **Cost** = what it changes on the board.
The mandatory changes are in [NEXT_REVISION.md](NEXT_REVISION.md) and
[kicad_next/CHANGES_5_2.md](kicad_next/CHANGES_5_2.md).

## 1. Aux flyback (TR1, PWM2 ICE5AR0680AG)

| # | Improvement | When | Cost | Ref |
|---|---|---|---|---|
| 1.1 | **C1 / C2 → EEEFT1E471AP** (470 µF 25 V, 850 mA rms, 80 mΩ, C178591, 8 × 10.2 mm) on 15V / 15V_ISO_SEC. Today EEEFTE221XAP is rated 600 mA rms against ≈ 0.6 A rms at 20 W | 20 W continuous at high ambient is a real use case, or the caps run hot on the first board | new 8 mm footprint ×2, room next to TR1 | NR 1.11, EEL19_DESIGN.md 14 |
| 1.2 | Same ripple check / upsizing for C6, C36, C71, C114, C115 if 1.1 is done | as 1.1 | footprints | NR 1.11 |
| 1.3 | **Larger drain copper** for PWM2 than the 2–3 cm² placement constraint | the CoolMOS case is hotter than ≈ 95 °C at 20 W / 100 V on the bench | copper area F.Cu + B.Cu (no inner layers, primary domain) | EEL19_DESIGN.md 14 |
| 1.4 | **Line OVP divider DNP** (R151–R153 not fitted → VIN held at GND by R154, LOVP off) | the PFC OVP is trusted and the divider's ≈ 7 mW / 3 HV resistors are unwanted; or the 460–505 V trip window interferes with a bus test | BOM only | CHANGES 1.5 VIN |
| 1.5 | Lp 650 µH / Rcs 0.75 Ω TR1 variant (1–3 K cooler) | only if the full-load start at 100 V is never needed: at the minimum current limit it needs 31 ms against the 30 ms OLP blanking | TR1 gap + Rcs | EEL19_DESIGN.md 14 |
| 1.6 | Clamp R45 → 2 × 100k | the bench VDS is above ≈ 650 V at a 450 V bus | resistor value | CHANGES 1.5 clamp |
| 1.7 | Accurate 12-lead 3D model for PG-DSO-12 (today the stock SOIC-16 model, 16 leads drawn) | renders / mechanical review | gen_next_3d.py (CadQuery) | kicad_next/README.md |

First-board fallback (not an improvement, kept here for reference): today's TR1 winding with only the new Rcs also
delivers 20 W at 100 V, at ΔT ≈ 56 K (4 K below the limit).

## 2. DAB (TR3, Q-bridge, DRV5/DRV6)

| # | Improvement | When | Cost | Ref |
|---|---|---|---|---|
| 2.1 | **Lower-RDS(on) MOSFETs** than STF7N60M2 (1.3 Ω hot): the sending bridge carries 3.4 W per switch, the dominant DAB loss (11.6 W total at 400 W). A ≈ 0.3–0.6 Ω part roughly halves to quarters it, and makes synchronous rectification worthwhile on the receiving side | heatsink temperature on the bench, or more output power | part swap (TO-220/TO-247 on the shared bent-plate heatsink; check Coss for the 150 ns dead time / 66 ns no-load swing) | DAB_SIMULATION.md 3 |
| 2.2 | **Vacuum impregnation** of TR3 (and TR1) | partial discharge margin at 778 Vpk / humidity; audible noise | process only | DAB_TRANSFORMER.md 8.1 |
| 2.3 | Keep the RM8 L3 pads with a jumper | if the TR3 leakage turns out too small for the phase-shift range | board space for the RM8 | NR 2.4 |
| 2.4 | Load-dependent dead time: 150 ns below ≈ 150 W, 100 ns above (firmware) | efficiency tuning | firmware | DAB_SIMULATION.md |
| 2.5 | Burst mode at light load / DC+ tracking (firmware) against mismatch hard switching | larger input/output mismatch than ±2 % | firmware | DAB_SIMULATION.md 3 |

## 3. Measurements

| # | Improvement | When | Cost | Ref |
|---|---|---|---|---|
| 3.1 | U9 (TLV316 bias buffer) split feedback 100k + 1 nF against the 29 mA line-frequency term on PFC_I | the bias ripple is visible in PFC_I | 2 parts | FINDINGS.md 11.3 |
| 3.2 | PFC shunt ESL compensation caps 27–33 pF | only if the bench shows a spike on PFC_I | 2 caps | FINDINGS.md 11.4 |
| 3.3 | Retune the ESL caps 12p / 5.6p; rescale if the shunts become 5 mΩ (KRL2012E) | bench | values | CHANGES open question 7 |
| 3.4 | INA296B current-sense amplifiers instead of LMH6643 (saves 18 resistors / 6 caps; 1.1 MHz bandwidth, fixed gains, needs the bias reference kept for the bidirectional DAB current) | not taken (user 2026-11-17: LMH6643); only if space becomes critical | rework of 4 channels | NR 4.10 |

## 4. Parts and sourcing

| # | Item | When | Cost | Ref |
|---|---|---|---|---|
| 4.1 | PWM2 ICE5AR0680AG: JLC had **3 pcs** (C17699638) – consign the bought parts | at order time | – | jlc_parts_next.csv |
| 4.2 | R124 2.61k low JLC stock (75 / 43 pcs) – pick an alternative value/series | at order time | value | CHANGES open question 11 |
| 4.3 | C73 (2.2 µF 450 V X6S 2220 on DC+): ≥ 630 V part when one is stocked | stock appears | part | NR 5.6 |
| 4.4 | CA-IS3761LW / CA-IS3721HW: get current VDE/UL certificates for the 552 Vrms reinforced barrier; fall back to Si8661BD/Si8621 if not certified | before ordering | part swap (same pinout) | CHANGES open question 2 |
