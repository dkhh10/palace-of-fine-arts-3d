# QA round 17 — Phase **6c, the foliage gate**, round two of two, 2026-09-17. Verdict: **6c CLOSED WITH RESIDUALS**

Scored on `round16c` (main @ 401e6dd; the recaptured build after the r3 review fixes, 1920x1080 stations / 2560x1440 perf, every round-3 default on:
`crownint 0.30/0/1/1.05/0.85/0.50`, `cardint 0.20/0.30`, `leafgate 0.45`, `impint 0.90/0.015`, `cardenv 0.30`, `foliagebias 0.8`, `walkupmesh 15`,
`impmod=full`, `fartreemesh=12`, `t=0`) against the `round16cnopost` control, `round16b`, and the references (station 1 the Phase 5 Cycles hero,
2-6 `renders/previews/qa/round13_0N_*_cycles.png`; 3 and 5 keep their round-15 caveat). No Blender, no Chrome. Tools: `scripts/qa_r17_probe.py`
(imports `qa_r16_probe` unchanged; adds `norm mae perf17 walk`) + `scripts/qa_r17_tiles.py` + `scripts/qa_r17_gate.py`. Capture clean: **0 page errors**,
0 shader errors, ready in 6.51 s, 254/254 far-tree rows joined and lit, 145 placements modulated, 1 376/1 376 LOD1 shrubs bound. Composite
`renders/web/round17_gate.png`. The six-station tile review (§4) was written **before** decisions.md's "Viewer r3 (33903b8)" lead judgement was read; §5 is
the comparison. The two-round rule closes 6c whatever this scores.

## 1. Verdict against the 6c acceptance

| conjunct (docs/briefs/qa_round_17.md) | result |
|---|---|
| no station below its round-15 score by more than 0.1 | **PASS** — none drops at all; three rise |
| station 2 above round 15 | **PASS** — 3.00 -> **3.25** (+0.25); MAE 23.27 -> **18.38** |
| frame time within +3 ms of round 15 at 1440p | **FAIL on the pass of record / pending** — the cold pass is +4.2 and +4.8 at stations 1 and 2 (§6) |
| tiles show crowns with interior **and** shrubs at the reference level | **PASS on both, but the shrub *structure* is unchanged** (§3, §4) |

Round 3 did what QA 16 asked: the crowns have interiors, the shrub level came down, and the 3 m walk-in now reads as a canopy. Two things stop this being
**ACCEPTED**: the +3 ms conjunct cannot be called PASS from the figure of record, and CLAUDE.md's rule that the tiles govern means "shrubs at the reference
level" does not settle "foliage credible at 3 m" — at 100 % the shrub band is still broad flat angular cards at stations 1, 2, 3 and 5. **6c CLOSED WITH
RESIDUALS**; §7 names each with an owner and a one-line fix for `docs/delivery.md`.

## 2. Scores

| row | 01 | 02 | 03 | 04 | 05 | 06 |   | row | 01 | 02 | 03 | 04 | 05 | 06 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Silhouette | 4 | 3.5 | 2.5 | 3.5 | 3.5 | 3.5 |  | Water reflection | 3.5 | n/a | n/a | n/a | 2.5 | 3 |
| Proportion | 4 | 3.5 | 3 | 3.5 | 3.5 | 3.5 |  | Repetition | 3.5 | 3 | 2.5 | 2.5 | 2.5 | 2.5 |
| Ornament | 4 | 3 | 3 | 3 | 3 | 2.5 |  | Scale cues | 3.5 | 2.5 | 2.5 | 3 | 3 | 3 |
| Material realism | **4** (3.5) | 3.5 | **3.5** (3) | 3 | **3.5** (3) | 3 |  | **round 17** | **3.78** | **3.25** | **2.63** | **2.88** | **2.94** | **2.83** |
| Edge wear | 3.5 | 2.5 | 2 | 1.5 | 2.5 | 1 |  | round 16 | 3.72 | 3.13 | 2.56 | 2.88 | 2.94 | 2.83 |
| Lighting mood | 4 | **4** (3.5) | 2 | 3 | **2.5** (3) | 3.5 |  | round 15 | 3.72 | 3.00 | 2.56 | 2.88 | 2.94 | 2.83 |
|  |  |  |  |  |  |  |  | **delta r16 / r15** | **+0.06/+0.06** | **+0.12/+0.25** | **+0.07/+0.07** | 0/0 | 0/0 | 0/0 |
|  |  |  |  |  |  |  |  | delta Phase 5 | +0.11 | **+0.31** | +0.07 | +0.07 | -0.12 | +0.17 |

