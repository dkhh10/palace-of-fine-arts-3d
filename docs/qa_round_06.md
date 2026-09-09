# QA round 06 — Phase 4 polish round 4 gate (2026-09-09)

Scored master: the file on disk at 13:36 (`renders/logs/lead_build_r6.log`, EXIT 0), **9709 objects**, LOD1 **11.11 M tris**,
67 materials, 0 placeholders, 154.4 MB, opens in **0.72 s**; probes baked on the diffuse world
(`LIGHTPROBE_rotunda` 20x20x14, `LIGHTPROBE_colonnade` 48x20x6, bake 4.2 s). Merged this round: ARCH r4, LIGHT r12 + r13,
MAT r7, ENV r7 + r8 + the paving rebuild. No other Blender ran during any QA render; every render was one blocking
`scripts/blender_run.sh` call.

## What was rendered and compared

| file | what |
|---|---|
| `renders/previews/qa/round06_0K_*.png` | Eevee 1280x720, 32 TAA, LOD1, `apply_preview_eevee`. Times **44.5 / 43.8 / 49.7 / 26.7 / 31.4 / 22.7 s** (round 05: 22.7 / 22.2 / 23.6 / 18.7 / 18.0 / 12.7 s). Whole pass **218.6 s** vs 120.6 s — **+81 %**, the cost of LIGHT r13's Eevee-only `LIGHT_shade_fill` / vault rig. Log `renders/logs/qa_r06_eevee.log`. |
| `round06_01_lagoon_hero_cycles.png` | Cycles 1920x1080, 128 spp adaptive uncapped, OIDN, GPU: **381.4 s** (round 05: 355.8 s; +7 %). Log `qa_r06_cycles_hero.log`. |
| `round06_04_rotunda_ceiling_cycles.png` | Cycles 1280x720, 64 spp: **219.9 s** (round 05: 219.1 s). Log `qa_r06_cycles_cam04.log`. |
| `renders/qa_comparisons/round06_cam0K.png`, `round06_sheet.png` | render / canonical photo / 50 % blend per camera (cam01 vs `cam_01b_..._ref169.jpg`); `round06_cam01_cycles.png` is the Cycles hero on the same layout |
| `round06_cam01_aligned_vs_ref169.png` | the round-03/04/05 yardstick: W_a-aligned overlay on the raw ref 169. Scale **1.3036, dx -286.4, dy -121.7** (round 05: 1.3108 / -291.8 / -124.6) — every round-03/05 box is valid within 5 px, and the cached reference row reproduces on it (attic 188.2 vs 189.6, entablature 147.6 vs 146.4, shaded 116.3 vs 115.0, columns 95.4 vs 95.8, near water 106.4 / 191.1 vs 107.7 / 192.1; only `dome_cap` drifts, 236.5 vs 215.6, because that box straddles the cap edge at the new scale). |
| `round06_cam01_crops_vs_ref169.png` | 1:1 crop pairs (attic + entablature, capital + shaft, shore + waterline, near water) with boxes and numbers burnt in |
| `round06_stack_offset.png` | brief item 7: the hero-facing stack course by course, render beside ref 169 at x8 vertical zoom with every detected course edge labelled |
| **`renders/qa_comparisons/round06_gate.png`** | **the gate composite**: Cycles hero beside ref 169, six Eevee views, score deltas r05 -> r06, trend table r02 -> r06 |

Commands: `scripts/blender_run.sh 900 -- --background --python scripts/qa_render_round.py -- --round 06 --eevee`;
`... 1500 -- ... --round 06 --final --samples 128 --res 1920 1080 --cams 01`; `... 900 -- ... --samples 64 --res 1280 720 --cams 04`;
`... 300 -- ... scripts/qa_inspect.py`. Analysis (no Blender): `qa_silhouette.py align` (crop 690 40 1235 520 / ref-crop 749 127 1165 493),
`qa_compare.py`, `qa_crops.py`, `qa_measure.py`, **`qa_stack_offset.py` (new this round)**, `qa_gate_sheet.py --round 06`,
and the owners' own tools on the merged master: `light_r10_measure.py`, `light_r11_measure.py --cam04 --wings --gap`,
`light_r12_measure.measure_wings`, `light_r13_measure.py --cam06`, `mat_r6_measure.py cornice|waterline|coffer`,
`mat_r7_measure.py hero|cam05`. Nothing was written to master.blend.

## Score table (0-5; target >= 4 every row, hero average >= 4.5). Round 05 -> round 06.

