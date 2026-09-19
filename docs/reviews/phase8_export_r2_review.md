# phase8e-export r2 (26310cd) — MERGE WITH FIXES

Read-only review, no Blender, no Chrome. Branch base is **3b0adc8** (`git merge-base main 26310cd`), so
the real delta is 5 files (`git diff 3b0adc8..26310cd`): `export/trees_far.py`, `export/p8e_leaf_probe.py`,
`export/README.md` "Phase 8e", `docs/briefs/phase8e_analysis.md`, `renders/logs/8e_trees_far.log`. The doc
deletions visible in `93ed07a..26310cd` are only main having advanced since the base — the branch touches
no file the lead has written on main, so the merge cannot lose the "8e decision" / "8e built" entries.
`npm test` in the worktree's `web/`: **green** ("all passed", three r186). `python3 export/p8e_leaf_probe.py`
re-runs on CPU and reproduces its own printed table.

## Verified (re-measured here, not taken on trust)

- **(1) The lever is what the brief asked for.** `tile_card_uvs` (trees_far.py:372-412) scales UVs about
  each component's own UV centroid, `ku=1.0` / `kv=2.5` (willow 1.5), plus a golden-ratio v offset by
  component index; it is called between `thin_and_grow` and `join` (trees_far.py:536-543) and only when
  `SETS['far'].uv_tile` (walk-up explicitly `uv_tile=False`, trees_far.py:105-108). Leaf-only is asserted,
  not assumed (`len(c) <= 2 and all(f.material_index in leaf_slots)`), and the shipped report confirms it
  on all 16 prototypes: `components_skipped == 0` and `cards_tiled == reduction.cards_kept` for every one.
  No vertex is added, moved or removed: COLOR_0 attached from `vertex_ao.npz` at `topology_rev 2` with
  **no `color0_refused`**, `verify_glb.json` `trees_far` = 127 placements / 1 007 775 drawn tris /
  126 997 unique, `failures: []`. `vertex_ao.npz` itself is untouched (mtime Sep 17).
- **(2) The sampler patch is surgical.** `env_trees.gltf` now has sampler 1 = `wrapS/wrapT 10497` used by
  exactly textures 3,4,5,6,10,11,12,13 (the 8 leaf albedo/normal maps); sampler 0 (bark) unchanged and no
  clone was needed (`samplers_cloned: []`). `env_trees_ktx2.gltf` carries it through; the packed
  `env_trees.glb` omits `wrapS/wrapT` because REPEAT is the glTF default, which `GLTFLoader` reads as
  `RepeatWrapping`. **Tier 0 untouched**: `out/gate5/groups/{env_t0,m_env_t0,…}.glb` all still mtime 14:08
  against the 19:06 export run. `env.gltf` / `env_trees_lod1.gltf` still `33071`, as intended.
- **(3) The "other roots are inside 0-1" claim is true.** Decoded from the bins: `env.gltf` leaf
  TEXCOORD_0 u 0.0750-0.9250, v 0.0000-1.0000; `env_trees_lod1.gltf` identical; `env_trees.gltf` now
  -1.7498..1.7500 in v, which is exactly `1 - v` of the report's own -0.75..2.7498 (Blender's V flip) —
  the two records agree. So CLAMP stays a no-op everywhere it is left.
- **(5) Sync and idempotency.** All six gate1 files are md5-identical between the worktree and MAIN
  (`env_trees.{glb,gltf,bin}`, `env_trees_ktx2.gltf`, `trees_far.json`, `verify_glb.json`); every other
  gate1 artefact keeps its pre-run mtime. The script rebuilds from `master_delivery.blend` every run and
  patches a freshly written glTF, so a second run is a no-op on the inputs and byte-stable on the outputs
  (the offsets are deterministic in `components()` face order).
- **(7) The stale manifest is genuinely cosmetic.** `web/src/main.js:326` HEADs each file and uses the
  manifest `bytes` only as a fallback, so the 3 699 324 → 3 856 412 staleness affects the progress readout
  and nothing else. Reverting `tiers.py --no-pack` (it re-measures another agent's `web/dist` boot
  overhead) was the right call.

## Findings

