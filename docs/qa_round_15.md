# QA round 15 — Phase 6 **Gate 4, round two**, 2026-09-17. **6a PARITY REACHED** (45 fps still not met)

Scored on `round15` (`phase6-viewer` @ 43b1e0a, 1920x1080, manifest v4 with `lightmaps.instance_irradiance`,
`lighting=baked&post=all&probe=1&impostors=1&water=1&reflset=orn&billboards=0&treeboards=0&t=0`) against the `round15nopost` control, the round-14
capture and the references (station 1 the Phase 5 Cycles hero, 2-6 `renders/previews/qa/round13_0N_*_cycles.png`). No Blender, no Chrome. Tools:
`scripts/qa_r15_probe.py` (imports `qa_r13_probe` unchanged, registers the round-15 triple, adds `bloom / loading / delta`) +
`scripts/qa_r15_gate.py`. Capture clean: **0 page errors** (only 404 is `favicon.ico`); the log confirms 16/16 lightmaps, 988/988 slots, **1 379/1 379
instance placements over 25/25 nodes**, 127 treeboards hidden, ripple "8 waves 1.20-0.034 m".

## 1. Parity per station, and the hero boxes
| station | r15 | r14 | ref | ratio (r14) | MAE r14 -> r15 |   | box, `post=all`/ref | round15 (r14) | read |
|---|---|---|---|---|---|---|---|---|---|
| 01 hero | 133.2 | 129.0 | 140.0 | **0.95x** (0.92x) | 27.9 -> **24.6** |  | hero shade band | **0.99x** (1.02x) | holds |
| 02 NE 3/4 | 107.7 | 101.1 | 100.4 | **1.07x** (1.01x) | 24.5 -> **23.1** |  | sunlit attic **hold** | sat **0.87x** (0.80x) | under 0.89x |
| 03 colonnade | 80.9 | 81.8 | 49.0 | 1.65x (1.67x) | 36.4 -> **35.9** |  | S-colonnade wall | mid **0.44x** (0.40x) | worst box |
| 04 ceiling | 70.6 | 70.7 | 63.4 | 1.11x (1.11x) | 13.10 -> 13.08 |  | N-col / backdrop wall | **1.26x** (1.00x) | **new regression** |
| 05 south lawn | 152.8 | 156.8 | 151.2 | **1.01x** (1.04x) | 22.3 -> **20.3** |  | capital row | 1.00x, std **0.85x** (0.69x) | contact shade back |
| 06 aerial | 101.0 | 77.8 | 100.9 | **1.00x** (0.77x) | 37.1 -> **18.7** |  | entabl. / columns / vault | 1.04x / 1.07x / **1.13x** (1.25x) | over-lift halved |
|  |  |  |  |  |  |  | water refl. strip | **0.99x** (0.90x), hp9 2.08x | §2 |
|  |  |  |  |  |  |  | cam05 pier / cam04 coffer | sat **0.84x** (0.72x) / 1.02x | washed less / closed |

MAE falls at all six; cam06 is the round (the derived murk turns a near-black lagoon into a lagoon). cam02 is the only station whose *level* drifts
away (1.01x -> 1.07x) while its MAE improves — its near water is now brighter than the reference's; cam03 and cam04 are untouched by round 7 (cam04's
boxes are bit-identical to round 14). **QA-13-1 holds closed** — band `20 520 540 645` B > R+20 **0.2 %** (Cycles 0.0 %, gate 3.9 %); cam06 4.8 % (ref
10.9 %). **QA-12b-1** G>R: cam02 7.4 % (ref 2.2), cam06 1.6 % (1.4), cam05 8.5 -> **6.3 %** (6.0), cam01 0.3 % (0.1) — flat to better, post-off still
19.7 / 21.5 %, so still the airlight. **QA-12-4** shaft CV south 0.327 -> 0.338, north **0.361 -> 0.248** (Phase 5 0.469 / 0.539): the north run
flattens.

## 2. QA-14-1 water — **largely closed**, one residual
| measure, cam01 | round14 | **round15** | reference | acceptance |
|---|---|---|---|---|
| open-water row high-pass | 0.97 | **6.92** | 13.23 | 0.5x-2x -> **PASS** (0.52x) |
| open-water row/col | 0.72 | **3.71** | 3.24 | streaks not blur -> **PASS** |
| reflection mass lum / hue | 74.6 (0.85x) / 43.3 | **88.1 (1.00x)** / 45.2 | 88.2 / 42.4 | **PASS** (+2.8 deg) |
| open water lum | 66.8 (0.57x) | **88.2 (0.75x)** | 118.0 | short |
| **open water hue / sat** | 200.2 / 0.326 | **195.6 / 0.363** | 144.8 / 0.041 | within 20 deg -> **FAIL** (+50.8) |
| Fresnel far -> near | 72.7 … flat at 41 | **84.0 93.5 95.5 80.8 70.3 67.1 67.2 65.1** | 96.5 … 60.4 | slope -> **PASS** |

