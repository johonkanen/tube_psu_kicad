"""Helpers for the per-sheet transcription scripts (tools/sheets/sheetNN.py).

The generic helpers come from p2k.sheetkit (grid g(), sheet(), left/right/up/down,
glabel_*/label_*, power_at, bus_group, flagged_power, vert2, horiz2, terminal); add helpers
for blocks that repeat on this board below. Each sheet script starts with
    from _common import *  # noqa: F401,F403
"""
import os
import sys

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(TOOLS, "p2k"))  # proteus2kicad
from p2k.sch_builder import Sheet  # noqa: E402,F401
from p2k.sheetkit import *  # noqa: E402,F401,F403


def si8274_cell(sh, ref, UX, UY, vdd, gnd, pwm, nc1, dt, cdec, boot, rail, railcaps, boot_side,
                vo_hi, src_hi, vo_lo):
    """Si8274 isolated half-bridge driver cell as on sheet 2 (DRV5 / DRV6), IC at (UX, UY).

    Input side (left): vdd/gnd = power nets of VDD1 (3, 5, 8) / GND1 (4); pwm = (label, (rref,
    rval)) on pin 1 PWM with its pull-down to gnd, nc1 = the same for pin 2 NC1 (Proteus wires a
    signal to it); dt = (rref, rval) dead-time resistor pin 6 to gnd; cdec = (cref, cval, top)
    decoupling cap vdd-gnd (`top` = pin on the vdd side).
    Output side (right): `rail` = power net of the driver supply; railcaps = [(cref, cval, top)]
    decoupling caps rail-gnd (`top` = pin on the rail side); boot = ((dref, dval), (rref, rval),
    (cref, cval, top)) bootstrap diode (A on the rail), series resistor (pin 1 at the diode) and
    bootstrap cap (`top` = pin on the VDD side). boot_side 'B' = bootstrap feeds VDDB/GNDB (pins
    11/9, outputs VOB high side), 'A' = VDDA/GNDA (16/14). vo_hi / src_hi / vo_lo = global labels
    of the high-side gate, high-side source and low-side gate."""
    u = sh.place("SI8274", ref, UX, UY, value="SI8274")
    VDD1a, VDD1b, PWM, EN, DT, GND1, NC1, NC2 = (u.pin(n) for n in (3, 8, 1, 5, 6, 4, 2, 7))
    VDDA, VOA, GNDA, NC3, NC4, VDDB, VOB, GNDB = (u.pin(n) for n in (16, 15, 14, 13, 12, 11, 10, 9))
    sh.no_connect(*NC2)
    sh.no_connect(*NC3)
    sh.no_connect(*NC4)

    # --- input side -------------------------------------------------------------------
    xs = UX - g(12)                       # VDD1 bus (pins 3 and 8), fed from the top
    sh.wire(VDD1a, (xs, VDD1a[1]))
    sh.wire(VDD1b, (xs, VDD1b[1]))
    top = (xs, UY - g(16))
    sh.wire(top, (xs, VDD1b[1]))
    sh.junction(xs, VDD1a[1])
    power_at(sh, vdd, top, "up")
    cref, cval, ctop = cdec
    xc = UX - g(20)
    _, ct, cb = vert2(sh, "C", cref, xc, UY - g(13), cval, top=ctop)
    sh.wire(top, ct)
    sh.junction(*top)
    power_at(sh, gnd, cb, "down")
    q = left(EN, 2)                       # EN tied to VDD1: own power symbol (the bus would cross PWM)
    sh.wire(EN, q)
    power_at(sh, vdd, q, "left")
    # PWM (pin 1): label at the far left, pull-down beside it
    lab, (rref, rval) = pwm
    xl, xr = UX - g(40), UX - g(36)
    sh.wire(PWM, (xl, PWM[1]))
    sh.glabel(lab, xl, PWM[1], 180)
    _, rt, rb = vert2(sh, "R", rref, xr, PWM[1] + g(3), rval, top=2)
    sh.junction(*rt)
    power_at(sh, gnd, rb, "down")
    # NC1 (pin 2): leaves downwards (under the GND1 / DT wiring), label at the far left
    lab, (rref, rval) = nc1
    row = UY + g(14)
    sh.wire(NC1, (UX - g(10), NC1[1]), (UX - g(10), row), (xl, row))
    sh.glabel(lab, xl, row, 180)
    _, rt, rb = vert2(sh, "R", rref, xr, row + g(3), rval, top=2)
    sh.junction(*rt)
    power_at(sh, gnd, rb, "down")
    # DT resistor and GND1 share a ground symbol
    rref, rval = dt
    xd = UX - g(20)
    sh.wire(DT, (xd, DT[1]))
    _, rt, rb = vert2(sh, "R", rref, xd, UY + g(3), rval, top=1)
    grd = (UX - g(14), UY + g(8))
    sh.wire(rb, (xd, grd[1]), grd)
    sh.wire(GND1, (grd[0], GND1[1]), grd)
    sh.junction(*grd)
    power_at(sh, gnd, grd, "down")

    # --- output side ------------------------------------------------------------------
    RAIL = UY - g(20)
    xr0 = UX + g(10)                      # left end of the rail
    (dref, dval), (rref, rval), (cref, cval, ctop) = boot
    _, da, dc = horiz2(sh, "D", dref, UX + g(36), RAIL, dval, left="A")
    _, r1, r2 = horiz2(sh, "R", rref, UX + g(46), RAIL, rval, left=1)
    sh.wire(dc, r1)
    sh.wire((xr0, RAIL), da)
    power_at(sh, rail, (xr0, RAIL), "up")
    for i, (cr, cv, ct_) in enumerate(railcaps):
        x = xr0 + g(8 * (i + 1) - 2)
        _, ct, cb = vert2(sh, "C", cr, x, RAIL + g(3), cv, top=ct_)
        sh.junction(x, RAIL)
        power_at(sh, gnd, cb, "down")
    xb = r2[0]                            # bootstrap column down from the resistor
    if boot_side == "B":
        sh.wire(VDDA, (xr0, VDDA[1]), (xr0, RAIL))
        sh.junction(xr0, RAIL)
        glabel_right(sh, vo_lo, VOA, 2)
        q = right(GNDA, 2)
        sh.wire(GNDA, q)
        power_at(sh, gnd, q, "right")
        sh.wire(r2, (xb, VDDB[1]), VDDB)
        glabel_right(sh, vo_hi, VOB, 2)
        bt, bb = VDDB[1], GNDB[1] + g(2)
        sh.wire(GNDB, (UX + g(26), GNDB[1]), (UX + g(26), bb), (UX + g(38), bb))
        sh.glabel(src_hi, UX + g(38), bb, 0)
    else:
        sh.wire(r2, (xb, VDDA[1]), VDDA)
        glabel_right(sh, vo_hi, VOA, 2)
        bt, bb = VDDA[1], GNDA[1] + g(2)
        sh.wire(GNDA, (UX + g(26), GNDA[1]), (UX + g(26), bb), (UX + g(38), bb))
        sh.glabel(src_hi, UX + g(38), bb, 0)
        q = right(VDDB, 6)
        sh.wire(VDDB, q)
        power_at(sh, rail, q, "up")
        glabel_right(sh, vo_lo, VOB, 2)
        q = (UX + g(12), GNDB[1] + g(2))
        sh.wire(GNDB, (q[0], GNDB[1]), q)
        power_at(sh, gnd, q, "down")
    _, ct, cb = vert2(sh, "C", cref, UX + g(30), bt + g(3), cval, top=ctop)   # bootstrap cap
    sh.junction(*ct)
    sh.junction(*cb)
    # both floating nodes (bootstrap VDD and the high-side source) are fed by passives only
    sh.pwr_flag(UX + g(40), bt, 0)
    sh.junction(UX + g(40), bt)
    sh.pwr_flag(UX + g(34), bb, 180)
    sh.junction(UX + g(34), bb)
    return u


