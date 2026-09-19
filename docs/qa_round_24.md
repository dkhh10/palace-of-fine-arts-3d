# QA round 24 — verification of the far-tree irradiance re-key on deploy 12, live URL, 2026-09-19

**Verdict: BLOCKER CLOSED. The QA-23 brightness regression is reverted on the delivered frames, 8e's blade margin is restored to the byte,
and nothing else in the scene moved. All five Phase 8 art items are closed and no blocker is open.**

Capture `gate12` on the live URL (deploy 12, version `6513cf48`, main `2be3817` / capture `aee019c`): desktop 1-6 at 1920x1080, `gate12_net.json`,
1440p `gate12_perf.json`, `?tier=mobile` 1-6 + `gate12m_net.json`, the mobile close orbit (80 m, h 5 m, headings 253 / 215). Before = `gate11`
(round 23, the re-bake) and `gate10` (round 22, pre-re-bake). Measures `scripts/qa_r24_probe.py` (a thin extension of r23 -> r22 -> … -> r13;
only the three-way comparisons are new), crossings `export/p8_atlas_probe.py viewer`. No Blender, no Chrome; the URL read with `curl` only.
Reference sets, the 960 px rule and the water mask exactly as round 23. Sheet `renders/web/gate12_gate.png`.

## 1. The 127 existing far trees — returned to their 6c values

`qa_r24_probe fartree3`, the QA-21 far-crown boxes, 960 px on both sides against the **Phase 8 Cycles** reference:

* **9 of 10 boxes are back within 3 % of gate10** — seven of them to three decimals (g12/g10 1.000x). The single exception is
  `05 lawn tree crown` at **0.957x**, and it moves **toward** the reference (1.143 g10 / 1.191 g11 -> **1.094x** g12), i.e. better than the
  pre-re-bake state.
* **Mean |viewer/cycles - 1| 6.7 % (g10) -> 9.7 % (g11) -> 6.3 % (g12)** — the QA-23 number is not merely undone, it is 0.4 points better than
  gate10's. The three QA-17 control crowns: `02 fill tree` 1.074 / **1.246** / **1.074x**, `05 lawn crown` 1.143 / 1.191 / **1.094x**,
  `01 hero shore crown` 1.075 / 1.101 / **1.083x**.
* **The dark cores are back**: dark share (luma < 0.20) equals gate10 at eight boxes and exceeds it at two, both toward Cycles
  (`02 fill tree` 67.81 -> **75.21 %**, Cycles 75.34; `05 lawn crown` 12.86 -> **21.52 %**, Cycles 34.76; `01 hero shore crown` 21.76 -> **23.68 %**,
  Cycles 29.69).

## 2. The 39 belt rows — untouched, and they read as shaded trees

They keep the r2 bake (median modulation 0.2424) and were not re-keyed. Their boxes move only with the far trees behind them: level
**0.957-0.984x** gate11, and **all four move toward the Phase 8 Cycles reference** (g11/p8 1.212 / 1.102 / 1.216 / 1.083 -> g12/p8
**1.194 / 1.055 / 1.186 / 1.058x**); box MAE vs Cycles **9.38 / 11.57 / 10.00 / 10.59 %**, better than round 23's 9.62 / 12.27 / 10.16 / 10.84 at
three of four. **Not black cut-outs**: near-black share (< 0.06) **0.00 / 0.00 / 9.09 / 0.00 %** against Cycles' 0.11 / 0.21 / 11.54 / 0.02, shaded
foliage (0.06-0.25) 41.6 / 24.7 / 48.6 / 18.0 % against 61.0 / 33.3 / 58.1 / 22.7, box sd 0.189-0.258 against 0.188-0.245. The 100 % tiles
(`/tmp/r24_c01_crowns`, `_c02_belt`, `_c05_lawn`) show crowns with sky gaps, trunks and internal tone, sitting where Cycles puts its dark mass, and
carried as broken dark streaks in the reflection.

## 3. 8e — the blade margin is restored exactly

`qa_r24_probe orbit3`, the six mobile close-orbit crown boxes: run p90 gate10 24/21/23/27/21/20 -> gate11 27/26/29/28/21/20 -> **gate12
24/21/23/27/21/20 px**, i.e. **mean 22.7 -> 25.2 -> 22.7 px** and **boxes at or under the 25 px target 5/6 -> 2/6 -> 5/6**. Coverage vs gate10
**0.991-1.000x** — no thinning bought the width back. The 100 % orbit tile shows separated leaf blades with sky between them.

## 4. Regression — everything else is byte-close

* **Frames, above the waterline** (g12/g11): luma 0.9950 / 0.9899 / 0.9979 / **1.0000** / 0.9930 / 0.9962x; **station 4 bit-identical**; MAE
  0.00-1.12 levels = **0.00-0.44 %, inside the brief's 0.5 % rule at every station**.
* **Parity improves at all six stations**, against the Phase 8 set (-0.19 / -0.17 / -0.07 / 0.00 / -0.22 / -0.16) and against the Phase 5 set
  (-0.19 / -0.20 / -0.07 / 0.00 / -0.21 / -0.15).
* **Architecture unmoved**: of the nine true architecture boxes, **seven are bit-identical**, `capital row` is 0.984x and the non-reproducible
  water reflection 0.998x — **0 of 9 move more than 3 %**. The four boxes that do are all foliage and all move *down*, back toward gate10.
* **Far crowns (crossings per 100 px, Phase 5 Cycles in brackets)**: cam01 11.64 -> **11.68** (11.73), cam02 9.10 -> **7.33** (7.76) — round 23's
  overshoot is gone — cam05 9.37 -> **12.28** (15.89, QA 21 11.67), so **the QA-23 cam05 residual closes to within 0.61 of QA 21**. cam02's
  dark-foliage share **57.35 -> 69.86 %** against Cycles' 72.26: **QA-23 residual 2 (the belt covering less than Cycles) narrows from 12.6 points
  to 2.4** without a density change.
