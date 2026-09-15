# QA round 11 — Phase 6 Gate 1: geometry freeze check in the viewer (brief from the lead, 2026-09-15). Model: Opus 5 xhigh. Read docs/briefs/qa.md, CLAUDE.md gate checks + the "Phase 6" section, docs/briefs/phase6_plan.md §2 §5, docs/briefs/phase6_budget.md, export/README.md, web/README.md.
What is under test: the exported geometry set (ARCH_/ORN_ LOD0 decimated, ENV_ LOD1 thinned near trees + far-tree billboards, neutral grey materials
with the ORN normal + AO maps, `direct` lighting mode, no PBR, no lightmaps) as the viewer shows it at the six stations. Materials and lighting are NOT
scored this round: only Silhouette, Proportion, Ornament fidelity (shape + normal-map relief), Repetition visibility and Scale cues, each station vs
the Phase 5 render of that station (parity: renders/previews/qa/round09_0K_*.png Eevee 1280x720; cam01 vs renders/final/v2/qa_round10b_cam01_cycles.png).
Inputs (already rendered by the lead through web/tools/gate1.sh; do NOT run Chrome or Blender unless a frame is missing, and then only through
scripts/chrome_run.sh with the GPU guard in a separate command): renders/web/gate1_cam01..06.png (1920x1080), renders/web/gate1_pair_cam0K.png,
the six 100 % tiles of cam01 under renders/web/gate1_tiles/, renders/web/gate1_perf.json, export/out/gate1/name_sweep.json (or .txt), export/out/gate1/export_set.json.
1. Name sweep: restate the export engineer's result (0 non-exempt hits or the list, with the exemptions on record in docs/quality_checklist.md).
2. Budget: per-class placed tris vs plan §2 (ARCH 1.10 M / ORN 1.10 M / ENV 0.80 M, total <= 3.0 M), draw calls and GPU cost per station at 1440p from
   gate1_perf.json vs the 45 fps target (state the median frame time and whether it is vsync-capped).
3. Full-resolution tiles of cam01 (3 x 2), each viewed: every geometry defect (decimation artefacts, cracked shells, missing instances, flipped normals,
   normal-map seams, billboards reading as slabs, filled openings) listed with tile, pixel box, owner (export / viewer). The main arch must show the far
   arch and sky through the opening (the Phase 5 ray test, by eye at 100 %).
4. Silhouette: align the viewer cam01 frame to the Phase 5 Cycles hero (scripts/qa_silhouette.py align, same as rounds 3-10; scale/dx/dy and the apex
   delta in % of frame height), and the stack band course rows; per station 02-06 the pair sheet at 100 % on two crops of your choice.
5. Score table (the five geometry rows only, 0-5) per station, with the Phase 5 round-9 score of the same rows beside it and the delta; verdict line:
   GATE 1 PASS / FAIL (FAIL names the blocking defect + owner + the one-line fix). Parity rule: every station within 0.5 of its Phase 5 rows.
Write docs/qa_round_11.md (< 200 lines), the composite renders/web/round11_gate.png (six pairs + the tile list), append to docs/quality_checklist.md.
Commit only those files + scripts/qa_*.py you add. Downscale before viewing except the tiles. Report < 30 lines.
