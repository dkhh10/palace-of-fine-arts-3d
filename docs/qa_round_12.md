# QA round 12 — Phase 6 **Gate 2**: the baked PBR set alone, 2026-09-15. **GATE 2: FAIL** (one row).

Scored on the viewer engineer's 19:09 capture (`materials=pbr`, `lighting=direct` — full sun + PMREM irradiance, **no
lightmaps, no shadows, no compositor** — both placeholder sets hidden), six stations 1920x1080, manifest
`pfa-phase6/3`, 60 sets. No Blender, no Chrome. The cam01 tiles did not exist for Gate 2 and were cut here
(`scripts/qa_r12_probe.py tiles` -> `renders/web/tiles/gate2/`, viewed at 100 %); two 100 % crops per station 02-06 from
the same script. New: `scripts/qa_r12_probe.py`, `scripts/qa_r12_gate.py` -> `renders/web/round12_gate.png`.

**Only Material realism / Edge wear / Repetition are scored** (geometry frozen at Gate 1; Lighting mood, Water and the
geometry rows unscored). **Luminance is not a material metric at this gate** and is never scored: with no shadow and no
bounce every shaded surface is lifted (whole-building lum 1.16x the Phase 5 hero, cam03 3.0x, cam05 1.33x). Hue and
saturation on *sunlit* stone, and the spatial variation of the albedo, are the material metrics.

## 1. What the bake got right — say this first

* **Sunlit stone is correct.** `sunlit attic 900 222 1020 256`: hue **39.9 vs 38.0** (+1.9 deg), sat **0.503 vs 0.518 =
  0.97x** of the round-10b Cycles hero. That is the cleanest material box in the frame (direct sun in both, no shade
  term) and it lands.
* **The frame-chroma defect QA-10b-1 is gone.** Whole building `700 160 1240 480` sat **0.532** against the r10b render's
  0.636 (**0.84x**) — i.e. **1.02x of photograph 169's 0.521**, where r10b was 1.22x. Hue **39.0 vs 39.4**.
* **The round-9 attic photo projection survives the bake and is registered.** Attic mid-band (9-33 px) 9.2-19.2 against
  Phase 5's 13.9-14.9 (0.67-1.29x); no seam, no double image, no shifted band at 100 % in tile r1c2.
* **ORN relief is real.** 33 prototypes replace their Gate 1 normal and keep the Gate 1 AO; the procession frieze,
  capitals, maidens, urns and keystones all read as relief at 100 % at cam01, cam05 and cam06. No ORN set is missing.
