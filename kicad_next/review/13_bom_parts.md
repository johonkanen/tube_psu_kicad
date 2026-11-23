# Review checklist 13 – BOM and parts: ratings and deratings, footprint vs ordered part, LCSC numbers, stock, consigned parts

You are reviewing **one aspect** of the tube_power 5.2 power-supply board, alone, from this file and the repository
`/home/jari/dev/tube_psu_kicad`. You are doing a design review, not a redesign.

**Rules (full text: `kicad_next/review/README.md`, "Common rules" – read that section first):**
read-only on the repository, the only file you write is `kicad_next/review/findings/13_bom_parts.md`; no commit, no
push; never touch `kicad_next/tube_psu_5_2.kicad_pcb` / `.kicad_pro` and never run a script that saves or
regenerates design files (`route_s*.py`, `update_board_parts.py`, `setup_project.py` / `make_board.py` / generators
without `--check`); do not edit the parts tables in `lib/`; stop if a KiCad lock file exists (`rv guard`); RAM
under 3 GB – no board DRC, no `check_next.sh` (use the existing reports); never `pkill -f`; never run the KiCad
AppImage with `--version`; **the owner's name / e-mail / account stay out of web requests – look parts up by LCSC
number or manufacturer part number only, without logging in anywhere.** **Acceptance bar: match the
bench-verified 5.1 board and add creepage – do not optimise beyond that.** Datasheet and stock facts come from
pages you fetch now (give URL and date), not from memory.

## 1. Scope

The board has **363 schematic parts** and is meant to be assembled by JLCPCB (standard PCBA, both sides) with a
number of parts consigned or hand-fitted. Three hand-maintained tables define what is bought:

| File | Content |
|---|---|
| `lib/jlc_parts_next.csv` | one row per refdes: value, footprint, **lcsc**, mpn, manufacturer, library_type (basic / extended), stock_at_check, unit_price, check_date (2026-11-17 … 23), **status** (exact / equivalent / changed / consigned / missing / dnp), **review** (open remark), note (rating, why this part) |
| `lib/part_map_next.csv` | refdes → symbol, schematic value (source of the value field) |
| `lib/footprint_map_next.csv` | refdes → footprint with a note |

State at the time of writing (`rv sch check`): 363 rows, 0 differences against the netlist; status equivalent 208,
exact 72, changed 50, consigned 17, missing 14, dnp 2; 102 different LCSC numbers; **33 refdes without an LCSC
number** (C10, C26 = DNP; the 12 blade terminals; TR1, TR2, TR3, L1, L2 = wound / consigned; Q5, Q6, Q7, Q8, Q19, Q21,
SICD1, SICD2, DB1, R27 and the four 4 mΩ shunts R21, R30, R83, R93 = "missing / not available at JLC"); stock or
price **not read** for C22, C41, C42, C49 (C105987) and J4 (C492405); 46 rows carry a `review` remark.

This checklist is the systematic pass over **all** parts: (1) is each part electrically adequate for the node it
sits on (voltage, current, power, temperature, tolerance, dielectric) with the usual derating; (2) does the ordered
part fit the footprint on the board; (3) is the LCSC number the part the note says, in stock, and not a
basic / extended surprise; (4) are consigned / missing parts handled; (5) are the three tables, the schematic and the
board consistent. The circuit-specific questions (is 3.3 nF the right value …) belong to checklists 01 – 09; if
their findings files exist in `kicad_next/review/findings/`, read their "parts" items first and do not repeat
calculations they already did – verify and reference them.

Node voltages to rate against (sources: `kicad_next/README.md` "Working voltages and numbers", checklists 01 – 07):

