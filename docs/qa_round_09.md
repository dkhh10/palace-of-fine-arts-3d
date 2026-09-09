# QA round 09 — the LAST polish round (2026-09-10). Gate NOT passed; hero 3.67 -> 3.67 (+0.00).

Scored master: the file on disk after `lead_build_r9.log`, **9679 objects**, LOD1 **11.38 M tris**, 72 materials,
0 placeholders, **160.9 MB**, opens in **0.75 s**, **frame range 1-1224** at 24 fps (51.0 s). Merged this round and
nothing else: **cam02's lens 40 -> 27 mm** (QA-08-1) and **LIGHT r16** (sun-side diffuse tint b 40 -> 70, a cam03
knob, the flythrough re-planned to 1224 frames with ORN in the clearance check). **No materials, ornament or
environment round.** No other Blender ran during any QA render; every render was one blocking `scripts/blender_run.sh`
call and every one exited on its own.

## What was rendered and compared

| file | what |
|---|---|
| `renders/previews/qa/round09_0K_*.png` | Eevee 1280x720, 32 TAA, LOD1. Times **24.6 / 21.5 / 29.4 / 19.4 / 21.7 / 17.5 s**; whole pass **137.5 s** (r08 134.9, r07 146.1). Log `qa_round09_eevee.log`. |
| `round09_01_lagoon_hero_cycles.png` | Cycles 1920x1080, 128 spp adaptive, OIDN, GPU: **380.6 s** (r08 380.0). |
| `round09_04_rotunda_ceiling_cycles.png` | Cycles 1280x720, 64 spp: **228.1 s** (r08 229). |
| **`round09_02_lagoon_ne_threequarter_cycles.png`** | **new this round** (brief item 1): Cycles 1280x720 64 spp, **105.8 s** — the delivery engine's own verdict on the re-framed cam02. |
| `round09_06_aerial_nocomp.png` | the un-composited twin for the cam06 ratio gate (22 s), `scripts/qa_r09_c06.py`. |
| `renders/qa_comparisons/round09_cam0K.png`, `round09_sheet.png` | render / canonical photo / 50 % blend per camera |
| `round09_cam01_aligned_vs_ref169.png` | the round-03..09 yardstick. **Scale 1.3108, dx -291.8, dy -126.6** — identical to round 08 to four decimals; apex delta **0.44 %H**. |
| `round09_stack_offset.png` | the hero-facing stack course by course at x8 vertical zoom |
| **`renders/qa_comparisons/round09_gate.png`** | **the gate composite**: Cycles hero beside ref 169, six Eevee views, r08 -> r09 deltas per row, trend r02 -> r09 |

Commands: `scripts/blender_run.sh 900 -- --background --python scripts/qa_render_round.py -- --round 09 --eevee`;
`... 1500 -- ... --round 09 --final --samples 128 --res 1920 1080 --cams 01`; `... 1500 -- ... --samples 64 --res 1280 720 --cams 04`;
`... 900 -- ... --samples 64 --res 1280 720 --cams 02`; `... 600 -- ... scripts/qa_r09_c06.py`; `... 600 -- ... scripts/qa_inspect.py`.
Analysis (no Blender): `qa_silhouette.py align/measure`, `qa_compare.py`, `qa_stack_offset.py`, `qa_r07_measure.py`,
`qa_gate_sheet.py --round 09`, and the owners' read-only tools (`mat_r6_measure.py`, `mat_r9_measure.py coffer`,
`light_measure.py --summary ceiling`, `env_r7_measure.c06_ratio`). Nothing was written to master.blend; environment's
`r7_numbers.json` was reverted after use (it was in fact never written — the ratio was called in-process).

## Brief item 1 — the re-base

**cam01 needs no re-base at all.** The alignment transform came back **bit-identical** to round 08
(scale 1.3108, dx -291.8, dy -126.6, apex delta 0.0044 of frame height), and every reference box re-measured on this
round's panel reproduces round 08's number exactly (sunlit attic 189.8 / 40.6 / 0.582 / +134.2; shaded attic
120.5 / 30.6 / 0.454; reflection 165.5 / 33.7 / 0.358; ripples 104.7 / 182.8; flank 154.0 / 200.5; shore 115.2;
south wing 111.7; north wing 145.6; dome cap 224.3 / 44.1 / 0.272). **The round-07/08 boxes are used unshifted.**

The stronger statement: the hero's *geometry* did not move either. The twelve strongest luminance edges in the
hero-facing stack band (x 880-1040, rows 150-350) are at the same rows in both rounds — 177, 179, 193, 262, 263, 276,
277, 289, 290, 296, 297, 324 — and the whole-frame difference between the round-08 and round-09 Cycles heroes is
**mean |d| 1.24 lum**, split **R 0.53 / G 0.47 / B 2.73**. The only thing that happened to cam01 this round is that the
sun-side tint took blue out of the lit stone. Every proportion, silhouette and stack result of round 08 therefore
carries forward unchanged and is not re-litigated here (QA-06-1 stays closed; QA-08-11 and QA-08-12 stay open).

