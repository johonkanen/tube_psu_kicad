# Measurement-circuit simulations – plan

Goal: one simulation per analog measurement circuit of tube_power_5_1. ngspice gives the
reference frequency response (`.ac`); an hVHDL_ode model of the same circuit, driven with
broadband dither, gives its response through hVHDL_ode's Welch H1 estimator
(`python/freq_response.py`); a check compares the two within set limits. The VHDL models can
then replace the generic `isolated_adc_model` in tube_power_control_fpga's closed-loop
testbenches.

## 1. Circuits (inventory 2026-11-12, values = schematic, = kicad/*.kicad_sch)

| # | Signal | Path | DC transfer | Poles from R/C | Model group |
|---|---|---|---|---|---|
| 1 | PFC_I1_MEAS (J2-43) | R93 4 mΩ → U4:A diff amp 6.8k/330, bias | Vb + 82.4 mV/A | 1.17 MHz (R98·C113), 15.9 MHz (R96·C88) | A: shunt diff amp |
| 2 | PFC_I2_MEAS (J2-44) | R21 → U4:B, same as 1 | same | same | A |
| 3 | DHB_I_MEAS (J2-37) | R83 → U1:B 15k/330, 33 Ω out, C26 not fitted | Vb + 0.182 V/A | 530 kHz | A |
| 4 | HEATER_I_MEAS (J2-45) | R30 → U1:A 33k/330, 33 Ω out, C10 not fitted | Vb + 0.4 V/A | 241 kHz | A |
| 5 | VAC_MEAS (J2-47) | AC2−AC1 → 3×1M / 15k diff amp U8 TLV316, bias | Vb + 0.005·Vac | none (op-amp + parasitic C only) | B: HV diff amp |
| 6 | DC_LINK_MEAS (J2-41) | DC+ → 3×1M / 15k U6 TLV316, R2/C4 | 0.005·Vdc | 159 kHz | B |
| 8 | AD2 Vin (isolated, ISO_GND) | 420V → 3×1M / 15k, C27 on + leg, U3 TLV316, R13/C5 | 0.005·V420 | 8.9 kHz (+ leg only), 159 kHz | B |
| 7 | AUX_MEAS (J2-40) | 15V → 22k / 4.7k, C61 | 0.176 | 41 kHz | C: divider + RC |
| 9 | AD1 Vin (isolated, HT_GND) | 6V3 → 15k / 6.8k, U2 non-inverting 1.453, R18/C7 | 0.453 | 1.59 MHz | D: divider + non-inv amp |
| (10) | IW1818 Vsense | AUX_FB → (39k‖15k) / (33k‖4.7k), C50, 1k | 0.275 | 2.4 MHz | not simulated (controller input) |
| (11) | IW1818 I_sense | R8‖R9 1.245 Ω, no filter | 1.245 V/A | none | not simulated (controller input) |

Shared: the +1V65_BIAS source (Proteus name "+1V65_BIAS") (REF1 → R110 220 / R3 470, C48 100n: 150 Ω Thevenin
resistance, about 10.6 kHz, loaded by about 2.7 kΩ of amplifier bias resistors) is part of
circuits 1–5 and is simulated with them, not as an ideal source. The bias is **1.65 V** (user,
2026-11-14: the fitted REF1 gives 1.65 V on the bias net); the REF1 source voltage in the
models is set so that the loaded bias node is 1.65 V. Scope: the 9 ADC paths (1–9). Five
generic models cover them: A (×4 parameter sets), B (×3), C (×1), D (×1), bias network.

## 2. Folder layout

```
simulation/
  PLAN.md  README.md
  hVHDL_ode/                git submodule (github.com/hVHDL/hVHDL_ode, pinned)
  circuits.py               circuit list: id, refdes set, input/output nets, sources, band, limits
  spice/
    extract.py              sub-netlist per circuit from the KiCad schematic netlist
                            (kicad-cli sch export netlist), so values never drift from kicad/
    models/                 op-amp models: macromodel (GBW, Aol, poles, Rout) + vendor models
    run_ac.py               writes <id>.cir (+ sources, op-amp model, .ac dec), runs
                            `ngspice -b`, writes out/<id>_spice.csv in test_plot format
                            (#FREQRESPONSE frequency,magnitude_db,phase_deg)
  vhdl/
    meas_models_pkg.vhd     deriv functions of models A–D + bias network (state equations)
    meas_circuit_tb.vhd     one generic testbench: model + parameter set by generic, dither +
                            step excitation, write_to .dat with freq_pair / freq_save config
  run_sim.py                VUnit (NVC): ode library from the submodule, one config per circuit,
                            post_run = compare.py
  compare.py                VHDL H1 vs ngspice .ac: RMS dB / deg error over the band, -3 dB
                            frequency, DC gain vs circuits.py; writes out/report.md + Bode PNGs
  out/                      generated (git-ignored except report.md)
```