def ixdd609_cell(sh, ref, UX, UY, vcc, gnd, in_label, r_in, cdec, r_out, out_label, r_gate):
    """IXDD609 MOSFET driver cell as on sheet 9 (DRV1 / DRV2), IC at (UX, UY): VCC pins 1/8
    on a bus fed by the `vcc` power symbol with decoupling cap cdec = (cref, cval, top), EN (3)
    tied to vcc by its own symbol, IN (2) from global label in_label with pull-down r_in =
    (rref, rval), GND pins 4/5/9 on a bus to `gnd`; OUTA/OUTB joined into the parallel gate
    resistors r_out = [(rref, rval), (rref, rval)] (pin 1 on the driver side) and the gate node
    with global label out_label and pull-down r_gate = (rref, rval)."""
    u = sh.place("IXDD609", ref, UX, UY, value=sh_value(ref))
    VCC1, VCC8, IN, EN = u.pin(1), u.pin(8), u.pin(2), u.pin(3)
    OUTA, OUTB, GND4, GND5, TAB = u.pin(7), u.pin(6), u.pin(4), u.pin(5), u.pin(9)
    # VCC bus (pins 1 and 8) fed from the top, decoupling cap beside it
    xs = UX - g(12)
    sh.wire(VCC1, (xs, VCC1[1]))
    sh.wire(VCC8, (xs, VCC8[1]))
    top = (xs, UY - g(12))
    sh.wire(top, (xs, VCC8[1]))
    sh.junction(xs, VCC1[1])
    power_at(sh, vcc, top, "up")
    cref, cval, ctop = cdec
    _, ct, cb = vert2(sh, "C", cref, UX - g(20), UY - g(9), cval, top=ctop)
    sh.wire(top, ct)
    sh.junction(*top)
    power_at(sh, gnd, cb, "down")
    q = left(EN, 2)
    sh.wire(EN, q)
    power_at(sh, vcc, q, "left")
    # IN with pull-down
    xl = UX - g(32)
    sh.wire(IN, (xl, IN[1]))
    sh.glabel(in_label, xl, IN[1], 180)
    rref, rval = r_in
    _, rt, rb = vert2(sh, "R", rref, UX - g(28), IN[1] + g(3), rval, top=2)
    sh.junction(*rt)
    power_at(sh, gnd, rb, "down")
    # GND bus (4, 5, TAB)
    xg = UX + g(10)
    for p in (GND4, GND5, TAB):
        sh.wire(p, (xg, p[1]))
    gb = (xg, TAB[1] + g(4))
    sh.wire((xg, GND4[1]), gb)
    sh.junction(xg, GND5[1])
    sh.junction(xg, TAB[1])
    power_at(sh, gnd, gb, "down")
    # outputs joined, two parallel gate resistors, gate node with pull-down
    xo = UX + g(12)
    sh.wire(OUTA, (xo, OUTA[1]), (xo, OUTB[1]))
    sh.wire(OUTB, (UX + g(16), OUTB[1]))
    sh.junction(xo, OUTB[1])
    (ra, va), (rb_, vb) = r_out
    rowa, rowb = OUTB[1] - g(6), OUTB[1]
    _, al, ar = horiz2(sh, "R", ra, UX + g(22), rowa, va, left=1, text="above")
    _, bl, br = horiz2(sh, "R", rb_, UX + g(22), rowb, vb, left=1, text="below")
    sh.wire((UX + g(16), rowb), (UX + g(16), rowa), al)
    sh.wire((UX + g(16), rowb), bl)
    sh.junction(UX + g(16), rowb)
    sh.wire(ar, (UX + g(28), rowa), (UX + g(28), rowb))
    sh.wire(br, (UX + g(38), rowb))
    sh.junction(UX + g(28), rowb)
    sh.glabel(out_label, UX + g(38), rowb, 0)
    rref, rval = r_gate
    _, rt, rb = vert2(sh, "R", rref, UX + g(34), rowb + g(3), rval, top=2, text="left")
    sh.junction(*rt)
    power_at(sh, gnd, rb, "down")
    return u


