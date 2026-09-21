# phase9-viewer-shade2 r2 (764e9ab) — MERGE WITH FIXES

Opus 5, read-only, no Blender, no Chrome. `main...HEAD` = 8 files, all in scope (web/src, web/test, web/README.md,
export/manifest_v4.py + test). No binaries; worktree clean; MAIN's export/out not written (its manifest is still
2026-09-19 23:39, the mirror has no symlinks). `npm test` in the worktree: **771 checks, 0 failures**.

**Verified independently** (re-ran the fitter on the mirrored `sky_diffuse_1024x512.exr`, 12.7 s CPU)
1. Reproduces exactly: open E/pi (2.195763, 3.432181, 11.255903); **zenith 11.3205 vs quadrature 11.2559 = 1.00574x**;
   axis normals lobes/exact 0.982 / 0.996 / 0.994 / 0.987; **blue p50 0.534 % / p95 2.985 %** (SH9 1.228x at the zenith,
   p95 41.5 %, 113x at the nadir — shipping lobes over SH9 is supported by its own numbers). Two runs, byte-identical
   lobes and SH: **deterministic**. r1 finding 1 closed — I wrote a vertically flipped EXR and `manifest_v4.py:398-402` aborts.
2. **Axes.** The shipped lobe nearest `sun.direction_blender` (negated, b2t) is at **dot 0.997** and is by far the reddest
   (r/b 203); an azimuth or handedness error could not produce that. Independent of `sky.rotation_deg`, as claimed.
3. **GLSL.** three 0.186 declares `geometryNormal` in `lights_fragment_begin`, which precedes `lights_fragment_maps`, so
   `materials.js:159` is in scope; texel divided by `lightMapIntensity` first; `radiance += iblRadiance * pfaSkyVis` is the
   only IBL-specular accumulation and `directSpecular *= pfaSunVis` runs before `lights_fragment_end`; `dotNL` uses the same
   `b2t(sun.toSunBlender)` that places the light (main.js:652-655 vs 1575). `?specgate=0` emits no GLSL and no key term,
   `?specgate=1` is round 1, three distinct keys; the slot-atlas path takes the gate (both `#include <common>` patches coexist).
4. **Item 3 holds.** cam03 near column (0.989, 0, −0.147): E0 (4.70 r, 5.43 b), dotNL 0.596 → skyVis **0.0162**, sunVis
   **0.0000** (r1: 0.0078 / 0.0016). ~0 in both rounds, so the residual 1.45x is not specular. Manifest cost **+9 734 B raw**, exact.

**Findings**
1. `web/test/spec_gate_test.mjs:397-400` — **fix now.** §10b pins B.6's *absolute* skyVis (0.008/0.036/0.084 ±0.001) against
   the **shipped** constants — what §6 was rewritten to stop doing. MAIN's sky was re-baked at 07:17 (open blue 11.256 →
   5.825, be8610b's own note): once `manifest_v4.py` runs in MAIN these read 0.0150/0.0685/0.161 and **fail**. Fix:
   `near( specGateEval(rgb, live, [0,1,0]).skyVis, specGateEval(rgb, live).skyVis, 1e-3 )` — the stated invariant, sky-independent.
2. `export/manifest_v4.py:446-447` — carry. "six axis normals within 1.3 %, p95 2.8 %" is not what the code measures: east
   wall **1.77 %**, nadir 0 vs 0.0227, p95 **2.99 %**. README:1253 has the right numbers.
3. `web/README.md:1346` — carry (r1 finding 3, still open): the chain table says "690 checks"; it is **771**.
4. `export/manifest_v4.py:731` — carry. r1 finding 5 is fixed the right way (warning + `scene_audit_stale`), but nothing
   asserts the flag is false: a stale audit ships as one stderr line. One row in `manifest_test.mjs` closes it.
5. `web/src/manifest.js:582` / `main.js:1576` — carry, operational. Without `sky.diffuse_lobes` the gate goes **fully OFF**
   (B.6's 2.55x veil returns), not back to round 1. MAIN has no such block today: run `manifest_v4.py` in MAIN before the
   capture or the deployed viewer is ungated. The viewer does say so in its notes.
6. `web/test/spec_gate_test.mjs:280-296` — carry. The "1.0/1.0 at five normals" identity uses a **uniform-sky** fixture where
   E0(n) is constant, so it cannot catch an axis error in the fitted lobes; the shipped sky is checked only at the zenith.
   Assert finding-2-above's sun/reddest-lobe relation, or the walls' `lobes_over_exact_b`.
7. `web/src/materials.js:159` — carry. `inverseTransformDirection` is `@deprecated r185` in three 0.186; and `geometryNormal`
   there is the **normal-mapped** shading normal, not the geometric one the lightmap was baked against.
8. `web/README.md:1257-1268` — carry. The "r19 re-bake" column (5.825, 1.013x, the partition table) was measured on MAIN's
   re-baked sky, not mirrored here and with no committed producer: name the file and its timestamp.
9. Brief deviation, **accepted**: the shade end is unchanged only at the *upward* normal (skyVis rises elsewhere — attic east
   0.0078 → 0.0358 — which is the fix; sunVis 0.0016 → 0.0123 at the zenith preserves `sunVis*dotNL`). Cost is stated (40 dots
   + 40 vec2 mads ≈ 360 flops per lightmapped fragment) but **unmeasured**: the 6a ≥ 45 fps gate needs a 1440p median in the window.