**cam02 at 27 mm — the new frame, on lighting r16's boxes.**

| quantity | round 08 (40 mm) | **round 09 (27 mm)** | ref 062 | verdict |
|---|---|---|---|---|
| sky in the top-centre band (x 400-900, rows 0-60) | **0.2 %** | **91.8 %** | **91 %** in its own rows 0-27 | **QA-08-1 CLOSED** |
| dome apex row, as a fraction of frame height | apex not in frame (`measure` -> 0) | **34 / 720 = 0.047** | acceptance **0.05 +- 0.02** | **pass** |
| podium base row | — | not measurable: the near planting occludes the podium base at this station | acceptance 0.85 +- 0.03 | untested half |

The ref-062 *residuals* still cannot be restated as a row-by-row chi-square: ref 062 is a **midday** photograph of a
**sunlit** NNE face, while the shipped sun at morning golden hour leaves that face entirely in shade. The two frames
now contain the same building at the same framing, but their tonality can never agree. What is testable on cam02 is
what lighting r16's windows already encode — the *hue family* of the shade (25-60 at sat <= 0.35) — and that is
measured below. This is a permanent property of the camera/reference pair, not a defect, and it caps cam02's
Lighting-mood and Material-realism rows for the life of the project.

## Brief item 2 — status of every round-08 defect, with the number that proves it

| defect | owner | status | the number |
|---|---|---|---|
| **QA-08-1** cam02 lens clips the dome | lead | **CLOSED** | top-band sky **0.2 % -> 91.8 %** against ref 062's 91 %; apex at **0.047** of frame height (test 0.05 +- 0.02). |
| **QA-08-2** cam02 face indigo | lighting | **half closed in EEVEE, OPEN in CYCLES** | Eevee: shade_pier **53.4 / hue 28.1 / sat 0.523**, shade_frieze **68.9 / 28.7 / 0.266** (hue window 25-60 **pass**, frieze sat pass); shade_pier_r **78.9 / 301.7 / 0.132** and shade_arch **37.4 / 260.8 / 0.407** still violet. **Cycles — the delivery engine — is violet on all four**: shade_pier **58.0 / 268.4 / 0.320**, shade_pier_r **72.9 / 234.6 / 0.401**, shade_arch **59.0 / 249.5 / 0.388**, shade_frieze **78.0 / 351.2 / 0.127**, every one with a **negative R-B** (-13 to -45). The ratio half of the test does pass: shade_pier_r / sunlit_pier **0.477 Eevee / 0.431 Cycles** (test <= 0.8) — round 08's 1.046 was a ratio against a piece of sky. |
| **QA-08-3** sunlit stone chroma | materials + lead | **CLOSED as the lead directed — and the round-09 number argues for closing it, not against** | attic sat **0.462 -> 0.487**, R-B **104.9 -> 110.6** (window 0.53-0.62 / >= 120): the tint bought 26 % of the remaining saturation gap and 19 % of the remaining R-B gap. But it moved the *whole building* (700 160 1240 480) from **sat 0.528** to **0.571** against ref 169's **0.521** — from 1.01x the photograph to **1.10x** — and its hue from 36.0 to 37.6 against the photo's 34.4. **The window is box-specific; the frame as a whole passed it in round 08 and now overshoots.** No lever was found that the owners missed. Logged as the new QA-09-1 below, minor, do-not-chase. |
| **QA-08-4** archivolt + bed-mould blank | ornament + architecture | **open, unchanged** (no ORN round) | 8 `SOCKET_archivolt_run_##`, 0 instances. |
| **QA-08-5** hero mirror level | materials | **open, unchanged** | reflection **115.8** (r08 116.3; window 124-208) at R-B +50.2 / hue 40.6 / sat 0.383; mirror / own sunlit attic **0.614** vs the photograph's **0.872**. |
| **QA-08-6** cam05 lagoon band | materials + lighting | **open, unchanged** | **133.2** (r08 133.6; window 70-117) at sat 0.254. The frame moved by 0.20 lum mean between rounds. |
| **QA-08-7** cam03 walk green | lighting + environment | **open, unchanged** | walk hue **92.1** at sat 0.138 — the same two digits as round 08. cam03's whole frame moved **0.18 lum mean**: r16's cam03 knob produced no measurable change. |
| **QA-08-8** coffer saucer | materials | **open, unchanged** | Cycles field sat **0.341** / rim **0.634** (r08 0.339 / 0.626; window 0.38-0.50, ref 0.427 / 0.438). Eevee field 0.414 passes, rim 0.653 fails. |
| **QA-08-9** Eevee-Cycles soffit W gap | lighting | **open, unchanged** | **+0.224** (test <= 0.15; r08 +0.222, r07 +0.202); Cycles soffit W **0.237** against ref 083's 0.381. |
| **QA-08-10** shoreline a dark hedge | environment | **open, unchanged** | shore band **88.4** vs the photograph's 115.2 = **0.767**; no trunks, no built structure, no figures. |
| **QA-08-11** entablature sub-courses | architecture | **open, unchanged** | cornice 1.33 of the photo's rows, frieze 0.87 (geometry bit-identical, above). |
| **QA-08-12** entablature row std | architecture / materials | **open, unchanged** | **37.3** on the fixed box (test >= 40), **40.3** on the course-tracking control; ref 53.0. |
| **QA-08-13** frame range | lead | **CLOSED** | `qa_inspect` reads **frame_range [1, 1224]** at 24 fps = 51.0 s. |
| QA-07-5 cam03 black frame | lighting | **stays closed** | below lum 10 **12.8 %** (test <= 20 %), below 20 36.2 %; outer row **16.2 / 98.3 = 0.165** (test >= 0.15) at hue 58.9. |
| QA-07-6 cam06 far field | environment | **stays closed** | ratio **0.636** (test >= 0.60), far-shore lines **3** composited / 6 un-composited (test >= 3). |
| QA-03-16 4K 768 spp timing | lead | **open, not run** | excluded by the brief; the only untested delivery item. |

