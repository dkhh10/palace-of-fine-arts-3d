# QA round 04 — Phase 4 polish round 2 gate (2026-09-08)

Round 04 renders the master rebuilt after lighting r09 + r10, architecture p4r2 (+ rosette socket fix), materials r4 + r5,
environment r4 + r5 and ornament r4 (lead build `renders/logs/lead_build_r4c.log`, EXIT 0; 8736 objects). Machine quiet: no
other Blender during any QA render. Watchdog: both GPU Cycles frames (335 s and 211 s wall) survived — QA-03-1 closed.

## What was rendered and compared

| file | what |
|---|---|
| `renders/previews/qa/round04_0K_*.png` | Eevee 1280x720, 32 TAA, LOD1, `apply_preview_eevee`. Times **17.3 / 24.3 / 21.4 / 16.3 / 16.2 / 11.5 s** (round 03: 36.4 / 38.1 / 52.9 / 33.3 / 35.0 / 25.3 s). cam02 re-rendered at the new station: 23.1 s. |
| `renders/previews/qa/round04_01_lagoon_hero_cycles.png` | Cycles 1920x1080, **128 spp adaptive, uncapped**, OIDN, GPU: **335.4 s** wall (round 02 uncapped: 446 s). |
| `renders/previews/qa/round04_04_rotunda_ceiling_cycles.png` | Cycles 1280x720, 64 spp, uncapped: 210.9 s — the interior-fill check. |
| `renders/qa_comparisons/round04_cam0K.png`, `round04_sheet.png` | render / canonical photo / 50 % blend per camera, contact sheet |
| `round04_cam01_aligned_vs_ref169.png` | W_a-aligned overlay (the 2 % silhouette test): scale 1.3113, dx -292.0, dy -126.3 (round 03: 1.307 / -291.5 / -128.1, so every round-03 box is still valid within 2 px) |
| `round04_cam01_crops_vs_ref169.png` | 1:1 crop pairs (stone, capital/cornice, waterline, shore shrubs, near water) with boxes and numbers burnt in |
| **`renders/qa_comparisons/round04_gate.png`** | **the gate composite**: Cycles hero beside ref 169, six Eevee views, score deltas r03 -> r04 |

Commands: `blender -b --python scripts/qa_render_round.py -- --round 04 --eevee`, `-- --round 04 --final --samples 128 --res 1920 1080
--cams 01`, `-- --round 04 --final --samples 64 --res 1280 720 --cams 04`, `scripts/qa_inspect.py`, `scripts/qa_cam02_probe.py`
(new, the cam02 station sweep), `scripts/light_r10_measure.py` (lighting's tool, on QA's boxes), `qa_silhouette.py align`, `qa_crops.py`,
`qa_gate_sheet.py --round 04`. `qa_render_round.py` now always rebuilds the QA_CAMERAS collection from `qa_cameras.py` (the saved master
carried the old cam02); nothing is written back to master.blend.

## Score table (0-5; target >= 4 every row, hero average >= 4.5). Round 03 -> round 04.

| row | cam01 | cam02 | cam03 | cam04 | cam05 | cam06 |
|---|---|---|---|---|---|---|
| Silhouette match | 4 -> 4 | 2 -> **3.5** | 2.5 -> 2.5 | 3.5 -> 3.5 | 3 -> 3.5 | 4 -> 4 |
| Proportion | 4 -> 4 | 3 -> 3.5 | 3 -> 3 | 3.5 -> 3.5 | 3 -> 3 | 3.5 -> 3.5 |
| Ornament fidelity | 3 -> 3.5 | 2.5 -> 3 | 2.5 -> 2.5 | 1.5 -> **3** | 3 -> 3 | 2.5 -> 2.5 |
| Material realism | 3 -> 3 | 2.5 -> 2.5 | 1.5 -> 1.5 | 1.5 -> 1.5 | 2.5 -> 2.5 | 1.5 -> 2 |
| Edge wear | 1.5 -> 1.5 | 1 -> 1 | 0.5 -> 0.5 | 0.5 -> 0.5 | 1.5 -> 1.5 | 0.5 -> 0.5 |
| Lighting mood | 4 -> 4 | 3 -> 3 | 2.5 -> **1.5** | 2 -> 2 | 3.5 -> 3.5 | 2 -> 2.5 |
| Water reflection | 3.5 -> 3.5 | 2.5 -> 2 | n/a | n/a | 2.5 -> 2.5 | 1.5 -> 2 |
| Repetition visibility | 3 -> 3 | 2 -> 2.5 | 2 -> 2 | 2 -> 2.5 | 2.5 -> 2.5 | 2 -> 2 |
| Scale cues | 3.5 -> **3** | 2.5 -> 3 | 2.5 -> 2.5 | 2.5 -> 3 | 2.5 -> 2.5 | 2 -> 2.5 |
| **average (delta)** | **3.28 (+0.00)** | **2.67 (+0.33)** | **2.00 (-0.12)** | **2.44 (+0.31)** | **2.72 (+0.06)** | **2.39 (+0.22)** |

