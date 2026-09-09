# Architecture round 5 (no render, no master write) — brief from the lead (2026-09-09). Branch `architecture`. Read docs/briefs/process.md first.
Slot-filler while QA round 6 holds the GPU: nothing in this round renders. `git merge main` first (main has your r4 merged).
1. Projection UV layer (precondition of the photo-projection pass, docs/briefs/materials_r8_projection.md). On the hero-facing objects you
   listed in docs/arch_notes.md round 4 (attic band incl. per-face 00/07/01 panels/frames/pilasters, ARCH_rotunda_entablature + dentils +
   modillions + eggs on BOTH LOD objects that share a mesh, drum/band/cornice) add a second UV layer `UVProj` = the vertex's position in the
   CAM_qa_01_lagoon_hero frame (scripted per vertex with world_to_camera_view, camera from qa_cameras.py; u,v in 0..1 of the 1920x1080 frame;
   vertices behind the camera or outside the frame clamped and flagged). `UVMap` stays the first and active layer. Verify numerically: at least
   three named vertices whose frame position you can predict (attic corner, cornice corona at face 00 centre, drum ring) land within 2 px of the
   arch_entab_probe map. Save into assets/architecture.blend; report tri counts unchanged and arch_socket_check unchanged.
2. Course-row table from the model (pairs with QA round 6 item 7): frame row on cam01 of attic top, attic panel frame top and bottom, cornice
   corona top and bottom, dentil bed, frieze top and bottom, architrave bottom, capital top, via arch_entab_probe --map; write it as a table in the
   notes (no render). If ref 169's rows are available in QA's round-6 report by the time you finish, add the per-course offset in metres.
3. Carries from docs/reviews/arch_r4_review.md: 1 (comment), 4 (commit the post-r4b silhouette log), 7 (QA alignment constant in one place, REF169
   path via common.REFERENCE_DIR), 8 (measure script threshold text = the brief's tests).
Deliverables: assets/architecture.blend, scripts/arch_uvproj.py, notes section "Round 5", report < 20 lines with the vertex checks and last commit.