## Score table (0-5; target >= 4 every row, hero average >= 4.5). Round 08 -> round 09.

| row | 01 hero | 02 NE 3/4 | 03 colonnade | 04 ceiling | 05 S lawn | 06 aerial |
|---|---|---|---|---|---|---|
| Silhouette match | 4 -> 4 | 2.5 -> **3.5** | 2.5 -> 2.5 | 3.5 -> 3.5 | 3.5 -> 3.5 | 4 -> 4 |
| Proportion | 4 -> 4 | 3.5 -> 3.5 | 3 -> 3 | 3.5 -> 3.5 | 3.5 -> 3.5 | 3.5 -> 3.5 |
| Ornament fidelity | 4 -> 4 | 4 -> 4 | 3 -> 3 | 3 -> 3 | 3.5 -> 3.5 | 2.5 -> 2.5 |
| Material realism | 3.5 -> 3.5 | 2 -> 2 | 2.5 -> 2.5 | 3 -> 3 | 3.5 -> 3.5 | 2.5 -> 2.5 |
| Edge wear | 3.5 -> 3.5 | 2.5 -> 2.5 | 1.5 -> 1.5 | 1 -> 1 | 2 -> 2 | 0.5 -> 0.5 |
| Lighting mood | 4.5 -> 4.5 | 2 -> **2.5** | 3.5 -> 3.5 | 3 -> 3 | 3.5 -> 3.5 | 3 -> 3 |
| Water reflection | 3 -> 3 | n/a | n/a | n/a | 2.5 -> 2.5 | 2.5 -> 2.5 |
| Repetition visibility | 3 -> 3 | 2.5 -> 2.5 | 2 -> 2 | 2.5 -> 2.5 | 2.5 -> 2.5 | 2.5 -> 2.5 |
| Scale cues | 3.5 -> 3.5 | 2.5 -> **3** | 2.5 -> 2.5 | 3 -> 3 | 3 -> 3 | 3 -> 3 |
| **average (delta)** | **3.67 (+0.00)** | **2.94 (+0.25)** | **2.56 (+0.00)** | **2.81 (+0.00)** | **3.06 (+0.00)** | **2.67 (+0.00)** |

### Why five cameras are flat to two decimals

Not an omission — the round merged one lighting socket and one lens. The frame-to-frame difference between the round-08
and round-09 renders, mean |d| in 8-bit luminance over the whole frame:

| camera | mean \|d\| r08 -> r09 | per channel R / G / B | reading |
|---|---|---|---|
| 01 hero (Eevee) | **1.03** | 0.75 / 0.48 / 1.86 | blue removed from the lit stone |
| 01 hero (Cycles) | **1.24** | 0.53 / 0.47 / 2.73 | the same, stronger; **the tint is a Cycles-side change** — the Eevee hero's sunlit attic did not move at all (0.518 / R-B 114.9 -> 114.8) |
| 02 NE 3/4 | **52.14** | 48.5 / 50.6 / 57.4 | a different frame (27 mm) |
| 03 colonnade | **0.18** | 0.21 / 0.21 / 0.12 | below the scoring resolution |
| 04 ceiling | **0.09** | 0.10 / 0.11 / 0.07 | below the scoring resolution |
| 05 S lawn | **0.20** | 0.16 / 0.16 / 0.29 | below the scoring resolution |
| 06 aerial | **2.34** | 1.30 / 1.27 / 4.44 | the warm-band composite got warmer; all three hue boxes stay in window |

