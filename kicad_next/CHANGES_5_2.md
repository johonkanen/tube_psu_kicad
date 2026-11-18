# tube_power 5.2 – schematic changes (phase 2)

Phase 2 of [../NEXT_REVISION_PLAN.md](../NEXT_REVISION_PLAN.md), 2026-11-18. Every change is a script edit in
`tools/next/` (sheets, `gen_symbols.py`, `setup_project.py`) plus the hand-maintained tables
`lib/part_map_next.csv` (values), `lib/footprint_map_next.csv`, `lib/jlc_parts_next.csv` (LCSC per refdes,
JLC parts API 2026-11-18). The 5.1 migration (`kicad/`, `tools/sheets/`, 5.1 `lib/` files) is unchanged.
Checks: `tools/next/check_next.sh` (ERC 0 errors, every net in one isolation domain, 19 rule tests,
netlist / CSV check). The generated netlist diff 5.1 → 5.2 is at the end of this file
(`python3 tools/next/netlist_diff.py --update`).

New refdes (next free numbers of 5.1): R125–R137, C118–C137, D35, U9–U12. Removed: DRV9, L3, R40, R25, C4.

## 1. Auxiliary flyback (sheet 1)

| NR | Done | Refdes / value / nets |
|---|---|---|
| 1.1 | yes | TR1 → symbol `EEL19_4P6` (value `EEL19_4+6 Lp600u`): 1 = A15 → D5 (15V), 2 = GND, 3 = A5 → D6 / AUX_FB, 11 FL_DC = DC+, 12 FL_C = collector (net renamed **FLY_C**), 5 SHV → D8 (−100V BIAS), 7 S5 → D29 (5V_ISOL), 8 SN5 → D14 (−5V_SEC), 9 ISO_GND, 10 S15 → D4 (15V_ISO_SEC); bobbin pins 4 / 6 clipped (no symbol pin) – EEL19_DESIGN.md 6a |
| 1.2 | yes | footprint `tube_psu_next:Transformer_EEL19_V_4+6_FlyLeads` (pads 1,2,3,5,7–10, 11/12 fly leads) |
| 1.3 / 1.4 | layout | phase 5 |
| 1.5 | yes | PWM2 → **iW1819-00** (symbol `IW1819`, Renesas datasheet Rev. 1.5): 1 VSENSE, 2 VCC, 3 + 8 GND, 4 NC (floating), 5 + 6 C (= FLY_C), 7 E shorted to 9 ISENSE (R8 ‖ R9 to GND), 10 ASU not used (no-connect; resistor start-up R114–R116 as in 5.1). Footprint `tube_psu_next_parts:SOIC-10_Batwing_iW1819` (new generator `tools/next/gen_next_footprints_parts.py`, land pattern after the LCSC/EasyEDA pattern of C17225733 – the datasheet has no outline). JLC C17225733: 0 stock → **consigned** |
| 1.5 recheck | yes | iW1819 vs the 5.1 network: VSENSE nominal 1.536 V / OVP 1.838 V and ISENSE 1.00 V (regulation limit) / OCP 1.15 V are the IW1818 values the 5.1 notes use → feedback divider R64 39k ‖ R81 15k / R86 1k / R84 33k ‖ R85 4.7k ‖ C50 unchanged (NR 1.12). VCC: start-up 13.5–15.5 V (typ 14.5), UVLO 4.4 V, max operating 20 V → 15V rail via D10 gives ≈ 14.6 V in operation (the 15V rail must stay below ≈ 20 V at light load – preload R125 helps); start-up 3 × 1M from DC+ ≈ 0.13 mA against 1.6 µA start-up current, C58 + C51 9.4 µF → ≈ 1 s as in 5.1 |
| 1.6 | yes | R8, R9 2.49R → **2.0R** 1206 1 % (Rsense 1.0 Ω: Ipk 1.0 A, OCP 1.15 A) – C17942 |
| 1.7 | yes | **R125 2.2k 1206** 15V–GND, **R126 1k 0805** 5V–GND |
| 1.8 | yes | R124 12.1k → **2.61k** 1206 (C245506, stock 75 – low) |
| 1.9 | yes | D8 value ES1A → **US1M** (1000 V, C412437) |
| 1.10 | yes | D4, D5 → **ES1D** (200 V); also D6, D14, D29 value ES1A → ES1D (the 5.1 JLC choice; stale schematic value) |
| 1.11 | open | ripple-current check of C1, C2, C6, C36, C71, C114, C115 at 15 W (no part change) |
| C102 | yes | value → `56u 250V` (Ymin KCXE 56 µF 250 V D10, ≥ 160 V) |

## 2. DAB transformer (sheet 7)

