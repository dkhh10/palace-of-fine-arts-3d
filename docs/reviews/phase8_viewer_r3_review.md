# phase8b-viewer r3 (059713b) — MERGE WITH FIXES

Diff `3e513a2..059713b -- web/` in the worktree, against `docs/briefs/phase8b_viewer_fix.md`, the round
report and web/README.md "Phase 8b fix round". No Blender, no Chrome, no viewer run. `npm test` in the
worktree's `web/`: **green, 12 suites, "all passed"** (three r186).

## Verified

- **(a) the cull is correct and the claim is measured, not asserted.** `buildDistanceCull`
  (foliageLazy.js:91-144) is the far-tree block extracted verbatim; `loadFarTrees`' `out` initialises
  `chunks/drawCalls/tris` to 0 at foliageLazy.js:312-314 and nothing increments them before the call,
  so the far-tree path is behaviour-preserving. The limit closure is evaluated per frame, as before.
  **`?shrubcull=0` is a true restore path**: `o.cull === '0'` skips the chunking, the per-frame update
  AND the `frustumCulled` write, and `p8b_a_A*_perf.json` reproduces `gate9_perf.json`'s counts to the
  unit at all six stations (6 361 468 / 335, 6 344 584 / 329, 7 111 092 / 351, 3 293 588 / 184,
  6 125 874 / 320, 6 729 552 / 355). Budget default 48 is parsed defensively (`parseFloat` NaN → 48,
  `budget 0` → no chunking but still culling) and mobile differs only through `dist` (25 m vs 30 m),
  which the mobile table reflects (tighter at st1/2/4, equal at st3/5 where the chunk boundaries bind).
- **Every triangle and draw figure in the README table matches the committed JSONs exactly** (desktop
  A3/C4/A4/C5, mobile Am/Cm): all six Δ tris close against both the frame totals and the
  `tris_by_group` shrub rows; st6 → 0; st4 is single-pass (no Reflector) and its shrub row is half the
  others, as it must be. The 128-budget sweep (B/B2/B3) supports what is claimed of it. The ms column
  is honestly labelled as inside the session drift (A-vs-A 7.8 ms at st3, from the same files).
- **Reflection safety is sound, not lucky.** Mirroring across the water plane, for any point ABOVE the
  plane the mirrored camera is never nearer than the main camera, so culling on the main camera cannot
  drop a shrub the reflection would still draw; `CULL_MARGIN_M` is pure slack.
- **(b) the counter reaches by type, not by name** (main.js:2153-2170): all 21 material slots, every
  `uniforms` entry whose value `isTexture`, `userData.pfaFoliage.uniforms`, `userData.pfaDetailTextures`,
  the composer passes (`pass.material`, `pass.uniforms`, `pass.fsQuad._mesh.material`),
  `scene.background` / `scene.environment`. Render-target textures are collected FIRST into `rtTextures`
  and refused inside `addTex` (143 hits at the hero), so the one-rule replacement of the old
  pmrem special case holds and nothing is billed twice. Geometry is deduped per `BufferAttribute`
  with the old per-geometry rule kept beside it. **The arithmetic checks out end to end**:
  114.5 + 0.3 + 1 255.6 + 443.8 = 1 814.2 ✓ (p8b_b_old/new/2k `total_bytes` = 1 814 155 788);
  by-kind 1 082.14 + 67.11 + 67.11 + 33.55 + 5.59 + 0.07 = 1 255.6 ✓; the +98.0 split
  (67.1 + 25.2 + 5.6 + 0.07) ✓; old textures 1 157.6 = 1 082.14 − 25.2 + 67.11 + 33.55 ✓ against
  gate9's own 1 157 635 136; by-kind texture count 291 = `texture_sources` ✓; mobile
  73.8 + 0.3 + 236.4 + 237.4 = 547.9 ✓ against the old-counter 563.5 in `p8b_a_Am_perf.json`.
  16 × 4 194 304 × 1 B = 67.1 MB ✓ and the sky equirect 4096×2048×8 = 67.1 MB ✓.
- **(c) the method is sound.** `light_r16_measure.py` resizes each frame to `BOXES[cam]["size"]`
  (1280×720) before slicing, so reading the sweep at 1920×1080 is legitimate and the report's own
  refusal to read the 1170×2532 portrait frame with the same fixture is the right call. The four
  quoted (b*, h_ab) pairs are internally consistent (h = atan2(b*, a*) reproduces 341.8 / 297.1 / 80.6
  / 294.2 from the stated b*). The conclusion follows: the viewer is WARMER than the Cycles reference
  at all three defect boxes, the two controls (sky Δb* 0.31, frieze Δb* 0.80, sunlit chroma Δb* 0.37)
  exclude a LUT / exposure / colour-space error, and each viewer stage is neutral (`probe=0`, `lut=0`)
  or warming (`post=none` −4.3, `lighting=direct` −5 to −22). Not implementing anything is correct
  under the Phase 5 freeze, and the proposal is routed to the lead rather than taken.
- **(d) the lazy path is wired.** `trnMaps` is in `common` (main.js:1218), so `applyFoliageAlbedo`
  really does re-wrap the translucency map on both lazy roots, from the SAME `old` the albedo takes —
  the two can never diverge there — and the shared-texture conflict is noted, not silent. Test §8
  covers clamp, REPEAT, the lazy re-wrap and the warning.

## Findings

