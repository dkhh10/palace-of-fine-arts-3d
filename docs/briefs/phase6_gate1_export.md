# Phase 6 Gate 1 — export engineer (lead, 2026-09-15). Branch `phase6-export`, worktree .claude/worktrees/phase6-export. Opus high.
Read first: CLAUDE.md "Phase 6" section, docs/briefs/process.md, docs/briefs/phase6_plan.md (§1, §2, §4b, §5), docs/decisions.md (the two
2026-09-15 entries at the end), export/README.md (Gate 0 pipeline + carries), export/gate0_common.py / export_set.py (extend, do not fork).
Source: the MAIN checkout's master_delivery.blend (read-only, absolute path). Outputs to export/out/gate1/ (gitignored), synced to the main
checkout with export/sync_main.sh (no --delete). Every Blender run through scripts/blender_run.sh; GPU jobs only through your queue (below).

Goal: the frozen export SET at the budget, packed, loadable — no PBR and no lightmaps yet (Gates 2-3); neutral grey materials plus the ORN
normal + AO maps so the QA silhouette / normal check can run in the viewer at the six stations.
1. `export/export_set.py --gate1` (generalise Gate 0): select by name suffix (ARCH_/INST_ LOD0, ENV_ LOD1, unsuffixed ARCH_/ENV_; ORN_
   prototypes and PH_ never), un-hide + view_layer.update() before reading transforms, assert placements. Decimate to the plan §2 class
   budgets (ARCH 1.10 M, ORN 1.10 M, ENV 0.80 M placed, total <= 3.0 M) with the per-asset targets in §2; keep every shared mesh shared
   (columns, bases, astragals, the 33 ORN prototypes -> EXT_mesh_gpu_instancing). UV1 for the material bake on everything that gets a PBR
   bake at Gate 2 (ARCH grouped per element + material, ORN per prototype), UV2 for the Gate 3 lightmaps on ARCH/ENV ground, UV2 = the
   256 px atlas slot layout for ORN instances (option c: per-instance slot index in the manifest, two 4K atlases). Trees: the near list =
   every tree within 25 m of the walkable area (walkable = the paths/lawn objects; state the rule you used and the count) at LOD1 thinned
   50 %; the far list = tagged billboard quads (prototype id, height, trunk base) for the Gate 3 impostor bake; shrubs LOD2.
2. ORN normal + AO, hi (LOD0) -> lo, 2K per prototype, 1K for prototypes under 1 m (keystone, rosette, finial): a detached queue
   `export/bake_queue.sh` over a job manifest, one Blender per job through blender_run.sh (max 900 s), `export/out/bake_queue/status.json`
   ({state, current, done, total, started, updated}), resume skips done jobs, and the GPU rule: a job starts only when the watchdog state dir
   holds no live registered Blender pid other than the queue's (a materials builder renders concurrently this session; the queue waits, you
   do not — do CPU work meanwhile).
3. docs/briefs/phase6_budget.md: the per-asset table (asset, class, source tris, exported tris, placements, placed tris, UV sets, texture
   plan for Gates 2-3), class totals vs budget, draw-call estimate at cam01, texture-memory estimate. Actual numbers from the export.
4. Name sweep on the export set: `export/name_sweep.py` applying scripts/qa_name_sweep.py's pattern and exemptions to export_set.json
   (every exported object); 0 non-exempt hits or the list.
5. `export/gltf_pack.sh --gate1`: glb per class (arch.glb, orn.glb, env.glb, ground.glb) with `-cc -mi`, KTX2 for the normal/AO maps,
   manifest v2 (`pfa-phase6/2`, documented in export/README.md: assets, instancing groups, stations, water, sun, exposure, LUT, sky,
   compositor block, reference frames, orn slots, tree lists). Report bytes per glb and total.
6. Sizes and times per step, every failure, last commit id. Commit after every script. Report < 30 lines, no adjectives without a number.
