#!/usr/bin/env python3
"""Sheet 2 - DHB gate drive (PDF page 2). 5.2: two UCC21520DWR isolated dual gate drivers (NEXT_REVISION.md 3a,
replacing the Si8275BB of 5.1): DRV5 for the primary half-bridge (5V / 15V side, outputs DHB_HI_GATE /
DHB_LOW_GATE) and DRV6 for the secondary (5V_ISOL / 15V_ISO_SEC, outputs DHB_HI_GATE_SEC / DHB_LOW_GATE_SEC),
each with a bootstrap diode + resistor + cap for the high side, pull-downs on the PWM inputs, a dead-time
resistor (R127 / R128 10k = 100 ns hardware backstop; the FPGA dead time is 150 ns total, NR 2.7) with its noise
cap, and the DISABLE input brought out (NR 3.3): DAB_DIS from J2-18 on DRV5 (pull-down R129 = enabled by
default, as the 5.1 EN tied high; bypass C120) and, through ISO2 channel C, DAB_DIS_SEC on DRV6.
DRV6's input side stays on the secondary domain (ISO2 carries its PWM, as in 5.1) - see kicad_next/CHANGES_5_2.md.
R40 / R25 (the Si8274 dead-time resistors on Si8275 NC pin 6) are removed."""
from _common import *  # noqa: F401,F403

sh = sheet("02_dhb_gate_drive.kicad_sch")

# Primary driver. PDF label PRI_DHB_LO on INA = IPC net B12 (J2 pin B12); the bootstrap is on the B side
# (VDDB/OUTB/VSSB = high side), INB = PRI_DHB_HI.
ucc21520_cell(sh, "DRV5", g(100), g(44), vdd="5V", gnd="GND",
              pwm=("B12", ("R74", "10k")), nc1=("PRI_DHB_HI", ("R73", "10k")), dt=("R127", "10k", "C118", "100p"),
              cdec=("C94", "100n", 1),
              boot=(("D19", "S1M"), ("R41", "2R"), ("C92", "1u", 2)), rail="15V",
              railcaps=[("C95", "4.7u", 2), ("C96", "1u", 1)], boot_side="B",
              vo_hi="DHB_HI_GATE", src_hi="DHB_HI_SOURCE", vo_lo="DHB_LOW_GATE",
              dis=("DAB_DIS", ("R129", "10k"), ("C120", "1n")))
sh.text("PDF label PRI_DHB_LO = net B12 (J2 pin B12); DC- = GND.", g(48), g(74))
sh.text("UCC21520: DT = 10 ns/kOhm x R_DT -> R127 / R128 10k = 100 ns minimum, not additive (FPGA dead time 150 ns total, NR 2.7).", g(48), g(77))
sh.text("DAB_DIS (J2-18, FPGA): high = all four DAB gates off; R129 pull-down = enabled when the FPGA does not drive it.", g(48), g(80))

# Secondary driver: bootstrap on the A side (VDDA/OUTA/VSSA = high side); DISABLE from ISO2 channel C.
ucc21520_cell(sh, "DRV6", g(100), g(130), vdd="5V_ISOL", gnd="ISO_GND",
              pwm=("ISO_SEC_DHB_HI", ("R75", "10k")), nc1=("ISO_SEC_DHB_LO", ("R76", "10k")),
              dt=("R128", "10k", "C119", "100p"), cdec=("C93", "100n", 1),
              boot=(("D18", "S1M"), ("R46", "2R"), ("C46", "1u", 2)), rail="15V_ISO_SEC",
              railcaps=[("C72", "4.7u", 2), ("C43", "1u", 2)], boot_side="A",
              vo_hi="DHB_HI_GATE_SEC", src_hi="DHB_HI_SOURCE_SEC", vo_lo="DHB_LOW_GATE_SEC",
              dis=("DAB_DIS_SEC", None, None))
sh.text("5.2: DRV5 / DRV6 = UCC21520DWR (5.7 kVrms reinforced, 8 V output UVLO); both sides of each driver stay in one isolation domain.",
        g(48), g(160))
sh.text("DRV6 input side on the secondary (5V_ISOL / ISO_GND): PWM and DISABLE come through ISO2 (CA-IS3761LW) channels A / B / C.",
        g(48), g(163))

# Rails entering this sheet (5V, 5V_ISOL, 15V_ISO_SEC, ISO_GND) are generated on sheet 1 (AUX supply),
# where their PWR_FLAGs are.
sh.text("The rails entering this sheet (5V, 5V_ISOL, 15V_ISO_SEC, ISO_GND) have their PWR_FLAGs on sheet 1 (AUX supply).",
        g(48), g(170))
sh.save()
print("sheet02: written")
