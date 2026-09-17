# 6c export brief, round 2 (Opus high, fresh agent, 2026-09-17). Branch phase6-export (worktree .claude/worktrees/phase6-export; `git merge main` first).
Read: docs/briefs/phase6c_export.md and docs/briefs/phase6c_foliage.md (items D, E); CLAUDE.md "Phase 6" and machine rules; docs/decisions.md from
"2026-09-17 · Impostor blue cast" to the end (the three lead decisions in "6c export findings" are your scope); export/README.md section "Phase 6c" (items 34+, your
predecessor's state); export/foliage_tex.py, export/read_foliage.py, export/shrub_lod1.py, export/trees_far.py, export/manifest_v4.py (the `materials.foliage`, `shrubs.lod1`
and `trees.far_mesh` writers), export/gltf_pack.sh --trees, export/verify_glb.py.
1. TINTED albedo: bake the albedo per shrub/reed material AFTER the Phase 5 tint (MAT_shrub 95/0.46, MAT_shrub_light 94/0.52, MAT_shrub_dry 36/0.60 straw, MAT_reeds 0.65 —
   the node tree's own tint, not a viewer-side constant), replacing the raw 1K card PNG in the KTX2 set; keep the translucency factor map; report mean hue/value per material
   before and after, and against the Cycles cam02 foliage hue (102.4°). Export fidelity only: no Phase 5 material edit.
2. Drop the 2K upsample (`leaf_2k`) from foliage_tex.py's outputs and from manifest_v4.py's `materials.foliage` block (decision 2: no 2K source exists; 1K ships).
3. COLOR_0 attach for the far trees: when export/out/gate3/trees_far/vertex_ao.npz exists in MAIN and MAIN's export/out/bake_queue/status.json says idle (the bake engineer
   is producing it this session; poll the two files with ONE `until` shell loop sleeping 120 s, max 3 h — never poll in turns), run
   `scripts/blender_run.sh 900 -- --background master_delivery.blend --python export/trees_far.py && export/gltf_pack.sh --trees`, then verify_glb on env_trees.glb
   (127 rows, COLOR_0 present, encode range recorded), then sync_main.sh. Do items 1-2 first while the bake runs.
GPU: the bake engineer owns it while status.json says running. Any Cycles bake you need for item 1 runs on the CPU device (1K card materials; set the device explicitly
and say so in the report). Blender only through blender_run.sh with honest seconds; never save master*.blend; commit after every script; do not edit manifest.json by hand
(the lead re-runs manifest_v4). Report < 20 lines: hue/value numbers per material, bytes per KTX2, the COLOR_0 range, verify_glb lines, files, commit id.
