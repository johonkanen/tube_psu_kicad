#!/usr/bin/env python3
"""Sheet 4 - MCU socket and misc (PDF page 4): the 2x25 MCU header J2, the +3V3 regulator V4
(TPS73033 from 5V), the +1V65_BIAS reference REF1 with R110 / R3 / C48, the 15V measurement
divider R11 / R12 (AUX_MEAS), the DC-link measurement amplifier U6 (TLV316, DC+ through
3 x 1M) -> DC_LINK_MEAS, and the UART connector J4 (RX / TX).

PDF: the J2 pins are labelled with the MCU pin names (A12, B12, C15, ...); the signal names are
tied to them by separate wires (e.g. EPWM6A - A12). KiCad uses the IPC net names; the MCU pin
names are kept as small texts on the pin wires. PDF DGND = net GND."""
from _common import *  # noqa: F401,F403

sh = sheet("04_mcu_connector.kicad_sch")

# --- J2: (pin, IPC net, PDF MCU pin name); power nets and global/local labels ------------------
J2_PINS = [
    (1, "GND", "DGND"), (2, "5V", "5V"), (3, "EPWM6A", "A12"), (4, "PRI_DHB_HI", "A11"),
    (5, "EPWM5A", "A13"), (6, "B12", "B12"), (7, "$HT_CS", "A14"), (8, "$CUK_CS", "B13"),
    (9, "SYNCH_2", "A15"), (10, "EPWM2A", "B14"), (11, "HT_SDATA", "C15"), (12, "EPWM2B", "B16"),
    (13, "SYNCH_1", "D16"), (14, "CUK_CLK", "C16"), (15, "HT_CLK", "F15"), (16, "CUK_SDATA", "D15"),
    (17, "GPIO_BYPASS_RLY", "G16"), (18, "F16", "F16"), (19, "PFC_PWM1", "J15"), (20, "G15", "G15"),
    (21, "K16", "K16"), (22, "EPWM1A", "J16"), (23, "L16", "L16"), (24, "RX", "K15"),
    (25, "N14", "N14"), (26, "TX", "L15"), (27, "N15", "N15"), (28, "N16", "N16"),
    (29, "P15", "P15"), (30, "P16", "P16"), (31, "T15", "T15"), (32, "R16", "R16"),
    (33, "PFC_PWM2", "T13"), (34, "T14", "T14"), (35, "GND", "DGND"), (36, "GND", "DGND"),
    (37, "DHB_I_MEAS", "ADB6"), (38, "CUK_CAP_MEAS_RAW", "ADA6"), (39, "HEATER_CAP_AD_MEAS", "ADB5"),
    (40, "AUX_MEAS", "ADA5"), (41, "DC_LINK_MEAS", "ADB4"), (42, "ADA4", "ADA4"),
    (43, "PFC_I1_MEAS", "ADB3"), (44, "PFC_I2_MEAS", "ADA3"), (45, "HEATER_I_MEAS", "ADB2"),
    (46, "ADA2", "ADA2"), (47, "VAC_MEAS", "ADB1"), (48, "ADA1", "ADA1"), (49, "ADB0", "ADB0"),
    (50, "ADA0", "ADA0"),
]
GLOBAL = {"EPWM6A", "PRI_DHB_HI", "EPWM5A", "B12", "$HT_CS", "$CUK_CS", "SYNCH_2", "EPWM2A", "HT_SDATA",
          "EPWM2B", "SYNCH_1", "CUK_CLK", "HT_CLK", "CUK_SDATA", "GPIO_BYPASS_RLY", "PFC_PWM1", "PFC_PWM2",
          "DHB_I_MEAS", "PFC_I1_MEAS", "PFC_I2_MEAS", "HEATER_I_MEAS", "VAC_MEAS"}
