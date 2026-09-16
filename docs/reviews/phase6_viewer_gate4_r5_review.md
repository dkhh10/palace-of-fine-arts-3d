# Code review — phase6-viewer, Gate 4 round 5 (0b08a6b)

Range `d76bee0..0b08a6b` (12 commits) plus a lighter pass over `396bd4b..d76bee0` (Gate 4 item 1, never
reviewed). Read-only: no Blender, Chrome, npm or script was run; every number below is read from the
committed sidecars, the source, or the README, never re-measured.

## Verdict: MERGE WITH FIXES

The step-0 finding is the real thing and it is proved, not argued. `gltfpack` stores TEXCOORD_n as
12-bit normalised ushorts and puts the dequantisation in `KHR_texture_transform` on the baseColor
texture, which three applies only to that texture's own channel — so TEXCOORD_1 and every
Gate-2-replaced `material.map` sampled a 1/16 x 1/16 corner. Undoing it once on the attribute
(`uvDequant.js`) is the correct place: it is done immediately after `parseAsync` and before
`processGltf`, chunking, PBR, detail and the lightmap join, so no later pass has to know anything. The
transform is READ from the glb (`texture.repeat`/`offset`, which GLTFLoader filled from the extension),
never assumed to be 16 — `round13b_cam.json` shows per-material scales of 6.08, 6.40, 6.72, 8.41, 11.3,
12.2, 13.1, 13.6, 15.2…16.0, i.e. the tighter-bbox meshes are handled correctly and an `-vpf`/`-vc`
change on the export side cannot silently break it. Idempotence is real (`geometry.userData
.pfaUvDequantized`, and `BufferGeometry.copy` carries `userData` by reference, so a clone is covered);
InstancedMesh is covered because it is `isMesh`; the chunked slot geometries are merged from already-
dequantised sources. `skipped` is 0 on all four glbs, so nothing was left behind today.
The V-flip decision is measured, not assumed (`?lmflip=1` is worse on every metric: 117.8 vs 134.3,
MAE 42.0 vs 31.1), `lightMapIntensity = pi` is right for a Cycles diffuse pass against three's
`irradiance * BRDF_Lambert`, and the sky-diffuse double count is removed per patched material
(`noEnvDiffuse` deletes `getIBLIrradiance`) and only there, so unpatched meshes keep the documented
environment-lit path. The 988/988, 16/16, max match error 0.019 m and post=null are all in the capture
sidecar, so the scored `round13b` frames were taken with no post chain at all; the tip's default
(`CFG.post ?? 'none'`) leaves the frame untouched, so those captures are still reproducible at 0b08a6b.

## Fix now

1. **`web/tools/hero_boxes.py:21`** — `MAIN = Path("/Users/dk/Projects/…")` hard-coded, no
   `PFA_MAIN_ROOT`. This is the exact defect the Gate 2 review raised as fix-now #4 for
   `check_manifest_files.py` and the export review raised for `gate3_relay_check.py`. One line:
   `os.environ.get("PFA_MAIN_ROOT")` first, as `gate4.sh:18` already does.
2. **`web/src/postChain.js:104` with `web/src/main.js:349`** — the "default is none" guarantee holds
   only when the parameter is ABSENT. `parsePost('')` returns all-on (`s === ''` falls into the `all`
   branch), and `CFG.post` is `''`, not null, for `?post=`, which `screenshot.mjs`'s `qmap`/`--query`
   can emit. An empty `post=` therefore turns on the invented mist (`MIST_NEAR_M 60`/`MIST_FAR_M 1400`)
   in a scored capture. Make `''` mean none, and/or refuse `mist` until the manifest carries
   `world.mist_settings.start/depth/falloff`. (`postState` is in `__pfaInfo`, so a capture at least
   records what it used — that is why this is one line and not a blocker.)
3. **`web/test/gate3_test.mjs:83, 91`** — two of the loosened checks are now tautologies.
   `manifest.js:683` defines `ownCount` as `Object.values(ownMaps).filter(m => m.url).length`, which is
   exactly the test's `usable`, and `selectOwnMap` sets `url` and `blocked` from the same `tex`, so
   `blocked.length === own.length - usable` cannot fail either. The suite no longer pins anything about
   the export's state — which is what it exists for. The `-kv` re-pack has landed and the capture shows
   16/16, so pin the fact: `usable === 16 && g3.blockedNoUv2 === 0`, and keep the derived checks as the
   consistency half. (The other relaxations are fine: `relaid === 7 && flagFalse.every(a => a.relaid)`
   and the new "a flag can go back" case are genuinely stronger than what they replaced, and the
   `r2.own.matched === 0` rewrite correctly encodes the new claim contract.)

## Carry

4. **`uvDequant.js:97`** — a mesh whose geometry is already dequantised `return`s before step 3, so a
   SECOND material sharing that geometry keeps `repeat = 1/16` on its own textures. Unreachable in the
   four glbs today (meshes == geometries in all four reports), but it is the same class of bug as the
   one just fixed. Move the material neutralisation above the geometry guard.
