# Phase 8e — mobile: the LOD2 leaf-card scale at 37-45 m (brief from the lead, 2026-09-19). Opus 5 high. Fresh agent. Branch `phase8e-export` from main,
worktree .claude/worktrees/phase8e-export. Owner: export (export/trees_far.py, export/tiers.py, the env_trees.glb block); the viewer is not touched (the mobile
shaded-stone tint is item (c) of docs/briefs/phase8b_viewer_fix.md, not this brief).
Read: CLAUDE.md, docs/qa_round_19.md §4 finding (a) ("LOD2 leaf cards scale-implausible at 37 m: individual leaves ~40 px wide as gold/black duotone blades"),
docs/decisions.md "PHASE 7 APPROVED" (D) and the Phase 7 merge entry (mobile: farTreeMesh 45 m draws the LOD2 far-tree set from env_trees.glb with vertex AO; walkupMesh 0),
export/README.md "6c item A" (env_trees.glb, the LOD2 meshes, vertex_ao.npz) and the tiers section (which tier ships env_trees.glb; desktop does not load the LOD2 block),
scripts/env_trees.py `_lod2_cards` (4 crossed cards + a disc per crown; the leaf texture and its UV repeat), the MAT_leaf_* materials (frozen; the albedo textures may not change).
PART 0 — analysis (CPU, < 50 lines, docs/briefs/phase8e_analysis.md; NO Blender, NO Chrome): (1) measure the apparent leaf width in px at 37-45 m on the mobile close orbit
captures (renders/web/gate7_orbit_*.png, MAIN checkout, 100 %) and the same crowns in the Cycles/reference (what leaf size is plausible: Monterey cypress / eucalyptus /
pine leaves at that distance are sub-pixel to ~6 px); (2) find where the leaf scale is set — the UV repeat on the LOD2 card mesh, the card size, or the texture — and which
of these the export can change WITHOUT touching the blend (a UV scale on the LOD2 meshes in trees_far.py while writing env_trees.glb; the vertex_ao.npz keys must survive);
(3) cost: the LOD2 block size before/after, the tier it ships in, whether tier 0 changes (it must not), whether desktop is affected (it should not: desktop never loads the block).
Recommendation with the UV factor per species. Commit; report < 10 lines; wait for the lead's go.
PART 1 — after the go: apply in the export (Blender through scripts/blender_run.sh, honest max seconds, ONLY when `pgrep -fl "MacOS/Blender|headless"` is empty and
export/out/bake_queue/status.json is idle; never beside Chrome); write to the worktree's export/out first, diff against MAIN (env_trees.glb only may change; every other
file byte-identical; tier 0 byte-identical; instance rows/order unchanged), then sync to MAIN's export/out; tests green; export/README.md "Phase 8e" section; commit.
Report < 12 lines: the factor applied, block size before/after, the diff summary, commit id. The lead deploys and captures the mobile orbit for QA.
