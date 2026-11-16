"""Winding options for TR1 (EF20) – the current build and the candidates.

Winding names (OpenMagnetics) and their circuit roles (board pins, schematic sheet 1):

  P, P1, P2  primary 52 T, pin 4 (DC+) -> pin 5 (collector, PWM2 IW1818 C)
  A15        primary-side 15 V aux, pin 2 (GND) -> pin 1 -> D5 -> net 20V (gate drivers, IW1818 Vcc via D10)
  A5         primary-side 5 V / feedback, pin 2 -> pin 3 -> D6 -> net 5V; pin 3 = AUX_FB (Vsense divider)
  S15        isolated 15 V, pin 9 (ISO_GND) -> pin 10 -> D4 -> 20V_ISO_SEC
  S5         isolated 5 V, pin 9 -> pin 7 -> D29 -> 5V_ISOL
  SN5        isolated -5 V, pin 8 -> D14 (cathode) ; anode -> -5V_SEC ; other end pin 9
  SHV        isolated -80 V, pin 6 -> D8 (cathode) ; anode -> -100V BIAS ; other end pin 9
  ...x       the extension of a tapped (AC-stacked) winding, e.g. S15x = pin 7 -> pin 10 on top of S5

Current build: V2 "52/8/3||7/3/3/42" (PDF sheet 1). The user confirmed that V2 (52 T
primary) is the wound transformer and that every secondary is a separate winding (none
stacked). Mapping, checked against the pinout and the rail voltages (1.86 V/turn at the
regulated knee, 5.58 V / 3 T from the Vsense divider):
  52 primary (4-5) / 8 = 20V aux (1-2, 14.9 V - Vf) / 3 = 5V aux + feedback (3-2)
  || 7 = 20V_ISO_SEC (10-9, 13.0 V - Vf) / 3 = 5V_ISOL (7-9) / 3 = -5V_SEC (8-9) / 42 = -100V BIAS (6-9, 78 V - Vf).
  "||" is the isolation barrier (4 layers of tape, design doc ch. 2.1); the list is taken as
  the winding order from the bobbin outwards (assumed). The isolated 15 V winding has 7 T,
  one less than the primary-side one (design doc table 2.1 lists one "15V winding 8 T").
  All windings 3 x AWG34 in parallel (design doc), 3 mm margin tape both sides (design doc,
  user), windings on top of each other (user), one tape layer between windings (assumed).

Bifilar / trifilar sections use om_model mode "multifilar": the strands of the windings
alternate one by one across the layer, as when the wires are wound together as one bundle.
(Until 2026-11-16 the mode "bifilar" alternated whole turns, i.e. groups of 3-4 parallel
strands per winding side by side, which gave 3-5x the leakage between the windings sharing
the layer; the MKF field grid was checked and is converged, the layout was the cause.)

Spice connection: every winding is (dot, other). All windings are wound in the same
direction; the primary dot is DC+, so during the flyback interval every dot is negative
with respect to its other end. Positive outputs: dot on the return, diode anode on the
other end. Negative outputs: dot on the diode cathode, other end on the return.
"""

W34 = "Round 34.0 - Heavy Build"      # AWG34 heavy build, 0.16 mm Cu, 0.191 mm OD
W30 = "Round 30.0 - Heavy Build"      # 0.255 mm Cu
W28 = "Round 28.0 - Heavy Build"
W32 = "Round 32.0 - Heavy Build"      # 0.203 mm Cu
TIW30 = "Round TCA3 30 AWG"           # Rubadue TCA3 triple insulated, reinforced (IEC 61558/62368 class)
TIW28 = "Round TCA3 28 AWG"
TIW26 = "Round TCA3 26 AWG"
TIW32 = "Round TCA3 32 AWG"

PRI, SEC = "primary", "secondary"
M3 = (0.003, 0.003)                   # 3 mm margin tape both sides (design doc)

# standard circuit connections (nodes of flyback_sim.py)
SP_BASE = {
    "P": ("dcp", "col"), "P1": ("dcp", "pm"), "P2": ("pm", "col"),
    "A15": ("0", "a1"), "A5": ("0", "a3"),
    "S15": ("iso", "s10"), "S5": ("iso", "s7"),
    "SN5": ("s8", "iso"), "SHV": ("s6", "iso"),
    # tapped (AC-stacked) variants: 5 V section from the return to the tap, extension on top
    "A15x": ("a3", "a1"),          # 20V winding = A5 + A15x  (pin 2 -> 3 -> 1)
    "S15x": ("s7", "s10"),         # 20V_ISO = S5 + S15x      (pin 9 -> 7 -> 10)
    "SHVx": ("s6", "s8"),          # -80 V = SN5 + SHVx       (pin 9 -> 8 -> 6)
}


