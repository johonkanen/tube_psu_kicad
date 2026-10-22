#!/usr/bin/env python3
"""Sheet 1 - AUX supply (PDF page 1): the flyback auxiliary supply. PWM2 (IW1818) switches the primary
of TR1 (EF20, pins 4/5) from DC+ with the RCD snubber D7 / R72 / R45 || C12; its Vcc comes from 20V
through D10 (startup through R116 / R115 / R114 from DC+, C58 / C51), the current sense from the
shunt R8 || R9 (pins E and I_sense), the feedback from the 5V winding (AUX_FB: R64 || R81 -> R86 ->
Vsense, R84 || R85 || C50 to GND). Primary-side windings: 1-2 -> D5 -> 20V (C1, C39), 2-3 -> D6 -> 5V
(C36, C6, C71). Secondary windings: 10 -> D4 -> 20V_ISO_SEC (C3, C2), 8 -> D14 -> -5V_SEC (C44, C40),
7 -> D29 -> 5V_ISOL (C114, C115), 6 -> D8 -> -100V BIAS (C45, C102); pin 9 = ISO_GND. The outputs go
to the terminals +15V OUT / -5V OUT / -80V OUT / +5V OUT / SEC GND (KiCad refdes P15V_OUT, N5V_OUT,
N80V_OUT, P5V_OUT, SEC_GND) with the bleeders R124 / R123 / R68 / R67.

PDF: DC- = GND, RET_iso / RET_ISO / ISO_GND = ISO_GND (the page joins the terminals RET_iso and
ISO_GND by a bare wire, no part), 20V_ISO_sec = 20V_ISO_SEC, 5v_isol = 5V_ISOL, -100V bias = -100V
BIAS; the PDF net labels d5_A, Sec11, d14_k, d15_K (IPC D5_A, SEC11, D14_K, D15_K) are the winding
ends, wired directly here; aux_fb (two terminals in the PDF) = AUX_FB local labels. This sheet
generates 20V, 5V, 20V_ISO_SEC, -5V_SEC, 5V_ISOL, -100V BIAS and ISO_GND (terminal SEC GND): their
permanent PWR_FLAGs are here; PWM2 Vcc (#00032, fed through D10 / R114 only) has one too."""
from _common import *  # noqa: F401,F403

sh = sheet("01_aux_supply.kicad_sch")

# --- TR1 and the primary-side rectifiers ------------------------------------------------------------
TX, TY = g(150), g(70)
tr = sh.place("EF20", "TR1", TX, TY, value=sh_value("TR1"))
P1, P2, P3, P4, P5 = (tr.pin(str(n)) for n in (1, 2, 3, 4, 5))
P10, P9, P8, P7, P6 = (tr.pin(str(n)) for n in (10, 9, 8, 7, 6))
# pin 1 -> D5 -> 20V rail (raised above the 5V group), C39 / C1 to GND
_, dc, da = horiz2(sh, "D", "D5", TX - g(14), P1[1], sh_value("D5"), left="C", text="above")
sh.wire(da, P1)
x20 = TX - g(24)
R20 = P1[1] - g(10)
sh.wire(dc, (x20, P1[1]), (x20, R20), (TX - g(46), R20))
for x, ref, sym in ((TX - g(32), "C39", "C"), (TX - g(40), "C1", "C_Polarized")):
    _, ct, cb = vert2(sh, sym, ref, x, R20 + g(3), sh_value(ref), top=1)         # pin 1 = 20V
    sh.junction(x, R20)
    if ref == "C39":
        sh.wire(cb, (x - g(8), cb[1]))
    else:
        sh.junction(*cb)
        power_at(sh, "GND", cb, "down")
