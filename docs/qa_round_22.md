# QA round 22 — Phase 8 items 8a (relight + 8a-3 shrub-card UV scale), 8d (backdrop), 8e (mobile leaf cards) and the viewer fix round, on the live URL, 2026-09-19

**Verdict: 8a NOT CLOSED (closed at stations 1 and 5, untouched at 3) · 8d NOT CLOSED — BLOCKER · 8e CLOSED · fix round VERIFIED.**
The 8d tree belt is drawn as hard-edged, untextured, faceted low-poly shards in every intercolumniation at cam01, cam02 and cam05 at 100 %, and in the
lagoon reflection. It replaces a flat pale wall with flat pale spikes: the numeric colour gains do not override what the tiles show (gate rule, 2026-09-10).

Capture `gate10` on the live URL (deploy 10, main e393b33): desktop 1-6 at 1920x1080, `gate10_net.json`, 1440p `gate10_perf.json`, `?tier=mobile` 1-6,
`gate10m_net.json`, and the mobile close orbit (80 m, h 5 m, headings 253 / 215). Before = `gate9` / `gate9m` (round 21) and `gate7_orbit*` (round 19).
Measures `scripts/qa_r22_probe.py` (extending r21 -> r20 -> … -> r13 unchanged), tiles `scripts/qa_r22_tiles.py`, crossings `export/p8_atlas_probe.py viewer`.
No Blender, no Chrome; the URL read with `curl` only. Sheet `renders/web/gate10_gate.png`.
**Water mask** (the reflector is not session-reproducible): every viewer-vs-viewer pixel number below keeps cam01 y < 680, cam05 y < 910, cam06 y < 540
(its top row, where 8d lives); cam02 / 03 / 04 have no water in frame. Whole-frame rows are printed by the probe but carry no claim.

## 1. 8a — the relight and the shrub-card UV scale

**The eight QA-17 boxes** (`qa_r22_probe shrubs`), gate9 -> **gate10** (reference): level within the 3 % budget at 7/8; **05 shrub/reed W 1.032x** is 0.2 pt
over it. Hard-edge share: **no box newly crosses the reference** and one box crosses back below it (01 shore shrub S 6.06 -> **2.78 %**, ref 3.38); three boxes
move more than the 0.3-point allowance but **all three move down, toward the reference** (01 shore 3.70 -> 3.17, 05 W 8.00 -> 5.73) — the allowance was written
against a rise, and the direction is right. Leaf-green share (REPORT, not a gate, per the 8a decision): mean **0.86x of the reference, unchanged to 0.00x**;
per box 0.80 / 0.80 / 0.64 / 0.87 / 0.31 / 1.14 / 0.54 / 1.79. Hue unchanged (< 0.5° at every box).

**The tiles are the acceptance, and they split.** At **cam05** (`/tmp/r22_shore_05.png`, sheet panel 1) gate9's shore band is gold confetti — 20-40 px leaf
blobs with black gaps; **gate10's cards carry small varied leaves and read as lit-and-shaded bushes**, the closest the viewer has been to the Cycles row above
it. At **cam01** the same: the shore band is fine-grained instead of chunky. At **cam03** (`/tmp/r22_shore_03.png`) gate9 and gate10 are near-identical and
still large flat gold/black cut-outs against Cycles' dense dark bushes — 8a-3 scaled the **LOD2** cards (env.glb / env_t0), and cam03 sees the **LOD1 walk-in**
set at ~8 m, which nothing this round touched. **The 25 m LOD switch at cam05 is not visible** in the band: no tile-size step, no luminance step across the
switch distance (the strip is continuous; blob size 23.8 -> 16.9 px per the export matches the LOD1 card).
**8a verdict: NOT CLOSED** — closed where 8a-3 reached (1, 5), open at 3. The remaining item is the LOD1 walk-in card's texture scale, owner EXPORT.

## 2. 8d — the backdrop (BLOCKER)

**What the tiles show.** `/tmp/r22_hero_bandN.png`, `/tmp/hero_r2c1.png`, `/tmp/hero_r2c3.png`, `/tmp/bd25.png` (all 100 %): behind the north **and** south
colonnades, and at cam02 and cam05, the R2 tree belt is a row of **hard-edged faceted polygons in two flat tones** — straight silhouette edges, visible
vertices, no leaf texture, no light through the gaps. ref 169 at the same registered pixels is a soft dark mass with deep shade. The belt is ~58 triangles per
crown (6 986 tris / ~120 crowns) and looks it. It is in two of the six hero tiles, in the third through the centre gap, and it is reflected in the lagoon.
**This is a new hero-visible geometry/material defect and a regression against gate9's flat wall.**

