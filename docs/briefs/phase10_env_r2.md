# Phase 10 round 2 — ENV: the hero-shore willow to ref 169's box (brief from the lead, 2026-09-24)

Opus 5 high. Fresh agent. Branch `phase10-env2`, worktree `.claude/worktrees/phase10-env2` (created from main after the phase10-env merge ea12906).
Read `docs/briefs/process.md`, `docs/briefs/phase10_env.md` item 2, `docs/briefs/phase10_env_report.md` (round 1: the willow box FAILED and the report says
it needs a plan move, not density), `docs/reviews/phase10_env_r1_review.md` fix-now 3 and carried items, the `PLAN` block of `scripts/env_trees.py`
(the hero-shore willow is `("willow", 6.9, 43.4, 9.0, "P hero-shore willow, ref 169 x 0.33-0.42 ...")`, ships cam01 x 0.340-0.417).

## Why
Ref 169's willow sits at cam01 x ~0.39-0.47 with its canopy up at the arch impost (frame y ~0.45 at 1080p) and its drape down to the water. Ours is a 9 m
tree at x 0.34-0.42 whose crown never reaches the box `x .39-.47 y .45-.62`. Round 1 densified the drape (kept, decisions.md 2026-09-24) and handed the
leaf colour to materials (running separately on assets/materials.blend, NOT yours). This round moves and scales the willow so its silhouette fills the box.

## You own (nothing else)
`assets/environment.blend`, `scripts/env_*.py` (the PLAN and the solvers), `scripts/env_p10r2_*.py` (new), `docs/briefs/phase10_env_r2_report.md`,
`renders/previews/environment/p10r2_*`, `renders/qa_comparisons/env_p10r2_*`. Never assets/materials.blend, lighting, ARCH, export/, web/, MAIN's master.

## Items
1. **Measure first, colour-independent.** Render cam01 1920x1080 in Eevee with an object-index / Cryptomatte pass (or a flat emission override in a scratch
   scene) so you can count the willow's OWN pixels inside the box, and its crown-top row; do the same estimate on ref 169 by hand-segmenting the willow
   (its leaf share and crown-top row inside the box: state the method). Before numbers for our willow: expect near 0 in the box.
2. **Move / scale the hero-shore willow** within the plan's rules (`env_r9_replan.py --verify` LAND, ring, 3.5 m spacing; `env_p10_plan.py --check`; the
   cam01 rotunda-span rule: the willow may overlap the rotunda's LEFT base and the left column as in the photo, never the arch opening or the drum).
   Levers in order: planted height (the willow height window may be raised for THIS instance only, state the new window and why), position toward
   x 0.39-0.47 (stay on land, the shoreline is at WATER_Z), crown width. No new prototype unless the height needs a new Sapling seed (say so with numbers).
3. **Silhouette rule**: cam01 rotunda arch opening and drum pixels covered by the willow = 0; the left column may be partially covered (ref 169 does).
4. **Budget**: tris per LOD before / after (+15 % rule counts from the ROUND-1 numbers 16,440,294 / 5,741,062 / 849,706).

## Renders
Rebuild environment.blend and master in your worktree (`scripts/lead_build.sh`). Eevee cam01 + cam02 1920x1080 before / after (600 s each), ONE Cycles
cam01 1920x1080 32 spp at the end (900 s). The GPU is shared with the projection agent (bakes, depth renders): `pgrep -fl "MacOS/Blender"` before every run,
a GUI Blender (pid 5262, the user's) may be open, leave it; never wait for another agent, one full-scene render at a time on your side.

## Acceptance
Willow own-pixel share of the box within 10 points of the ref willow's share; crown-top row within 20 px of ref's; item 3 holds; verify/check pass; tri
budget holds. Sheet `renders/qa_comparisons/env_p10r2_sheet.png` (cam01 100 % box crops before / after / ref, cam02 full at 960, the index-pass crop).
Report < 20 lines into docs/briefs/phase10_env_r2_report.md: numbers per item, the plan change (old -> new line), sheet path, last commit id.
Commit after every successful script with the attribution line `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`; never 15 min without a commit.
