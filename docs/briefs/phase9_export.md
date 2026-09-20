# Phase 9 export — the belt-tree billboard rule at cam03, plus the export review carries (brief from the lead, 2026-09-20). Opus 5 high. Fresh agent.
Branch `phase9-export`, worktree .claude/worktrees/phase9-export (merge main first). Owns export/ (scripts, README), export/out in the worktree. Read
docs/briefs/process.md first. **CPU only until the lead says otherwise**: no render, no bake, no Chrome; a read-only Blender run through scripts/blender_run.sh
(open a file, read data, quit) is allowed one at a time. The lighting round holds the GPU after the lead's references; the export re-run that ships your rule
is scheduled by the lead behind the lighting chain (it will ride the same export/deploy).

## Item 1 — cam03 draws 3 belt trees as meshes (+1.3 M tris, +28 draws; QA 23 residual 3, QA 24 item 3, export/README.md "Recorded, not fixed: cam03 draws
the belt trees as meshes"). The README prices a billboard-only rule for the 39 HB-tagged rows (1.16 M saved on desktop) and names its cost: cam03 stands
6.5 m from the nearest belt tree. Analysis first, CPU: from the belt JSON (docs/briefs/phase8d_belt_r2_report.md) and the cam03 station (scripts/qa_cameras.py,
18 mm), which of the 3 within-15-m belt trees are INSIDE cam03's frustum, at what screen size, and what a magnified impostor card looks like there
(docs/briefs/phase8e_analysis.md has the card-magnification numbers). Then choose, with numbers: (a) billboard-only for all HB rows; (b) billboard-only for the
HB rows outside every station's walkable reach; (c) a per-row mesh distance if the viewer can carry it cheaply (say what the viewer would need — hand-off,
not a viewer change from you). Implement the chosen rule in export/trees_far.py for both sets (desktop walk-up + mobile far), instance rows re-dumped
(instance_rows.mjs x2, gate4_instance_order), the far-tree manifest counts, verify_glb, the export pin (docs/decisions.md "8a export gate": say what moves and why),
tests updated. Do NOT run the pack/deploy: leave the chain ready (README section "Phase 9") and report the exact command list the lead runs after the lighting
re-bake.
## Item 2 — carries: docs/reviews/phase8_export_r1_review.md items 2-4 (tiers.lowres entry for the 1 K albedo, p8_texel_probe --root default, the KTX2 claim in
phase8c_export_analysis.md (b)4) and phase8_export_r6_review.md item 7 (the stale pin artefact `glbs` block). Each its own small commit.
## Report (< 20 lines): the frustum table for the 3 near belt trees, the chosen rule and its tri/draw saving per set, the pin delta, the command list, suite
count in every commit message, last commit id.
