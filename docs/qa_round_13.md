# QA round 13 — Phase 6 **Gate 3, the lightmaps alone**, 2026-09-16. **LIGHTMAPS ACCEPTED, one re-bake**

Scored on the viewer engineer's `round13b` capture (`phase6-viewer` @ 0b08a6b, `renders/web/round13b_cam01..06.png`, manifest v4, `materials=pbr`, `lighting=baked`, **post off**, water on, placeholders hidden, 1920x1080) against the matching `round13direct_*` control and the Gate 2 capture. No Blender, no Chrome. New: `scripts/qa_r13_probe.py` (boxes / green / shafts / frame / black / perf — three frames per box plus the reference, which is what "closed, halved or left" needs) and `scripts/qa_r13_gate.py` -> `renders/web/round13_gate.png`; definitions as round 12b (`web/tools/qa12_boxes.py`). `round13_cam0N.png` (pre `-kv`) was **not** scored, per the brief's addendum.

## 0. The step-0 finding is closed

Hero whole-frame luma **117.5 (quantised UV2) -> 134.3 (dq1) -> 135.99** against the Cycles hero's **139.98 = 0.971x**; p10 **52.89 vs 52.22** (the broken UV had 22.3). MAE against each station's reference falls on **all six**: 36.67 -> 29.88 (01), 40.15 -> 27.63 (02), 119.44 -> 46.26 (03), 57.31 -> 51.01 (04), 39.60 -> 31.32 (05), 63.62 -> 48.59 (06). `gate3.own` **16/16 applied**, max match error 0.019 m; `gate3.slots` **988/988 applied**, max 0.005 m; 9 materials cloned, 21/21 lightmap textures loaded, 0 failed. One diagnostic near-miss (`ENV_terrain_ground`, a neighbour with no TEXCOORD_1).

## 1. Parity per box (`qa_r13_probe.py boxes`; Rec.709 luma, hue, HSV sat, `mid(5-21)`, `hp9`; ratios viewer / Phase 5)

| box (cam01 @1920x1080 unless noted) | Gate 2 | **baked** | Phase 5 | the lightmap |
|---|---|---|---|---|
| hero shade band `1110 225 1150 260` | 143.8 (1.18x), std 35.9 | **114.0 (0.93x), std 55.5** | 122.1, std 44.2 | **closed** (slightly past it) |
| S-colonnade wall `1600 590 1670 635` | 200.9 (1.44x), hp9 5.83 | **170.8 (1.23x), hp9 27.71** | 139.3, hp9 26.32 | **halved**; hp9 now at parity |
| N-colonnade wall `62 548 104 606` | 130.8 (2.33x), hue 47.7 | **71.0 (1.27x), hue 219.9** | 56.1, hue 40.9 | level halved, **hue broken — QA-13-1** |
| capital row `1400 520 1900 556` | 171.1 (1.25x), std 51.4 | **151.4 (1.11x), std 57.7** | 136.4, std 62.4 | **halved**, std at 0.93x |
| cam05 pier face `1180 560 1280 680` | 144.8, std 23.6, mid 5.82 | **153.2, std 29.4, mid 10.23** | 145.5, std 38.1, mid 12.50 | std 0.62x -> **0.77x**, mid 0.47x -> **0.82x** |
| entablature `900 262 1020 296` / columns `680 280 1240 470` | 143.8 (1.20x) / 139.2 (1.22x), std 47.4 | **118.6 (0.99x)** / **114.8 (1.00x), std 58.2** | 120.2 / 114.3, std 56.6 | both **closed** |
| vault field `900 380 1010 430` | 94.6 (1.56x) | **46.1 (0.76x)** | 60.6 | closed then **over-darkened** |
| water reflection `900 760 1020 840` | 144.7, std 30.6, sat 0.396 | **135.3 (1.05x), std 35.0 (1.02x), sat 0.163** | 128.6, std 34.2, sat 0.250 | Gate 4 water: level/std land, sat 0.65x |
| **sunlit attic hold** `900 222 1020 256` | sat 0.488 (0.94x), hue +1.6 deg | **sat 0.460 (0.89x)**, hue -0.2 deg | sat 0.518, hue 38.0 | hue PASS, **sat hold BREAKS** |

