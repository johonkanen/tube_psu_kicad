# Review checklist 12 – thermal and mechanical: heatsinks, tall parts, mounting holes, connectors, assembly clearances

You are reviewing **one aspect** of the tube_power 5.2 power-supply board, alone, from this file and the repository
`/home/jari/dev/tube_psu_kicad`. You are doing a design review, not a redesign.

**Rules (full text: `kicad_next/review/README.md`, "Common rules" – read that section first):**
read-only on the repository, the only file you write is `kicad_next/review/findings/12_thermal_mechanical.md`; no
commit, no push; never touch `kicad_next/tube_psu_5_2.kicad_pcb` / `.kicad_pro` and never run a script that saves or
regenerates design files (`route_s*.py`, `update_board_parts.py`, `setup_project.py` / `make_board.py` / generators
without `--check`; **no 3-D render or STEP export of the board either – they are heavy KiCad jobs**); stop if a
KiCad lock file exists (`rv guard`); RAM under 3 GB – no board DRC, no `check_next.sh` (use the existing reports);
never `pkill -f`; never run the KiCad AppImage with `--version`; the owner's name / e-mail stay out of web
requests. **Acceptance bar: match the bench-verified 5.1 board and add creepage – do not optimise beyond that.**
Datasheet facts come from the datasheet you fetch now, not from memory.

## 1. Scope

The board is 163.1 × 110.1 mm (outline x −71.95 … 91.15, y −91.35 … 18.75; same outline as 5.1), 1.6 mm, 6 layers,
parts on both sides (F.Cu: 97 SMD + 61 through-hole footprints incl. holes and wire pads; B.Cu: 216 SMD), no
silkscreen. It is screwed to the earthed amplifier chassis through
**seven mounting holes** (3.0 mm NPTH with a 3.5 mm copper ring, no net): H1 (−67.0, −87.5), H2 (6.9, −87.5),
H3 (87.0, −87.5), **H4 (5.8, −40.1) inside the board**, H6 (−67.0, 14.5), H7 (3.4, 14.5), H8 (84.2, 14.5); H5
(87.15, −29.8) was removed in 5.2. The 2021 build dissipated the heat of the PFC and DHB semiconductors into an
aluminium plate and measured **+30 K on the plate and +25 K on the DHB transformer at full load**, with passive
cooling and a 70 °C rack ambient as the design case (design document p 33 – 34).

**5.2 mechanics that changed:** all primary power semiconductors now stand in one line for one heatsink (owner's
placement, README "Stage 4a"): pin columns at x 3.1 – 3.8 (Q5 TO-247, pins at y −29.6 … −18.7; SICD2 TO-220-2, pins at
y −3.8 … 1.3) and at x 11.4 – 12.75 (Q19 TO-220 y −52 … −47, Q7 y −63 … −58, SICD1 y −26.5 … −21.4, Q6 TO-247
y −7.9 … 3.0). The courtyard boxes of the TO-220 parts show their bodies on the inner side of each column (SICD2
box x 1.5 … 6.5 from pins at 3.1; SICD1 8.4 … 13.3 from 11.8; Q19 / Q7 9.3 … 14.3 from 12.75), i.e. the two columns
face each other across a gap at about x 6.4 … 8.4 where the plate / bracket must stand; the TO-247 courtyards are
nearly symmetric about their pin rows (Q5 0.8 … 6.4, Q6 8.8 … 14.4) – on which side their tabs are is item A1.
In that gap or reaching into it on F.Cu: **H4** (ring x 4.1 … 7.6 at
y −40.1), **DB1** (SMD bridge, box x −1.3 … 8.4, y −16.0 … −8.3), **C73** (2220, box x 8.6 … 16.4, y −17.0 … −11.0),
**C87** (0603, x 4.2 … 7.2, y −60.2 … −58.6) – the known open input "heatsink footprint and height against C73, DB1,
C87, H4". Q21 / Q8 (DAB secondary, TO-220 pins at y −41.95, x 54.7 … 71.4, courtyards y −43.5 … −38.5) keep a separate
secondary heatsink. Other changes: TR1 EEL19 (20 × 23 × 29 mm), TR3 EC42/15 (46 × 42 × 31.5 mm, the heaviest part), L1 / L2 as
upright toroids (31.5 mm high, body position ± 3 mm from a photo), Q10 / Q11 as DPAK on copper, PWM2 SO-12 with a
drain copper area, taller electrolytics (C19 / C30 50 mm, C28 / C29 / C37 / C56 45 mm), J4 1×6 at the top edge,
internal milled slots.

