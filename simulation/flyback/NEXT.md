# TR1 flyback study – session 4 (2026-11-18): reinforced isolation → TIW build

**The user requires reinforced primary ↔ secondary isolation**: 552 Vrms / 778 Vpk, 11.1 mm
creepage, 4.0 mm clearance (kicad_next/README.md). The 3 + 3 mm margins of the enamel EEL19
build are too small. Details: [EEL19_DESIGN.md](EEL19_DESIGN.md) section 12, tables in
[eel19_results.md](eel19_results.md).

- **New recommendation: `eel19_tiw_sandwich_s_pre3`.** MAS:
  [mas/tr1_eel19_tiw_recommended.json](mas/tr1_eel19_tiw_recommended.json).
  - Build: P1 52 (AWG32, spread over the full 21.2 mm) | S15 16 (2 × TEX-E 0.30) |
    SHV 84 (TEX-E 0.20, 2 layers) | S5+SN5 6+6 (3 + 3 × TEX-E 0.30, one bundle) | A5 6 (8 × AWG30) |
    A15 16 (3 × AWG30) | P2 52 (AWG32 spread).
  - No margins, 1 tape layer between sections.
  - Same turns, Lp 600 µH, Rsense 1.0 Ω and preloads as before; spacer gap.
  - P–S leakage 14 µH (enamel 20 µH); P with everything shorted 3.1 µH (enamel 8.9 µH).
- **Results** (iW1819 model):

  | rail / quantity | TIW build | enamel b_pre3 |
  |---|---|---|
  | 15V | 14.44–15.45 V | 14.59–15.97 V |
  | 5V | 4.79–5.16 V | 4.83–5.22 V |
  | 15V_ISO_SEC | 15.02–17.42 V | 14.91–16.75 V |
  | 5V_ISOL | 4.90–5.34 V | |
  | −5V | 4.93–5.29 V | |
  | −80 V | 80.5–84.1 V | |
  | Vcol at full15 | 568 V | 603 V |
  | winding loss at full15 (MKF upper bound) | 1.56 W | 1.22 W |
  | window radial build | 83 % | 69 % |

  ΔT ≈ 41 °C at 15 W.
- **Alternative `eel19_tiw_paired_ms_pre3`** (15 V and 5 V windings each in one shared
  multifilar layer, primary spread): best 15 V tracking (14.4–15.3 V on both 15 V rails), but
  5V_ISOL / −5V reach 5.6–5.7 V at bleeder-only load, and it is harder to wind.
- **Rejected:**
  - Paired variants with a close-wound primary: MKF winding loss 3.6–5 W at 15 W.
  - Simple order: 15V reaches 18.5 V.
  - Close-wound AWG32 primary: P–S leakage 47 µH.
- **Buy:** Furukawa TEX-E 0.30 mm and 0.20 mm, about 10 m each (e.g. Block CU-TIW 100/0,30 and
  100/0,20). Solder-pot tinning at ≈ 420–450 °C, or strip only the pin wrap.
- **Core = primary.** Wrap the bottom yoke / outer legs with 3 tape layers (the secondary pin
  wraps are within 11.1 mm of the core). Hipot: primary + core → isolated pins, 3 kV rms.
  PD test on the first samples (778 Vpk recurring).
- **PCB:** the TR1 footprint (`tools/next/gen_next_footprints.py` →
  `lib/tube_psu_next.pretty/Transformer_EEL19_V_4+6_FlyLeads`) now has a **1.2 × 26.5 mm milled
  slot on Edge.Cuts** on the row midline, y −10 … +16.5.
  - Minimum creepage between primary and isolated pads is now 13.18 mm (was 9.23 mm FL_DC → pin 5
    and 10.8 mm row to row).
  - The fly-lead holes can stay where they were.
- **TR3 (DAB, option B 20:21):** the 5 mm divider gives only ≈ 9.2 mm creepage, and the
  secondary is ≈ 3 mm from the core, so 3 tape layers do not make it reinforced.
  - **Secondary in reinforced-jacket litz** (135 × 0.071, IEC 62368-1 Annex J: Elektrisola
    EFOLIT, NEWind FEP, Rubadue TCA3 litz; OD ≤ 1.6 mm, 7 turns per layer × 3).
  - Rerun: Lsc 40 µH and losses 2.23 W (unchanged); gap 0.34 mm.
  - See DAB_TRANSFORMER.md section 8.
