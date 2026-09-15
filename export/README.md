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
| `sky` | the two equirects (`camera` = background sphere, `glossy` = PMREM source), the mapping, how the Light Path branch was isolated, and the sun's measured position in the image |
| `gltf`, `glb` | what the exporter and gltfpack produced, including `lightmap_slot` and `viewer_action` |
| `reference_frame` | the Cycles frame the viewer is scored against |
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
