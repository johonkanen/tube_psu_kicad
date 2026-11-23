# Findings: 11 power loops / layout  (reviewer: Claude Opus 5.5, 2026-11-23, commit 01a1adf)

## Summary
No blocker for ordering found in the power loops, return paths or copper cross-sections. Against the bench-verified
5.1 board the commutation loops are equal or smaller (PFC legs, DAB primary, DAB secondary), the gate loops of the DAB
primary are clearly shorter, and the switch-node copper is smaller. 5.2 is narrower than 5.1 in several DC+ / drain
necks (Q19 drain entry, SICD1 neck, PFC_DRAIN_1 lobe at the SICD1 anode, heater DC+ branch, Q14_DRAIN), but every one
carries its current with factor >= 1.4 ... 12 by the project rule. One item should be fixed: the DAB **secondary**
switch node reaches Q8 drain only through **one 1.0/0.5 mm via and 0.75 mm exits** (2.2 A rms; 5.1 had 4 vias plus an
In2 pour). **The DAB primary commutation loop is not 6× worse than 5.1**: the 9 mm² figure for 5.1 comes from a
pad-centre polygon that does not follow the 5.1 copper. With the real copper paths, 5.1 encloses 69 - 78 mm² and 5.2
encloses 58 mm². Estimated inductance is 24 - 26 nH on 5.1 against 20 nH on 5.2 (about 9 nH counting In1 shielding).
See "DAB primary loop: the two figures explained".

Method: helper dumps `/tmp/tube_psu_review_1000/b52.json` / `b51.json` (`rv setup` already run, `rv guard`: no lock
file, no KiCad job), `rv bq …` / `rv bq51 …`, and four read-only scripts in my scratch directory (outside the
repository): `plot.py` (renders nets per layer), `lind.py` / `loops.py` (partial-inductance loop model), `rpath.py`
(shortest-resistance path of a net), and `neckloc.py`. No DRC was run; `reports/next/drc.json` is current
(`drc_summary.py`: newer than the board, 137 items, 2 starved_thermal = C102 pin 1 only). The `routing/*.png` layer
plots of the outer layers are from 2026-11-22 17:13, older than the board (2026-11-23 19:32), so I used my own renders.

## DAB primary loop: the two figures explained

| figure | what it measures | does it describe the commutation loop? |
|---|---|---|
| "switch-node area 207 → 144 mm²" (draft verification, `verify/report_t4.md` row 16 in the session scratch of that run – **not** in `kicad_next/README.md`; the README stage-7 text has no such numbers) | copper area of net DHB_HI_SOURCE on the outer layers. Re-measured on the current boards: 5.1 F.Cu 173 + B.Cu 34 = **207 mm²**, 5.2 F.Cu 123 + B.Cu 22 = **145 mm²** (plus about 13 mm² of pad rings per inner layer on 5.2) | **No.** It sets the dV/dt-driven capacitive coupling / EMI antenna of the node, not the di/dt loop inductance |
| "gate loops much shorter" (same report, rows 1 - 8) | driver → gate resistor → gate → source → driver paths | **No.** Gate loops. Confirmed: Q19 turn-on loop pad-centre path 21.6 mm (5.2) against 55.8 mm (5.1) |
| same report, row 13 ("DC+ decoupling loop", 33.2 → 38.5 mm, "same") | path length of Q19 drain → C67 → Q7 source + the switch-node leg | yes, but path length only |
| checklist: "≈ 40 mm / 60 mm² (5.2) against ≈ 41 mm / 9 mm² (5.1)" (`rv bq loop Q19.2 Q19.3 Q7.2 Q7.3 C67.2 C67.1`) | polygon through pad **centres**, closed by straight lines | **5.2: yes (close to the copper). 5.1: no.** On 5.1 all six pads lie in one row (y −41.9 … −43.7). The closing line C67.1 (25.2, −43.7) → Q19.2 (45.6, −41.9) runs back along the row, over the forward path. The real 5.1 copper is different: the DC+ return runs in a 5.6 mm band 3.6 mm south of the row (`rv bq51 xsec DC+ F.Cu x 35 -46 -30`: y −38.30 … −32.71, and the drop at Q19 `… y -40 40 50`: x 44.51 … 46.82). The forward switch node runs 2.5 mm north of the row (1.778 mm track Q7.2 → (34.3, −43.5) → y −44.41 → Q19.3, `rv bq51 net DHB_HI_SOURCE`) |

**The commutation loop that matters** is the edge loop Q19 drain → Q19 → switch node → Q7 → Q7 source → C67 / C70
(100 nF + 100 nF, DC+ – DHB_CURRENT) → Q19 drain. At 140 / 280 kHz most of the bridge's AC input current comes from
the bulk capacitors (about 0.2 Ω path against 2.8 Ω for 200 nF at 280 kHz). C67 / C70 take over above about
1 / (2π√(35 nH · 200 nF)) ≈ 1.9 MHz, i.e. during the 9 - 11 ns node swing (DAB_SIMULATION.md 2.1).

Real copper paths (centre lines read from the board; `rv bq loop` with the corner points):