| row | 01 hero | 02 NE 3/4 | 03 colonnade | 04 ceiling | 05 S lawn | 06 aerial |
|---|---|---|---|---|---|---|
| Silhouette match | 4 -> 4 | 3.5 -> 3.5 | 2.5 -> 2.5 | 3.5 -> 3.5 | 3.5 -> 3.5 | 4 -> 4 |
| Proportion | 4 -> **3.5** | 3.5 -> 3.5 | 3 -> 3 | 3.5 -> 3.5 | 3 -> 3 | 3.5 -> 3.5 |
| Ornament fidelity | 3.5 -> 3.5 | 3 -> 3 | 2 -> **2.5** | 3 -> 3 | 3 -> 3 | 2.5 -> 2.5 |
| Material realism | 3 -> 3 | 2.5 -> 2.5 | 1 -> **1.5** | 2 -> **2.5** | 2.5 -> **3** | 2 -> **1.5** |
| Edge wear | 2 -> **2.5** | 1.5 -> **2** | 0.5 -> **1** | 1 -> 1 | 1.5 -> **2** | 0.5 -> 0.5 |
| Lighting mood | 3.5 -> **4** | 3 -> 3 | 1 -> **2** | 2 -> **3** | 3.5 -> 3.5 | 3 -> **2** |
| Water reflection | 3 -> **2** | 2.5 -> **1.5** | n/a | n/a | 2.5 -> **1.5** | 2 -> **1.5** |
| Repetition visibility | 3 -> 3 | 2.5 -> 2.5 | 2 -> 2 | 2.5 -> 2.5 | 2.5 -> 2.5 | 2.5 -> 2.5 |
| Scale cues | 3.5 -> 3.5 | 3 -> 3 | 2 -> **2.5** | 3 -> 3 | 3 -> 3 | 2.5 -> 2.5 |
| **average (delta)** | **3.22 (-0.06)** | **2.72 (-0.06)** | **2.12 (+0.38)** | **2.75 (+0.19)** | **2.78 (+0.00)** | **2.28 (-0.22)** |

**Hero delta, stated explicitly (brief item 2): 3.28 -> 3.22, -0.06.** One row was re-scored on new evidence rather than on a
change: hero **Proportion 4 -> 3.5**, because this is the first round in which the stack was measured course by course
(section (g)) and the render's attic storey is **0.70** and its capital **0.65** of ref 169's under the same alignment that
puts the silhouette within 0.47 % of frame height. The geometry did not move this round (ARCH r4 reported silhouette change
0.000 %). **Holding Proportion at 4 the hero is 3.28 — flat for a fourth round.** Either reading, the hero did not gain.

### Trend across rounds 02 -> 06 (averages)

| cam | r02 | r03 | r04 | r05 | **r06** | reading |
|---|---|---|---|---|---|---|
| 01 hero | 2.94 | 3.28 | 3.28 | 3.28 | **3.22** | **stuck for four rounds.** Lighting +0.5 and Edge wear +0.5 paid for by Water -1.0 and the Proportion re-score |
| 02 NE 3/4 | 2.11 | 2.33 | 2.67 | 2.78 | **2.72** | first decline; the shade opened (+) but the lagoon went blue-violet (-1.0) |
| 03 colonnade | 1.94 | 2.13 | 2.00 | 1.75 | **2.12** | **first gain in three rounds** (+0.38): the walk, the bases and the shafts are readable |
| 04 ceiling | 2.31 | 2.13 | 2.44 | 2.56 | **2.75** | best round; Lighting 2 -> 3 on the coffer fix |
| 05 S lawn | 2.11 | 2.67 | 2.72 | 2.78 | **2.78** | flat: stone +0.5 and edge wear +0.5 cancelled by water -1.0 |
| 06 aerial | 2.17 | 2.17 | 2.39 | 2.50 | **2.28** | **regression**: the diffuse sky tint flooded the frame blue |

Verdict: **gate not passed.** Round 06 closed or nearly closed five of the round-05 blockers by number (hero shade colour,
Cycles coffers, cornice/dentil shadow, cam03 shade level, cam05 stone) and lost the same amount again in water and in the
aerial. The pattern of rounds 4 and 5 repeats a third time: **the number an owner is given is met and a new artefact appears
in a row nobody was measuring.** This round the artefact is the diffuse sky tint (bake world tint **(1.0, 0.65, 17.0)**,
strength 0.800 x boost 2.50): tuned on the hero's shaded attic it is exact there (hue 30.7 vs ref 29.5) and it turns every
weakly-sunlit surface elsewhere blue-violet — cam06 roofs hue **36.6 -> 253.4**, near ground **39.3 -> 268.8**, trees
**35.8 -> 239.9**; cam03 paving hue **222-225** at sat 0.56-0.76; cam02 and cam05 lagoon hue **39.4 -> 265.5** and sat
**0.31 -> 0.12**.

Explicit "clean CAD / game asset" rejects this round, each with its crop:
- **The hero's capitals and the whole ornamented band above them** (`round06_cam01_crops_vs_ref169.png` pane 2, box 660 280 900 480):
  the render's Corinthian capitals are smooth blobs **24 px** tall against the photo's **37 px** of separated acanthus, volutes and
  fleuron; the frieze and bed-mould between them are blank walls where the photo carries modillions, rosettes and egg-and-dart;
  the arch has no moulded archivolt. At 1:1 the whole zone reads as a massing model with a texture on it.
- **cam06** (`round06_cam06.png`): a lavender relief map. Roofs, lawns, trees and water all sit at hue 240-269 with sat 0.13-0.22
  against ref 105's near-neutral warm city (hue 2.7 / sat 0.05) and warm foreground (51.2 / 0.207); the lagoon is a flat
  near-white plane. Nothing in the frame is the colour of anything.
- **The lagoon at cam05** (`round06_cam05.png`, band 0.35-0.75 w x 0.86-0.99 h): render lum 120.3 hue 5.9 sat **0.123** vs the
  photo's 93.4 / 64.9 / **0.306** — 1.29x too bright, 0.4x the chroma and 59 deg off hue. It is a mirror with a sheen, not water.
- **The hero's attic weathering is still not rain** (crops pane 1): streak anisotropy **0.41** vs the photo's **4.07**
  (col sd 10.1 / row sd 25.0 in the render, 20.1 / 4.9 in the photo). The render's dark is organised in *rows* — it is the
  cornice's shadow, not run-off. Third round with this number below 1.

