# Lighting round 14 prep (no render, no master write) — brief from the lead (2026-09-09). Branch `lighting`. Read docs/briefs/process.md first.
Slot-filler while QA round 6 holds the GPU: nothing in this round renders (no Eevee test animation yet; the lead schedules it in Phase 5).
`git merge main` first (main has your r13 merged with the lead's review fixes in common.configure_cycles).
1. Phase 5 flythrough path: scripts/light_flythrough.py predates rounds 4-13. Update the route to the current site (cam01 station and the
   cam02 SSE shore path from qa_cameras.py, colonnade walk level -0.60 from arch_params.COLONNADE_GROUND_Z, the north grove at 120-135 m from
   environment r8, the rotunda ceiling look-up), rebuild it into assets/lighting.blend, and validate WITHOUT rendering: sample the camera every
   12 frames, ray-cast from the camera position against ARCH + ENV (link the assets in a temp scene) and print a table of frame, position,
   nearest-hit distance; require >= 1.5 m clearance everywhere and no frame with the camera below the walk or inside the lagoon (z < WATER_Z + 0.5
   over water); speed profile: no segment faster than 6 m/s except the water crossing (<= 10 m/s); eased holds at the hero view (>= 3 s) and
   under the dome (>= 3 s). 720 frames at 24 fps unless the table says otherwise. Save the table in the notes.
2. Carries from docs/reviews/light_r13_review.md: 2 (sweep energy_eevee key), 5 (COMP comment), 6-11 where each is under 10 lines.
3. Delivery doc: write docs/tech_notes.md section "Opening and rendering master.blend" (the saved Eevee viewport state and what it contains,
   the Eevee-only rigs and why, how to render Cycles correctly: light_presets.apply_final_cycles or common.configure_cycles, sample counts and
   the measured times from rounds 4-6, the flythrough camera and how to render the test animation at 640x360 Eevee).
Deliverables: assets/lighting.blend, scripts/light_flythrough.py (+ a light_flythrough_check.py if separate), notes §23, docs/tech_notes.md
section, commits after every successful script, report < 20 lines with the clearance table summary and last commit.
