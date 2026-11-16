# Measurement circuits – simulation findings and recommended fixes

Board tube_power_5_1 (KiCad migration), the 9 analog paths that feed an ADC.
Source: the ngspice references and hVHDL_ode models of `simulation/` (run_sim.py, all 9
pass, see [README.md](README.md) and [out/report.md](out/report.md)), and what-if ngspice runs
of the fixes below (`python3 simulation/spice/whatif_fixes.py`, after run_sim.py), and
transient simulations of the control card's ADC mux switching
(`python3 simulation/spice/mux_settling.py`, section 9).
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
| 2 | VAC_MEAS has no filter; 1 MΩ parasitics make it rise at HF | 22 dB above DC gain at 20–50 MHz: line noise reaches the ADC 12× stronger than the signal 1 nF C0G across R80 and across R49; keep R65 100 Ω, **no** output capacitor (mux, section 9) | High |
| 3 | DC_LINK_MEAS output RC is bypassed by the same feedthrough | flattens at −58…−64 dB above 1 MHz (only 12–18 dB below DC gain) 1 nF C0G across R17 and across R82; R2 1 k → 100 Ω and remove C4 (mux, section 9) | High |
| 4 | DHB_I / HEATER_I drive J2 through 33 Ω with no capacitor (C26 / C10 not fitted) | none: the control card buffers the mux output (OPA365), so no charge reservoir is needed | Leave C26 / C10 unfitted (fitting 1 nF makes the mux settling slightly worse) | Info |
| 5 | AD2 (420 V) bandwidth 8.86 kHz, from C27 on the + leg only | −6.8° at 1 kHz; legs unbalanced | No hardware change; use 8.86 kHz in the control model | Info |
| 6 | HEATER_I_MEAS gain 0.18 % low (LMH6658 finite gain at noise gain 101) | small gain error | Calibrate in firmware | Low |
| 7 | U1 (LMH6658, DHB_I / HEATER_I) has no local decoupling | supply noise / possible oscillation | 100 nF (+ 1 µF) at U1 pin 8 | Medium |
| 8 | REF1 schematic value ISL21010CFH315Z (1.5 V) ≠ fitted part (bias 1.65 V) | documentation | Correct the value (the nets are already renamed to +1V65_BIAS / 15V / 15V_ISO_SEC, 2026-11-16) | Low |
| 9 | ADC mux channel leakage: DC_LINK_MEAS (1 k + 1 nF) and AUX_MEAS (3.9 kΩ + 1 nF) recharge the mux node slowly | 254 / 505 LSB of the previous channel left after 1 µs; ≈ 10 µs / > 20 µs to settle | DC_LINK: fix 3; AUX_MEAS: C61 1 nF → 1 µF (0.7 LSB, any dwell) | High |
| 10 | VAC_MEAS range: 1.65 V ± 0.005·Vline uses the whole 0–3.3 V at 325 V peak | clips above ≈ 330 V peak (230 V + 1.5 %) | R49 and R80 15 k → 12 k (gain 0.004: ±1.49 V at 264 V rms) | High |

## 1. The AC line couples into the bias and every current channel

**Finding.** The +1V65_BIAS node (named "+2V5_BIAS" in Proteus) (REF1 → R110 220 Ω / R3 470 Ω, C48 100 nF) has a source
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
node), drive +1V65_BIAS from the follower output through ≈ 22 Ω, keep C48 on the bias node
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
Keep R65 100 Ω with **no** capacitor on VAC_MEAS: an output RC (1 kΩ + 1 nF) would filter a
little more above 1 MHz, but it makes the ADC mux leak 254 LSB of the previous channel into
VAC after 1 µs (section 9); the feedback capacitors alone already give −81 dB at 1 MHz.

