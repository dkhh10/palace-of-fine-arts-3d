# Phase 8a — shrub / reed card density (ENV, branch `phase8-env`)

**Why LOD2 is in scope.** The web export ships the **LOD2** shrub mesh for all 1 379 placements — `export/gate1_set.py:741` *"# shrubs at LOD2, shared mesh per prototype"*, taking the placed `_LOD1` object only for its transform (all 28 shrub rows in `docs/briefs/phase6_budget.md` are `ENV_src_*_LOD2`). Every station, the hero's shore band at 80–160 m included, therefore draws LOD2, and a LOD1-only change would have reached only the Cycles renders and the Blender viewport. **Lead's decision, 2026-09-19:** apply the clump emitter at LOD2 (free) *and* the densification `card=3.30, cover=0.85, blade=0.24`; the resulting +102 k placed triangles break the Gate 1 ENV freeze of 800 k placed and the lead accepts the exception, logged, with the viewer measuring the frame cost after export.

**The change** (`scripts/env_build.py`). Cards are emitted as **clumps** (`_leaf_clump`: 4–9 cards, four leaf scales with mean square 1.0, shared dominant azimuth ± 0.85 rad, tilt spread ± 0.55) instead of an even scatter of one-size quads; blade clumps come in **tufts** of 4–8 sharing an origin and lean. Clumping now runs at **all three LODs**. The round-02 "k× wider, k²× fewer" rule is relaxed at LOD1 (`card 2.20 / cover 0.95 / blade 0.33` → **`1.65 / 1.00 / 0.75`**: leaf card 18.7 → **14.0 cm**, 1.87× the cards; reed blade 7.8 → **5.2 cm**, 2.3× the blades) and at LOD2 (`4.50 / 0.85 / 0.12` → **`3.30 / 0.85 / 0.24`**: leaf card 38.3 → **28.1 cm**, 1.86× the cards; reed blade 12.9 → **9.2 cm**, 2.0× the blades). LOD0's card count and card size are untouched, so its triangle total is unchanged and only the distribution moves. No material, name, placement or LOD-assignment change (1 379 placements, 25 sources × 3 LODs, `MAT_shrub{,_light,_dry}` / `MAT_reeds` untouched).

**Triangles, exact** (`scripts/env_build.py -- --shrub-stats`, and the same per-source table × the placement counts):

| | unique before → after | placed before → after |
|---|---|---|
| LOD0 | 79 814 → **79 814** (1.000×) | 2 425 986 → **2 425 986** (1.000×) |
| LOD1 | 17 094 → **31 268** (1.829×, brief cap 2× = 34 188) | 551 576 → **1 015 498** (1.841×) |
| LOD2 | 3 920 → **6 948** (1.772×) | 135 880 → **238 032** (1.752×, +102 152) |

ENV collection totals after the rebuild: LOD0 13 909 362 / LOD1 5 237 628 / LOD2 772 574. Largest leaf card 20 cm, unchanged.

**Evidence.** `renders/qa_comparisons/p8a_shrubs_lod2_hero_crop.png` — the hero shore band at **LOD2, 100 % of the cam01 Eevee preview**, before over after: the band goes from sparse angular slabs with stone showing between them to a continuous mass of smaller, varied, tufted foliage with a broken top edge. `p8a_shrubs_cam02.jpg` rows 4–6 show the same at LOD1 on the cam02 reed clump (four broad orange slabs → a tufted mass of small blades). `p8a_shrubs_cam0{1,2,3,5}.jpg` carry the QA-17 box crops before/after/reference and `p8a_shrubs_frames.jpg` the four whole frames.

**Numbers, per box** (`scripts/env_p8_boxes.py`, QA 16's own `box_stats`; ENV `--local --lod=1` Eevee previews, 1280×720, 16 spp). The reference column reproduces every QA-17 value exactly, which is the harness check; the *preview* columns cannot be compared to it (previews are upscaled to the 1920×1080 box space so `hard%` reads ~10× low, and env_preview's olive look makes the leaf mask catch lit stone so `leaf%` runs ~1.7× the reference **before** any change — the mask is saturated and added leaf area has nothing left to cover).

| box | leaf% before → after (ref) | hard% before → after (ref) |
|---|---|---|
| 01 shore shrub/reed | 58.8 → 58.8 (17.9) | 0.11 → 0.11 (1.77) |
| 01 shore shrub S | 40.3 → 38.8 (13.6) | 0.33 → 0.35 (3.38) |
| 02 shrub/reed shore | 87.2 → **89.0** (88.6) | 0.33 → 0.49 (3.44) |
| 02 reed clump SE | 40.5 → 35.6 (24.9) | 0.00 → 0.00 (1.57) |
| 05 shrub/reed shore | 55.6 → 54.6 (33.4) | 0.37 → 0.29 (4.30) |
| 05 shrub/reed W | 42.0 → 41.7 (20.1) | 0.59 → 0.59 (4.06) |
| 03 shrub cards | 70.4 → 70.4 (26.5) | 0.10 → 0.07 (1.48) |

Mean leaf% 56.4 → 55.6, hard% 0.26 → 0.27: flat, as this harness must be. The constraint the brief sets — hard-edge share must not rise above the reference — holds everywhere. The real numbers come from QA on the exported build.

**Files.** `scripts/env_build.py` (`_leaf_clump`, `SHRUB_LOD`, `CLUMP_*`/`TUFT_LODS`, `shrub_sources()` extracted, `--shrub-stats [--lod2=card,cover,blade,sub[,clump]]` to price any LOD2 setting in 5 s), `scripts/env_preview.py` (`--local --lod=N` now switches `ENV_shrub_*` render visibility — it only did trees, so a "LOD1 preview" silently rendered the LOD0 cards), `scripts/env_p8_boxes.py` (new), `assets/environment.blend` (rebuilt by script), `renders/qa_comparisons/p8a_shrubs_*.{jpg,png}`, `renders/previews/environment/*_p8a_{before,after,before_lod2,after_lod2,after_lod0}.png`, `renders/logs/p8a_*.log`.

**Sanity.** LOD0 previews at cam01/02/05 (`*_p8a_after_lod0.png`): shore band continuous, no bald patches from the clumping — the Cycles path is safe.
