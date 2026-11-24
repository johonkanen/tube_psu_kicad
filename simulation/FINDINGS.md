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

### 9a. INA296 option (NEXT_REVISION.md 4.10), `spice/mux_ina296.py`

INA296 output modelled as a follower with 1.1 MHz loop GBW and an open-loop output resistance
RO of 50 / 200 Ω (the datasheet gives no output-impedance curve), same mux model. LSB for a
3.3 V difference:

| Output network | RO | 0.2 µs | 0.4 µs | 0.7 µs | 1 µs | 1.5 µs | 2 µs |
|---|---|---|---|---|---|---|---|
| 100 Ω + 100 pF | 50 | 98 | 27 | 3.0 | 0.32 | 0 | 0 |
| 100 Ω + 100 pF | 200 | 373 | 143 | 7.2 | 0.19 | 0 | 0 |
| 33 Ω, no C | 50 | 85 | 21 | 2.6 | 0.31 | 0 | 0 |
| 33 Ω, no C | 200 | 377 | 88 | 9.3 | 0.98 | 0.02 | 0 |
| 100 Ω + 1 nF | 200 | 326 | 15 | 99 | 39 | 10 | 0.82 |

The INA296 (1.1 MHz) settles slower than the LMH6658 (140 MHz GBW): sample ≥ 1.5 µs after the
switch, keep 100 Ω / 100 pF (1 nF rings). Slew (5–8 V/µs) is not modelled (≈ +0.2 µs for the
≈ 1 V charge-sharing dip).

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

## 11. 5.2 circuits (phase 4a, 2026-11-18)

Board tube_power 5.2 (`kicad_next/tube_psu_5_2.kicad_sch`, values per
[kicad_next/CHANGES_5_2.md](../kicad_next/CHANGES_5_2.md) section 4). Rerun:
`python3 simulation/run_sim.py --rev 5.2` (golden check against `circuits.GOLDEN_52`, ngspice,
hVHDL_ode, output `out/5.2/`), then `spice/bias_buffer.py`, `spice/shunt_esl.py`,
`spice/mux_settling.py --rev 5.2`, `spice/ranges_5_2.py` (result tables `out/5.2/*_results.md`).
The 5.1 flow is unchanged and still reproduces sections 1–10 (`run_sim.py` without `--rev`).

**Models.** Op-amp macromodels (A0, one pole, Rout; same in ngspice and VHDL): LMH6643 57 MHz,
96 dB, Rout 75 Ω; TLV9062 10 MHz, 118 dB, 100 Ω; TLV316 unchanged (10 MHz, 250 Ω). The TI vendor
models are now downloaded and run in ngspice (`spice/vendor_models.py`, not committed; PLAN step 5
partly done): TLV316 110 dB / 16.5 MHz unity gain / Zo 253 Ω / 6 V/µs, TLV9062 118 dB / 9.8 MHz /
99 Ω / 6.1 V/µs, LMH6643 (NSC 2005 transistor model) 114 dB / 85 MHz / Zo 73 Ω above 100 kHz. For
transients a slew-limited variant (`opamp_<part>_sr`: gm current limited to SR·C1, rails 0.04–3.26 V;
LMH6643 120 V/µs, TLV316 6 V/µs, TLV9062 6.5 V/µs) is used. The VHDL model gained a follower
(group E: AUX, 5V_MEAS), the U9 bias follower as a state, a − leg that is only capacitive sections
(Cf with the 1 MΩ parasitics) and the capacitor loop with the bias capacitor (VAC + leg: 3 × 0.2 pF +
C126 + C48).

### 11.1 AC responses: all 10 channels pass (hVHDL_ode vs ngspice)

[out/5.2/report.md](out/5.2/report.md): 0.007–0.027 dB / 0.04–0.19° RMS, DC gains identical
(5V_MEAS −0.004 %: VHDL DC point not fully settled, 0.6 ms τ), −3 dB within 1.1 %.

| channel (J2, ADC) | DC gain | −3 dB | note |
|---|---|---|---|
| PFC_I1 (J2-42, A) / PFC_I2 (J2-44, A) | 82.41 mV/A | 825 kHz | 5.1: 993 kHz (LMH6643 lower GBW) |
| DHB_I (J2-38, A) | 181.7 mV/A | 517 kHz | balanced 12p/12p |
| HEATER_I (J2-45, B) | 399.4 mV/A (−0.16 %) | 342 kHz | 5.6p/5.6p; op-amp limited (noise gain 101) |
| VAC (J2-47, B) | 0.0040072 (+0.18 %) | 13.3 kHz | −33 / −38 / −50 dB rel. DC at 1 / 10 / 50 MHz (5.1: +22 dB) |
| DC_LINK (J2-41, B) | 0.0050 | 10.6 kHz | −35 / −40 / −52 dB at 1 / 10 / 50 MHz |
| AUX (J2-43, B) | 0.17603 | 411 Hz | C61 100n behind the follower |
| 5V_MEAS (J2-49, B) | 0.4000 | 265 Hz | new |
| AD2 420 V / AD1 6V3 | 0.0050 / 0.4533 | 8.86 kHz / 1.82 MHz | unchanged |

