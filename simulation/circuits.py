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

Roles map to reference designators. A role may list several refs (series sections).
"""

# op-amp macromodel: same in ngspice (spice/run_ac.py) and VHDL (vhdl/meas_params_pkg.vhd)
# a0 = DC open-loop gain, gbw = unity-gain frequency [Hz], rout = open-loop output resistance
OPAMPS = {
    # TLV316 (SBOS752): 10 MHz GBW, Zo 250 ohm @ 10 MHz; A0 100 dB assumed (rail-to-rail CMOS)
    "TLV316IDBVR": dict(a0=1.0e5, gbw=10.0e6, rout=250.0,
                        pins={"": ("3", "4", "1")}),
    # LMH6658 (SNOSA35): 140 MHz GBW, A_VOL 95 dB typ; Rout 10 ohm assumed (not specified)
    "LMH6658": dict(a0=10 ** (95 / 20), gbw=140.0e6, rout=10.0,
                    pins={"A": ("3", "2", "1"), "B": ("5", "6", "7")}),
}

# parasitic capacitance added across every 1 Mohm resistor of the group-B chains (PLAN step 2)
C_PAR_PER_MOHM = 0.2e-12

BIAS_NET = "+1V65_BIAS"
BIAS_VOLTAGE = 1.65            # user decision 2026-11-14: loaded bias node = 1.65 V
BIAS_REFS = dict(ref="REF1", r_top="R110", r_bot="R3", c_bias="C48", c_ref="C69")
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

CIRCUITS = [
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
