# DAB transformer TR3: replacement on EC42x15 PC40 with built-in series inductance

Board tube_power_5_1, sheet `kicad/07_dhb.kicad_sch`: half-bridge / half-bridge DAB
(Q7/Q8 on DC+ = 400 V with split caps C47/C54; Q19/Q21 on 420 V with split caps
C16/C55; all STF7N60M2). Today: TR3 = ETD34 26:28 plus series inductor L3 = 70 µH (RM8).
Goal: one transformer on the new EC42x15 core and 2-chamber bobbin whose leakage
inductance replaces L3.

Rerun: `python3 simulation/dab/run_dab.py` (about 1 min, one process, about 0.6 GB RAM).
Outputs go to `out/` (git-ignored: `results.md`, `results.json`, `run.log`). MAS files go to
`mas/tr3_dab_A_70uH.json` and `mas/tr3_dab_B_42uH.json`.

## 1. Assumptions. Please read before using the numbers

- **Switching frequency 140 kHz** (user: same as the PFC). This is the main case. 100 kHz
  is shown only as a sensitivity line.
- **Phase-shift inconsistency. Please confirm.** With L3 = 70 µH at 140 kHz, 400 W at
  400 V → 420 V needs φ ≈ 45–50°, not the 20–30° stated. Getting 25° at 140 kHz needs about
  42 µH in total. This report therefore gives two leakage targets:
  - **A, "replicate L3"**: target 70 µH, accepted range 60–85 µH. φ ≈ 40–47°. Note that
    the user's "primary RMS ≈ 2.5 A" fits this case: it gives 2.4–2.6 A, against 2.2 A at
    25°.
  - **B, "25° operation"**: about 42 µH. φ ≈ 23–24°.

  To choose between them, check the real phase shift in the firmware, or measure the old
  ETD34's leakage (secondary shorted) plus L3.
  At 140 kHz, 70 µH can transfer only about 515 W at φ = 90° (Pmax = V1·V2′/(8 f L)). That
  leaves little control margin at low DC+, and it is one more reason to prefer B, or the
  low end of A.
- Square-wave bridges: ±200 V primary and ±210 V secondary. Dead time is ignored in the
  waveforms. The split caps are modelled as 2 µF per side, in series for AC; the cap
  midpoint ripple is about 4 Vpp.
- Material: PC40 is in the MKF database (TDK), so it was used directly, including its
  Steinmetz data from 16 to 150 kHz.
- Winding resistance is taken at 80 °C, with 40 °C ambient. Litz is Elektrisola
  single-served, grade 1, and the maximum OD from the database is used.
- STF7N60M2 Co(tr) ("Coss eq.", 0–480 V) = **75.5 pF** (ST DS9793). That is higher than
  the 60 pF first assumed. Per switch node, C = 2·75.5 + 30 pF (winding + layout,
  assumed) = 181 pF.

## 2. Core and bobbin model

**Core.** The seller's "EC42*15" has a round centre leg, which makes it MKF family "er".
It is defined as a custom shape: A 42.0, B 21.5, C (depth) 15.3, D (half window) 15.5,
E 30.5, F (centre leg) 15.2 mm. MKF gives **Ae 187.0 mm², le 98.8 mm, Ve 18.47 cm³**,
close to the hand estimate of 181 / 100 / 18. The database shape ER 42/22/15 gives
172.7 / 100.6 / 17.37 and was not used, because its leg is 14.7 mm and its window
31.9 mm.

**Bobbin.** The 2-chamber bobbin is modelled as one winding window, radially 8.9–15.0 mm
(tube OD 17.8, flange OD 30.0) and axially ±13.9 mm, with a 5 mm divider in `dividers`.
- Chamber 1 is 10.4 mm wide (y −13.9…−3.5, pins 1–8).
- Chamber 2 is 12.4 mm wide (y +1.5…+13.9, pins 9–16).
- The divider sits at y −3.5…+1.5, so the core midplane (y = 0) lies under the divider:
  1.5 mm from the wall of chamber 2 and 3.5 mm from chamber 1.

One window is used because MKF's field grid only covers `windingWindows[0]`. Turns are
placed by hand (`om_dab.build_coil`, the same approach as the flyback work), giving
cartesian turn coordinates and a turn length of 2πr.

**Leakage method.**
- MKF inductance matrix (energy method on the window field). The grid is converged:
  default vs 50×100 points vs mirroring 3 vs precision 3 agree within 1.1 %.
- An independent axisymmetric finite-difference solver (`fd_leakage.py`) for the same
  layers agrees with MKF to within 3 % when the core is treated as a closed pot ("pot":
  81.7 µH vs MKF 84.4 µH for 25:26).
- MKF's 2-D window model, however, treats the whole turn as if it were inside the core. On
  this ER core, the outer legs and plates cover only the band |z| < 7.65 mm, which is about
  45 % of a turn. Outside that band the leakage field closes through air.
- `fd_leakage.py` therefore also solves the case with only the centre rod ("rod") and
  combines the two per element, weighted by the in-band fraction. The result is
  **0.73–0.76 × MKF**. This "best" value is used for the design. MKF's value is reported as
  the upper bound.
