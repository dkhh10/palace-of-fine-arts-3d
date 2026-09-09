# Materials round 9b — the projection in linear space (short fix round from the lead, 2026-09-09). Branch `materials`. Read docs/briefs/process.md.
Same branch, same worktree, `git merge main` first. Opus xhigh, but SHORT: budget allows ONE Cycles hero frame (64 spp, 1920x1080) for the
acceptance plus at most one bordered diagnostic; no Eevee pass, no cam04/cam05. Report < 20 lines. Lighting is merged and idle.
Read: docs/reviews/mat_r9_review.md (all four findings are this round), docs/briefs/materials_r9.md items A, B, F, and your Round 9 notes.
1. Finding 3 (the round's real defect): the ratio map is a quotient of two AgX display-space PNGs applied to a scene-linear albedo, so it
   delivers ~1/3 of its correction. Fix inside mat_projection.build: build the ratio in linear space. Either (a) render the flat-white
   reference frame and read the photo through the measured inverse of the SHIPPED view pipeline (AgX + the look light_presets.py:32 ships,
   'AgX - High Contrast': re-run mat_r9_agx.py at that look and use its per-luminance transfer to raise the display ratio to the local
   1/transfer power), or (b) write the reference render as linear EXR and linearise the photo with the same measured transfer. State which,
   and prove it on one number: Photo 0 -> 1 must now move the shaded attic by the amount the map asks (-9.6 %), not a third of it.
2. Findings 1-2: re-measure the AgX transfer at the shipped look, fix the notes' conclusions (Punchy lowers chroma; "unreachable" is not
   shown), and measure the real binding constraint: the shaded attic sat <= 0.50 ceiling as the sunlit box is pushed toward sat 0.53-0.62
   / R-B >= 120. Weight (<= 0.6) is chosen where the sunlit box gets as close as possible with the shaded sat ceiling, the shaded hue
   29.5 +- 6 and the columns mask held.
3. Finding 4: commit phtest.py as scripts/mat_r9_phtest.py; fix the stale comment at mat_build.py:180 with the measured numbers.
4. Lead's call on the mirror: WATER_GLOSS_MIX default 0.25 -> 0.45 in mat_build.py (refl 116 / near water 125 / sat 0.20 per your table).
   Measure it on the same acceptance frame; no sweep.
Acceptance table (one Cycles hero frame on your rebuilt master, object count stated): attic sunlit lum/hue/sat/R-B, attic shaded lum/hue/sat,
columns, entablature, std ratio / aniso both boxes, water_refl, near_water, ripples, flank. Hold list as r9. Commit after every script;
report the table, the Photo 0 -> 1 proof, and the last commit id.