* **8a carried numbers revert with the level**: leaf-share mean **0.92 -> 0.86x** of the reference (QA 22's value) and every box level returns
  (`01 shore shrub S` 1.13 -> 1.08x ref, `05 shrub/reed shore` 1.11 -> 1.08x). **The hard-edge share does not**: `01 shore shrub S` 2.78 (g10) /
  6.31 (g11) / **5.95 % (g12)**, `05 shrub/reed W` 5.73 / 7.23 / **7.12 %**. Since the luma reverted and the edges did not, **QA 23 mis-attributed
  this rise to the modulation; the cause is the belt r2 standing behind those shrubs.** Residual, owner ENV — not a blocker (ref 3.38 / 4.06).
* **The QA-21 dotted rim returns to its gate10 level**: lattice mean -6.03 -> **-5.61**, worst box `02 fill tree` 2.57 -> **6.71**, still **3/10**
  above their Cycles control. Visible at 100 % on cam02's crown rims. Residual 1 of round 21 stands, owner VIEWER, unchanged by this round.
* **Payload**: desktop **46 756 312 B / 318 req** before the first frame (**-5 105** vs gate11), mobile **46 824 395 B / 376 req** (-288) — both
  inside the 50 000 000 rule. Totals 586.9 / 67.1 MB. One 404 (favicon) as before; **0 page errors** in all three captures.
* **Perf**: draws [317, 341, 371, 197, 308, 305], triangles [4.95, 5.51, 7.35, 2.96, 4.93, 4.71] M, programs and **resident 1 814.2 MB
  (tex 1 255.6, geo 114.5, rt 443.8)** are **identical to gate11 in every figure** — the scene did not change. The 1440p medians nevertheless read
  +3.5 / +5.4 / +2.2 / +0.3 / +1.5 / +0.5 ms (hero **31.7 ms / 31.5 fps**, cam03 40.8 / 24.5 fps): with the geometry bit-identical this is a
  session / thermal difference (the 4K Cycles hero had just released the machine), **not charged**, but the 45 fps target stays open and the next
  perf number should be taken on an idle machine.
* **Mobile**: station 4 byte-identical; 1 / 2 / 3 / 5 / 6 differ over 3.9 / 5.3 / 0.6 / 6.9 / 9.3 % of pixels, MAE 0.02-0.69 levels — the far trees
  and what stands behind them, nothing else.
* **Name sweep**: 738 desktop manifest rows + 341 mobile, **0 object-shaped hits**; 0 mobile paths absent from the desktop plan.

## 5. Scores

Rubric as QA 17 (six rows, station = their mean, so one row moving 0.5 moves a station 0.083). Only stations with far trees in frame may move.
Desktop: **01 4.01 · 02 3.30 · 03 2.83 · 04 2.88 · 05 3.28 · 06 3.07** — deltas vs QA 23 **+0.04 / +0.08 / 0 / 0 / +0.08 / +0.04**.
**01** foliage material +0.25: the far crowns return to gate10 and the frame's deviation from Cycles is the best of the three gates, against the
dotted rim returning with them. **02** background +0.5: the control crown is back at 1.074x Cycles with its dark core, and the belt's cover gap
closes to 2.4 points; foliage material held flat because the crown rim is back at its gate10 stipple. **03 / 04** unchanged (MAE 0.17 / 0.00
levels). **05** foliage material +0.5: the lawn crown moves past gate10 toward Cycles and the crossings return. **06** +0.25 for its two crowns
returning to gate10 level; R1's colour residual is where QA 22 left it.
Mobile: **01 3.40 · 02 3.38 · 03 2.52 · 04 2.70 · 05 3.04 · 06 2.62** — deltas **+0.08 / +0.08 / 0 / 0 / +0.08 / +0.04**. Mobile takes the same
gains and reverses QA 23's -0.25 hero foliage-material charge, 8e's blade p90 being restored to 22.7 px.

## 6. Residuals for `docs/delivery.md`, with owners

1. **CLOSED** — QA 23 residual 1 (the far-tree irradiance brightness regression, EXPORT). Reverted on the delivered frames; no successor.
2. **QA 23 residual 2 narrows** (the belt covering less of the pale backdrop than Cycles — ENV): cam02 now 2.4 points under Cycles' dark share
   (was 12.6) and cam05's crossings 3.6 under (was 6.5). Still open, no longer material at cam02.
3. **QA 23 residual 3 stands** (the belt drawn as LOD2 meshes at cam03: 7.35 M tris, 371 draws, the slowest station — EXPORT/VIEWER). Unchanged.
4. **Re-attributed** — the shrub hard-edge rise (01 shore shrub S 2.78 -> 5.95 %, 05 shrub/reed W 5.73 -> 7.12 %) belongs to the belt r2, not the
   re-bake; owner **ENV**, carried, not hero-visible.
5. **Carried unchanged**: QA 22's cam06 R1 colour move (ENV) and the 8a cam03 bush-interior darkness (VIEWER/LIGHTING); QA 21's dotted crown rim
   (VIEWER, back at its gate10 level), station 2's crown coverage (BAKE/VIEWER), azimuth-frame popping untested, the blue-violet shaded stone on
   cam02 (Phase 5 lighting, the user's call), cam03's missing deep shade, cam06's water moiré, the reflection cooler than Cycles, the hero under
   45 fps at 1440p, and the user's Safari hero screenshot and iPhone walk recording.