What moved and why. **01** Material realism 3.5 -> 4: the hero's largest remaining material error, the left-shore band, halves its excess (1.70 ->
1.47x frame-normalised) and halves its hard-edge share (6.82 -> 3.44 %, ref 1.77). **02** Lighting mood 3.5 -> 4 (the fill tree's dark core and lit shell
is the golden-hour read, and its centre/edge is now 0.393 against the reference's 0.364) and Scale cues 2.5 -> 3 (foliage depth is the only scale cue in
that frame and it now works at 3 m). **03** Material realism 3 -> 3.5: the round's worst box, 2.20 -> 1.53x with the hard-edge share down from 12.11 to
4.82 %. **05** nets zero on purpose: Material realism 3 -> 3.5 (the shore band lands at 1.02x with a *lower* hard-edge share than Cycles, 3.64 vs 4.30) is
cancelled by Lighting mood 3 -> 2.5 (the frame is now 3 % **under** the reference, 146.8 vs 151.2, its probe MAE is the only one to rise, and crowns go
blotchy near-black where the enclosure and sun-path terms stack). **04** is bit-identical to round16b. **06** holds: a 0.09x move on one band in an aerial
does not earn a half-step while the backdrop planes and the water moiré are untouched.

MAE r16b -> r16c (`qa_r17_probe frame`, full 1920x1080): 24.79 -> **24.75** / 20.48 -> **18.68** / 35.41 -> **34.80** / 13.08 -> 13.08 / 20.37 -> **21.32**
/ 18.41 -> **18.14**. The committed pair sheets (`qa_r17_probe mae`, 1280x720 panels) agree in sign at five and differ in size at station 5 (+0.28 there,
+0.95 on the full frame): **station 5 is the one station 6c made measurably worse**, and both numbers say so. Every round-14/15 architecture box is
unmoved (hero shade band 0.99x, S-colonnade mid 0.45x, attic sat 0.87x, cam04 coffer 1.02x, N-colonnade wall 1.26x); capital-row std improves 0.92 ->
**0.95x** of Cycles, which is the trees behind the capitals darkening, not the stone.

## 3. The foliage boxes, round16b -> round16c

**Crown interior — CLOSED.** Columns round16b / **round16c** / **ref**.

| crown box | centre/edge | p10 | (p90-p10)/mean | level |
|---|---|---|---|---|
| 02 fill tree `700 660 1240 950` | 0.504 / **0.393** / **0.364** | 18.6 / **5.3** / 4.1 | 2.05 / **2.33** / 3.12 | 1.28 -> **1.01x** |
| 05 lawn tree `300 580 500 870` | 0.874 / **0.924** / 0.960 | 58.9 / **27.0** / 31.7 | 1.26 / **1.72** / 1.77 | 1.19 -> **1.05x** |
| 01 shore crown `760 545 1000 690` | 0.680 / **0.491** / **0.852** | 61.4 / **20.9** / 36.8 | 1.04 / **1.71** / 1.44 | 1.18 -> **0.94x** |

Both targets the r3 brief set are met (cam02 within 0.029 of the reference, cam05 within 0.051) and every crown's level lands inside 0.9-1.1x where
round16b ran 1.04-1.28x. **The hero's crown overshoots**: its centre/edge moves *away* from the reference (0.680 -> 0.491 against 0.852) and its p10 lands
at 0.57x of the reference's — the hero's shore crowns are now darker inside than Cycles, not flatter. That is residual 2.

