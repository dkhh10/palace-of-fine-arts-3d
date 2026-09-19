# 8c export brief, ANALYSIS FIRST — column concrete texel budget at cam03 (Opus high, fresh agent). Branch `phase8-export` (worktree .claude/worktrees/phase8-export, from main).
Read first: CLAUDE.md Phase 6, docs/decisions.md "PHASE 8 APPROVED", docs/qa_round_17.md §4 (r1c3/r2c3: the column concrete is visibly blurred and vertically banded
at 1 m at station 3) and docs/qa_round_19.md, docs/briefs/phase6_budget.md ("Texture plan and resident memory": the ASTC rule, the per-class texture plan, the ORN
roughness-at-1K lever), export/README.md Gate 2 (the PBR bake: albedo/roughness/normal per material set, resolutions, `materials.sets`, the detail tiling maps
`materials.detail`), export/bake_pbr.py, export/gate2_set.py, export/tiers.py (tiers, lowres, transfer budget), web/src/pbr.js (how sets and detail maps are applied).
Phase 1 (this brief, NO GPU, no renders): (a) identify the material sets and meshes of the colonnade columns and entablature nearest cam03 (the station in
scripts/qa_cameras.py; the assets within 5 m of it from the manifest's location_blender), their baked map resolutions, their UV area, and the resulting texel
density in texels per metre at 1 m from the camera vs what 1920x1080 at cam03's lens resolves (pixels per metre at 1 m); state the ratio; (b) the "vertical banding":
inspect the baked albedo/normal at 100 % for those sets (export/out/gate2 sources, not the KTX2) — is it the bake resolution, the UV layout (stretched shafts),
the detail tiling map's frequency, or the KTX2 UASTC quality; show one 100 % crop pair (source vs the shipped KTX2 at the same texels) at 960 px in
renders/qa_comparisons/p8c_texel_*.jpg; (c) cost the options: a 2K (or 4K) re-bake for the near-column sets only, a higher-frequency detail map for concrete, a UV
re-layout of the shafts, or a KTX2 quality change — each with its resident-memory delta (ASTC rule), tier placement (tier 1 or 2, never tier 0), bake queue wall
time (from status.json history for comparable jobs), and which stations it touches. Write docs/briefs/phase8c_export_analysis.md (< 40 lines) with the numbers,
the diagnosed cause, the recommended option, and STOP for the lead's decision. Commit the analysis and any read-only probe script (export/p8_texel_probe.py).
No edits to the export chain, the bake, or master_delivery.blend yet.
