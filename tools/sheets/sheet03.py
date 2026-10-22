#!/usr/bin/env python3
"""Sheet 3 - Isolated measurements (PDF page 3): two identical isolated measurement channels.
Each channel: an Si8661 digital isolator (ISO) between the MCU (+3V3 / GND, global labels) and an
isolated side, an ADC121S101 (AD) whose CS / CLK / SDATA go through the isolator, a TLV316 (U)
measurement amplifier feeding the ADC input through a series resistor + cap, and a MIC5205 LDO (V,
TPS73033 device) making the isolated 3.3 V rail with its decoupling caps.

  secondary (top): ISO2 / AD2 / U3 / V2, ground ISO_GND, rail AD2_3V3 (power symbol), V2 fed by
                   5V_ISOL; measures CUK_CAP_MEAS2 (- input CUK_CAP_MEAS-) for the Cuk capacitor.
  primary HT side (bottom): ISO1 / AD1 / U2 / V3, ground HT_GND, rail = auto net #00086 (wire),
                   V3 fed from 6V3 (PDF terminal HT_AUX) through D2 + D3; measures HEATER_VOLTAGE_MEAS.

PDF aliases: SEC_GND = ISO_GND, HT_AUX = 6V3, AD2_3v3 = AD2_3V3, lowercase synch_1/2, ht_clk,
ht_sdata, CUK_clk, CUK_sdata, Cuk_cap_meas2 / Cuk_cap_meas- = IPC names; overlined CUK_CS / HT_CS
= $CUK_CS / $HT_CS. The ADC is drawn rotated 180 (digital pins facing the isolator), the LDO rotated
180 (VOUT facing the rail)."""
from _common import *  # noqa: F401,F403

sh = sheet("03_isolated_measurements.kicad_sch")


