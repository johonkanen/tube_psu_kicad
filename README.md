# tube_psu_kicad

Migration of the **tube_power_5_1** board ("Tube power supply", V5.1) from Proteus 8.12
to KiCad 10. The KiCad schematic is redrawn from the Proteus PDF, and the PCB is rebuilt
from the Proteus gerbers, so that every pad, track, via and pour carries a net from the new
schematic. The goal is a KiCad design that is **electrically identical** to the Proteus
original.

The Proteus project file is binary and cannot be read, so the IPC-D-356A netlist in the
CADCAM export is the reference: 193 nets, 315 parts, 1165 pad/via/hole records, each with
net, refdes, pin and coordinates. Every check in this repo compares against that file.

The method follows `tools/p2k/CONVERSION_PLAYBOOK.md`. The tools are the shared
[proteus2kicad](https://github.com/johonkanen/proteus2kicad) repository, a git submodule in
`tools/p2k` (clone with `git clone --recurse-submodules`, or run
`git submodule update --init`); everything specific to this board is in `p2k_config.py`.

- `PLAN.md`: the plan, inventory of the source files, risks and model usage.
- `STATUS.md`: what is done, the last verification output, findings about the original
  design, and what comes next.
- `next_prompt.md`: the prompt for the next work session, replaced at the end of every
  phase.

## Layout

```
source/      Proteus exports (read-only): schematic PDF + page renders + text, the .pdsprj,
             cadcam/ = Gerber X2 export with drill gerbers and IPC-D-356A netlist (used),
             cadcam_rs274x/ = earlier RS-274X export with Excellon drill (cross-check only)
reference/   tables generated from the IPC netlist: pads (CSV/JSON), pin→net per part,
             pins per net
lib/         project symbols / footprints, part and footprint maps (Phase 1-2)
kicad/       KiCad project (Phase 1-3)
p2k_config.py  board configuration of the proteus2kicad tools
tools/       check_all.sh, erc.sh, board-specific scripts; p2k/ = proteus2kicad submodule
reports/     generated reports
```

## Phases

| Phase | Content | State |
|---|---|---|
| 0 | Tooling: KiCad AppImage wrappers, IPC-D-356A parser, reference tables, X2 export check | done |
| 1 | Schematic: symbols, part map, netlist comparison, 11 sheets redrawn | – |
| 2 | Footprints, fitted to the IPC pads | – |
| 3 | PCB: board, tracks/vias from gerbers, nets, zones, DRC | – |
| 4 | Independent verification: gerber round trip, IPC-D-356 diff | – |

## Checks

`tools/check_all.sh` runs every check and prints `ALL CHECKS PASSED` or the failing steps.

| Script | Checks |
|---|---|
| `tools/p2k/bin/p2k ipc356 --check` | IPC parser counts and fix-ups; reference tables up to date |
| `tools/p2k/bin/p2k check_sources` | Gerber X2 flashes (vias, pads, free pads, holes) and drills vs IPC; outline |

`tools/p2k/bin/p2k ipc356` regenerates `reference/` after a change of `p2k_config.py`.

## KiCad environment

KiCad 10.0.7 AppImage at `~/kicad/kicad-10.0.7-x86_64.AppImage`. `tools/p2k/bin/kipy` (KiCad's
Python with `pcbnew`) and `tools/p2k/bin/kicad-cli` mount it on demand (`tools/p2k/bin/kicad_env.sh`).
Never run the AppImage with `--version`: it starts the GUI and hangs.
