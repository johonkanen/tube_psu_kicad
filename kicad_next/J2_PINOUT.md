# J2 control-card header (2 × 25, 1.27 mm) – tube_power 5.2 pin use

Generated from the 5.2 schematic netlist (kicad-cli, 2026-11-20); the FPGA ball / card pin name is the
5.1 PDF name in `tools/next/sheets/sheet04.py` `J2_PINS`. The user confirmed 2026-11-20 that the
ball-named pins are unused on the control card.

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
| 4 | A11 | PRI_DHB_HI | DRV5.2, R73.2 |
| 5 | A13 | EPWM5A | DRV3.1, R78.2 |
| 6 | B12 | B12 | DRV5.1, R74.2 |
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
| 18 | F16 | DAB_DIS | C120.1, DRV5.5, ISO2.4, R129.1 |
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
