#!/usr/bin/env python3
"""Sheet 9 - AC measurement (PDF page 9): the two PFC MOSFET drivers DRV1 / DRV2 (5.2: UCC27511A; 5.1 IXDD609,
PFC_PWM1/2 -> GATE1/2) and the mains voltage difference amplifier U8 (TLV316) from AC1 / AC2
through 3 x 1M per leg, biased at +1V65_BIAS, output VAC_MEAS."""
from _common import *  # noqa: F401,F403

sh = sheet("09_ac_measurement.kicad_sch")

# PDF labels pfc_pwm1/2 and gate1/2 = IPC nets PFC_PWM1/2 and GATE1/2.
# 5.2 (NR 3a): DRV1 / DRV2 = UCC27511ADBVR (SOT-23-6, split outputs: R14 / R20 turn-on on OUTH, R1 / R19
# turn-off on OUTL; was the IXDD609 with both resistors in parallel).
ucc27511_cell(sh, "DRV1", g(60), g(40), vcc="15V", gnd="GND", in_label="PFC_PWM1", r_in=("R71", "10k"),
              cdec=("C79", "4.7u", 1), r_on=("R14", "5R"), r_off=("R1", "5R"), out_label="GATE1",
              r_gate=("R43", "10k"))
ucc27511_cell(sh, "DRV2", g(170), g(40), vcc="15V", gnd="GND", in_label="PFC_PWM2", r_in=("R69", "10k"),
              cdec=("C80", "4.7u", 1), r_on=("R20", "5R"), r_off=("R19", "5R"), out_label="GATE2",
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
_, rt, rb = vert2(sh, "R", "R80", AX - g(12), AY - g(5), sh_value("R80"), top=1)     # pin 1 = +1V65_BIAS
sh.junction(*rb)
power_at(sh, "+1V65_BIAS", rt, "up")
# 5.2 (NR 4.2): C126 1 nF C0G across R80 (pole 13.3 kHz with 12k), matched with C127 across R49
_, ct, cb = vert2(sh, "C", "C126", AX - g(17), AY - g(5), sh_value("C126"), top=1, text="left")   # pin 1 = +1V65_BIAS
sh.wire(ct, rt)
sh.junction(*rt)
sh.junction(*cb)
node = (AX + g(12), OUT[1])
sh.wire(OUT, node)
_, rl, rr = horiz2(sh, "R", "R49", AX + g(2), AY + g(12), sh_value("R49"), left=2, text="above")   # pin 1 = output
sh.wire(node, (node[0], AY + g(12)), rr)
sh.wire(rl, (AX - g(14), AY + g(12)), (AX - g(14), INN[1]))
sh.junction(AX - g(14), INN[1])
_, cl, cr = horiz2(sh, "C", "C127", AX + g(2), AY + g(16), sh_value("C127"), left=2, text="below")  # pin 1 = output
sh.wire((AX - g(14), AY + g(12)), (AX - g(14), AY + g(16)), cl)
sh.wire(cr, (node[0], AY + g(16)), (node[0], AY + g(12)))
sh.junction(AX - g(14), AY + g(12))
sh.junction(node[0], AY + g(12))
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
sh.text("5.2: R49 / R80 15k -> 12k (gain 0.004, no clipping up to 264 Vrms, NR 4.3), C126 / C127 1 nF C0G across R80 / R49 (NR 4.2); no output cap (ADC mux).", g(40), g(163))
sh.save()
print("sheet09: written")
