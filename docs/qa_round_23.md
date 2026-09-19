# QA round 23 — Phase 8 closing round: 8d belt r2 + the far-tree irradiance re-bake, on the live URL, 2026-09-19

**Verdict: 8d CLOSED · far-tree irradiance re-bake — BRIGHTNESS REGRESSION CONFIRMED, blocker, owner EXPORT · 8a closed with its residual ·
8e closed, walk-up delivered · fix round VERIFIED with a new cost (cam03 +1.30 M tris, +3.5 ms).**
The QA-22 blocker is gone: at 100 % the belt is tree crowns with sky-gapped silhouettes and trunks at cam01, cam02, cam03 and cam05 and in the
lagoon reflection, every band moves toward the Phase 8 Cycles reference, and no shard survives anywhere. What replaces it is the re-bake: the far
trees are 0-3 % brighter (harmless) but the boxes backed by the belt and three of six mobile-orbit crowns are 4-16 % brighter, which moves 7 of 10
far-crown boxes away from the Cycles reference and un-does 8e's measured blade gain.

Capture `gate11` on the live URL (deploy 11, main 2c0398a): desktop 1-6 at 1920x1080, `gate11_net.json`, 1440p `gate11_perf.json`, `?tier=mobile`
1-6, `gate11m_net.json`, the mobile close orbit (80 m, h 5 m, headings 253 / 215) and the 2.5 m walk-up on belt tree #19 (`gate11_walkup_*`).
Before = `gate10` / `gate10m` (round 22). Measures `scripts/qa_r23_probe.py` (extending r22 -> r21 -> … -> r13 unchanged), tiles
`scripts/qa_r23_tiles.py`, crossings `export/p8_atlas_probe.py viewer`. No Blender, no Chrome; the URL read with `curl` only.
Sheet `renders/web/gate11_gate.png`.

**The two reference sets.** Phase 5 Cycles stays the record for the ARCHITECTURE boxes; the Phase 8 Cycles set
(`renders/qa_comparisons/cycles_p8/`, 1080p / 32 spp from the Phase 8 master) is parity at every BACKDROP / BELT box. **Only the 960 px JPEG
copies of the Phase 8 set survive** — the full-resolution PNGs are gitignored and the `phase8d-env` worktree is gone — so every Phase 8 number
below is computed at 960x540 on both sides with the boxes halved; `hf` / `sd` from those rows are labelled `@960` and the 1920 px viewer-only rows
carry the continuity with rounds 17-22.
**Ref-set agreement** (`qa_r23_probe refcheck`): the eight architecture boxes give MAE 0.82-3.26 % between the two sets with luma ratios
0.993-1.009x. The brief's "< 1 %" is unreachable — the ENV builder's own seed-0/seed-1 control of the *same* scene floors at 1.24-3.61 % — so the
sets **agree on level within 0.9 %** and the measured MAE sits inside that floor. Accepted.
**Water mask** unchanged from round 22: cam01 keeps y < 680, cam05 y < 910, cam06 y < 540; cam02 / 03 / 04 have no water in frame.

## 1. 8d — the hall-east belt r2 — CLOSED

