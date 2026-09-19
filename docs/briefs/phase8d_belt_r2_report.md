# Phase 8d belt r2 — build report (assembled by the lead from the ENV builder's report and docs/phase8d_belt_r2_trees.json; branch phase8d-env 0748e42, review docs/reviews/phase8_env_r3_review.md)
- The four ENV_backdrop_hall_belt_* icosphere objects are removed (`BELT_ICOSPHERE = False` keeps the placement geometry as a record).
- 39 far trees (`env_trees.hall_belt`, note tag HB) on the hall's concave east face, appended after every relief pass and the gallery gate, so no existing tree moved
  (PLAN_TABLE rows 0-130 untouched). Species cypress 14 / eucalyptus 7 / pine 6 / columnar cypress 6 / redwood 6 from a shuffled deck; 12 prototypes, every one mapped by
  gate3_set proto_map (_LOD2 -> _LOD1) onto the 16 baked impostor prototypes — no atlas re-bake. Heights 12.5-16.8 m; cap 16.0 m world z applied before the 0.94-1.08 size
  jitter, so realised tops run 11.1-17.0 m (two crowns ~0.3 m above the 16.7 m parapet, 3 m under the 20 m crest; re-cap only if the tile review sees it). Spacing 4.5 m
  along the offset curve of the hall polygon (the first build's real defect was 10-16 m gaps). Undersides grounded by the far-tree path's land snap.
- Tri counts: ENV LOD0 13 916 262 -> 15 444 910 (+1 528 648, ~39 k per tree: a Cycles / master_delivery cost), LOD1 5 244 528 -> 5 298 928, LOD2 779 474 -> 833 874;
  objects 5 929 -> 6 042. Export: backdrop_forest loses 6 900 tris, far billboards 127 -> 166 (+78 placed tris); ENV placed 901 874 -> 895 052; near 20 unchanged
  (tree_allow headroom 6 908 vs the cheapest extra candidate 12 892).
- Probe (scripts/env_belt_probe.py, one ray per band pixel): hall wall visible through the colonnade 2.4 -> 3.3 % frame-left, 1.5 -> 1.1 % frame-right, 6.5 -> 0.8 % at
  cam05; belt pixels luma 0.160 / sd 0.095 / sat 0.262 vs the icospheres' 0.112 / 0.102 / 0.398 (ref 169 band 0.337 / 0.200); band hf 0.0569 -> 0.0660 (N). Harness caveat:
  ENV previews are placeholder sun / AgX Base / -0.8 EV — direction only.
- Sheet renders/qa_comparisons/phase8d_belt_r2_960.jpg (lead viewed: crowns with sky gaps and trunks, no shards at 1/2/5). Tree list docs/phase8d_belt_r2_trees.json
  (name, prototype = the export's far-tree key, species, seed, position, scale, rotation, height).
- Export risks named by the review: p8d_pin expectations (trees 186, far 166, lod2_blob 85, EXPECT_ENV_DELTA -6 822 net); the far-row re-sort is an interleave (name-sorted
  bpy.data.objects), so TREEFAR_### indices shift; vertex-AO arrays needed for 3 prototype LOD2 meshes new to the far block; backdrop_forest's Gate 2 UV1 changed -> backdrop
  re-bake. Carries: hall_belt has no lagoon keep-out (all 39 on land, closest 15.4 m); env_belt_sheet.OUT hard-codes the worktree path.