## What works (keep it)

- **Hero shade colour is solved.** Shaded attic (1110 225 1150 260) **114.7 / hue 30.7 / sat 0.373** vs ref 169
  **115.0 / 29.5 / 0.425** — lum within 0.3 %, hue within 1.2 deg, sat 0.05 under. Round 05 was 94.6 / 43.1 / **0.819**.
  Shade-vs-sunlit on the hero **0.636** vs ref **0.607**.
- **Cycles coffers.** coffer / own sky **0.451** (ref 083 0.437; window 0.35-0.55) from 0.211; Eevee 0.346; Eevee-Cycles
  coffer gap **0.105** (test 0.15). Robust statistic dark quarter / light quarter **0.234** Cycles, **0.232** Eevee vs ref **0.265**
  (round 05: 0.121) — the floors are no longer black.
- **The cornice exists.** Entablature box 900 262 1020 296: texture std **52.0 = 0.81** of the photo's 64.4 (test 0.60; round 05 0.52),
  row-profile std **36.5** vs 20.9 (photo 54.0). Crops pane 1 shows a real corona shadow and a dentil row.
- **Waterline band closed.** Columns with a >= 20 lum drop above the water **44.9 %** on 245 edge columns, against the same
  tool's **38.2 %** on ref 169 (round 05: 39.3 % / 84). The render is now above the photograph.
- **cam03 is a picture again.** Frame below lum 10: **71.1 % -> 46.1 %**; below 20: 84.5 % -> 72.7 %. The walk has paving
  slabs with joints, the column bases and the fluting read, the far rotunda is exposed (QA-05-11 closed by ENV r7).
- **cam05 stone at 110 m (QA-05-12 closed).** Band 300 150 980 260 std **50.5** vs ref 063's **54.7 = 0.92** (test 0.60);
  anisotropy 1.43 vs 1.39. The "one flat yellow" of three rounds is gone.
- **Sunlit attic luminance back in window**: **180.4** (window 178-201; round 05 166.5). Columns hue **24.0** (ref 24.5),
  sat **0.573** (ref 0.588) — the best column match of the project; mask lum 108.5 = 1.13 of ref (round 05 1.00).
- Silhouette: apex within **0.47 %** of frame height of ref 169 (round 05 0.63 %); rise / W_a 0.229 vs 0.239; W_a 541 px.
- cam05 apex **28 px = 3.89 %** below the top edge (test >= 3 %); cam06 dome cap / far-shore band **2.15 : 1** (test >= 1.5).
- Saved deliverable state intact: GPU / 768 adaptive (min 64, threshold 0.01) / OIDN / time limit 0 / `AgX - High Contrast` /
  exposure -2.8331; Eevee taa 8 / 16, raytracing off; `CAM_flythrough` + `_path` + `_target`; 2 light probes; 0 placeholder materials.

## Measurements

### (a) Chroma at delivery resolution (Cycles hero 1920x1080, QA round-03 boxes, ref 169 through the round-06 aligned panel)

| region | box | round 05 | **round 06** | ref 169 | verdict |
|---|---|---|---|---|---|
| sunlit attic panel | 900 222 1020 256 | 166.5 / 39.8 / 0.643 / 134 | **180.4** / 36.3 / **0.473** / **102.7** | 188.2 / 40.5 / 0.581 / 133.0 | lum **pass** (178-201); sat 0.06 **under** the window (0.53-0.62); R-B 30 short |
| attic string course | 880 214 1040 222 | 157.3 / 40.1 / 0.622 | 175.6 / 35.7 / 0.436 | 185.2 / 39.2 / 0.585 | lum 0.95; sat low |
| entablature | 900 262 1020 296 | 130.0 / 40.6 / 0.836 | **125.5** / 37.8 / **0.707** | 147.6 / 33.8 / 0.584 | lum 0.85; sat still 0.12 over (test <= 0.70, misses by 0.007) |
| dome cap | 920 95 1000 120 | 192.3 / 37.9 / 0.371 | 206.6 / 33.1 / 0.216 | 236.5 / 45.7 / 0.257 | lum 0.87, hue 12.6 cool |
| shaded attic | 1110 225 1150 260 | 94.6 / 43.1 / 0.819 | **114.7 / 30.7 / 0.373** | 116.3 / 30.2 / 0.444 | **pass on all three** |
| columns (mask hue<32 sat>0.30, 680 280 1240 470) | mask | 95.9 / 27.8 / 0.758 | 108.5 / **24.0** / **0.573** | 95.4 / 24.5 / 0.588 | hue + sat **pass**; lum ratio 1.13 (was 1.00) |
| water reflection column | 900 760 1020 840 | 122.7 / 50.7 / 0.106 | **103.0 / 87.0 / 0.043** / R-B **+2.5** | 166.1 / 33.7 / 0.358 / **+69.0** | **worst of five rounds** |
| ripples | 1100 960 1500 1060 | — | 114.9 / 215.4 / 0.267 / **-36.9** | 105.7 / 184.6 / 0.166 / **-18.4** | too blue by 31 deg |
| near water, sky-reflecting | 1150 1000 1450 1050 | 0.280 / 208.9 | 0.303 / **213.8** | 0.261 / 191.1 | sat pass, hue fail (185-200), 5 deg worse |
| lagoon flank | 100 900 400 960 | 174.1 | 156.6 / 211.2 | 153.4 / 200.4 | lum 1.02 ok, hue 11 blue |
| sky top / sky low-left | lighting's boxes | 154.8 / 167.9 -> 0.922 | 154.8 / 167.9 -> **0.922** | aligned panel **0.921** | **closed as measured-equal** (decisions.md 2026-09-09) |
| shore band | 700 600 1200 740 | 71.7 | **91.6** / 40.6 / 0.529 | 115.3 / 40.9 / 0.632 | 0.79 (test +-25 % **pass**); 24 lum short |