* **QA-11c-2 is closed on both halves as an attachment question.** All ten `MAT_EXP_ENVBD__*` backdrop sets attach after
  the `-km` re-pack (cam06 linear ratio 2.837 grey -> **1.548** pbr); the attic pedestals/balustrade take their texture
  (`700 200 780 240` std 50.5 / hp9 27.6 against Phase 5's 32.2 / 15.9). 64 of 74 materials textured, 0 failures,
  0 colour-space conflicts, `without_uv1` empty, the only 10 unmatched are the foliage materials (rule 7, by design).
* **cam02 is better than its Phase 5 reference.** The round-09 frame's piers are violet (box hue **262.1**, sat 0.182);
  the export is warm (**hue 47.1**, sat 0.545). QA-10-12's magenta shaft cluster does not exist here.

## 2. The cam01 six-tile pass at 100 %, and the station crops

| tile / crop | box | what is wrong | owner | material or lighting |
|---|---|---|---|---|
| r1c2 | 640 0 1280 540 | Attic, dome, entablature all read cleaner than Phase 5: no grime in the dentil and modillion recesses, no contact darkening under the cornice. Albedo detail is present (mid 0.67-1.29x); what is missing is occlusion. | — | **lighting** (Gate 3) |
| r1c2 | 900 90 1020 130 | **QA-12-2** dome cap: sat **0.334 vs 0.464 = 0.64x**, a smooth near-white lid. The baked albedo is near-white by construction (`ARCH_rotunda__dome_membrane` mean 0.911/0.919/0.671) and roughness 0.43 takes a hard sky specular with no shadow. | materials / bake | **material** (QA-10-8 carried, now flatter) |
| r1c3, r2c3 | 1560 540 1760 640 | **QA-12-3** south-colonnade back wall and its panels: **hp9 0.6-0.8** against **13-19** on the rotunda attic in the same frame, std 8.4 over `1600 590 1670 635`. No albedo variation reaches this surface. The two colonnade atlases pack **0.16 UV coverage** (every other ARCH group 0.40-0.69) and are the only ARCH groups at 3.8 cm/texel. | bake | **material** |
| r2c1, r2c2, r2c3 | y 540-1080 | Water is still a perfect mirror against a rippled reference. | viewer | lighting (QA-11-5, Gate 4) |
| r2c1, r2c2 | shore band | Shrub and leaf cards read as pale blue-white chips: the 10 foliage materials have no Gate 2 set (rule 7) and under sky-only irradiance with no shadow the cards blow out. | env / viewer | lighting + no PBR set (Gate 3/4) |
| r1c1, r1c3 | 0 0 640 540 / 1280 0 1920 540 | Colonnade-roof canopy sparse, south-colonnade tree absent — the 127 suppressed impostor carriers. | env | geometry (QA-11-1 / -3, Gate 3) |
| cam03 L | 420 120 1060 480 | Near column at 5.5 m: a smooth cream cylinder with flute gradients and no concrete grain. The colonnade set ships `normal.texture: null`. | bake | **material** |
| cam03 R | 640 560 1280 920 | Colonnade walk paving reads cold grey-blue (hp9 3.2) where the set is `paving_stone` / `paving_stone_worn`. | bake | material (hue) + lighting |
| cam04 | 560 200 1200 560 | Coffer soffits read navy-grey; only the rosettes are gold. Stone box sat 1.33x Phase 5 but the field is sky-lit. | lighting | **lighting** (no lightmap) |
| **cam05 L** | 1100 500 1420 720 | **QA-12-1, BLOCKER.** Pier face, attic wall and spandrel are perfectly smooth pale ochre at 15-25 m: mid-band (5-21 px, both at the reference's native 1280x720) **2.68 vs 10.11 = 0.27x**, std **12.3 vs 38.3**; attic wall 2.87 vs 9.79. This is the "clean CAD / plastic" read the project's non-negotiables reject. | bake | **material** |
| cam06 R | 1180 120 1820 480 | Backdrop ground and hill take a tint but read as flat facets (hp9 0.2-5.0); backdrop forest is dark faceted blobs. | env / bake | geometry + material (Gate 3/4) |

**Root cause of QA-12-1, from the manifest, not from an impression.** The albedo is a **DIFFUSE colour-only** bake, so the
bump-driven shading that produces most of the Phase 5 concrete's streaking is discarded; and the map that should carry
it back is absent — **7 of the 12 ARCH/ground sets ship `normal.texture: null`** (`ARCH_colonnade_north`,
`ARCH_colonnade_south`, `ARCH_rotunda__concrete_inner`, `ARCH_rotunda__dome_membrane`,
`ARCH_rotunda__plaster_ceiling_rib`, `ARCH_site__concrete_podium`, `ARCH_site__paving`; plus 7 backdrop sets).
Measured independently: the baked `concrete_ochre` albedo itself carries mid(5-21 texel) **5.5** against the 10.1 the
Phase 5 frame shows on the same pier, so even a perfect 1:1 magnification could not reach parity from the albedo alone.
Texel density (export/README Gate 2 finding 2) makes it worse but is not the whole of it. `pbr.js` already sets
anisotropy 8, so filtering is not the cause.

**Per-instance variation is gone by construction** (export/README Gate 2 finding 3: one texture per shared mesh, baked
through the placement nearest a station). Colonnade shaft-to-shaft coefficient of variation at cam01: **0.028 south /
0.089 north** against Phase 5's **0.072 / 0.319**. Some of the Phase 5 spread is shadow, but nothing in the Gate 2 set can
differentiate two instances; the plan puts that in the Gate 3 per-instance lightmap slot.

## 3. Boxes on cam01 vs the round-10b Cycles hero (luminance reported, never scored)

| box | viewer hue / sat / lum | ref hue / sat / lum | sat ratio | read |
|---|---|---|---|---|
| sunlit attic 900 222 1020 256 | 39.9 / 0.503 / 182.7 | 38.0 / 0.518 / 187.7 | **0.97x** | material PASS |
| shaded attic 1110 225 1150 260 | 40.9 / 0.599 / 137.6 | 41.2 / 0.628 / 122.1 | 0.95x | lighting (lum 1.13x, no shade) |
| entablature 900 262 1020 296 | 39.2 / 0.560 / 153.2 | 39.2 / 0.777 / 120.2 | 0.72x | lighting (cornice shadow missing) |
| columns 680 280 1240 470 | 38.0 / 0.589 / 140.0 | 39.1 / 0.712 / 114.3 | 0.83x | lighting |
| **dome cap 900 90 1020 130** | 40.4 / **0.298** / 198.4 | 40.0 / 0.464 / 185.6 | **0.64x** | **material** (QA-12-2) |
| **whole building 700 160 1240 480** | 39.0 / **0.532** / 147.0 | 39.4 / 0.636 / 126.6 | **0.84x** = 1.02x of photo 169 | material PASS |
| attic pedestals 700 200 780 240 | 40.9 / 0.465 / 154.3 | 39.7 / 0.555 / 166.7 | 0.84x | QA-11c-2 closed |
| podium band 820 520 1100 560 | 37.1 / 0.391 / 163.4 | 38.6 / 0.548 / 141.9 | 0.71x | lighting; mid-band 16.9 vs 20.2 = 0.84x |
| vault field 900 380 1010 430 | 39.9 / 0.626 / 88.4 | 40.2 / 0.701 / 60.6 | 0.89x | lighting (1.46x lum) |

Stone-region saturation ratio per station (viewer / Phase 5): 01 **0.84x**, 02 **3.00x** (the reference is violet — the
export is right), 03 0.54x, 04 1.33x, 05 0.66x, 06 1.33x. Hue is within 2 deg at 01 / 04 / 05, +6 to +8 deg at 03 / 06.

## 4. Score table — three rows only (round 09 -> **round 12**, delta)

| row | 01 hero | 02 NE 3/4 | 03 colonnade | 04 ceiling | 05 S lawn | 06 aerial |
|---|---|---|---|---|---|---|
| Material realism | 3.5 -> **3.5** (0.0) | 2 -> **2.5** (+0.5) | 2.5 -> **2** (-0.5) | 3 -> **2.5** (-0.5) | 3.5 -> **2.5** (**-1.0**) | 2.5 -> **2.5** (0.0) |
| Edge wear | 3.5 -> **3** (-0.5) | 2.5 -> **2** (-0.5) | 1.5 -> **1** (-0.5) | 1 -> **1** (0.0) | 2 -> **1.5** (-0.5) | 0.5 -> **0.5** (0.0) |
| Repetition visibility | 3 -> **2.5** (-0.5) | 2.5 -> **2** (-0.5) | 2 -> **1.5** (-0.5) | 2.5 -> **2** (-0.5) | 2.5 -> **2** (-0.5) | 2.5 -> **2** (-0.5) |

**Parity fails on exactly one row: cam05 Material realism, -1.0 against a window of 0.5.** Every other row is at or
inside 0.5, though Repetition sits on the boundary at all six stations. cam03 and cam05 are scored against Eevee
round-09 frames, which are not luminance parity targets; the texture measurements above are valid against them because
Eevee evaluates the same procedural material, and the root cause (`normal.texture: null`, colour-only albedo) is a
manifest fact that needs no reference at all.

## 5. Budget and performance — PASS on every line

Resident **1 333.8 MB** at 1440p (textures 855.6 + render targets 437.5 + geometry 40.6); 1 204.8 MB at 1080p. The Gate 2
PBR set itself is **566.2 MB**, and the budget lines whose assets exist today measure 733.5 MB against the 1 200 MB
texture budget — room for the Gate 3 lightmaps and impostors. *(The brief's "textures 921 MB" does not match the
capture's 855.6 MB; the capture is the source.)* Hero **267 draws of 400**, GPU **1.7 ms** median / 2.7 p95; worst
station cam06 287 draws / 1.9 ms. Load 483.2 MB in 4.17 s. 178 attachments, 168 unique files, all `RGBA_ASTC_4x4`;
93 superseded Gate 1 textures disposed, 155.2 MB freed; 0 failures.

## 6. Verdict

**GATE 2: FAIL.** One blocking material defect.

**QA-12-1 — ARCH stone carries no surface at walking distance. Owner: bake. Severity: blocker.** At cam05 the pier face,
attic wall and spandrel measure mid(5-21 px) **2.68 / 2.87** against Phase 5's **10.11 / 9.79** and std 12.3 vs 38.3; at
cam03 the near column at 5.5 m has no grain; at cam01 the south-colonnade back wall measures hp9 0.6-0.8 against 13-19
on the rotunda attic in the same frame. Cause: the albedo is a DIFFUSE colour-only bake and **7 of 12 ARCH/ground sets
ship `normal.texture: null`**, so the material's bump — which is where most of the Phase 5 concrete's streaking lives —
is in neither map.
**One-line fix:** bake the ARCH/ground materials' own bump into a normal map for all twelve groups (no hi twin needed:
the same `--gate2` pass already does it for `concrete_ochre`), and re-pack the two colonnade atlases whose UV1 coverage
is 0.16.
**Acceptance:** cam05 `1180 560 1280 680` mid(5-21) **>= 7.0** and std **>= 25** against Phase 5's 10.11 / 38.25, and
cam01 `1600 590 1670 635` hp9 **>= 4.0**; sunlit-attic hue and sat must stay within today's 0.97x / +1.9 deg.

Not blocking, to fix or accept with the same re-bake: **QA-12-2** dome cap sat 0.64x (QA-10-8 carried; owner materials —
the membrane's near-white albedo is faithful, the extra flatness is roughness 0.43 against a sky-only specular).
**QA-12-3** colonnade atlas 0.16 UV coverage (folded into the QA-12-1 fix). **QA-12-4** per-instance variation is
absent by construction (every Repetition row -0.5); it is Gate 3's per-instance lightmap slot, not a re-bake.
Carried unchanged: QA-11-1 / -3 (impostors) and the foliage sets at Gate 3, QA-11-5 (water) and QA-11d-1 / -2 at Gate 4.
