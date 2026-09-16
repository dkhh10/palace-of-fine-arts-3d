# phase6-bake @ 08901f1 — Gate 3 lightmap / slot atlas / impostor / probe bake — MERGE WITH FIXES (14 findings: 5 fix now, 9 carry)

Reproduced from the records: 65 jobs (16 own + 2 own_gate1uv2 + 27 slot + 2 vertex + 16 impostor + probe + sky),
65 records, 0 non-zero rc, queue wall **23 495.0 s** = 6 h 32 m, per class own 9 651 / slot 12 758 / impostor 787 /
probe 141 / vertex 86 / own_gate1uv2 69 / sky 3 s — all correct. Correct too: 7 UV2 re-lays and every cm/texel pair
in README §1 (riprap 32.61→4.62, podium 55.07→12.87, ochre 68.70→17.39, north 37.50→10.64, south 38.17→10.95,
rib 18.11→5.15, walk 5.91→2.49); `lightmap_uv2.npz` holds exactly those 7 as float32 `(n_loops, 2)` keyed by the
Gate 1 EXPM mesh name, written from the same layout the bake used (the `UV2_gate1` copy is taken *before*
`smart_project`, gate3_set.py:158-176, so the two `lmg1_*` diagnostics really are the frozen layout); 33 EXPHI
asserted `hide_render` both at set time and again per job (bake_lm.py:51); 129 occluders appended (127 `source_tree`
+ water + bay, 0 missing) and 127 `ENV_treeboard_*` hidden; `MAT_ornament_concrete` relinked onto 33 EXPM_ORN_
meshes; the slot job item set is bit-identical to `orn_slots` (988 instances, 436 orn + 552 arch_inst, 5 atlases,
256/180/256/256/40, 0 blank) and the packing `divmod(slot, 16)` → `(row*256+4, col*256+4)` matches
`gate1_common.slot_uv`'s offset `4/4096` and scale `248/4096 = 0.060546875` exactly, with compose's own read-back
`slot_check` 0.060–0.198 abs; encode.json's 23 maps give gamma2 0.028–0.163 stops and rgbm8 0.009–0.058 stops as
claimed, every `range` = the map's own max; probe z = 2·(−1.3) − 1.3 = **−3.9** from the manifest's own hero station
and water_z, `position_gltf = (x, z, −y)`, face means 0.38–4.66, cube-face basis (zax = −forward, xax = up × zax)
verified correct for the three.js face/up convention; sky diffuse upper/lower 5.736/0.060. Residency recomputes
exactly: own 101.28 + atlases 106.65 + impostors 32.00 + probe 8.00 + sky 2.67 = **250.60**, carried 804.57 →
**1 055.17**, measured basis 953.5 + 250.60 = **1 204.10**. Gate 2 finding 1 is genuinely fixed and inherited by
`--gate3`: `blender_run.sh:18` writes `BLENDER_RUN_OWNER` as field 3 and `gpu_free` exempts only `RUNNER_TAG`
(bake_queue.sh:90-106); status.json is copied to MAIN from both `write_status` and `record_job`. Nothing writes
`master*.blend` (`save_copy` refuses, gate0_common.py:142); no tracked binary added; the only absolute paths are the
three `PFA_MAIN_ROOT` defaults; `sync_main.sh` has no `--delete` anywhere and ships neither blends nor EXRs.
Gate 2's carries 4, 5, 6, 8, 9, 10 live in files this diff does not touch and are untouched; carry 7 is satisfied
for Gate 3 (every job kind calls `apply_final_cycles_checked` through `prepare()`, bake_lm.py:43).

1. **export/bake_lm.py:342 + manifest_v4.py:156,185-186 — fix now.** `centre_above_base_m = centre.z − bbox_min.z`
   is measured from the **bbox bottom**, but `impostors.placement` tells the viewer to add it to `trunk_base`, and
   `s = height_m / bbox_m[2]` divides by a height that includes below-ground geometry. 14 of the 16 prototypes have
   `bbox_min.z = 0.00` so this is invisible — but `ENV_tree_willow_s37_LOD1` is −2.67 m and `ENV_tree_willow_s11_LOD1`
   −0.72 m, so every willow impostor comes out ~19 % / ~6 % too small **and** 2.67·s / 0.72·s too high. Fix: record
   `base_z_m = bbox_min.z` per prototype and define the contract against the prototype's own z = 0 —
   `s = height_m / (bbox_max.z − max(bbox_min.z, 0))`, centre offset `(centre.z − 0)·s`.
