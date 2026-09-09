# Environment round 8 (short) — brief from the lead (2026-09-09). Branch `environment`, worktree .claude/worktrees/environment. Read docs/briefs/process.md first.

One item, before QA round 6. Context: docs/environment_notes.md § "Round 7 review follow-up" (your branch, head f426672), docs/reviews/env_r7_review.md finding 1,
docs/decisions.md 2026-09-09 "Pin rule beats the band clearer". `git merge main` first.
1. The hand-placed A/A2 cluster ("dark mass right of the dome", from ref 169) resolves at x 0.76-0.985 of the hero frame; ref 169's mass is at x 0.71-0.76 (and
   report its y extent). Re-derive the cluster's plan positions from ref 169 through the cam01 camera (qa_cameras.py station; scripts/env_sightlines.py or the
   round-5 fit tools) so the mass lands at 0.71-0.76 with the same height, then rebuild. The pin rule stays: the band clearer must report moved 0 / dropped 0.
   Acceptance on your rebuilt master (state its object count): north band 1360 480 1860 600 lum >= 0.90 of ref 145.9 (was 91.9 after the pin fix, 137.5 before),
   foliage share <= 40 %; south band and cam05 numbers within 2 % of round 7c; cam03 / cam06 unchanged. Composite renders/qa_comparisons/env_r8_sheet.png:
   hero crop before / after / ref 169 with the mass position marked, and the north-band numbers.
Deliverables: assets/environment.blend, env_trees changes, notes section "Round 8", commits after every successful script, report < 20 lines.
