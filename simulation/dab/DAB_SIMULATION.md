# DAB switching simulation (5.2, TR3 option B 20:21)

ngspice switching model of the 5.2 DAB (dual half bridge) with the new EC42 transformer.
It checks phase shift, currents, ZVS of all four switches, dead time, gap, losses, the DHB
shunt signal and start-up. The transformer design itself is in
[DAB_TRANSFORMER.md](DAB_TRANSFORMER.md).

Rerun:
- `python3 simulation/dab/dab_spice.py`: all studies, about 2.5 h with 2 ngspice processes,
  about 12 MB RAM each. `--only full,load,mismatch,lm,shunt,startup,coss,scan,scan2,scanlm,lm200`
  picks studies, which merge into `out/spice_results.json`. `--report` rebuilds `out/spice_results.md` from `out/spice_results.json`.
- `python3 simulation/dab/dab_spice_plot.py`: waveform figure `dab_spice_waves.png`.

`out/` is git-ignored.

## 1. Model

All values are read from `kicad_next/tube_psu_5_2.kicad_sch` (kicad-cli netlist, sheets 02, 07
and 08) and from the OpenMagnetics run of option B with the TIW-litz secondary
(`mas/tr3_dab_B_42uH_TIW.json`, `out/results_tiw.json`).

| block | model |
|---|---|
| primary bridge | Q19 (high, DC+ → DHB_HI_SOURCE) / Q7 (low, → DHB_CURRENT). Split caps C47 / C54 1 µF (15 mΩ, 8 nH each); C67 + C70 2 × 100 nF DC+ → DHB_CURRENT; **R83 4 mΩ DHB_CURRENT → GND + ESL 0.7 nH (0 / 0.5 / 1 nH in the shunt study)**. The PFC bulk is a 400 V source behind 0.1 Ω + 60 nH (bulk ESR / ESL + DC+ trace). |
| secondary bridge | Q21 (high, 420V → DHB_HI_SOURCE_SEC) / Q8 (low, → ISO_GND). Split caps C16 / C55 1 µF (15 mΩ, 8 nH); 6 × 100 nF on 420V. Load: **constant voltage** (420 V source behind 50 mΩ + 50 nH), so the sign of φ sets the power direction. ISO_GND → GND 10 kΩ (DC reference only). |
| TR3 | coupled inductors, dot at the bridge midpoints. **Lm 307 µH** (gap 0.34 mm), **Lsc 40.4 µH** primary-referred, split 47.4 % primary / 52.6 % secondary (geometry), n = 21/20. R_ac at 140 kHz 70 / 74 mΩ (MKF winding loss with the real currents ÷ Irms²). Core loss 1.5 W as 24 kΩ across the primary. Winding self-capacitance from MKF (Albach model) about 3 / 4.5 pF, rounded up to 5 / 7 pF. Interwinding capacitance 2 × 1.5 pF, a hand estimate for the 5 mm divider (MKF gives no interwinding term for side-by-side chambers). Layout 10 pF per switch node. |
| gate drive | UCC21520 as an ideal PWM source, 1 Ω output, 10 ns edges, 15 V (low side) / 14.2 V (bootstrap high side). Network as on sheet 07: R90/R26/R57/R87 **40 Ω turn-on**, in parallel with **3.3 Ω + ZLLS400 for turn-off**, 10 kΩ gate pull-down, RG(int) 7.2 Ω. The dead time is the time from one switch's off command to the other's on command. It is the total, i.e. max(FPGA dead time, the UCC21520 DT of 100 ns). |
| STF7N60M2 | ST's SPICE model could not be fetched (st.com refuses scripted downloads), so the model is built from the datasheet (DocID024894). Level-1 channel (Vth 3 V, Kp 2.5 A/V²) plus drift resistance, R_on **1.3 Ω** (0.86 Ω typ × 1.5 at Tj ≈ 75 °C). Coss and Crss are smooth charge functions fitted to Fig. 8. **Coss below 50 V is scaled up so that Q(0…480 V) = Co(tr) × 480 V = 36 nC.** The small-signal curve alone gives only 22 nC, i.e. 46 pF time-related; section 2.7 checks that. Crss is scaled so that Qgd ≈ 4.3 nC; Cgs is 260 pF. Body diode: Vsd ≈ 0.9 V at 2.5 A and **TT 250 ns**, so Qrr ≈ 1.5 µC at 5 A (Table 8). |

