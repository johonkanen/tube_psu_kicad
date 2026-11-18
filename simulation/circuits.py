"""The measurement circuits simulated by simulation/run_sim.py (PLAN.md section 1).

Only references and roles are written here; every value comes from the KiCad schematic
through spice/extract.py. One topology covers all four model groups (vhdl/meas_models_pkg.vhd):

    + leg:  IN --[in_p: 1..3 sections R (|| Cpar)]-- NP --[ref_p: R || C]-- REF
    - leg:  0  --[g:    1..3 sections R (|| Cpar)]-- NN --[f:     R || C]-- VO
    op-amp: NP, NN -> VO (macromodel: A0, one pole at GBW/A0, Rout)
    output: VO --[o: R]-- OUT --[c_o: C]-- 0        (no c_o: OUT = VO, R unloaded)
    REF = the +1V65_BIAS node (REF1 -> R110 / R3 || C48 + the loads of the other circuits)
          or the circuit's ground

  group A shunt diff amp (1-4):   IN = shunt voltage (input = shunt current x R_shunt)
  group B HV diff amp (5, 6, 8):  3 x 1M chains with a parasitic C_PAR across each 1M
  group C divider + RC (7):       no op-amp, OUT = NP
  group D divider + non-inv (9):  - leg R to ground, f = feedback R

  group E divider + follower (5.2 AUX_MEAS, 5V_MEAS): + leg as group C, op-amp follower
          (NN = VO, no - leg), output R (unloaded)

Roles map to reference designators. A role may list several refs (series sections).

Board revision: 5.1 (kicad/, the default) or 5.2 (kicad_next/). Selected by the environment
variable MEAS_SIM_REV or a `--rev 5.2` argument of the calling script (run_sim.py, run_ac.py,
extract.py, gen_params.py, compare.py); the rev decides the schematic, the circuit list, the bias
network and the output folder (5.1: simulation/out/, 5.2: simulation/out/5.2/).
"""
import os
import sys
from pathlib import Path


def _rev():
    if "--rev" in sys.argv[:-1]:
        os.environ["MEAS_SIM_REV"] = sys.argv[sys.argv.index("--rev") + 1]
    rev = os.environ.get("MEAS_SIM_REV", "5.1")
    if rev not in ("5.1", "5.2"):
        raise SystemExit(f"unknown board revision {rev!r} (5.1 or 5.2)")
    return rev


REV = _rev()
SIM = Path(__file__).resolve().parent
REPO = SIM.parent
if REV == "5.1":
    OUT = SIM / "out"
    SCHEMATIC = REPO / "kicad/tube_psu.kicad_sch"
    NETFILE = OUT / "tube_psu.net"
    PARAMS_VHD = SIM / "vhdl/meas_params_pkg.vhd"
else:
    OUT = SIM / "out/5.2"
    SCHEMATIC = REPO / "kicad_next/tube_psu_5_2.kicad_sch"
    NETFILE = OUT / "tube_psu_5_2.net"
    PARAMS_VHD = SIM / "vhdl/rev5_2/meas_params_pkg.vhd"
SPICE_OUT = OUT / "spice"

# op-amp macromodel: same in ngspice (spice/run_ac.py) and VHDL (vhdl/meas_params_pkg.vhd)
# a0 = DC open-loop gain, gbw = unity-gain frequency [Hz], rout = open-loop output resistance
OPAMPS = {
    # TLV316 (SBOS752): 10 MHz GBW, Zo 250 ohm @ 10 MHz; A0 100 dB assumed (rail-to-rail CMOS)
    "TLV316IDBVR": dict(a0=1.0e5, gbw=10.0e6, rout=250.0,
                        pins={"": ("3", "4", "1")}),
    # LMH6658 (SNOSA35): 140 MHz GBW, A_VOL 95 dB typ; Rout 10 ohm assumed (not specified)
    "LMH6658": dict(a0=10 ** (95 / 20), gbw=140.0e6, rout=10.0,
                    pins={"A": ("3", "2", "1"), "B": ("5", "6", "7")}),
    # 5.2. LMH6643 (SNOS966Q): GBWP 57 MHz (applications section), A_VOL 96 dB typ / 80 dB min at
    # 3 V, 2 k; SR 120 V/us typ at 3 V (135 at 10 V); Rout 75 ohm = open-loop Zo of the TI/NSC
    # vendor model above 100 kHz (spice/vendor_models.py)
    "LMH6643": dict(a0=10 ** (96 / 20), gbw=57.0e6, rout=75.0, sr=120e6,
                    pins={"A": ("3", "2", "1"), "B": ("5", "6", "7")}),
    # TLV9062 (SBOS839): 10 MHz GBW, 6.5 V/us; A0 118 dB and Zo 100 ohm from the TI vendor model
    "TLV9062": dict(a0=10 ** (118 / 20), gbw=10.0e6, rout=100.0, sr=6.5e6,
                    pins={"A": ("3", "2", "1"), "B": ("5", "6", "7")}),
}
OPAMPS["TLV316IDBVR"]["sr"] = 6.0e6
OPAMPS["TLV9062IDGKR"] = OPAMPS["TLV9062"]