**What the numbers say** (`qa_r22_probe backdrop`; the Phase 5 Cycles column at these boxes is the BEFORE state — it was rendered with the old backdrop
materials — so it is not the target here): cam06 top row luma 0.426 -> **0.444** (target ~0.80, ref 105 **0.834**), saturation 0.388 -> **0.329** (target ~0.10,
ref 105 **0.071**) — about **15 % of the stated saturation move and 5 % of the luma move**. cam06 city r1c3 sat 0.391 -> 0.337; **06 far field sat 0.377 ->
0.263** is the one box that moves properly (-30 %). Hero N band sat 0.652 -> **0.596** (target ~0.43, ref 169 0.395); its **luma sd falls 0.156 -> 0.153 and its
hf 0.1312 -> 0.1306**, where the 8d report predicted sd **up** 0.159 -> 0.177 — the delivered frame moved the opposite way, and both stay far under ref 169's
0.200 / 0.2027. Hero S band is worse on both: sd 0.216 -> **0.190**, hf 0.1485 -> **0.1234** (ref 0.258 / 0.234). The far lawn is **not** washed out
(luma 0.493 -> 0.493, sat 0.401 -> 0.385, ref-side of Cycles' 0.430).
**No seam and no tiling** anywhere (`qa_r22_probe seam`): the lattice index is -3.7 to -10.4 at all seven boxes, at or below its own Cycles control.
**8d verdict: NOT CLOSED, blocker, owner ENV (+ EXPORT for the re-bake).** R1 moved in the right direction and under-delivered; R2 must be re-shaped or
reverted before any gate. The belt does not satisfy "a dark tree belt with light through the gaps".

## 3. 8e — the mobile leaf cards

Measured on the **delivered** orbit frames, read at their native 1170x2532 (`qa_r13_probe.rgb` resizes everything to 1920x1080 and silently squashed the
portrait orbit frames — QA 19's orbit statistics were computed on that squashed raster; a carried measurement defect, fixed here).
`qa_r22_probe orbit`, six crown boxes over the two headings, run-width p90 of contiguous sunlit-leaf runs, gate7_orbit -> **gate10_orbit**:
35 -> **24**, 29 -> **21**, 35 -> **23**, 30 -> **27**, 25 -> **21**, 23 -> **20** px; **mean 29.5 -> 22.7 px**, **5/6 boxes at or under the 25 px target**
(before 2/6). **Coverage 1.02-1.23x — no thinning anywhere** (the kv-2.5 failure mode does not appear; the smaller blades fill *more* of the box).
Tiles (sheet panel 4, `/tmp/r22_orbit_h02530.png`): gate7's ~40 px duotone blades become many small leaves with visible internal structure. The QA-19 mobile
leaf-blade finding **closes**. **One gap: the 2.5 m walk-up was not captured** — `gate10_orbit.json` has `walkProbes: []` — so "no fattening close up" is
carried from the export's own measurement, not verified on a frame. **8e verdict: CLOSED**, with the walk-up owed (owner LEAD, one capture).

## 4. The viewer fix round — VERIFIED

Draws / triangles per station, gate9 -> gate10: **hero 6 361 468 -> 4 966 388 (-1 395 080**, claim -1 410 000**)**, cam06 6 729 552 -> 4 719 000
(**-2 010 552**, claim -2 020 000); every station falls (-0.33 M to -2.01 M), draws 335 -> 317 at the hero. Mobile 5.29 -> 3.69 M at the hero.
**Resident, the new figure of record: 1 814.8 MB desktop** (gate9 1 862.9; geometry 261.2 -> 115.2, textures 1 157.6 -> 1 255.6 with the impostor atlases now
counted, render targets 443.8 unchanged) and **551.0 MB mobile** (563.5). Both are ~0.6 MB / 3.1 MB above the branch's 1 814.2 / 547.9 — close, but the
delivered numbers are these. **Perf, 1440p medians: 28.2 / 32.5 / 35.1 / 24.2 / 30.9 / 32.2 ms**, vs gate9 **-4.3 / -1.0 / -2.9 / -0.6 / +0.6 / -3.9**, and
below the idle `gate5cold` baseline at all six. The band's flagged station 3 is **35.1 ms, not slower** (38.0 before). Hero **35.5 fps** (30.8 before).

## 5. Regression, rules, mobile

* **Frames, above the waterline.** g10/g9 luma 1.0013 / 0.9858 / 1.0035 / **1.0000** / 1.0024 / 1.0415x; station 4 is bit-identical. MAE against Cycles rises
  at 02 (18.61 -> 18.68), 03 (34.53 -> 34.77) and **06 (14.64 -> 18.30)** and at 01 (13.18 -> 13.47): **8d moves the viewer away from the frozen Phase 5
  Cycles look**, which the Phase 6 stopping rule scores as *parity*. The lead should note that viewer-vs-Cycles parity at every backdrop box is now
  unreachable by the viewer alone.
* **Boxes.** 3 of 25 move more than 3 %: S-colonnade wall 0.929x, N-colonnade wall 0.930x, 05 shrub/reed W 1.032x. The two "wall" boxes are **inside the 8d
  band** and sample the backdrop through the intercolumniation, not palace stone — **0 of the 9 true architecture boxes move** (max 1.023x, the capital row).
* **Far crowns.** Crossings per 100 px, gate9 -> gate10 (Cycles): cam01 11.97 -> **11.80** (11.73), cam02 7.35 -> **7.34** (7.76) — both inside the 0.3
  tolerance; **cam05 11.67 -> 10.80 is outside it** and moves away from Cycles' 15.89. Its foliage-under-40 share falls 10.41 -> 8.69 %, i.e. the crowns did
  not change — the belt behind them got brighter and fewer crown pixels fall under the dark threshold. Same root cause as §2; owner ENV.
* **The QA-21 dotted rim is unchanged** (`qa_r22_probe grid`): mean lattice index -5.37 -> -5.61, **3/10 boxes above their Cycles control in both captures**,
  worst still `02 fill tree` (7.81 -> 6.71). Residual 1 of round 21 stands as written, owner VIEWER.
* **Payload.** Desktop **46 882 679 B / 320 req** before the first frame (+5 350 vs gate9), mobile **46 810 129 B / 376 req** (+2 781) — both inside the
  50 000 000 rule (the export's tier-0 delta was +312 B; the rest is the JS bundle and request variance). Totals 587.3 / 67.3 MB. One 404 (favicon) as before;
  **0 page errors** in all three captures.
* **Mobile.** Station 4 byte-identical; 1 / 2 / 3 / 5 / 6 differ over 2.2 / 14.8 / 8.3 / 2.6 / 11.3 % of pixels, and a 8x3 change map puts **every** changed
  cell in the shore / planting / backdrop bands — sky and architecture bands are at 0 %. Nothing moved that was not the shrub cards, the backdrop or the
  8e leaf cards, as the contract requires.
* **Name sweep.** 738 desktop manifest rows + 341 mobile, **0 object-shaped hits**; 0 mobile paths absent from the desktop plan.

## 6. Scores

Rubric as QA 17 (six rows, station = their mean, so one row moving 0.5 moves a station 0.083).
Desktop: **01 3.81 · 02 3.14 · 03 2.75 · 04 2.88 · 05 3.12 · 06 3.03** — deltas vs QA 21 **-0.08 / -0.17 / 0 / 0 / 0 / +0.08**.
**01** foliage material +0.5 (the shore cards) against background realism -1.0 (the faceted belt in three of six hero tiles and in the reflection).
**02** background realism -1.0: the belt is the whole left-of-centre band at 100 % and there is no compensating gain (cam02's foreground is the untouched
LOD1 set). **05** +0.5 foliage, -0.5 background — they cancel. **06** +0.5 on backdrop colour (sat -15 % city, -30 % far field, luma up) with the faceted
form untouched. **03** and **04** unchanged (cam04 is bit-identical).
Mobile: **01 3.2 · 02 3.22 · 03 2.44 · 04 2.7 · 05 2.88 · 06 2.58** — deltas **0 / -0.08 / +0.04 / 0 / +0.08 / +0.08**. Mobile carries the 8e gain
(desktop draws `env_trees_lod1.glb` and does not) and the same belt loss.

## 7. Residuals for `docs/delivery.md`, with owners

1. **NEW, BLOCKER — the 8d tree belt draws as faceted untextured low-poly shards at cam01 / 02 / 05 and in the reflection — owner ENV.** Re-shape (more
   crowns, fewer facets, a leaf material) or revert R2; R1's colour move may stay.
2. **NEW — 8d R1 delivered ~15 % of its cam06 saturation target and ~5 % of its luma target, and the hero band's luma sd and hf moved the wrong way
   — owner ENV.** The Eevee preview's before/after direction did not transfer to the delivered frame at the hero.
3. **NEW — 8a-3 did not reach the LOD1 walk-in shrub cards; cam03's cards are unchanged magnified cut-outs — owner EXPORT.**
4. **NEW — the 2.5 m mobile walk-up was not captured this round — owner LEAD.** One capture closes the last line of the 8e contract.
5. **NEW — QA 19's orbit statistics were measured on portrait frames resized to 1920x1080 by `qa_r13_probe.rgb` — owner QA.** Any future orbit measure must
   read natively (`qa_r22_probe._rgb_native`).
6. **Carried from QA 21:** the dotted crown rim at stations 2 and 5 (VIEWER); station 2's crown box overshooting its reference coverage (BAKE/VIEWER);
   azimuth-frame popping still untested; blue-violet shaded stone on cam02 (Phase 5 lighting, deferred to the user); cam03's missing deep shade;
   cam06's water moiré; the reflection cooler than Cycles; hero now 35.5 fps at 1440p against the 45 target; the user's Safari hero screenshot and iPhone
   walk recording. **Cleared this round:** the `env_shrubs.glb` walk-in set drawn at every station, `resident()` omitting the impostor atlases, mobile leaf scale.