| Net(s) | Highest normal voltage | Notes |
|---|---|---|
| DC+ (to GND) | 400 V nominal, 430 V with ripple / overshoot, 450 V design maximum; flyback LOVP trip 483 V | bulk capacitors are 450 V |
| PFC_DRAIN_1 / 2, DHB_HI_SOURCE, HEATER_HI_SOURCE (to GND) | 0 … DC+ switching, + overshoot | |
| FLY_C | ≈ 600 – 630 V peak (DC+ + reflected 102 V + spike) | PWM2 800 V |
| AC1, AC2, RES_IN, IN2, L1_PRI2, L2_PRI2 | 253 Vrms, 358 V peak, 2.5 kV transients (OVC II) | X2 / Y2 parts |
| HEATER_CAP_MEAS, DHB_CAP | DC+ / 2 ± AC swing | |
| 420V, DHB_HI_SOURCE_SEC (to ISO_GND) | 420 V, 450 V design maximum | |
| "-100V BIAS" | −80 … −84 V nominal, up to ≈ −100 V unloaded | C102 250 V, C45 630 V |
| 15V | 14.2 – 15.5 V | |
| 15V_ISO_SEC | 14.5 – 17.5 V (bleeder only) | |
| −15V_SEC | −14.2 … −16.8 V | |
| 5V / 5V_ISOL | 5.0 V ± 2 % / 4.8 – 5.35 V | |
| 6V3 | 6.3 V, up to ≈ 7 V unloaded | |
| +3V3, AD2_3V3, heater 3.3 V | 3.3 V | |
| gate nets | 0 … 15 V (15V_ISO_SEC: up to 17.5 V); 6.3 V on the SR gates | |

## 2. Read first

1. `lib/jlc_parts_next.csv` header lines (meaning of the columns) and `STATUS.md` section "JLC part numbers"
   (`kicad_next/review/tools/rv headings STATUS.md | grep -i jlc`, then `rv section`).
2. `kicad_next/CHANGES_5_2.md` – every row that names a part number (sections 1 – 5, "Open questions" 2, 8 – 11).
3. `NEXT_REVISION.md` section 3a (driver choices with stock), 5.2b (electrolytics), 5.4, 5.6 (parts JLC cannot
   supply); `OPTIONAL_IMPROVEMENTS.md` section 4 "Parts and sourcing".
4. `kicad_next/README.md` "Footprints and 3D models" → paragraph "Audit against the ordered parts" (package string
   of all LCSC numbers checked 2026-11-18; what was found) and "Stackup" (standard PCBA only).
5. `tools/next/netlist_diff.py` (what its CSV check covers) and, if present, `tools/next/jlc_fab.py` and
   `kicad_next/fab/` (BOM / CPL as generated – details are checklist 14).
6. External: the LCSC / JLCPCB part page of each LCSC number you examine (public pages, by number), the
   manufacturer datasheets, JLCPCB's assembly capability page (minimum package, standard vs economic PCBA,
   consigned-parts rules).

## 3. How to extract facts

```sh
kicad_next/review/tools/rv guard && kicad_next/review/tools/rv setup
kicad_next/review/tools/rv sch check                     # netlist vs lib/jlc_parts_next.csv; status counts; parts without LCSC
kicad_next/review/tools/rv sch kind C                    # every capacitor: value, footprint, nets, lcsc, mpn, status, stock, review, note
kicad_next/review/tools/rv sch kind R
kicad_next/review/tools/rv sch kind D
kicad_next/review/tools/rv sch kind Q
kicad_next/review/tools/rv sch kind U
kicad_next/review/tools/rv sch kind DRV
kicad_next/review/tools/rv sch kind ISO
kicad_next/review/tools/rv sch kind V
kicad_next/review/tools/rv sch kind C | grep -E "DC\+|420V|BIAS|AC1|AC2|IN2|RES_IN|PRI2|DHB_CAP|TRANS_SEC|HEATER_CAP|FLY_C|PE"
kicad_next/review/tools/rv sch kind R | grep -E "DC\+|420V|BIAS|AC1|AC2|IN2|RES_IN|Pad[12]\)" | head -60
kicad_next/review/tools/rv sch part C95,R68,C73           # full rows of the three tables for single parts
python3 tools/next/netlist_diff.py --check               # the project's own netlist / CSV check (read-only with --check)
python3 kicad_next/review/tools/parts_table.py           # the table by LCSC number (lowest stock first), review remarks, one-LCSC-two-values check
python3 kicad_next/review/tools/parts_table.py board     # board fields (Value, footprint id, LCSC, DNP) against the table
kicad_next/review/tools/rv bq fp PWM2,U1,U10,DRV1,Q10,Q1,R83,C58,DB1 | grep -v "^   pad"     # footprint ids actually on the board
ls kicad_next/fab 2>/dev/null
```

Looking parts up: `https://www.lcsc.com/product-detail/<LCSC number>.html` and the JLCPCB parts page for the same
number show package, datasheet link, stock and whether the part is basic / extended / preferred. Stock moves daily:
record the date and the number you saw next to `stock_at_check`.

## 4. Checklist

### A. Consistency of the tables, schematic and board

