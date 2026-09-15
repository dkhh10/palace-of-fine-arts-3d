# QA round 11c — Phase 6 **Gate 1**, third check, 2026-09-15. **GATE 1: FAIL.**

Scored on the lead's 16:25 capture of the merged export (`2c1c7fe`), six stations 1920x1080, **`?billboards=0&treeboards=0`**, neutral grey + ORN normal/AO, `direct` lighting, water reflector on. Geometry rows only, each station against the Phase 5 render named in `gate1_pairs.json`. No Blender, no Chrome; tiles re-cut 16:11 with the frames and viewed at 100 %. New: `scripts/qa_r11c_probe.py` (`pixels`, `slabs`) and `scripts/qa_r11c_gate.py` -> `renders/web/round11c_gate.png`.

## 1. Placeholders — both sets are out of the frame

| station | 01 | 02 | 03 | 04 | 05 | 06 |
|---|---|---|---|---|---|---|
| geometric board mask (upper bound, `qa_r11b_probe.py boards`) | 16.0 % | 19.7 % | 23.2 % | 0 % | 25.5 % | 19.6 % |
| **measured board coverage of the frame** | **0 %** | **0 %** | **0 %** | **0 %** | **0 %** | **0 %** |

Three independent proofs. (a) In the **shipped** `env.glb`, `MAT_EXP_treeboard` survives gltfpack as `alphaMode MASK`, `alphaCutoff 1.0`, `baseColorFactor` alpha **0** on all 127 board primitives — every fragment is discarded. (b) The viewer also hides them by material name: page log `127 ENV_treeboard_* stand-ins hidden` + `127 far-tree quads suppressed`, `hiddenBoards: 127` in `gate1_perf.json`, and all six frames come from that one page load (`gate1_cam.json.url` carries both switches). (c) Pixels: the three largest board quads per station were flat grey when they last drew (`b828fa4^`: std **0.28-0.65**, mean 200-210) and now carry structure (std **21-51**, 79-99 % of their interiors changed). No flat grey slab is left under the mask.

**Name sweep: PASS.** `export/name_sweep.py` on `export_set.json`: **2540 exported objects, 127 exempt, 0 to explain** (`ENV_treeboard_\d+`, "Gate 3 impostor carriers, hidden in every QA capture until the impostor bake" — satisfied above). `scripts/qa_name_sweep.py` carries the same `board|impostor|billboard` pattern, so QA-11b-2 cannot recur.

## 2. The blocking defect — **QA-11c-1 (BLOCKER, export)**

**1379 of the 1536 ENV mesh nodes carry no transform and are drawn stacked at the world origin.** In `export/out/gate1/env.gltf` every `ENV_shrub_*_LOD2` node is `{"mesh": N, "name": ...}` — no `matrix`, no `translation/rotation/scale`, no parent (all 1536 nodes are scene roots) — while the 25 shrub prototype meshes are **local** (`EXPM_ENV_src_agap0_LOD2` bbox 0.87 x 0.80 x 0.65 m, base at y=0). ARCH writes a transform on 562 of 564 mesh nodes and ORN on 436 of 436; in ENV only the 127 treeboards and the 20 near trees have one. `gltfpack -mi` cannot invent what is not there, and `manifest.instancing` holds no matrices, so **25 meshes / 1379 objects / 135 880 placed tris all render at (0,0,0)** — the centre of the rotunda floor.

Measured, not inferred: the origin projects to (960,655) at cam01, (960,908) at cam02, (960,852) at cam05, (960,654) at cam06, and a foliage clump sits at exactly those pixels in the viewer and nowhere in the Phase 5 reference (`round11c_gate.png`, strip 1). At cam04 the pile is 2.4-2.9 m from the station, inside the rotunda, its leaf cards crossing the ceiling. Everywhere else the planting is **gone**: bare shore and lawn at cam02/cam05, an empty colonnade walk at cam03, an unplanted site at cam06. Rounds 11 and 11b could not see it — the 127 opaque boards covered 16-26 % of five frames exactly over the shore and podium, so QA-11-4 / -7 / -8 read as "boards hide the planting". With the boards cut, there is no planting behind them.

## 3. cam01 six-tile pass at 100 %, and the opening test