### 11.2 Ranges ([out/5.2/ranges_results.md](out/5.2/ranges_results.md))

Bias node 1.6418 V (divider 1.6554 V − 13.6 mV over R131 at 0.62 mA of + leg loads; ±14 mV from
the REF3325 / 1 % divider tolerances, common to all channels → zero calibration). Output range taken
0.04–3.26 V.

| channel | range | LMH6643 Vos 3.4 / 5 / 7 mV (25 °C max / task / temp. max) | range after 7 mV | 1 LSB |
|---|---|---|---|---|
| PFC_I1/I2 | −19.4 / +19.6 A | 0.89 / 1.31 / 1.84 A | ±17.6 A | 2.4 mA |
| DHB_I | −8.8 / +8.9 A | 0.87 / 1.28 / 1.79 A | ±7.0 A | 1.1 mA |
| HEATER_I | −4.0 / +4.1 A | 0.86 / 1.26 / 1.77 A | ±2.2 A | 0.5 mA |

(Vos × noise gain / channel gain; the datasheet's 5 mV column is the LMH6642/44, the LMH6643 is
3.4 mV at 25 °C and 7 mV over temperature.) VAC: 0.146–3.138 V at 264 V rms (373 V peak), clips at
400 V peak (283 V rms) – the 12 k change works. DC_LINK full scale 652 V (2.00 V at 400 V). AUX full
scale 18.5 V (2.64 V at 15 V). 5V_MEAS 2.000 V at 5.0 V, full scale 8.15 V, 0.5 mV/LSB, ±0.08 % from
the 0.1 % divider. LMH6643 inputs at 1.57–1.63 V, inside its common-mode range (≤ 1.9 V over
temperature at 3.3 V).

**Note 2026-11-24 (shunts 5 mΩ, kicad_next/CHANGES_5_2.md 6.2):** the results above are for the 4 mΩ design value and
stay as computed. The board is now built with 5 mΩ KRL2012E-M-R005-F-T5: every current-channel gain × 1.25 (PFC
103.0 mV/A = 9.71 A/V, DHB 227.1 mV/A = 4.40 A/V, HEATER 499.2 mV/A = 2.00 A/V), ranges × 0.8 (PFC −15.6 / +15.7 A,
DHB ±7.1 A, HEATER ±3.2 A; after 7 mV Vos ±14.1 / ±5.6 / ±1.8 A), LSB 1.96 / 0.89 / 0.40 mA. The ESL compensation
of 11.4 (τ sized for 4 mΩ) over-compensates by about 25 % – to be tuned on the bench. Not re-simulated.

### 11.3 Bias buffer U9 stability ([out/5.2/bias_buffer_results.md](out/5.2/bias_buffer_results.md))

U9 drives 22 Ω + 100 nF with the feedback from its output pin: the 22 Ω sets an HF loop attenuation
22 / (Zo + 22) and a pole/zero pair at 5.9 / 72 kHz, far below the crossover.

| op-amp model | crossover | phase margin | gain margin | 10 mV step overshoot (U9 out / bias) |
|---|---|---|---|---|
| macromodel, 1 pole | 0.81 MHz | 85° | – | 5.8 % / 0 % |
| 2 poles (+30 MHz) + Zo 250 Ω | 0.81 MHz | 84° | – | 5.8 % / 0 % |
| **TI TLV316 vendor model** | **0.87 MHz** | **84°** | **35 dB** | **5.5 % / 0 %** |
| (feedback from the bias node instead) | 0.24 MHz | 1° | – | oscillates (vendor) |

**Stable as built.** Do not move the feedback to the bias node. Side effect of the output-pin
feedback: the bias source impedance is 22 Ω up to ≈ 50 kHz, so the VAC + leg (3.012 MΩ from AC2)
still injects 7.3·10⁻⁶ V/V into the bias (5.1: 4.7·10⁻⁵): 2.4 mV peak at 325 V peak = **29 mA on
PFC_I, 13 mA DHB_I, 6 mA HEATER_I** at line frequency (VAC gain +0.18 %); a 1 mA load step moves
the bias by 22 mV. Options if that matters: firmware subtracts k·VAC (k from the 22 Ω, fixed), or
split feedback (100 kΩ bias node → IN−, 1 nF U9 out → IN−, PM 84°, vendor model): coupling
2.3·10⁻⁷, the 13.6 mV DC drop gone; two parts, not required.

### 11.4 Shunt ESL compensation ([out/5.2/shunt_esl_results.md](out/5.2/shunt_esl_results.md))

4 mΩ + L, 0 → 3 A in 20 ns (raw spike L·dI/dt = 75 / 120 / 180 mV at 0.5 / 0.8 / 1.2 nH against
12 mV of signal), both feedback caps swept, LMH6643 slew-limited (slew not reached: identical to the
linear model). Overshoot above the final value with the 5.2 caps, and the smallest C that keeps the
overshoot ≤ 1 %:

| channel | 5.2 C (τ = Rf·C) | overshoot at L 0 / 0.5 / 0.8 / 1.2 nH | C for ≤ 1 % at 0.5 / 0.8 / 1.2 nH | first-order L/(R·Rf) |
|---|---|---|---|---|
| PFC (6.8k) | 20p (136 ns) | 0 / 0 / 2.8 % (84 mA) / 44 % (1.3 A) | 10 / 21 / 38 pF | 18 / 29 / 44 pF |
| DHB (15k) | 12p (180 ns) | 0 / 0 / 0 / 0 | 3.9 / 4.6 / 11.7 pF | 8.3 / 13 / 20 pF |
| HEATER (33k) | 5.6p (185 ns) | 0 / 0 / 0 / 0 | ≤ 1 pF at every L | 3.8 / 6.1 / 9.1 pF |

The op-amp's closed-loop pole adds to Rf·Cf, so less C than L/(R·Rf) is enough; HEATER at noise gain
101 is filtered by the LMH6643 itself (≈ 0.56 MHz) and needs no ESL cap (its 5.6p only sets the
342 kHz bandwidth). **Recommendation: keep 20p / 12p / 5.6p** (no spike up to 0.8 nH on any channel;
DHB is clean up to 1.2 nH). If the bench shows a spike on PFC_I (loop inductance ≥ 1 nH), go to 27–33p
(C113/C106, C112/C107 together). DHB 12p is the 1.2 nH value: at the typical 0.5 nH it is
over-compensated (−23 % at 300 ns, 1 % after 1.3 µs instead of 0.7 µs with 3.9p) – lower it on the
bench to 5.6–8.2p if a faster edge is wanted.

(2026-11-24: with the 5 mΩ shunts of CHANGES_5_2.md 6.2 the L/R time constant is 20 % shorter and the compensation
above about 25 % too strong; bench tuning, not re-simulated.)

### 11.5 ADC mux leakage ([out/5.2/mux_results.md](out/5.2/mux_results.md))

TMUX1308 RON 350 Ω, 45 pF, node precharged to the farther rail, slew-limited op-amps; LSB per 3.3 V
difference at the planned dwell (A 1 µs, B 2 µs), target < 0.5 LSB:

| output | ADC | macromodel (datasheet GBW) 1 / 1.5 / 2 / 3 µs | vendor LMH6643 model at the dwell | at planned dwell |
|---|---|---|---|---|
| PFC_I1, PFC_I2 | A | 0.62 / 0.05 / 0 / 0 | 0.02 (1 µs) | **0.62 (macro) / 0.02 (vendor)** |
| DHB_I | A | 2.98 / 0.58 / 0.11 / 0 | 0.15 (1 µs) | **2.98 / 0.15** |
| HEATER_I | B | 8.2 / 2.8 / 0.95 / 0.11 | 0.04 (2 µs) | **0.95 / 0.04** |
| VAC, DC_LINK | B | 0.02 from 0.4 µs | – | 0.02 |
| AUX, 5V_MEAS | B | 0 from 0.4 µs | – | 0 |

Charge injection ≤ 0.03 LSB everywhere. The LMH6643 recovers from the mux charge kick more slowly
than the LMH6658 of 5.1 (57 vs 140 MHz, Zo 75 vs 10 Ω): the dip decays with Rf·Cf. The macromodel
with the datasheet GBW and the vendor Zo is the conservative bound, the vendor model (85 MHz) the
optimistic one. C26 / C10 = 1 nF does not help (3.9 / 0.96 LSB). **Recommended dwell: ADC A ≥ 2 µs
(DHB 0.11, PFC 0 LSB; A has 2.38 µs per channel at 140 kHz with three channels), ADC B ≥ 3 µs before
HEATER_I (0.11 LSB)**, ≥ 0.5 µs for the TLV316 / TLV9062 channels. No hardware change. (NR 4c.4
still says A ≥ 1 µs / B ≥ 2 µs – to update there.)

### 11.6 Summary – schematic changes needed

None required. Optional: U9 split feedback (100k + 1n) against the 29 mA line-frequency term on
PFC_I (11.3); PFC ESL caps 27–33p only if the bench shows a spike (11.4). Firmware: zero
calibration (Vos up to 1.8 A input-referred over temperature, bias tolerance), mux dwell A ≥ 2 µs /
B ≥ 3 µs before HEATER_I (11.5).

## Next steps

1. Re-run fixes 1–3 with the TI vendor models (TLV316, LMH6658) for stability and
   output-swing checks (PLAN.md step 5).
2. Decide the bandwidths for VAC_MEAS and DC_LINK_MEAS with the control design, then size
   the capacitors (fc = 1/(2π·15 kΩ·C)).
3. Measure one board: line ripple on PFC_I1_MEAS at zero current (expected ±15 mV as built)
   and the VAC_MEAS response with a network analyser, to replace the assumed 0.2 pF.
4. Put the chosen fixes into the schematic of the next revision; extend circuits.py /
   whatif_fixes.py so run_sim.py checks the new circuit.
