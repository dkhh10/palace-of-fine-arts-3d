# QA round 03 — Phase 4 polish round 1 gate (2026-09-07)

QA / Critic (Fable 5.1, xhigh). Reviewed `master.blend` (153 MB, rebuilt by `scripts/lead_build.sh` at 20:12 after
all five p4r1 branches were merged: architecture, environment 9a68bc1, ornament b509ce8, materials e550acc,
lighting d62402d): **9041 objects, LOD1 11.62 M tris** (lead's build number; 15.18 M in round 02), probes baked,
cam03 and cam05 re-stationed, Eevee previews at LOD1. First round rendered on a quiet machine.

## What was rendered and compared

| file | what |
|---|---|
| `renders/previews/qa/round03_0K_*.png` | Eevee 1280x720, 32 TAA, **LOD1**, `apply_preview_eevee`. Times: **36.4 / 38.1 / 52.9 / 33.3 / 35.0 / 25.3 s** (round 02 at LOD0: 46.3 / 45.4 / 36.7 / 33.6 / 54.8 / 32.8). Whole pass incl. open 221 s. |
| `renders/previews/qa/round03_01_lagoon_hero_cycles.png` | Cycles 1920x1080, 128 spp adaptive requested, **sampling capped at 270 s** (see QA-03-1), OIDN, GPU. 277 s wall. |
| `renders/previews/qa/round03_04_rotunda_ceiling_cycles.png` | Cycles 1920x1080, 64 spp, 270 s cap (251 s wall, 64 spp reached), the extra interior-fill check. |
| `renders/qa_comparisons/round03_cam0K.png`, `round03_sheet.png` | render / canonical photo / 50 % blend per camera, contact sheet |
| `round03_cam01_aligned_vs_ref169 / _vs_ref085 / _vs_user.png` | W_a-aligned overlays (the 2 % silhouette test) |
| `round03_cam01_crops_vs_ref169.png` | 1:1 crop pairs (stone, waterline, shore shrubs, near water) with boxes and numbers burnt in |
| **`renders/qa_comparisons/round03_gate.png`** | **the gate composite**: Cycles hero beside ref 169, six Eevee views, score deltas |

Commands: `blender -b --python scripts/qa_render_round.py -- --round 03 --eevee`, then
`-- --round 03 --final --samples 128 --time-limit 270 --res 1920 1080 --cams 01` and `--samples 64 --time-limit 270 --cams 04`.
New tools (QA-owned): `scripts/qa_crops.py` (matched crop pairs via the alignment transform, stats burnt in),
`scripts/qa_inspect.py` (deliverables / perf inspection of master.blend, read-only). `qa_gate_sheet.py` now takes any round.

**Render-infrastructure incident.** The lead's `scripts/blender_watchdog.sh --loop` killed my first 128-spp hero at
330 s ("no CPU progress"): a Cycles render on the Metal GPU sits in `MetalDeviceQueue::synchronize()` and the Blender
*process* CPU time does not advance (sampled: 8.9 s CPU after 105 s wall, 0.0 %). The renders in this round were
therefore re-run with Cycles' own `time_limit` = 270 s so that sampling ends before the watchdog's 300 s. The hero
survived (277 s); the cam04 frame at the same cap was killed a second time at 20:40:25 because the cap covers sampling
only and GPU denoising pushed the no-CPU window past 300 s, so it was re-run at a 180 s cap. The hero is consequently
below the 128-spp spec in its slowest tiles (round 02's uncapped 128 spp took 446 s). See QA-03-1.

## Score table (0-5; target >= 4 every row, hero average >= 4.5). Round 02 -> round 03.

| row | cam01 hero | cam02 NE 3/4 | cam03 colonnade | cam04 ceiling | cam05 S lawn | cam06 aerial |
|---|---|---|---|---|---|---|
| Silhouette match | 4 -> **4** | 2 -> **2** | 1.5 -> **2.5** | 3.5 -> **3.5** | 2 -> **3** | 4 -> **4** |
| Proportion | 3.5 -> **4** | 3 -> **3** | 3 -> **3** | 3.5 -> **3.5** | 3 -> **3** | 3.5 -> **3.5** |
| Ornament fidelity | 3 -> **3** | 2.5 -> **2.5** | 2.5 -> **2.5** | 1.5 -> **1.5** | 2 -> **3** | 2.5 -> **2.5** |
| Material realism | 2.5 -> **3** | 2 -> **2.5** | 2 -> **1.5** | 2 -> **1.5** | 2 -> **2.5** | 1.5 -> **1.5** |
| Edge wear | 1 -> **1.5** | 1 -> **1** | 1 -> **0.5** | 0.5 -> **0.5** | 1 -> **1.5** | 0.5 -> **0.5** |
| Lighting mood | 3.5 -> **4** | 2.5 -> **3** | 2 -> **2.5** | 3 -> **2** | 3 -> **3.5** | 2 -> **2** |
| Water reflection | 3 -> **3.5** | 2 -> **2.5** | n/a | n/a | 2 -> **2.5** | 1.5 -> **1.5** |
| Repetition visibility | 2.5 -> **3** | 2 -> **2** | 2 -> **2** | 2 -> **2** | 2 -> **2.5** | 2 -> **2** |
| Scale cues | 3.5 -> **3.5** | 2 -> **2.5** | 1.5 -> **2.5** | 2.5 -> **2.5** | 2 -> **2.5** | 2 -> **2** |
| **average** | **2.94 -> 3.28 (+0.34)** | 2.11 -> 2.33 (+0.22) | 1.94 -> 2.13 (+0.19) | 2.31 -> 2.13 (**-0.19**) | 2.11 -> 2.67 (+0.56) | 2.17 -> 2.17 (0.00) |

Rows that went **down**: cam03 Material / Edge wear because the re-stationed camera now puts a shaft 3 m from the lens
and it is a smooth unfluted cylinder on a flat olive plane (QA-03-9); cam04 Lighting because the halved sky left the
interior fills ~2x too strong and the ceiling is now floodlit with no shadow depth (QA-03-3, coffer/sky 1.04 vs 0.44).

**Gate verdict: not passed.** The hero moved the most in one round since round 01 (+0.34) and three of round 02's four
blockers are closed or mostly closed (exposure, blotch/olive stone, cam05 dome — the last by camera, see below). What
remains is the same headline as attempts 1 and 2, now with numbers at delivery resolution: at 1:1 the hero stone is a
**uniform clean ochre with no flutes, no streaks and no recess dirt** (crop x 760-1230 y 250-460 against ref 169 at the
same scale), the sunlit stone is **6.4 deg cool and 0.16 under-saturated** (R-B 92 vs 138), and the interior is floodlit.
Explicit "clean CAD / game asset" rejects this round: hero stone at 1:1 (QA-03-4), the cam03 near shaft and ground
(QA-03-9), the cam04 ceiling (QA-03-3/-8), the cam06 backdrop (QA-03-11).

## What works (keep it)

- **Silhouette holds after every merge.** Cycles hero apex **+1.01 %** of frame height vs ref 169 (round 02: +1.32 %),
  **-0.62 %** vs ref 085, **-0.50 %** vs the user image; rise / W_a 0.222 (refs 0.242 / 0.211 / 0.213). W_a 562 px.
- **Exposure (QA-02-4) is closed at the AgX response.** Sunlit attic front panel lum 178.0 vs ref 169's 189.9 (0.94,
  inside +-10 %); sky top at lighting's boxes 154.2 vs 165.7 (0.93); water reflection column 144.3 vs 169.5 (0.85);
  shaded north attic 128.6 vs 115.2 (1.12). Materials' "+1 EV" no longer stands: another stop would put the attic at
  ~210 and the sky at ~186, both over the +10 % line.
- **Blotch / olive / hue-spread stone (QA-02-2) closed.** No hard-edged patch wider than 20 px in the 1:1 crop; shaded
  stone hue 36.9-37.1 (band 34-42); capitals no longer differ by hue.
- **Lagoon tonal range (QA-02-6) closed.** Mid-left flank 146.9 vs ref 129.6 (1.13; round 02: 0.26); reflection column
  0.85 of the photo's; ripples, murk and Fresnel all read.
- **Eevee got faster while the scene got bigger**: LOD1 previews 25-53 s (round 02 LOD0: 33-55 s) with 9041 objects.
- **cam05 now shows the dome and drum** (round 02: a sliver of drum wall), the attic relief reads as three registers of
  figures with real shadow, and the corner figures have cascades.
- **Haze colour (QA-02-8, half)**: cam06 far shore hue 39.3 sat 0.296 (round 02: hue 60-76, sat 0.08).

## Measurements

### (c) The near-water saturation dispute — ONE crop, settled

Three agents measured three different patches: QA round 02 (sat 0.426, an off-axis patch), ENV (0.11, from the
round-02 aligned panel), MAT (0.611, a warm reflection patch). Ref 169's near water is genuinely bimodal: where it
reflects sky it is grey-teal, where it reflects the sunlit shore it is warm brown. The acceptance crop is the sky
reflecting one, because that is the patch the cyan complaint was about:

| crop | hero 1920x1080 box (x0 y0 x1 y1) | ref 169 box (raw file, 1920x1192) | render | ref 169 |
|---|---|---|---|---|
| **near water, sky-reflecting (THE crop)** | **1150 1000 1450 1050** | **1103 863 1332 901** | 85,114,137 · hue 206.3 · **sat 0.382** · lum 109.8 | 87,113,119 · hue 191.9 · **sat 0.269** · lum 107.6 |
| near water, shore-reflecting (for reference) | 760 1000 1160 1060 | 805 863 1111 909 | 104,77,52 · hue 28.7 · sat 0.501 · lum 80.7 | 116,79,42 · hue 30.3 · sat 0.636 · lum 84.4 |

Mapping: ref pixel = (render pixel - (dx, dy)) / s with s 1.307, dx -291.5, dy -128.1 (this round's align transform).
Verdict: luminance matches (1.02); the render is **0.11 too saturated and 14 deg too blue** in the sky-reflecting water
(target sat 0.22-0.32, hue 185-200) and slightly *under*-saturated in the warm reflection. ENV's 0.11 came from the
round-02 aligned panel, which is scaled/resampled and 0.16 lower than the raw file at the same place; use the raw box.

### (d) Chroma at delivery resolution (1920x1080 Cycles hero vs ref 169, matched boxes via the align transform)

| region | render box | render | ref 169 (mapped box) | delta |
|---|---|---|---|---|
| sunlit attic front panel | 900 222 1020 256 | 213,173,122 · lum **178.0** · hue **33.6** · sat **0.429** · R-B **92** | 233,187,95 · lum 189.9 · hue 40.0 · sat 0.591 · R-B 138 | lum 0.94 ok; hue **-6.4**; sat **-0.16**; R-B **-46** |
| attic string course | 880 214 1040 222 | 201,163,111 · lum 167.0 · hue 34.3 · R-B 89 | 224,179,94 · lum 182.2 · hue 39.1 · R-B 130 | hue -4.8, R-B -41 |
| entablature front | 900 262 1020 296 | 204,163,113 · lum 168.1 · hue 33.1 · sat 0.445 · R-B 91 | 191,141,76 · lum 147.3 · hue 33.9 · sat 0.600 · R-B 115 | lum 1.14; sat -0.16 |
| dome cap | 920 95 1000 120 | 212,184,156 · lum 188.0 · hue 29.8 · sat 0.266 · R-B 57 | 233,213,165 · lum 213.9 · hue 42.3 · sat 0.291 · R-B 68 | lum 0.88; hue **-12.5** |
| columns (mask hue<32, sat>0.30 inside x 680-1240 y 280-470) | mask | 177,127,81 · lum **134.4** · hue 28.5 · sat 0.542 · R-B 96 (13 228 px) | 124,80,52 · lum **87.2** · hue 23.6 · sat 0.582 · R-B 72 (23 866 px) | lum **1.54**; hue +4.9 |
| shaded north attic | 1110 225 1150 260 | 156,126,77 · lum 128.6 · hue 37.1 · sat 0.504 | 141,111,81 · lum 115.2 · hue 29.5 · sat 0.425 | lum 1.12 ok |
| sky top (lighting's boxes) | 0.63-0.88 x 0.02-0.07 | 117,161,199 · lum 154.2 · sat 0.415 | 116,174,226 · lum 165.7 · sat 0.487 | 0.93 ok |
| sky low left (lighting's boxes) | 0.02-0.10 x 0.085-0.145 | 104,151,192 · lum 144.0 | 159,200,235 · lum 193.8 | **0.74** — no haze band toward the horizon |
| water reflection column | 900 760 1020 840 | 154,143,127 · lum 144.3 · sat 0.174 | 195,166,129 · lum 169.5 · sat 0.338 | 0.85; sat -0.16 |

Lighting's own re-measure (attic lum 167.9, R-B 97.4 at its `attic_sunlit_b` box) is reproduced exactly here
(167.8 / 97.5) — but that box sits on the **drum** in the render frame (y 157-189 is above the attic corner top at
y 213) and on the attic in the photo frame; the matched attic panel is 178 / 92. Either way the conclusion is the
same: **luminance is in, chroma is not**: hue 6 deg cool on the attic, 12 deg on the dome, saturation 0.16 short, R-B
spread 92 against 138 (the 110 floor is not met). The 960x540 sweep numbers (R-B 113-118) were optimistic by ~20, as
lighting warned. The columns are the opposite problem: 54 % too bright and 5 deg too yellow — in ref 169 the shafts sit
in the entablature's shadow as a dark dusty terracotta; in the render they are lit almost like the sunlit attic
(134 vs 178 = 0.75; ref 87 vs 190 = 0.46). That is fill / sky-glossy light on the shafts, not albedo.

### (b) QA-02-1 re-test at the re-stationed cam05 (28.1, 111.8, 1.5) / 40 mm, ref 063

Metric (defined once, applied to both): first-non-sky row profile across the rotunda; attic extent = columns where
the profile jumps from the sky to the attic corner blocks; front attic cornice = the dark edge under the drum at the
rotunda's centre column; rise = cornice row - apex row, as % of the attic extent.

| | render (1280x720) | ref 063 (1920x1280) |
|---|---|---|
| attic extent | x 340-930 = **590 px** | x 534-1452 = **918 px** |
| apex row | **0 — clipped by the frame** (rows 0-3 over x 480-760 are dome: 203,175,142) | 57 |
| drum-top / dome-base dark edge (centre column) | 42-45 (lum 95-117) | 88-102 (lum 96-118) |
| attic cornice dark edge (centre column) | 115-117 (lum 82-129) | 111-121 (lum 96-127) |
| dome cap depth (cap only) / extent | >= 42 / 590 = **>= 7.1 %** | 31 / 918 = **3.4 %** |
| dome + drum rise above the attic cornice / extent | >= 115 / 590 = **>= 19.5 %** | 64 / 918 = **7.0 %** |

Round 02's "12.2 %" for ref 063 used a hand crop with the attic top taken at a side corner (y ~150); the numbers above
use the front cornice for both images, so they are the ones to carry forward. The render now shows **more** drum than
the photo, not less — because the station changed (115 m / 40 mm vs the photo's closer, lower-angle station: its attic
spans 48 % of frame width with strong perspective on the corner blocks), not because the geometry changed. Two
consequences: (1) QA-02-1 as written ("visible rise >= 9 % from CAM_qa_05") is met, but by the camera, so it is
**closed by camera, geometry unverified at the photo's station**; (2) the apex is cut off by the top of the frame,
which fails the camera itself (QA-03-5): tilt up or 40 -> 35 mm so the apex sits >= 3 % below the top edge.

### (e) Interior fill check, cam04 vs ref 083 (boxes as fractions of the frame; ref 083 boxes re-picked this round)

Ref 083 boxes: sky = bottom-left wedge (0.00-0.10, 0.93-1.00) -> 153,181,216 lum 177.8; soffit W (0.10-0.20,
0.28-0.50) lum 67.8, soffit E (0.80-0.90, 0.28-0.50) lum 76.2; coffer field (0.40-0.60 sq) lum 77.7.
Render boxes (lighting's `light_measure.REGIONS["ceiling"]`): own_sky (0.005-0.05, 0.83-0.95), soffit W
(0.075-0.15, 0.28-0.50), soffit E (0.80-0.875, 0.30-0.52), coffer (0.40-0.60 sq).

| ratio | ref 083 | round 02 Eevee | round 03 Eevee | round 03 Cycles 64 spp |
|---|---|---|---|---|
| mean soffit / own sky | **0.405** (0.38 / 0.43) | 0.20 | **0.80** (0.75 / 0.86; sky 112.5, soffits 83.9 / 96.8) | **0.70** (0.67 / 0.73; sky 112.1, soffits 74.9 / 82.0) |
| coffer field / own sky | **0.437** | 0.50 | **1.04** (coffer 116.9) | **1.00** (coffer 112.6) |
| soffit / coffer | 0.93 | 0.40 | 0.77 | 0.70 |

Round 02's "0.58 / 0.39" used a brighter ref sky patch; with the boxes fixed above the reference ratios are 0.405 and
0.437 and the photo's soffit-brighter-than-coffer inversion is 0.93, not 1.5. Lighting's belief is confirmed: with the sky
halved and FILL 7600 / VAULT_FILL 2400 unchanged, the interior sits at **~2x** the photo's ratios in Eevee
(1.7x / 2.3x in Cycles). Halving both fills is the right first move; then re-measure with exactly these boxes.

### (f) Exposure

QA-02-4 **closed**: attic 178.0 / 189.9 = 0.94, sky top 0.93, reflection 0.85, shade 1.12 — all inside +-10 % except
the reflection (-15 %, water/materials, not exposure). Materials' +1 EV request is **withdrawn by measurement**: the
deficit that motivated it is chroma (sat -0.16, R-B -46), and the measured AgX response (-1.1 deg hue and ~+32 lum per
EV) means another stop would blow the attic to ~210 and change hue by only ~1 deg. Do not move `view_settings.exposure`
(-2.39) again; move sun colour / sky share / albedo chroma (QA-03-2).

### Other regions (Cycles hero unless stated)

| measure | render | reference | note |
|---|---|---|---|
| north wing band (60 480 560 600) | lum 87.0 | ref 169 109.5 (raw mapping) / 137.2 (env_measure's round-02 aligned panel) | **0.79 / 0.63** — still dark; QA-02-7 half open |
| south wing band (1360 480 1860 600) | lum 112.6 | 146.5 / 141.0 | 0.77 / 0.80 — passes the 25 % test by env_measure, marginal by raw mapping |
| lagoon flank (100 900 400 960) | lum 146.9 | 129.6 | 1.13 — QA-02-6 closed |
| cam06 far shore (Eevee) | hue 39.3 sat 0.296 lum 131.2 | — | haze now warm; **dome cap 136.8 vs far shore 131.2 = 1.04:1** contrast, still one beige |
| cam06 lawn / far hills / lagoon far | sat 0.26-0.27, lum 133-137 | — | everything past 150 m is the same tone |
| cam03 near shaft (0 150 420 720) | lum 23.1 hue 55 | ref 128 shaft (0 700 700 2560) lum 69.7 hue 39.5 | 3x too dark, no flutes, base a smooth flare |
| cam05 top crop (300 0 980 200) | lum 164.9 sat 0.311 | ref 063 (470 0 1520 300) lum 183 | relief legible; stone uniform; apex clipped |

## Viewport performance (pass/fail, not scored)

Measured with `blender -b --python scripts/qa_inspect.py` (read-only) on the 20:12 master.blend, while lighting's sweep shared the GPU.

- **master.blend open time: 0.96 s** headless (1.8 s in round 02), 153.1 MB, 9041 objects, 34 materials, 0 placeholders. Budget 60 s — **pass**.
- **Viewport LOD1 triangles: 11.62 M** (sum of mesh triangles over objects visible at LOD1; no collection instances), down from 15.18 M in round 02 with 3000 more objects — **pass**.
- **Eevee preview seconds per QA camera (LOD1, quiet machine): 36.4 / 38.1 / 52.9 / 33.3 / 35.0 / 25.3** (round 02 at LOD0: 46.3 / 45.4 / 36.7 / 33.6 / 54.8 / 32.8). cam03 is the slow one (the closest geometry, 18 mm). Cycles 1080p hero 277 s at the 270 s cap; cam04 64 spp 251 s at the 180 s cap.

## Deliverables present (pass/fail)

- **Cycles final config — pass via the preset, FAIL as saved.** `apply_final_cycles` gives GPU / 768 spp adaptive / OIDN / High Contrast at script time, but the *saved* master carries `cycles.device = CPU`, `samples = 4096`, `adaptive_min = 0`, `time_limit = 0`, look `AgX - Base Contrast`, exposure -2.389. A manual F12 or a lead who opens the file and renders will get CPU, 4096 spp and the wrong look (QA-03-17).
- **Eevee viewport config — pass.** `BLENDER_EEVEE`, taa 16 / 32, raytracing on, shadow rays 2, AgX, two baked irradiance volumes (`LIGHTPROBE_rotunda`, `LIGHTPROBE_colonnade`), active camera `CAM_qa_01_lagoon_hero`.
- **`CAM_flythrough_path` — pass** (QA-02-11 closed): `CAM_flythrough`, `CAM_flythrough_path` (curve), `CAM_flythrough_target` present; frame range 1-250 at 24 fps.
- Phase-5 items (3840x2160 Cycles hero, low-res Eevee test animation) not yet due — and not renderable under the current watchdog (QA-03-1).

## Status of every round-02 defect

| id | owner | status | evidence |
|---|---|---|---|
| QA-02-1 dome absent from cam05 | architecture (+ lead) | **closed by camera; geometry unverified** | at the new station rise >= 19.5 % of the attic extent vs ref 063's 7.0 % (and the apex is clipped, QA-03-5); cam01 apex still within 1.0 % / 0.6 % / 0.5 % of the three photos. No station-matched proof that the parapet no longer occludes the cap from ~55 m. |
| QA-02-2 blotch / olive / hue-spread stone | materials | **closed** | 1:1 crop x 760-1230 y 250-460: no hard patch > 20 px, shaded stone hue 36.9-37.1, capitals same hue. Residual: flat and unfluted (QA-03-4). |
| QA-02-3 no edge wear / no algae line | materials (+ architecture) | **open** (partially: ledge streaks claimed, not visible) | in the hero crops there is no readable streak under the cornice, no dust in capital recesses, and the waterline band is hidden behind the shrub row, so the algae line cannot be verified from any QA camera. |
| QA-02-4 exposure 0.9 EV under | lighting | **closed** | attic 178.0 vs 189.9 (0.94), sky 0.93, shade 1.12 at the AgX response. |
| QA-02-5 cam03 inside the row | lead | **closed** | two shafts frame the view, bases and ground in frame, rotunda between columns 026/028. New defects on what it reveals (QA-03-9). |
| QA-02-6 lagoon tonal range | environment + materials | **closed** | flank 1.13 of ref (was 0.26); near-water sat 0.382 <= 0.45 by the old test, but see the settled crop (target 0.27, QA-03-7). |
| QA-02-7 wings buried in trees | environment | **partially closed** | south wing 0.77-0.80 of ref (pass); north wing 0.63-0.79 (fail at 25 %). |
| QA-02-8 haze too dense / olive | lighting | **partially closed** | hue 39-44 (warm) and sat 0.26-0.30 at cam06 pass; contrast rotunda / far shore 1.04:1 fails the 1.5:1 test (QA-03-11). |
| QA-02-9 relief reads as decal | ornament | **partially closed** | cam05 attic panels now three depth registers with shadow (score 2 -> 3); cam04 coffers still flat outlines with no shadow (QA-03-8). |
| QA-02-10 corner figures / scrolls | ornament | **partially closed** | figures show head/torso/cascade break-up at cam05; the paired scrolls read as finial blobs at 720 px, not as volute pairs. |
| QA-02-11 flythrough missing | lead | **closed** | `CAM_flythrough`, `CAM_flythrough_path` (the only curve object) and `CAM_flythrough_target` are in master.blend (`scripts/qa_inspect.py`); path evaluability not exercised this round (Phase 5). |
| QA-02-12 vault soffits light-starved | lighting | **over-closed** | soffit / sky 0.80 in Eevee vs ref 0.405 (target was >= 0.45) — now 2x too bright (QA-03-3). |
| QA-02-13 vegetation collides with the rotunda | environment | **open** | cam05: two conifers still stand in front of the SE face (x 0.62-0.78 of frame); shrub row still hides the podium. |
| QA-02-14 sunlit stone cool | materials + lighting | **open** | attic hue 33.6 vs 40.0, sat 0.429 vs 0.591, R-B 92 vs 138 at 1920x1080 (QA-03-2). |
| QA-02-15 cam06 flat ground / box houses | environment | **open** | horizon crop (0 0 1280 220): ~5 box houses on an olive plane; no paths readable. |
| QA-02-16 render budget stale | lead | **open** | Cycles hero 277 s only because capped; uncapped 128 spp was 446 s; no 4K timing logged; and the watchdog now forbids any GPU render over 5 min (QA-03-1). |
| QA-02-17 cam02 station | lead | **open — recommendation below** | canonical photo is ref 062 byte-for-byte (md5 a53cd09d…); the render's rotunda is 41 % of frame width vs the photo's 44 % (scale fine), but the station is across the water and the photo's is on land. |
| QA-02-18 shrub pom-poms | environment | **partially closed** | warm dry fraction now present (rust shrubs, hue spread > 25 deg); sizes still within ~1.5:1 and the row is still evenly spaced (crop 700 640 1200 720). |

## Defect list — round 03

Severity: **blocker** = must be fixed before the next gate; **major** = visible at hero distance; **minor** = specific view.

| id | cam | owner | sev | defect (measurable) | where | acceptance test |
|---|---|---|---|---|---|---|
| QA-03-1 | — | lead | **blocker** | `scripts/blender_watchdog.sh` kills every GPU Cycles render longer than 5 min: a Metal render waits in `MetalDeviceQueue::synchronize()` and the process CPU time does not advance (8.9 s CPU after 105 s wall). It killed QA's 128-spp hero at 330 s (`renders/logs/watchdog.log` 20:23:49). The Phase-5 4K hero (1.5-2.5 h) cannot be rendered while it runs; this round's Cycles frames had to be capped at 270 s of sampling. | `scripts/blender_watchdog.sh` (criterion `cputime`) | Watchdog treats a process as alive if its CPU time **or** its GPU time / render log grows, or exempts `--python` renders under a generous wall limit; verified by a 10-min Cycles render surviving under `--loop`. |
| QA-03-2 | 01 | lighting + materials | **blocker** | Sunlit stone chroma at delivery resolution: attic front panel hue **33.6 vs 40.0**, sat **0.429 vs 0.591**, R-B **92 vs 138**; string course R-B 89 vs 130; dome cap hue 29.8 vs 42.3. Luminance is right (0.94), so this is colour, not exposure. Columns are the inverse: lum 134 vs 87 (**1.54x**), hue 28.5 vs 23.6 — fill / glossy sky light on shafts that should sit in the entablature's shadow. | `LIGHT_sun` colour / temperature, `SKY_GLOSSY_BOOST`, `MAT_concrete_*` / `MAT_column_*` chroma | On a 1920x1080 Cycles hero, box (900 222 1020 256): hue >= 37, sat >= 0.53, R-B >= 118 with lum within +-10 % of 190; column mask (hue<32, sat>0.30, x 680-1240 y 280-470) lum within 25 % of 87. |
| QA-03-3 | 04 | lighting | **blocker** | Interior fills ~2x: Eevee soffit/sky **0.80** and coffer/sky **1.04** vs ref 083's 0.405 / 0.437; Cycles soffit/sky **0.70**, coffer/sky **1.00** — the two engines agree within 12 %, so this is the rig, not Eevee. The ceiling is floodlit with no shadow structure. | `light_build.FILL["energy"]` 7600, `VAULT_FILL["energy"]` 2400 | soffit / own-sky 0.35-0.50 and coffer / own-sky 0.35-0.55 at the boxes in (e), in Eevee **and** Cycles. |
| QA-03-4 | 01, 05 | materials + architecture | **blocker** | "Clean CAD" at 1:1 (hero crop x 760-1230 y 250-460 beside ref 169 x 805-1164 y 289-450): column shafts show **no flutes** where the photo shows them clearly at the same scale; the entablature and attic are a uniform ochre with no streaks, no recess dirt and no shadow depth under the cornice; capitals are low-contrast blobs. | `ARCH_rotunda_column_*` LOD0/LOD1 flutes, `MAT_column_*` (flute normal / grain), `MAT_concrete_*` streak and recess masks, capital LOD | Same crop: a horizontal luminance profile across a front shaft shows >= 8 modulation cycles with >= 10 % contrast; luminance std-dev over the entablature box >= 60 % of the photo's over its mapped box; visible dark streak under the cornice in the crop pair. |
| QA-03-5 | 05 | lead | major | `CAM_qa_05` clips the dome: rows 0-3 over x 480-760 are dome (203,175,142); the apex is above the frame so the cam05 dome test cannot be measured. The station (115 m, 40 mm) also shows 2.8x more drum than ref 063's closer station. | `CAM_qa_05_south_lawn` in `scripts/qa_cameras.py` | apex >= 3 % of frame height below the top edge; the lead either documents ref 063's station (attic 48 % of frame width, apex 4.5 % from top) and matches it, or accepts the cam05 test as station-dependent. |
| QA-03-6 | 02 | lead | major | QA-02-17: the camera is across the water, the photo on land; scale already matches (41 vs 44 % of frame width). See the recommendation. | `CAM_qa_02` (-45, 52, 1.3) 20 mm | letterboxed blend: apex within 3 % of the top edge and the podium base row within 3 % of the photo's (85 % of height); no water in the foreground. |
| QA-03-7 | 01 | materials | major | Near water, sky-reflecting crop (1150 1000 1450 1050): sat **0.382 hue 206** vs ref 169's 0.269 hue 192 at (1103 863 1332 901). Also the near-field reflection is too coherent: streaks tens of px long where the photo breaks up at ~10 px (crop 760 1000 1160 1060 pair). | `MAT_water_lagoon` murk tint, near-field ripple scale | same crop: sat 0.22-0.32, hue 185-200; ripple break-up at <= 15 px in the near-water crop. |
| QA-03-8 | 04 | ornament + architecture | major | Vault coffers and rosettes still read as flat inset outlines at cam04 (both Eevee and Cycles): no coffer casts a shadow. Ref 083 shows deep boxes with hard shadow and a 0.93 soffit/coffer ratio. QA-02-9 half. | `ARCH_rotunda_vault_coffers_*`, `ORN_rosette_*` | coffer field luminance std-dev >= 60 % of ref 083's over the central 0.40-0.60 box after QA-03-3 lands. |
| QA-03-9 | 03 | materials + architecture + environment | major | The nearest shaft in the build (crop 0 150 420 720): lum 23.1 vs ref 128's 69.7 (3x dark), no flutes, a smooth bell-shaped base with no torus/scotia, on a flat olive plane with a soft blob shadow; the foreground foliage is black cards. | colonnade column LOD1 flutes/base, `MAT_column_*`, `ENV_terrain` path material, leaf materials in shade | same crop: flutes resolved (>= 8 cycles across the shaft), base mouldings read, ground shows gravel/grass texture with luminance std-dev >= 12; shaft lum within 30 % of ref 128's. |
| QA-03-10 | 01, 02 | environment | major | North wing still 0.63-0.79 of ref 169 (band 60 480 560 600); trees remain in front of it. | `ENV_tree_instances_*` north of the rotunda | band within 25 % of ref by both ref panels (raw-mapped box 269 465 651 557). |
| QA-03-11 | 06 | environment + lighting | major | cam06 backdrop and distance: everything past 150 m is sat 0.26-0.30 / lum 131-142; dome vs far shore **1.04:1**; ~5 box houses on an olive plane in the horizon crop (0 0 1280 220), no paths. Reads as a game-level skybox. | `ENV_backdrop_*`, `ENV_terrain_ground`, mist | rotunda / far-shore contrast >= 1.5:1; >= 30 building volumes with roof pitch and >= 3 colours in the horizon crop; paths readable. |
| QA-03-12 | 01 | lighting | minor | Sky has no haze band toward the horizon: sky_left 144.0 vs ref 193.8 (0.74) while sky top is 0.93. The sky reads flat deep blue to the tree line. | sky `air/aerosol density`, `SKY_CAMERA_BOOST` | sky_left / sky_top ratio within 10 % of the photo's (1.17). |
| QA-03-13 | 05 | environment | minor | QA-02-13 still open: two conifers stand in front of the SE face at cam05 (x 0.62-0.78, y 0.25-0.75 of frame); shrub row hides the podium and Greek-key band. | `ENV_tree_instances_*`, `ENV_shrubs_pen` | no crown inside the rotunda's silhouette from cam05; podium band visible over >= 60 % of the rotunda width. |
| QA-03-14 | 01, 05 | environment | minor | Shore shrubs: colours now vary but the row is evenly spaced same-size mounds (crop 700 640 1200 720; size spread ~1.5:1). | `ENV_shrubs_shore` | size spread >= 2:1, gaps irregular (spacing std-dev >= 40 % of mean). |
| QA-03-15 | 01 | ornament | minor | Capitals at hero distance are low-contrast blobs (1:1 crop): the acanthus rows do not resolve into leaf tiers. | `ORN_capital_corinthian_LOD0/1` shading, recess dirt | in the crop pair the capital shows >= 2 readable leaf tiers with dark recesses. |
| QA-03-16 | — | lead | minor | Render budget still unlogged (QA-02-16): 4K hero time unknown; Cycles at 1080p 128 spp is ~446 s uncapped. | `docs/lighting_notes.md`, `light_presets.FINAL_SAMPLES` | a measured 4K timing logged before Phase 5. |
| QA-03-17 | — | lead + lighting | minor | The saved master.blend does not carry the final preset: `cycles.device` CPU, 4096 spp, `adaptive_min` 0, look `AgX - Base Contrast` (lighting shipped High Contrast), so a manual render from the opened file is not the deliverable configuration. | `scripts/build_master.py` / `light_presets.apply_final_cycles` at build time | `qa_inspect.py` on the built master reports device GPU (Metal), samples 768, look `AgX - High Contrast`. |

## Recommendation on QA-02-17 (cam02)

**Re-point the camera; keep the photo.** Numbers: the canonical `cam_02_ne_shore_threequarter.jpg` *is* ref 062
(identical md5), so "re-pick ref 062" is a no-op; the render already matches the photo's scale (rotunda 520/1280 =
41 % of frame width vs 840/1920 = 44 %), so only the station is wrong. The photo has no water in the foreground, a
lamppost and people at the podium, the south wing behind-left: a ground station on the land north-east of the rotunda,
roughly 43 m from the centre at azimuth ~20 deg (world (-40, 15, 1.4) — outside the OSM lagoon polygon; the reference
sheet's own (-32, 38) and the current (-45, 52) both test inside it), lens ~18 mm, target (0, 0, 20) so the apex sits
1-3 % from the top as in the photo (apex at 0.9 %). Cost: one line in `scripts/qa_cameras.py` and one 38-s Eevee
render; re-picking a photo would cost a new canonical file, a new sheet entry and a new baseline for every future round.

## Notes for the lead

1. **The watchdog and the GPU are incompatible as written (QA-03-1).** Any agent's Cycles frame over ~5 min will die,
   including the deliverable 4K hero. Fix the criterion before polish round 2; until then every Cycles run must set a
   `time_limit` under 270 s, which is what this round's numbers were measured at.
2. **Exposure is done; stop moving it.** The remaining stone deficit is chroma. Sun colour, the glossy-sky share on the
   shafts (columns 1.54x too bright) and albedo chroma are the levers; the measured AgX response says exposure is not.
3. **QA-02-1 was closed by moving the camera.** That is legitimate for the checklist but it means no one has shown that
   the parapet stops occluding the cap from ref 063's own station. If architecture wants the credit, one Eevee render
   from a station matched to ref 063 (attic 48 % of frame width, apex 4.5 % from top, 16:9) settles it in a minute.
4. **Halve the interior fills, then let ornament put depth in the coffers** — in that order, because the coffer test
   (std-dev) is meaningless while the ceiling is floodlit.
5. **The next round is again a materials round, plus flutes.** The three photoreal rejects (hero 1:1, cam03 shaft,
   cam04 ceiling) are all "smooth surface, no relief, no dirt". Flutes are geometry at hero distance and normal maps
   are not enough at 3 m.
