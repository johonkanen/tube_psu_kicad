# J2 control-card header (2 × 25, 1.27 mm) – tube_power 5.2 pin use

Generated from the 5.2 schematic netlist (kicad-cli, 2026-11-20); the FPGA ball / card pin name is the
5.1 PDF name in `tools/next/sheets/sheet04.py` `J2_PINS`. The user confirmed 2026-11-20 that the
ball-named pins are unused on the control card.

## Firmware constants and bring-up cautions (5.2)

Collected 2026-11-24 from the design review (kicad_next/review/findings, RESOLUTIONS.md) and the owner decisions of
that day. All analog channels are referred to **+1V65_BIAS ≈ 1.642 V** (1.6554 V divider − 13.6 mV over R131;
±14 mV tolerance, common to all channels: calibrate the zero at start-up); usable ADC input 0.04–3.26 V.

| Channel (J2, card ADC) | 5.2 scale | 5.1 / earlier value | Range (from the bias) | Source |
|---|---|---|---|---|
| VAC_MEAS (J2-47, ADB1) | **0.004 V/V** (4.0072 mV/V simulated) | 0.005 V/V | ≈ ±400 V peak (clips at ≈ 400 V peak = 283 Vrms) | R49 / R80 12k (CHANGES 4.3), findings 09 F1 |
| DC_LINK_MEAS (J2-41, ADB4) | 0.0050 V/V | unchanged | full scale ≈ 652 V | FINDINGS 11.1 / 11.2 |
| AUX_MEAS (J2-43, ADB3) | 0.17603 V/V | 5.1 unbuffered | full scale ≈ 18.5 V | FINDINGS 11.1 |
| 5V_MEAS (J2-49, ADB0) | 0.4000 V/V | new | full scale ≈ 8.15 V | CHANGES 4b |
| PFC_I1 / PFC_I2 (J2-42 ADA4 / J2-44 ADA3) | **9.71 A/V** (103.0 mV/A) | 12.13 A/V (4 mΩ) | −15.6 / +15.7 A | 5 mΩ shunts R93 / R21, CHANGES 6.2 |
| DHB_I (J2-38, ADA6) | **4.40 A/V** (227.1 mV/A) | 5.50 A/V (4 mΩ) | −7.1 / +7.1 A | 5 mΩ shunt R83, CHANGES 6.2 |
| HEATER_I (J2-45, ADB2) | **2.00 A/V** (499.2 mV/A) | 2.50 A/V (4 mΩ) | −3.2 / +3.2 A | 5 mΩ shunt R30, CHANGES 6.2 |

- **Current channels:** LMH6643 offset up to 7 mV over temperature = 1.4 A input-referred on every current channel
  (5 mΩ): zero-current calibration at start-up is required (ranges after an uncalibrated worst-case offset ±14.1 /
  ±5.6 / ±1.8 A). The ESL compensation caps were sized for 4 mΩ and over-compensate by about 25 % with 5 mΩ: tune on
  the bench (slow over/undershoot = C too large). **HEATER_I** is a Kelvin tap at the shunt R30 since stage 14a (the
  5.1 / early-5.2 tap at the Q10 source via read 12.5 mm of power track); its 0.16–0.18 % gain error is a calibration
  item. Check the PFC range against the low-line DCM peak and the heater range against the LLC primary peak.
- **DAB (Q7 / Q8 / Q19 / Q21 = IPA60R280CFD7 since 2026-11-24):** dead time **200 ns total, not above 200 ns** (was
  150 ns with the STF7N60M2); the UCC21520 DT of 100 ns is a hardware minimum, not added. TR3 Lm starts at ≈ 120 µH
  (tape spacer), tuned on the bench for soft switching at light load. **Re-measure the zero-power phase offset and the
  loop gain** (the larger Co(tr) and lower Lm change both). Light load: keep V(420V) / V(DC+) ≈ 21 / 20 (NEXT_REVISION
  2.7).
- **DAB_DIS = J2-18 → card J1-17 = Ti60 ball R3** (card net J1_P17, direct HVIO; weak pull-up 25–67 kΩ during
  configuration against R129 10k pull-down on the board). The "F16" in the pin table above and the "D15" of older notes
  are the 5.1 PDF names, not the card ball (findings 04 F3). High = all four DAB gates off.
- **Heater LLC:** resonant capacitors **13.2 nF C0G** (4 × 3.3 nF, no bias / temperature drift; 5.1 had about 12.5 nF of
  biased X7R). **Synchronous-rectifier conduction window: start at ≤ 2.2 µs and lengthen** while watching the secondary
  current, to just before it reverses. The 5.1 value 2.65 µs is right only if the operating leakage of TR2 is
  ≈ 59 µH (half period 2.69–2.77 µs); with 42 µH the half period is 2.34 µs and 2.65 µs would leave the SR on after the
  current reverses (drain overshoot on Q1 / Q2). Measure TR2 leakage both ways first (simulation/llc/TR2_OPENMAGNETICS.md).
  The minimum frequency may have to go down to **≈ 130 kHz** (FHA: ≈ 137–159 kHz needed at 380–400 V with the higher
  leakage; the ZVS boundary is at 73–90 kHz); keep the 270 kHz start (findings 06 F2).
