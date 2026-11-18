"""Helpers for the 5.2 sheet scripts (tools/next/sheets/sheetNN.py), forked from tools/sheets/_common.py.

Same helpers as the 5.1 migration; the differences are all in this header and in the CSV paths:
  - output: kicad_next/<sheet> of the project tube_psu_5_2 (the 5.1 scripts write kicad/),
  - symbols: lib/tube_psu_next.kicad_sym (library nickname tube_psu_next, tools/next/gen_symbols.py),
  - values / footprints / LCSC: lib/part_map_next.csv, lib/footprint_map_next.csv, lib/jlc_parts_next.csv
    (hand-edited forks of the 5.1 tables).
The shared p2k submodule is not changed: p2k.sch_builder's library / footprint lookups are replaced at
module level and Sheet.save rewrites the library nickname. Symbol UUIDs are seeded as in 5.1 (project
name of p2k_config.py + sheet file), so an unchanged sheet keeps the 5.1 UUIDs.
Each sheet script starts with
    from _common import *  # noqa: F401,F403
"""
import os
import sys

NEXT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # tools/next
TOOLS = os.path.dirname(NEXT)                                        # tools
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, os.path.join(TOOLS, "p2k"))  # proteus2kicad
from p2k import sch_builder  # noqa: E402
from p2k.sch_builder import Sheet  # noqa: E402,F401
from p2k.sexpr import find_all, load  # noqa: E402
from p2k.sheetkit import *  # noqa: E402,F401,F403

PROJECT = "tube_psu_5_2"                       # KiCad project (kicad_next/tube_psu_5_2.kicad_pro)
SYMLIB = "tube_psu_next"                       # symbol library nickname -> lib/tube_psu_next.kicad_sym
OUT_DIR = os.environ.get("TUBE_PSU_NEXT_OUT", os.path.join(ROOT, "kicad_next"))
LIB_DIR = os.path.join(ROOT, "lib")
_NEXT_LIB = None
_NEXT_FP = None


def _next_lib():
    global _NEXT_LIB
    if _NEXT_LIB is None:
        _NEXT_LIB = {s[1]: s for s in find_all(load(os.path.join(LIB_DIR, SYMLIB + ".kicad_sym")), "symbol")}
    return _NEXT_LIB


def _next_footprint(ref):
    import csv
    global _NEXT_FP
    if _NEXT_FP is None:
        with open(os.path.join(LIB_DIR, "footprint_map_next.csv")) as f:
            _NEXT_FP = {r["refdes"]: r["footprint"] for r in csv.DictReader(l for l in f if not l.startswith("#"))}
    return _NEXT_FP.get(ref, "")


sch_builder.lib = _next_lib
sch_builder.footprint = _next_footprint


def _rename_lib(node, old, new):
    for i, c in enumerate(node):
        if isinstance(c, list):
            _rename_lib(c, old, new)
        elif isinstance(c, str) and c.startswith(old):
            node[i] = new + c[len(old):]


def _save_next(self):
    _rename_lib(self.tree, f"{PROJECT}:", f"{SYMLIB}:")
    sch_builder.save(self.path, self.tree)


Sheet.save = _save_next


TITLE_REV, TITLE_COMMENT = "V5.2", "tube_power 5.2 - from the 5.1 migration, NEXT_REVISION.md changes (tools/next)"


def sheet(fname):
    """The 5.2 sub-sheet kicad_next/<fname>, cleared for a fresh rebuild (replaces p2k.sheetkit.sheet); the
    title block gets the 5.2 revision."""
    sh = Sheet(os.path.join(OUT_DIR, fname), project=PROJECT).clear()
    for tb in find_all(sh.tree, "title_block"):
        for c in tb:
            if isinstance(c, list) and c and str(c[0]) == "rev":
                c[1] = TITLE_REV
            elif isinstance(c, list) and c and str(c[0]) == "comment" and c[1] == 1:
                c[2] = TITLE_COMMENT
    return sh


# --- LCSC field --------------------------------------------------------------------------------------
# Every placed part gets a hidden "LCSC" property (JLCPCB/LCSC part number, empty for consigned /
# missing / DNP parts) from lib/jlc_parts_next.csv. Done here by wrapping Sheet.place so the shared p2k
# submodule stays unchanged; power symbols and flags (#PWR, #FLG) and parts not in the CSV get no field.
_LCSC = None


