#!/usr/bin/env python3
"""Sheet 5 - PFC (PDF page 5): mains input IN1 (RES_IN) / IN2 / PE terminals, inrush resistor R27
bypassed by the relay RL1 (coil on 5V, driven by Q9 from GPIO_BYPASS_RLY through R44, pull-down R32,
C35; freewheel D9 + D28 to 5V), X/Y caps C86 / C85 / C84, common-mode choke CM1, C38 / C81 / C65,
CM4 -> AC1 / AC2 (to the bridge DB1 and the AC measurement, sheet 9), C117, the HF bypass caps
C64 / C66 (AC1 / AC2 to GND), the PFC chokes L2 (AC1 -> PFC DRAIN 1) and L1 (AC2 -> PFC DRAIN 2)
with the switches Q5 / Q6 (GATE1 / GATE2, shunts R93 / R21 -> PFC CURRENT 2+ / 3+) and the SiC
diodes SICD1 / SICD2 to DC+; the bridge DB1 (AC1 / AC2 -> DC+ / GND, drawn standalone as in the
PDF); C82 GND - PE; R4 / R5 / R6 from IN2 to RES_IN.

PDF: gate1 / gate2 = GATE1 / GATE2, "PFC drain 1" / "pfc drain 2" = PFC DRAIN 1 / 2 (one-sheet nets,
wired), "PFC current 2+/3+" = PFC CURRENT 2+ / 3+, res_in / in2 = RES_IN / IN2; the DB1 symbol pin
names AC1 / AC2 (pins 1 / 3) are the other way round than the nets (pin 1 = AC2, pin 3 = AC1).
The common-mode choke is drawn as a pass-through filter (Device:Filter_EMI_LL_1423 with the
Proteus ids, see STATUS.md "Symbol changes"). DC+ and GND are generated here (bridge DB1): their
permanent PWR_FLAGs are on DB1."""
from _common import *  # noqa: F401,F403

sh = sheet("05_pfc.kicad_sch")

TOPR, BOTR = g(70), g(86)                 # the two mains lines (RES_OUT -> L1_PRI2 -> AC1 / IN2 -> L2_PRI2 -> AC2)


def ycap(ref, x, row, up_):
    """Y cap between a line and PE: on `row`, going up (up_) or down, PE local label at the end."""
    if up_:
        _, ct, cb = vert2(sh, "C", ref, x, row - g(3), sh_value(ref), top=2)      # pin 2 = PE
        sh.junction(x, row)
        sh.label("PE", *ct, 90)
    else:
        _, ct, cb = vert2(sh, "C", ref, x, row + g(3), sh_value(ref), top=1)      # pin 1 = line
        sh.junction(x, row)
        sh.label("PE", *cb, 270)


def xcap(ref, x, top):
    """X cap between the two lines (pin `top` on the upper line)."""
    _, ct, cb = vert2(sh, "C", ref, x, (TOPR + BOTR) / 2, sh_value(ref), top=top)
    sh.wire((x, TOPR), ct)
    sh.wire(cb, (x, BOTR))
    sh.junction(x, TOPR)
    sh.junction(x, BOTR)


def choke(ref, x):
    """Common-mode choke centred at x between the lines; returns (x_left, x_right) of its verticals."""
    cm = sh.place("SCF20-05-550", ref, x, (TOPR + BOTR) / 2, value=sh_value(ref),
                  ref_at=(x, TOPR - g(2), 0, None), value_at=(x, BOTR + g(2), 0, None))
    for pin, row in ((1, TOPR), (2, TOPR), (3, BOTR), (4, BOTR)):
        p = cm.pin(pin)
        sh.wire(p, (p[0], row))
    return cm.pin(1)[0], cm.pin(2)[0]


