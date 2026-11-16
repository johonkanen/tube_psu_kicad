#!/usr/bin/env python3
"""Sheet 6 - Heaters (PDF page 6): the heater half-bridge Q11 / Q10 (DC+ to the shunt R30 ->
HEATER_CURRENT) driving the primary of TR2 through the resonance caps C49/C42 (DC+ side) and
C41/C22 (shunt side) with the HEATER_CAP_MEAS node at TR2 pins 4/5; the synchronous rectifiers
Q1 / Q2 on the secondary (Q14_DRAIN / Q13_DRAIN, sources on HT_GND); the 6V3 heater rail with its
capacitor bank, the divider R54 / R55 -> HEATER_VOLTAGE_MEAS and the terminals HT_6V3 / HT_GND;
the isolated high-side driver DRV3 (Si8271, EPWM5A -> HEATER_HI_GATE, bootstrap D11 / R99 / C25
from 15V), the low-side driver DRV9 (IXDD609, EPWM6A -> HEATER_LOW_GATE through R37 and R31 + D33)
and the rectifier gate driver DRV4 (IXDD604 on 6V3, EPWM6A_ISO / EPWM5A_ISO -> HEATER_SYNC_GATE_1/2).

PDF: DC- = GND, HT_AUX = 6V3, heater_current / heater_cap_meas / q13_drain / EPWMxA_iso = the IPC
names. The PDF transformer symbol has centre-tap pins on both windings that have no footprint pad
(primary "ct1" dangling, secondary wired to 6V3): the IPC has no TR2 pad on 6V3, so the 6V3 rail is
drawn without TR2 (on the board the winding wires go to the free wire pads 6V3 x2, Q13_DRAIN,
Q14_DRAIN)."""
from _common import *  # noqa: F401,F403

sh = sheet("06_heaters.kicad_sch")

# --- heater half-bridge, resonance caps, TR2 primary ------------------------------------------
QX, Y1 = g(50), g(40)                 # Q11 centre; column A = QX + g(2) (D / S pins)
XA = QX + g(2)
DCP, SROW, CMR, HC = Y1 - g(8), Y1 + g(8), g(60), g(66)
q11 = sh.place("Q_NMOS_GDS", "Q11", QX, Y1, value=sh_value("Q11"),
               ref_at=(QX + g(6), Y1 - g(2), 0, "left"), value_at=(QX + g(4), Y1 - g(6), 0, "left"))
q10 = sh.place("Q_NMOS_GDS", "Q10", QX, Y1 + g(16), value=sh_value("Q10"),
               ref_at=(QX + g(6), Y1 + g(14), 0, "left"), value_at=(QX + g(4), Y1 + g(10), 0, "left"))