| | 5.1 (4-layer, all on F.Cu) | 5.2 |
|---|---|---|
| path | Q19.2 → DC+ drop x 45.6 → DC+ band (inner edge y −38.3) → x 25.2 → C70 / C67 pad 1 → C → DHB_CURRENT pour → Q7.3 → Q7 → switch node via y −44.4 → Q19.3 | Q19.2 → F.Cu DC+ 0.92 mm entry + zone `S4B_DC+_F` → C67.1 (18.2, −48) [C70 on B.Cu under it, via (18.3, −48.5)] → C67.2 → F.Cu zone → 2 vias 0.8/0.4 (22.6, −49 / −50) → **In2 1.2 mm track** (22.6, −49) – (22.6, −50.9) – (21.2, −52.3) – (17.4, −52.3) – (17.4, −62.14) – (15.5, −62.14) – (14.3, −63.34) – Q7.3 → Q7 → F.Cu switch-node strip x 15 … 16.55 → Q19.3 |
| length / plan-view area | 47.3 mm / 69.1 mm² (C70), 49.6 mm / 78.1 mm² (C67) | 53.0 mm / 58.2 mm² |
| layers | forward and return on F.Cu side by side, In1.Cu GND only under x 24 … 32 (`rv bq51 xsec GND In1.Cu x 30 -46 -36`: 8.7 mm; `x 40`: none) | forward F.Cu, return In2 0.64 mm below, **In1 GND plane between them**. In2 return and F.Cu switch-node strip are 1.6 mm apart in plan view for 9.8 mm |
| loop inductance, partial-inductance model (`loops.py`: Manhattan strips, 7 filaments each, uniform current; FET packages as a 2.54 mm pin-to-pin segment on both boards; check: 20 × 3 mm rectangle of 1 mm strips = 21.9 nH) | **23.7 - 25.6 nH** (free space; DC+ band 2 or 5.6 mm wide, C70 or C67) | **20.0 nH** free space (plane transparent, i.e. around the fundamental). **9.2 nH** with In1 as a perfect thin plane (limit at the edge harmonics: the 15 µm plane has an eddy-current corner of roughly 0.1 - 1 MHz at mm scale) |
| ΔV = L · di/dt at the turn-off (2.4 - 2.7 A in about 10 ns, DAB_SIMULATION.md 2.1) | ≈ 6.5 V | ≈ 2.4 - 5.4 V |

**Verdict:** 5.2's DAB primary commutation loop is **equal to or better than 5.1** (area 0.75 - 0.84 ×, path 1.07 - 1.12 ×,
inductance 0.8 × free space, about 0.4 × with plane shielding). The checklist's 60 vs 9 mm² is right for 5.2 but wrong for
5.1. The draft verification's "better" claims (switch-node area, gate loops) are true but describe other things. Its
only commutation-loop row (13) said "same", which this measurement confirms (slightly better). The bridge is ZVS at
turn-on, so the turn-off overshoot of a few volts is negligible against the 600 V part. Confidence: medium-high. The
model ignores current crowding and the FET package loops, which are the same on both boards; the conclusion "not
worse" holds for any reasonable choice in the model.

