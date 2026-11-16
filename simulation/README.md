# Measurement-circuit simulations

The 9 ADC measurement paths of tube_power_5_1, simulated twice and compared:

- **ngspice** `.ac` 1 Hz – 50 MHz: the reference (`spice/run_ac.py`), netlists cut out of
  the KiCad schematic.
- **hVHDL_ode** (`hVHDL_ode/`, submodule): a VHDL state-space model of the same circuit
  (`vhdl/meas_models_pkg.vhd`), driven with broadband dither in NVC, its response
  estimated with hVHDL_ode's Welch H1 (`python/freq_response.py`).

Plan and decisions: [PLAN.md](PLAN.md); parts, values, pin lists: [INVENTORY.md](INVENTORY.md);
latest result: [out/report.md](out/report.md) and `out/<id>_bode.png`.

## Running

```
git submodule update --init simulation/hVHDL_ode
python3 simulation/run_sim.py                   # all: 9 circuits x 4 bands, ~75 s
python3 simulation/run_sim.py '*c5*'            # one circuit (VUnit pattern)
python3 simulation/run_sim.py --no-spice ...    # reuse out/spice
python3 simulation/spice/extract.py --check     # golden check only
python3 simulation/spice/run_ac.py [c1 ...]     # ngspice only
python3 simulation/compare.py --analytic-selftest
python3 simulation/hVHDL_ode/python/test_plot.py --freq-only out/spice/c1_spice.csv out/c1_vhdl.csv
```

Not part of `tools/check_all.sh` (user decision). Needs ngspice (`$NGSPICE`, `--ngspice`
in run_ac.py, or PATH; tested with ngspice 47), NVC (VUnit simulator, set by run_sim.py),
VUnit, numpy, scipy, pandas, matplotlib, and `tools/p2k/bin/kicad-cli` for the netlist export.

run_sim.py: golden check → `gen_params.py` (writes `vhdl/meas_params_pkg.vhd`) →
compare.py self-test → ngspice → VUnit with **`-p 1` forced** (one simulation at a time;
any `-p` given is replaced) → `compare.py` as post_run. Exit status 1 on any failure.

Resources (2026-11-14, full run): 72 s wall, of which 62 s NVC (36 runs of 1.4–3 s);
peak RSS 250 MB; `out/vunit_out` 323 MB (each `meas.dat` 7.5 MB, band 3 15 MB).

## Files

| file | what |
|---|---|
| `circuits.py` | circuit list: refdes by role, input/output nets, op-amp macromodels, bands, limits |
| `spice/extract.py` | `kicad-cli sch export netlist` → values / pins; topology check of the roles; golden check vs INVENTORY.md |
| `spice/run_ac.py` | `out/spice/<id>.cir`, `ngspice -b`, `<id>_spice.csv` (test_plot `#FREQRESPONSE` format), `<id>_op.json` |
| `gen_params.py` | `vhdl/meas_params_pkg.vhd` (generated, committed; `--check`) |
| `vhdl/meas_models_pkg.vhd` | the model: one parameterised topology, derivative, output, initial state |
| `vhdl/meas_circuit_tb.vhd` | one testbench, generics `g_circuit`, `g_band` |
| `compare.py` | Welch H1 per band, stitching, checks, `out/report.md`, Bode PNGs, `out/<id>_vhdl.csv` |
| `run_sim.py` | the whole flow |

## How the models are built

**Values** all come from the schematic: the KiCad netlist is exported and every R/C is
looked up by reference. `circuits.py` only says which reference plays which role. Two
checks guard this: the golden check compares the parts, values and pin → net lists of
circuits 1–9 and the bias network with INVENTORY.md (73 R/C, 26 IC pins, 36 unnamed nets
mapped one-to-one), and the topology check confirms each role sits between the right
nets (e.g. the + leg chain runs from the input net to the op-amp + pin).

**One topology** covers all four groups of PLAN.md (see the header of
`vhdl/meas_models_pkg.vhd`): a + leg (input → 1–3 series sections, optionally with a parasitic C
across each → NP → R ‖ C to the reference), a − leg (ground → 1–3 sections → NN → R ‖ C
→ VO), the op-amp, and an output R + C. The reference is either ground or the
+1V65_BIAS node. Group A (shunt diff amps, circuits 1–4), B (HV diff amps 5, 6, 8),
C (divider 7) and D (non-inverting 9) are parameter sets of it. One state per capacitor;
the nodes without a capacitor are solved algebraically inside the derivative.

