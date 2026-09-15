# Technical notes for Blender 5.2.1 headless work (lead-verified 2026-09-06)

All snippets were run with `/Applications/Blender.app/Contents/MacOS/Blender --background --python x.py`.

## Engines, colour, denoise
- `scene.render.engine = 'BLENDER_EEVEE'` (this is Eevee Next) or `'CYCLES'`. `common.configure_eevee()` / `common.configure_cycles()`.
- `scene.view_settings.view_transform = 'AgX'`; looks by string e.g. `'AgX - Punchy'`, `'AgX - Base Contrast'`.
- `scene.cycles.denoiser = 'OPENIMAGEDENOISE'`, `scene.cycles.device = 'GPU'` (Metal, Apple M2 10 cores: budget ~1-3 min per 1280x720 at 128 spp for a full scene, expect 4K finals to take an hour or more).
- Headless Eevee at 1280x720 of the placeholder scene: 1-5 s per frame after shader compile.

## Sky texture (world)
`ShaderNodeTexSky` props: `sky_type` ('MULTIPLE_SCATTERING' = physically based, use this), `sun_disc`, `sun_size`, `sun_intensity`,
`sun_elevation`, `sun_rotation` (**verified: rotation 0 puts the sun toward world +Y and increases clockwise, so `sun_rotation = radians(azimuth - 90)` in our frame**; always build skies with `light_calibrate.make_sky_world`), `altitude`, `air_density`,
`aerosol_density`, `ozone_density`. No `sun_azimuth` attribute. The node outputs physically scaled radiance; expect to use a strongly
negative exposure (around -6 to -9 EV) or scale the Background strength.

## Sun light
`bpy.data.lights.new(name, 'SUN')`: `energy` (W/m2 irradiance), `angle` (0.0093 rad = 0.53 deg real sun disc), `color`,
`use_temperature`/`temperature`. Aim with `common.aim_sun(obj, azimuth_deg, elevation_deg)` (azimuth clockwise from north = -X).

## Sun position (NOAA) without the UI
```python
from bl_ext.blender_org.sun_position import sun_calc
az_rad, el_rad = sun_calc.get_sun_coordinates(local_time_hours, 37.8029, -122.4484, utc_zone, month, day, year)
# utc_zone is the value ADDED to local time to get UTC: PST -> 8, PDT -> 7
```
Table (Palace of Fine Arts, azimuth clockwise from north, elevation):

| date / time | az | el |
|---|---|---|
| 2026-09-20 07:30 PDT | 93 | 6.0 |
| 2026-10-10 08:00 PDT | 105 | 8.2 |
| 2026-10-25 08:15 PDT | 112 | 8.0 |
| **2026-11-08 07:30 PST (chosen)** | **118.1** | **7.8** |
| 2026-11-20 07:45 PST | 123 | 7.8 |
| 2026-06-21 06:30 PDT | 65 | 6.6 |
| 2026-06-21 19:45 PDT (evening alt.) | 294 | 8.1 |
| 2026-10-25 17:30 PDT (evening alt.) | 247 | 8.4 |

## Sapling tree generator headless
Works only when the active object is NOT something else (it reads `bpy.context.object`). Start from an empty file or
deselect everything and make sure `bpy.context.object` is None or a curve. Verified call (0.4 s, makes objects 'tree' (CURVE) and 'leaves' (MESH)):
```python
bpy.ops.wm.read_homefile(use_empty=True)   # or ensure no active object
bpy.ops.curve.tree_add(do_update=True, bevel=True, showLeaves=True, seed=3, levels=3, length=(1.0,0.3,0.6,0.45),
    branches=(0,40,30,10), curveRes=(8,5,3,1), scale=13, scaleV=3, shape='7', baseSize=0.3, ratio=0.015,
    leaves=25, leafShape='hex', leafScale=0.17, leafScaleX=0.5, bevelRes=2, resU=4, makeMesh=False, ...)
```
Full parameter list: run once with defaults and print `bpy.ops.curve.tree_add.get_rna_type().properties`. Rename the two
objects immediately (they are always called 'tree' and 'leaves'). Convert the curve to mesh for instancing
(`bpy.ops.object.convert(target='MESH')` with a context override, or `obj.to_mesh()` via the depsgraph).

