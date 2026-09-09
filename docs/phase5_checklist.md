# Phase 5 delivery checklist (lead, 2026-09-09; runs when the definition of done in CLAUDE.md is met)

Gate: hero (cam01) >= 4.0, OR two consecutive QA rounds after materials r8 (the photo-projection pass) improving the hero by < 0.1.
Then, in this order, one Blender at a time, every run through scripts/blender_run.sh:
1. Final master: scripts/lead_build.sh (build + probe bake) on the merged main; ornament bake first if `orn_build.py -- --bake-pending` lists any.
2. Open time: `blender_run.sh 300 -- --background master.blend --python-expr "import time"` with timing in the log; must be < 60 s (round 6: 0.72 s).
3. Eevee navigability: the saved viewport state (light_presets.apply_viewport_eevee, LOD1 default, light_threshold 0.01, RT off) opens and the
   six QA cameras render in Eevee under 150 s total (QA-06-13 target); record the pass time.
4. 4K hero timing FIRST at 128 spp fixed, adaptive OFF, time_limit 0, 3840x2160, cam01, final preset, through blender_run.sh with max 7200 s
   (scripts/qa_4k_probe.py or light_preview --hero-only at 4K); record wall time and memory. Choose the final sample count from that time
   (target: the final frame under 90 min; 768 spp only if 128 spp took < 12 min).
5. 4K Cycles hero final at the chosen count, denoised, saved to renders/final/hero_cam01_3840x2160.png, with its side-by-side vs ref 169 in
   renders/qa_comparisons/final_hero_vs_ref169.png and the measured numbers from light_r12_measure / qa_measure.
6. Flythrough: CAM_flythrough (1224 frames @ 24 fps, docs/lighting_notes.md §23); re-run light_flythrough_check.py at LOD0 (prep review 5);
   Eevee test animation at 640x360, 16 TAA, every 2nd frame if needed, ffmpeg to renders/final/flythrough_test_640.mp4; record wall time.
7. Deliverables list in docs/status.md final entry: master.blend, assets/*.blend, renders/final/*, docs/tech_notes.md "Opening and rendering",
   docs/qa_round_XX.md final gate, docs/decisions.md.
Fable is used once here: the final gate judgement (QA critic brief docs/briefs/qa.md with "final" in the round name).
