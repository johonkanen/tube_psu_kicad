#!/usr/bin/env python3
"""Stage 14a (one-shot, not re-runnable; run with tools/p2k/bin/kipy): Kelvin tap of the heater shunt R30.

    tools/p2k/bin/kipy tools/next/route_s14a_heater_kelvin.py [--dry-run OUT.kicad_pcb]

Design review 2026-11-24 (findings 08 F1 / B1, 06 F1): the In2 HEATER_CURRENT sense lane started on the Q10 source
via (-12.8, -68.6); between it and R30 pad 1 lay 12.46 mm of 0.8 mm B.Cu carrying the whole Q10 current
(about 6 - 8 mOhm in series with the 4 mOhm shunt). F.Cu over R30 pad 1 is the Q11 gate pad / gate track /
Q11 tab (HV, 1.2 mm), so no through via fits at the pad; the tap is therefore a separate 0.2 mm B.Cu wire:
  * Q10 trunk (B.Cu 0.8 mm) moved off the pad tip: (-12.8, -71.0) -> (-12.8, -71.6) -> (-12.0, -72.4) -> (-12.0, -79.8),
    ending in the HEATER_CURRENT B.Cu pour 20 west of the pad (the current now enters pad 1 at its outer edge);
  * pour 20 cut back to x <= -11.2 (centre of pad 1): it touches only the outer half of the pad;
  * Kelvin wire from the inner half of the pad tip (-11.1, -79.6) on B.Cu north... along x -11.1 to y -72.5,
    diagonal to (-9.3, -70.7), via 0.5/0.3 at (-9.3, -69.9) (1.45 mm from the Q11 DC+ tab on F.Cu);
  * In2 lane cut at x -7.7 and joined to that via; it no longer reaches the Q10 via.
Record: kicad_next/routing/moves_s14a.json.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s14_common  # noqa: E402

N = "HEATER_CURRENT"


def edit(b, ed):
    # Q10 trunk
    ed.delete_track(N, "B.Cu", (-12.8, -71.0), (-11.2, -72.6), 0.8)
    ed.delete_track(N, "B.Cu", (-11.2, -72.6), (-11.2, -80.4), 0.8)
    ed.add_path(N, "B.Cu", [(-12.8, -71.0), (-12.8, -71.6), (-12.0, -72.4), (-12.0, -79.8)], 0.8)
    # pour 20: outer half of pad 1 only (keep the 5.1 hole)
    z = ed.zone("Proteus B.Cu pour 20", N, "B.Cu")
    old = ed.outline(z)
    holes = old[0][1:]
    ed.set_outline(z, [[[(-14.0, -81.5), (-11.2, -81.5), (-11.2, -79.3), (-14.0, -79.3)]] + holes],
                   "touches only the outer half of R30 pad 1")
    # Kelvin wire + via
    ed.add_path(N, "B.Cu", [(-11.1, -79.6), (-11.1, -72.5), (-9.3, -70.7), (-9.3, -69.9)], 0.2)
    ed.add_via(N, (-9.3, -69.9), 0.5, 0.3)
    # In2 lane
    ed.delete_track(N, "In2.Signal_HV", (-3.8, -68.3), (-12.6, -68.3), 0.2)
    ed.add_path(N, "In2.Signal_HV", [(-3.8, -68.3), (-7.7, -68.3), (-9.3, -69.9)], 0.2)


if __name__ == "__main__":
    sys.exit(s14_common.main("s14a", __file__, edit, sys.argv[1:]))
