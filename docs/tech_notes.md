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
