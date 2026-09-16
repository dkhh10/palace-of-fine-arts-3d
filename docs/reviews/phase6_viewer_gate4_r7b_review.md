# phase6-viewer — Gate 4 round 7b pre-merge review, DELTA 2dab197..43b1e0a

Read-only (Opus 5); no Blender, no Chrome, nothing run. Code read at 43b1e0a via `git show`; line
numbers are at 43b1e0a. Claims are checked against the committed sidecars in `renders/web/`.

**VERDICT: MERGE AFTER FIXES.** The two round-7 fix-now items are closed and the water and item 1c work
is sound: the ripple maths, the murk derivation, the per-node segment cursor and the shader gate all
check out, and `renders/web/round15_cam.json` proves 1 379/1 379 placements over 25/25 nodes with 0
page errors. Two one-line defects block a clean merge, both in the *failure* paths: the new
`ERR_ABORTED` whitelist excuses every planned URL including `arch.glb`, and a manifest node that is
missing from the scene is reported but never fails.

## Closure of the round-7 items (docs/reviews/phase6_viewer_gate4_r7_review.md)

| # | item | status | evidence at 43b1e0a |
|---|---|---|---|
| 1 fix-now | far-water uv leaves [0,1] under the grazing factor | **closed** | `water.js:246` caps `grazingRaw` at `grazingMax` (uniform 6.0, `:198`), `:247` mixes by `grazingGain` which defaults to 0 (`:170`, `:352`), `:251` hard-clamps `quv` to [0,1] and every blur tap is clamped too (`:259-262`). The round-6 multiplier is off by default and bounded when on. |
| 2 fix-now | the WIP water ships as the default, tile unjudged | **closed by decision** | docs/decisions.md 2026-09-16 "Water tile judged": the lead judged the 100 % tile and ruled "the new water is the default (settles the r7 review's fix-now 2)", with a bounded pass for a 5-8x finer ripple. The delta delivers exactly that pass. |
| 3 should-fix | `reflset=orn` default not in decisions.md | **closed** | docs/decisions.md 2026-09-16 "reflset=orn is the default reflection set" authorises it on the 0.03x measurement; `main.js:630` keeps the backdrop in the reflection (`backdrop: CFG.reflSet === 'both'`), which is what that entry says. |
| 4 should-fix | `requestfailed:` does not fail a capture | **closed, but over-broad** | `screenshot.mjs:355` adds `requestfailed:` to the gate — see FIX-NOW 1 for the exception it carries. |
| 5 should-fix | the water's airlight hardcodes the LINEAR mist shape | **open** | `water.js:281` is still `fogIntensity + (1-fogIntensity)*t` with no `mistShapeGlsl` equivalent. Carried. |
| 6 should-fix | the probe refusal misses `own.unmatched` | **closed** | `probeEnv.js:142-145`. The `pfaWantsProbeEnv` escape at `:160` is correctly scoped to the cov==0 fallback. |
| 7-8 note | duplicate murk write / `debugMode 5` undocumented | **closed** | the twin `setRGB` is gone (`water.js:321-322` is derive-then-override); debug 5 and 6 are implemented at `:273-274`. |
| 9-10 note | no test for the refusal branch; `__pfaOrbit` camera | **open** | no `web/test` change in the delta. |
| 11 note | `reflectionSet.orn` unproven from an artefact | **closed** | `round15_cam.json` `info.reflectionSet` = `{excluded 36, orn 36, backdrop 0, kept 129}`. |
| 12 note | the walk sidecar is 12.5k lines | **improved** | `round15_walk.json` 7 015 lines. |

## Findings

### fix now

1. **The `net::ERR_ABORTED` exclusion is justified by the wrong cause and covers `arch.glb`.**
   `web/tools/screenshot.mjs:354`. The comment attributes the aborts to the sky `.hdr`/`.exr` twin and
   to LRU chunk drops. In `renders/web/round15_cam.json` all **189** `requestfailed` lines are
   `ERR_ABORTED` on **189 distinct** URLs — exactly the 189 files of `load plan: 189 files`, i.e. they
   are `measurePlan()`'s own HEAD probes (`main.js:203`), which Chrome reports this way. `arch.glb` and
   `env.glb` are in that list. Failure scenario: a cancelled GET of `arch.glb` logs a byte-identical
   line, is whitelisted, and the `glb ... FAILED` diagnostic is a `note()` → `console.log`
   (`main.js:126`), which the error regex does not match — so a capture of a building-less frame exits
   0 and gets scored. Fix: ignore an abort only when `r.method() === 'HEAD'` (puppeteer exposes it), or
   drop the HEAD pass; and correct the comment and the README bullet to the real cause.
