# Next prompt

Ready-to-paste prompt for the next agent session. Replaced at the end of every phase or session, see
PLAN.md section 9.

State written 2026-11-24, end of the review-resolution session (tube_power 5.2, `kicad_next/`).

---

Continue the tube_power 5.2 board in `/home/jari/dev/tube_psu_kicad` (`kicad_next/tube_psu_5_2.kicad_pcb`, 6 layers).
Read first: this file, `kicad_next/review/RESOLUTIONS.md` (status of every should-fix finding of the twelve reviews),
`kicad_next/review/README.md`, `kicad_next/CHANGES_5_2.md` section 6, `kicad_next/fab/README.md`, and the newest
"Stage" sections at the top of `kicad_next/README.md` (15a–15g).

## Where the design stands

- Fully routed: 0 unconnected, 0 shorts, 0 clearance, 0 dangling, 0 parity, 0 isolation violations; DRC 139 items
  (courtyards_overlap 135, pth_inside_courtyard 2, starved_thermal 2); gate `tools/next/check_next.sh` passes;
  `python3 tools/next/check_creepage.py` (four layer-split passes, ≈ 8 min) 0 violations after the Part-1 board
  changes (stage 15g). Acceptance bar: match the bench-verified 5.1 board and add creepage.
- Twelve design reviews done (`kicad_next/review/findings/` 01–11, 14). Fixes on the board: stages 13a–13d, 14a–14h,
  15a–15g. Owner decisions of 2026-11-24, all in the design:
  - 15a C141 100 nF at DRV6 VDDB; 15b R68 → six 73.2k 1206 (97 mW each); 15c R4–R6 200k (X-cap discharge 1.9 s);
  - 15d DAB FETs Q7 / Q8 / Q19 / Q21 → IPA60R280CFD7 (consigned from the owner's stock), TR3 gapped with tape,
    start Lm ≈ 120 µH (≈ 0.83 mm), DAB dead time 200 ns;
  - 15e shunts 5 mΩ KRL2012E-M-R005-F-T5 (scales PFC 9.71 / DAB 4.40 / heater 2.00 A/V);
  - 15f / 15g J2 = female socket XKB X1321FV-2x25-C43D24, drill 0.70 / pad 1.02 mm;
  - isolators CA-IS3761LW / CA-IS3721HW accepted (ratings and CMTI in CHANGES 6.a);
  - nylon mounting hardware at H2 / H4 / H7 / H8; no extra 100 nF on the DAB primary loop; no switch-node capacitor
    footprints.
- Documents: TR1 winding specification consolidated at the top of `simulation/flyback/EEL19_DESIGN.md`; firmware
  constants and bring-up cautions in `kicad_next/J2_PINOUT.md`.
- Fabrication set: `kicad_next/fab/` from `tools/next/jlc_fab.py` (regenerated after stage 15g; `--check` up to date).
- New one-shot board-edit helpers: `tools/next/s15_common.py` (add / replace footprints from the netlist) on top of
  `s14_common.py`; `tools/next/update_board_parts.py` now also empties an LCSC field the schematic leaves empty.

## Next steps, in order

1. Checklists **12** (thermal / mechanical) and **13** (assembly), one fresh Opus agent each, as described in
   `kicad_next/review/README.md`.
2. **Update `simulation/dab/dab_spice.py` to the IPA60R280CFD7** (it still models the STF7N60M2; the CFD7 check in
   DAB_SIMULATION.md 2.9 is a scratch-run result) and re-run ZVS / losses, start-up and the ±2 % mismatch at
   Lm 120 µH / 200 ns.
3. **Assembly-order preparation** (findings 14 F1, F4, F5, F7, F8): rotations in JLC's placement preview, fiducials /
   rails note, assembly drawing / hand-assembly sheet, ready-to-paste order remark, the parts without a JLC number
   (NOT_ASSEMBLED.md), C10 / C26 DNP (needs the schematic DNP attribute in the sheet generator first).
4. Bench items once a board exists: listed at the end of RESOLUTIONS.md (TR3 Lm tuning, DAB phase offset / loop gain,
   ESL caps, heater SR window / f_min, DRV6 VDDB ringing, isolator outputs during DAB switching).

## Waiting for the owner

- Caliper measurements: TR1 (EEL19 4+6) and TR3 (EC42) pin diameters and bobbin bases against the drills
  (findings 01 F2, 14 F2).
- L1 / L2 inductance; TR2 real turns (64 / 66), gap, winding temperature at 10 / 15 A, leakage both ways.
- Heatsinks: outlines, potential, insulation (findings 10 F4).
- J2 socket against the card: mating height (4.3 mm insulator + card pin length) and orientation / pin 1.
- The CA-IS3761LW VDE certificate scope for the WB part; whether R4–R6 should go to 180k for margin at 264 V.
- The card's `power_board_header.csv`: J2-18 = J1-17 = ball R3 = DAB_DIS, 5.2 ADC map.

## Standing rules

- Push only when the owner says so. Never push the sibling repo `ac_psu_kicad`.
- Subagents run on Opus. KiCad GUI closed before any board edit. RAM under 3 GB: one heavy KiCad job at a time,
  no unsplit creepage DRC, never `pkill -f`, never the KiCad AppImage with `--version`.
- Routing scripts `tools/next/route_s*.py` are one-shot records: never re-run them; new edits go into new
  `route_s16*.py` scripts on a board copy with DRC from the start.
- Commit with explicit paths; never commit `kicad/tube_psu.kicad_pro` or the `.history` directories.
