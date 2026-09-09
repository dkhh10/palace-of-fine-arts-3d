# mat r7 review (branch `materials`, head 02b60a8) — Opus 5 code review, 2026-09-09

MERGE WITH FIXES

Verified by re-running the owner's own tools on the committed renders (no Blender): every number in the round-7
acceptance table reproduces exactly — attic 180.3 / sat 0.474 / std ratio 0.74 / aniso 0.40, entablature 0.704 / 37.8,
shaded 30.9 / 0.373, coffer quarter ratio 0.233 (mat_r6_measure), near-water 0.324 / 213.6, ripples -39.1, refl 0.043,
shore 91.7. Anisotropy is defined as the brief asks (colsd/rowsd, mat_r7_measure.py:97). Probe backs the 50 % ORN /
50 % MAT_concrete_ochre @ 84.9 m attic claim (renders/logs/mat_r7_probe.log). Paving names match env_build.py:358-359.
41 materials / 38 appended / 38 placeholders remapped (mat_r7_lib6.log, mat_r7_build6.log); mat_build clears materials
and node groups + rebuild_collection = idempotent; scripts exit cleanly; 5.2 API names fine; grunge fetch still gated
behind `--fetch` (r6 follow-up closed); only materials-owned files touched; 13 commits; no intermediate binary > 5 MB.

1. **fix now** — brief item 4 (ship the sheen at a level meeting refl sat >= 0.25) was not executed. `Sheen Weight`
   is 0.0, unchanged from main (mat_build.py:940); the one sheen case in the sweep (w6, mat_r7_sweep.py:38) was never
   rendered — the logs run ctl,w1-w4,w7-w9 = **8** cases, not the "9-case sweep" of the notes (materials_notes.md:979)
   — and the box regressed 0.260 -> 0.043. Fix: render w6 (+ a 0.15-gain-with-sheen case), or tell the lead the sheen
   is deliberately abandoned so QA-05-4 can be re-scoped rather than silently failed.
2. **fix now** — notes describe a superseded water build. materials_notes.md:1012 says "a 0.55 gain ... ~0.20 at the
   hero / ~0.42 at cam06"; shipped is `WATER_MURK_GAIN` **0.15** (mat_build.py:937), i.e. ~0.054 / ~0.114 of the r6
   murk. mat_build.py:916 still says "Transmission 0.28 -> 0.40" where the shipped value is 0.18 (line 938), and
   :930 quotes the weight (0.36/0.76) as if it were the shipped murk. Fix the two comments and the notes paragraph.
3. **fix now** — QA-02-6 (lagoon black from above) is untested at the shipped gain. The "leaves the aerial lagoon
   alone" argument was computed for gain 0.55; at 0.15 cam06 keeps ~11 % of the r6 murk, and no cam06 render was made
   this round (mat_scene_check has the job; only hero/ceiling/cam03/cam05 are committed). One cam06 render pre-merge.
4. **fix now** — the ARCH/QA hand-off (materials_notes.md:960-968) overstates both share and magnitude. Re-measured on
   its own proposed plain box 900 224 1020 248: render aniso **0.75** vs ref **5.04**, colsd 10.3 vs 21.95; dropping
   the cornice rows takes rowsd 25.2 -> 13.8 (**45 %**, not "~2/3") and still leaves the test 6.7x short, so most of
   QA-05-2's direction failure is materials', not the box. And "13 px = **0.65 m**" (line 964) is asserted: no script
   derives it, and at the probe's own 84.9 m with 20 mm / 36 mm / 1920 px it is **1.03 m** (their own item-5
   arithmetic gives 9.4 cm/px). Restate the hand-off with the derived number; drop "re-boxing fixes the test".
5. **fix now** — item 7 is reported PASS on a self-chosen +-25 % window. Shore band lum moved 91.1 -> 91.7 against the
   brief's "+43.9 lum to reach 115.6", and saturation **rose** 0.487 -> 0.538 where the brief said without raising it.
   The leaf translucency/tint lift did not reach the box (probe: 23 % podium, 21 % water, ~45 % foliage). Report as
   not delivered, with the probe composition, so ENV/lighting can take it.
6. **carry** — the reflection box 900 760 1020 840 was never probed: mat_r7_probe.py lists it, mat_r7_probe.log covers
   six other boxes. The "crossed to the photo's side" reading rests on pixels alone. One probe run settles water vs shore.
7. **carry** — stale reference constants, mat_r7_measure.py:44-52: re-running `ref` on the same aligned sheet gives
   water_refl 164.6 / 0.370 (constants 168.9 / 0.339), shore_band sat 0.631 (0.663), ripples R-B -16.4 (-26.0). Stone
   rows reproduce exactly. Also mat_r6_measure.py:17 calls the coffer quarter-ratio reference 0.439 where the brief and
   notes use 0.265, and light_measure.py:194 has coffer/sky ref 0.39 where the notes say 0.437 — reconcile before r8.
8. **carry** — mat_r7_sheet.py:25 hard-codes `/Users/dk/.../reference/photos` instead of common.REFERENCE_DIR /
   $PFA_REFERENCE_DIR; its `--after` default is the superseded `r7c` whose previews were deleted, so a bare re-run fails.
9. **carry** — mat_build.py:631 comment says "G/R 0.832 -> 0.819"; the shipped (0.748, 0.590) is 0.789 (the r7b value).
10. **carry** — mat_r7_measure.load() bilinearly upsamples sub-scale renders to the hero grid; lighting verified that
    for luminance only. std / colsd / anisotropy are smoothed by the resample — never quote `--scale` renders for QA-05-2.
