# Code review — phase6-viewer, Gate 4 round 5b, impostors (08e9262)

Range `0b08a6b..08e9262` (3 commits). Read-only: no Blender, Chrome, npm or script was run. Every number
is read from the source, `renders/web/imp_cam.json`, `export/bake_lm.py` / `export/gate3_common.py` or
`export/README.md`, never re-measured.

## Verdict: MERGE WITH FIXES

The frame lookup is right and it can be shown, not argued. `b2t` is `(bx,by,bz) -> (bx,bz,-by)`
(`blenderCamera.js:25`), so the shader's `vec3( d.x, -d.z, d.y )` (`impostors.js:54`) is its exact inverse
and is the manifest's `(x,-z,y)`. The fold (`impostors.js:97-100`) is the manifest's encode verbatim and
the true inverse of the bake's decode (`bake_lm.py:239-246`). The bake's lattice is `u = col/(N-1)*2-1`,
so frames sit ON the lattice points and the viewer's `g = uv01*(grid-1)` with floor + interpolation is
exactly consistent — blending three frames instead of the manifest's `round` refines the same
parameterisation rather than drifting from it.

**The V flip is correct and masks nothing.** `gate3_common._png:158` writes `arr[::-1]`, so the bottom-up
atlas array is stored top-down in the PNG; toktx's default (no `--lower_left_maps_to_s0t0`) keeps that and
stamps `KTXorientation rd`; a compressed upload cannot flip, so data row 0 is the image TOP. The manifest
counts the row AND `f.y` from the bottom, so the correct undo is one whole-atlas mirror of the composed
pixel coordinate — precisely `1.0 - (pyFromBottom + 0.5)/atlasPx` (`impostors.js:88`). Row index and
intra-frame offset are mirrored together because they are stored together; a row-only flip would have been
the wrong fix. The committed 960 px hero shows upright far trees, which is the other half.

Straight alpha is resolved the only correct way (`impostors.js:123-125`): weights sum to 1, colour is
alpha-weighted and divided by the same weighted alpha, the test precedes the divide, opaque output forces
`a = 1`. The quad is the manifest's square (`2*radius_m*s` on both axes) against a square frame, and the
capture log says `12x12 frames at 85 px on a 1024 px atlas` — the manifest states the SHIPPED geometry, so
there is no 2K/1K unit mismatch. `imp_cam.json`: `instances 127, prototypes 16, textures 16, skipped 0,
missingPrototypes []` — the whole far list, 16 draw calls.

## Fix now

1. **`impostors.js:114-115` — the upper triangle's barycentric weights are swapped.** For the triangle
   (1,1),(0,1),(1,0), solving `a(1,1)+b(0,1)+c(1,0)=(fx,fy)` gives `a = fx+fy-1`, **`b = 1-fx`** for
   vertex (0,1) and **`c = 1-fy`** for (1,0). The code pairs `c1 = gi+(0,1)` with `1-fr.y` and
   `c2 = gi+(1,0)` with `1-fr.x`. They still sum to 1, so there is no brightness error and the diagonal
   agrees by accident (`1-fy == fx` there) — but off the diagonal the blend leans on the wrong neighbour
   by up to a full cell (~15-25° of view direction) and it is **discontinuous at every cell edge**: at
   `fx -> 1` the left cell weights `(gi.x-1, gi.y+1)` by `1-fy` while the right cell at `fx = 0` weights
   `(gi.x, gi.y)` by `1-fy`. With the correct weights the two agree. One line:
   `w = vec3( fr.x + fr.y - 1.0, 1.0 - fr.x, 1.0 - fr.y );`. Re-capture cam01/cam02 after.
2. **`manifest.js:679-680`** — `grid: impRaw.grid ?? 12` is an assumed value, and `framePx`/`innerPx`/
   `gutterPx`/`atlasPx` fall back to `null`, which reaches the shader as a float uniform and turns every
   UV into NaN silently. The module's own claim is "every field READ, never assumed": refuse the block
   (a `g3notes` entry, `impostors = null`) when any of the five is missing.
3. **`web/README.md:366, 426-427`** — still say "Item 2, the far-tree impostors, is not started" and
   document `WEB_far_tree_billboard_*` as what the far trees are, instructing that they "must be reported
   as such in any tile review". QA reads this before scoring. One paragraph.

## Carry

4. **`impostors.js:105`** — `gi = min(gi, grid-2)` is applied AFTER `fr = g - gi`, so at exactly
   `uv01 = 1` the fraction is 0 against a base one cell short and the sample jumps a frame. Recompute
   `fr` after the clamp. Same file `:99-100`: hand-rolled `sign()` differs from the bake's at exactly 0.
