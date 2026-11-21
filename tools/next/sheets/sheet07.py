#!/usr/bin/env python3
"""Sheet 7 - DHB (PDF page 7): the dual half-bridge. Primary: Q19 / Q7 (DC+ -> DHB_HI_SOURCE ->
DHB_CURRENT -> R83 4m -> GND), C47 / C54 with the DHB_CAP node -> TR3 primary (5.2: EC42/15, L3 removed),
C67 / C70 across DC+ - DHB_CURRENT. Secondary: Q21 / Q8 (420V -> DHB_HI_SOURCE_SEC -> ISO_GND), C16 /
C55 with the TRANS_SEC node at TR3's secondary, C89 / C90 on 420V. 5.2: 2 x 220k balancing resistors
across each split cap (R143-R146 primary, R147-R150 secondary, NR 2.8; secondary since 2026-11-21:
R150 + R149 across C16, R148 + R147 across C55). Every MOSFET gate has the same
network: global gate label -> 40R, with a Schottky diode + 3.3R turn-off path, optionally a 10k
pull-down to the source (high side) or GND (Q7). The 420V rail: terminal +400V (P400V), caps C101 /
C91 / C30 / C19 / C99 / C100 to ISO_GND (terminal GND is on ISO_GND), dividers R23 / R34 / R39 ->
CUK_CAP_MEAS2 (R38, C27) and R118 / R119 / R120 -> CUK_CAP_MEAS-.

PDF: DHB_HI_gate / DHB_low_gate / DHB_HI_gate_sec / DHB_low_gate_sec / DHB_HI_SOURCE_sec / dhb_current /
trans_pri / trans_sec / DHB_cap / iso_GND / Cuk_cap_meas2 = IPC names, DC- = GND; terminal GND is on
ISO_GND; the terminals SEC_GND and ISO_GND are joined by a bare wire (no part). C91 (hidden refdes in
the PDF) is drawn next to C101. The C47/C54 and C16/C55 columns cross the source rows without a
junction, as in the PDF."""
from _common import *  # noqa: F401,F403

sh = sheet("07_dhb.kicad_sch")


def gate_net(sh, G, label, r_on, r_off, d, pull=None):
    """Gate network at the gate pin end G (wire goes left): global label -> r_on (pin 1 at the label)
    -> node; diode d (cathode at the label) + r_off (pin 1 at the diode) on the row below; pull =
    (rref, "gnd") / (rref, "src") puts a pull-down (pin 1 at the node) under the node, to GND or to the
    source row (node column, 10 grid units below the gate; the caller wires it). Returns the node x."""
    gx, gy = G
    xn, xl, rb = gx - g(4), gx - g(24), gy + g(4)
    _, a1, a2 = horiz2(sh, "R", r_on, xn - g(10), gy, sh_value(r_on), left=1, text="above")
    sh.wire((xl - g(2), gy), a1)
    sh.wire(a2, G)
    sh.glabel(label, xl - g(2), gy, 180)
    sh.junction(xl, gy)
    sh.junction(xn, gy)
    _, dc, da = horiz2(sh, "D_Schottky", d, xl + g(4), rb, sh_value(d), left="C", text="below")
    _, f1, f2 = horiz2(sh, "R", r_off, xn - g(6), rb, sh_value(r_off), left=1, text="below")
    sh.wire((xl, gy), (xl, rb), dc)
    sh.wire(da, f1)
    sh.wire(f2, (xn, rb), (xn, gy))
    if pull:
        rref, to = pull
        _, pt, pb = vert2(sh, "R", rref, xn, rb + g(3), sh_value(rref), top=1)   # pin 1 = node
        sh.junction(*pt)
        if to == "gnd":
            power_at(sh, "GND", pb, "down")
    return xn


# --- primary half-bridge --------------------------------------------------------------------------
QX, Y1 = g(52), g(40)
XA = QX + g(2)
DCP, SR, CAPR, HC = g(32), g(50), g(42), g(72)
q19 = sh.place("Q_NMOS_GDS", "Q19", QX, Y1, value=sh_value("Q19"),
               ref_at=(QX + g(4), Y1 - g(4), 0, "left"), value_at=(QX + g(4), Y1 - g(6), 0, "left"))
q7 = sh.place("Q_NMOS_GDS", "Q7", QX, Y1 + g(20), value=sh_value("Q7"),
              ref_at=(QX + g(4), Y1 + g(16), 0, "left"), value_at=(QX + g(4), Y1 + g(14), 0, "left"))