Verdict: **gate not passed.** The two round-03 blockers that were numbers are now met on the hero (attic chroma, flutes), the coffers exist,
the cam02 station is on land, and the watchdog no longer kills renders — but the hero average did not move: what the hero gained in
ornament it lost in scale cues (the shoreline under the rotunda is now a bare pale quay with 0.5 m pom-pom shrubs where ref 169 has
2-4 m mounds and a willow), and two regressions appeared off-axis: the **Eevee ceiling is black** (coffer / own-sky 0.035 vs Cycles 0.26
vs ref 0.44) and the **cam03 foreground is crushed** (near shaft 7.3 vs ref 69.7, was 23.1). At 1:1 the hero stone still reads as clean
CAD: uniform ochre with std 55 % of the photo's, no streak under any cornice, no algae band, no dust in the recesses (round 3 of the
same finding). Explicit "clean CAD / game asset" rejects this round: hero stone at 1:1 (`round04_cam01_crops_vs_ref169.png`, panes 1-2:
attic and entablature are a single flat yellow with soft blotches; the photo is orange-brown with grey weathering and hard cornice shadows),
the cam04 ceiling (Cycles: clean-edged uniform-ochre boxes with no dirt gradient inside any coffer; Eevee: black), the hero shoreline
(pane 3: a pale unbroken concrete strip with dot shrubs, no damp band, no reeds), cam06 (identical box houses, dark olive far field).

## What works (keep it)

- Hero silhouette: apex within **0.78 %** of frame height of ref 169 (round 03: 1.0 %); wa 556 px / rise 0.223 vs photo 0.238.
- Attic chroma at delivery resolution (QA-03-2 attic half): hue 38.9, sat 0.554, R-B 121.9, lum 180.4 (ref 40.3 / 0.588 / 136 / 190):
  all four inside the acceptance box. Lighting's r10 numbers (0.549 / 120.8 / 180.9) reproduce on QA's own hero within 0.005 / 1.1 / 0.5.
- Flutes on the hero shafts (QA-03-4 flute half): the best front shaft (x 841-880, rows 360-400) shows **5 cycles with >= 10 % contrast**,
  the same count as ref 169's front shafts (4-5 by the same test); round 03 had 0-3.
- Capitals resolve into two leaf tiers with dark recesses at hero distance (QA-03-15 closed); attic panels read as figure groups.
- Coffers are real boxes in both engines and the rosettes sit on the base-ring face and coffer floors (QA-03-8 geometry half).
- cam05: no crown inside the rotunda silhouette (0.0 % foliage over the rotunda column band, QA-03-13 closed); dome visible.
- Near-water saturation 0.272 vs ref 0.249-0.270 (QA-03-7 sat half); ripple break-up now <= 15 px.
- cam06 dome-cap / far-shore contrast 1.02 -> **1.21:1**; horizon-band std-dev 15.5 -> 23.5; Marina/Presidio field present.
- Eevee previews twice as fast as round 03 on the same LOD1 scene; Cycles hero 128 spp uncapped in 335 s.
- Saved master carries the final preset (QA-03-17 closed): GPU, 768 adaptive (min 64), OIDN, AgX - High Contrast, exposure -2.833,
  `CAM_flythrough` + path + target present, no placeholder materials, open 0.69 s, LOD1 10.95 M tris.

## Measurements

### (a) Chroma at delivery resolution (Cycles hero 1920x1080, `light_r10_measure.py` boxes = QA round-03 boxes, ref = ref 169 aligned)

