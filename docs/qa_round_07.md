# QA round 07 — Phase 4 polish round 5 gate (2026-09-09)

Scored master: the file on disk at 17:27 (`renders/logs/lead_build_r7.log`, EXIT 0), **9681 objects**, LOD1 **11.38 M tris**,
72 materials, 0 placeholders, 160.9 MB, opens in **0.74 s**; probes baked on the diffuse world (`LIGHTPROBE_rotunda`
20x20x14, `LIGHTPROBE_colonnade` 48x20x6, bake 4.6 s). Merged this round: ARCH r6 + r7, ORN r6 + r7 (+ the lead's LOD1
bake), LIGHT r14 (+ prep), MAT r8, ENV r9. No other Blender ran during any QA render; every render was one blocking
`scripts/blender_run.sh` call.

**The photo-projection pass did NOT ship this round.** MAT r8 was re-scoped by the lead to the water blocker + the coffer
albedo (status.md / decisions.md 2026-09-09 budget plan), so brief item 3's seam check has nothing to inspect: there is no
projected photo in the master, and no seam or doubled feature exists to be a blocker. What item 3 can be answered on is the
delta and the precondition, and both are below (hero **+0.22**, and the stack now registers, so a rigid projection *can*
register from round 08 on).

## What was rendered and compared

| file | what |
|---|---|
| `renders/previews/qa/round07_0K_*.png` | Eevee 1280x720, 32 TAA, LOD1, `apply_preview_eevee`. Times **28.2 / 26.5 / 30.2 / 19.3 / 22.4 / 19.5 s**; whole pass **146.1 s** (round 06: 218.6 s, round 05: 120.6 s) — **-33 %**, QA-06-13 closed. Log `renders/logs/qa_round07_eevee.log`. |
| `round07_01_lagoon_hero_cycles.png` | Cycles 1920x1080, 128 spp adaptive, OIDN, GPU: **373.7 s** (round 06: 381.4 s). Log `qa_round07_cycles_hero.log`. |
| `round07_04_rotunda_ceiling_cycles.png` | Cycles 1280x720, 64 spp: **231 s** (round 06: 219.9 s). Log `qa_round07_cycles_cam04.log`. |
| `round07_06_aerial_nocomp.png` | the un-composited twin of cam06 (Eevee, `use_compositing = False`, 20.1 s) — the cam06 gate is a *ratio* and needs the pair. `scripts/qa_r07_c06.py`, log `qa_round07_c06.log`. |
| `renders/qa_comparisons/round07_cam0K.png`, `round07_sheet.png` | render / canonical photo / 50 % blend per camera; `round07_cam01_cycles.png` is the Cycles hero on the same layout |
| `round07_cam01_aligned_vs_ref169.png` | the round-03..06 yardstick: W_a-aligned overlay on the raw ref 169. Scale **1.3084, dx -290.0, dy -123.0** (round 06: 1.3036 / -286.4 / -121.7) — every earlier box is valid within 5 px, and the cached reference row reproduces exactly on it (attic 188.3 vs 188.2, entablature 148.2 vs 147.6, shaded 118.8 vs 116.3, columns 95.4 / 24.5 / 0.588 vs 95.4 / 24.5 / 0.588, dome cap 236.6 vs 236.5). |
| `round07_cam01_crops_vs_ref169.png` | 1:1 crop pairs (attic + entablature, capital + shaft, reflection, shore) with boxes and numbers burnt in |
| `round07_stack_offset.png` | brief item 1: the hero-facing stack course by course, render beside ref 169 at x8 vertical zoom |
| **`renders/qa_comparisons/round07_gate.png`** | **the gate composite**: Cycles hero beside ref 169, six Eevee views, score deltas r06 -> r07, trend r02 -> r07 |

