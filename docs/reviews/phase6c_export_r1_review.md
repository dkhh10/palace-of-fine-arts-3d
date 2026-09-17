# phase6-export round 1 (6c items A/D/E) — MERGE WITH FIXES

Range `main..d553a5a`, read pinned at d553a5a while round 2 adds commits. Only `export/` touched; no binaries, no
other owner's files. Holds up: `-vpf` over `-vp 16` is justified by a measured failure (README 36); the LOD1/LOD2
join is sound — one `instance_irradiance.json`, `irradiance_sha256` pinned in both order files, `[mesh, count,
offset]` segments re-checked against a running cursor per node (verify_glb.py:113-120), `glb_bytes` pinned both
sides, the subset restriction applied to every count (gate4_instance_order.py:164-184, 266-276); KTX2 OETF is right
(albedo sRGB, translucency/normal/data linear); `manifest_v4` copies every field from a report and invents nothing.
Carried, not a finding: the 2K foliage maps are a plain upsample — decision 2 says drop them, which is round-2 work,
and the code already says so (foliage_tex.py docstring, README 39).

1. **trees_far.py:310 / shrub_lod1.py:138-140 — the placement asserts are tautologies (fix now).**
   `no.location = Vector(row["trunk_base"])` then asserts `no.location == trunk_base`; shrub_lod1 builds the object
   from `src_ob.matrix_world.decompose()` and then compares its translation to `src_ob`'s. Both always pass, and
   `PLACE_TOL_M` never bites. The real shrub residual (`d` vs `a["location_blender"]`, line 133) is computed, stored
   as `centre_delta_m` and never asserted. So README 34 "asserted per row", the manifest's `placement_check.
   translation = "asserted ... on every one of the 127 rows"` and shrub_lod1's docstring "every one of them is
   asserted against the Gate 1 asset's recorded world bbox centre" are claims no code makes. The only substantive
   geometric check is the crown-top deviation (trees_far.py:317-321), which does bound scale.
   Fix: assert `d < PLACE_TOL_M` in shrub_lod1, and in trees_far assert the exported `env_trees.gltf` node
   translations equal `to_gltf(trunk_base)` (the swap already exists in gate4_instance_order) — else soften the claims.
2. **trees_far.py:192 — `leaf_area_kept` is modelled, not measured (fix now).**
   `keep_fraction * scale**2` assumes equal-area cards and treats a triangle ratio as an area ratio; README 34 quotes
   the 0.24-0.80 range as a result. Fix: sum `f.calc_area()` over the card components before the drop and after the
   grow and report the true ratio.
3. **trees_far.py:172 — card thinning keeps contiguous blocks (fix now).**
   `(i % 1000) >= keep_pct` keeps cards 0..keep_pct-1 of every 1000 in bmesh face order, which is branch-coherent. At
   gate1_set's near-tree fraction that was mild; at these 18-31 % keeps it bald-patches whole branches, and growing
   the survivors 1.6x cannot fill a gap. Fix: `(i * 997) % 1000 >= keep_pct` — same determinism, scattered.
4. **foliage_tex.py:116,142 — the colour spaces are assumed, not read (fix now).**
   `s2l()` is applied to every albedo source and the factor map is taken as linear, while `read_foliage.image_info`
   already records `colorspace` per image and nothing checks it. A Non-Color albedo or an sRGB factor map would ship
   a silently wrong tint — the exact defect item D exists to close. Fix: assert `"sRGB"` / `"Non-Color"`.
5. **read_foliage.py:80-88 — `chain_to_image` drops unrecognised terms silently (carry).**
   The "follow the first linked colour-ish input" fallback walks through any node it does not know (a Mix multiply, a
   Gamma) contributing nothing, and `ShaderNodeHueSaturation` is pinned to identity without checking its sockets are.
   The docstring says "the structure asserted". Fix: raise on an unknown `bl_idname`; assert the HSV sockets.
6. **verify_glb.py:145 — the new checks are silently optional (carry).**
   `extra_glb_check` / `shrub_lod1_order_check` return `None` when the glb or report is absent, so a gate run after a
   failed pack reports ok with no tree/shrub check. Fix: fail when the manifest declares the block but the file is gone.
7. **sync_main.sh:39 — `[ -n "$PFA_SYNC_STATUS" ]` fires on `PFA_SYNC_STATUS=0` (carry).** Fix: `= 1`.
8. **gltf_pack.sh trees/shrubs fallback — a PNG glb ships under a KTX2 manifest (carry).**
   If gltfpack refuses the KTX2 glTF the script packs the PNG one, prints to stderr and exits 0 while `manifest_v4`
   still advertises `textures.ktx2_dir`. Fix: record `SRC` in the report and fail unless the caller opted in.
