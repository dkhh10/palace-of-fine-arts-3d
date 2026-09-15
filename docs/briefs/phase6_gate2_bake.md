# Phase 6 Gate 2 — material (PBR) bake (lead, 2026-09-15). Branch `phase6-bake` (round 2, fresh agent), worktree .claude/worktrees/phase6-bake. Opus xhigh.
Read first: CLAUDE.md "Phase 6" section, docs/briefs/process.md, docs/briefs/phase6_plan.md §2 §3 §5, docs/briefs/phase6_budget.md (per-asset table: UV1
atlas groups, texture plan, the hero-near set), export/README.md (Gate 0 + Gate 1 sections, manifest v2, carries), docs/qa_round_11.md (Gate 1 verdict and
defect list), docs/reviews/phase6_export_gate1_review.md, export/bake_pbr.py (Gate 0), export/bake_queue.sh, export/gate1_common.py.
Sources: geometry + UV1/UV2 = export/out/gate1/gate1_bake.blend (the frozen Gate 1 set); materials = the REGENERATED `master_delivery.blend` in the MAIN
checkout (2026-09-15 14:44, carries MAT r10: dome cap membrane + coffer albedos). The Gate 1 blend copied the OLD materials: relink every material by name
from the regenerated delivery file before baking (append, replace same-name), and prove it on MAT_dome_membrane (the 28-panel ridge inputs must be present).
Never save master*.blend. Every Blender run through blender_run.sh; every GPU job through the detached queue with the GPU rule (no other live registered pid);
status.json written to the MAIN checkout's export/out/bake_queue/status.json (the shared file the viewer's guard reads), not only the worktree copy.
1. `export/bake_pbr.py --gate2` per UV1 atlas group / ORN prototype: albedo (base colour after every procedural mix, the round-9 photo projection included,
   scene-linear 16-bit PNG), roughness, and the tangent normal combined with the Gate 1 hi->lo normal (ORN) or the material's bump/normal detail (ARCH) —
   metal only if any material has it (report: none expected). 2K default; 4K for the hero-near set as docs/briefs/phase6_budget.md names it (inside the
   cam01 frame within 30 m). Foliage cards keep their shipped 1K textures (no bake); MAT_water_lagoon is the viewer's; backdrop procedurals are baked at 1K.
   Per job print wall seconds and bytes; the queue resumes, one Blender per job, max 900 s.
2. KTX2: UASTC + zstd + mipmaps for desktop (`export/gltf_pack.sh --gate2`); write the mobile ETC1S variants only for the hero-near set now (timing sample),
   the rest at Gate 5. Report bytes per class and the resident-memory sum against the 1 200 MB budget (the Gate 1 projection was 1 343 MB: apply the
   levers the budget doc names — ORN albedo/roughness at 1K under 2 m, backdrop ETC1S — and state what the sum is after them).
3. Manifest v3 (`pfa-phase6/3`): per-material texture sets, colour spaces (albedo sRGB-encoded or linear: state it and be consistent with the viewer's
   loader), lightmap_encoding unchanged, `materials.mode = "pbr"`; documented in export/README.md; sync to MAIN without --delete.
4. Verification without the viewer: re-render the Gate 0 reference station (cam01, 1280x720, 64 spp) of the SLICE with the baked textures applied to
   flat Principled materials in Blender vs the procedural originals: sunlit / shaded column and capital boxes within 3 % linear. Report the numbers.
5. Report < 30 lines: per-class job counts and seconds, texture bytes and resident estimate, the verification boxes, every failure or item left, the last
   commit id. Commit after every script (export/*, export/README.md only). The viewer engineer wires the PBR set at Gate 2's viewer round; QA measures the
   PBR set alone (direct lighting, no lightmaps) before Gate 3 combines them.
