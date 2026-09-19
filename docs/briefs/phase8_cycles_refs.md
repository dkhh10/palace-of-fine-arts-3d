# Phase 8 Cycles station references — the parity baseline for QA 23 (brief from the lead, 2026-09-19). ENV builder (Opus high) on phase8d-env, after the master_delivery
rebuild that includes belt r2. GPU render; nothing else renders while it runs (the export chain's Gate 1 is CPU-only Blender and may run concurrently; its Gate 2 bake starts
only after you report).
Why: decisions.md "QA 22" — 8d moves the viewer away from the frozen Phase 5 Cycles references at the backdrop boxes by design; QA 23 measures parity against references
rendered from the Phase 8 master, while the Phase 5 references stay the record for the architecture boxes.
Do: from a scratch copy of master_delivery.blend (never the file itself; the haze-check script's method: delivery look asserted `AgX - High Contrast` / -2.8331 EV, Cycles GPU,
1920x1080, 32 spp fixed, adaptive OFF, OIDN), render the six QA stations (scripts/qa_cameras.py names CAM_qa_01..06) through scripts/blender_run.sh 1200 each, one Blender at
a time, into renders/qa_comparisons/cycles_p8/cam0N_1080_32spp.png (+ a 960 px copy each in renders/qa_comparisons/cycles_p8/960/). Also render the hero at the same settings
with the water plane hidden? NO — the references are the delivery look as-is. Compare each with the Phase 5 reference the QA rounds used (docs/qa_round_17.md names them;
round-13 references) at 960 px in one composite (6 rows: Phase 5 ref | Phase 8 ref): the architecture must be pixel-close (MAE at the QA-17 architecture boxes < 1 %),
the backdrop and the belt are where they differ — report those numbers. Commit the 960 px copies and the composite (full-res PNGs are gitignored) with the attribution
line; delete the scratch blend; report < 8 lines: paths, per-station architecture MAE, the backdrop deltas, wall time per frame, commit id.
