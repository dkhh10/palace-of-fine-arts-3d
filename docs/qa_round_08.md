# QA round 08 — Phase 4 polish round 6 gate (2026-09-09). The first round after the photo-projection pass.

Scored master: the file on disk at 23:01 (`renders/logs/lead_build_r8.log`), **9679 objects**, LOD1 **11.38 M tris**,
72 materials, 0 placeholders, 161.0 MB, opens in **0.75 s**. Merged this round: the new stations (cam01 down 0.30 m to
z 1.3 = 2.6 m over the water; cam02 re-stationed to the ref-062 NNE fit at 40 mm), **LIGHT r15**, **MAT r9 + r9b (the
photo projection)**, **ORN r8 + the lead's capital bake**. No other Blender ran during any QA render; every render was
one blocking `scripts/blender_run.sh` call.

## What was rendered and compared

| file | what |
|---|---|
| `renders/previews/qa/round08_0K_*.png` | Eevee 1280x720, 32 TAA, LOD1. Times **24.5 / 20.8 / 28.9 / 18.9 / 21.3 / 17.4 s**; whole pass **134.9 s** (r07 146.1, r06 218.6) — QA-06-13 held with margin. Log `qa_round08_eevee.log`. |
| `round08_01_lagoon_hero_cycles.png` | Cycles 1920x1080, 128 spp adaptive, OIDN, GPU: **380.0 s** (r07 373.7). Log `qa_round08_cycles_hero.log`. |
| `round08_04_rotunda_ceiling_cycles.png` | Cycles 1280x720, 64 spp: **229 s** (r07 231). |
| `round08_06_aerial_nocomp.png` | the un-composited twin for the cam06 ratio gate (19.3 s), `scripts/qa_r08_c06.py`. |
| `renders/qa_comparisons/round08_cam0K.png`, `round08_sheet.png` | render / canonical photo / 50 % blend per camera |
| `round08_cam01_aligned_vs_ref169.png` | the round-03..08 yardstick. **Scale 1.3108, dx -291.8, dy -126.6** (r07 1.3084 / -290.0 / -123.0); apex delta **0.44 %H** (r07 0.51 %). |
| `round08_stack_offset.png` | the hero-facing stack course by course at x8 vertical zoom |
| `round08_cam01_crops_vs_ref169.png` | 1:1 crop pairs (attic+entablature, capital+shaft/arch, reflection, shore) |
| **`round08_seams.png`** | **brief item 2**: the projection seam crops on cam02 / cam05 / cam01 with the coherent-step numbers burnt in (`scripts/qa_r08_seams.py`, new this round) |
| **`renders/qa_comparisons/round08_gate.png`** | **the gate composite**: Cycles hero beside ref 169, six Eevee views, r07 -> r08 deltas, trend r02 -> r08 |

Commands: `scripts/blender_run.sh 900 -- --background --python scripts/qa_render_round.py -- --round 08 --eevee`;
`... 1500 -- ... --round 08 --final --samples 128 --res 1920 1080 --cams 01`; `... 1500 -- ... --samples 64 --res 1280 720 --cams 04`;
`... 600 -- ... scripts/qa_r08_c06.py`; `... 600 -- ... scripts/qa_inspect.py`. Analysis (no Blender): `qa_silhouette.py align`
(crop 690 40 1235 520 / ref-crop 749 127 1165 493), `qa_compare.py`, `qa_crops.py`, `qa_stack_offset.py`, `qa_r07_measure.py`,
`qa_r08_seams.py`, `qa_gate_sheet.py --round 08`, and the owners' read-only tools on the merged master
(`light_r15_measure.py`, `mat_r6_measure.py`, `mat_r9_measure.py coffer`, `light_measure.py --summary ceiling`,
`env_r7_measure.py --c06ratio`). Nothing was written to master.blend; environment's `r7_numbers.json` was reverted after use.

## Brief item 1 — the re-base. **No round-07 box needs a row shift.**

Both stations moved, so this was checked twice.

**cam01.** The camera dropped 0.30 m, and every named course of the hero-facing stack moved **up exactly 4 rows**
(crown corona 181 -> 177, panel frame top 199 -> 195, panel bottom 265 -> 261, entablature corona 281 -> 277, dentil
bottom 294 -> 290, frieze top 301 -> 297, architrave top 321 -> 317, abacus 333 -> 329). At the attic's 13.36 px/m that
is **0.299 m** against the 0.30 m commanded — the station moved by exactly what it was told to.

The re-registration absorbed it: the alignment's `dy` moved **-123.0 -> -126.6**, i.e. the warped photograph moved up
**3.6 rows** against the render's 4.0. The residual is **0.4 rows = 3 cm**, so at any fixed frame row the render and the
aligned photograph still show the same course. The proof is the reference row itself, re-measured on this round's panel
at the **unchanged** round-03 box coordinates:

| box | r07 cached ref | **r08 ref on the new panel** | drift |
|---|---|---|---|
| sunlit attic 900 222 1020 256 | 188.3 / 40.5 / 0.580 / +132.8 | **189.8 / 40.6 / 0.582 / +134.2** | +0.8 % |
| attic string 880 214 1040 222 | 185.3 / 39.3 / 0.585 | 181.0 / 39.0 / 0.583 | -2.3 % |
| entablature 900 262 1020 296 | 148.2 / 33.8 / 0.581 | 145.5 / 33.7 / 0.588 | -1.8 % |
| shaded attic 1110 225 1150 260 | 118.8 / 30.5 / 0.451 | 120.5 / 30.6 / 0.454 | +1.4 % |
| water reflection 900 760 1020 840 | 164.8 / 33.7 / 0.373 | 165.5 / 33.7 / 0.358 | +0.4 % |
| ripples / near water / flank | 104.2 / 105.4 / 152.4 | 104.7 / 105.3 / 154.0 | <= 1.1 % |
| shore / south wing / north wing | 115.7 / 113.8 / 146.4 | 115.2 / 111.7 / 145.6 | <= 1.8 % |
| **dome cap 920 95 1000 120** | 236.6 / 45.8 / 0.257 | **224.3 / 44.1 / 0.272** | **-5.2 %** |