Seven of the ten close or halve the deficit round 12b attributed to lighting; the two that do not are QA-13-1 (hue) and the sunlit-attic sat hold, and the vault field over-shoots to 0.76x.

## 2. The carried lighting items

* **QA-12b-1 olive cast — NOT closed, worse at cam02. Owner viewer, not the bake.** G > R on the 12b crops: cam02
  **16.0 -> 19.7 %**, cam06 **21.9 -> 20.2 %** against Phase 5 **0.1 / 9.7 %** (cam01 2.1 -> 0.6 %, cam05 5.3 -> 5.1 %). Not a
  brightness artefact — per luma bin on the cam02 building crop the baked frame is **30.9 % vs the reference's 2.3 %** at
  luma 40-60 and 37.7 % vs 5.4 % at 60-90 — and not the lightmaps either, since the same build in `lighting=direct` is as
  green or greener in every bin. `sky.diffuse` did not buy what bake item 8 predicted.
* **QA-12b-2 S-colonnade blow-out — halved, still open.** Wall mean **201-221 -> 170.8** vs Phase 5's 139.3 (1.23x); the
  panels do shade now (`hp9` 5.83 -> 27.71 vs 26.32, std 9.07 -> 35.00 vs 53.32). At 100 % (r2c3) it still reads as a flat
  cream field with a pasted rectangle checker where the reference is deep shade behind a tree mass.
* **QA-12-3 flatness — mostly closed:** columns std 0.84x -> 1.03x, capital row 0.82x -> 0.93x, entablature 1.06x -> 1.16x,
  cam05 pier mid 0.47x -> 0.82x. **Sunlit-attic saturation FAILS its hold**, 0.94x -> **0.89x** (0.460 vs 0.518, luma 1.03x).
* **QA-12-4 per-instance variation — improved, not closed.** cam01 shaft CV **0.041 -> 0.088** south, **0.133 -> 0.187**
  north, vs Phase 5's 0.469 / 0.539 (an upper bound dominated by tree shadow). The tree shadow *is* in the maps — cam03's
  near column carries real dappled leaf shadow — but the cam01 south row is still uniform.

## 3. The bake's own open questions

| question | answer |
|---|---|
| cam04 coffer field: black or lit? | **Black — QA-13-2, a lightmap defect, not the Gate 1 draw order.** Field mean **24.3 vs 60.7 = 0.40x**, soffit 24.4 vs 48.2 = 0.51x, **p10 0.00**, **37.8 % of pixels below luma 8** where Phase 5 has 0.0 % and p10 27.8. The ribs are lit (their own `gate3_relaid` map, range 30.17); it is the coffer beds — `ARCH_rotunda_plaster_ceiling_merged`, max **0.72** over 4.9 % non-zero texels — that render black, and the rib/coffer mesh is visibly in front and correct. **RE-BAKE.** |
| drum band; near-tree shadows | **Neither is a defect.** Drum band cam01 140.4 vs 134.9 = **1.04x**, cam06 157.1 vs 150.1 = **1.05x** (the near-black merged map is on interior faces; the visible band is the ORN slot instances). Near-tree shadow *is* in the maps (cam03 dapple); the cards are wrong-coloured only because the vertex irradiance is not applied — re-measure after COLOR_0. |
| `ENV_tree_broadleaf_06` in a city block; `ENV_lagoon_bed` 3.5 % non-zero | **Expected, on record** (ENV placement, faithful to Phase 5; the bed is under the restored water plane). Neither is visible at the six stations. |
| any other surface black where Phase 5 has light | None. One went the *other* way: the colonnade roof soffit `1400 556 1900 580` is **177.5 vs 105.7 = 1.68x**, a light leak. |

