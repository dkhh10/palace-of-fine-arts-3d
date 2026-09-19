# QA round 21 — Phase 8 item **8b, the band atlas** on the live URL, 2026-09-19

Verdict: **8b CLOSED.** The station-2 crown has limbs and sky, the QA-20 ordered dot grid is gone from every crown body (the hero is clean at 200 %), the willow
highlight does not exist on the delivered frames, nothing regresses, and every rule holds. **One new, smaller residual is carried, not blocking:** a dotted
*rim* one pixel deep survives on the far crowns at stations 2 and 5 at 100 %, and the share lever cannot fix it (§2c) — owner VIEWER.

Capture `gate9` on the staging URL (deploy 9, main 7300fa4): desktop stations 1-6 at 1920x1080, `gate9_net.json`, 1440p `gate9_perf.json`, `?tier=mobile`
stations 1-6, `gate9m_net.json`; no orbit. Before = `gate8` / `gate8m` (round 20). Measures: `scripts/qa_r21_probe.py` (extending r20 -> r19 -> r18b -> r18 -> r17 ->
r16 -> r13 unchanged) and `export/p8_atlas_probe.py viewer` as-is (`viewer` mode, so the bake report's crown-top/trunk label swap applies to no number here).
Tiles: `scripts/qa_r21_tiles.py` — 36 station tiles at 100 %, 10 crown strips (Cycles | gate8 | gate9) at 100 %, 5 at 200-600 %, 4 willow strips. No Blender, no
Chrome; the URL read with `curl` only. Composite `renders/web/gate9_gate.png`.

## 1. Crowns — the point of the round

Crossings per 100 screen px (`p8_atlas_probe viewer gate8 gate9`), gate8 -> **gate9** (Cycles): cam01 7.99 -> **11.97** (11.73), cam02 6.97 -> **7.35** (7.76),
cam05 8.53 -> **11.67** (15.89). The hero now sits **on** its reference (+2 %); station 2 lands 5 % under it; station 5 closes 43 % of its gap. These are the
viewer's own A/B numbers reproduced on the delivered frames, so the band shipped what it measured.

QA-17 crown boxes, gate8 -> **gate9** (Cycles reference): hero leaf % 24.1 -> **23.4** (22.2), centre/edge 0.566 -> **0.581** (0.852), p10 33.6 -> **34.9** (36.8),
hard-edge share 3.16 -> **4.73 %** (4.94) — every one toward the reference, the hard-edge share now within 0.2 pt of Cycles after two rounds at 3.2 %. cam02 c/e
0.434 -> **0.432** (0.364), level 1.09 -> **1.11x**, leaf % 31.2 -> **34.6** (17.4): station 2's crown keeps overshooting its box's coverage and level, as the
viewer's sweep predicted for share 0.10. cam05 c/e 0.910 -> **0.926** (0.960), hard % 4.80 -> **7.47** (6.30) — now 1.2 pt **above** the reference.

**The tiles.** Sheet row A (`crown3_02_fill_crown`, 100 %): gate8's station-2 crown is the familiar soft mass with a halftone over it; **gate9 shows needle
clumps, limb structure and sky between the branch masses** — the contract's acceptance, met plainly. Hero at 200 % (row B): leaf clumps against the balustrade
instead of a blob. Station 1's roof-line crowns at 300 % (`z3_01_roofline`): gate8 is a dense ordered dot grid over the whole crown, **gate9 is clean** — solid
clumps, crisp edges, closest of the three captures to Cycles' silhouette. The hero-shore willow at 200 % (`willow_01_willow_shore_W_200`) gains a trunk and
limbs. **No band-frame seam, no double image, no vertical cut and no mirrored half in any of the ten crown boxes**; popping between azimuth frames cannot be
judged from stills — no orbit was captured (owner VIEWER, one orbit capture settles it).

## 2. The QA-20 ordered dot grid

**a. Measured.** `qa_r21_probe grid`: the lattice index is the excess autocorrelation of the high-pass residual at the multiples of its own period (2/3/4) over
the other lags, x100 — Cycles is the negative control, gate8 (share 0.15) the positive one. Ten crown boxes, gate8 -> **gate9** (Cycles): mean **2.22 -> -5.37**
(-10.39); boxes more than 5 above their own Cycles control **8/10 -> 3/10**. The worst: 01 far roofline 10.08 -> **-9.35** (-11.21, *at* the control), 02 right
cypress 10.26 -> **-3.44** (-10.61), 02 fill tree 20.24 -> **7.81** (-9.64), 05 left crown 1.23 -> **2.56** (-11.04).

**b. Seen.** At 100 % and at 300 % the grid is **gone from every crown body**, including all four hero shore crowns and both roof-line crowns QA 20 named. What
remains, at stations 2 and 5 only, is a **dotted rim** on the silhouette against the sky — `gate9_cam02_r1c3` (the right cypress) and `sky_05_left_crown`. At
600 % (`z6_05_left`) it is an ordered period-2 checkerboard one to two pixels deep along the edge; at 100 % it reads as a soft speckled fringe, not as the
halftone that covered the crown in gate8.

**c. Why the share cannot fix it.** The viewer's own sweep (web/README.md "Phase 8b — the real atlas") records stations 1 and 5 as **byte-identical across
share 0 / 0.10 / 0.15 / 0.25 / 0.40** at 341 px frames: the coverage share never engages there, so no share value changes station 5's rim. The rim is the
alpha-test edge where a band texel is sub-pixel, a different mechanism from the halftone the share paints. Carried as a residual with owner VIEWER, named so the
next round does not re-spend the share lever on it.

## 3. Willows — no re-bake needed

`qa_r21_probe willow`, five hero-shore willow bodies (`env_trees.py`'s own recorded screen fractions) plus the cam05 shore band, gate8 -> **gate9** (Cycles):
p99 182.4 -> **182.6** (180.8) / 200.3 -> **200.5** (203.2) / 207.4 -> **206.8** (205.4) / 197.8 -> **198.5** (201.9) / 196.3 -> **196.9** (197.7); p99.9 and max
**unchanged to 0.1** in four of five; pixels over 235 and over 245: **0.000 % in every willow box in both captures and in Cycles**; flat near-white patches
0.000 %. 49-69 % of the pixels in those boxes changed, so they are band-drawn — the tail simply did not move. Whole-frame check (`qa_r21_probe clip`): **0 new
pixels over lum 240 at all six stations** (and 0 lost); station 2's 0.0384 % over 240 is the pale backdrop building, identical in both captures. The 1.62 % of
clipped willow texels do not reach the delivered frames: **`PFA_BAND_RANGE=band` is not needed** (the review's finding 1 — read `e.range` — still stands as
insurance if anyone re-bakes).

## 4. Regression, rules, mobile

* **Frames.** g9/g8 luma 1.0039 / 0.9999 / 1.0010 / **1.0000** / 1.0062 / 1.0008x. MAE against Cycles: 24.45 -> **24.33** (01) and 20.56 -> **20.16** (05) both
  improve; 18.34 -> 18.61 (02), 34.47 -> 34.53 (03), 18.01 -> 18.14 (06) rise slightly; station 4 is bit-identical. 11-16 % of pixels change at five stations —
  the far-tree band.
* **Boxes.** 3 of 25 move over 3 %, all foliage or foliage-driven: water reflection 1.033x (it mirrors the changed crowns), 01 near tree band 1.031x, 05
  shrub/reed W 1.031x. **0 of 11 architecture boxes move** (max 0.992x, the capital row = the trees behind it). **Shrub boxes restated:** leaf % mean 0.84 ->
  0.86x of the reference, hard % up 0.2-2.7 pt at six boxes — the band draws crowns *inside* those boxes; **no shrub asset changed on the wire** (asset diff:
  16 band atlases in, the 16 2K albedo atlases out, the JS bundle; nothing else). 8a is unchanged and still not closed.
* **Payload.** Desktop **46 877 329 B / 320 requests** before the first frame (+4 508 vs gate8), mobile **46 807 348 B** (+6 314) — both inside the 50 000 000
  rule. The export's 49 393 776 / 47 629 409 are the *planned* tier-0 figures in the manifest; the wire says 46.88 / 46.81 MB. The band costs **8.4 MB at tier 1**
  and *saves* 0.9 MB, because the 2K albedo atlases it replaces are no longer fetched. One 404 (favicon) as before; 0 page errors; totals 587.2 / 66.1 MB.
* **Perf, 1440p medians.** 32.5 / 33.5 / **38.0** / 24.8 / 30.3 / 36.1 ms; vs gate8 **-0.3 / -4.2 / -4.0 / -1.4 / -3.4 / -0.5**, vs the idle `gate5cold`
  +1.7 / -3.7 / **+0.1** / +0.5 / -2.9 / +1.8. Every station is inside the +3 ms rule on both baselines and **station 3's QA-20 flag clears** (+3.1 -> +0.1 vs
  cold) — with the drift caveat, which cuts both ways. Draws, programs and triangles are **identical to gate8 at every station**, so the walk-in shrub-set bug
  (env_shrubs.glb drawn in full at every station, +1.12 M tris) is still in this deploy exactly as QA 20 measured it; the viewer fix round runs in parallel and
  this round does not re-fail on it.
* **Memory.** Sidecar resident **1 862.9 MB**, byte-identical to gate8 (a 4096x1024 atlas and a 2048x2048 one are the same 4 M texels). Corrected **estimate**,
  per the brief: 1 862.9 + 67 (band) + 48 (2K octahedral) = **~1 978 MB** — an estimate, not a measurement, and on the wire this deploy no longer loads the 2K
  albedo atlases, so the 48 MB term stands for the octahedral atlases kept for the normal/depth and tier-0 path. Mobile **563.5 MB**, unchanged.
* **Mobile.** The export's claim is verified: `gate9m` is **byte-identical to gate8m at all six stations** (MAE 0.00000, max |d| 0, 0.0000 % of pixels differ),
  same draws, same triangles, 0 page errors — tier 0 is untouched by the band, as the contract requires.
* **Name sweep.** `qa_r21_probe names`: 738 desktop manifest rows + 341 mobile, **0 object-shaped hits**; 0 mobile paths absent from the desktop plan.

## 5. Scores

Desktop (rubric rows as QA 17): **01 3.89 · 02 3.31 · 03 2.75 · 04 2.88 · 05 3.12 · 06 2.95** — deltas vs QA 20 **+0.11 / +0.06 / 0 / 0 / +0.06 / +0.06**.
**01** Material realism 4 -> 4.5 (the crossings land on Cycles, the hard-edge share within 0.2 pt, and the dot grid that cancelled round 20's two real gains is
gone) and Scale cues 3.5 -> 4 (the roof-line crowns now read as limbs at depth). **02** Material realism 3.5 -> 4 for the crown the band was bought for, held to
one step by the box overshoot (leaf % 34.6 against 17.4) and the surviving rim. **05** and **06** Material realism +0.5 each: real branch structure at 100 %,
station 5 still carrying the rim and its crown hard-edge share now above the reference. **03** and **04** unchanged (2.6 % and 0 % of pixels changed).
Mobile **3.2 · 3.3 · 2.4 · 2.7 · 2.8 · 2.5**, deltas **0 / 0 / 0 / 0 / 0 / 0** — the frames are byte-identical, so the scores must be.

## 6. Residuals for `docs/delivery.md`, with owners

1. **NEW — a dotted rim survives on the far-crown silhouettes at stations 2 and 5 at 100 % — owner VIEWER.** Period-2, one to two pixels deep, the alpha-test
   edge where a band texel is sub-pixel; the coverage share cannot reach it (§2c). Much smaller than the QA-20 defect it replaces.
2. **Azimuth-frame popping is untested — owner VIEWER.** Stills cannot show it and no orbit was captured this round; one orbit capture settles it.
3. **Station 2's crown box overshoots its reference coverage and level** (leaf % 34.6 vs 17.4, level 1.11x) — owner BAKE/VIEWER, the cost of share 0.10.
4. **Carried unchanged from QA 20:** 8a not closed (05 shore 0.29x, 03 cards 0.54x, 02 shore 0.65x — card shape, not count); the `env_shrubs.glb` walk-in set
   drawn at every station (+1.12 M tris, viewer fix in flight); `resident()` omitting the impostor atlases; blue-violet shaded stone on desktop cam02 (strong at
   100 % on `gate9_cam02_r1c2`); flat backdrop city blocks and colonnade backdrop walls; cam03's missing deep shade (1.62x); cam06's water moiré; the reflection
   cooler than Cycles; mobile leaf scale; hero 30.8 fps at 1440p against 45; owed by the user — the Safari hero screenshot and the iPhone walk recording.
   (The violet far-tree crowns at station 6 are **not** a defect of the band: Cycles' own crowns are violet there, and gate9 is closer to it than gate8 was.)
