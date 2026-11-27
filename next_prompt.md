# Next prompt

Ready-to-paste prompt for the next agent session. Replaced at the end of every phase or session, see
PLAN.md section 9.

State written 2026-11-24, end of the review-resolution session (tube_power 5.2, `kicad_next/`).

---

Continue the tube_power 5.2 board in `/home/jari/dev/tube_psu_kicad` (`kicad_next/tube_psu_5_2.kicad_pcb`, 6 layers).
Read first: this file, `kicad_next/review/RESOLUTIONS.md` (status of every should-fix finding of the twelve reviews),
`kicad_next/review/README.md`, `kicad_next/CHANGES_5_2.md` section 6, `kicad_next/fab/README.md`, and the newest
"Stage" sections at the top of `kicad_next/README.md` (18c … 15a).

## Session 2026-11-25 (status check only, no design change)

- Re-verified at `1e37a8a`: `tools/next/check_next.sh` ALL PASSED, `jlc_fab.py --check` up to date. Creepage not
  re-run: stages 18a–18c moved no copper, so the 0-violation result from stage 17b stands.
- Pre-order checklist made. **Blockers for the bare board:** (1) TR1 / TR3 pin diameters vs drills (14 F2),
  (2) caliper check of C2M0160120D / C3D02060A / IPA60R280CFD7 for the heatsink plate (12 F1), (3) J2 mating height
  and orientation against the card. **Decide before ordering:** use 5.1 spares or substitutes for Q5 / Q6 / SICD1 /
  SICD2 (check substitute pin-outs against `TO-220-2_Vertical_KA`); fit of C38 / C86 / C117; land pattern of the
  5 mΩ shunts. **At the order:** `fab/ROTATION_CHECK.md` in JLC's preview, stock on the day (C105987, J4, CM1 /
  CM4 = 20), THT decision, stackup name, J2 annular ring 0.159 mm, JLC Gerber viewer / DFM. Can wait: dab_spice CFD7
  update, bench items.
- Stale line to fix: `RESOLUTIONS.md` "Checklists 12 (thermal / mechanical) and 13 (assembly) still to run". Both
  have been run.
- KiCad MCP server (`~/dev/KiCAD-MCP-Server`, KiCad 10.0.7 Python through `kicad10_python.sh`) registered for this
  project, local scope (`claude mcp get kicad`). Its tools load in a new session.

## Session 2026-11-27 (no copper change)

- Creepage slots re-checked against the pads and domains: all five correctly placed, `check_domains.py` 0 below limit.
- **14 F2 closed**: owner says TR1 / TR3 square pins are just below the limits for the existing 0.9 / 1.0 / 1.2 mm
  drills; drills unchanged (RESOLUTIONS, README, `jlc_fab.py` notes → `fab/HAND_ASSEMBLY.md`). Stale "checklists 12 / 13
  still to run" line removed.
- Owner will hand-solder the large parts and choose Q5 / Q6 / SICD1 / SICD2 on the bench (TO-247-3 G-D-S,
  TO-220-2 KA = pin 1 / tab cathode; DSC04C065 checked compatible). The plate is made after the parts are chosen, so
  the package caliper check is no longer an ordering blocker. **Only remaining bare-board blocker: J2 mating height /
  orientation against the card.** Then the order-time items (SMD-only assembly, rotation check, stock, stackup, DFM).

## Where the design stands

- Fully routed: 0 unconnected, 0 shorts, 0 clearance, 0 dangling, 0 parity, 0 isolation violations; DRC 138 items
  (courtyards_overlap 136, pth_inside_courtyard 2); gate `tools/next/check_next.sh` passes;
  `python3 tools/next/check_creepage.py` (four layer-split passes, ≈ 8 min) 0 violations after stage 17b. Acceptance bar: match the bench-verified 5.1 board and add creepage.
