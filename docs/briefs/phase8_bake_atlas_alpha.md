# 8b bake brief, ANALYSIS FIRST — far-tree impostor atlas alpha at the crown tops (Opus xhigh, fresh agent). Branch `phase8-bake` (worktree .claude/worktrees/phase8-bake, from main).
Read first: CLAUDE.md Phase 6 (bake queue owns the GPU; `export/out/bake_queue/status.json`; one Blender per job through blender_run.sh), docs/decisions.md
"PHASE 8 APPROVED" and "PHASE 7 DONE WITH RESIDUALS" (item 1), docs/qa_round_17.md §7 item 4 and docs/qa_round_19.md (the far-tree cards read as pale opaque
masses where Cycles shows sky through the twigs), export/README.md sections `impostors`, "Phase 6c (bake engineer's notes)" (how the 16 prototypes' octahedral
atlases — 12x12 frames, 85 px at 1K / 170 px at 2K — are rendered and composed: export/trees_far.py, trees_far_compose.py, gate3_env_cards.py, imp_diag_*.py),
web/src/impostors.js (how the viewer samples alpha: the Phase 7 premultiplied 12-tap + alpha-to-coverage; `?impedge=`).
Phase 1 (this brief, NO GPU, no Blender renders): establish WHERE the opacity comes from, with numbers: (a) read the composed atlas alpha for three prototypes
(a broadleaf, a cypress, a pine) from export/out/gate3 (the EXR/PNG sources, not the KTX2): the alpha histogram at the crown top vs the trunk band, the share of
semi-transparent texels (0 < a < 1), and whether the compose step thresholds or dilates alpha (grep the compose for threshold/dilate/erode/premultiply); (b) render
NOTHING — instead compare the Cycles reference crown at station 2 (renders/previews/qa/round13_02_*_cycles.png) with the atlas frame nearest that view, at
100 %, and state whether the difference is atlas resolution (85/170 px per frame vs the crown's screen size), alpha thresholding in the bake/compose, the
viewer's alpha ramp, or the bake's own leaf density; (c) cost the options: a 4K atlas (memory x4, tier), a higher-res frame for the hero-facing views only,
alpha kept unthresholded with coverage from the bake's sample count, or a per-frame "alpha at the crown top" fix in the compose. Write
docs/briefs/phase8b_bake_analysis.md (< 40 lines) with the measured numbers, the diagnosed cause, the recommended fix, its GPU time (bake queue wall
time per prototype from status.json history), its memory and tier cost, and STOP for the lead's decision. Commit the analysis and any read-only probe script
(export/p8_atlas_probe.py). No edits to the export chain yet.