- **A1** `rv sch check` → 0 differences; `python3 tools/next/netlist_diff.py --check` passes. PASS: both.
- **A2 Board fields.** `python3 kicad_next/review/tools/parts_table.py board`: Value, footprint id and LCSC field of
  every board footprint equal the table; DNP flags agree. PASS: 0 field differences. At the time of writing the
  script reports **C10 and C26: status dnp in the table, but the DNP attribute is not set on the board
  footprints** – check how the fab BOM / CPL treats them (`kicad_next/fab/NOT_ASSEMBLED.md`, the BOM): if they
  would be placed (value "na", no LCSC number → JLC drops them anyway) it is a note; if a BOM line "na" could
  confuse the order it is a should-fix.
- **A3 One LCSC number = one part.** `parts_table.py`: the "CHECK same LCSC" lines. PASS: none, or the differing
  value strings are the same part written differently (e.g. `33` / `33R`, `100` / `100R`, `2u2` / `2.2u`, `470pF` /
  `470pf`); list value-string inconsistencies as a documentation note (BOM grouping by value would split them).
- **A4 Status semantics.** For each status class give the count and what will physically happen at assembly:
  exact / equivalent / changed → placed by JLC; consigned → supplied by the owner to JLC or hand-fitted (which?);
  missing → no source in the table (who buys them, where – 14 parts: list them); dnp → not fitted. PASS: every
  part has exactly one defined supply route written in a repository document; FAIL (should fix) if "missing"
  parts have no stated source.
- **A5 Review column.** Go through all 46 remarks (`parts_table.py` output). For each: still open? resolvable now by a
  lookup (e.g. "stock / price not read", "body size to verify", "check gender / height", "reinforced certificate
  to confirm")? PASS per remark when closed with evidence; the rest go to "Could not verify" with what is needed.

### B. Ratings and derating (systematic tables)

For B1 – B6 build a table (one row per LCSC number, not per refdes) with: part, rated value from the fetched
datasheet / LCSC page, the worst node it is used on (from `rv sch kind …` nets and the voltage table of section 1),
stress ratio, verdict. Derating targets used here: ceramic / film capacitor voltage ≤ 80 % of rating (≤ 100 % only if
5.1 had the same part and node), electrolytic voltage ≤ 90 %, resistor power ≤ 60 % and voltage ≤ 100 % of the
element's rated working voltage, diode reverse voltage ≤ 80 %, MOSFET VDS ≤ 80 %, IC supply ≤ recommended maximum.

- **B1 Capacitors on high-voltage nodes.** The `kind C | grep` command of section 3: C12 (470 pF C0G 1 kV on the
  flyback clamp), C15 / C20 / C67 / C70 / C45 / C89 – C91 / C99 – C101 (100 nF X7R 630 V 1210, C692295), C47 / C54 / C16 / C55
  (1 µF X7R 630 V 2220, C784102), **C73 (2.2 µF X6S 450 V on a 400 – 450 V bus: 89 – 100 %)**, C22 / C41 / C42 / C49
  (3.3 nF C0G 630 V 1206), bulk C28 / C29 / C37 / C56 (450 V), C19 / C30 (KCXE5002W680MF: the note says 450 V – confirm
  the voltage code from the Ymin datasheet), C102 (250 V on ≤ 100 V), X2: C86 / C117 (275 VAC, 680 nF, generic
  brand), C38 (470 nF 275 VAC KEMET R46), C64 / C66 (47 nF 305 VAC) – **C64 / C66 sit from AC1 / AC2 to GND, i.e.
  across the low-side bridge diodes: they see the rectified half wave (0 … 358 V unipolar) plus PFC HF ripple
  current, not line-to-line AC: is an X2 film capacitor rated for that DC-biased use and the HF current?
  (5.1 has the same circuit; the part changed from Kemet R46 to TDK B32921.)** Y2: C65, C81, C82, C84, C85
  (CS45-E2GA222M: X1 / Y2 300 / 440 VAC). PASS per the derating targets; safety capacitors must carry the class
  marking (X2 / Y2) and approvals in the datasheet.
- **B2 Low-voltage ceramics – DC bias.** 22 µF / 100 µF in 1206 (C6, C36, C71, C114, C115, C40), 10 µF 1206 on 6V3 and
  15V (C8, C9, C18, C23, C24, C33: X5R 50 V), 4.7 µF 0603 X5R 25 V on 15 V (C95, C52, C79, C80 – known open point:
  derating not calculated) and on 6V3 (C17), 4.7 µF 1206 X7R 50 V, 2.2 µF / 1 µF 0603. For each LCSC part: rated
  voltage, dielectric, effective capacitance at its bias from the manufacturer's curve (fetch it; if none, use a
  curve of an equivalent Murata / Samsung part and say so). PASS: voltage ≤ 80 % of rating; effective capacitance
  ≥ 50 % of nominal where the circuit needs the value (driver bypass, LDO stability), with the numbers.
  "C71 100u" on the 5V rail in a 1206: which part, which voltage rating (6.3 V on 5 V = 79 %)?
