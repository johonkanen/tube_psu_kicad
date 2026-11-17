# Next board revision (tube_power 5.2) – list of changes

Status 2026-11-17. The KiCad design in `kicad/` is still the 1:1 migration of the built
tube_power_5_1 board (verified against the Proteus CADCAM files by `tools/check_all.sh`); none of
the changes below is in it yet. Each item points to the study that backs it.

Priority: **H** = fix / required for the new parts, **M** = should do, **L** = documentation or
optional. "Decided" = the user has agreed; "to confirm" = needs an answer or a measurement first.

## 1. Auxiliary flyback (sheet 1) – new TR1 on EEL19, 12 W continuous

Source: [simulation/flyback/EEL19_DESIGN.md](simulation/flyback/EEL19_DESIGN.md) (sections 6, 6a,
7, 8). Decided: EEL19, fly-lead primary, margin tape (no TIW), board move, preloads, 12 W
continuous.

| # | Ref | Change | Why | Prio |
|---|---|---|---|---|
| 1.1 | TR1 | EF20 → **EEL19 vertical 4+6** (PC40), P 52+52 T split primary on fly leads, S15 16 / SHV 84 / S5+SN5 6+6 ‖ A5 6 / A15 16 T, Lp 600 µH ± 5 %, spacer gap (≈ 0.37–0.46 mm, set by measurement) | 12–15 W, better cross regulation | H |
| 1.2 | TR1 footprint | **Done:** `lib/tube_psu_next.pretty/Transformer_EEL19_V_4+6_FlyLeads` (`tools/next/gen_next_footprints.py`). Primary row 4 × 3.5 mm (pin 4 = crossover post, **no pad**), isolated row 6 × 2.7 mm (pin 2 spare, no pad), rows 12.5 mm apart, **+2 fly-lead holes** FL_DC / FL_C (1.2 mm drill) | new bobbin | H |
| 1.3 | TR1 placement | Move TR1 ≈ +0.93 mm in x (recheck with the 4+6 footprint: up to +0.5 mm more); move D8, D14, C45, C40, C44 (+1.5…2 mm x), C114/C115 (+1.5 mm), C102 (≈ 1.4 mm down), new place for C3; re-route all TR1 pads, DC+ / collector to the fly-lead holes | fit | H |
| 1.4 | ISO_GND pour (F.Cu) | Pull the edge back to x ≥ 69.8 for y 2…14 | FL_DC hole clearance; also fixes the **existing 5.08 mm DC+ to ISO_GND creepage** spot | H |
| 1.5 | PWM2 | IW1818 → **iW1819-00** (SO-10 batwing, 18 W, 0 mV cable comp; in stock at DigiKey/Mouser; not -01/-11) – new symbol, footprint and pinout; recheck Rsense, Vsense divider and Vcc network against the iW1819 datasheet | IW1818 is rated 10–12 W only | M – **decided: iW1819-00** |
| 1.6 | R8, R9 | 2.49 Ω → **2.0 Ω** 1206 1 % (Rsense 1.0 Ω, OCP 1.15 A) – value for the IW1818; confirm for the iW1819 | power capability | H |
| 1.7 | new | **Preloads 2.2 kΩ on 15V** (1206, 0.25 W) and **1 kΩ on 5V** | light-load excursions | H |
| 1.8 | R124 | 12.1 kΩ → **2.61 kΩ** 1206 (15V_ISO_SEC bleeder) | light-load excursion | H |
| 1.9 | D8 | Keep a **≥ 600 V** diode in the BOM (US1M 1000 V; the fitted part is 1000 V); the schematic's ES1A-family 200 V is wrong | V_R 395–420 V | H |
| 1.10 | D4, D5 | ES1B / ES1D (≥ 100 V) | V_R ≈ 77 V | M |
| 1.11 | C1, C2, C6, C36, C71, C114, C115 | Check ripple-current rating at 15 W (winding rms 0.6–0.8 A) | not simulated with real ESR | M |
| 1.12 | R64, R81, R84, R85 | **Unchanged** (aux turns ratio kept) | – | – |

## 2. DAB / DHB transformer (sheet 7) – TR3 + L3 → one two-chamber transformer