sh.wire(q19.pin(2), (XA, DCP))
power_at(sh, "DC+", (XA, DCP), "up")
sh.junction(XA, DCP)
sh.wire(q19.pin(3), q7.pin(2))                     # DHB_HI_SOURCE node on column A
sh.junction(XA, SR)
sh.wire(q7.pin(3), (XA, HC))
sh.junction(XA, HC)
_, rt, rb = vert2(sh, "R", "R83", XA, HC + g(3), sh_value("R83"), top=1)        # pin 1 = DHB_CURRENT
power_at(sh, "GND", rb, "down")
xn = gate_net(sh, q19.pin(1), "DHB_HI_GATE", "R26", "R53", "D30", pull=("R22", "src"))
sh.wire((xn - g(4), SR), (xn, SR))                 # R22 pin 2 on the source row
sh.wire((xn, SR), (XA, SR))
sh.junction(xn, SR)
sh.glabel("DHB_HI_SOURCE", xn - g(4), SR, 180)
gate_net(sh, q7.pin(1), "DHB_LOW_GATE", "R90", "R92", "D34", pull=("R70", "gnd"))
# C47 / C54 column (crosses the source row), DHB_CAP -> L3 -> TR3 primary
xc = QX + g(18)
sh.wire((XA, DCP), (xc, DCP))
_, ct, cb = vert2(sh, "C", "C47", xc, DCP + g(3), sh_value("C47"), top=1)        # pin 1 = DC+
sh.wire(cb, (xc, CAPR))
sh.junction(xc, CAPR)
_, ct, cb = vert2(sh, "C", "C54", xc, CAPR + g(19), sh_value("C54"), top=1)      # pin 1 = DHB_CAP
sh.wire((xc, CAPR), ct)
sh.wire(cb, (xc, HC))
sh.junction(xc, HC)
# 5.2 (NR 2.1 / 2.4): TR3 = EC42/15 two-chamber, option B 20:21, two pins per winding end (4+5 primary
# start (dot) = DHB_CAP, 7+8 primary finish = DHB_HI_SOURCE, 9+10 secondary start (dot) = TRANS_SEC, 13+14
# secondary finish = DHB_HI_SOURCE_SEC; DAB_TRANSFORMER.md 5; pins re-assigned 2026-11-21 to the pairs nearest
# to the split capacitors / bridges, was 1+2 / 7+8 / 9+10 / 15+16). L3 is removed: its leakage replaces it, DHB_CAP
# goes straight to the primary (the 5.1 net TRANS_PRI disappears).
# 5.2 (NR 2.8): balancing resistors R143 + R144 across C47 (DC+ symbol above, ends on the DHB_CAP row) and
# R145 + R146 across C54 (column crosses the source row like C54), right of the C47 / C54 column.
xbal = xc + g(6)
_, rt, rb = vert2(sh, "R", "R143", xbal, CAPR - g(9), sh_value("R143"), top=1)    # pin 1 = DC+
power_at(sh, "DC+", rt, "up")
_, rt, rb2 = vert2(sh, "R", "R144", xbal, CAPR - g(3), sh_value("R144"), top=1)
sh.junction(xbal, CAPR)
_, rt, rb = vert2(sh, "R", "R145", xbal, CAPR + g(13), sh_value("R145"), top=1)   # pin 1 = DHB_CAP
sh.wire((xbal, CAPR), rt)
_, rt, rb = vert2(sh, "R", "R146", xbal, CAPR + g(19), sh_value("R146"), top=1)   # pin 2 = DHB_CURRENT
sh.wire(rb, (xbal, HC))
sh.junction(xbal, HC)
sh.label("DHB_CAP", xbal + g(2), CAPR, 0)
TRX, TRY = g(108), CAPR + g(4)
tr = sh.place("EC42_2CH", "TR3", TRX, TRY, value=sh_value("TR3"))
P1, P2, P7, P8 = (tr.pin(n) for n in ("4", "5", "7", "8"))          # primary start pair, finish pair
S1, S2, S15, S16 = (tr.pin(n) for n in ("9", "10", "13", "14"))    # secondary start pair, finish pair
xbus = P1[0] - g(2)
sh.wire((xc, CAPR), (xbus, CAPR))
sh.wire((xbus, CAPR), P1)
sh.wire(P2, (xbus, P2[1]), (xbus, CAPR))
sh.junction(xbus, CAPR)
sh.wire((XA, SR), P8)
sh.wire(P7, (xbus, P7[1]), (xbus, SR))
sh.junction(xbus, SR)
# C67 / C70 across DC+ - DHB_CURRENT, DHB_CURRENT label at the right end of the shunt row
for i, ref in enumerate(("C67", "C70")):
    x = xc + g(12 + 8 * i)
    _, ct, cb = vert2(sh, "C", ref, x, HC - g(3), sh_value(ref), top=1)         # pin 1 = DC+
    sh.junction(x, HC)
    if i == 0:
        power_at(sh, "DC+", ct, "up")
        sh.junction(*ct)
        sh.wire(ct, (x + g(8), ct[1]))