def current():
    return {
        "name": "current",
        "title": "Current V2 build: P | A15 | A5 || S15 | S5 | SN5 | SHV, 3xAWG34, 3 mm margins",
        "write_mas": True,
        "sections": [
            {"windings": [("P", 52, 3, W34, PRI)], "margin": M3, "tape_after": 1},
            {"windings": [("A15", 8, 3, W34, PRI)], "margin": M3, "tape_after": 1},
            {"windings": [("A5", 3, 3, W34, PRI)], "margin": M3, "tape_after": 4},
            {"windings": [("S15", 7, 3, W34, SEC)], "margin": M3, "tape_after": 1},
            {"windings": [("S5", 3, 3, W34, SEC)], "margin": M3, "tape_after": 1},
            {"windings": [("SN5", 3, 3, W34, SEC)], "margin": M3, "tape_after": 1},
            {"windings": [("SHV", 42, 3, W34, SEC)], "margin": M3, "tape_after": 1},
        ],
    }


def stacked():
    """Electrical change only: same build order and wire, but AC-stacked (tapped) windings:
    20V = A5 3 T + A15x 5 T (pin 2 -> 3 -> 1), 20V_ISO = S5 3 T + S15x 4 T (pin 9 -> 7 -> 10),
    -80 V = SN5 3 T + SHVx 39 T (pin 9 -> 8 -> 6). Same pins, same board."""
    return {
        "name": "stacked",
        "title": "Current build, windings tapped (AC-stacked) on the 5 V windings, 3xAWG34, margins",
        "sections": [
            {"windings": [("P", 52, 3, W34, PRI)], "margin": M3, "tape_after": 1},
            {"windings": [("A5", 3, 3, W34, PRI), ("A15x", 5, 3, W34, PRI)], "margin": M3, "tape_after": 4},
            {"windings": [("S5", 3, 3, W34, SEC), ("S15x", 4, 3, W34, SEC)], "margin": M3, "tape_after": 1},
            {"windings": [("SN5", 3, 3, W34, SEC), ("SHVx", 39, 3, W34, SEC)], "margin": M3, "tape_after": 1},
        ],
    }


def margin_sandwich():
    """No TIW: keep enamel wire and 3 mm margins, but split the primary around the
    secondaries (two barriers of 4 tape layers), fill each low-turn layer with parallel
    strands spread over the 6.6 mm, wind 5V_ISOL and -5V bifilar, aux windings outside."""
    return {
        "name": "margin_sandwich",
        "title": "Enamel + margins: P1 || S15 | S5/SN5 bifilar | SHV || A5 | A15 | P2, spread strands",
        "sections": [
            {"windings": [("P1", 26, 1, W32, PRI)], "margin": M3, "tape_after": 4},
            {"windings": [("S15", 7, 3, W30, SEC)], "margin": M3, "align": "spread", "tape_after": 1},
            {"windings": [("S5", 3, 3, W30, SEC), ("SN5", 3, 3, W30, SEC)], "mode": "multifilar",
             "margin": M3, "align": "spread", "tape_after": 1},
            {"windings": [("SHV", 42, 1, W34, SEC)], "margin": M3, "align": "spread", "tape_after": 4},
            {"windings": [("A5", 3, 6, W30, PRI)], "margin": M3, "align": "spread", "tape_after": 1},
            {"windings": [("A15", 8, 2, W30, PRI)], "margin": M3, "align": "spread", "tape_after": 1},
            {"windings": [("P2", 26, 1, W32, PRI)], "margin": M3, "tape_after": 1},
        ],
    }


def tiw_simple():
    """TIW secondaries, no margin tape (full 12.6 mm width), same order as today:
    P | A15 | A5 | S15 | S5/SN5 bifilar | SHV, low-turn windings spread with parallels."""
    return {
        "name": "tiw_simple",
        "title": "TIW secondaries, no margins: P | A15 | A5 | S15 | S5/SN5 bifilar | SHV",
        "sections": [
            {"windings": [("P", 52, 1, W30, PRI)], "tape_after": 1},
            {"windings": [("A15", 8, 4, W30, PRI)], "align": "spread", "tape_after": 0},
            {"windings": [("A5", 3, 12, W30, PRI)], "align": "spread", "tape_after": 1},
            {"windings": [("S15", 7, 3, TIW30, SEC)], "align": "spread"},
            {"windings": [("S5", 3, 4, TIW30, SEC), ("SN5", 3, 4, TIW30, SEC)], "mode": "multifilar", "align": "spread"},
            {"windings": [("SHV", 42, 1, TIW32, SEC)], "align": "spread", "tape_after": 1},
        ],
    }


def tiw_sandwich():
    """TIW secondaries, no margins, split primary: P1 | S15 | A5/S5/SN5 trifilar | SHV | A15 | P2.
    The feedback winding A5 (enamel) is wound in the same layer as the two isolated 5 V
    windings (TIW provides the reinforced insulation between them)."""
    return {
        "name": "tiw_sandwich",
        "title": "TIW, no margins, sandwich: P1 | S15 | A5+S5+SN5 trifilar | SHV | A15 | P2",
        "sections": [
            {"windings": [("P1", 26, 1, W30, PRI)], "align": "spread", "tape_after": 1},
            {"windings": [("S15", 7, 3, TIW30, SEC)], "align": "spread"},
            {"windings": [("A5", 3, 3, W30, PRI), ("S5", 3, 3, TIW30, SEC), ("SN5", 3, 3, TIW30, SEC)],
             "mode": "multifilar", "align": "spread"},
            {"windings": [("SHV", 42, 1, TIW32, SEC)], "align": "spread", "tape_after": 1},
            {"windings": [("A15", 8, 4, W30, PRI)], "align": "spread", "tape_after": 1},
            {"windings": [("P2", 26, 1, W30, PRI)], "align": "spread", "tape_after": 1},
        ],
    }


