# QA round 11b — Phase 6 **Gate 1** re-check after the two blockers, 2026-09-15. **GATE 1: FAIL.**

Scored on the lead's 15:31 capture of the merged export (`ec4832b`), six stations 1920x1080, `?billboards=0`, neutral grey + the ORN normal/AO bakes, `direct` lighting, water reflector on. **Geometry rows only**, each station against the Phase 5 render named in `gate1_pairs.json`. No Blender and no Chrome ran. The six cam01 tiles in `renders/web/tiles/` were **stale (14:42, the round-11 frame)** — re-cut from the 15:31 frame with `web/tools/gate1_sheets.py --stations 1` before viewing.
New: `scripts/qa_r11b_probe.py` (`probe` = which exported mesh covers a pixel, from the glTF node tree and the viewer's own logged camera matrices; `boards` = per-station coverage of the exported far-tree quads) and `scripts/qa_r11b_gate.py` -> `renders/web/round11b_gate.png`.

## 1. The two blockers

**B1 backdrop `texCoord = -1` — FIXED.** All four Gate 1 glTFs carry **zero** negative `texCoord` (arch 13 / orn 33 / env 12 / ground 4 materials checked); the ten `MAT_EXP_ENVBD__*` are plain grey factors with no probe texture — the stronger form of the fix. Corroborated three ways: the page log has **no shader error and no `useProgram` warning** (round 11: one `VALIDATE_STATUS false` + 256 warnings), the program count is **12, was 13**, and the backdrop is visibly there — at cam06 the city blocks, roof planes, lawn and the hill/forest ridge fill the upper right where round 11 had a grey void, at cam05 the horizon is back, at cam01 the stepped city mass reads at the tile r1c1 / r1c3 horizon. 151,737 placed tris draw again (`env.glb` 679,779 + `ground.glb` 113,043 = the 792,822 ENV total).

**B2 voxel-remeshed attic panels — FIXED.** `export_set.json`: `voxel_remeshed` **empty**, `orn_lo_from_lod1` records the three panels built from the Phase 5 `_LOD1` (35,912 / 35,651 / 35,823 -> **7,999** tris, exported bbox delta 8.8 / 5.6 / 4.2 mm against their own source). At 100 % at the three places round 11 named: **cam01 tile r1c2** — the figure procession is continuous, no black voids, no speckle; **cam02 (690,165)-(890,290)** — robed figures, raised arms and the panel frame intact and legible against the Cycles reference; **cam05 (700,130)-(1200,220)** — the whole band reads as continuous relief on both faces. Residual: slightly faceted against the Cycles frame's softer read, which is what an 8 k lo plus a normal map looks like. Accepted.

## 2. cam01 tile pass (3 x 2 at 100 %) and the opening test

| round-11 item | state | evidence |
|---|---|---|
| QA-11-1 r1c1 colonnade-roof canopy sparse | **OPEN** | far-tree list; with the quads off the roof line is bare. Gate 3. |
| QA-11-2 r1c2 attic relief torn | **FIXED** | continuous relief, no voids |
| QA-11-3 r1c3 south colonnade canopy absent | **OPEN** | same cause as QA-11-1. Gate 3. |
| QA-11-4 r2c1 slabs over the colonnade shore | **OPEN** | **re-attributed**: exported `ENV_treeboard_*`, not the viewer quads |
| QA-11-5 r2c1 water a ripple-free mirror | **VIEWER (Gate 4)** | the boards reflect as hard rectangles (r2c1, r2c3) |
| QA-11-6 r2c2 main-arch opening covered | **OPEN** | now **44.5 %** of the opening box (917,465)-(1000,620), was 37.4 % |
| QA-11-7 r2c2 shore planting / podium hidden | **OPEN** | same boards; `probe` at (840,620) -> `ENV_treeboard_120` at 54.5 m |
| QA-11-8 r2c3 stylobate + riprap a flat slab | **OPEN** | same boards; the left half of the tile is one flat field |
| QA-11-9 cam04 ORN ceiling sliver | **OPEN** | unchanged, see §3 |
| QA-11-10 cam02 / cam05 attic panels destroyed | **FIXED** | see §1 |
| QA-11-11 backdrop never draws | **FIXED** | see §1 |
| new, r1c3 / cam06 | note | backdrop blocks and hill/forest are untextured stepped masses and faceted blobs — Gate 2 materials |

**Ray-cast opening test by eye, cam01 main arch: PARTIAL, unchanged.** Clear sky through the top of the opening, and in the central strip (frame x 937-999) the far interior wall, the far ground and a shrub — the far side of the opening, exactly as Phase 5; **no face of the near vault, rib plate or archivolt intrudes.** But the lower 44.5 % of the opening box is still an opaque placeholder 54-55 m from the camera, in front of the building, so the far side below the springline stays unjudgeable. The board-mask outlines land exactly on the hard vertical edges of every slab in the opening — that is how the attribution below was confirmed.

## 3. The blocking defects

**QA-11b-1 (BLOCKER, export).** `?billboards=0` suppresses only the **viewer's** 127 `WEB_far_tree_billboard_*` quads (page log: "127 far-tree quads suppressed"). The export ships **its own 127 far-tree placeholders inside `env.glb`** — `ENV_treeboard_000..126`, `kind: "tree_board"`, two triangles, material `MAT_EXP_treeboard` (grey, **no `alphaMode`, so OPAQUE**), axis-aligned, scaled to the tree's width and height (`export/gate1_set.py` ~L569). Projected exactly (`scripts/qa_r11b_probe.py boards`, an upper bound before the depth test):

| station | 01 | 02 | 03 | 04 | 05 | 06 |
|---|---|---|---|---|---|---|
| exported board coverage of frame | **16.0 %** | 19.7 % | 23.2 % | 0 % | **25.5 %** | 19.6 % |

The same 16 % of the hero that round 11 measured for the viewer quads, in the same places, for the same 127 trees: the re-capture changed nothing a geometry score depends on. Nor are they distant impostors — the widest are 42.2 x 30.9 m, 43 of 127 are over 20 m wide, and **94 of the 127 far-list trees are within 40 m of the walk path** (some 4-12 m). The shore planting, podium base, riprap, benches and colonnade stylobate — everything Scale cues is scored on — sit behind them at five of the six stations.

**QA-11b-2 (export / gate tooling).** The sweep pattern (`placeholder|proxy|blocker|fill|occlud|block|dummy|temp|card`) has no `board`, `impostor` or `billboard` term, so `export/name_sweep.py` reports **2540 objects, 0 hits, PASS** while 127 `kind: "tree_board"` placeholders are in the render. This round's sweep PASS is a false negative.

**QA-11b-3 (export / viewer).** With `?billboards=1` — the default, and how round 11 was captured — the same 127 far trees draw **twice**: once as the exported boards, once as the viewer's camera-facing quads.

**QA-11-9 (BLOCKER 2, export / ORN), unchanged.** cam04 (400,80)-(600,350) at 100 %: a long thin normal-mapped wedge crosses the ceiling coffers with a second loose triangular shard beside it. It is on the building, at a QA station, in the gate whose purpose is to catch decimation artefacts, and it is absent from the Phase 5 frame.

## 4. Score table — geometry rows only (Phase 5 round 09 / round 11 / **round 11b**)

| row | 01 hero | 02 NE 3/4 | 03 colonnade | 04 ceiling | 05 S lawn | 06 aerial |
|---|---|---|---|---|---|---|
| Silhouette match | 4 / 4 / **4** | 3.5 / 3.5 / **3.5** | 2.5 / 2.5 / **2.5** | 3.5 / 3.5 / **3.5** | 3.5 / 3.5 / **3.5** | 4 / 3 / **4** |
| Proportion | 4 / 4 / **4** | 3.5 / 3.5 / **3.5** | 3 / 3 / **3** | 3.5 / 3.5 / **3.5** | 3.5 / 3.5 / **3.5** | 3.5 / 3.5 / **3.5** |
| Ornament fidelity | 4 / 3.5 / **4** | 4 / 3 / **4** | 3 / 3 / **3** | 3 / 2.5 / **2.5** | 3.5 / 2.5 / **3.5** | 2.5 / 2.5 / **2.5** |
| Repetition visibility | 3 / 3 / **3** | 2.5 / 2.5 / **2.5** | 2 / 2 / **2** | 2.5 / 2.5 / **2.5** | 2.5 / 2.5 / **2.5** | 2.5 / 2.5 / **2.5** |
| Scale cues | 3.5 / 3 / **3** | 3 / 2.5 / **2.5** | 2.5 / 2.5 / **2.5** | 3 / 3 / **3** | 3 / 2.5 / **2.5** | 3 / 2.5 / **2.5** |
| **average (delta vs Phase 5)** | **3.60 (-0.10)** | **3.20 (-0.10)** | **2.60 (0.00)** | **3.00 (-0.10)** | **3.10 (-0.10)** | **3.00 (-0.10)** |

**Numeric parity passes for the first time**: every row is within 0.5 of its Phase 5 value — the three rows that broke it in round 11 (cam06 Silhouette, cam02 and cam05 Ornament) are restored by B1 and B2. **It is provisional**: five rows sit exactly at the -0.5 limit and four of them (Scale cues at 01, 02, 05, 06) are scored on frames where a placeholder covers 16-26 % of the image, which the round-11 rule forbids. Silhouette re-measured against the Phase 5 Cycles hero: **scale 1.0000, dx 0.0, dy 0.0, apex delta 0.00 %H**, apex row 84 and corner-top row 209 in both — the attic rebuild did not move the outline.

## 5. Budget and performance — PASS on every line

Placed tris ARCH **844,554** / ORN **1,099,192** / ENV **792,822** = **2,736,568** of 3.0 M (the viewer logs ORN 1,097,468 after gltfpack welding); 154 draw-call batches, **140 inside the cam01 frustum** (budget 400); unique 902,355 tris over 140 meshes. 1440p, 120 frames after 24 warm-up, ANGLE Metal / M2:

| station | 01 | 02 | 03 | 04 | 05 | 06 |
|---|---|---|---|---|---|---|
| draw calls | 197 | 191 | 201 | 78 | 187 | 203 |
| `renderer.info` tris (M) | 5.24 | 5.11 | 5.36 | 2.57 | 5.00 | 5.39 |
| GPU cost ms median / p95 | **1.5** / 3.0 | 1.4 / 1.9 | 1.5 / 2.6 | 0.5 / 1.1 | 1.4 / 2.7 | 1.5 / 2.7 |
| presented ms (median) | 16.7 | 16.6 | 16.6 | 16.8 | 16.6 | 17.2 |
| uncapped fps | 667 | 714 | 667 | 2000 | 714 | 667 |

The hero costs **1.5 ms of the 22.2 ms a 45 fps frame allows — 6.8 % of the budget** (round 11: 2.1 ms, with 68 more draw calls for the viewer quads). Presented time is 60 fps vsync, not a ceiling. `renderer.info` triangles are ~1.9x the placed count because the **planar water reflector draws the scene a second time**. Resident **1.016 GB** (textures 545 MB, render targets 438 MB, geometry 33 MB) against the 1.2 GB plan. Load **2.54 s for 206.0 MB**, `orn.glb` 154.1 MB of it (still the 6b payload hand-off).

## 6. The sRGB re-encode — in the packer, not in the pixels

`gltf_pack.sh` now defaults to `--assign_oetf srgb` with only data maps linear and writes 85 KTX2 (was 81), but the re-encode **cannot be observed in this capture**: cam04 — the one station with no boards and no backdrop, so nothing else changed — is pixel-identical to round 11 (frame mean **88.51 -> 88.52**, a ceiling patch identical to 4 decimals, 0.22 % of pixels differing at AA level), and the frame luma ratios move only where geometry changed (01 1.205 -> 1.230, 02 1.529 -> 1.780, 06 2.246 -> 3.040; 03 8.576 -> 8.396, 04 2.176 -> 2.177, 05 1.495 -> 1.493). Either the viewer never sampled a re-encoded map or the tag never affected it; the export owes a pixel-level proof at Gate 2. **Either way the tonal rows stay unscored** — a neutral-grey pass against a full-colour Phase 5 render makes every luma ratio in `gate1_pairs.json` a sanity check, never a metric.

## 7. Verdict

**GATE 1 FAIL.** Blocking defect: **the export ships its own 127 opaque far-tree placeholders, `ENV_treeboard_000..126` in `env.glb`, which `?billboards=0` does not touch; they cover 16.0 % of cam01 (44.5 % of the main-arch opening) and 19.7 / 23.2 / 25.5 / 19.6 % of cam02 / 03 / 05 / 06, hiding the shore, podium, riprap and stylobate that Scale cues and the opening test are scored on.** Owner **export**. One-line fix: give the viewer a `treeboards=0` switch (hide every object named `ENV_treeboard_*`) and re-capture the six stations with both placeholder sets off — and add `board|impostor|billboard` to the name-sweep pattern so they can never pass as 0 hits again. Blocker 2, owner **export / ORN**: re-decimate the cam04 ceiling mesh that carries the QA-11-9 sliver, or rebuild its lo from the LOD1 as the attic panels now do.

Everything else is in good shape and both fixes landed cleanly: budget, draw calls, GPU cost, resident memory, a silhouette identical to the Phase 5 hero, a backdrop that draws, attic relief that reads as relief, and — once the placeholders are out of the frame — a score table whose every row is within 0.5 of Phase 5.
