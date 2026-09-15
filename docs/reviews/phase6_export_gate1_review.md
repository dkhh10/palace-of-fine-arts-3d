# MERGE WITH FIXES — `phase6-export` @ e88da10 (Gate 1 export), 11 findings (5 fix now, 6 carry, 0 blockers)

Reproduced from the committed logs/JSON, not the report: 844,554 / 1,099,194 / 792,822 = 2,736,570 placed; 140 meshes, 2,540
placements, 154 scene batches / 140 in frustum; orn 436 slots over 2 atlases, arch_inst 552 over 3; queue 33/33 rc=0 in 5,766 s;
UV1 worst overlap 0.0; `name_sweep.py` re-run → 0 hits. Passing: LOD by name suffix only after a blanket `hide_viewport=False`
(gate1_set.py:147-175), `ORN_`/`PH_`/`SOCKET_` never selected, `EXPHI_*` never in `assets`; placed tris = evaluated tris × placements
in both export_set.json and the budget-doc column; the frustum test reads `bpy.data.objects[g0.HERO_CAM]` after
`qa_cameras.ensure(scene)` (gate1_set.py:742, gltf_gate1.py:213), no hand copy; shared meshes stay shared, one decimate each (columns
50/48/16 placements, :286-299); one Blender per job via `blender_run.sh 900` + `--python-exit-code 1` + record check; nothing writes
master_delivery/master.blend; no `--delete`; no tracked binaries or files outside export/* + budget doc + README + 3 renders/logs;
`PFA_MAIN_ROOT` honoured throughout; all scripts idempotent.

1. **fix now** — `gltf_pack.sh:31-35`: only `*albedo*|*basecolor*` get `--assign_oetf srgb`, so the seven sRGB colour PNGs that exist
   (`uv1_probe_grey`, `leaves_broadleaf|eucalyptus|shrub`, `needles_cypress|pine`, `reeds`) are tagged **linear** and the viewer skips
   the sRGB decode — the Gate 1 grey (0.5 linear → 0.735 in the PNG) and all foliage albedo come back ~1.47× too bright, poisoning
   every parity number; `bark_*_diff_2k.jpg` also never reaches toktx (loop is `*.png(N)`). *Fix:* default `oetf=srgb`, linear only for
   the data maps (`*_normal|*_nrm|*_ao|*rough*|*disp*|*lightmap*`), glob `*.(png|jpg)`.
2. **fix now** — `bake_queue.sh:20,31-48`: `MAIN` is computed and never used, so status.json is written only inside the worktree and
   MAIN's copy advances only when `sync_main.sh:20` runs by hand — exactly the 12:59 staleness the lead saw. CLAUDE.md makes this the
   only GPU-liveness signal for other agents, so the MAIN sync is a **gap, not the design**. *Fix:* `cp -f "$STATUS"
   "$MAIN/export/out/bake_queue/status.json"` as the last line of `write_status`.
3. **fix now** — `gate1_set.py:690-695`: slots tile exactly (`uv2_scale = 256/4096`, offsets exact multiples) so adjacent slots share
   an edge with **no gutter**; the Gate 3 bake margin, bilinear filtering and every mip will pull the neighbouring instance. (Index is
   deterministic — `sorted(assets.items())`, per-pool counter — and the 2/3-atlas split is right.) *Fix:* `uv2_scale=(256-8)/4096`,
   offset `(col*256+4)/4096`, gutter recorded in `manifest.lightmap_encoding.slot_atlas`.
4. **fix now** — `gate1_set.py:784` vs `:819-840`: `voxel_remeshed` (the 3 attic panels) lands in export_set.json but **not in
   manifest.json**, the QA/viewer contract; `budget_doc.py:235` re-derives them from a `cage > 0.1 m` proxy instead of the flag.
   *Fix:* `man["voxel_remeshed"] = sorted(remeshed)` and `meshes[name]["remeshed"] = True`.
5. **fix now** — `budget_doc.py:189`: "~13 400 placed triangles" per near tree is hand-typed; measured is 391,908/20 = **19,595**, so
   "room for 19 more near trees" should read 13 in a doc that claims every number is measured. *Fix:*
   `per_tree = tr['near_tris_used'] // max(1, tr['near_exported'])`. (`foliage = 15 × 1K` at `:144` is likewise unmeasured.)
6. **carry** — `gate1_set.py:157-175`: an `ENV_*` object with a LOD suffix other than `ENV_tree*_LOD1`/`ENV_shrub*_LOD2` is dropped
   silently and `source_counts` shows only matched buckets. *Fix:* count unmatched meshes into `rep["skipped"]` and assert the list.
7. **carry** — `gate1_set.py:147-148`: `hide_render` is never read or logged, so a render-disabled `ARCH_`/`ENV_` object would ship.
8. **carry** — `gate1_set.py:483`: the near-tree allowance uses raw `tris_of(obs[0].data)` for shrubs while `:573` exports the
   evaluated mesh. *Fix:* estimate from `new_from_object(evaluated_get(dg))`.
9. **carry** — `bake_queue.sh:118-121`: no retry path at all, none for `rc=143` (watchdog SIGTERM at the 900 s cap); recovery is
   "re-run `start`, resume skips done jobs" — works, but undocumented and untested (33/33 rc=0). The `:14` header also claims resume
   checks the two maps; the code checks only `bake/<id>.json`. *Fix:* one retry on rc in (143,137); correct the comment.
10. **carry** — `gate1_set.py:468,490,573` leak `new_from_object` meshes (147 evaluated LOD1 trees just to count triangles) until
    `purge_orphans`, where `gate1_probe.py:104-106` uses `to_mesh()/to_mesh_clear()`; `gltf_pack.sh:49,53` appends to `gltfpack.log`
    forever (`: > "$OUT/gltfpack.log"` at the top of the `--gate1` block).
11. **carry** — tree rule vs headline: **77** real-LOD1 trees are within 25 m; 20 export and 57 join the impostor list on the ENV
    allowance (plus 46 `_LOD1` objects already carrying `_LOD2` blobs, excluded up front). Consistent with the user's "~20 reachable
    trees" and documented in `manifest.tree_rule` + the budget doc, but "near = 20 (within 25 m)" is not the radius rule's count —
    carry the 77 to the user, as with texture memory **1,343 MB vs 1,200** (a Gate 2/3 lever list, not a Gate 1 defect).