5. **Nothing tests any of this** (`gate3_test.mjs:112` checks only `count === 16`). The fold, the cell
   weights and `s = height/heightAboveBase` are ~25 lines of pure arithmetic that port straight to a
   `.mjs` test; one would have caught finding 1 — but only if it compares against a reference barycentric
   solve and asserts continuity across a cell edge, not merely that the weights sum to 1.
6. **`impostors.js:177, 219`** — the geometry is a unit quad at the origin and every instance matrix is
   the identity; placement lives only in the vertex shader, so every scene-graph consumer sees 127 unit
   quads at the world origin. `walk.js:95-140` traverses the whole scene and is saved only by
   `OBSTACLE_RE`/`GROUND_RE` not matching `WEB_impostor_*` / `MAT_WEB_impostor_*`; any later raycast, bbox
   or cull inherits the trap. Set a bounding sphere from the instance centres and say so.
7. **Reflector double-draw** (+32 not +16 at cam01, as claimed) is correct as written: the reflection pass
   supplies the mirrored camera's `cameraPosition`, so each impostor picks the frame for the below-water
   direction — what a reflection should show — and `DoubleSide` covers the flipped winding. But
   `frustumCulled = false` on all 16 means both passes always submit; a distance/frustum cull is the cheap
   lever when 6b's budget bites.
8. **`postChain.js:70`** — `near = start, far = start + depth` is exactly the plain linear fog the export
   review (`docs/reviews/phase6_export_gate3_r3_review.md`) carried to the viewer as "~5x off near the
   camera; read the compositor block's mapping, not just start/depth". Here the guard never fires because
   `compositor.mist` is null, but main's merged manifest now populates it (20 m / 2000 m), so the refusal
   stops firing and the note will call the result `invented: false`. Already assigned; it must land before
   any scored capture turns mist on. `?mist=60` (one value) also falls back silently.
9. **`uvDequant.js:100`** — `report.skipped` now counts both "no transform recoverable" and "geometry
   already dequantised", opposite conditions, making r5-review carry 5 (`gate4.sh` fails on
   `skipped > 0`) unimplementable. Split the counters.
10. **`screenshot.mjs:134-143`, `PFA_DEV_SHARE_GPU=1`** is absent from the commit's claims and relaxes the
    CLAUDE.md "headless Chrome never concurrent with the GPU" rule. Its shape is right (bake queue still
    refused, `--perf` refused, loud banner), but a machine-rule exemption belongs in `docs/decisions.md`
    and the README, not only a code comment.
11. **Hard-coded numbers** — `ALPHA_TEST = 0.33` (`impostors.js:37`) has no stated derivation and is not
    read from the manifest; `manifest.js:728` still defaults a missing tree height to 12 m, which now
    scales an impostor instead of a grey card; `main.js:62` `parseInt` puts NaN in an `int` uniform for a
    garbage `?impdebug`. Paths are clean.
12. **Hygiene** — the new rule does NOT block the 960 px composites: `renders/web/*_cam0*.png` cannot
    match `renders/web/960/...` (a git `*` never crosses `/`), and `!renders/web/960/*` is belt-and-braces.
    Net −28 MB of PNGs, but +4120 lines of `imp_cam.json`: r5-review carry 10's sidecar half is still open.

## Closed from the r5 review

Fix-now 1 (`hero_boxes.py:21-24`, `PFA_MAIN_ROOT` first, fallback as `gate4.sh` does); 2 (`parsePost('')`
and every unrecognised value mean none, and `applyMist` returns `{refused}` without `compositor.mist` —
the capture proves both: `compositor.mist: null`, `requested "none"`, `mistSpec: null`); 3
(`gate3_test.mjs:87-89` pins `usable === 16 && blockedNoUv2 === 0`, keeping the derived equality apart);
carry 4 (`uvDequant.js:98-103`, the material neutralisation now runs past the geometry guard). The
placeholder claim holds: `main.js:492` builds `WEB_far_tree_billboard_*` only when `! impAvailable`.

## Could not verify

Nothing was executed. Taken as reported: `npm test` 144 green; every luma, draw, triangle and resident
figure beyond the four `imp_cam.json` states; whether the item 2 captures ran under `PFA_DEV_SHARE_GPU=1`;
the live manifest's impostor fields (`export/out` is gitignored — the 85 px / 1024 px geometry is read from
the capture's page log); and the `ktx info` reading of `KTXorientation rd`, which I did not run but which
the `_png` + toktx default chain independently predicts. Not a viewer defect but visible in the committed
hero: the waterline foliage reads as pale opaque cards — the export-owned `MAT_leaf_*` `alphaMode` item
already in `docs/status.md`.