There is **no heatsink drawing in the repository** – only an outline helper footprint in the library
(`lib/tube_psu_next.pretty/Heatsink_Plate_Keepout_L120mm.kicad_mod`, 120 × 3 mm plate, not placed on the board) and
a 30 mm high placeholder STEP model. Part of this review is therefore to state exactly what is fixed by the board
and what the owner still has to define.

## 2. Read first

1. Design document p 33 – 34 (`rv pdf 33 34`): what ran how hot on 5.1; p 11 – 13 and p 25 for losses.
2. `kicad_next/README.md`: "Stage 4a: single primary heatsink line" (table of moves, what stands where);
   "First draft" → table rows courtyards_overlap / pth_inside_courtyard / starved_thermal, "Not checked",
   "Open inputs (user)"; "Stage 7" (420 V capacitor pitch); "Stage 8" (C95 beside DRV5, courtyard pair);
   "Stage 10" (H5); "Footprints and 3D models" (complete: body sizes, heights, "Still to confirm with calipers").
3. `NEXT_REVISION.md` rows 5.4 (DPAK copper), 5.5 (heatsink / bracket, insulation of tabs), 1.3 / 2.3 (placement
   notes); `NEXT_REVISION_PLAN.md` phase 5 (placement constraints 1 – 8).
4. `kicad_next/CHANGES_5_2.md` row "1.5 layout" (PWM2 drain copper 2 – 3 cm², RthJA).
5. `simulation/flyback/EEL19_DESIGN.md` 14.8 (PWM2 and TR1 temperatures); `simulation/dab/DAB_TRANSFORMER.md` 3 and 7
   (TR3 losses); `simulation/dab/DAB_SIMULATION.md` 2.1 (switch losses).
6. The 3-D renders of both boards are on the branch `origin/renders` of this repository (not in the working tree):
   `mkdir -p /tmp/rv12 && git show origin/renders:tube_psu_5_2/3d_top.png > /tmp/rv12/52_top.png`, the same for
   `tube_psu_5_2/3d_bottom.png`, `tube_psu/3d_top.png`, `tube_psu/3d_bottom.png` (5.1); view them with the Read
   tool. Read them from git, **not from the web** (the URL in the top-level README contains the owner's account
   name). They may predate the last routing stages (`git log -1 --format=%cd origin/renders`). Also
   `kicad_next/routing/*.png`.
7. Datasheets to fetch for thermal data: STF7N60M2 (TO-220FP RthJC), C2M0160120D, C3D02060A, TBS22K (RthJA / RthJL,
   package height), IPD60R280P7S (RthJA vs copper area), BUK9Y15-60E, ICE5AR0680AG, a generic thermal pad
   (e.g. 0.3 K·in²/W class) for the interface, Songle SRD and TWW10 dimensions.

## 3. How to extract facts