Method:
- Each run starts from the steady state of the ideal circuit (`dab_wave.py`, with R_on and the
  winding R) and simulates 80 periods (50 in the φ scans). The last period is evaluated.
- The slow split-cap / Lm mode (≈ 4.5 kHz, Q ≈ 10) is excited only a little. At 30 periods the
  residual DC magnetising current is 16 mA; at 120 periods it is below 1 mA, with identical
  P, currents and ZVS.
- At 100–400 W, φ is solved for the power into the 420 V source by a secant method in SPICE,
  to within ±1.5 W.
- Near φ = 0, P(φ) is not smooth: the dead time shifts the effective edges. Light load is
  therefore scanned in φ (section 2.3).

Evaluation per switch:
- **Vds at turn-on**: the drain-source voltage when Vgs crosses Vth. About −0.8 V means the
  body diode conducts, i.e. full ZVS; anything above 0 V is partial or hard switching.
- **Node swing**: the time from the outgoing switch's Vth crossing until the node reaches 95 % of
  the rail. The dead time minus the swing time is the ZVS time margin.
- **i_off**: the drain-source current at the off command.
- **Eoff**: the integral of Vds·I_channel over the dead time.

ngspice notes: uic plus nearly coincident PULSE breakpoints of the two bridges, or 5 ns
driver edges, made ngspice stop with "timestep too small". The model therefore offsets the
secondary edges by 0.1 ns, uses 10 ns edges and sets `rshunt=1e9`. `run_case` retries with a
smaller first step if the first picoseconds fail.

## 2. Results

Full tables: `out/spice_results.md` (`--report`). Waveforms at 400 W and ≈ 0 W (150 ns, Lm 307 µH): `dab_spice_waves.png`.

### 2.1 400 W, 400 V → 420 V, both directions

| total dead time | direction | φ (ideal model) | P_in / P_out W | eff. | I1 rms / pk A | I2 rms / pk A | current at the off command (sending bridge / receiving bridge) A | current at turn-on of the incoming sending-side switch A | Vds at turn-on, all 4 switches |
|---|---|---|---|---|---|---|---|---|---|
| 100 ns | fwd | **+23.8°** (24.1°) | 412 / 400 | 97.2 % | 2.31 / 2.70 | 2.22 / 2.85 | 2.68 / 2.56 | −1.75 | −0.9 V (ZVS) |
| 150 ns | fwd | +23.8° | 412 / 400 | 97.2 % | same | same | same | −1.27 | −0.9 V |
| 200 ns | fwd | +23.8° | 412 / 400 | 97.2 % | same | same | same | −0.77 | −0.8 V |
| 250 ns | fwd | +23.8° | 412 / 400 | 97.2 % | same | same | same | **−0.27** | −0.8 V |
| 100 ns | rev | **−23.2°** (−23.2°) | 388 / 399 (from 420 V) | 97.3 % | 2.28 / 2.97 | 2.13 / 2.46 | 2.44 / 2.67 | −1.58 | −0.9 V |
| 150…250 ns | rev | −23.2° | same | same | same | same | same | −1.11 / −0.64 / **−0.17** | −0.8 V |

- **φ at 400 W is 23.8° forward and 23.2° reverse**, which meets the ≈ 24° target. The
  steady-state model in DAB_TRANSFORMER.md gave 23.6°. φ is independent of the dead time at
  400 W: the turn-off instants set the edges, and the node swings in 9–11 ns.
- **RMS / peak currents:** I1 2.31 / 2.70 A and I2 2.22 / 2.85 A. Magnetising current 0.98 A
  peak. Split-cap ripple 4.8 V pp (primary) and 5.1 V pp (secondary).
- **ZVS at 400 W:** all four switches turn on with the body diode conducting. The current at the
  off command is 2.4–2.7 A, against the ≈ 0.5 A needed.
- **Dead-time limit:** after the edge, the sending bridge's current decays at about 10 A/µs
  and crosses zero 260–270 ns after the edge at 400 W, and earlier at lower load. At 250 ns
  only 0.2–0.3 A is left at full load. At 100–200 W the current has already reversed at
  turn-on for DT ≥ 150–200 ns (+0.1 … +0.7 A). The node is then held only by the body
  diode's stored charge (Qrr), not by the transformer current (section 2.2).
