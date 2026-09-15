# QA round 11 — Phase 6 **Gate 1** (geometry freeze in the viewer), 2026-09-15. **GATE 1: FAIL.**

Scored: the Gate 1 export set as the viewer draws it at the six stations (ARCH/ORN LOD0 decimated, ENV LOD1 thinned
near trees + 127 far-tree placeholder quads, neutral grey + the ORN normal/AO bakes, `direct` lighting, water reflector
on). **Geometry rows only** — Silhouette, Proportion, Ornament fidelity (shape + normal-map relief), Repetition
visibility, Scale cues — each station against the Phase 5 render of that station (`renders/web/gate1_pairs.json` names
the reference per station; cam01 against `renders/final/v2/qa_round10b_cam01_cycles.png`).

No Blender and no Chrome ran for this round: every input was captured by the lead through `web/tools/gate1.sh` at 14:41
and every number below comes from those files plus `python3` analysis.

**Encoding note (from the export review, mid-round):** the grey UV1 probe texture and the foliage albedos in the Gate 1
glbs were written **linear instead of sRGB**, so every viewer frame is ~1.47x too bright in linear terms — no luminance,
tonality or material row is scored here and **every luma / ratio number in `gate1_pairs.json` is unusable this round**.
It does not touch geometry, silhouette, normals or repetition.

| file | what |
|---|---|
| `renders/web/gate1_cam01..06.png` | viewer, 1920x1080, `direct` |
| `renders/web/gate1_pair_cam0K.png` (+ `.json`) | viewer \| Phase 5 \| blend, 3872x762 |
| `renders/web/tiles/gate1_cam01_tile_r{1,2}c{1,2,3}.png` | the six 100 % tiles (viewer 640x540 \| same crop of the reference) |
| **`renders/web/round11_gate.png`** | **the gate composite**: six pairs, the tile list, the verdict (`scripts/qa_r11_gate.py`) |
| `scripts/qa_r11_billboards.py` | projects the 127 placeholder quads into any station (new this round) |

---

## 1. Name sweep — **PASS**

`export/name_sweep.py export/out/gate1/export_set.json` (the export engineer's sweep, same pattern and exemptions as
`scripts/qa_name_sweep.py`, run on the objects the export actually writes): **2540 exported objects, 0 hits, 0 exempt,
exit 0.** The round-10 exemptions (`ARCH_rotunda_inner_block_*`, `ENV_backdrop_fill*`) no longer match any name: the
city blocks are merged into `EXPM_ENV_backdropgroup_backdrop_fill{,roof}`, covered by the `EXEMPT_GATE1` rule.

