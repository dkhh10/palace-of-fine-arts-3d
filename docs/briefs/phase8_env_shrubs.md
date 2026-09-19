# 8a ENV brief — shrub/reed card density (Opus high, Blender, fresh agent). Branch `phase8-env` (worktree .claude/worktrees/phase8-env, from main today).
Read first: CLAUDE.md (conventions, Blender hygiene, blender_run.sh, preview rules, image discipline), docs/decisions.md "PHASE 8 APPROVED" and the 6c entries
("Export r3", "Viewer r3", "6c CLOSED") for what the shrub band is and why it fails, docs/qa_round_17.md §3 (the shrub boxes at stations 1/2/3/5 with reference
values: level, hue, hard-edge share, leaf-green pixel share ~half the reference), scripts/env_build.py and scripts/env_lib.py (how the 28 shrub/reed LOD0/1/2 card
meshes and the 1 379 placements are built), scripts/env_preview.py and common.render_previews (Eevee previews from the QA cameras), docs/reference_sheet.md
(the shore planting: species, heights), reference photos under reference/photos (MAIN checkout path; the hero photo = ref 169; cam02 ref 062; the QA-17 crops).
Goal, measured: at the QA-17 shrub boxes (stations 1, 2, 3, 5) the LOD1 card set's leaf-green pixel share reaches the reference (currently ~0.5x) with the
hard-edge share not rising above the reference (1.77 at the hero) and the level/hue unchanged (they are at the reference already). The fix is STRUCTURE: more,
smaller, more varied cards per cluster (leaf clumps at several scales, oriented with variation, not broad flat blades), LOD1 only (LOD0 may follow the same
generator at a higher count; LOD2 unchanged — it is the mobile/far set), same object names, same 1 379 placements and the same four materials (MAT_shrub_light,
MAT_shrub, MAT_shrub_dry, MAT_reeds — no material edits: the look is frozen). Keep each LOD1 card mesh under a triangle budget you state (the current 28 meshes'
totals are in docs/briefs/phase6_budget.md; the whole LOD1 shrub set must stay under 2x its current unique triangles).
Deliverables: (1) the generator change in scripts/env_*.py (idempotent, rebuilds the ENV shrub collection only); (2) assets/environment.blend rebuilt by script;
(3) Eevee previews at cam01/02/03/05 (common.render_previews('env'), 1280x720, low samples, blender_run.sh 600 s each, ONE Blender at a time, `pgrep -fl MacOS/Blender`
first) and a comparison sheet before/after/reference for the shrub boxes at 960 px (renders/qa_comparisons/p8a_shrubs_*.jpg) with the leaf-green share and
hard-edge share numbers measured by a script (scripts/env_p8_boxes.py; the QA-17 box definitions are in scripts/qa_r17_probe.py); (4) a docs/briefs/phase8a_env_report.md
under 25 lines: numbers before/after per box, triangle counts, files, commit id. Commit after every script; no edits outside scripts/env_*.py, assets/environment.blend
and the report; do not touch master.blend (the lead rebuilds it) or export/. Report to the lead when the blend is committed.