- **Losses: 11.6 W at 400 W (97.2 %).**
  - The **sending bridge's MOSFETs carry 6.8 W (3.4 W each)** of conduction loss: R_on
    1.3 Ω hot × (2.31 A)²/2 per switch.
  - The receiving bridge carries 2.1 W, mostly in the body diodes: 1.3 Ω × 2.5 A is above the
    diode's 0.9 V, so synchronous rectification hardly helps with this MOSFET.
  - Transformer 2.2 W; split caps, shunt and bus about 0.5 W.
- **Turn-off loss:** Eoff is 0.13–0.18 µJ per switch per edge (ZVS turn-off with Coss as the
  snubber), so about **0.1 W for all four switches together**. Turn-on loss is 0 at 400 W.
- **Thermal note:** 3.4 W per sending-side STF7N60M2 (TO-220FP, RthJC 6.25 K/W) is the
  dominant loss.
  - A lower-R_on part in the same package (e.g. the 0.4 Ω MDmesh M2 class) would roughly halve
    it.
  - But its larger Coss needs more magnetising current, so Lm and the dead time would have to
    be redone. Not changed here.

### 2.2 ZVS vs load at the matched voltage (420 V), Lm 307 µH

Here φ is solved for each power (`load` study). The 0 W point does not converge with the
secant (P(φ) jumps near 0), so light load comes from the φ scan in 2.3.

| total DT | 100 W fwd | 200 W fwd | 400 W fwd | 100 W rev | 200 W rev | 400 W rev |
|---|---|---|---|---|---|---|
| 100 ns | ZVS | ZVS | ZVS | sec 0.3 V (marginal) | ZVS | ZVS |
| 150 ns | ZVS (i_on +0.1 A) | ZVS | ZVS | ZVS (i_on +0.1 A) | ZVS | ZVS |
| 200 ns | ZVS (i_on +0.1 A) | ZVS (i_on +0.3 A) | ZVS | ZVS | ZVS (i_on +0.3 A) | ZVS |
| 250 ns | ZVS (i_on +0.1 A) | ZVS (i_on +0.7 A) | ZVS | sec **0.5 V** | ZVS (i_on +0.7 A) | ZVS |

How to read the table:
- φ: 4.7° at 100 W, 10.8° at 200 W, 23.8° at 400 W (reverse 5.3 / 10.9 / 23.2°).
- "i_on +x A": the current in the incoming switch of the sending bridge has already reversed when
  its gate turns on. The node stays clamped only by the body-diode recovery charge. That works
  in the model (Eon ≤ 0.03 µJ) but has no margin, and it gets worse with a faster diode or a
  longer dead time.

### 2.3 Light load: φ scans (P −250 … +250 W)

Near φ = 0, P(φ) is steep and not monotonic: about 100 W/° between −1° and −0.5°, against 20 W/°
elsewhere.
- **φ = 0 does not give 0 W**: at 150 ns it gives about +46 W, because the secondary node needs
  longer to swing than the primary. **Zero power needs φ ≈ −0.8°.**
- For the firmware: the power loop gain is about 5× higher around zero power. A small negative
  φ is needed to hold 0 W.

**Lm 307 µH (gap 0.34 mm):**

Hard switching = Vds at turn-on above 20 V (5 % of the rail) on any switch; partial = 2…20 V. Eon = the largest per-edge turn-on energy (Coss discharge + body-diode recovery of the partner).