- The user's hand formula (125 µH at 26 T) used h = 6.3 mm and MLT 75 mm. With the ferrite
  gap of 7.65 mm and MLT ≈ 2π·10.7 mm, the same formula gives MKF's in-window value. The
  ER correction then removes another quarter.

## 3. Results at 140 kHz, 400 W, 400 V → 420 V

### 3.1 Turns sweep

Litz 60×0.1 on both windings, pushed against the divider, ungapped. "Lsc best" is the
ER-corrected short-circuit inductance referred to the primary. The DAB waveform (exact
piecewise-linear steady state with the 2×2 matrix and the split caps) is computed with it.

| Np:Ns | Lsc MKF µH | Lsc best µH | Lm µH | Pmax W | φ° @400 W | I1rms A | I1pk A | Bpk T | Pcore W | Pcu W | total W | ΔT K |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 16:17 | 36 | 28 | 992 | 1256 | 15.2 | 2.16 | 2.45 | 0.119 | 2.49 | 0.60 | 3.10 | 22 |
| 18:19 | 45 | 35 | 1254 | 1020 | 19.3 | 2.18 | 2.39 | 0.106 | 1.90 | 0.69 | 2.59 | 19 |
| 19:20 | 50 | 39 | 1397 | 915 | 21.9 | 2.20 | 2.38 | 0.100 | 1.69 | 0.73 | 2.42 | 18 |
| 20:21 | 54 | 42 | 1548 | 851 | 23.9 | 2.22 | 2.38 | 0.095 | 1.49 | 0.79 | 2.29 | 17 |
| 21:22 | 59 | 46 | 1707 | 784 | 26.4 | 2.24 | 2.40 | 0.091 | 1.34 | 0.86 | 2.21 | 17 |
| 22:23 | 65 | 50 | 1873 | 719 | 29.5 | 2.27 | 2.43 | 0.087 | 1.21 | 0.94 | 2.15 | 16 |
| 23:24 | 72 | 55 | 2048 | 657 | 33.1 | 2.30 | 2.48 | 0.083 | 1.10 | 1.01 | 2.11 | 16 |
| 24:25 | 79 | 60 | 2230 | 601 | 37.4 | 2.35 | 2.55 | 0.079 | 1.00 | 1.09 | 2.09 | 16 |
| 25:26 | 85 | 64 | 2419 | 563 | 40.9 | 2.39 | 2.61 | 0.076 | 0.90 | 1.18 | 2.08 | 16 |
| 26:27 | 91 | 69 | 2615 | 524 | 45.5 | 2.44 | 2.69 | 0.073 | 0.82 | 1.28 | 2.10 | 16 |
| 26:28 (old turns) | 92 | 69 | 2615 | 503 | 48.6 | 2.53 | 2.92 | 0.073 | 0.83 | 1.35 | 2.17 | 16 |

The full table, including 17:18, is in `out/results.md`.

How the columns were computed:
- **Pcore**: MKF iGSE. Steinmetz gives +4 % and Roshen +30 %.
- **Pcu**: MKF Dowell/Ferreira for litz, using the real trapezoidal currents.
- **ΔT**: rough natural-convection estimate (McLyman, (P[mW]/A[cm²])^0.833) over about
  75 cm² of core plus exposed winding. MKF's core-only model gives 59–71 °C core
  temperature at 40 °C ambient.
- **Bpk** is low everywhere, at 0.07–0.12 T. That is about V/(4fNAe), confirming the hand
  estimate of 0.10 T at 20 T.

Losses are small for every option, about 2–3 W in total. Core loss dominates at low N and
copper loss at high N. The minimum is flat around 23–26 T.

### 3.2 Winding position, litz and chamber assignment

The knobs are tested at 20:21 and 24:25.

| change (vs divider-aligned 60×0.1) | Lsc best, 20:21 / 24:25 | Pcu |
|---|---|---|
| both windings pushed to the flanges | +21 % / +18 % | ≈ same |
| centred in the chambers | +12 % / +10 % | ≈ same |
| turns spread over the full chamber width | +7 % / +7 % | −3 % |
| Litz 90×0.1 | −2 % / −5 % | −6 % / −13 % |
| **Litz 135×0.071** | −2 % / +2 % | **−20 % / −21 %** |
| primary in the 12.4 mm chamber | 0 % / −5 % | ≈ same |

Notes:
- Pushing the windings to the flanges or spreading them is the fine-tuning knob for
  leakage, worth up to about +20 %.
- 0.071 mm strands beat 0.1 mm at 140 kHz: the skin depth is 0.18 mm and proximity effect
  dominates.
- **Chamber assignment:** it makes no difference electrically, because the ampere-turns
  are equal. Put the **primary in chamber 1 (10.4 mm, pins 1–8)** and the secondary, which
  has one more turn, in chamber 2 (12.4 mm, pins 9–16).

### 3.3 Recommended options

