# Code review — `phase8d-env` belt r2 (head 0748e42, 4 commits after the main merge)

Reviewer: Claude Fable 5.1, read-only, no Blender, no Chrome. Judged from the scripts, the committed JSON /
plan table / commit messages, and the export code the belt feeds (`export/gate1_set.py`, `export/gate3_set.py`,
`export/p8d_pin.py`). The .blend is binary and was not opened.

## Verdict: **MERGE WITH FIXES**

The belt is built the right way. Every load-bearing claim in the brief checks out arithmetically or structurally:
the 39 trees go down the existing far-tree path, all 12 prototypes resolve to already-baked atlases, the icosphere
belt is off with nothing else in the backdrop rebuild touched, and the export pin window still holds with
`near 20` unchanged. The fixes below are one real (small) geometry overshoot, one missing hand-off file the
export r2 brief already points at, and two robustness/hygiene items. None of them justifies holding the merge or
re-running the 40-minute env build before the master rebuild.

---

## 1. Same far-tree path, no existing tree moved — **verified (1 of 1 blocking check)**

`hall_belt()` returns ordinary plan tuples `(species, x, y, h, note)` tagged `"HB …"`, and `build_all` appends
them with `plan = plan + hall_belt(...)` as the **last** step inside the `if colonnade_polys and hall_poly:`
block — after `land_snap`, `shadow_relief`, `frame_band_relief`, the second `land_snap` and the gallery gate
(`scripts/env_trees.py:1321-1327`). The invariant holds for three independent reasons, all readable in the code:

* **Plan order.** Nothing after the append re-sorts `plan`. Entries `0..N-1` keep their index `i`, so
  `seed = seeds[i % len(seeds)]` (`:1338`) is unchanged for every existing tree.
* **RNG.** `rnd = random.Random(77)` is created *after* the append and is consumed strictly in plan order, so
  `rot`, `sx/sy/sz`, `tilt` for trees `0..N-1` are the same draws as before. `hall_belt` uses its own
  `random.Random(8104)` and never touches the module-level `random`, so it cannot perturb the stream.
* **Names.** `per_species_idx` is a running counter in plan order → belt trees get the indices *after* the
  existing ones (first belt cypress is `ENV_tree_cypress_33`), no existing name is reused or shifted.

Committed before/after evidence: the `PLAN_TABLE` in `docs/environment_notes.md` is a pure-addition diff — rows
0–130 are untouched, rows 131–169 are the 39 new `HB` entries. (The table carries species/x/y/height only;
rotation and scale are covered by the RNG argument above, not by the table.)

Classification: `note` starts with `"H"`, so `far = True` at `:1347` — the same branch the existing `H`
backdrop rows and the `E2/E3` screen rows take. LOD0 object carries the `_LOD1` mesh, LOD1 object carries the
`_LOD2` mesh, LOD2 unchanged. Adding `"HB"` to the `light` tuple at `:1350` is **redundant** (the `far` branch
already substitutes `lods[2]` at `lod == 1`) but harmless and self-documenting. Naming is `ENV_tree_<species>_NN_LODn`
throughout — clean for `scripts/qa_name_sweep.py` (no placeholder/proxy/fill/card/block token; `cypress_column`
is a species, not a "column" object).

## 2. Prototypes — **all 12 are inside the baked 16, no atlas re-bake** ✔

`docs/phase8d_belt_r2_trees.json` records 12 distinct prototypes over the 39 trees:
`cypress_s3 (7), cypress_s41 (4), cypress_s17 (3), pine_s29 (4), pine_s7 (2), eucalyptus_s61 (4),
eucalyptus_s23 (2), eucalyptus_s5 (1), redwood_s43 (3), redwood_s13 (3), cypress_column_s2 (3),
cypress_column_s31 (3)` — all `_LOD2`.

