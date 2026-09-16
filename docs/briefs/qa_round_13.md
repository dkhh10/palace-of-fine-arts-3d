# QA round 13 — Gate 3 lightmaps alone, before Gate 4 post (brief from the lead, 2026-09-16). Opus 5 xhigh. Fresh agent. Do NOT run Chrome or Blender.
Read: docs/qa_round_12b.md (Gate 2 verdict and its carried list), docs/briefs/qa_round_12b.md, docs/quality_checklist.md (tail), docs/qa_round_10b.md (the hero boxes),
`git show phase6-bake:export/README.md` "Gate 3 — what the bake found" (items 1-9: the UV2 relay, the restored occluders, the near-black surfaces, encodings, impostor range,
probe culling, sky.diffuse), docs/reviews/phase6_bake_gate3_review.md, web/README.md (lighting modes, ?lighting=direct|baked, what is and is not applied yet).
What changed since round 12b: the viewer's lighting mode `baked` — Cycles diffuse lightmaps (direct+indirect, sun included) on UV2 per asset, 248 px per-instance slots for the
988 ORN/ARCH instances, vertex irradiance on terrain/near trees, sky.diffuse as the diffuse environment for everything unlit-mapped, sun specular-only. NOT in yet (Gate 4,
do not score as defects, list as "expected"): post (bloom, AO, mist, vignette), the planar water, the octahedral impostors (127 far trees may still be absent or stand-ins),
and — if docs/status.md says the re-export has not landed — the seven relaid-UV2 assets (uv2_in_glb false: they show the lmg1_* fallback or direct shading; name them per station).
Inputs: the viewer engineer's baked capture named in the latest docs/status.md entry (six stations, baked, post off, placeholders hidden), the matching direct-mode
capture of the same stations, pair sheets vs the Phase 5 Cycles renders, renders/web/tiles/<capture>/ for the cam01 six 100 % tiles, the perf json.
1. Parity, lightmaps alone: for each station, the round-10b boxes (hero shade band, S-colonnade wall, capital row, pier face cam05) measured baked vs Phase 5 Cycles vs direct:
   report lum / hue / sat / std per box; state per box whether the lightmap closed, halved, or left the deficit that round 12b attributed to lighting.
2. The carried lighting items, one verdict each with numbers: QA-12b-1 olive cast (% of building pixels G > R at cam02 / cam06 vs 16.0 / 21.9 and the Phase 5 0.1);
   QA-12b-2 S-colonnade blow-out (wall mean vs 201-221, panels now shaded?); QA-12-3 remaining flatness; QA-12-4 per-instance variation (shaft-to-shaft CV of the colonnade
   columns vs Phase 5's 0.469 / 0.539); sunlit-attic saturation still >= 0.94x (must not drift).
3. The bake's own open questions: cam04 rotunda ceiling — does the coffer field read black (the 1 102-tri plaster shell drawn in front of the rib/coffer mesh: geometry, Gate 1)
   or lit; near-tree shadows lighter than Phase 5 (thinned cards); ENV_tree_broadleaf_06 inside a city block (on record, ENV placement); the drum band and any other surface
   that reads black where Phase 5 has light — for each say lightmap defect / geometry defect / expected.
4. The cam01 six tiles at 100 %: lightmap seams at UV2 island edges, slot bleed between adjacent ORN instances, texel blockiness on the relaid assets (their texel is 5-17 cm),
   encoding banding in the shade (gamma2 vs the rgbm8 variant if the viewer exposes it), light leaks under the colonnade roof, double shadows (sun specular + baked).
5. Score table per station (all rubric rows) vs round 12b and round 9 (Phase 5); verdict for the round: LIGHTMAPS ACCEPTED / REBAKE NEEDED (name the assets) — Gate 4 itself
   is judged after post + water + impostors, so no gate verdict here. Name sweep: read the export engineer's latest sweep result, restate the count.
Write docs/qa_round_13.md (< 110 lines), renders/web/round13_gate.png (960 px composite, one per gate), append docs/quality_checklist.md; commit only those + scripts/qa_*.py.
Report < 20 lines: the verdict, the rebake list if any, the three worst boxes with numbers, the commit id.