Both use Litz 135×0.071, with 7 turns per layer in chamber 1 and 9 in chamber 2. That
leaves one turn of slack per layer for hand winding. Both windings are pushed against the
divider. Values are with the recommended gap (section 4) unless the row says "ungapped".

| | **A: 25:26** (target 60–85 µH) | **B: 20:21** (target ≈ 42 µH) |
|---|---|---|
| layers, build incl. 3 tape layers | P 4 layers (7/7/7/4), 5.3 mm of 6.1; S 3 layers (9/9/8), 4.0 mm | P 3 layers (7/7/6), 4.0 mm; S 3 layers (9/9/3), 4.0 mm |
| copper fill (Cu / chamber area) | 21 % / 18 % | 17 % / 15 % |
| Rdc at 80 °C | 69 mΩ / 69 mΩ | 53 mΩ / 54 mΩ |
| Lsc best (MKF upper bound) | **63 µH** (84 µH) | **41 µH** (53 µH) |
| Lm ungapped → gapped | 2.42 mH → 0.337 mH | 1.55 mH → 0.300 mH |
| Pmax at φ = 90° | 580 W | 885 W |
| φ at 400 W, ungapped → gapped | 39.6° → **41.4°** | 22.9° → **23.5°** |
| I1rms / I1pk, gapped | 2.52 A / 3.10 A | 2.31 A / 2.91 A |
| I2rms, gapped | 2.41 A | 2.18 A |
| Bpk | 0.076 T | 0.095 T |
| Pcore (iGSE / Steinmetz / Roshen) | 0.91 / 0.95 / 1.19 W | 1.50 / 1.55 / 1.99 W |
| Pcu, gapped (ungapped) | 1.09 W (0.96 W) | 0.72 W (0.65 W) |
| **total, gapped** | **2.0 W, ΔT ≈ 15 K** | **2.2 W, ΔT ≈ 17 K** |
| 100 kHz sensitivity, ungapped | φ 25.2°, total 2.1 W | φ 15.2°, total 2.8 W, Bpk 0.133 T |
| ZVS at 400 W (edge current, needs < −0.5 A) | −3.1 A / −3.0 A | −2.9 A / −2.7 A |

**Gap changed again (owner, 2026-11-24): tape spacer, Lm tuned on the bench.** The DAB FETs become
IPA60R280CFD7 (Co(tr) 249 pF vs 75.5 pF of the STF7N60M2; `DAB_SIMULATION.md` "CFD7 check (2026-11-24)"), which
needs **Lm ≈ 120 µH with 200 ns dead time** for soft switching at light load. The core is gapped with **tape (a
spacer under all legs)** and Lm is adjusted on the bench until the bridge switches soft; no fixed grind dimension is
a requirement. Starting tape thickness from `gap_for_lm` (option B, TIW-litz secondary, MKF reluctance, run
2026-11-24): **0.83 mm → 120 µH**; 0.78 mm → 124 µH, 0.88 mm → 117 µH (≈ 3.5 µH per 0.05 mm tape layer around the
target); 0.615 mm → 140 µH, 1.245 mm → 100 µH; the same function still gives 0.335 mm → 200 µH. The losses / φ of
the tables in this file were computed for 200–300 µH and are not re-run for 120 µH (the no-load primary current
grows, ≈ 0.84 A rms vs 0.52 A in the CFD7 scratch run). The 200 µH texts below are superseded.

**Gap target changed (user decision 2026-11-18, section 4; superseded 2026-11-24, see above):** option B is now gapped to
**Lm ≈ 200 µH** (≈ 0.66–0.68 mm centre grind), not 0.300 mH. The "gapped" rows above are
for 300 µH; at 200 µH the switching model gives φ +0.4°, I1rms +3 % and about +0.5 W at
400 W (`DAB_SIMULATION.md` 2.4). Leakage changes by < 1 %.

Option A uses 25:26 rather than 26:27 on purpose. Its best estimate (63 µH) and its MKF
upper bound (84 µH) both fall inside 60–85 µH. 26:27 would give 68 / 93 µH, so its upper
bound is out of range, and Pmax would drop to 515 W.

### 3.4 Baseline: existing ETD34 26:28 + L3, same calculation

The builds are assumed, because the real ones are unknown:
- TR3: ETD34 PC40 on the Norwe 90642 vertical bobbin, concentric (primary inside, 3 tape
  layers, secondary outside), Litz 60×0.1 on both windings.
- L3: RM8 PC40, 25 T of Litz 40×0.1, gap 0.78 mm, fitted to 70 µH.

| | ETD34 TR3 | L3 (RM8) | total |
|---|---|---|---|
| leakage / L | 4.6 µH | 70 µH | 74.6 µH |
| φ at 400 W, I1rms | 54.5°, 2.60 A | | |
| Bpk | 0.148 T | 0.160 T | |
| Pcore | 3.59 W | 0.73 W | |
| Pcu | 1.34 W | 1.04 W | |
| total | 4.9 W (ΔT ≈ 48 K) | 1.8 W | **6.7 W** |