# --- relay / inrush block above the top line ------------------------------------------------------
RX, RY = g(44), g(48)
rl = sh.place("SONGLE_RELAY", "RL1", RX, RY, rot=180, value=sh_value("RL1"))
COM, NC, NO, C1, C2 = (rl.pin(n) for n in (1, 2, 3, 4, 5))         # rot 180: contacts left, coil right
sh.no_connect(*NC)
terminal(sh, "IN1", g(24), NO[1], "left")
sh.wire((g(24), NO[1]), NO)
xr = RX - g(12)
sh.junction(xr, NO[1])
_, rt, rb = vert2(sh, "R", "R27", xr, NO[1] + g(3), sh_value("R27"), top=2, text="left")   # pin 2 = RES_IN
sh.wire((xr - g(4), NO[1]), (xr - g(4), NO[1] - g(4)))
sh.junction(xr - g(4), NO[1])
sh.label("RES_IN", xr - g(4), NO[1] - g(4), 90)
xo = RX - g(10)                                                     # RES_OUT down to the top line
sh.wire(COM, (xo, COM[1]), (xo, rb[1]))
sh.wire(rb, (xo, rb[1]), (xo, TOPR))
sh.junction(xo, rb[1])
# coil: C1 on 5V, C2 switched by Q9; freewheel D9 + D28 to 5V
sh.wire(C1, right(C1, 2))
power_at(sh, "5V", right(C1, 2), "right")
QX, QY = g(76), RY + g(8)
q9 = sh.place("Q_NMOS_DGS", "Q9", QX, QY, value=sh_value("Q9"))
D9_, G9, S9 = q9.pin(1), q9.pin(2), q9.pin(3)
xd = D9_[0]
sh.wire(C2, (xd, C2[1]))
sh.wire((xd, RY - g(6)), D9_)
sh.junction(xd, C2[1])
power_at(sh, "GND", S9, "down")
_, da, dc = horiz2(sh, "D_Schottky", "D9", xd + g(6), RY - g(6), sh_value("D9"), left="A")
_, ea, ec = horiz2(sh, "D_Schottky", "D28", xd + g(16), RY - g(6), sh_value("D28"), left="A")
sh.wire((xd, RY - g(6)), da)
sh.wire(dc, ea)
sh.wire(ec, right(ec, 2))
power_at(sh, "5V", right(ec, 2), "up")
# gate: GPIO_BYPASS_RLY -> R44 -> gate, C35 gate - GND, R32 pull-down
_, r2, r1 = horiz2(sh, "R", "R44", QX - g(12), G9[1], sh_value("R44"), left=2, text="above")   # pin 1 = gate
sh.wire(r1, G9)
xg = QX - g(6)
sh.junction(xg, G9[1])
_, ct, cb = vert2(sh, "C", "C35", xg, G9[1] + g(3), sh_value("C35"), top=1)       # pin 1 = gate
power_at(sh, "GND", cb, "down")
xl = QX - g(18)
sh.wire(r2, (xl, G9[1]))
sh.glabel("GPIO_BYPASS_RLY", xl, G9[1], 180)
sh.junction(xl, G9[1])
_, rt, rb = vert2(sh, "R", "R32", xl, G9[1] + g(3), sh_value("R32"), top=1)      # pin 1 = GPIO_BYPASS_RLY
power_at(sh, "GND", rb, "down")

# --- the mains lines: terminals, X/Y caps, chokes ------------------------------------------------
terminal(sh, "IN2", g(24), BOTR, "left")
sh.wire((g(24), BOTR), (g(40), BOTR))
sh.wire((g(40), BOTR), (g(40), BOTR + g(4)))
sh.junction(g(40), BOTR)
sh.label("IN2", g(40), BOTR + g(4), 270)
ycap("C85", g(96), TOPR, True)
ycap("C84", g(96), BOTR, False)
xcap("C86", g(104), 1)                                          # pin 1 = RES_OUT
cl, cr = choke("CM1", g(118))
sh.wire((xo, TOPR), (cl, TOPR))
sh.wire((g(40), BOTR), (cl, BOTR))
ycap("C81", g(132), TOPR, True)
ycap("C65", g(132), BOTR, False)
xcap("C38", g(140), 1)                                          # pin 1 = L1_PRI2
dl, dr = choke("CM4", g(154))
sh.wire((cr, TOPR), (dl, TOPR))
sh.wire((cr, BOTR), (dl, BOTR))
sh.label("L1_PRI2", cr + g(2), TOPR - g(4), 0)                  # one-sheet nets, named as in the PDF
sh.wire((cr + g(2), TOPR), (cr + g(2), TOPR - g(4)))
sh.junction(cr + g(2), TOPR)
sh.label("L2_PRI2", cr + g(2), BOTR + g(4), 0)
sh.wire((cr + g(2), BOTR), (cr + g(2), BOTR + g(4)))
sh.junction(cr + g(2), BOTR)
xcap("C117", g(168), 1)                                         # pin 1 = AC1
# AC1 / AC2 global labels on stubs, AC2 line drops to a lower row for the PFC section
sh.wire((g(174), TOPR), (g(174), TOPR - g(4)))
sh.junction(g(174), TOPR)
sh.glabel("AC1", g(174), TOPR - g(4), 90)
sh.wire((g(174), BOTR), (g(174), BOTR + g(4)))
sh.junction(g(174), BOTR)
sh.glabel("AC2", g(174), BOTR + g(4), 270)
AC2R = g(120)
xdrop = g(180)
sh.wire((dr, BOTR), (xdrop, BOTR), (xdrop, AC2R))
# HF bypass caps C64 (AC1 - GND) and C66 (AC2 - GND)
_, ct, cb = vert2(sh, "C", "C64", g(188), TOPR + g(3), sh_value("C64"), top=1)   # pin 1 = AC1
sh.junction(g(188), TOPR)
power_at(sh, "GND", cb, "down")
_, ct, cb = vert2(sh, "C", "C66", g(188), AC2R + g(3), sh_value("C66"), top=1)   # pin 1 = AC2
sh.junction(g(188), AC2R)
power_at(sh, "GND", cb, "down")