```sh
kicad_next/review/tools/rv guard && kicad_next/review/tools/rv setup
kicad_next/review/tools/rv bq slots                      # outline box, internal slots / cut-outs
kicad_next/review/tools/rv bq fp H1,H2,H3,H4,H6,H7,H8
kicad_next/review/tools/rv bq51 fp H1,H2,H3,H4,H5,H6,H7,H8
kicad_next/review/tools/rv bq fp Q5,Q6,SICD1,SICD2,Q7,Q19,Q21,Q8,DB1,C73,C87
kicad_next/review/tools/rv bq area 6.4 -66 9.3 8 --touch        # every courtyard that reaches into the heatsink gap x 6.4 … 9.3
kicad_next/review/tools/rv bq area 0 -66 16 8 --touch           # everything in the heatsink line strip, both sides
kicad_next/review/tools/rv bq area 50 -45 76 -36 --touch        # the secondary bridge Q21 / Q8 and its neighbours
kicad_next/review/tools/rv bq area -72 -92 -68 19 --touch       # parts within 4 mm of the west edge
kicad_next/review/tools/rv bq area 88 -92 92 19 --touch         # east edge
kicad_next/review/tools/rv bq area -72 -92 92 -88 --touch       # north (top) edge
kicad_next/review/tools/rv bq area -72 15 92 19 --touch         # south edge
for h in H1 H2 H3 H4 H6 H7 H8; do kicad_next/review/tools/rv bq fp $h | head -1; done
kicad_next/review/tools/rv bq area 1.8 -44.1 9.8 -36.1 --touch  # footprints within a 8 x 8 mm box round H4 (repeat per hole)
kicad_next/review/tools/rv bq fp TR1,TR2,TR3,L1,L2,C19,C30,C28,C29,C37,C56,C102,RL1,R27,CM1,CM4,J2,J4 | grep -v "pad "
python3 - <<'EOF'
# side / package census from the board dump: how many parts per side, THT vs SMD
import json, subprocess, collections
d = json.load(open(subprocess.check_output(["kicad_next/review/tools/rv", "dir"], text=True).strip() + "/b52.json"))
c = collections.Counter()
for f in d["footprints"]:
    tht = any(p["drill"] for p in f["pads"])
    c[(f["side"], "THT" if tht else "SMD")] += 1
print(dict(c))
print("SMD on B with THT nearby is normal here; tall SMD on B.Cu:", [f["ref"] for f in d["footprints"] if f["side"] == "B" and ("CP_Elec" in f["fp"] or "2220" in f["fp"] or "SMA" in f["fp"])])
EOF
python3 kicad_next/review/tools/drc_summary.py
python3 kicad_next/review/tools/drc_summary.py pth_inside_courtyard
python3 kicad_next/review/tools/drc_summary.py courtyards_overlap | grep -c "Courtyards overlap"
python3 kicad_next/review/tools/drc_summary.py courtyards_overlap 0 -66 16 8
kicad_next/review/tools/rv bq net FLY_C | grep zone      # PWM2 drain copper area
kicad_next/review/tools/rv bq net HEATER_HI_SOURCE | grep zone
kicad_next/review/tools/rv bq net Q13_DRAIN Q14_DRAIN | grep -E "==|zone|vias"
grep -n "Heatsink\|HEATSINK" tools/next/gen_next_footprints.py | head
ls lib/tube_psu_next.3dshapes/
```

Part heights are not stored in the board: use the README list ("Tallest parts: C19 / C30 50 mm, C28 / 29 / 37 / 56
45 mm, TR3 31.5, TR1 29.2, R27 26, TO-247 25.4, CM1 / CM4 25"), the `_H<n>mm` suffix of the electrolytic footprints,
and datasheets. The courtyard / body box of every footprint is in `rv bq fp REF` (first line) and
`rv bq area … --touch`.

## 4. Checklist

### A. Primary heatsink line (the open input)

- **A1 Geometry fixed by the board.** From `rv bq fp Q5,Q6,SICD1,SICD2,Q7,Q19`: pin positions, rotation, and the
  side the body / tab faces (the courtyard box extends from the pin row towards the body; TO-220 body ≈ 4.5 mm
  thick, TO-247 ≈ 5 mm; the metal back is the face away from the marking – derive from the KiCad footprint
  `Package_TO_SOT_THT:TO-220-3_Vertical` / `TO-247-3_Vertical` which side of the pin row the tab is on at the
  given rotation). Produce a table: refdes, package, pin-row x, tab-face x, y-extent of the body, tab potential
  (Q5 / Q6 drain = PFC switch node, SICD1 / SICD2 cathode = DC+, Q19 = DC+ (FullPAK: isolated), Q7 = switch node
  (FullPAK)), mounting-hole height of the package above the board (TO-220: ≈ 16.5 mm from the seating plane with
  full-length leads – datasheet; TO-247 ≈ 20 mm). PASS: **all tab faces lie in two planes that a single plate
  (or a U / T profile) can touch**; give the plate thickness that fits between the two rows (distance between
  the tab faces of the west row and the east row) – or FAIL with the x-offset that makes a single flat plate
  impossible.
- **A2 What stands in the plate's way.** `rv bq area 6.4 -66 9.3 8 --touch` on F.Cu: H4 ring (x up to 7.6 at
  y −42 … −38), DB1 (to x 8.4, y −16 … −8.3, height ≈ 2.6 mm assumed – TBS datasheet), C73 (from x 8.6, y −17 … −11,
  2220 MLCC ≈ 2.5 – 2.8 mm high), C87 (to x 7.2 at y −60 … −58.6, 0.9 mm high), SICD2 / Q5 bodies themselves.
  PASS: a plate standing on / just above the board can be notched or raised to clear each (state the required
  notch: position, width, height: e.g. "≥ 3.2 mm clearance height over y −17.5 … −7.8 and a hole or cut-out
  for the H4 screw head at y −40.1"), and nothing else on F.Cu lies in x 6.4 … 9.3 between y −64 and 6.
  CANNOT VERIFY the final fit without a drawing – the finding then lists the dimensions the owner must
  confirm, exactly.
- **A3 H4 and the plate.** H4 is an earthed chassis screw (basic insulation to primary: 3.2 mm creepage, 2.0 mm
  clearance). If the plate is earthed too, it may touch the standoff; if it is floating or at primary
  potential it must keep 2.0 mm clearance / 3.2 mm creepage from the screw, standoff and washer (≈ 6 – 7 mm
  across). Which is intended (NEXT_REVISION 5.5: "plate = primary / earthed")? PASS: stated in a document; else
  a finding "define the plate potential" (shared with checklist 10 D1).
- **A4 Electrical insulation of the tabs.** Bare tabs: Q5, Q6 (TO-247, drain on the back), SICD1 / SICD2 (TO-220-2,
  cathode on the tab) → insulating pad + insulated screw or clip, creepage across the pad edge ≥ the table value
  for the plate's potential (earthed plate: basic for 400 V: 4.0 mm creepage per the README anchor row; primary
  floating plate: functional). Q7 / Q19 STF = TO-220FP (isolated, 2.5 kV class – datasheet). PASS: the documents
  say how each device is insulated (find it; `grep -rn "pad\b\|sil-pad\|insulat" NEXT_REVISION*.md
  kicad_next/README.md | head`), or finding.
