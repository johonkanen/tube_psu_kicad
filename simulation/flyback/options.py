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

Current build ("V2 : 52/8/3||7/3/3/42", PDF sheet 1), interpretation used here:
  52 primary / 8 (15 V aux) / 3 (5 V aux, feedback) || 7 (isolated 15 V) / 3 (5 V_ISOL) / 3 (-5 V) / 42 (-80 V).
  "||" is read as the isolation barrier (4 layers of tape, design doc ch. 2.1) between the
  primary-side windings and the isolated ones, and the list as the winding order from the
  bobbin outwards (primary first). The 7 T isolated 15 V winding differs from the 8 T one
  of design doc table 2.1 (which lists one "15V winding 8 T" for both sides).
  All windings 3 x AWG34 in parallel (design doc), 3 mm margin tape both sides (design doc),
  windings simply on top of each other (user), one tape layer between windings (assumed).

Spice connection: every winding is (dot, other). All windings are wound in the same
direction; the primary dot is DC+, so during the flyback interval every dot is negative
with respect to its other end. Positive outputs: dot on the return, diode anode on the
other end. Negative outputs: dot on the diode cathode, other end on the return.
"""

W34 = "Round 34.0 - Heavy Build"      # AWG34 heavy build, 0.16 mm Cu, 0.191 mm OD
W30 = "Round 30.0 - Heavy Build"      # 0.255 mm Cu
W28 = "Round 28.0 - Heavy Build"
TIW30 = "Round TCA3 30 AWG"           # Rubadue TCA3 triple insulated, reinforced (IEC 61558/62368 class)
TIW28 = "Round TCA3 28 AWG"
TIW26 = "Round TCA3 26 AWG"

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


OPTIONS = {"current": current}


def get(name):
    opt = OPTIONS[name]()
    opt.setdefault("spice", {})
    for sec in opt["sections"]:
        for w in sec["windings"]:
            opt["spice"].setdefault(w[0], SP_BASE[w[0]])
    return opt
