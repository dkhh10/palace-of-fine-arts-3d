# Ornament round 8 (no render) — brief from the lead (2026-09-09). Branch `ornament`. Read docs/briefs/process.md first.
`git merge main` first. Carries from docs/reviews/orn_r7_review.md, all without renders or bakes (the lead runs the bakes):
1. `orn_r7_capital_layout.py --verify`: parse ARCH_R6 and the bell_radius / leaf_spine bodies out of orn_build.py (no hand copies), and loop the
   check over every CAPITAL_STYLE. Then fix the presets so v2's volute top stays below the abacus seat and v3's upper tier / r_tip sit inside
   the reference window; rebuild capital_rotunda --no-bake ONLY if a preset changed (say so; the lead re-bakes), gate exit 0.
2. Back-row count off the integer cliff (explicit count or a tolerance); bake_pending exit code; the "abacus" label on gate line 145.
3. Notes: ref_002 column marked as canon + hand reading, with the crop file named so it can be re-measured.
Deliverables: scripts, notes "Round 8", report < 10 lines with the per-style verify table and the last commit id.
