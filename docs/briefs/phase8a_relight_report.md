# Phase 8a — the shrub/reed card directional relight: what was built and what it measures

Branch `phase8a-viewer`. Option B of `docs/briefs/phase8a_rescope_analysis.md` (decisions.md "8a
decision 2"). Viewer only: `web/src/foliage.js` (+ its test and the README section) — no bake, no
export, no MB, no frozen material, no deploy. Every number is same-session on this Mac (bake queue
idle, no Blender alive), headless Chrome through `scripts/chrome_run.sh`, local `web/dist` against
the MAIN checkout's `export/out/gate5`, 1920x1080, stations 1, 2, 3, 5, 6.

## What ships

`?cardsun=amt[,share[,wrap[,shade[,mean[,chroma[,cap[,two]]]]]]]`, **`0` / `off` = today byte for
byte** (the program is not patched at all), default = the adopted **`0.6, 0.8, 0.35, 0.9, 0.38, 1,
3, 1`**. Maths, switch table and derivation: `web/README.md` "Phase 8a". The term *redistributes*
the flat per-placement irradiance around its own scene mean, so at `g = 1` it returns the baked
value exactly in every channel. `two = 1` (|N·L|) is what makes the level stable between stations:
the one-sided cosine took the backlit station-2 shore to 0.85x on its own.

## The eight QA-17 boxes, cardsun 0 -> adopted (against the Phase 5 Cycles reference)

| box | leaf/ref 0 -> adopted (ref) | hard% 0 -> adopted (ref) | level (fn) /cardsun 0 | leaf hue 0 -> adopted (ref) |
|---|---|---|---|---|
| 01 shore shrub/reed | 0.86 -> 0.85 | 3.70 -> 3.82 (1.77) | 1.003 | 54.4 -> 54.4 (63.0) |
| 01 shore shrub S | 0.82 -> 0.82 | 6.06 -> 5.93 (3.38) | 1.005 | 57.5 -> 57.5 (58.9) |
| 02 shrub/reed shore | 0.64 -> 0.64 | 9.44 -> 9.64 (3.44) | **0.972** | 71.6 -> **75.7** (90.3) |
| 02 reed clump SE | 0.85 -> 0.85 | 1.73 -> 1.81 (1.57) | 1.008 | 53.5 -> 53.5 (63.7) |
| 05 shrub/reed shore | 0.31 -> 0.31 | 4.29 -> **4.27** (4.30) | 1.012 | 55.3 -> 55.3 (61.1) |
| 05 shrub/reed W | 1.13 -> 1.13 | 8.00 -> 7.90 (4.06) | 1.002 | 58.8 -> 58.8 (58.3) |
| 03 shrub cards | 0.54 -> 0.52 | 4.85 -> 4.99 (1.48) | 1.005 | 67.2 -> 66.2 (70.9) |
| 06 shore planting | 1.76 -> 1.76 | 0.52 -> 0.53 (0.20) | 1.000 | 50.1 -> 50.1 (52.1) |

* **Level (constraint): held** — worst box 0.972x of cardsun 0, budget 3 %; `amt` and `mean` were set
  BY it (the same shape at `amt = 1` reads 0.952x at station 2).
* **Hard edge (constraint): no box crosses the reference that was not already across it.** Seven of
  eight are above it at cardsun 0 (a standing QA-16 item); the eighth, 05 shore, stays at 4.27 %
  against 4.30 %. Movement vs cardsun 0: -0.13 to +0.20 pp.
* **Leaf-green share (reported, not gated): unchanged**, +-0.02x. Hue moves toward the reference only
  at station 2 (+4.1 deg of an 18.7 deg gap) and slightly away at station 3 (-1.0).
* Sweep for the record (station-2 level, its leaf hue): `1,0.8,0.35,0.9,0.38,1,3,1` 0.952 / 77.9;
  `1,0.8,0.05,0.9,0.30,1,3,1` 0.943 / 79.1; `1,0.8,0.05,0.9,0.45,1,3,1` 0.888 / 90.1 (the
  reference's hue, at three times the level budget); the one-sided cosine 0.854.

## The tiles (100 %, `renders/web/tiles/p8a/`, contact sheet `renders/web/960/p8a_tiles.jpg`)

Cycles / cardsun 0 / adopted, stations 1, 3, 5. **The relight does what it says and it is not what
the shore band needs.** Station 1: the three panels are hard to tell apart at 100 %. Stations 3 and
5: the relit cards do read as lit-and-shaded rather than one flat gold, but the dominant defect in
both is the one QA 19 found on the far trees — **the shrub cards' leaf texture is magnified**, single
"leaves" of 20-40 px with black gaps, where the reference has a dense small-leaved bush. No shading
term fixes a texture drawn four times too large. **Recommendation: route the shrub/reed cards to the
8e export fix (the per-card UV scale `k`) — same defect, same class of asset.**

## Performance and the mobile tier

1440p at the hero, three paired same-session runs: cardsun 0 median frame 27.5 / 29.3 / 29.9 ms,
adopted 29.4 / 28.4 / 28.9 ms; GPU cost median 3.1-3.3 ms in both — inside the run-to-run noise (the
adopted build is the faster of the pair in two of three), well inside the +1 ms budget; resident
bytes and draws identical (1 814.2 MB, 317). Mobile tier at station 1 (`manifest_mobile.json`,
`tier=mobile`): loads and draws, no shader-patch error, 312 draws.

## Correction (r4 review 1-2, 2026-09-19)

The r2-6 carry commit (`f099e0c`) left backticks inside `impostors.js`'s GLSL template literal: the
module stopped parsing, `npm test` could not start and `vite build` exited 1 for four commits. Two
consequences, both corrected here and nowhere else in this report: (a) the "npm test green" lines in
those four commit messages were false — the suite is green again at this fix, 510 PASS / 0 FAIL over
12 suites, and `node --check` now runs over every changed module; (b) every capture taken after that
edit was served the PREVIOUS bundle, so the r2-6 pixel and frame-cost numbers are **retracted** — the
band change is unverified on the GPU and needs one A/B capture plus one paired 1440p run. **Nothing
in the sections above is affected**: every 8a relight capture, box table, tile and perf number was
taken before that edit, from bundles that built.

## Evidence

`renders/web/p8a_{cs0,adopt}_cam0N.png`, the sweep `p8a_{cs05,cs1,two1,twostrong,v30,v45,half,soft,
a6,b7}_cam0N.png`, `p8a_boxes.txt|json`, `960/p8a_hero_pair.jpg`, `960/p8a_tiles.jpg`,
`p8a_perf*_perf.json`, `renders/logs/p8a_*.log`. New probes: `scripts/p8a_relight_boxes.py`,
`web/tools/p8a_tiles.py`.
