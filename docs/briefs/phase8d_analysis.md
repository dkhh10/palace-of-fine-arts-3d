# Phase 8d PART 0 — backdrop analysis (env builder, 2026-09-19, branch `phase8d-env`). CPU only: no Blender, no Chrome, no render.

Method: `scripts/env_probe_backdrop.py` — a numpy z-buffer that rasterises the **Gate 1 export itself**
(`export/out/gate1/{env,arch,ground,orn}.gltf`, the unpacked pair that still carries object names) through the six
`qa_cameras.py` stations with the viewer's own camera model (`web/src/blenderCamera.js`: 36 mm horizontal fit, `ndc_y -= 2·shift_y·aspect`),
plus the viewer's water plane at WATER_Z. Silhouettes registered against `renders/web/gate9_cam*.png` (checked at 480 px; rotunda, colonnade
and shore land on the capture). Two bounds per station: **solid** = leaf cards/impostors occlude as opaque (lower bound on backdrop);
**foliage-off** = the same raster with `far_impostor/near_tree/shrub` dropped (upper bound). Truth is between; alpha is ~50 % on those cards.

## 1. What the six stations see of the backdrop (% of a 1920x1080 frame; px are 1920x1080 px)

| station | backdrop solid → foliage-off | the groups that own it (solid px) | where in the frame |
|---|---|---|---|
| cam01 hero | **1.13 % → 4.66 %** | building 13 084, **skylight 8 120**, roof 1 176, door 740, gulls 392 | one band y 524–670, 75 % of it in tile **r2c1** |
| cam02 | 1.63 % → 3.88 % | building 30 000, skylight 2 544, gulls 832 | tile r2c3 (8 217 of 8 443 px @960) |
| cam03 | 0.04 % → 0.09 % | building 568 | 50x70 px through one arch, tile r2c2 |
| cam04 | 0.00 % | — | — |
| cam05 | 0.52 % → 4.19 % | building 4 700, roof 3 540, skylight 1 584, gulls 928 | band y 654–786 spread over r2c1/r2c2/r2c3 |
| cam06 aerial | **34.89 % → 40.30 %** | roof 259 656, forest 154 952, lawn 152 440, building 148 572 | whole top row: r1c1 53 %, r1c2 44 %, **r1c3 92 %** of the tile |

**`backdrop_forest` (99 640 tris, 11 % of ENV) is visible at cam06 only** — 0 px at cam01/cam05, 44 px at cam02.
**The hero's N-colonnade wall is `backdrop_building` + `backdrop_skylight`: 21 204 px (1.02 % of the hero).**
The "dark rectangles" QA 17 names are the hall's 102 glazed bays (`backdrop_skylight`, 1 236 tris) — 38 % of the hero's backdrop px.

## 2. Why it reads flat — measured, not opinion
* Texel density of the Gate 2 backdrop bake (1024², ~70 % fill, area from the glTF):
  **building 0.79 texels/m** (1 170 168 m² on one 1K atlas), roof 1.87, forest 0.35, lawn 0.18, skylight 15.2.
* The hall's east wall is 146–154 m from the hero → **7.0 px/m on screen**. One baked texel spans ~9 screen px. Nothing
  finer than 1.3 m can survive the bake; `MAT_backdrop_building` already has 3 image nodes and they are averaged away.
  Raising `SIZE_BACKDROP` to 2048 buys 1.58 texels/m — still 4.4x short. **A bigger bake cannot fix this.**
* cam06 top row vs ref 105: luma **0.435 vs 0.820**, saturation **0.387 vs 0.073** (5.3x too saturated), high-frequency
  energy (|laplacian|) **0.025 vs 0.118** (4.7x too little). The reference city is hazed almost to white.
* Hero wall band vs ref 169: saturation **0.654 vs 0.431**, luma sd **0.151 vs 0.212**, hf **0.126 vs 0.248**.
* ref 169 at 100 % (`/tmp/hero_wall_pair.jpg`, viewer over reference): **behind the north colonnade the photograph has no lit
  wall at all** — a dark tree belt and deep shade fill every intercolumniation (luma 0.40–0.49, sd 0.18–0.22). We draw a
  continuous sunlit olive field with 102 regular dark panels. That is the hero defect, and it is as much *placement* as texture.