- **Controller change pending:** the iW1819 is hard to get, and the user proposes the
  **Infineon ICE5AR4780BZS**.
  - The magnetics carry over: winding structure, leakage, isolation, footprint and slot.
  - The **rail voltages, light-load excursions, Vcol and losses depend on the iW1819 model**
    and must be redone.
  - The follow-up needs to model:
    - 100 kHz fixed-frequency peak-current mode (DCM at 15 W with Lp 600 µH: Ipk ≈ 0.75 A;
      BCM only at about 50 W), with jitter;
    - Rcs ≈ 0.8 Ω (CS limit 0.8 V → 1.0 A, so the same Bpk 0.247 T / OCP margin), and leading-edge
      blanking;
    - regulation by a resistor divider from the primary-side **5V** rail into VERR (internal
      transconductance amplifier, ref 1.80 V) instead of PSR knee sampling. The A5 winding then
      feeds 5V directly, and AUX_FB / the Vsense divider go away. The cross regulation then
      depends on the 5V rail's own load, not the knee, so rerun all 19 cases;
    - Active Burst Mode (≈ 83 kHz bursts, selectable entry / exit levels) instead of
      PFM / DPWM / DDPWM. The light-load cases (min_*, light, idle) and the preload values need
      a new look;
    - VCC from A15 / 15V: on / off 16 / 10 V, VCC OVP ≈ 25.5 V. Check that 15V stays below the
      OVP in min_15V, and that start-up works with the 16 V turn-on threshold;
    - CoolMOS 800 V, 4.13 Ω: conduction loss about 0.2 W at 15 W; output capacitance in place of
      the BJT model (affects the snubber and Vcol);
    - possibly fewer turns for 100 kHz (same Bpk at Ipk 1.0 A). Keep 104 T unless the regulation
      structure changes the 6 T A5 requirement.

---

# TR1 flyback study – where it stands (session 3, 2026-11-17: new EEL19 transformer)

**Session 3 (2026-11-17): the user chose a NEW transformer on an EEL19 core** (vertical 5+5
bobbin, PC40, primary on fly leads, enamel + 3 mm margins, 10–15 W). Design:
[EEL19_DESIGN.md](EEL19_DESIGN.md), tables [eel19_results.md](eel19_results.md), MAS
[mas/tr1_eel19_recommended.json](mas/tr1_eel19_recommended.json). The EF20 study below stays as
it was (its results reproduce; EF20 netlists / matrices unchanged).

- Recommended: **`eel19_sandwich_b_pre3`, spacer gap**.
  - Turns: P1 52 ‖ S15 16 | SHV 84 | S5+SN5 6+6 ‖ A5 6 | A15 16 | P2 52, i.e. every EF20 turn
    count × 2. The Vsense divider and Vor stay the same.
  - Lp 600 µH; spacer about 0.4 mm, set by measurement (30 T test coil → 50 µH).
  - **R8 = R9 = 2.0 Ω** (Rsense 1.0 Ω).
  - Preloads 2.2k on 15V, 1k on 5V, 3.3k on 15V_ISO_SEC (R124 → 2.61k).
  - Pin 5 is the P1–P2 crossover post; pins 4/5 have no net; 2 fly-lead holes.
- Results over the 15 standard cases:

  | rail | EEL19 recommended | EF20 recommendation |
  |---|---|---|
  | 15V | 14.59–15.97 V | 14.40–15.78 V |
  | 5V | 4.83–5.22 V | 4.85–5.22 V |
  | 15V_ISO_SEC | 14.91–16.75 V | 14.75–17.07 V |

  The other rails are better. 15 W out: Pin 17.1 W, Ipk 0.84 A of 1.0 A, Vcol 603 V,
  Bpk 0.21 T (0.284 T at OCP).