- **A5 Screw / clip access.** With devices on both faces of one plate, the mounting screws of the west-row
  devices (Q5, SICD2) and east-row devices (Q6, SICD1, Q7, Q19) must not collide: compare the y-extents
  (Q5 y −32.4 … −15.8 vs SICD1 y −29.2 … −18.6 – they overlap in y on opposite faces → a through screw would join
  both, or two tapped holes collide). List each opposing pair and the y-offset of their mounting holes
  (TO-247 hole ≈ 14.8 – 15.2 mm above the seating plane on the body axis; TO-220 hole on the tab axis – at the
  pin-row centre in y). PASS: no two opposing device holes closer than ≈ 6 mm in y at the same height, or
  clips are specified.
- **A6 Soldering order / tolerance.** Through-hole power parts in a row fixed to one plate: the leads must be
  soldered after the devices are screwed to the plate (or formed) – pin-row x positions fix the plate plane to
  ± 0.3 mm. Two different pin-row x values per face? (West face: Q5 at 3.75, SICD2 at 3.09; east face: Q19 / Q7
  12.75, SICD1 11.8, Q6 11.39.) With different package thicknesses (TO-247 vs TO-220: tab-face offset from the
  pin axis differs) the faces may still be coplanar – compute each tab face x from the package drawings
  (pin-axis-to-back distance: TO-220 ≈ 2.8 mm?, TO-220FP, TO-247 ≈ 2.4 mm? – take them from the datasheets) and
  give the spread. PASS: spread ≤ 0.5 mm per face (leads can take it) – else FAIL with the numbers.
- **A7 Bottom-side parts under the heatsink line.** DRV5, U1, C95, C92 and ≈ 15 more SMD parts sit on B.Cu at
  x −4 … 17, y −65 … −42 between the TO-220 pins (`rv bq area 0 -66 16 -40 --touch`). They are soldered by reflow
  before the THT power parts are hand- or wave-soldered: is there ≥ 1.0 mm between each THT pad of Q7 / Q19 and
  the nearest B.Cu SMD pad for the iron (`rv bq near "Net-(Q19-G)" --within 1.0 --layer B.Cu`, courtyard pairs
  in `drc_summary.py courtyards_overlap 0 -66 16 -40`)? PASS: ≥ 0.5 mm copper-to-copper and no SMD body within
  1.0 mm of a THT pad edge, or the README records the owner's acceptance (stage 8: C95 0.21 mm beside the DRV5
  pin pads is SMD-to-SMD – fine).

### B. Secondary heatsink (Q21 / Q8) and the area round TR3

