# TR2 heater LLC transformer: OpenMagnetics check (2026-11-23)

Model check of the existing, bench-verified heater LLC transformer TR2 (EF25) with PyOpenMagnetics 1.7.41, an
independent 2-D finite-difference leakage solver and a time-domain LLC model. Two runs by an Opus subagent; the
second one uses the owner's 2021 design document (`tube_amp_power.pdf`, chapter 4, pages 16 - 22). The numbers below
are model results; only the resonance arithmetic was re-checked by hand outside the subagent. Nothing here was
measured on the bench in 2026.

Scripts and raw output are in this directory (`om_tr2.py` model builder, `run_tr2.py` first run, `run_v2.py` second
run, `fd2d_leakage.py`, `llc_sim.py`, `fit3.py`, `lm_cal.py`, `diag_sign.py`; `out/`, `mas/`).

## Inputs

| Source | Fact |
|---|---|
| design document p 19 | EF25, 64 T primary, 2 + 2 T centre-tapped secondary, synchronous rectifiers |
| design document p 19 | chosen build: secondary between two 64 T primaries in parallel, leakage 42 µH (flat winding 62 µH, 32 + 32 T series sandwich 24 µH) |
| design document p 19 | off-the-shelf core with 1 mm gap, Lm 320 µH; "resonance capacitor 22 nF, 220 kHz" |
| design document p 20 - 22 | control range 150 - 270 kHz; rectifier conduction time 2.65 µs; design load 10 A; start-up peak 100 A |
| owner 2026-11-23 | primary 66 T, 8 strands AWG 30: 6 parallel strands wound first, then the secondary (litz 35 × 0.2 mm), then 2 parallel strands; both portions in parallel |
| owner 2026-11-23 | 42 µH leakage, 220 kHz resonance, verified to 15 A secondary current |
| owner 2026-11-23 | the 5.1 resonant capacitors are 4.7 nF **X7R**; measured to give the right resonance at the 200 V bias |
| assumed | core E 25/13/7 (Ae 51.8 mm²), bobbin Norwe 10220-024 (window 4.2 × 15.8 mm), N97; 64 T as documented; 100 °C windings; gap type (centre leg or spacer) unknown |

## Results

**Turns.** The model agrees with 42 µH only for 2 + 2 secondary turns (first run, 66 T: 36 - 38 µH from two solvers,
36 - 57 µH over believable build variants). 1 + 1 turns gives 72 - 77 µH and cannot make 6.3 V from 400 V.
66 T instead of 64 T: leakage +2.6 %, Lm +6 %, output -3 % at the same frequency, peak flux -3 %.

**Resonance and the capacitor change.** The two capacitor halves are in parallel for AC.

| Capacitors | C total | f with 42 µH | f with 58.7 µH (operating, see below) |
|---|---|---|---|
| 5.1: 4 × 4.7 nF X7R at 200 V bias | about 12.5 nF | 220 kHz | 186 kHz |
| 5.2 since ecf0024: 4 × 3.3 nF C0G | 13.2 nF | 214 kHz | 181 kHz |
| first 5.2 parts list: 4 × 4.7 nF C0G | 18.8 nF | 179 kHz | 151 kHz |

With 18.8 nF the time-domain model cannot hold 6.3 V at 380 - 400 V anywhere in 150 - 270 kHz; this is why C22 / C41 /
C42 / C49 were changed to 3.3 nF C0G 630 V (CHANGES_5_2.md row 2.9). Stress per capacitor at 15 A, 400 V, 157 kHz:
200 V dc ± 98 V (about 300 V peak, about 340 V at the start-up spike), 0.22 A rms.

**Operating leakage.** In each half cycle only one secondary half conducts. The model ratio between "one half
shorted" and "whole secondary shorted" is 1.40, so if the 42 µH was measured with the whole secondary shorted the
circuit sees about 59 µH. With 12.5 nF that is 186 kHz, half period 2.69 µs, which matches the 2.65 µs rectifier
conduction time and the 2.6 - 2.8 µs pulses of Fig 4.3. **To settle it on the bench** (LCR meter on the primary,
100 - 200 kHz): one secondary half shorted should read about 55 - 60 µH, all three secondary terminals tied together
about 42 µH, secondary open gives Lm.

**Magnetizing inductance.** 320 µH needs a 1.78 mm centre-leg gap or a 0.84 mm spacer in the model; the documented
"1 mm" fits a spacer gap best (288 µH, -10 %).

**Gain** (Lm 320 µH, 13.2 nF), frequency needed for 6.3 V:

| Input | 6.5 A | 10 A | 15 A |
|---|---|---|---|
| 420 V | 186 kHz | 179 kHz | 171 kHz |
| 400 V | 168 kHz | 163 kHz | 157 kHz |
| 380 V | 154 kHz | 150 kHz | not reachable at or above 150 kHz |

**Flux.** 108 mT peak at 150 kHz, 3.8 times below saturation of N97 at 100 °C (0.41 T). Core loss 0.1 - 0.25 W.

**Losses - model and bench disagree.** With the real gap the model predicts 4 - 6 W in total at 10 - 15 A
(15 A, 161 kHz: 5.9 W with a centre gap, 5.3 W with a spacer), dominated by fringing-field loss in the AWG 30
primary strands near the gap, roughly independent of load and frequency. That would be a 70 - 180 K rise, which is
implausible for a part run at 15 A on the bench. The subagent puts ±50 % on the absolute number and expects less
with a spacer gap (corrected estimate about 2.9 W at 10 A, 4.0 W at 15 A). Without a gap the model gives 2.2 - 2.4 W.
**Open: measure the winding temperature at 10 A and 15 A.**

**Other.**
- Current share between the primary portions (ungapped model): inner 6 strands 38 %, outer 2 strands 62 %.
- Fit: radial stack 4.31 mm against a 4.2 mm window; no room for reinforced insulation as wound.
- Soft switching: magnetizing current at the edge about 1 A; 150 ns dead time may be short (estimate about 270 ns,
  based on a FET output capacitance scaled from another part - speculative). Check the switch-node waveform.
- No single build fits all three measured leakage values of the design document better than about 20 %.

## Not verified

Core material, gap type and real Lm; how the 42 µH was measured; actual primary turns (64 in the document and the
schematic note, 66 per the owner); real temperature at 15 A; output capacitance of IPD60R280P7S; the time-domain
model uses an ideal rectifier and a fixed output voltage.
