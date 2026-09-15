# QA round 12b — Gate 2 re-check after QA-12-1 (brief from the lead, 2026-09-15). Opus 5 xhigh. Read docs/qa_round_12.md, docs/briefs/qa_round_12.md, the last three docs/decisions.md entries (atlas split; grain as a detail layer; QA-12-1 material share closed), export/README.md "Gate 2" tail (detail sets, normals 19/19, the 8-bit height finding), web/README.md (detail layer, ?detail=0).
What changed since round 12: every ARCH/ground set ships a real normal (was 7 null); the six merged UV1 masses have their own atlases (hero stone coverage 0.056 -> 0.191,
colonnade texel 9.4 -> 1.07 cm on the instanced meshes, 5.3 cm on the merged wall); a world-space tiling detail layer (albedo ratio / roughness / normal from the Phase 5
materials' own height at the Bump's slope) is applied to 20 materials; 62/62 sets attach. Inputs: renders/web/gate2_cam01..06.png (the viewer engineer's final capture,
detail on, pbr + direct, placeholders hidden), pair sheets + json, renders/web/tiles/gate2/, gate2_perf.json, and the viewer's own QA-12-1 box table in its commit message /
renders/web/gate2_*.json (detail on vs off). Do NOT run Chrome or Blender.
1. QA-12-1 at 100 %: cam05 pier face, cam01 south colonnade wall, cam03 near column — state the material share vs the lighting share of the remaining gap explicitly:
   the Phase 5 box std includes shade and occlusion that `direct` mode cannot show (no shadows, no bounce, no AO); judge the material rows on hue/sat/texel density/grain
   PRESENCE at 100 %, not on the box std alone. The 8-bit source height finding (texel gradient below 1/255) is on record: do not ask for relief the source does not hold.
2. QA-12-2 dome cap, QA-12-3 colonnade texel density, QA-12-4 (per-instance variation, Gate 3 by construction): FIXED / OPEN / GATE 3.
3. The cam01 six tiles again; new defects (seams from the re-laid atlases, detail tiling repeats visible at 100 %, colour-space errors).
4. Score table Material realism / Edge wear / Repetition per station vs round 9 and round 12; verdict GATE 2 PASS / FAIL with the parity rule applied to the MATERIAL share
   (a row whose remaining deficit you attribute to lighting is not a Gate 2 failure — say so per row). Budget lines restated.
Write docs/qa_round_12b.md (< 100 lines), renders/web/round12b_gate.png, append docs/quality_checklist.md; commit only those + scripts/qa_*.py. Report < 20 lines.