A round that moves four of six frames by less than a quarter of a luminance level cannot move their scores, and
inventing a delta for them would corrupt the definition-of-done clock.

## The definition of done — stated explicitly (brief item 3)

- **Hero: 3.67 -> 3.67, delta +0.00.** The gate passes at **>= 4.0**; **3.67 does not pass**, and the hero is **0.33** short.
- The alternative exit is *two consecutive rounds after the concrete photo-projection pass improving the hero by less
  than 0.1*. Round 08 was the first post-projection round and moved **+0.22** (not < 0.1), so the clock was armed at
  0 of 2. **Round 09 is +0.00, which is < 0.1: the clock now reads 1 of 2.**
- Under the *strict* rule one more sub-0.1 round would be needed to stop the loop. Under the **user's round-08
  instruction as carried in this round's brief** — "hero under 4.0 after round 08 -> ONE more round, then Phase 5
  regardless" — round 09 is that round and **the project moves to Phase 5 now**. QA agrees with the second reading on
  its own evidence: the +0.33 the hero owes is spread over three rows (Material realism, Edge wear, Water reflection,
  all at 3.5 or 3) whose causes are named below, and none of them is a lighting or colour-management item. Continuing
  the loop with lighting alone would return +0.00 again.

### Trend across rounds 02 -> 09 (averages)

| cam | r02 | r03 | r04 | r05 | r06 | r07 | r08 | **r09** | since r02 |
|---|---|---|---|---|---|---|---|---|---|
| 01 hero | 2.94 | 3.28 | 3.28 | 3.28 | 3.22 | 3.44 | 3.67 | **3.67** | +0.72 |
| 02 NE 3/4 | 2.11 | 2.33 | 2.67 | 2.78 | 2.72 | 3.06 | 2.69 | **2.94** | +0.83 |
| 03 colonnade | 1.94 | 2.12 | 2.00 | 1.75 | 2.12 | 2.25 | 2.56 | **2.56** | +0.62 |
| 04 ceiling | 2.31 | 2.12 | 2.44 | 2.56 | 2.75 | 2.88 | 2.81 | **2.81** | +0.50 |
| 05 S lawn | 2.11 | 2.67 | 2.72 | 2.78 | 2.78 | 3.00 | 3.06 | **3.06** | +0.94 |
| 06 aerial | 2.17 | 2.17 | 2.39 | 2.50 | 2.28 | 2.50 | 2.67 | **2.67** | +0.50 |

## Measurements

### (a) Chroma at delivery resolution (Cycles hero 1920x1080; ref 169 on this round's aligned panel)