- **B1** `rv bq fp Q21,Q8`, `rv bq area 50 -45 76 -36 --touch`: both at y −41.95, pins along x, bodies on which side?
  A separate small heatsink at secondary potential / floating: distance to primary copper and parts (the
  L-shaped cut-out begins at x 50.8; TR3 body from y −48; ISO2 at (66.8, −26.6); C98; J2 control card?).
  PASS: a heatsink up to the size used on 5.1 (find it in the design document photos / text or state unknown)
  fits without coming within 4.0 mm (clearance) of primary parts and 11.1 mm creepage along the board.
- **B2 TR3 mass and the cut-out.** EC42/15 with windings ≈ 100 – 150 g on eight soldered pins at the top edge
  between H2 (6.9, −87.5) and H3 (87.0, −87.5) – 80 mm apart, with the L-shaped milled slot (box x 50.8 … 68.6,
  y −62.0 … −39.2) right below it and H5 removed. PASS: reasoned statement on board flex / vibration (guitar
  amplifier: transport shocks, speaker vibration in a combo): support by H2 / H3 / H4 distances, slot not
  cutting the load path between TR3 and the nearest holes; recommend glue / tie only as a note.

### C. Tall parts, envelope, control card

- **C1 Height map.** Table of every part > 12 mm: refdes, height, position (from README + `rv bq fp`), and the
  available height (enclosure) – if the enclosure is not documented, compare with 5.1: which parts are taller
  than on 5.1 (C19 / C30 50 mm vs 5.1's 39 µF cans; C28 … 45 vs 50 mm; TR3 31.5 vs ETD34; TR1 29.2 vs EF20; L1 / L2
  31.5 upright "as on the built 5.1")? PASS: nothing taller than the tallest 5.1 part (50 mm), or noted.
- **C2 Control card over the board.** J2 (2 × 25, 1.27 mm) at x 33.1 … 34.4, y −22.2 … 8.3 carries the FPGA card.
  Card outline and stand-off height: in `~/dev/ti60f225_tube_psu_control_card/` (read-only; look for the board
  outline / README) or the design document p 29 photo. Which power-board parts lie under the card and how tall
  are they (bulk capacitors at x ≈ 20 – 25 are 45 mm tall and 8 mm west of J2; TR1 at x 55 … 72; C1 / C39)?
  PASS: same J2 position as 5.1 (`rv bq51 fp J2`) and no part under the card's footprint taller than on 5.1;
  CANNOT VERIFY if the card outline is not available – say so.
- **C3 L1 / L2 body positions (open input).** Bodies 31.5 × 16.7 mm placed "± 3 mm": `rv bq fp L1,L2` boxes
  (L2: x −31.8 … 1.7, y −52.2 … −30.2; L1 similar at the south edge). Neighbours within 3 mm of each box
  (`rv bq area -35 -55 5 -27 --touch`, and the L1 box): C117, C64, Q5, DRV5 area, H4, the board edge (L1
  courtyard ends 1.0 mm inside the edge). PASS: a ± 3 mm shift of either body hits nothing taller than 3 mm and
  does not overhang the board; else list the conflicts for the owner's measurement.
- **C4 Edge clearances.** `rv bq area … --touch` for the four edge strips: parts whose courtyard is within 1 mm of
  the outline; connectors must reach the edge they serve (J4 at the top edge: pins at x 11.4, y −89 … −76.3,
  cable exit direction?; blade terminals along the west and east edges). PASS: no SMD part within 1.0 mm of the
  edge or of a milled slot (depanelisation / milling stress on MLCCs: C73, C47, C54, C16, C55 2220 parts –
  distance to the nearest slot / edge and orientation), connectors usable with the board mounted.

### D. Mounting holes

- **D1 Positions equal 5.1 (minus H5).** `rv bq fp H…` vs `rv bq51 fp H…`. PASS: identical coordinates for the
  seven holes; H5 absent; `tools/p2k/bin/kipy tools/next/make_board.py --check` would confirm but is part of
  check_next (do not run it here; cite the last check_next result if a log exists, else compare coordinates).