The new part saves about 4.5 W. Most of that is core loss: the ETD34's Ae is only 97 mm².

## 4. Gap: magnetizing current for ZVS at no load

**Requirement.** At no load both bridges run in phase (φ ≈ 0), and only the magnetizing
current commutates the switch nodes. Each leg's 181 pF must swing 400 V (primary) or 420 V
(secondary) within the firmware dead time, which gives I ≥ C·Vdc/t_dead. The magnetizing
current splits between the bridges in proportion to their leakage shares. The geometry
gives a 46–48 % primary share. (The split computed from MKF's matrix is numerically
fragile and was not used.) Both bridges therefore need about Im/2 each, as the user
expected. The table comes from the full circuit (`lm_for_zvs`: smallest |edge current| on
either bridge ≥ the requirement, Vout = 420 V).

**Required Im / Lm vs firmware dead time** (the gate driver is dual-input, so the FPGA
sets the dead time):

| dead time | I_req pri / sec | A: Lm | A: centre grind | A: spacer (all legs) | B: Lm | B: centre grind | B: spacer |
|---|---|---|---|---|---|---|---|
| 100 ns | 0.72 / 0.76 A | 211 µH | 1.31 mm | 0.65 mm | 197 µH | 0.68 mm | 0.34 mm |
| **150 ns** | 0.48 / 0.51 A | **337 µH** | **0.58 mm** | **0.30 mm** | **300 µH** | **0.35 mm** | **0.18 mm** |
| 200 ns | 0.36 / 0.38 A | 446 µH | 0.38 mm | 0.20 mm | 404 µH | 0.22 mm | 0.12 mm |

- Gap lengths come from MKF (Zhang reluctance with fringing), fitted to the primary
  open-circuit inductance with the real coil.
- Hand check: the user's estimate was Lm ≈ 0.45 mH for 2 × 0.4 A. With the datasheet
  Co(tr) of 75.5 pF and 30 pF winding capacitance, the requirement is higher, about
  2 × 0.5 A at 150 ns.
- ~~Recommendation: grind to the 150 ns value and run the FPGA at 150–200 ns dead time.
  Targets were A 337 µH (AL 0.54 µH) and B 300 µH (AL 0.75 µH).~~ **Superseded (user decision
  2026-11-18, from the switching model `dab_spice.py` / `DAB_SIMULATION.md` 2.4 and 3):
  option B target Lm ≈ 200 µH (AL 0.50 µH, Np = 20), FPGA dead time 150 ns total.** 200 µH is
  the "100 ns" row of the table (197 µH): ZVS at no load even with the 100 ns UCC21520 DT
  alone (node swing 66 ns), no hard switching at a +5 % bus mismatch, only small (≤ 6 µJ)
  edges in a 30–110 W window at −5 % (37 µJ at 307 µH). Cost: +0.5 W at 400 W, +0.3 W at no
  load. The UCC21520's 100 ns DT is a minimum, not added to the FPGA dead time.
  Gap for 200 µH, recomputed with `gap_for_lm` (MKF reluctance, option B, the same for the
  served-litz and the TIW-litz secondary): **centre grind 0.659 mm, spacer (all legs)
  0.335 mm**; the tolerance band 170–210 µH is 0.87–0.61 mm centre / 0.44–0.31 mm spacer.
  - At 200 ns the no-load charge margin is 1.33×.
  - At full load the node swings in about 25 ns (3 A), so the body diode then conducts for
    the rest of the dead time. That costs about 0.2 W in total, with no reverse-recovery
    problem under ZVS.
  - A load-dependent dead time in the FPGA would remove that loss.

**Effect of the gap at 400 W.**
- Leakage drops by only 0.3–1 % at 0.6 mm (MKF).
- Im peaks at 0.87 A (A) and 1.08 A (B). It adds to the current at the switching edge,
  which improves the ZVS margin.
- I1rms rises by 6 % (A) and 4.5 % (B), and φ by 1.8° and 0.6°.
- Pcu rises by 0.13 W (A) and 0.07 W (B).
- Bpk is unchanged at 0.076 / 0.095 T. The core is voltage-driven, and the gap only lowers
  Lm; it adds no DC flux.

**Light load vs output voltage.** These are edge currents with the A gap at 150 ns, in
amps; each must be ≤ −0.48 (primary) or ≤ −0.51 (secondary). See `out/results.md` for B.

| Vout | 0 W | 50 W | 100 W | 400 W |
|---|---|---|---|---|
| 400 V | −0.81 / −0.27 | −1.06 / −0.52 | −1.32 / −0.79 | −3.43 / −2.91 |
| 420 V | −0.54 / −0.55 | −0.79 / −0.79 | −1.05 / −1.04 | −3.10 / −3.01 |
| 440 V | −0.27 / −0.83 | −0.52 / −1.06 | −0.78 / −1.30 | −2.79 / −3.13 |

When Vout differs from the matched value (400·Ns/Np = 416 V for A, 420 V for B) by ±5 %,
one bridge loses ZVS below about 50 W. If the output voltage varies, use a 200 ns dead
time or grind to the 100 ns column. (The current needed for more Im/2 margin scales with
1/Lm.)

