# Phase 8a — the shrub-card directional relight, viewer-only (brief from the lead, 2026-09-19). Opus 5 high. Fresh agent. Branch `phase8a-viewer` from main
(after the phase8b-viewer fix round is merged), worktree .claude/worktrees/phase8a-viewer. Owns web/src/foliage.js (+ tests, README section). Nothing else.
Read: CLAUDE.md (Phase 6 machine rules; Chrome only via scripts/chrome_run.sh, never beside Blender or the bake queue), docs/decisions.md "8a decision 2 (re-scope)",
docs/briefs/phase8a_rescope_analysis.md (§2 the term decomposition: what the viewer does to the card irradiance today, the fitted correction; §4 option B; §5),
scripts/p8a_rescope_{boxes,terms,sim}.py (the box probe you re-run on your captures), docs/qa_round_17.md §3 (the eight shrub boxes, reference values), web/README.md
"Phase 8b fix round" (the fix round's changes to foliage.js you build on), the manifest's sun block (vector, colour) and the instance irradiance join.
Build option B: split the flat per-placement card irradiance into a sun term (cosine on the card normal, a clump/self shadow term so the inner and lee cards go to the
sky term, sun vector and colour from the manifest, the same exposure/LUT path as everything else) and a sky term, under `?cardsun=<0..1>` (0 = today's look byte-identical;
default = the value you adopt). The level must hold (QA 17's closed shrub item: level at the boxes within 3 % of today) and the hard-edge share must not rise above the
reference at any of the eight boxes — measure both; the leaf-green share is reported, not gated. Method: same-session captures at stations 1, 2, 3, 5 through
web/tools/screenshot.mjs at cardsun 0 / 0.5 / adopted; the eight boxes with scripts/p8a_rescope_boxes.py (leaf/ref, hard-edge, level, hue) against the reference and the
Cycles renders; 100 % tiles of the shore band at 1, 3, 5: Cycles | today | relit (the shrubs must read as lit-and-shaded bushes with gold rims, not darker cut-outs); the
hero at 960 px for the lead; 1440p perf same-session at the hero (inside +1 ms); mobile tier drawn once at station 1 to confirm nothing breaks. Tests green.
Rules: check `pgrep -fl "MacOS/Blender|headless"` is empty and export/out/bake_queue/status.json says idle before every Chrome run; never deploy; never touch export/.
Commit after each step with the attribution lines. Write web/README.md "Phase 8a relight" (the maths, the switch, before/after tables, the composite path) and
docs/briefs/phase8a_relight_report.md (< 60 lines). Report < 15 lines: the adopted value, the eight boxes before/after vs reference, hard-edge and level per box,
the tile finding, perf, commit ids.
Carries from docs/reviews/phase8_viewer_r3_review.md (after the relight is measured, each its own commit, none may change a pixel of the relit frames unless stated):
review r3 items 3 (eager path: albedo and translucency can take different wraps — one sampler rule for both), 4 (cull radius/centre recorded but unused: test the
sphere, not the origin), 5 (the main.js "must match" comment vs the post chain's quads), 6 (commit the item-c CIELAB script); r2 carry 6 (the band samples `c2` at weight 0 —
drop the four wasted taps; measure the frame cost same-session, it is allowed to be faster) and 5b (`rows` > 4 silently truncated: warn). Report which you did.
