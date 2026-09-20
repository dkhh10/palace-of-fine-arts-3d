# Phase 9 viewer r2 — finish the r1 review fixes (brief from the lead, 2026-09-20). Opus 5 high. Fresh agent.
Branch `phase9-viewer`, worktree .claude/worktrees/phase9-viewer. Owns web/src, web/tools, web/README.md. Read docs/briefs/process.md first.
**CPU only: no Chrome, no Blender** (the lighting round holds the GPU; the lead schedules the rim capture in a later window). `npm test` in web/ is your suite;
put its count in every commit message.

## State you inherit
Commits up to 486518e closed review r1 findings 1 and 5 (docs/reviews/phase9_viewer_r1_review.md). The previous agent left the worktree with UNCOMMITTED
edits to web/README.md and web/tools/p9v_rim.py — `git diff` first: they are partial work on findings 2-4 and 6. Keep what is right, finish what is not,
commit each finding as its own small commit (message names the finding number).

## Do
Findings **2, 3, 4, 6, 7** of docs/reviews/phase9_viewer_r1_review.md, each verified against the file:line the reviewer cites (the lines may have moved).
Finding 6 (p9v_rim.py frame-size assert, BOXES relative to the frame) needs no capture: assert on the shape and derive BOXES from it; test it on the
existing renders/web/gate12_cam02.png / gate12_cam05.png full-size frames if present in MAIN (read-only, absolute path), else on a synthetic frame.
Finding 7 (?impq=0 is not the Phase 8b program): fix the wording in README and impostor_rim_test.mjs, or make it true — say which. Carries 8-14 stay carries
(list them in the README's carry table if it has one; do not build them).

## Do NOT
Touch export/, assets/, scripts/, web/public/assets, or deploy. No capture. Do not merge main unless a conflict blocks a commit (say so).

## Report (< 15 lines) in the final message
Per finding: what changed (file, one line), test added or not; `npm test` count; last commit id; anything from the uncommitted edits you discarded and why.
