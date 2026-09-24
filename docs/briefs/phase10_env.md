# Phase 10 round 1 — tree mass and the willow to ref 169 (brief from the lead, 2026-09-24)

Opus 5 high. Fresh agent. Branch `phase10-env`, worktree `.claude/worktrees/phase10-env` (already created from main; `git merge main` first anyway).
Read `docs/briefs/process.md`, then `docs/approach_review_2026-09-24.md` §1, `docs/briefs/phase9_env_report.md` (the current state of the belt
and the plan) and the `PLAN` block of `scripts/env_trees.py` (the solvers `env_r9_replan.py --verify` must keep passing).

## Why
On the delivered 4K hero against ref 169 (`reference/photos/raw/ref_169_main_Palace_of_Fine_Arts_16794p.jpg`, MAIN checkout) the foliage
silhouette is the largest compositional difference left: the photo has a dense, dark, layered conifer mass right of the rotunda running from the
rotunda's edge to the north colonnade with its tops near the attic base, and a big drooping willow immediately left of the rotunda reaching the
impost. Ours has the same species at the same plan positions but reads as two or three thin crowns with sky through them and a sparse willow. QA
25/26 carry "crowns wash out" and "foliage material -0.25" at the hero. Materials are NOT yours this round (the projection agent owns
`assets/materials.blend`): this is crown geometry, leaf-card density, crown scale and drape only.

## You own (nothing else)
`assets/environment.blend`, `scripts/env_*.py`, `scripts/env_p10_*.py` (new), `docs/briefs/phase10_env_report.md`, `renders/previews/environment/*`,
`renders/qa_comparisons/env_p10_*`. NOT `assets/materials.blend` (hand off any leaf / bark material need as a measured number in the report),
not lighting, not ARCH, not export/ or web/, not MAIN's master.

## Items
1. **North-east conifer mass** (ref 169, cam01 frame x ~0.58-0.74, tops at y ~0.30-0.33 of 1080p, i.e. near the attic base): make the cluster read as
   one continuous dark mass with layered crowns, not separate trees with sky between. Levers, in order: leaf-card count and card size per crown
   (LOD0 and LOD1 both, keep LOD2 as is), crown radius / height within the plan's height windows, one or two more instances of the existing
   prototypes inside the plan's ring rules (`env_r9_replan` LAND + ring must still verify), never on the rotunda's body or the arch (the plan's
   cam01 spans). Measure with the existing box tools (`scripts/env_p8_boxes.py` or the QA probes): dark-pixel share and sky-through share in the
   box, crown-top row, before / after / ref 169.
2. **The willow left of the rotunda** (ref 169 x ~0.39-0.47, canopy to the impost height, drape to the water): denser drape, wider crown; same
   measures on its box.
3. **Behind the colonnade**: keep the sky-through rule from the plan (15-20 % sky through the bays); report the number, do not chase it.
4. **Budget**: ENV placed triangles per LOD before / after; stay within +15 % at LOD1 and LOD0 (the export tiers depend on it); no new species, no
   new prototypes unless a count change alone cannot do it (then say why with the numbers).

## Renders
Build on CPU first (environment.blend rebuild through `scripts/blender_run.sh`). Rebuild master in your worktree (`scripts/lead_build.sh`) and render
Eevee 1920x1080 previews of cam01, cam02, cam05 (600 s each) before and after — the before set may be the gate14 / cycles_p9 frames already in
`renders/qa_comparisons/` if the boxes are unchanged. ONE Cycles hero 1920x1080 32 spp (<= 900 s) at the end for the sheet. The GPU is shared with
the projection agent (depth renders, bakes, three measurement renders): one full-scene render at a time per agent, never wait for the other, `pgrep
-fl "MacOS/Blender"` before each run; a GUI Blender (pid 5262, the user's) may be open — not yours, leave it.

## Acceptance
Item 1 box: dark share and sky-through within 5 points of ref 169, crown-top row within 12 px; item 2 box: within 8 points; the rotunda silhouette
untouched (the plan's cam01 span rule); `env_r9_replan.py --verify` passes; tri delta within budget; sheet `renders/qa_comparisons/env_p10_sheet.png`
(cam01 100 % crops before / after / ref, cam02 and cam05 full frames at 960). Report < 20 lines: files, each item before / after / ref, tri delta per
LOD, the material hand-off if any, sheet path, last commit id. Commit after every successful script with the attribution line.