2. **export/manifest_v4.py:171 — fix now.** `normal_depth ... a = depth / depth_range_m` is not what
   bake_lm.py:295 writes: `a = (z − (dist − radius)) / (2·radius)` with `dist = 6·radius`, i.e. a = 0.5 is the
   billboard centre and `dist` is never exported, so the viewer cannot recover a depth from the stated formula.
   Fix: state `depth_from_centre_m = (a − 0.5) · depth_range_m` (and the same in README:937).
3. **export/README.md:913 vs gate3_compose.py:108-114 — fix now.** The v4 section promises the export engineer
   "`float32 (n_verts, 3) per MESH name, scene-linear irradiance/pi`"; the file on disk is **uint8**, gamma-2
   encoded at range 64.0 (verified: `EXPM_ENV_tree_broadleaf_s19_LOD1_thin (17996, 3) uint8, 0..22`). The manifest
   block carries `encode`/`range` so it is decodable, but the document the export engineer was told to read first
   is wrong by a square. Fix: say uint8 + `rgb = (t/255)² · range`, and add the same decode line to
   `lightmaps.vertex_irradiance`.
4. **export/gate3_compose.py:105 — fix now.** One gamma-2 `range` (64.0) is shared by all 14 near-tree meshes and
   is set by the brightest (max 43.3). Measured consequence in compose.json's own rows: roundtrip `rel_p99` 0.244
   (cypress_s41), 0.239 (pine_s29), 0.226 (cypress_s3), while `broadleaf_s19` (max 0.469) uses 22 of 255 codes.
   The manifest already carries a per-mesh `max`. Fix: per-mesh range in the npz and in
   `vertex_irradiance.meshes[*].range`. CPU-only re-run of compose + manifest_v4, no GPU, and nothing has consumed
   the npz yet.
5. **export/manifest_v4.py:151,153 vs gate3_pack.sh:44 — fix now.** The impostor normal+depth atlas is declared
   `encode: "rgba8_unorm"` while the packer encodes it `--encode uastc` (ASTC 4×4) — and `gate3_common.resident_mb:317`
   only treats `rgbm8`/`rgba8` as uncompressed, so the 32.00 MB impostor line silently (and correctly for the file,
   wrongly for the label) counts it at 1 B/texel. `textures.gate3.encoders.impostor` in the same block says UASTC.
   Fix: label it `uastc_astc4x4`; and decide explicitly whether a map whose A channel is depth should be block
   compressed at all (lossless `--zcmp` is +3 MB per prototype at 1K).