- **D2 Keep-out for screw head / standoff.** For each hole: a 7 mm circle (M3 pan head ≈ 5.6 mm, washer 7 mm,
  hex standoff 5.5 mm AF = 6.35 mm across corners): any footprint courtyard or copper inside on the screw side
  (F.Cu) and the standoff side (B.Cu)? an 8 × 8 mm box round each hole centre, e.g. for H4 `rv bq area 1.8 -44.1 9.8 -36.1 --touch` (boxes
  are squares – check the corners by distance), `rv bq near H4 --within 2.0`. PASS: nothing within r = 3.5 mm of the
  hole centre on either side except the hole's own ring; H4 (inside the DAB / PFC area) gets special attention:
  nearest parts R14 / R1 (B.Cu, x 4.6 … 9.3, y −35.4 … −31.0), the In2 control-bus lanes (not mechanical), DRV5.
- **D3 Support span.** Largest unsupported span between holes and the heavy parts on it (TR3, TR2, L1 / L2, CM1 /
  CM4, bulk capacitors, heatsink plate – is the plate fixed to the chassis or only to the board?). Removing H5
  leaves the east edge supported by H3 and H8 only (102 mm apart) with C19 / C30 / terminals between. Owner's
  decision "does not droop" – note only.

### E. Thermal checks on paper

- **E1 Loss budget table.** For every part dissipating > 0.2 W give loss, thermal path, estimated temperature at
  the 70 °C design ambient (or state 40 °C room as second case): Q5 / Q6, SICD1 / 2, DB1 (SMD, 1 – 2 W? only its
  pads as heatsink, **under / beside the plate**), Q7 / Q19, Q21 / Q8, Q10 / Q11 (DPAK on copper: area from
  `rv bq net`), Q1 / Q2 (LFPAK: ≈ 2 W each at 15 A), PWM2 (drain copper F.Cu 125 mm² + B.Cu 69 mm² = 1.9 cm² vs
  the 2 – 3 cm² asked), TR1, TR2, TR3, L1 / L2, CM1 / CM4, R27 (0 W with the relay closed), R68 (≈ 0.55 W in a 1206 –
  see checklist 01 A13), R125 / R124 preloads, V4 LDO, shunts, the four TO-220 / TO-247 gate drivers
  (UCC21520 at 140 kHz: Qg × V × f + quiescent ≈ 0.1 – 0.2 W each), bulk capacitors (ripple heating). Sources:
  the simulations named in "Read first" and datasheets. PASS: each ≤ its rated temperature with ≥ 15 K margin at
  70 °C ambient, or equal to 5.1's proven situation; list the three hottest.
- **E2 DB1 specifically.** TBS22K SMD bridge between the device rows: conduction loss ≈ 2 × Vf × I_avg ≈ 2 × 0.9 V ×
  1.2 A ≈ 2 W at full load? (In a bridgeless PFC the bridge carries the return current each half cycle –
  checklist 05 A9 gives the number.) Thermal path: pads to the DC+ / GND / AC pours; position unchanged from
  5.1 (`rv bq51 fp DB1`)? PASS: same place and copper as 5.1, or the estimate shows Tj ≤ 125 °C.
- **E3 DPAK and SO-12 copper.** NEXT_REVISION 5.4: "≥ 2 cm² of L1 copper with thermal vias to L2 – L6" for Q10 / Q11;
  CHANGES 1.5: 2 – 3 cm² for PWM2 with "no inner-layer copper on it". `rv bq net HEATER_HI_SOURCE | grep zone`
  (Q10 tab: F.Cu 195 mm²), Q11 tab on DC+ (`rv bq neck DC+ F.Cu -13.838 -73.55 -10.3 -84.925`, area of the local
  DC+ piece), `rv bq net FLY_C | grep zone`. PASS: areas ≥ the documents' own targets or the loss is so small
  (E1) that it does not matter – say which.
- **E4 Heat into neighbours.** Electrolytics next to hot parts: C28 (19.9, −30.2) and C56 beside the heatsink line
  (x 20 vs plate at x ≈ 7 – 9 and Q6 / SICD1 bodies to x 14.4): distance ≥ 5 mm; C31 / C32 beside Q1 / Q2 and TR2;
  C102 / C1 / C2 at TR1; C19 / C30 beside TR3 (courtyard gap 2.85 mm per README). PASS: no electrolytic closer
  than 3 mm to a part running > 85 °C; lifetime note for the bulk capacitors at the ripple current of
  checklist 05 A10.

### F. Assembly

