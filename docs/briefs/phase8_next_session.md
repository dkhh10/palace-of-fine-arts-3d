# Phase 8 — next-session plan (lead hand-off, 2026-09-19). Resume from docs/status.md "SESSION 7 STOP STATE". Fresh agents only.
State: deploy 9 live (band atlas default, dense LOD2 shrubs, 2K + coverage, detailproj dominant); gate9 capture on disk (renders/web/gate9_*, 960 px copies) — not yet QA'd.
Order of work:
1. QA 21 (Opus xhigh) on gate9: brief = docs/briefs/qa_round_19.md's method applied to the band (crown crossings vs Cycles at 1/2/5, QA-17 boxes, the station-2 crown tile
   Cycles | 2K | band at 100 %, the hero 200 % crop, the 100 % dot-grid check that QA 20 flagged at share 0.15 — the band ships at 0.10; willows at the water's edge for flat
   highlights), plus a regression pass vs gate8 and the payload/perf/resident rules. Verdict closes 8b or names the fix (share, or the willow re-bake `PFA_BAND_RANGE=band`).
2. Viewer fix round (Opus high, branch phase8b-viewer from main): (a) the env_shrubs.glb LOD1 walk-in set is drawn in full at every station although shrubLod reports
   lod1:0 (+1.12 M tris/frame, mobile too) — find why the distance gate does not hide it and fix; re-measure 1440p same-session; (b) `resident()` never counts the impostor
   atlases (custom uniform; ~+67 MB unbilled) — count them and restate the figure of record; (c) blue-violet shaded stone on desktop cam02 (the probe tint) — measure and
   propose. Review, merge, deploy 10, capture, fold into QA 22.
3. 8a re-scope (ENV + export): the leaf-green share moved at 1 of 8 boxes with LOD2 density; the metric is colour coverage, so the next lever is the shrub albedo/lighting on
   the cards (materials are frozen: a decisions entry + user approval per CLAUDE.md before any MAT_shrub change) or the LOD0/LOD1 sets where the walk-in looks. Write the
   analysis first (CPU), decide, then build.
4. 8d backdrop (ENV builder in Blender: textured city blocks, Sapling-based backdrop trees instead of faceted cones; export re-run of the backdrop class; the UV1 pin check
   as in 8a) and 8e mobile (export: LOD2 leaf-card scale; viewer: nothing more after 2b). Each: build -> review -> merge -> master rebuild if Blender -> export -> deploy -> QA.
5. Close Phase 8 with the comparison sheet the user asked for: viewer hero gate7 (before Phase 8) vs the final capture; the Cycles 4K hero v2 (renders/final) vs a NEW 4K
   Cycles render of the changed master_delivery.blend (scripts/phase5_deliver.sh 5, blender_run 7200 s); the reference photo (ref 169); 960 px composite + full-res tiles;
   the lead's own tile pass; delivery.md Phase 8 section; burn.
Rules unchanged: one builder on the GPU at a time; Chrome never beside Blender or the bake queue; review before every merge; briefs point at files; stop on a usage limit.