| region | box | round 03 | **round 04** | ref 169 | verdict |
|---|---|---|---|---|---|
| sunlit attic panel | 900 222 1020 256 | lum 178.0 hue 33.6 sat 0.429 R-B 92 | lum 180.4 hue 38.9 sat **0.554** R-B **122** | 189.6 / 40.3 / 0.588 / 136 | **pass** (>= 37 / >= 0.53 / >= 118 / lum +-10 %) |
| attic string course | 880 214 1040 222 | 167.0 / 34.3 / 0.445 / 90 | 166.4 / 39.7 / 0.568 / 115 | 181.9 / 39.3 / 0.580 / 129 | pass |
| entablature | 900 262 1020 296 | 168.1 / 33.1 / 0.445 / 91 | 161.7 / 39.4 / 0.634 / 128 | 146.4 / 34.0 / 0.604 / 115 | lum 1.10, hue +5 (too yellow) |
| dome cap | 920 95 1000 120 | 188.0 / 29.8 / 0.266 / 57 | 196.3 / 37.4 / 0.349 / 78 | 215.6 / 42.7 / 0.288 / 67 | lum 0.91, hue -5 |
| shaded north attic | 1110 225 1150 260 | 128.6 / 37.1 / 0.504 | 112.2 / **43.1** / **0.736** | 115.0 / **29.5** / 0.425 | lum ok; **shade 13.6 deg too yellow-green and 0.31 over-saturated** |
| columns (mask hue<32 sat>0.30, x 680-1240 y 280-470) | mask | 153.2 / 28.2 (1.60x) | **122.0** / 31.2 / 0.753 | 95.8 / 24.5 / 0.588 | **1.27x, fail** (test: within 25 % -> <= 120); hue +6.7 |
| water reflection column | 900 760 1020 840 | 144.3 / sat 0.174 | 145.9 / hue 42.7 / sat **0.146** | 168.9 / 33.7 / 0.339 | lum 0.86, sat -0.19: the sunlit stone reflects grey |
| near water, sky-reflecting | 1150 1000 1450 1050 | sat 0.382 hue 206 | sat **0.272** hue **208.7** | 0.249-0.270 / 189.9-192.1 | sat pass, hue fail (185-200) |
| lagoon flank | 100 900 400 960 | 146.9 | 171.1 | 155.2 | 1.10 ok |
| sky top / sky low-left | lighting's boxes | 154.2 / 144.0 | 167.9 / 154.8 -> ratio **0.922** | ref ratio 1.17 | fail (1.05-1.29): still no haze band |

### (b) Texture / weathering at 1:1 (luminance std-dev over matched boxes; test: render >= 60 % of the photo's)

| box | round 03 | round 04 | ref 169 | ratio |
|---|---|---|---|---|
| attic panel 900 222 1020 256 | 16.0 | 23.1 | 42.1 | **0.55** (was 0.38) |
| entablature 900 262 1020 296 | 28.3 | 35.3 | 65.2 | **0.54** (was 0.43) |
| stone crop 760 250 1230 460 | 43.1 | 57.1 | 63.8 | 0.89 (shadow structure, not surface) |

Flute modulation (horizontal luminance profile, rows 360-400, shafts found by hue < 40 / sat > 0.30, peaks separated by troughs
>= 10 % of the run mean): render shafts x 695-752: 1 cycle, 785-835: 2, **841-880: 5**, 1032-1073: 2, 1189-1223: 0; ref 169 (rows 373-404
mapped): 4, 5, 0, 2, 0 on its five shafts. The front-lit shafts now match the photo; the side-lit ones (1-2 vs 2-4) still lag.
In the crop pair there is **no readable dark streak under the main cornice or the string course**, no algae band at the waterline (the
shore strip is a uniform pale concrete), no dust gradient in the capital recesses beyond the AO of the leaf tiers.

### (c) Interior fills, cam04 vs ref 083 (boxes exactly as round 03 (e); ref soffit/sky 0.405, coffer/sky 0.437, soffit/coffer 0.93)

