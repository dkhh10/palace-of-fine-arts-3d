# Ornament round 7 (no render) — brief from the lead (2026-09-09). Branch `ornament`. Read docs/briefs/process.md first.
Slot-filler while lighting holds the GPU. `git merge main` first (main has your r6 + the lead's gate fix). Carries from docs/reviews/orn_r6_review.md:
1. Capital re-lay (finding 2): the 3.0 m capital is the 2.6 m design stretched in Z only. Re-lay the Corinthian proportions for H 3.0 against the
   reference (sheet / ref 169 / ref 085 crops): two acanthus tiers at their photographed heights (lower ~0.30 H, upper ~0.30 H), caulicoli and
   volutes in the top ~0.35 H, abacus ~0.10 H; leaf width / projection re-derived from H, not held at the 2.6 m values. Tris inside the tier
   budget; stats gate exit 0.
2. Attic panels (finding 5): scale the figure X positions with PANEL_K so the composition is not crowded 17 % laterally; keep Y depth and the
   socket origin; notes corrected.
3. Findings 3 (RES_X / SENSOR from qa_cameras), 10 (26 mm overshoot: clamp after displace + weld; stale 0.90 comment). Finding 4 (normal map
   baked before the squash) and the AO bakes: only if `pgrep -fl "MacOS/Blender"` shows no other Blender; otherwise leave `--bake-pending`.
Deliverables: assets/ornament.blend (committed once), scripts, notes "Round 7", report < 15 lines with the capital proportion table before / after / ref,
the gate log, the last commit id. No renders, no master write.