G11, D11_, S11 = q11.pin(1), q11.pin(2), q11.pin(3)
G10, D10, S10 = q10.pin(1), q10.pin(2), q10.pin(3)
sh.wire(D11_, (XA, DCP))
power_at(sh, "DC+", (XA, DCP), "up")
sh.junction(XA, DCP)
sh.wire(S11, D10)                                     # HEATER_HI_SOURCE node on column A
sh.junction(XA, SROW)
sh.wire(S10, (XA, HC))                                # HEATER_CURRENT node
sh.junction(XA, HC)
_, rt, rb = vert2(sh, "R", "R30", XA, HC + g(3), sh_value("R30"), top=1)          # pin 1 = HEATER_CURRENT
power_at(sh, "GND", rb, "down")
sh.wire((XA, HC), (QX - g(4), HC))
sh.glabel("HEATER_CURRENT", QX - g(4), HC, 180)
# gates: HEATER_HI_GATE with R36 gate-source, HEATER_LOW_GATE
xg = QX - g(10)
sh.wire(G11, (xg, G11[1]), (xg - g(4), G11[1]))
sh.label("HEATER_HI_GATE", xg - g(4), G11[1], 180)
sh.junction(xg, G11[1])
_, rt, rb = vert2(sh, "R", "R36", xg, G11[1] + g(3), sh_value("R36"), top=1, text="left")   # pin 1 = HEATER_HI_GATE
sh.wire(rb, (xg, SROW), (XA, SROW))
sh.wire(G10, (xg, G10[1]))
sh.label("HEATER_LOW_GATE", xg, G10[1], 180)
# TR2 primary: pins 1/2 = HEATER_HI_SOURCE, 4/5 = HEATER_CAP_MEAS
TX, TY = g(108), SROW + g(2)
tr = sh.place("EF25_8PIN", "TR2", TX, TY, value=sh_value("TR2"))
P1, P2, P4, P5 = (tr.pin(n) for n in ("1", "2", "4", "5"))
P10, P9, P7, P6 = (tr.pin(n) for n in ("10", "9", "7", "6"))
x12, x45 = TX - g(8), TX - g(10)
sh.wire(P1, (x12, P1[1]), (x12, P2[1]), P2)
sh.wire((XA, SROW), (x12, SROW))
sh.junction(x12, SROW)
sh.label("HEATER_HI_SOURCE", XA + g(4), SROW, 0)
sh.wire(P4, (x45, P4[1]), (x45, CMR))
sh.wire(P5, (x45, P5[1]))
sh.junction(x45, P5[1])
# resonance caps: upper pair DC+ - HEATER_CAP_MEAS on one column (crosses the source row, as in the
# PDF), lower pair HEATER_CAP_MEAS - HEATER_CURRENT
xl, xr, xj = QX + g(24), QX + g(28), QX + g(26)
sh.wire((XA, DCP), (xj, DCP), (xj, DCP + g(4)))
sh.junction(xj, DCP)
for x, ref in ((xl, "C49"), (xr, "C42")):
    _, ct, cb = vert2(sh, "C", ref, x, DCP + g(9), sh_value(ref), top=1, text="left" if x == xl else "right")  # pin 1 = DC+
    sh.wire((xj, DCP + g(4)), (x, DCP + g(4)), ct)
    sh.wire(cb, (x, DCP + g(16)), (xj, DCP + g(16)))
sh.wire((xj, DCP + g(16)), (xj, CMR))
sh.wire((xl, CMR), (x45, CMR))
sh.junction(xj, CMR)
sh.label("HEATER_CAP_MEAS", xj + g(4), CMR, 0)
for x, ref in ((xl, "C41"), (xr, "C22")):
    _, ct, cb = vert2(sh, "C", ref, x, CMR + g(3), sh_value(ref), top=1, text="left" if x == xl else "right")  # pin 1 = HEATER_CAP_MEAS
    if x == xr:
        sh.junction(*ct)
    sh.junction(x, HC)
xc20 = TX + g(28)
sh.wire((xj, DCP), (xc20, DCP))
_, ct, cb = vert2(sh, "C", "C20", xc20, DCP + g(3), sh_value("C20"), top=1)      # pin 1 = DC+
sh.wire(cb, (xc20, HC), (XA, HC))
sh.text("20n resonance cap, note X7R cap voltage bias (PDF note).", QX - g(14), HC + g(12))
sh.text("E25 : 64/2/2, check primary turns! (PDF note). V5.1 (PDF hand note).", QX - g(14), HC + g(15))
sh.text("TR2 centre taps (PDF: primary 'ct1' dangling, secondary wired to 6V3) have no footprint pad: not drawn.", QX - g(14), HC + g(18))

# --- TR2 secondary: Q14_DRAIN (pins 9/10), Q13_DRAIN (pins 6/7) -> local labels ---------------
x9, x6 = TX + g(8), TX + g(10)
sh.wire(P10, (x9, P10[1]), (x9, P9[1]), P9)
sh.wire((x9, P10[1]), (x9 + g(4), P10[1]))
sh.junction(x9, P10[1])
sh.label("Q14_DRAIN", x9 + g(4), P10[1], 0)
sh.wire(P7, (x6, P7[1]), (x6, P6[1]), P6)
sh.wire((x6, P6[1]), (x6 + g(4), P6[1]))
sh.junction(x6, P6[1])
sh.label("Q13_DRAIN", x6 + g(4), P6[1], 0)

