# 8a export brief — re-export the ENV class from the rebuilt master_delivery.blend (Opus high). Branch `phase8-export` (same worktree as the 8c analysis; merge main first).
Read first: docs/decisions.md "8a decision" and its correction (what changed: the 28 shrub/reed card meshes at LOD0/1/2 — LOD2 unique 3 920 -> 6 948 — clumped and
densified; the 1 379 placements' keys, positions, rotations and count unchanged; instance scale moved slightly for cap-bound shrubs), export/README.md "Gate 1"
(export_set / gate1_set: shrubs at LOD2 shared mesh per prototype), "Phase 6c (foliage pass)" rounds 1-3 (export/shrub_lod1.py: the LOD1 walk-in set; the
instance_irradiance join by placement translation, 0.02 m, runner-up 3x), "Gate 5" items 27-48 (tiers.py, groups, verify_glb --gate5, sync_main gate5), and
docs/briefs/phase6_budget.md (ENV placed budget 800 k — the lead accepted +102 k for the LOD2 shrubs; record the new ENV placed total).
Source: MAIN master_delivery.blend rebuilt 2026-09-19 13:01 from the merged assets/environment.blend. First check (bpy, CPU, blender_run.sh 600 s, one Blender at a
time, `pgrep -fl MacOS/Blender` first): the LOD2 shrub prototypes' unique triangles in master_delivery.blend sum to 6 948 and LOD1 to 31 268; if not, stop and report.
Then: re-export the ENV class (the env groups env_t0/env_t2 with the new LOD2 shrub meshes; the shrub LOD1 set via shrub_lod1.py; the far trees / impostor
placements are unchanged and must be byte-identical or you report why), re-run the instance_irradiance join per group (the bake is unchanged: same placements,
so the same 1 376/1 379 must match; the scale change must not break the translation key — assert), foliage albedo check unchanged (materials untouched), gltfpack
as before, tiers.py desktop then --mobile then --no-pack (README item 48), verify_glb --gate5 PASS on both, tiers.unpublished 0, first_frame_on_wire_bytes for both
manifests (tier 0 may move by the env_t0 group's size — report the delta; it must stay <= 49 500 000), re-sync MAIN. No GPU renders, no bakes. Commit after every
script; report under 12 lines: the triangle check, env group bytes before/after, irradiance match count, first-frame bytes, ENV placed total, commit id.
