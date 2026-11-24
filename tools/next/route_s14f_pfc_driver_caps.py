#!/usr/bin/env python3
"""Stage 14f (one-shot, not re-runnable; run with tools/p2k/bin/kipy): PFC driver supply capacitors C79 / C80.

    tools/p2k/bin/kipy tools/next/route_s14f_pfc_driver_caps.py [--dry-run OUT.kicad_pcb]

Design review 2026-11-24 (findings 05 F4): the UCC27511A drivers DRV1 / DRV2 (SOT-23-6, B.Cu) sit on the old IXDD609
origins, C79 / C80 stayed where they were: VDD reached the capacitor only through vias and an inner layer (pad gaps
DRV1.1-C79.1 2.54 mm, DRV1.4-C79.2 3.54 mm, DRV2.1-C80.1 4.24 mm; 5.1 0.5 - 0.7 mm). On the SOT-23-6 VDD (pin 1) and
GND (pin 4) are diagonal corners, so a 0603 cannot touch both; each capacitor now sits at pin 1 with a direct B.Cu track
and returns to the GND planes through its own via(s) at the GND pad:
  DRV1 / C79: C79 (15.47, -36.278) -> (12.44, -36.5), 0 deg; pin 1 -> C79.1 0.4 mm track; the B.Cu 15V trunk from
    (14.67, -37.929) now ends in C79.1 ((14.67, -37.6) -> (12.2, -37.6) -> C79.1), its old stub / 15V via (13.67, -36.28)
    removed; C79.2 -> GND via (14.1, -36.5) (inside the B.Cu GND pour); old C79.2 GND via (16.845, -36.278) + stub
    removed. No GND via fits at DRV1 pin 4 (In3 UART lanes y -32.0 / -31.25, In2 PFC_PWM1 / OUTL lanes); pins 4 / 5
    sit in the B.Cu GND pour. New copper >= 6.2 mm from the H4 centre (no new mounting-hole pair).
  DRV2 / C80: C80 (12.159, 14.141) -> (13.3, 7.225), 90 deg (pad 1 south at y 8.0, 0.35 mm from pin 1); pin 1 -> C80.1
    track; C80.2 -> two GND vias (13.3, 5.5) / (12.6, 5.5); old C80.1 feed (F.Cu 15V (14.06, 10.6) -> (14.06, 12.1) ->
    via (12.96, 13.14) -> B.Cu) removed (the old
    C80.2 GND via (11.359, 14.649) stays as a pour stitch). No GND via at DRV2 pin 4 fits (In2 PFC_PWM2 / OUTL lanes,
    HV lanes at x 8.6 / 9.7); pins 4 / 5 sit in the B.Cu GND pour.
Record: kicad_next/routing/moves_s14f.json.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s14_common  # noqa: E402


def pad_at(ed, ref, num, want):
    f = ed.footprint(ref)
    p = [q for q in f.Pads() if q.GetNumber() == num][0]
    x, y = ed.pt(p.GetPosition())
    if abs(x - want[0]) > 0.01 or abs(y - want[1]) > 0.01:
        ed.fail(f"{ref}.{num} at ({x:.3f}, {y:.3f}), expected {want}")


def edit(b, ed):
    # DRV1 / C79
    ed.delete_track("15V", "B.Cu", (14.67, -36.28), (13.67, -36.28), 0.4)
    ed.delete_via("15V", (13.67, -36.28))
    ed.delete_track("15V", "B.Cu", (14.6701, -36.278), (14.6701, -37.929), 0.762)
    ed.delete_track("GND", "B.Cu", (16.2701, -36.278), (16.8452, -36.278))
    ed.delete_via("GND", (16.8452, -36.278))
    ed.move_footprint("C79", (12.44, -36.5), 0.0)
    pad_at(ed, "C79", "1", (11.665, -36.5))
    pad_at(ed, "C79", "2", (13.215, -36.5))
    ed.add_track("15V", "B.Cu", (11.515, -34.749), (11.665, -36.5), 0.4)
    ed.add_path("15V", "B.Cu", [(14.6701, -37.929), (14.6701, -37.6), (12.2, -37.6), (11.665, -36.5)], 0.5)
    ed.add_track("GND", "B.Cu", (13.215, -36.5), (14.1, -36.5), 0.4)
    ed.add_via("GND", (14.1, -36.5), 0.6, 0.3)
    ed.delete_track("15V", "B.Cu", (14.6701, -36.278), (14.7151, -36.233))
    # DRV2 / C80
    ed.delete_track("15V", "B.Cu", (12.96, 14.14), (12.96, 13.14), 0.4)
    ed.delete_track("15V", "B.Cu", (12.959, 14.141), (13.1561, 13.9439))
    ed.delete_via("15V", (12.96, 13.14))
    ed.delete_track("15V", "F.Cu", (12.96, 13.14), (12.96, 13.04), 0.4)
    ed.delete_track("15V", "F.Cu", (14.06, 12.1), (13.16, 13.0), 0.4)
    ed.delete_track("15V", "F.Cu", (14.06, 10.6), (14.06, 12.1), 0.4)
    ed.move_footprint("C80", (13.3, 7.225), 90.0)
    pad_at(ed, "C80", "1", (13.3, 8.0))
    pad_at(ed, "C80", "2", (13.3, 6.45))
    ed.add_track("15V", "B.Cu", (12.868, 9.126), (13.3, 8.0), 0.4)
    ed.add_path("GND", "B.Cu", [(13.3, 6.45), (13.3, 5.5)], 0.4)
    ed.add_track("GND", "B.Cu", (13.3, 5.5), (12.6, 5.5), 0.4)
    ed.add_via("GND", (13.3, 5.5), 0.6, 0.3)
    ed.add_via("GND", (12.6, 5.5), 0.6, 0.3)


if __name__ == "__main__":
    sys.exit(s14_common.main("s14f", __file__, edit, sys.argv[1:]))
