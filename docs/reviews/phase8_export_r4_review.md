# phase8d-export r4 (1aa1abc) — MERGE WITH FIXES

Review of `5424281..1aa1abc` (five commits, `1c44f3e` → `1aa1abc`) in
`.claude/worktrees/phase8d-export`. Read-only: no Blender, no Chrome. Verified by re-running CPU probes
(`export/p8e_leaf_probe.py`, `--shrubs`, `export/name_sweep.py`), by decoding the shipped glTF/JSON in MAIN
(`export/out/gate1`, `out/gate2`, `out/gate3`, `out/gate5`), and by `npm test` in the worktree's `web/`:
**green** (three r186, "all passed"). `git merge-tree main 1aa1abc`: **clean**. The merge base is `22f6f61`,
so the apparent deletions of the "8e merged" `docs/decisions.md` entry and the last `docs/status.md` line in
a two-dot diff are divergence artefacts — the branch touches neither file; only `docs/briefs/phase6_budget.md`
(regenerated) changes under `docs/`.

## Verified, re-measured here

1. **The pin record.** `export/out/gate1/p8d_pin.json` in MAIN holds **22** checks (not the README's 21), all
   `ok`. They are: uv1 groups 52, the full uv1 atlas-tile dict, uv1 coverage per group, coverage min 0.0876,
   uv2 meshes 66, lightmap slots (`orn` 436/2, `arch_inst` 552/3), lightmap assets 16, `uv_missing` 10/0,
   `meshes_not_single_material`, six `tree_rule` scalars (147 / 77 / 20 / 127 / 46 / 391 908), the far and near
   tree lists, ARCH 949 382, ORN 1 099 192, the ENV delta, and the two lawn-rename checks. The two tree lists
   are compared with Python `==` on a list of dicts, so **content AND order** are both pinned (the far list is
   the impostor-atlas key and the instance-row order) — the check name says so honestly. The ENV delta is the
   one check with an `expected`: `eq("placed_tris.ENV delta", da, da, expect=6900)` compares the computed
   delta to the literal 6 900, and `env_placed` records 894 974 → 901 874. `--glbs` hashes with **sha256**,
   not size: `arch.glb` 4 613 040, `orn.glb` 154 253 424, `ground.glb` 1 959 104 all `identical: true`.
2. **The shared module.** `export/foliage_uv.py` carries the shrub factors the r3 review asked for —
   `MAT_shrub` (2,2), `MAT_shrub_light` (2,2), `MAT_shrub_dry` **(1,2)**, `MAT_reeds` (1,1) — and the export
   log and `out/gate1/gltf_gate1.json` confirm what actually ran: shrub ku2/kv2 1 196 cards / 5 meshes,
   shrub_light ku2/kv2 1 822 / 11, shrub_dry **ku1/kv2** 284 / 5, reeds untouched (a (1,1) factor never enters
   `active`, so the mesh is not even opened). r3 finding 3 is closed: `UV_TILE_U` is now per species like
   `UV_TILE_V`, an unknown species falls to `UV_TILE_DEFAULT = (1,1)`, is counted in `untiled_species`, and is
   asserted (`known or (ku,kv) == (1.0,1.0)`). r3 finding 4 is closed properly (in code, not prose): `off`
   sets `u={} v={} v_offset=False wrap=False`, which collapses `UV_TILE` to False, so no tiling, no
   golden-ratio v offset, no REPEAT patch, no cutoff patch — and the `uv_range ⊂ [0,1]` assert then guards it.
3. **The far-tree path is byte-unchanged.** For the seven known species `iso_cut` still resolves to
   ku 2.0 / kv 3.0 with `v_offset` on and the same `V_OFFSET` constant, so the refactor is output-preserving:
   `export/out/gate1/env_trees.glb` is **3 768 500 B, mtime 19:48** (the 8e merge), and the pin's `--glbs`
   block reports it `identical: true` against MAIN. `env_trees.gltf` still carries MASK 0.27/0.21/0.10/0.12
   and sampler 1 = 10497.
4. **The sampler clone is exactly right, on disk.** `env.gltf` now has three samplers: 0 (no wrap), **1 =
   33071 CLAMP — still carrying the four `MAT_leaf_*` textures and `MAT_reeds`, untouched**, and a new **2 =
   10497 REPEAT** carrying textures 12-17, i.e. the six maps of `MAT_shrub`, `MAT_shrub_light`,
   `MAT_shrub_dry`. `env_shrubs.gltf` mirrors it (0 = CLAMP for reeds, new 1 = REPEAT for the three). Both
   `*_ktx2.gltf` variants carry the same samplers, so the pack inherits them. `patch_samplers` asserts, per
   texture outside the set, that both the sampler *index* and its *contents* are unchanged — the r3 finding 9
   predicate ("shared with any texture outside the tiled set", not "non-foliage") is what is implemented.
5. **The rows were re-dumped in the right order, and manifest_v4's asserts are satisfied.**
   `out/gate3/instance_rows.json` → `env.glb` **38 348 124**, `instance_rows_shrub_lod1.json` →
   `env_shrubs.glb` **668 388**, and both `instance_order*.json` carry the same `glb_bytes`, matching the
   files on disk (`manifest_v4.py:148` and `:263`). `gate5_instance_rows` / `instance_order_groups.json` share
   the 20:24 timestamp. `instance_rows_trees_far.json` still holds the phase6 2 014 340 — unasserted anywhere,
   as r3 already noted.
6. **Gate 2.** `out/bake_queue/status.json` records exactly **7** backdrop jobs, all `rc: 0`
   (building, forest, hill, **backdrop_lawn**, roof, roof_tile, skylight) at 20:17-20:18. `asphalt` is not a
   missing eighth job: the gate2 log shows `MAT_backdrop_asphalt` is 1 274 polygons *inside* the
   backdrop_lawn group, so it is baked there. Min/max per map are present and sane (albedo maxima 0.56-0.88,
   normals flat about 0.5/0.5/1.0, forest coverage 0.20 as a card set should be). The **stale purge is real**:
   no `ENVBD__lawn` anywhere in `out/gate2/bake/`, in `status.json`'s 22 job records, or in `tex_ktx2` (only
   `gate2_ENVBD__backdrop_lawn_{albedo,normal,roughness}.ktx2`), and `tex_ktx2` is back to the full **203**
   files in both MAIN and the worktree. **`backdrop_uv1_shipped.npz` is byte-identical (sha256) to
   `backdrop_uv1.npz`**; its ten arrays include `backdrop_forest` at **318 180** loops as claimed, and
   `manifest_v3`'s own cross-check reports 10/10 meshes matching at worst distinct-UV match 1.00000.