1. **fix now (doc — the figure of record)** — web/README.md:1211 and
   docs/briefs/phase8b_viewer_fix_report.md:54 give the pre-8b geometry as **261.5 MB**. It is
   **261.2** (`gate9_perf.json` `geometry_bytes` = 261 214 822, and `p8b_b_old.json`
   `geometry_bytes_before_dedup` = the same number). As printed the row contradicts its own total:
   261.5 + 0.3 + 1 157.6 + 443.8 = 1 863.2, not the 1 862.9 beside it. A restatement of the figure of
   record must be exact. Fix: 261.2 MB and Δ **−146.7**.
2. **fix now (the counter still has one blind spot of the kind item b closed)** — main.js:2153-2170
   reaches `m.uniforms` and `userData.pfaFoliage.uniforms`, but a texture written straight into
   `shader.uniforms` INSIDE `onBeforeCompile` is reachable from neither. `patchBakedMaterial` does
   exactly that: materials.js:150 `shader.uniforms.pfaLmAtlasB = { value: opts.atlasB || mat.lightMap }`,
   fed by the second lightmap atlas `tb` at lightmaps.js:266. Today it is billed only if that atlas
   happens to be some other material's `lightMap` — i.e. by luck, and the new
   `texture_bytes_by_kind` tripwire would not fire. Fix: `mat.userData.pfaLmAtlasB = opts.atlasB || mat.lightMap`
   at patch time (materials.js, outside the compile hook) and add the key to the walk, or add a
   `uniform lightmap atlas B` row. Re-report the hero figure after.
3. **fix next (item d — the eager path can still serve the two maps different wraps)** —
   foliageLazy.js:936-940 takes the translucency wrap from `srcMaps[0]` (the FIRST material of that
   name), while foliageLazy.js:958-959 gives the albedo `old.wrapS/wrapT` inside the per-material loop,
   so the LAST material wins for the albedo. Two eager materials sharing a name and disagreeing about
   wrap therefore end with albedo REPEAT and translucency CLAMP — the exact mis-serve item d exists to
   prevent; the note that fires only describes the translucency choice. Fix: choose `wrapS/wrapT` once
   and assign both maps from it.
4. **fix next (robustness of the now-shared helper)** — foliageLazy.js:116 records `centre`/`radius`
   per batch and foliageLazy.js:131-136 never uses either: the test is the ROW ORIGIN only. For an
   InstancedMesh row that is fine (`CULL_MARGIN_M` covers the crown), but a NON-instanced,
   site-spanning mesh is tested at its object origin and can be hidden while its geometry is on
   screen. Not observed here (pixel parity 0-122 px against an A-vs-A control of 134), but the helper
   is now used by two sets and will be used by more. Fix: test `lim + b.radius` when
   `! mesh.isInstancedMesh`.
5. **fix next (a code comment that a later agent will trust)** — main.js:2289 says `info_*` "must
   match" the hooked tally. It cannot: the composer's full-screen quads are not in the scene graph.
   Measured in the branch's own data (`p8b_a_C_perf.json`, station 1): 4 952 550 vs 4 952 588 tris and
   301 vs 317 draws. Reword to "must match within the post chain's full-screen quads", or the next
   round will chase a 38-triangle phantom.
6. **fix next (reproducibility)** — item c's CIELAB numbers, the strongest evidence this round
   produced, have **no committed script**: only the 960 px sheet is in the tree. CLAUDE.md requires
   everything to be reproducible from scripts. Before those numbers are quoted in a QA gate or a
   `docs/decisions.md` entry, land the measuring tool (web/tools/ or scripts/) with the frame paths
   and the box fixture it used.
7. **nit** — "128 … adds **+53 draws at cam02**" (README and report) is against the PRE-8B baseline
   (329 → 382), while foliageLazy.js:821 says "adds 41 draw calls at cam02" against budget 48
   (341 → 382). Both are true; neither names its baseline.
8. **nit** — web/tools/p7.sh:37-40 passes any `--*` argument to screenshot.mjs but leaves its VALUE
   to be swallowed as `--query <value>`. Only value-less flags (`--groups`, `--dev`) are safe; say so
   in the header line.

## Carry from phase8_viewer_r2_review items 3-6

- **3 — closed on main before this branch**: impostors.js:259 is `float i0 = min( floor( cf ), cols - 1.0 );`,
  with the test "clamps i0 to the last column" green.
- **4 — open, correctly left**: the NaN `vDirBlender` path is unchanged and is not a regression.
- **5 — half closed**: manifest.js:1145 now matches the `top` TOKEN, with a test for "merely CONTAINS
  top". The other half is **still open**: manifest.js:1081/1103 accept `rows` > 4, which `pfaBandEl`
  (a vec4) and the shader's `for ( r < 4 )` truncate silently. Not in this brief; carry.
- **6 — open on both halves, and this is the one a perf round could fairly have taken**: the band
  branch still sets `c2 = c1` at weight 0 (impostors.js:275) and still fetches it — `frameTexel( c2 … )`
  at impostors.js:318 and `sampleFrame( c2 … )` at impostors.js:340, i.e. 4 wasted taps per band
  fragment in the premul path — in the same frame cost this round spent a session measuring. And
  README:976-992, whose lines 990-992 this branch edited, still names no script for its table and perf
  line (`export/p8_atlas_probe.py viewer`, `web/tools/p8_perf_table.py`). Neither is a blocker; both
  belong in the next viewer brief.

## Verdict

**MERGE WITH FIXES.** No blocker: the cull is correct, its restore path is exact, every published
triangle, draw and byte figure reconciles against the committed captures, the counter's arithmetic is
sound, item c's conclusion follows from its numbers and stops at the freeze as it should, and item d's
lazy path is really wired. Take findings 1 and 2 before the restated resident figure is quoted at a
gate; 3-8 in the next viewer round.