# parasitic capacitance added across every 1 Mohm resistor of the group-B chains (PLAN step 2)
C_PAR_PER_MOHM = 0.2e-12

BIAS_NET = "+1V65_BIAS"
if REV == "5.1":
    BIAS_VOLTAGE = 1.65        # user decision 2026-11-14: loaded bias node = 1.65 V
    BIAS_REFS = dict(kind="divider", ref="REF1", r_top="R110", r_bot="R3", c_bias="C48", c_ref="C69")
    REF_VALUE = "ISL21010CFH315Z"
else:
    # 5.2 (NR 4.1 / 4.8): REF3325 (2.5 V) -> R110 1.00k / R3 1.96k + C128 -> U9 TLV316 follower
    # (feedback from its output pin) -> R131 22R -> +1V65_BIAS with C48. REF1 = ideal 2.5 V source.
    # The bias voltage is computed (divider 1.6554 V minus the 22R drop of the loads), not forced.
    BIAS_VOLTAGE = None
    REF_VOLTAGE = 2.5
    BIAS_REFS = dict(kind="buffered", ref="REF1", r_top="R110", r_bot="R3", c_div="C128",
                     c_ref="C69", buf="U9", r_buf="R131", c_bias="C48")
    REF_VALUE = "REF3325"
GROUNDS = ("GND", "ISO_GND", "HT_GND")

# Frequency bands of the VHDL runs (one VUnit run per circuit and band; the Welch estimate of
# band b is used from f_lo to f_hi). fs / 20 >= f_hi, f_lo >= 10 bins of fs / nperseg.
# The four bands stitch 1 Hz .. 50 MHz without one huge fixed-step run (memory rule).
BANDS = [
    dict(name="b0", fs=1.0e9, nperseg=2 ** 14, windows=5, f_lo=625e3, f_hi=50e6),
    dict(name="b1", fs=12.5e6, nperseg=2 ** 14, windows=5, f_lo=8e3, f_hi=625e3),
    dict(name="b2", fs=160e3, nperseg=2 ** 14, windows=5, f_lo=100.0, f_hi=8e3),
    dict(name="b3", fs=2e3, nperseg=2 ** 15, windows=5, f_lo=1.0, f_hi=100.0),
]

AC_START, AC_STOP, AC_PER_DECADE = 1.0, 50e6, 50

# pass limits (PLAN section 4)
LIMITS = dict(rms_db=0.5, rms_deg=5.0, coherence=0.95, dc_gain_rel=0.005, f3db_rel=0.05,
              bias_rel=0.002)