def tiw_sandwich_stacked():
    """tiw_sandwich with tapped windings: S15 = S5 + S15x 4 T, SHV = SN5 + SHVx 39 T,
    A15 = A5 + A15x 5 T. Same pins."""
    return {
        "name": "tiw_sandwich_stacked",
        "title": "TIW sandwich + tapped: P1 | S15x | A5+S5+SN5 trifilar | SHVx | A15x | P2",
        "sections": [
            {"windings": [("P1", 26, 1, W30, PRI)], "align": "spread", "tape_after": 1},
            {"windings": [("S15x", 4, 5, TIW30, SEC)], "align": "spread"},
            {"windings": [("A5", 3, 3, W30, PRI), ("S5", 3, 3, TIW30, SEC), ("SN5", 3, 3, TIW30, SEC)],
             "mode": "multifilar", "align": "spread"},
            {"windings": [("SHVx", 39, 1, TIW32, SEC)], "align": "spread", "tape_after": 1},
            {"windings": [("A15x", 5, 6, W30, PRI)], "align": "spread", "tape_after": 1},
            {"windings": [("P2", 26, 1, W30, PRI)], "align": "spread", "tape_after": 1},
        ],
    }


def recommended(preload=None):
    """tiw_sandwich with the isolated 15 V winding at 8 T (same as the primary-side 15 V
    winding, so 20V_ISO_SEC comes out at ~15 V like 20V instead of ~13 V)."""
    o = tiw_sandwich()
    o["name"] = "recommended" + ("_pre" if preload else "")
    o["title"] = "TIW sandwich, S15 8 T: P1 | S15 | A5+S5+SN5 trifilar | SHV | A15 | P2" + (" + preloads" if preload else "")
    o["sections"][1] = {"windings": [("S15", 8, 3, TIW30, SEC)], "align": "spread"}
    o["write_mas"] = not preload
    if preload:
        o["preload"] = preload
    return o


def sandwich_paired(order="b"):
    """TIW sandwich with every voltage class paired in one multifilar layer: the two 15 V
    windings (A15 enamel + S15 TIW, both 8 T) and the three 5 V windings (A5 + S5 + SN5,
    3 T) each share a layer, so each pair sees the same leakage field and the feedback
    winding A5 sits directly beside the 15 V pair.
    order b: P1 | SHV | A15+S15 | A5+S5+SN5 | P2   (low-turn layers shielded from P1 by SHV)
    order c: P1 | A5+S5+SN5 | A15+S15 | SHV | P2   (feedback layer next to the primary)"""
    p1 = {"windings": [("P1", 26, 1, W30, PRI)], "align": "spread", "tape_after": 1}
    p2 = {"windings": [("P2", 26, 1, W30, PRI)], "align": "spread", "tape_after": 1}
    shv = {"windings": [("SHV", 42, 1, TIW32, SEC)], "align": "spread"}
    w15 = {"windings": [("A15", 8, 3, W30, PRI), ("S15", 8, 3, TIW30, SEC)], "mode": "multifilar", "align": "spread"}
    w5 = {"windings": [("A5", 3, 3, W30, PRI), ("S5", 3, 3, TIW30, SEC), ("SN5", 3, 3, TIW30, SEC)],
          "mode": "multifilar", "align": "spread"}
    secs = [p1, shv, w15, w5, p2] if order == "b" else [p1, w5, w15, shv, p2]
    names = " | ".join("+".join(w[0] for w in x["windings"]) for x in secs)
    return {"name": f"sandwich_paired_{order}", "title": f"TIW sandwich, paired layers, S15 8 T: {names}",
            "sections": secs}


PRELOAD = {"20V": 3300.0, "5V": 1000.0}      # what-if preload resistors (not in the schematic)


OPTIONS = {"current": current, "stacked": stacked, "margin_sandwich": margin_sandwich,
           "tiw_simple": tiw_simple, "tiw_sandwich": tiw_sandwich,
           "tiw_sandwich_stacked": tiw_sandwich_stacked,
           "recommended": recommended, "recommended_pre": lambda: recommended(PRELOAD),
           "sandwich_paired_b": lambda: sandwich_paired("b"), "sandwich_paired_c": lambda: sandwich_paired("c")}


def get(name):
    opt = OPTIONS[name]()
    opt.setdefault("spice", {})
    for sec in opt["sections"]:
        for w in sec["windings"]:
            opt["spice"].setdefault(w[0], SP_BASE[w[0]])
    return opt