## Cloth simulation headless (for draped figures)
Verified: add CLOTH modifier, set `point_cache.frame_start/end`, then step `scene.frame_set(f)` for each frame, then read the
evaluated mesh: `ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()); me = bpy.data.meshes.new_from_object(ev)`.
1089-vertex sheet, 60 frames: 4.4 s. In the smoke test the sheet fell through a sphere carrying a COLLISION modifier, so
verify collision settings (collision object `collision.thickness_outer`, cloth `collision_settings.distance_min`,
`quality`) before relying on it; a pinned vertex group (`vertex_group_mass`) is the robust way to hang cloth over a body.

## Baking (normal/AO from hi to mid LOD)
`bpy.ops.object.bake(type='NORMAL', use_selected_to_active=True, cage_extrusion=0.05)` needs: Cycles engine, both objects
selected with the low-poly active (use `bpy.context.view_layer.objects.active` and `obj.select_set(True)`), an image node
selected in the low-poly material, and works in background mode. Save images with `image.save_render(path)` or `image.filepath_raw` + `image.save()`.

## Extensions
Installed: `bl_ext.blender_org.sun_position`, `bl_ext.blender_org.sapling_tree_gen`. More via `common.ensure_extension('modular_tree')`
etc. (`bagapie`, `ivygen`, `scatter_objects`, `space_colonization_tree_generator` exist on extensions.blender.org).

## Linking between files
`common.link_collection(path, 'ARCH')` links; `link=False` appends. Keep every asset in ONE top-level collection named for
the owner (ARCH/ORN/ENV/LIGHT) with sub-collections allowed. Materials are appended by name through `common.load_material`.
Image texture paths must be relative (`//textures/...`) and the files committed under `assets/textures/`.

## Comparison sheets
`python3 scripts/qa_compare.py --render r.png --ref p.jpg --out renders/qa_comparisons/x.png` (render | reference | 50% blend)
and `--sheet out.png a.png b.png ...` for grids. This ffmpeg build has no drawtext filter; label via filenames.

## Lighting rig numbers (lighting agent, verified 2026-09-07)
Morning 2026-11-10 07:30 PST: az 118.49, el 7.36. `LIGHT_sun` energy 71.83 W/m2, colour (1.0, 0.616, 0.269), angle 0.0093;
world sky MULTIPLE_SCATTERING (aerosol 1.0, ozone 2.0, altitude 5 m, disc OFF) strength 2.0 with a camera/glossy-ray boost 1.6;
exposure -3.90 EV (18% card facing the sun = middle grey at -4.40, +0.5 bias), look 'AgX - Base Contrast'; compositor
`COMP_golden_hour` (mist haze 3% at 120 m, bloom, 2-3% vignette). Apply to any scene with `light_presets.apply_look(scene)`.
Cycles 768 spp 1280x720 = 65 s on the placeholder -> 4K estimate ~10 min; real scene expected 5-10x heavier.

## Opening and rendering master.blend (lighting, 2026-09-09; Phase 5 delivery)

### What is in the saved file
`master.blend` is saved **in the Eevee viewport state**, which is what makes it navigable, and everything below is
already set — no script needs to run to fly around in it.