Patterns copied from hVHDL_ode (`ngspice_ref_models/fc_5level.py`: netlist from Python,
`ngspice -b` via subprocess, `$NGSPICE`) and tube_power_control_fpga
(`simulation/pfc/filter_check.py` + VUnit post_run: the existing sim-vs-reference check).

## 3. Steps

Status 2026-11-14: steps 0–4 and 6 (run_sim.py, STATUS.md) **done**, all 9 circuits pass
(simulation/README.md, out/report.md); step 5 open; the parameter export of step 6 open.

0. **[done]** **Prerequisite:** ngspice (`sudo apt install ngspice`, Ubuntu 22.04 gives ngspice 36).
   PySpice is not needed. Installed: ngspice 47 (built from source, ~/.local/bin).
1. **[done]** **Netlist extraction + golden check.** `spice/extract.py` cuts each circuit out of the
   KiCad netlist by refdes set; a test compares it with the hand inventory (`simulation/INVENTORY.md`) so a schematic change shows up.
2. **[done]** **ngspice references.** Op-amps as a macromodel first (TLV316: 10 MHz GBW, rail-to-rail;
   LMH6658 / OPA2353: datasheet GBW and output resistance), 0.2 pF per 1 MΩ resistor for
   group B. `.ac dec 50 1 Hz – 50 MHz`, input = shunt current / line or rail voltage,
   output = J2 / ADC Vin node. DC operating point checked against the transfer column above
   and `tube_power_control_fpga/docs/TUBE_POWER_J2_MEASUREMENTS.md`.
3. **[done]** **VHDL models.** Nodal state equations per group (one state per capacitor; op-amp as the
   same single- or two-pole macromodel, so both simulators model the same circuit).
   `generic_trbdf2` for the stiff ones (15.9 MHz output RC next to a 10 kHz bias pole),
   rk4/vern7 elsewhere. Step ≤ 1/(20·fastest pole); run length ≥ 5 Welch windows of the
   lowest frequency of interest; dither + one step, `freq_deskew=zoh`.
   *As built:* one parameterised topology for groups A–D; trbdf2 in all bands; four bands
   (1 GS/s … 2 kS/s) instead of one run; first-order-hold dither (no deskew; the
   zero-order hold is wrong for circuits fast compared with fs) and the DC gain from two
   DC operating points instead of a step (README "How the comparison works").
4. **[done]** **Comparison.** `compare.py` from the VUnit post_run; pass limits per circuit (start:
   ≤ 0.5 dB / 5° RMS over the band where coherence > 0.95, DC gain ≤ 0.5 %, -3 dB frequency
   ≤ 5 %). Report + overlay plots with `test_plot.py`.
5. **[open]** **Vendor op-amp models (optional).** Rerun ngspice with TI's TLV316 / OPA2353 models to
   show where the macromodel stops being valid (only the SPICE side; the VHDL keeps the
   macromodel).
6. **[done, except the parameter export]** **Hook-up.** `simulation/run_sim.py` runs separately (not part of tools/check_all.sh);
   STATUS.md section; later a parameter export (gain, poles) for tube_power_control_fpga's
   `isolated_adc_model`.

## 4. Decisions (user, 2026-11-14)

1. Bias: +1V65_BIAS = 1.65 V (fitted REF1; the schematic value ISL21010CFH315Z is a 1.5 V part,
   so the fitted part differs from the schematic value – noted, schematic not changed).
2. Scope: the ADC paths 1–9; the IW1818 inputs 10/11 are not simulated.
3. Op-amps: the same simple macromodel in ngspice and VHDL (vendor models optional, step 5).
4. Band and limits as proposed: `.ac` 1 Hz – 50 MHz, compared where coherence > 0.95;
   ≤ 0.5 dB / 5° RMS, DC gain ≤ 0.5 %, -3 dB frequency ≤ 5 %.
5. Run separately (`simulation/run_sim.py`), not from tools/check_all.sh.
6. Location: `simulation/` in tube_psu_kicad.

## 5. Design findings from the inventory (to check, not simulation work)

- +1V65_BIAS (Proteus name +2V5_BIAS, renamed 2026-11-16) is 1.65 V (fitted REF1), and the schematic value of REF1
  (ISL21010CFH315Z, 1.5 V) does not match the fitted part; the net is loaded ≈ 5 % by the
  amplifier bias resistors (the PDF note already asks for buffering).
- U1 (LMH6658, circuits 3/4) has no local decoupling capacitor.
- Circuit 8 has C27 on the + leg only, so the two divider legs are unbalanced above ≈ 9 kHz.
- Circuit 9: amp and ADC are supplied from the rail they measure (via D2/D3 + V3).
- IW1818 Vsense (10, not simulated): divider ratio 0.275 vs the PDF note's 0.263 (R64 / R84
  are stale-value parts).
- Circuits 3/4: no output filter (C10 / C26 not fitted); the 33 Ω drives the J2 line directly.
