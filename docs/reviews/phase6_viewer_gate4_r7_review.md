# phase6-viewer — Gate 4 round 7 pre-merge review (8d76e7d..2dab197)

Read-only (Opus 5); nothing was run, no Blender, no Chrome. Code read at the fixed commit 2dab197 via
`git show`; commits after 2dab197 are out of scope. Line numbers are at 2dab197.

**VERDICT: MERGE AFTER FIXES.** All seven round-6 fix-now items are closed and the probe fix is the
right one, verified against three 0.186's own upload path. What blocks a clean merge is the round-6
WIP water: its new values are the **shipped default** while the engineer's own commit message records
five of six acceptance metrics NOT MET and the 100 % tile unjudged, and the grazing term it adds is
unbounded enough to sample outside the reflection target. Land the rest; land the water behind
`grazingGain = 0` (which the code documents as an exact revert) until the lead judges the tile.

## Closure of the round-6 fix-now items (docs/reviews/phase6_viewer_gate4_r6_review.md)

| # | item | status | evidence at 2dab197 |
|---|---|---|---|
| 1 | probe cube never uploaded / PMREM black | **closed** | `web/src/probeEnv.js:52` now `new THREE.CubeTexture( texs )` with `type/format/colorSpace` copied from `texs[0]` (:53-55) — three takes the data path from `texture.image[0].isDataTexture`, which a DataTexture satisfies. Belt and braces added: a CPU per-face non-zero check that refuses before the GPU (:61-72) and a 5-point `readRenderTargetPixels` on the PMREM atlas that refuses a black convolution (:84-104). DataTextures are disposed only after `fromCubemap` (:76, :106). |
| 2 | a scored capture must fail on a page error | **closed** | `web/tools/screenshot.mjs:345-346` filters `error:`/`pageerror:`/`httperror:`/`Failed to execute` (so the swallowed `THREE.WebGLState: … texSubImage2D` warning is caught), :353-360 prints a loud banner and sets `pageErrorExit`, :400 exits 5; `PFA_ALLOW_PAGE_ERRORS=1` is the opt-out. A new `response` listener (:194) records the URL a bare 404 console line lacks. Propagation verified: `scripts/chrome_run.sh:19-23` returns the child rc, `web/tools/gate4.sh:21` is `set -e`. |
| 3 | `__pfaOrbit` rendered without the ornament | **closed** | `web/src/main.js:1050` `camera.layers.enableAll()` on the new orbit camera. |
| 4 | `__pfaPick` could not see ORN | **closed** | `web/src/main.js:1311` `rc.layers.enableAll()`. |
| 5 | the probe could mask a failed slot lightmap | **closed** | `web/src/probeEnv.js:133-144` refuses the whole pass on `texturesFailed`, `slots.matched > slots.applied`, or `slots.noUv2Attribute`. Field names check out against `web/src/lightmaps.js:95-96,217,256`. Correctly *excludes* `own.noUv2Attribute`, which is a near-miss counter (`lightmaps.js:161-165`), not a failure — including it would have refused the probe on every real run (`renders/web/round14_cam.json` has `own.noUv2Attribute` 1 with slots 988/988 clean). |
| 6 | `?quality` precedence / unknown values | **closed** | `web/src/main.js:42-43` lowercases once and rejects anything but `look|fast`; `:426` reports the rejection instead of echoing the raw value. |
| 7 | the lost README QA-notes section | **closed** | `web/README.md:444-507`, restored and extended with the round-14 black-cube void note and the re-measured probe table. |

## Findings

### fix now

1. **The water's grazing term samples outside the reflection target.** `web/src/water.js:124-127`:
   `grazingRaw` is clamped to 40 and multiplies both uv offsets, with the shipped defaults
   `distortion 0.10`, `distortAniso 4`, `grazingGain 1` (:213-217). At the hero's near water
   `dot(V,N)` is ~0.1-0.3, so the vertical offset is `n.y * 0.1 * 4 * (3…10)` — up to most of an NDC
   unit, and at the far water far more than one. The Reflector's target is ClampToEdge, so
   `texture2DProj` returns the RT border: the far water is smeared edge texels rather than a
   reflection. Failure scenario: the delivery hero ships a band of stretched border pixels along the
   far lagoon that no metric in `water_probe.py`'s two crops looks at. Clamp the projected
   `uv.xy / uv.w` to [0,1] (or cap `grazing` near 6) before the gather.
