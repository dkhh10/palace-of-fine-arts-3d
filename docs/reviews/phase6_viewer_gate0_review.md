MERGE WITH FIXES

`phase6-viewer` @ ef6a270 vs main. Verified good: both patch strings occur exactly once in the installed three 0.186
(`lights_physical_pars_fragment` L546 inside RE_Direct_Physical; `lights_fragment_maps`); deleting `iblIrradiance +=`
does NOT remove the lightmap (it feeds `irradiance`, consumed by RE_IndirectDiffuse) and `lightMapIntensity` is kept;
RGBM decoded linear (NoColorSpace), range 64 from `textures.*.rgbm_range`; order exposure -> log2 shaper -> LUT ->
raw framebuffer, toneMapping NONE, composer target HalfFloat/NoColorSpace, LUTCubeLoader sets LinearFilter; the shift
survives resize (fov and `e[9]*aspect` recomputed in the patched `updateProjectionMatrix`, no setViewOffset) and the
camera is confirmed independently by the 0 px column-bbox delta vs Cycles in gate0_pair.png.json; nothing generated
or > 5 MB is tracked, lockfile committed, three/vite pinned exact; gate0.sh guards the GPU before Chrome, and
screenshot.mjs closes the browser in `finally` and exits.

1. manifest.js:162-173 + main.js:274-281 — blocker (latent). `assets[].lightmap` is a texture KEY
   ("column_lightmap"), not a URL: it resolves to /assets/gate0/column_lightmap (404), sets encoding 'linear' (no
   RGBM decode, range 7 not 64) and skips the emissive path, leaving `emissiveMap` live so the lightmap renders as
   full-bright emissive. Masked today only because gltfpack puts every mesh on an UNNAMED child node (gate0.glb
   nodes 0-17), so `matchLightmap` never fires. Fix: resolve via `raw.textures[key]` and match the parent node name,
   or drop the assets[] branch and keep the in-glb emissive path.
2. main.js:316 — fix now. `res.shaperPivot` is never copied, so the manifest's `lut.shaper.pivot` is silently
   dropped and the uniform keeps 0.18. Add `res.shaperPivot = manifest.lut.shaperPivot;`.
3. manifest.js:156,171,176 — fix now. Two RGBM defaults (7.0 on the lightmaps[]/assets[] path vs `rgbmRange` 64 on
   the emissive path), and `rgbmRange` is a key-contains-'lightmap' scan falling back to 7.0 with no note: a silent
   9x brightness error. One default (`rgbmRange`) plus a `def()` note when it is absent.
4. main.js:374 + water.js:103 — fix now. Water phase is wall-clock (`elapsed()`), so any water frame
   (gate0_viewer_cam01_water.png) is not reproducible. Add `?t=<s>` freezing `u.time` for captures.
5. screenshot.mjs:31 + vite.config.js:8-9 — fix now. The main-checkout absolute path is hard-coded twice as the
   PFA_ASSETS default; use `$PFA_MAIN_ROOT/export/out`, else `path.join(REPO, 'export/out')`.
6. main.js:271 (+249-270) — fix now. The final note still says "1 without a lightmap left on stock lighting:
   GATE0_column" after the borrow block patched it, and `patchedMaterials` (3 in the QA sidecar) excludes it.
7. test/camera_test.mjs:31,44 — carry. The projection expectation `-2*shift_y*aspect` is the formula under test
   (circular); only matrix_world-vs-euler is a true Blender cross-check. Dump `calc_matrix_camera()` and compare.
8. main.js:122 — carry (Gate 2). Specular-only sun with `castShadow=false`: surfaces shadowed in the lightmap still
   take a sun highlight; needs a bake-side direct-visibility term to modulate the sun.
9. manifest.js:111-117 — carry. Sky +90 deg is a VIEWER default fitted by a 90 deg-granular sweep (33.1/1.5/19.0/21.4
   of 255), not a manifest value. Have bake_lut.py emit `sky.rotation_deg`; refine the sweep to +/-5 deg.
10. manifest.js:6 + stations_blender.json — carry. WATER_Z and the six stations are hand-copied from common.py /
    qa_cameras.py with no generator, and targets exist only in the copy. Add a dump script or export `target`.
11. carry, four small ones: main.js:313 LUTCubeLoader defaults to UnsignedByteType, so a 65^3 8-bit LUT behind a log2
    shaper quantizes the shadow end (`.setType(THREE.FloatType)` if OES_texture_float_linear is there);
    web/public/basis/* (585 kB) duplicates `three/examples/jsm/libs/basis` for the pinned three (copy at build time);
    package.json:10 `npm run shot` bypasses scripts/chrome_run.sh; screenshot.mjs:64-67 lacks the root-containment
    check vite.config.js:24 has.
12. For the lead/QA, not a code defect: gate0_pair.png.json has the sunlit column at 0.759x and the shaded column at
    0.74x of the Cycles linear value while the sky matches to 1.03x — a lightmap/material gap, not camera or LUT.