flagged_power(sh, "20V", TX - g(46), R20)
# pin 2 = GND
sh.wire(P2, left(P2, 2))
power_at(sh, "GND", left(P2, 2), "left")
# pin 3 -> D6 -> 5V rail, C36 / C6 / C71 (pin 2 = 5V) to GND; AUX_FB taken off by a stub label
_, dc, da = horiz2(sh, "D", "D6", TX - g(26), P3[1], sh_value("D6"), left="C", text="below")
sh.wire(da, P3)
xfb = TX - g(16)
sh.junction(xfb, P3[1])
sh.wire((xfb, P3[1]), (xfb, P3[1] + g(8)))
sh.label("AUX_FB", xfb, P3[1] + g(8), 270)
x5 = TX - g(36)
sh.wire(dc, (x5, P3[1]), (TX - g(64), P3[1]))
GR5 = P3[1] + g(6)
for i, ref in enumerate(("C36", "C6", "C71")):
    x = TX - g(42 + 8 * i)
    _, ct, cb = vert2(sh, "C", ref, x, P3[1] + g(3), sh_value(ref), top=2)       # pin 2 = 5V
    sh.junction(x, P3[1])
    if i:
        sh.wire((x + g(8), GR5), cb)
    if i:
        sh.junction(*cb)
power_at(sh, "GND", (TX - g(58), GR5), "down")
flagged_power(sh, "5V", TX - g(64), P3[1])
# pin 4 = DC+, pin 5 = collector (down to PWM2's C pins)
sh.wire(P4, left(P4, 2))
power_at(sh, "DC+", left(P4, 2), "left")
xcol = TX - g(8)
CROW = g(112)
sh.wire(P5, (xcol, P5[1]), (xcol, CROW))

# --- PWM2 with the Vcc network, the snubber, the shunt and the feedback network ------------------
PX, PY = g(70), g(116)
pwm = sh.place("IW1818", "PWM2", PX, PY, value=sh_value("PWM2"))
VCC, VSENSE, ISENSE, E, C8, C7, PGND = (pwm.pin(n) for n in (5, 4, 2, 1, 8, 7, 3))
sh.wire(C8, (xcol, C8[1]))                                       # collector row
sh.wire(C7, right(C7, 2), (C7[0] + g(2), C8[1]))
sh.junction(C7[0] + g(2), C8[1])
sh.wire(PGND, right(PGND, 2))
power_at(sh, "GND", right(PGND, 2), "down")
# snubber: D7 (A at the collector) -> R72 -> node -> R45 || C12 -> DC+
xs = g(120)
_, dt, db = vert2(sh, "D", "D7", xs, CROW - g(3), sh_value("D7"), top="C")         # A = collector
sh.junction(xs, CROW)
_, rt, rb = vert2(sh, "R", "R72", xs, dt[1] - g(3), sh_value("R72"), top=1)        # pin 1 = node
node = rt
_, rt, rb = vert2(sh, "R", "R45", xs, node[1] - g(3), sh_value("R45"), top=1)      # pin 1 = DC+
_, ct, cb = vert2(sh, "C", "C12", xs + g(6), node[1] - g(3), sh_value("C12"), top=1)   # pin 1 = DC+
sh.wire(node, cb)
sh.wire(rt, ct)
sh.junction(*node)
sh.junction(*rt)
power_at(sh, "DC+", rt, "up")
# C15: DC+ decoupling (standalone pair)
_, ct, cb = vert2(sh, "C", "C15", g(100), g(91), sh_value("C15"), top=2)           # pin 2 = DC+
power_at(sh, "DC+", ct, "up")
power_at(sh, "GND", cb, "down")
# Vcc: D10 from 20V, startup chain R116 / R115 / R114 from DC+, C58 / C51, PWR_FLAG (passive feed)
xv = PX - g(18)
NV = VCC[1] - g(12)
sh.wire(VCC, (xv, VCC[1]), (xv, NV))
_, da, dc = horiz2(sh, "D_Schottky", "D10", PX - g(38), NV, sh_value("D10"), left="A")   # A = 20V
sh.wire(da, left(da, 2))
power_at(sh, "20V", left(da, 2), "left")
sh.wire(dc, (xv, NV), (xv + g(4), NV))
sh.junction(xv, NV)
sh.pwr_flag(xv + g(4), NV, 270)
prev = (xv, NV)
for i, r in enumerate(("R114", "R115", "R116")):
    _, rt, rb = vert2(sh, "R", r, xv, NV - g(3) - g(6 * i), sh_value(r), top=1)   # pin 1 = DC+ side
    sh.wire(rb, prev)
    prev = rt
