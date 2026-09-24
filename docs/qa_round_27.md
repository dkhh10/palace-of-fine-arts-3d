# QA round 27 — Phase 10 gate on the Cycles master (Opus xhigh, 2026-09-24)

**Verdict: PHASE 10 GATE PASSED — hero (cam01) 4.26 (+0.21 vs QA 26) ≥ 4.05, no new blocker.** The column tint, the water and the hero cypress each move the hero toward ref 169 on its measured boxes and in the tiles; the shelved atlas is an exact no-op on screen (stone pixels unmoved). Two Phase 10 regressions are residuals, not blockers: the rose shafts go violet/mauve where cam02 and cam06 see them in shade, and the new cypresses read blue-grey in shade and lime in sun.

Inputs: `renders/qa_comparisons/cycles_p10/cam0N_1080_32spp.png` (hero also 64 spp; rebuilt Phase 10 master_delivery.blend) vs `cycles_p9/` (same spp; its cam06 predates ENV R3, QA 26 §3); ref 169 warped into the hero frame (`mat_projection.warp_ref169`) and the canonical refs of `scripts/qa_cameras.py`. Tools `scripts/qa_r27_probe.py` (diff / movemap / stone / cam02 / shafts), `scripts/qa_r27_tiles.py` (tiles / gate), `scripts/qa_r27_rays.py`, and `scripts/mat_p10w_measure.py` re-run on these frames. Logs `renders/logs/qa_r27_{names,rays,probe,hero_boxes}.log`. Sheet `renders/qa_comparisons/round27_gate.png`.

## 0. Gate checks
**Name sweep** (`qa_name_sweep.py` on master.blend via blender_run.sh): **520 exempt, 0 hits — PASS**; the new ENV cypresses / leaf cards add no placeholder-shaped names.
**Ray-cast openings** (`qa_r27_rays.py`, **95 rays, 0 fails — PASS**): hero bay 0 z 16-22 (5 pass-through to the inner ring / ceiling beyond the band, 1 soffit, 1 sky); cam02 bay 7 and cam03 bay 2 pass-through or soffit at every z; cam04 all 8 inner bays: sky, the far wall or the vault soffit at its radius; cam03 colonnade fan (18 rays through the intercolumniation): first hit always ≥ 151 m out (north colonnade, rotunda inner ring, trees, sky) against a rotunda wall 58.6 m away — no near face in any opening.
**Full-resolution tile review** (3x2 tiles of 640x540 per station, all 36 viewed at 100 %). New:
1. **cam02**: both new cypresses read as blue spruce (crown B/G 1.06-1.15, hue 201-210) and grainy at 32 spp where ref 062 has dark green conifers; the right crown covers the left pier's outer shaft. The shaded shafts go plum -> saturated **blue-violet** (hue 288 -> **251**, sat .26 -> **.40**; ref 062 shafts hue 15, sat .31).
2. **cam06**: the shaded rose shafts turn mauve (hue 21 -> **344**, review finding 8); the two new front cypresses are blue-violet.
3. **cam01 / cam05**: the new right-hand cypress is a lime-yellow clump (conifer B/G .35 vs ref .77); ref 169's crowns are taller, darker, grey-green. **Rotunda silhouette untouched**: first sky pixel right of the rotunda identical p9 -> p10 on every row y 140-420; the crown fills only the sky gap above the colonnade.
4. **No atlas artefact anywhere**: no seam, no ghosting (people / tree shadows / sky in the stone), no texel stretching on the shafts; stone boxes move ≤ 7 levels on 0.05 % of pixels.
5. Carried, unchanged: cam03 olive near shaft, crushed ground, black paving joints; cam04 flat grey ceiling plate and gradient-free coffers; smooth pale dome (1/5/6); cam02 hard-edged foreground leaf cards and orange reed cards; cam06 faceted backdrop trees; cam05 flat backdrop wall; dark triangular patches on the hero waterline coping (already in p9).

## 1. Projection at weight 0; the column tint as a plain retune
**Hold table** (hero, p9 -> p10, ref 169, lum): attic sunlit 187.3 -> 187.5 (189.5) · attic shaded 120.3 -> 120.6 (120.0) · entablature 119.1 -> 119.5 (134.5) · vault 59.9 -> 60.0 (45.4) · drum 141.0 -> 141.3; cam04 coffers 54.0 -> 54.1. All held within 0.4 lum / 0.2°, so the round-9 anisotropy / std-ratio cannot move and were not re-run.
**Columns** (hero): QA mask 73.8/28.9/.702 -> **103.2/28.7/.616** (ref 96.8/24.8/.585); fixed crop 105.7/38.1/.744 -> **111.3/38.0/.684** (ref 112.3/33.8/.599) — closer on all six, fixed-crop hue/sat still outside the window (review finding 2). At 100 % the hero, cam03 and cam05 shafts read fluted dusty rose, not entablature brown: approach-review item 2 closes in sun, not in shade (item 1 above).

