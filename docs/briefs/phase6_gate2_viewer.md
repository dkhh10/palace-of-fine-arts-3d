# Phase 6 Gate 2 — viewer engineer (lead, 2026-09-15). Branch `phase6-viewer` (round 3, fresh agent), worktree .claude/worktrees/phase6-viewer. Opus high.
Read first: CLAUDE.md "Phase 6" section, docs/briefs/process.md, web/README.md (carries), docs/reviews/phase6_viewer_gate1_review.md (carries), docs/briefs/phase6_gate2_bake.md
(what the bake engineer produces: manifest v3 `pfa-phase6/3`, per-material albedo / roughness / normal KTX2, colour spaces stated), export/README.md manifest v3 section when it
appears (read it from the phase6-bake worktree first), docs/qa_round_11c.md (Gate 1 verdict and the viewer-owned open items).
1. Materials mode `pbr`: MeshStandardMaterial per manifest material with albedo (sRGB) / roughness / normal (linear) from KTX2, `direct` lighting unchanged
   (full sun + PMREM irradiance, no lightmaps yet), ORN normal + AO kept. Grey mode stays selectable (?materials=grey) so Gate 1 frames reproduce.
2. Loading order: geometry first, then textures by distance to the camera station (mips: KTX2 loads whole files, so order the files), loading screen bytes/total.
3. Six-station capture + 1440p perf pass as Gate 1 (web/tools/gate1.sh generalised to gate2.sh: PFA_QUERY passes through, both placeholder sets hidden by default
   for QA captures), pair sheets vs the Phase 5 renders, cam01 tiles; report resident texture bytes (with render targets) against the 1 200 MB budget.
4. Carries from the Gate 1 review that are cheap now: G1-5 (screenshot root containment), G1-7 (camera_test against calc_matrix_camera dump if the export engineer
   left one), the LUT FloatType check on a device without OES_texture_float_linear (fallback path documented).
5. Report < 25 lines: per station frame time / GPU / draws / bytes at 1440p, texture bytes resident, the pair-sheet luma ratios per station (now meaningful: sRGB
   fixed), every failure, last commit id. Chrome only through scripts/chrome_run.sh with the GPU guard in a separate command (the PBR bake queue shares the GPU).
