# Architecture round 6 — register the hero stack (brief from the lead, 2026-09-09). Branch `architecture`. Read docs/briefs/process.md first.
`git merge main` first (main has your r5 + the review fixes). This round renders (GPU is free): Cycles crops on cam01 only, <= 64 spp.
Read: docs/qa_round_06.md (defect QA-06-1 and the "stack offset per course" table + renders/qa_comparisons/round06_stack_offset.png),
docs/decisions.md 2026-09-09 "After QA round 6", your own round-5 course-row table in docs/arch_notes.md.
QA measured (aligned overlay, 13.42 px/m, + = render higher than ref 169): attic crown +0.07, crown corona +0.30, panel frame top +1.27,
panel frame bottom +2.31, cornice corona +2.01, frieze top +1.34, frieze bottom +1.34, capital top +1.12 m. Attic storey render/ref 0.70,
capital 0.65, frieze 1.00. The outer silhouette (apex, corner top, W_a) fits ref 169/085/063 within 1 % and must keep doing so.
1. Re-measure the course heights on ref 169 (and ref 085 / 062 as cross-checks) with QA's alignment: attic storey (attic crown to cornice
   corona), attic panel frame, entablature position, capital height / column shaft split. Report each as metres with the two-photo agreement.
2. Move the courses inside the fixed envelope so every row in QA's table lands within +-0.15 m (2 px): the attic storey grows toward the
   photo's (0.70 -> ~1.0), the entablature corona drops ~2 m, the capital top ~1.1 m, columns shorten accordingly (the round-1 dome fit
   stays: dome, drum ring and attic crown do not move; state which arch_params change and by how much). Ornament sockets follow the
   courses (capitals, frieze_run at the new frieze, attic panels / figures / corner scrolls): arch_socket_check must pass and you report
   every socket group's z delta for ornament. Colonnade: only if the same courses are shared by parameter; say so.
3. Prove it: Cycles cam01 crop (rows 120-340, 64 spp) with the aligned overlay, the per-course table before / after / ref, silhouette
   fit within 1 % on the three photos, tri counts within +5 %, then re-run scripts/arch_uvproj.py (the projector camera is unchanged
   but every vertex moved) and repeat its named-point checks.
Deliverables: assets/architecture.blend, arch_params / arch_build changes, composite renders/qa_comparisons/arch_r6_sheet.png (overlay
before / after / ref with the table burnt in), notes "Round 6", commits after every successful script, report < 25 lines with the
socket z deltas for ornament and the last commit id.
