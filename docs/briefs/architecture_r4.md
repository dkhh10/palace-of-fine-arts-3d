# Architecture round 4 — brief from the lead (2026-09-09). Branch `architecture`, worktree .claude/worktrees/architecture. Read docs/briefs/process.md first.

Context on disk: your branch (745a512) holds "Polish round 4" in docs/arch_notes.md (line ~657): the QA-05-6 derivations
(entablature split re-measured on ref 169: architrave 1.15 / frieze 0.90 / cornice 1.75 m, total 3.80 unchanged; corona projection
1.66 m; cornice profile rebuilt in code) and the drum-ring re-measurement (report only). The geometry is in code but NOT yet baked
into assets/architecture.blend and not rendered. Read that section, docs/qa_round_05.md section (b) (entablature std 0.52 of ref;
row std 20.9 vs 53.6: hard horizontal shadow bands under the cornice and dentils are missing) and defect QA-05-6.

Items:
1. QA-05-6 (major). Build the measured cornice profile / dentil course into assets/architecture.blend (all LODs; LOD1 stays the
   viewport default; report LOD0/1/2 triangle counts before/after; keep the ARCH total within +10 %). Silhouette check: cam01 fit vs
   ref 169 / 062 / 063 must stay within 1 % (scripts/arch_compare.py / arch_silhouette.py); NO rotunda proportion change
   (decisions.md 2026-09-08). Sockets: scripts/arch_socket_check.py must pass unchanged (frieze_run sockets follow the frieze face).
   Test: entablature box 900 262 1020 296 on a Cycles hero (1920x1080, 64 spp, your rebuilt master, apply the FINAL look preset)
   luminance std >= 0.60 of ref 169's 64.6, row-std >= 35. Composite renders/qa_comparisons/arch_r4_sheet.png: 1:1 entablature
   crop before / after / ref 169 with the numbers.
2. Drum-ring re-measurement: if it implies a geometry change, report the number and the ref-062/063 consequence; do not change
   proportions without the lead's decision.
3. Lead question to answer in the report (for the photo-projection fallback): which ARCH objects make up the hero-facing attic band,
   entablature and drum (names, UV state: do they have non-overlapping UVs or would a camera projection need its own UV layer?).
Deliverables: assets/architecture.blend rebuilt, arch_params/arch_lib changes, docs/arch_notes.md round-4 section completed with
numbers, sheet, commits after every successful script, final report < 30 lines.
