#!/usr/bin/env python3
"""Sheet 1 - AUX supply (PDF page 1): the flyback auxiliary supply. 5.2: PWM2 = ICE5AR0680AG (NR 1.5, PG-DSO-12
CoolSET, 800 V CoolMOS) switches the primary of TR1 (EEL19, fly leads FL_DC = DC+ / FL_C = FLY_C) from DC+ with
the RCD clamp D7 / R72 / R45 || C12; its VCC comes from 15V through R142 / D10 (C58 / C51), the cascode
start-up through R116 / R115 / R114 from DC+ to GATE, the current sense from Rcs = R8 || R9, the line OVP
divider R151-R153 / R154 || C140 from DC+ to VIN; the integrated
error amplifier regulates the primary-side 5V rail directly (VERR divider R138 / R139, FB network R140 + C138,
C139, RSel R141). Primary-side windings: 1 -> D5 -> 15V (C1, C39), 3 -> D6 -> 5V
(C36, C6, C71). Secondary windings: 10 -> D4 -> 15V_ISO_SEC (C3, C2), 8 -> D14 -> -15V_SEC (C44, C40),
7 -> D29 -> 5V_ISOL (C114, C115), 5 -> D8 -> -100V BIAS (C45, C102); pin 9 = ISO_GND. The outputs go
to the terminals +15V OUT / -15V OUT / -80V OUT / +5V OUT / SEC GND (KiCad refdes P15V_OUT, N15V_OUT,
N80V_OUT, P5V_OUT, SEC_GND) with the bleeders R124 / R123 / R68 / R67.

PDF: DC- = GND, RET_iso / RET_ISO / ISO_GND = ISO_GND (the page joins the terminals RET_iso and
ISO_GND by a bare wire, no part), 20V_ISO_sec = 15V_ISO_SEC, 5v_isol = 5V_ISOL, -100V bias = -100V
BIAS; the PDF net labels d5_A, Sec11, d14_k, d15_K (IPC D5_A, SEC11, D14_K, D15_K) are the winding
ends, wired directly here; the 5.1 aux_fb net (IW1818 knee sensing) is gone in 5.2. This sheet
generates 15V, 5V, 15V_ISO_SEC, -15V_SEC, 5V_ISOL, -100V BIAS and ISO_GND (terminal SEC GND): their
permanent PWR_FLAGs are here; PWM2 VCC (fed through D10 only) has one too."""
from _common import *  # noqa: F401,F403

sh = sheet("01_aux_supply.kicad_sch")

# --- TR1 and the primary-side rectifiers ------------------------------------------------------------
TX, TY = g(150), g(70)
# 5.2: EEL19 4+6 with fly-lead primary (NR 1.1, EEL19_DESIGN.md 6a): FL_DC (11) = DC+, FL_C (12) = collector,
# 1 = A15 (15V), 2 = GND, 3 = A5 (5V); 5 = SHV (-100V BIAS), 7 = S5, 8 = SN5, 9 = ISO_GND, 10 = S15
tr = sh.place("EEL19_4P6", "TR1", TX, TY, value=sh_value("TR1"))
P1, P2, P3, P4, P5 = (tr.pin(str(n)) for n in (1, 2, 3, 11, 12))
P10, P9, P8, P7, P6 = (tr.pin(str(n)) for n in (10, 9, 8, 7, 5))
# pin 1 -> D5 -> 15V rail (raised above the 5V group), C39 / C1 to GND
_, dc, da = horiz2(sh, "D", "D5", TX - g(14), P1[1], sh_value("D5"), left="C", text="above")
sh.wire(da, P1)
x20 = TX - g(24)
R20 = P1[1] - g(10)
sh.wire(dc, (x20, P1[1]), (x20, R20), (TX - g(46), R20))
for x, ref, sym in ((TX - g(32), "C39", "C"), (TX - g(40), "C1", "C_Polarized")):
    _, ct, cb = vert2(sh, sym, ref, x, R20 + g(3), sh_value(ref), top=1)         # pin 1 = 15V
    sh.junction(x, R20)
    if ref == "C39":
        sh.wire(cb, (x - g(8), cb[1]))
    else:
        sh.junction(*cb)
        power_at(sh, "GND", cb, "down")