- **F1 Courtyard overlaps (133 documented).** `python3 kicad_next/review/tools/drc_summary.py courtyards_overlap`
  (count) and the README classification: 106 pairs as in 5.1, 26 new courtyard-only pairs, + C95 / DRV5.
  Re-derive the count; then check **the new pairs** against real body sizes (0603 1.6 × 0.8, 0805 2.0 × 1.25,
  1206 3.2 × 1.6, 1210 3.2 × 2.5, 2220 5.7 × 5.0, SOD-323 1.7 × 1.25, SOT-23, SOIC-16W 10.3 × 7.5 body) from
  the footprint positions (`rv bq fp A,B` → centres and rotations). PASS: body-to-body gap ≥ 0.2 mm for every
  new pair (JLC assembly minimum spacing – look up their current figure) and no pad of one part under the body
  of another; list pairs below 0.3 mm.
- **F2 pth_inside_courtyard (2).** IN1 pin 1 and CM1 pin 3 inside the courtyard of C86 – "as in 5.1". PASS if the
  real C86 body (X2 680 nF, 26.5 × 11.5 mm footprint; the ordered generic part's size is flagged "body size to
  verify" in the parts table) leaves the two pins free; CANNOT VERIFY without the part's datasheet dimensions –
  fetch them by LCSC number C2888216.
- **F3 Double-sided assembly.** Census (script in section 3): SMD on F and B, THT parts. Heavy / tall SMD on the
  second reflow side: C58 (5 × 5.4 electrolytic) and SMA diodes on B.Cu? D-PAK / 2220 on F. JLC assembles both
  sides (standard assembly; the stackup excludes economic assembly per README). PASS: no part on B.Cu heavier
  than ≈ 0.1 g per mm² of pad area rule of thumb… simply list B.Cu parts larger than 1210 and say whether they
  need glue.
- **F4 Hand-soldered parts.** Wire pads WP1 – WP4 (4.0 mm pad, 2.55 mm drill) for the heater secondary, TR1 fly
  leads (pads 11 / 12, 1.2 mm drill), transformers, toroids, terminals, TO parts, R27, relay, film capacitors:
  each reachable with an iron after the SMD assembly; thermal relief on plane-connected pins (README: THT pads
  on spokes 0.3 mm gap / 0.6 – 0.8 mm) so that they can be soldered at all on a 6-layer board with two GND
  planes: `python3 kicad_next/review/tools/drc_summary.py starved_thermal`, and spot-check five GND / 6V3 / DC+
  THT pins (`rv bq fp HT_GND` etc.: are they "all Cu" pads tied solid to four layers?). PASS: every THT power pin
  on planes uses thermal relief or is deliberately solid with a note for the assembler.
- **F5 No silkscreen.** Given. Consequence to check: polarity / pin-1 information for hand-placed parts
  (electrolytics, TO parts, transformers, J2, J4, bridge) must exist somewhere else – an assembly drawing with
  refdes and polarity in the fab package (checklist 14) or F.Fab layer content. `grep -c "F.Fab" kicad_next/tube_psu_5_2.kicad_pcb`
  (non-zero) – PASS if the fab layers carry refdes + polarity for every THT part; else finding for 14.

## 5. Out of scope / given

- Electrical creepage numbers (checklist 10), loop / current layout (11), part ratings (13), the fab outputs (14).
- Given: single primary heatsink line and the owner's placement of Q19 / Q7 / SICD1 / SICD2; Q21 / Q8 on their own
  heatsink; H5 removed; toroids upright on the RM8 holes; no silkscreen (do not ask for one); via-in-pad;
  stackup. The heatsink itself is not designed yet – report constraints and conflicts, do not design it.

## 6. Findings format

Write `kicad_next/review/findings/12_thermal_mechanical.md` exactly in the format of
`kicad_next/review/README.md` "Common findings format": summary; one table row per item above (A1 … F5) with
**PASS / FAIL / CANNOT VERIFY** and the evidence (file:line, command + output lines, calculation with inputs, or
datasheet document / page / URL); ranked findings with severity (**blocker for ordering / should fix / note**),
what is wrong, evidence, smallest fix, confidence; "Compared with 5.1"; "Could not verify"; "Outside scope".
"Looks fine" without evidence is not acceptable. Add one section "Dimensions the owner must confirm before
ordering" (the caliper list of the README plus what you found).