| output | dead time | phi at P = 0 deg | worst Vds_on at P ≈ 0 V (switch) | node swing at P ≈ 0 ns (max) | P range with hard switching W | P range with partial ZVS W | max Eon uJ (at P W) |
|---|---|---|---|---|---|---|---|
| 399 V | 100 ns | -3.02 | 398.4 (Q21, P 0) | 101 | -111 … 103 | -161 … -125 | 34.69 (39) |
| 399 V | 150 ns | -5.61 | 397.9 (Q8, P 2) | 151 | -82 … 148 | -149 … -108 | 37.29 (38) |
| 399 V | 200 ns | -8.18 | 397.3 (Q8, P 3) | 201 | -135 … 191 | -182 … -148 | 39.61 (48) |
| 399 V | 250 ns | -10.53 | 396.9 (Q8, P 4) | 250 | -200 … 233 | -229 … -210 | 42.20 (67) |
| 420 V | 100 ns | -0.71 | 40.1 (Q8, P -4) | 97 | -4 … 66 | -78 … 75 | 0.67 (38) |
| 420 V | 150 ns | -0.80 | 0.7 (Q8, P 5) | 106 | none | none | 0.00 (-49) |
| 420 V | 200 ns | -0.80 | -0.7 (Q21, P 5) | 106 | none | none | 0.00 (120) |
| 420 V | 250 ns | -0.80 | -0.7 (Q21, P 5) | 106 | none | none | 0.01 (-111) |
| 441 V | 100 ns | 3.05 | 394.3 (Q7, P -1) | 100 | -114 … 88 | 104 … 144 | 25.97 (-51) |
| 441 V | 150 ns | 5.50 | 386.5 (Q7, P -0) | 150 | -164 … 83 | 102 … 144 | 30.07 (-63) |
| 441 V | 200 ns | 7.13 | 396.3 (Q7, P -27) | 200 | -214 … 141 | 154 … 188 | 33.19 (-75) |
| 441 V | 250 ns | 9.33 | 291.2 (Q19, P 21) | 249 | -249 … 206 | 217 … 246 | 35.52 (-76) |

Scanned P range per row: about -249 … 255 W.
**±2 % mismatch, Lm 307 µH:**

Hard switching = Vds at turn-on above 20 V (5 % of the rail) on any switch; partial = 2…20 V. Eon = the largest per-edge turn-on energy (Coss discharge + body-diode recovery of the partner).

| output | dead time | phi at P = 0 deg | worst Vds_on at P ≈ 0 V (switch) | node swing at P ≈ 0 ns (max) | P range with hard switching W | P range with partial ZVS W | max Eon uJ (at P W) |
|---|---|---|---|---|---|---|---|
| 412 V | 150 ns | -3.72 | 361.9 (Q21, P 34) | 149 | 34 … 107 | -102 … 105 | 4.78 (69) |
| 412 V | 200 ns | -3.85 | 8.7 (Q21, P -41) | 119 | 91 … 120 | -134 … 118 | 4.29 (91) |
| 428 V | 150 ns | 1.85 | 6.1 (Q7, P 27) | 103 | -71 … -61 | -78 … 90 | 0.17 (-61) |
| 428 V | 200 ns | 1.86 | 0.8 (Q7, P 26) | 105 | none | 42 … 119 | 0.04 (90) |

Scanned P range per row: about -134 … 147 W.


Matched voltage (420 V):
- **≥ 150 ns gives ZVS over the whole light-load range** (worst +1.7 V at 150 ns, i.e. ZVS in
  practice).
- The longest node swing is **114 ns**, on the secondary at P ≈ 0 to +40 W. At **100 ns** (the
  UCC21520 DT alone) the secondary is partly hard-switched between −80 and +75 W, up to 170 V.

**Output mismatch is the real limit.**
- **±5 % (399 / 441 V):** the lower-voltage bridge is **hard-switched at full voltage** (up to
  398 V) from about −100 … −200 W to about +100 … +230 W. The range grows with the dead time,
  because a node that does not swing shifts the effective edge by the whole dead time.
- Eon is up to **35–42 µJ per edge**. That includes the body-diode recovery of the partner, i.e.
  **5–6 W per switch** at 140 kHz. The total loss reaches 15–17 W at 40–100 W of load, against
  12 W at 400 W. With the SJ body diode (Qrr ≈ 1.5 µC), **repeated hard commutation is a
  reliability risk**, not just a loss.
- At 400 W, ±5 % is fine: ZVS on all switches, φ 25.0° (399 V) / 23.0° (441 V), I1 rms 2.42 /
  2.25 A.
- **±2 % (412 / 428 V):** 428 V is fine at 200 ns (partial ZVS only, Eon ≤ 0.04 µJ). 412 V still
  has hard edges at +34 … +107 W (150 ns) and +91 … +120 W (200 ns), with Eon ≤ 4.8 µJ, i.e.
  ≤ 0.7 W per switch.
- **So at light load, the two bus voltages must track within about ±1 %**: V(DC+) × 21/20 ≈ V(420V).
  The same result was found analytically in DAB_TRANSFORMER.md 4, but the SPICE boundary
  (≈ ±150 W at ±5 %) is much wider than the 50 W estimated there.