CIRCUITS_51 = [
    dict(id="c1", title="PFC_I1_MEAS (J2-43), U4:A", group="A", out="PFC_I1_MEAS",
         input=dict(kind="I", net="PFC CURRENT 2+", dc=0.0, unit="A"),
         opamp=("U4", "A"), ref="bias",
         roles=dict(shunt="R93", in_p=["R33"], ref_p="R60", c_ref_p="C106", g=["R97"],
                    f="R98", c_f="C113", o="R96", c_o="C88"),
         extra=[], inventory=1),
    dict(id="c2", title="PFC_I2_MEAS (J2-44), U4:B", group="A", out="PFC_I2_MEAS",
         input=dict(kind="I", net="PFC CURRENT 3+", dc=0.0, unit="A"),
         opamp=("U4", "B"), ref="bias",
         roles=dict(shunt="R21", in_p=["R62"], ref_p="R100", c_ref_p="C107", g=["R94"],
                    f="R95", c_f="C112", o="R61", c_o="C77"),
         extra=[], inventory=2),
    dict(id="c3", title="DHB_I_MEAS (J2-37), U1:B", group="A", out="DHB_I_MEAS",
         input=dict(kind="I", net="DHB_CURRENT", dc=0.0, unit="A"),
         opamp=("U1", "B"), ref="bias",
         roles=dict(shunt="R83", in_p=["R104"], ref_p="R105", c_ref_p=None, g=["R101"],
                    f="R102", c_f="C63", o="R42", c_o="C26"),
         extra=[], inventory=3),
    dict(id="c4", title="HEATER_I_MEAS (J2-45), U1:A", group="A", out="HEATER_I_MEAS",
         input=dict(kind="I", net="HEATER_CURRENT", dc=0.0, unit="A"),
         opamp=("U1", "A"), ref="bias",
         roles=dict(shunt="R30", in_p=["R106"], ref_p="R103", c_ref_p=None, g=["R29"],
                    f="R89", c_f="C11", o="R35", c_o="C10"),
         extra=[], inventory=4),
    dict(id="c5", title="VAC_MEAS (J2-47), U8", group="B", out="VAC_MEAS",
         # AC2 driven, AC1 held at 0 V (one line terminal is clamped to GND by the bridge)
         input=dict(kind="V", net="AC2", dc=0.0, unit="V", hold={"AC1": 0.0}),
         opamp=("U8", ""), ref="bias",
         roles=dict(in_p=["R50", "R51", "R52"], ref_p="R80", c_ref_p=None,
                    g=["R47", "R48", "R79"], f="R49", c_f=None, o="R65", c_o=None),
         extra=[], inventory=5),
    dict(id="c6", title="DC_LINK_MEAS (J2-41), U6", group="B", out="DC_LINK_MEAS",
         input=dict(kind="V", net="DC+", dc=330.0, unit="V"),
         opamp=("U6", ""), ref="GND",
         roles=dict(in_p=["R16", "R15", "R10"], ref_p="R17", c_ref_p=None,
                    g=["R112", "R111", "R109"], f="R82", c_f=None, o="R2", c_o="C4"),
         extra=[], inventory=6),
    dict(id="c7", title="AUX_MEAS (J2-40)", group="C", out="AUX_MEAS",
         input=dict(kind="V", net="15V", dc=15.0, unit="V"),
         opamp=None, ref="GND",
         roles=dict(in_p=["R11"], ref_p="R12", c_ref_p="C61"),
         extra=[], inventory=7),
    dict(id="c8", title="420V -> AD2 Vin (ISO_GND), U3", group="B", out="Net-(AD2-Vin)",
         input=dict(kind="V", net="420V", dc=420.0, unit="V"),
         opamp=("U3", ""), ref="ISO_GND",
         roles=dict(in_p=["R23", "R34", "R39"], ref_p="R38", c_ref_p="C27",
                    g=["R118", "R119", "R120"], f="R113", c_f=None, o="R13", c_o="C5"),
         extra=["AD2"], inventory=8),
    dict(id="c9", title="6V3 -> AD1 Vin (HT_GND), U2", group="D", out="Net-(AD1-Vin)",
         input=dict(kind="V", net="6V3", dc=6.3, unit="V"),
         opamp=("U2", ""), ref="HT_GND",
         roles=dict(in_p=["R54"], ref_p="R55", c_ref_p=None, g=["R121"], f="R122",
                    c_f=None, o="R18", c_o="C7"),
         extra=["AD1"], inventory=9),
]