def lcsc(ref):
    """LCSC part number of a refdes from lib/jlc_parts_next.csv ('' if none, None if not listed)."""
    import csv
    global _LCSC
    if _LCSC is None:
        path = os.path.join(LIB_DIR, "jlc_parts_next.csv")
        _LCSC = {}
        if os.path.exists(path):
            with open(path, newline="", encoding="utf-8") as f:
                _LCSC = {r["refdes"]: r["lcsc"] for r in csv.DictReader(l for l in f if not l.startswith("#"))}
    return _LCSC.get(ref)


_sheet_place = Sheet.place


def _place_with_lcsc(self, name, ref, *args, **kw):
    code = lcsc(ref)
    if code is not None and len(args) < 6:  # fields not passed positionally
        kw["fields"] = dict(kw.get("fields") or {})
        kw["fields"].setdefault("LCSC", code)
    return _sheet_place(self, name, ref, *args, **kw)


Sheet.place = _place_with_lcsc


def ucc21520_cell(sh, ref, UX, UY, vdd, gnd, pwm, nc1, dt, cdec, boot, rail, railcaps, boot_side,
                  vo_hi, src_hi, vo_lo, dis=None, local=False):
    """UCC21520 isolated dual gate driver cell (5.2, NEXT_REVISION.md 3a), IC at (UX, UY). Forked from the 5.1
    Si8275 cell: the UCC21520 has the same SOIC-16W pin positions (1 INA, 2 INB, 3/8 VCCI, 4 GND, 5 DISABLE,
    6 DT, 9 VSSB, 10 OUTB, 11 VDDB, 14 VSSA, 15 OUTA, 16 VDDA; 7/12/13 NC); INA -> OUTA, INB -> OUTB.

    Input side (left): vdd/gnd = power nets of VCCI (3, 8) / GND (4); pwm = (label, (rref, rval)) on pin 1
    INA with its pull-down to gnd, nc1 = the same for pin 2 INB; dt = (rref, rval, cref, cval): dead-time
    resistor DT - GND (DT = 10 ns per kOhm, hardware backstop for the FPGA dead time) with its noise cap in
    parallel (datasheet: <= 1 nF); cdec = (cref, cval, top) decoupling cap vdd-gnd. dis = None ties DISABLE
    (pin 5) to gnd; dis = (label, (rref, rval) or None, (cref, cval) or None) brings it out to a global
    label with an optional pull-down and bypass cap to gnd (high = both outputs off).
    Output side (right): as the 5.1 cell - rail, railcaps, boot = ((dref, dval), (rref, rval), (cref, cval,
    top)), boot_side 'B' = bootstrap on VDDB/VSSB (OUTB high side), 'A' = VDDA/VSSA; vo_hi / src_hi / vo_lo
    = labels of the high-side gate, high-side source and low-side gate (global, or local with local=True)."""
    lab_fn = sh.label if local else sh.glabel
    u = sh.place("UCC21520", ref, UX, UY, value=sh_value(ref))
    VDD1a, VDD1b, PWM, DIS, DT, GND1, NC1, NC2 = (u.pin(n) for n in (3, 8, 1, 5, 6, 4, 2, 7))
    VDDA, VOA, GNDA, NC3, NC4, VDDB, VOB, GNDB = (u.pin(n) for n in (16, 15, 14, 13, 12, 11, 10, 9))
    sh.no_connect(*NC2)
    sh.no_connect(*NC3)
    sh.no_connect(*NC4)

    # --- input side -------------------------------------------------------------------
    xs = UX - g(12)                       # VCCI bus (pins 3 and 8), fed from the top
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
    xl, xr = UX - g(48), UX - g(44)
    if dis is None:                       # DISABLE tied to the input ground (datasheet: tie low if unused)
        q = left(DIS, 2)
        sh.wire(DIS, q)
        power_at(sh, gnd, q, "left")
    else:
        lab, pd, cap = dis
        xq = UX - g(34)
        sh.wire(DIS, (xq, DIS[1]))
        sh.glabel(lab, xq, DIS[1], 180)
        for x, part, sym in ((UX - g(26), pd, "R"), (UX - g(30), cap, "C")):
            if part:
                _, pt, pb = vert2(sh, sym, part[0], x, DIS[1] + g(3), part[1], top=1)
                sh.junction(*pt)
                power_at(sh, gnd, pb, "down")
    # INA (pin 1): label at the far left, pull-down beside it
    lab, (rref, rval) = pwm
    sh.wire(PWM, (xl, PWM[1]))
    sh.glabel(lab, xl, PWM[1], 180)
    _, rt, rb = vert2(sh, "R", rref, xr, PWM[1] + g(3), rval, top=2)
    sh.junction(*rt)
    power_at(sh, gnd, rb, "down")
    # INB (pin 2): leaves downwards (under the GND / DT wiring), label at the far left
    lab, (rref, rval) = nc1
    row = UY + g(14)
    sh.wire(NC1, (UX - g(10), NC1[1]), (UX - g(10), row), (xl, row))
    sh.glabel(lab, xl, row, 180)
    _, rt, rb = vert2(sh, "R", rref, xr, row + g(3), rval, top=2)
    sh.junction(*rt)
    power_at(sh, gnd, rb, "down")
    # DT resistor || cap and GND share a ground symbol
    rref, rval, dcref, dcval = dt
    xd = UX - g(20)
    sh.wire(DT, (xd, DT[1]))
    _, rt, rb = vert2(sh, "R", rref, xd, UY + g(3), rval, top=1)
    _, ct, cb = vert2(sh, "C", dcref, UX - g(16), UY + g(3), dcval, top=1, text="right")
    sh.junction(*ct)
    sh.wire(cb, rb)
    sh.junction(*rb)
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

    def out(name, p):
        q = right(p, 2)
        sh.wire(p, q)
        lab_fn(name, *q, 0)

    if boot_side == "B":
        sh.wire(VDDA, (xr0, VDDA[1]), (xr0, RAIL))
        sh.junction(xr0, RAIL)
        out(vo_lo, VOA)
        q = right(GNDA, 2)
        sh.wire(GNDA, q)
        power_at(sh, gnd, q, "right")
        sh.wire(r2, (xb, VDDB[1]), VDDB)
        out(vo_hi, VOB)
        bt, bb = VDDB[1], GNDB[1] + g(2)
        sh.wire(GNDB, (UX + g(26), GNDB[1]), (UX + g(26), bb), (UX + g(38), bb))
        lab_fn(src_hi, UX + g(38), bb, 0)
    else:
        sh.wire(r2, (xb, VDDA[1]), VDDA)
        out(vo_hi, VOA)
        bt, bb = VDDA[1], GNDA[1] + g(2)
        sh.wire(GNDA, (UX + g(26), GNDA[1]), (UX + g(26), bb), (UX + g(38), bb))
        lab_fn(src_hi, UX + g(38), bb, 0)
        q = right(VDDB, 6)
        sh.wire(VDDB, q)
        power_at(sh, rail, q, "up")
        out(vo_lo, VOB)
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