# --- synchronous rectifiers Q1 / Q2 (BUK9Y15-60E, Proteus ids 1=S 2=G 3=D) --------------------
for ref, qy, drain, gate, rpd in (("Q1", g(50), "Q14_DRAIN", "HEATER_SYNC_GATE_1", "R108"),
                                  ("Q2", g(70), "Q13_DRAIN", "HEATER_SYNC_GATE_2", "R107")):
    qx = g(170)
    q = sh.place("Q_NMOS_SGD", ref, qx, qy, value=sh_value(ref))
    S, G, D = q.pin(1), q.pin(2), q.pin(3)
    sh.wire(D, up(D, 2))
    sh.label(drain, *up(D, 2), 0)
    power_at(sh, "HT_GND", S, "down")
    xg = qx - g(8)
    sh.wire(G, (xg, G[1]), (xg - g(4), G[1]))
    sh.label(gate, xg - g(4), G[1], 180)
    sh.junction(xg, G[1])
    _, rt, rb = vert2(sh, "R", rpd, xg, G[1] + g(3), sh_value(rpd), top=1, text="left")   # pin 1 = gate
    power_at(sh, "HT_GND", rb, "down")

# --- 6V3 rail: terminals, capacitor bank, divider R54 / R55 -----------------------------------
X0, R6, GR = g(204), g(34), g(44)
terminal(sh, "HT_6V3", X0, R6, "left")
terminal(sh, "HT_GND", X0, GR, "left")
bank = ["C24", "C23", "C31", "C32", "C33", "C8", "C9"]
for i, ref in enumerate(bank):
    x = X0 + g(8 * (i + 1))
    sym = "C_Polarized" if ref in ("C31", "C32") else "C"
    _, ct, cb = vert2(sh, sym, ref, x, R6 + g(3), sh_value(ref), top=1)             # pin 1 = 6V3 (+)
    sh.wire(cb, (x, GR))
    sh.junction(x, R6)
    sh.junction(x, GR)
x1 = X0 + g(8 * len(bank)) + g(8)
sh.wire((X0, GR), (x1, GR))
flagged_power(sh, "HT_GND", x1, GR)                 # HT_GND enters here (terminal): permanent flag
xd = x1 + g(8)
xt = xd + g(12)
sh.wire((X0, R6), (xt, R6))
flagged_power(sh, "6V3", xt, R6)                    # 6V3 enters here (terminal): permanent flag
sh.junction(xd, R6)
_, rt, rb = vert2(sh, "R", "R54", xd, R6 + g(5), sh_value("R54"), top=1)           # pin 1 = 6V3
sh.wire((xd, R6), rt)
node = rb
_, rt2, rb2 = vert2(sh, "R", "R55", xd, node[1] + g(3), sh_value("R55"), top=1)   # pin 1 = HEATER_VOLTAGE_MEAS
sh.junction(*node)
power_at(sh, "HT_GND", rb2, "down")
glabel_right(sh, "HEATER_VOLTAGE_MEAS", node, 4)
sh.text("6V3 and HT_GND enter the board through the terminals HT_6V3 / HT_GND: PWR_FLAGs here (moved from sheet 3).", X0 - g(4), GR + g(16))