flagged_power(sh, "15V", TX - g(46), R20)
# pin 2 = GND
sh.wire(P2, left(P2, 2))
power_at(sh, "GND", left(P2, 2), "left")
# pin 3 -> D6 -> 5V rail, C36 / C6 / C71 (pin 2 = 5V) to GND (5.2: no AUX_FB tap, PWM2 regulates the 5V rail)
_, dc, da = horiz2(sh, "D", "D6", TX - g(26), P3[1], sh_value("D6"), left="C", text="below")
sh.wire(da, P3)
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
sh.label("FLY_C", xcol, CROW, 0)                                 # 5.2: named collector node (HV net class)

# --- PWM2 with the Vcc network, the clamp, the shunt, the start-up chain and the feedback network --------
PX, PY = g(70), g(118)              # 5.2: DRAIN (right row 0 of 6) on CROW
# 5.2: ICE5AR0680AG (NR 1.5, Infineon datasheet V2.3 PG-DSO-12, non-isolated application figure 2,
# EEL19_DESIGN.md 14): 5-8 DRAIN = FLY_C, 12 GND, 4 CS (Rcs R8 || R9), 10 GATE (cascode start-up R116 / R115 /
# R114 from DC+), 11 VCC (15V via R142 / D10, C58 / C51), 2 VERR (5V divider R138 / R139), 3 FB (R140 + C138,
# C139, RSel R141 to GND), 1 VIN (line OVP: DC+ -> R151-R153 -> VIN, R154 || C140 to GND), 9 NC
pwm = sh.place("ICE5AR", "PWM2", PX, PY, value=sh_value("PWM2"))
GATE, VCC, VERR, FB, CS, DRAIN, PGND = (pwm.pin(n) for n in (10, 11, 2, 3, 4, 5, 12))
VIN = pwm.pin(1)
sh.wire(DRAIN, (xcol, DRAIN[1]))                                 # drain row = CROW
# DRAIN pins 6 / 7 / 8 joined to pin 5 by a short bus right of the symbol
xdb = DRAIN[0] + g(2)
for n in (6, 7, 8):
    p = pwm.pin(n)
    sh.wire(p, (xdb, p[1]))
sh.wire((xdb, DRAIN[1]), (xdb, pwm.pin(8)[1]))
for n in (5, 6, 7):
    sh.junction(xdb, pwm.pin(n)[1])
sh.no_connect(*pwm.pin(9))                                       # pin 9 NC (next to the drain gap)
sh.wire(PGND, right(PGND, 2))
power_at(sh, "GND", right(PGND, 2), "down")
# clamp: D7 (A at the drain) -> R72 -> node -> R45 || C12 -> DC+
xs = g(120)
_, dt, db = vert2(sh, "D", "D7", xs, CROW - g(3), sh_value("D7"), top="C")         # A = drain
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
# VIN: line OVP divider DC+ -> R151 -> R152 -> R153 -> VIN, R154 (178k) || C140 (470p) to GND: trip 2.85 V x
# 30.178 / 0.178 = 483 V (EEL19_DESIGN.md 14). R151-R153 DNP leaves VIN at GND through R154 = LOVP disabled.
VR = VIN[1]
xvn = VIN[0] + g(14)
sh.wire(VIN, (xvn, VR))
_, ct, cb = vert2(sh, "C", "C140", VIN[0] + g(6), VR + g(3), sh_value("C140"), top=1, text="right")
sh.junction(*ct)
power_at(sh, "GND", cb, "down")
_, rt, rb = vert2(sh, "R", "R154", xvn, VR + g(3), sh_value("R154"), top=1, text="right")   # pin 1 = VIN
power_at(sh, "GND", rb, "down")
prev = (xvn, VR)
for i, r in enumerate(("R153", "R152", "R151")):
    _, rl, rr = horiz2(sh, "R", r, xvn + g(6) + g(8) * i, VR, sh_value(r), left=2, text="above")  # pin 1 = DC+ side
    sh.wire(prev, rl)
    prev = rr
sh.junction(xvn, VR)
sh.wire(prev, right(prev, 2))
power_at(sh, "DC+", right(prev, 2), "up")
# C15: DC+ decoupling (standalone pair)
_, ct, cb = vert2(sh, "C", "C15", g(100), g(91), sh_value("C15"), top=2)           # pin 2 = DC+
power_at(sh, "DC+", ct, "up")
power_at(sh, "GND", cb, "down")
# GATE: cascode start-up chain R114 / R115 / R116 (3 x 4.7M 1206) from DC+ (starts from 60 V)
xg = PX - g(14)
sh.wire(GATE, (xg, GATE[1]))
prev = (xg, GATE[1])
for i, r in enumerate(("R114", "R115", "R116")):
    _, rt, rb = vert2(sh, "R", r, xg, GATE[1] - g(6) - g(8 * i), sh_value(r), top=1, text="right")   # pin 1 = DC+ side
    sh.wire(rb, prev)
    prev = rt
