# Phase 6 Gate 3 — lightmap bake, ORN slot atlases, impostors, hero probe (lead, 2026-09-15). Branch `phase6-bake` (round 3, fresh agent). Opus xhigh.
Read first: CLAUDE.md "Phase 6" section, docs/briefs/process.md, docs/briefs/phase6_plan.md §3 §4 §4b, docs/decisions.md (2026-09-15 entries: ORN option c,
trees = impostors beyond 25 m + thinned near, the GPU rule, the Gate 2 calls), export/README.md (Gate 0-2 sections, manifest v3, carries), docs/qa_round_12.md
(Gate 2 verdict), export/bake_lightmap.py (Gate 0), export/gate2_common.py, export/bake_queue.sh, docs/tech_notes.md "Phase 6".
Sources: geometry/UV2 = export/out/gate1/gate1_bake.blend (frozen; UV2 = per-asset non-overlapping for ARCH/ground, 248/256 px slots for the 988 ORN + ARCH
instances); lighting = the regenerated master_delivery.blend's final rig via light_presets.apply_final_cycles (Eevee-only rigs off, asserted); materials
= the Gate 2 relink (albedo affects bounce only: the pass is colour-off). Never save master*.blend. All GPU work through the detached queue with the GPU
rule, status.json copied to MAIN on every update, per-job max 1 800 s, resume skips done jobs; many short jobs.
1. Lightmaps (Cycles Diffuse direct+indirect, colour off, 128 spp + OIDN, EXR): 2K per ARCH/ground UV2 asset (list from the budget doc; the ENV terrain and
   the near trees get vertex-colour irradiance instead: `bake.target = 'VERTEX_COLORS'`); per-instance 248 px slots for the 988 ORN/ARCH instances into the
   two 4K ORN atlases + three ARCH-instance atlases, baked per placement (the shared mesh at each placement's transform, one job per atlas row-batch of
   ~40 instances, report seconds per instance vs Gate 0's 5.1 s). Encoding: RGBM8 range from the measured max (report min/max/mean/clipped on the source
   EXR per map), lossless KTX2 (`toktx --zcmp`, no Basis) and a gamma-2 encode (the Gate 0 carry); `lightmap_scale = pi`, `rgbm_range` per texture entry.
2. Impostors: Cycles-baked octahedral impostors for the 25 far-tree prototypes, 12 x 12 views on a 2K atlas (albedo+alpha, normal+depth), at the final rig
   with the sun and translucency (cards) as Cycles renders them; per prototype report seconds and bytes; manifest `impostors` block (atlas paths, frame
   grid, prototype height/width, trunk base) matching the 127 `tree_far` entries. Resident budget: 267 MB planned; ETC1S variants later (6b).
3. Hero reflection probe: one cubemap (6 x 1K, EXR -> .hdr) at CAM_qa_01_lagoon_hero's station mirrored below the water plane (z = 2*WATER_Z - cam z),
   final rig, 64 spp, sky through the world's glossy branch; manifest `probe` block.
4. Manifest v4 (`pfa-phase6/4`): lightmaps per asset / per instance slot (atlas, slot uv rect), vertex-irradiance flags, impostors, probe; README section first.
   Sync to MAIN without --delete. Report < 30 lines: queue totals and per-class seconds, bytes and resident sum vs 1 200 MB, the per-map range table,
   every failure, last commit id. The viewer round wires lightmaps + impostors + probe (Gate 4 brief); QA round 13 scores lightmaps alone before Gate 4 post.