**Op-amp macromodel** (same in both simulators): A0 at DC, one pole at GBW/A0, unity
buffer, open-loop output resistance; no rails, no input capacitance.
TLV316: GBW 10 MHz, Zo 250 Ω (datasheet SBOS752), A0 100 dB (assumed).
LMH6658: GBW 140 MHz, A_VOL 95 dB (datasheet SNOSA35), Rout 10 Ω (assumed, not specified).
The real parts are not checked against this model (vendor models: PLAN step 5, not done).

**Bias network**: REF1 is an ideal source at its VOUT net, set to 2.5589 V so the loaded
+1V65_BIAS node is 1.65 V (user decision). ngspice simulates circuits 1–5 together with
the whole bias network (only the circuit under test driven). The VHDL model of each of
those circuits has the bias node as a state, its own + leg exactly, and the + legs of the
four others as one DC resistance (their 20 pF caps and the 1M parasitics dropped). The
comparison shows the effect is below 0.03 dB.

**Group B parasitics**: 0.2 pF across each 1 MΩ resistor (PLAN step 2; not in the
schematic). In circuit 8 these caps and C27 form a capacitor-only loop with the source.
The model takes du/dt there, and du/dt is finite because the input is a first-order hold.

**Neglected (both simulators)**: the ADC input (AD1/AD2) and J2 line loads; the 4 mΩ
shunt's loading by the 330 Ω input (VHDL only, 1.2e-5); the isolated grounds are node 0
of their own circuit; circuit 5 has AC1 held at 0 V and AC2 driven (one line terminal is
clamped to GND by the bridge in each half cycle).

## How the comparison works

- **Bands.** 1 Hz – 50 MHz in one fixed-step run would need 5·10^9 steps, so each circuit
  runs four times (memory rule). Each run is 5 Welch windows long:

  | band | fs | nperseg | used from – to |
  |---|---|---|---|
  | 0 | 1 GS/s | 16384 | 625 kHz – 50 MHz |
  | 1 | 12.5 MS/s | 16384 | 8 kHz – 625 kHz |
  | 2 | 160 kS/s | 16384 | 100 Hz – 8 kHz |
  | 3 | 2 kS/s | 32768 | 1 Hz – 100 Hz |

  Each band is used up to fs/20 and down to 10 bins above 0 Hz. The solver is `generic_trbdf2`
  (L-stable) in every band, because the op-amp loops reach 140 MHz while band 3 steps at 0.5 ms.
- **Excitation.** Uniform dither, ±(0.1 V at the output / ideal gain), one value per
  sample, joined by straight lines (first-order hold). PLAN.md proposed a
  zero-order hold with `freq_deskew=zoh`, but that is only correct when the circuit is
  slow compared with fs. In bands 2–3 most circuits settle within one step, so a
  zero-order hold would show a full one-sample delay instead of a half-sample one. With a
  first-order hold and y sampled at the sample instants, the Welch estimate is
  H_d(f) = Σk H(f + k·fs)·sinc²((f + k·fs)/fs) whether the circuit is fast or slow.
  compare.py builds this H_d from the ngspice response (k = ±3; above 50 MHz taken as 0)
  and compares against it. The k = 0 factor alone is within 0.07 dB at fs/20. For the
  −3 dB frequency, the plots and `out/<id>_vhdl.csv`, the VHDL estimate is divided by
  sinc²(f/fs). The DC level is subtracted before writing (`write_to` prints 7 significant
  digits). No step is applied: the DC gain comes from two DC operating points (u0,
  u0 + u_amp) solved with long TR-BDF2 steps.
- **Checks** (PLAN section 4): RMS dB and RMS deg of H_vhdl / H_ref over all bins with
  coherence > 0.95 (≤ 0.5 dB / 5°); DC gain VHDL vs ngspice ≤ 0.5 %; −3 dB frequency
  VHDL vs ngspice ≤ 5 % (both "none" also passes); bias node 1.65 V ± 0.2 % in both.
  The ngspice DC gain vs the ideal transfer of the schematic values is reported but not
  checked, because it is a property of the design (see findings).