7. **The numbers reconcile with MAIN.** `out/gate5/groups/env_t0.glb` is **2 172 696 B** on disk;
   `manifest.json` `tiers.bytes["0"] = 48 270 284` (= 48 269 972 + **312**),
   `first_frame_on_wire_bytes = 49 394 896`, and the value the 50 000 000 rule is actually tested against,
   `first_frame_transfer_bytes = 49 358 446`, leaves **641 554 B** of headroom (the README quotes the more
   conservative 605 104 B, measured on the on-wire figure); `tier0_within_target: true`.
   `env_t2.glb` 6 956 512, `env.glb` 38 348 124, `env_shrubs.glb` 668 388. `verify_gate5_{desktop,mobile}.json`
   both `fail: []` with 2 540/2 540 assets; `export/name_sweep.py` re-run here: **PASS**, 127 exempt
   treeboards, 0 to explain.
8. **8a-3 coverage reproduces.** `p8e_leaf_probe.py --shrubs` prints the shipped factors as its own columns
   and gives, to the digit, the README's rows: cam05 25 m shrub **1.08x** (21.7 → 16.9 px), shrub_light
   **1.07x** (23.8 → 16.4), shrub_dry at ku1/kv2 **0.98x** (9.8 → 9.4), reeds 1.00x; 54 m 1.00 / 1.00 / 1.03 /
   1.00; cam03 25 m 0.99 / 0.99 / 1.05 / 1.00. `p8e_leaf_probe.py` with no arguments now prints a
   `SHIPPED 2.0,3.0` column with the per-material cutoffs 0.27 / 0.21 / 0.10 / 0.12 — r3 finding 1 closed.