power_at(sh, "DC+", prev, "up")
# Vcc: 15V -> R142 -> D10 -> Vcc, C58 (22u) / C51 to GND, PWR_FLAG (passive feed)
xv = PX - g(18)
NV = VCC[1] - g(14)
sh.wire(VCC, (xv, VCC[1]), (xv, NV))
_, da, dc = horiz2(sh, "D_Schottky", "D10", PX - g(38), NV, sh_value("D10"), left="A")   # A = 15V side
_, rl, rr = horiz2(sh, "R", "R142", PX - g(48), NV, sh_value("R142"), left=1, text="above")
sh.wire(rr, da)
sh.wire(rl, left(rl, 2))
power_at(sh, "15V", left(rl, 2), "left")
sh.wire(dc, (xv, NV), (xv, NV - g(4)))
sh.junction(xv, NV)
sh.pwr_flag(xv, NV - g(4), 0)
for x, ref, sym in ((xv - g(12), "C58", "C_Polarized"), (xv - g(6), "C51", "C")):
    _, ct, cb = vert2(sh, sym, ref, x, NV + g(3), sh_value(ref), top=1)           # pin 1 = Vcc
    sh.junction(x, NV)
    power_at(sh, "GND", cb, "down")
# CS: Rcs = R8 || R9 to GND
xe = PX - g(14)
SROW = CS[1] + g(8)
sh.wire(CS, (xe, CS[1]), (xe, SROW), (xe + g(10), SROW))
_, at, ab = vert2(sh, "R", "R8", xe, SROW + g(3), sh_value("R8"), top=1)          # pin 1 = CS
_, bt, bb = vert2(sh, "R", "R9", xe + g(10), SROW + g(3), sh_value("R9"), top=1)
sh.junction(*at)
sh.wire(ab, bb)
sh.junction(*ab)
power_at(sh, "GND", ab, "down")
# FB: R140 + C138 (compensation), C139 (HF pole), R141 = RSel (ABM option 2) to GND
xf = PX - g(20)
FROW = FB[1] + g(8)
sh.wire(FB, (xf, FB[1]), (xf, FROW), (xf - g(12), FROW))
for x, ref, sym in ((xf, "C139", "C"), (xf - g(6), "R141", "R")):
    _, t, b = vert2(sh, sym, ref, x, FROW + g(3), sh_value(ref), top=1, text="right")
    sh.junction(x, FROW)
    power_at(sh, "GND", b, "down")
_, t, b = vert2(sh, "R", "R140", xf - g(12), FROW + g(3), sh_value("R140"), top=1, text="left")
_, ct, cb = vert2(sh, "C", "C138", xf - g(12), b[1] + g(3), sh_value("C138"), top=1, text="left")
power_at(sh, "GND", cb, "down")
# VERR: 5V -> R138 -> VERR node -> R139 -> GND (0.1 %)
xd = PX - g(46)
sh.wire(VERR, (xd, VERR[1]))
_, rt, rb = vert2(sh, "R", "R138", xd, VERR[1] - g(3), sh_value("R138"), top=1, text="left")   # pin 1 = 5V
power_at(sh, "5V", rt, "up")
_, rt2, rb2 = vert2(sh, "R", "R139", xd, VERR[1] + g(3), sh_value("R139"), top=1, text="left")  # pin 1 = VERR
power_at(sh, "GND", rb2, "down")
sh.junction(xd, VERR[1])
sh.text("PWM2 ICE5AR0680AG (NR 1.5, PG-DSO-12, 100-450 V DC+): 5V = 1.80 V x (1 + R138 / R139) = 5.00 V; RSel R141 750k = ABM option 2 (entry VFB 0.93 V, VCS 0.22 V);", g(16), g(146))
sh.text("Rcs R8 || R9 = 2 x 1.37R = 0.685R (Ipk limit 1.04-1.30 A at VCS_N 0.72-0.88 V); start-up 3 x 4.7M from DC+ to GATE (starts from 60 V); VCC 14-15 V from 15V via R142 / D10.", g(16), g(149))
sh.text("VIN line OVP: 3 x 10M / 178k = trip 483 V (R151-R153 DNP: VIN at GND, LOVP off). Layout: DRAIN pins 5-8 one F.Cu + B.Cu area 2-3 cm2 (HV_PRIMARY, FLY_C),", g(16), g(152))
sh.text("away from FB / VERR and the TR1 slot, pin 9 NC unconnected; VERR / FB parts close to pins 2 / 3, Rcs return to pin 12.", g(16), g(155))

