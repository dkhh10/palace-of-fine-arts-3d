# Phase 6 Gate 0 — vertical slice (lead, 2026-09-15). Read docs/briefs/process.md, docs/briefs/phase6_addendum_draft.md, docs/briefs/phase6_plan.md first.

Two agents, two branches, one contract. Nothing else runs until this gate passes. Both: Opus 5; bake engineer xhigh on
branch `phase6-bake`, viewer engineer high on branch `phase6-viewer`; worktrees `.claude/worktrees/<branch>`; `git merge main`
first. Source is `master_delivery.blend` in the MAIN checkout (absolute path, gitignored, 280 MB, regenerated 2026-09-15):
open it read-only, never save it. Tools: `tools/bin/gltfpack`, `tools/bin/toktx` (prepend `tools/bin` to PATH). Every
Blender run through `scripts/blender_run.sh <honest seconds>`; every Chrome run through `scripts/chrome_run.sh`.

## The slice
- Asset: `ARCH_rotunda_column_00_LOD0` (fluted, 14 396 tris, `MAT_column_rose`; its mesh is shared by the 16 rotunda
  columns `ARCH_rotunda_column_00..15_LOD0`; export all 16 placements as instances of ONE decimated mesh).
- Ornament: `INST_capital_rotunda_000_LOD0` (the capital on that column; mesh `ORN_capital_rotunda_v?_LOD0_*` shared by
  5-7 placements, 64 000 tris, `MAT_ornament_concrete`): decimate to 6 000 with the hi->lo normal + AO bake, its own UV2
  lightmap (this is the timing for the per-instance option), exported as ONE placement. Report the three ORN options'
  numbers (addendum: unique mesh / shared PBR no lightmap / atlas offset) from what you measured: tris, texture bytes, bake
  seconds per instance.
- Ground: the object the column's base stands on (find it by a downward ray cast from the column origin, report its name;
  export it as is, with a lightmap on UV2) and the lagoon water as a viewer plane at `common.WATER_Z` (-1.3), not geometry.
- Sky: the world `WORLD_golden_hour`, two equirects (see plan section 3).

## Bake engineer (branch phase6-bake) — export/ scripts, each idempotent, each printing wall seconds and output bytes
1. `export/export_set.py --gate0`: select by name, copy the column mesh, decimate to 3 500 tris (report the real count),
   UV1 (material) + UV2 (lightmap, non-overlapping, 2K) unwrap; the ground gets UV2 only. Keep the 16 placements.
2. `export/bake_normal.py`: hi (LOD0) -> lo tangent normal map, 2K, cage extrusion measured, not guessed.
3. `export/bake_pbr.py`: albedo, roughness, normal (combined with 2) from the node tree at the final look-independent
   scene-linear values (bake type EMIT of each channel, or DIFFUSE colour + ROUGHNESS + NORMAL; state which), 2K, PNG 16-bit.
4. `export/bake_lightmap.py`: Cycles Diffuse direct+indirect, colour off, and for EVERY lightmap report min, max, mean and
   the clipped-pixel count (value > the encoding's ceiling) of the EXR and again after the conversion to the three.js
   format (RGBM8 / RGBE .hdr / half-float), so the range implied by -2.833 EV is shown to survive; `light_presets.apply_final_cycles` first (the
   Eevee-only rigs must be off; assert `LIGHT_shade_fill*` and the vault override are inactive), 128 spp + OIDN, 2K EXR,
   for the column (one bake on the shared mesh in the world position of column 00 is NOT acceptable: bake one instance,
   `ARCH_rotunda_column_00_LOD0`, and report how the other 15 would be done at Gate 3) and for the ground.
5. `export/bake_lut.py`: (a) the LUT: Blender does not expose OCIO to Python, so push an identity Hald image (level 8 or
   larger, scene-linear values loaded as an image with `Non-Color`/linear colour space) through Blender's OWN view transform
   at the scene's settings (AgX High Contrast, exposure -2.833) — e.g. composite it to the render output with `save_render`
   at the scene's view settings — and read the display-referred result back as the LUT (`.cube` 33^3 or the Hald PNG). If you
   do it any other way, write what you did and how you verified it into docs/tech_notes.md ("Phase 6 LUT"). (b) two 4096x2048 equirect EXRs of the world: camera branch and glossy
   branch (say how the branch was isolated), plus `.hdr` copies. Prove the LUT: a flat 0.18 grey plane rendered by Cycles
   must match the LUT applied to 0.18 within 1/255.
6. `export/gltf_pack.sh`: glTF export (bpy, Y-up handled by the exporter, `export_yup=True`, tangents on) -> gltfpack
   `-cc -mi -kn` -> KTX2 via toktx (UASTC, zstd, mipmaps; lightmap as RGBM8 or as a separate `.hdr`, state which), writing
   `export/out/gate0/` with `manifest.json` (assets, textures, stations from scripts/qa_cameras.py with lens/shift/sensor,
   WATER_Z, sun direction, exposure, LUT path).
7. Reference frame: Cycles 1280x720, 64 spp, of the SLICE ONLY (column x16 + capital + ground + world) from `CAM_qa_01_lagoon_hero`,
   `renders/web/gate0_cycles_cam01.png`, through the same final preset. This is what the viewer must match.
8. Report per step: wall seconds, output size, and every failure. Bake timings go into docs/briefs/phase6_plan.md
   section 4 (edit that section only). Commit after every script; last commit id in the report.

## Viewer engineer (branch phase6-viewer) — web/, no GPU work until export/out/gate0 exists
1. `web/`: Vite + three (pin the versions installed in package.json), `npm run dev` and `npm run build` -> `web/dist`.
   Loads `manifest.json`, the glb (meshopt decoder + KTX2Loader with the basis transcoder), MeshStandardMaterial with
   `lightMap` on UV2 (`lightMapIntensity` 1, the map is scene-linear irradiance x albedo already: state how you avoid
   double-lighting with the DirectionalLight, plan section 3), PMREM from the glossy sky, the camera sky as background,
   a water plane at `y = WATER_Z` with a planar Reflector, tone mapping OFF and the LUT applied in a post pass, exposure
   from the manifest. Station presets on keys 1-6 built from the manifest's Blender camera (location, rotation, lens
   36 mm sensor, shift_y): convert Blender's camera to three.js exactly (Z-up -> Y-up; fov vertical from lens and aspect;
   shift via setViewOffset or the projection matrix) and print the resulting matrix.
2. `web/tools/screenshot.mjs` (puppeteer-core on `PFA_CHROME`, headless new, window 1280x720 for this gate), waits for
   `window.__pfaReady === true`, writes `renders/web/gate0_viewer_cam01.png`; run it only through
   `scripts/chrome_run.sh 120 -- node web/tools/screenshot.mjs ...` and only while `export/out/bake_queue/status.json`
   (or the bake engineer's report) says the GPU is free.
3. Acceptance: `renders/web/gate0_pair.png` = Cycles frame | viewer frame | 50 % blend, plus a 100 % crop of the column
   and capital (both frames). Report the column's pixel bounding box in both (must agree within 1 % of frame height), the mean luminance
   of the sunlit and shaded column faces and of the sky box (x 0-300, rows 0-100) in both, and the frame time at 1280x720.
4. Report per step: wall seconds, bundle size, and every failure. Commit after every step; last commit id in the report.

## Rules for both
Report before changing anything outside your branch. No edits to assets/*.blend, scripts/*, master*.blend. No adjectives
without a number. Report < 30 lines. If a step cannot be done as written, do every other step and say exactly what was left.