`export/gate3_set.py:216-221` builds `proto_map[p] = p[:-5] + "_LOD1"` for every far row, so each of the 12
`_LOD2` keys resolves to a `_LOD1` prototype. The baked set is exactly the 16 `ENV_tree_*_LOD1` names that
appear across the gate1/gate3/band logs, and **all 12 targets are in it**, including the three that until now
only ever appeared as LOD1-direct far trees (`pine_s29`, `cypress_column_s2`, `cypress_column_s31`). `protos =
sorted(set(proto_map.values()))` is therefore unchanged at 16 → **no new octahedral atlas, no new band atlas**.
The JSON's `prototype` field is the LOD1 *object's mesh name*, which is precisely `tree_far[i].prototype` in
`gate1_set.py:709` — the key the export and `impostors.prototype_map` join on. The field is correct as
documented. Willow and broadleaf (the shore species) are correctly absent.

## 3. Icosphere belt off, backdrop otherwise untouched ✔

`scripts/env_backdrop.py` diff is two hunks: `BELT_ICOSPHERE = False` plus the guarded call. `build_hall_belt`
is dead code kept as the record of the measured east-face geometry — justified, and it is *inert*: it uses its
own `random.Random(8004)` (siblings use `Random(3)` and `Random(9)`), and `env_city._canopy_mesh(name, seed,…)`
seeds its own `Random(seed)`. So dropping the call **cannot** shift `build_houses` / `build_landscape` /
`env_city` output by an RNG side effect — the usual way a removal like this silently rewrites a backdrop.
`ENV_src_hallbelt_*` meshes and `ENV_backdrop_hall_belt_0..3` objects simply disappear; `env_backdrop` tris
158 639 → 151 739 (−6 900), matching `docs/status.md`.

## 4. Tri arithmetic and the export pin — **checks out, `near 20` survives** ✔

Export-side (`gate1_set.py`):

* Belt LOD1 objects carry `_LOD2` meshes → excluded from `within` at `:637` → **every belt tree lands in `far`**
  → 39 × 2-tri billboards = **+78**. `far_billboards` 127 → **166**, `lod2_blob_objects` 46 → **85**,
  `trees_total` 147 → **186**, `within_radius` **28 unchanged** (the `_LOD2` exclusion precedes the radius test).
* `env_so_far` loses the 6 900 icosphere tris; `tree_allow = CLASS_BUDGET["ENV"] − env_so_far − shrub_est −
  2*len(tree_rows)` (`:654`) therefore goes 398 894 (pre-8d baseline) − 78 = **398 816**.
* `near_tris_used` 391 908 → headroom **6 908**. `docs/briefs/phase8d_analysis.md:40` measured the cheapest
  additional thinned candidate at **12 892**, so no 21st near tree is pulled in: `near_exported` **stays 20**,
  the near list stays identical in content *and* order (`within` is a stable sort over a set the belt cannot
  enter). The net move against the pin window (−5 900 … +6 986) is **−78** — comfortably inside it.
* **ENV placed = 894 974 + 78 = 895 052 = 901 874 − 6 900 + 78.** The lead's arithmetic is exactly right;
  the delta against the currently merged state is **−6 822**.

Scene-side (from the commit messages, not independently verifiable without Blender): ENV LOD0
13 916 262 → 15 444 910 (**+1 528 648**, ≈39 k per tree — the LOD1 crown the far path gives LOD0), LOD1 and LOD2
both +54 400 (≈1.4 k per tree), objects 5 929 → 6 042 (= +39×3 − 4 icospheres, consistent). **Flag for the lead:
LOD0 grows 11 %.** That is the Cycles cost of master.blend and master_delivery.blend, not an export cost, but the
4K hero and the delivery re-pack will feel it. `assets/environment.blend` itself shrank slightly (191 172 863 →
191 106 435 B) because the belt is instanced meshes, not new geometry.

## 5. Heights, spacing, determinism, idempotency

