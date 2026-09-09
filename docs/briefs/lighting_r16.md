# Lighting round 16 — the last polish round before Phase 5 (brief from the lead, 2026-09-09). Branch `lighting`. Read docs/briefs/process.md first.
`git merge main` first (main has MAT r9/r9b, QA round 08, cam02 at 27 mm). Opus high, SHORT: one sweep, one Eevee five-camera pass, at most
2 Cycles hero frames (64-128 spp) + 1 Cycles cam02 (720p). Materials is idle; nothing else renders. Report < 25 lines.
Read: docs/qa_round_08.md defects QA-08-2, QA-08-3, QA-08-7, QA-08-13 and sections on cam02 / the hero chroma; docs/reviews/light_r15_review.md carries;
docs/flythrough_plan.md (branch phase5, .claude/worktrees/phase5/docs/flythrough_plan.md) findings 1-3.
0. cam02's lens is now 27 mm: re-base your cam02 boxes on one Eevee frame from the new frame (as r15 item 0), say which are new.
1. QA-08-3 (blocker, hero). Sunlit stone sat 0.462 / R-B 104.9 vs the photo's 0.582 / 134.2; materials proved the albedo cannot carry it without
   breaking the shaded hue window (docs/materials_notes.md Round 9b, mat_r9b_constraint.py), and Punchy is worse than the shipped look. The
   remaining lever is the SUN: temperature / tint / the sun-disc vs sky split at el ~8 (a warmer, more saturated direct term with the diffuse sky
   held). Sweep it on the hero: target attic 900 222 1020 256 sat >= 0.53 and R-B >= 120 at lum 178-201, with the shaded attic 1110 225 1150 260
   held at hue 23.5-35.5 / sat <= 0.50 / lum 103.5-126.5 (now 127.8, 1.3 over: land it if the same sweep can), columns hue 24.5 +- 4, and the
   reflection box R-B >= +35 / hue 25-45 (a warmer sun warms the mirror too: welcome, measure it). If the sun cannot land sat 0.53 without the
   sky boxes leaving their windows, report the frontier and ship the best point.
2. QA-08-2 (blocker, cam02): the camera-facing side is indigo (pier hue 263 / sat 0.46, pier_r / sunlit_pier 1.046: no directional light on
   that face). Window: hue 25-60 at sat <= 0.35 on the shaded pier, and the face must show a sunlit / shaded split. The NNE fill lamp is aimed
   at the hero; find what the NNE face needs (a second lamp or the sky's anti-sun term) without moving the hero's shade boxes.
3. QA-08-7 (major, cam03): walk hue 92.1 (blue -> green; window 25-60). One knob with the cam03 black fraction (12.6 %) and outer row (0.166) held.
4. QA-08-13 + Phase 5: the master's frame range went 1-1224 -> 1-2616 because light_flythrough.py takes cam02's station from qa_cameras and cam02
   crossed the building. Decision: the flythrough stays ~50 s (1200-1300 frames at 24 fps); re-plan the route for the new cam02 (or route past
   the NNE shore without the full crossing), fix the hold-boundary speed step (plan finding 1, ACCEL 2.5 respected at frames ~85 and ~1105-1129),
   include ORN in light_flythrough_check's link (finding 2) and re-run the check at --step 4 on LOD1 (state the gallery / outside minima), state
   the frames 398-408 window (finding 3). No animation render.
5. r15 review carries (docs/reviews/light_r15_review.md item 4): docstring, §25.3 AFTER column, Eevee hero attic hue 36.5, sheet path.
Hold list: hero sky boxes, hero shaded attic hue/sat, columns, reflection box, cam06 roofs, cam03 black fraction / outer row, cam05 lagoon sat.
Deliverables: light_presets values, assets/lighting.blend, light_r16_sheet.png (hero + cam02 + cam03 before / after / ref, ONE composite), §26 in
the notes with the acceptance table on your rebuilt master (object count stated), commits after every successful script, report < 25 lines with
the numbers per box, the flythrough frame count and clearance minima, and the last commit id.
