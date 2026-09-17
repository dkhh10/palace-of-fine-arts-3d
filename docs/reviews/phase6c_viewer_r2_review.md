# phase6-viewer 6c round 2 — MERGE WITH FIXES (nothing structural; four small fixes, five carries)

Range `063c100..1dc121d`, pinned; `git merge-tree main 1dc121d` clean (main c067ab1). The viewer's commits touch only `web/`,
`renders/web/`, `.gitignore`; no tracked binary over 5 MB. **Round-1 blocker and fix-nows 1-5 closed, with carries 6 and 9.** The dissolve
partitions: mesh discards `hash >= vPfaFade` (foliage.js:262), impostor `hash < 1 - vPfaFade` (impostors.js:125), mesh fade `1-t` vs
impostor `t`, both ends correct (`treemesh=inf` → impostor keeps nothing, `0` → mesh keeps nothing); `foliage_lazy_test.mjs` proves it
numerically. Fix-nows 2-5 and carry 6 are closed in code (re-crowned bark, clamped switches, `keepMeshAlways`, `drawnGeom` plus the three
info fields, `bytes2k`). COLOR_0 decode matches the manifest's prose encode (`vColor^2 * range`, matched by regex not token) and alpha is
forced opaque so MASK cannot eat the canopy. The shrub mask indexes through `pfaChunk.indices` (chunking.js:96, foliageLazy.js:829-839) with
a length check, and the LOD2 materials are per-node clones, so no chunk can be written at the wrong row (1 376/1 376 over 25 nodes, 3
masked). The far-tree join is Blender-keyed (`toBlender` = (x,-z,y)) and refuses on an unjoined row; the placement gate reports centre 0.73
m max / 0.254 median over 127. Sidecars carry every cited number: 30.1/33.5/32.7/22.7/31.8/33.5 ms, MAE
26.52/20.08/33.94/13.12/22.22/**20.59** (README says 20.58), resident 1 717.4 MB, far box 1.284x + hp9/mid/std, bare URL real
(impmod full, 145 modulated, 254/254 lit, 0 shader errors) and the walk-in coordinates recorded.

1. **Fix now — `web/test/foliage_lazy_test.mjs:21`**: `path.resolve( import.meta.dirname, '../../..' )` is one level
   too high (web/test → `<repo>/..`), so `npm test` exits 1 in the worktree *and* in MAIN. Fix: `'../..'`, as every
   other test does. With `PFA_MAIN_ROOT` set, all checks pass (I ran it).
2. **Fix now — 16 full-resolution A/B PNGs, 30.6 MB, committed** (`renders/web/r16b_*.png`, `smoke_*.png`): the brief
   said commit the JSON and the 960 px copy and gitignore the rest; these match no ignore pattern. Fix: `git rm
   --cached` and add both globs to `.gitignore`.
3. **Fix now — `web/README.md:1010-1021`**: the switch list omits `?farao=`, `?fartrn=`, `?shrubenv=` entirely
   (`?fartreemesh=` is prose-only at :780), so "every default" does not hold. Fix: add the four with their defaults.
4. **Fix now — `web/src/foliage.js:604-618`**: `RATIO_CLAMP = 4.0` and the zero-channel fallback are hardcoded while the
   manifest ships `trees.far_mesh.lighting.impostor.{strength, clamp, zero_channel_fallback}`; `strength` is unimplemented
   (a no-op at 1.0) and chroma never clamps although its comment says it does. Values coincide today, so no pixel is
   wrong. Fix: read the three from the block, defaulting to the constants.
5. **Carry — the number justifying the 12 m default is in no sidecar.** README:775 cites 1.957x / hp9 34.56 at 40 m;
   1.284x is committed but no committed capture ran `?fartreemesh=40` (round-1 carry 7 recurs for the decisive
   measurement). Fix: re-run that one A/B through `foliage_boxes.py --json` and commit it.
6. **Carry — `foliageLazy.js:341-375`**: the E_placement join is an exact 2-dp key with no tolerance and no fallback
   once the bake block exists; a missed row drops silently to the probe (254/254 today). Fix: error when `lit < rows`.
7. **Carry — `foliageLazy.js:494-505`**: a placement whose crown is not clustered is skipped from `byId`, so its
   impostor keeps `iNear = 0` (always drawn) while its mesh still fades in at 12 m — both drawn inside 12 m, the mirror
   of round-1 finding 4. 127/127 matched today. Fix: report the reverse count and keep those meshes off.
8. **Carry — the 0.9995 guard**: inside it both sides keep ~0.05 % of the pixels (an overlap, never a hole, so invisible) — the README's "exact" claim wants that clause.
9. **Carry — decisions**: the 12 m far-tree switch (against the brief's `treeMeshDist`) and `?farao=1` (AO on
   `iblIrradiance`/`radiance`, beyond the manifest's stated COLOR_0 use) live only in web/README.md; the lead should
   ratify both in docs/decisions.md before Gate 4.