Every box reproduces within 2.3 % except the **dome cap**, which is 25 rows below the apex where the 0.44 %H apex
residual bites; its r07 -> r08 luminance comparison carries a +-5 % band and nothing was scored on it.
**Decision: the round-07 boxes are used unshifted for every number in this report.** Where a *round-over-round* render
statistic is sensitive to which course is inside the box (the entablature row-profile std, the attic anisotropy) the
course-tracking control at box-4 is printed next to it.

**cam02.** The station is new, so lighting r15's re-based boxes are used as the brief directs
(`light_r15_measure.BOXES["02"]`: shade_pier 573 227 653 387, shade_pier_r 700 240 760 380, shade_soffit 400 280 520 355,
shade_frieze 250 40 420 110, sunlit_pier 273 340 350 500, sky 60 40 200 140; the old `water` box is retired — there is
no water at the NNE station). **The ref-062 residuals cannot be restated: the render does not contain the picture.**
See QA-08-1 — the dome is clipped out of the top of frame.

## Brief item 3 / item 5 — the camera-height check at the new station, and the mirror ratio

- **Height.** By construction cam01 is at z 1.3 = `WATER_Z` + **2.6 m**, which is QA round 07's measured height for
  ref 169's photographer (2.6 m, 1.9-3.2 m for +-6 rows of horizon). The render confirms it two ways: the 4.0-row rise
  of the stack = 0.299 m at 13.36 px/m (above), and the strong waterline edge under the rotunda band moved
  **700 -> 694 rows**, 6 rows for the same 0.30 m, i.e. **k = 20.0 px/m** at the shore's distance against 13.36 px/m at
  the attic's — the shore is at 0.67 of the attic's distance, which is what the plan says. The row-correlation mirror
  search is still unusable on the render (best M 474.5 at corr 0.63, physically inside the building); the geometric
  check above replaces it. **The station is correct and is not the cause of the mirror deficit.**
- **Mirror ratio (brief item 3's addition).** reflection box / own sunlit attic = **116.3 / 189.4 = 0.614**
  against the photograph's **165.5 / 189.8 = 0.872**. Round 07: 0.55 vs 0.88. The mirror gained 0.06 of the 0.33 it owes.

## Brief item 2 — the photo projection

**Seams: none found. Not a blocker.** `scripts/qa_r08_seams.py` crops the two places a mask edge can show — the band
edge (`projection_meta.json` band rows 86-100 .. 312-328 of the hero frame, i.e. world z ~26-27 m at the capital and
~43-44 m at the dome springing) and the facing-mask ramp around the rotunda's curvature — on the two cameras that are
NOT the projector, and reports the largest **coherent** step of the horizontally blurred row profile:

| crop | max coherent step (lum/row) | median | ratio |
|---|---|---|---|
| cam02 lower band edge (capital / architrave) | 6.34 | 0.57 | 11.0x |
| cam02 facing-mask ramp (N face -> E face) | 4.46 | 0.87 | 5.1x |
| cam02 upper band edge (dome springing) | 9.34 | 0.97 | 9.6x |
| cam05 lower band edge (attic -> colonnade) | 13.55 | 0.88 | 15.5x |
| cam05 facing-mask ramp along the south wing | 8.24 | 0.99 | 8.3x |
| **cam01, the projector's own frame** | **22.44** | 1.72 | 13.1x |

Every step above coincides with a real moulding in the crop, and **the projector's own frame carries the largest step of
the six** — the opposite of what a mask edge would do, since the projection is at full strength there and absent from the
others. No doubled feature and no sun in the shade: the hero's shaded attic did not gain luminance (134.0 -> **127.8**)
while its chroma moved onto the photograph's (sat 0.310 -> **0.432** against ref **0.454**, hue 32.1 -> **34.3** against
ref 30.6), which is the projection importing the photograph's *shaded* colour, not its sunlit colour.

| the projection's own tests | round 07 | **round 08** | ref 169 | verdict |
|---|---|---|---|---|
| attic std ratio 900 222 1020 256 | 29.4 / 44.9 = 0.65 | **28.8 / 42.8 = 0.673** | — | **pass** (test >= 0.60) |
| attic anisotropy, wide box | 3.12 | **5.02** (course-tracking control 3.76) | 3.39 | pass (>= 2.0), now **1.48x the photo** |
| attic anisotropy, narrow box | 3.52 | **8.23** (control 3.89) | 4.58 | pass, **1.80x the photo** |
| sunlit chroma (QA-07-2) sat / R-B | 0.437 / 98.8 | **0.462 / 104.9** | 0.582 / 134.2 | **FAIL**: +0.025 of the 0.09 asked, +6.1 of the 35 |
| Eevee vs Cycles albedo, sunlit attic | — | Eevee 181.8 / 36.8 / 0.517 vs Cycles **189.4 / 36.1 / 0.462** | — | lum 0.96, hue 0.7 deg, sat 0.055 apart — **agree** |

Reading: the projection **shipped, registered and is invisible as a seam**, and it moved the shade's colour onto the
photograph's. It did **not** move the sunlit chroma anywhere near the window — 28 % of the saturation gap and 17 % of the
R-B gap. MAT r9b's own conclusion (the shaded-hue window binds at tint exponent 1.25, so albedo cannot carry QA-07-2)
is confirmed on the merged master: QA-07-2 is a colour-management / sun-colour item, not an albedo item.