| item | state | evidence |
|---|---|---|
| QA-11-1 r1c1 colonnade-roof canopy sparse | **OPEN — Gate 3** | far-tree list; the roof line is bare with the quads off |
| QA-11-2 r1c2 attic relief torn | **FIXED** | procession continuous, no voids, no speckle |
| QA-11-3 r1c3 south colonnade canopy absent | **OPEN — Gate 3** | same cause |
| QA-11-4 r2c1 slabs over the colonnade shore | **FIXED** | boards cut; shore, quay and riprap now draw |
| QA-11-5 r2c1 water a ripple-free mirror | **OPEN — Gate 4 (viewer)** | board reflections gone, the mirror is still ripple-free |
| QA-11-6 r2c2 main-arch opening covered | **FIXED** | see the ray test below |
| QA-11-7 r2c2 shore planting / podium hidden | **OPEN — re-attributed to QA-11c-1** | the podium draws; the planting does not exist there |
| QA-11-8 r2c3 stylobate + riprap a flat slab | **FIXED** (flatness is Gate 2) | stylobate, balustrade and riprap read as modelled |
| QA-11-9 cam04 ceiling sliver | **FIXED** | see §4 |
| QA-11-10 cam02 / cam05 attic panels destroyed | **FIXED** | confirmed again at 100 % |
| QA-11-11 backdrop never draws | **FIXED** | city mass, roofs and ridge draw at 01 / 05 / 06 |
| 11b note: backdrop / hill-forest untextured | **OPEN — Gate 2** | stepped masses and faceted blobs, no texture |

**Arch-opening ray test, cam01 main arch (890,430)-(1040,650) at 100 %: PASS.** Through the opening: clear sky above the springline, then the **far** interior wall with its ledges and the far ground — the same far side the Phase 5 Cycles hero shows at the same pixels. **No face of the near vault, rib plate or archivolt intrudes anywhere in the opening.** The only object inside it that should not be there is the origin shrub pile in the bottom ~10 % (QA-11c-1), 44.5 % of opaque board in 11b -> 0 %.

New this round, not blockers: **QA-11c-2 (Gate 2)** the colonnade attic pedestals and balustrade read as flat pale rectangles — the merged colonnade exports **as modelled** (36 456 -> 36 456 tris), so this is missing texture/AO, not decimation. **QA-11c-3 (Gate 3, export/viewer)** the page logs `defaulted lightmap rgbm_range (no textures.*lightmap*.rgbm_range …) = 7` although the manifest carries `lightmap_encoding.rgbm_range = 64` — the viewer reads the wrong key. Harmless now (no lightmaps), a 9.1x error on every lightmap at Gate 3. Fix before the bake.

## 4. QA-11-9 at cam04, and the shrub inside the rotunda

**QA-11-9: FIXED.** At (470,140)-(600,350) and at the export probe's own box mapped to 1920x1080, (705,210)-(900,525), the loose triangular shard and the jagged facet 11b photographed are **gone**; coffers and ribs read as the Phase 5 geometry. `EXPM_ARCH_rotunda_plaster_ceiling_rib_merged` exports as modelled at **160 828** tris (was 56 000 decimated) — the 57.6 % of that box the export's ray-cast attributed to it. The coffers still read shallow (no shadow map, no AO at Gate 1): Gate 2/3, not geometry.