* **Spacing method is sound.** The fine 1 m walk with the gap measured along the local face tangent *from the
  last tree actually planted* is the right fix for the 10–16 m holes the first build left where the hall face
  turns; the two commit messages carry the measured before/after (hall-wall share of through-rays: frame-left
  20.4 % → 6.7 % → 3.3 %, frame-right → 1.1 %, cam05 → 0.8 %). Dealing the species from a shuffled deck rather
  than 29 independent draws is the right call and is documented at the constant.
* **Determinism:** single seeded `Random(8104)`, draws made unconditionally per 1 m sample (so the stream does
  not depend on acceptance), deterministic deck reshuffle. Same `hall_poly` → same belt. **Idempotent:**
  collections are rebuilt by `env_build`, the belt adds no global state.
* **Finding A (fix): the 16.0 m "hard cap in world z" is not hard.** `hall_belt` caps `h` at
  `HALL_BELT_TOP_Z − z0`, but `build_all` then applies a per-object `sz = scale * rnd.uniform(0.94, 1.08)`
  (`:1357`) — *after* the cap. Reconstructing the jitter per prototype from the committed JSON (`scale[2]`
  vs `height_m`, median = nominal), the realised crown tops run **11.1 – 17.0 m world z**: two trees
  (`ENV_tree_cypress_42`, `ENV_tree_redwood_31`) reach ≈17.0 m, i.e. **≈0.3 m above the hall's 16.7 m parapet
  top**, not 0.7 m below it as the docstring states. Still 3.0 m below the 20.0 m roof crest, so the reference
  read ("the roof line shows above the belt") survives, and at ~145 m it is ~4 px of foliage over a parapet
  edge. **Recommended fix: correct the docstring now; change `HALL_BELT_TOP_Z` to `16.0 / 1.08 ≈ 14.8` (or apply
  the cap after the jitter) only if the QA tile review reports a crown over the roofline** — it is not worth a
  40-minute env rebuild on its own.
* **Finding B (latent): `hall_belt.blocked()` has no lagoon/land test.** The belt is appended *after* both
  `land_snap` passes, so a belt tree in the water would be neither snapped nor caught by the PLAN-ERROR raise.
  I tested all 39 coordinates against `reference/plans/site_local.json` (`lagoon0/1/2` via `osm_to_world`):
  **none is in the water, the closest is 15.4 m from a lagoon vertex**, so nothing is wrong today. Add
  `lagoon_field` to the keep-out (or run the belt through `land_snap`) before the hall footprint or the
  terrain ever moves.

## 6. The probe — reproducible, caveats stated ✔ (one hygiene item)

`scripts/env_belt_probe.py` is committed, CPU-deterministic, takes `--bands` and `--env`, and its band boxes are
identical to `scripts/qa_r22_probe.BACKDROP[0:3]`. Two real harness caveats are written into the code where they
bite: the cast runs at **LOD1 because `hide_viewport`, not `hide_render`, is what the depsgraph honours** (so the
reported crown coverage is an upper bound and the residual hall share a lower bound), and **positive `shift_y`
puts the horizon below centre** (the first run aimed the band at the lagoon). The sheet labels the previews as
the Eevee preview harness (placeholder sun, AgX Base, −0.8 EV), i.e. not the delivery look — correctly stated.
*Hygiene:* the band boxes are re-declared rather than imported from `qa_r22_probe`, and `env_belt_sheet.OUT` is a
hard-coded `.claude/worktrees/phase8d-env/...` path that will be wrong once the branch is merged — make it
`ROOT`-relative. Also: the probe's numbers live only in commit messages; nothing in `docs/` carries them (see
Finding C).

## 7. Risk to the export chain r2 (`docs/briefs/phase8d_export_r2.md`)

1. **`export/p8d_pin.py` fails by design and must be updated first.** It pins `trees_total`, `far_billboards`,
   `lod2_blob_objects` and `tree_far_list` "identical in content AND order", and `EXPECT_ENV_DELTA = 6900`.
   New expectations: `trees_total 186`, `far_billboards 166`, `lod2_blob_objects 85`, `within_radius 28`,
   `near_exported 20`, `near_tris_used 391 908`, `EXPECT_ENV_DELTA = 78` (vs MAIN pre-8d).
