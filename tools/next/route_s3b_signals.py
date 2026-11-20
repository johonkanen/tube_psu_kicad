#!/usr/bin/env python3
"""Routing stage 3b of tube_power 5.2: signals and the open ends left by stage 3a (system python3).

    python3 tools/next/route_s3b_signals.py [--dry-run OUT.kicad_pcb | --strip]

Order of a full rebuild (the stage-3a router must not see the copper of the later stages; stage 3c = clean-up of
the kept 5.1 copper, route_s3c_cleanup.py, and stage 3d = the drawn ISO2 / AD2 fan-out, route_s3d_iso2.py, run
between 3a and this stage):
    python3 tools/next/route_s3b_signals.py --strip
    python3 tools/next/route_s3e_j2.py --strip
    python3 tools/next/route_s3d_iso2.py --strip
    python3 tools/next/route_s3c_cleanup.py --strip
    python3 tools/next/route_s3a_power.py
    python3 tools/next/route_s3c_cleanup.py
    python3 tools/next/route_s3d_iso2.py
    python3 tools/next/route_s3e_j2.py
    python3 tools/next/route_s3b_signals.py
    tools/p2k/bin/kipy tools/next/route_s2_planes.py

Engine: tools/next/s3_router.py (class clearances, HV functional 1.2 mm, domain spacings against all layers).
TABLE is one connection per row, grouped: (group, net, start, end, layers, width, options). It was generated
from the unconnected list of the board after stage 3a (842d301) and is edited by hand from there; rows are routed
in table order. start / end: "REF.PAD" or a point (x, y, layer) on kept 5.1 copper; a point as the end means "the
rest of the net near that point". Layers: F, B, 2 = In2.Signal_HV; switch nodes stay on the outer layers.
Re-runnable: the copper of the last run (kicad_next/routing/s3b_added.json) is removed first.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s3_router as R  # noqa: E402

VS = (0.6, 0.3)
SLOT_GAP = (57.5, -22.5, 66.0, -9.0)      # primary tracks of ISO2 do not use the gap between the TR1 and ISO2 slots
# (the ISO2 / AD2 rows - both sides of ISO2, the AD2 SPI, DAB_DIS / DAB_DIS_SEC, AD2_3V3, C103 - are stage 3d now:
# route_s3d_iso2.py)
# (the J2 nets - the analog escapes at J2, the control bus round mounting hole H4, EPWM5A / EPWM6A at DRV3, B12 /
# PRI_DHB_HI / DAB_DIS at DRV5 with its dead-time net, HT_SDATA at ISO1 - are stage 3e: route_s3e_j2.py. Two open
# connections have no row any more, they need a decision (README "Stage 3e"): EPWM6A -> R77 pin 2 and the 5V link
# from the bus to DRV3)

TABLE = [
    # ---- supply, ground and switch-node leftovers
    ('supply, ground and switch-node leftovers', '+1V65_BIAS', 'C123.1', (1.5, -54.5, 'In2.Signal_HV'), 'FB2', 0.3, {'relax': ('C123',)}),
    ('supply, ground and switch-node leftovers', '+1V65_BIAS', 'C126.1', (30.518, 9.182, 'F.Cu'), 'FB2', 0.3, {'relax': ('C126',)}),
    ('supply, ground and switch-node leftovers', '5V', (-23.3, -53.036, 'B.Cu'), (-22.6, -53.1, 'B.Cu'), 'FB2', 0.3, {}),
    ('supply, ground and switch-node leftovers', 'ISO_GND', (71.51, -61.3436, 'B.Cu'), (71.51, -60.3784, 'B.Cu'), 'FB2', 0.3, {}),
    ('supply, ground and switch-node leftovers', '/06 Heaters/HEATER_HI_SOURCE', 'DRV3.14', (-18.3, -61.7, 'B.Cu'), 'FB', 0.3, {'relax': ('DRV3',)}),
    ('supply, ground and switch-node leftovers', '+3V3', (6.5, -59.4, 'F.Cu'), (7.2, -58.1, 'In2.Signal_HV'), 'FB2', 0.3, {}),
    ('supply, ground and switch-node leftovers', '+1V65_BIAS', 'R103.2', (5.2, -54.5, 'In2.Signal_HV'), 'FB2', 0.3, {'relax': ('R103',)}),
    ('supply, ground and switch-node leftovers', '+1V65_BIAS', 'C122.1', (1.5, -60.8, 'B.Cu'), 'FB2', 0.3, {'relax': ('C122',)}),
    ('supply, ground and switch-node leftovers', 'DHB_HI_SOURCE', 'C92.1', 'DRV5.9', 'FB', 0.3, {'relax': ('C92', 'DRV5')}),
    ('supply, ground and switch-node leftovers', 'ISO_GND', (69.9, -65.1476, 'B.Cu'), (71.51, -61.6484, 'B.Cu'), 'FB2', 0.3, {}),
    ('supply, ground and switch-node leftovers', '/06 Heaters/HEATER_HI_SOURCE', 'C25.2', (-18.3, -61.7, 'B.Cu'), 'FB', 0.3, {'relax': ('C25',)}),
    ('supply, ground and switch-node leftovers', '+1V65_BIAS', 'C48.1', (27.9, -28.1, 'In2.Signal_HV'), 'FB2', 0.3, {'relax': ('C48',)}),
    ('supply, ground and switch-node leftovers', '/06 Heaters/HEATER_HI_SOURCE', 'DRV3.14', (-16.191, -55.643, 'F.Cu'), 'FB', 0.3, {'relax': ('DRV3',)}),
    ('supply, ground and switch-node leftovers', 'DHB_HI_SOURCE', 'DRV5.9', 'TR3.7', 'FB', 0.3, {'relax': ('DRV5', 'TR3'), 'foreign_gap': 4.0}),
    ('supply, ground and switch-node leftovers', 'ISO_GND', (65.435, -49.1, 'B.Cu'), (65.105, -44.1774, 'B.Cu'), 'FB2', 0.3, {}),
    ('supply, ground and switch-node leftovers', '+1V65_BIAS', 'R131.2', (23.7, -17.8, 'B.Cu'), 'FB2', 0.3, {'relax': ('R131',)}),
    ('supply, ground and switch-node leftovers', 'ISO_GND', (70.0524, -65.3, 'B.Cu'), (74.935, -67.52, 'B.Cu'), 'FB2', 0.3, {}),
    ('supply, ground and switch-node leftovers', '15V', 'D11.A', (-9.5708, -61.5, 'B.Cu'), 'FB2', 0.3, {}),       # (no relax: D11 pin C is the bootstrap node)
    ('supply, ground and switch-node leftovers', '+3V3', 'C125.1', 'C87.1', 'FB2', 0.3, {'relax': ('C125', 'C87')}),
    ('supply, ground and switch-node leftovers', '5V_ISOL', 'DRV6.3', 'DRV6.8', 'FB2', 0.3, {'relax': ('DRV6',)}),
    ('supply, ground and switch-node leftovers', '+3V3', 'C125.1', (-1.1, -52.8, 'In2.Signal_HV'), 'FB2', 0.3, {'relax': ('C125',)}),
    ('supply, ground and switch-node leftovers', 'DHB_HI_SOURCE_SEC', 'DRV6.14', (55.45, -47.275, 'F.Cu'), 'FB', 0.3, {'relax': ('DRV6',)}),
    ('supply, ground and switch-node leftovers', 'DHB_HI_SOURCE_SEC', 'C46.1', (55.45, -47.275, 'F.Cu'), 'FB', 0.3, {'relax': ('C46',)}),
    ('supply, ground and switch-node leftovers', '+3V3', 'U11.3', (6.4, -61.0, 'B.Cu'), 'FB2', 0.3, {'relax': ('U11',)}),
    # ---- gate drives
    ('gate drives', 'Net-(D10-PadA)', 'D10.A', 'R142.2', 'FB2', 0.4, {'relax': ('D10', 'R142')}),
    ('gate drives', 'ISO_SEC_DHB_HI', 'R75.2', (68.975, -61.452, 'In2.Signal_HV'), 'FB2', 0.4, {'relax': ('R75',)}),
    ('gate drives', 'EPWM5A_ISO', 'DRV4.4', (-53.3, -65.1, 'In2.Signal_HV'), 'FB2', 0.4, {'relax': ('DRV4',)}),
    ('gate drives', 'Net-(DRV4-OUTB)', 'DRV4.5', (-52.35, -71.6, 'In2.Signal_HV'), 'FB2', 0.4, {'relax': ('DRV4',)}),
    ('gate drives', 'ISO_SEC_DHB_LO', 'R76.2', (68.7, -60.182, 'In2.Signal_HV'), 'FB2', 0.4, {'relax': ('R76',)}),
    ('gate drives', 'EPWM5A_ISO', 'ISO1.14', (-48.2, -53.605, 'In2.Signal_HV'), 'FB2', 0.4, {'relax': ('ISO1',), 'foreign_gap': 4.0}),
    ('gate drives', 'SYNCH_2', 'ISO1.4', (-36.317, -54.2104, 'B.Cu'), 'FB2', 0.4, {'relax': ('ISO1',), 'foreign_gap': 4.0}),
    ('gate drives', 'SYNCH_1', 'ISO1.3', (-36.317, -52.9404, 'B.Cu'), 'FB2', 0.4, {'relax': ('ISO1',), 'foreign_gap': 4.0}),
    ('gate drives', 'Net-(DRV6-DT)', 'R128.1', 'C119.1', 'FB2', 0.4, {'relax': ('C119', 'R128')}),
    ('gate drives', 'DAB_DIS', 'R129.1', 'C120.1', 'FB2', 0.4, {'relax': ('C120', 'R129')}),
    ('gate drives', 'Net-(DRV3-DT)', 'R130.1', 'C121.1', 'FB2', 0.4, {'relax': ('C121', 'R130')}),
    ('gate drives', '/06 Heaters/HEATER_LOW_GATE', 'D33.A', (-10.3, -76.2, 'B.Cu'), 'FB2', 0.4, {'relax': ('D33',)}),
    ('gate drives', 'Net-(Q9-G)', 'R44.1', 'Q9.2', 'FB2', 0.4, {'relax': ('Q9', 'R44')}),
    ('gate drives', 'Net-(Q9-G)', 'Q9.2', 'C35.1', 'FB2', 0.4, {'relax': ('C35', 'Q9')}),
    ('gate drives', 'Net-(Q8-G)', 'R87.2', 'R88.2', 'FB2', 0.4, {'relax': ('R87', 'R88')}),
    ('gate drives', 'EPWM6A_ISO', 'ISO1.13', (-48.89, -54.2104, 'B.Cu'), 'FB2', 0.4, {'relax': ('ISO1',), 'foreign_gap': 4.0}),
    ('gate drives', '/06 Heaters/HEATER_HI_GATE', 'D35.A', 'R36.1', 'FB2', 0.4, {'relax': ('D35', 'R36')}),
    ('gate drives', 'DHB_LOW_GATE_SEC', 'R87.1', 'D32.C', 'FB2', 0.4, {'relax': ('D32', 'R87')}),
    ('gate drives', 'Net-(Q8-G)', 'R88.2', (71.415, -41.9499, 'B.Cu'), 'FB2', 0.4, {'relax': ('R88',)}),
    ('gate drives', 'Net-(DRV3-VDDA)', 'R99.2', 'C25.1', 'FB2', 0.4, {'relax': ('C25', 'R99')}),
    ('gate drives', 'Net-(D32-PadA)', 'D32.A', 'R88.1', 'FB2', 0.4, {'relax': ('D32', 'R88')}),
    ('gate drives', '/06 Heaters/HEATER_HI_DRV', (-21.9, -64.212, 'B.Cu'), (-20.433, -62.567, 'B.Cu'), 'FB2', 0.4, {}),
    ('gate drives', 'Net-(DRV3-DT)', 'DRV3.6', 'R130.1', 'FB2', 0.4, {'relax': ('DRV3', 'R130')}),
    ('gate drives', 'Net-(DRV5-DT)', 'DRV5.6', 'R127.1', 'FB2', 0.4, {'relax': ('DRV5', 'R127')}),
    ('gate drives', '/06 Heaters/HEATER_SYNC_GATE_1', 'Q1.2', 'R63.1', 'FB2', 0.4, {'relax': ('Q1', 'R63')}),
    ('gate drives', 'Net-(DRV6-VDDA)', 'C46.2', 'DRV6.16', 'FB2', 0.4, {'relax': ('C46', 'DRV6')}),
    ('gate drives', 'Net-(DRV4-OUTA)', 'DRV4.7', 'R63.2', 'FB2', 0.4, {'relax': ('DRV4', 'R63')}),
    ('gate drives', 'Net-(D35-K)', 'R59.2', 'D35.C', 'FB2', 0.4, {'relax': ('D35', 'R59')}),
    ('gate drives', 'GATE1', (3.7529, -29.576, 'B.Cu'), (6.3, -29.126, 'B.Cu'), 'FB2', 0.4, {}),
    ('gate drives', 'Net-(DRV3-VDDA)', 'C25.1', 'DRV3.16', 'FB2', 0.4, {'relax': ('C25', 'DRV3')}),
    ('gate drives', 'ISO_SEC_DHB_HI', 'DRV6.1', (68.34, -61.452, 'B.Cu'), 'FB2', 0.4, {'relax': ('DRV6',)}),
    ('gate drives', 'EPWM6A_ISO', 'DRV4.2', (-54.3, -63.3, 'In2.Signal_HV'), 'FB2', 0.4, {'relax': ('DRV4',)}),
    ('gate drives', 'ISO_SEC_DHB_LO', 'DRV6.2', (68.7, -60.182, 'In2.Signal_HV'), 'FB2', 0.4, {'relax': ('DRV6',)}),
    ('gate drives', 'Net-(DRV5-VDDB)', 'DRV5.11', (21.6, -56.2, 'B.Cu'), 'FB2', 0.4, {'relax': ('DRV5',)}),
    ('gate drives', 'Net-(D11-K)', 'D11.C', 'R99.1', 'FB2', 0.4, {'relax': ('D11', 'R99')}),
    ('gate drives', '/06 Heaters/HEATER_HI_GATE', 'R36.1', 'R24.2', 'FB2', 0.4, {'relax': ('R36', 'R24')}),
    ('gate drives', 'Net-(DRV1-OUTH)', 'R14.1', 'DRV1.2', 'FB2', 0.4, {'relax': ('DRV1', 'R14')}),
    ('gate drives', '/06 Heaters/HEATER_HI_DRV', 'DRV3.15', (-20.433, -62.567, 'B.Cu'), 'FB2', 0.4, {'relax': ('DRV3',)}),
    ('gate drives', 'Net-(D18-K)', 'R46.1', (60.4, -66.8, 'B.Cu'), 'FB2', 0.4, {'relax': ('R46',)}),
    ('gate drives', '/06 Heaters/HEATER_HI_GATE', 'R24.2', 'Q11.1', 'FB2', 0.4, {'relax': ('Q11', 'R24')}),
    ('gate drives', 'Net-(DRV2-OUTL)', 'DRV2.3', (11.943, 6.6571, 'B.Cu'), 'FB2', 0.4, {'relax': ('DRV2',)}),
    ('gate drives', 'PFC_PWM1', 'DRV1.6', (15.875, -34.087, 'In2.Signal_HV'), 'FB2', 0.4, {'relax': ('DRV1',)}),
    ('gate drives', 'Net-(DRV6-VDDA)', 'DRV6.16', 'R46.2', 'FB2', 0.4, {'relax': ('DRV6', 'R46')}),
    ('gate drives', 'Net-(DRV2-OUTH)', 'DRV2.2', 'R20.1', 'FB2', 0.4, {'relax': ('DRV2', 'R20')}),
    ('gate drives', 'Net-(DRV5-VDDB)', 'C92.2', 'R41.2', 'FB2', 0.4, {'relax': ('C92', 'R41')}),
    ('gate drives', '/06 Heaters/HEATER_SYNC_GATE_1', 'R63.1', 'R108.1', 'FB2', 0.4, {'relax': ('R108', 'R63')}),
    ('gate drives', 'Net-(DRV1-OUTL)', 'R1.1', 'DRV1.3', 'FB2', 0.4, {'relax': ('DRV1', 'R1')}),
    ('gate drives', 'PFC_PWM2', 'DRV2.6', (14.1, 13.8, 'B.Cu'), 'FB2', 0.4, {'relax': ('DRV2',)}),
    ('gate drives', '/06 Heaters/HEATER_LOW_GATE', 'Q10.1', (-10.028, -73.1, 'B.Cu'), 'FB2', 0.4, {'relax': ('Q10',)}),
    ('gate drives', 'Net-(DRV6-DT)', 'DRV6.6', 'R128.1', 'FB2', 0.4, {'relax': ('DRV6', 'R128')}),
    ('gate drives', 'Net-(DRV3-VDDA)', 'DRV3.16', (-23.9, -56.1, 'B.Cu'), 'FB2', 0.4, {'relax': ('DRV3',)}),
    ('gate drives', 'DHB_HI_GATE_SEC', 'DRV6.15', (62.3, -53.9, 'B.Cu'), 'FB2', 0.4, {'relax': ('DRV6',)}),
    ('gate drives', 'DHB_LOW_GATE', 'DRV5.15', (34.78, -50.72, 'B.Cu'), 'FB2', 0.4, {'relax': ('DRV5',)}),
    ('gate drives', 'ISO_SEC_DHB_LO', (68.7, -60.182, 'In2.Signal_HV'), (78.105, -54.677, 'In2.Signal_HV'), 'FB2', 0.4, {}),
    ('gate drives', 'DHB_HI_GATE', 'DRV5.10', (35.2175, -52.6, 'B.Cu'), 'FB2', 0.4, {'relax': ('DRV5',)}),
    ('gate drives', '/06 Heaters/HEATER_LOW_DRV', 'DRV3.10', (-10.028, -70.441, 'B.Cu'), 'FB2', 0.4, {'relax': ('DRV3',)}),
    ('gate drives', 'DHB_LOW_GATE_SEC', 'D32.C', 'DRV6.10', 'FB2', 0.4, {'relax': ('D32', 'DRV6')}),
    ('gate drives', 'ISO_SEC_DHB_HI', (70.88, -59.547, 'In2.Signal_HV'), (79.38, -40.772, 'In2.Signal_HV'), 'FB2', 0.4, {}),
    ('gate drives', 'DAB_DIS', 'C120.1', 'J2.18', 'FB2', 0.4, {'relax': ('C120', 'J2')}),
    # ---- current sense and analog
    ('current sense and analog', 'Net-(C138-Pad1)', 'C138.1', 'R140.2', 'FB2', 0.2, {'relax': ('C138', 'R140')}),
    ('current sense and analog', 'Net-(U8-+)', 'C126.2', 'R52.2', 'FB2', 0.2, {'relax': ('C126', 'R52')}),
    ('current sense and analog', 'Net-(U10A--)', 'U10.1', 'U10.2', 'FB2', 0.2, {'relax': ('U10',)}),
    ('current sense and analog', 'Net-(U10B--)', 'U10.7', 'U10.6', 'FB2', 0.2, {'relax': ('U10',)}),
    ('current sense and analog', 'Net-(R48-Pad2)', (5.3, 8.6, 'B.Cu'), (6.2, 8.6, 'In2.Signal_HV'), 'FB2', 0.3, {}),
    ('current sense and analog', 'Net-(U10A--)', 'U10.2', 'R132.1', 'FB2', 0.2, {'relax': ('R132', 'U10')}),
    ('current sense and analog', 'Net-(U10A-+)', 'U10.3', (38.922, -1.277, 'F.Cu'), 'FB2', 0.2, {'relax': ('U10',)}),
    ('current sense and analog', 'HEATER_CURRENT', (-11.2, -80.4, 'B.Cu'), (-11.2, -79.1, 'In2.Signal_HV'), 'FB2', 0.2, {}),
    ('current sense and analog', 'Net-(U10B-+)', 'R133.2', 'R134.1', 'FB2', 0.2, {'relax': ('R133', 'R134')}),
    ('current sense and analog', 'Net-(U9-+)', 'R3.1', 'R110.1', 'FB2', 0.2, {'relax': ('R110', 'R3')}),
    ('current sense and analog', 'Net-(U10B-+)', 'R134.1', 'C132.1', 'FB2', 0.2, {'relax': ('C132', 'R134')}),
    ('current sense and analog', 'Net-(U6-+)', 'R17.1', 'C130.1', 'FB2', 0.2, {'relax': ('C130', 'R17')}),
    ('current sense and analog', 'Net-(U1A-+)', 'C123.2', 'R103.1', 'FB2', 0.2, {'relax': ('C123', 'R103')}),
    ('current sense and analog', 'Net-(C12-Pad2)', 'R72.1', (45.1, 15.1, 'F.Cu'), 'FB2', 0.3, {'relax': ('R72',)}),
    ('current sense and analog', 'Net-(R143-Pad2)', 'R143.2', 'R144.1', 'FB2', 0.3, {'relax': ('R143', 'R144')}),
    ('current sense and analog', 'Net-(R151-Pad2)', 'R151.2', 'R152.1', 'FB2', 0.3, {'relax': ('R151', 'R152')}),
    ('current sense and analog', 'Net-(R147-Pad2)', 'R147.2', 'R148.1', 'FB2', 0.3, {'relax': ('R147', 'R148')}),
    ('current sense and analog', 'Net-(U9-+)', 'C128.1', 'U9.3', 'FB2', 0.2, {'relax': ('C128', 'U9')}),
    ('current sense and analog', 'Net-(U10B-+)', 'R133.2', 'U10.5', 'FB2', 0.2, {'relax': ('R133', 'U10')}),
    ('current sense and analog', 'Net-(R145-Pad2)', 'R146.1', 'R145.2', 'FB2', 0.3, {'relax': ('R145', 'R146')}),
    ('current sense and analog', 'Net-(C127-Pad1)', 'C127.1', (27.9, 11.4, 'B.Cu'), 'FB2', 0.2, {'relax': ('C127',)}),
    ('current sense and analog', 'Net-(R149-Pad2)', 'R149.2', 'R150.1', 'FB2', 0.3, {'relax': ('R149', 'R150')}),
    ('current sense and analog', 'Net-(R152-Pad2)', 'R152.2', 'R153.1', 'FB2', 0.3, {'relax': ('R152', 'R153')}),
    ('current sense and analog', 'Net-(U10B--)', 'U10.6', 'R135.1', 'FB2', 0.2, {'relax': ('R135', 'U10')}),
    ('current sense and analog', 'Net-(U9-+)', 'U9.3', 'R3.1', 'FB2', 0.2, {'relax': ('R3', 'U9')}),
    ('current sense and analog', 'Net-(U9--)', 'R131.1', 'U9.4', 'FB2', 0.2, {'relax': ('R131', 'U9')}),
    ('current sense and analog', 'DHB_CURRENT', (7.2, -58.8, 'In2.Signal_HV'), (10.1, -59.3, 'In2.Signal_HV'), 'FB2', 0.2, {}),
    ('current sense and analog', 'Net-(U9--)', 'U9.4', 'U9.1', 'FB2', 0.2, {'relax': ('U9',)}),
    ('current sense and analog', 'Net-(U1B-+)', 'R104.1', 'C122.2', 'FB2', 0.2, {'relax': ('C122', 'R104')}),
    ('current sense and analog', 'Net-(U8--)', 'C127.2', (33.6272, 13.9, 'B.Cu'), 'FB2', 0.2, {'relax': ('C127',)}),
    ('current sense and analog', '/04 MCU connector/DC_LINK_MEAS', (33.1357, 3.2438, 'F.Cu'), (29.8, 2.7, 'B.Cu'), 'FB2', 0.2, {}),
    ('current sense and analog', 'CUK_CAP_MEAS-', 'R113.1', (79.3, -29.6, 'B.Cu'), 'FB2', 0.2, {'relax': ('R113',)}),
    ('current sense and analog', 'Net-(U6--)', 'C131.1', (18.6918, 1.4, 'B.Cu'), 'FB2', 0.2, {'relax': ('C131',)}),
    ('current sense and analog', 'Net-(C131-Pad2)', 'C131.2', (22.1, 3.0, 'B.Cu'), 'FB2', 0.2, {'relax': ('C131',)}),
    ('current sense and analog', 'Net-(C63-Pad1)', (5.75, -62.0, 'B.Cu'), (5.75, -54.95, 'In2.Signal_HV'), 'FB2', 0.2, {}),
    ('current sense and analog', 'Net-(R48-Pad2)', (11.25, 17.15, 'In2.Signal_HV'), (6.2, 8.6, 'In2.Signal_HV'), 'FB2', 0.3, {}),
    ('current sense and analog', 'HEATER_CURRENT', (-1.5, -66.0, 'In2.Signal_HV'), (-10.592, -70.281, 'F.Cu'), 'FB2', 0.2, {}),
    ('current sense and analog', 'HEATER_CURRENT', (-1.5, -66.0, 'In2.Signal_HV'), (0.4, -56.1, 'B.Cu'), 'FB2', 0.2, {}),
    ('current sense and analog', 'Net-(C11-Pad1)', (15.1, -47.9, 'In2.Signal_HV'), (7.9, -57.2, 'In2.Signal_HV'), 'FB2', 0.2, {}),
    ('current sense and analog', 'DHB_CURRENT', 'R146.2', (18.8, -58.1, 'In2.Signal_HV'), 'FB2', 0.2, {'relax': ('R146',)}),
    ('current sense and analog', 'Net-(R51-Pad2)', (29.2213, 16.4778, 'In2.Signal_HV'), (5.3, 6.5, 'B.Cu'), 'FB2', 0.3, {}),
    # ---- SPI and control
    ('SPI and control', 'Net-(AD1-CS)', 'ISO1.12', (-48.128, -55.4804, 'B.Cu'), 'FB2', 0.2, {'relax': ('ISO1',), 'foreign_gap': 4.0}),
    ('SPI and control', 'Net-(AD1-SDATA)', 'ISO1.10', (-48.128, -57.487, 'B.Cu'), 'FB2', 0.2, {'relax': ('ISO1',), 'foreign_gap': 4.0}),
    ('SPI and control', 'Net-(AD1-CLK)', 'ISO1.11', (-48.3312, -56.217, 'F.Cu'), 'FB2', 0.2, {'relax': ('ISO1',), 'foreign_gap': 4.0}),
    ('SPI and control', 'Net-(PWM2-FB)', 'R140.1', 'R141.1', 'FB2', 0.2, {'relax': ('R140', 'R141')}),
    ('SPI and control', '$HT_CS', 'ISO1.5', (-36.063, -55.455, 'B.Cu'), 'FB2', 0.2, {'relax': ('ISO1',), 'foreign_gap': 4.0}),
    ('SPI and control', 'HT_CLK', 'ISO1.6', (-36.0504, -56.7504, 'F.Cu'), 'FB2', 0.2, {'relax': ('ISO1',), 'foreign_gap': 4.0}),
    ('SPI and control', 'Net-(PWM2-VIN)', 'PWM2.1', 'C140.1', 'FB2', 0.2, {'relax': ('C140', 'PWM2')}),
    ('SPI and control', 'GPIO_BYPASS_RLY', 'R44.2', 'R32.1', 'FB2', 0.2, {'relax': ('R32', 'R44')}),
    ('SPI and control', 'Net-(PWM2-FB)', 'C139.1', 'PWM2.3', 'FB2', 0.2, {'relax': ('C139', 'PWM2')}),
    ('SPI and control', 'Net-(PWM2-VERR)', 'PWM2.2', 'R139.1', 'FB2', 0.2, {'relax': ('PWM2', 'R139')}),
    ('SPI and control', 'Net-(PWM2-FB)', 'R140.1', 'C139.1', 'FB2', 0.2, {'relax': ('C139', 'R140')}),
    ('SPI and control', 'Net-(PWM2-VIN)', 'C140.1', 'R154.1', 'FB2', 0.2, {'relax': ('C140', 'R154')}),
    ('SPI and control', 'Net-(Q9-D)', 'Q9.1', (-58.9615, -33.2935, 'B.Cu'), 'FB2', 0.2, {'relax': ('Q9',)}),
    ('SPI and control', 'Net-(PWM2-VERR)', 'R139.1', 'R138.2', 'FB2', 0.2, {'relax': ('R138', 'R139')}),
    ('SPI and control', 'AC2', (-6.0, 2.9, 'B.Cu'), (-0.2, 6.5, 'B.Cu'), 'FB2', 0.3, {}),
    ('SPI and control', 'Net-(PWM2-VIN)', 'R153.2', 'PWM2.1', 'FB2', 0.2, {'relax': ('PWM2', 'R153')}),
    ('SPI and control', 'AC1', 'R47.1', (-15.5, -2.5, 'B.Cu'), 'FB2', 0.3, {'relax': ('R47',)}),
    ('SPI and control', 'GPIO_BYPASS_RLY', 'R44.2', (-37.81, -45.3, 'In2.Signal_HV'), 'FB2', 0.2, {'relax': ('R44',)}),
    # ---- UART
    ('UART', 'Net-(U11-B1)', 'U11.13', 'R137.1', 'FB2', 0.2, {'relax': ('R137', 'U11')}),
    ('UART', 'Net-(U11-B2)', 'U11.12', 'R136.1', 'FB2', 0.2, {'relax': ('R136', 'U11')}),
    ('UART', '/04 MCU connector/UART_RXD', 'R137.2', 'J4.4', 'FB2', 0.2, {'relax': ('J4', 'R137')}),
    ('UART', '/04 MCU connector/UART_TXD', 'R136.2', 'J4.3', 'FB2', 0.2, {'relax': ('J4', 'R136')}),
    ('UART', '/04 MCU connector/RX', 'U11.5', (40.1, -19.5029, 'B.Cu'), 'FB2', 0.2, {'relax': ('U11',)}),
    ('UART', '/04 MCU connector/TX', 'U11.4', (40.6, -19.5, 'B.Cu'), 'FB2', 0.2, {'relax': ('U11',)}),
    # ---- ground repairs: pads / pieces that the signal tracks above cut off from their pour
    ('ground repairs', 'HT_GND', 'DRV4.3', 'via:In1.GND', 'F', 0.3, {'relax': ('DRV4',), 'via': (0.8, 0.4)}),
    ('ground repairs', 'GND', (10.5, -55.63, 'B.Cu'), 'via:In1.GND', 'B', 0.3, {'via': (0.8, 0.4)}),
]


def groups():
    out, names = {}, []
    for g, net, a, b, layers, w, o in TABLE:
        if g not in out:
            out[g] = []
            names.append(g)
        opt = dict(layers=layers, w=w, via=VS, margin=3.0, via_cost=20.0, zone_cost=10.0)
        opt.update(o)
        if isinstance(b, str):
            target = b
        else:
            target = "net"
            opt["window"] = [(b[0], b[1])] + list(opt.get("window", []))
        out[g].append(("auto", net, a, target, opt))
    return [(g, out[g]) for g in names]


if __name__ == "__main__":
    R.RELAX_OWN_DOMAIN = True
    R.HARD_ZONES = True
    R.run("s3b", groups(), sys.argv[1:])