### 2.4 Gap / Lm

At 400 W, Lm hardly matters:
- 250 µH: φ 24.0°, I1 rms 2.34 A, loss 11.8 W.
- 307 µH: φ 23.8°, I1 rms 2.31 A, loss 11.6 W.
- 400 µH: φ 23.9°, I1 rms 2.31 A, loss 11.6 W.
- The magnetising peak is 1.19 / 0.98 / 0.76 A.

Light load at 150 ns, scanned in φ (`scan_lm`):

| Lm | 420 V: worst Vds_on, longest node swing | 441 V (+5 %): hard-switching range, max Eon | 399 V (−5 %): hard-switching range, max Eon | I1 rms at 0 W | 400 W: φ, I1 rms, loss |
|---|---|---|---|---|---|
| 200 µH | ZVS, 66 ns (also ZVS at 100 ns DT) | **none** (partial ≤ 3.4 V), 0.02 µJ | +30 … +109 W, **6.2 µJ** (worst 20 V at P ≈ 0) | 0.52 A | 24.3°, 2.38 A, 12.1 W |
| 250 µH | ZVS, 85 ns | −126 … −27 W, 7.9 µJ | – | – | 24.0°, 2.34 A, 11.8 W |
| **307 µH (0.34 mm gap)** | ZVS, 114 ns | −164 … +83 W, **30 µJ** | −82 … +148 W, **37 µJ** | 0.34 A | 23.8°, 2.31 A, 11.6 W |
| 400 µH | partial, hard 84–92 W, 123 ns | −168 … +112 W, 40 µJ | – | – | 23.9°, 2.31 A, 11.6 W |

**The gap is a strong lever for mismatch tolerance.**
- More magnetising current (Im peak 1.48 A at 200 µH, against 0.98 A at 307 µH) keeps both
  bridges' edge currents in the right direction when the two voltages differ.
- At 200 µH, +5 % gives no hard switching at all. −5 % leaves a small window (+30…+109 W) with
  ≤ 6 µJ edges instead of 37 µJ, i.e. about 0.9 W per switch instead of about 5 W.
- The cost is +0.5 W at 400 W (I1 rms +3 %) and +0.3 W at no load.
- 200 µH also gives ZVS at no load with only the 100 ns hardware DT (node swing 66 ns).

### 2.5 Transformer voltage stress (400 W)

- Winding voltage peak: 203 V (primary) and 213 V (secondary), i.e. half the bus plus the
  split-cap ripple. There is no ringing overshoot at the ZVS edges.
- Primary hot end ↔ secondary hot end: 421 V peak at 140 kHz, taking GND = ISO_GND at DC. This
  comes on top of the 552 Vrms mains working voltage from DAB_TRANSFORMER.md 8.
- Node dv/dt: 63–70 V/ns on the primary and 32–36 V/ns on the secondary. With about 3 pF
  interwinding capacitance, that drives **≈ 0.2 A common-mode current spikes** into
  ISO_GND / earth at each edge. This matters for EMI: keep the interwinding capacitance low
  (the divider does) and give ISO_GND a defined Y-cap return.

### 2.6 DHB shunt R83: what the current measurement sees

R83 sits between DHB_CURRENT and GND. C47 / C54 and C67 / C70 return to DHB_CURRENT, so **R83
carries only the bridge's input current from the PFC bulk**, not the transformer current.
That current is about 1.03 A DC plus a 280 kHz ripple, 2.6 A pp at 400 W.
- I(R83) average = P_in / 400 V (1.029 A). The amplifier reads 1.024 A, i.e. −0.5 %, which is a
  gain / bias offset to calibrate.
- So the shunt gives input power / current, not φ or the transformer current. It cannot be
  used for peak-current protection of the transformer.

| R83 ESL | V(R83) pk-pk (R only) | amplifier: I pk-pk seen (true 2.62 A) | max instantaneous error |
|---|---|---|---|
| 0 nH | 10.5 mV (10.5) | 1.46 A | 1.02 A (C63/C122 over-filter) |
| 0.5 nH | 13.9 mV | 1.65 A | 0.60 A |
| 1.0 nH | 23.6 mV | 2.29 A | **0.19 A** |