Source: [simulation/dab/DAB_TRANSFORMER.md](simulation/dab/DAB_TRANSFORMER.md). Core set bought:
EC42/15 PC40 + 2-chamber bobbin 8+8 pins.

| # | Ref | Change | Why | Prio |
|---|---|---|---|---|
| 2.1 | TR3 | ETD34 → **EC42/15 PC40, 2-chamber bobbin**: primary in the 10.4 mm chamber, secondary in the 12.4 mm chamber, litz 135×0.071, centre-leg gap for no-load ZVS. Option **A 25:26** (leakage ≈ 63 µH, replaces L3 = 70 µH, φ ≈ 41° at 400 W) or **B 20:21** (≈ 41 µH, φ ≈ 24°) | leakage = series L, ≈ 2 W loss instead of ≈ 6.7 W | H – **decided: option B 20:21** (user 2026-11-17) |
| 2.2 | TR3 footprint | **Done:** `lib/tube_psu_next.pretty/Transformer_EC42x15_2Slot_2x8_P5mm`. 2 × 8 pins, 5.0 mm pitch, rows 40 mm apart, body ≈ 46 × 42 mm, seated height ≈ 31.5 mm; pads only on the used pins (2 per winding end: 1+2, 7+8, 9+10, 15+16) | new core | H |
| 2.3 | TR3 placement | Over the old TR3 + L3 area, centred ≈ (43.5, −69.8), axis along x, primary row on the half-bridge side (x ≈ 23.5), secondary row next to C16/C55; ≥ 1.4 mm from the top board edge | fit | H |
| 2.4 | L3 | **Remove**; connect DHB_CAP directly to the primary (or keep the RM8 pads with a jumper as a fallback for a small residual L) | leakage replaces it | H |
| 2.5 | C47, C54 | Move into the freed L3 corner (x ≈ 10–20) next to the primary pins | they sit under the new primary row | H |
| 2.6 | DRV5, C46 (B.Cu) | Keep clear of the new pin rows (or omit the pads of the unused bobbin pins and clip those pins) | pin collisions | H |
| 2.7 | Firmware | Dead time 150–200 ns (the gap is sized for 150 ns, 181 pF per switch node) | ZVS at no load | M |

## 3. DHB gate drivers (sheet 2)

| # | Ref | Change | Why | Prio |
|---|---|---|---|---|
| 3.1 | DRV5, DRV6 | Schematic / BOM: **Si8275BB** (dual input, 8 V UVLO) – already corrected in the KiCad design (`5ef2e7f`) | wrong part number (Si8274) | done in KiCad |
| 3.2 | R40, R25 | Remove (DNP): they sit on pin 6 = NC of the Si8275 | dead-time resistors of the Si8274 | L |
| 3.3 | DRV5/DRV6 EN (pin 5) | Optional: route EN to an FPGA pin (today tied to VDDI) for a hardware disable | Si8275 has no overlap protection; dead time only from firmware | L |

## 3b. Serial port J4 – isolated (user 2026-11-17)

Today J4 (66226-003, 3 pins) carries RX (J2-24, FPGA input), TX (J2-26, FPGA output) and **GND –
the mains-referenced primary ground** (the PFC shunts and bridge sit on it). A USB-UART cable on J4
ties the PC to line potential, so it only works with an external isolator. Next revision: isolate it
on the board; the cable side is powered by the cable itself, so no isolated DC/DC is needed.

