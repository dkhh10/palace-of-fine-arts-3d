# QA round 19 — Phase **7, the foliage look on the live URL** (the closing Phase 7 round), 2026-09-19. Verdict: **PHASE 7 DONE WITH RESIDUALS**

Capture `gate7` on https://pfa-walkthrough.3d-render-blender-3rd-attempt-building.workers.dev (deploy 7, main 0a5cf52): desktop stations 1-6 at 1920x1080,
`gate7_net.json`, 1440p `gate7_perf.json`, `?tier=mobile` stations 1-6 at 1170x2532, and the lead's close orbit `gate7_orbit_h0{2530,2150}` (80 m, height 5 m,
headings 253/215 — the fixture that reproduces the user's iPhone screenshot). Before = `gate5b` (desktop) and `gate5cm` (mobile), round 18b. Measures:
`scripts/qa_p7_probe.py` (the viewer's own tool, run unchanged) and `scripts/qa_r19_probe.py` (an extension of r18b -> r18 -> r17 -> r16 -> r13). No Blender,
no Chrome; the URL was read with `curl` only. Composite: `renders/web/gate7_gate.png`.

## 1. Verdict against the brief's acceptance

| item | required | measured on `gate7` | |
|---|---|---|---|
| hero crown p10 vs Cycles | >= 0.8x (was 0.57x) | **0.894x** | PASS |
| cam02 centre/edge | hold ~0.39 (ref 0.364) | **0.397** | PASS |
| station 5 frame luma | 1.00 +- 0.01 | **0.976x** (was 0.970x) | **MISS** — carried, see residual 1 |
| desktop tiles: jagged / dithered silhouettes, pale halo, near-black blotches | gone or named | halo and blotches **gone**; the cards are still opaque, named | PASS with residual 3 |
| mobile near trees inside the radius | meshes, no black cores | `farTrees.meshDist` **45 m** live, 127 placements as meshes, 0 card crowns in either orbit frame | PASS |
| architecture unmoved | < 3 % | **0 of 11** boxes move (max 1.006x) | PASS |
| perf | inside +3 ms | +0.4 / +1.7 / +0.0 / +0.8 / +1.4 / +0.0 vs `gate5b`; +0.8 / +0.1 / +1.0 / +2.0 / +2.7 / +2.2 vs `gate5cold` | PASS |
| resident desktop | +100 MB max | **1 861.3 MB**, identical to the byte | PASS |
| resident mobile | < 700 MB | **561.9 MB** (+62.2 from 499.7) | PASS |
| payload before the first frame | <= 50 000 000, tier 0 untouched | **46 811 106 B** over the same 320 requests (+2 202 B, of which the JS bundle is +1 808 B; no new asset file) | PASS |
| page errors / name sweep | 0 | 0 errors desktop, mobile and orbit; 0 name hits over 706 + 341 manifest rows | PASS |

## 2. The crown boxes, round 18b -> round 19 (QA 17 §3's boxes and measures; reference = 1.000x)

| crown box | centre/edge (ref) | p10 | p10 / ref | level | hard-edge % (ref) | halo dL (ref) |
|---|---|---|---|---|---|---|
| 01 hero shore crown | 0.467 -> **0.532** (0.852) | 20.8 -> **32.9** | 0.564 -> **0.894x** | 0.91 -> **0.94x** | 3.70 -> **3.32** (4.94) | -2.06 -> **-6.83** (-39.30) |
| 02 fill tree | 0.368 -> **0.397** (0.364) | 5.3 -> **10.4** | 1.289 -> **2.494x** | 1.00 -> **1.04x** | 1.54 -> **1.47** (2.29) | -0.72 -> **-2.44** (-1.72) |
| 05 lawn tree | 0.922 -> **0.912** (0.960) | 28.0 -> **41.1** | 0.883 -> **1.297x** | 1.05 -> **1.09x** | 6.03 -> **5.04** (6.30) | -9.76 -> **-14.58** (-23.28) |

The floor does what QA 17 asked **at the box it was fitted to** and overshoots at the other two: the hero's dark end goes from 0.56x to 0.89x of Cycles, but
cam02's goes from 1.29x to **2.49x** and cam05's from 0.88x to **1.30x**. The halo dL moves toward the reference at all three and reaches at most 17 % of the
way there. Whole-frame luma / reference: 0.924 -> **0.927** / 1.049 -> **1.052** / 1.622 -> 1.623 / 1.113 -> 1.113 / 0.970 -> **0.976** / 0.975 -> **0.977**;
MAE against the reference falls at four stations (24.80 -> **24.52**, 18.58 -> **18.44**, 21.39 -> **20.69**, 18.15 -> **18.03**) and is unchanged at 03 / 04.
Of the 25 round-13/15/16 boxes, **4 move more than 3 %, all foliage and all intended** (01 near tree band 1.038x, 02 fill tree 1.042x, 05 tree crown 1.035x,
05 shrub/reed W 1.055x); three move toward the reference, `05 tree crown` moves away (112.3 vs the reference's 103.4). No architecture box moves.

## 3. Tiles — desktop (hero at 100 % in six 3x2 tiles, plus 300 %/800 % pairs at the far band, and before/after/Cycles triptychs at 01/02/03/05/06)

1. **The user's two desktop defects are closed on the tiles.** At 800 % on the hero's roof-line band (`renders/web/gate7_gate.png` row A) the one-pixel
   whitish fringe that ran along every silhouette in 6c — against the sky *and* against the stone — is gone and the leaf colour carries to the boundary; the
   binary 0/1 edge steps are resolved into intermediate pixels. The near-black blotches inside the shore crowns (row B) are gone and the crowns read as lobed
   leafy masses instead of flat cut-outs with dark holes.
2. **What the same tiles still show (not Phase 7's scope).** The far-tree cards remain **pale, opaque grey-green masses** where the Cycles reference shows
   dark twigs with sky between them (QA 17 residual 4, owner bake/export) — with the halo removed this is now the dominant far-tree fault. The hero's four
   shore crowns repeat one silhouette. r2c1/r2c2 the shrub and reed band is still broad flat gold blades; r2c1 the N-colonnade backdrop is a flat olive field
   with dark panels; r2c2/r2c3 the reflection stays cooler and less saturated than Cycles.
3. **cam02** the fill crown's core is legible instead of black, at the cost of the 2.49x dark-end overshoot above; no trunk or branch is visible through it
   where the reference has both. **cam05** the cypress silhouette is the round's cleanest edge win — no pale rim against the sky. **cam03** the shrub cards are
   pixel-for-pixel the 6c cards (1.5 % of the frame moved, all of it the band behind), i.e. the deferred residual 1 is visibly unchanged. **cam04** is
   bit-identical (0.008 % of pixels, max 26/255 in one card). **cam06** gains a little leaf structure at the shore, +1.1 % on the box.
4. No filled opening, missing ornament, lightmap seam, z-fighting or new material defect in any tile; every arch the hero looks through is open to its far side.

## 4. Tiles — mobile (six stations + the close orbit, at 100 %)

1. **The user's phone defect is closed.** In both orbit headings the crowns at 37-40 m are **meshes**: branches, individual leaf cards and background through
   the canopy (gate composite row C, beside the 6c card). Near-black share inside the four orbit crown boxes is 0.00 / 4.47 / 0.00 / 0.00 % and the 4.47 % is a
   shaded trunk in front of a dark column, not a card core; p05 is 35.7 / 14.0 / 37.0 / 39.9 against 6c's featureless dark blobs.
2. **Confirmed live from the sidecar:** `farTrees.meshDist` 45 m with 127 placements lit from the bake, `foliage.meshDist` 25 m (18 near units), `shrubLod1`
   25 nodes / 1 376 rows at 25 m, `impostors.interior` floor 0.55 at strength 0.45. 0 page errors, 0 shader errors, canvas 1170x2532 at ratio 0.712.
3. **Station tiles:** all six draw the whole scene at full canvas; m cam02 at 100 % turns a band of dark blobby cards into branched trees with sky through
   them, and the hero lagoon now reflects the rotunda (that half is the 6d fix, which `gate5cm` predates — the mobile before/after deltas below bundle both).
4. **New mobile findings.** (a) The LOD2 leaf cards are **scale-implausible at 37 m**: individual leaves read ~40 px wide as gold/black duotone blades, so the
   near crowns are legible but not believable (owner export/bake). (b) The shaded colonnade stone in the close orbit reads **blue-violet**; it is in the 6c
   orbit panel too, so it is carried, not a Phase 7 regression (owner materials/lighting on the mobile tier).

## 5. Scores

Desktop (rubric rows as QA 17; only the row named below moves): **01 3.78 · 02 3.25 · 03 2.63 · 04 2.88 · 05 3.06 · 06 2.83** — deltas vs QA 17/18b
0 / 0 / 0 / 0 / **+0.12** / 0. Station 5's Lighting mood goes 2.5 -> **3.0**: two of the three faults QA 17 docked it for are fixed (crowns no longer blotchy
near-black; its probe MAE, the only one that rose in 6c, falls 21.39 -> 20.69) while the third, the frame running under the reference, only improves
0.970 -> 0.976x. **The hero does not move**: the rows Phase 7 touched (Material realism 4, Lighting mood 4) were already at the top of their band, and the
hero's remaining material faults — the shrub band at 1.47x, the flat backdrop wall, the desaturated reflection — are the deferred ones. The gain at 01 is real
but it is in the boxes and the tiles, not in a half-step.

Mobile (first scored in QA 18b): **01 3.2 · 02 3.3 · 03 2.3 · 04 2.7 · 05 2.8 · 06 2.4** against 2.9 / 3.0 / 2.3 / 2.7 / 2.5 / 2.4 — Material realism and
Water reflection at the three water stations, nothing elsewhere; 03 and 06 are unchanged to 0.2 % of frame luma and 04 is bit-identical. Attribution: the water
half of that move is the 6d reflection fix, the foliage half is Phase 7.

## 6. Perf, payload, sweep, URL

1440p medians **31.6 / 37.3 / 38.9 / 26.3 / 35.9 / 36.5 ms** (hero 31.6 fps), taken right after the 35-minute capture as `gate5b`'s were; against the idle
`gate5cold` pass the deltas are +0.8 / +0.1 / +1.0 / +2.0 / +2.7 / +2.2, every one inside the +3 ms rule, with draw calls, triangles and programs **identical**
to `gate5b` at all six stations (hero 335 draws / 5.25 M tris / 141 programs) — `treemesh` 80 costs nothing at the stations because no near tree is within 80 m
of any of them. I re-ran the viewer's own same-session A/B arithmetic against the seven `p7ab_*` / `p7cost_*` perf JSONs: the files exist, the medians match the
README's tables to 0.01 ms, and the adopted setting's worst station is **+0.70 ms against a +0.60 ms drift control**; A + B together cost between -0.60 and
+0.50 ms. Payload: 46 811 106 B / 320 requests before the first frame (**46.81 MB**, the +2 202 B over `gate5b` is the rebuilt JS bundle, +1 808 B, plus
response-boundary noise); tier 0 carries the same asset files; mobile first frame 46 740 252 B and total 65.79 MB (+4.13 MB, all of it lazy tier 2). Name sweep
**0 object-shaped hits** over both manifests; 0 mobile paths absent from the desktop plan. URL by `curl`: `/` 200 `max-age=300`, both manifests 200 `max-age=60`,
bake files 200 `immutable`, and the deployed bundle's default manifest is `assets/gate5` with `farTreeMesh:45` / `shrubLod:25` in the mobile tier. The bare-URL
*frame* check needs Chrome and was not re-run this round; it stands from the 6b close on the same deployment path.

## 7. Residuals for `docs/delivery.md`, with owners

1. **Station 5's frame stays 2.4 % under the reference — owner VIEWER/LIGHTING.** 0.976x against the brief's 1.00 +- 0.01. The branch swept the lever to 0.55
   (0.981x) with every crown overshooting, so the remaining 2 % is not foliage. Named and measured, not fitted.
2. **The crown floor overshoots at two of three boxes — owner VIEWER.** cam02's fill-tree dark end is 2.49x of the reference's p10 and cam05's 1.30x, where the
   hero (the box it was fitted to) lands at 0.894x. A per-distance or per-prototype floor, not a global one, is the fix.
3. **The far-tree cards are opaque — owner BAKE/EXPORT** (QA 17 residual 4, unchanged). With the halo gone this is the visible far-tree fault: pale closed
   silhouettes where Cycles shows sky through the twigs, and a halo dL still 6x from the reference.
4. **Shrub / reed card STRUCTURE — owner EXPORT** (QA 17 residual 1, deferred by decision). Verified unchanged, reported, not failed on.
5. **Mobile close-up leaf scale, and blue-violet shaded stone on the mobile tier — owners EXPORT/BAKE and MATERIALS.** Both described in §4.4; the second is
   carried from 6c, not introduced here.
6. **Carried unchanged from 6a/6b/6c:** flat backdrop city blocks and colonnade backdrop walls; cam03 has no deep shade (1.62x) and blurred column concrete at
   1 m; cam06's water moiré; the hero reflection cooler and less saturated than Cycles; hero 31.6 fps at 1440p against the 45 target; the mobile portrait
   framing; still owed by the user — the macOS Safari hero screenshot and the iPhone 16 Pro walk recording.