- **B3 Electrolytics.** C1 / C2 (EEEFTE221XAP 220 µF 25 V on 15 V / 15V_ISO_SEC ≤ 17.5 V), C58 (22 µF 35 V on VCC ≤ 16 V,
  OVP 24 V), C31 / C32 (1500 µF 10 V on 6.3 V), C102, C19 / C30, bulk: ripple current vs rating at 105 °C, life at
  the temperatures of checklist 12, voltage ratio. PASS per targets; quote the ripple numbers from checklists
  01 / 05 / 06 / 07 if their findings exist, else from the documents.
- **B4 Resistors: power and voltage.** `rv sch kind R`: (a) HV dividers and bleeders – 1 MΩ 0805 chains on DC+ / 420V /
  AC (R10, R15, R16, R23, R34, R39, R47, R48, R50 – R52, R79, R109, R111, R112, R118 – R120: 133 – 150 V dc or 124 V peak
  each – rated working voltage of UNI-ROYAL 0805W8F1004T5E?), 4.7 MΩ / 10 MΩ 1206 start-up / LOVP chains (133 –
  160 V each), 470 k discharge R4 – R6 (108 Vrms each), 220 k 1206 balancing R143 – R150, R155 – R158 (100 – 105 V,
  45 – 50 mW), R45 1 MΩ 1206 on the clamp (≈ 115 V), **R68 12.1 k 1206 on the −100 V bias (≈ 0.55 – 0.6 W at 82 – 84 V:
  far above a 0.25 W 1206 – confirm the arithmetic and what 5.1 fitted)**, R124 2.61 k (86 mW), R125 2.2 k
  (0.1 W), R67 / R123 / R126; (b) gate resistors (pulse power), R41 / R46 / R99 2 Ω bootstrap, R8 / R9 1.37 Ω current
  sense (≈ 0.09 W total), R142 10 Ω, R136 / R137 47 Ω; (c) shunts 4 mΩ. PASS per targets; every FAIL with the
  smallest fix (a higher-rated part in the same footprint from the JLC list, or two footprint-compatible
  options).
- **B5 Semiconductors.** Diodes: ES1D 200 V (D4, D5, D6, D14, D29), US1M 1000 V (D8), S1M 1000 V standard recovery
  (D7 clamp, D11 / D18 / D19 bootstrap), ZLLS400TA 40 V Schottky (gate turn-off, D2 / D3, D9 / D28, D10).
  MOSFETs: STF7N60M2 600 V on 400 – 450 V (67 – 75 %), C2M0160120D 1200 V, IPD60R280P7S 600 V on 400 V,
  BUK9Y15-60E 60 V on ≈ 13 – 20 V, BSS138 (Q9) 50 V. SiC diodes C3D02060A 600 V / 2 A. Bridge TBS22K. PASS per
  targets with the node voltages of section 1 (reverse voltages of the flyback rectifiers from checklist 01
  A10).
- **B6 ICs: supply and absolute maximums.** UCC21520 (VDD up to 17.5 V on DRV6), UCC27511A (15V), UCC27524A (6V3),
  CA-IS3761LW / CA-IS3721HW (3.3 V both sides), ICE5AR0680AG, LMH6643 (3.3 V: minimum supply 2.7 V), TLV316,
  TLV9062, ADC121S101, MIC5205-3.3 (V_in 16 V max; AD1 side fed from 6V3 through two diodes), TPS73033 (5.5 V
  max in – the 5V rail is regulated to 5.0 V ± 2 %; light-load excursion?), REF3325. PASS: every supply inside
  the recommended range in all documented operating cases; list the smallest margins.