6. **export/gate3_encode.py:32 + gate3_common.py:142 — carry.** "0 clipped texels on every map" (README:1059) is a
   tautology: `rng = max(a)` and `clipped = (lum > rng).sum()`, so the count cannot be non-zero in either pass
   (the first pass's power-of-two ceiling is also ≥ max). Fix: drop the claim, or report clipping against the
   *shipped* range when it is ever chosen below the max.
7. **export/bake_lm.py:321 — carry.** `clipped_body` is computed and never written into `rec`, and
   `gate3_report.py` computes neither it nor a code mean — so README:1067's "code means 61–97 of 255, with 3–235
   saturated texels per atlas (0.002–0.18 %)" is the one clip number that *is* meaningful and it is not reproducible
   from the records, against the section's own opening line ("every number below is `gate3_report.py`, printed from
   the records"). Fix: `rec["clipped_body"] = clipped_body` plus the encoded mean, and print both in the report.
8. **export/bake_lm.py:302-310 — carry.** `reduce2` premultiplies RGB by channel 3 before the 2×2 box filter,
   which is right for the albedo atlas (alpha = coverage) and wrong for the normal atlas, where channel 3 is
   **depth**: the shipped 1K normal atlas is a depth-weighted average of normals, and any 2×2 block whose mean
   depth is ≤ 1e-4 is written as (0,0,0) → decoded (−1,−1,−1). Harmless while the impostor is drawn unlit
   (manifest `unlit`), a defect the moment the viewer uses the normal. Fix: plain box filter for `nrm`,
   re-normalise after.
9. **export/bake_lib.py:48 + gate3_set.py:169 — carry.** Both make UV2 the *active render* UV. The bake target
   already has an explicit `BAKE_TARGET_UV` node wired to its Vector input, so `active_render` is not needed for
   the target; its only effect is that the baked object's own material samples any image texture that relies on
   the default UV with the lightmap layout during the colour-off pass — a bounce-tint error on the 16 own-map
   assets, unmeasured. Fix: restore UV1 as `active_render` after `attach_target`.
10. **export/bake_queue.sh:63,66 — carry.** `old.setdefault("started", ...)` is never reset, so status.json's
    `started` (17:21:26) belongs to an earlier run while the first Gate 3 record is 22:28:44 — the queue's own
    elapsed time cannot be read from the file; and `PFA_QUEUE_OWNER` still defaults to `"phase6-export/bake_queue"`
    with no gate3 value (it was right here only because the agent exported it). Related: `record_job` replaces a
    job by id, so the 787 s impostor pass is **already inside** the 23 495 s, and README:1012's "plus a 764 s
    re-bake" double counts it. Fix: reset `started`/`jobs` when `run` begins, default the owner from `$GATE`,
    and say "23 495 s including the impostor re-bake".
11. **docs/tech_notes.md — carry (brief item not done).** The branch does not touch it. The two new Blender 5.2
    findings the pipeline depends on exist only as comments at bake_lm.py:216-218 (`OPEN_EXR_MULTILAYER` is only
    offered once `media_type = "MULTI_LAYER_IMAGE"`; without `use_exr_interleave = True` 5.2 writes a **multi-part**
    EXR that gate3_common's reader asserts against at :328) and are in no README section either. The "two
    Eevee-only rigs" section (tech_notes.md:105-126) still omits `LIGHT_gallery_fill` — 16 strips, 1 200 W in
    Cycles, 0 W + `hide_render` in Eevee — which is a third engine-conditional rig and is inside every map this
    gate baked (`rig.lights = 20`). Fix: one tech_notes entry for each.
12. **export/README.md:937,944,995,1013(v4 block) — carry.** The README v4 schema, which the export and viewer
    engineers are told to read first, disagrees with the manifest the writer actually emits, in the viewer's
    favour only by luck: `"albedo": "srgb + alpha"` (it is gamma-2 at the prototype's own range — manifest_v4.py:170
    says so correctly), `encoders.impostor_albedo ... --assign_oetf srgb` (gate3_pack.sh:44 uses **linear**, and
    `add_tex` declares `colorspace: "linear"`), `trunk_base_offset_m` and `tris` (never emitted), vertex
    `range: 16.0` (it is 64.0), `range: 64.0` presented as the norm (it is per map, 0.72–52.8). Fix: regenerate
    the v4 section from a real manifest entry, or mark it illustrative and point at the file.
13. **export/manifest_v4.py:231,250-253 — carry.** `gate3_lightmaps_own` excludes the two `lmg1_*` maps
    (10.66 MB resident) although the manifest instructs the viewer to ship exactly those two until the re-export —
    so the honest pre-re-export figure is 261.27 / 1 065.83, not 250.60 / 1 055.17. And README:1087's 2K-impostor
    lever "+50.3 MB" is neither the manifest's own `levers_not_applied` "+96.0 MB" (albedo *and* normal at 2K)
    nor the albedo-only resident delta (+48.0 MB); it looks like a byte figure quoted as residency. Fix: add a
    `gate3_lightmaps_gate1_layout` row and reconcile the lever to the manifest.
14. **export/bake_lm.py:407-410 — carry.** `sky.diffuse` — the map QA-12b-1 asked for, the **irradiance**
    environment — ships as 8-bit RGBE with a measured `hdr_rel_p99` of **0.2298**, against 0.0136–0.0261 on the six
    probe faces, because the equirect's 523.6 max sets the shared exponent for the dim channel of the same texel.
    PMREM integration averages much of that away, but a 23 % p99 channel error on the map that exists to fix an
    olive-green ambient is worth not accepting blind. The 32-bit EXR is on disk and already named in the manifest.
    Fix: ship `sky_diffuse_1024x512.exr` (2.3 MB) for the irradiance PMREM, or report the post-PMREM error.

Also noted, no finding: `gate3_encode.py`'s docstring still cites "max 64.7 ... encoded at range 128" for
`ARCH_rotunda_column_tan_inner_merged`, whose record says 29.085 at range 32 (the README §5 text is right);
the nursery row the impostors are baked in (x −600…−420, y ≈ −570, base z ≈ 0) sits wholly inside the 400 m
`GATE3_imp_lawn` at (−510, −570, 0), so every prototype does get the ground bounce the docstring claims; and eight
`renders/logs/g3_*.log` / `gate3_*.log` sit outside the brief's `export/*`, the same scope nit as Gate 2 finding 10.
