# QA round 10 — hero gate on the fixed vaults (2026-09-10). Tile review **FAIL**; hero **3.67 -> 3.56 (-0.11)**.

Scored master: the file on disk after `lead_build_r10`, **9695 objects**, LOD1 **11.52 M tris**. Merged since round 09:
**ARCH r8** (the vault-plate chord fix on all 8 bays) and **LIGHT r17** (arch soffits re-lit, `LIGHT_gallery_fill` for
cam03, cam02 pier re-measured). Hero only, per the brief: Cycles cam01 plus a defect pass on the Eevee cam02 / cam03.
No other Blender ran during any render; every render was one blocking `scripts/blender_run.sh` call and exited on its own.

| file | what |
|---|---|
| `renders/final/v2/qa_round10_cam01_cycles.png` | Cycles 1920x1080, 128 spp, OIDN, GPU: **384.5 s** (r09 380.6). Also `renders/previews/qa/round10_01_lagoon_hero_cycles.png`. |
| `renders/previews/qa/round10_0{1,2,3}_*.png` | Eevee 1280x720, 32 TAA, LOD1; whole three-camera pass **79.5 s**. |
| `renders/final/v2/round10_cam01_aligned_vs_ref169.png` | `qa_silhouette.py align`, crop 690 40 1235 520 / ref-crop 749 127 1165 493 |
| **`renders/final/v2/round10_gate.png`** | **the gate composite**: hero vs ref 169, the arch 1:1 pair, the tile defect list, the score deltas, the verdict |
| `renders/final/v2/round10_RENDERS_DONE` | touched after the last render exited |

Commands: `scripts/blender_run.sh 400 -- --background master.blend --python scripts/qa_name_sweep.py`;
`... 600 -- ... scripts/qa_r10_rays.py`; `... 300 -- ... scripts/qa_r10_pixel_probe.py`;
`... 1500 -- --background --python scripts/qa_render_round.py -- --round 10 --final --cams 01 --samples 128 --res 1920 1080`;
`... 600 -- ... --round 10 --eevee --cams 01 02 03`. Analysis, no Blender: `qa_hero_tiles.py`, `qa_silhouette.py align`,
`qa_r07_measure.py box`, `qa_r10_gate.py`. Nothing was written to master.blend.

---

## Item 1 — name sweep

`scripts/qa_name_sweep.py`: **520 exempt, 1 hit, exit 1.**

    HIT  LIGHT_shade_fill_00   [LIGHT]  LIGHT  (0.0, 0.0, 80.0)

Not a geometry stand-in: it is the az-25 el-2 blue sun lamp that has stood in for sky-shade since round 14
(`light_build.SHADE_FILL`, energy 49.0 Cycles / 38.5 Eevee, documented in `light_build.py` and `light_presets.py`).
**Added to `docs/quality_checklist.md` as a named exception** — with the note that it is the measured source of the
hero's magenta arch jamb below, so the exception covers the *name*, not the *defect*. The 520 exempt hits are the
`ARCH_rotunda_inner_block_*` piers and the `ENV_backdrop_fill*` city blocks already on record. **PASS** as a sweep.

## Item 2 — ray-cast opening test (`scripts/qa_r10_rays.py`, new)

Rays start at the real camera station (from `qa_cameras.CAMERAS` by name), aimed at the bay axis at z = 16..22, and
every hit along the ray is listed with its apothem and its radius from the springing axis. Legal first hit: beyond the
barrel band (the far side / sky) or the soffit within 0.45 m of its local radius.

| camera / bay | result |
|---|---|
| cam01 / bay 00 | **7 / 7 PASS** — z 16 clear to sky; z 17-21 first hit at apothem **-9.6 to -15.4**, i.e. the *far* side of the rotunda 114-118 m out; z 22 the near soffit `ARCH_rotunda_vault_coffers_00` at r **4.9** against a local soffit radius of 4.98 (dev 0.08). |
| cam02 / bay 07 | **7 / 7 PASS** — z 16-21 through to the ceiling ribs / inner wall at apothem -1.8 to -8.1; z 22 `ARCH_rotunda_vault_coffers_07` at r **5.0**. |

