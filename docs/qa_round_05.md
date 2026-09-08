# QA round 05 — Phase 4 polish round 3 gate (2026-09-08)

Round 05 renders the master rebuilt after lighting r11, materials r6, environment r6 (+ follow-up) and the architecture mini-round
(rib material, ref 062 fit); lead build `renders/logs/lead_build_r5.log` (EXIT 0; 9175 objects; probes baked on the physical vault rig).
Machine quiet: no other Blender during any QA render; each render waited on a single blocking command.

## What was rendered and compared

| file | what |
|---|---|
| `renders/previews/qa/round05_0K_*.png` | Eevee 1280x720, 32 TAA, LOD1, `apply_preview_eevee`. Times **22.7 / 22.2 / 23.6 / 18.7 / 18.0 / 12.7 s** (round 04: 17.3 / 24.3 / 21.4 / 16.3 / 16.2 / 11.5 s; +1 to +5 s on cams 01, 03-06 with 439 more objects and the probe bake). Whole pass 120.6 s. |
| `round05_01_lagoon_hero_cycles.png` | Cycles 1920x1080, **128 spp adaptive, uncapped**, OIDN, GPU: **355.8 s** wall (round 04: 335.4 s; +6 %). |
| `round05_04_rotunda_ceiling_cycles.png` | Cycles 1280x720, 64 spp, uncapped: **219.1 s** (round 04: 210.9 s) — the interior-fill check. |
| `renders/qa_comparisons/round05_cam0K.png`, `round05_sheet.png` | render / canonical photo / 50 % blend per camera (cam01 vs `cam_01b_..._ref169.jpg`), contact sheet; `round05_cam01_cycles.png` is the Cycles hero on the same layout |
| `round05_cam01_aligned_vs_ref169.png` | W_a-aligned overlay on the raw ref 169 (the round 03/04 yardstick): scale **1.3108, dx -291.8, dy -124.6** (round 04: 1.3113 / -292.0 / -126.3), so every round-03/04 box is valid within 2 px |
| `round05_cam01_crops_vs_ref169.png` | 1:1 crop pairs (attic + entablature, capital + shaft, shore + waterline, near water) with boxes and numbers burnt in |
| **`renders/qa_comparisons/round05_gate.png`** | **the gate composite**: Cycles hero beside ref 169, six Eevee views, score deltas r04 -> r05 |