- All fourteen design reviews done (`kicad_next/review/findings/` 01–14). Fixes on the board: stages 13a–13d,
  14a–14h, 15a–15g, 16a–16b, 17a–17b, 18a–18c. **Stage 16a fixed a blocker found by review 13: SICD1 / SICD2 were reversed for a diode
  clamped tab-to-plate (cathode on the PFC drain); new footprint `TO-220-2_Vertical_KA`, copper swapped. Boards must
  not be made from any revision before d3be2f7.** Stage 16b moved C102 clear of the H8 screw head. Stages 17a / 17b put the primary heatsink line on one flat plate (SICD2 pins x 3.40, Q19 / Q7 pins x 11.60, DRV5 group 0.85 mm west). Owner decisions of 2026-11-24, all in the design:
  - 15a C141 100 nF at DRV6 VDDB; 15b R68 → six 73.2k 1206 (97 mW each); 15c R4–R6 200k (X-cap discharge 1.9 s), 18a R4–R6 180k (1.81 s at 264 V) and C69 1 µF at REF3325;
  - 15d DAB FETs Q7 / Q8 / Q19 / Q21 → IPA60R280CFD7 (consigned from the owner's stock), TR3 gapped with tape,
    start Lm ≈ 120 µH (≈ 0.83 mm), DAB dead time 200 ns;
  - 15e shunts 5 mΩ KRL2012E-M-R005-F-T5 (scales PFC 9.71 / DAB 4.40 / heater 2.00 A/V);
  - 15f / 15g J2 = female socket XKB X1321FV-2x25-C43D24, drill 0.70 / pad 1.02 mm;
  - isolators CA-IS3761LW / CA-IS3721HW accepted (ratings and CMTI in CHANGES 6.a);
  - nylon mounting hardware at H2 / H4 / H7 / H8; no extra 100 nF on the DAB primary loop; no switch-node capacitor
    footprints.
- Documents: TR1 winding specification consolidated at the top of `simulation/flyback/EEL19_DESIGN.md`; firmware
  constants and bring-up cautions in `kicad_next/J2_PINOUT.md`.
- Fabrication set: `kicad_next/fab/` from `tools/next/jlc_fab.py` (regenerated after stage 18c with rotation check list, hand-assembly sheet, order remarks and assembly drawings; `--check` up to date).
- New one-shot board-edit helpers: `tools/next/s15_common.py` (add / replace footprints from the netlist) on top of
  `s14_common.py`; `tools/next/update_board_parts.py` now also empties an LCSC field the schematic leaves empty.

## Next steps, in order

1. Heatsink line (findings 12 F1, F3): **board side done** (stages 17a / 17b): SICD2 pins x 3.40, Q19 / Q7 pins
   x 11.60 (DRV5 group 0.85 mm west). Nominal back faces west Q5 6.15 / SICD2 5.99, east Q6 8.99 / SICD1 9.22 /
   Q19 / Q7 8.96; flat plate 2.34 - 2.56 mm with 0.25 mm pads under Q5 / Q6 / SICD1 / SICD2 only (README stage 17b).
   Still open: the owner's caliper check of the three packages, plate cut-out at the H4 head, notch at C87, plate
   potential and tab insulation (fab README open items).
2. **Update `simulation/dab/dab_spice.py` to the IPA60R280CFD7** (it still models the STF7N60M2; the CFD7 check in
   DAB_SIMULATION.md 2.9 is a scratch-run result) and re-run ZVS / losses, start-up and the ±2 % mismatch at
   Lm 120 µH / 200 ns.
3. **Assembly-order preparation: done** (stages 18b / 18c): `kicad_next/fab/` now holds `ROTATION_CHECK.md`,
   `HAND_ASSEMBLY.md`, `ORDER_REMARK.md` and the assembly drawings; rails / fiducials note and anchor list in the fab
   README; C10 / C26 DNP. **Left for the owner at the order:** tick off `ROTATION_CHECK.md` in JLC's placement preview
   (the rotation corrections and the bottom-side rule come from the common KiCad → JLC tools and are not verified),
   decide the 24 THT parts in the BOM, the parts with status `missing`, paste the remarks, "confirm production file".
4. Bench items once a board exists: listed at the end of RESOLUTIONS.md (TR3 Lm tuning, DAB phase offset / loop gain,
   ESL caps, heater SR window / f_min, DRV6 VDDB ringing, isolator outputs during DAB switching).

## Waiting for the owner

- Caliper measurements of one C2M0160120D, one C3D02060A and one IPA60R280CFD7 (lead centreline to back face, body
  thickness) to confirm the plate thickness of stage 17b (datasheet nominal values used); C102 can diameter; screw-head / washer sizes at H2 and H8.
- Physical check before soldering: a C3D02060A held over SICD1 / SICD2 with the tab to the plate has its cathode
  (pin 1, tab) on the DC+ pad.
- Q5 / Q6 (C2M0160120D) and SICD1 / SICD2 (C3D02060A) are obsolete at Wolfspeed: 5.1 spares, or C3M0160120D /
  C6D04065A (diode pin-out to check).
- Caliper measurements: TR1 (EEL19 4+6) and TR3 (EC42) pin diameters and bobbin bases against the drills
  (findings 01 F2, 14 F2).
- L1 / L2 inductance; TR2 real turns (64 / 66), gap, winding temperature at 10 / 15 A, leakage both ways.
- Heatsinks: outlines, potential, insulation (findings 10 F4).
- J2 socket against the card: mating height (4.3 mm insulator + card pin length) and orientation / pin 1.
- The CA-IS3761LW VDE certificate scope for the WB part.
- The card's `power_board_header.csv`: J2-18 = J1-17 = ball R3 = DAB_DIS, 5.2 ADC map.

## Standing rules

- Push only when the owner says so. Never push the sibling repo `ac_psu_kicad`.
- Subagents run on Opus. KiCad GUI closed before any board edit. RAM under 3 GB: one heavy KiCad job at a time,
  no unsplit creepage DRC, never `pkill -f`, never the KiCad AppImage with `--version`.
- Routing scripts `tools/next/route_s*.py` are one-shot records: never re-run them; new edits go into new
  `route_s16*.py` scripts on a board copy with DRC from the start.
- Commit with explicit paths; never commit `kicad/tube_psu.kicad_pro` or the `.history` directories.