# 5.2 (kicad_next/CHANGES_5_2.md section 4): LMH6643 U1/U4, balanced ESL caps on DHB / HEATER
# (C122 / C123 on the + leg), VAC 12k + Cf 1 nF both legs, DC_LINK Cf 1 nF both legs, R2 100R,
# C4 removed, AUX and 5V_MEAS through TLV9062 U10 followers + 100R, J2 channel map NR 4b.
# "adc": control-card ADC input (A = PFC/DHB, dwell >= 1 us; B = the rest, dwell >= 2 us).
CIRCUITS_52 = [
    dict(id="c1", title="PFC_I1_MEAS (J2-42, ADA4), U4:A", group="A", out="PFC_I1_MEAS", adc="A",
         input=dict(kind="I", net="PFC CURRENT 2+", dc=0.0, unit="A"),
         opamp=("U4", "A"), ref="bias",
         roles=dict(shunt="R93", in_p=["R33"], ref_p="R60", c_ref_p="C106", g=["R97"],
                    f="R98", c_f="C113", o="R96", c_o="C88"), extra=[]),
    dict(id="c2", title="PFC_I2_MEAS (J2-44, ADA3), U4:B", group="A", out="PFC_I2_MEAS", adc="A",
         input=dict(kind="I", net="PFC CURRENT 3+", dc=0.0, unit="A"),
         opamp=("U4", "B"), ref="bias",
         roles=dict(shunt="R21", in_p=["R62"], ref_p="R100", c_ref_p="C107", g=["R94"],
                    f="R95", c_f="C112", o="R61", c_o="C77"), extra=[]),
    dict(id="c3", title="DHB_I_MEAS (J2-38, ADA6), U1:B", group="A", out="DHB_I_MEAS", adc="A",
         input=dict(kind="I", net="DHB_CURRENT", dc=0.0, unit="A"),
         opamp=("U1", "B"), ref="bias",
         roles=dict(shunt="R83", in_p=["R104"], ref_p="R105", c_ref_p="C122", g=["R101"],
                    f="R102", c_f="C63", o="R42", c_o="C26"), extra=[]),
    dict(id="c4", title="HEATER_I_MEAS (J2-45, ADB2), U1:A", group="A", out="HEATER_I_MEAS", adc="B",
         input=dict(kind="I", net="HEATER_CURRENT", dc=0.0, unit="A"),
         opamp=("U1", "A"), ref="bias",
         roles=dict(shunt="R30", in_p=["R106"], ref_p="R103", c_ref_p="C123", g=["R29"],
                    f="R89", c_f="C11", o="R35", c_o="C10"), extra=[]),
    dict(id="c5", title="VAC_MEAS (J2-47, ADB1), U8", group="B", out="VAC_MEAS", adc="B",
         input=dict(kind="V", net="AC2", dc=0.0, unit="V", hold={"AC1": 0.0}),
         opamp=("U8", ""), ref="bias",
         roles=dict(in_p=["R50", "R51", "R52"], ref_p="R80", c_ref_p="C126",
                    g=["R47", "R48", "R79"], f="R49", c_f="C127", o="R65", c_o=None), extra=[]),
    dict(id="c6", title="DC_LINK_MEAS (J2-41, ADB4), U6", group="B", out="DC_LINK_MEAS", adc="B",
         input=dict(kind="V", net="DC+", dc=330.0, unit="V"),
         opamp=("U6", ""), ref="GND",
         roles=dict(in_p=["R16", "R15", "R10"], ref_p="R17", c_ref_p="C130",
                    g=["R112", "R111", "R109"], f="R82", c_f="C131", o="R2", c_o=None), extra=[]),
    dict(id="c7", title="AUX_MEAS (J2-43, ADB3), U10:A", group="E", out="AUX_MEAS", adc="B",
         input=dict(kind="V", net="15V", dc=15.0, unit="V"),
         opamp=("U10", "A"), ref="GND",
         roles=dict(in_p=["R11"], ref_p="R12", c_ref_p="C61", o="R132", c_o=None), extra=[]),
    dict(id="c8", title="420V -> AD2 Vin (ISO_GND), U3", group="B", out="Net-(AD2-Vin)",
         input=dict(kind="V", net="420V", dc=420.0, unit="V"),
         opamp=("U3", ""), ref="ISO_GND",
         roles=dict(in_p=["R23", "R34", "R39"], ref_p="R38", c_ref_p="C27",
                    g=["R118", "R119", "R120"], f="R113", c_f=None, o="R13", c_o="C5"),
         extra=["AD2"]),
    dict(id="c9", title="6V3 -> AD1 Vin (HT_GND), U2", group="D", out="Net-(AD1-Vin)",
         input=dict(kind="V", net="6V3", dc=6.3, unit="V"),
         opamp=("U2", ""), ref="HT_GND",
         roles=dict(in_p=["R54"], ref_p="R55", c_ref_p=None, g=["R121"], f="R122",
                    c_f=None, o="R18", c_o="C7"), extra=["AD1"]),
    dict(id="c10", title="5V_MEAS (J2-49, ADB0), U10:B", group="E", out="5V_MEAS", adc="B",
         input=dict(kind="V", net="5V", dc=5.0, unit="V"),
         opamp=("U10", "B"), ref="GND",
         roles=dict(in_p=["R133"], ref_p="R134", c_ref_p="C132", o="R135", c_o=None), extra=[]),
]