- IW1818 is rated 10–12 W, so 15 W continuous is above the IC rating. Measure the pin-3
  temperature, or use the iW1819 (board change).
- Board: no drop-in. TR1 +0.93 mm in x, about 9 parts move, and the ISO_GND F.Cu pour is pulled
  back (this also fixes an existing 5.08 mm DC+ creepage spot).
- Si8275BB (UVLO 8 V) replaces the "Si8274 UVLO grade" question: every 15 V rail stays ≥ 14.45 V
  and ≤ 16.75 V.
- Answered 2026-11-17: height OK (lots of room), board move OK, 0.2 W preloads OK, D8 fitted
  is a 1000 V diode (OK). 12 W continuous is enough; iW1819-00 (in stock at DigiKey/Mouser)
  may replace the IW1818 in the next revision. Still open: real core / bobbin dims (calipers). See EEL19_DESIGN.md 9–10.
- Commands: EEL19_DESIGN.md 11. Use `--jobs 4` while other simulations run (3 GB total budget).

---

# Session 2 status (EF20 rewind, 2026-11-16)

Task: improve the cross regulation of the auxiliary flyback (sheet 1, IW1818 + TR1 EF20)
with an OpenMagnetics-designed rewind; design study only (schematic / board unchanged).
Findings: [FLYBACK_DESIGN.md](FLYBACK_DESIGN.md), tables: [results.md](results.md).

## Status

Steps 0–5 of the session-2 prompt are done.

0. **Calibration** (FLYBACK_DESIGN.md 2.1): model changes in `flyback_sim.py` – fixed 15V
   load 9.5 mA (IW1818 + Si827x supplies, was 5 mA) + AUX_MEAS divider 26.7 kΩ (was
   missing), iW1819-type light-load modes (PFM → DPWM 25 kHz → Ipk min 0.185 A → DDPWM
   2.1 kHz; the old model limit-cycled at a 2.4 kHz floor), PI gains scaled with the output
   power, knee sample at 0.2 At with 80 ns tracking, ES1D rectifiers with reverse-voltage
   measurement; new case `idle` (calibration point). Result: 15V idle 15.95 V (measured
   15.5 V). The old 20.6 V was the *min_15V* case, not light load; it is 19.92 V on the
   calibrated model (still above 18.7 V).
1. **MKF leakage grid**: converged (default / fine / mirroring 3 within 1 %). The high
   A5–S5 leakage of tiw_sandwich came from the layout ("bifilar" alternated whole 3-strand
   turns); new om_model mode `multifilar` (strand by strand) used for all bifilar/trifilar
   sections.
2. **All options simulated** on the calibrated model (15 cases at 400 V + nom325), incl.
   new margin-tape candidates and TIW references.
3. **cscale = 1 check**: scaled capacitors bias the levels by +0.03…+0.2 V (+1 V on −80 V),
   same direction for every option.
4. **Losses / Bpk / isolation / Vpeak** per option: results.md and FLYBACK_DESIGN.md 4.
5. **Recommendation** (user has no TIW → enamel + 3 mm margins): **`margin_sandwich_8_pre`**
   = P1 26 T ‖ S15 8 T | S5+SN5 bifilar | SHV 42 T ‖ A5 3 T | A15 8 T | P2 26 T, two 4-layer
   barriers, spread strands, preloads 3.3 kΩ on 15V and 1 kΩ on 5V. Winding spec in
   FLYBACK_DESIGN.md 5, `mas/tr1_recommended.json` (option `recommended`).
   15V 14.40–15.78 V (was 14.94–19.92), 5V 4.85–5.22 (4.87–6.14), 15V_ISO_SEC 14.75 V
   nominal (12.94), 14.75–17.07 V (optional 3.3 kΩ preload on 15V_ISO_SEC: 14.78–15.87).
   **D8 finding**: 389–403 V reverse at DC+ 400 V – a 200 V ES1D is overstressed, fit
   ≥ 600 V (ES1J / US1J).