**Shrub and reed level — CLOSED; structure — OPEN.** Frame-normalised (each box's raw ratio divided by its station's whole-frame ratio, QA 16's definition).

| shrub / reed box | raw 16b -> **16c** | frame-norm 16b -> **16c** | hard-edge % 16b -> **16c** (ref) | leaf-green % **16c** (ref) |
|---|---|---|---|---|
| 01 shore `0 620 640 700` | 1.61 -> **1.36x** | 1.70 -> **1.47x** | 6.82 -> **3.44** (1.77) | 11.4 (17.9) |
| 01 shore S `1280 600 1900 690` | 1.28 -> **1.10x** | 1.35 -> **1.18x** | 7.57 -> **5.29** (3.38) | 10.1 (13.6) |
| 02 shore `40 860 640 1060` | 1.62 -> **1.18x** | 1.48 -> **1.12x** | 8.56 -> 8.99 (3.44) | 57.7 (88.6) |
| 02 reed clump `1380 880 1860 1070` | 1.50 -> **1.14x** | 1.37 -> **1.09x** | 6.22 -> **2.07** (1.57) | 25.1 (24.9) |
| 05 shore `200 840 1200 930` | 1.35 -> **1.02x** | 1.33 -> **1.05x** | 7.92 -> **3.64** (4.30) | 10.2 (33.4) |
| 05 W `1300 700 1900 900` | 1.11 -> **0.88x** | 1.09 -> **0.91x** | 6.79 -> **6.57** (4.06) | 18.2 (20.1) |
| 03 cards `860 620 1280 750` | 2.20 -> **1.53x** | 1.34 -> **0.94x** | 12.11 -> **4.82** (1.48) | 14.9 (26.5) |
| 06 shore planting `640 740 1280 890` | 1.12 -> **1.03x** | 1.13 -> **1.06x** | 2.02 -> **0.56** (0.20) | 34.7 (20.0) |

QA 16's 1.09-1.70x frame-normalised band becomes **0.91-1.47x**; the hard-edge share falls at seven boxes of eight (cam02's shore is the one that does
not, 8.56 -> 8.99 against the reference's 3.44). Two things the level does **not** fix: the **leaf-green pixel share** is still about half the reference's
at five boxes (cam05 shore 10.2 % vs 33.4 %, cam01 shore 11.4 % vs 17.9 %, cam03 14.9 % vs 26.5 %), and the **hero's own band is still the worst of the
eight** at 1.47x — exactly as QA 16 said, and still on the frame we deliver.

**The 3 m walk-in — CLOSED.** `tiles/round16c/round16c_walkin_tile.png`, both headings at 100 %: overlapping leaf cards at several depths, dark bark
branches crossing them, sky through the gaps. It reads as standing inside a canopy, where QA 16 found "magnified cream-white cut-outs and a few bare
sticks". One defect inside it: on the shaded heading a large minority of cards render pale grey-cream rather than dark green — the translucent back face
carries no chroma.

## 4. Tile defects (36 tiles, six stations, 3 x 2 at 100 %, each viewer tile beside the same crop of its Cycles reference)

1. **cam01.** r2c1/r2c2 the shore planting is transformed — dark green clustered masses at the reference's level where round16b had gold confetti — but
   the clusters are still flat angular cut-out lobes with several crowns repeating the same silhouette, and a **pale grey halo now reads around the darker
   crowns** (present in round16b too; the darkening made it conspicuous). r1c1/r1c3 the roof-line crowns have the right colour and some lobing but remain
   closed blobs against branched, sky-gapped reference canopies. r2c1 the N-colonnade backdrop wall is still a flat olive field with dark rectangular
   panels; r2c2/r2c3 the reflection is cooler and markedly less saturated than the Cycles gold and the open lagoon is a flat teal slab. r1c2 the rotunda
   is a close match (dome a little cooler and smoother).
2. **cam02.** r2c2 the fill tree is now a crown with a dark core, a lit shell and real gaps — the round's clearest win; no trunk or branch is visible
   through it. r2c1 at 3 m the cards are dense and at the right level but still broad flat blades, with the reeds reading over-saturated orange (the
   `MAT_reeds` 1.49 residual the export measured); the pale lavender cut-outs QA 16 flagged **match a lavender in the reference at this tile**. r1c3 the
   far tree's top is still a **solid opaque silhouette** where the reference shows sky through the twigs — unmoved by round 3. r2c3 the backdrop city
   blocks are flat cream/olive planes with a blown white edge.
3. **cam03.** r2c2 the shrub cards at ~8 m are pale angular blades against dense dark-green reference shrubs — much closer in level (1.53x from 2.20x) but
   the same shape. r1c1 the overhead tree is still a flat opaque olive cut-out. r1c3/r2c3 at 100 % the **column concrete is visibly blurred and vertically
   banded** where the reference is crisp — a texel-resolution defect this tile pass reports first. r2c1 the station still has no deep shade.
   **cam04** is bit-identical to round16b; the blown white aliasing streak on the entablature edge in r2c3 persists.
4. **cam05.** r2c1/r2c2/r2c3 the crowns have volume and the shore band sits at the reference level, but the crowns read **colder and darker** than the
   Cycles trees, the halo fringe is at its most visible here, and the shrubs are wide flat "leaf-blade" cards. Backdrop through the arches is a flat pale
   band. **cam06** r1c1/r1c3 the backdrop city blocks are flat saturated planes (the faceted low-poly backdrop trees are in the **Cycles reference too**,
   so they are a Phase 5 asset, not a viewer defect); r2c1 the water carries the same regular diagonal cross-hatch moiré at grazing incidence.
   No lightmap seam, slot bleed, texel blockiness, banding, z-fighting, filled opening or missing ornament in any of the 36 tiles; every arch the six
   stations look through is open to its far side.

## 5. Where I agree and differ with the lead's tile judgement (decisions.md "Viewer r3 (33903b8)", same capture)

**Agree on all four of the lead's calls**, and the boxes back them: the crowns have volume (three boxes at or within 0.05 of the reference), the shrubs
are darker but still card clusters (level closed, leaf-green share still ~half), the hero's left-shore band is still paler and sparser (1.47x, the worst of
eight), and some crowns go blotchy near-black where the terms stack (cam01 p10 20.9 vs the reference's 36.8 is that, measured). **Differ, three ways.**
(a) **The far-tree *tops* are a separate open item the lead's three stations did not isolate**: cam02 r1c3 and cam03 r1c1 are opaque cut-outs against
sky-gapped reference canopies, unchanged by round 3, and they are an atlas/silhouette problem, not a lighting one. (b) On "the far impostors at the
top-left are still lavender": at cam02's 100 % tile the lavender cut-outs I can see have a **matching lavender in the Cycles reference**, so I would scope
that residual to the horizon band the lead saw and not to the near cards. (c) Two defects outside the foliage that the 100 % pass makes reportable:
cam03's column texture is blurred and banded at 1 m, and station 5 is now measurably **darker than its reference** (146.8 vs 151.2 whole-frame, the only
station whose MAE rises) — the darkening is slightly over-applied, not under.