**The shrub `ENV_shrub_big3_0796_LOD2` is visible at cam04, and is a Gate 1 defect, not a Phase 5 inheritance.** It is one of the 1379 objects of QA-11c-1, at the world origin 2.4 m from the station (5 of the export probe's 3124 rays). The long blue-grey leaf-speckled wedge crossing the ceiling in the 11b and 11c frames alike is its leaf card, and Phase 5 `round09_04_rotunda_ceiling_cycles.png` has **no foliage anywhere in the frame** — ceiling, arch soffits and sky only; likewise the olive masses at the cam04 top-left, top-centre and top-right.

## 5. Score table — geometry rows only (Phase 5 round 09 / round 11b / **round 11c**)

| row | 01 hero | 02 NE 3/4 | 03 colonnade | 04 ceiling | 05 S lawn | 06 aerial |
|---|---|---|---|---|---|---|
| Silhouette match | 4 / 4 / **4** | 3.5 / 3.5 / **3.5** | 2.5 / 2.5 / **2.5** | 3.5 / 3.5 / **3.5** | 3.5 / 3.5 / **3.5** | 4 / 4 / **4** |
| Proportion | 4 / 4 / **4** | 3.5 / 3.5 / **3.5** | 3 / 3 / **3** | 3.5 / 3.5 / **3.5** | 3.5 / 3.5 / **3.5** | 3.5 / 3.5 / **3.5** |
| Ornament fidelity | 4 / 4 / **4** | 4 / 4 / **4** | 3 / 3 / **3** | 3 / 2.5 / **3** | 3.5 / 3.5 / **3.5** | 2.5 / 2.5 / **2.5** |
| Repetition visibility | 3 / 3 / **3** | 2.5 / 2.5 / **2.5** | 2 / 2 / **2** | 2.5 / 2.5 / **2.5** | 2.5 / 2.5 / **2.5** | 2.5 / 2.5 / **2.5** |
| **Scale cues (re-scored clean)** | 3.5 / 3 / **2.5** | 3 / 2.5 / **2** | 2.5 / 2.5 / **2** | 3 / 3 / **2** | 3 / 2.5 / **2** | 3 / 2.5 / **2** |
| **average (delta vs Phase 5)** | **3.50 (-0.20)** | **3.10 (-0.20)** | **2.50 (-0.10)** | **2.90 (-0.20)** | **3.00 (-0.20)** | **2.90 (-0.20)** |

**Parity FAILS.** The four Scale-cues rows 11b flagged as provisional (01, 02, 05, 06) were scored under 16-26 % of placeholder; re-scored on the clean frames they fall to 2.0-2.5, and cam04 falls with them. **Five rows are 1.0 below Phase 5, twice the 0.5 limit** — 01, 02, 04, 05, 06 Scale cues; cam03 is exactly at -0.5. Every other row is within 0.5 or unchanged, and two improve: cam04 Ornament (+0.5, the shard) and cam06 Silhouette (unchanged at 4 with the backdrop drawing).

## 6. Budget and performance — PASS on every line

Placed ARCH **949 382** / ORN **1 099 192** / ENV **792 822** = **2 841 396** of 3.0 M (158 604 spare); the viewer draws 2 837 912 after welding, 140 unique meshes, 154 draw-call batches. 1440p, 120 frames after 24 warm-up, ANGLE Metal / M2:

| station | 01 | 02 | 03 | 04 | 05 | 06 |
|---|---|---|---|---|---|---|
| draw calls | 195 | 189 | 199 | 77 | 185 | 201 |
| `renderer.info` tris (M) | 5.44 | 5.32 | 5.57 | 2.68 | 5.21 | 5.60 |
| GPU cost ms median / p95 | **1.5** / 2.7 | 1.4 / 2.7 | 1.6 / 2.8 | 0.5 / 0.7 | 1.4 / 2.7 | 1.5 / 2.9 |
| presented ms (median) | 16.7 | 16.6 | 17.3 | 16.5 | 16.7 | 16.6 |

The hero costs **1.5 ms of the 22.2 ms a 45 fps frame allows — 6.8 %**; presented time is 60 fps vsync, not a ceiling. `renderer.info` triangles are ~1.9x placed because the planar water reflector draws the scene twice. Resident **1.019 GB** (tex 545 / RT 438 / geo 36 MB) against the 1.2 GB plan; load **2.31 s for 206.4 MB**, `orn.glb` 154.1 MB of it; 12 programs, no shader error, no `useProgram` warning. Tonal rows stay unscored — a neutral-grey pass against a full-colour Phase 5 render makes every luma ratio a sanity check, never a metric.

## 7. Verdict

**GATE 1 FAIL.** Blocking defect: **every `ENV_shrub_*_LOD2` node — 1379 objects, 25 meshes, 135 880 placed tris — is written to `env.gltf` with no transform, so the entire shrub layer draws stacked at the world origin on the rotunda floor: the site planting is missing at all six stations and a foliage pile sits inside the rotunda, visible through the cam01 main arch and across the cam04 ceiling.** Owner **export**. One-line fix: write the object's world transform on every instanced ENV node in `gltf_gate1.py` (the shrub path is the only one that omits it — ARCH 562/564, ORN 436/436, ENV 147/1536), re-pack and re-capture.

Everything the last two rounds fixed holds: both placeholder sets are out of the frame at 0 % measured coverage, the name sweep sees them, the backdrop draws, the attic relief reads as relief, the main-arch opening shows the far side with no near-vault intrusion, the cam04 decimation shard is gone, and budget, draw calls, GPU cost and resident memory pass with margin.
