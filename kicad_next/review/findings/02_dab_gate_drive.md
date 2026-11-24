# Findings: 02 DAB gate drive  (reviewer: Claude Opus 5.5, 2026-11-24, commit 3e1e31e)

## Summary
The gate-drive schematic is correct against the UCC21520 datasheet (SLUSCJ9F) and keeps 5.1's firmware-visible
behaviour: J2-4 drives the primary high side, J2-6 the primary low side, J2-10 / J2-12 the secondary high / low side,
and J2-18 high turns all four gates off. Dead time and DISABLE are correct, and the gate networks match 5.1 value for value.
The primary layout (DRV5) is clearly better than 5.1: the gate loops are about 2.5 times shorter and C95 is 0.6 mm from pin 11.
**No blocker for ordering.** Three things should be fixed:
1. **DRV6 pin 11 (VDDB) has no local decoupling capacitor.** The nearest one is 11.9 mm away (5.1: 7.3 mm).
2. **The simulated primary switch-node slope (63–70 V/ns) is above the STF7N60M2 "MOSFET dv/dt ruggedness" of
   50 V/ns.** The fix belongs to checklist 07; the driver itself is not the limit (CMTI 125 V/ns).
3. **The secondary high-side gate track runs under the DRV6 body, 1.21 mm from the DT input pad** (5.1: about 2.4 mm).
The rest are notes.

Board changes since the checklist (stages 13a–13d) do not touch the driver area, apart from the Q8 drain vias
(13a). Where the board differs from a checklist number, I trusted the board and say so in the row.