| ratio | ref 083 | r03 Eevee | r03 Cycles | **r04 Eevee** | **r04 Cycles 64 spp** | lighting r10 claim |
|---|---|---|---|---|---|---|
| soffit / own sky (W / E) | 0.405 | 0.80 | 0.70 | **0.40 / 0.14** (own sky 109.8; soffits 43.7 / 15.6) | **0.29 / 0.52** (sky 109.8; soffits 31.5 / 57.3) | 0.54 |
| coffer field / own sky | 0.437 | 1.04 | 1.00 | **0.035** (coffer 3.8) | **0.26** (coffer 28.7) | 0.38 |
| Eevee - Cycles gap (claimed <= 0.15) | | | | soffit E **0.38**, coffer **0.23** | | |

Cycles is now inside the soffit window on average (0.40) but the coffer field is 0.26 (window 0.35-0.55) — the rig went from 2x to
0.6x; Eevee is **black at the coffers** (3.8 / 255) and 0.14 on the east soffit, so the viewport ceiling is unusable and the "engine-
conditional cutoff" fix does not hold in QA's preview path (`apply_preview_eevee(samples=32)` on the saved master; the log shows
"vault emitters for EEVEE: 8 lights, x8.0 + 13 m cutoff" so the override *ran*). Coffer-field std-dev (0.40-0.60 box): Cycles 11.9 vs
ref 36.3 = 33 % (test >= 60 %) — but std/mean 0.42 vs 0.47 = 89 %, i.e. the coffers cast shadow now and only the level is wrong.

### (d) cam03, near shaft crop (0 150 420 720) and ground (420 560 900 720)

| | round 03 | round 04 | ref 128 |
|---|---|---|---|
| near shaft lum | 23.1 | **7.3** (hue 58, sat 0.62) | 69.7 (hue 39.5) |
| ground lum / std | 60.1 / 27.2 | **21.2** / 23.1 | (std test >= 12 pass) |
| flutes across the near shaft (rows 300-340) | none | **19 cycles >= 10 %** (profile 0.8-23.5) | resolved |

The shaft is fluted now (architecture / materials delivered) and 10x too dark (lighting: 0.10 of the photo, was 0.33) — the whole
colonnade-shade foreground collapsed with r10's exposure / sky-diffuse split. The ground reads as black with a texture.

### (e) Wings on the hero (Cycles; ref 169 raw mapping)

| band | round 03 | round 04 | ref 169 | ratio |
|---|---|---|---|---|
| north wing 60 480 560 600 | 87.0 | 90.2 | 109.5 (raw) / 137.2 (env aligned panel) | **0.82 / 0.66** — raw passes 25 %, aligned fails |
| south wing 1360 480 1860 600 | 112.6 | **91.6** | 146.5 | **0.63 — regression** (was 0.77) |

### (f) cam05 (35 mm) vs ref 063; cam06 vs ref 105

cam05: apex row 10 px = **1.4 % below the top** (test >= 3 %, QA-03-5 still fails, by 12 px); foliage inside the rotunda column band
(x 396-881, top 75 %) **0.0 %**; top crop (300 0 980 200) lum 168.2 sat 0.196 (r03 164.9 / 0.311; ref 183).
cam06: dome cap 118.0 vs far-shore band (0 40 1280 110) 97.8 -> **1.21:1** (r03 1.02; test >= 1.5); horizon crop (0 0 1280 220)
lum 101.4 hue 37.6 sat 0.466 std 23.5 (r03 135.0 / 39.4 / 0.269 / 15.5): the far field is darker, more saturated and more varied,
but it is still a plane of identical box houses under one olive tone; no paths readable at this size.

### (g) cam02 station search (QA-03-6 / QA-02-17) — decision

`scripts/qa_cam02_probe.py` (one Blender run): polar grid az 0-350 step 10, r 30-90 step 5, 468 stations; 127 on land (downward
ray hits terrain, not `ENV_water`); for each, the pitch is solved per lens (16-24 mm) so the rotunda's **visible top silhouette**
(281 vertical-ray top-surface points) sits 0.02 from the frame top, then the podium-base row (first rostra face on a z 1.5 ray, at
its ground line), attic width and tree / colonnade occlusion (ray casts to ~150 silhouette points) are recorded.