- **5V_MEAS** time constant 0.6 ms (6 kΩ × 100 nF); **AUX** divider filter C61 = 100 nF (findings 09 F4).
- **J4 (UART, isolated by U11):** pin 6 must be the far end's 3.3 V I/O supply and always connected (findings 04 F6).

## Free pins (12) – not connected on the 5.2 board

| J2 pin | Card pin / ball | Note |
|---|---|---|
| 20 | G15 | spare FPGA I/O |
| 21 | K16 | spare FPGA I/O |
| 22 | J16 | net name EPWM1A since 5.1 (a PWM-capable pin on the card); unconnected on the 5.1 board too |
| 23 | L16 | spare FPGA I/O |
| 25 | N14 | spare FPGA I/O |
| 27 | N15 | spare FPGA I/O |
| 28 | N16 | spare FPGA I/O |
| 29 | P15 | spare FPGA I/O |
| 30 | P16 | spare FPGA I/O |
| 31 | T15 | spare FPGA I/O |
| 32 | R16 | spare FPGA I/O |
| 34 | T14 | spare FPGA I/O |

## Spare ADC inputs tied to GND on the board (6)

Free analog channels of the card; the 5.2 board grounds them (NR 4b). Usable later by cutting the GND
connection at the pin and routing a signal there.

| J2 pin | Card ADC input |
|---|---|
| 37 | ADB6 |
| 39 | ADB5 |
| 40 | ADA5 |
| 46 | ADA2 |
| 48 | ADA1 |
| 50 | ADA0 |

## All pins

| J2 pin | Card pin / ball | 5.2 net | Board connections |
|---|---|---|---|
| 1 | DGND | GND | power / ground |
| 2 | 5V | 5V | power / ground |
| 3 | A12 | EPWM6A | DRV3.2, R77.2 |
| 4 | A11 | PRI_DHB_HI | DRV5.1, R73.2 |
| 5 | A13 | EPWM5A | DRV3.1, R78.2 |
| 6 | B12 | B12 | DRV5.2, R74.2 |
| 7 | A14 | $HT_CS | ISO1.5 |
| 8 | B13 | $CUK_CS | ISO2.5 |
| 9 | A15 | SYNCH_2 | ISO1.4 |
| 10 | B14 | EPWM2A | ISO2.2 |
| 11 | C15 | HT_SDATA | ISO1.7 |
| 12 | B16 | EPWM2B | ISO2.3 |
| 13 | D16 | SYNCH_1 | ISO1.3 |
| 14 | C16 | CUK_CLK | ISO2.6 |
| 15 | F15 | HT_CLK | ISO1.6 |
| 16 | D15 | CUK_SDATA | ISO2.7 |
| 17 | G16 | GPIO_BYPASS_RLY | R32.1, R44.2 |
| 18 | F16 (5.1 PDF name; card: J1-17 → ball R3) | DAB_DIS | C120.1, DRV5.5, ISO2.4, R129.1 |
| 19 | J15 | PFC_PWM1 | DRV1.6, R71.2 |
| 20 | G15 | G15 | **free** |
| 21 | K16 | K16 | **free** |
| 22 | J16 | EPWM1A | **free** |
| 23 | L16 | L16 | **free** |
| 24 | K15 | RX | U11.5 |
| 25 | N14 | N14 | **free** |
| 26 | L15 | TX | U11.4 |
| 27 | N15 | N15 | **free** |
| 28 | N16 | N16 | **free** |
| 29 | P15 | P15 | **free** |
| 30 | P16 | P16 | **free** |
| 31 | T15 | T15 | **free** |
| 32 | R16 | R16 | **free** |
| 33 | T13 | PFC_PWM2 | DRV2.6, R69.2 |
| 34 | T14 | T14 | **free** |
| 35 | DGND | GND | power / ground |
| 36 | DGND | GND | power / ground |
| 37 | ADB6 | GND | power / ground |
| 38 | ADA6 | DHB_I_MEAS | C26.2, R42.2 |
| 39 | ADB5 | GND | power / ground |
| 40 | ADA5 | GND | power / ground |
| 41 | ADB4 | DC_LINK_MEAS | R2.1 |
| 42 | ADA4 | PFC_I1_MEAS | C88.1, R96.1 |
| 43 | ADB3 | AUX_MEAS | R132.2 |
| 44 | ADA3 | PFC_I2_MEAS | C77.1, R61.1 |
| 45 | ADB2 | HEATER_I_MEAS | C10.2, R35.2 |
| 46 | ADA2 | GND | power / ground |
| 47 | ADB1 | VAC_MEAS | R65.1 |
| 48 | ADA1 | GND | power / ground |
| 49 | ADB0 | 5V_MEAS | R135.2 |
| 50 | ADA0 | GND | power / ground |