**One placeholder class the export-side sweep cannot see**, recorded here as a named exception: the viewer builds 127
`WEB_far_tree_billboard_<prototype>` quads (25 prototypes) with `userData.pfaPlaceholder = 'gate3_tree_impostor'`
(web/README.md "Far-tree billboards"; the user's decision, phase6_plan §4b). They are on record and legitimate — but see
§3: they are opaque, camera-facing, and they hide the building.

## 2. Budget and performance — **PASS on every line**

| class | placed tris | budget | headroom |
|---|---|---|---|
| ARCH | 844,554 | 1,100,000 | 255,446 |
| ORN | 1,099,194 | 1,100,000 | 806 |
| ENV | 792,822 | 800,000 | 7,178 |
| **total** | **2,736,570** | **3,000,000** | **263,430** |

Draw-call batches 154 for the scene, **140 inside the cam01 frustum** (budget 400). Unique 902,356 tris over 140 meshes.
Of the ENV total, **151,737 placed triangles never draw at all** — see the blocker in §4; the effective drawn ENV is
641,085.

1440p perf (`gate1_perf.json`, 120 frames after 24 warm-up, ANGLE Metal / M2):

| station | draw calls | renderer.info tris | GPU cost ms (median / p95) | presented ms (median) | uncapped fps |
|---|---|---|---|---|---|
| 01 hero | 265 | 5,241,301 | **2.1** / 2.4 | 16.6 | 476 |
| 02 | 257 | 5,115,135 | 1.9 / 2.3 | 16.6 | 526 |
| 03 | 269 | 5,363,925 | 1.9 / 2.4 | 16.8 | 526 |
| 04 | 111 | 2,428,570 | 0.6 / 1.1 | 16.7 | 1667 |
| 05 | 255 | 5,005,403 | 1.9 / 3.2 | 16.6 | 526 |
| 06 | 269 | 5,393,665 | 1.9 / 2.9 | 16.7 | 526 |

The presented frame time is **60 fps vsync-capped**, not a ceiling: the GPU does the hero frame in 2.1 ms, ~8x the 45 fps
target. `renderer.info` triangles are ~1.9x the placed count because the planar water reflector renders the scene twice.
Resident **1.083 GB** (textures 612 MB, render targets 438 MB, geometry 33 MB) against the 1.2 GB plan. Load 2.58 s for
201.8 MB, `orn.glb` 155.3 MB of it (budget doc hand-off 2 — a 6b payload problem, not a Gate 1 one).

## 3. cam01 100 % tile review (3 x 2) — **11 defects**

Every tile viewed at 100 %, never the downscale. `scripts/qa_r11_billboards.py` reconstructs the placeholder quads
exactly (validated: station 1 reproduces the viewer's own logged three.js matrices to 0.03 % of frame area).

| # | tile | pixel box | defect | owner |
|---|---|---|---|---|
| QA-11-1 | r1c1 | (390,470)-(640,540) | colonnade-roof canopy is a few sparse leaf-card clusters where the reference has a continuous canopy — these trees went to the far list | export |
| QA-11-2 | r1c2 | (820,195)-(1000,285) | **attic relief panel torn**: the figure procession is legible but pocked with hard black voids and speckle; the reference band is continuous | export / ORN |
| QA-11-3 | r1c3 | (1280,440)-(1560,540) | south colonnade canopy absent altogether | export |
| QA-11-4 | r2c1 | (430,540)-(640,900) | placeholder slabs cover the colonnade entablature and its shore | viewer |
| QA-11-5 | r2c1 | whole tile | water is a ripple-free mirror; the slab reflections are hard rectangles (Gate 4 item, stated for the record) | viewer |
| QA-11-6 | r2c2 | (917,465)-(1000,620) | **main-arch opening 37.4 % covered by placeholder quads**; see the opening test below | viewer |
| QA-11-7 | r2c2 | (640,555)-(1280,900) | shore planting, podium base and riprap entirely hidden behind slabs | viewer |
| QA-11-8 | r2c3 | (1280,540)-(1600,760) | colonnade stylobate and riprap replaced by a flat slab | viewer |
| QA-11-9 | off-tile, cam04 | (470,140)-(600,350) | **ORN decimation sliver**: a long thin normal-mapped wedge crosses the ceiling coffers, absent from the Phase 5 frame | export / ORN |
| QA-11-10 | off-tile, cam02/cam05 | cam02 (690,165)-(890,290), cam05 (700,130)-(1200,220) | the same attic panels at the stations where they are largest: the relief is **destroyed**, figures shredded into disconnected fragments | export / ORN |
| QA-11-11 | off-tile, all | whole backdrop | **BLOCKER** — the entire ENV backdrop group never draws (§4) | export |

Nothing else: no cracked shells, no flipped normals, no z-fighting, no normal-map seams, no filled openings on the
building itself. The ARCH decimation is invisible — column flutes survive as geometry at 100 % (tiles r2c1, r2c3 and the
cam03 near column), dentils, modillions, the coffer field and the rotunda ceiling read 1:1 against Phase 5 (cam04).

**Ray-cast opening test, by eye at 100 % (CLAUDE.md gate check): PARTIAL.** Through the main arch the viewer shows clear
sky above y≈515 and **no face of the near vault, rib plate or archivolt intrudes into the opening** — the Phase 5 result
holds. But the lower 37.4 % of the opening box is a placeholder quad, not the far side of the opening, so the far
geometry could not be verified. There is no `?billboards=0` frame in the capture set; one is needed before Gate 2.

**Placeholder coverage per station** (projected quad area, upper bound before the depth test):
cam01 **16.1 %**, cam02 **32.2 %**, cam03 **33.9 %**, cam04 0 %, cam05 **25.9 %**, cam06 **28.0 %** of frame.

## 4. Blocker — 10 ENV materials never compile

`export/out/gate1/env.gltf` and `env_ktx2.gltf` give all ten `MAT_EXP_ENVBD__*` materials
`pbrMetallicRoughness.baseColorTexture.texCoord = **-1**` (invalid glTF; the spec requires an unsigned integer).
three.js turns that into `map.channel = -1`, the vertex shader is generated with
`vMapUv = ( mapTransform * vec3( uv18446744073709552000, 1 ) ).xy`, and the program fails:

> `THREE.WebGLProgram: Shader Error 0 - VALIDATE_STATUS false … ERROR: 0:389: 'uv18446744073709552000' : undeclared identifier`

followed by 256 `useProgram: program not valid` warnings — one per draw per pass, at every station. Only one error is
printed because the ten materials share a program key and WebGL then suppressed further reporting.

The cause is upstream in the export set: `export_set.json.uv_missing.uv1` lists exactly these ten
`EXPM_ENV_backdropgroup_*` meshes as having no UV1, and the grey UV1 probe texture was attached to them anyway.

**What is lost:** backdrop_building 33,696 · backdrop_forest 99,640 · roof 5,927 · lawn 5,882 · bird_white 2,268 ·
roof_tile 1,380 · skylight 1,236 · hill 880 · lamp_post 816 · door_green 12 = **151,737 placed triangles, 19.1 % of the
ENV budget and 5.54 % of the scene, drawn at no station.** Visible as an empty grey void beyond the colonnade at cam06
(city, roads, lawn and far forest all gone), and as a missing horizon at cam05.

**Fix (one line):** in the glTF writer, do not attach the grey probe base-colour texture to a material whose mesh has no
UV0 — or write `texCoord: 0` — then re-pack `env.glb`. A viewer-side clamp (`channel < 0 -> 0` in `materials.js`) is
worth adding as belt and braces so an invalid manifest can never silently drop geometry again.

**Blocker 2 — the three voxel-remeshed attic panels.** `phase6_budget.md` hand-off 1 pre-flagged them (COLLAPSE stalls on
~40 000 relief islands, so the 8 k lo is a voxel shell, lo->hi deviation max 367 mm, normal-map blue mean 0.79-0.81
against 0.97 on a clean pair) and asked for a Gate 1 tile check: *"retopologise by hand only if it reads flat."*
It does not read flat — it reads **torn**. At cam02 the panel spans ~200 px and the figures break into disconnected
speckled fragments with black voids; at cam05 the whole band does; at the hero it is legible but pocked. This is the
single reason the cam02 and cam05 Ornament rows break parity. There is 255 k of ARCH headroom and 263 k scene headroom
to pay for a proper lo-poly on three meshes.

## 5. Silhouette — the decimation costs nothing

`scripts/qa_silhouette.py align`, viewer cam01 against the Phase 5 Cycles hero, both 1920x1080, crop `690 40 1235 520`:

**scale 1.0000, dx 0.0, dy 0.0, apex delta 0.00 % of frame height.** Apex row 84 and corner-top row 209 in both.
Per-column profile difference over the 545 building columns: **mean |d| 0.81 px = 0.075 %H**, p95 3 px, max 23 px (one
column at a dome-cap urn edge). Course rows — dome cap, drum band, attic cornice, dentil course, entablature, stylobate
— land on the same rows in both frames. **The LOD0 decimation is silhouette-neutral.** (Widen the crop past the building
and the measure is contaminated by the placeholder slabs, not by the model.)

## 6. Score table — geometry rows only, viewer vs the Phase 5 render of the same station

Phase 5 (round 09) -> Gate 1 viewer. Parity rule: each row within 0.5 of its Phase 5 value.

| row | 01 hero | 02 NE 3/4 | 03 colonnade | 04 ceiling | 05 S lawn | 06 aerial |
|---|---|---|---|---|---|---|
| Silhouette match | 4 -> 4 | 3.5 -> 3.5 | 2.5 -> 2.5 | 3.5 -> 3.5 | 3.5 -> 3.5 | 4 -> **3** ✗ |
| Proportion | 4 -> 4 | 3.5 -> 3.5 | 3 -> 3 | 3.5 -> 3.5 | 3.5 -> 3.5 | 3.5 -> 3.5 |
| Ornament fidelity | 4 -> **3.5** | 4 -> **3** ✗ | 3 -> 3 | 3 -> **2.5** | 3.5 -> **2.5** ✗ | 2.5 -> 2.5 |
| Repetition visibility | 3 -> 3 | 2.5 -> 2.5 | 2 -> 2 | 2.5 -> 2.5 | 2.5 -> 2.5 | 2.5 -> 2.5 |
| Scale cues | 3.5 -> **3** | 3 -> **2.5** | 2.5 -> 2.5 | 3 -> 3 | 3 -> **2.5** | 3 -> **2.5** |
| **average (delta)** | **3.50 (-0.20)** | **3.00 (-0.30)** | **2.60 (0.00)** | **3.00 (-0.10)** | **2.90 (-0.30)** | **2.80 (-0.30)** |

Every station average is within 0.5, but **three individual rows are not**: cam06 Silhouette (-1.0, the backdrop is
gone), cam02 Ornament (-1.0) and cam05 Ornament (-1.0, both the attic panels). The parity rule is per row, so it fails.

Scoring notes. Repetition visibility is judged on geometry alone — the instance set, placements and the 3 variants per
ORN class are identical to Phase 5, so no station moves; the grey pass removes the per-instance weathering that carried
part of the Phase 5 score, and that will have to be re-checked at Gate 2. Scale cues drop wherever the placeholder slabs
replace the shoreline planting, benches and riprap that give the building its human scale (cam01, cam02, cam05, cam06).

## 7. Verdict

**GATE 1 FAIL.** Blocking defect: **`env.gltf` ships ten `MAT_EXP_ENVBD__*` materials with
`baseColorTexture.texCoord = -1`, so their vertex shader never compiles and 151,737 placed triangles — the whole ENV
backdrop group — are drawn at no station.** Owner **export**. One-line fix: do not attach the grey UV1 probe texture to
a material whose mesh has no UV0 (or write `texCoord: 0`), re-pack `env.glb`, and clamp `channel < 0 -> 0` in the viewer
so this can never fail silently again.

Second blocker, same owner: retopologise or re-decimate the three `ORN_attic_panel_v*_LOD0` meshes — the voxel shell
tears the relief at cam02 and cam05 (QA-11-2, QA-11-10). There is 263 k of scene headroom to pay for it.

Also required before the gate is re-run: a `?billboards=0` capture of cam01/02/05/06 so the geometry the 127 placeholder
quads hide (16-34 % of those frames, 37.4 % of the hero's main-arch opening) can actually be judged; and the sRGB
re-encode the export review already has in hand, so the next capture's luma numbers mean something.

Everything else passes and passes well: budget, draw calls, GPU cost, resident memory, the name sweep, and a
silhouette that is identical to the Phase 5 hero to 0.075 % of frame height.