**Fringing: does the gap sit under the divider? Yes.**
- The centre-leg gap at y = 0 is under the 5 mm divider. The nearest secondary turn is
  1.5 mm axially and 1.3 mm radially from the gap edge, and the nearest primary turn is
  3.5 mm away.
- MKF's raw winding losses with its fringing term on are much higher: 2.45 W instead of
  1.09 W (A), and 1.56 W instead of 0.72 W (B).
- That increase appears with the balanced load currents but not with the magnetizing
  current alone. Physically, the gap MMF is the net ampere-turns N·Im: the load
  ampere-turns cancel around any loop through the gap. So the fringing increase is an
  artefact of how MKF superposes the per-winding fringing.
- The values used here therefore take MKF without fringing and add the fringing increment
  of the magnetizing current alone. That increment is **0.013 W (A) and 0.009 W (B)**: the
  fringing loss is negligible.
- The spacer variant (gaps in all three legs) gives the same corrected losses. It spreads
  more stray field outside the core, so the **centre-leg grind is preferred**. A Kapton or
  paper shim of 0.30 mm (A) or **0.335 mm (B, Lm 200 µH; 0.18 mm was the old 300 µH
  target)** under all legs is a quick way to try the first sample before grinding. The
  fringing increment at the B gap of ≈ 0.66 mm is of the same order as the 0.013 W found
  for A at 0.58 mm, i.e. negligible.

## 5. Recommended winding specification

The common items are the same for both options. Choose A or B after confirming the phase
shift (section 1).

| item | A (70 µH class) | B (42 µH class) |
|---|---|---|
| primary, chamber 1 (10.4 mm) | 25 T Litz 135×0.071, 7 per layer, 4 layers | 20 T Litz 135×0.071, 7 per layer, 3 layers |
| secondary, chamber 2 (12.4 mm) | 26 T Litz 135×0.071, 9 per layer, 3 layers | 21 T Litz 135×0.071, 9 per layer, 3 layers → **reinforced (TIW-jacket) litz 135×0.071, OD ≤ 1.6 mm, 7 per layer, 3 layers (section 8)** |
| gap (centre leg, total) | 0.58 mm → Lm 337 µH | **tape spacer under all legs, starting Lm ≈ 120 µH ≈ 0.83 mm (`gap_for_lm`), tuned on the bench for soft switching at light load** (owner 2026-11-24, CFD7 FETs, 200 ns dead time). Was ≈ 0.66–0.68 mm centre grind / 0.335 mm spacer → Lm ≈ 200 µH (STF7N60M2, 150 ns), before that 0.35 mm → 300 µH |

**Wire.** Litz 135×0.071 single-served has OD 1.19–1.29 mm and 0.534 mm² of copper
(about 4.5 A/mm² at 2.4 A). An alternative is 60×0.1 (OD 1.2 mm), at about +25 % Pcu.

**Winding.**
- Wind both windings in the same direction, starting at the tube. Keep each layer tight
  against the **divider wall**.
- Put one layer of tape between layers if the litz is single-served.
- Put **3 layers of polyester tape (25 µm film)** over each winding.
- The 5 mm divider separates the windings. The core counts as primary side, and the
  secondary is isolated (ISO_GND). **Reinforced isolation is required (section 8): the
  secondary must be TIW-jacket litz; the divider and tape alone do not meet 11.1 mm.** Keep the secondary's outer layer at least 0.5 mm below
  the flange rim, and run its leads out without crossing chamber 1.

**Pins (5.2 board, re-assigned 2026-11-21).** Use 2 pins per winding end, splitting the litz
strands over 2 adjacent pins. That is 4 pins per row; cut the other pins (primary row 1, 2, 3, 6;
secondary row 13, 14, 15, 16): the 5.2 footprint has no pads for them.

Pin numbering as on the footprint, seen from above with the primary row on the left: pin 1 is at
the top of the primary row (chamber 1), 8 at the bottom; 9 is at the bottom of the secondary row
(chamber 2), 16 at the top. On the board "bottom" is the side of the TO-220 row (Q7 / Q19 / Q21 / Q8).

| winding | chamber | start (inner layer, **dot**) | finish (outer layer) | turns (option B) |
|---|---|---|---|---|
| primary | 1 (10.4 mm, pins 1–8) | **pins 4 + 5** → split-cap midpoint DHB_CAP (C47 / C54), the quiet end, next to the core | **pins 7 + 8** → primary bridge midpoint DHB_HI_SOURCE (Q19 source / Q7 drain) | 20 |
| secondary | 2 (12.4 mm, pins 9–16) | **pins 9 + 10** → split-cap midpoint TRANS_SEC (C16 / C55) | **pins 11 + 12** → secondary bridge midpoint DHB_HI_SOURCE_SEC (Q21 source / Q8 drain) | 21 |

Both windings are wound in the same direction, so the two starts are the dotted ends (primary
start ↔ secondary start, as before).