- With the 5.2 compensation (15 k × 12 p = 180 ns ↔ L = 0.72 nH at 4 mΩ), the ESL spikes are
  cancelled when the ESL is 0.7–1 nH (shunt plus Kelvin loop).
- With 0.5 nH the output is slightly over-filtered (0.6 A error), which does not matter for
  the average. Bench-tune C63/C122 as NR 4.11 says.
- The average, which the firmware uses for power, is right to −0.5 % for any ESL.

### 2.7 Coss sensitivity

With the small-signal Fig. 8 curve (22 nC, 46 pF time-related) instead of Co(tr) (36 nC):
- the no-load node swing drops from 114 to 71 ns (secondary) and from 64 to 56 ns (primary);
- 100 ns would then already give ZVS at 0 W.

The Co(tr) model is the conservative one.

### 2.8 Start-up and the split caps

| case (first 14 periods, secondary gates off = diode doubler) | I1 pk | I2 pk | channel pk Q19/Q7 |
|---|---|---|---|
| 140 kHz, 420V rail at 0 V | **10.1 A** | 9.1 A | 10.1 A |
| 140 kHz, 420V rail at 200 V | 8.2 A | 7.1 A | 8.2 A |
| 280 kHz, rail 0 V | 4.8 A | 4.3 A | 4.7 A |
| 420 kHz, rail 0 V | **3.2 A** | 2.8 A | 3.0 A |

- With the 420V bulk (C19 / C30 + load caps) empty, the secondary is a short through the
  diode doubler, so only Lsc limits the current. At 140 kHz the peak is 10 A, twice the
  STF7N60M2's 5 A continuous rating (20 A pulsed). Charging about 136 µF to 420 V takes
  ≈ 10 ms, and the conduction loss would be ≈ 40 W per primary switch for that time.
- **Soft-start: start at ≥ 3 × f (≈ 420 kHz, peak 3.2 A ≈ the 400 W peak) and sweep down to
  140 kHz as V420 rises.** (φ does not limit the current here.) Alternatively burst with a
  current limit. The ZVS of the primary holds during start-up (lagging current).
- **Split-cap imbalance:** C47 / C54 at +10 % / −10 % leave DHB_CAP at 218–220 V before
  switching starts (capacitive divider, no balancing resistors).
  - When switching starts at no load, the 20 V offset drives a magnetising DC transient of up to
    **0.79 A** (Im peak 1.9 A instead of 1.1 A). It decays through the 4.5 kHz split-cap / Lm
    mode in about 1 ms, with the midpoint back to 200 V.
  - Peak flux rises about 1.7×, to ≈ 0.16 T, which is fine against PC40 Bsat.
  - **But the first ≈ 10 periods after enabling are hard-switched**: the offset turns one edge per period
    against its partner's conducting body diode, with a channel peak of 45 A and a body-diode
    recovery current of 30 A at the first edge (9 µs after enabling). It is the same failure mode as 2.3.
    Cures: centre the midpoints before enabling (balancing resistors, below) and/or
    start at a high frequency.
  - Starting at a high frequency also reduces the offset transient (volt-seconds ∝ 1/f).

### 2.9 CFD7 check (2026-11-24)

**Scratch-run result, not reproduced by the scripts in this directory** (the device model in `dab_spice.py` is still
the STF7N60M2; updating it to the IPA60R280CFD7 and re-running is an open item, `next_prompt.md`,
`kicad_next/review/RESOLUTIONS.md`). A datasheet + SPICE check by another agent (2026-11-24) for the owner's change of
Q7 / Q8 / Q19 / Q21 to the Infineon **IPA60R280CFD7** (datasheet Rev. 2.2, 2020-01-30; STF7N60M2 from ST DocID024894
Rev 1, 2013):

| | STF7N60M2 | IPA60R280CFD7 |
|---|---|---|
| MOSFET dv/dt rating | 50 V/ns | **120 V/ns** |
| body-diode dv/dt rating | 15 V/ns | **70 V/ns** |
| Qrr | 1.55 µC | **0.29 µC** |
| RDS(on) max (25 °C) | 0.95 Ω | **0.28 Ω** |
| Co(tr) | 75.5 pF | 249 pF |
| Qg | 8.8 nC | 18 nC (VGS(th) 3.5–4.5 V, internal RG 11 Ω) |
| simulated DAB loss at 400 W | 11–12 W | 6.2–6.9 W |
| no-load primary current | 0.52 A rms | 0.84 A rms (at Lm 120 µH) |

