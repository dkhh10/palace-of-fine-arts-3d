# Phase 6 Gate 3 — re-bake ARCH_rotunda_plaster_ceiling_merged (lead, 2026-09-16). Branch `phase6-bake`, worktree .claude/worktrees/phase6-bake. Opus xhigh. Fresh agent.
Read first: CLAUDE.md "Phase 6" section, docs/briefs/process.md, docs/briefs/phase6_gate3_bake.md, export/README.md "Gate 3 — what the bake found" (items 1 and 3: the UV2 relay, the
restored occluders) and the manifest v4 `lightmaps` section, docs/reviews/phase6_bake_gate3_review.md (carries), docs/qa_round_13.md (QA-13-2, the cam04 coffer field: 0.40x, p10 0,
37.8 % of pixels below luma 8), docs/status.md from "2026-09-16 · Session 3" to the end.
Defect: the visible coffer-bed shell of the rotunda ceiling takes the merged asset's lightmap, whose UV2 is dominated by the merged mass's interior and backing faces (map max 0.72,
4.9 % non-zero texels), so the coffer field at cam04 reads black where Phase 5 has light (mean 60.7, p10 27.8). The ribs (their own asset, EXPM_ARCH_rotunda_plaster_ceiling_rib_merged)
are lit and stay as they are.
1. Measure first: which faces of EXPM_ARCH_rotunda_plaster_ceiling_merged are visible from cam04 and from the hero (ray-cast or a face-id render), what fraction of the UV2 area they own,
   and what the bake wrote on them (non-zero fraction, max) — report before changing anything.
2. Fix on the bake side, keeping the Gate 1 geometry frozen (same tris, same placements, same UV1): either relay the asset's UV2 so the visible shell owns >= 0.6 of the map with the
   interior/backing faces packed small (the export re-applies it through export/out/gate3/lightmap_uv2.npz -> TEXCOORD_1 as for the seven relaid assets), or bake the shell at a
   higher texel budget on its own map if the manifest schema allows a second map per asset (say which and why). Re-bake ONLY this asset (one Blender through scripts/blender_run.sh
   with an honest max; Cycles diffuse, same settings as the Gate 3 queue; the bake must not run while a lead Cycles reference render from master.blend is active: `pgrep -f qa_render_round`
   must be empty — if it is not, do the non-render steps and stop, do not wait). Report min/max/clipped and the non-zero fraction as the Gate 3 rule requires.
3. Update the npz for that mesh (loop count must match exactly), the manifest inputs (encode.json / compose.json as the writer expects; do NOT edit manifest.json by hand), sync with
   the same mechanism the Gate 3 bake used; write a hand-off line for the export engineer (which mesh's UV2 changed) and for the viewer (the map is replaced in place or renamed).
Rules: bakes are GPU renders; one Blender at a time; `pgrep -fl "MacOS/Blender"` before each launch; commit after every script that runs; downscale any image to 960 px before viewing.
Report < 15 lines: the measurement, the fix chosen, the new map's stats, files changed for export/viewer, last commit id.