| # | Ref | Change | Why | Prio |
|---|---|---|---|---|
| 3b.1 | new U (isolator) | 2-channel digital isolator, 1 forward + 1 reverse, **reinforced, wide body (8 mm creepage)**, **default-high outputs** (UART idle; with no cable the FPGA RX stays high): **Si8621BD-B-IS** C7315709 (SOIC-16W, 5 kV, 709 pcs, ≈ $1.84; same Si86xx family as ISO1/ISO2 and the Si8275 drivers) – alternative NSi8221W1-DSWR C2987925 (SOW-16, 965 pcs, ≈ $1.34). Not the narrow SOIC-8 parts (ADuM1201, ISO7721D, CA-IS372xS: basic, 4 mm). Side 1: +3V3, GND, 100 nF; side 2: cable 3.3 V, ISO_UART_GND, 100 nF. Check the default-output letter in the datasheet before ordering | safety, convenience | H |
| 3b.2 | J4 | → **6-pin 2.54 mm FTDI header** (TTL-232R-3V3 pinout: 1 GND, 2 CTS n.c., 3 VCC 5 V in, 4 TXD → isolator → J2-24 RX, 5 RXD ← isolator ← J2-26 TX, 6 RTS n.c.) on its own isolated copper island (ISO_UART_GND) | standard cable plugs straight in | H |
| 3b.3 | new LDO | 5 V (cable VCC) → 3.3 V for isolator side 2 (SOT-23 LDO, ≤ 5 mA load, 1 µF in/out), so the outputs match the 3.3 V cable I/O | 3.3 V logic on the cable side | H |
| 3b.4 | Layout | Isolator straddles the barrier; keep ≥ 8 mm creepage / clearance between the J4 island and any primary copper on all layers (no planes or pours under the island), like the existing Si8661 barrier. 22–100 Ω series resistors on the cable-side TXD/RXD optional (ESD / ringing) | reinforced isolation | H |
| 3b.5 | Docs | Until then: **never connect a non-isolated USB-UART to J4 while the board is on mains** | safety | H (now) |

## 4. Measurement circuits (sheets 4, 8, 9)

Source: [simulation/FINDINGS.md](simulation/FINDINGS.md) (ngspice + hVHDL_ode, ADC mux transient).

