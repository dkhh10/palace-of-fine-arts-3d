# QA round 14 — Phase 6 **Gate 4, the viewer proper**, 2026-09-16. **ONE MORE ROUND** (no blocker)

Scored on `round14` (`phase6-viewer` @ 1cc73fd, 1920x1080, manifest v4, `lighting=baked&post=all&probe=1&impostors=1&
water=1&billboards=0&treeboards=0&t=0`) against the `round14nopost` control, the round-13 `round13b` frames, and the
references: station 1 the Phase 5 Cycles hero, 2-6 `renders/previews/qa/round13_0N_*_cycles.png` (128 spp, compositor
on). No Blender, no Chrome. Tools: `scripts/qa_r13_probe.py --round 14 {boxes green shafts frame black band foliage
mist water walk perf}` (extended, not forked — new `band / foliage / mist / water / walk` and a `--round` selector)
and `scripts/qa_r13_gate.py --round 14` -> `renders/web/round14_gate.png`. Boxes unchanged from round 10b / 12b.
cam06's 0.71x, the foliage hue and the probe-as-diffuse-environment override are on record, not re-litigated. The
README's "QA notes — read before scoring" (3a84e3f) was dropped from `web/README.md` again at 184d785; read from git.

## 1. Parity per station, and what each Gate 4 item bought

| station | post=all | post=off | round13b | reference | ratio | MAE r13 -> r14 |
|---|---|---|---|---|---|---|
| 01 hero | 129.0 | 124.2 | 136.0 | 139.98 | **0.92x** | 29.9 -> **27.9** |
| 02 NE 3/4 | 101.1 | 96.5 | 110.9 | 100.38 | **1.01x** | 26.9 -> **24.5** |
| 03 colonnade | 81.8 | 80.6 | 81.7 | 48.99 | **1.67x** | 37.0 -> 36.4 |
| 04 ceiling | 70.7 | 70.3 | 60.1 | 63.44 | **1.11x** | 21.5 -> **13.1** |
| 05 south lawn | 156.8 | 148.2 | 163.0 | 151.16 | **1.04x** | 24.2 -> **22.3** |
| 06 aerial | 77.8 | 47.2 | 72.1 | 100.86 | **0.77x** | 45.0 -> **37.1** |

MAE falls at all six. **Post** is the whole story at cam06 (47.2 -> 77.8) and +4..+9 luma elsewhere, and costs
contrast everywhere. **The probe** closed QA-13-1 and most of the olive. The round-10b boxes at cam01:

| box | round13b | **round14** | reference | read |
|---|---|---|---|---|
| hero shade band | 114.0 (0.93x) | **124.8 (1.02x)**, std 1.07x | 122.1, std 44.2 | **closed** |
| sunlit attic **hold** | sat 0.460 (0.89x) | **sat 0.416 (0.80x)**, std 0.85x | 0.518, std 29.5 | **breaks further** |
| S-colonnade wall | 170.8 (1.23x), mid 18.3 | **164.7 (1.18x)**, mid **14.6 (0.40x)**, std 0.48x | 139.3, mid 36.6 | QA-12b-2, flatter |
| N-colonnade wall | 71.0, **hue 219.9** | **55.8 (1.00x), hue 40.2** | 56.1, hue 40.9 | **QA-13-1 closed** |
| capital row | 151.4 (1.11x), std 0.93x | **153.7 (1.13x), std 0.69x** | 136.4, std 62.4 | level held, **flattened** |
| entablature / columns | 118.6 (0.99x) / 114.8 (1.00x) | 136.9 (1.14x) / 127.4 (1.11x) | 120.2 / 114.3 | over-lifted |
| vault field | 46.1 (0.76x) | **76.0 (1.25x)** | 60.6 | over-shot the other way |
| water reflection strip | 135.3 (1.05x), sat 0.163 | **115.5 (0.90x)**, sat 0.77x, R-B 0.67x | 128.6, sat 0.250 | §2 |
| cam05 pier face | 153.2 (1.05x), std 1.00x | 161.5 (1.11x), **std 0.82x, sat 0.72x** | 145.9, sat 0.810 | washed |
| cam04 coffer field | 24.3 (0.40x), p10 0.00 | **60.1 (1.02x)**, p10 29.5, std 0.98x | 58.7, p10 28.6 | **QA-13-2 closed** |