power_at(sh, "DC+", prev, "up")
for x, ref in ((xv - g(12), "C58"), (xv - g(6), "C51")):
    _, ct, cb = vert2(sh, "C", ref, x, NV + g(3), sh_value(ref), top=1)           # pin 1 = Vcc
    sh.junction(x, NV)
    power_at(sh, "GND", cb, "down")
# shunt: E and I_sense tied, R8 || R9 to GND
xe = PX - g(14)
sh.wire(ISENSE, (xe, ISENSE[1]), (xe, E[1]))
sh.wire(E, (xe, E[1]))
sh.junction(xe, E[1])
SROW = E[1] + g(8)
sh.wire((xe, E[1]), (xe, SROW), (xe + g(10), SROW))
_, at, ab = vert2(sh, "R", "R8", xe, SROW + g(3), sh_value("R8"), top=1)          # pin 1 = I_sense
_, bt, bb = vert2(sh, "R", "R9", xe + g(10), SROW + g(3), sh_value("R9"), top=1)
sh.junction(*at)
sh.wire(ab, bb)
sh.junction(*ab)
power_at(sh, "GND", ab, "down")
# feedback: AUX_FB -> R81 || R64 -> node -> R86 -> Vsense; R84 || R85 || C50 node - GND
xn = PX - g(28)
_, rl, rr = horiz2(sh, "R", "R86", PX - g(18), VSENSE[1], sh_value("R86"), left=2, text="below")   # pin 1 = Vsense
sh.wire(rr, VSENSE)
sh.wire((xn, VSENSE[1]), rl)
sh.junction(xn, VSENSE[1])
xl = PX - g(42)
_, rl, rr = horiz2(sh, "R", "R81", PX - g(36), VSENSE[1], sh_value("R81"), left=1, text="above")   # pin 1 = AUX_FB
sh.wire(rr, (xn, VSENSE[1]))
sh.wire(rl, (xl, VSENSE[1]))
sh.junction(xl, VSENSE[1])
sh.wire((xl, VSENSE[1]), (xl - g(4), VSENSE[1]))
sh.label("AUX_FB", xl - g(4), VSENSE[1], 180)
row2 = VSENSE[1] + g(4)
_, rl, rr = horiz2(sh, "R", "R64", PX - g(36), row2, sh_value("R64"), left=1, text="below")       # pin 1 = AUX_FB
sh.wire((xl, VSENSE[1]), (xl, row2), rl)
sh.wire(rr, (xn, row2), (xn, VSENSE[1]))
row3 = row2 + g(4)
sh.wire((xn, row2), (xn, row3))
sh.junction(xn, row2)
for x, ref, sym, top in ((xn - g(6), "C50", "C", 2), (xn, "R84", "R", 1), (xn + g(6), "R85", "R", 1)):
    _, t, b = vert2(sh, sym, ref, x, row3 + g(3), sh_value(ref), top=top,        # node side on top
                    text="left" if x < xn else "right")
    if x != xn:
        sh.wire((xn, row3), t)
        sh.wire((xn, row3 + g(6)), b)
    else:
        sh.junction(*t)
        sh.junction(*b)
power_at(sh, "GND", (xn, row3 + g(6)), "down")