Why these pins: each winding end sits on the pin pair nearest to the copper it connects to on the
5.2 board, with the parts as the user placed them on 2026-11-21.
- Primary start 4 + 5: C47 / C54 stand 3.9 mm left of these two pins, with their DHB_CAP pads at
  the height of pin 4 … 5 (was 1 + 2 at the top of the row, with the capacitors next to them).
- Primary finish 7 + 8: the bottom of the row, nearest to Q7 / Q19 (unchanged).
- Secondary start 9 + 10: the bottom of the row; the TRANS_SEC pads of C16 / C55 face each other
  3.9 mm right of them (unchanged).
- Secondary finish 11 + 12 (was 15 + 16 at the top of the row, 13 + 14 for one commit): the pair
  nearest to the secondary bridge, 15 mm less switch-node track than 15 + 16. The DRV6 parts
  R75 / R76 / C72 stood on those two pin places on the bottom side and were moved 2.3–2.6 mm.
  The secondary now uses the four bottom pins 9–12 next to each other: start pair 9 + 10,
  finish pair 11 + 12, 5 mm between pin 10 and pin 11 (TRANS_SEC ↔ switch node, 210 V + ripple;
  pad to pad 2.6 mm on the board).

Earlier assignments: until 2026-11-21 1 + 2 primary start, 7 + 8 primary finish, 9 + 10 secondary
start, 15 + 16 secondary finish; commit 6c3a9bf 4 + 5 / 7 + 8 / 9 + 10 / 13 + 14.

If power flows the wrong way at a positive phase command, swap one winding's ends, or
change the phase sign in the FPGA.

**L3.** Remove it and bridge its pads (DHB_CAP → transformer primary). Keep the RM8
footprint for now. If the measured leakage comes out low, a small residual L3 of a few
turns on the RM8 can make up the difference.

**Board.** The new part needs a new footprint (2×8 pins, 5.0 mm pitch, rows 40 mm apart).
The ETD34 footprint does not fit. This is not done here.

## 6. First wound sample: what to measure and how to adjust

1. **Before gapping**, with an LCR meter at 100 kHz and a low level:
   - **Lm** (primary, secondary open): expected 2.4 mH (A) or 1.55 mH (B). Wide tolerance
     (±30 %): PC40 µi and the residual gap of the lapped faces.
   - **Lsc** (primary, secondary shorted with a short, thick link): expected
     **63 µH (A) or 41 µH (B)**. The accepted model range is A 57–84 µH and B 37–53 µH;
     the top of each range is MKF's in-window value. Also measure from the secondary side,
     with the primary shorted. It should read about Lsc·(Ns/Np)².
2. **Adjust if Lsc misses the target.** Lsc scales with N²: N′ = N·√(L_target/L_measured),
   then Ns = round(1.04…1.05·N′). One turn pair changes Lsc by about 8 %. For fine tuning
   without changing turns:
   - move both windings to the flanges (+18–21 %),
   - spread the turns over the chamber width (+7 %),
   - put a tape spacer of a few mm at the divider side of each chamber (raises g),
   - if Lsc comes out too low, add a small residual L3.
3. **Gap (2026-11-24, B with CFD7 FETs):** tape spacer under all three legs, start at ≈ 0.83 mm (Lm ≈ 120 µH),
   add / remove 0.05 mm layers (≈ 3.5 µH each) until the switch node completes its swing at no load / light load
   with 200 ns dead time (step 4). The grind procedure below is the superseded 200 µH plan.
   *Superseded:* Grind the centre leg of one half, or both halves by half each, in steps.
   Re-measure Lm (primary open) after each step, at 10–100 kHz and a low level. **Stop at
   337 µH (A) or 200 µH (B), tolerance −15 % / +5 %, i.e. B 170–210 µH** (≈ 0.87–0.61 mm
   centre grind; aim for ≈ 200 µH ≈ 0.66 mm and grind in steps of ≈ 0.05 mm: one step is
   ≈ 10 µH there). Lower is safer for ZVS and costs only a little copper loss
   (≈ +0.5 W at 400 W for 200 vs 300 µH). Then re-check Lsc; it should be within 1 % of
   before.
4. **On the board.** Look at the switch-node transition at no load and at full load, with
   **200 ns dead time total with the CFD7 FETs (was 150 ns), not above 200 ns** (the UCC21520 DT 100 ns is a minimum, not additive). At 200 µH
   the no-load swing is ≈ 66 ns (`DAB_SIMULATION.md` 2.4). If the no-load transition does not
   finish (the node does not reach the rail before turn-on), lower Lm (thicker tape); do not
   go above 200 ns (the sending-side current reverses before turn-on at 100–250 W).

## 7. Confidence and caveats

- **Leakage is the largest uncertainty**, about −10 % / +30 % around the best value. The
  2-D MKF and the axisymmetric FD "pot" agree within 3 %. The ER (open-sided core)
  correction of about −25 % comes from a simple per-element in-band/out-of-band weighting,
  not a 3-D solve. Measure the first sample (section 6). One turn pair is worth about 8 %.
