# Materials round 8 — photo-projected concrete on the hero-facing faces (brief from the lead, 2026-09-09; go/no-go after QA round 6)

Why (decisions.md 2026-09-08 and 2026-09-09): four procedural rounds did not produce the photo's weathering signature on the hero
(anisotropy 0.40-0.75 vs 4-5 in ref 169; the stone reads as blotch, not as streaks running down the wall under the cornice and
string course). The definition of done (CLAUDE.md) counts rounds after this pass.
Inputs already on disk: materials' answer in docs/status.md "MAT r7 reported" (window-coordinate lookup or one UVProject modifier from
CAM_qa_01_lagoon_hero; photo as a mean-1.0 ratio = ref 169 aligned / flat-white render of the same frame; three masks: facing 25-70 deg,
projector visibility, attic / entablature / drum band; weight <= 0.6), architecture's answer in docs/arch_notes.md round 4 (one triplanar
world-metre UVMap per ARCH mesh, a projection needs its own layer; hero face index 00, object list), QA's aligned overlay
renders/qa_comparisons/round05_cam01_aligned_vs_ref169.png (scale 1.3108, dx -291.8, dy -124.6) and round 6's stack-offset table.
Constraints: (1) the projection multiplies the calibrated albedo chroma and value as a ratio; it must not bake the photo's sun (sunlit
numbers stay inside their windows: attic lum 178-201, hue 34-46, R-B >= 110; shade hue 29.5 +- 6). (2) It applies only to the ARCH
hero-facing attic band, entablature and drum (materials' band mask), weight <= 0.6, and falls back to the procedural elsewhere and
on every other camera; no visible seam at the mask edges from cam02 / cam05 (state the seam test). (3) The stack offset per course
(QA round 6 item 7) is applied as a per-band vertical shift in the projector UV, not by moving geometry: architecture's stack is frozen.
(4) Streak direction test: anisotropy on the attic panel box 900 224 1020 248 >= 2.0 and on QA's box 900 222 1020 256 >= 1.5; std
ratio >= 0.60; entablature row-std >= 35 on the model's cornice window. (5) Eevee must show the same albedo (it is a texture, so it
should; prove it with one Eevee hero crop). (6) Texture budget: one 4K RGB ratio map + one 4K mask pack, tracked under
assets/textures/projection/, licence line for ref 169 in docs/reference_sheet.md.
Deliverables: scripts/mat_projection.py (build the ratio map, the masks, and the UV layer or UVProject modifier on the listed ARCH objects
via a library override or a MAT-owned node group applied to MAT_concrete_* — do NOT edit assets/architecture.blend; if a UV layer on
ARCH meshes is unavoidable, stop and report: the lead will route it through architecture), assets/materials.blend, composite
renders/qa_comparisons/mat_r8_sheet.png (1:1 attic + entablature crops before / after / ref 169 with the numbers; cam02 and cam05
seam crops), Round 8 section in docs/materials_notes.md, commits after every successful script, report < 30 lines.
