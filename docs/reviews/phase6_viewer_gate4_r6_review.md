# phase6-viewer — Gate 4 round 6 pre-merge review (8d76e7d..2d267ba)

Read-only (Opus 5); nothing was run. Nothing outside `web/` is touched except `renders/web/` QA
artefacts; no new hard-coded paths (gate4.sh's `MAIN=` default is pre-existing context).

**VERDICT: MERGE BLOCKED.** The code is well made and the reflection-layer work is sound, but the
probe never actually reaches the GPU: finding 1 is a blocker, and every probe-derived conclusion
since viewer c79b7b6 — QA-13-1's closure, the `?probespec=1` lead, the round-14 numbers — was
measured on a **black** cube. Fix 1-7, re-run the probe A/B, re-state QA-13-1, then merge.

## Findings

1. **fix now — BLOCKER. The probe cube is never uploaded; the PMREM is black.**
   `web/src/probeEnv.js:46` builds `new THREE.CubeTexture( texs.map( t => t.image ) )`. three 0.186
   picks the data path from `texture.image[0].isDataTexture` (`three.module.js:12450`); RGBELoader's
   `.image` is a bare `{data,width,height}`, so all six faces take the DOM-source branch and
   `texSubImage2D` throws — and `WebGLState.texSubImage2D` (`three.module.js:10659`) **swallows** it,
   so nothing propagates to the `try/catch` at `main.js:518`. Evidence in the committed capture:
   `renders/web/round14_cam.json` pageLog has six
   `THREE.WebGLState: TypeError: Failed to execute 'texSubImage2D' … Overload resolution failed.`
   immediately before `probe env: 6 x 512 px HDR cube … convolved to irradiance in 0.22 s`.
   `texStorage2D` allocated the storage, so the cube is zero-filled: the 15 materials get a BLACK
   `envMap`, which **overrides** `scene.environment` and therefore **removes** their sky irradiance
   rather than adding the warm bounce. That reproduces every reported symptom (blue → amber-brown,
   band B>R 15.5 % → 0.2 %, foliage amber where Cycles is olive) as an artefact of deleting the blue
   sky. `?probespec=1` sets the same black texture as the baked materials' specular env, so the
   "G > R 21.7 → 17.2 %" lead on QA-12b-1 is likewise just "glossy env removed".
   Fix: `new THREE.CubeTexture( texs )` (keep `type/format/colorSpace` from `texs[0]`); dispose the
   DataTextures only after `fromCubemap`.
   Everything *else* checks out: face order `px,nx,py,ny,pz,nz` and the manifest's `axes` are three's
   own cube convention, so no re-ordering is right; RGBE is decoded exactly once by the loader
   (HalfFloat, colorSpace copied, `flipY` already false); identity `envMapRotation` is correct here.

2. **fix now — a scored capture must fail on a page error.** `web/tools/screenshot.mjs:190-193`
   records `error:` / `pageerror:` into `pageLog` and never acts on it; `web/tools/gate4.sh` checks
   nothing. Six WebGL errors passed through a Gate capture unnoticed. Exit non-zero (or print a loud
   `[shot] PAGE ERRORS` banner) when pageLog holds any `error:`/`pageerror:` line, with an opt-out
   env var and the first-request 404 whitelisted.

3. **fix now — `__pfaOrbit` renders without the ornament.** `web/src/main.js:1018` builds a *new*
   `PerspectiveCamera` and never calls `camera.layers.enableAll()` (which `applyStation` does at
   `main.js:925`). With the default `?reflset=orn` the 436 ORN meshes are on layer 2 only, so every
   orbit frame — the impostor rotational-pop sweep — is shot with all ornament invisible. One line.

4. **fix now — `__pfaPick` can no longer see ORN.** `main.js:1278` uses a default `Raycaster`, whose
   layer mask is layer 0; `Raycaster.intersectObject` tests `object.layers`
   (`three.core.js:56752`), so after `reduceReflectionSet()` a pick over an ornament silently reports
   the surface behind it. `rc.layers.enableAll()`.

5. **fix now — the probe CAN mask a failed slot lightmap.** For `own` maps the order is safe
   (`web/src/lightmaps.js:230` patches before the fetch, so a failed texture renders black and shows
   itself). For the 988 instance **slots** `patchBakedMaterial` runs only inside the `.then`, after
   `if ( ! ta ) return;` (`lightmaps.js:248-253`), and the "no uv1" branch (`lightmaps.js:224`)
   `continue`s without patching. Such a material ends with neither `pfaPatched` nor `lightMap`, so
   `applyProbeEnv` (`probeEnv.js:85-88`) hands it the probe and it looks plausibly lit instead of
   black. Guard: pass the planned-material set into `applyProbeEnv` and skip it, or refuse the probe
   pass outright and note loudly when `gate3Report.texturesFailed.length` or
   `slots.applied < slots.expected`.

6. **fix now (one-liner) — preset precedence.** `main.js:29-30` compares `qs.get( 'quality' )`
   **un-lowercased** while `CFG.quality` is lowercased at `main.js:28`, so `?quality=FAST` reports
   the fast preset and silently runs full-res bloom and a 1024 Reflector. Use `CFG.quality`. An
   unknown value (`?quality=potato`) is also accepted and echoed as a preset name — reject anything
   but `look|fast`. `?bloomres` / `?reflres` overriding the preset is right, and `?reflset` defaults
   to `orn` for both presets, which matches the README.

7. **fix now — restore the README section.** Confirmed: `## QA notes — read before scoring (Gate 4 /
   QA 14)` exists at `184d785^:web/README.md:344-379` and is absent at 184d785 and at 2d267ba —
   collateral of rewriting the Performance table directly above it. **No other section was lost**
   (the heading lists are otherwise identical; the Performance heading was rewritten in place).
   Restore from `git show 184d785^:web/README.md`, and add finding 1 to it: the reference-repointing
   table it carries is still the standing QA guidance.

8. **carry — the layer trick itself is correct.** `Reflector.onBeforeRender` calls
   `this.getReflectionCamera( camera )` (`Reflector.js:118`), so the instance override at
   `web/src/water.js:367` is used and re-applies `layers.set( 0 )` on every call, covering cameras
   cloned later; `sunLight.castShadow = false` (`main.js:343`) means the mask cannot leak into shadow
   rendering; `walk.js` clamps on a rasterised heightfield, not raycasts, so the ground clamp and the
   lagoon test are unaffected. Two residuals: ORN is matched by root name `WEB_glb_orn`
   (`water.js:353`), which survives chunking only by inheritance — confirm once that
   `reflectionSet.orn` still equals the ORN mesh count after chunking; and the layer is never
   restored, so switching back to `full` in-session needs a reload.

9. **carry — the tests could not have caught this.** `gate3_test.mjs:68-73` does assert against the
   real `export/out/gate3/manifest.json` (good); `post_probe_test.mjs` covers `applyProbeEnv` only
   and never `buildProbeEnv`, which needs a GPU. Hence finding 2, plus an `__pfaInfo.probeEnv`
   luminance readback so a report can prove the cube is not black.

10. **carry — QA artefacts.** ~41k lines of sidecar JSON under `renders/web/`; it is what made
    finding 1 provable, so keep the practice (trim `round14_walk.json`, 12.5k lines). Unexplained in
    the same capture: eight `GL_INVALID_OPERATION: glGenerateMipmap` warnings (they precede the
    probe) and one 404 on the first request. One README line each.

## Could not verify
The perf tables, "173 green", the presented medians and the fast-vs-look deltas all need a run.
Finding 1's pixel consequence is inferred from the committed page log plus three's source, not from a
re-render; a corrected probe may move the `look`/`fast` deltas too.