def ucc27511_cell(sh, ref, UX, UY, vcc, gnd, in_label, r_in, cdec, r_on, r_off, out_label, r_gate):
    """UCC27511A low-side gate driver cell (5.2, NEXT_REVISION.md 3a; replaces the 5.1 IXDD609 cell on
    sheet 9), IC at (UX, UY): VDD (1) from the `vcc` power symbol with the decoupling cap cdec = (cref, cval,
    top), IN+ (6) from global label in_label with the pull-down r_in = (rref, rval), IN- (5) and GND (4)
    to gnd; the split outputs OUTH (2) / OUTL (3) through r_on / r_off = (rref, rval) (pin 1 on the driver
    side: separate turn-on / turn-off resistors) into the gate node with the global label out_label and
    the pull-down r_gate = (rref, rval)."""
    u = sh.place("UCC27511A", ref, UX, UY, value=sh_value(ref))
    VDD, INP, INN, OUTH, OUTL, GNDP = (u.pin(n) for n in (1, 6, 5, 2, 3, 4))
    xs = UX - g(12)
    top = (xs, UY - g(10))
    sh.wire(VDD, (xs, VDD[1]), top)
    power_at(sh, vcc, top, "up")
    cref, cval, ctop = cdec
    _, ct, cb = vert2(sh, "C", cref, UX - g(18), UY - g(7), cval, top=ctop)
    sh.wire(top, (UX - g(18), top[1]), ct)
    sh.junction(*top)
    power_at(sh, gnd, cb, "down")
    xl = UX - g(28)
    sh.wire(INP, (xl, INP[1]))
    sh.glabel(in_label, xl, INP[1], 180)
    rref, rval = r_in
    _, rt, rb = vert2(sh, "R", rref, UX - g(24), INP[1] + g(3), rval, top=2)
    sh.junction(*rt)
    power_at(sh, gnd, rb, "down")
    q = left(INN, 2)
    sh.wire(INN, q)
    power_at(sh, gnd, q, "left")
    q = right(GNDP, 2)
    sh.wire(GNDP, q)
    power_at(sh, gnd, q, "down")
    ya, yb = OUTH[1] - g(4), OUTL[1]
    sh.wire(OUTH, (UX + g(10), OUTH[1]), (UX + g(10), ya))
    (ra, va), (rb_, vb) = r_on, r_off
    _, al, ar = horiz2(sh, "R", ra, UX + g(16), ya, va, left=1, text="above")
    _, bl, br = horiz2(sh, "R", rb_, UX + g(16), yb, vb, left=1, text="below")
    sh.wire((UX + g(10), ya), al)
    sh.wire(OUTL, bl)
    xj = UX + g(24)
    sh.wire(ar, (xj, ya), (xj, yb))
    sh.wire(br, (xj + g(10), yb))
    sh.junction(xj, yb)
    sh.glabel(out_label, xj + g(10), yb, 0)
    rref, rval = r_gate
    _, rt, rb = vert2(sh, "R", rref, xj + g(6), yb + g(3), rval, top=2, text="left")   # pin 2 = gate (as 5.1)
    sh.junction(*rt)
    power_at(sh, gnd, rb, "down")
    return u


