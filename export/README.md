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