| # | Ref | Change | Why | Prio |
|---|---|---|---|---|
| 4.1 | +1V65_BIAS | **Buffer the bias**: TLV316-class follower from +3V3, 100 nF on the REF1 divider node, 22 Ω to the bias net, C48 after the 22 Ω | AC line couples into every current channel (±15 mV, ≈ 0.19 A on PFC_I) | H |
| 4.2 | VAC_MEAS (U8) | 1 nF C0G across R80 and across R49; keep R65 100 Ω, no output capacitor | no filter, +22 dB at 20–50 MHz | H |
| 4.3 | VAC_MEAS range | R49, R80 15 kΩ → **12 kΩ** (and the 1 nF of 4.2 with them) | clips above ≈ 330 V peak | H |
| 4.4 | DC_LINK_MEAS (U6) | 1 nF C0G across R17 and across R82; R2 1 kΩ → **100 Ω**; **remove C4** | HF feedthrough; ADC mux leakage 254 LSB at 1 µs | H |
| 4.5 | AUX_MEAS | C61 1 nF → **1 µF** | ADC mux leakage 505 LSB at 1 µs → 0.7 LSB | H |
| 4.6 | U1 (LMH6658) | Add 100 nF (+ 1 µF) at pin 8 | no local decoupling | M |
| 4.7 | C10, C26 | Keep unfitted | mux settling is better without | – |
| 4.8 | REF1 | Correct the schematic value to the fitted 1.65 V reference (ISL21010CFH315Z is the 1.5 V part) | documentation | L |
| 4.9 | Firmware | HEATER_I gain −0.18 % calibration; AD2 (420 V) bandwidth 8.86 kHz in the control model | – | L |
| 4.10 | U1, U4 + 18 resistors / 6 caps | **Not taken (user 2026-11-17: LMH6643, item 4.10b).** Was optional: replace the four LMH6658 difference amplifiers by **INA296B current-sense amplifiers** (SOT-23-8 2.9 × 2.8 mm, 1.1 MHz at every gain, CM −5…110 V, gain error ±0.1 %, 2.5 mA each from +3V3): PFC_I1/I2 INA296B2 (20 V/V, 80 mV/A, was 82.5), DHB_I INA296B3 (50 V/V, 0.2 V/A, ±8.25 A, was 0.182 V/A), HEATER_I INA296B4 (100 V/V, 0.4 V/A, same). All channels stay **bidirectional around +1V65_BIAS** (user 2026-11-17: reverse currents are measured, the DAB is bidirectional): **REF1 = REF2 = +1V65_BIAS**, which needs the bias buffer of item 4.1 (the REF pins drive an internal resistor network). (REF1 = +3V3 / REF2 = GND would also give a 1.65 V mid-scale, but ratiometric to the power-board +3V3 instead of the reference.) Keep the output 100 Ω / 100 pF (not 1 nF: it rings with the mux load) and sample ≥ 1.5 µs after the mux switch (section 4c). Saves ≈ 70 mm² of B.Cu courtyard (141 → 70 mm², 24 → 8 parts), gives ≥ the present bandwidth (DHB 452 kHz → 1.1 MHz, HEATER 241 kHz → 1.1 MHz), removes the resistor-ratio gain errors and the amplifier bias resistors that load the bias today (≈ 2.7 kΩ in total). INA181/INA2181 are smaller/cheaper but only 105–350 kHz (too slow for the 140 kHz DHB current). **JLC stock 2026-11-17 → use the pin-compatible INA241A** (same 1.1 MHz / 8 V/µs / −5…110 V, plus enhanced PWM rejection, ±0.01 % gain error): INA241A2IDDFR C5240853 (20 V/V, 109 pcs; VSSOP INA241A2IDGKR C36752877 2684 pcs), **INA241A3IDDFR C6051860** (50 V/V, 7956 pcs), **INA241A4IDDFR C20345440** (100 V/V, 1190 pcs), about $2.7–3.8 each, extended parts. INA296 stock is thin for the gains needed (A2 28, B2/B3 0 pcs in SOT-23-8). | space, accuracy | M – to decide |
| 4.10b | U1, U4 (if the difference amplifiers stay) | **LMH6658 is not stocked at JLC** (11 pcs VSSOP-8, 2026-11-17). Drop-in for the same VSSOP/TSSOP-8 3 × 3 mm footprint and pinout: **LMH6643MMX/NOPB C478382** (15 316 pcs, ≈ $0.95; **57 MHz GBW** (130 MHz is its unity-gain −3 dB bandwidth), 135 V/µs, output within 40 mV of the rails, 2.7–12.8 V; inputs sit at ≈ 1.6 V, inside its input range at 3.3 V; **Vos 5 mV max = 1.25 A input-referred on 4 mΩ**, so calibrate the zero at start-up). Ranges with today's gains (bias 1.65 V, 40 mV swing margin): PFC ±19.5 A (±18.2 A after worst-case offset), DHB ±8.8 A (±7.6 A), HEATER ±4.0 A (±2.8 A); 1 LSB = 2.4 / 1.1 / 0.5 mA. Closed-loop bandwidth 57 MHz / noise gain = 2.6 / 1.2 / 0.56 MHz, above the 1.17 MHz / 530 kHz / 241 kHz feedback-cap poles (HEATER loses ≈ 10 % of its bandwidth). Alternatives: ADA4891-2ARMZ-R7 C143927 (2067 pcs, ≈ $5.4, 240 MHz), OPA2354AIDGKR C95502 (4366 pcs, ≈ $12, 250 MHz RRIO). Too slow for HEATER_I's gain of 100: OPA2350 (38 MHz), TLV9062 / LMV722 (10 MHz). Two LMH6643 + resistors ≈ $2 against four INA241A ≈ $12 | availability | **H – decided (LMH6643)** |
| 4.11 | All four shunt inputs (R93, R21, R83, R30 → amplifier) | **RC compensation of the shunt inductance**: the 4 mΩ KRL2012 shunt has ESL < 1 nH (Susumu typ ≈ 0.5 nH) plus the Kelvin-loop inductance, i.e. a zero at R/(2πL) ≈ 0.6–1.3 MHz. On the fast switched currents (MOSFET source / bridge return, di/dt ≈ 0.1 A/ns) 1 nH gives ≈ 100 mV spikes against 4 mV/A of signal. Cancel it with a pole of the same time constant: **2 × Rf in series with the inputs + Cf across the inputs, 2·Rf·Cf = L/R**. With the INA241A: Rf = **10 Ω** (input bias 35 µA typ → ≈ 0.35 mV common shift; keep Rf ≤ 10 Ω so the bias mismatch stays ≈ 0.1 mV = 25 mA, calibrated as offset), Cf = **10 nF C0G** (τ 200 ns ↔ 0.8 nH; 6.8 nF ↔ 0.54 nH, 12 nF ↔ 1 nH). Place Rf/Cf at the amplifier, Kelvin traces from the shunt pads as a tight pair. **Tune Cf on the bench**: look at the amplifier output across a switching edge – a spike means Cf too small, a slow undershoot/overshoot after the edge means too large. With the LMH6658 difference amplifiers the same pole comes from the feedback caps (τ = Rfb·C): today PFC 6.8 k·20 p = 136 ns (≈ 0.54 nH, both legs), DHB 15 k·20 p = 300 ns and HEATER 33 k·20 p = 660 ns with **no matching cap on the + leg** (C63 / C11 only) – add the matching 20 pF from the + input to +1V65_BIAS (and retune) if the LMH6658 stays | spikes / aliasing on fast edges | H |

