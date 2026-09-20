# Phase 9 lighting round — station 2's blue-violet shaded stone (brief from the lead, 2026-09-20). Opus 5 high. Fresh agent.
Branch `phase9-light`, worktree .claude/worktrees/phase9-light (merge main first). Owns assets/lighting.blend, scripts/light_build.py, scripts/light_r19_*.py
(new), docs/lighting_notes.md (append a section 27), renders/previews/lighting/*, renders/qa_comparisons/lighting_r19_*. Read docs/briefs/process.md first.

## Why (approved by the user 2026-09-20, docs/decisions.md "PHASE 9 APPROVED": a Phase 5 lighting change)
QA-08-2 / QA-09-6, open since round 08 and carried through Phase 8: at station 2 (CAM_qa_02, the NNE rotunda station) the shaded fluted shafts of the
camera-facing rotunda face render blue-violet in Cycles where ref 062 shows warm pink-grey stone. Measured in docs/briefs/phase8b_viewer_fix_report.md item c
(CIELAB b*, boxes `light_r16_measure.py BOXES["02"]`): Cycles shade_pier -5.01 / shade_pier_r -18.35 / shade_arch -3.29 against the photo +10.89 / +10.99 /
+5.33; shade_frieze (control) Cycles +12.24, photo +11.07. The violet is the direct NNE sky fill: `LIGHT_shade_fill` (light_build.py SHADE_FILL: az 25 el 2,
colour (0.03, 0.02, 1.00), 70 W/m2 in Cycles) whose own comment records the cost ("cam02's shaded pier, hue 262 against QA-07-11's 25-60 window") and whose
reason to exist is the hero's shaded attic (hue window 23.5-35.5, lum 103.5-126.5, sat <= 0.50; light_r16_measure.py WIN). Read the SHADE_FILL, SKY_DIFFUSE_TINT*,
SKY_DIFFUSE_BOOST and SUN_BLUE_MULT comments in scripts/light_build.py and docs/lighting_notes.md sections 21, 24, 26 before touching anything: every knob's
measured cost is recorded there, and the anti-sun / horizon weights are the levers that separate a shaded wall from the hero's attic.

## Acceptance (Cycles, 1920x1080, 32 spp fixed, adaptive off, OIDN, the delivery look; scripts/p8_cycles_refs.py on a scratch copy of the rebuilt master_delivery)
1. Station 2, boxes shade_pier / shade_pier_r / shade_arch (r16 boxes; r17 notes shade_arch lands on the central shaft cluster, keep it) and soffit_l / soffit_r
   (light_r17_measure.py): **b* >= +5, h_ab 40-80 deg, R-B >= +10** on every one; shade_frieze held at **+11.4 +- 1.5**; the `sky` box unmoved (camera rays).
2. Hero (CAM_qa_01) HOLD: every box of scripts/light_r17_measure.py BOXES["01"] and scripts/qa_r17_probe.py's hero boxes within **3 % of luma and 2 deg of hue**
   of the BEFORE frame, the shaded_attic and sunlit_attic windows still met. The noise floor is the control: render cam01 once more with `--seed 1` and report
   MAE(seed 0, seed 1); a box that moves less than that floor has not moved.
3. Stations 3 and 4 HOLD the same way (cam03 p10 and column-shade luma, cam04 ceiling ratios from light_r17_measure CEIL): the colonnade's deep shade in
   Cycles is right and must not open up; the lagoon (cam01 near-water sat window 0.22-0.32, hue) unmoved.
4. Eevee cost: report cam02 / cam03 Eevee preview seconds before / after (the r14 shadow-resolution lesson).

## BEFORE frames — do not re-render them
The lead is rendering the six station references from the current master_delivery into MAIN `renders/qa_comparisons/cycles_p8/cam0N_1080_32spp.png`
(logs renders/logs/p9_cycles_ref_0N.log). The GPU is the lead's until the marker file MAIN `renders/qa_comparisons/cycles_p8/.p9_refs_done` exists.
Do all CPU work first (merge, read, write the sweep + measure scripts, dry-run the measurement on the BEFORE frames as they appear). Before your first
Blender run, wait with ONE blocking command: `until [ -f "<MAIN>/renders/qa_comparisons/cycles_p8/.p9_refs_done" ]; do sleep 30; done` (max 45 min; if it
does not appear, stop and report). From then on the GPU is yours and nobody else renders: one Blender at a time, scripts/blender_run.sh with honest seconds
(lead_build.sh in your worktree for the master rebuild; 1200 s per station render; keep sweeps to cam02 + cam01 at 32 spp, verify the hold on 03/04 once at the end).

## Build
scripts/light_r19_sweep.py (the candidates: e.g. the NNE lamp's colour re-solved toward the photo's warm shade, its energy traded against SKY_DIFFUSE_TINT /
ANTISUN_P so the hero's attic holds, a horizon-band or sun-side counterweight — you choose from measurement, at most 6 candidates, each one rebuilt master +
cam02 + cam01), scripts/light_r19_measure.py (extends light_r17_measure with CIELAB b* / h_ab / R-B per box and the deltas against BEFORE), scripts/light_r19_sheet.py
(a 960 px composite: BEFORE / AFTER / ref 062 crops of the shaded shafts, plus the hero attic BEFORE / AFTER). Ship the winner in light_build.py with the
knob comments written in the file's own style (what moved, what it measured, why). Every candidate's numbers go in docs/lighting_notes.md 27.

## Do NOT
Touch materials, ENV, ARCH, export/, web/, master.blend in MAIN, or the Phase 5 exposure / look. Do not rebuild MAIN's master. No Chrome.

## Report (< 25 lines, numbers only) into docs/briefs/phase9_light_report.md and the final message
Per box before / after / photo for station 2; the hero hold table; stations 3/4 hold; Eevee seconds; the sheet path; the winning knob values; test suite
count in every commit message (run whatever tests scripts/ has for lighting; if none, say "no suite"); last commit id. Hand-off to the bake engineer: which
sky sockets changed (camera / glossy / diffuse) so the chain re-bake can skip the untouched equirects.