## 6. Perf, memory, walk, sweep, bare URL

**Frame time, 2560x1440, median of 120 frames.** Three passes of the identical build exist and they spread up to 3.9 ms:

| | 01 | 02 | 03 | 04 | 05 | 06 |
|---|---|---|---|---|---|---|
| round 15 | 28.2 | 32.2 | 32.9 | 22.5 | 30.4 | 32.1 |
| round16b | 30.1 | 33.5 | 32.7 | 22.7 | 31.8 | 33.5 |
| r16c warm A / warm B | 30.2 / 32.9 | 33.5 / 37.4 | 34.4 / 37.2 | 23.2 / 21.9 | 33.7 / 32.1 | 35.1 / 34.8 |
| **r16c COLD (the figure of record)** | **32.4** | **37.0** | **35.1** | **22.1** | **32.2** | **34.0** |
| **cold - round 15** | **+4.2** | **+4.8** | **+2.2** | **-0.4** | **+1.8** | **+1.9** |

On the cold pass the +3 ms gate **fails at stations 1 and 2**. It is not yet callable as a 6c regression, for one measured reason: **draw calls are
identical to round16b at all six stations and triangle counts are identical at five** — only cam03 carries more (5.59 -> **5.98 M**, the walk-up LOD1
replacing LOD2 within 15 m). Stations 1 and 2 submit exactly the geometry round16b submitted, so their +4 ms is either shader cost or the machine; round 15
was measured on a different day. The lead's same-session A/B (round-15 look / 6c look / round-15 look) settles it and is **pending**; until it lands the
honest statement is "the gate fails on the pass of record and the cause is not established". Hero **30.9 fps** cold, still short of 45. Load **664.0 MB in
6.74 s**. **Resident 1 931.4 MB** (texture 1 227.5 + render targets 443.8 + geometry 260.0) — identical across all three passes, **+130.8 MB** on round16b
and **1.61x** the 1 200 MB Gate 1 budget; every byte of the rise is the walk-up set's 472 k unique triangles. QA 16's README/decisions.md discrepancy is
fixed: 1 931.4 MB is the figure of record and it agrees with the sidecar's own `total_bytes`.

