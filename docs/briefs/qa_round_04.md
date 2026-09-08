# QA round 04 — brief from the lead (2026-09-08)

Round 04 renders the master rebuilt after: lighting r09 + r10, architecture p4r2 (+ socket fixes), materials r4 + r5,
environment r4 + r5, ornament r4. Everything merged since round 03 is listed in docs/status.md (entries dated 2026-09-08).

Required this round, beyond the standard renders / comparisons / scores / defect list (docs/briefs/qa.md):
1. Status of every QA-03 defect with the number that proves it. Watch especially: QA-03-2 chroma (lighting r10 claims attic
   sat 0.549 / R-B 120.8 / lum 180.9 at 1920x1080 on QA's own boxes; verify with scripts/light_r10_measure.py or qa_measure),
   QA-03-3 fills (Cycles cam04 soffit/coffer 0.54/0.38 claimed; Eevee within 0.15 of Cycles claimed after the cutoff fix),
   QA-03-4/-9 flutes and base (architecture: real semicircular hollows; the hero-scale flute contrast is materials' flute relief),
   QA-03-8 coffers (they were LOD0-only and hidden in every previous QA render; now visible at all LODs, 0.38-0.55 m deep) and
   the ceiling rosettes (sockets re-framed; 16 on the base-ring face, 8 on coffer floors), QA-03-10 north wing (env: 0.95 raw /
   0.76 aligned), QA-03-11 cam06 (city field; forest darkened), QA-03-13/-14 shrubs, QA-03-15 capitals (cavity attribute live).
2. cam02 station (QA-03-6 / QA-02-17): the lead tested QA's (-40, 15, 1.4) and seven more stations at 40-60 m in the N/NW/W
   sectors (renders/previews/lead/cam02_cand*.png): the on-land ones are under tree crowns or have the colonnade between camera
   and rotunda. Run a probe sweep like scripts/qa_cam03_probe.py (Eevee, 640x360, low samples, one Blender run) over a grid of
   on-land stations (both shore paths N and S of the rotunda, the west lawn inside the colonnade arc, 30-70 m from the axis,
   lens 16-24 mm) and pick the station that best matches ref 062's letterboxed blend (apex within 3 % of the top, podium base row
   within 3 % of 85 % height, no water in the foreground, rotunda not occluded by trees > 10 % of its silhouette). Write the
   chosen station into scripts/qa_cameras.py (you own qa_*.py), render round 04 cam02 from it, and say what you chose and why.
3. Deliverables / performance as before (open time, LOD1 tris, Eevee s/camera; saved master preset is now GPU / 768 adaptive /
   OIDN / AgX High Contrast; CAM_flythrough_path present).
4. QA-03-16 (4K timing) is still open: lighting's two 4K attempts stalled in the tail after 60 and 92 minutes with no frame
   written, suspected to be the 4K compositor pass. If, and only if, all round-04 renders and the report are committed and no
   builder is on the GPU (pgrep), run ONE isolating test: 3840x2160, 16 spp, compositor OFF vs ON (scene.use_nodes / render
   use_compositing), each with a 20-min cap, and log the two wall times in docs/qa_round_04.md. Otherwise leave it and say so.
5. Gate composite renders/qa_comparisons/round04_gate.png (Cycles hero beside ref 169, six Eevee views, score deltas r03->r04).
Commit only docs/qa_round_04.md, docs/quality_checklist.md, scripts/qa_*.py, renders/qa_comparisons/round04_*,
renders/previews/qa/round04_* (git add explicit paths). Touch renders/previews/qa/round04_RENDERS_DONE when every render has
exited. Final report under 60 lines: score table with deltas, pass/fail lines, top 10 defects (id, owner, one line), the cam02
decision, composite path.
