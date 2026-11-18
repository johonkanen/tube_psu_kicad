#!/usr/bin/env python3
"""Sheet 10 - PFC current measurement (PDF page 10, untitled): U4 dual op-amp (5.2: LMH6643, NR 4.10b), U4:A
amplifies PFC CURRENT 2+ -> PFC_I1_MEAS, U4:B PFC CURRENT 3+ -> PFC_I2_MEAS, both biased at
+1V65_BIAS (bias resistor with a 20p cap in parallel), +3V3 decoupling C87."""
from _common import *  # noqa: F401,F403

sh = sheet("10_pfc_current_measurement.kicad_sch")

# U4:A (pins 3/2/1): R60 pin 1 = +1V65_BIAS, C106 pin 1 = +1V65_BIAS; R96 pin 2 at the op-amp,
# C88 pin 1 at the label
lmh6658_diffamp(sh, "U4", 1, g(100), g(50), inp=("PFC CURRENT 2+", ("R33", "330R")),
                bias=("R60", "6.8k"), bias_top=1, cbias=("C106", "20p", 1), inn_gnd=("R97", "330R"),
                fb=("R98", "6.8k"), cfb=("C113", "20p"), rout=("R96", "100"), rout_amp=2,
                out_label="PFC_I1_MEAS", cout=("C88", "100p"), cout_label=1)
# U4:B (pins 5/6/7): R100 pin 2 = +1V65_BIAS, C107 pin 1 = +1V65_BIAS; R61 pin 2 at the op-amp,
# C77 pin 1 at the label
lmh6658_diffamp(sh, "U4", 2, g(100), g(110), inp=("PFC CURRENT 3+", ("R62", "330R")),
                bias=("R100", "6.8k"), bias_top=2, cbias=("C107", "20p", 1), inn_gnd=("R94", "330R"),
                fb=("R95", "6.8k"), cfb=("C112", "20p"), rout=("R61", "100"), rout_amp=2,
                out_label="PFC_I2_MEAS", cout=("C77", "100p"), cout_label=1)
# U4 supply (unit 3) with the decoupling cap C87 (pin 1 = +3V3)
u = sh.place("LMH6643", "U4", g(180), g(80), unit=3, value=sh_value("U4"))
VP, VN = u.pin(8), u.pin(4)
top = (VP[0], VP[1] - g(2))
sh.wire(VP, top)
power_at(sh, "+3V3", top, "up")
_, ct, cb = vert2(sh, "C", "C87", g(196), VP[1] + g(1), "1u", top=1)
sh.wire(top, (g(196), top[1]), ct)
sh.junction(*top)
power_at(sh, "GND", cb, "down")
power_at(sh, "GND", VN, "down")

sh.text("2k = 22k||2.2k (PDF hand note, twice on the page).", g(60), g(150))
sh.text("5.2: legs already balanced (C113 / C106, C112 / C107 20p): tau = 6.8k * 20p = 136 ns ~ 0.54 nH / 4 mOhm (NR 4.11); offset calibrated (LMH6643 Vos).", g(60), g(153))
sh.save()
print("sheet10: written")