sh.wire((XA, HC), (xc + g(24), HC))
sh.glabel("DHB_CURRENT", xc + g(24), HC, 0)

# --- secondary half-bridge ------------------------------------------------------------------------
Q2X = g(196)                                       # 5.2: +12 (room for the C16 / C55 balancing resistors)
XB = Q2X + g(2)
V4R, IGR = DCP, HC
q21 = sh.place("Q_NMOS_GDS", "Q21", Q2X, Y1, value=sh_value("Q21"))
q8 = sh.place("Q_NMOS_GDS", "Q8", Q2X, Y1 + g(20), value=sh_value("Q8"))
sh.wire(q21.pin(2), (XB, V4R))
sh.junction(XB, V4R)
sh.wire(q21.pin(3), q8.pin(2))
sh.junction(XB, SR)
sh.wire(q8.pin(3), (XB, IGR))
power_at(sh, "ISO_GND", (XB, IGR), "down")
sh.junction(XB, IGR)
xn = gate_net(sh, q21.pin(1), "DHB_HI_GATE_SEC", "R57", "R58", "D31", pull=("R56", "src"))
sh.junction(xn, SR)
gate_net(sh, q8.pin(1), "DHB_LOW_GATE_SEC", "R87", "R88", "D32")
# TR3 secondary: TRANS_SEC node with C16 / C55 (column crosses the source row), S2 = DHB_HI_SOURCE_SEC
xc2 = g(142)
xbr = S1[0] + g(2)
sh.wire(S1, (xbr, CAPR))
sh.wire((xbr, CAPR), (xc2, CAPR))
sh.wire(S2, (xbr, S2[1]), (xbr, CAPR))
sh.junction(xbr, CAPR)
sh.label("TRANS_SEC", xbr + g(2), CAPR, 0)
sh.junction(xc2, CAPR)
sh.wire(S15, (xbr, S15[1]), (xbr, SR))
sh.junction(xbr, SR)
S2 = S16                                           # the secondary finish (13 + 14) = DHB_HI_SOURCE_SEC row
_, ct, cb = vert2(sh, "C", "C16", xc2, V4R + g(3), sh_value("C16"), top=1)       # pin 1 = 420V
sh.wire(cb, (xc2, CAPR))
sh.wire((xc2, V4R), (XB, V4R))
_, ct, cb = vert2(sh, "C", "C55", xc2, CAPR + g(19), sh_value("C55"), top=1)     # pin 1 = TRANS_SEC
sh.wire((xc2, CAPR), ct)
sh.wire(cb, (xc2, IGR), (XB, IGR))
# 5.2 (NR 2.8): balancing resistors across C16 (420V symbol above, ends on the TRANS_SEC row) and across C55
# (crosses the source row, ends on ISO_GND at C55), between TR3 and the C16 / C55 column.
# 2026-11-21: the user swapped C16 / C55 on the board (420V end now at the bridge); the resistor row under them
# stays where it is and takes the nets of the capacitor above each pair instead: R150 + R149 across C16
# (R150 pin 2 = 420V), R148 + R147 across C55 (R147 pin 1 = ISO_GND). Was R147 + R148 across C16, R149 + R150
# across C55; four equal 220k resistors, the mid nodes Net-(R147-Pad2) / Net-(R149-Pad2) are unchanged.
xbal2 = xc2 - g(8)
_, rt, rb = vert2(sh, "R", "R150", xbal2, CAPR - g(9), sh_value("R150"), top=2)   # pin 2 = 420V
power_at(sh, "420V", rt, "up")
vert2(sh, "R", "R149", xbal2, CAPR - g(3), sh_value("R149"), top=2)                # pin 1 = TRANS_SEC
sh.junction(xbal2, CAPR)
_, rt, rb = vert2(sh, "R", "R148", xbal2, CAPR + g(13), sh_value("R148"), top=2)  # pin 2 = TRANS_SEC
sh.wire((xbal2, CAPR), rt)
_, rt, rb = vert2(sh, "R", "R147", xbal2, CAPR + g(19), sh_value("R147"), top=2)  # pin 1 = ISO_GND
sh.wire(rb, (xbal2, IGR), (xc2, IGR))
sh.junction(xc2, IGR)
sh.wire(S2, (xn, SR))                              # through R56's bottom pin
sh.wire((xn, SR), (XB, SR))
xs_ = S2[0] + g(30)                                # label on a stub below the row (the row continues)
sh.wire((xs_, SR), (xs_, SR + g(4)), (xs_ + g(4), SR + g(4)))
sh.junction(xs_, SR)
sh.glabel("DHB_HI_SOURCE_SEC", xs_ + g(4), SR + g(4), 0)
# 420V rail: C89 / C90 and the permanent PWR_FLAG (the rail enters through the terminal +400V)
xk = XB + g(18)
sh.wire((XB, V4R), (xk + g(16), V4R))
mid = (xk + g(4), V4R + g(6))
for i, ref in enumerate(("C89", "C90")):
    x = xk + g(8 * i)
    _, ct, cb = vert2(sh, "C", ref, x, V4R + g(3), sh_value(ref), top=1)        # pin 1 = 420V
    sh.junction(x, V4R)
    sh.wire(cb, mid)