| region | box | round 08 | **round 09** | ref 169 | verdict |
|---|---|---|---|---|---|
| sunlit attic panel | 900 222 1020 256 | 189.4 / 36.1 / 0.462 / +104.9 | **188.7 / 37.0 / 0.487 / +110.6** | 189.8 / 40.6 / 0.582 / +134.2 | lum **0.99 pass**; sat 0.043 under the 0.53 floor (was 0.068), R-B 9.4 short of 120 (was 15.1) |
| attic string course | 880 214 1040 222 | 180.4 / 35.8 / 0.460 | **179.7 / 36.8 / 0.488** | 181.0 / 39.0 / 0.583 | lum 0.99 |
| entablature | 900 262 1020 296 | 132.9 / 38.1 / 0.700 | **132.2 / 39.0 / 0.735** | 145.5 / 33.7 / 0.588 | lum 0.91; **sat 1.25x the photograph and rising** |
| dome cap | 920 95 1000 120 | 190.6 / 36.7 / 0.361 | **189.5 / 38.0 / 0.397** | 224.3 / 44.1 / 0.272 | lum 0.845 (+-5 % band, see round 08 item 1) |
| shaded attic | 1110 225 1150 260 | 127.8 / 34.3 / 0.432 | **127.6 / 34.8 / 0.443** | 120.5 / 30.6 / 0.454 | hue + sat **pass**; lum **1.1 over** the 126.5 ceiling; hue 0.7 deg from the 35.5 edge |
| columns population (680 280 1240 470, sat > 0.30) | 87 % of box | 131.6 / 36.5 / 0.632 / +106.9 | **130.7 / 38.3 / 0.694 / +117.7** | 126.3 / 32.9 / 0.595 / +98.2 | **sat 1.17x the photo (was 1.06x), hue 5.4 deg off (was 3.6)** |
| **whole building block** | 700 160 1240 480 | 134.6 / 36.0 / **0.528** | 133.8 / 37.6 / **0.571** | 136.5 / 34.4 / **0.521** | **1.01x -> 1.10x the photograph's saturation** |
| water reflection column | 900 760 1020 840 | 116.3 / 39.0 / 0.348 / +45.5 | **115.8 / 40.6 / 0.383 / +50.2** | 165.5 / 33.7 / 0.358 / +68.7 | R-B + hue + sat pass; **lum 0.70, 8 under the 124 floor** |
| ripples | 1100 960 1500 1060 | 121.8 / 208.7 / -22.5 | **121.8 / 208.4 / -22.4** | 104.7 / 182.8 / -17.0 | 1.16x, 26 deg blue |
| near water, sky-reflecting | 1150 1000 1450 1050 | 125.3 / 207.9 / 0.200 | **125.3 / 207.8 / 0.200** | 105.3 / 190.3 / 0.252 | lum pass (window 79-132); **hue 7.8 deg outside 185-200** |
| lagoon flank | 100 900 400 960 | 162.8 / 209.6 / 0.230 | **162.7 / 209.6 / 0.229** | 154.0 / 200.5 / 0.266 | both halves pass (1.06x, hue <= 210) |
| sky top / sky low-left | lighting's boxes | 154.8 / 167.9 -> 0.922 | **154.8 / 167.9 -> 0.922** | panel 186.7 / 202.8 -> 0.921 | closed, unchanged; note the render's sky is **0.83x the photograph's level** and 0.10-0.13 more saturated |
| shore band | 700 600 1200 740 | 89.2 / 42.3 / 0.638 | **88.4 / 43.9 / 0.712** | 115.2 / 40.9 / 0.632 | **0.767** (test +-25 %, passing by 0.017) |
| south wing | 60 480 560 600 | 100.5 / 37.8 / 0.287 | **100.2 / 39.2 / 0.311** | 111.7 / 34.6 / 0.162 | 0.90 — fails the >= 103 test again |
| north wing | 1360 480 1860 600 | 139.0 / 41.3 / 0.471 | **138.4 / 42.3 / 0.504** | 145.6 / 42.1 / 0.496 | 0.951 pass |

### (b) Texture / weathering at 1:1 (all unchanged — no materials round)

| box | round 08 | **round 09** | ref 169 | ratio / reading |
|---|---|---|---|---|
| attic std 900 222 1020 256 | 28.8 | **28.9** | 42.8 | **0.675 pass** (test >= 0.60) |
| entablature std 900 262 1020 296 | 50.7 | **50.4** | 64.5 | 0.78 pass |
| attic anisotropy, wide | 5.02 (control 3.76) | **5.01** (control **3.75**) | 3.39 | pass |
| attic anisotropy, narrow 900 224 1020 248 | 8.23 | **8.23** | 4.58 | pass |
| entablature row-profile std | 37.6 (control 40.5) | **37.3** (control **40.3**) | 53.0 | at the margin: fixed box fails >= 40, control passes by 0.3 |
| under-cornice run-off (`mat_r6_measure cornice`) | 20.8 % | **20.0 %** | 19.2 % | above the photograph, pass |
| waterline band (`mat_r6_measure waterline`) | 51.1 % / 223 cols | **48.2 % / 220 cols**, mean drop 24.5 | 38.2 % | pass |
| capital alternation (band 680-1240 x 320-350) | 25 vs 22 at 0.97 of the photo's contrast | **20 maxima vs the photo's 18**, contrast **1.278 vs 1.209 = 1.06x** | — | pass |

### (c) Interior fills, cam04 vs ref 083 (round-03 boxes) — unchanged

| ratio | ref 083 | r08 Eevee | r08 Cycles | **r09 Eevee** | **r09 Cycles 64 spp** |
|---|---|---|---|---|---|
| soffit / own sky (W / E) | 0.381 / 0.429 | 0.461 / 0.423 | 0.237 / 0.471 | **0.461 / 0.425** | **0.237 / 0.471** |
| coffer field / own sky | 0.437 | 0.349 | 0.462 | **0.349** | **0.461 pass** |
| dark quarter / light quarter | 0.265 | 0.223 | 0.231 | **0.223** | **0.231 pass** (test >= 0.20) |
| coffer field sat / rim sat | 0.427 / 0.438 | — | 0.339 / 0.626 | 0.414 / **0.653** | **0.341 / 0.634** — both outside 0.38-0.50 |
| Eevee - Cycles gap (test <= 0.15) | | | | coffer -0.112 pass; soffit E -0.046 pass; **soffit W +0.224 fail** | |