- **Self-test** (`compare.py --analytic-selftest`, part of run_sim.py): circuit 7's
  analytic H(s) from the schematic values, simulated as its exact first-order-hold
  discretisation (scipy), must pass. A pole moved 8 % must fail on −3 dB, and a gain
  1 dB high must fail on RMS and DC gain.
- **Resolution limit.** The VHDL −3 dB frequency is interpolated between Welch bins
  (763 Hz apart in band 1, 61 kHz in band 0). That accounts for the 0.3–1.0 % differences
  in the report. Limit: 5 %.

## Result (2026-11-14)

All 9 pass. Errors are 0.007–0.028 dB / 0.03–0.19° RMS, DC gains are identical, and
the −3 dB frequencies agree within 1.0 %. See [out/report.md](out/report.md).

## Design findings (documented, schematic not changed)

The findings with recommended fixes and what-if simulations are in [FINDINGS.md](FINDINGS.md).

1. **VAC_MEAS couples into the bias and the current channels.** The +1V65_BIAS source has
   a Thevenin resistance of 142 Ω (R110 ‖ R3 ‖ loads). Circuit 5's + leg (3 MΩ from AC2)
   feeds the line voltage into it, so the bias moves by 4.7·10⁻⁵ × V(AC2), ±15 mV at
   325 V peak. Every bias-referenced output carries this 1:1 (ngspice, 1 Hz): about
   0.19 A equivalent on PFC_I1/I2_MEAS (82.5 mV/A), 84 mA on DHB_I_MEAS and 38 mA on
   HEATER_I_MEAS, at line frequency. The same effect makes circuit 5's own DC gain
   0.94 % above the ideal 0.005. This supports the PDF note asking for a bias buffer.
2. **VAC_MEAS has no filter, and its response rises at HF.** With 0.2 pF per 1 MΩ, the
   gain rises from about 300 kHz and is 22 dB above the DC gain (−24 dB instead of
   −46 dB) at 20–50 MHz. R65 drives J2-47 with no capacitor, so differential line noise
   in the MHz range reaches the MCU ADC 12× stronger than the signal. Options: a capacitor
   on VAC_MEAS (as C4 on DC_LINK_MEAS), or capacitors across R80 and R49 that match the
   chain's time constant. The size depends on the real parasitics (0.2 pF is an assumption).
3. **DC_LINK_MEAS output filter is limited by the same feedthrough.** Above 1 MHz the
   response stays at −58 to −64 dB, only 12–18 dB below the DC gain, instead of falling
   20 dB/decade from R2/C4 (159 kHz).
4. **Circuit 8 (AD2, 420 V)**: −3 dB at 8.86 kHz, set by C27 on the + leg only (−6.8° at
   1 kHz). It is a single-ended measurement, so the leg imbalance only matters for the
   bandwidth and phase; use this figure in the control model.
5. **Circuit 4 (HEATER_I_MEAS)**: the gain is 0.18 % low from the LMH6658's finite open-loop
   gain at a noise gain of 101 (95 dB assumed). Circuits 3/4 have no output capacitor
   (C26/C10 not fitted). Their bandwidth (453 kHz / 206 kHz) comes from the feedback
   capacitors only.
6. As noted in PLAN.md: the REF1 schematic value (ISL21010CFH315Z, 1.5 V) does not match
   the fitted 1.65 V bias. U1 has no local decoupling capacitor.
7. `kicad-cli sch export netlist` warns "schematic has annotation errors". This was not
   investigated here: the netlist used matches INVENTORY.md and the existing ERC /
   netlist checks are in tools/check_all.sh.

## Auxiliary flyback (TR1) cross regulation – in progress

`flyback/`: OpenMagnetics (PyOpenMagnetics) models of the EF20 flyback transformer TR1
(current V2 build and rewind options) and an ngspice transient model of the IW1818
flyback with the full coupled-inductor matrix; findings in
[flyback/FLYBACK_DESIGN.md](flyback/FLYBACK_DESIGN.md), status in [flyback/NEXT.md](flyback/NEXT.md).