## Checklist results
| Item | Verdict | Evidence |
|---|---|---|
| A1 | PASS | `rv sch sheet 2`: DRV5 and DRV6 pins 1 INA, 2 INB, 3 VCCI, 4 GND, 5 DIS, 6 DT, 7 NC, 8 VCCI, 9 VSSB, 10 OUTB, 11 VDDB, 12/13 NC, 14 VSSA, 15 OUTA, 16 VDDA. This agrees with the pin table in SLUSCJ9F (Nov 2024) p 4 (https://www.ti.com/lit/ds/symlink/ucc21520.pdf). VCCI pins 3 and 8 are both on 5V / 5V_ISOL. NC pins 7, 12, 13 are on `unconnected-…` nets only. |
| A2 | PASS | DRV5: 1 INA = PRI_DHB_HI (J2.4, R73) → 15 OUTA = DHB_HI_GATE → R26 → Q19.G; 16 VDDA = Net-(DRV5-VDDA) (R41.2, C92.2); 14 VSSA = DHB_HI_SOURCE = Q19.S = Q7.D. 2 INB = B12 (J2.6, R74) → 10 OUTB = DHB_LOW_GATE → R90 → Q7.G; 11 VDDB = 15V; 9 VSSB = GND. `J2_PINOUT.md:45` (pin 4 PRI_DHB_HI → DRV5.1) and `:47` (pin 6 B12 → DRV5.2) say the same. 5.1 (`rv sch51 ref DRV5`): VIB (pin 2) = PRI_DHB_HI → VOB = DHB_HI_GATE, and VIA = B12 → VOA = DHB_LOW_GATE. So J2-4 = high side and J2-6 = low side on both boards; the swap only exchanged driver channels. |
| A3 | PASS | J2.10 EPWM2A → ISO2.2 → ISO2.15 → ISO_SEC_DHB_HI → DRV6.1 INA → OUTA → DHB_HI_GATE_SEC → R57 → **Q21 (high)**. J2.12 EPWM2B → ISO2.3 → ISO2.14 → ISO_SEC_DHB_LO → DRV6.2 → OUTB → R87 → **Q8 (low)**. 5.1 (`rv sch51 ref ISO2` and `net EPWM2A…`, Si8661) has the same pins and nets. |
| A4 | PASS | R127 / R128 10k 1 % (C25804) with C118 / C119 100 pF C0G (C14858). SLUSCJ9F p 4 pin table: "2-kΩ to 500-kΩ … DT (in ns) = 10 × RDT (in kΩ) … parallel a ceramic capacitor, ≤ 1 nF". p 9 table 6.9 gives "Dead time, RDT = 10 kΩ: 80 / 100 / 120 ns". The p 24 §8.4.2 rule ("output dead time is always set to the longer of either the driver's programmed dead time or the input signal's own dead time") means the 120 ns maximum stays below the 150 ns firmware dead time (CHANGES_5_2.md:49). 100 pF ≤ 1 nF. DRV5: R127 0.40 mm and C118 0.81 mm from pin 6 (`padgap`). DRV6: R128 5.24 mm, C119 5.78 mm from pin 6, reached through two vias and 5.75 mm of F.Cu (`rv bq net "Net-(DRV6-DT)"`). That is not "close to the DT pin" (§11.1) → note F9. |
| A5 | PASS | SLUSCJ9F p 4: DISABLE "Disables both driver outputs if asserted high, enables if set low or left open … pulled low internally … Bypass using a ≈1nF". VENH max 2.0 V, VENL min 0.8 V (p 8). DAB_DIS: J2.18 → DRV5.5, R129 10k to GND, C120 1 nF C0G, ISO2.4 → ISO2.13 → DAB_DIS_SEC → DRV6.5. τ = 10 kΩ × 1 nF = 10 µs, which only matters when the line is not driven; when driven, the FPGA output drives 1 nF directly. When J2-18 is not driven, both drivers are enabled (as 5.1 EN = 5V), and R73–R76 hold all four PWM inputs low → all gates low. If ISO2 side 1 is unpowered, the CA-IS3761**L** outputs default low (LCSC C528659 datasheet p 1 "L … 默认输出为低", tDO 8–12 ns, §6.10): DIS_SEC is low (DRV6 enabled) and so are its PWM inputs. In that state the secondary cannot be disabled, but 5.1 had no disable at all (EN tied to 5V_ISOL), so this is not worse. |
| A6 | PASS | VINAH / VINBH max 2.0 V at VCCI 3.3 or 5 V (SLUSCJ9F p 8 §6.8). 3.3 V logic leaves 1.3 V margin. ISO2 side 2 = AD2_3V3 (`rv sch ref ISO2`, pin 16), so DRV6 also sees 3.3 V logic with VCCI = 5V_ISOL. R73 / R74 sit 3.7 / 4.7 mm from DRV5 pins 1 / 2. R75 / R76 sit 6.7 mm from DRV6 pins 1 / 2 (`padgap`). |
| A7 | PASS | SLUSCJ9F p 7 §6.3: VDD 9.2–25 V for the 8 V UVLO version; §6.1 abs max VDD–VSS 30 V and VCCI 20 V; p 8: VDD UVLO on 7.7–8.9 V, off 7.2–8.4 V. Rails: 15V 14.18–15.31 V and 15V_ISO_SEC 14.55–17.44 V (`simulation/flyback/EEL19_DESIGN.md:37`) are inside 9.2–25 V. Bootstrapped VDDA ≈ 15 − 1.1 (S1M VF) ≈ 13.9 V, 5 V above the UVLO-off maximum. VCCI 5 V is inside 3–18 V. |
| A8 | PASS | Same S1M / 2R / 1 µF as 5.1 (`rv sch51 ref D19,R41,C92`). Charge per cycle: Qg(15 V) ≈ 8.8 nC (ST DocID024894 Rev 1 Table 6, VGS 10 V) + ≈ 0.6 nF × 5 V ≈ 12 nC; VDDA current 4.2 mA max (SLUSCJ9F p 8, 500 kHz) / 140 kHz = 30 nC; R22 15 V / 10 kΩ × 3.57 µs = 5.4 nC. Total ≈ 47 nC. Droop on C92 (≥ 0.5 µF effective at 14 V, taking TI's own figure on p 31 for a 25 V X7R; C92 is 50 V X7R 1206) ≤ 0.1 V. TI minimum CBoot = 47 nC / 0.5 V = 94 nF (p 31 eq. 20). Refresh window: low-side on-time ≈ 3.57 − 0.15 = 3.4 µs at 140 kHz and ≈ 1.0 µs at the 420 kHz soft start, against τ = 2 Ω × 1 µF = 2 µs. The deficit is only about 0.1 V, so this is enough. Peak current (15 − 1.1) / 2 Ω ≈ 7 A, but only at the first charge from 0 V. In steady state the current is ≈ deficit / 2 Ω, i.e. tens of mA. S1M IFSM 30 A (MDD Rev 2025A4, https://datasheet.lcsc.com/datasheet/pdf/77f85fa395523de30fe84672709cb97b.pdf). RBOOT 2 Ω is inside TI's 1–20 Ω (p 27). TI recommends "fast recovery or SiC" (p 27); the MDD S1M datasheet gives **no trr / Qrr**, so the recovery loss cannot be calculated (F11). The recovery charge is small because the diode current is only mA when the node rises. 5.1 used the same diode, so this is not worse. |
| A9 | PASS | Requirement at pin 11: Q7 turn-on takes ≈ 12 nC per event; for a 0.5 V droop (TI example) 10 × 12 nC / 0.5 V = 240 nF. C95 CGA0603X5R475K250JT (HRE, LCSC C6119856; https://datasheet.lcsc.com/datasheet/pdf/1b21e771dd7effa9a953f11dd7513d39.pdf) gives ±10 % and X5R ±15 % but **no DC-bias curve**. Bound: 4.7 µF × 0.9 × 0.85 = 3.6 µF before DC bias. A 0603 25 V X5R at 15 V typically keeps 25–35 %, i.e. ≈ 0.9–1.3 µF. TI's own data point (p 31) is that even a 25 V X7R loses 50 % at 15 V. The requirement holds unless more than 93 % of the capacitance were lost. SLUSCJ9F gives no hard VDD minimum, only "≈10 µF for device biasing" (p 38), which 5.1's 4.7 µF did not meet either. C96 1 µF 1206 X7R 50 V is at (28.0, −42.6), 20 mm away, at the D19 anode, and supplies the bootstrap refill. Note F7. |
| A10 | PASS | Same as 5.1 (`rv sch51 ref R26,R53,D30,…`): turn-on 40R (40.2 Ω, C2933439), turn-off 3.3R + ZLLS400TA, G-S 10k on Q19 / Q7 / Q21, none on Q8 (5.1 `Net-(Q8-G)`: Q8.1 R87.2 R88.2, as now). Diode direction: D30 K = DHB_HI_GATE (driver), A = Net-(D30-PadA) → R53 → Net-(Q19-G); the same for D34 / D31 / D32. Peak currents: on 15 / (40.2 + 7.2 RG,int) ≈ 0.32 A against 4 A source; off (15 − 0.6) / (3.3 + 7.2 + 0.55) ≈ 1.3 A against 6 A sink (SLUSCJ9F p 9). ZLLS400 (DS33226 Rev 10-2, https://www.diodes.com/assets/Datasheets/ZLLS400.pdf p 2): VR 40 V; IFPK 0.85 A repetitive and IFSM 12 A for t ≤ 100 µs. The ≈ 1.2 A, few-ns turn-off pulse is above IFPK on paper (note F8, as 5.1). Gate power 12 nC × 15 V × 140 kHz = 25 mW per FET; R26 takes ≈ 10 mW, R53 ≈ 3.5 mW, R22 15² / 10k / 2 = 11 mW, all against 0805 / 0603 ratings of 125 / 100 mW. VGS max ±25 V (ST Table 2) against 15 V drive. |
| A11 | PASS | Crss 0.68 pF at VDS 100 V (ST Table 6) × 70 V/ns (worst simulated primary slope, `DAB_SIMULATION.md:212`) = 48 mA through R53 + RG,int + ROL (3.3 + 7.2 + 0.55 Ω) = 0.53 V, plus the Schottky VF ≈ 0.3 V, ≈ 0.85 V. VGS(th) min is 2 V (ST Table 4): margin 2.3×. The table has no Crss value below 100 V, where Crss is larger, but there the node slope is smaller (Coss also larger), so this is an estimate. The gate network is unchanged from 5.1. The driver CMTI is ≥ 125 V/ns (SLUSCJ9F p 9), above 70 V/ns. The FET's own dv/dt rating is a separate issue → F2. |
| A12 | PASS | Primary: the input dead time of 150 ns loses at most tPWD 6 ns + tDM 6.5 ns (−40…−10 °C; 5 ns above −10 °C) = 12.5 ns (SLUSCJ9F p 9) → ≥ 137.5 ns at the outputs. Secondary adds ISO2: PWD 4.5 ns + tsk(o) 2.5 ns (CA-IS376x §6.10.1/6.10.2) → ≥ 130.5 ns. Both are above the hardware DT maximum of 120 ns, and §8.4.2 never lets the output dead time fall below the programmed 80–120 ns. The slower 40 Ω turn-on adds further dead time at the gate. The checklist's "150 − 100 ns" budget does not apply literally, because hardware DT and firmware dead time do not add (the larger one wins). |
| B1 | PASS | `padgap`: DRV5.11–C95.2 0.59 mm (the checklist's "1.2 mm" is the track length in README Stage 8, not the pad gap). DRV5.9–C95.1 0.21 mm, with GND via (8.25, −54.345) at pin 9. C92: 0.42 mm to pin 16 and 0.41 mm to pin 14. C94: 0.70 mm to pin 3 and pin 4. Pin 8 is fed through B.Cu 5V copper (`drc_summary.py`: unconnected_items 0). |
| B2 | PASS | Out: pin 15 → 1.95 + 0.94 + 0.97 + 0.62 mm → R26 → 1.9 mm → Q19.G, ≈ 8.4 mm. Return: Q19.3 → (12.75 / 10.8, −52.06) → x 10.25 → C92.1 → pin 14, ≈ 8.8 mm, side by side on B.Cu 0.67–1.2 mm apart. Total ≈ 17 mm, below 40 mm. Pad polygon `rv bq loop DRV5.15 R26.1 R26.2 Q19.1 Q19.3 DRV5.14`: 21.6 mm / 22 mm². On 5.1 (`bq51 loop DRV5.10 …`) it was 55.8 mm, so 5.2 is 2.6× shorter. `near "Net-(Q19-G)"`: DC+ only at 0.635 mm, which is the Q19 pin pitch (one footprint); gate tracks are 1.22 mm from the DC+ pad and the return 1.25 mm. |
| B3 | PASS | Q7 return: DHB_CURRENT → R83 (4 mΩ, F.Cu (15.9, −64.0)) → GND 1.0 mm F.Cu → three GND vias 0.6/0.3 at (17.25 / 17.96 / 18.55, −64.9 … −64.55) → In1/In4 → via (8.25, −54.345) at pin 9. Pad loop 25.7 mm / 18 mm² (5.1: 32.2 mm / 41 mm²). DHB_LOW_GATE is 0.2 mm wide for 1.55 mm between the C95 pads. Its real peak is ≈ 1.3 A turn-off (3.3 Ω + 7.2 Ω RG,int), not 4.5 A, for ≈ 5 ns, with an average of 12 nC × 2 × 140 kHz ≈ 3.4 mA. That is acceptable for 1 oz copper; the extra inductance is ≈ 1.5 nH. |
| B4 | PASS | D30.A–R53.1 0.22 mm (same net). `near "Net-(D30-PadA)"`: Net-(D19-K) 0.255 mm (group), Net-(Q19-G) 0.47 mm (group), +1V65_BIAS 1.257 mm (≥ 1.2). `near "Net-(D19-K)"`: 15V 1.289 mm. Courtyard overlaps R53/D30, R41/D30, C92/R26, C92/DRV5, R90/D34, R92/D34, R90/R70 are courtyards only. Bodies from the positions: C92/R26 0.28 mm, R53/D30 0.15 mm, R41 body to the D30 A pad 0.33 mm, R90/D34 0.68 mm, so no body overlap. SMD pads near TO-220 pads (own script on the dump): R26.2 0.20 mm and R92.2 0.15 mm, both the same net as the gate pad (harmless). Different nets: R26.1 0.57, R92.1 0.52, D30.C 0.75 mm — all ≥ 0.5 mm for hand soldering. |
| B5 | PASS | 15V via (25.562, −48.6) → B.Cu 0.4 mm → D19 (anode 1.0 mm from the C96 15V pad) → Net-(D19-K) 0.5 mm → R41 → VDDA 0.3 / 0.4 mm → C92 / pin 16. At 7 A for the first-charge µs pulses and mA average, these widths are fine. Net-(D19-K) to non-group copper: 15V 1.289 mm, +1V65_BIAS ≥ 1.25 mm (≥ 1.2). Bootstrap recharge loop (pad polygon C96 → D19 → R41 → C92 → Q7 → R83 → C96): 70.3 mm / 258 mm²; 5.1: 67.2 mm / 208 mm² (comparable). |
| B6 | **FAIL** | `near` for all six group nets, outer layers: only pad pairs of one footprint (Q19 / Q7 pins 0.635 mm, DRV5 NC pad 13 0.67 mm) and group-internal gaps ≥ 0.2 mm, **except Q7.2 (DHB_HI_SOURCE) – R70.2 (GND), 0.883 mm on B.Cu**. That is a pad pair of two different footprints, passed only by the `!(Pad && Pad)` exemption of rule "HV functional, outer layers" (`.kicad_dru:56-59`) → F4. Inner layers: Q19.3 barrel to In3 15V / In1, In4 GND 0.50 mm (≥ 0.5). `rv bq nets` for the group: tracks on F.Cu / B.Cu only, none on inner layers. |
| B7 | **FAIL** | `padgap DRV5.11 DRV5.14` 3.21 mm edge to edge (NC pads 12 / 13 between, 0.67 mm each). No track, via or pour is connected to pads 12 / 13. But the B.Cu GND pour "Proteus B.Cu pour 4" fills under the DRV5 body from pin 9 up to 0.20 mm from pads 10–13 and **1.20 mm from pad 14** (switch node), measured with shapely on the stored fill. So GND (low side) copper shortens the 3.2 mm low-side ↔ high-side pad gap to 1.2 mm. SLUSCJ9F p 39 §11.1: "increase the creepage distance of the PCB layout between the high and low-side PCB traces"; channel-to-channel 1500 V (p 7) → F5. |
| B8 | PASS | Lanes on In3 (README Stage 4i). `near PRI_DHB_HI / B12 / DAB_DIS --within 1.0 --other-class` lists only PRIMARY_LV nets, no HV_PRIMARY. GND planes on In1 and In4 cover the lane rows (`xsec GND In4.GND y -46.15 -5 20`: −5 … 12.10 and 13.40 … 20; the only gap is the antipad of the Q19 gate barrel; In1 identical). So a GND plane lies between the lanes and both outer switch-node layers. R73 / R74 / R129 / C120 are at the driver (≤ 5 mm). |
| C1 | **FAIL** | `padgap DRV6.11 C43.2` **11.91 mm** edge (13.20 mm centres), `DRV6.11 C72.2` 13.25 mm, `DRV6.9 C43.1` 10.78 mm. Pin 11 goes by 1.6 mm B.Cu to via (57.957, −55.102) into the In3 15V_ISO_SEC plane; pin 9 goes to via (57.957, −52.562). 5.1 (`bq51 fp DRV6,C43`): pin 11 (66.807, −50.502) – C43.2 (63.53, −44.025) = 7.3 mm. → F1. The bootstrap capacitor is fine: C46 1.10 mm from pin 16, 3.75 mm from pin 14 (≤ 5 mm). VCCI: C93 1.19 mm from pin 8 (pin 3 is 8.3 mm away; the checklist says "C93 at pins 3 / 8", but the board has it at pin 8 only; that meets the "pin 3 **or** pin 8" criterion); pin 3 is fed (unconnected 0). |
| C2 | PASS | Q21: out ≈ 24 mm on B.Cu (`area.py` tracks: 1.3 + 7.5 + 1.18 + 1.8 + 3.32 + 2.17 mm + R57 + 4.6 mm); return Q21.3 → F.Cu 1.6 mm track x 55.45 → via (57.85, −58.912) → pin 14. `bq loop` along the copper: 48.9 mm / 92 mm². 5.1 out ≈ 17.5 mm (DHB_HI_GATE_SEC 12.55 mm + R57 + ≈ 3 mm) → 1.4×. Q8: out ≈ 29 mm (B.Cu 1.94, In3 0.3 mm × 17.23, B.Cu 4.7, R87, 2.44); 5.1 ≈ 16 mm (10.44 + R87 + 3.78) → 1.8×. Return in the ISO_GND planes; In4 under the lane `xsec ISO_GND In4.GND y -54.1 55 76`: 58.72 … 72.39 (gaps only at the two via antipads); In1 identical. Width 0.3 mm. Both are within 2× of 5.1, and the lane is documented (README:2122). |
| C3 | **FAIL** | `near` for the six secondary group nets, outer layers: Q21 / Q8 pin-pitch pairs 0.635 mm (one footprint), NC pad 13 0.67 mm (exempt by rule). **C72.1 (ISO_GND) – R46.1 (Net-(D18-K)) 1.175 mm** (pad pair of two footprints, below 1.2 mm) → F6. DHB_HI_GATE_SEC under the DRV6 body: 1.211 mm from DT pad 6, 1.254 mm from DAB_DIS_SEC, 1.296 mm from ISO_GND. These meet the rule but see F3. No group net on an inner layer (`rv bq nets`). |
| C4 | PASS | R75 / R76 at (73.2, −61.5 / −60.2), 6.7 mm from pins 1 / 2 (≤ 15 mm). The ISO_SEC_DHB_HI / LO lanes run on In2 (x 75–79, y −59.65 / −58.85) with the In1 ISO_GND plane solid between them and F.Cu (`xsec ISO_GND In1.GND y -60.0 60 80`: 20.0 mm, one piece). On F.Cu, DHB_HI_SOURCE_SEC comes no closer than 1.25 mm, at the two input vias. DAB_DIS_SEC: In2 36 mm, no local pull-down or capacitor at DRV6.5 (see F9). |
| D1 | PASS | `rv sch cmp51 2`: only pin 5 (EN 5V → DAB_DIS with pull-down) and pin 6 (NC → DT) differ functionally, besides the deliberate DRV5 channel swap. UCC21520 side checked: 8 V UVLO class (A7), TTL/CMOS inputs (A6), outputs non-inverting, tPWmin 20 ns (SLUSCJ9F p 9) against a half-length first pulse of ≥ 0.6 µs at 420 kHz. Both-inputs-high forces both outputs low (p 24). The Si8275 datasheet could not be fetched (Skyworks returned HTML), so the Si8275 side comes from the 5.1 symbol pin names (EN_5, NC6_6) only. |
| D2 | PASS | `rv sch cmp51 2`: R25, R40 only in 5.1; C118–C120, R127–R129 only in 5.2. They are on the board (`rv bq fp`) and in `kicad_next/fab/tube_psu_5_2_bom.csv` (C120 in the 1n line, C118 / C119 in the 100p line, R127–R129 in the 10k line) and `_cpl.csv`. |
| D3 | PASS | `rv bq fp DRV5`: pads 2.05 × 0.6, pitch 1.27, rows x −2.35 / 6.95 = 9.30 mm. SLUSCJ9F p 51 DW0016B land pattern example: 16X (2) × 16X (0.6), 14X (1.27), (9.3). |
| D4 | PASS (circuit) | `drc_summary.py erc`: ground_pin_not_ground 3 (DRV5.14, DRV6.14, DRV3.14 VSSA = switch node by design); 15 warnings in total. README:59 says "14 warnings … 2 ground_pin_not_ground" → documentation mismatch, note F10. |
| E1 | PASS (bring-up note) | With DC+ at 0 V: 15V at DRV5.11 / C95, 15V_ISO_SEC at DRV6.11; VDDA (C92 / C46) only after the low side has been on; DT pin ≈ 0.8 V (SLUSCJ9F p 24 §8.4.2); DIS low; VCCI 5 V at C94 / C93. No dedicated test points. Gate probes from the bottom side: Q19 G-S across R22 (gate pad 1, source pad 2, floating – needs an isolated / differential probe); Q7 across R70 (gate / GND); Q21 across R56; Q8 at R88.2 / R87.2 against C43.1 (ISO_GND). With the heatsink on the top side these B.Cu pads stay reachable only if the bottom side is accessible in the enclosure (not in the repository). |
| E2 | PASS (handover note) | J2-4 = primary high side (Q19), J2-6 = primary low side (Q7), J2-10 = Q21, J2-12 = Q8; J2-18 high = all four gates off (pull-down = enabled when not driven). Hardware DT 80–120 ns (10k); firmware dead time ≥ 130 ns at the gates for 150 ns at the pins (A12); do not go below ≈ 125 ns at the FPGA, or DT takes over. Bootstrap: turn the low sides on first, for several µs (τ ≈ 2 µs per cycle; TI p 32 note on large CBOOT). Soft start by frequency (≥ 420 kHz) per DAB_SIMULATION.md §3. |

## Findings (ranked, most severe first)

### F1 DRV6 VDDB (pin 11) has no decoupling capacitor near the pins
- Severity: **should fix** (worse than 5.1; datasheet "must")
- What is wrong: the nearest 15V_ISO_SEC capacitors are C43 (11.9 mm edge to edge, 13.2 mm centres) and C72 (13.3 mm).
  Pin 11 and pin 9 each reach the In3 / In4 planes through one via at x 57.957. On 5.1, C43 stood 7.3 mm from pin 11.
  SLUSCJ9F p 39 §11.1: "Low-ESR and low-ESL capacitors must be connected close to the device between … the VDD
  and VSS pins". The Q8 turn-on current (≈ 0.3 A in a few ns) is fed through ≈ 25 mm of plane path, and the VDD pin
  sees the resulting ringing.
- Evidence: `rv bq padgap DRV6.11 C43.2` → 11.911 mm; `rv bq51 fp DRV6,C43` → 5.1 centres 7.3 mm;
  `area.py` tracks: 15V_ISO_SEC B.Cu (56.357, −55.102) → (57.957, −55.102) 1.6 mm + via.
- Smallest fix: add one 0603 (1 µF X7R 50 V, C15849 class, or the 4.7 µF part) on B.Cu west of the DRV6 pin row,
  standing north–south at about x 54.3, y −52.6 … −55.1. B.Cu has no copper at x 48–55.3, y −58 … −50 (checked); it is
  2.3 mm east of the barrier slot edge (x 52.015) and > 3 mm from pin 14. Short tracks go to pins 11 / 9 (or onto their
  existing 1.6 mm stubs). Reviewer 10 should confirm creepage around the slot.
- Confidence: high that the capacitor is missing; medium on how much it matters (5.1 worked at 7.3 mm). A bench look at VDDB
  ringing would settle it.

### F2 Simulated primary switch-node slope exceeds the STF7N60M2 dv/dt rating on paper
- Severity: **should fix** (rating exceeded on paper; the cure is in the power stage, checklist 07)
- What is wrong: DAB_SIMULATION.md:212 gives a node dv/dt of **63–70 V/ns (primary)** and 32–36 V/ns (secondary). The
  STF7N60M2 datasheet (DocID024894 Rev 1, June 2013, Table 2,
  https://static.chipdip.ru/lib/210/DOC005210689.pdf) rates "MOSFET dv/dt ruggedness **50 V/ns** (VDS ≤ 480 V)" and
  "peak diode recovery 15 V/ns". 70 V/ns is 1.4× the first. The newer ST revision (DS9793 Rev 2) timed out and
  could not be checked. The gate network is not the limit: in ZVS the slope is set by the turn-off current and Coss,
  not by R53 / R92. The Miller pull-up stays below VGS(th) (A11) and the driver CMTI of 125 V/ns is met. 5.1 used the
  same FET and gate network; its slope is not in the repository, so the comparison with 5.1 cannot be made.
- Evidence: the two numbers above; ST Table 2 note 3.
- Smallest fix: measure the node slope on the first board (100 MHz+ probe at Q7 D-S). If it is > 50 V/ns, slow the
  edge without loss by adding C_DS (e.g. a few tens of pF, 1 kV C0G) across Q7 / Q19. This costs ZVS dead-time margin
  (36 ns margin on a 114 ns no-load swing, §3), so checklist 07 / the simulation should size it. Alternatively, ask ST
  whether the 50 V/ns rating applies to ZVS edges.
- Confidence: medium. The rating is clear; how much the simulated peak slope (at the low-Coss end of the swing) stresses
  the part is not.

### F3 Secondary high-side gate track under the DRV6 body, 1.21 mm from the input-side DT pad
- Severity: **should fix** (worse than 5.1; against the datasheet layout note)
- What is wrong: DHB_HI_GATE_SEC (0 ↔ 435 V at 32–36 V/ns) runs as a B.Cu diagonal (57.657, −60.182) → (62.957,
  −54.882) → (63.093, −54.693) across the space under the DRV6 package. It passes **1.211 mm** from DT pad 6 (a
  10 kΩ ‖ 100 pF node), 1.254 mm from DAB_DIS_SEC and 1.296 mm from ISO_GND. This shortens the package's 7.25 mm
  input ↔ output pad-row distance to 1.2 mm. SLUSCJ9F §11.1: "avoid placing any PCB traces or copper below the driver
  device" and "increase the creepage distance … between the high and low-side PCB traces". Coupling ≈ 0.1 pF ×
  435 V ≈ 40 pC per edge into the DT node (≈ 0.4 V on 100 pF, against a 0.8 V nominal) is enough to disturb the
  dead-time timer. On 5.1 the nearest switch-node copper to DRV6 input-side copper was 2.37 mm (`bq51 near
  DHB_HI_SOURCE_SEC --within 2.5`: 5V_ISOL 2.370 mm). It meets the 1.2 mm rule, so the DRC is clean.
- Evidence: `rv bq dist DHB_HI_GATE_SEC "Net-(DRV6-DT)" --layer B.Cu` → 1.211 mm at (63.44, −54.76) / (64.63, −54.95).
- Smallest fix: reroute the diagonal to run north at x ≈ 60.3. That keeps 1.2 mm to the ISO_GND / 15V_ISO_SEC /
  DHB_LOW_GATE_SEC vias at x 57.96–58.3 and leaves ≈ 3.9 mm to the input pad row. Then continue to (62.3, −52.1) →
  D31 / R57 as now. Not tried on the board.
- Confidence: medium (geometry measured; the size of the DT disturbance is an estimate).

### F4 Q7 switch-node pad 0.88 mm from the GND pad of R70
- Severity: **note**
- What is wrong: R70 (Q7 G-S 10k) pad 2 = GND sits 0.883 mm from Q7 pin 2 (DHB_HI_SOURCE, 0–400 V) on B.Cu. The
  project rule "HV functional, outer layers" (1.2 mm) is passed only because both items are pads; the exemption is
  meant for package pin pitch, but these are two footprints. The stress is no higher than between the TO-220's own pins
  (0.635 mm), so it is not unsafe. On 5.1, R70 was far from Q7 (`bq51`: R70 at (28.7, −45.0)).
- Evidence: own pad-pair script on `b52.json` → `0.883 Q7.2 [DHB_HI_SOURCE] – R70.2 [GND]`; `rv bq near
  DHB_HI_SOURCE` → GND 0.883 mm at (11.75, −60.71) / (10.88, −60.62).
- Smallest fix: move R70 0.35 mm west (or turn it so that its GND pad faces away from Q7.2).
- Confidence: high.

### F5 GND pour under DRV5 comes to 1.20 mm of the switch-node pin 14
- Severity: **note** (meets the 1.2 mm rule; 5.1's DRV6 had switch-node copper 0.30 mm beside its NC pads)
- What is wrong: "Proteus B.Cu pour 4" (GND, joined to pin 9) fills under the DRV5 body to 0.20 mm from pads 10–13
  and 1.201 mm from pad 14. This replaces the 3.2 mm pin-11 ↔ pin-14 gap (with the NC pads as spacers) by 1.2 mm of
  GND ↔ 400 V, under the body where flux collects. This is the lead "GND copper 0.2 mm from NC pad 12": confirmed, and
  the gap that matters is 1.20 mm, to pin 14.
- Evidence: shapely distance of the stored fill to the DRV5 pads: 9 0.000, 10–13 0.200, 14 1.201, 15 2.339,
  16 3.563 mm.
- Smallest fix: a B.Cu keep-out rule area for zone fill under DRV5, north of y ≈ −51.2. Pin 9 and pin 11's C95 keep
  their copper.
- Confidence: high on the geometry.

### F6 C72 GND pad 1.175 mm from the bootstrap node pad of R46
- Severity: **note**
- What is wrong: C72.1 (ISO_GND) – R46.1 (Net-(D18-K), swings with the secondary switch node 0–435 V) is 1.175 mm
  on B.Cu, 0.025 mm under the 1.2 mm functional rule. It passes through the pad-pad exemption.
- Evidence: pad-pair script → `1.175 C72.1 [ISO_GND] R46.1 [Net-(D18-K)]`; `rv bq near "Net-(D18-K)"` → ISO_GND
  1.175 mm.
- Smallest fix: move C72 0.1 mm east. This can be combined with F1 (C72 could then move to DRV6, but it is the D18
  anode bypass, so keep it near D18).
- Confidence: high.

### F7 C95 derating: enough at the pins, less than 5.1
- Severity: **note** (lead "derating not calculated": now estimated)
- What is wrong: CGA0603X5R475K250JT has no DC-bias curve in its datasheet. Estimated ≈ 0.9–1.3 µF at 15 V
  (typical 0603 25 V X5R retention 25–35 % on 3.6 µF after tolerance and temperature). The pin-local requirement is
  240 nF (10 × 12 nC / 0.5 V), so the margin is ≥ 3.7×. 5.1's 1206 X7R 50 V kept ≈ 3 µF, so 5.2 has about a third of
  the bulk at the pins. C96 (1 µF 1206 at D19, 20 mm away) and the 15V plane add to it. TI suggests ≈ 10 µF
  (SLUSCJ9F p 38), which neither board meets.
- Smallest fix (only if wanted): a 10 µF 25 V (or 4.7 µF 50 V) 0603 in the same footprint (JLC stock not checked).
- Confidence: medium. The part's DC-bias data is missing; a curve for C6119856 or a measurement would raise it.

### F8 ZLLS400 turn-off peak above its repetitive peak rating on paper (as 5.1)
- Severity: **note**
- What is wrong: the turn-off pulse is ≈ (15 − 0.6) / (3.3 + 7.2 + 0.55) ≈ 1.2–1.3 A for ≈ 5 ns. DS33226 Rev 10-2
  gives IFPK 0.85 A ("rectangular pulse duty cycle") and IFSM 12 A (t ≤ 100 µs). The duty is ≈ 0.07 %, so thermally
  negligible, and the network is identical to the bench-verified 5.1.
- Smallest fix: none needed. Document it.
- Confidence: medium (the IFPK conditions are not fully stated in the text of the datasheet).

### F9 DRV6 DT network and DISABLE input are not local
- Severity: **note**
- What is wrong: R128 / C119 are 5.2 / 5.8 mm from DRV6 pin 6, reached through two vias and 5.75 mm of F.Cu. TI asks
  for them close to the DT pin (§11.1, §8.4.2). DAB_DIS_SEC arrives over ≈ 42 mm from ISO2 with no ≈ 1 nF at pin 5
  (TI §7.3 recommends one "when connecting … with distance"). It is driven push-pull by ISO2, so the risk is low. DRV5
  has both locally.
- Smallest fix: none required. If F3's reroute frees the room, put C119 next to pin 6.
- Confidence: medium.

### F10 README ERC count is stale
- Severity: **note** (documentation)
- What is wrong: `kicad_next/README.md:59` says "14 warnings … 2 ground_pin_not_ground"; `reports/next/erc.rpt` has 15
  warnings, of which 3 are ground_pin_not_ground (DRV5.14, DRV6.14, DRV3.14).
- Smallest fix: change the README line to 15 / 3.
- Confidence: high.

### F11 S1M bootstrap diodes: recovery not specified
- Severity: **note** (as 5.1)
- What is wrong: TI recommends fast-recovery or SiC bootstrap diodes (SLUSCJ9F p 27). The ordered MDD S1M (C64915,
  Rev 2025A4) datasheet gives no trr / Qrr, so the recovery loss cannot be calculated. In steady state the diode
  carries only mA when the node rises (A8), so the stored charge is small. 5.1 used the same diode and works.
- Smallest fix: none for ordering. If a fast part is wanted later, use a 1000 V fast-recovery diode in SMA (e.g. RS1M
  class), same footprint.
- Confidence: medium.

## Compared with 5.1
- **Better:** primary gate loops are 2.6× (high side, 21.6 vs 55.8 mm pad path) and 1.25× (low side, 25.7 vs 32.2 mm)
  shorter. Hardware dead time (DT 100 ns) is a new backstop against overlap (5.1: Si8275 NC on pin 6). DISABLE is a new
  all-gates-off input. C95 sits 0.6 mm from VDDB (5.1 1206 at 2.5 mm). All gate-group nets stay on the outer layers,
  with inner planes under the input lanes.
- **Equal:** gate network values and topology (A10), bootstrap network (A8), bootstrap recharge loop (70 vs 67 mm),
  J2 functions (A2, A3), UVLO class.
- **Worse:** DRV6 VDDB decoupling distance 13.2 vs 7.3 mm (F1); secondary gate paths 1.4× (Q21) and 1.8× (Q8) longer,
  the Q21 return taking a separate F.Cu route (C2); the gate track under the DRV6 body is closer to the input side,
  1.21 vs ≈ 2.4 mm (F3); C95 effective capacitance about a third of 5.1's (F7); R70 pad 0.88 mm from Q7.2 (F4).

## Could not verify
- STF7N60M2 current revision (DS9793 Rev 2, April 2026): the st.com fetch timed out; DocID024894 Rev 1 (2013) was used.
- DC-bias curve of CGA0603X5R475K250JT (HRE, C6119856): not in its datasheet. A9 / F7 use a typical-class estimate.
- S1M trr / Qrr: not in the MDD datasheet of the ordered part.
- Si8275BB datasheet (5.1 driver): the Skyworks URL returned HTML. D1 is judged from the UCC21520 datasheet and the 5.1
  symbol pin names.
- The 5.1 switch-node dv/dt (no 5.1 simulation or measurement in the repository), needed to compare F2 with 5.1.
- The real node slope, VDDB ringing on DRV6 and the bootstrap start-up need bench measurements.
- J2-18 / J2-4 / J2-6 state while the FPGA is configuring (internal pull-ups against the 10 k pull-downs): card side,
  not in the repository.

## Outside scope
- **07 power stage:** start-up hard switching (DAB_SIMULATION.md §2.8: first ≈ 10 periods with 30 A body-diode
  recovery) far exceeds the STF7N60M2 peak diode recovery rating of 15 V/ns; the balancing resistors recommended in §3
  are not on the board. The C_DS question of F2 also belongs there.
- **01 aux flyback / docs:** `simulation/flyback/EEL19_DESIGN.md:127` and `:277` still name the DRV5 / DRV6 as
  Si8275BB (now UCC21520DWR; the numbers still hold: 8 V UVLO, 30 V abs max).
- **03 / 10:** CA-IS3761LW reinforced certificates are still "pending" in its 2019 datasheet (CHANGES open question 2).
- **10 creepage:** the extra capacitor proposed in F1 sits 2.3 mm from the primary/secondary barrier slot
  (x 50.8–52.0); check it when it is placed.
