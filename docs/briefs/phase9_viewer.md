# Phase 9 viewer — the dotted rim on far-crown silhouettes at stations 2 and 5, plus the review carries (brief from the lead, 2026-09-20). Opus 5 high.
Fresh agent. Branch `phase9-viewer`, worktree .claude/worktrees/phase9-viewer (merge main first). Owns web/src, web/tools, web/README.md, renders/web/p9v_*.
Read docs/briefs/process.md first. **No Chrome and no Blender until the lead grants a GPU window** (the lead's Cycles references, then the lighting round,
hold the GPU; Chrome never runs beside Blender or the bake queue — export/gpu_lock.sh check must say idle AND the lead must have said go). Build and unit-test
first; capture last.

## Item 1 — the dotted rim (QA 21 item 1, carried through QA 24 "back at its gate10 level")
docs/qa_round_21.md §2c and item 1 (line ~93): a period-2, one-to-two-pixel dotted rim on the far-crown silhouette against the sky at stations 2 and 5 at
100 % (tiles gate9_cam02_r1c3 the right cypress, sky_05_left_crown); the coverage-share lever does not engage there. The far crowns at those stations are
octahedral impostors (web/src/impostors.js; export/README.md "Far trees: the Gate 3 octahedral impostors", "Phase 8b" band atlas) — read how alpha is tested
(alpha-to-coverage / cutoff / premultiplied band branch, mip selection, the `cols-1` guard carry) and find the mechanism of a period-2 rim by reasoning and by
unit test on the shader math or by an offline re-implementation over the atlas texels (export/out/gate3/... KTX2/PNG sources; export/read_alpha.py). Candidate
causes to rule in or out with numbers: alpha-test against a mip whose alpha is dithered; MSAA alpha-to-coverage on a 2x2 sample pattern; the frame-blend
between two octahedral views with different silhouettes; the band-branch premultiplied edge. Fix in the shader / material; keep every other station bit-identical
(the QA regression rule: MAE <= 0.5 % at stations 1, 3, 4, 6; use scripts/qa_r21_tiles.py / qa_r21_probe.py measures for the rim: count of rim pixels along the
silhouette, period-2 share).
## Item 2 — carries from docs/reviews/phase8_viewer_r2_review.md items 3-6 (see phase8_viewer_r3_review.md "Carry" for their current state) and
phase8_viewer_r1_review.md items 4-6 if still open. Each its own small commit.
## Capture (only after the lead's go): scripts/chrome_run.sh with web/tools/screenshot.mjs, stations 2 and 5 (and 1, 3, 4, 6 for the regression MAE) at the
gate12 settings, into renders/web/p9v_cam0N.png; 960 px copies committed, tiles gitignored. Report the rim measure before / after per station.
## Do NOT touch export/, assets/, scripts/ (except adding a p9v probe under scripts/ if the r21 probe cannot be reused), or deploy.
## Report (< 20 lines): the mechanism with its evidence, the fix, rim counts before/after at 2 and 5, regression MAE at the other four, unit tests added,
suite count in every commit message (`npm test` in web/), last commit id. If the capture window has not been granted when the build is done, report without it
and say so; the lead schedules the capture.
