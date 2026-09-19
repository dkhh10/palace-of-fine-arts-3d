# Code review — `phase8d-export2` export chain r2 (head 763f61c, 4 commits on 71e7cef)

Reviewer: Claude Opus 5, read-only, no Blender, no Chrome. Judged from the diff, the committed logs, the
regenerated artefacts under `export/out/` (MAIN and the worktree — byte-identical, the branch synced), and
`npm test` re-run here. Files read: `export/p8d_pin.py`, `export/manifest_v4.py`, `export/trees_far.py`,
`export/budget_doc.py`, `export/README.md` "Phase 8d r2", `export/verify_glb.py`, `export/gltf_pack.sh`,
`web/src/foliageLazy.js`, the briefs and the r3/r4 reviews.

## Verdict: **MERGE WITH FIXES — DO NOT DEPLOY until finding 1 is closed**

The branch's *code* is good and most of it is better than the brief asked for: the interleave invariant is
stated correctly and checked three independent ways, the prototype-map extension asserts instead of assuming,
the vertex-AO question turns out to need nothing, and both far sets were rebuilt and cross-checked row for
row. Twenty-five pin checks pass and I could not break any of them by construction.

But the chain was run **in the wrong order for the one pair the branch's own README warns about**, and the
result is a shipped manifest that describes 127 far-tree placements for a glb that now carries 166. The
viewer's own join code turns that into a silent removal of the entire far-tree mesh layer. That is a deploy
blocker, and closing it needs a GPU step this chain did not run or price (finding 2).

---

## 1. BLOCKER — `trees.far_mesh` / `trees.walkup_mesh` are stale at 127 against a 166-instance glb

`export/out/gate3/manifest.json` was written at **22:12:26**; `env_trees.glb` at **22:13:51** and
`env_trees_lod1.glb` at **22:14:13**. `manifest_v4.py` therefore read the *previous* `trees_far.json` and
baked the pre-belt numbers into the manifest that `tiers.py` then copied into
`out/gate5/manifest.json` and `manifest_mobile.json`:

| field | in the manifest | on disk / in `tree_far` |
|---|---|---|
| `trees.far_mesh.placements` | **127** rows (last = index 126, willow_s37) | 166 |
| `trees.far_mesh.bytes` | 3 768 500 | **3 769 736** |
| `trees.far_mesh.placed_tris` | 1 007 775 | 166-row value |
| `trees.walkup_mesh.bytes` | 7 642 344 | **7 643 580** |
| `trees.walkup_mesh.placements.count` | 127 (`verified_pre_pack.rows` 127) | 166 (the fresh report says 166, delta 0.0 m) |
| `trees.far_mesh.lighting.mesh.placements` | 127 | — |
| `tree_far` (same file) | **166** | 166 |

The manifest's own `impostor_join` contract — "placements[i].billboard is tree_far[i].billboard" — is broken
by this on every row.

**What it does in the viewer.** `web/src/foliageLazy.js:414-460` joins each `EXT_mesh_gpu_instancing`
translation to `trees.far_mesh.placements[].loc`. Every tree is bark + leaf, so 166 placements give 332 rows
against a 127-entry table: 78 rows match nothing within `JOIN_TOL_M`, `out.unjoined` is non-zero, and the code
does exactly what it says it does —

> `far-tree meshes: JOIN FAILED — …; the meshes are not drawn and every far tree stays its impostor`
> `scene.remove( root )`

and the walk-up set falls back to `far_mesh`, which fails the same way. **All 166 far trees lose their real
mesh**, including the 36-40 m broadleaves the whole 6c item-A / walk-up work exists for. Nothing in the chain
caught it: `verify_glb` checks `env_trees.glb` against the *builder's* fresh `trees_far.json` (166) and against
`env_trees.gltf`, never against the manifest, so `--gate5` legitimately reported `fail: []`.

**Fix:** re-run `manifest_v2 → manifest_v4 → budget_doc`, then `sync_main.sh`, `tiers ×3`,
`verify_glb --gate5`, `tiers_test`, `name_sweep`, sync — **after** finding 2, because manifest_v4 will not
complete until then.

## 2. BLOCKER — the far-tree per-placement irradiance cannot be regenerated as it stands

`export/manifest_v4.py:69-81` (`trees_lighting_block`) joins `out/gate3/trees_far/instance_irradiance.json`
to `trees_far.json` **by `pl["object"]`** (the `TREEFAR_###` id) and then asserts the two `loc`s agree within
0.02 m. That file was baked **2026-09-17** and has **127** rows. The interleave starts at index 40, so:

* rows `TREEFAR_040…126` now name *different trees* than the bake does (I measured: **87 of the 127 existing
  far trees changed their billboard / `TREEFAR_###` id**), and
* `TREEFAR_127…165` have no row at all.