**Walk clamp, re-run as QA 16 §6.4 asked** (`round16c_walk.json`, 24 probes = six stations x four headings at **30 s**, 3.2 m/s, on the full 6c scene):
lowest ground **-0.750 m** against the `WATER_Z + 0.1` floor of **-1.20**, **0 probes below it**, 0 page errors. **Closed.** **Name sweep** (`qa_r17_probe
names`, over the export set's manifests, no Blender): only `ARCH_rotunda_inner_block`, `ENV_backdrop_fill(roof)` and the bake-side
`LIGHT_gallery_fill_north/south_##` — all named exceptions in this file; **0 new to explain**, including the round-3 walk-up set. **Bare URL** against the
station-1 preset: luma **0.9999x**, MAE 8.09/255 (the 1280x720 capture upscaled — the same resampling round16b measured at 8.23), 0 page errors, and its
boot log carries every round-3 default. **Same look, no dev defaults.**

## 7. Residual defects for `docs/delivery.md`, with owners

1. **Shrub and reed STRUCTURE — owner EXPORT.** The level, hue and edge softness are at the reference; the cards are still broad flat angular blades with
   ~half the reference's leaf-green pixel share at five boxes, worst at cam03 (1.53x at ~8 m) and cam01 (1.47x, the hero). *Fix:* a denser LOD1 card set —
   more, smaller, more varied cards per cluster — not another shading term.
2. **The darkening overshoots — owner VIEWER.** The hero's crown p10 is 0.57x of the reference's and its centre/edge moves away from it; station 5's whole
   frame runs 3 % under the reference and is the only station whose MAE rises; some crowns go blotchy near-black. *Fix:* clamp the stacked
   `impint` + `crownint` + sun-path darkening and rebalance so the frame level holds at 1.00x.
3. **A pale halo reads around the crowns — owner VIEWER.** Carried from round16b, newly conspicuous now that the crowns are dark. *Fix:* the alpha fringe
   on the impostor cut-out (premultiply / mip-bias on the atlas edge), not the lighting.
4. **Far-tree tops stay opaque — owner BAKE/EXPORT.** cam02 r1c3, cam03 r1c1: solid silhouettes where the reference shows sky through the twigs. *Fix:*
   the atlas's own alpha at the crown top, or a mesh at those distances.
5. **`MAT_reeds` reads 1.49 on 0.6 % of card pixels — owner EXPORT** (measured and deliberately left in `albedo_check.json`; moves the worst box < 0.3 %).
6. **Carried from 6a/6b, unchanged by 6c:** cam03 has no deep shade (1.64x) **and its column concrete is visibly blurred and banded at 1 m** (owner:
   materials/export, texel budget); cam06's water moirés at grazing incidence; the backdrop city blocks are flat untextured planes and their trees are
   faceted low-poly in the Cycles source too; the S-colonnade and N-colonnade backdrop walls are untextured fields (N at 1.26x); the hero's reflection is
   cooler and less saturated than Cycles and the open lagoon is a flat teal slab; **30.9 fps** cold at the hero at 1440p against the 45 target; resident
   **1 931.4 MB** (1.61x the Gate 1 budget) and a 664.0 MB payload, both 6b's tiers to cut.
7. **Open, not a defect: the same-session perf A/B.** Until `perfab_{r15look,6c,r15look2}` land, the +3 ms gate is recorded as failing on the cold pass at
   stations 1 and 2 with the cause unestablished (identical draws and triangles there).