## 4b. ADC channel allocation (J2 analog pins)

User decision (2026-11-17): the PFC currents and the DAB current go on **one** muxed ADC, sampled
synchronously with the 140 kHz PWM at fixed sample positions; the LLC (heater supply) runs at a
variable frequency, so its ADC carries the LLC current plus the non-critical, slow channels.

Control card (`~/dev/ti60f225_tube_psu_control_card`, `reference/mux_assignment.csv`,
`reference/power_board_header.csv`): ADC A = U10 → OPA365 → ADS7056 (ADA0–6), ADC B = U13 → … (ADB0–6).
Today the critical channels are split: PFC_I2 on A, PFC_I1 and DHB_I on B, AUX on A.

| Signal | Today (power-board J2 pin → card net) | Next revision | ADC |
|---|---|---|---|
| PFC_I1_MEAS | J2-43 → ADB3 | **J2-42 → ADA4** (free today) | A |
| PFC_I2_MEAS | J2-44 → ADA3 | unchanged | A |
| DHB_I_MEAS | J2-37 → ADB6 | **J2-38 → ADA6** (was the unconnected CUK_CAP_MEAS_RAW) | A |
| HEATER_I_MEAS (LLC) | J2-45 → ADB2 | unchanged | B |
| VAC_MEAS | J2-47 → ADB1 | unchanged | B |
| DC_LINK_MEAS | J2-41 → ADB4 | unchanged | B |
| AUX_MEAS | J2-40 → ADA5 | **J2-43 → ADB3** (freed by PFC_I1) | B |
| **5V_MEAS (new)** | – | **J2-49 → ADB0** (free today) | B |
| spare | – | A: ADA0–2, ADA5 (J2-50/48/46/40); B: ADB5, ADB6 (J2-39/37) | – |

- ADC A then holds only the three low-impedance current outputs (100 Ω/100 pF, 33 Ω): at 140 kHz
  (7.14 µs) each gets ≥ 2.3 µs, the mux settles to < 1 LSB in ≈ 1 µs (FINDINGS.md 9), so every
  channel can be sampled at the same PWM-locked position every period (or twice, e.g. at the
  PWM centre for the PFC average current).
- ADC B sees a varying channel order (LLC timing), so its slow, high-impedance channels need the
  mux-leakage fixes 4.4 (DC_LINK) and 4.5 (AUX, C61 1 µF) – both already in the list.
- Equivalent alternative: keep the power-board pins and swap the mux inputs on the control card
  (its mux table is still open there). Doing it on the power board needs no control-card change.
- Firmware: update the channel map (ADA4 = PFC_I1, ADA6 = DHB_I, ADB3 = AUX, ADB0 = 5V).
- **5V_MEAS (new, user 2026-11-17):** the primary-side 5V rail (flyback feedback winding, MCU/control
  card supply; same GND as the ADC). Divider 15 kΩ / 10 kΩ 0.1 % (gain 0.4: 5.0 V → 2.0 V, full scale
  8.25 V, so a light-load rise is still visible; 1 LSB = 0.5 mV), 100 nF across the 10 kΩ (6 kΩ ·
  100 nF → 1.6 ms), then a **follower + 100 Ω** to J2-49. Use a dual op-amp for both slow rails:
  **TLV9062IDGKR** C398356 (10 MHz RRIO, 2.5–5.5 V, 48 k pcs, ≈ $0.23) on +3V3 – channel A buffers
  AUX_MEAS (rule 4c.2), channel B buffers 5V_MEAS. The isolated 5V_ISOL cannot go to this ADC
  directly (it would need an isolated measurement like AD1/AD2).

