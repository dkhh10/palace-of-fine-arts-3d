# Phase 8a-4 — the LOD1 walk-in shrub cards at cam03 (export, 2026-09-19). CPU only: no Blender, no Chrome.

QA 22 finding 3: cam03's shrubs are "large flat gold/black cut-outs against Cycles' dense dark bushes", owner EXPORT,
on the assumption that they are the LOD1 twin of the magnification 8a-3 fixed on the LOD2 set. **Measured, they are
not.** Probe: `export/p8e_leaf_probe.py` (`SHRUB_CARD['LOD1']`, `blade`, `solve_cutoff`) + the instance rows; frames
`renders/web/gate10_cam03.png` and `renders/previews/qa/round13_03_colonnade_walk_cycles.png` at 100 %.

## 1. Where the LOD1 cards actually are, and how big
cam03 is 18 mm on 1920x1080 → 960/d px per metre. The nearest LOD1 row **in frame is 17.3 m**, not 3 m: shrub 8 rows
17.3-27.8 m (p50 19.8, instance scale p50 1.46), shrub_light 20 rows 18.7-29.3 (p50 25.9, 1.06), shrub_dry 25 rows
17.7-29.0 (p50 22.0, 1.06), reeds 8 rows 21.3-26.9 (0.81). At those distances a card is **5.1-13.0 px wide and
7.4-17.1 px tall**, and one painted leaf (5.3 % of the texture) is **0.4-0.9 px — sub-pixel**. There is no
magnification left to remove at this station; the 3 m walk-in case (cards 30-75 px, painted leaf 3.9-5.2 px) is real
but no station stands there.

## 2. What the two frames actually differ in (same boxes, 100 %)
| measure (bush box 860-1180, 650-760) | viewer | Cycles | |
|---|---|---|---|
| grain: median / p90 distance between luma extrema along rows | **2.0 / 4.0 px** | **2.0 / 4.0 px** | identical |
| bush-body luma (darkest 60 %) | 0.142 | 0.058 | **2.4x too bright** |
| dark share (luma < 0.05) | 0.062 | 0.248 | **the dark interior is missing** |
| g - r on the body | -0.030 | +0.003 | **warm/gold cast** |
| saturation | 0.74 | 0.78 | matched |

And the station context, same frames: column shade **2.55x** brighter than Cycles, far water/shore **1.78x**, the bush
**1.79x**, pavement **1.37x**. So the bush carries the station's own brightness error (cam03's missing deep shade, a
QA-21 carry) plus ~1.3x of its own, and it has none of Cycles' dark core. **The cards read as cut-outs because each
one is uniformly bright against a dark background — the silhouette is what is visible, not the leaves.** Grain, the
one thing a UV scale changes, already matches the reference.

## 3. What a per-card UV scale k would give anyway
Per material at cam03's distances (run width p90 / thickness p90 / coverage ratio, cutoff solved to hold coverage):
shrub 19.8 m **12.6 → 7.0 px at 1.01x** (cut 0.50→0.47); shrub_light 25.9 m 8.1 → 5.8 at 1.02x (0.51);
shrub_dry 22.0 m 5.6 → 5.6 at 0.96x (0.51) — already at the card's own width, so k buys nothing; reeds **must stay
1.0** (1 px cards: k=2 measures 1.99x coverage at 30 m, pure aliasing). At the 3 m walk-in: shrub 23.4 → 17.1 px,
shrub_light 22.0 → 16.9, shrub_dry 18.4 → 12.0, all within 1.00-1.01x coverage.

**The constraint that decides it.** 8a-3 chose LOD2 k=2 precisely so the 25-30 m LOD switch is invisible: the LOD2
tile is 0.185 m against the LOD1 card's 0.20 m (7 % apart, measured with each set's own median instance scale). A
LOD1 k=2 makes it **0.10 m against 0.185 m — a 1.85x grain jump at a boundary that is IN FRAME at cam03** (the band
runs 17-30+ m). Matching it would need LOD2 k=4, which the 8a-3 table already measures as aliasing at 54 m+
(coverage 1.28x, run width climbing back to 9.8 px). So tiling LOD1 cannot be done without re-opening the LOD2 set.

## 4. Recommendation, and the cost if it is overruled
**Recommend: no export change for cam03.** The defect the tiles show is luminance, interior occlusion and hue, not
card scale — owner VIEWER/LIGHTING: cam03's missing deep shade (already carried), the card interior/self-shadow term
that gives Cycles its 0.248 dark share (`foliage.js` `cardInt`/`crownInt`, the knobs 8a tuned for the far trees), and
a ~0.03 g-r warm cast. A UV scale would make the foliage finer than the reference while breaking the LOD-switch
match — a regression paid for a metric that is already level.

If the lead wants the 3 m walk-in improved anyway, the export scope is small and **tier-2 only**: `MAT_shrub` and
`MAT_shrub_light` k=2 with cutoffs solved (~0.47-0.53), `MAT_shrub_dry` and `MAT_reeds` unchanged, applied in
`export/shrub_lod1.py` (the samplers in both `env.gltf` and `env_shrubs.gltf` are already REPEAT, so no sampler work).
Chain: `shrub_lod1.py` → `gltf_pack.sh --shrubs` → `instance_rows.mjs` (shrub set) → `PFA_ORDER_SET=shrub_lod1
gate4_instance_order.py` → `gate5_instance_rows.py` → `manifest_v4.py` (its `glb_bytes` assert) → `tiers.py` x3 →
`verify_glb --gate5` + `tiers_test`. Byte cost, estimated on the trees' measured 0.54 B per unique triangle over
env_shrubs' 31 268 unique tris: **≈ +16 kB on a 668 388 B tier-2 lazy file; tier 0 untouched, first frame unchanged.**