| saved setting | value | why |
|---|---|---|
| engine | `BLENDER_EEVEE` (Eevee Next) | opens navigable; a bare F12 from the UI is a correct Eevee frame |
| Eevee TAA | 8 viewport / 16 render (`apply_viewport_eevee`) | the QA preview preset is 32; 8/16 is for flying |
| shadows | on, ray count 1, step 2, resolution scale 0.5, `shadow_pool_size` 512 | |
| raytracing / fast GI | **off** | measured (QA-04-12, notes 20.8): raytracing moves the vault coffer 0.218 -> 0.218 |
| `light_threshold` | **0.01** (not the 0.05 default) | 0.05 culls the eight vault emitters, which is exactly the dome |
| `gi_irradiance_pool_size` | 64 MB | the default 16 cannot hold the two baked LIGHTPROBE volumes (QA-01-9) |
| light probes | 2 baked irradiance volumes, baked on the PHYSICAL rig | `light_probes.bake(physical_vault=True)` in `lead_build.sh` |
| view transform / look | AgX, `AgX - High Contrast`, exposure **-2.833 EV** | notes 19 (round 10) |
| compositor | `COMP_scene_golden_hour` (mist airlight cap 0.25 / k 5.0, bloom, vignette) | notes 22.4 |
| world | `WORLD_golden_hour`, sky MULTIPLE_SCATTERING, az 118.49 / el 7.36 | |
| measured (QA round 05) | open **0.72 s** headless, 9175 objects, LOD1 **11.01 M tris**, 154.6 MB | budget was 60 s |

### The two Eevee-only rigs — read this before rendering Cycles
Two rigs in `LIGHT` exist **only** to make Eevee agree with Cycles, and they must be switched off for any Cycles frame:

- **the vault override** — the eight interior emitters at `energy_scale 6.0`, `cutoff_distance 21.0`
  (`light_presets.EEVEE_VAULT`). Eevee's probe volumes cannot carry the rotunda vault's bounce; Cycles path-traces it.
- **`LIGHT_shade_fill`** — three wide-angle anti-sun lamps, **55 / 55 / 38.5 W/m2 in Eevee, 0.0 W/m2 in Cycles**
  (and `hide_render` there). The round-12 shade fix is three diffuse-only world sockets, and Eevee's shaded stone is
  lit by its screen-traced horizon scan rather than by the world, so those sockets never reach it (notes 22.1-22.2).

Both are engine-conditional, both are idempotent, and both read their energies from the objects' own custom
properties (`energy_W`, `energy_W_eevee`). **Every** Cycles path must call the switch:

```python
import light_presets as lp, common
lp.apply_final_cycles(scene)                 # 4K hero / flythrough finals: also sets samples, denoiser, film
common.configure_cycles(scene, samples=128)  # measurement renders: calls the same two switches since r13
```
`common.configure_cycles` applies `apply_vault_for_engine("CYCLES")` / `apply_shade_for_engine("CYCLES")` itself, so
`common.render_previews(engine="CYCLES")` and the other agents' Cycles scripts are safe. What is **not** safe is
setting `scene.render.engine = "CYCLES"` by hand (in a script or in the UI) and pressing F12: that renders three
55 W/m2 blue suns and a 6x vault into the frame.

### Cycles sample counts and the measured wall times (M2 10-core Metal, GPU, OIDN)

| what | settings | measured |
|---|---|---|
| hero cam01 1920x1080 | 128 spp adaptive (thr 0.01, min 64), uncapped | **335.4 s** (QA r04), **355.8 s** (QA r05) |
| cam04 1280x720 | 64 spp adaptive | **210.9 s** (r04), **219.1 s** (r05) |
| hero 3840x2160 | 16 spp, compositor on / off | **175.3 s / 177.1 s** (QA r04) — the compositor is not the cost |
| hero 3840x2160 | 768 spp adaptive (the saved `FINAL_SAMPLES`) | **no frame in 90+ min in three attempts**; killed at 95.1 min |
| Eevee QA previews 1280x720 | 32 TAA, `apply_preview_eevee` | 12.7-23.6 s per camera, 120.6 s for all six (r05) |

