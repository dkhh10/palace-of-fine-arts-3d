# Lighting & Rendering notes (Phase 2)

Lighting & Rendering specialist, 2026-09-07. Everything here is produced by `scripts/light_*.py` headless in
Blender 5.2.1; every number below is either measured by `scripts/light_calibrate.py` (tiny Cycles renders read back as
32-bit EXR) or printed by the build. Re-running `light_build.py` regenerates all of it.

Deliverables: `assets/lighting.blend` (collection `LIGHT`: `LIGHT_sun`, `CAM_flythrough_path`, `CAM_flythrough_target`,
`CAM_flythrough`; world `WORLD_golden_hour`; compositor node group `COMP_golden_hour`), `scripts/light_build.py`,
`scripts/light_calibrate.py`, `scripts/light_presets.py`, `scripts/light_flythrough.py`, `scripts/light_preview.py`.

## 1. The moment (single parameter)

`light_build.MOMENTS` holds the date/time; `--moment evening` switches everything (sun aim, sky, lamp colour/energy,
exposure) in one go. Solar position from the Sun Position extension's NOAA code
(`sun_calc.get_sun_coordinates(local_hours, 37.8029, -122.4484, utc_zone, month, day, year)`, utc_zone = 8 for PST, 7 for PDT):

| moment | local time | azimuth (cw from N) | elevation | lamp energy (sky units) | lamp colour (max = 1) | exposure (card) | exposure used |
|---|---|---|---|---|---|---|---|
| **morning (chosen)** | 2026-11-10 07:30 PST | **118.49°** | **7.36°** | **71.83** | **(1.000, 0.616, 0.269)** | −4.40 EV | **−3.90 EV** |
| evening (alternate) | 2026-10-20 17:45 PDT | 250.86° | 6.94° | 68.78 | (1.000, 0.603, 0.251) | −4.32 EV | −3.82 EV |

(Both rows use the final sky; the evening row is recomputed automatically by `--moment evening`.) The moment's
values are stored as custom properties on `LIGHT_sun`
(`date`, `time_local`, `utc_offset_h`, `latitude`, `longitude`, `azimuth_deg`, `elevation_deg`, `lamp_energy_W_m2`,
`lamp_color`, `exposure_ev`, …) and on the world (`sky_*`, `sun_azimuth_deg`, `sky_sun_rotation_deg`).

## 2. Sky-rotation convention (verified empirically)

`scripts/light_calibrate.py -- --convention` renders an equirectangular panorama of the sky with the disc ON and
compares the disc's centroid with emissive markers placed at true north (−X), east (+Y) and the zenith
(`renders/previews/lighting/calibration/convention_check.json`).

- Markers: north at column 360.0, east at 720.0 (of 1440 → azimuth increases to the right, 0.25°/px), zenith at row 718.5.
- With the naive `sun_rotation = radians(azimuth)` the disc landed at **208.1°** for a requested 118.5° (Δ = +89.6°).
- Therefore the node's `sun_rotation = 0` puts the sun at **world +Y** and increases **clockwise seen from above**
  (Blender treats +Y as its north). Our +Y is east, so **`sun_rotation = azimuth − 90°`**
  (`light_calibrate.sky_rotation_for_azimuth`). After the fix the disc centroid reads **118.47° / 7.46°** for
  118.5° / 7.4° requested (Δ −0.03°, +0.06°).
- Visual check: `renders/previews/lighting/calibration/convention_pole_shadow_and_disc.png` — a 12 m pole, the lamp
  aimed with `common.aim_sun(118.5, 7.4)` and the sky's (enlarged, dimmed) disc ON: the disc glow sits over the pole
  and the pole's shadow runs away from it.
- **Consequence for others:** the lead's `lead_placeholder_blockout.py` used `sun_rotation = 0` (sun at +Y = east,
  az 90°) — harmless there, but anyone building a sky must use `light_calibrate.make_sky_world` or the −90° rule.

## 3. Radiometric calibration (why the numbers are what they are)

