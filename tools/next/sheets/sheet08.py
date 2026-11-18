#!/usr/bin/env python3
"""Sheet 8 - Current measurement (PDF page 8): U1 dual op-amp (5.2: LMH6643, NR 4.10b; 5.1 LMH6658), U1:B
amplifies DHB_CURRENT -> DHB_I_MEAS, U1:A HEATER_CURRENT -> HEATER_I_MEAS, both biased at +1V65_BIAS.

5.2 (NR 4.11): shunt-ESL compensation with balanced legs - the feedback cap (C63 / C11) gets a matching cap
from the + input to +1V65_BIAS (C122 / C123), tau = Rfb * C ~ L/R of the 4 mOhm shunt (~0.5-0.8 nH incl. the
Kelvin loop -> 125-200 ns): DHB 15k * 12p = 180 ns, HEATER 33k * 5.6p = 185 ns (5.1: 20 pF on the - leg only,
300 / 660 ns). Start values - tune on the bench (spike = C too small, slow over/undershoot = too large).
U1 decoupling C124 100n + C125 1u at pin 8 (NR 4.6)."""
from _common import *  # noqa: F401,F403

sh = sheet("08_current_measurement.kicad_sch")

# U1:B (pins 5/6/7): R105 pin 1 = +1V65_BIAS
lmh6658_diffamp(sh, "U1", 2, g(100), g(50), inp=("DHB_CURRENT", ("R104", "330R")),
                bias=("R105", "15k"), bias_top=1, cbias=("C122", sh_value("C122"), 1), inn_gnd=("R101", "330R"),
                fb=("R102", "15k"), cfb=("C63", sh_value("C63")), rout=("R42", "33"), out_label="DHB_I_MEAS",
                cout=("C26", "na"))
# U1:A (pins 3/2/1): R103 pin 2 = +1V65_BIAS
lmh6658_diffamp(sh, "U1", 1, g(100), g(110), inp=("HEATER_CURRENT", ("R106", "330R")),
                bias=("R103", "33k"), bias_top=2, cbias=("C123", sh_value("C123"), 1), inn_gnd=("R29", "330R"),
                fb=("R89", "33k"), cfb=("C11", sh_value("C11")), rout=("R35", "33R"), out_label="HEATER_I_MEAS",
                cout=("C10", "na"))
# U1 supply (unit 3) with the decoupling caps C124 / C125 (pin 1 = +3V3), NR 4.6
u = sh.place("LMH6643", "U1", g(180), g(80), unit=3, value=sh_value("U1"))
VP, VN = u.pin(8), u.pin(4)
top = (VP[0], VP[1] - g(2))
sh.wire(VP, top)
power_at(sh, "+3V3", top, "up")
for i, (ref, val) in enumerate((("C124", sh_value("C124")), ("C125", sh_value("C125")))):
    x = g(196 + 8 * i)
    _, ct, cb = vert2(sh, "C", ref, x, VP[1] + g(1), val, top=1)
    sh.wire((x - g(8), top[1]) if i else top, (x, top[1]), ct)
    power_at(sh, "GND", cb, "down")
sh.junction(*top)
sh.junction(g(196), top[1])
power_at(sh, "GND", VN, "down")

sh.text("C10 / C26 value 'na' (not assembled) in Proteus, pads in the layout. PDF terminals DC- = GND.", g(60), g(150))
sh.text("2k = 22k||2.2k (PDF hand note).", g(60), g(153))
sh.text("5.2: LMH6643 Vos <= 5 mV = 1.25 A on 4 mOhm: zero-current offset calibrated at start-up (firmware).", g(60), g(156))
sh.save()
print("sheet08: written")