def iso_channel(sh, IX, IY, iso, left_pins, out_pins, cdec, adc, c_vin, r_in, amp, inp, inn, r_fb,
                gnd, rail_power, rail_caps, reg, c_nr, c_in, vin):
    """One channel with the isolator at (IX, IY). left_pins = {pin: global label or None (= gnd)}
    for ISO pins 2-7, out_pins = {15: .., 14: .., 13: ..} global labels or None (= no connect);
    cdec = +3V3 decoupling cap ref (standalone pair at the left); c_vin / r_in = ADC input cap /
    series resistor refs (R pin 1 at the op-amp, C pin 1 at the ADC); amp = TLV316 ref with + input
    global label `inp` and - node `inn` = ("label", name) or ("res", ref) (resistor pin 1 at the
    node, pin 2 to gnd); r_fb = feedback resistor (pin 1 at the - node); gnd = isolated ground
    power net; rail_power = power symbol on the rail or None (auto net); rail_caps = cap refs
    (pin 1 on the rail); reg = LDO ref, c_nr = NR cap (pin 1 at NR), c_in = input cap (pin 1 at VIN);
    vin = ("power", net) or ("diodes", [refs A->C from the source], flagged source power net)."""
    u = sh.place("SI8661", iso, IX, IY, value=sh_value(iso))
    # --- MCU side (left) -------------------------------------------------------------------
    VDD1, GND1 = u.pin(1), u.pin(8)
    xs = IX - g(12)
    sh.wire(VDD1, (xs, VDD1[1]), (xs, VDD1[1] - g(4)))
    power_at(sh, "+3V3", (xs, VDD1[1] - g(4)), "up")
    for pin, lab in left_pins.items():
        p = u.pin(pin)
        if lab is None:                        # input tied to GND
            q = left(p, 2)
            sh.wire(p, q)
            power_at(sh, "GND", q, "left")
        else:
            glabel_left(sh, lab, p, 6)
    sh.wire(GND1, (xs, GND1[1]))
    power_at(sh, "GND", (xs, GND1[1]), "down")
    _, ct, cb = vert2(sh, "C", cdec, IX - g(26), IY - g(3), sh_value(cdec), top=1, text="left")  # pin 1 = +3V3
    sh.wire(ct, up(ct, 2))
    power_at(sh, "+3V3", up(ct, 2), "up")
    power_at(sh, "GND", cb, "down")

    # --- isolated side (right): rail column, outputs, ADC digital pins ----------------------
    RAIL = IY - g(28)
    VDD2, GND2 = u.pin(16), u.pin(9)
    xr = IX + g(12)
    sh.wire(VDD2, (xr, VDD2[1]), (xr, RAIL))
    if rail_power:
        power_at(sh, rail_power, (xr, RAIL), "up")
        sh.junction(xr, RAIL)
    for pin, lab in out_pins.items():
        p = u.pin(pin)
        if lab is None:
            sh.no_connect(*p)
        else:
            glabel_right(sh, lab, p, 6)
    sh.wire(GND2, down(GND2, 4))
    power_at(sh, gnd, down(GND2, 4), "down")
    AX, AY = IX + g(28), IY + g(4)
    a = sh.place("ADC121S101", adc, AX, AY, rot=180, value=sh_value(adc))
    VA, AGND, VIN_A, CS, SDATA, CLK = (a.pin(n) for n in (1, 2, 3, 6, 5, 4))
    VO_D, VO_E, VI_F = u.pin(12), u.pin(11), u.pin(10)
    sh.wire(VO_E, CLK)                                   # straight: E -> CLK, F <- SDATA
    sh.wire(VI_F, SDATA)
    xl = IX + g(14)                                      # D -> CS loops down (2 wire crossings as in the PDF)
    sh.wire(VO_D, (xl, VO_D[1]), (xl, CS[1]), CS)
    # --- ADC analog side: GND, VA up to the rail, Vin node with cap + series resistor --------
    power_at(sh, gnd, AGND, "right")
    xva = AX + g(40)
    VAROW = IY + g(16)
    sh.wire(VA, (AX + g(20), VA[1]), (AX + g(20), VAROW), (xva, VAROW), (xva, RAIL))
    sh.junction(xva, RAIL)
    node = (AX + g(24), VIN_A[1])
    sh.wire(VIN_A, node)
    sh.junction(*node)
    _, ct, cb = vert2(sh, "C", c_vin, node[0], node[1] + g(3), sh_value(c_vin), top=1)   # pin 1 = ADC Vin
    power_at(sh, gnd, cb, "down")
    _, rl, rr = horiz2(sh, "R", r_in, AX + g(30), node[1], sh_value(r_in), left=2, text="above")  # pin 2 = ADC side
    sh.wire(node, rl)
    xn = AX + g(36)                                      # op-amp output node column
    sh.wire(rr, (xn, node[1]))

    # --- op-amp above the ADC row ----------------------------------------------------------
    OX, OY = AX + g(28), IY - g(18)
    o = sh.place("TLV316IDBVR", amp, OX, OY, value=sh_value(amp))
    INP, INN, OUT, VP, VN = o.pin(3), o.pin(4), o.pin(1), o.pin(5), o.pin(2)
    sh.wire(OUT, (xn, OUT[1]), (xn, node[1]))
    sh.junction(xn, OUT[1])
    sh.wire(VP, (VP[0], RAIL))
    sh.junction(VP[0], RAIL)
    power_at(sh, gnd, VN, "down")
    glabel_left(sh, inp, INP, 6)
    fx = AX + g(18)                                      # - node column
    sh.wire(INN, (fx, INN[1]))
    sh.junction(fx, INN[1])
    if inn[0] == "label":
        sh.wire((fx, INN[1]), (AX + g(16), INN[1]))
        sh.glabel(inn[1], AX + g(16), INN[1], 180)
    else:
        _, rl, rr = horiz2(sh, "R", inn[1], AX + g(13), INN[1], sh_value(inn[1]), left=2, text="below")  # pin 1 = - node
        sh.wire(rr, (fx, INN[1]))
        sh.wire(rl, left(rl, 2))
        power_at(sh, gnd, left(rl, 2), "left")
    FROW = OY + g(12)
    _, rl, rr = horiz2(sh, "R", r_fb, AX + g(30), FROW, sh_value(r_fb), left=1, text="below")  # pin 1 = - node
    sh.wire((fx, INN[1]), (fx, FROW), rl)
    sh.wire(rr, (xn, FROW))
    sh.junction(xn, FROW)

    # --- rail caps and the LDO (rotated 180: VOUT on the left, on the rail) -----------------
    VX = AX + g(78)
    v = sh.place("TPS73033", reg, VX, RAIL, rot=180, value=sh_value(reg))
    VIN, VGND, EN, NR, VOUT = (v.pin(n) for n in (1, 2, 3, 4, 5))
    sh.wire((xr, RAIL), VOUT)
    GROW = RAIL + g(6)
    xs0 = AX + g(42)
    for i, cref in enumerate(rail_caps):
        x = xs0 + g(6 * i)
        _, ct, cb = vert2(sh, "C", cref, x, RAIL + g(3), sh_value(cref), top=1)        # pin 1 = rail
        sh.junction(x, RAIL)
        if i:
            sh.wire((x - g(6), GROW), cb)                # common ground row under the caps
        if 0 < i < len(rail_caps) - 1:
            sh.junction(*cb)
    power_at(sh, gnd, (xs0 + g(6), GROW), "down")
    xnr = VX - g(12)
    sh.wire(NR, (xnr, NR[1]))
    _, ct, cb = vert2(sh, "C", c_nr, xnr, NR[1] + g(3), sh_value(c_nr), top=1, text="left")   # pin 1 = NR
    power_at(sh, gnd, cb, "down")
    power_at(sh, gnd, VGND, "right")
    xi = VX + g(22)                                      # VIN and EN tied
    sh.wire(EN, (xi, EN[1]), (xi, VIN[1]), VIN)
    sh.junction(xi, VIN[1])
    _, ct, cb = vert2(sh, "C", c_in, xi, VIN[1] + g(3), sh_value(c_in), top=1)          # pin 1 = VIN
    power_at(sh, gnd, cb, "down")
    if vin[0] == "power":
        sh.wire((xi, EN[1]), (xi, EN[1] - g(4)))
        power_at(sh, vin[1], (xi, EN[1] - g(4)), "up")
    else:
        DROW = RAIL - g(14)
        sh.wire((xi, EN[1]), (xi, DROW))
        sh.pwr_flag(xi, DROW + g(6), 270)            # permanent: VIN fed by the diodes + cap only
        sh.junction(xi, DROW + g(6))
        prev = (xi, DROW)
        for i, dref in enumerate(vin[1]):
            _, da, dc = horiz2(sh, "D_Schottky", dref, xi - g(5) - g(10 * i), DROW, sh_value(dref), left="A")
            sh.wire(dc, prev)
            prev = da
        q = (prev[0] - g(4), DROW)
        sh.wire(prev, q)
        flagged_power(sh, vin[2], *q)
    return u