- The core-loss models spread by about 30 % (Roshen high) and do not decide anything. The
  temperature rise is a rough natural-convection estimate.
- The baseline's builds (litz, layout, the L3 design) are assumed. Its result (6.7 W) is
  indicative only.
- No dead-time dynamics: ZVS uses the constant-current charge criterion with C = 181 pF.
  Coss rises at low voltage; the time-related value covers this.
- MKF's fringing term was overridden on physical grounds (section 4).

## 8. Isolation (reinforced, added 2026-11-18)

**Requirement** (kicad_next/README.md, isolation domains): TR3 bridges the primary (DC+, mains
referenced) and the DAB secondary (420 V rail, ISO_GND earthed). The insulation between the two
windings, and from the secondary to anything primary-side, must be **reinforced** for a working
voltage of **552 Vrms / 778 Vpk**: creepage **11.1 mm**, clearance **4.0 mm** (PD2, material
group III, OVC II). On top of the mains-frequency term there is the 140 kHz square-wave difference
of the two bridges (up to ≈ 410 V); IEC 60664-4 (> 30 kHz) has not been assessed, but at this
voltage its creepage values are well below 11.1 mm.

**The core counts as primary.** The primary is served litz on the tube: served litz is not
insulation, and from the primary to the core there is only the tube wall and a few millimetres
over the chamber-1 flange. So the core is treated as a primary-side conductive part.

| path | served litz on both windings, 3 tape layers (section 5 as drawn) | required |
|---|---|---|
| primary ↔ secondary over the 5 mm divider. The windings touch the divider; the path runs from the outer layer edge (r ≈ 12.9 mm) up to the rim (r 15.0), across 5 mm and down the other side | 2.1 + 5.0 + 2.1 ≈ **9.2 mm** | 11.1 mm: **fails** |
| secondary winding ↔ core over the chamber-2 flange (winding edge → rim → core end face) | ≈ 2 + 1 ≈ **3 mm** | 11.1 mm: **fails** |
| secondary outer layer ↔ ER outer leg (r 15.25 mm), through air | ≈ 2.3 mm | 4.0 mm clearance: **fails** |
| primary pin row ↔ secondary pin row (40 mm) | ≈ 38 mm | **passes** |

**Do 3 tape layers suffice under a "solid insulation" reading? No.**
- IEC 62368-1 accepts thin-sheet insulation as reinforced: ≥ 3 layers, any 2 of which pass the
  electric-strength test (or 2 layers if each passes it alone). That covers the tape over a
  winding's surface.
- But the tape does not enclose the winding. It ends against the divider and the flanges in
  joints that are not cemented, and the litz runs out to the pins through those joints.
- Along such joints the creepage rules apply in full, and those are the three failing rows
  above. A taller divider would need ≥ 3 mm of free wall above each winding *and* a wider
  divider; margin tape cannot be fitted either (it would take 5.5 mm per side in 10.4 / 12.4 mm
  chambers). Neither fits this bobbin.

**Decision: wind the secondary in reinforced-insulated litz (TIW litz). The primary stays served
litz.**
- With one winding in IEC 62368-1 Annex J wire, the wire's own insulation is the reinforced
  barrier: to the primary, to the core and through the divider joints alike. The divider and
  the tape then only do mechanical work.
- Products in the 135 × 0.071 class:
  - **Elektrisola EFOLIT**: taped reinforced litz with ≥ 3 tape layers (sPET / sPEN / sPI),
    VDE-certified to EN 62368-1 Annex J, IEC 61558-1 Annex K and IEC 60601-1 Annex L. The
    reinforced range starts at 1.5 mm OD; made to order.
  - **New England Wire NEWind**: litz with triple extruded FEP / ETFE (155 °C) or PFA (180 °C),
    listed for IEC 62368-1 Annex J.
  - **Rubadue TCA3 litz**: triple extruded. MKF has 135/38 AWG at 1.76 mm OD; 0.071 mm strands
    are a custom construction.
  - Furukawa TEX-ELZ only goes up to 7 strands (7/0.30), which is too small.
- **Specify:** 135 × 0.071 mm (or the nearest stock construction of ≈ 0.53 mm² Cu with
  ≤ 0.08 mm strands), reinforced to IEC 62368-1 Annex J, OD ≤ 1.6 mm, ≥ 155 °C.
- **Annex J vs Annex K:** some regulators want IEC 61558-1 Annex K for transformers with SELV
  outputs (Australian SCO guidance). EFOLIT lists both.

**Rerun for option B with the TIW-litz secondary** (`python3 simulation/dab/run_dab.py --tiw`,
OD assumed 1.55 mm, so 7 turns per layer in the 12.4 mm chamber, 3 × 7; the primary is unchanged;
table in `out/results_tiw.md`, MAS `mas/tr3_dab_B_42uH_TIW.json`):