## 4. The cam01 six tiles at 100 % (`renders/web/tiles/round13b/`)

| tile | what the tile shows | owner |
|---|---|---|
| r1c2 | **The gain.** Attic returns, frieze, dentils and capitals carry real contact shade, the vault is concave and shaded, and the tile is structurally and tonally close to the reference. Two blemishes: soft low-frequency blotching on the rotunda ochre mass (consistent with its 17.4 cm/texel relaid map) and a green-grey cast on the right-hand attic return where the reference is warm brown. | — / viewer |
| r2c1, r1c1 | **QA-13-1, the largest colour error in the frame.** The north colonnade intercolumniations are a checker of saturated blue rectangles, RGB ~ **52/86/188**. **23.0 %** of the band `20 520 540 645` is B > R + 20 against **3.9 %** at Gate 2 and **0.0 %** in Phase 5, and **96.4 %** of those pixels are **bit-identical between `lighting=baked` and `lighting=direct`**, so the surface takes no light from either path. It is not the background sky (the sky 30 px above is 181/204/222) and it is not the bake. Best guess: the backdrop plane QA-12b recorded as "untextured flat grey" now reading blue, or a material the Gate 3 split left untouched. The same blue band is at cam05 behind the colonnade and across the cam06 backdrop. **Identify the surface before Gate 4.** | viewer / export |
| r1c3 | A saturated blue strip along the south colonnade roof line — same defect, same family. r2c3: QA-12b-2, the S-colonnade wall still a flat cream field with a pasted panel checker (§2). | viewer / export |
| r2c2, r2c3 | The reflection is coherent and unbroken where the reference is cut into ripple streaks; the box numbers land (1.05x lum, 1.02x std) but the micro-structure is missing and the reflection is too dark and desaturated (sat 0.65x). Gate 4. | viewer |
| r1c1, r1c3, r2c1-2 | Colonnade-roof canopy and the south colonnade tree absent (the 127 suppressed impostor carriers); the shoreline planting is blue-and-yellow angular confetti (no vertex irradiance). **Both expected.** | export |
| all six | **No lightmap seam at any UV2 island edge, no slot bleed between adjacent ORN instances, no texel blockiness on the relaid assets at 100 %, no encoding banding in the shade (the darkest scored box is the vault field at 46.1 and shows no stepping), no double shadow from the sun's specular.** | — |

## 5. Name sweep, budget, performance

**Name sweep:** the export engineer's Gate 3 r2 sweep on the export set is **0 to explain** (docs/status.md, 2026-09-16). The viewer still carries the **127 `WEB_far_tree_billboard_*`** objects, declared `userData.pfaPlaceholder` and **hidden** here (`hiddenBoards: 127`) — the Gate 4 impostor carriers, on record, not a sweep hit.

**Budget at 2560x1440:** resident **1 677.8 MB** = textures **1 171.6** (28.4 MB under the 1 200 MB line, impostors not yet loaded, the 2K -> 1K lever unspent) + render targets 443.8 + geometry 62.4; load **629.1 MB in 5.82 s**; 73/88 materials matched (the 15 unmatched are the foliage set, rule 7), 62/62 sets, 0 failures, 0 colour-space conflicts. **Performance:** hero **269 draws of 400**, GPU **2.3 / 3.9 ms** (uncapped 435 fps), worst cam06 291 draws / 2.4 / 4.1 ms; presented **39-45 fps** (frame median 22.2-25.8 ms), display bound not GPU bound — the lead should say whether the 6a >= 45 fps target means presented or GPU cost. Flag: the two 4x-MSAA composer targets (166 MB at 1440p) are resident although `post=none`.

## 6. Scores

Parity caveat, bigger than the brief assumed: **only station 1 has a reference rendered from the lighting the lightmaps
were baked from.** 3 and 5 are Eevee round-09, 6 is round-09 Cycles with no compositor, and **2 and 4 are round-09 Cycles
frames that predate LIGHT r18 and the shade-fill-off** — the cam02 reference still shows the violet shafts and blue soffits
round 10b recorded as fixed (QA-10-12). So 2 and 4 are **provisional** too: extend the Cycles references the lead is rendering for 3 / 5 / 6 to **2 and 4** (none had landed when this was written).