Parallel pool (`run_flyback.py --jobs 8`, 3 GB ngspice budget): 96 cases / 6 options in
747 s wall, peak 2.1 GB ngspice memory (8 idle cases at once ≈ 260 MB each); 64 cases in
666 s, peak 1.0 GB; 32 cases in 331 s, peak 0.97 GB. (Sequential before: ≈ 15–17 min per
option.)

## Open questions for the user

1. Is the split primary acceptable (P1–P2 crossover in a reinforced sleeve across both
   barriers, in the margin zone; all 10 pins are used)? If not: `stacked` (no split, 15V
   max 17.7 V, 15V_ISO_SEC still ≈ 12.8 V) or margin_order_8 (5V rail runs high).
2. May 15V_ISO_SEC also get a preload (3.3 kΩ more, or R124 12.1 kΩ → 2.7 kΩ, 83 mW)?
   It removes the 17 V excursion when that rail carries only its bleeder.
3. ~~Which part is really fitted at D8?~~ Answered: a 1000 V diode (OK). Can the D8 reverse voltage /
   ringing be measured?
4. Bench data to tighten the calibration: 5V at idle (model 4.7–4.9 V), 15V with the
   isolated outputs loaded and the primary gate drivers idle (model 19.9 V on today's
   transformer), real idle loads on 5V (MCU board) and the IW1818 Vcc current.
5. Si8274 VDDB UVLO grade (15V_ISO_SEC moves from ≈ 12.9 V to ≈ 14.75 V with 8 T).

## Known limitations

- *idle* / *light* hunt slowly between the light-load modes (±0.3–0.5 V on 15V); values are
  10 ms / 5 ms averages. Light-load control law partly assumed (iW1819 data).
- Model 15V idle +0.45 V above the measurement (no HF damping, estimated idle loads).
- MKF core-loss models disagree (0.01–0.41 W); not used for decisions.
- `checks.py d8bv200` (200 V breakdown at D8) does not converge in ngspice.
- Do not `pkill -f run_flyback` from a shell whose command line contains that string; kill
  by PID.

## Commands

```
cd /home/jari/dev/tube_psu_kicad
python3 simulation/flyback/run_flyback.py --om-only current recommended            # MAS files
python3 simulation/flyback/run_flyback.py margin_sandwich_8_pre --jobs 8           # cached cases are skipped
python3 simulation/flyback/run_flyback.py --report current stacked margin_sandwich margin_sandwich_8 \
    margin_sandwich_8_pre margin_sandwich_8_pre3 margin_sandwich_8b_pre margin_order_8 margin_order_8_pre \
    tiw_simple tiw_sandwich tiw_sandwich_stacked tiw_recommended tiw_recommended_pre \
    sandwich_paired_b sandwich_paired_c sandwich_paired_c_pre
python3 simulation/flyback/losses.py margin_sandwich_8_pre
python3 simulation/flyback/checks.py cscale
```

run_flyback.py runs the load cases in a pool (`--jobs N`, default 8, total ngspice RAM
budget 3 GB enforced from /proc; user rule since 2026-11-16 – do not start several
run_flyback.py processes on top of the pool). Cached results: `out/results/<option>__<case>.json`
(git-ignored); delete to rerun.

## Prompt for the next session

> Continue the TR1 flyback study in /home/jari/dev/tube_psu_kicad (simulation/flyback/,
> read NEXT.md, EEL19_DESIGN.md and FLYBACK_DESIGN.md first; the current design is the EEL19
> transformer `eel19_sandwich_b_pre3`; apply the user's caliper data / first-sample
> measurements from EEL19_DESIGN.md section 9 and recalibrate). Rules: up to 8 parallel simulations within
> 3 GB total (run_flyback.py --jobs), scratchpad for temp files, do not change the
> schematic/board, commit after each step (trailer Co-Authored-By: Claude Opus 5.5
> <noreply@anthropic.com>), do not push. Apply the user's answers to the open questions in
> NEXT.md (split primary acceptable? 15V_ISO_SEC preload? D8 part? bench data), recalibrate
> if new bench data arrive, and finalise the rewind spec (FLYBACK_DESIGN.md 5,
> mas/tr1_recommended.json). The user has no triple-insulated wire: enamel + 3 mm margins.
