# Phase 8a item 3 — the shrub / reed cards at stations 3 and 5 (export, 2026-09-19). CPU only: no Blender, no Chrome.

Probe: `python3 export/p8e_leaf_probe.py --shrubs` (the 8e method: the card's own wrapped UV window box-averaged to its
drawing-buffer samples = the mip the GPU picks, cut at the material's `alphaCutoff`, then **run width p90** / thickness
p90 / coverage). Geometry from `export/out/gate1/{env,env_shrubs}.gltf` + `out/gate3/instance_rows{,_shrub_lod1}.json`;
px/m from `scripts/qa_cameras.py` lenses on a 36 mm sensor at 1920x1080 (cam03 18 mm = 960/d, cam05 35 mm = 1866.6/d).

## 1. Which file carries what
| set | file | tier | bytes | materials | card W x H (placed) |
|---|---|---|---|---|---|
| **LOD2 cards** (drawn beyond `shrubLod` 25-30 m — *this is the defect*) | `env.glb` -> `gate5/groups/env_t0.glb` **and** `env_t2.glb` (+ mobile twins) | **0** and 2 | 2 172 384 / 6 787 864 | all four in t0 | shrub 0.37x0.49, light 0.37x0.51, dry 0.10x0.46, reeds 0.06x0.25 |
| **LOD1 walk-in** (within 25 m) | `env_shrubs.glb` | 2, lazy | 668 352 | all four | shrub 0.18x0.24, light 0.19x0.25, dry 0.11x0.26, reeds 0.03x0.25 |

**The LOD2 card is exactly 2x the LOD1 card** at the same texture — that IS the magnification the relight tiles saw.
Every shrub/reed card samples the **whole** texture (u 0-1, v 0-1), unlike the trees' centred strip. Textures:
`leaves_shrub.png` (1024 px, ~1400 painted leaves, L 38-70 px = 3.7-6.8 % of the card = **1.6-3.1 cm** on a 0.46 m card)
and `reeds.png`; cutoffs 0.50 everywhere; samplers **CLAMP (33071)** in both files today.

## 2. What is on screen (run width p90 / thickness p90 / coverage, capture px)
Distances are measured, not assumed: the LOD2 rows run 15-216 m from cam03/cam05 (p5 15-48 m, p50 112-141 m), and the
`shrubLod` switch at 25 m is the nearest a LOD2 card is ever drawn.

| case | card px | k=1 (shipped) | k=2 | k=3 | k=4 |
|---|---|---|---|---|---|
| shrub, cam05 25 m | 28x36 | **21.7 / 9.4 / 0.55** | 16.9 / 10.3 / 1.08x | 11.2 / 8.4 / 1.05x | 8.4 / 5.6 / 1.07x |
| shrub_light, cam05 25 m | 28x38 | **23.8 / 8.4 / 0.55** | 16.4 / 10.3 / 1.07x | 11.2 / 8.4 / 1.06x | 8.4 / 6.6 / 1.06x |
| shrub, cam05 54 m | 13x17 | 15.4 / 10.3 / 0.58 | 7.0 / 5.6 / 1.00x | 5.6 / 5.6 / 0.95x | 15.4 / 5.6 (alias) |
| shrub, cam03 25 m | 14x19 | 16.9 / 10.3 / 0.59 | 8.4 / 5.6 / 0.99x | 5.6 / 5.6 / 0.96x | 17.4 (alias) |
| shrub, cam03 54 m | 7x9 | 8.1 / 6.2 / 0.52 | 9.0 / 4.4 / 1.09x | 9.8 / 2.8 / 1.28x | 9.8 / 2.8 |
| dry, cam05 25 m | 7x35 | 9.8 / 8.4 / 0.59 | 9.0 / 5.6 / 1.01x | 9.8 / 8.4 / 1.15x | 9.8 / 8.1 |
| reeds, cam05 25 m | 5x19 | 4.5 / 5.6 / 0.23 | 2.8 / 2.8 / **0.82x** | 2.8 / 2.8 / **0.63x** | 4.8 / 2.8 / 0.63x |
| reeds, cam03 54 m | 1x4 | 1.4 / 2.8 / 0.17 | **0.0 / 0.0 / 0.00x** | 0.00x | 0.00x |
| LOD1 shrub, walk-in 3 m | 113x148 | 29.5 / 13.1 / 0.53 | 22.0 / 8.4 / 1.02x | 19.7 / 8.4 / 1.02x | 17.8 / 8.4 / 1.04x |

The shipped LOD2 `shrub` / `shrub_light` blobs are **17-24 px wide** at 25-54 m — the "20-40 px single leaves with black
gaps" of the tile finding, and the painted leaves inside them (1.6-3.1 cm = 0.6-2.3 px) are long gone to the mip.

## 3. The UV scale, and why it is cheaper here than on the trees
Because the window is already the whole texture, an isotropic k **repeats what the card already samples**: coverage is
neutral by construction (measured 0.95-1.09x, no trend) and **no cutoff solve is needed** — the 8e trade (widening u off
the cluster's dense core) does not exist here. Reeds are the exception: they are 1-5 px blades whose mask is already
sparse (coverage 0.17-0.23), and k>1 erodes them (0.82x at 25 m, **0.00x** at cam03 54 m — they vanish).

**Recommendation — `MAT_shrub` k = 2.0, `MAT_shrub_light` k = 2.0, `MAT_shrub_dry` k = 2.0, `MAT_reeds` k = 1.0 (leave),
LOD1 walk-in set unchanged at k = 1.0.** k = 2 halves the blob (21.7-23.8 -> 16.4-16.9 px at 25 m, 15.4 -> 7.0 px at
54 m) at neutral coverage, and it is the value that makes the **25 m LOD switch invisible**: the LOD2 tile becomes
0.215-0.255 m against the LOD1 card's 0.21-0.26 m, i.e. the two sets finally paint the same leaf size. k = 3-4 reads
better at 25 m but aliases at 54 m+ (coverage 1.28x, run width climbing back) where most rows live.

## 4. Cost, and the tier-0 delta
Not a one-file patch like 8e: the LOD2 cards live in `env.glb`, so the change rides the **ENV chain** (`export_set.py
--gate1` -> `gltf_gate1.py` -> `gltf_pack.sh --gate1` -> `manifest_v2/v4` -> `tiers.py` x3 -> `verify_glb --gate5`), which
rewrites every group glb including tier 0 — **it should ride with the 8d ENV re-export, not as a separate pass.**
* **Byte delta:** measured on `env_trees.glb`, widening the UV range cost **0.54 B per unique triangle** (69 176 B over
  126 997 tris at u x2 / v x3). The shrub cards are **7 684 unique triangles** in `env.gltf`, so the whole ENV set moves
  by **~4 kB**, part of it in `env_t0.glb`. First frame on the wire is 49 393 776 B against the 50 000 000 rule:
  **606 224 B of headroom, and this spends under 1 % of it.** Even a 10x worse estimate fits.
* **Samplers:** both files ship CLAMP, so k > 1 needs REPEAT. Patch it in **both** `env.gltf` and `env_shrubs.gltf` (the
  8e pattern: clone a sampler shared with a non-foliage texture, assert no other texture moved). Because every root that
  uses `MAT_shrub*` would then agree, the shared-texture wrap race that 8e had (`applyFoliageAlbedo` re-wraps one shared
  texture, and three r186 only applies sampler state on upload) **cannot arise** — no viewer change is needed for this one.
* **Re-running `tiers.py` also re-measures the `web/dist` boot overhead** (see the Phase 8e note): expect that drift in
  the manifests, and take it deliberately with the rest of the chain.
