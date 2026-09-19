# Phase 8d export chain — the backdrop after the master rebuild (brief from the lead, 2026-09-19). Opus 5 high. Fresh agent. Branch `phase8d-export` from main
(after phase8d-env and phase8e-export are merged and master_delivery.blend is rebuilt), worktree .claude/worktrees/phase8d-export. Owns export/ only.
Read: CLAUDE.md (Phase 6 machine rules), docs/decisions.md "8d decision", "8e built" and the 8a export gate entry (the pin rule), docs/reviews/phase8_env_r2_review.md
(the export places that must follow the lawn -> backdrop_lawn rename, quoted here so nothing is missed: gate1_set.py:587 derived names ENV_backdropgroup_backdrop_lawn /
EXPM_… / MAT_EXP_ENVBD__MAT_backdrop_lawn; gate2_set.py job_id = a NEW bake job ENVBD__backdrop_lawn, so purge the stale ENVBD__lawn entry from out/bake_queue/status.json
and its maps from out/gate2 before packing; export/budget_doc.py:288 hard-codes 99 640 / "never closer than the far shore" — now 106 540 and 150 m; manifests regenerate),
docs/reviews/phase8_export_r2_review.md (8e: the manifest refresh that rides with this chain), export/README.md "Phase 8a" (the chain as last run: gate1 in the worktree,
diff against MAIN, budget constant 902 000, sync_main, tiers, verify_glb --gate5, tiers_test), docs/briefs/phase8d_env_report.md (what changed: +6 900 backdrop tris on
MAT_backdrop_forest, the new MAT_backdrop_lawn on the far ground, seven reworked MAT_backdrop_* graphs; nothing else in ENV).
Steps, in order, each committed: (1) Gate 1 in the worktree: the PIN REPORT first — uv1 coverage/tiles/groups identical to MAIN, arch/orn/ground glbs byte-identical,
near 20 / far 127 impostor placements and instance rows byte-identical, ENV placed = MAIN + 6 900 (+ the four belt objects merged into backdrop_forest), the lawn group
renamed; if the pin does not hold, STOP and report (no re-bake is in scope). (2) Gate 2 albedo/rough/normal bake for the changed backdrop groups ONLY (building, skylight,
roof, roof_tile, forest, hill, asphalt, backdrop_lawn) through export/bake_queue.sh — GPU, 8-15 min; the queue owns the GPU; you check no Chrome is running before starting
it (`pgrep -fl headless`) and you never start Chrome. Report min/max/clipped per map as every bake round does. (3) manifests (v2 + v4), budget_doc (fix line 288), tiers.py
(desktop / mobile / no-pack) — this is where the 8e env_trees.glb byte counts refresh; tier-0 bytes may change ONLY by the backdrop groups' new textures/geometry — report
the tier-0 delta and the first-frame wire bytes (must stay <= 50 000 000); verify_glb --gate5; tiers_test.mjs; name sweep on the export set. (4) Diff the whole export/out
against MAIN before sync: list every changed file with its reason; then sync_main. Report < 15 lines: the pin report, the bake numbers, the tier-0 and first-frame deltas,
the list of changed files, the water.js reflection-set question for the viewer (the far-ground group now matches /MAT_EXP_ENVBD__MAT_backdrop_/ and drops out of the
reflection set at reflSet 'both' — state what the hero reflection loses), commit ids. Never deploy.
ADDED 2026-09-19 (8a-3, decisions.md "8a-3 decision"): the same chain applies the shrub-card UV scale from docs/briefs/phase8a3_shrub_cards_analysis.md — k = 2.0 on
MAT_shrub / MAT_shrub_light / MAT_shrub_dry LOD2 cards, k = 1.0 on MAT_reeds, LOD1 walk-in set unchanged, samplers REPEAT in BOTH env.gltf and env_shrubs.gltf (every root
agrees, so no viewer change); coverage is neutral by construction (measure and report it anyway, 0.95-1.09x expected); tier-0 delta ~4 kB is accepted and reported against
the 50 000 000 first-frame rule. This is a tier-0 change: the pin report must still show uv1/instance rows/impostor placements byte-identical (a UV0 scale on the shrub cards
touches none of them); env_t0.glb changes by the backdrop and the shrub UVs only — list its byte delta separately.
