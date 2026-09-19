# Phase 8d belt r2 — real crowns behind the north colonnade (brief from the lead, 2026-09-19). Opus 5 high. Fresh agent. Branch `phase8d-env` (merge main first),
worktree .claude/worktrees/phase8d-env. Owns assets/environment.blend, scripts/env_backdrop.py, scripts/env_trees.py (belt placement only), scripts/env_build.py if the
belt needs a hook. Blender is yours (no Chrome runs until you report); scripts/blender_run.sh with honest seconds; one Blender at a time.
Read: CLAUDE.md, docs/decisions.md "QA 22" entry (the decision), docs/qa_round_22.md §8d (the tiles: what failed and where), docs/briefs/phase8d_env_report.md (the belt as
built: ENV_backdrop_hall_belt_0..3, 89 crowns, 2.8 m row, 5.4/9.2 m off the hall face, tops capped 15.7 m), docs/briefs/phase8d_analysis.md §4 (tree options and the pin),
scripts/env_trees.py (FAR_RADIUS 130, the "E2/E3 back screen rows" that place far trees with LOD2 meshes, the species library and the prototype names the impostor bake
used — see export/README.md "Far trees: the Gate 3 octahedral impostors" and docs/briefs/phase8b_band_atlas.md for the 16 baked prototypes), ref 169 at 100 % (MAIN
reference/, the hero reference: the dark belt's height, density, species read — cypress/eucalyptus/pine silhouettes, not blobs).
Build: (1) remove the four ENV_backdrop_hall_belt_* icosphere objects (and their planter code path, or leave it behind a flag defaulting off); (2) place a belt of real far
trees along the hall's east face through the far-tree mechanism so each tree is a normal ENV_tree_* far placement (LOD1 object carrying the LOD2 mesh at this distance,
exactly like the existing far rows) using ONLY prototypes that already have a baked impostor (the 16), species mixed as the reference reads, heights 12-19 m, tops below
the hall roof crest by a stated margin, undersides grounded, spacing so the belt is continuous from the hero and cam05 but not a wall of identical silhouettes (rotate,
scale within the prototype's baked range, mirror where the bake allows); N as small as closes the intercolumniations from the hero station (expect 25-45); (3) count the placed
tris per LOD and report the delta against the current ENV placed 901 874 — the export moves its budget constant by exactly that delta; (4) previews at cam01, cam02, cam05
(600 s each, common.render_previews) and a 960 px composite: gate10-style crop of the N band vs ref 169; the belt must read as tree crowns with sky-gapped silhouettes at
100 %, not shards, not a hedge; (5) the far-tree count the viewer will see: list the new trees' names, prototype, position, scale in a JSON the export can diff.
Do NOT rebuild master, do NOT touch export/. Commit after every successful script with the attribution line. Report < 10 lines: N, species mix, placed-tri delta per LOD,
the composite path, the JSON path, commit id.