## 4c. Interface to the control-card ADC mux – no channel-to-channel leakage

Control card: TMUX1308 (RON 120 Ω typ / 350 Ω max, C_D 40 pF, charge injection 1 pC, leakage
±45 nA) → OPA365 follower → 33 Ω / 680 pF → **ADS7056, 14 bit, 0–3.3 V (1 LSB = 201 µV)**. The
mux output node keeps the previous channel's voltage; each J2 output must recharge it through RON
before the sample. Target: **< 0.5 LSB** of the previous channel for a full-scale (3.3 V)
difference, at the planned dwell time. Simulations: `simulation/spice/mux_settling.py`
(FINDINGS.md 9) and `simulation/spice/mux_ina296.py` (INA296 option).

Rules for every J2 analog output:

1. Driven by a low-impedance amplifier output through ≤ 100 Ω, with ≤ 100 pF at the pin –
   never a large capacitor behind a large resistor (that charge-shares and then recovers with
   its own slow RC: DC_LINK 254 LSB, AUX 505 LSB at 1 µs as built).
2. Unbuffered dividers only with a reservoir ≥ 1 µF (AUX with C61 1 µF: fixed 0.67 LSB, plus
   0.9 LSB offset from the 45 nA mux leakage through 3.9 kΩ). For zero leakage: **buffer AUX_MEAS**
   (TLV316 follower + 100 Ω like U6/U8) – recommended (M), else item 4.5.
3. No floating mux inputs: tie every spare J2 analog pin to GND on the power board (spares after
   4b: J2-50/48/46/40 on ADC A, J2-39/37 on ADC B). A grounded input can also serve as a reset
   step before a channel if ever needed.
4. Dwell (switch → sample), firmware: ADC A ≥ 1 µs with the LMH6658 outputs (PFC ≤ 0.02 LSB,
   DHB 0.18 LSB), **≥ 1.5 µs with the INA296 option** (≤ 0.02 LSB; 0.2–1 LSB at 1 µs); ADC B
   ≥ 2 µs (HEATER_I 0.10 LSB; VAC/DC_LINK with fixes < 0.01 LSB from 0.4 µs). ADC A has ≥ 2.3 µs per
   channel at 140 kHz, so both are met. ADC B's LLC-timed sequence must keep the 2 µs minimum.
5. Charge injection (1 pC) ≤ 0.05 LSB and leakage current ≤ 0.02 LSB on ≤ 100 Ω sources –
   no action.

Resulting per-channel status (next revision, with items 4.2, 4.4, 4.5 / AUX buffer):

| Channel | ADC | Output network | Leakage at the planned dwell |
|---|---|---|---|
| PFC_I1, PFC_I2 | A | LMH6658 (or INA296) + 100 Ω / 100 pF | ≤ 0.02 LSB (≥ 1 / 1.5 µs) |
| DHB_I | A | LMH6658 (or INA296) + 33 Ω (C26 unfitted) | ≤ 0.18 LSB (1 µs), 0.01 (2 µs) |
| HEATER_I | B | LMH6658 + 33 Ω (C10 unfitted) | 0.10 LSB (2 µs) |
| VAC | B | TLV316 + 100 Ω, Cf 1 nF in the feedback, no output C | < 0.01 LSB |
| DC_LINK | B | TLV316 + 100 Ω, Cf 1 nF, C4 removed | < 0.01 LSB |
| AUX | B | follower + 100 Ω (recommended) / C61 1 µF | ≈ 0 / 0.67 LSB + 0.9 LSB offset |
| 5V (new) | B | TLV9062 follower + 100 Ω | ≈ 0 (low-impedance output) |

Do not put a capacitor larger than ≈ 100 pF on an INA296 output: 100 Ω + 1 nF rings with the mux
load (up to 99 LSB at 0.7 µs in the model).

## 5. General / documentation

