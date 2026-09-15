# QA round 12b — Phase 6 **Gate 2** re-check after QA-12-1, 2026-09-15. **GATE 2: PASS**

Scored on the viewer engineer's final 21:41 capture (`materials=pbr`, `lighting=direct` — full sun + PMREM irradiance,
**no lightmaps, no shadows, no bounce, no AO, no compositor**, both placeholder sets hidden), six stations 1920x1080,
KTX2 detail set at gain 1, 62/62 sets used, 0 failures. No Blender, no Chrome. The `renders/web/tiles/gate2/` tiles were
stale (19:11 against 21:41 frames) and were re-cut here; `renders/web/gate2_pair_cam0K.png` regenerated. New:
`scripts/qa_r12b_probe.py` (accept / control / green / shafts / budget), `scripts/qa_r12b_gate.py` ->
`renders/web/round12b_gate.png`. Band-pass metrics are `web/tools/qa12_boxes.py`'s, the definitions round 12 stated.

**Only Material realism / Edge wear / Repetition are scored** (geometry frozen at Gate 1). **Luminance is not a material
metric at this gate.** Hue, saturation, texel density and grain *presence at 100 %* are.

## 1. QA-12-1 — the acceptance boxes, and the control that settles the attribution

| box | round 12 | **round 12b** | Phase 5 | target | verdict |
|---|---|---|---|---|---|
| cam05 pier `787 373 853 453` @1280x720 | mid 2.68 | **7.05** | 12.92 | >= 7.0 | **PASS** |
| the same, std | 12.3 | **22.87** | 38.25 | >= 25 | short by 2.1 — see below |
| the same, hp9 | — | **8.14** | 17.00 | — | mean 144.8 vs ref 145.4 |
| cam01 S-colonnade wall `1600 590 1670 635` | hp9 0.6-0.8 | **hp9 5.83** | (ref box is tree shade) | >= 4.0 | **PASS** |
| cam01 sunlit attic hold | sat 0.97x, +1.9 deg | **sat 0.94x, +1.6 deg** | 0.518 / 38.0 | hold | hue PASS, sat drifts 0.03 |

**The control.** Gate 2 renders with no shadow, no bounce and no AO, so a box the sun reaches in *both* frames compares
material to material, and a box the reference has in shade compares material+shade to material alone. Split that way the
numbers separate cleanly (viewer / Phase 5, `qa_r12b_probe.py control`):

| lit in both frames | mid(5-21) | hp9 | std | | reference in shade | mid | hp9 | std |
|---|---|---|---|---|---|---|---|---|
| sunlit attic | **1.10x** | 0.94x | 1.17x | | entablature (cornice shadow) | 0.88x | 1.37x | 1.06x |
| attic pedestals | **1.33x** | 1.64x | 1.49x | | shaded attic | 0.75x | 1.36x | 0.81x |
| dome cap | 0.99x | 0.88x | 0.91x | | podium band | 0.74x | 0.88x | 0.77x |
| | | | | | cam05 pier face | **0.47x** | 0.63x | 0.62x |
| | | | | | colonnade pedestal (deep shade) | **0.44x** | 0.50x | 0.35x |

Where the light is the same, the baked material is **at or above** the Phase 5 amplitude on every box. Where the
reference has shade the export cannot have, it is 0.35-0.81x, and the deficit grows with the depth of the shade. Two
independent facts close it: the export measured the baked `concrete_ochre` albedo's own ceiling at **mid 5.5** on this
pier, and the viewer now delivers **7.05** — *more* than the albedo alone holds, because the detail layer and the
low-frequency atlas normal add to it; and the source `*_disp` maps are 8-bit JPEGs whose texel-to-texel gradient
(0.00134-0.00173) is below the 1/255 quantisation step, so no honest derivation yields more (export/README, on record —
a gain knob would be invented relief). **The remaining cam05 std is the shade and occlusion term. It is not a Gate 2
defect. QA-12-1 is CLOSED on its material share; the residual moves to Gate 3's lightmaps.**

## 2. QA-12-2 / -3 / -4

* **QA-12-2 dome cap — OPEN, not blocking, unchanged in kind.** sat **0.318 vs 0.464 = 0.69x** (was 0.64x), lum 1.13x.
  The amplitude is now at parity (mid 20.07 vs 20.30 = 0.99x), so this is purely the near-white membrane albedo against
  a sky specular at roughness 0.43, exactly as MAT r10 accepted it. At 100 % in tile r1c2 and the cam06 crop it is the
  most plastic-reading element in the set: a smooth white lid. Owner materials; the round-10 decision (one bounded
  round) stands, so it is carried, not re-opened.