- **B7 Temperature range.** Every IC / capacitor / relay rated to ≥ 85 °C ambient-equivalent given the 70 °C rack
  design case (design document p 34) + self-heating; electrolytics 105 °C types; X7R vs X5R (85 °C) near hot
  parts – C95 / C52 / C79 / C80 are **X5R** next to gate drivers and the heatsink line. PASS or list of parts
  with ≤ 85 °C rating within 10 mm of a part dissipating more than 0.5 W (use `rv bq area … --touch`).

### C. Ordered part vs footprint on the board

- **C1 Re-run the package audit for parts changed since 2026-11-18.** README "Audit against the ordered parts"
  covered 98 LCSC numbers on 2026-11-18. Since then changed / added: PWM2 → ICE5AR0680AG (C17699638; JLC package
  string "BSOP-12-EP-300mil" is wrong – the footprint is a 3.9 mm SO-12 without exposed pad), C95 → 0603
  (C6119856), C22 / C41 / C42 / C49 → C105987 (1206), J4 → C492405 (1×6 header), C58 (C2887274, 5 × 5.4 SMD
  electrolytic), R8 / R9 (C3000600), R114 – R116 (C37800), R151 – R153 (C26119), R154, R138 – R141, C138 – C140,
  R155 – R158, R123, C40 (C12891). For each: package on the LCSC page = footprint id on the board
  (`rv bq fp REF`). PASS: all match.
- **C2 Polarised and multi-pin parts: pin 1 / polarity vs footprint numbering.** The board keeps several 5.1
  "Proteus" footprints whose pad numbers follow the Proteus symbols, not the manufacturer pin numbers:
  `tube_psu:SOT-23_Proteus` (REF1, Q9), `SOT-23-5_Proteus` (U2, U3, U6, U8, V2, V3, V4), `SOT-23-6_Proteus` (AD1,
  AD2), `D_SMA_AC` / `D_SOD-323_AC` (pads named A / C), `LFPAK56_Proteus` (Q1, Q2), `Relay_Songle_SRD_5pin`,
  `D_Bridge_TBS`, `TO-220-2_Vertical_AK`. They are proven on 5.1 **for the 5.1 parts**. For every such footprint
  whose part number changed in 5.2 (REF1 ISL21010 → REF3325; Q9 "2n7000" → BSS138 per the table; the diodes'
  values) compare the physical pad positions (`rv bq fp REF1,Q9`) with the new part's package drawing and the
  netlist pin functions (`rv sch ref REF1,Q9`). PASS: physical lead ↔ net is right for the ordered part;
  a mismatch is a **blocker**.
- **C3 Footprint / package pairs flagged in the documents.** LMH6643MMX (VSSOP-8) on `TSSOP-8_3x3mm_P0.65mm`
  ("user-accepted"); IPD60R280P7S (TO-252-3) on `TO-252-2`; C1 / C2 on `CP_Elec_6.3x7.7_EEEFTE221XAP`; KRL2012 on
  `R_0508_1220Metric_KRL2012`; C38 body width vs the 6 mm outline; C86 / C117 generic 680 nF body vs 26.5 × 11.5
  (fetch the dimensions by LCSC number); J2 header gender / height; the THT electrolytics' diameter × pitch.
  PASS: dimensions from the fetched datasheet fit the footprint (pad pitch within ± 0.2 mm, body inside the
  courtyard); list each with numbers.
- **C4 CPL rotation risks.** Parts whose JLC library orientation commonly differs from KiCad's (SOT-23-x, SOIC,
  electrolytic SMD, diodes, the SO-12, LFPAK, DPAK): are rotation offsets handled in the fab script
  (`grep -n -i "rot" tools/next/jlc_fab.py` if it exists)? PASS / note for checklist 14.

### D. Sourcing

- **D1 Stock today.** For every LCSC number with `stock_at_check` below 500 or empty, and for the 20 most
  expensive lines, fetch today's stock and price (public LCSC / JLC page by number). Known low: R124 2.61 k C245506
  (75), C19 / C30 C913388 (103), CM1 / CM4 C1534140 (20 → "10 boards max"), AD1 / AD2 C74860 (276), V2 / V3 C37970
  (673), C73 C445674 (758), C102 (386), PWM2 (public stock 3; the owner holds 10 in his JLC parts stock),
  C22 … C49 and J4 "not read". PASS per line: stock ≥ 5 × the quantity for the build size (assume 5 boards unless
  a number is documented), else finding with an alternative part number in the same footprint if one exists.