The 4K final is therefore **not** to be attempted at 768 spp first. QA's recommendation, which lighting agrees with:
render 4K at **128 spp fixed with adaptive OFF and `time_limit = 0`**, under an outer wall-clock guard
(`scripts/blender_run.sh 7200 -- ...`), to get the first finished 4K frame and its wall time, then choose the final
sample count from that number. Scaling 1080p 128 spp (355.8 s) by the 4x pixel count puts it near 24 min plus the
OIDN pass on a 4K buffer.

### The flythrough camera and the low-res test animation
`scripts/light_flythrough.py` builds `CAM_flythrough` (24 mm), `CAM_flythrough_path` and `CAM_flythrough_target`
in `assets/lighting.blend`. Route, validated by ray-cast in `scripts/light_flythrough_check.py` (notes 23):
cam01 hero hold 3.50 s -> lagoon crossing at up to 9.2 m/s -> the cam02 SSE station -> a radial entry through one
4.5 m colonnade bay -> the gallery centreline at eye height over the walk -> out at the wing's rotunda end -> in
through the az-217 arch -> under the dome, ceiling look-up held 4.17 s. **250.1 m, 1224 frames at 24 fps = 51.0 s.**
`cam["schedule"]` carries the leg and hold frame ranges as JSON; `light_flythrough.load_schedule()` reads it back.

```sh
# rebuild the path (writes assets/lighting.blend only)
scripts/blender_run.sh  600 -- --background --python scripts/light_flythrough.py
# re-validate it against ARCH + ENV without rendering (exit 0 only if all four gates pass)
scripts/blender_run.sh 2400 -- --background --python scripts/light_flythrough_check.py --
```

To render the test animation from `master.blend`, set the scene camera and frame range from the schedule, apply the
Eevee preset, and render 640x360:

```python
import light_flythrough as ft, light_presets as lp
sch = ft.load_schedule()
scene.camera = bpy.data.objects["CAM_flythrough"]
scene.frame_start, scene.frame_end = 1, sch["frames"]      # 1..1224
scene.render.fps = sch["fps"]                              # 24
scene.frame_step = 1                                       # 2 halves the cost; render at fps 12 to keep the timing
lp.apply_preview_eevee(scene, samples=16)                  # or apply_viewport_eevee(scene) for the cheapest pass
scene.render.resolution_x, scene.render.resolution_y = 640, 360
scene.render.image_settings.file_format = "PNG"            # frames, then ffmpeg; not Blender's encoder
scene.render.filepath = "renders/previews/lighting/flythrough/f_"
bpy.ops.render.render(animation=True)
```
Cost estimate, **scaled from the measured 1280x720 numbers, not measured**: 640x360 is a quarter of the pixels of
the QA preview, so 3-6 s per frame -> **60-100 min for all 1224 frames**, or 30-50 min at `frame_step = 2` with the
output at 12 fps. Give `blender_run.sh` an honest max (7200). Then:
`ffmpeg -framerate 24 -i renders/previews/lighting/flythrough/f_%04d.png -c:v libx264 -crf 18 -pix_fmt yuv420p out.mp4`.

## Opening and rendering (Phase 5)

Everything above is still true; this is the delivery wrapper around it (`docs/phase5_checklist.md`).

**Opening:** `master.blend` opens straight into the saved Eevee viewport preset (LOD1, `light_threshold` 0.01,
raytracing off, measured 0.72 s) -- see "What is in the saved file" above. No script needs to run just to fly around.

**Rendering the hero:** `scripts/phase5_hero.py` opens `master.blend`, calls `light_presets.apply_final_cycles`
(the same preset every Cycles final has used -- denoiser, light tree, the vault-override / shade-fill switches),
rebuilds the QA camera stations in memory (`qa_cameras.ensure`, never trusts a stale station in the file) and sets
`CAM_qa_01_lagoon_hero`. Nothing is saved back to the file.