### (d) cam03 — the shade test on lighting's boxes

| box | what it is | round 08 | **round 09** | / sunlit rotunda (98.3) |
|---|---|---|---|---|
| 480 150 560 600 | sky-visible shaft flank | 61.2 / 46.6 / 0.865 | **61.3 / 46.6 / 0.865** | **0.624** — inside 0.30-0.70 |
| 880 120 1200 600 | outer (lagoon-side) row | 16.3 / 58.9 / 0.947 | **16.2 / 58.9 / 0.947** | **0.165 pass** (>= 0.15) at hue 58.9 |
| 420 560 900 720 | the walk | 74.9 / 92.1 / 0.138 | **74.8 / 92.1 / 0.138** | 0.761; hue **green**, outside 25-60 |
| frame below lum 10 / 20 | | 12.6 % / 36.0 % | **12.8 % / 36.2 %** | test <= 20 % — **pass** |

### (e) cam02 (27 mm, r16 boxes), cam05, cam06

**cam02 Eevee**: shade_pier **53.4 / 28.1 / 0.523**, shade_pier_r **78.9 / 301.7 / 0.132**, shade_arch **37.4 / 260.8 / 0.407**,
shade_frieze **68.9 / 28.7 / 0.266**, sunlit_pier 165.5 / 45.6 / 0.385, sky 170.2 / 210.3.
**cam02 Cycles (delivery engine)**: shade_pier **58.0 / 268.4 / 0.320**, shade_pier_r **72.9 / 234.6 / 0.401**,
shade_arch **59.0 / 249.5 / 0.388**, shade_frieze **78.0 / 351.2 / 0.127**, sunlit_pier 169.2 / 43.1 / 0.345,
sky 170.2 / 210.2. **Four of four shaded boxes violet with a negative R-B.**
**cam05**: water band (448 619 960 713) **133.2 / 39.0 / 0.254** vs ref 063's 93.4 / 64.9 / 0.306 — sat passes,
lum 1.14x and outside 70-117; attic band 165.1 / 39.7 / 0.442, std 43.5 vs ref 63.5 = **0.685 pass**.
**cam06**: roofs 126.0 / **27.9** / 0.053; plaza 107.4 / **46.4** / 0.218; trees 123.2 / **41.0** / 0.251 — all three
inside the 22-52 window; horizon crop mean 116.6 std **33.7** against the un-composited twin's 78.4 / **53.1**.
**Gate 33.7 / 53.1 = 0.636 (test >= 0.60) pass**; far-shore lines **3** composited / 6 un-composited (test >= 3).

### (f) Wings on the hero (shadow = below half the band's own p90) — unchanged

| band | box | render p90 / shadow share | ref 169 aligned | reading |
|---|---|---|---|---|
| SOUTH (frame-left) | 60 480 560 600 | 203.8 / **59.6 %** | 219.5 / **54.8 %** | +4.8 pt darker (r08 +4.6) |
| NORTH (frame-right) | 1360 480 1860 600 | 219.3 / **38.1 %** | 228.4 / **39.3 %** | -1.2 pt (r08 -1.3) |

## Explicit "clean CAD / game asset" rejects this round

- **cam02's camera-facing face in Cycles** (`round09_cam02.png`, pane 1 and the Cycles twin): the fluted shafts, the
  arch vaults and the frieze all read deep indigo-violet at negative R-B against ref 062's warm pink-grey. On this
  frame it is not a detail — it is most of the picture, and it is the first frame where the delivery engine disagrees
  with the engine the fix was tuned on.
- **The hero's arch soffit / intrados** (unchanged since round 07): a smooth pale vault where the photograph carries a
  moulded archivolt over a coffered soffit. Still the largest blank surface in the hero's ornament zone.
- **The hero mirror**: a dim smeared reflection at 0.614 of its own sunlit stone where the photograph reads 0.872 with
  hard gold-and-blue vertical streaks.
- **The shoreline**: a uniform dark green hedge (88.4 lum) against ref 169's willows with visible trunks, a small shed
  with a green door, and people.
- **cam04's saucer**: grey fields (sat 0.341) between orange ribs (0.634) where the photograph is one warm cream
  surface at 0.427 / 0.438.

## What works (keep it)

- **The projection still registers with no drift**: attic std ratio **0.675**, anisotropy **5.01 / 8.23** against the
  photo's 3.39 / 4.58, alignment transform bit-identical to round 08.
- **The hero shade holds** through the tint: 127.6 / 34.8 / 0.443 against ref 120.5 / 30.6 / 0.454 — hue and
  saturation inside their windows, luminance 1.1 over.
- **The lagoon's open water holds**: flank 162.7 / hue 209.6, ripples R-B -22.4, near water 125.3 — all identical to
  round 08's passing numbers.