| row | 01 hero | 02 NE 3/4 | 03 colonnade | 04 ceiling | 05 S lawn | 06 aerial |
|---|---|---|---|---|---|---|
| Silhouette match | 4 | 3.5 | 2.5 | 3.5 | 3.5 | 3.5 |
| Proportion | 4 | 3.5 | 3 | 3.5 | 3.5 | 3.5 |
| Ornament fidelity | **4** (3.5) | 3 | 3 | **2** (2.5) ✗ | **3** (2.5) | 2.5 |
| Material realism | 3.5 | 2.5 | **3** (2.5) | **2** (2.5) | 3 | 2.5 |
| Edge wear | **3.5** (3) | **2.5** (2) | **2** (1.5) | 1 | **2.5** (2) | 0.5 |
| Lighting mood | **3.5** ✗ | **2** | **3** | **1.5** ✗ | **3** | **2** |
| Water reflection | **2.5** | n/a | n/a | n/a | 2.5 | **2** |
| Repetition visibility | 3 | **2.5** (2) | **2.5** (2) | 2 | 2.5 | 2 |
| Scale cues | **2.5** ✗ | **2** | 2.5 | 3 | 2.5 | 2.5 |
| **average** | **3.39** | **2.69** | **2.69** | **2.31** | **2.89** | **2.33** |
| round 09 (Phase 5) | 3.67 | 2.94 | 2.56 | 2.81 | 3.06 | 2.67 |
| **delta** | **-0.28** | **-0.25** | **+0.13** | **-0.50** | **-0.17** | **-0.34** |

Previous value in brackets where a row moves (round 12b for the material rows, round 11 otherwise). Every station average is inside the 0.5 window; cam04 (2.31) and cam06 (2.33) are below the 2.5 floor. **Four rows are outside 0.5**: cam01 Lighting mood (-1.0, QA-13-1 + the blue foliage) and Scale cues (-1.0, the absent impostor trees, expected at Gate 4); cam04 Lighting mood (-1.5) and Ornament fidelity (-1.0), both the black coffer field.

## 7. Verdict

**LIGHTMAPS ACCEPTED, with one re-bake: `ARCH_rotunda_plaster_ceiling_merged`.** The maps do what they were baked for:
the hero lands at 0.971x of the Cycles hero with its shadow end on the reference's, 16/16 own maps and 988/988 slots
attach, every station's MAE falls, and seven of the ten acceptance boxes close or halve the deficit round 12b attributed to
lighting — with no seam, no slot bleed and no encoding artefact at 100 %. The one unusable map is the rotunda plaster shell
(max 0.72, 4.9 % non-zero; cam04 at 0.40x with 37.8 % of the coffer field below luma 8): re-bake it with the visible shell
split from the merged mass's interior and backing faces, or on its own relaid UV2. No other asset needs a re-bake.
Gate 4 is **not** judged here (post, planar water, impostors and the near-tree vertex irradiance are not all in). Carried
into Gate 4, in order of hero cost: **QA-13-1** the lighting-independent blue surface in the colonnade bays (viewer /
export — identify it first); **QA-13-2** the plaster-shell re-bake; **QA-12b-1** the olive cast, neither the asset nor the
lightmap and not fixed by `sky.diffuse`; the **sunlit-attic sat hold at 0.89x**; **QA-12b-2** the S-colonnade wall at
1.23x; the colonnade-roof light leak at 1.68x; the vault field at 0.76x; water ripple micro-structure and reflection
saturation (0.65x). Accepted: QA-12-2 the dome cap. Expected, not scored as defects: post, the 127 far-tree impostors, the
14 near-tree vertex irradiance (blue foliage at every station), mist.
