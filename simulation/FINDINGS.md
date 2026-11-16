# Measurement circuits – simulation findings and recommended fixes

Board tube_power_5_1 (KiCad migration), the 9 analog paths that feed an ADC.
Source: the ngspice references and hVHDL_ode models of `simulation/` (run_sim.py, all 9
pass, see [README.md](README.md) and [out/report.md](out/report.md)), and what-if ngspice runs
of the fixes below (`python3 simulation/spice/whatif_fixes.py`, after run_sim.py).
Status 2026-11-16. The schematic is **not** changed; these are recommendations for the next
board revision.

Model limits: the op-amps are a single-pole macromodel (TLV316 10 MHz GBW, 250 Ω out;
LMH6658 140 MHz GBW, 10 Ω out; open-loop gains and the LMH6658 output resistance assumed),
and each 1 MΩ resistor has an assumed 0.2 pF in parallel. The macromodel does **not** show
op-amp stability with capacitive loads: check every fix that puts a capacitor on an op-amp
output with the vendor model (PLAN.md step 5) or on the bench. The bias is 1.65 V (fitted
REF1). The line voltage is modelled differentially (AC1 at ground).

## Summary

| # | Finding | Effect | Recommended fix | Priority |
|---|---|---|---|---|
| 1 | VAC divider feeds the line into the shared bias (142 Ω source) | ±15 mV line-frequency ripple on every current channel (≈ 0.19 A on PFC_I1/I2); VAC gain +0.94 %; bias loaded ≈ 5 % | Buffer the bias: follower + 22 Ω + C48 at the output | High |
| 2 | VAC_MEAS has no filter; 1 MΩ parasitics make it rise at HF | 22 dB above DC gain at 20–50 MHz: line noise reaches the ADC 12× stronger than the signal | 1 nF C0G across R80 and across R49; R65 1 k + 1 nF to GND | High |
| 3 | DC_LINK_MEAS output RC is bypassed by the same feedthrough | flattens at −58…−64 dB above 1 MHz (only 12–18 dB below DC gain) | 1 nF C0G across R17 and across R82 (or smaller for more bandwidth) | Medium |
| 4 | DHB_I / HEATER_I drive J2 through 33 Ω with no capacitor (C26 / C10 not fitted) | no anti-alias / charge reservoir for the MCU ADC sample-and-hold | Fit C26 / C10 (≈ 1 nF C0G) after checking LMH6658 stability with 33 Ω + C | Medium |
| 5 | AD2 (420 V) bandwidth 8.86 kHz, from C27 on the + leg only | −6.8° at 1 kHz; legs unbalanced | No hardware change; use 8.86 kHz in the control model | Info |
| 6 | HEATER_I_MEAS gain 0.18 % low (LMH6658 finite gain at noise gain 101) | small gain error | Calibrate in firmware | Low |
| 7 | U1 (LMH6658, DHB_I / HEATER_I) has no local decoupling | supply noise / possible oscillation | 100 nF (+ 1 µF) at U1 pin 8 | Medium |
| 8 | REF1 schematic value ISL21010CFH315Z (1.5 V) ≠ fitted part (bias 1.65 V); net named +2V5_BIAS | documentation | Correct the value; rename the net (e.g. +1V65_BIAS) | Low |

## 1. The AC line couples into the bias and every current channel

**Finding.** The "+2V5_BIAS" node (REF1 → R110 220 Ω / R3 470 Ω, C48 100 nF) has a source
resistance of ≈ 142 Ω with its loads. VAC_MEAS's + leg (R50–R52, 3 MΩ from AC2, R80 15 kΩ)
returns to this node, so the line voltage is injected into the bias with 4.7·10⁻⁵ V/V
(C48 is only 32 kΩ at 50 Hz, it does not help). All four current amplifiers are referenced
to the bias and pass it 1:1 to their outputs.

| Output | Coupling from AC2 at 50 Hz | At 325 V peak | Equivalent current |
|---|---|---|---|
| PFC_I1_MEAS / PFC_I2_MEAS | 4.70·10⁻⁵ | ±15.3 mV | ±0.19 A (82.5 mV/A) |
| DHB_I_MEAS | 4.70·10⁻⁵ | ±15.3 mV | ±84 mA (0.182 V/A) |
| HEATER_I_MEAS | 4.70·10⁻⁵ | ±15.3 mV | ±38 mA (0.40 V/A) |
| VAC_MEAS (own gain) | 5.047·10⁻³ | – | +0.94 % gain error |