| Variant | 50 Hz | 10 kHz | 100 kHz | 1 MHz | 10 MHz | 20 MHz | 50 MHz | −3 dB | Phase 50 Hz |
|---|---|---|---|---|---|---|---|---|---|
| As built | −45.9 | −46.0 | −46.0 | −42.0 | −26.8 | −24.6 | −24.1 | none | 0.00° |
| **1 nF across R80 + R49 (recommended)** | −45.9 | −48.8 | −65.3 | −81.3 | −86.3 | −90.3 | −97.5 | 10.7 kHz | −0.27° |
| + R65 1 k / 1 nF out (rejected: mux leakage, section 9) | −45.9 | −48.8 | −66.6 | −97.3 | −123.4 | −133.9 | −149.4 | 10.7 kHz | −0.29° |
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

**Fix.** 1 nF C0G across R17 and across R82 (matched), as in fix 2, **and** R2 1 kΩ → 100 Ω
with C4 removed: the filtering then happens inside the amplifier and the output is low
impedance for the ADC mux (section 9: the as-built 1 kΩ + 1 nF leaves 254 LSB of the previous
channel after 1 µs).

| Variant | 50 Hz | 10 kHz | 100 kHz | 1 MHz | 10 MHz | 20 MHz | 50 MHz | −3 dB |
|---|---|---|---|---|---|---|---|---|
| As built | −46.0 | −46.0 | −47.3 | −58.0 | −63.8 | −68.2 | −76.1 | 171 kHz |
| 1 nF across R17 + R82 (R2/C4 kept) | −46.0 | −48.9 | −66.7 | −97.4 | −123.4 | −134.0 | −149.5 | 10.7 kHz |
| **1 nF across R17 + R82, R2 100 Ω, C4 removed (recommended)** | −46.0 | −48.9 | −65.3 | −81.4 | −86.5 | −90.4 | −97.7 | 10.7 kHz |

If the DC-link control needs more than ≈ 10 kHz, use a smaller capacitor
(220 pF → 48 kHz, 470 pF → 23 kHz); any value restores the roll-off above 1 MHz.

## 4. DHB_I_MEAS and HEATER_I_MEAS have no output capacitor

**Finding.** C26 and C10 (footprints exist) are "na". The LMH6658 outputs drive the J2 lines
through 33 Ω only; the bandwidth (453 kHz / 206 kHz) comes from the 20 pF feedback capacitors.

**Recommendation: leave them unfitted.** The control card puts an OPA365 follower between
the TMUX1308 and the ADS7056 (33 Ω + 680 pF at the ADC pin), so the power-board outputs only
have to recharge the mux node (≈ 45 pF), not an ADC sampling capacitor. As built, DHB_I and
HEATER_I leave < 1 LSB after 0.4 µs; with C26 = 1 nF fitted the 0.2 µs value gets worse
(1.6 → 6.1 LSB, section 9) and the LMH6658 would drive a capacitive load. Fit them only if
anti-aliasing at the 33 Ω output is wanted, and then check the LMH6658 phase margin first.

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
- Net names: Proteus called the 1.65 V bias "+2V5_BIAS" and the 15 V flyback rails "20V" /
  "20V_ISO_SEC". They are renamed in the KiCad design to +1V65_BIAS, 15V and 15V_ISO_SEC
  (2026-11-16, `NET_ALIASES` in p2k_config.py maps the Proteus IPC names).
- `kicad-cli sch export netlist` warns "schematic has annotation errors" – to be
  investigated (the netlist itself matches the inventory and the IPC netlist).

## 9. ADC mux: leakage between channels

**Control card** (`~/dev/ti60f225_tube_psu_control_card`, `hardware/sheets/adc.kicad_sch`):
J1 pins go straight to the TMUX1308 sources (no R, C or clamp on the card). Chain A: U10 →
OPA365 U11 (follower) → 33 Ω / 680 pF C0G → ADS7056 U12; chain B: U13 → U14 → U15. 0–3.3 V
(AVDD = reference), 14 bit, AINM = GND, selects A0–A2 straight from the FPGA, ~EN tied low,
one input per mux tied to GND (U10 S7, U13 S4). TMUX1308 at 3.3 V: RON 120 Ω typ / 350 Ω max,
C_D(ON) 40 pF, charge injection −1 pC, leakage ±45 nA (TI SCDS426E, quoted in the card's
CONVERSION_PLAN.md). No ADC/mux sequencing code exists yet (no RTL in the card repo), so the
dwell time after a channel switch is still free to choose.