## Score table (0-5; target >= 4 every row, hero average >= 4.5). Round 07 -> round 08.

| row | 01 hero | 02 NE 3/4 | 03 colonnade | 04 ceiling | 05 S lawn | 06 aerial |
|---|---|---|---|---|---|---|
| Silhouette match | 4 -> 4 | 3.5 -> **2.5** | 2.5 -> 2.5 | 3.5 -> 3.5 | 3.5 -> 3.5 | 4 -> 4 |
| Proportion | 4 -> 4 | 3.5 -> 3.5 | 3 -> 3 | 3.5 -> 3.5 | 3.5 -> 3.5 | 3.5 -> 3.5 |
| Ornament fidelity | 4 -> 4 | 3.5 -> **4** | 2.5 -> **3** | 3 -> 3 | 3.5 -> 3.5 | 2.5 -> 2.5 |
| Material realism | 3 -> **3.5** | 3 -> **2** | 2 -> **2.5** | 3.5 -> **3** | 3 -> **3.5** | 2.5 -> 2.5 |
| Edge wear | 3 -> **3.5** | 2.5 -> 2.5 | 1 -> **1.5** | 1 -> 1 | 2 -> 2 | 0.5 -> 0.5 |
| Lighting mood | 4 -> **4.5** | 3.5 -> **2** | 2.5 -> **3.5** | 3 -> 3 | 3.5 -> 3.5 | 2.5 -> **3** |
| Water reflection | 2.5 -> **3** | 2.5 -> n/a | n/a | n/a | 2.5 -> 2.5 | 2 -> **2.5** |
| Repetition visibility | 3 -> 3 | 2.5 -> 2.5 | 2 -> 2 | 2.5 -> 2.5 | 2.5 -> 2.5 | 2.5 -> 2.5 |
| Scale cues | 3.5 -> 3.5 | 3 -> **2.5** | 2.5 -> 2.5 | 3 -> 3 | 3 -> 3 | 2.5 -> **3** |
| **average (delta)** | **3.67 (+0.22)** | **2.69 (-0.37)** | **2.56 (+0.31)** | **2.81 (-0.06)** | **3.06 (+0.06)** | **2.67 (+0.17)** |

**Hero delta, stated explicitly (brief item 4): 3.44 -> 3.67, +0.22** — a second consecutive hero gain, and the largest
two-round run of the project (3.22 -> 3.67, +0.45 over rounds 07-08).

**The definition-of-done rule applied (CLAUDE.md).** The gate passes at hero **>= 4.0**: **3.67, so it does not pass.**
The alternative exit is "two consecutive rounds after the concrete photo-projection pass improve the hero by less than
0.1". **Round 08 is the first round after the projection pass and it improved the hero by 0.22, which is not < 0.1.**
The clock is therefore armed with **0 of its 2 flat rounds used**: one more round is owed under the rule, and only if
that round *and* the one after it both come in under +0.1 does the rule stop the polishing. QA's own reading of the
headroom: the hero is 0.33 short of 4.0 and three of its nine rows are at 3.5 with a measured, named cause each
(material realism, edge wear, water) — the +0.33 is reachable, but not from albedo, and not in one round unless the
sun/look question behind QA-07-2 is answered.

**cam02's -0.37 is the new station, not a loss in the model.** The round-07 station stood SSE (the mirror-image face)
and framed the whole building; the round-08 station stands on ref 062's own NNE side and is the correct choice, but at
40 mm it clips the dome out of frame and it points the camera at a face whose shade is violet. Both are fixable and both
are listed below. On the *old* station's own numbers nothing regressed.

### Trend across rounds 02 -> 08 (averages)

| cam | r02 | r03 | r04 | r05 | r06 | r07 | **r08** | reading |
|---|---|---|---|---|---|---|---|---|
| 01 hero | 2.94 | 3.28 | 3.28 | 3.28 | 3.22 | 3.44 | **3.67** | +0.45 over two rounds; the projection carried the shade, not the sun |
| 02 NE 3/4 | 2.11 | 2.33 | 2.67 | 2.78 | 2.72 | 3.06 | **2.69** | the new NNE station: right side, wrong lens, violet face |
| 03 colonnade | 1.94 | 2.13 | 2.00 | 1.75 | 2.12 | 2.25 | **2.56** | best round yet; the frame is no longer black (28.0 -> 12.6 %) |
| 04 ceiling | 2.31 | 2.13 | 2.44 | 2.56 | 2.75 | 2.88 | **2.81** | unchanged optically; the coffer rim over-corrected the other way |
| 05 S lawn | 2.11 | 2.67 | 2.72 | 2.78 | 2.78 | 3.00 | **3.06** | the projected stone reads; the lagoon band is still 1.14x too bright |
| 06 aerial | 2.17 | 2.17 | 2.39 | 2.50 | 2.28 | 2.50 | **2.67** | far-shore lines 0 -> 3, the band is warm again |

Verdict: **gate not passed.** But the round did what the projection was commissioned to do on the shade and the water,
and it broke nothing that was passing except the entablature row-profile std at the margin and cam04's coffer rim.

Explicit "clean CAD / game asset" rejects this round, each with its crop:
- **The arch soffit / intrados on the hero** (`round08_cam01_crops_vs_ref169.png` pane 2, unchanged from round 07): a
  smooth untextured pale vault where the photograph carries a moulded archivolt over a coffered soffit. Eight
  `SOCKET_archivolt_run_##` have been in the file since ARCH r7 and nothing is instanced on them. At 1:1 it is still the
  largest single blank surface in the hero's ornament zone.
- **cam02's shaded face** (`round08_seams.png` panes 1-3): the fluted shafts and the arch vaults are deep indigo
  (hue 255-263 at sat 0.43-0.46) against ref 062's warm pink-grey. This is the round-06 violet flood, alive on the one
  face no camera looked at until this round.
