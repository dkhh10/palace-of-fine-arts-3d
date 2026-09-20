# 8c — cam03 column concrete: texel budget, measured. ANALYSIS ONLY, nothing changed.

Probe `export/p8_texel_probe.py` (CPU only, read-only: parses the pre-gltfpack `export/out/gate1/arch.gltf` + `.bin`, the Gate 2 bake sidecars, the Gate 5 manifest). Re-run: `python3 export/p8_texel_probe.py --radius 16`.
Crop pair `renders/qa_comparisons/p8c_texel_column_albedo_src_vs_ktx2.jpg` (100 %, 1 px = 1 texel = 13.0 mm of shaft).

## (a) What cam03 asks for vs what the atlas gives
cam03 = 18 mm on a 36 mm sensor at 1920x1080 → **960 px per metre at 1 m (1.04 mm per pixel)**.

| set within 16 m of cam03 | atlas | nearest | area | UV1 tri cov | texels/m | mm/texel | **ratio at 1 m** |
|---|---|---|---|---|---|---|---|
| `…colonnade_south__MAT_concrete_colonnade` (shaft + base, 4 meshes, 174 placements) | 2048 | **0.48 m** | 204 m² | 0.277 | **77** | **13.0** | **12.4 : 1** |
| `…colonnade_south__…__merged` (entablature / wall mass, 1 mesh) | 2048 | 11.7 m | 5 805 m² | 0.106 | **8.8** | **114** | 110 : 1 |
| `…colonnade_north__MAT_concrete_colonnade` | 2048 | 9.8 m | 205 m² | 0.277 | 75 | 13.3 | 12.5 : 1 |
| ORN capitals / maidens (for scale — these are fine) | 2048 | 9.9 m | 35 m² | ~0.35 | 200–395 | 2.5–5.0 | 2.4–4.8 : 1 |

The shaft's UV is **not** stretched: 81.9 tex/m vertical vs 73.8 horizontal, anisotropy 1.11. It is uniformly 12x too coarse.

## (b) Blur and banding are two different defects
1. **Blur = the baked atlas magnified 12.4x**: 13.0 mm/texel where the camera samples at 1.04 mm/px.
2. **Vertical banding = the detail layer's projection, not the bake.** `web/src/detail.js` defaults to `objxy` (`uv = (x, −z)/tile`); on a vertical shaft that gradient is ~zero along the vertical. Measured on the shaft: **15.2 texels/m vertical vs 948.1 horizontal — 62 : 1 (66 mm per texel vertically)**, i.e. every detail texel is a streak running the column's full 11.2 m. With `dominant` (already implemented, `?detailproj=dominant`) the same maps give **947 vs 853 tex/m, 1.11 : 1**.
3. **The UV pack compounds it and no bake resolution fixes it.** Welded by UV position the shaft has **89 islands, median 5.2 x 337 texels, 93 % narrower than 16 texels** — slivers with an 8 px gutter each side; the merged mass has **7 964 islands, median 0.7 x 2.1 texels** (sub-texel).
4. **KTX2 is not a cause.** Source PNG vs shipped UASTC level 0: mean |Δ| **0.35/255**, RMSE 0.78, Laplacian std 19.64 → 19.80; the crop pair is indistinguishable.
   *Committed 2026-09-20 (review r1 finding 4, which noted the only artefact behind these numbers was the crop jpg): `python3 export/p8c_ktx2_compare.py` is the measurement — `tools/bin/ktx` v4.4.2 `extract --transcode rgba8 --level 0` on the shipped file against the baked PNG, no resize, no colour conversion. It reproduces the claim on `gate2_ARCH_colonnade_south__concrete_colonnade_albedo` (2048², the map this section is about): **mean |Δ| 0.3473/255, RMSE 0.7766**, p99 3.0, max 24.0. Its Laplacian std reads **22.015 → 22.188 (1.0079x)** rather than 19.64 → 19.80 — the absolute value depends on the operator (this one is the 4-neighbour Laplacian of the luma over the interior, and the original was never written down), but the **ratio is the same to three decimals** (19.80 / 19.64 = 1.0081), which is the number the "blur" claim rests on. Conclusion unchanged and now reproducible.*

## (c) Options, costed (ASTC 4x4 = 1 B/texel, x4/3 mips: 2K = 5.59 MB, 1K = 1.40 MB, 4K = 22.37 MB)
| option | resident Δ | transfer / tier | bake wall | stations |
|---|---|---|---|---|
| **A. detail projection `objxy` → `dominant`** (CFG default in `web/src/main.js`; code already shipped) | **0** | 0, no tier change | **0** | all (ARCH concrete + ground) |
| B. 4K re-bake, two south sets only | **+75.5 MB** (12.58 → 50.33 per set) | ~+26 MB at **tier 2** (58 → 84 MB; tier 0 byte-unchanged) | ~12 min GPU + ~8 min toktx | 3, 5 |
| B′. same for all four colonnade sets | +151 MB | ~+52 MB, tier 2 | ~25 + ~16 min | 1, 2, 3, 5 |
| C. UV re-layout (cylindrical shaft unwrap + tighter pack) | 0 | 0, tier 1 re-issue | ~12 min bake **plus** gate1 re-export of arch.glb, gate3 relay, gate5 re-split | 1, 2, 3, 5 |
| D. higher-frequency detail map | — | — | — | **no gain**: already 1.05 mm/texel, finer than the camera |
| E. KTX2 quality change | — | — | — | **reject**: measured no-op |

B buys 77 → 154 tex/m (6.5 mm/texel) — still 6.2 : 1 at 1 m, on a texture budget already 175 MB over (docs/briefs/phase6_budget.md). C's coverage 0.277 → ~0.70 buys ~123 tex/m (8.1 mm/texel) and does nothing for the 5 805 m² merged mass (8.8 → ~18 tex/m at best).

## Recommendation
**A** — flip the detail projection default to `dominant`. It is the measured cause of the banding (62 : 1 → 1.1 : 1), it restores real per-metre grain at 1.05 mm/texel on the shaft, and costs no memory, no transfer, no tier and no bake. It touches every station, so it needs one QA capture round. Reserve: if `dominant`'s four plane-flips per round shaft read as seams, a triplanar blend in `detail.js` (~30 lines, still zero memory/bake). Only if the hero still reads flat after A: **B**, two south sets, tier 2, progressive. **Do not** spend the round on C or a blanket 4K re-bake. STOPPING for the lead's decision.