9. **The tiling cannot leak into the bake or double-apply.** `gltf_gate1.py` never saves
   `gate1_set.blend`, so the UV scale lives only in the exported glTF; re-running the step is idempotent, and
   the Gate 2 bake blend keeps the untiled UVs (correct — the shrub cards are bake-free, "1K foliage cards as
   shipped").
10. **The lead's water.js fix restores exactly the pre-8d set.** Every backdrop mesh in `env.gltf` is
    single-material. `/MAT_EXP_ENVBD__MAT_backdrop_(?!lawn)/` excludes **7** — building, door_green, forest,
    hill, roof, roof_tile, skylight — and keeps `backdrop_lawn`, `bird_white`, `lamp_post`. Pre-8d the far
    ground was `MAT_EXP_ENVBD__MAT_lawn`, which the old `/MAT_EXP_ENVBD__MAT_backdrop_/` also did not match,
    so the excluded set is the same 7 before and after. Confirmed by matching both regexes against the
    material names read out of MAIN's `export/out/gate1/env.gltf`.

## Findings

1. **[Medium — the hazard 8a-3 just closed for the shrubs is still open for the leaves]**
   `export/gltf_gate1.py:493-497`. `env.gltf` ships `MAT_leaf_broadleaf/cypress/eucalyptus/pine` on sampler 1
   = **CLAMP** while `env_trees.gltf` ships the same four material names on a **REPEAT** sampler. That is
   precisely the condition the branch's own comment in `shrub_lod1.py` calls fatal: `foliageLazy.js:284-286`
   copies *this root's* glb sampler onto the ONE shared tinted albedo, so the **last root processed wins**,
   and `:296-302` only *warns* on the disagreement. Today env_trees.glb is the lazily-loaded root and wins, so
   the far trees keep REPEAT; but the leaf UVs in `env_trees` run **-2..2**, so if load order ever changes
   (mobile plan, a tier move, an eager env_trees) the far crowns clamp and smear. *Fix (one line, and it
   changes no shipped byte in env_trees):* add the `MAT_leaf_*` names to the `env.gltf` patch list —
   `patch_samplers` already clones a shared sampler, and env.gltf's own leaf UVs are inside 0-1, so REPEAT is
   a no-op there. Until then, QA should read the boot log's `albedoWrap` line and confirm no
   "sampler … disagrees" note fires.
2. **[Medium — trap 1 is documented, not fixed; it will fire again and next time silently]**
   `export/gate2_common.py:37-38`. `GATE1_BLEND_DIR` still defaults to
   `<MAIN>/.claude/worktrees/phase6-export/export/out/gate1`. This round it failed loudly only because the
   lawn mesh had been renamed (`KeyError: EXPM_ENV_backdropgroup_backdrop_lawn`, `8d_gate2_set.log`); a
   geometry-only change with no rename would have baked another branch's geometry without a word. The README
   chain's `export PFA_GATE1_BLEND_DIR=…` is a human step. *Fix:* default to the local
   `ROOT/export/out/gate1` when it exists (local-then-MAIN, exactly the pattern this branch adopted for the
   npz), or assert that the blend's recorded source root matches `ROOT`.
3. **[Medium — trap 3 is documented, not fixed, and the manual repair is easy to forget]**
   `export/gltf_pack.sh:22` (`--gate2`: `rm -rf "$KTX" "$ETC"`). In a worktree with a partial `out/gate2/tex`,
   this leaves `tex_ktx2` holding only the maps just encoded (36 of 203) and `manifest_v3` is then written
   against a partial texture set — which is what the committed `8d_manifest_v3.log` shows (181 textures,
   backdrop ktx2 8 778 774 B). The chain was repaired by hand with `rsync --ignore-existing`, and MAIN is
   correct now (203 files, manifest 1 752 834 B at 20:27 carrying `lightmap_encoding`). *Fix:* remove only the
   `.ktx2` files whose source PNG is present in `$TEXIN` (or encode into a temp dir and move), so the step is
   safe from any worktree.
4. **[Medium-Low — the only committed evidence of the `manifest_v3` step is an aborted run, and the abort was
   silent]** `renders/logs/8d_manifest_v3.log` ends in `KeyError: 'lightmap_encoding'` at
   `manifest_v3.py:338` — *after* `manifest.json` had already been written (`mp.write_text` is at :329, the
   carry asserts at :338-339), so a partial manifest was left on disk, and because the script runs under
   `blender --background --python`, the watchdog logged `rc=0`. The final artefacts are right (MAIN's
   `out/gate2/manifest.json` and `out/gate3/manifest.json` both carry `lightmap_encoding` and
   `textures.schema`, both 20:27), so this is evidence hygiene, not a shipped defect. *Fix:* commit the log of
   the successful re-run, and note in the README that these post-write asserts do not fail the process —
   `--python-exit-code 1` on that invocation would make the chain stop where it thinks it stops.
5. **[Low — the pin record on disk no longer describes what shipped, and it is not committed]**
   `p8d_pin.json`'s `glbs` block says `env_shrubs.glb` 668 352, `identical: true`, because `--glbs` runs
   *before* `shrub_lod1.py` in the chain; the shipped file is 668 388 (the REPEAT sampler patch), as the
   README states. Also: `out/` is gitignored, so the pin record is not in history and `p8d_pin.py` is not
   re-runnable after `sync_main.sh` (it diffs against MAIN's `export_set.json`, which sync overwrote).
   *Fix:* either re-run `--glbs` at the end of the chain, or add one line to the README saying the block is a
   mid-chain snapshot; and copy `p8d_pin.json` into `docs/` (or the log) so the gate's evidence survives.
6. **[Low — README nits that a reader will check]** (a) "21 checks" — the record holds **22**. (b) "7 jobs,
   52.7 s" — the queue's per-job walls sum to **70 s** (9+8+7+9+8+10+19). (c) "the three tiled materials land
   in **0.98-1.08x**" omits the fourth LOD2 case the probe prints: cam03 at 54 m gives shrub **1.09x**,
   shrub_light **1.09x**, shrub_dry **0.94x**, so the honest band is **0.94-1.09x** — still inside the brief's
   0.95-1.09 expectation to within the probe's own quantisation, but it should be the stated range, and the
   0.94 named.
7. **[Low — a reporting overlap in the new module]** `foliage_uv.leaf_uv_range(doc, path, prefix=m)` is called
   with a full material *name* used as a `startswith` prefix, so `uv_range["MAT_shrub"]` is the union of
   `MAT_shrub` + `MAT_shrub_light` + `MAT_shrub_dry` (15 116 verts = 5 084 + 7 948 + 2 084). The numbers are
   correct for what they measure; the key is misleading. (The apparent -1.49 minimum on `MAT_shrub_dry`, whose
   ku is 1.0, is not a bug — glTF writes `v_gltf = 1 - v_blender`, so its v range 2.4193 maps to -1.4193.)
   *Fix:* exact-name matching, or name the key `MAT_shrub*`.
8. **[Low — carried r3 doc items still half-done]** `export/README.md` "Phase 8e": line 2494's table header is
   still "iso k=2 + cutoff (`iso_cut`)" (the ku/kv only appear in the recommendation line 2517), and line 2519
   still reads "`kv25` is what shipped" — stale since the lead chose `iso_cut`. `p8e_leaf_probe.shrubs`'s
   docstring and its printed header still assert that an isotropic k is "coverage-neutral by construction",
   the claim `foliage_uv.py` now correctly contradicts (r3 finding 8). Prose only.
9. **[Low — a future-proofing note on the water fix]** `web/src/water.js:389` builds `name` by joining *all*
   of a mesh's material names, so the exclusion is "any slot matches". Every backdrop mesh is single-material
   today, so the fix is exact; but the lawn group carries five materials per polygon in the bake blend
   (`MAT_backdrop_hill/lawn/soil/backdrop_asphalt/gravel_path`), so if a future export ever preserves them the
   `backdrop_hill` name in the joined string would silently exclude the far ground again. *Fix (cheap):* test
   per material slot, or key the exclusion on the group/mesh name.
10. **[Low — Gate 2 "clipped" is vacuous for PBR maps]** Every backdrop map's `stats.clipped` is `null`: the
    clipped counter exists only on the lightmap / band paths (`bake_lightmap.py`, `gate3_common.py`), not on
    the Gate 2 albedo/rough/normal stats. The CLAUDE.md rule asks each bake round to report min/max/clipped,
    so either the stat should be added for these maps or the round should say it does not apply. Worth one
    look regardless: `backdrop_lawn` roughness runs -9.9e-05 to **1.0**, i.e. hard against both clamps.

## Verdict

**MERGE WITH FIXES.** No blocker. The pin is honest and stronger than the README claims (22 checks, sha256
not size, both tree lists order-sensitive); the far-tree asset is byte-identical to the 8e merge; the shrub
UV scale lands per material at the measured ratios with REPEAT samplers cloned in both roots and the tree
leaf cards' sampler provably untouched; the stale `ENVBD__lawn` bake and its maps are gone and
`backdrop_uv1_shipped.npz` is a byte-identical promotion of the layout that was baked against; the rows were
re-dumped so `manifest_v4`'s two `glb_bytes` asserts hold; tier 0 +312 B and the 49 394 896 B first frame
reconcile with MAIN's manifests with 641 554 B of headroom; `verify_glb --gate5`, `name_sweep` and `npm test`
are green; and the lead's one-line `water.js` fix restores exactly the pre-8d reflection set. Finding 1 is the
one I would take before the deploy (one line, no shipped byte moves). Findings 2-3 are the two traps left as
prose that will bite the next chain run and should become code. 4-10 are evidence and documentation.
