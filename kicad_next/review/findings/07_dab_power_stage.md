# Findings: 07 DAB power stage  (reviewer: Claude Opus 5.5, 2026-11-23, commit 01a1adf)

## Summary
The DAB power stage can be ordered: I found no blockers. Schematic, TR3 pin assignment, split-capacitor and
balancing networks, transformer electrical design (flux, loss, magnetising current) and the TR3 PRI–SEC barrier
are all consistent and match 5.1 or do better.
Four things should be fixed, all small:
(1) The HF commutation loop of the primary bridge (C67 / C70 → Q7 source) returns through a 22.7 mm, 1.2 mm
    **In2** track. That breaks the "power on outer layers" decision and gives a longer loop than 5.1.
(2) The Q8 drain reaches the secondary switch node through **one** 1.0 / 0.5 via (1.57 A rms against about 1.2 A by
    the project's via scale).
(3) Builder-facing documents still give the old TR3 **gap 0.35 mm** (parts CSV, `fab/NOT_ASSEMBLED.md`, plan D1).
(4) The owner's ringing question. An RC snubber across TR3 is not worth it: the 5.1 ringing came mainly from L3's
    winding capacitance, as the design document says, and L3 is gone. I do recommend a cheap **DNP C / RC footprint
    at the switch node(s)** before ordering (F2).
Datasheet facts that could not be fetched: the DC-bias and ripple data of the split capacitors, the ripple current of
C19 / C30, and the EC42 core data.

## Checklist results
| Item | Verdict | Evidence |
|---|---|---|
| A1 | PASS | `rv sch sheet 7`: TR3 4/5 = DHB_CAP, 7/8 = DHB_HI_SOURCE, 9/10 = TRANS_SEC, 11/12 = DHB_HI_SOURCE_SEC. Q19 D = DC+ / S = DHB_HI_SOURCE; Q7 D = DHB_HI_SOURCE / S = DHB_CURRENT; Q21 D = 420V; Q8 S = ISO_GND. `rv sch net '*TRANS_PRI*'` → "no net matches". `rv sch cmp51 7`: only R143–R150 added, L3 removed, C19/C30 39u→68u, 100 nF 1206→1210, TR3 value / footprint / pins. All of these are documented in CHANGES 2.1–2.8 and 5.2b / 5.6. |
| A2 | CANNOT VERIFY | In 5.2 the dots are on the starts 4+5 / 9+10 (CHANGES "Transformer pins and winding tables"; DAB_TRANSFORMER.md 5; symbol desc in `tools/next/gen_symbols.py:183`). In 5.1 the TR3 P1 = TRANS_PRI (cap side through L3), P2 = DHB_HI_SOURCE, S1 = TRANS_SEC, S2 = DHB_HI_SOURCE_SEC (`rv sch51 ref TR3,L3`). This is the same cap-side/node-side assignment as 5.2, but the 5.1 symbol `ETD34_TRAN_1P1S` (lib/tube_psu.kicad_sym) carries no dots and the 5.1 winding sense is not documented. So "in phase at φ = 0" cannot be checked against 5.1. Fallback written down: DAB_TRANSFORMER.md 5, "If power flows the wrong way … swap one winding's ends, or change the phase sign in the FPGA". The switch nodes sit on the outer layers (finishes) with the quiet ends next to the core (DAB_TRANSFORMER.md 5 table). With side-by-side chambers this changes no interwinding term, so there is no EMI consequence stated or found. |
| A3 | PASS | DAB_SIMULATION.md 2.1: 400 W fwd φ +23.8°, I1 2.31 / I2 2.22 A rms; rev −23.2°, 2.28 / 2.13 A. ZVS (2.4, Lm 200 µH, 150 ns): matched 420 V ZVS over the whole light-load range; +5 % (441 V) no hard switching; −5 % (399 V) small window +30…+109 W, ≤ 6.2 µJ. At 400 W, ±5 % gives ZVS on all switches (2.3). The design doc used 26 : 29 with L3 (`rv pdf 25`). |
| A4 | PASS | Half-bridge DAB, P = (V1/2)(V2′/2)·φ(π−φ)/(2π² f L), V1/2 = 200 V, V2′/2 = 420·20/21/2 = 200 V, f 140 kHz, L 41 µH, so the denominator is 113.3. φ = 24° (0.419 rad) → **403 W**; Pmax (φ = 90°) → **871 W**. At +30 % L (53.3 µH): Pmax 670 W, 400 W at **φ = 32.9°** (≤ 45°). 5.1 (70 + 4.6 µH, DAB_TRANSFORMER.md 3.4): Pmax ≈ 480 W, so 5.2 ≥ 5.1. 3 A peak at 420 V (1.26 kW) is above Pmax: peaks come from C19 / C30, as in 5.1. Low-leakage sample (25 µH): 400 W at φ ≈ 13.6°, about 30 W/°. Mitigation per DAB_TRANSFORMER.md 6 step 2: re-turn, or windings to the flanges (+18–21 %). The "residual L3" option there no longer exists (no footprint, CHANGES 2.4); see F11. |
| A5 | CANNOT VERIFY | Same part as 5.1 (C784102 FS55X105K631EHG in both, `rv sch51 ref C47,C16` / `rv sch part C47`). The PSA FS-series approval sheet (2017-09-15, from the LCSC/JLC C784102 datasheet link) has **no DC-bias curve, ESR or ripple-current data**. It notes an internal series-unit construction. My estimates: at 1 µF nominal the sim gives 4.8 / 5.1 V pp (2.1). At a pessimistic 0.4 µF under 200 V bias, about 12 V pp, which is still ≤ 20 V (10 % of half-rail). Peak ≈ 210 + 6 V ≤ 500 V. 2C_eff (0.8–2 µF) with Lsc 41 µH resonates at 18–28 kHz and with Lm at the ≈ 4.5 kHz mode the sim found (Q ≈ 10, model section 1). Both are far below 140 kHz; the balancing resistors and firmware centring handle the start-up offset. Ripple 1.2 A rms per capacitor: the rating is not in the datasheet. |
| A6 | PASS | `rv sch sheet 7`: R143 DC+→Net-(R143-Pad2)→R144→DHB_CAP; R145 DHB_CAP→R146→DHB_CURRENT; R150 420V→R149→TRANS_SEC (across C16); R148 TRANS_SEC→R147→ISO_GND (across C55); R147.1 = ISO_GND, R150.2 = 420V. One 440 k chain per capacitor. 105 V and **50 mW** per resistor (105²/220 k; the checklist's "≤ 25 mW" is wrong, CHANGES 2.8 says ≤ 50 mW), against 200 V / 0.25 W for the 1206W4F2203T5E (C17956). The lower primary chain ends on DHB_CURRENT (0.45 mA × 4 mΩ = 2 µV, negligible); the secondary ends on ISO_GND. τ = (440 k ‖ 440 k) × 2 µF = 0.44 s, so the 2 s wait is 4.5 τ. |
| A7 | PASS | STF7N60M2, DocID024894 Rev 1 (June 2013, copy at static.chipdip.ru/lib/210/DOC005210689.pdf; st.com refuses scripted download). VDS 600 V, ID 5 A (25 °C) / 3.5 A (100 °C), IDM 20 A, RDS(on) 0.86 / 0.95 Ω, Coss eq. 75.5 pF, Rthj-case 6.25 K/W (Tables 2, 3, 5, 6). The Table 8 Qrr is printed as "1.55 nC"; this is a typo for µC (275 ns × 11 A / 2). Per switch I_rms = 2.31/√2 = 1.63 A. With RDS(on) about 1.5 Ω at 100 °C: **4.0 W** (the sim uses 1.3 Ω, 3.4 W); ΔTjc 25 K. 5.1 ran 2.60 A rms (DAB_TRANSFORMER 3.4), so 5.2 is lower. VDS 400 + overshoot (C2: < 50 V even for a hard-switched edge) < 480 V. Light-load hard switching (35–42 µJ, 5–6 W/switch) is avoided by DC+ tracking / burst (DAB_SIMULATION 3) and is reduced by Lm 200 µH. Same devices as 5.1. See F6 for the dv/dt ratings. |
| A8 | CANNOT VERIFY | Ymin KCX page (ymin.cn KCX product page): KCXE5002W680MF = 450 V, 68 µF, D10 × 50, −40…105 °C, 3000 h, tanδ 0.18. Ripple multipliers 0.5 at 120 Hz and 1.0 at 100 kHz, but **no ripple-current value** is published (the LCSC PDF C913388 is image-only). Voltage: 450 ≥ 420 × 1.05 = 441 V, PASS (thin margin, F12). Capacitance 2 × 68 > 2 × 39 µF (5.1). Ripple current: not verifiable. |
| A9 | PASS | C67 / C70 1=DC+, 2=DHB_CURRENT in 5.2 and 5.1 (`rv sch sheet 7`, `rv bq51 fp C67,C70`). The HF loop excludes R83 as in 5.1. Layout: C2. |
| A10 | PASS | All firmware conditions are in one table row, `NEXT_REVISION.md:45` (NR 2.7): 150 ns total dead time, not ≥ 250; DC+ tracks V420·20/21 or burst < 150 W; soft start 420 → 140 kHz; enable ≥ 2 s after centring; φ(0 W) ≈ −0.8°; DHB_I average. DAB_DIS default: `NEXT_REVISION.md:54` (NR 3.3). |
| B1 | FAIL | Correct: DAB_TRANSFORMER.md 5 (20 : 21, litz 135 × 0.071 / TIW secondary, pins 4+5 / 7+8 / 9+10 / 11+12, gap ≈ 0.66–0.68 mm or 0.335 mm spacer, Lm 170–210 µH by measurement); CHANGES 2.1 gap; sheet note `tools/next/sheets/sheet07.py:195`; NEXT_REVISION.md:39. **Stale "gap 0.35 mm"** (no "spacer under all legs") in `lib/jlc_parts_next.csv` TR3 note, in **`kicad_next/fab/NOT_ASSEMBLED.md:20`** (the builder's list, generated from the CSV) and in `NEXT_REVISION_PLAN.md:31` (D1, "gap 0.35 mm / Lm ≈ 300 µH"). See F3. |
| B2 | PASS | B_pk = 200 V / (4 · 140 kHz · 20 · 187 mm²) = **0.096 T**. Ae is from the seller dimensions in DAB_TRANSFORMER.md 2; no vendor EC42/15 datasheet exists for this core. TDK PC40 (TDK/Dexter "Ferrites for switching power supplies" summary, material table): Pcv 410 kW/m³ at 100 kHz / 200 mT / 100 °C; Bs 390 mT at 100 °C. Steinmetz (α 1.3, β 2.6) to 140 kHz / 96 mT gives ≈ 95 kW/m³ sine, ≈ 85 kW/m³ for square volts, × 18.47 cm³ = **≈ 1.6 W** (project: 1.50 W iGSE). Copper 0.73 W, so the total is ≈ 2.3 W ≤ 4 W. Document's ΔT ≈ 17 K, against 25 K measured on 5.1 (`rv pdf 33`). The design doc's 1 W rule (p 25) is exceeded by 0.5 W, but the total is lower than the 5.1 ETD34 + L3 estimate of 6.7 W. |
| B3 | PASS | No DC flux (split capacitors on both sides). ΔI_m = 200 V · 3.57 µs / 200 µH = 3.57 A pp → ±1.79 A at no load. Sim 1.48 A peak at 400 W (2.4); flux is set by volt-seconds (0.096 T, independent of Lm). The 20 V start-up imbalance gives 0.16 T (2.8), against Bs 390 mT, so the margin is ≥ 2.4×. Equivalent net magnetising current to Bs ≈ 7 A, against 1.8 A. The load ampere-turns cancel. 5.1: 0.7 A peak (p 25). The extra conduction loss is in the sim (+0.5 W at 400 W for 200 µH, 2.4) and in A7. |
| B4 | CANNOT VERIFY | `rv bq fp TR3`: 8 pads, drill 1.2, 5.0 mm pitch, rows 40 mm. README:2073–2076 "Still to confirm with calipers: EC42 set: pin diameter (drill 1.2), base 46 × 40, core depth, seated height, core-plate height above the board at the secondary pins". **No measurement recorded.** Cut-pin instruction: DAB_TRANSFORMER.md 5 ("cut the other pins (primary row 1, 2, 3, 6; secondary row 13 – 16)"), CHANGES "the other pins cut", footprint F.Fab "clip" texts. It is not in `fab/NOT_ASSEMBLED.md`. Measure before ordering: pin diameter / position tolerance (vs 1.2 mm drill), row spacing 40 mm, base outline, seated height, core-plate height above the board at pins 9–12. |
| B5 | PASS | `rv bq padgap TR3.8 TR3.9` 37.6 mm. Every copper item in the box x 42.5…54.5, y −91.35…−47.7 on all layers: only GND In1 / In4 reaching x 42.9 near y −90.9. `rv bq dist GND ISO_GND --layer In1.GND` 11.600 mm, In4 11.611 mm (≥ 11.1). `xsec` y −70: GND In1 ends 42.5, ISO_GND starts 54.5. `rv bq near @SEC --within 11.1 --other-domain`: nearest is DC+ F.Cu 6.93 mm at (46.8, −41.3) vs Q21.3, separated by the L-slot (`rv bq slots`), the other entries are at the TR1 / ISO2 slots (checklist 10). Core-to-secondary insulation is specified: DAB_TRANSFORMER.md 8 item 2 (3 tape layers on the secondary core plate or a cap) and TIW secondary. |
| B6 | CANNOT VERIFY | Under the body: primary switch-node / DHB_CAP zones and secondary TRANS_SEC zone, DHB_HI_SOURCE_SEC 1.6 mm track (x 55.45…69.5). The bobbin stand-off / core-plate height above the board is not measured (README:2075–2076). Tape on the secondary core plate is specified (DAB_TRANSFORMER.md 8 item 2), which covers the core ↔ secondary-pin path, but not the board copper ↔ core bottom distance. |
| C1 | PASS | `rv bq neck DC+ F.Cu 12.75 -49.52 20.2 -17.2` = 0.92 mm, to C67.1 0.92 mm; README Stage 8 table: 0.9 + 0.9 mm. 5.1 `rv bq51 neck … ` 2.05 mm. `padgap Q19.2 Q19.3` 0.635 mm. Rule 3.25·0.92^0.725 = 3.06 A per neck, 6.1 A for both, against 1.63 A rms: factor 3.7. R = 1.72e-8 · 1.5 mm / (0.92 mm · 35 µm) = 0.80 mΩ (≈ 1.05 mΩ hot) per neck, 0.52 mΩ for both; P = 1.63² · 0.52 mΩ = **1.4 mW**. Added inductance of two 1.5 mm necks, about 1 nH: negligible against the loop (C2). Narrower than 5.1 but within the rule; note only. |
| C2 | FAIL | Return C67/C70.2 → Q7.3: `rv bq neck DHB_CURRENT F.Cu 12.75 -63.34 21.175 -48.0` = **0 (not joined on F.Cu)**. Path (track dump): C67.2 → B.Cu 0.8 mm → vias 0.8/0.4 (22.6, −49 / −50) → **In2 1.2 mm** (22.6,−50.9)→(21.2,−52.3)→(17.4,−52.3)→(17.4,−62.14)→(15.5,−62.14)→(14.3,−63.34)→Q7.3, **22.7 mm on a 0.5 oz signal layer**. `rv bq loop` (C67 path): **46.6 mm, 84 mm²** across F.Cu / In2. The parallel split-cap path (C47 + C54, outer layers only): 69.4 mm, 125 mm². 5.1 (`rv bq51 loop Q19.2 C67.1 C67.2 Q7.3 Q7.2 Q19.3`): 41.3 mm, 9.4 mm² plan view, all F.Cu. Estimate (rectangle-loop formula): about 16 nH (5.2) vs about 8–12 nH (5.1), so ≤ 2× but worse. Overshoot: ZVS edge 2.7 A / 10 ns → about 4 V; hard-switched edge with 11–30 A recovery at 1–3 A/ns → 16–48 V, so VDS < 480 V. The FAIL is on the criterion "the HF loop does not run through an inner layer over more than a via" (README Stage 9 decision: DC+ and its GND return on outer layers). See F1. |
| C3 | PASS | Zone 120.6 mm² F.Cu (`rv bq net DHB_HI_SOURCE`). 5.1: 164.3 mm² (`rv bq51 net`), so 5.2 is smaller. Neck from Q19.3: 4.47 mm. From Q7.2: pad entry 1.08 mm (x 13.9), strip 1.65 mm at y −59 (x 14.95…16.6), ≥ 2.7 mm from x 15. Rule: 1.08 mm → 3.4 A, against 1.63 A rms for Q7. The only < 1.2 mm neighbours on F.Cu are pad pairs and the DRV5 group (0.2 mm rule). The "≥ 2 mm everywhere" target is missed only at the pad entry; I take that as within the current rule. |
| C4 | PASS | DHB_CAP zone 57.1 mm². `neck C47.2→TR3.4` 1.19 mm: the zones use `connect_pads thru_hole_only`, so the SMD pads of C47 / C54 have 1.2 mm thermal spokes (TR3 pads solid). Fine for 1.2 A per capacitor (3.7 A per spoke); note only. DC+ to C47: `neck DC+ B.Cu 18.225 -48 23.85 -70.9` 2.00 mm. Vias north: 2 × 0.8/0.4 + 1 × 0.6/0.3 = 2.7 A. South: 3 × 0.8/0.4 = 3 A, against 1.2 A rms, so ≥ 2×. Spacing 1.25 mm by construction (README Stage 7b). The B.Cu DC+ run crosses under the F.Cu switch-node zone with the In1 / In4 GND planes between them; capacitive coupling only, note. |
| C5 | PASS | R83 GND: 3 × 0.6/0.3 vias on a 1.0 mm F.Cu bar (README Stage 7). Per DAB_SIMULATION 2.6, R83 carries **only the bridge input current**, not the winding current: 1.03 A DC + 2.6 A pp at 280 kHz, so ≈ 1.27 A rms. Via capacity 3 × 0.7 = 2.1 A, against 1.5 × 1.27 = 1.9 A: passes, marginally. Q7.3 → C54.2 `neck` 0.78 mm, 2.7 A by the rule, against 1.2 A rms × 1.5 = 1.8 A. |
| C6 | PASS | `rv bq near DHB_HI_SOURCE --within 1.3`: outer non-pad-pair gaps all ≥ 1.2 mm except the DRV5 high-side group (Net-(Q19-G) 0.373 mm, DHB_HI_GATE 0.667 mm on B.Cu, both allowed by the 0.2 mm group rule). Inner 0.5 mm spots (hole wall to plane / pour): DHB_HI_SOURCE ↔ In1 GND (29.96, −57.91) and In4 GND (29.04, −55.69) at TR3 7/8; ↔ In3 15V (13.06, −52.52) at Q19.3. DC+ (Q19.2 barrel) ↔ In1 GND (12.96, −50.03) and ↔ In3 15V (13.06, −49.98). 0.5 mm of FR-4 meets the README basis "inner 0.5 mm" and is ≥ IPC-2221 B1 (0.25 mm, 301–500 V). 5.1 (`rv bq51 near DHB_HI_SOURCE --within 0.8`): In1 / In2 rings 0.635 mm and outer 0.45 mm, so 5.2 is equal or better. Cross-footprint pad pair Q7.2 ↔ R70.2 (GND) **0.883 mm on B.Cu** passes the DRC only through the pad-pair exemption (F5). |
| D1 | PASS | `neck 420V F.Cu Q21.2→C16.1` 0.92 mm (pad entry); `neck ISO_GND F.Cu Q8.3→C55.2` = 0, so the return is through the In1/In4 ISO_GND planes (Q8.3 all-Cu pad, C55.2 zone + 3 vias). Loop via C16/C55: `rv bq loop Q21.2 C16.1 C16.2 C55.1 C55.2 Q8.3 Q8.2 Q21.3` **74.0 mm / 37 mm²**. Via C89: 104.5 mm. 5.1: via C16/C55 112.4 mm, via C89 93.8 mm. So 5.2 ≤ 5.1 (better). |
| D2 | FAIL | `rv bq net DHB_HI_SOURCE_SEC` and track dump: Q8.2 → B.Cu 0.75 mm (2.45 mm) → 1.0 mm (68.88,−46.5)→(62.8,−46.5)→(62.8,−49.2) → **single via 1.0/0.5 at (62.8, −49.2)** → F.Cu 1.2 mm → the Q21.3–TR3 1.6 mm track. Q8 carries I2/√2 = 2.22/√2 = **1.57 A rms (2.85 A peak)** through this one via. The README scale (0.8/0.4 ≈ 1 A, 0.6/0.3 ≈ 0.7 A) gives about 1.2 A for 1.0/0.5. README 3a.3 claims "good for 3.3 A", which is the 1.0 mm track; the via is the limit. No node copper on inner layers; ≥ 1.2 mm to other nets except the DRV6 group (0.262 / 0.290 mm, group rule 0.2 mm). Q21.3 ↔ Q8.2 path ≈ 25 mm (switch-node inductance in the secondary loop). 5.1 joined Q8.2 through the In4 pour (README:583). See F4. |
| D3 | PASS | `neck TRANS_SEC 69.5,-51.8 → C16.2` 1.19 mm (thermal spokes of the SMD pad, zone `connect_pads thru_hole_only`); TRANS_SEC zone 6.9 mm wide at x 71.2. 420V band 4.04 mm at x 66 (`xsec 420V F.Cu x 66`), 427 mm² pour; `neck 420V Q21.2→P400V` 0.92 mm (Q21 pad entry, 3.06 A vs 1.57 A rms). The detour round the removed H5 is still there (README Stage 10); it is long, not narrow. |
| D4 | FAIL (note) | `rv bq fp C89…C101`: rows at 2.9 mm pitch (C90/C91 74.7/77.6 F; C101/C100/C99 72.5/75.4/78.3 B). PSA FM-series spec FM-000-001-13 (C692295 datasheet), 1210: W = **2.50 ± 0.30 mm**, T code G 2.50 ± 0.30. Nominal body gap 0.40 mm (≥ 0.3), **worst case 0.10 mm**. The neighbours' pads are the same nets (all turned −90°), so there is no 420V–ISO_GND pad pair between row neighbours (pad-to-pad 0.2 mm, same net). Courtyard overlaps C90/C91, C99/C100, C100/C101 known (`drc_summary.py courtyards_overlap`). See F7. |
| D5 | FAIL (note) | `rv bq dist P400V fp:GND` = **3.31 mm** on all layers (pads (83.2/88.2, −51.1) vs (83.2/88.2, −45.8)); 5.1 identical (`rv bq51 dist` 3.310 mm), so equal to 5.1. To H3 (86.97, −87.5): > 30 mm. See F8. |
| E1 | PASS | `rv bq fp L3` → "L3: not on the board"; `rv sch net '*TRANS_PRI*'` → none. |
| E2 | PASS | Symbol (`rv sch sheet 7`), board pads (`rv bq fp TR3`: 4/5 DHB_CAP, 7/8 DHB_HI_SOURCE, 9/10 TRANS_SEC, 11/12 DHB_HI_SOURCE_SEC), CHANGES table and DAB_TRANSFORMER.md 5 all agree. |
| E3 | PASS | `rv bq fp C16,C55`: C16 pad 1 420V, pad 2 TRANS_SEC; C55 pad 1 TRANS_SEC, pad 2 ISO_GND. |
| E4 | PASS | `drc_summary.py`: 0 dangling, 0 unconnected (137 items = courtyards 133, pth_inside_courtyard 2, starved_thermal 2 at C102). `rv bq near DC+ --within 0.3 --layer F.Cu` → 0 pairs. One leftover: a **0.9 mm² floating DC+ fill island** of 'Proteus F.Cu pour 29' at x 45.1…46.1, y −42.5…−41.4 (the 5.1 Q19 drain place) in the stored fill, touching no pad or via. The zone has island_removal_mode 0, so a refill should delete it. Note F10. |
| E5 | PASS | `rv bq fp C19,C30`: `CP_Radial_D10.0mm_P5.00mm_H50mm`, pad 1 = 420V, pad 2 = ISO_GND. C19 / C30 courtyards overlap (body centres 10.4 mm apart for D10 cans: 0.4 mm nominal gap; checklist 12). |
| E6 | PASS | `kicad_next/tube_psu_5_2.kicad_dru:105–107`: the Q19/Q21 exception is removed (comment only). L-slot polygon (50.815…52.015 × −62…−39.2 plus the bar y −40.4…−39.2 to x 68.6). It is still needed: it is what separates Q21.3 from the DC+ pour edge (6.93 mm straight, creepage round the slot ≫ 11.1). Board stiffness between TR3 and the Q21/Q8 heatsink is for checklist 12. |
| F1 | PASS | DAB_TRANSFORMER.md 6 (Lm before / after gap, Lsc from both sides, gap steps to 170–210 µH, no-load / full-load switch-node check) and 8 item 4 (hi-pot primary + core ↔ secondary 3 kV rms 1 min, PD test). Missing from the list: the split-capacitor / Lm resonance check (≈ 4.5 kHz) and a ringing check on the primary current (F2). |
| F2 | PASS | NEXT_REVISION.md:45 lists soft start, centring ≥ 2 s and DHB_I. Expected no-load current per bridge at 200 µH: 0.52 A rms (DAB_SIMULATION 2.4), Im peak about 1.8 A. A current-limited first power-up is not written anywhere (bring-up note, F2). |

Counts: **25 PASS, 5 FAIL (B1, C2, D2, D4, D5), 5 CANNOT VERIFY (A2, A5, A8, B4, B6)**.

## Findings (ranked, most severe first)

### F1 Primary HF commutation loop returns over 22.7 mm of In2 (C67 / C70 → Q7 source)
- Severity: **should fix**
- What is wrong: The bypass capacitors C67 / C70 (DC+ → DHB_CURRENT at (19.7, −48.0)) reach Q7's source (12.75, −63.34)
  only through a 1.2 mm **In2** track (0.5 oz) and two vias (22.6, −49 / −50). DHB_CURRENT is the bridge's power
  return before the shunt, so this contradicts the Stage 9 decision (DC+ and its GND return on F.Cu / B.Cu). The loop
  is 46.6 mm / 84 mm² against 5.1's 41 mm with flux-cancelling go and return on F.Cu, about 16 nH against about
  8–12 nH (estimate). The second HF path through C47 + C54 is on the outer layers but longer (69 mm). Electrically
  the margins hold (ZVS edges about 4 V, hard-switched edges < 50 V overshoot; thermally ≤ 0.75 A rms of 280 kHz
  ripple worst case against 1.13 A for 1.2 mm inner). But this loop is the path where the 5.1 ringing showed, and 5.2
  is worse than 5.1 here.
- Evidence: `rv bq neck DHB_CURRENT F.Cu 12.75 -63.34 21.175 -48.0` → 0; `rv bq net DHB_CURRENT` (In2 1.2 mm
  22.67 mm); `rv bq loop Q19.2 C67.1 C67.2 22.6 -49 22.6 -50.9 21.2 -52.3 17.4 -52.3 17.4 -62.14 15.5 -62.14 Q7.3 Q7.2 Q19.3`
  → 46.6 mm, 83.9 mm²; README Stage 4d "C67 return (HF loop) … In2 1.2 mm".
- Smallest fix: add **one 100 nF 630 V 1210 (C692295) on B.Cu at about (21.5, −60.5)**. Pad 1 goes on the existing
  2.5 mm B.Cu DC+ run (x 23.85, y −56.75…−70.9); pad 2 goes on a via (or 2) up into the F.Cu DHB_CURRENT zone
  next to C54 pad 2. B.Cu in the box x 18.5…26.5, y −63.5…−57.5 holds only that DC+ track (checked). The loop
  becomes Q19.2 → DC+ vias (17.7 / 18.7, −50) → B.Cu → capacitor → F.Cu → Q7.3, about 42 mm, all outer layers,
  i.e. 5.1-like. The In2 track can stay as a parallel path. Spacing (1.2 mm to R146 / TR3 pads, GND-pour opening)
  still has to be checked by DRC; not tried.
- Confidence: medium (inductance figures are estimates). A field solver or a measured VDS at turn-off on the first
  board would settle it.

### F2 Ringing / snubber: an RC across TR3 is not worth it; a DNP C / RC at the switch node is
- Severity: **should fix** (cheap insurance, DNP; not a blocker)
- What is wrong: The owner's 5.1 observation is heavy ringing (5–10 A peak, about 10 MHz) that disturbed the UART.
  The design document attributes it to winding capacitance, `rv pdf 25`: "The external inductor has high enough
  winding capacitance that the current has high levels of current spiking and oscillations … ringing during the phase
  shift period, due to high winding capacitance of the external ac inductor … the transformer also has excessive
  winding capacitance". 5.2 removes L3. The series inductance is now TR3's leakage, which is bypassed only by the
  interwinding capacitance across the 5 mm divider (≈ 3 pF, DAB_SIMULATION 1) and the winding self-capacitances
  (3–7 pF). A 41 µH / ≈ 6 pF mode is also at about 10 MHz, but with Z0 = √(41 µH / 6 pF) ≈ 2.6 kΩ a 400 V edge
  drives only about 0.15 A. In 5.1, 4.6 µH ETD34 leakage against tens of pF of L3 capacitance gave Z0 of a few
  hundred ohms or less. So the dominant mechanism is gone, and the sim sees "no ringing overshoot at the ZVS edges"
  (2.5). An RC across TR3 (DHB_CAP ↔ switch node) would dissipate C·(400 V)²·f = 0.5 W per 22 pF. It needs ≥ 2 ×
  1206 in series (±200 V) and damps only transformer modes. It does nothing for the two remaining HF sources:
  (a) **common-mode current through the interwinding capacitance**, ≈ 0.2 A spikes into ISO_GND per edge
      (DAB_SIMULATION 2.5). This is the more likely UART disturber; it is a Y-cap / return-path issue for
      checklists 04 / 10.
  (b) **body-diode recovery** in hard-switched edges (start-up imbalance: 30 A recovery; light-load mismatch), which
      rings in the bridge loops (F1, D1).
  The STF7N60M2 is also rated **MOSFET dv/dt 50 V/ns (VDS ≤ 480 V)** and **diode recovery dv/dt 15 V/ns (ISD ≤ 5 A,
  di/dt ≤ 400 A/µs)** (DocID024894 Table 2), while the sim gives **63–70 V/ns** on the primary node (2.5). The same
  was very likely true on 5.1.
- Evidence: design document p 25 / p 33 (`rv pdf 25`, `rv pdf 33`); DAB_SIMULATION.md 1, 2.5, 2.8; STF7N60M2 Table 2
  (static.chipdip.ru/lib/210/DOC005210689.pdf).
- Smallest fix: no footprint across TR3. Add a **DNP 1210 630 V capacitor footprint (optionally a series 1206
  resistor) from DHB_HI_SOURCE to DHB_CURRENT next to Q7** (pad on the F.Cu switch-node strip x 15–16.55, pad in the
  DHB_CURRENT zone east of it, at about y −59…−61). Add the same from DHB_HI_SOURCE_SEC to ISO_GND near Q8 if there
  is room. Populated with about 47–100 pF C0G it cuts dv/dt below 50 V/ns and is lossless under ZVS. The no-load
  node swing rises from about 66 ns to about 85–100 ns at Lm 200 µH, still < 150 ns dead time. With a series R it
  becomes an RC snubber for the hard-switched cases. Space is not checked by DRC.
- Confidence: medium that a TR3 snubber is unnecessary; low-to-medium that the switch-node footprint will be needed.
  Measuring the primary current and the switch nodes on the first board (F2 bring-up) decides it.

### F3 Builder documents still give the old TR3 gap 0.35 mm (Lm 300 µH)
- Severity: **should fix**
- What is wrong: The decided target is Lm ≈ 200 µH (0.66–0.68 mm centre grind, or 0.335 mm spacer under all legs,
  set by measurement). The transformer line of the assembly list says "gap 0.35 mm", which a winder reads as a
  centre-leg gap. The result would be Lm ≈ 300 µH, i.e. the 307 µH case of DAB_SIMULATION 2.3–2.4 (37 µJ hard edges
  at −5 % bus mismatch instead of ≤ 6 µJ).
- Evidence: `lib/jlc_parts_next.csv` TR3 note (`rv sch part TR3`), `kicad_next/fab/NOT_ASSEMBLED.md:20`,
  `NEXT_REVISION_PLAN.md:31` (D1). Correct in DAB_TRANSFORMER.md 4 / 5 / 6, CHANGES 2.1, sheet note
  `sheet07.py:195`, NEXT_REVISION.md:39.
- Smallest fix: CSV note → "gap ≈ 0.66–0.68 mm centre leg (or 0.335 mm spacer under all legs), set by measuring Lm
  170–210 µH; secondary TIW litz; cut pins 1, 2, 3, 6, 13–16 (DAB_TRANSFORMER.md 5 / 6 / 8)". Then regenerate
  NOT_ASSEMBLED with `jlc_fab.py` and edit D1 in the plan.
- Confidence: high.

### F4 Q8 drain joined to the secondary switch node through a single 1.0 / 0.5 via
- Severity: **should fix**
- What is wrong: Q8.2 → B.Cu → one via (62.8, −49.2) → F.Cu → switch node. Q8 carries 1.57 A rms / 2.85 A peak.
  By the project's own via scale a 1.0 / 0.5 via is about 1.2 A. A real 0.5 mm plated via probably carries 2–3 A, so
  this is a rating issue on paper, not a likely failure. The ≈ 25 mm detour also adds inductance in the secondary
  commutation loop (Q21.3 ↔ Q8.2).
- Evidence: `rv bq net DHB_HI_SOURCE_SEC` (vias: 1 × 1.0/0.5); README Stage 3a.3 ("Good for 3.3 A" refers to the
  1.0 mm track); README "Current and width" via scale.
- Smallest fix: add one or two 0.8 / 0.4 vias beside (62.8, −49.2) on the existing B.Cu 1.0 mm / F.Cu 1.2 mm pieces
  (e.g. along y −46.5…−49.2 on x 62.8 / along y −49.6).
- Confidence: medium-high on the arithmetic, low that it matters thermally.

### F5 Cross-footprint pad pairs below the 1.2 mm HV functional spacing
- Severity: **note** (whole-board rule question for checklist 10)
- What is wrong: The "HV functional, outer layers" rule exempts **every** pad–pad pair, not only pads of one
  footprint. In this part: Q7.2 (400 V switch node) ↔ R70.2 (GND) **0.883 mm on B.Cu**; C90.1 (420V) ↔ C89.2 (ISO_GND)
  **1.075 mm on F.Cu** (C89 moved out of the row in 5.2). Both are bare pads.
- Evidence: `rv bq near DHB_HI_SOURCE --within 1.3` (GND B.Cu 0.883 mm at (10.88, −60.62) = R70 pad 2);
  `rv bq near 420V --within 1.2 --layer F.Cu` (ISO_GND 1.075 mm at (75.8, −78.55)); `kicad_next/tube_psu_5_2.kicad_dru:59–62`.
- Smallest fix: move R70 about 0.4 mm west and C89 about 0.2 mm south, or restrict the exemption to
  `A.Parent == B.Parent`.
- Confidence: high on the distances; the acceptability is a basis decision (≥ IPC-2221 B4 0.8 mm only with coating).

### F6 STF7N60M2 dv/dt ratings on paper
- Severity: **note** (same devices and similar edges as 5.1)
- What is wrong: The sim gives primary node dv/dt 63–70 V/ns under ZVS against a 50 V/ns "MOSFET dv/dt ruggedness"
  rating. Hard-switched events (start-up imbalance, light-load mismatch) exceed the 15 V/ns / 400 A/µs diode
  recovery conditions (sim: 30 A recovery current at the first edge, 2.8).
- Evidence: DocID024894 Rev 1 Table 2; DAB_SIMULATION.md 2.5, 2.8.
- Smallest fix: firmware (centring, frequency soft start, DC+ tracking) as already recorded. Optional node capacitance
  through the F2 footprint.
- Confidence: medium (sim dv/dt from a fitted Coss model).

### F7 420V 1210 row pitch 2.9 mm leaves 0.1 mm worst-case body gap
- Severity: **note** — W = 2.50 ± 0.30 mm (FM-000-001-13), nominal gap 0.4 mm. The neighbours are the same nets and
  orientation, so touching bodies are harmless electrically. For JLC placement see checklist 14.

### F8 Output terminals P400V / GND 3.31 mm apart
- Severity: **note** — below the checklist's 4 mm, identical to 5.1 (`rv bq51 dist P400V fp:GND` 3.310 mm). The
  insulated faston receptacles and the earthed ISO_GND make it a functional gap (≥ IPC-2221 B2 2.5 mm, 301–500 V).

### F9 Split-capacitor DC-bias derating not documented
- Severity: **note** — the FS55X105K631EHG approval sheet gives no DC-bias, ESR or ripple data. The sim uses 1 µF.
  Even at 0.4 µF effective the ripple stays within 10 %, and the part is the 5.1 part. Measure C at 200 V bias on one
  sample if convenient.

### F10 Floating 0.9 mm² DC+ fill island at the old 5.1 Q19 place
- Severity: **note** — 'Proteus F.Cu pour 29' piece x 45.1…46.1, y −42.5…−41.4, connected to nothing, in the stored
  fill (island removal is on, so a refill removes it). Check that the Gerbers (`kicad_next/fab/`) are from a refilled
  board (checklist 14).

### F11 Low-leakage fallback paragraph is stale
- Severity: **note** — DAB_TRANSFORMER.md 5 "L3. Remove it and bridge its pads … Keep the RM8 footprint for now … a
  small residual L3" and 6 step 2 "add a small residual L3" contradict CHANGES 2.4 (no L3 position). If the sample's
  Lsc is low, the only remedies are re-turning or moving the windings outward. Also DAB_TRANSFORMER.md line 4 swaps
  the refdes ("Q7/Q8 on DC+ … Q19/Q21 on 420 V"; it should be Q19/Q7 primary, Q21/Q8 secondary).

### F12 C19 / C30 voltage margin
- Severity: **note** — 450 V rated against 441 V (420 V + 5 %). A bidirectional converter can pump energy back but
  also limits overshoot actively; make sure the firmware's 420V over-voltage trip is ≤ 445 V. The ripple current is
  not published by Ymin.

## Compared with 5.1
- **Better:** total magnetic loss (≈ 2.3 W vs ≈ 6.7 W for ETD34 + L3, DAB_TRANSFORMER 3.4); MOSFET rms current
  (2.31 vs 2.60 A); Pmax 871 W vs ≈ 480 W (A4); main ringing source (L3 winding capacitance) removed; secondary
  commutation loop 74 mm vs 94–112 mm (D1); switch-node copper 121 vs 164 mm²; output capacitance 136 vs 78 µF;
  balancing resistors added; 630 V 1210 bypass parts; reinforced TR3 barrier (37.6 mm rows, 11.6 mm plane gap).
- **Equal:** devices (STF7N60M2), split capacitors (same part), terminal spacing 3.31 mm, inner HV spacing (0.5 mm to
  the hole wall vs 0.635 mm ring-to-ring).
- **Worse:** primary HF loop (In2 return, ≈ 16 vs ≈ 8–12 nH estimated, F1); DC+ entry into the Q19 drain 0.9 + 0.9 mm
  vs 2.3 mm (C1, within the rule); Q8 drain link through one via instead of the In4 pour (F4); magnetising current
  ±1.8 A vs 0.7 A (intended, costs ≈ 0.5 W); no fallback position for an external inductor.

## Could not verify
- A2: 5.1 TR3 winding sense / dot convention (not in the 5.1 schematic or documents); needs the 5.1 firmware phase sign
  or a look at the 5.1 transformer.
- A5: DC-bias curve, ESR and ripple-current rating of FS55X105K631EHG (not in the PSA approval sheet fetched from the
  JLC C784102 link).
- A8: ripple-current rating of KCXE5002W680MF (not on the Ymin KCX page; the LCSC PDF is an image without text).
- B2: an EC42/15 core datasheet (generic seller core; Ae 187 mm² / Ve 18.47 cm³ taken from DAB_TRANSFORMER.md 2).
- B4 / B6: caliper data of the bought EC42 set (pin diameter, row spacing, base, seated height, core-plate height /
  bobbin stand-off over the secondary pins and board copper).
- STF7N60M2: only Rev 1 (2013) could be read; st.com refused the download, and a search snippet mentions a 2026
  Rev 2 with a 650 V-at-Tjmax wording. The values used (RDS(on), Coss eq., ratings) should be re-checked against
  the current revision.
- KRL2012 4 mΩ datasheet not fetched (R83 is checklist 08; only the via / copper path is judged here).
- The size of the 5.1 ringing current in the 5.2 layout is a bench question (F2).

## Outside scope
- Checklist 10: the pad-pair exemption across footprints in "HV functional, outer layers" (F5); TR1 / ISO2 slot pairs
  at 7.25–11 mm in `rv bq near @SEC --within 11.1 --other-domain` (slot-separated, not checked here).
- Checklist 04 / 10: common-mode return for the ≈ 0.2 A TR3 interwinding spikes (Y-capacitor path ISO_GND ↔ GND) as
  the likely UART disturber (F2).
- Checklist 12: C19 / C30 10 mm cans with 0.4 mm nominal body gap (courtyard overlap); L-slot stiffness between TR3
  and the Q21 / Q8 heatsink.
- Checklist 14: stored zone fill with the DC+ island (F10); 1210 row spacing for placement (F7).
- Checklist 13: `fab/NOT_ASSEMBLED.md` TR2 line says "custom transformers (EF20 / EF25 / ETD34)" (stale wording).
- Checklist 02: R70 (Q7 gate pull-down) pad 0.883 mm from Q7 drain on B.Cu (F5).
