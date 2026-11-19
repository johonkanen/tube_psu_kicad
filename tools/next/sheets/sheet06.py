#!/usr/bin/env python3
"""Sheet 6 - Heaters (PDF page 6): the heater half-bridge Q11 / Q10 (DC+ to the shunt R30 ->
HEATER_CURRENT) driving the primary of TR2 through the resonance caps C49/C42 (DC+ side) and
C41/C22 (shunt side) with the HEATER_CAP_MEAS node at TR2 pins 4/5; the synchronous rectifiers
Q1 / Q2 on the secondary (Q14_DRAIN / Q13_DRAIN, sources on HT_GND); the 6V3 heater rail with its
capacitor bank, the divider R54 / R55 -> HEATER_VOLTAGE_MEAS and the terminals HT_6V3 / HT_GND;
5.2: the half-bridge driver DRV3 (UCC21520, EPWM5A / EPWM6A -> HEATER_HI_GATE / HEATER_LOW_GATE, bootstrap
D11 / R99 / C25 from 15V; replaces the 5.1 Si8271 DRV3 + IXDD609 DRV9) and the rectifier gate driver DRV4
(UCC27524A on 6V3, EPWM6A_ISO / EPWM5A_ISO -> HEATER_SYNC_GATE_1/2; was IXDD604). Q10 / Q11 = IPD60R280P7S (DPAK).

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
# 5.2: balancing resistors across the resonance split caps (user 2026-11-19, as R143-R150 on the DAB):
# R155 + R156 across C49 || C42 (DC+ - HEATER_CAP_MEAS), R157 + R158 across C41 || C22 (HEATER_CAP_MEAS -
# HEATER_CURRENT), 2 x 220k 1206 each = 100 V per resistor at a 400 V bus, 0.45 mA / 0.18 W in total.
xb1, xb2, yb = g(28), g(34), g(88)
_, rt, rb = vert2(sh, "R", "R155", xb1, yb + g(3), sh_value("R155"), top=1, text="left")    # pin 1 = DC+
power_at(sh, "DC+", rt, "up")
_, rt, rb = vert2(sh, "R", "R156", xb1, yb + g(9), sh_value("R156"), top=1, text="left")
sh.wire(rb, (xb2, rb[1]))
sh.label("HEATER_CAP_MEAS", xb2, rb[1], 0)
_, rt, rb = vert2(sh, "R", "R157", xb2, yb + g(15), sh_value("R157"), top=1)                # pin 1 = HEATER_CAP_MEAS
_, rt, rb = vert2(sh, "R", "R158", xb2, yb + g(21), sh_value("R158"), top=1)
sh.glabel("HEATER_CURRENT", xb2, rb[1], 0)
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

# --- DRV3: UCC21520 isolated half-bridge driver for Q11 (high) / Q10 (low) - 5.2, NR 3a ----------------
# Replaces the 5.1 pair DRV3 (Si8271, high side) + DRV9 (IXDD609, low side). INA = EPWM5A -> OUTA (high
# side, bootstrap D11 / R99 / C25 from 15V on VDDA / VSSA = HEATER_HI_SOURCE), INB = EPWM6A -> OUTB (low
# side, VDDB = 15V, VSSB = GND); DISABLE tied low; dead time R130 10k = 100 ns backstop.
ucc21520_cell(sh, "DRV3", g(90), g(124), vdd="5V", gnd="GND",
              pwm=("EPWM5A", ("R78", "10k")), nc1=("EPWM6A", ("R77", "10k")), dt=("R130", "10k", "C121", "100p"),
              cdec=("C53", "100n", 1), boot=(("D11", sh_value("D11")), ("R99", sh_value("R99")), ("C25", "1u", 1)),
              rail="15V", railcaps=[("C52", "4.7u", 1), ("C18", "10u", 1)], boot_side="A",
              vo_hi="HEATER_HI_DRV", src_hi="HEATER_HI_SOURCE", vo_lo="HEATER_LOW_DRV", local=True)


def gate_pair(x, y, drv, r_on, r_off, d, gate, pull=None):
    """Driver output label `drv` at (x, y) -> r_on (turn-on) || r_off + Schottky d (cathode at r_off,
    anode at the gate: turn-off path) -> gate label; optional pull-down (rref, rval) gate - GND."""
    sh.label(drv, x, y, 180)
    _, al, ar = horiz2(sh, "R", r_on, x + g(8), y, sh_value(r_on), left=1, text="above")       # pin 1 = driver
    rowb = y + g(5)
    _, bl, br = horiz2(sh, "R", r_off, x + g(8), rowb, sh_value(r_off), left=1, text="below")  # pin 1 = driver
    _, dc, da = horiz2(sh, "D_Schottky", d, x + g(15), rowb, sh_value(d), left="C", text="below")
    xj = x + g(20)
    sh.wire((x, y), al)
    sh.wire((x + g(2), y), (x + g(2), rowb), bl)
    sh.junction(x + g(2), y)
    sh.wire(br, dc)
    sh.wire(ar, (xj, y), (xj + g(8), y))
    sh.wire(da, (xj, rowb), (xj, y))
    sh.junction(xj, y)
    sh.label(gate, xj + g(8), y, 0)
    if pull:
        rref, rval = pull
        _, rt, rb = vert2(sh, "R", rref, xj + g(4), y + g(3), rval, top=1, text="right")   # pin 1 = gate
        sh.junction(*rt)
        power_at(sh, "GND", rb, "down")


# gate networks (5.1: the Si8271 split outputs OUT+ R24 / OUT- R59, the IXDD609 R37 || R31 + D33, R66)
gate_pair(g(160), g(150), "HEATER_HI_DRV", "R24", "R59", "D35", "HEATER_HI_GATE")
gate_pair(g(160), g(166), "HEATER_LOW_DRV", "R37", "R31", "D33", "HEATER_LOW_GATE", pull=("R66", "10k"))
sh.text("5.2: DRV3 = UCC21520DWR drives both heater LLC switches (Q10 / Q11 = IPD60R280P7S DPAK, NR 5.4); DRV9 removed.", g(150), g(180))
sh.text("High side: R24 turn-on, D35 + R59 turn-off (was the Si8271 OUT+ / OUT- pair); low side as the 5.1 IXDD609 output network.", g(150), g(183))

# --- DRV4: UCC27524A dual low-side driver on 6V3 for the synchronous rectifiers (5.2, NR 3a; was IXDD604) ---------------------------
DX, DY = g(236), g(120)
d4 = sh.place("UCC27524A", "DRV4", DX, DY, value=sh_value("DRV4"))
VCC, ENA, INA, INB, ENB = (d4.pin(n) for n in (6, 1, 2, 4, 8))
OUTA, OUTB, GNDP = (d4.pin(n) for n in (7, 5, 3))
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
sh.wire(GNDP, (xgb, GNDP[1]), (xgb, GNDP[1] + g(6)))
power_at(sh, "HT_GND", (xgb, GNDP[1] + g(6)), "down")

sh.text("PDF aliases: DC- = GND, HT_AUX = 6V3, heater_current / heater_cap_meas / q13_drain / EPWM5A_iso / EPWM6A_iso = IPC names.", g(36), g(190))
sh.save()
print("sheet06: written")