def sh_value(ref):
    """Value of a refdes from lib/part_map.csv."""
    import csv
    global _PART_MAP
    try:
        _PART_MAP
    except NameError:
        with open(os.path.join(os.path.dirname(TOOLS), "lib", "part_map.csv")) as f:
            _PART_MAP = {r["refdes"]: r["value"] for r in csv.DictReader(l for l in f if not l.startswith("# "))}
    return _PART_MAP[ref]


def lmh6658_diffamp(sh, ref, unit, AX, AY, inp, bias, bias_top, inn_gnd, fb, cfb, rout, out_label, cout,
                    cbias=None, rout_amp=1, cout_label=2):
    """One half of an LMH6658 drawn as on sheets 8/10: non-inverting amplifier with the input
    through inp = (label, (rref, rval)) (pin 1 at the op-amp), the + node biased by bias = (rref,
    rval) to +2V5_BIAS (`bias_top` = pin on the +2V5_BIAS side), optionally with cbias = (cref,
    cval, top) in parallel (sheet 10), the - node to GND through inn_gnd = (rref, rval) (pin 2 at
    GND), feedback fb = (rref, rval) and cfb = (cref, cval) (pin 2 at the - node), output through
    rout = (rref, rval) (pin `rout_amp` at the op-amp) to the global label out_label with cout =
    (cref, cval) to GND (pin `cout_label` at the label). Returns the placed unit."""
    u = sh.place("LMH6658", ref, AX, AY, unit=unit, value="LMH6658")
    pins = {1: (3, 2, 1), 2: (5, 6, 7)}[unit]
    INP, INN, OUT = (u.pin(n) for n in pins)
    # + input (the resistor moves left when the bias cap needs the room)
    lab, (rref, rval) = inp
    _, rl, rr = horiz2(sh, "R", rref, AX - g(26 if cbias else 22), INP[1], rval, left=2)
    sh.wire(rr, INP)
    glabel_left(sh, lab, rl, 3)
    rref, rval = bias
    _, rt, rb = vert2(sh, "R", rref, AX - g(12), INP[1] - g(3), rval, top=bias_top)
    sh.junction(*rb)
    power_at(sh, "+2V5_BIAS", rt, "up")
    if cbias:
        cref, cval, ctop = cbias
        _, ct, cb = vert2(sh, "C", cref, AX - g(18), INP[1] - g(3), cval, top=ctop, text="left")
        sh.wire(ct, rt)
        sh.junction(*rt)
        sh.junction(*cb)
    # - input: ground resistor, feedback resistor and cap on the row below
    row = AY + g(10)
    sh.wire(INN, (AX - g(12), INN[1]), (AX - g(12), row))
    rref, rval = inn_gnd
    _, rl, rr = horiz2(sh, "R", rref, AX - g(18), row, rval, left=2)
    sh.wire(rr, (AX - g(12), row))
    sh.wire(rl, left(rl, 3))
    power_at(sh, "GND", left(rl, 3), "down")
    rref, rval = fb
    _, rl, rr = horiz2(sh, "R", rref, AX - g(4), row, rval, left=2)
    sh.wire((AX - g(12), row), rl)
    node = (AX + g(10), OUT[1])
    sh.wire(rr, (node[0], row), node)
    cref, cval = cfb
    _, cl, cr = horiz2(sh, "C", cref, AX - g(4), row + g(8), cval, left=2,
                       ref_at=(AX - g(4), row + g(5), 90, None), value_at=(AX - g(4), row + g(11), 90, None))  # rot 270 part: text angle 90 = horizontal
    sh.wire((AX - g(12), row), (AX - g(12), row + g(8)), cl)
    sh.wire(cr, (node[0], row + g(8)), (node[0], row))
    sh.junction(AX - g(12), row)
    sh.junction(node[0], row)
    # output
    sh.wire(OUT, node)
    sh.junction(*node)
    rref, rval = rout
    _, rl, rr = horiz2(sh, "R", rref, AX + g(16), OUT[1], rval, left=rout_amp)
    sh.wire(node, rl)
    q = (AX + g(24), OUT[1])
    sh.wire(rr, q, (AX + g(28), OUT[1]))
    sh.glabel(out_label, AX + g(28), OUT[1], 0)
    cref, cval = cout
    _, ct, cb = vert2(sh, "C", cref, q[0], q[1] + g(3), cval, top=cout_label)
    sh.junction(*q)
    power_at(sh, "GND", cb, "down")
    return u
