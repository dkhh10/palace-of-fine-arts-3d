# Environment round 7 — brief from the lead (2026-09-09). Branch `environment`, worktree .claude/worktrees/environment. Read docs/briefs/process.md first.

Context on disk: your branch (19b4514) holds "Polish round 7" in docs/environment_notes.md (line ~908): measurement + code complete
for cam03 paving / walk level -0.60 / edge planting, shore sun samples (QA-05-10), cam06 road pad; the NE shoreline is verified
correct (renders/qa_comparisons/env_r7_shoreline.png; item closed); the south wing (QA-05-5) is LIGHTING's (sky term), not planting.
No Blender run happened last session; the chain scripts lived in the old scratchpad and must be re-created from env_build.py.
Read that section, docs/qa_round_05.md defects QA-05-4, -05-9/-10/-11 and section (f), and docs/status.md from "QA round 5 in" on.

Items:
1. Build assets/environment.blend with the round-7 code (env_build.py chain). Report LOD1 triangle count (was 4.66 M; ceiling 4.8 M).
2. cam03 ground: paving / walk level / edge planting per your notes; test as in your notes (ground box 420 560 900 720 std and level
   vs ref 128 / ref 169 as you defined it); render cam03 Eevee before/after.
3. QA-05-10 shore band: the deficit is level (1.5-1.9x), not occlusion; your shore sun samples prove where the sun reaches. Report
   the shore band level after the build; if the remainder is the sky term, hand it to lighting with the number.
4. cam06 road pad / streets (QA-05-9 leftovers): render cam06 Eevee before/after, footprint / roof-colour counts unchanged or better.
5. Do NOT touch the lagoon water or bed materials (QA-05-4 near-water hue is MAT_water_lagoon + horizon sky: materials + lighting).
   Do not add planting for the south wing.
Deliverables: assets/environment.blend rebuilt, composite renders/qa_comparisons/env_r7_sheet.png (cam03, cam05 shore, cam06:
before / after / ref with numbers), docs/environment_notes.md round-7 section completed, commits after every successful script,
final report < 30 lines.
