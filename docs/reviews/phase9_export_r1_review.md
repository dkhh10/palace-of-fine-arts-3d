# phase9-export r1 (d6d2545) — MERGE WITH FIXES (1 blocker before the chain runs, 1 wrong claim, 3 carries)

Suites re-run here, all CPU: `belt_rule` **PASS** (far 22/17, walkup 4/35, tri deltas exactly as reported),
`--frustum` **PASS** (2 of 3 in frame, 17.7 / 11.8 px per texel), `p9_rule_selftest` **23/23**, `gate4_order_selftest`
**10/10**, `web npm test` **450 PASS**. Touched: export/ (8), docs/decisions.md, the report, phase8c_export_analysis.md
(brief item 2), web/test/foliage_lazy_test.mjs (the 4c contract) — no other phase9 branch touches those two, no binaries.
decisions.md keeps all three 2026-09-20 entries (1071, 1076, 1087) + the new 1100. The pin is 13 new checks, subset by
index. `verify_glb.trees_lod1_order_check`'s relaxation (`y[0] > x[0]`) is safe: `extra_glb_check` still pins each set's
row total against its own report.

1. **BLOCKER — the next far-tree irradiance bake hard-fails, and the file claims it cannot.**
   `export/trees_far.py:1235` writes `topology.json placements=placements`, now the far set's **149** rows, while
   `export/trees_far_set.py:173` iterates `topo["placements"]` and `:217` asserts `len(placed) == len(man["tree_far"])`
   (166). The lighting round forces that bake, so the chain dies there — and `export/trees_far.py:1197-1201` states the
   opposite ("trees_far_set.py iterates the manifest, not this list"). The `billboard_only` rows also carry no `scale` /
   `object`, so it is not a one-line patch. *Fix:* keep all 166 rows in `topology.json` with `mesh: true|false` (plus
   `scale`/`object` on the excluded ones), or rebuild the excluded rows in `trees_far_set.py` from `man["tree_far"]`.

2. **FIX NOW — "THE ONE HAND-OFF THAT GATES THE SHIP" is not what the viewer on main does.**
   `export/README.md:2879`, `docs/decisions.md:1119-1122`, `export/trees_far.py:246-253`, `export/manifest_v4.py:61-63`
   and report item 3 say a billboard-only row never gets `iIrr` and would draw ~4x too bright. But
   `web/src/main.js:1097-1100` runs `farTreeIrradiance` over **all** `manifest.treesFar`, joined **by location**
   (`foliage.js:1167`, not by mesh placement), and passes `irr` into `buildImpostors`, which writes `iIrr` at build time
   (`impostors.js:828-840`) — before any lazy load. Live proof: `renders/web/p9b_perfband_shot.json` logs "127 far + 18
   near placement(s) modulated" (main.js) *and* "127 re-lit" (foliageLazy). foliageLazy only re-writes the same value, so
   a billboard-only row keeps its modulation while the lighting list keeps its row — which this branch guarantees. What
   really changes is `activateImpostorMeshes`' `modulated` counter (166 -> 131/149), i.e. reporting. *Fix:* downgrade the
   four claims to "no viewer change required; confirm the capture note still says 166 modulated" and do not gate the
   deploy on it. Keep test 4c — its `info` line describes the harness (impostors built without `irr`), not the viewer.

3. **CARRY — `export/belt_rule.py:98` makes the `--frustum` invariant unfalsifiable at today's numbers.** `frustum_rows`
   scans only rows within `FRUSTUM_WITHIN_M = 15 m` of cam03's eye, while exclusion needs > 20 m (walkup) / > 50 m (far)
   from every eye, so the FAIL at `:201` can never fire. Checked: at scan radius 20 and 50, 0 in-frame excluded rows;
   unbounded, 34 / 17, all correctly beyond the draw distance. It does still catch a rule that stops honouring proximity
   (option (a)). *Fix:* scan to `max(DRAW_WITHIN_M) + FADE_BAND_M`, FAIL only inside the set's own radius, and call the
   check cam03-only in the README, not "a station's frame".

4. **CARRY — stale prose the script contradicts.** `export/trees_far.py:243` still says "17.9 and 11.9 SCREEN pixels"
   (corrected to 17.7 / 11.8 everywhere else) and `:239` hand-copies the cam03 station `(81.0, 12.04, 1.7)` that r1 item 3
   just removed from `p8_texel_probe.py`. *Fix:* quote `belt_rule --frustum` and drop the literal.

5. **CARRY — one key, two types.** `export/manifest_v4.py:93` does `dict(pl, mesh=True)`, so
   `trees.far_mesh.lighting.mesh.placements[].mesh` is a **bool** while `trees.walkup_mesh.placements[].mesh` (`:1142`) is
   the mesh-name **string**. *Fix:* name the flag `has_mesh`.
