#!/usr/bin/env python3
"""Stage 16b (one-shot, not re-runnable; run with tools/p2k/bin/kipy): C102 away from the screw head at H8.

    tools/p2k/bin/kipy tools/next/route_s16b_c102_h8.py [--dry-run OUT.kicad_pcb]

Design review 2026-11-24, finding 12 F2: the can of C102 (Ymin KCXE 56 uF 250 V, D10 x 18, centre (77.0, 11.35)) was
7.88 mm from the centre of mounting hole H8 (84.232, 14.477): a 6 mm screw head overlapped it by 0.12 mm, a 7 mm
washer by 0.62 mm.
  * C102 1.25 mm west: pads (77.0, 13.85) / (77.0, 8.85) -> (75.75, 13.85) / (75.75, 8.85), rot 90 kept; can centre
    (75.75, 11.35) 9.04 mm from H8: 1.04 mm clear of a 6 mm head, 0.54 mm clear of a 7 mm washer (nominal can).
    No track or via ends on its pads; both are fed by the pours (ISO_GND / -100V BIAS) only.
  * The pads then stand in the pour keep-out "around the TR1 slot end at the fly leads" (x 57.5..77.0, y 4..18.4,
    all six layers), where no pour could reach them. Its east end gives way: x 74.5..77.0, y 6.8..18.4 is
    taken out of the keep-out on every layer, so the F.Cu / B.Cu / In1 / In4 ISO_GND pours and the F.Cu -100V BIAS
    pour reach the pads as before (the primary DC+ / FLY_C fly-lead pads TR1.11 / TR1.12 stay > 12 mm away across
    the TR1 slot end; check_domains.py verifies the 11.1 / 4.0 mm limits).
Record: kicad_next/routing/moves_s16b.json.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s14_common  # noqa: E402

KEEPOUT = "barrier pour keep-out: around the TR1 slot end at the fly leads"
LAYERS = ["F.Cu", "In1.GND", "In2.Signal_HV", "In3.Power", "In4.GND", "B.Cu"]


def edit(b, ed):
    ed.move_footprint("C102", (75.75, 13.85), 90.0)
    z = ed.zone(KEEPOUT)                       # one rule area on all six copper layers
    layers = sorted(ed.b.GetLayerName(l) for l in z.GetLayerSet().Seq())
    if layers != sorted(LAYERS):
        ed.fail(f"{KEEPOUT}: layers {layers}")
    old = ed.outline(z)
    ring = [tuple(p) for p in old[0][0]]
    if len(old) != 1 or len(old[0]) != 1 or sorted(ring) != sorted([(57.5, 4.0), (77.0, 4.0), (77.0, 18.4),
                                                                     (57.5, 18.4)]):
        ed.fail(f"{KEEPOUT}: outline not as expected: {old}")
    ed.set_outline(z, [[[(57.5, 4.0), (77.0, 4.0), (77.0, 6.8), (74.5, 6.8), (74.5, 18.4), (57.5, 18.4)]]],
                   "east end x 74.5..77.0, y 6.8..18.4 freed: C102 moved 1.25 mm west (finding 12 F2)")


if __name__ == "__main__":
    sys.exit(s14_common.main("s16b", __file__, edit, sys.argv[1:]))