- **The shore** (crops pane 4): a uniform dark green hedge against the photograph's willows with visible trunks, a small
  building with a green door, and people. Render 89.2 lum vs the photograph's 115.2 on the same band.
- **The hero mirror** (crops pane 3): a dim smeared reflection with a flat pale-blue patch where the photograph has hard
  gold-and-blue vertical streaks.

## What works (keep it)

- **The projection is invisible and it registered.** No resolvable seam on cam02 or cam05 (table above), std ratio
  **0.673**, anisotropy **5.02 / 8.23** against the photo's 3.39 / 4.58, and Eevee and Cycles agree on the projected
  albedo to 4 % of luminance and 0.7 deg of hue.
- **The hero shade landed.** Shaded attic **127.8 / 34.3 / 0.432** against ref **120.5 / 30.6 / 0.454** — 1.3 lum over
  the 103.5-126.5 window (round 07: 7.5 over) with hue and saturation both inside, and shade / sunlit **0.675** against
  the photograph's **0.635**.
- **The open lagoon closed.** Flank **162.8 / hue 209.6** vs the photo's 154.0 / 200.5 (lum 1.06x, both halves of
  QA-07-1's flank test pass); ripples R-B **-22.5** vs -17.0 (round 07: -47.6); near water lum **125.3** inside the
  +-25 % window (round 07 143.9, 1.37x).
- **cam03 is no longer a black frame.** Below lum 10 **28.0 % -> 12.6 %** (test <= 20 %), below 20 **57.1 % -> 36.0 %**,
  and the outer lagoon-side row at **0.166** of the sunlit rotunda (test >= 0.15) at hue 58.9 — QA-07-5 closes on both
  halves for the first time.
- **cam06's far field came back.** **3** readable far-shore lines on the composited frame (test >= 3; round 07: 0) with
  the ratio gate held at **0.633** (test >= 0.60), and the band is warm again (roofs hue 33.8, plaza 46.1, trees 41.5,
  all inside the 22-52 window).
- **The capitals sharpened again**: **25** luminance maxima along the capital band against the photograph's **22** at
  contrast **1.309 vs 1.350** = 0.97 of the photo's (round 07: 20 vs 17 at 0.95).
- **The stack still registers** after the station move: every named course within **5 rows / 0.37 m** of ref 169, attic
  storey **97 vs 101 rows = 0.96** (test: within 10 %), capital 35 vs 30 rows.
- **Weathering is at or above the photograph's**: under-cornice run-off **20.8 %** of columns (photo 19.2 %), waterline
  band **51.1 %** on 223 columns (photo 38.2 %), entablature texture std **50.7** = 0.79 of the photo's.
- **Eevee is cheap**: six-camera pass **134.9 s** (r07 146.1, r06 218.6).
- Saved deliverable state intact (see "Deliverables present").

## Measurements

### (a) Chroma at delivery resolution (Cycles hero 1920x1080; ref 169 on THIS round's aligned panel)

| region | box | round 07 | **round 08** | ref 169 | verdict |
|---|---|---|---|---|---|
| sunlit attic panel | 900 222 1020 256 | 190.4 / 35.8 / 0.437 / 98.8 | **189.4 / 36.1 / 0.462 / 104.9** | 189.8 / 40.6 / 0.582 / 134.2 | lum **1.00 pass**; sat 0.12 under, R-B 29 short — **QA-07-2 still fails** |
| attic string course | 880 214 1040 222 | 171.9 / 35.9 / 0.462 | **180.4** / 35.8 / 0.460 | 181.0 / 39.0 / 0.583 | lum **1.00** (was 0.93) |
| entablature | 900 262 1020 296 | 142.8 / 38.2 / 0.626 | **132.9** / 38.1 / **0.700** | 145.5 / 33.7 / 0.588 | lum 0.91 (was 0.96); sat at the 0.70 ceiling |
| dome cap | 920 95 1000 120 | 206.2 / 35.6 / 0.248 | 190.6 / 36.7 / 0.361 | 224.3 / 44.1 / 0.272 | lum 0.85 (+-5 %, see item 1) |
| shaded attic | 1110 225 1150 260 | 134.0 / 32.1 / 0.310 | **127.8 / 34.3 / 0.432** | 120.5 / 30.6 / 0.454 | hue + sat **pass**; lum 1.3 over the window (was 7.5) |
| columns (mask hue<32 sat>0.30, 680 280 1240 470) | mask | 107.4 / 25.9 / 0.610 | **105.4 / 26.3 / 0.628** | 95.4 / 24.5 / 0.588 | hue + sat **pass**; lum 1.10 |
| water reflection column | 900 760 1020 840 | 105.6 / 36.5 / 0.307 / +36.4 | **116.3 / 39.0 / 0.348 / +45.5** | 165.5 / 33.7 / 0.358 / +68.7 | R-B + hue + sat pass; **lum 0.70, still under 124** |
| ripples | 1100 960 1500 1060 | 139.6 / 229.7 / -47.6 | **121.8 / 208.7 / -22.5** | 104.7 / 182.8 / -17.0 | much better; 1.16x, 26 deg blue |
| near water, sky-reflecting | 1150 1000 1450 1050 | 143.9 / 227.9 / 0.300 | **125.3 / 207.9 / 0.200** | 105.3 / 190.3 / 0.252 | lum **pass** (1.19, window 79-132); hue 7.9 deg outside 185-200 |
| lagoon flank | 100 900 400 960 | 189.5 / 224.2 | **162.8 / 209.6 / 0.230** | 154.0 / 200.5 / 0.266 | **both halves pass** (1.06x, hue <= 210) |
| sky top / sky low-left | lighting's boxes | 154.8 / 167.9 -> 0.922 | 154.8 / 167.9 -> **0.922** | panel 0.921 | closed, unchanged |
| shore band | 700 600 1200 740 | 88.8 / 41.8 / 0.595 | 89.2 / 42.3 / 0.638 | 115.2 / 40.9 / 0.632 | **0.774** (test +-25 %, pass by 0.024) |
| south wing | 60 480 560 600 | 104.2 / 36.7 / 0.247 | **100.5** / 37.8 / 0.287 | 111.7 / 34.6 / 0.162 | 0.90 — **fails the >= 103 test again** |
| north wing | 1360 480 1860 600 | 142.3 / 40.7 / 0.432 | 139.0 / 41.3 / 0.471 | 145.6 / 42.1 / 0.496 | 0.955 pass |

