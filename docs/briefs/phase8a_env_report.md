# Phase 8a — shrub / reed card density (ENV, branch `phase8-env`)

**BLOCKING FINDING, read first.** The web export ships the **LOD2** shrub mesh for all 1 379 placements — `export/gate1_set.py:741` *"# shrubs at LOD2, shared mesh per prototype"*, taking the placed `_LOD1` object only for its transform (the 28 shrub rows in `docs/briefs/phase6_budget.md` are all `ENV_src_*_LOD2`). The QA-17 shrub boxes therefore measure LOD2 geometry, and **this LOD1 change cannot move them.** It does reach the Cycles renders (shrubs 80–160 m from every QA camera carry the LOD1 mesh at LOD0) and the Blender viewport. Lead's call, costed on ENV's 800 k placed-triangle class budget: (a) ship LOD1 in the viewer = 1 015 k placed, 1.27× the whole ENV budget — impossible; (b) LOD2 at `card=3.30, cover=0.85, blade=0.24` = unique 3 920 → 6 948, placed ≈ 240 k (+105 k, from the near-tree allowance); (c) LOD2 clumped at its present card size and count = **0 triangles**, lobes instead of an even scatter. `scripts/env_build.py -- --shrub-stats --lod2=card,cover,blade,sub[,clump]` prices any option in 5 s.

**The change** (`scripts/env_build.py`). Cards are emitted as **clumps** (`_leaf_clump`, 4–9 cards, four leaf scales with mean square 1.0, shared dominant azimuth ± 0.85 rad, tilt spread ± 0.55) instead of an even scatter of one-size quads; blade clumps come in **tufts** of 4–8 sharing an origin and lean. LOD1 drops the round-02 "k× wider, k²× fewer" rule from `card 2.20 / cover 0.95 / blade 0.33` to **`1.65 / 1.00 / 0.75`**: leaf card 18.7 → **14.0 cm** with **1.87×** the cards, reed blade 7.8 → **5.2 cm** with **2.3×** the blades. Clumping runs at LOD0 and LOD1; LOD2 keeps the round-02 scatter. No material, name, placement or LOD-assignment change (1 379 placements, 25 sources × 3 LODs, `MAT_shrub{,_light,_dry}` / `MAT_reeds` untouched).

**Triangles.** Unique LOD1 **17 094 → 31 268 = 1.83×** (brief cap 2× = 34 188). Unique LOD0 **79 814** and LOD2 **3 920** unchanged to the triangle — the clump emitter keeps the card *count*, so only the distribution moves. Placed: LOD0 2 425 986 → 2 425 986 (1.000×), LOD1 551 576 → **1 015 498** (1.841×), LOD2 135 880 unchanged. Largest leaf card 20 cm, unchanged.

**Numbers, per box** (`scripts/env_p8_boxes.py`, QA 16's own `box_stats`; ENV `--local --lod=1` Eevee previews, 1280×720, 16 spp). The reference column reproduces every QA-17 value exactly, which is the harness check; the *preview* columns are not directly comparable to it (previews are upscaled to the 1920×1080 box space, so `hard%` reads ~10× low, and env_preview's olive look makes the leaf mask catch lit stone, so `leaf%` runs ~1.7× the reference). Decision metric is before → after.

| box | leaf% before → after (ref) | hard% before → after (ref) |
|---|---|---|
| 01 shore shrub/reed | 58.8 → 58.8 (17.9) | 0.11 → 0.11 (1.77) |
| 01 shore shrub S | 40.3 → 38.8 (13.6) | 0.33 → 0.35 (3.38) |
| 02 shrub/reed shore | 87.2 → **89.0** (88.6) | 0.33 → 0.49 (3.44) |
| 02 reed clump SE | 40.5 → 35.6 (24.9) | 0.00 → 0.00 (1.57) |
| 05 shrub/reed shore | 55.6 → 54.6 (33.4) | 0.37 → 0.29 (4.30) |
| 05 shrub/reed W | 42.0 → 41.7 (20.1) | 0.59 → 0.59 (4.06) |
| 03 shrub cards | 70.4 → 70.4 (26.5) | 0.10 → 0.07 (1.48) |

Mean leaf% 56.4 → 55.6, hard% 0.26 → 0.27: **the boxes are flat, and at this harness they cannot be anything else** — the preview's leaf mask is already saturated by the olive look (1.7× the reference before the change) so added leaf area has nothing left to cover, and `hard%` is destroyed by the 1280→1920 upscale. Hard-edge share does not rise, which is the constraint the brief sets. The structure change is real and visible at 100 %: `renders/qa_comparisons/p8a_shrubs_cam02.jpg` rows 4–6 show the reed clump going from four broad orange slabs to a tufted mass of small varied blades. QA should re-measure on the exported build, and only after the lead has decided the LOD2 question above.

**Files.** `scripts/env_build.py` (`_leaf_clump`, `SHRUB_LOD`, `CLUMP_*`/`TUFT_LODS`, `shrub_sources()` extracted, `--shrub-stats[--lod2=…]`), `scripts/env_preview.py` (`--local --lod=N` now switches `ENV_shrub_*` render visibility — it only did trees, so a "LOD1 preview" was silently rendering the LOD0 cards), `scripts/env_p8_boxes.py` (new), `assets/environment.blend` (rebuilt: 1 379 shrubs, ENV LOD0 13 909 362 / LOD1 5 237 300 / LOD2 670 422), `renders/qa_comparisons/p8a_shrubs_cam0{1,2,3,5}.jpg` + `p8a_shrubs_frames.jpg`, `renders/previews/environment/*_p8a_{before,after,after_lod0}.png`, `renders/logs/p8a_*.log`.

**Sanity.** LOD0 previews at cam01/02/05 (`*_p8a_after_lod0.png`): shore band continuous, no bald patches from the clumping — the Cycles path is safe.
