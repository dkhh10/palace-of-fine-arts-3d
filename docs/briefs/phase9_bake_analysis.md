# Phase 9 bake analysis — price the lighting re-bake chain, decompose station 3's missing deep shade (brief from the lead, 2026-09-20). Opus 5 xhigh.
Fresh agent. Branch `phase9-bake`, worktree .claude/worktrees/phase9-bake (merge main first). CPU ONLY in this brief: no render, no bake, no Chrome. A
read-only Blender run (open master_delivery.blend or export/out/gate3/gate3_bake.blend, read data, quit; no render/bake) is allowed through
scripts/blender_run.sh <secs>, one at a time, while the lead's Cycles references render on the GPU. Read docs/briefs/process.md first.
Output: docs/briefs/phase9_bake_analysis_report.md, committed on your branch, then stop and report. No build in this brief.

## Part A — price the chain that follows a change to assets/lighting.blend
The lighting round (docs/briefs/phase9_light.md) changes the NNE shade fill and possibly the sky's diffuse sockets. Enumerate every web asset whose bake
depends on the lighting: own lightmaps (which ARCH assets are hit by the NNE lamp / the diffuse sky at all — the hero-visible rotunda and the north wing, or
every own map?), the ORN slot atlases (988 instances), the vertex-colour batches, the shrub instance irradiance (1 379 placements), the far-tree irradiance
(tfirr_00..03), the probe, the three sky equirects (camera / glossy / diffuse — which ones move if only the diffuse sockets change?), the impostor atlases (the
"neutral nursery" question: do they see the rig?) and their per-placement modulation E_bake, the shrub vertex AO, the LUT (unchanged unless the look moves).
Sources: export/README.md "Running Gate 3", "manifest.json v4", "Phase 6c", "QA 23"; export/bake_lm.py, gate3_set.py, gate3_instance_jobs.py, trees_far.py,
bake_lut.py, band_*.py; export/out/bake_queue/status.json (109 jobs with wall_s) and the gate3 bake records (export/out/gate3/bake/*.json) for per-job wall
times. Deliver: an ordered table (script, job count, GPU seconds measured or estimated with the basis, what skips when only lamp X / socket Y changes),
the total wall for the FULL chain and for the MINIMAL chain, the pack/manifest/tier/verify/deploy steps after it, and the resume/partial-failure rules.
State which manifests re-pin (export pin rule, docs/decisions.md "8a export gate") and what the QA-23 far-tree irradiance rule means for a re-bake.

## Part B — station 3: where the viewer's shade brightness comes from
Carried since QA-14-2: at CAM_qa_03 the viewer has no deep shade — p10 luma 38-40 against Cycles 7.3, whole frame 1.62-1.67x (docs/qa_round_14.md item 2,
docs/qa_round_17.md item 6). docs/briefs/phase8a4_lod1_shrubs_analysis.md §2 measured the same frames per region: column shade 2.55x Cycles, far water/shore
1.78x, bush 1.79x, pavement 1.37x. Cycles is the reference (it has the shade); the gap is in the bake/viewer chain, and it has never been decomposed.
Frames: viewer renders/web/gate12_cam03.png (full res; also the gate12 tiles), Cycles renders/previews/qa/round13_03_colonnade_walk_cycles.png and, once the lead's
run lands, MAIN renders/qa_comparisons/cycles_p8/cam03_1080_32spp.png. Boxes: scripts/qa_r17_probe.py / qa_r21_probe.py cam03 boxes and the 8a-4 boxes.
Decompose the excess per box by term: (1) the lightmap texel values of the objects under each box (manifest v4 → the asset's EXR/RGBM, UV2; the r17 near_column
box is one ARCH asset) against the Cycles diffuse the bake should equal (irradiance/pi; export/README.md "The lightmap"); (2) the probe / sky-diffuse term the
non-lightmapped objects and the specular path add; (3) the sun DirectionalLight specular; (4) the post chain (bloom / haze: web/README.md post flags) — the
viewer flags `?lighting=baked|direct`, `?probe=0`, `?post=none` are documented in web/README.md but you cannot capture now; use the existing flag captures under
renders/web/ if any cover cam03, otherwise say what capture the viewer engineer must take. State, with numbers, which term carries the 2.55x and whether the fix is
a bake-side change (e.g. the lightmap of the colonnade assets, bounces, `PFA_BAKE_DIFFUSE_WORLD`), a viewer-side composition change, or a lighting.blend change
(the LIGHTING agent holds the Cycles side; do not propose opening the shade in Cycles). Recommend one fix with its chain cost from Part A.

## Report (< 30 lines in the final message; the full tables in the report file)
Part A totals (full / minimal GPU minutes, job counts, the skip rules); Part B the per-term table and the recommended fix; hand-offs; suite count in the commit
messages (export/ has tests: say which ran); last commit id.
