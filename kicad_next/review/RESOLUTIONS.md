# Design review 2026-11-24 – resolutions

Status of every **should-fix / blocker finding** of the twelve reviews in `findings/` (01–11, 14), plus the checklist
FAIL rows that the owner asked to track separately (07 B1). The findings files themselves are not edited. Stages
13a–13d, 14a–14h, 15a–15g and 16a–16b are described in `kicad_next/README.md`; design changes are in
`kicad_next/CHANGES_5_2.md` (section 6 for the 2026-11-24 owner decisions). State: 2026-11-24, after commit
`867ed8c` (Part 2 documents) and this file.

Owner decisions (2026-11-24): mounting hardware at H2 / H4 / H7 / H8 is **nylon** (insulating); **no extra 100 nF on the
DAB primary loop** (loop measured equal or better than 5.1, findings 11 F2); **isolators accepted** (CA-IS3761LW,
CA-IS3721HW); **DAB FETs → IPA60R280CFD7** (stage 15d); **TR3 gapped with tape, Lm tuned on the bench**; no switch-node
capacitor footprints. Open owner measurements: TR1 / TR3 pin diameters and bobbins, L1 / L2 inductance, TR2 turns /
gap / temperature / leakage both ways, heatsinks.

| Review | Finding | One line | Status |
|---|---|---|---|
| 01 | F1 | R68 −100V BIAS bleeder at 0.53–0.59 W in a 250 mW 1206, under C102 | **fixed** – stage 15b (`8606411`): 6 × 73.2k 1206 = 12.2k, 97 mW each, moved away from C102 |
| 01 | F2 | TR1 bobbin pin diameter / base outline / base creepage not measured | **open** – owner measurement (calipers on the bought EEL19 4+6 bobbin); then footprint drills checked (also 14 F2) |
| 01 | F3 | No single TR1 winding spec; Summary / 12.3 show the −5 V build | **fixed** – `fc38d55`: consolidated spec at the top of `simulation/flyback/EEL19_DESIGN.md`, 12.3 / 14.4 marked superseded |
| 01 | F4 | Wrong JLC package string of PWM2 not in the order notes | **fixed** – `867ed8c`: warning in the parts-table review column, printed in `fab/README.md` review notes |
| 02 | F1 | DRV6 VDDB (pin 11) without a capacitor near the pins | **fixed** – stage 15a (`7a1a153`): C141 100 nF X7R 0603 at pins 11 / 9 |
| 02 | F2 | Simulated switch-node slope above the STF7N60M2 dv/dt rating | **fixed by the part change** – stage 15d (`967f47c`): IPA60R280CFD7, 120 V/ns rating vs 62–81 V/ns simulated (1.6–1.9×); scratch-run result, see DAB_SIMULATION.md 2.9 |
| 02 | F3 | Secondary high-side gate track under DRV6, 1.21 mm from the DT pad | **fixed** – stage 14e (`c319958`) |
| 03 | F1 | Isolator rating in the documents is the 2019 value; VDE pending; README names old parts | **accepted by the owner, documents corrected** – `7d45926` (CHANGES 6.a: v1.05 1000 Vrms reinforced, certificates listed; Rev F 600 Vrms noted; VDE scope for the WB part still to confirm) |
| 03 | F2 | R68 bleeder overload (same as 01 F1) | **fixed** – stage 15b |
| 04 | F1 | J2 part C69941 male header, 0.5 mm holes, gender unresolved | **fixed** – stages 15f / 15g (`280fc6f`, `39410c2`): female socket XKB X1321FV-2x25-C43D24 (C2881768), drill 0.70 / pad 1.02 mm. **Open:** owner to check mating height / orientation against the card |
| 04 | F2 | CA-IS3721HW certificates "pending" for a user-accessible barrier | **accepted by the owner** (isolators accepted 2026-11-24); rev C datasheet: all certificates pending (CHANGES 6.a); certified fallback Si8621ED-B-IS (consigned) |
| 04 | F3 | DAB_DIS card pin mis-named (F16 / D15) | **fixed (documents)** – `6f0e231`: J2-18 = card J1-17 = ball R3 in CHANGES 3.3 / OQ 4 and J2_PINOUT.md. **Open:** the card's `power_board_header.csv` update (card repository, owner) |
| 05 | F1 | Mains RES_IN ↔ IN2 only 1.81 mm on F.Cu | **fixed** – stage 14b (`debfa1e`): 3.20 mm |
| 05 | F2 | SICD1 area DC+ / drain necks narrow | **fixed** – stage 14c (`cbb9549`) |
| 05 | F4 | DRV1 / DRV2 VDD capacitors 2.5–4.2 mm from the pins | **fixed** – stage 14f (`a8df12f`) |
| 05 | F5 | X-capacitor discharge 3.5–4.4 s (> 2 s) | **fixed** – stage 15c (`8741f8d`): R4–R6 200k, 1.86 s at 230 V (2.01 s at 264 V without, 1.82 s with the VAC divider). **Open (owner):** 180k if margin at 264 V / +10 % C is wanted |
| 05 | F6 | L1 / L2 inductance not recorded | **open** – owner measurement (L1 / L2), then CHANGES 5.2 value |
| 05 | F7 | Q9 schematic value 2n7000 | **fixed** – `867ed8c`: value BSS138 (schematic + board) |
| 06 | F1 | HEATER_I sense tapped at the Q10 source via | **fixed** – stage 14a (`f51c950`): Kelvin tap at R30 |
| 06 | F2 | SR window / frequency floor tuned on the 5.1 tank | **fixed (documents)** – `6f0e231`: SR window from ≤ 2.2 µs, f_min to ≈ 130 kHz, 13.2 nF C0G (J2_PINOUT.md firmware section). **Open:** TR2 leakage both ways (owner measurement) |
| 06 | F3 | Q14_DRAIN (Q1 drain) copper narrower than 5.1 | **fixed** – stage 14d (`610762a`): tab vias 12 → 16 (width rule met) |
| 07 | F1 | Primary HF commutation loop returns over 22.7 mm of In2 | **accepted by the owner** – no extra 100 nF on the DAB primary loop: loop measured equal or better than 5.1 (findings 11 F2) |
| 07 | F2 | Ringing / snubber: DNP C / RC at the switch node suggested | **resolved by the part change** – stage 15d: the slope is inside the CFD7 rating; no switch-node capacitor footprints (owner) |
| 07 | F3 | Builder documents give the old TR3 gap 0.35 mm | **fixed, then superseded** – `2df3784` (Lm 200 µH), now the owner's tape-gap statement (stage 15d: tape spacer, start Lm ≈ 120 µH ≈ 0.83 mm, tuned on the bench) |
| 07 | B1 (checklist) | TR3 gap text in the builder documents | **superseded** by the tape-gap statement of 2026-11-24 (CSV TR3 note, NEXT_REVISION_PLAN D1, CHANGES 2.1 gap, sheet 7, DAB_TRANSFORMER.md) |
| 07 | F4 | Q8 drain joined to the secondary node through one via | **fixed** – stage 13a (`292a290`) |
| 08 | F1 | HEATER_I sense taps at Q10, not at R30 | **fixed** – stage 14a |
| 08 | F3 (note) | Shunt value undecided; 5 mΩ changes the constants | **fixed** – stage 15e (`476bd33`): 5 mΩ C2073455, scales 9.71 / 4.40 / 2.00 A/V |
| 09 | F1 | VAC scale 0.005 → 0.004 not flagged as a firmware action | **fixed (documents)** – `6f0e231` (CHANGES 4.9, NEXT_REVISION 4.9 / 4b, J2_PINOUT.md) |
| 10 | F1 | Mounting-hole keep-off measured from the ring, not the screw head | **fixed / accepted** – stage 13c (`3dd3160`, no copper ring, 6 mm head) + nylon hardware at H2 / H4 / H7 / H8 (owner) |
| 10 | F2 | Three creepage slots exactly 1.0 mm (JLC ±0.2 mm) | **fixed** – stage 13b (`361b47f`): 1.5 mm |
| 10 | F3 | Primary ↔ heater 410 Vrms → 8.2 mm | **fixed** – stage 13d (`07a9b1a`) |
| 10 | F4 | Heatsink potentials and insulation not defined | **open** – owner (heatsinks: potential, insulation pads, mounting); checklist 12 |
| 11 | F1 | DAB secondary switch node reaches Q8 drain through one via | **fixed** – stage 13a |
| 14 | F1 | Rotations / polarity unverified, JLC polarity check needs silkscreen (blocker, PCBA) | **open** – procedural at the order: JLC placement preview checked part by part (assembly-order preparation, owner) |
| 14 | F2 | Transformer pin drills not confirmed (blocker, bare board) | **open** – owner measurement of TR1 / TR3 pin diameters before ordering |
| 14 | F3 | Three slots exactly 1.0 mm | **fixed** – stage 13b |
| 14 | F4 | Fiducials / edge rails: none, not documented | **open** – assembly-order preparation: state in the order remark / fab README that JLC adds rails and fiducials (checklist 13) |
| 14 | F5 | No assembly drawing / hand-assembly sheet | **open** – assembly-order preparation (checklist 13) |
| 14 | F6 | NPTH mounting-hole copper rings 0.25 mm | **fixed** – stage 13c (no copper ring) |
| 14 | F7 | No ready-to-paste order remark | **open** – assembly-order preparation (checklist 13) |
| 14 | F10 (note) | C10 / C26 (dnp) not flagged DNP on the board | **open** – a board-only DNP flag would be a schematic-parity difference; needs the DNP attribute on the schematic symbols (sheet generator) first; fab files already leave them out (CHANGES 6.b) |
| 14 | F8 | README "anchor off centre" list wrong | **open** – to re-check in `tools/next/jlc_fab.py` with the order preparation (not re-verified here) |
| 12 | F2 | C102 can overlaps a 6 mm screw head at H8 (0.12 mm; 7 mm washer 0.62 mm) | **fixed** – stage 16b: C102 1.25 mm west, can 1.04 mm clear of a 6 mm head and 0.54 mm of a 7 mm washer; TR1 slot-end pour keep-out gave up x 74.5…77.0, y 6.8…18.4 so the pours still reach the pads; C102.1 plane contact one spoke → three (both `starved_thermal` items gone, DRC 139 → 137). H8 keeps nylon hardware (pour edges at 6.27 mm). Washer check of the other holes in README stage 16b: H2 – J4 housing overlaps a 7 mm washer by 0.29 mm (**open**, owner: washer ≤ 6.4 mm at H2), H7 – L1 outline in plan only (toroid high above the board) |
| 13 | F1 | SICD1 / SICD2 reversed when clamped tab-to-plate (C3D02060A pin 1 = cathode on the pad named A) (blocker) | **fixed** – stage 16a: footprint `TO-220-2_Vertical_KA` (pin 1 = K), copper of the two pad sites swapped (cathode on DC+, anode on the drain); DC+ island ↔ trunk F.Cu 1.34 → 2.48 mm neck (5.27 mm at x = 13), PFC_DRAIN_1 neck 2.78 → 3.13 mm, loops 52.6 / 50.5 → 46.4 / 46.7 mm (5.1 46.3 / 44.3). Fab open item: hold a C3D02060A over the sites before soldering. Orientation check of the other parts below |