* **QA-12-3 colonnade texel density — CLOSED numerically, watch at Gate 3.** The atlas split took the back wall from
  9.4 to 5.28 cm/texel and the instanced columns to 1.07 cm; hp9 on the acceptance box went **0.6-0.8 -> 5.83**, and at
  cam03 the near column at 5.5 m now shows fluting *and* grain (own-frame mid 15.6, hp9 7.2) where round 12 found a
  smooth cream cylinder. At 100 % the back wall still reads flat — but its mean is **200.9 of 255**, i.e. blown out by
  the missing shade; its own relative contrast (hp9/mean 2.9 %) against the sunlit attic's 12.9 % is a luminance-ceiling
  effect, not a missing texture. Lighting, Gate 3.
* **QA-12-4 per-instance variation — GATE 3 by construction**, as briefed. The detail layer is tiled in *world* space,
  so two instances of one mesh no longer sample identical texels at the grain scale, but their means barely move:
  cam01 shaft-to-shaft CV **0.041 south / 0.133 north** (Phase 5 0.469 / 0.539 on the same strip, overwhelmingly tree
  shadow — an upper bound, not a material target). Nothing in a Gate 2 set can differentiate two instances at the metre
  scale; that is the per-instance lightmap slot.

## 3. The cam01 six tiles at 100 %, and the station crops — every defect, new ones marked