2. **The far-tree re-sort is an INTERLEAVE, not an append — the brief's "first 127 rows byte-identical" will
   not hold.** `gate1_set.py:281` iterates `bpy.data.objects`, which Blender keeps name-sorted, so the belt's
   `ENV_tree_cypress_33…46` land *inside* the cypress block, ahead of every `cypress_column`, `eucalyptus`,
   `pine`, `redwood` and `willow` far tree. Every `TREEFAR_###` index after the first insertion shifts. The
   manifest is regenerated wholesale and the viewer joins by index within one manifest, so this is self-consistent
   — but the correct pin is "the same 127 `(source_tree, prototype, trunk_base)` tuples, re-sorted by object
   name", and any diagnostic pinned to a literal placement (`trees_far_ratio_check.PLACEMENT = "TREEFAR_000"`,
   `p8e_leaf_probe`'s `TREEFAR_000/001/116/117`, the `imp_diag_*` scripts) now points at a different tree.
3. **`prototype_map` resolves 39/39 with no re-bake** (§2). The three prototypes new to the `_LOD2` key space
   (`pine_s29`, `cypress_column_s2/s31`) map onto LOD1 atlases that already exist — the export should assert this
   rather than assume it, as the brief says.
4. **Vertex AO / the LOD2 mobile block.** `trees_far_compose.py` keys `vertex_ao.npz` per **LOD2 mesh name** and
   hard-fails on a vertex-count mismatch. The belt adds three prototype LOD2 meshes that were not previously in
   the far block, plus 39 placements. The brief's "stated stand-in AO" escape is the right call; the hard failure
   is on topology, not on placement count, so the three new meshes are the only thing that needs an AO array.
5. **Gate 2:** the `backdrop_forest` merged group lost 6 900 tris, so its merged geometry — and therefore its
   Gate-2-generated UV1 — changed. A backdrop re-bake is required; the other groups are untouched.
6. **`CLASS_BUDGET["ENV"]`.** Either choice is safe: leave it at 902 000 (the move is −78 against the pin
   baseline, inside the window) or move it by the placed delta as the brief says (tree_allow then returns to
   391 994 ≥ near_tris_used 391 908, so `near 20` still holds). Say which in the pin log; don't do both.

## 8. Finding C (fix, blocking for the export agent, not for the merge)

`docs/briefs/phase8d_export_r2.md` tells the export engineer to read **`docs/briefs/phase8d_belt_r2_report.md`**
— that file does not exist on the branch. The numbers (N, species mix, per-LOD deltas, probe percentages,
prototype list) exist only in the four commit messages and in `docs/phase8d_belt_r2_trees.json`. Write the report
(or re-point the brief at the JSON + `git log`) before dispatching the export agent.

## Fix list

| # | Fix | Severity | Blocks merge |
|---|-----|----------|--------------|
| A | Top cap is pre-jitter: realised tops reach 17.0 m, 0.3 m over the parapet. Correct the docstring; lower `HALL_BELT_TOP_Z` only if QA's tile review sees it. | low | no |
| B | `hall_belt.blocked()` has no lagoon/land keep-out (verified clean today: 0/39 in water, min 15.4 m). | low, latent | no |
| C | Write `docs/briefs/phase8d_belt_r2_report.md` — the export r2 brief already points at it. | medium | no (blocks the export dispatch) |
| D | `env_belt_sheet.OUT` hard-codes the worktree path; make it `ROOT`-relative. Import the band boxes from `qa_r22_probe` instead of re-declaring them. | hygiene | no |
| E | Redundant `"HB"` in the `light` tuple (`far` already forces the same meshes) — leave it, but it is not what makes the belt far. | note | no |

Nothing here is a blocker. Merge, rebuild master, then fix C before the export chain r2 is dispatched.