# 5.2 golden values (kicad_next/CHANGES_5_2.md section 4 + the unchanged 5.1 parts): every
# part of CIRCUITS_52 and of the bias network must carry exactly this value in the netlist
GOLDEN_52 = {
    "R93": "4m", "R21": "4m", "R83": "4m", "R30": "4m",
    "R33": "330R", "R60": "6.8k", "C106": "20p", "R97": "330R", "R98": "6.8k", "C113": "20p",
    "R96": "100", "C88": "100p",
    "R62": "330R", "R100": "6.8k", "C107": "20p", "R94": "330R", "R95": "6.8k", "C112": "20p",
    "R61": "100", "C77": "100p",
    "R104": "330R", "R105": "15k", "C122": "12p", "R101": "330R", "R102": "15k", "C63": "12p",
    "R42": "33", "C26": "na",
    "R106": "330R", "R103": "33k", "C123": "5.6p", "R29": "330R", "R89": "33k", "C11": "5.6p",
    "R35": "33R", "C10": "na",
    "R50": "1M", "R51": "1M", "R52": "1M", "R80": "12k", "C126": "1n", "R47": "1M", "R48": "1M",
    "R79": "1M", "R49": "12k", "C127": "1n", "R65": "100R",
    "R16": "1M", "R15": "1M", "R10": "1M", "R17": "15k", "C130": "1n", "R112": "1M",
    "R111": "1M", "R109": "1M", "R82": "15k", "C131": "1n", "R2": "100R",
    "R11": "22k", "R12": "4.7k", "C61": "100n", "R132": "100R",
    "R133": "15k 0.1%", "R134": "10k 0.1%", "C132": "100n", "R135": "100R",
    "R23": "1M", "R34": "1M", "R39": "1M", "R38": "15k", "C27": "1n2", "R118": "1M",
    "R119": "1M", "R120": "1M", "R113": "15k", "R13": "1k", "C5": "1n",
    "R54": "15k", "R55": "6.8k", "R121": "15k", "R122": "6.8k", "R18": "100R", "C7": "1n",
    "R110": "1.00k", "R3": "1.96k", "C128": "100n", "C69": "100n", "R131": "22R", "C48": "100n",
    "U1": "LMH6643", "U4": "LMH6643", "U8": "TLV316IDBVR", "U6": "TLV316IDBVR",
    "U3": "TLV316IDBVR", "U2": "TLV316IDBVR", "U9": "TLV316IDBVR", "U10": "TLV9062IDGKR",
    "REF1": "REF3325AIDBZR",
}
# 5.2 parts that must be gone
REMOVED_52 = ("C4",)

CIRCUITS = CIRCUITS_51 if REV == "5.1" else CIRCUITS_52
BY_ID = {c["id"]: c for c in CIRCUITS}


def circuit_refs(c):
    """All refs of a circuit: role refs + op-amp."""
    refs = []
    for v in c["roles"].values():
        if v is None:
            continue
        refs.extend(v if isinstance(v, list) else [v])
    if c["opamp"]:
        refs.append(c["opamp"][0])
    return refs + c["extra"]


def bias_circuits():
    return [c for c in CIRCUITS if c["ref"] == "bias"]