The simulated switch-node slope stays at 62–81 V/ns peak (design figure ≈ 100 V/ns), so the review finding "slope
above the FET rating" (findings 02 F2 / 07 F2) is resolved by the rating, with 1.6–1.9× margin (120 V/ns). The price
is the 3.3× larger Co(tr): with Lm 200 µH and 150 ns the bridge hard-switches at light load. ZVS cases (bus mismatch
±5 %):

| FET, Lm, dead time | matched buses | +5 % | −5 % |
|---|---|---|---|
| STF7N60M2, 200 µH, 150 ns | soft | soft | hard at 40–109 W, 6.2 µJ |
| IPA60R280CFD7, 200 µH, 150 ns | hard at light load, 6.8 µJ | hard, 25 µJ | hard, 35 µJ |
| **IPA60R280CFD7, 120 µH, 200 ns** | **soft** | **soft** | hard only at 76–93 W, 0.3 µJ |
| IPA60R280CFD7, 120 µH, 150 ns | soft | partial (≤ 3.6 V) | hard at 14–111 W, 5.8 µJ |

Consequences: **Lm ≈ 120 µH** (tape spacer under all legs, ≈ 0.83 mm by `gap_for_lm`, tuned on the bench,
DAB_TRANSFORMER.md 4 / 6) and **200 ns dead time, not above 200 ns**; gate resistors unchanged. Not verified by that
check: no Infineon SPICE model (the Coss curve was synthesised from Co(tr), Eoss and Coss at 400 V), start-up and the
±2 % mismatch not re-run, STF7N60M2 data from the 2013 revision. Sections 2.1–2.8 and 3 are the STF7N60M2 results;
their Lm 200 µH / 150 ns recommendation is superseded by this section.

## 3. Recommendations

- **FPGA dead time: 150 ns total** (FPGA dead time 150 ns > UCC21520 DT 100 ns; the UCC21520 does
  not add the two – the larger one wins).
  - This gives ZVS over the full load range at matched voltage, with a 36 ns margin on the
    114 ns no-load swing.
  - 200 ns is acceptable and tolerates a ±2 % mismatch better. But the sending-side current
    then reverses before turn-on at 100–250 W (it relies on the body-diode Qrr).
  - **Do not use 250 ns**: only 0.2 A is left at 400 W.
  - 100 ns (DT alone) loses ZVS at light load.
  - Optional refinement: 150 ns below ≈ 150 W, 100 ns above.
  - With the recommended Lm ≈ 200 µH, 150 ns still applies; the no-load swing drops to 66 ns,
    which leaves margin for parts with a higher Coss.
- **Gap target: Lm ≈ 200 µH (−10 % / +5 %) instead of 300 µH.** *(Superseded 2026-11-24 by 2.9: CFD7 FETs, Lm ≈ 120 µH by a tape spacer, 200 ns.)* In DAB_TRANSFORMER.md 4 terms that
  is the "100 ns" column for option B (197 µH): a **centre-leg grind of ≈ 0.68 mm** (or a 0.34 mm
  spacer under all legs) instead of 0.34–0.35 mm.
  - With TIW litz, 0.66–0.70 mm; set it by measuring Lm, as in DAB_TRANSFORMER.md 6 step 3.
  - Benefits: ZVS at matched voltage with DT ≥ 100 ns; no hard switching at +5 %; small
    (≤ 6 µJ) edges in a 30–110 W window at −5 % (2.4).
  - Cost: +0.5 W at 400 W, +0.3 W at no load, φ +0.4°. The leakage changes by < 1 %; the
    fringing loss of the larger gap was negligible at 0.6 mm in DAB_TRANSFORMER.md 4 (option A).
  - 300 µH (the present 0.34 mm) works only if the two bus voltages track within about ±1 % at
    light load. 400 µH is worse in every respect except a negligible copper saving.