Re-running `manifest_v4` will therefore hard-fail on `missing` and on `worst < 0.02`. It fails safe — nothing
wrong ships silently — but it means the manifest cannot simply be regenerated. Required before finding 1 can
be closed:

* re-key the existing 127 by **world location** rather than by object name (CPU, exact — the locations did not
  move, only their labels), and
* produce rows for the 39 belt placements: either the Gate-4 instance-irradiance bake for those placements
  (GPU — price it), or a documented stand-in (nearest-neighbour / per-prototype mean) recorded in the manifest
  and in `docs/decisions.md`, the same way the r2 chain handled the vertex-AO question.

Note that `export/trees_far_compose.py:183` (`len(got) == len(order) == 127`) and
`export/trees_far_set.py:214` (`len(placed) == 127`) are still hard-coded at 127, so the re-bake path will
stop there first. They fail loudly, which is right, but they now need the same treatment `trees_far.py` got.

## 3. `manifest_v4` has no guard tying `far_mesh.placements` to `tree_far` — add it

The one-line assert that would have caught finding 1, at `export/manifest_v4.py:907` right after
`tf = json.loads(tf_p.read_text())`:

```python
assert len(tf["placements"]) == len(man["tree_far"]), (
    f"trees_far.json has {len(tf['placements'])} placements and the export set {len(man['tree_far'])} "
    f"far trees - re-run trees_far.py (both sets) BEFORE manifest_v4")
```

and, because the manifest states it as a contract, the billboard identity:
`assert all(pl["billboard"] == man["tree_far"][i]["billboard"] for i, pl in enumerate(tf["placements"]))`.
The same applies to `tf_glb.stat().st_size` — a glb older than the report should be a failure, not a number.
`verify_glb.py` should gain the mirror check (manifest `far_mesh.placements` count vs the glb's instance rows
vs `tree_rule.far_billboards`); today all three are checked pairwise except the pair that broke.

## 4. The pin's 25 checks — the interleave invariant is right, and jointly non-bypassable ✔

`p8d_pin.py:63-75` replaces "the first 127 rows are byte-identical" with three checks, and they hold together
better than any one of them does alone:

* `fa` (MAIN's 127) vs `old_rows` (the new list minus the belt names), **with `billboard` stripped from both
  sides and compared as ordered lists** — this is exactly "the same rows, same content, same relative order",
  and the one field that legitimately shifts is the one excluded. Correct.
* `len(new_rows) == len(belt_names)` and `sorted(new names) == sorted(belt names)`.
* The count `39` is never asserted against a literal — but a truncated belt JSON cannot slip through, because
  the missing belt names would then fall into `old_rows` and break the first check (127 ≠ 161). Good.
* The `key` lambda falls back to `billboard` if `source_tree` is absent; that would make `new_rows` empty and
  fail loudly rather than pass. Rows do carry `source_tree` (verified).

The near list is compared **in order** (`p8d_pin.py:105`, plain `==` on two lists) and is unchanged at 20 with
`near_tris_used` 391 908 and `within_radius` 77 — the `_LOD2` exclusion precedes the radius test, exactly as
the r3 review predicted. ARCH 949 382 / ORN 1 099 192 identical; arch/orn/ground glbs byte-identical.
`EXPECT_ENV_DELTA -6 822` reconciles: 901 874 − 6 900 + 78 = 895 052, and `budget_doc` agrees (ENV 895 052 /
902 000, headroom 6 948). 25/25 ok.

**4a (low).** `far_interleave.billboard_reindexed` is **0 by construction** and therefore meaningless: it
compares `fa[i]["billboard"]` with `fb[i]["billboard"]` at the same *fb* index, and billboards are numbered
positionally, so the two are always equal. The true answer is **87** (`old_rows[j].billboard !=
ENV_treeboard_%03d % j`). Since that number is what finding 2 turns on, the diagnostic should be fixed rather
than deleted. `first_new_index: 40` is correct.

**4b (low).** The pin is now **not re-runnable**: `sync_main.sh` overwrote MAIN's `export_set.json` with the
new one, so a second run compares the set against itself and fails `EXPECT_ENV_DELTA`. Fine for this round,
worth a line in the README so the next reader does not think the pin regressed.

**4c (low).** `p8d_pin.py`'s module docstring (lines 9-12) still says "far billboards 127 … the near and far
LISTS identical in content AND order" and "ENV placed = MAIN + 6 900". The constants and the code below now
say the opposite. Update the docstring.

## 5. `prototype_map_added` — correct, asserted, recorded ✔

`manifest_v4.py:581-598` extends `impostor_prototype_map` with `gate3_set.py`'s own `_LOD2 → _LOD1` rule and
**asserts the target is in the already-baked `protos`**. Measured in the shipped manifests
(gate3, gate5 desktop, gate5 mobile): map keys 25 → **28**, `prototype_map_added` = **3** — precisely the three
the r3 review named (`cypress_column_s2`, `cypress_column_s31`, `pine_s29`, at `_LOD2`); the other 9 belt
prototypes already had keys. `prototypes` stays **16**, so `sorted(set(...))` and every atlas tile index are
unchanged and no atlas or impostor blend is re-baked. **All 166 rows resolve, 0 outside the baked set.**
The atlas join is by prototype string, not by row index, so the interleave cannot touch it. Verified.

## 6. Vertex AO — nothing was needed, and the r3 review's risk 4 was a false alarm ✔

The far block builds one LOD2 mesh **per impostor prototype**, and the prototype set did not move (16). The
belt added placements, not prototypes — the three "new" names are new to the `_LOD2` *key space* of
`prototype_map`, not to the mesh set. `8d2_trees_far.log` reports `prototypes=16`, `color0:far meshes=16`;
`trees_far.json` carries `color0.source = out/gate3/trees_far/vertex_ao.npz`, `topology_rev 2`, 16 meshes,
`color0_meshes` 16, `gltf_fixup.promoted_to_color0` 32, no `color0_refused`. No stand-in AO, none needed.
The topology-revision gate and the `len(COLOR_0) == len(protos_out)` assert are both intact.

**6a (low) — `trees_far.py`'s `== 127` replacement is circular.** `assert len(placements) == len(far)` where
`far = man["tree_far"]` and `placements` is built by iterating `far` is very nearly a tautology: it catches a
skip inside the loop, nothing else. A stale manifest at 127 would be accepted silently — which is a near miss
here, since the manifest *was* the stale artefact. Cheap real pin: cross-check the upstream source, e.g.
`assert len(far) == json.loads((g1.OUT/"export_set.json").read_text())["tree_rule"]["far_billboards"]`.

## 7. Both far sets, 166 / 332, order matching ✔

`env_trees.glb` and `env_trees_lod1.glb` were rebuilt in the same session (22:13 / 22:14), both report
`placements=166` and `nodes=166`. The walk-up set's `instance_order_check` against `env_trees.gltf`:
**166 rows, worst translation delta 0.0 m**. The far set's post-export `gltf_translation_check`: 166 rows,
worst residual 2.9e-05 m, worst scale residual 5.1e-07. 332 rows across the two sets as the brief asked.
`manifest_v4`'s `len(tw["placements"]) == len(tf["placements"])` assert held — on the stale pair, which is why
it did not catch finding 1.

**7a (low).** `p8d_pin.json`'s `glbs` block reports `env_trees.glb` and `env_trees_lod1.glb` as
`identical: true` at 3 768 500 / 7 642 344. It was captured at **22:10:28**, before both were rebuilt, and
`--glbs` was never re-run; the shipped files are 3 769 736 / 7 643 580. The arch/orn/ground byte-identity
(the part that is actually pinned) is genuine — that ran before the sync. The two tree rows are simply stale
and now unrecoverable, because MAIN's baseline has been overwritten. Note it in the JSON or re-run `--glbs`
last in the chain.

## 8. Gate 2 — one group, correctly scoped ✔

Only `ENVBD__backdrop_forest` ran (`bake_queue` job list ends with it; every other Gate 2 job logs
`skip … already done`), and `out/gate2/tex` contains exactly **three** PNGs — forest albedo / normal /
roughness. The README's claim that `backdrop_uv1.npz` shows the forest as the only changed UV set
(318 180 → 297 480 loops) is consistent with the group losing the four icospheres, and `gate2_set.log` shows
`backdrop_forest 6 objects, 98 920 polys`. The r4 fix held: `gltf_pack.sh --gate2` no longer `rm -rf`s the
directory — `kept 186 existing map(s), replacing 17` and 186 + 17 = the 203 the r4 review recorded. Of the 17
re-encoded, 3 are the forest and 14 are the unchanged shared `detail_*` set, which is why the count looks
larger than the re-bake. `manifest_v3`: 62/62 material sets `uv1_in_glb`, backdrop UV cross-check 10/10,
0 jobs missing, no clipping reported.

## 9. Tier-0 trim and the first frame — acceptable, documented, reconciles ✔

The trim is a **ranked automatic solver**, not a hand pick: `tiers.tier0_trim` records `reason` (tier 0 on the
wire was 51 142 667 B against the 49 500 000 target), 32 moved keys with their `hero_order`, `moved_bytes`
1 866 524, and `effect` ("each covers less than 0.003 % of the hero frame; the glb's own base colour stands in
until tier 1"). The marginal drop the README names —
`gate2_ORN__ORN_capital_inner_v1_LOD0_a_normal`, hero order **-0.00019**, 131 281 B — is the last entry, its
albedo sibling at the same rank was already out, and the full-resolution file is in tier 1. Acceptable, and it
is documented in the artefact itself, not only in prose.

Arithmetic reconciles against MAIN's manifests: tier 0 transfer 48 111 210 + boot 1 123 454 + headers 36 288 =
**49 270 952**, i.e. `first_frame_on_wire_bytes`, **729 048 B under the 50 000 000 rule**; `tiers.bytes[0]`
48 139 115 matches `verify_gate5_desktop.json`. (The `reason` string quotes the pre-measure boot/header figures
1 123 461 / 41 472 — a cosmetic inconsistency with the final 1 123 454 / 36 288, not an error.)
`verify_gate5_desktop.json` and `_mobile.json`: `fail: []`, 2579/2579 assets covered. `npm test` re-run here:
**three r186, all passed** — no test is pinned to a `TREEFAR_###` index.

## 10. Chain-order correction and the doc carries (low)

The r2 section states the correct order (**v2 → v3 → v4**) and explains why the r1 listing worked by accident.
But the r1 runbook block itself (`export/README.md:2607` / `:2616`) is **left uncorrected** — still
`manifest_v3.py` first, and still carrying the pre-r4 comment "`rm -rf`s tex_ktx2: restore MAIN's other maps
after". Someone will copy that block. Correct it in place or mark it superseded. The same section should also
record the far-tree sets and `manifest_v4` in the order finding 1 requires.

Stale index / count references the interleave invalidated, none of them shipped code paths:

* `export/p8e_leaf_probe.py:133-135` — `TREEFAR_116` / `_117` were willows, they are now `ENV_tree_pine_15/16`
  (the willows moved to 155/156). `TREEFAR_000` / `_001` are still the broadleaves, so
  `export/trees_far_ratio_check.py:45 PLACEMENT = "TREEFAR_000"` is still valid.
* `export/manifest_v4.py:644` ships "46 of the 127 far trees were exported against an LOD2 blob" **inside the
  manifest** — it is 85 of 166 now. Same for `:513-514` (the occluder note) and `web/src/impostors.js:705`.
* `export/name_sweep.py`'s exemption regex `ENV_treeboard_\d+` is count-agnostic and needs no change; the
  README's r1 "127 exempt treeboards" line is superseded by the r2 run.

## 11. `CLASS_BUDGET["ENV"]` (low)

Left at 902 000 — the right call (the move is −78 against the pin baseline and the near list is untouched),
and the budget doc shows the result (895 052 / 902 000, 6 948 free). But the r3 review asked the chain to
**say which of the two options it took**, and the r2 README section states the placed arithmetic without
stating the constant decision. One sentence.

---

## Fix list

| # | Fix | Severity | Blocks merge | Blocks deploy |
|---|-----|----------|--------------|---------------|
| 1 | `trees.far_mesh` / `walkup_mesh` stale at 127 vs a 166-instance glb; the viewer drops the whole far-tree mesh layer. Re-run v2 → v4 → budget_doc → sync → tiers ×3 → verify --gate5 → tiers_test → name_sweep. | **blocker** | no | **YES** |
| 2 | `instance_irradiance.json` is 127 rows keyed by `TREEFAR_###`; 87 ids were re-pointed and 39 are absent. Re-key by world location and produce the 39 belt rows (bake, or a documented stand-in) before fix 1 can complete. | **blocker** | no | **YES** |
| 3 | `manifest_v4`: assert `len(tf["placements"]) == len(man["tree_far"])` (and the billboard identity); mirror it in `verify_glb`. | high | no | no |
| 4 | `trees_far_compose.py:183` and `trees_far_set.py:214` still hard-code 127 — they will stop the fix-2 re-bake. | medium | no | no |
| 5 | `far_interleave.billboard_reindexed` is 0 by construction; the true figure is 87. | low | no | no |
| 6 | `trees_far.py`'s `len(placements) == len(far)` is circular — pin `far` against `export_set.json`'s `tree_rule.far_billboards`. | low | no | no |
| 7 | `p8d_pin.json`'s `glbs` rows for the two tree glbs are stale (captured before the rebuild); the pin is no longer re-runnable after the sync. Note both. | low | no | no |
| 8 | `p8d_pin.py` docstring lines 9-12 still describe the r1 invariants. | low | no | no |
| 9 | README r1 runbook block (`:2607`, `:2616`) still lists v3 before v2 and the pre-r4 `rm -rf` comment; `p8e_leaf_probe` indices, `manifest_v4:644`/`:513`, `impostors.js:705` "127/46" notes. | low | no | no |
| 10 | State the `CLASS_BUDGET["ENV"]` decision (left at 902 000) in the r2 section. | low | no | no |

Merge the branch — the code is sound and fixes 3-10 are cheap follow-ups. **Do not deploy** until 1 and 2 are
closed and the six-station tile review has been re-taken against a viewer whose far-tree meshes actually draw.