## Checklist results
| Item | Verdict | Evidence |
|---|---|---|
| A1 | PASS | `rv bq net DC+`: tracks F.Cu / B.Cu only, vias F.Cu-B.Cu only, zone fill F.Cu only (no In-layer DC+). Branches (neck = `rv bq neck DC+ F.Cu …`, capacity by the project rule I = 3.25·w^0.725): **bulk → Q19.2**: 0.92 mm (pad entry; east from `S4B_DC+_F` and west from pour 29), C56 ↔ (20, −42) 6.42 mm; 2 × 3.06 A = 6.1 A for 1.63 A rms → 3.7×. **→ C47.1**: 3 vias (0.6/0.3 + 2 × 0.8/0.4 = 2.7 A) → B.Cu 2.0 / 2.5 mm (`neck DC+ B.Cu 18.3 -48.5 23.85 -70.9` = 2.00) → 3 × 0.8/0.4 (3 A) → C47.1; ≈ 1.2 A rms (half the transformer current) → 2.25×. **→ Q11.2 (heater)**: 0.92 mm neck at x 10 … 12, y −44 … −42 (`neck DC+ F.Cu 10 -44 20 -42` = 0.92, `5 -46 10 -44` = 2.08, `-13.838 -73.55 8 -46` = 2.16); 0.25 A dc → 12×; 5.1 2.60 mm. **→ TR1.11 (flyback)**: 0.50 mm (`neck DC+ F.Cu 61.316 11.222 20.4 -3.8`), 0.05 A dc → 40×. **SICD1.K → bulk**: 7.99 mm. **Peninsula (DB1.2, C73.1, SICD2.K) → trunk**: see A4, 3.3×. All ≥ 1.5 |
| A2 | PASS | DAB: P = 400 W, I1 = 2.31 A rms (DAB_SIMULATION.md 2.1, line 62). Per switch √(2.31²/2) = 1.63 A rms. Bus DC 412 W / 400 V = 1.03 A. With split capacitors the bus current is ≈ |i_T|/2 → 1.16 A rms, AC part √(1.16² − 1.03²) = 0.53 A at 280 kHz. Bulk path ≈ 0.2 Ω against 2.8 Ω (C67 + C70) and 1.1 Ω (C47 – C54 in series) → ≈ 80 % from bulk: **R83 / GND return ≈ √(1.03² + 0.42²) = 1.1 A rms**, not the 2.4 A quoted in the checklist (that is the transformer current); C67 / C70 and the In2 return ≤ 0.5 A rms. PFC: 540 W / 400 V = 1.35 A; each boost diode conducts in its own half line cycle, average i = 2.7·sin² → LF rms 2.7·√(3/16) = 1.17 A; HF total 2 - 3 A rms during conduction → ≈ 2.1 A over the line cycle. Heater 0.16 - 0.25 A dc, flyback 0.03 - 0.05 A dc (checklist values, not re-derived) |
| A3 | PASS (worse than 5.1, acceptable) | `rv bq neck DC+ F.Cu 12.75 -49.52 20.2 -17.2` = 0.92 mm; 5.1 `bq51 neck … 45.615 -41.949 …` = 2.05 mm (README: ≈ 2.3). Two entries of 0.92 mm over ≈ 1 mm length: R = 1.72e-8 · 1e-3 / (0.92e-3 · 35e-6) = 0.53 mΩ each, 0.27 mΩ in parallel; P = 1.63² · 0.27 mΩ = 0.7 mW; ΔT negligible (pad and pour on both sides). Capacity 2 × 3.06 A for 1.63 A → 3.7×. Partial inductance ≈ 0.5 - 1 nH, part of the 20 nH loop above. B.Cu entry not possible by README stage 8 (high-side group encloses the pad); the smallest improvement would be R22 to the west side (README stage 8), not needed |
| A4 | PASS (premise corrected) | F.Cu `neck DC+ F.Cu 11.8 -26.48 9.863 -14.0` = 1.34 mm (5.1: 3.14). `xsec DC+ F.Cu x 13 -25 12`: 1.48 mm (y −19.21 … −17.73) + B.Cu 1.0 mm track (y −19.15 … −18.15), **nothing else joins the peninsula to the trunk** (`x 13 10 19`: 0; `x 9 -30 19`: one piece). 5.1: 5.49 mm F.Cu at x = 13. So the neck is **not** only a C73 branch: it carries the whole LF current of the SICD2 boost diode (L1 / Q6 phase) and DB1's inrush to the bulk capacitors, plus the HF share that C73 (2.2 µF) does not take. Estimate √(1.17² + 1.3²) ≈ 1.75 A rms. Capacity F.Cu 1.25 mm → 3.8 A, plus B.Cu 1.0 mm limited by its 2 vias 0.8/0.4 at (10.2 / 11.3, −18.55) → 2 A; 5.8 A → 3.3× |
| A5 | PASS (with the exceptions listed) | PFC: R93.2 → C73.2 on B.Cu 6.34 mm (`neck GND B.Cu 3.8 -15.6 15.137 -14.0`), R21.2 → C73.2 B.Cu 1.55 mm; C73.2 has 15 vias 0.5/0.3 within 3 mm → outer-layer return ✓. DAB: R83.2 (F.Cu) is not joined to any bulk capacitor on F.Cu or B.Cu alone (`neck GND B.Cu 15.9 -64.525 25.2 -17.2` = 0). The return is 3 × 0.6/0.3 vias → In1 / In4 → THT pins of the bulk capacitors (2.1 A for 1.1 A, 1.9×). Heater: R30.2 sits in a B.Cu GND piece of 82.7 mm² whose nearest vias are 0.6/0.3 at (−6.2, −81.3), 4.1 mm away, and (−6.15, −74.83), 6.9 mm away (1.4 A for < 0.5 A). Flyback: R8.2 / R9.2 (F.Cu) and C15.1 (B.Cu) are joined only through planes, one 0.8/0.4 via at each end (1 A for 0.4 A). (c) README "DC+ and its GND return on F.Cu / B.Cu" is **true for DC+ and the PFC, not for the DAB, heater and flyback returns, nor for the GND pins of C56 / C37** (B.Cu contact 0, only 2 / 1 kept 0.152 mm spokes; In1 / In4 carry them). This is electrically fine: the return lies under the outer-layer DC+ pour |
| A6 | PASS | Contact length of pad outline in zone fill + track spokes per layer (script on the dumps): DC+ pins of C28 / C56 / C37 / C29 solid in F.Cu on both boards (5.8 / 5.8 / 5.8 / 9.2 mm of outline) plus 4 kept 0.152 mm spokes. GND pins 5.2: In1 and In4 thermal relief 2.6 mm of contact each (C29 2.5), B.Cu solid for C28 / C29, only spokes for C56 (2) / C37 (1). 5.1: In1 solid (4.8 mm), same B.Cu. 5.2 2 × 2.6 mm ≈ 5.1 1 × 4.8 mm; 0.5 oz relief 2.6 mm ≈ 1.95 A per layer by the rule → 3.9 A for 1 - 1.5 A ripple. `drc_summary.py starved_thermal`: only C102 pin 1 (ISO_GND, no current) |
| A7 | PASS | `xsec DC+ F.Cu y -40 -15 50` = 16.68 mm (B.Cu 0); `xsec GND In1.GND y -40 -45 60` = 71.3 mm, In4 71.3 mm, B.Cu 4.1 mm. The PFC returns close locally on B.Cu at C73. The DAB returns go through the planes to the bulk pins and share no narrow piece with the PFC. 5.1 (cut x = 28 between the capacitors and the 5.1 bridge): DC+ 6.99 mm, GND B.Cu 15.4 + In1 14.7 mm. 5.2 ≥ 5 mm |
| B1 | FAIL (note) – only the heater row; DAB primary PASS | Table "Commutation loops" below. Heater path 59.5 / 36.7 mm = 1.62 × (> 1.5 ×; area 1.12 ×) → F7. DAB primary: real copper 53.0 mm / 58.2 mm² against 47.3 - 49.6 mm / 69 - 78 mm² → PASS by the main criterion. The literal clause "closed only through the In2 track" is true (the parallel C47 – C54 route via B.Cu is ≈ 4× longer), but the inductance is ≤ 5.1's (20 vs 24 - 26 nH), so I do not apply the FAIL clause, which assumed a 6× larger loop; see F3 |
| B2 | PASS | 74.0 mm / 37.4 mm² (5.2) vs 112.4 mm / 157.1 mm² (5.1). Q8.3 is THT on the In1 / In4 ISO_GND planes (`neck ISO_GND F.Cu 66.335 -41.949 76.1 -61.237` = 0, B.Cu = 0); C55.2 has 3 × 0.8/0.4 vias within 3 mm; In1 ISO_GND under the 420V pour: `xsec ISO_GND In1.GND y -46 55 82` = 22.0 mm → plane-assisted return. But see F1 (switch-node via) |
| B3 | PASS | HEATER_CURRENT power return Q10.3 → F.Cu 0.8 mm → via 0.8/0.4 (−12.8, −68.6) → B.Cu 0.8 mm (`neck HEATER_CURRENT B.Cu -12.8 -68.6 -11.2 -80.4` = 0.80) → R30.1 / C20.2 area (B.Cu zone 5.4 mm², via (−17.8, −82.8)). The In2 0.2 mm 22.7 mm piece is the sense line to R106 / R158, not the power return. 0.8 mm → 2.75 A for < 1 A; soft-switched |
| B4 | PASS | 51.4 mm / 49.1 mm² and 50.5 mm / 60.7 mm² (5.2) vs 46.3 / 73.0 and 44.3 / 92.2 (5.1). Copper: Q5.3 → R93.1 B.Cu 4.37 mm, Q6.3 → R21.1 B.Cu 3.54 mm, R93.2 → C73.2 B.Cu 6.34 mm, R21.2 → C73.2 B.Cu 1.55 mm, C73.2 15 vias; DC+ SICD1.K → C73.1 1.34 mm (A4); **drain side PFC_DRAIN_1 Q5.2 → SICD1.A only 1.37 mm** (`xsec PFC_DRAIN_1 F.Cu x 9 -26 -18`: y −23.10 … −21.72; 5.1 `neck "Net-(L2-2)" …` = 4.55) → F5; PFC_DRAIN_2 Q6.2 → SICD2.A B.Cu 2.40 mm |
| C1 | PASS (notes Q10, Q8) | Pad-centre loops driver out → R → gate → source (→ shunt) → driver return, 5.2 / 5.1 (path mm / area mm²): Q5 47.8/95 – 49.1/104; Q6 47.8/5.9 – 42.5/6.9; **Q19 21.6/22 – 55.8/14**; Q7 32.7/9.2 – 33.7/53; Q21 42.1/56 – 39.9/7.6; Q8 45.5/85 – 22.1/28 (2.06 ×; DHB_LOW_GATE_SEC 17.2 mm on In3 directly over the In4 ISO_GND plane at 0.2 mm, `xsec ISO_GND In4.GND y -53.832 56 75` = 16.3 mm → plane-referenced); Q11 53.1/7.9 – 35.2/17 (1.5 ×); **Q10 64.4/81 – 28.9/10.5 (2.2 ×)**: HEATER_LOW_DRV runs 19.2 mm on In2 0.4 mm from DRV3.10 (−24.25, −59.3) to R37, directly under the In1 GND plane (`xsec GND In1.GND y -63.05 -25 -9` = 15.3 mm) → plane-referenced, LLC soft-switched → F8; Q1 20.7 – 16.1; Q2 34.3 – 26.7. Every 5.2 path ≤ 2 × 5.1, ≤ 30 mm, or plane-referenced |
| C2 | PASS (notes) | Driver GND pin ↔ shunt GND pad: DRV1.4 ↔ R93.2 ≈ 19 mm, DRV2.4 ↔ R21.2 ≈ 19 mm (same positions as 5.1); DRV5.9 (6.95, −54.35) ↔ R83.2 (15.9, −64.5) 13.6 mm (5.1 10.2); **DRV3.9 (−25.5, −59.3) ↔ R30.2 (−10.2, −80.4) 26 mm (5.1 DRV9.5 ↔ R30.2 12 mm)**. Plane path from R83 vias to DRV5.9 passes the Q7 pin-column antipad row through the 4 mm web y −57.1 … −53.1 (D1), no plane cut |
| C3 | PASS | `rv bq nets '*HI_SOURCE*'`, `'*HI_GATE*'`, `'Net-(DRV?-VDDA)'`, Net-(Q19-G), Net-(Q21-G), Net-(D30/D31-PadA), Net-(D35-K), HEATER_HI_DRV: F.Cu / B.Cu only |
| D1 | PASS | In1 / In4 GND one piece each (5537 mm² + 5 islands ≤ 3.1 mm²). Antipad rows: Q7 / Q19 pin column x 12.75: plane gaps y −64.49 … −57.11 (7.4 mm) and −53.11 … −45.93 (7.2 mm, two 0.44 mm webs) (`xsec GND In1.GND x 12.75 -66 -44`). Crossing it on In2: the 9-lane bus over the 1.48 mm web y −45.93 … −44.45 ($HT_CS −44.57, EPWM5A −44.87, EPWM6A −45.18), Net-(C63-Pad1) −53.75 / 5V −54.2 / Net-(C11-Pad1) −55.55 over the 4.0 mm web, DHB_CURRENT Kelvin −64.8 over the 0.71 mm web. J2: plane absent in a strip x 32.53 … 35.01 from y ≈ −22.7 to −1.6 (21 mm, `xsec GND In1.GND y -12 20 50`), but **no track crosses the J2 column** there (script: 0 crossings), the lanes end on the pins. No slot > 15 mm across a fast loop |
| D2 | PASS | Long In2 supply tracks: 5V. `rpath.py` (shortest-resistance path, 20 °C, 17.5 µm inner / 35 µm outer): D6.C → RL1.4 **571 mΩ** (5.1: 389 mΩ), → DRV3.3 279 mΩ, → DRV5.3 163 mΩ, → J2.2 8 mΩ (the control card is fed from the In3 5V pour, not over In2). Relay SRD-05VDC-SL-C (LCSC C35449 page, read 2026-11-23: 5 V, 70 Ω, 360 mW → 71.4 mA): drop 41 mV (≈ 47 mV with JLC's 15.2 µm inner copper) ≤ 50 mV; 0.15 mm 0.5 oz → 0.25 A → 3.5×. 15V on In2 0.4 - 1.27 mm (21 mm), < 0.1 A. DHB_CURRENT 1.2 mm: ≤ 0.5 A rms (A2) → 2.2×. No In2 track is the only return of a hard-switched loop **except** the DAB primary C67 / C70 return (B1 / F3) |
| D3 | FAIL (note) | Necks < 0.5 mm exist in the distribution: 5V In2 0.15 mm (23.7 mm, west branch to RL1 / D28) and 0.25 mm (29.6 mm); 15V B.Cu 0.1524 mm pieces at C52 (−9.36, −61.72) and the 0.3 / 0.4 mm feeds. Each carries its current with factor ≥ 3 (15V < 0.1 A: 0.15 mm 1 oz → 0.82 A). 5.1 had the same widths (5V B.Cu 0.1524 mm 41 mm on the relay path) → note F9. Drivers whose nearest ≥ 1 µF is > 5 mm: **DRV6.11 (15V_ISO_SEC, Q8 low-side supply) 13.2 mm to C43 (5.1: 7.3 mm), no smaller capacitor on that net nearer than 13.2 mm**; DRV4.1 7.2 mm (pins 6 / 8 2.2 - 3.4 mm); DRV3.14 / DRV6.14 5.2 / 5.3 mm; logic 5V pins of DRV3 / DRV5 / DRV6 (≥ 1 µF far, 100 nF local – checklists 02 / 06) |
| D4 | PASS (note) | Order of magnitude, microstrip L' ≈ µ0·h / w_eff: DC+ pour (5 mm) over In1, h 0.43 mm: 0.11 nH/mm (3313: 0.025). The DAB bulk return path is ≈ 40 mm → ≈ 4 nH instead of 1 nH, i.e. 7 mΩ at 280 kHz, irrelevant. Secondary loop Q8.3 → plane → C55.2 (≈ 22 mm, 1.6 mm strips): ≈ 3 nH instead of ≈ 1.7 nH. ZVS bridge, no verdict changes. No earlier stage conclusion depends on the 0.1 mm thickness: the DAB primary loop does not close through the plane, and the README "Stackup" says "not calculated" |
| D5 | PASS | Outer-layer copper 5.2 / 5.1 (mm²): PFC_DRAIN_1 144 / 185 + 166 on In1 (5.1 Net-(L2-2)); PFC_DRAIN_2 98 / 137 + 118 on In1 (Net-(L1-1)); DHB_HI_SOURCE 145 / 207; DHB_HI_SOURCE_SEC 107 / 82 + 249 on In2; HEATER_HI_SOURCE 221 / 284; FLY_C 200 (no 5.1 equivalent, PWM2 heatsinking); Q13 / Q14_DRAIN 355 / 232 (5.1 +190 / 163 per inner layer). All ≤ 2 × 5.1. Script: In2 / In3 tracks under each switch-node copper where the adjacent plane (In1 for F.Cu, In4 for B.Cu) is absent: **none** for all eight nets |
| E1 | FAIL (note) | Q13_DRAIN: F.Cu / B.Cu necks TR2.6 → Q2.3 7.10 mm and TR2.7 → Q2.3 4.89 mm per layer (5.1: 7.09 / 6.42 + In1 / In2 pours 190 mm²). Q14_DRAIN: TR2.10 → Q1.3 4.48 mm, TR2.9 → Q1.3 4.94 mm per layer (5.1: 7.68 / 7.68 + inner pours 163 mm²) → narrower than 5.1 (inner pours removed by decision 6, given). Capacity at the narrowest: (4.48 + 4.94) mm per layer = 16.8 A per layer, 33.6 A for both layers. At 12 A rms per FET (15 A output) ΔT ≈ 20 K · (12 / 33.6)^2.27 ≈ 2 K. Drain tab vias 12 × 0.5/0.3 at Q1 (5.1: 16) carry the B.Cu half (≈ 6 A) → 8.4 A by the rule, 1.4×. 6V3: `xsec 6V3 B.Cu x -60 -90 -60` 22.65 mm + In3 22.48 mm (5.1: B.Cu 22.85) ✓ |
| E2 | PASS | `neck 420V F.Cu 57.215 -41.949 86.898 -61.983` = 0.92 mm (Q21 drain pad entry; 5.1 2.30), Q21 drain ≈ 1.6 A rms → 3.06 A, 1.9×. B.Cu not joined (F.Cu pour) |
| E3 | PASS | F.Cu necks 5.2 / 5.1: L2_PRI2 CM1.4 → CM4.3 3.72 / 3.72 mm; L1_PRI2 11.19 / 13.02; IN2 terminal → CM1.3 2.50 / 2.34; Net-(RL1-COM) 3.29 mm. Pour areas equal to 5.1 (AC1 218 / 222, AC2 170 / 170, RES_IN 254 / 257) except Net-(RL1-COM) 215 / 317 mm² and the inner copper removed by decision 6 (L2_PRI2 In1 / In2 185 mm²). All ≥ 1.5 mm |
| E4 | FAIL (should fix, F1) | DC+ → C47 3 + 3 (2.7 / 3 A for 1.2 A) ✓; R83.2 3 × 0.6/0.3 (2.1 A for 1.1 A) ✓; C73.2 15 × 0.5/0.3 ✓; Q1 / Q2 tabs 12 / 16 × 0.5/0.3 (1.4× / 1.9× for the B.Cu half, E1) ✓; 6V3 / HT_GND: THT terminals and pins, current stays on the pours; PFC_DRAIN_2 F ↔ B through THT pads only. **DHB_HI_SOURCE_SEC: one 1.0/0.5 via (62.8, −49.2) in the power path Q8.2 → TR3.11 / 12 (2.22 A rms)** → F1 |
| E5 | PASS | Bulk capacitors see A6. TO-220 / TO-247 pins and terminals in the 5.2-made zones connect solid (neck results above are not limited to 0.15 mm). The kept 5.1 spokes (0.152 mm) on DC+ / GND bulk pins lie parallel to solid zone contact. Only starved thermal: C102 pin 1 (no current) |
| F1 | PASS | Tables below and the ranked list (findings F1 – F9) |
| F2 | PASS | Measurement list in "Could not verify" |

## Findings (ranked, most severe first)

### F1 DAB secondary switch node reaches Q8 drain through one via and 0.75 mm exits
- Severity: **should fix**
- What is wrong: the switch node DHB_HI_SOURCE_SEC (2.22 A rms, 140 kHz) from Q8.2 (68.875, −41.949) to the F.Cu trunk
  Q21.3 → TR3.11 / 12 runs B.Cu 0.75 mm (68.88, −41.95 … −44.4) → B.Cu 1.0 mm → **one via 1.0/0.5 at (62.8, −49.2)** →
  F.Cu 1.2 mm → trunk 1.6 mm. The F.Cu 420V pour lies between Q8.2 and the trunk. Q21.3 leaves on a 0.75 mm F.Cu
  piece (2.65 mm long). By the project rule (0.8/0.4 ≈ 1 A) the via gives ≈ 1.25 A against 2.22 A (0.56×), and 0.75 mm
  gives 2.65 A (1.2×). 5.1 had 4 vias 0.5/0.3 plus a 249 mm² In2 pour on this net. Physically the via dissipates only
  ≈ 4 mW (0.9 mΩ), so it will not burn. It is the weakest link of the secondary power path, worse than 5.1 and below
  the project's own via rule, and it sits in the secondary commutation loop.
- Evidence: `rv bq net DHB_HI_SOURCE_SEC` (vias at (62.8, −49.2) (60.25, −62.05) (57.85, −58.912); the latter two are the
  0.3 mm driver / C46 branch); `rv bq neck DHB_HI_SOURCE_SEC F.Cu 68.875 -41.949 69.5 -61.8` = 0 and `… B.Cu …` = 0
  (Q8.2 not joined to TR3 on one layer); `rv bq neck DHB_HI_SOURCE_SEC F.Cu 54.675 -41.949 69.5 -61.8` = 0.75 mm.
- Smallest fix: 2 - 3 more vias 0.8/0.4 beside (62.8, −49.2) on the B.Cu 1.0 mm track / F.Cu 1.2 mm track, and widen the
  B.Cu piece at Q8.2 and the F.Cu piece at Q21.3 to ≥ 1.0 mm where the 1.2 mm HV rule allows.
- Confidence: high on the geometry; medium that it matters in practice (no thermal or electrical failure expected).

### F2 DAB primary: the checklist's 60 vs 9 mm² comparison is an artefact; real loop equal or better than 5.1
- Severity: **note** (clears a suspected should-fix)
- What is wrong: see "DAB primary loop: the two figures explained". The 5.1 pad-centre polygon closes C67.1 → Q19.2 along
  the pin row, but the 5.1 copper returns 3.6 mm south (DC+ band) and the forward path runs 2.5 mm north (switch node
  at y −44.4). The draft verification's 207 → 144 mm² is switch-node copper area (re-measured 207 → 145 mm² outer).
- Evidence: `rv bq51 loop 45.615 -41.949 43.075 -41.949 34.335 -41.949 31.795 -41.949 28.337 -41.8 25.212 -41.8 25.5 -38.5 45.6 -38.5` → 47.3 mm / 69.1 mm²;
  `rv bq loop 12.75 -49.52 18.225 -48.0 21.175 -48.0 22.6 -49.0 22.6 -50.9 21.2 -52.3 17.4 -52.3 17.4 -62.14 15.5 -62.14 14.3 -63.34 12.75 -63.34 12.75 -60.8 15.8 -60.8 15.8 -52.06 12.75 -52.06` → 53.0 mm / 58.2 mm²;
  inductance model 23.7 - 25.6 nH (5.1) vs 20.0 nH (5.2, plane transparent) / 9.2 nH (perfect In1 plane).
- Smallest fix: none needed. Correct the checklist / README text if it is reused.
- Confidence: medium-high. A bench measurement of the Q7 / Q19 VDS ringing would confirm it (F2 list).

### F3 DAB primary HF return relies on one In2 track (0.5 oz) and two vias
- Severity: **note**
- What is wrong: C67 / C70 return to Q7 source only over the 1.2 mm × 22.7 mm In2 track of DHB_CURRENT (vias (22.6, −49 / −50)).
  The net is in class SIGNAL, although it carries power current. The current is small (≤ 0.5 A rms, A2; 1.12 A
  capacity) and the inductance is not worse than 5.1 (F2), so this is no fault, only the one place where a switching
  loop uses an inner signal layer.
- Evidence: `rv bq net DHB_CURRENT` (In2 w 1.2 mm 22.67 mm); `rv bq neck DHB_CURRENT F.Cu 21.175 -48.0 12.75 -63.34` = 0, B.Cu = 0.
- Smallest fix: none required. If wanted, the checklist's 100 nF 630 V 1210 DC+ – DHB_CURRENT next to Q7.3 / Q19.2 on
  B.Cu would shorten the edge loop further (room not checked).
- Confidence: high.

### F4 PFC peninsula (DB1, C73, SICD2 cathode) joined to the DC+ trunk only by the SICD1 neck
- Severity: **note**
- What is wrong: the SICD1 neck (F.Cu 1.25 - 1.48 mm + B.Cu 1.0 mm with 2 vias) is in series with the whole SICD2 diode
  current to the bulk capacitors and DB1's inrush, not only with C73's HF share (checklist premise). 5.1: 5.49 mm.
- Evidence: `rv bq xsec DC+ F.Cu x 13.0 -25 12` / `… B.Cu …`, `x 13 10 19` = 0; `neck DC+ F.Cu 3.09 1.26 20.4 -3.8` = 1.25.
- Smallest fix: none needed (3.3× margin on ≈ 1.75 A rms). The README stage 4k / 4l options (cut pour 30 further, or
  SICD1 0.6 mm south) remain if more margin is wanted.
- Confidence: medium (current split between C73 and the bulk is estimated).

### F5 PFC_DRAIN_1 lobe to the SICD1 anode only 1.37 mm (5.1: 4.55 mm)
- Severity: **note** (not in the checklist's known list)
- What is wrong: the drain pour of Q5 reaches SICD1.A through a lobe 1.37 mm wide over ≈ 2.6 mm (x 8.2 … 10.8, y −23.10 … −21.72).
  This piece carries the boost-diode current (≈ 2.1 A rms, 10 A peak) inside the PFC leg-1 commutation loop.
- Evidence: `rv bq neck PFC_DRAIN_1 F.Cu 3.752 -24.115 11.8 -21.4` = 1.37 mm; `xsec PFC_DRAIN_1 F.Cu x 9 -26 -18` = 1.376; 5.1 `neck "Net-(L2-2)" F.Cu 3.752 -24.115 11.5 -26.73` = 4.55.
  4.2 A by the rule → 1.4 - 2.0×; R ≈ 0.9 mΩ → < 10 mW; ≈ 2.5 nH → ≈ 1.3 V at 10 A / 20 ns.
- Smallest fix: none needed; widen the lobe if the anode pocket allows when the area is next touched.
- Confidence: high on geometry.

### F6 Narrower DC+ entries than 5.1: Q19 drain 0.92 + 0.92 mm (5.1 2.05 - 2.3), heater branch 0.92 mm (5.1 2.6)
- Severity: **note** (known weak point confirmed, acceptable)
- Evidence: A1 / A3 (3.7× and 12× margin). The heater branch passes the 0.92 mm neck at x 10 … 12, y −44 … −42 between
  the H4 keep-out and the Q19 gate pad.
- Smallest fix: none. Thermal-camera check at 400 W (F2 list).
- Confidence: high.

### F7 Heater bridge loop path 1.6 × 5.1
- Severity: **note**
- What is wrong: pad-centre path 59.5 mm vs 36.7 mm (area 23.0 vs 20.6 mm²), the result of the DPAK parts and the
  0.8 mm return over a via pair. LLC, soft-switched, < 1 A.
- Evidence: `rv bq loop Q11.2 Q11.3 Q10.2 Q10.3 C20.2 C20.1` / `bq51`; B3.
- Smallest fix: none.
- Confidence: high.

### F8 Gate loops of Q10 (2.2 ×) and Q8 (2.06 ×) longer than 5.1, both plane-referenced; DRV6 VDDB 13 mm from its capacitor
- Severity: **note** (owners 06 / 02)
- Evidence: C1, C2, D3. Q10: DRV3.10 → In2 0.4 mm 19.2 mm → R37 under the solid In1 GND plane; DRV3.9 ↔ R30.2 26 mm
  (5.1 12 mm). Q8: In3 17.2 mm over the In4 ISO_GND plane. DRV6.11 nearest ≥ 1 µF (C43) 13.2 mm (5.1 7.3 mm).
- Smallest fix: none for the loops; for DRV6.11 a 1 µF 0603 at pins 11 / 9 (checklist 02 to judge).
- Confidence: medium.

### F9 Supply necks < 0.5 mm in 5V / 15V (as in 5.1); 5V to the relay 571 mΩ
- Severity: **note**
- Evidence: D2 / D3. 41 - 47 mV drop at 71.4 mA; capacity ≥ 3×.
- Smallest fix: none.
- Confidence: high.

## Compared with 5.1

**Commutation loops** (pad-centre `rv bq loop` unless marked "copper"):

| Loop | 5.1 path / area | 5.2 path / area | forward / return same layer? plane under it? | verdict |
|---|---|---|---|---|
| PFC leg 1 (Q5 – SICD1 – C73 – R93) | 46.3 mm / 73.0 mm² | 51.4 mm / 49.1 mm² | DC+ / drain F.Cu, return B.Cu → 15 vias at C73.2; In1 / In4 between | equal (1.11 ×, 0.67 ×); drain lobe 1.37 mm (F5) |
| PFC leg 2 (Q6 – SICD2 – C73 – R21) | 44.3 / 92.2 | 50.5 / 60.7 | drain B.Cu 2.4 mm, DC+ F.Cu, return B.Cu 1.55 mm | equal (1.14 ×, 0.66 ×) |
| DAB primary (Q19 – Q7 – C67 / C70) | **copper 47.3 - 49.6 / 69 - 78** (pad-centre 41.3 / 9.4 is not the copper) | **copper 53.0 / 58.2** (pad-centre 40.0 / 60.5) | 5.1 all F.Cu side by side; 5.2 F.Cu forward, In2 return with In1 between | **equal / better**: 24 - 26 nH vs 20 nH (9 nH with plane) |
| DAB secondary (Q21 – Q8 – C55 / C16) | 112.4 / 157.1 | 74.0 / 37.4 | 420V F.Cu over In1 ISO_GND; return via plane | better; but one via in the switch node (F1) |
| Heater bridge (Q11 – Q10 – C20) | 36.7 / 20.6 | 59.5 / 23.0 | F.Cu pour forward, 0.8 mm F/B return | path 1.6 × (F7), soft-switched |
| Flyback primary (C15 – TR1.11 – TR1.12 – PWM2 – R8 – GND) | different converter (EF20 / IW1818), no like-for-like loop | 47.2 / 9.2 | return through planes, 1 via 0.8/0.4 at R8 / R9 and at C15 | 0.4 A rms, adequate |

**Paths: current, narrowest cross-section, capacity by the project rule:**

| Path | current | 5.1 | 5.2 | capacity 5.2 | margin |
|---|---|---|---|---|---|
| bulk → Q19 drain | 1.63 A rms | 2.05 mm F | 0.92 + 0.92 mm F (pad entries) | 6.1 A | 3.7 × |
| DC+ → C47.1 | ≈ 1.2 A rms | pour | B.Cu 2.0 mm, 3 + 3 vias | 2.7 A (vias) | 2.25 × |
| peninsula ↔ trunk (SICD1 neck) | ≈ 1.75 A rms | 5.49 mm F | 1.25 - 1.48 F + 1.0 B (2 vias) | 5.8 A | 3.3 × |
| Q5 drain → SICD1.A | ≈ 2.1 A rms | 4.55 mm | 1.37 mm | 4.2 A | 2.0 × |
| Q6 drain → SICD2.A | ≈ 2.1 A rms | – | 2.40 mm B | 6.4 A | 3 × |
| DC+ → heater bridge | 0.25 A dc | 2.60 mm | 0.92 mm | 3.06 A | 12 × |
| DC+ → flyback | 0.05 A | – | 0.50 mm | 1.97 A | 40 × |
| C67 / C70 return (DHB_CURRENT In2) | ≤ 0.5 A rms | F.Cu pour | 1.2 mm 0.5 oz, 2 vias 0.8/0.4 | 1.12 A | ≥ 2.2 × |
| R83 → planes (DAB return) | ≈ 1.1 A rms | B.Cu pour, 0 vias | 3 × 0.6/0.3 | 2.1 A | 1.9 × |
| Q7.2 / Q19.3 switch node → TR3 | 1.63 / 2.31 A rms | 2.02 mm | 0.92 mm (pad entry) / 4.47 mm | 3.06 / 9.6 A | 1.9 / 4 × |
| **Q8.2 → secondary switch node** | 2.22 A rms | 4 vias + In2 pour | **1 via 1.0/0.5, 0.75 mm** | ≈ 1.25 A | **0.56 ×** (F1) |
| Q21 drain (420V) | ≈ 1.6 A rms | 2.30 mm | 0.92 mm (pad entry) | 3.06 A | 1.9 × |
| TR2 → Q1 drain (Q14_DRAIN) | 12 A rms | 2 × (7.68 + 7.68) + inner pours | 2 × (4.48 + 4.94) | 33.6 A | 2.8 × (ΔT ≈ 2 K) |
| TR2 → Q2 drain (Q13_DRAIN) | 12 A rms | 2 × (7.09 + 6.42) + inner | 2 × (7.10 + 4.89) | 39 A | 3.3 × |
| 6V3 at x = −60 | 15 A | 22.85 mm B | 22.65 B + 22.48 In3 | – | ≥ 5.1 |
| 5V D6 → RL1 | 71.4 mA | 389 mΩ | 571 mΩ | – | 41 mV drop |
| mains L2_PRI2 / IN2 | 2.5 A rms | 3.72 / 2.34 mm | 3.72 / 2.50 mm | 8.9 / 6.6 A | 3.6 / 2.6 × |

**Where 5.2 is worse than 5.1, ranked, with the smallest fix:** (1) secondary switch-node via / 0.75 mm exits (F1:
add 2 - 3 vias, widen to ≥ 1 mm); (2) PFC_DRAIN_1 lobe 1.37 vs 4.55 mm (F5: none needed); (3) SICD1 neck 2.25 - 2.5 vs
5.5 mm (F4: none needed / README 4k options); (4) Q19 drain entry and heater DC+ neck 0.92 mm vs 2.05 - 2.6 mm (F6:
none); (5) Q14_DRAIN narrower, 12 vs 16 tab vias (E1: none); (6) Q10 / Q8 gate loops, DRV6.11 bypass (F8: 1 µF at
DRV6 pins 11 / 9, checklist 02); (7) 5V relay path 571 vs 389 mΩ (F9: none). **Better than 5.1:** DAB primary gate
loops (Q19 21.6 vs 55.8 mm, Q7 area 9 vs 53 mm²), DAB primary commutation loop (F2), DAB secondary loop (37 vs
157 mm²), PFC loop areas, switch-node copper areas (D5), no switch node on an inner layer.

## Could not verify
- **Real loop inductances / overshoot**: only estimated (partial-inductance model, In1 either transparent or perfect).
  On the first board, measure: VDS of Q7 / Q19 (and Q8 / Q21) at turn-off at 400 W with a short-ground probe,
  overshoot expected < 10 V; VDS of Q5 / Q6 at turn-off at full PFC load.
- **Current split** between C67 / C70, C47 – C54 and the bulk capacitors (sets the In2 and R83 currents in A2). This
  needs a simulation with layout parasitics, or a current probe on R83 (whose voltage is already measured).
- **Temperatures**: thermal camera at 400 W DAB + full PFC on the Q19 drain entry, the SICD1 neck, the PFC_DRAIN_1 lobe
  at SICD1.A, the via (62.8, −49.2) of DHB_HI_SOURCE_SEC, and the Q1 / Q2 drain tabs at 12 - 15 A heater current.
- The 5.1 inner-copper thickness / stackup (for A6 and for the 5.1 plane under the DAB loop) is not in the repository;
  5.1 is treated as free space in the loop model.
- The flyback loop has no like-for-like 5.1 counterpart (different IC and transformer).
- The "207 → 144 mm²" figure is not in `kicad_next/README.md` as the brief says. I found it in the draft verification's
  scratch report (`verify/report_t4.md`, row 16, outside the repository) and reproduced it from the board.
- The IPC-2152 fit of the project's current rule was not re-checked against a fetched source. All margins use the
  project rule as given.

## Outside scope
- **02 (DAB gate drive)**: DRV6 pin 11 (15V_ISO_SEC, Q8 gate supply) has no capacitor within 13.2 mm (5.1: 7.3 mm). In the
  D30 / R53 / R41 area, D30.A ↔ R41.1 is 0.255 mm (same floating group). The floating group is 1.257 mm from the
  +1V65_BIAS via (rule 1.2 mm). Legal, at the limit.
- **06 (heater)**: DRV3 low-side output 14 mm from R37 over In2; DRV3 GND pin 26 mm from the shunt R30 GND (5.1 DRV9: 12 mm).
- **07 / 10**: DHB_CURRENT carries the bridge's HF return but is in net class SIGNAL. Its clearance to the HV nets is
  therefore governed by the SIGNAL class; checklist 10 to confirm that this is intended.
- **10**: the J2 pin column leaves a 2.5 × 21 mm strip without In1 / In4 plane (x 32.5 … 35.0, y −22.7 … −1.6). This
  is not a loop problem.