Commands: `scripts/blender_run.sh 900 -- --background --python scripts/qa_render_round.py -- --round 07 --eevee`;
`... 1500 -- ... --round 07 --final --samples 128 --res 1920 1080 --cams 01`; `... 900 -- ... --samples 64 --res 1280 720 --cams 04`;
`... 300 -- ... scripts/qa_r07_c06.py`; `... 300 -- ... scripts/qa_inspect.py`. Analysis (no Blender): `qa_silhouette.py align`
(crop 690 40 1235 520 / ref-crop 749 127 1165 493), `qa_compare.py`, `qa_crops.py`, `qa_stack_offset.py`,
**`qa_r07_measure.py` (new this round: box / mask / rows / frac / alternation / shadowfrac / mirror / camheight)**,
`qa_gate_sheet.py --round 07`, and the owners' own read-only tools on the merged master: `mat_r6_measure.py cornice|waterline|coffer`,
`env_r7_measure.py --c06ratio`. Nothing was written to master.blend (env's `r7_numbers.json` was reverted after use).

## Score table (0-5; target >= 4 every row, hero average >= 4.5). Round 06 -> round 07.

| row | 01 hero | 02 NE 3/4 | 03 colonnade | 04 ceiling | 05 S lawn | 06 aerial |
|---|---|---|---|---|---|---|
| Silhouette match | 4 -> 4 | 3.5 -> 3.5 | 2.5 -> 2.5 | 3.5 -> 3.5 | 3.5 -> 3.5 | 4 -> 4 |
| Proportion | 3.5 -> **4** | 3.5 -> 3.5 | 3 -> 3 | 3.5 -> 3.5 | 3 -> **3.5** | 3.5 -> 3.5 |
| Ornament fidelity | 3.5 -> **4** | 3 -> **3.5** | 2.5 -> 2.5 | 3 -> 3 | 3 -> **3.5** | 2.5 -> 2.5 |
| Material realism | 3 -> 3 | 2.5 -> **3** | 1.5 -> **2** | 2.5 -> **3.5** | 3 -> 3 | 1.5 -> **2.5** |
| Edge wear | 2.5 -> **3** | 2 -> **2.5** | 1 -> 1 | 1 -> 1 | 2 -> 2 | 0.5 -> 0.5 |
| Lighting mood | 4 -> 4 | 3 -> **3.5** | 2 -> **2.5** | 3 -> 3 | 3.5 -> 3.5 | 2 -> **2.5** |
| Water reflection | 2 -> **2.5** | 1.5 -> **2.5** | n/a | n/a | 1.5 -> **2.5** | 1.5 -> **2** |
| Repetition visibility | 3 -> 3 | 2.5 -> 2.5 | 2 -> 2 | 2.5 -> 2.5 | 2.5 -> 2.5 | 2.5 -> 2.5 |
| Scale cues | 3.5 -> 3.5 | 3 -> 3 | 2.5 -> 2.5 | 3 -> 3 | 3 -> 3 | 2.5 -> 2.5 |
| **average (delta)** | **3.44 (+0.22)** | **3.06 (+0.33)** | **2.25 (+0.12)** | **2.88 (+0.12)** | **3.00 (+0.22)** | **2.50 (+0.22)** |

**Hero delta, stated explicitly (brief item 3): 3.22 -> 3.44, +0.22 — the first hero gain in five rounds, and the first
round in which all six cameras gained at once.** No row was re-scored on new evidence this round; every change is a change
in the render. On the round-05 basis (Proportion held at 4 through round 06) the hero reads 3.28 -> 3.44, +0.16.

### Trend across rounds 02 -> 07 (averages)

| cam | r02 | r03 | r04 | r05 | r06 | **r07** | reading |
|---|---|---|---|---|---|---|---|
| 01 hero | 2.94 | 3.28 | 3.28 | 3.28 | 3.22 | **3.44** | four flat rounds broken: Proportion, Ornament, Edge wear and Water each +0.5 |
| 02 NE 3/4 | 2.11 | 2.33 | 2.67 | 2.78 | 2.72 | **3.06** | best gain of the round (+0.33): the violet went out of the shade and the water |
| 03 colonnade | 1.94 | 2.13 | 2.00 | 1.75 | 2.12 | **2.25** | second gain in a row, still the worst camera: 28 % of the frame under lum 10 |
| 04 ceiling | 2.31 | 2.13 | 2.44 | 2.56 | 2.75 | **2.88** | the coffer albedo landed (sat 0.91 -> 0.47); the Eevee/Cycles west soffit still disagrees |
| 05 S lawn | 2.11 | 2.67 | 2.72 | 2.78 | 2.78 | **3.00** | first time at 3.00: registered stack + warm water |
| 06 aerial | 2.17 | 2.17 | 2.39 | 2.50 | 2.28 | **2.50** | the lavender flood is gone; the frame is now a milky haze (0 far-shore lines composited vs 5 un-composited) |

Verdict: **gate not passed** (target >= 4 on every row, hero >= 4.5). But for the first time the round did not trade one
row for another: **eight of the thirteen round-06 defects closed or half-closed on their own acceptance numbers and nothing
that was passing went below its window except the hero's shade level (114.7 -> 134.0, 13 % over ref) and the aerial's
far-field structure.** The four-round pattern from rounds 4-6 ("meet the number, break a row nobody measured") did not
repeat: LIGHT r14's tint fix held the hero shade *colour* (32.1 vs ref 30.5) while moving cam03/05/06, and MAT r8's water
fix did not touch the stone.

Explicit "clean CAD / game asset" rejects this round, each with its crop:
- **The arch soffit / intrados on the hero** (`round07_cam01_crops_vs_ref169.png` pane 2): a smooth untextured pale-yellow
  vault where the photo carries a moulded archivolt with a coffered soffit. ARCH r7 shipped the 8 archivolt sockets; nothing
  is instanced on them yet, so at 1:1 the largest single surface in the pane is blank.
- **The open lagoon** (`round07_cam01.png`, and the gate composite's two top panels): flank box **189.5 / hue 224.2** against
  the photo's **152.4 / 200.3** — 1.24x too bright and 24 deg too blue; near water 143.9 / **227.9** vs 105.4 / 190.0. The
  reflection under the building is now right and the water either side of it is a lavender plastic sheet.
- **cam06's far field**: composited far-shore line count **0** (un-composited 5), crop std 32.0 vs 50.6 un-composited. The
  city is a milky gradient; the mist erased the structure the geometry actually has.
- **The attic relief at 1:1** (crops pane 1): the render's figures are soft-edged with no cast shadow between limb and ground,
  the dentil course is a single row of plain blocks where the photo has modillions over dentils.

## What works (keep it)

- **The hero-facing stack registers.** All eight named courses within **5 rows (0.37 m)** of ref 169 under the alignment that
  puts the apex within 0.51 % of frame height; attic storey **100 rows vs the photo's 101**; see (g). Round 06 was +0.07 to
  +2.31 m with the attic storey at 0.70.
- **The capitals read.** Luminance alternation along the capital band: **20 maxima vs the photo's 17** over the same 530 px,
  contrast **1.118 vs 1.178** (0.95 of the photo's). Capital height 35 rows vs the photo's 30. Round 06: a 24 px blob.
- **Weathering runs the right way for the first time.** Attic streak anisotropy **3.12** (ref 4.08) against round 06's 0.41;
  under-cornice run-off **19.2 % of columns >= 15 lum below the field = the photo's own 19.2 %** (round 06: 11.7 %);
  waterline band 43.6 % on 227 columns (photo 38.2 %).
- **The entablature closes QA-06-9**: row-profile std **44.0** on 900 262 1020 296 (test >= 40; round 06 36.5, photo 54.3).
- **The reflection carries stone colour**: R-B **+36.4** (test >= +35; round 06 **+2.5**, photo +71.7) at hue **36.5**
  (window 25-45) and sat 0.307.
- **The violet flood is gone**: cam06 plaza hue 268.8 -> **33.3**, trees 239.9 -> **32.6**, roofs 253.4 -> neutral
  (R-B +2.2 at sat 0.063); cam02 water 265.5 -> **43.5**; cam03 walk 222.6 -> 195.6 at sat 0.558 -> 0.175.
- **The vault is the colour of concrete**: coffer sat **0.467** Cycles / 0.499 Eevee against ref 083's 0.427 (round 06:
  0.914 / 0.966), with coffer / own sky **0.465** (window 0.35-0.55) and dark/light quarter **0.233** (ref 0.265) held.
- **Eevee is cheap again**: six-camera pass **146.1 s** (round 06 218.6 s; test < 150 s) — QA-06-13 closed.
- **cam03 is half as black**: frame below lum 10 **46.1 % -> 28.0 %**, below 20 **72.7 % -> 57.1 %**; the walk is clear and
  visible across the full frame width (ENV r9's 2.80 m gallery width and 1.71 m clearance are visible, no shrub in the walk).
- Sunlit attic luminance **190.4** (window 178-201, ref 188.3); columns hue **25.9** / sat **0.610** (ref 24.5 / 0.588);
  south wing **104.2** on the aligned panel (test >= 103) at sat 0.247 against the photo's own 0.153.
- Saved deliverable state intact (see "Deliverables present").

## Measurements

### (a) Chroma at delivery resolution (Cycles hero 1920x1080, QA round-03 boxes; ref 169 measured on THIS round's aligned panel)

| region | box | round 06 | **round 07** | ref 169 (aligned) | verdict |
|---|---|---|---|---|---|
| sunlit attic panel | 900 222 1020 256 | 180.4 / 36.3 / 0.473 / 102.7 | **190.4** / 35.8 / **0.437** / **98.8** | 188.3 / 40.5 / 0.580 / 132.8 | lum **pass** (1.01); sat 0.14 under, R-B 34 short — **worse than r06** |
| attic string course | 880 214 1040 222 | 175.6 / 35.7 / 0.436 | 171.9 / 35.9 / 0.462 | 185.3 / 39.3 / 0.585 | lum 0.93; sat low |
| entablature | 900 262 1020 296 | 125.5 / 37.8 / 0.707 | **142.8** / 38.2 / **0.626** | 148.2 / 33.8 / 0.581 | lum **0.96**, sat now inside <= 0.70 — **pass** |
| dome cap | 920 95 1000 120 | 206.6 / 33.1 / 0.216 | 206.2 / 35.6 / 0.248 | 236.6 / 45.8 / 0.257 | lum 0.87, hue 10 cool |
| shaded attic | 1110 225 1150 260 | 114.7 / 30.7 / 0.373 | **134.0** / **32.1** / **0.310** | 118.8 / 30.5 / 0.451 | hue + sat pass; **lum 1.13, outside the 103.5-126.5 window (regression)** |
| columns (mask hue<32 sat>0.30, 680 280 1240 470) | mask | 108.5 / 24.0 / 0.573 | 107.4 / **25.9** / **0.610** | 95.4 / 24.5 / 0.588 | hue + sat **pass**; lum ratio 1.13 |
| water reflection column | 900 760 1020 840 | 103.0 / 87.0 / 0.043 / **+2.5** | **105.6 / 36.5 / 0.307 / +36.4** | 164.8 / 33.7 / 0.373 / +71.7 | **R-B pass, hue pass, lum 0.64 fail** (window 124-208) |
| ripples | 1100 960 1500 1060 | 114.9 / 215.4 / -36.9 | 139.6 / 229.7 / **-47.6** | 104.2 / 182.2 / -16.7 | worse: 1.34x bright, 47 deg blue |
| near water, sky-reflecting | 1150 1000 1450 1050 | 0.303 / 213.8 | 0.300 / **227.9** / lum 143.9 | 0.248 / 190.0 / 105.4 | hue 38 deg off (window 185-200), **worse**; lum 1.37 |
| lagoon flank | 100 900 400 960 | 156.6 / 211.2 | **189.5 / 224.2** | 152.4 / 200.3 | 1.24x bright, 24 deg blue — **worse** |
| sky top / sky low-left | lighting's boxes | 154.8 / 167.9 -> 0.922 | 154.8 / 167.9 -> **0.922** | aligned panel 0.921 | closed, unchanged |
| shore band | 700 600 1200 740 | 91.6 / 40.6 / 0.529 | **88.8** / 41.8 / 0.595 | 115.7 / 40.9 / 0.631 | 0.77 (test +-25 %, pass by 0.02) |
| south wing | 60 480 560 600 | 94.2 / 32.0 / 0.186 | **104.2** / 36.7 / 0.247 | 113.8 / 35.1 / **0.153** | **0.92 — aligned test (>= 103) passes**; sat now ABOVE the photo's |
| north wing | 1360 480 1860 600 | 140.1 / 40.7 / 0.430 | 142.3 / 40.7 / 0.432 | 146.4 / 42.2 / 0.491 | 0.97 pass |

### (b) Texture / weathering at 1:1 and its direction

| box | round 05 | round 06 | **round 07** | ref 169 | ratio / reading |
|---|---|---|---|---|---|
| attic std 900 222 1020 256 | 28.8 | 32.6 | **29.4** | 44.9 | **0.65 pass** (test 0.60) |
| entablature std 900 262 1020 296 | 33.5 | 52.0 | **53.7** | 64.6 | 0.83 pass |
| attic **anisotropy** 900 222 1020 256 | 0.64 | 0.41 | **3.12** | **4.08** | **pass** (test >= 2.0), 0.76 of the photo |
| attic anisotropy, narrow box 900 224 1020 248 | — | 0.76 | **3.52** | 4.33 | pass on the secondary box too |
| entablature row-profile std 900 262 1020 296 | 20.9 | 36.5 | **44.0** | 54.3 | **pass** (test >= 40) — QA-06-9 closes |
| under-cornice run-off (`mat_r6_measure cornice`) | 10.0 % | 11.7 % | **19.2 %** | **19.2 %** | **equal to the photograph** (test >= 19 %) |
| waterline band (`mat_r6_measure waterline`) | 39.3 % / 84 cols | 44.9 % / 245 | **43.6 % / 227** | 38.2 % | pass, held |

Caveat QA states against its own number: part of the anisotropy jump is geometric, not material. In round 06 the attic box
was 53 % cornice (the render's panel frame bottom sat at row 238); after ARCH r6 the same box is entirely inside the attic
panel (frame 199-265), so the box now contains the panel's *vertical relief figures* — which the photo's box also contains.
The comparison is like-for-like for the first time, and the 3.12 : 4.08 ratio is honest, but MAT should not read it as proof
that the streak maps changed: they did not ship this round.

### (c) Interior fills, cam04 vs ref 083 (round-03 boxes)

| ratio | ref 083 | r06 Eevee | r06 Cycles | **r07 Eevee** | **r07 Cycles 64 spp** |
|---|---|---|---|---|---|
| soffit / own sky (W / E) | 0.381 / 0.429 | 0.432 / 0.402 | 0.237 / 0.471 | **0.440 / 0.405** | **0.238 / 0.472** |
| coffer field / own sky | 0.437 | 0.346 | 0.451 | **0.356** | **0.465 pass** |
| dark quarter / light quarter | 0.265 | — | 0.234 | — | **0.233 pass** (test >= 0.20) |
| coffer sat / rim sat | 0.427 / 0.438 | 0.966 / 0.922 | 0.914 / 0.782 | **0.499 / 0.408** | **0.467 / 0.323 pass** (window 0.38-0.50; the Cycles rim is now 0.06 *under*) |
| Eevee - Cycles gap (test <= 0.15) | | | | coffer **-0.109 pass**; soffit E -0.067 pass; **soffit W +0.202 fail** (r06 +0.195) |

### (d) cam03 — the shade test on the round-06 boxes (`light_r14_measure.BOXES`)

| box | what it is | round 06 | **round 07** | / sunlit rotunda (560 0 880 320, lum **98.2**) |
|---|---|---|---|---|
| 480 150 560 600 (the test) | the sky-visible shaft flank | 33.8 / 45.2 / 0.737 | **50.7 / 48.5 / 0.808** | **0.516** — inside the 0.30-0.70 window |
| 880 120 1200 600 | the outer (lagoon-side) row | 5.8 / 83.3 / 0.460 | **9.5 / 70.8 / 0.922** | **0.097** (test >= 0.15 at hue 25-60) — **still fails** |
| 420 560 900 720 | the walk | 41.7 / 222.6 / 0.558 | **54.8 / 195.6 / 0.175** | 0.558; hue window 25-60 **still fails**, but the chroma is nearly gone (sat 0.175) |
| 0 150 420 720 | the retired, sky-occluded box | 13.3 / 197.7 | 18.8 / 75.2 | 0.191 |
| frame below lum 10 / 20 | | 46.1 % / 72.7 % | **28.0 % / 57.1 %** | test <= 20 % — **still fails, halved** |

### (e) cam02 / cam05 / cam06 (Eevee 1280x720, `light_r14_measure.BOXES`)

cam02: shade pier 70.5 / hue **7.0** / sat 0.242 (r05 41.6, r06 blue; now over-warm past the 25-60 window on the low side);
shade soffit 67.6 / 25.7 / 0.485; balustrade 72.8 / 42.7 / 0.564; water 46.3 / **43.5** / 0.110 (r06 64.3 / 265.5 / 0.178).
cam05: water band (448 619 960 713) **128.6 / 35.3 / 0.244** vs ref 063 93.4 / 64.9 / 0.306 — **sat passes (>= 0.24), hue
misses 40-80 by 4.7 deg, lum 1.38x (window 70-117) fails**; attic band (300 150 980 260) 159.9 / 39.1 / 0.440, std 47.0
against ref 063's 63.5 on the same box = **0.74 pass**.
cam06: roofs 116.0 / hue 317.1 / sat 0.063 / R-B **+2.2** (near-neutral, i.e. the flood is gone but the band is not warm);
plaza 101.2 / **33.3** / 0.175; trees 114.6 / **32.6** / 0.244; horizon crop (rows 0-220) mean 109.7 **std 32.0**
(r06 122.3 / 38.0). **cam06 gate (ENV's definition): std composited / un-composited = 32.0 / 50.6 = 0.631 (test >= 0.60) —
pass**, computed by `env_r7_measure.py --c06ratio` on this round's pair. Far-shore lines: **0 composited, 5 un-composited**
(QA-06-12's >= 3 fails on the frame the viewer sees).

### (f) Wings on the hero, on a render (the environment item)

Definition QA uses, stated because it is not ENV's ray probe: within each wing band, "in shadow" = below **half the band's
own 90th-percentile luminance** (so exposure cancels).

| band | box | render p90 / shadow share | ref 169 aligned p90 / shadow share | reading |
|---|---|---|---|---|
| SOUTH (frame-left) | 60 480 560 600 | 204.0 / **57.2 %** | 220.0 / **53.9 %** | +3.3 pt darker than the photograph |
| NORTH (frame-right) | 1360 480 1860 600 | 219.5 / **36.3 %** | 229.0 / **39.0 %** | -2.7 pt, i.e. slightly *less* shadow than the photograph |

ENV's own ray probe says 21.2 / 21.2 % of the wing entablature band is in tree shadow against a 22 % cap (0.8 pt of margin).
On the render the wings are not over-shadowed: both bands are within 3.3 points of ref 169's own dark share. QA accepts the
21.2 % probe figure as confirmed on a render at the level the picture can resolve, and notes that the two statistics are not
the same quantity (the probe counts wing surface; the box counts every pixel in the band, foliage included).

### (g) The hero-facing stack, course by course (brief item 1, QA-06-1's acceptance)

Method unchanged from round 06: `scripts/qa_stack_offset.py` on the aligned overlay, band x 880-1040, row-mean luminance,
courses at local extrema of dL/dy, read against the labelled x8 panel `round07_stack_offset.png`. Positive = the render's
course sits **higher** in frame than the photograph's. 13.42 px/m.

| course | r06 render / ref | **r07 render row** | **ref 169 row** | **delta rows** | **delta m** |
|---|---|---|---|---|---|
| attic crown cornice, top lit edge | 168 / 169 (-1) | 165 | 169 | **-4** | **+0.30** |
| attic crown corona, shadow under it | 178 / 182 (-4) | 181 | 182 | **-1** | **+0.07** |
| attic panel frame top | 181 / 198 (-17) | 199 | 198 | **+1** | **-0.07** |
| attic panel frame bottom | 238 / 269 (-31) | 265 | 270 | **-5** | **+0.37** |
| entablature cornice corona (shadow onset) | 254 / 281 (-27) | 281 | 282 | **-1** | **+0.07** |
| dentil band bottom | 280 / 298 (-18) | 294 | 292 | **+2** | **-0.15** |
| frieze top | — | 301 | 297 | **+4** | **-0.30** |
| frieze bottom = architrave top | 302 / 320 (-18) | 321 | 321 | **0** | **0.00** |
| capital top (abacus) | 306 / 321 (-15) | 333 | 328 | **+5** | **-0.37** |

**Every course is within 5 rows (0.37 m) of the photograph; the acceptance was +-8 rows. QA-06-1 is closed.**

| storey | render rows | ref rows | render / ref | round 06 |
|---|---|---|---|---|
| attic (crown top -> panel frame bottom) | 165-265 = **100** | 169-270 = **101** | **0.99** (test: within 10 %) | 0.70 |
| entablature cornice (corona -> frieze top) | 281-301 = 20 | 282-297 = 15 | 1.33 | 1.53 |
| frieze (frieze top -> architrave top) | 301-321 = 20 | 297-321 = 24 | 0.83 | 1.00 |
| capital (abacus top -> shaft top) | 333-368 = **35** | 328-358 = **30** | **1.17** | 0.65 |

**Consequence for the photo-projection pass: the precondition is now MET.** The residual spread across the whole elevation
is 9 rows (0.67 m) against round 06's 31 rows, and the two storeys that a projection cares about (attic, frieze) are within
1 % and 17 %. A single rigid scale-and-shift now lands each photographic band on the modelled band that means the same
thing. The remaining sub-course errors (cornice 1.33, capital 1.17) are within the width of a projected moulding.

### (h) Brief item 5 — ref 169's camera height over the water

Geometry (level camera, water plane): with the horizon at image row `s`, a point at height `H` above the water at
distance `d` images at `y = s - k(H - h)` and its reflection at `y = s + k(H + h)`, `k = f/d`. Their midpoint is the
**mirror row** `M = s + k h`, so **`h = H (M - s) / (M - y_direct)`** — no focal length or distance needed. `M` is measured
by maximising the correlation between the building's row profile and the water's reflected profile
(`qa_r07_measure.py mirror`).

| quantity | render (cam01) | ref 169 (raw 1920x1192) |
|---|---|---|
| mirror row M | 693.9 (predicted; measured correlation is unusable, corr 0.17-0.36 on a dark mirror) | **622.0** (corr **0.72-0.76** on two independent bands) |
| horizon row s | **655.2** = 540 + 0.06 x 1920 (level camera, `shift_y` 0.06) | **596** assumed (level, principal point at the frame centre) |
| direct course row (attic crown), height above water | 165, H = **39.60 m** (crown 38.30 m, water -1.30 m) | 223.2, same course |
| implied k (px per metre at the attic's distance) | 13.36 | 10.03 -> **13.12 in the render's grid** (x 1.3084) — within **1.8 %** of the render's, which is the check that M is right |
| **camera height over the water** | **2.90 m** (the tool returns 2.90 from the row data, i.e. the method is self-consistent) | **2.6 m** |

Sensitivity: the horizon is the only assumption. s = 590 / 596 / 602 / 608 gives **3.18 / 2.58 / 1.99 / 1.39 m**;
M is good to +-3 rows = +-0.3 m. So **ref 169's photographer stood 2.6 m over the water (1.9-3.2 m)** against cam01's
**2.90 m** — the same eye height within the measurement's own error, and a plausible standing eye height on a path
1.0-1.5 m above the lagoon. **The hero camera is at the right height and the 0.88 reflection ratio is not a station
problem.** The render's own reflection / sunlit-attic ratio is **105.6 / 190.4 = 0.55** against the photo's
**164.8 / 188.3 = 0.88**: the mirror returns 0.63 of what it should. That is the water shader's reflectance and the
brightness of what it mirrors, not the camera. **Do not move cam01** (every yardstick in rounds 03-07 is aligned to it).

### (i) Brief item 2 — the cam02 station

| | current cam02 (QA round 04) | ARCH r7's ref-062 fit (r7 review correction) |
|---|---|---|
| station | az **160** (SSE), D 75 m, eye 1.5 m, **24 mm** | az **17** (NNE), D **83.4 m**, eye 1.55 m, ~40 mm, pitch +13.5 |
| world coords | (70.5, 25.6, 1.1) -> (0, 0, 21.1) | **(-79.8, 24.4, 1.55) -> (0, 0, 23.5)** |
| on land? | yes | yes (the az-37 / D 88.6 variant is in the lagoon; az 17 is not) |
| residuals | letterboxed targets: apex 0.07 (ref 0.07), podium base 0.86 (ref 0.85), **attic width 0.41 vs the photo's 0.55 = -25 %** | rows chi2 7.80; dome apex -0.2 px, attic top -0.22 m, **attic base +0.83 m (2.0 %H)**, arch springing +0.23 m, attic-ring width **-1.0 %**, podium base -2.05 %H |

**The fitted station beats the current one** (worst residual 2.0 % of frame height against a 25 % width miss), and it also
sits on the **correct side of the building**: ref 062 is "View of Rotunda from north east" and the current cam02 stands
SSE, i.e. QA round 04 substituted the mirror-image face. **Decision: cam02 is NOT re-stationed inside this gate**, and the
station above is handed to the lead for round 08. Reasons, stated so the lead can overrule: (1) every cam02 acceptance
number in rounds 04-07 — including QA-06-2's four shade boxes, which are this round's evidence — is tied to the current
frame, and moving the camera mid-gate would invalidate the comparison the brief asked for; (2) the change is a 24 mm wide
view to a ~40 mm rotunda portrait, which is an art-direction call about what cam02 is for, not a QA correction;
(3) architecture's own az scan is flat (chi2 7.69 at az 37, 7.80 at az 17), so the azimuth is chosen, not measured.
No courses were moved.

## Viewport performance (pass/fail, not scored)

- Open **0.74 s** headless (budget 60 s) — pass. 9681 objects, 72 materials, 0 placeholders, file 160.9 MB.
- LOD1 **11.38 M tris** (round 06 11.11 M) — pass.
- Eevee 1280x720 previews **19.3-30.2 s** per camera at LOD1, whole pass **146.1 s** vs round 06's 218.6 s — **pass, -33 %**
  (QA-06-13's test was < 150 s). Round 05's 120.6 s is not back, and the hero shade term is what the extra 25 s buys.
- Cycles hero 1920x1080 128 spp adaptive **373.7 s** (381.4 s); cam04 64 spp 1280x720 **231 s** (219.9 s).

## Deliverables present (pass/fail)

- Cycles final config **pass, as saved**: GPU, 768 spp adaptive (threshold 0.01, min 64), OIDN, time limit 0,
  `AgX - High Contrast`, exposure -2.8331, 1920x1080 at 100 %.
- `CAM_flythrough`, `CAM_flythrough_path`, `CAM_flythrough_target` **pass**; frame range **1-1224 at 24 fps** (LIGHT r14's
  51 s path) **pass**; 2 light probes **pass**; 7 cameras, active camera = the hero.
- Eevee viewport config **pass**: taa 8 / 16, raytracing off, shadow ray count 1; ceiling readable (Eevee coffer / sky 0.356).
- 4K 768-spp timing (QA-03-16): **not run this round** by instruction. Still open, still the only untested delivery item.

## Status of every round-06 defect (measured on the lead's master, brief item 1)

| defect | owner | status | the number |
|---|---|---|---|
| QA-06-1 hero stack does not register | architecture | **CLOSED** | all eight courses within **5 rows / 0.37 m** (was +0.07 to +2.31 m); attic storey **100 vs 101 rows** = 0.99 (was 0.70); capital 35 vs 30 rows (was 0.65); apex within 0.51 %H. |
| QA-06-2 diffuse tint floods four cameras violet | lighting | **closed on 3 of 4 boxes** | cam06 plaza hue **33.3** (window 21.6-51.6 pass), trees **32.6** (pass), roofs neutral R-B +2.2 at sat 0.063 (out of 200-300, but not warm either); cam02 water **43.5**; cam03 walk **195.6** at sat 0.175 — **still outside 25-60**. Hero shade colour held: **32.1 / 0.310** vs ref 30.5 / 0.451. |
| QA-06-3 water fails everywhere | materials | **half closed** | hero reflection **R-B +36.4 pass, hue 36.5 pass, lum 105.6 fail** (124-208); cam05 band sat **0.244 pass**, hue 35.3 fail, lum 1.38x fail; cam06 lagoon no longer white; **near water hue 227.9 (was 213.8) and lagoon flank 189.5 / 224.2 are worse than round 06.** |
| QA-06-4 attic weathering isotropic | materials | **CLOSED on both boxes** | anisotropy **3.12** wide / **3.52** narrow (test >= 2.0; photo 4.08 / 4.33) with std ratio **0.65** held; under-cornice run-off **19.2 % = the photo's 19.2 %** (test >= 19 %). See the caveat in (b): part of this is ARCH's geometry. |
| QA-06-5 sunlit stone lost its chroma | materials | **open, worse** | attic sat **0.437** (window 0.53-0.62; r06 0.473) and R-B **98.8** (test >= 120; r06 102.7). The luminance is right (190.4) and the colour is 25 % short of the photo's. |
| QA-06-6 capitals / ornamented band are a massing model | ornament | **half closed** | height 35 rows vs the photo's 30 (r06 24 vs 37); **alternation 20 maxima vs 17, contrast 1.118 vs 1.178** — the acanthus/volute modulation is there. Open: the bed-mould has no modillions and **the archivolt is still blank** (ARCH r7 shipped 8 sockets, nothing instanced). |
| QA-06-7 cam03 half black | lighting | **half closed** | frame below lum 10 **46.1 % -> 28.0 %** (test <= 20 %); outer row **0.066 -> 0.097** of sunlit (test >= 0.15) at hue 70.8. |
| QA-06-8 vault saturation | materials | **CLOSED** | coffer sat **0.467** Cycles / 0.499 Eevee (window 0.38-0.50; ref 0.427) with coffer / sky **0.465** held. New residual: the Cycles rim is now **0.323**, 0.06 under the window. |
| QA-06-9 entablature row std | architecture | **CLOSED** | row-profile std **44.0** on 900 262 1020 296 (test >= 40; r06 36.5, photo 54.3); texture std 53.7 = 0.83 of the photo's. |
| QA-06-10 Eevee-Cycles soffit W gap | lighting | **open, unchanged** | gap **+0.202** (test <= 0.15; r06 +0.195); Cycles soffit W 0.238 vs ref 083's 0.381. |
| QA-06-11 south wing | lighting + environment | **CLOSED** | **104.2** on the aligned panel (test >= 103; r06 94.2) = 0.92 of ref; sat 0.247 against the photo's own **0.153** — the r06 test's sat half was mis-specified (it compared to the north wing, not to ref 169). |
| QA-06-12 cam06 street lines | environment | **open, regressed** | **0** far-shore lines composited (r06 2; test >= 3), **5** un-composited. The ratio gate that replaced it passes: **0.631** (test >= 0.60). |
| QA-06-13 Eevee preview cost | lighting | **CLOSED** | six-camera pass **146.1 s** (test < 150 s; r06 218.6 s) with the hero shade term held. |
| QA-03-16 4K 768 spp timing | lead | **open, not run** | excluded from this round by the brief. |

## Defect list — round 07

| id | cam | owner | severity | description (measurable) | where | acceptance test |
|---|---|---|---|---|---|---|
| QA-07-1 | 01, 02, 05, 06 | materials + lighting | **blocker** | The open lagoon is a bright lavender sheet either side of the (now correct) reflection: flank 100 900 400 960 **189.5 / hue 224.2** vs the photo's 152.4 / 200.3 (1.24x bright, 24 deg blue); near water 143.9 / **227.9** / 0.300 vs 105.4 / 190.0 / 0.248; ripples R-B **-47.6** vs -16.7; cam05 band lum **128.6** vs 93.4 (1.38x). The mirror got its stone colour and everything the water shows of the SKY got brighter and bluer. MAT r8 and LIGHT r14 each moved it in the same direction. | `MAT_water_lagoon` sky-facing sheen / murk vs incidence; the r14 sky's horizon term (MAT r8's hand-off: "the r14 sky moved near-water 214 -> 228") | near water 1150 1000 1450 1050: **hue 185-200 and lum within 25 % of 105** ; flank 100 900 400 960 within 25 % of 152 at hue <= 210; cam05 band lum 70-117 with sat >= 0.24 held; hero reflection box unchanged (R-B >= +35, hue 25-45). |
| QA-07-2 | 01 | materials | **blocker** | Sunlit stone is 25 % short of the photograph's chroma and got worse: attic sat **0.437** (window 0.53-0.62, ref 0.580; r06 0.473), R-B **98.8** (test >= 120, ref 132.8), string course 0.462 vs 0.585. Luminance, texture std and streak direction all pass now, so the only thing between this frame and the photo's stone is colour. | `MAT_concrete_ochre` base albedo saturation (the round-06 hand-off of +0.11 sat / +30 R-B was never applied) | attic 900 222 1020 256 **sat 0.53-0.62 and R-B >= 120** with lum held at 178-201, the shaded attic at hue 29.5 +- 6 / sat <= 0.50, and the columns mask held at hue 24.5 +- 4 / sat 0.55-0.65. |
| QA-07-3 | 01 | materials | major | The hero mirror is 0.64 of the photograph's brightness: reflection box **105.6** vs 164.8 (window 124-208), i.e. reflection / own sunlit attic **0.55** against the photo's **0.88**. QA item 5 rules out the camera: cam01 is 2.90 m over the water against ref 169's measured **2.6 m**. MAT r8 got the colour (R-B +36.4) and stopped 20 lum short of the level. | `MAT_water_lagoon` specular level / roughness at 87-89 deg, and the luminance of what is mirrored (the building's lower stone) | reflection box 900 760 1020 840 **lum 124-208** with R-B >= +35 and hue 25-45 held. |
| QA-07-4 | 01, 02 | ornament + architecture | major | The archivolt is still a blank vault: at 1:1 (crops pane 2) the arch soffit is a smooth untextured surface where the photo has a moulded archivolt over a coffered soffit, and the bed-mould under the cornice has no modillions. ARCH r7 shipped **8 archivolt_run sockets**; nothing is instanced on them. This is the largest blank surface in the hero's ornament zone. | `ORN` archivolt band on `SOCKET_archivolt_run_##` (band along local +Z), bed-mould modillion subtype | a 1:1 pane in which the archivolt carries a moulded band and the bed-mould a modillion course; alternation count along the archivolt within 30 % of the photo's on the same band. |
| QA-07-5 | 03 | lighting | major | The colonnade is still a black frame: **28.0 %** of cam03 below lum 10 (test <= 20 %) and the outer lagoon-side row at **0.097** of the sunlit rotunda (test >= 0.15) at hue 70.8 — bounce only, no sky. LIGHT r14 measured the same box at 0.138 on its own frames and flagged it as an r15 item; on the merged master it is 0.097. | sky visibility inside the colonnade, `LIGHT_shade_fill` reach | frame below lum 10 **<= 20 %** and box 880 120 1200 600 at **>= 0.15** of the sunlit rotunda with hue 25-60. |
| QA-07-6 | 06 | environment + lighting | major | The far field is a milky gradient: **0** readable far-shore street lines on the composited frame against **5** on the un-composited twin, crop std 32.0 vs 50.6. The geometry has the structure; the mist deletes it. The ratio gate passes (0.631 >= 0.60), so the gate is measuring the wrong thing for this defect. | the r13/r14 mist density vs distance, `env_city.py` block contrast | **>= 3 far-shore lines on the COMPOSITED frame** (rows 0-110, >= 15 lum below the roofs) with the ratio held >= 0.60. |
| QA-07-7 | 01 | lighting | major | The shade level overshot while its colour was being fixed: hero shaded attic **134.0** against ref 118.8 and the 103.5-126.5 window (round 06: 114.7, the best colour match of the project). Shade / sunlit is now **0.70** against the photo's 0.63. | `LIGHT_shade_fill` energy (70 W/m2 Cycles), the diffuse boost | shaded attic 1110 225 1150 260 back inside **103.5-126.5** with hue 23.5-35.5 and sat <= 0.50 held. |
| QA-07-8 | 04 | lighting | minor | Eevee-Cycles soffit W gap **+0.202** (test <= 0.15; r06 +0.195), Cycles soffit W **0.238** vs ref 083's 0.381 — unchanged for three rounds, and Cycles is the engine that is wrong. | probe / screen-trace coverage of the west soffit | gap <= 0.15 **and** Cycles soffit W within 0.10 of 0.381. |
| QA-07-9 | 04 | materials | minor | The coffer rim over-corrected: Cycles rim sat **0.323**, 0.06 below the 0.38-0.50 window (ref 083 0.438) while the coffer field landed at 0.467. The saucer now reads slightly grey at the ribs. | the rim variant's albedo saturation | rim sat 0.38-0.50 with the coffer field held. |
| QA-07-10 | 01, 05 | environment | minor | The mid-ground trees do not mass where the photograph's do: ref 169 carries dark tree masses against the wings and behind the rotunda that the render has as low shrubs, which is most of the residual difference in the gate composite's two top panels. The north-wing band matches (0.97) because ENV r8 solved that band; the rest of the shoreline does not. | `ENV` cluster plan behind the rotunda and along the south wing | the hero's tree-mask area between x 0.55-0.75 and x 0.25-0.45 within 30 % of ref 169's on the aligned panel. |
| QA-07-11 | 02 | lighting | minor | cam02's shaded pier is now over-warm past the window on the low side: hue **7.0** at sat 0.242 (window 25-60; r05 41.6, r06 265.5). LIGHT r14 already carried this as a known over-correction. | the anti-sun / horizon tint exponents on cam02's facing | shade pier 600 110 660 200 hue **25-60** with the hero shade held. |
| QA-07-12 | 01 | architecture | minor | Two sub-courses inside the now-registered stack are still off: the entablature cornice is **1.33** of the photo's rows (20 vs 15) and the frieze **0.83** (20 vs 24) — the same imbalance ARCH r7 costed as option A (CORNICE_H 1.37 -> 1.79, frieze 0.81 -> 0.61 with an ornament refit). Deferred by decisions.md until QA scored the registered stack; it is now scored, and it is worth 0.5 of Proportion, not more. | `CORNICE_H` / `FRIEZE_H`, ornament's rinceau band | cornice and frieze both within 15 % of the photo's rows on `qa_stack_offset.py --y0 260 --y1 340`. |
| QA-03-16 | — | lead | open | 4K 768 spp timing, still never run. | — | one 3840x2160 frame at 128 spp fixed (adaptive off) with an outer wall-clock guard, before attempting 768. |

## Notes for the lead

1. **The answer to item 3.** The projection did not ship, so there is nothing to inspect for seams; the hero moved **+0.22
   without it**, on geometry (ARCH r6/r7), ornament (ORN r6/r7) and water colour (MAT r8). The precondition QA blocked on in
   round 06 is now met: the stack registers within 0.37 m course by course and the attic storey is 0.99 of the photograph's.
   **The projection pass is cleared to run.** Hero 3.44 < 3.6, so by the budget plan MAT r9 = the projection pass is the next
   round, and QA agrees with that ordering: the two open hero blockers (QA-07-1 lagoon, QA-07-2 stone chroma) are both colour
   problems that a projected photograph either solves outright (the stone) or is unaffected by (the water).
2. **This round did not trade rows.** For the first time since round 03 nothing that was passing broke, with two exceptions
   worth one line in the next brief each: the shade level overshot (QA-07-7, 114.7 -> 134.0) and the water's sky component
   got brighter and bluer while its stone component was fixed (QA-07-1). The hold-list discipline recommended in round 06
   worked; keep it, and add the hero's shaded-attic box and the lagoon-flank box to it.
3. **Two closed defects deserve a caveat.** QA-06-4's anisotropy closed partly because ARCH moved the box off the cornice
   (see (b)) — the streak maps did not ship; and QA-06-11's south wing closed against a test whose saturation half was
   mis-specified (the photo's own south wing is at sat 0.153, below the render's). Neither is a reason to reopen them, but
   neither is a materials win.
4. **cam02's station is on the wrong side of the building** (SSE against ref 062's NE). Not changed inside this gate
   (section (i)); the fitted, on-land station is (-79.8, 24.4, 1.55) -> (0, 0, 23.5) at ~40 mm. If cam02 is meant to be
   the ref-062 twin, re-station it at the START of round 08 and re-base its four shade boxes in the same commit.
5. **Item 5, for the record:** ref 169's camera stands **2.6 m** over the water (1.9-3.2 m for +-6 rows of horizon) against
   cam01's **2.90 m**. cam01 was not moved. The mirror deficit is 0.55 vs 0.88 of the direct stone — a shader number, not a
   station number.