### (b) Texture / weathering at 1:1 and its direction

| box | round 06 | round 07 | **round 08** | ref 169 | ratio / reading |
|---|---|---|---|---|---|
| attic std 900 222 1020 256 | 32.6 | 29.4 | **28.8** | 42.8 | **0.673 pass** (test 0.60) |
| entablature std 900 262 1020 296 | 52.0 | 53.7 | **50.7** | 64.5 | 0.79 pass |
| attic anisotropy, wide | 0.41 | 3.12 | **5.02** | 3.39 | pass; control at box-4 **3.76** |
| attic anisotropy, narrow 900 224 1020 248 | 0.76 | 3.52 | **8.23** | 4.58 | pass; control **3.89** |
| entablature row-profile std | 36.5 | 44.0 | **37.6** (control at box-4 **40.5**) | 53.0 | **at the margin**: the fixed box fails the >= 40 test, the course-tracking box passes by 0.5 |
| under-cornice run-off (`mat_r6_measure cornice`) | 11.7 % | 19.2 % | **20.8 %** | 19.2 % | **above the photograph** (test >= 19 %) |
| waterline band (`mat_r6_measure waterline`) | 44.9 % / 245 | 43.6 % / 227 | **51.1 % / 223** | 38.2 % | pass |

### (c) Interior fills, cam04 vs ref 083 (round-03 boxes)

| ratio | ref 083 | r07 Eevee | r07 Cycles | **r08 Eevee** | **r08 Cycles 64 spp** |
|---|---|---|---|---|---|
| soffit / own sky (W / E) | 0.381 / 0.429 | 0.459 / 0.423 | 0.238 / 0.472 | **0.459 / 0.423** | **0.237 / 0.471** |
| coffer field / own sky | 0.437 | 0.356 | 0.465 | **0.349** | **0.462 pass** |
| dark quarter / light quarter | 0.265 | — | 0.233 | 0.223 | **0.231 pass** (test >= 0.20) |
| coffer field sat / rim sat (`mat_r9_measure coffer`) | 0.427 / 0.438 | — | 0.325 / **0.541** | — | **0.339 / 0.626** — **both outside 0.38-0.50; the rim moved the wrong way** |
| Eevee - Cycles gap (test <= 0.15) | | | | coffer **-0.113 pass**; soffit E -0.052 pass; **soffit W +0.222 fail** (r07 +0.202) |

### (d) cam03 — the shade test on lighting's boxes (`light_r15_measure.BOXES["03"]`)

| box | what it is | round 07 | **round 08** | / sunlit rotunda (lum 98.2) |
|---|---|---|---|---|
| 480 150 560 600 | the sky-visible shaft flank | 50.7 / 48.5 / 0.808 | **61.2 / 46.6 / 0.865** | **0.623** — inside 0.30-0.70 |
| 880 120 1200 600 | the outer (lagoon-side) row | 9.5 / 70.8 / 0.922 | **16.3 / 58.9 / 0.947** | **0.166 PASS** (test >= 0.15 at hue 25-60) |
| 420 560 900 720 | the walk | 54.8 / 195.6 / 0.175 | **74.9 / 92.1 / 0.138** | 0.762; hue went blue -> **green**, still outside 25-60 |
| frame below lum 10 / 20 | | 28.0 % / 57.1 % | **12.6 % / 36.0 %** | test <= 20 % — **PASS** |

### (e) cam02 / cam05 / cam06

