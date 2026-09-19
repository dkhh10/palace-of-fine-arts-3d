# phase8e-export r3 (24eb45e) — MERGE WITH FIXES

Delta review of `26310cd..24eb45e` (three commits: `911af2d` review fixes + iso_cut prepared, `7b59637`
iso_cut exported, `24eb45e` the 8a-3 shrub analysis). Read-only, no Blender, no Chrome. Files touched:
`export/trees_far.py`, `export/p8e_leaf_probe.py`, `export/README.md` "Phase 8e",
`docs/briefs/phase8a3_shrub_cards_analysis.md`, `renders/logs/8e_trees_far_isocut.log`. `npm test` in the
worktree's `web/`: **green** (three r186, "all passed"); worktree clean after my runs.
`python3 export/p8e_leaf_probe.py` and `--shrubs` both run on CPU in ~5 s and 30 s.

## Verified (re-measured here, not taken on trust)

- **The iso_cut write reaches exactly the intended materials.** `export/out/gate1/env_trees.gltf`,
  `env_trees_ktx2.gltf` and the packed `env_trees.glb` all carry `MAT_leaf_broadleaf` MASK **0.27**,
  `MAT_leaf_cypress` **0.21**, `MAT_leaf_eucalyptus` **0.10**, `MAT_leaf_pine` **0.12**, and sampler 1 =
  `wrapS/wrapT 10497` (the packed glb drops the keys because REPEAT is the glTF default — `GLTFLoader`
  reads that as `RepeatWrapping`). **Not** touched: `env.gltf` (0.50 / 0.45 / 0.50 / 0.42, sampler 1 =
  33071) and `env_trees_lod1.gltf/.glb` (same cuts, CLAMP). `out/gate5/groups/{env_t0,env_t2,m_env_t0,
  m_env_t2,…}.glb` all still mtime 14:08-14:09 against the 19:48 export — **tier 0 byte-untouched**.
- **The patch ordering is safe.** `cutoff_patch` runs *after* the `read_alpha.cut_chain` pass that sets
  `alphaMode = MASK`, so its `assert alphaMode == "MASK"` cannot misfire; `len(cutoff_patch) ==
  len(LEAF_CUTOFF)` catches a material rename; the whole override is gated on `UV_TILE and LEAF_CUTOFF`,
  so the walk-up export keeps the Phase 5 cuts. No viewer code overrides `alphaTest` for leaf materials
  (`web/src/foliage.js:862` only enables `alphaToCoverage`), so the exported cutoff is what draws.
- **The README numbers reconcile with the committed json and the files on disk.** `env_trees.glb`
  **3 768 500 B** (= +69 176 over the pre-8e 3 699 324, **+1.87 %**, and 87 912 B *less* than kv25's
  3 856 412); `gltf.leaf_uv_range` `{min: -1.9998, max: 2.0, verts: 167876}` (README "-2..2");
  `wrap_patch.samplers_patched` **[1]**, `samplers_cloned []`, `leaf_textures [3,4,5,6,10,11,12,13]`,
  `samplers_total 2`; `species_not_tiled {}`; `mode "iso_cut"`, `u 2.0`, `v 3.0` for all seven species.
  `KHR_texture_transform` baseColour v scale **64.011879** with 16-bit normalised TEXCOORD accessors
  (VEC2/5123/normalized), so the quantisation step is 64.011/65535 ≈ **1.0 texel** of 1024 — as claimed.
- **MAIN is in sync and the deploy staging already carries it.** md5 of `env_trees.{glb,gltf,bin}` and
  `env_trees_ktx2.gltf` identical between the worktree and MAIN; `web/deploy_out/assets/gate1/env_trees.glb`
  is the same inode at 3 768 500 B.
- **The shipped configuration measures what the README says.** Driving the probe's own API at ku 2 / kv 3
  with the per-material cutoffs (run width p90 / thickness p90 / coverage ratio, 40 m, capture px):
  broadleaf 18.4 / 8.4 / **0.92**, cypress 23.9 / 14.0 / 0.99, cypress_column 21.1 / 12.2 / 1.00,
  eucalyptus 25.3 / 14.0 / 0.99, pine 22.5 / 12.2 / 1.03, redwood 19.7 / 10.3 / 0.97, willow 12.6 / 11.2 /
  1.07 — the README table to the digit (its 0.93 for the broadleaf is 0.92 here). At the 2.5 m walk-up:
  **0.82-1.02x**, no fattening. The per-material solve is real: broadleaf+willow mean 0.995, cypress pair
  0.995, pine+redwood 1.00.
- **Fix 4 is in code.** `leaf_uv_range()` decodes `TEXCOORD_0` of every `MAT_leaf_*` primitive from the
  written glTF + .bin, reports it, and asserts ⊂ [0,1] on every non-tiled (walk-up/desktop) export.
- **r2 finding 3 is closed on main** — `web/src/foliageLazy.js` now sets `needsUpdate` when the copied wrap
  actually changed (and warns when two roots disagree), so the mobile deploy gate from r2 is lifted.