The hard reflection line is gone and the reflection mass is a field of golden streaks at 100 %, reading as the reference does. What did not: the water
*away* from the reflection — the 100 % strip (composite row 3) is a flat, featureless, saturated teal slab where Cycles has fine crests everywhere.
The ripple is visible only where something bright is reflected in it.

## 3. QA-14-2 / -3 / -4 / -5
**QA-14-3 cam06 CLOSED.** near 60 m 43.4 -> **80.6** (ref 82.6, 0.98x), p10 **3.6 -> 69.1** (ref 58.0); shoreline 52.2 -> **89.0** (0.92x); far 400 m+
1.02x with sat **0.622 -> 0.343** (ref 0.169, 3.7x -> **2.0x**). The far terrain's own colour is the residual — bake/export, as the viewer attributed
it. **QA-14-2 cam03 FLAT.** near 10-25 m p10 **52.5 -> 53.1** against the reference's 17.0, frame 1.67x -> 1.65x; post moves the box 0.2 luma.
Surfaces with no baked light on a single-point probe carry no occlusion. Bake/export, post-6a. **QA-14-4 bloom, at its ceiling.** capital-row std
**0.69x -> 0.85x** (gate 0.85x **PASS**); dome-cap sky ring +12.0 -> **+5.1** over the reference, post-on minus post-off there **+7.65 -> +0.76** —
the halo is gone. S-colonnade mid 0.40x -> **0.44x** (gate 0.70x **FAIL**) but post-off is 0.51x; sunlit-attic sat 0.80x -> **0.87x** (gate 0.89x
**FAIL**), post-off ceiling 0.887x. Both ceilings are pre-post, so bloom is done: it now costs 0.013 sat where it cost 0.084. **QA-14-5 foliage,
half.** cam02 near trees 84.5 -> **104.5** (ref 106.0, **0.99x**), cyan gone, 1 379/1 379 placements bound; hue **57.7 vs 102.4 (-44.7 deg**, was
-45.9) and G>R 37.4 % vs 70.9 % stay flat — the cards' albedo, not the irradiance. cam01 shore planting sat 0.515 -> 0.638 (ref 0.415) is a small
regression; cam06 shoreline hue lands.

## 4. The cam01 six tiles at 100 % (`renders/web/tiles/round15/`, viewer beside the same crop of Cycles)
| tile | what is visible |
|---|---|
| r1c1 | Roof impostor canopy still thin and wiry, **white specks on the alpha-tested leaf edges** (fewer than r14). |
| r1c2 | **Halo gone**, dome silhouette clean; structure, frieze, dentils, capitals, coffered vault correct. Shade side still flatter than the reference (less contact shade under each cornice), the reference's violet shade cast missing. |
| r1c3 | South attic warm ochre, gulls and balustrade right; the **colonnade roof strip reads a brighter, more saturated blue** than the reference's grey-blue; the left impostor a flat olive mass beside a branched reference tree. |
| r2c1 | Water transformed — streaked golden reflection over rippled water. Still: **backdrop wall one untextured mustard field**, shore planting **hard gold angular leaf confetti**, one shrub group a **grey-blue smeared impostor blob**, white/violet speckles on the water, lower lagoon a **saturated cyan slab**. |
| r2c2 | Reflection streaks close to the reference in character, but the ripple is more **regular / comb-like** than its irregular crests, the gaps between streaks are cyan where Cycles is near-black olive, and near shrubs are **blue-grey blurred blobs** over **black gaps in the leaf cut-outs**. |
| r2c3 | **QA-12b-2 at 100 %**: the S-colonnade wall a flat cream field with hard-edged pale leaf cards pasted on it, against a textured shaded reference wall — the worst material defect in the hero. The hard reflection line is **gone**; the bottom ~15 % of the water smooths out again. |

No lightmap seam, slot bleed, texel blockiness, encoding banding, z-fighting, filled opening, missing ornament or placeholder-grade object in any of
the six. **Name sweep (restated, no Blender run):** export set **0 to explain** (Gate 3 r2 sweep, docs/status.md 2026-09-15/16); membership unchanged
since — the only re-export was `env.glb`'s COLOR_0 re-encode and the `instance_irradiance` block. The 127 `ENV_treeboard_*` carriers stay in `env.glb`
and stay hidden (`?treeboards=0`), impostors drawing in their place: the standing named exception.