| NR | Done | Refdes / value / nets |
|---|---|---|
| 2.1 | yes | TR3 → symbol `EC42_2CH`, value `EC42/15 2CH 20:21` (option B, D1): 1 + 2 primary start = **DHB_CAP**, 7 + 8 primary finish = DHB_HI_SOURCE, 9 + 10 secondary start = TRANS_SEC, 15 + 16 secondary finish = DHB_HI_SOURCE_SEC (DAB_TRANSFORMER.md 5) |
| 2.2 | yes | footprint `tube_psu_next:Transformer_EC42x15_2Slot_2x8_P5mm` |
| 2.4 | yes | **L3 removed** (no jumper position: the leakage is the series L; the net TRANS_PRI disappears) |
| 2.3 / 2.5 / 2.6 | layout | C47 / C54 at the TR3 primary pins (note on the sheet), phase 5 |
| 2.7 | firmware | dead time 150–200 ns (note on sheets 2 / 7) |

## 3. Gate drivers (sheets 2, 6, 9) – NR 3, 3a

| NR | Done | Refdes / value / nets |
|---|---|---|
| 3.1 / 3a | yes | DRV5, DRV6 Si8275BB → **UCC21520DWR** (C601651, SOIC-16W, 5.7 kVrms reinforced, 8 V UVLO). Same pin positions as the Si8275, so the connections are those of 5.1: INA / INB from B12 / PRI_DHB_HI (DRV5) and ISO_SEC_DHB_HI / LO (DRV6), bootstrap D19/R41/C92 and D18/R46/C46 unchanged |
| 3.2 | yes | **R40, R25 removed**. New DT resistors **R127 / R128 10k** (DT = 10 ns/kΩ → 100 ns hardware minimum below the 150–200 ns FPGA dead time) with **C118 / C119 100p** (datasheet: ≤ 1 nF noise cap) |
| 3.3 | yes | DISABLE brought out: DRV5 pin 5 = **DAB_DIS** from **J2-18** (spare FPGA pin, ball D15 on the card; 5.1 single-pin net F16), **R129 10k** pull-down (enabled when not driven, as 5.1's EN tied high), **C120 1n**; DRV6 pin 5 = **DAB_DIS_SEC** from **ISO2 channel C** (pin 4 input, was GND; pin 13 output, was unused) |
| 3a DRV6 input side | decision | **kept on the secondary** (5V_ISOL / ISO_GND, PWM through ISO2 as in 5.1). Moving it to the primary would free two ISO2 channels but put a second reinforced barrier crossing (the driver itself) next to TR3 and change the ISO2 / 5V_ISOL wiring – no simplification of the barrier; one UCC21520 cell for all three bridges either way |
| 3a heater | yes | DRV3 (Si8271) + DRV9 (IXDD609) → **one UCC21520DWR = DRV3**: INA = EPWM5A (R78) → OUTA → HEATER_HI_DRV, bootstrap D11 / R99 / C25 from 15V on VDDA / VSSA = HEATER_HI_SOURCE; INB = EPWM6A (R77) → OUTB → HEATER_LOW_DRV, VDDB 15V (C52, C18), VSSB GND; VCCI 5V (C53); DISABLE tied to GND; DT **R130 10k + C121 100p**. Gate networks: HEATER_HI_DRV → R24 10R (on) ‖ R59 3.3R + **D35 ZLLS400TA** (off) → HEATER_HI_GATE; HEATER_LOW_DRV → R37 10R ‖ R31 3.3R + D33 → HEATER_LOW_GATE (R66 pull-down). **DRV9 removed** |
| 3a | yes | DRV1, DRV2 IXDD609 → **UCC27511ADBVR** (C2676982, SOT-23-6): VDD 15V (C79 / C80), IN+ = PFC_PWM1/2 (R71 / R69), IN− GND, OUTH → R14 / R20 (turn-on), OUTL → R1 / R19 (turn-off) → GATE1/2 (R43 / R7 pull-down) |
| 3a | yes | DRV4 IXDD604 → **UCC27524ADR** (C185857, SOIC-8): VDD / ENA / ENB 6V3, INA EPWM6A_ISO, INB EPWM5A_ISO, OUTA → R63, OUTB → R28, GND HT_GND |
| 3a | yes | ISO1, ISO2 → **CA-IS3761LW** (C528659): pinout **checked identical** to the Si8661 (1 VDDA, 2–6 inputs, 7 output, 8 GNDA, 9 GNDB, 10 input, 11–15 outputs, 16 VDDB), default low, VIOWM 1000 Vrms / VIOTM 7070 Vpk (WB); footprint → KiCad `SOIC-16W_7.5x10.3mm_P1.27mm` |

## 3b. Isolated serial port (sheet 4)

| NR | Done | Refdes / value / nets |
|---|---|---|
| 3b.1 | yes, part changed | **U11 = CA-IS3721HW** (C5337993, symbol `SI8621`). **Si8621BD is default-LOW** (Skyworks ordering guide: Bx = low, Ex = high), so with no cable the FPGA RX would read a break; the default-high Si8621**ED** has 0 JLC stock, the Chipanalog CA-IS3721HW has the **same WB SOIC-16 pinout** (1/7 GND1, 3 VDD1, 4 A1 in → 13 B1 out, 12 B2 in → 5 A2 out, 9/16 GND2, 14 VDD2) and default-high outputs, 1358 pcs. Side 1: +3V3 / GND, A1 ← **TX** (J2-26), A2 → **RX** (J2-24), C134 100n; side 2: UART_3V3 / ISO_UART_GND, C135 100n |
| 3b.2 | yes | **J4 → 1×6 2.54 mm FTDI header** (C492405): 1 ISO_UART_GND, 2 CTS n.c., 3 **UART_5V**, 4 TXD → **R136 47R** → B2, 5 RXD ← **R137 47R** ← B1, 6 RTS n.c. |
| 3b.3 | yes | **U12 XC6206P332MR** (C5446, SOT-23) UART_5V → UART_3V3, **C136 / C137 1µ** |
| 3b.4 | rules | new domain **UART** (ground ISO_UART_GND, barrier U11) in `setup_project.py`: nets ISO_UART_GND, UART_5V, UART_3V3, UART_TXD, UART_RXD, U11-B1/B2, unconnected U11 / J4 pins → class **UART_ISO** (12 nets); rules PRI-UART 8.0 mm / SEC-UART 8.4 mm / HEATER-UART 1.0 mm were already in the `.kicad_dru`, now tested by 4 new cases in `check_rules.py` (19/19 pass). Layout (slot under U11, island keep-out) phase 5 |

## 4. Measurements (sheets 4, 8, 9, 10)

| NR | Done | Refdes / value / nets |
|---|---|---|
| 4.1 | yes | **U9 TLV316** follower: REF1 → R110 **1.00k** / R3 **1.96k** divider (1.655 V unloaded) + **C128 100n** → U9 + input; output → **R131 22R** → +1V65_BIAS with C48 100n on the bias node; feedback from the op-amp output (before the 22R, stability with C48); **C129** decoupling. The DC drop over R131 (≈ 0.6 mA of bias loads → ≈ 13 mV) is common to all channels (zero calibration) |
| 4.2 | yes | **C126 / C127 1n C0G** across R80 / R49 (U8 VAC), no output cap |
| 4.3 | yes | R49, R80 15k → **12k** (gain 0.004, pole 13.3 kHz) |
| 4.4 | yes | **C130 / C131 1n C0G** across R17 / R82 (U6 DC_LINK), **R2 1k → 100R**, **C4 removed** |
| 4.5 / 4c.2 | yes | AUX_MEAS **buffered**: R11 22k / R12 4.7k with **C61 1n → 100n** → **U10A** (TLV9062IDGKR, C398356) → **R132 100R** → AUX_MEAS |
| 4.6 | yes | U1 decoupling **C124 100n + C125 1u** at pin 8 |
| 4.7 | yes | C10 / C26 stay unfitted (value `na`) |
| 4.8 | yes | REF1 value → **REF3325AIDBZR** (2.5 V, C69039; same SOT-23 pinout 1 IN / 2 OUT / 3 GND as the ISL21010, i.e. the Proteus-numbered footprint stays). The 5.1 value ISL21010CFH315Z is the 1.5 V part; the fitted part (simulation: 2.56 V source) made 1.65 V only with the bias loads – with the buffer the divider was re-sized. ISL21010CFH325Z (2.5 V) has 0 JLC stock |
| 4.9 | firmware | HEATER_I gain calibration, AD2 bandwidth (no change) |
| 4.10b | yes | U1, U4 → **LMH6643** (symbol `LMH6643`, same dual pinout and TSSOP/VSSOP-8 footprint) |
| 4.11 | yes | balanced legs, τ = Rfb·C ≈ L/R (125–200 ns): DHB **C63 20p → 12p** + **C122 12p** (+ input to +1V65_BIAS) = 180 ns; HEATER **C11 20p → 5.6p** + **C123 5.6p** = 185 ns; PFC C113/C106, C112/C107 20p unchanged (6.8k·20p = 136 ns, already both legs). Start values – bench-tune; LMH6643 Vos (≤ 5 mV = 1.25 A) → zero-current calibration in firmware (note on sheet 8) |
| 4b | yes | J2 map: **PFC_I1 → J2-42** (ADA4), **DHB_I → J2-38** (ADA6), **AUX → J2-43** (ADB3), **5V_MEAS → J2-49** (ADB0); spare analog **J2-37/39/40/46/48/50 → GND** (NR 4c.3); the 5.1 single-pin nets CUK_CAP_MEAS_RAW, HEATER_CAP_AD_MEAS, ADA0/1/2/4 are gone. Control card / firmware channel map to update (ADA4 = PFC_I1, ADA6 = DHB_I, ADB3 = AUX, ADB0 = 5V) |
| 4b 5V_MEAS | yes | **R133 15k 0.1 % / R134 10k 0.1 %** from 5V, **C132 100n** across R134 → **U10B** → **R135 100R** → 5V_MEAS; U10 decoupling **C133** |

## 5. General

| NR | Done | Refdes / value / nets |
|---|---|---|
| 5.2 | partly | L1, L2 → symbol `L_TOROID` (two leads; 5.1 RM8 pri1 / pri2 = 1 / 2), value **`TBD (measured)`**, **no footprint** (RM8 dropped; toroid footprint after measuring: phase 3). PFC drain nodes named **PFC_DRAIN_1 / PFC_DRAIN_2** |
| 5.2b | yes | C28 / C29 / C37 / C56 value `82u 450V` (Man Yue ERT826M2WI45RRS0F-R C51890374), C19 / C30 **39u → 68u** (Ymin KCXE5002W680MF C913388, stock 103), C102 (see 1) |
| 5.4 | yes | Q10, Q11 → **IPD60R280P7S** DPAK (C536813), footprint `Package_TO_SOT_SMD:TO-252-2` (1 G, 2 D tab, 3 S = the Q_NMOS_GDS pins) |
| 5.5 | layout | heatsink / bracket – phase 5 |
| 5.6 | yes | 100 nF on DC+ / 420V / −100V BIAS: **C15, C20, C45, C67, C70, C89, C90, C91, C99, C100, C101 → 1210 630 V** (FM32X104K631EGG C692295); C73 (2.2 µF 450 V 2220 on DC+) kept – no 2.2 µF ≥ 630 V in 1210 / 1812 |
| 5.6 others | partly | DRV1/2/3/4/5/6/9 solved by 3a; ISO1/2 by CA-IS3761LW; PWM2 iW1819 consigned; Q5/Q6, Q7/8/19/21, SICD1/2, DB1, R27, shunts, transformers, L1/L2 still consigned / missing as in `lib/jlc_parts_next.csv` |
| title | yes | root and sub-sheet title blocks rev **V5.2** (`gen_schematic.py` ROOT_EDITS, `_common.sheet()`) |

## Isolation domains after phase 2

`setup_project.py`: 224 nets – SIGNAL 105, PRIMARY_LV 5, HV_PRIMARY 39, SECONDARY_LV 28, HV_SECONDARY 12,
HEATER 22, UART_ISO 12, PE_EARTH 1. Barrier parts: TR1, TR2, TR3, ISO1, ISO2, **U11**. No other part bridges two
domains (the UCC21520s have both sides in one domain). HV_NETS updated for the renamed nets (FLY_C,
PFC_DRAIN_1/2, HEATER_HI_DRV, Net-(D35-K), Net-(DRV3-VDDA); TRANS_PRI removed).

## Open questions / to check

1. **iW1819 footprint**: the Renesas datasheet has no package drawing; the batwing land pattern follows LCSC/EasyEDA
   (C17225733). Confirm against the Renesas outline (phase 3). HV–LV pin spacing 1.47 mm (datasheet 10.16.1) –
   slot if needed. JLC: 0 stock → consign (DigiKey / Mouser).
2. **CA-IS3761LW / CA-IS3721HW reinforced rating**: the CA-IS376x datasheet (2019) lists VDE / UL / CQC as
   "pending" – get the current certificates (VIOWM vs the 552 Vrms ISO2 barrier). Both are default-low (3761L) /
   default-high (3721H) as intended: ISO1/ISO2 outputs low when the primary is unpowered (PWM off, DIS low, ADC CS
   low = harmless).
3. **UART isolator part**: Si8621BD (asked for) is default-low → used CA-IS3721HW (default-high, same pinout).
   Alternative: Si8621ED-B-IS (default-high, 0 JLC stock → consign). Confirm.
4. **DAB_DIS default**: pull-down = drivers enabled when the FPGA does not drive J2-18 (as 5.1). A pull-up (disabled
   until the FPGA enables) is the fail-safe alternative – needs firmware to drive it low. Control-card pin D15
   (power-board J2-18) to be assigned in the card's pin table.
5. **Dead time**: UCC21520 DT 100 ns is a hardware minimum – the FPGA dead time (DAB 150–200 ns, heater LLC) must
   stay above it, else DT sets the dead time.
6. **Bias buffer stability**: U9 (TLV316) with 22R + 100 nF, feedback from the op-amp output – check with the vendor
   model in phase 4; the 22R drop (≈ 13 mV) shifts the bias of all channels equally.
7. **ESL caps** 12p / 5.6p are calculated start values (τ ≈ 180 ns ↔ 0.72 nH at 4 mΩ); HEATER at noise gain 101 is
   limited by the LMH6643 (≈ 0.56 MHz), tune on the bench. If the shunts become 5 mΩ (KRL2012E, NR 5.6) rescale.
8. **L1 / L2**: value and footprint after measuring the toroids (NR 5.2, phase 3).
9. **Q10 / Q11 P7** standard body diode – LLC start-up / overload commutation in the phase-4 simulation (NR 5.4).
10. **C73** (2.2 µF 450 V X6S 2220 on DC+) left as is (NR 5.6 asks for ≥ 630 V; no stocked 2.2 µF part).
11. **R124 2.61k** low JLC stock (75 / 43 pcs).
12. **R99 pin orientation** changed by the shared driver cell (pin 1 now at D11) – electrically identical.
13. Phase-1 findings still open: slots under the SOIC-16W isolators (ISO1, ISO2, U11) and the EEL19 TR1 row
    spacing vs 11.1 mm creepage (phase 3/5).

## Netlist diff 5.1 → 5.2 (generated)

Reviewed against the items above: every difference is one of the listed changes (pin-number changes of
re-symbolled parts – PWM2, DRV1–DRV4, TR1, TR3, J4, L1/L2 – show as + / − pins of the same net).

<!-- netlist_diff.py begin -->
Parts: 5.1 315, 5.2 348; removed 5, added 38.

**Removed parts:** C4 (1n), DRV9 (IXDD609D2TR), L3 (70u), R25 (82k), R40 (82k)

**Added parts:** C118 (100p), C119 (100p), C120 (1n), C121 (100p), C122 (12p), C123 (5.6p), C124 (100n), C125 (1u), C126 (1n), C127 (1n), C128 (100n), C129 (100n), C130 (1n), C131 (1n), C132 (100n), C133 (100n), C134 (100n), C135 (100n), C136 (1u), C137 (1u), D35 (ZLLS400TA), R125 (2.2k), R126 (1k), R127 (10k), R128 (10k), R129 (10k), R130 (10k), R131 (22R), R132 (100R), R133 (15k 0.1%), R134 (10k 0.1%), R135 (100R), R136 (47R), R137 (47R), U9 (TLV316IDBVR), U10 (TLV9062IDGKR), U11 (CA-IS3721HW), U12 (XC6206P332MR)

**Changed parts** (value / symbol / footprint, 5.1 -> 5.2):

| Ref | Value | Symbol | Footprint |
|---|---|---|---|
| C11 | 20p -> 5.6p |  |  |
| C15 |  |  | Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder -> Capacitor_SMD:C_1210_3225Metric |
| C19 | 39u -> 68u |  |  |
| C20 |  |  | Capacitor_SMD:C_1206_3216Metric -> Capacitor_SMD:C_1210_3225Metric |
| C28 | 82u -> 82u 450V |  |  |
| C29 | 82u -> 82u 450V |  |  |
| C30 | 39u -> 68u |  |  |
| C37 | 82u -> 82u 450V |  |  |
| C45 |  |  | Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder -> Capacitor_SMD:C_1210_3225Metric |
| C56 | 82u -> 82u 450V |  |  |
| C61 | 1n -> 100n |  |  |
| C63 | 20p -> 12p |  |  |
| C67 |  |  | Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder -> Capacitor_SMD:C_1210_3225Metric |
| C70 |  |  | Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder -> Capacitor_SMD:C_1210_3225Metric |
| C89 |  |  | Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder -> Capacitor_SMD:C_1210_3225Metric |
| C90 |  |  | Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder -> Capacitor_SMD:C_1210_3225Metric |
| C91 |  |  | Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder -> Capacitor_SMD:C_1210_3225Metric |
| C99 |  |  | Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder -> Capacitor_SMD:C_1210_3225Metric |
| C100 |  |  | Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder -> Capacitor_SMD:C_1210_3225Metric |
| C101 |  |  | Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder -> Capacitor_SMD:C_1210_3225Metric |
| C102 | UCS2G560MND9 -> 56u 250V |  |  |
| D4 | ES1A -> ES1D |  |  |
| D5 | ES1A -> ES1D |  |  |
| D6 | ES1A -> ES1D |  |  |
| D8 | ES1A -> US1M |  |  |
| D14 | ES1A -> ES1D |  |  |
| D29 | ES1A -> ES1D |  |  |
| DRV1 | IXDD609D2TR -> UCC27511ADBVR | IXDD609 -> UCC27511A | tube_psu:DFN-8-1EP_P0.95mm_IXDD60xD2 -> Package_TO_SOT_SMD:SOT-23-6 |
| DRV2 | IXDD609D2TR -> UCC27511ADBVR | IXDD609 -> UCC27511A | tube_psu:DFN-8-1EP_P0.95mm_IXDD60xD2 -> Package_TO_SOT_SMD:SOT-23-6 |
| DRV3 | SI8271 -> UCC21520DWR | SI8271 -> UCC21520 | tube_psu:SOIC-8_3.9x4.9mm_P1.27mm_Proteus -> Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm |
| DRV4 | IXDD604D2TR -> UCC27524ADR | IXDD604 -> UCC27524A | tube_psu:DFN-8-1EP_P0.95mm_IXDD60xD2 -> Package_SO:SOIC-8_3.9x4.9mm_P1.27mm |
| DRV5 | SI8275BB -> UCC21520DWR | SI8275 -> UCC21520 | tube_psu:SOIC-16_3.9x9.9mm_P1.27mm_Proteus -> Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm |
| DRV6 | SI8275BB -> UCC21520DWR | SI8275 -> UCC21520 | tube_psu:SOIC-16_3.9x9.9mm_P1.27mm_Proteus_KiCadPads -> Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm |
| ISO1 | SI8661 -> CA-IS3761LW |  | tube_psu:SOIC-16W_7.5x10.3mm_P1.27mm_Proteus -> Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm |
| ISO2 | SI8661 -> CA-IS3761LW |  | tube_psu:SOIC-16W_7.5x10.3mm_P1.27mm_Proteus -> Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm |
| J4 | 66226-003 -> FTDI 1x6 | CONN_01X03 -> CONN_01X06 | Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical -> Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical |
| L1 | 200u -> TBD (measured) | RM8_INDUCTOR -> L_TOROID | tube_psu:L_RM8_Proteus ->  |
| L2 | 200u -> TBD (measured) | RM8_INDUCTOR -> L_TOROID | tube_psu:L_RM8_Proteus ->  |
| PWM2 | IW1818 -> iW1819-00 | IW1818 -> IW1819 | Package_DIP:DIP-8-N6_W7.62mm -> tube_psu_next_parts:SOIC-10_Batwing_iW1819 |
| Q10 | IPA60R280CFD7XKSA1 -> IPD60R280P7S |  | Package_TO_SOT_THT:TO-220-3_Vertical -> Package_TO_SOT_SMD:TO-252-2 |
| Q11 | IPA60R280CFD7XKSA1 -> IPD60R280P7S |  | Package_TO_SOT_THT:TO-220-3_Vertical -> Package_TO_SOT_SMD:TO-252-2 |
| R2 | 1k -> 100R |  |  |
| R3 | 470 -> 1.96k |  |  |
| R8 | 2.49R -> 2.0R |  |  |
| R9 | 2.49R -> 2.0R |  |  |
| R49 | 15k -> 12k |  |  |
| R80 | 15k -> 12k |  |  |
| R110 | 220 -> 1.00k |  |  |
| R124 | 12.1K -> 2.61k |  |  |
| REF1 | ISL21010CFH315Z-TK -> REF3325AIDBZR |  |  |
| TR1 | EF20 -> EEL19_4+6 Lp600u | EF20 -> EEL19_4P6 | tube_psu:Transformer_EF20_2x5_P3.81mm -> tube_psu_next:Transformer_EEL19_V_4+6_FlyLeads |
| TR3 | ETD34 TRAN 1P1S -> EC42/15 2CH 20:21 | ETD34_TRAN_1P1S -> EC42_2CH | tube_psu:Transformer_ETD34_4x3pads -> tube_psu_next:Transformer_EC42x15_2Slot_2x8_P5mm |
| U1 | LMH6658 -> LMH6643 | LMH6658 -> LMH6643 |  |
| U4 | LMH6658 -> LMH6643 | LMH6658 -> LMH6643 |  |

Nets: 5.1 208, 5.2 224 (with at least one part pin).

**5.1 nets gone** (no pin left in any 5.2 net): /04 MCU connector/ADA0, /04 MCU connector/ADA1, /04 MCU connector/ADA2, /04 MCU connector/ADA4, /04 MCU connector/CUK_CAP_MEAS_RAW, /04 MCU connector/HEATER_CAP_AD_MEAS, /07 DHB/TRANS_PRI, Net-(DRV3-OUT-), Net-(DRV5-NC6), Net-(DRV6-NC6), unconnected-(DRV5-NC12-Pad12), unconnected-(DRV5-NC13-Pad13), unconnected-(DRV5-NC7-Pad7), unconnected-(DRV6-NC12-Pad12), unconnected-(DRV6-NC13-Pad13), unconnected-(DRV6-NC7-Pad7), unconnected-(L1-NC-Pad1), unconnected-(L1-NC-Pad2), unconnected-(L2-NC-Pad1), unconnected-(L2-NC-Pad2), unconnected-(L3-NC-Pad1), unconnected-(L3-NC-Pad2)

**New 5.2 nets** (only new part pins): ISO_UART_GND, Net-(D35-K), Net-(DRV3-DT), Net-(DRV5-DT), Net-(DRV6-DT), Net-(U10A-+), Net-(U10A--), Net-(U10B-+), Net-(U10B--), Net-(U11-B1), Net-(U11-B2), Net-(U9-+), Net-(U9--), UART_3V3, UART_5V, /04 MCU connector/UART_RXD, /04 MCU connector/UART_TXD, unconnected-(DRV3-NC-Pad12), unconnected-(DRV3-NC-Pad13), unconnected-(DRV3-NC-Pad7), unconnected-(DRV5-NC-Pad12), unconnected-(DRV5-NC-Pad13), unconnected-(DRV5-NC-Pad7), unconnected-(DRV6-NC-Pad12), unconnected-(DRV6-NC-Pad13), unconnected-(DRV6-NC-Pad7), unconnected-(J4-Pin_2-Pad2), unconnected-(J4-Pin_6-Pad6), unconnected-(PWM2-ASU-Pad10), unconnected-(PWM2-NC-Pad4), unconnected-(U11-NC-Pad10), unconnected-(U11-NC-Pad11), unconnected-(U11-NC-Pad15), unconnected-(U11-NC-Pad2), unconnected-(U11-NC-Pad6), unconnected-(U11-NC-Pad8)

**5.1 nets split in 5.2:** Net-(DRV1-OUTA), Net-(DRV2-OUTA)

**Renamed nets** (same pins, new name): /04 MCU connector/ADB0 -> /04 MCU connector/5V_MEAS; /04 MCU connector/F16 -> DAB_DIS; unconnected-(ISO2-VO_C-Pad13) -> DAB_DIS_SEC; Net-(D7-PadA) -> /01 AUX supply/FLY_C; Net-(DRV3-OUT+) -> /06 Heaters/HEATER_HI_DRV; Net-(DRV9-OUTA) -> /06 Heaters/HEATER_LOW_DRV; Net-(R49-Pad1) -> Net-(C127-Pad1); Net-(R2-Pad2) -> Net-(C131-Pad2); Net-(DRV1-OUTA) -> Net-(DRV1-OUTH); Net-(DRV1-OUTA) -> Net-(DRV1-OUTL); Net-(DRV2-OUTA) -> Net-(DRV2-OUTH); Net-(DRV2-OUTA) -> Net-(DRV2-OUTL); Net-(DRV3-VDD2) -> Net-(DRV3-VDDA); Net-(PWM2-Vsense) -> Net-(PWM2-VSENSE); Net-(D5-PadA) -> Net-(TR1-A15); Net-(D4-PadA) -> Net-(TR1-S15); Net-(D29-PadA) -> Net-(TR1-S5); Net-(L2-2) -> /05 PFC/PFC_DRAIN_1; Net-(L1-1) -> /05 PFC/PFC_DRAIN_2

**Changed connections** (+ pin joined, - pin left; pins of added / removed parts summarised):

| Net (5.2) | Change |
|---|---|
| +1V65_BIAS | -R3.1 R110.1; new parts C122 C123 C126 R131 |
| +3V3 | new parts C124 C125 C129 C133 C134 U9 U10 U11 |
| 15V | +DRV3.11; -DRV1.3 DRV1.8 DRV2.3 DRV2.8; new parts R125; removed parts DRV9 |
| 5V | +DRV3.3 DRV3.8; -DRV3.2 DRV3.4 DRV5.5; new parts R126 R133 |
| 5V_ISOL | -DRV6.5 |
| /04 MCU connector/ADB0 -> /04 MCU connector/5V_MEAS | new parts R135 |
| 6V3 | +DRV4.8; -DRV4.4 |
| AC1 | +L2.1; -L2.pri1 |
| AC2 | +L1.2; -L1.pri2 |
| /04 MCU connector/AUX_MEAS | +J2.43; -C61.2 J2.40 R11.2 R12.1; new parts R132 |
| /04 MCU connector/F16 -> DAB_DIS | +DRV5.5 ISO2.4; new parts C120 R129 |
| unconnected-(ISO2-VO_C-Pad13) -> DAB_DIS_SEC | +DRV6.5 |
| DC+ | +TR1.11; -TR1.4 |
| /04 MCU connector/DC_LINK_MEAS | removed parts C4 |
| /07 DHB/DHB_CAP | +TR3.1 TR3.2; removed parts L3 |
| DHB_HI_SOURCE | +TR3.7 TR3.8; -TR3.2 |
| DHB_HI_SOURCE_SEC | +TR3.15 TR3.16; -TR3.4 |
| DHB_I_MEAS | +J2.38; -J2.37 |
| EPWM5A_ISO | +DRV4.4; -DRV4.3 |
| EPWM6A | +DRV3.2; removed parts DRV9 |
| Net-(D7-PadA) -> /01 AUX supply/FLY_C | +PWM2.5 PWM2.6 TR1.12; -PWM2.7 PWM2.8 TR1.5 |
| GND | +DRV3.4 DRV3.5 DRV3.9 J2.37 J2.39 J2.40 J2.46 J2.48 J2.50 PWM2.8; -DRV1.9 DRV2.9 DRV3.3 ISO2.4 J4.3; new parts C118 C120 C121 C124 C125 C128 C129 C130 C132 C133 C134 R125 R126 R127 R129 R130 R134 U9 U10 U11; removed parts C4 DRV9 R40 |
| Net-(DRV3-OUT+) -> /06 Heaters/HEATER_HI_DRV | +DRV3.15 R59.1; -DRV3.7 |
| /06 Heaters/HEATER_HI_GATE | -R59.2; new parts D35 |
| /06 Heaters/HEATER_HI_SOURCE | +DRV3.14; -DRV3.5 |
| Net-(DRV9-OUTA) -> /06 Heaters/HEATER_LOW_DRV | +DRV3.10; removed parts DRV9 |
| HT_GND | +DRV4.3; -DRV4.7 DRV4.9 |
| ISO_GND | new parts C119 R128; removed parts R25 |
| Net-(R49-Pad1) -> Net-(C127-Pad1) | new parts C127 |
| Net-(R2-Pad2) -> Net-(C131-Pad2) | new parts C131 |
| Net-(D10-K) | +PWM2.2; -PWM2.5 |
| Net-(D11-K) | +R99.1; -R99.2 |
| Net-(D8-K) | +TR1.5; -TR1.6 |
| Net-(DRV1-OUTA) -> Net-(DRV1-OUTH) | +DRV1.2; -DRV1.6 DRV1.7 R1.1 |
| Net-(DRV1-OUTA) -> Net-(DRV1-OUTL) | +DRV1.3; -DRV1.6 DRV1.7 R14.1 |
| Net-(DRV2-OUTA) -> Net-(DRV2-OUTH) | +DRV2.2; -DRV2.6 DRV2.7 R19.1 |
| Net-(DRV2-OUTA) -> Net-(DRV2-OUTL) | +DRV2.3; -DRV2.6 DRV2.7 R20.1 |
| Net-(DRV3-VDD2) -> Net-(DRV3-VDDA) | +DRV3.16 R99.2; -DRV3.8 R99.1 |
| Net-(DRV4-OUTA) | +DRV4.7; -DRV4.8 |
| Net-(PWM2-E) | +PWM2.7 PWM2.9; -PWM2.1 PWM2.2 |
| Net-(PWM2-Vsense) -> Net-(PWM2-VSENSE) | +PWM2.1; -PWM2.4 |
| Net-(U1A-+) | new parts C123 |
| Net-(U1B-+) | new parts C122 |
| Net-(U6-+) | new parts C130 |
| Net-(U6--) | new parts C131 |
| Net-(U8-+) | new parts C126 |
| Net-(U8--) | new parts C127 |
| Net-(L2-2) -> /05 PFC/PFC_DRAIN_1 | +L2.2; -L2.pri2 |
| Net-(L1-1) -> /05 PFC/PFC_DRAIN_2 | +L1.1; -L1.pri1 |
| PFC_I1_MEAS | +J2.42; -J2.43 |
| PFC_PWM1 | +DRV1.6; -DRV1.2 |
| PFC_PWM2 | +DRV2.6; -DRV2.2 |
| /04 MCU connector/RX | -J4.1; new parts U11 |
| /07 DHB/TRANS_SEC | +TR3.10 TR3.9; -TR3.3 |
| /04 MCU connector/TX | -J4.2; new parts U11 |

<!-- netlist_diff.py end -->
