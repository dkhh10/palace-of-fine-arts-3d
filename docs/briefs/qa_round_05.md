# QA round 05 — brief from the lead (2026-09-08)

Round 05 renders the master rebuilt after polish round 3: lighting r11, materials r6, environment r6, architecture mini-round
(rib material, ref 062 fit). What merged and each owner's claimed numbers: docs/status.md entries after "QA round 4 in".
Required this round, beyond the standard renders / comparisons / scores / defect list (docs/briefs/qa.md):
1. Status of every QA-04 defect with the number that proves it. Watch: QA-04-1 Eevee vault (lighting: probe bake was on the
   cutoff rig; claims Eevee coffer 0.325 / soffit E 0.419 vs Cycles 0.387 / 0.532), QA-04-2 shade (lighting says the shaded
   attic hue is albedo and that cam03's ref 128 is a midday photo: RE-BASE the cam03 shade test on a golden-hour reference or
   state the test as shade-vs-sunlit ratio on ref 169; say what you chose), QA-04-3 stone at 1:1 (materials: attic std 0.598 of
   ref via macro maps, entablature 0.51 unchanged and handed to architecture as cornice/dentil depth; waterline zone; cornice
   run-off), QA-04-4 shoreline (env: p90 shrub 2.83 m, 3 willows, podium base hidden 78 %, Greek key visible 93.6 % from cam05),
   QA-04-5 columns (mat hue 26.8, lum 119; lighting 123.7), QA-04-6 wings (env north band 1.00 of ref; frame-left band is the
   SOUTH wing per environment: your (e) labels were swapped, fix the labels), QA-04-7 coffers (Cycles 0.387; rib material
   MAT_plaster_ceiling_rib now separate), QA-04-8 water (hue ~204 after three levers; reflection sat 0.13), QA-04-13 cam06
   (8 roof colours / 13 footprints), QA-04-14 cam02 shore edge, QA-04-10 cam05 apex (target z 21.5).
2. Deliverables / performance as before; the saved Eevee state is now light_threshold 0.01, raytracing off, taa 8/16.
3. Gate composite renders/qa_comparisons/round05_gate.png with deltas r04 -> r05, and a one-line trend per camera across
   rounds 02-05 (are scores still improving? which rows are stuck?). The lead decides from that whether to continue polish
   rounds or change approach (e.g. texture projection from reference photos for the concrete).
4. If, and only if, all round-05 work is committed and no builder is on the GPU: the 768-spp 4K hero timing (QA-03-16) with a
   90-min cap, logging progress via --time-limit 5400 so a frame is written; report wall time and whether the frame completed.
Commit only docs/qa_round_05.md, docs/quality_checklist.md, scripts/qa_*.py, renders/qa_comparisons/round05_*,
renders/previews/qa/round05_* (explicit paths). Touch renders/previews/qa/round05_RENDERS_DONE when every render has exited.
Final report under 60 lines: score table with deltas, trend line per camera, pass/fail lines, top 10 defects (id, owner, one
line), the cam03 re-base decision, the 4K result or why skipped, composite path.