Commands: `blender -b --python scripts/qa_render_round.py -- --round 05 --eevee` (log `renders/logs/qa_r05_eevee.log`), `-- --round 05 --final
--samples 128 --res 1920 1080 --cams 01`, `-- --round 05 --final --samples 64 --res 1280 720 --cams 04`, `scripts/qa_inspect.py`,
`scripts/qa_compare.py`, `scripts/qa_silhouette.py align` (crop 690 40 1235 520 / ref-crop 749 127 1165 493), `scripts/qa_crops.py`,
`scripts/light_r11_measure.py` (lighting's tool on QA's boxes: hero, cam03, cam04), `scripts/mat_r6_measure.py cornice|waterline|coffer`
(materials' tool for the three prose tests), `scripts/qa_measure.py`, `scripts/qa_gate_sheet.py --round 05`. Nothing was written to master.blend.

## Score table (0-5; target >= 4 every row, hero average >= 4.5). Round 04 -> round 05.

| row | cam01 | cam02 | cam03 | cam04 | cam05 | cam06 |
|---|---|---|---|---|---|---|
| Silhouette match | 4 -> 4 | 3.5 -> 3.5 | 2.5 -> 2.5 | 3.5 -> 3.5 | 3.5 -> 3.5 | 4 -> 4 |
| Proportion | 4 -> 4 | 3.5 -> 3.5 | 3 -> 3 | 3.5 -> 3.5 | 3 -> 3 | 3.5 -> 3.5 |
| Ornament fidelity | 3.5 -> 3.5 | 3 -> 3 | 2.5 -> **2** | 3 -> 3 | 3 -> 3 | 2.5 -> 2.5 |
| Material realism | 3 -> 3 | 2.5 -> 2.5 | 1.5 -> **1** | 1.5 -> **2** | 2.5 -> 2.5 | 2 -> 2 |
| Edge wear | 1.5 -> **2** | 1 -> **1.5** | 0.5 -> 0.5 | 0.5 -> **1** | 1.5 -> 1.5 | 0.5 -> 0.5 |
| Lighting mood | 4 -> **3.5** | 3 -> 3 | 1.5 -> **1** | 2 -> 2 | 3.5 -> 3.5 | 2.5 -> **3** |
| Water reflection | 3.5 -> **3** | 2 -> **2.5** | n/a | n/a | 2.5 -> 2.5 | 2 -> 2 |
| Repetition visibility | 3 -> 3 | 2.5 -> 2.5 | 2 -> 2 | 2.5 -> 2.5 | 2.5 -> 2.5 | 2 -> **2.5** |
| Scale cues | 3 -> **3.5** | 3 -> 3 | 2.5 -> **2** | 3 -> 3 | 2.5 -> **3** | 2.5 -> 2.5 |
| **average (delta)** | **3.28 (+0.00)** | **2.78 (+0.11)** | **1.75 (-0.25)** | **2.56 (+0.12)** | **2.78 (+0.06)** | **2.50 (+0.11)** |

### Trend across rounds 02 -> 05 (averages)

| cam | r02 | r03 | r04 | r05 | trend | rows stuck (3 rounds without gain) |
|---|---|---|---|---|---|---|
| 01 hero | 2.94 | 3.28 | 3.28 | 3.28 | **stuck** at 3.28 for three rounds; every gain (scale cues, edge wear) is paid for by a loss (lighting, water) | Material realism 3, Repetition 3, Ornament 3.5, Silhouette / Proportion 4 (at ceiling for the current geometry) |
| 02 NE 3/4 | 2.11 | 2.33 | 2.67 | 2.78 | improving, slowly (+0.11); most of the gain was the round-04 re-station | Material 2.5, Repetition 2.5, Silhouette 3.5 |
| 03 colonnade | 1.94 | 2.13 | 2.00 | 1.75 | **declining** since r03: the shade got darker every round (23 -> 7 -> 5.5) | Silhouette 2.5, Proportion 3, Edge wear 0.5, Material <= 1.5 |
| 04 ceiling | 2.31 | 2.13 | 2.44 | 2.56 | flat-to-slow; Lighting mood at 2 for three rounds (2x over, then 0.6x, now 0.5x) | Lighting 2, Ornament 3, Silhouette / Proportion 3.5, Repetition 2.5 |
| 05 S lawn | 2.11 | 2.67 | 2.72 | 2.78 | flat since r03 (+0.06 / round) | Material 2.5, Ornament 3, Proportion 3, Lighting 3.5 |
| 06 aerial | 2.17 | 2.17 | 2.39 | 2.50 | slowly improving (+0.11) | Material 2, Edge wear 0.5, Ornament 2.5, Water 2 |

Verdict: **gate not passed.** Round 05 closed real defects by number (shoreline, columns, cam05 apex, north wing, Eevee vault no longer
black, decisions log, attic std) and the hero average still did not move: **3.28 for the third round**. What the hero gained in scale
cues (2-4 m shore mounds, a willow, birds) and edge wear (variegation) it lost in lighting mood (sunlit attic dropped out of its luminance
window: 166.5 vs 190; shaded stone sat 0.82; the frame-left wing still 0.63) and water (the building's reflection is greyer than in round 04:
sat 0.106). Two owners' claimed numbers do not reproduce on the merged master: lighting's Cycles coffer 0.387 measures **0.21** (down from
0.26) and Eevee 0.325 measures 0.16; materials' near-water hue 204 measures 208.9. cam03 declined for the third round.

Explicit "clean CAD / game asset" rejects this round, each with its crop:
- **Hero stone is no longer clean CAD; it is now a dirt decal** (`round05_cam01_crops_vs_ref169.png` pane 1, box 880 200 1040 300): an
  isotropic 0.3-3 m blotch laid over everything at the same density, no vertical streak direction under the cornice or the string course,
  the attic relief gone soft under it, and the whole attic darker and more saturated than the photo (lum 139 vs 170, sat 0.72 vs 0.59 in
  the pane). Number: streak anisotropy (std of column means / std of row means, attic box 900 222 1020 256) **0.64** in the render vs
  **4.07** in the photo — the photo's weathering runs *down* the wall, the render's is a blotch.
- **cam04 vault in both engines** (`round05_cam04.png` panel 1; Cycles `round05_04_rotunda_ceiling_cycles.png`): coffer floors are black holes
  with lit rims (darkest quarter / lightest quarter **0.121** vs ref 083 **0.265** by the same tool on the same canonical), so the vault
  reads as an ambient-occlusion decal on a brown saucer, not a sky-lit concrete ceiling.
- **cam03** (`round05_cam03.png`): 80 % of the frame is black (near shaft 5.5 / 255); the x8-gain check shows the fluted shaft and the path
  are there — the shade is crushed, nothing occludes the lens.
- **Near water** (crops pane 4, box 1100 960 1500 1060): a flat blue-grey plane with uniform fine ripple noise and no warm reflected colour
  in the ripples (hue 209 vs 192, R-B -33 vs -26); the photo's ripples carry the stone's orange.

## What works (keep it)

- Silhouette: apex within **0.63 %** of frame height of ref 169 on the raw-ref yardstick (round 04: 0.78 %); W_a 544 px, rise / W_a 0.226 vs photo 0.239.
- Columns (QA-04-5 / QA-03-2 column half) **closed**: mask lum **95.9** vs ref 95.8 (ratio 1.00; test <= 120), hue 27.8 (test 20-29). Sat 0.758 vs 0.588 is noted, not tested.
- Flutes hold: by one counter on both images (rows 360-400, troughs >= 10 % of run mean) the front shafts show 8 (841-880) and 9 (1040-1072) cycles vs the aligned photo's 7 / 9 on its front shafts.
- Attic texture std (QA-04-3 first half) **0.66** of the photo's (test >= 0.60; materials claimed 0.598) — the *amount* of variegation is now right; its *direction* is wrong (see the reject above).
- Shoreline under the rotunda (QA-04-4) **closed**: 2-4 m mounded shrubs with size spread, a willow crown at frame-left, birds on the shrubs; shore band (700-1200 x 620-720) pale-stone pixels **36.5 % -> 7.1 %**, green 3.5 -> 16.3 %; the 14 rows above the per-column waterline (row 784) are stone in 3.2 % of columns (podium base hidden **96.8 %**; env's sight-line 78 % was at cam05).
- Frame-right (NORTH) wing band 1360 480 1860 600: **137.5 = 0.94** of ref (was 91.6 = 0.63). Labels corrected this round: frame-left is the SOUTH wing (camera at +Y looking -Y puts -X = north on the right).
- Eevee vault no longer black (QA-04-1 Eevee half): coffer / own-sky **0.035 -> 0.162**, soffits W 0.362 / E 0.304; the Eevee-Cycles coffer gap is **0.05** (test <= 0.15).
- cam05 apex **27 px = 3.75 %** below the top edge (test >= 3 %; QA-04-10 closed by the lead's target z 21.5); 0 % foliage over the rotunda band; the Greek-key band is visible over the shore shrubs.
- cam06 dome cap / far-shore band **2.07:1** (test >= 1.5; was 1.21); horizon crop has 14 quantized colours at >= 1 % share (roof variety is real).
- cam02's bottom strip has reeds and a ripple edge now (bottom 12 %: mean 55, std 43; QA-04-14 closed); ref 062's station is documented by architecture (D 91.7 m / 42.4 mm: the photo was taken from farther with a longer lens; QA-04-11 closed, no proportion change).
- Saved preset intact: GPU / 768 adaptive (min 64, threshold 0.01) / OIDN / AgX High Contrast / exposure -2.833; Eevee taa 8 / 16, raytracing off, light_threshold logged in decisions.md (QA-04-12 closed); open 0.72 s; LOD1 11.01 M tris; 65 materials, 0 placeholders.

## Measurements

### (a) Chroma at delivery resolution (Cycles hero 1920x1080, `light_r11_measure.py --hero`, QA round-03 boxes, ref 169 aligned)

| region | box | round 04 | **round 05** | ref 169 | verdict |
|---|---|---|---|---|---|
| sunlit attic panel | 900 222 1020 256 | lum 180.4 hue 38.9 sat 0.554 R-B 122 | lum **166.5** hue 39.8 sat **0.643** R-B 134 | 189.6 / 40.3 / 0.588 / 136 | **lum 0.88 (window 178-201) fail — regression**; hue / R-B pass; sat +0.06 over |
| attic string course | 880 214 1040 222 | 166.4 / 39.7 / 0.568 / 115 | 157.3 / 40.1 / 0.622 / 121 | 181.9 / 39.3 / 0.580 / 129 | lum 0.86 |
| entablature | 900 262 1020 296 | 161.7 / 39.4 / 0.634 / 128 | 130.0 / **40.6** / **0.836** / 146 | 146.4 / 34.0 / 0.604 / 115 | lum 0.89; hue +6.6, sat +0.23: too yellow and too saturated |
| dome cap | 920 95 1000 120 | 196.3 / 37.4 / 0.349 / 78 | 192.3 / 37.9 / 0.371 / 81 | 215.6 / 42.7 / 0.288 / 67 | lum 0.89, hue -5 |
| shaded attic | 1110 225 1150 260 | 112.2 / 43.1 / 0.736 | 94.6 / **43.1** / **0.819** | 115.0 / 29.5 / 0.425 | lum 0.82; hue +13.6, sat +0.39 — **worse**; no sky in the shade |
| columns (mask hue<32 sat>0.30, x 680-1240 y 280-470) | mask | 122.0 / 31.2 / 0.753 | **95.9** / 27.8 / 0.758 | 95.8 / 24.5 / 0.588 | **pass** (ratio 1.00; hue in 20-29) |
| water reflection column | 900 760 1020 840 | 145.9 / 42.7 / 0.146 | **122.7** / 50.7 / **0.106** | 168.9 / 33.7 / 0.339 | lum 0.73, sat -0.23 — **regression** (the sheen was dropped on the lead's follow-up) |
| near water, sky-reflecting | 1150 1000 1450 1050 | sat 0.272 hue 208.7 | sat 0.280 hue **208.9** | 0.249-0.270 / 189.9-192.1 | sat pass, hue fail (185-200); materials' 204 does not reproduce |
| lagoon flank | 100 900 400 960 | 171.1 | 174.1 | 155.2 | 1.12 ok |
| sky top / sky low-left | lighting's boxes | 167.9 / 154.8 -> 0.922 | 167.9 / 154.8 -> **0.922** | ref 1.17 | fail (1.05-1.29), unchanged: no haze band |

Shade-vs-sunlit on the hero (the golden-hour anchor used in (d)): shaded attic / sunlit attic **94.6 / 166.5 = 0.57** vs ref 169 **0.607** — the *level* of open shade on the hero is right; its colour is not.

### (b) Texture / weathering at 1:1 (luminance std-dev over matched boxes; test: render >= 60 % of the photo's)

| box | round 04 | **round 05** | ref 169 | ratio |
|---|---|---|---|---|
| attic panel 900 222 1020 256 | 23.1 | **28.8** | 43.8 | **0.66 pass** (was 0.55) |
| entablature 900 262 1020 296 | 35.3 | 33.5 | 64.6 | **0.52 fail** (unchanged; handed to architecture as cornice / dentil depth) |
| stone crop 760 250 1230 460 | 57.1 | 52.5 | 63.0 | 0.83 |

Direction of the variegation (new this round; std of column means / std of row means over the box — vertical streaks make the column
profile vary and the row profile flat):

| box | round 04 | **round 05** | ref 169 | reading |
|---|---|---|---|---|
| attic field 900 222 1020 256 | 0.77 | **0.64** | **4.07** | photo: streaks down the wall (col std 20.0, row std 4.9); render: blotch (10.2 / 16.1) |
| entablature 900 262 1020 296 | 0.39 (row std 28.3) | 0.62 (row std **20.9**) | 0.24 (row std **53.6**) | photo: hard horizontal shadow bands under the cornice and the dentils; render: half as deep, and less than round 04 |

Materials' own r6 tools on the round-05 hero: under-ledge run-off (`mat_r6_measure cornice`): attic columns >= 15 lum darker below the
cornice **10.0 %** (round 04 6.7 %; **the photo itself scores 19.2 %** by the same tool, so QA-04-3's ">= 30 %" threshold was set above
the photo and is re-based to ">= the photo's 19 %"), entablature frieze 14.2 % (= photo 14.2 %, pass). Waterline (`mat_r6_measure waterline`):
columns with a >= 20 lum drop above the water **39.3 %** with 84 edge columns (round 04: 38.9 % / 54 columns) — the tool prints PASS on its
own criterion but the number did not move, and in crops pane 3 the band is a thin dark line at the water, not a 0.3-0.6 m damp zone.

### (c) Interior fills, cam04 vs ref 083 (boxes exactly as round 03 (e); ref soffit/sky 0.405, coffer/sky 0.437)

| ratio | ref 083 | r04 Eevee | r04 Cycles | **r05 Eevee** | **r05 Cycles 64 spp** | lighting r11 claim (branch) |
|---|---|---|---|---|---|---|
| soffit / own sky (W / E) | 0.405 | 0.40 / 0.14 | 0.29 / 0.52 | **0.362 / 0.304** (sky 109.7; soffits 39.7 / 33.4) | **0.141 / 0.370** (sky 109.8; soffits 15.5 / 40.6) | 0.419 (E) |
| coffer field / own sky | 0.437 | **0.035** | 0.26 | **0.162** (coffer 17.8) | **0.211** (coffer 23.2) | 0.325 Eevee / **0.387** Cycles |
| Eevee - Cycles gap (test <= 0.15) | | | | coffer **0.05 pass**; soffit E 0.07 pass; soffit W **0.22 fail** | | |

Robust coffer statistic (`mat_r6_measure coffer`, same tool on both): darkest quarter / lightest quarter **0.121** (dark 14.2, light 117.6) vs
ref 083 **0.265** (28.5 / 107.6); coffer-field std 42.7 vs ref 31.2 — *more* contrast than the photo, because the floors are black and the
rims are lit. The 0.40-0.60 box: Cycles mean 23.2 std 14.4 (std/mean 0.62) vs ref 77.7 / 36.3 (0.47). The QA-04-1 Eevee half is closed
(bake on the physical rig works: 0.035 -> 0.162, gap 0.05), the QA-04-7 Cycles half regressed (0.26 -> 0.21 against a claimed 0.387).
The claim was measured on lighting's branch before materials r6 (in-coffer gradient, `MAT_plaster_ceiling_rib`) merged; the merged master
has darker coffer floors than either branch alone — an integration regression, owner lighting + materials, to be measured on the lead's build.

### (d) cam03 — the shade test, re-based (QA-04-2)

Decision: ref 128 is a midday photo (lighting is right), and there is no golden-hour photo from the colonnade walk, so the cam03 shade test
is **re-stated as a shade-vs-sunlit ratio measured inside the cam03 frame itself**, anchored on ref 169's golden-hour shade: shaded attic /
sunlit attic = 115.0 / 189.6 = **0.607**. A colonnade soffit is darker than an open shaded wall, so the window is **0.30-0.70** for near shaft
(0 150 420 720) / sunlit rotunda (560 0 880 320, the lit far rotunda in the same frame), plus hue 25-42 and sat <= 0.55 for the shade
(ref 169's shade: hue 29.5, sat 0.425). The absolute ref 128 number (69.7) is retired.

| | round 03 | round 04 | **round 05** | window |
|---|---|---|---|---|
| near shaft lum / hue / sat | 23.1 / 55.4 / 0.518 | 7.3 / 58.3 / 0.618 | **5.5 / 58.2 / 0.615** | hue 25-42, sat <= 0.55 |
| sunlit rotunda lum (560 0 880 320) | 93.1 | 96.5 | 87.8 | |
| **near shaft / sunlit** | 0.248 | 0.076 | **0.063** | **0.30-0.70 — fail by 5x** |
| ground (420 560 900 720) / sunlit | 0.646 | 0.220 | 0.197 | |

The x8-gain check (`round05_03_colonnade_walk.png` boosted) shows the fluted shaft and the walk are there and uniformly crushed; the shade's
hue 58 / sat 0.62 is bounced stone light with no sky component — the same signature as the hero's shaded attic (43.1 / 0.82). This is not
albedo: ref 169's shade is 0.61 of its sunlit stone at sat 0.43; the render's is 0.06 at sat 0.62. Third consecutive decline.

### (e) Wings on the hero (Cycles; ref 169 raw mapping; labels corrected: frame-left = SOUTH, frame-right = NORTH)

| band | round 04 | **round 05** | ref 169 | ratio |
|---|---|---|---|---|
| **south** wing, frame-left 60 480 560 600 | 90.2 | **86.0** | 109.5 (raw) / 137.2 (env aligned panel) | **0.79 / 0.63 — fail** (unchanged) |
| **north** wing, frame-right 1360 480 1860 600 | 91.6 | **137.5** | 146.5 | **0.94 pass** (was 0.63) |

### (f) cam05 vs ref 063; cam06 vs ref 105; cam02

cam05: apex row **27 px = 3.75 % below the top** (test >= 3 %: pass; QA-04-10 closed); foliage over the rotunda column band 0 %; top crop
(300 0 980 200) lum 165.8 (r04 168.2; ref 183). At 110 m the stone reads as one flat yellow (material 2.5 held).
cam06: dome cap (auto-found pale blob 527-708 x 114-210, lum 198.7) vs far-shore band (0 40 1280 110) 96.1 -> **2.07:1** (test >= 1.5: pass);
horizon crop (0 0 1280 220) lum 100.6 hue 37.5 sat 0.471; 14 quantized colours >= 1 % share, 31 >= 0.3 %. Visually still one beige plane with
no road network readable — the numbers pass, the read is 2.5.
cam02: bottom-12 % strip mean 55.4, std 43.2, row-profile std 14.4 (reeds and a ripple edge present; QA-04-14 closed); the frame-left
colonnade remains a dark unlit mass (Lighting mood held at 3).

## Viewport performance (pass/fail, not scored)

- Open **0.72 s** headless (budget 60 s) — pass. 9175 objects, 65 materials, 0 placeholder materials, file 154.6 MB.
- LOD1 **11.01 M tris** (round 04: 10.95 M) — pass.
- Eevee 1280x720 previews **12.7-23.6 s per camera** at LOD1 (round 04: 11.5-24.3 s) — pass; the 32-TAA QA preset, not the saved 8/16.
- Cycles hero 1920x1080 128 spp adaptive uncapped: **355.8 s** (round 04: 335.4 s); cam04 64 spp 1280x720: 219.1 s (210.9 s).

## Deliverables present (pass/fail)

- **Cycles final config: pass, as saved** — GPU, 768 spp adaptive (threshold 0.01, min 64), OIDN, time limit 0, `AgX - High Contrast`, exposure -2.833.
- **`CAM_flythrough_path`: pass** — `CAM_flythrough`, `CAM_flythrough_path` (curve), `CAM_flythrough_target`.
- **Eevee viewport config: pass** — taa 8 / 16, raytracing off, light_threshold 0.01, 2 baked irradiance volumes; logged in decisions.md (QA-04-12 closed).
- **Eevee navigability of the ceiling: pass with a note** — the vault is dim (coffer 17.8 / 255, 0.16 of its sky) but readable; no longer black.
- Phase-5 items (4K hero, low-res Eevee animation): not due; the 768-spp 4K timing (QA-03-16) is in the last section.

## Status of every round-04 defect

| defect | owner | status | the number |
|---|---|---|---|
| QA-04-1 Eevee vault black | lighting | **half closed** | Eevee coffer / sky 0.035 -> **0.162**, soffits 0.362 / 0.304; Eevee-Cycles gap coffer 0.05 and soffit E 0.07 (pass), soffit W **0.22** (fail); Cycles coffer 0.211 (window 0.35-0.55, fail). Lighting's 0.325 / 0.419 do not reproduce on master. |
| QA-04-2 shade collapsed / yellow-green | lighting | **open, blocker, worse** | re-based test (d): near shaft / sunlit rotunda **0.063** (window 0.30-0.70; r04 0.076; r03 0.248), hue 58.2 (25-42), sat 0.615 (<= 0.55); hero shaded attic hue 43.1 / sat **0.819** (29.5 +- 6 / <= 0.50); hero shade *level* 0.57 vs 0.607 passes. |
| QA-04-3 stone clean CAD at 1:1 | materials (+ architecture) | **half closed, re-stated** | attic std **0.66** (pass); entablature 0.52 (fail, ARCH cornice / dentil depth: row-profile std 20.9 vs photo 53.6); cornice run-off 10.0 % vs photo's 19.2 % (threshold re-based, fail); waterline 39.3 % (unchanged); streak anisotropy **0.64 vs 4.07** — new blocker QA-05-2 (the blotch reads as a decal). |
| QA-04-4 hero shoreline bare quay | environment | **closed** | shore band pale-stone 36.5 -> 7.1 %, green 3.5 -> 16.3 %; base hidden 96.8 % of columns; 2-4 m mounds, willow at frame-left, birds; scale cues 3 -> 3.5. Residual: band lum 71.7 vs photo 114 (QA-05-10). |
| QA-04-5 columns 1.27x / yellow | lighting + materials | **closed** | mask lum **95.9** vs 95.8 (ratio 1.00), hue 27.8 (20-29). |
| QA-04-6 wings dark | lighting + environment | **half closed** | north (frame-right) **0.94** pass; south (frame-left) 0.79 raw / 0.63 aligned fail (86.0 vs 109.5 / 137.2). Labels fixed. |
| QA-04-7 Cycles coffers 0.26 + no rib / panel split | lighting + materials | **open, regressed** | Cycles coffer / sky **0.211** (was 0.26; claimed 0.387); dark / light quarter 0.121 vs ref 0.265; rib plates now carry `MAT_plaster_ceiling_rib` and read as lighter bars (tone split present). |
| QA-04-8 water hue / grey reflection | environment + materials | **open, reflection regressed** | near-water hue **208.9** (185-200 fail; claimed 204); sat 0.280 pass; reflection column sat **0.106** / lum 122.7 = 0.73 of ref (was 0.146 / 0.86). |
| QA-04-9 sky haze band | lighting | **open** | 0.922 vs 1.17 (1.05-1.29), third round unchanged. |
| QA-04-10 cam05 apex | lead | **closed** | 27 px = 3.75 % below the top (>= 3 %). |
| QA-04-11 ref 062 station | architecture + lead | **closed** | documented fit D 91.7 m / 42.4 mm (decisions.md): the photo was taken from farther with a longer lens; no proportion change. |
| QA-04-12 saved Eevee state | lead | **closed** | decisions.md 2026-09-08 entry: RT off measured (0.218 -> 0.218), light_threshold 0.01. |
| QA-04-13 cam06 far field | environment + lighting | **numbers closed, read open** | dome / far shore **2.07:1** (>= 1.5); 14 colours >= 1 %; no roads readable, one beige plane (minor QA-05-8). |
| QA-04-14 cam02 foreground | environment | **closed** | bottom 12 %: reeds + ripple edge, std 43.2 (was flat). |

Carried from round 03: QA-03-16 (4K 768 spp) — see the last section.

## Defect list — round 05

| id | cam | owner | severity | description (measurable) | where | acceptance test |
|---|---|---|---|---|---|---|
| QA-05-1 | 03, 01 | lighting | **blocker** | Shade crushed for the third round: cam03 near shaft **5.5** = **0.063** of the sunlit rotunda in the same frame (golden-hour anchor ref 169: 0.607; window 0.30-0.70); ground 0.197; shade hue 58 / sat 0.62 = bounced stone light only. On the hero the shaded attic is 43.1 / **0.82** vs 29.5 / 0.43: the shade has no blue-sky component in either frame. The hero's shade *level* (0.57) is fine, so the fix is the shade's sky share (diffuse sky boost / `SHADE_FILL` at real energy), not exposure. | `SKY_DIFFUSE_BOOST` split, `SHADE_FILL` (shipped at 0 W), `EXPOSURE_BIAS` | cam03 near shaft / sunlit rotunda 0.30-0.70 with hue 25-42 and sat <= 0.55; hero box 1110 225 1150 260 hue 29.5 +- 6, sat <= 0.50, lum within 15 % of 115. |
| QA-05-2 | 01, 02, 05 | materials | **blocker** | Hero stone is a dark isotropic dirt decal (crops pane 1): streak anisotropy **0.64** vs photo **4.07** in the attic box; attic lum **166.5** (window 178-201, was 180.4), sat 0.643 (ref 0.588); entablature hue 40.6 / sat **0.836** (ref 34.0 / 0.604); shaded attic sat 0.82; under-cornice run-off 10.0 % of columns vs the photo's 19.2 %; relief softened under the blotch. The macro maps deliver the std number and the wrong signal: rain runs down, it does not blotch. | `MAT_concrete_*` macro grunge (isotropic 0.3-3 m tiles), streak masks, base value (Macro darkened mean ~8 %, not 5 %) | attic box 900 222 1020 256: lum 178-201, sat 0.53-0.62, std ratio >= 0.60 kept, anisotropy >= 2.0; entablature sat <= 0.70, hue 32-38; cornice run-off >= 19 % of columns; a 1:1 pane in which the darkening under the cornice is a set of vertical runs, not blotches. |
| QA-05-3 | 04 | lighting + materials | **blocker** | Cycles coffer / sky **0.211** (window 0.35-0.55; r04 0.26; lighting's branch 0.387), floors black: dark / light quarter **0.121** vs ref 0.265; Eevee 0.162. Reads as an AO decal on a brown saucer. The regression is the merge of materials' in-coffer gradient onto lighting's re-tuned fill; neither owner measured the merged master. | `VAULT_FILL`, `FILL`, in-coffer gradient in `MAT_concrete_*` coffer variant, `MAT_plaster_ceiling_rib` value | on the lead's master: Cycles coffer / sky 0.35-0.55, dark / light quarter >= 0.20, Eevee within 0.15 on coffer and both soffits (soffit W now 0.22 off). |
| QA-05-4 | 01 | materials + environment | major | Water: near-water hue **208.9** (185-200; unchanged three rounds; owner's 204 not reproduced), reflection column sat **0.106** / lum 0.73 of ref (regressed from 0.146 / 0.86 after the sheen was dropped); crops pane 4: flat blue-grey plane, uniform fine ripple, no warm colour in the ripples. | `MAT_water_lagoon` murk tint / upwelling, reflection roughness, `MAT_lagoon_bed` | crop 1150 1000 1450 1050 hue 185-200 on the QA hero; reflection box 900 760 1020 840 sat >= 0.28, lum within 10 % of 168.9. |
| QA-05-5 | 01 | lighting + environment | major | SOUTH wing (frame-left, 60 480 560 600) **86.0** = 0.79 raw / 0.63 aligned of ref; the north wing passed at 0.94 after its foliage thinning, so the same treatment (foliage share, shade sky share) is owed on the south side. | south-wing shading trees, sky diffuse | band within 25 % of ref by both panels (>= 82 raw-mapped 109.5 x 0.75 and >= 103 aligned). |
| QA-05-6 | 01 | architecture | major | Entablature has no hard cornice / dentil shadow bands: row-profile std **20.9** vs photo **53.6** (box 900 262 1020 296); texture std 0.52 of the photo's (test 0.60, unchanged three rounds); crops pane 1 shows a dentil row with no shadow under the corona. Carried from QA-04-3 second half. | `arch_params` cornice projection, corona depth, dentil depth | row-profile std >= 40 and texture std ratio >= 0.60 on the box, under the same light. |
| QA-05-7 | 01 | lighting | minor | Sky haze band: sky_left / sky_top **0.922** vs 1.17, third round unchanged (QA-03-12 / QA-04-9). | sky `aerosol_density`, camera-sky gradient | 1.05-1.29. |
| QA-05-8 | 06 | environment | minor | Far field passes its numbers (2.07:1, 14 colours) but reads as one beige plane: no road grid, no block structure at 1280 px. | `env_city.py` street grid / block gaps, mist gradient | >= 3 readable dark street lines crossing the horizon crop (0 0 1280 220) at >= 15 lum below the roofs. |
| QA-05-9 | 04 | lighting | minor | Eevee soffit W / sky 0.362 vs Cycles 0.141: gap **0.22** (test 0.15); the two engines disagree on the west soffit only. | probe bake coverage of the west soffit, `LIGHTPROBE_rotunda` extent | gap <= 0.15 on both soffits. |
| QA-05-10 | 01 | environment + lighting | minor | Shore band (700 600 1200 740) lum **71.7** vs photo 114 (0.63): the new shrubs sit in shadow and read black-green; the photo's are sunlit soft green. | shrub albedo / translucency, sun reach at the shore | band lum within 25 % of 114 with hue 40-60. |
| QA-05-11 | 03 | environment | minor | With the shade fixed, cam03 will need its ground: the walk is bare (ground / sunlit 0.197, std 15.7); ref 128 has paving joints and planting edges. | `ENV_ground_colonnade_walk`, edge planting | ground std >= 12 at a level within 30 % of the shade window. |
| QA-05-12 | 05 | materials | minor | At 110 m the stone is one flat yellow (Material 2.5 for three rounds): the macro maps are tuned for 60-90 m and vanish at cam05. | macro map amplitude vs distance | attic band std on cam05 >= 60 % of ref 063's on the same band (to be boxed next round). |

## 4K 768-spp hero timing (QA-03-16)

Run after the round-05 commit (6c109ef) with no other Blender on the GPU: `scripts/qa_4k_probe.py -- --samples 768 --modes on
--time-limit 5400 --out renders/previews/qa/round05_4k` (log `renders/logs/qa_round05_4k.log`), started 08:20:06. At the machine-stop
checkpoint (09:53:39, ~92 min wall) the process was still sampling / in its tail with **no frame written** (Cycles' 5400 s cap had
elapsed, so the remaining time is the denoise tail or the cap was not honoured by adaptive sampling); the lead killed it at the checkpoint.
**Result: killed at checkpoint; 4K timing needs re-running.** QA-03-16 stays open: 4K 16 spp completes in 177 s (round 04), 1080p 128 spp
in 356 s; a 4K 768-spp frame has now failed to appear inside 90 min in three attempts (lighting x2, QA x1). Recommended next attempt: 4K at
**128 spp fixed, adaptive off, time_limit 0**, with `--time-limit` replaced by an outer wall-clock guard, to get the first finished 4K frame
and its wall time before trying 768.

## Notes for the lead

1. **Three rounds at 3.28 is a structural result, not noise.** The hero's silhouette, proportion and ornament rows are at their ceiling for
   the current geometry (4 / 4 / 3.5); the rows that must move are Material realism (3 for three rounds), Edge wear (2), Water (3) and
   Lighting mood (3.5, slipping). Each polish round has fixed the *number* an owner was given and produced a new artefact in the same row:
   r4 chroma -> shade crushed; r5 variegation std -> isotropic blotch and a darker attic; r5 coffer gradient -> black floors. The stone now
   has the right amount of variance in the wrong direction. Procedural grunge is not converging on the photo's signature (vertical streaks,
   hard course shadows, course-to-course tone changes); a photo-projected albedo for the hero-facing attic / entablature / drum band (ref 169
   and ref 085 are already aligned to the render frame) would carry all three signatures at once. Recommendation: change approach for the
   concrete on the hero-facing faces; keep the procedural for the rest.
2. **Claimed numbers must be measured on the lead's master, not the owner's branch.** Two of this round's headline claims (Cycles coffer
   0.387, near-water hue 204) do not reproduce; the coffer one regressed because two owners' fixes multiply. Suggest: the acceptance
   measurement is the lead's post-build run of the owner's own tool, attached to the merge.
3. cam03 has declined for three rounds while the hero was tuned; QA-05-1 is a shade *colour* problem (no sky share), not exposure — the
   hero's shade level already matches ref 169. Lighting should measure cam03 and the hero's shaded box together before touching the hero again.
4. The cam03 test is re-based (section (d)): shade-vs-sunlit inside the cam03 frame, window 0.30-0.70, anchored on ref 169. The lead may
   prefer a golden-hour colonnade photo if one exists in the index; none is catalogued as canonical.
