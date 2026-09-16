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
    2 join back to a mesh unambiguously. `gltf_gate1.py` now encodes every mesh at **one range = 43.31984**
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