## 2. Trees, water
**NE mass** (p9 -> p10, ref): conifer luma 61.5 -> **100.7** (107.9), sky share 58.7 -> **45.5 %** (34.8), dark 15.4 -> 17.3 % (15.2), B/G .85 -> .35 (.77). **Willow box 2**: dark 28.4 -> 29.2 % (8.9), leaf luma 52.8 -> 74.6 (155.1) — still a dark hedge.
**Water, reflection box**: Lx 12.4 -> **6.7** (7.9), aniso 7.58 -> **1.96** (2.36), sat .214 -> **.383** (.403), R-B +27.9 -> **+50.2** (+77.2), lum 124.0 -> 120.2 (162.1), dark share 10.4 -> 6.4 % (16.2, away). **Near-water** moves toward ref on all three vs Phase 9 (lum 124.8 -> 118.7 / 103.6, hue 204.7 -> 195.9 / 187.4, sat .184 -> .193 / .229). cam06 lagoon hue 44.6 -> 54.7, sat .135 -> .203 (olive). Tiles: the reflection breaks into streaks; the foreground is a regular wind-wave field where ref 169 is near-calm.

## 3. Regression, cycles_p10 vs cycles_p9 (moved = 8x8 block mean > 4 levels; 32 vs 64 spp of one frame moves 5.4 % of blocks but 37 % of pixels)
| st | MAE % | moved blk | luma ratio | explained by |
|---|---|---|---|---|
| 01 | 4.645 | 42.6 % | 0.998 | water (86.8 % of the bottom third), shafts, cypress, shore leaves |
| 02 | 3.011 | 22.5 % | 0.967 | cypresses (x 160-640 sky 167 -> 65 lum), shafts, leaves, water |
| 03 | 0.390 | 6.0 % | 1.006 | arch shafts 27.7 %, leaf grade 11.4 %, hedges 9.6 %; near colonnade shafts 0.02 % |
| 04 | 0.061 | 0.37 % | 1.002 | noise |
| 05 | 3.574 | 32.3 % | 1.004 | water (77.5 % of bottom third), shafts, cypress, planting |
| 06 | 1.584 | 43.7 % | 1.006 | lagoon, leaf grade on every crown, the stale-p9 ENV R3 city tiles |
Every move is explained by a Phase 10 change.

## 4. Scores (QA-17 rubric, six rows, station = mean; Phase 10 row moves on the QA 26 baseline, read on the Cycles master; mobile not scored)
| st | rows moved | QA 27 | Δ QA 26 |
|---|---|---|---|
| 01 | material +0.5, water +0.5, foliage +0.25 | **4.26** | **+0.21** |
| 02 | material -0.25 (violet shafts); foliage 0 (right place, wrong colour) | **3.51** | -0.04 |
| 03 | material +0.25 (rose arch shafts) | **3.12** | +0.04 |
| 04 | — | **3.05** | 0 |
| 05 | material +0.25, water +0.25, foliage +0.25 (ref 063 has the dark cypress right of the rotunda) | **3.37** | +0.13 |
| 06 | water +0.25 (olive lagoon), material -0.25 (mauve shafts) | **3.15** | 0 |

## 5. Residuals for docs/delivery.md "Phase 10"
1. **NEW** rose shafts violet in shade (cam02 hue 251 / sat .40, cam06 hue 344; sunlit ref hue 15 / sat .31) from the col-hue -10 / COL_VALUE x1.22 retune, the two steps uncoupled in code (review carry 6) — **MATERIALS**.
2. **NEW** cypress colour: blue-grey in shade (B/G 1.06-1.15), lime in sun (.35 vs .77), grainy; cam02 crown covers the left pier shaft; levers are shading / density, not albedo (review 5) — **ENV / MATERIALS**.
3. **NEW** hero willow still a dark hedge (box 2 dark 29.2 vs 8.9 %, leaf luma 74.6 vs 155) — **ENV / MATERIALS**.
4. **NEW** water: dark gaps 6.4 vs 16.2 %, reflection lum 120 vs 162, regular wave field vs a near-calm photo — **MATERIALS**; murk Cycles-only, `web/src/water.js` does not carry it (review 4a/b) — **VIEWER**.
5. **NEW** web parity: leaf grade lost in glTF export (review 4c), impostor rebake and EXPM LOD1_thin rows owed — **EXPORT**; Phase 6 parity refs stale for water / columns / foliage, re-render before the next viewer score — **LEAD / LIGHT**.
6. **NEW** projection: registration does not hold (held-out 20.4 px), ORN reliefs without UVBake, colonnade uncovered, weight-0 atlas still costs two samples per concrete shader; the concrete stays one uniform mottle (approach-review item 1) — **MATERIALS / ARCH**.
7. **NEW** ENV gate debt: shadow / frame gates at CROWN_R (real crown 2.4x), `P10R2_WIDEN` keyed on the note string, willow_03 0.3 m inside the podium ring — **ENV**. Hero waterline coping triangles (since p9) — **ENV**.
8. **Carried from QA 26, unchanged**: 4K dark sliver above the S entablature (**ARCH / LIGHT**); `cycles_p9/cam06` stale (**LEAD**); cam03 olive shaft / crushed ground / black joints (**MATERIALS / LIGHT**); cam04 flat coffers and ceiling plate (**ARCH / MATERIALS**); smooth pale dome with meridian seams (**MATERIALS**); faceted aerial trees, backdrop wall / slabs, cam02 foreground cards and orange reeds (**ENV**); station 3 warm excess, cam05 p10, far-crown over-brightening, the cam06 viewer moiré (absent in Cycles p10), 45 fps, walkProbes 0 (**VIEWER / BAKE**); the user's Safari hero screenshot and iPhone walk (**LEAD**).
