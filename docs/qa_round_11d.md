# QA round 11d — Phase 6 **Gate 1**, fourth check, 2026-09-15. **GATE 1: PASS.**

Scored on the lead's 16:50 capture of the merged export (`a9b2d3d`, `env.glb` re-packed only; the page log confirms the new
pack: 41 env meshes / 1526 instances against 39 / 1458 in 11c), six stations 1920x1080, **`?billboards=0&treeboards=0`**,
neutral grey + ORN normal/AO, `direct` lighting, water reflector on. Geometry rows only, each station against the Phase 5
render in `gate1_pairs.json`. No Blender, no Chrome; the six cam01 tiles (16:42) are newer than the frames (16:41) and were
viewed at 100 %. New: `scripts/qa_r11d_probe.py` and `scripts/qa_r11d_gate.py` -> `renders/web/round11d_gate.png`.

## 1. QA-11c-1 — **FIXED**

| proof | 11c | 11d |
|---|---|---|
| `env.gltf` mesh nodes with a transform | 147 / 1536 | **1526 / 1536** (the 10 without are the merged world-space `ENV_backdropgroup_*`, identity by design) |
| shrub nodes within 1 m of the world origin | 1379 | **0**; spread **-138.8..110.8 / -1.6..-0.3 / -120.9..45.1 m** (250 x 166 m of site, at ground level). Writer assertion `gltf_gate1.json.near_origin` = **`{}`** |
| `export/verify_glb.py`, re-run by QA | — | **PASS**: drawn vs `export_set` arch -0.185 %, orn -0.157 %, **env 0.000 %**, ground 0.000 %; 0 plain nodes at the origin |

**The origin-pixel test is not by itself a discriminator.** At cam01 (960,655), cam02 (960,908) and cam05 (960,852) the origin
projects onto ground the Phase 5 render shows *planted*; at cam05 the 11c pile sat behind a colonnade column and never reached the
pixel. What separates a pile from planting is whether the foliage is an **island**, measured over the reference planting band (50-px
columns above 15 % foliage; band coverage in brackets, 11c -> 11d): cam01 shore **1 -> 21 of 29** (4.0 -> 26.2 %) · cam02 **0 -> 15
of 31** (1.2 -> 19.5 %) · cam03 walk **0 -> 5 of 39** (1.9 -> 5.3 %) · cam05 lawn **0 -> 29 of 33** (12.9 -> 29.5 %) · cam06 **0 ->
1 of 33** (1.7 -> 7.2 %; aerial clumps). At **cam01** the isolated clump 11c photographed under the main arch is replaced by a
continuous shore band running the full width, where the Phase 5 hero's band runs (strip 1; tiles r2c1/r2c2/r2c3 at 100 %);
**cam05**'s band runs the length of the colonnade base as in Phase 5; **cam03** is planted but thin (a bank against the podium, no
bed along the near walk edge); **cam06**'s lagoon and rotunda rings are planted. **cam04: the shrub is gone** — the leaf cards that
filled the top-right corner and the wedge across the ceiling are now coffers, ribs and sky (strip 2); the green-excess metric is
meaningless there (gold ceiling), so cam04 rests on the 100 % crop and the node audit.

## 2. cam01 six-tile pass at 100 %, and the open list

**FIXED, seen again at 100 %.** QA-11-2 / -10 attic relief (r1c2: procession, dentils, dome and vault continuous, no voids or
speckle); QA-11-4 (r2c1: shore, quay, riprap and the shrub band all draw); QA-11-6 (ray test below); QA-11-7 (r2c2: podium
draws, planting in front of it exists); QA-11-8 (r2c3: balustrade, quay edge, riprap modelled — flatness is Gate 2); QA-11-9
(cam04 rib group as modelled, 160 828 tris, corner clean); QA-11-11 (city mass, roofs, ridge at 01/05/06); **QA-11c-1** (§1);
**QA-11c-3** — the `defaulted lightmap rgbm_range … = 7` line is gone and the manifest's 64 is read. **OPEN — Gate 3:**
QA-11-1 and QA-11-3, the sparse colonnade-roof canopy (r1c1) and the absent south-colonnade tree (r1c3) — both are the 127
suppressed impostor carriers. **OPEN — Gate 4 (viewer):** QA-11-5, a perfect mirror against a rippled reference in all three
r2 tiles. **OPEN — Gate 2:** QA-11c-2 (attic pedestals and balustrade flat pale; undecimated 36 456 -> 36 456, so missing
texture/AO, not geometry) and the 11b note on the untextured backdrop / hill forest.

**Arch-opening ray test, cam01 main arch (890,430)-(1040,650) at 100 %: PASS.** Sky above the springline, the far interior wall
with its ledges below it, no face of the near vault, rib plate or archivolt in the opening — and the origin clump that held the
bottom ~10 % in 11c is gone (strip 1, left vs centre).