Not one ray hits a face of the near vault, rib plate or archivolt inside the opening. Independently,
`scripts/qa_r10_pixel_probe.py` fires through the hero's own pixel (960, 500) — the centre of the main arch — and
returns **SKY**. **The v1 blocker is gone and is verified three ways** (rays, pixel probe, and 214.4 lum of sky
measured inside the opening against the photograph's 233.3 = 0.92x).

## Item 3 — the 100 % tile review, before any score

Six tiles of the Cycles hero (3 x 2, 640 x 540 each) and four tiles each of the Eevee cam02 / cam03, viewed one by one
at 100 %. Pixel boxes are in the full frame (1920x1080 for the hero, 1280x720 for the Eevee pair). Object names come
from `qa_r10_pixel_probe.py`, so each defect names the object its ray hit.

| # | tile | box | defect | object | owner | sev |
|---|---|---|---|---|---|---|
| QA-10-1 | r1c1 | 1055 1005 1090 1065 | **Two flat-shaded icospheres** (body + head), chalk white, no neck, beak, wing, tail or leg — at **7.5 m**, the closest object to the hero camera. A placeholder-grade asset in the hero foreground. | `ENV_gulls_sitting` [ENV_extras, MAT_bird_white] | environment | **blocker** |
| QA-10-2 | r0c1 | 866 395 895 490 | The arch jamb / reveal is **magenta-violet**: lum 61.5 / **hue 338.5** / sat 0.265 against the photograph's 95.7 / 22.2 / 0.466. And the vault field (900 380 1010 430) is **103.1 lum against ref 44.9 = 2.30x**: the frame's deepest shade is a mid-tone. The arch the user complained about still does not read. | `LIGHT_shade_fill_00` + the rotunda interior fill | lighting | **blocker** |
| QA-10-3 | r0c1 | 840 290 1100 580 | **No archivolt.** A plain bevelled lip where the photograph has a moulded band, keystone and rosette course. Arch-ring 890 340 1050 370: render std **40.8 vs ref 64.2 (0.64x)**, col-sd **23.5 vs 47.9 (0.49x)**. | `ARCH_rotunda` arch head, 8 empty `SOCKET_` | ornament | major |
| QA-10-4 | r0c1 | 890 355 1030 470 | The coffered barrel reads as a **perforated plate**: round holes in a pale flat field, no coffer depth, no cast shadow, no rosette. The chords are gone; what replaced them is a sheet with holes, not a vault. | `ARCH_rotunda_vault_coffers_00` | architecture | major |
| QA-10-5 | r0c1 | 760 360 900 470 / 1100 360 1240 470 | The two side-bay soffits are **112-face flat dark-olive plates** with no coffer relief. | `ARCH_rotunda_vault_01` / `_07`, MAT_concrete_inner | architecture | major |
| QA-10-6 | r1c0 r1c1 r1c2 | 715 705 1785 840 | Five more gulls in open water; each mirrors as an **unbroken white column ~4x its own height**, reading as a white post standing mid-lagoon. | `ENV_gulls_sitting` + MAT_water_lagoon roughness | environment | major |
| QA-10-7 | r0c1 | 845 330 890 540 / 1050 330 1095 540 | Shafts are **hard vertical stripes**, bright ochre against violet-black, with no cylindrical falloff. Columns box sat **0.694 vs the photo's 0.595**. | `ARCH_rotunda_column_03_LOD1`, MAT_column_rose | materials | major |
| QA-10-8 | r0c1 | 920 95 1000 120 | Dome cap untextured near-white, col-sd **5.1**; a smooth plastic lid. 189.5 vs ref 224.3. | `ARCH_rotunda_dome`, MAT_dome_membrane | materials | major |
| QA-10-9 | r1c0 | 0 540 250 650 | The left-of-frame colonnade back wall behind the shafts is **flat indigo panels** with no texture. | `ARCH_colonnade_south` | lighting | minor |
| QA-10-10 | r1c0 r1c2 | 0 540 640 680 / 1280 540 1920 670 | Shoreline planting: hard-edged leaf cards, black clumps with no leaf mass, an **orange mulch blob** at 1755 655 1820 690, evenly spaced identical bank rocks. | ENV trees / shrubs | environment | minor |
| QA-10-11 | r0c0 r0c2 | whole sky | Cloudless, structureless gradient at 0.83x the photograph's level (carried from r07). | world | lighting | minor |
| QA-10-12 | cam02 r0c0 r0c1 | 340 210 640 360 | The whole shaded NE face is **violet-indigo** — shafts, dentils, piers. QA-08-2, open in the delivery engine. | shade rig | lighting | major |
| QA-10-13 | cam02 r0c0 r0c1 | 735 275 830 360 | The arch soffit is a **chrome-yellow rim on an indigo coffer field**: reads as painted gold-on-blue decoration, not shaded concrete. LIGHT r17's `rib-field contrast 111 / 115 PASS` is measuring exactly this. | interior fill | lighting | major |
| QA-10-14 | cam02 r1c1 | 920 465 1160 590 | **Untextured stepped ochre boxes** in cam02's mid-ground at 116-122 m — 66 faces on the pavilion. | `ENV_backdrop_hall_detail` / `_hall_pavilion`, MAT_backdrop_building | environment | major |
| QA-10-15 | cam02 r1c0 r1c1 | 0 360 1280 720 | The whole lower half is near-black; individual leaf cards read as separate hard cut-outs. | foliage / shade | environment | major |
| QA-10-16 | cam03 r1c0 r1c1 | 0 480 460 720 | The colonnade paving is a **black-and-white chequer of large triangles** — a test pattern: cold blue-grey, no grout depth, no wear, no dirt. | MAT paving | materials | major |
| QA-10-17 | cam03 r0c1 r1c1 | 845 0 1280 720 | The near column fills **34 % of the frame as a flat olive-green slab**: no cylindrical shading, flutes gone, only a vertical streak texture. `LIGHT_gallery_fill` lights it evenly from the front, which is what removed the form. | near column | lighting | major |
| QA-10-18 | cam03 r0c0 | 0 0 200 360 | Foreground foliage is a black spiky silhouette with no leaf mass. | ENV trees | environment | minor |

## Item 4 — the score, and the arch verdict

Round-07..09 boxes, re-based in round 08; the alignment came back **bit-identical again** (scale 1.3108, dx -291.8,
dy -126.6, apex delta 0.44 %H) so the boxes are used unshifted for the fourth round running.

| row | r09 | **r10** | why |
|---|---|---|---|
| Silhouette match | 4 | **4** | transform bit-identical, apex delta 0.44 %H |
| Proportion | 4 | **4.5** | the arch opening has its real depth: ray test 14/14 and the hero's own arch-centre pixel returns SKY; far sky 214.4 vs ref 233.3 |
| Ornament fidelity | 4 | **3.5** | the revealed arch has no archivolt and its coffers are punched holes: arch-ring structure 0.64x / 0.49x the photograph's |
| Material realism | 3.5 | **3.5** | every chroma and texture box within 0.1 of round 09 |
| Edge wear | 3.5 | **3.5** | attic std 28.9, aniso 5.03, run-off 20.0 % — unchanged |
| Lighting mood | 4.5 | **4.0** | the frame's deepest shade is 2.30x the photograph with a magenta edge (jamb hue 338.5) |
| Water reflection | 3 | **3** | lum 115.8 -> **131.5** clears the 124 floor at last (0.795 of ref 165.5), but sat 0.383 -> **0.227** (ref 0.358) and R-B +50.2 -> **+31.9** (ref +68.7) now fail: a trade, not a gain |
| Repetition visibility | 3 | **3** | unchanged |
| Scale cues | 3.5 | **3** | the waterfowl that carry the hero's scale are two-icosphere blobs, the nearest 7.5 m from the camera |
| **average** | **3.67** | **3.56** | **-0.11** |

**Two readings, both stated so the lead can use either.** Scoring *only what the round changed* — Proportion +0.5 for
the opening, Lighting -0.5 for the fill that flooded it — the hero is **3.67, +0.00**. The **-0.11** is the mandated
100 % re-scoring of Ornament fidelity and Scale cues: those defects were always there, the arch fill and the 960 px
composite hid them, and the new gate check exists to stop exactly that. Neither reading reaches 4.0 and the
definition-of-done clock is already spent, so this changes no schedule.

### Every other box, r09 -> r10 (Cycles hero)

Unchanged to within noise except the reflection: sunlit attic 188.7 / 37.0 / 0.487 / +110.6 (identical); attic string
179.7; entablature 132.2 -> 132.9; dome cap 189.5; shaded attic 127.6 / 34.8 / 0.443; whole building 133.8 -> 132.8,
sat 0.571 -> 0.565; ripples 121.8 -> 122.1; near water 125.3 -> 125.4; flank 162.7 -> 162.8; shore 88.4 -> 88.9;
south wing 100.2 -> 101.1; north wing 138.4 -> 138.9; attic std 28.9, aniso 5.03 / control unchanged.
**Water reflection column 900 760 1020 840: 115.8 / 40.6 / 0.383 / +50.2 -> 131.5 / 41.9 / 0.227 / +31.9.** This is
ARCH r8's doing, exactly as LIGHT r17 predicted: the open arch now mirrors sky and vault instead of a lit plate, so
the column got brighter and much bluer.

### Does the arch read as the photograph's? (brief item 4)

**Half.** The composite's middle panel is the answer at 1:1, same 260 x 290 px box in both.

* **Yes, structurally.** Near arch -> concave coffered barrel -> far arch -> sky, in that order, with sky measured at
  0.92x the photograph's level inside the opening. The chord fill is gone by three independent tests. This is a real
  fix and the largest single geometry correction since round 01.
* **No, as a piece of architecture.** The photograph's arch is carried by a deep moulded archivolt with a keystone and
  a rosette course, deep sunk coffers with hard shadow lines, engaged capitals at the springing, and a warm bounce in
  the reveal. The render has a plain lip, round holes in a pale plate, plain piers, and a magenta reveal. The three
  numbers that say it: arch-ring structure **0.64x**, arch-ring horizontal variation **0.49x**, vault field **2.30x**
  too bright.

## Verdict

**TILE REVIEW: FAIL.** Two blockers before the 4K v2 is worth its 70 minutes, both cheap:

1. **QA-10-1 / QA-10-6 — `ENV_gulls_sitting`, owner ENVIRONMENT.** Two-icosphere placeholder waterfowl, the nearest
   7.5 m from the hero camera, plus five in open water whose reflections read as white posts. Acceptance: no
   waterfowl within 40 m of `CAM_qa_01_lagoon_hero` unless it carries a silhouette with neck, beak and tail at
   >= 40 px in the 4K frame; the open-water ones removed or moved to the far bank.
2. **QA-10-2 — the rotunda interior fill, owner LIGHTING.** Acceptance: the vault field box `900 380 1010 430` on the
   Cycles hero lands at **45-65 lum** (photograph 44.9) and the jamb box `872 400 892 480` returns a hue in
   **25-60 deg** with a positive R-B (photograph 22.2 / +58.9).

Both are one-number / one-visibility changes and neither needs a full round. Everything else in the table above is a
major for the Phase 5 known-issues list, ordered by hero visibility: QA-10-3 (archivolt), QA-10-4 / QA-10-5 (coffer
depth), QA-10-7 (column stripes), QA-10-8 (dome cap), QA-10-16 / QA-10-17 (cam03 chequer and flat column),
QA-10-12 / QA-10-13 (cam02 violet and gold-on-blue soffit), QA-10-14 (backdrop boxes), then the minors.
