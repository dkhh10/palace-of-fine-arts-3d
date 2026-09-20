# phase9-export r2 (76774ae) — MERGE (all three r1 items closed; 2 new carries, r1 carries 3 and 5 still open)

Suites re-run here, all CPU: `belt_rule` **PASS** (far 22/17 → 149 rows, walkup 4/35 → 131, tri deltas unchanged),
`--frustum` **PASS** (2 of 3 in frame, 17.7 / 11.8 px per texel), `p9_rule_selftest` **34/34**, `gate4_order_selftest`
**10/10**, `web npm test` **450 PASS / 0 FAIL** (this branch's `web/` predates the viewer merge; main's extra tests are
`impostor_rim` / `detail_proj`, untouched here — main since the merge-base touches no file this branch touches, so the
merge is clean). Scope respected; no binaries, no other owner's files.

1. **Blocker (r1 item 1) CLOSED, verified end to end.** `trees_far.py:684-745` builds `topo_rows` for every far row; an
   excluded row gets a real object at the same scale and location in `EXP_TREEFAR_BILLBOARD_ONLY` (`:695`), and the
   glTF export selects `exp.objects` alone (`:935`), so `len(nodes) == len(placements)` at `:1015` still holds at
   149 / 131 while `topology.json` carries 166 (`:1258`). The world-bbox loop at `:773` runs over all 166, so each
   excluded row publishes its own `placed_bbox_*`. `belt_rule.topology_problems` (`:214-271`) is asserted by the writer
   (`:803`), the reader (`trees_far_set.py:110`) and 11 self-test checks.
   **Yes, the next bake now covers the billboard-only rows, and that is correct:** `trees_far_set.py:181` places every
   row, `:217`'s `len(placed) == len(man["tree_far"])` passes at 166, `hidden_src` (`:156`) already iterated all 166,
   and `irr_scope.json` / the `tfirr_*` chunks follow `placed` — so `instance_irradiance.json` regains rows for the
   excluded trees, which is the *other* consumer (`foliageLazy.loadFarTreeLighting`, the sidecar path) that would
   otherwise have lost their modulation. Bake cost +17 rows, expected.
2. **Fix-now (r1 item 2) CLOSED — the reading is right.** Re-verified against main (f6c65aa): `main.js:1101-1104` maps
   `irr` over the whole `manifest.treesFar`, `foliage.js:1160-1168` joins **by location** with no mesh filter,
   `impostors.js:951-952` writes `iIrr` at build time, `loadFarTreeLighting:215` passes rows through unfiltered.
   README:2879-2905, decisions.md:1119-1127, `trees_far.py:246-257`, `manifest_v4.py:59-64`, `viewer_change`
   (`trees_far.py:820-827`), report item 3 and `foliage_lazy_test.mjs:338-352` now agree, same 166 / 131 / 149 counter
   expectation; `grep -rn "GATES THE SHIP\|must re-light\|viewer fix"` over export/ docs/ web/test/: no hits.
   `verify_glb.py:264` does fail on a cut-down lighting list, as claimed.
3. **Finding 4 CLOSED.** `trees_far.py:239-246` quotes `belt_rule --frustum` and drops the hand-copied cam03 station and
   the 17.9 / 11.9 numbers; the printed table matches.
4. **CARRY (new) — `manifest_v4.py:95`** re-derives `object=f"TREEFAR_{b['index']:03d}"`, overriding the `object`
   `trees_far.py:735-745` now writes into `billboard_only`. *Fix:* use `b["object"]`.
5. **CARRY (new) — stale `127`** in `trees_far_set.py:177` and the `irr_scope.json` note at `:238`, where the list is
   now 166. *Fix:* quote `len(placed)`.
6. **Lead, sequencing (not a defect):** `trees_far_set.py:110` hard-fails on a `topology.json` left from the r1 head
   (149 rows) — the next bake must re-run `export/trees_far.py` (far) first; the assert names the contract, not that.
7. **r1 carries 3 (unfalsifiable `--frustum` radius) and 5 (`mesh` bool vs string) stay open**, tabled with fixes in
   `export/README.md:3017-3032`; both still true. Accepting the deferral is the lead's call.