| | B, served litz (section 3.3) | **B, TIW-litz secondary** |
|---|---|---|
| secondary layers, build incl. 3 tape | 9/9/3, 4.0 mm | **7/7/7, 4.8 mm** (of 6.1 mm) |
| Lsc best (MKF upper bound) | 40 µH (53) | **40 µH (54)** |
| Lm req. at 150 ns → centre gap | 300 µH → 0.35 mm | **307 µH → 0.34 mm** (now superseded: target 200 µH → 0.66 mm, section 4) |
| φ at 400 W, gapped | 23.5° | **23.6°** |
| Rdc pri / sec at 80 °C | 53 / 54 mΩ | 53 / **58 mΩ** |
| Pcu / Pcore / total, gapped | 0.72 / 1.50 / 2.21 W | **0.73 / 1.50 / 2.23 W** |

The copper is unchanged and the leakage is unchanged within 1 %: the 3 × 7 layers sit at the
divider like the 9/9/3 build, so the extra jacket thickness barely moves the field. **Option B
stands as specified**, apart from the secondary wire and the 7-turn layers. Above 1.75 mm OD,
7 turns no longer fit the 12.4 mm chamber, and 6 per layer would need 4 layers (≈ 7 mm, more
than the 6.1 mm available). In that case use 120 × 0.071 strands or a thinner taped jacket.

**What still needs care with the TIW-litz secondary:**
1. **Terminations.** The jacket must run unbroken into the chamber and out to pins 9/10 and
   11/12. Strip it only over the last few millimetres that wrap the pin. Never lead secondary
   wire across chamber 1 or the primary pins.
2. **Secondary pins ↔ core.** On this horizontal EC bobbin the core end plates sit above the
   pin rows (core 43 mm along the axis, pin rows at ±20 mm). The bare pin wraps of pins 9/10/11/12
   are a few millimetres from the core, which is primary-side.
   - **Measure** the path from the secondary pin wraps to the core along the bobbin: it needs
     ≥ 11.1 mm creepage and ≥ 4.0 mm clearance.
   - If it is shorter (likely), insulate the core end plate on the secondary side with
     **3 layers of polyester tape** (thin-sheet reinforced) wrapped around the plate, or fit an
     insulating core cap.
   - The primary pins need nothing (same domain).
3. **Primary ↔ secondary pins on the PCB:** the rows are 40 mm apart, which is fine.
4. **Hipot (type / sample):** primary + core to secondary, 3 kV rms for 1 min (or 4.2 kV DC).
   **Partial discharge:** 778 Vpk recurring is above the ≈ 700 V level from which IEC 60664-1
   asks for PD-free reinforced insulation (verify against the edition used). Run a PD test on
   the first samples (extinction ≥ 1.5 × 778 V ≈ 1.2 kVpk). Extruded TIW litz is typically
   PD-free well above that; taped constructions should state it.

### 8.1 Vacuum impregnation (optional add-on)

Vacuum (or vacuum-pressure) impregnation with a transformer varnish or resin, such as a polyester
or epoxy class F/H varnish, fills the voids in the litz bundles, between layers and in the
tape / divider joints. This helps in three ways:
- **Partial discharge:** it removes the air voids where PD starts at the 778 Vpk recurring peak
  plus the 140 kHz edges.
- **Humidity and dirt:** pollution in the chamber joints is sealed, and the windings take up
  less moisture.
- **Noise and mechanics:** no magnetostrictive or winding hum, and the turns are fixed against
  the divider, so the leakage does not drift.

It also improves heat transfer a little. **It does not reduce the creepage or clearance
requirement.** Only a qualified cemented-joint process does that (IEC 62368-1 / IEC 60664-3
coating or potting with type tests, which can count the joints as PD1 / solid insulation), and
this design does not claim one. Impregnate after the gap is set and Lm / Lsc are measured, and
measure again afterwards: the varnish's permittivity raises the winding capacitance slightly,
while the leakage does not change.

## 9. Files

| file | content |
|---|---|
| `om_dab.py` | custom EC42 shape, 2-chamber bobbin, hand-placed coil in MKF format, inductance matrix, leakage, Rdc |
| `fd_leakage.py` | axisymmetric FD leakage, pot / rod / ER combination (`python3 fd_leakage.py` runs a grid-convergence self-test) |
| `dab_wave.py` | exact steady-state DAB waveforms, phase for P, ZVS edge currents (`python3 dab_wave.py` runs a check against the textbook power formula) |
| `run_dab.py` | sweep, knobs, recommended options with gap / ZVS, baseline, MAS export; `--tiw`: option B with the TIW-litz secondary (section 8) |
| `dab_spice.py`, `DAB_SIMULATION.md` | ngspice switching model of the whole DAB with this transformer: ZVS, dead time, gap / Lm, shunt, start-up. **It recommends Lm ≈ 200 µH (≈ 0.68 mm centre gap) rather than the 300 µH of section 4, for tolerance against bus-voltage mismatch at light load** |
| `mas/tr3_dab_*.json` | MAS of the recommended options (and `tr3_dab_B_42uH_TIW.json`, section 8), gapped (inputs: 400 W operating point; magnetic; outputs: L matrix, losses) |