**QA-13-1 CLOSED.** Band `20 520 540 645`, B > R + 20: **23.0 % -> 0.2 %** (Cycles 0.0 %, gate 3.9 %); the same
surface at cam06 **64.7 % -> 4.6 %** (reference 10.9 %, now *less* blue than Cycles).
**QA-13-2 CLOSED.** Coffer field 0.40x -> **1.02x**, p10 0.00 -> **29.5** (ref 28.6), below luma 8 **37.78 -> 0.02 %**
(ref 0.03 %); soffit 24.4 -> 56.6 (1.12x).
**QA-12b-1 — closed at cam06, 3.4x at cam02.** G > R: cam06 **20.2 -> 1.5 %** (ref 1.4 %), cam02 **19.7 -> 7.4 %**
(ref 2.2 %), cam01 0.6 -> 0.3 % (ref 0.1 %), cam05 5.1 -> 8.5 % (ref 6.0 %). All of it is post (post-off still
19.7 / 19.5 %) — the airlight the decision log predicted. The cam02 residue is the foliage, §4. Not the lightmaps.
**Sunlit-attic sat hold FAILS worse:** 0.518 -> 0.460 -> **0.416 (0.80x)**, entirely post (post-off 0.460).
**QA-12-4 largely closed:** shaft CV south **0.088 -> 0.327**, north **0.187 -> 0.361** (Phase 5 0.469 / 0.539).
**Carried, improved:** colonnade-roof light leak 1.68x -> **1.34x**.

## 2. Water at cam01 — **QA-14-1, the worst measurement of the round**

The rotunda **does** reflect — arch, attic and shaft row legible at 100 % (r2c2) — so the 6a criterion is met. The
surface is not.

| crop | round14 | reference | ratio |
|---|---|---|---|
| reflection mass `700 700 1300 950` sat / R-B | 0.351 / 29.0 | 0.596 / 63.2 | **0.59x / 0.46x** |
| **open water** `300 900 1600 1060` lum / hue / sat | 66.8 / **200.2 deg** / 0.326 | 118.0 / **144.8 deg** / 0.041 | **0.57x / +55 deg / 8x** |
| **ripple** (mean row-to-row \|dLuma\|), open water | **0.97** | **13.23** | **0.07x** |
| ripple, reflection mass | 2.98 | 10.09 | 0.30x |
| **row/col high-pass** (streaks), open water | **0.72** | **3.24** | a mirror, not a lagoon |

Fresnel, mean luma of 40 px rows far shore -> near edge: reference **96.5 93.4 87.8 81.0 71.8 66.7 63.2 60.4**, a
smooth fall; viewer **72.7 82.1 85.3 59.8 46.1 43.0 42.8 41.1**, collapsing at the fourth row and flat at ~41 over the
whole near half — the hard boundary visible in tiles r2c1/r2c3 where the reflection stops along a line and the water
becomes a plain blue slab. The ripple normal map produces no visible structure, and the murk tint is a saturated blue
(hue 200) where Cycles' lagoon is near-neutral green-cyan (145, sat 0.041). The same surface makes cam06 read black.

## 3-5. Impostors, foliage, mist

**Impostors.** Rotational pop swept by the viewer (61 frames at 1 deg, max/median 1.21x). Silhouettes correct; no
frame seam, no pop, no LOD snap; paler/flatter/bluer than the reference, on record. New: the colonnade-roof canopy is
thin and speckled with **white bloom fireflies** on the alpha edges (r1c1), and one impostor at ~`500-620, 560-660`
is close enough to read as a blurred grey-blue billboard beside sharp neighbours (r2c1).
**Foliage.** cam02 near trees hue **221.5 -> 56.6** vs Cycles **102.4** = **-45.9 deg**, G>R 37.4 vs 70.9 %; cam01
shore planting +1.3 deg, cam06 shoreline +3.3 deg. The logged decision **half-closed** it — the blue is gone
everywhere and the hue lands at cam01/cam06, but the cam02 near trees are amber-brown where Cycles is olive-green,
exactly as predicted, and that is most of the cam02 G > R residue.
**Mist** is an airlight, not a linear fog: at cam06 post lifts the **far** band's p10 by **+52.3** (21.4 -> 73.7, ref
76.9) and the **near** band's by **+1.9**; far level 0.85x. Two errors: the far band's **sat 0.622 vs 0.169 (3.7x)**,
so cam06's backdrop terrain is warm ochre where Cycles is grey-blue haze; and cam06's near half is crushed (0.53x,
**p10 3.6 vs 58.0**), which an airlight correctly cannot reach. cam03's 1.67x is not mist: near p10 **52.5 vs 17.0**,
and post moves the frame 1.2 luma.

