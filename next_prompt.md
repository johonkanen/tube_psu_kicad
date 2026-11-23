# Next prompt

Ready-to-paste prompt for the next agent session. Replaced at the end of every phase or session, see
PLAN.md section 9.

State written 2026-11-23, end of session (tube_power 5.2, `kicad_next/`).

---

Continue the tube_power 5.2 board in `/home/jari/dev/tube_psu_kicad` (`kicad_next/tube_psu_5_2.kicad_pcb`, 6 layers).
Read first: this file, `kicad_next/review/README.md`, the four findings files in `kicad_next/review/findings/`,
`kicad_next/fab/README.md`, and the newest "Stage" sections at the top of `kicad_next/README.md`.

## Where the design stands

- The board is a fully routed first draft: 0 unconnected, 0 shorts, 0 clearance errors, 0 isolation violations;
  gate `tools/next/check_next.sh`. Acceptance bar: match the bench-verified 5.1 board and add creepage.
- Decisions of 2026-11-23 (all on the board): stackup JLC06161H-7628D; DC+ on outer layers only; mounting hole H5
  removed; J4 1×6 (G, TXD, G, RXD, G, 3V3); UART TX / RX gap 0.61 mm; heater resonant capacitors 4 × 3.3 nF C0G
  (CHANGES 2.9); no switch-node capacitor footprints and no snubber across TR3 (5.1 bar).
- Fabrication set: `kicad_next/fab/` from `tools/next/jlc_fab.py` (Gerbers without silkscreen, drill, BOM, CPL).
- Review: 14 checklists in `kicad_next/review/`. Done by Opus reviewers: 07, 10, 11, 14 (findings committed).
  No blocker in the copper.
- TR2 model check: `simulation/llc/TR2_OPENMAGNETICS.md`.

## In progress when the session ended

One Opus agent block was applying the review fixes, one commit per item, not pushed:

| Item | State at the time of writing |
|---|---|
| A TR3 gap text (Lm about 200 µH) | committed 2df3784 |
| B Q8 drain link: more vias, wider exits | committed 292a290 (stage 13a) |
| C slots under ISO1 / ISO2 / U11 1.0 -> 1.5 mm | committed 361b47f (stage 13b) |
| D mounting holes: copper ring removed, keep-off for a 6 mm screw head | running or not started |
| E primary - heater creepage 8.0 -> 8.2 mm (heater on the -100 V bias: 410 Vrms) | not started |
| after D / E: fab set regenerated, four KiCad creepage passes on the final board | not started |

**First thing next session:** `git log --oneline -12` and `git status --short` to see how far the block got, then
run `tools/next/check_next.sh` yourself. Commits 2df3784, 292a290 and 361b47f have NOT been verified by the main
session. If the working tree has uncommitted board changes, the block was cut off mid-item: inspect before keeping
or discarding (`git diff --stat`), do not assume.

## Next steps, in order

1. Verify the fix block (gate, DRC counts, creepage passes; scratch script in the old session's scratchpad may be
   gone - the method is in `kicad_next/README.md`, "Stage 7" / draft verification: four layer-split passes).
2. Finish items D and E if they are not committed.
3. Regenerate and check the fab set: `python3 tools/next/jlc_fab.py` and `--check`.
4. Run the remaining ten checklists (01 - 06, 08, 09, then 12, 13), one fresh Opus agent each, as described in
   `kicad_next/review/README.md`. Reviewer 06 should also read `simulation/llc/TR2_OPENMAGNETICS.md`.
5. Assembly order preparation: rotations in JLC's preview (67 parts listed in findings 14), fiducials / rails
   note, assembly drawing, order remark, the 14 parts without a JLC number.

## Waiting for the owner

- Caliper measurements: TR1 (EEL19) and TR3 (EC42) pin diameters against the drills (0.9 / 1.0 mm and 1.2 mm),
  L1 / L2 body positions, bobbin data.
- Heatsink outlines, potential and insulation (primary line x 5 - 13; secondary plate at Q21 / Q8), against C73,
  DB1, C87, H4.
- TR2: real primary turns (64 or 66), gap type, winding temperature at 10 A and 15 A, leakage with one secondary
  half shorted.
- TR3 dots and turns before winding; J2-18 check.

## Standing rules

- Push only when the owner says so. Never push the sibling repo `ac_psu_kicad`.
- Subagents run on Opus. KiCad GUI closed before any board edit. RAM under 3 GB: one heavy KiCad job at a time,
  no unsplit creepage DRC, never `pkill -f`, never the KiCad AppImage with `--version`.
- Routing scripts `tools/next/route_s*.py` are one-shot records: never re-run them; the board file is the source
  of truth.
- Commit with explicit paths; never commit `kicad/tube_psu.kicad_pro` or the `.history` directories.
