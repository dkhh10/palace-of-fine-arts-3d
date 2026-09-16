# QA round 14 — Gate 4: the viewer proper (brief from the lead, 2026-09-16). Opus 5 xhigh. Fresh agent. Do NOT run Chrome or Blender.
Read: docs/qa_round_13.md (verdict, QA-13-1/13-2, carried list), docs/briefs/qa_round_13.md (method), docs/quality_checklist.md (tail), docs/qa_round_10b.md (the hero boxes),
docs/decisions.md from "2026-09-16 · Gate 4 round 5" to the end (UV dequantisation, probe irradiance override, ceiling re-bake, foliage hue, mist coefficient, light-path
branch test result), web/README.md on main (lighting modes, post chain, probe, impostors, walk, QA notes incl. the re-measured reference ratios), CLAUDE.md "Phase 6" definition
of done 6a, docs/briefs/phase6_gate4_viewer.md items 1-7.
References: station 1 = the Phase 5 Cycles hero as before; stations 2-6 = renders/previews/qa/round13_0N_*_cycles.png (1920x1080, 128 spp, compositor on, from master.blend,
this session) — NOT the round-09 frames. Rubric = the reference photos as in every round.
Inputs: the viewer engineer's Gate 4 capture named in the latest docs/status.md entry (six stations, baked + probe + impostors + water + post=all, placeholders gone), the
matching post-off capture, pair sheets vs the references, renders/web/tiles/<capture>/ (cam01 six 100 % tiles), the perf json (1440p median frame time, GPU cost, resident memory,
draw calls), the walk-probe json, the loading-screen screenshot.
1. Parity per station: whole-frame luma ratio and the round-10b boxes (lum / hue / sat / std) vs the reference, and the QA-13 values, so each Gate 4 item is attributed: post
   (bloom/AO/mist/vignette), probe irradiance (backdrop + foliage), impostors, water. Confirm QA-13-1 closed (band 20 520 540 645 B > R+20 <= 3.9 %), QA-13-2 closed (cam04 coffer
   field vs 60.7 / p10 27.8), QA-12b-1 status (% building pixels G > R at cam02/06, Phase 5 0.1 / 9.7), the sunlit-attic sat hold, cam06 (the old reference hid a 0.71x deficit).
2. Water at cam01: the rotunda reflects (reflection box lum/hue/sat/std vs the Phase 5 hero per docs/qa_round_10b.md), ripple structure at 100 %, Fresnel at the near edge.
3. Impostors: far-tree silhouettes vs the reference at cam01/cam02/cam06 (paler/flatter is on record), any visible frame seams or pop in the 12-heading sweep the viewer provides.
4. Foliage hue: near-tree cards and shrubs/reeds vs Cycles (amber-brown vs olive-green is on record; state the hue error per station and whether the decision logged in
   decisions.md closed it).
5. Mist: the haze at cam03/cam06 vs the reference (airlight = cap (1 - exp(-k mist)), cap 0.25, k 5), not a plain linear fog.
6. cam01 six tiles at 100 %: every geometry or material defect regardless of the numbers (filled openings, flat surfaces, missing ornament, seams, z-fighting, impostor edges,
   leaf-card cutouts, reflection artefacts). Name sweep: restate the export engineer's latest count.
7. Definition of done 6a: score table per station (all rubric rows) vs round 13 and round 9 (Phase 5); every station within 0.5 of its Phase 5 score and none below 2.5?
   Water reflects the rotunda at the hero? Walk clamp holds (probe json: never below WATER_Z + 0.1, never inside the lagoon polygon)? Loading screen shows progress? Perf >= 45 fps
   median at 1440p or the measured number with the GPU-vs-CPU attribution? Verdict: GATE 4 PASSED / ONE MORE ROUND (name the items) / FAILED (name the blocker).
Write docs/qa_round_14.md (< 120 lines), renders/web/round14_gate.png (960 px composite), append docs/quality_checklist.md; commit only those + scripts/qa_*.py on main.
Report < 20 lines: verdict, per-station scores, the three worst boxes with numbers, tile defects, commit id.

Addendum (lead, 2026-09-16): the capture is `round14` in the phase6-viewer worktree (`.claude/worktrees/phase6-viewer/renders/web/`: round14_cam01..06.png full-res untracked on disk,
960/ copies, six pair sheets, tiles/round14/, round14_perf.json, round14_walk.json, 960/round14_loading_screen.jpg). Read docs/status.md's "round14 CAPTURED" entry for the
whole-frame ratios and what was NOT shipped (half-res levers, probe-as-specular). Perf is 34.6 fps with everything on: score it as measured with the viewer's attribution (Reflector
second traversal + full-res bloom over one vsync interval); the 45 fps work continues in parallel. The sky-branch hypothesis for QA-12b-1 was refuted (decisions.md); the olive cast
is downstream of the bake and still open — report its numbers, do not attribute it to the lightmaps.
