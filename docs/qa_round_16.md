# QA round 16 — Phase **6c, the foliage gate**, round one of two, 2026-09-17. Verdict: **ONE MORE ROUND**

Scored on `round16b` (main @ 98b9f3e, 1920x1080 stations / 2560x1440 perf, every 6c default on: `impmod=full`, `fartreemesh=12`, `treemesh=40`,
shrub LOD1 at 30 m, foliage 1 K, 2 K impostor atlas, `t=0`) against the `round16bnopost` control, `round15`, and the references (station 1 the Phase 5
Cycles hero, 2-6 `renders/previews/qa/round13_0N_*_cycles.png`; 3 and 5 keep their round-15 caveat). No Blender, no Chrome. Tools:
`scripts/qa_r16_probe.py` (imports `qa_r15_probe` / `qa_r13_probe` unchanged; adds `foliage16 crown bareurl perf16 names`) + `scripts/qa_r16_gate.py`.
Capture clean: **0 page errors**, 0 shader errors, 254/254 far-tree rows joined and lit from the bake, 127/127 placements modulated, 1 376/1 376 LOD1
shrubs bound, ready in 6.39 s. Composite `renders/web/round16b_gate.png`. The six-station tile review below was written **before** decisions.md's
"Lead 100 % tile judgement of round16b" was read, as the brief's addendum requires; §5 is the comparison.

## 1. Verdict against the 6c acceptance (`docs/briefs/phase6c_foliage.md`)

| 6c criterion | result |
|---|---|
| no station drops more than 0.1 | **PASS** — none drops at all |
| station 2 must rise | **PASS** — 3.00 -> **3.13** (+0.13); MAE 23.11 -> **20.48**, the round's largest move |
| frame time within +3 ms of round 15 at 1440p | **PASS** — worst **+1.9 ms** (hero 28.2 -> 30.1); cam03 **-0.2** |
| resident GPU memory reported | **1 800.6 MB** = **1.50x** the 1 200 MB Gate 1 budget (§4) |

**The stated acceptance passes; 6c's own goal does not.** The goal is "foliage credible at 3 m from every station and along the walk", and CLAUDE.md's
rule is that the numeric boxes never override the tiles. At 100 % the shrub/reed cards are straw-pale hard-edged confetti at **1.3x-1.7x** the reference
level at *every* station, the crowns are smooth balloons with no interior, and the 3 m walk-in does not read as a tree. **ONE MORE ROUND** (the brief
allows two); §3 names the station, box and owner of each.

## 2. Scores

| row | 01 | 02 | 03 | 04 | 05 | 06 |   | row | 01 | 02 | 03 | 04 | 05 | 06 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Silhouette | 4 | 3.5 | 2.5 | 3.5 | 3.5 | 3.5 |  | Water reflection | 3.5 | n/a | n/a | n/a | 2.5 | 3 |
| Proportion | 4 | 3.5 | 3 | 3.5 | 3.5 | 3.5 |  | Repetition | 3.5 | 3 | 2.5 | 2.5 | 2.5 | 2.5 |
| Ornament | 4 | 3 | 3 | 3 | 3 | 2.5 |  | Scale cues | 3.5 | 2.5 | 2.5 | 3 | 3 | 3 |
| Material realism | 3.5 | **3.5** (3) | 3 | 3 | 3 | 3 |  | **round 16** | **3.72** | **3.13** | **2.56** | **2.88** | **2.94** | **2.83** |
| Edge wear | 3.5 | 2.5 | 2 | 1.5 | 2.5 | 1 |  | round 15 | 3.72 | 3.00 | 2.56 | 2.88 | 2.94 | 2.83 |
| Lighting mood | 4 | **3.5** (3) | 2 | 3 | 3 | 3.5 |  | **delta r15** | **0.00** | **+0.13** | 0.00 | 0.00 | 0.00 | 0.00 |
|  |  |  |  |  |  |  |  | delta Phase 5 | +0.05 | **+0.19** | 0.00 | +0.07 | -0.12 | +0.17 |

Only station 2 moves: Material realism 3 -> 3.5 because the largest colour error in the frame (a blue impostor filling the middle of it — the user's own
finding) is closed, and Lighting mood 3 -> 3.5 because the trees now take the scene's warm bounce instead of the isolated bake's open sky. Nothing else
earns a half-step either way: stations 3 and 5 measure slightly *worse* on every foliage box (§3), but their round-15 / round-16b / Cycles A/B at 100 %
shows a hair more brightness and a hair softer edge, not a visible drop, so they hold.

