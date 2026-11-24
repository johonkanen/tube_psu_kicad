#!/usr/bin/env python3
"""Stage 14h (one-shot, not re-runnable; run with tools/p2k/bin/kipy): small copper clean-ups.

    tools/p2k/bin/kipy tools/next/route_s14h_cleanup.py [--dry-run OUT.kicad_pcb]

Design review 2026-11-24:
  1. (findings 08 F4, 07) leftover 5.1 DHB_CURRENT copper with no pad: 'Proteus F.Cu pour 23' (x 27.6 ... 32.7), the via
     (31.795, -41.95) at the 5.1 Q7.3 place with its two F.Cu stubs, and the 0.254 mm In2 stub from that via to
     (22.6, -49.6) (DAB_DIS 0.235 mm from it on In2) - deleted. The C67 / C70 return (In2 1.2 mm, vias (22.6, -49.0 /
     -50.0), zone S4B_DHB_CURRENT_F) and the R83 Kelvin line are not touched.
  2. (findings 02 B7) B.Cu pour keep-out (rule area, no zone fill) x 4.4 ... 9.6, y -51.3 ... -46.2 under the DRV5
     output side: the GND fill no longer wraps the NC pads 12 / 13 and keeps > 1.5 mm from pad 14 (switch node).
  3. (findings 07 F10) the floating 0.9 mm2 DC+ fill island at the old 5.1 Q19 place is no longer in the stored fill
     (removed by the refills of stages 13 / 14; island removal is on) - nothing to do.
Record: kicad_next/routing/moves_s14h.json.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s14_common  # noqa: E402

N = "DHB_CURRENT"


def edit(b, ed):
    z = ed.zone("Proteus F.Cu pour 23", N, "F.Cu")
    ed.rec.append(dict(op="delete_zone", zone="Proteus F.Cu pour 23", net=N, layer="F.Cu", outline=ed.outline(z)))
    b.Remove(z)
    ed.delete_track(N, "F.Cu", (30.8, -41.95), (32.3, -41.95), 0.5)
    ed.delete_track(N, "F.Cu", (31.795, -42.9), (31.795, -41.0), 0.5)
    ed.delete_via(N, (31.795, -41.95))
    for s, e in [((31.795, -41.9499), (30.2, -41.9499)), ((30.2, -41.9499), (28.5499, -43.6)),
                 ((28.5499, -43.6), (28.5499, -48.6)), ((28.5499, -48.6), (27.5499, -49.6)),
                 ((27.55, -49.6), (22.6, -49.6))]:
        ed.delete_track(N, "In2.Signal_HV", s, e, 0.254)
    ed.add_keepout("S14H_KO DRV5 output side: no GND fill round NC pads 12 / 13, >= 1.5 mm from pad 14", "B.Cu",
                   [(4.4, -51.3), (9.6, -51.3), (9.6, -46.2), (4.4, -46.2)], "findings 02 B7")


if __name__ == "__main__":
    sys.exit(s14_common.main("s14h", __file__, edit, sys.argv[1:]))