**New, neither a blocker. QA-11d-1 (Gate 4):** the shrub `InstancedMesh` bounds now span the whole 250 x 166 m site, so every
env batch passes the frustum test at every station — cam04, which sees almost none of the site, went 77 -> 99 draws and
2.68 -> 2.80 M triangles while the pile it used to draw was removed; 0.1 ms today, but chunk the shrubs spatially before the
flythrough. **QA-11d-2 (Gate 2, export):** `gltfpack.log` warns `position data has significant error (37 %)` for the re-packed
`env.glb`; nothing is visibly displaced at 100 %, but re-pack with `-vp 16` and re-check. Carried: one unattributed `404` in
the page log while all 7 planned files load.

## 3. Score table — geometry rows only (Phase 5 round 09 / round 11c / **round 11d**)

| row | 01 hero | 02 NE 3/4 | 03 colonnade | 04 ceiling | 05 S lawn | 06 aerial |
|---|---|---|---|---|---|---|
| Silhouette match | 4 / 4 / **4** | 3.5 / 3.5 / **3.5** | 2.5 / 2.5 / **2.5** | 3.5 / 3.5 / **3.5** | 3.5 / 3.5 / **3.5** | 4 / 4 / **4** |
| Proportion | 4 / 4 / **4** | 3.5 / 3.5 / **3.5** | 3 / 3 / **3** | 3.5 / 3.5 / **3.5** | 3.5 / 3.5 / **3.5** | 3.5 / 3.5 / **3.5** |
| Ornament fidelity | 4 / 4 / **4** | 4 / 4 / **4** | 3 / 3 / **3** | 3 / 3 / **3** | 3.5 / 3.5 / **3.5** | 2.5 / 2.5 / **2.5** |
| Repetition visibility | 3 / 3 / **3** | 2.5 / 2.5 / **2.5** | 2 / 2 / **2** | 2.5 / 2.5 / **2.5** | 2.5 / 2.5 / **2.5** | 2.5 / 2.5 / **2.5** |
| **Scale cues (planting in place)** | 3.5 / 2.5 / **3** | 3 / 2 / **2.5** | 2.5 / 2 / **2** | 3 / 2 / **3** | 3 / 2 / **2.5** | 3 / 2 / **2.5** |
| **average (delta vs Phase 5)** | **3.60 (-0.10)** | **3.20 (-0.10)** | **2.50 (-0.10)** | **3.10 (0.00)** | **3.10 (-0.10)** | **3.00 (-0.10)** |

**Parity PASSES: no row is more than 0.5 below its Phase 5 value.** `arch.glb` and `orn.glb` are byte-identical to the 11c capture, so those four rows carry with their 11c evidence. Scale cues recover 0.5-1.0 everywhere (planting back where Phase 5 has it; cam04 back to its Phase 5 value with the foreign shrub gone) and stay 0.5 under Phase 5 at 01 / 02 / 03 / 05 / 06 for one reason: the far-tree canopy is still the 127 suppressed carriers (QA-11-1 / -3, Gate 3). Tonal rows stay unscored.

## 4. Budget and performance — PASS on every line

Placed ARCH **949 382** / ORN **1 099 192** / ENV **679 779** + ground **113 043** = **2 841 396** of 3.0 M (158 604 spare); 140 unique meshes, 154 batches. 1440p, 120 frames after 24 warm-up, ANGLE Metal / M2:

| station | 01 | 02 | 03 | 04 | 05 | 06 |
|---|---|---|---|---|---|---|
| draw calls (11c) | 199 (195) | 193 (189) | 203 (199) | 99 (77) | 189 (185) | 205 (201) |
| `renderer.info` tris (M) | 5.44 | 5.32 | 5.57 | 2.80 | 5.21 | 5.60 |
| GPU cost ms median / p95 | **1.5** / 2.8 | 1.4 / 2.3 | 1.5 / 2.5 | 0.6 / 1.1 | 1.4 / 2.7 | 1.5 / 2.8 |
| presented ms (median) | 16.7 | 16.7 | 17.1 | 16.7 | 16.7 | 16.6 |

The hero costs **1.5 ms of the 22.2 ms a 45 fps frame allows — 6.8 %**; presented time is 60 fps vsync, not a ceiling, and
`renderer.info` triangles are ~1.9x placed because the planar water reflector draws the scene twice. Resident **1.019 GB**
(tex 545 / RT 438 / geo 36 MB) of the 1.2 GB plan; load **2.57 s for 206.5 MB**; 12 programs, no shader error. The +22 draws
at cam04 are QA-11d-1. **Name sweep re-run by QA: PASS** — 2540 exported objects, 127 exempt `ENV_treeboard_*`, 0 to explain.

## 5. Verdict

**GATE 1 PASS.** The round-11c blocker is fixed at the source and proven three ways (transform audit, writer assertions,
`verify_glb` triangles) and in the pixels at five stations; both placeholder sets stay out of frame at 0 % coverage; the name
sweep is clean; the main-arch opening shows the far side; every geometry row is within 0.5 of Phase 5; budget, draw calls, GPU
cost and memory pass with margin. Open: QA-11-1 / -3 (impostors) and QA-11-5 (water) at Gates 3 / 4; QA-11c-2, the untextured
backdrop and QA-11d-2 (`-vp 16`) at Gate 2; QA-11d-1 (batch bounds) at Gate 4.