POWER = {"GND", "5V"}
J2X, J2Y = g(270), g(100)
j2 = sh.place("HEADER_2X25_50MIL", "J2", J2X, J2Y, value=sh_value("J2"))
for pin, net, mcu in J2_PINS:
    p = j2.pin(pin)
    side = "left" if pin % 2 else "right"
    n = 6 if (net in POWER or net in GLOBAL) else 20     # local labels clear of the global label boxes
    q = left(p, n) if side == "left" else right(p, n)
    sh.wire(p, q)
    if net in POWER:
        power_at(sh, net, q, side)
    elif net in GLOBAL:
        sh.glabel(net, *q, 180 if side == "left" else 0)
    else:
        sh.label(net, *q, 180 if side == "left" else 0)
    if mcu != net:
        tx = J2X - g(11) if side == "left" else J2X + g(8) + 0.3
        sh.text(mcu, tx, p[1] - 0.4, size=1.0)
sh.text("J2: MCU pin names of the PDF as small texts; nets = IPC names (PDF DGND = GND).", J2X - g(44), J2Y + g(32))
sh.text("Single-pin nets (ADA0.., F16, G15, ...): label on the J2 pin only (PDF: no other connection).", J2X - g(44), J2Y + g(35))
sh.text("AD converter range [0 - 3v3] (PDF note).", J2X - g(44), J2Y + g(38))

# --- REF1: +1V65_BIAS reference ------------------------------------------------------------------
RX_, RY = g(60), g(40)
ref = sh.place("ADR380", "REF1", RX_, RY, value=sh_value("REF1"))
VIN, VOUT, RGND = ref.pin(2), ref.pin(3), ref.pin(1)
GROW = RGND[1] + g(4)                       # ground rail under the block
xin = RX_ - g(14)
sh.wire(VIN, (xin, VIN[1]))
power_at(sh, "+3V3", (xin, VIN[1]), "up")
_, ct, cb = vert2(sh, "C", "C68", xin, VIN[1] + g(3), "1u", top=1)    # pin 1 = +3V3
sh.junction(xin, VIN[1])
sh.wire(cb, (xin, GROW))
xo = RX_ + g(14)
sh.wire(VOUT, (xo, VOUT[1]))
_, ct, cb = vert2(sh, "C", "C69", xo, VOUT[1] + g(3), "100n", top=1)          # pin 1 = REF1 VOUT
sh.junction(xo, VOUT[1])
sh.wire(cb, (xo, GROW))
_, rl, rr = horiz2(sh, "R", "R110", RX_ + g(22), VOUT[1], "220", left=2, text="above")     # pin 2 = REF1 VOUT
sh.wire((xo, VOUT[1]), rl)
xb = RX_ + g(30)                            # +1V65_BIAS node
sh.wire(rr, (xb, VOUT[1]))
sh.junction(xb, VOUT[1])
sh.wire((xb, VOUT[1]), (xb, VOUT[1] - g(8)))
flagged_power(sh, "+1V65_BIAS", xb, VOUT[1] - g(8))   # permanent: the rail is made by R110 (passive)
_, rt, rb = vert2(sh, "R", "R3", xb, VOUT[1] + g(3), "470", top=1)          # pin 1 = +1V65_BIAS
sh.wire(rb, (xb, GROW))
xc = xb + g(8)
sh.wire((xb, VOUT[1]), (xc, VOUT[1]))
_, ct, cb = vert2(sh, "C", "C48", xc, VOUT[1] + g(3), "100n", top=1)         # pin 1 = +1V65_BIAS
sh.wire(ct, (xc, VOUT[1]))
sh.wire(cb, (xc, GROW))
sh.wire(RGND, (RX_, GROW))
sh.wire((xin, GROW), (xc, GROW))
for x in (xin, xo, RX_, xb):
    sh.junction(x, GROW)
power_at(sh, "GND", (xin, GROW), "down")
sh.text("PDF notes: 'MORE CAPACITANCE TO BIAS VOLTAGE / BUFFER REF OUTPUT or add load 220R load resistor'.", xin, GROW + g(7))
sh.text("+1V65_BIAS PWR_FLAG lives here (R110 from REF1); +3V3 is driven by V4 VOUT below.", xin, GROW + g(10))

