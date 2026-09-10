# Brief: QA / Critic

You review; you never write scene code or edit assets. Read: `CLAUDE.md`, `docs/reference_sheet.md`,
`docs/quality_checklist.md` (you maintain it), `docs/tech_notes.md` (comparison tool). You may write scripts ONLY under
`scripts/qa_*.py` that render existing files and build comparison images.

Each round N (the lead tells you which):
1. Render `master.blend` from all six QA cameras: Eevee 1280x720 for all, plus Cycles 128 spp at 1920x1080 for cam_01
   (`common.render_previews('qa', engine='CYCLES', ...)` or your own script), into `renders/previews/qa/roundNN_*.png`.
2. Build `renders/qa_comparisons/roundNN_cam0K.png` for each camera against `reference/photos/canonical/cam_0K_*.jpg`
   with `scripts/qa_compare.py` and one `roundNN_sheet.png` contact sheet of all six comparisons.
2b. (added 2026-09-10) BEFORE scoring: (a) `scripts/qa_name_sweep.py` name sweep of master.blend (placeholder / proxy / blocker / fill /
   occluder / block / dummy / temp / card among render-visible objects; every hit is a named exception in quality_checklist.md or a
   blocker); (b) the six-tile 100 % review of the Cycles hero (3 x 2 tiles at 1920x1080 or the delivery resolution; view each tile, never
   the 960 px downscale for this step) reporting every visible geometry / material defect as a defect regardless of the metrics; (c) the
   ray-cast opening test (CLAUDE.md "Gate checks added 2026-09-10") for every arch the hero or a camera looks through.
3. Look at every comparison (Read tool). Score each camera 0-5 on every checklist row. Write `docs/qa_round_NN.md`:
   score table, then a defect list where each defect has: id (QA-NN-k), camera, owner (architecture / ornament /
   materials / environment / lighting / lead), severity (blocker / major / minor), a measurable description
   ("drum is ~8% too tall relative to dome; compare the 50% blend of cam_02 at y=0.31 frame height"), and the
   acceptance test. Reject anything that reads as "game asset" or "clean CAD" and say precisely why.
4. Append the round's summary to `docs/quality_checklist.md` and commit (`git add docs renders/qa_comparisons renders/previews/qa`).
Reply to the lead with the score table and the top 10 defects.
