# Phase 9 viewer shade r2 — the specular gate's sunlit end (brief from the lead, 2026-09-21). Opus 5 high. Fresh agent.
Branch `phase9-viewer-shade2` from main (5a2fcd1 or later), worktree .claude/worktrees/phase9-viewer-shade2. Read docs/briefs/process.md, then
docs/decisions.md entry "2026-09-21 · Phase 9: the round-19 lighting ships ... cam03 specular gate gets a second round" (the decision and the acceptance),
docs/briefs/phase9_viewer_capture_report.md (set B: the measured per-station MAE and p10 table; set A), docs/briefs/phase9_viewer_shade.md and its
review docs/reviews/phase9_viewer_shade_r1_review.md (carries), web/src/materials.js (the gate as shipped), web/test/spec_gate_test.mjs, export/manifest_v4.py
(the two constants and their derivation), docs/briefs/phase9_bake_analysis_report.md B.6.
**CPU only: no Chrome, no Blender** (the re-bake chain owns the GPU for hours; the lead grants the capture window between the bake queue and the pack).
Do NOT write into MAIN's export/out: mirror it into the worktree per file as the capture agent did, and run manifest_v4 / tiers --no-pack there.

## The two defects (decisions.md) and the fix
1. skyVis normalises the lightmap's blue by the open-sky irradiance/π of an UPWARD-facing surface (11.256). A vertical wall sees at most half the sky, an east
   wall under this sky less: fully unoccluded walls read skyVis 0.14-0.5 and lose most of their IBL specular, which Cycles keeps. Fix: manifest_v4 projects the
   shipped sky_diffuse EXR to SH9 (RGB, irradiance/π convention, the same quadrature check as the constants) and writes `sky.diffuse_sh9`; the shader evaluates
   the unoccluded irradiance/π for the world normal, E0(n), and uses skyVis = clamp(lm.b / max(E0(n).b, ε), 0, 1). Check the SH convention against three.js'
   LightProbe / SH3 evaluation so the same normal gives the same number (unit test: the SH evaluated at +Z must equal 11.256 within 1 %; at the sun's
   azimuth/elevation the sunlit east wall's E0(n) must make the B.6 sunlit band's blue 1.604 read as a plausible visibility, state the value).
2. sunVis = (lm.r − 0.195·lm.b)/21.428 ≈ dotNL on a sunlit surface, and it multiplies reflectedLight.directSpecular which already carries dotNL (three.js
   RE_Direct: irradiance = dotNL * color). Fix: sunVis = clamp((lm.r − k·lm.b)/(21.428·max(dotNL, 0.05)), 0, 1) with dotNL from the geometry normal and the
   sun direction (available in the light loop / as a uniform from the manifest sun az/el); clamp so grazing faces do not amplify.
Keep ?specgate=0 = the Phase 8 shaders character-for-character (the existing test), and keep the pre-round gate reachable as ?specgate=1 for the A/B if cheap
(else document). Extend spec_gate_test.mjs: the B.6 decile table for the shade end unchanged (skyVis/sunVis at the deep-shade bands within 0.001 of today),
plus the sunlit-band checks above. Materials without a lightmap untouched.

## Chain (CPU, in the worktree mirror): manifest_v4 -> tiers.py --no-pack (+ --mobile) -> verify_glb --gate5 -> tiers_test -> name_sweep -> npm run build.
Report the manifest byte cost of the SH block. No deploy.

## Report (< 20 lines): the SH9 coefficients' derivation and unit checks; the gate math as shipped; predicted cam03 near_column and the sunlit-station effect
from the numbers you can compute offline (the lightmap decile table, E0(n) for the hero attic's normal); npm test count in every commit message; last commit id;
the exact capture commands for the window (stations 1-6 gate ON -> renders/web/p9s2_cam0N.png, cam03 specgate=0 control; MAE vs gate12 and vs p9s_).