# --- V4: +3V3 regulator -------------------------------------------------------------------------
VX, VY = g(60), g(90)
v4 = sh.place("TPS73033", "V4", VX, VY, value=sh_value("V4"))
VIN, VGND, EN, NR, VOUT = (v4.pin(n) for n in (1, 2, 3, 4, 5))
xin = VX - g(20)
sh.wire(VIN, (xin, VIN[1]), (xin, EN[1]), EN)       # VIN and EN both on 5V
sh.junction(xin, VIN[1])
top5 = (xin, VIN[1] - g(4))
sh.wire((xin, VIN[1]), top5)
power_at(sh, "5V", top5, "up")
_, ct, cb = vert2(sh, "C", "C75", xin - g(8), VIN[1] + g(1), "1u", top=1)   # pin 1 = 5V
sh.wire(ct, (xin - g(8), top5[1]), top5)
sh.junction(*top5)
power_at(sh, "GND", cb, "down")
q = left(VGND, 2)                                   # GND between the VIN and EN wires, no crossing
sh.wire(VGND, q)
power_at(sh, "GND", q, "left")
# NR cap, output
xo = VX + g(14)
sh.wire(NR, (xo, NR[1]))
_, ct, cb = vert2(sh, "C", "C74", xo, NR[1] + g(3), "100n", top=1)           # pin 1 = NR
power_at(sh, "GND", cb, "down")
xv = VX + g(22)
sh.wire(VOUT, (xv, VOUT[1]))
sh.junction(xv, VOUT[1])
sh.wire((xv, VOUT[1]), (xv, VOUT[1] - g(4)))
power_at(sh, "+3V3", (xv, VOUT[1] - g(4)), "up")
_, ct, cb = vert2(sh, "C", "C76", xv, VOUT[1] + g(3), "1u", top=1)           # pin 1 = +3V3
power_at(sh, "GND", cb, "down")
sh.text("+3v3 (PDF) = +3V3.", VX - g(20), VY + g(16))

# --- 15V measurement: R11 / R12 divider -> AUX_MEAS (one-sheet net, J2 pin 40) ------------------
MX, MY = g(24), g(140)
_, rt, rb = vert2(sh, "R", "R11", MX, MY, "22k", top=1)                     # pin 1 = 15V
sh.wire(rt, up(rt, 2))
power_at(sh, "15V", up(rt, 2), "up")
node = (MX, rb[1] + g(2))
sh.wire(rb, node)
_, rt2, rb2 = vert2(sh, "R", "R12", MX, node[1] + g(5), "4.7k", top=1)     # pin 1 = AUX_MEAS
sh.wire(node, rt2)
sh.junction(*node)
xc = MX + g(8)
_, ct, cb = vert2(sh, "C", "C61", xc, node[1] + g(5), "1n", top=2)          # pin 2 = AUX_MEAS
sh.wire(node, (xc, node[1]), ct)
sh.wire((xc, node[1]), (xc + g(4), node[1]))
sh.junction(xc, node[1])
sh.label("AUX_MEAS", xc + g(4), node[1], 0)
grow = rb2[1] + g(2)
sh.wire(rb2, (MX, grow), (xc, grow), cb)
sh.junction(MX, grow)
power_at(sh, "GND", (MX, grow), "down")
sh.text("15V measurement (PDF: 18.7/3V3)", MX - g(8), MY - g(11))

