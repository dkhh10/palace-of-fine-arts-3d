# Code review: branch environment (round 6, 8995384) — MERGE WITH FIXES (merged; fixes as a follow-up)

1. MEDIUM — the sight-line cap does not read scripts/qa_cameras.py: `env_build.py:44` BAND_EYES is a hand-copied snapshot of
   cams 01/05/02; more copies at env_trees.py:501 (cam 01 loc + lens 20), env_build.py:390 and :815 (cam 02). Matches main today,
   silently mis-caps after the next re-station. Fix: `import qa_cameras` and derive from qa_cameras.CAMERAS by name
   (`_qa_01_`, `_qa_02_`, `_qa_05_`), `next(..., None)` so a missing camera drops that eye.
2. LOW — env_sightlines.py:196 classifies ENV_lagoon_bed / MAT_lagoon_bed as architecture (no "bed" test). Fix: `or "bed" in nm`.
3. LOW — env_build.py:271-272 passes the full terrain verts to both halves of the bed split: ENV_lagoon_bed carries ~100k
   loose verts and a 720 m bounding box. Fix: remap used indices per half before mesh_from_tris.
4. LOW — band_sightline_cap is now a global 4 m ceiling on every shrub (put() at env_build.py:706 unconditional; SHORE_H_MAX
   applies where no ray hits the podium). Fix: return None when no eye constrains the point, or state the global ceiling.
5. LOW — env_sheet_r6.py:22 reads renders/previews/qa absolutely; guard with .exists().
Verified: pins hold, willows ENV_tree_willow_NN_LOD0/1/2 seeded, cam06 deterministic (Random(77)), shared materials,
MAT_lagoon_bed via load_material, idempotent, no out-of-ownership files.
