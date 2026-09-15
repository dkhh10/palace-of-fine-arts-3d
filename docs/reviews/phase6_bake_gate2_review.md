# phase6-bake @ a9794e8 — Gate 2 PBR bake — MERGE WITH FIXES (10 findings: 3 fix now, 7 carry)

Reproduced from the records: 60 jobs / 182 maps / 168 shipped + 14 constant / 3245.3 s / 274,500,161 KTX2 B (= 261.8
MiB; "274.5 MB" is decimal) / resident 1166.33 MB — all correct. Sound: the colour chain (linear buffer -> sRGB-encoded
16-bit PNG for albedo only -> `--assign_oetf srgb` -> manifest `"srgb"`, all else linear end to end); TANGENT + POS_X/
POS_Y/POS_Z (bake_lib.py:126-128), as the Gate 1 ORN normals and glTF; the -1 sentinel mask is strict (bake_lib.py:207);
the albedo bake does capture the whole tree — the round-9 projection comes from Geometry>Position (mat_build.py:499-515),
not a camera/window coord or baked UV, and gate2_set.py:255-265 bakes a real placement; the ENV per-polygon restore is a
deterministic world-space KDTree nearest (gate2_set.py:217-231); nothing writes master*.blend (save_copy:142 refuses);
no tracked binary > 5 MB, no path hard-coded past `PFA_MAIN_ROOT`; worst job 307 s of the 900 s cap, 0 failures.

1. **export/bake_queue.sh:87 — fix now.** The GPU rule exempts *any* registered Blender running `bake_orn.py|bake_pbr.py`,
   not just this queue's own child, so a second queue (e.g. the export engineer's Gate 1 run) would bake concurrently.
   Fix: record the pid `blender_run.sh` registers for this runner and exempt that pid only.
2. **export/bake_pbr.py:84-86 — fix now.** Cycles' DIFFUSE colour pass weights base colour by (1 − Metallic), so the two
   metallic backdrop materials bake dark (`MAT_lamp_post` ~15 % everywhere, `MAT_backdrop_door_green` fittings up to
   70 %) and the viewer applies `metallic` again — double attenuation. Fix: for a job with `metallic`, bake the albedo
   through the same `emit_bsdf_input(mat, "Base Color")` rewire already used for the metallic channel.
3. **export/manifest_v3.py:168 + README "the 9 under it" — fix now.** Only 7 ORN prototypes ship 1K albedo, not 9:
   gate2_set.py:329 takes `size1 = j1["size"]` from Gate 1, whose threshold is `ORN_SMALL_DIM_M = 1.0`, so
   `gate2_common.size_for`'s ORN branch is dead and the 1.60/1.63 m prototypes keep 2K (~8 MB). The 1166.33 MB total is
   still right. Fix: say "7 under 1 m", or route the ORN size through `size_for(cls, max_dim_m)`.
4. **export/gate2_verify.py:350 vs 352-356 — carry.** `worst_abs_delta_with_normal_pct` / `worst_abs_noise_floor_pct`
   are computed after verify.json is written: printed, never persisted. Fix: move the write below them.
5. **export/gate2_verify.py:341 / gate2_report.py:89 / README table — carry.** The pass metric mixes variants (column =
   B0 material-only, capital = B with the normal map), and the report prints `delta_with_normal_pct` for the non-hi-poly
   rows while `pass_3pct` uses `delta_pct` (−1.39 vs −1.376). Fix: print the field the pass test uses, or both columns.
6. **Verification confidence — carry.** The capital boxes are 218/219 px and their own noise floor (−2.35 %, −5.23 %)
   exceeds the 2.78 % the gate passes on (column, 739 px: 1.4 % vs 1.0 %). Fix: more spp or a seed-averaged A.
7. **export/bake_pbr.py:39-44 — carry.** `apply_final_cycles_checked` is called on the Gate 0 branch (:139) and in
   gate2_verify.py:39 but not on the --gate2 bake path. Harmless for DIFFUSE/ROUGHNESS/NORMAL/EMIT (no light path), but
   the Eevee-rig assertion is absent. Fix: call it, or assert the bake type never samples light.
8. **export/gate2_set.py:324 — carry.** `set_material(ob.data, mats)` writes the master prototype's slot order onto the
   Gate 1 lo/hi meshes without checking their existing `material_index` was built against the same order; a reorder
   would silently swap materials on a multi-slot ORN prototype. Fix: assert the slot names match before clearing.
9. **Cosmetic — carry.** bake_lib.py:245 `is_data=img.is_float and True` is always True (meant `img.is_data`; line 246
   reassigns); manifest_v3.py:106 `if kind == "ao"` is dead; :140's `etc1s_encoder` string omits `--assign_oetf`.
10. **Scope — carry.** Five `renders/logs/gate2_*.log` sit outside the brief's `export/*`. And the backdrop textures stay
    unusable until `env.glb` is re-exported with `backdrop_uv1.npz` — a hard dependency on export before Gate 3.