```sh
scripts/blender_run.sh 7200 -- --background --python scripts/phase5_hero.py -- \
    --spp 128 --res 3840 2160 --adaptive off --time-limit 0        # timing probe first (checklist step 4)
scripts/blender_run.sh 7200 -- --background --python scripts/phase5_hero.py -- \
    --spp 768 --res 3840 2160 --adaptive off --denoise on          # final, once the probe's wall time allows it
```
Writes `renders/final/hero_cam01_<W>x<H>_<spp>spp.png` and prints `wall_time_s=` / `peak_rss_mb=`.

**Rendering the flythrough test:** `scripts/phase5_flythrough.py` opens `master.blend`, sets `CAM_flythrough`, reads
the frame count/fps from `light_flythrough.load_schedule()` (1224 @ 24, sec 23), applies `apply_preview_eevee`
(16 TAA) and renders 640x360 frames to `renders/anim/flythrough_test/frame_####.png` (directory cleared first).

**Cleaning the delivery file (step 1b):** `scripts/phase5_deliver.sh 1b` copies `master.blend` to
`master_delivery.blend` and runs `scripts/phase5_cleanup.py` on the **copy** -- master.blend is never modified by the
driver (the script itself refuses to write a file named `master.blend` without `--allow-master`). It purges local
orphans recursively (linked ids are reported, never purged or edited), re-applies `common.set_lod(viewport=1,
render=0)` and `light_presets.apply_viewport_eevee`, hashes every camera matrix+lens before/after so a station can
never move, writes `renders/logs/phase5_cleanup.json` (data-blocks per type, libraries, images external vs packed,
file size, LOD counts) and times an in-process re-open, failing the run if it is not under 60 s. Measured on the
round-7 master: 12 616 data-blocks, **0 orphans to purge**, 9 681 objects, 160.9 MB, **re-open 0.78 s**, 7 camera
stations unchanged. `--pack` (or `PFA_PACK=1` on the driver) packs the 87 external images (116.0 MB -> a 277 MB
file); it is off by default because the texture library ships in the repo, and the script refuses to pack past 1.5 GB.
In an `all` run steps 2-6 then render the cleaned copy; run alone they default to `master.blend`, and
`PFA_DELIVERY_BLEND=master_delivery.blend` (or `--blend` on the scripts themselves) points them at it.

**Driving both, plus the ffmpeg encode:** `scripts/phase5_deliver.sh [1b|2|3|4|5|6|all]` runs checklist steps 1b-6 in
order through `blender_run.sh`, one Blender at a time, stopping at the first failure; step 5 auto-picks the final
sample count/resolution from step 4's logged wall time (override with `--final-spp N --res W H`); step 6 encodes
`renders/anim/flythrough_test/` to `renders/final/flythrough_test_640.mp4` at `fps / frame_step`. Each step is
independently runnable (`scripts/phase5_deliver.sh 4`) and logs to `renders/logs/phase5_<step>.log`.

**LOD convention (unchanged, applies to every render above):** `_LOD0` hi / `_LOD1` mid (viewport + Eevee QA default)
/ `_LOD2` low, via `common.set_lod(viewport, render)`; the 4K/flythrough Cycles finals render at LOD0
(`set_lod(viewport=1, render=0)`, the default `render_previews`/`qa_render_round.py --final` already leave in place).

## Phase 6 — web export and bake pipeline (lead, 2026-09-15, from the Gate 0 bake engineer's measurements; full detail in export/README.md)

**Blender 5.2 findings the pipeline depends on (all measured, not assumed):**
- `Image.save_render()` applies NO colour management: 0.18 and 0.02526 came back as 0.180 / 0.02525 with the scene at AgX High Contrast
  -2.833 EV. Anything that must pass through the view transform is rendered through the compositor instead (an Image node into a
  `NodeGroupOutput` on `scene.compositing_node_group`, render size = the lattice, one sample). That is how the 65^3 AgX LUT is baked.