# --- DC-link measurement: U6 TLV316 ---------------------------------------------------------------
AX, AY = g(120), g(160)
u6 = sh.place("TLV316IDBVR", "U6", AX, AY, value="TLV316IDBVR")
INP, INN, OUT, VP, VN = u6.pin(3), u6.pin(4), u6.pin(1), u6.pin(5), u6.pin(2)
# + input: DC+ -> R16 -> R15 -> R10 -> (+), R17 to GND; pin 1 on the DC+ side, R17 pin 1 at the node
x2 = AX - g(20)
prev = None
for i, r in enumerate(("R16", "R15", "R10")):
    _, rt, rb = vert2(sh, "R", r, x2, INP[1] - g(21) + g(8 * i), "1M", top=1)
    if prev is None:
        sh.wire(rt, up(rt, 2))
        power_at(sh, "DC+", up(rt, 2), "up")
    else:
        sh.wire(prev, rt)
    prev = rb
sh.wire(prev, (x2, INP[1]), INP)
sh.junction(x2, INP[1])
_, rl, rr = horiz2(sh, "R", "R17", x2 - g(6), INP[1], "15k", left=2)
sh.wire(rr, (x2, INP[1]))
sh.wire(rl, left(rl, 2))
power_at(sh, "GND", left(rl, 2), "left")
# - input: GND -> R112 -> R111 -> R109 -> (-) below the op-amp (pin 2 at the - side), feedback R82
x1 = AX - g(14)
sh.wire(INN, (x1, INN[1]))
prev = (x1, INN[1])
for i, r in enumerate(("R109", "R111", "R112")):
    _, rt, rb = vert2(sh, "R", r, x1, INN[1] + g(5) + g(8 * i), "1M", top=2, text="left")
    sh.wire(prev, rt)
    prev = rb
sh.wire(prev, down(prev, 2))
power_at(sh, "GND", down(prev, 2), "down")
fx = AX - g(10)
sh.junction(fx, INN[1])
frow = AY + g(12)
_, rl, rr = horiz2(sh, "R", "R82", AX, frow, "15k", left=1, text="below")   # pin 1 = - node
sh.wire((fx, INN[1]), (fx, frow), rl)
node = (AX + g(10), OUT[1])
sh.wire(rr, (node[0], frow), node)
# output -> R2 -> DC_LINK_MEAS (J2 pin 41) with C4
sh.wire(OUT, node)
sh.junction(*node)
_, rl, rr = horiz2(sh, "R", "R2", AX + g(16), OUT[1], "1k", left=2)         # pin 2 = op-amp side
sh.wire(node, rl)
q = (AX + g(24), OUT[1])
sh.wire(rr, q, (AX + g(28), OUT[1]))
sh.label("DC_LINK_MEAS", AX + g(28), OUT[1], 0)
_, ct, cb = vert2(sh, "C", "C4", q[0], q[1] + g(3), "1n", top=2)             # pin 2 = DC_LINK_MEAS
sh.junction(*q)
power_at(sh, "GND", cb, "down")
# supply: +3V3 with C62, GND
top = (VP[0], AY - g(10))
sh.wire(VP, top)
power_at(sh, "+3V3", top, "up")
_, cl, cr = horiz2(sh, "C", "C62", AX + g(4), AY - g(10), "2.2u", left=1,    # pin 1 = +3V3
                   ref_at=(AX + g(4), AY - g(13), 270, None), value_at=(AX + g(4), AY - g(7), 270, None))
sh.wire(top, cl)
sh.junction(*top)
sh.wire(cr, right(cr, 3))
power_at(sh, "GND", right(cr, 3), "right")
power_at(sh, "GND", VN, "down")
sh.text("DC-link measurement (PDF: 663/3V3)", AX - g(30), AY + g(36))

# --- J4: UART (RX / TX one-sheet nets to J2 pins 24 / 26; PDF DGND = GND) ---------------------
JX, JY = g(210), g(170)
j4 = sh.place("CONN_01X03", "J4", JX, JY, value=sh_value("J4"))
label_left(sh, "RX", j4.pin(1), 4)
label_left(sh, "TX", j4.pin(2), 4)
q = left(j4.pin(3), 4)
sh.wire(j4.pin(3), q)
power_at(sh, "GND", q, "left")

sh.save()
print("sheet04: written")