Besides the line ripple, the amplifier bias resistors (R60, R100, R103, R105, R80, ≈ 2.7 kΩ
in total) load the divider ≈ 5 %, so the bias depends on the resistor tolerances of the
loads. The PDF note on the sheet already asks for "more capacitance to bias voltage /
buffer ref output".

**Fix.** Buffer the bias with a unity-gain follower (a TLV316-class rail-to-rail op-amp in
SOT-23-5, supplied from +3V3). Keep the REF1 divider unloaded (add 100 nF on the divider
node), drive +2V5_BIAS from the follower output through ≈ 22 Ω, keep C48 on the bias node
after the 22 Ω and take the follower feedback from the bias node (or from the op-amp output
if the stability check prefers it). The 22 Ω isolates the 100 nF from the op-amp output.

| Variant (what-if ngspice) | Coupling AC2 → current channels, 50 Hz | VAC gain error | Bias at 1 MHz from AC2 |
|---|---|---|---|
| As built | 4.70·10⁻⁵ | +0.94 % | 8.5·10⁻⁷ |
| Follower, C48 moved to the divider | 9.3·10⁻¹⁰ | 0.00 % | – (VAC HF worse, see 2) |
| **Follower + 22 Ω + C48 at the output** | **1.0·10⁻⁹** (−93 dB vs as built) | **0.00 %** | 9.1·10⁻⁷ |

The ripple drops from ±15 mV to ≈ 0.3 µV. Keeping C48 at the output matters: with C48 moved
to the divider the VAC high-frequency feedthrough becomes 20–30 dB worse at 10–50 MHz, because
the follower's output impedance rises with frequency.

Alternative without an extra op-amp: give VAC_MEAS its own bias divider (from +3V3 or REF1)
so the line no longer reaches the shared bias. This fixes the current channels but not the
load-dependent bias error.

## 2. VAC_MEAS: no filter, gain rises at high frequency

**Finding.** The 3 × 1 MΩ chains have only their parasitic capacitance across them (0.2 pF
each assumed). Above ≈ 300 kHz this capacitive divider takes over and the gain rises from
−46 dB (0.005) to −24 dB at 20–50 MHz, 22 dB above the DC gain. There is no capacitor in the
signal path and none on the output (R65 100 Ω drives J2-47 directly), so differential noise
on the line in the MHz range reaches the MCU ADC amplified relative to the 50 Hz signal.

**Fix.** Make the difference amplifier a low-pass: 1 nF C0G across R80 and across R49
(matched, 1–2 %, so the common-mode rejection holds), pole at 1/(2π·15 kΩ·1 nF) = 10.6 kHz.
Add an output RC like DC_LINK_MEAS: R65 1 kΩ + 1 nF C0G to GND (159 kHz).

| Variant | 50 Hz | 10 kHz | 100 kHz | 1 MHz | 10 MHz | 20 MHz | 50 MHz | −3 dB | Phase 50 Hz |
|---|---|---|---|---|---|---|---|---|---|
| As built | −45.9 | −46.0 | −46.0 | −42.0 | −26.8 | −24.6 | −24.1 | none | 0.00° |
| 1 nF across R80 + R49 | −45.9 | −48.8 | −65.3 | −81.3 | −86.3 | −90.3 | −97.5 | 10.7 kHz | −0.27° |
| **+ R65 1 k / 1 nF out** | −45.9 | −48.8 | −66.6 | −97.3 | −123.4 | −133.9 | −149.4 | 10.7 kHz | −0.29° |
| + bias follower (fix 1, 22 Ω + C48 at output) | −46.0 | −48.9 | −66.7 | −97.3 | −123.4 | −133.9 | −149.4 | 10.7 kHz | −0.29° |

(dB of VAC_MEAS / V(AC2).) At 20 MHz the fixed circuit is 109 dB lower than as built. The
−0.29° at 50 Hz is a fixed phase lag that the PLL / firmware can compensate. The size of the
capacitors depends on the real resistor parasitics (assumed 0.2 pF) and on the bandwidth the
control needs; fc = 1/(2π·15 kΩ·C).

## 3. DC_LINK_MEAS: the output filter stops working above 1 MHz