### 13 F1 follow-up: orientation of every heatsink-mounted / polarised power part (stage 16a, 2026-11-24)

Tab side from the footprint rotation (KiCad TO-220 / TO-247 vertical: pin 1 at local (0, 0), tab on local −y, so
pin 1 is the left lead seen from the front); plate = primary heatsink line x ≈ 5–13 (west row tabs east, east row tabs
west), secondary plate south of Q8 / Q21 (keep-out "Q21 / Q8 to ISO2 under the heatsink plate", y −39.2 … −33).

| Part | Data sheet pins | Board (tab / mark as mounted) | Verdict |
|---|---|---|---|
| Q5 C2M0160120D TO-247-3 (Rev. 07; C3M0160120D Rev. 04 the same: 1 G, 2 D, 3 S, tab D) | 1 G, 2 D, 3 S | rot −90, tab east to the plate: pad 1 (−29.565) GATE1, 2 PFC_DRAIN_1, 3 PFC CURRENT 2+ | OK |
| Q6 same | 1 G, 2 D, 3 S | rot 90, tab west: 1 (3.014) GATE2, 2 PFC_DRAIN_2, 3 PFC CURRENT 3+ | OK |
| SICD1 / SICD2 C3D02060A TO-220-2 (Rev. 10) | 1 K, 2 A, case K | before stage 16a: cathode on the drain | **wrong → fixed** (stage 16a) |
| Q7 / Q19 IPA60R280CFD7 TO-220 FullPAK (Rev. 2.2) | 1 G, 2 D, 3 S | rot 90, tab west: Q7 1 Net-(Q7-G), 2 DHB_HI_SOURCE, 3 DHB_CURRENT; Q19 1 Net-(Q19-G), 2 DC+, 3 DHB_HI_SOURCE | OK |
| Q8 / Q21 same | 1 G, 2 D, 3 S | rot 180, tab south to the secondary plate (as 5.1): Q8 1 Net-(Q8-G), 2 DHB_HI_SOURCE_SEC, 3 ISO_GND; Q21 1 Net-(Q21-G), 2 420V, 3 DHB_HI_SOURCE_SEC | OK |
| DB1 TBS22K (SMD) | symbol 1 AC, 2 +, 3 AC, 4 − | pads 1 AC2, 2 DC+, 3 AC1, 4 GND; footprint, position, rotation and pad nets identical to the bench-verified 5.1 | OK as 5.1 (MCC drawing not fetched: 404 / 403) |
| Q10 / Q11 IPD60R280P7S TO-252 | 1 G, 2 / tab D, 3 S | Q10 1 HEATER_LOW_GATE, tab HEATER_HI_SOURCE, 3 HEATER_CURRENT; Q11 1 HEATER_HI_GATE, tab DC+, 3 HEATER_HI_SOURCE (SMD, cannot be fitted turned) | OK |
| Q1 / Q2 BUK9Y15-60E LFPAK56 | 1–3 S, 4 G, mb D | pad "1" ×3 HT_GND, pad 2 (gate) at the pin-4 end, pad 3 (mb) drain | OK |
| C19 C30 C28 C29 C37 C56 C31 C32 C102 (THT), C1 C2 C58 (SMD) | symbol `C_Polarized` pin 1 = +, footprint pad 1 = + (rect / roundrect) | + on 420V, DC+, 6V3, ISO_GND (C102: −100V BIAS on −), 15V, 15V_ISO_SEC, PWM2 VCC | OK |

