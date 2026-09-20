# export/ — Phase 6 web asset pipeline (bake engineer, branch `phase6-bake`)

Everything under `export/out/` is generated and gitignored. The source is always
`/Users/dk/Projects/3d render blender 3rd attempt building/master_delivery.blend`, opened read-only; no script in
this directory ever saves a `master*.blend`.

## Running Gate 0

```sh
export/gate0.sh            # steps 1-7 in order, one Blender at a time, through scripts/blender_run.sh
```

or step by step (each is idempotent and prints `STEP <name> wall_s=… <file>=<bytes>`):

| step | command (all through `scripts/blender_run.sh <max_s> -- …`) | writes |
|---|---|---|
| 1 | `--background master_delivery.blend --python export/export_set.py -- --gate0` | `out/gate0/gate0_set.blend`, `manifest.json` |
| 2 | `--background out/gate0/gate0_set.blend --python export/bake_normal.py` | `tex/gate0_*_normal.png`, `*_ao.png` |
| 3 | `… --python export/bake_pbr.py` | `tex/gate0_*_albedo.png`, `*_roughness.png` |
| 4 | `… --python export/bake_lightmap.py` | `tex/gate0_*_lightmap.exr`, `*_lightmap_rgbm8.png` |
| 5 | `… --python export/bake_lut.py` | `lut_agx_high_contrast_65.cube`, `sky_{camera,glossy}_4096x2048.{exr,hdr}` |
| 6 | `… --python export/gltf_export.py` then `export/gltf_pack.sh` | `gate0.gltf`, `tex_ktx2/*.ktx2`, `gate0.glb`, `gate0_instanced.glb` |
| 7 | `… --python export/render_reference.py` | `renders/web/gate0_cycles_cam01.png` |

`export/out/bake_queue/status.json` is `{"state":"running"}` while any of these owns the GPU and `{"state":"idle"}`
when it does not. **No other agent may start a GPU job (headless Chrome included) while it says `running`.**

## manifest.json — the contract with the viewer

One JSON object at `export/out/gate0/manifest.json`. `schema` is `"pfa-phase6-gate0/1"`; keys are added, never
renamed or removed, while that string stands.

| key | meaning |
|---|---|
| `schema`, `generator`, `source_blend` | provenance |
| `units` | `scale_m` 1.0; axes. **The glb is written with `export_yup=True`: Blender +Y → glTF −Z, Blender +Z → glTF +Y.** Every `*_blender` vector in this file is Blender Z-up and the viewer converts it as `(x, z, −y)`. |
| `water.water_z` | −1.3. The water is a viewer plane at `y = water_z`, never exported geometry |
| `view` | `view_transform` AgX, `look` "AgX - High Contrast", `exposure_ev` −2.8331399, `display_device` sRGB |
| `sun` | `energy_w_m2`, `color`, `angle_rad`, `direction_blender` and `direction_gltf` (the direction the light travels). The DirectionalLight must be **specular-only**: the diffuse sun is already inside every lightmap |
| `stations` | the six `scripts/qa_cameras.py` cameras by name: `location`, `rotation_euler_xyz` (Blender Z-up, XYZ order), `lens_mm`, `sensor_width_mm` 36, `sensor_fit` HORIZONTAL, `shift_x`, `shift_y`, `clip_start`, `clip_end`, `reference_photo`. `hero_camera` names the hero |
| `assets` | per exported object: `mesh`, `tris`, `material`, `uv` (UV1 = material, UV2 = lightmap), `location_blender`, `lightmap` (the `textures` key that belongs to it, or `null`) |
| `textures` | per map: `path` (relative to this file), `uv`, `colorspace`, `encoding`; lightmaps also carry `rgbm_range`, `decode` and the `exr` source |
| `lut` | `.cube` path (`lut_agx_high_contrast_65.cube`), `size` 65, the shaper, `exposure_ev`, `exposure_applied_by`, `method`, and the five-patch grey `proof` |
| `sky` | the two equirects (`camera` = background sphere, `glossy` = PMREM source), the mapping, `rotation_deg` / `u_offset` (see below), how the Light Path branch was isolated, and the sun's measured position in the image |
| `gltf`, `glb` | what the exporter and gltfpack produced, including `lightmap_slot` and `viewer_action` |
| `reference_frame` | the composited Cycles frame (kept for compatibility; same file as `reference.with_compositor`) |
| `reference` | **both** Cycles frames at 1280x720 / 64 spp from `CAM_qa_01_lagoon_hero`: `with_compositor` (the Phase 5 look) and `no_compositor` (`scene.compositing_node_group = None`, nothing else changed). Score against `no_compositor` first — a gap that survives there is the colour/lighting pipeline (exposure, the LUT, the lightmap π); a gap that only appears against `with_compositor` is the missing haze / bloom / vignette in `compositor` |
| `compositor` | every node of `COMP_scene_golden_hour` with its unconnected input values (mist / bloom / vignette) |

### Colour, exactly

The viewer does, per pixel, **with three.js tone mapping off**:

```
linear  = <what the renderer produced>
graded  = LUT3D( clamp((log2(max(linear * 2^exposure_ev, 1e-10) / 0.18) - shaper.min_ev)
                       / (shaper.max_ev - shaper.min_ev), 0, 1) )        // per channel
framebuffer = graded            // already display-referred sRGB, no further encode
```

`lut.size` is 65 (a 33³ lattice left a 1.7/255 trilinear error on mid grey). `shaper.min_ev` −12.47393, `shaper.max_ev` 4.026069, pivot 0.18, `exposure_ev` −2.8331399. Exposure is applied by
the viewer *before* the shaper; the LUT itself was baked through Blender at that exposure, so applying it twice, or
not at all, is wrong in both directions. `lut.proof` carries the Cycles-rendered 0.18 grey patch and the same value
pushed through the LUT — they must agree within 1/255.

### The lightmap

glTF has no lightmap slot, so the map rides in `emissiveTexture` on `TEXCOORD_1`. Per material, in this order:

1. **`texture.colorSpace = NoColorSpace` first.** glTF declares `emissiveTexture` as sRGB, so GLTFLoader would
   sRGB-decode the RGBM texels and every later step would be wrong.
2. `material.lightMap = material.emissiveMap` (keep `channel = 1`), then `material.emissiveMap = null` and
   `material.emissive = 0x000000`.
3. Decode RGBM8 as `rgb = texel.rgb * texel.a * textures.<key>.rgbm_range` (range 64 on every Gate 0 map), linear,
   no sRGB anywhere.
4. **`material.lightMapIntensity = manifest.lightmap_scale` = π (3.14159265).** The bake is Cycles' diffuse pass
   with **colour off**, i.e. irradiance/π, and three.js' `lightMap` path multiplies by `BRDF_Lambert` = albedo/π —
   so `lightMapIntensity = 1` renders π times too dark. The maps are deliberately *not* re-baked ×π; the constant
   lives in the manifest so there is one place to change it.
5. The sun `DirectionalLight` is **specular-only**: its diffuse is already inside the lightmap.

## Two Blender 5.2 findings this pipeline depends on (both measured here, both worth a docs/tech_notes.md entry)

1. **`Image.save_render()` applies no colour management at all.** Pushed 0.18 and 0.02526 through it with the scene
   at AgX / High Contrast / −2.833 EV and got 0.180 and 0.02525 back — the raw buffer. The LUT is therefore baked by
   **rendering the lattice through the compositor** (`scene.compositing_node_group` = an Image node wired to a
   `NodeGroupOutput`, render resolution = the lattice size, one sample), which is the path that does apply view
   transform, look and exposure. `export/out/gate0/bake_lut.json` carries the probe as `save_render_probe`.
2. **`scene.use_nodes = False` does not disable the compositor in 5.2** (the property is deprecated and on its way
   out in 6.0). Only `scene.compositing_node_group = None` does. Measured on the 0.18 grey emission plane:
   **0.075029** with `COMP_scene_golden_hour` still attached, **0.082078** without — a 7.5 % linear difference that
   first showed up as a 1.7/255 "LUT failure". Every measurement render that is not meant to carry the Phase 5
   compositor (the LUT proof, the two sky equirects) detaches the group; `export/render_reference.py` deliberately
   keeps it, because the reference frame is the Phase 5 look.
   Also: the compositor in 5.2 lives on `scene.compositing_node_group` and ends in a `NodeGroupOutput`, not on
   `scene.node_tree` with a `CompositorNodeComposite`.

A third, cheaper trap: `master_delivery.blend` is saved with `common.set_lod(viewport=1)`, so every `_LOD0` object is
`hide_viewport=True`, is **not in the depsgraph**, and therefore reads back `matrix_world` as the identity and is
invisible to `scene.ray_cast`. `export/export_set.py` un-hides the slice and calls `view_layer.update()` before it
reads any transform, and asserts every placement afterwards (`placement_max_error_m` 0.0).

### Where the sky sits after the Y-up swap — `sky.rotation_deg = 90.0`, derived not fitted

The equirects are written with

```
u_img = 0.5 + atan2(x_B, y_B) / 360        # u = 0.5 is Blender +Y (the lagoon side), u grows toward +X
v_img = 0.5 - elevation / 180              # measured from the FILE'S TOP row; the top row is the zenith
```

The exporter's Y-up swap is `(x, y, z)_Blender -> (x, z, -y)_three`, so a three.js direction `d` corresponds to
`x_B = d.x` and `y_B = -d.z`, and the texel the viewer wants is at

```
u_img = 0.5 + atan2(d.x, -d.z) / 360
      = 0.5 + (atan2(d.z, d.x) + 90) / 360
      = equirectUv(d).u + 0.25            # equirectUv is three.js' own built-in equirect lookup
```

So three.js' native lookup is a quarter of the width short: apply **+90° about the three.js Y axis** to the
background and to the PMREM environment (`scene.backgroundRotation` / `scene.environmentRotation`), or offset `u`
by **+0.25**. This is the same +90° the viewer had fitted by eye, now with a derivation behind it. Checked against
the image itself (`sky.orientation_check`): the file's upper half has mean luminance **3.393** against **0.030**
for the lower half, so the top row really is the zenith and no vertical flip is needed; the brightest pixel sits at
`v = 0.4993` from the top (the horizon glow, the sun disc being off) and at `u = 0.57922`, which is the sun's
azimuth to within 0.026°.

## Running Gate 1 (the frozen export set, branch `phase6-export`)

```sh
scripts/blender_run.sh 2400 -- --background <MAIN>/master_delivery.blend \
    --python export/export_set.py -- --gate1      # the set + the slim bake file + the job manifest
export/bake_queue.sh start                        # detached: 33 ORN normal+AO jobs, one Blender each
python3 export/name_sweep.py                      # the CLAUDE.md name sweep, on the export set
scripts/blender_run.sh 900 -- --background export/out/gate1/gate1_set.blend --python export/gltf_gate1.py
export/gltf_pack.sh --gate1                       # KTX2 + arch/orn/env/ground .glb
python3 export/manifest_v2.py                     # carry Gate 0's colour blocks, derive the instancing groups
python3 export/budget_doc.py                      # rewrite docs/briefs/phase6_budget.md from the JSON
export/sync_main.sh                               # copy out/ to the MAIN checkout the viewer reads
```

| file | what it writes |
|---|---|
| `export/gate1_common.py` | the Gate 1 constants: selection rule, per-asset decimation targets, tree rule, atlas slot size |
| `export/gate1_probe.py` | `out/gate1/probe.json` - read-only measurements (walkable surface per material, tree distances, PBR groups) |
| `export/gate1_set.py` | `out/gate1/gate1_set.blend` (the set), `gate1_bake.blend` (the 33 ORN lo/hi pairs only), `export_set.json`, `bake_jobs.json`, `manifest.json` |
| `export/bake_orn.py` | one prototype's `tex/orn_<proto>_normal.png` + `_ao.png` and `out/gate1/bake/<id>.json` |
| `export/bake_queue.sh` | `out/bake_queue/status.json` `{state,current,done,total,started,updated,jobs[]}`, resume, the GPU rule |
| `export/gltf_gate1.py` | `out/gate1/{arch,orn,env,ground}.gltf` + `tex_gltf/`, and the cam01 frustum batch count |
| `export/gltf_pack.sh --gate1` | `out/gate1/tex_ktx2/*.ktx2` and `{arch,orn,env,ground}.glb` (`gltfpack -cc -mi`) |

### What the set contains and why

* **Selection** - `ARCH_` at LOD0 + unsuffixed, `INST_` at LOD0, `ENV_` at LOD1 + unsuffixed, shrubs at LOD2.
  `ORN_` prototypes, `PH_`, `SOCKET_`, `ENV_lagoon_water` and `ENV_backdrop_bay` are never exported (the water
  is a viewer plane at `WATER_Z`).
* **Shared meshes stay shared.** One decimated datablock per (source mesh, modifier signature); the 138 fluted
  columns, the 138 base tori, the 138 astragals and the 33 ORN prototypes are one mesh each with N placements,
  which is what `EXT_mesh_gpu_instancing` draws in one call.
* **Single-use ARCH is merged** per (zone, material) - 1 032 + 149 source objects become 12 merged meshes, so
  the colonnade is 1 draw call instead of 300. Same for the ENV backdrop, merged per source material.
* **Decimation** is iterative: weld at 1e-5, then up to four COLLAPSE passes at `target/current`. Three ORN
  attic panels are ~40 000 separate relief islands and COLLAPSE stalls at 38-78 k against an 8 k target; those
  are voxel-remeshed first (the relief goes into the hi->lo normal map anyway) and then collapsed.
* **Trees** - near = a real-LOD1 tree whose base is within 25 m of the walkable surface (the paved
  `ENV_ground_colonnade_walk` plus the `MAT_gravel_path` faces of `ENV_terrain_ground`; `MAT_lawn` is excluded
  because it covers 489 424 m2 out to +-365 m and would make every tree near). Near trees keep LOD1 with leaf
  cards deleted until the mesh is half its triangle count - branch geometry untouched, so the crown gets
  sparser, not smaller. Far trees are 2-triangle billboard quads tagged with prototype, height and trunk base
  for the Gate 3 octahedral impostor bake. 46 of the 147 `_LOD1` tree objects already carry a `_LOD2` blob mesh
  (inherited from Phase 5) and go straight to the impostor list.