## 3. The export pin — the binding constraint (`export/gate1_set.py:642,654`)
`env_so_far` **includes the backdrop groups**, so every backdrop triangle moves `tree_allow` and can re-cut the near/far tree split.
Slack today: `near_tris_budget` 398 894 − `near_tris_used` 391 908 = **6 986 triangles**; the cheapest thinned candidate that
could be pulled in is 12 892.
→ **Backdrop tri delta of −5 900 … +6 986 keeps near 20 / far 127 byte-identical with `CLASS_BUDGET["ENV"]` untouched at 902 000.**
Outside that window, `CLASS_BUDGET["ENV"]` must move by exactly Δ (the 8a precedent) or the impostor placements re-index and the atlas re-bakes.
Backdrop UV1 is generated at **Gate 2** from the merged geometry (`gate2_common.py:48`), so a material-only change reproduces UV1 exactly.
A tiled UV0 in metres would have to be authored on the source objects with one shared layer name (640 objects are joined) — it does not
disturb UV1, but it needs `grey()` in `gate1_set.py` to stop writing a flat 0.5 grey material, which is export-engineer work, not mine.

## 4. Tree options, costed
| option | tris | Δ vs 99 640 | texture | pin / lockstep | seen by Cycles |
|---|---|---|---|---|---|
| (a) band-atlas billboards for the crowns within 450 m (59 % of forest tris, ~1 030 crowns) | 2 060 + 40 580 kept | **−56 968** | reuses the 8b band atlases, +0 MB | **breaks the window** → CLASS_BUDGET 902 000→845 032; needs a *second* viewer band path for a merged group (bake+export+viewer lockstep) | yes (blend changes) |
| (b) Sapling LOD2 for the nearest ring + impostors beyond | ~330 crowns x ~3 k | **+1 M** | none | impossible inside a 902 k ENV budget | — |
| (c) textured canopy mass: keep the 57-tri lobes, fix the material | 99 640 | **0** | needs a tiled UV0 (the 1K bake gives 0.35 texels/m) | **none** — byte-identical | yes |
Geometry is not the cam06 defect: a crown is ~50 px there (6.7 px/m at 400 m) and the band atlas's {0°,20°,40°} rows do cover cam06's
22.8° look-down, but the measured misses are tone (−0.39 luma), saturation (5.3x) and detail (4.7x), none of which more triangles buy.

## 5. Recommendation — three items, in pixel order, all inside my own files
* **R1 (zero tris, zero pin risk, biggest measured win).** Rework `MAT_backdrop_building/_skylight/_roof/_forest/_lawn` so everything they
  carry is *low frequency* — the only band a 0.2–1.9 texel/m atlas can hold: distance haze toward the sky colour (bakeable, because it is a
  fixed function of world position), per-building albedo spread, and a shaded, desaturated value on the hall's east face with the glazed-bay
  contrast dropped. Targets: cam06 top row luma 0.435→~0.80, sat 0.387→~0.10; hero wall sat 0.654→~0.43.
* **R2 (the reference's own answer at the hero).** A tree belt on the hall's east face, capped at **≤ 6 986 tris** (~120 crowns at 57 tris)
  so the pin stays byte-identical. Covers most of the hero's 21 204 backdrop px and the cam05 band.
* **R3 (deferred, lead's call).** The high-frequency half — a tiled facade/canopy/roof atlas on a new UV0 — is a joint env+export change;
  R1+R2 first, measure, then decide. **Rejected:** a viewer-side fog (Cycles would not see it) and `SIZE_BACKDROP` 2048 (1.58 texels/m).
* **Cycles:** R1 and R2 live in `assets/materials.blend` + `assets/environment.blend`, so the end-of-Phase-8 4K hero shows them.

## 6. Cost
* GPU: ENV Eevee previews at cams 1/5/6 ≈ 6–8 min a round, 2–3 rounds → **≤ 25 min**. Gate 2 re-bake of the 4–5 changed
  `MAT_EXP_ENVBD__` groups, 3 maps at 1024² (16/16/4 spp) → **8–15 min**. Nothing else is a GPU job.
* ENV budget delta: **0** for R1, **≤ +6 986** for R2 → `CLASS_BUDGET["ENV"]` stays 902 000 and near 20 / far 127 hold.
* Export scope: Gate 1 re-run only to *prove* the pin (uv1 coverage/tiles/groups, arch/orn/ground byte-identical, near 20 / far 127);
  Gate 2 bake for the changed backdrop groups only; `manifest_v2` + `manifest_v4` + `budget_doc`; `sync_main.sh`; `tiers.py` (desktop,
  mobile, no-pack) + `verify_glb --gate5` + `tiers_test.mjs`. **No Gate 3** — the backdrop has no lightmap and no impostor row changes.