2. **A manifest node that is missing from the scene is reported but never fails.**
   `web/src/lightmaps.js:497-498` fills `out.missing`, but `:286` throws only on `ai.errors.length`, and
   the census / "NODE(S) NOT FOUND" line goes through `note()` (console.log), which the capture gate
   ignores. Failure scenario: the day an export gives a shrub node two primitives, GLTFLoader puts the
   `nodes` association on the wrapping Group only (GLTFLoader.js:4476, and the EXT_mesh_gpu_instancing
   group path at :1846), no mesh carries `pfaGltfNode`, that node's placements silently return to the
   cyan probe, and both the capture and `web/README.md`'s "throws and the viewer refuses to boot" claim
   pass. Fix: fold `missing.length` into `errors`, and route the FAILED/missing notes through
   `console.error` (the pattern already exists at `main.js:486`).

### should fix

3. **The derived screen displacement is world-axis-locked, not view-derived.** `water.js:249-250` sends
   world `slope.x` to screen x and world `slope.z` to screen y. That is only the reflected ray's
   projection for a camera looking along world Z (the hero); the horizontal term also wants the `(N·V)`
   weight that the vertical one gets for free. Failure scenario: at cam02/cam05/cam06 the ripple smears
   the reflection along the wrong screen axis, and `web/README.md`'s "read per station instead of
   fitted at the hero's 20 mm lens" is not true of the heading. Project the slope through `viewMatrix`.
4. **A non-instanced node would upload a 1-element per-vertex attribute.** `lightmaps.js:479`: for a
   plain `Mesh` (`count = 1`) the attribute is a `THREE.BufferAttribute` of 1 element bound to a
   geometry with many vertices. Failure scenario: a single-placement card that gltfpack leaves
   un-instanced draws with `INVALID_OPERATION: attempt to access out of range vertices` and vanishes.
   (The ORN slot path at `:243` has the same shape, so a shared fix is fine.)
5. **Two primitives on one node are counted twice.** `lightmaps.js:447` keys `seen` by mesh, not by
   node, so both primitive meshes of one node are bound (correctly) but `out.nodes`/`out.rows` are
   incremented twice — the "25/25, 1 379/1 379" self-check can read clean while the totals are wrong.
6. **The bloom scale is written back into the compositor object.** `main.js:446` mutates
   `comp.bloomThreshold` in place, so `postState.compositor` and every sidecar now report 12.83 as if
   it were the manifest's value; the Blender number survives nowhere. Keep both.
7. **README staleness.** `web/README.md:278` still states "Defaults `reflBlur 0.0045`, `reflSat 0.66`"
   where the code ships 0.003 / 1.0 (`water.js:340-341`); and `?instirr=`, `?bloomthr=`, `?bloomrad=`
   are missing from the URL-parameter list at `:745-752`.

### note

8. `makeWater` falsy-tests its options (`water.js:313`), so `?watercrest=0` — a collimated fan — is
   silently ignored; `main.js:105` also calls it a "spread power" where it is a half-angle in degrees.
9. `water.js:324-330` and `:348-352` write the same five uniforms twice; dead but harmless.
10. `reflSat` 1.0 and `reflBlur` 0.003 ship with no decisions.md line — the 2026-09-16 tile entry said
    reflSat 0.66 "tested at 1". The lead should log the acceptance either way.
11. `report.instanceIrradiance` is not in `__pfaInfo().gate3` (keys: own, slots, materialsCloned,
    textures*), so QA can only read the note string. Same as `vertexIrradiance`; worth exposing both.
12. Precision: at 600 m the 0.034 m wave's phase is ~1e5 rad (highp ulp ~0.016 rad) and `time`
    accumulates into the same range. The `fwidth` fade hides it at distance today; a long session or a
    closer short wave would jitter. Wrapping the phase would make it unconditional.
13. Verified sound, for the record: the analytic slope and the `(-s.x, 1, -s.z)` world normal, the
    segment cursor and its `total !== count !== spec.count` refusal, `cov == 0 → pfaInstOn 0`, the
    material clone per node (so a shared datablock cannot read a missing attribute), the chunker's
    generic `pfa*` instanced-attribute slicing (`chunking.js:67`) which covers the two new attributes,
    `uniform mat4 projectionMatrix` in the fragment stage (the renderer does set it, three.module.js:18643),
    and the throw path, which surfaces as `__pfaError` and is failed loudly by `screenshot.mjs:211-213`.

## Could not verify
Every measured number in the new README sections needs a run; the round-15 per-station table and the
item 1c census were checked against the committed sidecars only.