1. **[Medium — the decisive measurement is not in the repo] `export/p8e_leaf_probe.py:215-245`.** The
   committed `cards()` models an **isotropic** k only (`blob(tex, uw, w/k, h/k)`) with a **fixed** u
   window, and its coverage column is invariant (0.43-0.61 at k = 1…3 — I re-ran it). The README table
   that overrode the lead-approved isotropic k = 2.0 (coverage 0.62-0.76x vs kv = 2.5's 0.96-1.00x)
   **cannot be produced by any committed code**. I reproduced it with a ~15-line variant (widen the u
   window to `uw*ku`, tile v `kv` times, downsample to the card's drawing-buffer px) and the numbers hold:
   coverage ratio iso k=2 **0.63-0.76**, kv=2.5 **0.93-1.05**, blade p90 11-14 px / max 14-20 px. So the
   decision is sound — but the project rule is that the claim carries its check, and willow actually
   measures 0.93x, outside the stated "0.96-1.00x". *Fix:* give `cards()` an anisotropic mode
   (`factors=((1,1),(2,2),(1,2.5),(1,3))`, u window `uw*ku`) and quote its committed output in the README;
   correct the willow figure. No re-export needed.
2. **[Medium — the fix may not address the defect QA named] `export/trees_far.py:133-147`.** A v-only
   tiling shrinks the *thickness* the probe's erosion metric reports, not the blade's *width*. Same model,
   horizontal p90 run width at 40 m, shipped → kv = 2.5: broadleaf 35.3 → **36.5** px, cypress 26.7 →
   **26.7**, eucalyptus 30.3 → **30.9**, pine 22.5 → **22.5** (isotropic k = 2 halves it: 35.3 → 16.9,
   26.7 → 18.3). QA 19 said "~40 px **wide** … blades". The change squashes each blade to 1/2.5 of its
   height — leaves become horizontal dashes at the same width — so the metric improves while the named
   defect may not. Not a merge blocker (no regression is proven, coverage holds, and it is cheap to judge)
   but: *fix:* the lead scores the mobile orbit capture on blade **width**, and the README/decisions record
   that what moved is thickness. If QA still reads them wide, the coverage-preserving alternative is
   isotropic k with a lower leaf `alphaCutoff` — the script already writes it (trees_far.py:783) —
   measured here: broadleaf k=2 at cutoff 0.50→0.25 gives coverage 0.94x at run-width 18.3 px; cypress
   0.45→0.23 gives 0.97x at 23.9 px.
3. **[Medium — deploy gate, not this branch's file] `web/src/foliageLazy.js:267` (main).** `t.wrapS =
   old.wrapS; t.wrapT = old.wrapT` on the tinted albedo without `t.needsUpdate = true`. In three r186
   sampler parameters are applied only inside `uploadTexture`, so this REPEAT never reaches an albedo the
   eager roots already uploaded — and on mobile `env_t0`/`env_t2` carry `MAT_leaf_cypress` and
   `MAT_leaf_eucalyptus`. Those two species would then clamp and smear the edge texel across every tile:
   **worse than today**. The branch flags it (README "ONE VIEWER LINE IS STILL NEEDED"); it is not on main.
   *Fix:* merge this branch, but do not deploy or capture the mobile orbit until that one line lands on
   `phase8a-viewer`.
4. **[Low — standing check] `export/trees_far.py:792` / README.** The "every other root's leaf UVs are
   inside 0-1" claim is prose; I had to decode the bins to confirm it. *Fix:* in the `uv_tile=False`
   branch assert leaf `TEXCOORD_0` ⊂ [0,1] after the export, so a future drift is caught by the export
   rather than by a smeared viewer.
5. **[Low — next chain] `export/trees_far.py:541` `UV_TILE_V[species_of(p)]`.** A species not in the dict
   raises a bare `KeyError` and kills the gate-1 export. 8d adds LOD2 backdrop trees; if any new
   `ENV_tree_*` species reaches this set the failure is an opaque traceback. *Fix:* `.get(sp)` with an
   explicit assert naming the species and this file (or default 1.0 plus a report line).
6. **[Low — QA scope] mobile draws this block at every distance.** `device.js` has `walkupMesh: '0'`, so
   `env_trees.glb` is what a walker sees at 2 m as well as at 40 m; kv = 2.5 stacks 2.5 copies of the
   cluster inside one 0.5-0.9 m card and the 12-bit UV step is now ~0.87 texels. The analysis judges
   37-45 m only. *Fix:* include one mobile walk-up frame under a far tree in the QA capture, not only the
   orbit.

## Verdict

**MERGE WITH FIXES.** The shipped asset is correct and verified: leaf-only, card-centred, far-set-only,
vertical-only, deterministic, no topology or instance-row change, tier 0 byte-identical, MAIN in sync, and
the numbers in the README reconcile with an independent re-measurement. Findings 1, 4 and 5 are
documentation/check work that changes no shipped byte and can land on the branch or as a follow-up commit;
finding 3 gates the deploy; findings 2 and 6 are instructions for the QA round that judges this change.