# --- DRV3: Si8271 isolated high-side driver ---------------------------------------------------
DX, DY = g(74), g(110)
d3 = sh.place("SI8271", "DRV3", DX, DY, value=sh_value("DRV3"))
VDD1, VIN, EN, GND1 = d3.pin(2), d3.pin(1), d3.pin(4), d3.pin(3)
VDD2, OUTP, OUTM, GND2 = d3.pin(8), d3.pin(7), d3.pin(6), d3.pin(5)
xs = DX - g(12)
sh.wire(VDD1, (xs, VDD1[1]), (xs, VDD1[1] - g(4)))
power_at(sh, "5V", (xs, VDD1[1] - g(4)), "up")
sh.wire(EN, left(EN, 2))
power_at(sh, "5V", left(EN, 2), "left")
sh.wire(GND1, (xs, GND1[1]))
power_at(sh, "GND", (xs, GND1[1]), "down")
sh.wire(VIN, (DX - g(32), VIN[1]))
sh.glabel("EPWM5A", DX - g(32), VIN[1], 180)
_, rt, rb = vert2(sh, "R", "R78", DX - g(28), VIN[1] + g(3), sh_value("R78"), top=2)   # pin 2 = EPWM5A
sh.junction(*rt)
power_at(sh, "GND", rb, "down")
for x, ref, net in ((DX - g(44), "C53", "5V"), (DX - g(54), "C18", "15V")):           # decoupling, standalone pairs
    _, ct, cb = vert2(sh, "C", ref, x, DY - g(1), sh_value(ref), top=1, text="left")   # pin 1 = rail
    sh.wire(ct, up(ct, 2))
    power_at(sh, net, up(ct, 2), "up")
    power_at(sh, "GND", cb, "down")
# bootstrap: 15V -> D11 -> R99 -> VDD2, C25 VDD2 - GND2 (= HEATER_HI_SOURCE)
BR = DY - g(14)
sh.wire((DX - g(8), BR), (DX - g(5), BR))
power_at(sh, "15V", (DX - g(8), BR), "up")
_, da, dc = horiz2(sh, "D", "D11", DX - g(2), BR, sh_value("D11"), left="A")
_, r2, r1 = horiz2(sh, "R", "R99", DX + g(8), BR, sh_value("R99"), left=2)             # pin 1 = VDD2 side
sh.wire(dc, r2)
xb, xc = DX + g(14), DX + g(48)
sh.wire(r1, (xb, BR), (xb, VDD2[1]), VDD2)
sh.wire((xb, BR), (xc, BR))
sh.junction(xb, BR)
sh.pwr_flag(DX + g(30), BR, 0)                      # permanent: VDD2 fed through D11 / R99 only
sh.junction(DX + g(30), BR)
_, ct, cb = vert2(sh, "C", "C25", xc, DY - g(2), sh_value("C25"), top=1)              # pin 1 = VDD2
sh.wire((xc, BR), ct)
BOT = DY + g(8)
sh.wire(cb, (xc, BOT), (xb, BOT), (xb, GND2[1]), GND2)
sh.wire((xc, BOT), (xc + g(4), BOT))
sh.junction(xc, BOT)
sh.label("HEATER_HI_SOURCE", xc + g(4), BOT, 0)
sh.pwr_flag(DX + g(30), BOT, 180)                   # permanent: the high-side return is a MOSFET node
sh.junction(DX + g(30), BOT)
# outputs: OUT+ -> R24, OUT- -> R59, joined into HEATER_HI_GATE
_, pl, pr = horiz2(sh, "R", "R24", DX + g(20), OUTP[1], sh_value("R24"), left=1, text="above")   # pin 1 = OUT+
_, ml, mr = horiz2(sh, "R", "R59", DX + g(20), OUTM[1], sh_value("R59"), left=1, text="below")   # pin 1 = OUT-
sh.wire(OUTP, pl)
sh.wire(OUTM, ml)
xo = DX + g(26)
sh.wire(pr, (xo, OUTP[1]), (xo, OUTM[1]))
sh.wire(mr, (DX + g(30), OUTM[1]))
sh.junction(xo, OUTM[1])
sh.label("HEATER_HI_GATE", DX + g(30), OUTM[1], 0)
sh.text("Si8271: PWR_FLAGs on VDD2 (bootstrap through D11 / R99) and on the high-side return HEATER_HI_SOURCE.", DX - g(40), BOT + g(8))