* **UV1** is the Gate 2 material atlas: one multi-object smart project per (zone, material) group for ARCH and
  ENV ground, one per prototype for ORN. **UV2** is the Gate 3 lightmap: a `[0,1]` unwrap per unique mesh.
  A mesh with one placement gets its own 2K map; an instanced mesh gets a per-instance 256 px slot on a 4K
  atlas (the user's ORN option (c)), and `manifest.assets[<name>].lightmap` carries `{atlas, slot, uv2_offset,
  uv2_scale}`.
* **Materials at Gate 1** are neutral greys, one per atlas group, plus the ORN normal map and the AO map in
  glTF's `occlusionTexture` (written through a node group named `glTF Material Output`). Foliage keeps its
  original bark/leaf materials so the silhouette check has the leaf alpha. PBR lands at Gate 2.

## manifest.json v2 - the contract with the viewer

`export/out/gate1/manifest.json`, `schema` = `"pfa-phase6/2"`. Everything documented for Gate 0 above still
holds for `units`, `water`, `view`, `sun`, `stations`, `lut`, `sky`, `compositor`, `reference` and the colour /
lightmap rules; those blocks are copied verbatim from the Gate 0 manifest by `export/manifest_v2.py` with their
paths rewritten to `../gate0/<file>`, after asserting that the exposure and the look still match.

| key | meaning |
|---|---|
| `schema` `pfa-phase6/2`, `gate` `gate1`, `generator`, `source_blend` | provenance |
| `assets` | every exported object: `cls`, `mesh`, `tris`, `material`, `instanced`, `kind` (ground / backdrop / tree_near / tree_board / shrub), `merged_from`, and `lightmap` = `{mode: "asset"\|"slot"\|"none", ...}`. For a billboard also `prototype`, `source_tree`, `height_m`, `width_m`, `trunk_base`, `walk_dist_m` |
| `meshes` | every unique mesh: `cls`, `src_mesh`, `src_tris`, `target`, `tris`, `placements`, `material`, `instanced`, `kind`, and for ORN `dims_m` / `max_dim_m` |
| `instancing` | mesh -> `{count, cls, tris, material, placed_tris, objects[]}`. **`gltfpack -mi` drops node names, so this is the only place the placement identity survives.** |
| `totals` | `placed_tris` / `unique_tris` / `objects` per class, `unique_meshes`, `draw_call_batches`, and the budgets they are measured against |
| `orn_slots` | `{orn: [...], arch_inst: [...]}` - the per-instance 256 px lightmap-atlas slot assignment (atlas index + slot index), the user's option (c) |
| `tree_rule`, `tree_near`, `tree_far` | the rule as applied with its counts, the near list, and the far list with prototype / height / trunk base for the Gate 3 impostor bake |
| `glb` | `per_class` = `{arch, orn, env, ground}` with bytes, placed tris, objects, meshes; `total_bytes`; the gltfpack flags |
| `textures` | `schema` (the shape of a per-map entry, and that **`rgbm_range` is required on every lightmap entry**), the KTX2 directory, the file list, total bytes and the encoder line |
| `lightmap_encoding` | **the RGBM contract, read by the viewer, never defaulted**: `encoding` RGBM8, `rgbm_range` 64 (Gate 0 measured 0 source texels above it), `decode` = `rgb = texel.rgb * texel.a * rgbm_range`, `colorspace` NoColorSpace, `uv` TEXCOORD_1, `lightmap_scale` pi, `slot_atlas` = 4096 px / 256 px slots. A viewer that falls back to its own default (e.g. 7.0) is wrong by that ratio — 9x at 7.0. `export/manifest_v2.py` asserts the field is present on every lightmap texture entry. |
| `colour_source` | which Gate 0 manifest the colour blocks came from and which keys were carried |
| `water`, `sun`, `stations`, `hero_camera`, `view`, `lut`, `sky`, `compositor`, `reference`, `lightmap_scale` | unchanged from Gate 0 (`lightmap_scale` = pi is the contract) |

## Gate 1 review and QA round 11 — what was fixed, what carries

Fixed on `phase6-export` after `docs/reviews/phase6_export_gate1_review.md` (5 fix-now) and `docs/qa_round_11.md`
(2 blockers):

1. `gltf_pack.sh` tagged colour textures `--assign_oetf linear`. **sRGB is now the default and only data maps
   (`*_normal|*_nrm|*normal*|*_ao|*rough*|*disp*|*translu*|*_mask*`) are linear**; the glob takes `.jpg` too, so
   the four bark diffuse maps reach toktx at all (85 KTX2, was 81), and `gltf_ktx2_patch.py` accepts `.jpg`.
2. `bake_queue.sh` wrote `status.json` only inside the worktree. `write_status`/`record_job` now copy it to
   `$MAIN/export/out/bake_queue/status.json` on every update — that copy is the GPU-liveness signal other agents
   read, so keeping it in step is the design, not a sync step.
3. The 256 px UV2 slots tiled with no gutter. `gate1_common.slot_uv()` is now the single source of truth for the
   slot layout (`export/manifest_v2.py` re-derives from it): **4 px border on every side, 248 usable px,
   `uv2_scale` 0.060547**, recorded in `manifest.lightmap_encoding.slot_atlas`.
4. `voxel_remeshed` / `orn_lo_from_lod1` are in `manifest.json` (the QA contract), and each affected mesh record
   carries the flag; the budget doc reads the flag instead of a cage-size proxy.
5. The budget doc's per-near-tree cost is measured (`near_tris_used / near_exported` = 19 595, so 13 more trees
   fit the headroom, not 19) and it states the radius rule's own count: **77 real-LOD1 trees within 25 m, 20
   exported, 57 to the impostor list**.
6. **QA blocker 1** — the grey UV1 probe was attached to the ten UV-less backdrop materials, so the exporter wrote
   `baseColorTexture.texCoord = -1`, three.js failed to link the program and the whole backdrop (151 737 placed
   tris) drew nowhere. A material only gets the probe when every mesh using it has UV1, and `gltf_gate1.py`
   **asserts no material in any class references a texture with a negative `texCoord`**.
7. **QA blocker 2** — the three ORN attic panels now build their low-poly from the Phase 5 `_LOD1` mesh
   (35 912 / 35 651 / 35 823 -> 7 999 each, collapse clean, no voxel remesh). Root cause of a second defect found
   on the way: an object created **after** the depsgraph was captured is not in it, and `evaluated_get(dg)` then
   returns a STALE evaluation — v2 got v1's low-poly and v3 got v2's. `exp_mesh(src_me=...)` copies the mesh
   datablock directly, and the exported mesh's bounding box is asserted against its own source.

### QA round 11b (three more, all on this branch)

8. The sweep could not see stand-ins named `board` / `impostor` / `billboard`, so the export's own 127 far-tree
   carriers passed as **0 hits** while covering 16-26 % of every frame. `export/name_sweep.py` now matches those
   three words and lists `ENV_treeboard_\d+` as a **named exemption**: *"Gate 3 impostor carriers, hidden in
   every QA capture until the impostor bake"*. The same three words belong in `scripts/qa_name_sweep.py` (the
   lead's file): `PAT = re.compile(r"placeholder|proxy|blocker|fill|occlud|block|dummy|temp|card|board|impostor|billboard", re.I)`.
9. The boards shipped **OPAQUE**, so a viewer that did not know the material name drew them as grey slabs.
   `MAT_EXP_treeboard` now carries `alphaMode: "MASK"`, `alphaCutoff: 1.0` **and `baseColorFactor` alpha 0** in
   the glb. The alpha 0 is not cosmetic: with an alpha of 1 gltfpack reasons "MASK over an always-opaque
   material == OPAQUE" and strips `alphaMode` again (measured at cutoff 1.0, 0.99 and 0.5). The material name is
   unchanged, so the viewer's existing name test still works.
10. **QA-11-9, the cam04 ceiling sliver.** Ray-cast attribution through the cam04 station over the defect box
    (470,140)-(600,350): `ARCH_rotunda_plaster_ceiling_rib_merged` **57.6 %** of the box and
    `ARCH_rotunda_plaster_ceiling_merged` 41.8 % (`export/qa_cam04_probe.py`, 3 124 samples). The rib group is
    the only decimated one of the two, so `ARCH_rotunda_ceiling_ribs` (19 564 -> 8 000) and the eight
    `ARCH_rotunda_vault_coffers_*` (17 658 -> 6 000 each) now export **as modelled**: the merged mesh goes
    **56 000 -> 160 828** triangles and the geometry at that station is the Phase 5 geometry, so no decimation
    artefact can survive there. Cost +104 828 placed; ARCH 949 382 (150 618 under budget), scene 2 841 396
    (158 604 under 3.0 M). A thin-triangle count is NOT the discriminator here and is not claimed as one: the
    undecimated source has 12 625 triangles thinner than 50 (radial fans on a coffer are naturally thin)
    against 174 in the decimated version.

Also seen by the cam04 probe and left for ENV/QA, not an export defect: `ENV_shrub_big3_0796_LOD2` sits **2.4 m**
from the cam04 station, inside the rotunda, and is hit by 5 of the 3 124 rays.

### QA round 11c (one blocker, the last of Gate 1)

11. **QA-11c-1 — 1379 shrubs drew stacked at the world origin.** Root cause is in the source, not the writer: in
    `master_delivery.blend` **only the `_LOD1` ENV objects carry a placement** — every `_LOD0` and `_LOD2` sibling
    sits at the origin as an unplaced stub (measured: shrubs 1379/1379 LOD1 non-identity, 1379/1379 LOD0 and
    1379/1379 LOD2 at the origin; `ENV_shrub_agap0_0005_LOD1` is at (-35.04, 2.93, -0.66), its LOD2 twin at
    (0,0,0)). Taking the LOD2 **object** for the shrub budget therefore took the stub. The shrub export now takes
    the **LOD1 object for the transform and its `_LOD2` mesh for the geometry**, exactly as the near trees already
    did; the exported object keeps the `_LOD2` name and records `placement_from`. Triangles are unchanged
    (135 880 placed), so no budget moves.

    Three assertions were added so this class of bug cannot ship again:
    * `gate1_set.py` — every exported asset records `location_blender` (its world bbox centre), and **no class may
      have more than one object within 1 m of the world origin**;
    * `gltf_gate1.py` — per class, `mesh nodes == exported objects`, and **a mesh node may carry no transform only
      if its Blender object's transform is identity** (arch 2 = 2, orn 0 = 0, env 10 = 10, ground 4 = 4 — the
      merged world-space groups), plus the same near-origin check read back from `export_set.json`;
    * `export/verify_glb.py` (new, run at the end of `gltf_pack.sh --gate1`) — per class the **triangles the glb
      actually draws** (primitive triangles x instance count) must match `export_set.json` within 1 %. Node counts
      prove nothing after gltfpack merges single-use nodes (564 ARCH objects -> 442 nodes, 4 ground objects -> 1);
      triangles do. Measured: arch -0.185 %, orn -0.157 %, env 0.000 %, ground 0.000 % — the small deficits are
      gltfpack dropping degenerate triangles, and a single dropped placement group would be orders of magnitude
      larger (the stacked shrubs were 8.8 % of ENV).

### Gate 2 hand-offs (backdrop UV1) and QA-11d-2 (position quantisation)

12. **The ten backdrop meshes now carry the Gate 2 bake's own UV1.** They shipped Gate 1 with no UV layer;
    the Gate 2 bake generated one and wrote the exact loop UVs to `export/out/gate2/backdrop_uv1.npz`
    (float32 `[loops, 2]` per Gate 1 mesh name, `phase6-bake` a9794e8). `export/gltf_gate1.py` reads it back
    and writes it as `TEXCOORD_0` for those ten meshes, **asserting the loop count per mesh** (75 478, 24,
    297 480, 1 760, 14 293, 3 220, 2 472, 6 780, 1 836, 11 764 — all matched). With a UV layer they also take
    the grey probe like every other material, so `uv1_probe` is now 61 materials with **0 skipped**, and the
    Gate 1 manifest carries `uv1_in_glb` **true on 143/143 meshes** with `uv1_source` naming the gate that
    produced each layer. The same flag in the bake engineer's `export/out/gate2/manifest.json`
    (`pfa-phase6/3`) does not exist yet and is theirs to write.
13. **QA-11d-2, the ENV position error.** Measured on `env_ktx2.gltf` with `gltfpack -cc -mi`, the error as
    gltfpack reports it: default **37 %** / 34 397 340 B; `-vp 16` **9 %** / 34 845 316 B; `-vp 18` and
    `-vp 20` byte-identical to `-vp 16` (**16 is gltfpack's maximum**, so more bits buy nothing); `-vpf`
    **no warning** / 35 797 240 B. `-vp 16` as briefed still leaves 9 %, so env takes **`-vpf`**: +952 KB over
    `-vp 16`, 2.7 % of env.glb, and `gltfpack.log` is now empty for all four classes. One flag reverts it.
    The structural fix is to split the 1.4 km backdrop into its own glb so the box stops covering the site —
    a Gate 2/3 option, not done here. `arch/orn/ground` keep the default and are byte-identical.

    `export/verify_glb.py` needed a correction for this: with `-vpf` gltfpack writes float positions and drops
    the node translation, so "no translation" no longer implies "at the origin" and the check reported five
    false positives. It now takes each plain node's centre from its POSITION accessor `min`/`max` plus the
    node transform. All four classes report 0 nodes with geometry at the origin.

14. **`-km` on env, and material names are now asserted.** The viewer review saw only one
    `MAT_EXP_ENVBD__*` material in env.glb: gltfpack merges materials whose factors are identical, and the ten
    backdrop greys were identical (flat `baseColorFactor`, no texture), so nine names vanished and nine Gate 2
    backdrop texture sets matched no scene material. Two things changed since that build: item 12 gave the ten
    meshes a UV layer and therefore the grey probe **texture**, which already kept them distinct (measured:
    10/10 `ENVBD` names present before `-km`), and env is now packed with **`-km`** so it is structural rather
    than incidental. `export/verify_glb.py` asserts, for any class packed with `-km`, that **every material
    name the export set uses exists in the glb**, and reports (without failing) the same for the classes that
    are frozen without it. Measured this pack — expected / in the glb / named / missing: arch 13/13/13/0,
    orn 33/33/33/0, env **21/21/21/0** (enforced), ground 4/4/4/0. The flags each class was packed with are
    written to `export/out/gate1/gltfpack_flags.txt` and read back by the verifier.

15. **QA-12-1, the two colonnade UV1 atlases.** Three real causes, measured, not guessed:
    * the group was unwrapped with a **multi-object** smart project, which packs ONE shared layout across the
      selection, so every mesh kept only its own sparse share of the square and the tiling step then scaled
      that sparseness into a tile — now each mesh is unwrapped on its own;
    * the island margin was `TILE_MARGIN` (0.004) **of the unwrap square**, which becomes 0.004 x tile side at
      the atlas: on the merged colonnade mesh 0.004 gives 0.036 self-coverage, 0.001 gives 0.114, 0.0003 gives
      0.146. `ISLAND_MARGIN_TILED` = 0.001 (~1.8 px at 2K on the big tile) is the safe end;
    * the tile scale was a fixed `1/sqrt(1.6)` guess; `pack_tiles` now **bisects** for the largest scale that
      fits — tile area 0.35 -> 0.788.
    Result, `MAT_EXP_ARCH_colonnade_north__MAT_concrete_colonnade` **0.0403 -> 0.0996** and
    `MAT_EXP_ARCH_colonnade_south__MAT_concrete_colonnade` **0.0394 -> 0.0939** (2.5x and 2.4x). Every other
    UV1 group is byte-identical (50 groups, 2 changed, asserted against the previous `uv1_atlas` boxes); the
    three rotunda multi-mesh groups keep the old layout through `g1.UV1_LEGACY_PACK` because their Gate 2
    bakes already shipped.

    **The 0.40 target is not reachable while these two atlases stay as one group, and the reason is
    structural, not a packing bug.** The merged 130-object colonnade mass holds 76 % of the group's surface
    area, so area weighting gives it 76 % of the atlas, and its own island packing tops out at 0.146 even with
    Blender's concave `pack_islands` (measured: smart project 0.146, pack_islands CONVEX 0.108, CONCAVE
    0.144). 0.76 x 0.15 caps the group near 0.13 whatever the other five meshes do. Raising the number by
    giving the merged mass a smaller tile would LOWER the density where the texels are actually needed.
    **The fix that works is to split the merged mass onto its own atlas**: it then gets a whole 2K instead of
    76 % of one (1.3x density) and the five instanced meshes reach ~0.40 on theirs. Cost: one extra material
    and one extra texture set per colonnade side (+4 x 2K maps, ~32 MB ASTC), and the bake engineer bakes four
    groups instead of two. **Lead's call — not taken here, because it changes the material set and the Gate 2
    bake plan.**

16. **UV1 atlas split (lead's go, 2026-09-15).** The merged single-use mass of the two colonnade groups now
    has its own material and its own 2K (`g1.UV1_SPLIT_MERGED`); four masses that were already alone on their
    atlas just take the fine island margin (`g1.UV1_FINE_MARGIN_GROUPS`); the `UV1_LEGACY_PACK` pin on the
    three rotunda groups is lifted; and the tile packer is a best-area-fit guillotine instead of shelves.
    Coverage before -> after (512² raster of the UV square):

    | group | before | after | target |
    |---|---|---|---|
    | `ARCH_colonnade_north__MAT_concrete_colonnade` (instanced) | 0.0403 | **0.2768** | 0.35 |
    | `ARCH_colonnade_north__MAT_concrete_colonnade__merged` (new) | - | **0.1143** | 0.13 |
    | `ARCH_colonnade_south__MAT_concrete_colonnade` (instanced) | 0.0394 | **0.2807** | 0.35 |
    | `ARCH_colonnade_south__MAT_concrete_colonnade__merged` (new) | - | **0.1099** | 0.13 |
    | `ARCH_rotunda__MAT_concrete_ochre` (the hero's stone) | 0.0560 | **0.1908** | 0.13 |
    | `ARCH_rotunda__MAT_plaster_ceiling_rib` | 0.0647 | **0.2002** | 0.13 |
    | `ARCH_site__MAT_concrete_podium` | 0.0827 | **0.3126** | 0.13 |
    | `ENV__riprap` | 0.0130 | **0.0876** | 0.13 |
    | `ARCH_rotunda__MAT_column_rose` (pin lifted) | 0.2282 | **0.3977** | 0.35 |
    | `ARCH_rotunda__MAT_column_tan_inner` (pin lifted) | 0.2241 | **0.4471** | 0.35 |
    | `ARCH_rotunda__MAT_concrete_podium` (pin lifted) | 0.3042 | **0.5075** | 0.35 |

    Eight of eleven meet their target. **The three that do not are capped by geometry, not by the packer.**
    The two instanced colonnade atlases hold two nearly equal column meshes, and two equal squares cannot
    exceed side 0.496 each in a unit square, so the tile area is capped near 0.545 (measured 0.5453 / 0.5421,
    and a guillotine packer returns exactly the same layout as the shelf packer — the bound is geometric).
    At the columns' own 0.545 self-coverage that gives 0.28. The two split masses reach 0.114 / 0.110 at the
    0.001 margin; 0.0003 would give 0.146 but leaves a 0.6 px gutter against a 16 px bake margin, so I did
    not take it. `ENV__riprap` is 49 joined rock objects and reaches 0.088. Raising any of the three further
    means 4K for those atlases or a finer margin — both the lead's call, with the numbers above.

Carried to Gate 2/3 (review findings 6-11, none a blocker): silent drop of an `ENV_*` LOD suffix that matches no
bucket; `hide_render` never read; the near-tree allowance estimates shrubs from the raw mesh; no retry on
`rc=143` in the queue; `new_from_object` meshes leak until `purge_orphans`; texture memory 1 343 MB against the
1 200 MB budget (a Gate 2/3 lever list).

## Carries (code-review findings 6-10, `docs/reviews/phase6_bake_gate0_review.md`, not fixed at Gate 0)

6. `export/bake_lut.py` reports `u_error_deg` and `horizon_row_v` but never asserts them, and the
   "brightest pixel sits on the horizon" reading assumes `sky.sun_disc` is off. Add `assert abs(u_error_deg) < 0.5`
   and log `sun_disc` at Gate 1.
7. All five LUT proof patches are neutral, so only the grey diagonal of the LUT is proven; AgX's hue path is
   untested. Add two saturated patches at Gate 1.
8. `MAIN_ROOT` is re-hard-coded in `gate0_common.py`, `gate0.sh`, `sync_main.sh` and `gltf_pack.sh` instead of
   `os.environ.get("PFA_MAIN_ROOT", str(common.MAIN_ROOT))`, and `HERO_CAM` duplicates
   `qa_cameras.CAMERAS[0]["name"]`.
9. **Done at Gate 0** — `sync_main.sh` no longer passes `--delete`, so it cannot erase what the export or viewer
   agent writes into the shared `$MAIN/export/out/gate0/`.
10. `gltf_export.py` never clears `tex_gltf/`, so a stale PNG from an earlier run would still be fed to toktx
    (wasteful, not wrong), and `gate0_common.guard_no_master_write` is dead code — call it or delete it.

## Running Gate 2 (the PBR bake, branch `phase6-bake`)

```sh
scripts/blender_run.sh 1800 -- --background --python export/gate2_probe.py     # read-only inventory -> out/gate2/probe.json
scripts/blender_run.sh 1800 -- --background --python export/gate2_set.py       # the two bake blends + bake_jobs.json
export/bake_queue.sh --gate2 start                                             # detached: one Blender per job, 900 s each
export/gltf_pack.sh --gate2                                                    # KTX2 UASTC desktop (+ ETC1S sample)
python3 export/manifest_v3.py                                                  # manifest v3, schema pfa-phase6/3
scripts/blender_run.sh 1200 -- --background --python export/gate2_verify.py    # baked vs procedural, Gate 0 station
export/sync_main.sh                                                            # copy out/ to the MAIN checkout (no --delete)
```

| file | what it writes |
|---|---|
| `export/gate2_common.py` | Gate 2 constants: the four bake classes, sizes, sample counts, the backdrop UV1 helper |
| `export/gate2_probe.py` | `out/gate2/probe.json` - read-only: every source material's node inventory (metallic, roughness, bump, images), the per-group surface area, UV1 presence, and the distance of every placement to the six QA stations |
| `export/gate2_set.py` | `out/gate2/gate2_bake.blend` (ARCH + ground + backdrop, from `gate1_set.blend`), `gate2_orn_bake.blend` (the 33 ORN lo/hi pairs, from `gate1_bake.blend`), `bake_jobs.json`, `backdrop_uv1.npz` |
| `export/bake_pbr.py --gate2 --job <id>` | one job's `tex/gate2_<job>_{albedo,roughness,normal}.png` and `out/gate2/bake/<job>.json` |
| `export/bake_queue.sh --gate2` | the same detached queue as Gate 1 (`out/bake_queue/status.json`, resume, the GPU rule) over `out/gate2/bake_jobs.json` |
| `export/gltf_pack.sh --gate2` | `out/gate2/tex_ktx2/*.ktx2` (UASTC + zstd + mips) and `tex_ktx2_etc1s/` for the timing sample |
| `export/manifest_v3.py` | `out/gate2/manifest.json`, schema `pfa-phase6/3` |
| `export/gate2_verify.py` | `out/gate2/verify.json` + two 1280x720 Cycles frames: the slice with the baked textures on flat Principled materials vs the procedural originals |

## manifest.json v3 — the contract with the viewer at Gate 2

`export/out/gate2/manifest.json`, `schema` = `"pfa-phase6/3"`, `gate` = `"gate2"`. **Everything in v2 still holds**:
`units`, `water`, `view`, `sun`, `stations`, `hero_camera`, `lut`, `sky`, `compositor`, `reference`,
`lightmap_scale`, `assets`, `meshes`, `instancing`, `totals`, `orn_slots`, `tree_rule` / `tree_near` / `tree_far`,
`glb`, `colour_source` are carried from the Gate 1 manifest by `export/manifest_v3.py` with their paths rewritten
to `../gate1/<file>` (and, for the colour blocks Gate 1 itself carried, `../gate0/<file>`).
**`lightmap_encoding` and `textures.schema` are copied verbatim and are not renegotiated at Gate 2** — `rgbm_range`
is still required on every lightmap texture entry, `lightmap_scale` is still π.

Two keys are new, and one is extended.

### `materials` — new

```jsonc
"materials": {
  "mode": "pbr",                       // "grey" at Gate 1; the viewer switches on this string
  "uv": "TEXCOORD_0",                  // every PBR map rides UV1; the lightmap keeps TEXCOORD_1
  "colorspace": { "albedo": "srgb", "roughness": "linear", "normal": "linear", "occlusion": "linear" },
  "sets": {
    "<glb material name>": {           // exactly the material name in the glb, e.g. MAT_EXP_ARCH_rotunda__MAT_column_rose
      "job": "arch_rotunda__MAT_column_rose",
      "cls": "arch" | "ground" | "backdrop" | "orn",
      "src_material": "MAT_column_rose",      // the Phase 5 material it was baked from (null for ground/ORN groups)
      "size": 2048,
      "albedo":    { "texture": "gate2_<job>_albedo",    "factor": [r, g, b] },
      "roughness": { "texture": "gate2_<job>_roughness", "factor": 0.83 },
      "normal":    { "texture": "gate2_<job>_normal",    "scale": 1.0, "constant": false },
      "occlusion": { "texture": null, "in_glb": true, "gate1_texture": "orn_<proto>_ao" },   // ORN only
      "metallic":  { "texture": null, "constant": true, "factor": 0.0 },
      "uv1_in_glb": true               // false for the ten backdrop groups: see "The backdrop" below
    }
  }
}
```

Rules the viewer can rely on:

1. **`texture` is a key into `textures.gate2.files`, never a path.** Resolve it there and join with `textures.gate2.ktx2_dir`.
2. **`texture: null` with `constant: true` is not an error — it is the map.** A map whose baked standard deviation is
   below `materials.constant_threshold` ships as a factor only (no file, no GPU memory). Apply `factor` as
   `material.color` / `material.roughness` / `material.metalness` and leave the map unset.
3. **A `normal` entry can be constant too**, with `factor [0.5, 0.5, 1.0]`: the baked map never left the flat
   value (measured on 6 of the 10 backdrop groups), so the surface uses its geometry normal and no map is loaded.
   An `occlusion` entry with `in_glb: true` is already inside `orn.glb`'s `occlusionTexture` — load nothing for it.
4. **`factor` is present even when `texture` is not null.** It is the baked map's mean (albedo: linear RGB;
   roughness / metallic: scalar) and is the correct value to use before the texture has streamed in, and the
   correct multiplier to leave at 1.0/white once it has. Never multiply the texture by the factor.
5. **Albedo is sRGB-encoded** in the file and the KTX2 carries `sRGB` transfer, so three.js `SRGBColorSpace`;
   roughness, normal and occlusion are linear data (`NoColorSpace`). The bake buffer itself is scene-linear —
   the encode happens on save, once.
6. **Roughness rides the green channel** of a glTF metallicRoughness texture when one is used; here it is shipped as
   its own single-purpose map, so assign it to `material.roughnessMap` and set `material.metalness` from
   `metallic.factor` (0.0 on 28 of the 30 source materials; the two exceptions are named in the report).
7. **Normal maps are tangent-space, +X +Y +Z (OpenGL convention)**, baked on the exported low-poly's UV1. For ORN they
   already carry the Gate 1 hi→lo relief *and* the material's own bump, baked in one pass — the Gate 2 ORN normal
   **replaces** `orn_<proto>_normal` from Gate 1; do not multiply or blend the two.
8. A material name that is not in `materials.sets` keeps whatever the glb gave it (the foliage bark/leaf materials,
   `MAT_EXP_treeboard`, and `MAT_water_lagoon`, which is the viewer's own plane).

### `textures.gate2` — the extension

`textures` keeps every v2 key (`schema`, `ktx2_dir`, `files`, `bytes`, `encoding`, `uv`) unchanged, describing the
Gate 1 set, and gains:

```jsonc
"textures": {
  "schema": "...unchanged, rgbm_range still required on every lightmap entry...",
  "gate2": {
    "ktx2_dir": "../gate2/tex_ktx2",
    "etc1s_dir": "../gate2/tex_ktx2_etc1s",    // only the mobile timing sample exists at Gate 2
    "encoder": "toktx --t2 --encode uastc --uastc_quality 2 --zcmp 18 --genmipmap --assign_oetf <srgb|linear>",
    "files": {
      "gate2_<job>_albedo": {
        "path": "gate2_<job>_albedo.ktx2", "w": 2048, "h": 2048, "map": "albedo",
        "colorspace": "srgb", "cls": "arch", "job": "<job>",
        "bytes": 1234567,            // on disk, KTX2
        "resident_mb": 5.33,         // ASTC 4x4 on the Apple GPU = 1 byte/texel, x4/3 for the mip chain
        "stats": { "mean": [...], "std": [...], "min": [...], "max": [...] }   // the baked float buffer, linear
      }
    },
    "bytes": 0, "resident_mb": 0.0
  }
}
```

### `budget` — new

```jsonc
"budget": { "resident_mb": { "<set name>": 0.0, "total": 0.0 }, "budget_mb": 1200,
            "levers_applied": ["..."], "note": "..." }
```

### The backdrop, and the one thing the viewer cannot do alone

The ten `MAT_EXP_ENVBD__*` groups left Gate 1 **with no UV1 at all** (`export_set.json.uv_missing.uv1`), which is why
QA-11c-2 sees them untextured. Gate 2 therefore does two things for them:

* every backdrop group gets a `factor` for every map, measured from its own bake — those work **today**, with no
  re-export, because a factor needs no UV;
* the UV1 the bake used is written to `out/gate2/backdrop_uv1.npz` (one float32 array of loop UVs per mesh, keyed by
  the Gate 1 mesh name) so the export engineer can apply the **identical** layout and re-export `env.glb`; the
  textures are already baked against it. Until that re-export the viewer must honour `uv1_in_glb: false` and use the
  factors only.

## Gate 2 — what the bake found, and what it hands off

**1. The "hero-near set" as the plan defines it is empty — measured, not assumed.** `docs/briefs/phase6_plan.md` §2
asks for 4K on "the 6 assets inside the hero frame within 30 m of cam01". `CAM_qa_01_lagoon_hero` stands at
`(-14.1, 100.0, 1.3)`, 100 m out in the lagoon, and the nearest bake group inside its frustum is the backdrop
lamp post at **36.2 m** (then riprap 51.2 m, the lagoon bed 51.3 m); no group is within 30 m. The walkthrough's own
stations do come close — 8 ARCH groups are within 30 m of one of the six QA stations, the nearest being the rotunda
podium at 5.2 m and the south colonnade at 5.5 m — and that set is what `export/gate2_sample.py` returns and what the
ETC1S timing sample uses. It is **not** baked at 4K: a 4K set (4K albedo + 4K normal + 1K roughness) is 44.0 MB
resident per group against 12.0 MB at 2K, so +32.0 MB each and **+256 MB for the eight** — 1 422 MB against a
1 200 MB budget, on top of a Gate 1 projection that was already 143 MB over.
The size is one line in `gate2_common.size_for` if the lead wants to spend the impostor lever on it instead.

**2. Texel density is the honest limit on the ARCH atlases, and 4K would not fix it.** The rotunda podium group is
1 200 m² of surface on one 2K atlas = 1.7 cm per texel, seen from 5.2 m where a 1440p pixel covers 0.37 cm — the
texture is 4.5x coarser than the screen, and 4K would still be 2.3x coarser. The colonnade is 3.8 cm per texel at
5.5 m, 10x coarser. A unique atlas is the wrong tool at that range; a tiling detail texture blended in the viewer is,
and that is a Gate 4 item, not a Gate 2 one. ORN is the opposite case: a colonnade capital is 2.9 mm per texel at 2K
against a 1.4 cm pixel at its nearest station, which is why its roughness ships at 1K with no visible cost.

**3. `PFA_concrete` reads world space, so a shared mesh can only carry one instance's answer.** The concrete group
takes **Geometry ▸ Position** for its grey drift (`Grey Below Z` / `Grey Above Z`), `PFA_algae` puts the waterline
band at world z = −1.3, and `PFA_instance` reads **Object Info ▸ Random / Location** for the per-instance weathering.
Gate 1 shares one mesh across every placement (138 fluted columns, 105 drum-band instances, 39 colonnade capitals),
so one texture must serve them all. Every job therefore bakes through the placement **closest to a QA station**
(recorded per job as `reps[].object` / `station_d_m`, and for ORN as the `matrix` the lo/hi pair is moved onto), which
makes the map right where it is seen best and wrong nowhere it is seen closely. The per-instance variation the
Phase 0-5 non-negotiable asks for survives only through the Gate 3 per-instance lightmap slot, not through albedo.
That is the cost of the user's instancing decision at Gate 1, recorded here so it is not rediscovered as a defect.

**4. The backdrop: baked, but it needs one thing from the export engineer.** The ten `MAT_EXP_ENVBD__*` groups have
no UV1 in the Gate 1 set (`export_set.json.uv_missing.uv1`), which is QA-11c-2's untextured backdrop. Gate 2
generates one (`gate2_common.smart_uv1`, a multi-object smart project, island margin 0.004), bakes against it, and
writes the exact loop UVs to **`out/gate2/backdrop_uv1.npz`** (one float32 `[loops, 2]` array per Gate 1 mesh name).
**Closed** — the export engineer re-exported `env.glb` with that layer (export b00344c), and `manifest_v3.py` now
derives `uv1_in_glb` by reading `TEXCOORD_0` back out of the Gate 1 glTF instead of asserting it: all 60 sets are
`true`. It also proves the layout is the baked one rather than a fresh unwrap — the set of distinct UV pairs in
`env.gltf` matches `backdrop_uv1.npz` at **1.00000 on all ten meshes** under glTF's top-left origin
(`v_gltf = 1 − v_blender`), against 0.0000–0.0017 without the flip. A mean-based check had called all ten a
mismatch: the exporter de-duplicates vertices, so counts and means differ while the distinct-UV set does not. The same re-export is
what gives the colonnade pedestals and balustrade (the other half of QA-11c-2) their texture — they are inside
`EXPM_ARCH_colonnade_*_concrete_colonnade_merged`, which has had UV1 since Gate 1, so for them nothing but the
Gate 2 material wiring is needed.

**5. The Gate 1 merge flattened every ENV mesh onto one material slot**, and restoring it was not optional. Every
`EXPM_ENV_*` mesh has `poly_material_index == {0: n}`, so taking slot 0 would have baked the gravel paths, the soil
and the city asphalt as lawn. `gate2_set.py` rebuilds the per-polygon assignment from the source objects by nearest
polygon centre in world space: `ENV_terrain_ground` comes back as **30 547 lawn / 4 917 soil / 8 952 gravel path**
faces — the gravel count `docs/briefs/phase6_budget.md` measured independently for the walkable-surface rule — plus
772 / 73 paving stone / worn on the colonnade walk and five materials across the backdrop lawn group.

**6. ETC1S is a payload lever, not a memory one.** On the Apple GPU both UASTC and ETC1S transcode to ASTC 4x4, so
the resident bytes are identical; what changes is the download. Measured on the sample: a 2K UASTC + zstd albedo is
**3.5 MB** on disk against **194 KB** as ETC1S, an 18x reduction. That is the lever for 6b's 50 MB initial payload,
and it costs nothing in GPU memory — so the budget-doc line "ETC1S instead of UASTC on the backdrop" does not move
the 1 200 MB number and is not counted as one of the levers that does.

**7. Carried to Gate 4 (not a Gate 2 defect, not fixed here).** The fluted shafts decimate 14 396 → 3 500 triangles
and `gate1_common.ARCH_TARGETS` says "flutes → normal map", but **no ARCH hi→lo normal bake exists**: the brief scopes
the ARCH normal to the material's own bump, and there is no hi twin for ARCH in the Gate 1 set. Adding it means
appending the `_LOD0` source objects to the bake blend and one selected-to-active pass per shaft mesh.

### The numbers (60/60 jobs, 2026-09-15)

`python3 export/gate2_report.py` prints all of this from the records; nothing below is typed by hand.

| class | jobs | maps baked | shipped | constant | bake s | KTX2 bytes | resident MB |
|---|---|---|---|---|---|---|---|
| arch | 13 | 39 | 32 | 7 | 1 305.7 | 41 660 407 | 118.56 |
| ground | 4 | 12 | 12 | 0 | 186.5 | 21 755 684 | 47.96 |
| backdrop | 10 | 32 | 25 | 7 | 100.2 | 11 107 418 | 33.25 |
| orn | 33 | 99 | 99 | 0 | 1 640.7 | 199 963 172 | 339.67 |
| **total** | **60** | **182** | **168** | **14** | **3 233.1** | **274 486 681** | **539.44** |

Queue wall time 3 573 s over the 60-job run (mean 59.6 s), zero failures, zero retries; the two metallic
backdrop jobs were re-run afterwards for review finding 2 (28 s + 12 s), which is why their bake seconds and
KTX2 bytes here are slightly below the first pass. The 14 constants are 7 ARCH and
7 backdrop maps whose covered texels varied by less than 0.005 — 13 flat normal maps and one flat roughness — and
they ship as factors with no file and no GPU memory.

**Resident against the 1 200 MB budget** (ASTC 4x4 = 1 byte/texel, x4/3 for mips):

| set | MB | gate |
|---|---|---|
| Gate 2 PBR (albedo + roughness + normal + 2 metallic) | 539.44 | 2 |
| ORN AO, carried unchanged from Gate 1 | 147.89 | 1 |
| foliage cards as shipped | 20.00 | - |
| lightmaps, own map | 85.00 | 3 |
| lightmap slot atlases | 107.00 | 3 |
| tree impostor atlases | 267.00 | 3 |
| **total** | **1 166.33** | **33.67 MB under the 1 200 MB budget** |

The Gate 1 projection was 1 343 MB; the net is −176.7 MB, and it is **not** all ORN (review finding 3 corrected
an earlier claim here). Measured, against the budget doc's own rows: ORN albedo + roughness **192.0 MB against
296 MB (−104 MB)** and ARCH + ground **166.52 MB against 272 MB (−105.5 MB)**, less **+33.25 MB** for the backdrop,
which the Gate 1 table did not carry at all. The ORN albedo keeps Gate 1's sizes — 2K for 26 prototypes and **1K
for the 7 under 1 m** (`ORN_SMALL_DIM_M = 1.0`), not "9 under 2 m": the normal and AO maps of a prototype must
share its resolution, so the albedo follows Gate 1's threshold and `gate2_set.py` now asserts the two agree
(checked on all 33; no size changed, nothing re-baked). The saving that is actually ORN's is **roughness at 1K
for all 33** — a colonnade capital is 2.9 mm per texel at 2K against a 1.4 cm pixel at its nearest station. The
impostor lever (2K → 1K, −200 MB) is **not** spent and stays available to Gate 3. Measured cost of the 1K roughness: over the 43 groups baked at 2K and shipped at 1K, the
reduction's RMS error is **0.0283 mean, 0.0521 worst**, against maps whose own standard deviation averages 0.0775.

**Metallic: 2 of 30 source materials drive it**, both in the backdrop — `MAT_lamp_post` (mean 0.150) and
`MAT_backdrop_door_green` (mean 0.019, max 0.700, i.e. metal fittings on a non-metal door). Both are baked through
an Emission rewire and shipped; every other material is `metallic.factor = 0.0` with no map. The brief expected
none; these two are the exception and they cost 2.67 MB.

**Their albedo is baked through the same rewire, not through DIFFUSE** (review finding 2). Cycles' DIFFUSE colour
pass weights base colour by `(1 − Metallic)`, so a metallic material bakes dark and a viewer that also applies
`metallic` attenuates it a second time. Re-baked through `emit_bsdf_input(mat, "Base Color")`: the lamp post's
albedo mean went **0.189 → 0.207** and its brightest texel 0.881; the door's **0.216 → 0.225**. Only these two jobs
of the 60 take the EMIT path — `bake_type` records which — and only they were re-run (28 s + 12 s).

### Verification, Blender side only (`export/out/gate2/verify.json`)

Gate 0 slice, `CAM_qa_01_lagoon_hero`, 1280x720, 64 spp, compositor detached, 32-bit linear EXR. Masks come from a
blurred A, not from A's own per-pixel luminance — splitting on the noisy image selects its noise into the two halves
and produced a 16-54 % "noise floor" between two renders of the *same* scene. With the blur the floor is 0.6-5.2 %.

| box | reference | procedural | baked | delta | noise floor | px |
|---|---|---|---|---|---|---|
| column sunlit | low-poly | 2.016187 | 1.988218 | **−1.39 %** | −1.04 % | 739 |
| column shaded | low-poly | 1.399913 | 1.405444 | **+0.40 %** | −0.63 % | 740 |
| capital sunlit | hi-poly | 4.012901 | 4.075629 | **+1.56 %** | −2.35 % | 218 |
| capital shaded | hi-poly | 2.511865 | 2.442141 | **−2.78 %** | −5.23 % | 219 |
| whole frame | low-poly | 2.577324 | 2.576476 | **−0.03 %** | — | 921 600 |

Worst box **2.78 %**, inside the 3 % the brief asks for — but read the two capital rows with their floors: at
218/219 px their own noise floor (−2.35 %, −5.23 %) is **as large as or larger than the delta the gate passes on**,
so those two rows show no disagreement rather than proving agreement. The column rows, 739/740 px, are the ones
that carry weight: −1.39 % and +0.40 % against a 1.0 % floor. Tightening the capital means more samples or a
seed-averaged reference, which is a carry (review finding 6), not a re-render done here.

**Why the capital is measured against the hi-poly and the column is not.** The column's normal map carries only
`MAT_column_rose`'s own bump, so the low-poly with the procedural material is the right reference. The capital's maps
are baked **selected-to-active from a 64 000-triangle hi-poly**, so they carry every term `MAT_ornament_concrete`
evaluates on the hi surface — `Geometry ▸ Normal`, `PFA_concrete`'s edge and ledge weights, the dirt in the recesses
— which the 6 000-triangle low-poly cannot reproduce. Against the low-poly the baked capital reads −17.5 %; against
the hi-poly it replaces, +1.6 %. The gap is the low-poly itself: **the procedural low-poly is +23.1 % brighter than
the hi-poly**, and the bake removes that error rather than introducing one. Reporting only the first number would
have called a working bake a failure.

### Review fixes applied (docs/reviews/phase6_bake_gate2_review.md, findings 1-3)

1. **`bake_queue.sh` GPU rule.** Exempting any registered Blender whose command line matched `bake_orn.py|bake_pbr.py`
   would have let a second queue — the export engineer's Gate 1 run, or a second `--gate2` runner — bake concurrently.
   The runner now tags its child through `BLENDER_RUN_OWNER` with `bake_queue_<gate>_<its own pid>` and `gpu_free`
   exempts only the state file carrying that tag (field 3 of the file `blender_run.sh` names after the Blender pid).
   Every other live registered Blender, bake script or not, now blocks the queue.
2. **Metallic albedo.** See the metallic paragraph above: baked through the Emission rewire, two jobs re-run.
3. **The ORN size rule.** `gate2_set.py` took `size1 = j1["size"]` from Gate 1, leaving `gate2_common.size_for`'s
   ORN branch dead. It now calls `size_for(CLS_ORN, max_dim_m)` and asserts the Gate 1 value matches — both use
   `ORN_SMALL_DIM_M = 1.0`, so all 33 agree, no size changed and nothing was re-baked. The wrong claim ("9 under
   2 m") is corrected above to 7 under 1 m.

Carried, not fixed (findings 4, 5, 7, 8, 9, 10): `gate2_verify.py` writes `verify.json` before computing
`worst_abs_delta_with_normal_pct` / `worst_abs_noise_floor_pct`, so those two are printed but not persisted; the pass
metric mixes the B0 and B variants between the column and capital rows, and `gate2_report.py` prints a different field
from the one `pass_3pct` uses (−1.39 vs −1.376); the capital's confidence (finding 6, stated with its floor above);
`apply_final_cycles_checked` is not called on the `--gate2` bake path (harmless — DIFFUSE colour-only, ROUGHNESS,
NORMAL and EMIT sample no light path — but the Eevee-rig assertion is absent); `gate2_set.py` writes the master
prototype's slot order onto the Gate 1 lo/hi meshes without asserting the existing `material_index` was built against
the same order; `bake_lib.py` `is_data=img.is_float and True` is always True (line 246 reassigns the colorspace, so it
is cosmetic), `manifest_v3.py`'s `if kind == "ao"` is dead, and its `etc1s_encoder` string omits `--assign_oetf`; the
five `renders/logs/gate2_*.log` sit outside the brief's `export/*`.

## QA-12-1 — why the stone read flat, and what actually fixes it

QA round 12 failed Gate 2 on one row: at cam05 the pier face, attic wall and spandrel are smooth pale ochre at
15-25 m, mid-band amplitude **2.68 against the Phase 5 reference's 10.11**, std 12.3 against 38.3. The report's
root cause was that 7 of the ARCH/ground sets shipped `normal.texture: null`, and the prescribed fix was to bake
each material's bump to a tangent normal map for every group.

**The seven nulls were real and are fixed** — an ARCH or ground set now always ships a normal map
(`manifest_v3.py`, the `CONSTANT_STD` rule no longer applies to them), so the viewer can never fall back to a flat
geometry normal on stone. **But the normal map is not where the grain lives, and measurement says it cannot be.**

| what was measured | result |
|---|---|
| Cycles NORMAL bake of the bump, `ARCH_site__concrete_podium` at 2K | X/Y std **0.00167** |
| the same bake at 4K | X/Y std **0.00272** — 1.63x for 2x the resolution, i.e. it scales with the texel footprint |
| the same bump baked as a HEIGHT map and converted to a normal at the map's own resolution (`bake_lib.height_to_normal`, no bake differentials in it) | flatter still |
| the arithmetic | Bump `Distance` **0.015 m** against an atlas texel of **0.038-0.118 m**; the height field varies by only **0.041** (std, full range) from texel to texel |

Extrapolated, the Cycles bake would need roughly **50x** the resolution to reach a usable amplitude. The grain is
not missing from the bake; it is finer than the bake's Nyquist. Phase 5 does not have this problem because Cycles
evaluates the same Bump per **camera pixel** — about 2 cm at the cam05 station — and because the detail images
underneath it are 2048 px across a 2.16-2.71 m tile, i.e. **1.05-1.32 mm per texel**, 36-110x finer than any unique
atlas this project can afford.

### The fix: a shared object-space detail set (`materials.detail`)

`export/gate2_detail.py` exports what Phase 5 itself uses — five shared texture sets, tiled in object space, on top
of the baked albedo/roughness:

| set | used by | object scale | tile | mm/texel in Blender |
|---|---|---|---|---|
| `concrete_wall_007` | colonnade, rotunda podium, drum band, ceiling ribs, paving stone | 0.462963 | 2.16 m | 1.05 |
| `concrete_wall_008` | column rose, tan inner, concrete inner/ochre, plaster ceiling, paving | 0.369004 | 2.71 m | 1.32 |
| `gravelly_sand` | gravel path | 0.403226 | 2.48 m | 1.21 |
| `rock_boulder_dry` | riprap | 0.85 | 1.18 m | 0.57 |
| `forest_ground_04` | soil | 0.31746 | 3.15 m | 1.54 |

Each set ships albedo, roughness and a tangent normal derived from its own height at the tile's real scale
(`k = Distance / m_per_texel`, 9.8-26.1), all at **1K = 19.95 MB resident for the whole scene** — independent of
how many atlases exist, because the sets are shared. The height map itself is not shipped.

**The proof QA asked for, on one group** (`ARCH_colonnade_south`, whose detail set is `concrete_wall_007`):

| map | red mean / std | blue mean / std | red range |
|---|---|---|---|
| atlas normal, 2K at 3.8 cm/texel (before) | 0.50003 / **0.00205** | 1.00000 / **0.00015** | 0.4504 – 0.6033 |
| detail normal, 1K over a 2.16 m tile = 2.11 mm/texel (after) | 0.50002 / **0.01649** | 0.99957 / **0.00580** | **0.067 – 1.000** |
| ratio | **8.0x** | **38.7x** | flat band -> full relief |

Those detail-normal figures are read back **from the saved PNG**, not from the array that produced it. The first
export of this set wrote fifteen 1024x1024 all-zero 16-bit PNGs (27 749 B each, extrema 0/0): `Image.save()` on a
generated float image whose pixels were written with `foreach_set` never got the buffer to the encoder, and the
numbers quoted in the first report were the in-memory arrays. The detail path no longer uses Blender image IO at
all - `bake_lib.write_png_rgb8` / `read_png_rgb8` write the file from numpy and read it back, every map's mean and
std are measured from the file, and a map that reads back flat aborts the run.

`manifest.materials.detail` carries the sets, the per-material object scale and the apply rule; the viewer
multiplies the baked albedo by the detail albedo over its own mean and blends the detail normal over the baked one.
Without that layer the atlas normal alone cannot move the cam05 numbers, whatever resolution it is baked at.

### After the atlas split (export 9badae4) — the numbers that shipped

The export engineer split every merged mass onto its own atlas. Re-baked all 19 ARCH/ground groups rather than
the 11 named: the export regenerated every UV1 layout in one pass, and a stale UV scrambles a texture, so the 8
unnamed groups cost ~8 minutes to prove instead of assume. The backdrop UV cross-check against
`backdrop_uv1_shipped.npz` still matches at **1.00000 on all ten meshes**, which is also the canary that the
regeneration was deterministic and the 33 ORN maps are therefore not stale.

| group | area m2 | UV1 coverage | cm/texel | atlas normal std X/Y |
|---|---|---|---|---|
| colonnade north, instanced remainder | 205 | 0.427 | **1.07** | 0.01272 |
| colonnade north, merged mass (new set) | 5 732 | 0.491 | **5.28** | 0.00270 |
| colonnade south, instanced remainder | 204 | 0.432 | **1.06** | 0.01277 |
| colonnade south, merged mass (new set) | 5 805 | 0.477 | **5.39** | 0.00271 |
| rotunda concrete ochre | 26 288 | 0.623 | 10.03 | 0.02582 |
| rotunda plaster ceiling rib | 2 443 | 0.827 | 2.65 | 0.00291 |
| site concrete podium | 23 787 | 0.705 | 8.97 | 0.00273 |
| ENV riprap | 1 021 | 0.990 | 1.57 | 0.00772 |

The colonnade was one atlas at 0.161 coverage and **9.4 cm/texel**; it is now two, at 1.07 cm for the columns,
bases and astragals the walker stands next to and 5.28 cm for the back wall — a 1.8x linear gain on the mass and
**8.8x on the instanced remainder**. QA-12-3's box (the south colonnade back wall) sits on the merged mass.
**19 of 19 ARCH/ground sets ship a normal texture; none is constant.** The atlas normals are still 0.003-0.026
std, as the measurements above say they must be — the surface itself rides `materials.detail`.

Resident after this round: **1 247.57 MB** (PBR 600.73 + ORN AO 147.89 + detail 19.95 + foliage 20 + the Gate 3
reservations 459). That is 47.57 MB over the 1 200 MB line, which the lead accepted for the new atlases; the
impostor lever (2K -> 1K, -200 MB) is still unspent and brings it to **1 047.57 MB** whenever Gate 3 wants it.

### The detail normal at the slope Cycles shades with, and the ceiling the sources impose

Re-derived: `h(x) = Distance * H(x)` metres, `n = normalize(-dh/dx, -dh/dy, 1)`, differentiated at the **source**
2048 px and the normal reduced afterwards (reducing the height first smooths the slope away — it cost 30 % of the
encoded std). `Distance` is the Bump node's own 0.015 m. The two concrete sets now ship at 2048, the ground sets at
1024, roughness at 1024 everywhere.

| set | ship px | tile m | mm/texel | k | height std | mean abs dH per texel | normal std R | std G | albedo contrast |
|---|---|---|---|---|---|---|---|---|---|
| `concrete_wall_008` | 2048 | 2.71 | 1.32 | 11.3 | 0.0098 | 0.00134 | **0.0189** | **0.0161** | 3.2 % |
| `concrete_wall_007` | 2048 | 2.16 | 1.05 | 14.2 | 0.0176 | 0.00173 | **0.0239** | **0.0268** | 3.3 % |
| `gravelly_sand` | 1024 | 2.48 | 1.21 | 12.4 | 0.0236 | 0.00351 | **0.0268** | **0.0265** | 5.0 % |
| `rock_boulder_dry` | 1024 | 1.18 | 0.57 | 26.1 | 0.1440 | 0.00178 | **0.0309** | **0.0315** | 6.2 % |
| `forest_ground_04` | 1024 | 3.15 | 1.54 | 9.8 | 0.0410 | 0.00117 | **0.0079** | **0.0077** | 9.3 % |

That is **+45 % on the concrete_wall_007 normal** (0.0165 → 0.0239) and +69 % on concrete_wall_008
(0.0112 → 0.0189), with the albedo ratio now unsmoothed (+35 % contrast, 0.0182 → 0.0246 std).

**It will not go an order of magnitude further, and the reason is in the source files.** Every `*_disp` map is an
**8-bit JPEG**: `concrete_wall_007_disp_2k.jpg` spans 0.0235–0.7255 but has a standard deviation of only **0.0176**
across 178 distinct levels, and its mean absolute texel-to-texel gradient is **0.00173** — *below* the 1/255 = 0.0039
quantisation step. `concrete_wall_008` is half that again (std 0.0098, gradient 0.00134). These are low-frequency
displacement maps for large-scale relief, not grain maps. With `Distance` = 15 mm and a 1.05 mm texel the honest
encoded slope is what the table shows; a gain of 6–10 on top would not be a stronger derivation, it would be
invented relief. If the Phase 5 amplitude has to be matched exactly, the lever is a higher-contrast source height
(a 16-bit or procedurally generated grain map), not a multiplier in the viewer.

**Where the rest of the cam05 amplitude actually is.** The metre-scale part of `PFA_concrete` — blotches at 2.2–3.0 m,
blocks at 1.2–3.0 m — is in the baked *albedo* and is resolvable by the atlas, but its *shading* is not: at 10 cm per
texel on `concrete_ochre`, `k = Distance / m_per_texel` = 0.15, so even a full-range height step across one texel is
an 8.5° tilt and a metre-scale one is under a degree. That is physically what Cycles does too. The remainder of the
gap at this gate is occlusion, which Gate 2 excludes by construction (QA round 12 scores the PBR set with no
lightmaps and no shadows).

**Colour space, checked on disk rather than assumed.** Every `detail_*_albedo.ktx2` carries DFD transfer **2 (sRGB)**
and every normal/roughness carries **1 (linear)** — `gltf_pack.sh --gate2` has tagged them that way since the detail
set was added. So the GPU returns linear after its sRGB decode and `mean_linear` is in that same sampled space:
`ratio = albedo_sampled / mean_linear` is correct as published, with no 45 % term. `mean_linear` and `std_linear`
are measured on the linear array before the sRGB encode, and `file_mean` / `file_std` are read back from the
written file.

---

## Running Gate 3 (the lightmap bake, branch `phase6-bake`)

```sh
scripts/blender_run.sh 1200 -- --background --python export/gate3_probe.py    # read-only inventory -> out/gate3/probe.json
scripts/blender_run.sh 1800 -- --background --python export/gate3_set.py      # gate3_bake.blend + gate3_imp.blend + bake_jobs.json
export/bake_queue.sh --gate3 start                                            # detached: one Blender per job, 1800 s each
export/gate3_pack.sh                                                          # KTX2 (lossless RGBM8 + gamma-2 UASTC) + .hdr
python3 export/manifest_v4.py                                                 # manifest v4, schema pfa-phase6/4
export/sync_main.sh                                                           # copy out/ to the MAIN checkout (no --delete)
```

| file | what it writes |
|---|---|
| `export/gate3_common.py` | Gate 3 constants (sizes, spp, slot geometry, the two encodings) + numpy PNG/EXR IO that never goes through `Image.save()` |
| `export/gate3_probe.py` | `out/gate3/probe.json` — read-only: per-asset UV2 coverage and cm/texel, the 988 slot instances, the vertex-bake candidates, the 25 far-tree prototypes |
| `export/gate3_set.py` | `out/gate3/gate3_bake.blend` (scene + final Cycles rig, UV2 re-laid where it had to be), `gate3_imp.blend` (the 25 tree prototypes alone), `bake_jobs.json`, `lightmap_uv2.npz` |
| `export/bake_lm.py --job <id>` | one job: an own map, a slot batch, a vertex-colour batch, an impostor prototype, the probe, or the diffuse equirect |
| `export/bake_queue.sh --gate3` | the same detached queue, `out/bake_queue/status.json`, resume, the GPU rule with the own-pid exemption |
| `export/gate3_pack.sh` | `out/gate3/tex_ktx2/*.ktx2` (both encodings) and `out/gate3/probe/*.hdr` |
| `export/manifest_v4.py` | `out/gate3/manifest.json`, schema `pfa-phase6/4` |

## manifest.json v4 — the contract with the viewer at Gate 3

`export/out/gate3/manifest.json`, `schema` = `"pfa-phase6/4"`, `gate` = `"gate3"`. **Everything in v3 still holds** and is
carried with its paths rewritten to `../gate2/<file>` / `../gate1/<file>` / `../gate0/<file>`: `units`, `water`, `view`,
`sun`, `stations`, `hero_camera`, `lut`, `sky`, `compositor`, `reference`, `lightmap_scale`, `lightmap_encoding`,
`assets`, `meshes`, `instancing`, `totals`, `orn_slots`, `tree_rule` / `tree_near` / `tree_far`, `glb`, `materials`,
`textures` (including `textures.gate2`), `budget`, `colour_source`.

Three keys are new (`lightmaps`, `impostors`, `probe`), `sky` gains one entry, `textures` gains `textures.gate3`, and
`budget` is recomputed. Nothing in v3 is renamed or removed.

**Every value below is copied out of a real `export/out/gate3/manifest.json` entry** (code review Gate 3, finding 12:
this section had drifted from the writer in five places). `export/manifest_v4.py` is the only thing that fills these
blocks and the file it writes is authoritative; where the two ever disagree again, the file wins.

### The one rule that governs every lightmap in this file

```
irradiance = decode(texel) * lightmap_scale        // lightmap_scale = pi, unchanged since Gate 0
```

with `decode` chosen by the texture's own `encode` field, never guessed:

| `encode` | decode | channels | why it exists |
|---|---|---|---|
| `"rgbm8"` | `rgb = t.rgb * t.a * range` | RGBA, **lossless KTX2 only** (`--zcmp`, no Basis) | exact; the M channel cannot survive block compression (a one-step error in M scales all three channels) |
| `"gamma2"` | `rgb = t.rgb * t.rgb * range` | RGB, UASTC → ASTC 4×4 | block-compressible, 4× less resident; the Gate 0 carry ("a gamma-2 encode of the RGB part would roughly halve the 4.8 % RGBM error") |

Every lightmap entry carries **both** variants and a `default` naming the one the budget can afford. `range` is
per texture, a power of two at or above the map's own measured max, and is **not** assumed to be 64.
`colorSpace = NoColorSpace` on every lightmap texture, in both variants. The sun `DirectionalLight` stays
**specular-only** and no shadow map is drawn: the diffuse sun, the sky and every bounce are inside these maps.

### `lightmaps` — new

```jsonc
"lightmaps": {
  "mode": "baked",
  "uv": "TEXCOORD_1",
  "scale": 3.14159265358979,                 // == lightmap_scale
  "bake": { "engine": "CYCLES", "type": "DIFFUSE", "direct": true, "indirect": true,
            "color": false, "samples": 128, "denoiser": "OPENIMAGEDENOISE",
            "rig": "light_presets.apply_final_cycles (Eevee-only rigs asserted off)" },

  "assets": {                                // the own-map assets, keyed by the glb OBJECT name
    "<object>": {
      "size": 2048,
      "textures": { "rgbm8": "<key into textures.gate3.files>", "gamma2": "<key>" },
      "default": "gamma2",
      "range": 29.085427,                    // the map's OWN max, per map: measured 0.72 (rotunda plaster
                                             // ceiling) to 52.83 (the orn slot atlas 0). Never assume 64.
      "uv2_in_glb": true,                    // FALSE means the glb's UV2 is stale: see "Re-laid UV2" below
      "uv2_source": "gate1" | "gate3_relaid",
      "uv2_coverage": 0.4912, "cm_per_texel": 5.31,
      "exr": "tex/gate3_lm_<object>.exr",
      "stats": { "min": 0.0, "max": 51.77, "mean": 5.77, "mean_nonzero": 7.83, "p99": 33.30,
                 "clipped_px_vs_range": 0, "clipped_pct_vs_range": 0.0 },
      "roundtrip": { "rgbm8_abs_max": 0.0, "rgbm8_rel_p99": 0.0,
                     "gamma2_abs_max": 0.0, "gamma2_rel_p99": 0.0 }   // both measured on the file read back from disk
    }
  },

  "slots": {                                 // the 988 per-instance slots, option (c)
    "atlases": {
      "<atlas key>": { "pool": "orn" | "arch_inst", "atlas": 0, "atlas_px": 4096,
                       "slot_px": 256, "gutter_px": 8, "usable_px": 248,
                       "slots_used": 256, "textures": { "rgbm8": "<key>", "gamma2": "<key>" },
                       "default": "gamma2", "range": 52.832478, "stats": {...}, "exr": "..." }
    },
    "note": "the per-instance uv2_offset / uv2_scale are `orn_slots` (unchanged since v2, derived from export/gate1_common.slot_uv); this block only names which atlas texture each pool+atlas index is."
  },

  "vertex_irradiance": {                     // the near trees: no UV2 that could carry a lightmap
    "encode": "none", "dtype": "float32", "shape": "(n_verts, 3)",
    "units": "scene-linear irradiance / pi (x lightmaps.scale = pi)",
    "attribute": "COLOR_0", "in_glb": false,
    "npz": "vertex_irradiance.npz",          // float32 (n_verts, 3) per MESH name, NOT encoded: the baked
    "bytes": 803100,                         // values themselves, same units as a DECODED lightmap texel.
    "meshes_n": 14, "verts": 347840,         // How COLOR_0 is quantised in the glb is the exporter's call,
                                             // made on these numbers.
    "glb_encode": "gamma2 per mesh (code = sqrt(v / range)), FLOAT_COLOR, env.glb -vc 16",
    "glb_decode": "v = COLOR_0 * COLOR_0 * meshes[<mesh>].range, then irradiance = v * lightmaps.scale (pi) - exactly as a gamma2 lightmap texel. `range` is PER MESH; glTF multiplies COLOR_0 into base colour by default, so these 14 meshes must consume it as irradiance, not as a tint.",
    "meshes": { "<glb mesh>": { "verts": 17996, "min": 0.0, "max": 0.469, "mean": 0.000009,
                                "mean_nonzero": 0.00472, "p99": 0.0,
                                "roundtrip": { "abs_max": 0.0, "rel_p99": 0.0, "rel_mean": 0.0 },
                                "range": 0.5, "encoding": "gamma2",   // <- copied from uv2_relay_status.json
                                "mean_linear": 0.0, "roundtrip_rel_p99": 0.0 } },
    "note": "`in_glb: false` until the export engineer re-exports env.glb with COLOR_0. Until then the viewer keeps the near trees on the PMREM path and must use `sky.diffuse` for their irradiance, not `sky.glossy` (QA-12b-1)."
  }
}
```

**Re-laid UV2 (`uv2_in_glb: false`), the one thing the viewer cannot do alone.** Gate 1's UV2 on the merged ARCH and
ENV masses is margin-dominated: measured on `gate1_set.blend`, the south colonnade merged mass packs **0.0095** of its
2K map (median triangle 0.21 px across, i.e. sub-texel), the rotunda ochre mass 0.0133, the riprap 0.0023. A lightmap
baked on that layout is 32–69 cm per texel and cannot carry a shadow edge. Gate 3 therefore re-unwraps UV2 for the
assets below `lightmaps.uv2_relay_threshold` **in its own bake blend**, bakes against the new layout, and writes the
new loop UVs to `out/gate3/lightmap_uv2.npz` (one float32 `(n_loops, 2)` array per Gate 1 MESH name) so the export
engineer can apply the identical layout and re-export. This is the same hand-off shape as Gate 2's
`backdrop_uv1.npz`. **Until that re-export the viewer must honour `uv2_in_glb: false` and not apply those maps** —
there is no factor fallback for a lightmap; the object stays on its Gate 2 material with no lightMap.

**Who sets `uv2_in_glb`.** Not this writer. The export engineer applies the npz, re-packs, and writes
`out/gate3/uv2_relay_status.json` (`pfa-phase6/gate3-relay/1`); `manifest_v4.py` reads that file — from the worktree
or from MAIN — and takes every flag from it, leaving them **false** while the file is absent. Three consumers:
`lightmaps.assets[*].uv2_in_glb` (the own maps, by MESH name), `lightmaps.slots.uv2_in_glb` (the 988 per-instance
slots are addressed by the ORN meshes' own TEXCOORD_1, so they are unusable until `orn.glb` is packed with `-kv`),
and `lightmaps.vertex_irradiance.in_glb`. The two `lmg1_*` diagnostics take the **inverse** of the relay's flag for
their mesh: they are baked on the frozen Gate 1 layout and are usable only while the glb still carries it.
`lightmaps.uv2_relay_status` in the manifest reports the file's schema, the per-glb TEXCOORD_1 counts and the
gltfpack flags, so a reader can see why a flag is what it is. Background (docs/decisions.md 2026-09-16): gltfpack had
been stripping TEXCOORD_1 from every glb since Gate 1, so Gate 1's own `uv2_in_glb: true` was never true.

### `lightmaps.instance_irradiance` — new at Gate 4 (the 1 379 shrub/reed placements)

The 28 shrub/reed card meshes are the only env.glb geometry with neither a lightmap nor `COLOR_0`
(`export/gate3_env_cards.py`, `out/gate3/env_cards.json`), so they were lit by the sky alone and read cyan
(hue 180 against the reference's 102, QA round 14). They cannot take the near trees' per-mesh `COLOR_0`: those
28 meshes carry **1 379 placements**, up to 101 on one mesh, 279 m apart on average across a 250 x 166 m site,
so one value per mesh would give 1 379 shrubs 28 arbitrary irradiances. Per **placement** is the only correct
granularity (docs/decisions.md 2026-09-16 "Shrub/reed irradiance is baked PER PLACEMENT, not per mesh"), and
it keeps the instancing: one scene-linear RGB per instance, consumed as an `InstancedBufferAttribute` exactly
like the ORN slot offsets, with no unique meshes and no `COLOR_0` on the cards.

```jsonc
"instance_irradiance": {                     // the shrub/reed cards: no UV2, and 1 379 instances of 28 meshes
  "encode": "none", "dtype": "float32", "encoding": "linear-float32",
  "units": "scene-linear irradiance / pi (x lightmaps.scale = pi)",   // same units as a DECODED lightmap texel
  "attribute": "_IRRADIANCE",                // the viewer's per-instance attribute name; NOT COLOR_0
  "json": "instance_irradiance.json",        // out/gate3/, 400 kB, the file below; nothing is quantised
  "placements": 1379, "meshes_n": 28,
  "range_global": 17.2167,                   // max component over all 1 379; informational, nothing is encoded to it
  "in_glb": false,                           // true only once env.glb carries the attribute (export engineer)
  "key": "WORLD TRANSLATION",                // `loc`, matched per mesh; the object name is only a label
  "join": { "tolerance_m": 0.02, "min_separation_within_mesh_m": 0.0882 },
  "meshes": { "<export-set mesh>": { "n": 101, "min": [...], "max": [...], "mean": [...],
                                     "lum_min": 0.0, "lum_mean": 1.5, "lum_max": 8.6, "cov_mean": 0.85 } }
}
```

`out/gate3/instance_irradiance.json` (`pfa-phase6/gate4-instance-irradiance/1`, written by
`export/gate3_instance_compose.py`, **not** by `manifest_v4.py`; the manifest writer reads it the way it reads
the relay file) carries, besides those summaries, `meshes["<mesh>"].placements = [{object, loc, rgb, mean_all,
cov}, ...]`:

* `loc` — **the key**: the placement's world translation in Blender metres. glTF is Y-up, so the instancing
  row's translation is `(x, z, -y)` of this. Join **per mesh**: for each `EXT_mesh_gpu_instancing` row of a
  mesh take that mesh's nearest entry, assert the residual is under `join.tolerance_m` (0.02 m) and that the
  assignment is a bijection. Measured: the closest two placements of one mesh are **0.088 m** apart and no
  same-mesh pair is within 2 x tolerance, so the match is unambiguous. (Three pairs of *different* meshes sit
  9–29 mm apart; the per-mesh join cannot confuse them.) `gltfpack` quantises instance translations, so never
  require an exact match — and never fall back to a guess: if a residual exceeds the tolerance, fail.
* `object` — a label only (`ENV_shrub_pitto5_0999_LOD2`). It is **not resolvable from the glb**: `gltfpack -mi`
  drops node names and the manifest's `instancing.<mesh>.objects[]` is truncated at 16 entries. The array order
  is `export_set.json["assets"]` order filtered to the mesh; a convenience, never the contract.
* `rgb` — float32 scene-linear irradiance / pi at that instance's own world transform, the mean over the card's
  **lit** vertices. Use it as a decoded lightmap texel: `irradiance = rgb * lightmaps.scale`, multiplied into
  the card's diffuse term in place of the sky-only ambient, never as a tint.
* `mean_all` — the same mean over **all** vertices, i.e. `rgb` scaled down by the fraction of the card buried
  in the terrain. Shipped for a consumer that wants the occluded form; `rgb` is the recommended one.
* `cov` — the fraction of the card's vertices that received light (mean 0.853). **`cov == 0` is a contract, not
  a diagnostic:** 7 placements are fully enclosed, ship `[0,0,0]`, and the viewer falls back to the probe
  irradiance for them (lead, 2026-09-17). They are listed in `checks.dark`.

**How it is baked** (`export/bake_lm.py` kind `instance`, jobs `inst_irr_00..03` from
`export/gate3_instance_jobs.py`, run through `export/bake_queue.sh --gate3`): the same rig, `DIFFUSE`
direct+indirect with `color: false` at 128 spp into `VERTEX_COLORS`, as the near trees' `vertex` kind, but the
mesh data is made **single-user per placement inside the bake process** (nothing is saved, the export set's
shared meshes are untouched) so each instance is baked at its own transform. Cost: 4 jobs, **2 517 s** of GPU,
1.82 s per placement, ~100 placements per `bpy.ops.object.bake` call (a multi-object `VERTEX_COLORS` bake
writes every selected object — proved by `inst_probe`, whose first chunk was batched and second baked one
object at a time).

**The material override, what it changes, and why the scope is the whole set.** A leaf card's material is
alpha cut-out, and at a vertex that falls in a transparent texel a `DIFFUSE` bake returns exactly **0** — the
same artefact that put 77–99 % exact zeros in the near trees' `COLOR_0`. On a 36-tri card it is fatal:
`inst_probe` measured **10.7 %** coverage with the cards' own material and **1 of 12 placements entirely
black**. The bake therefore wraps each card *material* so that **Light Path ▸ Is Shadow Ray** picks the
original cut-out chain for shadow rays and an opaque grey Principled for every other ray, with
`visible_shadow` left **ON**: every shadow the leaf casts — on itself, on its neighbours, on the ground — is
the real leaf-shaped one, and only the baked surface itself is grey. Coverage rises to **0.853**. Because
materials are shared datablocks the wrap covers all 1 379 placements in every job, so **no value depends on
the job split**: one placement baked in two jobs with different companions and different chunk sizes returns a
bit-identical rgb (`inst_splitA` / `inst_splitB`, delta 0.000000). The earlier form of this override (opaque
material on the job's own objects with `visible_shadow = False`) was withdrawn at review: it removed the
cards' real self- and neighbour shadow and only 28.9 % of nearest neighbours shared a job, so the values
depended on the partition.

**This is not a neutral re-encoding, and the README no longer claims it is.** Matched per vertex — same
vertices, same transform, only the material changed — the shadow-ray wrap reads a **median 1.61x** brighter
than the cut-out bake (0.12–3.39 across the 11 probe placements with any matched vertex; the two below 1.0 are
cards whose few cut-out-lit vertices now sit in a real neighbour shadow). The withdrawn no-shadow variant was
a further **median 1.14x** on top of that, up to **2.01x** on sunlit cards. `color: false` does divide the
albedo out, but the surface that receives the light is a full grey lambert instead of a partly transparent
leaf, so the number is a measurement of the *card's* incident light, not of the leaf's. Also measured and
**not** used: the same wrap on **Is Camera Ray** (a bake's primary hit is a camera ray — coverage 0.857
confirms it), which would leave the cut-out in place for the diffuse bounces between cards as well; it reads a
median **0.929x** of the shadow-ray form. The lead prescribed the shadow-ray form; the camray number is here
so the choice can be revisited with a measurement rather than an argument.

**Verification** (`checks` in the same file, plus `out/gate3/instance_check.json` from
`export/gate3_instance_check.py`, which ray-casts each placement onto the ground and samples that asset's baked
lightmap EXR at the hit point): the shrubs track the ground under them monotonically — ground luminance
quartiles 0.19 / 0.67 / 1.37 / 3.82 give shrub means **0.59 / 1.18 / 1.59 / 3.42** (n = 161 each, Pearson
**0.617** over the 645 placements standing on the terrain; it was 0.456 before the real shadows came back).
The shrub range is still compressed against the ground's (top decile over bottom decile: 13.5x against 106x)
for two structural reasons, both expected: a card is vertical and is averaged over its whole height, so it
keeps a large sky term where a horizontal texel in shade loses the sun term outright; and the ground texel
directly under a shrub carries that shrub's own baked cut-out shadow, so the reference is biased low exactly
where it is darkest. 701 of the 1 379 rays land on a lightmapped ground asset; the rest hit another card, the
water or the backdrop lawn and are itemised in `all_ray_hits`.

**The near trees were re-baked with the same wrap** (review finding 6, lead decision 2026-09-17). `vc_00` and
`vc_01` re-ran in place — same ids, same `out/gate3/vertex/<id>.npz`, same schema, so `gate3_compose.py --only
vertex` and the export's r2 encode re-run unchanged — for **117 s** of GPU. Vertex coverage over the 347 840
verts went **0.203 → 0.756**; 12 of the 14 meshes moved from 0.09–0.33 to **0.86–0.98**. The two that did not
are `broadleaf_s19` (0.002 → 0.010) and `pine_s29` (0.005 → 0.022): they have no loose vertices (checked), so
with a grey lambert at every vertex they still receive essentially nothing — README's earlier "sit in full
shadow" reading is **confirmed for those two** and was the cut-out artefact for the other twelve. The previous
npz is kept as `out/gate3/vertex_irradiance_before_shadowray.npz` and the per-mesh before/after is in
`out/gate3/vertex_before_shadowray.json`. `lightmaps.vertex_irradiance`'s per-mesh statistics in the manifest
are regenerated from the new npz, so the stale `mean 0.000009` figures quoted in the block above belong to the
pre-Gate-4 bake.


### `trees.far_mesh.lighting` — new at 6c (the 127 far trees once they are MESHES, and what the impostors divide by)

6c item A gives every one of the 127 far trees a real LOD2 mesh in a lazily loaded `env_trees.glb`
(`EXT_mesh_gpu_instancing`, the same transforms as the `tree_far` entries). Mesh trees cannot be `unlit` the
way the impostor atlas is, so they need the same two terms the near trees and the shrubs already have — one
static ambient-occlusion factor per prototype, and one irradiance per placement — and the impostors that still
draw beyond `treeMeshDist` need a third number so the two paths agree across the crossfade.

```jsonc
"trees": { "far_mesh": {
  "glb": "env_trees.glb", "placements": 127, "prototypes_n": 16,
  "lighting": {
    "vertex_ao": {                            // per PROTOTYPE, on the export's LOD2 topology
      "npz": "trees_far/vertex_ao.npz",       // out/gate3/, float32 per vertex, key = the LOD2 mesh name
      "dtype": "float32", "encode": "none",
      "units": "0-1 ambient occlusion (1 = unoccluded)",
      "bake": "lights off, uniform white world, DIFFUSE colour off, the shadow-ray cut-out override, 64 spp, VERTEX_COLORS",
      "topology": "asserted equal to the export's LOD2 vertex count per prototype; a mismatch is a hard failure",
      "meshes": { "<LOD2 mesh>": { "verts": 0, "min": 0.0, "mean": 0.0, "max": 0.0 } } },
    "instance_irradiance": {                  // per PLACEMENT, the shrub/reed schema and join, at /2
      "json": "trees_far/instance_irradiance.json",
      "schema": "pfa-phase6/gate4-instance-irradiance/2",   // /1 is the shrub file; /2 adds `prototypes`
      "reduce": "`rgb` = mean_nonzero over the cov mask, the reducer the shrub file ships; `cov` beside it",
      "encode": "none", "dtype": "float32", "encoding": "linear-float32",
      "units": "scene-linear irradiance / pi (x lightmaps.scale = pi)",
      "attribute": "_IRRADIANCE", "placements": 127, "key": "WORLD TRANSLATION",
      "join": { "tolerance_m": 0.02 } },
    "prototype_e_bake": {                     // 16 values, in the SAME json under `prototypes`
      "where": "trees_far/instance_irradiance.json -> prototypes[\"<prototype>\"].E_bake = [r, g, b]",
      "units": "the same scene-linear irradiance / pi as instance_irradiance",
      "bake": "the DIFFUSE irradiance (colour off, the same shadow-ray override, the same mean_nonzero reducer) of the `_LOD1` PROTOTYPE OBJECT that job imp_<proto> rendered into the atlas, in gate3_imp.blend's OWN environment - the lawn under the open sky, the prototype isolated, the lamps exactly as the atlas bake had them. NOT the export's LOD2 mesh (review r1 finding 5): the divisor has to describe the body that produced the atlas. LOD2 is the mesh path's AO / _IRRADIANCE geometry only.",
      "raw": "BOTH VALUES RAW: this file's `rgb` (or the unscaled `_IRRADIANCE` attribute) over this file's E_bake. `lightmaps.scale` (pi) is applied to NEITHER - scaling only the numerator makes every impostor pi x too bright (review r1 finding 7).",
      "use": "IMPOSTOR ONLY. Beyond `treeMeshDist` the viewer draws atlas_frame * (E_placement / E_bake) per placement, per channel: the atlas already holds lit radiance baked in the nursery, so dividing it by the irradiance that nursery supplied and multiplying by the irradiance the placement actually receives turns the unlit atlas into the same shading the mesh path applies. Clamp the ratio (the lead sets the ceiling) and fall back to 1 where E_bake has a zero channel." } } }
```

Why the division exists: the 6c item-1 diagnosis (finding 33 below) measured that the atlas is a faithful
encode of Cycles, and that Cycles rendered each prototype ALONE on a lawn under the whole unoccluded sky dome
— sun-only gives the crown `[0.113, 0.112, 0.000]` and sky-only `[0.078, 0.157, 0.387]`, so every blue photon
in the atlas is a sky term the scene does not have. `E_placement / E_bake` removes exactly that nursery sky
and puts the placement’s own irradiance in its place, which is why the impostor and the mesh match across
the crossfade instead of the impostor jumping blue (lead’s decision, docs/decisions.md 2026-09-17).

**The GPU path for these jobs.** The 16 AO jobs, the 127-placement irradiance and the 16 `E_bake` values all
go through `export/bake_queue.sh --gate3` like every other bake. `export/gpu_lock.sh claim|release` is the
accepted path for a **one-off** Blender run that is not a queue job (it was added for the 6c item-1
diagnosis): it writes the same `state: running|idle` into `out/bake_queue/status.json` and copies it to MAIN,
which is the only GPU-liveness signal other agents may read. Mutual exclusion itself still comes one level
down, from `scripts/blender_run.sh` registering the pid with the watchdog.


### `impostors` — new

```jsonc
"impostors": {
  "mapping": "octahedral",                   // FULL octahedron, not hemi
  "grid": 12, "frame_px": 170, "inner_px": 162, "gutter_px": 4, "atlas_px": 2048,
  "shipped_px": 1024,                        // the atlas actually referenced; the 2K variant is on disk
  "encode": { "albedo": "gamma2 on RGB at the prototype's own `range` (rgb = t.rgb*t.rgb*range, LINEAR oetf, NOT sRGB), straight alpha in A",
              "normal_depth": "rgb = world normal * 0.5 + 0.5 (Blender Z-up); A is depth about the BILLBOARD CENTRE, a = 0.5 there: depth_from_centre_m = (a - 0.5) * depth_range_m, positive away from the camera. The bake-time camera stand-off is not exported and is not needed.",
              "normal_depth_note": "block compressed (UASTC -> ASTC 4x4) on purpose while `unlit` holds and nothing samples the normal or the depth; repack lossless (+3.0 MB resident per prototype at 1K, +48.0 over the 16) the day the viewer shades or soft-depth-tests it" },
  "lighting": "baked: Cycles Combined at the final rig, sun + sky + leaf translucency, film_transparent",
  "frame_lookup": "d = normalize(camera_pos - billboard_pos) in BLENDER Z-up (the viewer converts its own three.js dir back with (x, -z, y)); n = d / (|d.x|+|d.y|+|d.z|); if n.z >= 0 { u = n.x; v = n.y } else { u = (1-|n.y|)*sign(n.x); v = (1-|n.x|)*sign(n.y) }; uv01 = (u,v)*0.5+0.5; col = round(uv01.x*(grid-1)); row = round(uv01.y*(grid-1))",
  "frame_uv": "u = (col*frame_px + gutter_px + f.x*inner_px) / atlas_px, v likewise with row; clamp f to [0,1] and inset by half a texel",
  "instance_rotation": "IGNORED on purpose: the lighting is baked in world space, so the frame is picked from the world-space view direction and the instance's own Z rotation is not applied. Two instances of one prototype therefore differ by scale, not silhouette.",
  "prototypes": {
    "<prototype>": { "albedo": "<key into textures.gate3.files>", "normal_depth": "<key>",
                     "albedo_2k": "<key>", "normal_depth_2k": "<key>",
                     "range": 2.4210851,     // the gamma-2 range of THIS prototype's albedo
                     "radius_m": 15.1491, "bbox_m": [16.7846, 20.7329, 14.367],
                     "base_z_m": 0.0,        // bbox bottom in the prototype's own frame; -2.6748 on the willow
                     "centre_z_m": 7.1835,   // billboard centre above the prototype's z = 0
                     "height_above_base_m": 14.367,   // bbox_max.z - max(base_z_m, 0): the scale denominator
                     "depth_range_m": 30.2983, "views": 144, "alpha_coverage": 0.1305,
                     "render_s": 56.3, "s_per_view": 0.391, "bytes": 5176867,
                     "roundtrip_albedo": { "abs_max": 42.59, "rel_p99": 0.02343, "rel_mean": 0.007219 } }
  },
  "placement": "s = tree_far[i].height_m / prototypes[p].height_above_base_m; the quad is a screen-facing square of side 2*radius_m*s centred at trunk_base + (0,0, centre_z_m*s). Both heights are measured from the prototype's OWN z = 0 - the plane trunk_base maps to - never from the bbox bottom.",
  "prototype_map": { "<tree_far prototype, sometimes _LOD2>": "<the _LOD1 prototype actually baked>" },
  "billboards": "join on `tree_far[i].prototype` through `prototype_map`; height_m and `placement` scale and place the quad"
}
```

### `probe` — new

```jsonc
"probe": {
  "kind": "cube", "faces": ["px","nx","py","ny","pz","nz"],   // three.js CubeTexture order, +X first
  "size_px": 512, "rendered_px": 1024, "format": "rgbe .hdr (EXR kept on disk)",
  "station": "CAM_qa_01_lagoon_hero",
  "position_blender": [x, y, z],              // the hero station MIRRORED below the water plane: z = 2*water_z - cam_z
  "position_gltf": [x, z, -y],
  "axes": "faces are rendered in BLENDER world axes and named for the THREE.js axes after the (x, z, -y) swap; face `px` looks along three.js +X",
  "samples": 64, "world_branch": "glossy",
  "use": "fallback environment for the water plane and for anything the planar Reflector cannot reach; NOT the diffuse environment (see sky.diffuse)"
}
```

### `sky.diffuse` — new entry in the existing `sky` block

QA-12b-1 measured 16.0 % of the cam02 building pixels and 21.9 % of cam06's rendering with G > R (olive-green) against
0.1 % in the Phase 5 Cycles hero, because the viewer's *diffuse* ambient came from the PMREM of the **glossy** branch.
The world's diffuse branch is a different colour (it carries the warm sun-side / anti-sun / horizon tints). Gate 3
exports it as a third equirect:

```jsonc
"sky": { "...v3 keys unchanged...": null,
         "diffuse": { "hdr": "sky_diffuse_1024x512.hdr", "exr": "sky_diffuse_1024x512.exr",
                      "w": 1024, "h": 512, "branch": "diffuse",
                      "rotation_deg": 90.0, "u_offset": 0.25,
                      "use": "PMREM source for IRRADIANCE only (scene.environment for diffuse). `sky.glossy` stays the PMREM source for specular and `sky.camera` the background sphere." } }
```

Everything a lightmap covers takes its diffuse from the lightmap, not from this. It applies to what has no lightmap:
the near trees, the impostors, the foliage and the shrubs.

### `textures.gate3` — the extension

`textures` keeps every v2/v3 key unchanged and gains, with the same shape as `textures.gate2`:

```jsonc
"textures": {
  "gate3": {
    "ktx2_dir": "../gate3/tex_ktx2",
    "encoders": { "rgbm8":  "toktx --t2 --zcmp 18 --genmipmap --assign_oetf linear   (lossless, RGBA8 resident)",
                  "gamma2": "toktx --t2 --encode uastc --uastc_quality 2 --zcmp 18 --genmipmap --assign_oetf linear",
                  "impostor": "toktx --t2 --encode uastc --uastc_quality 2 --zcmp 18 --assign_oetf LINEAR (NO mips: an octahedral atlas mips across frames). Both impostor maps go through this one encoder; `colorspace` is `linear` on both." },
    "files": { "<key>": { "path": "<file>.ktx2", "w": 2048, "h": 2048, "map": "lightmap"|"impostor_albedo"|"impostor_normal_depth",
                          "colorspace": "linear"|"srgb", "encode": "rgbm8"|"gamma2"|"uastc_astc4x4",
                          "bytes": 0, "resident_mb": 0.0, "mips": true,
                          "stats": { "min": [...], "max": [...], "mean": [...] } } },
    "bytes": 0, "resident_mb": 0.0
  }
}
```

`resident_mb` uses the same rule as Gate 2 — ASTC 4×4 on the Apple GPU (`gamma2`, `uastc_astc4x4`) = 1 byte/texel,
×4/3 for the mip chain — and **5.333 bytes/texel for an `rgbm8` (lossless, uncompressed RGBA8) variant**, which is why `default` is `gamma2`
wherever the budget is tight. A texture shipped without mips counts ×1.0.

## Gate 3 — what the bake found, and what it hands off

Every number below is `python3 export/gate3_report.py`, printed from the records; nothing is typed by hand.
65 jobs, 0 failures, 0 retries, queue wall 23 495 s (6 h 32 m) on one M2 GPU, plus a 764 s re-bake of the 16
impostor atlases after the range fix below.

**1. The blocker Gate 3 found: Gate 1's UV2 on the merged masses is margin-dominated.** Measured on
`gate1_set.blend`: the south colonnade merged mass packs **0.0095** of its 2K map (median triangle **0.21 px**
across — sub-texel), the rotunda ochre mass 0.0133, the riprap 0.0023, the site podium 0.0187, the ceiling rib
0.0178. A lightmap on that layout is **32–69 cm per texel** and cannot carry a shadow edge. `gate3_set.py`
re-unwraps UV2 for the seven assets under `UV2_RELAY_THRESHOLD` = 0.15 (smart project, island margin 0.0008),
keeps the frozen layout beside it as the `UV2_gate1` layer, and writes `out/gate3/lightmap_uv2.npz` (one float32
`(n_loops, 2)` array per Gate 1 MESH name) as the hand-off. Gain, cm/texel before → after: riprap 32.61 → 4.62,
site podium 55.07 → 12.87, rotunda ochre 68.70 → 17.39, colonnade north 37.50 → 10.64, south 38.17 → 10.95,
ceiling rib 18.11 → 5.15, colonnade walk 5.91 → 2.49. **Those seven ship `uv2_in_glb: false`** and the viewer
must not apply them until `env.glb` / `arch.glb` / `ground.glb` are re-exported against the npz. Two of them
were also baked on the frozen layout (`lmg1_*`, `uv2_in_glb: true`) so the viewer has something before the
re-export: at 38.17 cm/texel the south colonnade map costs 28.7 s to bake and carries no contact shadow.

**2. Occluders the export set does not contain, restored for the bake.** The Gate 1 set replaces the 127 far
trees with billboard quads and the lagoon water with a viewer plane. A lightmap baked against a quad has no tree
shadow where Phase 5 has one, and tree shadow is most of the per-instance variation QA-12-4 asks for
(Phase 5's own shaft-to-shaft CV is 0.469/0.539, "overwhelmingly tree shadow"). `gate3_set.py` appends the 127
real `source_tree` objects plus `ENV_lagoon_water` and `ENV_backdrop_bay` from `master_delivery.blend` and hides
the 127 quads from the rays. The 33 EXPHI hi-poly twins are asserted `hide_render` in every job. The ORN
instances carry the grey Gate 1 placeholder in `gate2_bake.blend`; `MAT_ornament_concrete` is relinked onto all
33 so the bounce off 436 ornaments is ochre, not grey.

**3. The terrain keeps a texture map, against the brief, on a measurement.** `ENV_terrain_ground` is
514 896 m² with 22 450 vertices = **4.79 m per vertex**; its own UV2 packs 0.902, which at 4K is **18.44 cm per
texel** — 26x finer than a `VERTEX_COLORS` bake could be. It ships as a 4K own map (849 s, the second longest
job). The 20 near trees do take `VERTEX_COLORS` (0.07–0.19 m per vertex, finer than their leaf cards):
14 meshes, 347 840 vertices, 803 kB npz (float32, **unencoded** since the review fix below),
`in_glb: false` until `env.glb` carries COLOR_0.

**4. Two surfaces come back almost black, and it is the geometry, not the bake.** *(The ceiling half of this
finding was diagnosed wrong and is resolved below under "QA-13-2"; the guess that the shell was drawn in front
of the rib mesh was refuted by measurement — its normals are inverted. The drum band and the lagoon bed stand.)*
`ARCH_rotunda_plaster_ceiling_merged` (756 m², 1 102 tris) has max **0.721** and 4.9 % non-zero texels;
`ARCH_rotunda_drum_band_merged` max 26.6 with 5.7 % non-zero; `ENV_lagoon_bed` 3.5 % non-zero (it is under the
water plane this bake restored — correct). These are merged masses whose area is mostly interior and backing
faces the merge carried, so most of their UV2 is enclosed surface. QA round 13 did look at the rotunda ceiling
at cam04 and the coffer field did read black (QA-13-2) — but not for the reason guessed here; see "QA-13-2"
below. `ENV_tree_broadleaf_06_LOD1` bakes to max 0.007 because it stands inside
a backdrop city block (ray cast up from its crown hits `ENV_backdropgroup_backdrop_building` at z = 15.45 m) —
the same is true of the Phase 5 renders, so the bake is faithful; it is an ENV placement defect, on record.

**5. Encoding.** `export/gate3_encode.py` is the encoder and it is a separate pass over the archival EXRs, so
`range` is each map's own maximum rather than the next power of two (that alone was worth up to a full stop:
`ARCH_rotunda_column_tan_inner_merged` max 29.085 was being encoded at range 32, the atlases at 64). Error is
reported in **stops** over the texels above 1 % of the map's own p99 — a relative error's 99th percentile is
otherwise dominated by the invisible near-black tail, which read "16.7 stops" on the drum band before the floor
was per-channel. Over all 23 maps: **gamma2 0.028–0.163 stops, rgbm8 0.009–0.058 stops, 0 clipped texels on
every map.** gamma2 is the default (1 byte/texel against 4) and rgbm8 ships beside it for anything that needs
exactness.

**6. The impostor range is the crown's p99.9, not the atlas maximum.** Un-premultiplying the Cycles Combined
pass with a 1e-4 alpha floor let a near-transparent leaf-card edge divide radiance by 10 000; the per-prototype
range came out at 6–512 while the opaque crown sits at 0.25–5, and the 8-bit codes had a mean of **5/255**
(32 % quantisation on the body). With a 0.02 alpha floor and `range = p99.9(alpha > 0.5) * 1.1` the ranges are
**2.24–6.11** and the code means **61–97 of 255**, with 3–235 saturated texels per atlas (0.002–0.18 % of the
crown). 16 prototypes, not 25: 46 of the 127 far trees were exported against an LOD2 blob and every impostor is
baked from the LOD1 mesh, so the manifest carries `impostors.prototype_map`.

**7. The probe must cull below the water plane.** The mirrored hero station is at z = −3.9, i.e. 2.6 m under the
water it reflects. With the water surface and the lagoon bed left in, the +Y (up) face came back at mean
**0.0003 / max 0.002** — black. Culling `ENV_lagoon_water`, `ENV_backdrop_bay`, `ENV_lagoon_bed` and every mesh
whose bbox tops out at or below `water_z` gives the six faces means 0.38–4.66 and the building upside down in
`pz`, which is what a planar reflection is.

**8. `sky.diffuse`, for QA-12b-1.** The world's diffuse branch as a 1024x512 equirect (1.5 s, upper half mean
5.736 against lower 0.060, so the top row is the zenith). Everything with a lightmap or a baked impostor takes
no term from it; it is the irradiance environment for the near trees, the impostors, the foliage and the shrubs,
and it replaces the glossy-branch PMREM that made 16–22 % of the cam02/cam06 building pixels read olive-green.

**9. Resident, both accountings.** Gate 3 measured **250.60 MB** against its **459 MB** reservation
(**−208.40**): lightmaps own 101.28, slot atlases 106.65, impostors 32.00 (16 x 2 atlases at 1K, no mips —
an octahedral atlas mips across frames), probe cube 8.00, sky diffuse 2.67. Against this manifest's own carried
rows the total is **1 055.17 MB**, 144.8 under the 1 200 MB line; against the viewer's *measured* texture
residency at round 12b (953.5 MB) it is **1 204.10 MB**, 4.1 over. Levers still unspent, in order of value:
the 2K impostor albedo is on disk (+50.3 MB, 170 px frames instead of 85), and the lossless rgbm8 variant of
every lightmap is on disk (+623.8 MB, exact instead of 0.028–0.163 stops).

### QA-13-2 — the rotunda plaster shell baked black because its normals are inverted (`FLIP_NORMALS_FOR_BAKE`)

**Read this before re-baking anything.** `ARCH_rotunda_plaster_ceiling_merged` is a single-sided surface whose
normals **all point up**, away from the rotunda it ceilings: `area_normal_up = 1.000`, and at cam04 every one of
its 440 visible faces has `normal · to_camera = −0.99` (`export/out/gate3/ceiling_probe.json`,
`export/gate3_ceiling_probe.py`). **A Cycles render flips the shading normal toward the incoming ray; a bake has
no incoming ray and does not.** So the first bake integrated the sealed cavity between the shell and the dome
(median ray hit 11.55 m, zero sky escape) instead of the lit rotunda below it (median 0.91 m, 59 % of rays
inside 2 m), and came back at max 0.721 / 4.9 % non-zero while the Phase 5 frame has light there.

It was **not** a UV2 problem — that was the first hypothesis and the measurement killed it: coverage 0.769 at
**1.53 cm/texel**, with the cam04-visible faces already owning **78.9 % of the asset's UV2 and 60.6 % of the
map**. Nor was it a draw-order problem: the rib/coffer mesh is correctly in front (39.4 % of the frame against
the shell's 12.55 %).

The fix is **bake-side only**. `gate3_common.FLIP_NORMALS_FOR_BAKE` names the asset; `gate3_set.py` puts
`flip_normals_for_bake` on its own job; `bake_lm.py` reverses the winding after loading the blend and before
attaching the bake target, then asserts (a) every face's UV2 corner set is **bit-identical** to before the flip,
so the map still lands on the unchanged glb, and (b) the facing actually reversed. **The blend is never saved**,
so Gate 1 geometry, UV1 and UV2 stay frozen, the glb is untouched, `lightmap_uv2.npz` is unchanged (this mesh
was never in it), and the texture keys are unchanged — **the map is replaced in place; export re-applies
nothing and the viewer renames nothing.** No other map is affected: in the other 64 jobs this shell is only an
occluder, and Cycles does not backface-cull occlusion.

Result, 1 313.8 s at 128 spp: max **0.721 → 16.755**, mean **0.000221 → 0.631**, mean-non-zero **0.0045 →
2.057**, non-zero texels **4.9 % → 30.7 %**, 0 clipped. For scale the neighbouring rib map, which QA judged
correctly lit, is mean-non-zero 1.696. Re-encoded at `range` **32.0 → 16.755**: gamma2 round-trip **0.163 →
0.0248 stops**, rgbm8 0.0039 — from the worst of the 23 maps to among the best.

**The six-station backface sweep** (`export/gate3_scene_audit.py` → `out/gate3/scene_audit.json`) found this is
the **only** non-foliage object over 200 px that is seen from behind at any QA station; the trees above it in
that list are two-sided leaf cards, which is expected. Run it again after any geometry change.

### `PFA_BAKE_DIFFUSE_WORLD` — prepared, **off**, and it should stay off

`gate3_common.BAKE_DIFFUSE_WORLD` swaps `light_probes.bake_world(scene)` — the Phase 5 sky rebuilt
`split_rays=False`, i.e. the diffuse branch applied to every ray — in for the four **bake-target** job kinds
(`own`, `own_gate1uv2`, `slot`, `vertex` = 47 of the 65 jobs, 22 499 s of the 23 419 s). It exists because
round 13 measured Eevee's light-probe capture taking the world's **camera** branch, and the same failure in a
Cycles bake would have put the plain blue sky into every lightmap where the render gets the tinted one
(QA-12b-1).

**It was tested and the hypothesis is refuted** (`export/gate3_skybranch_probe.py` →
`out/gate3/skybranch_probe.json`). Against a debug world that reports the ray class as a colour — camera red,
glossy blue, everything else green — with all 20 lamps off: the 256 px DIFFUSE bake came back
**[0.000, 0.189, 0.000] = normalised [0, 1, 0], pure green** over its 3 629 non-zero texels (R and B *exactly*
zero), and the cam02 frame's ARCH pixels **[0.108, 0.878, 0.014]**, also green. Sky pixels read
**[0.989, 0.001, 0.000]**, pure red, so the gating itself is sound. **A Cycles bake takes the diffuse branch,
exactly like the render.** Independently: the branch equirects are diffuse **[1.915, 2.314, 11.537]** vs camera
**[1.286, 1.728, 2.775]**, ratio **[1.49, 1.34, 4.16]** — the *diffuse* branch is the blue one, so a
camera-branch bake would have been *less* blue, the opposite of QA-12b-1's symptom. (The shipped
`sky_diffuse_1024x512.exr` means **[1.914, 2.319, 11.529]**, matching the diffuse equirect to three decimals, so
`sky.diffuse` carries the tinted branch as intended.)

The switch is armed **only** by `PFA_BAKE_DIFFUSE_WORLD` set to `1`/`true`/`yes`/`on`; every other value,
including `0`/`false`/`off`, is disarmed and an unrecognised value prints a warning. The environment is
inherited straight through `bake_queue.sh` → `blender_run.sh` → Blender, so `bake_queue.sh --gate3` now echoes
the armed state and the `FLIP_NORMALS_FOR_BAKE` list in its log header. Per-job the choice is recorded in
`rec["rig"]["world"] / ["world_before"] / ["diffuse_world"]`.

### Review fixes applied (docs/reviews/phase6_bake_gate3_review.md, findings 1-5, plus carries 11 and 12)

1. **The impostor placement datum.** `centre_above_base_m = centre.z - bbox_min.z` measured from the bbox bottom,
   but `impostors.placement` adds it to `tree_far[i].trunk_base`, and `s = height_m / bbox_m[2]` divided by a height
   that includes geometry below the trunk base. The datum is the prototype's **own z = 0** — in the impostor nursery
   (x −600…−420, y ≈ −570) every prototype stands on the lawn plane at z = 0, and 14 of the 16 have `bbox_min.z`
   exactly 0.0000. The two willows do not: `ENV_tree_willow_s37_LOD1` **−2.6748 m** and `ENV_tree_willow_s11_LOD1`
   **−0.7183 m** (fronds hanging below the trunk, buried in the Phase 5 scene). The manifest now carries `base_z_m`,
   `centre_z_m` and `height_above_base_m`, and `placement` is `s = height_m / height_above_base_m`, centre at
   `trunk_base + (0,0, centre_z_m*s)`. Measured before → after, per unit of `tree_far.height_m`:

   | prototype | scale denominator | centre above trunk base |
   |---|---|---|
   | `ENV_tree_willow_s37_LOD1` | 14.4175 → **11.7427** m (impostor +22.8 % bigger) | 0.500·h → **0.386**·h |
   | `ENV_tree_willow_s11_LOD1` | 12.0017 → **11.2834** m (+6.4 %) | 0.500·h → **0.468**·h |
   | the other 14 | unchanged (`base_z_m` = 0) | unchanged |

   **No re-bake.** The atlas frames are rendered about `centre` with `ortho_scale = 2*radius*(frame/inner)`, and
   neither `centre` nor `radius` changed: this is a record/manifest correction only. The measurement is the job's own
   `bbox_min` / `bbox_max` in `out/gate3/gate3_set.json` (`impostor_prototypes`), the same numbers `bake_lm.py` was
   handed, cross-checked against each record's `centre` (`centre_z - base_z == centre_above_base_m`, asserted in the
   writer). `bake_lm.py` now records the three fields directly, so a re-bake needs no derivation.
2. **The depth channel.** `bake_lm.py:295` writes `a = (z - (dist - radius)) / (2*radius)` with `dist = 6*radius`, so
   `a = 0.5` is the billboard centre plane and `dist` is never exported. The manifest said `a = depth / depth_range_m`,
   which the viewer cannot invert. It now says **`depth_from_centre_m = (a - 0.5) * depth_range_m`**, positive away
   from the camera — the same text here and in the code comment.
3 + 4. **Vertex irradiance ships unencoded.** One shared gamma-2 `range` of 64.0, set by the brightest of the 14
   near-tree meshes, cost the dim ones their code space: roundtrip `rel_p99` was 0.2442 (cypress_s41), 0.2391
   (pine_s29), 0.2264 (cypress_s3), 0.2153 (redwood_s13), 0.2085 (pine_s7), and `broadleaf_s19` (max 0.469) used
   22 of 255 codes. `vertex_irradiance.npz` is a hand-off to the export engineer, not a shipped texture, so it now
   holds **float32 `(n_verts, 3)` scene-linear RGB per mesh, no encoding at all** — `rel_p99` **0.0 on all 14**,
   read back bit-identical per mesh. 183 719 → 803 100 B. `compose.json` keeps per-mesh min / max / mean /
   mean_nonzero / p99 for the record, and `gate3_compose.py` gained `--only atlases|vertex` so the vertex pass can
   re-run without reverting the five atlas PNGs to the first-pass power-of-two range (CPU, 0.1 s, no GPU, no re-bake).
5. **The normal+depth atlas label.** `gate3_pack.sh:44` packs it `--encode uastc` (ASTC 4×4) while the manifest
   declared `rgba8_unorm`. Residency was always computed right (`resident_mb` charges 1 B/texel to anything that is
   not `rgbm8`/`rgba8`), so the **32.00 MB impostor line is unchanged**; only the label moved, to `uastc_astc4x4`,
   and `resident_mb` now asserts on an encode it does not know. The explicit decision the review asked for: the map
   **stays block compressed** while `impostors.unlit` holds and nothing samples the normal or the depth; the lossless
   repack (`toktx --zcmp`, no `--encode`) is **+3.0 MB resident per prototype at 1K, +48.0 MB over the 16**, and is
   recorded in `impostors.encode.normal_depth_note` as the lever to spend the day the viewer shades the impostor.
12. **The v4 section above now comes from a real manifest entry**, with a line saying the file wins. Five divergences
   closed: impostor albedo is gamma-2 at the prototype's own range (not "srgb + alpha"); the impostor encoder assigns
   **linear**, not sRGB, and is one encoder for both maps; `trunk_base_offset_m` and `tris` are gone (never emitted)
   and the real keys are listed; the vertex block is float32 with no `range`; and the example `range` values are real
   (`0.72`–`52.83` across the 21 maps) instead of 64.0 presented as the norm.
11. Both Blender 5.2 findings and the third engine-conditional rig are now in **docs/tech_notes.md** "Phase 6".

**The flags, from the export engineer's file, never by hand.** `manifest_v4.py` now reads
`out/gate3/uv2_relay_status.json` (schema `pfa-phase6/gate3-relay/1`) and every `uv2_in_glb` / `in_glb` comes from it.
As of this run: the **seven** re-laid assets are `true` (arch.glb 29/29 and ground.glb 4/4 meshes carry TEXCOORD_1
after the `-kv` re-pack), the two `lmg1_*` diagnostics are now `false` (inverse sense — the frozen layout they were
baked on is no longer in the glb), `lightmaps.slots.uv2_in_glb` is **false** (0 of 33 `orn.glb` meshes carry
TEXCOORD_1; the `-kv` re-pack of orn.glb was still running) and `vertex_irradiance.in_glb` is **false** — the relay
checked the npz before this branch rewrote it and recorded `dtype uint8`, so COLOR_0 was not exported. Both re-run on
the export engineer's next hand-off: re-running `python3 export/manifest_v4.py` is the whole step.

Not fixed here: carries 6, 7, 8, 9, 10, 13 and 14 stand as the review lists them.


## Gate 3 export hand-off (branch `phase6-export`, 2026-09-16)

```sh
scripts/blender_run.sh 900 -- --background export/out/gate1/gate1_set.blend --python export/gltf_gate1.py
export/gltf_pack.sh --gate1            # KTX2 + the four glbs + verify_glb
python3 export/gate3_relay_check.py    # reads the attributes BACK out -> out/gate3/uv2_relay_status.json
export/sync_main.sh
```

14. **The blocker this gate found: `gltfpack` was stripping `TEXCOORD_1` out of every glb.** gltfpack removes
    any vertex attribute no material references, and **nothing in a glb references UV2** — the lightmaps are
    separate KTX2 files the viewer attaches from the manifest. Measured on the Gate 2 glbs: `arch.gltf`
    carried `TEXCOORD_1` on **29/29** meshes and `arch.glb` on **0**; `ground.gltf` 4/4 → `ground.glb` 0;
    `orn.gltf` carried `TEXCOORD_1` (33) and `COLOR_0` (13) → `orn.glb` neither. So **no lightmap could have
    been applied to anything**, re-laid or not, and `lightmaps.assets[*].uv2_in_glb: true` on the nine Gate 1
    assets was wrong for the same reason. The fix is gltfpack's `-kv` ("keep source vertex attributes even if
    they aren't used"), given to a class exactly when its `.gltf` carries `TEXCOORD_1` or `COLOR_0`
    (`gltf_pack.sh` asks `gltf_gate1.json`), so a class with neither is packed byte-identically.
    **`orn` is excluded by hand**: `-kv` would also restore the ORN meshes' own `COLOR_0`, which three.js
    multiplies into base colour — a look change for the lead, and it leaves the ORN slot-atlas lightmap
    unusable until that call is made. `verify_glb.py` now asserts, per class packed with `-kv`, that the
    triangles carrying `TEXCOORD_1` / `COLOR_0` in the glb match the `.gltf` to within the same 1 %
    degenerate-triangle tolerance as the placement check.
15. **The seven re-laid UV2 layers are in the glbs.** `export/out/gate3/lightmap_uv2.npz` (float32
    `[loops, 2]` per Gate 1 mesh name) is loaded onto the **same** `UV2` layer — never a third layer, because
    `TEXCOORD_n` follows the UV layer order and a third one would ship as `TEXCOORD_2` — with the loop count
    asserted per mesh and `UV2` asserted to be UV layer 1. Island-area fraction of the unit square, Gate 1 →
    Gate 3 (this is the bake's own `uv2_coverage` metric, recomputed here from the glTF's indices and
    `TEXCOORD_1`): riprap 0.00229 → **0.11408** (×49.8), colonnade south 0.00950 → **0.11552** (×12.2),
    colonnade north 0.00972 → **0.12071** (×12.4), rotunda ochre 0.01328 → **0.20723** (×15.6), ceiling rib
    0.01777 → **0.21954** (×12.4), site podium 0.01870 → **0.34247** (×18.3), colonnade walk 0.12920 →
    **0.72795** (×5.6). Three of the seven still pack under the 0.15 relay threshold; the bake measured the
    same and baked against this layout, so that is reported, not asserted — what is asserted is that the
    layer changed and that it packs more than Gate 1's.
16. **`COLOR_0` for the near trees is NOT in the glbs yet.** `export/out/gate3/vertex_irradiance.npz` shipped
    as **uint8** gamma-2 codes at one shared range of 64, not the float32 scene-linear per mesh the manifest
    and this README promise (`docs/reviews/phase6_bake_gate3_review.md` findings 3-4), and the bake is
    re-writing it. `gltf_gate1.py` reads the dtype and **refuses to encode `COLOR_0` from anything but the
    float32 file**: the encoding that ships depends on the real per-mesh range, and a wrong one is invisible
    in the glb and wrong in every frame. `lightmaps.vertex_irradiance.in_glb` stays **false**. When the
    float32 npz lands, the encoder and the value tests in `gate3_relay_check.py` change together — the
    attribute is written as `FLOAT_COLOR`/`POINT` (never `BYTE_COLOR`, which is sRGB in Blender and would be
    linearised on export), the exporter's `export_all_vertex_colors` is already `True`, and gltfpack
    quantises colours to **8 bits by default** (`-vc N`), so whatever encoding is chosen has to live in
    `[0, 1]` and survive 8-bit — or `-vc 16` has to be added to `env`.
17. **The hand-off file.** `export/out/gate3/uv2_relay_status.json` (`pfa-phase6/gate3-relay/1`) is written by
    `export/gate3_relay_check.py`, which reads the attributes back out of the exported files — never from the
    script that wrote them — and carries `{mesh: {uv2_in_glb, coverage, glb, asset, …}}` for the seven and
    `{mesh: {in_glb, encoding, mean, …}}` for the near trees. **The manifest writer flips
    `lightmaps.assets[*].uv2_in_glb` and `lightmaps.vertex_irradiance.in_glb` from that file; nobody edits
    `manifest.json` by hand.** `export/sync_main.sh` copies `out/gate3/` to MAIN with no `--delete` and
    excludes the bake's blends, so the export only ever adds its own file there.
18. **What it cost and what verify says.** `arch.glb` 3 589 032 → **4 609 468 B** (+1.02 MB, +28 %) and
    `ground.glb` 1 238 288 → **1 959 104 B** (+0.72 MB, +58 %) for `-kv`; `env.glb` (35 797 240 B) and
    `orn.glb` (154 065 360 B) are byte-identical, so the payload grows **1.74 MB** in total and nothing else
    moves. `verify_glb` PASS: arch 947 622 drawn triangles (−0.185 % against `export_set.json`, the usual
    degenerate-triangle loss), orn −0.157 %, env and ground 0.000 %, 15/15 + 62/62 material names kept under
    `-km`, 0 objects at the origin; `TEXCOORD_1` reaches **349 614 of arch's 351 374** triangles (−0.5 %) and
    **113 043 of 113 043** on ground. `export/name_sweep.py`: 2 540 objects, 127 exempt, **0 to explain**.
    `gate3_relay_check.py`: all seven re-laid layers in the glbs, ≥ 99.97 % of their exported `TEXCOORD_1`
    values found in the npz. 66 meshes carry `TEXCOORD_1` in the glTFs (29 arch + 4 ground + 33 orn); the 33
    `orn` ones are still stripped by the pack and are the open item.
19. **ORN (lead's decision, docs/decisions.md 2026-09-16).** The `COLOR_0` on the ORN prototypes is the
    `cavity` FLOAT_COLOR attribute (`scripts/orn_lib.py vertex_cavity`) the ornament material reads for recess
    dust, and the Gate 2 albedo bake already contains it — shipping it would apply the dust twice, because
    standard glTF multiplies `COLOR_0` into base colour. `gltf_gate1.py` removes colour attributes from the
    **export copies** (26 meshes; the source blend is only ever read) except the near-tree irradiance, so
    `orn` can take `-kv`: `orn.glb` 154 065 360 → **154 253 424 B** (+188 KB) and now carries `TEXCOORD_1` on
    **112 533 of 112 533** triangles (all 33 prototypes) and no `COLOR_0`. `verify_glb` asserts both, and that
    no class exports `COLOR_0` for a mesh that is not near-tree irradiance. All **66** UV2 meshes
    (29 arch + 4 ground + 33 orn) are now `uv2_in_glb: true` in `uv2_relay_status.json`.
20. **The near-tree `COLOR_0` (Gate 3 hand-off 2, resume r2).** `out/gate3/vertex_irradiance.npz` is now the
    corrected float32 scene-linear file (phase6-bake ac63e44), and `gltf_gate1.py` encodes it per the lead's
    decision (docs/decisions.md 2026-09-16): **gamma-2 at a PER-MESH range**, `code = sqrt(v / range)`,
    `range` = that mesh's own max, written as a `FLOAT_COLOR`/`POINT` attribute named `irradiance` and packed
    with `-vc 16` on `env` only. Per-mesh ranges span **0.469 to 43.32** — 6.5 stops — which is why one shared
    range was refused: at range 64 the darkest mesh would have used 8 % of the code space.
    The decode the manifest publishes is `v = COLOR_0² · range_mesh`, then `irradiance = v · lightmaps.scale`.
21. **Blender writes a FAKE white `COLOR_0` and pushes the real data to `COLOR_1`.** With
    `export_all_vertex_colors=True`, `io_scene_gltf2/blender/exp/primitive_extract.py` (5.2, ~line 818) does:
    *if the material's node tree references no colour attribute and the mesh has one, insert a "fake Vertex
    Color" as `COLOR_0`* — a constant-white `UNSIGNED_BYTE` VEC4 — and append the real attribute as `COLOR_1`.
    The near-tree materials read colour from textures, never from an attribute, so the first run shipped
    `COLOR_0` with min = max = 1.0 on all 14 meshes and the irradiance hidden in `COLOR_1` (measured:
    `COLOR_0` u8 constant 1.0, `COLOR_1` u16-normalised, mean 0.1097). *This is also what the earlier README
    note meant by "orn.gltf carries the ORN meshes' COLOR_0/COLOR_1" — the ORN `cavity` was `COLOR_1` too.*
    `gltf_gate1.py` now drops the fake and renumbers, **proving** which is which rather than assuming: the
    fake is the `UNSIGNED_BYTE` set whose every value is 1.0, there must be exactly one of it and exactly one
    survivor, and the survivor must be `UNSIGNED_SHORT`/float. 27 primitives fixed on `env`, and the file is
    asserted to end with `COLOR_0` and nothing else. Blender writes a `FLOAT_COLOR` attribute as a **16-bit
    normalised** accessor, so the gamma-2 code keeps a 1/65535 step end to end (`-vc 16` stops gltfpack
    requantising it to 8; the packed `env.glb` carries 5123/VEC4/normalized on all 14).
22. **The colonnade colbase merge (viewer round-13 finding 2), and why the fix is not `-kn`.** gltfpack merges
    two meshes when they share a material **and** their node transform SETS are identical. The colonnade
    `colbase_###_plinth` (12 tris) and `colbase_###_torus` (600 tris) sit at the same origin with no rotation,
    so gltfpack merged each pair into one 612-tri mesh: arch.glb drew **438** of the 988 per-instance lightmap
    slots, 56 + 58 = **114** short, and the surviving mesh took ONE slot for both halves. The rotunda pairs
    escaped only because their plinth carries a rotation the torus does not. Both options were measured on the
    same `arch_ktx2.gltf`:
    | option | arch.glb | Δ bytes | draw calls | placements | slots reached |
    |---|---|---|---|---|---|
    | as shipped | 4 609 468 | — | 27 | 442 | 438 / 988 |
    | `-kn` | 4 662 020 | **+52 552** | **564** | 564 | 988 |
    | material split (shipped) | 4 613 040 | **+3 572** | **29** | 556 | **988** |
    `-kn` reaches 988 only by disabling `-mi` (gltfpack 1.2 warns "-kn disables mesh merge (-mm) and mesh
    instancing (-mi)"), which costs 537 draw calls — every colonnade column drawn one at a time. What ships
    instead breaks the merge KEY: `gltf_gate1.py` gives the second mesh of each colliding group its own copy
    of the material **under the same name**, so `-km` (already on arch, and it disables named-material
    merging) keeps them apart and both meshes stay instanced. The viewer matches materials by name
    (`web/src/pbr.js candidateKeys`, `web/src/detail.js`), so a duplicate name resolves to the same Gate 2
    texture set and nothing downstream sees a new material. The collision is DETECTED, not hard-coded — any
    two meshes sharing a material and a transform set are split — and after the split `gltf_gate1.py` asserts
    no collision survives. `verify_glb.py` now also asserts, per class, that `placements_in_glb` covers that
    class's share of `orn_slots` (arch 556 ≥ 552, orn 436 ≥ 436), which is the regression guard: the old pack
    would have failed it.
23. **What resume r2 cost.** `arch.glb` 4 609 468 → **4 613 040** (+3 572 B, the material split) and
    `env.glb` 35 797 240 → **36 951 988** (+1 154 748 B, +3.2 %: `-kv` plus the 14 meshes' 16-bit `COLOR_0`).
    `orn.glb` (154 253 424) and `ground.glb` (1 959 104) are byte-identical. `verify_glb` PASS (arch −0.185 %,
    orn −0.157 %, env and ground 0.000 % against `export_set.json`; `COLOR_0` reaches 274 162 of env's
    274 162 `COLOR_0` triangles; 0 objects at the origin). `gate3_relay_check` PASS: every exported code sits
    **7.6e-6** from this mesh's own gamma-2 code — exactly the 0.5/65535 bound — and the 16-bit round trip's
    p99 relative error is **≤ 0.7 %** on every mesh whose mean is above 0.01 (the two near-black meshes,
    broadleaf_s19 at 9e-6 and pine_s29 at 1.1e-3, read 2.8 % and 7.6 % of a value no frame can show).
    The per-vertex mean ratio glb/npz is 0.89-1.31 because the exporter splits 6-36 % more vertices; the
    assertion is on the mean of the DISTINCT values, which a split cannot move (within 1 % on all 14).
    `export/name_sweep.py`: 2 540 objects, 127 exempt, **0 to explain**.
24. **Review fixes (docs/reviews/phase6_export_gate3_review.md, findings 1-3, all three "fix now").**
    (1)+(2) The encoder and the checker now resolve the Gate 3 hand-off **the same way**: MAIN's
    `export/out/gate3`, through `PFA_MAIN_ROOT` (`gate3_relay_check.py` `__main__`; it used to hard-code the
    MAIN path and to prefer a LOCAL `out/gate3` whenever one held a `lightmap_uv2.npz`, so it could have
    validated the glbs against a file `gltf_gate1.py` never read). A missing npz now prints which file and
    which directory and exits 1, instead of raising `FileNotFoundError` out of `np.load`.
    (3) The material-split guard is **bidirectional**: a class with duplicate names but no split still fails,
    and now a split class must also carry `-km` **and** show at least `len(split)` duplicate names in the
    packed glb. `-km` is on arch and env only; **orn and ground are packed `-cc -mi -kv` with no `-km`, and
    neither is split today** (`merge_split`: arch 2 meshes, orn/env/ground none) — the guard makes that a rule
    instead of a coincidence, so a future split on either fails loudly rather than being merged back in
    silence. Verified by a negative run with a fake split injected on orn: both new assertions fire.
25. **`docs/briefs/phase6_budget.md` is stale for arch and env** (the lead owns that file; not edited here).
    It predates the Gate 3 re-packs: arch.glb is **4 613 040 B** at **29 draw calls** (was quoted before the
    `-kv` re-pack and the slot-merge material split) and env.glb is **36 951 988 B** (before `-kv`, `-vc 16`
    and the 14 meshes' `COLOR_0`). orn.glb (154 253 424 B) and ground.glb (1 959 104 B) are unchanged.
26. **The near-tree `COLOR_0` range is GLOBAL, not per mesh (viewer round 13b; lead's decision).** The viewer
    cannot apply a per-mesh range: `gltfpack -mi` splits each tree by material and instances the resulting
    primitives **across** trees, so the 14 baked buffers arrive as 14 primitives over 26 placements and only
    2 join back to a mesh unambiguously. `gltf_gate1.py` now encodes every mesh at **one range** read from the
    npz on every run (**43.31984** at r2; **44.25656** after the shadow-ray re-bake, export r6)
    (the max over all 14 in `vertex_irradiance.npz`), still gamma-2, `FLOAT_COLOR`, `-vc 16`, same `-mi`.
    `uv2_relay_status.json` carries `vertex_irradiance_range_global` once and `range` on each row (the same
    number); `manifest_v4.py` copies it to `lightmaps.vertex_irradiance.range` — **one number the viewer
    reads** — and asserts it exists whenever `in_glb` is true. The cost, measured per mesh (16-bit round-trip
    p99 relative error, global vs per-mesh): pine_s7 **0.92 %** / 0.68, cypress_s3 0.61 / 0.45, cypress_s41
    0.69 / 0.37, cypress_column_s31 0.32 / 0.23, redwood_s13 0.28 / 0.25, redwood_s43 0.26 / 0.19,
    cypress_s17 0.23 / 0.22, euc_s23 0.15 / 0.15, euc_s5 0.14 / 0.14, cypress_column_s2 0.16 / 0.16,
    euc_s61 0.07 / 0.07, willow_s37 0.03 / 0.02. **Worst is 0.92 %, the gate was 2 %.** The two meshes the
    global range really costs — broadleaf_s19 26 % and pine_s29 14 % — have mean irradiance 9e-6 and 1.1e-3:
    they sit in full shadow and no frame can show it. The declined alternative was keeping the 14 trees out
    of `-mi`. `env.glb` 36 951 988 → **36 945 984 B** (−6 004; one range compresses marginally better).
27. **`compositor.mist` (the manifest recorded the haze ramp as a zero).** `COMP_golden_hour`'s `Mist` group
    input reads **0.0** in the carried `compositor` block, which is only what a *disconnected socket's stored
    default* reports — the live value is the Mist **pass** the Render Layers node feeds it, and that pass is
    shaped entirely by `scene.world.mist_settings`. `export/read_mist.py` (read-only, no render, no save,
    through `scripts/blender_run.sh 600`) reads them out of `master_delivery.blend` into
    `out/gate3/mist_settings.json` (`pfa-phase6/gate3-mist/1`), and `manifest_v4.py` copies them into
    `compositor.mist` with the formula and the units. Measured: **`use_mist` true, `start` 20.0 m, `depth`
    2000.0 m, `falloff` LINEAR, `height` 0.0, `intensity` 0.0**, view layer `use_pass_mist` **true**, scene
    unit scale 1.0. So `mist = clamp((dist − 20) / 2000, 0, 1)` along the view ray, in metres, no height
    falloff and no floor — a ramp that only reaches 1.0 at 2 020 m, which is why the haze reads as gentle.
28. **Review r3 fixes (docs/reviews/phase6_export_gate3_r3_review.md, both "fix now").**
    (1) A glb is now **pinned to the glTF it is checked against**. Both checks read the Gate 3 attributes out
    of `<cls>.gltf` and their presence out of `<cls>.glb`, so a glb older than its source describes a file it
    was never packed from — and neither check would catch it, because `verify_glb` compares triangle *counts*
    and material *name sets*, never UV values or primitive→material order. `verify_glb.py` (class loop) and
    `gate3_relay_check.py` (before the npz reads) now FAIL when `<cls>.gltf` or `<cls>_ktx2.gltf` is newer
    than `<cls>.glb`, 1 s of slack for filesystem granularity. Verified: against the carried-over state they
    reported arch/orn/ground stale (14:48:10 glTF vs 14:15:49 glb).
    Then `export/gltf_pack.sh --gate1` re-packed all four from this run's glTFs (no Blender; toktx re-encoded
    all 85 KTX2 in 203 s, which is why the env-only shortcut was taken the round before). **All four glbs came
    back byte-identical** — arch 4 613 040, orn 154 253 424, env 36 945 984, ground 1 959 104 — which also
    proves after the fact that the carried-over glbs were the right ones. No class glb is carried any more.
    (2) `manifest_v4.py` resolves `mist_settings.json` **local-then-MAIN**, the same `next(...)` the relay json
    uses, because `export/out/` is gitignored and a local-only lookup would have dropped `compositor.mist`
    silently after the merge. When neither exists it prints a WARNING naming the `read_mist.py` command and
    records `compositor.mist = null` with `mist_missing` saying why, instead of leaving the block absent.
29. **Every leaf card shipped OPAQUE (viewer, cam02).** A glTF material with no `alphaMode` is OPAQUE by
    spec, and none of the foliage materials declared one — so every near-tree leaf card drew as a solid
    metre-wide rectangle across a third of cam02. **Eight** materials were affected, all in `env`, all with an
    RGBA base-colour PNG whose alpha *is* the leaf shape: `MAT_leaf_broadleaf` (leaves_broadleaf.png),
    `MAT_leaf_cypress` (needles_cypress.png), `MAT_leaf_eucalyptus` (leaves_eucalyptus.png), `MAT_leaf_pine`
    (needles_pine.png), `MAT_reeds` (reeds.png), `MAT_shrub`, `MAT_shrub_light`, `MAT_shrub_dry` (all three
    leaves_shrub.png). **All eight take `alphaMode: MASK` at `alphaCutoff` 0.5.**
    The cutoff is read, not guessed. `export/read_alpha.py` (read-only on `master_delivery.blend`, no render,
    no save) dumps every material whose node tree reaches an RGBA image — **including inside node groups**,
    which is the whole trick here: these materials feed their Principled through a group and their Image
    Texture nodes have no links in the material's own tree, so the Principled `Alpha` input is *unlinked at
    1.0* and a "follow the Base Color link" test finds nothing. No material has a Math `GREATER_THAN` in an
    alpha chain, so the clip value is each material's own **`alpha_threshold` = 0.5**, under
    `blend_method HASHED` / `surface_render_method DITHERED` — Blender clips them stochastically and 0.5 is
    the deterministic threshold the file states. All 28 materials it found agree on 0.5; `gltf_gate1.py`
    additionally asserts the hand-off against its own copy of each datablock before writing the mode.
    **Which** materials get it is decided by the exported file, never by a name list: the material's
    `baseColorTexture` PNG header must carry alpha (colour type 4 or 6). That is why the 20 `MAT_ornament_*`
    materials that also report `alpha_threshold` 0.5 are untouched — their colour ends up on the 8x8 UV1
    probe, which is RGB. `alpha_cutoffs.json` resolves **local-then-MAIN** (it is the export's own hand-off,
    like `uv2_relay_status.json`, not the bake's MAIN-only npz).
    `verify_glb.py` now asserts, per class, that every material recorded with an alpha-carrying
    baseColorTexture is `MASK` or `BLEND` in the **packed** glb and that its *effective* cutoff matches —
    gltfpack legitimately drops `alphaCutoff` when it equals the glTF default of 0.5, so the check compares
    the effective value or a non-default cutoff would silently fall back and still pass.
    Cost: `env.glb` 36 945 984 → **36 946 136 B** (+152). arch, orn and ground byte-identical. The stale-glb
    pin from item 28 required the full `gltf_pack.sh --gate1`, so toktx re-encoded all 85 KTX2 (258 s) —
    an env-only re-pack is no longer possible once the other three glTFs have been regenerated.
30. **Correction to item 29: `material.alpha_threshold` is NOT the cut (r4 review).** It is Blender's factory
    **0.5 on every material in the file** and is inert under `blend_method HASHED` /
    `surface_render_method DITHERED` — so reading it was right for six materials by coincidence and wrong for
    two. The real cut is built by `scripts/mat_build.py leaf_material` (~1385-1417): the material output's
    Surface is a **Mix Shader** between a **Transparent BSDF** and the shaded branch, and its factor is a
    **Map Range** over the base-colour image's `Alpha`, `From Min = alpha_cut − 0.15`,
    `From Max = alpha_cut + 0.15`. The 50 % crossing — the one number a glTF `alphaCutoff` can express — is
    the **midpoint**, i.e. `alpha_cut` itself. `read_alpha.cut_chain()` walks exactly that graph and returns a
    **reason** rather than a default on anything else; a file-backed alpha card that does not resolve is a
    hard failure, and the script asserts it is running on `master_delivery.blend`.
    The eight, as read: **MAT_leaf_cypress 0.45**, **MAT_leaf_pine 0.42** (`mat_build.py` ~1738-1741),
    MAT_leaf_broadleaf / MAT_leaf_eucalyptus / MAT_reeds / MAT_shrub / MAT_shrub_light / MAT_shrub_dry 0.5.
    `gltf_gate1.py` imports `cut_chain` (read_alpha's discovery run is guarded by `__main__`) and re-walks the
    graph on its **own copy** of each material — comparing against `alpha_threshold` would have agreed with a
    wrong number, since it reads 0.5 for the two that are not.
    **glb evidence:** `env.glb` carries `alphaCutoff` **0.449999988** on MAT_leaf_cypress and **0.419999987**
    on MAT_leaf_pine (float32 of 0.45 / 0.42), and omits the field on the six at 0.5 — gltfpack drops it only
    when it equals the glTF default, and `verify_glb` compares the *effective* value so a dropped non-default
    would fail. `verify_glb.json` records env `alpha_cutout_cutoffs: [0.42, 0.45, 0.5]`.
    Also closed (r4 carry, same defect class): `png_has_alpha` no longer returns `None` for an unrecognised
    format and silently skips the material — it returns False only for a JPEG (which never has alpha) and
    **raises** otherwise, because a texture whose alpha cannot be tested is a card that ships opaque in
    silence. `env.glb` 36 946 136 → **36 946 188 B** (+52); arch, orn, ground byte-identical.

31. **Gate 4 — the 1 379 shrub/reed placements' irradiance, ordered against `env.glb` itself** (export r5).
    The bake hands over `out/gate3/instance_irradiance.json`: one scene-linear RGB per **placement** of the 28
    card meshes. The viewer uploads those as an `InstancedBufferAttribute`, which is indexed by **glb instance
    row**, and `gltfpack -mi` re-orders the rows, drops every node name (gltfpack 1.2 refuses `-kn` with
    `-mi`) and merges meshes — so the file's own array order is not the contract and, per
    `docs/reviews/phase6_bake_gate4_instance_review.md`, **a name cannot be recovered from the glb at all**.
    The join is therefore positional, and the pipeline is:
    ```sh
    node web/tools/instance_rows.mjs export/out/gate1/env.glb export/out/gate3/instance_rows.json
    python3 export/gate4_instance_order.py      # -> out/gate3/instance_order.json (tolerance 0.02 m)
    python3 export/verify_glb.py                # the Gate 4 row-count gate (also inside gltf_pack.sh --gate1)
    python3 export/gate4_order_selftest.py      # 10 negative cases against the same check
    python3 export/manifest_v4.py && export/sync_main.sh
    ```
    **Re-run the whole chain after every re-bake.** `manifest_v4.py` refuses a stale join: it asserts the order
    file's `irradiance_sha256` and `irradiance_generated` against the `instance_irradiance.json` on disk and its
    `glb_bytes` against `env.glb` (the bake added `loc` to the file on 2026-09-17 without changing `generated`,
    which is exactly why the hash, not the timestamp, is the pin).
    `instance_rows.mjs` is node, not python, because every accessor in the packed glbs rides in an
    `EXT_meshopt_compression` bufferView: it loads `env.glb` through three's `GLTFLoader` + `MeshoptDecoder`
    and dumps each `InstancedMesh`'s rows in accessor order, with the glTF node index from
    `parser.associations` as the stable key. `gate4_instance_order.py` then converts each placement's Blender
    `loc` to glTF space — **Blender (x, y, z) → glTF (x, z, −y)**, asserted on the seven bake-measured
    `checks.dark` locs against the pre-pack `env.gltf` node translations (0.6 mm, the JSON's 3-decimal
    rounding) — decides per node which mesh(es) it draws by containment, and matches rows to placements
    one-to-one by nearest translation: tolerance **0.02 m** (the value the bake states), runner-up at least
    **3x** further. Measured:
    worst residual **5.9 mm** (gltfpack recentres a merged mesh, so the residual is that offset, not noise)
    against a smallest within-node placement separation of **88 mm**, worst margin **55x**, **1 379/1 379**
    rows over **28/28** meshes and **25** instanced nodes — the shipped `instance_order.json` carries those two
    numbers itself (`worst_residual_m`, `worst_margin_ratio`), so read them there rather than from this text. Any unmatched row, duplicate match or mesh found in
    two nodes is a hard failure — a silently swapped pair lights two shrubs with each other's irradiance. The
    object name rides along as a label and is cross-checked against the nearest `env.gltf` node, never joined
    on. `PFA_INSTANCE_IRR=<file>` runs the same join against a candidate JSON without touching the synced one.
    **The name fallback is opt-in and unshippable.** If any placement lacks `loc` the join exits; only
    `PFA_INSTANCE_ORDER_HARNESS=1` takes the positions from `env.gltf` by object name, and that output is
    stamped `loc_in_json: false`, on which `manifest_v4.py` emits no array at all and `verify_glb.py` raises a
    failure as soon as the irradiance JSON does carry `loc`.
    **What it found:** gltfpack merged `EXPM_ENV_src_{maho2,pitto5,reed1}_LOD2.001` — each a one-placement
    near-duplicate of its base mesh — into the base mesh's node, so glTF nodes 10 / 16 / 21 hold 46 / 102 / 76
    rows against their base mesh's 45 / 101 / 75, with the odd row *inside* the run (rows 8, 14, 22). A viewer
    binding one mesh's array to those nodes is one row short and misaligned from that point on, so the
    manifest block carries `nodes[*].segments` — an ordered **`[mesh, count, offset]`** list per node — beside
    the per-mesh arrays. A mesh therefore owns **two** segments in those nodes (`8 @0 + 1 @0 + 37 @8` on node
    10), and `offset` is the row index into that mesh's own array: read the segments with a running cursor,
    never one slice per mesh, or 37 mahonias take the irradiance of placements 0-36. `verify_glb` checks the
    offsets tile each mesh's array exactly once.
    **env.glb is not re-packed** (byte-identical, 36 946 188 B): the order is fully recoverable, no `COLOR_0`
    changes and nothing is re-decimated, so `lightmaps.instance_irradiance.in_glb` stays **false** and the
    data ships in the manifest: measured on the current artefacts, the block adds **107 kB** (1 852 075 B →
    1 959 199 B) — worth serving gzip/br on the 6b host, since the manifest blocks the first frame. `verify_glb.py`
    asserts the data against the glb: every node named is really instanced, its `TRANSLATION` accessor count
    equals its segment total, the segment offsets tile each mesh's array once, and each of the 28 meshes gets
    exactly its placement count of rows (`gate4_instance_irradiance.counts_match`). The MAIN `manifest.json` is
    written by the lead's own `manifest_v4.py` run, so the size above is measured, not shipped by this branch.

32. **Export r6 — the shadow-ray re-bake re-encoded** (2026-09-17, against `phase6-bake f9feec3`). Both hand-off
    files were re-baked with shadow rays, so both were re-run through the unchanged r2/r5 chain, in order:
    `gltf_gate1.py` (COLOR_0 from the new `vertex_irradiance.npz`), `gltf_pack.sh --gate1`,
    `gate3_relay_check.py`, `instance_rows.mjs`, `gate4_instance_order.py`, `verify_glb.py`,
    `gate4_order_selftest.py`. **COLOR_0:** one global range **44.25656** (was 43.31984 — the max moved only
    2 %, but the per-mesh means rose 2.6-5.0x on the twelve trees whose coverage rose, and broadleaf_s19 /
    willow_s37 are unchanged at 1.0x); the 16-bit round trip's `roundtrip_rel_p99` is **<= 0.47 %** on every
    mesh with a mean above 0.01 and 28 % / 21 % on the two in full shadow (means 8e-6 and 0.0045), the same
    structural result as r2 and for the same reason. **The glbs:** `env.glb` **36 946 188 -> 38 119 568 B**
    (+1 173 380, the denser COLOR_0 codes at `-vc 16`); arch, orn and ground are byte-identical.
    **The join, on the new glb:** 1 379/1 379 rows, 28/28 meshes, 25 nodes, worst residual **5.8 mm**, worst
    margin **68.7x**, axis swap off by **0.1 mm** on the seven bake-measured locs (the new JSON carries `loc`
    to 4 decimals). `verify_glb` PASS, `gate4_order_selftest` 10/10. The stale guards both fired on the way
    through and are the reason the order was re-run at all: `verify_glb` refused the old order file against
    the new `env.glb` by size, and `manifest_v4` refuses it against a different `instance_irradiance.json` by
    sha256 — verified by hand on this round's files.

33. **`export/sync_main.sh` no longer copies `bake_queue/status.json`** (lead, 2026-09-17, 6c). That file is the
    **GPU lock**, not an artefact: every agent reads MAIN's copy to decide whether the GPU is busy, and an
    export sync was pushing this worktree's stale copy over it - harmless while both were idle, but mid-bake it
    tells the viewer's headless Chrome the GPU is free. The bake engineer's queue and `gpu_lock.sh` write MAIN's
    copy themselves; the sync only does it when **`PFA_SYNC_STATUS=1`** says the caller is the queue. Everything
    else in the sync is unchanged (still no `--delete`).

## Phase 6c (bake engineer's notes, branch `phase6-bake`, 2026-09-17)

*Two agents appended to this file in the same round and their item numbers overlap. Both tails are kept
verbatim under their own heading: a reference to "item 37" means item 37 of the section it is written in
(`export/README.md items 33 and 35-38` in the bake's commits = this section; item 34-46 references in
`export/trees_far.py`, `foliage_tex.py` and the export commits = the section below).*

35. **6c item 1 — the impostor blue is in the ATLAS, and a re-bake with the diffuse-branch sky will not fix
    it** (2026-09-17, `export/imp_diag_atlas.py`, `imp_diag_ref.py`, `imp_diag_view.py`, `imp_diag_sheet.py`;
    sheet `renders/web/960/6c_impostor_diag.png`, JSONs in `out/gate3/impostor_diag_*.json`). Test tree:
    `ENV_tree_broadleaf_s53_LOD1`, the far tree that stands on the axis of station 2 at 40.2 m
    (`tree_far[0]`), frame **col 1 row 7** — the frame `impostors.frame_lookup` picks from that station.
    * **The shipped atlas is blue by itself.** Decoded with the manifest's own rule, the crown (alpha > 0.5)
      of that frame is linear **[0.186, 0.275, 0.372]**, hue **211.4 deg**, B/G **1.356**. Over all 16
      prototypes the whole-atlas crown hue is **149-257 deg** with B/G **0.87-1.52** and 40-63 % of crown
      texels having BLUE as their maximum channel. Sun-facing frames are green (41-72 deg); it is the
      sky-lit side of the octahedron that is blue.
    * **The encode chain is exact.** A fresh 64 spp Cycles render of the same prototype at the same view and
      the same rig reads **[0.193, 0.274, 0.375]**, hue **213.2**, B/G **1.367** — within 4 % of what the
      atlas decodes. Nothing is lost or shifted between Cycles and the gamma-2/`range` encode.
    * **The diffuse-branch sky is not the cause.** The same view with `light_probes.bake_world` (the world's
      diffuse branch on every ray) reads hue **215.6**, B/G **1.431**: a **2.4 deg** move, in the wrong
      direction. Re-baking the 16 prototypes that way would spend 16 GPU jobs and change nothing.
    * **Ground truth.** The same tree as a MESH in the Phase 5 Cycles reference at station 2
      (`renders/previews/qa/round13_02_..._cycles.png`, projected by `imp_diag_ref.py`) is display-referred
      sRGB **[18.6, 17.6, 11.4]**, hue **52.2 deg**, B/G **0.648**. Through the same AgX High Contrast at
      -2.833 EV the atlas frame is **[17.8, 32.2, 38.8]**, hue **199 deg**, B/G **1.207**: the same
      brightness in R, **1.8x** the G and **3.4x** the B, **147 deg** of hue apart.
    * **Where the blue comes from.** Decomposed at the same view: **sun only** (no world) is
      **[0.113, 0.112, 0.000]**, hue 59.4, B/G **0.0**; **sky only** (every light hidden) is
      **[0.078, 0.157, 0.387]**, hue 224.6, B/G **2.458**, 82 % blue-max. The leaf albedo carries no blue at
      all, so **100 % of the impostor's blue channel is the sky term**, and the nursery
      (`gate3_imp.blend`: one prototype alone on a lawn) gives every prototype the whole unoccluded sky dome.
      In the delivery scene the same tree stands in a thicket in front of the sunlit ochre building, so that
      sky term is mostly occluded and replaced by warm bounce — which is exactly what the reference shows.
    * **So the fix is context, not a re-bake of the same isolated tree**: the per-placement irradiance and
      vertex AO of 6c item B (and the far-tree meshes of item A) are what carry the occlusion the nursery
      cannot know. Whatever still draws an impostor beyond `treeMeshDist` needs the same per-placement
      modulation, or its sky term has to be baked with the scene around it. That call is the lead's.

36. **Round-1 review, carried open items (bake).** `docs/reviews/phase6c_bake_r1_review.md` items 8-10, left
    open by the lead's instruction, all in the item-1 diagnosis tooling and none of them affecting a shipped
    number: (8) `imp_diag_atlas.py:33`, `imp_diag_ref.py:28`, `imp_diag_sheet.py:24` and
    `imp_diag_view.py:59` hard-code the MAIN path instead of
    `os.environ.get("PFA_MAIN_ROOT", "<default>")` as every other export script does; (9)
    `imp_diag_ref.py`'s `foliage_p80` is a fixed quantile rather than a sky test, so the ground-truth crop
    keeps sky when there is more than 20 % of it and throws away sunlit leaves when there is none - the
    147 deg hue gap dwarfs that bias, and the same caveat is written into `trees_far/ratio_check.json`;
    (10a) `imp_diag_sheet.py:70-82` re-derives the crop without `shift_x`/`shift_y` and with a wider box than
    `imp_diag_ref.py` (harmless only because station 2's shifts are 0); (10b) "sun-facing frames are green
    (41-72 deg)" in item 35 has no script that selects frames BY sun direction - 41.4 deg is the lowest
    *nearest-cam02* frame hue in `impostor_diag_atlas.json`, so read it as that. Review item 3 is fixed
    (`imp_diag_view.py` now merges variants into one report and the usage line tees the run), but **the
    `asis` 213.2 / 1.367 and `diffuse` 215.6 / 1.431 headline numbers in item 35 and in docs/decisions.md
    come from the run that the old fixed path overwrote**; they were not re-spent on the GPU. Review item
    10c is fixed by shipping `trees_far/instance_irradiance.json` at schema
    **`pfa-phase6/gate4-instance-irradiance/2`** (the shrub file stays at /1).

37. **The far-tree placement anchor: one definition, the export's - and the bake's first run used another**
    (corrected 2026-09-17 after `docs/reviews/phase6c_bake_r2_review.md` finding 1; supersedes what this
    item said before). `export/trees_far.py` DOES subtract an anchor: `:301` takes the LOD2 mesh's **bbox XY
    centre at z = 0** - the point the impostor rotates about - asserts it against the manifest's `radius_m` /
    `base_z_m`, and `:335` transforms the mesh by `Translation(-anchor)` before the 127 placements set
    `location = trunk_base, scale = s`. That is the definition, it is computed once, and it now ships in
    `topology.json` as `prototypes[p].anchor`. **The bake's first run derived a different one** - the
    prototype OBJECT's world translation out of `gate3_imp.blend` - and the two differ by up to
    **(3.44, 2.66) m** (pine_s7, pine_s29; over 1 m on six prototypes), so the first `E_placement` set was
    baked with trees up to ~2.2 m x s from where `env_trees.glb` draws them. The four `tfirr_*` jobs were
    re-run against the export's anchor; `trees_far_set.py` now READS it and refuses to start if
    `topology.json` does not carry it. What let the error through was review finding 2: the old assert,
    `matrix_world @ (anchor.x, anchor.y, 0)` against `trunk_base`, is an algebraic identity for
    `T(loc) @ S @ T(-anchor)` and passes whatever anchor it is handed. It is now an assert on the **placed
    mesh's WORLD bbox against `topology.json`'s own `placed_bbox_min` / `placed_bbox_max`** - which
    `export/trees_far.py` computes independently - at **0.005 m**, plus the bottom against
    `loc.z + bbox_min.z * s` at **0.05 m**; worst residual **7e-05 m over 127/127 rows**. Note what it is
    deliberately NOT: "XY centre within 0.05 m of `trunk_base`" would fail on correct data, because the
    anchor is the SOURCE prototype's bbox XY centre (the impostor's axis) and the reduction then shifts the
    reduced crown's own centre off it by `placed_xy_offset_m`, 0.10-2.83 m over the 127 (median 0.28).

38. **6c item 2 - the far-tree lighting hand-off: 36 jobs, `vertex_ao.npz` + `instance_irradiance.json` at
    schema /2** (2026-09-17; `export/trees_far_set.py`, `export/bake_lm.py` kind `proto`,
    `export/trees_far_compose.py`, `export/trees_far_ratio_check.py`). All 36 through
    `bake_queue.sh --gate3`, **764 s of Blender wall** on the first pass (16 AO jobs 44 s, 16 E_bake jobs
    158 s, 4 x ~32-placement irradiance jobs 562 s). Two re-runs followed, both on the same scripts:
    the four `tfirr_*` jobs against the export's published anchor (item 37) and then, when the export
    published `topology_rev: 2` (the two floating crowns fixed by protecting the trunk base from the branch
    decimate, and `CARD_SELECT` changed from `block` to `stride`), the 16 AO jobs on the rev-2 meshes -
    **44 s**. The table below is rev 2, and `vertex_ao.npz` carries `topology_rev: 2` as an npz key (plus a
    `trees_far/vertex_ao.json` sidecar), which is what lets `export/trees_far.py` refuse to paint a rev-1
    array onto a rev-2 mesh. Rev 2's stride selection spreads the surviving cards, so AO rose from a
    rev-1 mean of 0.193-0.502 to **0.240-0.505** and the fully-occluded fraction fell from 4.2-34.0 % to
    **1.9-19.8 %**. `instance_irradiance.json` records that E_placement was baked on the rev-1 vertex
    counts (`e_placement_topology.matches_current_rev: false`): it is one RGB per PLACEMENT joined by world
    translation, the anchor and the 127 transforms are identical across revisions, and only the crown's own
    card selection moved - far less than the 27x spread the site itself shows.
    * **Vertex AO is normalised, not assumed.** Each AO job hides every light, swaps in a uniform white
      world of radiance 1 and bakes the prototype ALONE (all 16 sit at the world origin in
      `trees_far_lod2.blend`), plus a 2 m calibration plane 1 km away with nothing above it. That plane
      reads **1.0000 in all 16 jobs**, which is what makes the raw DIFFUSE value the AO factor. Every
      array is asserted in [0, 1] and against the export's LOD2 vertex count. The statistics are over the
      FACED vertices: 11 of the 16 meshes carry loose vertices (willow_s11 316 at rev 1), a vertex no
      polygon references is never written by the bake, and counting its 0 as occlusion dragged min / mean /
      p05 / zeros_pct down (review r2 finding 5). The npz still ships at full length - a loose vertex is in
      no face, so nothing shades it.
    * **E_bake is measured on the body that produced the atlas** (review r1 finding 5): the `_LOD1`
      prototype object in `gate3_imp.blend`, isolated with the lawn exactly as `imp_<proto>` isolated it,
      at the same rig, 128 spp. Both sides of the ratio use `mean_nonzero` over the cov mask (finding 4)
      and both ship `cov`. Determinism checked: `tfeb_ENV_tree_broadleaf_s53_LOD1` baked with an override
      scope of 1 object and again with all 16 gives the **identical** [3.04233, 2.24703, 5.57665].

    | prototype | LOD2 faced verts | AO min / mean / max | AO zeros % | E_bake R, G, B | E_bake cov |
    |---|---|---|---|---|---|
    | `broadleaf_s19` | 13595 | 0.000 / 0.288 / 0.961 | 15.7 | 2.693, 2.018, 5.162 | 0.948 |
    | `broadleaf_s53` | 13740 | 0.000 / 0.294 / 0.953 | 15.8 | 3.042, 2.247, 5.577 | 0.943 |
    | `cypress_column_s2` | 13006 | 0.000 / 0.266 / 0.961 | 18.6 | 1.906, 1.425, 4.332 | 0.889 |
    | `cypress_column_s31` | 12812 | 0.000 / 0.240 / 0.961 | 19.8 | 1.715, 1.277, 3.788 | 0.818 |
    | `cypress_s17` | 14040 | 0.000 / 0.343 / 1.000 | 7.1 | 2.786, 2.117, 6.047 | 0.978 |
    | `cypress_s3` | 13883 | 0.000 / 0.338 / 0.977 | 8.9 | 2.716, 2.052, 5.669 | 0.977 |
    | `cypress_s41` | 13798 | 0.000 / 0.317 / 0.961 | 8.5 | 2.419, 1.831, 5.073 | 0.972 |
    | `eucalyptus_s23` | 12621 | 0.000 / 0.438 / 1.000 | 6.9 | 3.501, 2.675, 7.639 | 0.979 |
    | `eucalyptus_s5` | 12280 | 0.000 / 0.452 / 1.000 | 7.0 | 3.394, 2.587, 7.414 | 0.965 |
    | `eucalyptus_s61` | 12389 | 0.000 / 0.434 / 1.000 | 6.7 | 3.459, 2.615, 7.078 | 0.973 |
    | `pine_s29` | 13678 | 0.000 / 0.441 / 0.977 | 4.5 | 3.898, 2.958, 8.909 | 0.992 |
    | `pine_s7` | 13769 | 0.000 / 0.423 / 0.984 | 5.3 | 3.963, 2.955, 8.053 | 0.992 |
    | `redwood_s13` | 14265 | 0.000 / 0.404 / 0.984 | 6.9 | 3.437, 2.534, 7.228 | 0.996 |
    | `redwood_s43` | 14239 | 0.000 / 0.404 / 0.961 | 7.3 | 3.217, 2.383, 7.159 | 0.996 |
    | `willow_s11` | 8529 | 0.000 / 0.502 / 1.000 | 1.9 | 3.169, 2.435, 6.455 | 0.992 |
    | `willow_s37` | 8033 | 0.000 / 0.505 / 1.000 | 2.0 | 3.129, 2.395, 6.446 | 0.992 |

    * **E_placement, 127 placements, 0 dark.** `trees_far_irr.blend` = `gate3_bake.blend` with the 127 LOD2
      placements linked in and the 127 `source_tree` objects and 127 `ENV_treeboard_*` billboards hidden -
      the scene as it ships once the far trees are meshes. Per-channel **0.130-4.920 R, 0.158-3.701 G,
      0.196-9.064 B**, luminance **0.156-4.262** (mean 2.273), cov mean **0.871**, **0** placements with a zero
      channel (the shrub file had 7). The join is unambiguous: the closest two placements of the same mesh
      are **6.11 m** apart against a 0.02 m tolerance, and no same-mesh pair sits within 2x it.
    * **The ratio was validated on one placement before the other 15 E_bake jobs were queued** (review r1
      finding 6, the lead's gate), and it is judged DISPLAY-referred through `lut_agx_high_contrast_65.cube`
      at -2.8331399 EV, because the reference is a display PNG whose `b_over_g_linear` is only an
      inverse-sRGB of it. Test: `TREEFAR_000`, `ENV_tree_broadleaf_s53_LOD1`, 40.19 m on the axis of
      station 2, frame col 1 row 7. E_bake **[3.042, 2.247, 5.577]**, E_placement **[3.189, 2.235, 0.978]**
      -> ratio **[1.048, 0.995, 0.175]**: the placement receives the same warm light and **5.7x less blue**,
      which is the diagnosis' prediction measured. The crown goes display sRGB8 **[21.5, 33.6, 42.6] ->
      [23.7, 29.7, 1.2]**, **hue 205.5 -> 72.6 deg against the reference's 52.2** - 86.7 % of the hue gap
      closed, no overshoot - at 0.92x the luminance. **PASS**, so all 16 were queued.
    * **The one caveat, reported rather than smoothed over:** on B/G alone the full ratio overshoots
      (display 1.267 -> 0.041 against 0.648). B/G is the fragile metric here - after modulation the display
      BLUE is 1.2/255, so it is a ratio of a near-black channel - and hue, which uses all three, says the
      full ratio is right. The structural reason an overshoot is possible at all: E_placement is the mean
      over the WHOLE crown volume while the atlas frame shows only the sky-facing outer shell, which keeps
      more sky than the volume mean; and the reference's own `foliage_p80` crop biases the target blue-up
      (carry 9). If the lead wants the B/G matched instead of the hue, `ratio ** k` with **k = 0.4386**
      lands display B/G exactly on 0.648 (hue 105.4, worse). Numbers in `trees_far/ratio_check.json`.

39. **Round-2 review, carried open items (bake).** `docs/reviews/phase6c_bake_r2_review.md` 7, 9 and 10; 8 is
    fixed (`trees_far_compose.py` now asserts `not missing_eb`, so a half-finished queue cannot ship a
    schema /2 file with an incomplete `prototypes` block). (7) `trees_far_ratio_check.py:47-48` hard-codes
    the LUT shaper constants (`-2.8331399`, `-12.47393`, `16.5`, `0.18`) instead of parsing the `.cube`
    header or importing `gate0_common`; they match today, so the display path really is the delivery LUT,
    but a re-bake at another exposure would mis-judge silently. (9) Two prototypes' LOD2 meshes float:
    `topology.json` `bbox_min.z` is **3.6541** (cypress_column_s2) and **4.3547** (redwood_s13) where the
    other 14 are ~0, so those crowns sit 2.4-2.8 m x s above `trunk_base` in the glb and in
    `trees_far_irr.blend`. That is the export's reduction, not the bake's, and the bake's new bbox assert
    measures against `topology.json`'s own `bbox_min.z`, so it is consistent with whatever the export
    ships - for the export engineer. (10) The `tfeb_ENV_tree_broadleaf_s53_LOD1` determinism check
    (override scope of 1 object vs all 16, identical `mean=3.4148 cov=0.943`) survives only in
    `renders/logs/6c_bake_run1.log:291` and `6c_bake_run2.log:96`, because run 2 overwrote the record;
    superseded records should be kept beside the new one.

40. **Round-2b review, carried open items (bake).** `docs/reviews/phase6c_bake_r2b_review.md` 5, 7 and 8;
    1-4 and carry 6 are fixed (the hand-off file's `placement_transform` and `ratio.strength_decision` now
    describe the rule that is used and quote `ratio_check.json`'s own anchor-corrected figures instead of
    the pre-fix ones; item 37's last sentence states the assert that exists; and when
    `e_placement_topology.matches_current_rev` is false, `trees_far_compose.py` ASSERTS that
    `trees_far_set.json`'s recorded anchors equal `topology.json`'s current ones - 0.0 m today - instead of
    arguing it in prose). (5) The pidless `gpu_lock.sh claim` is crash-safe only on the clock: with no pid
    to disprove it, a crashed agent holds the published GPU signal for the whole `secs` and `guard` refuses
    other owners until it expires. **Prefer `gpu_lock.sh run <secs> -- <cmd>` (or pass `PFA_LOCK_PID`),
    which records a real pid and releases from a trap; a bare `claim` must pass an honest SHORT `secs`,
    never the 1800 s default for a long hold.** (7) `trees_far_ratio_check.py:138` computes the hue verdict
    as `h_moved >= 0.5 * h_gap and h_after >= h_target`, which assumes the crown starts BLUER than the
    reference; with a future reference above the crown hue the first term is trivially true and the
    direction is unchecked - compare on `abs()` with an explicit direction. (8) r2 carries 7 and 10 are
    still open: the LUT shaper constants in `trees_far_ratio_check.py:49-50` are a hard-coded copy of
    `gate0_common.SHAPER_*` rather than parsed from the `.cube` header, and `status.json` keeps only the
    newest record per job id, so the first-pass `tfao` / `tfirr` timings survive only in the committed
    `renders/logs/6c_bake_run3.log` and `6c_bake_run4.log`.


## Phase 6c (foliage pass, branch `phase6-export`, 2026-09-17)

34. **Item A - `env_trees.glb`: every far tree gets a real mesh.** `export/trees_far.py` builds one LOD2 mesh
    per impostor prototype from its `_LOD1` and instances it at the 127 `tree_far` placements;
    `export/gltf_pack.sh --trees` packs it. **The shipped `_LOD2` objects are not used and the reason is
    measured, not assumed**: all 16 exist and every one is a branch skeleton of 1 188-3 812 triangles with
    **six** leaf faces (`topology.json` `lod2_objects_rejected`). The reduction is card-aware - leaf cards
    (components of <= 2 faces) are split from the branches, the branches take their pro-rata share of the
    8 k budget through the gate1_set COLLAPSE path, the cards fill the rest and are then grown
    `min(1.6, 1/sqrt(keep))` about their own centre so a crown that keeps 18-31 % of its cards does not go
    see-through. Result: **7 992-8 243 tris** each, 129 817 unique, 1 030 195
    placed, `env_trees.glb` **2 014 340 B**. The transforms are the impostors' own
    (`s = height_m / height_above_base_m` at `trunk_base`, rotation ignored); worst crown-top
    deviation against the impostor quad **0.76 m** on a 37 m tree.
    *(Round 2 corrections, review items 1-3: the leaf-area figure quoted here was the MODELLED
    `keep_fraction * scale^2`, now replaced by a measured `sum f.calc_area()` ratio - see item 43; the card
    thinning kept contiguous blocks and now strides; and "asserted per row" was a tautology, the real assert
    is on the exported glTF - see item 43.)* Hand-off for the vertex-AO bake:
    `out/gate3/trees_far/{topology.json, trees_far_lod2.blend}` (32 MB, the 16 objects alone in prototype world
    space). `vertex_ao.npz` comes back on the same contract as `vertex_irradiance.npz` and is attached as
    COLOR_0 by re-running the script.
35. **Item E - `env_shrubs.glb`: the shrub/reed LOD1 set, as a SEPARATE glb.** The brief said "into env.glb".
    It is not, and the reason is the pinned bake state: env.glb's contents come from `gate1_set.py`, which
    rebuilds the **UV1 atlases** every Gate 2 PBR bake and every Gate 3 lightmap was baked against (QA-12-1,
    items 14-15, 28), and a re-packed env.glb also invalidates `instance_order.json` and pushes arch/orn/ground
    back through gltfpack. `env_shrubs.glb` (25 meshes, 1 376 placements, 549 748 placed tris against the LOD2
    set's 135 472, **422 520 B**) carries the same transforms and loads lazily. **Three of the 28 are skipped**:
    `EXPM_ENV_src_{maho2,pitto5,reed1}_LOD2` have no `_LOD1` in the source (item 31's three near-duplicates),
    so a "LOD1" copy would be the card env.glb already draws - and, as lone one-placement meshes, gltfpack
    merged two of them into a single node, collapsing two placements into ONE instance row (measured 1 378 rows
    for 1 379 placements). Those three keep their env.glb card at every distance.
36. **Both new glbs take `-vpf`, not the briefed `-vp 16`.** With `-vp 16` gltfpack folds each mesh's
    dequantisation transform into its `EXT_mesh_gpu_instancing` rows: measured on env_trees, the rows came out
    **40-700 m** from their nodes with instance scales of 0.001, and the positional join - the only key that
    survives `-mi` - is then unrecoverable. With `-vpf` (what env.glb and arch.glb already use) the rows match
    the node translations and the join's worst residual is the familiar **5.8 mm**. Both also take `-tr`
    (external textures): the leaf and bark KTX2 are the ones env.glb already carries, and embedding them again
    cost env_trees **24 960 876 B** against 2 014 340 B.
37. **The join for both LODs is one irradiance file.** `export/gate4_instance_order.py` grew a `SETS` table and
    `PFA_ORDER_SET`: the default is unchanged (byte-identical output re-verified, `gate4_order_selftest` 10/10)
    and `PFA_ORDER_SET=shrub_lod1` runs the same positional join against `env_shrubs.glb`, restricted to the
    placements that set carries. `manifest_v4` emits `lightmaps.instance_irradiance.lod1` - the SAME per-
    placement RGB in the LOD1 glb's own row order (+56 kB), so crossing the LOD distance cannot change a
    shrub's lighting. `verify_glb` gained `trees_far`, `shrub_lod1` and `shrub_lod1_order`.
38. **Item D - the foliage cards ship the MATERIAL's albedo, not the raw texture.** `export/read_foliage.py`
    reads the graph (tint, translucent colour, the translucency factor's Map Range, alpha cut, roughness,
    specular, sheen, normal strength) with the structure asserted; `export/foliage_tex.py` composes
    `clip(image_linear * tint)` with an alpha-weighted resample plus the translucency factor map;
    `gltf_pack.sh --foliage` encodes both sizes into `out/gate3/foliage/tex_ktx2`, and they land in the
    manifest as `materials.foliage`. **What it found:** env.glb ships the raw 1 K PNG, so MAT_shrub /
    MAT_shrub_light / MAT_shrub_dry are three identical mid-green cards at hue 95.4 / value 0.344 where the
    materials are 95.0/0.464, 94.2/0.516 and **36.1/0.600** (straw), and MAT_reeds is 0.491 against 0.651. So
    the albedo is not "45 deg too warm" - it is the untinted texture, ~1.9x too dark on the shrubs. The warmth
    QA measured at cam02 is in the shading, and the missing term is the **Translucent branch**: colour
    `albedo * (0.85, 1.15, 0.60)`-style green-biased multipliers at
    `maprange(trn, 0.05, 0.85, 0.35, 1.55) * translucency`, which is what makes a backlit leaf green in Cycles
    and is now shipped as a per-material factor map for item C.
39. **There is no 2 K foliage source.** Every map under `assets/textures/foliage/` is **1024x1024**
    (`scripts/mat_leaf_textures.py` generates them at 1 K), so the briefed 2048 set is an upsample: 4x the
    texture memory for no new detail, its only real gain a smoother alpha edge at 3 m. Both are built and both
    are in the manifest - **13.0 MB of KTX2 at 1 K, 46.0 MB at 2 K** - with the 1 K named as the default. A
    genuine 2 K would mean re-running the generator, which changes a Phase 5 material source and needs the
    user's approval.

### Round 2 (2026-09-17)

40. **Item 1 - the tinted albedo is what ships, and it was already right; what was missing is the number
    against the render.** `foliage_tex.py` already composed `clip(image_linear * tint)` (item 38), and the
    re-run reproduces the brief's targets exactly: MAT_shrub **95.4/0.344 -> 95.0/0.464**, MAT_shrub_light
    **95.4/0.344 -> 94.2/0.516**, MAT_shrub_dry **95.4/0.344 -> 36.1/0.600** (the straw one), MAT_reeds
    **68.7/0.491 -> 69.3/0.651**; `clipped_texel_fraction` 0.0000 on all eight, so no tint (MAT_shrub_dry's
    6.3x red included) blows a texel. **No Cycles bake was needed**: every term is a graph constant read by
    `read_foliage.py`, so this ran on the CPU in numpy, no Blender and no GPU.
41. **The cam02 hue gap is NOT the leaf albedo, measured.** `scripts/qa_r13_probe.py`'s own box
    (station 2, `60 520 700 980`) on `renders/previews/qa/round13_02_lagoon_ne_threequarter_cycles.png`
    reproduces QA's **102.4 deg** exactly (crop mean `[100.9 108.4 97.7]`, sat 0.098 - that mean is mostly
    sky-lit background). Restricted to the green-dominant pixels, which is what a leaf actually is, the
    reference reads **90.5 deg, sat 0.526**. The four tree materials in that box carry an *identity* tint
    (broadleaf 93.1, cypress 92.5, eucalyptus 80.6; only pine is tinted, 100.8 -> 102.7), i.e. their shipped
    albedo is already within 0-10 deg of the reference's leaf hue. So the viewer's 57.7 deg cannot be fixed by
    the albedo on the near trees - it is the shading, and the term the glb never carried is the Translucent
    branch (item 38). What the tint *does* fix is the shrub/reed **value** (1.35-1.5x too dark) and
    MAT_shrub_dry's hue, which was the wrong plant entirely (95.4 green where the material is 36.1 straw).
42. **Item 2 - the 2 K set is gone** (lead decision 2). `PX_SET = (1024,)`; `foliage_tex.py` now deletes any
    PNG in `tex/` it did not write this run (`stale_removed` in the report), `gltf_pack.sh --foliage` already
    `rm -rf`s its KTX2 directory, and the manifest's `sizes`, `per_size_bytes` and every `albedo` /
    `translucency_map` / `normal` key follow `fo["sizes"]`, so they carry one size with no code change.
    **22 KTX2, 13 001 325 B (13.0 MB), was 44 files / 59.0 MB.** `sync_main.sh` deliberately has no
    `--delete`, so MAIN's 22 dropped `*_2048.ktx2` were removed by hand after the sync (44 -> 22 files,
    57 708 -> 12 744 KiB).

43. **Round-2 review fixes (docs/reviews/phase6c_export_r1_review.md).** The three that change what item 34
    reports:
    * **The placement asserts were tautologies.** `trees_far` asserted `no.location` against the `trunk_base`
      it had been assigned three lines earlier; `shrub_lod1` asserted an object's translation against the
      source translation it had just been decomposed from. Neither could fail. Both now read the WRITTEN
      glTF back and assert every node translation against `to_gltf(loc) = (x, z, -y)` (and, in `trees_far`,
      every node scale against `height_m / height_above_base_m`), which crosses the exporter's Z-up -> Y-up
      swap and float32 round trip and is the same key the per-placement irradiance join uses after gltfpack
      drops the node names. `PLACE_TOL_M = 0.001`; measured on the shipped glTFs, worst residual
      **0.029 mm** over the 127 tree rows and **0.050 mm** over the 1 376 shrub rows.
    * **`shrub_lod1`'s `centre_delta_m` is not a tolerance.** The review asked for `d < PLACE_TOL_M`, but
      `d` is the LOD1 instance's translation against the Gate 1 asset's `location_blender`, which
      `gate1_set.py` records as the **LOD2 object's bounding-box centre**. LOD1 and LOD2 are different
      meshes, so `d` is **0.2171-1.9503 m** (p50 0.80) across all 1 376 placements and a 0.01 m assert would
      fail every row. It stays a reported number; `placement_check.centre_delta_note` says why.
    * **Leaf area is measured, not modelled.** `leaf_area_kept` was `keep_fraction * scale^2`, which assumes
      every card has the mean area and that the grow is exact. It is now
      `sum f.calc_area()` over the kept cards after the grow / over all cards before the thin, with
      `leaf_area_m2_before/after` per prototype and the old estimate retained as `leaf_area_kept_modelled`.
    * **The card thinning strides.** `(i % 1000) >= keep_pct` keeps the first `keep_pct` of every run of
      1 000 components, and `components()` returns broadly spatial order, so whole branches went bald at the
      18-31 % keep the big crowns land on. `(i * 997) % 1000` is a bijection mod 1000: the same number of
      cards survive, scattered through the crown.
    The other four: `foliage_tex.py` asserts the colour space `read_foliage.image_info` recorded (sRGB
    albedo, Non-Color factor and normal) instead of assuming it; `sync_main.sh` tests
    `PFA_SYNC_STATUS = 1` rather than `-n`; `gltf_pack.sh --trees/--shrubs` **exits 1** when gltfpack refuses
    the KTX2 glTF instead of silently shipping the PNG glTF under a manifest that advertises `ktx2_dir`; and
    `verify_glb.py` **fails** when a side glb or its report is missing instead of returning `None` and
    letting the run print PASS. `manifest_v4` accepts instance-irradiance schema `/1` or `/2` (`IRR_SCHEMAS`)
    - `/2` adds the bake's per-prototype `E_bake` block and changes no field this writer reads.
44. **`verify_glb` reads COLOR_0 out of the GLB.** `extra_glb_check` used to report `color0` by echoing the
    builder's report, which is written by the Blender run BEFORE gltfpack - and gltfpack drops vertex colours
    without `-kv`. It is now counted per PRIMITIVE in the glb (bark and leaf are separate meshes) and fails
    three ways: declared but absent, partial, or present but undeclared. `color0_primitives` and
    `color0_range` are in the report line.

45. **Finding 9 (two LOD2 prototypes float): the DIAGNOSIS. SUPERSEDED BY ITEM 46, which fixes it in
    this same round** - read 46 for what ships. Kept because the measurements below are what identified
    the cause and ruled out the card thinning.
    Cause proven by measurement, not inferred (`/tmp/diag9.py` pattern, three prototypes through
    `split_cards` -> `collapse` -> `thin_and_grow` with the z extent printed at every stage):
    it is the **branch COLLAPSE decimate**, not the card thinning.
    | prototype | branch z before collapse | after | cards z |
    |---|---|---|---|
    | `cypress_column_s2` | 0.000 | **3.654** | 3.936 (foliage genuinely starts there) |
    | `redwood_s13` | 0.000 | **4.476** | 4.400 |
    | `cypress_column_s31` (control) | 0.000 | -0.005 | 2.980 |
    The decimate ratios are effectively identical (0.209 / 0.207 / 0.201), so it is the trunk's own
    topology: Decimate COLLAPSE run over the whole branch mesh finds the trunk-base rings the cheapest
    edges to remove. Per-material z confirms the cards are innocent - `MAT_leaf_*` on those two starts at
    3.936 / 4.400 m in the SOURCE.
    `bbox_min.z - base_z_m` over all 16: broadleaf_s19 +0.000, broadleaf_s53 +0.000, **cypress_column_s2
    +3.654**, cypress_column_s31 -0.005, cypress_s17 -0.004, cypress_s3 -0.004, cypress_s41 -0.003,
    eucalyptus_s23 -0.010, eucalyptus_s5 -0.007, eucalyptus_s61 -0.006, pine_s29 -0.502, pine_s7 -0.008,
    **redwood_s13 +4.355**, redwood_s43 -0.005, willow_s11 +0.411, willow_s37 +1.526. (The willows are the
    hanging fronds the thinning drops, below the trunk base and buried in the Phase 5 scene; pine_s29 hangs
    *below* base_z, which is not the defect.)
    **A band split is the wrong fix, measured:** protecting the faces wholly below `base_z + 5 m` and
    decimating base and rest separately fixes `redwood_s13` (0.000) but only improves `cypress_column_s2`
    to +1.061 and *regresses* the control `cypress_column_s31` from -0.005 to +1.372 - the trunk is built
    from long vertical quads, so at a 2 m band there are no faces wholly inside it at all. The fix should
    be Decimate's own `vertex_group` / `vertex_group_factor` protection of the trunk-base band, which
    preserves those vertices without re-partitioning the mesh.
    **Why it is not in this round:** the fix changes mesh TOPOLOGY, and `out/gate3/trees_far/vertex_ao.npz`
    is addressed by vertex index. It therefore has to land in the same topology revision as the card-thinning
    stride (item 43) and share one re-bake of the 16 AO jobs. `CARD_SELECT` already refuses to attach across
    such a change; the trunk fix must join that contract before it ships.

46. **Topology rev 2: finding 9 fixed, the stride on, one revision, one re-bake.** `TOPOLOGY_REV = 2`
    (rev 1 = `CARD_SELECT` "block" with no trunk protection, which the first `vertex_ao.npz` was baked
    against). Three changes, all of which move vertices:
    * **Decimate's vertex group, with the semantics measured rather than assumed.** The group marks what
      GETS decimated (weight 1 = full ratio, weight 0 = left alone), *not* what is protected: putting the
      base band in the group left the whole upper trunk untouched at **10 727 tris against a 2 631 target**.
      So the group holds everything ABOVE `base_z + BASE_BAND_M`, by membership rather than
      `invert_vertex_group`, so it does not depend on a flag's meaning. Band and factor chosen by sweeping
      (0.5/1/2/3/5 m x 1.0/0.3/0.2) over both failures, a control and a willow: **1 m at factor 1.0** puts
      all four at 0.000 for **11-21 extra branch triangles**; 5 m cost +1 304 on the control for no gain.
    * **The lowest leaf cards are force-kept** whatever the stride says (`cards_forced_low`). On the willows
      the lowest geometry is fronds hanging BELOW the trunk base, and subsampling at 9-12 % always took
      them: 43 cards on `willow_s11`, 7 on `willow_s37`.
    * **`CARD_SELECT = "stride"`** (item 43).
    **`bbox_min.z - base_z`, rev 1 -> rev 2, all 16:** broadleaf_s19 +0.000 -> +0.000, broadleaf_s53 +0.000
    -> +0.000, **cypress_column_s2 +3.654 -> +0.000**, cypress_column_s31 (control) -0.005 -> +0.000,
    cypress_s17 -0.004 -> +0.000, cypress_s3 -0.004 -> +0.000, cypress_s41 -0.003 -> +0.000, eucalyptus_s23
    -0.010 -> +0.000, eucalyptus_s5 -0.007 -> +0.000, eucalyptus_s61 -0.006 -> +0.000, pine_s29 -0.502 ->
    +0.000, pine_s7 -0.008 -> +0.000, **redwood_s13 +4.355 -> +0.000**, redwood_s43 -0.005 -> +0.000,
    willow_s11 +0.411 -> -0.000, willow_s37 +1.526 -> +0.000. **All 16 within 0.05 m, nothing regressed.**
    Triangles 7 856-8 020 (was 7 992-8 243), measured leaf area kept **0.234-0.782**.
    **The revision gate.** `topology.json` carries `topology_rev`, `card_select`, `vertex_counts` and
    `topology_rev_note`. The COLOR_0 attach reads `topology_rev` from the npz (an npz key, or a sibling
    `vertex_ao.json`) and **refuses any other value**, printing what to re-bake, rather than aborting - the
    export must still be able to publish a new revision for the bake to work from. Verified live: the rev-1
    npz was refused ("declares topology_rev None ... this export builds rev 2") and the run still published
    rev 2. A count check could not have caught this: the stride keeps the same card COUNT as rev 1.

47. **Round-2 review fixes (`docs/reviews/phase6c_export_r2_review.md`, MERGE WITH FIXES).**
    * **Fix 1 - `trees.far_mesh.lighting.impostor` is now implementable from the manifest alone.** Its `how`
      is the formula `atlas_frame * clamp((E_placement / E_bake) ** strength, 0, clamp)`, and `strength`,
      `clamp`, `zero_channel_fallback`, `fallback` and `e_bake_body` are copied verbatim from the bake JSON's
      `ratio` beside it. Copied, never defaulted: a missing key means the bake changed its contract and
      should fail loudly rather than be papered over.
    * **Fix 2 - `foliage_tex.py` merges into `foliage_tex.json` instead of clobbering it.**
      `gltf_pack.sh --foliage` writes `ktx2_dir`/`ktx2_bytes`/`ktx2_files` back into that same file and
      `manifest_v4`'s `materials.foliage` reads them, so a plain overwrite dropped the entire KTX2 side of
      the block - which is exactly what had happened. Keys this run owns win, keys only the packer writes
      are carried (listed in `carried_from_previous`). Re-packed: **22 KTX2, 13 001 325 B, and all 22
      sha256 are byte-identical to before the re-pack**; a bare `foliage_tex.py` re-run now leaves them in
      place (verified).
    * **Fix 3 - `shrub_lod1.json` carries `placement_check` again.** One CPU re-run plus
      `gltf_pack.sh --shrubs`: 1 376 rows, **worst node-translation residual 0.0 mm** (the 0.050 mm quoted
      earlier was an artefact of comparing against the report's 4-dp-rounded `loc`; the live check uses the
      full-precision translation, and the exporter writes the same float32 back). **`env_shrubs.glb` is
      byte-identical - 422 520 B, sha256 32987a9b... - so `instance_order_shrub_lod1.json` stays valid and
      the viewer's round-16b capture is unaffected.**
    * **Carry 6 - `me.validate()` after `join()`, and what it actually means here.** The exporter logs
      "Mesh ... is not valid" for all 16 far trees. `validate()` now runs after the join and its result is
      recorded per prototype as `mesh_validate`. **It returns True on all 16 while the vertex and face
      counts are unchanged on all 16 (`geometry_changed: false`) and the packed `env_trees.glb` is
      byte-identical (sha256 `7e17167d...`)** - so on these meshes it normalises something that is not
      geometry, and a bare True is not an alarm. The counts are what matter, because a real repair would
      move every vertex index and silently invalidate the index-addressed vertex AO; they are recorded
      before and after so that shows up as a number, not a flag. The rev-2 AO is therefore still valid.
48. **Open items carried out of the round-2 review** (recorded here on the lead's instruction, not fixed):
    * **Review carry 4 - the KTX2-refusal `exit 1` is only in `--trees`/`--shrubs`.** `gltf_pack.sh`'s
      `--gate1` and `--gate0` branches still log to stderr and pack the PNG glTF at exit 0, under the same
      manifest that advertises `ktx2_dir` - and that is the whole arch/orn/env/ground payload, not a 3.7 MB
      side file. Fix is the same `exit 1` in both branches; untouched here only because those branches
      produce the outputs every pinned bake and `instance_order.json` depend on.
    * **Review carry 5 - `shrub_lod1_order_check` still returns `None`** when
      `instance_order_shrub_lod1.json` or `env_shrubs.glb` is missing, so a run without the order file
      prints PASS with the LOD1 row order unchecked. `extra_glb_check` was fixed; this one needs the same
      `bad.append`.
    * **Review carry 7 (second half) / round-1 finding 5 - `read_foliage.chain_to_image` walks unknown
      `bl_idname`s silently** and pins `ShaderNodeHueSaturation` without checking its sockets. It should
      raise on an unknown node, now that the tint it produces is what ships.

### Round 3 (2026-09-17) — the last 6c export round

47. **Item 1 — the shrub/reed level gap is LIGHTING, and the number is the Cycles Diffuse Colour pass.**
    QA 16 "Open 1" measures the viewer's shrub boxes at 1.34-1.70x the Cycles level and assigns EXPORT on the
    grounds that the round-2 tinted albedo pushed four of five boxes further out. A rendered level is
    albedo x irradiance, so it cannot separate the two; `export/foliage_albedo_render.py` renders the albedo
    alone (DiffCol + IndexMA + IndexOB, 16 spp, 1920x1080, cam02 and cam05, 32 s, master_delivery never
    saved) and `export/foliage_albedo_check.py` divides it into the shipped tinted albedo.
    **Every shrub box's shipped albedo is DARKER than the albedo Cycles uses on the same cards:**

    | shrub box | 02 shore | 02 reed clump SE | 05 shore | 05 W |
    |---|---|---|---|---|
    | shipped albedo / pass albedo | **0.98** | **0.87** | **0.98** | **0.89** |

    Per material, pixel-weighted over those boxes: MAT_shrub_light **0.98** (94 % of cam02's shore box),
    MAT_shrub **0.92**, MAT_shrub_dry **0.90**, MAT_reeds **1.49** on **0.6 %** of the boxes' card pixels.
    So the albedo cannot be the 1.34-1.70x; if anything it *understates* the viewer's irradiance excess.
    **Owner: VIEWER** (the irradiance reducer, the translucency term, the missing self-shadow).
    Three ways the comparison could have lied, each measured and ruled out rather than argued:
    * **Two different texel populations.** `leaf_material` RAMPS the alpha (`maprange(a, cut-0.15, cut+0.15,
      0, 1)`), so the texels Cycles draws opaque are `a > cut+0.15` while the viewer's glTF `MASK` draws
      `a > cut`. The ratio is taken over the ramp population; `as_drawn_over_ramp` is 0.991-1.001 on all
      eight, so the choice is worth 1 %.
    * **Density selection.** A pixel only clears `alpha > 0.98` where the sheet is locally dense, which on a
      32 %-opaque sheet is a colour-correlated subset. Reproduced on the texture at 3x3, 5x5 and 9x9
      footprints: the mean moves by **under 1 %** on every material, including MAT_reeds.
    * **The source.** Every foliage image in master_delivery is a PACKED `...png.001` duplicate and
      `foliage_tex.py` tints the FILE. `export/foliage_uv_probe.py` decodes both through the same loader:
      **max RGB delta 0.000000 and max alpha delta 0.000000 on all eight**. The two halves of the pipeline
      read the same image.
    The **translucent branch** is applied before the ratio is taken (Cycles' DiffCol sums the diffuse
    closures and `leaf_material` mixes a Translucent BSDF at `maprange(trn)*constant`), and the
    `material.pass_index` map is validated by HUE, not trusted: worst |delta hue| **11.7 deg** over every
    material and box, with MAT_shrub_dry reading 36-40 deg where the others read 69-95.
    **MAT_reeds is a measured outlier and is NOT fixed here.** It is +45 % on the whole frame as well as in
    the boxes, on 248 objects with full-sheet UVs, 7 of them large enough to judge in frame, whose per-object
    means scatter by only +-7 % - so it is neither a small-sample artefact of the per-instance terms nor any
    of the three above. Its node chain is structurally identical to the seven materials that agree
    (`VectorMath -> HueSaturation -> VectorMath -> TexImage`), so there is no missing node to add, and
    scaling its albedo by 0.69 would be fitting a number rather than fixing a chain. It covers 0.6 % of the
    shrub boxes' card pixels and moves the worst box level by under 0.3 %. Sheet:
    `renders/web/960/6c_albedo_check.jpg`; numbers: `out/gate3/foliage/albedo_check.json` and `uv_probe.json`.
48. **Item 2 — `env_trees_lod1.glb`, the walk-up set.** `trees_far.py` grew a `SETS` table and
    `PFA_TREES_SET` (the same pattern as `gate4_instance_order.py`), because a second script would be a
    second anchor, a second placement rule and a second way for the two glbs to disagree about where a tree
    stands - the one thing the viewer cannot recover once `gltfpack -mi` has dropped the node names.
    **The default is byte-identical**: `env_trees.glb` re-packs to sha256 `7e17167d...`, the same file as
    before the refactor. `PFA_TREES_SET=walkup` builds the 16 prototypes at **25 604-29 984 tris** (all under
    the 30 k budget; the source `_LOD1` meshes are 25.6 k-45.2 k, so two need no reduction at all),
    **472 626 unique** and **3 771 087 placed** over the same 127 placements. **`env_trees_lod1.glb` =
    7 642 344 B** (32 meshes, 254 rows, external KTX2 through `-tr` exactly as `env_trees.glb`).
    * **No card grow.** The far set scales surviving cards by `1/sqrt(keep)` because it drops 70-80 % of
      them; at 30 k the keep fraction is 0.7-1.0 and a grown leaf is visible at the 3 m this mesh exists for,
      so `card_scale_max = 1.0` makes `min(scale_max, 1/sqrt(keep))` exactly 1.
    * **No COLOR_0** (brief: the viewer's interior term covers it), and **no hand-off blend** - writing one
      would overwrite the far set's `topology.json` and invalidate the vertex AO's revision gate.
    * **Same instance order, asserted twice.** Pre-pack, `instance_order_check` reads both written glTFs and
      compares all 127 mesh nodes name for name and translation for translation (worst delta **0.000 m**).
      Post-pack, `verify_glb.trees_lod1_order_check` compares what gltfpack could still re-segment: meshes
      32/32, instanced nodes 32/32, rows 254/254, and the material on each node. The row TRANSLATIONS
      themselves are meshopt-encoded by `-cc` and only the viewer's loader can decode them
      (`web/tools/instance_rows.mjs`, how Gate 4 recovers env.glb's order).
    * `manifest_v4` writes `trees.walkup_mesh` {glb, bytes, prototypes, placements, join, draw_within_m
      15 m, lighting}. **`placements` is deliberately not a second copy of the 127 rows** - it is
      `{count, same_as: "trees.far_mesh.placements", verified_pre_pack, verified_post_pack}`, because two
      lists that must be identical can only ever disagree. `lighting` says to reuse
      `trees.far_mesh.lighting` verbatim.

## Phase 6b Gate 5 — load tiers, per-tier groups, mobile (branch `phase6b-export`, 2026-09-18)

```sh
# A: per-station, per-asset visibility (CPU, no render; ~310 s at 640x360)
scripts/blender_run.sh 1800 -- --background \
  .claude/worktrees/phase6-export/export/out/gate1/gate1_set.blend \
  --python export/gate5_visibility.py -- --rays 640x360 --out export/out/gate5
python3 export/gate5_tex.py --probe          # the ETC1S / quarter-res-UASTC measurement
python3 export/gate5_tex.py --encode --tier0-div 2
python3 export/tiers.py                      # desktop  -> out/gate5/manifest.json
python3 export/tiers.py --mobile             # mobile   -> out/gate5/manifest_mobile.json
python3 export/verify_glb.py --gate5 export/out/gate5
python3 export/gate5_report.py               # docs/briefs/phase6b_export_report.md
export/sync_main.sh                          # gate5 -> MAIN (no --delete)
```
**Order matters**: the desktop run `rm -rf`s `out/gate5/groups`, so it goes first and `--mobile` second.

27. **The tiers, measured.** Desktop tier 0 **43.3 MB / 228 files**, tier 1 488.3 MB / 286, tier 2
    69.4 MB / 50; total **601.1 MB** against the 671.0 MB the same look cost at Gate 3. Mobile total
    **61.9 MB** (t0 40.7 / t1 11.8 / t2 9.4), ASTC-rule resident estimate **274 MB** against the
    iPhone 16 Pro's 700 MB target. **0 files over Cloudflare Pages' 25 MiB cap** in either variant
    (at Gate 3, `orn.glb` at 154.3 MB and `env.glb` at 38.1 MB were both over it).
28. **`-tr` on every group, and why the first cut was wrong.** The first desktop cut packed the groups
    the way `gltf_pack.sh` packs a class, with the Gate 1 maps embedded: the 16 ENV groups came to
    **180.3 MB against env.glb's 38.1 MB**, because gltfpack embeds a copy of every map into every
    group that reaches it and the bark, leaf and needle sets are shared by most of them. With `-tr`
    a group is geometry alone (`env_g06` 11 100 000 B -> 409 892 B), each map is published once, and a
    map can carry its own tier. The group `.gltf` is written INTO the groups directory because
    gltfpack rewrites a kept URI relative to the OUTPUT file; `tiers.rewrite_glb_image_uris` then
    rewrites the packed glb's JSON chunk so the URIs are relative to the PUBLISHED `out/gate5/groups`,
    not to whichever worktree built them, and `verify_glb --gate5` re-checks the GLB framing byte by
    byte afterwards.
29. **The 86.3 MB of ORN Gate 1 normal maps are not published at all.** Every Gate 2 ORN set declares
    `normal.replaces_gate1: orn_<proto>_normal`, and `web/src/pbr.js` (line ~157, `replaced_glb_normal`)
    overwrites `normalMap` from the Gate 2 set on every ORN material — so at Gate 3 those 33 maps were
    downloaded inside `orn.glb`, decoded, and thrown away. `gate5_split.py --drop-gate1-normals` removes
    `normalTexture` from exactly the materials whose Gate 2 set declares the replacement (27 + 6 across
    the ORN groups, 0 on ENV), so the payload loses 86.3 MB and **the rendered result is unchanged**:
    the map that is dropped is the one the viewer was already replacing. `occlusionTexture` is never
    dropped — pbr.js KEEPS the glb's aoMap (`kept_glb_ao`) and no Gate 2 set replaces it.
30. **The tier-0 encoding, decided by measurement.** The brief offered "ETC1S KTX2 or quarter-res UASTC,
    whichever is smaller at equal or better look". Neither dominated, so two intermediate ETC1S
    resolutions were measured with them (bytes / RMS against the source png, in linear light, the
    decoded image resampled back to the source resolution). **Half-resolution ETC1S is smaller AND
    lower-error than quarter-res UASTC on 5 of 6 sampled maps**, and 8-15x smaller on the two normals
    for +0.0005 RMS. Tier 0 and the entire mobile set use it; the numbers are in
    `out/gate5/lowres.json` and the report.
31. **What tier 0 does NOT carry, and why.** No lightmaps and no detail set (the first frame is allowed
    to be a placeholder — the user's decision, docs/decisions.md 2026-09-18). **The probe moved to
    tier 1**, against the brief's list: the six `.hdr` faces are 6.29 MB, tier 0 had 6.7 MB of headroom,
    and the probe is the water's FALLBACK environment — the hero's water is the planar reflector. The
    lead can move it back by one line in `tiers.assign_and_write` if the first frame's water looks wrong.
    The `ENV_treeboard_*` stand-ins are in tier 1, not tier 0: the viewer hides them by default
    (`?treeboards=0` since 6a) and draws those trees from the impostor atlases, which ARE in tier 0 at
    half resolution — 0 hero-visible assets are missing from tier 0 once the boards are accounted for.
32. **Mobile geometry.** ARCH and ORN have no LOD1 in the export set (Gate 1 is LOD0, and
    `orn_lo_from_lod1` covers only the three attic panels), so the brief's fallback applies:
    `gltfpack -si 0.5`, which is CPU and needs no Blender. Measured drawn triangles: arch **0.4723x**,
    orn **0.6204x** of Gate 3. ENV is already `_LOD1`/`_LOD2` and ground is the terrain and lagoon bed,
    where a simplifier would move the shoreline, so neither is simplified (1.0000x). The three lazy
    foliage glbs (`env_trees`, `env_trees_lod1`, `env_shrubs`) are not published on mobile at all.
    **Known compromise, for the QA round:** `-si` keeps UV2 interpolated but does not respect the
    lightmap island borders, so a mobile ARCH/ORN lightmap may bleed at an island edge.
33. **Paths.** Every path in v5 is relative to **MAIN's `out/gate5`**, not to the worktree that built it
    (`gate5_common.pub_rel`). `tiers.rebase_gate3_paths` rewrites the four v4 entries that were relative
    to `out/gate3` (`textures.gate3.ktx2_dir`, `probe.dir`, `sky.diffuse.hdr`, `materials.foliage.dir`)
    and spells out the three lazy glbs; what it moved is recorded in `tiers.path_rebase`, never silently.
34. **What the viewer has to do with this** (viewer brief, not done here): read `tiers.bytes` for the
    loading-screen denominator; load `files` in array order, which is already (tier, hero coverage,
    path); for a tier-0 texture key use `tiers.lowres.files[key].path` instead of the manifest's own
    path and re-load the full file when tier 1 arrives; treat a tier-0 `glb.groups[*]` with
    `placeholder: true` as replaceable by the tier-1 group of the same class; `?tier=mobile` selects
    `manifest_mobile.json`.

### Gate 5 review pass (2026-09-18, `docs/reviews/phase6b_export_r1_review.md` + two viewer measurements)

```sh
python3 export/tiers.py                    # desktop  (packs groups)
python3 export/tiers.py --mobile           # mobile   (packs m_* groups; the two no longer clobber)
python3 export/gate5_instance_rows.py      # per-group shrub/reed irradiance node maps
python3 export/tiers.py --no-pack ; python3 export/tiers.py --mobile --no-pack   # fold them in
python3 export/verify_glb.py --gate5 export/out/gate5 ; python3 export/gate5_report.py
export/sync_main.sh
```

35. **The budget is TRANSFER bytes, and it now includes the boot overhead.** `files[*].transfer` is
    `gzip -9` for the types Cloudflare Pages compresses and the size on disk for KTX2 / glb / wasm /
    `.hdr` / `.cube`. `tiers.boot_overhead_bytes` measures what the browser fetches before frame 1 that
    is NOT in `files` - `web/dist/index.html`, the Vite bundle, `/basis/` (the path main.js gives
    KTX2Loader) and the manifest itself, which is iterated to a fixed point because it is part of the
    payload it reports. `tiers.first_frame_transfer_bytes` = tier 0 + that, and THAT is what is tested
    against 50 000 000. Desktop **49 488 169 B**, mobile **47 515 …** - both within.
36. **The probe is in tier 0** (lead's decision). Tier 0 ships no lightmap, so without it the first
    frame is sky-diffuse-lit only. The 6.29 MB was found in two places: the 46 tier-0 normal maps at
    ETC1S **qlevel 32** instead of 128 (-20.8 % of their bytes, RMS against the source unchanged to
    five decimals - measured on five of them) and, after that, **28 Gate 2 placeholder maps moved to
    tier 1**, least hero-visible first: the largest of them covers **0.0022 %** of the hero frame.
    `tiers.tier0_trim` lists every one with its hero fraction. Restated from `lowres.json` over the
    whole shipped set rather than a hand sample: the 46 normals go **3 057 292 -> 2 520 098 B, -17.6 %**
    (537 194 B); the only error measurement for that change is the five-file probe in `lowres.json`, so
    no error claim is made for all 46. The 28 trimmed maps are **dropped** from tier 0, not moved into
    it, because their full-resolution file is already in tier 1 - their materials carry no map at all
    until then, and they have no `tiers.lowres.files` entry either.
37. **No placeholder groups, and no duplicated geometry.** The first cut shipped a tier-0 subset group
    beside the tier-1 group holding the same prototypes' other instances: the viewer measured **428
    draw calls and 5.83 M drawn triangles at the hero against Gate 3's 329 and 5.24 M**. Every instance
    of a prototype is now in exactly ONE group (`orn_t0`, `orn_t2`, `env_t0`, `env_t2`), whose tier is
    the earliest any instance needs. What tier 1 upgrades is the TEXTURE, never the mesh.
38. **A group embeds nothing and names the FULL-resolution file.** Pointing the URIs at `tex_lo` was
    the first cut and it dead-ends: a texture that arrives inside the glb reaches three.js as a blob
    with no name, so nothing can pair it with its full-resolution twin. Each group's image URIs are
    `../../gate1/tex_ktx2/<name>.ktx2`; `tiers.lowres.files[key]` carries `path` (the half-resolution
    copy) and `full` (that same URI), and the viewer redirects the URI to `path` while the scene is in
    tier 0. `verify_glb --gate5` fails any group image with a `bufferView` or without a `uri`.
39. **`lightmaps.instance_irradiance.groups`** re-keys the 1 379 shrub/reed placements to the per-tier
    ENV groups, which renumber env.glb's node indices. The join is the bake's own key - the instance
    TRANSLATION - decoded with `web/tools/instance_rows.mjs`, brought back to Blender space as
    `(x, -z, y)`, matched to the nearest placement within 0.02 m with the runner-up at least 3x
    further; `segments` is REBUILT from the matched rows. Matching node-to-node against env.glb was
    tried first and fails: the split changes which meshes gltfpack merges into one node, and 4 of the
    25 card nodes came out with a different row count (224 placements lost). **1 376 of 1 379**
    covered; the three `.001` near-duplicate cards the manifest's own `lod1` block already calls
    `not_in_lod1` fall back to the probe, as they do today.
40. **`uv2_relay_status.json` is published beside the v5 manifest** (tier 0) and named at
    `lightmaps.uv2_relay_status.path`: main.js resolves it against the manifest URL, and a 404 there
    silently changes which lightmap variant every own-map asset uses.
41. **`tiers.unpublished` is the completeness guard.** Every file `gate5_common.resolve_files` knows
    about is published, or published as its half-resolution twin, or deliberately dropped by that
    variant; anything else is listed. It is 0 on both variants. The viewer treats a fetch outside
    `files` as an error, so the plan has to be exhaustive - this is what missed the detail set.
42. **The deploy set is four gates, not one.** `files` spans `out/gate0` (LUT, sky), `out/gate1`
    (group textures, the lazy foliage glbs, arch/ground), `out/gate2` (PBR, detail), `out/gate3`
    (lightmaps, impostors, probe, foliage cards) and `out/gate5`. `web/deploy.sh` must build the
    publish directory FROM `files`, not by copying `out/` wholesale - `out/` also holds ~2 GB of bake
    sources, the `rgbm8` lightmap twins and the unpublished `orn.glb` / `env.glb`.

### Gate 5 wire pass (2026-09-18, viewer network log + lead items 1-4)

43. **The budget is now what the network log counts.** `tiers.request_header_allowance` adds one
    response-header block per tier-0 request (+6 boot requests), at **162 B**, MEASURED from the
    viewer's `renders/web/gate5_tier0_net.json`: Chrome's `encodedDataLength` is body + headers, and on
    the 14 tier-0 responses no host compresses (`.hdr`, `.glb`, `.cube`, `.wasm`) the body size on disk
    is exact, so the difference is the header block. `tiers.first_frame_on_wire_bytes` = tier 0
    transfer + boot + headers, tested against `G.TIER0_TARGET` = **49 500 000**. Desktop **49 316 003**,
    mobile **47 556 566**. The rest of the gap to the viewer's 50.4 MB is compression the dev server
    does not do and Pages does (manifest 2 517 666 -> 224 918, bundle 1 177 647 -> 321 602,
    uv2_relay 31 977 -> 3 914).
44. **31 placeholder maps trimmed** (1 735 243 B), least hero-visible first; the largest covers
    **0.019 %** of the hero frame, every one is listed in `tiers.tier0_trim` with its fraction, and
    each is DROPPED rather than moved, because its full-resolution file is already in tier 1.
45. **`files[]` is the whole deploy set.** `web/tools/publish_set.mjs` now finds **0** files by
    reference in the desktop plan (was 108): the v5 manifest no longer NAMES a file it does not publish
    (`textures.gate2.etc1s_dir` and the impostor `*_2k` keys are gone, with a note in their place),
    `tiers.path_rebase` is a LIST - as a dict its keys ended in `_dir` and every walker read them as
    directory declarations - and every half-resolution file only `manifest_mobile.json` needs is named
    at tier 2 as `kind: mobile_lo`. `tiers.deploy_from` says it: **build the publish directory from
    `manifest.json`**, never from `manifest_mobile.json`, which is a LOAD plan whose material sets name
    the full-resolution keys the viewer redirects.
46. **The water has no texture to tier.** The lagoon ripple is procedural - 8 analytic waves in
    `web/src/water.js` under `rippleTiling` - so there is no ripple or normal map in any tier, in
    either variant, at 0 bytes. The tier-0 water differs from the tier-1 water only in what it
    REFLECTS.
47. **ENV instances: 1 523 instanced rows + 6 plain nodes = 1 529 placements, against env.glb's
    1 526 + 5 = 1 531 - and nothing is missing.** All 1 536 source nodes are in the groups and the
    triangles DRAWN are 679 779, exactly Gate 3's. gltfpack merges single-use meshes that share a
    material and merges two more of them in the split than in the whole file, so three cards that used
    to be instanced rows now sit inside a merged plain node. Those three are the `.001` near-duplicates
    in `instance_order_groups.json.unmatched`: a merged plain node has no per-instance row, so their
    irradiance cannot be keyed and they fall back to the probe, as the seven fully enclosed cards
    already do. 1 376 of 1 379 placements keyed.

## Phase 8a — the ENV re-export at the raised budget (2026-09-19, export engineer, branch `phase8-export`)

**`gate1_common.CLASS_BUDGET["ENV"]` is 902 000, not 800 000.** The 8a decision accepted "+~105 k against
the frozen 800 k ENV budget = +13 %, accepted for the hero" for the densified LOD2 shrubs, but nothing
raised the constant, so `tree_allow = CLASS_BUDGET[ENV] - env_so_far - shrub_est - 2*len(tree_rows)` paid
for the shrubs out of the NEAR-TREE allowance instead: `near_exported` 20 → 15, `far_billboards` 127 → 132.
That re-indexes the impostor placements across five species and would force an impostor re-bake. At 902 000
(+102 152, exactly the shrub increase) `tree_far_list` and `tree_near_list` come back byte-identical, ENV
lands at 894 974 placed with 7 026 spare, and the only figure that moves in `tree_rule` is
`near_tris_budget` 399 046 → 398 894. `export/budget_doc.py` now imports the constants from
`gate1_common` instead of keeping a second copy of them, which is why it printed 800 000 and a headroom of
−94 974 against a run that was under budget.

**Two things a class re-pack silently invalidated, both fixed here.**

1. **`glb.per_class` was frozen at Gate 2.** `manifest_v4.py` carried the block out of
   `out/gate2/manifest.json`, so it described the glbs as they were when the Gate 2 chain last ran — and
   `verify_glb.py --gate5` checks the triangles the tier groups draw against its `placed_tris`. Every
   class's `bytes` had been stale since the QA-12-1 re-pack (arch 3 589 032, orn 154 065 360, env
   35 797 240, ground 1 238 288 against 4 613 040 / 154 253 424 / 38 181 724 / 1 959 104 on disk) and
   nothing noticed, because only env's triangle count ever moved. `manifest_v4.py` now refreshes
   `glb.per_class` from the Gate 1 manifest beside the glbs and records what changed in
   `glb.per_class_refreshed_from_gate1`.
2. **Gate 5 reads MAIN, not the worktree.** `gate5_common.GATE1/GATE3` resolve to `PFA_MAIN_ROOT`
   deliberately ("the bake branch's files arrive in MAIN via sync"), so `tiers.py`'s group builder reads
   `MAIN/export/out/gate1/<cls>_ktx2.gltf`. A gate5 run before `sync_main.sh` rebuilds the groups from the
   PREVIOUS class glb and they come out byte-identical — which is exactly what it looks like when nothing
   changed. **Sync gate1 and gate3 to MAIN before running `tiers.py`**, and check the group bytes moved.

**The chain, in the order it has to run** (no GPU, no bakes; the 33 ORN normal/AO maps in `out/gate1/tex`
are unchanged and are copied in rather than re-baked — `orn.bin` and `orn.glb` come back byte-identical):

```sh
scripts/blender_run.sh 2400 -- --background <MAIN>/master_delivery.blend --python export/export_set.py -- --gate1
scripts/blender_run.sh  900 -- --background export/out/gate1/gate1_set.blend --python export/gltf_gate1.py
export/gltf_pack.sh --gate1
scripts/blender_run.sh  900 -- --background <MAIN>/master_delivery.blend --python export/shrub_lod1.py
export/gltf_pack.sh --shrubs
node web/tools/instance_rows.mjs <W>/export/out/gate1/env.glb        <W>/export/out/gate3/instance_rows.json
node web/tools/instance_rows.mjs <W>/export/out/gate1/env_shrubs.glb <W>/export/out/gate3/instance_rows_shrub_lod1.json
python3 export/gate4_instance_order.py && PFA_ORDER_SET=shrub_lod1 python3 export/gate4_instance_order.py
python3 export/verify_glb.py && python3 export/gate4_order_selftest.py
python3 export/manifest_v2.py && python3 export/manifest_v3.py && python3 export/manifest_v4.py \
  && python3 export/budget_doc.py            # v2 -> v3 -> v4: v3 asserts the carry v2 writes
export/sync_main.sh                       # gate1 + gate3 MUST reach MAIN before the next line
python3 export/tiers.py && python3 export/tiers.py --mobile && python3 export/tiers.py --no-pack
python3 export/verify_glb.py --gate5 && (cd <MAIN>/web && node test/tiers_test.mjs)
export/sync_main.sh
```

`manifest_v2.py` is the step that is easy to skip and expensive to skip: without it `glb.per_class` keeps
the previous pack's numbers and Gate 5's triangle check fails against them.

## Phase 8e — the mobile far-tree leaf-card scale (2026-09-19, export engineer, branch `phase8e-export`)

QA 19 finding 4(a): on the mobile close orbit the far crowns' leaves read as "~40 px wide gold/black duotone
blades" at 37 m. Analysis and the numbers: `docs/briefs/phase8e_analysis.md`, probe `export/p8e_leaf_probe.py`
(CPU; no Blender, no Chrome) — it re-derives the orbit camera's px/m from `renders/web/gate7_orbit_cam.json`
(fov 40 deg VERTICAL, canvas 1170x2532, dpr 0.712 → 86.9 px/m at 40 m), reads the card geometry and UV windows
out of `export/out/gate1/env_trees.gltf`, and predicts the blade from the foliage albedo's own mip.

**What the defect is.** One far-tree card is ONE quad carrying a centred vertical strip of the whole 1024 px
cluster texture (u 0.18-0.85 by species, v 0-1; one texture tile = 0.88-1.02 m of prototype world, 0.54-0.85 m
as placed). The painted leaves are 0.05-0.11 m — 4-10 px at 40 m, plausible — but at 20-30 texels per screen
pixel the mip merges them and `alphaMode MASK` re-hardens the mush into blades of 17-22 px (p90) / 22-28 px
(max), against 9-13 px for a believable foliage clump. It is a mip-and-cut defect, not a card-size defect.

**The lever (this change).** `trees_far.py` scales each leaf card's UVs about its own UV centre after
`thin_and_grow` and before `join`, so a card samples the cluster k times over; `SETS['far'].uv_tile` gates it
to the far set (the walk-up set is what DESKTOP draws). No vertex is added, moved or removed, so
`out/gate3/trees_far/vertex_ao.npz` (POINT domain, by index, `topology_rev` 2) and the instance rows are
untouched — `verify_glb` reports the same 254 rows, 127 placements and 1 007 775 drawn triangles.

**Why (ku, kv) = (1.0, 2.5) and not the isotropic 2.0 the analysis recommended.** The analysis assumed the
alpha coverage — the share of the card the cut leaves opaque, i.e. the crown's leaf area — is invariant under
the scale. Measured per species at 40 m, as (coverage vs today) / blade p90 / blade max:

| | coverage | blade p90 | blade max |
|---|---|---|---|
| shipped (k=1) | 1.00x | 17-22 px | 22-28 px |
| isotropic k=2 | **0.62-0.76x** | 10-13 px | 14-17 px |
| ku=1.0, kv=2.5 (shipped here) | **0.96-1.00x** | 11-14 px | 14-20 px |
| ku=1.0, kv=3.0 | 0.97-1.03x | 8-13 px | 11-17 px |

The card's u window is the cluster's DENSE CORE and widening it pulls in the radially faded rim; v is free
because the card's v window is the full texture height, so k periods of it average exactly what one period
averages. The isotropic form would have thinned every far crown by a third — the 6c see-through defect Phase 7
exists to undo — as a silent side effect of a leaf-size fix. kv=3.0 is the next step if QA still reads the
leaves large; a u factor is not. Willow is 1.5 (its cards are 0.14 m wide, 12 px at 40 m: no kv changes its
blade). A deterministic golden-ratio v offset per card keeps neighbouring cards from stacking the same tile
boundary at the same height; the offset is v-only for the same reason (averaged over u offsets the coverage
falls to the full-width mean, 0.35 against 0.56 on the cypress).

**r2 review (`docs/reviews/phase8_export_r2_review.md`, findings 1, 2, 4, 5) — what changed after it.**

* *Finding 1 — the table now comes from committed code.* `p8e_leaf_probe.py` grew an anisotropic mode:
  `card_alpha(tex, u_win, ku, kv, w_px, h_px, v_off)` (the card's own wrapped UV window box-averaged to its
  drawing-buffer samples = the mip the GPU picks), `run_width` beside `thickness`, `solve_cutoff`, and
  `cards(factors=…, solve_for=…)`. `python3 export/p8e_leaf_probe.py` prints the table below.
* *Finding 1 — the willow figure was wrong, and so was the precision of "0.96-1.00x".* The coverage ratio is
  a MEAN over the per-card v offsets; per card it runs **0.81-1.19** (the offset chooses which 2.5 periods a
  card shows), mean 0.96-1.02 over the seven species. The reviewer's willow 0.93x is one offset inside that
  spread, not a contradiction. The crowns carry 1 000-3 000 cards each, so the mean is what the crown shows.
* *Finding 4 — the "other roots are inside 0-1" claim is now a check.* `leaf_uv_range()` decodes
  `TEXCOORD_0` of every `MAT_leaf_*` primitive out of the WRITTEN glTF and its .bin (UV accessors carry no
  min/max), reports it in `gltf.leaf_uv_range`, and **asserts ⊂ [0,1] whenever the set is not tiled** — i.e.
  on every walk-up export. Measured now: walk-up 0.0000-1.0000 over 674 164 verts, far -1.7498-1.7500.
* *Finding 5 — an unknown species no longer raises.* `UV_TILE_V.get(sp, UV_TILE_V_DEFAULT=1.0)`: a species
  with no entry is exported untiled and named in `gltf.uv_tiling.species_not_tiled`, so an 8d backdrop tree
  reaching this set costs a report line, not a gate-1 traceback.

**Finding 2 — the substantive one: kv shrinks THICKNESS, not WIDTH.** Re-measured with `run_width` (p90 of
the horizontal run of the cut mask), per species at 40 m, in capture px:

| species (card px) | shipped k=1 | kv 2.5 | iso k=2, cutoff unchanged | iso k=2 + cutoff (`iso_cut`) |
|---|---|---|---|---|
| broadleaf (40x47) | 35.7 / 19.7 / 1.00 | 36.2 / 11.2 / 0.98 | 16.9 / 10.3 / **0.76** | **18.4 / 8.4 / 0.93** |
| cypress (27x71) | 26.7 / 18.7 / 1.00 | 26.7 / 14.0 / 1.00 | 18.6 / 12.5 / **0.68** | 23.9 / 14.0 / 0.99 |
| cypress_column (24x64) | 23.9 / 16.9 / 1.00 | 23.9 / 14.0 / 0.99 | 18.3 / 11.7 / **0.68** | 21.1 / 12.2 / 1.00 |
| eucalyptus (31x74) | 30.6 / 18.7 / 1.00 | 30.9 / 14.0 / 0.99 | 20.1 / 13.1 / **0.66** | 25.3 / 14.0 / 1.00 |
| pine (22x64) | 22.5 / 17.8 / 1.00 | 22.5 / 12.2 / 1.00 | 18.3 / 13.1 / **0.66** | 22.5 / 12.2 / 1.03 |
| redwood (21x52) | 21.1 / 15.9 / 1.00 | 21.1 / 11.2 / 0.96 | 15.4 / 10.3 / **0.62** | 19.7 / 10.3 / 0.97 |
| willow (12x67) | 12.6 / 11.2 / 1.00 | 12.6 / 11.2 / 0.99 | 12.6 / 11.2 / 0.98 | 12.6 / 11.2 / 1.07 |

(run width p90 / thickness p90 / coverage ratio. `iso_cut` cutoffs, one per MATERIAL because that is what a
glTF material carries, solved so the mean ratio over the species sharing it is 1.00: `MAT_leaf_broadleaf`
0.50 -> **0.27**, `MAT_leaf_cypress` 0.45 -> **0.21**, `MAT_leaf_eucalyptus` 0.50 -> **0.10**,
`MAT_leaf_pine` 0.42 -> **0.12**.)

Two things the table settles. **(a) A blade's width at 40 m IS its card's width** for every species but the
broadleaf: the cards are 12-31 px wide and no mip can break a mask inside them, so cypress/pine/willow are
already at or under QA 19's "~40 px" and nothing in UV space moves them. **(b) The species QA looked at is
the broadleaf** (TREEFAR_000 / _001 at 36.7 / 38.5 m, cards 40 px), and only a widened u window narrows it —
35.7 -> 18.4 px — at the cost of coverage, which the lowered cut buys back. At the mobile WALK-UP distance
(2.5 m, near-native mip, where a lower cut only adds the painted leaves' antialiased rims) `iso_cut` measures
0.82-1.03x of today's coverage, so it does not fatten the close-up cards either.

**Recommendation: `iso_cut` (ku 2.0, kv 3.0, per-material cutoff).** It is the only variant that moves the
metric QA named while holding the crown's leaf area, and it subsumes the kv win (thickness 8.4-14.0 px).
`UV_TILE_MODE` selects it (`kv25` is what shipped, `off` disables; `PFA_UV_TILE_MODE=` overrides for an A/B).
**`iso_cut` is what `env_trees.glb` now ships** (the lead called it the same evening; `trees_far.py` 30 s of
Blender + `gltf_pack.sh --trees` 1 s + the copy to MAIN, no GPU). The export carries the numbers: mode
`iso_cut`, `gltf.uv_tiling.leaf_cutoff` `{broadleaf 0.50 -> 0.27, cypress 0.45 -> 0.21, eucalyptus 0.50 ->
0.10, pine 0.42 -> 0.12}`, `gltf.leaf_uv_range` -2.0000..2.0000 over 167 876 verts, `species_not_tiled` {},
and `verify_glb` unchanged at 254 rows / 127 placements / 1 007 775 drawn tris / COLOR_0 32/32.
**`env_trees_lod1.glb` (desktop) still carries the Phase 5 cuts 0.42-0.50 and UVs 0.0000-1.0000** — the
alphaCutoff override, like the sampler patch, reaches this one glTF only. `PFA_UV_TILE_MODE=kv25` re-exports
the first variant if QA prefers it.

**The sampler.** The tiled v leaves 0-1, and the shipped leaf samplers are `CLAMP_TO_EDGE` (Blender writes
33071 for an image node set to EXTEND), which would smear the edge texel over every tile past the first. The
script patches `wrapS/wrapT = REPEAT` into the written `env_trees.gltf` — not into the blend: `MAT_leaf_*` and
its textures are frozen, and `master_delivery.blend` is opened read-only. A sampler shared with a non-leaf
texture would be cloned rather than patched (here sampler 1 is the 8 leaf albedo/normal maps and nothing else);
the script asserts that no other texture's sampler moved. gltfpack then omits `wrapS/wrapT` because REPEAT is
the glTF default — that is what `env_trees.glb` ships, and `GLTFLoader` reads it as `RepeatWrapping`.

**Route: patch `env_trees.glb` alone; the leaf materials are NOT renamed.** The two alternatives both fail:
* patching every glb that shares the leaf material names would have to touch `gate5/groups/env_t0.glb` and
  `m_env_t0.glb`, which carry `MAT_leaf_cypress` and `MAT_leaf_eucalyptus` and are **tier 0** — that file set
  must stay byte-identical;
* giving the re-scaled cards their own material names loses the tinted albedo altogether:
  `applyFoliageTextures` does `if ( ! mats.length ) { out.missing.push( name ); continue; }` BEFORE
  `albedoMaps[ name ] = aTex`, so a name that exists only in a lazily loaded root is registered for the
  translucency map and never for the albedo. It would also duplicate 4 albedo + 4 translucency KTX2 textures
  (~8-10 MB of GPU memory on the mobile tier, which is already at 561.9 MB resident).

It is safe to leave every other root at clamp **because their leaf UVs are all inside 0-1** (decoded from
`env.gltf` and `env_trees_lod1.gltf`: u 0.075-0.925 / 0.31-0.69 / 0.29-0.71 / 0.3-0.7, v 0-1), so REPEAT and
CLAMP are the same sampler for them.

**ONE VIEWER LINE IS STILL NEEDED (not this branch's file).** The tinted albedo and the translucency map are
ONE texture object shared by every root using that material name. `applyFoliageAlbedo` re-wraps both from the
lazy root's own sampler (8b item d, a610c6b) — so `env_trees.glb`'s REPEAT wins — but it sets `needsUpdate`
only on the translucency map. In three r186 `setTexture2D` applies the sampler parameters **only inside
`uploadTexture`**, i.e. only when `texture.version` has advanced, so a wrap change on an albedo that has
already been uploaded (the eager near-tree leaf materials in `env_t0`/`env_t2` draw first) never reaches the
GPU. `t.needsUpdate = true` beside the existing `t.wrapS = old.wrapS` closes it.

**Cost.** `env_trees.glb` 3 699 324 -> 3 856 412 B as `kv25` (+4.2 %) and **-> 3 768 500 B as `iso_cut`**
(+69 176 over the pre-8e file, **+1.9 %**; the u tiling widens the u range but the lower cut removes mask
detail, so the meshopt UV stream costs less than `kv25`'s), tier 2, `glb_lazy`, mobile-only in
practice (`device.js`: mobile `walkupMesh: '0'`, `farTreeMesh: 45`; desktop leaves `walkupMesh` null and draws
`env_trees_lod1.glb`, falling back to this file only if that glb 404s or fails the join). The growth is the UV
stream: gltfpack quantises TEXCOORD_0 over the file's own range, and the tiled v widens it 3.5x
(`KHR_texture_transform` v scale 16.003 -> 56.010 as `kv25`, 64.011 as `iso_cut`), which costs entropy and
takes the UV step from ~0.25 to ~0.87 (`kv25`) / ~1.0 (`iso_cut`) texels of a 1024 px map — still sub-texel, and ~0.02 px on screen at 40 m. Tier 0 is untouched and
byte-identical; no other glb changed.

**Stale after this change, and why it stays stale:** `out/gate5/manifest.json` still advertises
`files[].bytes` = 3 699 324 for this file (the progress readout only; `manifest_mobile.json` does not list the
lazy glbs at all). `python3 export/tiers.py --no-pack` was run to refresh it and **reverted**: it does refresh
the byte count and nothing else of this export (desktop `files[540].bytes/transfer` 3 699 324 -> 3 856 412,
`tiers.bytes/transfer_bytes[2]` 58 344 715 -> 58 501 803, the two grand totals; mobile byte-identical), but it
ALSO re-measures `tiers.boot_overhead_bytes` from `MAIN/web/dist`, which has been rebuilt since the manifests
were written (bundle `index-CglJAl3O.js` 1 197 522 B -> `index-CLU6xaD-.js` 1 199 428 B, boot total
1 115 259 -> 1 116 029 B, and the `tier0_trim.reason` sentence that quotes it). That is another agent's viewer
build, not this change, so the manifests were restored byte-identical to MAIN and the refresh belongs to
whoever next rebuilds them — by then the bundle it measures will be the one being shipped. Tier 0 is unaffected
either way: this file is tier 2, and the tier-0 wire total moves only by the boot-overhead line.

```
# reproduce (CPU only for the probe; the export is one Blender, no GPU)
python3 export/p8e_leaf_probe.py                                     # the measurement + export/out/p8e/leaf_probe.json
scripts/blender_run.sh 1200 -- --background <MAIN>/master_delivery.blend --python export/trees_far.py
export/gltf_pack.sh --trees                                          # toktx (cached) + gltfpack + verify_glb
cp export/out/gate1/{env_trees.glb,env_trees.gltf,env_trees.bin,env_trees_ktx2.gltf,trees_far.json,verify_glb.json} <MAIN>/export/out/gate1/
cp export/out/gate3/trees_far/{topology.json,trees_far_lod2.blend}     <MAIN>/export/out/gate3/trees_far/
(cd web && npm test)
```

## Phase 8d — the ENV re-export after the backdrop rebuild, with 8a-3 riding it (2026-09-19, export engineer)

Chain, in the order it actually has to run (the brief's order put the Gate 2 bake second; `gltf_gate1` cannot
run before it, because it loads `backdrop_uv1.npz` onto the export set and asserts the loop counts):

```sh
export PFA_GATE1_BLEND_DIR="$PWD/export/out/gate1"        # else Gate 2 reads the phase6-export worktree
scripts/blender_run.sh 2400 -- --background <MAIN>/master_delivery.blend --python export/export_set.py -- --gate1
python3 export/p8d_pin.py                                  # THE PIN. Stop here if it fails.
scripts/blender_run.sh 1800 -- --background --python export/gate2_probe.py
scripts/blender_run.sh 1800 -- --background --python export/gate2_set.py
rm export/out/gate2/bake/ENVBD__backdrop_{building,skylight,roof,roof_tile,forest,hill}.json \
   export/out/gate2/bake/ENVBD__lawn.json export/out/gate2/tex_ktx2/gate2_ENVBD__lawn_*.ktx2
export/bake_queue.sh --gate2 start                         # GPU; 7 jobs, 52.7 s
export/gltf_pack.sh --gate2                                # r4 fix: it now replaces only what it re-encodes
cp export/out/gate2/backdrop_uv1.npz export/out/gate2/backdrop_uv1_shipped.npz   # see below
# manifest_v2 FIRST: manifest_v3 asserts the `lightmap_encoding` carry that v2 writes (r2 correction)
python3 export/manifest_v2.py && python3 export/manifest_v3.py
scripts/blender_run.sh 1200 -- --background export/out/gate1/gate1_set.blend --python export/gltf_gate1.py
export/gltf_pack.sh --gate1 ; python3 export/p8d_pin.py --glbs
scripts/blender_run.sh 900 -- --background <MAIN>/master_delivery.blend --python export/shrub_lod1.py
export/gltf_pack.sh --shrubs
node web/tools/instance_rows.mjs <W>/export/out/gate1/env.glb        <W>/export/out/gate3/instance_rows.json
node web/tools/instance_rows.mjs <W>/export/out/gate1/env_shrubs.glb <W>/export/out/gate3/instance_rows_shrub_lod1.json
python3 export/gate4_instance_order.py && PFA_ORDER_SET=shrub_lod1 python3 export/gate4_instance_order.py
python3 export/gate5_instance_rows.py && python3 export/gate4_order_selftest.py && python3 export/verify_glb.py
python3 export/manifest_v2.py && python3 export/manifest_v4.py && python3 export/budget_doc.py
export/sync_main.sh && python3 export/tiers.py && python3 export/tiers.py --mobile && python3 export/tiers.py --no-pack
python3 export/verify_glb.py --gate5 && (cd web && node test/tiers_test.mjs) && python3 export/name_sweep.py
export/sync_main.sh
```

**The pin** (`export/p8d_pin.py`, CPU, exit 1 on failure, record in `out/gate1/p8d_pin.json`): 21 checks, all
green — uv1 groups 52 / atlas tiles / coverage / min 0.0876, uv2 meshes 66, lightmap slots and assets,
`uv_missing` 10/0, near trees 20, far billboards 127 with both lists identical in content **and order**, ARCH
949 382 and ORN 1 099 192 placed unchanged, ENV placed 894 974 -> 901 874 = **+6 900**, and the lawn group
renamed with nothing stale left. After the pack, `--glbs`: **arch.glb, orn.glb, ground.glb byte-identical**.

**Three traps this chain walked into, all now fixed in code or documented:**
1. `gate2_common.GATE1_BLEND_DIR` defaults to the **phase6-export** worktree. Every Gate 2 step needs
   `PFA_GATE1_BLEND_DIR`, or the bake is built from another branch's geometry.
2. `gltf_gate1.py` read `backdrop_uv1.npz` from a hard-coded MAIN path — now local-then-MAIN, like every
   other hand-off. Its loop-count assert is what caught it (297 480 vs 318 180 loops on backdrop_forest).
3. `gltf_pack.sh --gate2` starts with `rm -rf tex_ktx2`, so in a worktree that has no `tex/` PNGs it leaves
   only the maps it just encoded (36 of 203). Restore MAIN's others (`rsync -a --ignore-existing`) **before**
   `manifest_v3`, or the manifest is written against a partial texture set.

**`backdrop_uv1_shipped.npz` was promoted** (it is the canary that the shipped backdrop textures and the
shipped UV1 agree). Measured before promoting: of the ten backdrop meshes only **backdrop_forest** differs in
UV SET (297 480 -> 318 180 loops: the belt) and only **backdrop_building** differs per loop while its UV set
is unchanged (the 640-object merge order moved, the atlas did not); the lawn rename is bit-identical
(`allclose` on the arrays); the other seven are untouched. Both meshes that moved were re-baked this round,
so nothing ships against a stale layout.

**8a-3, measured per material** (not claimed): `MAT_shrub` ku2/kv2 on 1 196 cards, `MAT_shrub_light` ku2/kv2
on 1 822, `MAT_shrub_dry` **ku1/kv2** on 284 (its LOD2 card is 0.89x wide / 1.77x tall against its LOD1 card,
so an isotropic 2 would have halved its leaf width the wrong way — review r3 finding 7), `MAT_reeds`
untouched. Coverage **at the shipped factors**, from `p8e_leaf_probe.py --shrubs` (it now reads `SHRUB_TILE`, so its
default columns are the asset's own): at cam05's 25 m LOD switch shrub **1.08x** (blob 21.7 -> 16.9 px),
shrub_light **1.07x** (23.8 -> 16.4), shrub_dry at ku1/kv2 **0.98x** (9.8 -> 9.4), reeds 1.00x untouched;
at 54 m 1.00x (15.4 -> 7.0) / 1.00x (15.4 -> 7.0) / 1.03x (4.2 -> 4.2) / 1.00x; at cam03's 25 m 0.99x /
0.99x / 1.05x / 1.00x. So the three tiled materials land in **0.98-1.08x**, and nothing was taken on trust. Samplers went REPEAT
in `env.gltf` for those three materials only (cloned, because sampler 1 is shared with the tree leaf cards)
and in `env_shrubs.gltf` to match, so the one shared runtime albedo cannot be re-wrapped to CLAMP.

**r4 fixes (pre-deploy).** (1) `env.gltf` now patches the four `MAT_leaf_*` materials to REPEAT beside the
three shrub ones - `env_trees.gltf` ships those same names on a REPEAT sampler with UVs at -2..2, and
`foliageLazy` copies each root's sampler onto the ONE shared tinted albedo, so a CLAMP here was a
last-root-wins hazard. In the packed `env.glb` the four leaf materials move from sampler 1 (33071) to the
wrap-less sampler 2 (= REPEAT, the glTF default) beside the shrubs; `MAT_reeds` stays on 1 = CLAMP, and
this root's own leaf UVs are asserted inside 0-1 (measured 0.0000-1.0000 over 250 980 verts), so it is a
no-op for its pixels. Cost: `env_t2.glb` **-64 B**, `env_t0.glb` and the whole of tier 0 **unchanged**.
(2) `gate2_common.GATE1_BLEND_DIR` defaults local-then-MAIN instead of to the phase6-export worktree.
(3) `gltf_pack.sh --gate2` no longer `rm -rf`s `tex_ktx2`: it removes only the maps whose PNG source is in
`out/gate2/tex` (the ones it is about to re-encode) and prints how many it kept.

**Cost.** `env_t0.glb` **2 172 384 -> 2 172 696 B (+312)** — the only tier-0 geometry change; tier 0 total
48 269 972 -> **48 270 284 (+312)**; first frame on the wire 49 393 776 -> **49 394 896 (+1 120**, the +312
plus the boot-overhead re-measure of the rebuilt `web/dist`), **605 104 B under the 50 000 000 rule**. Mobile
tier 0 +312, first frame 47 630 546. `env_t2.glb` 6 787 864 -> 6 956 512 (+168 648: the belt and the shrub
UVs), `env.glb` 38 181 724 -> 38 348 124, `env_shrubs.glb` 668 352 -> 668 388, and the manifests now carry
8e's `env_trees.glb` at 3 768 500 (the refresh that rode with this chain). `verify_glb` PASS, `--gate5` PASS
desktop and mobile, `tiers_test` all green, `name_sweep` PASS (127 exempt treeboards, 0 to explain).

## Phase 8d r2 — the hall-east belt (2026-09-19, export engineer, branch `phase8d-export2`)

The four icosphere belt objects left `backdrop_forest` and 39 ordinary far trees took their place on the hall's
east face. Chain as r1 (the `PFA_GATE1_BLEND_DIR` export, the pin first, Gate 2 only for what moved) with four
differences, all of them recorded in code:

1. **The pin moved on purpose, and says so.** `p8d_pin.py` pins `trees_total` **186**, `far_billboards` **166**,
   `lod2_blob_objects` **85**, `near_exported` **20**, and `EXPECT_ENV_DELTA` **-6 822** (= -6 900 icospheres
   +78 billboards, ENV placed 901 874 -> **895 052**). Everything else still pins to MAIN and did: uv1 groups
   52 / tiles / coverage / min 0.0876, uv2 66, lightmap slots and assets, `within_radius` 77,
   `near_tris_used` 391 908, ARCH 949 382, ORN 1 099 192, the near list in order.
2. **The far-row re-sort is an INTERLEAVE, not an append.** `bpy.data.objects` is name-sorted, so the belt names
   land among the existing ones and every `TREEFAR_###` index after the first of them shifts. The pin therefore
   checks the invariant instead of the byte order: the 127 existing rows survive with their content and their
   relative order (the billboard id is excluded from that comparison - it is what shifts), exactly 39 rows are
   new, and every new row is a name from `docs/phase8d_belt_r2_trees.json`. `p8d_pin.json` records where the
   interleave starts and how many billboards were re-indexed. **Any diagnostic that quoted a `TREEFAR_###`
   index must be re-read against the new list**; the atlas joins by PROTOTYPE and the instance rows by position
   in the re-dumped order, both regenerated here, so nothing else depends on the index.
3. **Three prototypes are new to the far block** (`ENV_tree_cypress_column_s2_LOD2`, `_s31_LOD2`,
   `ENV_tree_pine_s29_LOD2`): the Gate 3 `impostor_prototype_map` was built from the previous far list and has
   no key for them. `manifest_v4` now extends the map with `gate3_set.py`'s own rule (an impostor is always the
   LOD1 prototype), **asserts the target is an already-baked prototype**, prints what it added and records it as
   `impostors.prototype_map_added`. No atlas and no impostor blend is re-baked.
4. **Vertex AO: nothing to bake and nothing stood in.** The far block builds one LOD2 mesh per IMPOSTOR
   PROTOTYPE; the belt added placements, not prototypes, so the run reports `prototypes=16`, **COLOR_0 16/16**
   attached from the existing `vertex_ao.npz` at `topology_rev` 2, no refusal. `trees_far.py`'s hard-coded
   `== 127` assert is replaced by the invariant that matters (every far row gets a placement).

**Gate 2 was one job.** Comparing the fresh `backdrop_uv1.npz` with the shipped one, `backdrop_forest` is the
only mesh whose UV SET changed (318 180 -> 297 480 loops); every other backdrop group is identical, so only
`ENVBD__backdrop_forest` was purged and re-baked (5.2 s: albedo max 0.824, roughness max 0.953, no clipping,
coverage 0.150-0.283). The r4 fix held: `gltf_pack --gate2` **kept 186 existing maps** and replaced 17.

**Chain-order correction:** `manifest_v3` asserts the `lightmap_encoding` carry that `manifest_v2` writes, so
the order is **v2 -> v3 -> v4**; the r1 listing had v3 first and only worked because a stale gate1 manifest
still carried it. Both far-tree sets must be re-run together (`trees_far.py` and `PFA_TREES_SET=walkup`), or
`verify_glb` fails the walk-up/far row comparison - which is exactly what caught it here.

**Bytes.** `env.glb` 38 348 124 -> **38 180 924**; `env_trees.glb` 3 768 500 -> 3 769 736 and
`env_trees_lod1.glb` 7 642 344 -> 7 643 580 (166 placements each, 332 rows, COLOR_0 32/32, walk-up order
matches); `env_t2`/`m_env_t2` 6 956 448 -> **6 789 444**; `env_t0`/`m_env_t0` 2 172 696 -> 2 172 808 (+112).
Tier 0 **48 270 284 -> 48 139 115 (-131 169)** and the first frame **49 395 053 -> 49 270 952 (-124 101)**,
**729 048 B under the 50 000 000 rule** - the -131 281 of it is the tier-0 trim solver dropping one more ORN
normal (`gate2_ORN__ORN_capital_inner_v1_LOD0_a_normal`, hero order -0.00019) now that the boot overhead grew;
the geometry contributed +112. `budget_doc` line 288 is back to 99 640 / 11.0 % with the belt named as far
billboards. arch / orn / ground glbs byte-identical to MAIN; `verify_glb` PASS, `--gate5` PASS desktop and
mobile, `tiers_test` green, `name_sweep` PASS, `npm test` all passed (three r186).

### r2 follow-ups (review r5, all closed here)

* **`CLASS_BUDGET["ENV"]` stays at 902 000** (the 8a gate's value). The belt SPENDS 6 822 fewer triangles
  than the icospheres it replaced - 895 052 placed against 902 000 - so the constant needed no decision;
  it is stated here because r2 changed the placed number and the review asked for the line.
* **The far-tree counts are now checked in three places at once** (`verify_glb --gate5` check 5): the export
  set's `tree_rule.far_billboards`, `trees.far_mesh.placements` / `walkup_mesh.count`, and the per-placement
  lighting rows. Every pair but that one was already checked, which is how the r2 manifest shipped 127
  placements against a 166-instance glb.
* **`manifest_v4` joins the per-placement irradiance BY WORLD LOCATION**, which is what
  `instance_irradiance.json` says its key is ("the object name is a label"). The name join was only
  incidentally right: the belt's interleave re-pointed 87 of the 127 `TREEFAR_###` ids.
* **A `TREEFAR_###` id is not a stable reference.** Anything that quotes one - a probe box, a diagnostic, a
  review note - must be re-read against the current `tree_far` list. `p8e_leaf_probe.py`'s orbit boxes name
  the trees they measured at the r1 ids; the geometry pass in that probe recomputes them from the
  placements, so its table is unaffected, but the box LABELS are r1 names.

### r5 blockers closed (the far-tree manifest and the per-placement irradiance)

**Blocker 1 - the manifest advertised 127 against a 166-instance glb.** `manifest_v4` had run before
`trees_far.py`, so `trees.far_mesh.placements`, `walkup_mesh.placements.count` and the per-placement
lighting rows were all the pre-belt 127; `foliageLazy` would have failed the join and dropped the whole
far-tree mesh layer, walk-up set included. All three now read **166**, and three guards make the class of
bug unshippable: `manifest_v4` asserts `len(trees_far.json placements) == len(tree_far)` plus the
billboard identity row by row and refuses a glb older than the report; `verify_glb --gate5` gained check 5,
which compares `tree_rule.far_billboards`, `far_mesh.placements`, `walkup_mesh.placements.count` and the
lighting rows **in one place** (every pair but that one was already checked); `web/test/foliage_lazy_test.mjs`
takes the count from the manifest (`FAR_N`) instead of the literal 127 / 254 it used to assert.

**Blocker 2 - the per-placement irradiance could not be regenerated.** `instance_irradiance.json` declares
its key as WORLD TRANSLATION ("the object name is a label"), but `manifest_v4` joined it by the
`TREEFAR_###` label, and the belt's interleave re-pointed 87 of the 127 ids while 39 had no row at all.
Two changes: the join is by world location on a 0.02 m grid, with a uniqueness assert on the cell; and the
39 belt rows were **baked, not stood in**. Price, measured from the 6c records (554 s for 127 placements =
4.36 s each): 166 x 4.36 = **~12 min**, under the lead's 15-minute rule. Actual: four `tfirr_*` jobs,
**199.1 + 189.5 + 198.5 + 192.2 = 779 s = 13.0 min** of GPU, 4.69 s per placement, all rc=0;
`trees_far_compose.py` then wrote **166 placements, lum 0.1369-6.0972, 0 zero placements, 16/16 E_bake**.
The bake needs two files `sync_main.sh` deliberately does not copy - `gate3_bake.blend` (315 MB) and
`gate3_imp.blend` (67 MB) - plus `trees_far/ao` and `trees_far/ebake`; they were APFS-cloned read-only
from the **phase6-bake** worktree, which is also what keeps the new rows in the same scene and rig as the
127 that were already there. `trees_far_compose.py` and `trees_far_set.py` no longer hard-code 127.

## QA 23 — the far-tree irradiance goes back to 6c for the 127, the belt keeps the r2 bake (2026-09-19)

QA 23 measured what `docs/decisions.md` predicted: the r2 re-bake brightened every crown read against a
background by **4-16 %**, 7 of 10 boxes moving AWAY from the Phase 8 Cycles references, and the 8e blade
margin was lost photometrically rather than geometrically. The fix is `export/p8d_irr_restore.py` (CPU
only, no Blender, no GPU):

* **The 127 existing far trees go back to their 6c values.** Source: the 6c file itself,
  `<phase6-bake worktree>/export/out/gate3/trees_far/instance_irradiance.json`, generated
  **2026-09-17T10:16:23**, 127 rows, md5 `11212fbcc3bbe8482f5396f8a8f9917b`, untouched since the 6c bake.
  The deploy-10 manifest was checked and **rejected as a source**: its lighting block is the r2 one
  (generated 2026-09-19T22:47:28) and all 127 rows differ.
* **The 39 hall-belt trees keep the r2 bake** - they have no 6c value, and re-baking them alone would need
  the GPU that is on the 4K hero.
* Joined **by world location** on the same 0.02 m grid `manifest_v4` uses, because the belt's name-sorted
  interleave re-pointed 87 of the 127 `TREEFAR_###` labels. Every per-mesh and per-file statistic is
  recomputed from the merged rows, each row carries a `source` field (`6c` / `8d-r2`), and `rows_source`
  in the file records the counts, both source md5s and why the deploy copy was not used.
* **The two populations, as the impostor path applies them** (`clamp(E_placement / E_bake, 0, 4)`,
  strength 1.0, reported as luminance): **6c n=127 median 0.9415** (p10 0.2394, p90 1.3476);
  **belt n=39 median 0.2424** (p10 0.0798, p90 1.7596). The belt's low median is its position: the hall's
  east face is in shade for most of the day. File `lum_mean` 2.897442 -> **2.012746**.
* Chain re-run: manifest v2 -> v3 -> v4, tiers x3, `verify_glb --gate5` PASS desktop and mobile (far-tree
  counts 166/166/166/166 on both), `tiers_test` green, `npm test` all passed. Tier 0 unchanged at
  **48 139 115**; first frame 49 273 775 -> **49 273 819** (+44 B, the manifest's own size), **726 181 B
  under the 50 000 000 rule**. Only the gate3 / gate5 manifests and the irradiance JSON changed.

### Recorded, not fixed: cam03 draws the belt trees as meshes (QA 23 residual)

**What governs it.** On desktop the viewer loads the WALK-UP set (`device.js` leaves `walkupMesh` null), so
the distance is `trees.walkup_mesh.draw_within_m` = **15 m** (`WALKUP_DIST_M` in `foliageLazy.js:57`), plus
the fade band (5 m) and `CULL_MARGIN_M`, and it is applied **per CHUNK** by `buildDistanceCull`
(`chunk: {minRadius: 12, minCount: 2, maxDepth: 3, budget: 256}`) - a chunk is submitted whole if any part
of it is inside the limit. The belt stands 4.5 m apart along the hall's east face and **3 of its 39 trees
are within 15 m of cam03** (nearest 6.5 m, median 96.7 m), so the chunks those three sit in are submitted
with their neighbours: that is the +1.3 M triangles and +28 draws QA measured. On mobile the far set is
used instead (`farTreeMesh` 45 m), where the same rule applies to 7 934-triangle meshes.

**What a billboard-only rule for HB-tagged trees would cost.** Tag the 39 rows in `tree_far` (the belt
report already carries the HB tag) and skip them in `trees_far.py` for BOTH sets: they would always draw as
impostor quads. Saves at most **39 x 29 747 = 1.16 M** submitted triangles on desktop (**0.31 M** on
mobile) and 78 instance rows (~28 draws when chunked); `env_trees.glb` and `env_trees_lod1.glb` each lose
39 rows (~1.2 kB each). The cost is the close-up: a walker beside a belt tree - and cam03 stands 6.5 m from
the nearest one - would see a magnified impostor card instead of a mesh, which is the defect Phase 7 fixed
for the other far trees. A per-row rule ("HB trees are meshes only within 8 m") would need the viewer to
carry a per-row distance, which it does not today.

## Phase 9 item 1 — the belt's billboard-only rule, per set (2026-09-20, export engineer, branch `phase9-export`)

This closes QA 23 residual 3 / QA 24 item 3 (`cam03 draws the belt trees as meshes`, recorded two sections
up). **Nothing here has been run**: the rule is implemented and self-tested on CPU, and the export re-run
rides the lead's lighting chain. The command list is at the bottom of this section.

### What was measured first (CPU, no Blender)

`export/belt_rule.py` is the rule AND its own analysis, so neither is prose that can age:
`python3 export/belt_rule.py` prints the per-set table, `python3 export/belt_rule.py --frustum` prints the
cam03 table below; both exit non-zero if an invariant breaks. The station, the lens, the sensor, the crown
sizes and `inner_px` are all read from the gate3 manifest — nothing in the table is typed in. From the cam03
station (81.0, 12.04, 1.7, 18 mm on 36 mm, 16:9 — a 90° horizontal field), of the three belt trees whose
trunk base is inside 15 m **two are actually in frame**:

| `tree_far` | tree | d to crown (trunk, xy) | in frustum | ndc x | ndc y | crown on screen | impostor texel |
|---|---|---|---|---|---|---|---|
| 40 | `ENV_tree_cypress_33_LOD1` | **7.1 m** (6.5, 5.9 xy) | **yes** | -2.27 .. **+0.10** | -1.81 .. 4.42 | 10.7 x 13.4 m, 1 435 px wide | **17.7 px** |
| 147 | `ENV_tree_redwood_26_LOD1` | 8.2 m (6.6, 6.1 xy) | **no** — only one corner clears the near plane (+0.2 m) and it projects to ndc x -27.8 | – | – | – | – |
| 41 | `ENV_tree_cypress_34_LOD1` | **11.8 m** (10.4, 10.1 xy) | **yes** | -1.74 .. **-0.38** | -0.85 .. 3.03 | 11.8 x 17.6 m, 956 px wide | **11.8 px** |

Two readings the table depends on. "d to crown" is the eye-to-**crown-centre** distance, because that is
where a card is quoted; the rule itself measures the **trunk base** (the second number), which is the row's
`trunk_base` and the only position the export knows. And cypress_33's crown centre is 0.9 m *behind* the eye
plane while the tree is in frame: at 6.5 m a 13.4 m crown straddles the camera, and the near half of it
(corners to +5.7 m) is what draws. So "in frustum" is the ndc box of the corners that clear the near plane,
never a centre-point test — a centre test calls cypress_33 invisible and would have justified option (a).

"impostor texel" = the atlas's 81 inner px per frame (1 K, `impostors.frame_px` 85 / `inner_px` 81) spread
over the crown's screen width at 1920 px wide, i.e. what a magnified card would show there. The 8e card
table's believable band is 9-13 px for a foliage CLUMP at 40 m; 17.7 px of a single octahedral frame across
the left half of the hero colonnade frame is the defect Phase 7 built the walk-up set to cure.

So **(a) billboard-only for all 39 is rejected** (it puts those two cards in cam03's frame), and **(b) as
the brief worded it — "outside every station's walkable reach" — is empty**: every one of the 39 belt trees
is **0.2-7.3 m from a walkable surface** (`walk_dist_m`, median 3.5), so walk distance cannot discriminate.
**(c) a per-row mesh distance is not taken here**: the dissolve's `pfaSwitchDist` is a shared uniform, so a
per-row distance needs a per-instance attribute in the shader as well as in `buildDistanceCull` — that is a
viewer change, and it is written down as one rather than half-built here.

### The rule that shipped, and what it saves

**A row tagged `HB` keeps its mesh only if its trunk base is within that SET's own viewer draw distance plus
the 5 m fade band of a QA station eye.** Beyond that the fragment dissolve discards every fragment, so no
station can ever see the mesh and the row is its impostor at every distance. The radius is per set because
the two sets are drawn at different distances, which is the whole point:

| set | glb | drawn within | radius | tagged rows kept | billboard-only | placed tris | rows |
|---|---|---|---|---|---|---|---|
| walk-up (**desktop**) | `env_trees_lod1.glb` | 15 m | **20 m** | 4 | **35** | 4 937 933 -> **3 890 782** (**-1 047 151**, -21.2 %) | 166 -> **131** |
| far (**mobile**) | `env_trees.glb` | 45 m | **50 m** | 22 | **17** | 1 317 097 -> **1 182 338** (**-134 759**, -10.2 %) | 166 -> **149** |

Against QA 23's measurement (`cam03 6 044 248 -> 7 346 118, +1 301 870, draws 343 -> 371`), the desktop rule
removes **1 047 151 of the 1 301 870** submitted triangles at cam03, about **24 of the 28** draws; mobile
(4.92 -> 5.22 M, draws 380 -> 424) loses **134 759** and about 19 draws. The four rows desktop keeps are the
only belt trees any station can see as meshes: cypress_33 6.5 m, redwood_26 6.6 m, cypress_34 10.4 m,
cypress_35 16.7 m, all at cam03. The rule is deliberately conservative about WHICH station: it is a sphere
about each eye, not a frustum test, so six of the far set's 22 keeps are cam04 (the rotunda ceiling camera,
which looks straight up) at 43-50 m. A frustum test would drop them; a sphere is what survives a walker
turning round on the spot.

**Recorded, not fixed: a free walker.** The viewer's walk is not confined to the stations, so a walker who
leaves cam03 and follows the path along the hall's east face comes within a few metres of one of the 35
excluded trees and sees the magnified card. That is the price of (b) and it is what (c) would buy back.

### THE ONE HAND-OFF THAT GATES THE SHIP — the viewer must re-light a billboard-only impostor

`foliageLazy.js` builds its impostor complement from the MESH placements
(`placements.find( q => q.billboard === t.id )`, then `activateImpostorMeshes`). A row with no mesh
placement therefore gets neither `iNear = 1` — **right**, its impostor must never fade out — nor `iIrr`,
which is **wrong**: it loses the QA-23 `E_placement / E_bake` modulation, and the belt's median ratio is
**0.2424** (it stands in the hall's shade), so those 35 crowns would draw about **four times too bright** and
QA 23's fix would be undone. **Do not ship the rule before this lands.** Everything the fix needs is already
in the manifest: `trees.far_mesh.lighting.mesh.placements` carries a row for **every** `tree_far` tree with a
`mesh: true|false` flag (`with_mesh` / `billboard_only` counts beside it), and `trees.<set>.billboard_only`
names the excluded rows with their billboard id and location. The viewer change is to set `irr` for a row
that has no mesh placement while leaving `near` at 0.
`web/test/foliage_lazy_test.mjs` section 4c holds the contract: it drops one placement and asserts the
impostor is NOT flipped, that the lighting row survives, and it reports the missing `iIrr` as the hand-off.

### What changed, and the invariants that had to be re-cut

* **`export/belt_rule.py` (new)** — the rule, with no `bpy`, so it can be measured and regression-tested on
  CPU. `trees_far.py` imports it and asserts its own `SET["draw_within_m"]` against `DRAW_WITHIN_M`, so the
  analysis and the export can never place different rows. `--frustum` is the cam03 measurement above, and it
  carries the invariant that decides the whole question: **no belt row that is in a station's frame may be
  billboard-only in either set**. Move a station, re-cut the belt, change a lens or change a
  `draw_within_m`, and this run FAILs by name instead of shipping a magnified card into the frame.
* **`export/trees_far.py`** — tagged rows outside the radius are skipped; `placements + billboard_only ==
  tree_far` replaces the old equality; the two `zip(placements, far)` loops zip against the kept rows;
  `TREEFAR_###` is still the `tree_far` index, so every downstream key is unchanged. The **cross-set order
  check becomes a subsequence contract**: every node of this set must be a node of the other set's glTF, in
  the same relative order and at the same translation, and this set may hold fewer rows but never one the
  other does not have.
* **`export/manifest_v4.py`** — the lighting list is per FAR TREE, not per mesh placement (see the hand-off);
  the count assert closes on `placements + billboard_only`; the billboard identity is checked through each
  row's own `index` instead of its position; both sets carry a `billboard_only` block; and the walk-up
  placements are written out **as a list** now that the two sets differ — a shape `foliageLazy` already
  reads (`Array.isArray( w.placements ) ? w.placements : ... same_as`), so **no viewer change is needed for
  the placements**. While the sets do hold the same rows the block still says `same_as`, exactly as before.
* **`export/p9_rule_selftest.py` (new)** — the CPU negative suite for all of it, in the pattern of
  `gate4_order_selftest.py`: it builds the two reports the rule WOULD write (the real ones minus the
  excluded rows), pushes them through `manifest_v4.trees_lighting_block` and `verify_glb.far_tree_counts`,
  and asserts the five ways of getting it wrong are each reported — a vanished mesh row, an inflated
  billboard-only count, a lighting list cut down to the mesh placements, a walk-up row the far set does not
  have, and an export set that disagrees with the manifest — plus that the PRE-rule shape
  (166 / 166 / `same_as`, no `billboard_only`) still passes unchanged. 16/16 today.
* **`export/verify_glb.py`** — the far-tree count block is factored out as `far_tree_counts(man)` so the
  suite above can feed it bad data; check 5 becomes a per-set identity (`mesh rows + billboard-only = far trees`)
  plus the nesting (`walkup <= far`) and the lighting list at one row per far tree;
  `trees_lod1_order_check` accepts fewer rows per node on the walk-up side, never more, and still requires
  the same node sequence and materials.
* **`export/p8d_pin.py`** — the export set does **not** move (`tree_rule` 186 / 166 / 85 / 20, ENV placed
  895 052, arch/orn/ground byte-identical): a billboard-only row keeps its billboard, its impostor frame and
  its irradiance row, and loses only an instance row in the mesh glbs. Four pins are added downstream of the
  export set: `trees_far[far|walkup].placements` **149 / 131**, `billboard_only` **17 / 35**, `placed_tris`
  **1 182 338 / 3 890 782**, and the subset relation. Run against MAIN's pre-rule reports the pin FAILs on
  exactly those six numbers, which is the delta.

### The chain the lead runs (after the lighting re-bake, NOT run here)

Both far-tree sets must be re-run **together** and in this order (`walkup` reads `env_trees.gltf` for its
order check), then everything that states a far-tree count. `<W>` = this worktree, `<MAIN>` = the main
checkout.

```sh
export PFA_GATE1_BLEND_DIR="$PWD/export/out/gate1"
python3 export/belt_rule.py && python3 export/belt_rule.py --frustum \
    && python3 export/p9_rule_selftest.py                        # CPU: the two tables, the invariants,
                                                                 # the manifest/verify readers - all first
scripts/blender_run.sh 1200 -- --background <MAIN>/master_delivery.blend --python export/trees_far.py
PFA_TREES_SET=walkup scripts/blender_run.sh 1200 -- --background <MAIN>/master_delivery.blend \
    --python export/trees_far.py
export/gltf_pack.sh --trees                                      # env_trees.glb
export/gltf_pack.sh --trees-lod1                                 # env_trees_lod1.glb
python3 export/p8d_pin.py                                        # THE PIN (149/131, 17/35, the tri counts)
node web/tools/instance_rows.mjs <W>/export/out/gate1/env_trees.glb \
     <W>/export/out/gate3/instance_rows_trees_far.json
node web/tools/instance_rows.mjs <W>/export/out/gate1/env_trees_lod1.glb \
     <W>/export/out/gate3/instance_rows_trees_far_lod1.json
python3 export/gate4_instance_order.py && PFA_ORDER_SET=shrub_lod1 python3 export/gate4_instance_order.py
python3 export/gate4_order_selftest.py && python3 export/verify_glb.py
python3 export/manifest_v2.py && python3 export/manifest_v3.py && python3 export/manifest_v4.py
python3 export/budget_doc.py
export/sync_main.sh && python3 export/tiers.py && python3 export/tiers.py --mobile \
    && python3 export/tiers.py --no-pack
python3 export/verify_glb.py --gate5 && python3 export/verify_glb.py --gate5 --mobile
(cd web && npm test) && (cd web && node test/tiers_test.mjs) && python3 export/name_sweep.py
python3 export/p8d_pin.py --glbs                                 # after the pack, never before
export/sync_main.sh
```

Expected after it: `env_trees.glb` and `env_trees_lod1.glb` both smaller (17 / 35 fewer instance rows,
~1.2 kB each, the meshes themselves unchanged); **no tree glb is in tier 0**; `env_t2` smaller by the same
rows; `verify_glb` and `--gate5` PASS on desktop and mobile with far-tree counts `149 + 17 = 166` and
`131 + 35 = 166` and `lighting_rows 166`.

**The one thing that does grow is the manifest**, which IS in the first frame: the walk-up placements stop
being a `same_as` reference and become a 131-row list, the two `billboard_only` blocks arrive, and every
lighting row gains its `mesh` flag. Measured on the shipped gate5 manifest by replaying the rule on it:
**2 141 481 -> 2 189 980 B raw (+48 499)**, and on the wire, which is what the 50 MB rule counts,
**230 224 -> 236 390 B gzipped (+6 166)** — **0.8 % of the 726 181 B of headroom** the last deploy had. An
index-only subset shape would save most of that and cost a viewer change; at 6 kB it is not worth one.

**The viewer's `iIrr` fix must be in the same deploy.**