**Mechanism.** After a switch the mux output node (C_D + OPA365 input, ≈ 45 pF) still holds the
previous channel's voltage. The new channel's power-board output network recharges it
through RON; what is left at the ADC sample instant is leakage of the previous channel into
this one (its size scales with the voltage difference between the two channels). A channel
whose output has a large capacitor behind a large resistor (DC_LINK, AUX) charge-shares
instantly with the node and then recovers with its own slow RC.

**Simulation** (`spice/mux_settling.py`): the power-board output network of each channel
(same netlists as section 1–3), switch, RON 350 Ω (worst case), 45 pF precharged to 0 V;
leakage = remaining fraction of the step at the sample instant, also given as LSB for a
full-scale 3.3 V difference between the two channels; separately the 1 pC charge injection.
Op-amps as the macromodel (no slew-rate limit: real TLV316 6 V/µs adds ≈ 0.5 µs for a
3.3 V step).

| Channel network | 0.2 µs | 0.4 µs | 1 µs | 2 µs | 5 µs | 10 µs | 20 µs |
|---|---|---|---|---|---|---|---|
| PFC_I1/I2 (100 Ω + 100 pF) | 0.07 | 0.76 | 0.02 | 0 | 0 | 0 | 0 |
| DHB_I (33 Ω) | 1.6 | 1.0 | 0.18 | 0.01 | 0 | 0 | 0 |
| HEATER_I (33 Ω) | 0.88 | 0.79 | 0.36 | 0.10 | 0 | 0 | 0 |
| VAC (100 Ω, no C) | 5.4 | < 0.01 | 0 | 0 | 0 | 0 | 0 |
| **DC_LINK as built (1 kΩ + 1 nF)** | **547** | **452** | **254** | **97** | **5.5** | 0.05 | 0 |
| **AUX as built (22 k / 4.7 k + 1 nF)** | **615** | **585** | **505** | **394** | **188** | **55** | **4.6** |
| VAC fix 2 (Cf 1 nF, R65 100 Ω, no C) | 4.4 | < 0.01 | 0 | 0 | 0 | 0 | 0 |
| VAC with R65 1 k + 1 nF (rejected) | 547 | 452 | 254 | 97 | 5.5 | 0.05 | 0 |
| VAC with R65 100 Ω + 10 nF | 59 | 48 | 26 | 9.0 | 0.4 | 0 | 0 |
| **DC_LINK fix 3 (Cf 1 nF, R2 100 Ω, no C4)** | 4.4 | < 0.01 | 0 | 0 | 0 | 0 | 0 |
| DC_LINK with Cf 1 nF, R2 100 Ω, C4 10 nF | 59 | 48 | 26 | 9.0 | 0.4 | 0 | 0 |
| AUX with C61 100 nF | 6.7 | 6.7 | 6.7 | 6.7 | 6.6 | 6.5 | 6.4 |
| **AUX with C61 1 µF** | 0.72 | 0.67 | 0.67 | 0.67 | 0.67 | 0.67 | 0.67 |
| DHB_I with C26 1 nF fitted | 6.1 | 1.2 | 0.22 | 0.01 | 0 | 0 | 0 |

(LSB of 201 µV left from a 3.3 V difference to the previous channel; "0" = below 0.01 LSB.)
Charge injection (1 pC) adds ≤ 0.02 LSB on the low-impedance outputs, 2.1 LSB at 1 µs on
DC_LINK as built and 4.1 LSB on AUX as built; ≤ 0.05 LSB with the fixes.