# --- DRV9: IXDD609 low-side driver (EPWM6A -> HEATER_LOW_GATE via R37 and R31 + D33) ----------
ixdd609_cell(sh, "DRV9", g(74), g(154), vcc="15V", gnd="GND", in_label="EPWM6A", r_in=("R77", "10k"),
             cdec=("C52", "4.7u", 1), r_out=[("R37", "10R"), ("R31", "3.3R")], out_label="HEATER_LOW_GATE",
             r_gate=("R66", "10k"), diode=("D33", "ZLLS400TA"), local=True, r_gate_top=1)

# --- DRV4: IXDD604 dual driver on 6V3 for the synchronous rectifiers ---------------------------
DX, DY = g(236), g(120)
d4 = sh.place("IXDD604", "DRV4", DX, DY, value=sh_value("DRV4"))
VCC, ENA, INA, INB, ENB = (d4.pin(n) for n in (6, 1, 2, 3, 4))
OUTA, OUTB, GNDP, TAB = (d4.pin(n) for n in (8, 5, 7, 9))
xs = DX - g(12)
sh.wire(VCC, (xs, VCC[1]), (xs, VCC[1] - g(8)))
power_at(sh, "6V3", (xs, VCC[1] - g(8)), "up")
_, ct, cb = vert2(sh, "C", "C17", DX - g(24), VCC[1] - g(5), sh_value("C17"), top=1, text="left")   # pin 1 = 6V3
sh.wire(ct, (xs, VCC[1] - g(8)))
sh.junction(xs, VCC[1] - g(8))
power_at(sh, "HT_GND", cb, "down")
for p in (ENA, ENB):
    sh.wire(p, left(p, 2))
    power_at(sh, "6V3", left(p, 2), "left")
sh.wire(INA, (DX - g(28), INA[1]))
sh.glabel("EPWM6A_ISO", DX - g(28), INA[1], 180)
_, rt, rb = vert2(sh, "R", "R117", DX - g(24), INA[1] + g(3), sh_value("R117"), top=1, text="left")   # pin 1 = EPWM6A_ISO
sh.junction(*rt)
power_at(sh, "HT_GND", rb, "down")
row = INB[1] + g(10)
sh.wire(INB, (DX - g(20), INB[1]), (DX - g(20), row), (DX - g(28), row))
sh.glabel("EPWM5A_ISO", DX - g(28), row, 180)
_, rt, rb = vert2(sh, "R", "R91", DX - g(24), row + g(3), sh_value("R91"), top=1, text="left")       # pin 1 = EPWM5A_ISO
sh.junction(*rt)
power_at(sh, "HT_GND", rb, "down")
_, al, ar = horiz2(sh, "R", "R63", DX + g(14), OUTA[1], sh_value("R63"), left=2, text="above")   # pin 2 = OUTA
_, bl, br = horiz2(sh, "R", "R28", DX + g(24), OUTB[1], sh_value("R28"), left=2, text="below")   # pin 2 = OUTB
sh.wire(OUTA, al)
sh.wire(ar, (DX + g(32), OUTA[1]))
sh.label("HEATER_SYNC_GATE_1", DX + g(32), OUTA[1], 0)
sh.wire(OUTB, bl)
sh.wire(br, (DX + g(32), OUTB[1]))
sh.label("HEATER_SYNC_GATE_2", DX + g(32), OUTB[1], 0)
xgb = DX + g(10)
sh.wire(GNDP, (xgb, GNDP[1]), (xgb, TAB[1] + g(4)))
sh.wire(TAB, (xgb, TAB[1]))
sh.junction(xgb, TAB[1])
power_at(sh, "HT_GND", (xgb, TAB[1] + g(4)), "down")

sh.text("PDF aliases: DC- = GND, HT_AUX = 6V3, heater_current / heater_cap_meas / q13_drain / EPWM5A_iso / EPWM6A_iso = IPC names.", g(36), g(190))
sh.save()
print("sheet06: written")
