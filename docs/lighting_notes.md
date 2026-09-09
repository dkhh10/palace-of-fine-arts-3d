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

## 11. QA-01-20 — the dome from above

The defect was written against the placeholder ("blows out to near white from above, roughness 0.7"). With
`MAT_dome_membrane` in place that is gone: on cam06 (aerial, Eevee) the dome cap now reads **sRGB 130.2, 100.8, 76.7**
(Y 0.146) against the lawn's 64.5, 70.7, 64.5 (Y 0.060) — no clipped channel anywhere on the cap, dome/lawn = 2.45.

`ref 105` is a poor photometric reference for this: it is a distant, hazy, high-sun aerial in which the palace is about
100 px across, and neither the dome cap nor a comparable lawn patch can be isolated with confidence (the teal mask picks
up the whole marina, not the lagoon). The honest exposure-invariant test uses **ref 169**, a golden-hour photograph of
our exact moment, where the dome and a sunlit attic panel share one exposure:

| | dome cap | sunlit attic | dome / attic (Y) |
|---|---|---|---|
| render, Cycles hero | 160.3, 118.5, 82.1 (Y 0.2118) | 182.5, 136.9, 93.7 (Y 0.2867) | **0.74** |
| ref 169 | 226.6, 192.1, 134.6 (Y 0.5576) | 208.5, 164.5, 93.4 (Y 0.4100) | **1.36** |

In the photograph the dome is 36 % *brighter* than the sunlit wall; in the render it is 26 % darker — the membrane is
about 46 % too dark relative to the concrete, and it is much less warm (hue 28.0 vs 37.5). Both surfaces see the same
sun, so this is albedo, not lighting: **hand to materials** — `MAT_dome_membrane` needs to be lifted and warmed relative
to `MAT_concrete_ochre` until the ratio lands near 1.3. The lighting side of QA-01-20 (no blow-out, correct roughness
response) is closed.

## 10. QA-01-12 — exposure, sky colour and haze

Baseline (master built from main `e84b67e`, Cycles 48 spp hero) against ref 169, same regions:

| region | render (baseline) | ref 169 | verdict |
|---|---|---|---|
| sunlit attic (south corner) | 182.5, 136.9, 93.7 · Y 0.287 · hue 29.2 | 208.5, 164.5, 93.4 · Y 0.410 · hue 37.1 | **30 % dark**, hue -7.9 deg |
| sunlit attic (centre band) | 179.4, 135.2, 90.2 · Y 0.278 | 232.7, 189.1, 98.6 · Y 0.546 | 49 % dark |
| sky top | 143.1, 169.3, 196.5 · Y 0.384 · sat 0.272 | 116.0, 174.4, 226.1 · Y 0.396 · sat 0.487 | luminance **already within 3 %**; saturation 44 % low (B/R 1.37 vs 1.95) |
| far colonnade | 166.4, 182.7, 196.0 · Y 0.459 | 107.4, 90.4, 72.1 · Y 0.110 | (different framing; used only for the haze gradient) |

The important correction to the defect text: **the sky was not 10 % dark, it was desaturated.** At `SKY_CAMERA_BOOST`
1.6 the visible sky sat high enough in AgX's highlight roll-off to lose its blue. So the fix is not "brighten the sky";
it is "raise the exposure for the stone and take the boost back out of the sky, then put the saturation back with a
node that only camera and glossy rays see".

Changes in `light_build.py` (all four are single named constants):

| constant | was | now | why |
|---|---|---|---|
| `EXPOSURE_BIAS` | +0.50 EV | **+1.10 EV** | closes about two thirds of the sunlit-stone gap. **Assumption stated for the lead: the materials agent is warming the concrete albedo by a few percent concurrently, so this deliberately leaves ~0.1-0.2 EV of headroom rather than chasing the whole 30 %.** If materials overshoots, drop this constant, not the albedo. |
| `SKY_CAMERA_BOOST` | 1.60 | **1.50** | the exposure lift alone would push the sky ~25 % over ref 169; the boost is trimmed so the sky lands back on it. Glossy rays keep it, so the lagoon still reflects a bright sky. |
| `SKY_CAMERA_SATURATION` | — (new) | **1.20** | Hue/Saturation node in the world, driven by `Is Camera Ray + Is Glossy Ray`, so the *lighting* keeps the physical sky colour while the *visible* sky gets its blue back. Implemented in `light_calibrate.make_sky_world(camera_saturation=…)`. |
| `SKY["aerosol_density"]` | 1.0 | **1.6** | Mie extinction reddens the direct beam (lamp colour 1.000/0.607/0.258 vs 1.000/0.616/0.269) and warms the sun-side horizon — the physical way to buy back the hue instead of tinting the lamp by hand. The greying it causes in the anti-solar sky is exactly what `SKY_CAMERA_SATURATION` undoes. |
| `MIST` depth | 1500 m | **700 m** | at 1500 m the mist pass reached only 0.11 at 200 m, so the compositor haze was 6 % on the colonnade ends. 700 m gives mist 0.24 at 200 m. |
| `COMP["haze_strength"]` | 0.55 | **0.85** | with the shorter mist depth this is 12 % haze at 110 m, 24 % at 200 m (the colonnade ends), 67 % at 500 m (the backdrop). |
| `COMP["haze_warmth"]` | (1.06, 1.0, 0.88) | **(1.22, 1.0, 0.74)** | ref 169's veil behind the wings is distinctly warm, not neutral. |

### QA-01-9 result: the fill sweep (cam04, Eevee 32 TAA, probes baked, master rebuilt on main `6b54fbd`)

| `FILL["energy"]` | coffer field sRGB | Y | hue | ratio to the sunlit attic (197/255) |
|---|---|---|---|---|
| 0 (probes baked, no fill) | 0.3, 0.1, 0.1 | 0.0000 | — | 0.00 |
| baseline (no probes, fast GI) | 24.5, 22.1, 14.3 | 0.0081 | 45.5 | 0.12 |
| 4 000 W | 40.1, 28.5, 13.7 | 0.0134 | 33.7 | 0.20 |
| **9 000 W (shipped)** | **60.4, 45.6, 26.2** | **0.0297** | **34.0** | **0.31** |
| 20 000 W | 91.0, 71.2, 44.7 | 0.0695 | 34.3 | 0.46 |
| ref 083 (exposed for the ceiling) | 91.7, 76.1, 52.5 | 0.0770 | 36.2 | — |

Evidence: `renders/qa_comparisons/light_r07_qa0109_ceiling.png` (before / Cycles ground truth / 4 000 W / 9 000 W /
ref 083 / probes-with-no-fill).

**Shipped 9 000 W, ratio 0.31 against QA's 0.35 target — deliberately, and here is the argument.** At 9 000 W the octagonal
coffers, the rosettes and the vault ribs are all legible and the hue (34.0) matches ref 083 (36.2) within 2 deg; the
"before" frame is a shapeless blue-grey murk. 20 000 W lands the coffer field on ref 083's own numbers (91.0 vs 91.7)
and passes 0.35 comfortably — but ref 083 is exposed *for the ceiling*, and a hero frame exposed for the sunlit exterior
should not show the interior at a ceiling-exposure brightness. **`light_build.FILL["energy"]` is one number**: if QA wants
the acceptance ratio met literally, set it to 20 000 (or 12 000 for ~0.37) and re-run the probe bake. Both bracketing
renders are committed, so the choice is an art-direction call with the evidence already on disk.

### QA-01-12 result (cam01, master rebuilt on main `6b54fbd` with ARCH + ENV merged)

| region | before (Cycles 48 spp) | after | ref 169 | after / ref |
|---|---|---|---|---|
| sunlit attic | 182.5, 136.9, 93.7 · Y 0.287 · hue 29.2 | **192.0, 153.3, 118.7 · Y 0.354 · hue 28.3** | 208.5, 164.5, 93.4 · Y 0.410 · hue 37.1 | **0.86** (was 0.70); hue -8.8 deg |
| sky top | 143.1, 169.3, 196.5 · Y 0.384 · sat 0.272 | **140.4, 176.9, 210.5 · Y 0.417 · sat 0.333** | 116.0, 174.4, 226.1 · Y 0.396 · sat 0.487 | **1.05 — inside the +-10 % target** |
| shaded north face | 120.9, 88.6, 54.5 · Y 0.114 | 137.0, 103.0, 70.0 · Y 0.155 | 147.5, 112.1, 78.0 · Y 0.184 | 0.84 (was 0.62) |

Composite with the numbers burnt in: `renders/qa_comparisons/light_r07_qa0112_hero.png` (before Cycles / after / ref 169).
The warm haze is visibly doing its job in the after frame: the north wing behind the rotunda is veiled and lifted,
which it was not before.

**Sky luminance: closed (within 5 %).** **Sunlit stone: 0.86 of ref 169, i.e. 14 % dark, and this is on purpose.**
The materials agent is warming the concrete albedo in the same round; a 5 % albedo lift lands the attic inside the
+-10 % window without touching the rig again. **If materials comes in short, raise `light_build.EXPOSURE_BIAS` from 1.10
to about 1.25 and trim `SKY_CAMERA_BOOST` from 1.50 to ~1.40 to keep the sky where it is.** Do not close it by
brightening albedos past the measured neutral values — the rig is calibrated to a physical 18 % card.

**Not fully closed: sky saturation.** 0.272 -> 0.333 against ref 169's 0.487 (B/R 1.37 -> 1.50 vs 1.95). Two measured
points bracket the knobs: (boost 1.15, sat 1.35) gave sky Y 0.300 / sat 0.572 — saturated enough but a stop dark; the
shipped (boost 1.50, sat 1.20) gives Y 0.417 / sat 0.333. Along that one-dimensional line the target pair is not
reachable, so the next move is to raise `SKY_CAMERA_SATURATION` alone (1.20 -> ~1.45) at the shipped boost and re-measure;
I did not ship that untested. The remaining hue gap on the stone (8.8 deg vs the 8 deg target) is mostly albedo and
should shrink with the same materials change.

## 12. What the lead has to do (round 07 delivery)

1. `blender --background --python scripts/build_master.py` — as usual. The rig now brings in, inside `LIGHT`:
   `LIGHT_sun`, `LIGHT_rotunda_bounce`, `LIGHTPROBE_rotunda`, `LIGHTPROBE_colonnade`, plus the flythrough objects.
2. **New, required step:** `blender --background --python scripts/light_probes.py -- --blend master.blend --bake --save`
   (~10-50 s). Without it the two probe volumes are present but unbaked and Eevee falls back to fast GI.
   Re-run it after any architecture change or a change of moment. `-- --free` clears the caches.
3. Nothing else changes: `light_presets.apply_final_cycles` / `apply_preview_eevee` / `apply_viewport_eevee` remain the
   single source of truth for render settings, and `build_master.py` already calls `light_presets.apply_look`.
   The viewport preset is untouched apart from the irradiance pool size, so the Eevee fly-around stays as fast as it was
   (viewport preset: 16 TAA, shadows on, raytracing and fast GI off).
4. Two knobs are deliberately left for the art director, both one line + a re-bake: `light_build.FILL["energy"]`
   (9 000 shipped; 20 000 matches ref 083 exactly) and `light_build.EXPOSURE_BIAS` (1.10 shipped; ~1.25 if the materials
   albedo warming lands short of the 14 % the sunlit stone still needs).

New/changed files this round: `scripts/light_probes.py` (new), `scripts/light_measure.py` (new),
`scripts/light_lookdev.py` (new), `scripts/light_build.py`, `scripts/light_calibrate.py`, `scripts/light_presets.py`,
`scripts/light_preview.py`, `assets/lighting.blend`.

---

# Round 08 — Phase 4 polish round 1, from QA round 02

Four defects: QA-02-4 (blocker, exposure), QA-02-11 (flythrough missing from master), QA-02-8 (haze greys cam06),
QA-02-12 (vault soffits dark). Everything below was measured on a local master built with `scripts/lead_build.sh`
from this branch. Renders: `renders/previews/qa/roundlight3_*`.

## 13. QA-02-4 — exposure: QA was right and I was wrong, +0.9 EV

`EXPOSURE_BIAS` 1.10 -> **2.00**, i.e. `view_settings.exposure` -3.2911 -> **-2.3911**. Nothing else changed: not the
sun colour, not the sky strength, not an albedo. QA-02-14 (stone 5-9 deg cool) is deliberately left to materials,
because the measured response is -1.1 deg of hue per +1 EV — exposure moves warmth the *wrong* way.

**Why my round-07 estimate of "+0.15 EV" was an order of magnitude short.** I measured the deficit in display-referred
sRGB (the sunlit attic was 14 % under ref 169) and reasoned about it as if the transfer were roughly linear. It is not:
AgX's shoulder compresses about 1.6x of display gain into each stop of scene exposure in that range, so a 14-26 %
display gap is most of a stop of scene light. QA measured the response curve instead of assuming it
(`scripts/qa_exposure_sweep.py`, three renders at +0/+0.5/+1.0 EV) and got +32.0 / +35.2 / +30.5 / +33.8 sRGB units
per EV on attic / column / sky / water. That is the right way to answer this question and I should have done it in
round 07. **Rule for the rest of this build: never convert a display-referred error into an exposure change by
reasoning; render the sweep.**

### Result, Cycles hero 1920x1080 64 spp vs ref 169 (`scripts/light_measure.py --regions hero`)

Same `light_measure` boxes on the render (`hero`) and on ref 169 (`hero_ref169`); "lum" is display-referred
relative luminance of the mean sRGB, the same quantity QA used.

| region | round 02 | round 08 | ref 169 | ref/render | EV gap |
|---|---|---|---|---|---|
| sunlit attic | 142.4 | **178.8** | 168.7 | 0.94 | -0.08 |
| sunlit attic (b) | — | **175.6** | 191.8 | 1.09 | +0.13 |
| sky top | 153.7 | **193.9** | 165.7 | 0.85 | -0.23 |
| sky left | — | **186.7** | 193.8 | 1.04 | +0.05 |
| colonnade far | — | **93.9** | 92.7 | 0.99 | -0.02 |
| water centre | 108.9 | **104.2** | 106.0 | 1.02 | +0.02 |
| shade, north face | — | **146.0** | 117.2 | 0.80 | -0.32 |

Every region is now inside +-0.33 EV of ref 169, against +0.70 to +1.44 EV before. **QA's acceptance test — sunlit
attic within +-10 % of 179.4 — is met at 175.6-178.8, i.e. within 2 %.** Closed.

**Two residuals I am flagging rather than hiding, because neither is an exposure error:**

1. **Sky gradient, not sky level.** The render's sky is nearly flat top-to-horizon (193.9 / 186.7) while ref 169 falls
   17 % from the hazy low sky to the top (193.8 / 165.7). The two-box mean is 190.3 vs 179.8, +6 %, inside the window;
   but no single value of `SKY_CAMERA_BOOST` fixes both boxes, because the shape is wrong, not the scale. Trimming the
   boost to hit the top box would put the horizon box 13 % under. This is a sky-model job (ozone/aerosol profile, or
   letting the compositor haze reach the sky instead of masking it off with `is_geometry`), and it is the next thing
   I would do on the world if the lead wants it in round 09.
2. **Shade is now 25 % too light.** Shaded stone / sunlit stone reads 0.82 in the render against 0.70 in ref 169, i.e.
   the render's dynamic range is 0.23 EV flatter than the photo's. The cause is `SKY_STRENGTH = 2.0`, the round-05 art
   bias that doubled the sky's *lighting* contribution to open the shadows; +0.9 EV has made that bias visible. The
   knob is one line, but it feeds `light_calibrate` and so moves the calibrated exposure I just closed, which is why I
   did not touch it in the same round. Recommend it as a round-09 item, swept, not guessed.

## 14. QA-02-11 — the flythrough was being deleted by my own rebuild

Not a modelling bug and not the lead's: **`light_build.py` rebuilds the LIGHT collection with
`common.rebuild_collection` at the top of every run**, and `light_flythrough.py` wrote `CAM_flythrough_path` /
`_target` / `CAM_flythrough` into that same collection *afterwards*, as a separate manual step. So every later
`light_build.py` run silently deleted the deliverable, and the committed `assets/lighting.blend` shipped without it.
`build_master.py` was innocent — it appends the whole LIGHT collection and would have carried the objects through.

Fix: `light_build.build()` now calls `light_flythrough.build(scene)` itself, last, before the save. The flythrough is
part of the rig, so it cannot be out of step with the rig again.

Verified headlessly on both files:

- `assets/lighting.blend` LIGHT collection: `LIGHT_sun`, `LIGHT_rotunda_bounce`,
  `LIGHT_rotunda_vault_bounce_00..07`, `LIGHTPROBE_rotunda`, `LIGHTPROBE_colonnade`,
  **`CAM_flythrough_path`, `CAM_flythrough_target`, `CAM_flythrough`**.
- `master.blend` after `scripts/lead_build.sh`: all three present; `CAM_flythrough` carries `FOLLOW_PATH` ->
  `CAM_flythrough_path` and `TRACK_TO` -> `CAM_flythrough_target`, and the path evaluates —
  frame 1 (-16.0, 113.9, 1.0), 240 (73.5, 95.3, 4.3), 480 (66.6, 4.4, 6.0), 720 (0.0, 1.0, 2.5).

## 15. QA-02-8 — the aerial haze: the veil was wrong, but it is not what greys cam06

Two things were wrong with the round-07 haze and both are fixed:

1. **Shape.** The mist pass was used raw as the haze factor (LINEAR, 30 -> 730 m) times 0.85. That is a ramp with no
   asymptote, so everything past ~730 m sat at 0.85 haze and the whole background mixed to one colour. Airlight is
   `1 - exp(-d/L)`, which rises fast near the camera and then flattens. The mist pass is now a plain linear distance
   ramp over a long baseline (20 -> 2020 m) and `COMP_golden_hour` shapes it: `cap * (1 - exp(-k * mist))`, exposed as
   the **Haze Falloff** socket (`k`; extinction length `L = MIST["depth"] / k`) beside **Haze Strength** (now the cap,
   not a scale). Shipped: L = 800 m, cap 0.50 — 5 % veil at 110 m, 10 % at 200 m, 23 % at 500 m, 42 % at 1200 m.
2. **Colour.** `haze_warmth` (1.22, 1.0, 0.74) on the measured west-horizon radiance produced (3.82, 3.74, 3.02) —
   a neutral grey-yellow at linear saturation 0.21. That *was* the grey-olive. Now (1.70, 1.00, 0.48) gives
   (5.32, 3.74, 1.96): linear hue 32 deg, saturation 0.63. **The warmth is carried by the haze colour, not by more
   haze** — which is the whole point, since more haze is exactly the global desaturation this fix had to avoid.

### But the diagnosis in QA-02-8 is only half right, and the measurement says so

`scripts/light_r08_sweep.py` rendered cam06 at five haze settings **including the haze switched off entirely**
(640x360 Eevee, `--cap 0.0`):

| cam06 setting | dome | far shore | far hills | dome/shore | shore hue | shore sat |
|---|---|---|---|---|---|---|
| **haze OFF (cap 0)** | 120.6 | 111.5 | 108.4 | **1.08:1** | **84.6** | **0.178** |
| cap 0.60, L 1500 m | 140.6 | 136.6 | 136.9 | 1.03:1 | 53.8 | 0.171 |
| cap 0.60, L 900 m | 148.0 | 145.5 | 146.5 | 1.02:1 | 48.2 | 0.172 |
| cap 0.60, L 400 m | 160.1 | 158.9 | 160.2 | 1.01:1 | 42.6 | 0.164 |
| round 02 (ramp x 0.85) | 135.9 | 135.4 | 139.3 | 1.00:1 | 57.8 | 0.089 |

**With no haze at all the aerial is already hue 84.6 (olive) at saturation 0.178, and the dome/far-shore contrast is
already 1.08:1.** The haze took saturation from 0.178 down to 0.089 and it flattened 1.08 to 1.00 — real damage, now
undone — but it did not create the grey-olive and it did not create the flatness. Those are the scene's own colour and
the scene's own tonal range at that distance: the same cam06 lawn QA-02-15 calls "a flat olive plane" and the same
stone QA-02-3 calls "blotchy olive". **QA's acceptance numbers for this defect (contrast >= 1.5:1) are therefore not
reachable from the lighting rig**: 1.08:1 is the ceiling with the haze deleted. I am not going to fake it by pushing
contrast into the compositor, because that would hide an environment/materials defect behind a lighting knob.

### Shipped result, cam06 Eevee 1280x720 (`roundlight4_06_aerial.png`)

| measure | round 02 | round 08 | QA target |
|---|---|---|---|
| far shore saturation | 0.089 | **0.218** | >= 0.20 **met** |
| far hills saturation | 0.081 | **0.177** | — |
| dome cap saturation | 0.091 | **0.192** | — |
| far shore hue | 57.8 | **43.8** | 30-45 warm band **met** |
| far hills hue | 56.9 | **45.6** | 30-45 **just outside** |
| dome / far shore contrast | 1.00:1 | **1.03:1** | 1.5:1 **not reachable** (1.08:1 with haze off) |

Saturation at 0.218 is *above* the no-haze floor of 0.178, because the shipped haze colour is itself saturated (0.63)
and warm — the veil now adds chroma instead of removing it. **Two of three acceptance numbers met; the contrast one
belongs to environment + materials and I have put the haze-off measurement on record so it can be re-assigned.**

## 16. QA-02-12 — vault soffits: improved 75 %, and the reason the target is unreachable from inside

Added `LIGHT_rotunda_vault_bounce_00..07`: eight up-facing 12.5 x 4 m rectangles, one on each bay axis at radius
17.5 m, z 13.0, spread 90 deg, 2400 W each. `scripts/light_vault_probe.py` (raycast, no render) first ruled out the
obvious explanation: the soffits see the emitters perfectly well, at cos 0.87-0.97 over 14-15 m, and they see the
central disk too at cos 0.34-0.43. It was never occlusion.

### Shipped result, cam04 Eevee (`roundlight4_04_rotunda_ceiling.png`)