# Secondary channel (PDF top): Cuk capacitor voltage, isolated 3.3 V rail AD2_3V3 from 5V_ISOL.
iso_channel(sh, g(46), g(56), iso="ISO2",
            left_pins={2: "EPWM2A", 3: "EPWM2B", 4: None, 5: "$CUK_CS", 6: "CUK_CLK", 7: "CUK_SDATA"},
            out_pins={15: "ISO_SEC_DHB_HI", 14: "ISO_SEC_DHB_LO", 13: None}, cdec="C98",
            adc="AD2", c_vin="C5", r_in="R13", amp="U3", inp="CUK_CAP_MEAS2", inn=("label", "CUK_CAP_MEAS-"),
            r_fb="R113", gnd="ISO_GND", rail_power="AD2_3V3", rail_caps=["C103", "C105", "C57"],
            reg="V2", c_nr="C34", c_in="C21", vin=("power", "5V_ISOL"))

# Primary HT channel (PDF bottom): heater voltage, rail = auto net (V3 VOUT) fed from 6V3 via D2 + D3.
iso_channel(sh, g(46), g(126), iso="ISO1",
            left_pins={2: None, 3: "SYNCH_1", 4: "SYNCH_2", 5: "$HT_CS", 6: "HT_CLK", 7: "HT_SDATA"},
            out_pins={15: None, 14: "EPWM5A_ISO", 13: "EPWM6A_ISO"}, cdec="C97",
            adc="AD1", c_vin="C7", r_in="R18", amp="U2", inp="HEATER_VOLTAGE_MEAS", inn=("res", "R121"),
            r_fb="R122", gnd="HT_GND", rail_power=None, rail_caps=["C59", "C104", "C83"],
            reg="V3", c_nr="C78", c_in="C13", vin=("diodes", ["D3", "D2"], "6V3"))

sh.text("Primary (MCU side)", g(14), g(14), size=2.0)
sh.text("Secondary (isolated side)", g(120), g(14), size=2.0)
sh.text("Pin compatible with MAX11110, ADS7886 S/H, ADS7883 S/H (PDF note on the ADC).", g(14), g(18))
sh.text("V5.1 (PDF hand note).", g(14), g(21))
sh.text("PDF aliases: SEC_GND = ISO_GND, HT_AUX = 6V3, AD2_3v3 = AD2_3V3; lowercase labels = IPC names.", g(14), g(160))
sh.text("The HT rail (ISO1 VDD2, AD1 VA, U2 V+, V3 VOUT, C59/C104/C83) is an unnamed net in Proteus (#00086): plain wire.", g(14), g(163))
# 6V3 and HT_GND enter through the terminals HT_6V3 / HT_GND on sheet 6; on this sheet only passives and
# power-input pins touch them, so they carry PWR_FLAGs here until sheet 6 is drawn.
sh.text("PWR_FLAGs of 6V3 (at D2) and HT_GND (below): temporary, to be moved to sheet 6 (terminals HT_6V3 / HT_GND).", g(14), g(166))
sh.text("The PWR_FLAG on V3 VIN is permanent (the net is fed by D3 and C13 only).", g(14), g(169))
flagged_power(sh, "HT_GND", g(30), g(176))
sh.save()
print("sheet03: written")