- **Firmware, more important than the gap:**
  1. At light load (< ≈ 150 W), keep V(420V) / V(DC+) close to 21/20 by setting the PFC setpoint
     from V420 (or the 420 V setpoint): within ±1 % with Lm 300 µH, within about ±3 % with
     200 µH. Use **burst mode** (packets at ≥ 150 W) if the mismatch can be larger.
     (DC+ 100 Hz ripple scales with power, so it is small exactly where this matters.)
  2. The power loop must handle φ(0 W) ≈ −0.8° and the steep P(φ) around zero.
  3. **Soft-start by frequency** (≥ 420 kHz → 140 kHz) while the 420V rail charges.
  4. Use the DHB_I average for power and current limiting. It does not see the transformer
     peak current.
- **Schematic changes: none required. Recommended (small) – not done here, kicad_next untouched:**
  - **Balancing resistors across each split cap** (C47, C54, C16, C55: 2 × 220 kΩ 1206 in
    series per cap, 0.09 W).
    - They centre DHB_CAP / TRANS_SEC at Vdc/2 before the first pulse: τ = 220 kΩ × 2 µF ≈ 0.45 s
      for the pair, so wait ≥ 2 s after DC+ / 420V settle before enabling.
    - This removes the hard-switched first periods of 2.8.
  - The DHB shunt compensation (C63 / C122 12 p) stays as is; bench-tune it.
  - The MOSFET R_on (3.4 W per sending switch) is worth a look in the thermal design.

## 4. Heater LLC (Q10 / Q11 IPD60R280P7S): not simulated, data missing

Sheet 06 (5.2):
- Q11 (high) / Q10 (low) half bridge on DC+ with the R30 shunt and UCC21520 DRV3 (DT 100 ns).
  Gate 10 Ω on, 3.3 Ω + ZLLS400 off.
- Resonant capacitor C42 + C49 (DC+ side) and C41 + C22 (return side): 5.2 **4 × 3.3 nF C0G = 13.2 nF** (from 2026-11-23,
  CHANGES 2.9); 5.1 had 4 × 4.7 nF X7R (18.8 nF nominal, about 12.5 nF at the 200 V bias).
- TR2 EF25 with a centre-tapped secondary to 6V3, synchronous rectifiers Q1 / Q2 (BUK9Y15-60E)
  driven by DRV4 from EPWM5A/6A.
- There is no separate resonant inductor, so the TR2 leakage is Lr.

**The risk:**
- P7 has a standard body diode (Qrr in the µC range, as here).
- Hard commutation happens when the LLC runs below resonance (capacitive mode). That occurs
  - at overload, and in particular with **cold heaters**: filament resistance is about 1/5–1/10
    of hot, so the inrush overloads the converter;
  - at the first pulses of start-up, with the resonant cap not yet at its operating point;
  - in a short circuit.
- In capacitive mode the incoming switch turns on into the partner's conducting body diode,
  which is the same recovery event as the 30–40 µJ edges in 2.3, but at higher current.

**Data needed for a simulation:**
1. TR2 turns (Np : Ns : Ns), Lm, and leakage measured from the primary (secondary shorted),
   plus winding capacitance.
2. Heater load: tubes and total 6.3 V current, cold-to-hot resistance ratio, whether the
   heaters are switched in steps.
3. Operating frequency range and control law (EPWM5A/6A), firmware dead time, soft-start
   sequence, overcurrent action.
4. The type and tolerance of C22 / C41 / C42 / C49.

**Until then:**
- The firmware should start the LLC well above resonance (≥ 2 × fr) and sweep down.
- Raise the frequency on overcurrent.
- Check the sign of HEATER_I at each switching edge: current not lagging means capacitive mode,
  so raise f immediately.
- If capacitive operation cannot be excluded, the fast-diode IPD60R360PFD7S (NR 5.4) is the
  safer part.

## 5. Caveats

- MOSFET model from the datasheet, not ST's SPICE model: Coss / Crss fitted, diode recovery by
  a simple transit-time model with no snappiness. The hard-switching energies (2.3) are
  indicative (±50 %). Whether they occur is not in doubt.
- Leakage ±(10…30) % (DAB_TRANSFORMER.md 7) moves φ in proportion. ZVS at full load is robust to
  that; the light-load results scale with Lm / Lsc.
- Layout parasitics are lumped (10 pF per node, nH loops). R_on is fixed at 75 °C.
- 420V is a constant-voltage load. With a resistive load the operating points are the same
  (the steady state is defined by V1, V2 and P).

