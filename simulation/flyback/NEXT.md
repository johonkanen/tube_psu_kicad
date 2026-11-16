# TR1 flyback study – where it stands (session 2, 2026-11-16, in progress)

**Session 2 status (update at each commit):**
- Step 0 (calibration) – model changes done (flyback_sim.py: 15V fixed load 9.5 mA +
  AUX_MEAS divider, iW1819-type multi-mode light-load law, load-scaled PI gains, knee
  0.2 At / 80 ns tracking, ES1D rectifiers with reverse-voltage measurement; run_flyback.py:
  new `idle` case = calibration point, long averaging for idle/light). See
  FLYBACK_DESIGN.md 2.1. All cached results were deleted (old model); old results copied to
  the session scratchpad only.
- Step 1 (MKF leakage grid) – done: grid converged (default vs fine vs mirroring 3 within
  1 %); the high A5–S5 leakage of tiw_sandwich came from the layout mode "bifilar"
  (alternating whole 3-strand turns). New om_model mode "multifilar" (strand by strand);
  all bifilar/trifilar sections in options.py use it (tiw_sandwich A5–S5 15.8 → 4.1 µH).
- Step 0 results (current transformer, calibrated model, 16 cases + nom325): 15V idle
  15.95 V (measured 15.5 V), light 16.64 V, nominal 15.44 V, worst case min_15V 19.92 V
  (isolated rails loaded, primary 15V only its fixed load) – exceeds 18.7 V. D8 reverse
  389–402 V at 400 V (341 V at 325 V): 200 V ES1D overstressed (FLYBACK_DESIGN.md 6).
- Step 2 partial results (calibrated): current, tiw_sandwich, tiw_simple, recommended done
  (see results.md); recommended_pre, stacked, tiw_sandwich_stacked, margin_sandwich running.
  Added options sandwich_paired_b / _c (15 V pair and 5 V triple each in one multifilar
  layer) – to run after the batch: `run_flyback.py --om-only sandwich_paired_b
  sandwich_paired_c`, then each option.
- Step 2 – batch running: `--om-only --force` for all options, then current, tiw_sandwich,
  tiw_simple, recommended, recommended_pre, stacked, tiw_sandwich_stacked, margin_sandwich
  (one ngspice at a time). If stopped: rerun the same commands; cached cases are skipped.
- Steps 3–5 not started.

Task: improve the cross regulation of the auxiliary flyback (sheet 1, IW1818 + TR1 EF20)
with an OpenMagnetics-designed rewind; design study only (schematic / board unchanged).
Findings so far: [FLYBACK_DESIGN.md](FLYBACK_DESIGN.md) (unfinished sections marked
TODO), tables: [results.md](results.md).

## Done

1. **PyOpenMagnetics 1.7.41** installed (`pip install --user PyOpenMagnetics`), works.
   `om_model.py` places turns itself (MKF `wind()` ignores tape thickness, cannot do
   bifilar layers) and gets the inductance matrix / leakage / Rdc from MKF; checked against
   `wind()` (21.9 vs 22.2 µH). Gap fitted to Lp = 171 nH × 52² = 462 µH (0.319 mm).
   `mas/tr1_current.json` written.
2. **Current V2 build modelled** (user-confirmed: 52/8/3‖7/3/3/42, six separate windings,
   3 mm margins, 4 tape layers at the barrier). Leakage referred to the primary: P–S15 24,
   P–S5 45, P–SN5 52, P–SHV 34 µH; A5–S5 32, A5–SN5 43 µH.
3. **ngspice flyback model** (`flyback_sim.py`) with the full coupled-inductor matrix and a
   behavioural IW1818 (knee sampling, PI, PWM/PFM). 35–70 s per run, ≈150 MB.
