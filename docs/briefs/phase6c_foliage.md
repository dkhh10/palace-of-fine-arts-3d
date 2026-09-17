# Phase 6c — foliage pass (lead, 2026-09-17; user's decision: foliage before 6b deployment, full look stays the default)
Why: the user's close-up at station 2 (and the lead's tile pass, decisions.md "FINAL JUDGEMENT OF 6a") shows the foliage as the one thing a walker sees that is not the building:
a far-tree IMPOSTOR (85 px frames, classified "far" once at export by distance to the hero) standing a few metres from the camera as a blue blob; near trees as flat leaf cards
(no translucency, hard mask, low-res 1K cards); shrubs/reeds as LOD2 confetti with a hard mask and an albedo 45° too warm.
Goal and acceptance: foliage credible at 3 m from every station and along the walk. Measured by 100 % tiles at stations 1, 2, 5 against the Cycles references
(renders/final hero, renders/previews/qa/round13_02/05_*_cycles.png), judged by the lead; QA 16 (Opus xhigh) scores all six stations: no station drops more than 0.1, station 2
must rise; frame time within +3 ms of round 15 at 1440p; resident GPU memory reported. Two rounds maximum, then the lead's judgement and 6b.
Items (owner):
A. Every tree gets a mesh (export): the 127 far trees' 16 prototypes at LOD2 (target <= 8 k tris each; decimated by the existing export_set path, own UVs, `_LOD2` names) into a
   separate lazily-loaded `env_trees.glb` with EXT_mesh_gpu_instancing placements (127 rows, same transforms as the impostors' tree_far entries); manifest block `trees.far_mesh`.
B. Tree lighting for A (bake): per-prototype vertex AO (16 jobs, lights off, white world, shadow-ray override as gate 4) on the export's LOD2 topology, plus per-placement RGB
   irradiance for the 127 (existing kind `instance`, join by location). Impostor diagnosis (bake): one prototype's atlas frame beside a Cycles render of the same prototype at the
   same view and rig — is the blue cast in the atlas (bake) or in the viewer's shading of it? Re-bake the 2K variant with the final rig if the atlas is wrong.
C. Leaf shader (viewer): two-sided, translucency for the sun through the card (a constant per material from the Phase 5 MAT_leaf_* translucency, or the map from D), soft edges
   (alpha-to-coverage when the target is multisampled, else alpha hash + the existing post), normals bent toward each tree's crown centre (computed at load per tree object),
   applied to near trees, far-tree meshes and shrub/reed cards alike. Runtime LOD: mesh within `treeMeshDist` (default 40 m from the walker, flag) else impostor, with a short
   crossfade; impostor atlas = the 2K variant on desktop. Shrubs/reeds: LOD1 within 30 m (from E), LOD2 beyond.
D. Leaf textures at 2K (export): albedo+alpha (+ translucency mask if the node tree has one) from the Phase 5 MAT_leaf_* trees, KTX2 UASTC, the cut chain read as Gate 3 (0.45/0.42).
E. Shrub/reed LOD1 meshes (export) beside the LOD2 in env.glb (same placements; manifest says which is which); the albedo hue: measure the baked MAT_shrub_*/MAT_reeds albedo
   against the Cycles render's foliage hue (57.7° vs 102.4° at cam02) and fix the bake if the albedo is wrong (colour space, the cut chain, a missing tint node), not the viewer.
F. Round-16 capture (viewer, gate4.sh set + cam02 100 % tiles + a 3 m walk-in shot at station 2), QA 16, lead judgement.
Sequence and the GPU: viewer starts C now on the shipped assets (Chrome captures pause on status.json). Export starts A, D, E now (CPU + short Blender runs, no GPU render).
Bake starts with the impostor diagnosis now (short GPU), then B once the export's LOD2 tree set is in MAIN (the export engineer reports it in status.md). Hard cap 3 builders.
Branches: phase6-bake, phase6-export, phase6-viewer (merge main first). Reviews before every merge as Phase 6. Budget: one session; log burn at the end.
