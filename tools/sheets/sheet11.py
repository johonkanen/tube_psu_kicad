#!/usr/bin/env python3
"""Sheet 11 - Startup circuit (PDF page 11): the DC+ bulk capacitor bank C73/C29/C56/C28/C37
and the 15V buffer C14. The Proteus page also joins the terminals HT_AUX and 6V3 by a bare
wire (no part on this page); HT_AUX is only an alias of the 6V3 net."""
from _common import *  # noqa: F401,F403

sh = sheet("11_startup.kicad_sch")

TOP = g(40)     # DC+ rail
BOT = g(64)     # GND rail
X0 = g(40)      # rail start (power symbols)
bank = [("C", "C73", "2.2u"), ("C_Polarized", "C29", "82u"), ("C_Polarized", "C56", "82u"),
        ("C_Polarized", "C28", "82u"), ("C_Polarized", "C37", "82u")]
xs = [X0 + g(12 * (i + 1)) for i in range(len(bank))]
for x, (sym, ref, val) in zip(xs, bank):
    _, pt, pb = vert2(sh, sym, ref, x, g(52), val, top=1)     # pin 1 = DC+ side
    sh.wire(pt, (x, TOP))
    sh.wire(pb, (x, BOT))
# rails, DC+ / GND power symbols at the left end (PDF: terminals DC+ and GND)
sh.wire((X0, TOP), (xs[-1], TOP))
sh.wire((X0, BOT), (xs[-1], BOT))
for x in xs[:-1]:
    sh.junction(x, TOP)
    sh.junction(x, BOT)
# DC+ and GND come from the PFC bridge (sheet 5), where their PWR_FLAGs are
power_at(sh, "DC+", (X0, TOP), "up")
power_at(sh, "GND", (X0, BOT), "down")

# C14: 15V buffer (PDF: 15V terminal to the DC- = GND rail)
XC = xs[-1] + g(16)
_, pt, pb = vert2(sh, "C", "C14", XC, g(52), "4.7u", top=1)    # pin 1 = 15V
sh.wire(pb, (XC, BOT))
sh.wire((xs[-1], BOT), (XC, BOT))
sh.junction(xs[-1], BOT)
sh.wire(pt, (XC, g(40)))
power_at(sh, "15V", (XC, g(40)), "up")   # 15V is generated on sheet 1 (AUX supply), PWR_FLAG there

sh.text("Bulk capacitors of the DC link (C29/C56/C28/C37: EEE-FTE221XAP note in the PDF).", X0, g(74))
sh.text("PDF terminal DC- = net GND. PWR_FLAGs: 15V on sheet 1 (AUX supply), DC+ and GND on sheet 5 (bridge DB1).", X0, g(78))
sh.text("The PDF page also wires the terminals HT_AUX and 6V3 together: HT_AUX is an alias of the 6V3 net (no part here).", X0, g(86))
sh.save()
print("sheet11: written")