Two facts the sweep exposed. (1) From eye level the dome apex (53.4 m, the lead's photo-derived value) clears the near attic top
(z 38.3 at r 24.4) only beyond ~77 m (52.6 / D > 37.5 / (D - 22)); closer, the frame top lands on the near attic / entablature.
(2) With the visible top at 0.02, every NE-peninsula station (<= 47 m, the photo's own side) puts the podium base at **1.02-1.25 of
the frame height at 16 mm** — the build's rotunda needs a 13 mm lens from there. The lead's finding (40-60 m N/NW/W stations behind
the colonnade or under crowns) is confirmed: az 200-210 r 50-60 occC 0.66-0.87, az 340-10 r 65-80 occT 0.29-0.54.

| candidate | loc | lens | top | apex | base | attic W | occ tree | face off | remark |
|---|---|---|---|---|---|---|---|---|---|
| **az160_r75 (chosen)** | (70.5, 25.6, 1.1) | **24** | 0.020 | 0.070 | **0.861** | 0.405 | 0.07 | 12 | SSE shore path; dome peeks over the attic as in the photo; south colonnade behind-left |
| az180_r60 | (60.0, 0.0, 1.0) | 18 | 0.020 | 0.101 | 0.820 | 0.382 | 0.09 | 8 | colonnade column at the left edge, water bottom-right |
| az160_r90 | (84.6, 30.8) | 24 | 0.020 | 0.050 | 0.728 | 0.344 | 0.06 | 12 | no foreground water; base 12 % short |
| az070_r45 (NE, photo's side) | (-15.4, 42.3, 0.8) | 16 | 0.020 | 0.206 | **1.025** | 0.409 | 0.00 | 12 | podium base out of frame; rostra loom |

Chosen: **`CAM_qa_02` = (70.5, 25.6, 1.1) -> (0, 0, 21.1), 24 mm** (written to `scripts/qa_cameras.py`). Letterboxed check on the
rendered frame vs ref 062: top silhouette 0.000-0.019 vs 0.010-0.032 (median), building extent at y = 0.25: 0.442 vs 0.480 of the
width, base 0.86 vs 0.85; tree occlusion 7 %. Two deviations from the brief, both unavoidable on this build: 75 m (brief said
30-70; at 70 m the base falls to 0.89) and a strip of south-embayment water in the bottom 12 % of the frame (every on-land
station that frames the base is across an embayment). The ref 062 photo stays; the photo's exact NE station is not reproducible
until the rotunda's height-to-width ratio or the podium radius is re-checked (see QA-04-11).

## Viewport performance (pass/fail, not scored)

- Open **0.69 s** headless (budget 60 s) — pass. 8736 objects, 63 materials, 0 placeholder materials, file 153.5 MB.
- LOD1 **10.95 M tris** (round 03: 11.62 M) — pass.
- Eevee 1280x720 previews **11.5-24.3 s per camera** at LOD1 (round 03: 25-53 s) — pass.
- Cycles hero 1920x1080 128 spp adaptive: 335 s uncapped (GPU); cam04 64 spp 1280x720: 211 s.

## Deliverables present (pass/fail)

- **Cycles final config: pass, as saved** — device GPU, 768 spp adaptive (threshold 0.01, min 64), OIDN, time limit 0, look
  `AgX - High Contrast`, exposure -2.833. QA-03-17 closed.
- **`CAM_flythrough_path`: pass** — `CAM_flythrough`, `CAM_flythrough_path` (curve), `CAM_flythrough_target` present.
- **Eevee viewport config: pass with a note** — saved state is taa 8 / 16 render samples, **raytracing off**, 2 baked irradiance
  volumes (`LIGHTPROBE_colonnade`, `LIGHTPROBE_rotunda`). Round 03's saved file had taa 16/32 and raytracing on; the lead's
  `apply_viewport_eevee` at the end of `build_master` changed it (QA-04-12: confirm intended).
- **Eevee navigability of the ceiling: FAIL** — the vault is black in the saved Eevee state (QA-04-1).
- Phase-5 items (4K hero, low-res Eevee animation): not due; 4K timing test in the section below.

## Status of every round-03 defect

| defect | owner | status | the number |
|---|---|---|---|
| QA-03-1 watchdog kills GPU renders | lead | **closed** | 128-spp hero 335 s and cam04 211 s both completed under the centisecond-cputime watchdog (7c164d5). |
| QA-03-2 chroma at delivery resolution | lighting + materials | **half closed** | attic hue 38.9 / sat 0.554 / R-B 122 / lum 180 all pass; **columns 1.27x** (test <= 1.25x, i.e. <= 120 lum) and hue +6.7 fail; shade hue 43.1 vs 29.5 fails (new QA-04-2). |
| QA-03-3 interior fills 2x | lighting | **open, over-corrected** | Cycles soffit 0.40 (pass), coffer 0.26 (fail low); Eevee soffit 0.40 / 0.14, coffer 0.035 (black). Eevee-Cycles gap 0.23-0.38, not <= 0.15. |
| QA-03-4 clean-CAD hero stone / flutes | materials + architecture | **flutes closed; stone open** | best shaft 5 cycles >= 10 % (= ref); attic std 0.55 and entablature 0.54 of the photo (test 0.60); no cornice streak in the crop pair. |
| QA-03-5 cam05 apex clipped | lead | **open (minor)** | apex 1.4 % below the top edge at 35 mm; test >= 3 % (12 px short). |
| QA-03-6 cam02 station | lead -> QA | **closed by QA re-station** | (70.5, 25.6, 1.1) / 24 mm; top 0.00-0.02, base 0.86, width 0.44 vs photo 0.48; see (g) for the two deviations. |
| QA-03-7 near-water sat / ripple scale | materials | **half closed** | sat 0.272 (0.22-0.32 pass); hue 208.7 (185-200 fail); break-up <= 15 px pass. |
| QA-03-8 flat coffers | ornament + architecture | **geometry closed; test open** | coffers cast shadow in both engines (std/mean 0.42 vs ref 0.47) but absolute std 33 % of ref because the field is dark (QA-03-3). 16 + 8 rosettes visible at cam04. |
| QA-03-9 cam03 near shaft | materials + architecture + environment (+ lighting) | **flutes closed; brightness regressed** | 19 flute cycles; shaft lum 7.3 vs ref 69.7 (0.10, was 0.33); ground 21.2 (std 23 passes, level fails). |
| QA-03-10 north wing dark | environment | **half closed** | 0.82 of ref by the raw mapping (pass 25 %), 0.66 by the aligned panel (fail); south wing regressed to 0.63 (QA-04-6). |
| QA-03-11 cam06 backdrop | environment + lighting | **improved, open** | dome / far shore 1.21:1 (test 1.5); horizon std 23.5 (was 15.5); houses still identical boxes on one olive plane. |
| QA-03-12 sky haze band | lighting | **open** | sky_left / sky_top 0.922 vs 1.17. |
| QA-03-13 cam05 conifers / podium band | environment | **closed** | 0.0 % foliage over the rotunda band; podium band visible across the rotunda. |
| QA-03-14 shore shrubs | environment | **open, changed** | the row is now 0.5-1 m dots on a bare pale strip (crop 700 640 1200 720: lum 118 hue 41, a flat quay); ref 169 has 2-4 m mounds and a willow. |
| QA-03-15 capitals blobs | ornament | **closed** | two leaf tiers with dark recesses in the 1:1 pair; cavity attribute visible. |
| QA-03-16 4K timing | lead + lighting | **open; compositor exonerated** | 4K 16 spp: compositor off 177.1 s / on 175.3 s, both frames written; no 768-spp 4K frame yet. |
| QA-03-17 saved preset | lead + lighting | **closed** | GPU / 768 adaptive / OIDN / High Contrast / exposure -2.833 as saved. |

## Defect list — round 04

| id | cam | owner | severity | description (measurable) | where | acceptance test |
|---|---|---|---|---|---|---|
| QA-04-1 | 04 | lighting (+ lead's review fix) | **blocker** | Eevee vault black: coffer / own-sky **0.035**, soffit E 0.14, soffit W 0.40 on the saved master through `apply_preview_eevee`; Cycles 0.26 / 0.52 / 0.29. The viewport ceiling is unreadable and the Eevee-Cycles gap is 0.23-0.38. The x8 / 13 m override ran (log line present) and still starves the coffers: cutoff too short for the 23-40 m vault, or energy_W seeded from the boosted value. | `light_presets.apply_viewport_eevee / apply_preview_eevee`, `VAULT_FILL`, `cutoff_distance` | QA's boxes (round 03 (e)): Eevee soffit and coffer ratios within 0.15 of Cycles, Cycles coffer / sky 0.35-0.55. |
| QA-04-2 | 03, 01 | lighting | **blocker** | Shade collapsed and turned yellow-green: cam03 near shaft **7.3 vs ref 69.7** (0.10; r03 0.33), ground 21.2 (r03 60.1); hero shaded attic hue **43.1 / sat 0.736** vs 29.5 / 0.425 (r03 37.1 / 0.504). Round 10's exposure drop and camera / glossy / diffuse sky split removed the diffuse-sky share that lit the shade; what remains is bounced yellow off the stone. | `EXPOSURE_BIAS`, sky diffuse share, `SKY_*_BOOST` split | cam03 crop (0 150 420 720) lum within 30 % of 69.7 and hue 34-42; hero box (1110 225 1150 260) hue 29.5 +- 6, sat <= 0.50, lum within 15 % of 115. |
| QA-04-3 | 01, 05, 02 | materials | **blocker** | Stone still clean CAD at 1:1 (round 3 of QA-02-2/-3/QA-03-4): attic std **0.55** and entablature **0.54** of the photo's; no dark streak under the main cornice or string course in `round04_cam01_crops_vs_ref169.png` pane 2; no damp / algae band at the waterline (pane 3: the shore strip is one uniform pale concrete tone, lum 118 std low); recess dust limited to leaf AO. | `MAT_concrete_*` streak / recess masks (0.31 m streaks, 0.20 m edge claimed but invisible at hero scale), `ARCH_site_rostra_*` waterline band | std ratio >= 0.60 on both boxes; a streak visibly darker than its field by >= 15 lum under the cornice over >= 30 % of its length; a 0.3-0.6 m band >= 20 lum darker than the wall above it along the waterline in pane 3. |
| QA-04-4 | 01 | environment | major | Shoreline under the rotunda is a bare pale quay: shrub band (700 640 1200 720) shows 0.5-1 m dot shrubs at ~40 px spacing and an exposed podium base; ref 169 has 2-4 m mounded shrubs and a willow crown at frame-left hiding the base entirely. Scale cues drop 3.5 -> 3. | `ENV_shrubs_shore`, `ENV_shrubs_pen`, willow placement (r5 "pinned groups") | shrub heights 1.5-4 m along the shore band, size spread >= 2:1, >= 60 % of the podium base hidden at cam01, a willow silhouette in frame-left as in ref 169. |
| QA-04-5 | 01 | lighting + materials | major | Columns 1.27x too bright (122 vs 95.8; test <= 120) and 6.7 deg too yellow (31.2 vs 24.5), sat 0.753 vs 0.588: the shafts are lit like the sunlit attic (0.68 of attic; ref 0.51). Half of QA-03-2. | `SKY_GLOSSY_BOOST` on the shafts, `MAT_column_*` chroma | column mask lum 72-120 and hue 20-29 on the 1920x1080 hero. |
| QA-04-6 | 01 | lighting + environment | major | South wing band (1360 480 1860 600) **0.63** of ref (91.6 vs 146.5), regressed from 0.77; north wing 0.82 raw / 0.66 aligned. Both wings read as dull ochre masses beside the photo's sunlit colonnades. | sun elevation / wing shading trees, `EXPOSURE_BIAS` | both bands within 25 % of ref by both panels. |
| QA-04-7 | 04 | lighting + materials | major | Cycles coffer field / sky 0.26 (window 0.35-0.55) and the ceiling reads as clean CAD: uniform ochre boxes with clean edges, no dirt gradient inside any coffer, no tonal difference between rib and panel (ribs share the panel material; ARCH rib plate material name still pending). | `VAULT_FILL`, `MAT_concrete_*` on `ARCH_rotunda_vault_coffers_*`, rib plate material | coffer / sky 0.35-0.55 in Cycles; coffer-field std >= 60 % of ref 083's; visible rib / panel tone split >= 10 lum. |
| QA-04-8 | 01 | environment + materials | major | Sky-reflecting near water hue **208.7** vs 190-192 (blue, not teal) at the settled crop; the reflection of the sunlit stone (900 760 1020 840) is grey: sat 0.146 vs 0.339, lum 0.86. The lagoon reflects the sky correctly and the building weakly. | `MAT_water_lagoon` murk / upwelling tint, reflection tint | crop hue 185-200; reflection column sat >= 0.28 and lum within 10 %. |
| QA-04-9 | 01 | lighting | minor | Sky haze band: sky_left / sky_top 0.922 vs 1.17 (QA-03-12 carried). | sky `aerosol_density`, `SKY_CAMERA_BOOST` gradient | ratio 1.05-1.29. |
| QA-04-10 | 05 | lead | minor | cam05 apex 1.4 % below the top edge (QA-03-5 carried): tilt down ~12 px or 35 -> 33 mm. | `CAM_qa_05_south_lawn` | apex >= 3 % below the top. |
| QA-04-11 | 02 | architecture + lead | minor | The ref 062 station (NE, ~50 m, 26 mm, dome cap visible over the attic, base at 0.85) cannot be reproduced on the build: from eye level the apex clears the near attic only beyond ~77 m and the apex-to-base span needs 13 mm at 45 m. Either the attic / drum are too tall for the dome, or the podium (rostra) radius is too large, or the photo was taken from farther away with a longer lens. | `arch_params` attic 31.2-38.3, drum, `ARCH_site_rostra_*` radius | one documented station (D, lens, height) at which the letterboxed blend of ref 062 aligns top, base and width within 3 %. |
| QA-04-12 | — | lead | minor | Saved Eevee viewport state changed: taa 8 / 16, raytracing off (round 03: 16 / 32, on). If intended for viewport speed, log it in decisions.md; otherwise restore. | `build_master.py` -> `apply_viewport_eevee` | decision logged or state restored. |
| QA-04-13 | 06 | environment + lighting | minor | Far field: dome / far shore 1.21:1 (test 1.5); horizon crop shows one house model repeated with one roof colour, no paths, dark olive forest at sat 0.47. | `ENV_backdrop_*`, `env_city.py` variants, mist | >= 3 roof colours and >= 2 house footprints in the horizon crop; contrast >= 1.5:1. |
| QA-04-14 | 02 | environment | minor | cam02's foreground strip is flat black-blue water with no ripple or shore edge; the shrubs on the far shore are dots. | `MAT_water_lagoon` near-field, south-embayment shore planting | ripple break-up and a rip-rap / reed edge readable in the bottom 12 % of the frame. |

## 4K isolating test (QA-03-16)

Run after the round-04 commit (f4b4b33) with no other Blender on the GPU: `scripts/qa_4k_probe.py -- --samples 16 --modes off,on
--time-limit 1200` (log `renders/logs/qa_round04_4k.log`). Hero camera, 3840x2160, Cycles GPU, 16 spp, OIDN, `apply_final_cycles`;
compositor tree `COMP_scene_golden_hour` (3 nodes).

| compositor | wall | frame written |
|---|---|---|
| **off** (`render.use_compositing = False`) | **177.1 s** | yes, 12.9 MB |
| **on** | **175.3 s** | yes, 13.3 MB |

The compositor pass is **exonerated**: on / off differ by 2 s and both frames are written. Whatever stalled lighting's 60- and 92-minute
runs is in the 768-spp sampling / denoise tail, not the compositor: scaling from this round's 1080p 128 spp (335 s) the 4K frame at
128 spp is ~22 min and at 768 adaptive plausibly 45-90 min of GPU sampling before OIDN runs on a 4K buffer, i.e. the runs were killed
or gave up inside normal sampling time. Note for Blender 5.2: `scene.node_tree` / `scene.use_nodes` no longer exist; the compositor is
`scene.compositing_node_group` and `render.use_compositing`. Recommended next step for lighting: one 4K frame at 128 spp fixed
(no adaptive, `time_limit` 0) with progress logged, then 768 adaptive; QA-03-16 stays **open** until a 768-spp 4K frame exists.

## Notes for the lead

1. The hero is stuck at 3.28 for a structural reason: every round fixes numbers on the stone (exposure, chroma, flutes) and the surface
   still has no weathering signal at hero scale. Materials' streak (0.31 m) and edge (0.20 m) inputs are invisible in the crop pair;
   the acceptance is a *visible* dark streak and a waterline band, not a parameter. That is the one defect whose closure would move the
   gate more than any other.
2. Lighting r10 traded shade for chroma: the attic passes, the shade (cam03, coffers in Eevee, wings, shaded attic hue) regressed. The
   next lighting round needs QA-04-1 and -2 measured on cam03 and cam04 *before* touching the hero numbers again.
3. The cam02 station is now a QA-owned decision with its reasoning in (g); QA-04-11 is the geometric question it raised.