4. **Cross regulation, 15 load cases at 400 V + nominal at 325 V** – finished for
   `current`, `stacked`, `tiw_simple`; `tiw_sandwich` 6 of 15 (nom, min_*).

   | option | 15V max (≤ 18.7 V) | 5V max | 15V_ISO_SEC | 5V_ISOL | −5V_SEC | −100V BIAS |
   |---|---|---|---|---|---|---|
   | current | **20.56 (exceeds)** | 6.45 | 12.60–14.36 | 4.85–5.33 | 4.94–5.36 | 77.9–81.1 |
   | stacked | 17.95 | 5.91 | 12.35–13.30 | 4.82–5.31 | 4.89–5.59 | 77.4–82.2 |
   | tiw_simple | 17.09 | 5.95 | 12.67–13.92 | 4.82–5.29 | 4.86–5.26 | 79.1–80.9 |
   | tiw_sandwich (6/15) | 16.37 | 5.71 | 12.45–14.47 | 4.82–5.19 | 4.75–5.08 | 79.2–80.0 |

   Other findings: 15V_ISO_SEC is ≈ 12.7 V with 7 T (target 15 V → 8 T); ES1A (50 V) on
   D8 sees ≈ 420 V reverse, on D4/D5 70–80 V; collector peak 539–589 V.
5. `losses.py` works (current nom: winding losses 0.148 W; core losses model-dependent
   0.11–1.46 W, same for all options). `report.py` → results.md, PNGs.

## In progress / not started

- **tiw_sandwich**: 9 cases left (max_*, light, nom325). Before trusting it, check MKF's
  leakage for windings sharing one layer: its A5–S5 (trifilar) 15.8 µH is higher than
  tiw_simple's 11.1 µH (separate layers), which is physically suspicious. Planned test
  (was running when stopped): compare the A5–S5 / A5–SN5 / S5–SN5 / P1–S15 short-circuit
  inductance with settings `leakageInductanceGridPrecisionLevelWound: 3`,
  `magneticFieldNumberPointsX/Y: 100/200` (`leakageInductanceGridAutoScaling: False`),
  `magneticFieldMirroringDimension: 3`. If the default grid is too coarse, raise it in
  `om_model.analyse` for all options and rerun the OM step (`--om-only --force`), then the sims.
- Not run: `tiw_sandwich_stacked`, `margin_sandwich`, `recommended` (tiw_sandwich with S15
  8 T, writes `mas/tr1_recommended.json`), `recommended_pre` (+ preloads 3.3 k on 15V,
  1 k on 5V).
- Capacitor-scaling check: one `current` nom run with `cscale=1` (call `fs.netlist(...,
  cscale=1.0, tstop=30e-3)`) to show the DC levels do not depend on the scaling.
- Losses / Bpk / isolation / Vpeak / snubber per option; final recommendation and winding
  spec; FLYBACK_DESIGN.md sections 3–6 (marked TODO).
- Not modelled yet: AUX_MEAS divider load on 15V (0.56 mA), real IW1818 Vcc current.

## Commands

```
cd /home/jari/dev/tube_psu_kicad
python3 simulation/flyback/run_flyback.py tiw_sandwich            # continues: cached cases are skipped
python3 simulation/flyback/run_flyback.py tiw_sandwich_stacked margin_sandwich recommended recommended_pre
python3 simulation/flyback/run_flyback.py --report current stacked tiw_simple tiw_sandwich tiw_sandwich_stacked margin_sandwich recommended recommended_pre
python3 simulation/flyback/losses.py current recommended
```

Run one ngspice at a time (the script does). Cached results: `out/results/<option>__<case>.json`
(git-ignored); delete to rerun. Do not `pkill -f run_flyback` from a shell whose own
command line contains that string (it kills the shell); kill by PID.

## User answers (2026-11-16) – apply these first

1. **Rectifiers:** the fitted diodes are the **200 V versions of ES1A** (ES1D class), not 50 V
   ES1A. Use 200 V parts in the model. Check D8 (−100V BIAS): the simulation showed ≈ 420 V
   reverse at 400 V DC+ (≈ 80 V + 42/52 × Vin). If that holds, a 200 V diode is overstressed:
   re-check the D8 reverse voltage (winding polarity, actual DC+ range) and report it as a
   design finding if confirmed.