# --- PFC switches: L2 / Q5 / SICD1 on the AC1 line, L1 / Q6 / SICD2 on the AC2 line -------------
XDC = g(236)
for row, lref, lleft, qref, gate, dref, rref, cur in (
        (TOPR, "L2", "pri1", "Q5", "GATE1", "SICD1", "R93", "PFC CURRENT 2+"),
        (AC2R, "L1", "pri2", "Q6", "GATE2", "SICD2", "R21", "PFC CURRENT 3+")):
    # 5.2 (NR 5.2): sendust toroid with two leads (5.1 RM8 pri1 / pri2 = toroid pins 1 / 2, same orientation)
    t = -1 if lleft == "pri2" else 1
    _, l1, l2 = horiz2(sh, "L_TOROID", lref, g(200), row, sh_value(lref), left={"pri1": 1, "pri2": 2}[lleft],
                       ref_at=(g(200), row + t * g(5), 90, None), value_at=(g(200), row + t * g(3), 90, None))
    sh.wire((dr if row == TOPR else xdrop, row), l1)
    q = sh.place("Q_NMOS_GDS", qref, g(212), row + g(6), value=sh_value(qref))
    G, D, S = q.pin(1), q.pin(2), q.pin(3)
    node = (D[0], row)                                          # PFC DRAIN n node
    sh.wire(l2, node)
    sh.wire(node, D)
    sh.junction(*node)
    sh.label("PFC_DRAIN_1" if qref == "Q5" else "PFC_DRAIN_2", node[0] - g(4), row, 0)   # 5.2: named (HV class)
    _, a, k = horiz2(sh, "C3D02060A", dref, g(224), row, sh_value(dref), left="A")
    sh.wire(node, a)
    sh.wire(k, (XDC, row))
    glabel_left(sh, gate, G, 4)
    cn = down(S, 4)
    sh.wire(S, cn)
    sh.wire(cn, right(cn, 4))
    sh.junction(*cn)
    sh.glabel(cur, *right(cn, 4), 0)
    _, rt, rb = vert2(sh, "R", rref, cn[0], cn[1] + g(3), sh_value(rref), top=1)   # pin 1 = PFC CURRENT n+
    power_at(sh, "GND", rb, "down")
sh.wire((XDC, AC2R), (XDC, TOPR), (XDC, TOPR - g(6)))
sh.junction(XDC, TOPR)
power_at(sh, "DC+", (XDC, TOPR - g(6)), "up")
sh.text("PFC drain 1 / pfc drain 2 (PDF labels) are the wired nodes L2-Q5-SICD1 / L1-Q6-SICD2.", g(180), g(150))
sh.text("5.2: L1 / L2 = sendust toroids (OD 31.5 x 16.7 mm, 2 leads, NR 5.2); value = measured L at 0 A / PFC peak (TBD), footprint phase 3.", g(180), g(153))

# --- bridge rectifier DB1 (standalone, as in the PDF): generates DC+ and GND -> permanent PWR_FLAGs
DBX, DBY = g(270), g(40)
db = sh.place("TBS22K", "DB1", DBX, DBY, value=sh_value("DB1"))
P1, P2, P3, P4 = (db.pin(n) for n in (1, 2, 3, 4))
sh.wire(P3, up(P3, 2))
sh.glabel("AC1", *up(P3, 2), 90)
sh.wire(P1, down(P1, 2))
sh.glabel("AC2", *down(P1, 2), 270)
sh.wire(P2, right(P2, 4))
flagged_power(sh, "DC+", *right(P2, 4))
sh.wire(P4, left(P4, 4))
flagged_power(sh, "GND", *left(P4, 4))
sh.text("TBS22k - diode bridge (PDF). DB1 pin 1 = AC2, pin 3 = AC1 (the symbol pin names are swapped against the nets).", g(236), g(16))
sh.text("DC+ and GND PWR_FLAGs: permanent (generated here).", g(236), g(19))
# C82: GND - PE
_, ct, cb = vert2(sh, "C", "C82", g(300), g(78), sh_value("C82"), top=2)         # pin 2 = PE
sh.label("PE", *ct, 90)
power_at(sh, "GND", cb, "down")
terminal(sh, "PE", g(300), g(100), "down")
sh.wire((g(300), g(100)), (g(300), g(96)))
sh.label("PE", g(300), g(96), 90)

# --- R4 / R5 / R6: IN2 -> RES_IN ----------------------------------------------------------------
Y6 = g(150)
sh.label("IN2", g(40), Y6, 180)
prev = (g(40), Y6)
for i, r in enumerate(("R4", "R5", "R6")):
    _, a, b = horiz2(sh, "R", r, g(48) + g(10 * i), Y6, sh_value(r), left=2)        # pin 2 = IN2 side
    sh.wire(prev, a)
    prev = b
sh.wire(prev, (prev[0] + g(4), Y6))
sh.label("RES_IN", prev[0] + g(4), Y6, 0)

sh.text("PDF notes: DEBB33F222KN3A/ 2n2, T60405-R6131-X204 VAC; R463F247040N0M/ 47n 305VAC, R463F310040M1M/ 100nf 310VAC;", g(24), g(166))
sh.text("HF bypass for low side bridge rectifier diodes (C64 / C66). V5.1 (PDF hand note). PE is a one-sheet net (local labels).", g(24), g(169))
sh.save()
print("sheet05: written")
