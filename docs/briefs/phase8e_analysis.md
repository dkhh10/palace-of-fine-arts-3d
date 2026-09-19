# Phase 8e PART 0 — the LOD2 leaf-card scale at 37-45 m (export, 2026-09-19). CPU only: no Blender, no Chrome.

Probe: `export/p8e_leaf_probe.py` (numpy + PIL). Inputs: `export/out/gate3/trees_far/{placements,topology}.json`,
`export/out/gate1/env_trees.gltf` (UVs decoded from the bin), `assets/textures/foliage/*.png`, `renders/web/gate7_orbit*`.
Orbit camera = `window.__pfaOrbit` (fov **40 deg vertical**, canvas 1170x2532, dpr 0.712), stations read from
`renders/web/gate7_orbit_cam.json`, so px/m at distance d = 2532 / (2 d tan 20 deg) = **86.9 px/m at 40 m**.

## 1. What is actually on screen (measured, two independent ways)
The far meshes are **not** `scripts/env_trees.py::_lod2_cards` — `trees_far.py` rejects every shipped `_LOD2` object
(`topology.json: lod2_objects_rejected`) and rebuilds the crowns from the `_LOD1` Sapling cards. A card is ONE quad
carrying a centred vertical strip of the 1024 px cluster texture (u window 0.18-0.85 by species, v 0-1); one full
texture tile = 0.88-1.02 m of prototype world, 0.54-0.85 m once the placement scale (0.40-1.23, median 0.58-0.87) is on.

| species (leaf tex) | card W x H (m, placed) | card px @40 m | blob p90/max px, k=1 | k=2 | k=2.5 |
|---|---|---|---|---|---|
| broadleaf (leaves_broadleaf) | 0.46 x 0.54 | 40 x 47 | **22 / 28** | 11 / 14 | 8 / 11 |
| cypress, cypress_column (needles_cypress) | 0.31 x 0.82 | 27 x 71 | **20 / 28** | 11 / 14 | 11 / 11 |
| eucalyptus (leaves_eucalyptus) | 0.36 x 0.85 | 31 x 74 | **20 / 28** | 11 / 14 | 11 / 11 |
| pine (needles_pine) | 0.26 x 0.73 | 22 x 64 | **20 / 22** | 11 / 11 | 8 / 8 |
| redwood (needles_pine) | 0.24 x 0.60 | 21 x 52 | **17 / 22** | 8 / 11 | 8 / 8 |
| willow (leaves_broadleaf) | 0.14 x 0.77 | 12 x 67 | **11 / 14** | 6 / 6 | 6 / 6 |

"blob" = the width of what survives `alphaMode MASK` (cutoff 0.42-0.50, read from the glb) once the albedo's ALPHA is
box-downsampled to the card's RENDERED size (card px x 0.712), i.e. the mip the GPU picks; 2 x p90 of an erosion
distance transform, reported back in capture px. **This is the defect**: the painted leaves are 0.05-0.11 m (4-10 px,
plausible), but at 20-30 texels per pixel the mip merges them and the alpha cut re-hardens the mush into blades
**0.23-0.32 m / 20-28 px** with long axes of 47-74 px — QA 19's "~40 px gold/black duotone blades", reproduced from the
texture and the geometry alone. The nearest crowns in the two orbit frames are TREEFAR_117 willow 37.4 m, TREEFAR_001
broadleaf 38.5 m (h215) and TREEFAR_000 broadleaf 36.7 m, TREEFAR_116 willow 37.7 m (h253); a pixel measurement inside
those crowns gives 10-12 px for the shaded halves, the lit halves cannot be masked cleanly (warm stone behind them).
Plausible at 37-45 m: an individual leaf 2-10 px, a foliage clump 0.10-0.15 m = **9-13 px**. Shipped is 2-3x over.

## 2. Where the scale is set, and the one lever the export owns
Card world size = Sapling's leaf scale in the prototype x `trees_far.thin_and_grow`'s `CARD_SCALE_MAX = 1.6` grow
x the placement scale. Shrinking the card (any of those) is the wrong lever: leaf area goes as the square, and 6c's
see-through crowns are what the 1.6 grow and Phase 7 exist to prevent. **Coverage after the alpha cut is invariant under
a UV scale** (0.45-0.61 at every k in the table): tiling the cluster divides the apparent leaf size by k and leaves the
crown's opacity untouched. So the lever is a **UV scale k about each card's own UV centre, on the LEAF-material faces
only, in `trees_far.py` between `thin_and_grow` and `join`, gated to `SET_NAME == 'far'`** (the walk-up set is desktop's),
plus a deterministic per-card UV offset so neighbouring cards do not share a grid. No vertex is added, moved or removed:
`vertex_ao.npz` (POINT domain, by index, `topology_rev` 2) still matches, and the instance rows, order and translations
that the placement join keys on are untouched.

**Recommended k (the smallest that puts the blade at p90 <= 11 px, max <= 14 px at 40 m): broadleaf 2.0, cypress 2.0,
cypress_column 2.0, eucalyptus 2.0, pine 2.0, redwood 2.0, willow 1.5** (willow already meets the bar at k=1 — its cards
are 0.14 m wide — so 1.5 there is optional margin, not a fix). If QA still reads them large, 2.5 is the next step (p90 8-11 px); beyond 3 the 3x3
repeat inside one card becomes visible to a walker standing under it (mobile draws this set within 45 m).

**Two dependencies the lead must rule on before PART 1.** (a) The leaf textures ship with `wrapS/wrapT = CLAMP_TO_EDGE`
(sampler 1 of `env_trees.glb`, used by exactly the 8 leaf albedo/normal textures; bark is sampler 0). Any k > 1 leaves
0-1 in v, so that sampler must become REPEAT. Cheapest honest route: patch the written `env_trees.gltf` JSON in the
export (the pattern of `export/gltf_ktx2_patch.py`) — no `MAT_leaf_*` material and no albedo texture is touched.
(b) The runtime swaps in the tinted albedo (which inherits the glb's wrap, fine) but hard-codes the translucency map to
`ClampToEdgeWrapping` at `web/src/foliageLazy.js:838`; outside the first tile the translucency factor would clamp.
That is a one-line viewer change this brief does not own — 8e cannot ship without it.

## 3. Cost
`env_trees.glb` is **3 699 324 B**, `tier 2`, `kind glb_lazy` (`out/gate5/manifest.json` files row; the mobile manifest
shares the same file). UV values change, not counts or layout, so the only byte effect is gltfpack's UV quantisation
range growing k-fold (16-bit UVs over a 2x wider range, still far under a texel): **expect under +-1 %, measured in PART 1**.
**Tier 0 is untouched** (no tree glb in it) and must come out byte-identical. **Desktop is untouched in the steady
state**: `device.js` leaves `walkupMesh` null, so `foliageLazy` picks `trees.walkup_mesh` = `env_trees_lod1.glb` and
only falls back to `env_trees.glb` if the walk-up glb 404s or fails the join — which is why the factor is gated to the
`far` set. Mobile (`walkupMesh: '0'`, `farTreeMesh: 45`) is the only tier that draws it.
