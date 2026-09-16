# Phase 6 Gate 3 — export hand-off: Gate 3 UV2 + COLOR_0 into the glbs (lead, 2026-09-16). Branch `phase6-export`, worktree .claude/worktrees/phase6-export. Opus high. Fresh agent.
Read first: CLAUDE.md "Phase 6" section, docs/briefs/process.md, export/README.md on branch `phase6-bake` (`git show phase6-bake:export/README.md`,
the "Gate 3 — what the bake found" section, items 1 and 3, and the manifest v4 section `lightmaps`), docs/reviews/phase6_export_gate1_review.md (carries),
export/gltf_gate1.py / export/gltf_export.py / export/verify_glb.py / export/sync_main.sh (extend, do not fork), docs/tech_notes.md "Phase 6".
Sources (read-only, absolute paths in the MAIN checkout): export/out/gate1/gate1_bake.blend (frozen Gate 1 geometry), export/out/gate3/lightmap_uv2.npz
(7 meshes, float32 (n_loops, 2) per `EXPM_*` mesh name = the Gate 3 re-laid UV2), export/out/gate3/vertex_irradiance.npz (14 near-tree meshes, per-vertex
linear RGB irradiance), export/out/gate3/manifest.json (v4; `lightmaps.assets[*].uv2_in_glb` false on the seven, `lightmaps.vertex_irradiance.in_glb` false).
Goal: env.glb / arch.glb / ground.glb re-exported so the seven assets carry the Gate 3 UV2 as TEXCOORD_1 and the 14 near trees carry COLOR_0, with nothing
else changed (the Gate 1 geometry is frozen: same tris, same placements, same UV1, same instancing, same gltfpack flags incl. -vp 16 on env.glb).
1. Load the UV2 npz onto the seven meshes by name (assert loop counts match exactly; the frozen Gate 1 layout stays in the blend as `UV2_gate1`, the export
   writes the Gate 3 layer as TEXCOORD_1). Load the vertex irradiance as a colour attribute on the 14 tree meshes and export it as COLOR_0 (linear float or
   normalised u16, state which; check the exporter does not sRGB-encode it and record the encoding + a per-mesh mean in the hand-off json). Assert vertex
   counts match; report the mean vs the npz mean per mesh after a round trip through the glb (read back with pygltflib or the meshopt-decoded buffer).
2. Re-run the pack (gltf_pack.sh, same flags as Gate 1/2) and export/verify_glb.py: drawn tris vs export_set within 1 %, mesh nodes == objects, 0 objects at
   the origin, texCoord >= 0, plus two new assertions: the seven meshes' TEXCOORD_1 differs from the Gate 1 layer (UV2 island-area fraction reported, expect
   >= 0.15 of the square) and the 14 trees carry COLOR_0. Sizes of the three glbs before/after.
3. Hand-off: write export/out/gate3/uv2_relay_status.json ({mesh: {uv2_in_glb: true, coverage, glb}} for the seven, {mesh: {in_glb: true, encoding, mean}}
   for the 14) — the bake engineer's manifest writer flips the manifest flags from it at the merge; do NOT edit manifest.json by hand. Sync with
   export/sync_main.sh (no --delete). Name sweep on the export set (scripts/qa_name_sweep.py) unchanged: 0 hits.
Rules: every Blender run through scripts/blender_run.sh (this is a glTF export, no render: max 900 s, one Blender at a time, `pgrep -fl "MacOS/Blender"`
first). No GPU renders on this branch. Commit after every script that runs. Report < 20 lines: per-mesh UV2 coverage before/after, COLOR_0 encoding + mean
check, verify_glb results, glb sizes, sync done, last commit id. If a loop-count or vertex-count mismatch appears, stop and report it — do not re-decimate.
