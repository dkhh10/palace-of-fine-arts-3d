# Phase 8a re-scope analysis — the shrub/reed shore band (brief from the lead, 2026-09-19). Opus 5 high. Fresh agent. CPU only: NO Blender, NO Chrome.
Branch `phase8a-rescope` from main, worktree .claude/worktrees/phase8a-rescope. Deliverable: docs/briefs/phase8a_rescope_analysis.md (< 120 lines) + probe scripts
scripts/p8a_rescope_*.py; stop for the lead's decision. Do not build.
Read: docs/decisions.md "PHASE 8 APPROVED", "8a decision", "QA 20" entries; docs/qa_round_20.md §1 and the shrub section (the metric: leaf-green share vs the reference
at the QA-17 boxes moved at 1 of 8 boxes with 1.8x/2.5x more cards; hard-edge share up at 6/8; "the cards' albedo/lighting, not their count, dominates it");
docs/qa_round_17.md §3 (the eight shrub boxes, reference values: leaf-green share, hard-edge share, level, hue); docs/briefs/phase8a_env_report.md (clump emitter, what each
LOD set is, which set each station draws); export/README.md "Phase 8a" and the env group layout; docs/briefs/phase8_env_shrubs.md; scripts/env_*.py for the shrub/reed
card generator and MAT_shrub* materials (read the source, do not run it); docs/reference_sheet.md material catalog (the shrub/reed materials are frozen: any MAT_ change
needs a decisions.md entry and the user's approval).
Questions, each answered with a number from the captures/textures on disk (renders/web/gate9_cam0*.png, gate8, the reference photos, export/out albedo textures of the
shrub cards, the lightmap/irradiance values the export joins to the shrub instances — read the manifest and the KTX2/PNG files, not the blend):
1. WHAT the reference shore band is made of at each box: the leaf-green share decomposed into hue/saturation/level histograms of the reference vs the viewer; is the gap
   colour (our cards are too dark/olive/desaturated), coverage (gaps of water/ground between cards), or species (the reference has reeds/willow fronds/grass the model lacks)?
2. WHERE the cards' colour comes from in the viewer: the card albedo texture (its mean/percentiles in linear and after the LUT), the per-instance irradiance/lightmap term,
   the translucency/backlight, the alpha coverage cut. Which term would move the leaf-green share the most, by how much (simulate on the capture pixels: re-tint the shrub
   mask by the candidate factor and re-run the QA-17 box probe, no rendering).
3. WHICH LOD set draws in each box at each station (LOD0 walk-in / LOD1 / LOD2) and whether swapping the set at 80-160 m (LOD1 instead of LOD2 at the hero shore) is
   inside the frame budget (tris per station from the gate9 sidecar) — the walk-in bug fix runs in parallel; use the export's numbers.
Deliver: a costed option list — for each: what changes (export-only, viewer-only, ENV blend + master rebuild + export, or a frozen MAT_ change needing user approval),
GPU minutes, MB, which files, the predicted leaf-green share at the 8 boxes from the simulation, the risk to the hard-edge share and the level — and ONE recommendation.
Commit the analysis and scripts on the branch with the attribution lines. Report to the lead < 15 lines: the gap diagnosis per box, the top lever with its predicted
numbers, whether it needs the user's approval, commit id.
