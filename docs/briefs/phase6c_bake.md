# 6c bake brief (Opus xhigh, fresh agent). Branch phase6-bake (worktree .claude/worktrees/phase6-bake; `git merge main` first). Read docs/briefs/phase6c_foliage.md (items B and
the impostor diagnosis), CLAUDE.md "Phase 6" and machine rules, docs/briefs/phase6_gate3_bake.md items 1-2 (how the impostors and vertex irradiance were baked), export/README.md
manifest v4 `impostors` and `lightmaps.instance_irradiance` sections, export/bake_lm.py kinds `vertex` and `instance` (the shadow-ray override), docs/decisions.md from
"2026-09-17 · Shadow-ray bake measured" to the end.
1. Impostor diagnosis FIRST (short GPU): pick the prototype that stands nearest cam02 (find it from the manifest's tree_far placements and scripts/qa_cameras.py station 2),
   render it alone in Cycles at the final rig from one of its atlas views (same direction, same framing), and put that frame beside the atlas frame (one 960 px composite in
   renders/web/960/6c_impostor_diag.png, plus mean RGB / hue of the crown in both). Say whether the blue is in the atlas or in the viewer's shading. If the atlas is wrong,
   re-bake the 2K variant for all 16 prototypes with the final rig (sun on, diffuse-branch sky, translucency as Cycles), through bake_queue.sh, and report the per-prototype
   crown hue before/after. If the atlas is right, stop there and say what the viewer must change (report only; the viewer engineer owns it).
2. When docs/status.md says the export's far-tree LOD2 set is in MAIN (export/out/gate3/trees_far/*): per-prototype vertex AO (16 jobs, lights off, uniform white world,
   shadow-ray override, VERTEX_COLORS, 64 spp) on the export's LOD2 topology (assert vertex counts match the export's), written as float32 per vertex to
   export/out/gate3/trees_far/vertex_ao.npz; and per-placement RGB irradiance for the 127 placements with the existing `instance` kind (join by location, same JSON schema as the
   shrubs, file export/out/gate3/trees_far/instance_irradiance.json). README manifest v4 spec for both (block `trees.far_mesh.lighting`). Sync to MAIN, commit after every script,
   report < 20 lines: the diagnosis verdict with numbers, jobs and seconds, ranges, files, commit id. Never save master*.blend; blender_run.sh with honest seconds; many short jobs.