### (b) Texture / weathering at 1:1 and its direction

| box | round 05 | **round 06** | ref 169 | ratio / reading |
|---|---|---|---|---|
| attic std 900 222 1020 256 | 28.8 | **32.6** | 44.8 | **0.73 pass** (test 0.60) |
| entablature std 900 262 1020 296 | 33.5 | **52.0** | 64.4 | **0.81 pass** (was 0.52 — QA-05-6's texture half closed) |
| attic **anisotropy** 900 222 1020 256 | 0.64 | **0.41** | **4.07** | **fail, worse**; col sd 10.1 / row sd 25.0 vs photo 20.1 / 4.9 |
| attic anisotropy, MAT r7's box 900 224 1020 248 (brief item 8) | — | **0.76** | **4.35** | narrowing the box removes the cornice rows and doubles the render's number, but it is still **5.7x short** and the std ratio falls to **0.55** (below the 0.60 the wider box passes). **QA keeps 900 222 1020 256 as the primary box** and reports MAT's as secondary. |
| entablature anisotropy | 0.62 | 0.49 | 0.22 | render's row std 36.5 vs photo 54.0 -> **0.68** (test >= 40 row std: **fail by 3.5**) |

Prose tests on the merged master: under-ledge run-off (`mat_r6_measure cornice`) attic **11.7 %** of columns >= 15 lum below
the field (round 05 10.0 %) against the photo's **22.5 %** on the same box — fail; entablature frieze **22.5 %** vs the
photo's 11.7 % — pass, now above the photograph. Waterline (`mat_r6_measure waterline`) **44.9 %** on 245 edge columns vs the
photo's 38.2 % on 102 — **closed**.

### (c) Interior fills, cam04 vs ref 083 (round-03 boxes)

| ratio | ref 083 | r05 Eevee | r05 Cycles | **r06 Eevee** | **r06 Cycles 64 spp** |
|---|---|---|---|---|---|
| soffit / own sky (W / E) | 0.405 | 0.362 / 0.304 | 0.141 / 0.370 | **0.432 / 0.402** | **0.237 / 0.471** |
| coffer field / own sky | 0.437 | 0.162 | 0.211 | **0.346** | **0.451 pass** |
| dark quarter / light quarter | 0.265 | — | 0.121 | **0.232** | **0.234 pass** (test >= 0.20) |
| Eevee - Cycles gap (test <= 0.15) | | | | coffer **-0.105 pass**; soffit E -0.068 pass; **soffit W +0.195 fail** (round 05 +0.22) |

Colour, not level: the render's coffer field sits at sat **0.914** (Cycles) / **0.966** (Eevee) and the rim at 0.782 / 0.922
against ref 083's **0.427** on both. The vault is now lit correctly and is twice as saturated as the concrete it depicts.

### (d) cam03 — the shade test, re-based twice (QA-05-1; brief item 4)

The round-05 window stands: shaded / sunlit **0.30-0.70**, anchored on ref 169's 115.0 / 189.6 = 0.607, plus hue 25-42 and
sat <= 0.55 for the shade. Lighting r12 proved the round-05 near-shaft box is occluded from the sky and from the anti-sun
hemisphere, so QA re-based the *box* (decisions.md 2026-09-09). **Both boxes are reported once, here, and the new one is the
test from now on.**

| box | what it is | lum | hue | sat | / sunlit rotunda (560 0 880 320, lum **88.1**) |
|---|---|---|---|---|---|
| **150 150 420 720** (old) | near shaft, sky-occluded | 13.3 | 197.7 | 0.202 | **0.151** (round 05 0.063, round 04 0.076) — retired |
| **480 150 560 600** (new, the test) | the near shaft's frame-right flank, the one shaft face in the frame with an open view of the sky through the colonnade gap | **33.8** | **45.2** | **0.737** | **0.384 — inside the 0.30-0.70 window** |
| 880 120 1200 600 | the outer (lagoon-side) colonnade row that decisions.md names | 5.8 | 83.3 | 0.460 | **0.066** |
| 420 560 900 720 | the walk in front of the camera | 41.7 | **222.6** | 0.558 | 0.473 |

Reading: the shade **level** now passes on a sky-visible face (0.384) and the shade **colour** still fails in two opposite
directions in the same frame — sky-facing surfaces are blue-violet (walk hue 222.6, old box 197.7; window 25-42) and
sky-occluded surfaces are still bounce-only and black (outer row 0.066 at hue 83.3). 46.1 % of the frame is below lum 10.
The chosen box's own sat **0.737** fails the <= 0.55 half.

### (e) Wings on the hero (Cycles; labels: frame-left = SOUTH, frame-right = NORTH; brief item 5)

| band | box | render r05 | **render r06** | ref RAW (native ref-169 coords) | ref ALIGNED panel | ratio raw / aligned |
|---|---|---|---|---|---|---|
| **SOUTH**, frame-left | 60 480 560 600 | 86.0 | **94.2** (hue 32.0, sat 0.186) | 82.9 | 112.1 | **1.14 / 0.84** |
| **NORTH**, frame-right | 1360 480 1860 600 | 137.5 | **140.1** (hue 40.7, sat 0.430) | 148.3 | 146.8 | **0.94 / 0.95** |

QA-05-5's two-panel acceptance was ">= 82 raw AND >= 103 aligned": **raw passes (94.2), aligned fails (94.2 < 103)** — half
closed. The north wing holds after ENV r8's cluster re-solve (0.94-0.95, and ENV's own number 133.1 / 145.9 reproduces).
Note for the record: round 05's quoted "raw" reference of 109.5 for the south band does not reproduce — ref 169 is
1920x1192 and the same box on it reads **82.9**, on a 1920x1080 resize **71.2**. The aligned panel (112.1 / 146.8) is the
only mapping where render and reference share pixels, and is what QA will quote from here on.

