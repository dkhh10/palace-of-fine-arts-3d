# Lighting round 13 — brief from the lead (2026-09-09). Branch `lighting`, worktree .claude/worktrees/lighting. Read docs/briefs/process.md first.

Runs AFTER materials r7 merges (never concurrently with materials). `git merge main` first; measure on your rebuilt master with materials r7 in place.
Read: docs/reviews/light_r12_review.md (carries), docs/lighting_notes.md §21.12 (lead's Eevee check), docs/status.md entries "ENV r7 reported" and
"ENV r7 merged" (environment's hand-offs), docs/decisions.md 2026-09-09.
1. Eevee misses the r12 diffuse shade term (shaded attic Eevee 94.9 / 42.2 / 0.769 vs Cycles 116.7 / 35.4 / 0.412; sunlit 155.7 vs 178.0): the world probe
   bake evaluates the light-path split as a camera ray. Give Eevee the shade term (probe-time world override, or an Eevee-only shade fill on the
   EEVEE_VAULT pattern) so the hero's shaded attic in `apply_preview_eevee` is within 6 deg hue / 0.1 sat / 15 % lum of Cycles; sky and lagoon must stay
   identical to Cycles (they are now: 208.2 / 0.52).
2. cam06 (ENV hand-off, QA-05-8): COMP_golden_hour's mist adds +58 lum on the horizon crop and cuts its std 44.0 -> 23.5, flattening the far-shore line
   that environment's geometry now produces un-composited. Pull the mist near limit / density until the crop's std recovers past 35 with the compositor
   on; re-run `scripts/env_r7_measure.py` count_lines (environment's tool, read-only) and report lines composited / un-composited.
3. South wing aligned panel: 94.3 vs >= 103 aligned (raw 0.86 passes). Shore band: 79.6 vs 115.6 after environment's sun samples and materials' r7 albedo;
   report what the sky term can add without moving the hero's sunlit numbers out of their windows (attic lum 178-201, sat >= 0.50, R-B >= 110).
4. Review carries: meta / world provenance for the r12 sockets (sky_diffuse_tint, _antisun, _horizon, sky_diffuse_hue); near-water cell in the sheet;
   SUN_BLUE_MULT sits at 0.00 (blue-free sun on specular glints: check a glint crop, and state whether 0.05-0.10 costs the shade window); the Cycles world
   importance map cannot see the diffuse-only multipliers (measure noise at 128 spp on the shaded attic box vs r11); comments and the index-picked Mix
   sockets in light_build.py:611-613.
Deliverables: as usual (values, assets/lighting.blend, light_r13_sheet.png with before / after / ref and numbers for cam01 Eevee vs Cycles, cam06, wings,
§22 in the notes, commits after every successful script, report < 30 lines).