- **cam02's framing is now correct** — the first round in which cam02 contains the picture ref 062 contains.
- **cam03 and cam06 stay closed** (frame black 12.8 %, outer row 0.165; cam06 ratio 0.636 with 3 far-shore lines).
- **Weathering stays at or above the photograph's**: under-cornice 20.0 % (photo 19.2 %), waterline 48.2 % on 220
  columns (photo 38.2 %), capital alternation 1.06x the photo's contrast.
- **Eevee is cheap and stable**: six-camera pass **137.5 s**; Cycles hero 380.6 s at 128 spp.

## Viewport performance and deliverables (pass/fail, not scored)

- Open **0.75 s** headless (budget 60 s) — pass. 9679 objects, 72 materials, 0 placeholders, 160.9 MB.
- LOD1 **11.38 M tris** — pass. Eevee previews 17.5-29.4 s each — pass.
- Cycles final config as saved: GPU, **768 spp** adaptive (threshold 0.01, min 64), OIDN, time limit 0,
  `AgX - High Contrast`, exposure **-2.8331**, 1920x1080 at 100 % — pass.
- `CAM_flythrough`, `CAM_flythrough_path`, `CAM_flythrough_target` present; 2 light probes; 7 cameras, active camera
  = the hero — pass. **Frame range 1-1224 at 24 fps = 51.0 s — QA-08-13 closed.**
- Eevee viewport config: taa 8 / 16, raytracing off, shadow ray count 1 — pass.
- **QA-03-16, the 4K 768-spp timing, has still never been run.** It is the only delivery item with no measurement
  behind it and it is now Phase 5's first job.

## Defect list — round 09 = the Phase 5 known-issues list, ordered by hero visibility

Each row is written to be pasted into the delivery notes: what a viewer sees on the hero first, its owner, and the
one-line fix. Severity is against the photoreal bar, not against shipping.