- **D2 Basic vs extended.** Count extended parts (each adds a JLC feeder fee); note only – unless a basic
  equivalent with identical ratings exists for a high-count line.
- **D3 Consigned / missing parts.** For Q5 / Q6 (C2M0160120D), Q7 / Q8 / Q19 / Q21 (STF7N60M2), SICD1 / 2 (C3D02060A), DB1
  (TBS22K), R27 (TWW10J47RE), the 4 mΩ KRL2012 shunts (or the stocked 5 mΩ C2073455: +25 % current gain – a
  firmware-visible change, see checklist 08), TR1 / TR2 / TR3 / L1 / L2, the blade terminals: is the part still
  manufactured (not obsolete / NRND – check the manufacturer page), and where does the owner get it (he has
  5.1 boards: reuse?). PASS: each is either in stock at a distributor today (name it, no login needed) or
  documented as on hand; obsolete parts are findings with a replacement candidate of the same footprint and
  ratings.
- **D4 Lifecycle of the new 5.2 ICs.** UCC21520DWR, UCC27511ADBVR, UCC27524ADR, CA-IS3761LW, CA-IS3721HW,
  ICE5AR0680AG, LMH6643MMX, TLV9062IDGKR, REF3325AIDBZR, IPD60R280P7S: active status on the manufacturer page.
  PASS: all active.
- **D5 Isolation certificates (known open point).** CA-IS3761LW / CA-IS3721HW: certification status (VDE 0884-17 /
  UL 1577 / CQC) from the current datasheet or the manufacturer's certificate page. PASS: certificate numbers
  found; otherwise CANNOT VERIFY (it is also item A5 of checklist 03 and D6 of checklist 04 – one finding, not
  three).

### E. Documentation of values

- **E1 Schematic value strings.** `rv sch kind R`, `kind C`: inconsistent notations (`33` vs `33R`, `12.1K` vs
  `2.61k`, `470nF` / `470pF` / `470pf` / `2u2` / `2.2u`, `na` for DNP, "SONGLE RELAY", "50 PIN HEADER 50TH", Q9
  "2n7000" while the BSS138 is ordered, V2 / V3 "MIC5205" without the 3.3 V suffix, U1 / U4 "LMH6643"). PASS for
  function; list as documentation notes those that could cause a wrong part to be bought by someone using
  only the schematic (Q9, V2 / V3, L1 / L2 "TBD (measured)", the four shunts "4m").
- **E2 Parts whose rating is only in the table note.** Voltage ratings of HV capacitors / resistors are not in
  the schematic value field (only C28 … "82u 450V", C40 "22u 25V", C58, C102 carry them). Note; suggest nothing
  beyond "the table is the BOM source".
- **E3 Table notes that contradict the design documents.** Read the `note` column of the changed / consigned rows
  against CHANGES_5_2.md. Example to verify: TR3's note says "gap 0.35 mm" while CHANGES row "2.1 gap" says
  Lm ≈ 200 µH, ≈ 0.66 – 0.68 mm centre-leg grind (0.335 mm only as a spacer under all legs). PASS: no note states
  a superseded value; list each stale note.

## 5. Out of scope / given

- Whether a value is right for the circuit (checklists 01 – 09); layout (10 – 12); the format of the fab BOM / CPL
  (14).
- Given: the part choices listed in CHANGES_5_2.md as owner decisions (UCC21520 / UCC27511A / UCC27524A,
  CA-IS3761LW / CA-IS3721HW, ICE5AR0680AG, LMH6643, IPD60R280P7S, C95 0603 X5R 25 V, 4 × 3.3 nF C0G, C73 as is,
  consigned semiconductors and magnetics) – check their ratings and sourcing, do not propose different
  architectures. JLC standard PCBA; no silkscreen; via-in-pad is fine.

## 6. Findings format

Write `kicad_next/review/findings/13_bom_parts.md` exactly in the format of `kicad_next/review/README.md` "Common
findings format": summary; one table row per item above (A1 … E3) with **PASS / FAIL / CANNOT VERIFY** and the
evidence (file:line, command + output lines, calculation with inputs, or datasheet / part page with URL and date);
ranked findings with severity (**blocker for ordering / should fix / note**), what is wrong, evidence, smallest
fix, confidence; "Compared with 5.1"; "Could not verify"; "Outside scope". Attach the rating tables of section B
as an appendix in the same file. "Looks fine" without evidence is not acceptable.