| tile / crop | box | what is visible | owner | material or lighting |
|---|---|---|---|---|
| r1c2 | 640 0 1280 540 | Attic, frieze, maidens, dentils, capitals all read as relief and as weathered stone; no grime in the recesses and no contact darkening under the cornice. | — | **lighting** (Gate 3) |
| r1c2, cam06 c1 | 900 90 1020 130 | **QA-12-2** dome: smooth near-white lid, sat 0.69x. | materials | **material**, carried |
| r2c3 | 1380 545 1780 700 | **QA-12b-2 NEW.** The S-colonnade back wall reads as a flat cream field with a regular checker of cooler recessed panels (panel hue 36.7 / sat 0.217 / lum 221 against the wall's 40.4 / 0.362 / 205). The panels are real geometry on the same atlas; what makes them read as pasted-on rectangles is the 201-221 mean with no shade to land on. | viewer / lighting | **lighting** (blow-out), material share within ceiling |
| cam02 c1+c2, cam06 c1 | 560 90 1200 450 | **QA-12b-1 NEW, the largest visible defect in the set.** Every stone face the sun never reaches reads olive-green: cam02 RGB **107/125/107**, hue **119.4**, sat 0.143. **16.0 %** of cam02's building pixels and **21.9 %** of cam06's have G > R, against **0.1 %** in the Phase 5 Cycles hero. It cannot come from the asset: the baked `ORN_maiden_v1` and `ARCH concrete_ochre` albedos are R > G > B on **100.0 %** of their pixels. It is the sky-only irradiance through AgX with no bounce and no warm ground fill. | lighting / viewer | **lighting** (Gate 3) |
| r1c1, r1c3 | 0 0 640 540 / 1280 0 1920 540 | Colonnade-roof canopy sparse, south-colonnade tree absent — the 127 suppressed impostor carriers. | env | geometry (QA-11-1 / -3, Gate 3) |
| r2c1, r2c2, r2c3 | y 540-1080 | Water a perfect mirror against a rippled reference. | viewer | lighting (QA-11-5, Gate 4) |
| r2c1, r2c2, cam03 c2 | shore band | Foliage cards read as pale blue-white and sage chips; at cam03 the shrub bed is a shatter of angular chips. The 10 foliage materials have no Gate 2 set (manifest rule 7, named exception). | env / viewer | lighting + no PBR set (Gate 3/4) |
| cam04 c1 | 560 200 1200 560 | Coffer soffits dark olive, only the rosettes gold; the field is sky-lit with no bounce. | lighting | **lighting** (no lightmap) |
| cam03 c2 | 640 560 1280 920 | Colonnade walk paving now warm (hue 47.5, was cold grey-blue) with a visible joint grid and grain. Fixed since round 12. | — | — |
| cam06 c2 | 1180 120 1820 480 | Backdrop ground/hill textured but faceted; backdrop forest dark blobs; **the bay water plane is untextured flat grey (hp9 0.19-0.41)**. | env / viewer | geometry + water (Gate 3/4) |

**No new seams, no tiling repeat visible at 100 %, no colour-space error.** The re-laid atlases show no join anywhere in
the six tiles or the ten station crops; 0 colour-space conflicts, `without_uv1` empty, `flat_normal_constant` empty,
19/19 ARCH/ground sets ship a real normal (was 7 null), 33 ORN normals replaced, 95 superseded Gate 1 textures disposed.

## 4. Score table — Material realism / Edge wear / Repetition (round 09 -> round 12 -> **round 12b**)

| row | 01 hero | 02 NE 3/4 | 03 colonnade | 04 ceiling | 05 S lawn | 06 aerial |
|---|---|---|---|---|---|---|
| Material realism | 3.5 -> 3.5 -> **3.5** (0.0) | 2 -> 2.5 -> **2.5** (+0.5) | 2.5 -> 2 -> **2.5** (0.0) | 3 -> 2.5 -> **2.5** (-0.5) | 3.5 -> 2.5 -> **3** (-0.5) | 2.5 -> 2.5 -> **2.5** (0.0) |
| Edge wear | 3.5 -> 3 -> **3** (-0.5) | 2.5 -> 2 -> **2** (-0.5) | 1.5 -> 1 -> **1.5** (0.0) | 1 -> 1 -> **1** (0.0) | 2 -> 1.5 -> **2** (0.0) | 0.5 -> 0.5 -> **0.5** (0.0) |
| Repetition visibility | 3 -> 2.5 -> **3** (0.0) | 2.5 -> 2 -> **2** (-0.5) | 2 -> 1.5 -> **2** (0.0) | 2.5 -> 2 -> **2** (-0.5) | 2.5 -> 2 -> **2.5** (0.0) | 2.5 -> 2 -> **2** (-0.5) |

Delta is against round 09. **Every one of the eighteen rows is at 0.0 or -0.5 — inside the 0.5 parity window.** Per-row
attribution of the residual, as the brief requires: 01/03/05 Material realism and all six Edge wear rows are held down
by the missing shade, occlusion and contact darkening (**lighting**); 02 and 04 Material realism by the sun-less green
cast and the unlit coffer field (**lighting**); 06 by the faceted backdrop and flat bay (**geometry / Gate 4 water**);
every Repetition row that is still -0.5 is per-instance weathering, which is Gate 3's lightmap slot **by construction**.
**No row's residual is a material gap**, so no row is a Gate 2 failure.

## 5. Budget and performance — PASS on every line

Resident **1 433.6 MB** at 1440p (textures **953.5** + render targets 437.5 + geometry 42.6), up 99.8 MB on round 12 for
the per-mass atlases and the 2K concrete detail sets. Detail layer **33.6 MB** for 4 sets on 20 materials (the README's
19.95 MB plan was 1K; the two concrete sets ship at 2K). Textures sit **246.5 MB under** the 1 200 MB texture budget,
and the impostor 2K -> 1K lever (-200 MB) is still unspent for Gate 3. Hero **267 draws of 400**, GPU **1.8 ms** median /
3.1 p95; worst station cam06 287 draws / 1.9 ms; cheapest cam04 116 draws / 0.6 ms. Load **537.4 MB in 4.78 s**.
64/74 materials matched (the 10 unmatched are the foliage set, rule 7), 62/62 sets used, 181 unique files, all
`RGBA_ASTC_4x4`, 0 failures.

## 6. Verdict

**GATE 2: PASS.** QA-12-1 is closed on everything a material can carry: the acceptance mid and hp9 land, the grain is
present at 100 % on the cam05 pier and the cam03 near column, and where the light is equal the export matches or beats
the Phase 5 amplitude on every box. The cam05 std shortfall (22.87 of 25) is the shade term `direct` mode excludes by
construction, and the 8-bit source-height ceiling is on record: do not re-bake for it.

Carried into **Gate 3** (all lighting, none a Gate 2 defect): **QA-12b-1** the olive-green cast on sun-less stone (16-22 %
of the building pixels at cam02/cam06 — the single most damaging thing in the set to a photoreal read, and it needs the
bounce/ground fill, not a new bake); **QA-12b-2** the blown-out S-colonnade wall and its panel checker; QA-12-3's
remaining flatness; QA-12-4 per-instance weathering; QA-11-1 / -3 the impostor carriers and the foliage PBR sets.
Carried to **Gate 4**: QA-11-5 mirror water and the flat bay plane, QA-11d-1 / -2. Carried as accepted: **QA-12-2** the
dome cap at 0.69x (materials, MAT r10's one-round rule), and the sunlit-attic saturation drift 0.97x -> **0.94x**, which
is inside any material window but should not drift further — re-check it at Gate 3.
