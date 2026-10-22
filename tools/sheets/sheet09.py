#!/usr/bin/env python3
"""Sheet 9 - AC measurement (PDF page 9): the two PFC MOSFET drivers DRV1 / DRV2 (IXDD609,
PFC_PWM1/2 -> GATE1/2) and the mains voltage difference amplifier U8 (TLV316) from AC1 / AC2
through 3 x 1M per leg, biased at +2V5_BIAS, output VAC_MEAS."""
from _common import *  # noqa: F401,F403

sh = sheet("09_ac_measurement.kicad_sch")

# PDF labels pfc_pwm1/2 and gate1/2 = IPC nets PFC_PWM1/2 and GATE1/2
ixdd609_cell(sh, "DRV1", g(60), g(40), vcc="20V", gnd="GND", in_label="PFC_PWM1", r_in=("R71", "10k"),
             cdec=("C79", "4.7u", 1), r_out=[("R14", "5R"), ("R1", "5R")], out_label="GATE1",
             r_gate=("R43", "10k"))
ixdd609_cell(sh, "DRV2", g(170), g(40), vcc="20V", gnd="GND", in_label="PFC_PWM2", r_in=("R69", "10k"),
             cdec=("C80", "4.7u", 1), r_out=[("R20", "5R"), ("R19", "5R")], out_label="GATE2",
             r_gate=("R7", "10k"))

# --- difference amplifier -----------------------------------------------------------------
AX, AY = g(100), g(120)
u8 = sh.place("TLV316IDBVR", "U8", AX, AY, value="TLV316IDBVR")
INP, INN, OUT, VP, VN = u8.pin(3), u8.pin(4), u8.pin(1), u8.pin(5), u8.pin(2)
# input legs: AC1 -> R47 -> R48 -> R79 -> (-), AC2 -> R50 -> R51 -> R52 -> (+); pin 1 at the AC side
for x, lab, chain, pin in ((AX - g(30), "AC1", ("R47", "R48", "R79"), INN),
                           (AX - g(22), "AC2", ("R50", "R51", "R52"), INP)):
    sh.glabel(lab, x, AY - g(30), 90)
    prev = (x, AY - g(30))
    for i, r in enumerate(chain):
        _, rt, rb = vert2(sh, "R", r, x, AY - g(24) + g(8 * i), "1M", top=1)
        sh.wire(prev, rt)
        prev = rb
    sh.wire(prev, (x, pin[1]), pin)
# bias of the + input, feedback of the - input
_, rt, rb = vert2(sh, "R", "R80", AX - g(12), AY - g(5), "15k", top=1)     # pin 1 = +2V5_BIAS
sh.junction(*rb)
power_at(sh, "+2V5_BIAS", rt, "up")
node = (AX + g(12), OUT[1])
sh.wire(OUT, node)
_, rl, rr = horiz2(sh, "R", "R49", AX + g(2), AY + g(12), "15k", left=2, text="below")   # pin 1 = output
sh.wire(node, (node[0], AY + g(12)), rr)
sh.wire(rl, (AX - g(14), AY + g(12)), (AX - g(14), INN[1]))
sh.junction(AX - g(14), INN[1])
sh.junction(*node)
# output through R65 to VAC_MEAS
_, rl, rr = horiz2(sh, "R", "R65", AX + g(18), OUT[1], "100R", left=2, text="above")     # pin 2 = output side
sh.wire(node, rl)
glabel_right(sh, "VAC_MEAS", rr, 3)
# supply: +3V3 with C60 (drawn flat above the op-amp), GND
top = (VP[0], AY - g(10))
sh.wire(VP, top)
power_at(sh, "+3V3", top, "up")
_, cl, cr = horiz2(sh, "C", "C60", AX + g(4), AY - g(10), "2u2", left=1,    # pin 1 = +3V3
                   ref_at=(AX + g(4), AY - g(13), 270, None), value_at=(AX + g(4), AY - g(7), 270, None))  # rot 90 part: angle 270 = horizontal
sh.wire(top, cl)
sh.junction(*top)
sh.wire(cr, right(cr, 3))
power_at(sh, "GND", right(cr, 3), "right")
power_at(sh, "GND", VN, "down")

sh.text("PDF labels pfc_pwm1/2, gate1/2 = nets PFC_PWM1/2, GATE1/2.", g(40), g(160))
sh.text("PWR_FLAGs for +3V3 (V4 on sheet 4) and +2V5_BIAS (divider on sheet 4) here until sheet 4 is drawn.", g(40), g(163))
flagged_power(sh, "+3V3", g(44), g(172))
flagged_power(sh, "+2V5_BIAS", g(60), g(172))
sh.save()
print("sheet09: written")
