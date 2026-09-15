MERGE WITH FIXES (1 and 2 before gate1.sh is run for score)

`phase6-viewer` @ 02ccbf3 vs main, web/ only. Verified good: `direct`-mode units are right — three 0.186 has no legacy
light scaling (WebGLLights.js:332 is `color * intensity`) and RE_Direct_Physical's BRDF_Lambert divides by pi, so a
DirectionalLight at `energy_w_m2` 67.32 reproduces Cycles' irradiance exactly; no lux/W factor is missing and the frames
will not be wildly bright (sunlit grey lands ~3.4 EV over pivot, inside the shaper's 4.026 ceiling). No sky double-count:
both equirects are baked with the sun disc off (gate0 `sky.verification`). InstancedMesh culling is correct in 0.186
(`boundingSphere` null-not-undefined, `Frustum.intersectsObject` computes it over the instance matrices); instance TRS
comes from the exporter's own Y-up glb, never re-rotated; `seenMats` patches each shared material once. `__pfaRenderCost`
(gl.finish) is clean and `residentBytes` a real byte sum from KTX2 mip data + attribute lengths. Determinism holds: pixelRatio 1, `?t=0` freezes the water, billboards re-aim only on camera move,
stations come from the manifest by NAME (CAM_flythrough correctly lands at 7). `npm test` passes against the real gate1
manifest (max euler-vs-look-at diff 3.0e-6) and `dump_stations.py --check` is clean. Tracked files clean: 26 files,
largest 527 kB (basis, carry 11b), lockfile committed, node_modules/dist/public/assets ignored, `npm run shot` and
gate1.sh both go through chrome_run.sh.

1. manifest.js:66 — **blocker**. manifest v2 writes the glbs as `glb.per_class = {arch:{path,bytes,…}, orn, env,
   ground}` (export/gltf_pack.sh:69), but the pick list is `glbs | glb.parts | glb.files | glb.classes | files.glbs`;
   `listOf(raw.glb)` then walks `per_class` / `total_bytes` / `gltfpack` and finds no url, so `glbs = []` and boot()
   falls into `buildTestScene` — Gate 1 would capture six frames of the test scene with no error. The v2 fixture
   (testdata/v2shape) and README:45 both assume a top-level `glbs`, which no exporter writes. Fix: add
   `'glb.per_class'` to the pick list (arch/orn/env/ground insertion order is already the load order); fix README:45
   and :50 (`tree_far`, not `trees.far[]`).
2. main.js:584-588 + 657-678 — **fix now**. `animate()` keeps its own rAF render running while `__pfaFrameStats` drives
   a second one, so every tick renders the scene TWICE and the reported "median presented frame time over 120 frames"
   is up to 2x the real value (the gl.finish cost is unaffected — that loop is synchronous). Fix: a `measuring` flag
   that makes `animate` skip `renderFrame` while the stats promise is open.
3. main.js:623-656 — fix now. `residentBytes` omits every render target: the composer's two HalfFloat `samples:4`
   buffers (~30 MB each pre-MSAA at 1440p), the water Reflector's 1024^2 and the PMREM cubeUV (no `image`, so `addTex`
   adds 0) — the dominant part of the GPU-memory figure. Fix: add a `render_target_bytes`.
4. gate1.sh:17-19 — fix now. The status.json + pgrep guard runs once, then `npm run build` and two Chrome sessions
   follow: the 1440p pass (line 29) starts minutes later with no re-check ("before each run"). Fix: a `guard()` called
   again before line 29.
5. billboards.js:33 — carry (Gate 3). The placeholder material never goes through `patchBakedMaterial`, so under
   `baked` it takes the full unshadowed 67.3 W/m2 sun diffuse while everything around it is specular-only.
6. main.js:599 — carry. `renderer.info.programs` is top-level, so perf `programs` is always null (one line).
7. main.js:319-326 — carry. In `direct` mode the diffuse irradiance is PMREM'd from the GLOSSY-branch equirect (the
   bake isolates camera vs glossy only), so a diffuse-branch difference in the Phase 5 world would go unnoticed.
8. test/camera_test.mjs:19-24 — carry. Without `PFA_MAIN_ROOT` there is no export/out in the worktree, every
   orientation cross-check skips and the run still exits 0. Fail when all stations skip.
