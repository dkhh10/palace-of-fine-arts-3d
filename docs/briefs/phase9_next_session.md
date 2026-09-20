# Phase 9 — finish everything carried (lead hand-off, 2026-09-20). Resume from docs/status.md "SESSION 8 STOP STATE". Fresh agents only.
User's decision (2026-09-20): "I would like everything to get finished eventually" — every residual listed in docs/delivery.md "Phase 8 / Known issues (owners), carried"
is in scope, including the Phase 5 lighting change at station 2 (this is the user's approval CLAUDE.md requires for a frozen-lighting change; the lead still reports to the
user before the lighting round starts and logs it in docs/decisions.md). Multi-session accepted; on a usage limit stop.
State: deploy 12 live; main clean at the Phase 8 close; master.blend / master_delivery.blend contain belt r2 + backdrop R1; the 4K hero and the comparison sheet exist.
Order of work (hero impact first; each item: analysis (CPU) -> decision -> build -> review -> merge -> master rebuild if Blender -> export -> deploy -> QA on the URL):
1. ONE lighting round for stations 3 and 2 together (LIGHTING agent, Opus high, Blender; lighting and materials never concurrent):
   (a) station 3 deep shade — the colonnade station has read too bright in shadow since Phase 6 (QA-21 carry; the shrub interiors there 2.4x Cycles, docs/briefs/
   phase8a4_lod1_shrubs_analysis.md); (b) station 2 blue-violet shaded stone — the NNE sky fill in the Phase 5 lighting (docs/briefs/phase8b_viewer_fix_report.md item c:
   the Cycles reference is bluer than the photo; acceptance b* >= +5 / h_ab 40-80° / R-B >= +10 at the QA-17 shaded-stone boxes). Both change assets/lighting.blend and need
   the Gate 3 lightmap re-bake for the affected ARCH assets + the instance irradiance + the probe/sky equirects (bake engineer prices the chain first; expect the longest GPU
   job of the phase). The hero must not move more than the acceptance says: measure the QA-17 hero boxes before/after in Cycles at 1080p/32 spp first (scripts/p8_cycles_refs.py).
2. Aerial city blocks (ENV builder, Blender): 8d R3 — a tiled facade / roof / canopy atlas on a new UV0 for the backdrop groups (docs/briefs/phase8d_analysis.md §5 R3,
   the UV1 pin rule in decisions.md "8a export gate"); the Sapling-vs-cones question for backdrop canopies is answered there (impostor billboards if at all). Export re-run of
   the backdrop class; the Cycles side sees it (the phase closes with a new 4K hero).
3. Belt and far trees (ENV + EXPORT + VIEWER, small): the belt covers less pale backdrop than Cycles at the hero band and the shrub hard-edge share rose 5.95 / 7.12 %
   (docs/qa_round_24.md); cam03 draws 3 belt trees as meshes (+1.3 M tris — a billboard-only rule for HB-tagged trees, export/README.md "Phase 8d" r2 notes, saves 1.16 M);
   the 1-2 px dotted rim on far-crown silhouettes at 2 and 5 (VIEWER; docs/qa_round_21.md).
4. Housekeeping: 1440p perf re-take on an idle machine (docs/perf_ab_6c.md rule); regenerate the Phase 8 Cycles refs at full size (scripts/p8_cycles_refs.py) and keep them
   under renders/qa_comparisons/cycles_p8/ (gitignored PNGs); the code carries in docs/reviews/phase8_*_review.md marked "carry" (each its own small commit, reviewed).
5. Close: QA gate on the URL with the six-station tile review; a new 4K Cycles hero (scripts/phase5_deliver.sh 4, blender_run 7200 s; preserve the Phase 8 hero in
   renders/final/phase8/ first); re-run scripts/phase8_sheet.py with the new AFTER (a Phase 9 copy of the script, not an edit of the Phase 8 sheet); docs/delivery.md Phase 9;
   docs/decisions.md; burn in docs/status.md.
Rules unchanged (CLAUDE.md): one builder on the GPU at a time; Chrome never beside Blender or the bake queue; review before every merge; briefs point at files; fresh agents
every session; builders paste the test suite count into commit messages; report to the user at each QA verdict and before the lighting change starts; stop on a usage limit.
Definition of done for Phase 9: every item above closed by QA on the tiles or explicitly re-scoped in docs/decisions.md with the user informed; no open blocker; the hero
not below 4.0 at the close.