# --- secondary rectifier groups, fanned out on separate rows (nested columns, no crossings) ------
sh.wire(P9, right(P9, 4))
power_at(sh, "ISO_GND", right(P9, 4), "right")
XN = TX + g(26)                                                 # rail start column
groups = [  # pin, column offset, row, diode (ref, pin at the transformer side), rail net, caps (ref, sym, top), cap text
    (P10, 2, g(52), ("D4", "A"), "15V_ISO_SEC", [("C3", "C", 1), ("C2", "C_Polarized", 1)]),
    (P8, 6, g(84), ("D14", "C"), "-15V_SEC", [("C44", "C", 2), ("C40", "C", 2)]),
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
# --- preloads (NR 1.7): 2.2k on 15V, 1k on 5V (standalone pairs) -------------------------------------
for x, ref, rail in ((g(28), "R125", "15V"), (g(40), "R126", "5V")):
    _, rt, rb = vert2(sh, "R", ref, x, g(52), sh_value(ref), top=1)                  # pin 1 = rail
    power_at(sh, rail, rt, "up")
    power_at(sh, "GND", rb, "down")
sh.text("Preloads R125 / R126 (NR 1.7, light-load excursions).", g(16), g(62))

sh.text("Secondary winding ends (PDF labels Sec11, d14_k, d15_K; IPC SEC11, D14_K, D15_K) and D5_A are wired directly.", TX + g(2), g(134))

# --- terminals with the bleeders -----------------------------------------------------------------
XT = g(292)
y = g(136)
terminal(sh, "SEC_GND", XT, y, "right")
sh.wire((XT - g(20), y), (XT, y))
flagged_power(sh, "ISO_GND", XT - g(20), y)
for i, (tref, rail, rref) in enumerate((("P15V_OUT", "15V_ISO_SEC", "R124"), ("N15V_OUT", "-15V_SEC", "R123"),
                                         ("N80V_OUT", "-100V BIAS", "R68"), ("P5V_OUT", "5V_ISOL", "R67"))):
    y = g(148 + 12 * i)
    terminal(sh, tref, XT, y, "right")
    sh.wire((XT - g(40), y), (XT, y))
    power_at(sh, rail, (XT - g(40), y), "left")
    _, rt, rb = vert2(sh, "R", rref, XT - g(20), y + g(3), sh_value(rref), top=2)   # pin 2 = rail, pin 1 = ISO_GND
    sh.junction(XT - g(20), y)
    power_at(sh, "ISO_GND", rb, "down")
sh.text("Terminals +15V OUT / -15V OUT / -80V OUT / +5V OUT / SEC GND = P15V_OUT / N15V_OUT / N80V_OUT / P5V_OUT / SEC_GND;", g(100), g(200))
sh.text("the PDF joins the terminals RET_iso and ISO_GND by a bare wire (one net ISO_GND, no part).", g(100), g(203))

# --- PDF notes ----------------------------------------------------------------------------------
sh.text("5.2: TR1 = EEL19 4+6 (fly leads FL_DC / FL_C, pins 4 / 6 clipped), PWM2 = ICE5AR0680AG (5V regulated through VERR); R8 || R9 = 1.37R || 1.37R = 0.685R.", g(16), g(37))
sh.text("5.1 PDF notes (IW1818 Vsense / Isense values, EF20 winding variants) dropped in 5.2: PWM2 and TR1 replaced (NR 1.1, 1.5).", g(16), g(20))
sh.text("PWR_FLAGs: 15V, 5V, 15V_ISO_SEC, -15V_SEC, 5V_ISOL, -100V BIAS (rectifier outputs), ISO_GND (SEC GND terminal), PWM2 Vcc (fed through D10 only): permanent.", g(16), g(34))
sh.save()
print("sheet01: written")
