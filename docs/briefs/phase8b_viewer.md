# 8b viewer brief — impostor alpha as coverage (Opus high, fresh agent). Branch `phase8-viewer` (worktree .claude/worktrees/phase8-viewer, from main today).
Read first: docs/briefs/phase8b_bake_analysis.md (the diagnosis with numbers: crossings per 100 screen px Cycles 7.76 vs 2.40 at 1K / 3.28 at 2K; 93-100 % of covered
crown-top texels semi-transparent; ALPHA_TEST 0.33 + a saturated a2c ramp paint them solid), docs/decisions.md "8b decision", web/src/impostors.js and the Phase 7
premultiplied 12-tap + a2c path (`?impedge=`), web/README.md "Phase 7" and "src/foliage.js", CLAUDE.md Phase 6 machine rules (Chrome only through scripts/chrome_run.sh
and NEVER while a Blender process is alive: the ENV builder runs Blender on this machine now — do the code first, capture when `pgrep -fl MacOS/Blender` is empty, never
kill it, never set PFA_DEV_SHARE_GPU).
Deliverable A: under magnification (atlas texel > 1 screen px) the card's alpha is treated as COVERAGE, not a cut: alpha-to-coverage fed by the atlas alpha directly
(the ramp must not saturate: scale the ramp width by the magnification, or bypass the fwidth ramp and pass a directly to gl_FragCoverage-equivalent via a2c), with
an ordered-dither fallback when MSAA is off; `?impcov=` (default on, 0 restores Phase 7). No change to lighting or to the premultiplied colour reconstruction. Measure at
station 2 and the hero with export/p8_atlas_probe.py's crossings metric (extend it to read a viewer capture; per 100 screen px, target toward Cycles' 7.76 from 2.40 at
1K; report the number for 1K and, once the export lands the 2K keys in MAIN, for 2K), the QA-17 crown boxes (level, centre/edge must hold), and 100 % tile pairs of the
station-2 crown (before / after / Cycles). Deliverable B: when MAIN export/out/gate5/manifest.json carries the 2K atlas keys (the lead tells you), confirm the viewer
picks them at tier 1 and the 1K stand-in at tier 0 (boot log), and re-measure. Commit after every working step; build + suites pass; README "Phase 8b" section; no deploy.
Report < 15 lines: crossings before/after at 1K (and 2K if available), the box numbers, tile paths, commit id.
