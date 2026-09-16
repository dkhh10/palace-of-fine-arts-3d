# Phase 6 Gate 4 — per-placement irradiance for the shrub/reed cards (lead, 2026-09-16 session 4). Branch `phase6-bake`, worktree `.claude/worktrees/phase6-bake` at 67f4e90. Opus xhigh. Fresh agent.
Start: `git merge main` in the worktree (main carries the decision). Read first: `git log -1 --format=%B 67f4e90` (the stop report: what was found, why per-mesh was refused),
docs/decisions.md entries "2026-09-16 · Probe re-measured on the real cube" and "2026-09-16 · Shrub/reed irradiance is baked PER PLACEMENT" (the decision you execute),
export/gate3_env_cards.py (yours; the 28-mesh / 1 379-placement table in export/out/gate3/env_cards.json), export/bake_lm.py vertex kind (the 14 near trees: the precedent),
export/README.md manifest v4 section, CLAUDE.md "Phase 6" machine rules. Never save master*.blend; the bake source is export/out/gate1/gate1_bake.blend + the final rig as Gate 3.
Task: one scene-linear RGB per PLACEMENT (1 379) = the mesh's vertex-averaged Cycles DIFFUSE direct+indirect irradiance (colour off, same settings as the trees' vertex bake) at
that placement's world transform. Shared mesh data must be made single-user per placement inside the bake process only (nothing saved). Batch the placements so each Blender run
is short (many short jobs, `scripts/blender_run.sh <honest seconds>`); run through export/bake_queue.sh so export/out/bake_queue/status.json says `running` while the GPU is
yours — the viewer engineer's Chrome reads that file and pauses on it. Estimated 3-5 GPU minutes total.
Output: export/out/gate3/instance_irradiance.json {mesh_name: {placements: [{object: <source object name>, rgb: [r,g,b]}...] in the export's placement order (the order
export_set/compose write env.glb's instance matrices — state which order you used and how the export can reproduce it: object name is the key), range_global, encoding
"linear-float32" (no quantisation: 16.5 kB), summary min/max/mean per mesh}. Then extend export/README.md manifest v4 with the `lightmaps.instance_irradiance` block spec exactly
as the decision states it (the export engineer implements it in manifest_v4.py; do NOT edit manifest.json). Sanity checks in the report: a shaded colonnade placement vs a sunlit
lawn placement (expected ratio from the lightmap of the ground under each), one placement beside a near tree vs that tree's COLOR_0 mean, and the count 1 379 = env_cards.json.
Sync to MAIN with export/sync_main.sh (no --delete). Commit after every script that runs. Report < 20 lines: jobs and seconds, the per-mesh range table's extremes, the three
sanity checks, the placement-order statement, files synced, last commit id.
