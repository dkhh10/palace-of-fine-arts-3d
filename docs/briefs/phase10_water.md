# Phase 10 round 2 — the lagoon: olive murk and a streaked reflection, to ref 169 (brief from the lead, 2026-09-24; DISPATCH ONLY after phase10-proj merges)

Opus 5 xhigh. Fresh agent. Branch `phase10-water`, worktree `.claude/worktrees/phase10-water` (the lead creates it from main after the projection merge).
Read docs/briefs/process.md, docs/materials_notes.md (every "water" section: rounds 7-9 and 10b carry the sweeps, the hold windows and the priced trade-offs — do not
re-run a sweep whose table is already there), docs/approach_review_2026-09-24.md §1 item 4, and `scripts/mat_build.py` MAT_water_lagoon (the comments are the history).
You own `assets/materials.blend` MAT_water_lagoon only, `scripts/mat_p10w_*.py`, docs/materials_notes.md "Phase 10 r2", renders/previews/materials/*, renders/qa_comparisons/mat_p10w_*.
Lighting is frozen: the sky's glossy term and WATER_GLOSS_MIX's split with lighting stand (decisions.md); you work murk colour / murk depth, ripple spectrum and slope,
distance filtering, Fresnel. Never concurrent with another materials agent.

## What the lead sees on the 4K hero against ref 169 (960 px side by side)
The photo's water is dark olive-brown between reflections, and the building's golden reflection is chopped into short horizontal streaks with dark gaps; ours is a cleaner,
bluer mirror with fine uniform ripple and a saturated blue field. Two measured targets, both on the 1080p hero grid with the round-9 box tools:
1. **Reflection breakup**: on the reflection column box (900 760 1020 840) the row-wise luminance autocorrelation / anisotropy must move toward ref 169's (measure the photo
   first, state the number); the reflection's mean lum and R-B stay inside the round-10b hold (R-B >= +35, lum 124-208), i.e. redistribute, do not dim.
2. **Field colour**: open-water boxes (near water 79-131 lum / hue 185-200 / sat 0.22-0.32 window; report where ref 169's own open-water boxes sit in hue and sat and whether the
   window itself should move toward them — say so as a hand-off to the lead, do not silently retarget). cam05 lagoon sat >= 0.25, cam06 lagoon not black.

## Renders
Rebuild master in the worktree (scripts/lead_build.sh). ONE Cycles hero 1920x1080 64 spp (<= 900 s), ONE cam05 and ONE cam06 at 1280x720 32 spp (<= 600 s each).
At most four water cases in one sweep, priced in a table as round 9 did. Sheet renders/qa_comparisons/mat_p10w_sheet.png: reflection and open-water 100 % crops
before / after / ref 169, cam05 and cam06 at 960. Report < 20 lines with the hold table; commit after every successful script with the attribution line.

## Added 2026-09-24 (lead): foliage colour hand-off from ENV round 1 (docs/briefs/phase10_env_report.md), same agent, same file
Also own `MAT_leaf_*` / the conifer and willow leaf materials in assets/materials.blend (names in scripts/mat_build.py; ENV never edits them). Measured on the
Cycles cam01 after-frame vs ref 169: conifer mass mean RGB (63,57,17) luma 51 vs ref (114,109,84) luma 98; willow leaf (57,57,11) luma 48 vs ref (174,159,85)
luma 155; blue/green 0.19-0.30 vs 0.77. Target: leaf albedo about +1 stop, less saturated, more blue (olive-grey, not yellow-green), translucency kept; land the
conifer box luma within +-15 of ref and B/G within +-0.15, without the crowns washing out at cam05 (QA 25/26 residual). Measure with scripts/env_p10_boxes.py on
the rebuilt master (cam01 Cycles 32 spp is enough for these boxes; it doubles as the water hero if you render at 64 spp once). Add the two foliage rows to the sheet.