- `scene.use_nodes = False` does NOT disable the compositor in 5.2 (deprecated property); only `scene.compositing_node_group = None`
  does. Measured on a 0.18 emission plane: 0.075029 with `COMP_scene_golden_hour` attached, 0.082078 without (7.5 % linear).
  In 5.2 the compositor lives on `scene.compositing_node_group` and ends in `NodeGroupOutput`, not on `scene.node_tree`.
- `master_delivery.blend` is saved at LOD1 in the viewport, so every `_LOD0` object is `hide_viewport=True`, absent from the depsgraph:
  `matrix_world` reads identity and `scene.ray_cast` misses it. Un-hide, `view_layer.update()`, then read transforms.
- gltfpack 1.2: `-mi` (EXT_mesh_gpu_instancing) and `-kn` (keep node names) are mutually exclusive. The lead chose `-cc -mi`.

**Colour contract (viewer, tone mapping off):** `graded = LUT3D(clamp((log2(max(linear * 2^-2.8331, 1e-10) / 0.18) - (-12.47393))
/ (4.026069 - (-12.47393)), 0, 1))`, LUT 65^3 (a 33^3 lattice left 1.7/255 on mid grey), proven on five Cycles grey patches at worst
0.072/255. The exposure is applied by the viewer before the shaper and the LUT was baked at that exposure: applying it twice or not at
all is wrong in both directions.

**Lightmap contract:** Cycles Diffuse direct+indirect, colour OFF = irradiance/pi; three.js' lightMap path multiplies by
BRDF_Lambert = albedo/pi, so `lightMapIntensity = manifest.lightmap_scale = pi`. The map rides in the glTF `emissiveTexture` on
TEXCOORD_1 as RGBM8 (range 64, PNG at Gate 0): set `colorSpace = NoColorSpace` FIRST (glTF declares emissive as sRGB), move it to
`lightMap` channel 1, zero the emissive, decode `rgb = texel.rgb * texel.a * range`. The sun DirectionalLight is specular-only
(its diffuse is in the map). Gate 0 wall times, 2K, 128 spp + OIDN, M2: column 306 s, capital 221 s, 12-tri ground 300 s once its
own hi twin was hidden from the rays (461 s before). Any coincident hi-poly twin must be excluded from the bake rays.

**Sky:** two 4096x2048 equirects (camera branch = background, glossy branch = PMREM) with the Light Path links cut in memory and the
branch constants written into the inputs; `u_img = 0.5 + atan2(x_B, y_B)/360`, top row = zenith. After the exporter's Y-up swap
the viewer applies +90 deg about three.js Y (`sky.rotation_deg` in the manifest = `equirectUv(d).u + 0.25`), sun azimuth check 0.026 deg.

**Headless Chrome:** a raw `--headless=new --screenshot` on Chrome 152 lingers 60-90 s per frame; `web/tools/screenshot.mjs`
(puppeteer-core, waits for `window.__pfaReady`, closes in `finally`) through `scripts/chrome_run.sh` returns in seconds and leaves
no process. Never overlap Chrome with a bake: check `export/out/bake_queue/status.json` in a SEPARATE command before launching.
- (QA 11c, export a9b2d3d) In `master_delivery.blend` only the `_LOD1` ENV objects carry a placement; every `_LOD0` and `_LOD2` sibling sits at the
  origin as an unplaced stub (1379/1379 shrubs measured). Any export or bake that selects a LOD0/LOD2 ENV *object* must take the transform from
  its LOD1 sibling (`placement_from` in export_set.json). The glTF writer now asserts 0 objects within 1 m of the origin per class and
  `export/verify_glb.py` checks drawn triangles vs export_set within 1 %.
- (Gate 2) `Image.save()` on an image made with `images.new(float_buffer=True)` and filled by `foreach_set` wrote correctly sized all-zero PNGs
  (15 detail maps, every byte 0). Write bake outputs from numpy with your own PNG writer and read every saved map back from disk before claiming a
  number; in-memory statistics are not evidence (export/bake_lib.write_png_rgb8 / read_png_rgb8).