# --- secondary rectifier groups, fanned out on separate rows (nested columns, no crossings) ------
sh.wire(P9, right(P9, 4))
power_at(sh, "ISO_GND", right(P9, 4), "right")
XN = TX + g(26)                                                 # rail start column
groups = [  # pin, column offset, row, diode (ref, pin at the transformer side), rail net, caps (ref, sym, top), cap text
    (P10, 2, g(52), ("D4", "A"), "20V_ISO_SEC", [("C3", "C", 1), ("C2", "C_Polarized", 1)]),
    (P8, 6, g(84), ("D14", "C"), "-5V_SEC", [("C44", "C", 2), ("C40", "C", 2)]),
    (P7, 4, g(100), ("D29", "A"), "5V_ISOL", [("C114", "C", 1), ("C115", "C", 1)]),
    (P6, 2, g(116), ("D8", "C"), "-100V BIAS", [("C45", "C", 2), ("C102", "C_Polarized", 2)]),
]
for pin, dx, row, (dref, dside), rail, caps in groups:
    x = pin[0] + g(dx)
    sh.wire(pin, (x, pin[1]), (x, row))
    _, dl, dr = horiz2(sh, "D", dref, TX + g(18), row, sh_value(dref), left=dside)
    sh.wire((x, row), dl)
    sh.wire(dr, (XN, row), (XN + g(30), row))
    for i, (cref, sym, top) in enumerate(caps):
        cx = XN + g(4 + 8 * i)
        _, ct, cb = vert2(sh, sym, cref, cx, row + g(3), sh_value(cref), top=top)   # rail pin on top
        sh.junction(cx, row)
        if i:
            sh.wire((cx - g(8), cb[1]), cb)
    sh.junction(XN + g(4), row + g(6))
    power_at(sh, "ISO_GND", (XN + g(4), row + g(6)), "down")
    flagged_power(sh, rail, XN + g(30), row)
sh.text("Secondary winding ends (PDF labels Sec11, d14_k, d15_K; IPC SEC11, D14_K, D15_K) and D5_A are wired directly.", TX + g(2), g(134))

# --- terminals with the bleeders -----------------------------------------------------------------
XT = g(292)
y = g(136)
terminal(sh, "SEC_GND", XT, y, "right")
sh.wire((XT - g(20), y), (XT, y))
flagged_power(sh, "ISO_GND", XT - g(20), y)
for i, (tref, rail, rref) in enumerate((("P15V_OUT", "20V_ISO_SEC", "R124"), ("N5V_OUT", "-5V_SEC", "R123"),
                                         ("N80V_OUT", "-100V BIAS", "R68"), ("P5V_OUT", "5V_ISOL", "R67"))):
    y = g(148 + 12 * i)
    terminal(sh, tref, XT, y, "right")
    sh.wire((XT - g(40), y), (XT, y))
    power_at(sh, rail, (XT - g(40), y), "left")
    _, rt, rb = vert2(sh, "R", rref, XT - g(20), y + g(3), sh_value(rref), top=2)   # pin 2 = rail, pin 1 = ISO_GND
    sh.junction(XT - g(20), y)
    power_at(sh, "ISO_GND", rb, "down")
sh.text("Terminals +15V OUT / -5V OUT / -80V OUT / +5V OUT / SEC GND = P15V_OUT / N5V_OUT / N80V_OUT / P5V_OUT / SEC_GND;", g(100), g(200))
sh.text("the PDF joins the terminals RET_iso and ISO_GND by a bare wire (one net ISO_GND, no part).", g(100), g(203))

# --- PDF notes ----------------------------------------------------------------------------------
for i, t in enumerate(("vsense nominal = 1.536 V; vsense OVP threshold = 1.838 V; Isense pk = 1V",
                       "R8/R9 = 3.57R if V1 design is used; Vpeak = 640V with V2 design",
                       "V1 : 67/9/4/54;  V2 : 52/8/3||7/3/3/42;  V3 : 58/9/4/47;  TR1 : core 171nh (winding notes)",
                       "R64 = 39k/ v2 trans;  Vsense @ 1.536V = 5.8368Vaux;  Isense ocp = 1.15V;  V5.1")):
    sh.text(t + " (PDF note).", g(16), g(20 + 3 * i))
sh.text("PWR_FLAGs: 20V, 5V, 20V_ISO_SEC, -5V_SEC, 5V_ISOL, -100V BIAS (rectifier outputs), ISO_GND (SEC GND terminal), PWM2 Vcc (D10 / R114): permanent.", g(16), g(34))
sh.save()
print("sheet01: written")
