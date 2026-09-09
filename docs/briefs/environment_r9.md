# Environment round 9 (no render) — brief from the lead (2026-09-09). Branch `environment`. Read docs/briefs/process.md first.
Slot-filler: nothing renders (ARCH r6 holds the GPU for cam01 crops). `git merge main` first (main has your r8 + the lead's paving rebuild).
1. Lighting's flythrough check (docs/status.md "LIGHT r14 prep reported", docs/lighting_notes.md §23): ENV_shrub_pitto1_1107 overhangs the colonnade
   walk at theta -50.8 (about (63.5, -5.9)), 1.45 m from the gallery centreline, the only ENV object inside the 2.80 m clear width. Move it out
   of the gallery (or drop it) by a rule in env_build / env_trees (planting must keep >= 1.5 m from the colonnade centreline over the whole
   walk), rebuild, and prove with a no-render probe (walk centreline sampled every 2 m, nearest ENV object distance >= 1.5 m).
2. Carries from docs/reviews/env_r8_review.md 3, 5, 6, 7 and docs/reviews/env_r7_review.md 5, 7, 10: shadow_relief must not relocate
   hand-placed (pinned) trees (log moved 0 for pinned in BOTH relief passes), stale frame-x comments, y-window hint, the two cam03 std
   figures, the A-group share. Rebuild and check the r8 numbers that need no render (band clearer moved 0 / dropped 0, LOD1 tris, tree count).
3. cam06 far-shore std gate: environment's crop tool and lighting's read different statistics on the same crop (env 44.0 / 23.5 vs lighting
   59.8 / 33.8). Agree one definition in env_r7_measure (document the box, the luminance formula, composited vs not) and restate the gate as
   a ratio composited / un-composited (lighting ships 0.64); record it in the notes for QA.
Deliverables: assets/environment.blend, env scripts, notes "Round 9", commits after every successful script, report < 15 lines with the walk
clearance table summary and the last commit id. No renders, no master write.