sh.junction(*mid)
power_at(sh, "ISO_GND", mid, "down")
flagged_power(sh, "420V", xk + g(16), V4R)
sh.text("V5.1 (PDF hand note). 1W core loss: ETD34 : 32, RM12 : 26 (PDF note).", g(30), g(86))
sh.text("5.2: TR3 = EC42/15 PC40 two-chamber 20:21 (leakage ~41 uH = series L, Lm ~200 uH, gap ~0.68 mm set by measuring Lm); L3 removed (NR 2.1 / 2.4).", g(30), g(80))
sh.text("Layout: C47 / C54 at the TR3 primary pins (NR 2.5), C16 / C55 at the secondary pins; firmware dead time 150 ns total (NR 2.7).", g(30), g(83))
sh.text("The PDF joins the terminals SEC_GND and ISO_GND by a bare wire (one net, ISO_GND); terminal GND is on ISO_GND.", g(30), g(89))

# --- 420V capacitor bank with the terminals +400V / GND, dividers -----------------------------------
X0, VR, GR = g(120), g(104), g(114)
terminal(sh, "P400V", X0, VR, "left")
terminal(sh, "GND", X0, GR, "left")
bank = ["C101", "C91", "C30", "C19", "C99", "C100"]
for i, ref in enumerate(bank):
    x = X0 + g(8 * (i + 1))
    sym = "C_Polarized" if ref in ("C30", "C19") else "C"
    _, ct, cb = vert2(sh, sym, ref, x, VR + g(3), sh_value(ref), top=1)         # pin 1 = 420V (+)
    sh.wire(cb, (x, GR))
    sh.junction(x, VR)
    sh.junction(x, GR)
x1 = X0 + g(8 * len(bank)) + g(8)
sh.wire((X0, GR), (x1, GR))
power_at(sh, "ISO_GND", (x1, GR), "down")
xd = x1 + g(8)
sh.wire((X0, VR), (xd, VR))
power_at(sh, "420V", (x1, VR), "up")
sh.junction(x1, VR)
# R23 / R34 / R39 -> CUK_CAP_MEAS2 with R38 and C27
prev = (xd, VR)
for i, r in enumerate(("R23", "R34", "R39")):
    _, rt, rb = vert2(sh, "R", r, xd, VR + g(5) + g(6 * i), sh_value(r), top=1)   # pin 1 = 420V side
    sh.wire(prev, rt)
    prev = rb
node = prev
_, rt, rb = vert2(sh, "R", "R38", xd, node[1] + g(3), sh_value("R38"), top=1)      # pin 1 = CUK_CAP_MEAS2
sh.junction(*node)
power_at(sh, "ISO_GND", rb, "down")
_, ct, cb = vert2(sh, "C", "C27", xd + g(8), node[1] + g(3), sh_value("C27"), top=2)   # pin 2 = CUK_CAP_MEAS2
sh.wire(node, ct, (xd + g(12), node[1]))
sh.junction(*ct)
sh.glabel("CUK_CAP_MEAS2", xd + g(12), node[1], 0)
power_at(sh, "ISO_GND", cb, "down")
# R120 / R119 / R118 -> CUK_CAP_MEAS- (ISO_GND at the bottom)
xe = xd + g(32)
sh.glabel("CUK_CAP_MEAS-", xe, VR, 90)
prev = (xe, VR)
for i, r in enumerate(("R120", "R119", "R118")):
    _, rt, rb = vert2(sh, "R", r, xe, VR + g(5) + g(6 * i), sh_value(r), top=2)   # pin 2 = CUK_CAP_MEAS- side
    sh.wire(prev, rt)
    prev = rb
power_at(sh, "ISO_GND", prev, "down")
sh.text("Terminal GND = net ISO_GND (PDF iso_GND); C91 has no visible refdes in the PDF (hidden), drawn next to C101.", X0 - g(4), GR + g(32))
sh.text("420V PWR_FLAG: permanent (the rail comes in through the terminal +400V).", X0 - g(4), GR + g(35))
sh.save()
print("sheet07: written")
