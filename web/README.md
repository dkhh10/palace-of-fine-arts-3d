# PFA web viewer (Phase 6)

Three.js viewer for the baked slice: the frozen Phase 5 look (AgX High Contrast at -2.833 EV) with
three.js tone mapping OFF and a 3D LUT baked from Blender's OCIO.

## Carries from the Gate 0 code review (docs/reviews/phase6_viewer_gate0_review.md)
- **7** `test/camera_test.mjs` checks the shift formula against itself; dump Blender's
  `calc_matrix_camera()` and compare instead. Only matrix_world-vs-euler is a true cross-check today.
- **8** (Gate 2) The specular-only sun has `castShadow = false`, so a surface shadowed in the lightmap
  still takes a sun highlight. Needs a bake-side direct-visibility term to modulate the sun.
- **9** `sky.rotation_deg` is read from the manifest when present; the +90 deg fallback was fitted by a
  90 deg-granular sweep (33.1 / 1.5 / 19.0 / 21.4 of 255). Have `bake_lut.py` emit it and refine to +/-5 deg.
- **10** `src/stations_blender.json` and `WATER_Z` are hand-copied from `scripts/qa_cameras.py` /
  `scripts/common.py`; no generator, and look-at targets exist only in the copy.
- **11** `LUTCubeLoader` defaults to `UnsignedByteType`, so a 65^3 8-bit LUT behind a log2 shaper quantizes
  the shadow end (`setType(FloatType)` where `OES_texture_float_linear` exists); `public/basis/*` (585 kB)
  duplicates `three/examples/jsm/libs/basis` (copy at build time); `npm run shot` bypasses
  `scripts/chrome_run.sh`. The static server's root containment check is done.

## Run
    export PFA_MAIN_ROOT="/path/to/the main checkout"   # holds export/out (the bake output)
    npm install
    npm run dev          # /assets/* is served straight from $PFA_MAIN_ROOT/export/out, never copied
    npm run build        # -> web/dist (2.0 MB: index 780 kB, basis transcoder 576 kB)

URL parameters: `?station=1..6` (keys 1-6 too), `?size=WxH`, `?water=0`, `?lut=0`, `?testlut=identity|gamma22`,
`?test=1`, `?exposure=`, `?skyrot=`, `?sun=`, `?lmscale=`, `?haze=` (diagnostic constant airlight, not the
real mist), `?unlit=share|stock|black`, `?t=<seconds>` (freezes the water phase), `?hud=0`.

## Screenshots (never launch Chrome any other way)
    scripts/chrome_run.sh 300 -- node web/tools/screenshot.mjs --station 1 --size 1280x720 \
        --frames 120 --out renders/web/gate0_viewer_cam01.png --probe GATE0_column_lit
Check the GPU first (`export/out/bake_queue/status.json` idle, no Blender). `web/tools/gate0.sh` does the
guard, build, screenshot and pair sheet in one go.

## Manifest fields (schema pfa-phase6-gate0/1)
`glb.path`; `stations.<name>` (location, rotation_euler_xyz, lens_mm, sensor_width_mm, sensor_fit, shift_x/y,
clip_start/end); `water.viewer_y`; `view.exposure_ev`; `lut` (path, size, shaper.min_ev/max_ev/pivot,
exposure_applied_by); `sky.camera.hdr`, `sky.glossy.hdr`, `sky.rotation_deg`; `sun` (direction_blender =
direction of travel, energy_w_m2, color); `textures.*.rgbm_range`; `lightmap_scale`; `assets[].lightmap`
(a KEY into `textures`). The lightmap ships inside the glb as `emissiveTexture` on TEXCOORD_1: the viewer
moves it to `lightMap` channel 1, forces linear colour space, decodes RGBM8 and zeroes the emissive.
