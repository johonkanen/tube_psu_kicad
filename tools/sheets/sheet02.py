#!/usr/bin/env python3
"""Sheet 2 - DHB gate drive (PDF page 2): two Si8274 isolated half-bridge drivers, DRV5 for the
primary (5V / 20V side, outputs DHB_HI_GATE / DHB_LOW_GATE) and DRV6 for the secondary
(5V_ISOL / 20V_ISO_SEC, outputs DHB_HI_GATE_SEC / DHB_LOW_GATE_SEC), each with a bootstrap
diode + resistor + cap for the high side and pull-downs on the PWM inputs."""
from _common import *  # noqa: F401,F403

sh = sheet("02_dhb_gate_drive.kicad_sch")

# Primary driver. PDF label PRI_DHB_LO on pin 1 = IPC net B12 (J2 pin B12); the bootstrap is on
# the B side (VDDB/VOB/GNDB = high side).
si8274_cell(sh, "DRV5", g(100), g(44), vdd="5V", gnd="GND",
            pwm=("B12", ("R74", "10k")), nc1=("PRI_DHB_HI", ("R73", "10k")), dt=("R40", "82k"),
            cdec=("C94", "100n", 1),
            boot=(("D19", "S1M"), ("R41", "2R"), ("C92", "1u", 2)), rail="20V",
            railcaps=[("C95", "4.7u", 2), ("C96", "1u", 1)], boot_side="B",
            vo_hi="DHB_HI_GATE", src_hi="DHB_HI_SOURCE", vo_lo="DHB_LOW_GATE")
sh.text("PDF label PRI_DHB_LO = net B12 (J2 pin B12); DC- = GND.", g(48), g(74))
sh.text("DT = 173ns; DT(ns) = 2.02*Res(k)+7.77 (PDF note).", g(48), g(77))
sh.text("RGL34K, possible option for charge pump gate driver (PDF note).", g(48), g(80))

# Secondary driver: bootstrap on the A side (VDDA/VOA/GNDA = high side).
si8274_cell(sh, "DRV6", g(100), g(130), vdd="5V_ISOL", gnd="ISO_GND",
            pwm=("ISO_SEC_DHB_HI", ("R75", "10k")), nc1=("ISO_SEC_DHB_LO", ("R76", "10k")),
            dt=("R25", "82k"), cdec=("C93", "100n", 1),
            boot=(("D18", "S1M"), ("R46", "2R"), ("C46", "1u", 2)), rail="20V_ISO_SEC",
            railcaps=[("C72", "4.7u", 2), ("C43", "1u", 2)], boot_side="A",
            vo_hi="DHB_HI_GATE_SEC", src_hi="DHB_HI_SOURCE_SEC", vo_lo="DHB_LOW_GATE_SEC")
sh.text("Pin 2 (NC1) of both drivers carries a signal in Proteus (PRI_DHB_HI / ISO_SEC_DHB_LO); on the Si8274 it is a no-connect pin.",
        g(48), g(160))

# Rails entering this sheet: generated on sheet 1 (AUX supply: 5V, 5V_ISOL, 20V_ISO_SEC; ISO_GND
# through the SEC GND terminal). PWR_FLAGs here until sheet 1 is drawn, one flag per rail.
sh.text("PWR_FLAGs of the rails entering this sheet (5V, 5V_ISOL, 20V_ISO_SEC, ISO_GND): to be moved to sheet 1 (AUX supply) when it is drawn.",
        g(48), g(170))
for i, net in enumerate(["5V", "5V_ISOL", "20V_ISO_SEC"]):
    flagged_power(sh, net, g(52 + 16 * i), g(176))
flagged_power(sh, "ISO_GND", g(100), g(176))
sh.save()
print("sheet02: written")