| # | id | cam | owner | sev | what a viewer sees (with the number) | one-line fix |
|---|---|---|---|---|---|---|
| 1 | **QA-09-2** (was QA-08-5) | 01 | materials | major | The lagoon mirrors the building at **0.614** of its own sunlit stone against the photograph's **0.872**; the reflection box reads **115.8**, 8 lum below the 124-208 window. The single largest area of the hero that does not look like the photograph. | Raise the mirror at grazing incidence without touching `WATER_GLOSS_MIX` — a low-roughness specular lobe above ~87 deg only — and re-check cam05's band stays <= 117. |
| 2 | **QA-09-3** (was QA-08-4 / 07-4) | 01, 02 | ornament + architecture | major | The arch intrados is a blank pale vault: **8 `SOCKET_archivolt_run_##`, 0 instances**, and the bed-mould has no modillions. At 1:1 it is the largest untextured surface in the hero's ornament zone. | Instance the archivolt band on the 8 existing sockets and add a modillion subtype to the bed-mould; target the photo's alternation count within 30 %. |
| 3 | **QA-09-1** (new) | 01 | materials + lighting | minor | The stone is now **more** saturated than the photograph everywhere except the one box the window is defined on: whole building **0.571 vs 0.521** (1.10x), columns **0.694 vs 0.595** (1.17x), entablature **0.735 vs 0.588** (1.25x), while the sunlit attic box is still 0.043 under its 0.53 floor. Hue is 3.2 deg yellow of the photograph's on the building block. | **Do not chase QA-08-3 further.** If anything is done, back the sun-side tint b off 70 -> ~55 and accept attic sat ~0.475: it costs 0.012 on one box and returns ~0.02 of saturation on the other three. |
| 4 | **QA-09-4** (was QA-08-10 / 07-10) | 01, 05 | environment | minor | The shoreline is a uniform dark hedge at **88.4 lum vs the photograph's 115.2 (0.767)** with no trunks, no built structure and no figures, against ref 169's willows, green-doored shed and people. Costs Scale cues on the hero. | Add trunk geometry to the front willow row plus one shed and 2-3 figures in the hero's 700-1200 band. |
| 5 | **QA-09-5** (was QA-08-7) | 03 | lighting + environment | major | The colonnade walk — the largest surface in cam03 — is **green: hue 92.1 at sat 0.138**, outside the 25-60 window, unmoved by r16's knob (frame delta 0.18 lum). | Tint the up-facing bounce on the walk warm, or lower `ENV` grass albedo's green bleed; hold the outer row at >= 0.15 of sunlit. |
| 6 | **QA-09-6** (was QA-08-2) | 02 | lighting | **blocker on cam02** | In **Cycles** all four shaded boxes on the camera-facing face are violet — hue **268 / 235 / 250 / 351** at negative R-B — where r16's Eevee tuning shows two of them warm (28.1 / 28.7). Cam02 is the one frame where the delivery engine and the preview engine disagree about colour. | Re-tune the anti-sun / horizon tint discriminators **against a Cycles frame**, not an Eevee one; acceptance is all four boxes at hue 25-60, sat <= 0.35, in Cycles, with the hero's shade held. |
| 7 | **QA-09-7** (was QA-08-6) | 05 | materials | major | cam05's lagoon band is **133.2** against the 70-117 window (ref 063: 93.4) — the cost of the gloss-mix decision that bought the hero its 11 lum. | Make the sheen ramp incidence-dependent so cam05's shallower angle is not lifted, or accept it as the documented hero/cam05 trade. |
| 8 | **QA-09-8** (was QA-08-8) | 04 | materials | major | The coffered saucer reads grey between orange ribs: field sat **0.341**, rim **0.634**, both outside 0.38-0.50 (ref 0.427 / 0.438). | Move `MAT_plaster_ceiling` up and `..._rib` down in albedo saturation until both land in 0.38-0.50 by `mat_r9_measure.py coffer`. |
| 9 | **QA-09-9** (was QA-08-9) | 04 | lighting | minor | Eevee and Cycles disagree about the west barrel-vault soffit by **+0.224** (test <= 0.15) for the fifth round running, and **Cycles is the wrong one** (0.237 against ref 083's 0.381). The Phase-5 Eevee test animation will not predict the Cycles final in that corner. | Extend probe / screen-trace coverage over the west soffit; acceptance gap <= 0.15 with Cycles within 0.10 of 0.381. |
| 10 | **QA-09-10** (was QA-08-11) | 01 | architecture | minor | Inside the correctly registered stack the entablature cornice is **1.33** of the photograph's rows (20 vs 15) and the frieze **0.87** (20 vs 23). Worth about 0.5 of Proportion on the hero. | Re-cut `CORNICE_H` / `FRIEZE_H` to within 15 % of the photo's rows and refit the rinceau. |
| 11 | **QA-09-11** (was QA-08-12 / 06-9) | 01 | architecture + materials | minor | Entablature row-profile std **37.3** on the fixed box against the >= 40 test (control box 40.3; ref 53.0) — the cornice and dentil shadows are shallower than the photograph's. | Deepen the cornice / dentil undercut so both the fixed and the course-tracking box pass >= 40. |
| 12 | **QA-09-12** (was QA-08-3, closed by the lead) | 01 | lead | closed / accepted | Sunlit stone sits at sat **0.487 / R-B 110.6** against the photograph's 0.582 / 134.2. Measured cap: AgX High Contrast passes only 0.19-0.24 % display blue per 1 % scene blue at lum 188 and the sun has no blue left. | Accepted as a colour-management limit of the shipped view transform. Re-opening it means re-measuring every window of rounds 3-9 under a new look — out of scope. |
| 13 | **QA-03-16** | — | lead | open | The 4K 768-spp render has never been timed. | Phase 5 step 1: one 3840x2160 frame at **128 spp fixed, adaptive off**, under an outer wall-clock guard, then choose the final sample count from that wall time. |
| 14 | **QA-09-13** (new, information) | 02 | lead | note | ref 062 is a **midday, sunlit-NNE-face** photograph; the shipped morning golden hour leaves that face in shade. cam02 can match ref 062's framing (it now does) but never its tonality. | State it in the delivery notes so the cam02 comparison is not read as a defect; score cam02 on hue family only. |

## Notes for the lead

1. **The round is honest and flat.** One socket and one lens were merged; four of six frames moved by less than
   0.25 lum mean. The hero is **+0.00**, which is the clock's first flat round (1 of 2), and under the user's
   round-08 instruction Phase 5 starts now.
2. **The one real gain is cam02's framing** (+0.25, top-band sky 0.2 % -> 91.8 % against ref 062's 91 %), and the one
   real discovery is that **cam02's violet face is still violet in Cycles** — lighting r16 measured it in Eevee.
   Whoever touches lighting again must measure on the delivery engine.
3. **QA-08-3 should stay closed, and round 09 is the argument for it.** The tint bought the headline box 26 % of its
   remaining gap and simultaneously took the whole building from 1.01x to 1.10x the photograph's saturation. The
   window is a property of one box, not of the picture; chasing it further makes the render less like the photograph,
   not more.
4. **The cheapest remaining hero points are still not colour**: the mirror level (Water reflection 3 -> 4) and the
   archivolt (Ornament 4 -> 4.5). Together they are worth about +0.17 on the hero — not the 0.33 the gate wants.
   The gate is not reachable inside the polish loop as scoped, which is why the rule stops it here.
