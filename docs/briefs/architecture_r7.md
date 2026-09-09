# Architecture round 7 (no render) — brief from the lead (2026-09-09). Branch `architecture`. Read docs/briefs/process.md first.
Slot-filler while lighting r14 holds the GPU. `git merge main` first (main has your r6 + fixes).
1. Archivolt socket (QA-06-6 second half; ornament r6 proposal, docs/ornament_notes.md Round 6 §4 on branch ornament / after its merge on main):
   add a socket type `archivolt_run` on the rotunda's eight arches (outer face and, if the proposal says so, the inner face): origin at the
   springing, +X = tangent along the arc at the origin, +Y = outward face normal, +Z up; properties arc radius, arc angle (springing to
   springing), crown face width (0.22 m today), per-instance variant_seed; document in docs/sockets.md; arch_socket_check --type archivolt_run
   with an independent geometric assertion (origin on the arch face within 5 mm, +Y away from the wall). No geometry change to the arch.
2. r6 review carry 8: the entablature sub-courses (corona 0.25 m over a 1.66 m oversail, eggs 0.13 at 0.47 pitch, modillions 0.45 x 0.86)
   come from the 0.783 scaling, not the photo. Measure them on ref 169 / ref 085 crops (px at 13.42 px/m on the hero) and either confirm
   within 10 % or propose the corrected values with their consequence for the 1.37 m cornice (no build unless all three stay inside 1.37
   and the row registration holds; if built, re-run the qa_stack_offset log).
3. Ref 062 conflict for QA (decisions.md 2026-09-09): fit ref 062 with ATTIC_Z0 fixed at 29.18 and report the best station (az, D, lens) and
   residuals, so QA can re-station cam02 on the new stack without moving the courses.
Deliverables: assets/architecture.blend (sockets only), scripts, docs/sockets.md, notes "Round 7", report < 15 lines, last commit id. No renders,
no master write.
