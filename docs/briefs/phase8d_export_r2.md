# Phase 8d export chain r2 — the real-crown belt (brief from the lead, 2026-09-19). Opus 5 high. Branch `phase8d-export` from main (after the belt r2 merge and the
master / master_delivery rebuild), worktree .claude/worktrees/phase8d-export. Owns export/ only. Blender/GPU yours; no Chrome until you report.
Read: docs/briefs/phase8d_export.md (the r1 chain as run, the rename fan-out, the traps), export/README.md "Phase 8d" (r1 numbers: ENV placed 901 874, far 127, near 20,
tier 0 48 270 284, first frame 49 395 053), docs/decisions.md "QA 22" and "8a-4" entries, docs/briefs/phase8d_belt_r2_report.md (the ENV builder's report: N new far trees,
their names / prototypes / positions JSON, the placed-tri delta per LOD, the removed icosphere belt), docs/reviews/phase8_export_r4_review.md carries 5-10.
What changes on purpose this time: the far-tree set grows from 127 to 127 + N (the belt trees are ordinary ENV_tree_* far placements on prototypes that already have
band + octahedral atlases); the instance rows and order change accordingly; the backdrop_forest group loses the 6 900 icosphere tris; CLASS_BUDGET['ENV'] moves by exactly
the placed delta the ENV report states (log the arithmetic). What must NOT change: uv1 groups/tiles/coverage, uv2 meshes, lightmap slots, arch/orn/ground glbs (byte-identical),
the near-tree list (20, same order), every existing far tree's row content (only appended rows plus whatever re-sort the exporter applies deterministically — say which),
the impostor atlases (no bake: every new tree resolves through prototype_map to a baked prototype; if any does not, STOP and report), tier-0 first frame <= 50 000 000.
Steps: (1) Gate 1 in the worktree with the pin script extended: the r1 21/22 checks plus "far = 127 + N, the first 127 rows byte-identical or a documented deterministic
re-sort", "prototype_map resolves N/N", "ENV placed = 901 874 - 6 900 + delta"; (2) NO Gate 2 bake unless a backdrop group's UV set changed (report why if it did); Gate 3:
instance rows / order re-dump, the far-tree LOD2 block (env_trees.glb) re-run so the new trees have their LOD2 meshes for mobile (vertex_ao.npz keys for the new trees: the
bake side of vertex AO — if that needs a Cycles run, price it and ask; otherwise the new trees may ship with a stated stand-in AO and the report says so); (3) manifests,
budget_doc, tiers x3, verify_glb --gate5 both variants, tiers_test, name sweep; (4) full diff vs MAIN with reasons, sync. Report < 15 lines: the pin report with the moved
numbers, far count, prototype resolution, ENV placed and the budget constant, tier-0 / first-frame deltas, the vertex-AO decision, changed files, commit ids. Never deploy.