2. **The WIP water ships as the default look with its acceptance unmet and the 100 % tile unjudged.**
   `web/src/water.js:213-217` make the round-6 values the defaults (distortion 0.10, normalScale 0.5,
   rippleTiling 0.11, distortAniso 4, grazingGain 1, reflBlur 0.0045 → 0.003, waves 14 → 22). The
   commit message itself reports rowHF 4.60 vs an acceptance of 6.6-26.5, lum 0.58x, hue 199 vs 145,
   sat 0.292 vs 0.041, Fresnel not monotone, and "the 100 % tile has NOT been judged". decisions.md
   2026-09-16 ("Probe re-measured on the real cube") states the metric alone cannot accept this fix —
   **the lead judges the open-water tile**. Failure scenario: the merge silently changes the frozen
   Phase 5 hero water to a surface nobody has looked at. Merge with `grazingGain: 0` as the default
   (the file documents it as an exact round-14 revert) and flip it after the tile judgement.

### should fix

3. **`?reflset=orn` is the default for the `look` preset, which the decision does not say.**
   `web/src/main.js:56`. decisions.md 2026-09-16 "Gate 4 frame rate" puts `reflset=orn` inside the
   **fast** preset and says the default "ships the full look … everything on"; `web/README.md:397`
   says `look` includes `reflset=orn`. One of the two is wrong. Failure scenario: delivery ships a
   hero reflection with 436 ORN instances missing on an undocumented default. Either add the
   decisions.md line (the 0.03x measurement supports it) or default `look` to `full`.
4. **A failed request does not fail a scored capture.** `web/tools/screenshot.mjs:345-346`: the
   `requestfailed:` lines pushed at :193 do not match the pageErrors regex, and their console twin
   (`error: Failed to load resource`) is explicitly whitelisted. Only an HTTP >= 400 is caught.
   Failure scenario: a glb or lightmap whose fetch is aborted or fails at the network layer renders
   the scene incomplete and the capture still exits 0. Add `|^requestfailed:` to the regex.
5. **The water's airlight hardcodes the LINEAR mist shape.** `web/src/water.js:153-156` computes
   `mist = intensity + (1-intensity) * t` with no `mistShapeGlsl` equivalent, while
   `web/src/postChain.js:61-62` applies `t`, `t*t` or `sqrt(t)` from `compositor.mist.falloff`. Both
   match `scripts/light_build.py:281,299-300` (`MIST` LINEAR, `cap * (1 - exp(-k * mist))`, cap 0.25,
   k 5) **today**. Failure scenario: the day the export supplies a QUADRATIC falloff, the water is the
   one surface in the frame hazed on a different curve, silently.
6. **The probe refusal misses `own.unmatched`.** `web/src/probeEnv.js:133-137` checks the slot path
   and `texturesFailed` but not `gate3Report.own.unmatched` (0 today). Failure scenario: an own asset
   that never matched a mesh gets no lightmap, is never patched, and the probe makes it look
   plausibly lit instead of black — exactly the masking finding 5 set out to prevent.

### note

7. `web/src/water.js:188` and `:203` are the same `if ( o.murk ) u.murk.value.setRGB(...)` line twice,
   and `:190` is superseded by `:213`; dead but harmless.
8. `web/src/water.js:105-107` documents `debugMode 5 = |ripple offset|`; only 1-4 are implemented
   (:147-150). `?waterdebug=5` silently renders the normal surface.
9. `web/test/post_probe_test.mjs:82-90` never exercises the new `gate3Report` refusal branch, and
   `buildProbeEnv` still has no test (it needs a GPU). The regression that finding 1 fixed would still
   not be caught by `npm test`; the read-back note in the page log is the only guard.
10. `__pfaOrbit` (`web/src/main.js:1046-1059`) replaces the module camera with a non-station camera and
    never restores it, and `screenshot.mjs` runs `--orbit` (:292-304) before `--pick`/`--pixels`
    (:307-341). A run combining them reports picks against the last orbit heading.
11. Carry from r6 finding 8, still unverified from a committed artefact: `reflectionSet.orn` vs the ORN
    mesh count after chunking. `renders/web/round14_cam.json` predates the feature (`reflectionSet`
    and `quality` are both null in it), so no sidecar in this range proves the 436 were matched by
    `rootOf` (`web/src/water.js:257,262`). One number in the next capture closes it.
12. `renders/web/round14_walk.json` is 12.5k lines. Trim as suggested last round; the rest of the
    sidecar practice is what made both findings provable and should stay.

## Could not verify
Every measured number in `web/README.md` (the preset table, the re-measured probe A/B, the water
probe figures) needs a run. The probe fix is verified by reading three 0.186's cube upload path, not
by a render; the black-cube guard now makes a repeat self-reporting either way.
