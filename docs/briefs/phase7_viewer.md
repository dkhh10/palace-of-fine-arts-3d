# Phase 7 viewer brief — foliage look, desktop far trees + mobile near trees (Opus high, fresh agent). Branch `phase7-viewer` (worktree .claude/worktrees/phase7-viewer, from main today).
Read first: CLAUDE.md "Phase 6" machine rules (Chrome only through scripts/chrome_run.sh; never while a Blender process is alive; low frame counts), docs/decisions.md from
"2026-09-19 · PHASE 7 APPROVED" (the scope) and the 6c entries from "2026-09-17 · QA 16" to "6c CLOSED WITH RESIDUALS" (what the foliage terms are and why),
docs/qa_round_17.md §3, §4 and §7 (the crown/shrub boxes, their reference values, the residual list with the one-line fixes), web/README.md "src/foliage.js" and
"Phase 6b" sections (every switch and its default; the tier table in web/src/device.js), web/src/foliage.js, web/src/impostors.js, scripts/qa_r17_probe.py (the boxes
you re-measure with), docs/perf_ab_6c.md (how a same-session A/B is reported). The user's two screenshots that opened this phase: renders/web/user/phase7_desktop_hero_user.png
and renders/web/user/phase7_iphone_close_user.png (view at 960 px). `npm install` in web/ first (fresh worktree); set PFA_MAIN_ROOT to the MAIN checkout; assets come from
MAIN export/out (read-only for you).
## Deliverables (commit after every working step; `npm run build` + the 9 suites pass at every commit; no deploy — the lead deploys)
A. **Impostor edge.** The far-tree impostor cards show a jagged, dithered alpha silhouette and a pale halo at the hero and station 2. Fix on the atlas sampling side
   (premultiplied alpha in the shader, a negative mip bias or explicit LOD on the atlas, alphaToCoverage or a softer alpha test at the card edge), not by moving lighting.
   Measure with the QA-17 crown boxes (hard-edge share, the halo share) before/after at stations 1, 2, 5 at 1920x1080 through screenshot.mjs (gate4 settings,
   `?manifest=/assets/gate5/manifest.json&tiers=all`), and show a 100 % tile pair of one crown at station 2.
B. **Crown darkening floor.** Clamp the stacked `impint` + `crownint` + sun-path darkening: no crown pixel population below a floor you derive from the Cycles reference
   (QA 17: hero crown p10 must return from 0.57x of the reference toward >= 0.8x; station 5's frame luma back to 1.00 +- 0.01; no near-black blotches at 100 %). Keep the
   interior/rim read QA 17 credited (cam02 centre/edge ~0.39 vs ref 0.364).
C. **Mesh switch distance A/B, same session, 1440p gate4 settings, 120 frames, warmup 24, on the DESKTOP tier:** current defaults (treemesh 40 / fartreemesh 12) vs
   treemesh 60 / fartreemesh 30 vs treemesh 80 / fartreemesh 60, stations 1-6 back to back with a repeat of the default last (drift control, as docs/perf_ab_6c.md).
   Adopt the largest setting whose hero median stays within +3.0 ms of the same-session default and resident within +100 MB; report draws/tris per setting. Update the
   defaults in code only for the adopted setting; the others stay reachable by query.
D. **Mobile tier** (web/src/device.js TIER_SETTINGS.mobile): near-tree meshes within ~25 m (`treeMesh`), the walk-up set within ~10 m (`walkupMesh`), LOD1 shrubs
   inside that radius (`shrubLod`), impostor darkening eased (impint strength ~halved on mobile, or the B floor raised there). Measure at 1170x2532 `?tier=mobile`:
   draws, tris, resident (must stay < 700 MB; report the delta from 499.7 MB), the Mac frame time as a proxy only; capture a close orbit like the user's screenshot
   (`window.__pfaOrbit` around the rotunda at ~30 m, height ~5 m, two headings) before/after, and the six stations after.
E. **Docs and report.** web/README.md "Phase 7" section (what changed, the A/B table, the mobile numbers, the before/after captures: `renders/web/960/p7_*.jpg`, full-res
   under renders/web/ untracked). Report < 25 lines to the lead: per item the numbers before/after, the adopted C setting, the mobile resident, capture paths, commit id.
Rules: no Blender; no edits to export/, assets/, master*.blend or anything under export/out; do not change the tier-0 payload (a texture you add to tier 0 breaks the
50 MB definition of done — if A needs a different atlas encode, say so and stop); commit every 15 minutes; code review before merge (the lead dispatches it).
