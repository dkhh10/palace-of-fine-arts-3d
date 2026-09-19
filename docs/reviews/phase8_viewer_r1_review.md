# phase8-viewer r1 (f0ad577) — MERGE WITH FIXES

Diff a7fbfc9...f0ad577. No Blender, no Chrome, no edits.

## Verified- **No manufactured opacity.** `covMag = mix( covRamp, clamp( a ), share )` (impostors.js:329) is convex, so coverage never
  exceeds `max( Phase-7 ramp, a )`; `pfaCov = mix( pfaCov, covMag, magT )` is 0-weighted at mag ≤ magLo. The ramp half can
  raise coverage for texels just *below* `alphaTest` (the +0.5 offset over a widened `covW`), bounded at 0.5 and < 1 texel of
  silhouette growth — intended edge softening, not opacity.
- **`impcov=0` bypass.** Preprocessing the fragment source for every define combination: with no `PFA_IMP_COV` the cov block
  and `pfaBayer4` vanish and the Phase 7 `a < alphaTest` discard is restored; the moved discard is semantically identical.
- **Dither.** `pfaBayer4( gl_FragCoord.xy )` is screen-space, integer-celled, deterministic per pixel; compiled only under
  `#ifndef PFA_IMP_A2C`, i.e. only when no coverage mask is written (verified per combination, not from the test).
- **Ramp per texel.** `pfaMag = 1 / ( innerPx * max( |d vQuadUv| ) )` matches `frameTexel`'s own `g * innerPx` (impostors.js:182),
  so it is atlas texels, not screen; `innerPx` follows the 2K variant (impostors.js:556), so mag halves for free.
- **detailproj.** Flipped only at the URL layer (main.js:106); the committed capture sidecars confirm `p8cproj` → dominant and
  `p8cbase` (`?detailproj=objxy`) → objxy.
- **A/B arithmetic.** `p8_perf_table.py` on the committed perf JSONs reproduces the README table exactly (31.85 / 30.75 −1.10 /
  31.95 +0.10 / 34.40 +2.55 / 36.75 +4.90; draws 355/399/439/575; −243.9 MB); same session, default first and repeated last.
- Images 960 px; no file > 5 MB; `node test/impostor_cov_test.mjs` at f0ad577 passes and is wired into `npm test`.

## Findings
1. **fix now** — export/tiers.py:287-299 (unchanged on main and at f0ad577) pops `albedo_2k`/`normal_depth_2k` from the
   published manifest for *both* variants, which contradicts web/README.md "Deliverable B" ("the manifest publishes each
   `albedo_2k` with the 1K as its tier-0 stand-in"). The `p8k2` capture got 16/16, so its manifest did not come from this code
   path. Fallback is graceful (1K + `atlas2kMissing` note), but confirm with the export owner or re-run the export before the
   claim and the `imp2k` default ship.
2. **fix now** — web/test/impostor_cov_test.mjs:183 `! p.includes( '#define PFA_IMP_A2C' )` is vacuous (the source carries no
   `#define`), so "the ordered dither is the no-mask fallback" can never fail. Fix: `! ( 'PFA_IMP_A2C' in combo )`.
3. **fix now (doc)** — README calls `renders/web/960/p8ship_crown_tile.jpg` "the required tile sheet … shipped", but `p8ship`
   was captured at `atlas2k=false`, `objxy`. The shipped default is 2K + 0.15 + dominant; cite the p8k2 / p8cproj tiles.
4. **carry** — web/src/main.js:407 `impTier` omits `p.albedo2k`/`normalDepth2k`, so "no 2K before tier 1" holds only because the
   export tiers both atlases together. Fix: `impTier = Math.max( ..., CFG.imp2k ? tierOf( p.albedo2k ) : 0 )`.
5. **carry** — impostors.js:145 comment labels `pfaImpCov.z/.w` "coverage quantum q, gamma"; they are share and ramp. And
   `parseImpCov`'s docstring says `samples` "sets the coverage quantum the ordered dither works against" — it does not (4x4
   Bayer regardless); it only sets the report/boot-note flag.
6. **carry** — detail.js:256 an unknown `?detailproj=` value silently falls back to objxy while detail.js:420 prints the raw
   string; with dominant as the default a typo now silently restores the old look. No test pins the new default (impcov's is).
7. **carry** — 6.56 MB / 37 capture sidecars added under renders/web; they hold no measurements (`pixels`/`probes` null) and
   their PNGs are gitignored. Keep p8base/p8ship/p8k2/p8cproj plus the five perf JSONs; prune the sweep's.