cam02 (lighting r15's re-based boxes, Eevee 1280x720): shade_pier **32.5 / hue 263.0 / sat 0.464**, ratio 0.727;
shade_pier_r **46.7 / 255.8 / 0.428**, ratio 1.046; shade_soffit 42.2 / **239.3** / 0.524, ratio 0.944; shade_frieze
95.5 / 39.7 / 0.453, ratio 2.137; sunlit_pier 44.7 / 34.1 / 0.723; sky 168.4 / 209.9. **Three of the four shaded boxes
are violet at saturations of 0.43-0.52**, and the "sunlit" denominator is darker than one of its own shaded boxes
(ratio 1.046), i.e. the near face is not lit at all at this station.
cam05: water band (448 619 960 713) **133.6 / 38.8 / 0.250** vs ref 063's 93.4 / 64.9 / 0.306 — **sat passes
(>= 0.24); lum 1.14x, outside the 70-117 window and worse than round 07's 128.6**; attic band (300 150 980 260)
165.1 / 39.7 / 0.442, std 43.6 against ref 063's 63.5 = **0.687 pass**.
cam06: roofs 127.5 / **33.8** / 0.072; plaza 109.6 / **46.1** / 0.202; trees 124.2 / **41.5** / 0.256 — all three inside
the 22-52 window for the first time; horizon crop mean 117.2 **std 33.9** against the un-composited twin's 81.5 / 53.5.
**cam06 gate: 33.9 / 53.5 = 0.633 (test >= 0.60) pass**, and **far-shore lines 3 composited / 7 un-composited**
(test >= 3) — **QA-07-6 closes**.

### (f) Wings on the hero, on a render (shadow = below half the band's own p90)

| band | box | render p90 / shadow share | ref 169 aligned | reading |
|---|---|---|---|---|
| SOUTH (frame-left) | 60 480 560 600 | 203.8 / **59.4 %** | 219.5 / **54.8 %** | +4.6 pt darker (r07 +3.3) |
| NORTH (frame-right) | 1360 480 1860 600 | 219.3 / **38.0 %** | 228.4 / **39.3 %** | -1.3 pt (r07 -2.7) |

Both bands are within 5 points of the photograph's own dark share; ENV r9's 21.2 % ray-probe figure stays confirmed at
the level a render can resolve.

### (g) The hero-facing stack after the station move (`round08_stack_offset.png`, band x 880-1040, 13.42 px/m)

| course | r08 render row | ref 169 row | delta rows | delta m |
|---|---|---|---|---|
| attic crown cornice, top lit edge | 164 | 165 | -1 | +0.07 |
| attic crown corona, shadow under it | 177 | 179 | -2 | +0.15 |
| attic panel frame top | 195 | 195 | 0 | 0.00 |
| attic panel frame bottom | 261 | 266 | -5 | +0.37 |
| entablature cornice corona | 277 | 279 | -2 | +0.15 |
| dentil band bottom | 290 | 289 | +1 | -0.07 |
| frieze top | 297 | 294 | +3 | -0.22 |
| frieze bottom = architrave top | 317 | 317 | 0 | 0.00 |
| capital top (abacus) | 329 | 325 | +4 | -0.30 |

**Every course within 5 rows (0.37 m); the acceptance is +-8. QA-06-1 stays closed after the station move.**
Storeys: attic 97 vs 101 rows = **0.96**; entablature cornice 20 vs 15 = 1.33; frieze 20 vs 23 = 0.87; capital 35 vs
30 = 1.17. (The tool's auto-walk mis-pairs edges — the rows above are read course by course off the labelled x8 panel,
as in round 07.)

## Viewport performance (pass/fail, not scored)

- Open **0.75 s** headless (budget 60 s) — pass. 9679 objects, 72 materials, 0 placeholders, 161.0 MB.
- LOD1 **11.38 M tris** — pass.
- Eevee 1280x720 previews **17.4-28.9 s** per camera, whole pass **134.9 s** — pass.
- Cycles hero 1920x1080 128 spp adaptive **380.0 s**; cam04 64 spp 1280x720 **229 s**.

## Deliverables present (pass/fail)

- Cycles final config **pass, as saved**: GPU, 768 spp adaptive (threshold 0.01, min 64), OIDN, time limit 0,
  `AgX - High Contrast`, exposure -2.8331, 1920x1080 at 100 %.
- `CAM_flythrough`, `CAM_flythrough_path`, `CAM_flythrough_target` **pass**; 2 light probes **pass**; 7 cameras,
  active camera = the hero.
- **Frame range is now 1-2616 at 24 fps (109 s)** against round 07's 1-1224 (51 s). Nothing in the round's briefs asked
  for it; the lead should confirm which path length is intended before the Phase-5 test animation is timed.
- Eevee viewport config **pass**: taa 8 / 16, raytracing off, shadow ray count 1.
- 4K 768-spp timing (QA-03-16): **not run this round** by instruction. Still open, still the only untested delivery item.

## Status of every round-07 defect (measured on the lead's master, brief item 3)

| defect | owner | status | the number |
|---|---|---|---|
| QA-07-1 open lagoon bright + lavender | materials + lighting | **closed on 3 of 4 boxes** | flank **162.8 / hue 209.6** (both halves pass; 1.06x, window <= 210); near water lum **125.3** pass, **hue 207.9 fails 185-200 by 7.9 deg**; ripples R-B -22.5 (photo -17.0); **cam05 band 133.6, window 70-117, fails and is worse than r07's 128.6**; hero reflection unchanged in colour (R-B +45.5, hue 39.0) as required. |
| QA-07-2 sunlit stone chroma | materials | **open; the projection could not carry it** | attic sat **0.462** (window 0.53-0.62, +0.025 of the 0.09 asked), R-B **104.9** (test >= 120, +6.1 of the 35). Luminance 1.00, hue 36.1, texture and streak direction all pass. Confirms MAT r9b: the shaded-hue window binds before albedo can reach the sunlit window. |
| QA-07-3 hero mirror 0.64 of the photo | materials | **half closed** | reflection **116.3** (window 124-208; r07 105.6) at R-B +45.5 / hue 39.0 / sat 0.348 — colour pass, **level still 8 lum under the window**; mirror / own sunlit attic **0.614** vs the photo's **0.872**. |
| QA-07-4 archivolt + bed-mould blank | ornament + architecture | **open, unchanged** | 8 `SOCKET_archivolt_run_##` in the file, 0 instances on them; the arch soffit is still the largest blank surface in the hero at 1:1 (crops pane 2). |
| QA-07-5 cam03 black frame | lighting | **CLOSED on both halves** | below lum 10 **12.6 %** (test <= 20 %; r07 28.0 %); outer row **0.166** of sunlit (test >= 0.15; r07 0.097) at hue **58.9** (window 25-60). |
| QA-07-6 cam06 far field milky | environment + lighting | **CLOSED** | **3** far-shore lines composited (test >= 3; r07 0), 7 un-composited, ratio **0.633** held (test >= 0.60). |
| QA-07-7 hero shade level overshoot | lighting | **half closed** | shaded attic **127.8** against the 103.5-126.5 window — **1.3 lum over** (r07 134.0, 7.5 over) with hue 34.3 and sat 0.432 both inside. |
| QA-07-8 Eevee-Cycles soffit W gap | lighting | **open, slightly worse** | gap **+0.222** (test <= 0.15; r07 +0.202); Cycles soffit W **0.237** vs ref 083's 0.381. |
| QA-07-9 coffer rim saturation | materials | **open, over-corrected the other way** | Cycles rim sat **0.626** (was 0.541 by the same tool; window 0.38-0.50, ref 0.438) and the field fell to **0.339** (ref 0.427). Both ends of the saucer are now outside the window in opposite directions. |
| QA-07-10 mid-ground tree masses | environment | **open, unchanged** | shore band 0.774 of ref; the hero's shoreline is a uniform dark hedge against ref 169's willows with visible trunks (crops pane 4). |
| QA-07-11 cam02 shaded pier over-warm | lighting | **superseded and much worse** | on the new station three shaded boxes are **violet**: pier hue **263.0** at sat 0.464, pier_r **255.8** / 0.428, soffit **239.3** / 0.524. Reclassified as QA-08-2. |
| QA-07-12 entablature sub-courses | architecture | **open, unchanged** | cornice **1.33** of the photo's rows (20 vs 15), frieze **0.87** (20 vs 23). |
| QA-06-9 entablature row std | architecture | **at the margin** | **37.6** on the fixed box (test >= 40), **40.5** on the course-tracking box; ref 53.0. Not reopened, flagged. |
| QA-03-16 4K 768 spp timing | lead | **open, not run** | excluded by the brief. |

## Defect list — round 08

| id | cam | owner | severity | description (measurable) | where | acceptance test |
|---|---|---|---|---|---|---|
| QA-08-1 | 02 | lead | **blocker** | cam02's new station clips the dome out of frame: **0 % sky** in the top-centre band (x 400-900) of rows 0-60 against ref 062's **91 % sky in rows 0-27**, and `qa_silhouette.py measure` returns apex_y **0**. Geometry: from (-79.8, 24.4, 1.55) the apex (z 53.4, D 83.4 m) is **31.87 deg** above horizontal and the axis to (0,0,23.5) is **14.75 deg**, so the apex is **17.1 deg** off-axis against a 40 mm half-FOV of **14.2 deg** — 2.9 deg outside. The station is right (ref 062 is the NE view); the lens is not. | `scripts/qa_cameras.py` cam02 `lens` | reproduce ref 062's framing: apex at **0.05 +- 0.02** of frame height and podium base at **0.85 +- 0.03**. The vertical field needed is -1.06 deg to +31.87 deg = 32.9 deg over 0.80 of the frame, i.e. a full field of 41.1 deg -> **lens ~27 mm** at this station (or hold 40 mm and move out past D 120 m). |
| QA-08-2 | 02 | lighting | **blocker** | The camera-facing side of the rotunda is violet: shade_pier **32.5 / hue 263.0 / sat 0.464**, shade_pier_r **46.7 / 255.8 / 0.428**, shade_soffit **42.2 / 239.3 / 0.524** against ref 062's warm pink-grey; and shade_pier_r is **brighter than the sunlit_pier denominator** (ratio 1.046), so the NNE face has no directional light at all. This is the round-06 violet flood surviving on the one face no camera had looked at. LIGHT r15 carried it as a minor because the hero holds; on the frame the viewer now sees it is the whole picture. | the anti-sun / horizon tint discriminators on a NNE-facing surface; the single `LIGHT_shade_fill` NNE lamp's own colour | all four cam02 shade boxes at **hue 25-60 with sat <= 0.35**, `shade_pier_r / sunlit_pier <= 0.8`, and the hero's shaded attic held at 103.5-126.5 / hue 23.5-35.5 / sat <= 0.50. |
| QA-08-3 | 01 | materials + lead | **blocker** | Sunlit stone is still 0.12 of saturation and 29 of R-B short of the photograph (attic **0.462 / 104.9** vs **0.582 / 134.2**) after the projection pass moved it 28 % and 17 % of the way. MAT r9b's transfer measurement plus this round's number closes the albedo route: raising albedo further breaks the shaded-hue window, which is now *passing* (34.3 / 0.432 vs ref 30.6 / 0.454). The remaining levers are the sun's own colour/temperature and the view-transform look. | `LIGHT_sun` temperature / `sun_intensity`, or `scene.view_settings.look`; not `MAT_concrete_ochre` | attic **sat 0.53-0.62 and R-B >= 120** at lum 178-201, **with** the shaded attic held at 103.5-126.5 / hue 23.5-35.5 / sat <= 0.50 and the columns mask at hue 24.5 +- 4 / sat 0.55-0.65. Whoever tries it must show all three boxes in the same frame. |
| QA-08-4 | 01, 02 | ornament + architecture | major | The archivolt is still a blank vault and the bed-mould has no modillions (unchanged from QA-07-4). 8 `SOCKET_archivolt_run_##`, 0 instances. At cam02's new station this surface is now **four times larger in frame** than on the hero. | `ORN` archivolt band on the sockets; bed-mould modillion subtype | a 1:1 pane in which the archivolt carries a moulded band and the bed-mould a modillion course; alternation count along the archivolt within 30 % of the photo's on the same band. |
| QA-08-5 | 01 | materials | major | The hero mirror is **0.614** of its own sunlit stone against the photograph's **0.872**; the reflection box is **116.3**, 8 lum under the 124-208 window. Colour is solved (R-B +45.5, hue 39.0, sat 0.348 vs the photo's 0.358); only the level is short, and `WATER_GLOSS_MIX` is already at 0.45 with cam05 over its own ceiling. | `MAT_water_lagoon` specular level / roughness at 87-89 deg, or the luminance of the lower stone being mirrored | reflection box 900 760 1020 840 **lum 124-208** with R-B >= +35 and hue 25-45 held, **and** cam05's water band back inside 70-117. |
| QA-08-6 | 05 | materials + lighting | major | cam05's lagoon band went the wrong way: **133.6** against the 70-117 window and ref 063's 93.4 (round 07: 128.6, round 06: 114.9). The gloss-mix decision that bought the hero mirror 11 lum cost cam05 5. Saturation still passes (0.250 >= 0.24). | the same `WATER_GLOSS_MIX` / sheen ramp, at cam05's incidence | cam05 band 448 619 960 713 **lum 70-117** at sat >= 0.24, with the hero reflection box not falling below 116.3. |
| QA-08-7 | 03 | lighting | major | The colonnade walk turned from blue to **green**: hue **92.1** at sat 0.138 (round 07: 195.6 at 0.175), still outside the 25-60 window, and it is the largest surface in the frame. The shade is now bright enough (frame black 12.6 %) and the wrong colour. | the bounce term's tint on up-facing ground inside the colonnade; `ENV` grass albedo bleeding into the walk | walk 420 560 900 720 at **hue 25-60**, sat <= 0.35, with the outer row held at >= 0.15 of sunlit. |
| QA-08-8 | 04 | materials | major | The coffer saucer over-corrected in both directions: field sat **0.339** (ref 0.427) and rim sat **0.626** (ref 0.438), both outside the 0.38-0.50 window, where round 07 had the field inside it. The saucer now reads grey in the fields and orange at the ribs. | `MAT_plaster_ceiling` / `MAT_plaster_ceiling_rib` albedo saturation | both **0.38-0.50** by `mat_r9_measure.py coffer`, with dark/light ratio >= 0.20 and coffer/sky 0.35-0.55 held. |
| QA-08-9 | 04 | lighting | minor | Eevee-Cycles soffit W gap **+0.222** (test <= 0.15; r07 +0.202, r06 +0.195) — four rounds unchanged, and Cycles is the engine that is wrong (0.237 vs ref 083's 0.381). | probe / screen-trace coverage of the west soffit | gap <= 0.15 **and** Cycles soffit W within 0.10 of 0.381. |
| QA-08-10 | 01, 05 | environment | minor | The shoreline is a uniform dark hedge: shore band **89.2** vs the photograph's **115.2** (0.774, passing its own +-25 % test by 0.024) with no trunks, no built structure and no figures, against ref 169's willows, green-doored shed and people. Unchanged from QA-07-10. | `ENV` shoreline cluster plan and its trunk / prop content | the hero's tree-mask area between x 0.55-0.75 and x 0.25-0.45 within 30 % of ref 169's on the aligned panel, and at least one non-vegetation shoreline object in the hero's 700-1200 band. |
| QA-08-11 | 01 | architecture | minor | The two sub-courses inside the registered stack are unchanged: entablature cornice **1.33** of the photo's rows (20 vs 15), frieze **0.87** (20 vs 23) — ARCH r7's option A. Worth 0.5 of Proportion on the hero, not more. | `CORNICE_H` / `FRIEZE_H` and the rinceau refit | cornice and frieze both within 15 % of the photo's rows on `qa_stack_offset.py --y0 260 --y1 340`. |
| QA-08-12 | 01 | architecture / materials | minor | Entablature row-profile std **37.6** on the fixed round-03 box, below the >= 40 test that closed QA-06-9 in round 07 (44.0); the course-tracking control gives **40.5**, so the loss is mostly the 4-row station shift and only ~3.5 of it is real. Ref 53.0. | the cornice/dentil shadow depth | **>= 40 on both** the fixed box and the box-4 control. |
| QA-08-13 | — | lead | minor | The saved frame range moved to **1-2616** (109 s at 24 fps) from round 07's **1-1224** (51 s), with nothing in the round's briefs asking for it. The Phase-5 test animation is timed off this number. | `master.blend` scene frame range / the flythrough builder | the lead states which length is intended and the file carries it. |
| QA-03-16 | — | lead | open | 4K 768 spp timing, still never run. | — | one 3840x2160 frame at 128 spp fixed (adaptive off) with an outer wall-clock guard, before attempting 768. |

## Notes for the lead

1. **The projection did its job on the shade and not on the sun.** No seam, no doubled feature, no baked sunlight, std
   ratio and anisotropy at or above the photograph's, and the shaded attic's colour is now on ref 169's (sat 0.432 vs
   0.454, hue 34.3 vs 30.6) — that is the projection speaking. The sunlit chroma moved 28 % of the way and stopped
   exactly where MAT r9b predicted it would. **QA-08-3 should not be sent back to materials as an albedo task.** The
   next attempt on it is the sun's colour or the look, and it has to be shown against three boxes at once.
2. **cam02 is the round's real regression and neither half of it is the model.** The station is correct and should
   stay; the lens is 13 mm too long (QA-08-1, with the arithmetic) and the face it now points at was never lit
   (QA-08-2). Both are small, cheap fixes that would take cam02 back over 3.0 on their own numbers.
3. **Three defects closed outright** — QA-07-5 (cam03 on both halves), QA-07-6 (cam06 far field), and QA-07-1's flank
   and ripple boxes — and QA-07-7 came within 1.3 lum of its window. Nothing that was passing broke except the coffer
   rim (QA-08-8) and the entablature row std at the margin (QA-08-12).
4. **The rule.** Hero **3.67**, below 4.0, so the gate does not pass; and since the hero moved **+0.22 >= 0.1** in the
   first round after the projection, the two-round flat clock has **0 of 2** rounds on it. One more polish round is owed
   before the rule can stop the loop. If the lead wants the cheapest +0.33 on the hero, it is not on the hero: it is
   QA-08-5 (mirror level, Water reflection 3 -> 4) plus QA-08-4 (archivolt, Ornament 4 -> 4.5) — the two rows with the
   largest named gaps and the smallest unknowns. QA-08-3 is worth 0.5 on two rows but has no known lever.
