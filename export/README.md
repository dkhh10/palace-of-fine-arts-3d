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