def sh_value(ref):
    """Value of a refdes from lib/part_map_next.csv."""
    import csv
    global _PART_MAP
    try:
        _PART_MAP
    except NameError:
        with open(os.path.join(LIB_DIR, "part_map_next.csv")) as f:
            _PART_MAP = {r["refdes"]: r["value"] for r in csv.DictReader(l for l in f if not l.startswith("# "))}
    return _PART_MAP[ref]


def follower(sh, part, ref, unit, X, Y, rout, out_label=None, local=True):
    """Unity-gain follower (5.2, NEXT_REVISION.md 4.1 / 4b / 4c): op-amp unit at (X, Y) with the - input fed
    back from the output (before the series resistor), output through rout = (rref, rval) (pin 1 at the
    op-amp) to the label out_label (local or global; None = the caller wires the resistor end). Returns
    (+ input point, resistor far end, placed unit); supply pins (TLV316 V+ / V-) are wired by the caller. Pins as the MCP6L91T / LM2904 std symbols (+ at (-7.62, 2.54),
    - at (-7.62, -2.54), out at (7.62, 0))."""
    pins = (3, 4, 1) if part == "TLV316IDBVR" else {1: (3, 2, 1), 2: (5, 6, 7)}[unit]   # (+, -, out)
    u = sh.place(part, ref, X, Y, unit=unit, value=sh_value(ref))
    INP, INN, OUT = (u.pin(n) for n in pins)
    node = (X + g(8), OUT[1])
    sh.wire(OUT, node)
    fy = INN[1] + g(2)
    sh.wire(INN, (X - g(8), INN[1]), (X - g(8), fy), (node[0], fy), node)
    sh.junction(*node)
    rref, rval = rout
    _, rl, rr = horiz2(sh, "R", rref, X + g(14), OUT[1], rval, left=1, text="above")
    sh.wire(node, rl)
    if out_label:
        q = right(rr, 3)
        sh.wire(rr, q)
        (sh.label if local else sh.glabel)(out_label, *q, 0)
    return INP, rr, u


def lmh6658_diffamp(sh, ref, unit, AX, AY, inp, bias, bias_top, inn_gnd, fb, cfb, rout, out_label, cout,
                    cbias=None, rout_amp=1, cout_label=2, part="LMH6643"):
    """One half of an LMH6658 drawn as on sheets 8/10: non-inverting amplifier with the input
    through inp = (label, (rref, rval)) (pin 1 at the op-amp), the + node biased by bias = (rref,
    rval) to +1V65_BIAS (`bias_top` = pin on the +1V65_BIAS side), optionally with cbias = (cref,
    cval, top) in parallel (sheet 10), the - node to GND through inn_gnd = (rref, rval) (pin 2 at
    GND), feedback fb = (rref, rval) and cfb = (cref, cval) (pin 2 at the - node), output through
    rout = (rref, rval) (pin `rout_amp` at the op-amp) to the global label out_label with cout =
    (cref, cval) to GND (pin `cout_label` at the label). Returns the placed unit."""
    u = sh.place(part, ref, AX, AY, unit=unit, value=sh_value(ref))       # 5.2: LMH6643 (NR 4.10b)
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
    power_at(sh, "+1V65_BIAS", rt, "up")
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