| # | Item | Change | Prio |
|---|---|---|---|
| 5.1 | Net names | 15V / 15V_ISO_SEC / +1V65_BIAS – done in the KiCad design (`46a60f9`) | done |
| 5.2 | L1, L2 (PFC) | Confirmed (user): **toroids**, not the RM8 of the schematic. Part: iron-silicon-aluminium (sendust) ring inductor, OD 31.5 × H 16.7 mm (±0.3), leads 8 mm, listing "3 mH, 0.8 mm wire, 6 A". New footprint: 2 pads (lead spacing ≈ 16.7 mm from the drawing – measure), courtyard ≈ Ø 32.5 mm, flat mounting with a hold-down (tie / glue). Set the schematic value to the measured inductance: the 3 mH is the zero-bias listing value (schematic says 200 µH) and sendust loses a large part of it at DC bias – measure L at 0 A and at the PFC peak current before any PFC simulation | M |
| 5.2b | Tall HV electrolytics (JLC stock 2026-11-17) | The fitted parts are **not stocked** (UPZ2W820MNY9, EKXJ451ELL390MJ50S, UCS2G560MND9: 0 pcs). Same footprints (D12.5 / D10, P5): **C28, C29, C37, C56** (DC+, 82 µF 450 V 12.5×50) → **Man Yue ERT826M2WI45RRS0F-R C51890374** (82 µF 450 V 12.5×45, 1.57 A @ 100 kHz, 2870 pcs, ≈ $1.00) or Ymin KCXL4502W101MF C19193642 (100 µF 450 V 12.5×45, 1.18 A @ 100 kHz, 4844 pcs) / Rubycon 450HXW100MEFR12.5X50 C5115126 (100 µF, 500 pcs); not the 400 V types (DC+ is 400 V nominal). **C19, C30** (420V, 39 µF 450 V 10×50) → Ymin KCXE5002W680MF C913388 (68 µF 450 V 10×50, 1 A @ 100 kHz, 103 pcs – enough for 2/board) or Lelon RGL330M2WBKF1035 C335047 (33 µF 450 V 10×35, 131 pcs); 420 V on 450 V parts is the same derating as today. **C102** (−80 V rail, 400 V part today) only needs ≥ 100 V: any 10 mm 160 V / 56 µF | availability | M |
| 5.4 | Q10, Q11 (heater LLC) | No heatsink today (IPA60R280CFD7 TO-220 FullPAK, not stocked at JLC): free to move, or **SMD: IPD60R280P7S C536813** (DPAK, 600 V 280 mΩ, 6503 pcs, ≈ $1.01) on ≥ 2 cm² of L1 copper with thermal vias to L2–L6. P7 has a standard body diode (CFD7 = fast): fine while the LLC stays in ZVS; check start-up / overload commutation in the LLC simulation, else IPD60R360PFD7S (DPAK, fast diode, poor JLC stock) | assembly, space | M |
| 5.5 | Power heatsink (PFC + DAB) | New bent-aluminium bracket for the whole row – PFC Q5/Q6 (TO-247) and SICD1/2 (TO-220-2) on the left, DAB Q7/Q8/Q19/Q21 (TO-220FP) on the right; the row may move (one straight line, clear of the control card); bracket drawing (hole positions, bend) from the placement. The plate carries primary **and** secondary (Q8/Q21 on ISO_GND / 420V) devices, so tab → pad → plate → pad → tab must be **reinforced in total** (rated pads + shoulder washers on bare tabs, FullPAK + pad on Q8/Q21, plate spacing to secondary copper), or split the bracket into a primary and a secondary plate | mechanics, safety | H |
| 5.3 | Fitted-value overrides | Keep `FITTED_VALUES` in `tools/make_part_map.py` in step with the BOM (DRV5/DRV6 today; REF1, D8 candidates) | L |

## 6. Before the layout work starts

1. Calipers on the EEL19 core and 4+6 bobbin (pin diameter, base outline, inner winding length)
   and on the EC42/15 set (core outline, pin pitch / row spacing as in the drawing).
2. Choose DAB option A or B (item 2.1).
3. iW1819-00 datasheet: pinout, Rsense, Vcc and Vsense networks (item 1.5).
4. Measure the PFC toroids: lead spacing / diameter, and L at 0 A and at peak current (item 5.2).
5. Decide how the KiCad design leaves the migration baseline: once the board is edited by hand,
   drop `make_pcb.sh --check` and the Proteus comparisons from `tools/check_all.sh` (STATUS.md,
   Phase 5 notes), keeping ERC / DRC.