### (f) cam02 / cam05 / cam06

cam02: attic 116.9 -> **131.3**, hue 43.2 -> **38.1**, sat 0.664 -> **0.400**; columns 76.0 -> 94.6, hue 37.7 -> 35.1,
sat 0.836 -> 0.675 (the shade opened, all in the right direction). Water 61.8 / hue **39.4** / sat 0.558 ->
64.3 / hue **265.5** / sat **0.178**. Bottom-12 % strip mean 55.0 std 51.8 (reeds hold).
cam05: attic band 152.9 / 38.9 / 0.453 (ref 063 118.4 / 33.7 / 0.292), std ratio 0.92; apex 3.89 % below the top;
water band lum 120.3 / hue 5.9 / sat 0.123 vs the photo's 93.4 / 64.9 / 0.306.
cam06: horizon crop (rows 0-220) mean **122.3** std **38.0** (round 05 100.6 / 33.8 — LIGHT r13's mist landed);
far-field street lines **2** (test >= 3, QA-05-8 still open); dome / far shore 2.15 : 1. But roofs / ground / trees at
hue **253.4 / 268.8 / 239.9**, sat 0.19 / 0.13 / 0.22, against round 05's 36.6 / 39.3 / 35.8 and ref 105's 2.7 / 51.2.

### (g) The hero-facing stack, course by course (brief item 7 — the number the lead asked for)

Method: `scripts/qa_stack_offset.py` on the aligned overlay (panel 0 = render, panel 1 = ref 169 warped into the render's
pixel grid, so one row means the same thing in both). Row-mean luminance over the band **x 880-1040**, smoothed 3 rows;
a course is a local extremum of dL/dy. Rows are exact; metres are quoted at the brief's **13.42 px/m** *and* at the scale
QA measures from the model's own geometry (crown 38.30 m to panel-frame bottom 32.55 m = 5.75 m over 70 rows = **12.17 px/m**).
Positive = the render's course sits **higher** in frame than the photograph's.

| course | render row | ref 169 row | delta rows | **delta m @ 13.42** | delta m @ 12.17 |
|---|---|---|---|---|---|
| attic crown cornice, top lit edge | 168 | 169 | -1 | **+0.07** | +0.08 |
| attic crown corona, shadow under it | 178 (weak, -1.7) | 182 (**-49.1**) | -4 | **+0.30** | +0.33 |
| attic panel frame top | 181 | 198 | -17 | **+1.27** | +1.40 |
| attic panel frame bottom | 238 | 269 | -31 | **+2.31** | +2.55 |
| entablature cornice corona (shadow onset) | 254 | 281 | -27 | **+2.01** | +2.22 |
| dentil band bottom = frieze top | 280 | 298 | -18 | **+1.34** | +1.48 |
| frieze bottom = architrave top | 302 | 320 | -18 | **+1.34** | +1.48 |
| capital top (abacus), read off `round06_stack_offset.png` +-3 rows | 306 | 321 | -15 | **+1.12** | +1.23 |

**The offset is not a constant.** It runs from **+0.07 m at the attic crown to +2.31 m at the attic panel frame bottom** and
sits at +1.1 to +2.0 m through the entablature. Equivalently, under the same alignment that puts the silhouette within
0.47 % of frame height:

| storey | render rows | ref rows | render / ref |
|---|---|---|---|
| attic (crown top -> panel frame bottom) | 168-238 = **70** | 169-269 = **100** | **0.70** |
| entablature cornice (corona -> frieze top) | 254-280 = 26 | 281-298 = 17 | 1.53 |
| frieze | 280-302 = 22 | 298-320 = 22 | **1.00** |
| capital (abacus top -> shaft top) | 306-330 = **24** | 321-358 = **37** | **0.65** |

So the two earlier claims are both true and both partial: architecture's "cornice 1.04 m high" is measured here as
**+2.01 m** at the corona (they measured a different edge of the same course), and materials' "attic panel frame ~0.65 m
high" is **+1.27 m** at the frame top and **+2.31 m** at the frame bottom, i.e. the frame is not shifted, it is **short**.
QA also confirms materials' third claim: the attic box 900 222 1020 256 catches the render's cornice — the render's
attic panel frame bottom is at row 238, so rows 238-256 of that box (18 of 34 rows, **53 %**) are cornice, not panel.

**Consequence for the photo-projection pass (this is the decision the brief asked for): the precondition is NOT met.**
A projected photo registers to the render only by a rigid 2-D transform; here a single scale-and-shift cannot fit, because
the attic storey is 0.70 of the photo's while the frieze is 1.00 and the cornice 1.53. Projecting ref 169 onto the current
geometry would put the photo's relief figures across the render's cornice and the photo's dentils across the render's frieze.
Architecture has to close the attic storey (and the capital) first, or the projection has to be per-course (a separate
UV/window mapping per band, which is not the ~120-line job materials scoped).

### (h) The reflection test needs a warmth term (brief item 8)

Every sheen weight MAT r7 swept that reached sat >= 0.25 did so at hue ~213 — blue water passes a saturation-only test.
Measured on this round's hero, the reflection box **900 760 1020 840** is render 103.0 / hue 87.0 / sat 0.043 / **R-B +2.5**
against the aligned ref's 166.1 / 33.7 / 0.358 / **R-B +69.0**. **New test, from round 07 on:**

> `water_refl` 900 760 1020 840 on the Cycles hero: **R-B >= +35** (half the photo's +69) **and** hue in **25-45** **and**
> lum within 25 % of 166 (124-208). Saturation is dropped as a criterion — it cannot tell reflected stone from blue sky.

The box is on the rotunda's reflection (the render's std there is 58.8, i.e. bright streaks on dark water); it is not
"100 % water" as MAT r7 reported — the failure is that the streaks carry no stone chroma, not that the box is empty.

## Viewport performance (pass/fail, not scored)

- Open **0.72 s** headless (budget 60 s) — pass. 9709 objects, 67 materials, 0 placeholders, file 154.4 MB.
- LOD1 **11.11 M tris** (round 05 11.01 M) — pass.
- Eevee 1280x720 previews **22.7-49.7 s** per camera at LOD1, whole pass 218.6 s vs round 05's 120.6 s — **pass but
  regressed 81 %**. The delivery brief wants an Eevee-navigable file; a 2x cost on the preview rig is worth a look before
  Phase 5's flythrough test (owner lighting: `LIGHT_shade_fill` + the EEVEE vault rig).
- Cycles hero 1920x1080 128 spp adaptive: **381.4 s** (355.8 s); cam04 64 spp 1280x720: **219.9 s** (219.1 s).

## Deliverables present (pass/fail)

- Cycles final config **pass, as saved**: GPU, 768 spp adaptive (threshold 0.01, min 64), OIDN, time limit 0,
  `AgX - High Contrast`, exposure -2.8331.
- `CAM_flythrough`, `CAM_flythrough_path`, `CAM_flythrough_target` **pass**; 2 light probes **pass**.
- Eevee viewport config **pass**: taa 8 / 16, raytracing off; ceiling readable (Eevee coffer / sky 0.346).
- 4K 768-spp timing (QA-03-16): **not run this round** by instruction (Phase 5 item, lead schedules it). Still open.

## Status of every round-05 defect (measured on the lead's master, brief item 1)

| defect | owner | status | the number |
|---|---|---|---|
| QA-05-1 shade crushed / no sky share | lighting | **level closed, colour open** | cam03 sky-visible shaft (480 150 560 600) / sunlit **0.384** (window 0.30-0.70); old box 0.151 (was 0.063); hero shaded attic **114.7 / 30.7 / 0.373** vs ref 115.0 / 29.5 / 0.425 — **all three pass**. Open: the shade's colour away from the hero (walk hue 222.6, cam06 240-269), the chosen shaft box's sat 0.737, and 46.1 % of cam03 below lum 10. |
| QA-05-2 hero stone a dark isotropic decal | materials | **half closed** | attic lum **180.4** (window 178-201) **pass**; std ratio **0.73** pass; entablature std 0.81 pass. Fail: sat **0.473** (0.53-0.62), R-B 102.7 (>= 120), **anisotropy 0.41** (>= 2.0; 0.76 on MAT's narrower box), entablature sat 0.707 (<= 0.70 by 0.007), cornice run-off 11.7 % vs the photo's 22.5 %. |
| QA-05-3 Cycles coffers 0.211 / black floors | lighting + materials | **closed** | Cycles coffer / sky **0.451** (0.35-0.55), dark / light quarter **0.234** (>= 0.20), Eevee gap on the coffer **0.105** (<= 0.15). New residual: coffer sat 0.914 vs ref 0.427. |
| QA-05-4 water hue / grey reflection | materials + environment | **open, regressed** | reflection sat **0.043** (was 0.106), R-B **+2.5** vs +69.0, lum 0.62 of ref; near-water hue **213.8** (185-200; was 208.9); ripples R-B -36.9 vs -18.4. And now cam02 / cam05 / cam06 lagoons at hue 265 / 6 / 332 with sat 0.12-0.18. |
| QA-05-5 south wing dark | lighting + environment | **half closed** | 86.0 -> **94.2**: raw panel **pass** (>= 82), aligned panel **fail** (94.2 < 103, ratio 0.84). North holds 0.94-0.95. |
| QA-05-6 entablature has no cornice shadow | architecture | **half closed** | texture std **0.81** of the photo's (test 0.60) **pass**; row-profile std **36.5** vs the photo's 54.0 (test >= 40) **fail by 3.5**. The remaining gap is now a *stack* problem, not a profile one: see (g). |
| QA-05-7 sky haze band | lighting | **closed** | 0.922 render vs 0.921 on the aligned ref — measured-equal (decisions.md). |
| QA-05-8 cam06 no readable streets | environment | **open** | 2 far-field lines (test >= 3); crop std 33.8 -> 38.0. Overtaken by the blue flood (QA-06-2). |
| QA-05-9 Eevee soffit W gap | lighting | **open** | gap **+0.195** (test 0.15; round 05 0.22). Cycles soffit W 0.237 vs ref 0.38. |
| QA-05-10 shore band dark | environment + lighting | **closed on the window** | **91.6** vs ref 115.3 = 0.79 (test +-25 %); hue 40.6 vs 40.9. Sat 0.529 vs 0.632. |
| QA-05-11 cam03 walk bare | environment | **closed** | paving slabs with joints and edge planting; frame below lum 20: 84.5 % -> 72.7 %; ground / sunlit 0.197 -> 0.473. |
| QA-05-12 cam05 flat stone at 110 m | materials | **closed** | band std **50.5 = 0.92** of ref 063's 54.7 (test 0.60). |
| QA-03-16 4K 768 spp timing | lead | **open, not run** | excluded from this round by the brief. |

## Defect list — round 06

| id | cam | owner | severity | description (measurable) | where | acceptance test |
|---|---|---|---|---|---|---|
| QA-06-1 | 01 | architecture | **blocker** | The hero-facing stack does not register course by course: offsets run **+0.07 m** (attic crown) to **+2.31 m** (attic panel frame bottom), +2.01 m at the cornice corona, +1.34 m at the frieze. The attic storey is **0.70** and the capital **0.65** of ref 169's under the alignment that puts the silhouette within 0.47 %. This blocks the photo-projection pass (a rigid projection cannot fit) and is the reason QA's attic box is 53 % cornice. | `arch_params` ATTIC_H / the attic sub-course split (base moulding 0.9, panel frame 0.45, top cornice 0.8), CAPITAL_H 2.6, ENTABLATURE_Z0 | on `qa_stack_offset.py --x0 880 --x1 1040` against ref 169: every one of the eight courses within **+-8 rows (0.6 m)** and the attic storey within 10 % of the photo's 100 rows. |
| QA-06-2 | 06, 03, 02, 05 | lighting | **blocker** | The diffuse sky tint **(1.0, 0.65, 17.0)** at strength 0.800 x boost 2.50 is tuned on one box and floods everything else blue-violet: cam06 roofs hue **36.6 -> 253.4**, ground **39.3 -> 268.8**, trees **35.8 -> 239.9** (ref 105: 2.7 / 51.2); cam03 walk hue **222.6** at sat 0.558; cam02 water hue **39.4 -> 265.5**. The aerial reads as a lavender relief map. | `SKY_DIFFUSE_BOOST` tint / boost, the anti-sun and horizon terms, the r13 mist colour | cam06 roofs, near ground and trees all with **hue outside 200-300** and within 15 deg of ref 105's warm neutrals; cam03 walk hue **25-60**; hero shaded attic must stay 29.5 +- 6 / sat <= 0.50 while they move. |
| QA-06-3 | 01, 02, 05, 06 | materials | **blocker** | Water fails in two opposite ways at once. Hero: reflection R-B **+2.5** vs the photo's **+69.0** (sat 0.043, lum 0.62 of ref) — the streaks carry no stone colour; near water hue **213.8** (185-200), ripples R-B -36.9 vs -18.4. At distance: cam05 band lum **120.3** / hue **5.9** / sat **0.123** vs 93.4 / 64.9 / **0.306**, cam06 lagoon a near-white plane. The specular sheen saturates at grazing angles and there is no green murk term. | `MAT_water_lagoon` murk tint / absorption depth, IOR + roughness vs incidence, `MAT_lagoon_bed` | hero 900 760 1020 840: **R-B >= +35, hue 25-45, lum 124-208** (section (h)); near water hue 185-200; cam05 band (0.35-0.75 w, 0.86-0.99 h) sat **>= 0.24** and hue **40-80** with lum within 25 % of 93.4. |
| QA-06-4 | 01, 02, 05 | materials | major | Attic weathering still runs the wrong way: streak anisotropy **0.41** (0.76 on the narrow box) vs the photo's **4.07**; col sd 10.1 / row sd 25.0 against 20.1 / 4.9. Under-cornice run-off **11.7 %** of columns vs the photo's **22.5 %**. Procedural macro grunge has now missed this in three rounds; authored per-panel streak maps were proposed by MAT r7 and not shipped. | `MAT_concrete_*` streak masks, per-panel authored maps | attic 900 222 1020 256: **anisotropy >= 2.0** with std ratio >= 0.60 held, and cornice run-off >= 19 %. |
| QA-06-5 | 01 | materials | major | Sunlit stone lost its chroma while gaining its luminance: attic sat **0.473** (window 0.53-0.62; ref 0.581) and R-B **102.7** (>= 120; ref 133.0); string course sat 0.436 vs 0.585. The hero now reads slightly washed / grey-yellow where round 05 read too orange. LIGHT r13 handed materials **+0.025 sat / +6.9 R-B**; the measured shortfall is **+0.11 sat / +30 R-B**. | `MAT_concrete_ochre` base albedo saturation | attic sat 0.53-0.62 and R-B >= 120 **with** the shaded attic held at hue 29.5 +- 6 / sat <= 0.50. |
| QA-06-6 | 01, 02 | ornament | major | At 1:1 the capitals and the band above them are a massing model (crops pane 2): capitals **24 px** tall vs the photo's 37 with no separated acanthus or volutes; bed-mould, frieze and archivolt blank where the photo has modillions, rosettes and egg-and-dart. Ornament fidelity has been 3.5 on the hero for four rounds. | `ORN` capital LOD0/LOD1 at hero distance, frieze rosette band, archivolt moulding | a 1:1 pane in which the capital's two acanthus rows and four volutes are separately readable, and the bed-mould carries modillions; capital height within 15 % of the photo's after QA-06-1. |
| QA-06-7 | 03 | lighting | major | The colonnade is still half black: **46.1 %** of the cam03 frame below lum 10, and the outer (lagoon-side) row measures **0.066** of the sunlit rotunda at hue 83.3 — bounce only, no sky. The re-based test passes only on the one shaft face with an open sky view (0.384). | sky visibility / fill inside the colonnade, `SHADE_FILL` | frame below lum 10 **<= 20 %**, and the outer row box 880 120 1200 600 at **>= 0.15** of the sunlit rotunda with hue 25-60. |
| QA-06-8 | 04 | materials | major | The vault is lit right and coloured wrong: coffer field sat **0.914** (Cycles) / 0.966 (Eevee) and rim 0.782 / 0.922 against ref 083's **0.427** on both boxes. A saturated orange saucer. | `MAT_plaster_ceiling*` / the coffer variant albedo saturation | coffer and rim sat **0.38-0.50** with the coffer / sky ratio held at 0.35-0.55. |
| QA-06-9 | 01 | architecture | major | Entablature row-profile std **36.5** vs the photo's **54.0** (test >= 40): the corona shadow exists now but is ~2/3 as deep, and the dentils sit in a single flat row where the photo has a modillion course over a dentil course. Carried from QA-05-6 / QA-04-3. | cornice corona projection, the second bed-mould course | row std >= 40 on 900 262 1020 296 under the same light. |
| QA-06-10 | 04 | lighting | minor | Eevee-Cycles soffit W gap **+0.195** (test 0.15; round 05 0.22); Cycles soffit W 0.237 vs ref 0.38 — the two engines still disagree on the west soffit only, and Cycles is the one that is wrong. | probe / screen-trace coverage of the west soffit | gap <= 0.15 **and** Cycles soffit W within 0.10 of 0.405. |
| QA-06-11 | 01 | lighting + environment | minor | South wing **94.2**: raw panel passes (>= 82), aligned panel fails (103 needed, ratio 0.84). Sat 0.186 vs the north wing's 0.430 — the south band is not just dark, it is desaturated. | south-wing sun reach / sky share | >= 103 on the aligned panel with sat >= 0.30. |
| QA-06-12 | 06 | environment | minor | Far field still has **2** readable street lines (test >= 3), unchanged; the r13 mist raised the crop std 33.8 -> 38.0 without adding structure. | `env_city.py` street grid / block gaps | >= 3 lines at >= 15 lum below the roofs in rows 0-110. |
| QA-06-13 | all | lighting | minor | The Eevee preview pass costs **218.6 s** for six cameras, up from 120.6 s (+81 %), on the same LOD1 geometry; per camera 22.7-49.7 s vs 12.7-23.6 s. Phase 5's Eevee flythrough test inherits this. | `LIGHT_shade_fill`, the EEVEE vault rig, shadow rays | six-camera Eevee pass back under 150 s with the shade term held (hero Eevee shaded attic within 6 deg / 0.10 sat of Cycles). |

## Notes for the lead

1. **Answer to the question you actually asked (item 7): do not start the photo-projection pass yet.** The stack offsets are
   not a rigid shift (+0.07 m to +2.31 m across eight courses; attic storey 0.70 of the photo's, cornice 1.53, frieze 1.00,
   capital 0.65). A single projected photo would land the reference's figures on the render's cornice. Either architecture
   closes the attic storey and the capital first (QA-06-1), or the projection is authored per-course, which is a much bigger
   job than the ~120 lines MAT r7 scoped. My recommendation: **one architecture round on the stack, then the projection**,
   because the same fix also closes QA-06-9 and half of QA-06-6 and makes QA's attic box mean what it says.
2. **The four-round pattern is now a rule, not a coincidence.** r4 chroma -> shade crushed; r5 variegation -> isotropic
   blotch; r6 shade colour -> the whole world blue-violet away from the box it was tuned on. Every round an owner meets a
   number on the box they were given and breaks a row nobody measured. Suggestion: **every lighting or materials brief from
   round 07 carries a hold-list** — the boxes on the other five cameras that must not move by more than a stated amount —
   and the merge measurement runs all six cameras, not the hero.
3. **The good news is real.** The hero's shade is the first exact colour match of the project (30.7 / 0.373 / 114.7 vs
   29.5 / 0.425 / 115.0), the coffers are solved, cam03 gained for the first time in three rounds, and cam05's stone finally
   holds at 110 m. Four of five round-05 blockers moved. The hero average did not, because water lost exactly what lighting
   and materials won.
4. **Water is now one defect across four cameras, not two.** Hero reflection, near water, cam02, cam05 and cam06 all fail the
   same way: the specular sheen dominates and there is no absorption/murk that survives distance. It is worth one dedicated
   materials round measured on **all four** water frames, with the new R-B test in (h).
5. The 4K 768-spp timing (QA-03-16) is still the only untested delivery item. Recommend the round-05 note's plan: 4K at
   **128 spp fixed, adaptive off, time_limit 0**, with an outer wall-clock guard, before attempting 768.