**Result.** With the mux switched every sample (0.4 µs at 2.5 MSPS) the amplifier outputs are
already clean (≤ 1 LSB), but DC_LINK_MEAS and AUX_MEAS carry hundreds of LSB of whatever
channel was selected before them – a channel-order-dependent error at 0.4 µs of up to
452 LSB = 2.8 % FS on DC_LINK (≈ 18 V on the DC link) and 585 LSB = 3.6 % FS on AUX
(≈ 0.7 V on the 20 V rail). Recommended power-board changes (all channels then ≤ 1 LSB at 0.4 µs, except AUX's
fixed 0.67 LSB):

1. **DC_LINK_MEAS:** fix 3 (Cf 1 nF across R17 and R82, R2 100 Ω, C4 removed). Keeps the
   10.7 kHz bandwidth and the HF rejection (−81 dB at 1 MHz), leakage < 0.01 LSB at 0.4 µs.
2. **AUX_MEAS:** C61 1 nF → 1 µF X7R (bandwidth 41 kHz → 41 Hz, ample for a rail monitor).
   The charge sharing with 45 pF is then 4.5·10⁻⁵ (0.67 LSB per 3.3 V difference),
   independent of the dwell time. A follower (TLV316 like U6/U8) would remove it entirely
   but costs a part; 100 nF leaves 6.7 LSB.
3. **VAC_MEAS:** fix 2 without an output capacitor (Cf only).
4. **DHB_I / HEATER_I / PFC_I:** no change (leave C10 / C26 unfitted).
5. Mux leakage current (±45 nA max at 85 °C) through the source resistance: ≈ 0.9 LSB offset
   on AUX (3.9 kΩ), negligible on the amplifier outputs.

Control-card / firmware options (no power-board change): a dwell time of ≥ 10 µs before
sampling DC_LINK and ≥ 30 µs before AUX (as built); or sample the slow channels twice and
discard the first; or pass through the grounded mux input before each slow channel, which
turns the order-dependent leakage into a fixed, calibratable gain error. J2-38 (ADA6) and
J2-39 (ADB5) are unconnected on the power board but named "Cuk_cap_meas_raw" /
"heater_cap_ad_meas" in the card's `power_board_header.csv`: as floating mux inputs they
read whatever the previous channel left – do not use them, or tie them to GND.

## 10. ADC range of VAC_MEAS and AUX_MEAS

- **VAC_MEAS** = 1.65 V + 0.005·(V(AC2) − V(AC1)). At 230 V rms (325 V peak) the swing is
  ±1.63 V, i.e. 0.02–3.28 V: only 25 mV headroom. Above ≈ 330 V peak (230 V + 1.5 %) the
  TLV316 output clips at the rails, and at 230 V + 10 % (358 V peak) it would need −0.14 V…
  3.44 V. **Fix:** R49 and R80 15 kΩ → 12 kΩ (gain 0.004: ±1.43 V at 253 V rms, ±1.49 V at
  264 V rms). With fix 2 the pole moves to 1/(2π·12 kΩ·1 nF) = 13.3 kHz.
- **AUX_MEAS** = 0.176·V(15V). The 15V rail (Proteus name "20V", left over from an old
  revision; likewise 15V_ISO_SEC = "20V_ISO_SEC") is 15 V nominal, so AUX_MEAS ≈ 2.64 V and the
  divider's 18.7 V full scale (PDF note) leaves 3.7 V of headroom for the light-load rise of
  the flyback (cross regulation, see `flyback/`). No change needed unless the flyback study
  shows the rail exceeding 18.7 V.

## Next steps

1. Re-run fixes 1–3 with the TI vendor models (TLV316, LMH6658) for stability and
   output-swing checks (PLAN.md step 5).
2. Decide the bandwidths for VAC_MEAS and DC_LINK_MEAS with the control design, then size
   the capacitors (fc = 1/(2π·15 kΩ·C)).
3. Measure one board: line ripple on PFC_I1_MEAS at zero current (expected ±15 mV as built)
   and the VAC_MEAS response with a network analyser, to replace the assumed 0.2 pF.
4. Put the chosen fixes into the schematic of the next revision; extend circuits.py /
   whatif_fixes.py so run_sim.py checks the new circuit.
