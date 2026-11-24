# Findings: 13 BOM and parts  (reviewer: Claude Opus 5.5, 2026-11-24, commit fdae703)

## Summary
The parts tables, the schematic and the board agree: 369 parts, 0 netlist differences, 0 board field differences. Every
part added or changed in the last two days has the right rating and the right package for its footprint. **One problem
blocks ordering, and it is not a parts-table problem.** Stage 4k turned SICD1 / SICD2 by 180° so that their outlines face
the heatsink, but the A / K pad nets stayed where they were. Wolfspeed's C3D02060A has **pin 1 = cathode**. With the tab
on the heatsink, as on 5.1, the cathode lead now goes into pad A (PFC drain) and the anode into pad K (DC+), so both
diodes are reversed (F1).
Two of the six "missing" part numbers, C2M0160120D (Q5 / Q6) and C3D02060A (SICD1 / 2), are **obsolete** at Wolfspeed
today. The table only says "consign" and names no source (F2). JLC stock for 2 × CM1 / CM4 is 20, which covers about
10 boards (F4). I could not read today's stock for any part: the public LCSC / JLC pages did not show stock, and the
permission system blocked the JLC / LCSC API.

Counts: 24 items: **PASS 9, FAIL 11, CANNOT VERIFY 4**.

## Checklist results
| Item | Verdict | Evidence |
|---|---|---|
| A1 | PASS | `rv sch check`: "369 parts in the netlist, 369 csv rows, 0 difference(s); status: equivalent 203, exact 78, changed 59, consigned 21, missing 6, dnp 2; 104 different LCSC numbers". `python3 tools/next/netlist_diff.py --check`: "369 parts, CSV check OK". `python3 tools/next/jlc_fab.py --check`: "kicad_next/fab/ up to date (19 files)". **Differs from the checklist**: it says 363 parts, missing 14, 102 LCSC numbers and 33 without an LCSC number. Today there are 29 without one: the four shunts are fitted now, R68 has five new parallel parts (R159–R163), C141 is new, and Q7 / Q8 / Q19 / Q21 changed from missing to consigned. |
| A2 | FAIL (note) | `parts_table.py board`: "380 footprints … 0 field difference(s)". C10 and C26 have status dnp, but the DNP attribute is not set on the board. They are in neither `fab/tube_psu_5_2_bom.csv` nor `_cpl.csv` (grep: no hit), so no "na" BOM line can confuse the order. **Their paste openings are in `tube_psu_5_2-F_Paste.gtp`**: flashes at Gerber (35.475, −10.0), (33.925, −10.0), (27.6, −2.875) and (27.6, −1.325) = C10 / C26 pads (`rv bq fp C10,C26`: GND ↔ HEATER_I_MEAS and GND ↔ DHB_I_MEAS). JLC's stencil will print paste on four empty 0603 pads. → F7 |
| A3 | PASS (doc note) | `parts_table.py` "CHECK same LCSC" lines: C12891 `22u 25V` / `22u`; C23630 `2.2u` / `2u2`; C22775 `100` / `100R`; C21190 `1.00k` / `1k`; C23140 `33` / `33R`. These are the same part written differently. C51890374 and C528659 are one part on two footprint variants (Proteus pad variant; ISO1 / ISO2 slot variants). `jlc_fab.py` writes one BOM line per LCSC number (fab/README "17 BOM lines … different value texts"), so nothing is split. |
| A4 | FAIL | exact 78 / equivalent 203 / changed 59 → placed by JLC (BOM / CPL 340 parts). Consigned 21 = 12 blade terminals, TR1–TR3, L1, L2, Q7 / Q8 / Q19 / Q21: hand-fitted by the owner ("Through-hole parts JLC does not fit at all", fab/README). dnp 2 = C10, C26. **Missing 6** = DB1, Q5, Q6, R27, SICD1, SICD2: NOT_ASSEMBLED.md gives only "consign or global sourcing" / "consign" and no distributor, quantity or on-hand statement. Q5 / Q6 / SICD parts are obsolete (D3). → F2, F3 |
| A5 | CANNOT VERIFY (partly closed) | 45 rows carry a remark today (checklist: 46). **Closed with evidence:** R1 / R14 / R19 / R20 4.99 Ω and R26 / R57 / R87 / R90 40.2 Ω (E96 substitutes, value notes only); Q7 / Q8 / Q19 / Q21 pin-out (Infineon datasheet Rev. 2.2, 2020-01-30, p 1: pin 1 gate, 2 drain, 3 source, fetched); J4 C492405 identity (LCSC page: XFCN PZ254V-11-06P, 1 × 6, 2.54 mm, male, THT, 3 A); C105987 identity (LCSC / JLC pages: IHHEC C1206N332J631T, 1206, 3.3 nF, NP0, 630 V, ±5 %, extended); R21 / R30 / R83 / R93 body against pads (Susumu KRL catalogue p 51–52: KRL2012 L 1.25 ± 0.2, W 2.00 ± 0.2, terminal a 0.30 ± 0.2 mm, 1 W, 3–9 mΩ ±1 % ±50 ppm; pads cover 0.3125…0.6625 mm from centre against terminals 0.325…0.625 mm). **Still open:** stock / price of C105987 and C492405 (pages fetched, no stock shown); C38 body width and C86 / C117 body size (no dimensions on the fetched pages; LCSC says "Part not found" for C2888216, JLC lists it); KRL2012 recommended land pattern (not in the catalogue pages fetched); J2 mating height (owner); the CA-IS3761LW / CA-IS3721HW certificate scope (owner accepted, D5); CM1 / CM4, R124, C19 / C30, AD1 / AD2 stock (D1); L1 / L2 value (owner measurement). |
| B1 | FAIL (notes, as 5.1) | Appendix B1. Over the 80 % ceramic / film target: **C73** 2.2 µF X6S 450 V on DC+ at 400–450 V = 89–100 % (as designed and as 5.1's original part number). Within the target: C692295 630 V on ≤ 450 V = 71 %; C784102 630 V on the half bus ≈ 225 V ± ripple = 36–40 %; C105987 630 V at 365 V per part = 58 % (06 A2 calculation, checked: 200 V + 165 V swing); C12 1 kV C0G; C102 250 V on ≤ 100 V = 40 %; X2 / Y2 parts at their class rating (C38 275 VAC KEMET R46 X2; C64 / C66 TDK B32921 X2 305 VAC; C86 / C117 Dongtong MKP62 X2 275 VAC per the JLC page; C65 / C81 / C82 / C84 / C85 TDK CS45 X1 / Y2 per 05 A5). C64 / C66 see the unipolar rectified half-wave of ≤ 358 V peak against 305 VAC × √2 = 431 V. Their HF ripple current is not published on the pages I fetched (CANNOT VERIFY); 5.1 had the same circuit. |
| B2 | PASS | C95 / C52 / C79 / C80 C6119856 (LCSC page: HRE CGA0603X5R475K250JT, 0603, 4.7 µF, X5R, 25 V, ±10 %) on 15V (14.2–15.5 V) = 62 % ≤ 80 %. Effective capacitance: no DC-bias curve published. 02 F7 estimates ≈ 0.9–1.3 µF at 15 V against a pin-local need of 240 nF, so ≥ 3.7× (not re-derived: no curve available). C141 C14663 (LCSC: Yageo CC0603KRX7R9BB104, 100 nF X7R 50 V ±10 %) on 15V_ISO_SEC ≤ 17.5 V = 35 %. C71 C6119961 10 V X5R on 5V = 50 %. C6 / C36 / C114 / C115 22 µF 25 V on 5 V = 20 %. C40 25 V on −15V_SEC ≤ 16.8 V = 67 %. C8 / C9 / C18 / C23 / C24 / C33 50 V on ≤ 15.5 V. C57 / C60 / C62 / C83 CL10A225KO8NNNC 16 V on 3.3 V nets (`rv sch ref`: AD2_3V3, +3V3, +3V3, AD1-VA) = 21 %. C17 25 V on 6V3 ≤ 7 V = 28 %. |
| B3 | FAIL (notes, as 5.1) | Electrolytic target 90 %. **C19 / C30** C913388 (LCSC page: Ymin KCXE5002W680MF, 68 µF, **450 V**, D10 × 50, P5, 1 A @ 100 kHz, 3000 h @ 105 °C) on 420 V nominal / 441 V (+5 %) = 93–98 %. 5.1 had 450 V parts (EKXJ451) on the same node. Bulk C28 / C29 / C37 / C56 450 V on 430 V peak = 96 %; their ripple rating was checked by 05 A10. Within the target: C1 / C2 25 V on ≤ 17.5 V = 70 % (ripple ≈ at rating at 20 W, 01 A14); C58 C2887274 (LCSC: KNSCHA RVT 22 µF 35 V SMD D5 × 5.4, 105 °C, 2000 h, 280 mA @ 120 Hz) on VCC ≤ 16 V (OVP 24 V) = 46 % (69 %); C31 / C32 10 V on ≤ 7 V = 70 %; C102 KCXE 250 V on ≤ 100 V = 40 %. The C19 / C30 HF ripple current (1 A rating) is not compared, because the DAB output-capacitor current was not computed (07 A8). |
| B4 | PASS (at the limit, as 5.1) | Uniroyal thick-film data sheet V.3, Feb 12 2019, p 4/9 (fetched via datasheet.lcsc.com …0a975aaa…pdf?productCode=C17514): **0805 max working 150 V, overload 300 V; 1206 200 V / 400 V**; rated power to 70 °C. (a) 1 MΩ 0805 C17514 chains (R10 / R15 / R16 DC link; R23 / R34 / R39 420V; R109 / R111 / R112; VAC divider): 400 / 3 = 133 V, 420 / 3 = 140 V, **450 / 3 = 150 V = 100 % of the working voltage**, 154–161 V at 462–483 V transients (< 300 V overload); 20–23 mW of 125 mW. R4–R6 C17954 (LCSC: 1206, 200 kΩ, 1 %, 250 mW, 200 V): 88 Vrms = 124 Vpk = 62 %, 39 mW = 16 %. R68 + R159–R163 C368302 (LCSC: Walsin WR12X7322FTL, 1206, 73.2 kΩ, 250 mW, 200 V, −55…155 °C): 84.4 V = 42 %, 84.4² / 73.2k = 97 mW = 39 %. R151–R153 10 MΩ / R114–R116 4.7 MΩ 1206: ≤ 168 V at 505 V = 84 % of 200 V. R143–R150 / R155–R158 220 kΩ 1206: 105 V, 50 mW = 20 %. R124 2.61 kΩ 1206: 86 mW = 34 %. R8 / R9 C3000600 (LCSC: FOJAN 1206 1.37 Ω 250 mW 200 V). Shunts C2073455 (LCSC: 5 mΩ, 1 W): ≤ 3 A rms → ≤ 45 mW. |
| B5 | FAIL (notes, as 5.1) | Voltages within target: IPA60R280CFD7 V(BR)DSS 600 V (datasheet Rev. 2.2 p 5) on ≤ 450 V = 75 %; C2M0160120D 1200 V; C3D02060A VRRM 600 V (Wolfspeed Rev. 10, Oct 2024 p 1) on ≤ 450 V + overshoot; BSS138LT1G 50 V (onsemi BSS138LT1/D Rev. 15, Sept 2026, p 1) on a 5 V relay coil; ZLLS400 VR 40 V on gate nets ≤ 17.5 V = 44 %. **Over a current rating on paper:** ZLLS400 (Diodes DS33226 Rev. 10-2, Maximum Ratings: IFPK 0.85 A "rectangular pulse duty cycle", IFSM 12 A for t ≤ 100 µs, 2.5 A for 10 ms) in the turn-off paths D30–D35 / D33 carries ≈ 1.2–4.4 A for a few ns (02 F8, 06 F9 arithmetic checked: 14.4 V / (3.3 + Rg,int + Rsink)). That is above IFPK but far inside IFSM for ≤ 100 µs. D35 copies the bench-verified D33 network. **DB1** TBS22K runs at its 2.2 A average rating at 540 W (05 F9; JLC page for TBS22K-TP C17401133 and TBS22M-TP C17666797: 2.2 A, 950 mV @ 2 A, 90 A IFSM). Reverse voltage 800 V on 358 V peak = 45 %. |
| B6 | FAIL (note: C69) | **REF3325** (TI SBOS392I, Aug 2007 – revised Apr 2026, fetched from ti.com/lit/ds/sbos392d/sbos392d.pdf): capacitive load **0.1 µF min … 10 µF**; VIN VOUT + 0.2 = 2.7 … 5.5 V (supply +3V3 → PASS). C69 = C14663 100 nF X7R ±10 % (`rv sch ref C69`: Net-(REF1-VOUT) – GND), so 90 nF at −10 %: **below the minimum at tolerance** (as 04 F5; not in RESOLUTIONS.md). Other supplies, checked against the datasheets fetched by the earlier reviews (values checked, not re-fetched): UCC21520 VDD 9.2–25 V recommended against 15V 14.2–15.5 V / 15V_ISO_SEC ≤ 17.44 V (02 A7, SLUSCJ9F §6.3); UCC27511A on 15V (05 A12, SLUSD95A); UCC27524A on 6V3 (06 C1, SLUSBP4C); MIC5205 VIN 2.5–16 V against ≈ 5.7 V (03 B5, DS20005785A); LMH6643 at 3.3 V ≥ 2.7 V (08 C1, SNOS966Q). Smallest margins: C69 (−10 %); 15V_ISO_SEC 17.44 V against 25 V. |
| B7 | FAIL (note, mostly as 5.1) | X5R (85 °C) parts within 10 mm (courtyard to courtyard, `rv bq fp`, script in this review) of parts that dissipate > 0.5 W: C95 0 mm Q19 / 0.3 mm Q7; C80 0 mm Q6; C52 0 mm Q10; C79 5.6 mm Q5; C87 2.1 mm Q7; C43 0 mm Q8 / 0.3 mm Q21; C21 2.2 mm Q8; C57 4.9 mm Q8; C62 4.2 mm Q6; C8 / C9 / C23 / C33 / C13 / C17 0–3.9 mm Q1 / Q2; C18 0 mm TR2; C6 / C36 / C40 / C71 / C114 / C115 0–0.3 mm TR1; C83 5.0 mm R27. "0 mm" means an overlap seen from above with the part on the other side. Most of these are 5.1 parts in 5.1 places. New in 5.2: C95 changed from X7R 1206 to X5R 0603; C79 / C80 moved to the driver pins (stage 14f). |
| C1 | PASS (with one note) | LCSC pages fetched 2026-11-24, package = footprint (`rv bq fp`): C105987 1206 → `C_1206_3216Metric`; C6119856 0603 → `C_0603`; C14663 (C141) 0603 → `C_0603`; C368302 / C17954 1206 → `R_1206_3216Metric`; C2073455 "2012" (KRL2012, 1.25 × 2.00 mm long-side terminals) → `R_0508_1220Metric_KRL2012`; C492405 1 × 6 P2.54 THT male → `PinHeader_1x06_P2.54mm_Vertical` (drill 1.0); C2881768 2 × 25 P1.27 THT female socket → `PinSocket_2x25_P1.27mm_Vertical_XKB_X1321FV` (drill 0.70 / pad 1.02); C2887274 SMD D5 × 5.4 → `CP_Elec_5x5.4`; C3000600 1206 → R_1206; C913388 D10 P5 → `CP_Radial_D10.0mm_P5.00mm_H50mm`; C536369 / IPA60R280CFD7 "TO-220F-3" → `TO-220-3_Vertical` (pads 2.54 mm, drill 1.1). PWM2 C17699638: footprint against datasheet figure 39 by 01 C8 (the JLC package string is wrong and the order notes say so). **Note:** IPA60R280CFD7 leads (Infineon outline Z8B00003319 rev 10: b 0.65–0.90, c 0.40–0.63 mm) have a diagonal of up to 1.10 mm, equal to the 1.1 mm drill at maximum material (typical 0.93 mm). The footprint and the 5.1 STF7N60M2 FullPAK are the same. |
| C2 | **FAIL (blocker)** | Q9: `SOT-23_Proteus` descr "pad 1 = JEDEC pin 3, pad 2 = pin 1, pad 3 = pin 2". Pad coordinates (pad 2 (−0.95, −0.94), pad 3 (−0.95, +0.94), pad 1 (+0.96, 0)) = the KiCad SOT-23 pin 1 / 2 / 3 positions. BSS138LT1G style 21: 1 G, 2 S, 3 D. Board: pad 2 Net-(Q9-G), pad 3 GND, pad 1 Net-(Q9-D) → **PASS**. REF1: REF33xx 1 IN / 2 OUT / 3 GND (SBOS392I); pad 2 +3V3, pad 3 VOUT, pad 1 GND → **PASS**. D35 (new) ZLLS400 on `D_SOD-323_AC`, as D33 → same handling as 5.1. **SICD1 / SICD2 `TO-220-2_Vertical_AK`: reversed with the tab on the heatsink** → F1. |
| C3 | CANNOT VERIFY (partly PASS) | PASS: C19 / C30 D10 / P5 (LCSC); KRL2012 body against pads (A5); 5.1 used the same KRL2012 footprint. LMH6643MMX / IPD60R280P7S / C1–C2 pairs: checked by 08 C1 / 06 / 01 (no change since). Open: **C38** body width (LCSC page gives no size; datasheet wrapper not readable); **C86 / C117** body (LCSC: "Part not found" for C2888216; the JLC page lists the part with no dimensions); **J2**: I could not fetch the XKB drawing myself (LCSC datasheet link is an HTML wrapper). The CSV / CHANGES 6.1 quote rev A0: hole Ø0.70, pin 0.45 mm, insulator 4.3 mm; footprint drill 0.70 matches. Mating height / orientation against the card: owner. |
| C4 | PASS (note for 14) | fab/README "Rotations: NOT verified": `ROTATION_FIX` is empty. The families are listed (14 SOT-23 Proteus parts, 11 SOIC / MSOP, 21 diodes, 12 polarised caps …), and the order step "check every polarised part in JLC's placement preview" is written down (RESOLUTIONS 14 F1 open). |
| D1 | FAIL (on the table's figures); today's stock CANNOT VERIFY | The public pages (lcsc.com/product-detail/C…, jlcpcb.com/partdetail/C…) fetched for C105987, C2881768, C492405, C2073455, C536369, C17666797, C2888216 show **no stock or price**. The permission system blocked the JLC / LCSC API (stock is loaded by script). Against "≥ 5 × quantity for 5 boards" with the CSV stock: **CM1 / CM4 C1534140 20 (need 10 for 5 boards, 50 for the 5× margin) → FAIL**; PWM2 public 3 (owner holds 10 in his JLC stock → covered); R124 C245506 75 ≥ 25; C19 / C30 C913388 103 ≥ 50; J2 C2881768 202 ≥ 25; AD1 / AD2 C74860 276 ≥ 50; C102 386; IPA60R280CFD7 C536369 15 (consigned, not needed); C105987 and C492405 **never read**; C2888216 (C86 / C117) delisted on LCSC ("Part not found"). → F4 |
| D2 | PASS (note) | fab/README: placed parts basic 165 / 38 LCSC numbers, **extended 175 / 66 LCSC numbers**. High-count extended lines are passive parts with no basic part of the same rating in the table (C692295 630 V × 11, C460267 × 11, C17956 × 12). No action. |
| D3 | FAIL | **C2M0160120D: "Obsolete"** (wolfspeed.com product page, fetched 2026-11-24; suggested replacement C3M0160120D). Wolfspeed "C2M0160120D Transition Guide" (Sept 2024, assets.wolfspeed.com): EOL issued Oct 2024; C3M0160120D TO-247-3 "**Fully Compatible**", VGS −4 / +15 V (recommended turn-on 15 V; abs max +19 / −8 V), RDS(on) 160 mΩ typ, Qg 38 nC, RθJC 1.29 °C/W (C2M 0.9). C3M0160120D datasheet Rev. 04 Sept 2024: VGS(th) 1.8–3.6 V, RDS(on) 160 / 208 mΩ at 15 V; LCSC C5713505 exists. **C3D02060A: "Obsolete"** (Wolfspeed page, no replacement named). C6D04065A is Active (Wolfspeed page): TO-220-2, 650 V, 4 A, **Qc 16 nC** (C3D02060A 5.8 nC, Rev. 10 p 1); LCSC C7453727. DB1 TBS22K: mccsemi.com returned 403 → CANNOT VERIFY. DigiKey says TBS22M-TP is "no longer available at DigiKey". JLC lists TBS22K-TP C17401133 and TBS22M-TP C17666797 (1 kV, 2.2 A, same TBS family; no stock shown). R27 TWW10J47RE: ohmite.com 418, octopart 403 → CANNOT VERIFY. Q7 / Q8 / Q19 / Q21: on hand per CHANGES 6.6. TR1–3, L1 / L2: wound by the owner. Blade terminals: no part number anywhere in the repository. → F2, F3 |
| D4 | CANNOT VERIFY (TI parts PASS) | ti.com product pages fetched 2026-11-24: UCC21520 **ACTIVE** (newer pin-compatible UCC21550 offered); UCC27511A **ACTIVE**; UCC27524A **ACTIVE** (UCC27624 offered as drop-in); LMH6643 **ACTIVE**; TLV9062 **ACTIVE**; REF33 family **ACTIVE**. The pages give the status per device, not per orderable suffix. Infineon pages for ICE5AR0680AG and IPA60R280CFD7 returned only navigation (status not readable); IPD60R280P7S and Chipanalog CA-IS3761LW / CA-IS3721HW were not fetched. |
| D5 | CANNOT VERIFY (owner accepted) | Not re-fetched. One finding with 03 F1 / 04 F2: CA-IS3761LW v1.05 lists VDE / UL / CQC / TÜV certificates; CA-IS3721HW rev C has all certificates pending. Owner accepted both on 2026-11-24 (RESOLUTIONS.md 03 F1, 04 F2; CHANGES 6.a). Certified fallback named: Si8621ED-B-IS (consign). |
| E1 | PASS (doc notes) | Q9 is now `BSS138` and the shunts are `5m` (`rv sch ref`). Values a schematic-only buyer could get wrong: V2 / V3 value `MIC5205` (no −3.3), with lib_id `tube_psu:TPS73033` and part_map device `TPS73033`. A TPS73033 bought for V3 (input ≈ 5.7 V from 6V3) would be above its 5.5 V maximum. U1 / U4 `LMH6643` (MMX only in the table); L1 / L2 `TBD (measured)`; RL1 `SONGLE RELAY`. Stale `device` strings in `lib/part_map_next.csv` (not on the schematic: grep of `*.kicad_sch` finds none): C22 / C41 / C42 / C49 `12061C103KAT2A` (10 nF X7R), Q7 / Q8 / Q19 / Q21 `IRFBE20`, Q5 / Q6 `IRFP460`, C19 `EKXJ451ELL390MJ50S`. |
| E2 | PASS (note) | Only C28 / C29 / C37 / C56 `82u 450V`, C40 `22u 25V`, C58 `22u 35V` and C102 `56u 250V` carry a rating in the value. The table is the BOM source (`jlc_fab.py` reads `lib/jlc_parts_next.csv`). |
| E3 | FAIL (note) | Stale or incomplete notes: Q5 / Q6 "C2M0160120D (Wolfspeed) 0 stock; only clone-branded parts < 100; consign" (no EOL, no C3M0160120D); SICD1 / SICD2 suggest VS-C04ET07T-M3 "check pinout" and do not say the C3D02060A is obsolete; the J2 note says "pad 1.0 mm" (board 1.02 mm since stage 15g, `rv bq fp J2`). TR3 carries the new tape-gap note (checked: CSV TR3 note "≈ 0.83 mm spacer … tuned on the bench"). |

## Findings (ranked, most severe first)

### F1 SICD1 / SICD2 lead assignment reversed by the stage-4k 180° turn
- Severity: **blocker for ordering** (bare board)
- What is wrong: `tube_psu:TO-220-2_Vertical_AK` has pad A at the KiCad pin-1 position (local (0, 0)) and pad K at
  (5.08, 0), with the tab on local −y (descr "pads A (pin 1) / K (pin 2, tab)"). The Wolfspeed C3D02060A has **pin 1 =
  CATHODE, pin 2 = ANODE, case = cathode** (data sheet Rev. 10, Oct 2024, "Package Dimensions & Pin-Out", fetched from
  assets.wolfspeed.com/uploads/2020/12/C3D02060A.pdf). So a diode inserted as its outline shows puts the cathode into
  pad A.
  On 5.1 (`rv bq51 fp`) the SICD outlines faced **away** from the heatsink: SICD1 rot −90 in the Q6 column (Q6 rot 90,
  tab −x), SICD2 rot 90 in the Q5 column. So the real diodes were mounted against their outline, tab to the plate.
  That mounting put the cathode into K (DC+), which is why 5.1 works.
  On 5.2 the user turned both by 180° (README "Stage 4k": "anode and cathode changed sides", 05 C7: "their tabs now face
  the same way as Q5 / Q6"). The pours were reshaped so that A stays on the drain and K on DC+. The physical positions
  of drain and DC+ therefore swapped. SICD1: 5.1 A (11.503, −26.727) north / K (11.503, −21.647) south; 5.2 A (11.8,
  −21.4) south / K (11.8, −26.48) north, with the tab on the same (−x) side.
  With the tab on the heatsink, the cathode now lands in PFC_DRAIN_1 / PFC_DRAIN_2 and the anode in DC+. When Q5 / Q6
  turn on, DC+ is shorted through the diode and the FET.
- Evidence: footprint pads (`grep -A2 "(pad" lib/tube_psu.pretty/TO-220-2_Vertical_AK.kicad_mod`); `rv bq fp
  SICD1,SICD2,Q5,Q6` and `rv bq51 fp SICD1,SICD2,Q5,Q6`. The same KiCad convention (pin 1 at local x = 0, viewer's left
  seen from the front, tab at −y) gives the correct G-D-S for Q7 / Q19 with the Infineon pin 1 = gate (`rv bq fp Q7`:
  pad 1 Net-(Q7-G) at the +y end with the tab towards −x), and for Q5 / Q6 on both boards.
- Smallest fix: swap the two leads' nets at SICD1 / SICD2 again. Either turn both footprints back by 180° about their
  centre and redo the stage-4k pours (the tab outline then points away from the plate, as on 5.1, which is cosmetic),
  or keep the positions and give the footprint pad K at local (0, 0) and pad A at (5.08, 0) (a "KA" variant), then
  re-shape the pours. Before that, hold a C3D02060A over a 1:1 print of F.Cu with its tab towards x ≈ 8, or look at a
  5.1 photo, to confirm. Checklists 05 / 12 should re-check the copper.
- Confidence: medium-high. The datasheet pin-out and the board geometry are certain. The open assumption is that the
  real diodes are clamped tab-first to the common plate (README "Stage 4a" heatsink line; 05 A8 "with the plate").

### F2 Q5 / Q6 (C2M0160120D) and SICD1 / SICD2 (C3D02060A) are obsolete, and no source is documented
- Severity: **should fix** (a **blocker for ordering** if the owner has no 5.1 spares)
- What is wrong: both Wolfspeed pages, fetched 2026-11-24, say "Obsolete". The table and NOT_ASSEMBLED.md say only
  "consign" and do not say whether the owner holds spares.
- Evidence: D3 row (Wolfspeed product pages; C2M0160120D Transition Guide, Sept 2024: "EOL issued Oct 2024";
  replacement C3M0160120D, TO-247-3, "Fully Compatible").
- Smallest fix: write the supply route into the CSV notes / NOT_ASSEMBLED.md: "5.1 spares on hand: n", or buy
  **Wolfspeed C3M0160120D** (2 per board; recommended 15 V gate, which suits the UCC27511A on 15V (14.2–15.5 V < 19 V
  abs max); RθJC 1.29 against 0.9 °C/W; LCSC C5713505). For the diodes, **Wolfspeed C6D04065A** (active, TO-220-2,
  650 V / 4 A, LCSC C7453727). Its Qc is 16 nC against 5.8 nC: about 2.8× the capacitive switching charge per PFC
  edge. Confirm its pin 1 / case = cathode from its drawing (the text of the fetched copy gives only "PIN 1 / CASE /
  PIN 2"), and fit it the same way as F1 requires.
- Confidence: high for the status. Medium for the replacements' suitability: they are as rated and pin-compatible,
  but have not been simulated.

### F3 Missing / consigned parts without an orderable part number or source
- Severity: **should fix** (documents)
- What is wrong: R27 has only "TWW10J47RE not stocked; consign" (no distributor found today: Ohmite 418, Octopart 403).
  DB1 has "TBS22K not stocked … consign or global sourcing". The **12 blade terminals** (2 legs, 5.0 mm pitch, Ø1.4 mm
  holes) have no part number anywhere in the repository (`lib/jlc_parts.csv` 5.1 and `_next` both "blade (faston)
  terminals: hardware").
- Evidence: NOT_ASSEMBLED.md; D3 row.
- Smallest fix: write the exact orderable numbers: DB1 **MCC TBS22K-TP** (JLC C17401133) or **TBS22M-TP** (1 kV, same
  family / package, JLC C17666797), via JLC global sourcing or consigned; R27 **Ohmite TWW10J47RE**; the terminal part
  the owner used on 5.1. Stock of all three: CANNOT VERIFY today.
- Confidence: high that the documents lack it; stock unknown.

### F4 CM1 / CM4 JLC stock 20 for 2 per board
- Severity: **should fix** (order-day check)
- What is wrong: C1534140 KEMET SCF20-05-550, stock 20 on 2026-11-17. That is 10 boards with no margin, below the
  5× rule. It is also the most expensive JLC line ($7.37).
- Evidence: `parts_table.py` line "C1534140 | 2 | SCF20-05-550 | extended | 20".
- Smallest fix: read the JLC BOM page on the order day. If it is short, buy SCF20-05-550 at a distributor and consign
  it. The same applies to C105987 / C492405, whose stock was never read, and to C2888216 (C86 / C117: JLC lists it,
  LCSC says "Part not found").
- Confidence: medium (the stock figure is a week old).

### F5 C69 at the REF3325 minimum load capacitance
- Severity: **note** (same as 04 F5, not tracked in RESOLUTIONS.md)
- What is wrong: REF3325 needs 0.1–10 µF on OUT (SBOS392I §6.5). C69 100 nF X7R ±10 % can be 90 nF.
- Smallest fix: C69 → 1 µF 0603 C15849 (already in the BOM: no new line).
- Confidence: high for the arithmetic; low for a real instability (no data below 0.1 µF).

### F6 Deratings above target that are equal to 5.1 (summary)
- Severity: **note**
- 1 MΩ 0805 dividers at 150 V = 100 % of the 150 V working voltage at 450 V (Uniroyal V.3 p 4); C19 / C30 450 V on
  420–441 V (93–98 %); bulk 450 V at 96 %; C73 450 V MLCC at 89–100 %; ZLLS400 turn-off peak above IFPK 0.85 A (inside
  IFSM 12 A); DB1 at its 2.2 A rating; X5R parts near the FETs (B7). All of these are identical in part and node to the
  bench-verified 5.1, or (C95, D35) copy a 5.1 network. Under the acceptance bar no change is required. Measure the DB1
  temperature at bring-up.
- Confidence: high.

### F7 C10 / C26 receive solder paste
- Severity: **note**
- What is wrong: no part is placed, but the F.Paste Gerber has openings on all four pads (A2). After reflow, two pads
  of each 0603 site carry blobs. A bridge across 0.65 mm is unlikely, but it would short HEATER_I_MEAS / DHB_I_MEAS to
  GND.
- Smallest fix: once the generator can set DNP on the schematic symbols (RESOLUTIONS 14 F10), set the DNP attribute,
  or exclude paste for the two footprints. Or ask JLC in the order remark not to paste unpopulated pads. Inspect C10 /
  C26 after assembly.
- Confidence: high (Gerber flashes found).

### F8 Documentation strings
- Severity: **note**
- V2 / V3 `MIC5205` value with TPS73033 lib_id / device; stale `device` column in `lib/part_map_next.csv` (C22 …
  12061C103KAT2A, Q7 … IRFBE20, Q5 / Q6 IRFP460, C19 EKXJ451…); J2 CSV note "pad 1.0 mm" (board 1.02 mm); SICD / Q5
  notes without the EOL status (E1, E3).

## Compared with 5.1
- **Better:** R68 bleeder now 6 × 97 mW instead of 0.59 W in one 1206; X-cap discharge resistors at 200 kΩ (1.86 s);
  heater resonant caps C0G instead of X7R (value kept under bias, 58 % of 630 V); DAB FETs with 120 V/ns dv/dt
  (IPA60R280CFD7) instead of STF7N60M2; shunts are now fitted by JLC (5.1: a 4 mΩ part not at JLC); 100 nF on HV nodes
  in 630 V 1210 instead of 500 V 1206; local C141 on DRV6 VDDB.
- **Equal:** 1 MΩ 0805 HV dividers at 100 % of the working voltage; 450 V bulk and output electrolytics; C73; ZLLS400
  turn-off networks; DB1 rating; KRL2012 footprint; TO-220 / TO-247 footprints and FET orientation.
- **Worse:** C95 has about a third of 5.1's effective capacitance at the pins (02 F7, still ≥ 3.7× the need) and is
  X5R. **SICD1 / SICD2 lead assignment (F1)**. Q5 / Q6 / SICD parts are now obsolete, which is a sourcing problem and
  not a design one.

## Could not verify
- **Stock and price today for every LCSC number.** The public LCSC / JLC part pages show no stock (script-loaded), and
  the permission system refused the JLC / LCSC API. All stock figures in this review are the CSV's
  (2026-11-17 … 24). C105987 and C492405 were never read.
- Distributor stock and lifecycle of TBS22K-TP / TBS22M-TP (mccsemi.com 403) and Ohmite TWW10J47RE (ohmite.com 418,
  octopart 403).
- Lifecycle of ICE5AR0680AG, IPA60R280CFD7, IPD60R280P7S (Infineon pages did not render the status) and of the
  Chipanalog isolators (not fetched).
- C38 (KEMET R46) and C86 / C117 (Dongtong MKP62) body dimensions: no dimensions on the fetched pages; the LCSC
  datasheet links are HTML wrappers.
- XKB X1321FV drawing (J2): not fetched by me. The CSV quotes rev A0 (Ø0.70 mm).
- Susumu recommended land pattern for KRL2012 (not on catalogue p 51–52).
- C6D04065A pin 1 / case assignment (the drawing text says only "PIN 1 / CASE / PIN 2"; the family convention is
  cathode).
- Ripple current of C64 / C66 (X2 used DC-biased with PFC HF current), C19 / C30 HF current against 1 A, and the
  C105987 dissipation factor (C0G class DF ≤ 0.1 % assumed: ≈ 9 mW at 0.2 A, 214 kHz).
- An exact part number for the 12 blade terminals.

## Outside scope
- **F1 (SICD orientation)**: copper / mechanical work for checklists 05 (PFC) and 12 (heatsink line). Check the
  heatsink-plate side of every TO-220 / TO-247 on the plate against its pin 1 together.
- Checklist 14: C10 / C26 paste openings (F7); rotation preview (C4).
- Checklist 06: `lib/part_map_next.csv` device strings of C22 … C49 (also 06 F8).

## Appendix – rating tables (one row per LCSC number; worst node from `rv sch ref` / section 1 table)

### B1 capacitors on high-voltage nodes
| LCSC | Part | Rated (source) | Worst node | Stress | Verdict |
|---|---|---|---|---|---|
| C107177 | Yageo CC1206JKNPOCBN471 470 pF C0G | 1 kV (CSV; 01 A9) | flyback clamp, ≈ 150–230 V across | ≤ 23 % | PASS |
| C692295 | PSA FM32X104K631EGG 100 nF X7R 1210 | 630 V (CSV, 07 D4 spec sheet) | DC+ / 420V ≤ 450 V | 71 % | PASS |
| C784102 | PSA FS55X105K631EHG 1 µF X7R 2220 | 630 V | half bus ≈ 225 V ± 5 V | 36–40 % | PASS |
| C445674 | TDK C5750X6S2W225KT000N 2.2 µF X6S | 450 V | DC+ 400–450 V | 89–100 % | FAIL (note; as designed / 5.1 part) |
| C105987 | IHHEC C1206N332J631T 3.3 nF NP0 1206 | 630 V (LCSC / JLC page, 2026-11-24) | 200 V + ≤ 165 V swing | 58 % | PASS |
| C22464691 | Ymin KCXE1802E560MF 56 µF | 250 V | −100V BIAS ≤ 100 V | 40 % | PASS |
| C3297747 | KEMET R46KN347000P1K 470 nF X2 | 275 VAC (LCSC page) | 253 Vrms | X2 class | PASS |
| C2888216 | Dongtong MKP62-275V684KP22.5 680 nF X2 | 275 VAC (JLC page) | 253 Vrms | X2 class | PASS (body size open) |
| C3298405 | TDK B32921C3473K289 47 nF X2 | 305 VAC (CSV) | 0…358 V unipolar + HF | 83 % of 431 Vpk | PASS (ripple open) |
| C96522 | TDK CS45-E2GA222M-NKA 2.2 nF | X1 / Y2 300 / 440 VAC (05 A5) | line – PE | class | PASS |

### B2 low-voltage ceramics
| LCSC | Part | Rated | Worst net | Ratio | Effective C |
|---|---|---|---|---|---|
| C6119856 | HRE CGA0603X5R475K250JT 4.7 µF X5R 0603 | 25 V (LCSC) | 15V 15.5 V | 62 % | ≈ 0.9–1.3 µF estimated (02 F7; no curve published) ≥ 240 nF need |
| C14663 | Yageo CC0603KRX7R9BB104 100 nF X7R | 50 V (LCSC) | 15V_ISO_SEC 17.5 V | 35 % | – |
| C6119961 | HRE CGA1206X5R107M100NT 100 µF X5R | 10 V (CSV) | 5V | 50 % | – |
| C12891 | Samsung CL31A226KAHNNNE 22 µF X5R | 25 V | −15V_SEC 16.8 V | 67 % | ≈ 9 µF at 15 V (01 A14) |
| C13585 | Samsung CL31A106KBHNNNE 10 µF X5R | 50 V | 15V | 31 % | – |
| C23630 | Samsung CL10A225KO8NNNC 2.2 µF X5R | 16 V | 3.3 V nets | 21 % | – |
| C15849 | Samsung CL10A105KB8NNNC 1 µF X5R | 50 V | 15V_ISO_SEC | 35 % | – |
| C29823 | FH 1206B475K500NT 4.7 µF X7R | 50 V | 15V | 31 % | – |

### B3 electrolytics
| LCSC | Part | Rated | Node | Ratio | Ripple / life |
|---|---|---|---|---|---|
| C913388 | Ymin KCXE5002W680MF 68 µF | 450 V, 1 A @ 100 kHz, 3000 h @ 105 °C (LCSC page) | 420V ≤ 441 V | 93–98 % | FAIL (note, 5.1 450 V too) |
| C51890374 | Man Yue ERT826M2WI45RRS0F-R 82 µF | 450 V, 1.574 A @ 100 kHz, 5000 h (05 A10) | DC+ ≤ 430 V | 96 % | FAIL (note, as 5.1) |
| C190724 | Panasonic EEEFTE221XAP 220 µF | 25 V, 600 mA, 2000 h (01 A14) | 15V / 15V_ISO_SEC ≤ 17.5 V | 70 % | PASS (ripple at rating at 20 W) |
| C2887274 | KNSCHA RVT 22 µF 35 V D5 × 5.4 | 35 V, 280 mA @ 120 Hz, 2000 h @ 105 °C (LCSC) | VCC ≤ 16 V (OVP 24) | 46 % (69 %) | PASS |
| C432399 | Rubycon 10ZLH1500MEFCT78X20 | 10 V | 6V3 ≤ 7 V | 70 % | ripple open (06 C4) |
| C22464691 | Ymin KCXE 56 µF | 250 V | −100 V | 40 % | PASS |

### B4 resistors
| LCSC | Part | Rated (source) | Worst | Ratio V / P | Verdict |
|---|---|---|---|---|---|
| C17514 | Uniroyal 0805W8F1004T5E 1 MΩ | 150 V work / 300 V overload, 125 mW (V.3 p 4) | 150 V at 450 V | 100 % / 18 % | PASS at limit (as 5.1) |
| C17954 | Uniroyal 1206W4F2003T5E 200 kΩ | 200 V, 250 mW (LCSC; V.3) | 124 Vpk, 39 mW | 62 % / 16 % | PASS |
| C368302 | Walsin WR12X7322FTL 73.2 kΩ | 200 V, 250 mW (LCSC) | 84.4 V, 97 mW | 42 % / 39 % | PASS |
| C26119 / C37800 | Uniroyal 1206 10 MΩ / 4.7 MΩ | 200 V (V.3) | ≤ 168 V at 505 V | 84 % | PASS |
| C17956 | Uniroyal 1206 220 kΩ | 200 V, 250 mW | 105 V, 50 mW | 53 % / 20 % | PASS |
| C245506 | Ever Ohms CR1206F2K61P05Z | 250 mW | 86 mW | 34 % | PASS |
| C3000600 | FOJAN FRC1206F1R37TS 1.37 Ω | 200 V, 250 mW (LCSC) | ≈ 45 mW each | 18 % | PASS |
| C2073455 | Susumu KRL2012E-M-R005-F-T5 | 1 W (LCSC; catalogue) | ≤ 3 A rms → 45 mW | ≤ 5 % | PASS |

### B5 semiconductors
| Part | Rated (source) | Worst | Ratio | Verdict |
|---|---|---|---|---|
| IPA60R280CFD7 (Q7 Q8 Q19 Q21) | 600 V, dv/dt 120 V/ns, VGS ±20 / ±30 V, VISO 2500 Vrms (Rev. 2.2) | 450 V | 75 % | PASS |
| C2M0160120D (Q5 Q6) | 1200 V | ≤ 450 V | 38 % | PASS (obsolete, F2) |
| C3D02060A (SICD) | 600 V (Rev. 10) | ≤ 450 V + overshoot | ≈ 75 % | PASS (obsolete F2; orientation F1) |
| ZLLS400 (D2 D3 D9 D10 D28 D30–D35) | 40 V, IFPK 0.85 A, IFSM 12 A ≤ 100 µs (DS33226 R10-2) | 1.2–4.4 A for ns | > IFPK, ≪ IFSM | FAIL (note, as 5.1) |
| TBS22K (DB1) | 800 V, 2.2 A (JLC page TBS22K-TP) | 2.2 A avg at 540 W | 100 % | FAIL (note, as 5.1) |
| BSS138LT1G (Q9) | 50 V, VGS ±20 V, VGS(th) ≤ 1.5 V (Rev. 15) | 5 V, 3.3 V gate | 10 % | PASS |
