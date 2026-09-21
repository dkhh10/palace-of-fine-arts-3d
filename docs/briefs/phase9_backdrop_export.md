# Phase 9 backdrop export + viewer — carry the ENV gain tiles into the walkthrough (brief from the lead, 2026-09-21). Opus 5 high. Fresh agent.
Branch `phase9-backdrop-export` from main (after the phase9-env merge and the lead's master rebuild), worktree .claude/worktrees/phase9-backdrop-export.
Owns export/ (the backdrop class only: gate1 export of kind=="backdrop", the four KTX2, manifest rows, tiers) and web/src (the backdrop material only),
web/test, web/README.md "Phase 9" section, docs/briefs/phase9_backdrop_export_report.md. Read docs/briefs/process.md, then docs/briefs/phase9_env_report.md
section "Export hand-off" IN FULL (the node table, per-group constants, the UV0 layout in tile units, the constant-amp variant), docs/reviews/phase9_env_r1_review.md,
export/README.md "Phase 9" (the chain the lead runs; the backdrop class in the Gate 1/2 set), docs/briefs/phase9_rebake_report.md section 3 (the pack chain as
last run: the manifests now carry sky.diffuse_lobes etc. — do not lose them; run manifest_v4 last, after gate3_relay_check, per the README order).

## UV index change (ENV review r1 fix 2, cross-owner; yours to land)
The ENV round inserted UV0 "UVMap" at index 0 on the 1 291 backdrop meshes, so in env.glb the BAKED backdrop atlas (albedo/lightmap UV, formerly TEXCOORD_0)
now lands at TEXCOORD_1 and the tile UV at TEXCOORD_0. The viewer's backdrop material currently indexes the atlas at set 0: change it (or pin the sets by
name in the manifest and read them by role), with a test that fails if the two sets are swapped. State both indices in the report.

## What ships
The four gain PNGs (assets/textures/backdrop/*.png, mean 0.505, tileable) as REPEAT-sampled, Non-Color KTX2 on TEXCOORD_0 (UV0 is pre-divided into tile
units — NO texture transform), multiplied over the baked backdrop albedo/lightmap in the viewer exactly as Cycles does:
`albedo *= 1 + (tex − 0.5)·2·strength·(1 − (1 − keep)·haze)` after the atmosphere term, per-group strength/keep from the ENV report. Desktop and mobile
(mobile: halved textures per the tier rule). Gate 1 re-export of the backdrop class only (kind=="backdrop"; gate1_set.py:804 keeps them out of the UV1
groups): verify UV0 survives at TEXCOORD_0 and Gate 2's smart_uv1 lands UV1 at index 1 (the ENV hand-off's explicit check), arch/orn/ground/env-trees glbs
byte-identical (sha256 before/after), the backdrop lightmaps NOT re-baked (the bake is lighting-only; the tiles are albedo — say so in the report).
Blender: the Gate 1 export is a CPU Blender run through scripts/blender_run.sh; `pgrep -fl "MacOS/Blender"` must be empty first — the lead's 4K hero render may
hold the GPU when you start: if a Blender is running, do everything CPU-only first (tiles -> KTX2, viewer material, tests) and wait for the export with ONE
blocking `until` loop (max 60 min) before the Blender step. No Chrome (the lead grants the capture window); no deploy.

## Acceptance (report numbers): cam06 city band hf in the viewer before/after at the QA-22 boxes (env_p9_probe.py's metric) — expect the Eevee +12-25 %
order; cam01/cam05 backdrop bands within the ENV report's named regression (-1..3 % hf, +0.01-0.018 sat), nothing else moves > 0.5 % MAE; payload cost of
the four KTX2 per tier (first frame must stay <= 49.5 MB desktop); verify_glb --gate5 both tiers, tiers_test, name_sweep, npm test counts in every commit;
`npm run build` clean. Chain: stop after the build (tiers, verify, name_sweep, npm run build); the lead captures, deploys 14 and runs QA 26.
## Report (< 20 lines): the KTX2 sizes; the shader as shipped; the UV index check; sha256 table; the hf table; payload; last commit id; capture commands.