5. **`uvDequant.js:30-41`** — the transform is recoverable only FROM a texture. A material with no
   texture at all yields `xf = null`, the geometry keeps its 1/16 UVs, and the later PBR / detail /
   lightmap pass then assigns a map that samples the 1/16 window silently. `skipped` is 0 today and the
   note prints it; make `gate4.sh` fail on `skipped > 0`, and cover the case in `uv_dequant_test.mjs`,
   which does not test it.
6. **`uvDequant.js:98`** — a rotated transform is counted, then DROPPED: rotation is zeroed on the
   texture and never applied to the attribute, so the mesh renders wrong with only a note. 0 today;
   it should throw.
7. **`walk.js:131`** — any obstacle footprint wider than 60 m in x or z is skipped ("a merged mass, not
   a column"), so the walker passes straight through merged architecture; only columns and small ORN
   stop it. `walk_test.mjs` covers a 1 m box, a kerb and a lintel, not a merged wall.
8. **`walk.js:147-155`** — `groundAt` takes the MAX over a 3x3 half-cell neighbourhood, so at a wall or
   step edge the walker's feet snap up to the highest surface within ~1 m, up to a cell early. The
   probe's `minGround` is insensitive to it, so "ground clamp" is evidenced for the lagoon but not for
   step edges.
9. **`postChain.js:30-38`** — `patchFogChunk` replaces `THREE.ShaderChunk.fog_fragment` process-wide,
   one-shot, with strength and falloff baked in as constants, and is NOT guarded by `once()` the way
   every other shader patch in `materials.js` is. A three upgrade renaming that chunk's contents fails
   silently instead of throwing. Same file: the patch can never be re-applied with different
   parameters within a page.
10. **Repo hygiene** — the two ranges add ~58 MB of 1920x1080 PNGs and ~100 k lines of sidecar JSON
    under `renders/web/`, of which ~20 MB are one-shot A/B frames (`dq1`, `dq1flip`, `dq2water`,
    `dq3water`, `dq4vi`, `wA`, `wB`, `c03grey`, `c03grey2`, `c03fix`, `_flip0/1`). CLAUDE.md commits
    "QA screenshots at 960 px". The station captures follow the Gate 1/2 precedent; the diagnostics do
    not. Lead's call, but `.gitignore` should grow a rule before the next round (the pair sheets are
    already correctly ignored — only their `.png.json` sidecars are tracked).
11. **`web/README.md:241`** — "All 114 meshes across the four glbs … scale 8.41..16.0" is pre-merge;
    the round13b capture reports 116 meshes and 6.08..16.0. Stale by one re-pack.
12. **`water.js:77-86`** — `reflBlur` adds four extra `texture2DProj` taps per water fragment,
    unweighted box, at a screen-space-constant radius, and the reflection RT stays 1024² at 1440p.
    Cheap today (2.3 ms GPU at the hero) but it is the one term that scales with water coverage; revisit
    at the mobile pass. The calibration itself is honest — swept, tabulated, and R-B deliberately left
    at 0.66x pending the near-tree irradiance.

## Gate 2 carries

Closed on this branch: fix-now 1 (`main.js:980`, the PMREM is no longer double-billed), 2
(`gate2.sh:43` runs `check_manifest_files.py`), 3 (`.gitignore:44-45`), 4 (`check_manifest_files.py:20`
honours `PFA_MAIN_ROOT`), 7 (`chunking.js:94` copies `matrix`); carries 8 (`pbr.js:147` sets `csOf`
before the await), 9 (`pbr.js:211` no longer applies the Gate 2 scale to a kept normal), 12 (`MAT_SLOTS`
now lists `envMap`/`bumpMap`/`displacementMap`/`specularMap`, and `maxChunks` is gone), 13
(`screenshot.mjs:121-127` carries the `status.json` + `pgrep` guard), 6 (README no longer quotes the
unlike pair). Still open: 5 (backdrop, export-owned), 10 (`kept_glb_ao` is still structurally 0 at
`pbr.js:142`), 11 (`qmap` still lets `--query station=/size=` override the flags, and the nearest-first
order is still computed for the first station only).

## Could not verify

Nothing was executed. Unverified, taken as reported: `npm test` 140 checks green; the UV2-vs-npz IoU
0.994-0.999 (the tool reads plausibly and the 0.003 before-figure is the right control, but the IoU is
an occupancy overlap and would not catch a sub-texel shift); the hero luma 117.5 -> 134.3 and the
post/water/perf tables; the 24 walk probes and the -1.22 m minimum; the 1440p fps table and the claim
that the frame is CPU/compositor-bound (the `gl.finish` method at `main.js:1036` is sound for a render
cost — untimed warm frame first, median of 60, no vsync — but it measures the renderer, not the gap it
is being used to attribute, which the README correctly says is the open half of item 6). Also not
verified: that gltfpack's texcoord quantisation really is per material rather than per primitive; the
committed per-geometry scales are consistent with per-material, and the measured IoU is the evidence
that matters, but if that ever changes the material-keyed lookup is where it would break.
