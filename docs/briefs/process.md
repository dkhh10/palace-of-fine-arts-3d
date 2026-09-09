# Process rules for every builder / fix agent (2026-09-09 wave onward). Read before your brief.

- You work ONLY in your worktree `.claude/worktrees/<branch>` on branch `<branch>`. First command: `git merge main`
  (fast, brings scripts/blender_run.sh, CLAUDE.md, the QA round-05 report). Reference photos: read them from the MAIN
  checkout's absolute path `/Users/dk/Projects/3d render blender 3rd attempt building/reference/` (not in worktrees).
- Every Blender run goes through `scripts/blender_run.sh <max_seconds> -- --background --python scripts/<x>.py -- <args>`.
  It blocks until Blender exits and registers the pid with the watchdog, which kills only pids past their max duration.
  Pick the max honestly (Eevee preview pass 600, Cycles 1080p hero at 64-128 spp 1200, probe bake 1800). Never poll a
  log in repeated turns; one blocking command per run. Never start a second Blender while yours is running.
- Do not wait for another agent's render. The GPU is shared; keep samples low (Eevee previews 32 TAA, Cycles measurement
  renders <= 128 spp at 1920x1080 or 64 spp at 1280x720). One full-scene render at a time per agent.
- Measure on the rebuilt master, not on your asset file alone: `scripts/lead_build.sh` in your worktree (build_master then
  the probe bake), as in the previous round. Claims in your report must be numbers measured on that master.
- Commit after every script that runs successfully, or every 15 minutes. Commit only your own files (assets/<yours>.blend,
  scripts/<prefix>_*.py, docs/<prefix>_notes.md, renders/previews/<agent>/*, renders/qa_comparisons/<prefix>_*).
  Delete intermediate previews before committing (keep the sheet + the panels it references).
- Images: before viewing any render, downscale to 960 px wide JPEG (`sips -Z 960 in.png --out out.jpg`). View composites,
  not single crops. Read long files with grep + offset/limit (no file over 300 lines in full).
- Never edit another owner's file. Hand-offs go into your report as "hand-off to <owner>: <measured number>".
- Final report < 30 lines: what changed (files), each brief item with the measured number before / after / reference,
  the composite sheet path, open items and hand-offs, last commit id. No adjectives without a number.
- If you hit a usage limit or an unrecoverable error: commit what you have, write a checkpoint section in your notes, stop.