All in "sky units" (the MULTIPLE_SCATTERING node's native output; it is physically scaled, hence the −4 EV exposure).

1. **Cycles Sun lamp convention** — a white Lambertian card facing a Sun of energy 1 renders **0.31831 = 1/π**
   (so energy E W/m² ⇒ radiance E/π). Uniform environment of radiance L ⇒ white card L. Both verified.
2. **Sun-disc integration** (final sky: aerosol 1.0, ozone 2.0, altitude 5 m, sun_size 0.533°, disc ON vs OFF on a
   card facing the sun): **E_sun = (71.83, 44.28, 19.30)**, luminance 48.3. ⇒ `LIGHT_sun.energy = 71.83`,
   `color = (1.0, 0.616, 0.269)`, `angle = 0.0093 rad` (0.533°, same as the sky's `sun_size`). The world's disc is OFF;
   the lamp is the disc. (With ozone 1.0 the same integral gave 91.1 / (1, 0.597, 0.206): ozone's Chappuis band
   removes green/yellow at this air mass.)
3. **Sky irradiances (disc OFF, strength 1):** on the sun-facing card (8.96, 8.99, 9.83); on a horizontal card
   (3.08, 5.21, 9.56) — total horizontal with the sun (12.28, 10.88, 12.03). Radiances: zenith (0.34, 0.73, 1.70),
   30° up looking south (0.83, 1.63, 3.31), west horizon (3.53, 4.23, 4.50), horizon toward the sun (53.3, 38.1, 21.1).
4. **Sun : sky ratio.** The model's direct-normal / diffuse-horizontal luminance ratio at 7.4° elevation is
   48.3 / 6.2 ≈ **7.8 (9.9 with ozone 1)**; clear-sky measurements at this elevation sit around 5, and refs 054/169 show
   shade ≈ 3 stops under sunlit, not 4+. **`SKY_STRENGTH = 2.0`** (world Background strength for lighting) closes that
   gap; the A/B sheet `renders/previews/lighting/sheet_r02_skystrength_1.0_1.7_2.5_punchy1.7.png` shows 1.0 (shade
   too dark), 1.7, 2.5 (contrast flattened) and Punchy.
5. **Visible-sky boost.** Even at ×2 the rendered sky was ~1 stop darker than ref 169 relative to the sunlit stone
   (photo sky top 145/194/239 sRGB, horizon 217/246/254; render 109/138/163, 143/164/181). A Light Path node in the
   world multiplies the background by **`SKY_CAMERA_BOOST = 1.6` for camera and glossy rays only**, so the sky and its
   reflection in the lagoon brighten without lifting the shade further. Final hero samples: sky top **137/164/193**,
   horizon **166/187/206**, sunlit attic 206/180/156 (photo 236/195/106 — the difference is the placeholder's flat,
   unsaturated albedo, a materials matter).
6. **Sky colour.** Aerosol density hardly changes the sky the hero camera sees (looking west, away from the sun:
   top pixel 126/152/176 for aerosol 0.3 … 2.0) but warms the sun-side horizon; kept at **1.0** (the sweep sheet
   `sheet_r01_skysweep_aerosol_0.5_1_2_3.png` shows 2–3 going grey). **Ozone 2.0** deepens the blue at low sun
   (B/R 1.59 vs the photo's 1.65; ozone 1.0 gave 1.39; 3.0 gave 1.82 but too dark).
7. **Exposure.** 18 % grey card facing the sun under lamp + sky (disc OFF, strength 2): scene-linear
   (5.14, 3.57, 2.23), luminance 3.80 ⇒ **exposure = log2(0.18 / 3.80) = −4.40 EV**; through AgX Base Contrast the
   card displays as sRGB (0.526, 0.440, 0.353) — a warm middle grey. **`EXPOSURE_BIAS = +0.5 EV`** on top (−3.90 EV
   used): ref 169's sunlit stone sits about half a stop above a sun-facing card, and the bias keeps the sky-lit
   shade readable. Re-check on the real materials: the target for the sunlit attic is ≈ 236/195/106 sRGB.
8. **Look: `AgX - Base Contrast`.** Punchy (same exposure) gives the photo's saturation (sky 77/108/135, stone
   193/158/118) but darkens the shade about 0.4 stop and starts crushing the arch soffits — against the brief's
   "no crushed blacks". Base Contrast keeps the gradient; its cost is highlight desaturation (the sky's B/R drops
   from 1.59 to 1.41 as it brightens). Switch = `LOOK` in `light_build.py` / `light_presets.py`; A/B panel in sheet r02.
9. **No fill light.** With the ×2 sky and Cycles bounces (`diffuse_bounces 3`) the shade is sky-blue-grey lifted by
   warm bounce; a fill lamp would fight the physically-derived ratio. Revisit only if the QA round on real materials
   shows the north faces reading black.

## 4. Atmosphere: `COMP_golden_hour`

Node group (inputs: Image, Mist, Depth, Haze Color, Haze Strength, Bloom Threshold, Bloom Strength, Bloom Size,
Vignette; output: Image). Wired by `light_presets.build_scene_compositor(scene, group)` into a LOCAL scene tree
(`COMP_scene_golden_hour`: Render Layers → group → Group Output) — a scene tree must be local because a linked one
carries a Render Layers node bound to lighting.blend's own scene and Blender then refuses to render ("no camera").

- **Haze** = mix toward `Haze Color` by `Mist × Haze Strength × is_geometry` (depth < 4000 m; the sky keeps the sky
  model's own aerial perspective). World mist: start 40 m, depth 1500 m, linear. Haze colour = measured west-horizon
  radiance × (1.06, 1.0, 0.88) = **(3.74, 4.23, 3.96)** scene units (pale, faintly warm); strength **0.55** ⇒ 3 % at
  120 m, 6 % at 200 m, 17 % at 500 m. Deliberately subtle: ref 169's colonnades at ~150 m are only faintly veiled.
- **Bloom** (Glare node, type Bloom, quality High): threshold = 0.9 / 2^exposure = **13.5 scene units** (only
  near-white pixels: sun-side horizon glow, water glints), strength 0.05, size 0.6, smoothness 0.2.
- **Vignette** = Ellipse mask (size 1.0) → Gaussian blur 200 px → `1 − 0.08·(1 − mask)`; measured 2–3 % darker in the
  extreme corners (0.975 / 0.983 of the uncomposited value), zero at the edge midpoints — well under the 0.1 cap.
- Verified active: hero with compositing OFF vs ON differs by 0.9/255 mean (subtle by design); with the inputs
  exaggerated (haze 1.0, bloom 0.5, vignette 0.1) by 10/255.
- **No world volume.** The compositor haze costs nothing measurable; a volume would add ≥ 30 % to Cycles at 4K for a
  site that is < 300 m deep. Mist pass + depth pass are enabled on the view layer by `apply_look`.

## 5. Render presets (`scripts/light_presets.py`) and timings

Timing test (`light_presets.py -- --time`, placeholder blockout, hero camera, 1280×720, M2 10-core Metal;
`renders/previews/lighting/timing/timing.json`):

| preset | samples | 1280×720 | extrapolated 3840×2160 (×9 pixels) |
|---|---|---|---|
| `apply_viewport_eevee` | 16 TAA | 0.47 s | — |
| `apply_preview_eevee` | 32 TAA, raytracing, fast GI | 1.51 s (1.24 s warm) | — |
| `apply_final_cycles` | 256, adaptive 0.01 | 28.4 s | 4.3 min |
| `apply_final_cycles` | **768**, adaptive 0.01 | 65.2 s | **9.8 min** |

The placeholder is trivial (flat materials, no trees); a textured scene with leaf cards and displaced ornament costs
5–15× more per sample, which still lands a 4K hero at 768 spp inside the 2 h budget (9.8 min × 12 ≈ 2 h). Final
settings: OIDN GPU denoise (albedo+normal, accurate prefilter, high quality), adaptive sampling threshold 0.01 / min 64,
light tree, bounces 8 (diffuse 3, glossy 4, transmission 4, transparent 16), filter glossy 0.5, clamp indirect 10,
no caustics, persistent data, 16-bit PNG. `FINAL_TIME_LIMIT_S` (0) is the hard stop the lead can set per frame
(6600 s keeps any frame under the budget). **Before the 4K hero, rerun `--time` on master.blend and scale
`FINAL_SAMPLES` from the measured 1280×720 time × 9.**

Preview Eevee: 32 TAA, screen-space raytracing (½ res, denoised) for the lagoon reflections, fast GI (2 rays, 60 m),
shadow rays 2 / steps 4, overscan 3 %. Viewport Eevee: shadows on (1 ray / 2 steps, ½ res), raytracing/fast GI/volumetric
shadows off. QA set at 1280×720 renders in 1.3–3.6 s per camera after shader compile.

`apply_look(scene)` = AgX + look + exposure read from `LIGHT_sun["exposure_ev"]` + mist/depth passes + compositor.
`apply_rig(scene)` = link `LIGHT` + `WORLD_golden_hour` from `assets/lighting.blend`, then `apply_look`.

## 6. Flythrough (`scripts/light_flythrough.py`)

`CAM_flythrough_path` (bezier, 13 auto-handle control points, 278.1 m), `CAM_flythrough_target` (keyframed empty),
`CAM_flythrough` (24 mm, Follow Path fixed-position with keyframed `offset_factor`, Track To the target; all keys
Bezier / ease-in-out / auto-clamped). 720 frames @ 24 fps = 30 s, mean 9.3 m/s. Offset keys are arc-length fractions
(the evaluated curve is sampled, so the Follow Path parameter is uniform in distance).

| frame | t (s) | waypoint | arc | position (X, Y, z) | look-at |
|---|---|---|---|---|---|
| 1–37 | 0.0–1.5 | hero_start (hold) | 0.000 | (−16.0, 113.9, 1.0) = CAM_qa_01 | rotunda (0, 0, 17) |
| 200 | 8.3 | shore_se | 0.270 | (58.0, 112.0, 3.0) | rotunda (0, 0, 15) |
| 280 | 11.6 | (crossing the water) | — | — | colonnade end pylons (72, 40, 12) |
| 330 | 13.7 | colonnade_end | 0.506 | (79.0, 54.0, 6.0) | down the gallery (74, 22, 9) |
| 580 | 24.1 | colonnade_out | 0.839 | (37.0, −22.5, 5.5) | rotunda (12, −8, 12) |
| 700 | 29.1 | rotunda_centre | 1.000 | (0.0, 1.0, 2.5) | dome (0, 0, 30) |
| 720 | 30.0 | rotunda_centre (hold) | 1.000 | (0.0, 1.0, 2.5) | dome apex (0, 1, 46) |

Segment speeds: shore 11.1 m/s, water crossing 12.1 m/s, colonnade 8.9 m/s, rotunda approach 9.0 m/s (eased to a stop).
Test frames: `renders/previews/lighting/flythrough_test_{0001,0145,0289,0432,0576,0720}.png` (640×360 Eevee) and
`sheet_flythrough_test.png`. Frames 432 and 576 are grey because the placeholder colonnade is a solid extruded
footprint — the camera is inside it, on the real gallery axis; frame 720 looks up into the placeholder dome.
Waypoints live in `WAYPOINTS`; the gallery axis was taken from the OSM roof polygon (`roof306`), so once ARCH exists
the column positions may need the entry point (`colonnade_in`) nudged.

## 7. Previews and comparisons

- `renders/previews/lighting/*_r06.png`: six QA cameras (Eevee preview preset) + Cycles 128 spp hero, placeholder
  blockout + this rig. `sheet_r06_eevee_qa_cams.png`, `sheet_r06_morning_vs_evening_cycles.png`.
- `renders/qa_comparisons/lighting_r0{1,3,4,5,6}_hero_cycles_vs_ref169.png`: render | ref 169 | 50 % blend for each round.
- `renders/previews/lighting/*_cycles_evening2.png`: the evening alternate (`light_preview.py -- --moment evening`,
  rig rebuilt in memory so the asset is untouched): rotunda backlit from the WSW, glow left of the dome (ref 035 mood).
- Checklist against ref 169 (round 6, placeholder geometry): low warm sun ✔ (east/south-east faces peach, north faces
  sky-lit blue-grey, not black); long soft-edged shadows ✔ (0.533° disc; the lead's pier shadows stretch across the
  platform); sky-lit shade ✔; warm haze on distant elements — present but subtle (see §4, tune `Haze Strength`);
  water reflecting a bright warm sky ✔ in the placeholder mirror (real water = ENV/materials); no crushed blacks ✔
  (darkest shade in the hero ≈ 60/255); no blown highlights ✔ (brightest stone ≈ 210/255, sky horizon 206/255).

## 8. Open issues and requests

1. **Lead / `build_master.py`:** after linking, call `light_presets.apply_look(scene)` (or `apply_rig`) — master
   currently links `LIGHT` + the world but leaves exposure at 0 EV and no compositor, which renders ~4 stops over.
2. **Materials:** albedo/saturation of the sunlit stone is the biggest remaining gap to ref 169 (206/180/156 vs
   236/195/106); the rig is calibrated to a physical 18 % card, so please do not compensate by brightening albedos —
   re-check `EXPOSURE_BIAS` with me once `MAT_concrete_ochre` exists.
3. **ENV/water:** the sky boost applies to glossy rays, so the lagoon reflection will read as bright as the sky
   (ref 169 shows it ~0.8 stop darker: murk + Fresnel). If the water material is not dark enough, lower
   `SKY_CAMERA_BOOST` or make the boost camera-only (drop the `Is Glossy Ray` add in `make_sky_world`).
4. **QA:** A/B `AgX - Punchy` on the real materials (one line in `light_presets.LOOK`); it may win once textures carry
   the saturation.
5. **Flythrough:** re-check `colonnade_in`/`colonnade_out` against ARCH's column positions; 24 mm may need 28 mm
   inside the gallery.
6. The placeholder's own `PLACEHOLDER_LIGHT` collection (sun + world) is excluded in my previews; master must not
   link it once `LIGHT` exists.

---

# Phase 3 fix round (round 07, 2026-09-07) — QA-01-9, QA-01-12, QA-01-20

Measured with `scripts/light_measure.py` (plain python3 + numpy/PIL; fractional region rectangles so the same region
set applies to a render and to a photo). Every number below is an sRGB mean of a named rectangle plus its linear
luminance Y (sRGB primaries). The region sets live in `light_measure.REGIONS` (`hero`, `hero_ref169`, `ceiling`,
`aerial`, `dome_hero`, `dome_hero_ref169`) so any later round re-measures exactly the same patches.

Baseline for the round: `master.blend` rebuilt in the lighting worktree from main at `e84b67e` (materials library v1 +
the raised dome), Eevee `apply_preview_eevee` 32 TAA and Cycles `apply_final_cycles` 48 spp, both 1280x720.

## 9. QA-01-9 — the rotunda ceiling: what is actually wrong

The defect said "4x too dark in Eevee, no light probes". Both halves needed measuring before fixing.

**There were no probes** (`master.blend` contained zero `LIGHT_PROBE` objects), so Eevee Next was lighting the vault
with nothing but its screen-space *Fast GI* approximation. Measurements on cam04 (coffer field = the central 20 % x 20 %
of the frame, the same patch in the render and in ref 083):

| configuration | coffer field sRGB | Y |
|---|---|---|
| Eevee, no probe, fast GI on (the QA-01-9 baseline) | 24.5, 22.1, 14.3 | 0.0081 |
| Eevee, no probe, fast GI **off** | 0.1, 0.1, 0.1 | 0.00003 |
| Eevee, baked irradiance volume | 5.2, 2.1, 0.4 | 0.0008 |
| **Cycles 48 spp, 3 diffuse bounces (ground truth)** | **11.9, 6.3, 2.8** | **0.0022** |
| Cycles 48 spp, 8 diffuse bounces | 12.3, 6.4, 2.9 | 0.0023 |
| Cycles 48 spp, 8 bounces, no indirect clamp | 12.3, 6.4, 2.9 | 0.0023 |
| ref 083 (photo) | 91.7, 76.1, 52.5 | 0.0770 |

Three conclusions, all of which change the fix:

1. **Eevee was not 4x too dark, it was 2x too bright** — its 24/255 was a screen-space guess. Cycles, the ground truth,
   says 12/255. A correct baked volume lands at 5/255, i.e. the probe bake works and is *more* right than fast GI.
   (The bake itself was verified headless on a control scene: an open-sky sphere keeps its world irradiance and gains
   correct occlusion under the probe, so `bpy.ops.object.lightprobe_cache_bake` is not silently failing in background.)
2. **The vault is not bounce-limited.** 3 vs 8 diffuse bounces differ by 0.4/255. Raising `diffuse_bounces` buys nothing
   and costs render time, so `apply_final_cycles` keeps 3 (noted in the code).
3. **The rotunda genuinely receives almost no light in this model.** At 7.4 deg the sun never reaches the interior floor,
   and from a coffer 25 m up the four arches subtend a small solid angle of sky. The interior lands ~7 stops under the
   sunlit attic (12/255 vs 182/255). Ref 083 shows ~3.5 stops — but ref 083 is *exposed for the ceiling* (its sky in the
   arch openings reads 219-254/255, i.e. blown), so it is not a photometric reference for a frame exposed for the
   exterior. The one honest in-frame comparison, ref 169's arch soffits against its own sunlit attic
   (136,92,64 vs 209,165,93, ratio 0.65 sRGB), the render already matches (94,70,45 vs 182,137,94, ratio 0.51-0.80).

**The fix, in two parts.**

*Probes.* `scripts/light_probes.py` builds two Eevee Next irradiance volumes inside `LIGHT`, so they travel with the rig:

| probe | centre | half-extent | grid | spacing |
|---|---|---|---|---|
| `LIGHTPROBE_rotunda` | (0, 0, 15) | 27 x 27 x 17 m | 20 x 20 x 14 | 2.8 x 2.8 x 2.6 m |
| `LIGHTPROBE_colonnade` | (-3, 8, 6.5) | 112 x 46 x 8 m | 48 x 20 x 6 | 4.8 x 4.8 x 3.2 m |

`light_build.py` creates them (unbaked) in `assets/lighting.blend`. **A bake is a function of the scene, not of the rig**:
baking inside `lighting.blend` would only ever see an empty world, so the delivery is a bake step the lead runs on the
assembled file after `build_master.py`:

```
blender --background --python scripts/light_probes.py -- --blend master.blend --bake --save
```

It takes ~50 s on the M2, changes nothing but the probe caches, and must be re-run whenever the architecture or the
sun moves. `apply_preview_eevee` / `apply_viewport_eevee` now set `gi_irradiance_pool_size = 64` MB (the default 16
cannot hold the two volumes).

*Interior bounce fill (`LIGHT_rotunda_bounce`).* An up-facing 36 m disk area light at z 7.5 in the rotunda centre, warm
(1.0, 0.86, 0.68). It models the one thing the model has no geometry for — the pale concrete plaza, the lawn and the
lagoon throwing light up into the vault — and because an area light emits only along its +Z it lifts the coffers and the
vault soffits while adding almost nothing to what cam01 sees through the arch (which already matches ref 169). This is an
art bias, sized by measurement, exactly like `EXPOSURE_BIAS`: `light_build.FILL["energy"]` is the single number to dial.