- **The 8d chain is not disturbed.** `env_trees` packs through `gltf_pack.sh --trees`, never `--gate1`, so an
  ENV re-export cannot clobber the patched file; no manifest assert references `env_trees.glb`'s size
  (`instance_rows_trees_far.json`'s `glb_bytes` is a phase6 2 014 340 and is not checked anywhere).
  `out/gate5/manifest.json` still advertises 3 699 324 for it — cosmetic (main.js:326 HEADs each file) and
  self-healing the next time `manifest_v*`/`tiers.py` run.
- **`--shrubs` reproduces its own doc.** Spot-checked rows (shrub cam03 25 m k=1 16.9/10.3/0.59, k=2
  8.4/5.6/0.99x; reeds cam03 54 m k=2 0.00x; LOD1 3 m 29.5/13.1/0.53) match the analysis table.

## Findings

1. **[Medium — r2 finding 1 is only half fixed] `export/p8e_leaf_probe.py:355-378`.** The probe did grow
   the anisotropic mode, `run_width` and `solve_cutoff` as asked, but its **defaults still do not print the
   shipped configuration**: `cards(factors=…, solve_for=((2,2),))` prints ku,kv = 2,2 with cutoffs solved
   **per species** — 0.16 / 0.20 / 0.20 / 0.08 / 0.14 / 0.10 / 0.48 — while the asset ships ku 2 / **kv 3**
   with cutoffs solved **per material** (0.27 / 0.21 / 0.10 / 0.12). So `python3 export/p8e_leaf_probe.py`
   still contradicts the README table a reader is told it produces. The numbers themselves are right (I
   reproduced the whole table with a ~10-line driver over the probe's own functions, above), so this is
   reproducibility, not a shipped defect. *Fix:* add `(2, 3)` to `factors`/`solve_for` and a per-material
   solve — best by importing `trees_far.UV_TILE_MODES[UV_TILE_MODE]` so the probe prints **the mode that
   ships**, which also makes the table self-updating for the next mode.
2. **[Medium — the name and the decision entry say something the asset is not] `export/trees_far.py:163-168`,
   `docs/decisions.md` "8e decision 2", README table header.** `iso_cut` is **not isotropic**: ku 2.0 over a
   0.85-wide u window and kv 3.0 over a full-height v window give 43.5 vs 65.4 texels per screen pixel
   (k = 1 is 21.8 / 21.8, i.e. the card is isotropic *before* the tiling and anisotropic after). The decision
   entry records "isotropic k = 2 with per-material alpha cutoffs" and the README column is headed "iso
   k=2 + cutoff"; the shipped mode is the (2, 3) variant, whose numbers are the ones both documents quote.
   *Fix:* the lead amends the decisions entry to (ku 2.0, kv 3.0); the README column header and the mode's
   docstring say ku/kv explicitly. Renaming the mode string is optional (it is now in `trees_far.json`).
3. **[Medium — the fix for r2 finding 5 does not hold under the default mode] `export/trees_far.py:174-177,
   600-604`.** `UV_TILE_V.get(sp, 1.0)` defaults only **kv**; `UV_TILE_U` is a single global, so an unknown
   species still gets **ku = 2.0** — a widened u window at the *unmodified* Phase 5 cutoff, which is exactly
   the 0.62-0.76x crown thinning this branch exists to avoid, plus leaf UVs outside 0-1 on an unlisted
   species. The code comment ("A species with no entry is NOT tiled (factor 1.0)") and the README bullet
   ("exported untiled and named") are therefore false for the shipped mode. The same gap applies to a fifth
   leaf material: `LEAF_CUTOFF` is keyed by name and an unlisted `MAT_leaf_*` keeps its Phase 5 cut under a
   widened u. With 8d adding backdrop/hall-belt trees this is the likeliest next trip. *Fix:* make u
   per-species like v (`UV_TILE_U.get(sp, 1.0)`), or assert `species_known` before applying `ku != 1`.
4. **[Low — the A/B baseline is not a baseline] `export/trees_far.py:169` + `tile_card_uvs:420-424`.**
   `PFA_UV_TILE_MODE=off` still calls `tile_card_uvs` with (1, 1), which **still applies the golden-ratio
   per-card v offset**, and `UV_TILE` is still true so the REPEAT sampler patch still runs. `off` is
   therefore a cyclically v-shifted, REPEAT-sampled variant, not the pre-8e asset the README implies
   ("`off` disables"). *Fix:* skip `tile_card_uvs` and the wrap/cutoff patches when the mode is `off`, or
   restate in the README what `off` actually produces.
5. **[Low — decode nits] `export/trees_far.py:400-420` `leaf_uv_range`.** Assumes float VEC2 TEXCOORDs
   (asserted, fine), reads `count * (stride // 4)` floats — which over-reads the tail by `stride - 8` bytes
   if a `byteStride > 8` ever appears — and ignores sparse accessors and a GLB-embedded buffer (`uri`-less
   buffers are skipped, so the count would silently drop to 0 and, in the non-tiled branch, the assert would
   fire on `None`). Loud rather than silent in every case, and Blender writes tightly packed .gltf+.bin
   today. *Fix (optional):* slice per element, or `assert bufs`, when someone next touches it.
6. **[Medium — the 8a-3 chain list is missing two steps] `docs/briefs/phase8a3_shrub_cards_analysis.md` §4.**
   Changing `env.glb` / `env_shrubs.glb` trips `export/manifest_v4.py:148` and `:263`
   (`glb.stat().st_size == order["glb_bytes"]`, pinned at 38 181 724 and 668 352). The listed chain
   (`export_set --gate1` → `gltf_gate1` → `gltf_pack --gate1` → `manifest_v2/v4` → `tiers.py` ×3 →
   `verify_glb --gate5`) will abort at `manifest_v4` unless `node web/tools/instance_rows.mjs` is re-run for
   **both** sets and `export/gate4_instance_order.py` (plain and `PFA_ORDER_SET=shrub_lod1`) re-joins, plus
   `export/gate5_instance_rows.py` for the per-group node maps. *Fix:* add those three to §4 before the 8d
   ENV re-export rides with it.
7. **[Medium — the k recommendation overshoots on one material] same doc, §1 and §3.** "The LOD2 card is
   exactly 2x the LOD1 card" holds for `MAT_shrub` (2.06 / 2.05) and `MAT_shrub_light` (2.00 / 2.00) only.
   From the doc's own `SHRUB_CARD` table, `MAT_shrub_dry` is **0.89x in width / 1.77x in height** and
   `MAT_reeds` 2.0x / 1.0x. An isotropic k = 2 on `shrub_dry` takes its LOD2 tile to 0.048 x 0.232 m against
   the LOD1 card's 0.107 x 0.262 m — half the LOD1 leaf width, the opposite of the "make the 25 m switch
   invisible" argument, which the quoted "0.215-0.255 m against 0.21-0.26 m" only checks in **height**.
   *Fix:* per-material factors from the measured LOD2/LOD1 ratio — `shrub` and `shrub_light` k = 2,
   `shrub_dry` ku 1 / kv 2, `reeds` 1.0 as recommended.
8. **[Low — an empirical result stated as a construction argument] same doc, §3.** Coverage is *not*
   neutral by construction: thresholding after a coarser box average is not invariant, and the doc's own
   reeds row (0.82x at 25 m, 0.00x at cam03 54 m) is the counterexample. Measured at the recommended k = 2
   it is 0.94-1.09x for the three shrub materials; the "0.95-1.09x, no trend" range is only true at k = 2
   (the same table runs 0.63-1.28x at k = 3-4). *Fix:* say "measured, at k = 2, for these three materials".
9. **[Low — the sampler claim is right, the clone rule needs sharpening] same doc, §4.** Verified: both
   files ship CLAMP today (`env.gltf` sampler 1 = 33071, used by all four shrub/reed textures **and** the
   four `MAT_leaf_*` textures and the rest of the env set; `env_shrubs.gltf` has a single sampler 0 = 33071)
   — so the doc's "samplers CLAMP in both, patch REPEAT into both" is correct, and the r2-style wrap race
   genuinely cannot arise once both roots agree: the tinted albedo inherits the source wrap
   (`foliageLazy.js:958`), the translucency map follows the albedo (`:937-946`), and the gated
   `needsUpdate` re-upload never triggers. One sharpening: in `env.gltf` the shared partner of sampler 1 is
   *foliage* (the LOD2 tree leaf textures), so the 8e clone predicate must be "shared with any texture
   outside the tiled **shrub** set", not "non-foliage", or the fix will silently flip the tree cards too.
10. **[Low — estimate, used safely] same doc, §4.** The ~4 kB tier-0 delta extrapolates 0.54 B/tri from a
    different widening (u x2 v x3 on trees vs u x2 v x2 on shrubs) and a different quantisation range. It is
    labelled an estimate with a 10x margin against 606 224 B of headroom, so it is fine as used — but the
    real number should be read off the rebuild, not carried forward as measured.
11. **[Low — for the QA round that judges this]** with MSAA on, `foliage.js:862` turns on
    `alphaToCoverage` for any `alphaTest > 0`, so the shipped silhouette is a soft ramp around a cut that
    8e just lowered to 0.10-0.27, not the probe's hard cut. The relative comparison (k = 1 vs iso_cut)
    holds, but the absolute on-screen run width may sit above the 18.4-25.3 px predicted. Judge the mobile
    orbit **and** one walk-up frame by eye, as r2 finding 6 asked.

## Verdict

**MERGE WITH FIXES.** No blocker. The shipped `env_trees.glb` is correct and independently verified: the
per-material cutoffs and REPEAT samplers land in this one glTF and its pack, `env.gltf` /
`env_trees_lod1.*` and every tier-0 group are untouched, MAIN and the deploy staging carry the same bytes,
the README's figures reconcile with the committed json and the files, and the shipped (ku 2, kv 3 + cut)
variant re-measures to the README's table at 40 m and 0.82-1.02x at the 2.5 m walk-up. Fixes 1-5 are
code/doc work on this branch that changes no shipped byte (3 is the one that matters before the 8d trees
touch this set); 6-10 are corrections to the 8a-3 analysis to apply before that work is briefed; 11 is an
instruction for the QA round.