**The tiles are the acceptance, and they pass.** `/tmp/r23_belt_*` and `/tmp/r23_hero_r2c1|r2c3`, all at 100 %: at cam02 (the QA-22 "row of
spikes" tile) gate10's hard-edged two-tone faceted polygons are replaced by tree crowns with irregular sky-gapped silhouettes, visible trunks and
leaf texture, sitting where the Phase 8 Cycles row puts its dark mass. Same at the hero's north and south colonnade bands, at cam05, and at cam03
(gate10's pale shard in the top-left intercolumniation is gone). **No shard, no hedge of identical silhouettes, no floating crown, no gap under a
crown, and every top is below the hall roofline.** The lagoon reflection carries the belt as broken dark streaks instead of gate10's pale spikes.
**Parity moves the right way at every band** (`qa_r23_probe belt`, MAE vs the Phase 8 Cycles reference, 960 px, noise floor 1-4 %):
hero N band **11.24 -> 9.62 %**, hero S **13.73 -> 12.27 %**, cam02 belt **10.80 -> 10.16 %**, cam05 belt **11.46 -> 10.84 %**; luma falls toward
Cycles at all four (0.350 -> 0.332 vs 0.274; 0.333 -> 0.321 vs 0.264) and saturation rises toward it (0.580 -> 0.614 vs 0.672).
**The QA-22 residual 2 reverses at the hero.** On the exact QA-22 boxes at 1920 px: hero N band **luma sd 0.153 -> 0.165** and **hf 0.1306 ->
0.1440**; hero S **sd 0.190 -> 0.203**, **hf 0.1234 -> 0.1624**. Last round both moved the wrong way; both now move toward ref 169 (0.200 / 0.2027
and 0.258 / 0.234), though both still fall short of it.
**No seam and no tiling** (`qa_r23_probe seam`): the lattice index is -7.8 to -10.4 at all seven boxes, at or below its own Cycles control.
**cam06 is untouched, as designed** (R1 only, no belt in frame): top row luma 0.444 -> 0.444, saturation 0.329 -> 0.328. **QA-22 residual 2 stands
for cam06** — R1 still delivers ~5 % of its luma target and ~15 % of its saturation target against ref 105's 0.834 / 0.071. Far lawn not washed out
(0.493 -> 0.494, ref-side of Cycles' 0.474).
**What the belt does not do:** it covers less of the pale backdrop than the icospheres did and than Cycles does. At cam02 the dark-foliage share in
the crossing box falls **69.85 -> 56.91 %** (Cycles 69.51) and the bright-background share rises 20.56 -> 25.81 %; at cam05 the background share
rises 75.62 -> 79.59 % at a flat background level. That is a residual, not the blocker — the tiles show trees.

## 2. The far-tree irradiance re-bake — BRIGHTNESS REGRESSION, blocker, owner EXPORT

Required by decisions.md "Belt export chain r2 merged" (the re-bake moved the 127 existing rows, full-mode modulation median 0.942 -> 1.390).
**On the far trees themselves it is harmless.** The seven QA-21 sky-crown boxes that contain only crown and sky move **+0.0 to +3.0 % (median
+1.1 %)**, and two of them move *toward* the Phase 8 Cycles reference. A +48 % modulation median buys ~1 % of screen luma.
**Everywhere the crown is read against something, it is not.** `qa_r23_probe fartree`: 8 of 10 boxes brighten and **7 of 10 move away from the
Phase 8 Cycles reference** — mean |viewer/cycles - 1| rises **6.7 % -> 9.7 %**. The three worst are the QA-17 *control* crowns
(`02 fill tree` 1.074 -> **1.246x** Cycles, `05 lawn tree crown` 1.143 -> **1.191x**, `01 hero shore crown` 1.075 -> **1.101x**), and their dark
share falls with it (02 fill tree 75.21 -> **67.81 %**, Cycles 75.34; 05 lawn crown 16.12 -> **12.86 %**, Cycles 34.76).
**It costs 8e its margin.** `qa_r23_probe orbit`, the six mobile close-orbit crown boxes, gate10_orbit -> gate11_orbit: run-width p90
24/21/23/27/21/20 -> **27/26/29/28/21/20 px**, mean **22.7 -> 25.2 px**, **boxes at or under the 25 px target 5/6 -> 2/6**. The three boxes that
rose are exactly the three whose mean luma rose (66.0 -> 70.2, 57.0 -> 62.6, 65.3 -> 71.8, i.e. **+6.4 to +10.0 %**); the three that held moved
+0.6 to +0.8 %. **The tile (`/tmp/r23_orbit_h02530.png`) shows the same leaves in the same places, only brighter** — so this is not a geometric
fattening, it is the brightness rise widening a brightness-thresholded run. Coverage 1.004-1.247x, no thinning.
**Also visible in 8a's carried numbers:** hard-edge share now rises at three shrub boxes by more than the 0.3-point allowance and *away* from the
reference (01 shore shrub S 2.78 -> **6.31 %**, ref 3.38; 05 shrub/reed W 5.73 -> **7.23 %**, ref 4.06), where QA 22's three movers all moved down.
Leaf-green share (REPORT) mean **0.86x -> 0.92x** of the reference — the same brightening read as a gain.
**Verdict: a brightness regression, blocker, owner EXPORT**, per the rule the lead set at the merge. The fix decisions.md already names is a re-key
to the 6c bodies. Scope note for the lead: it is confined to the far-tree modulation term, the hero moves only +2.4 % at one box, and the
frame-level parity still *improves* at five of six stations — so it is a blocker by the stated rule, not by hero-visible damage.

## 3. 8a and 8e — closed

**8a** is closed with the cam03 residual the 8a-4 decision logged (lighting carry, owner VIEWER/LIGHTING). Regression only this round: box level
within 3 % at 7/8 (05 shrub/reed shore 1.08 -> 1.11x ref, +2.7 %); leaf share reported above; hue unchanged (< 0.6° everywhere). The hard-edge rise
is charged to §2, not to 8a.
**8e** closes with the owed frame delivered. `gate11_walkup.json`: **0 page errors**, two probes at 2.5 m on belt tree #19 (h 0° and 90°),
1170x2532. The close cards read as painted foliage, not stretched slabs: run p90 **37.8-71.0 px**, which is what a 10-20 cm leaf cluster subtends at
2.5 m in that raster — **no fattening**. At that distance the cards are flat cut-outs, which is a card limitation and not an 8e defect; no QA
station stands there. The QA-19 mobile leaf-blade finding stays closed on the tiles; the numeric margin is the §2 casualty.

## 4. The viewer fix round — VERIFIED, with a new cost

Triangles per station, gate10 -> gate11: five stations fall by **13 644** (the icospheres leaving), cam04 by 6 744 — and **cam03 rises
6 044 248 -> 7 346 118 (+1 301 870)** with draws 343 -> 371. That is 39 belt trees × ~33.4 k, i.e. the far-tree path drawing the belt as LOD2
meshes rather than billboards at cam03's range. **cam03's 1440p median goes 35.1 -> 38.6 ms (+3.5 ms, 25.9 fps — now the slowest station)** and
cam04 24.2 -> 26.2 ms; the other four are within ±1.2 ms and all six stay below the idle `gate5cold` baseline except 03 / 04. Hero **28.2 ms /
35.5 fps, unchanged**, against the 45 fps target. Mobile carries the same cost (cam03 4.92 -> 5.22 M tris, draws 380 -> 424).
**Resident, the figure of record: 1 814.2 MB desktop** (gate10 1 814.8; textures 1 255.6 and render targets 443.8 unchanged, geometry 115.2 ->
114.5) and **550.3 MB mobile** (551.0). Both now match the branch's own 1 814.2 / 547.9 within 2.4 MB.

## 5. Regression, rules, mobile

* **Frames, above the waterline.** g11/g10 luma 0.9970 / 1.0047 / 0.9984 / **1.0000** / 1.0028 / 0.9996x; station 4 is bit-identical; MAE
  0.96-2.91 levels. **Parity improves at five of six stations** against the Phase 8 Cycles set (-0.75 / -0.03 / -0.29 / 0.00 / -0.26 / -0.22) and at
  five of six against the Phase 5 set (only cam02 +0.64). QA 22's "8d moves the viewer away from the frozen look" reverses.
* **Boxes.** 5 of 25 move more than 3 %, and **0 of the 9 true architecture boxes** do (max 2.3 %, the capital row; seven are bit-identical). The
  five movers are the two intercolumniation "wall" boxes (S 0.811x, **toward** ref 139.29; N 1.128x, **away** — the pale backdrop through the belt's
  gaps), the non-reproducible water reflection (1.061x, no claim), and the two belt-backed crowns of §2.
* **Far crowns.** Crossings per 100 px, gate10 -> gate11 (Phase 5 Cycles): cam01 11.80 -> **11.64** (11.73, inside 0.3 of QA 21's 11.97 and now
  within 0.09 of Cycles); cam02 7.34 -> **9.10** (7.76) — outside 0.3, an *overshoot* from the belt's real silhouettes; cam05 10.80 -> **9.37**
  (15.89, QA 21 11.67) — it did **not** return within 0.3, and the decomposition explains it as the belt backing the brief allows: the box's
  foliage share falls 8.69 -> 7.41 % while its background *share* rises 75.62 -> 79.59 % at a flat background level, i.e. more background is visible
  past the crown, the crown itself did not brighten. Logged, owner ENV.
* **The QA-21 dotted rim improves but stands.** Mean lattice index -5.61 -> **-6.03**; worst box `02 fill tree` **6.71 -> 2.57** (the shards were
  feeding it); still **3/10 boxes above their Cycles control**. Residual 1 of round 21 stands, owner VIEWER.
* **Payload.** Desktop **46 761 417 B / 318 req** before the first frame (**-121 262** vs gate10), mobile **46 824 683 B / 376 req** (+14 554) —
  both inside the 50 000 000 rule. Totals 586.9 / 67.1 MB. One 404 (favicon) as before; **0 page errors** in all four captures.
* **Mobile.** Station 4 byte-identical; 1 / 2 / 3 / 5 / 6 differ over 6.0 / 9.3 / 8.4 / 7.8 / 14.2 % of pixels, MAE 0.50-3.50 levels, cam03 the
  largest (the belt enters its frame). Nothing moved outside the belt, the shore cards and the backdrop.
* **Name sweep.** 738 desktop manifest rows + 341 mobile, **0 object-shaped hits**; 0 mobile paths absent from the desktop plan.

## 6. Scores

Rubric as QA 17 (six rows, station = their mean, so one row moving 0.5 moves a station 0.083).
Desktop: **01 3.97 · 02 3.22 · 03 2.83 · 04 2.88 · 05 3.20 · 06 3.03** — deltas vs QA 22 **+0.16 / +0.08 / +0.08 / 0 / +0.08 / 0**, vs QA 21
**+0.08 / -0.09 / +0.08 / 0 / +0.08 / +0.08**.
**01** background realism +1.0 (the belt is trees in three of six hero tiles and in the reflection) and +0.5 for beating QA 21's flat wall, against
-0.5 foliage material (far crowns now 1.03-1.10x Cycles). **02** +1.0 background restored, -0.5 for the belt's gappier cover (dark share 12.6
points under Cycles) and its 1.22x luma. **03** +0.5 background: gate10's shard in the top-left intercolumniation is gone; everything else at cam03
is unchanged and its deep-shade carry stands. **04** bit-identical. **05** +0.5 background (shards gone), no foliage change. **06** unchanged — the
belt is not in frame and R1's colour residual is exactly where QA 22 left it.
Mobile: **01 3.32 · 02 3.30 · 03 2.52 · 04 2.70 · 05 2.96 · 06 2.58** — deltas vs QA 22 **+0.12 / +0.08 / +0.08 / 0 / +0.08 / 0**. Mobile takes the
same belt gains and a -0.25 foliage-material charge at the hero for §2's brightness rise on the orbit crowns.

## 7. Residuals for `docs/delivery.md`, with owners

1. **NEW, BLOCKER — the far-tree irradiance re-bake brightens every crown read against a background by 4-16 %, moves 7 of 10 far-crown boxes away
   from the Phase 8 Cycles reference (mean deviation 6.7 % -> 9.7 %) and drops 8e's blade metric from 5/6 to 2/6 boxes under target — owner
   EXPORT.** Fix as decisions.md names it: re-key to the 6c bodies. Not hero-visible damage; a blocker by the rule the lead set at the merge.
2. **NEW — the belt covers less of the pale backdrop than the icospheres and than Cycles: cam02's dark-foliage share is 12.6 points under Cycles,
   cam05's crossings 6.5 under, the hero's N-colonnade wall box 1.128x its reference — owner ENV.** Density or a second row, not a re-shape.
3. **NEW — the belt draws as LOD2 meshes at cam03: +1 301 870 triangles, +28 draws, +3.5 ms (25.9 fps, the slowest station) — owner EXPORT/VIEWER.**
   The far-tree mesh/billboard switch distance does not account for the hall's east face.
4. **Carried from QA 22:** 8d R1's cam06 colour move (~5 % of the luma target, ~15 % of the saturation target) — ENV; the 8a cam03 bush-interior
   darkness as a lighting carry (8a-4 decision) — VIEWER/LIGHTING; the orbit-measurement fix (`qa_r22_probe._rgb_native`) — QA, applied here.
   **Cleared this round:** the faceted belt (QA 22 residual 1), the hero band's sd/hf moving the wrong way (part of residual 2), the missing 2.5 m
   walk-up (residual 4).
5. **Carried from QA 21:** the dotted crown rim at stations 2 and 5 (VIEWER, improved); station 2's crown box overshooting its reference coverage
   (BAKE/VIEWER); azimuth-frame popping still untested; blue-violet shaded stone on cam02 (Phase 5 lighting, deferred to the user); cam03's missing
   deep shade; cam06's water moiré; the reflection cooler than Cycles; hero 35.5 fps at 1440p against the 45 target; the user's Safari hero
   screenshot and iPhone walk recording.
