# Phase 9 viewer — station 3's shade: gate the specular path by the lightmap's sky and sun visibility (brief from the lead, 2026-09-20). Opus 5 high.
Fresh agent. Branch `phase9-viewer-shade` from main (after the phase9-viewer and phase9-export merges), worktree .claude/worktrees/phase9-viewer-shade.
Owns web/src, web/tools, web/README.md, renders/web/p9_cam03_*, renders/web/p9s_*; PLUS, by the lead's exception, the two manifest constants in
export/manifest_v4.py and their schema test (one commit, nothing else in export/). Read docs/briefs/process.md, then docs/briefs/phase9_bake_analysis_report.md
Part B in full (B.0-B.7) and docs/decisions.md "session 10: station 3's viewer shade excess" — the decision is made; you build it.

## Why (measured, B.1-B.6)
cam03's column shade is 2.55x Cycles (viewer p10 38-40 vs Cycles 7.3). The lightmap is right (0.997x). The excess is the viewer's specular path: the
environment PMREM specular applied without occlusion (carries all the viewer's blue) and the sun DirectionalLight's specular applied unshadowed (the warm
remainder). The post chain is ~0 on the near column.

## Item 0 — the export hand-off that gates the belt-rule ship (added 2026-09-20 after the export report; ships in the SAME deploy as the rule)
docs/briefs/phase9_export_report.md item 3 and export/README.md "THE ONE HAND-OFF THAT GATES THE SHIP": web/src/foliageLazy.js builds its
impostor complement from the MESH placements, so a billboard-only belt row (35 on desktop, 17 on mobile) never gets `iIrr` and would draw ~4x too
bright (median E_placement/E_bake 0.2424). Fix: set `irr` for a row with no mesh placement, leave `near` at 0; `trees.far_mesh.lighting.mesh.placements`
carries every far tree with a `mesh` flag and `trees.<set>.billboard_only` names the excluded rows. The contract test is web/test/foliage_lazy_test.mjs
section 4c (it prints the hand-off). Its own commit, first.

## Viewer carries from docs/reviews/phase9_viewer_r2_review.md (2 and 3), if cheap: p9v_rim.py boxes_for's aspect claim; the ?tier=mobile owed
measure is a whole-frame MAE against gate12m (the rim guard refuses 1170x2532 by design). Otherwise leave them tabled.

## Build
1. **Manifest constants** (export/manifest_v4.py, its own commit): `sky.open_irradiance_over_pi = [R,G,B]` = the upper-hemisphere cosine-weighted mean
   radiance of the shipped sky_diffuse EXR (B.6 measured (2.196, 3.432, 11.256) on the current one — that is your test fixture, not a constant), and
   `sun.irradiance_over_pi` = the sun's direct irradiance / π at dotNL = 1 read from the scene/bake audit (67.32/π = 21.428 today). Both re-derive on
   every manifest run, so the lighting re-bake feeds new values with no viewer change. Extend the manifest schema test; tiers.py must carry them through.
2. **Viewer** (web/src/materials.js, inside the existing lights_fragment_maps patch that already deletes the env diffuse):
   `skyVis = clamp(lightMapIrradiance.b / openSky.b, 0, 1)` scales the IBL specular `radiance`; `sunVis = clamp((lightMapIrradiance.r − (openSky.r/openSky.b)·
   lightMapIrradiance.b) / sunIrrOverPi, 0, 1)` scales `reflectedLight.directSpecular`. Uniforms from the manifest; a `?specgate=0` switch restores the
   Phase 8 path bit-identically (prove it with the existing frame test pattern); document in README. Mind the lightmap decode (the KTX2/EXR encoding and any
   exposure factor the material applies BEFORE the irradiance is in linear W/m²/sr·π units — B.2 states what the shipped texel range is; the gate must read
   the same units the constants are in, or it is wrong at both ends). Unit-test the gate on the B.6 decile table: deep shade -> sunVis ≈ 0.002, skyVis ≈ 0.008;
   sunlit band -> sunVis ≈ 0.75. Materials without a lightmap (impostors, water, backdrop, foliage) are untouched.
3. Chain: manifest_v4 -> tiers.py x3 -> verify_glb --gate5 -> tiers_test -> qa_name_sweep -> build. No bake, no KTX2, no deploy (the lead deploys with the
   re-bake chain).

## Captures (only in the Chrome windows the lead grants; Chrome never beside Blender or the bake queue; scripts/chrome_run.sh + web/tools/screenshot.mjs)
Window 1 (before your build, on the merged main viewer): station 3 at 1920x1080 with `?post=none`, `?probe=0`, `?lighting=direct`, and the `post=all`
control -> renders/web/p9_cam03_{postnone,probe0,direct,all}.png; run `export/p9_shade_terms.py --boxes --cycles renders/qa_comparisons/cycles_p8/cam03_1080_32spp.png`
on them and report whether B.3/B.4's split holds to the channel. Window 2 (after the build): all six stations at the gate12 settings ->
renders/web/p9s_cam0N.png; report per station MAE vs the gate12 frames (hero parity first: stations 1, 2, 4, 5, 6 must move <= 0.5 % MAE outside shade;
station 3 near_column and p10 luma before / after / Cycles). 960 px copies committed, tiles gitignored.

## Do NOT
Touch assets/, scripts/, export/ beyond item 1, the lightmap bake, the LUT, the exposure/look, or deploy. No Blender.

## Report (< 20 lines): the constants as computed; the gate math as shipped; the unit-test numbers; the cam03 flag-capture split; per-station MAE table;
`npm test` count in every commit message; last commit id; what the capture windows still owe if one was not granted.