**Finding.** Same divider structure as VAC_MEAS (to DC+ and GND) with an output RC
(R2 1 kΩ / C4 1 nF, 159 kHz). The parasitic feedthrough of the 1 MΩ chains bypasses the
amplifier's attenuation: above 1 MHz the response stays at −58 to −64 dB instead of falling
20 dB/decade.

**Fix.** 1 nF C0G across R17 and across R82 (matched), as in fix 2.

| Variant | 50 Hz | 10 kHz | 100 kHz | 1 MHz | 10 MHz | 20 MHz | 50 MHz | −3 dB |
|---|---|---|---|---|---|---|---|---|
| As built | −46.0 | −46.0 | −47.3 | −58.0 | −63.8 | −68.2 | −76.1 | 171 kHz |
| **1 nF across R17 + R82** | −46.0 | −48.9 | −66.7 | −97.4 | −123.4 | −134.0 | −149.5 | 10.7 kHz |

If the DC-link control needs more than ≈ 10 kHz, use a smaller capacitor
(220 pF → 48 kHz, 470 pF → 23 kHz); any value restores the roll-off above 1 MHz.

## 4. DHB_I_MEAS and HEATER_I_MEAS have no output capacitor

**Finding.** C26 and C10 (footprints exist) are "na". The LMH6658 outputs drive the J2 lines
and the MCU ADC sampling capacitor through 33 Ω only. The bandwidth (453 kHz / 206 kHz) comes
from the 20 pF feedback capacitors alone.

**Fix.** Fit C26 / C10, ≈ 1 nF C0G (33 Ω · 1 nF = 4.8 MHz, so the response is unchanged
below 1 MHz; it gives the MCU ADC a charge reservoir and some anti-aliasing). The value
depends on the MCU ADC sample time and input capacitance. Check the LMH6658's phase margin
with 33 Ω + 1 nF on the vendor model or the bench before fitting (not shown by the
macromodel). The PFC channels already have this (R96/R61 100 Ω, C88/C77 100 pF).

## 5. AD2 (420 V, isolated) bandwidth is 8.86 kHz

**Finding.** C27 (1.2 nF) sits across the + leg only (R38 15 kΩ ‖ 3 MΩ), giving a 8.86 kHz
pole (−6.8° at 1 kHz); the − leg has no capacitor. A matching 1.2 nF across R113 was
simulated: it changes the 420V → AD2 response by < 0.5 dB up to 50 MHz, because the − leg
input is ISO_GND (no common-mode signal in this circuit). **No change recommended**; use the
8.86 kHz pole and the 159 kHz R13/C5 pole in the control model (tube_power_control_fpga's
`isolated_adc_model`).

## 6. HEATER_I_MEAS gain 0.18 % low

At a noise gain of 101 the LMH6658's finite open-loop gain (95 dB assumed) costs 0.18 %.
Below the resistor tolerances; calibrate in firmware (offset at zero current, gain at a
known current).

## 7. U1 has no local decoupling

U1 (LMH6658, a 140 MHz part driving circuits 3 and 4) has no capacitor at its supply pin;
U4, the identical PFC-channel amplifier, has C87 1 µF. Add 100 nF (and 1 µF) next to U1 pin 8.
Not simulated (the macromodel has no supply pin).

## 8. Documentation

- REF1: the schematic value ISL21010CFH315Z-TK is the 1.5 V version (bias would be ≈ 1.02 V);
  the fitted part gives 1.65 V on the bias net. Correct the value to the fitted part.
- The net is named +2V5_BIAS but is 1.65 V; rename it (e.g. +1V65_BIAS) in the next revision.
- `kicad-cli sch export netlist` warns "schematic has annotation errors" – to be
  investigated (the netlist itself matches the inventory and the IPC netlist).

## Next steps

1. Re-run fixes 1, 2 and 4 with the TI vendor models (TLV316, LMH6658) for stability and
   output-swing checks (PLAN.md step 5).
2. Decide the bandwidths for VAC_MEAS and DC_LINK_MEAS with the control design, then size
   the capacitors (fc = 1/(2π·15 kΩ·C)).
3. Measure one board: line ripple on PFC_I1_MEAS at zero current (expected ±15 mV as built)
   and the VAC_MEAS response with a network analyser, to replace the assumed 0.2 pF.
4. Put the chosen fixes into the schematic of the next revision; extend circuits.py /
   whatif_fixes.py so run_sim.py checks the new circuit.