## 5. Definition of done 6a
| row | 01 | 02 | 03 | 04 | 05 | 06 |   | row | 01 | 02 | 03 | 04 | 05 | 06 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Silhouette | 4 | 3.5 | 2.5 | 3.5 | 3.5 | 3.5 |  | Water reflection | **3.5** (2.5) | n/a | n/a | n/a | **2.5** (2) | **3** (2) |
| Proportion | 4 | 3.5 | 3 | 3.5 | 3.5 | 3.5 |  | Repetition | 3.5 | **3** (2.5) | 2.5 | 2.5 | 2.5 | 2.5 |
| Ornament | 4 | 3 | 3 | 3 | 3 | 2.5 |  | Scale cues | 3.5 | 2.5 | 2.5 | 3 | 3 | 3 |
| Material realism | 3.5 | 3 | 3 | 3 | **3** (2.5) | **3** (2.5) |  | **round 15** | **3.72** | **3.00** | **2.56** | **2.88** | **2.94** | **2.83** |
| Edge wear | 3.5 | 2.5 | 2 | 1.5 | 2.5 | 1 |  | round 14 | 3.61 | 2.94 | 2.56 | 2.88 | 2.83 | 2.56 |
| Lighting mood | 4 | 3 | 2 | 3 | 3 | **3.5** (2.5) |  | round 09 (Phase 5) | 3.67 | 2.94 | 2.56 | 2.81 | 3.06 | 2.67 |
|  |  |  |  |  |  |  |  | **delta vs Phase 5** | **+0.05** | **+0.06** | **0.00** | **+0.07** | **-0.12** | **+0.17** |

Round 14 in brackets where a row moves. Five of six stations gain, none loses; round 13 was 3.39 / 2.69 / 2.69 / 2.31 / 2.89 / 2.33.

| 6a criterion | result |
|---|---|
| every station within 0.5 of Phase 5 | **PASS**, worst **-0.12** (cam05); four of six now above Phase 5 |
| none below 2.5 | **PASS** — floor cam03 2.56; cam06 leaves the floor (2.56 -> 2.83) |
| water reflects the rotunda at the hero | **PASS**, and for the first time as broken ripple streaks, not a mirror |
| walk clamp, never in the lagoon | **PASS** — 24/24 probes, **0 below the `WATER_Z + 0.1` floor** (lowest -0.702 m); lagoon headings refused (st1/180 343 of 361, st1/270 341, st2/0 200, st2/270 159, st5/180 271, st5/270 307). **Caveat:** this probe ran **6 s / 19.3 m** per heading against round 14's 30 s / 96 m, and round 14's st1/270 violation happened at t ~ 12.5 s, so only 2 of the 3 round-14 failures fall inside the re-tested window. Re-run once at 30 s, post-6a |
| loading screen with a correct total | **PASS** — planned **640 126 514 B = loaded**, bar ends at **100.0 %** (r14 122.3 %), 55 off-plan urls folded in. The denominator is still discovered progressively (the screenshot reads `156.2 / 523.5 MB — orn.glb`), so the bar runs a few points fast early; by design it can lag but never exceed 100 % |
| >= 45 fps median at 1440p | **NOT MET** — **28.2 ms = 35.5 fps** at the hero (r14 28.9 / 34.6); 31 / 30 / **44** / 33 / 31 fps at 02-06. GPU median 2.5 ms (p95 30.3), 279 draws, 4.14 M tris, resident **1 677.9 MB** (tex 1 171.6 + RT 443.8 + geo 62.5), load 640.1 MB in 6.11 s. Same vsync-quantisation attribution as round 14; `?bloomres=half` is the untaken lever |
| deterministic headless screenshots | **PASS** — `t=0`, `__pfaReady`, no input, 0 page errors, six stations in one command |

## 6. Verdict — **6a PARITY REACHED**
All five parity criteria hold: every station inside the 0.5 window (worst -0.12), none below 2.5, the hero water reflects the rotunda *and* now
ripples, the walk clamp holds on 24/24 probes, the loading bar carries a correct total. The one 6a line still open is the **>= 45 fps target: 35.5
fps** — a target in CLAUDE.md's 6a list, not a parity criterion, reported with the attribution accepted at round 14; and this is the second round
after Gate 4, so the stopping rule closes 6a here either way.

**Residual defects for the delivery notes** — what a walkthrough viewer sees that the Cycles frames do not:
1. The open lagoon away from the reflection is a flat saturated teal slab (hue +51 deg, sat 8.9x); the ripple exists only inside the reflection and its crests are more regular than a real lagoon's.
2. The S-colonnade wall and the backdrop wall behind the north bays are flat untextured fields (mid 0.44x; the single-point probe) with hard-edged leaf cards pasted on them, the cards showing black gaps at 100 %; near shrubs and reeds read as blue-grey blurred impostor blobs, and near-tree hue is 45 deg warm of Cycles (albedo).
3. cam03 has no deep shade (p10 3.1x the reference); cam06's far terrain is 2.0x over-saturated. Both bake-side.
4. Leaf-edge bloom specks on the roof impostor canopy; the colonnade roof strip reads bluer than the reference; the probe-lit backdrop wall brightened this round, 1.00x -> **1.26x** of Cycles (new, minor, viewer/probe side).
5. 35.5 fps at 1440p, not 45; `?bloomres=half` and the Reflector's second traversal remain the named levers.

No re-bake, re-export or geometry change is requested by this round; items 2-3 are bake/export work and are post-6a. Composite:
`renders/web/round15_gate.png`.
