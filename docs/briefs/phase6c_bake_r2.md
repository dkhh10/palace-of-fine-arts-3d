# 6c bake brief, round 2 (Opus xhigh, fresh agent, 2026-09-17). Branch phase6-bake (worktree .claude/worktrees/phase6-bake; `git merge main` first,
then `git cherry-pick 5512dba` = the export branch's sync_main.sh guard that stops the sync overwriting MAIN's bake_queue/status.json, the GPU lock).
Scope: ITEM 2 of docs/briefs/phase6c_bake.md, exactly as written there, plus the 16 E_bake values. Read: that brief; docs/briefs/phase6c_foliage.md item B;
CLAUDE.md "Phase 6" and machine rules; docs/decisions.md from "2026-09-17 · Impostor blue cast" to the end; export/README.md on your branch, section
"`trees.far_mesh.lighting` — new at 6c" (your predecessor's spec, ~line 1068: the npz contract, the JSON schema, E_bake, the GPU path); export/bake_lm.py kinds
`vertex` and `instance`; docs/briefs/phase6_gate3_bake.md items 1-2; the export's hand-off note in the export worktree (read-only, do not edit):
.claude/worktrees/phase6-export/export/README.md section "Phase 6c" item 34 (why the LOD2 topology is a fresh reduction; vertex counts in topology.json).
Inputs in MAIN export/out/gate3/trees_far/: topology.json, trees_far_lod2.blend (16 prototype objects in prototype world space). Assert vertex counts against topology.json.
Deliverables (all in export/out/gate3/trees_far/, synced to MAIN with sync_main.sh AFTER the queue is idle): vertex_ao.npz (float32 per vertex, key = the LOD2 mesh name,
lights off, uniform white world, shadow-ray override, VERTEX_COLORS, 64 spp); instance_irradiance.json (127 placements, existing `instance` kind, join by location, same schema
as the shrubs, plus prototypes["<prototype>"].E_bake = [r,g,b] = the irradiance the isolated gate3_imp.blend nursery supplied each prototype, measured the same way as
E_placement so the ratio is unit-free). All jobs through bake_queue.sh --gate3 (status.json in MAIN says running while you own the GPU; idle when done) with honest
blender_run.sh seconds; many short jobs; never save master*.blend; commit after every script. Report < 20 lines: jobs and seconds, AO range per prototype (min/mean/max),
irradiance range and count of zero placements, E_bake per prototype, files, commit id, and confirm MAIN's status.json says idle at the end.