## 6. The cam01 six tiles at 100 % (`renders/web/tiles/round14/`)

| tile | defect |
|---|---|
| r1c1 | Roof impostor canopy thin and pale, **white bloom fireflies** on the alpha-tested leaf edges. |
| r1c2 | **Bloom halo ringing the dome cap** into the sky; shade side flatter than the reference (less contact shade under every cornice); barrel washed at 1.25x. Structure, ornament, dentils, frieze, capitals all correct. |
| r1c3 | The round-13 blue roof strip is **gone**; the south attic now reads desaturated grey-cream where the reference is warm ochre; left impostor flat olive against a lit textured tree. |
| r2c1 | **QA-13-1 gone**, bays warm ochre — but the backdrop wall behind them is a **uniform untextured mustard field** (the probe's single point); shoreline planting is **hard yellow-and-black angular leaf confetti**; white/violet speckles on the water. |
| r2c2 | **QA-14-1**: an evenly blurred dark mirror where the reference is broken into bright golden ripple streaks. Near shrubs are blue-grey blobs; leaf clusters show **black gaps through the alpha cut-outs**. |
| r2c3 | **QA-12b-2**: S-colonnade wall a flat cream field with hard-edged leaf cards pasted on it (mid 0.40x). The reflection **stops along a hard line** (the §2 Fresnel collapse). |
| all six | No lightmap seam, no slot bleed, no texel blockiness, no encoding banding, no z-fighting, no filled opening, no missing ornament, no placeholder-grade object. |

**Name sweep.** Export set **0 to explain** (export engineer's Gate 3 r2 sweep, docs/status.md 2026-09-16; nothing
re-exported for this capture). Viewer-side the 127 `WEB_far_tree_billboard_*` carriers remain in `env.glb` and remain
hidden (`hiddenBoards: 127`, `billboards=0&treeboards=0`); the octahedral impostors draw in their place. On record.

## 7. Definition of done 6a

| row | 01 | 02 | 03 | 04 | 05 | 06 |
|---|---|---|---|---|---|---|
| Silhouette match | 4 | 3.5 | 2.5 | 3.5 | 3.5 | 3.5 |
| Proportion | 4 | 3.5 | 3 | 3.5 | 3.5 | 3.5 |
| Ornament fidelity | 4 | 3 | 3 | **3** (2) | 3 | 2.5 |
| Material realism | 3.5 | **3** (2.5) | 3 | **3** (2) | **2.5** (3) | 2.5 |
| Edge wear | 3.5 | 2.5 | 2 | **1.5** (1) | 2.5 | **1** (0.5) |
| Lighting mood | **4** (3.5) | **3** (2) | **2** (3) | **3** (1.5) | 3 | **2.5** (2) |
| Water reflection | 2.5 | n/a | n/a | n/a | **2** (2.5) | 2 |
| Repetition visibility | **3.5** (3) | 2.5 | 2.5 | **2.5** (2) | 2.5 | **2.5** (2) |
| Scale cues | **3.5** (2.5) | **2.5** (2) | 2.5 | 3 | **3** (2.5) | **3** (2.5) |
| **round 14** | **3.61** | **2.94** | **2.56** | **2.88** | **2.83** | **2.56** |
| round 13 | 3.39 | 2.69 | 2.69 | 2.31 | 2.89 | 2.33 |
| round 09 (Phase 5) | 3.67 | 2.94 | 2.56 | 2.81 | 3.06 | 2.67 |
| **delta vs Phase 5** | **-0.06** | **0.00** | **0.00** | **+0.07** | **-0.23** | **-0.11** |

Round 13 in brackets where a row moves. cam03's Lighting mood drops because this is the first round scored against a
compositor-on Cycles reference, not because the frame changed — the correction the README warned about.

| 6a criterion | result |
|---|---|
| every station within 0.5 of Phase 5 | **PASS**, worst -0.23 (cam05) |
| none below 2.5 | **PASS, thin** — cam03 and cam06 both at 2.56 |
| water reflects the rotunda at the hero | **PASS** (legible at 100 %); the surface is QA-14-1 |
| walk clamp, never in the lagoon | **PASS** — 24/24 probes, zero steps in water; lagoon headings refused (st1/180 1783 of 1801, st2/270 1561, st5/180 1711), inland headings run the full 96 m. **Marginal FAIL on `WATER_Z + 0.1`**: 3 of 24 stand at **-1.225 m**, 25 mm under the -1.20 floor and 75 mm above the water (st1/270, st2/270, st5/270) — riprap at the waterline |
| loading screen with progress | **PASS** — bar, `175.6 / 522.3 MB — orn.glb`, per-class name. Denominator is the *planned* 522.3 MB against **639.0 MB loaded**: the bar under-reports by 18 % and finishes early |
| >= 45 fps median at 1440p | **NOT MET** — **28.9 ms = 34.6 fps** at the hero; 33.3 / 32.5 / **45.0** / 35.3 / 31.2 at 02-06. GPU median **2.7 ms** (p95 28.4), 314 draws, 5.24 M tris, resident **1 677.8 MB** (tex 1 171.6 + RT 443.8 + geo 62.4), load 639.0 MB in 6.24 s. Attribution as the viewer measured it: the Reflector's second traversal (314 -> 164 draws, 6.3 ms) plus full-res bloom (8.4 ms) push a 17.3 ms frame past one 16.7 ms vsync interval and it quantises to two — 2.7 ms of GPU work in a 28.9 ms frame, not a renderer cost |
| deterministic headless screenshots | **PASS** — `t=0`, `__pfaReady`, no input, six stations in one command |

## 8. Verdict — **ONE MORE ROUND**, no blocker

Gate 4 did what it was for: **QA-13-1 and QA-13-2 closed outright**, QA-12b-1 closed at cam06 and cut to a third at
cam02, QA-12-4 largely closed, MAE down at all six, four of six stations gain, every station inside the 0.5 window and
none under 2.5. Nothing is a blocker and nothing needs a re-bake. It is not a pass because three things a walkthrough
is judged on are visibly wrong at 100 % and the frame rate is not met. In order of cost:

1. **QA-14-1 water (viewer).** Ripple 0.07x, row/col 0.72 vs 3.24, level 0.57x, hue +55 deg, sat 8x, Fresnel flat
   over the near half — the largest visible error in the hero frame, and it drives cam06's black lagoon too.
2. **QA-14-2 cam03 (lighting transfer).** 1.67x, p10 39.8 vs 7.3 — no deep shade; Gate 4 did not touch it.
3. **QA-14-3 cam06 lower frame.** p10 9.7 vs 65.6, near ground 0.53x, far terrain sat 3.7x. cam03 and cam06 sit on
   the 2.5 floor because of 2 and 3.
4. **QA-14-4 bloom flattens the hero** (capital-row std 0.69x, S-colonnade mid 0.40x, vault 1.25x, attic sat 0.80x,
   dome halo, leaf-edge fireflies). The half-res lever was measured and not shipped; a lower threshold / smaller
   radius is the same lever and buys part of item 6 too.
5. **QA-14-5 near foliage.** Flat angular cut-outs with black gaps at 100 %; cam02 hue -45.9 deg. Held, still open;
   vertex irradiance for shrubs and reeds is the remaining candidate.
6. **Perf 34.6 fps vs 45** — attributed, in flight, not re-litigated here.
7. **Minors:** the walk floor by 25 mm at three stations; the loading bar's 18 % denominator error; the backdrop wall
   as one flat mustard field (probe single point, on record); QA-12b-2 at 1.18x / mid 0.40x and the colonnade-roof
   leak at 1.34x (both carried, both improved); `web/README.md` has lost its QA-notes section a second time.

Composite: `renders/web/round14_gate.png`.