## Checklist FAIL rows (not notes) and where they are covered

| Review / row | Covered by |
|---|---|
| 01 A9, A11, A13, D2 | 01 F5 (note), F3, F1, F4 |
| 02 B6 / C3, B7, C1 | 02 F4 / F6 (notes), stage 14h, 02 F1 (stage 15a) |
| 05 A3, A4, B4, C4, C5 | 05 F7 / F10, F5, F2, F4, F1 |
| 06 C5, D5 | 06 F3, F1 |
| 07 B1, C2, D2 | 07 F3 (superseded, above), F1, F4 |
| 08 B1 | 08 F1 |
| 09 E2 | 09 F1 |
| 10 A1, C6, D2 | 10 F3, F2, F1 |
| 11 E4 | 11 F1 |
| 14 A1, B4, B8, C2, D1–D5 | 14 F9 (note: fab README names no git revision), F6, F4, F8, F7 / F5 |

## Open items from this round (not findings)

- **`simulation/dab/dab_spice.py` still models the STF7N60M2**: update the device model to the IPA60R280CFD7 (Coss
  curve; no Infineon SPICE model was available to the scratch check) and re-run the ZVS / loss cases, start-up and the
  ±2 % mismatch at Lm 120 µH / 200 ns (DAB_SIMULATION.md 2.9).
- Bench: TR3 Lm tuning for soft switching at light load, DAB zero-power phase offset and loop gain, ESL-compensation
  tuning of the current channels (5 mΩ), SR window and f_min of the heater LLC, DRV6 VDDB ringing, ISO2 / U11 outputs
  during DAB switching (CMTI margin, CHANGES 6.a).
- Checklists 12 (thermal / mechanical) and 13 (assembly) still to run.