MAE r15 -> r16b (`qa_r16_probe frame`, 1920x1080, the round-15 table's definition): 24.60 -> **24.79** / 23.11 -> **20.48** / 35.87 -> **35.41** / 13.08
-> 13.08 / 20.27 -> **20.37** / 18.72 -> **18.41**. The viewer's own pair sheets (1280x720 panels) agree except at 01 and 05, where the move is under
±0.3 either way — noise. Every round-14/15 box holds: hero shade band **0.99x**, capital-row std 0.85x -> **0.92x**, S-colonnade mid 0.44x -> **0.45x**,
attic sat **0.87x**, QA-13-1 band **0.1 %** (gate 3.9 %), cam04 coffer 1.02x, N-colonnade wall **1.26x** (the round-15 regression, unmoved).

## 3. The foliage boxes

**Closed — the far-tree impostors, by the modulation and not by the mesh.** cam02's fill tree `700 660 1240 950`: **1.41x -> 1.28x**, hue **68.2 ->
54.3** (ref 45.5), sat **0.100 -> 0.594** (ref 0.530), G>R 74.0 -> 57.0 (ref 33.3). The hero's far-tree roofline `400 440 620 540`: **1.12x -> 1.01x**,
hue **137.5 -> 75.3** (ref **76.9**) — round 15's "flat olive mass" is now the reference's colour. cam02 near trees `60 520 700 980`: G>R **37.4 ->
66.2 %** (ref 70.9), hue 57.7 -> **70.8** (ref 102.4, still 32 deg short).

**Open 1 — the shrub/reed cards are too bright, and 6c made them brighter. Owner: EXPORT.**

| shrub / reed box | round15 | **round16b** | ref lum | frame-normalised | hard-edge % (ref) |
|---|---|---|---|---|---|
| 01 shore `0 620 640 700` | 1.60x | **1.61x** | 56.6 | **1.70x** | 6.82 (1.77) |
| 02 shore `40 860 640 1060` | 1.44x | **1.62x** | 47.3 | **1.47x** | 8.56 (3.44) |
| 02 reed clump `1380 880 1860 1070` | 1.32x | **1.50x** | 48.2 | **1.36x** | 6.22 (1.57) |
| 03 cards `860 620 1280 750` | 2.13x | **2.20x** | 40.8 | **1.34x** | 12.11 (**1.48**) |
| 05 shore `200 840 1200 930` | 1.31x | **1.35x** | 92.3 | **1.34x** | 7.92 (4.30) |

Frame-normalised divides out each station's whole-frame ratio (it removes cam03's own 1.64x lift). The tinted albedo fixed the **hue** (cam02 G>R **4.2
-> 58.8 %** against the reference's 83.7) and pushed the **level** further out at four boxes of five; `post=off` reads the same (1.59x / 1.30x), so it is
the albedo, not post, not the probe. Leaf-green pixel share is the other half: cam05's box is **15.1 %** leaf-green against the reference's **33.4 %** —
cream and straw cut-outs where the reference has dense, dark-green, species-distinct planting. **Station 1 belongs on this list**: worst of the five at
1.70x, untouched by 6c, and it is the hero we deliver.

**Open 2 — the crowns have no interior. Owner: VIEWER.** Columns are round15 / **round16b** / **ref**.

| crown box | centre/edge | gradient | (p90-p10)/mean | p10 |
|---|---|---|---|---|
| 02 fill tree `700 660 1240 950` | 0.540 / **0.504** / **0.364** | 4.16 / **5.44** / **8.51** | 1.88 / **2.05** / **3.12** | 24.2 / 18.6 / **4.1** |
| 05 lawn tree `300 580 500 870` | 0.933 / **0.874** / 0.960 | 9.89 / **11.24** / 13.20 | 1.34 / **1.26** / **1.77** | 57.4 / 58.9 / **31.7** |
| 01 shore crown `760 545 1000 690` | 0.634 / **0.680** / **0.852** | 10.53 / **11.89** / 14.32 | 1.08 / **1.04** / **1.44** | 59.1 / 61.4 / **36.8** |

centre/edge is geometric (central 50 % of the box over the ring around it), so it needs no mask and is reference-comparable; the mask-based interior/rim
in `qa_r16_probe crown` is readable only down the viewer columns, the reference's crowns being too dark for the leaf mask. Every viewer crown carries
**1.6x-4.5x** the reference's p10 and **0.66x-0.77x** its dynamic range — lit all the way through. At cam05 the 6c leaf shader made it **6 % flatter**
(1.34 -> 1.26): the crown-bent normals plus the soft edges took the last of the contact shade.

**Open 3 — the 3 m walk-in. Owner: EXPORT.** Judged as a tile at 100 %: the LOD2 crown at 3 m is a handful of magnified cream-white cut-outs and a few
bare sticks over open sky. It does **not** read as a tree. The viewer already flagged it (README: "a walk-up that wants to stop AT a tree wants its
LOD1"); as the 6c goal is written, this is the item that fails it, and it needs the LOD1 tree set, not a viewer switch. **Ratified, though:**
`?fartreemesh=12` is right — `round16b_meshdist_ab` at 100 % shows the LOD2 crown at station distance as cream-white leaves against a dark-green
reference (1.957x, hp9 34.56 vs 17.46) where the modulated atlas lands at 1.28x / 17.12. Keep the 12 m default.

## 4. Tile defects (six stations, 3 x 2 at 100 %, viewer over the Cycles crop), perf, sweep, bare URL

1. **cam01** r1c1/r1c3 rooftop and left-edge crowns are pale grey-green lumps against branched, sky-gapped reference canopies — right colour now, wrong
   structure; r2c1/r2c3 the S-colonnade and backdrop walls are flat untextured mustard/cream fields, the shore planting hard gold angular confetti with
   white speckles, the open lagoon a flat teal slab. All carried from round 15; only the tree colour moved.
2. **cam02** r1c3 the far tree's top is a solid opaque silhouette where the reference shows sky through the twigs; r2c1 foreground cards are chunky,
   holey, part-lavender cut-outs and the reeds over-saturated orange spikes; r2c2 the fill tree is a smooth lumpy cloud — no trunk, no branch, no
   see-through; r2c3 the backdrop city blocks are flat coloured planes with a blown white edge and the reed clump is pale salmon against deep orange.
3. **cam03** r1c1 the overhead tree is a flat opaque olive cut-out; r2c2 the shrub cards are pale yellow-white spikes against dark-green reference shrubs
   at ~8 m — the round's worst hard-edge share (12.1 % vs 1.5 %); the station still has no deep shade (1.64x, p10 38.0 vs 7.3) and its column texture
   reads soft and blurred. **cam04** matches (MAE bit-identical to round 15); one blown white aliasing streak on the entablature edge in r2c3.
4. **cam06** r1c1 backdrop blocks are flat saturated planes; r2c1 the water carries a regular diagonal cross-hatch moiré at grazing incidence where the
   reference is smooth — measured identical to round 15 (hp9 6.23 -> 6.04, ref 4.21), so a carried defect this tile pass is the first to report, not a 6c
   change. No lightmap seam, slot bleed, texel blockiness, banding, z-fighting, filled opening or missing ornament in any of the 36 tiles; every arch the
   six stations look through is open to its far side.

**Perf, 2560x1440, median of 120 frames.** 30.1 / 33.5 / 32.7 / 22.7 / 31.8 / 33.5 ms (round 15: 28.2 / 32.2 / 32.9 / 22.5 / 30.4 / 32.1) — worst
**+1.9 ms**, inside the +3 ms gate, against a ~2 ms run-to-run spread; hero **33.2 fps**. Draws 329-351 (was 279), 5.24-5.60 M tris (4.14), load
**660.0 MB in 6.43 s**. **Resident 1 800.6 MB** (tex 1 227.5 + RT 443.8 + geo 129.3) against round 15's 1 677.9 and round 16's 1 684.7: **+115.9 MB**,
**1.50x** the 1 200 MB Gate 1 budget. *Finding:* `web/README.md` and `docs/decisions.md` both say 1 717 MB / "+111"; the committed `round16b_perf.json`
says 1 800.6 / +115.9 and its own `total_bytes` agrees with the sum — the two documents are wrong by ~83 MB. **Owner: viewer**, documentation only.

**Name sweep, restated** (`qa_r16_probe names`, over the export set's own manifests; no Blender). The only object-shaped pattern matches are
`ARCH_rotunda_inner_block` (the real inner piers), `ENV_backdrop_fill(roof)` (the city blocks) and `LIGHT_gallery_fill_north/south_##` (bake-side lights,
not render-visible geometry) — all named exceptions already in `docs/quality_checklist.md`. 6c's new members carry no hit (16 `ENV_tree_<species>_s##`,
25 `EXPM_ENV_src_*_LOD2`); every other match in those files is a JSON **field** name (`cards`, `card_scale`, `occluders`, `slots_filled`), not an object.
The 127 hidden `ENV_treeboard_*` carriers stay as before. **0 new to explain.** **Bare URL** against the station-1 preset: luma **1.0002x**, MAE
8.23/255 (a 1280x720 capture upscaled — resampling, not look); its boot log carries every delivery default — `impmod` full with 16 per-prototype
`E_bake`, 145 placements modulated, 2K atlas 16/16, 254/254 far-tree rows lit from the bake, 1 376/1 376 LOD1 shrubs, foliage at 1 024 px, 0 shader and
0 page errors. **Same look, no dev defaults.**

## 5. Where I agree and differ with the lead's tile judgement (decisions.md, same capture)

**Agree**, and the numbers back all three: the cam02 fill tree is a smooth opaque mass (centre/edge 0.504 vs 0.364, gradient 5.44 vs 8.51); the cam05
near trees are uniformly lit clouds and the 6c leaf shader flattened them a further 6 %; the shore shrubs are straw-pale sparse cards (leaf-green share
15.1 % vs 33.4 %). The lead's two proposed round-2 owners are the two my boxes point at. **Differ, three ways.** (a) The lead calls station 1
"acceptable at distance": its shore band is the **worst** of the five shrub boxes — 1.70x frame-normalised, 3.9x the reference's hard-edge share — it
did not move in 6c, and it is the hero we deliver; it belongs on the round-2 list beside 2 and 5.
(b) The lead leaves the shrub cause open between the tinted albedo, the per-placement irradiance and the translucency term; the boxes decide it — the
tint fixed the hue and pushed the level further out at four boxes of five, `post=off` is identical, and the same shift appears on the LOD1 meshes and the
LOD2 cards alike. It is the **albedo**, so that item is **export**, not viewer. (c) Two defects the lead's three stations could not show: **cam03**'s
cards carry the same straw paleness at ~8 m with the round's worst hard-edge share, and **cam06**'s water moirés at grazing incidence. Neither is a 6c
regression; both belong in the delivery notes.

## 6. Residual defects for `docs/delivery.md`

1. **Shrub and reed cards** read as straw-pale, hard-edged confetti at every station: 1.3-1.7x the Cycles level, 2-8x its hard-edge share, about half its
   leaf-green pixel share.
2. **Tree crowns have no interior shadow** — smooth balloons at 1.6-4.5x the reference's p10 and 0.66-0.77x its dynamic range; far crowns are opaque
   where the reference shows sky through the twigs. **A walk-up to a far tree** at 3 m shows magnified LOD2 cards and bare sticks; it wants the LOD1 set.
3. Carried from 6a: the open lagoon away from the reflection is a flat saturated teal slab; the S-colonnade and backdrop walls are untextured fields;
   cam03 has no deep shade (1.64x); cam06's far terrain is over-saturated and its water moirés at grazing incidence; the N-colonnade/backdrop wall sits
   at 1.26x; **33.2 fps** at the hero at 1440p, short of 45; resident **1 800.6 MB** (1.50x the Gate 1 budget) and a 660.0 MB payload, both 6b's to cut.
4. **Not re-measured on round16b: the walk clamp.** `round16_walk.json` (6c round one, before `env_trees.glb` / `env_shrubs.glb`) reads 24/24 probes,
   lowest ground **-0.702 m**, **0** below the `WATER_Z + 0.1` floor — but 6c added 1.0 M placed triangles a ground clamp may now hit, and the probe
   still runs the short 6 s / 19 m window round 15 flagged: re-run it once at 30 s on the 6c scene before delivery. Minor: the far-tree placement gate's
   worst base offset is **3.271 m** — inside its `max(3, 0.4 x height)` tolerance, but one tree sits up to 3.3 m off vertically.
