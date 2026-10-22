#!/usr/bin/env python3
"""Sheet 8 - Current measurement (PDF page 8): U1 LMH6658 dual op-amp, U1:B amplifies
DHB_CURRENT -> DHB_I_MEAS, U1:A HEATER_CURRENT -> HEATER_I_MEAS, both biased at +2V5_BIAS."""
from _common import *  # noqa: F401,F403

sh = sheet("08_current_measurement.kicad_sch")

# U1:B (pins 5/6/7): R105 pin 1 = +2V5_BIAS
lmh6658_diffamp(sh, "U1", 2, g(100), g(50), inp=("DHB_CURRENT", ("R104", "330R")),
                bias=("R105", "15k"), bias_top=1, inn_gnd=("R101", "330R"), fb=("R102", "15k"),
                cfb=("C63", "20p"), rout=("R42", "33"), out_label="DHB_I_MEAS", cout=("C26", "na"))
# U1:A (pins 3/2/1): R103 pin 2 = +2V5_BIAS
lmh6658_diffamp(sh, "U1", 1, g(100), g(110), inp=("HEATER_CURRENT", ("R106", "330R")),
                bias=("R103", "33k"), bias_top=2, inn_gnd=("R29", "330R"), fb=("R89", "33k"),
                cfb=("C11", "20p"), rout=("R35", "33R"), out_label="HEATER_I_MEAS", cout=("C10", "na"))
# U1 supply (unit 3)
u = sh.place("LMH6658", "U1", g(180), g(80), unit=3, value="LMH6658")
power_at(sh, "+3V3", u.pin(8), "up")
power_at(sh, "GND", u.pin(4), "down")

sh.text("C10 / C26 value 'na' (not assembled) in Proteus, pads in the layout. PDF terminals DC- = GND.", g(60), g(150))
sh.text("2k = 22k||2.2k (PDF hand note).", g(60), g(153))
sh.save()
print("sheet08: written")