| measure | round 02 | round 08 | QA target |
|---|---|---|---|
| vault soffit W / frame's own sky | 0.197 | **0.352** | >= 0.45 |
| vault soffit E / own sky | 0.215 | **0.367** | >= 0.45 |
| mean soffit / own sky | 0.206 | **0.360** (+75 %) | >= 0.45 |
| coffer field / own sky | 0.411 | 0.710 | (was passing at 0.50 vs ref 083's 0.39) |

### Why I stopped at 0.36 instead of buying 0.45

**The soffit and the coffered ceiling are locked together.** Six configurations, measured on cam04 at 640x360:

| emitter | soffit/sky | coffer/sky | **soffit/coffer** |
|---|---|---|---|
| none (disk only) | 0.241 / 0.265 | 0.455 | 0.556 |
| r 17.5, z 13, 2400 W | 0.336 / 0.359 | 0.689 | 0.504 |
| arch plane r 20, z 9, tilted 55 deg in, 4000 W | 0.380 / 0.405 | 0.778 | 0.505 |
| r 17.5, z 13, 4000 W | 0.394 / 0.417 | 0.805 | 0.503 |
| r 17.5, z 15, 4000 W, **central disk off** | 0.318 / 0.308 | 0.644 | 0.486 |
| r 17.5, z 8, 5000 W | 0.411 / 0.458 | 0.842 | 0.516 |
| r 17.5, z 15, 8000 W, **central disk off** | 0.452 / 0.423 | 0.855 | 0.512 |

Height, radius, tilt, spread, and switching the central disk off entirely: the ratio never leaves 0.486-0.556.
So hitting QA's 0.45 costs a coffer field at **0.855 of sky, 2.2x ref 083's 0.39** — it buys QA-02-12 by re-opening
QA-01-9, which QA has already marked closed. That is a bad trade and I am not making it silently.

**The physical reason.** In ref 083 the soffits are *brighter than* the coffers (0.58 vs 0.39, a 1.5:1 the other way
round); in our render the coffers are 2x the soffits. That inversion is not a fill-light strength problem. The real
soffits are lit by the sunlit plaza and lagoon seen through the great arches from a few metres away — a source that is
*outside* the building. Our 7.4 deg morning sun genuinely never lands on that plaza, so there is nothing outside to
bounce, and **no interior source can reproduce a ratio that comes from outside**: whatever I put under the vault
lights the ceiling through the same open volume. The honest fixes are (a) let the sun actually reach the plaza (a
moment/elevation change — art direction, not a knob), or (b) light linking, which Cycles has and Eevee Next does not,
so it would break the "confirmed in both engines" half of the acceptance.

**One number for the lead**, as in round 07: `light_build.VAULT_FILL["energy"]`. 2400 shipped (soffit 0.36, coffer
0.71); **8000 with `FILL["energy"] = 0` meets QA's 0.45 literally** (soffit 0.45, coffer 0.86). Both renders are on
disk under `renders/previews/lighting/r08sweep_04_*`. Re-run `scripts/lead_build.sh` after changing it (probe re-bake).

### Side effect of the lighter haze the lead needs to know about (hands QA-02-7 back to environment)

On the same Cycles hero, the far colonnade band went **93.9 -> 65.4** between the heavy round-07-style haze
(`roundlight3`) and the shipped one (`roundlight4`), against ref 169's 92.7. It did not get darker: the round-07 haze
was *lifting* it by 44 %, which is why round 02 measured the wings at "only" 52 % dark. **The veil was cosmetically
hiding QA-02-7.** With an honest haze the wings read 1.42x under ref 169 and environment has to fix the tree screen
for real. Everything else in the hero is unchanged within 0.03 EV.

| hero region | roundlight3 (cap 0.60 / L 400 m) | roundlight4 (shipped, cap 0.50 / L 800 m) | ref 169 |
|---|---|---|---|
| sunlit attic | 178.8 / 175.6 | **177.6 / 174.2** | 168.7 / 191.8 |
| sky top / left | 193.9 / 186.7 | **193.9 / 186.7** | 165.7 / 193.8 |
| water centre | 104.2 | **104.0** | 106.0 |
| shade north | 146.0 | **139.9** | 117.2 |
| colonnade far | 93.9 | **65.4** | 92.7 |

### QA-02-12 cross-engine check: **Cycles meets the target, Eevee does not, and it is not the bake**

QA asked for the fix to be confirmed in Cycles so it is not Eevee-only. Cycles cam04, 1920x1080, 64 spp, 606 s
(`roundlight4_04_rotunda_ceiling_cycles.png`):

| cam04, same rig | vault soffit W / E | mean soffit / own sky | coffer field / own sky |
|---|---|---|---|
| round 02 Eevee (before) | 0.197 / 0.215 | 0.206 | 0.411 |
| round 08 **Eevee** | 0.352 / 0.367 | **0.360** | 0.710 |
| round 08 **Cycles 64 spp** | 0.451 / 0.507 | **0.479** | 0.696 |

**In Cycles the soffits land at 0.479, i.e. QA's `>= 0.45` acceptance is met**, and the two engines agree to 2 % on
the coffer field (0.710 vs 0.696) — so the fix is real and not an Eevee artefact. The 33 % that Eevee is missing is
on the soffits only. Since the deliverable hero and the Phase-5 finals are Cycles, **the defect is closed where it
counts**; Eevee, which is the viewport/preview engine, reads the vaults about a third darker than they will render.

I tested the obvious cause and it is **not** bake resolution. Re-baked `LIGHTPROBE_rotunda` at (28, 28, 20) —
2.0 x 2.0 x 1.8 m spacing, 2.8x the samples — and the Eevee soffit moved **0.360 -> 0.359**. That is Eevee Next's
irradiance-volume + screen-trace approximation under-lighting a concave soffit that Cycles path-traces properly.
Reverted to (20, 20, 14) and a 64 MB pool rather than pay 3x the bake time and a 128 MB pool for nothing; the negative
result is recorded in `scripts/light_probes.py` so it does not get re-tried.

## 17. Round 08b — sunlit-stone chroma (materials' hand-off). PARTIAL, and one measurement caveat matters

Materials measured that at +0.9 EV albedo has no authority left over chroma (a 44 % cut of albedo blue moved display
blue 3 %), leaving the sunlit attic's R-B spread at 81-89 against ref 169's 134. Three lighting levers were swept on
the Cycles hero; all three help, none is enough on its own.

| lever | attic R-B | note |
|---|---|---|
| baseline (sky x2.0, Base Contrast) | 88.1 | |
| `SKY_STRENGTH` 2.0 -> 1.0 | 94.8 | the round-05 art bias was washing sky-blue over every sunlit face |
| `SKY_STRENGTH` 2.0 -> 0.6 | 97.8 | shade 146.5 -> 128.1 |
| sun blue x0.7 | 97.7 | at strength 1.0 |
| -0.35 EV | 102.2 | but attic luminance falls out of the +-10 % window |
| **`LOOK` -> `AgX - High Contrast`** | **113.5-118.1** | the strongest lever by far |
| `LOOK` -> `AgX - Punchy` | 112.7 | same chroma, but a stop of luminance and water 111 -> 71: rejected again |

**Shipped: `SKY_STRENGTH` 1.0, `LOOK` "AgX - High Contrast", `SKY_CAMERA_BOOST` 1.20, new `SKY_GLOSSY_BOOST` 3.00,
`EXPOSURE_BIAS` 1.75 (view exposure still -2.39; the calibration moved -4.39 -> -4.14 when the sky halved).**
`light_calibrate.make_sky_world` gained a `glossy_boost` split from `camera_boost`, because the camera's sky had to
come DOWN to ref 169 while the lagoon's reflection had to stay UP, and one socket could not do both.

### The caveat, and it invalidates part of the sweep

The sweep was run at 960x540 / 32 spp. Re-rendering the *identical* shipped rig at 1920x1080 / 64 spp gives
materially different numbers on these small regions:

| same rig, same exposure, same look | attic sRGB | attic lum | R-B | sky top |
|---|---|---|---|---|
| 960x540, 32 spp (what the sweep measured) | 229.8, 177.0, 112.5 | 183.6 | 117.3 | 165.8 |
| **1920x1080, 64 spp (the real deliverable)** | 206.0, 162.5, 108.6 | **167.9** | **97.4** | **154.1** |

So **every knob choice above was picked against numbers that are ~16 luminance and ~20 R-B optimistic.** The chroma
targets are NOT met at delivery resolution: R-B 97.4 against the >= 110 asked for, attic luminance 167.9 just under
the 172.6 floor. Sky top 154.1 (window 149.1-182.3) and shade 131.8 (floor 93.8) do pass, and R-B did improve
88.8 -> 97.4 while the sky's 17 % excess was fixed. **Anyone continuing this must re-sweep at 1920x1080.**

### Where I stopped

Unfinished: (a) re-sweep at delivery resolution to close R-B 97.4 -> 110, most likely by combining High Contrast with
a warmer sun (`sun blue x0.4-0.7`, worth ~+3 to +7) and a small albedo/exposure trade with materials; (b) the interior
fills are now oversized for the halved sky — cam04 Eevee soffit/own-sky went 0.360 -> 0.803 and coffer 0.710 -> 1.040,
so `FILL["energy"]` 7600 and `VAULT_FILL["energy"]` 2400 both want scaling down by roughly half, re-measured against
ref 083's 0.58 / 0.39. Neither was started. cam06 improved on its own: far-shore saturation 0.218 -> **0.296**,
hue 43.8 -> 39.3.

## 18. Round 09 — chroma at delivery resolution (A) and the interior fills (B). BOTH CLOSED

### The finding that reframes round 08b: the shipped AgX look never reached master.blend

There were two `LOOK` constants. `light_build.LOOK` has said `"AgX - High Contrast"` since round 08b and sets the
look inside `assets/lighting.blend`; `light_presets.LOOK` still said `"AgX - Base Contrast"` from round 05, and it is
**that** one `build_master.py` writes into `master.blend` through `apply_look`. So every QA render and the
deliverable rendered at Base Contrast while round 08b's strongest chroma lever sat in a file nothing renders from.
The rebuilt master's own report line now reads `look 'AgX - High Contrast', exposure -2.333`.

This also means **round 08b's "the sweep is ~16 lum / ~20 R-B optimistic at delivery resolution" was wrong**, and
anyone acting on it would have gone hunting in the wrong place. Same rig, same exposure, cam01 attic R-B:

| | 960x540 / 32 spp | 1920x1080 / 64 spp |
|---|---|---|
| AgX - Base Contrast | 94.8 (lum 170.0) | **97.4 (lum 167.9)** |
| AgX - High Contrast | 117.9 (lum 183.1) | **119.0 (lum 181.1)** |

Resolution is worth **+2.6 R-B and -2.1 luminance**, not +20/+16. The whole gap was the look divergence. The look is
now defined once, in `light_presets.py`, and `light_build.LOOK` aliases it so they cannot drift apart again.

### A. What each knob bought at 1920x1080 / 64 spp, Cycles, cam01 hero

Every row is a real render (`scripts/light_r09_sweep.py --hero`, one at a time on the lead's freshly built master).
The exposure is **not** held constant when the sky moves: `light_build` re-runs the 18 % grey-card calibration
whenever `SKY_STRENGTH` changes, and the sweep reproduces that in closed form (`exposure_compensation`, asserted
against the two calibrations on record), so each row is "less sky-blue", not "less light".

| # | sky | cam boost | sun blue | look | attic lum | **attic R-B** | sky top | shade | attic sat |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 1.00 | 1.20 | 1.00 | Base Contrast | 167.9 | **97.4** | 154.1 | 131.8 | 0.473 |
| 1 | 1.00 | 1.20 | 1.00 | **High Contrast** | 181.1 | **119.0** | 165.9 | 134.7 | 0.523 |
| 2 | 0.80 | 1.50 | 0.75 | High Contrast | 180.7 | **122.9** | 168.4 | 132.3 | 0.538 |
| 3 | 0.60 | 2.00 | 0.55 | High Contrast | 180.4 | **125.8** | 170.9 | 129.7 | 0.550 |
| 4 | 1.00 | 1.20 | 1.00 | Very High Contrast | 186.7 | **118.9** | 170.9 | 136.0 | 0.509 |
| — | ref 169 | | | | 191.8 | **134.1** | 165.7 | 117.2 | 0.576 |
| | target | | | | >= 172.6 | >= 110 | 149.1-182.3 | >= 93.8 | |

Row 0 is the control and it reproduced `roundlight6` to the last digit (97.4 / 167.9 / 154.1 / 131.8), so the
sweep and QA are measuring the same thing.

- **The look is worth +21.6 R-B and +13.2 luminance on its own** (row 0 -> 1) and by itself moves all four numbers
  into their windows. Nothing else was needed to meet the brief; everything below is the margin.
- **Sky 1.00 -> 0.80 with the camera boost raised 1.20 -> 1.50 is worth ~+2.5 R-B for free.** The product
  `sky x camboost` stays at 1.20, so the visible sky is bit-identical to round 08b's and only the diffuse fill
  changes. It is a chroma knob, not a level knob: on a sun-facing surface the sky supplies 10.4 of 27.7 blue units
  against 11.2 of 78.5 red (`calibration_report` `E_sunfacing_disc_on/off`), i.e. 2.6x more leverage on blue.
  `SKY_GLOSSY_BOOST` went 3.00 -> 3.75 for the same reason, so the lagoon reflects the same sky it did.
- **Sun blue x0.75 is worth ~+1.4 R-B and +0.015 saturation at no luminance cost** (blue carries 7 % of luminance).
  Applied to the *calibrated* lamp colour, after the sun-disc integration, so the calibration stays physical:
  (1.000, 0.607, 0.258) -> (1.000, 0.607, 0.193).
- **Very High Contrast is not better than High Contrast.** It buys luminance (186.7, nearest ref) but *loses*
  saturation (0.509 vs 0.523) and pushes the shade further from ref 169 (136.0 vs 117.2). Rejected.
- **Exposure was never traded.** The luminance floor was the binding constraint at row 0, and the look fixed it; a
  negative exposure delta would have bought chroma at the cost of the one number that was already failing.

**Shipped: row 2** — `SKY_STRENGTH 0.80`, `SKY_CAMERA_BOOST 1.50`, `SKY_GLOSSY_BOOST 3.75`, `SUN_BLUE_MULT 0.75`,
`LOOK "AgX - High Contrast"`, `EXPOSURE_BIAS` unchanged at 1.75 (calibration -4.08 + 1.75 = **-2.33 EV**, exactly
what the sweep measured). Row 3 is on record if the lead wants +3 more R-B for a 40 % sky cut; I stopped at 0.80
because it is the smallest departure from the physical sky that takes most of the gain.

**Verified on the rebuilt master** (`r09_verify_01_hero_cycles.png`, Cycles 1920x1080 / 64 spp): attic sRGB
229.3, 176.5, 109.7 -> **R-B 119.6, lum 182.9, sky top 168.5, shade 137.2 — all four pass.** The verification
number differs from row 2 by -3.3 R-B / +4.9 shade because the interior fills changed underneath it (B, below);
row 2 was measured on the old fills.

**Still open and NOT lighting's:** attic hue 33.3 against ref 169's 40.5 (QA-02-14). Seven degrees, and the whole
round-09 sweep moved it by 0.5 deg. Saturation is now 0.523 against 0.576, inside QA's 0.06 window. The hue is in
the albedo.

### B. Interior fills — and the soffit/coffer lock is broken

Round 08 measured soffit/coffer at 0.486-0.556 across height, radius, tilt, spread and the central disk, and
concluded ref 083's 0.58/0.39 (a **1.49** ratio the other way round) was unreachable from inside the building.
That conclusion was wrong, and the knob is **spread**. At 90 deg each vault emitter floods the whole vault volume,
so most of its light lands on the central coffered dome instead of the soffit above it — which is also physically
wrong: the plaza light these bays actually receive arrives through their own arch opening, which subtends roughly
+-25 deg from a point under the vault. **A restricted cone is the more faithful model, not a cheat.**

Cycles, cam04, round-09 rig (960x540 / 48 spp for the sweep; ratios are large-region means and move < 0.01 with
resolution — confirmed by the 1920x1080 verification below):

| disk W | vault W each | spread | soffit / own sky | coffer / own sky | soffit/coffer |
|---|---|---|---|---|---|
| 7600 | 2400 | 90 | 0.617 | **1.016** | 0.61 |
| 3800 | 1200 | 90 | 0.371 | 0.647 | 0.57 |
| 2280 | 720 | 90 | 0.253 | 0.459 | 0.55 |
| 0 | 1560 | 90 | 0.316 | 0.472 | 0.67 |
| 0 | 2400 | 30 | 0.309 | 0.186 | 1.66 |
| 3040 | 3360 | 45 | 0.531 | 0.489 | 1.09 |
| 0 | 4320 | 45 | 0.538 | 0.305 | 1.76 |
| **1140** | **3960** | **45** | **0.535** | **0.376** | **1.42** |
| ref 083 | | | 0.58 | 0.39 | 1.49 |

Uniform scaling could never work: at 90 deg the pair walks along a line of slope 0.6 and the two targets are on a
line of slope 1.49, so every uniform scale trades QA-02-12 against QA-01-9 — which is exactly what round 08
observed. Narrowing the cone rotates the line.

**Shipped: `FILL["energy"] 7600 -> 1140 W`, `VAULT_FILL["energy"] 2400 -> 3960 W`, `spread_deg 90 -> 45`.**
Verified on the rebuilt master at delivery resolution (`r09_verify_04_ceiling_cycles.png`, Cycles 1920x1080):
**soffit / own sky 0.541 (ref 0.58, delta -0.039) and coffer / own sky 0.384 (ref 0.39, delta -0.006) — inside
+-0.08 of both, for the first time.** soffit/coffer 1.408 against ref's 1.49.

**Eevee, same file, same frame: soffit 0.405, coffer 1.137.** Eevee and Cycles agreed to 2 % on the coffer field in
round 08 and they now disagree by 3x. The probes were re-baked by `scripts/lead_build.sh` after the change, so it is
not a stale bake: Eevee Next is not honouring the 45 deg spread the way Cycles does — its baked irradiance
redistributes the emitters' power over the whole vault volume, which is precisely the 90 deg behaviour the fix
removes. Cycles is the deliverable engine (hero, Phase-5 finals) so **the defect is closed where it counts**, but
the Eevee viewport now shows a coffered dome about 3x too bright. Two honest routes if that matters: split the
emitters into a Cycles-only narrow set plus an Eevee-only weak wide set (breaks "confirmed in both engines"), or
model the arch opening as real geometry with an emissive plane inside it. Neither was attempted.

**Second cost on record:** at 45 deg the two soffit boxes read 0.404 W / 0.679 E in Cycles, a 1.7:1 imbalance
against 1.14:1 at 90 deg — a narrow cone leaves the obliquest part of the vault to the sky alone. Eevee, which is
ignoring the spread, stays balanced (0.420 / 0.390). If QA flags the imbalance, spread 60 deg halves it but costs
the coffer target (0.535 / 0.570 at the nearest energy tried).

### Where round 09 stopped

- Attic hue 33.3 vs ref 169's 40.5 is materials' (QA-02-14); no lighting knob moves it more than 0.5 deg.
- The Eevee/Cycles vault disagreement above.
- cam06 and the aerial haze were not re-touched; round 08's finding stands (the grey-olive is the scene's own
  colour, not the veil).
- Water: `water_centre` saturation 0.228 -> 0.314 and hue 27.9 -> 30.6 (ref 30.6) came free with the look; luminance
  96.6 -> 90.2 against ref 106.0, i.e. still ~0.2 EV dark. Not chased.

## 19. Round 10 — the whole round is one number: the exposure was 0.5 EV hot

Brief: `docs/briefs/lighting_r10.md`, items 1-7. Everything below is measured with **QA's own hero boxes**
(`docs/qa_round_03.md` "Measurements", reproduced in `scripts/light_r10_measure.py`), not with lighting's old
`REGIONS["hero"]` — QA showed in round 03 that lighting's `attic_sunlit_b` box sits on the drum in the render frame
and on the attic in the photo frame, so the two agents were measuring different stone. The reference row is ref 169
warped into the render frame by QA's align transform (`round03_cam01_aligned_vs_ref169.png` panel 1), which
reproduces QA's published numbers to 0.5 units.

### Baseline on the lead's merged master (arch p4r2, mat r4, env r4), cam01 Cycles 1920x1080 / 64 spp

| | before | ref 169 | target |
|---|---|---|---|
| sunlit attic sRGB | 232,194,130 | 231,187,95 | |
| attic saturation | 0.441 | 0.588 | >= 0.53 |
| attic R-B | 102.3 | 136.1 | >= 120 |
| attic luminance | **197.5** | 189.6 | 178.2-201.0 |
| shaded attic hue / lum | 42.5 / 130.6 | 29.5 / 115.0 | hue 29.5 +- 6 |
| columns (QA mask) | 152.0 | 95.8 | 1.0x |
| near water sat / hue | 0.487 / 204.8 | 0.270 / 192.1 | 0.22-0.32, 185-200 |
| sky_top / sky_left ratio | 168.5 / 0.922 | 165.7 / 1.170 | 149-182, 1.05-1.29 |

**Read the attic row: R matches the photo to one unit and G to seven; the whole chroma deficit is 35 units of excess
BLUE.** That is what round 08b and round 09 were chasing with sky strength, sun colour and the AgX look.

### The finding: at 197.5 the sunlit stone is on the AgX shoulder, where chroma cannot exist

Sixteen rigs were swept at 960x540 / 48 spp (r09 established the resolution offset is ~+1 R-B, and the r10 control
reproduced it: 199.3 at 960x540 against 197.5 at 1920x1080). Every colour knob is nearly dead:

| lever | attic R-B | note |
|---|---|---|
| control (bias 1.75, sky 0.80, sun blue 0.75, High Contrast) | 101.3 | |
| sun blue 0.75 -> 0.35 (a 32 % cut of the blue *irradiance*) | 105.2 | display blue moved 3 units |
| sky strength 0.80 -> 1.60 (visible sky held) | 103.3 | and the shade got 2 deg **warmer** |
| aerosol 1.6 -> 8 | 98.1 | worse: the sky brightens faster than the sun |
| aerosol 8 + ozone 0.6 | 103.2 | |
| diffuse sky saturation x2 / x3 | 126.0 / 126.7 | at -0.5 EV; see the shade section |
| **exposure bias 1.75 -> 1.25 (-0.5 EV)** | **123.0** | saturation 0.433 -> 0.554 |
| exposure -1.0 EV | 150.2 | luminance 161.6, out of the window |
| "AgX - Punchy" | 110.5 | luminance 159.1, still out of the window: rejected a third time |

Materials measured that a 44 % albedo-blue cut moved display blue 3 %, and concluded "AgX's inset makes ~77 % of
display blue leakage from R and G". Round 10 measures the same wall from the light side — a 32 % cut of blue
irradiance moves display blue 3 units — and finds the way round it: **the leakage is a property of where the pixel
sits on the AgX curve, so the lever is not the blue, it is the luminance.** Bringing the sunlit stone down half a
stop takes it off the shoulder and the chroma comes back on its own.

QA-03 closed QA-02-4 and told lighting not to move the exposure again. That reading was taken on a master still
rendering at "AgX - Base Contrast" (the round-09 look bug) and before materials r4; on the rebuilt master the same
box reads 197.5 against 189.6, i.e. 1.04x the photo and 19 units above QA's own floor. **The +0.9 EV bought in round
08 was paying for albedo that materials has since supplied, and giving it back is the correct move, not a new art
bias.** The visible sky and the lagoon's reflection are held still through the camera / glossy boosts, so this is a
stone exposure change, not a global one.

### Shipped (`scripts/light_build.py`, `assets/lighting.blend` rebuilt, exposure -4.083 + 1.25 = **-2.833 EV**)

| constant | round 09 | round 10 | why |
|---|---|---|---|
| `EXPOSURE_BIAS` | 1.75 | **1.25** | the half stop above |
| `SKY_CAMERA_BOOST` | 1.50 | **2.10** | 1.50 x 2^0.5: holds the visible sky at sky_top 168.8 (it was 168.5) |
| `SKY_GLOSSY_BOOST` | 3.75 | **5.25** | same hold for the lagoon's reflection of the sky |
| `SKY_GLOSSY_SATURATION` | (shared 1.20) | **0.90** | new socket, QA-03-7; see below |
| `SKY_DIFFUSE_SATURATION` | — | 1.00 | new socket, left physical; swept and rejected |
| `SKY_STRENGTH`, `SKY`, `SUN_BLUE_MULT`, `LOOK` | | unchanged | 0.80 / aerosol 1.6, ozone 2.0 / 0.75 / High Contrast |

`light_calibrate.make_sky_world` now takes three independent saturations chained on the sky colour — DIFFUSE (the
light that lands on shaded stone), CAMERA (the visible sky) and GLOSSY (the sky the lagoon mirrors) — each selected
by its own Light Path socket. Camera and glossy shared one knob before.

### Verified at delivery resolution (cam01, Cycles 1920x1080 / 64 spp, `r10fhero_SHIP.png`)

| | before | **after** | ref 169 | verdict |
|---|---|---|---|---|
| sunlit attic sRGB | 232,194,130 | **220,178,99** | 231,187,95 | blue 130 -> 99 against 95 |
| attic saturation | 0.441 | **0.549** | 0.588 | PASS (>= 0.53) |
| attic R-B | 102.3 | **120.8** | 136.1 | PASS (>= 120) |
| attic luminance | 197.5 | **180.9** | 189.6 | PASS (0.954x, window 178.2-201.0) |
| attic hue | 37.7 | 38.8 | 40.3 | |
| shaded attic lum | 130.6 | **113.0** | 115.0 | 0.98x |
| shaded attic hue | 42.5 | 42.9 | 29.5 | **FAIL, and not lighting's — see below** |
| columns (QA mask) | 152.0 | **123.9** | 95.8 | 1.59x -> **1.29x**, 51 % of the excess removed |
| near water sat | 0.487 | **0.270** | 0.270 | PASS (window 0.22-0.32), exact |
| near water hue | 204.8 | 208.7 | 192.1 | **FAIL, and not lighting's — see below** |
| sky_top | 168.5 | **168.8** | 165.7 | PASS (window 149-182) |
| sky_left/sky_top | 0.922 | 0.922 | 1.170 | **FAIL — see item 4** |
| water reflection lum | 153.4 | 145.9 | 168.9 | still ~0.2 EV dark |

**Items 1 and 2 of the brief are met on every number lighting owns; item 3's saturation is met exactly.**

### QA-03-7 / item 3: the near-water saturation is the GLOSSY sky socket, and the hue is not the sky

At grazing angles the lagoon is a Fresnel mirror of the horizon sky, so the near-water chroma is the sky's chroma on
the glossy path — and materials had already measured that murk, tint and transmission do nothing there. Splitting the
saturation socket makes it a one-knob fix. cam01, near-water box, ref 169 = 0.270:

| `SKY_GLOSSY_SATURATION` | 1.20 (shared) | 0.90 | 0.85 | 0.70 | 0.45 |
|---|---|---|---|---|---|
| near-water saturation | 0.525 | **0.270** | 0.243 | 0.173 | 0.086 |

The remaining 17 deg of **hue** (208.7 against ref 192.1) is **environment's, and the measurement proves it**: the
visible sky's own hue in the render is **208.7 against ref 169's 208.2**, i.e. exact. In the photograph the water is
16 deg greener than the sky it mirrors; in the render it is the same colour as the sky. That difference is the
lagoon's own upwelling green, i.e. the water shader's diffuse/volume term, not the sky.

### Item 1's other half: the shaded stone's hue is materials', with a number

The shaded attic needs 36 more units of blue (39 against ref 169's 81) at an R and G that already match. Two lighting
attacks, both measured, both null:

* `SKY_DIFFUSE_SATURATION` 1.0 -> 2.0 -> 3.0 (the sky made bluer for diffuse rays only, at constant peak):
  shaded attic 142,112,36 -> 136,107,35 -> 135,107,34. **One unit of blue out of the 36 needed.**
* `SKY_STRENGTH` 0.80 -> 1.60 with the visible sky held: shade hue 42.9 -> 45.0, i.e. **warmer**, because more sky
  also lights the sunlit plaza and comes back as warm bounce.

So **more than 97 % of the light on the shaded stone is warm interreflection off the sunlit stone and ground, not
sky, and no sky colour can reach it.** The photo drops 11 deg of hue from sun to shade (40.3 -> 29.5); we rise 4 deg
(38.8 -> 42.9). Since the *sunlit* hue now matches the photo to 1.5 deg, the shade's 13 deg is the stone's blue
reflectance in shadow — a materials/albedo job (it is the same albedo-chroma finding as QA-02-14). **Handed to
materials with these numbers.**

### Item 4: the horizon haze band — the sky model tops out at 0.965 and part of the gap is the boxes

sky_left / sky_top, ref 169 = 1.170, render = 0.922. Every atmosphere in the sweep, at matched sky_top:

| aerosol | ozone | air | sky_left/sky_top | cost |
|---|---|---|---|---|
| 1.6 (shipped) | 2.0 | 1.0 | 0.922 | — |
| 4 | 2.0 | 1.0 | 0.943 | attic R-B -0.9, shade +3.8, columns +9.5 |
| 8 | 2.0 | 1.0 | 0.965 | attic R-B -3.2, shade +13, lamp 67.3 -> 33.5 W/m2 |
| 8 | 2.0 | 1.5 | 0.965 | shade +22 |
| 10 | 0.6 | 1.5 | 0.964 | attic hue -6, shade +21 |

**The ratio saturates at ~0.965 and cannot reach 1.05.** Two reasons, and the second one matters for how QA reads it:
(1) raising aerosol brightens the *whole* sky, so the gradient hardly changes once the camera boost is pulled back to
hold sky_top; (2) **the two boxes are not at the same elevation in the two framings.** The render's horizon sits at
y ~0.63 of frame and the photo's at ~0.54, so `sky_left` (y 0.085-0.145) sits 0.82 of the way from horizon to frame
top in the render and 0.67 in the photo — the photo's box is simply lower in the sky, where any clear sky is
brighter. Some part of the 1.170 is framing, not haze. **Not shipped: the 0.02-0.04 of ratio that aerosol 4-8 buys
costs the two numbers that were the round's blockers.** If the lead wants the band as an art bias, the cheapest
honest route is a compositor sky gradient, which was not attempted.

### Item 6: Eevee vs Cycles on the rotunda ceiling — it was never the 45 deg spread

Round 09 concluded Eevee was ignoring the emitters' spread. It is not, and two measurements kill that story:

* switching the eight vault emitters **off** and clamping them with a 13 m cutoff give the *same* Eevee coffer ratio,
  so they are not what lights it;
* **the identical file renders the Eevee coffer at 0.246 (960x540) and 1.075 (1280x720).** No real light does that.

It is Eevee Next's screen-traced ambient term filling the closed vault volume in proportion to how much of the vault
is on screen, and cam04 looks straight up into it. Turning Fast GI off, or dropping `fast_gi_distance` 60 -> 10 m,
moves the coffer by less than 0.05 (1.075 -> 1.033 / 1.076), so it is the screen-space trace itself. Cycles has no
such term, and no single rig satisfies both engines.

The engine-conditional fix is `cutoff_distance` (Blender's "Custom Distance"), which **Eevee honours and Cycles
ignores**: at 13 m each vault emitter still reaches its own soffit (4.5-11 m) but not the coffered dome 20.7 m away.
cam04, 1280x720, Eevee (Cycles target: soffit 0.536, coffer 0.364; QA's window is +-0.15):

| Eevee rig | soffit/own-sky | coffer/own-sky |
|---|---|---|
| as shipped in round 09 | 0.375 (-0.161) | **1.075 (+0.711)** |
| cutoff 13 m | 0.145 | 0.246 |
| cutoff 13 m, energy x2 | 0.201 | 0.247 |
| cutoff 16 m, energy x5 | 0.348 | 0.255 |
| **cutoff 13 m, energy x8** | **0.408 (-0.128)** | **0.255 (-0.109)** |

**Shipped in `light_presets.apply_vault_for_engine`, called from `apply_final_cycles` ("CYCLES", restores the
physical energy from the light object's new `energy_W` custom property) and from both Eevee presets ("EEVEE", x8 and
a 13 m cutoff). Both ratios are now inside 0.15 of Cycles; the defect is closed in the engine QA previews with.**
Cost on record: Eevee's soffit W/E balance is 0.562 / 0.253 where Cycles reads 0.395 / 0.678, i.e. the engines now
lean opposite ways across the vault; and `scripts/lead_build.sh` bakes the Eevee irradiance volumes, so the bake
should be taken after whichever preset the lead wants the baked term to match (the direct term is retuned at render
time either way).

### Item 5 (cam06 far-field contrast): measured, not touched

The merged master reads dome / far-shore **1.22:1** (`env_cam06_audit.py`, Eevee, 1920x1080 downscaled), against
environment's reported 1.45:1 and QA's 1.5:1 target. It was left alone deliberately: the compositor haze colour is
(5.32, 3.74, 1.96) scene units against a far shore at ~127 display, i.e. **the haze is brighter than the thing it
veils, so every increase in mist density lowers this contrast rather than raising it** — which is also what round 08
measured when it turned the haze off entirely and the contrast moved 1.08 -> 1.08. The remaining lever is the haze
COLOUR (a darker, cooler veil), which trades against the warm aerial perspective QA-02-8 asked for. Lighting has no
knob here that does not undo an accepted defect; this is environment's far-field albedo/value range.

### Open, and for whom

* **shaded stone hue 42.9 vs 29.5 (13 deg) — materials.** Sky colour cannot reach it (1 unit of blue out of 36).
* **near-water hue 208.7 vs 192.1 (17 deg) — environment.** The render's sky hue matches the photo's exactly
  (208.7 vs 208.2); the photo's water is 16 deg greener than its own sky.
* **sky_left/sky_top 0.922 vs 1.170 — open, partly a box-placement artifact.** The physical sky tops out at 0.965.
* **columns 1.29x ref** (was 1.59x). The rest is albedo and self-shadowing contrast, not level: QA measured the
  render's entablature luminance sd at 28 against the photo's 64.
* **water reflection 145.9 vs 168.9** (~0.2 EV dark) — carried over from round 09, not chased.
* cam06 far-field contrast 1.22:1 — environment (above).

### Item 7 (QA-03-16): the 4K timing test — ABORTED at the 60-minute limit, twice, and that is itself the result

`blender -b --python scripts/light_r10_sweep.py -- --res 3840 2160 --samples 768 --timelimit 3600 --hero "tag=SHIP4K"`
(the shipped round-10 rig, `apply_final_cycles`, `cycles.time_limit = 3600 s`).

* Attempt 1 was killed at 24 min: the environment agent's r5 chain had the Metal GPU and my process had gained
  0.04 s of CPU in 45 s. One GPU, two agents.
* Attempt 2 ran on a free GPU for **1 h 32 min** and never wrote a frame. Its resident set dropped 1.76 GB -> 0.88 GB
  at ~70 min (the render buffers being released) and its CPU time then flatlined at 1 s per 20 min, so it was past
  the sampling stage and stuck in the tail — most likely the 3840x2160 compositor pass (`COMP_golden_hour` +
  Mist + Depth) rather than Cycles itself. Killed per the brief's 60-minute rule.
* **The sample count reached is not recoverable**: Blender writes background render progress to a carriage-return
  stream that the redirected log does not capture. Anyone repeating this should add `--log-level 1` or write the
  frame with `cycles.use_progressive_refine` off and poll `bpy.app.timers`, and should render the 4K frame with the
  compositor DISABLED first to separate the two costs.

What is measured and reliable: **cam01 at 1920x1080 / 64 spp takes 173 s on a quiet GPU and 205-256 s on a shared
one** (five renders this round). Pure resolution scaling to 3840x2160 is 4x = ~690 s at 64 spp; `FINAL_SAMPLES = 768`
is 12x that sample count before adaptive sampling claws any of it back. **The brief's "4K frame in under ~2 h"
is not demonstrated, and `FINAL_SAMPLES = 768` should be treated as unvalidated at 4K until someone lands this
test.** Recommendation to the lead: re-run it with the compositor off to isolate the cost, and if the compositor is
the tail, either bake the haze into the world/volume or run the compositor as a separate pass on the saved EXR.

## 20. Round 11 — the shade (QA-04-2), the Eevee vault (QA-04-1) and the coffer level (QA-04-7)

Brief: the lead's round-11 dispatch. Every number below is measured with `scripts/light_r11_measure.py`, which
reproduces QA's round-04 numbers on QA's own frames to the second decimal before anything is changed:

| | QA round 04 | light_r11_measure on the same file |
|---|---|---|
| cam03 near shaft (0,150)-(420,720) | 7.3 | **7.25** |
| cam03 ground (420,560)-(900,720) | 21.2 | **21.23** |
| cam04 Eevee coffer / own sky | 0.035 | **0.034** |
| cam04 Eevee soffit E / own sky | 0.14 | **0.142** |
| cam04 Cycles soffit W / E, coffer | 0.29 / 0.52, 0.26 | **0.289 / 0.522, 0.261** |

so the round is arguing with QA's arithmetic, not around it.

### 20.1 QA-04-2 — where the shade actually went, and why the obvious lever is the wrong one

**First: cam03 is not an Eevee defect.** The same frame in Cycles at the same resolution reads the near shaft at
**4.62**, i.e. *darker* than Eevee's 7.23. Whatever is wrong is in the rig, not in Eevee's ambient term.

**Second: the colonnade shade is sky-dominated, and the shaded attic is not.** Rendering the sun lamp and the sky
separately on cam03 (Cycles 1280x720 / 64 spp, `--case "sm=0"` / `"wm=0"`):

| cam03 | near shaft | ground |
|---|---|---|
| sky alone (sun lamp off) | 3.26 | 14.29 |
| sun alone (world off) | 0.50 | 4.93 |
| both (shipped) | 4.62 | 23.64 |

Round 10 measured the *hero's shaded attic* and found >97 % of its light was warm interreflection; that finding does
not transfer to the colonnade, where ~70 % of the shade is sky. So the sky IS the lever on cam03 — and it still
cannot be used, because of what it costs on the hero.

**`SKY_DIFFUSE_BOOST` — the new socket the brief asked for first, built, measured, and shipped at 1.00.**
`light_calibrate.make_sky_world` now takes a fourth per-ray gain: `gain = diffuse_boost + is_camera*(cb - db) +
is_glossy*(gb - db)`, so the sky can be raised for the light that lands on shaded stone while the visible sky and the
lagoon's reflection are held exactly still by their own sockets. Cycles, the lead's merged master, cam03 at
1280x720 and cam01 at 1920x1080 / 64 spp:

| diffuse boost | cam03 shaft | cam03 ground | attic sat | attic R-B | attic lum | shade hue | columns |
|---|---|---|---|---|---|---|---|
| **1.0 (shipped)** | 4.6 | 23.6 | **0.554** | **122** | 180.4 | 43.1 | 1.27x |
| 2.0 | 9.1 | 34.6 | 0.502 | 112.3 | 187.7 | **44.8** | 1.47x |
| 4.0 | 17.9 | 53.8 | 0.423 | 96.9 | 198.8 | **47.4** | 1.58x |

Two independent reasons to reject it, and the second one is the interesting one. (1) The brief's budget was 0.02
saturation and 5 R-B; a boost of 2 costs **0.052 and 9.7** and pushes the columns from 1.27x to 1.47x of ref, i.e. it
re-opens QA-04-5 as well. (2) It drives the shaded attic's hue the **wrong way** — 43.1 -> 44.8 -> 47.4 against a
target of 29.5 — because most of the extra sky lands on the sunlit plaza and comes back as warm bounce. More sky
makes the shade warmer. That is the same wall round 10 hit from the saturation side, measured from the level side.

### 20.2 QA-04-6 — the sun angle is right; the wings are a LEVEL error, not a shadow-geometry error

QA asked lighting to check the sun elevation / azimuth against the shadow edges in ref 169 **before** touching any
fill, and it is a fair thing to ask: a mean cannot tell a shadow that is in the wrong place from stone that is simply
too dark. `light_r11_measure.py --wings` separates them. Take the horizontal luminance profile of each wing band in
the render and in ref 169 warped into the render frame (QA's own aligned panel), normalise both to zero mean and unit
variance, and find the pixel shift that maximises their correlation. A wrong azimuth slides every shadow boundary
along the wing, so it shows up as a large shift **in the same direction on both wings**.

| band (1920x1080) | render | ref 169 aligned | ratio | corr at 0 px | best corr | best shift |
|---|---|---|---|---|---|---|
| north wing 60,480-560,600 | 82.6 (sd 18.1) | 107.3 (sd 29.2) | **0.77** | +0.319 | +0.337 | **-3 px** |
| south wing 1360,480-1860,600 | 81.7 (sd 38.1) | 133.6 (sd 41.5) | **0.61** | +0.261 | +0.441 | **-25 px** |

The north wing's shadow structure lands within **3 px out of a 500 px band** of the photo's, and the two wings
disagree on the sign and size of their residual shift (-3 vs -25). A sun-azimuth error cannot do that: it would move
both bands the same way by a similar amount. **The solar position (az 118.5, el 7.4, NOAA for 2026-11-10 07:30 PST)
is confirmed against the photo's own shadows and is not touched this round.** The south wing also carries almost the
photo's full amount of structure (sd 38.1 against 41.5) at 0.61 of its level, which is the signature of correct
shadows on stone that is too dark — albedo and wing-shading trees, i.e. materials and environment, exactly as the
lead split it. Lighting's only level knob here is the exposure, and the exposure is pinned by the sunlit attic
(0.954x of ref 169, and QA-04-2 exists because round 10 already spent half a stop).

### 20.3 QA-04-1 — the Eevee vault was black because `lead_build.sh` bakes the Eevee HACK into the light probes

Round 10 shipped an engine-conditional vault rig: Eevee gets the eight vault emitters at x8 energy with a 13 m
`cutoff_distance` (which Eevee honours and Cycles ignores), Cycles keeps the physical energy. Measured then, on
cam04 at 1280x720, that gave Eevee soffit 0.408 / coffer 0.255 against Cycles 0.536 / 0.364 — both inside 0.15.
QA round 04 measured the same override, on the same camera, at the same resolution, through the same
`apply_preview_eevee`, and got soffit W 0.399 / E 0.142 and **coffer 0.034**. The log line even confirms the override
ran. The soffit reproduced round 10's number and the coffer fell by a factor of 7.5.

**What changed between the two measurements is not the rig, it is the BAKE.** The lead's review fix put
`light_presets.apply_viewport_eevee` at the end of `build_master.py` so the saved Eevee state carries the vault
override — correct in itself — and `scripts/lead_build.sh` then runs `light_probes.py --bake` on that saved state.
So the two irradiance volumes were baked with the vault emitters **cut off at 13 m**, and the central coffered dome
is 20.7 m from them. The coffers are therefore starved in the baked *indirect* term as well as in the direct one,
and nothing is left to light them. Round 10's probe was taken before that review fix, i.e. on a bake made with the
uncut rig, which is exactly why its coffer read 0.255 and why "switching the emitters off changes nothing" was true
then: the bake was doing the work.

This also retires round 10's story that Eevee's screen-traced ambient is what fills the vault. The screen trace has
no light of its own; where a screen ray misses it falls back on the irradiance volume, so the resolution dependence
round 10 measured (0.246 at 960x540, 1.075 at 1280x720) was the *bake* being sampled more or less, not an
independent ambient source.

**Fix, in `scripts/light_probes.py` (`bake(..., physical_vault=True)`): the bake now forces the PHYSICAL vault rig,
bakes, and restores whatever override was live, so the saved Eevee state is unchanged.** A light probe volume is
meant to hold the scene's real indirect light; baking a render-time engine hack into it was a bug, and the fix is
one that cannot be undone by the order in which the lead runs his two commands.

### 20.4 QA-04-2 — what CAN reach the shade: `SHADE_FILL`, and what cannot

If the sky cannot be raised without paying for it on the sunlit stone, the fill has to be light that reaches the
anti-sun faces and nothing else. `SHADE_FILL` (new in `light_build.py`) is three wide-angle SUN lamps on the
anti-sun hemisphere — az 300 / 205 / 25 at elevation 16 / 16 / 20 deg, weights 1.0 / 1.0 / 0.7, colour (0.42, 0.62,
1.00) i.e. clear-sky blue, `angle` 55 deg so the shadows are sky-soft, `specular_factor` 0.10 so it stays out of the
lagoon's reflection and off the column highlights (QA-03-7 and QA-04-5 are both glossy-side defects), and
`visible_camera = False` so a 55 deg disc never appears in the sky.

A sun lamp is the right primitive here for three reasons: its energy IS an irradiance in W/m2, directly comparable
with the calibrated 67.3 W/m2 of the real sun, so the fill can be quoted as a fraction of the sun rather than as a
magic number; it is occluded by the building exactly the way the sky is, so it can never leak through a wall; and it
costs almost nothing to sample. The lamps sit LOW on purpose: a low fill rakes vertical shaded faces, where the
defect is, and lands on the horizontal plaza at cos(el) ~ 0.3, so it adds little of the warm ground bounce that made
`SKY_DIFFUSE_BOOST` fail.

**The one thing it cannot fix is cam03's near shaft, and the measurement says why.** Eevee, cam03, 1280x720, total
fill irradiance swept:

| SHADE_FILL total | near shaft | ground |
|---|---|---|
| 0 (round 10) | 7.23 | 18.5 |
| 3 W/m2 | 7.69 | 18.8 |
| 6 W/m2 | 8.29 | 23.2 |
| 12 W/m2 (18 % of the sun) | 9.09 | 27.4 |

The walkway floor responds (18.5 -> 27.4, +48 %) and the shaft does not (7.23 -> 9.09, +26 % for 4x the fill). QA's
box (0,150)-(420,720) is the column standing 3 m from an 18 mm lens: it is occluded from the whole sky by the
columns and entablature around it, which is also why the sky-only render put only 3.26 there. **No exterior light
can reach it, in either engine, and that is a geometry fact, not a rig setting.**

**And QA's target for it is a midday photograph.** ref 128 has a blown white sky, no cast shadows anywhere in frame
and near-vertical light; its 69.7 is the shade level of a colonnade under a high sun. Our sun is 7.4 deg above the
horizon by the lead's own decision, and the frame's whole point is the long raking light. 0.5 of ref 128 is not a
golden-hour number. What round 11 does deliver on cam03 is the *ground* and the *hue*, and that is stated as a
partial in the report rather than dressed up as a pass.

**And the fill's cost, measured on the hero (Cycles 1920x1080 / 64 spp), is why it ships small.** The control row
reproduces the lead's merged master to 0.5 R-B and 0.002 saturation, so the sweep and QA are measuring the same
pixels:

| SHADE_FILL (el 16 deg) | attic sat | attic R-B | **shaded attic hue** | shaded lum | columns | near-water sat |
|---|---|---|---|---|---|---|
| control (= master) | 0.556 | 122.4 | **43.1** | 112.2 | 1.29x | 0.274 |
| 6 W/m2 | 0.544 | 119.9 | **44.4** | 120.8 | 1.37x | 0.207 |
| 14 W/m2 | 0.528 | 116.7 | **45.9** | 130.8 | 1.40x | 0.165 |

The sunlit stone holds up well (the budget was 0.02 sat / 5 R-B and 6 W/m2 costs 0.012 / 2.5, exactly as designed —
the fill is behind the sunlit faces). Everything else says no:

* **the shaded attic gets WARMER again**, 43.1 -> 44.4 -> 45.9, and this is the finding of the round. A blue light
  on ochre stone does not make blue stone: at 6 W/m2 the shaded attic's blue rises 37 -> 44 (+7) but its green rises
  111 -> 121 (+10), because the fill's own green is 0.62 of its blue AND because the fill lands on the plaza and
  comes back warm. Hue is (G-B)/(R-B): green wins, so hue rises. **Three independent levers now say the same thing
  — round 10's `SKY_DIFFUSE_SATURATION` (1 unit of blue out of 36), round 11's `SKY_DIFFUSE_BOOST` (+4.3 deg the
  wrong way) and round 11's directional cool fill (+2.8 deg the wrong way). The shaded stone's hue is its albedo's
  blue reflectance in shadow, it is materials', and lighting has now proved it from the level side, the saturation
  side and the direction side.**
* at elevation 16 deg the fill also lands on the water at sin(16) = 0.28 and takes the near-water saturation from
  0.274 (dead centre of QA's 0.22-0.32 window, the one number round 10 hit exactly) to 0.207 at 6 W/m2, and it pushes
  the columns from 1.29x to 1.37x of ref, i.e. it re-opens QA-03-7 and worsens QA-04-5 to buy shade luminance.

### 20.5 QA-04-7 — the Cycles coffer level: the -0.5 EV of round 10 cost the interior fills a factor of 3

Round 09 shipped `FILL 1140 W` / `VAULT_FILL 3960 W` and measured coffer / own sky 0.384 at the round-09 exposure.
Round 10 took half a stop out of the whole frame and did not re-tune the interior, so the same rig now reads 0.261,
i.e. the exposure move cost 0.12 of ratio and dropped the coffer field out of QA's 0.35-0.55 window while leaving the
soffit mean at 0.405, exactly ref 083's. Cycles, cam04, 960x540 / 48 spp (r09 established that these ratios move
< 0.01 with resolution):

| FILL x | VAULT x | soffit W | soffit E | soffit mean | coffer / sky |
|---|---|---|---|---|---|
| 1.0 (round 10) | 1.0 | 0.289 | 0.522 | **0.405** | **0.261** |
| 1.8 | 1.0 | 0.301 | 0.537 | 0.419 | 0.310 |
| 2.6 | 1.0 | 0.319 | 0.553 | 0.436 | 0.360 |
| 2.6 | 0.8 | 0.278 | 0.482 | 0.380 | 0.341 |

Both knobs are linear over this range and they separate cleanly: +1.0 of FILL is worth +0.062 coffer and only
+0.019 soffit (the central disk is the emitter the coffers see best), while VAULT trades 0.28 of soffit for 0.095 of
coffer per unit. Shipped **FILL 1140 -> 3648 W (x3.2) and VAULT_FILL 3960 -> 3564 W (x0.9)**, which puts the coffer
in the middle of QA's window instead of on its edge and keeps the soffit mean within 4 % of ref 083. The x3.2 is not
a new art bias: it is the factor round 10's exposure change removed and never gave back.

### 20.6 QA-04-1 result — the bake fix on its own restores the coffers by a factor of 7

Everything below is cam04 at **1280x720** (Eevee's vault reading is resolution-sensitive, so it is measured at QA's
resolution, not at the sweep resolution), with the round-11 interior fills (FILL x3.2, VAULT x0.9) and the probe
volumes re-baked **in memory on the physical rig** by `light_r11_sweep.py --rebake CYCLES`:

| Eevee vault override | soffit W | soffit E | soffit mean | coffer / own sky |
|---|---|---|---|---|
| **round 10's x8 + 13 m, baked WITH the cutoff (what QA measured)** | 0.399 | **0.142** | 0.270 | **0.034** |
| x8 + 13 m, baked on the physical rig | 0.428 | 0.194 | 0.311 | **0.240** |
| x4 + 25 m | 0.459 | 0.375 | 0.417 | 0.611 |
| x2 + 45 m | 0.443 | 0.392 | 0.418 | 1.145 |
| x1, no cutoff (physical) | 0.293 | 0.276 | 0.284 | 0.839 |

**Changing nothing but the bake takes the coffer field from 0.034 to 0.240 — a factor of 7 — with the identical
render-time rig.** That is the proof of the diagnosis in 20.3: the coffers were dark because the light that should
have been in the baked irradiance volume was never put there.

It also shows the cutoff is doing far more than round 10 thought. Between 13 m and 25 m the coffer jumps 0.240 ->
0.611, i.e. the emitters reach the central dome as soon as they are allowed to, and the Eevee soffit E follows the
same knob (0.194 -> 0.375). The two numbers QA measures therefore move together and the tuning is one-dimensional.

### 20.7 QA-04-7 CLOSED in Cycles, and what the Eevee vault can and cannot be made to match

Verified at QA's own resolution (cam04, 1280x720, Cycles 64 spp, `r11j_SHIP_e8cut18_04c.png`), with the round-11
interior fills:

| | round 04 | **round 11** | ref 083 | QA's window |
|---|---|---|---|---|
| soffit W / own sky | 0.289 | **0.316** | 0.38 | — |
| soffit E / own sky | 0.522 | **0.532** | 0.43 | — |
| soffit mean | 0.405 | **0.424** | **0.405** | within 4 % |
| coffer field / own sky | **0.261** | **0.387** | 0.437 | **0.35-0.55 PASS** |

**The Eevee side is a double-count, and that is a better story than round 10's.** With the probe volumes baked on the
physical rig, the baked irradiance already contains the vault emitters' light — and Eevee then adds their *direct*
light on top of it, while Cycles path-traces the whole thing once. That is why Eevee with no cutoff and the plain
physical energy (x1) puts the coffer at **0.839** where Cycles reads 0.387: it is counting the same emitters twice.
The `cutoff_distance` override is therefore not a fudge for a missing ambient term (round 10's reading) but the
removal of a duplicate: at 13-21 m each emitter still lights its own soffit (4.5-11 m) and stops double-counting into
the coffered dome 20.7 m away, leaving the coffer to the bake alone at 0.24-0.25.

What that leaves unreachable is the soffit **W/E split**. Cycles reads E much brighter than W (0.532 / 0.316) and
Eevee reads the opposite (0.23 / 0.47) at every cutoff that keeps the coffer honest; opening the cutoff to 25-45 m
brings Eevee's E up to 0.375-0.392 but takes the coffer to 0.611-1.145, i.e. it buys the split by re-opening the
double-count. The soffit **mean** and the coffer field — the two numbers ref 083 is quoted on and the two QA
tabulates a window for — are what round 11 lands.

**Shipped Eevee override: `EEVEE_VAULT` x8 / 13 m -> `x6 / 21 m`.** Against the round-11 Cycles frame (soffit W
0.316 / E 0.532 / mean 0.424, coffer 0.387), on QA's 0.15 box:

| | round 04 (what QA measured) | **round 11** | Cycles | gap before -> after |
|---|---|---|---|---|
| coffer field / own sky | 0.034 | **0.325** | 0.387 | 0.227 -> **0.062** |
| soffit E / own sky | 0.142 | **0.419** | 0.532 | 0.380 -> **0.113** |
| soffit mean | 0.270 | **0.483** | 0.424 | 0.135 -> **0.059** |
| soffit W / own sky | 0.399 | 0.546 | 0.316 | 0.110 -> **0.230 (COST)** |

Both numbers QA flagged land inside the box, and so does the soffit mean. The soffit W is the price and it is
stated as such: W and E move together in Eevee at every cutoff tried (x3/25 m gives 0.382 / 0.320, x6/21 m gives
0.546 / 0.419) while Cycles wants them 0.22 apart in the other direction, so no single override lands all three.

### 20.8 QA-04-12 — the decision, and the reason it is not the one the question implied

QA asked whether the saved Eevee viewport state (taa 8/16, **raytracing off**) was intended, and the lead's brief
asked lighting to decide whether the viewport preset should carry raytracing on, "since Eevee's screen-traced ambient
is likely what lights the vault". **It is not.** Measured on cam04 at 1280x720 with the round-11 rig and a physical
bake, turning raytracing ON in `apply_viewport_eevee` moved the coffer field **0.218 -> 0.218** and the soffit E
0.084 -> 0.089. Nothing. Round 10's "screen-traced ambient" story does not survive a correct bake.

The real difference between the two Eevee presets was **`light_threshold`**: 0.05 in the viewport preset against 0.01
in the preview preset. At 0.05 Eevee culls the eight vault emitters wherever their estimated contribution is small,
which is precisely the coffered dome. cam04, 1280x720:

| viewport preset | soffit W | soffit E | coffer / own sky | frame |
|---|---|---|---|---|
| as saved (rt off, threshold 0.05) | 0.315 | 0.084 | **0.218** | 12.2 s |
| rt on, threshold 0.05 | 0.315 | 0.089 | **0.218** | 11.2 s |
| **rt on, threshold 0.01 (shipped)** | 0.345 | 0.132 | **0.320** | 24.2 s |
| `apply_preview_eevee` for comparison | 0.546 | 0.419 | 0.325 | — |
| Cycles ground truth | 0.316 | 0.532 | 0.387 | — |

**Decision (for docs/decisions.md), CORRECTED after the round-11 code review: raytracing stays OFF in
`apply_viewport_eevee`; the fix is `light_threshold` 0.05 -> 0.01.** The first version of this section turned
raytracing on and credited it with the vault, which contradicts the measurement three lines above it; the reviewer
caught the contradiction and the measurement wins. Raytracing buys the viewport nothing on the ceiling and this
preset exists to be fast, so it goes back to off (`apply_preview_eevee` keeps it on — the QA previews need
screen-space reflections in the lagoon). Verified on the saved file with the shipped preset:

| viewport preset, cam04 1280x720 | soffit W | soffit E | coffer / own sky | frame |
|---|---|---|---|---|
| threshold 0.05, rt off (round 10) | 0.315 | 0.084 | **0.218** | 12.2 s |
| threshold 0.05, rt on | 0.315 | 0.089 | **0.218** | 11.2 s |
| **threshold 0.01, rt off (SHIPPED)** | 0.334 | 0.124 | **0.319** | **7.9 s** |
| `apply_preview_eevee` for comparison | 0.546 | 0.419 | 0.325 | — |
| Cycles ground truth | 0.316 | 0.532 | 0.387 | — |

The viewport coffer lands within 0.068 of Cycles and level with the preview preset's 0.325, so the ceiling is
readable when a viewport user flies under it, and the preset got *faster* rather than slower. taa 8 / 16 is kept.
Also `shadow_pool_size` 256 -> 512 in the viewport preset and 512 -> 1024 in the preview preset: the QA previews
were logging "Shadow buffer full (2118 / 2048)" on **every** frame, i.e. Eevee was silently dropping shadow pages.
Each pool assignment now sits in its own try/except that prints (they shared one block, so a rejected enum would
have silently skipped the irradiance-pool assignment too and left the baked volumes unused).

### 20.8b Review fixes, and the bake save sequence proved on a copy of master

`scripts/light_r11_verify.py` runs the real `lead_build.sh` sequence on a COPY of master.blend and prints the vault
state at each step (never touching the lead's file). On the lead's current master:

| step | engine | vault energy | `energy_W` | cutoff |
|---|---|---|---|---|
| as opened (what `build_master.py` leaves) | BLENDER_EEVEE | 31680 W | 3960 | on @ 13 m |
| after `light_probes.bake()` | BLENDER_EEVEE | 23760 W | 3960 | on @ 21 m |
| after save + reopen | BLENDER_EEVEE | 23760 W | 3960 | on @ 21 m |

i.e. the engine comes back, the Eevee override is what gets saved, and the physical energy survives untouched in
`energy_W` (3960 here because that master predates the round-11 lighting.blend; the script says so). The bake itself
costs **3.5 s**, so re-running it is free. The other review fixes: the probe-less early-out now happens *before* the
vault is switched and the restore is in a `finally`, so a master with no light probes can no longer be saved holding
the physical rig; the engine to restore is captured before anything forces BLENDER_EEVEE; `build_shade_fill` returns
early at 0 W/m2 so three shadow-casting suns no longer ship for no light; `light_r11_sweep` honours
`$PFA_MAIN_ROOT` and rebuilds `SHADE_FILL` from a pristine copy each case; and the round's intermediate previews are
down from 127 MB to 5.4 MB (the four sheet inputs, re-encoded 8-bit, plus the sheet).

### 20.9 QA-04-5 and QA-04-9 — measured, and no knob without a bigger cost

**QA-04-5, the columns.** The shipped round-11 hero measures the QA mask at **123.7** against a test of <= 120
(ref 95.8), i.e. it misses by 3 %, and the round-04 render of the *same rig* measured 122.0: the defect is inside
the run-to-run spread of its own threshold. Everything lighting can do to it makes something else worse — the shade
fill pushed it to 1.35-1.40x, and the only remaining lever, `SKY_GLOSSY_BOOST`, is what holds the lagoon's
reflection, which is already 0.86x of ref 169 (146.2 against 168.9). QA's own round-04 measurement of the render's
entablature luminance sd (28 against the photo's 64) says what is left is surface contrast, not level. **Materials.**

**QA-04-9, the horizon haze band.** sky_left / sky_top is **0.922** against a 1.05-1.29 window, unchanged, and
round 10 established why with a five-row atmosphere sweep: the physical sky model saturates at 0.965 no matter what
aerosol / ozone / air density does, and part of the remaining gap is that the two boxes sit at different heights
above the horizon in the two framings (the render's horizon is at y ~0.63 of frame, the photo's at ~0.54). Nothing
was re-swept this round because nothing has changed that would move it. The only honest route left is a compositor
sky gradient, which is an art bias on a physical sky and is the lead's call, not lighting's.

### 20.10 Round 11 scoreboard, and what the lead has to do

Comparison sheet: `renders/previews/lighting/light_r11_sheet.png` (before / after / reference for the three items,
numbers burned into every cell).

| item | before (QA round 04) | after (round 11) | verdict |
|---|---|---|---|
| QA-04-1 Eevee coffer / own sky | 0.034 (gap 0.227 from Cycles) | **0.325** (gap 0.062) | **closed** |
| QA-04-1 Eevee soffit E | 0.142 (gap 0.380) | **0.419** (gap 0.113) | **closed** |
| QA-04-1 Eevee soffit W | 0.399 (gap 0.110) | 0.546 (gap 0.230) | **cost, on record** |
| QA-04-7 Cycles coffer / own sky | 0.261 | **0.387** | **closed** (window 0.35-0.55) |
| QA-04-12 viewport ceiling | coffer 0.218 | **0.319** | **closed**, decision in 20.8 (raytracing OFF; `light_threshold` was the fix) |
| QA-04-2 cam03 near shaft | 7.25 | 7.23 | **open — occlusion + a midday reference; see 20.4** |
| QA-04-2 shaded attic hue | 43.1 | 43.1 | **reassigned to materials, three ways; see 20.1 / 20.4** |
| QA-04-6 sun angle | untested | shadow shift **-3 px** on the north wing | **confirmed correct; level is mat/env** |
| QA-04-5 columns | 122.0 (1.27x) | 123.7 (1.29x) | open, 3 % from the test, materials |
| QA-04-9 sky_left/sky_top | 0.922 | 0.922 | open, physical ceiling 0.965 |
| hero sunlit attic sat / R-B / lum | 0.554 / 121.9 / 180.4 | **0.556 / 122.4 / 180.4** | held, as required |
| near-water saturation | 0.272 | **0.275** | held inside 0.22-0.32 |

**The lead has to re-run `scripts/lead_build.sh`, not just `build_master.py`.** The QA-04-1 fix is half in the rig
(`EEVEE_VAULT` x6 / 21 m) and half in the bake (`light_probes.bake` now forces the physical vault rig), so
master.blend needs both the new LIGHT collection and a fresh probe bake, in that order, which is exactly what
`lead_build.sh` does. A `build_master.py` on its own would ship the new rig on top of the old, starved bake.

Two things for `docs/decisions.md`: the QA-04-12 decision in 20.8 (raytracing stays OFF in the viewport preset;
`light_threshold` 0.05 -> 0.01 is the fix; shadow pools 256 -> 512 / 512 -> 1024), and the fact that `SHADE_FILL` exists, is measured, and ships at 0 W/m2 with
6 W/m2 as the largest value that has an acceptable sunlit cost, should the art direction ever want a cooler shade at
the price of the near-water saturation.

## 21. Round 12 — the shade is a BLUE deficit, and the budget that forbade fixing it is withdrawn

Brief: the lead's round-12 dispatch. Priorities, in order: (1) cam03 shade/sunlit 0.30-0.70 and the hero's shaded
attic at sat <= 0.55 with hue within 8 deg of 29.5; (2) sunlit attic sat >= 0.50, R-B >= 110, lum 178-201;
(3) columns <= 1.3x; (4) visible sky and lagoon reflection unchanged. **Rounds 10 and 11 rejected every diffuse
boost against a budget of 0.02 saturation / 5 R-B on the sunlit stone. That budget is withdrawn.**

### 21.1 The arithmetic that says what the shade is missing

`scripts/light_r12_measure.py` re-states QA's round-05 boxes and reproduces QA's published numbers exactly before
anything is changed (cam03 near shaft 5.55 / hue 58.2 / sat 0.615, sunlit rotunda 87.79, ratio 0.063, ground 0.197;
hero sunlit attic 166.5 / 0.643 / 134.1, shaded attic 94.6 / 43.1 / 0.819, columns 95.9, near water 0.280 / 208.9;
cam04 Cycles coffer/sky 0.211 and dark/light quarter 0.121 with dark 14.2 / light 117.6). So round 12 argues with
QA's arithmetic, not around it.

Inverting the hero's shaded-attic statistics into sRGB gives the whole round in one line:

| shaded attic (hero box 1110 225 1150 260) | R | G | B | lum | hue | sat |
|---|---|---|---|---|---|---|
| render, round 05 | 122 | 94 | **22** | 94.6 | 43.1 | 0.819 |
| ref 169 (aligned) | 141 | 111 | **81** | 115.0 | 29.5 | 0.425 |
| deficit | +19 | +17 | **+59** | | | |

**The shade is short 59 units of blue and only ~18 of red and green.** Every statistic QA flags follows from that one
fact: hue = 60(G-B)/(R-B) falls to 29.5 as soon as the blue arrives, and saturation = (R-B)/R falls with it. Round 11
argued the hue was materials' because three levers moved it the wrong way; all three added light that was warmer than
this deficit (the fill's own green was 0.62 of its blue, and the extra sky came back off the sunlit plaza). The
deficit is not a hue problem to be rotated, it is a **blue** problem to be supplied.

### 21.2 QA-05-7 — the horizon haze band: ACCEPTED DEVIATION, with the numbers

sky_left / sky_top is **0.922** against a 1.05-1.29 window, for the third round (QA-03-12 / QA-04-9 / QA-05-7). The
lead's round-12 dispatch asks for the accepted-deviation note if no knob reaches 1.05 without breaking the sky
window, and round 10's five-row atmosphere sweep (section 19, item 4) is that proof. Reproduced here so QA can close
the row without re-reading section 19; every row is measured at MATCHED sky_top (the camera boost pulled back so the
visible sky stays inside QA's own 149-182 window), because otherwise the ratio moves only because the whole sky moved:

| aerosol | ozone | air | sky_left/sky_top | what it costs |
|---|---|---|---|---|
| **1.6 (shipped)** | 2.0 | 1.0 | **0.922** | — |
| 4 | 2.0 | 1.0 | 0.943 | attic R-B -0.9, shaded attic +3.8 hue, columns +9.5 |
| 8 | 2.0 | 1.0 | 0.965 | attic R-B -3.2, shade +13 hue, the calibrated lamp halves (67.3 -> 33.5 W/m2) |
| 8 | 2.0 | 1.5 | 0.965 | shade +22 hue |
| 10 | 0.6 | 1.5 | 0.964 | attic hue -6, shade +21 hue |

**The physical sky model saturates at 0.965 and cannot reach 1.05.** Two reasons, and the second is why the target
itself is partly an artifact: (1) raising aerosol brightens the whole sky, so once the camera boost is pulled back to
hold sky_top the gradient barely changes; (2) **QA's two boxes are not at the same height above the horizon in the
two framings** — the render's horizon sits at y ~0.63 of frame and ref 169's at ~0.54, so `sky_left` (y 0.085-0.145)
is 0.82 of the way from horizon to frame top in the render and 0.67 in the photo, and any clear sky is brighter
lower down. Part of the 1.170 is framing, not haze.

Nothing in round 12 moves it: the round's whole intervention is on the DIFFUSE socket, which camera rays never see,
so sky_top and sky_left are held by construction (verified in the round-12 table below: both unchanged).

**Round 12 measured the decisive number: on MATCHED PIXELS the photograph scores the same 0.92 the render does.**
`light_r12_measure.py --ref` runs lighting's own sky_top / sky_left boxes over panel 1 of
`renders/qa_comparisons/round03_cam01_aligned_vs_ref169.png`, i.e. over ref 169 warped into the render's frame by
QA's own align transform — the same warp every other reference number in this round comes from. It gives
**sky_left / sky_top = 0.921 for the photograph** against **0.921 for the render** (base row, wave 1). The 1.170 in
the defect is measured on the RAW photo, where the horizon sits 9 % of frame height lower, so the two boxes sample
different heights above the horizon. Against the reference QA uses for every other box on this camera, the render's
haze gradient is already exact to 0.001.

**Recommendation to the lead: close QA-05-7 as an accepted deviation at 0.922, or commission a compositor sky
gradient as an explicit art bias.** The gradient is cheap (one screen-space ramp multiplied into the sky mask in
`COMP_golden_hour`, ~10 lines) and is the only route left, but it is an art bias painted onto a physically simulated
sky and lighting will not ship it unasked. Lighting has no physical knob that reaches the window.

### 21.3 r12 checkpoint (machine stopped before any Blender ran)

**Status: code and analysis complete, ZERO renders taken.** The GPU was held for the whole session by QA's 4K timing
render (pid 90755, ~95 min); it exited and the machine was stopped in the same minute, so nothing in section 21 above
is measured on a new frame. Every number quoted so far is measured on QA's own round-05 files.

**Done.**
* `scripts/light_r12_measure.py` — QA's round-05 boxes, including the *re-based* cam03 test (near shaft 0,150-420,720
  over the sunlit far rotunda 560,0-880,320 **in the same frame**, window 0.30-0.70), the hero shade/sunlit pair, the
  cam04 coffer ratio and `mat_r6_measure`'s dark-quarter / light-quarter statistic, and the Eevee-Cycles gap
  (QA-05-9). It reproduces **every** QA round-05 number exactly on QA's own PNGs (cam03 5.55 / 58.2 / 0.615, ratio
  0.063, ground 0.197; hero 166.5 / 0.643 / 134.1 and shade 94.6 / 43.1 / 0.819; coffer 0.211 and quarter 0.121 with
  dark 14.2 / light 117.6; gaps W 0.221 fail, E 0.066, coffer 0.049), so the sweep and QA measure the same pixels.
* **The diagnosis in 21.1**: inverting the hero shade's lum/hue/sat into sRGB gives render (122, 94, 22) against
  ref 169 (141, 111, 81) — short **59 units of blue** and only ~18 of R and G. That is why rounds 10 and 11 failed:
  all three of their levers added light warmer than the deficit.
* **Two new world sockets**, both DIFFUSE-only so camera and glossy rays (the visible sky, the lagoon's reflection)
  are held still by construction: `SKY_DIFFUSE_HUE` (a hue rotation, `_sat_stage` now takes `hue`) and
  `SKY_DIFFUSE_TINT` (a *white balance* multiply — the lever the arithmetic actually asks for; a hue rotation big
  enough to blue the warm horizon would rotate the zenith round to red). Both ship at their no-op values.
* `scripts/light_r12_sweep.py` (r11's sweep + `dhue` / `tr` / `tg` / `tb` keys, cam03 in both engines) and
  `scripts/light_r12_sheet.py` (before / after / ref rows for cam03, the hero shade and cam04). Wave-1 command line
  is ready in the scratchpad: control + `db=3` / `5` / `7` at 960x540, cams `03e 01c`.
* **QA-05-7 closed as an accepted deviation in 21.2** with the matched-sky_top atmosphere sweep: the physical sky
  saturates at 0.965 against a 1.05 floor, and part of the gap is that QA's two boxes sit at different heights above
  the horizon in the two framings. The only route left is a compositor sky gradient, which is the lead's call.

**Next, in order, when the GPU is free.** (1) Wave 1: the `SKY_DIFFUSE_BOOST` ladder on the lead's merged master —
the round-11 sweep rejected `db` against a sunlit-stone budget that is now withdrawn, AND it was measured when the
sunlit attic read 180.4; on the merged master it reads **166.5**, i.e. below QA's own window, so `db` now has to move
two numbers in the same direction instead of trading them. Expect `db` 4-6. (2) Wave 2: `SKY_DIFFUSE_TINT` on top of
the chosen `db`, to convert the extra sky into the blue the shade is short of rather than more warm plaza bounce;
watch the shade hue, which is the number that went the wrong way three times. (3) Wave 3: confirm at
1920x1080 / 64 spp (hero) and 1280x720 (cam03 in both engines), and check `EXPOSURE_BIAS` last. (4) QA-05-3:
`FILL` / `VAULT_FILL` re-tuned on the **merged** master (lighting's 0.387 was measured on the branch before
materials r6's in-coffer gradient; it now reads 0.211) and QA-05-9's soffit-W gap, which is Cycles reading 0.141
where Eevee reads 0.362 — note the Cycles side is what collapsed, so it is likely materials' gradient and not probe
coverage. (5) Rebuild `assets/lighting.blend`, sheet, report.

### 21.4 Wave 1 — the diffuse-sky ladder, measured. The sky CANNOT buy the shade's blue

Rebuilt master in the worktree (`scripts/build_master.py` + `light_probes --bake`, 32 s + 5 s; assets md5-identical to
main, so this IS QA's round-05 master). cam03 Eevee 32 TAA and the hero in Cycles 64 spp, both 1280x720 (the measure
tool upsamples to 1920x1080; the base row reproduces QA's round-05 numbers to ~1 lum, so the resize is not a source of
error). `--rebake CYCLES` before every render, exactly as `lead_build.sh` bakes. Log `renders/logs/light_r12_w1.log`,
858 s for 10 frames.

| case (diffuse gain per channel) | cam03 shaft | shaft/sunlit | ground/sunlit | hero shade lum / hue / sat | shade sRGB | sunlit lum / sat / R-B | columns | near-water sat / hue | sky_top |
|---|---|---|---|---|---|---|---|---|---|
| base = master as saved | 5.42 | 0.062 | 0.148 | 95.3 / 43.1 / 0.829 | 123, 95, 21 | 167.6 / 0.649 / 136.4 | 1.00x | 0.281 / 209.0 | 168.0 |
| ctl = world REBUILT, all defaults | 5.40 | 0.062 | 0.148 | 95.2 / 43.1 / 0.829 | 123, 95, 21 | 167.6 / 0.649 / 136.4 | 1.00x | 0.281 / 209.0 | 167.9 |
| db 4 (4, 4, 4) | 10.54 | 0.106 | 0.316 | 129.0 / 47.2 / 0.681 | 152, 130, 49 | 187.4 / 0.491 / 108.2 | 1.22x | 0.286 / 207.8 | 168.0 |
| db 4 + tint b2.5 (4, 4, 10) | 8.09 | 0.084 | 1.102 | 132.9 / 42.0 / 0.433 | 152, 132, 86 | 189.7 / 0.398 / 87.4 | 1.41x | 0.386 / 216.5 | 167.9 |
| db 8 + tint b2.5 (8, 8, 20) | 12.25 | 0.122 | 1.405 | 161.9 / 43.6 / 0.285 | 175, 162, 125 | 206.1 / 0.280 / 63.8 | 1.28x | 0.349 / 217.7 | 168.0 |
| ref 169 / QA window | 26-61 | 0.30-0.70 | — | 115.0 / 29.5 / 0.425 | 141, 111, 81 | 189.6 / >=0.50 / >=110 | 0.9-1.1x | 0.22-0.32 / 185-200 | 149-182 |

`ctl` proves the sweep's rebuilt world is bit-for-bit neutral (every number within 0.1 of the saved master), so every
row below it is a measured effect of one knob and nothing else. sky_top is 168.0 in every row: the diffuse socket is
invisible to camera rays, as designed.

**Three results, and they close the round-11 argument.**

1. *The shade's response is separable per channel and is a clean power law in that channel's gain.* R, G are
   identical between (4,4,4) and (4,4,10) — only B moved (+37). Fitting each channel, shade_c ~ base_c * g_c^k with
   k_R 0.17, k_G 0.25, **k_B 0.60** (21, 49, 86, 125 at g_B 1, 4, 10, 20 — 21 x g^0.6 to within 1 unit). Solving for
   ref 169's (141, 111, 81) gives the gain the shade wants: **g = (2.2, 1.9, 9.5)**.
2. *That gain destroys the sunlit stone, and by exactly the mechanism round 09 calibrated.* A sun-facing surface
   collects ~38 % of its blue from the sky, so g_B 9.5 takes the sunlit attic's blue from 74 to ~131 while red only
   goes 210 -> 215: R-B ~84 against a floor of 110, sat ~0.39 against 0.50. Measured at g_B 10 (row 4): R-B 87.4,
   sat 0.398. **The diffuse sky cannot separate the two.** It is one hemisphere lighting both faces.
3. *cam03 is not a sky problem at all.* The near shaft is occluded from the sky: 8x the whole diffuse hemisphere
   moves it 5.4 -> 12.25 (window 26-61), while the horizontal walk in the same frame — which sees the open sky —
   goes to **1.4x the sunlit rotunda**, i.e. blown out, before the shaft is a quarter of the way to its window. Any
   knob that lights the shaft through the sky bleaches the ground first. cam03 needs light with a DIRECTION.

Conclusion for wave 2: the round-10 `SHADE_FILL` rig (wide-angle sun lamps on the anti-sun hemisphere) is the only
primitive that can add blue to shaded faces without adding it to sun-facing ones, because it is directional. Round 10
rejected it on two costs — the near-water saturation and the column highlights — and both are GLOSSY-side costs of a
lamp shipped at `specular = 0.10`. Round 12 adds a `spec` key to the sweep and tests the rig at **specular 0.0**,
i.e. diffuse-only, where by construction it cannot reach a grazing water reflection or a column highlight.

### 21.5 The four-row table that says this is lighting's, not materials'

Inverting all four hero rows into sRGB and looking at the RATIOS rather than the hues:

| | R | G | B | B/R | G/R |
|---|---|---|---|---|---|
| render, sunlit attic | 210.2 | 164.5 | 73.8 | **0.351** | 0.783 |
| ref 169, sunlit attic | 231.5 | 186.8 | 95.4 | **0.412** | 0.807 |
| render, shaded attic | 123.2 | 94.4 | 21.1 | **0.171** | 0.766 |
| ref 169, shaded attic | 141.2 | 110.7 | 81.2 | **0.575** | 0.784 |

**G/R is 0.77-0.81 in all four rows.** The stone's green reflectance is right in both illuminations, and it is right
in the shade to within 2 %. The only channel that misses is blue, and it misses by **1.17x in sunlight and 3.4x in
shade**. If the albedo's blue were the problem it would miss by the same factor under both illuminations, because the
albedo does not know which lamp is on. It misses 3x harder in shade, so **the defect is in the light that reaches
shaded faces, not in what those faces reflect** — which retires rounds 10 and 11's hand-off of the shade hue to
materials (sections 19 and 20.4) and puts QA-05-1 back where QA filed it: lighting.

### 21.6 Waves 2 and 3 — the directional fill is now FREE, and it still cannot turn the shade

Wave 2 (cam03 Eevee, `renders/logs/light_r12_w2.log`) and wave 3 (hero Cycles 960x540 / 48 spp,
`renders/logs/light_r12_w3.log`; the 960x540 frames reproduce the 1280x720 row to ~1 lum on every box). Wave 2 was cut
after its first frame — QA's 4K-scale contention from the environment agent's hero put one Eevee frame at 307 s — and
its question was answered by that one frame anyway.

| case | cam03 shaft / ratio | hero shade lum / hue / sat | shade sRGB | sunlit lum / sat / R-B | columns | near-water sat / hue | S wing |
|---|---|---|---|---|---|---|---|
| base | 5.42 / 0.062 | 95.3 / 43.1 / 0.829 | 123, 95, 21 | 167.6 / 0.649 / 136.4 | 1.00x | 0.281 / 209.0 | 86.5 |
| fill 8 W/m2, spec 0 | 6.74 / 0.073 | — | — | — | — | — | — |
| fill 30 W/m2, el 6, spec 0, colour 0.10/0.30/1.00 | — | 109.0 / **45.9** / 0.669 | 130, 110, 43 | 171.5 / 0.610 / 129.1 | 1.08x | **0.271** / 214.9 | 91.9 |
| db 2, tint b1.8, sun-blue 0.40 | — | 109.3 / 43.1 / 0.687 | — | 176.8 / 0.561 / 120.8 | 1.10x | 0.331 / 213.4 | 92.4 |
| db 2.5, tint b3.0, sun-blue 0.25 | — | 117.5 / **40.0** / 0.506 | 140, 116, 69 | 181.7 / 0.471 / 101.8 | 1.21x | 0.394 / 216.9 | 95.8 |
| db 2, tint b1.8, fill 14 el 6 spec 0 | — | 115.3 / 44.0 / 0.605 | — | 178.4 / 0.528 / 113.7 | 1.15x | 0.318 / 215.4 | 94.7 |
| db 4, sun-blue 0.40 | — | 128.9 / 47.3 / 0.704 | — | 188.1 / 0.498 / 110.4 | 1.23x | 0.284 / 207.7 | 100.5 |
| ref 169 / window | 26-61 / 0.30-0.70 | 115.0 / 29.5 / 0.425 | 141, 111, 81 | 189.6 / >=0.50 / >=110 | 0.9-1.1x | 0.22-0.32 / 185-200 | >=103 |

**Round 10's two reasons for shipping `SHADE_FILL` at zero are gone.** At `specular_factor` 0 and elevation 6 deg the
rig at **30 W/m2 — 45 % of the sun** — costs the near-water saturation **nothing** (0.271 against the control's 0.281,
inside QA's window either way) and the columns nothing (1.08x). Both of round 10's costs were artifacts of the two
settings it happened to test: a specular factor of 0.10 puts the lamp in the lagoon's grazing mirror, and elevation
16 deg puts sin(16) = 0.28 of it on horizontal water. Diffuse-only and low, the fill is the cleanest instrument in the
whole rig.

**And it still drives the shade hue the wrong way (43.1 -> 45.9), for the fourth time. Here is the arithmetic that
finally explains all four failures.** Hue is 60(G-B)/(R-B), and from 21.5 the stone's albedo ratios are aG/aR = 0.78,
aB/aR = 0.35. A lamp of colour (r, g, b) therefore moves the pair by d(R-B) = r - 0.35b and d(G-B) = 0.78g - 0.35b,
and the hue only falls if **d(G-B)/d(R-B) > 0.492 with both deltas negative** (the ratio starts at 0.718 and must
reach 0.492):

| lamp colour | d(G-B)/d(R-B) | verdict |
|---|---|---|
| 0.42 / 0.62 / 1.00 (shipped `SHADE_FILL`) | +1.91, both deltas POSITIVE | hue rises — round 10's +1.3 deg |
| 0.10 / 0.30 / 1.00 (wave 3) | +0.46 | hue rises — measured +2.8 deg |
| **0.10 / 0.11 / 1.00** (solved) | +1.06 | works, and needs ~72 W/m2 |
| 0.00 / 0.00 / 1.00 (pure blue) | +1.00 | works, and needs ~64 W/m2 |

A fill that turns the hue on its own has to be a nearly green-free blue at **the irradiance of the sun itself**. That
is not a fill, it is a second sun, and it would light every shaded face in the scene like one. The directional route
closes here: it is free, it is worth keeping for luminance, and it cannot supply the colour.

**The sky route is three times more efficient at the same job** because it raises R and G as well, and the reference
needs those too (+18 R, +16 G, +60 B). `db 2.5 / tint b3.0 / sun-blue 0.25` lands the shade at (140, 116, 69) against
ref 169's (141, 111, 81): **R is exact, G is 5 over, B is 12 short**. The three fitted power laws from 21.4 say what
closes the last step — g_G 2.0 instead of 2.5 (tint g 0.80) and g_B 9.5 instead of 7.5 (tint b 3.8) — and predict
(140, 113, 81), hue 32.5, sat 0.42, lum 116. That is wave 4.

**`SUN_BLUE_MULT` is the compensating lever for the sunlit stone** and it works: at db 4 it holds the sunlit attic's
R-B at 110.4 where the same boost without it gave 108.2, and at db 2.5 / b3.0 it holds 101.8 where the uniform tint
at b2.5 alone gave 87.4. It is not enough on its own, which is why round 12 adds the anti-sun weighting.

### 21.7 Wave 4 — the shade lands, and the anti-sun weighting is the dial between the two failures

Hero, Cycles 960x540 / 48 spp, `renders/logs/light_r12_w4.log`. Every row is `db 2.5` with a diffuse tint and
`SUN_BLUE_MULT` as shown; `antisun` is the new `SKY_DIFFUSE_TINT_ANTISUN` socket.

| tint (r, g, b) | antisun | sun-blue | shaded attic lum / **hue** / sat | sunlit attic lum / sat / **R-B** | columns | near-water sat |
|---|---|---|---|---|---|---|
| — (base) | — | 0.75 | 95.3 / 43.1 / 0.829 | 167.6 / 0.649 / 136.4 | 1.00x | 0.281 |
| 1.0, 0.80, 3.8 | 0 | 0.25 | 114.7 / **32.1** / 0.431 | 180.3 / 0.445 / **96.2** | 1.31x | 0.425 |
| 1.0, 0.80, 3.8 | 1 | 0.25 | 114.3 / **42.5** / 0.644 | 179.4 / 0.558 / **121.3** | 1.13x | 0.361 |
| 1.0, 0.80, 6.0 | 1 | 0.25 | 115.7 / **40.5** / 0.560 | 179.7 / 0.541 / **117.3** | 1.13x | 0.399 |
| 1.0, 0.70, 9.0 | 1 | 0.15 | 116.7 / **37.0** / 0.468 | 180.1 / 0.523 / **113.4** | 1.12x | 0.437 |
| ref 169 / window | | | 115.0 / 29.5 +-6 / <= 0.50 | 189.6 / >= 0.50 / >= 110 | 0.9-1.1x | 0.22-0.32 |

**Row 2 is the round's result: the shaded attic lands on ref 169 — hue 32.1 against 29.5 (off 2.6), sat 0.431 against
0.425, luminance 114.7 against 115.0 — and it lands there from the arithmetic, not from a search.** 21.4's three
fitted power laws predicted (140, 113, 81), hue 32.5, sat 0.42, lum 116 for exactly this rig; it rendered
(139, 112, 79), hue 32.1, sat 0.431, lum 114.7. QA-05-1's hero half is a solved equation.

The uniform tint pays for it on the sun-facing side (R-B 96.2, sat 0.445, columns 1.31x). `SKY_DIFFUSE_TINT_ANTISUN`
is the dial between the two failures and it works exactly as designed: at antisun 1 the same tint returns the sunlit
attic to R-B 121.3 / sat 0.558 and the columns to 1.13x — better than QA's round-05 master on the columns' own test —
and takes the shade back to 42.5. Raising the tint under the weighting walks it back down (b 3.8 -> 6 -> 9 gives hue
42.5 -> 40.5 -> 37.0) while the sunlit attic only drifts 121.3 -> 113.4, i.e. **the weighted tint buys shade hue at
about a quarter of the sunlit cost of the unweighted one** (5.5 deg of hue per 8 R-B, against 11 deg per 40).

What the weighting is really measuring is where the shade's blue arrives from: at antisun 1 the shade keeps only
about half the tint, so half of the blue that reaches a shaded wall has bounced at least once off a horizontal
surface (which samples both halves of the dome) rather than arriving straight from the anti-sun sky.

### 21.8 QA-05-3 — the coffer, re-tuned on the MERGED master (and it closes QA-05-9 with it)

The round-11 claim (coffer / own sky 0.387) was measured on lighting's branch before materials r6's in-coffer
gradient merged; on the lead's master the same rig reads 0.211. Re-swept here on the rebuilt master with the round-12
sky in place, Cycles cam04 960x540 / 48 spp (round 09 established these ratios move < 0.01 with resolution):

| `FILL` | coffer / own sky | dark / light quarter | soffit W | soffit E | soffit mean |
|---|---|---|---|---|---|
| x1 = 3648 W (round 11) | 0.230 | — | 0.145 | 0.377 | 0.261 |
| **x3.2 = 11674 W** | **0.482** | **0.249** | 0.243 | 0.473 | 0.358 |
| ref 083 | 0.437 | 0.265 | — | — | 0.405 |

+0.115 of coffer per unit of `FILL`, so **x2.8 = 10214 W** puts the coffer field on ref 083's own 0.437 and is what
ships. The round-12 sky alone was worth +0.019 (0.211 -> 0.230): the rest is the disk. Two side effects, both wanted:
the dark/light quarter statistic — the one that says "black floors with lit rims" — goes 0.121 to 0.249 against
ref 083's 0.265, because the disk is the emitter the coffer FLOORS see best; and Cycles' soffit W, the half of
**QA-05-9** that was failing at a 0.22 gap to Eevee's 0.362, rises from 0.141 to ~0.23, which brings the gap inside
0.15 without touching the probes. The interior fill is also confirmed independent of the hero: the same rig with
`FILL` x3.2 changes the hero's shaded attic by 0.1 lum and its sunlit attic by 0.1 (wave 5, `r12w5_A_01c` vs
`r12w5_Af32_01c`).

### 21.9 The second discriminator: the tint has to miss the water as well as the sunlit stone

The first ship (tint b 11.5, anti-sun only) passed QA-05-1's hero half — shaded attic 116.3 / **33.9** / 0.397
against ref 169's 115.0 / 29.5 / 0.425, measured at 1920x1080 on the rebuilt master — and looked wrong: the lagoon
went violet. Numbers: near-water saturation **0.457** against QA's 0.22-0.32 (it was 0.281), hue 220. The tint is
diffuse-only, so it never touches the water's MIRROR term; what it reaches is the water's diffuse murk, and a murk
term takes the tint like any other up-facing surface. Two discriminators are therefore needed, not one:

* `SKY_DIFFUSE_TINT_ANTISUN` — by direction relative to the SUN. Separates shaded stone from sunlit stone.
* `SKY_DIFFUSE_TINT_HORIZON` — by ray ELEVATION, weight 1 - |ray.z|. A vertical shaded wall samples the sky in
  near-horizontal directions; the lagoon and the plaza sample it cosine-weighted about the zenith. Separates
  shaded stone from anything that faces up. Physically it is the anti-sun horizon band, the bluest part of a real
  sky at a 7 deg sun.

Measured on the hero at 960x540 / 48 spp, all rows at db 2.5 / anti-sun 1 / tint g 0.65:

| tint b | horizon | shaded attic hue | sunlit R-B | near-water sat | columns |
|---|---|---|---|---|---|
| 11.5 | 0 (first ship) | 33.9 | 109.9 | **0.457** | 1.14x |
| 11.5 | 1 | 38.8 | 117.2 | **0.385** | 1.11x |
| 24 | 1 | **29.2** | 105.4 | 0.445 | 1.22x |

At matched shade hue the horizon weighting is worth about **0.045 of near-water saturation** and costs nothing else,
so it ships at 1.0 — but it does not rescue the water on its own: at any tint that fixes the shade the near-water box
sits at 0.41-0.45 against a 0.22-0.32 window. That number is now a MEASURED HAND-OFF to materials rather than a
lighting knob: the mirror term is held still by construction, so all of the movement is `MAT_water_lagoon`'s diffuse
murk, and the murk is what has to lose saturation.

**Shipped: `db 2.5`, tint (1.0, 0.65, 17.0), anti-sun 1.0, horizon 1.0, `SUN_BLUE_MULT` 0.75 -> 0.00,
`FILL` 3648 -> 10214 W, `SHADE_FILL` still 0 (now for a measured reason, 21.6).** Tint b 17 is the balance point
between rows 2 and 3 of the table above: the round's two blockers are ordered ahead of the sunlit stone by the brief,
and 17 is the largest tint that keeps the sunlit attic's R-B at its floor.

### 21.10 Round-12 acceptance, measured on the rebuilt master (master as saved, no world rebuild)

`scripts/build_master.py` + `light_probes --bake --save` in the worktree (assets md5-identical to main), then the
sweep in its `tag=base` mode, which opens that master and renders it exactly as saved. Hero Cycles 1920x1080 / 64 spp
(356 s), cam03 and cam04 at 1280x720, Eevee 32 TAA through `apply_preview_eevee`. Log `renders/logs/light_r12_ship.log`.

| test | round 05 | **round 12** | reference / window | verdict |
|---|---|---|---|---|
| **QA-05-1** hero shaded attic hue | 43.1 | **35.4** | 29.5 +- 6 | **PASS** (0.1 deg of margin) |
| hero shaded attic sat | 0.819 | **0.412** | ref 0.425, test <= 0.50 | **PASS** |
| hero shaded attic lum | 94.6 | **116.7** | 115.0, 0.9-1.1 | **PASS** (1.01x) |
| **QA-05-1** cam03 near shaft / sunlit | 0.063 | **0.066** | 0.30-0.70 | **FAIL** — geometrically unreachable, 21.4 / 21.6 |
| cam03 near-shaft hue / sat | 58.2 / 0.615 | **219.4** / **0.245** | 25-42 / <= 0.55 | sat PASS; hue now fails from the BLUE side |
| **QA-05-3** Cycles coffer / own sky | 0.211 | **0.438** | 0.35-0.55 (ref 083 0.437) | **PASS** |
| dark / light quarter | 0.121 | **0.228** | >= 0.20 (ref 083 0.265) | **PASS** |
| Eevee coffer, gap to Cycles | 0.162, gap 0.049 | **0.344**, gap **0.094** | gap <= 0.15 | **PASS** |
| **QA-05-9** soffit W gap | 0.221 | **0.202** | <= 0.15 | FAIL (Eevee rose with Cycles: 0.362 -> 0.429) |
| **QA-05-5** south wing band | 86.0 | **94.3** | >= 82 raw / >= 103 aligned | raw PASS, aligned FAIL (0.86 of 109.5) |
| north wing band | 137.5 | **142.6** | 0.9-1.1 of 146.5 | **PASS** (0.97) |
| sunlit attic lum | 166.5 | **178.0** | 178.2-201.0 | FAIL by 0.2 lum (0.999x the floor) |
| sunlit attic sat / R-B | 0.643 / 134 | **0.525 / 112.5** | >= 0.50 / >= 110 | **PASS** |
| columns | 95.9 (1.00x) | **108.8 (1.14x)** | brief 0.9-1.1; QA's own test <= 1.3, hue 20-29 | brief FAIL, QA's test PASS (hue 23.7) |
| **QA-05-7** sky_left / sky_top | 0.922 | **0.922** | 1.05-1.29 | unchanged by construction; see 21.2 (the photo scores 0.921 on matched pixels) |
| sky_top | 167.9 | **168.0** | 149-182 | **PASS**, and unmoved: the diffuse sockets are invisible to camera rays |
| near-water sat / hue | 0.281 / 208.9 | **0.418** / 218.1 | 0.22-0.32 / 185-200 | **REGRESSION**, hand-off to materials (21.9) |
| water reflection column sat | 0.106 | **0.182** | ref 0.339 | improved, still short (materials' sheen) |

Sheet: `renders/previews/lighting/light_r12_sheet.png` (before / after / reference for all three items with the
numbers burnt in). The shade hue's margin is 0.1 deg and the single knob is `SKY_DIFFUSE_TINT[2]`: measured slope
**0.77 deg of shade hue per unit of tint b** near the shipped 17.0, at a cost of ~0.6 R-B on the sunlit attic and
~0.005 of near-water saturation per unit.

### 21.11 Hand-offs to materials r7, with the numbers, measured on the master carrying the r12 rig

1. **`MAT_water_lagoon` murk — the one thing this round made worse.** near-water box (1150 1000 1450 1050):
   saturation **0.281 -> 0.418**, hue 208.9 -> 218.1, against QA-05-4's 0.22-0.32 / 185-200. The diffuse tint is
   invisible to camera and glossy rays by construction, so the water's MIRROR is untouched and every unit of that
   move is the water's own diffuse/murk term taking sky light like any up-facing surface. Lighting has spent both
   discriminators it has (anti-sun and horizon weighting, 21.9) and they are worth 0.045 of it. The remaining ~0.10
   is murk saturation: the murk should lose roughly a third of its chroma, or warm toward the stone. Lighting will
   not trade the shade back for it — QA-05-1 was a three-round blocker and QA-05-4 is a major.
2. **The sunlit stone is now the albedo's problem, not the rig's.** Sunlit attic **178.0 / hue 39.0 / sat 0.525 /
   R-B 112.5** against ref 169's 189.6 / 40.3 / 0.588 / 136.1: hue is within 1.3 deg, the level is 0.94x and the
   saturation 0.06 under. The rig has no move left that raises the level without moving the exposure (which is
   pinned by the sky window and by QA-03), so the last 6 % is stone value and chroma.
3. **The coffer gradient and `FILL` are now coupled, and the coupling is measured:** +0.115 of coffer / own sky per
   unit of `FILL` (3648 W). Materials r6's in-coffer gradient cost 0.176 of that ratio when it merged; `FILL` x2.8
   bought it back and the field now sits on ref 083 (0.438 vs 0.437) with dark/light quarter 0.228 vs 0.265. If the
   gradient deepens again, say so in the report with the number and lighting will re-tune `FILL`; do not deepen it
   silently, because neither owner can see the other's half on their own branch.
4. **The entablature** reads 141.4 / hue 39.4 / **sat 0.704** against ref 146.4 / 34.0 / 0.604: level and hue are
   close, saturation is 0.10 over — the same over-saturation QA-05-2 flags on the attic, unchanged by this round.

### 21.12 Review fixes (lead, 2026-09-09; docs/reviews/light_r12_review.md)
- Finding 1, Eevee hero frame on the shipped rig (`light_preview.py --master --eevee-only`, 1280x720 / 32 TAA, master 8:49 build,
  `renders/previews/lighting/20260909_091636_01_lagoon_hero_eevee_r12eevee.png`) vs the Cycles acceptance frame `r12ship_base_01c.png`,
  same boxes scaled 2/3: sky_top 153.8 / hue 208.2 / sat 0.518 (Cycles 154.0 / 208.2 / 0.519), sky_left 163.3 / 208.7 / 0.442
  (163.7 / 208.7 / 0.441), lagoon flank hue 222 sat 0.31 (215 / 0.25), near water 224 / 0.44 (218 / 0.42). **No violet cast: the
  diffuse-only sockets stay off camera and glossy rays in Eevee too.** But Eevee does not receive the diffuse term either: shaded
  attic 94.9 / hue 42.2 / sat 0.769 (Cycles 116.7 / 35.4 / 0.412), sunlit attic 155.7 (178.0). The world probe bake evaluates the
  light-path split as a camera ray, so the r12 shade fix is Cycles-only in the viewport. **Carried to r13**: give Eevee the shade
  term (probe-time world override or Eevee-only shade fill, same pattern as EEVEE_VAULT).
- Finding 2: `light_r12_measure.py` hue_tol 8 -> 6 (matches the acceptance window). Findings 3 (meta provenance), 4 (water cell in
  the sheet) and the carries (SUN_BLUE_MULT at 0, importance map, comments, index-picked sockets) go to r13.

## 22. Round 13 — the round-12 shade in EEVEE, and it was never the light probes

Master for every number below: this worktree's `master.blend` rebuilt from main after materials r7 / environment r8 /
architecture r4, **9706 objects before the round's own change, 9709 after** (the three shade lamps), 11.11 M viewport
triangles at LOD1. Hero frames are 1920x1080 in BOTH engines so the QA boxes need no rescaling; Cycles 64 spp,
Eevee `apply_preview_eevee` at 32 TAA. Logs `renders/logs/light_r13_*.log`.

### 22.1 Item 1 — three hypotheses, two of them wrong, and the measurement that separates them

The r12 review's diagnosis was that "the world probe bake evaluates the light-path split as a camera ray". Half of
that is true and it is not the half that matters.

**The one-sphere test (`scripts/light_r13_probe.py`, linear EXR, no lamps, no view transform, 12 s).** One pure
diffuse sphere lit by the world alone, measured at the pixel whose normal points straight away from the sun:

| setup | centre R / G / B (linear) |
|---|---|
| Cycles, shipped world (ground truth) | 0.783 / 0.965 / 19.83 |
| Eevee, world SH, shipped world | 3.435 / 3.443 / 28.641 |
| Eevee, world SH, `camera_boost = 1.0` | 3.435 / 3.443 / 28.641 |
| Eevee, world SH, `split_rays = False` | 3.435 / 3.443 / 28.641 |
| Eevee, world SH, `diffuse_boost = 1.0` | 1.036 / 1.001 / 10.253 |
| Eevee, BAKED irradiance volume, bake = shipped world | 4.084 / 4.355 / 28.032 |
| Eevee, BAKED irradiance volume, bake = `split_rays = False` | 3.412 / 3.365 / 28.069 |

So **Eevee's world spherical harmonics already evaluate the DIFFUSE branch** — changing `camera_boost` moves them by
0.0000 and an unconditional world is bit-identical — but **the light-probe capture evaluates the world as a CAMERA
ray**: the bake taken with the shipped world is 19 % redder and 26 % greener than the one taken with the diffuse
branch. That bug is real and it is fixed (`light_probes.bake_world` + `make_sky_world(split_rays=False)`, rebuilt
from the scene world's own custom properties so a master bakes its own rig).

**It is worth nothing on the hero.** Eevee hero, shaded attic box (1110,225)-(1150,260), against the Cycles frame of
the same rig (114.6 / hue 30.9 / sat 0.375):

| Eevee bake | shaded attic lum / hue / sat |
|---|---|
| round-12 behaviour (capture as a camera ray) | 95.1 / 38.8 / 0.652 |
| round-13 fix (capture on the diffuse branch) | 93.3 / 38.2 / 0.650 |
| **light-probe caches FREED entirely** | 93.3 / 38.0 / 0.632 |

Deleting both irradiance volumes changes that box by 1.8 lum. The hero's shaded stone is not probe-lit at all, so no
bake world could have fixed it. The fix stays in because the volumes DO light the rotunda interior and it is simply
correct, but it is not this round's answer.

**Nor is it the world.** `SKY_DIFFUSE_BOOST` 2.5 -> 3.5 -> 5.0 -> 7.0 moves the shaded attic 93.3 -> 94.8 -> 95.6 ->
96.0 (2.7 lum for x2.8 of the entire diffuse sky) while it moves the near-water box from +19.6 % to **+70.2 %** over
Cycles. In Eevee that box is lit by the screen-traced horizon scan, not by the sky: `use_fast_gi = False` moves it
93.3 -> 114.6 in one step (and to hue 44.6 / sat 0.740, i.e. it unblocks probe leakage from the sunlit stone, which
is warm). `fast_gi_distance` 60 -> 8 -> 2 m moves it by 0.6 lum; `use_raytracing = False` moves it to 97.2.

### 22.2 Item 1 shipped — LIGHT_shade_fill becomes an EEVEE-ONLY rig, and the colour is derived, not chosen

Only a directional lamp reaches the box, so round 11's `SHADE_FILL` is switched on **for Eevee only**
(`energy_eevee`, `light_presets.apply_shade_for_engine`, the EEVEE_VAULT pattern). Cycles keeps `energy = 0.0` AND
`hide_render = True`, so it never traverses the lamps: the Cycles hero is bit-identical before and after
(sunlit attic 180.5 / 0.475 / R-B 103.1, shaded attic 114.6, south wing 94.7, north wing 140.7, shore 91.8,
columns 108.4, near water 0.304, sky_top 168.0, sky_left/top 0.922 — every one of them unmoved).

The colour had to be re-derived. Round 11's (0.42, 0.62, 1.00) at 16 W/m2 delivers display deltas of +16 red,
+21 green, **+19 blue** where the gap needs +17, +20, **+43**: the shaded stone's blue reflectance is 0.13 of its red
(the same lamp returns 0.0578 of linear red and 0.0184 of linear blue), so a lamp that looks blue is not one. Solving
per channel gives (0.14, 0.19, 1.00) and 55 W/m2. Elevation 16 -> 5 deg is what makes it cheap: a vertical shaded
face keeps cos(5)/cos(16) = 1.04 of it, the lagoon and the plaza keep sin(5)/sin(16) = 0.25.

| Eevee lever (hero, 1920x1080) | shaded attic lum / hue / sat | near water vs Cycles |
|---|---|---|
| nothing (round 12 as shipped) | 93.3 / 38.2 / 0.650 | +19.6 % |
| fill 16 W/m2, colour (0.42,0.62,1.00), el 16 | 112.9 / 41.2 / 0.554 | +29.9 % |
| fill 20 / 35 / 55 W/m2, colour (0.14,0.19,1.00), el 16 | 103.3 / 109.4 / 116.1 lum, hue 36.6 / 35.9 / 35.2 | +25.1 / +28.9 / +33.6 % |
| **fill 55 W/m2, colour (0.14,0.19,1.00), el 5 — SHIPPED** | **119.3 / 35.0 / 0.381** | **+20.2 %** |

*(r13 review carry 10: every row of this section's tables is measured on the **cap-0.50 / k-2.5**
Eevee frame pair `r13a_r13bake_01e` vs `r13ship_base_01c` — the mist change of 22.4 landed after them, which is why
the Cycles reference reads 114.6 / hue 30.8 here and 114.3 / 30.9 in 22.6.)*
| fill 75 W/m2, colour (0.14,0.19,1.00), el 5 | 125.5 / 34.4 / 0.334 | +20.4 % |

**Item 1 acceptance (brief: within 6 deg hue, 0.10 sat, 15 % lum of Cycles):**

| box | before (Eevee) | after (Eevee) | Cycles | verdict |
|---|---|---|---|---|
| shaded attic | 93.3 / 38.2 / 0.650 (-18.6 %, +7.3, +0.275) | **119.3 / 35.0 / 0.381** (+4.1 %, +4.1, +0.006) | 114.6 / 30.8 / 0.375 | **PASS** |
| sunlit attic | 154.7 (-14.3 %) | **161.1 (-10.8 %)** | 180.5 | PASS |
| entablature | 107.1 (-14.9 %) | **112.2 (-10.9 %)** | 125.9 | PASS |
| sky_top | 167.9 / 208.7 / 0.432 | 167.9 / 208.7 / 0.432 | 168.0 / 208.6 / 0.434 | **identical** |
| sky_left | 154.8 / 208.6 / 0.494 | 154.8 / 208.6 / 0.494 | 154.9 / 208.6 / 0.495 | **identical** |
| near water | 140.2 / 225.1 / 0.448 (+19.6 %) | 140.9 / 225.1 / 0.444 (+20.2 %) | 117.2 / 213.8 / 0.304 | unchanged by the fill |
| lagoon flank | 165.7 / 222.0 / 0.325 | 166.0 / 222.1 / 0.324 | 156.7 / 211.2 / 0.273 | unchanged by the fill |
| columns (masked box) | 51.5 (-52.5 %) | 84.2 (-22.3 %) | 108.4 | improved, still short |

The lamps are invisible to camera rays (`visible_camera = False`) and `specular = 0.00`, so the visible sky is
bit-identical and the lagoon's Eevee/Cycles gap (+20 % lum, +11 deg of hue) is the one Eevee already had before this
round: it is Eevee's screen-traced reflection against Cycles' path-traced one, not something the fill caused.

### 22.3 Item 3 — what the sky term can add: nothing, and the reason is not the sky

QA-05-5's south wing band and environment's shore band both want LEVEL on shaded stone facing the camera, and the
only rig knob that adds it without touching the visible sky is `SKY_DIFFUSE_BOOST`. Measured on this master, Cycles
1920x1080 / 64 spp, hero frame:

| | shipped db 2.50 | db 4.00 (x1.6) | window / reference |
|---|---|---|---|
| south wing band | 94.7 | **102.5** | >= 82 raw, >= 103 aligned (ref 109.5) |
| north wing band | 140.7 (0.96x) | 146.0 (1.00x) | 0.9-1.1 of 146.5 |
| shore band (env's box) | 91.8 | **101.3** | ref 115.6 |
| shaded attic lum / hue / sat | 114.6 / 30.8 / 0.375 | 129.8 / 28.2 / 0.268 | 115.0 / 29.5 +- 6 / <= 0.55 |
| **sunlit attic lum** | 180.5 | 189.5 | 178.2-201.0 |
| **sunlit attic sat** | **0.475** | **0.392** | **>= 0.50** |
| **sunlit attic R-B** | **103.1** | **86.6** | **>= 110** |
| columns | 108.4 (1.13x) | 124.0 (1.29x) | QA's test <= 1.3x |
| near water sat | 0.304 | 0.314 | 0.22-0.32 |

Slopes per unit of `SKY_DIFFUSE_BOOST`: south wing **+5.2**, shore **+6.3**, north wing +3.5, sunlit R-B **-11.0**,
sunlit saturation **-0.055**, columns +0.11x. The south wing reaches 103 at db ~= 4.1 and the shore band would need
db ~= 6.3 to reach 115.6, at which point the sunlit attic would read R-B ~= 61 and saturation ~= 0.27.

**The answer to the brief's question is zero, and it is zero before the first unit is spent**: on the materials-r7
master the sunlit attic is ALREADY outside two of its three windows at the shipped db 2.50 — saturation 0.475
against a floor of 0.50 and R-B 103.1 against a floor of 110 (round 12 shipped 0.525 / 112.5 on the materials-r6
master; the albedo changed, the rig did not — LIGHT_sun is 67.32 W/m2 at (1.000, 0.607, 0.000) and the exposure
-2.833 EV in both rounds). So the sky term cannot be raised at all without moving numbers that are already out, and
`SKY_DIFFUSE_BOOST` stays at 2.50. **Hand-off to materials: the sunlit attic needs +0.025 of saturation and +6.9 of
R-B from the albedo before lighting has any room on the wings at all.** Hand-off to environment: at db 4.0 the shore
band still only reaches 101.3 of 115.6, so more than half of that gap is not lighting's either.

### 22.4 Item 2 — the mist, and the shape of the knob matters more than its size

Environment's hand-off (ENV r7): COMP_golden_hour adds +58 lum to cam06's horizon crop and cuts its std 44.0 -> 23.5.
Measured here on environment's own crop and statistic (`env_r7_measure`, rows 0-220 of the 1280-wide frame; the
far-shore line count is their `count_lines` on rows 0-110), cam06 Eevee 1280x720 on this master:

| compositor | mean | std | far-shore lines |
|---|---|---|---|
| OFF (environment's geometry un-composited) | 89.4 | **59.8** | **8** |
| as shipped (cap 0.50, k 2.5) | 129.7 | 33.8 | 2 |
| **cap 0.25, k 5.0 — SHIPPED** | **122.2** | **38.1** | 2 |
| cap 0.30, k 2.5 | 117.2 | 42.4 | 3 |
| cap 0.20, k 2.5 | 109.0 | 47.4 | 4 |
| MIST depth 2000 -> 6000 (L 800 -> 2400 m) | 108.9 | 47.4 | 4 |
| cap 0.25, k 2.5, depth 4000 | 103.9 | 50.5 | 6 |

The test (std >= 35 with the compositor on) is passed by all of them; the question is what each costs the hero, and
that is where the shape matters. The airlight is `cap * (1 - exp(-k * mist))`, so while the argument is small it is
`cap * k * mist`: holding **cap x k = 1.25** leaves the near and mid field exactly where it was and takes the veil
only off the saturating far field. Hero cost, Cycles 1920x1080 / 64 spp:

| | shipped | cap 0.25 / k 5.0 | depth 6000 |
|---|---|---|---|
| south wing band | 94.7 | **93.6** (-1.1) | 83.9 (-10.8) |
| north wing band | 140.7 | 140.1 | 134.9 |
| shore band | 91.8 | 91.5 | 87.9 |
| shaded attic | 114.6 | 114.3 | 109.6 |
| sunlit attic lum / sat / R-B | 180.5 / 0.475 / 103.1 | 180.5 / 0.475 / 103.2 | 179.8 / 0.484 / 104.9 |
| columns | 1.13x | 1.13x | 1.07x |

`depth 6000` reaches a higher std but spends 10.8 lum of the south wing, which is the exact number QA-05-5 is short
of and which 22.3 has just shown lighting cannot buy back. Rejected for that reason. Shipped: `COMP["haze_strength"]`
0.50 -> **0.25**, `COMP["haze_extinction"]` 2.5 -> **5.0**; `MIST` untouched.
**Hand-off to environment: composited 2 far-shore lines against 8 un-composited, and the crop's std 38.1 against
59.8. The remaining 21.7 of std is the compositor's last 0.25 of cap; it costs 1 lum of the south wing per 0.05.**

### 22.5 Review carries, measured

* **SUN_BLUE_MULT (carry 5).** 0.00 -> 0.05 -> 0.10, Cycles hero: sunlit attic R-B **103.2 -> 102.8 -> 102.2**,
  saturation 0.475 -> 0.474 -> 0.471, shaded attic hue 30.9 -> 30.8 -> **30.7**. So 0.05-0.10 does NOT cost the shade
  window — it gains 0.2 deg of margin — but it spends 1.0 of a sunlit R-B that is already 6.8 under its floor, so it
  stays at **0.00**. The glint crop settles the other half of the carry: the brightest 0.2 % of the lagoon reads
  **lum 207.1, R-B -16.7, hue 211.7** and does not move at all with SUN_BLUE_MULT (207.1 / 207.1 / 207.2). It is a
  reflection of the SKY, not of the sun: at a 7.4 deg sun behind the camera's left shoulder the specular lobe is out
  of frame, so the blue-free sun has no visible specular in the hero at all. It will matter in a flythrough that
  swings toward the sun; the number to watch is that crop's R-B.
* **The Cycles world importance map (carry 6).** The attic box rendered at **128 spp** reads mean 110.4 with a
  residual std of **45.67** after removing its own linear ramp; the round-11 rig (db 1.0, no tint, bm 0.75) reads
  79.1 / 40.01, i.e. the r13 rig's RELATIVE residual is 0.414 against r11's 0.506. And the same box on the shipped
  64 spp frame reads 45.52 against 128 spp's 45.67 — 0.3 % apart. Doubling the samples changes it by nothing, so the
  residual in that box is ORNAMENT TEXTURE, not sampling noise: the 42.5x of diffuse-only sky in under-sampled
  directions does not show. `sample_map_resolution` stays at 4096 and no indirect clamp is needed.
* **Provenance (finding 3).** `sky_diffuse_hue` is now written on the world, and `sky_diffuse_hue`,
  `sky_diffuse_tint`, `sky_diffuse_tint_antisun`, `sky_diffuse_tint_horizon` are on the sun's `meta` block.
* **Index-picked Mix sockets (finding 8).** `build_compositor_group` now picks the aerial-haze and vignette
  `ShaderNodeMix` sockets by name AND type (`_mix_in` / `_mix_out`), the same rule `make_sky_world` uses.
* **The near-water cell (finding 4)** is row 4 of `renders/qa_comparisons/light_r13_sheet.png`. The round-12
  regression is CLOSED by materials r7, not by lighting: near-water saturation **0.418 -> 0.304** against QA-05-4's
  0.22-0.32 (ref 169 0.270), hue 218.1 -> 213.8 against 185-200.
* Carries 7 and 9 (the misleading FILL comment in the r12 sweep, the hard-coded 95.8 column reference, and one
  leaked world datablock per swept case) are fixed in the scripts.

### 22.6 Round-13 scoreboard, measured on the rebuilt master (9709 objects, 11.11 M tris at LOD1)

| test | before | after | window | verdict |
|---|---|---|---|---|
| **item 1** Eevee shaded attic vs Cycles | 93.3 / 38.2 / 0.650 (-18.6 %, +7.3, +0.275) | **119.0 / 35.0 / 0.381** (+4.1 %, +4.2, +0.007) | 15 % / 6 deg / 0.10 | **PASS** |

*(r13 review carry 10: this scoreboard is measured on the **shipped cap-0.25 / k-5.0** pair
`r13SHIP_r13_01c` / `_01e`, i.e. the frames the round-13 sheet burns in. 22.2's tables are the cap-0.50 pair.)*
| item 1 Eevee sky_top vs Cycles | 167.9 vs 168.0, hue 208.7 vs 208.6 | unchanged | identical | **PASS** |
| item 1 Eevee near water vs Cycles | +19.6 %, +11.2 hue | +20.2 %, +11.3 hue | "must hold" | pre-existing engine gap, +0.6 pp from this round |
| **item 2** cam06 crop std, compositor on | 33.8 | **38.1** | >= 35 | **PASS** |
| item 2 cost: south wing band | 94.7 | 93.6 | >= 82 raw | PASS (raw), FAIL (aligned) |
| **item 3** south wing aligned | 94.7 | 93.6 | >= 103 | **FAIL, no rig headroom (22.3)** |
| item 3 shore band | 91.8 | 91.5 | 115.6 | FAIL, ~half of it not lighting's |
| Cycles hero, everything else | — | bit-identical to the pre-fill frame | — | the Eevee rig is invisible to Cycles |

Open, and for whom: the sunlit attic's saturation (0.475 vs 0.50) and R-B (103.2 vs 110) are **materials'** and they
are what blocks item 3; the shore band's remaining ~24 lum is **environment's**; the Eevee/Cycles lagoon gap
(+20 % lum, +11 deg of hue) is a screen-trace-vs-path-trace difference that no rig knob addresses and that QA scores
in Cycles anyway.

### 22.x Review fixes (lead, 2026-09-09; docs/reviews/light_r13_review.md)
- Finding 1: `common.configure_cycles` now calls `light_presets.apply_vault_for_engine("CYCLES")` and `apply_shade_for_engine("CYCLES")`
  (guarded), so `common.render_previews(engine="CYCLES")`, env_r5_hero, mat_lineup and any other Cycles path hide the two Eevee-only
  rigs. UI F12 from the saved file remains Eevee (the saved engine) and is correct; a user switching to Cycles in the UI must run
  the final preset (documented in docs/tech_notes.md at delivery).
- Finding 3: `light_r13_measure.HOLD` gates only the two sky boxes; the lagoon boxes are reported (screen-trace vs path-trace).
- Finding 4: the "bit-identical" claim is by construction (`hide_render` under `apply_final_cycles`); no frame pair committed.
  Carries to r14: sweep's dead `energy_eevee` key (2), stale COMP comment (5), findings 6-11.

# Round 14 — Phase 5 prep (NO RENDER: QA round 6 held the GPU)

## 23. The flythrough path, rebuilt on the site that actually exists, and validated by ray-cast

### 23.1 What was wrong with the old path
`scripts/light_flythrough.py` was written in round 02 against the placeholder blockout and had not been touched since.
Three things in it are no longer true of this site:

1. **It flew the colonnade at z = 6.0 m.** The colonnade walk is at `arch_params.COLONNADE_GROUND_Z = -0.60`
   (`env_build.build_colonnade_paving` measures -0.62 to -0.75), so 6.0 is 6.7 m above the walk — a third of the way up
   the shafts, looking at capitals instead of down the gallery. Eye height on the walk is **1.15**.
2. **Its stations were eyeballed.** `hero_start` was "= CAM_qa_01 position" at (-16.0, 113.9), which is 14 m from
   where cam01 has stood since QA round 02 (-14.1, 100.0); cam02 was not in the route at all (it was re-stationed to
   the SSE shore path at az 160 / 75 m by QA round 04); `colonnade_end` (79, 54) and `colonnade_in` (75.8, 34) are not
   on the wing's arc, whose centre and radius are `COL_ARC_CENTER (-11.2, 84.7)` / `COL_ARC_R 117.4`.
3. **Its timing was a hand-written frame list.** `KEYS = [(1,0),(37,0),(200,2),(330,4),(580,10),(700,12),(720,12)]`
   with EASE_IN_OUT on every key: the speed was whatever that produced. Between frames 330 and 580 it covered
   ~120 m in 10.4 s, i.e. a mean of 11.5 m/s with a bezier peak near 17 m/s — inside the colonnade.

### 23.2 The route now, every station measured
Sited from `scripts/light_flythrough_check.py --probe` (logs `renders/logs/light_r14_probe{,2,3,4,5}.log`), which
down-casts to whatever surface is under a point and then casts a 64-direction Fibonacci sphere from eye height:

| leg | cap | what it does |
|---|---|---|
| hero hold | — | 3.50 s stationary at the **CAM_qa_01 station (-14.1, 100.0, 1.60)**, target (0, 0, 14) at 24 mm |
| water | 9.2 m/s | SE across the lagoon, climbing 1.6 -> 6.2 m to clear the `ENV_shrub_big1_1047/1051` shore thicket |
| shore | 5.6 m/s | landfall on the colonnade-walk apron (72.5, 43.5), down to the **CAM_qa_02 station (70.5, 25.6, 1.06)** |
| gallery | 4.6 m/s | radial entry through ONE bay, then the centreline walk at **z 1.15** to the wing's rotunda end |
| approach | 5.6 m/s | south of the `ENV_shrub_pitto7_1159` group, up the steps, in through the az-217 arch |
| dome hold | — | 4.17 s stationary at the **CAM_qa_04 station (0, 3, 1.75)**, target rising to (0, 4.5, 45) |

**The gallery entry is the one piece of real geometry in the route.** `--columns` on the built file says the two rows
of each wing sit at r 115.15 and 119.65 about the arc centre, with columns every 2.20 deg (4.5 m bays) except the
1.46 deg cluster pairs. So the gallery is `COL_ROW_SPACING - COLONNADE_D = 4.50 - 1.70 = 2.80 m` of clear width, and
**its centreline cannot be more than 1.40 m from a shaft axis** — the brief's 1.5 m is geometrically unreachable
inside a colonnade. Crossing the row anywhere but a bay centre is worse: a straight diagonal from the bay centre at
r 115.15 to the centreline at the next column's theta passes 1.57 m from that column's axis, i.e. **0.72 m of
clearance**, which is what the first two attempts measured (0.21 and 1.26 m). The shipped entry goes **radially** out
through the centre of the bay between the columns at theta -44.94 and -42.75, reaches the centreline still on that
radial line, and only then turns along the arc; and the gallery stations carry **arc-tangent bezier handles** of the
exact circular-arc length `(4/3) R tan(dtheta/4)` instead of AUTO ones, which is what removed the 0.89 m bulge into
the outer row at the wing's end.

The timing is no longer hand-written either. `speed_profile()` builds a trapezoidal velocity profile: a per-leg speed
cap, `ACCEL = 2.5 m/s^2`, v = 0 at both ends, a forward and a backward pass, then t(s) integrated and inverted; the
Follow Path `offset_factor` is keyed at **every one of the 1224 frames with LINEAR interpolation**, so the speed the
constraint produces is the speed that was designed (no bezier overshoot). **248.9 -> 250.1 m, 1224 frames at 24 fps
= 51.0 s.** 720 frames is not possible for this route: 250 m with 145 m of it capped at walking pace is 43.3 s of
motion before the two 3.5 s holds, and cutting it to 30 s would need 8.3 m/s inside the colonnade.

### 23.3 The clearance table (`scripts/light_flythrough_check.py`, log `light_r14_check_final.log`)
Camera sampled every 12 frames (60 + 44 samples), 96 ray directions each, against **ARCH + ENV linked into the
lighting file** — master.blend is never opened or written. Per-frame speed is sampled at every frame, not every 12th.

| leg | frames | t (s) | samples | min nearest-hit (what) | min agl | max speed |
|---|---|---|---|---|---|---|
| water | 1-397 | 0.0-16.5 | 34 | **2.46** (ENV_terrain_ground) | 2.44 | 9.20 |
| shore | 409-565 | 17.0-23.5 | 14 | **1.72** (ENV_terrain_ground) | 1.71 | 5.60 |
| gallery | 577-913 | 24.0-38.0 | 29 | **1.42** (ARCH_colonnade_south_column_006_LOD1) | 1.69 | 4.60 |
| approach | 925-1224 | 38.5-51.0 | 26 | **1.70** (ARCH_site_platform) | 1.68 | 5.60 |

| gate | requirement | measured | |
|---|---|---|---|
| clearance | >= 1.50 m | **1.70 m** outside the gallery | PASS |
| clearance (gallery) | >= 1.35 m (1.40 is the geometric bound; the flutes give 0.02 back) | **1.42 m** | PASS |
| level | agl >= 1.50 m; z >= WATER_Z + 0.5 = -0.80 over water | **1.68 m**; min z over water **1.60** (30 samples) | PASS |
| speed | <= 6 m/s except the water crossing <= 10 | land **5.60**, water (frames 1-404) **9.20** | PASS |
| holds | >= 3 s at the hero and under the dome | hero **3.50 s**, dome **4.17 s** | PASS |

Re-run at `--step 4` (306 samples, 41 s) to confirm the every-12 sampling was not hiding a spike: the same four gates
pass, min clearance **1.42 m** (frame 829, `column_006`), min agl **1.56 m**, the tightest ENV object is
`ENV_shrub_pitto1_1107` at **1.45 m** — a pittosporum that overhangs the colonnade walk at theta -50.8, world
~(63.5, -5.9). **Hand-off to environment:** that shrub is the only ENV object inside the gallery's clear width; if it
is meant to be off the walk it wants ~0.5 m more setback. Nothing is blocked by it — the path clears it.

### 23.4 Round-13 review carries (docs/reviews/light_r13_review.md)
- **2** `light_r13_sweep.py` now passes `energy_eevee=c["fill"]` (and keeps the Cycles energy at the shipped 0.0).
  The `fill=` key really was dead: `apply_preview_eevee` overwrites `data.energy` from `energy_W_eevee`, so `fill=0`
  rendered the full 55 W/m2. The round-13 ladder in 22.2 was measured before `apply_shade_for_engine` existed and is
  not reproducible with the old script; anyone re-running it should re-measure, not compare to those rows.
- **5** the stale paragraph above `MIST` in `light_build.py` argued for "L = 800 m ... not the 400 m of round 07's
  ramp". k = 5.0 on a 2000 m ramp **is** L = 400 m, and it is what the cam06 table below it selects. Withdrawn in
  place, with the reason: the 800 m was an atmospheric-plausibility argument, the 400 m is a measurement.
- **6** `apply_shade_for_engine` seeds a missing `energy_W` from `light_build.SHADE_FILL["energy"]` (0.0), not from
  `data.energy` (the Eevee 55). Verified on the saved rig: with the property deleted, the CYCLES branch now sets
  0.0 W/m2 and `hide_render True` on all three lamps (was 55.0 / False).
- **7** `light_probes.bake` builds and assigns the bake world **inside** the `try`, so a raise in `make_sky_world`
  can no longer leave the rig switched to CYCLES.
- **8 NOT DONE — carried to the first round that may render.** It asks for one `--cams 01v` frame through
  `apply_viewport_eevee` to show the navigable master still fits its 512 shadow pool with three more sun lamps.
  Round 14 is a no-render round; this is the one carry that needs the GPU. It is cheap (one Eevee frame).
- **9** cam06's ">= 35" std threshold was set on ENV's measurement of that crop (44.0 un-composited / 23.5
  composited); lighting measures the same crop at 59.8 / 33.8, so **38.1 is 0.64 of lighting's un-composited std, not
  the 0.86 that ">= 35" implies on env's numbers**. The two sides are not measuring the same statistic.
  **Hand-off to the lead and environment:** restate that gate as a *ratio* of the un-composited std of the same
  frame (lighting ships 38.1 / 59.8 = 0.64) rather than an absolute number, or agree one crop tool.
- **10** which frame each round-13 table is measured on is now stated in 22.2 and 22.6.
- **11** housekeeping: `light_r12_sweep` worlds renamed `R12_` and no longer leaked one per case;
  `light_r13_sheet` writes its scratch frame to the system temp dir instead of the tracked previews dir;
  `calibration_report.json` values rounded to 6 significant figures (they churned by ~1e-7 on every run);
  and the **root cause** of the 10 MB tracked panels is fixed — `apply_final_cycles` wrote 16-bit **RGBA** at
  compression 15 while `film_transparent` was False, so a quarter of every file was a constant alpha plane and the
  rest was barely deflated. It now writes RGB at compression 90, which is lossless (the RGB planes are unchanged).
  The three existing 10 MB frames are left as they are: they are the panels 22.2/22.6 cite, and re-encoding them
  losslessly needs a 16-bit PNG writer that is not on this machine (no ImageMagick, and PIL down-converts 16-bit
  RGBA on read).

### 23.5 Delivery doc
`docs/tech_notes.md` gains "Opening and rendering master.blend": the saved Eevee viewport state row by row, the two
Eevee-only rigs and the rule that every Cycles path goes through `apply_final_cycles` or `common.configure_cycles`
(never a bare engine switch + F12), the measured Cycles/Eevee wall times from QA rounds 04-05, why the 4K final
starts at 128 spp fixed rather than the saved 768 adaptive, and the flythrough test-animation recipe.

# Round 14 — the violet flood (QA-06-2), the reflection, cam03's outer row and the Eevee pass time

## 24. Round 14

### 24.0 Prep-review fix-nows and carries (docs/reviews/light_r14prep_review.md)

- **1** `light_flythrough.qa_xy(name)` looks the cam01 / cam02 / cam04 stations up in `qa_cameras.CAMERAS` by name.
  Only (x, y) is taken: the flythrough's z is an eye height over a **probed** surface, not the QA camera's z
  (cam02 stands at 1.10 in `qa_cameras`, the route at 1.06 over a walk measured at -0.69). Rebuilt: the three
  stations print (-14.1, 100.0), (70.5, 25.6), (0.0, 3.0) — unchanged, which is the point of the fix.
- **2** the station table and `cam["schedule"]["stations"][i]["note"]` read `st[5]`, not the arc theta `st[4]`;
  every note is now populated (0 lines reading `None` in `renders/logs/light_r14_fly_rebuild.log`).
- **3** the stale "gates that leg at 1.30 m" comment now says 1.35 and names `CLEAR_MIN_GALLERY`.
- **4** `--step 4` re-run with the **shipped** 1.35 gate (`renders/logs/light_r14_check_step4_shipped.log`),
  which had never been done — the committed step-4 log was measured with the older 1.25 gate:

  | gate | requirement | step 12 | **step 4, shipped gates** | |
  |---|---|---|---|---|
  | clearance, gallery | >= 1.35 m | 1.42 | **1.42** (frame 829, `column_006`) | PASS |
  | clearance, outside | >= 1.50 m | 1.70 | **1.57** (0.07 m of margin) | PASS |
  | level | agl >= 1.50; z >= -0.80 over water | 1.68 / 1.60 (30 smp) | **1.56** / 1.60 (**88** smp) | PASS |
  | speed | land <= 6, water <= 10 | 5.60 / 9.20 | **5.60 / 9.20** | PASS |
  | holds | >= 3 s each | 3.50 / 4.17 | **3.50 / 4.17** | PASS |

  The step-4 minima are the ones to quote from here on: 1.42 m in the gallery and **1.57 m outside it**, not 1.70.
- **8** the over-water gate FAILS loudly on zero samples instead of passing vacuously (`WATER_NAMES` is matched by
  literal name, so an ENV rename would otherwise have silenced it). **9** `columns()` takes
  `arch_params.COL_ARC_CENTER`. **10** the dome hold is stationary in POSITION only and deliberately so: the
  `TARGET_KEYS` empty travels (0, 2, 26) -> (0, 4.5, 45) across the hold, which is the ceiling look-up itself; the
  holds gate measures camera translation, which is what "hold" means for a hold.
- **7, the north grove.** It is not on the route because it is not near the route. Environment r8's re-solved
  conifers sit at world x -40..-61, y -29..-45 (behind the NORTH wing, 133-148 m from the hero station); the
  route's four legs are all on the south and east sides, and the closest any station comes is **56.0 m**
  (`ENV_tree_cypress_01`), with the nearest tree of any kind north of x = -40 at 42.2 m. The grove is a
  BACKGROUND mass for the hero frame — that is the job environment r8 solved it for, against ref 169's dark mass
  at frame x 0.71-0.76 — and reaching it would add ~120 m to a 250 m route, through the north wing, to look at
  trees. The five brief beats (hero hold, water crossing, colonnade walk, arch approach, dome hold) fill the 51 s.
- **5** (clearance re-run at `viewport=0`, i.e. against LOD0 foliage) stays with the Phase 5 render round, as the
  brief directs.

### 24.1 QA-06-2 — what the tint actually did, measured on an illuminant probe instead of on the master

The brief's premise is that `(1.0, 0.65, 17.0)` "cannot make a sky colour" because G < R. **Measured, it does.**
`scripts/light_r14_skyprobe.py` puts four Lambertian cards in an empty scene — up-facing, a wall with its normal
ANTI-sun, a wall facing the sun, and a wall under a 2 m soffit (the hero's shaded-attic geometry) — lights them
with the world alone and renders them through the master's own AgX + `AgX - High Contrast` + the calibrated
-2.833 EV, so a card's sRGB is directly comparable with a render box. A **neutral 0.18 grey card is the
illuminant**. On the r13 rig it reads

| grey card | sRGB | hue | sat |
|---|---|---|---|
| up-facing | (114, 162, 230) | **215.2** | 0.504 |
| wall, anti-sun | (131, 170, 243) | **219.1** | 0.459 |
| wall under a soffit | — | **218.7** | 0.476 |

i.e. the diffuse sky IS a sky colour, hue 215-219, G between R and B, because the sky it multiplies is warm enough
that a 0.65 green multiplier still leaves G/R above 1. **The defect is not the chromaticity of the light, it is how
much of it lands on surfaces that face UP.** Round 12 built two discriminators (anti-sun by direction, horizon by
ray elevation) and shipped both at **1.0, their maximum amount**, so round 12 had nothing left; and at that amount
the horizon weight barely discriminates at all. A vertical wall samples the sky about a HORIZONTAL normal (mean
|ray.z| ~0.42, mean 1-|z| ~0.58); an up-facing surface samples it about the ZENITH (E[z] = 2/3, mean 1-|z| ~0.33).
The wall keeps only **1.8x** what a roof, a walk or the lagoon's murk keeps. Measured on the ochre card, the blue
the r13 tint adds is +110.3 sRGB on the shaded wall and **+69.2 on the up-facing card** — the flood, exactly.

**Round 14's lever is the SHARPNESS of those two weights, not their amount:** `(1 - |ray.z|)^p` and
`(0.5 + 0.5 * Incoming.sun)^q`, new sockets `SKY_DIFFUSE_TINT_HORIZON_P` / `_ANTISUN_P`. It is also the more honest
shape — the anti-sun horizon band at a 7 deg sun is a band a few degrees deep, not a linear ramp from the zenith.
Blue added by the tint, ochre card, sRGB units above the untinted sky (probe logs `light_r14_probe1..3.log`):

| rig | shaded wall (soffit) | up-facing | sun-facing | wall / up |
|---|---|---|---|---|
| untinted (base) | 0 (88.7) | 0 (115.1) | 0 (111.6) | — |
| **r13 as shipped** (q1 p1, b 17) | **+110.3** | **+69.2** | **+36.0** | 1.6 |
| q1 p4, b 17 | +81.4 | +28.1 | +20.1 | 2.9 |
| q1 p8, b 17 | +59.8 | +12.3 | +12.4 | 4.9 |
| q3 p6, b 40 | +98.7 | +24.8 | +2.4 | 4.0 |
| q3 p8, b 55 | +102.7 | +22.9 | +2.5 | 4.5 |
| **q3 p10, b 80** | **+110.9** | **+23.3** | **+3.0** | **4.8** |

The last row is the one to test on the master: it delivers the shaded wall **exactly** the blue the r13 tint did
(+110.9 against +110.3), gives up-facing surfaces **34 %** of what they were getting, and takes the sun-facing wall
from +36.0 to +3.0 — which is the sunlit attic's R-B budget that 22.3 said lighting had already overspent.

### 24.2 Wave 1 on the master — the exponent works everywhere except where the shade's blue comes from

Master rebuilt in the worktree (`scripts/lead_build.sh`): **9709 objects, 11.11 M tris at LOD1, 154 MB**, probes
re-baked. Hero Cycles 1280x720 / 64 spp, cam02/03/05/06 Eevee 1280x720 / 32 TAA, `--rebake` per case.
Log `renders/logs/light_r14_w1.log` (822 s, 15 frames). Cases: `base` = the master as saved; `A` = q3 p6 b40;
`H` = q3 p10 b80.

| box (camera) | base = r13 | **A (q3 p6 b40)** | H (q3 p10 b80) | window |
|---|---|---|---|---|
| hero shaded attic | **116.2 / 31.0 / 0.382** | 113.4 / **40.5** / **0.603** | 113.8 / 40.0 / 0.581 | 103-127 / 23.5-35.5 / <= 0.50 |
| hero sunlit attic lum / sat / R-B | 182.4 / 0.470 / **102.9** | 180.8 / **0.542** / **119.1** | 180.8 / 0.540 / 118.6 | 178-201 / >= 0.50 / >= 110 |
| hero water reflection R-B | +2.1 | **+10.0** | +10.3 | >= +35 (QA-06-3) |
| hero near water sat / hue | 0.303 / 213.9 | 0.270 / 209.9 | 0.269 / 209.7 | 0.22-0.32 / 185-200 |
| cam06 roofs hue / sat | **243.7** / 0.210 | **352.2** / 0.065 | — | 22-52 (ref 105 warm) |
| cam06 plaza hue | **250.5** | **34.3 PASS** | — | 22-52 |
| cam06 trees hue | **267.4** | **32.9 PASS** | — | 23-53 |
| cam06 frame median hue / violet pixels | 230.5 / **48.7 %** | **40.7 / 27.8 %** | — | — |
| cam03 walk hue / sat | 221.5 / 0.667 | 204.2 / **0.335** | — | 25-60 (QA) |
| cam03 outer row / sunlit | 0.087 | **0.141** | — | >= 0.15 (QA-06-7) |
| cam05 water band hue / sat | 356.7 / **0.106** | **39.3 / 0.428** | — | 40-80 / >= 0.24 |
| cam02 water hue / sat | **237.8** / 0.357 | **24.4** / 0.131 | — | 185-200 |

**Three readings, and the third is the round's real finding.**

1. The exponent does what the probe said it would, on every camera except the hero: cam06's frame comes back from
   a lavender relief map (median hue 230.5, 48.7 % of pixels in hue 200-300) to a warm one (40.7, 27.8 %), the
   plaza and the trees land inside QA's own 15 deg window, cam05's water band recovers its chroma
   (sat 0.106 -> 0.428) and cam02's water leaves the violet entirely.
2. **It also closes 22.3's blocked hand-off for free.** The sunlit attic's saturation and R-B — the two numbers
   that were already outside their windows before round 14 spent anything, and that blocked the wings — go
   0.470 / 102.9 to **0.542 / 119.1**, both inside. That is the anti-sun exponent taking the tint off sun-facing
   stone, exactly as the probe predicted (+36.0 sRGB of blue -> +3.0).
3. **A and H are the same frame.** Doubling the tint (b 40 -> 80) and sharpening the weight further (p 6 -> 10)
   moves the hero's shaded attic by 0.5 lum and 0.5 deg. On a free card in the probe those two rigs differ by
   12 sRGB units of blue on the wall. They do not differ in the building, which says the hero's shaded attic does
   NOT get its blue from near-horizontal sky rays at all: 21.7 already measured that about half of it arrives
   **after a bounce off a horizontal surface**, and the horizon exponent starves horizontal surfaces by
   construction. The tint cannot be sharpened onto the hero's shade, because the hero's shade is lit by the very
   up-facing surfaces the sharpening is meant to protect.

So the round splits in two: the diffuse tint is the right tool for the sunlit/up-facing SEPARATION and the wrong
tool for delivering the shade's blue. The blue has to come from a rig with a DIRECTION — which is
`SHADE_FILL`, built in round 11, measured free in Cycles in 21.6 (spec 0, el 6: near-water 0.271 against the
control's 0.281, columns 1.08x) and shipped in round 13 as an EEVEE-only rig for a reason that no longer holds.
At elevation 5 deg a sun lamp gives a vertical wall cos(5) = 0.996 of its irradiance and an up-facing surface
sin(5) = 0.087: an **11.4x** discrimination, against the horizon exponent's best measured 4.8x.

### 24.3 Item 2 — the hero reflection's warmth: what lighting owns and what it does not

QA-06-3's new test is `water_refl` 900 760 1020 840 on the Cycles hero: **R-B >= +35**, hue 25-45, lum 124-208.
Round 06 measured +2.5 against ref 169's **+69.0**. Materials r7 reported the box is "100 % water at 22 m" and
that no sheen weight fixes it; QA's own reading is that the box's std is 58.8, i.e. it IS the rotunda's reflection
in bright streaks on dark water, and the streaks carry no stone chroma.

The geometry says which term dominates. The hero stands 2.90 m over water at -1.30 and the box is ~22 m out, so
the incidence angle is atan(22 / 2.90) = **82.5 deg from the normal**. Fresnel at 82.5 deg for IOR 1.33 is ~0.57,
so the box is roughly 57 % MIRROR and 43 % the water's own diffuse (murk + bed). The mirror at that angle looks
back up at only 7.5 deg above the horizontal, which is the horizon sky as much as it is the building — and the
ripple normals scatter it: every degree of ripple slope swings the reflected ray 2 deg, so a 5 deg ripple facet
puts the mirror on the sky instead of on the stone.

**What lighting owns in that box is the sky the mirror sees**, i.e. `SKY_GLOSSY_BOOST` (5.25) and
`SKY_GLOSSY_SATURATION` (0.90), which are invisible to camera and diffuse rays by construction. The isolation
test is one frame with the glossy sky switched off (`gb = 0.02`): whatever R-B moves is lighting's share of the
box, and whatever does not is the murk's and the roughness'.

**The isolation test, measured** (hero Cycles 1280x720 / 64 spp, `renders/logs/light_r14_w2.log`, box 900 760 1020 840):

| rig | box lum | box hue | box sat | box **R-B** | near water lum |
|---|---|---|---|---|---|
| shipped (`gb` 5.25) | 103.8 | 91.1 | 0.041 | **+2.1** | 117.9 |
| **glossy sky OFF (`gb` 0.02)** | **52.1** | **42.2** | 0.773 | **+51.6** | 9.3 |
| ref 169, aligned | 166.1 | 33.7 | 0.358 | **+69.0** | — |

So the box is a two-term sum and both terms are now measured: the reflected **building + murk** is
**52.1 lum at R-B +51.6** (warm, correctly coloured stone), and the reflected **sky** adds **+51.7 lum at
R-B -49.5**, which is what drags the sum to +2.1. QA's reading is right and materials r7's is not: the streaks do
carry stone colour, they are simply outnumbered.

**Neither end of lighting's knob passes both halves of QA-06-3's test.** At `gb` 0.02 the R-B passes (+51.6 >= +35)
and the luminance fails by a factor of 2.4 (52.1 against the 124-208 window); at the shipped 5.25 the luminance is
still only 103.8 and the R-B fails. The glossy saturation cannot buy it either: round 10 measured `gsat` at
~0.65 of near-water saturation per unit, so the ~0.55 of `gsat` that would grey the reflected sky enough takes
QA-05-4's near-water box from 0.303 to about 0.05 against its 0.22-0.32 window.

**Hand-off to materials r8, with the arithmetic.** Hold the sky term where it is and make the water's mirror of
the BUILDING 2.3x brighter — 52.1 -> ~120 lum at the same R-B +51.6 — and the box lands on the photograph:
lum 120 + 51.7 = **171.7** (window 124-208) and R-B 51.6 x (120/52.1) - 49.5 = **+69.3** against ref 169's
**+69.0**. (Display-space linearity is an approximation at these levels; the direction and the factor are not.)
The knobs are `MAT_water_lagoon`'s specular strength and roughness at 82.5 deg of incidence, its ripple normal
scale (every degree of facet slope swings the mirror 2 deg, off the stone and onto the sky), and how much of the
box the murk/bed term occupies. Lighting will not lower the glossy sky to fake it: that number is QA-05-4's
near-water window and QA-03-7 spent two rounds calibrating it.

### 24.2b Which window is right for the other four cameras — settled on the photographs

The brief asks for the four non-hero cameras' shade in **hue 195-230 at sat <= 0.35** ("a neutral cool grey-blue");
QA-06-2's own acceptance asks for the opposite — cam03's walk in **25-60** and cam06's roofs/ground/trees within
15 deg of ref 105's warm neutrals. They cannot both be met, so they were measured on the photographs
(coarse tiles, darkest quartile = the shaded surfaces):

| photograph | shaded (darkest quartile) hue / sat / lum | tiles in hue 195-230 | tiles in hue 200-300 |
|---|---|---|---|
| ref 138, the colonnade | **25.3** / 0.342 / 70.7 | 7.9 % | 13.3 % |
| ref 105, the aerial | **49.4** / 0.119 / 158.1 | **0.0 %** | 0.5 % |
| ref 169, hero shaded attic (QA) | **29.5** / 0.425 / 115.0 | — | — |

**Shaded Palace concrete photographs WARM, at hue 25-50 and low saturation, in every reference we have.** The
neutral cool grey-blue of the brief is the ILLUMINANT, not the surface, and on this rig the illuminant already is
one: the probe's neutral grey card reads **hue 215-219 at sat 0.46-0.50** (24.1). So round 14 ships against QA's
windows for the surfaces and reports the illuminant's own hue/sat as the answer to the brief's 195-230 — they are
the same requirement stated about two different things, and the confusion is what QA-06-2 is made of.

### 24.3b Wave 2-3 — the shade's blue comes back from a DIRECTIONAL rig, and the exponent keeps it off everything else

Correction to wave 1's Eevee rows: the sweep's `fill` key defaults to 0, and `build_shade_fill` builds NO lamps at
zero, so wave 1's Eevee frames were rendered **without** the r13 Eevee shade fill. Every Eevee row from wave 2 on
carries `fill=55`, the shipped value, and the wave-2 `baseE` case is the correct "before".

`SHADE_FILL` is switched on in CYCLES as well (`cfill`), at a low elevation and with the colour re-derived: round
13's (0.14, 0.19, 1.00) was solved for EEVEE's deficit, and in Cycles it adds +9 red and +12 green for its +26
blue, which moves the shade's hue the wrong way as fast as its blue moves it back. Solved again from the wave-2
deltas: **(0.03, 0.02, 1.00)**. Hero Cycles 1280x720 / 64 spp, logs `light_r14_w2.log` / `w3.log`:

| case (all on q3 p6 b40 unless noted) | hero shaded attic lum / hue / sat | sunlit sat / R-B | near water lum / sat | cam06 plaza / trees hue |
|---|---|---|---|---|---|
| `baseE` = r13 as shipped | **116.2 / 31.0 / 0.382** | 0.470 / 103.0 | 117.9 / 0.303 | 250.5 / 267.4 |
| `Af0` no fill | 113.4 / **40.5** / **0.603** | **0.542 / 119.1** | 117.0 / 0.270 | 34.3 / 32.9 |
| `Af35` fill 35 W, el 5, r13 colour | 121.8 / 39.3 / 0.500 | 0.507 / 111.6 | 148.1 / 0.235 | — |
| `Af55` fill 55 W, el 5, r13 colour | 126.2 / 38.8 / 0.453 | 0.490 / 107.9 | 157.7 / 0.212 | — |
| `F3` fill 55 W, el 5, blue colour | 117.6 / 34.6 / 0.434 | 0.496 / 108.9 | 142.9 / 0.319 | — |
| **`F1` fill 55 W, el 2, blue colour** | **117.2 / 35.3 / 0.449** | **0.501 / 110.0** | 140.0 / 0.320 | — |
| **`F2` fill 90 W, el 2, blue colour** | **119.6 / 31.6 / 0.375** | 0.478 / 104.9 | 149.0 / 0.293 | 25.4 / 23.2 |
| `P3` q3 **p3** b34, no fill | 114.0 / 39.3 / 0.561 | 0.538 / 118.2 | 117.2 / 0.280 | 343.2 / 8.6 |
| `P2` q3 **p2** b24, no fill | 113.7 / 39.6 / 0.577 | 0.539 / 118.4 | 117.3 / 0.281 | 320.9 / 0.7 |
| window / ref 169 | 103-127 / 23.5-35.5 / <= 0.50 | >= 0.50 / >= 110 | — / 0.22-0.32 | 22-52 |

**The intermediate exponent is not a way out.** `P2` and `P3` land the hero's shaded attic at hue 39.3-39.6 — no
better than p6 — while cam06's roofs are still at 255-256 and the plaza has only rotated through magenta
(321-343). Between p1 and p2 the hero's shade has already lost its blue and the aerial has not yet got its warmth
back: there is no p that does both, which is 24.2's point restated as a measurement.

**The directional fill is.** At elevation 2 deg a sun lamp gives a vertical wall cos(2) = 0.999 of its irradiance
and a horizontal one sin(2) = 0.035 — a **29x** discrimination against the horizon exponent's 4.8x — and it is
blind to the sun-facing side because those faces point away from it. `F1` and `F2` bracket the answer: at 55 W the
hero's shade sits at hue 35.3 (0.2 deg inside the window) and **both sunlit windows pass for the first time in the
project** (0.501 / 110.0, against the 0.470 / 103.0 that 22.3 declared lighting had no room to fix); at 90 W the
shade returns to the r13 rig's own 31.6 / 0.375 with 3.9 deg of margin and the sunlit pair falls back to
0.478 / 104.9, still better than the r13 rig it replaces.

The fill's one real cost is the near-water box: 117.9 -> 140-149 of luminance and hue 213.9 -> 227-228, because
the lagoon's murk takes 3.5 % of a 55-90 W/m2 blue lamp. Its SATURATION stays inside QA-05-4's window
(0.293-0.320 against 0.22-0.32); its hue moves further from the 185-200 the same defect asks for.

### 24.5 QA-06-13 — where the Eevee pass time went (measured, not guessed)

The sweep prints a per-camera wall time. Waves 1 and 2 are the same master, the same cameras and the same 32 TAA;
the only difference is that wave 1 built **no** `LIGHT_shade_fill` lamps (the sweep's `fill` key defaults to 0 and
`build_shade_fill` builds nothing at zero) and wave 2 built the shipped three at 55 W/m2:

| camera, Eevee 1280x720 / 32 TAA | wave 1, no shade lamps | wave 2, the shipped three | cost of the three lamps |
|---|---|---|---|
| cam03 colonnade walk | 54.9 s | **92.8 s** | **+69 %** |
| cam06 aerial | 31.2 s | **48.6 s** | **+56 %** |

That is QA-06-13's +81 %, isolated to its cause: **three lamps, not the world and not the probes.** And the cause
inside the cause is a default. `build_shade_fill` never set `shadow_maximum_resolution` or `use_shadow_jitter`, so
three 55-degree soft suns whose entire job is to lay a diffuse blue on shaded stone were each rendering shadow maps
at Blender's default **0.001 m/texel — finer than LIGHT_sun's own 0.002** — with jitter on. Both are now rig keys
(`SHADE_FILL["shadow_res"]`, `["shadow_jitter"]`) and are swept in 24.6.

### 24.4 What round 14 ships

| socket | round 13 | **round 14** | why |
|---|---|---|---|
| `SKY_DIFFUSE_TINT` | (1.0, 0.65, 17.0) | **(1.0, 0.65, 40.0)** | a sharp weight passes less tint; b 40 restores the shaded wall's blue at q3 p6 |
| `SKY_DIFFUSE_TINT_ANTISUN_P` | — (implicitly 1) | **3.0** | takes the tint off SUN-facing stone (probe: +36.0 -> +3.0 sRGB of blue) |
| `SKY_DIFFUSE_TINT_HORIZON_P` | — (implicitly 1) | **6.0** | takes it off UP-facing surfaces: the roofs, the walk, the lagoon's murk |
| `SHADE_FILL["energy"]` (CYCLES) | 0.0 | **70.0 W/m2** | the shade's blue now arrives from a rig with a DIRECTION |
| `SHADE_FILL["color"]` | (0.14, 0.19, 1.00) | **(0.03, 0.02, 1.00)** | the r13 colour was solved for Eevee's deficit; in Cycles it added +9 R / +12 G per +26 B |
| `SHADE_FILL` lamp elevation | 5.0 deg | **2.0 deg** | 29x discrimination between a vertical wall and a horizontal surface |
| `SHADE_FILL["shadow_res"]` | (default 0.001 m/texel) | **0.20 m/texel** | QA-06-13; 0.001 is finer than LIGHT_sun's own 0.002, for a soft fill |
| `SHADE_FILL["shadow_jitter"]` | (default True) | **False** | same |
| `SKY_DIFFUSE_BOOST`, `SKY_STRENGTH`, `SKY_CAMERA_*`, `SKY_GLOSSY_*`, `FILL`, `VAULT_FILL`, `MIST`, `COMP`, exposure | | **unchanged** | the visible sky, the lagoon's mirror and the interior fills are held still by construction |

### 24.6 QA-06-13 — the fix, measured

| case (same master, same 32 TAA, 1280x720) | cam03 | cam06 | shade quality |
|---|---|---|---|
| shade lamps at Blender's default shadows | 89.0 s | 46.1 s | cam03 walk sat 0.401; cam06 trees hue 23.2 sat 0.171 |
| **0.20 m/texel, jitter off** | **53.6 s (-40 %)** | **37.1 s (-20 %)** | cam03 walk sat **0.345**; cam06 trees hue **32.5** sat **0.244** |

The coarse map does not cost the shade — it **improves** it on every box measured, because a softer shadow from a
55-degree soft sun is what a fill of that shape should cast in the first place. The two cameras that carry the
colonnade and the aerial fall 135.1 s -> 90.7 s together, i.e. 33 % off the two most expensive frames in the set.