2. **Measured light-load 15V ≈ 15.5 V** (simulation said 20.6 V). Calibrate the model against
   this before comparing options: check the IW1818 supply current assumption (5 mA), the
   light-load (burst / PFM) controller model, the AUX_MEAS divider load (0.56 mA, not
   modelled) and the winding order below. The 18.7 V AUX_MEAS limit is met on the real board.
3. **Winding order (confirmed by the user):** primary innermost, then the primary-side windings
   (8 T → 15V, 3 T → 5V + feedback), then the barrier tape (4 layers), then the isolated
   windings 7 T (15V_ISO_SEC), 3 T (5V_ISOL), 3 T (−5V_SEC), 42 T (−100V BIAS), each separated
   by one layer of tape. All 5 V windings have **3 turns** (as in "52/8/3||7/3/3/42"). This is
   the order already assumed in `om_model` for the current transformer, so no rebuild is needed
   for the order; check the tape layers between the isolated windings match.
4. **Preload resistors on 15V and 5V are acceptable** (run `recommended_pre`).

## Open questions for the user

1. Which rectifiers are actually fitted (schematic says ES1A, 50 V; D8 needs ≥ 600 V,
   D4/D5 ≥ 100 V)?
2. Measured rail voltages on the bench, especially 15V and 5V at light load and
   15V_ISO_SEC (model says 12.6–14.4 V)? Real IW1818 Vcc current?
3. Winding order of the wound V2 transformer (assumed: primary innermost, then
   8/3, barrier, 7/3/3/42) and whether the 3-turn windings are bunched or spread?
4. Is triple-insulated wire acceptable for the rewind (removes the margin tape; reinforced
   insulation by the wire, IEC 62368-1 Annex J class)? The pinout and footprint stay; a split
   primary needs its middle crossover sleeved across the secondaries (all 10 pins in use).
5. Should 15V_ISO_SEC become 8 T (≈ 15 V) – check the Si8274 UVLO grade?
6. Are small preload resistors on 15V / 5V acceptable (≈ 70 mW / 25 mW)?

## Known issues

- Light-load cases run in PFM with burst-like control; their averages carry more drift
  than the others (see `drift` in the result JSONs).
- Core-loss models in MKF disagree by 10× for this waveform.
- The IW1818 controller is behavioural (PWM/PFM boundary 0.12 and PFM law assumed).

## Prompt for the next session

> Continue the TR1 flyback cross-regulation study in /home/jari/dev/tube_psu_kicad
> (simulation/flyback/, read NEXT.md and FLYBACK_DESIGN.md first). Rules: one ngspice
> simulation at a time, keep memory low, scratchpad for temp files, do not change the
> schematic/board, commit after each step (trailer Co-Authored-By: Claude Opus 5.5
> <noreply@anthropic.com>), do not push. Steps: (0) apply "User answers (2026-11-16)" in NEXT.md: 200 V rectifiers, calibrate to the measured 15.5 V light-load 15V rail, the winding order is confirmed (as already modelled), preloads allowed; (1) check MKF's leakage for windings
> sharing one layer (grid settings listed in NEXT.md) and fix om_model if needed;
> (2) finish tiw_sandwich and run tiw_sandwich_stacked, margin_sandwich, recommended,
> recommended_pre; (3) cscale=1 check; (4) losses / Bpk / isolation / Vpeak per option;
> (5) choose the recommended design (keep the TR1 pinout/footprint), write its full winding
> spec and mas/tr1_recommended.json, finish FLYBACK_DESIGN.md sections 3–6 (remove the
> TODO marks) and update NEXT.md. Use the net names 15V / 15V_ISO_SEC (Proteus 20V /
> 20V_ISO_SEC); the 15V rail must stay below 18.7 V (AUX_MEAS ADC range).
