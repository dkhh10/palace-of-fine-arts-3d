# Code review brief (Opus 5, no Blender, read-only) — one branch per review

Review branch `<branch>` at its head against `main` in the worktree .claude/worktrees/<branch>: `git diff main...HEAD` plus the
owner's report / notes section. Do not run Blender, do not edit files, do not commit. Write findings to
docs/reviews/<branch>_<round>_review.md in the main checkout (the lead commits it), pattern: docs/reviews/light_r11_review.md.
Look for: logic that cannot produce the claimed number (measurement boxes, engine/preset mismatches, stale defaults), idempotency
(rebuild_collection, clear-before-build), Blender 5.2 API names (CLAUDE.md lists the differences), absolute paths that break in a
worktree ($PFA_MAIN_ROOT / common.REFERENCE_DIR), hard-coded copies of shared constants (camera stations from qa_cameras.py, WATER_Z),
name collisions with other owners' objects/materials, tracked binaries > 5 MB that are intermediates, commits touching other
owners' files, and claims in the report with no script that measures them. Verdict on line 1: MERGE / MERGE WITH FIXES / SEND BACK,
then numbered findings with file:line, severity (blocker / fix now / carry), and the one-line fix. Under 40 lines.
